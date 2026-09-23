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
