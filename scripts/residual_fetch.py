"""Download the prior-year Socrata datasets used by the residual_* scripts into raw/residual/ (gitignored).

  ord2024      x394-e874  2024 ordinance appropriations
  rec2024      rrdf-6mjk  2024 recommendations appropriations
  rec2025      miyk-k49p  2025 recommendations appropriations
  revord2024   rmi8-cugu  2024 ordinance revenue
  revrec2024   at79-usba  2024 recommendations revenue
  revrec2025   u72v-5iyn  2025 recommendations revenue
Everything else the residual_* scripts need comes from raw/ as built by scripts/gap_fetch.py.

Run: python3 scripts/residual_fetch.py   (idempotent)
"""
import json
import os
import urllib.request

OUT = os.path.join(os.path.dirname(__file__), "..", "raw", "residual")
SETS = {"ord2024": "x394-e874", "rec2024": "rrdf-6mjk", "rec2025": "miyk-k49p",
        "revord2024": "rmi8-cugu", "revrec2024": "at79-usba", "revrec2025": "u72v-5iyn"}
os.makedirs(OUT, exist_ok=True)
for name, ds in SETS.items():
    p = os.path.join(OUT, f"{name}.json")
    if os.path.exists(p):
        print(name, "already present")
        continue
    url = f"https://data.cityofchicago.org/resource/{ds}.json?$limit=50000"
    rows = json.load(urllib.request.urlopen(url, timeout=120))
    json.dump(rows, open(p, "w"))
    print(name, ds, len(rows))
