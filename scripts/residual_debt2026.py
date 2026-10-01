"""Transfer-residual investigation, part 12: Corporate Fund 2026 debt proceeds (rounded figures only).

Overview p.38 and the 2027 Forecast p.14 say the 2026 Corporate Fund includes about $166.0M of one-time
borrowing inside 'Proceeds and Transfers in - Other' ($194.0M = $28.0M Skyway/meter interest + $166.0M debt),
and the Forecast p.15 says the Fines line carries an assumed $89.6M 'from the sale of City debt'.
Those are rounded to $0.1M, so we can only test within a tolerance. 2025 had no such borrowing in the
Corporate Fund ('Proceeds and Transfers in - Other' was exactly $28.0M), yet 2025 still has a $60.6M residual.

Tests: does any simple combination of {166.0M, 89.6M, 28.0M, 50.5M (ISE intergovernmental), 10.87M (ISE other),
90,493,270 (bond fund subsidy), 25.0M (bond fund transfers in), 18,611,165 (Library transfers in), 125,926,011}
land within +-150,000 of the 2026 residual (152,502,787), of residual before Appendix (171,181,563), or of
residual minus matching (116,988,502)?  Prints every hit and how many a decoy (+3.7M) produces.

Run: python3 scripts/residual_debt2026.py
"""
import itertools

from residual_pool import PRINTED

C = {"166.0M debt (P&T In-Other)": 166_000_000, "89.6M debt (Fines)": 89_600_000, "28.0M Skyway/meter interest": 28_000_000,
     "ISE Intergov 50.5M": 50_500_000, "ISE Other Reimb 10,870,065": 10_870_065, "Bond subsidy 90,493,270": 90_493_270,
     "Bond Transfers In 25.0M": 25_000_000, "Library Transfers In 18,611,165": 18_611_165,
     "Library debt 125,926,011": 125_926_011}
T = {"residual 152,502,787": PRINTED["ord"]["resid"],
     "residual before App A+B 171,181,563": PRINTED["ord"]["resid"] + 18_678_776,
     "residual after matching 116,988,502": PRINTED["ord"]["resid_after_match"]}
TOL = 150_000
names = list(C)
for tn, t in T.items():
    for tag, tt in (("target", t), ("decoy", t + 3_700_000)):
        hits = [c for r in range(1, len(names) + 1) for c in itertools.combinations(names, r)
                if abs(sum(C[n] for n in c) - tt) <= TOL]
        print(f"{tn} {tag}: {len(hits)} hit(s) within {TOL:,}")
        if tag == "target":
            for h in hits[:5]:
                print("    ", h, f"{sum(C[n] for n in h):,}")

# ---- second pass: the 2026-vs-2025 jump (91,921,157) against the rounded 89.6M "sale of City debt" ----
# 91,921,157 - 89,600,000 = 2,321,157. Is the 2.32M leftover explained by any one or two year-over-year line deltas?
from residual_pool import approps, revenue
jump = PRINTED["ord"]["resid"] - PRINTED["25"]["resid"]
print(f"\nresidual jump 2025->2026 ord = {jump:,}; minus 89.6M = {jump - 89_600_000:,}; minus 166.0M = {jump - 166_000_000:,}")
R = revenue(); A, _ = approps()
d = [(k, v["ord"] - v["25"]) for k, v in list(R.items()) + list(A.items()) if v["ord"] != v["25"]]
left = jump - 89_600_000
n1 = [(k, x) for k, x in d if abs(x - left) <= 50_000]
n2 = [(a[0], b[0], a[1] + b[1]) for a, b in itertools.combinations(d, 2) if abs(a[1] + b[1] - left) <= 50_000]
dec = [(a[0], b[0]) for a, b in itertools.combinations(d, 2) if abs(a[1] + b[1] - (left + 777_777)) <= 50_000]
print(f"single lines within 50k of {left:,}: {len(n1)}; pairs: {len(n2)} (decoy pairs: {len(dec)}) -> from {len(d)} changed lines")
print("=> the 89.6M coincidence is NOT distinguishable from chance; not claimed as an explanation")
