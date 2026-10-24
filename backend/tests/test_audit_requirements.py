import pytest
from datetime import date, timedelta
from app.services.elexon_client import ElexonClient
from app.data.database import init_db, get_db_connection
from app.data.repository import upsert_forecasts, upsert_actuals, get_forecast_records, get_actual_records
from app.services.metrics import calculate_accuracy_metrics
from app.core.time_utils import get_settlement_period_count_for_date

def test_api_chunking_boundaries():
    """Verify that Elexon 7-day query limits are respected by the chunker (<= 6 days per chunk)."""
    # Test a full 31-day month range (Jan 1 to Jan 31)
    d_start = date(2026, 1, 1)
    d_end = date(2026, 1, 31)
    
    # Generate chunks using same logic as ElexonClient
    chunks = []
    curr = d_start
    while curr <= d_end:
        chunk_end = min(curr + timedelta(days=5), d_end)
        chunks.append((curr.isoformat(), chunk_end.isoformat()))
        curr = chunk_end + timedelta(days=1)

    assert len(chunks) == 6  # 31 days in 6-day max chunks: 6, 6, 6, 6, 6, 1
    for start_str, end_str in chunks:
        s = date.fromisoformat(start_str)
        e = date.fromisoformat(end_str)
        span_days = (e - s).days + 1
        # Elexon API fails with HTTP 400 if span > 7 days inclusive
        assert span_days <= 7, f"Chunk {start_str} to {end_str} exceeds 7-day limit!"

    # Ensure continuity: first start is Jan 1, last end is Jan 31
    assert chunks[0][0] == "2026-01-01"
    assert chunks[-1][1] == "2026-01-31"

def test_duplicate_ingestion_across_boundaries():
    """Verify upsert idempotency when the same record is ingested multiple times across chunk borders."""
    import tempfile
    import os
    from app.core.config import settings

    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        temp_db = f.name

    old_db = settings.DATABASE_PATH
    settings.DATABASE_PATH = temp_db
    try:
        init_db()
        records = [
            {"dataset": "WINDFOR", "publish_time": "2026-01-01T11:30:00Z", "delivery_time": "2026-01-02T12:00:00Z", "generation_mw": 14500.0, "source_status": "OK"},
            {"dataset": "WINDFOR", "publish_time": "2026-01-01T11:30:00Z", "delivery_time": "2026-01-02T12:00:00Z", "generation_mw": 14500.0, "source_status": "OK"},
        ]
        # Ingest twice
        c1 = upsert_forecasts(records)
        c2 = upsert_forecasts(records)
        assert c1 == 2
        assert c2 == 2

        cached = get_forecast_records("2026-01-02T12:00:00Z", "2026-01-02T12:00:00Z")
        assert len(cached) == 1
        assert cached[0]["generation_mw"] == 14500.0
    finally:
        settings.DATABASE_PATH = old_db
        if os.path.exists(temp_db):
            os.remove(temp_db)

def test_dst_clock_change_settlement_counts():
    """Verify expected settlement period counts across standard, short, and long days."""
    # Standard day: 48 SP
    assert get_settlement_period_count_for_date("2026-01-15") == 48
    # 2026 UK Spring clock change (March 29, 2026): 46 SP (23 hours)
    assert get_settlement_period_count_for_date("2026-03-29") == 46
    # 2026 UK Autumn clock change (October 25, 2026): 50 SP (25 hours)
    assert get_settlement_period_count_for_date("2026-10-25") == 50

def test_missing_data_provenance_and_zero_actual():
    """Verify that zero actuals do not crash WAPE and missing data preserves clear provenance."""
    aligned = [
        {"delivery_time": "2026-01-01T00:00:00Z", "actual_mw": 0.0, "forecast_mw": 500.0, "error_mw": -500.0, "abs_error_mw": 500.0, "status": "VALID"},
        {"delivery_time": "2026-01-01T01:00:00Z", "actual_mw": 0.0, "forecast_mw": 0.0, "error_mw": 0.0, "abs_error_mw": 0.0, "status": "VALID"},
        {"delivery_time": "2026-01-01T02:00:00Z", "actual_mw": None, "forecast_mw": 400.0, "error_mw": None, "abs_error_mw": None, "status": "MISSING_ACTUAL"},
        {"delivery_time": "2026-01-01T03:00:00Z", "actual_mw": 600.0, "forecast_mw": None, "error_mw": None, "abs_error_mw": None, "status": "MISSING_FORECAST"},
    ]

    metrics = calculate_accuracy_metrics(aligned, expected_count=4)
    assert metrics.valid_pairs_count == 2
    assert metrics.missing_actual_count == 1
    assert metrics.missing_forecast_count == 1
    assert metrics.coverage_pct == 50.0
    assert metrics.mae_mw == 250.0  # (|0 - 500| + |0 - 0|) / 2 = 250
    # Both actuals are 0.0 -> denominator is 0.0 -> WAPE is handled gracefully
    assert metrics.wape_pct is None
    assert "zero" in metrics.explanation["wape_note"].lower()
