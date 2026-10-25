import pytest
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

from app.core.config import settings
from app.core.time_utils import format_utc_iso, parse_utc_iso
from app.data.database import init_db
from app.data.repository import get_forecast_records
from app.services.elexon_client import ElexonClient, ElexonClientError


@pytest.fixture
def clean_db(tmp_path, monkeypatch):
    """Provide an isolated, initialized test SQLite database."""
    test_db = str(tmp_path / "test_windfor_ingestion.db")
    monkeypatch.setattr(settings, "DATABASE_PATH", test_db)
    init_db()
    return test_db


@pytest.mark.anyio
async def test_record_exactly_at_chunk_boundary(clean_db, monkeypatch):
    """
    1. Verify that a forecast record published exactly at a chunk boundary is
    captured without gaps and deduplicated across overlapping chunk queries.
    """
    client = ElexonClient()

    # Query an 8-day window: Chunk 1 = Days 0..5, Chunk 2 = Days 5..8
    t_start = "2026-01-01T00:00:00Z"
    t_boundary = "2026-01-06T00:00:00Z"  # exactly 5 days later
    t_end = "2026-01-09T00:00:00Z"

    # The boundary record is returned by BOTH Chunk 1 and Chunk 2 (inclusive boundary)
    boundary_record = {
        "publishTime": t_boundary,
        "startTime": "2026-01-06T12:00:00Z",
        "generation": 12500.5
    }

    chunk1_params = {"publishDateTimeFrom": t_start, "publishDateTimeTo": t_boundary}
    chunk2_params = {"publishDateTimeFrom": t_boundary, "publishDateTimeTo": t_end}

    captured_requests = []

    async def mock_request(url, params):
        captured_requests.append(dict(params))
        if params["publishDateTimeTo"] == t_boundary:
            # Chunk 1 returns boundary record + earlier record
            return {
                "data": [
                    {"publishTime": "2026-01-03T12:00:00Z", "startTime": "2026-01-04T00:00:00Z", "generation": 11000.0},
                    boundary_record
                ]
            }
        else:
            # Chunk 2 returns boundary record + later record
            return {
                "data": [
                    boundary_record,
                    {"publishTime": "2026-01-08T00:00:00Z", "startTime": "2026-01-08T12:00:00Z", "generation": 13000.0}
                ]
            }

    monkeypatch.setattr(client, "_request_with_retry", mock_request)

    records = await client.fetch_windfor_forecasts(t_start, t_end)

    # Verify query parameters for both chunks meet seamlessly at t_boundary
    assert len(captured_requests) == 2
    assert captured_requests[0] == chunk1_params
    assert captured_requests[1] == chunk2_params

    # Verify boundary record is in memory exactly once
    boundary_in_memory = [
        r for r in records
        if r["publish_time"] == t_boundary and r["delivery_time"] == "2026-01-06T12:00:00Z"
    ]
    assert len(boundary_in_memory) == 1
    assert boundary_in_memory[0]["generation_mw"] == 12500.5

    # Total distinct records returned in memory: 3
    assert len(records) == 3

    # Verify database persistence: exactly 1 row for boundary record
    db_records = get_forecast_records()
    assert len(db_records) == 3
    db_boundary = [
        r for r in db_records
        if r["publish_time"] == t_boundary and r["delivery_time"] == "2026-01-06T12:00:00Z"
    ]
    assert len(db_boundary) == 1
    assert db_boundary[0]["generation_mw"] == 12500.5


@pytest.mark.anyio
async def test_records_immediately_before_and_after_boundary(clean_db, monkeypatch):
    """
    2. Verify records 1 second before, exactly at, and 1 second after chunk boundary
    are all captured without omission or duplication.
    """
    client = ElexonClient()

    t_start = "2026-01-01T00:00:00Z"
    t_boundary = "2026-01-06T00:00:00Z"
    t_end = "2026-01-08T00:00:00Z"

    rec_before = {
        "publishTime": "2026-01-05T23:59:59Z",  # 1s before boundary
        "startTime": "2026-01-06T01:00:00Z",
        "generation": 10100.0
    }
    rec_at = {
        "publishTime": "2026-01-06T00:00:00Z",  # exactly at boundary
        "startTime": "2026-01-06T02:00:00Z",
        "generation": 10200.0
    }
    rec_after = {
        "publishTime": "2026-01-06T00:00:01Z",  # 1s after boundary
        "startTime": "2026-01-06T03:00:00Z",
        "generation": 10300.0
    }

    async def mock_request(url, params):
        if params["publishDateTimeTo"] == t_boundary:
            # Chunk 1: includes before and boundary
            return {"data": [rec_before, rec_at]}
        else:
            # Chunk 2: includes boundary and after
            return {"data": [rec_at, rec_after]}

    monkeypatch.setattr(client, "_request_with_retry", mock_request)

    records = await client.fetch_windfor_forecasts(t_start, t_end)

    # In-memory returned records should contain all three without duplicates
    assert len(records) == 3
    publish_times = {r["publish_time"]: r["generation_mw"] for r in records}
    assert publish_times["2026-01-05T23:59:59Z"] == 10100.0
    assert publish_times["2026-01-06T00:00:00Z"] == 10200.0
    assert publish_times["2026-01-06T00:00:01Z"] == 10300.0

    # In database: exact 3 rows
    db_records = get_forecast_records()
    assert len(db_records) == 3
    db_times = {r["publish_time"]: r["generation_mw"] for r in db_records}
    assert db_times == publish_times


@pytest.mark.anyio
async def test_multiple_consecutive_chunks_coverage(clean_db, monkeypatch):
    """
    3. Verify that multiple consecutive chunks (e.g. 14 days = 3 chunks)
    maintain seamless continuity from start to finish.
    """
    client = ElexonClient()

    t_start = "2026-01-01T00:00:00Z"
    t_end = "2026-01-14T00:00:00Z"  # 13 days = 3 chunks (5d + 5d + 3d)

    expected_intervals = [
        ("2026-01-01T00:00:00Z", "2026-01-06T00:00:00Z"),
        ("2026-01-06T00:00:00Z", "2026-01-11T00:00:00Z"),
        ("2026-01-11T00:00:00Z", "2026-01-14T00:00:00Z")
    ]

    actual_queries = []

    async def mock_request(url, params):
        actual_queries.append((params["publishDateTimeFrom"], params["publishDateTimeTo"]))
        # Return a record for this chunk
        p_from = params["publishDateTimeFrom"]
        return {
            "data": [
                {
                    "publishTime": p_from,
                    "startTime": "2026-01-15T00:00:00Z",
                    "generation": 5000.0
                }
            ]
        }

    monkeypatch.setattr(client, "_request_with_retry", mock_request)

    records = await client.fetch_windfor_forecasts(t_start, t_end)

    # Verify query sequence matches expected adjacent slices
    assert actual_queries == expected_intervals

    # Verify start of first chunk matches requested start, end of last matches requested end
    assert actual_queries[0][0] == t_start
    assert actual_queries[-1][1] == t_end

    # Verify seamless contiguous chain without gaps
    for i in range(len(actual_queries) - 1):
        assert actual_queries[i][1] == actual_queries[i + 1][0]


@pytest.mark.anyio
async def test_reingesting_same_interval_is_idempotent(clean_db, monkeypatch):
    """
    4. Verify re-ingesting the same interval is idempotent, updates values cleanly,
    and produces no duplicate rows in SQLite.
    """
    client = ElexonClient()

    t_start = "2026-01-01T00:00:00Z"
    t_end = "2026-01-07T00:00:00Z"

    # Initial run data
    v1_data = {
        "data": [
            {"publishTime": "2026-01-02T12:00:00Z", "startTime": "2026-01-03T12:00:00Z", "generation": 12000.0},
            {"publishTime": "2026-01-06T00:00:00Z", "startTime": "2026-01-07T00:00:00Z", "generation": 15000.0}
        ]
    }

    async def mock_request_v1(url, params):
        return v1_data

    monkeypatch.setattr(client, "_request_with_retry", mock_request_v1)

    r1 = await client.fetch_windfor_forecasts(t_start, t_end)
    assert len(r1) == 2

    db_rows_1 = get_forecast_records()
    assert len(db_rows_1) == 2
    assert db_rows_1[0]["generation_mw"] in [12000.0, 15000.0]

    # Re-ingest with updated revised generation value for the same forecast run
    v2_data = {
        "data": [
            {"publishTime": "2026-01-02T12:00:00Z", "startTime": "2026-01-03T12:00:00Z", "generation": 12500.0},
            {"publishTime": "2026-01-06T00:00:00Z", "startTime": "2026-01-07T00:00:00Z", "generation": 15500.0}
        ]
    }

    async def mock_request_v2(url, params):
        return v2_data

    monkeypatch.setattr(client, "_request_with_retry", mock_request_v2)

    r2 = await client.fetch_windfor_forecasts(t_start, t_end)
    assert len(r2) == 2

    # Verify SQLite row count remains exactly 2 (no duplicates) and values updated
    db_rows_2 = get_forecast_records()
    assert len(db_rows_2) == 2
    gens = {r["publish_time"]: r["generation_mw"] for r in db_rows_2}
    assert gens["2026-01-02T12:00:00Z"] == 12500.0
    assert gens["2026-01-06T00:00:00Z"] == 15500.0


@pytest.mark.anyio
async def test_empty_chunks_and_api_failure(clean_db, monkeypatch):
    """
    5. Verify graceful handling of empty chunks (data: []) and proper error propagation on failure.
    """
    client = ElexonClient()

    t_start = "2026-01-01T00:00:00Z"
    t_end = "2026-01-11T00:00:00Z"  # 2 chunks

    # 5a. Empty chunk in first chunk, valid records in second
    async def mock_empty_first(url, params):
        if params["publishDateTimeFrom"] == t_start:
            return {"data": []}
        return {
            "data": [
                {"publishTime": "2026-01-08T00:00:00Z", "startTime": "2026-01-08T12:00:00Z", "generation": 9000.0}
            ]
        }

    monkeypatch.setattr(client, "_request_with_retry", mock_empty_first)

    records = await client.fetch_windfor_forecasts(t_start, t_end)
    assert len(records) == 1
    assert records[0]["generation_mw"] == 9000.0

    # 5b. API failure propagation
    async def mock_failure(url, params):
        raise ElexonClientError("HTTP 500: Internal Server Error", status_code=500)

    monkeypatch.setattr(client, "_request_with_retry", mock_failure)

    with pytest.raises(ElexonClientError) as exc_info:
        await client.fetch_windfor_forecasts(t_start, t_end)
    assert "HTTP 500" in str(exc_info.value)


@pytest.mark.anyio
async def test_final_chunk_and_requested_end_timestamp_precision(clean_db, monkeypatch):
    """
    6. Verify that the final chunk stops exactly at requested end timestamp,
    and single-timestamp queries (from == to) execute exactly one query.
    """
    client = ElexonClient()

    # Case A: Arbitrary end time with minutes/seconds
    t_start = "2026-01-01T00:00:00Z"
    t_end = "2026-01-06T15:30:45Z"  # 5 days + 15 hours + 30 min + 45 sec

    requested_params = []

    async def mock_precision(url, params):
        requested_params.append(dict(params))
        return {"data": []}

    monkeypatch.setattr(client, "_request_with_retry", mock_precision)

    await client.fetch_windfor_forecasts(t_start, t_end)

    assert len(requested_params) == 2
    # First chunk is exactly 5 days
    assert requested_params[0]["publishDateTimeFrom"] == "2026-01-01T00:00:00Z"
    assert requested_params[0]["publishDateTimeTo"] == "2026-01-06T00:00:00Z"
    # Second chunk stops at exact requested end timestamp
    assert requested_params[1]["publishDateTimeFrom"] == "2026-01-06T00:00:00Z"
    assert requested_params[1]["publishDateTimeTo"] == "2026-01-06T15:30:45Z"

    # Case B: Single instant query (t_start == t_end)
    instant_params = []

    async def mock_instant(url, params):
        instant_params.append(dict(params))
        return {
            "data": [
                {"publishTime": "2026-01-01T12:00:00Z", "startTime": "2026-01-02T12:00:00Z", "generation": 14000.0}
            ]
        }

    monkeypatch.setattr(client, "_request_with_retry", mock_instant)

    single_rec = await client.fetch_windfor_forecasts("2026-01-01T12:00:00Z", "2026-01-01T12:00:00Z")
    assert len(instant_params) == 1
    assert instant_params[0]["publishDateTimeFrom"] == "2026-01-01T12:00:00Z"
    assert instant_params[0]["publishDateTimeTo"] == "2026-01-01T12:00:00Z"
    assert len(single_rec) == 1
