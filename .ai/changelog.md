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
- **Hardware Priority:** Formally prioritized high-end GPU training (`cuda`) with Apple Silicon (`mps`) and `cpu` fallback in `.ai/ml_spec.md` and `.ai/rules.md`.
- **Offline Seeding Strategy:** Decoupled local development database seeding from remote GDAC FTP mirrors by adopting the self-contained reference dataset `seed_reference_profiles.json` (< 2 second ingestion).
- **Captum Multi-Output Wrapper:** Documented and mandated `SingleOutputModelWrapper` in `.ai/ml_spec.md` and `.ai/rules.md` to prevent Captum crashes on multi-head Bi-LSTM outputs.
- **Phase 6 Gating Invariant:** Enforced strict rule forbidding modifications to working React frontend code until backend Python endpoints and tests are verified green.
- **Export Scope:** Prioritized standard JSON export (`GET /api/forecast/{id}/export-json`) for immediate development; CF-compliant NetCDF export deferred to future scope.

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
