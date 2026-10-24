import sqlite3
import os
import sys

# Ensure backend root is on PYTHONPATH
sys.path.insert(0, os.path.join(os.getcwd(), "backend"))

from app.core.config import settings
settings.DATABASE_PATH = os.path.abspath("backend/data/wind_forecast.db")

from app.data.repository import get_actual_records, get_forecast_records
from app.services.vintage_selector import select_forecasts_for_delivery_intervals
from app.core.time_utils import generate_expected_intervals_in_range
from app.services.alignment import align_forecast_and_actuals
from app.services.metrics import calculate_accuracy_metrics

db_path = "backend/data/wind_forecast.db"
conn = sqlite3.connect(db_path)
c = conn.cursor()

# 1. Total forecast records in DB
c.execute("SELECT COUNT(*) FROM wind_forecasts")
total_forecasts = c.fetchone()[0]

# 2. Total actual records in DB
c.execute("SELECT COUNT(*) FROM actual_generation")
total_actuals = c.fetchone()[0]

# 3. Forecasts for Jan 1-5 delivery
c.execute("SELECT COUNT(*) FROM wind_forecasts WHERE delivery_time >= '2026-01-01T00:00:00Z' AND delivery_time <= '2026-01-05T23:59:59Z'")
forecasts_jan1_5 = c.fetchone()[0]

# 4. Forecasts fetched in the initial Jan 1-5 call (publish_time from 2025-12-29 to 2026-01-05)
c.execute("SELECT COUNT(*) FROM wind_forecasts WHERE publish_time >= '2025-12-29T00:00:00Z' AND publish_time <= '2026-01-05T23:59:59Z'")
forecasts_pub_jan1_5 = c.fetchone()[0]

print(f"Total forecasts in DB: {total_forecasts}")
print(f"Total actuals in DB: {total_actuals}")
print(f"Forecasts with Jan 1-5 delivery: {forecasts_jan1_5}")
print(f"Forecasts published Dec 29 - Jan 5: {forecasts_pub_jan1_5}")

actuals = get_actual_records("2026-01-01", "2026-01-05")
print(f"Actuals count Jan 1-5: {len(actuals)}")

raw_forecasts = get_forecast_records("2026-01-01T00:00:00Z", "2026-01-05T23:59:59Z")
print(f"Raw forecasts retrieved for Jan 1-5: {len(raw_forecasts)}")

exp = generate_expected_intervals_in_range("2026-01-01", "2026-01-05")

# Test cutoff: 2025-12-31T11:30:00Z
sel_1130 = select_forecasts_for_delivery_intervals(raw_forecasts, "2025-12-31T11:30:00Z")
aligned_hh_1130 = align_forecast_and_actuals(exp, actuals, sel_1130, "half_hourly")
m_hh_1130 = calculate_accuracy_metrics(aligned_hh_1130, len(exp))

print("\n--- RESULTS AT CUTOFF 2025-12-31T11:30:00Z (Half-Hourly) ---")
print(f"Valid pairs: {m_hh_1130.valid_pairs_count}")
print(f"MAE: {m_hh_1130.mae_mw} MW")
print(f"RMSE: {m_hh_1130.rmse_mw} MW")
print(f"Bias (ME): {m_hh_1130.bias_mw} MW")
print(f"WAPE: {m_hh_1130.wape_pct}%")
print(f"Coverage: {m_hh_1130.coverage_pct}%")

# Test cutoff: 2025-12-31T12:00:00Z
sel_1200 = select_forecasts_for_delivery_intervals(raw_forecasts, "2025-12-31T12:00:00Z")
aligned_hh_1200 = align_forecast_and_actuals(exp, actuals, sel_1200, "half_hourly")
m_hh_1200 = calculate_accuracy_metrics(aligned_hh_1200, len(exp))

print("\n--- RESULTS AT CUTOFF 2025-12-31T12:00:00Z (Half-Hourly) ---")
print(f"Valid pairs: {m_hh_1200.valid_pairs_count}")
print(f"MAE: {m_hh_1200.mae_mw} MW")
print(f"RMSE: {m_hh_1200.rmse_mw} MW")
print(f"Bias (ME): {m_hh_1200.bias_mw} MW")
print(f"WAPE: {m_hh_1200.wape_pct}%")

# Test Retrospective Latest (No Cutoff / Latest published before delivery)
# With strict publish_time <= delivery_time
vintages_by_delivery = {}
for f in raw_forecasts:
    vintages_by_delivery.setdefault(f["delivery_time"], []).append(f)

latest_forecasts = {}
for deliv, v_list in vintages_by_delivery.items():
    # Only vintages published at or before delivery
    valid_v = [v for v in v_list if v["publish_time"] <= deliv]
    if valid_v:
        valid_v.sort(key=lambda x: (x["publish_time"], x["id"]), reverse=True)
        latest_forecasts[deliv] = valid_v[0]

aligned_hh_latest = align_forecast_and_actuals(exp, actuals, latest_forecasts, "half_hourly")
m_hh_latest = calculate_accuracy_metrics(aligned_hh_latest, len(exp))
print("\n--- RESULTS RETROSPECTIVE LATEST (publish_time <= delivery_time, Half-Hourly) ---")
print(f"Valid pairs: {m_hh_latest.valid_pairs_count}")
print(f"MAE: {m_hh_latest.mae_mw} MW")
print(f"RMSE: {m_hh_latest.rmse_mw} MW")
print(f"Bias (ME): {m_hh_latest.bias_mw} MW")
print(f"WAPE: {m_hh_latest.wape_pct}%")

aligned_h_latest = align_forecast_and_actuals(exp, actuals, latest_forecasts, "hourly")
m_h_latest = calculate_accuracy_metrics(aligned_h_latest, len(exp)//2)
print("\n--- RESULTS RETROSPECTIVE LATEST (publish_time <= delivery_time, Hourly Native) ---")
print(f"Valid pairs: {m_h_latest.valid_pairs_count}")
print(f"MAE: {m_h_latest.mae_mw} MW")
print(f"RMSE: {m_h_latest.rmse_mw} MW")
print(f"Bias (ME): {m_h_latest.bias_mw} MW")
print(f"WAPE: {m_h_latest.wape_pct}%")
