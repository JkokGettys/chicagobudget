"""Transfer-residual investigation, part 5: define the deduction from the REVENUE side.

Three books have consistent revenue data (2025 ord, 2026 rec, 2026 ord), so a revenue-side definition
must hit all three printed deductions at once (3 equations). For each base set B (a revenue-side
definition of the part we already understand), search every subset of up to 4 other revenue lines
(meet in the middle over pairs) such that  base + subset == printed deduction in all three books.

Bases tried:
  B0  nothing
  B1  pension allocation + advance revenue lines in funds 0681-0684   (the pension double count)
  B2  B1 + Corp Fund Internal Service Earnings: Enterprise + Special Revenue Funds
  B3  B1 + all four Corp Fund Internal Service Earnings lines
Chance calibration: the same search is repeated against a decoy target (printed deduction + 1,000,003)
to show how many coincidental hits that search space produces.

Run: python3 scripts/residual_revside.py
"""
import re
from collections import defaultdict

from residual_pool import BOOKS, PRINTED, revenue

R = revenue()
pf = ("0681", "0682", "0683", "0684")
pen = {b: sum(v[b] for k, v in R.items() if k[1] in pf and re.search("Pension Allocation|Advance Pension", k[2])) for b in BOOKS}


def line(fund, src):
    return R[("REV", fund, src)]


ise = {n: line("0100", n) for n in ("Enterprise Funds", "Special Revenue Funds", "Intergovernmental Funds", "Other Reimbursements")}
BASES = {
    "B0 nothing": dict.fromkeys(BOOKS, 0),
    "B1 pension alloc+advance revenue": pen,
    "B2 B1 + ISE enterprise + special revenue": {b: pen[b] + ise["Enterprise Funds"][b] + ise["Special Revenue Funds"][b] for b in BOOKS},
    "B3 B1 + all four ISE lines": {b: pen[b] + sum(v[b] for v in ise.values()) for b in BOOKS},
}
for b in BOOKS:
    print(b, "pension revenue lines", f"{pen[b]:,}")

excluded = re.compile(r"Pension Allocation|Advance Pension")
items = [(k, tuple(v[b] for b in BOOKS)) for k, v in R.items() if not excluded.search(k[2]) and any(v.values())]
print("revenue lines available:", len(items))


def search(target, maxk=4):
    pairs = defaultdict(list)
    n = len(items)
    for i in range(n):
        for j in range(i + 1, n):
            s = tuple(x + y for x, y in zip(items[i][1], items[j][1]))
            pairs[s].append((i, j))
    singles = defaultdict(list)
    for i in range(n):
        singles[items[i][1]].append((i,))
    hits = set()
    zero = (0, 0, 0)
    pools = [singles, pairs]
    for pa in (singles, pairs):
        for sa, la in pa.items():
            need = tuple(t - x for t, x in zip(target, sa))
            for pb in (singles, pairs, {zero: [()]}):
                for lb in pb.get(need, ()):
                    for ta in la:
                        s = tuple(sorted(set(ta) | set(lb)))
                        if len(s) == len(ta) + len(lb) and 1 <= len(s) <= maxk:
                            hits.add(s)
    return hits


ded = tuple(PRINTED[b]["deduct"] for b in BOOKS)
print("order of books:", BOOKS, "printed deductions:", ded)
for name, base in BASES.items():
    tgt = tuple(d - base[b] for d, b in zip(ded, BOOKS))
    hits = search(tgt)
    decoy = search(tuple(t + 1_000_003 for t in tgt))
    print(f"\n{name}: remaining target {tgt}")
    print(f"   exact hits (<=4 lines): {len(hits)}   decoy hits: {len(decoy)}")
    for h in sorted(hits, key=len)[:6]:
        print("     ", [(items[i][0][1], items[i][0][2]) for i in h])

# ---- second pass: the RESIDUAL (not the whole deduction) as target, revenue lines only, <=4 lines ----
print("\n--- residual targets, revenue lines only (pension revenue lines excluded), <=4 lines ---")
for label, key in (("residual", "resid"), ("residual - matching funds", "resid_after_match")):
    tgt = tuple(PRINTED[b][key] for b in BOOKS)
    h = search(tgt)
    d = search(tuple(t + 1_000_003 for t in tgt))
    print(f"{label}: target {tgt}: exact hits {len(h)}, decoy hits {len(d)}")
    for s in sorted(h, key=len)[:5]:
        print("     ", [(items[i][0][1], items[i][0][2]) for i in s])
