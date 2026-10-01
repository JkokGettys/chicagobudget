"""Transfer-residual investigation, part 3: broad pair/triple search over ALL lines, two books at once.

Finding that motivates this (see research/transfer_residual.md): the residual is ~60M in 2024 and 2025
(both the recommendations and the ordinance) and only jumps in 2026. So a true composition rule must
hit BOTH 2025 and 2026 ordinance residuals. Candidates are every revenue line (fund, source) and every
appropriation (fund, account text) outside the already-explained sets, as a 2-vector (2025 ord, 2026 ord).
We look for subsets of size 1..3 with sum == (target25, target26) exactly, for three target definitions.

Run: python3 scripts/residual_broad.py
"""
import itertools
import re
from collections import defaultdict

from residual_pool import PRINTED, approps, revenue

R = revenue()
A, _ = approps()

cands = {}
for k, v in R.items():
    if v["25"] or v["ord"]:
        cands[("REV",) + k[1:]] = (v["25"], v["ord"])
# appropriations grouped by (fund, account text), summed over departments
grp = defaultdict(lambda: [0, 0])
explained = re.compile(r"pension allocation|advance pension|^to reimburse|^transfer|matching and supplementary|"
                       r"^for services provided by|^american rescue plan revenue|^for the city's (advance )?contribution", re.I)
for k, v in A.items():
    _, fund, dept, acct = k
    if explained.search(acct):
        continue
    if v["25"] or v["ord"]:
        g = grp[("APP", fund, acct)]
        g[0] += v["25"]
        g[1] += v["ord"]
for k, v in grp.items():
    cands[k] = tuple(v)
# drop ones that are zero in both and obvious non-flows is NOT done: keep everything
items = [(k, v) for k, v in cands.items() if v != (0, 0)]
print("candidate lines:", len(items))

TARGETS = {
    "full residual": (PRINTED["25"]["resid"], PRINTED["ord"]["resid"]),
    "residual - matching funds": (PRINTED["25"]["resid_after_match"], PRINTED["ord"]["resid_after_match"]),
    "residual - matching - Corp Transfers Out(350k both)": (PRINTED["25"]["resid_after_match"] - 350_000,
                                                            PRINTED["ord"]["resid_after_match"] - 350_000),
}

# index singles by vector; pairs by vector; then triples = pair + single lookup
by_vec = defaultdict(list)
for i, (k, v) in enumerate(items):
    by_vec[v].append(i)

n = len(items)
for label, tgt in TARGETS.items():
    hits = []
    for i in range(n):
        if items[i][1] == tgt:
            hits.append((i,))
    pair_index = {}
    for i in range(n):
        vi = items[i][1]
        for j in range(i + 1, n):
            vj = items[j][1]
            s = (vi[0] + vj[0], vi[1] + vj[1])
            if s == tgt:
                hits.append((i, j))
            need = (tgt[0] - s[0], tgt[1] - s[1])
            for m in by_vec.get(need, ()):
                if m > j:
                    hits.append((i, j, m))
    print(f"\n{label}: target {tgt}: {len(hits)} subset(s) of size<=3")
    for h in hits[:10]:
        print("   ", [items[x][0] for x in h])
