# FloatChat: Design System & UI Specification

## 1. Design System Philosophy
FloatChat uses an academic and scientific oceanographic aesthetic: clean, high-contrast, data-dense, and utilitarian. It deliberately rejects generic visual tropes (such as neon gradients or decorative cards) in favor of crisp typography, precise line charts, and informative spatial cartography.

---

## 2. Color Palette & Tokens

### Primary Oceanographic Brand
- **Cyan / Ocean Depth Primary:**
  - `cyan-600` (`#0891b2`): Primary active tab accent, call-to-action buttons, target float markers.
  - `cyan-500` (`#06b6d4`): Forecast temperature curves, active radar sweep indicators.
  - `cyan-400` (`#22d3ee`): Highlights, waypoint halos, high-contrast labels in dark headers.
  - `cyan-50` (`#ecfeff`): Active pill backgrounds, selected item cards.

### Thermodynamic & Haline Semantic Colors
- **Temperature (Thermal / Heat Content):**
  - Line Color: `rose-600` / `red-500` (`#e11d48` / `#ef4444`)
  - Shaded 95% CI Area: `#ef4444` with `0.15` opacity.
  - Thermal Map Layer: Multi-stop gradient `#0284c7` (24°C upwelling) $\to$ `#10b981` $\to$ `#f59e0b` $\to$ `#e11d48` (29.8°C warm pool).
- **Salinity (Haline / Salt Concentration):**
  - Line Color: `blue-600` (`#2563eb`)
  - Shaded 95% CI Area: `#2563eb` with `0.15` opacity.
  - Haline Salinity Core: `#a855f7` (High-salinity ASHSW cores $>36.6\text{ PSU}$).
- **Potential Density ($\sigma_\theta$):**
  - Line Color: `emerald-600` (`#059669`).
- **Baseline Models:**
  - Persistence ($t-1$): `slate-400` (`#94a3b8`), dashed line (`strokeDasharray="4 4"`).
  - Gradient Boosting: `amber-500` (`#f59e0b`), dotted line (`strokeDasharray="2 2"`).

### Structural Neutrals
- **Canvas / App Background:** `slate-100` (`#f1f5f9`).
- **Surface / Card Background:** `white` (`#ffffff`) with `border-slate-200` (`#e2e8f0`).
- **Map & Header Surface:** `slate-900` (`#0f172a`) to `slate-950` (`#020617`).
- **Body Text:** `slate-900` (`#0f172a`) on light; `slate-100` (`#f1f5f9`) on dark.
- **Muted Text:** `slate-500` (`#64748b`) on light; `slate-400` (`#94a3b8`) on dark.

---

## 3. Typography Hierarchy
- **Font Family:** System default sans-serif stack (`font-sans`: `-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif`).
- **Monospace Stack:** `font-mono` (`ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", monospace`) for WMO IDs, cycle numbers, GPS coordinates, depth levels, and numerical values.
- **Sizes & Weights:**
  - App Title: `text-base font-black tracking-tight`
  - Section Headings: `text-sm font-bold text-slate-900`
  - Body Text: `text-xs leading-relaxed text-slate-700`
  - Metadata & Badges: `text-[10px] font-mono font-semibold uppercase`

---

## 4. Layout Geometry & Spacing
- **Container Max Width:** `max-w-7xl mx-auto` (`1280px`).
- **Grid Layouts:**
  - `ProfilePlot.tsx`: 2-column layout on desktop (`lg:grid-cols-2 gap-6`) comparing Temperature and Salinity.
  - `TrajectoryMap.tsx`: 4-column layout (`lg:grid-cols-4 gap-4`) with 3 cols for map stage and 1 col for float telemetry inspector.
  - `ControlBar.tsx`: Responsive flex wrap bar with centered controls and sticky top positioning.
- **Border Radius:**
  - Cards & Panels: `rounded-xl` (`12px`) with `border border-slate-200 shadow-xs`.
  - Buttons & Inputs: `rounded-lg` (`8px`).
  - Badges & Pills: `rounded-full` (`9999px`) or `rounded-md` (`6px`).

---

## 5. UI Components Catalog

### Header (`src/components/Header.tsx`)
- Sticky top bar with dark slate theme (`bg-slate-900 border-b border-slate-800`).
- Left: Logo icon (`Waves`), App Title, Subtitle, and active Float & Cycle badges.
- Navigation: 5-tab button group in exact sequence:
  1. Profile Forecast & UQ
  2. FloatChat
  3. Sea Map
  4. XAI & TEOS-10 Physics
  5. Model Benchmarks

### Control & Query Bar (`src/components/ControlBar.tsx`)
- Floating control strip sitting between Header and Main workspace.
- Float dropdown selector (WMO ID + region name).
- Cycle number selector with jump buttons.
- Variable view selector (`Both`, `Temperature Only`, `Salinity Only`).
- Real-time GPS location chip (`Lat°N, Lon°E`) and "Refresh Forecast" action button.

### Profile Chart & Live Readout (`src/components/ProfilePlot.tsx`)
- Left & Right SVG depth charts ($0\text{ to }1000\text{ dbar}$ depth on inverted vertical axis).
- Shaded confidence interval band with smooth polyline forecast curve.
- Dynamic mouse hover crosshair tracking exact depth coordinate.
- **Live Prediction Readout Box:** Directly above charts, updating in real time on hover with cards for:
  - Temperature (°C) + 95% CI + delta from persistence.
  - Salinity (PSU) + 95% CI + delta from persistence.
  - Potential Density ($\sigma_\theta$) + gravitational stability indicator.
  - Layer classification badge (Mixed Layer, Thermocline, Haline Core, Deep Ocean).
- Quick depth jump pills: `[Surface 5m]`, `[50m]`, `[100m]`, `[200m]`, `[400m]`, `[700m]`, `[1000m]`.
- Merged Evidence-Link Protocol section at the bottom.

### Conversational RAG Panel (`src/components/ChatPanel.tsx`)
- Chat dialogue stream with user and assistant message bubbles.
- Markdown rendering with KaTeX LaTeX math support for oceanographic formulas.
- Verification badge: `Grounding Verified via Evidence-Link Protocol`.
- Quick suggestion chips (e.g. *"Explain 100m thermocline gradient"*, *"Verify TEOS-10 stability"*).

### Hydrographic Sea Map (`src/components/TrajectoryMap.tsx`)
- Cartographic SVG viewport with Bathymetry, SST thermal, and Haline salinity core layers.
- Detailed landmass contours for Western India, Oman, Yemen, and Pakistan.
- Multi-cycle drift trajectory polyline with play/pause drift simulation controls.
- Distance range rings (150 km, 300 km, 450 km) and compass rose.
- Bottom cursor telemetry HUD showing latitude, longitude, estimated depth in meters, and named ocean basin.
