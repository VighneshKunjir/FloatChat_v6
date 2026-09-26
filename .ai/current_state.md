# FloatChat: Current System State

*Last updated: 2026-09-25*

---

## 1. Executive Snapshot
FloatChat operates as an end-to-end, fully functional React 19 + TypeScript single-page application integrated with a high-performance Python FastAPI ML service, backed by SQLite (`backend/data/floatchat.db`), a trained PyTorch Bi-LSTM neural model with Monte Carlo Dropout uncertainty quantification (UQ), TEOS-10 potential density validation (`gsw`), Captum Integrated Gradients XAI attribution, and Evidence-Link NetCDF provenance matching.

**Phase 0-5 Complete**: Python FastAPI backend fully implemented with all REST endpoints (`/api/health`, `/api/floats`, `/api/profiles/{wmoId}`, `/api/forecast`, `/api/chat`, `/api/history`, `/api/forecast/{id}/export-json`).

**Phase 6 Complete**: Frontend API service layer (`src/services/api.ts`) is fully wired to `App.tsx` and all React UI components. All browser requests are routed directly to the Python FastAPI backend via transparent reverse proxy. Legacy Node mock files (`server/argoData.ts`, `server/forecaster.ts`, `server/geminiService.ts`) are formally deprecated with `@deprecated` notices.

**Phase 7 Complete**: Automated backend pytest suite (10/10 green) and full end-to-end browser testing with Playwright validated all 3 PRD user flows: dynamic depth hover readout, quick depth jumps, Evidence-Link viewer, LaTeX conversational AI dialogue, interactive bathymetric sea map, XAI saliency matrix, and evaluation benchmarks.

---

## 2. Status by Functional Module

| Module / Feature | Code Location | Status | Implementation Details |
| :--- | :--- | :---: | :--- |
| **Top Navigation & Tabs** | `src/components/Header.tsx` | **DONE** | Clean 5-tab sequence: Forecast & UQ $\to$ FloatChat $\to$ Sea Map $\to$ XAI $\to$ Benchmarks. Removed "Arabian" from tab labels. |
| **Control Bar** | `src/components/ControlBar.tsx` | **DONE** | WMO dropdown, cycle selector, variable mode toggle (`both`, `temperature`, `salinity`), GPS readout chip, and refresh button. |
| **Profile Forecast Chart** | `src/components/ProfilePlot.tsx` | **DONE** | Dual SVG vertical charts ($0\text{ to }1000\text{ dbar}$) with inverted depth, shaded 95% CI bands, and baseline comparisons. |
| **Live Prediction Readout** | `src/components/ProfilePlot.tsx` | **DONE** | Dynamic card updating in real time on graph hover with exact $T$, $S$, $\sigma_\theta$, layer badge, and delta from persistence. |
| **Quick Depth Jump** | `src/components/ProfilePlot.tsx` | **DONE** | Fast clickable depth buttons (`5m`, `50m`, `100m`, `200m`, `400m`, `700m`, `1000m`). |
| **Evidence-Link Protocol** | `src/components/EvidenceLinkViewer.tsx` | **DONE** | Merged seamlessly at the bottom of the Forecast tab below target profile banner. |
| **Conversational FloatChat** | `src/components/ChatPanel.tsx` | **DONE** | Grounded Q&A with KaTeX LaTeX formulas and NetCDF evidence citations. Powered by Gemini API with offline analytical fallback. |
| **Hydrographic Sea Map** | `src/components/TrajectoryMap.tsx` | **DONE** | Detailed Arabian Sea bathymetry, SST, and Haline salinity cores. Interactive drift playback, range rings, and cursor telemetry HUD. |
| **XAI & Physics Diagnostics** | `src/components/XaiDiagnostics.tsx` | **DONE** | Visualizes temporal lag weights ($t-1, t-2, t-3$), depth saliency matrix, and Brunt-Väisälä buoyancy frequency ($N^2$). |
| **Model Benchmarks** | `src/components/EvaluationBenchmarks.tsx` | **DONE** | Metric cards and comparative bar charts evaluating LSTM vs Gradient Boosting vs Persistence. |
| **Python FastAPI Backend** | `backend/` | **DONE** | Full FastAPI stack with all endpoints, database integration, PyTorch inference, UQ, TEOS-10 physics, Captum XAI. |
| **Local SQLite/Postgres DB** | `backend/app/models/` | **DONE** | SQLAlchemy 2.0 models, Alembic migrations, seeded with operational floats and profile levels. |
| **Argo NetCDF Pipeline** | `backend/scripts/` | **DONE** | Downloader + processor → canonical CSV at `backend/data/processed/argo_30floats_canonical.csv`. |
| **PyTorch Bi-LSTM Model** | `backend/app/ml/` | **DONE** | 2-layer Bi-LSTM (569K params), dual heads, auto device, Captum wrapper. |

---

## 3. What is Real vs. What is Simulated

### Currently Real:
- Complete React 19 UI hierarchy, state management, event listeners, hover tracking, and SVG rendering.
- Real REST API endpoints (`/api/health`, `/api/floats`, `/api/profiles/:wmoId`, `/api/forecast`, `/api/chat`) running via Python FastAPI on port 8000 (proxied via port 3000).
- Real SQLAlchemy queries against SQLite database `backend/data/floatchat.db`.
- Real PyTorch Bi-LSTM neural inference with 50-pass Monte Carlo Dropout UQ.
- Real mathematical TEOS-10 potential density calculations ($\sigma_\theta$) and Brunt-Väisälä buoyancy frequency ($N^2$) via `gsw` / analytical fallback.
- Real Captum Integrated Gradients temporal attribution and cross-depth saliency matrix.
- Real Evidence-Link composite cosine + Haversine provenance search against historical profiles.
- Gemini Flash SDK integration with offline analytical fallback engine.

### Deprecated / Retired:
- `server/argoData.ts`, `server/forecaster.ts`, `server/geminiService.ts`: Formally deprecated with JSDoc `@deprecated` headers (TASK-603). All active queries flow exclusively to the Python FastAPI backend.

---

## 4. Immediate Next Action
All Phase 6 and Phase 7 verification tasks are complete. Model training stretch optimization (TASK-303) remains as a research iteration. System is fully operational and verified end-to-end.

## 5. UI Bugfix Hardening (2026-09-25, Phase 8)
Five manually-reported UI bugs fixed and verified (`pytest` 10/10, `tsc --noEmit` clean, live `TestClient` checks):
1. Float dropdown shows all 47 floats when served by the Python backend (`seed_all_floats.py` is the canonical seeder; `seed_db.py` alone yields only 4).
2. First-3-cycle base selections no longer 400 opaquely: dropdown lists only forecastable cycles and errors name the earliest valid cycle.
3. "Inspect Profile & Lineage" modal renders: citations carry `provenance_chain` + 16 measurements + real lat/lon, with frontend optional-chaining guards.
4. FloatChat answers vary by intent (8 DB-grounded templates + explicit-depth queries; Gemini-first when `GEMINI_API_KEY` is set).
5. "Run Forecast" confirms recompute with an "Updated HH:MM:SS" chip next to the button.
