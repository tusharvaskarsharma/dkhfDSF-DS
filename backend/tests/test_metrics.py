import pytest
import math
from app.services.metrics import calculate_accuracy_metrics, calculate_daily_breakdown

def test_metrics_calculation_hand_verified():
    # Let's craft 4 paired intervals with known values:
    # Pair 1: Actual = 1000, Forecast = 800  -> error = +200, abs = 200, sq = 40000
    # Pair 2: Actual = 2000, Forecast = 2200 -> error = -200, abs = 200, sq = 40000
    # Pair 3: Actual = 1500, Forecast = 1200 -> error = +300, abs = 300, sq = 90000
    # Pair 4: Actual = 2500, Forecast = 2500 -> error = 0,    abs = 0,   sq = 0
    # Sum errors = +200 - 200 + 300 + 0 = 300
    # ME (Bias) = 300 / 4 = 75.0 MW
    # Sum abs errors = 200 + 200 + 300 + 0 = 700
    # MAE = 700 / 4 = 175.0 MW
    # Sum sq errors = 40000 + 40000 + 90000 + 0 = 170000
    # RMSE = sqrt(170000 / 4) = sqrt(42500) = 206.155... -> 206.16 MW
    # Sum actuals = 1000 + 2000 + 1500 + 2500 = 7000
    # WAPE = (700 / 7000) * 100% = 10.0%
    aligned = [
        {"status": "VALID", "actual_mw": 1000.0, "forecast_mw": 800.0, "delivery_time": "2026-01-01T00:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 2000.0, "forecast_mw": 2200.0, "delivery_time": "2026-01-01T00:30:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 1500.0, "forecast_mw": 1200.0, "delivery_time": "2026-01-01T01:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 2500.0, "forecast_mw": 2500.0, "delivery_time": "2026-01-01T01:30:00Z", "settlement_date": "2026-01-01"},
    ]

    metrics = calculate_accuracy_metrics(aligned, expected_count=4)
    assert metrics.valid_pairs_count == 4
    assert metrics.expected_intervals_count == 4
    assert metrics.coverage_pct == 100.0
    assert metrics.bias_mw == 75.0
    assert metrics.mae_mw == 175.0
    assert metrics.rmse_mw == 206.16
    assert metrics.wape_pct == 10.0
    assert "Underpredicted" in metrics.explanation["bias_interpretation"]

def test_zero_actual_denominator_handling():
    aligned = [
        {"status": "VALID", "actual_mw": 0.0, "forecast_mw": 100.0, "delivery_time": "2026-01-01T00:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 0.0, "forecast_mw": 50.0, "delivery_time": "2026-01-01T00:30:00Z", "settlement_date": "2026-01-01"}
    ]
    metrics = calculate_accuracy_metrics(aligned, expected_count=2)
    assert metrics.wape_pct is None
    assert "undefined because total actual generation was zero" in metrics.explanation["wape_note"]

def test_empty_and_missing_intervals():
    aligned = [
        {"status": "MISSING_FORECAST", "actual_mw": 1000.0, "forecast_mw": None, "delivery_time": "2026-01-01T00:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "MISSING_ACTUAL", "actual_mw": None, "forecast_mw": 1200.0, "delivery_time": "2026-01-01T00:30:00Z", "settlement_date": "2026-01-01"},
        {"status": "MISSING_BOTH", "actual_mw": None, "forecast_mw": None, "delivery_time": "2026-01-01T01:00:00Z", "settlement_date": "2026-01-01"},
    ]
    metrics = calculate_accuracy_metrics(aligned, expected_count=4)
    assert metrics.valid_pairs_count == 0
    assert metrics.coverage_pct == 0.0
    assert metrics.mae_mw is None
    assert metrics.rmse_mw is None
    assert metrics.bias_mw is None
    assert metrics.wape_pct is None
    assert metrics.missing_forecast_count == 1
    assert metrics.missing_actual_count == 1

def test_daily_breakdown():
    aligned = [
        {"status": "VALID", "actual_mw": 1000.0, "forecast_mw": 900.0, "delivery_time": "2026-01-01T00:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 2000.0, "forecast_mw": 1900.0, "delivery_time": "2026-01-02T00:00:00Z", "settlement_date": "2026-01-02"},
    ]
    daily = calculate_daily_breakdown(aligned)
    assert len(daily) == 2
    assert daily[0].date == "2026-01-01"
    assert daily[0].mae_mw == 100.0
    assert daily[1].date == "2026-01-02"
    assert daily[1].mae_mw == 100.0

def test_energy_volume_duration_weighting():
    """Verify that MWh is calculated as MW * duration (1.0h for hourly, 0.5h for half-hourly)."""
    aligned = [
        {"status": "VALID", "actual_mw": 2000.0, "forecast_mw": 1500.0, "delivery_time": "2026-01-01T00:00:00Z", "settlement_date": "2026-01-01"},
        {"status": "VALID", "actual_mw": 3000.0, "forecast_mw": 2500.0, "delivery_time": "2026-01-01T01:00:00Z", "settlement_date": "2026-01-01"},
    ]
    # Hourly mode: 2 hours * avg MW
    # sum actual MW = 5000 -> 5000 MWh
    # sum forecast MW = 4000 -> 4000 MWh
    m_hourly = calculate_accuracy_metrics(aligned, expected_count=2, granularity="hourly")
    assert m_hourly.total_actual_mwh == 5000.0
    assert m_hourly.total_forecast_mwh == 4000.0
    assert round(m_hourly.total_actual_mwh - m_hourly.total_forecast_mwh, 2) == 1000.0

    # Half-hourly mode: 2 intervals of 0.5h each
    # sum actual MW = 5000 * 0.5 = 2500 MWh
    # sum forecast MW = 4000 * 0.5 = 2000 MWh
    m_hh = calculate_accuracy_metrics(aligned, expected_count=2, granularity="half_hourly")
    assert m_hh.total_actual_mwh == 2500.0
    assert m_hh.total_forecast_mwh == 2000.0
    assert round(m_hh.total_actual_mwh - m_hh.total_forecast_mwh, 2) == 500.0


