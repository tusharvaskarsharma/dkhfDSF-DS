import sqlite3
import math
from datetime import datetime, date, timedelta, timezone

conn = sqlite3.connect('backend/data/wind_forecast.db')
cursor = conn.cursor()

# Get all forecasts for Jan 1-5
cursor.execute("""
SELECT publish_time, delivery_time, generation_mw, id
FROM wind_forecasts
WHERE delivery_time >= '2026-01-01T00:00:00Z' AND delivery_time <= '2026-01-05T23:59:59Z'
ORDER BY delivery_time, publish_time
""")
all_fc = cursor.fetchall()

# Group forecasts by delivery_time
fc_by_delivery = {}
for r in all_fc:
    fc_by_delivery.setdefault(r[1], []).append(r)

# Evaluate with Day-Ahead Cutoff: For each delivery day D, cutoff is D-1 at 11:00 UTC
da_cutoffs = {
    "2026-01-01": "2025-12-31T11:00:00Z",
    "2026-01-02": "2026-01-01T11:00:00Z",
    "2026-01-03": "2026-01-02T11:00:00Z",
    "2026-01-04": "2026-01-03T11:00:00Z",
    "2026-01-05": "2026-01-04T11:00:00Z",
}

selected_hourly = {}
for hour_str, vintages in fc_by_delivery.items():
    deliv_date = hour_str[:10]
    cutoff = da_cutoffs.get(deliv_date)
    eligible = [v for v in vintages if v[0] <= cutoff]
    if eligible:
        # Latest published before cutoff
        eligible.sort(key=lambda x: (x[0], x[3]), reverse=True)
        selected_hourly[hour_str] = eligible[0]

print(f"Total delivery hours in Jan 1-5: 120")
print(f"Delivery hours with eligible forecast at DA 11:00 UTC: {len(selected_hourly)}")

# Check per day
for d_str, cutoff in sorted(da_cutoffs.items()):
    hours_for_day = [h for h in selected_hourly if h.startswith(d_str)]
    print(f"  {d_str} (Cutoff {cutoff}): {len(hours_for_day)} of 24 hours")

# Now align with actuals at Hourly resolution
cursor.execute("""
SELECT delivery_time, generation_mw 
FROM actual_generation 
WHERE settlement_date BETWEEN '2026-01-01' AND '2026-01-05'
ORDER BY delivery_time
""")
actuals = cursor.fetchall()

hourly_act = {}
for a in actuals:
    hour = a[0][:14] + "00:00Z"
    hourly_act.setdefault(hour, []).append(a[1])

errors = []
abs_errors = []
sq_errors = []
act_sum = []
for hour, act_list in sorted(hourly_act.items()):
    if hour in selected_hourly and len(act_list) == 2:
        avg_act = sum(act_list) / 2.0
        fc = selected_hourly[hour][2]
        err = avg_act - fc
        errors.append(err)
        abs_errors.append(abs(err))
        sq_errors.append(err ** 2)
        act_sum.append(avg_act)

N = len(errors)
print(f"\n=== Proper Day-Ahead 11:00 UTC Evaluation (Hourly 1-to-1) ===")
print(f"Valid paired hours: {N} of 120 (Coverage: {N/120*100:.1f}%)")
print(f"Bias (ME): {sum(errors)/N:.2f} MW")
print(f"MAE: {sum(abs_errors)/N:.2f} MW")
print(f"RMSE: {math.sqrt(sum(sq_errors)/N):.2f} MW")
print(f"WAPE: {sum(abs_errors)/sum(act_sum)*100:.2f}%")

# Half-hourly calculation (duplicating forecast to both SPs)
hh_errs, hh_abs, hh_sq, hh_acts = [], [], [], []
for a in actuals:
    hour = a[0][:14] + "00:00Z"
    if hour in selected_hourly:
        fc = selected_hourly[hour][2]
        act = a[1]
        e = act - fc
        hh_errs.append(e)
        hh_abs.append(abs(e))
        hh_sq.append(e**2)
        hh_acts.append(act)

print(f"\n=== Proper Day-Ahead 11:00 UTC Evaluation (Half-Hourly Broadcast) ===")
print(f"Valid paired periods: {len(hh_errs)} of {len(actuals)} (Coverage: {len(hh_errs)/len(actuals)*100:.1f}%)")
print(f"Bias (ME): {sum(hh_errs)/len(hh_errs):.2f} MW")
print(f"MAE: {sum(hh_abs)/len(hh_errs):.2f} MW")
print(f"RMSE: {math.sqrt(sum(hh_sq)/len(hh_errs)):.2f} MW")
print(f"WAPE: {sum(hh_abs)/sum(hh_acts)*100:.2f}%")

conn.close()
