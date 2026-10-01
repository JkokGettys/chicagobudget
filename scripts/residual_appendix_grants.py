"""Transfer-residual investigation, part 11: Appendix A/B external lines, grant-side interfund candidates,
and the Corporate Fund Internal Service Earnings tie-out.

Prints facts (all asserted) and a small exhaustive subset search over these named candidates:
  * Appendix A/B "External Reimbursements" (printed): 2026 ord 14,422,855 + 40,221,874; 2025 ord 17,156,418 + 42,601,874
  * Fund 0075 Indirect Cost Recovery grant appropriations (ordinance p. 545: 21,519,000 / 7,651,000)
  * Grant-side matching funds ('To Provide for Matching ...' in 925x funds)
  * Corp Fund ISE Intergovernmental Funds and Other Reimbursements
  * Vehicle Tax Fund Other Reimbursements, TIF admin reimbursement, Library Transfers In, Bond Fund Transfers In
Targets (2025, 2026): residual, residual - matching funds.

Run: python3 scripts/residual_appendix_grants.py
"""
import itertools
import json
import os

from residual_pool import PRINTED, approps, revenue

RAW = os.path.join(os.path.dirname(__file__), "..", "raw")
R = revenue()
A, _ = approps()

# --- tie-out: Corp Fund Internal Service Earnings (Enterprise + Special Revenue) vs FG 'To Reimburse' lines
o = json.load(open(os.path.join(RAW, "city_appropriations_2026.json")))
ent = {"0200", "0314", "0610", "0740"}
fg = [x for x in o if x["department_description"] == "Finance General" and x["appropriation_account_description"].startswith("To Reimburse")]
fg_ent = sum(int(x["_ordinance_amount_"]) for x in fg if x["fund_code"] in ent)
fg_oth = sum(int(x["_ordinance_amount_"]) for x in fg if x["fund_code"] not in ent)
ise_ent = R[("REV", "0100", "Enterprise Funds")]["ord"]
ise_spec = R[("REV", "0100", "Special Revenue Funds")]["ord"]
assert fg_ent == ise_ent == 202_689_118
print(f"Corp ISE 'Enterprise Funds' revenue {ise_ent:,} == FG 'To Reimburse' lines in enterprise funds {fg_ent:,} (exact)")
print(f"Corp ISE 'Special Revenue Funds' revenue {ise_spec:,} vs FG 'To Reimburse' in all non-enterprise funds {fg_oth:,}: "
      f"diff {ise_spec - fg_oth:,}  (FG lines include 4,427,507 Corp->Midway fire reimbursements)")
print("=> the reimbursement revenue lines are the mirror of lines already inside the FG interfund total; they add nothing new.")

cand = {
    "Appendix External A+B": (17_156_418 + 42_601_874, 14_422_855 + 40_221_874),
    "Fund 0075 indirect cost recovery (grants)": (7_651_000, 21_519_000),
    "Grant-side matching funds": tuple(sum(v[b] for k, v in A.items() if "matching and supplementary" in k[3] and k[2] != "Finance General") for b in ("25", "ord")),
    "ISE Intergovernmental Funds": (R[("REV", "0100", "Intergovernmental Funds")]["25"], R[("REV", "0100", "Intergovernmental Funds")]["ord"]),
    "ISE Other Reimbursements": (R[("REV", "0100", "Other Reimbursements")]["25"], R[("REV", "0100", "Other Reimbursements")]["ord"]),
    "Vehicle Tax Other Reimbursements": (R[("REV", "0300", "Other Reimbursements")]["25"], R[("REV", "0300", "Other Reimbursements")]["ord"]),
    "TIF admin reimbursement": (R[("REV", "0B21", "Tax Increment Financing Administrative Reimbursement")]["25"], R[("REV", "0B21", "Tax Increment Financing Administrative Reimbursement")]["ord"]),
    "Library Transfers In": (R[("REV", "0346", "Transfers In")]["25"], R[("REV", "0346", "Transfers In")]["ord"]),
    "Bond Fund Transfers In": (R[("REV", "0510", "Transfers In")]["25"], R[("REV", "0510", "Transfers In")]["ord"]),
    "Corp subsidy to bond fund": (R[("REV", "0510", "Corporate Fund Subsidy")]["25"], R[("REV", "0510", "Corporate Fund Subsidy")]["ord"]),
    "Casino pension revenue": (16_490_772, 44_610_000),
    "Water&Sewer utility tax to MEABF": (R[("REV", "0681", "Water and Sewer Utility Tax")]["25"], R[("REV", "0681", "Water and Sewer Utility Tax")]["ord"]),
}
names = list(cand)
targets = {"residual": (PRINTED["25"]["resid"], PRINTED["ord"]["resid"]),
           "residual - matching": (PRINTED["25"]["resid_after_match"], PRINTED["ord"]["resid_after_match"])}
for label, t in targets.items():
    hits = [c for r in range(1, len(names) + 1) for c in itertools.combinations(names, r)
            if (sum(cand[n][0] for n in c), sum(cand[n][1] for n in c)) == t]
    print(f"\n{label} {t}: {len(hits)} exact subset(s) of {len(names)} named candidates; 2026-only hits:",
          sum(1 for r in range(1, len(names) + 1) for c in itertools.combinations(names, r) if sum(cand[n][1] for n in c) == t[1]))
