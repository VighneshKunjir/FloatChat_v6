# FloatChat: API Contract & Interface Specifications

This document serves as the **single source of truth** between the React frontend and any backend implementation (FastAPI / Node / Express). All fields, types, request bodies, and responses must match this contract exactly.

---

## 1. Summary of Endpoints

| Method | Path | Purpose | Authentication |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Service health, model status, and region metadata | None |
| `GET` | `/api/floats` | List of available Argo floats and active cycles | None |
| `GET` | `/api/profiles/{wmoId}` | All historical vertical profile cycles for a float | None |
| `POST` | `/api/forecast` | Run forward forecast, UQ, TEOS-10, XAI & Evidence-Link | None |
| `POST` | `/api/chat` | Conversational RAG & anti-hallucination Q&A | Optional API Key |
| `POST` | `/api/history` | Log a user forecast query session (New feature) | None |

---

## 2. Detailed Endpoint Specifications

### 2.1 GET `/api/health`
- **Description:** Verifies service health, region bounds, and engine version.
- **Response Schema:**
  ```json
  {
    "status": "ok",
    "service": "FloatChat-XRAG-Forecasting-Engine",
    "region": "Arabian Sea / Northern Indian Ocean",
    "version": "1.2.0-IEEE-Access-Spec"
  }
  ```

---

### 2.2 GET `/api/floats`
- **Description:** Returns the catalog of active floats in the Arabian Sea with base coordinates and cycle lists (returns the 4 reference floats in offline seed mode, or all 30 operational floats across 4 years of cycles when seeded from the canonical dataset).
- **Response Schema:** Array of `FloatSummary`:
  ```json
  [
    {
      "wmo_id": "3902114",
      "name": "Float 3902114 (Northern Arabian Sea / Gulf of Oman)",
      "baseLat": 20.45,
      "baseLon": 62.15,
      "cycles": [85, 86, 87, 88, 89, 90, 91, 92, 93, 94, 95],
      "defaultCycle": 94
    },
    {
      "wmo_id": "2903334",
      "name": "Float 2903334 (Central Arabian Sea Basin)",
      "baseLat": 15.3,
      "baseLon": 65.8,
      "cycles": [120, 121, 122, 123, 124, 125, 126, 127, 128],
      "defaultCycle": 127
    },
    {
      "wmo_id": "1902442",
      "name": "Float 1902442 (Eastern Arabian Sea / Indian West Shelf)",
      "baseLat": 11.2,
      "baseLon": 72.4,
      "cycles": [64, 65, 66, 67, 68, 69, 70, 71],
      "defaultCycle": 70
    },
    {
      "wmo_id": "2902789",
      "name": "Float 2902789 (Southwestern Upwelling Corridor)",
      "baseLat": 8.7,
      "baseLon": 57.9,
      "cycles": [150, 151, 152, 153, 154, 155, 156],
      "defaultCycle": 155
    }
  ]
  ```

---

### 2.3 GET `/api/profiles/{wmoId}`
- **Description:** Retrieves all historical profiles for a given float ID, sorted by cycle number ascending.
- **Path Parameters:** `wmoId` (string, e.g. `3902114`).
- **Response Schema:** Array of `ArgoProfile` (matching `src/types.ts`):
  ```json
  [
    {
      "profile_id": "ARGO_3902114_CYC091",
      "wmo_id": "3902114",
      "float_name": "Argo-3902114 (North Arabian Sea)",
      "platform_type": "PROVOR_CTS4",
      "cycle_number": 91,
      "date": "2024-03-01",
      "latitude": 14.42,
      "longitude": 65.11,
      "sea_region": "Arabian Sea (Northern Indian Ocean)",
      "data_mode": "D",
      "qc_status": "QC_PASS_FLAG_1",
      "raw_netcdf_source": "nodc_D3902114_091.nc",
      "gdac_archive_path": "/ifremer/argo/dac/incois/3902114/profiles/D3902114_091.nc",
      "measurements": [
        { "depth_dbar": 5, "temperature": 28.62, "salinity": 36.42, "qc_temperature": 1, "qc_salinity": 1 },
        { "depth_dbar": 50, "temperature": 27.95, "salinity": 36.51, "qc_temperature": 1, "qc_salinity": 1 },
        { "depth_dbar": 100, "temperature": 23.41, "salinity": 35.91, "qc_temperature": 1, "qc_salinity": 1 },
        { "depth_dbar": 1000, "temperature": 7.42, "salinity": 35.21, "qc_temperature": 1, "qc_salinity": 1 }
      ]
    }
  ]
  ```

---

### 2.4 POST `/api/forecast`
- **Description:** Executes deep sequence forward forecasting with 50-pass Monte Carlo Dropout UQ, TEOS-10 physical diagnostics, Integrated Gradients XAI, and Evidence-Link NetCDF citations.
- **Request Body:**
  ```json
  {
    "wmoId": "3902114",
    "cycle": 92
  }
  ```
- **Response Schema:** `ForecastResult` (matches `src/types.ts`):
  ```json
  {
    "forecast_id": "FC_XRAG_3902114_C92_1740000000000",
    "target_float_id": "3902114",
    "target_cycle": 92,
    "predicted_cycle": 93,
    "forecast_date": "2024-03-11",
    "latitude": 14.52,
    "longitude": 65.23,
    "input_sequence_cycles": [89, 90, 91],
    "profiles": [
      {
        "depth_dbar": 5,
        "temperature_forecast": 28.52,
        "salinity_forecast": 36.45,
        "persistence_temperature": 28.62,
        "persistence_salinity": 36.42,
        "gradient_boosting_temperature": 28.48,
        "gradient_boosting_salinity": 36.41
      },
      {
        "depth_dbar": 100,
        "temperature_forecast": 23.42,
        "salinity_forecast": 35.92,
        "persistence_temperature": 23.41,
        "persistence_salinity": 35.91,
        "gradient_boosting_temperature": 23.28,
        "gradient_boosting_salinity": 35.88
      }
    ],
    "uncertainty_bounds": [
      {
        "depth_dbar": 5,
        "mean_temp": 28.52,
        "std_temp": 0.28,
        "ci90_temp_lower": 28.06,
        "ci90_temp_upper": 28.98,
        "ci95_temp_lower": 27.97,
        "ci95_temp_upper": 29.07,
        "mean_sal": 36.45,
        "std_sal": 0.04,
        "ci90_sal_lower": 36.38,
        "ci90_sal_upper": 36.52,
        "ci95_sal_lower": 36.37,
        "ci95_sal_upper": 36.53
      }
    ],
    "physical_diagnostics": {
      "is_gravitationally_stable": true,
      "min_density_gradient": 0.00312,
      "mixed_layer_depth_m": 40,
      "max_thermocline_gradient": 0.1245,
      "thermocline_depth_m": 100,
      "halocline_depth_m": 150,
      "surface_potential_density": 23.51,
      "deep_potential_density": 27.52,
      "stability_violation_count": 0,
      "density_profile": [
        { "depth_dbar": 5, "sigma_theta": 23.51, "buoyancy_frequency_n2": 0.0 },
        { "depth_dbar": 100, "sigma_theta": 25.14, "buoyancy_frequency_n2": 2.14e-4 }
      ]
    },
    "xai_attribution": {
      "temporal_attribution": [
        {
          "cycle_offset": -1,
          "cycle_label": "Cycle t-1 (Cycle 91)",
          "importance_score": 0.58,
          "interpretation": "Immediate upstream profile dominates pycnocline and mixed-layer boundary conditions."
        },
        {
          "cycle_offset": -2,
          "cycle_label": "Cycle t-2 (Cycle 90)",
          "importance_score": 0.27,
          "interpretation": "Medium-term thermal advection provides mesoscale eddy drift momentum."
        },
        {
          "cycle_offset": -3,
          "cycle_label": "Cycle t-3 (Cycle 89)",
          "importance_score": 0.15,
          "interpretation": "Baseline seasonal stratification trend in the Arabian Sea upper 500 dbar."
        }
      ],
      "depth_attribution_matrix": [
        { "input_depth": 20, "output_depth": 20, "saliency_weight": 0.88 },
        { "input_depth": 20, "output_depth": 75, "saliency_weight": 0.64 }
      ],
      "key_depth_influences": [
        {
          "target_zone": "Thermocline (75 - 150 dbar)",
          "dominant_input_depth": "Surface to 50 dbar heat flux + 100 dbar shear",
          "attribution_percentage": 68.4,
          "scientific_driver": "Surface solar irradiance and wind stress penetration control thermocline shoaling."
        }
      ]
    },
    "evidence_citations": [
      {
        "citation_id": "EVID_CITE_1_3902114_C91",
        "wmo_id": "3902114",
        "cycle_number": 91,
        "date": "2024-03-01",
        "latitude": 14.42,
        "longitude": 65.11,
        "distance_km": 18.5,
        "similarity_score": 0.9984,
        "cosine_profile_sim": 0.9992,
        "spatial_temporal_weight": 0.9908,
        "qc_flag": 1,
        "raw_netcdf_file": "nodc_3902114_prof.nc",
        "provenance_chain": {
          "origin": "Argo Global Data Assembly Centre (GDAC)",
          "archive_gdac": "ftp://ftp.ifremer.fr/ifremer/argo/dac/incois/3902114/profiles/D3902114_091.nc",
          "qc_step": "Delayed-Mode Standard Quality Control Flag 1/2 Verification",
          "standardized_grid": "Standard 10-50 dbar linear depth interpolation"
        },
        "key_feature_relevance": "Primary analogous profile with identical thermocline depth within 18.5 km.",
        "measurements": []
      }
    ],
    "metrics_comparison": [
      {
        "model": "Persistence Baseline (t-1)",
        "profile_rmse": 0.482,
        "profile_mae": 0.331,
        "thermocline_rmse": 0.742,
        "deep_rmse": 0.165,
        "physical_violation_rate": 0.0
      },
      {
        "model": "Gradient Boosting / Ridge",
        "profile_rmse": 0.341,
        "profile_mae": 0.235,
        "thermocline_rmse": 0.528,
        "deep_rmse": 0.118,
        "physical_violation_rate": 1.4
      },
      {
        "model": "FloatChat X-RAG (LSTM + MC Dropout)",
        "profile_rmse": 0.228,
        "profile_mae": 0.154,
        "thermocline_rmse": 0.312,
        "deep_rmse": 0.072,
        "physical_violation_rate": 0.0
      }
    ]
  }
  ```

---

### 2.5 POST `/api/chat`
- **Description:** Conversational RAG assistant grounded strictly in active forecast context and evidence citations.
- **Request Body:**
  ```json
  {
    "query": "What physical processes explain the predicted thermocline temperature at 100 dbar?",
    "wmoId": "3902114",
    "cycle": 92
  }
  ```
- **Response Schema:**
  ```json
  {
    "text": "### FloatChat X-RAG Scientific Forecast Analysis\n\n**1. Depth-Resolved Profile Forecast (Cycle 93)**\n- **Target Float:** WMO 3902114 at 14.52°N, 65.23°E.\n- **Thermocline Dynamics:** At 100 dbar, the temperature is predicted to be **23.42°C**...",
    "citations": ["3902114"],
    "verified": true,
    "forecast_context": { ... }
  }
  ```

---

## 3. Error Codes & Payloads

```json
{
  "error": {
    "code": "BAD_REQUEST",
    "message": "Field 'wmoId' is required and must be a valid 7-digit string.",
    "status": 400
  }
}
```

- `400 BAD_REQUEST`: Missing required fields, invalid cycle number.
- `404 NOT_FOUND`: Requested WMO ID or cycle not in dataset.
- `500 INTERNAL_SERVER_ERROR`: Matrix calculation failure or model inference error.
