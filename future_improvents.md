# FloatChat: Future Improvements Log

Living record of user-proposed future work. Items move here when raised,
and gain an implementation note once built. Nothing in this file gates
current phases.

---

## [OPEN] Custom-volume data pipeline (discover by years → download → train)
- **Raised:** 2026-09-26 (user).
- **Idea:** `discover_arabian_sea_floats.py` should discover floats for
  user-specified years; the result feeds the download script so we can
  train on any amount of data (34 → 45/50+ floats and beyond).
- **Enabling work already done:**
  - Discovery accepts `--years '2020-2024'` (or `'2022,2023'`) and
    `--min-cycles N`, and writes the floats file.
  - `download_argo_netcdf.py` accepts `--floats-file` (discovery output
    or `WMO,DAC[,NAME]` rows), replacing the hardcoded list.
  - `setup.py --discover --years …` chains discovery → download →
    process → train in one command.
- **Still open:** exercising a 60+ float corpus end-to-end and measuring
  whether volume moves test RMSE (evidence so far: 32 → 47 floats moved
  0.547 → 0.513; diminishing returns expected).

## [OPEN] Gemini API key input through the frontend
- **Raised:** 2026-09-26 (user).
- **Idea:** let the user paste their Gemini API key in the UI instead of
  only via `.env` / environment.
- **Design constraint:** setup must stay key-agnostic (ensure `.env`
  exists, prompt once at most, never require; offline fallback stays).
- **Backend work needed (not started):** e.g. `POST /api/config/gemini-key`
  storing a runtime override, with resolution order
  request override → stored key → env → offline synthesis.
  Chat endpoint and `ChatPanel.tsx` then need a key-status indicator.
- **Docs to update when built:** `.ai/env_and_setup.md`,
  `.ai/api_contract.md`, `.ai/integration_map.md`.
