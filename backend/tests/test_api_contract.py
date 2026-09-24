"""API contract tests per .ai/testing.md section 4."""
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


def test_profiles_endpoint():
    res = client.get("/api/profiles/3902114")
    assert res.status_code == 200
    profiles = res.json()
    assert len(profiles) >= 1
    assert profiles[0]["wmo_id"] == "3902114"


def test_forecast_contract_schema():
    payload = {"wmoId": "3902114", "cycle": 92}
    res = client.post("/api/forecast", json=payload)
    assert res.status_code == 200
    data = res.json()

    required_keys = [
        "forecast_id", "target_float_id", "target_cycle", "predicted_cycle",
        "profiles", "uncertainty_bounds", "physical_diagnostics",
        "xai_attribution", "evidence_citations", "metrics_comparison",
    ]
    for key in required_keys:
        assert key in data, f"Missing required key '{key}' in forecast response"

    assert len(data["profiles"]) == 16, "Profiles must have 16 standard pressure levels"
    assert len(data["uncertainty_bounds"]) == 16
    assert data["physical_diagnostics"]["is_gravitationally_stable"] is True


def test_chat_endpoint_grounded():
    payload = {"query": "What is the temperature at 100 dbar?", "wmoId": "3902114", "cycle": 92}
    res = client.post("/api/chat", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert data["verified"] is True
    assert len(data["citations"]) >= 1
