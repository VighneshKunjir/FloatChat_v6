# Agent Instructions for FloatChat

Welcome to **FloatChat** (Explainable Evidence-Linked Argo Ocean Profile Forecasting & Physics Validation Engine).

## CRITICAL DIRECTIVES FOR CODING AGENTS
1. **First Action:** You MUST read `.ai/README.md` and `.ai/current_state.md` before performing any code generation or modifications.
2. **Work Loop:** Work iteratively through the tasks documented in `.ai/tasks.md`. Select the first unchecked task, implement it according to `.ai/rules.md` and the relevant specifications, run the acceptance test, and update `.ai/tasks.md` and `.ai/current_state.md`.
3. **Preserve Working Frontend:** The React 19 frontend is complete, responsive, and styled. Do NOT rewrite or redesign existing UI components. Only wire data fetching layers to the real backend APIs.
4. **Physical Constraints:** All ocean predictions MUST conform to TEOS-10 static stability ($\frac{\partial\sigma_\theta}{\partial z} \ge 0$). No unphysical density inversions.
5. **Architectural Memory:** If you make an assumption or architectural decision, log it in `.ai/memory.md`.

Refer to the index in `.ai/README.md` for the complete documentation set.
