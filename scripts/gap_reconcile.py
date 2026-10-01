"""Reconcile the 2026 City ordinance total ($18.67B gross) to the official net figure.

Inputs (all in raw/, gitignored; run scripts/gap_fetch.py first for raw/gap/*):
  raw/city_appropriations_2026.json   adopted ordinance appropriations (dataset 6694-f78c)
  raw/gap/recs_approp_2026.json       Mayor's Budget Recommendations appropriations (axxr-vais)
  raw/gap/approp_2025.json            2025 ordinance appropriations (t59y-fr3k)
  raw/context/revenue_2026.json       2026 ordinance revenue (nydj-5nax)
  raw/context/revenue_rec_2026.json   2026 recommendation revenue (iiqa-6c55)

Official figures are hard-coded from the PRINTED books (page refs in research/reconciliation.md)
and every one is asserted against the data where the data can reproduce it.

Usage: python3 scripts/gap_reconcile.py   -> prints the table, writes data/gap_reconciliation.json
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "..", "raw")
OUT = os.path.join(HERE, "..", "data", "gap_reconciliation.json")


def load(*p):
    return json.load(open(os.path.join(RAW, *p)))


ORD = load("city_appropriations_2026.json")
REC = load("gap", "recs_approp_2026.json")
A25 = load("gap", "approp_2025.json")
REV_ORD = load("context", "revenue_2026.json")
REV_REC = load("context", "revenue_rec_2026.json")

# ---- printed figures -------------------------------------------------------------------
PRINTED = {
    # Annual Appropriation Ordinance 2026 (as passed 2025-12-20), Summary G, ordinance p. 544; Summary B p. 543
    "ord_gross": 18_668_568_460,
    "ord_deduct_transfers": 1_700_089_446,
    "ord_deduct_debt": 125_926_011,
    "ord_net": 16_842_553_003,
    # Budget Recommendations (Oct 2025) Summary G, rec book p. 603
    "rec_gross": 18_350_767_715,
    "rec_deduct_transfers": 1_679_051_626,
    "rec_deduct_debt": 117_145_000,
    "rec_net": 16_554_571_089,
    # 2026 Budget Overview pp. 32/34 (= Recs): 16,554.6M ; p. 182 "Interfund Transfers and Reimbursements"
    "rec_fg_interfund_line": 1_389_476_663,
    "ord2025_fg_interfund_line": 1_543_512_195,   # 2026 Overview p. 182, 2025 column
    "ord2025_deduct_transfers": 1_622_468_611,    # 2025 ordinance Summary B
    # Recs book Appendix A and B (internal transfers only)
    "rec_appA_internal": 9_015_367, "rec_appB_internal": 10_911_809,
    # Ordinance Appendix A/B (A changed in the adopted version)
    "ord_appA_internal": 7_766_967, "ord_appB_internal": 10_911_809,
}


def amt_ord(x):
    return int(x["_ordinance_amount_"])


def amt_rec(x):
    return round(float(x["recommendation"] or 0))


def amt_25(x):
    return int(float(x["_ordinance_amount_"]))


def is_fg(x):
    return x["department_description"] == "Finance General"


def nm(x):
    return x["appropriation_account_description"]


# ---- 1. totals tie ---------------------------------------------------------------------
gross_ord = sum(amt_ord(x) for x in ORD)
gross_rec = sum(amt_rec(x) for x in REC)
assert gross_ord == PRINTED["ord_gross"], gross_ord
assert gross_rec == PRINTED["rec_gross"], gross_rec
assert PRINTED["ord_gross"] - PRINTED["ord_deduct_transfers"] - PRINTED["ord_deduct_debt"] == PRINTED["ord_net"]
assert PRINTED["rec_gross"] - PRINTED["rec_deduct_transfers"] - PRINTED["rec_deduct_debt"] == PRINTED["rec_net"]


# ---- 2. the Finance General "Interfund Transfers and Reimbursements" line -----------------
def fg_interfund(rows, amt, pension_re, reimb_re, transfer_re, exclude_transfer_out=True):
    pen = sum(amt(x) for x in rows if is_fg(x) and re.search(pension_re, nm(x)))
    rei = sum(amt(x) for x in rows if is_fg(x) and re.search(reimb_re, nm(x)))
    trn = sum(amt(x) for x in rows if is_fg(x) and re.search(transfer_re, nm(x))
              and not (exclude_transfer_out and nm(x).lower() == "transfers out" and x["fund_code"] == "0100"))
    return pen, rei, trn


# Recommendation book labels are upper-case abbreviations ("REIMB - ...", "TRANSFER FOR ...").
pen_r, rei_r, trn_r = fg_interfund(REC, amt_rec, r"PENSION ALLOCATION|ADVANCE PENSION PAYMT",
                                   r"^REIMB( -|\s+MIDWAY)", r"^TRANSFER")
assert pen_r + rei_r + trn_r == PRINTED["rec_fg_interfund_line"], (pen_r, rei_r, trn_r)
# 2025 ordinance, same rule, ties to the 2025 Overview line to the dollar
pen_25, rei_25, trn_25 = fg_interfund(A25, amt_25, r"Pension Allocation|Advance Pension Payment",
                                      r"^To Reimburse", r"^Transfer")
assert pen_25 + rei_25 + trn_25 == PRINTED["ord2025_fg_interfund_line"], (pen_25, rei_25, trn_25)
# Adopted 2026, same rule
pen_o, rei_o, trn_o = fg_interfund(ORD, amt_ord, r"Pension Allocation|Advance Pension Payment",
                                   r"^To Reimburse", r"^Transfer")
fg_interfund_ord = pen_o + rei_o + trn_o

# ---- 3. what scripts/finance_general.py removes today ----------------------------------
# Same three tests as RULES[0:2] in scripts/finance_general.py.
current_rule = sum(
    amt_ord(x) for x in ORD if is_fg(x) and (
        "Pension Allocation" in nm(x) or "Advance Pension Payment" in nm(x)
        or nm(x).startswith("To Reimburse")))
assert current_rule == 1_521_146_451, current_rule

# What the rule misses, line by line (all inside Finance General):
transfer_lines = defaultdict(int)
for x in ORD:
    if is_fg(x) and nm(x).startswith("Transfer"):
        transfer_lines[(x["fund_description"], nm(x))] += amt_ord(x)
missed_transfers = sum(transfer_lines.values())
assert current_rule + missed_transfers == fg_interfund_ord + (
    # "Transfers Out" of the Corporate Fund ($350,000) is in transfer_lines but excluded by OBM
    350_000)

# ---- 4. appendices (reimbursements made to non-Finance-General departments) -------------
app_ab_ord = PRINTED["ord_appA_internal"] + PRINTED["ord_appB_internal"]
app_ab_rec = PRINTED["rec_appA_internal"] + PRINTED["rec_appB_internal"]

# The "For Services Provided by ..." lines in the ordinance are the department-side appropriations
# that Appendix A/B describe. They are NOT additive to the appendix totals.
svc_lines = sum(amt_ord(x) for x in ORD if not is_fg(x) and nm(x).startswith("For Services Provided by"))

# ---- 5. residual -----------------------------------------------------------------------
residual_ord = PRINTED["ord_deduct_transfers"] - fg_interfund_ord - app_ab_ord
residual_rec = PRINTED["rec_deduct_transfers"] - PRINTED["rec_fg_interfund_line"] - app_ab_rec

# ---- 6. exact identity: deduction (recs) -> deduction (adopted) -------------------------
adv_rec = sum(amt_rec(x) for x in REC if is_fg(x) and "ADVANCE PENSION PAYMT" in nm(x).upper())
adv_ord = sum(amt_ord(x) for x in ORD if is_fg(x) and "Advance Pension Payment" in nm(x))
delta_deduct = PRINTED["ord_deduct_transfers"] - PRINTED["rec_deduct_transfers"]
assert delta_deduct == 21_037_820
# Exact identity, to the dollar:
#   deduction(adopted) - deduction(recs) = [FG advance pension, adopted - recs]
#                                        + [Appendix A internal, adopted - recs] - 117,145,000
# Equivalently the unexplained residual FALLS by exactly 117,145,000 between the two books
# (269,647,787 -> 152,502,787). 117,145,000 is also the recs-book Library term-note amount, which both
# books already deduct separately as "Proceeds of Debt". Whether the recs deducted it twice is a guess
# from an exact numeric match; the books do not say. The remaining 152,502,787 is unexplained either way.
assert (adv_ord - adv_rec) + (PRINTED["ord_appA_internal"] - PRINTED["rec_appA_internal"]) - 117_145_000 \
    == delta_deduct

# ---- 7. Corporate Fund advance payments: the OBM "advance" flows -----------------------
# Appropriation side vs revenue side of the pension funds: both carry the same advance dollars.
rev_adv = sum(round(float(x["estimated_revenue"])) for x in REV_ORD
              if x["fund_code"] in ("0681", "0682", "0683", "0684") and "Advance Pension Payment" in x["revenue_source"])
exp_adv = sum(amt_ord(x) for x in ORD if is_fg(x) and "Advance Pension Payment" in nm(x))
assert rev_adv == exp_adv, (rev_adv, exp_adv)

# ---- 8. Appendix A/B tie to the department-side lines, exactly --------------------------
# Rule: LOCAL-fund appropriations named "For Services Provided by <City department>" outside Finance
# General, excluding "Performers and Exhibitors" (a vendor class at the Library, not a City department).
# This reproduces Appendix A + B "Internal Transfers" to the dollar once the Entitlement Fund line
# (13,148, listed by OBM as an EXTERNAL reimbursement from a federal grant) is left out.
svc_rule = sum(amt_ord(x) for x in ORD if not is_fg(x) and nm(x).startswith("For Services Provided by")
               and "Performers and Exhibitors" not in nm(x) and x["fund_type"] == "LOCAL")
assert svc_rule == app_ab_ord, (svc_rule, app_ab_ord)

# ---- 9. what is in the remaining residual? ----------------------------------------------
# Documented: the ordinance (Grant Detail text, p. 557) says "Required City matching funds for grant
# awards are reflected under both 925-Grant Funds and Finance General. The total required City match
# amounts are included in the Deduct Transfer between Funds line in Summary B."
match_fg = sum(amt_ord(x) for x in ORD if is_fg(x) and "Matching and Supplementary" in nm(x))
match_all = sum(amt_ord(x) for x in ORD if "Matching and Supplementary" in nm(x))
match_all_25 = sum(amt_25(x) for x in A25 if "Matching and Supplementary" in nm(x))
app_ab_25 = 8_955_367 + 9_419_419                                  # 2025 ordinance Appendix A + B internal
residual_25 = PRINTED["ord2025_deduct_transfers"] - PRINTED["ord2025_fg_interfund_line"] - app_ab_25
after_match_26 = residual_ord - match_all
after_match_25 = residual_25 - match_all_25

# Tested and REJECTED: Corporate Fund subsidy to the debt-service fund (Corp "For Payment of Bonds" =
# fund 0510 "Corporate Fund Subsidy"). It is a real interfund transfer (same dollars on both sides) but
# it cannot be in the deduction under one consistent rule: 2025's whole residual is smaller than it.
corp_bond_subsidy = sum(amt_ord(x) for x in ORD if x["fund_code"] == "0100" and is_fg(x)
                        and nm(x) == "For Payment of Bonds")
corp_bond_subsidy_25 = sum(amt_25(x) for x in A25 if x["fund_code"] == "0100" and is_fg(x)
                           and nm(x) == "For Payment of Bonds")
rev510 = {x["revenue_source"]: round(float(x["estimated_revenue"])) for x in REV_ORD if x["fund_code"] == "0510"}
assert corp_bond_subsidy == rev510["Corporate Fund Subsidy"]
assert sum(rev510.values()) == sum(amt_ord(x) for x in ORD if x["fund_code"] == "0510")
assert corp_bond_subsidy_25 > residual_25            # => the subsidy cannot be a component in 2025

# ---- 10. decomposition of the gap between the SITE and the printed net (adopted) -----------
site_removes = current_rule
printed_removes = PRINTED["ord_deduct_transfers"] + PRINTED["ord_deduct_debt"]
gap = printed_removes - site_removes
parts = {
    "FG transfer lines the site rule misses (OBM definition)": fg_interfund_ord - current_rule,
    "Appendix A+B department-side reimbursements (non-FG)": app_ab_ord,
    "Proceeds of Debt (Library term notes, printed separately)": PRINTED["ord_deduct_debt"],
    "Unexplained remainder inside Deduct Transfers": residual_ord,
}
assert sum(parts.values()) == gap, (sum(parts.values()), gap)

# ---- report ----------------------------------------------------------------------------
fmt = lambda n: f"{n:>16,}"
rows = [
    ("Ordinance gross (data = printed)", gross_ord),
    ("  printed Deduct Transfers between Funds", -PRINTED["ord_deduct_transfers"]),
    ("  printed Deduct Proceeds of Debt", -PRINTED["ord_deduct_debt"]),
    ("Ordinance printed Net Total", PRINTED["ord_net"]),
    ("", None),
    ("Recommendations gross (data = printed)", gross_rec),
    ("  printed Deduct Transfers between Funds", -PRINTED["rec_deduct_transfers"]),
    ("  printed Deduct Proceeds of Debt", -PRINTED["rec_deduct_debt"]),
    ("Recommendations printed Net Total (the $16.6B everyone quotes)", PRINTED["rec_net"]),
    ("", None),
    ("Deduction components, ADOPTED ordinance", None),
    ("  FG pension allocations + advance payments", pen_o),
    ("  FG 'To Reimburse ...' (indirect cost, pension)", rei_o),
    ("  FG 'Transfer ...' lines (excl. Corp Fund 'Transfers Out' $350,000)", trn_o),
    ("  = FG Interfund Transfers and Reimbursements (OBM def.)", fg_interfund_ord),
    ("  Appendix A + B internal transfers (printed)", app_ab_ord),
    ("  = explained", fg_interfund_ord + app_ab_ord),
    ("  printed Deduct Transfers between Funds", PRINTED["ord_deduct_transfers"]),
    ("  UNEXPLAINED RESIDUAL (not in any line the books label as transfer)", residual_ord),
    ("", None),
    ("Deduction components, RECOMMENDATIONS (the book behind $16.6B)", None),
    ("  FG Interfund Transfers and Reimbursements (printed = data)", PRINTED["rec_fg_interfund_line"]),
    ("  Appendix A + B internal transfers (printed)", app_ab_rec),
    ("  printed Deduct Transfers between Funds", PRINTED["rec_deduct_transfers"]),
    ("  UNEXPLAINED RESIDUAL", residual_rec),
]
print("\n".join(f"{a:<78}{fmt(b) if b is not None else ''}" for a, b in rows))
print(f"\ncurrent site rule removes {current_rule:,}; OBM FG line is {fg_interfund_ord:,}; "
      f"site rule misses {fg_interfund_ord - current_rule:,} inside FG")
print(f"missed 'Transfer ...' lines: {missed_transfers:,} (of which $350,000 Corp 'Transfers Out' OBM excludes)")
print(f"non-FG 'For Services Provided by' appropriations: {svc_lines:,} (= the department side of Appendix A/B)")
print(f"deduction change recs -> adopted: {delta_deduct:,} = advance pension +{adv_ord - adv_rec:,} "
      f"+ AppA {PRINTED['ord_appA_internal'] - PRINTED['rec_appA_internal']:,} - Library term-note 117,145,000")

print("\nSITE vs PRINTED NET (adopted ordinance): site removes", f"{site_removes:,}", "printed removes", f"{printed_removes:,}", "gap", f"{gap:,}")
for k, v in parts.items():
    print(f"  {v:>14,}  {k}")
print(f"\nRESIDUAL {residual_ord:,} (2026 adopted) vs {residual_25:,} (2025 adopted)")
print(f"  documented: matching grant funds {match_all:,} (2026; FG {match_fg:,} + grant side {match_all - match_fg:,})"
      f" and {match_all_25:,} (2025)")
print(f"  still unexplained after matching funds: {after_match_26:,} (2026), {after_match_25:,} (2025)")
print(f"  rejected: Corp Fund subsidy to debt fund {corp_bond_subsidy:,} (2025: {corp_bond_subsidy_25:,} > whole 2025 residual)")
print(f"Appendix A+B rule check: department-side 'For Services Provided by' lines = {svc_rule:,} = Appendix A+B {app_ab_ord:,}")

out = {
    "printed": PRINTED,
    "site_gap_parts": parts, "site_gap_total": gap,
    "residual_detail": {"residual_2026_adopted": residual_ord, "residual_2025": residual_25,
                        "matching_funds_2026": match_all, "matching_funds_2025": match_all_25,
                        "unexplained_after_matching_2026": after_match_26,
                        "unexplained_after_matching_2025": after_match_25,
                        "rejected_corp_fund_subsidy_2026": corp_bond_subsidy,
                        "rejected_corp_fund_subsidy_2025": corp_bond_subsidy_25},
    "gross_ord": gross_ord, "gross_rec": gross_rec,
    "fg_interfund_adopted": {"pension": pen_o, "reimburse": rei_o, "transfer": trn_o, "total": fg_interfund_ord},
    "fg_interfund_recs": {"pension": pen_r, "reimburse": rei_r, "transfer": trn_r, "total": pen_r + rei_r + trn_r},
    "fg_interfund_2025": {"pension": pen_25, "reimburse": rei_25, "transfer": trn_25, "total": pen_25 + rei_25 + trn_25},
    "current_site_rule_removes": current_rule,
    "site_rule_misses_in_fg": fg_interfund_ord - current_rule,
    "missed_transfer_lines": [{"fund": k[0], "account": k[1], "amount": v}
                              for k, v in sorted(transfer_lines.items(), key=lambda kv: -kv[1])],
    "appendix_ab_adopted": app_ab_ord, "appendix_ab_recs": app_ab_rec,
    "residual_adopted": residual_ord, "residual_recs": residual_rec,
    "delta_deduction_recs_to_adopted": delta_deduct,
    "advance_pension_delta": adv_ord - adv_rec,
    "net_if_site_removes_obm_fg_line_only": PRINTED["ord_gross"] - fg_interfund_ord - PRINTED["ord_deduct_debt"],
}
os.makedirs(os.path.dirname(OUT), exist_ok=True)
json.dump(out, open(OUT, "w"), indent=1)
print("wrote", os.path.relpath(OUT))
