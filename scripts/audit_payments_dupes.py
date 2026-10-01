#!/usr/bin/env python3
"""Audit duplicate rows in City payment files. Read-only; prints numbers.
Usage: python3 scripts/audit_payments_dupes.py [file.csv ...]
Default: the two DEDUPED files (raw/contracts/payments_2025_dedup.csv and payments_2026ytd_dedup.csv). Pass raw/city_payments_2025.csv to see the before picture.
Checks per file: rows, total, check_date years, exact duplicate rows, loose-key repeats (voucher + amount + date + vendor + contract, department ignored),
repeats left outside the $99M exemption (should be 0 in a deduped file), negatives, dollars with no department.
Then: named vendor pieces >= $10M in data/leaves_over_10m.json, matched by contract number against the LAST file given (default: the 2026 YTD deduped file,
which is the basis of the pieces), showing duplicate dollars still inside them.
History: before 2026-10-01 this script only read raw/city_payments_2025.csv, which no longer matches the pieces (they are 2026 YTD, deduped), so the piece check was comparing the wrong year."""
import csv, collections, os, sys, json, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
files = sys.argv[1:] or [f"{ROOT}/raw/contracts/payments_2025_dedup.csv", f"{ROOT}/raw/contracts/payments_2026ytd_dedup.csv"]
CHECK_CAP = 99_000_000
for path in files:
    rows = list(csv.DictReader(open(path)))
    print(f"\n=== {os.path.relpath(path, ROOT)} ===")
    print("rows", len(rows), "total", round(sum(float(r['amount']) for r in rows)))
    print("check_date year counts", dict(collections.Counter(r["check_date"][-4:] for r in rows)),
          "latest date", max((r["check_date"] for r in rows if len(r["check_date"]) == 10), key=lambda s: (s[6:], s[:2], s[3:5])))
    c = collections.Counter(tuple(r.values()) for r in rows)
    print("exact duplicate extra rows", sum(n - 1 for n in c.values() if n > 1), "dollars", round(sum((n - 1) * float(k[1]) for k, n in c.items() if n > 1)))
    loose = collections.Counter((r["voucher_number"], r["amount"], r["check_date"], r["vendor_name"], r["contract_number"]) for r in rows)
    rep = [(k, n) for k, n in loose.items() if n > 1]
    print("loose-key repeated extra rows", sum(n - 1 for k, n in rep), "dollars", round(sum((n - 1) * float(k[1]) for k, n in rep)),
          "| of which below the $99M exemption:", sum(n - 1 for k, n in rep if float(k[1]) < CHECK_CAP),
          round(sum((n - 1) * float(k[1]) for k, n in rep if float(k[1]) < CHECK_CAP)))
    print("negative rows total", round(sum(float(r['amount']) for r in rows if float(r['amount']) < 0)))
    print("no department dollars", round(sum(float(r['amount']) for r in rows if not r['department_name'])))
    print("rows with blank voucher_number", sum(1 for r in rows if not r["voucher_number"]))

# pieces >= $10M still carrying duplicate rows, checked against the last file (the basis of the pieces)
rows = list(csv.DictReader(open(files[-1])))
loose = collections.Counter((r["voucher_number"], r["amount"], r["check_date"], r["vendor_name"], r["contract_number"]) for r in rows)
dup_by_contract = collections.defaultdict(float)
for k, n in loose.items():
    if n > 1 and float(k[1]) < CHECK_CAP: dup_by_contract[k[4]] += (n - 1) * float(k[1])
d = json.load(open(f"{ROOT}/data/leaves_over_10m.json"))
print(f"\nNamed vendor pieces >= $10M in the leaves file with a contract number, repeats still inside ({os.path.basename(files[-1])}):")
n = tot_piece = tot_dup = 0
for p in d["remaining_pieces_over_10m"]:
    m = re.search(r"\(contract (\w+)\)", p["piece"] or "")
    if m:
        n += 1; tot_piece += p["amount"]; dd = dup_by_contract.get(m.group(1), 0); tot_dup += dd
        if dd > 0: print(f"  contract {m.group(1):>7} piece ${p['amount']/1e6:6.1f}M, repeats ${dd/1e6:5.2f}M  {p['piece'][:50]}")
print(f"  {n} contract pieces, ${tot_piece/1e6:.1f}M, repeats inside ${tot_dup/1e6:.2f}M")
