"""Transfer-residual investigation, part 1: what the books pin down about the residual.

Run: python3 scripts/residual_checks.py   (needs raw/ from scripts/gap_fetch.py)
Prints the residual in three books and the invariants. Asserts every printed number it uses.
"""
from residual_pool import BOOKS, PRINTED, approps, revenue

for b in BOOKS:
    p = PRINTED[b]
    print(f"{b:>4}: deduct {p['deduct']:>14,}  FG line {p['fg_line']:>14,}  App A+B {p['appAB']:>11,}"
          f"  resid {p['resid']:>12,}  match {p['match']:>11,}  resid-match {p['resid_after_match']:>12,}")

# Invariant 1 (documented in reconciliation.md): resid(rec) - resid(ord) = 117,145,000 exactly
assert PRINTED["rec"]["resid"] - PRINTED["ord"]["resid"] == 117_145_000
# Invariant 2: matching funds are identical in rec and ord, so resid-after-match also differs by 117,145,000
assert PRINTED["rec"]["match"] == PRINTED["ord"]["match"]
assert PRINTED["rec"]["resid_after_match"] - PRINTED["ord"]["resid_after_match"] == 117_145_000
assert PRINTED["ord"]["resid"] == 152_502_787 and PRINTED["ord"]["resid_after_match"] == 116_988_502

# Invariant 3: gross appropriation in the data == printed gross (all three books)
A, rows = approps()
for b in BOOKS:
    assert sum(v[b] for v in A.values()) == PRINTED[b]["gross"], b

# Which stable-between-books items exist? Sum of all lines identical in rec and ord, by kind
R = revenue()
stable_rev = {k: v for k, v in R.items() if v["rec"] == v["ord"] and v["rec"]}
print(f"\nrevenue lines identical in rec and ord: {len(stable_rev)} of {len(R)}")
