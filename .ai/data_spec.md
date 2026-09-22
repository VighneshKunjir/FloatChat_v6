# FloatChat: Oceanographic Data Specification

## 1. Problem Formulation & Prediction Target
- **Problem Type:** Multi-output Sequence-to-Vector Regression with Physical Constraints.
- **Inputs:** A time series of $K=3$ consecutive historical Argo vertical profile cycles for a specific float:
  $$\mathbf{X} = [\mathbf{P}_{t-3}, \mathbf{P}_{t-2}, \mathbf{P}_{t-1}]$$
  Each profile $\mathbf{P}_i$ contains Temperature and Salinity values sampled at $D=16$ standardized pressure levels, plus metadata $(\text{lat}, \text{lon}, \text{day\_of\_year})$.
- **Target Variables:**
  1. Forward Temperature Profile at cycle $t$: $\hat{\mathbf{T}}_t \in \mathbb{R}^{16}$ in degrees Celsius ($^\circ\text{C}$). Range: $[3.0^\circ\text{C}, 32.0^\circ\text{C}]$.
  2. Forward Salinity Profile at cycle $t$: $\hat{\mathbf{S}}_t \in \mathbb{R}^{16}$ in Practical Salinity Units (PSU). Range: $[34.0, 37.2\text{ PSU}]$.

---

## 2. Standardized Vertical Discretization Grid
Argo floats collect raw measurements at irregular vertical intervals (every 2–10 dbar in the upper water column and 20–50 dbar at depth). For machine learning input and visualization, all profiles are mapped onto the **16 Standard Oceanographic Depths (dbar)** used throughout the FloatChat frontend and server:

| Index | Pressure / Depth (`depth_dbar`) | Oceanographic Layer Classification | Physical Characteristics |
| :---: | :---: | :--- | :--- |
| **0** | `5` | Surface Mixed Layer | Direct atmospheric air-sea heat flux & wind forcing |
| **1** | `20` | Surface Mixed Layer | Upper isothermal layer & momentum boundary |
| **2** | `50` | Upper Thermocline | Seasonal pycnocline initiation |
| **3** | `75` | Main Thermocline | Rapid temperature drop; high acoustic sound velocity gradient |
| **4** | `100` | Main Thermocline Core | Maximum vertical temperature gradient $|dT/dz|$ |
| **5** | `150` | Subsurface Haline Core | Arabian Sea High Salinity Water (ASHSW) / Red Sea outflow |
| **6** | `200` | Subsurface Transition | Base of seasonal wind-driven gyre |
| **7** | `250` | Intermediate Waters | Persian Gulf Water (PGW) intrusion layer |
| **8** | `300` | Intermediate Waters | Oxygen Minimum Zone (OMZ) core |
| **9** | `400` | Deep Thermocline | Permanent oceanic thermocline base |
| **10** | `500` | Deep Intermediate Water | Slow baroclinic geostrophic flow |
| **11** | `600` | Deep Intermediate Water | Low high-frequency turbulence |
| **12** | `700` | Lower Mesopelagic | Stable intermediate salinity boundary |
| **13** | `800` | Bathypelagic Transition | Quasi-homogeneous cold deep ocean water |
| **14** | `900` | Bathypelagic Core | Abyssal thermal consistency |
| **15** | `1000` | Abyssal Parking Depth | Argo parking depth; cold, stable, high hydrostatic pressure |

---

## 3. Data Dictionary

### Model & Feature Attributes

| Field Name (`snake_case`) | TypeScript Match | Type | Unit | Range / Values | Source / Input | Description |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| `wmo_id` | `wmo_id` | `string` | - | 7-digit numeric string | `ControlBar` dropdown | Official WMO platform identifier of the Argo float |
| `cycle_number` | `cycle_number` | `integer` | - | $1 \le c \le 400$ | `ControlBar` cycle select | Profiling cycle number of the float (10-day period) |
| `date` | `date` | `string` | ISO 8601 | YYYY-MM-DD | NetCDF header | Observation timestamp |
| `latitude` | `latitude` | `float` | °N | $6.0 \le \text{lat} \le 26.0$ | GPS / NetCDF | Latitude in Arabian Sea basin |
| `longitude` | `longitude` | `float` | °E | $53.0 \le \text{lon} \le 79.0$ | GPS / NetCDF | Longitude in Arabian Sea basin |
| `depth_dbar` | `depth_dbar` | `integer` | dbar | 16 discrete levels | Standard grid | Hydrostatic pressure level (approximately depth in meters) |
| `temperature` | `temperature` | `float` | °C | $3.0 \le T \le 32.0$ | In-situ CTD sensor | Measured or predicted in-situ temperature |
| `salinity` | `salinity` | `float` | PSU | $34.0 \le S \le 37.2$ | In-situ CTD sensor | Measured or predicted practical salinity |
| `qc_temperature` | `qc_temperature` | `integer` | flag | `1` (Good) or `2` (Probably Good) | NetCDF QC flag | Argo delayed-mode quality control flag |
| `qc_salinity` | `qc_salinity` | `integer` | flag | `1` (Good) or `2` (Probably Good) | NetCDF QC flag | Argo delayed-mode quality control flag |
| `raw_netcdf_source` | `raw_netcdf_source` | `string` | - | e.g. `nodc_3902114_prof.nc` | GDAC archive | Filename of the source Argo NetCDF data product |
| `gdac_archive_path` | `gdac_archive_path` | `string` | URI | `/coriolis/dac/incois/...` | GDAC repository | File path in the global Argo data repository |

---

## 4. Derived & Engineered Physical Features
1. **Potential Density ($\sigma_\theta$):**
   - Computed via the TEOS-10 standard:
     $$\sigma_\theta = \rho(S, T, p=0) - 1000\text{ kg/m}^3$$
   - Approximated in the browser and exact in Python via `gsw.sigma0(SA, CT)`.
2. **Static Gravitational Stability ($\partial\sigma_\theta / \partial z$):**
   - The vertical density derivative between adjacent discrete levels:
     $$\frac{\Delta \sigma_\theta}{\Delta z} = \frac{\sigma_\theta(z_i) - \sigma_\theta(z_{i-1})}{z_i - z_{i-1}}$$
   - Physical stability requires $\frac{\Delta \sigma_\theta}{\Delta z} \ge 0$.
3. **Brunt-Väisälä Buoyancy Frequency Squared ($N^2$):**
   $$N^2 = \frac{g}{\rho_0} \frac{\partial \rho}{\partial z} \approx \frac{9.81}{1025} \frac{\Delta \sigma_\theta}{\Delta z} \quad [\text{s}^{-2}]$$
4. **Mixed Layer Depth (MLD):**
   - The depth where potential density exceeds the surface density by a threshold of $\Delta \sigma_\theta = 0.03\text{ kg/m}^3$:
     $$\text{MLD} = \min \{ z \mid \sigma_\theta(z) - \sigma_\theta(5\text{ dbar}) \ge 0.03\text{ kg/m}^3 \}$$
5. **Maximum Thermocline Gradient:**
   $$\max_{z} \left| \frac{\Delta T}{\Delta z} \right| \quad [^\circ\text{C/dbar}]$$

---

## 5. Dataset Acquisition & Seeding Strategy

### Primary Default for Local Development: Self-Contained Offline Seed
To ensure 100% offline reliability (avoiding remote FTP timeouts, firewall blocks, or network latency during local development), FloatChat uses a **self-contained embedded reference dataset**:
- **Seed File Path:** `backend/data/seed_reference_profiles.json`
- **Contents:** Full historical trajectories and vertical profile cycles for the 4 operational Arabian Sea reference floats:
  - `3902114` (Northern Arabian Sea / Gulf of Oman - 11 cycles [85–95], default 94)
  - `2903334` (Central Arabian Sea Basin - 9 cycles [120–128], default 127)
  - `1902442` (Eastern Arabian Sea / Indian West Shelf - 8 cycles [64–71], default 70)
  - `2902789` (Southwestern Upwelling Corridor - 7 cycles [150–156], default 155)
- **Ingestion Time:** `python backend/scripts/seed_db.py` parses this JSON file and populates the SQLite/PostgreSQL database in $< 2$ seconds.
- **Embedded Seed Schema (`seed_reference_profiles.json`):**
  ```json
  [
    {
      "wmo_id": "3902114",
      "name": "Float 3902114 (Northern Arabian Sea / Gulf of Oman)",
      "baseLat": 20.45,
      "baseLon": 62.15,
      "baseSST": 28.8,
      "baseSSS": 36.45,
      "startDate": "2024-04-10",
      "cycles": [85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95],
      "defaultCycle": 94,
      "profiles": [
        {
          "profile_id": "ARGO_3902114_CYC092",
          "cycle_number": 92,
          "date": "2024-05-20",
          "latitude": 20.85,
          "longitude": 62.91,
          "qc_status": "QC_PASS_FLAG_1",
          "data_mode": "D",
          "raw_netcdf_source": "nodc_D3902114_092.nc",
          "gdac_archive_path": "/ifremer/argo/dac/incois/3902114/profiles/D3902114_092.nc",
          "levels": [
            { "depth_dbar": 5, "temperature": 28.52, "salinity": 36.45, "qc_temperature": 1, "qc_salinity": 1 },
            { "depth_dbar": 100, "temperature": 23.42, "salinity": 35.92, "qc_temperature": 1, "qc_salinity": 1 },
            { "depth_dbar": 1000, "temperature": 7.42, "salinity": 35.21, "qc_temperature": 1, "qc_salinity": 1 }
          ]
        }
      ]
    }
  ]
  ```

### Scaling Pipeline: 30 Floats NetCDF Acquisition & Processing
For production training with realistic ocean physics and statistical generalization, the pipeline scales from the 4-float embedded seed to a full **30-float 4-year historical dataset** from the Argo GDAC:
- **Download Script:** `backend/scripts/download_argo.py`
  - Targets 30 operational Arabian Sea floats with extensive delayed-mode histories (e.g. INCOIS/Coriolis mirrors).
  - Downloads aggregated single NetCDF files per float (`<WMO_ID>_prof.nc`) rather than hundreds of single-cycle files.
  - Required NetCDF attributes extracted:
    - Identifiers & Temporal: `wmo_id` (Float ID), `cycle_number`, `juld` (converted from days since 1950-01-01 to ISO date)
    - Geospatial: `latitude`, `longitude`
    - Physical: Hydrostatic pressure in decibars (`PRES_ADJUSTED` or `PRES`), in-situ temperature (`TEMP_ADJUSTED` or `TEMP`), practical salinity (`PSAL_ADJUSTED` or `PSAL`)
    - Quality Flags: `TEMP_QC`, `PSAL_QC`, `PRES_QC`, `POSITION_QC`
    - Metadata: `DATA_MODE` (`D` / `A` preferred over `R`), `DIRECTION` (ascending `'A'` only)
- **Cleaning & Discretization Rules:**
  1. **Mask Missing Values:** Convert Argo fill value sentinels (`99999.0` / `9999.0`) to `NaN`.
  2. **QC Flag Filtering:** Retain only measurements with QC flags `1` (Good) or `2` (Probably Good).
  3. **Physical Range Bounds:** Filter out sensor spikes ($T \in [-2.0, 35.0]^\circ\text{C}$, $S \in [30.0, 42.0]\text{ PSU}$).
  4. **Vertical Interpolation:** Linear or Akima spline interpolation onto canonical 16-level pressure grid (`[5, 20, 50, 75, 100, 150, 200, 250, 300, 400, 500, 600, 700, 800, 900, 1000] dbar`). Profiles not reaching at least 850 dbar are discarded to avoid artificial extrapolation.
  5. **Deduplication:** Remove duplicate cycles by retaining the delayed-mode (`D`) version.
- **Processed Tabular Matrix (Wide Format CSV):**
  - Saved to: `backend/data/processed/argo_30floats_canonical.csv`
  - Shape: One row per (float, cycle) containing:
    `wmo_id, cycle_number, date, latitude, longitude, temp_5, temp_20, ..., temp_1000, sal_5, sal_20, ..., sal_1000, qc_temp_5, ..., qc_sal_1000`
  - Enables instant $O(1)$ windowing of 3 consecutive historical cycles for LSTM sequences without costly relational joins.

---

## 6. Preprocessing & Partitioning Pipeline
1. **Raw NetCDF Ingestion:** Read `PRES_ADJUSTED`, `TEMP_ADJUSTED`, and `PSAL_ADJUSTED` using Python `xarray` / `netCDF4`.
2. **Akima Spline / Linear Interpolation:** Map irregular pressure observations onto the 16 standard pressure levels.
3. **Temporal Sequencing:** Group profiles by `wmo_id` ordered by `cycle_number`. Construct sliding windows of length $L=4$ (3 input cycles $\to$ 1 target cycle).
4. **Standard Scaling:**
   - Fit `StandardScaler` on the training partition only.
   - Save scalers as `backend/app/ml/artifacts/preprocessor.joblib`.
5. **Data Split (No Leakage):**
   - **Spatial Partition:** 21 floats for training, 4–5 held-out floats for validation, and 4–5 completely unseen floats for spatial generalization testing.
   - **Temporal Partition:** For training floats, the final 10 cycles are held out as an operational temporal forecast benchmark ($t-3, t-2, t-1 \to t$).

