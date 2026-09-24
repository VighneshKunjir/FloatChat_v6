# FloatChat: Current System State

*Last updated: 2026-09-23*

---

## 1. Executive Snapshot
FloatChat currently operates as a complete, fully functional React 19 + TypeScript single-page application supported by an Express/Node.js development server bridge. The UI/UX is fully realized and responsive. The core forecasting algorithms, TEOS-10 potential density validation, Monte Carlo uncertainty bands, and GDAC Evidence citations are implemented in TypeScript in `server/forecaster.ts` and `server/argoData.ts`.

The next major architectural milestone is migrating the backend calculations into a high-performance Python FastAPI service backed by a real SQLite/PostgreSQL database and PyTorch ML models as planned in `.ai/tasks.md`.

**Phase 0 Complete**: Backend directory structure created, Python dependencies defined and installed, reverse proxy configured for `/api/*` → FastAPI (port 8000).

**Phase 1 Complete**: SQLAlchemy 2.0 ORM models implemented, Alembic migrations configured, database seeded with 4 floats, 35 profiles, 560 level measurements from `seed_reference_profiles.json`.

**TASK-104 Complete**: Argo NetCDF processing pipeline built (`backend/scripts/process_argo_netcdf.py`), canonical CSV created (`backend/data/processed/argo_30floats_canonical.csv`) with 8,738 profiles from 32 floats, 16 standard depths, TEOS-10 physics (σ_θ, N², MLD, stability).

**TASK-201 Complete**: TEOS-10 Physics Engine (`backend/app/core/physics.py`) with gsw + NumPy fallback, computes σ_θ, ∂σ_θ/∂z, N², MLD, thermocline gradient. Acceptance criteria passed.

**TASK-202 Complete**: Evidence-Link Matcher (`backend/app/core/evidence.py`) with cosine (75%) + Haversine spatial (25%) composite scoring. Returns top 3 citations with QC flag 1/2 and valid NetCDF paths.

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
| **Python FastAPI Backend** | `backend/` | **PHASE 0-1 DONE** | Directory structure, requirements, proxy configured. DB schema & seed done. Phases 2–6 in `.ai/tasks.md`. |
| **Local SQLite/Postgres DB** | `backend/app/models/` | **DONE** | SQLAlchemy 2.0 models, Alembic migrations, seeded with 4 floats / 35 profiles / 560 levels. |
| **Argo NetCDF Pipeline** | `backend/scripts/` | **DONE** | Downloader + processor → 8,738 profiles, 32 floats, canonical CSV at `backend/data/processed/argo_30floats_canonical.csv` |
| **PyTorch Bi-LSTM Model** | `backend/app/ml/` | **TO BUILD** | Architecture specified in `.ai/ml_spec.md`. |

---

## 3. What is Real vs. What is Simulated

### Currently Real:
- Complete React 19 UI hierarchy, state management, event listeners, hover tracking, and SVG rendering.
- Real REST API endpoints (`/api/health`, `/api/floats`, `/api/profiles/:wmoId`, `/api/forecast`, `/api/chat`) running via Express.
- Mathematical TEOS-10 potential density calculations ($\sigma_\theta$) and Brunt-Väisälä buoyancy frequency ($N^2$).
- Gemini 2.5/3.8 Flash SDK integration for conversational RAG dialogue with grounding verification.
- Offline analytical fallback engine generating grounded oceanographic explanations when API keys are absent.

### Currently In-Memory / Simulated:
- `server/argoData.ts`: 4 reference Arabian Sea floats with 35 cycles stored as in-memory TypeScript objects in the development bridge, mirroring `backend/data/seed_reference_profiles.json` rather than querying a relational database. **→ To be replaced by SQLite queries in Phase 5-6.**
- `server.ts` & `server/`: Currently acts as the development and AI Studio bridge serving mock API responses and the Vite SPA. In Phase 6, this is superseded or proxied to the production Python FastAPI ML backend.
- `server/forecaster.ts`: Forecasting logic uses analytical numerical simulations mimicking an evaluated LSTM rather than a loaded `.pt` neural network.
- Saliency weights: Hardcoded representative values calibrated from offline training rather than dynamically generated per-request by Captum.

---

## 4. Known Bugs & Minor Limitations
- No persistent storage for user forecast logs or custom chat sessions (reset on page reload).
- When running in purely client-side static mode without Node or Python backend, `/api` calls fail (requires running `npm run dev` or backend server).
- In the dual-stack development setup, proxying via `vite.config.ts` requires running standalone Vite or routing requests through `server.ts` when Express handles `/api/*` routes.

---

## 5. Immediate Next Action
Proceed to **Phase 2** in `.ai/tasks.md`:
1. Implement TEOS-10 Thermodynamic Calculations with Fallback (TASK-201: `backend/app/core/physics.py`).
2. Implement Evidence-Link Cosine Provenance Matcher (TASK-202: `backend/app/core/evidence.py`).
