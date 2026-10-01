"""Transfer-residual investigation, part 10: single-book search restricted to lines stable between books.

Exact identity (see residual_recdelta.py): residual(rec) - 117,145,000 == residual(ord) == 152,502,787.
So the unexplained 2026 amount X is the same number in both books once the rec-only 117,145,000 is set
aside, meaning X should be built from lines that did NOT change between the recommendations and the
ordinance (advance pension, Library debt, fines, lease tax, etc. all changed and so cannot be in X).
Candidates: revenue lines (fund, source) and appropriation lines (fund, dept, authority, account code)
with rec == ord != 0, EXCLUDING lines already explained (FG pension/reimburse/transfer, services-provided-by,
matching funds). Search subsets of size 1..4 (meet in the middle on pairs) for
  X0 = 152,502,787   and   X1 = 116,988,502 (after matching funds)   and X1 - 350,000.
Chance calibration: decoy targets X + 1,000,003 and X + 2,000,011.

Run: python3 scripts/residual_stable.py
"""
import json
import os
import re
from collections import defaultdict

from residual_pool import PRINTED, revenue

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
J = lambda *p: json.load(open(os.path.join(RAW, *p)))
rec, ordr = J("gap", "recs_approp_2026.json"), J("city_appropriations_2026.json")
EXPL = re.compile(r"PENSION ALLOCATION|ADVANCE PENSION|^TO REIMBURSE|^REIMB( -|\s+MIDWAY)|^TRANSFER|MATCHING AND SUPP|^FOR SERVICES PROVIDED BY", re.I)
O, Rr = defaultdict(int), defaultdict(int)
for rows, D, f in ((ordr, O, lambda x: int(x["_ordinance_amount_"])), (rec, Rr, lambda x: round(float(x["recommendation"] or 0)))):
    for x in rows:
        t = x["appropriation_account_description"]
        if EXPL.search(t) and (x["department_description"] == "Finance General" or re.search("SERVICES PROVIDED|MATCHING", t, re.I)):
            continue
        D[("APP", x["fund_code"], x["department_number"], x["appropriation_authority"], x["appropriation_account"])] += f(x)
items = [(k, O[k]) for k in O if O[k] and O[k] == Rr.get(k, None)]
for k, v in revenue().items():
    if v["rec"] == v["ord"] and v["ord"] and not re.search("Pension Allocation|Advance Pension", k[2]):
        items.append((k, v["ord"]))
n = len(items)
print("stable candidate lines:", n)
singles = defaultdict(list)
for i, (_, v) in enumerate(items):
    singles[v].append(i)
pairs = defaultdict(list)
for i in range(n):
    for j in range(i + 1, n):
        pairs[items[i][1] + items[j][1]].append((i, j))
print("pair sums:", sum(len(v) for v in pairs.values()))


def search(t):
    hits = set()
    for i in singles.get(t, ()):
        hits.add((i,))
    for p in pairs.get(t, ()):
        hits.add(p)
    for a, la in singles.items():
        for m in pairs.get(t - a, ()):
            for i in la:
                if i not in m:
                    hits.add(tuple(sorted((i,) + m)))
    for a, la in pairs.items():
        for m in pairs.get(t - a, ()):
            for p in la:
                if not set(p) & set(m):
                    hits.add(tuple(sorted(p + m)))
    return hits


X0, X1 = PRINTED["ord"]["resid"], PRINTED["ord"]["resid_after_match"]
for label, t in (("X0 residual", X0), ("X1 residual - matching", X1), ("X1 - Corp Transfers Out 350k", X1 - 350_000)):
    h = search(t)
    d1, d2 = search(t + 1_000_003), search(t + 2_000_011)
    print(f"{label} {t:,}: exact hits {len(h)}   decoy hits {len(d1)}, {len(d2)}")
    for s in sorted(h, key=len)[:8]:
        print("    ", [(items[i][0], items[i][1]) for i in s])
