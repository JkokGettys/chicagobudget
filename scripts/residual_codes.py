"""Transfer-residual investigation, part 6: 3-book exact search keyed on numeric account codes.

Part 3 keyed appropriation lines on account TEXT, which is abbreviated in the recommendations dataset
(axxr-vais), so the recommendations book could not be used there. Here appropriation lines are keyed on
(fund, department number, authority, account code), which is stable across books, so the residual must
be matched in all THREE books at once: 2025 ord, 2026 rec, 2026 ord.

Candidates: every revenue line (fund, source) and every appropriation line (fund, dept, account code)
outside the sets already inside the FG line / Appendix A+B. Targets (3-vectors, order 25, rec, ord):
  T0 = residual                       (60,581,630 ; 269,647,787 ; 152,502,787)
  T1 = residual - matching funds      (36,582,371 ; 234,133,502 ; 116,988,502)
Search subsets of size 1..3 (lookup-based). Chance calibration against decoy targets (+1,000,003).
Extra synthetic candidates allowed: the rec-only 117,145,000 (the Library term-note double-count idea).

Run: python3 scripts/residual_codes.py
"""
import json
import os
import re
from collections import defaultdict

from residual_pool import BOOKS, PRINTED, revenue

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
J = lambda *p: json.load(open(os.path.join(RAW, *p)))
SRC = {"25": (J("gap", "approp_2025.json"), lambda x: round(float(x["_ordinance_amount_"]))),
       "rec": (J("gap", "recs_approp_2026.json"), lambda x: round(float(x["recommendation"] or 0))),
       "ord": (J("city_appropriations_2026.json"), lambda x: int(x["_ordinance_amount_"]))}

# lines already inside FG line / Appendix A+B / matching funds, found by account TEXT in each book
EXPL = re.compile(r"PENSION ALLOCATION|ADVANCE PENSION|^TO REIMBURSE|^REIMB( -|\s+MIDWAY)|^TRANSFER|"
                  r"MATCHING AND SUPP|^FOR SERVICES PROVIDED BY|^TRANSFER FOR SERVICES", re.I)
A = defaultdict(lambda: dict.fromkeys(BOOKS, 0))
for b, (rows, f) in SRC.items():
    for x in rows:
        t = x["appropriation_account_description"]
        fgx = x["department_description"] == "Finance General"
        if EXPL.search(t) and (fgx or "SERVICES PROVIDED" in t.upper() or "MATCHING" in t.upper()):
            continue
        A[("APP", x["fund_code"], x["department_number"], x["appropriation_account"])][b] += f(x)

R = revenue()
cands = {k: tuple(v[b] for b in BOOKS) for k, v in R.items() if not re.search("Pension Allocation|Advance Pension", k[2])}
cands.update({k: tuple(v[b] for b in BOOKS) for k, v in A.items()})
cands[("SYN", "rec-only 117,145,000", "")] = (0, 117_145_000, 0)
cands = {k: v for k, v in cands.items() if any(v)}
items = list(cands.items())
n = len(items)
print("candidates:", n)

P = PRINTED
T0 = tuple(P[b]["resid"] for b in BOOKS)
T1 = tuple(P[b]["resid_after_match"] for b in BOOKS)
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


for label, T in (("T0 residual", T0), ("T1 residual - matching", T1),
                 ("T2 T1 - Corp 'Transfers Out' (350k)", tuple(t - 350_000 for t in T1))):
    h = search(T)
    d = search(tuple(t + 1_000_003 for t in T))
    print(f"\n{label}: target {T}\n   exact hits (<=3 lines): {len(h)}  decoy hits: {len(d)}")
    for s in sorted(h)[:8]:
        print("     ", [items[i][0] for i in s])
