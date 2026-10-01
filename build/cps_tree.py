"""Build the Chicago Public Schools FY2026 budget tree.

Base: raw/cps/cps_2026_exp_unit_fund_program_account.csv (159,589 rows, $10,253,327,463.68),
with the unit, account, fund and program dimension files for labels and hierarchy.
All amounts are integer cents. Rows are rounded to cents with the largest-remainder method so the
whole tree ties to the printed total to the cent (the source has sub-cent fractions).

Top of tree (organised by what the money is for):
  Chicago Public Schools
    Schools                         district-run schools (network > school), charter and contract schools
                                    each school: spending type > account > (job title | big fund lines)
    Central and network offices     area > department > spending type > account
    Citywide programs               special education, buses, meals, buildings, preschool, safety...
    Teacher pensions and insurance  one unit (U12470), by fund x program x account line
    Paying back loans               bond series (one leaf each, data/cps_debt_by_series_fy26.csv)
    Building projects               capital funds, 131 projects (data/cps_capital_projects_fy26.csv)

Splits use treelib.split() only: salary lines by job title (positions x budgeted salary),
pension levy, hospitalization reserve, special-ed buses and facility management (data/leaves_cps.json).
Fund and program are collapsed into extra (money_comes_from, program_areas) instead of nodes, except
for lines of $1M or more inside accounts of $10M or more, which stay visible.

Side info (never in amounts): FY2024 actual and FY2025 projected spending per unit, FY2026 vendor
payments (vendor level, not tied to budget lines) and 2024-25 school enrollment.

No employee names are used. Job titles are aggregated per unit and titles with fewer than 5
positions show the total only (no per-position average).

Run: python3 build/cps_tree.py   (exit 1 if any check fails)
"""
import json
import os
import re
import sqlite3
import sys
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

import pandas as pd

sys.path.insert(0, os.path.dirname(__file__))
from treelib import (Node, cents, check, depth_report, split, save_json, to_rows,  # noqa: E402
                     side_rows, load_into_db, slug)

ROOT_DIR = os.path.join(os.path.dirname(__file__), "..")
P = lambda *a: os.path.join(ROOT_DIR, *a)  # noqa: E731

EXPECTED = 1025332746368          # $10,253,327,463.68
ONE_M = 1_000_000_00
TEN_M = 10_000_000_00
problems = []


def D(name):
    with open(P("data", name)) as f:
        return json.load(f)


# ------------------------------------------------------------------ load
fact = pd.read_csv(P("raw/cps/cps_2026_exp_unit_fund_program_account.csv"), dtype=str)
dim_unit = pd.read_csv(P("raw/cps/cps_2026_dim_unit.csv"), dtype=str).set_index("Unit")
dim_acct = pd.read_csv(P("raw/cps/cps_2026_dim_account.csv"), dtype=str).set_index("Account")
dim_fund = pd.read_csv(P("raw/cps/cps_2026_dim_fund.csv"), dtype=str).set_index("Fund Grant")
dim_prog = pd.read_csv(P("raw/cps/cps_2026_dim_program.csv"), dtype=str).set_index("Program")
positions = pd.read_csv(P("raw/cps/cps_2026_positions_unit_job.csv"))
charter = pd.read_csv(P("data/cps_charter_by_school_fy26.csv"))
debt = pd.read_csv(P("data/cps_debt_by_series_fy26.csv"))
pens = pd.read_csv(P("data/cps_pension_insurance_fy26.csv"))
capital = pd.read_csv(P("data/cps_capital_projects_fy26.csv"))
vendors = pd.read_csv(P("data/cps_supplier_payments_fy2026_over1m.csv"))
awards = pd.read_csv(P("data/cps_contract_awards_fy21_27.csv"))
leaves_cps = D("leaves_cps.json")
leaves10 = D("leaves_over_10m.json")

# ---- round every row to cents (half up), then spread the tiny leftover (a few cents) by largest remainder
vals = [Decimal(s) * 100 for s in fact["fy_new_budget"]]
rounded = [v.to_integral_value(rounding=ROUND_HALF_UP) for v in vals]
cents_col = [int(x) for x in rounded]
deficit = EXPECTED - sum(cents_col)
if abs(deficit) > 1000:
    print(f"FAILED: base rows cannot be rounded to the expected total (deficit {deficit} cents)")
    sys.exit(1)
if deficit != 0:
    sign = 1 if deficit > 0 else -1
    # rows rounded down (deficit > 0) with the biggest fractional part first, or rounded up with the smallest
    order = sorted(range(len(vals)), key=lambda i: (vals[i] - rounded[i]) * sign, reverse=True)
    for i in order[:abs(deficit)]:
        cents_col[i] += sign
fact["cents"] = cents_col
assert fact["cents"].sum() == EXPECTED
print(f"base rows: {len(fact):,}  total {EXPECTED / 100:,.2f}  (rounding allocation: {deficit} cents)")

# ---- dimension look-ups
unit_name = dim_unit["Unit Description"].to_dict()
acct_desc = dim_acct["Account Description"].to_dict()
acct_sub = dim_acct["Account SubGroup"].to_dict()
acct_l3 = dim_acct["Level 3 Account Description"].to_dict()
fund_desc = {k: re.sub(r"\s*-\s*FG\d.*$", "", v).strip() for k, v in dim_fund["Fund Grant Description"].fillna("").items()}
fund_parent = dim_fund["Parent Fund Description"].fillna("Other funds").to_dict()
fund_group = dim_fund["Fund Group"].to_dict()
prog_desc = dim_prog["Program Description"].to_dict()
prog_l1 = dim_prog["Level 1 Program Description"].fillna("Other").to_dict()

SRC_BASE = {"dataset": "CPS FY2026 approved budget, Oracle BI unit x fund x program x account",
            "doc": "CPS FY2026 Budget Book",
            "url": "https://www.cps.edu/about/finance/budget/budget-2026/",
            "file": "raw/cps/cps_2026_exp_unit_fund_program_account.csv",
            "note": "fiscal year July 2025 to June 2026"}


def S(x):
    """NaN-safe string for extras (JSON must never contain NaN)."""
    return x if isinstance(x, str) else None


def src(**kw):
    s = dict(SRC_BASE)
    s.update(kw)
    return s


root = Node("cps", "Chicago Public Schools", gov="cps", kind="government", basis="budget",
            source=src(), extra={"official_name": "Chicago Public Schools (Board of Education of the City of Chicago)",
                                 "fiscal_year": "FY2026 (July 2025 to June 2026)"})

# ------------------------------------------------------------------ names
KID_ACCT = {
    "A51100": "Regular teacher pay", "A51130": "Teacher extended-day pay",
    "A51140": "Teacher sick and vacation payouts", "A51500": "Substitute teacher pay",
    "A52100": "Regular staff pay (aides, clerks, custodians and more)",
    "A52130": "Staff extended-day pay", "A52140": "Other staff pay",
    "A52150": "Staff sick and vacation payouts", "A52400": "Staff overtime",
    "A52500": "Substitute staff pay",
    "A57105": "Teacher pension (employer share)", "A57110": "Teacher pension (federal grants)",
    "A57135": "Teacher pension (employee share paid by CPS)",
    "A57205": "Staff pension (employee share)", "A57210": "Staff pension (employer share)",
    "A57215": "Staff pension (federal grants)", "A57305": "Health and dental insurance",
    "A57405": "Medicare tax", "A57415": "Social Security tax", "A57505": "Unemployment insurance",
    "A57605": "Workers' compensation",
    "A54320": "Tuition paid to charter schools", "A54305": "Tuition for special education private programs",
    "A54125": "Professional and administrative services", "A54105": "Cleaning, repair and laborer services",
    "A54130": "Other services", "A54210": "Student bus and van service",
    "A54205": "Travel", "A54215": "Car fare", "A54220": "Car mileage payments", "A54230": "Student trips",
    "A53405": "Classroom and office supplies", "A53205": "Food", "A53210": "Donated food",
    "A53215": "Purchased food", "A53105": "Electricity", "A53115": "Electricity delivery",
    "A53120": "Natural gas delivery", "A53125": "Natural gas",
    "A53304": "Digital learning materials", "A53305": "Books and learning materials",
    "A53306": "Software for offices", "A53307": "Software for classrooms",
    "A55005": "Equipment", "A55010": "Furniture", "A56105": "Building repair contracts",
    "A57705": "Rent for space", "A57805": "Bond principal", "A57810": "Bond interest",
    "A57915": "Money held back for later (contingency)", "A57940": "Other charges",
    "A56310": "Construction", "A54535": "Insurance claims", "A54530": "Insurance premiums",
    "A54405": "Phone and telecom", "A54505": "Memberships, seminars and subscriptions",
    "A54520": "Printing", "A51930": "Supplies set-aside (budget only)",
    "A58110": "Teacher pay set-aside (budget only)", "A58113": "Teacher extended-day set-aside (budget only)",
    "A58210": "Staff pay set-aside (budget only)", "A58115": "Pension set-aside (budget only)",
    "A58275": "Non-teacher pension set-aside (budget only)",
    "A58195": "Health insurance set-aside (budget only)",
    "A58190": "Workers' compensation set-aside (budget only)",
    "A58185": "Unemployment set-aside (budget only)",
}

TYPE_NAMES = {
    "Salary": ("salaries", "Salaries"),
    "Benefits": ("benefits", "Benefits (pensions, health insurance)"),
    "Contracts": ("contracts", "Contracts and services"),
    "Commodities": ("supplies", "Supplies, food and utilities"),
    "Equipment": ("equipment", "Equipment and furniture"),
    "Transportation": ("transportation", "Transportation and travel"),
    "Contingencies": ("reserves", "Reserves, claims and other charges"),
    "Others": ("other", "Other"),
}


def spending_type(acct):
    sg = acct_sub.get(acct) or "Others"
    if "CAPITAL OUTLAY" in str(acct_l3.get(acct) or ""):
        sg = "Equipment"
    return sg if sg in TYPE_NAMES else "Others"


def kid_acct(acct):
    return KID_ACCT.get(acct) or acct_desc.get(acct) or acct


KID_UNIT = {
    "U11675": "Special education teachers and therapists (citywide)",
    "U11674": "Special education supports and private placements",
    "U11673": "Special education service delivery",
    "U11672": "Special education testing and placement",
    "U11610": "Special education operations and data",
    "U11940": "School buses (citywide)", "U11870": "Student transportation office",
    "U12050": "School meals (citywide)", "U12010": "School meals office",
    "U11880": "Keeping school buildings running (citywide)", "U11860": "Building operations office",
    "U11890": "District warehouse", "U11910": "Real estate office",
    "U12150": "Capital planning office (staff and operating costs)",
    "U11385": "Preschool and early learning (citywide)", "U11360": "Early childhood office",
    "U10615": "School safety and security (citywide)", "U10610": "School safety office",
    "U12670": "Set-asides, savings targets and held-back money",
    "U12625": "Grant-funded programs",
    "U14051": "Student health and wellness (citywide)", "U14050": "Student health and wellness office",
    "U11540": "Language programs (citywide)", "U11510": "Language and culture office",
    "U13737": "Sports and stadiums (citywide)",
    "U10855": "Counseling and college advising (citywide)", "U10850": "Counseling and college advising office",
    "U10898": "Social and emotional learning (citywide)", "U10895": "Social and emotional learning office",
    "U13727": "Early college and career (citywide)", "U13725": "Early college and career office",
    "U10870": "College and career success office", "U10872": "Community schools office",
    "U10875": "Student support programs (citywide)", "U11371": "Student support and engagement",
    "U11405": "Computer science office",
    "U12510": "Technology services", "U12210": "Buying and contracts office",
    "U12460": "Insurance and risk office", "U12410": "Accounting", "U12430": "Paying bills",
    "U12450": "Payroll", "U12610": "Budget office", "U12440": "Treasury office",
    "U11810": "Finance office", "U11010": "Hiring and teacher support (Talent)",
    "U11070": "Talent programs (citywide)", "U10210": "Lawyers (Law Office)",
    "U10110": "Board of Education", "U10320": "Inspector General", "U10710": "Executive office",
    "U10510": "Communications", "U10810": "Teaching and learning office",
    "U10814": "Curriculum and digital learning", "U11210": "Testing and student support",
    "U02541": "Principal development", "U11110": "Network support",
    "U05261": "JROTC program", "U12470": "Teacher pensions and insurance",
    "U12480": "Paying back loans",
}

LEVEL3_GROUP = {
    "Chief Education Office Total": ("education-offices", "Education offices (teaching, learning, networks)"),
    "Chief Operating Officer Total": ("operations-offices", "Operations offices (technology, buying, families)"),
    "Finance Total": ("finance-offices", "Finance offices"),
    "Talent Office Total": ("talent-offices", "Hiring and people offices"),
    "Portfolio Office Total": ("planning-offices", "Planning and enrollment offices"),
}
LEADERSHIP = ("leadership-legal", "Board, leadership and legal offices")

CITYWIDE_GROUPS = [
    ("special-education", "Special education services",
     ["U11610", "U11672", "U11673", "U11674", "U11675"]),
    ("transportation", "Getting kids to school (buses)", ["U11940", "U11870"]),
    ("food", "School meals", ["U12050", "U12010"]),
    ("facilities", "Keeping school buildings clean and running",
     ["U11880", "U11860", "U11890", "U11910", "U12150"]),
    ("early-childhood", "Preschool and early learning", ["U11360", "U11385"]),
    ("safety", "School safety and security", ["U10610", "U10615"]),
    ("student-support", "Student health, counseling and college and career programs",
     ["U10850", "U10855", "U10870", "U10872", "U10875", "U10895", "U10898", "U11371", "U11405",
      "U13725", "U13727", "U14050", "U14051"]),
    ("language-sports", "Language programs, sports and stadiums", ["U11510", "U11540", "U13737"]),
    ("set-asides", "Grants, set-asides and savings targets", ["U12625", "U12670"]),
]
CITY_UNIT_GROUP = {u: g for g in CITYWIDE_GROUPS for u in g[2]}

NET_NAME = {
    "Independent Schools Network Total": "Independent schools network",
    "Options Network Total": "Options network (alternative schools)",
    "Charter Schools Network Total": "Charter schools",
    "Contract Schools Network Total": "Contract schools",
}


def net_name(l4):
    if l4 in NET_NAME:
        return NET_NAME[l4]
    return re.sub(r"\s*Total$", "", l4 or "Other network")


# ------------------------------------------------------------------ why sentences
WHY_BY_TYPE = {
    "Salaries": "This is the pay budgeted for one group of employees. The budget lists pay by job title and department, not for each person.",
    "Benefits": "CPS buys pensions and health insurance for all employees as a group, so the budget does not break it down person by person.",
    "Contracts and services": "The money goes to outside companies and groups. CPS publishes what each was paid in total, but not which budget line it came from.",
    "Supplies, food and utilities": "This is food, supplies or utilities bought for many places, and the budget does not list each purchase.",
    "Equipment and furniture": "This is equipment bought for many places, and the budget does not list each purchase.",
    "Transportation and travel": "CPS pays bus companies by contract, so the public can see the budget but not what each route cost.",
    "Reserves, claims and other charges": "This is money held back or set aside for things that have not been decided yet, so there are no purchases to list.",
    "Other": "This is a small budget line with no public detail below it.",
}
WHY_TUITION = "One charter campus gets one tuition payment that depends on its student count."
WHY_BOND = "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself."
WHY_PROJECT = "Several big programs (like fixing fire alarms in many schools) are one budgeted amount, and CPS does not publish the dollars for each school."

# leaves_over_10m.json sentences for CPS, keyed by (unit description, account, dollars)
why_map = {}
for lf in leaves10["leaves"]:
    if lf["budget"] != "CPS" or not lf.get("why_cant_go_deeper"):
        continue
    segs = lf["path"].split(" > ")
    acct = segs[-1].split(" ")[0]
    why_map[(segs[-4].strip().lower(), acct, round(lf["amount"]))] = lf["why_cant_go_deeper"]
why_used = set()


def lookup_why(unit, acct, amount_cents):
    key = (unit_name.get(unit, "").strip().lower(), acct, round(amount_cents / 100))
    w = why_map.get(key)
    if w:
        why_used.add(key)
    return w


def generic_why(acct):
    sg = spending_type(acct)
    return {
        "Salary": WHY_BY_TYPE["Salaries"], "Benefits": WHY_BY_TYPE["Benefits"],
        "Contracts": WHY_BY_TYPE["Contracts and services"],
        "Commodities": WHY_BY_TYPE["Supplies, food and utilities"],
        "Equipment": WHY_BY_TYPE["Equipment and furniture"],
        "Transportation": WHY_BY_TYPE["Transportation and travel"],
        "Contingencies": WHY_BY_TYPE["Reserves, claims and other charges"],
    }.get(sg, WHY_BY_TYPE["Other"])


# ------------------------------------------------------------------ side lookups
actuals = pd.read_csv(P("raw/cps/cps_2026_actuals_unit_fund_account.csv"))
fy24 = actuals.groupby("unit")["actual_Ym2"].sum()
exp_ufa = pd.read_csv(P("raw/cps/cps_2026_exp_unit_fund_account.csv"))
fy25 = exp_ufa.groupby("unit")["prev_projected_exp"].sum()

enroll = {}
with open(P("raw/cps/sprof.json")) as f:
    for r in json.load(f):
        try:
            sc = int(r.get("StudentCount") or 0)
            if sc > 0 and r.get("FinanceID") not in (None, ""):
                enroll[f"U{int(r['FinanceID']):05d}"] = sc
        except (TypeError, ValueError):
            pass
ENR_SRC = {"dataset": "CPS School Profile API, school year 2024-2025", "url": "https://api.cps.edu/schoolprofile/CPS/AllSchoolProfiles",
           "file": "raw/cps/sprof.json", "note": "enrollment counts only, no personal data"}

charter_by_unit = {r.unit: r for r in charter.itertuples()}

# ------------------------------------------------------------------ build helpers
unit_nodes = {}      # unit code -> node that represents the unit (school or department)


def money_mix(rows):
    """Aggregate fund and program into compact extra dicts (cents)."""
    funds, areas = {}, {}
    for fg, pg, c in rows:
        funds[fund_parent.get(fg, "Other funds")] = funds.get(fund_parent.get(fg, "Other funds"), 0) + c
        a = prog_l1.get(pg, "Other")
        areas[a] = areas.get(a, 0) + c
    top = lambda d: dict(sorted(d.items(), key=lambda kv: -abs(kv[1]))[:5])  # noqa: E731
    return {"money_comes_from_cents": top(funds), "program_areas_cents": top(areas), "budget_lines": len(rows)}


# positions by unit x class x title (aggregated, no names exist in this file)
CLASS_OF = {"A51100": "Teacher", "A52100": "ESP"}
pos_groups = {}
for r in positions.itertuples():
    pos_groups.setdefault((r.unit, r.position_class), {}).setdefault(r.job_title, [0.0, 0.0])
    pos_groups[(r.unit, r.position_class)][r.job_title][0] += r.fte
    pos_groups[(r.unit, r.position_class)][r.job_title][1] += r.amount

POS_SRC = {"dataset": "CPS FY2026 budget positions by unit and job title", "file": "raw/cps/cps_2026_positions_unit_job.csv",
           "note": "budgeted FTE and salary by title, no fund dimension, so it is a proxy unless it ties exactly"}
n_tied_pos = n_proxy_pos = 0


def split_salary(node, unit, acct):
    """Split a regular-salary line by job title using positions x budgeted salary."""
    global n_tied_pos, n_proxy_pos
    grp = pos_groups.get((unit, CLASS_OF[acct]))
    if not grp:
        return False
    # Titles under 5 positions are rolled into one "other titles" bucket (total only, no average) so that a
    # one-person title (a principal, a clerk) never shows as its own salary. If the bucket itself would hold
    # fewer than 5 positions, the smallest shown title is pulled in until it does.
    items = sorted(((t, f, a) for t, (f, a) in grp.items() if cents(a) != 0), key=lambda x: -x[2])
    small = [x for x in items if x[1] < 5]
    shown = [x for x in items if x[1] >= 5]
    while small and sum(x[1] for x in small) < 5 and shown:
        small.append(shown.pop())
    if small and not shown:
        shown, small = [], small       # whole unit is small titles: one bucket, total only
    pieces = []
    for title, fte, amt in shown:
        c = cents(amt)
        pc = {"key": title, "name": title, "amount": c, "basis": "proxy", "source": POS_SRC, "kind": "job_title",
              "count": round(fte, 1), "unit_amount": cents(amt / fte), "unit_label": "positions (FTE)",
              "extra": {"fte": round(fte, 2)}}
        if c >= TEN_M:
            pc["why"] = (f"This is about {fte:,.0f} {title} positions at roughly ${amt / fte:,.0f} each. "
                         "The budget lists pay by job title, not by person.")
        pieces.append(pc)
    if small:
        sf, sa = sum(x[1] for x in small), sum(x[2] for x in small)
        if sf < 5:
            # not even the whole unit reaches 5 positions: no bucket, the money stays in the line's residual
            small = []
        else:
            pc = {"key": "other-titles", "name": "Other job titles (fewer than 5 positions each)", "amount": cents(sa),
                  "basis": "proxy", "source": POS_SRC, "kind": "job_title_group",
                  "extra": {"fte": round(sf, 2), "titles_in_group": len(small)},
                  "note": "Titles with fewer than 5 positions are added together, total only, no average shown."}
            if cents(sa) >= TEN_M:
                pc["why"] = WHY_BY_TYPE["Salaries"]
            pieces.append(pc)
    if not pieces:
        return False
    tot = sum(p["amount"] for p in pieces)
    diff = node.amount - tot
    tied = False
    if diff != 0 and abs(diff) <= max(len(pieces), 3):      # pure cent rounding of the pieces
        big = max(pieces, key=lambda p: p["amount"])
        big["amount"] += diff
        tied = True
    elif diff == 0:
        tied = True
    if tied:
        for p in pieces:
            p["basis"] = "tied"
        n_tied_pos += 1
    else:
        n_proxy_pos += 1
    who = "teacher" if CLASS_OF[acct] == "Teacher" else "staff"
    split(node, pieces, residual_name=f"Other {who} pay not listed by job title",
          residual_note="Budget line minus budgeted positions by title (stipends, vacancies, timing and funds that the positions file does not carry).",
          residual_why=WHY_BY_TYPE["Salaries"], allow_over=True)
    node.note = ("Job titles are budgeted positions x budgeted salary (FY2026). "
                 + ("They add up to this line exactly." if tied else "The positions file has no fund dimension, so this is an estimate."))
    return True


def leaf_split(leaf, acct, c):
    """Splits from data/leaves_cps.json that attach to a budget row (matched by account and amount)."""
    for entry in leaves_cps["leaves"]:
        tags = entry["match_path_contains"]
        accts = [t for t in tags if re.fullmatch(r"A\d{5}", t)]
        if not accts or accts[0] != acct or abs(cents(entry["amount"]) - c) > 100:
            continue
        pieces, rname, rnote = [], "Other / not itemised", None
        if acct == "A58115":
            fsrc = {"dataset": "CTPF actuarial valuation 6/30/2025, Table 11 p.44", "file": "data/cps_ctpf_valuation_2025.csv",
                    "url": "https://www.ctpf.org/sites/files/2025-10/CTPF_FundingVal_2025_Final.pdf"}
            names = {"Retirees": "Retired teachers", "Disabled retirees": "Teachers retired on disability",
                     "Beneficiaries": "Families of teachers who died (survivor benefits)"}
            for p in entry["pieces"]:
                lab = p["name"].split(":")[0]
                pieces.append({"key": lab, "name": f"{names.get(lab, lab)} ({p['count']:,} people)",
                               "amount": cents(p["contribution_share_proxy"]), "basis": "proxy",
                               "count": p["count"], "unit_label": "people paid by the pension fund",
                               "source": fsrc, "extra": {"official_name": p["name"], "average_annual_benefit_cents": cents(p["average"]),
                                                        "annual_benefits_cents": cents(p["annual_benefits"])},
                               "note": "The levy is one payment by law. Its share is allocated by each group's share of benefit dollars (estimate).",
                               "why": lookup_why_levy()})
            rname, rnote = "Other / not itemised (rounding in the shares)", "The three shares come to $1 less than the levy."
        elif acct == "A58195":
            for p in entry["pieces"]:
                lab = p["name"]
                nm = {"Medical (HCSC) share": "Medical plan share (HCSC)", "Prescription (Caremark) share": "Prescription plan share (Caremark)",
                      "Dental share": "Dental plan share", "Life and disability share": "Life and disability insurance share"}.get(lab, lab)
                pieces.append({"key": lab, "name": nm, "amount": cents(p["amount"]), "basis": "proxy",
                               "source": {"dataset": "CPS supplier payments FY2026 (shares of vendor payments)",
                                          "file": "data/cps_supplier_payments_fy2026_over1m.csv"},
                               "note": "Reserve allocated by each plan's share of FY2026 vendor payments (estimate).",
                               "why": entry["why_cant_go_deeper"] if cents(p["amount"]) >= TEN_M else None})
        elif acct == "A54210":
            p = entry["pieces"][0]
            pieces.append({"key": "routes", "name": f"About {p['count']:,} special education bus routes (about ${p['average']:,} each)",
                           "amount": cents(p["count"] * p["average"]), "basis": "proxy", "count": p["count"],
                           "unit_amount": cents(p["average"]), "unit_label": "routes",
                           "source": {"doc": "CPS FY2026 Budget Book, Student Transportation Services", "file": "raw/cps/bb26.pdf.txt"},
                           "note": "About 14,000 students ride, which is about $10,479 per student. Routes are run by about 20 vendors.",
                           "why": entry["why_cant_go_deeper"]})
        elif acct == "A54105":
            p = entry["pieces"][0]
            pieces.append({"key": "buildings", "name": f"About {p['count']:,} school buildings (about ${p['average']:,} each, equal shares)",
                           "amount": cents(p["count"] * p["average"]), "basis": "proxy", "count": p["count"],
                           "unit_amount": cents(p["average"]), "unit_label": "buildings",
                           "source": {"doc": "CPS FY2026 Budget Book, facilities portfolio", "file": "raw/cps/bb26.pdf.txt"},
                           "note": "One facility-management contract covers all buildings. This is an equal share, not a real per-building cost.",
                           "why": entry["why_cant_go_deeper"]})
        else:
            continue
        split(leaf, pieces, residual_name=rname, residual_note=rnote,
              residual_why=entry["why_cant_go_deeper"] if leaf.amount - sum(p["amount"] for p in pieces) >= TEN_M else None)
        leaf.note = (leaf.note or "") + " Split below is an estimate (proxy), see each piece."
        return True
    return False


def lookup_why_levy():
    for lf in leaves_cps["leaves"]:
        if lf["match_path_contains"][-1] == "A58115":
            return lf["why_cant_go_deeper"]


def add_account(parent, unit, acct, rows, force_flat=False):
    """parent = spending-type node. rows = list of (fund, program, cents)."""
    total = sum(r[2] for r in rows)
    kname = kid_acct(acct)
    extra = {"account_code": acct, "official_name": acct_desc.get(acct, acct)}
    extra.update(money_mix(rows))
    neg_only = total < 0 and all(r[2] <= 0 for r in rows)
    budget_only = (acct_desc.get(acct, "")).startswith("Budget Only")
    note = None
    if budget_only:
        note = "Budget-only line: a set-aside or planned saving in the budget, not a payment to anyone."
    node = parent.add(acct, kname, amount=total, kind="account", extra=extra, note=note,
                      basis="adjustment" if neg_only else None)

    # tuition by school from the charter file
    ch = charter_by_unit.get(unit)
    if acct == "A54320" and ch is not None:
        if abs(cents(ch.fy26_charter_tuition_budget) - total) > 2:
            problems.append(f"charter tuition mismatch at {unit}: file {ch.fy26_charter_tuition_budget} vs tree {total / 100}")
        st = ch.students_profile_api
        if pd.notna(st) and st >= 50:
            node.count = float(st)
            node.unit_amount = cents(total / 100 / st)
            node.unit_label = "students"
            node.note = (f"{int(st):,} students (2024-25 school profile) x about ${total / 100 / st:,.0f} per student. "
                         "Per-student figure is tuition divided by profile enrollment (estimate).")

    if CLASS_OF.get(acct) and (unit, CLASS_OF[acct]) in pos_groups and total > 0 and not force_flat:
        if split_salary(node, unit, acct):
            return node

    big = [r for r in rows if abs(r[2]) >= ONE_M]
    if len(rows) > 1 and abs(total) >= TEN_M and big and not force_flat:
        used = 0
        for i, (fg, pg, c) in enumerate(sorted(big, key=lambda r: -abs(r[2]))):
            pd_name = prog_desc.get(pg, pg)
            if "Vacancy Factor" in pd_name:
                pd_name = "Planned savings from jobs left unfilled (vacancy factor)"
            nm = f"{pd_name} ({fund_desc.get(fg, fg)})"
            k = node.add(f"{fg}-{pg}-{i}", nm, amount=c, kind="budget_line",
                         basis="adjustment" if c < 0 else None,
                         extra={"fund": fund_desc.get(fg, fg), "fund_code": fg, "program": prog_desc.get(pg, pg),
                                "program_code": pg, "money_comes_from": fund_parent.get(fg, "Other funds")})
            used += c
            finish_leaf(k, unit, acct, c)
        rest = total - used
        if rest != 0 or len(big) < len(rows):
            n_rest = len(rows) - len(big)
            r_node = node.add("all-other", f"All other funds and programs ({n_rest:,} smaller lines)", amount=rest,
                              kind="budget_line", basis="adjustment" if rest < 0 else None,
                              extra=money_mix([r for r in rows if abs(r[2]) < ONE_M]))
            finish_leaf(r_node, unit, acct, rest)
        node.amount = total
    else:
        finish_leaf(node, unit, acct, total)
    return node


def finish_leaf(n, unit, acct, c):
    if n.children:
        return
    if leaf_split(n, acct, c):
        return
    if abs(c) >= TEN_M and not n.why:
        w = lookup_why(unit, acct, c)
        if not w:
            w = WHY_TUITION if acct == "A54320" else generic_why(acct)
        n.why = w


def build_unit(parent, unit, rows, name=None, key=None, kind="department", extra=None, force_flat=False):
    """rows: dataframe-like iterable of (fund, program, account, cents)."""
    off = unit_name.get(unit, unit)
    ex = {"unit_code": unit, "official_name": off, "unit_type": S(dim_unit["Unit Type"].get(unit))}
    if extra:
        ex.update(extra)
    node = parent.add(key or unit, name or KID_UNIT.get(unit) or off, kind=kind, extra=ex)
    by_acct = {}
    for fg, pg, ac, c in rows:
        by_acct.setdefault(ac, []).append((fg, pg, c))
    by_type = {}
    for ac in by_acct:
        by_type.setdefault(spending_type(ac), []).append(ac)
    for st, accts in by_type.items():
        tnode = node.add(TYPE_NAMES[st][0], TYPE_NAMES[st][1], kind="spending_type",
                         extra={"account_subgroup": st})
        for ac in sorted(accts):
            add_account(tnode, unit, ac, by_acct[ac], force_flat=force_flat)
    unit_nodes[unit] = node
    return node


# ------------------------------------------------------------------ route rows to boxes
fact["fund_group"] = fact["fund_grant"].map(fund_group)
is_cap = fact["fund_group"].eq("Capital Funds")
is_debt = fact["unit"].eq("U12480")
is_debt_extra = fact["unit"].eq("U12670") & fact["account"].eq("A57810")
is_pens = fact["unit"].eq("U12470")
rest = fact[~(is_cap | is_debt | is_debt_extra | is_pens)]

# ---- group units
u_info = dim_unit[["Unit Description", "Unit Type", "Level 3 Unit Description", "Level 4 Unit Description"]]


def classify(unit):
    l3 = u_info.at[unit, "Level 3 Unit Description"]
    l4 = u_info.at[unit, "Level 4 Unit Description"]
    if unit in CITY_UNIT_GROUP:
        return "citywide"
    if l3 == "School Networks Total":
        return "charter" if l4 in ("Charter Schools Network Total", "Contract Schools Network Total") else "school"
    return "central"


unit_rows = {}
for t in rest[["unit", "fund_grant", "program", "account", "cents"]].itertuples(index=False):
    unit_rows.setdefault(t.unit, []).append((t.fund_grant, t.program, t.account, t.cents))

# ============================================================ 1. Schools
schools = root.add("schools", "Schools", kind="box", extra={"official_name": "School networks"},
                   note="Every school's whole budget: teachers, staff, benefits, supplies and contracts.")
district = schools.add("district-run", "District-run schools", kind="group",
                       extra={"official_name": "CPS public, AUSL, alternative and independent schools"})
charters = schools.add("charter", "Charter and contract schools", kind="group",
                       extra={"official_name": "Charter Schools Network and Contract Schools Network"},
                       note="Charter schools are public schools run by outside groups. CPS pays each one tuition per student.")
network_nodes = {}
for unit in sorted(unit_rows, key=lambda u: (-sum(r[3] for r in unit_rows[u]), u)):
    cls = classify(unit)
    l4 = u_info.at[unit, "Level 4 Unit Description"]
    if cls == "school":
        nn = network_nodes.get(l4)
        if nn is None:
            nn = district.add(l4, net_name(l4), kind="network", extra={"official_name": l4})
            network_nodes[l4] = nn
        parent = nn
    elif cls == "charter":
        parent = charters
    else:
        continue
    gt = dim_unit["Grade Type"].get(unit)
    ex = {"grade_type": gt if isinstance(gt, str) else None}
    if unit in enroll:
        ex["enrollment_2024_25"] = enroll[unit]
    build_unit(parent, unit, unit_rows[unit], kind="school", extra=ex)

# ============================================================ 2. Central and network offices
central = root.add("central", "Central and network offices", kind="box",
                   extra={"official_name": "Central offices, network offices and the Board"},
                   note="The people and costs of running a district of 500+ schools, outside the schools themselves.")
area_nodes = {}
for unit in sorted(unit_rows, key=lambda u: (-sum(r[3] for r in unit_rows[u]), u)):
    if classify(unit) != "central":
        continue
    l3 = u_info.at[unit, "Level 3 Unit Description"]
    gk, gn = LEVEL3_GROUP.get(l3, LEADERSHIP)
    an = area_nodes.get(gk)
    if an is None:
        an = central.add(gk, gn, kind="group", extra={"official_name": l3 if isinstance(l3, str) else "Board, CEO and independent offices"})
        area_nodes[gk] = an
    build_unit(an, unit, unit_rows[unit])

# ============================================================ 3. Citywide programs
city = root.add("citywide", "Citywide programs", kind="box",
                extra={"official_name": "City Wide units (programs that serve every school)"},
                note="Services CPS runs for all schools at once, like buses, meals, building upkeep and special education.")
for gk, gname, units in CITYWIDE_GROUPS:
    gn = None
    for unit in units:
        # U12150 operating remainder only (capital funds are in Building projects)
        if unit not in unit_rows:
            continue
        if gn is None:
            gn = city.add(gk, gname, kind="group")
        build_unit(gn, unit, unit_rows[unit])

# ============================================================ 4. Teacher pensions and insurance (U12470)
pen_rows = fact[is_pens]
pbox = root.add("pensions", "Teacher pensions and insurance", kind="box",
                extra={"unit_code": "U12470", "official_name": "Pension & Liability Insurance - City Wide",
                       "file": "data/cps_pension_insurance_fy26.csv"},
                note=("The property-tax levy paid to the Chicago Teachers' Pension Fund, money set aside for non-teacher "
                      "pensions, health insurance and claims. School-level pension lines are inside each school."),
                source=src(dataset="CPS FY2026 budget, Pension & Liability Insurance unit (data/cps_pension_insurance_fy26.csv)"))
PGROUP = {
    "pension": ("Pensions and Medicare tax", {"A58115", "A58275", "A57105", "A57110", "A57135", "A57205", "A57210", "A57215", "A57405"}),
    "health": ("Health insurance", {"A58195", "A57305"}),
    "claims": ("Workers' compensation, unemployment and claims", {"A58190", "A58185", "A54535", "A54125", "A57605", "A57505"}),
    "pay": ("Salaries and payouts in this office", {"A51100", "A52100", "A51130", "A52130", "A51140", "A52150", "A51500", "A51140"}),
}
LINE_NAME = {
    ("FG129-000000", "A58115"): "Teacher pension levy paid to the Chicago Teachers' Pension Fund",
    ("FG115-000000", "A58115"): "Pension reserve in the general fund (a reservation, not a payment)",
    ("FG115-000000", "A58275"): "Reserve for non-teacher staff pensions (MEABF)",
}
groups_p = {}
for t in pen_rows.itertuples(index=False):
    k = next((g for g, (_, s) in PGROUP.items() if t.account in s), "other")
    groups_p.setdefault(k, []).append(t)
file_lines = {(r.fund, r.program, r.account): r.fy26_budget for r in pens.itertuples()}
for k in ["pension", "health", "claims", "pay", "other"]:
    if k not in groups_p:
        continue
    gnode = pbox.add(k, PGROUP[k][0] if k in PGROUP else "Other lines in this office", kind="group")
    for i, t in enumerate(sorted(groups_p[k], key=lambda t: -abs(t.cents))):
        fnm, pnm = fund_desc.get(t.fund_grant, t.fund_grant), prog_desc.get(t.program, t.program)
        # tie to the data file line (fund, program, account)
        fv = file_lines.get((fnm, pnm, t.account))
        if fv is None or abs(cents(fv) - t.cents) > 2:
            problems.append(f"pension file line missing or not tied: {fnm}/{pnm}/{t.account} file={fv} tree={t.cents / 100}")
        nm = LINE_NAME.get((t.fund_grant, t.account)) or f"{kid_acct(t.account)} ({pnm})"
        neg = t.cents < 0
        leaf = gnode.add(f"{t.fund_grant}-{t.program}-{t.account}", nm, amount=t.cents, kind="budget_line",
                         basis="adjustment" if neg else None,
                         extra={"account_code": t.account, "official_name": acct_desc.get(t.account),
                                "fund": fnm, "program": pnm},
                         note=("Budget-only offset: planned saving that offsets spending counted elsewhere." if neg
                               else ("Budget-only line: a reserve, not a payment." if acct_desc.get(t.account, "").startswith("Budget Only") else None)))
        if t.account == "A58275":
            leaf.extra.update({"retired_members": 21874, "average_annual_pension_cents": cents(49104),
                               "surviving_spouses": 3714, "note_source": "MEABF valuation, all City and CPS members"})
            leaf.note = ("Reserve in case CPS must repay the City for non-teacher pensions. A separate $175M repayment to the City is not in "
                         "the budget. Members and averages are for all City and CPS members, so no split by dollars is shown.")
        finish_leaf(leaf, "U12470", t.account, t.cents)
unit_nodes["U12470"] = pbox

# ============================================================ 5. Paying back loans (U12480 bond series)
dbox = root.add("debt", "Paying back loans", kind="box",
                extra={"unit_code": "U12480", "official_name": "Debt Services - City Wide", "file": "data/cps_debt_by_series_fy26.csv"},
                note="CPS borrows money by selling bonds. Each bond series has a yearly payment of principal and interest.",
                source=src(dataset="CPS FY2026 budget, Debt Services unit (data/cps_debt_by_series_fy26.csv)",
                           doc="CPS FY2026 Budget Book, Tables 3 to 6, pp.225-230"))
d_by_fund = {}
for t in fact[is_debt].itertuples(index=False):
    d_by_fund[t.fund_grant] = d_by_fund.get(t.fund_grant, 0) + t.cents
drows = {r.fund_grant: r for r in debt.itertuples()}
if set(d_by_fund) != set(drows):
    problems.append(f"debt funds differ: only base {sorted(set(d_by_fund) - set(drows))} only file {sorted(set(drows) - set(d_by_fund))}")
for fg, c in sorted(d_by_fund.items(), key=lambda kv: -kv[1]):
    r = drows.get(fg)
    if r is not None and abs(cents(r.fy26_total) - c) > 2:
        problems.append(f"debt series {fg} not tied: file {r.fy26_total} tree {c / 100}")
    name = f"Bond series {r.series_key}" if r is not None and isinstance(r.series_key, str) else "Fees on certificates of participation"
    ex = {"fund_code": fg, "official_name": fund_desc.get(fg, fg)}
    note = None
    if r is not None:
        ex.update({"principal_cents": cents(r.fy26_principal) if pd.notna(r.fy26_principal) else None, "interest_cents": cents(r.fy26_interest) if pd.notna(r.fy26_interest) else None,
                   "other_cents": cents(r.fy26_other) if pd.notna(r.fy26_other) else None, "outstanding_principal_6_30_2025_cents": cents(r.principal_outstanding_6_30_2025) if pd.notna(r.principal_outstanding_6_30_2025) else None,
                   "fixed_rate": S(r.fixed_rate), "final_maturity": S(r.final_maturity), "pledged_source": S(r.pledged_source)})
        if isinstance(r.fixed_rate, str):
            note = (f"Principal ${r.fy26_principal:,.0f} plus interest ${r.fy26_interest:,.0f}. "
                    f"Rate {r.fixed_rate}, final payment {r.final_maturity}, paid from {r.pledged_source}.")
        else:
            note = f"Fees of ${r.fy26_total:,.0f} on certificates of participation (no bond series)."
    leaf = dbox.add(fg, name, amount=c, kind="bond_series", extra=ex, note=note)
    if c >= TEN_M:
        leaf.why = WHY_BOND
dx = fact[is_debt_extra]
if len(dx):
    c = int(dx.cents.sum())
    leaf = dbox.add("general-fund-interest", "Bond interest paid from the general fund (not tied to one series)", amount=c,
                    kind="bond_series", extra={"unit_code": "U12670", "account_code": "A57810",
                                               "official_name": "Education General - City Wide, Debt - Interest Expense"},
                    note="Sits in the Education General unit of the budget. Not listed in the bond series table.")
    if c >= TEN_M:
        leaf.why = WHY_BOND

# ============================================================ 6. Building projects (capital)
cap_rows = fact[is_cap]
cap_total = int(cap_rows.cents.sum())
cbox = root.add("capital", "Building projects", kind="box",
                extra={"unit_code": "U12150", "official_name": "Capital/Operations - City Wide, capital funds",
                       "file": "data/cps_capital_projects_fy26.csv",
                       "capital_funds_cents": {fund_desc.get(fg, fg): int(g.cents.sum()) for fg, g in cap_rows.groupby("fund_grant")}},
                amount=cap_total,
                note="Fixing and building schools. The project list is $3,874 short of the capital fund lines in the budget database, shown below as a visible difference.",
                source=src(dataset="CPS FY2026 capital budget, project list (data/cps_capital_projects_fy26.csv)",
                           url="http://schoolreports.cps.edu/capitalplan/"))
cap_src = {"dataset": "CPS Capital Budget (Oracle BI), FY2026 project list", "file": "data/cps_capital_projects_fy26.csv",
           "url": "http://schoolreports.cps.edu/capitalplan/"}
cats = {}
for i, r in enumerate(capital.itertuples()):
    cats.setdefault(r.main_category, []).append((i, r))
cat_pieces = []
for cname, items in sorted(cats.items(), key=lambda kv: -sum(cents(r.budget) for _, r in kv[1])):
    cat_pieces.append({"key": cname, "name": cname, "amount": sum(cents(r.budget) for _, r in items), "kind": "group",
                       "basis": "budget", "source": cap_src})
made = split(cbox, cat_pieces, residual_name="Not matched to a listed project",
             residual_note="Capital fund lines in the budget ($555,945,321) minus the FY2026 project list ($555,941,447). CPS does not explain the $3,874.",
             residual_basis="residual")
phase_names = [("design", "Design"), ("construction", "Construction"), ("environmental", "Environmental review"),
               ("management", "Project management")]
for cnode in made:
    if cnode.id.endswith("other-not-itemised"):
        continue
    cname = next(k for k in cats if slug(k) == cnode.id.split(".")[-1])
    for i, r in cats[cname]:
        c = cents(r.budget)
        pn = r.project_name if isinstance(r.project_name, str) else "Project"
        ex = {"project_number": S(r.project_number), "official_name": pn,
              "sub_category": S(r.sub_category), "money_source": S(r.source), "status": S(r.status), "ward": S(r.ward) if isinstance(r.ward, str) else (str(int(r.ward)) if pd.notna(r.ward) else None),
              "school_unit": f"U{int(r.unit):05d}", "school_or_unit_name": S(r.unit_name), "pdf_url": S(r.pdf_url), "project_type": S(r.project_type)}
        pnode = cnode.add(f"{r.project_number}-{i}", pn, amount=c, kind="project", basis="budget", extra=ex, source=cap_src,
                          note=f"{S(r.project_type) or 'Project'}. Status: {S(r.status) or 'not stated'}. Paid for by: {S(r.source) or 'not stated'}.")
        phases = [(k, nm, r.design if k == "design" else r.construction if k == "construction"
                   else r.environmental if k == "environmental" else r.management) for k, nm in phase_names for _ in [0]]
        phases = [(k, nm, v) for k, nm, v in phases if pd.notna(v) and v]
        if phases:
            pcs = [{"key": k, "name": f"{pn}: {nm}", "amount": cents(v), "basis": "tied", "kind": "project_phase",
                    "source": cap_src} for k, nm, v in phases]
            if sum(p["amount"] for p in pcs) == c:
                split(pnode, pcs)
        if not pnode.children and c >= TEN_M:
            pnode.why = WHY_PROJECT
        for ph in pnode.children:
            if ph.amount >= TEN_M and not ph.why:
                ph.why = WHY_PROJECT

# ============================================================ side info
FY_SRC = {"dataset": "CPS Budget BI, prior-year measures", "file": "raw/cps/cps_2026_actuals_unit_fund_account.csv; cps_2026_exp_unit_fund_account.csv",
          "note": "BI actual columns understate audited district spending (see research/cps_deep.md section 6). Unit-level patterns only."}
n_side_fy = 0
for unit, node in unit_nodes.items():
    if unit == "U12150":      # mixed capital + operating unit: shown once on Building projects
        continue
    a, p25 = fy24.get(unit), fy25.get(unit)
    if a is not None and abs(a) >= 0.5:
        node.side.append({"kind": "prior_year_actual", "label": "FY2024 actual spending (Budget BI)", "amount": cents(a),
                          "period": "FY2024", "basis": "actual", "source": FY_SRC})
        n_side_fy += 1
    if p25 is not None and abs(p25) >= 0.5:
        node.side.append({"kind": "prior_year_actual", "label": "FY2025 projected spending (Budget BI)", "amount": cents(p25),
                          "period": "FY2025", "basis": "projected", "source": FY_SRC})
        n_side_fy += 1
# debt box also holds the U12670 interest rows: FY side for U12670 goes on its department node (already in unit_nodes)
unit_nodes["U12480"] = dbox
for unit in ("U12480",):
    a, p25 = fy24.get(unit), fy25.get(unit)
    if a is not None:
        dbox.side.append({"kind": "prior_year_actual", "label": "FY2024 actual spending (Budget BI)", "amount": cents(a),
                          "period": "FY2024", "basis": "actual", "source": FY_SRC})
    if p25 is not None:
        dbox.side.append({"kind": "prior_year_actual", "label": "FY2025 projected spending (Budget BI)", "amount": cents(p25),
                          "period": "FY2025", "basis": "projected", "source": FY_SRC})
# capital: unit U12150 as a whole (includes a small operating part that is under Citywide programs)
a, p25 = fy24.get("U12150"), fy25.get("U12150")
for lab, v, per, bs in (("FY2024 actual spending, whole capital/operations unit U12150 (Budget BI)", a, "FY2024", "actual"),
                        ("FY2025 projected spending, whole capital/operations unit U12150 (Budget BI)", p25, "FY2025", "projected")):
    if v is not None:
        cbox.side.append({"kind": "prior_year_actual", "label": lab, "amount": cents(v), "period": per, "basis": bs, "source": FY_SRC})

# enrollment per school
n_enr = 0
for unit, n in enroll.items():
    node = unit_nodes.get(unit)
    if node is not None and node.kind == "school":
        node.side.append({"kind": "enrollment", "label": "Students enrolled (2024-25 school profile)", "count": n,
                          "period": "2024-25", "basis": "count", "source": ENR_SRC})
        n_enr += 1

# vendors: normalise and link through Board Report sponsoring departments (+ documented links)


def norm(s):
    s = str(s).upper()
    s = re.sub(r"\(.*?\)", "", s)
    s = re.sub(r"[^A-Z0-9 ]", " ", s)
    s = re.sub(r"\b(INC|LLC|LP|LLP|CORP|CORPORATION|CO|COMPANY|LTD|THE|DBA|NO)\b", " ", s)
    return " ".join(s.split())


vendors["n"] = vendors["vendor"].map(norm)
aw = awards[awards["user_units"].notna() & awards["user_units"].astype(str).str.match(r"^\d{5}")]
vend_units = {}
for r in aw.itertuples():
    for part in str(r.user_units).split(";"):
        m = re.match(r"(\d{5})", part.strip())
        if m:
            vend_units.setdefault(norm(r.vendor), set()).add("U" + m.group(1))
VEND_SRC = {"dataset": "CPS procurement supplier payments FY2026 (vendors paid $1M or more)",
            "file": "data/cps_supplier_payments_fy2026_over1m.csv",
            "url": "https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026"}
LINK_AWARD = ("Linked by the sponsoring department named in Board Report contract awards (data/cps_contract_awards_fy21_27.csv)")
DOC_LINKS = {  # documented in research/cps_deep.md sections 1 and 4
    "U12470": ["HEALTH CARE SERVICE CORPORATION", "CVS PHARMACY", "DELTA DENTAL OF ILLINOIS", "STANDARD INSURANCE"],
    "U12050": ["ARAMARK EDUCATIONAL SERVICES"],
    # bus and van companies (name match, research/cps_deep.md section 4)
    "U11940": ["ILLINOIS CENTRAL SCHOOL BUS", "SUNRISE TRANSPORTATION", "ALLTOWN BUS", "A.M. BUS COMPANY", "FIRST STUDENT",
               "SCR MEDICAL TRANSPORTATION", "COMPASS TRANSPORTATION", "RELIANT TRANSPORTATION", "AMMONS TRANSPORTATION",
               "CONWAY BUS COMPANY", "BJ'S TRANSPORTATION"],
    # utilities and facility vendors named for this unit in research/cps_deep.md section 4
    "U11880": ["COMMONWEALTH EDISON", "PEOPLES GAS", "DIVERSE FACILITY SOLUTIONS", "TOTAL FACILITY MAINTENANCE"],
    # private special education placements in U11674 (research/cps_deep.md section 4)
    "U11674": ["CAMELOT THERAPEUTIC SCHOOLS", "SPECIAL EDUCATION SERVICES DBA MENTA", "PATHWAYS IN EDUCATION-ILLINOIS"],
}
n_v = 0
for r in vendors.itertuples():
    units = sorted(u for u in vend_units.get(r.n, set()) if u in unit_nodes)
    for u in units:
        unit_nodes[u].side.append({"kind": "vendor_payment", "label": f"{r.vendor}: paid FY2026, vendor-level, not tied to budget lines",
                                   "amount": cents(r.payment_amount), "period": "FY2026", "basis": "paid", "source": VEND_SRC,
                                   "link": LINK_AWARD, "departments_linked": len(units),
                                   "note": "The vendor total covers all CPS departments it works for."})
        n_v += 1
    for u, pats in DOC_LINKS.items():
        if u in unit_nodes and any(r.vendor.upper().startswith(p) for p in pats):
            if u in units:
                continue
            unit_nodes[u].side.append({"kind": "vendor_payment", "label": f"{r.vendor}: paid FY2026, vendor-level, not tied to budget lines",
                                       "amount": cents(r.payment_amount), "period": "FY2026", "basis": "paid", "source": VEND_SRC,
                                       "link": "Named for this department in research/cps_deep.md (health, nutrition) from CPS vendor and contract records",
                                       "note": "The vendor total covers all CPS departments it works for."})
            n_v += 1

# ============================================================ order children, then check
root.rollup()


def order_kids(n):
    n.children.sort(key=lambda c: (1 if (c.id.endswith("other-not-itemised") or c.id.endswith("all-other") or c.id.endswith(".difference")) else 0,
                                   -abs(c.amount or 0)))
    for c in n.children:
        order_kids(c)


TOP = ["schools", "central", "citywide", "pensions", "debt", "capital"]
for c in root.children:
    order_kids(c)
root.children.sort(key=lambda c: TOP.index(c.id.split(".")[-1]))

# -- tie-outs not covered by check()
if root.amount != EXPECTED:
    problems.append(f"root {root.amount} != {EXPECTED}")
if not any(c.id.endswith("other-not-itemised") and c.amount == 387400 for c in cbox.children):
    problems.append("capital residual is not $3,874")
for fgn, tgt in (("Capital Funds", 555945321_00),):
    if cbox.amount != tgt:
        problems.append(f"capital box {cbox.amount} != {tgt}")
if abs(dbox.amount - (cents(debt.fy26_total.sum()) + int(dx.cents.sum()))) > 50:
    problems.append(f"debt box {dbox.amount} != file total + general fund interest")
if pbox.amount != cents(pens.fy26_budget.sum()) and abs(pbox.amount - cents(pens.fy26_budget.sum())) > 5:
    problems.append(f"pension box {pbox.amount} vs file {cents(pens.fy26_budget.sum())}")
# every unit in the base appears once in the tree
placed = {n.extra.get("unit_code") for n in root.walk() if n.kind in ("school", "department")}
for u in set(fact["unit"]) - placed - {"U12470", "U12480"}:
    if u not in {t for t in fact.loc[is_cap | is_debt_extra, "unit"]}:
        problems.append(f"unit not placed: {u}")
# titles under 5 positions have no average
for n in root.find(lambda n: n.kind in ("job_title", "job_title_group")):
    if n.extra.get("fte", 0) < 5:
        problems.append(f"job title group under 5 positions shown on its own: {n.id}")
    if n.kind == "job_title_group" and n.unit_amount is not None:
        problems.append(f"title group shows an average: {n.id}")

# no employee names: bigram scan against the local roster (names never printed)
try:
    with open(P("data/people/cps_positions_2025q4.json")) as f:
        names = [p["name"] for p in json.load(f)["positions"] if p.get("name")]
    blob = json.dumps(to_rows(root), default=str) + json.dumps(side_rows(root), default=str)
    toks = re.findall(r"[A-Za-z']+", blob.upper())
    bigrams = set(zip(toks, toks[1:]))
    # school and department names honour real people (William Jones, Maria Saucedo...). Word pairs that come
    # from an official unit or vendor name are not employee names, so they are set aside and counted.
    official = set()
    for txt in list(dim_unit["Unit Description"].dropna()) + list(vendors["vendor"].dropna()) + \
            list(capital["project_name"].dropna()) + list(capital["unit_name"].dropna()):
        tk = re.findall(r"[A-Za-z']+", str(txt).upper())
        official.update(zip(tk, tk[1:]))
    skipped = len(bigrams & official)
    bigrams -= official
    hits = 0
    for nm in names:
        if "," not in nm:
            continue
        last, first = [x.strip() for x in nm.upper().split(",", 1)]
        fw = re.findall(r"[A-Z']+", first)
        lw = re.findall(r"[A-Z']+", last)
        if not fw or not lw or len(last) < 3 or len(first) < 3:
            continue
        if (fw[0], lw[0]) in bigrams or (lw[-1], fw[0]) in bigrams:
            hits += 1
    if hits:
        problems.append(f"{hits} roster names look present in the tree (first+last word pairs); inspect before publishing")
    print(f"name scan: {len(names):,} roster names checked, {hits} possible hits ({skipped} word pairs set aside as official school/vendor/project names)")
except FileNotFoundError:
    print("name scan skipped: data/people/cps_positions_2025q4.json not found")

_blob = json.dumps(to_rows(root)) + json.dumps(side_rows(root))
if "NaN" in _blob or "nan" in re.findall(r'"([^"]*)"', _blob):
    problems.append("NaN found in output")
problems += check(root, expected_total_cents=EXPECTED, verbose=True)

dr = depth_report(root)
n_nodes = sum(1 for _ in root.walk())
print(f"nodes: {n_nodes:,}   side rows: {len(side_rows(root)):,} (prior-year {n_side_fy}, enrollment {n_enr}, vendor {n_v})")
print(f"why sentences reused from data/leaves_over_10m.json: {len(why_used)} of {len(why_map)} CPS entries")
print(f"salary splits: {n_tied_pos} tie exactly, {n_proxy_pos} are proxies")
print("depth:", json.dumps(dr))
print("top level:")
for c in root.children:
    print(f"   {c.amount / 100:>18,.2f}  {c.name}")
print(f"   {root.amount / 100:>18,.2f}  TOTAL")

if problems:
    print(f"FAILED: {len(problems)} problems")
    for p in problems[:40]:
        print("  -", p)
    sys.exit(1)

os.makedirs(P("build/out"), exist_ok=True)
save_json(root, P("build/out/cps_tree.json"))
rows = to_rows(root)
side = side_rows(root)
db = P("data/budget.db")
con = sqlite3.connect(db)
try:
    con.execute("DELETE FROM checks WHERE gov='cps'")
    con.commit()
except sqlite3.OperationalError:
    pass
con.close()
load_into_db(db, "cps", rows, side,
             ("cps", datetime.now(timezone.utc).isoformat(), len(rows), root.amount, EXPECTED, 0, json.dumps(dr)))
print(f"OK: {len(rows):,} rows and {len(side):,} side rows written to {db}")
