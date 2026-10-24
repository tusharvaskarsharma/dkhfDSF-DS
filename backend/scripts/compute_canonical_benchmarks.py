import sqlite3
import sys
import os

sys.path.insert(0, os.path.join(os.getcwd(), 'backend'))

from app.core.config import settings
settings.DATABASE_PATH = os.path.abspath('backend/data/wind_forecast.db')

conn = sqlite3.connect(settings.DATABASE_PATH)
c = conn.cursor()

c.execute('''
    SELECT publish_time, delivery_time, generation_mw, id
    FROM wind_forecasts
    WHERE delivery_time >= '2026-01-01T00:00:00Z' AND delivery_time <= '2026-01-05T23:59:59Z'
    ORDER BY delivery_time, publish_time
''')
fcs = c.fetchall()

c.execute('''
    SELECT delivery_time, generation_mw, settlement_period, settlement_date
    FROM actual_generation
    WHERE settlement_date BETWEEN '2026-01-01' AND '2026-01-05'
    ORDER BY delivery_time
''')
acts = c.fetchall()

print(f"Total actual records (Jan 1-5): {len(acts)}")
print(f"Total forecast records (Jan 1-5 delivery): {len(fcs)}")

from app.services.vintage_selector import select_forecasts_for_delivery_intervals
from app.services.alignment import align_forecast_and_actuals
from app.services.metrics import calculate_accuracy_metrics
from app.core.time_utils import generate_expected_intervals_in_range

exp = generate_expected_intervals_in_range('2026-01-01', '2026-01-05')
raw_fc_dicts = [{'publish_time': r[0], 'delivery_time': r[1], 'generation_mw': r[2], 'id': r[3]} for r in fcs]
act_dicts = [{'delivery_time': r[0], 'generation_mw': r[1], 'settlement_period': r[2], 'settlement_date': r[3]} for r in acts]

modes = [
    ("Rolling DA 09:20 London (EPEX SPOT GB Day-Ahead 60)", "rolling_da", "09:20", None),
    ("Rolling DA 09:50 London (Nord Pool / N2EX GB Day-Ahead)", "rolling_da", "09:50", None),
    ("Rolling DA 11:00 London (Configurable Reference)", "rolling_da", "11:00", None),
    ("Rolling DA 15:30 London (EPEX SPOT Half-Hour Auction)", "rolling_da", "15:30", None),
    ("Rolling DA 17:00 London (NESO Day-Ahead Schedule)", "rolling_da", "17:00", None),
    ("Retrospective Latest Pre-Delivery", "latest", "11:00", None),
    ("Fixed Snapshot: Dec 31 11:30 UTC", "snapshot", "11:00", "2025-12-31T11:30:00Z"),
]

print("\n" + "="*90)
print(f"{'Mode':<45} | {'Res':<5} | {'N/Exp':<8} | {'Cov%':<6} | {'Bias(ME)':<10} | {'MAE':<9} | {'RMSE':<9} | {'WAPE%':<6}")
print("="*90)

for label, c_type, da_time, snap_iso in modes:
    sel = select_forecasts_for_delivery_intervals(
        raw_fc_dicts,
        cutoff_type=c_type,
        da_cutoff_time=da_time,
        decision_cutoff=snap_iso
    )
    
    # Hourly Native 1-to-1
    al_h = align_forecast_and_actuals(exp, act_dicts, sel, granularity="hourly")
    m_h = calculate_accuracy_metrics(al_h, 120)
    print(f"{label:<45} | Hourly| {m_h.valid_pairs_count:3d}/120  | {m_h.coverage_pct:5.1f}% | {m_h.bias_mw:8.2f} MW | {m_h.mae_mw:7.2f} MW | {m_h.rmse_mw:7.2f} MW | {m_h.wape_pct:5.2f}%")
    
    # Half-Hourly Broadcast
    al_hh = align_forecast_and_actuals(exp, act_dicts, sel, granularity="half_hourly")
    m_hh = calculate_accuracy_metrics(al_hh, 240)
    print(f"{label:<45} | Half-H| {m_hh.valid_pairs_count:3d}/240  | {m_hh.coverage_pct:5.1f}% | {m_hh.bias_mw:8.2f} MW | {m_hh.mae_mw:7.2f} MW | {m_hh.rmse_mw:7.2f} MW | {m_hh.wape_pct:5.2f}%")
    print("-" * 90)

conn.close()
