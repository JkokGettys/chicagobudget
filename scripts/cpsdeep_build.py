#!/usr/bin/env python3
"""Build the CPS "deep" split files in data/splits/cps/ (format in build/SPLITS.md).

Run: python3 scripts/cpsdeep_build.py            (writes the JSON files, then run python3 build/cps_tree.py)

Every number comes from a file in the repo or a quoted official document. Nothing is invented.
Sections (one JSON file each):
  1. cpsdeep_bonds.json      bond series split into principal and interest, with the revenue that pays each series
Later sections are added below as they are finished.
"""
import csv
import json
import os

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
OUT = P("data", "splits", "cps")
os.makedirs(OUT, exist_ok=True)

BB_URL = "https://www.cps.edu/globalassets/cps-pages/about-cps/finance/budget/budget-2026/docs/fy2026-budget-book-final-approved-1.2.pdf"
OS_URL = "https://www.cps.edu/about/finance/official-statements-for-long-term-bonds/"
OS_BASE = "https://www.cps.edu/globalassets/cps-pages/about-cps/finance/official-statements-for-long-term-bonds/"


def write(name, author_desc, splits):
    doc = {"meta": {"author": "cps deep research", "description": author_desc, "built_by": "scripts/cpsdeep_build.py"},
           "splits": splits}
    with open(os.path.join(OUT, name), "w") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote {name}: {len(splits)} splits")


def r2(x):
    return round(float(x), 2)


# ======================================================================================= 1. BONDS
# Official statements (OS) used to break the two series with accreting bonds into their parts.
OS_FILES = {
    "1999A": "official-statement-1999a-final.pdf",
    "1998B-1": "official-statement-series-1998b-1.pdf",
    "2009G": "os_2009g.pdf",
}

REVENUE_TEXT = {
    "EBF": "State aid (Evidence-Based Funding) is the first revenue pledged to this series.",
    "IGA / PPRT": "Payments from the City of Chicago under an intergovernmental agreement (property taxes the City levies) and the State's Personal Property Replacement Tax are pledged to this series.",
    "IGA": "Payments from the City of Chicago under an intergovernmental agreement are pledged to this series.",
    "EBF / Federal Subsidy": "State aid (Evidence-Based Funding) and a federal interest subsidy are pledged to this series.",
    "EBF / PPRT": "State aid (Evidence-Based Funding) and the State's Personal Property Replacement Tax are pledged to this series.",
    "EBF / IGA": "State aid (Evidence-Based Funding) and City intergovernmental agreement payments are pledged to this series.",
    "CIT": "The Capital Improvement Tax levy (a property tax collected for school buildings) is the only source for this series. These are not alternate revenue bonds.",
}


def bond_splits():
    rows = list(csv.DictReader(open(P("data", "cps_debt_by_series_fy26.csv"))))
    bb = {"doc": "CPS FY2026 Budget Book, Debt Management chapter, Tables 2 and 3", "url": BB_URL, "page": "223-227 (printed)",
          "file": "data/cps_debt_by_series_fy26.csv"}
    splits = []
    for r in rows:
        key = r["series_key"]
        if not key:
            continue
        fg = r["fund_grant"].lower()
        prin = r2(r["fy26_principal"])
        intr = r2(r["fy26_interest"])
        total = r2(r["fy26_total"])
        out = r2(r["principal_outstanding_6_30_2025"])
        src_txt = r["pledged_source"]
        side = [
            {"kind": "debt_facts", "label": "Principal still owed on 6/30/2025", "amount": out, "period": "6/30/2025", "basis": "gov_estimate",
             "source": bb},
            {"kind": "debt_facts", "label": f"Interest rate {r['fixed_rate']}, last payment {r['final_maturity']}", "period": "FY2026",
             "basis": "gov_estimate", "source": bb},
            {"kind": "revenue_that_pays", "label": f"Paid from: {src_txt}. " + REVENUE_TEXT.get(src_txt, ""), "period": "FY2026",
             "basis": "gov_estimate", "source": bb,
             "note": "Budget book p.220: CPS alternate revenue bonds are backed first by state aid, PPRT, City IGA revenue or federal subsidies, "
                     "and second by a property tax levy that is abated (not collected) while the first source is available. "
                     "Capital Improvement Tax bonds are paid only from the CIT levy."},
        ]
        base = {"target": {"by": "id", "id": f"cps.debt.{fg}"}, "expect_amount": total, "side": side}

        if key == "1998B-1":
            # OS: Capital Appreciation Bonds only. 2025 maturity: original principal $14,606,630.00, value at maturity $59,000,000
            osrc = {"doc": "Official Statement, Unlimited Tax GO Bonds (Dedicated Tax Revenues) Series 1998B-1, inside cover (2025 maturity)",
                    "url": OS_BASE + "official-statement-series-1998b-1.pdf"}
            splits.append(dict(base, mode="budget_split", pieces=[
                {"name": "Series 1998B-1: money borrowed in 1998 (principal)", "amount": prin, "basis": "tied", "source": osrc,
                 "why": "In 1998 CPS borrowed this part. The bond pays nothing until the end, so this is the day the original loan is repaid.",
                 "note": "Capital appreciation bond: it pays no interest each year. The Official Statement lists the 12/1/2025 maturity at $14,606,630.00 original principal and $59,000,000 total value at maturity ($1,237.85 per $5,000 at maturity)."},
                {"name": "Series 1998B-1: interest that built up since 1998 (accreted interest)", "amount": intr, "basis": "tied", "source": osrc,
                 "why": "This bond adds interest to what is owed for 27 years and pays it all on one day, so this is the interest bill that came due.",
                 "note": "Equals $59,000,000 value at maturity minus $14,606,630 original principal."},
            ], note="Whole FY2026 payment is the final value of the bonds that mature 12/1/2025 (capital appreciation bonds). It ties to the Official Statement: $59,000,000 at maturity."))
        elif key == "1999A":
            osrc = {"doc": "Official Statement, Unlimited Tax GO Bonds (Dedicated Tax Revenues) Series 1999A, inside cover and mandatory sinking fund schedule",
                    "url": OS_BASE + "official-statement-1999a-final.pdf"}
            splits.append(dict(base, mode="budget_split", pieces=[
                {"name": "Series 1999A: principal repaid", "amount": prin, "basis": "tied", "source": osrc,
                 "why": "This is the loan itself being paid back on 12/1/2025, split below into the two kinds of bond in this series.",
                 "children": [
                     {"name": "Zero-coupon bonds (capital appreciation), original principal due 12/1/2025", "amount": 8215896.00, "basis": "tied", "source": osrc,
                      "why": "The money borrowed in 1999 on bonds that pay nothing until they mature.",
                      "note": "Official Statement: 2025 maturity original principal $8,215,896.00, $1,239.20 per $5,000 at maturity, so $33,150,000 at maturity."},
                     {"name": "Regular bonds called by the sinking fund schedule (term bonds due 2026)", "amount": 27165000.00, "basis": "tied", "source": osrc,
                      "why": "A set yearly slice of the 5.5% term bonds that the 1999 documents require CPS to pay off each December 1.",
                      "note": "Official Statement: mandatory sinking fund redemption of $27,165,000 on 12/1/2025."}]},
                {"name": "Series 1999A: interest paid", "amount": intr, "basis": "tied", "source": osrc,
                 "why": "This is the interest bill for the year, split below into built-up interest on the zero-coupon bonds and yearly interest on the regular bonds.",
                 "children": [
                     {"name": "Built-up interest on the zero-coupon bonds (accreted interest)", "amount": 24934104.00, "basis": "tied", "source": osrc,
                      "why": "Interest that piled up since 1999 on bonds that pay it all at the end.",
                      "note": "$33,150,000 at maturity minus $8,215,896 original principal."},
                     {"name": "Yearly interest on the 5.5% regular bonds", "amount": 2324987.50, "basis": "tied", "source": osrc,
                      "note": "5.5% x half year on $55,855,000 (Dec 2025) plus 5.5% x half year on $28,690,000 (Jun 2026), balances from the sinking fund schedule."}]},
            ], note="Ties to the Official Statement: sinking fund $27,165,000 + zero-coupon maturity $33,150,000 + term-bond interest $2,324,987.50 = $62,639,987.50."))
        elif key == "2009G":
            osrc = {"doc": "Official Statement, Series 2009G Qualified School Construction Bonds; CPS FY2026 Budget Book Table 2 note 2 and p.219 (sinking fund)",
                    "url": OS_BASE + "os_2009g.pdf"}
            splits.append(dict(base, mode="budget_split", pieces=[
                {"name": "Series 2009G: final repayment of the loan (principal)", "amount": prin, "basis": "tied", "source": osrc,
                 "why": "This is the last payment on a 2009 school-building loan. CPS saved this money in a sinking fund over 15 years, so it does not add to this year's operating cost.",
                 "note": "Budget book: paid from a sinking fund funded by required deposits since FY2011 and 'did not add to the District's annual debt service costs funded by operations in FY2026'. Matures 12/15/2025."},
                {"name": "Series 2009G: interest (1.75% supplemental coupon)", "amount": intr, "basis": "tied", "source": osrc,
                 "note": "$254,240,000 x 1.75% for one half year. Bonds were Qualified School Construction Bonds, so most of the investors' return was a federal tax credit."},
            ], note="Principal is $254.2M of the $256.5M. The budget book says it is paid from a sinking fund saved up since FY2011, not from this year's revenue."))
        elif prin > 0:
            splits.append(dict(base, mode="budget_split", pieces=[
                {"name": f"Series {key}: principal repaid (the loan itself)", "amount": prin, "basis": "tied", "source": bb,
                 "why": "This is the part of the bond that is paid back this year, the original loan, as set by the bond's payment schedule.",
                 "note": f"Rate {r['fixed_rate']}, last payment {r['final_maturity']}."},
                {"name": f"Series {key}: interest paid to bondholders", "amount": intr, "basis": "tied", "source": bb,
                 "why": "This is the yearly interest on what CPS still owes on this bond.",
                 "note": f"Rate {r['fixed_rate']}."},
            ]))
        else:
            # interest only this year: the box already is the interest. Keep the box, add the facts.
            sp = dict(base, mode="side_only",
                      note=f"All interest this year, no principal is due until later (last payment {r['final_maturity']}). "
                           f"Paid from {src_txt}.")
            splits.append(sp)
    return splits


# ======================================================================================= 2. PENSION RESERVE, CONTINGENCIES, VACANCY
BB_PENS = {"doc": "CPS FY2026 Budget Book, Pensions chapter (CPS' Employer Contribution Requirements)", "url": BB_URL, "page": "35-37 (printed)"}
CTPF_SRC = {"doc": "CTPF Actuarial Valuation 6/30/2025, Executive Summary p.1", "url": "https://www.ctpf.org/sites/files/2025-10/CTPF_FundingVal_2025_Final.pdf",
            "file": "data/cps_ctpf_valuation_2025.csv"}


def reserve_splits():
    # Teacher pension arithmetic (all inputs are published numbers):
    board_required = 646_234_000 + 17_332_000      # CTPF valuation p.1: required + additional Board contribution
    levy = 602_309_665                             # BI: CTPF Pension Levy line (budget book: $602.3M)
    diversion = board_required - levy              # = 61,256,335 ; budget book p.36: "$61.3 million" operating diversion
    state = 346_838_000 + 16_256_000               # State normal cost + additional State = $363.094M
    school_level = 279_424_453.85 + 24_355_551.94  # BI A57105 + A57110 (teacher employer pension charged to schools and programs)
    line = 120_570_340
    piece1 = diversion
    piece2 = line - piece1                         # remainder; equals state - school_level within $11
    check = state - school_level
    assert abs(piece2 - check) < 20, (piece2, check)
    splits = [{
        "target": {"by": "id", "id": "cps.pensions.pension.fg115-000000-p119004-a58115"},
        "expect_amount": line, "mode": "budget_split",
        "note": "Budget-only reserve line (it is not a payment to anyone). Official explanation: the budget book says CPS pays $663.6M of the teacher pension fund's required "
                "$1,026.7M: $602.3M comes from the pension levy and $61.3M from the operating budget (p.36-37). The State pays the other $363.1M. The pieces below are our "
                "arithmetic from those published numbers (see each piece), not a CPS-published split of this line.",
        "pieces": [
            {"name": "CPS operating money diverted to the teacher pension fund", "amount": piece1, "basis": "proxy", "source": BB_PENS,
             "why": "The pension tax is not big enough to cover what CPS owes the teachers' pension fund, so CPS must add this much from its regular school money.",
             "note": "Method: Board required contribution $646,234,000 plus additional Board contribution $17,332,000 (CTPF valuation p.1) = $663,566,000, minus the $602,309,665 levy = $61,256,335. "
                     "The budget book reports this gap as '$61.3 million' (operating revenue diversion)."},
            {"name": "State's share of the teacher pension that schools are not charged for", "amount": piece2, "basis": "proxy", "source": CTPF_SRC,
             "why": "The State pays part of CPS teachers' pensions on CPS's behalf, and this part appears to be the matching cost in the budget (our reading of the numbers, not a CPS statement).",
             "note": "Method: remainder of the line. It matches the State's FY2026 share $363,094,000 (normal cost $346,838,000 + additional $16,256,000, CTPF valuation p.1) minus the "
                     f"$303,780,006 of teacher employer pension already charged to schools and programs (accounts A57105 + A57110), which is ${check:,.0f}, within $11 of the remainder. "
                     "Whole teacher pension chain ties: $1,160.594M (research/cps_deep.md section 1)."},
        ],
        "side": [
            {"kind": "official_explanation", "label": "Budget book: CPS contributes $663.6M for teacher pensions, $602.3M from the pension levy and $61.3M from operating revenue",
             "amount": 61_300_000, "period": "FY2026", "basis": "gov_estimate", "source": BB_PENS},
            {"kind": "official_explanation", "label": "Budget book: the operating diversion was $142.7M in FY2024 and $102.9M in FY2025", "period": "FY2024-FY2026", "basis": "gov_estimate", "source": BB_PENS},
        ],
    }]
    return splits


def reserve_side_splits():
    """Contingencies and the vacancy factor: no itemised use exists, so add the official explanation and the matching revenue as side info."""
    cont_src = {"doc": "CPS FY2026 Budget Book, 'Contingencies' in the operating budget summary", "url": BB_URL, "page": "15-16 (printed)"}
    cont_txt = ("Budget book: contingencies are 'funding that has been budgeted but not yet allocated to specific accounts or units where it will eventually be spent'. "
                "'Schools are not required to allocate all of their funds, but can hold some in contingency' and 'the District holds grant funds in contingency, particularly if the grant is not yet confirmed.' "
                "The contingency budget fell $155M from FY2025, driven largely by the end of pandemic-era grants.")
    items = [
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg324-041008-p600002-0", 120_000_000,
         "Matching income line: 'Others' in fund 324 (Other Grants) is budgeted at $136,177,302. Money for state, local and private grants that may arrive during the year, held here until a grant is confirmed."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg367-041008-p600002-3", 50_396_605.49,
         "Matching income line: federal Title I School Improvement grants (account A44331) are budgeted at $77,256,376 in fund 367. This contingency appears to be the part of that grant income not yet assigned to a school or program (same fund, our reading)."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg124-002239-p600005-4", 50_000_000,
         "Matching income line: 'Payments From Schools' (A45124) of $50,000,000 in fund 124 (school-generated money, 'Internal Accounts Book Transfers'). Spending authority for school-raised money that moves through the central books."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg332-041008-p888888-5", 35_330_376,
         "Federal grant fund 332 (NCLB / Title programs). Held back until federal grant awards are confirmed."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg124-150900-p600005-7", 30_000_000,
         "School-generated fund 124, 'Grants - Supplemental'. Spending authority for grants and donations that schools secure during the year."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg332-041008-p600002-8", 25_000_000,
         "Federal grant fund 332. Held back for federal grants expected to expand during the year."),
        ("cps.citywide.set-asides.u12670.reserves.a57915.fg130-000000-p888888-9", 25_000_000,
         "Matching income line: 'Fund Balance Appropriated' (A40001) of $25,000,000 in the CPS Blueprint Fund (fund 130). The budget book (p.10) says CPS used $25M of a 2023 philanthropic gift to help close the FY2026 deficit. The book does not name the fund, so this match is by amount only."),
    ]
    out = []
    for nid, amt, extra in items:
        out.append({"target": {"by": "id", "id": nid}, "expect_amount": amt, "mode": "side_only",
                    "note": "Official explanation (budget book): money budgeted but not yet assigned. See side info.",
                    "side": [{"kind": "official_explanation", "label": cont_txt, "period": "FY2026", "basis": "gov_estimate", "source": cont_src},
                             {"kind": "official_explanation", "label": extra, "period": "FY2026", "basis": "gov_estimate",
                              "source": {"doc": "CPS BI budget data (fund and account descriptions, revenue by fund)", "file": "raw/cps/cps_2026_rev_fund_account.csv"}}]})
    vac_src = {"doc": "CPS FY2026 Budget Book, glossary 'Vacancy Savings' and Appendix B (school funding formula)", "url": BB_URL, "page": "256 and 285 (pdf)"}
    vac_txt = ("Budget book glossary: vacancy savings are 'the anticipated savings resulting from the delay in staffing new and vacant positions.' "
               "In the budget the vacancy factor is a single FY2026 program (Vacancy Factor, P109981) of -$200,000,000 in the General Education Fund: "
               "-$143,275,556 against teacher salaries and -$56,724,444 against career service salaries. It is a budget-only offset: CPS plans for salary lines to come in lower because it expects not to fill every job all year.")
    for nid, amt in (("cps.citywide.set-asides.u12670.salaries.a58110.fg115-000000-p109981-0", -143_275_556.0),
                     ("cps.citywide.set-asides.u12670.salaries.a58210.fg115-000000-p109981-0", -56_724_444.44)):
        out.append({"target": {"by": "id", "id": nid}, "expect_amount": amt, "mode": "side_only",
                    "note": "Official explanation: planned savings because some jobs will sit empty for part of the year (vacancy savings).",
                    "side": [{"kind": "official_explanation", "label": vac_txt, "period": "FY2026", "basis": "gov_estimate", "source": vac_src},
                             {"kind": "prior_year_budget", "label": "FY2025 adopted vacancy factor in the same fund: -$123,275,556 teacher salaries and -$5,724,444 career service salaries",
                              "period": "FY2025", "basis": "gov_estimate",
                              "source": {"doc": "CPS BI actuals pull (adopted FY2025)", "file": "raw/cps/cps_2026_actuals_unit_fund_account.csv"}}]})
    return out


# ======================================================================================= 3. CAPITAL
CAP_SRC = {"doc": "CPS FY2026 Capital Budget project sheets", "url": "http://schoolreports.cps.edu/capitalplan/", "file": "raw/cps/cps_2026_capital_projects_detail.csv"}


def capital_splits():
    ex = list(csv.DictReader(open(P("raw", "cps", "cps_2026_capital_expenditures.csv"))))
    it = [r for r in ex if r["Unit"] == "12510"]
    exp_src = {"doc": "CPS Capital Expenditures (Oracle BI subject area), FY2026 project expenditures", "file": "raw/cps/cps_2026_capital_expenditures.csv",
               "url": "https://biportal.cps.edu/analytics/", "note": "Expenditure by project, project fiscal year 2026, period year 2026"}
    explain = {
        "2026-12510-SFW": ("Program Bridge (new accounting, HR and purchasing system)",
                           "CPS is replacing its old finance and HR computer systems with a new cloud system. The project sheet lists 'Bridge-ERP implementation' under this program."),
        "2026-12510-SFW-1": ("Safari Montage (video and learning library software)", None),
        "2026-12510-LAN": ("Data network upgrades in schools (LAN)", None),
        "2026-12510-SFW-2": ("STREAM (software project)", None),
    }
    pieces = []
    for r in sorted(it, key=lambda r: -float(r["expenditure"] or 0)):
        amt = round(float(r["expenditure"] or 0), 2)
        if amt <= 0:
            continue
        nm, why = explain.get(r["Project Number"], (r["Project Name"], None))
        p = {"name": f"{nm}: spent so far", "amount": amt, "basis": "paid_to_date", "source": exp_src,
             "note": f"Project {r['Project Number']}, category: {r['Project Type Description']}, paid for by: {r['Project Source']}."}
        if amt >= 10_000_000:
            p["why"] = why or "This is one IT project's spending so far this year."
        pieces.append(p)
    spent = sum(p["amount"] for p in pieces)
    splits = [{
        "target": {"by": "id", "id": "cps.capital.it-security-and-other-projects.tbd-15"},
        "expect_amount": 108_000_000, "mode": "paid_to_date", "pieces": pieces,
        "residual": {"name": "IT money budgeted but not spent on a named project yet",
                     "why": "CPS has not yet charged this part of the IT money to a named project, so there is nothing to list."},
        "note": "Official purpose (project sheet): 'improved cybersecurity, data warehouse upgrades, ITS roadmap development, generative AI pilot, digital curriculum, Bridge-ERP implementation, "
                "upgrades to school network services to enhance network reliability and speed.' The IT program is $113,015,321 in all: this $108,000,000 from CPS funds plus $5,015,321 paid by "
                "outside funds (E-Rate, a federal school internet subsidy). The project-level spending below cannot be separated by funding source, so it is shown here.",
        "side": [
            {"kind": "contract_authority", "label": "Board-approved FY26 spending authority, Sentinel Technologies, data network upgrades for schools (Board Report 25-0320-PR6): CPS funds $17,513,614 plus E-Rate $4,500,000",
             "amount": 17_513_614, "period": "FY2026", "basis": "gov_estimate",
             "source": {"doc": "Board Report 25-0320-PR6", "url": "https://www.cpsboe.org/content/actions/2025_03/25-0320-PR6.pdf"}},
            {"kind": "contract_authority", "label": "Oracle America, ERP cloud platform (Board Report 24-0222-PR11): $9,000,000 in FY26, charged to Fund 115 (operating), so not part of this capital line",
             "amount": 9_000_000, "period": "FY2026", "basis": "gov_estimate",
             "source": {"doc": "Board Report 24-0222-PR11", "url": "https://www.cpsboe.org/content/actions/2024_02/24-0222-PR11.pdf"}},
            {"kind": "contract_authority", "label": "IBM, ERP system integrator (Board Report 24-1212-PR5): $24,000,000 in FY26, charged to Fund 115 (operating), so not part of this capital line",
             "amount": 24_000_000, "period": "FY2026", "basis": "gov_estimate",
             "source": {"doc": "Board Report 24-1212-PR5", "url": "https://www.cpsboe.org/content/actions/2024_12/24-1212-PR5.pdf"}},
        ],
    }]
    # Emergency repairs, state projects, support services: official purpose and matching revenue only
    splits.append({
        "target": {"by": "id", "id": "cps.capital.facility-needs.tbd-8"}, "expect_amount": 80_000_000, "mode": "side_only",
        "note": "Official purpose (project sheet): 'funding for unanticipated/emergency projects throughout FY26.' Nothing is assigned to a school in advance, by design. "
                "The sheet (7/14/2025) showed $0 spent.",
        "side": [{"kind": "official_explanation", "label": "Project sheet: 'The purpose of this funding is for unanticipated/emergency projects throughout FY26.' Start and finish: 'Varies'",
                  "amount": 80_000_000, "period": "FY2026", "basis": "gov_estimate", "source": CAP_SRC},
                 {"kind": "spending_signal", "label": "CPS capital expenditure data lists 40 FY2026 jobs with 'emergency' in the name, $1,069,697 in all (leaks, sewers, roofs, boilers). They are paid from many different capital and repair lines, so they are not tied to this $80M",
                  "amount": 1_069_696.81, "period": "FY2026", "basis": "paid_to_date",
                  "source": {"doc": "CPS Capital Expenditures (Oracle BI)", "file": "raw/cps/cps_2026_capital_expenditures.csv"}}]})
    splits.append({
        "target": {"by": "id", "id": "cps.capital.facility-needs.tbd-13"}, "expect_amount": 25_000_000, "mode": "side_only",
        "note": "This is the outside-funded part of a $30,000,000 program ($5,000,000 from CPS funds plus $25,000,000 State grants). Official purpose: 'targeted renovations based upon the parameters provided in awarded state grants.'",
        "side": [{"kind": "revenue_that_pays", "label": "Budget book capital revenue table: State capital grants of $25.0M in FY2026. CPS spends this only if the State money is awarded",
                  "amount": 25_000_000, "period": "FY2026", "basis": "gov_estimate",
                  "source": {"doc": "CPS FY2026 Budget Book, Capital Budget, Table 2 (Summary of Capital Projects Funds)", "url": BB_URL, "page": "217 (printed)"}}]})
    splits.append({
        "target": {"by": "id", "id": "cps.capital.management-administrative.tbd-6"}, "expect_amount": 23_000_000, "mode": "side_only",
        "note": "Official purpose (project sheet and budget book): 'facility condition assessments, capital planning, estimating, managing project and construction timelines, managing the capital budget, and ensuring the effective design, implementation, and construction of various capital projects.' The five-year plan keeps this at $23.0M a year.",
        "side": [{"kind": "spending_signal", "label": "CPS capital expenditure data shows 17 'CIP Management' projects with $31,345,033 of FY2026 spending, mostly one citywide management project ($28,913,238). It is shared across capital funds, so it is not tied to this $23.0M line",
                  "amount": 31_345_033.1, "period": "FY2026", "basis": "paid_to_date",
                  "source": {"doc": "CPS Capital Expenditures (Oracle BI)", "file": "raw/cps/cps_2026_capital_expenditures.csv"}}]})
    return splits


# ======================================================================================= 4. PRESCHOOL, LUNCH, SPECIAL ED TUITION
def supplier_fy26():
    rows = json.load(open(P("raw", "cps", "cps_supplier_payments_FY2026.json")))
    return {r["Name"]: float(r["PaymentAmount"]) for r in rows}


SUP_SRC = {"doc": "CPS procurement API, supplier payments FY2026 (vendor totals, not tied to budget lines)",
           "url": "https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026", "file": "raw/cps/cps_supplier_payments_FY2026.json"}


def preschool_lunch_splits():
    sup = supplier_fy26()
    out = []
    iga = lambda n, u: {"doc": f"Board Report {n}", "url": f"https://www.cpsboe.org/content/actions/{u}/{n}.pdf"}  # noqa: E731
    out.append({
        "target": {"by": "id", "id": "cps.citywide.early-childhood.u11385.contracts.a54125.fg362-376689-p410001-0"},
        "expect_amount": 88_143_619, "mode": "side_only",
        "note": "Plain words: CPS passes this state grant money to the City's Department of Family and Support Services (DFSS), which pays about 88 community preschool and "
                "infant and toddler programs. CPS does not publish what each program gets, and the DFSS provider list is behind a login, so no provider boxes are shown. "
                "The budget line ($88.1M) is smaller than the Board's spending limit for the agreement ($95.6M for FY2026), and the difference is not explained in the sources.",
        "side": [
            {"kind": "contract_authority", "label": "Board Report 25-0925-EX2: fifth and final renewal of the agreement with the City's Department of Family and Support Services, not to exceed $99,624,439, "
             "'to support approximately 90 agencies to service prenatal parents and birth to 5 years of age'. Paid from Fund 362, Early Childhood Block Grant (state money from the Illinois State Board of Education)",
             "amount": 99_624_439, "period": "FY2026", "basis": "gov_estimate", "source": iga("25-0925-EX2", "2025_09")},
            {"kind": "contract_authority", "label": "Board Report 26-0730-EX2 (July 2026) amends it: FY2026 cut to $95,624,439, $4,000,000 moved to FY2027, term extended to 8/31/2026, about 88 agencies",
             "amount": 95_624_439, "period": "FY2026", "basis": "gov_estimate", "source": iga("26-0730-EX2", "2026_07")},
            {"kind": "contract_authority", "label": "Board Report 25-1218-EX4: new agreement for FY2027 at $49,100,000 for about 55 agencies, because oversight is now shared between DFSS and five other City Head Start grantees",
             "amount": 49_100_000, "period": "FY2027", "basis": "gov_estimate", "source": iga("25-1218-EX4", "2025_12")},
            {"kind": "vendor_payment", "label": "CITY OF CHICAGO paid FY2026 by CPS, all agreements together (vendor total, includes other City agreements, not tied to this line)",
             "amount": sup["CITY OF CHICAGO"], "period": "FY2026", "basis": "paid_to_date", "source": SUP_SRC},
            {"kind": "official_explanation", "label": "Budget book, Office of Early Childhood Education: 'Continue to sub-grant a portion of the Illinois Early Childhood Block Grant to DFSS to support the Community-Based Preschool for All and Prevention Initiative'",
             "period": "FY2026", "basis": "gov_estimate", "source": {"doc": "CPS FY2026 Budget Book, Office of Early Childhood Education", "url": BB_URL, "page": "77-78 (printed)"}},
        ]})
    out.append({
        "target": {"by": "id", "id": "cps.citywide.food.u12050.supplies.a53205.fg312-000000-p256013-0"},
        "expect_amount": 56_983_670, "mode": "side_only",
        "note": "Plain words: this is the food budget for school lunches, paid from the Lunchroom Fund. Two companies run CPS school food, Aramark and Open Kitchens, under one "
                "Board contract. Their payments cover all meals (breakfast, lunch, snacks, supper), so they cannot be assigned to this lunch line. Most of the money comes back from the federal government.",
        "side": [
            {"kind": "contract_authority", "label": "Board Report 25-0424-PR6: third renewal of the food management contract with Aramark Educational Services and Open Kitchens, not to exceed $116,000,000 for 7/1/2025 to 6/30/2026, about 700 sites (original agreement 22-0525-PR15 was $88,500,000)",
             "amount": 116_000_000, "period": "FY2026", "basis": "gov_estimate", "source": iga("25-0424-PR6", "2025_04")},
            {"kind": "vendor_payment", "label": "ARAMARK EDUCATIONAL SERVICES, LLC paid FY2026 (all meals, vendor total)",
             "amount": sup["ARAMARK EDUCATIONAL SERVICES, LLC"], "period": "FY2026", "basis": "paid_to_date", "source": SUP_SRC},
            {"kind": "vendor_payment", "label": "OPEN KITCHENS, INC. paid FY2026 (all meals, vendor total)",
             "amount": sup["OPEN KITCHENS, INC."], "period": "FY2026", "basis": "paid_to_date", "source": SUP_SRC},
            {"kind": "revenue_that_pays", "label": "Budget book: CPS expects $214M of federal meal reimbursements in FY2026, $209M for lunches, breakfasts, snacks and donated foods, $3.4M for the after-school adult-and-child food program, $2.0M for fresh fruit and vegetables. Every CPS school gives free meals to all students (Community Eligibility Provision)",
             "amount": 214_000_000, "period": "FY2026", "basis": "gov_estimate", "source": {"doc": "CPS FY2026 Budget Book, Revenue chapter (Child Nutrition Programs)", "url": BB_URL, "page": "27-28 (printed)"}},
            {"kind": "official_explanation", "label": "Budget book, Nutrition Support Services: department plus school-budget total of $223.1M for FY2026 (FY2025 approved $220.1M); 'reflects an increase in food costs and other programmatic changes'",
             "amount": 223_134_609, "period": "FY2026", "basis": "gov_estimate", "source": {"doc": "CPS FY2026 Budget Book, Nutrition Support Services", "url": BB_URL, "page": "152-153 (printed)"}},
        ]})
    return out


# Providers whose own websites or ISBE listings say they run ISBE-approved private special education programs (checked 2026-10-02).
# Pathways in Education, Ombudsman and Camelot are left out: Pathways and Ombudsman are CPS alternative high schools with their own budget units,
# and Camelot's Board Reports are for alternative safe school contracts, so their payments are not tuition for special education placements.
SPED_PROVIDERS = [
    ("SPECIAL EDUCATION SERVICES DBA MENTA ACADEMY CHICAGO WEST", "Menta Academy (Special Education Services)", "ISBE-approved nonpublic special education day school (menta.com, ISBE private facility listing site 1815)"),
    ("EASTER SEALS METROPOLITAN CHICAGO, INC.", "Easterseals Academy (Easter Seals Metropolitan Chicago)", "approved by ISBE for students 3 to 22 (eastersealschicago.org/programs/easterseals-academy)"),
    ("Leslie Shankman School Corporation dba Sonia Shankman Orthogenic Schoo", "Sonia Shankman Orthogenic School", "ISBE-approved therapeutic day school (oschool.org)"),
    ("LAWRENCE HALL", "Lawrence Hall Therapeutic Day School", "licensed by ISBE, part of the CPS network (lawrencehall.org)"),
    ("COVE SCHOOL", "The Cove School", "approved by the State Board of Education for students with learning disabilities (coveschool.org)"),
    ("ELIM CHRISTIAN SCHOOL", "Elim Christian School", "approved for private special education by ISBE (elimcs.org)"),
    ("NEW HORIZON CENTER FOR THE DEVELOPMENTALLY DISABLED DBA NEW HORIZON CE", "New Horizon Center", "children's program approved by ISBE (newhorizoncenter.org)"),
    ("REDWOOD SCHOOLS, INC.", "Redwood Schools (Everstone Day School)", "ISBE-approved (lmais.org school listing)"),
    ("SHRUB OAK INTERNATIONAL SCHOOL, LLC", "Shrub Oak International School (New York)", "out-of-state residential placements named in Board Reports 23-0125-EX26, 23-0222-EX2, 24-0627-EX2"),
    ("THE ACHIEVEMENT CENTERS INC DBA ACACIA ACADEMY", "Acacia Academy", "approved by ISBE for out-of-district placement (acaciaacademy.com)"),
    ("Soaring Eagle Academy", "Soaring Eagle Academy", "ISBE-approved nonpublic therapeutic day school (soaringeagleacademy.org)"),
]


def sped_splits():
    sup = supplier_fy26()
    pieces = []
    for key, nice, basis_txt in SPED_PROVIDERS:
        hits = [v for k, v in sup.items() if k.startswith(key)]
        assert len(hits) == 1, (key, hits)
        amt = hits[0]
        p = {"name": f"{nice}: paid so far", "amount": round(amt, 2), "basis": "paid_to_date", "source": SUP_SRC,
             "note": f"Vendor total paid by CPS in FY2026 under the name '{key}'. Why it is listed: {basis_txt}. The total can include other CPS contracts with the same organization, and CPS does not link payments to budget lines."}
        if amt >= 10_000_000:
            p["why"] = "This is what CPS has paid one private special education school so far this year for students whose plans say they need that setting."
        pieces.append(p)
    tot = sum(p["amount"] for p in pieces)
    return [{
        "target": {"by": "id", "id": "cps.citywide.special-education.u11674.contracts.a54305.fg114-376711-p124904-0"},
        "expect_amount": 66_654_450, "mode": "paid_to_date", "pieces": pieces,
        "residual": {"name": "Tuition budgeted but not matched to a payment shown here",
                     "why": "CPS pays many other private schools, and some listed schools were paid from other lines, so this part has no provider boxes."},
        "note": "Plain words: when a student's plan (IEP) says no CPS school can serve them, CPS pays a private school's tuition. The boxes are FY2026 vendor payments to private schools whose "
                f"own pages or ISBE listings say they are approved for special education (together ${tot:,.0f}). Payments are by vendor, not by budget line, so this is a partial match and the boxes "
                "can include other contracts. Left out on purpose: Pathways in Education and Ombudsman (CPS alternative high schools with their own budgets) and Camelot (alternative safe school contracts).",
        "side": [
            {"kind": "official_explanation", "label": "Budget book: the Contracts category 'includes tuition for charter schools and private therapeutic schools'", "period": "FY2026", "basis": "gov_estimate",
             "source": {"doc": "CPS FY2026 Budget Book, Operating Budget, Contracts", "url": BB_URL, "page": "16 (printed)"}},
            {"kind": "official_explanation", "label": "This line is in the Special Education Fund (114), 'Special Education - Non-Public Tuition'. A second line of $6,656,520 ('IDEA Room & Board', federal funds) pays the residential part", "period": "FY2026", "basis": "gov_estimate",
             "source": {"doc": "CPS BI budget data", "file": "raw/cps/cps_2026_exp_unit_fund_program_account.csv"}},
            {"kind": "contract_authority", "label": "Board Reports 23-0125-EX26, 23-0222-EX2, 23-0726-EX2 and 24-0627-EX2 approve individual out-of-state residential placements at Shrub Oak International School, each capped at $600,000 a year (student initials in the reports are not shown here)",
             "period": "FY2023-FY2025", "basis": "gov_estimate", "source": {"doc": "CPS Board Reports (cpsboe.org)", "url": "https://www.cpsboe.org/content/actions/2024_06/24-0627-EX2.pdf"}},
        ]}]



if __name__ == "__main__":
    write("cpsdeep_bonds.json", "CPS bond series split into principal and interest (budget book Tables 2-3, official statements) with the revenue that pays each series", bond_splits())
    write("cpsdeep_reserves.json", "CPS pension general-fund reserve split into the operating diversion and the State share; contingencies and vacancy factor explained from the budget book", reserve_splits() + reserve_side_splits())
    write("cpsdeep_capital.json", "CPS capital: IT centralized program spent-so-far by project; emergency repairs, state projects and support services explained from project sheets", capital_splits())
    write("cpsdeep_services.json", "CPS State Preschool for All (DFSS agreement), lunch program (food contract) explained; special education private tuition matched to provider payments", preschool_lunch_splits() + sped_splits())
