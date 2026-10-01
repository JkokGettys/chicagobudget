#!/usr/bin/env python3
"""Round 3, item 2a: City pension contributions split by statutory component and by benefit type, per fund.
Reads data/pensions_2026.json (already cited) plus the valuation texts in raw/pensions_debt/funds/ for the normal cost / ADC tables.
All numbers below were read from those texts (source lines named in each piece). Writes data/leaves_pensions.json.
Status stays split_proxy: the City contribution is not the benefit payment, so the benefit-type split is a PROXY allocation
(contribution x share of annual benefit dollars). The component split (normal cost vs unfunded liability) is derived arithmetic."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pens = json.load(open(f"{ROOT}/data/pensions_2026.json"))
T = 10_000_000
F = "raw/pensions_debt/funds/"

# (fund key, ordinance fund text in the leaf path, net employer normal cost, total normal cost, member contrib, ADC, source for components)
COMP = {
 "PABF": dict(path="Policemen's Annuity", nnc=222_445_185, tnc=348_426_849, mem=125_981_664, adc=1_416_650_276, amort=1_142_871_201,
              src=F + "PABF_20251231_Final.txt (Table 1C 'Net Normal Cost' line (8); Table 4 lines (1) to (6))"),
 "MEABF": dict(path="Municipal Employees' Annuity", nnc=146_922_858, tnc=409_399_589, mem=269_321_729, adc=1_350_383_529, amort=1_198_582_991,
              src=F + "MEABF_val_2025.txt (ADC table lines 1 to 10, p.27; includes $6.84M administrative expenses in employer normal cost)"),
 "FABF": dict(path="Firemen's Annuity", nnc=93_011_790, tnc=147_242_696, mem=58_147_816, adc=588_720_377, amort=554_483_168,
              src=F + "FABF_val_2025.txt (ADC table lines 1 to 10, p.24; includes $3.92M administrative expenses)"),
 "LABF": dict(path="Laborers' and Retirement", nnc=26_624_056, tnc=50_190_191, mem=23_566_135, adc=170_342_684, amort=134_694_224,
              src=F + "LABF_GRS_2025_Val.txt (Table 3 ADC lines (1) to (9), Table 1B net employer normal cost line (11))"),
}
# benefit types: (label, count, average annual, source) ; remainder pieces are DERIVED from the printed annual total
BEN = {
 "PABF": dict(total=1_032_071_723, rows=[("Service retirement annuities", 11271, 81154), ("Widow annuities (derived: total minus others)", 3068, None),
              ("Children's annuities", 166, 1_441_283 / 166), ("Widows' compensation annuities", 65, 4_836_294 / 65),
              ("Ordinary disability", 29, 1_647_209 / 29), ("Occupational disease disability", 18, 1_267_015 / 18),
              ("Duty disability", 177, 14_015_808 / 177), ("Children's disability", 101, 121_200 / 101)],
              src="PABF valuation Exhibit B (counts, p.44), Exhibit E (service retirees $914,683,048), Exhibit G (misc annuities $23,328,809)",
              acfr=dict(pension_and_disability=1_035_953_513, death=1_991_600, refunds=11_718_221), acfr_src=F + "PABF_FS_2025.txt lines 730 to 732 (2025 statement of changes)"),
 "MEABF": dict(total=1_147_424_016, rows=[("Retired members", 21874, 4092 * 12), ("Surviving spouses", 3714, 1628 * 12), ("Reversionary annuitants", 119, 411 * 12), ("Children (derived remainder)", 64, None)],
              src="MEABF valuation Section 2 (counts, monthly benefits $95,618,668 x 12) and Section 3 (average monthly: 4,092 / 1,628 / 411)",
              acfr=dict(benefits_and_refunds=1_173_302_782), acfr_src=F + "MEABF_val_2025.txt line 4134 (benefit payments including refunds, FY2025)"),
 "FABF": dict(total=454_037_460, rows=[("Employee annuitants", 4006, 8043 * 12), ("Spouse annuitants", 1191, 3107 * 12), ("Duty, occupational, ordinary disability and children (derived remainder)", 358, None)],
              src="FABF valuation Section 2 (4,006 / 1,191 / 202 duty / 73 occupational / 3 ordinary / 82 children; monthly benefits $37,836,455 x 12; averages $8,043 and $3,107 per month)",
              acfr=dict(benefits_and_refunds=452_300_000), acfr_src="data/pensions_2026.json acfr_fy2025.benefit_payments_incl_refunds_2025_thousands 452,300"),
 "LABF": dict(total=187_086_435, rows=[("Retirees", 2506, 65230), ("Surviving spouses", 934, 21301), ("Disability, reversionary annuitants and children (derived remainder)", 105, None)],
              src="LABF valuation Plan Membership (counts, averages) and summary page (annual benefits $187,086,435)",
              acfr=dict(benefits_and_refunds=189_963_742), acfr_src=F + "LABF_FS_2025.txt line 381 (benefits and refunds 2025)"),
}
leaves = []
for k, c in COMP.items():
    f = pens["funds"][k]; b = f["budget_2026"]; stat = b["statutory_contribution"]; adv = b["advance_contribution"]
    ben = BEN[k]
    # benefit-type pieces
    known = 0; pieces_b = []
    for lab, n, avg in ben["rows"]:
        if avg is not None:
            tot = n * avg; known += tot
            pieces_b.append({"name": lab, "count": n, "average": round(avg), "annual_benefit_dollars": round(tot), "basis": "count_x_average", "source": ben["src"]})
    rest = ben["total"] - known
    for lab, n, avg in ben["rows"]:
        if avg is None:
            pieces_b.append({"name": lab, "count": n, "average": round(rest / n), "annual_benefit_dollars": round(rest), "basis": "derived", "source": ben["src"]})
            rest = 0
    share = [dict(p, contribution_share_proxy=round(stat * p["annual_benefit_dollars"] / ben["total"])) for p in pieces_b]
    uaal = stat - c["nnc"]
    pieces = [
      {"name": "Net employer normal cost (cost of benefits earned this year, after member contributions, includes admin)", "amount": c["nnc"], "basis": "tied", "source": c["src"]},
      {"name": "Remainder toward the unfunded liability, derived: statutory contribution minus net normal cost", "amount": uaal, "basis": "derived", "source": c["src"]},
    ]
    leaves.append({"match_path_contains": [c["path"], "0976"], "amount": stat, "proposed_status": "split_proxy",
        "split_basis": "Component split is derived arithmetic (net normal cost is printed, remainder = statutory minus normal cost). Benefit-type split is a PROXY allocation by benefit-dollar share, because the City contribution is not the benefit payment.",
        "components": {"statutory_contribution_levy_year_2026": stat, "net_employer_normal_cost": c["nnc"], "total_normal_cost": c["tnc"], "expected_member_contributions": c["mem"],
                       "remainder_toward_unfunded_liability_derived": uaal, "actuarially_determined_contribution_2026_plan_year": c["adc"], "payment_on_unfunded_in_adc": c["amort"],
                       "shortfall_vs_adc_derived": c["adc"] - stat, "unfunded_liability_actuarial": f["valuation_12_31_2025"]["unfunded_liability_actuarial_value"]},
        "pieces": pieces, "benefit_type_pieces": share, "benefit_total_annual_valuation": ben["total"], "acfr_benefits_paid_2025": ben["acfr"], "acfr_source": ben["acfr_src"],
        "pieces_over_10m_after": [],
        "pieces_note": "The remainder toward the unfunded liability is still >= $10M as dollars. It is the debt the City is paying down, set by law, so the explorer shows it as 'paying for past promises' across the retirees below (count x average).",
        "why_cant_go_deeper": "The City sends one payment set by law to the retirement fund, and the fund then pays thousands of retirees, so the public records stop at how many retirees there are and what the average one gets."})
    leaves.append({"match_path_contains": [c["path"], "097A"], "amount": adv, "proposed_status": "split_proxy",
        "split_basis": "One voluntary payment above the statutory minimum, sent to the same fund. Shown with the same retiree count x average as the statutory line.",
        "pieces": [{"name": "Advance (above statute) payment, one payment to the fund", "amount": adv, "basis": "tied", "source": "data/pensions_2026.json budget_2026.advance_contribution"}],
        "pieces_over_10m_after": [],
        "why_cant_go_deeper": "This is one extra payment the City chose to make to the retirement fund on top of what the law requires."})
# Parks pension (PEABF)
leaves.append({"match_path_contains": ["Parks", "625020"], "amount": 63_332_412, "proposed_status": "split_proxy",
    "split_basis": "Segal valuation 12/31/2025 (raw/parks/pension_valuation_text.json page 10): employer normal cost incl. admin $9,419,176; total normal cost incl. admin $28,131,361; ADC (board policy) $88,904,199; expected employer contribution $63,332,412. Remainder toward unfunded liability is derived.",
    "components": {"employer_normal_cost": 9_419_176, "remainder_toward_unfunded_liability_derived": 63_332_412 - 9_419_176, "adc_board_policy": 88_904_199},
    "pieces": [{"name": "Employer normal cost", "amount": 9_419_176, "basis": "tied", "source": "raw/parks/pension_valuation_text.json p.10"},
               {"name": "Remainder toward unfunded liability (derived)", "amount": 63_332_412 - 9_419_176, "basis": "derived", "source": "same"}],
    "pieces_over_10m_after": [],
    "why_cant_go_deeper": "The Park District sends one payment set by law to its pension fund, and the fund pays about 2,700 retirees."})
meta = {"generated_by": "scripts/leaves_pensions.py", "sources_fetched": [{"url": "local files (fetched in rounds 1 and 2, see data/pensions_2026.json cites)", "http_status": "200 at fetch time", "note": "valuations PABF, MEABF, FABF, LABF; PABF and LABF financial statements; City ACFR 2025"}],
        "tied_check": {k: (pens["funds"][k]["budget_2026"]["statutory_contribution"]) for k in COMP}, "note": "Contributions are levy-year 2026 amounts paid in 2027 (data/pensions_2026.json timing_note)."}
json.dump({"meta": meta, "leaves": leaves}, open(f"{ROOT}/data/leaves_pensions.json", "w"), indent=1)
for l in leaves:
    if "components" in l: print(l["match_path_contains"], l["amount"], l["components"]["remainder_toward_unfunded_liability_derived"])
