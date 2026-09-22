# FloatChat: Testing Strategy & Test Plan

## 1. Overview & Quality Gates
To guarantee operational reliability in scientific oceanography, FloatChat requires a multi-layered verification harness:
1. **Frontend Type & Lint Check:** TypeScript strict compiler verification (`npm run lint`).
2. **Backend Unit & Physics Tests:** `pytest` verifying TEOS-10 thermodynamics, potential density monotonic gradients, and MLD calculations.
3. **ML Inference & UQ Sanity Tests:** Verifying Monte Carlo confidence bounds and Captum attribution convergence.
4. **API Contract Tests:** Verifying JSON payload schemas against `.ai/api_contract.md`.

---

## 2. Testing Commands

```bash
# 1. Frontend TypeScript verification
npm run lint

# 2. Frontend production build test
npm run build

# 3. Backend Unit & Physics test suite
pytest backend/tests/ -v

# 4. API Contract integration test
pytest backend/tests/test_api_contract.py -v

# 5. Physics sanity check (command-line one-liner)
python -c "import gsw; print('GSW TEOS-10 installed and verified:', gsw.__version__)"
```

---

## 3. Core Physics & Unit Tests (`backend/tests/test_physics.py`)

```python
import pytest
import numpy as np
from app.core.physics import (
    compute_potential_density,
    calculate_mld,
    verify_gravitational_stability
)

def test_surface_potential_density_calculation():
    # Warm surface Arabian Sea water (28.5°C, 36.5 PSU)
    sigma = compute_potential_density(temp=28.5, sal=36.5)
    # Expected sigma_theta approx 23.4 to 23.7 kg/m^3
    assert 23.0 <= sigma <= 24.0, f"Surface density {sigma} outside expected range"

def test_gravitational_stability_on_monotonic_profile():
    temps = [28.5, 28.0, 26.0, 22.0, 18.0, 14.0, 11.0, 8.0]
    sals = [36.5, 36.5, 36.2, 35.8, 35.5, 35.3, 35.2, 35.1]
    depths = [5, 20, 50, 100, 150, 250, 500, 1000]
    
    is_stable, violations, min_gradient = verify_gravitational_stability(temps, sals, depths)
    assert is_stable is True
    assert violations == 0
    assert min_gradient >= 0.0

def test_density_inversion_detection():
    # Artificially create a strong unstable density inversion
    temps = [20.0, 28.5] # Cold heavy water sitting on top of warm light water
    sals = [36.5, 35.0]
    depths = [5, 50]
    
    is_stable, violations, min_gradient = verify_gravitational_stability(temps, sals, depths)
    assert is_stable is False
    assert violations >= 1
    assert min_gradient < 0.0

def test_mld_detection():
    # Surface temp 28.0°C down to 40m, then drops sharply at 60m
    temps = [28.0, 28.0, 28.0, 27.9, 25.0, 22.0]
    sals = [36.5, 36.5, 36.5, 36.5, 36.0, 35.8]
    depths = [5, 10, 20, 30, 50, 75]
    
    mld = calculate_mld(temps, sals, depths)
    assert 30 <= mld <= 50, f"Computed MLD {mld} not matching thermocline shoaling"
```

---

## 4. API Contract & Integration Tests (`backend/tests/test_api_contract.py`)

```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "FloatChat" in data["service"]

def test_floats_catalog_endpoint():
    res = client.get("/api/floats")
    assert res.status_code == 200
    floats = res.json()
    assert len(floats) >= 4
    assert any(f["wmo_id"] == "3902114" for f in floats)

def test_forecast_contract_schema():
    payload = {"wmoId": "3902114", "cycle": 92}
    res = client.post("/api/forecast", json=payload)
    assert res.status_code == 200
    data = res.json()
    
    # Required top-level keys matching TypeScript ForecastResult
    required_keys = [
        "forecast_id", "target_float_id", "target_cycle", "predicted_cycle",
        "profiles", "uncertainty_bounds", "physical_diagnostics",
        "xai_attribution", "evidence_citations", "metrics_comparison"
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in forecast response"
        
    assert len(data["profiles"]) == 16, "Profiles must have 16 standard pressure levels"
    assert len(data["uncertainty_bounds"]) == 16
    assert data["physical_diagnostics"]["is_gravitationally_stable"] is True
```

---

## 5. End-to-End Visual Acceptance Criteria
1. **Live Prediction Readout:**
   - Navigating to `http://localhost:3000`.
   - Hovering mouse over SVG chart changes the displayed numbers instantly without lag.
   - Click jump pills (e.g. `[100m]`) sets the active depth to 100 dbar.
2. **Evidence-Link Viewer:**
   - Appears seamlessly at the bottom of the Forecast tab.
   - Shows top 3 GDAC citations with cosine similarity $> 95\%$.
3. **FloatChat Dialogue:**
   - Type *"Explain the predicted salinity at 150 dbar."*
   - Response contains valid LaTeX equations and citations to verified WMO floats.
