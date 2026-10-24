import urllib.request
import json

def inspect_elexon():
    # 1. FUELHH sample
    url_f = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH?settlementDateFrom=2026-01-01&settlementDateTo=2026-01-01&fuelType=WIND"
    req_f = urllib.request.Request(url_f, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_f) as resp:
        data_f = json.loads(resp.read().decode('utf-8'))
        items_f = data_f.get('data', [])
        print("=== FUELHH Official Record Schema ===")
        print(f"Total records for 2026-01-01: {len(items_f)}")
        if items_f:
            print("First record:", json.dumps(items_f[0], indent=2))
            print("Last record:", json.dumps(items_f[-1], indent=2))

    # 2. WINDFOR sample
    url_w = "https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR?publishDateTimeFrom=2025-12-31T11:00:00Z&publishDateTimeTo=2025-12-31T12:00:00Z"
    req_w = urllib.request.Request(url_w, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req_w) as resp:
        data_w = json.loads(resp.read().decode('utf-8'))
        items_w = data_w.get('data', [])
        print("\n=== WINDFOR Official Record Schema ===")
        print(f"Total records: {len(items_w)}")
        if items_w:
            print("First record:", json.dumps(items_w[0], indent=2))
            pts = set(x['publishTime'] for x in items_w)
            print("Distinct publishTimes:", pts)
            for pt in sorted(list(pts)):
                subset = [x for x in items_w if x['publishTime'] == pt]
                print(f"  publishTime: {pt}, count: {len(subset)}, min startTime: {min(x['startTime'] for x in subset)}, max startTime: {max(x['startTime'] for x in subset)}")

inspect_elexon()
