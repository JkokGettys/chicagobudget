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


if __name__ == "__main__":
    write()
