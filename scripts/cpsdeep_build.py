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


if __name__ == "__main__":
    write("cpsdeep_bonds.json", "CPS bond series split into principal and interest (budget book Tables 2-3, official statements) with the revenue that pays each series", bond_splits())
