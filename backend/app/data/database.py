import sqlite3
import os
from typing import Generator
from app.core.config import settings

def get_db_path() -> str:
    db_path = settings.DATABASE_PATH
    os.makedirs(os.path.dirname(db_path) if os.path.dirname(db_path) else ".", exist_ok=True)
    return db_path

def get_db_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    # Enable WAL mode for high performance concurrent read/write
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA synchronous=NORMAL;")
    return conn

def init_db():
    conn = get_db_connection()
    with conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS wind_forecasts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset TEXT NOT NULL DEFAULT 'WINDFOR',
            publish_time TEXT NOT NULL,
            delivery_time TEXT NOT NULL,
            generation_mw REAL NOT NULL,
            retrieval_time TEXT NOT NULL,
            source_status TEXT NOT NULL DEFAULT 'OK',
            UNIQUE(publish_time, delivery_time)
        );

        CREATE INDEX IF NOT EXISTS idx_forecast_delivery ON wind_forecasts(delivery_time);
        CREATE INDEX IF NOT EXISTS idx_forecast_publish ON wind_forecasts(publish_time);
        CREATE INDEX IF NOT EXISTS idx_forecast_del_pub ON wind_forecasts(delivery_time, publish_time);

        CREATE TABLE IF NOT EXISTS actual_generation (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset TEXT NOT NULL DEFAULT 'FUELHH',
            settlement_date TEXT NOT NULL,
            settlement_period INTEGER NOT NULL,
            delivery_time TEXT NOT NULL,
            fuel_type TEXT NOT NULL DEFAULT 'WIND',
            generation_mw REAL NOT NULL,
            publish_time TEXT NOT NULL,
            retrieval_time TEXT NOT NULL,
            UNIQUE(delivery_time, fuel_type)
        );

        CREATE INDEX IF NOT EXISTS idx_actual_delivery ON actual_generation(delivery_time);
        CREATE INDEX IF NOT EXISTS idx_actual_settlement_date ON actual_generation(settlement_date);

        CREATE TABLE IF NOT EXISTS sync_audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            dataset TEXT NOT NULL,
            query_params TEXT NOT NULL,
            records_ingested INTEGER NOT NULL,
            status TEXT NOT NULL,
            error_message TEXT,
            executed_at TEXT NOT NULL
        );
        """)
    conn.close()
