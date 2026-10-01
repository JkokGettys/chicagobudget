"""Build the Chicago Park District FY2026 budget tree.

Base: data/parks_2026.json (validated tree, sums to the printed Grand Total $637,580,350).
Reshaped by what the money is for, with kid-friendly names (official names kept in
extra["official_name"]). All amounts are integer cents.

Top of tree:
  Chicago Park District ($637,580,350)
    Parks and recreation               regions > park (name + number) > fund > account > job title,
                                       plus districtwide recreation programs and Grant Park Music Festival
    Maintaining the parks              Operations & Maintenance departments
    Running the District               Administration & Finance departments
    Utilities, benefits and other shared costs   (Finance General, what is left after the boxes below)
    Retirement (pensions)              Park Employees' Annuity and Benefit Fund
    Paying back loans                  25 bond series + planned borrowing + interest outside the schedule
    Soldier Field, harbors, golf and other managed venues   (all 626xxx management contracts)
    Museums and the zoo                11 institutions + Lincoln Park Zoo
    Building and fixing parks (capital)  operating money moved to capital (side info: CIP, TIF projects)
    Not itemised on any department page  ($880,099 reconciling item)

Side info (never in amounts): 2025 budget per node, 2019-2022 vendor payments (latest published),
capital project dollars (TIF plan lines, IGAs, contracts, grants), pension fund context.

Run: python3 build/parks_tree.py   (exit 1 if any check fails)
"""
import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from treelib import Node, cents, check, depth_report, split, save_json, to_rows, side_rows, load_into_db  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731


def D(name):
    with open(P("data", name)) as f:
        return json.load(f)


park = D("parks_2026.json")
vend = D("parks_vendors.json")
capj = D("parks_capital_projects.json")
leaves_parks = D("leaves_parks.json")
leaves_pens = D("leaves_pensions.json")
leaves10 = D("leaves_over_10m.json")

EXPECTED = cents(park["meta"]["grand_total_2026"])
assert EXPECTED == cents(637580350)

PDF_URL = park["meta"]["source_pdf"]
BASE_SRC = {"doc": "Chicago Park District 2026 Budget Appropriations", "url": PDF_URL}


def src(page=None, printed=None, note=None, **kw):
    s = dict(BASE_SRC)
    if page is not None:
        s["page"] = page
    if printed is not None:
        s["printed_page"] = printed
    if note:
        s["note"] = note
    s.update(kw)
    return s


SRC_2025 = src(note="2025 budget column of the same printed tables")

# ---------------------------------------------------------------------------------------
# kid-friendly names
# ---------------------------------------------------------------------------------------
FUND_KID = {
    "Corporate Fund": "Everyday operating money (Corporate Fund)",
    "Special Recreation Activity Fund": "Special recreation money (Special Recreation Activity Fund)",
    "Liability Fund": "Insurance and claims money (Liability Fund)",
    "Capital Project Administration Fund": "Money for managing building projects (Capital Project Administration Fund)",
    "Operating Grants Fund": "Grant money (Operating Grants Fund)",
}
CLASS_KID = {
    "610000": "Pay, benefits and savings reserves",
    "620000": "Supplies",
    "621000": "Small tools and equipment",
    "623000": "Contracts, utilities and services",
    "624000": "Programs",
    "625000": "Other costs",
}
ACCT_KID = {
    "611005": "Pay for staff (salaries and wages)", "611010": "Staff share of health care costs",
    "611011": "Savings from jobs left unfilled (vacancy allowance)", "611020": "Overtime pay",
    "611025": "Staff pay covered by grants", "612004": "Flexible spending account benefits",
    "612005": "Health insurance for staff", "612006": "Dental insurance for staff",
    "612007": "Life insurance for staff", "612008": "Prescription drug coverage for staff",
    "612009": "Health coverage for retirees", "612013": "Prescription coverage for retirees",
    "612021": "Money set aside for raises", "613005": "Medicare tax (employer share)",
    "613007": "Social Security tax (employer share)", "613010": "Unemployment insurance costs",
    "620010": "Beach and pool supplies", "620015": "Books and magazines",
    "620020": "Building and maintenance supplies", "620030": "Cleaning supplies",
    "620035": "Plants and landscaping supplies", "620040": "Electrical supplies",
    "620045": "Recreation supplies", "620060": "Office supplies", "620065": "Staff uniforms",
    "620075": "General supplies", "620085": "Supplies bought with grants",
    "620090": "Cultural center materials", "620095": "Program uniforms",
    "621005": "Small electronics", "621010": "Small playground equipment",
    "621015": "Small equipment", "621020": "Small tools", "621035": "Equipment bought with grants",
    "623015": "Phones and communications", "623020": "Professional services (outside experts)",
    "623022": "Cultural center outside services", "623025": "Lawsuit and subpoena fees",
    "623030": "Trash and waste removal", "623035": "Dues and memberships", "623045": "Postage",
    "623050": "Equipment rental", "623055": "Repairs and maintenance",
    "623070": "Natural gas bills", "623075": "Electric bills", "623080": "Water and sewer bills",
    "623090": "Car allowance and fares", "623093": "Transportation services",
    "623095": "Incentive fees for venue managers", "623100": "Management fees",
    "623105": "Advertising for programs and events", "623120": "New program development",
    "623130": "General contracts and services", "623135": "Credit card processing fees",
    "623140": "Services paid for by grants", "623146": "Parking expenses", "623150": "Insurance",
    "623170": "Chicago Parks Foundation (grant)", "623175": "NeighborSpace (grant)",
    "623180": "Garfield Park Conservatory Alliance (grant)",
    "623185": "Grant Park Music Festival (grant)", "623190": "Staff training reserve",
    "623195": "Travel", "624005": "Special programs", "624010": "Recognition and awards",
    "624015": "Tournaments", "625005": "Lincoln Park Zoo", "625010": "Museums and aquarium",
    "625015": "Court judgments (lawsuit payouts)", "625020": "Regular yearly pension payment",
    "625023": "One-time extra pension payment", "625035": "Workers' compensation (job injury claims)",
    "625040": "Debt service expense", "625060": "Transfers between budgets",
    "625065": "Money moved to capital projects", "626020": "Printing and copying",
    "626025": "Landscaping contractors", "626075": "Vehicle fleet costs",
    "627012": "Building improvements", "627070": "Equipment purchases", "627075": "Art purchases",
    "627100": "Leased equipment purchases",
}
UNIT_KID = {
    # Administration & Finance
    "8110": "Board of Commissioners (the governing board)", "8130": "General Superintendent's office",
    "8170": "Chief of Staff's office", "8120": "Secretary's office (board records)",
    "8115": "Inspector General (the watchdog)", "8150": "Communications (news and public information)",
    "8610": "Disability Policy Office", "8220": "Human Resources (unit 8220)",
    "8225": "Human Resources (unit 8225)", "8620": "Workforce Development (training and jobs)",
    "8230": "Information Technology (computers and networks)", "8280": "Law Department (lawyers and claims)",
    "8630": "Prevention and Accountability (workplace conduct)",
    "8160": "Government and community relations", "8155": "Marketing",
    "8240": "Purchasing (buying supplies and contracts)", "9310": "Revenue (earning money for the District)",
    "8190": "Budget office", "8300": "Comptroller (bookkeeping and paying bills)",
    "8175": "Financial Services", "8600": "New Business Development (partnerships and new income)",
    "8210": "Treasury (cash and investments)",
    # Operations & Maintenance
    "8460": "Building care (Facilities Management)", "8485": "Skilled trades crews (Facilities Management, Specialty Trades)",
    "8370": "Park security (Park Public Safety)", "8260": "Construction managers for park projects (Capital Construction)",
    "8270": "Planning and design of park projects", "8450": "Nature and landscaping crews (Natural Resources)",
    "8455": "Districtwide groundskeeping (Natural Resources, Districtwide)",
    "8480": "Conservatories (indoor gardens)",
    # Recreation & Programming
    "8350": "Recreation office (Community Recreation, Administration)",
    "8430": "Swimming programs (Aquatics)", "8435": "Districtwide swimming programs (Aquatics, Districtwide)",
    "8410": "Sports leagues (Athletics)", "8423": "Teen programs (Teen Engagement)",
    "8420": "Gymnastics", "8500": "Sailing programs",
    "8445": "Programs for people with disabilities (Special Recreation)",
    "8255": "Special Olympics", "8425": "Fitness and wellness programs",
    "8360": "Arts, culture and nature programs", "8490": "Outdoor and environmental education",
    "8440": "Grant Park Music Festival (summer concerts)",
    "4001": "Central Region office", "3001": "North Region office", "7001": "South Region office",
}

# management-contract accounts that move to the "managed venues" box
VENUE_CODES = {"626005", "626010", "626015", "626030", "626035", "626040", "626045", "626050",
               "626055", "626060", "626065", "626066", "626067", "626070"}
VENUE_KID = {
    "626045": "Soldier Field", "626040": "Boat harbors", "626050": "Golf courses",
    "626060": "Maggie Daley Park", "626055": "McFetridge Sports Center",
    "626005": "Parking lots and garages", "626065": "Beverly/Morgan Park Sports Complex",
    "626066": "Addams Park Sports Center", "626067": "Gately Park",
    "626010": "MLK Center (ice skating)", "626015": "Ice skating rinks",
    "626030": "Cell tower and phone equipment sites", "626035": "Concession stands",
    "626070": "Thillens and BSDK fields",
}
# operators and contract numbers as published (research/park_district.md section 3.4)
VENUE_OPERATOR = {
    "626045": ("SMG (now ASM Global)", "P-12035"), "626040": ("Westrec SMI OpCo LLC", "P-14010"),
    "626050": ("Indigo Sports, L.L.C. (Troon)", "P-24001"), "626060": ("ASM Global", "P-24009"),
    "626055": ("SMG", "P-12035"), "626005": ("Standard Parking Corporation", "P-14012"),
    "626065": ("SMG", "P-15018"), "626066": ("ASM Global", "P-19021"),
    "626067": ("ASM Global", "P-19021"), "626010": ("Chicago Skating Partners LLC", "P-25008"),
    "626015": ("Westrec SMI OpCo", "P-23010 and P-25021"), "626030": ("SPAAN Tech Inc", "P-25001"),
    "626035": ("UCG Associates, then Unison Consulting", "P-20011"),
}

# ---------------------------------------------------------------------------------------
# why-can't-I-go-deeper sentences (reused from the data files)
# ---------------------------------------------------------------------------------------
WHY = {}
for x in leaves10["leaves"]:
    if x.get("budget") != "Parks" or not x.get("why_cant_go_deeper"):
        continue
    codes = re.findall(r"\b(\d{6})\b", x["path"])
    if codes:
        WHY[codes[-1]] = x["why_cant_go_deeper"]
for x in leaves_parks["leaves"]:
    WHY.setdefault(x["match_path_contains"][0], x["why_cant_go_deeper"])
for need in ("625020", "626045", "626040", "623080", "623075", "600015"):
    assert need in WHY, need

# ---------------------------------------------------------------------------------------
# bookkeeping
# ---------------------------------------------------------------------------------------
A25 = {}            # node id -> 2025 budget (cents), explicit from the PDF
ACCT_NODES = {}     # account code -> [nodes]
VENUES = []         # accounts moved to the venues box
REGION_25 = {}      # region node id -> printed 2025 total (cents)


def reg_acct(code, node):
    ACCT_NODES.setdefault(code, []).append(node)


def tag_rounding(made, npieces, node, label, what):
    """Rename the visible difference child created by split() for PDF rounding."""
    if len(made) > npieces:
        r = made[-1]
        diff = r.amount
        r.name = label
        r.basis = "adjustment" if abs(diff) <= 1000 else "residual"  # cents: $10 or less is PDF rounding
        r.note = (f"{what}: the printed lines add to ${(node.amount - diff) / 100:,.2f} and the printed "
                  f"total is ${node.amount / 100:,.2f}.")
        r.kind = "rounding"
        r.why = None
        if r.basis == "residual":
            r.name = "Salary dollars not listed by job title"
            r.kind = "residual"
        return r
    return None


def acc_list(fund):
    out = []
    for c in fund["children"]:
        if c["type"] == "class":
            out.extend(c.get("children") or [c])
        else:
            out.append(c)
    return out


def class_of(fund, acct):
    for c in fund["children"]:
        if c["type"] == "class" and acct in (c.get("children") or []):
            return c["name"]
    return None


def add_fund(parent, f, unit, unit_node):
    """Fund node with account leaves (and job titles under salaries). Venue accounts move out."""
    pieces, srcs = [], []
    moved26 = moved25 = 0
    for a in acc_list(f):
        code = a.get("code")
        a26, a25 = a["amount2026"], a["amount2025"]
        if code in VENUE_CODES:
            if a26 or a25:
                VENUES.append({"a": a, "fund": f["name"], "unit": unit, "node": unit_node})
            moved26 += a26
            moved25 += a25
            continue
        if a26 == 0 and a25 == 0:
            continue
        key = code or "rounding"
        kid = ACCT_KID.get(code, a["name"])
        pieces.append({"key": key, "name": kid, "amount": cents(a26), "kind": "account",
                       "extra": {"official_name": a["name"], "account_code": code,
                                 "spending_class": class_of(f, a)}})
        srcs.append(a)
    fund_amt = cents(f["amount2026"] - moved26)
    f25 = f["amount2025"] - moved25
    if fund_amt == 0 and not pieces and f25 == 0:
        return None
    fn = parent.add(f["name"], FUND_KID.get(f["name"], f["name"]), amount=fund_amt, kind="fund",
                    extra={"official_name": f["name"]}, source=src(f.get("page"), f.get("printed_page")))
    A25[fn.id] = cents(f25)
    made = split(fn, pieces, allow_over=True)
    tag_rounding(made, len(pieces), fn, "Rounding in the printed budget",
                 "Rounding in the printed tables")
    keys = [p["key"] for p in pieces]
    assert len(keys) == len(set(keys)), (fn.id, keys)
    for node, a in zip(made, srcs):
        A25[node.id] = cents(a["amount2025"])
        reg_acct(a.get("code"), node)
        if a.get("children"):
            pp = []
            for i, p in enumerate(a["children"]):
                if p["amount2026"] == 0 and p["amount2025"] == 0:
                    continue
                fte = p.get("fte2026") or 0
                pp.append({"key": f"{p.get('job_code')}-{i}", "name": p["name"],
                           "amount": cents(p["amount2026"]), "kind": "position",
                           "count": fte if fte else None,
                           "unit_amount": (round(cents(p["amount2026"]) / fte) if fte else None),
                           "unit_label": "full-time equivalents" if fte else None,
                           "extra": {"official_name": p["name"], "job_code": p.get("job_code"),
                                     "fte_2025": p.get("fte2025")},
                           "_a25": cents(p["amount2025"])})
            a25s = [x.pop("_a25") for x in pp]
            mm = split(node, pp, allow_over=True)
            tag_rounding(mm, len(pp), node, "Rounding in the printed job list",
                         "The job-title table")
            for cn, v in zip(mm, a25s):
                A25[cn.id] = v
            for cn in mm[:len(pp)]:
                if cn.amount >= 10_000_000_00 and not cn.why:
                    cn.why = (f"The budget prints one pay line for all {cn.count:g} full-time-equivalent "
                              f"{cn.name.lower()} positions in this department, and it does not publish individual pay.")
    return fn


def add_unit(parent, u, key=None, kid=None, kind="department", extra=None):
    code = u.get("unit_code")
    ex = {"official_name": u["name"], "unit_code": code, "printed_total_cents": cents(u["amount2026"])}
    if extra:
        ex.update(extra)
    node = parent.add(key or f"{u['name']}-{code}", kid or UNIT_KID.get(code, u["name"]), kind=kind,
                      extra=ex, source=src(u.get("page"), u.get("printed_page")))
    for f in u["children"]:
        add_fund(node, f, u, node)
    if not node.children:
        parent.children.remove(node)
        return None
    moved25 = sum(cents(v["a"]["amount2025"]) for v in VENUES if v["unit"] is u)
    A25[node.id] = cents(u["amount2025"]) - moved25
    return node


# ---------------------------------------------------------------------------------------
# root
# ---------------------------------------------------------------------------------------
tree = park["tree"]
FN = {c["id"]: c for c in tree["children"]}
root = Node("parks", "Chicago Park District", gov="parks", basis="budget", kind="government",
            source=src(note="Appropriation ordinance and budget tables for fiscal year 2026"),
            extra={"official_name": "Chicago Park District FY2026 Operating Budget",
                   "printed_grand_total_cents": EXPECTED,
                   "printed_net_appropriation_cents": cents(park["meta"]["net_appropriation_2026"]),
                   "internal_service_earnings_cents": cents(park["meta"]["internal_service_earnings_2026"]),
                   "fiscal_year": 2026})
root.note = ("The $637.6M is the printed Grand Total of all funds. The District's 'net appropriation' of "
             "$631,880,350 is the same total less $5,700,000 of internal service earnings.")

# DA summary typo (documented in research/park_district.md)
da = next(x for x in park["reconciliation"]["pdf_inconsistencies"]
          if x.get("where", "").startswith("p76-77 District Administration Summary"))
root.extra["district_administration_summary"] = {
    "printed_total_cents": cents(da["printed_total"]),
    "class_lines_sum_cents": cents(da["class_sum"]),
    "difference_cents": cents(da["diff"]),
    "followed": "line items (the class lines tie to the Grand Total, so the printed total looks like a typo)",
    "page": "PDF p76-77",
}
assert da["diff"] == 150000

# ---------------------------------------------------------------------------------------
# 1. Parks and recreation
# ---------------------------------------------------------------------------------------
parks_box = root.add("parks-and-recreation", "Parks and recreation", kind="box",
                     note="Neighborhood parks grouped by region, plus districtwide recreation programs "
                          "and the Grant Park Music Festival.",
                     extra={"official_name": "Neighborhood Parks by Region + Recreation & Programming + Grant Park Music Festival"})
for reg in FN["cpd/parks-by-region"]["children"]:
    n_parks = sum(1 for c in reg["children"] if c["type"] == "park")
    rn = parks_box.add(reg["name"], f"{reg['name']} ({n_parks} parks)", kind="region",
                       extra={"official_name": reg["name"], "n_parks": n_parks,
                              "printed_region_summary_total_cents": cents(reg["printed_region_summary_total2026"])},
                       source=src(note="Region pages of the budget"))
    REGION_25[rn.id] = cents(reg["amount2025"])
    for c in reg["children"]:
        if c["type"] == "park":
            code = c["unit_code"]
            node = add_unit(rn, c, key=f"{c['name']}-{code}", kid=f"{c['name']} (park {code})", kind="park",
                            extra={"park_number": code, "region": reg["name"]})
        else:
            add_unit(rn, c, key=f"{c['name']}-{c['unit_code']}", kind="department")
rec_box = parks_box.add("districtwide-recreation-programs", "Districtwide recreation programs", kind="group",
                        extra={"official_name": "Recreation & Programming (Districtwide Programs)"},
                        note="Programs run for the whole city rather than at one park.")
for u in FN["cpd/recreation-programming"]["children"]:
    add_unit(rec_box, u, kind="department")
for u in FN["cpd/grant-park-music-festival"]["children"]:
    add_unit(parks_box, u, kind="department")

# ---------------------------------------------------------------------------------------
# 2. Maintaining the parks, 3. Running the District
# ---------------------------------------------------------------------------------------
om_box = root.add("maintaining-the-parks", "Maintaining the parks", kind="box",
                  extra={"official_name": "Operations & Maintenance"},
                  note="Crews that fix buildings, care for nature and landscaping, and keep parks safe.")
for u in FN["cpd/operations-maintenance"]["children"]:
    add_unit(om_box, u)
run_box = root.add("running-the-district", "Running the District", kind="box",
                   extra={"official_name": "Administration & Finance"},
                   note="Offices that hire, buy, count the money, handle lawsuits and run computers. "
                        "The management contracts for venues that sit in the Revenue department are shown "
                        "separately under Soldier Field, harbors, golf and other managed venues.")
run_box.extra["district_administration_summary"] = root.extra["district_administration_summary"]
run_box.note += (" The printed District Administration summary total is $150,000 above its own class lines. "
                 "This tree follows the line items.")
for u in FN["cpd/administration-finance"]["children"]:
    add_unit(run_box, u)

# ---------------------------------------------------------------------------------------
# Finance General: route accounts
# ---------------------------------------------------------------------------------------
fg = FN["cpd/finance-general"]
fg_src = src(fg.get("page"), fg.get("printed_page"), note="Finance General (all funds)")
FG_ACCT = {a["code"]: a for cl in fg["children"] for a in cl["children"]}
ROUTED = {"600005", "600015", "625020", "625023", "625005", "625010", "625065"}

shared = root.add("utilities-benefits-and-shared-costs", "Utilities, benefits and other shared costs", kind="box",
                  extra={"official_name": "Finance General (costs not routed to the boxes below)"},
                  source=fg_src,
                  note="Bills and reserves that belong to the whole District instead of one department. "
                       "Debt, pensions, museums, the zoo and capital transfers are shown in their own boxes.")
for cl in fg["children"]:
    pieces, srcs = [], []
    m26 = m25 = 0
    for a in cl["children"]:
        if a["code"] in ROUTED:
            m26 += a["amount2026"]
            m25 += a["amount2025"]
            continue
        if a["amount2026"] == 0 and a["amount2025"] == 0:
            continue
        pieces.append({"key": a["code"], "name": ACCT_KID.get(a["code"], a["name"]),
                       "amount": cents(a["amount2026"]), "kind": "account",
                       "extra": {"official_name": a["name"], "account_code": a["code"]}})
        srcs.append(a)
    if not pieces:
        continue
    cn = shared.add(cl["code"], CLASS_KID[cl["code"]], amount=cents(cl["amount2026"] - m26), kind="group",
                    extra={"official_name": cl["name"], "class_code": cl["code"]})
    A25[cn.id] = cents(cl["amount2025"] - m25)
    made = split(cn, pieces, allow_over=True)
    tag_rounding(made, len(pieces), cn, "Rounding in the printed budget", "Rounding in the printed tables")
    for node, a in zip(made, srcs):
        A25[node.id] = cents(a["amount2025"])
        reg_acct(a["code"], node)
        if a["code"] == "611011":
            node.basis = "adjustment"
            node.note = ("A budgeted offset: the District assumes some jobs will sit empty during the year, "
                         "so it subtracts this amount from pay.")
        if node.amount >= 10_000_000_00 and node.amount > 0:
            node.why = WHY[a["code"]]

# ---------------------------------------------------------------------------------------
# Retirement (pensions)
# ---------------------------------------------------------------------------------------
pen_src = src(252, 246, note="Appropriation C (pension) in the ordinance, PDF p252",
              valuation="Segal actuarial valuation as of 12/31/2025, Park Employees' Annuity and Benefit Fund")
pension_box = root.add("retirement-pensions", "Retirement (pensions)", kind="box", source=pen_src,
                       extra={"official_name": "Park Employees' Annuity and Benefit Fund contribution"},
                       note="The District pays into a pension fund for its workers. The fund pays the retirees.")
a20, a23 = FG_ACCT["625020"], FG_ACCT["625023"]
reg_pay = pension_box.add("regular-yearly-payment", "Regular yearly pension payment", amount=cents(a20["amount2026"]),
                          kind="account", extra={"official_name": a20["name"], "account_code": "625020"})
A25[reg_pay.id] = cents(a20["amount2025"])
pen_leaf = next(x for x in leaves_pens["leaves"] if x["match_path_contains"] == ["Parks", "625020"])
nc = pen_leaf["pieces"][0]
assert nc["name"] == "Employer normal cost" and pen_leaf["amount"] == a20["amount2026"]
made = split(reg_pay, [{"key": "employer-normal-cost",
                        "name": "Cost of benefits workers earn this year (employer normal cost)",
                        "amount": cents(nc["amount"]), "basis": "proxy", "kind": "account",
                        "note": "Estimate: normal cost from the fund's 12/31/2025 actuarial valuation, applied to the "
                                "budgeted payment. " + pen_leaf["split_basis"],
                        "source": src(note=nc["source"])}],
             residual_name="Paying down the pension shortfall (budget payment minus normal cost)",
             residual_note="Derived: the budgeted payment minus the employer normal cost. " + pen_leaf["split_basis"],
             residual_why=WHY["625020"])
assert made[1].amount == cents(pen_leaf["pieces"][1]["amount"])
supp = pension_box.add("one-time-extra-payment", "One-time extra payment (from surplus TIF money)",
                       amount=cents(a23["amount2026"]), kind="account",
                       extra={"official_name": a23["name"], "account_code": "625023"})
A25[supp.id] = cents(a23["amount2025"])
reg_acct("625020", reg_pay)
reg_acct("625023", supp)

# ---------------------------------------------------------------------------------------
# Paying back loans (25 bond series)
# ---------------------------------------------------------------------------------------
debt_j = park["beyond_operating"]["debt"]
ser = debt_j["ordinance_appropriation_M_by_bond_series_2026"]
debt_src = src(253, 247, note="Appropriation M (bond series) in the ordinance, PDF p253")
a5, a15 = FG_ACCT["600005"], FG_ACCT["600015"]
debt_box = root.add("paying-back-loans", "Paying back loans", kind="box", source=debt_src,
                    amount=cents(a5["amount2026"] + a15["amount2026"]),
                    extra={"official_name": "Debt service (accounts 600005 interest + 600015 principal)",
                           "interest_line_cents": cents(a5["amount2026"]),
                           "principal_line_cents": cents(a15["amount2026"])},
                    note="Money borrowed to build parks earlier is paid back each year: part loan, part interest.")
A25[debt_box.id] = cents(a5["amount2025"] + a15["amount2025"])


def series_kid(name):
    m = re.search(r"Series (\d{4}[A-Z](?:-\d)?)", name)
    s = m.group(1) if m else None
    if "Future Issuance" in name:
        return "Planned future borrowing (not yet issued)", None
    refi = "Refunding" in name
    kind = "refinancing loan" if refi else ("park-improvement loan" if "Park Bonds" in name else "harbor loan")
    back = None
    if "PPRT" in name:
        back = "backed by replacement tax money"
    elif "SRA" in name:
        back = "backed by the special recreation tax"
    elif "Harbor" in name:
        back = "backed by harbor income"
    return f"Series {s}: {kind}" + (f" ({back})" if back else ""), s


pieces = []
for r in ser["rows"]:
    kid, s = series_kid(r["name"])
    tot = cents(r["total"])
    if tot == 0:
        continue
    pieces.append({"key": s or "future-issuance", "name": kid, "amount": tot, "kind": "bond_series",
                   "extra": {"official_name": r["name"], "series": s, "principal_cents": cents(r["principal"]),
                             "interest_cents": cents(r["interest"])},
                   "why": WHY["600015"] if tot >= 10_000_000_00 else None})
assert abs(sum(p["amount"] for p in pieces) - cents(ser["total"]["total"])) <= 100  # PDF rounding of $1
n_series = sum(1 for p in pieces if p["key"] != "future-issuance")
assert n_series == 25, n_series
made = split(debt_box, pieces, residual_name="Interest paid outside the bond schedule",
             residual_note=(debt_j["ordinance_vs_operating_note"] + " The 25 series rows add to $1 more than the printed "
                            "schedule total (PDF rounding), so this line is $1,099,999 instead of $1,100,000."),
             residual_basis="residual")
assert abs(made[-1].amount - 110_000_000) <= 100 and made[-1].id.endswith("other-not-itemised")

# ---------------------------------------------------------------------------------------
# Museums and the zoo
# ---------------------------------------------------------------------------------------
mus_src = src(252, 246, note="Appropriation F (Aquarium and Museum Operating Fund) in the ordinance, PDF p252")
mus_box = root.add("museums-and-the-zoo", "Museums and the zoo", kind="box", source=mus_src,
                   extra={"official_name": "Remittances to Zoo, Aquarium and Museums (625005, 625010)"},
                   note="The District sends tax money to Lincoln Park Zoo and to 11 museums and the Shedd Aquarium "
                        "that sit on park land.")
a_zoo, a_mus = FG_ACCT["625005"], FG_ACCT["625010"]
zoo = mus_box.add("lincoln-park-zoo", "Lincoln Park Zoo", amount=cents(a_zoo["amount2026"]), kind="institution",
                  extra={"official_name": "Remittance To Zoo", "account_code": "625005"})
A25[zoo.id] = cents(a_zoo["amount2025"])
reg_acct("625005", zoo)
mus = mus_box.add("museums-and-aquarium", "Museums and aquarium (11 institutions)", amount=cents(a_mus["amount2026"]),
                  kind="group", extra={"official_name": a_mus["name"], "account_code": "625010"})
A25[mus.id] = cents(a_mus["amount2025"])
mleaf = next(x for x in leaves_parks["leaves"] if x["match_path_contains"] == ["625010"])
assert mleaf["amount"] == a_mus["amount2026"]
mp = [{"key": p["name"], "name": p["name"], "amount": cents(p["amount"]), "basis": p["basis"], "kind": "institution",
       "extra": {"official_name": p["name"]}} for p in mleaf["pieces"]]
split(mus, mp)
assert len(mus.children) == 11

# ---------------------------------------------------------------------------------------
# Building and fixing parks (capital)
# ---------------------------------------------------------------------------------------
cap_src = src(note="Finance General account 625065 and the Capital Improvement Plan 2026-2030 (PDF p69)")
cap_box = root.add("building-and-fixing-parks", "Building and fixing parks (capital)", kind="box", source=cap_src,
                   extra={"official_name": "Transfer to Capital Projects (625065) and the Capital Improvement Plan"},
                   note=("Only the operating money moved into the building fund counts in the total. The side panels "
                         "list capital project dollars from other public records. They use different bases and "
                         "overlap (a TIF line, its agreement and its construction contract can be the same project), "
                         "so do not add them up."))
a65 = FG_ACCT["625065"]
tr = cap_box.add("operating-money-moved-to-capital", "Operating money moved to capital projects",
                 amount=cents(a65["amount2026"]), kind="account",
                 extra={"official_name": a65["name"], "account_code": "625065"})
A25[tr.id] = cents(a65["amount2025"])
cleaf = next(x for x in leaves_parks["leaves"] if x["match_path_contains"] == ["625065"])
assert cleaf["amount"] == a65["amount2026"]
cp = [{"key": p["name"], "name": p["name"], "amount": cents(p["amount"]), "basis": "tied", "kind": "account",
       "note": cleaf["split_basis"]} for p in cleaf["pieces"][:2]]
mm = split(tr, cp, residual_name=cleaf["pieces"][2]["name"], residual_note=cleaf["split_basis"])
assert mm[-1].amount == cents(cleaf["pieces"][2]["amount"])
reg_acct("625065", tr)

# ---------------------------------------------------------------------------------------
# Managed venues (all 626xxx management contracts, wherever the budget lists them)
# ---------------------------------------------------------------------------------------
ven_box = root.add("managed-venues", "Soldier Field, harbors, golf and other managed venues", kind="box",
                   extra={"official_name": "Management contract accounts 626005 to 626070"},
                   note=("The District pays private companies to run these places. The budget lists one line per "
                         "contract. Three of the lines (Maggie Daley, McFetridge, Gately) sit on park pages in the "
                         "printed budget and are shown here so every venue is in one place."))
VEN_NODE = {}
for v in sorted(VENUES, key=lambda v: -v["a"]["amount2026"]):
    a = v["a"]
    code = a["code"]
    op = VENUE_OPERATOR.get(code)
    is_park = v["unit"].get("unit_code") in ("1303", "0189", "0244") and v["node"].kind == "park"
    where = f"{v['unit']['name']} ({v['unit'].get('unit_code')}), {v['fund']}"
    node = ven_box.add(code, VENUE_KID.get(code, a["name"]), amount=cents(a["amount2026"]), kind="venue",
                       source=src(v["unit"].get("page"), v["unit"].get("printed_page")),
                       extra={"official_name": a["name"], "account_code": code, "listed_under": where,
                              "operator": op[0] if op else None, "contract": op[1] if op else None},
                       note=(f"Run by {op[0]} under contract {op[1]}. " if op else "") +
                            f"Listed in the printed budget under {where}.")
    if node.amount >= 10_000_000_00:
        node.why = WHY[code]
    A25[node.id] = cents(a["amount2025"])
    VEN_NODE[code] = node
    reg_acct(code, node)
    if is_park:
        v["node"].extra["moved_to_venues_cents"] = v["node"].extra.get("moved_to_venues_cents", 0) + node.amount
        v["node"].note = ((v["node"].note or "") + f" The {node.name} management contract "
                          f"(${node.amount / 100:,.0f}) is shown under managed venues, not here.").strip()
assert set(VEN_NODE) <= VENUE_CODES

# ---------------------------------------------------------------------------------------
# Not itemised on any department page
# ---------------------------------------------------------------------------------------
un = FN["cpd/unitemized"]
un_box = root.add("not-itemised", "Not itemised on any department page", kind="box", basis="residual",
                  amount=cents(un["amount2026"]),
                  extra={"official_name": un["name"], "reconciling_item": True},
                  source=src(note="Districtwide Summary (PDF pp98-99) and all-funds account table (pp62-63)"),
                  note=un["note"])
pieces, srcs = [], []
for a in un["children"]:
    if a["amount2026"] == 0 and a["amount2025"] == 0:
        continue
    code = a.get("code")
    pieces.append({"key": code or "rounding", "name": ACCT_KID.get(code, a["name"]), "amount": cents(a["amount2026"]),
                   "kind": "account", "extra": {"official_name": a["name"], "account_code": code}})
    srcs.append(a)
made = split(un_box, pieces, allow_over=True)
for node, a in zip(made, srcs):
    A25[node.id] = cents(a["amount2025"])
tag_rounding(made, len(pieces), un_box, "Rounding in the printed budget", "Rounding in the printed tables")

ORDER = ["parks-and-recreation", "maintaining-the-parks", "running-the-district", "retirement-pensions",
         "paying-back-loans", "managed-venues", "museums-and-the-zoo", "utilities-benefits-and-shared-costs",
         "building-and-fixing-parks", "not-itemised"]
root.children.sort(key=lambda c: ORDER.index(c.id.split(".", 1)[1]))

# ---------------------------------------------------------------------------------------
# SIDE INFO
# ---------------------------------------------------------------------------------------
VSRC = {"doc": "Chicago Park District Ethics Ordinance vendor payment lists (2019-2022)",
        "url": vend["meta"]["source_page"], "files": vend["meta"]["source_urls"]}
YEARS = ["2019", "2020", "2021", "2022"]
GROUPS = {tuple(g["accounts"]): g for g in vend["mapping_groups"]}


def one_node(code):
    ns = [n for n in ACCT_NODES.get(code, []) if n.amount]
    assert len(ns) == 1, (code, [n.id for n in ns])
    return ns[0]


def year_label(name, y):
    return f"{name}: paid in {y} (latest published)" if y == "2022" else f"{name}: paid in {y} (earlier published list)"


def attach_group(node, accounts, covers=(), strength="A", label=None):
    g = GROUPS[tuple(accounts)]
    n_payees = len(g["payees"])
    pname = label or (g["payees"][0]["payee"] if n_payees == 1 else "payees matched to this line")
    for y in YEARS:
        amt = cents(g["paid_by_year"][y])
        if amt == 0:
            continue
        note = ("Cash paid by the District's accounting system in calendar year %s, all funds. Not 2026 spending." % y)
        if strength == "B":
            note += " The payee was matched to this budget line by type of payee only."
        node.side.append({
            "kind": "vendor_payment", "label": year_label(pname, y), "amount": amt, "period": y,
            "basis": "actual", "source": VSRC, "note": note,
            "covers_budget_accounts": list(accounts), "also_covers_nodes": [c.id for c in covers],
            "payees": {p["payee"]: cents(p["paid_by_year"][y]) for p in g["payees"] if p["paid_by_year"][y]},
            "mapping_strength": strength, "budget_2026_group_cents": cents(g["budget2026"]),
        })


V = VEN_NODE
attach_group(V["626045"], ["626045", "626055", "626065"], covers=[V["626055"], V["626065"]], label="SMG")
attach_group(V["626040"], ["626040", "626015"], covers=[V["626015"]], label="Westrec (harbors and ice rinks)")
attach_group(V["626050"], ["626050"])
attach_group(V["626010"], ["626010"])
attach_group(V["626005"], ["626005"], label="Standard Parking / SP Plus")
attach_group(V["626030"], ["626030"])
attach_group(V["626035"], ["626035"])
attach_group(V["626060"], ["626060"], strength="B")
attach_group(one_node("623030"), ["623030"])
attach_group(one_node("625035"), ["625035"])
attach_group(one_node("625005"), ["625005"])
attach_group(one_node("623185"), ["623185"])
attach_group(one_node("623170"), ["623170"])
attach_group(one_node("623175"), ["623175"])
attach_group(one_node("623180"), ["623180"])
attach_group(one_node("626025"), ["626025"], strength="B", label="landscaping companies")
attach_group(one_node("623075"), ["623070", "623075"], covers=[one_node("623070")], strength="B",
             label="gas and electric suppliers")
attach_group(one_node("626075"), ["626075"], strength="B", label="fleet leasing companies")
attach_group(pension_box, ["625020", "625023"], covers=[reg_pay, supp], label="Park Employees A&B Fund")
for sd in pension_box.side:
    if sd["kind"] == "vendor_payment":
        sd["note"] += " This is a pension contribution, not vendor spending."
# museums: one payee each
MUSEUM_PAYEE = {
    "Museum of Science and Industry": "MUSEUM OF SCIENCE & INDUSTRY",
    "Field Museum of Natural History": "FIELD MUSEUM OF NATURAL HISTORY",
    "Art Institute of Chicago": "THE  ART INSTITUTE OF CHICAGO",
    "John G. Shedd Aquarium": "SHEDD AQUARIUM SOCIETY",
    "Chicago History Museum": "CHICAGO HISTORICAL SOCIETY",
    "Peggy Notebaert Nature Museum (Chicago Academy of Sciences)": "CHICAGO ACADEMY OF SCIENCES",
    "Adler Planetarium": "ADLER PLANETARIUM",
    "DuSable Museum of African American History": "DUSABLE MUSEUM",
    "National Museum of Mexican Art": "NATIONAL MUSEUM OF MEXICAN ART",
    "Museum of Contemporary Art": "MUSEUM OF CONTEMPORARY ART",
    "Institute of Puerto Rican Arts and Culture (IPRAC)": "INSTITUTE  OF PUERTO RICAN  ARTS & CULTURE",
}
mus_payees = {p["payee"]: p for p in GROUPS[("625010",)]["payees"]}
for c in mus.children:
    pn = MUSEUM_PAYEE[c.extra["official_name"]]
    p = mus_payees[pn]
    for y in YEARS:
        amt = cents(p["paid_by_year"][y])
        if amt:
            c.side.append({"kind": "vendor_payment", "label": year_label(pn.replace("  ", " ").title(), y),
                           "amount": amt, "period": y, "basis": "actual", "source": VSRC,
                           "note": f"Cash paid in calendar year {y}. Not 2026 spending.", "payees": {pn: amt}})

# contract fee schedules from Board exhibits (terms, not payments)
for fs in vend["contract_fee_schedules_from_board_exhibits"]:
    tgt = V["626060"] if "Maggie Daley" in fs["asset"] else (V["626050"] if "Golf" in fs["asset"] else None)
    if tgt is None:
        continue
    fee = fs["management_fee_by_year"].get("2026")
    if fee:
        tgt.side.append({"kind": "contract_fee_schedule",
                         "label": f"Management fee in the contract {fs['contract']} for 2026 (a contract term, not a payment)",
                         "amount": cents(fee), "period": "2026", "basis": "contract", "source":
                         {"doc": f"Board action {fs['board_action']}", "url": fs["url"]},
                         "note": "The fee is only part of the budget line. The public files do not say how the rest splits."})

# pension fund context
PV = {"doc": "Segal actuarial valuation as of 12/31/2025, Park Employees' Annuity and Benefit Fund",
      "url": "https://www.chicagoparkpension.org/wp-content/uploads/2026/06/Park-Employees-Annuity-and-Benefit-Fund-of-Chicago_Actuarial-Valuation-Report-as-of-12.31.2025.pdf"}
pension_box.side.append({"kind": "pension_context", "label": "Fund's unfunded liability at 12/31/2025",
                         "amount": cents(903648276), "period": "2025-12-31", "basis": "actuarial", "source": PV})
pension_box.side.append({"kind": "pension_context",
                         "label": "Contribution the fund's own policy calls for in 2026 (the statute sets a lower payment)",
                         "amount": cents(88904199), "period": "2026", "basis": "actuarial", "source": PV})
pension_box.side.append({"kind": "pension_context", "label": "Share of the fund's promises covered by its assets (33.2 percent)",
                         "amount": None, "period": "2025-12-31", "basis": "actuarial", "source": PV})
pension_box.side[-1].pop("amount")
pension_box.side[-1]["ratio"] = 0.332

# ---- capital side info
CS = capj["meta"]["sources"]
cip = capj["cip_2026_2030_totals"]
cap_box.side.append({"kind": "capital_plan", "label": "Capital Improvement Plan 2026-2030, all sources",
                     "amount": cents(cip["total_sources"]["total_2026_2030"]), "period": "2026-2030", "basis": "plan",
                     "source": src(69, 63, note="Capital Improvement Plan table")})
for sname, row in cip["by_source"].items():
    if row["total_2026_2030"]:
        cap_box.side.append({"kind": "capital_plan", "label": f"Capital plan 2026-2030 funding: {sname}",
                             "amount": cents(row["total_2026_2030"]), "period": "2026-2030", "basis": "plan",
                             "source": src(69, 63, note="Capital Improvement Plan table")})
for k in park["beyond_operating"]["capital"]["ordinance_capital_appropriations_2026"]:
    if k["total"]:
        cap_box.side.append({"kind": "capital_appropriation", "label": f"2026 capital appropriation: {k['name']}",
                             "amount": cents(k["total"]), "period": "2026", "basis": "appropriation",
                             "source": src(k["page"], k["printed_page"], note=f"Ordinance Appropriation {k['letter']}")})
for ln in capj["tif_cip_lines"]:
    tot = ln.get("total_2026_2030") or 0
    if tot <= 0:
        continue
    cap_box.side.append({"kind": "capital_project_tif", "label": f"TIF plan: {ln['line']} ({ln['tif_district']})",
                         "amount": cents(tot), "period": "2026-2030", "basis": "projection",
                         "source": {"doc": "City TIF Projections 2025-2034", "url": CS["tif_projections"]},
                         "park_number": ln.get("park_no"), "park_name": ln.get("park_name"),
                         "by_year": {y: cents(v) for y, v in ln["by_year"].items() if v},
                         "note": "The City's planned TIF cash by year (Oct 2025), not the Park District's project budget."})
for ig in capj["tif_iga_approvals"]:
    if (ig.get("cdc_date") or "") < "2021" or not ig.get("approved_tif"):
        continue
    row = {"kind": "capital_project_tif_agreement", "label": f"TIF agreement approved {ig['cdc_date']}: {ig['project']}",
           "amount": cents(ig["approved_tif"]), "period": ig["cdc_date"], "basis": "approved",
           "source": {"doc": "City TIF agreements list", "url": CS["tif_agreements"]},
           "park_number": ig.get("park_no"), "tif_district": ig.get("tif_district")}
    if ig.get("total_project_cost"):
        row["total_project_cost_cents"] = cents(ig["total_project_cost"])
    cap_box.side.append(row)
for fp in capj["featured_project_budgets"]:
    cap_box.side.append({"kind": "capital_project_budget", "label": f"Stated project budget: {fp['project']}",
                         "amount": cents(fp["amount"]), "period": fp.get("status"), "basis": "stated",
                         "source": {"doc": "Park District featured capital projects page", "url": fp["source"]},
                         "park_number": fp.get("park_no")})
for b in capj["bonfire_capital_contracts"]:
    if b.get("value"):
        cap_box.side.append({"kind": "capital_contract", "label": f"Contract {b['spec']}: {b['name']} ({b['vendor']})",
                             "amount": cents(b["value"]), "period": b.get("term_start"), "basis": "contract_value",
                             "source": {"doc": "Park District public contracts library (Bonfire)", "url": b["url"]},
                             "park_number": b.get("park_no")})
for ba in capj["board_awards"]:
    amt = ba.get("amount_in_title") or ba.get("implied_price_from_mwbe_schedule")
    if not amt:
        continue
    cap_box.side.append({"kind": "capital_board_award", "label": f"Board action {ba['file']}: {ba['title'][:140]}",
                         "amount": cents(amt), "period": ba.get("date"),
                         "basis": "stated" if ba.get("amount_in_title") else "implied",
                         "source": {"doc": "Board of Commissioners record", "url": ba["legistar_url"]},
                         "note": ("Amount printed in the title." if ba.get("amount_in_title") else
                                  "Implied from the minority-subcontractor schedule (dollars divided by percent), "
                                  "accurate to about 7 percent. Not an announced award."),
                         "park_number": ba.get("park_no")})
for og in capj["grants_state_oslad"]:
    cap_box.side.append({"kind": "capital_grant", "label": f"State OSLAD park grant: {og['project']}",
                         "amount": cents(og["amount"]), "period": og["source"][-10:], "basis": "award",
                         "source": {"doc": og["source"], "url": og["url"]}, "park_number": og.get("park_no")})
for fg_ in capj["grants_federal_usaspending"]:
    if (fg_.get("start") or "") >= "2021" and "Commun" in fg_["agency"]:
        cap_box.side.append({"kind": "capital_grant", "label": "Federal HUD community project funding (parks not named)",
                             "amount": cents(fg_["amount"]), "period": fg_["start"], "basis": "award",
                             "source": {"doc": "USAspending", "url": fg_["url"]}})
am = capj["aldermanic_menu_park_district_2026"]
cap_box.side.append({"kind": "capital_aldermanic", "label": f"Aldermanic menu money for {len(am)} Park District projects (2026)",
                     "amount": cents(sum(x["amount"] for x in am)), "period": "2026", "basis": "approved",
                     "source": {"doc": "City aldermanic menu Q2 2026"}})

# ---- 2025 budget on every node that has it
computed = set()


def prior_walk(n):
    # bottom-up with computed flag
    for c in n.children:
        prior_walk(c)
    if n.id not in A25 and n.children and all(c.id in A25 for c in n.children):
        A25[n.id] = sum(A25[c.id] for c in n.children)
        computed.add(n.id)


for rid, v in REGION_25.items():
    rn_ = next(n for n in root.walk() if n.id == rid)
    mv = sum(cents(x["a"]["amount2025"]) for x in VENUES if x["node"].parent is rn_)
    A25[rid] = v - mv
A25[un_box.id] = cents(un["amount2025"])
prior_walk(root)
for n in root.walk():
    if n.id in A25:
        n.side.append({"kind": "prior_year_budget",
                       "label": "2025 budget" + (" (sum of the lines inside)" if n.id in computed else ""),
                       "amount": A25[n.id], "period": "2025", "basis": "budget", "source": SRC_2025})

# ---------------------------------------------------------------------------------------
# CHECKS
# ---------------------------------------------------------------------------------------
problems = check(root, expected_total_cents=EXPECTED)
# top-level amounts that should tie to the printed function totals
FUNC_TOT = {c["id"]: cents(c["amount2026"]) for c in tree["children"]}
# actual payments must never sit inside amounts: side only
for n in root.walk():
    if n.eff("basis") == "actual":
        problems.append(f"actual basis inside totals at {n.id}")
# 25 bond series
if sum(1 for n in root.walk() if n.kind == "bond_series" and n.extra.get("series")) != 25:
    problems.append("expected 25 bond series leaves")
if len(mus.children) != 11:
    problems.append("expected 11 museums")
# sum of boxes equals the printed function totals reshuffled
box_sum = sum(c.amount for c in root.children)
if box_sum != EXPECTED:
    problems.append(f"boxes sum {box_sum} != expected {EXPECTED}")
if un_box.amount != 880_099_00:
    problems.append("unitemised box is not $880,099")
# every account moved is accounted for: park page totals + moved == printed
for n in root.find(lambda n: n.kind == "park" and n.extra.get("moved_to_venues_cents")):
    if n.amount + n.extra["moved_to_venues_cents"] != n.extra["printed_total_cents"]:
        problems.append(f"park total + moved != printed at {n.id}")
# each department / park total equals the printed total, unless something moved out
for n in root.find(lambda n: n.kind in ("department", "park") and n.extra.get("printed_total_cents") is not None):
    moved = n.extra.get("moved_to_venues_cents", 0)
    if n.kind == "department" and n.extra.get("unit_code") == "9310":
        moved = sum(v.amount for v in VEN_NODE.values() if "Revenue" in v.extra["listed_under"])
    if n.amount + moved != n.extra["printed_total_cents"]:
        problems.append(f"unit total + moved != printed at {n.id}: {n.amount} + {moved} vs {n.extra['printed_total_cents']}")

dr = depth_report(root)
n_nodes = sum(1 for _ in root.walk())
print(f"nodes: {n_nodes:,}   side rows: {len(side_rows(root)):,}")
print("depth:", json.dumps(dr))
print("top level:")
for c in root.children:
    print(f"   {c.amount / 100:>16,.2f}  {c.name}")
print(f"   {root.amount / 100:>16,.2f}  TOTAL")

if problems:
    print(f"FAILED: {len(problems)} problems")
    for p in problems[:40]:
        print("  -", p)
    sys.exit(1)

os.makedirs(P("build/out"), exist_ok=True)
save_json(root, P("build/out/parks_tree.json"))
rows = to_rows(root)
side = side_rows(root)
db = P("data/budget.db")
import sqlite3  # noqa: E402
_con = sqlite3.connect(db)
try:  # keep one checks row per run of this script: drop older parks rows first
    _con.execute("DELETE FROM checks WHERE gov='parks'")
    _con.commit()
except sqlite3.OperationalError:
    pass  # table not created yet
_con.close()
load_into_db(db, "parks", rows, side,
             ("parks", datetime.now(timezone.utc).isoformat(), len(rows), root.amount, EXPECTED, 0, json.dumps(dr)))
print(f"OK: {len(rows):,} rows and {len(side):,} side rows written to {db}")
