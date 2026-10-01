#!/usr/bin/env python3
"""Round 3, item 2f: split single large City contracts and big vendor payments to the lowest public level, the check (voucher).

Reads  data/city_vendors_items_<basis>.json (vendor x contract totals), the deduplicated payments file for the same basis
       (raw/contracts/payments_2026ytd_dedup.csv or payments_2025_dedup.csv, made by scripts/payments_dedupe.py),
       raw/contracts/contracts_all.csv (Contracts rsxa-ify5, one row per revision_number).
Basis: default 2026ytd (Jan 1 to the latest 2026 check date, partial year, not annualized). Run with --basis 2025 for the 2025 view.
       The output keys keep their old names (paid_2025_item, paid_2025, vouchers_2025 ...) and hold the dollars of the chosen basis, see meta.basis.
Fetches (cached in raw/leaves/r3/) https://data.cityofchicago.org/resource/rsxa-ify5.json?purchase_order_contract_number=N for the named contracts to
confirm every revision, and records the HTTP status.
Writes data/leaves_contracts.json:
  voucher_floor : for every 2025 vendor x contract total >= $10M, the single vouchers (checks) that are still >= $10M
  contracts     : revision history (award amount per revision_number), 2025 and all-years paid, largest voucher, vouchers >= $10M
A voucher is the sum of its payment lines (one check). Payments stop at the voucher, so a voucher >= $10M is the floor."""
import argparse, csv, json, os, re, sys, urllib.request, urllib.parse
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from payments_dedupe import dedupe_rows  # noqa: E402
ap = argparse.ArgumentParser()
ap.add_argument("--basis", choices=["2026ytd", "2025"], default="2026ytd")
ARGS = ap.parse_args()
BASIS = ARGS.basis
ITEMS_FILE = {"2026ytd": "data/city_vendors_items_2026ytd.json", "2025": "data/city_vendors_items_2025.json"}[BASIS]
PAY_FILE = {"2026ytd": "raw/contracts/payments_2026ytd_dedup.csv", "2025": "raw/contracts/payments_2025_dedup.csv"}[BASIS]
OUT_FILE = {"2026ytd": "data/leaves_contracts.json", "2025": "data/leaves_contracts_2025basis.json"}[BASIS]
T = 10_000_000
os.makedirs(f"{ROOT}/raw/leaves/r3", exist_ok=True)
items = json.load(open(f"{ROOT}/{ITEMS_FILE}"))
pays = list(csv.DictReader(open(f"{ROOT}/{PAY_FILE}")))
allp, _dropped_all = dedupe_rows(list(csv.DictReader(open(f"{ROOT}/raw/contracts/payments_all.csv"))))  # all-years totals use the same dedupe rule
contracts = list(csv.DictReader(open(f"{ROOT}/raw/contracts/contracts_all.csv")))

def vouchers(rows):
    v = defaultdict(lambda: {"amount": 0.0, "date": None, "dept": None})
    for r in rows:
        x = v[r["voucher_number"]]; x["amount"] += float(r["amount"]); x["date"] = x["date"] or r["check_date"]; x["dept"] = x["dept"] or r["department_name"]
    return v

by_contract = defaultdict(list); by_dv = defaultdict(list)
for r in pays:
    c = r["contract_number"].strip()
    if c and c != "DV": by_contract[c].append(r)
    else: by_dv[r["vendor_name"].strip().upper()].append(r)

floor = {}
named = set()
for d in items["departments"].values():
    for fam, its in d["families"].items():
        for it in its:
            name, c, amt = it[0], it[1], it[2]
            if amt < T: continue
            if c: key = f"{c}"; rows = [r for r in by_contract.get(str(c), [])]
            else: key = "DV|" + name.strip().upper(); rows = by_dv.get(name.strip().upper(), [])
            if c: named.add(str(c))
            vs = vouchers(rows)
            big = sorted(({"voucher": k, "amount": round(x["amount"], 2), "check_date": x["date"]} for k, x in vs.items() if x["amount"] >= T), key=lambda z: -z["amount"])
            floor[key] = {"vendor": name, "paid_2025_item": round(amt), "paid_2025_vouchers": round(sum(x["amount"] for x in vs.values())), "n_vouchers": len(vs),
                          "vouchers_ge_10m": big, "largest_voucher": round(max([x["amount"] for x in vs.values()] or [0]), 2)}

# revision history for contracts named in the round 2 remaining pieces
NAMED = ["283596", "234083", "265292", "198906", "25743", "111685", "174908", "69568", "47314", "101451", "52685", "190841", "27075", "176561"]
out_c = []; log = []
for num in NAMED:
    url = "https://data.cityofchicago.org/resource/rsxa-ify5.json?" + urllib.parse.urlencode({"purchase_order_contract_number": num, "$limit": 100})
    cache = f"{ROOT}/raw/leaves/r3/rsxa_{num}.json"
    try:
        if not os.path.exists(cache):
            with urllib.request.urlopen(url, timeout=60) as r:
                open(cache, "wb").write(r.read()); st = r.status
        else: st = "cached 200"
        revs = json.load(open(cache))
    except Exception as e:
        st = f"error {e}"; revs = [r for r in contracts if r["purchase_order_contract_number"] == num]
    log.append({"url": url, "http_status": st, "revisions": len(revs)})
    revs = sorted(revs, key=lambda r: int(r.get("revision_number") or 0))
    p_all = vouchers([r for r in allp if r["contract_number"] == num])
    p25 = vouchers(by_contract.get(num, []))
    out_c.append({"contract": num, "vendor": revs[0].get("vendor_name") if revs else None, "description": (revs[0].get("purchase_order_description") if revs else "")[:90],
                  "department": revs[0].get("department") if revs else None,
                  "revisions": [{"revision_number": r.get("revision_number"), "award_amount": float(r.get("award_amount") or 0), "approval_date": (r.get("approval_date") or "")[:10]} for r in revs],
                  "total_award_all_revisions": sum(float(r.get("award_amount") or 0) for r in revs),
                  "paid_all_years_payments_all": round(sum(x["amount"] for x in p_all.values())), "vouchers_all_years": len(p_all),
                  "paid_2025": round(sum(x["amount"] for x in p25.values())), "vouchers_2025": len(p25),
                  "largest_voucher_2025": round(max([x["amount"] for x in p25.values()] or [0]), 2),
                  "vouchers_2025_ge_10m": sorted([{"voucher": k, "amount": round(x["amount"], 2), "check_date": x["date"]} for k, x in p25.items() if x["amount"] >= T], key=lambda z: -z["amount"])})
n_pc = len(floor); n_big = sum(len(v["vouchers_ge_10m"]) for v in floor.values())
LABEL = items.get("meta", {}).get("label", BASIS)
res = {"meta": {"generated_by": "scripts/leaves_contracts.py", "basis": f"{LABEL}. Payments s4vu-giwb, duplicates removed (scripts/payments_dedupe.py), file {PAY_FILE}. A voucher is one check (sum of its lines). Revision history from Contracts rsxa-ify5. Keys named *_2025 hold this basis's dollars.", "basis_id": BASIS, "payments_deduplicated": True,
                "sources_fetched": log, "vendor_contract_items_ge_10m": n_pc, "vouchers_still_ge_10m": n_big,
                "vouchers_ge_10m_dollars": round(sum(v["amount"] for f in floor.values() for v in f["vouchers_ge_10m"])),
                "caveat": ("Payments are 2026 checks Jan 1 to the latest check date (partial year, not annualized), matched to the 2026 budget. " if BASIS == "2026ytd" else "Payments are 2025 checks, not 2026 budget. ") + "A voucher at or above $10M cannot be split further with public data."},
       "voucher_floor": floor, "contracts": out_c}
json.dump(res, open(f"{ROOT}/{OUT_FILE}", "w"), indent=1)
print(json.dumps(res["meta"], indent=1)[:900])
for c in out_c: print(c["contract"], c["vendor"][:28], "revs", len(c["revisions"]), "award", round(c["total_award_all_revisions"]/1e6,1), "paid25", round(c["paid_2025"]/1e6,1), "v>=10M", len(c["vouchers_2025_ge_10m"]))
