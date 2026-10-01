#!/usr/bin/env python3
"""How far do 2025 City payments (s4vu-giwb) split the vendor leaves >= $10M?
Counts vendor x contract totals, then vendor x contract x month, then single vouchers, that are still >= $10M.
Excludes direct vouchers to pension funds, banks, county/state treasurers (not vendor spending).
Writes raw/leaves/leaves_payment_floor.json and prints the numbers used in research/leaves_over_10m.md."""
import csv, json, os, re
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 10_000_000
NONVENDOR = re.compile(r"PENSION|ANNUITY|A & B FUND|TREASURER|BANK|TRUST|ZIONS|AMALGAMATED|STATE OF ILLINOIS|COUNTY|CTA|CHICAGO TRANSIT|BOARD OF EDUCATION|PUBLIC BUILDING|DEPARTMENT OF FINANCE|PARK DISTRICT", re.I)
rows = list(csv.DictReader(open(f"{ROOT}/raw/city_payments_2025.csv")))
by_vc = defaultdict(float); by_vcm = defaultdict(float); by_v = defaultdict(float)
for r in rows:
    if NONVENDOR.search(r["vendor_name"]) and r["contract_number"].strip() in ("", "DV"):  # direct vouchers to pensions/banks/govts
        continue
    a = float(r["amount"]); m = r["check_date"][:2] + "/" + r["check_date"][-4:]
    k = (r["vendor_name"].strip().upper(), r["contract_number"].strip() or "DV")
    by_vc[k] += a; by_vcm[k + (m,)] += a; by_v[r["voucher_number"]] += a
def stat(d):
    o = {k: v for k, v in d.items() if v >= T}
    return {"count": len(o), "dollars": round(sum(o.values()))}
out = {"vendor_contract": stat(by_vc), "vendor_contract_month": stat(by_vcm), "voucher": stat(by_v),
       "top_vouchers": sorted(([round(v), k] for k, v in by_v.items() if v >= T), reverse=True)[:12],
       "note": "2025 checks, direct vouchers to pension funds, banks, treasurers and governments excluded"}
json.dump(out, open(f"{ROOT}/raw/leaves/leaves_payment_floor.json", "w"), indent=1)
print(json.dumps({k: out[k] for k in ("vendor_contract", "vendor_contract_month", "voucher")}))
for v, k in out["top_vouchers"][:8]:
    m = next(r for r in rows if r["voucher_number"] == k)
    print(v, k, m["vendor_name"][:40], m["contract_number"])
