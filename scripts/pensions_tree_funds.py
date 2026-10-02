"""Run this file: python3 scripts/pensions_tree_funds.py. Per-fund inputs for scripts/pensions_tree_build.py. Every number is printed in the cited valuation page
(PDF page index, page 1 = cover). One section per fund."""
from pensions_tree_build import add_fund, write


def S(kind, label, amount, period, basis, doc, url, page, **kw):
    d = {"kind": kind, "label": label, "period": period, "basis": basis,
         "source": {"doc": doc, "url": url, "page": page}}
    if amount is not None:
        d["amount"] = amount
    d.update(kw)
    return d


# ======================================================================= PABF (Police)
PU = "https://chipabf.org/wp-content/uploads/2026/07/PABF_20251231_Final.pdf"
PFS = "https://chipabf.org/wp-content/uploads/2026/07/final_PABF_FS_2025.pdf"
PD = "PABF Actuarial Valuation as of 12/31/2025 (Lewis & Ellis)"
PFD = "PABF Financial Statements 2025"
add_fund(dict(
    ids=dict(
        short="city.retirement.policemen-s-annuity-and-benefit-fund.0683-2005-0976.paying-down-the-shortfall-money-promised-but-nev",
        nc="city.retirement.policemen-s-annuity-and-benefit-fund.0683-2005-0976.cost-of-pensions-workers-earn-this-year",
        adv="city.retirement.policemen-s-annuity-and-benefit-fund.0683-2005-097a.extra-payment-above-what-the-law-requires"),
    val_doc=PD + ", Exhibits B, D, E, F, G; PABF Financial Statements 2025 p.17",
    val_url=PU, val_pages="44, 48-52 (valuation); FS p.17",
    src_note="Annual benefits by group: Exhibit E service retirees $914,683,048 (p.50), Exhibit F widows $94,059,866 (p.51), "
             "Exhibit G miscellaneous annuities (p.52); these add to $1,032,071,723 in Exhibit B (p.44). Death benefits $1,991,600 and "
             "refunds $11,718,221 are 2025 payments from the financial statements p.17. 110 refund payments in Exhibit D (pp.48-49).",
    short_amt=817827915,
    ben_label="$1,045,781,544 of benefit dollars (annual annuities in force at 12/31/2025 plus 2025 death benefits and refunds)",
    groups=[
        ("Service retirees", "retired officers", 11271, 914683048, "Exhibit E (p.50)."),
        ("Surviving spouses (widow annuities)", "widows and widowers", 3068, 94059866, "Exhibit F (p.51)."),
        ("Refunds to people who left", "", 0, 11718221, "2025 refunds of employee deductions, FS p.17. Exhibit D (pp.48-49) shows 110 refund payments, but that counts a different set of people than the accounting total, so no average is shown."),
        ("Duty disability", "disabled officers", 177, 14015808, "Exhibit G (p.52)."),
        ("Widows' compensation (service-connected death)", "widows", 65, 4836294, "Exhibit G (p.52)."),
        ("Death benefits", "", 0, 1991600, "2025 death benefits paid, FS p.17. The count is not printed."),
        ("Ordinary disability", "disabled officers", 29, 1647209, "Exhibit G (p.52)."),
        ("Children's annuities", "children", 166, 1441283, "Exhibit G (p.52)."),
        ("Occupational disease disability", "disabled officers", 18, 1267015, "Exhibit G (p.52)."),
        ("Children's disability", "children", 101, 121200, "Exhibit G (p.52)."),
    ],
    short_note="The valuation says this is a severely underfunded plan: funded ratio 26.1%, unfunded liability about $13.8 billion. "
               "The money here is the part of the City's payment left after the cost of this year's pensions. "
               "The State law (P.A. 99-0506) sets payments that aim for 90% funded by 2055.",
    short_side=[
        S("unfunded_liability", "Unfunded actuarial liability (promised pensions not yet saved for), 12/31/2025", 13845585439, "12/31/2025", "actual", PD, PU, 34),
        S("funded_ratio", "Funded ratio, actuarial value of assets $4,884,050,114 vs liability $18,729,635,553: 26.08%", None, "12/31/2025", "actual", PD, PU, 12, ratio=0.2608),
        S("amortization_target", "State law aims for a 90% funded ratio by plan year-end 2055 (P.A. 99-0506). The actuary's own measuring stick, "
          "a 25-year closed level-dollar payoff started 12/31/2024, has 24 years left.", None, "2055 target", "actual", PD, PU, 10, target_year=2055),
        S("amortization_payment", "Payment on the unfunded liability in the actuary's recommended 2026 contribution (25-year closed, level dollar)", 1142871201, "plan year 2026", "gov_estimate", PD, PU, 34),
        S("recommended_contribution", "Actuarially determined contribution for 2026 (City payment the actuary recommends)", 1416650276, "plan year 2026", "gov_estimate", PD, PU, 34),
        S("gap_vs_recommended", "Gap: recommended contribution minus the statutory contribution of $1,040,273,100", 376377176, "plan year 2026", "gov_estimate", PD, PU, 34),
        S("benefits_paid", "Total benefits and refunds paid in 2025 (pensions $1,035,953,513, death $1,991,600, refunds $11,718,221)", 1049663334, "2025", "actual", PFD, PFS, 17),
        S("annual_benefits_in_force", "Annual benefits in payment at 12/31/2025: 14,895 annuitants and beneficiaries", 1032071723, "12/31/2025", "actual", PD, PU, 44, members=14895),
    ],
    tiers=[
        dict(name="Tier 1 (hired before 2011)", count=4957, net_nc=130073340, page=29,
             src_note="Table 1C: Tier 1 net normal cost $130,073,340, 4,957 members.",
             note="Average net normal cost per member $26,240 = $130,073,340 / 4,957 (our division of the actuary's printed numbers). "
                  "Tier 1 payroll $672,681,254, average pay $135,703. Net of the $60,690,023 members are expected to pay in."),
        dict(name="Tier 2 (hired 2011 or later)", count=6682, net_nc=92371845, page=29,
             src_note="Table 1C: Tier 2 net normal cost $92,371,845, 6,682 members.",
             note="Average net normal cost per member $13,824 = $92,371,845 / 6,682 (our division of the actuary's printed numbers). "
                  "Tier 2 payroll $723,235,341, average pay $108,236. Net of the $65,291,641 members are expected to pay in."),
    ],
    nc_amt=222445185,
    nc_note="Net normal cost is the actuary's estimate of what this year of work by 11,639 active officers adds to the pension promise, "
            "after officers' own contributions (Table 1C, p.29). Tier 1 is hired before 1/1/2011, Tier 2 after.",
    nc_side=[
        S("active_payroll", "Active member payroll, annualized pay rate at 12/31/2025 (11,639 active members, average $119,934)", 1395916595, "12/31/2025", "actual", PD, PU, 29),
        S("active_payroll_t1", "Tier 1 payroll (4,957 members, average $135,703)", 672681254, "12/31/2025", "actual", PD, PU, 29),
        S("active_payroll_t2", "Tier 2 payroll (6,682 members, average $108,236)", 723235341, "12/31/2025", "actual", PD, PU, 29),
        S("total_normal_cost", "Total normal cost before member contributions (25.0% of pay)", 348426849, "2026", "gov_estimate", PD, PU, 29),
        S("member_contributions", "Estimated contributions by active officers themselves", 125981664, "2026", "gov_estimate", PD, PU, 29),
    ],
    adv_amt=72249824,
    adv_name="Advance payment: City pays more than State law requires",
    adv_doc=PD + " p.10",
    adv_page=10,
    adv_note="Under the City's Pension Management Policy (2022) the City budgets extra payments on top of the State-law minimum so "
             "the shortfall does not grow. The valuation lists the extras actually paid and assumes no more in its projections.",
    adv_side=[
        S("advance_history", "Extra contributions above the statutory minimum, FY2023", 89500000, "2023", "actual", PD, PU, 10),
        S("advance_history", "Extra contributions above the statutory minimum, FY2024", 79800000, "2024", "actual", PD, PU, 10),
        S("advance_history", "Extra contributions above the statutory minimum, FY2025", 67400000, "2025", "actual", PD, PU, 10),
        S("advance_history", "Extra contributions above the statutory minimum, FY2026", 36100000, "2026", "actual", PD, PU, 10),
    ],
))


# ======================================================================= FABF (Fire)
FU = "https://fabf.org/LinkClick.aspx?fileticket=G_bIYnMR31w%3d&portalid=0"
FD = "FABF Actuarial Valuation as of 12/31/2025 (Segal)"
_t1, _t2, _n = 76515423, 74644183, 93011790
_f1 = round(_n * _t1 / (_t1 + _t2), 2)
_f2 = round(_n - _f1, 2)
add_fund(dict(
    ids=dict(
        short="city.retirement.firemen-s-annuity-and-benefit-fund.0684-2005-0976.paying-down-the-shortfall-money-promised-but-nev",
        nc="city.retirement.firemen-s-annuity-and-benefit-fund.0684-2005-0976.cost-of-pensions-workers-earn-this-year",
        adv="city.retirement.firemen-s-annuity-and-benefit-fund.0684-2005-097a.extra-payment-above-what-the-law-requires"),
    val_doc=FD + ", Exhibits D.1, D.2, E and Section 2",
    val_url=FU, val_pages="35, 41-43, 52",
    src_note="Annual benefits in payment at 12/31/2025: service retirees Exhibit D.1 (p.41), spouses Exhibit D.2 (p.42, includes widows' "
             "compensation per its footnote 14, so the 63 widows' compensation annuities from Exhibit E are taken out of the spouse line), "
             "other groups Exhibit E (p.43). Refunds of contributions $3,702,355 are 2025 cash from the fund's income statement (p.52).",
    short_amt=348734731,
    ben_label="$457,739,817 of benefit dollars (annual benefits in payment at 12/31/2025 plus 2025 refunds of contributions)",
    groups=[
        ("Retired firefighters", "retirees", 4006, 386653292, "Exhibit D.1 (p.41): 3,778 men $365,720,753 and 228 women $20,932,539."),
        ("Surviving spouses", "spouses", 1128, 39109604, "Exhibit D.2 (p.42) total $44,404,654 for 1,191 spouses, minus the 63 widows' compensation annuities shown in Exhibit E (p.43)."),
        ("Duty disability", "disabled firefighters", 202, 16229924, "Exhibit E (p.43)."),
        ("Widows' compensation (service-connected death)", "widows", 63, 5295050, "Exhibit E (p.43)."),
        ("Occupational disease disability", "disabled firefighters", 73, 5549312, "Exhibit E (p.43)."),
        ("Refunds to people who left", "", 0, 3702355, "2025 refunds of contributions, income statement p.52. The count of refunds is not printed."),
        ("Children's annuities", "children", 82, 1067391, "Exhibit E (p.43)."),
        ("Ordinary disability", "disabled firefighters", 3, 132889, "Exhibit E (p.43)."),
    ],
    short_note="The valuation says the statutory funding policy 'systematically underfunds' the fund, aiming for 90% funded by 2055. "
               "Funded ratio is 24.7% and the unfunded liability is about $6.0 billion.",
    short_side=[
        S("unfunded_liability", "Unfunded actuarial accrued liability (promised pensions not yet saved for), 12/31/2025", 6048701965, "12/31/2025", "actual", FD, FU, 12),
        S("funded_ratio", "Funded ratio, actuarial value of assets $1,981,093,049 vs liability $8,029,795,014: 24.67%", None, "12/31/2025", "actual", FD, FU, 12, ratio=0.2467),
        S("amortization_target", "State law aims for 90% funded by the end of 2055. The statutory payment would take 34 years to pay off the unfunded liability (32 years for the next levy year).", None, "2055 target", "actual", FD, FU, 12, target_year=2055),
        S("amortization_payment", "Payment on the unfunded liability in the actuary's recommended 2026 contribution (layered closed 20-year bases)", 554483168, "plan year 2026", "gov_estimate", FD, FU, 28),
        S("recommended_contribution", "Actuarially determined contribution for 2026 (92.61% of payroll)", 588720377, "plan year 2026", "gov_estimate", FD, FU, 28),
        S("benefits_paid", "Benefits and refunds paid in 2025 (annuities $448,598,205, refunds $3,702,355)", 452300560, "2025", "actual", FD, FU, 52),
        S("annual_benefits_in_force", "Annual benefits in payment at 12/31/2025 to 5,557 retirees, survivors, disabled members and children (monthly $37,836,455)", 454037460, "12/31/2025", "actual", FD, FU, 12, members=5557),
    ],
    tiers=[
        dict(name="Tier 1 (hired before 2011)", count=1966, net_nc=_f1, page=62, basis="proxy",
             src_note="Table of normal cost components (p.62): Tier 1 total normal cost incl. admin $76,515,423. The valuation prints member contributions only for both tiers together ($58,147,816), so the employer cost is split by each tier's share of total normal cost.",
             note=f"Proxy: employer normal cost $93,011,790 shared by Tier 1's {_t1 / (_t1 + _t2) * 100:.1f}% of total normal cost incl. admin ($76,515,423 of $151,159,606). "
                  "The fund prints this only for both tiers together. 1,966 Tier 1 active members (p.35)."),
        dict(name="Tier 2 (hired 2011 or later)", count=2708, net_nc=_f2, page=62, basis="proxy",
             src_note="Table of normal cost components (p.62): Tier 2 total normal cost incl. admin $74,644,183. Employer cost split by share of total normal cost.",
             note=f"Proxy: employer normal cost $93,011,790 shared by Tier 2's {_t2 / (_t1 + _t2) * 100:.1f}% of total normal cost incl. admin ($74,644,183 of $151,159,606). "
                  "2,708 Tier 2 active members (p.35)."),
    ],
    nc_amt=93011790,
    nc_note="Employer normal cost is the actuary's estimate of what this year of work by 4,674 active firefighters adds to the pension promise, "
            "after firefighters' own contributions (p.28 and p.62). The tier split is our proxy.",
    nc_side=[
        S("active_payroll", "Total pensionable salary of 4,674 active members at 12/31/2025 (average $129,269)", 604204092, "12/31/2025", "actual", FD, FU, 12),
        S("projected_payroll", "Projected payroll for 2026", 635699685, "2026", "gov_estimate", FD, FU, 28),
        S("total_normal_cost", "Total normal cost before member contributions (23.16% of pay)", 147242696, "2026", "gov_estimate", FD, FU, 28),
        S("member_contributions", "Expected contributions by active firefighters themselves (9.15% of pay)", 58147816, "2026", "gov_estimate", FD, FU, 28),
        S("admin_expenses", "Administrative expenses included in the normal cost line", 3916910, "2026", "gov_estimate", FD, FU, 28),
    ],
    adv_amt=11583144,
    adv_name="One extra payment into the fund's savings",
    adv_doc=FD + " pp.10, 52",
    adv_page=10,
    adv_note="Under the City's Pension Management Policy the City budgets extra ('advance') payments on top of the State-law minimum so the "
             "shortfall does not grow. The valuation counts the January 2026 payment of $5,791,572 in its 2026 projections and says "
             "another is expected in June 2026 that it does not count.",
    adv_side=[
        S("advance_history", "Advance pension payment received in 2024", 28274000, "2024", "actual", FD, FU, 52),
        S("advance_history", "Advance pension payment received in 2025", 15640948, "2025", "actual", FD, FU, 52),
        S("advance_payment_2026", "Advance payment made January 2026 (the only 2026 payment the actuary counts)", 5791572, "2026", "actual", FD, FU, 10),
    ],
))


# ======================================================================= MEABF (Municipal)
MU = "https://www.meabf.org/wp-content/uploads/2026/06/MEABF_Actuarial-Valuation-Report-as-of-12.31.2025-06.26.2026.pdf"
MD = "MEABF Actuarial Valuation and Review as of 12/31/2025 (Segal)"
_m = [("Tier 1", 11756, 186501439), ("Tier 2", 5761, 52431252), ("Tier 3", 21862, 177311896)]
_mt = sum(x[2] for x in _m)
_mn = 146922858
_mc = [round(_mn * x[2] / _mt * 100) for x in _m]
_mc[2] += _mn * 100 - sum(_mc)
_mc = [c / 100 for c in _mc]
_mdesc = {"Tier 1": "Tier 1 (hired before 2011)", "Tier 2": "Tier 2 (hired 2011 to July 5, 2017)", "Tier 3": "Tier 3 (hired July 6, 2017 or later)"}
add_fund(dict(
    ids=dict(
        short="city.retirement.municipal-employees-annuity-and-benefit-fund.0681-2005-0976.paying-down-the-shortfall-money-promised-but-nev",
        nc="city.retirement.municipal-employees-annuity-and-benefit-fund.0681-2005-0976.cost-of-pensions-workers-earn-this-year",
        adv="city.retirement.municipal-employees-annuity-and-benefit-fund.0681-2005-097a.extra-payment-above-what-the-law-requires"),
    val_doc=MD + ", Section 3 Exhibits D.1 to D.3, Section 2, income statement",
    val_url=MU, val_pages="18, 40-43, 45",
    src_note="Annual benefits in payment at 12/31/2025: retirees Exhibit D.1 (p.40, 8,286 men $529,458,309 and 13,588 women $544,640,079), "
             "surviving spouses Exhibit D.2 (p.41), reversionary annuitants Exhibit D.3 (p.42). Children are the remainder of the printed "
             "monthly total $95,618,668 x 12 (p.18), so that line is derived. Refunds $40,088,296 and disability payments $8,185,003 are 2025 cash (p.45).",
    short_amt=818078695,
    ben_label="$1,195,697,315 of benefit dollars (annual benefits in payment at 12/31/2025 plus 2025 refunds and disability payments)",
    groups=[
        ("Retired members", "retirees", 21874, 1074098388, "Exhibit D.1 (p.40)."),
        ("Surviving spouses", "spouses", 3714, 72562411, "Exhibit D.2 (p.41)."),
        ("Refunds to members who left", "", 0, 40088296, "2025 refunds of contributions, income statement p.45. The valuation prints 1,839 refunds in the member count roll-forward (p.44) but that counts a different set, so no average is shown."),
        ("Disability payments to active members", "members on disability", 181, 8185003, "2025 disability payments, p.45. 93 ordinary and 88 duty disability members (p.17, p.33)."),
        ("Reversionary annuitants", "annuitants", 119, 586827, "Exhibit D.3 (p.42)."),
        ("Children's annuities (derived)", "children", 64, 176390, "Derived: printed monthly total of $95,618,668 x 12 minus the groups above (p.18)."),
    ],
    short_note="The valuation says the State-law policy aims for 90% funded by 2058 and 'systematically underfunds' the fund. "
               "Funded ratio is 27.4% and the unfunded liability is about $14.9 billion.",
    short_side=[
        S("unfunded_liability", "Unfunded actuarial accrued liability (promised pensions not yet saved for), 12/31/2025", 14927708891, "12/31/2025", "actual", MD, MU, 11),
        S("funded_ratio", "Funded ratio, actuarial value of assets $5,639,887,320 vs liability $20,567,596,211: 27.42%", None, "12/31/2025", "actual", MD, MU, 11, ratio=0.2742),
        S("amortization_target", "State law (P.A. 100-0023) aims for 90% funded by the end of 2058. The statutory payment would take 34 years to pay off the unfunded liability (32 years for the next levy year).", None, "2058 target", "actual", MD, MU, 11, target_year=2058),
        S("amortization_payment", "Payment on the unfunded liability in the actuary's recommended 2026 contribution", 1198582991, "plan year 2026", "gov_estimate", MD, MU, 27),
        S("recommended_contribution", "Actuarially determined contribution for 2026 (46.28% of pay)", 1350383529, "plan year 2026", "gov_estimate", MD, MU, 27),
        S("benefits_paid", "Benefits and refunds paid in 2025 (annuities $1,124,686,135, refunds $40,088,296, disability $8,185,003, health subsidies $343,348)", 1173302782, "2025", "actual", MD, MU, 45),
        S("annual_benefits_in_force", "Annual benefits in payment at 12/31/2025 to 25,771 retirees and beneficiaries (monthly $95,618,668)", 1147424016, "12/31/2025", "actual", MD, MU, 18, members=25771),
    ],
    tiers=[
        dict(name=_mdesc[x[0]], count=x[1], net_nc=c, page=55, basis="proxy",
             src_note=f"Normal cost components (p.55): {x[0]} total normal cost incl. admin ${x[2]:,}. Member contributions are printed only for all tiers together ($269,321,729), so employer cost is split by each tier's share of total normal cost.",
             note=f"Proxy: employer normal cost $146,922,858 shared by {x[0]}'s {x[2] / _mt * 100:.1f}% of total normal cost incl. admin (${x[2]:,} of ${_mt:,}). "
                  f"The fund prints this only for all tiers together. {x[1]:,} {x[0]} active members (p.33).")
        for x, c in zip(_m, _mc)],
    nc_amt=146922858,
    nc_note="Employer normal cost is the actuary's estimate of what this year of work by 39,379 active members adds to the pension promise, "
            "after members' own contributions (p.55). The tier split is our proxy.",
    nc_side=[
        S("active_payroll", "Total pensionable salary of 39,379 active members at 12/31/2025 (average $70,392)", 2771982184, "12/31/2025", "actual", MD, MU, 33),
        S("projected_payroll", "Projected payroll for 2026", 2917895225, "2026", "gov_estimate", MD, MU, 27),
        S("total_normal_cost", "Total normal cost before member contributions (14.03% of pay)", 409399589, "2026", "gov_estimate", MD, MU, 55),
        S("member_contributions", "Expected contributions by active members themselves (9.23% of pay)", 269321729, "2026", "gov_estimate", MD, MU, 55),
        S("admin_expenses", "Administrative expenses included in the normal cost line", 6844998, "2026", "gov_estimate", MD, MU, 55),
    ],
    adv_amt=161218894,
    adv_name="Two extra payments into the fund's savings (January and June 2026)",
    adv_doc=MD + " pp.10, 32, 45",
    adv_page=10,
    adv_note="Under the City's Pension Management Policy the City budgets extra ('supplemental') payments on top of the State-law minimum so the "
             "shortfall does not grow. The valuation counts the January 2026 payment of $80,609,447 and says another is expected in June 2026 "
             "(the line is exactly twice $80,609,447). It estimates the January payment cuts total required contributions through 2058 by about $160.0 million.",
    adv_side=[
        S("advance_history", "Supplemental pension payment received in 2024", 178085000, "2024", "actual", MD, MU, 45),
        S("advance_history", "Supplemental pension payment received in 2025", 168736173, "2025", "actual", MD, MU, 45),
        S("advance_payment_2026", "Supplemental payment made January 2026 (the only 2026 payment the actuary counts)", 80609447, "2026", "actual", MD, MU, 10),
        S("advance_savings", "Actuary's estimate of how much the January 2026 payment reduces total required contributions through 2058", 159998000, "through 2058", "gov_estimate", MD, MU, 32),
    ],
))


# ======================================================================= LABF (Laborers)
LU = "https://www.labfchicago.org/assets/1/7/GRS_2025_Val.pdf"
LFSU = "https://www.labfchicago.org/assets/1/7/2025_LABF_Issued_Financial_Statements.pdf"
LD = "LABF Actuarial Valuation as of 12/31/2025 (GRS)"
LFD = "LABF Financial Statements 2025"
_l = [("Tier 1 (hired before 2011)", 1196, 17305069, 27003421, 125526077, 104955, 9698352),
      ("Tier 2 (hired 2011 to July 5, 2017)", 502, 3960611, 8114017, 51387681, 102366, 4153406),
      ("Tier 3 (hired July 6, 2017 or later)", 1082, 5358376, 15072753, 87572506, 80936, 9714377)]
add_fund(dict(
    ids=dict(
        short="city.retirement.laborers-and-retirement-board-annuity-and-benefi.0682-2005-0976.paying-down-the-shortfall-money-promised-but-nev",
        nc="city.retirement.laborers-and-retirement-board-annuity-and-benefi.0682-2005-0976.cost-of-pensions-workers-earn-this-year",
        adv="city.retirement.laborers-and-retirement-board-annuity-and-benefi.0682-2005-097a.extra-payment-above-what-the-law-requires"),
    val_doc=LD + ", Summary of Actuarial Valuation p.11; " + LFD + " p.14",
    val_url=LU, val_pages="11 (valuation); FS p.14",
    src_note="Annual payments in force at 12/31/2025 (valuation p.11): employees' annuities $163,399,654 for 2,506 retirees, spouses' annuities "
             "$19,932,438 for 934 survivors, children's annuities $51,730 for 17 children, duty disability $1,513,912 plus $768,981 payments in lieu, "
             "ordinary disability $1,419,720 (57 members on disability in all). Refunds $3,580,965 are 2025 cash from the financial statements (p.14). "
             "The valuation lists 31 reversionary annuitants but prints no separate payment line for them.",
    short_amt=109949504,
    ben_label="$190,667,400 of benefit dollars (annual payments in force at 12/31/2025 plus 2025 refunds)",
    groups=[
        ("Retired members", "retirees", 2506, 163399654, "Valuation p.11."),
        ("Surviving spouses", "spouses", 934, 19932438, "Valuation p.11."),
        ("Disability (duty and ordinary)", "members on disability", 57, 3702613, "Valuation p.11: duty $1,513,912, duty payments in lieu $768,981, ordinary $1,419,720."),
        ("Refunds to members who left", "", 0, 3580965, "2025 refunds, financial statements p.14. The count of refunds is not printed."),
        ("Children's annuities", "children", 17, 51730, "Valuation p.11."),
    ],
    short_note="The valuation says the State-law policy aims for 90% funded by 2058, with most of the gain coming after 2043 ('back-loading'). "
               "Funded ratio is 43.5% and the unfunded liability is about $1.77 billion.",
    short_side=[
        S("unfunded_liability", "Unfunded actuarial accrued liability (promised pensions not yet saved for), 12/31/2025", 1771186323, "12/31/2025", "actual", LD, LU, 29),
        S("funded_ratio", "Funded ratio on actuarial value of assets: 43.5% (market value basis 44.3%)", None, "12/31/2025", "actual", LD, LU, 15, ratio=0.435),
        S("amortization_target", "State law aims for 90% funded by 2058 and holds 90% after that. The actuary's own measuring stick is a 30-year level-dollar payoff. Funded ratio is projected to stay below 50% until 2043.", None, "2058 target", "actual", LD, LU, 3, target_year=2058),
        S("amortization_payment", "30-year level-dollar payment on the unfunded liability in the actuary's recommended 2026 contribution", 134694224, "plan year 2026", "gov_estimate", LD, LU, 29),
        S("recommended_contribution", "Actuarially determined contribution for 2026 (64.41% of pay), after members' own contributions", 170342684, "plan year 2026", "gov_estimate", LD, LU, 29),
        S("gap_vs_recommended", "Gap: recommended contribution minus the estimated City contribution of $136,573,560", 33769124, "plan year 2026", "gov_estimate", LD, LU, 29),
        S("benefits_paid", "Benefits and refunds paid in 2025 (benefits $186,382,777, refunds $3,580,965)", 189963742, "2025", "actual", LFD, LFSU, 14),
        S("annual_benefits_in_force", "Annual payments in force at 12/31/2025 to 4,543 pay-status members (retirees, survivors, disabled, children)", 187086435, "12/31/2025", "actual", LD, LU, 11, members=4543),
    ],
    tiers=[
        dict(name=x[0], count=x[1], net_nc=x[2], page=31,
             src_note=f"Table 1B (p.31): {x[0]} net employer normal cost ${x[2]:,}, {x[1]:,} active members.",
             note=f"Average net employer normal cost per member ${x[2] / x[1]:,.0f} = ${x[2]:,} / {x[1]:,} (our division of the actuary's printed numbers). "
                  f"Capped payroll ${x[4]:,}, average ${x[5]:,}. Total normal cost ${x[3]:,}, of which members pay ${x[6]:,}.")
        for x in _l],
    nc_amt=26624056,
    nc_note="Net employer normal cost is the actuary's estimate of what this year of work by 2,780 active members adds to the pension promise, "
            "after members' own contributions (Table 1B, p.31).",
    nc_side=[
        S("active_payroll", "Capped payroll of 2,780 active members at 12/31/2025 (average $95,139)", 264486264, "12/31/2025", "actual", LD, LU, 31),
        S("total_normal_cost", "Total normal cost before member contributions (19.27% of expected pay, includes administration $3,822,623)", 50190191, "2026", "gov_estimate", LD, LU, 31),
        S("member_contributions", "Estimated contributions by active members themselves", 23566135, "2026", "gov_estimate", LD, LU, 31),
    ],
    adv_amt=14574818,
    adv_name="One extra payment into the fund's savings",
    adv_doc=LD + " p.15",
    adv_page=15,
    adv_note="The City has paid extra amounts above the State-law minimum since 2023 to help the fund. The valuation does not count on "
             "future extras in its projections. It says they will help reduce the City's long-term contribution requirements.",
    adv_side=[
        S("advance_history", "Extra City allocation above the statutory requirement, FY2023 (net received $11.8M)", 12100000, "2023", "actual", LD, LU, 15),
        S("advance_history", "Extra City allocation above the statutory requirement, FY2024 (net received $20.1M)", 20300000, "2024", "actual", LD, LU, 15),
        S("advance_history", "Extra City allocation above the statutory requirement, FY2025 (net received $19.9M)", 20200000, "2025", "actual", LD, LU, 15),
    ],
))


if __name__ == "__main__":
    write()
