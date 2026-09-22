# FloatChat: Current System State

*Last updated: 2026-09-21*

---

## 1. Executive Snapshot
FloatChat currently operates as a complete, fully functional React 19 + TypeScript single-page application supported by an Express/Node.js development server bridge. The UI/UX is fully realized and responsive. The core forecasting algorithms, TEOS-10 potential density validation, Monte Carlo uncertainty bands, and GDAC Evidence citations are implemented in TypeScript in `server/forecaster.ts` and `server/argoData.ts`.

The next major architectural milestone is migrating the backend calculations into a high-performance Python FastAPI service backed by a real SQLite/PostgreSQL database and PyTorch ML models as planned in `.ai/tasks.md`.

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
| **Python FastAPI Backend** | `backend/` | **TO BUILD** | Detailed in `.ai/tasks.md` (Phases 0–6). |
| **Local SQLite/Postgres DB** | `backend/app/models/` | **TO BUILD** | Schema specified in `.ai/database.md`. |
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
- `server/argoData.ts`: 4 reference Arabian Sea floats with 35 cycles stored as in-memory TypeScript objects in the development bridge, mirroring `backend/data/seed_reference_profiles.json` rather than querying a relational database.
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
Proceed to **Phase 0 & Phase 1** in `.ai/tasks.md`:
1. Initialize the `backend/` folder hierarchy.
2. Ingest `backend/data/seed_reference_profiles.json` and build `download_argo.py` for the 30-float canonical pipeline.
3. Implement SQLAlchemy models in `backend/app/models/schema.py` and run `seed_db.py`.
