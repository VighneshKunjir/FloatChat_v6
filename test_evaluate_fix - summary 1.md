# FloatChat Pipeline Audit & Fix Summary

**Date:** 2026-10-02  
**Auditor:** AI Agent (Physical Oceanographer & ML Systems Engineer)

---

## 1. Objective

Audit the FloatChat forecasting and explainability pipeline to verify:
1. Architecture correctness (Bi-LSTM, physics loss, Captum XAI, Evidence-Link)
2. Code execution without errors
3. Physical consistency (TEOS-10 static stability)
4. Prediction accuracy benchmarks
5. Explainability quality (Integrated Gradients convergence, attribution axioms)

---

## 2. System Overview

**FloatChat** is a Physics-Informed Neural Network for forecasting 16-depth vertical profiles of Temperature (T) and Salinity (S) from Argo float trajectories in the Arabian Sea.

**Key Components:**
- **Model:** 2-layer Bi-LSTM (128 hidden units, bidirectional) with dual output heads
- **Physics Loss:** MSE(T) + 2.5·MSE(S) + 10.0·L_stability + 1.5·L_thermocline
- **Static Stability:** ∂σ_θ/∂z ≥ 0 (no density inversions)
- **UQ:** Monte Carlo Dropout (50 passes)
- **XAI:** Captum Integrated Gradients with `SingleOutputModelWrapper`
- **Evidence-Link:** Cosine similarity (75%) + Haversine distance (25%)

---

## 3. Step-by-Step Audit Process

### Step 1: Code Inspection & Verification

**Files Examined:**
- `backend/app/ml/model.py` - Bi-LSTM architecture, `SingleOutputModelWrapper`
- `backend/app/ml/loss.py` - Physics-constrained loss function
- `backend/app/ml/xai.py` - Captum Integrated Gradients implementation
- `backend/app/core/physics.py` - TEOS-10 physics (gsw + fallback)
- `backend/app/core/evidence.py` - Analogue retrieval
- `backend/app/core/uq.py` - MC Dropout uncertainty quantification
- `backend/app/api/forecast.py` - Main inference endpoint

**Findings:**
- `SingleOutputModelWrapper` correctly implemented in both `model.py` and `xai.py`
- Physics loss uses differentiable TEOS-10 polynomial approximation
- Captum integration uses 50 Riemann steps with proper baseline
- Evidence linker uses proper composite scoring

### Step 2: Run Existing Tests

```bash
cd backend && pytest tests/ -v
```

**Initial Result:** 9 passed, 1 failed
- **Failure:** `test_forecast_contract_schema` - `FileNotFoundError` for preprocessor.joblib

### Step 3: Fix Forecast Endpoint Path Issues

**Problem:** `forecast.py` had multiple `joblib.load("backend/app/ml/artifacts/preprocessor.joblib")` calls with relative paths that failed in test context.

**Fix Applied:**
- Removed duplicate preprocessor loading calls
- Use global `preprocessor` variable loaded at startup via `load_model_and_preprocessor()`
- Fixed `global` declaration syntax errors (removed unnecessary `global` statements)

**Files Modified:** `backend/app/api/forecast.py` (lines 179, 219, 247-250)

### Step 4: Re-run Tests

```bash
cd backend && pytest tests/ -v
```

**Result:** 10 passed ✅

### Step 5: Physics Validation Bug Discovery

**Issue:** `compute_static_stability()` used `np.gradient()` (central differences) while the physics loss used forward differences `(σ[i+1]-σ[i])/(z[i+1]-z[i])`.

**Impact:** Density inversions were MASKED in validation (central differences smooth over sharp changes).

**Example:** A profile with σ = [..., 23.87, 23.65, ...] at 100→150 dbar showed:
- Forward diff: -0.2127 (VIOLATION)
- Central diff (np.gradient): +0.006 (no violation detected)

**Fix Applied:** Changed `compute_static_stability()` in `backend/app/core/physics.py` to use forward differences matching the training loss exactly.

### Step 6: Comprehensive Model Evaluation

Created evaluation scripts to benchmark on test set (5 unseen floats, 1003 windows).

**Evaluation Scripts Created:**
- `backend/eval_model.py` - Full accuracy + physics metrics
- `backend/eval_xai.py` - XAI attribution quality

---

## 4. Results Summary

### 4.1 Temperature Accuracy (Test Set)

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.513 °C** | ≤ 0.50 °C | ⚠️ Near |
| Profile MAE | **0.327 °C** | - | ✅ |
| Thermocline RMSE (50-150 dbar) | **0.804 °C** | ≤ 0.75 °C | ⚠️ Near |
| Deep RMSE (500-1000 dbar) | **0.156 °C** | - | ✅ |
| R² | **0.994** | - | ✅ |

### 4.2 Salinity Accuracy

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.107 PSU** | ≤ 0.11 PSU | ✅ |
| Profile MAE | **0.062 PSU** | - | ✅ |
| R² | **0.928** | - | ✅ |

### 4.3 Physical Consistency

| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Violation Rate** | **1.10%** (11/1003) | ≤ 0.05% | ❌ **Exceeds** |

> **Note:** Physics loss reduces violations from 21-23% (baselines) to ~1%, but strict 0.05% target not met.

### 4.4 Baseline Comparison

| Model | Temp RMSE (°C) | Violation Rate |
|-------|----------------|----------------|
| **FloatChat Bi-LSTM** | **0.513** | **1.10%** |
| Persistence (t-1) | 0.544 | 21.0% |
| Gradient Boosting | 0.500 | 22.9% |

✅ Bi-LSTM beats persistence by **5.7%** on RMSE with **20x fewer violations**

### 4.5 Explainability (XAI) Quality

| Check | Result | Target | Status |
|-------|--------|--------|--------|
| Convergence Delta | **2.98e-08** | < 1e-5 | ✅ |
| Temporal Attribution Sum | **1.000000** | = 1.0 | ✅ |
| Sensitivity Axiom | Satisfied | output = baseline + attribution | ✅ |

**Temporal Attribution at 100 dbar (Temperature):**
- t-1 (10 days): **77.1%** — dominates (immediate boundary conditions)
- t-2 (20 days): 13.9% — mesoscale advection
- t-3 (30 days): 9.0% — seasonal trend

**Salinity at 100 dbar:** More distributed (t-1: 52%, t-2: 36%, t-3: 11%)

### 4.6 Evidence-Link Retrieval

| Query | Top Match | Cosine | Distance | Composite |
|-------|-----------|--------|----------|-----------|
| 3902114, Cycle 92 | 2901465, Cycle 76 | 0.9971 | 163 km | 0.842 |
| | 2901465, Cycle 75 | 0.9974 | 172 km | 0.837 |
| | 2901370, Cycle 346 | 0.9974 | 175 km | 0.836 |

✅ Valid historical profiles with QC flags, NetCDF paths, composite scores

---

## 5. Files Modified

| File | Changes |
|------|---------|
| `backend/app/api/forecast.py` | Fixed preprocessor loading paths; removed duplicate loads; fixed `global` syntax |
| `backend/app/core/physics.py` | Changed `compute_static_stability()` from `np.gradient` to forward differences to match training loss |

---

## 6. Recommendations for Further Improvement

1. **Increase physics loss weight** - Retrain with `lambda_stability=50-100` to push violation rate below 0.05%
2. **GPU training** - Current test environment CPU-only; GPU would enable faster iteration
3. **Verify gsw vs polynomial consistency** - Ensure training loss polynomial matches gsw density values
4. **Surface gradient penalty** - Add explicit penalty for 0-50 dbar inversions

---

## 7. Test Suite Final Status

```
Pytest: 10 passed
├── test_health_endpoint ✅
├── test_floats_catalog_endpoint ✅  
├── test_profiles_endpoint ✅
├── test_forecast_contract_schema ✅
├── test_chat_endpoint_grounded ✅
└── test_physics (5 tests) ✅
```

All API contracts, physics validations, and integration tests pass.