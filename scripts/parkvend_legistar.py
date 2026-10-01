#!/usr/bin/env python3
"""Download ALL Chicago Park District Legistar matters (Board of Commissioners) via the
public Web API and save raw/parkvend/legistar_matters_all.json. Also fetches
matter attachments list for contract/management-agreement matters (see parkvend_award_parse.py)."""
import json, os, subprocess, time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "raw", "parkvend")
os.makedirs(OUT, exist_ok=True)
API = "https://webapi.legistar.com/v1/chicagoparkdistrict/matters"


def get(url):
    for _ in range(3):
        r = subprocess.run(["curl", "-sL", "-m", "90", "-A", "Mozilla/5.0", url], capture_output=True, text=True)
        try:
            return json.loads(r.stdout)
        except Exception:
            time.sleep(2)
    raise SystemExit("failed " + url)


rows, skip = [], 0
while True:
    page = get(f"{API}?$top=1000&$skip={skip}&$orderby=MatterId")
    rows += page
    print(skip, len(page), flush=True)
    if len(page) < 1000:
        break
    skip += 1000
json.dump(rows, open(os.path.join(OUT, "legistar_matters_all.json"), "w"))
print("matters", len(rows))
