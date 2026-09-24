# FloatChat: Implementation Tasks & Roadmap

This phased task backlog guides an autonomous CLI agent to build the full Python ML backend, seed the real database, train/serve the Physics-Informed LSTM model, and cleanly wire the React frontend.

---

## Phase 0: Setup, Environment & Repo Initialization
- [x] **TASK-001: Create Backend Directory Structure**
  - *Files:* `backend/app/`, `backend/scripts/`, `backend/tests/`, `backend/requirements.txt`
  - *Description:* Initialize the target Python backend layout conforming to `.ai/architecture.md`.
  - *Acceptance Criteria:* Running `ls -la backend/app` displays `api/`, `core/`, `models/`, `schemas/`, `ml/`, and `db/`.
- [x] **TASK-002: Define Backend Python Dependencies**
  - *Files:* `backend/requirements.txt`
  - *Description:* Specify exact pinned packages: `fastapi`, `uvicorn`, `pydantic`, `sqlalchemy`, `alembic`, `torch`, `gsw`, `netCDF4`, `xarray`, `scikit-learn`, `scipy`, `captum`, `google-genai`.
  - *Acceptance Criteria:* `pip install -r backend/requirements.txt` completes without dependency conflict.
- [x] **TASK-003: Configure Reverse Proxy to Python Backend**
  - *Files:* `server.ts`, `vite.config.ts`
  - *Description:* Configure proxying of `/api/*` routes to FastAPI backend (port 8000) when running the full Python stack. In the AI Studio runtime, `server.ts` can use `http-proxy-middleware` or an environment flag `USE_PYTHON_BACKEND=true` to forward requests to `http://localhost:8000`. For standalone Vite dev, `vite.config.ts` configures `server.proxy` for `/api`.
  - *Acceptance Criteria:* `curl http://localhost:3000/api/health` proxies transparently to FastAPI port 8000 when active.

---

## Phase 1: Database Setup & Argo GDAC Seeding
- [x] **TASK-101: Implement SQLAlchemy 2.0 ORM Models**
  - *Files:* `backend/app/models/schema.py`
  - *Description:* Implement `ArgoFloat`, `ArgoProfile`, `ProfileLevel`, and `ForecastLog` exactly as written in `.ai/database.md`.
  - *Acceptance Criteria:* `python -c "from app.models.schema import ArgoFloat; print(ArgoFloat.__tablename__)"` prints `argo_floats`.
- [x] **TASK-102: Configure Database Engine & Alembic Migrations**
  - *Files:* `backend/app/db/session.py`, `backend/alembic.ini`, `backend/alembic/`
  - *Description:* Configure SQLite default file engine (`sqlite:///./data/floatchat.db`) with fallback to `DATABASE_URL` environment variable.
  - *Acceptance Criteria:* `alembic upgrade head` generates all 4 tables in SQLite.
- [x] **TASK-103: Create Self-Contained Argo Seeding Script**
  - *Files:* `backend/scripts/seed_db.py`, `backend/data/seed_reference_profiles.json`
  - *Description:* Write a script to ingest the self-contained offline dataset (`backend/data/seed_reference_profiles.json`) containing historical profile cycles and standardized 16 depth levels for the 4 operational Arabian Sea reference floats (`3902114`, `2903334`, `1902442`, `2902789`). (Ensures zero network/FTP failures).
  - *Acceptance Criteria:* Running `python backend/scripts/seed_db.py` inserts $>500$ level measurement rows in $<2$ seconds; querying SQLite returns 4 floats.
- [x] **TASK-104: Implement 30-Float Real Data GDAC Ingestion Pipeline**
  - *Files:* `backend/scripts/download_argo.py`, `backend/data/processed/argo_30floats_canonical.csv`
  - *Description:* Create the automated pipeline to fetch NetCDF profiles for 30 operational Arabian Sea floats (4 years history), filter by QC flags (1/2), interpolate to canonical 16-level depth grid (`[5, 20, ..., 1000] dbar`), clean unphysical outliers, and export to canonical wide-format CSV matrix for ML training and database ingestion.
  - *Acceptance Criteria:* Wide-format CSV contains 30 distinct floats, clean 16 standard depths, and passes TEOS-10 static stability validation.

---

## Phase 2: Core Physics Engine & Diagnostic Algorithms
- [x] **TASK-201: Implement TEOS-10 Thermodynamic Calculations with Fallback**
  - *Files:* `backend/app/core/physics.py`
  - *Description:* Implement potential density $\sigma_\theta$, static gravitational stability $\partial\sigma_\theta / \partial z$, Brunt-Väisälä buoyancy frequency $N^2$, and Mixed Layer Depth (MLD) using `gsw.sigma0` with an analytical NumPy polynomial fallback if `gsw` C-extensions are missing.
  - *Acceptance Criteria:* A profile with temperature $[28, 27, \dots, 7]$ and salinity $[36.5, 36.4, \dots, 35.2]$ returns `is_gravitationally_stable = True` and zero stability violations under both `gsw` and fallback mode.
- [x] **TASK-202: Implement Evidence-Link Cosine Provenance Matcher**
  - *Files:* `backend/app/core/evidence.py`
  - *Description:* Implement composite similarity scoring combining vector cosine similarity ($75\%$) and Haversine spatial proximity ($25\%$) against the stored database of profiles.
  - *Acceptance Criteria:* Given float `3902114` cycle `92`, matcher returns top 3 historical citations with QC flag 1/2 and valid NetCDF paths.

---

## Phase 3: Machine Learning Model & Training Pipeline
- [x] **TASK-301: Implement Physics-Informed Bi-LSTM PyTorch Model**
  - *Files:* `backend/app/ml/model.py`
  - *Description:* Define the 2-layer Bi-LSTM with dropout ($p=0.2$) and dual linear projection heads for Temperature and Salinity. Implement automatic GPU (`cuda`/`mps`) device binding.
  - *Acceptance Criteria:* Forward pass on tensor of shape `(32, 3, 32)` outputs two tensors of shape `(32, 16)`.
- [x] **TASK-302: Implement Physics-Constrained Loss Function**
  - *Files:* `backend/app/ml/loss.py`
  - *Description:* Implement composite loss $\mathcal{L} = \text{MSE}(T) + 2.5\,\text{MSE}(S) + 10.0\,\mathcal{L}_{\text{stability}} + 1.5\,\mathcal{L}_{\text{therm}}$ as specified in `.ai/ml_spec.md`.
  - *Acceptance Criteria:* Backpropagation through a deliberate density inversion produces a positive loss penalty $\mathcal{L}_{\text{stability}} > 0$.
- [ ] **TASK-303: Build GPU-Prioritized Training & Artifact Export Script**
  - *Files:* `backend/scripts/train_model.py`
  - *Description:* Train model prioritizing high-end GPU (`cuda`/`mps`) with CPU fallback on Arabian Sea float sequence splits, apply early stopping, and serialize artifacts to `backend/app/ml/artifacts/model_weights.pt` and `preprocessor.joblib`.
  - *Acceptance Criteria (recalibrated per ADR-009):* Test temp RMSE $\le 0.50^\circ\text{C}$ ($\ge 5\%$ better than persistence on identical splits), sal RMSE $\le 0.11\text{ PSU}$, thermocline RMSE $\le 0.75^\circ\text{C}$, inversion rate $\le 1.0\%$; artifacts saved to disk ($<45$ seconds on GPU retained as directional target).
- [x] **TASK-304: Implement Baseline Regressors (Persistence & Gradient Boosting)**
  - *Files:* `backend/scripts/train_baselines.py`, `backend/app/ml/baselines.py`
  - *Description:* Train and benchmark standard Persistence ($t-1$) and Gradient Boosting (`HistGradientBoostingRegressor` or `XGBoost`) models on the same sequence splits. Generate benchmark comparison metrics (`metrics_comparison`) matching `ModelMetric[]` in `src/types.ts`.
  - *Acceptance Criteria:* Persistence and Gradient Boosting evaluation metrics match Table in `.ai/ml_spec.md` and are serialized to `backend/app/ml/artifacts/baseline_metrics.json`.

---

## Phase 4: Uncertainty Quantification & Explainability (XAI)
- [x] **TASK-401: Implement Monte Carlo Dropout UQ Service**
  - *Files:* `backend/app/core/uq.py`
  - *Description:* Execute 50 forward passes with active dropout; calculate mean, standard deviation, 90% CI, and 95% CI per depth level.
  - *Acceptance Criteria:* Returns `UncertaintyBound[]` array where upper CI is strictly greater than mean, and thermocline depth exhibits higher variance than abyssal 1000m.
- [x] **TASK-402: Implement Captum Integrated Gradients Attribution with Target Wrapper**
  - *Files:* `backend/app/ml/xai.py`
  - *Description:* Implement `SingleOutputModelWrapper` and compute path-integrated gradients to quantify temporal weights across $t-3, t-2, t-1$ and cross-depth saliency matrix without multi-output crashes.
  - *Acceptance Criteria:* Sum of temporal attribution importance scores equals $1.00 \pm 0.01$.

---

## Phase 5: FastAPI REST Endpoints & Schemas
- [x] **TASK-500: Implement Health Check Endpoint**
  - *Files:* `backend/app/api/health.py`
  - *Description:* Implement `GET /api/health` returning system status, service identity, and physics engine mode.
  - *Acceptance Criteria:* `curl http://localhost:8000/api/health` returns `200 OK` with JSON `{"status": "ok", "service": "FloatChat-XRAG-Forecasting-Engine"}`.
- [x] **TASK-501: Implement Pydantic Schemas**
  - *Files:* `backend/app/schemas/forecast.py`, `backend/app/schemas/chat.py`
  - *Description:* Write exact Pydantic schemas mirroring `.ai/api_contract.md`.
  - *Acceptance Criteria:* `ForecastResult.model_validate(sample_json)` validates with zero schema errors.
- [x] **TASK-502: Implement Floats & Profiles Endpoints**
  - *Files:* `backend/app/api/floats.py`
  - *Description:* Implement `GET /api/floats` and `GET /api/profiles/{wmoId}` querying SQLAlchemy.
  - *Acceptance Criteria:* `curl http://localhost:8000/api/floats` returns JSON array with all seeded operational floats.
- [x] **TASK-503: Implement Forecasting & Inference Endpoint**
  - *Files:* `backend/app/api/forecast.py`
  - *Description:* Wire preprocessor, PyTorch LSTM inference, MC Dropout UQ, TEOS-10 validator, Captum XAI, and Evidence-Link matcher into `POST /api/forecast`. Persist forecast result into `forecast_logs` table.
  - *Acceptance Criteria:* `POST /api/forecast` returns a complete `ForecastResult` payload in $<350\text{ ms}$ and writes record to `forecast_logs`.
- [x] **TASK-504: Implement Conversational RAG Endpoint**
  - *Files:* `backend/app/api/chat.py`
  - *Description:* Implement `POST /api/chat` with Gemini 2.5/3.8 Flash SDK call and automatic offline analytical synthesis fallback.
  - *Acceptance Criteria:* Submitting a prompt yields grounded oceanographic text citing the active WMO ID and NetCDF files with LaTeX formulas.
- [x] **TASK-505: Implement History Audit & JSON Export Endpoints**
  - *Files:* `backend/app/api/forecast.py`
  - *Description:* Implement `GET /api/history` returning recent forecast logs, and `GET /api/forecast/{id}/export-json` streaming the exact forecast payload as an attachment.
  - *Acceptance Criteria:* `curl http://localhost:8000/api/history` returns logged forecasts; export endpoint sets `Content-Disposition: attachment`.

---

## Phase 6: Frontend Integration & Mock Retirement
*(GATE: Phase 6 MUST NOT begin until all Phase 1–5 backend endpoints pass pytest)*
- [x] **TASK-601: Implement Frontend API Service Layer**
  - *Files:* `src/services/api.ts`
  - *Description:* Create clean, strongly typed API client module matching `.ai/integration_map.md`.
  - *Acceptance Criteria:* `src/services/api.ts` compiles cleanly with `tsc --noEmit`.
- [x] **TASK-602: Wire `App.tsx` and Components to API Service**
  - *Files:* `src/App.tsx`, `src/components/ChatPanel.tsx`
  - *Description:* Replace all direct `fetch()` calls with `apiService.getFloats()`, `apiService.runForecast()`, and `apiService.sendChatMessage()`.
  - *Acceptance Criteria:* The dashboard loads data dynamically over the API proxy without console errors.
- [x] **TASK-603: Deprecate In-Memory Server Mock Files**
  - *Files:* `server/argoData.ts`, `server/forecaster.ts`
  - *Description:* Archive or deprecate the Node mock forecaster in favor of the FastAPI backend.
  - *Acceptance Criteria:* All user actions in the browser are served exclusively by the real Python backend.

---

## Phase 7: Testing, Physics Validation & Benchmark Verification
- [x] **TASK-701: Write Automated Backend Unit & Physics Tests** *(completed early: required by Phase 6 gate)*
  - *Files:* `backend/tests/test_physics.py`, `backend/tests/test_forecast.py`
  - *Description:* Write pytest test suite verifying static stability checks, MLD calculations, and REST endpoint contracts.
  - *Acceptance Criteria:* Running `pytest backend/tests` passes 100% green.
- [x] **TASK-702: Validate Full End-to-End User Experience**
  - *Description:* Step through User Flows 1, 2, and 3 from `.ai/prd.md` in the browser.
  - *Acceptance Criteria:* Dynamic hover readout, quick depth jumps, Evidence-Link viewer, KaTeX equations, and bathymetric map work flawlessly.

---

## Definition of Done (DoD)
A task is marked done (`- [x]`) ONLY when:
1. All referenced files are created or edited according to specifications.
2. The code compiles without errors or warnings (`tsc --noEmit` and `pytest`).
3. Automated or manual curl verification succeeds.
4. `.ai/current_state.md` and `.ai/changelog.md` are updated.
