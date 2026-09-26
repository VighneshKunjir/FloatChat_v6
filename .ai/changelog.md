# FloatChat: Project Changelog

All notable technical and architectural updates to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased] - Planned for Local CLI Agent Migration
### Added
- Comprehensive `.ai/` AI Context Pack specification files (PRD, Architecture, Rules, Design, Data Spec, ML Spec, API Contract, Database, Integration Map, Tasks, Testing, Setup, Current State, Memory).
- Target directory layout for Python FastAPI ML backend (`backend/app/`).
- SQLAlchemy 2.0 ORM schemas for `argo_floats`, `argo_profiles`, `profile_levels`, and `forecast_logs`.
- Python scientific dependencies manifest in `backend/requirements.txt`.
- Initial embedded offline reference dataset schema in `backend/data/seed_reference_profiles.json`.

### Resolved Decisions & Architectural Directives
- **Hardware Priority:** Formally prioritized high-end GPU training (`cuda`) with Apple Silicon (`mps`) and `cpu` fallback in `.ai/ml_spec.md` and `.ai/rules.md` (ADR-004).
- **Offline Seeding Strategy:** Decoupled local development database seeding from remote GDAC FTP mirrors by adopting the self-contained reference dataset `seed_reference_profiles.json` with 35 cycles and 560 level measurements across the 4 operational floats (ADR-005).
- **Captum Multi-Output Wrapper:** Documented and mandated `SingleOutputModelWrapper` in `.ai/ml_spec.md` and `.ai/rules.md` to prevent Captum crashes on multi-head Bi-LSTM outputs (ADR-006).
- **Dual-Runtime & Request Alias Handling:** Added ADR-007 requiring Pydantic request models with `populate_by_name=True` and aliases (`wmoId`/`wmo_id`, `cycle`/`cycle_number`) to prevent 422 errors when bridging React frontend with FastAPI backend.
- **Depth Discretization Grid Unification:** Unified canonical 16-level standard depths (`[5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000]`) across all `.ai/` specifications and the offline dataset.
- **30-Float Real Data Pipeline (ADR-008):** Designed end-to-end ingestion and preprocessing in `backend/scripts/download_argo.py` scaling model training to 30 operational floats over 4 years with QC 1/2 filtering and wide CSV output (`argo_30floats_canonical.csv`).
- **Phase 6 Gating Invariant:** Enforced strict rule forbidding modifications to working React frontend code until backend Python endpoints and tests are verified green.
- **Export Scope:** Prioritized standard JSON export (`GET /api/forecast/{id}/export-json`) for immediate development; CF-compliant NetCDF export deferred to future scope.
- **KaTeX Asset Delivery:** Added official KaTeX stylesheet to `index.html` ensuring mathematical equations render correctly in all browser contexts.

---

## [Phase 0 Complete] - 2026-09-23
### Added
- **Backend Directory Structure**: Created `backend/app/{api,core,models,schemas,ml,db}` with `ml/artifacts`, `db/alembic`, `scripts`, `tests`, `data/{raw,processed}`.
- **Python Dependencies**: `backend/requirements.txt` with FastAPI, SQLAlchemy, PyTorch, gsw, Captum, and all scientific ML packages.
- **Reverse Proxy Configuration**: 
  - `vite.config.ts`: Added `server.proxy` for `/api/*` → `http://localhost:8000`
  - `server.ts`: Added `USE_PYTHON_BACKEND` env flag with `http-proxy-middleware` to forward `/api/*` to FastAPI
- **Node Dependency**: Installed `http-proxy-middleware@^3.0.3`

### Changed
- Updated `package.json` with `http-proxy-middleware` dependency.

### Verified
- `pip install -r backend/requirements.txt` completes successfully (all packages installed).
- `tsc --noEmit` passes with zero TypeScript errors.
- `seed_reference_profiles.json` exists with 4 floats, 35 cycles, 16 standard pressure levels.

---
 
## [Phase 1 Complete] - 2026-09-24
### Added
- **Argo NetCDF Processing Pipeline** (`backend/scripts/process_argo_netcdf.py`): Processes 11,801 raw NetCDF files from 32 floats into canonical CSV.
- **Canonical Training Dataset** (`backend/data/processed/argo_30floats_canonical.csv`): 8,738 profiles × 59 columns (metadata + 16 T + 16 S + 16 σ_θ).
- **TEOS-10 Physics Computation**: σ_θ, static stability (∂σ_θ/∂z), Brunt-Väisälä N², MLD per profile.
- **QC Filtering**: Delayed-mode only, QC flags 1/2, vertical interpolation (PCHIP) to 16 standard depths.

### Verified
- `python backend/scripts/process_argo_netcdf.py` completes in ~3 minutes
- Output: 8,738 profiles, 32 unique floats, date range 2002-2026
- 62.4% profiles pass TEOS-10 static stability (∂σ_θ/∂z ≥ 0)
- All 16 standard depth levels populated (5-1000 dbar)

---
 
## [TASK-201 Complete] - 2026-09-24
### Added
- **TEOS-10 Physics Engine** (`backend/app/core/physics.py`): Potential density σ_θ, static stability ∂σ_θ/∂z, Brunt-Väisälä N², MLD, thermocline gradient.
- **Dual-engine support**: `gsw` (TEOS-10) with NumPy polynomial fallback when C-extensions unavailable.
- **Validation function**: `validate_profile_physics()` returns full physics dict with stability flags.

### Verified
- `python -m app.core.physics` → Engine: gsw, Is stable: True, Violations: 0
- Fallback mode test → Engine: fallback, Is stable: True, Violations: 0
- Acceptance criteria profile (T=[28..7], S=[36.5..35.2]) passes with zero violations

---
 
## [TASK-401 Complete] - 2026-09-24
### Added
- **MC Dropout UQ Service** (`backend/app/core/uq.py`): 50 stochastic forward passes with active dropout, mean/std/90% CI/95% CI per 16 depth levels.
- **Validation utilities**: `validate_uncertainty_bounds()` checks upper CI > mean, thermocline variance > abyssal.
- **JSON serializer**: `uncertainty_bounds_to_dict()` for API responses.

### Verified
- 50 MC passes on CPU complete in ~3s; 16 UncertaintyBound entries with CI bounds.
- Upper CI > mean for both T/S at all depths.
- Output matches `UncertaintyBound` schema from `src/types.ts`.

---
 
## [TASK-304 Complete] - 2026-09-24
### Added
- **Baselines module** (`backend/app/ml/baselines.py`): persistence (t-1), per-depth GB via `MultiOutputRegressor` (parallel), shared `profile_metrics()` emitting the exact `metrics_comparison` schema.
- **Baseline runner** (`backend/scripts/train_baselines.py`): identical test windows to training (seed 42), LSTM row re-evaluated from saved artifacts.
- **`baseline_metrics.json`**: 3 measured rows (persistence 0.544/21.1%, GB 0.507/23.9%, LSTM 0.5141/0.30%).

### Verified
- All rows computed on identical 1,003 test windows (5 test floats); LSTM row matches `metadata.json` (0.5141).
- Qualitative pattern matches spec table (GB wins RMSE, LSTM wins physics + thermocline); absolute values differ — shipped measured per Data Authenticity rule ([RESOLVED-005]).

---

## [TASK-402 Complete] - 2026-09-24
### Added
- **Captum Integrated Gradients XAI** (`backend/app/ml/xai.py`): `SingleOutputModelWrapper` for multi-head Bi-LSTM, path-integrated gradients for temporal/depth attribution.
- **Temporal attribution**: Sums to 1.00 ± 0.01 (t-1 dominates at ~77% for thermocline).
- **Depth attribution matrix**: 16×16 cross-depth saliency matrix.
- **Key depth influences**: Thermocline driven by t-1 cycle (~77%).
- **Convergence delta**: ~6e-8 (well within tolerance).

### Verified
- Temporal attribution sums to 1.000 ± 0.01 (verified: 1.00000005).
- Depth matrix: 256 entries (16×16 cross-depth saliency).
- Key influences: Thermocline attribution 76.8% from t-1 cycle.
- Convergence delta: 5.96e-8 (well within tolerance).
- All outputs JSON-serializable.

---
 
## [Setup Orchestrator + Future Log] - 2026-09-26
### Added
- **One-command setup** (`setup.py`): `--profile full|serve`, `--only/--skip`, `--force[-download|-process|-train]`, `--floats/--floats-file/--discover --years --min-cycles --top-n`, `--check` doctor mode, and serve mode (uvicorn + `npm run dev` with log prefixes, health gates, Ctrl+C cleanup). Heavy stages skip-if-fresh.
- **Custom-volume chain**: discovery accepts `--years/--min-cycles`; downloader accepts `--floats-file` (discovery output or `WMO,DAC[,NAME]`).
- **`future_improvents.md`**: living log of user-proposed future work (custom data volume, frontend Gemini-key input).

### Verified
- `setup.py --check` reports true state; freshness helper fixed for file paths (`rglob` yields nothing on files).

---

## [TASK-603 & Phase 6 Complete] - 2026-09-25
### Changed
- **Node Server Proxying Enabled by Default** (`server.ts`): Set `USE_PYTHON_BACKEND` default to `true`. Mounted proxy before `express.json()` to preserve raw body streaming to FastAPI backend on port 8000.
- **Legacy Mock Files Deprecated** (`server/argoData.ts`, `server/forecaster.ts`, `server/geminiService.ts`): Added `@deprecated` JSDoc annotations. All active user requests in the browser now route directly through the Python FastAPI ML backend.

### Verified
- `npm run lint` (`tsc --noEmit`) → 0 errors.
- `npm run build` → Production bundle built cleanly.
- `http://localhost:3000/api/health`, `/api/floats`, `/api/forecast`, `/api/chat` proxy transparently to FastAPI backend.

---

## [TASK-702 Complete] - 2026-09-25
### Added
- **Full End-to-End Browser Validation**: Validated all User Flows 1, 2, and 3 using Playwright subagent.
- Verified dynamic depth hover readout card, quick depth jump pills, Evidence-Link GDAC citations, KaTeX LaTeX math equations, interactive bathymetric sea map with drift playback, and XAI saliency diagnostics.
- Zero runtime errors or unhandled exceptions across all 5 navigation tabs.

---

## [TASK-602 Complete] - 2026-09-24
### Changed
- **Frontend wired to API service**: `App.tsx` (floats, forecast, profiles) and `ChatPanel.tsx` (chat) now use `apiService`; zero direct `fetch()` outside `src/services/api.ts` (verified by grep).

### Verified
- `tsc --noEmit` → zero errors.
- Backend endpoints proven via `TestClient`; `/api` → `:8000` proxy block confirmed in `vite.config.ts`.
- Browser console check deferred to user / TASK-702 (no browser in sandbox).

---

## [Phase 6 Gate + TASK-601] - 2026-09-24
### Added
- **Backend pytest suite** (`backend/tests/`, gate requirement): `test_physics.py` (5 tests: surface density, stability, inversion, MLD, acceptance profile) + `test_api_contract.py` (5 tests: health, floats, profiles, forecast schema, chat). `conftest.py` fixes `app.*` imports from repo root.
- **Frontend API service** (`src/services/api.ts`): typed `apiService` (health, floats, profiles, forecast, chat) per `integration_map.md`.

### Verified
- `pytest backend/tests/ -v` → 10 passed (gate satisfied; TASK-701 closed early).
- `tsc --noEmit` → zero errors with new service layer.

---

## [Phase 5 Complete] - 2026-09-24
### Added
- **FastAPI REST Endpoints** (`backend/app/api/`): All 5 core endpoints implemented and tested.
  - `GET /api/health` - Service health check
  - `GET /api/floats` - Float catalog with cycles
  - `GET /api/profiles/{wmoId}` - Historical profiles for a float
  - `POST /api/forecast` - Full forecast with UQ, TEOS-10, XAI, Evidence-Link
  - `POST /api/chat` - Grounded conversational RAG with offline fallback
- **Pydantic Schemas** (`backend/app/schemas/`): Complete API contract schemas matching `api_contract.md`.
- **Database Integration**: SQLAlchemy queries replace in-memory mocks for floats/profiles.
- **ML Pipeline Integration**: Preprocessor, model, UQ, XAI, evidence linker all wired into forecast endpoint.

### Verified
- All 5 endpoints return 200 OK with correct JSON schemas.
- Float catalog: 4 floats returned.
- Profiles: 11 historical profiles for float 3902114.
- Forecast: 16 depth levels with uncertainty bounds.
- Chat: Grounded response with citations and verified=true.

---
 
## [Modeling Iteration + Target Recalibration] - 2026-09-24
### Fixed
- **Physics-loss units bug** (`backend/app/ml/loss.py`): TEOS-10 polynomial now denormalizes predictions to physical units first (it previously ran on standardized values) — inversions 36.5% → 0.225%, RMSE flat.
- **Temporal-split diagnostic** (`--split-mode temporal`): last-10-cycle holdout scores 1.03 C (worse) — recent cycles are harder; spatial protocol retained as primary.

### Changed
- **Recalibrated acceptance targets** (ADR-009, user-directed): temp ≤0.50 C (≥5% over persistence), sal ≤0.11 PSU, thermocline ≤0.75 C, inversions ≤1.0%. `ml_spec.md` table + TASK-303 updated; 0.23 C kept as stretch goal.
- **Serving artifact**: LR 3e-4 run (test 0.5141 C / sal 0.1062 / therm 0.7939 / inv 0.299%).

### Experiment record
- E1 basin-only: 0.5668 (worse — diversity helps). E2 LR sweep: 1e-3 → 0.5127, 3e-4 → 0.5141/inv 0.30%, 3e-3 → 0.5225. RMSE flat across LR; physics best at low LR.

---

## [50-Float Scaling + Retrain] - 2026-09-24
### Added
- **16 tier-2 floats** (global-index ranks 31-46, verified DACs) downloaded to `backend/data/raw` → 50 floats / 16,511 NetCDF files. Downloader supports comma-separated `--float` and extended `TARGET_FLOATS`.
- **Regenerated clean CSV**: 9,680 profiles × 47 floats (2901431/2901447/2901466 excluded — fleet-wide PSAL_QC=4 salinity failure, correctly dropped per QC 1/2 rule), 100% in-bounds, 83.1% stable.

### Verified
- Retrain (CPU, 178s, 7,357 train windows, early stop ep 45): test temp 0.5127 C, sal 0.1065 PSU, therm 0.8035 C, inversions 1.6%; val stable at 0.64-0.72.
- Persistence on identical splits: temp 0.5440 C — model beats persistence on all metrics (+6% temp, +11% sal). TASK-303 target (≤0.23 C) still open.

---

## [Processor Hardening + Stratified Retrain] - 2026-09-24
### Fixed
- **Upstream cleaning** (`backend/scripts/process_argo_netcdf.py`): fill-sentinel masking pre-interpolation, hard physical bounds per measurement, cycle discard on any out-of-bounds/NaN interpolated level, stability flagged not dropped.
- **Stratified domain-aware splits** (`backend/scripts/train_model.py`): Arctic 69030xx distributed across train/val, all-Arabian test, seed 42, recorded in `metadata.json`.
- **Regenerated canonical CSV** (old file deleted): 6,256 profiles × 32 floats, 100% train-time retention (was 6,256/8,738). Arctic counts corrected (e.g. 6903058: 500 → 13) — prior counts were sentinel-contaminated.

### Verified
- Retrain (CPU, 52s, early stop ep 21): test temp 0.5467 C, sal 0.1193 PSU, therm 0.7854 C, inversions 29.7%.
- Persistence on identical splits: temp 0.5386 C — model at parity, TASK-303 target (≤0.23 C) still open.

---

## [TASK-302 Complete] - 2026-09-24
### Added
- **Physics-Constrained Loss** (`backend/app/ml/loss.py`): Composite loss with MSE(T) + 2.5*MSE(S) + 10.0*L_stability + 1.5*L_therm.
- **Stability penalty**: Differentiable ∂σ_θ/∂z computation penalizing density inversions.
- **Thermocline loss**: Gradient matching at 75-150 dbar.
- **Differentiable TEOS-10**: Polynomial σ_θ approximation for backprop.

### Verified
- Normal profile stability loss: 0.0
- Inverted profile stability loss: 0.005202 (>0, correctly penalized)
- `loss.backward()` on inverted profile yields finite non-zero temp gradients (grad norm 0.040026)
- Loss components dict returned for logging

---
 
## [TASK-301 Complete] - 2026-09-24
### Added
- **Physics-Informed Bi-LSTM** (`backend/app/ml/model.py`): 2-layer Bi-LSTM (128 hidden, bidirectional) with dual heads.
- **Automatic device binding**: cuda > mps > cpu priority.
- **SingleOutputModelWrapper**: For Captum Integrated Gradients attribution.
- **569K parameters**, forward pass (32, 3, 32) → (32, 16) × 2.

### Verified
- `python -m app.ml.model` → Input (32, 3, 32), Temp/Sal outputs (32, 16)
- Device auto-selection: CUDA > MPS > CPU
- Wrapper extracts single scalar for Captum

---
 
## [TASK-202 Complete] - 2026-09-24
### Added
- **Evidence-Link Matcher** (`backend/app/core/evidence.py`): Cosine similarity (75%) + Haversine spatial (25%) composite scoring.
- **Database integration**: Queries seeded profiles, filters by QC flag 1/2.
- **Citation formatter**: Returns structured evidence with NetCDF paths, QC status, similarity scores.

### Verified
- `get_evidence_links('3902114', 92, db, 3)` → 3 citations with QC_PASS_FLAG_1
- Citations include: profile_id, wmo_id, cycle, date, distance_km, cosine/spatial/composite scores
- NetCDF paths: `raw_netcdf_source` (nodc_D2903334_120.nc) and `gdac_archive_path` (/ifremer/argo/dac/incois/...)
- Composite scoring: 0.75 × cosine + 0.25 × spatial (exponential decay)

---
 
## [Phase 1 Complete] - 2026-09-23
### Added
- **SQLAlchemy 2.0 ORM Models** (`backend/app/models/schema.py`): `ArgoFloat`, `ArgoProfile`, `ProfileLevel`, `ForecastLog` with proper relationships, constraints, and indexes matching `.ai/database.md`.
- **Database Engine & Session** (`backend/app/db/session.py`): SQLite default with `DATABASE_URL` override, `SessionLocal`, `init_db()`, context managers.
- **Alembic Migrations** (`backend/alembic/`): Configured with `script_location = alembic`, auto-generated initial migration, `alembic upgrade head` creates all 4 tables + `alembic_version`.
- **Self-Contained Seeding Script** (`backend/scripts/seed_db.py`): Ingests `backend/data/seed_reference_profiles.json` (4 floats, 35 profiles, 560 levels) in <2 seconds, idempotent with existence checks.

### Verified
- `python -c "from app.models.schema import ArgoFloat; print(ArgoFloat.__tablename__)"` → `argo_floats`
- `alembic upgrade head` → Creates `argo_floats`, `argo_profiles`, `profile_levels`, `forecast_logs`, `alembic_version`
- `python backend/scripts/seed_db.py` → 4 floats, 35 profiles, 560 levels inserted
- Database file at `backend/data/floatchat.db`

---

## [1.2.0] - 2026-09-21 (AI Studio Initial Build & UI Maturation)
### Added
- **Live Prediction Readout Box:** Real-time on-screen numerical readout in `ProfilePlot.tsx` updating on graph hover with exact Temperature (°C), Salinity (PSU), Potential Density ($\sigma_\theta$), and 95% Confidence Intervals.
- **Quick Depth Jump Pills:** Added instant click selectors (`5m`, `50m`, `100m`, `200m`, `400m`, `700m`, `1000m`) for rapid layer inspection.
- **Evidence-Link Protocol Merge:** Integrated GDAC NetCDF citations directly into the bottom of the Profile Forecast tab below the target profile banner.
- **Hydrographic Sea Map Upgrades:** Added realistic bathymetry, SST, and Haline salinity cores, multi-cycle drift playback controls, distance range rings (150–450 km), and real-time cursor telemetry HUD.
- **Conversational FloatChat with LaTeX:** Fully grounded scientific assistant with KaTeX equation rendering and offline fallback synthesis.
- **XAI & TEOS-10 Diagnostics:** Temporal lag saliency bar charts, cross-depth attribution matrix, and Brunt-Väisälä buoyancy profile.

### Changed
- Re-sequenced navigation tabs to:
  1. Profile Forecast & UQ
  2. FloatChat
  3. Sea Map
  4. XAI & TEOS-10 Physics
  5. Model Benchmarks
- Removed redundant "Arabian" wording from tab titles.
- Unified Evidence-Link protocol viewer inside the forecast workspace.

---

## [UI Bugfix Hardening] - 2026-09-25
### Fixed
- **Float catalog completeness** (`backend/app/api/floats.py`): `/api/floats` now returns all 47 seeded floats in stable WMO order (verified live). The "only 4 floats" symptom occurs when the UI talks to a backend seeded with only `seed_db.py` (4 reference floats) — canonical full seeding is `backend/scripts/seed_all_floats.py` (idempotent; DB holds 47 floats / 9,687 profiles).
- **Early-cycle forecast 400** (`backend/app/api/forecast.py`, `src/components/ControlBar.tsx`, `src/services/api.ts`): backend 400 now names the offending cycle, its position, and the earliest forecastable cycle; cycle dropdown hides the first 3 non-forecastable cycles (`slice(3)`); `apiService` surfaces the backend `detail` string instead of bare "Bad Request".
- **Blank evidence inspection modal** (`backend/app/api/forecast.py`, `backend/app/core/evidence.py`, `src/components/EvidenceLinkViewer.tsx`, `src/types.ts`): citations now include `provenance_chain` + 16 hydrated `measurements` + real lat/lon (previously `measurements: []`, no `provenance_chain`, lat/lon dropped by formatter); modal uses optional chaining with empty-state fallback.
- **Repetitive chat answers** (`backend/app/api/chat.py`): offline synthesis now reads real observed levels from the DB and routes to 8 grounded intents (thermocline, salinity, TEOS-10 stability with LaTeX, UQ, XAI, evidence provenance, MLD, explicit-depth queries) plus a DB-backed default; Gemini attempted first when `GEMINI_API_KEY` is set, offline fallback otherwise. Fixed invalid `return {...}, 400` tuple → `HTTPException(400)`.
- **Run Forecast feedback** (`src/App.tsx`, `src/components/ControlBar.tsx`): successful recompute stamps an "Updated HH:MM:SS" chip (button already spinners via `isLoading`); float dropdown label shows live float count.

### Verified
- `pytest backend/tests` → 10 passed; `tsc --noEmit` → 0 errors.
- Live `TestClient`: cycle 1 → 400 with actionable message; cycle 92 → citation has `provenance_chain` + 16 measurements + real lat/lon; 8 sample chat queries → 8 distinct grounded answers (after stem fix for "stable").

---

## Template for Future Changelog Entries
```markdown
## [X.Y.Z] - YYYY-MM-DD
### Added
- New features or endpoints added.
### Changed
- Changes in existing functionality.
### Fixed
- Bug fixes or resolved issues.
### Removed
- Deprecated or retired code.
```
