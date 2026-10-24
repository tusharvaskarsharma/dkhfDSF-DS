import sqlite3

conn = sqlite3.connect('backend/data/wind_forecast.db')
c = conn.cursor()

c.execute("SELECT COUNT(DISTINCT publish_time) FROM wind_forecasts")
print("Distinct publish runs in DB:", c.fetchone()[0])

deliv = "2026-01-01T12:00:00Z"
c.execute("""
    SELECT publish_time, generation_mw, id
    FROM wind_forecasts 
    WHERE delivery_time = ?
    ORDER BY publish_time
""", (deliv,))
runs = c.fetchall()
print(f"Total publication runs covering delivery {deliv}: {len(runs)}")
for p_time, mw, rid in runs:
    is_pre = p_time <= deliv
    lead_hours = (int(deliv[:4]) - int(p_time[:4])) # just display
    print(f"  ID: {rid:5d} | Pub: {p_time} | MW: {mw:6.0f} | Ex-Ante (Pre-Delivery): {is_pre}")

# Check actual outturn generation for this hour from FUELHH
c.execute("""
    SELECT settlement_period, generation_mw, delivery_time
    FROM actual_generation
    WHERE settlement_date = '2026-01-01' AND settlement_period IN (25, 26)
""")
acts = c.fetchall()
print(f"\nActual FUELHH outturn for {deliv} (SPs 25 & 26):")
for sp, mw, dt in acts:
    print(f"  SP {sp} ({dt}): {mw:.1f} MW")
avg_act = sum(a[1] for a in acts) / len(acts)
print(f"  Hourly Average Actual: {avg_act:.1f} MW")

conn.close()
