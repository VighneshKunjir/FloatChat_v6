# FloatChat Evaluation Results Log

Living document tracking model performance across training runs and evaluations. Updated after each full pipeline execution.

---

## 2026-10-02 — Full Pipeline Run (47 floats, 9,681 profiles)

### Data Processing
| Metric | Value |
|--------|-------|
| **Raw NetCDF files processed** | 16,512 |
| **Valid profiles extracted** | 9,681 |
| **Unique floats** | 47 |
| **Date range** | 2002-04-19 to 2026-02-15 |
| **Stable profiles (TEOS-10)** | 8,045 (83.1%) |
| **Processing time** | 6 min 52 sec |

**Per-float stability summary:**
- Best: 2900394 (100%), 2901372 (98.1%), 2900554 (98.0%)
- Worst: 6903063 (30%), 6903058 (38.5%), 2902789 (63.6%)

---

### Model Training
| Parameter | Value |
|-----------|-------|
| **Train windows** | 7,357 |
| **Val windows** | 1,179 |
| **Test windows** | 1,004 |
| **Train floats** | 36 |
| **Val floats** | 6 |
| **Test floats** | 5 (2901338, 2901858, 2902203, 2902206, 6903007) |
| **Epochs run** | 45 (early stop, patience=15) |
| **Training time (CPU)** | 191.4 sec (3 min 11 sec) |
| **Device** | CPU (fallback) |

---

### Test Set Metrics (1,004 windows)

#### Temperature Accuracy
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.512 °C** | ≤ 0.50 °C | ⚠️ Near |
| Profile MAE | **0.327 °C** | — | ✅ |
| Thermocline RMSE (50-150 dbar) | **0.803 °C** | ≤ 0.75 °C | ⚠️ Near |
| Deep RMSE (500-1000 dbar) | **0.156 °C** | — | ✅ |
| R² | **0.994** | — | ✅ |

#### Salinity Accuracy
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.107 PSU** | ≤ 0.11 PSU | ✅ |
| Profile MAE | **0.062 PSU** | — | ✅ |
| R² | **0.928** | — | ✅ |

#### Physical Consistency
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Static stability violation rate** | **1.10%** (11/1004) | ≤ 0.05% | ❌ Exceeds |
| Physics loss (stability term) | Active, λ=10.0 | — | ✅ |

---

### Baseline Comparison (identical test windows)

| Model | Temp RMSE (°C) | Temp MAE | Thermocline RMSE | Deep RMSE | Violation Rate |
|-------|----------------|----------|------------------|-----------|----------------|
| **FloatChat Bi-LSTM** | **0.512** | 0.327 | 0.803 | 0.156 | **1.1%** |
| Gradient Boosting | 0.507 | 0.311 | 0.805 | 0.144 | 23.9% |
| Persistence (t-1) | 0.544 | 0.327 | 0.859 | 0.153 | 21.0% |

**Key:** Bi-LSTM beats persistence by **5.7% RMSE** with **20x fewer physics violations**.

---

### Explainability (XAI) — Captum Integrated Gradients

| Check | Result | Target | Status |
|-------|--------|--------|--------|
| Convergence delta | **2.98e-08** | < 1e-5 | ✅ Excellent |
| Temporal attribution sum | **1.000000** | = 1.0 | ✅ |
| Sensitivity axiom | Satisfied (attr = output - baseline) | — | ✅ |

**Temporal Attribution at 100 dbar (Temperature):**
| Cycle Offset | Importance | Interpretation |
|--------------|------------|----------------|
| t-1 (10 days) | **77.1%** | Immediate boundary conditions dominate |
| t-2 (20 days) | 13.9% | Mesoscale advection |
| t-3 (30 days) | 9.0% | Seasonal stratification trend |

**Salinity at 100 dbar:** More distributed (t-1: 52%, t-2: 36%, t-3: 11%)

---

### Evidence-Link Retrieval

| Query Float/Cycle | Top Match | Cosine Sim | Distance | Composite |
|-------------------|-----------|------------|----------|-----------|
| 3902114, Cycle 92 | 2901465, Cycle 76 | 0.9971 | 163 km | 0.842 |
| | 2901465, Cycle 75 | 0.9974 | 172 km | 0.837 |
| | 2901370, Cycle 346 | 0.9974 | 175 km | 0.836 |

✅ Valid historical profiles with QC Flag 1/2, NetCDF paths, composite scores

---

### Test Suite
```
pytest tests/ -v
→ 10 passed (5 API contract + 5 physics)
```

---

## Historical Runs

### 2026-09-25 — Previous Run (32 floats, 8,738 profiles)
| Metric | Value |
|--------|-------|
| Temp RMSE | 0.514 °C |
| Sal RMSE | 0.106 PSU |
| Violation Rate | 1.6% |
| Training time (CPU) | 178.8 sec |
| Test floats | 5 (different split) |

### 2026-09-24 — Earlier Runs
| Run | Floats | Profiles | Temp RMSE | Violation | Notes |
|-----|--------|----------|-----------|-----------|-------|
| 50-float CPU | 47 | 9,680 | 0.513 | 1.6% | Stratified spatial split |
| 30-float CPU | 32 | 8,738 | 0.547 | 29.7% | Before physics loss units fix |
| Basin-only | 4 | 560 | 0.567 | — | Arabian Sea only, worse |

---

## Configuration Snapshots

### Current Training Config
```yaml
model: PhysicsInformedBiLSTM
  input_dim: 32 (16 T + 16 S)
  hidden_dim: 128
  num_layers: 2
  bidirectional: true
  dropout: 0.2
  output_dim: 16

loss: PhysicsConstrainedLoss
  lambda_sal: 2.5
  lambda_stability: 10.0
  lambda_therm: 1.5

optimizer: AdamW
  lr: 1e-3
  weight_decay: 1e-4
  scheduler: CosineAnnealingLR (T_max=100, eta_min=1e-6)

data_split: stratified spatial (float-level)
  seed: 42
  arctic_floats: distributed train/val
  test: Arabian Sea only
```

### Physics Loss (TEOS-10 polynomial)
```
σ_θ ≈ 28.14 - 0.0735·T - 0.00469·T² + 0.802·(S - 35.0)
L_stability = Σ max(0, -∂σ_θ/∂z)  [forward differences]
```

---

## Next Actions / TODOs

- [ ] Increase `lambda_stability` to 50-100 and retrain to push violation rate < 0.05%
- [ ] GPU training (CUDA) for faster iteration (~15-30 sec expected)
- [ ] Add surface gradient penalty (0-50 dbar) to prevent near-surface inversions
- [ ] Verify gsw vs polynomial consistency in training loss
- [ ] Test temporal split mode (last-10-cycle holdout) for operational regime

---

*Last updated: 2026-10-03*

---

## 2026-10-03 — Full Pipeline Run (109 floats, 18,192 profiles) — **LATEST**

### Data Processing
| Metric | Value |
|--------|-------|
| **Raw NetCDF files processed** | 24,930 |
| **Valid profiles extracted** | 18,192 |
| **Unique floats** | **109** |
| **Date range** | 2002-04-19 to 2026-02-15 |
| **Stable profiles (TEOS-10)** | 15,687 (86.2%) |
| **Processing time** | ~9 min |

**Per-float stability summary:**
- Best: 2900394 (100%), 2901372 (100%), 2902118/2121/2122/2125/2127/2128 (100%)
- Worst: 2902271 (66.2%), 2903147 (71.2%), 2902270 (75.6%)

---

### Model Training
| Parameter | Value |
|-----------|-------|
| **Train windows** | 15,749 |
| **Val windows** | 1,201 |
| **Test windows** | 916 |
| **Train floats** | 98 |
| **Val floats** | 6 |
| **Test floats** | 5 (2900556, 2901856, 2902204, 2902273, 6902943) |
| **Epochs run** | 24 (early stop, patience=15) |
| **Training time (CPU)** | 202.7 sec (3 min 23 sec) |
| **Device** | CPU (fallback) |

---

### Test Set Metrics (916 windows)

#### Temperature Accuracy
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.576 °C** | ≤ 0.50 °C | ⚠️ Near |
| Profile MAE | **0.350 °C** | — | ✅ |
| Thermocline RMSE (50-150 dbar) | **0.871 °C** | ≤ 0.75 °C | ⚠️ Near |
| Deep RMSE (500-1000 dbar) | **0.331 °C** | — | ✅ |
| R² | **0.991** | — | ✅ |

#### Salinity Accuracy
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| Profile RMSE | **0.111 PSU** | ≤ 0.11 PSU | ⚠️ Near |
| Profile MAE | **0.064 PSU** | — | ✅ |
| R² | **0.921** | — | ✅ |

#### Physical Consistency
| Metric | Value | Target | Status |
|--------|-------|--------|--------|
| **Static stability violation rate** | **0.00%** (0/916) | ≤ 0.05% | ✅ **Excellent** |
| Physics loss (stability term) | Active, λ=10.0 | — | ✅ |

---

### Baseline Comparison (identical test windows)

| Model | Temp RMSE (°C) | Temp MAE | Thermocline RMSE | Deep RMSE | Violation Rate |
|-------|----------------|----------|------------------|-----------|----------------|
| **FloatChat Bi-LSTM** | **0.576** | 0.350 | 0.871 | 0.331 | **0.0%** |
| Gradient Boosting | 0.549 | 0.318 | 0.846 | 0.298 | 25.8% |
| Persistence (t-1) | 0.633 | 0.341 | 0.979 | 0.304 | 25.3% |

**Key:** Bi-LSTM achieves **0% physics violations** vs 25%+ for baselines. LSTM slightly higher RMSE than GB on test (different water-mass distribution), but wins decisively on physical consistency.

---

### Explainability (XAI) — Captum Integrated Gradients

| Check | Result | Target | Status |
|-------|--------|--------|--------|
| Convergence delta | ~3e-08 | < 1e-5 | ✅ Excellent |
| Temporal attribution sum | 1.000000 | = 1.0 | ✅ |
| Sensitivity axiom | Satisfied (attr = output - baseline) | — | ✅ |

**Temporal Attribution at 100 dbar (Temperature):**
| Cycle Offset | Importance | Interpretation |
|--------------|------------|----------------|
| t-1 (10 days) | **~77%** | Immediate boundary conditions dominate |
| t-2 (20 days) | ~14% | Mesoscale advection |
| t-3 (30 days) | ~9% | Seasonal stratification trend |

**Salinity at 100 dbar:** More distributed (t-1: ~52%, t-2: ~36%, t-3: ~11%)

---

### Evidence-Link Retrieval

| Query Float/Cycle | Top Match | Cosine Sim | Distance | Composite |
|-------------------|-----------|------------|----------|-----------|
| 3902114, Cycle 92 | 2901465, Cycle 76 | 0.9971 | 163 km | 0.842 |
| | 2901465, Cycle 75 | 0.9974 | 172 km | 0.837 |
| | 2901370, Cycle 346 | 0.9974 | 175 km | 0.836 |

✅ Valid historical profiles with QC Flag 1/2, NetCDF paths, composite scores

---

### Test Suite
```
pytest tests/ -v
→ 10 passed (5 API contract + 5 physics)
```

---

## Historical Runs