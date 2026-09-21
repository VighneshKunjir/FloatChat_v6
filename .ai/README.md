# FloatChat AI Context Pack

Welcome to the AI Context Pack for **FloatChat (X-RAG Argo Ocean Profile Forecasting & Explainability System)**. This directory contains the complete technical specification, architectural blueprint, data dictionary, ML specification, API contracts, database schemas, and step-by-step task breakdown for building, running, and deploying the complete production system locally with a CLI coding agent (Claude Code, Gemini CLI, Codex CLI, etc.).

---

## 1. Directory Index

| File | Purpose & Description | Read Priority |
| :--- | :--- | :--- |
| **`README.md`** | This index file, reading order, and autonomous agent work loop | **1** |
| **`prd.md`** | Product requirements, problem statement, user personas, MVP features, user flows, and metrics | **2** |
| **`architecture.md`** | System architecture, tech stack versions, target repo structure, sequence flows, and Docker setup | **3** |
| **`rules.md`** | Strict coding standards, typing rules, API conventions, ML rules, frontend invariants, and DO NOT list | **4** |
| **`design.md`** | UI/UX tokens, Tailwind color palette, typography, chart conventions, and component guidelines | **5** |
| **`data_spec.md`** | Comprehensive oceanographic data dictionary, Argo GDAC NetCDF attributes, preprocessing, and splits | **6** |
| **`ml_spec.md`** | Physics-Informed LSTM + MC Dropout spec, Integrated Gradients XAI, TEOS-10 validation, and artifacts | **7** |
| **`api_contract.md`** | Exhaustive OpenAPI/REST contract, JSON payloads, Pydantic schemas, and TypeScript interfaces | **8** |
| **`database.md`** | PostgreSQL/SQLite schema (DDL & SQLAlchemy ORM), ER relationships, migrations, and seed scripts | **9** |
| **`integration_map.md`** | Precise mapping of every frontend React component to backend endpoints, mocks to remove, and hooks | **10** |
| **`tasks.md`** | Phased, actionable task backlog (Phases 0 to 8) with verifiable checkbox acceptance criteria | **11** |
| **`testing.md`** | Test suite specification (Unit, Physics, API Contract, E2E) with commands and tolerance ranges | **12** |
| **`env_and_setup.md`** | Local environment setup, `.env` definitions, dependency installation, and single-command launch | **13** |
| **`current_state.md`** | Snapshot of what is real, what is mocked, known limitations, and immediate next action | **14** |
| **`memory.md`** | Architectural decisions log, `[DECISION NEEDED]`, `[ASSUMPTION]` tracking, and gotchas | **15** |
| **`changelog.md`** | Historical changelog of development phases and template for future updates | **16** |

---

## 2. Order an Agent Should Read These Files

When a CLI agent initializes a work session on this repository, it MUST execute the reading sequence below:

```
Step 1: .ai/README.md (Understand project structure and work rules)
  └── Step 2: .ai/current_state.md (Check what works and what is mocked)
        └── Step 3: .ai/prd.md & .ai/architecture.md (Understand domain & system boundaries)
              └── Step 4: .ai/rules.md (Internalize constraints and the DO NOT list)
                    └── Step 5: .ai/tasks.md (Pick the next unchecked task)
                          └── Step 6: Specialized spec (.ai/api_contract.md, .ai/database.md, .ai/ml_spec.md, etc.)
```

---

## 3. Autonomous "How to Work" Loop

Every CLI agent working on this project MUST strictly follow this iterative execution loop:

1. **Check State**: Read `.ai/current_state.md` to see the current milestone, known bugs, and the active task.
2. **Select Task**: Open `.ai/tasks.md`. Identify the first unchecked task (`- [ ]`) whose dependencies are satisfied. Do not skip tasks.
3. **Review Specs**: Read the relevant detailed specifications (`.ai/api_contract.md`, `.ai/data_spec.md`, `.ai/ml_spec.md`, or `.ai/integration_map.md`).
4. **Implement**: Write clean, strongly typed, modular code adhering to `.ai/rules.md`. Never rewrite working UI components; only replace data fetching and state layers.
5. **Verify & Test**: Run the acceptance test specified in the task (unit test, curl command, or TypeScript compilation via `npm run lint`).
6. **Update Memory & State**:
   - Check off the completed task in `.ai/tasks.md` (`- [x]`).
   - If you made an architectural decision or assumption, log it in `.ai/memory.md`.
   - Record the commit/milestone in `.ai/changelog.md`.
   - Update `.ai/current_state.md` with the new status and next task.
