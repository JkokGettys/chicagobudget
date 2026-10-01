"""Transfer-residual investigation, part 8: add the 2024 ordinance as a third (tolerant) book.

The 2024 ordinance deduction is only printed to $0.1M in the 2025 Overview p.29 ($1,451.4M after
removing $117.1M debt), so the 2024 residual is known to about +-60,000 (rounding of the deduction plus
uncertainty in Appendix A/B, which I proxy with the 'For Services Provided by' data rule).
Search: subsets of size 1..3 matching (2025 ord, 2026 ord) EXACTLY and 2024 within TOL.
Targets: residual and residual - matching funds. Candidates keyed on numeric account codes.

Run: python3 scripts/residual_2024.py   (needs raw/residual/ord2024.json, revord2024.json)
"""
import json
import os
import re
from collections import defaultdict

from residual_pool import PRINTED

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
J = lambda *p: json.load(open(os.path.join(RAW, *p)))
TOL = 100_000
BK = ("24", "25", "ord")
SRC = {"24": (J("residual", "ord2024.json"), "_ordinance_amount_"),
       "25": (J("gap", "approp_2025.json"), "_ordinance_amount_"),
       "ord": (J("city_appropriations_2026.json"), "_ordinance_amount_")}
REVS = {"24": J("residual", "revord2024.json"), "25": J("gap", "revenue_2025.json"), "ord": J("context", "revenue_2026.json")}
EXPL = re.compile(r"PENSION ALLOCATION|ADVANCE PENSION|^TO REIMBURSE|^TRANSFER|MATCHING AND SUPP|^FOR SERVICES PROVIDED BY", re.I)
C = defaultdict(lambda: dict.fromkeys(BK, 0))
for b, (rows, k) in SRC.items():
    for x in rows:
        t = x["appropriation_account_description"]
        if EXPL.search(t) and (x["department_description"] == "Finance General" or re.search("SERVICES PROVIDED|MATCHING", t, re.I)):
            continue
        C[("APP", x["fund_code"], x["department_number"], x["appropriation_account"])][b] += round(float(x[k]))
for b, rows in REVS.items():
    for x in rows:
        if re.search("Pension Allocation|Advance Pension", x["revenue_source"]):
            continue
        C[("REV", x["fund_code"], x["revenue_source"])][b] += round(float(x["estimated_revenue"]))
items = [(k, tuple(v[b] for b in BK)) for k, v in C.items() if any(v.values())]
n = len(items)
print("candidates:", n)

# 2024 residual (approximate): deduction 1,451.4M +-0.05M
rows24 = SRC["24"][0]
amt = lambda x: round(float(x["_ordinance_amount_"]))
fg24 = 0
for x in rows24:
    if x["department_description"] != "Finance General":
        continue
    nme = x["appropriation_account_description"].upper()
    a = amt(x)
    if "PENSION ALLOCATION" in nme or "ADVANCE PENSION" in nme or nme.startswith("TO REIMBURSE") or \
            (nme.startswith("TRANSFER") and not (nme == "TRANSFERS OUT" and x["fund_code"] == "0100")):
        fg24 += a
svc24 = sum(amt(x) for x in rows24 if x["department_description"] != "Finance General" and x["fund_type"] == "LOCAL"
            and x["appropriation_account_description"].upper().startswith("FOR SERVICES PROVIDED BY")
            and "PERFORMERS" not in x["appropriation_account_description"].upper())
match24 = sum(amt(x) for x in rows24 if "MATCHING AND SUPP" in x["appropriation_account_description"].upper())
r24 = 1_451_400_000 - fg24 - svc24
print(f"2024 residual ~ {r24:,}  (after matching {r24 - match24:,})")

by = defaultdict(list)
for i, (_, v) in enumerate(items):
    by[v[1:]].append(i)


def search(t24, t25, t26):
    hits = set()
    tgt = (t25, t26)
    for i in range(n):
        vi = items[i][1]
        for j in range(i, n + 0):
            if j == i:
                continue
            s = tuple(a + b for a, b in zip(vi, items[j][1]))
            if s[1:] == tgt and abs(s[0] - t24) <= TOL:
                hits.add((i, j))
            need = (tgt[0] - s[1], tgt[1] - s[2])
            for m in by.get(need, ()):
                if m > j and abs(vi[0] + items[j][1][0] + items[m][1][0] - t24) <= TOL:
                    hits.add((i, j, m))
    return hits


P = PRINTED
for label, t24, t25, t26 in (("residual", r24, P["25"]["resid"], P["ord"]["resid"]),
                             ("residual - matching", r24 - match24, P["25"]["resid_after_match"], P["ord"]["resid_after_match"])):
    h = search(t24, t25, t26)
    d = search(t24, t25 + 1_000_003, t26)
    print(f"{label}: ({t24:,}, {t25:,}, {t26:,}) hits {len(h)}  decoy hits {len(d)}")
    for s in sorted(h)[:5]:
        print("    ", [items[i][0] for i in s])
