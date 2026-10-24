import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.data.database import init_db
from app.data.fixtures.fixture_loader import load_fixture_data_into_db

@pytest.fixture(autouse=True)
def setup_api_test_env(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_api_wind.db")
    monkeypatch.setattr(settings, "DATABASE_PATH", test_db)
    init_db()
    load_fixture_data_into_db()
    yield

def test_api_health_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "cached_forecast_count" in data
    assert data["cached_forecast_count"] > 0
    assert data["cached_actual_count"] > 0

def test_api_options_endpoint():
    client = TestClient(app)
    resp = client.get("/api/v1/config/options")
    assert resp.status_code == 200
    data = resp.json()
    assert data["default_date_from"] == "2026-01-01"
    assert len(data["available_cutoff_presets"]) > 0

def test_api_evaluation_endpoint():
    client = TestClient(app)
    # Evaluate 2026-01-01 to 2026-01-02 with Day-Ahead 12:00 UTC cutoff
    resp = client.get(
        "/api/v1/evaluation",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-01-02",
            "decision_cutoff": "2025-12-31T12:00:00Z",
            "granularity": "half_hourly",
            "mode": "demo"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["date_from"] == "2026-01-01"
    assert data["date_to"] == "2026-01-02"
    assert "metrics" in data
    metrics = data["metrics"]
    assert metrics["valid_pairs_count"] > 0
    assert metrics["coverage_pct"] > 0
    assert metrics["mae_mw"] is not None
    assert metrics["rmse_mw"] is not None
    assert metrics["bias_mw"] is not None
    assert len(data["intervals"]) == 96 # 2 days * 48 half-hours
    assert len(data["daily_breakdown"]) == 2

def test_api_vintages_endpoint():
    client = TestClient(app)
    target_delivery = "2026-01-01T12:00:00Z"
    resp = client.get(
        "/api/v1/vintages",
        params={
            "delivery_time": target_delivery,
            "decision_cutoff": "2025-12-31T12:00:00Z"
        }
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["delivery_time"] == target_delivery
    assert len(data["vintages"]) > 0
    # There should be an active selected vintage
    selected = [v for v in data["vintages"] if v["is_selected"]]
    assert len(selected) == 1

def test_api_export_csv():
    client = TestClient(app)
    resp = client.get(
        "/api/v1/export",
        params={
            "date_from": "2026-01-01",
            "date_to": "2026-01-01",
            "decision_cutoff": "2025-12-31T12:00:00Z",
            "granularity": "half_hourly"
        }
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    csv_text = resp.text
    assert "delivery_time_utc" in csv_text
    assert "actual_generation_mw" in csv_text
    assert "selected_forecast_mw" in csv_text
    lines = csv_text.strip().split("\n")
    # 1 header + 48 intervals
    assert len(lines) == 49
