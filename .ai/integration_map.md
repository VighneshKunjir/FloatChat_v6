# FloatChat: Frontend-to-Backend Integration Map

This map audits every single user interface component in `src/components/`, detailing its user triggers, current data handling, target API endpoint, database tables, and the exact modifications needed to eliminate all mock/simulated dependencies.

---

## 1. Component Wiring Table

| Page / Component | UI Trigger / Event | Current Behaviour | Target API Endpoint | Backend Service / Method | Database Tables Used | Target Data Shape | Frontend Modification Needed |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **`App.tsx`** | Component mount (`useEffect`) | Calls `GET /api/floats` | `GET /api/floats` | `floats.py:get_all_floats` | `argo_floats`, `argo_profiles` | `FloatSummary[]` | Point fetch to `apiService.getFloats()`. |
| **`ControlBar.tsx`** | Float dropdown changed | Updates `selectedWmo` & triggers `loadForecast` in `App.tsx` | `POST /api/forecast` | `forecast.py:compute_forecast` | `argo_floats`, `argo_profiles`, `profile_levels` | `ForecastResult` | None in component; receives updated props. |
| **`ControlBar.tsx`** | Cycle number selected / changed | Updates `selectedCycle` & triggers `loadForecast` | `POST /api/forecast` | `forecast.py:compute_forecast` | `argo_profiles`, `profile_levels` | `ForecastResult` | None in component. |
| **`ControlBar.tsx`** | "Refresh Forecast" button clicked | Calls `onRefreshForecast()` | `POST /api/forecast` | `forecast.py:compute_forecast` | `argo_profiles`, `profile_levels` | `ForecastResult` | None. |
| **`ProfilePlot.tsx`** | Cursor hovers over SVG canvas | Calculates nearest depth and updates local `activeDepth` state | Client-side reactive | Client-side interpolation from `forecast.profiles` | None (in-memory) | `{ depth_dbar, temp, sal, sigma }` | None; UI is purely reactive to `forecast` prop. |
| **`ProfilePlot.tsx`** | Quick Jump depth button clicked (e.g. `[100m]`) | Sets `activeDepth` to `100` | Client-side reactive | Client-side state | None | None | None. |
| **`EvidenceLinkViewer.tsx`** (Merged into `ProfilePlot`) | Rendered at bottom of forecast tab | Displays `forecast.evidence_citations` | In `POST /api/forecast` response | `evidence.py:match_analogues` | `argo_profiles`, `profile_levels` | `EvidenceCitation[]` | Ensure `raw_netcdf_file` and `gdac_archive_path` match real GDAC conventions. |
| **`ChatPanel.tsx`** | User submits chat query or clicks prompt chip | Posts `{ query, wmoId, cycle }` to `/api/chat` | `POST /api/chat` | `chat.py:scientific_dialogue` | In-memory `forecast` context + optional LLM | `{ text, citations, verified }` | Replace inline fetch with `apiService.sendChatMessage()`. |
| **`TrajectoryMap.tsx`** | Component mount / cycle slider / play drift | Simulates drift offsets using client math | `GET /api/profiles/{wmoId}` | `floats.py:get_float_trajectory` | `argo_profiles` | `Array<{ cycle, lat, lon, date }>` | Connect trajectory polyline directly to real profile GPS fixes from database. |
| **`XaiDiagnostics.tsx`** | Rendered in tab 4 | Visualizes `forecast.xai_attribution` | In `POST /api/forecast` response | `xai.py:compute_integrated_gradients` | None (computed during inference) | `XAIAttribution` | None; reactive to `forecast` prop. |
| **`EvaluationBenchmarks.tsx`** | Rendered in tab 5 | Displays `forecast.metrics_comparison` | In `POST /api/forecast` response | `evaluation.py:get_benchmark_metrics` | None (model metadata) | `ModelMetric[]` | None. |

---

## 2. API Service Layer Specification (`src/services/api.ts`)

To enforce strict separation of concerns, all components and `App.tsx` must delegate HTTP requests to `src/services/api.ts`:

```typescript
// src/services/api.ts
import { ForecastResult, ArgoProfile, ChatMessage } from '../types.ts';

const API_BASE = '/api';

export interface FloatSummary {
  wmo_id: string;
  name: string;
  baseLat: number;
  baseLon: number;
  cycles: number[];
  defaultCycle: number;
}

export interface ChatResponse {
  text: string;
  citations: string[];
  verified: boolean;
  forecast_context?: ForecastResult;
}

export const apiService = {
  async getHealth(): Promise<{ status: string; service: string }> {
    const res = await fetch(`${API_BASE}/health`);
    if (!res.ok) throw new Error(`Health check failed: ${res.statusText}`);
    return res.json();
  },

  async getFloats(): Promise<FloatSummary[]> {
    const res = await fetch(`${API_BASE}/floats`);
    if (!res.ok) throw new Error(`Failed to load floats: ${res.statusText}`);
    return res.json();
  },

  async getProfiles(wmoId: string): Promise<ArgoProfile[]> {
    const res = await fetch(`${API_BASE}/profiles/${wmoId}`);
    if (!res.ok) throw new Error(`Failed to load profiles for ${wmoId}: ${res.statusText}`);
    return res.json();
  },

  async runForecast(wmoId: string, cycle: number): Promise<ForecastResult> {
    const res = await fetch(`${API_BASE}/forecast`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ wmoId, cycle })
    });
    if (!res.ok) throw new Error(`Forecast computation failed: ${res.statusText}`);
    return res.json();
  },

  async sendChatMessage(query: string, wmoId: string, cycle: number): Promise<ChatResponse> {
    const res = await fetch(`${API_BASE}/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ query, wmoId, cycle })
    });
    if (!res.ok) throw new Error(`Chat generation failed: ${res.statusText}`);
    return res.json();
  }
};
```

---

## 3. List of Simulated Mocks to Replace

1. **`server/argoData.ts` In-Memory Map:**
   - *Current:* Hardcoded array of 5 floats and ~30 simulated profiles stored in a TypeScript `Map`.
   - *Replacement:* Read from PostgreSQL/SQLite `argo_floats` and `argo_profiles` tables via SQLAlchemy queries.
2. **`server/forecaster.ts` Hardcoded Perturbations:**
   - *Current:* High-fidelity synthetic formulas with mathematical sine/cosine epistemic perturbations mimicking an LSTM.
   - *Replacement:* Direct PyTorch `model.forward()` inference evaluating the real loaded `.pt` weights.
3. **`server/forecaster.ts` Synthetic Saliency Matrix:**
   - *Current:* Hardcoded saliency weights (`0.88`, `0.64`, `0.94`, etc.).
   - *Replacement:* Captum `IntegratedGradients(model).attribute()` computed dynamically per sequence.
