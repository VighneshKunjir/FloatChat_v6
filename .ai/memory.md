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

---

## 2. Tracking `[ASSUMPTION]` and `[DECISION NEEDED]`

### Active Assumptions:
- `[ASSUMPTION-001]`: The 16 standard pressure levels ($5, 10, 20, 30, 50, 75, 100, 125, 150, 200, 250, 300, 400, 500, 700, 1000\text{ dbar}$) are universally sufficient for Arabian Sea upper-ocean and thermocline characterization.
- `[ASSUMPTION-002]`: A 3-cycle historical window ($t-3, t-2, t-1$, representing a 30-day temporal lag) provides optimal balance between capturing seasonal drift and minimizing missing-cycle gaps in float lifetime.
- `[ASSUMPTION-003]`: In offline environments or when `GEMINI_API_KEY` is not provided, users prefer an instant, high-fidelity analytical response rather than an error modal.

### Decisions Needed:
- `[DECISION NEEDED-001]`: Should user forecast histories and chat sessions be persisted permanently across browser sessions, or kept ephemeral in-memory? (Recommended: Persist in `forecast_logs` table).
- `[DECISION NEEDED-002]`: Should the backend provide a direct NetCDF file export endpoint (`GET /api/forecast/export.nc`) for operational oceanographers?
- `[DECISION NEEDED-003]`: For the Python backend migration, should FastAPI run on port 8000 with Vite proxying `/api` requests, or should the frontend build be served directly by FastAPI static mounting in production? (Recommended: Proxy in dev, single Docker container in prod).

---

## 3. Gotchas & Domain Insights
1. **KaTeX CSS Requirement:** The KaTeX mathematical stylesheet must be explicitly included in `index.html` (`<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.8/dist/katex.min.css">`). Without this, mathematical equations like $\frac{\partial\sigma_\theta}{\partial z}$ render as unstyled raw text.
2. **Pressure vs. Depth:** In oceanography, pressure in decibars (`dbar`) is approximately equal to depth in meters (1 dbar $\approx$ 0.993 m at low latitudes). Vertical profile plots must invert the vertical axis (0 dbar at top, 1000 dbar at bottom).
3. **Delayed-Mode vs. Real-Time QC:** Only use delayed-mode (`DATA_MODE = 'D'`) or QC flags 1/2 for model training and evidence citations. Real-time (`'R'`) uncorrected data often contain sensor drift spikes near the surface.
