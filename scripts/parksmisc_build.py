"""Build data/splits/parks/misc.json and data/splits/city/misc.json (detail for Park District managed venues,
utilities, pension, bonds and for three City lines: Emergency Medical Transportation, the CTA share of the
real property transfer tax, and the judgments and settlements lines).

Run:   python3 scripts/parksmisc_build.py [parks|city|all]        (default all)
Reads: data/parks_2026.json, data/city_vendors_items_*.json (tracked) and these cached files in raw/parksmisc/
       (gitignored, URLs below, fetched by fetch() if missing):
         js_2026.xlsx          Law Department "Judgment and Settlement Payment Requests", 2026 through 7/31/2026
         ../parks/acfr25_text.json   Park District FY2025 ACFR text, page 77 (bond table)
Rules: build/SPLITS.md. Nothing here is estimated except the pension split (labelled proxy, same method as the
       City pension funds). Individuals are never named: settlements are summed by department and type of case.
"""
import collections
import json
import os
import re
import sys
import urllib.request

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
RAW = P("raw", "parksmisc")

JS_URL = ("https://www.chicago.gov/content/dam/city/depts/dol/JudgementAndSettlementRequests/2026/"
          "Finance%20Cmte%202026%20JS%20through%207.31.26.xlsx")
JS_PAGE = "https://www.chicago.gov/city/en/depts/dol/supp_info/judgment-and-settlement-payments-requests.html"


def fetch(url, path):
    if not os.path.exists(path):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with open(path, "wb") as f:
            f.write(urllib.request.urlopen(req, timeout=120).read())
    return path


def S(doc, url=None, page=None, note=None):
    d = {"doc": doc}
    if url:
        d["url"] = url
    if page is not None:
        d["page"] = page
    if note:
        d["note"] = note
    return d


def cents_round(x):
    return round(x + 1e-9, 2)


# =====================================================================================================
# PARKS
# =====================================================================================================
BOOK = "Chicago Park District 2026 Budget Appropriations"
BOOK_URL = "https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf"
ACFR = "Chicago Park District FY2025 ACFR"
ACFR_URL = "https://files.chicagoparkdistrict.com/2026-07/Chicago%20Park%20District_25%20ACFR_Final.pdf"
PEN_ACFR = "Park Employees' and Retirement Board Employees' Annuity and Benefit Fund, FY2025 annual report"
PEN_VAL = "Segal actuarial valuation of the Park Employees' Annuity and Benefit Fund as of 12/31/2025"
PEN_URL = ("https://www.chicagoparkpension.org/wp-content/uploads/2026/06/"
           "Park-Employees-Annuity-and-Benefit-Fund-of-Chicago_Actuarial-Valuation-Report-as-of-12.31.2025.pdf")


def parks_splits():
    out = []
    parks = json.load(open(P("data/parks_2026.json")))
    ser_rows = parks["beyond_operating"]["debt"]["ordinance_appropriation_M_by_bond_series_2026"]["rows"]

    # ---------------------------------------------------------------- Soldier Field (side only)
    out.append({
        "target": {"by": "id", "id": "parks.managed-venues.626045"},
        "expect_amount": 36292135,
        "mode": "side_only",
        "note": ("The budget book says Soldier Field is projected at $62.9 million of gross revenue and $36.3 million of "
                 "gross expenses in 2026, so this line is the expense side of the stadium. The District publishes no list "
                 "of what the operator spends it on. The operator (SMG, now ASM Global) was approved by the Board on "
                 "2013-02-13 for ten years at a management fee of $600,000 to $684,000 a year (press report), which would be "
                 "under 2 percent of this line. The budget also has a separate account, 623095 Management Contract "
                 "Incentive Fee ($1,183,983 in 2026, Revenue department), so some fees may sit outside this line. "
                 "The book does not say."),
        "side": [
            {"kind": "revenue_context", "label": "Soldier Field gross revenue budgeted for 2026 (account 420000, all sources)",
             "amount": 62899354, "period": "2026", "basis": "budget",
             "source": S(BOOK, BOOK_URL, "PDF p54 (printed 48) and narrative PDF p45")},
            {"kind": "revenue_context", "label": "of which event and stadium revenue (account 420005)", "amount": 48955346,
             "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "revenue_context", "label": "of which other income, mainly non-event parking (account 420015)",
             "amount": 6907552, "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "revenue_context", "label": "of which Bears and NFL contribution (account 420055)",
             "amount": 7036456, "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "revenue_context", "label": "Soldier Field revenue budgeted for 2025", "amount": 56838270,
             "period": "2025", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "prior_year_actual", "label": "Soldier Field revenue actually received in 2025 (General Fund)",
             "amount": 74567000, "period": "2025", "basis": "actual",
             "source": S(ACFR, ACFR_URL, "PDF p94 (budget versus actual, $ thousands: budget 56,838, actual 74,567)")},
            {"kind": "contract_term", "label": ("Bears lease (Permit and Operating Agreement): Bears pay an annual facility fee of "
                                                "$4,700,000 for 2004 to 2007, raised on each fifth anniversary of 1/1/2008 by "
                                                "50 percent of the cumulative inflation (CPI) since the last raise, plus a "
                                                "separate parking allotment fee. Term runs through the 2033 football season. "
                                                "The District pays routine maintenance and insurance."),
             "period": "2004-2033", "basis": "contract",
             "source": S("Chicago Bears lease summary, Marquette University Sports Law Library, sections 3.1, 14.1, 19.2, 27.1",
                         "https://law.marquette.edu/assets/sports-law/pdf/Chicago%20Bears%20Lease%20Summary.pdf", "1-3")},
            {"kind": "revenue_context", "label": "Rent received from the Bears in 2025 (facility fee plus parking allotment fee)",
             "amount": 7000000, "period": "2025", "basis": "actual",
             "source": S(ACFR, ACFR_URL, "PDF p78 (Note 9, lessor leases: 'the total amount of the inflows ... is $7.0 million')")},
            {"kind": "revenue_context", "label": "Rent received from the Chicago Fire soccer club in 2025 (lease ended 2025)",
             "amount": 3000000, "period": "2025", "basis": "actual",
             "source": S(ACFR, ACFR_URL, "PDF p78 (Note 9)")},
            {"kind": "contract_term", "label": ("Management agreement P-12035: Board of Commissioners approved a new 10-year SMG "
                                                "contract on 2013-02-13 covering Soldier Field and two other facilities "
                                                "(McFetridge and the Devon and Kedzie ballpark): management fee $600,000 to "
                                                "$684,000 a year, a $2.5 million contribution from SMG to the District and a "
                                                "$1 million marketing fund. The contract text is not on the District's Legistar "
                                                "site. The Bonfire contract library now lists the agreement as pending for "
                                                "2027-04-01 to 2028-03-31 with a stated value of $0."),
             "period": "2013-2028", "basis": "contract",
             "source": S("Chicago Tribune, 'Soldier Field management gets another contract', 2013-02-13",
                         "https://www.chicagotribune.com/2013/02/13/soldier-field-management-gets-another-contract/")},
            {"kind": "contract_term", "label": ("Soldier Field food service (separate contract P-23013, Levy Premium Foodservice, Board "
                                                "action 24-1058-0410): contractor puts in $12 million of capital at its own cost, "
                                                "3 percent of gross receipts goes to an equipment reserve, 1 percent of District "
                                                "concession sales goes to a community fund. Commissions to the District on concessions are "
                                                "48 percent of the first $13 million, 50 percent up to $20 million, 52 percent above. "
                                                "This is money the District receives, not part of this line."),
             "period": "2024-2029", "basis": "contract",
             "source": S("Exhibit A, Board matter 5896", "https://chicagoparkdistrict.legistar.com/")},
            {"kind": "context", "label": ("The 2025 audit says contractual services ran $7 million over budget mainly because Soldier "
                                           "Field revenue beat the plan and the extra events cost more to run. The expense line "
                                           "moves with the number of events (568 targeted for 2026, 386 in 2024)."),
             "period": "2025", "basis": "actual",
             "source": S(ACFR, ACFR_URL, "PDF p35; Revenue department performance table, budget PDF p94")},
            {"kind": "context", "label": "District spokesperson: Bears games are under 20 percent of the stadium's revenue",
             "period": "2026", "basis": "actual",
             "source": S("Block Club Chicago, 2026-02-23",
                         "https://blockclubchicago.org/2026/02/23/soldier-field-after-the-bears-park-district-pitches-plan-for-year-round-concert-venue/")},
        ],
    })

    # ---------------------------------------------------------------- Harbors (side only)
    out.append({
        "target": {"by": "id", "id": "parks.managed-venues.626040"},
        "expect_amount": 16580506,
        "mode": "side_only",
        "note": ("The budget book says harbor gross revenue is forecast at $31.5 million and gross expenses at $16.6 million, so "
                 "this line is the expense side of the harbor system. In addition, $10.6 million of 2026 debt service on bonds "
                 "backed by harbor revenue is paid from harbor income (it sits in the loan boxes, not here). The operator is "
                 "Westrec (2014 Board approval for 'management and operation of the Chicago Park District harbor system', "
                 "specification P-14010). No fee schedule or operating budget is published, and Legistar has only the "
                 "minority-business form for that approval."),
        "side": [
            {"kind": "revenue_context", "label": "Harbor fees budgeted for 2026 (account 417000: marine fees $31,488,599 plus other $38,508)",
             "amount": 31527107, "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "revenue_context", "label": "Harbor fees budgeted for 2025", "amount": 31247643, "period": "2025",
             "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "prior_year_actual", "label": "Harbor fees received in 2025, all funds", "amount": 31029000,
             "period": "2025", "basis": "actual", "source": S(ACFR, ACFR_URL, "PDF p50 ($ thousands: 31,029)")},
            {"kind": "debt_context", "label": "Harbor-backed bond payments in 2026 (paid from harbor revenue, shown under Paying back loans)",
             "amount": 10600000, "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "narrative PDF p46")},
            {"kind": "context", "label": ("10 harbors in the budget book, 11 in the ACFR, 4,679 boat slips and 715 mooring cans. "
                                           "Target harbor occupancy 86 percent in 2026."),
             "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p46 and p94; ACFR PDF p139")},
            {"kind": "contract_term", "label": ("Contract P-14010 (Westrec). Board approved 2014-11-12 (action 14-2148-1112). The Bonfire library "
                                                "shows P-14010 active May 2026 to April 2027. The 2026 harbor fee schedule is printed in the "
                                                "budget book and says 'Managed by Westrec SMI'."),
             "period": "2014-2027", "basis": "contract", "source": S(BOOK, BOOK_URL, "PDF p264; Legistar matter 3168")},
        ],
    })

    # ---------------------------------------------------------------- Golf (side only)
    out.append({
        "target": {"by": "id", "id": "parks.managed-venues.626050"},
        "expect_amount": 8490697,
        "mode": "side_only",
        "note": ("The budget book says golf gross revenue is $9.9 million and gross expenses $8.5 million in 2026, so this line "
                 "is the expense side of seven courses, three driving ranges, three learning centers and two mini-golf courses. "
                 "The contract fee is $1,275,000 a year, about 15 percent of the line. It is not shown whether that fee is "
                 "paid from this line or from account 623095 (Management Contract Incentive Fee). The rest is what the "
                 "operator spends running the courses, which the District does not itemise."),
        "side": [
            {"kind": "contract_term", "label": "Management fee in contract P-24001 (Indigo Sports, Troon), per year",
             "amount": 1275000, "period": "2025-2034", "basis": "contract",
             "source": S("Exhibit A, Board action 24-1125-0911 (2024-08-14), Legistar matter 5963",
                         "https://chicagoparkdistrict.legistar.com/")},
            {"kind": "contract_term", "label": "District holds back 10 percent of the fee ($127,500 a year) until a performance review",
             "amount": 127500, "period": "2025-2034", "basis": "contract", "source": S("Exhibit A, Board matter 5963")},
            {"kind": "contract_term", "label": ("Contractor capital at its own cost, $9,000,000 over 10 years: $3,575,000, $1,200,000, "
                                                "$1,700,000, $525,000, $1,250,000, $200,000, $150,000, $150,000, $150,000, $100,000. "
                                                "Plus $25,000 a year to a community youth fund."),
             "amount": 9000000, "period": "2025-2034", "basis": "contract", "source": S("Exhibit A, Board matter 5963")},
            {"kind": "revenue_context", "label": "Golf fees budgeted for 2026 (account 418000)", "amount": 9931373, "period": "2026",
             "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "revenue_context", "label": "Golf fees budgeted for 2025", "amount": 10134318, "period": "2025",
             "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p54")},
            {"kind": "prior_year_actual", "label": "Golf fees received in 2025 (General Fund)", "amount": 10535000,
             "period": "2025", "basis": "actual", "source": S(ACFR, ACFR_URL, "PDF p94 ($ thousands: 10,535)")},
            {"kind": "context", "label": ("Revenue management line 623095 'Management Contract Incentive Fee' is a separate account: "
                                           "$1,183,983 in 2026, $1,037,039 in 2025, $1,576,981 actual in 2024."),
             "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p94")},
        ],
    })

    # ---------------------------------------------------------------- Water and sewer (side only)
    out.append({
        "target": {"by": "id", "id": "parks.utilities-benefits-and-shared-costs.623000.623080"},
        "expect_amount": 16707439,
        "mode": "side_only",
        "note": ("No usage by park is published. The District does not post utility bills, the City's open data portal has "
                 "energy benchmarking (electricity and gas, no water) for only a few park buildings and none after 2020, "
                 "and the City's payments file lists no District water bills. The bill is the same $16,707,439 as in 2025. "
                 "The budget book says the District expects level water and sewer costs in 2026 after a multi-year City rate "
                 "increase that more than doubled them, and that the City added a water and sewer tax in 2017."),
        "side": [
            {"kind": "rate_context", "label": ("City water rate from 2026-06-01: $37.18 per 1,000 cubic feet (about $4.98 per 1,000 gallons), "
                                               "up 1.85 percent. The sewer charge is 100 percent of the water charge, added as a separate line, "
                                               "and a water-sewer tax is added on top."),
             "period": "2026", "basis": "actual",
             "source": S("City of Chicago Department of Finance, Water and Sewer Rates",
                         "https://www.chicago.gov/city/en/depts/fin/supp_info/utility-billing/water-and-sewer-rates.html")},
            {"kind": "context", "label": "All utilities together are budgeted at $37.6 million in 2026, 5.9 percent of the budget (water and sewer, electric, gas)",
             "amount": 37600000, "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p60 (printed 54)")},
        ],
    })

    # ---------------------------------------------------------------- Electric (side only)
    out.append({
        "target": {"by": "id", "id": "parks.utilities-benefits-and-shared-costs.623000.623075"},
        "expect_amount": 14805112,
        "mode": "side_only",
        "note": ("No usage by park is published. The budget book gives the change instead: electricity is up $823,000 from 2025 "
                 "(the two budget lines differ by $823,180) because of more data centers in the state and higher delivery rates. "
                 "A hedging plan saves about $1.5 million a year on the electricity commodity price, and the District buys "
                 "renewable energy credits equal to 100 percent of its electricity use."),
        "side": [
            {"kind": "context", "label": "Increase from the 2025 budget line ($13,981,932 to $14,805,112)", "amount": 823180,
             "period": "2026", "basis": "budget", "source": S(BOOK, BOOK_URL, "PDF p60 and account table PDF p62-63")},
            {"kind": "context", "label": "Hedging saves about $1.5 million a year on the electric commodity price", "amount": 1500000,
             "period": "2026", "basis": "gov_estimate", "source": S(BOOK, BOOK_URL, "PDF p60")},
            {"kind": "usage_context", "label": ("Only District building with published usage in the City's benchmarking data that is large enough "
                                                "to matter: Soldier Field used 108,529,613 kBtu of electricity and 16,899,451 kBtu of gas in 2015. "
                                                "No dollars and no later year."),
             "period": "2015", "basis": "actual",
             "source": S("City of Chicago Energy Benchmarking dataset xq83-jr8c, property 'Soldier Field'",
                         "https://data.cityofchicago.org/resource/xq83-jr8c")},
        ],
    })

    # ---------------------------------------------------------------- Pension shortfall (proxy split)
    # 2025 payments by type, Fund's own annual report (MD&A statement of changes, PDF p21). Same method as the
    # City pension funds: share the District's payment by each group's share of the benefit dollars.
    groups = [
        ("Pensions for retired workers (2,125 retirees)", 72365184, 2125, "retirees",
         "Retirement benefits paid in 2025. Retired members in pay status: 2,125, average annual benefit $34,793 "
         "(total in force $73,935,252)."),
        ("Pensions for surviving spouses (574 people)", 12368913, 574, "surviving spouses",
         "Spousal benefits paid in 2025. 574 surviving spouses, average annual benefit $20,655 (total in force $11,856,109)."),
        ("Benefits for children of workers who died (2 children)", 2200, 2, "children", "Child benefits paid in 2025."),
        ("Disability benefits", 341323, None, None,
         "Ordinary and duty disability benefits paid in 2025 ($308,705 and $32,618). The report gives no head count."),
        ("Death benefits", 180500, None, None, "Death benefits paid in 2025. The report gives no head count."),
        ("Refunds to workers who left", 2267404, None, None,
         "Refunds of employee contributions paid in 2025. 5,530 inactive members are owed a refund, "
         "but the report does not say how many were paid."),
    ]
    tot = sum(g[1] for g in groups)
    assert tot == 87525524, tot  # equals "Total Benefit payments and refunds" in the Segal valuation Exhibit F
    line = 53913236.00
    amts = [round(line * g[1] / tot, 2) for g in groups]
    amts[0] = round(amts[0] + (line - sum(amts)), 2)   # cents of rounding go to the largest group
    assert abs(sum(amts) - line) < 0.005
    pieces = []
    for g, a in zip(groups, amts):
        share = g[1] / tot
        p = {"name": g[0], "amount": a, "basis": "proxy", "kind": "benefit_group",
             "source": S(PEN_ACFR, "https://www.chicagoparkpension.org/about-us/annual-reports/", "PDF p21, p153-158; valuation Exhibits A, E, F",
                         "Benefits paid 2025 by type; total $87,525,524 equals Exhibit F of the Segal valuation."),
             "note": (f"Proxy: this group received ${g[1]:,} of the ${tot:,} the fund paid out in 2025 ({share:.2%}), so it gets "
                      f"{share:.2%} of the District's payment. {g[4]} The District's payment is not the same as the benefits paid. "
                      "The District sends one payment set by law, and the fund pays its people from that money plus member "
                      "contributions and investment earnings. This shares the payment by benefit dollars, so it is our "
                      "estimate, not a District figure."),
             "why": ("The District's payment goes to the fund as one lump sum and the fund pays about 2,700 people from it, so no single "
                     "person's pension is bought by one District payment.")}
        if g[2]:
            p["count"] = g[2]
            p["unit_amount"] = round(a / g[2], 2)
            p["unit_label"] = f"{g[3]} (share of the District's payment each)"
        pieces.append(p)
    out.append({
        "target": {"by": "id", "id": "parks.retirement-pensions.regular-yearly-payment.other-not-itemised"},
        "expect_amount": 53913236,
        "mode": "budget_split",
        "pieces": pieces,
        "note": ("Split by who the Park Employees' fund pays (2025 benefit dollars by group). The first group alone is about 83 "
                 "percent. Administrative costs ($1,976,961 in 2025) are not benefits and are left out of the shares."),
        "side": [
            {"kind": "benefits_paid", "label": "Total benefits and refunds the fund paid in 2025 (retirement $72,365,184, spousal $12,368,913, child $2,200, disability $341,323, death $180,500, refunds $2,267,404)",
             "amount": 87525524, "period": "2025", "basis": "actual", "source": S(PEN_ACFR, None, "PDF p21")},
            {"kind": "retirees", "label": "Members at 12/31/2025: 2,125 retirees, 574 surviving spouses, 2 children, 206 inactive with vested rights, 3,251 active (average pay $58,371), 5,530 inactive owed a refund",
             "period": "12/31/2025", "basis": "actual", "source": S(PEN_VAL, PEN_URL, "Exhibits A and D (PDF pp34-37)")},
            {"kind": "statute_context", "label": ("Statute P.A. 102-0263 sets the employer payment (normal cost plus a 32-year closed payoff of the "
                                                  "unfunded liability) and aims for 100 percent funded by 2057. The fund's own policy asks "
                                                  "for $88,904,199 in 2026, which is $25,571,787 more than the $63,332,412 budgeted."),
             "amount": 25571787, "period": "2026", "basis": "gov_estimate", "source": S(PEN_VAL, PEN_URL, "Section 1 (PDF p10) and Exhibit I")},
        ],
    })

    # ---------------------------------------------------------------- Bonds: principal and interest, plus facts
    acfr_rows = parse_acfr_bonds()
    n_split = 0
    for r in ser_rows:
        m = re.search(r"Series (\d{4}[A-Z](?:-\d)?)", r["name"])
        if not m:
            continue
        s = m.group(1)
        total = r["total"]
        if total == 0:
            continue
        ident = "parks.paying-back-loans." + s.lower()
        side = []
        a = acfr_rows.get(s)
        if a:
            side.append({"kind": "debt_context",
                         "label": (f"Bond facts at 12/31/2025: original ${a['orig']:,} thousand, still owed ${a['out']:,} thousand, "
                                   f"interest rate {a['rate']}, years of payment {a['years']}"),
                         "amount": a["out"] * 1000, "period": "12/31/2025", "basis": "actual",
                         "source": S(ACFR, ACFR_URL, "PDF p77 (Note 8, debt table)")})
        elif s in ("2016B",):
            side.append({"kind": "debt_context",
                         "label": "Fully refunded in December 2025 by Series 2025B. The ACFR shows no balance outstanding.",
                         "period": "12/31/2025", "basis": "actual", "source": S(ACFR, ACFR_URL, "PDF p76-77")})
        if r["principal"] > 0 and r["interest"] > 0:
            pcs = [
                {"name": "Paying back the loan itself (principal)", "amount": r["principal"], "basis": "tied", "kind": "bond_part",
                 "why": ("This is the part of one bond's yearly payment that repays the money borrowed, and the bond contract fixes it.")
                 if r["principal"] >= 10_000_000 else None},
                {"name": "Interest (what lenders charge)", "amount": r["interest"], "basis": "tied", "kind": "bond_part",
                 "why": ("This is the interest the bond contract charges for one year, so it cannot be split further.")
                 if r["interest"] >= 10_000_000 else None},
            ]
            for p in pcs:
                p["source"] = S(BOOK + ", ordinance Appropriation M", BOOK_URL, "PDF p253 (printed 247)")
            out.append({"target": {"by": "id", "id": ident}, "expect_amount": total, "mode": "budget_split",
                        "pieces": pcs, "side": side})
            n_split += 1
        elif side:
            out.append({"target": {"by": "id", "id": ident}, "expect_amount": total, "mode": "side_only", "side": side})
    print(f"parks: {n_split} bond series split into principal and interest")
    return out


def parse_acfr_bonds():
    path = P("raw/parks/acfr25_text.json")
    if not os.path.exists(path):
        print("  note: raw/parks/acfr25_text.json missing, bond facts skipped")
        return {}
    t = json.load(open(path))["77"]
    rows = {}
    for ln in t.split("\n"):
        m = re.search(r"Series (\d{4}[A-Z](?:-\d)?)\b(?: \(Taxable\))?\s*-\s*([\d.]+%(?:\s*(?:to|-)\s*[\d.]+%)?)", ln)
        if not m:
            continue
        rest = ln[m.end():]
        nums = re.findall(r"\d[\d,]*", re.sub(r"\*", " ", rest))
        yrs = re.findall(r"\b(20\d\d)\b", rest)
        if len(nums) < 2 or not yrs:
            continue
        orig, out_ = (int(x.replace(",", "")) for x in nums[-2:])
        years = yrs[0] if len(set(yrs[:2])) == 1 or len(yrs) == 1 else f"{yrs[0]} to {yrs[1]}"
        rows[m.group(1)] = {"rate": m.group(2).replace("  ", " "), "years": years, "orig": orig, "out": out_}
    return rows


# =====================================================================================================
# CITY
# =====================================================================================================
def num(x):
    if x is None:
        return 0.0
    if isinstance(x, (int, float)):
        return float(x)
    s = str(x).replace("\xa0", " ")
    neg = "(" in s and ")" in s
    s = re.sub(r"[^0-9.]", "", s)
    if not s:
        return 0.0
    return -float(s) if neg else float(s)


def load_js():
    import openpyxl
    path = fetch(JS_URL, os.path.join(RAW, "js_2026.xlsx"))
    import warnings
    warnings.filterwarnings("ignore")
    ws = openpyxl.load_workbook(path, data_only=True)["A"]
    rows = list(ws.iter_rows(values_only=True))
    hdr = next(i for i, r in enumerate(rows) if r[0] == "CASE #")
    end = next(i for i, r in enumerate(rows) if r[1] == "TOTAL GLOBAL WATTS SETTLEMENT")
    recs = []
    for i in range(hdr + 1, end):
        r = rows[i]
        if all(x is None for x in r[:9]):
            continue
        c, f = num(r[2]), num(r[3])
        if c == 0 and f == 0:
            continue
        recs.append({"row": i + 1, "amt": c, "fee": f, "cause": (r[4] or "").strip().upper(),
                     "dept": (r[5] or "").strip().upper(), "disp": (r[6] or "").strip().upper(),
                     "cof": r[8].date().isoformat() if hasattr(r[8], "date") else None})
    return recs, rows[end][2]   # second value: the sheet's own (understated) Watts total


def bucket(recs, rules, other_name):
    """rules: list of (name, predicate on cause). Returns ordered dict name -> [n, dollars], 'other' last."""
    out = collections.OrderedDict((n, [0, 0.0]) for n, _ in rules)
    out[other_name] = [0, 0.0]
    for r in recs:
        for n, pred in rules:
            if pred(r["cause"]):
                out[n][0] += 1
                out[n][1] += r["amt"] + r["fee"]
                break
        else:
            out[other_name][0] += 1
            out[other_name][1] += r["amt"] + r["fee"]
    return out


JS_SRC = S("City of Chicago Law Department, Judgment/Verdict and Settlement Report, 2026 expenditures through 2026-07-31 (unaudited)",
           JS_PAGE, "sheet A, summed by department and primary cause")
JS_CAVEAT = ("Payments are authorized payment requests from the Law Department to the Comptroller from 2026-01-02 to 2026-07-31, "
             "unaudited, and may change after reconciliation. The report names no fund or account, so a payment is placed here by "
             "its department only. ")


def pieces_from(buckets, why_by_name, desc_by_name, src=JS_SRC, big=10_000_000):
    pcs = []
    for n, (cnt, dollars) in buckets.items():
        if cnt == 0:
            continue
        d = cents_round(dollars)
        p = {"name": n, "amount": d, "basis": "paid_to_date", "kind": "settlement_group", "source": src,
             "note": f"{cnt} payment{'s' if cnt != 1 else ''}. {desc_by_name.get(n, '')}".strip()}
        if d >= big:
            p["why"] = why_by_name[n]
        pcs.append(p)
    return pcs


def city_splits():
    out = []
    recs, sheet_watts_total = load_js()
    watts_rows = [r for r in recs if r["cof"] == "2025-09-15" and r["cause"] == "REVERSED CONVICTION" and r["dept"] == "POLICE"]
    watts = cents_round(sum(r["amt"] + r["fee"] for r in watts_rows))
    assert abs(watts - 90_000_000.00) < 0.02, watts   # the Council approved exactly $90 million on 2025-09-15
    print(f"city: Watts block {len(watts_rows)} payments, ${watts:,.2f} (sheet's own total says ${sheet_watts_total:,.2f})")
    rest = [r for r in recs if r not in watts_rows]

    police = [r for r in rest if r["dept"] == "POLICE"]
    fire = [r for r in rest if r["dept"] == "FIRE"]
    water = [r for r in rest if r["dept"] == "WATER MGMT / WATER"]
    sewer = [r for r in rest if r["dept"] == "WATER MGMT / SEWER"]
    excl = {"POLICE", "FIRE", "WATER MGMT / WATER", "WATER MGMT / SEWER", "DEPT OF WATER", "AVIATION"}
    other = [r for r in rest if r["dept"] not in excl]
    unplaced = [r for r in rest if r["dept"] in ("DEPT OF WATER", "AVIATION")]

    # ------------------------------------------------ police
    pol_rules = [
        ("Wrongful conviction settlements, other than Watts (10 payments)", lambda c: c == "REVERSED CONVICTION"),
        ("Police vehicle chase crashes", lambda c: c.startswith("PURSUIT")),
        ("Lawsuits over police conduct and jobs (force, arrests, searches, discrimination, whistleblower)",
         lambda c: any(k in c for k in ("EXCESSIVE FORCE", "FALSE ARREST", "ILLEGAL SEARCH", "EXTENDED DETENTION",
                                        "OTHER POLICE MISCONDUCT", "WHISTLEBLOWER", "DISCRIMINATION", "CPDPP"))),
        ("Crashes and property damage involving police", lambda c: any(k in c for k in (
            "MVA", "VCCV", "VEHICLE COLLISION", "PROPERTY DAMAGE", "PDSC", "FIRETR", "ALLISION", "BICYCLE", "FALL DOWN"))),
    ]
    pol_other = "Union awards, public records lawsuits and small items"
    pb = bucket(police, pol_rules, pol_other)
    pb_all = collections.OrderedDict()
    pb_all["Watts global settlement (176 lawsuits, approved by the Council 2025-09-15)"] = [len(watts_rows), watts]
    pb_all.update(pb)
    why_pol = {
        "Watts global settlement (176 lawsuits, approved by the Council 2025-09-15)":
            "This is one court-approved deal that settled hundreds of lawsuits about one former sergeant, so there is no smaller bill to show.",
        "Wrongful conviction settlements, other than Watts (10 payments)":
            "These are a few very large payments to people whose convictions were overturned, and each was a separate court deal.",
        "Police vehicle chase crashes":
            "These are a few very large settlements for crashes during police chases, and each was a separate court deal.",
    }
    desc_pol = {
        pol_other: "Includes arbitration awards, public records (FOIA) lawsuits and discipline cases, mostly lawyers' fees and costs.",
        "Wrongful conviction settlements, other than Watts (10 payments)": "People are not named here. Each case closed with its own settlement.",
        "Watts global settlement (176 lawsuits, approved by the Council 2025-09-15)": (
            "Payments (including $10,389,123 of lawyers' fees and costs) were sent to the Comptroller in January and February 2026 for "
            "settlements the Council approved on 2025-09-15. The report's own 'Total Global Watts Settlement' cell shows $85,402,413 "
            "because 22 amounts in the sheet are typed as text. Adding them back gives exactly $90,000,000, the amount the Council approved."),
    }
    pol_total = sum(v[1] for v in pb_all.values())
    cpd_why = ("This pays legal claims and court judgments as they are settled during the year.")
    out.append({
        "target": {"by": "ordinance_line", "fund": "0100", "dept": "57", "authority": "1005", "account": "0931"},
        "expect_amount": 82558000,
        "mode": "paid_to_date",
        "pieces": pieces_from(pb_all, why_pol, desc_pol),
        "over": {"name": "Paid beyond the budget line (the City plans to borrow for settlements)",
                 "note": ("Settlement payments so far in 2026 are larger than the full-year budget line. This negative box keeps the boxes "
                          "adding up to the budget. The 2026 Budget Overview says amounts above the budgeted resources will be financed "
                          "and repaid over five years, and the Civic Federation says the budget uses debt to cover police settlements. "
                          "The report does not say which fund or bond issue pays each item. " + JS_CAVEAT)},
        "note": JS_CAVEAT + ("All Police Department payments in the report are placed here, including $90,000,000 for the Watts "
                             "global settlement. The line also pays outside lawyers and experts, which are not in this report."),
        "side": [
            {"kind": "prior_year_budget", "label": "2025 budget line", "amount": 82558000, "period": "2025", "basis": "budget",
             "source": S("City of Chicago 2025 ACFR, budgetary comparison, Police 1005.0931",
                         "https://www.chicago.gov/city/en/depts/fin/supp_info/comprehensive_annualfinancialstatements/2025-financial-statements.html", "PDF p148")},
            {"kind": "prior_year_actual", "label": "Actually spent on this line in 2025 (budget was $82,558,000)", "amount": 131088495,
             "period": "2025", "basis": "actual", "source": S("City of Chicago 2025 ACFR, budgetary comparison", None, "PDF p148")},
            {"kind": "context", "label": ("Police lawsuits that closed in 2025 cost $258,956,775 (Law Department counting rules, cases closed in 2025): 15 wrongful "
                                           "conviction cases $193,344,242, 9 vehicle pursuit cases $54,378,000, 20 use-of-force cases $1,844,207. "
                                           "On top, 184 Watts cases for $101,300,000 (Appendix C). Outside lawyers were paid $36,081,683 in 2025."),
             "amount": 258956775.56, "period": "2025", "basis": "actual",
             "source": S("Law Department, Report on 2025 CPD Litigation (2026-06-30)",
                         "https://www.chicago.gov/content/dam/city/depts/dol/CPDLitigationReports/2025/2025%20Annual%20Litigation%20Report%206.30.26.pdf")},
            {"kind": "context", "label": ("Not yet in the numbers above: a proposed $260.8 million global settlement for 16 lawsuits tied to a former "
                                           "detective was on the Finance Committee agenda for Monday 2026-10-05. It is a proposal, not a payment."),
             "amount": 260800000, "period": "2026", "basis": "gov_estimate",
             "source": S("Chicago Sun-Times, 2026-10-01",
                         "https://chicago.suntimes.com/city-hall/2026/10/01/brandon-johnson-proposed-global-settlement-police-misconduct-cases-ex-cpd-det-reynaldo-guevara")},
        ],
    })

    # ------------------------------------------------ fire
    fire_rules = [
        ("Paramedic malpractice lawsuits", lambda c: "PARAMEDIC" in c),
        ("Crashes involving fire vehicles", lambda c: any(k in c for k in ("VEHICLE COLLISION", "MVA", "FIRETR", "PROPERTY DAMAGE", "COLLISON"))),
        ("Discrimination and harassment cases (mostly lawyers' fees)", lambda c: any(k in c for k in ("DISCRIMINATION", "HARRASSMENT", "ADA "))),
    ]
    fb = bucket(fire, fire_rules, "Union awards, discipline cases and small items")
    out.append({
        "target": {"by": "ordinance_line", "fund": "0100", "dept": "59", "authority": "2005", "account": "0931"},
        "expect_amount": 12000000,
        "mode": "paid_to_date",
        "pieces": pieces_from(fb, {}, {"Discrimination and harassment cases (mostly lawyers' fees)":
                                       "Includes $1,015,666 of fees and costs awarded to one case's lawyers."}),
        "note": JS_CAVEAT + "All Fire Department payments in the report are placed here.",
        "side": [
            {"kind": "prior_year_actual", "label": "Actually spent on this line in 2025 (budget was $12,000,000)", "amount": 14828284,
             "period": "2025", "basis": "actual", "source": S("City of Chicago 2025 ACFR, budgetary comparison, Fire 2005.0931", None, "PDF p149")},
        ],
    })

    # ------------------------------------------------ other departments (Finance General, Corporate Fund)
    def oth_rule(sub):
        return lambda c: any(k in c for k in sub)
    ob = bucket(other, [
        ("Trips and falls on sidewalks, curbs and streets", oth_rule(("FALL DOWN",))),
        ("Crashes and road-condition claims", oth_rule(("MVA", "BICYCLE", "BA/", "VEHICLE", "PDSC", "ALLISION", "COLLISION"))),
        ("Property damage, including wrongful demolition", oth_rule(("PROPERTY DAMAGE",))),
    ], "Other claims, verdicts and lawyers' fees")
    out.append({
        "target": {"by": "ordinance_line", "fund": "0100", "dept": "99", "authority": "2005", "account": "0931"},
        "expect_amount": 40785387,
        "mode": "paid_to_date",
        "pieces": pieces_from(ob, {}, {}),
        "note": JS_CAVEAT + ("All payments for departments other than Police, Fire, Water Management and Aviation are placed here "
                             f"(Transportation is most of it). {len(unplaced)} small Aviation and 'Department of Water' payments are left out because "
                             "their lines are in other funds."),
        "side": [
            {"kind": "prior_year_actual", "label": "Actually spent on this line in 2025 (2025 budget was $44,358,000)", "amount": 38906432,
             "period": "2025", "basis": "actual", "source": S("City of Chicago 2025 ACFR, budgetary comparison, Finance General 2005.0931", None, "PDF p146")},
        ],
    })

    # ------------------------------------------------ water and sewer funds (tiny)
    for fund, dept_rows, amt, label in (("0200", water, 6800000, "Water Management (water)"),
                                        ("0314", sewer, 383133, "Water Management (sewer)")):
        d = cents_round(sum(r["amt"] + r["fee"] for r in dept_rows))
        if not dept_rows:
            continue
        out.append({
            "target": {"by": "ordinance_line", "fund": fund, "dept": "99", "authority": "2005", "account": "0931"},
            "expect_amount": amt, "mode": "paid_to_date",
            "pieces": [{"name": f"Claims paid for {label}", "amount": d, "basis": "paid_to_date", "kind": "settlement_group",
                        "source": JS_SRC, "note": f"{len(dept_rows)} payments. " + JS_CAVEAT}],
        })

    # ------------------------------------------------ Emergency Medical Transportation (9222): side only
    emt_src_b = S("City of Chicago 2026 Budget Recommendations", "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Recommendation%20Book.pdf", "PDF p573 (Finance General, account 9222)")
    hist = [("2020", 143000000, "fyin-2vyd"), ("2021", 77400000, "6tbx-h7y2"), ("2022", 77400000, "2cr6-8u6w"),
            ("2023", 96000000, "xbjh-7zvh"), ("2024", 125000000, "x394-e874"), ("2025", 127642689, "t59y-fr3k")]
    side = [{"kind": "prior_year_budget", "label": f"Appropriation for this line in the {y} ordinance (dataset {ds})", "amount": a,
             "period": y, "basis": "budget", "source": S(f"City of Chicago {y} Budget Ordinance - Appropriations, Finance General 9222",
                                                       f"https://data.cityofchicago.org/resource/{ds}")} for y, a, ds in hist]
    side += [
        {"kind": "prior_year_actual", "label": "Spent on this line in 2024", "amount": 116996954, "period": "2024", "basis": "actual", "source": emt_src_b},
        {"kind": "prior_year_actual", "label": "Spent on this line in 2025 (budget was $127,642,689)", "amount": 115267967, "period": "2025",
         "basis": "actual", "source": S("City of Chicago 2025 ACFR, budgetary comparison, Finance General 2005.9222", None, "PDF p147")},
        {"kind": "vendor_context", "label": ("The ambulance billing company, Advanced Data Processing, was paid $7,713,575 in 2025 (24 payments) and $2,780,182 in "
                                              "2026 through 9/28 (12 payments) on contract 54815, under the Department of Finance. Those payments are not "
                                              "in this line (this line is Finance General), and they equal about 6 percent of it."),
         "amount": 7713574.58, "period": "2025", "basis": "actual",
         "source": S("City payments data (contracts 54815)", "https://webapps1.chicago.gov/vcsearch/city/contracts/54815")},
        {"kind": "contract_term", "label": ("Billing contract 54815 (Part A EMS billing and collection, Part B patient tracking and electronic patient care reports): "
                                              "awarded 2018-04-13 for up to $17,572,176 over five years, extended by modifications to 2026-04-10, then to 2026-10-08. "
                                              "At award the fee was 3.95 percent of collections (2.7 percent base plus 1.25 percent compliance), down from 7 percent."),
         "period": "2018-2026", "basis": "contract",
         "source": S("City contract search, contract 54815; Chicago Sun-Times 2018-04-16",
                     "https://chicago.suntimes.com/2018/4/16/18406121/city-awards-17-5m-ambulance-fee-collection-contract-to-reverse-33-year-struggle")},
        {"kind": "context", "label": ("City statement: 2025 'local non-tax revenues are expected to underperform ... primarily due to ... lower "
                                       "reimbursements from the federally funded Ground Emergency Medical Transportation (GEMT) program, which provides "
                                       "supplemental Medicaid reimbursement for ambulance services.'"),
         "period": "2025", "basis": "gov_estimate", "source": S("City of Chicago 2026 Budget Forecast", None, "PDF p21")},
        {"kind": "context", "label": ("City statement, July 2026: Charges for Service are $34.3 million (16.0 percent) below budget 'mainly due to "
                                       "lower-than-expected Medicaid reimbursements for Emergency Medical Transport services'."),
         "amount": 34300000, "period": "2026", "basis": "actual",
         "source": S("City of Chicago Monthly Revenue Report, July 2026",
                     "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/RevenueReports/2026/Monthly_Revenue_Report_July_2026.pdf")},
        {"kind": "context", "label": ("The State's agreement for the GEMT program requires the local government to send the State 50 percent of the "
                                       "supplemental ambulance payments it receives, invoiced each quarter. Chicago joined in 2020 (DoltHub analysis)."),
         "period": "2025", "basis": "contract",
         "source": S("Illinois HFS GEMT intergovernmental agreement, 2025 form, Article II",
                     "https://hfs.illinois.gov/content/dam/soi/en/web/hfs/medicalproviders/costreports/transportation/2025%20GEMT%20IGA.pdf", "2")},
    ]
    out.append({
        "target": {"by": "ordinance_line", "fund": "0100", "dept": "99", "authority": "2005", "account": "9222"},
        "expect_amount": 124725187,
        "mode": "side_only",
        "note": ("What this line is: the City's budget documents do not say. It is a Finance General line, not part of the Fire "
                 "Department, and it is about 16 times what the ambulance billing company was paid in 2025, so it is not a billing "
                 "contract. It grew from $77.4 million (2021 and 2022) to about $125 million (2024 to 2026) after Chicago joined the Illinois "
                 "ambulance supplement (GEMT) program in 2020. Under that program the City must send the State half of the extra Medicaid "
                 "money. That fits this line, but no City document confirms it, so treat it as our reading and ask the Office of Budget "
                 "and Management. The budget book does not split the line, and the City says it is spent as ambulance-related payments "
                 "'as specified'."),
        "side": side,
    })

    # ------------------------------------------------ CTA share of the real property transfer tax (side only)
    cta_src = S("City of Chicago Department of Finance, Real Property Transfer Tax (7551)",
                "https://www.chicago.gov/city/en/depts/fin/supp_info/revenue/tax_list/real_property_transfertax.html")
    cta_bud = "https://www.transitchicago.com/assets/1/6/FY2026_-_Accessible_Text_Budget_Book.pdf"
    out.append({
        "target": {"by": "ordinance_line", "fund": "0B09", "dept": "99", "authority": "2005", "account": "9205"},
        "expect_amount": 62789053,
        "mode": "side_only",
        "note": ("One pass-through, so there is nothing to split. Since 2008-04-01 the City adds $1.50 for every $500 of a property's "
                 "sale price ('CTA portion') on top of its own $3.75 ('City portion'), $5.25 in all. The seller pays the CTA portion "
                 "by default. The City collects it, keeps $634,233 to cover collection costs, and sends the rest to the CTA, "
                 "which uses it in its operating budget."),
        "side": [
            {"kind": "rate_context", "label": "Tax rate: $1.50 per $500 of transfer price for the CTA portion (City portion $3.75, total $5.25)",
             "period": "2026", "basis": "actual", "source": cta_src},
            {"kind": "revenue_context", "label": "City's 2026 revenue estimate for the CTA Real Property Transfer Tax Fund (this line plus $634,233 collection cost)",
             "amount": 63423286, "period": "2026", "basis": "budget", "source": S("City of Chicago 2026 Budget Recommendations, revenue", None, None)},
            {"kind": "revenue_context", "label": "What the CTA's own budget book expects from the transfer tax in 2026 (a different, higher number than the City's)",
             "amount": 67043000, "period": "2026", "basis": "gov_estimate", "source": S("CTA FY2026 budget book", cta_bud, "PDF pp60, 62")},
            {"kind": "revenue_context", "label": "CTA forecast of the transfer tax for 2025", "amount": 65091000, "period": "2025", "basis": "gov_estimate",
             "source": S("CTA FY2026 budget book", cta_bud, "PDF p60")},
            {"kind": "prior_year_actual", "label": "Sent to the CTA in 2025 (appropriation $58,728,050)", "amount": 58728049, "period": "2025",
             "basis": "actual", "source": S("City of Chicago 2025 ACFR, budgetary comparison, CTA Real Property Transfer Tax Fund", None, "PDF p187")},
            {"kind": "context", "label": ("How the CTA uses it: the CTA receives 100 percent of the $1.50 increase as public funding for operations. "
                                           "The transfer tax receipts, which the City remits directly to the CTA, also back the 2008A and 2008B Sales and "
                                           "Transfer Tax Receipts Revenue Bonds ($1.94 billion issued for the pension and retiree health care funds). "
                                           "Debt service on them is $156,574,793 in 2026 and is paid in the CTA operating budget."),
             "amount": 156574793, "period": "2026", "basis": "gov_estimate", "source": S("CTA FY2026 budget book", cta_bud, "PDF pp116-117, 144")},
            {"kind": "context", "label": ("Separate from this line: the State adds 25 percent on top of the transfer tax receipts through the Public "
                                           "Transportation Fund ($17,246,000 for the CTA in 2026), and buyers age 65 or older can get the CTA portion refunded "
                                           "on homes of $250,000 or less."),
             "amount": 17246000, "period": "2026", "basis": "gov_estimate", "source": S("CTA FY2026 budget book; City Finance page", cta_bud, "PDF p61")},
            {"kind": "context", "label": "All City real property transfer tax receipts through July 2026 were 14.2 percent ($12.7 million) above budget",
             "amount": 12700000, "period": "2026", "basis": "actual",
             "source": S("City of Chicago Monthly Revenue Report, July 2026",
                         "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/RevenueReports/2026/Monthly_Revenue_Report_July_2026.pdf")},
        ],
    })
    totals = {"police_nonwatts": sum(v[1] for v in pb.values()), "fire": sum(v[1] for v in fb.values()),
              "other": sum(v[1] for v in ob.values()), "unplaced": sum(r["amt"] + r["fee"] for r in unplaced)}
    print("city: payments placed:", {k: f"{v:,.2f}" for k, v in totals.items()}, "police total incl Watts", f"{pol_total:,.2f}")
    return out


# =====================================================================================================
def write(path, author, desc, splits):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    doc = {"meta": {"author": "parks and misc detail agent", "description": desc, "built_by": "scripts/parksmisc_build.py"},
           "splits": splits}
    with open(path, "w") as f:
        json.dump(doc, f, indent=1)
    print(f"wrote {os.path.relpath(path, ROOT)}: {len(splits)} splits")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    if which in ("parks", "all"):
        write(P("data/splits/parks/misc.json"), "", "Soldier Field, harbors, golf, utilities (side facts), Park pension benefit groups, "
              "bond series principal and interest.", parks_splits())
    if which in ("city", "all"):
        write(P("data/splits/city/misc.json"), "", "Emergency Medical Transportation, CTA transfer tax share, and judgments and "
              "settlements paid so far in 2026.", city_splits())
