"""
Deterministic fixture data for automated tests and offline demo mode.
Includes historical publication vintages and actual FUELHH records for 2026-01-01 to 2026-01-03.
"""
from typing import List, Dict, Any
from datetime import datetime, date, timedelta, timezone
from app.core.time_utils import generate_settlement_periods_for_date, format_utc_iso

def get_fixture_actuals() -> List[Dict[str, Any]]:
    """
    Generate deterministic FUELHH actual generation records for 2026-01-01 through 2026-01-03.
    Realistic wind profile with peaks and troughs across 144 settlement periods.
    """
    records = []
    base_pattern = [
        13756, 13873, 14036, 14077, 14185, 14575, 14890, 15120,
        15340, 15480, 15600, 15720, 15850, 15900, 15780, 15610,
        15400, 15200, 14950, 14700, 14500, 14350, 14200, 14100,
        14050, 14150, 14300, 14550, 14800, 15100, 15450, 15800,
        16150, 16400, 16650, 16800, 16750, 16600, 16400, 16200,
        16000, 15850, 15720, 15650, 15626, 15542, 15578, 15538
    ]

    dates = ["2026-01-01", "2026-01-02", "2026-01-03"]
    multipliers = [1.0, 1.15, 0.85]

    for d_idx, d_str in enumerate(dates):
        mult = multipliers[d_idx]
        periods = generate_settlement_periods_for_date(d_str)
        for p in periods:
            sp = p["settlement_period"]
            # Intentionally omit period 30 on Jan 3 to simulate missing actual in tests
            if d_str == "2026-01-03" and sp == 30:
                continue
            gen = round(base_pattern[sp - 1] * mult)
            records.append({
                "dataset": "FUELHH",
                "settlement_date": d_str,
                "settlement_period": sp,
                "delivery_time": p["start_time_utc"],
                "fuel_type": "WIND",
                "generation_mw": float(gen),
                "publish_time": p["end_time_utc"],
                "retrieval_time": "2026-01-04T00:00:00Z"
            })

    return records

def get_fixture_forecasts() -> List[Dict[str, Any]]:
    """
    Generate deterministic WINDFOR forecast publications with multiple vintages per delivery hour.
    Calculates dates using datetime arithmetic to avoid invalid calendar dates.
    """
    forecasts = []

    for day in [1, 2, 3]:
        delivery_date = date(2026, 1, day)
        for hour in range(24):
            delivery_dt = datetime(2026, 1, day, hour, 0, 0, tzinfo=timezone.utc)
            delivery_time_str = format_utc_iso(delivery_dt)

            base_gen = 14000 + (hour * 120) if hour < 14 else 17000 - ((hour - 14) * 150)
            if day == 2:
                base_gen *= 1.12
            elif day == 3:
                base_gen *= 0.88

            # 1. Vintage D-2 12:00 UTC (48h before delivery start of day)
            d2_pub_dt = datetime(delivery_date.year, delivery_date.month, delivery_date.day, 12, 0, 0, tzinfo=timezone.utc) - timedelta(days=2)
            forecasts.append({
                "dataset": "WINDFOR",
                "publish_time": format_utc_iso(d2_pub_dt),
                "delivery_time": delivery_time_str,
                "generation_mw": float(round(base_gen + 1200)),
                "retrieval_time": "2026-01-04T00:00:00Z",
                "source_status": "FIXTURE_TEST_DATA"
            })

            # 2. Vintage D-1 06:00 UTC
            d1_06_pub_dt = datetime(delivery_date.year, delivery_date.month, delivery_date.day, 6, 0, 0, tzinfo=timezone.utc) - timedelta(days=1)
            forecasts.append({
                "dataset": "WINDFOR",
                "publish_time": format_utc_iso(d1_06_pub_dt),
                "delivery_time": delivery_time_str,
                "generation_mw": float(round(base_gen + 750)),
                "retrieval_time": "2026-01-04T00:00:00Z",
                "source_status": "FIXTURE_TEST_DATA"
            })

            # 3. Vintage D-1 11:30 UTC (Key Day-Ahead auction cutoff)
            d1_11_pub_dt = datetime(delivery_date.year, delivery_date.month, delivery_date.day, 11, 30, 0, tzinfo=timezone.utc) - timedelta(days=1)
            forecasts.append({
                "dataset": "WINDFOR",
                "publish_time": format_utc_iso(d1_11_pub_dt),
                "delivery_time": delivery_time_str,
                "generation_mw": float(round(base_gen + 300)),
                "retrieval_time": "2026-01-04T00:00:00Z",
                "source_status": "FIXTURE_TEST_DATA"
            })

            # 4. Vintage D-1 17:30 UTC
            d1_17_pub_dt = datetime(delivery_date.year, delivery_date.month, delivery_date.day, 17, 30, 0, tzinfo=timezone.utc) - timedelta(days=1)
            forecasts.append({
                "dataset": "WINDFOR",
                "publish_time": format_utc_iso(d1_17_pub_dt),
                "delivery_time": delivery_time_str,
                "generation_mw": float(round(base_gen - 150)),
                "retrieval_time": "2026-01-04T00:00:00Z",
                "source_status": "FIXTURE_TEST_DATA"
            })

            # 5. Vintage D-0 02:30 UTC (Only for hours >= 4)
            if hour >= 4:
                d0_02_pub_dt = datetime(delivery_date.year, delivery_date.month, delivery_date.day, 2, 30, 0, tzinfo=timezone.utc)
                forecasts.append({
                    "dataset": "WINDFOR",
                    "publish_time": format_utc_iso(d0_02_pub_dt),
                    "delivery_time": delivery_time_str,
                    "generation_mw": float(round(base_gen - 50)),
                    "retrieval_time": "2026-01-04T00:00:00Z",
                    "source_status": "FIXTURE_TEST_DATA"
                })

    return forecasts

def load_fixture_data_into_db() -> Dict[str, int]:
    """Loads fixture datasets into the database for testing or demo mode."""
    from app.data.repository import upsert_forecasts, upsert_actuals
    act = get_fixture_actuals()
    fc = get_fixture_forecasts()
    a_count = upsert_actuals(act)
    f_count = upsert_forecasts(fc)
    return {"actuals_loaded": a_count, "forecasts_loaded": f_count}
