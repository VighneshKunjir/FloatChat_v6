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
- **Curated 34-Float Real NetCDF Ingestion Pipeline (ADR-008):** Bound project data ingestion and model training strictly to the exact 34 downloaded NetCDF float platforms (`6903059`, `6903060`, `6903063`, `6903058`, `2900090`, `2901509`, `6902943`, `6903062`, `2900089`, `2901447`, `2901108`, `2901107`, `6903008`, `2900394`, `6903046`, `2901337`, `2901370`, `2901372`, `2902390`, `6903007`, `2902203`, `2901444`, `2901339`, `2901338`, `2901466`, `2901415`, `2901465`, `2902391`, `2902206`, `2901132`, `1902442`, `2902789`, `2903334`, `3902114`) in `backend/scripts/download_argo.py`, server catalogs, and all context specifications. Output serialized to `argo_34floats_canonical.csv`.
- **NetCDF Upstream Range Pre-Filtering & Split Stratification (RESOLVED-004):** Resolved `[ASSUMPTION-004]` by implementing upstream fill-value sentinel masking ($\ge 9990$, $\le -990$) and pre/post-interpolation physical range verification in `backend/scripts/download_argo.py`. Eliminated training-time row dropping (100% rows kept from canonical CSV). Implemented hydrographic domain stratification partitioning sub-polar (`69030xx`) and Arabian Sea floats across train/val/test splits to stabilize evaluation variance.
- **Phase 6 Gating Invariant:** Enforced strict rule forbidding modifications to working React frontend code until backend Python endpoints and tests are verified green.
- **Export Scope:** Prioritized standard JSON export (`GET /api/forecast/{id}/export-json`) for immediate development; CF-compliant NetCDF export deferred to future scope.
- **KaTeX Asset Delivery:** Added official KaTeX stylesheet to `index.html` ensuring mathematical equations render correctly in all browser contexts.

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
