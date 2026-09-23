# FloatChat: Engineering Rules & Coding Standards

## 1. Ground Rules & Work Invariants
1. **Never Break Working UI:** The current React frontend is visually refined, responsive, and passes all domain criteria. You must NOT alter layout geometry, spacing, color tokens, or component hierarchy unless explicitly instructed.
2. **API & Service Layer Separation:** UI components must never call `fetch()` directly. All HTTP requests MUST flow through `src/services/api.ts`.
3. **Data Authenticity:** No simulated random numbers in production pathways. All numbers must derive from actual Argo measurements, physics formulations (TEOS-10), or evaluated ML inference passes.
4. **Strong Typing Everywhere:** Zero `any` in new TypeScript code. Zero untyped dictionaries in Python backend endpoints (use Pydantic models).

---

## 2. Language & Framework Standards

### TypeScript / Frontend
- **Target:** TypeScript 5.8+ / ES2022.
- **Imports:** Standard top-level named imports (e.g. `import { ForecastResult, ArgoProfile } from '../types.ts';`). Avoid namespace star destructuring on CommonJS dynamic `require()` statements.
- **Icons:** All UI icons MUST be imported exclusively from `lucide-react`. Do NOT write custom inline SVG icons.
- **Styling:** Tailwind CSS utility classes exclusively. No external CSS files (except `src/index.css` which houses `@import "tailwindcss";`).
- **Mathematical Formulations:** All equations in chat or documentation MUST use valid LaTeX syntax (`$..$` for inline, `$$..$$` for block) compatible with `rehype-katex`.

### Python / Backend
- **Python Version:** 3.11+.
- **Formatting & Linting:** `ruff` or `black` for formatting; `flake8` and `mypy --strict` for static type checking.
- **Endpoints:** Every API route MUST define explicit `response_model` schemas using Pydantic v2.
- **Async I/O:** Use `async def` for I/O bound endpoints (database access, LLM calls) and `def` with background thread pools for heavy CPU matrix operations.

---

## 3. Machine Learning & Scientific Physics Rules

1. **Hardware & Compute Execution:** All PyTorch operations MUST prioritize high-end GPU compute (`cuda` if available, `mps` if on Apple Silicon, with `cpu` strictly as fallback):
   ```python
   device = torch.device("cuda" if torch.cuda.is_available() else "mps" if hasattr(torch.backends, "mps") and torch.backends.mps.is_available() else "cpu")
   ```
2. **TEOS-10 Thermodynamics & Fallback Resilience:** Calculate potential density $\sigma_\theta$ and static stability using `gsw.sigma0`. If `gsw` C-extensions fail to load on any platform, code MUST gracefully fallback to the pure NumPy UNESCO/TEOS-10 polynomial approximation:
   $$\sigma_\theta \approx 28.14 - 0.0735\,T - 0.00469\,T^2 + 0.802\,(S - 35.0)$$
   (Never crash on import error).
3. **Captum Attribution Multi-Output Wrapping:** Multi-head PyTorch models returning `(T, S)` tuples MUST be wrapped with `SingleOutputModelWrapper` targeting a specific variable and depth index before calling Captum `IntegratedGradients`.
4. **Physical Stability Constraint:** Every forecasted profile MUST be validated against the TEOS-10 potential density criterion:
   $$\frac{\partial \sigma_\theta}{\partial z} \ge 0$$
   If an inference pass violates this condition, it must be flagged with `is_gravitationally_stable = False` and the exact violation count recorded.
5. **Reproducibility & Random Seeds:** All stochastic operations (Monte Carlo dropout, train/val/test splits, baseline seeds) must use a fixed seed (`seed = 42`).
6. **No Data Leakage & Dataset Partitioning:** Training is grounded on the canonical 30 operational Arabian Sea floats spanning 4 years of historical profile cycles discretized across the canonical 16 depth levels (`[5, 20, ..., 1000] dbar`). When splitting into training, validation, and test sets, splits must be performed at the **Float Platform Level (WMO ID)** (e.g. 21 train / 4–5 val / 4–5 test floats) and temporally (historical cycles $1 \dots N-10$ for training, final 10 cycles for temporal testing). Never mix cycles from the same float across train and test without temporal partitioning.
7. **Inference Latency Limit:** Inference, uncertainty calculation (50 passes), and XAI attribution have a directional target of under **350 ms** on CPU/GPU (pipeline correctness and zero density inversions take absolute precedence over micro-optimization on CPU). Never run training or parameter optimization inside request handlers.

---

## 4. API Design & Error Handling Conventions

- **URL Convention:** All API endpoints must be prefixed with `/api/` (e.g., `/api/forecast`, `/api/chat`).
- **JSON Field Naming:**
  - **API Contract:** Strictly `snake_case` in schemas (e.g., `depth_dbar`, `temperature_forecast`, `uncertainty_bounds`, `wmo_id`).
  - **Pydantic Request Aliases:** Follow **ADR-007** in `.ai/memory.md` (`populate_by_name=True` with aliases `Field(alias="wmoId")` and `Field(alias="cycle")`) so incoming camelCase from frontend React components is parsed without 422 errors.
  - **TypeScript Interfaces:** Match `src/types.ts` exactly.
- **Standard Error Response:**
  ```json
  {
    "error": {
      "code": "FLOAT_NOT_FOUND",
      "message": "Argo Float with WMO ID 3909999 was not found in database.",
      "details": { "wmoId": "3909999" }
    }
  }
  ```
- **HTTP Status Codes:**
  - `200 OK`: Successful retrieval or forecast execution.
  - `400 Bad Request`: Invalid payload parameters (e.g. negative cycle, non-existent depth).
  - `404 Not Found`: Float or cycle does not exist in the archive.
  - `500 Internal Server Error`: Unhandled model computation or database failure.

---

## 5. Security & Environment Rules

1. **No Secrets in Source Code:** API keys (such as `GEMINI_API_KEY`) and database credentials MUST be read strictly from environment variables (`process.env` in Node, `os.environ` or Pydantic `BaseSettings` in Python).
2. **Never Commit Secrets:** Real keys must never be committed to Git. Document all required variables in `.env.example`.
3. **CORS Configuration:** In local development, permit requests from `http://localhost:3000` and `http://127.0.0.1:3000`.

---

## 6. The "DO NOT" List (Strict Agent Prohibitions)

- **DO NOT** delete, rename, or reorganize files in `src/components/` unless explicitly specified in an assigned task in `.ai/tasks.md`.
- **DO NOT** introduce secondary styling libraries (e.g., Material UI, Ant Design, Bootstrap, styled-components).
- **DO NOT** implement client-side mock databases when building the real backend; all data must be retrieved over HTTP from the backend service.
- **DO NOT** replace KaTeX math rendering with plain text approximations (e.g., never write "d(sigma)/dz >= 0" if LaTeX $\frac{\partial \sigma_\theta}{\partial z} \ge 0$ is expected).
- **DO NOT** generate unsolicited UI tabs, marketing banners, or navigation bars.
- **DO NOT** remove the NetCDF provenance metadata or quality control flags from the forecast result schema.
- **DO NOT** depend on external GDAC FTP connections during automated testing or seeding; always use the self-contained `seed_reference_profiles.json` dataset.
- **DO NOT** modify frontend components in `src/` until Phase 1–5 backend endpoints pass unit tests (`pytest`).
- **DO NOT** call Captum `IntegratedGradients` directly on a multi-head model without the `SingleOutputModelWrapper`.
