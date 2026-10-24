import pytest
import os
from app.core.config import settings
from app.data.database import init_db, get_db_connection
from app.data.repository import (
    upsert_forecasts,
    upsert_actuals,
    get_forecast_records,
    get_actual_records,
    get_cache_stats
)

@pytest.fixture(autouse=True)
def setup_test_db(tmp_path, monkeypatch):
    test_db = str(tmp_path / "test_wind.db")
    monkeypatch.setattr(settings, "DATABASE_PATH", test_db)
    init_db()
    yield

def test_upsert_forecast_deduplication():
    records = [
        {"dataset": "WINDFOR", "publish_time": "2026-01-01T10:00:00Z", "delivery_time": "2026-01-02T12:00:00Z", "generation_mw": 14000.0, "source_status": "OK"},
        {"dataset": "WINDFOR", "publish_time": "2026-01-01T10:00:00Z", "delivery_time": "2026-01-02T12:00:00Z", "generation_mw": 14500.0, "source_status": "REVISED"},
    ]
    upsert_forecasts(records)
    
    # Query back
    stored = get_forecast_records(delivery_from="2026-01-02T12:00:00Z", delivery_to="2026-01-02T12:00:00Z")
    assert len(stored) == 1
    # Updated value persists without duplicate rows
    assert stored[0]["generation_mw"] == 14500.0
    assert stored[0]["source_status"] == "REVISED"

def test_upsert_actual_deduplication():
    records = [
        {"dataset": "FUELHH", "settlement_date": "2026-01-01", "settlement_period": 1, "delivery_time": "2026-01-01T00:00:00Z", "fuel_type": "WIND", "generation_mw": 12000.0},
        {"dataset": "FUELHH", "settlement_date": "2026-01-01", "settlement_period": 1, "delivery_time": "2026-01-01T00:00:00Z", "fuel_type": "WIND", "generation_mw": 12100.0},
    ]
    upsert_actuals(records)
    stored = get_actual_records(date_from="2026-01-01", date_to="2026-01-01")
    assert len(stored) == 1
    assert stored[0]["generation_mw"] == 12100.0

def test_cache_stats_reporting():
    stats_empty = get_cache_stats()
    assert stats_empty["cached_forecast_count"] == 0
    assert stats_empty["cached_actual_count"] == 0

    upsert_forecasts([{"dataset": "WINDFOR", "publish_time": "2026-01-01T10:00:00Z", "delivery_time": "2026-01-02T12:00:00Z", "generation_mw": 14000.0}])
    upsert_actuals([{"dataset": "FUELHH", "settlement_date": "2026-01-01", "settlement_period": 1, "delivery_time": "2026-01-01T00:00:00Z", "fuel_type": "WIND", "generation_mw": 12000.0}])

    stats = get_cache_stats()
    assert stats["cached_forecast_count"] == 1
    assert stats["cached_actual_count"] == 1
    assert stats["available_date_range_actuals"]["min"] == "2026-01-01"
