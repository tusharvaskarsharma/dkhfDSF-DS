import sqlite3
import math

conn = sqlite3.connect('backend/data/wind_forecast.db')
cursor = conn.cursor()

# Get Jan 1-5 actuals
cursor.execute("""
SELECT settlement_date, settlement_period, delivery_time, generation_mw 
FROM actual_generation 
WHERE settlement_date BETWEEN '2026-01-01' AND '2026-01-05'
ORDER BY delivery_time
""")
actuals = cursor.fetchall()
print(f"Total actual half-hour periods: {len(actuals)}")

# Get latest forecasts for Jan 1-5
cursor.execute("""
SELECT delivery_time, generation_mw, MAX(publish_time)
FROM wind_forecasts
WHERE delivery_time >= '2026-01-01T00:00:00Z' AND delivery_time <= '2026-01-05T23:59:59Z'
GROUP BY delivery_time
ORDER BY delivery_time
""")
forecasts = {r[0]: r[1] for r in cursor.fetchall()}
print(f"Total forecast hours: {len(forecasts)}")

# 1. Half-hourly calculation (duplicating forecast to both half-hours)
hh_errors = []
hh_abs_errors = []
hh_sq_errors = []
hh_actuals = []
for a in actuals:
    deliv = a[2] # e.g. 2026-01-01T00:30:00Z
    hour = deliv[:14] + "00:00Z"
    if hour in forecasts:
        fc = forecasts[hour]
        act = a[3]
        err = act - fc
        hh_errors.append(err)
        hh_abs_errors.append(abs(err))
        hh_sq_errors.append(err ** 2)
        hh_actuals.append(act)

n_hh = len(hh_errors)
me_hh = sum(hh_errors) / n_hh
mae_hh = sum(hh_abs_errors) / n_hh
rmse_hh = math.sqrt(sum(hh_sq_errors) / n_hh)
wape_hh = (sum(hh_abs_errors) / sum(hh_actuals)) * 100

print("\n=== Half-Hourly Resolution (Duplicated Forecast) ===")
print(f"N: {n_hh}")
print(f"Bias (ME): {me_hh:.2f} MW")
print(f"MAE: {mae_hh:.2f} MW")
print(f"RMSE: {rmse_hh:.2f} MW")
print(f"WAPE: {wape_hh:.2f}%")

# 2. Hourly Resolution (native 1-to-1 alignment)
hourly_actuals = {}
for a in actuals:
    hour = a[2][:14] + "00:00Z"
    hourly_actuals.setdefault(hour, []).append(a[3])

h_errors = []
h_abs_errors = []
h_sq_errors = []
h_actuals = []
for hour, act_list in sorted(hourly_actuals.items()):
    if hour in forecasts and len(act_list) == 2:
        avg_act = sum(act_list) / 2.0
        fc = forecasts[hour]
        err = avg_act - fc
        h_errors.append(err)
        h_abs_errors.append(abs(err))
        h_sq_errors.append(err ** 2)
        h_actuals.append(avg_act)

n_h = len(h_errors)
me_h = sum(h_errors) / n_h
mae_h = sum(h_abs_errors) / n_h
rmse_h = math.sqrt(sum(h_sq_errors) / n_h)
wape_h = (sum(h_abs_errors) / sum(h_actuals)) * 100

print("\n=== Hourly Resolution (Native 1-to-1 Alignment) ===")
print(f"N: {n_h}")
print(f"Bias (ME): {me_h:.2f} MW")
print(f"MAE: {mae_h:.2f} MW")
print(f"RMSE: {rmse_h:.2f} MW")
print(f"WAPE: {wape_h:.2f}%")

conn.close()
