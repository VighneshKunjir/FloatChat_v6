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
Argo floats collect raw measurements at irregular vertical intervals (every 2–10 dbar in the upper water column and 20–50 dbar at depth). For machine learning input and visualization, all profiles are mapped onto the **16 Standard Oceanographic Depths (dbar)** used throughout the FloatChat frontend:

| Index | Pressure / Depth (`depth_dbar`) | Oceanographic Layer Classification | Physical Characteristics |
| :---: | :---: | :--- | :--- |
| **0** | `5` | Surface Mixed Layer | Direct atmospheric air-sea heat flux & wind forcing |
| **1** | `10` | Surface Mixed Layer | Diurnal warming layer |
| **2** | `20` | Surface Mixed Layer | Upper isothermal layer |
| **3** | `30` | Surface Mixed Layer | Wind-stirred mixed layer base in summer |
| **4** | `50` | Upper Thermocline / Barrier Layer | Seasonal pycnocline initiation |
| **5** | `75` | Main Thermocline | Rapid temperature drop; high acoustic sound velocity gradient |
| **6** | `100` | Main Thermocline Core | Maximum vertical temperature gradient $\|dT/dz\|$ |
| **7** | `125` | Lower Thermocline | Subsurface salinity maximum inflection |
| **8** | `150` | Subsurface Haline Core | Arabian Sea High Salinity Water (ASHSW) / Red Sea outflow |
| **9** | `200` | Subsurface Transition | Base of seasonal wind-driven gyre |
| **10** | `250` | Intermediate Waters | Persian Gulf Water (PGW) intrusion layer |
| **11** | `300` | Intermediate Waters | Oxygen Minimum Zone (OMZ) core |
| **12** | `400` | Deep Thermocline | Permanent oceanic thermocline base |
| **13** | `500` | Deep Intermediate Water | Slow baroclinic geostrophic flow |
| **14** | `700` | Deep Intermediate Water | Low high-frequency turbulence |
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

## 5. Dataset Acquisition & Sources

### Primary Real-World Source
- **Argo Global Data Assembly Centre (GDAC):**
  - FTP/HTTP mirrors:
    - US GODAE: `ftp://usgodae.org/pub/outgoing/argo/`
    - Coriolis (IFREMER): `ftp://ftp.ifremer.fr/ifremer/argo/dac/`
  - Regional Focus: **Indian Ocean National Data Centre (INCOIS)**. DAC directory: `dac/incois/`.
  - Target Arabian Sea WMO IDs available in current mock:
    - `3902114` (Central Arabian Basin - 94 cycles)
    - `2902084` (Northern Arabian Sea / Gulf of Oman slope - 88 cycles)
    - `2902266` (Southwestern Arabian Sea Upwelling zone - 76 cycles)
    - `2902123` (Eastern Arabian Sea / Lakshadweep Sea - 110 cycles)
    - `2902099` (Gulf of Aden entrance - 65 cycles)

### Quality Filtering Rules
1. Retain only profiles where `DATA_MODE == 'D'` (Delayed-Mode) or real-time profiles with `TEMP_QC == '1'` and `PSAL_QC == '1'`.
2. Discard profiles missing depth levels deeper than 800 dbar.
3. Reject profiles exhibiting density inversions $> 0.05\text{ kg/m}^3$ in the raw unadjusted data.

---

## 6. Preprocessing & Partitioning Pipeline
1. **Raw NetCDF Ingestion:** Read `PRES_ADJUSTED`, `TEMP_ADJUSTED`, and `PSAL_ADJUSTED` using Python `xarray` / `netCDF4`.
2. **Akima Spline / Linear Interpolation:** Map irregular pressure observations onto the 16 standard pressure levels.
3. **Temporal Sequencing:** Group profiles by `wmo_id` ordered by `cycle_number`. Construct sliding windows of length $L=4$ (3 input cycles $\to$ 1 target cycle).
4. **Standard Scaling:**
   - Fit `StandardScaler` on the training partition only.
   - Save scalers as `backend/app/ml/artifacts/preprocessor.joblib`.
5. **Data Split (No Leakage):**
   - **Training Set (70%):** All cycles for 70% of floats in the Arabian Sea.
   - **Validation Set (15%):** Held-out floats for hyperparameter tuning.
   - **Test Set (15%):** Completely unseen floats evaluating spatial and seasonal generalization.
