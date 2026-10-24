import pytest
from app.services.alignment import align_forecast_and_actuals
from app.core.time_utils import generate_settlement_periods_for_date

def test_half_hourly_alignment():
    expected = generate_settlement_periods_for_date("2026-01-01")[:4]
    actuals = [
        {"delivery_time": "2026-01-01T00:00:00Z", "generation_mw": 1000.0, "settlement_period": 1},
        {"delivery_time": "2026-01-01T00:30:00Z", "generation_mw": 1100.0, "settlement_period": 2},
        {"delivery_time": "2026-01-01T01:00:00Z", "generation_mw": 1200.0, "settlement_period": 3},
        # period 4 missing actual
    ]
    forecasts = {
        "2026-01-01T00:00:00Z": {"delivery_time": "2026-01-01T00:00:00Z", "generation_mw": 950.0, "publish_time": "2025-12-31T11:30:00Z", "lead_time_hours": 12.5},
        "2026-01-01T01:00:00Z": {"delivery_time": "2026-01-01T01:00:00Z", "generation_mw": 1150.0, "publish_time": "2025-12-31T11:30:00Z", "lead_time_hours": 13.5},
    }

    aligned = align_forecast_and_actuals(expected, actuals, forecasts, granularity="half_hourly")
    assert len(aligned) == 4
    
    # SP 1
    assert aligned[0]["status"] == "VALID"
    assert aligned[0]["actual_mw"] == 1000.0
    assert aligned[0]["forecast_mw"] == 950.0
    assert aligned[0]["error_mw"] == 50.0
    
    # SP 2 inherits the hourly forecast for 00:00:00Z
    assert aligned[1]["status"] == "VALID"
    assert aligned[1]["actual_mw"] == 1100.0
    assert aligned[1]["forecast_mw"] == 950.0
    assert aligned[1]["error_mw"] == 150.0

    # SP 3
    assert aligned[2]["status"] == "VALID"
    assert aligned[2]["actual_mw"] == 1200.0
    assert aligned[2]["forecast_mw"] == 1150.0

    # SP 4 has missing actual
    assert aligned[3]["status"] == "MISSING_ACTUAL"
    assert aligned[3]["forecast_mw"] == 1150.0
    assert aligned[3]["actual_mw"] is None

def test_hourly_alignment_averaging():
    expected = generate_settlement_periods_for_date("2026-01-01")[:4]
    actuals = [
        {"delivery_time": "2026-01-01T00:00:00Z", "generation_mw": 1000.0, "settlement_period": 1},
        {"delivery_time": "2026-01-01T00:30:00Z", "generation_mw": 1200.0, "settlement_period": 2},
    ]
    forecasts = {
        "2026-01-01T00:00:00Z": {"delivery_time": "2026-01-01T00:00:00Z", "generation_mw": 1050.0, "publish_time": "2025-12-31T11:30:00Z"},
    }

    aligned = align_forecast_and_actuals(expected, actuals, forecasts, granularity="hourly")
    # For hour 00:00-01:00, average actual is (1000 + 1200)/2 = 1100.0
    assert len(aligned) == 2
    h1 = aligned[0]
    assert h1["delivery_time"] == "2026-01-01T00:00:00Z"
    assert h1["actual_mw"] == 1100.0
    assert h1["forecast_mw"] == 1050.0
    assert h1["error_mw"] == 50.0
