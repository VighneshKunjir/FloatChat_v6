# FloatChat: Architectural Memory & Decision Log

## 1. Architectural Decisions (ADRs)

### ADR-001: Merging Evidence-Link Protocol into Profile Forecast Tab
- **Date:** 2026-09-21
- **Status:** Accepted & Implemented
- **Context:** Previously, "Evidence-Link Protocol" was a separate tab in the top navigation. Users had to switch tabs to verify the raw NetCDF data citations corresponding to the forecast they were viewing.
- **Decision:** Remove the standalone tab and merge the `EvidenceLinkViewer` component directly at the bottom of the `ProfilePlot` view, positioned right beneath the `Target Profile:` summary banner.
- **Consequences:** Provides an uninterrupted scientific workflow from high-level visual forecast curve down to granular NetCDF provenance on a single scrollable page.

### ADR-002: Tab Re-sequencing & Renaming
- **Date:** 2026-09-21
- **Status:** Accepted & Implemented
- **Context:** Tab labels contained redundant regional words ("Arabian Sea Map"), and the order did not match the typical researcher workflow.
- **Decision:** Removed "Arabian" from tab labels and established the fixed sequence:
  1. Profile Forecast & UQ
  2. FloatChat
  3. Sea Map
  4. XAI & TEOS-10 Physics
  5. Model Benchmarks
- **Consequences:** Cleaner navigation hierarchy aligned with user expectations.

### ADR-003: Selection of Dual-Mode Database Architecture (SQLite + PostgreSQL)
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** CLI coding agents and developers may run in diverse environments (some without Docker or local PostgreSQL daemons installed).
- **Decision:** Use SQLAlchemy 2.0 with standard SQL DDL so the backend defaults to zero-config file-based SQLite (`sqlite:///./data/floatchat.db`), while supporting PostgreSQL seamlessly via the `DATABASE_URL` environment variable.
- **Consequences:** Zero-friction local startup while remaining fully production-ready.

### ADR-004: High-End GPU Training Prioritization with CPU Fallback
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** User has a high-end dedicated GPU workstation. Training and forward-backward propagation should leverage CUDA first.
- **Decision:** All PyTorch code defaults to `torch.device("cuda" if torch.cuda.is_available() else "mps" if ... else "cpu")`. Training loops enable `torch.backends.cudnn.benchmark = True` and mixed precision.
- **Consequences:** Fast model training (< 30 seconds) on GPU with transparent fallback on CPU-only CI environments.

### ADR-005: Self-Contained Embedded Dataset Default with Future Scope for Live FTP
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** Remote GDAC FTP mirrors are prone to firewall blocks, timeouts, and network failures in sandboxed environments.
- **Decision:** Default local development database seeding strictly to `backend/data/seed_reference_profiles.json` (35 historical cycles across the 4 operational Arabian Sea reference floats: 3902114, 2903334, 1902442, 2902789).
- **Consequences:** Database seeding completes 100% offline in $< 2$ seconds.

### ADR-006: Captum Multi-Output Single Target Wrapper
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** Captum Integrated Gradients crashes on multi-head Bi-LSTM outputs returning tuples or multi-column tensors.
- **Decision:** Require `SingleOutputModelWrapper` isolating a specific target variable and depth index before computing attributions.

### ADR-007: Dual-Runtime Compatibility & Pydantic Request Alias Handling
- **Date:** 2026-09-21
- **Status:** Accepted
- **Context:** The frontend React components (`src/App.tsx`, `src/components/ChatPanel.tsx`) submit payload parameters in camelCase (`wmoId`, `cycle`), while standard Python conventions use snake_case (`wmo_id`, `cycle_number`). Furthermore, AI Studio enforces Port 3000 as the sole reverse proxy port.
- **Decision:** All FastAPI Pydantic request models must enable `populate_by_name=True` with explicit aliases (e.g., `Field(alias="wmoId")` and `Field(alias="cycle")`) to accept both conventions seamlessly. The dev environment routes requests through Port 3000 to maintain uninterrupted live preview.
- **Consequences:** Eliminates 422 Unprocessable Entity runtime errors when switching between frontend mock server and real Python FastAPI backend.

### ADR-008: 34-Float 4-Year NetCDF Pipeline for Operational Model Scaling
- **Date:** 2026-09-22 (Updated 2026-09-23)
- **Status:** Accepted
- **Context:** While the 4-float seed dataset is ideal for instant automated testing and offline development, training deep sequence models requires statistical diversity across seasonal monsoonal cycles and broader Arabian Sea hydrography. The user provided the exact set of 34 downloaded NetCDF float platforms (`6903059`, `6903060`, `6903063`, `6903058`, `2900090`, `2901509`, `6902943`, `6903062`, `2900089`, `2901447`, `2901108`, `2901107`, `6903008`, `2900394`, `6903046`, `2901337`, `2901370`, `2901372`, `2902390`, `6903007`, `2902203`, `2901444`, `2901339`, `2901338`, `2901466`, `2901415`, `2901465`, `2902391`, `2902206`, `2901132`, `1902442`, `2902789`, `2903334`, `3902114`).
- **Decision:** Target solely these 34 floats in `backend/scripts/download_argo.py` and the application catalog. Ingest 4-year NetCDF data for these 34 floats, clean fill values and unphysical outliers, filter by QC flags (1/2), and interpolate to the canonical 16-level depth grid. Export as a unified wide-format CSV (`backend/data/processed/argo_34floats_canonical.csv`) with one row per profile.
- **Consequences:** Restricts project scope and model training strictly to the exact 34 available NetCDF floats. Provides a scalable, high-volume training corpus for the PyTorch Bi-LSTM and Gradient Boosting baselines while maintaining seamless offline testing.

---

## 2. Tracking `[ASSUMPTION]` and Resolved Decisions

### Active Assumptions:
- `[ASSUMPTION-001]`: The 16 canonical standard pressure levels ($5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000\text{ dbar}$) are universally sufficient for Arabian Sea upper-ocean and thermocline characterization, matching the operational frontend visualization and deep abyssal layer.
- `[ASSUMPTION-002]`: A 3-cycle historical window ($t-3, t-2, t-1$, representing a 30-day temporal lag) provides optimal balance between capturing seasonal drift and minimizing missing-cycle gaps in float lifetime.
- `[ASSUMPTION-003]`: In offline environments or when `GEMINI_API_KEY` is not provided, users prefer an instant, high-fidelity analytical response rather than an error modal.

### Resolved Decisions:
- `[RESOLVED-001]`: **Forecast Persistence:** Persist all run forecasts into the `forecast_logs` table via `POST /api/forecast`. Provide `GET /api/history` for audit and retrospective visualization.
- `[RESOLVED-002]`: **Forecast Export Format:** Standard JSON export (`GET /api/forecast/{id}/export-json` or client-side download) is implemented now. CF-compliant NetCDF (`.nc`) export is logged under Future Scope.
- `[RESOLVED-003]`: **Runtime Architecture:** Dual-mode in development (FastAPI on 8000, Vite on 3000 proxying `/api`). In production Docker, single FastAPI service serving the static `dist/` bundle on port 3000.
- `[RESOLVED-004]`: **NetCDF Range Pre-Filtering & Arctic Split Stratification:** 
  - *Context:* `train_model.py` had to drop rows violating physical ranges ($T \in [-2, 35]^\circ\text{C}$, $S \in [30, 42]\text{ PSU}$) because raw NetCDF files and interpolation leaked sentinels (`99999.0`, `-999.0`) into CSV files. Additionally, the 5 sub-polar / Arctic floats (`6903058`, `6903059`, `6903060`, `6903062`, `6903063`) caused high validation variance under unstratified spatial splits due to extreme hydrographic differences.
  - *Resolution:*
    1. Upstream sanitization (`sanitize_raw_measurements` in `download_argo.py` / `process_argo_netcdf.py`) masks sentinels ($\ge 9990$, $\le -990$) to `np.nan` and enforces strict bounds on raw and post-interpolated values.
    2. Any cycle with unphysical levels after interpolation is discarded *before* writing to `argo_34floats_canonical.csv`, ensuring 100% of rows are retained during training.
    3. Spatial splits use **Hydrographic Domain Stratification** (24 train / 5 val / 5 test):
       - Sub-polar floats (`69030xx`): 3 in train, 1 in val, 1 in test.
       - Tropical Arabian Sea floats (29 floats): 21 in train, 4 in val, 4 in test.
       This prevents spatial domain shifts from inflating evaluation loss.

---

## 3. Gotchas & Domain Insights
1. **KaTeX CSS Requirement:** The KaTeX mathematical stylesheet must be explicitly included in `index.html` (`<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">`). Without this, mathematical equations like $\frac{\partial\sigma_\theta}{\partial z}$ render as unstyled raw text.
2. **Pressure vs. Depth:** In oceanography, pressure in decibars (`dbar`) is approximately equal to depth in meters (1 dbar $\approx$ 0.993 m at low latitudes). Vertical profile plots must invert the vertical axis (0 dbar at top, 1000 dbar at bottom).
3. **Delayed-Mode vs. Real-Time QC:** Only use delayed-mode (`DATA_MODE = 'D'`) or QC flags 1/2 for model training and evidence citations. Real-time (`'R'`) uncorrected data often contain sensor drift spikes near the surface.
