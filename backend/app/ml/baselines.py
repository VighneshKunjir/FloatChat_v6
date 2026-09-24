"""Baseline regressors: persistence (t-1) and gradient boosting.

Metric schema matches ForecastResult.metrics_comparison in src/types.ts:
{model, profile_rmse, profile_mae, thermocline_rmse, deep_rmse,
 physical_violation_rate}. All RMSE/MAE in original physical units;
violation rate in percent.
"""
import numpy as np
from sklearn.ensemble import HistGradientBoostingRegressor
from sklearn.multioutput import MultiOutputRegressor
from typing import Dict, Tuple

# Canonical depth indices: 5,20,50,75,100,150,200,250,300,400,500,600,700,800,900,1000
THERM_IDX = [2, 3, 4, 5]  # 50-150 dbar
DEEP_IDX = [10, 11, 12, 13, 14, 15]  # 500-1000 dbar


def persistence_predict(X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Predict the next profile as the last input cycle (t-1).

    X shape: (n, 3, 32) with [16T, 16S] per step.
    Returns (temp_pred, sal_pred), each (n, 16).
    """
    return X[:, 2, :16].copy(), X[:, 2, 16:].copy()


def train_gradient_boosting(
    X_train: np.ndarray,
    yT_train: np.ndarray,
    yS_train: np.ndarray,
    seed: int = 42,
) -> Dict[str, MultiOutputRegressor]:
    """Fit one regressor per depth level per variable (parallelized)."""
    Xf = X_train.reshape(len(X_train), -1).astype(np.float64)
    temp_model = MultiOutputRegressor(
        HistGradientBoostingRegressor(random_state=seed), n_jobs=-1
    )
    sal_model = MultiOutputRegressor(
        HistGradientBoostingRegressor(random_state=seed + 1), n_jobs=-1
    )
    temp_model.fit(Xf, yT_train.astype(np.float64))
    sal_model.fit(Xf, yS_train.astype(np.float64))
    return {"temp": temp_model, "sal": sal_model}


def predict_gradient_boosting(models: Dict, X: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
    """Run fitted GB models. Returns (temp_pred, sal_pred), each (n, 16)."""
    Xf = X.reshape(len(X), -1)
    return models["temp"].predict(Xf), models["sal"].predict(Xf)


def _sigma_original_units(t: np.ndarray, s: np.ndarray) -> np.ndarray:
    """TEOS-10 polynomial potential density (physical units only)."""
    return 28.14 - 0.0735 * t - 0.00469 * t**2 + 0.802 * (s - 35.0)


def violation_rate_percent(t_pred: np.ndarray, s_pred: np.ndarray) -> float:
    """Percent of predicted profiles with a density inversion."""
    sigma = _sigma_original_units(t_pred, s_pred)
    depths = np.array(
        [5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000],
        dtype=float,
    )
    d = np.diff(sigma, axis=1) / np.diff(depths)
    return float((d < -1e-6).any(axis=1).mean() * 100.0)


def profile_metrics(
    yT_true: np.ndarray,
    yS_true: np.ndarray,
    yT_pred: np.ndarray,
    yS_pred: np.ndarray,
    model_name: str,
) -> Dict:
    """Compute the metrics_comparison row for one model (original units)."""
    return {
        "model": model_name,
        "profile_rmse": round(float(np.sqrt(np.mean((yT_pred - yT_true) ** 2))), 4),
        "profile_mae": round(float(np.mean(np.abs(yT_pred - yT_true))), 4),
        "thermocline_rmse": round(
            float(np.sqrt(np.mean((yT_pred[:, THERM_IDX] - yT_true[:, THERM_IDX]) ** 2))), 4
        ),
        "deep_rmse": round(
            float(np.sqrt(np.mean((yT_pred[:, DEEP_IDX] - yT_true[:, DEEP_IDX]) ** 2))), 4
        ),
        "physical_violation_rate": round(violation_rate_percent(yT_pred, yS_pred), 3),
    }
