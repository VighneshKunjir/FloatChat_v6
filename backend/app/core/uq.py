"""
Monte Carlo Dropout Uncertainty Quantification Service

Implements MC Dropout (Gal & Ghahramani, 2016) for Bayesian UQ:
- Keep dropout active during evaluation
- Run 50 stochastic forward passes
- Compute mean, std, 90% CI, 95% CI per depth level
"""
import torch
import torch.nn as nn
import numpy as np
from typing import List, Dict, Tuple
from dataclasses import dataclass

from app.ml.model import PhysicsInformedBiLSTM


@dataclass
class UncertaintyBound:
    """Uncertainty bounds for a single depth level."""
    depth_dbar: int
    mean_temp: float
    std_temp: float
    ci90_temp_lower: float
    ci90_temp_upper: float
    ci95_temp_lower: float
    ci95_temp_upper: float
    mean_sal: float
    std_sal: float
    ci90_sal_lower: float
    ci90_sal_upper: float
    ci95_sal_lower: float
    ci95_sal_upper: float


# Standard 16 depth levels
STANDARD_DEPTHS = [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]

# Z-scores for confidence intervals
Z_90 = 1.645
Z_95 = 1.960

# Number of Monte Carlo passes
MC_PASSES = 50


def run_mc_dropout_inference(
    model: PhysicsInformedBiLSTM,
    x_scaled: torch.Tensor,
    temp_scaler,
    sal_scaler,
    n_passes: int = MC_PASSES,
) -> Tuple[List[UncertaintyBound], Dict[str, np.ndarray]]:
    """
    Run Monte Carlo Dropout inference.
    
    Args:
        model: Trained PhysicsInformedBiLSTM (dropout enabled)
        x_scaled: Preprocessed input tensor of shape (1, 3, 32) or (batch, 3, 32)
        temp_scaler: Fitted StandardScaler for temperature
        sal_scaler: Fitted StandardScaler for salinity
        n_passes: Number of Monte Carlo forward passes
    
    Returns:
        List of UncertaintyBound per depth level
        Raw predictions dict for potential debugging
    """
    model.train()  # Enable dropout
    
    # Ensure batch dimension
    if x_scaled.dim() == 2:
        x_scaled = x_scaled.unsqueeze(0)
    
    # Ensure on same device as model
    device = next(model.parameters()).device
    x_scaled = x_scaled.to(device)
    
    # Storage for predictions
    all_temp_preds = []
    all_sal_preds = []
    
    with torch.no_grad():
        for _ in range(n_passes):
            temp_scaled, sal_scaled = model(x_scaled)
            
            # Convert to numpy and inverse transform
            temp_pred = temp_scaler.inverse_transform(temp_scaled.cpu().numpy())
            sal_pred = sal_scaler.inverse_transform(sal_scaled.cpu().numpy())
            
            all_temp_preds.append(temp_pred)
            all_sal_preds.append(sal_pred)
    
    # Stack: (n_passes, n_samples, 16)
    temp_preds = np.stack(all_temp_preds, axis=0)
    sal_preds = np.stack(all_sal_preds, axis=0)
    
    # Mean across MC passes
    mean_temp = np.mean(temp_preds, axis=0).squeeze(0)  # (16,)
    mean_sal = np.mean(sal_preds, axis=0).squeeze(0)    # (16,)
    
    # Std across MC passes
    std_temp = np.std(temp_preds, axis=0, ddof=1).squeeze(0)
    std_sal = np.std(sal_preds, axis=0, ddof=1).squeeze(0)
    
    # Build UncertaintyBound list
    bounds = []
    for i, depth in enumerate(STANDARD_DEPTHS):
        bounds.append(UncertaintyBound(
            depth_dbar=depth,
            mean_temp=float(mean_temp[i]),
            std_temp=float(std_temp[i]),
            ci90_temp_lower=float(mean_temp[i] - Z_90 * std_temp[i]),
            ci90_temp_upper=float(mean_temp[i] + Z_90 * std_temp[i]),
            ci95_temp_lower=float(mean_temp[i] - Z_95 * std_temp[i]),
            ci95_temp_upper=float(mean_temp[i] + Z_95 * std_temp[i]),
            mean_sal=float(mean_sal[i]),
            std_sal=float(std_sal[i]),
            ci90_sal_lower=float(mean_sal[i] - Z_90 * std_sal[i]),
            ci90_sal_upper=float(mean_sal[i] + Z_90 * std_sal[i]),
            ci95_sal_lower=float(mean_sal[i] - Z_95 * std_sal[i]),
            ci95_sal_upper=float(mean_sal[i] + Z_95 * std_sal[i]),
        ))
    
    # Return bounds and raw data for debugging/validation
    raw_data = {
        'temp_preds': temp_preds,
        'sal_preds': sal_preds,
        'mean_temp': mean_temp,
        'mean_sal': mean_sal,
        'std_temp': std_temp,
        'std_sal': std_sal,
    }
    
    return bounds, raw_data


def validate_uncertainty_bounds(bounds: List[UncertaintyBound]) -> Dict[str, bool]:
    """
    Validate uncertainty bounds meet acceptance criteria.
    
    Returns dict with validation results.
    """
    results = {
        'upper_gt_mean_temp': True,
        'upper_gt_mean_sal': True,
        'thermocline_var_gt_abyssal': False,
    }
    
    # Check upper CI > mean for all depths
    for b in bounds:
        if not (b.ci95_temp_upper > b.mean_temp):
            results['upper_gt_mean_temp'] = False
        if not (b.ci95_sal_upper > b.mean_sal):
            results['upper_gt_mean_sal'] = False
    
    # Thermocline (indices 2-5: 50, 75, 100, 150 dbar) should have 
    # higher variance than abyssal 1000m (index 15)
    thermo_std_temp = np.array([b.std_temp for b in bounds[2:6]])
    abyssal_std_temp = bounds[15].std_temp
    
    if np.mean(thermo_std_temp) > abyssal_std_temp * 2:  # Significantly higher
        results['thermocline_var_gt_abyssal'] = True
    
    return results


def uncertainty_bounds_to_dict(bounds: List[UncertaintyBound]) -> List[dict]:
    """Convert UncertaintyBound list to JSON-serializable dict list."""
    return [
        {
            'depth_dbar': b.depth_dbar,
            'mean_temp': b.mean_temp,
            'std_temp': b.std_temp,
            'ci90_temp_lower': b.ci90_temp_lower,
            'ci90_temp_upper': b.ci90_temp_upper,
            'ci95_temp_lower': b.ci95_temp_lower,
            'ci95_temp_upper': b.ci95_temp_upper,
            'mean_sal': b.mean_sal,
            'std_sal': b.std_sal,
            'ci90_sal_lower': b.ci90_sal_lower,
            'ci90_sal_upper': b.ci90_sal_upper,
            'ci95_sal_lower': b.ci95_sal_lower,
            'ci95_sal_upper': b.ci95_sal_upper,
        }
        for b in bounds
    ]