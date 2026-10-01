"""Transfer-residual investigation, part 7: coarser building blocks (fund totals, object classes, groups).

Adds aggregates as candidates, not just single lines: per-fund appropriation totals, per-fund revenue
totals, per (fund, department) totals for Finance General, per revenue group (Internal Service Earnings
etc.), and per-fund sums of accounts in the 9xxx "Transfers and Reimbursements" object classes.
3-book exact search (25, rec, ord), sizes 1..3, with decoy calibration.

Run: python3 scripts/residual_fundtotals.py
"""
import json
import os
from collections import defaultdict

from residual_pool import BOOKS, PRINTED, revenue

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
J = lambda *p: json.load(open(os.path.join(RAW, *p)))
SRC = {"25": (J("gap", "approp_2025.json"), lambda x: round(float(x["_ordinance_amount_"]))),
       "rec": (J("gap", "recs_approp_2026.json"), lambda x: round(float(x["recommendation"] or 0))),
       "ord": (J("city_appropriations_2026.json"), lambda x: int(x["_ordinance_amount_"]))}
C = defaultdict(lambda: dict.fromkeys(BOOKS, 0))
for b, (rows, f) in SRC.items():
    for x in rows:
        a = f(x)
        C[("approp fund", x["fund_code"])][b] += a
        C[("approp fund-type", x["fund_type"])][b] += a
        C[("approp fund,dept", x["fund_code"], x["department_number"])][b] += a
        if x["appropriation_account"][:2] in ("94", "95", "96"):
            C[("approp 94-96xx", x["fund_code"])][b] += a
        if x["department_description"] == "Finance General":
            C[("FG fund", x["fund_code"])][b] += a
rev_rows = {"25": J("gap", "revenue_2025.json"), "rec": J("context", "revenue_rec_2026.json"), "ord": J("context", "revenue_2026.json")}
for b, rows in rev_rows.items():
    for x in rows:
        v = round(float(x["estimated_revenue"]))
        C[("rev fund", x["fund_code"])][b] += v
        if x.get("revenue_category") and x.get("revenue_group_type") in ("Proceeds and Transfers In",):
            C[("rev group", x["revenue_group_type"])][b] += v
        if "Property Tax Levy" not in x["revenue_source"] and x["fund_code"] in ("0510", "0521", "0681", "0682", "0683", "0684"):
            C[("rev non-levy (Summary B 'Other Revenue')", x["fund_code"])][b] += v
            C[("rev non-levy, property-tax-supported funds", "all")][b] += v
        if x.get("revenue_category") == "Internal Service Earnings":
            C[("rev ISE", x["revenue_source"])][b] += v
for k, v in revenue().items():
    C[("REV",) + k[1:]] = v

items = [(k, tuple(v[b] for b in BOOKS)) for k, v in C.items() if any(v.values())]
n = len(items)
print("aggregate candidates:", n)
by = defaultdict(list)
for i, (_, v) in enumerate(items):
    by[v].append(i)


def search(tgt):
    hits = set()
    for i in range(n):
        vi = items[i][1]
        if vi == tgt:
            hits.add((i,))
        for j in range(i + 1, n):
            s = tuple(a + b for a, b in zip(vi, items[j][1]))
            if s == tgt:
                hits.add((i, j))
            need = tuple(t - x for t, x in zip(tgt, s))
            for m in by.get(need, ()):
                if m > j:
                    hits.add((i, j, m))
    return hits


P = PRINTED
for label, T in (("residual", tuple(P[b]["resid"] for b in BOOKS)),
                 ("residual - matching", tuple(P[b]["resid_after_match"] for b in BOOKS)),
                 ("printed deduction minus pension revenue", tuple(P[b]["deduct"] - P[b]["fg_line"] + (P[b]["fg_line"] - 0) * 0 for b in BOOKS))):
    h, d = search(T), search(tuple(t + 1_000_003 for t in T))
    print(f"{label}: {T} exact hits {len(h)}, decoy hits {len(d)}")
    for s in sorted(h)[:5]:
        print("    ", [items[i][0] for i in s])
