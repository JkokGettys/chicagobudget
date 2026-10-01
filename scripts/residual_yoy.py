"""Transfer-residual investigation, part 4: year-over-year structure and delta search.

Corrected reading of the 2025 Overview p.29 table: 2025 proposed book deducts transfers $1,322.5M
(+ debt $117.1M = $1,439.6M footnote) and the 2024 ordinance deducts $1,451.4M (+ $117.1M = $1,568.6M).
Printed in $0.1M, so 2024/2025-rec residuals are only known to +-50,000.

Part A: residual per book (FG interfund line + Appendix A/B subtracted).
Part B: residual(2026) - residual(2025 ordinance), for rec and ord, as a target; search subsets (size<=3) of
        line-level year-over-year changes that equal it exactly.

Run: python3 scripts/residual_yoy.py   (needs raw/residual/*.json: python3 scripts/residual_fetch.py)
"""
import json
import os
import re
from collections import defaultdict

from residual_pool import PRINTED, approps, revenue

RES = os.path.join(os.path.dirname(__file__), "..", "raw", "residual")


def fg_line(rows, amt):
    pen = rei = trn = 0
    for x in rows:
        if x["department_description"] != "Finance General":
            continue
        n = x["appropriation_account_description"].upper()
        a = amt(x)
        if "PENSION ALLOCATION" in n or "ADVANCE PENSION PAY" in n:
            pen += a
        elif n.startswith("TO REIMBURSE") or re.match(r"REIMB( -|\s+MIDWAY)", n):
            rei += a
        elif n.startswith("TRANSFER") and not (n == "TRANSFERS OUT" and x["fund_code"] == "0100"):
            trn += a
    return pen + rei + trn


def svc(rows, amt):
    return sum(amt(x) for x in rows if x["department_description"] != "Finance General" and x["fund_type"] == "LOCAL"
               and x["appropriation_account_description"].upper().startswith("FOR SERVICES PROVIDED BY")
               and "PERFORMERS" not in x["appropriation_account_description"].upper())


def match(rows, amt):
    return sum(amt(x) for x in rows if "MATCHING AND SUPP" in x["appropriation_account_description"].upper())


def L(p):
    return json.load(open(p))


raw = os.path.join(os.path.dirname(__file__), "..", "raw")
BOOKS = [
    # name, rows, amount key, printed deduction (None = rounded to $0.1M), appendix A+B (None = use svc rule)
    ("2024 ord", L(f"{RES}/ord2024.json"), "_ordinance_amount_", 1_451_400_000),
    ("2025 rec", L(f"{RES}/rec2025.json"), "recommendation", 1_322_500_000),
    ("2025 ord", L(f"{raw}/gap/approp_2025.json"), "_ordinance_amount_", 1_622_468_611),
    ("2026 rec", L(f"{raw}/gap/recs_approp_2026.json"), "recommendation", 1_679_051_626),
    ("2026 ord", L(f"{raw}/city_appropriations_2026.json"), "_ordinance_amount_", 1_700_089_446),
]
print(f"{'book':<9}{'printed deduct':>16}{'FG line':>16}{'App A+B*':>12}{'residual':>14}{'matching':>12}{'resid-match':>14}")
res = {}
for name, rows, k, ded in BOOKS:
    amt = lambda x, k=k: round(float(x.get(k) or 0))
    fg, m = fg_line(rows, amt), match(rows, amt)
    # Appendix A/B: rec books label them differently; use the printed-in-the-text values where known
    ab = {"2024 ord": svc(rows, amt), "2025 rec": None, "2025 ord": 18_374_786, "2026 rec": 19_927_176, "2026 ord": 18_678_776}[name]
    if ab is None:
        ab = 18_374_786      # 2025 rec appendix not fetched: 2025 ord value is the closest known (flagged below)
    r = ded - fg - ab
    res[name] = r
    approx = "~" if name in ("2024 ord", "2025 rec") else " "
    print(f"{name:<9}{approx}{ded:>15,}{fg:>16,}{ab:>12,}{approx}{r:>13,}{m:>12,}{approx}{r - m:>13,}")
print("(~ = printed only to $0.1M in the Overview; 2025 rec Appendix assumed = 2025 ord value)")

# exact facts
assert PRINTED["ord"]["resid"] == res["2026 ord"]
assert PRINTED["25"]["resid"] == res["2025 ord"]
d25 = BOOKS[2][3] - BOOKS[1][3]
print(f"\n2025: deduction rec->ord changed by ~{d25:,}; FG line changed by "
      f"{fg_line(BOOKS[2][1], lambda x: round(float(x['_ordinance_amount_']))) - fg_line(BOOKS[1][1], lambda x: round(float(x['recommendation'] or 0))):,}"
      " (exactly 300,000,000): residual is the same in rec and ord to within rounding.")

# Part B: yoy delta search
R = revenue()
A, _ = approps()
tgt_ord = PRINTED["ord"]["resid"] - PRINTED["25"]["resid"]
tgt_rec = PRINTED["rec"]["resid"] - PRINTED["25"]["resid"]
print(f"\nresidual(2026 ord) - residual(2025 ord) = {tgt_ord:,};  residual(2026 rec) - residual(2025 ord) = {tgt_rec:,}")
explained = re.compile(r"pension allocation|advance pension|^to reimburse|^transfer|^for services provided by|"
                       r"^american rescue plan revenue|^for the city's (advance )?contribution|^reimb|^transfer", re.I)
items = []
for k, v in R.items():
    items.append((k, v["ord"] - v["25"], v["rec"] - v["25"]))
grp = defaultdict(lambda: [0, 0])
for k, v in A.items():
    if explained.search(k[3]):
        continue
    g = grp[("APP", k[1], k[3])]
    g[0] += v["ord"] - v["25"]
    g[1] += v["rec"] - v["25"]
for k, v in grp.items():
    items.append((k, v[0], v[1]))
items = [t for t in items if t[1] or t[2]]
print("delta candidate lines:", len(items))
for label, col, tgt in (("ord", 1, tgt_ord), ("rec", 2, tgt_rec)):
    idx = defaultdict(list)
    for i, t in enumerate(items):
        idx[t[col]].append(i)
    hits = []
    n = len(items)
    for i in range(n):
        if items[i][col] == tgt:
            hits.append((i,))
        for j in range(i + 1, n):
            s = items[i][col] + items[j][col]
            if s == tgt:
                hits.append((i, j))
            for m in idx.get(tgt - s, ()):
                if m > j:
                    hits.append((i, j, m))
    print(f"  {label}: target {tgt:,} -> {len(hits)} hit(s) with <=3 lines (of {n} lines; a handful expected by chance)")
    for h in hits[:6]:
        print("     ", [(items[x][0], items[x][col]) for x in h])
