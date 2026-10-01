"""Transfer-residual investigation, part 9: what changed between the recommendations and the ordinance.

Exact identity (asserted here and in gap_reconcile.py):
  deduction(ord) - deduction(rec) = d(advance pension) + d(Appendix A internal) - 117,145,000
Everything on the right except 117,145,000 is an itemised line. Question: is the -117,145,000 produced by
some set of lines that CHANGED between the two books (so the amendment package explains it)?
Search: all lines whose amount differs between the recs and the ordinance (appropriations keyed on numeric
codes, revenue keyed on fund+source), advance-pension lines excluded (already in the identity), for subsets
of size 1..4 summing to exactly -117,145,000 (and to +117,145,000), plus decoys for calibration.

Run: python3 scripts/residual_recdelta.py
"""
import json
import os
import re
from collections import defaultdict

from residual_pool import PRINTED, revenue

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
J = lambda *p: json.load(open(os.path.join(RAW, *p)))
rec, ordr = J("gap", "recs_approp_2026.json"), J("city_appropriations_2026.json")
assert PRINTED["ord"]["deduct"] - PRINTED["rec"]["deduct"] == 21_037_820

D = defaultdict(int)
for x in ordr:
    D[("APP", x["fund_code"], x["department_number"], x["appropriation_authority"], x["appropriation_account"])] += int(x["_ordinance_amount_"])
for x in rec:
    D[("APP", x["fund_code"], x["department_number"], x["appropriation_authority"], x["appropriation_account"])] -= round(float(x["recommendation"] or 0))
for k, v in revenue().items():
    d = v["ord"] - v["rec"]
    if d and not re.search("Advance Pension", k[2]):
        D[k] = d
items = [(k, v) for k, v in D.items() if v]
print("changed lines (excl. advance pension revenue):", len(items))
print("appropriation total change:", sum(v for k, v in items if k[0] == "APP"))
# appropriation lines with advance pension (account text) are in items too, but account codes are shared with other
# lines, so remove them by exact account code of the five advance-payment lines
adv_codes = {(x["fund_code"], x["department_number"], x["appropriation_authority"], x["appropriation_account"])
             for x in ordr if "Advance Pension Payment" in x["appropriation_account_description"]}
items = [(k, v) for k, v in items if not (k[0] == "APP" and k[1:] in adv_codes)]
print("after removing advance pension appropriation lines:", len(items))

by = defaultdict(list)
for i, (_, v) in enumerate(items):
    by[v].append(i)
n = len(items)


def search(t, maxk=3):
    hits = set()
    for i in range(n):
        if items[i][1] == t:
            hits.add((i,))
        for j in range(i + 1, n):
            s = items[i][1] + items[j][1]
            if s == t:
                hits.add((i, j))
            for m in by.get(t - s, ()):
                if m > j:
                    hits.add((i, j, m))
    return hits


for t in (-117_145_000, 117_145_000):
    h, d = search(t), search(t + 1_000_003)
    print(f"target {t:,}: exact hits {len(h)}, decoy hits {len(d)}")
    for s in sorted(h)[:6]:
        print("   ", [(items[i][0], items[i][1]) for i in s])

# also: which lines are exactly +-117,145,000 in either book?
for name, rows, key in (("rec", rec, "recommendation"), ("ord", ordr, "_ordinance_amount_")):
    big = [(x["fund_code"], x["department_description"], x["appropriation_account_description"][:60]) for x in rows
           if round(float(x[key] or 0)) == 117_145_000]
    print(name, "lines equal to 117,145,000:", big)
