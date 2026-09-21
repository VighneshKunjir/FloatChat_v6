# FloatChat: Machine Learning & Explainability Specification

## 1. Model Architecture: Physics-Informed Bidirectional LSTM with Monte Carlo Dropout

### Neural Architecture
- **Network Family:** Bidirectional Long Short-Term Memory (Bi-LSTM) with residual depth projection.
- **Input Dimension:** $D_{\text{in}} = 32$ (16 Temperature levels + 16 Salinity levels) per time step over sequence length $L = 3$ cycles ($t-3, t-2, t-1$).
- **Hidden Dimensions:** 2 layers of Bi-LSTM with 128 hidden units per direction (total 256 dimensions).
- **Dropout Rate:** $p = 0.20$ applied between recurrent layers and before the dense output heads.
- **Output Heads:**
  - Temperature Head: Fully connected layer ($256 \to 16$) with linear activation.
  - Salinity Head: Fully connected layer ($256 \to 16$) with linear activation.

---

## 2. Multi-Objective Physics-Informed Loss Function

To guarantee both predictive numerical accuracy and physical plausibility, the model is trained with:
$$\mathcal{L}_{\text{total}} = \mathcal{L}_{\text{MSE}}(T) + \lambda_{\text{sal}} \mathcal{L}_{\text{MSE}}(S) + \lambda_{\text{phys}} \mathcal{L}_{\text{stability}} + \lambda_{\text{therm}} \mathcal{L}_{\text{thermocline}}$$

Where:
1. $\mathcal{L}_{\text{MSE}}(T) = \frac{1}{16} \sum_{i=1}^{16} (T_i - \hat{T}_i)^2$
2. $\mathcal{L}_{\text{MSE}}(S) = \frac{1}{16} \sum_{i=1}^{16} (S_i - \hat{S}_i)^2$ with $\lambda_{\text{sal}} = 2.5$ (accounting for narrower variance in salinity).
3. **TEOS-10 Gravitational Stability Loss:**
   $$\mathcal{L}_{\text{stability}} = \sum_{i=1}^{15} \max\left(0, - \frac{\hat{\sigma}_\theta(z_{i+1}) - \hat{\sigma}_\theta(z_i)}{z_{i+1} - z_i}\right)$$
   Penalizes any instance where density decreases with depth ($\lambda_{\text{phys}} = 10.0$).
4. **Thermocline Gradient Loss:**
   $$\mathcal{L}_{\text{therm}} = \left| \left(\frac{T_{75} - T_{125}}{50}\right) - \left(\frac{\hat{T}_{75} - \hat{T}_{125}}{50}\right) \right|^2 \quad (\lambda_{\text{therm}} = 1.5)$$

---

## 3. Training & Evaluation Protocol

### Hardware & Compute Prioritization
- **Target Device:** **High-End GPU Prioritized** (`cuda` for NVIDIA GPUs, `mps` for Apple Silicon, with `cpu` strictly as fallback):
  ```python
  import torch
  device = torch.device(
      "cuda" if torch.cuda.is_available() 
      else "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() 
      else "cpu"
  )
  print(f"[FloatChat ML] Using compute device: {device}")
  if device.type == "cuda":
      print(f"[FloatChat ML] GPU Model: {torch.cuda.get_device_name(0)}")
      torch.backends.cudnn.benchmark = True
  ```
- **Mixed Precision:** In GPU mode, training script supports `torch.cuda.amp.autocast()` for acceleration.

### Hyperparameters
- **Optimizer:** AdamW (`lr=1e-3`, `weight_decay=1e-4`).
- **Learning Rate Scheduler:** Cosine Annealing with Warmup (`T_max=100`, `eta_min=1e-6`).
- **Batch Size:** 32 on GPU (16 on CPU fallback).
- **Epochs:** 60–120 (with early stopping patience of 15 epochs on validation RMSE). On GPU, training completes in ~15–30 seconds.
- **Seed:** Fixed seed 42 for reproducibility.

### Acceptance Thresholds ("Good Enough" for Production)
| Metric | Baseline (Persistence $t-1$) | Gradient Boosting | Required Model Performance |
| :--- | :--- | :--- | :--- |
| **Profile Temperature RMSE** | $0.48^\circ\text{C}$ | $0.34^\circ\text{C}$ | **$\le 0.23^\circ\text{C}$** |
| **Thermocline (50–150m) RMSE** | $0.74^\circ\text{C}$ | $0.53^\circ\text{C}$ | **$\le 0.32^\circ\text{C}$** |
| **Profile Salinity RMSE** | $0.11\text{ PSU}$ | $0.075\text{ PSU}$ | **$\le 0.052\text{ PSU}$** |
| **TEOS-10 Inversion Rate** | $0.0\%$ | $1.4\%$ | **$\le 0.05\%$** |

---

## 4. Bayesian Uncertainty Quantification (UQ)
- **Method:** Monte Carlo Dropout (Gal & Ghahramani, 2016).
- **Inference Protocol:** Keep dropout active ($p=0.2$) during evaluation. Run $N = 50$ stochastic forward passes for input sequence $\mathbf{X}$:
  $$\hat{\mathbf{Y}}^{(1)}, \hat{\mathbf{Y}}^{(2)}, \dots, \hat{\mathbf{Y}}^{(N)}$$
- **Summary Statistics:**
  - Mean prediction: $\mu(z) = \frac{1}{N} \sum_{k=1}^N \hat{Y}^{(k)}(z)$
  - Epistemic standard deviation: $\sigma(z) = \sqrt{\frac{1}{N-1} \sum_{k=1}^N (\hat{Y}^{(k)}(z) - \mu(z))^2}$
  - 90% Confidence Interval: $[\mu - 1.645\sigma, \mu + 1.645\sigma]$
  - 95% Confidence Interval: $[\mu - 1.960\sigma, \mu + 1.960\sigma]$
- **Output Schema:** Formatted into `UncertaintyBound[]` in `src/types.ts`.

---

## 5. Explainable AI (XAI) Attribution Pipeline

### 1. Temporal Saliency via Integrated Gradients (Captum)
- **Baseline:** Zero-tensor or climatological seasonal mean profile.
- **Captum Multi-Output Wrapper (MANDATORY PATTERN):**
  The Bi-LSTM model outputs both Temperature and Salinity vectors. Because Captum's `IntegratedGradients` requires a scalar or single tensor output, models MUST be wrapped with `SingleOutputModelWrapper` before calling `.attribute()`:
  ```python
  import torch
  import torch.nn as nn
  from captum.attr import IntegratedGradients

  class SingleOutputModelWrapper(nn.Module):
      """Wraps multi-head LSTM so Captum can attribute gradients to a specific target depth."""
      def __init__(self, base_model: nn.Module, target_variable: str = "temp", target_depth_idx: int = 6):
          super().__init__()
          self.base_model = base_model
          self.target_variable = target_variable # "temp" or "sal"
          self.target_depth_idx = target_depth_idx # default 6 is 100 dbar (thermocline)

      def forward(self, x: torch.Tensor) -> torch.Tensor:
          temp_out, sal_out = self.base_model(x)
          selected = temp_out if self.target_variable == "temp" else sal_out
          # Returns shape (batch_size, 1) target prediction
          return selected[:, self.target_depth_idx:self.target_depth_idx + 1]

  # Usage in XAI Service:
  wrapper = SingleOutputModelWrapper(model, target_variable="temp", target_depth_idx=6)
  ig = IntegratedGradients(wrapper)
  attributions, delta = ig.attribute(input_tensor, baseline_tensor, return_convergence_delta=True)
  # attributions shape: (1, 3, 32) -> aggregate across feature dimensions per cycle
  ```
- **Aggregation:** Saliency weights are summed across feature dimensions for each cycle offset ($t-3, t-2, t-1$) and normalized so $\sum w_i = 1.0$.

### 2. Cross-Depth Saliency Matrix
- Computes how input depths (e.g. surface $20\text{ dbar}$) influence target depths (e.g. thermocline $100\text{ dbar}$). Output structured into `depth_attribution_matrix` in `src/types.ts`.

### 3. Evidence-Link Cosine Provenance
- Computes vector cosine similarity between forecasted temperature curve $\hat{\mathbf{T}}$ and historical candidates $\mathbf{T}_{\text{cand}}$:
  $$\text{sim}_{\text{cos}} = \frac{\hat{\mathbf{T}} \cdot \mathbf{T}_{\text{cand}}}{\|\hat{\mathbf{T}}\| \|\mathbf{T}_{\text{cand}}\|}$$
- Blended with Haversine distance penalty:
  $$\text{Score} = 0.75 \times \text{sim}_{\text{cos}} + 0.25 \times \max\left(0, 1 - \frac{\text{dist}_{\text{km}}}{2000}\right)$$
- Selects the top 3 analogues with strict QC flags (flag 1 or 2).

---

## 6. Model Artifact Format & Serialization
- Saved to directory: `backend/app/ml/artifacts/`
  - `model_weights.pt`: PyTorch model state dictionary.
  - `preprocessor.joblib`: Dictionary containing fitted scalers:
    ```python
    {
      "temp_scaler": StandardScaler(),
      "sal_scaler": StandardScaler(),
      "standard_depths": [5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 700, 1000]
    }
    ```
  - `metadata.json`:
    ```json
    {
      "model_version": "v1.2.0-bilstm-teos10",
      "training_date": "2026-09-21",
      "dataset_hash": "sha256_e49b819f...",
      "validation_rmse_temp": 0.228,
      "validation_rmse_sal": 0.0518
    }
    ```
