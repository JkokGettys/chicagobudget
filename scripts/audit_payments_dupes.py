#!/usr/bin/env python3
"""Final audit: quantify exact duplicate rows and date spread in raw/city_payments_2025.csv, and how much of the duplicated money sits in
vendor contracts that appear as >= $10M leaves. Read-only; prints numbers."""
import csv, collections, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
rows = list(csv.DictReader(open(f"{ROOT}/raw/city_payments_2025.csv")))
tot = sum(float(r["amount"]) for r in rows)
print("rows", len(rows), "total", round(tot))
yrs = collections.Counter(r["check_date"][-4:] for r in rows)
print("check_date year counts", dict(yrs))
c = collections.Counter(tuple(r.values()) for r in rows)
dup_rows = sum(n - 1 for n in c.values() if n > 1)
dup_amt = sum((n - 1) * float(k[1]) for k, n in c.items() if n > 1)
print("exact duplicate extra rows", dup_rows, "dollars", round(dup_amt))
by_c = collections.defaultdict(float)
for k, n in c.items():
    if n > 1: by_c[(k[5], k[4])] += (n - 1) * float(k[1])
print("dup dollars with no contract/direct voucher DV:", round(sum(v for (vn, cn), v in by_c.items() if cn == "DV")))
for (vn, cn), v in sorted(by_c.items(), key=lambda x: -x[1])[:8]: print("  ", vn[:45], cn, round(v))
big = [(vn, cn, v) for (vn, cn), v in by_c.items() if v >= 10_000_000]
print("vendor-contract pairs with >= $10M of duplicate rows:", len(big))
neg = sum(float(r["amount"]) for r in rows if float(r["amount"]) < 0)
print("negative rows total", round(neg))
nodept = sum(float(r["amount"]) for r in rows if not r["department_name"])
print("no department dollars", round(nodept))

# Which >= $10M named vendor pieces in the leaves inventory are inflated by duplicate rows?
import json, re
d = json.load(open(f"{ROOT}/data/leaves_over_10m.json"))
dup_by_contract = collections.defaultdict(float); paid_by_contract = collections.defaultdict(float)
for k, n in c.items():
    if n > 1: dup_by_contract[k[4]] += (n - 1) * float(k[1])
for r in rows: paid_by_contract[r["contract_number"]] += float(r["amount"])
print("\nNamed vendor pieces >= $10M (2025 payments) with duplicate rows inside:")
tot_piece = tot_dup = 0
for p in d["remaining_pieces_over_10m"]:
    m = re.search(r"\(contract (\w+)\)", p["piece"] or "")
    if m and dup_by_contract.get(m.group(1), 0) > 0:
        dd = dup_by_contract[m.group(1)]; tot_piece += p["amount"]; tot_dup += dd
        print(f"  contract {m.group(1):>7} piece ${p['amount']/1e6:6.1f}M, duplicate rows ${dd/1e6:5.2f}M, piece without them ${(p['amount']-dd)/1e6:6.1f}M  {p['piece'][:40]}")
print(f"  total pieces ${tot_piece/1e6:.1f}M, duplicate rows inside ${tot_dup/1e6:.2f}M")
