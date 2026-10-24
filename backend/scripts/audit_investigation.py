import sqlite3
import json
import math

conn = sqlite3.connect('backend/data/wind_forecast.db')
cursor = conn.cursor()

# 1. Count actuals for Jan 1-5
cursor.execute("SELECT COUNT(*) FROM actual_generation WHERE settlement_date >= '2026-01-01' AND settlement_date <= '2026-01-05'")
act_count = cursor.fetchone()[0]
print(f"1. Actuals count (Jan 1-5): {act_count}")

# 2. Check sync audit log
cursor.execute("SELECT dataset, query_params, records_ingested, status, executed_at FROM sync_audit_log ORDER BY id DESC LIMIT 10")
print("\n2. Recent sync audit logs:")
for row in cursor.fetchall():
    print(" ", row)

# 3. Check raw WINDFOR records with delivery_time in Jan 1-5
cursor.execute("SELECT COUNT(*) FROM wind_forecasts WHERE delivery_time >= '2026-01-01T00:00:00Z' AND delivery_time <= '2026-01-05T23:59:59Z'")
fc_deliv_count = cursor.fetchone()[0]
print(f"\n3. Forecast records with delivery_time in Jan 1-5: {fc_deliv_count}")

# 4. Check cutoff at 2025-12-31T12:00:00Z
cursor.execute("""
SELECT DISTINCT delivery_time 
FROM wind_forecasts 
WHERE publish_time <= '2025-12-31T12:00:00Z'
  AND delivery_time >= '2026-01-01T00:00:00Z'
  AND delivery_time <= '2026-01-05T23:59:59Z'
ORDER BY delivery_time
""")
deliv_hours = [r[0] for r in cursor.fetchall()]
print(f"\n4. Distinct delivery hours available before 2025-12-31T12:00:00Z: {len(deliv_hours)}")
if deliv_hours:
    print(f"   First delivery hour: {deliv_hours[0]}")
    print(f"   Last delivery hour:  {deliv_hours[-1]}")
    # Which hours in Jan 1 and Jan 2 are covered?
    jan1_hours = [h for h in deliv_hours if h.startswith('2026-01-01')]
    jan2_hours = [h for h in deliv_hours if h.startswith('2026-01-02')]
    jan3_hours = [h for h in deliv_hours if h.startswith('2026-01-03')]
    print(f"   Jan 1 hours count: {len(jan1_hours)} of 24")
    print(f"   Jan 2 hours count: {len(jan2_hours)} of 24")
    print(f"   Jan 3 hours count: {len(jan3_hours)} of 24")
    if len(jan2_hours) < 24:
        missing_jan2 = [f"2026-01-02T{h:02d}:00:00Z" for h in range(24) if f"2026-01-02T{h:02d}:00:00Z" not in jan2_hours]
        print(f"   Missing hours on Jan 2: {missing_jan2}")

# 5. Check what the publication runs were on 2025-12-31 up to 12:00:00Z
cursor.execute("""
SELECT DISTINCT publish_time, COUNT(*), MIN(delivery_time), MAX(delivery_time)
FROM wind_forecasts
WHERE publish_time <= '2025-12-31T12:00:00Z'
GROUP BY publish_time
ORDER BY publish_time
""")
print("\n5. Publication runs on or before 2025-12-31T12:00:00Z:")
for row in cursor.fetchall():
    print(" ", row)

conn.close()
