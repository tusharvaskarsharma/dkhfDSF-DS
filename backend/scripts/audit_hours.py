import sqlite3

conn = sqlite3.connect('backend/data/wind_forecast.db')
cursor = conn.cursor()

# Run at 11:30 UTC
cursor.execute("""
SELECT DISTINCT delivery_time 
FROM wind_forecasts 
WHERE publish_time <= '2025-12-31T11:30:00Z'
  AND delivery_time >= '2026-01-01T00:00:00Z'
  AND delivery_time <= '2026-01-02T23:59:59Z'
ORDER BY delivery_time
""")
hours_1130 = [r[0] for r in cursor.fetchall()]
print(f"Distinct delivery hours before 11:30 UTC: {len(hours_1130)}")
print("Jan 1 hours:", len([h for h in hours_1130 if h.startswith('2026-01-01')]))
print("Jan 2 hours:", len([h for h in hours_1130 if h.startswith('2026-01-02')]))
missing_at_1130 = [f'2026-01-02T{h:02d}:00:00Z' for h in range(24) if f'2026-01-02T{h:02d}:00:00Z' not in hours_1130]
print("Missing hours on Jan 2 before 11:30 UTC:", missing_at_1130)

# What are the settlement periods for those missing hours?
# Hour 22:00:00Z is SP 45 and SP 46
# Hour 23:00:00Z is SP 47 and SP 48
print(f"Number of half-hourly periods missing before 11:30 UTC: {len(missing_at_1130) * 2}")
print(f"Total valid half-hourly pairs: (24 + 22) * 2 = 46 * 2 = {46 * 2} pairs!")

# Now check 12:00:00Z
cursor.execute("""
SELECT DISTINCT delivery_time 
FROM wind_forecasts 
WHERE publish_time <= '2025-12-31T12:00:00Z'
  AND delivery_time >= '2026-01-01T00:00:00Z'
  AND delivery_time <= '2026-01-02T23:59:59Z'
ORDER BY delivery_time
""")
hours_1200 = [r[0] for r in cursor.fetchall()]
print(f"\nDistinct delivery hours on or before 12:00 UTC: {len(hours_1200)}")
print("Jan 2 hours at 12:00 UTC:", len([h for h in hours_1200 if h.startswith('2026-01-02')]))

conn.close()
