"""Transfer-residual investigation, part 2: exhaustive subset-sum over interfund-like candidates.

Key observation (asserted): residual(rec) - 117,145,000 == residual(ord). So whatever composes the
unexplained part does not change between the recommendations and the ordinance, which eliminates any
revenue or appropriation line that changed (fines +92.6M, lease tax +82M, advance pension, etc.).
Targets are therefore tested as vectors over three books:
   T = (2025, rec - 117,145,000 [Library term-note double count hypothesis], ord)
and, separately, with the matching-fund piece already taken out.
Each candidate is a line (or small group) that is plausibly an interfund flow. Coefficients are 0/1.
A solution must hit all three books exactly; a single-book (ord only) pass is printed for contrast to
show how many coincidental hits one book alone produces.

Run: python3 scripts/residual_subsetsum.py
"""
import itertools
import sys
from collections import defaultdict

from residual_pool import PRINTED, approps, revenue

R = revenue()
A, rows = approps()


def rv(fund, src):
    return R[("REV", fund, src)]


def ap(pred):
    out = dict.fromkeys(("25", "rec", "ord"), 0)
    for k, v in A.items():
        if pred(k):
            for b in out:
                out[b] += v[b]
    return out


CAND = {
    "ISE Enterprise Funds (Corp)": rv("0100", "Enterprise Funds"),
    "ISE Special Revenue Funds (Corp)": rv("0100", "Special Revenue Funds"),
    "ISE Intergovernmental Funds (Corp)": rv("0100", "Intergovernmental Funds"),
    "ISE Other Reimbursements (Corp)": rv("0100", "Other Reimbursements"),
    "Reimb for City Services (Corp)": rv("0100", "Reimbursements for City Services"),
    "Proceeds and Transfers in - Other (Corp)": rv("0100", "Proceeds and Transfers in - Other"),
    "Vehicle Tax Other Reimbursements": rv("0300", "Other Reimbursements"),
    "Library Transfers In": rv("0346", "Transfers In"),
    "Bond Fund Transfers In": rv("0510", "Transfers In"),
    "Bond Fund Corp Subsidy": rv("0510", "Corporate Fund Subsidy"),
    "TIF Admin Reimbursement": rv("0B21", "Tax Increment Financing Administrative Reimbursement"),
    "Water&Sewer Utility Tax (0681)": rv("0681", "Water and Sewer Utility Tax"),
    "Library Property Tax Levy (0681)": rv("0681", "Library Property Tax Levy"),
    "Library pension residual (0681)": rv("0681", "Library Pension Residual Allocation After Property Tax Levy"),
    "Casino pension (0683+0684)": {b: rv("0683", "Casino Public Safety Pension Fund")[b]
                                    + rv("0684", "Casino Public Safety Pension Fund")[b] for b in ("25", "rec", "ord")},
    "Water Capital Funding": rv("0200", "Capital Funding"),
    "Sewer Capital Funding": rv("0314", "Capital Funding"),
    "Corp pays CTA RPT (0B09 distribution)": ap(lambda k: k[1] == "0B09" and "distribution of the net proceeds" in k[3]),
    "Indirect Costs (non-FG)": ap(lambda k: k[2] != "Finance General" and k[3] == "indirect costs"),
    "Reimbursable Overtime": ap(lambda k: k[3] == "reimbursable overtime"),
    "Midway->O'Hare salaries transfer (FG)": ap(lambda k: k[3].startswith("transfer to o'hare")),
    "Corp Transfers Out (FG, OBM excludes)": ap(lambda k: k[1] == "0100" and k[3] == "transfers out"),
    "Tuition reimbursement": ap(lambda k: k[3].startswith("tuition reimbursement")),
    "Services provided by PBC": ap(lambda k: k[3].startswith("for expenses related to services provided by pbc")),
    "Corp Fund bond subsidy approp": ap(lambda k: k[1] == "0100" and k[2] == "Finance General" and k[3] == "for payment of bonds"),
    "Matching grants, grant side": ap(lambda k: "matching and supplementary" in k[3] and k[2] != "Finance General"),
}
# Candidates are only valid if they exist and are constant between rec and ord (see module doc).
# Appropriation labels in the rec dataset are upper-case abbreviations, so rec is unreliable for
# appropriation-built candidates. Use the two books with consistent labels: 2025 and 2026 ordinance.
names = [n for n, v in CAND.items() if v["25"] or v["ord"]]
dropped = []
vec = {n: (CAND[n]["25"], CAND[n]["ord"]) for n in names}
print("candidates:", len(names))
for n in names:
    print(f"   {n:<46}{vec[n][0]:>14,}{vec[n][1]:>14,}")

TARGETS = {
    "resid": (PRINTED["25"]["resid"], PRINTED["ord"]["resid"]),
    "resid minus matching funds": (PRINTED["25"]["resid_after_match"], PRINTED["ord"]["resid_after_match"]),
}
assert PRINTED["rec"]["resid"] - 117_145_000 == PRINTED["ord"]["resid"]


def solve(target, use_year):
    """All subsets with 0/1 coefficients matching target on the chosen coordinates (meet in the middle)."""
    idx = (0, 1) if use_year == "both" else (1,)
    n = len(names)
    half = n // 2
    L, Rr = names[:half], names[half:]

    def enum(items):
        out = defaultdict(list)
        for mask in range(1 << len(items)):
            s = tuple(sum(vec[items[i]][j] for i in range(len(items)) if mask >> i & 1) for j in idx)
            out[s].append(mask)
        return out

    left, right = enum(L), enum(Rr)
    tgt = tuple(target[j] for j in idx)
    hits = []
    for s, ms in left.items():
        need = tuple(t - x for t, x in zip(tgt, s))
        if need in right:
            for ml in ms:
                for mr in right[need]:
                    hits.append([L[i] for i in range(len(L)) if ml >> i & 1] + [Rr[i] for i in range(len(Rr)) if mr >> i & 1])
    return hits


for label, tgt in TARGETS.items():
    for use in ("ord only", "both"):
        h = solve(tgt, "both" if use == "both" else "ord")
        print(f"\ntarget {label!r} using {use}: {len(h)} exact subset(s)")
        for s in h[:8]:
            print("   ", s)

# ---- second pass: allow the rule to change between years (delta search, any subset size) ----------
# If OBM's composition changed, only the year-over-year DELTA of the residual constrains it.
# Coefficient is 0/1 per line applied to the 2026-minus-2025 delta of that line.
dvec = {n: (CAND[n]["ord"] - CAND[n]["25"],) for n in names}
dnames = [n for n in names if dvec[n][0]]
DT = {
    "delta of residual (2026 ord - 2025 ord)": PRINTED["ord"]["resid"] - PRINTED["25"]["resid"],
    "delta of residual after matching": PRINTED["ord"]["resid_after_match"] - PRINTED["25"]["resid_after_match"],
}
half = len(dnames) // 2


def enum_d(items):
    out = defaultdict(list)
    for mask in range(1 << len(items)):
        out[sum(dvec[items[i]][0] for i in range(len(items)) if mask >> i & 1)].append(mask)
    return out


Ld, Rd = enum_d(dnames[:half]), enum_d(dnames[half:])
print(f"\n--- delta search over {len(dnames)} lines, all subset sizes ---")
for label, t in DT.items():
    for tt, tag in ((t, "target"), (t + 1_000_003, "decoy")):
        cnt = sum(len(ms) * len(Rd.get(tt - s, ())) for s, ms in Ld.items())
        print(f"{label} {tag} {tt:,}: {cnt} subset(s)")
        if tag == "target" and cnt:
            shown = 0
            for s, ms in Ld.items():
                for mr in Rd.get(tt - s, ()):
                    for ml in ms:
                        sel = [dnames[:half][i] for i in range(half) if ml >> i & 1] + [dnames[half:][i] for i in range(len(dnames) - half) if mr >> i & 1]
                        if shown < 6:
                            print("    ", sel)
                        shown += 1
