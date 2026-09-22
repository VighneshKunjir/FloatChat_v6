# FloatChat: Technical Architecture

## 1. Tech Stack & Exact Versions

### Frontend
- **Framework:** React 19 (`react@^19.0.1`, `react-dom@^19.0.1`)
- **Language:** TypeScript 5.8 / 7.0 (`typescript@^7.0.2`)
- **Build Tool:** Vite 8 (`vite@^8.3.0`, `@vitejs/plugin-react@^6.1.1`)
- **Styling:** Tailwind CSS v4 (`tailwindcss@^4.3.3`, `@tailwindcss/vite@^4.3.3`)
- **Icons:** Lucide React (`lucide-react@^0.546.0`)
- **Mathematical Rendering:** KaTeX (`katex@^0.18.7`, `rehype-katex@^7.0.1`, `remark-math@^6.0.0`, `react-markdown@^10.1.0`)
- **Animations:** Motion (`motion@^12.23.24`)

### Current Full-Stack Runtime (AI Studio Node/Express Bridge)
- **Server:** Node.js v20+ with Express 4 (`express@^4.21.2`, `@types/express@^4.17.21`)
- **TS Execution:** TSX (`tsx@^4.21.0`)
- **Server Bundler:** esbuild (`esbuild@^0.25.0`)
- **LLM SDK:** `@google/genai@^2.4.0`
- **Port:** Port `3000` (Vite middleware in dev, static dist server in production)

### Target Local Architecture (CLI Agent Python ML Backend)
- **Language:** Python 3.11+
- **Backend Framework:** FastAPI (`fastapi>=0.110.0`, `uvicorn[standard]>=0.28.0`)
- **Data Validation & Schemas:** Pydantic v2 (`pydantic>=2.6.0`)
- **Database & ORM:** SQLite (Zero-config dev) / PostgreSQL 16 (Production Docker Compose) + SQLAlchemy 2.0 (`sqlalchemy>=2.0.28`, `alembic>=1.13.1`)
- **Scientific & Oceanographic Libraries:**
  - `gsw>=3.6.17` (TEOS-10 Gibbs SeaWater Oceanographic Toolbox in Python)
  - `netCDF4>=1.6.5` / `xarray>=2024.2.0` (Argo GDAC NetCDF parsing)
  - `numpy>=1.26.4`, `scipy>=1.12.0`, `pandas>=2.2.1`
- **Machine Learning & Deep Learning:**
  - `torch>=2.2.1` (Physics-Informed PyTorch Sequence LSTM / GRU)
  - `scikit-learn>=1.4.1` (Baseline regressors, scalers, cosine similarity)
- **Explainability (XAI):**
  - `captum>=0.7.0` (PyTorch Integrated Gradients saliency attributions)
  - `shap>=0.45.0` (Shapley feature attribution baselines)

---

## 2. Target Repository Folder Structure

```
.
├── .ai/                                # [EXISTS] Complete AI Context Pack for CLI Agents
│   ├── README.md                       # Index and reading sequence
│   ├── prd.md                          # Product requirements & user stories
│   ├── architecture.md                 # System architecture (this file)
│   ├── rules.md                        # Coding standards & DO NOT list
│   ├── design.md                       # Design system tokens & component styles
│   ├── data_spec.md                    # Data dictionary & NetCDF schema
│   ├── ml_spec.md                      # ML model, training & XAI specifications
│   ├── api_contract.md                 # OpenAPI REST contract & schemas
│   ├── database.md                     # SQL DDL & SQLAlchemy ORM models
│   ├── integration_map.md              # Frontend-to-backend feature wiring table
│   ├── tasks.md                        # Phased task backlog with acceptance checkboxes
│   ├── testing.md                      # Test suite specification & commands
│   ├── env_and_setup.md                # Environment variables & run guide
│   ├── current_state.md                # Live project snapshot
│   ├── memory.md                       # Architectural decisions & assumptions
│   └── changelog.md                    # Historical record of changes
├── AGENTS.md                           # [EXISTS] Root CLI Agent entry point
├── package.json                        # [EXISTS] Frontend & Node dev dependencies
├── tsconfig.json                       # [EXISTS] TypeScript configuration
├── vite.config.ts                      # [EXISTS] Vite bundler config with Tailwind v4
├── index.html                          # [EXISTS] HTML shell with KaTeX CSS
├── server.ts                           # [EXISTS] Node/Express API bridge (to be migrated/proxied)
├── server/                             # [EXISTS] Node mock & forecasting modules
│   ├── argoData.ts                     # In-memory Argo profiles & baseline floats
│   ├── forecaster.ts                   # Forecast, UQ, TEOS-10 & Evidence linker
│   └── geminiService.ts                # Gemini API client & offline synthesis fallback
├── src/                                # [EXISTS] React 19 Frontend
│   ├── App.tsx                         # Main container & tab orchestrator
│   ├── types.ts                        # TypeScript domain interfaces
│   ├── index.css                       # Global styles (@import "tailwindcss";)
│   ├── main.tsx                        # React DOM entry point
│   ├── services/                       # [TO CREATE] Type-safe API client layer
│   │   └── api.ts                      # Clean fetch client routing to backend
│   └── components/                     # [EXISTS] Reusable UI components
│       ├── Header.tsx                  # Top banner & 5-tab navigation
│       ├── ControlBar.tsx              # WMO selector, cycle picker, variable mode
│       ├── ProfilePlot.tsx             # Dual-profile chart & Live Readout
│       ├── EvidenceLinkViewer.tsx      # GDAC NetCDF citations viewer
│       ├── ChatPanel.tsx               # LaTeX conversational assistant
│       ├── TrajectoryMap.tsx           # Arabian Sea bathymetric map
│       ├── XaiDiagnostics.tsx          # Temporal/depth saliency & Brunt-Väisälä
│       └── EvaluationBenchmarks.tsx    # Model comparison benchmarks
└── backend/                            # [TO CREATE] Production Python ML Backend
    ├── app/
    │   ├── main.py                     # FastAPI entry point & CORS configuration
    │   ├── config.py                   # Pydantic Settings & environment loader
    │   ├── api/                        # API route handlers
    │   │   ├── health.py               # GET /api/health
    │   │   ├── floats.py               # GET /api/floats & GET /api/profiles/{wmoId}
    │   │   ├── forecast.py             # POST /api/forecast (ML + UQ + XAI)
    │   │   └── chat.py                 # POST /api/chat (X-RAG conversational engine)
    │   ├── core/                       # Core scientific algorithms
    │   │   ├── physics.py              # TEOS-10 potential density & Brunt-Väisälä
    │   │   ├── evidence.py             # Vector cosine similarity & GDAC matching
    │   │   └── uq.py                   # Monte Carlo Dropout & CI calculations
    │   ├── models/                     # SQLAlchemy ORM database models
    │   │   ├── float_meta.py           # Argo float metadata
    │   │   ├── profile.py              # Measurements & cycles
    │   │   └── forecast_log.py         # Historical predictions & audit logs
    │   ├── schemas/                    # Pydantic request & response schemas
    │   │   ├── forecast.py             # ForecastResult, UncertaintyBound
    │   │   └── chat.py                 # ChatRequest, ChatResponse
    │   ├── ml/                         # ML inference & model artifacts
    │   │   ├── model.py                # PyTorch Physics-Informed LSTM definition
    │   │   ├── xai.py                  # Captum Integrated Gradients service
    │   │   └── artifacts/              # Serialized model weights & scaler (.pt/.joblib)
    │   └── db/                         # Database connection & migrations
    │       ├── session.py              # SQLAlchemy engine & sessionmaker
    │       └── alembic/                # Database migrations
    ├── data/                           # Local Argo data repository
    │   ├── raw/                        # Original NetCDF files from GDAC
    │   └── processed/                  # Standardized 16-level interpolated datasets
    ├── scripts/                        # Pipelines and seeding
    │   ├── download_argo.py            # Fetch Arabian Sea floats from IFREMER/USGODAE
    │   ├── train_model.py              # Physics-Informed LSTM training script
    │   └── seed_db.py                  # Ingest NetCDF into SQLite/PostgreSQL
    ├── requirements.txt                # Python dependencies
    ├── Dockerfile                      # Backend container definition
    └── docker-compose.yml              # Local PostgreSQL + Backend + Vite frontend
```

---

## 3. System Architecture Diagram

```
+-----------------------------------------------------------------------------------+
|                              REACT 19 FRONTEND                                    |
|  [ControlBar]  -->  [ProfilePlot]  -->  [ChatPanel]  -->  [TrajectoryMap]         |
|  (User WMO/Cyc)     (SVG + Readout)     (KaTeX Chat)     (Bathymetry Map)         |
+-----------------------------------------+-----------------------------------------+
                                          | JSON over HTTP / REST
                                          v
+-----------------------------------------------------------------------------------+
|                            FASTAPI BACKEND (Port 8000)                            |
|                                                                                   |
|  [API Router]                                                                     |
|    |-- GET  /api/health                                                           |
|    |-- GET  /api/floats                                                           |
|    |-- GET  /api/profiles/{wmoId}                                                 |
|    |-- POST /api/forecast  -----------------+                                     |
|    `-- POST /api/chat                       |                                     |
|                                             v                                     |
|  [Services & Pipelines]             [ML Inference Engine]                         |
|    |-- Preprocessing Scaler           |-- PyTorch Physics-Informed LSTM           |
|    |-- TEOS-10 Physics Engine (gsw)   |-- Monte Carlo Dropout (50 stochastic passes)|
|    |-- Evidence-Link Cosine Matcher   `-- Captum Integrated Gradients Saliency    |
|    `-- Grounded LLM Dialogue Synthesizer (Gemini / Offline Synthesis)             |
+-------------------------------------+---------------------------------------------+
                                      | SQLAlchemy ORM
                                      v
+-----------------------------------------------------------------------------------+
|                        LOCAL DATABASE (SQLite / PostgreSQL)                       |
|   Tables: argo_floats, argo_profiles, profile_levels, forecast_logs               |
+-----------------------------------------------------------------------------------+
```

---

## 4. Main Prediction Request Lifecycle
1. **Trigger:** User selects float `3902114`, cycle `92`, or clicks "Refresh Forecast" in `ControlBar.tsx`.
2. **Client Call:** `src/services/api.ts` invokes `POST /api/forecast` with `{ "wmoId": "3902114", "cycle": 92 }`.
3. **Validation:** FastAPI deserializes payload through `ForecastRequest` Pydantic schema.
4. **Data Retrieval:** Database loads cycles $t-3, t-2, t-1$ for float `3902114` (normalized onto 16 standard pressure levels).
5. **Inference & UQ:**
   - Preprocessing transforms input tensor into shape `(1, 3, 32)` ($3$ cycles, $16$ temps $+ 16$ salinities).
   - PyTorch LSTM executes $50$ Monte Carlo stochastic forward passes with dropout ($p=0.2$) enabled.
   - Mean vector $\mu$ yields forecasted profile; sample variance $\sigma^2$ yields 90% and 95% confidence intervals.
6. **Physics Verification:**
   - The thermodynamic engine (`gsw`) computes potential density $\sigma_\theta$ and static stability $\frac{\partial\sigma_\theta}{\partial z}$.
   - Mixed-layer depth (MLD) and maximum thermocline gradient are computed.
7. **Explainability Attribution:**
   - Captum computes Integrated Gradients against the input sequence to generate temporal attribution weights ($t-1, t-2, t-3$) and depth saliency matrix.
8. **Evidence Citation Matching:**
   - The candidate vector space of historical NetCDF profiles is searched using cosine similarity + spatial distance. Top 3 analogues are extracted with QC verification.
9. **Response Serialization:** A complete `ForecastResult` JSON object is returned to the client in $<250\text{ ms}$.
10. **UI Rendering:**
    - `ProfilePlot.tsx` updates SVG curves and shaded 95% CI bands.
    - `Live Prediction Readout` updates with active hover values.
    - `EvidenceLinkViewer.tsx` displays matching NetCDF citations.

---

## 5. Model Serving & Lifecycle Strategy
- **Load Once at Startup:** PyTorch model weights (`.pt`) and feature standardizers (`.joblib`) are loaded into GPU/CPU memory during FastAPI's `lifespan` event.
- **Model Artifact Packaging:**
  - `model_weights.pt`: PyTorch state dictionary.
  - `preprocessor.joblib`: Standard scalers for Temperature, Salinity, and Depth.
  - `metadata.json`: Architecture hyperparameters, training dataset hash, training timestamp, and validation metrics.
- **Thread Safety:** The PyTorch model operates in evaluation mode (`model.train(False)` for standard layers, with dropout layers explicitly set to `torch.nn.functional.dropout(..., training=True)` only during the Monte Carlo loop).

---

## 6. Configuration & Local Dev Setup

### Zero-Config Local Setup (Default)
- **Database:** SQLite file (`backend/data/floatchat.db`). Requires zero external installations.
- **Frontend & Backend Ports:**
  - Frontend (Vite): `http://localhost:3000`
  - Python Backend (FastAPI): `http://localhost:8000`
  - Vite reverse-proxies `/api/*` requests to `http://localhost:8000` via `vite.config.ts`.
