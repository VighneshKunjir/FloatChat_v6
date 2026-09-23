# FloatChat: Product Requirements Document (PRD)

## 1. Project Name & Summary
- **Project Name:** **FloatChat** (Full Title: *FloatChat: Explainable Evidence-Linked Oceanographic Profiling & Forecasting Engine*).
- **Executive Summary:** FloatChat is an oceanographic intelligence platform that predicts vertical temperature and salinity profiles ($0\text{ to }1000\text{ dbar}$) for autonomous Argo floats in the Arabian Sea (Northern Indian Ocean). It combines deep sequence modeling with thermodynamic physics constraints (TEOS-10 potential density), Bayesian Uncertainty Quantification (Monte Carlo Dropout), Explainable AI (Integrated Gradients temporal and depth attribution), and an anti-hallucinatory Evidence-Link protocol connecting forecasts directly to verified Argo GDAC NetCDF archives.

---

## 2. Problem Statement
Autonomous Argo floats drift at subsurface parking depths ($1000\text{ dbar}$) and ascend every 10 days to measure vertical profiles of the upper ocean. Operational oceanographers, climate researchers, and naval meteorologists require accurate 10-day forward forecasts of these vertical profiles to track monsoonal heat content, marine heatwaves, and acoustic sound velocity channels. 

However, existing deep learning models in oceanography suffer from three critical failures:
1. **Physical Implausibility:** Standard neural networks frequently predict density inversions ($\partial\sigma_\theta / \partial z < 0$), violating gravitational stability.
2. **Black-Box Opacity:** Models cannot explain *why* a thermocline shoaled or which historical cycle or depth layer drove the prediction.
3. **LLM Hallucinations:** Conversational AI interfaces generate ungrounded temperature values or fake float metadata when asked oceanographic questions.

FloatChat solves this by binding physics validation, attribution saliency, and NetCDF evidence provenance directly into the prediction and conversational pipeline.

---

## 3. Target User Personas
1. **Dr. Neha Rao (Physical Oceanographer & Climate Modeler):**
   - *Needs:* High-precision temperature and salinity forecasts down to 1000 dbar, mixed-layer depth (MLD) estimates, and verification that profiles do not violate TEOS-10 static stability.
2. **Captain Arjun Mehta (Naval Acoustic / Hydrographic Officer):**
   - *Needs:* Rapid assessment of the subsurface sound channel (thermocline gradient and halocline depth) with clear 95% uncertainty confidence intervals.
3. **Devon Vance (ML Engineer & Geoscientific Researcher):**
   - *Needs:* Transparent model attribution (which historical cycle contributed what percentage of the forecast) and lineage to verified Argo GDAC NetCDF files with QC flag 1 or 2.

---

## 4. Goals and Non-Goals
### Goals:
- Deliver 10-day forward vertical profile forecasts for Temperature ($T$) and Salinity ($S$) across 16 standard pressure levels ($5\text{ to }1000\text{ dbar}$).
- Enforce thermodynamic consistency: calculate Brunt-Väisälä frequency ($N^2$) and flag any density inversions via TEOS-10 formulations.
- Quantify epistemic uncertainty via Monte Carlo Dropout across 50 stochastic inference passes.
- Ground all conversational dialogue in mathematically verified forecast records and analogous NetCDF evidence floats.
- Maintain an interactive, responsive single-screen dashboard with dynamic hover readouts, interactive depth inspection, and hydrographic basin mapping.

### Non-Goals:
- Real-time satellite imagery ingestion (SST/SLA satellite products are treated as auxiliary static or preprocessed features; the system does not poll raw L3/L4 satellite feeds in real time).
- 3D full-ocean hydrodynamic grid simulation (FloatChat is Lagrangian float-following profile prediction, not a replacement for full-basin Eulerian numerical models like MOM6 or HYCOM).
- Commercial weather mobile app UX (this is an academic and operational scientific workbench).

---

## 5. Complete Feature List & Priorities

| Feature Name | Component / View | Description | Priority |
| :--- | :--- | :--- | :--- |
| **Float & Cycle Selection** | `ControlBar.tsx` | Select active float (e.g. WMO 3902114, 2903334, etc.) and cycle number with automated defaults. | **MVP** |
| **Variable View Toggle** | `ControlBar.tsx` | Switch between Temperature view, Salinity view, or dual synchronized curves. | **MVP** |
| **Profile Forecast Chart** | `ProfilePlot.tsx` | SVG/Canvas dual-profile visualization comparing Forecast vs Persistence ($t-1$) vs Gradient Boosting with 95% CI bands. | **MVP** |
| **Live Prediction Readout** | `ProfilePlot.tsx` | Real-time card updating on graph hover: exact $T(z)$, $S(z)$, $\sigma_\theta$, layer name, and 95% CI bounds. | **MVP** |
| **Quick Depth Jump** | `ProfilePlot.tsx` | Pill buttons to quickly set readout focus to 5m, 50m, 100m, 200m, 400m, 700m, or 1000m. | **MVP** |
| **Evidence-Link Protocol** | `EvidenceLinkViewer.tsx` | Integrated below profile graph: lists top 3 analogous GDAC NetCDF citations with cosine similarity, distance, and QC flags. | **MVP** |
| **Conversational FloatChat** | `ChatPanel.tsx` | Grounded oceanographic chat assistant with LaTeX math rendering (`react-markdown`, `katex`), citing verified WMO floats. | **MVP** |
| **Hydrographic Sea Map** | `TrajectoryMap.tsx` | Arabian Sea map showing drift tracks (cycles $t-4$ to $t+1$), bathymetry, SST, salinity cores, and telemetry HUD. | **MVP** |
| **XAI & Physics Diagnostics** | `XaiDiagnostics.tsx` | Visualizes temporal saliency bar charts, depth attribution matrix, Brunt-Väisälä buoyancy profile, and MLD. | **MVP** |
| **Model Benchmarks** | `EvaluationBenchmarks.tsx` | Compares FloatChat LSTM vs Gradient Boosting vs Persistence across RMSE, MAE, and physical violation rates. | **MVP** |
| **User Prediction History** | `backend/app/api/forecast.py` | Persists user-run forecasts and predictions in `forecast_logs` table (`/api/history`). | **Phase 5** |
| **JSON Export Endpoint** | `backend/app/api/forecast.py` | Direct export of forecasted profile as standard JSON (`/api/forecast/{id}/export-json`). CF-compliant NetCDF deferred to future scope. | **Phase 5** |

---

## 6. Step-by-Step User Flows

### Flow 1: Profile Forecasting & Depth Interrogation
1. User loads FloatChat. The header displays active WMO float `#3902114` and target cycle `92` $\to$ predicted cycle `93`.
2. User selects an alternate float (e.g., WMO 2903334) or adjusts the cycle slider in `ControlBar`.
3. System triggers `/api/forecast` and `/api/profiles/{wmoId}`.
4. `ProfilePlot` renders the vertical forecast curves alongside persistence baseline and 95% shaded confidence envelopes.
5. User moves cursor over the graph at 100 dbar:
   - The **Live Prediction Readout** updates immediately to show $T=23.42^\circ\text{C}$ (CI: $22.78^\circ\text{C} - 24.06^\circ\text{C}$), $S=35.91\text{ PSU}$, and $\sigma_\theta=25.14\text{ kg/m}^3$.
   - The system displays ocean layer classification: `Main Thermocline (High Thermal Gradient)`.
6. User scrolls to the bottom of the tab to inspect the **Evidence-Link Protocol** verifying the top 3 GDAC historical profiles matching this water mass.

### Flow 2: Conversational Question Answering with Evidence Verification
1. User clicks the **FloatChat** tab.
2. User clicks a suggested prompt or enters: *"What physical processes explain the predicted thermocline temperature at 100 dbar?"*
3. System posts `{ query, wmoId, cycle }` to `/api/chat`.
4. Backend retrieves the active forecast, constructs the grounded scientific prompt, and invokes Gemini (with automatic offline analytical synthesis fallback).
5. The assistant returns a structured scientific response formatted with LaTeX equations (e.g., $\frac{\partial\sigma_\theta}{\partial z} \ge 0$), citing `[Float 3902114 Cycle 92]` and GDAC NetCDF files.
6. A green badge confirms **Grounding Verified via Evidence-Link Protocol**.

### Flow 3: Trajectory and Hydrographic Spatial Inspection
1. User clicks the **Sea Map** tab.
2. User selects the **Bathymetry & Topography** layer. The map displays the continental shelf, Murray Ridge, and Carlsberg Ridge.
3. User clicks **Play Drift**. The trajectory simulator animates through cycles $t-4, t-3, t-2, t-1, t$, and projects cycle $t+1$.
4. User hovers over the ocean canvas: the bottom HUD displays `Cursor: 14.50°N, 65.20°E | Est. Depth: 4150 m | Central Arabian Basin Abyssal Plain`.

---

## 7. Machine Learning & Explainability Scope

### What is Being Predicted?
- **Dataset Corpus:** 30 operational Arabian Sea / Northern Indian Ocean Argo floats with 4 years of historical profiles (~1,500 total cycles across seasonal monsoons).
- **Target Variables:**
  - Discrete vertical Temperature profile: $\mathbf{T} = [T(z_1), T(z_2), \dots, T(z_{16})] \in \mathbb{R}^{16}$ where $z \in \{5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000\}\text{ dbar}$.
  - Discrete vertical Salinity profile: $\mathbf{S} = [S(z_1), S(z_2), \dots, S(z_{16})] \in \mathbb{R}^{16}$.
- **Horizon:** 10-day forward forecast (the standard operational resurfacing interval of an Argo float).

### What an "Explanation" Means for the User
1. **Temporal Saliency:** What fraction of the prediction was influenced by cycle $t-1$ (10 days ago), cycle $t-2$ (20 days ago), or cycle $t-3$ (30 days ago).
2. **Cross-Depth Coupling:** How surface heat fluxes and wind shear (0–50 dbar) drove changes in the deeper thermocline (75–150 dbar).
3. **Physical Diagnostics:** Verification that the vertical density gradient satisfies $\frac{\partial \sigma_\theta}{\partial z} \ge 0$ with zero gravitational instability violations.
4. **Analogue Provenance:** Concrete evidence citations pointing to identical past water masses with distance, cosine similarity, and NetCDF file names.

### Scientific Disclaimer Displayed in UI
> *"Notice: Forecasts are generated using physics-informed neural sequence models calibrated against historical Argo GDAC observations. Operational marine missions must cross-reference forecasts with official INCOIS / NOAA regional advisories."*

---

## 8. Success Metrics
- **Predictive Accuracy:** Profile RMSE $\le 0.25^\circ\text{C}$ for Temperature and $\le 0.055\text{ PSU}$ for Salinity (outperforming persistence baseline by $\ge 45\%$).
- **Physical Validity:** $0.0\%$ density inversion rate on standard profiles ($\ge 99.8\%$ gravitational stability).
- **Latency:** $\le 350\text{ ms}$ for full inference, uncertainty quantification, and XAI attribution generation.
- **Explainability Grounding:** $100\%$ of chat responses must cite at least one verified WMO float with valid NetCDF lineage.
