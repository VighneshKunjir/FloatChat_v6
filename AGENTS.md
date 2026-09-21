# Agent Instructions for FloatChat

Welcome to **FloatChat** (Explainable Evidence-Linked Argo Ocean Profile Forecasting & Physics Validation Engine).

## CRITICAL DIRECTIVES FOR CODING AGENTS
1. **First Action:** You MUST read `.ai/README.md` and `.ai/current_state.md` before performing any code generation or modifications.
2. **Work Loop:** Work iteratively through the tasks documented in `.ai/tasks.md`. Select the first unchecked task, implement it according to `.ai/rules.md` and the relevant specifications, run the acceptance test, and update `.ai/tasks.md` and `.ai/current_state.md`.
3. **Preserve Working Frontend:** The React 19 frontend is complete, responsive, and styled. Do NOT rewrite or redesign existing UI components. Only wire data fetching layers to the real backend APIs in Phase 6.
4. **Phase 6 Gating Invariant:** You MUST NOT edit or re-wire frontend code in `src/` until Phase 1–5 backend endpoints and unit tests pass with `pytest`.
5. **Hardware Priority:** Prioritize dedicated GPU (`cuda`) for model training and PyTorch tensor operations, with Apple Silicon (`mps`) or `cpu` strictly as fallback.
6. **Offline Data Seeding:** Database seeding MUST read from the local self-contained file `backend/data/seed_reference_profiles.json`. Do NOT attempt remote GDAC FTP calls during automated development.
7. **Captum Saliency Wrapper:** When using Captum's `IntegratedGradients`, you MUST wrap the multi-head Bi-LSTM model with `SingleOutputModelWrapper` as defined in `.ai/ml_spec.md`.
8. **Physical Constraints:** All ocean predictions MUST conform to TEOS-10 static stability ($\frac{\partial\sigma_\theta}{\partial z} \ge 0$). No unphysical density inversions.
9. **Architectural Memory:** If you make an assumption or architectural decision, log it in `.ai/memory.md`.

Refer to the index in `.ai/README.md` for the complete documentation set.
