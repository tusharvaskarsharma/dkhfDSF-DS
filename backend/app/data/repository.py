import sqlite3
from typing import List, Dict, Optional, Any, Tuple
from app.data.database import get_db_connection
from app.core.time_utils import format_utc_iso, parse_utc_iso
from datetime import datetime, timezone

def upsert_forecasts(records: List[Dict[str, Any]]) -> int:
    """
    Insert or update forecast records into wind_forecasts.
    Uses INSERT OR REPLACE to keep latest retrieval provenance if re-fetched.
    """
    if not records:
        return 0
    conn = get_db_connection()
    inserted = 0
    with conn:
        cursor = conn.cursor()
        for r in records:
            cursor.execute("""
            INSERT INTO wind_forecasts (
                dataset, publish_time, delivery_time, generation_mw, retrieval_time, source_status
            ) VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(publish_time, delivery_time) DO UPDATE SET
                generation_mw = excluded.generation_mw,
                retrieval_time = excluded.retrieval_time,
                source_status = excluded.source_status
            """, (
                r.get("dataset", "WINDFOR"),
                r["publish_time"],
                r["delivery_time"],
                float(r["generation_mw"]),
                r.get("retrieval_time", format_utc_iso(datetime.now(timezone.utc))),
                r.get("source_status", "OK")
            ))
            inserted += 1
    conn.close()
    return inserted

def upsert_actuals(records: List[Dict[str, Any]]) -> int:
    """
    Insert or update actual generation records into actual_generation.
    Uses INSERT OR REPLACE on (delivery_time, fuel_type).
    """
    if not records:
        return 0
    conn = get_db_connection()
    inserted = 0
    with conn:
        cursor = conn.cursor()
        for r in records:
            cursor.execute("""
            INSERT INTO actual_generation (
                dataset, settlement_date, settlement_period, delivery_time, fuel_type, generation_mw, publish_time, retrieval_time
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(delivery_time, fuel_type) DO UPDATE SET
                generation_mw = excluded.generation_mw,
                publish_time = excluded.publish_time,
                retrieval_time = excluded.retrieval_time
            """, (
                r.get("dataset", "FUELHH"),
                r["settlement_date"],
                int(r["settlement_period"]),
                r["delivery_time"],
                r.get("fuel_type", "WIND"),
                float(r["generation_mw"]),
                r.get("publish_time", ""),
                r.get("retrieval_time", format_utc_iso(datetime.now(timezone.utc)))
            ))
            inserted += 1
    conn.close()
    return inserted

def get_forecast_records(
    delivery_from: Optional[str] = None,
    delivery_to: Optional[str] = None,
    publish_cutoff: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve raw forecast records matching criteria."""
    conn = get_db_connection()
    query = "SELECT * FROM wind_forecasts WHERE 1=1"
    params = []

    if delivery_from:
        query += " AND delivery_time >= ?"
        params.append(delivery_from)
    if delivery_to:
        query += " AND delivery_time <= ?"
        params.append(delivery_to)
    if publish_cutoff:
        query += " AND publish_time <= ?"
        params.append(publish_cutoff)

    query += " ORDER BY delivery_time ASC, publish_time ASC, id DESC"
    cursor = conn.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_actual_records(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    delivery_from: Optional[str] = None,
    delivery_to: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieve actual generation records matching criteria."""
    conn = get_db_connection()
    query = "SELECT * FROM actual_generation WHERE fuel_type = 'WIND'"
    params = []

    if date_from:
        query += " AND settlement_date >= ?"
        params.append(date_from)
    if date_to:
        query += " AND settlement_date <= ?"
        params.append(date_to)
    if delivery_from:
        query += " AND delivery_time >= ?"
        params.append(delivery_from)
    if delivery_to:
        query += " AND delivery_time <= ?"
        params.append(delivery_to)

    query += " ORDER BY delivery_time ASC, settlement_period ASC"
    cursor = conn.execute(query, params)
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_vintages_for_delivery(delivery_time: str) -> List[Dict[str, Any]]:
    """Get all publication vintages for a specific delivery start time."""
    conn = get_db_connection()
    cursor = conn.execute(
        "SELECT * FROM wind_forecasts WHERE delivery_time = ? ORDER BY publish_time ASC, id DESC",
        (delivery_time,)
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows

def get_all_distinct_delivery_times(date_from: Optional[str] = None, date_to: Optional[str] = None) -> List[str]:
    """Retrieve all available delivery times present in actuals or forecasts."""
    conn = get_db_connection()
    query = """
    SELECT DISTINCT delivery_time FROM (
        SELECT delivery_time FROM actual_generation
        UNION
        SELECT delivery_time FROM wind_forecasts
    ) WHERE 1=1
    """
    params = []
    if date_from:
        query += " AND delivery_time >= ?"
        params.append(date_from)
    if date_to:
        query += " AND delivery_time <= ?"
        params.append(date_to + "T23:59:59Z")
    query += " ORDER BY delivery_time ASC"
    cursor = conn.execute(query, params)
    rows = [r["delivery_time"] for r in cursor.fetchall()]
    conn.close()
    return rows

def log_sync(dataset: str, query_params: str, records_ingested: int, status: str, error_message: Optional[str] = None):
    conn = get_db_connection()
    with conn:
        conn.execute("""
        INSERT INTO sync_audit_log (dataset, query_params, records_ingested, status, error_message, executed_at)
        VALUES (?, ?, ?, ?, ?, ?)
        """, (
            dataset,
            query_params,
            records_ingested,
            status,
            error_message,
            format_utc_iso(datetime.now(timezone.utc))
        ))
    conn.close()

def get_cache_stats() -> Dict[str, Any]:
    """Return summary statistics of cached records."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*), MIN(delivery_time), MAX(delivery_time) FROM wind_forecasts")
    f_count, f_min, f_max = cursor.fetchone()

    cursor.execute("SELECT COUNT(*), MIN(settlement_date), MAX(settlement_date) FROM actual_generation WHERE fuel_type = 'WIND'")
    a_count, a_min, a_max = cursor.fetchone()

    cursor.execute("SELECT executed_at FROM sync_audit_log WHERE status = 'SUCCESS' ORDER BY id DESC LIMIT 1")
    last_sync_row = cursor.fetchone()
    last_sync = last_sync_row[0] if last_sync_row else None

    conn.close()
    return {
        "cached_forecast_count": f_count or 0,
        "cached_actual_count": a_count or 0,
        "available_date_range_forecasts": {"min": f_min, "max": f_max} if f_count else None,
        "available_date_range_actuals": {"min": a_min, "max": a_max} if a_count else None,
        "last_sync_time": last_sync
    }
