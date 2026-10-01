"""Link City of Chicago non-salary budget lines to the vendors and contracts behind them.

Inputs (all public Chicago Open Data, see scripts/contracts_fetch.py):
  raw/city_appropriations_2026.json   2026 Budget Ordinance (6694-f78c), 3,268 lines
  raw/city_payments_2025.csv          Payments (s4vu-giwb) for check year 2025, 115,810 rows
  raw/contracts/contracts_all.csv     Contracts (rsxa-ify5), one row per contract revision
  raw/contracts/payments_all.csv      Payments (s4vu-giwb) all years (used only for cross checks)
  raw/contracts/ijrh-ktm6.csv, 72uz-ikdv.csv   TIF annual report vendors / projects
  raw/contracts/midyear_grants.csv    Mid-year grants report (iyu8-jkf8)
  raw/contracts/payroll_costing_2025.csv   Payroll costing aggregates (dawh-m56b), 2025

Outputs:
  data/city_vendors_items_2025.json   every (department, family, vendor, contract) with 2025 dollars
  data/city_vendors_coverage_2026.json   department x account family coverage vs the 2026 budget
  data/city_vendors_findings_2025.json   top vendors, sole source, consulting, delegate agencies
  raw/contracts/report_tables.md      markdown tables pasted into research/contracts_vendors.md

Run: python3 scripts/contracts_build.py
Every number is computed from the files above. Nothing is typed in by hand except the
mapping tables below (department aliases, contract type to account family rules), which are
the "mapping approach" and are documented in research/contracts_vendors.md.
"""
import json
import os
import re
from collections import defaultdict

import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, ".."))
RAW = os.path.join(ROOT, "raw")
RC = os.path.join(RAW, "contracts")
DATA = os.path.join(ROOT, "data")
os.makedirs(DATA, exist_ok=True)

M = 1_000_000.0

# ---------------------------------------------------------------------------
# 1. Department normalization: names used in Contracts / Payments -> 2026 budget dept number
# ---------------------------------------------------------------------------
# Budget department numbers come from the ordinance. Names on the left are every spelling
# seen in Contracts or Payments. Predecessor departments are mapped to their 2026 successor.
DEPT_ALIASES = {
    "85": ["CHICAGO DEPARTMENT OF AVIATION", "OHARE MODERNIZATION PROJECT", "O'HARE MODERNIZATION PROGRAM"],
    "41": ["CHICAGO DEPARTMENT OF PUBLIC HEALTH"],
    "84": ["CHICAGO DEPARTMENT OF TRANSPORTATION"],
    "59": ["CHICAGO FIRE DEPARTMENT"],
    "57": ["CHICAGO POLICE DEPARTMENT"],
    "91": ["CHICAGO PUBLIC LIBRARY"],
    "67": ["DEPARTMENT OF BUILDINGS", "DEPARTMENT OF CONSTRUCTION AND PERMITS"],
    "70": ["DEPARTMENT OF BUSINESS AFFAIRS AND CONSUMER PROTECTION", "DEPT OF BUSINESS AFFAIRS & CONSUMER PROTECTION",
           "DEPARTMENT OF BUSINESS AFFAIRS AND LICENSING", "DEPT OF CONSUMER SERVICES"],
    "23": ["DEPARTMENT OF CULTURAL AFFAIRS", "DEPARTMENT OF CULTURAL AFFAIRS AND SPECIAL EVENTS",
           "OFFICE OF SPECIAL EVENTS", "DEPARTMENT OF SPECIAL EVENTS"],
    "72": ["DEPARTMENT OF ENVIRONMENT", "DEPARTMENT OF ENVIROMENT"],
    "50": ["DEPARTMENT OF FAMILY AND SUPPORT SERVICES", "DEPT ON AGING", "DEPARTMENT OF CHILDREN AND YOUTH SERVICES",
           "MAYORS OFFICE OF WORKFORCE DEVELOPMENT"],
    "27": ["DEPARTMENT OF FINANCE", "DEPARTMENT OF REVENUE", "GENERAL ACCOUNTING"],
    "38": ["DEPARTMENT OF FLEET AND FACILITY MANAGEMENT", "DEPT OF FLEET MGMT", "DEPT OF GENERAL SERVICES",
           "DEPT OF ASSETS INFORMATION AND SERVICES", "GRAPHICS & REPRODUCTION CTR"],
    "21": ["DEPARTMENT OF HOUSING"],
    "33": ["DEPARTMENT OF HUMAN RESOURCES", "DEPARTMENT OF PERSONNEL"],
    "31": ["DEPARTMENT OF LAW", "DEPT OF LAW"],
    "54": ["DEPARTMENT OF PLANNING AND DEVELOPMENT", "PLANNING & DEVELOPMENT", "DEPARTMENT OF ZONING",
           "DEPT OF ZONING & LAND USE PLANNING", "DEPT OF ECONOMIC DEVELOPMENT"],
    "35": ["DEPARTMENT OF PROCUREMENT SERVICES"],
    "81": ["DEPARTMENT OF STREETS AND SANITATION"],
    "6": ["DEPARTMENT OF TECHNOLOGY AND INNOVATION", "DEPT OF BUSINESS & INFORMATION SERVICES",
          "DEPT OF INNOVATION & TECHNOLOGY"],
    "88": ["DEPARTMENT OF WATER MANAGEMENT", "DEPT OF WATER"],
    "58": ["OFFICE OF EMERGENCY MANAGEMENT AND COMMUNICATIONS"],
    "51": ["OFFICE OF PUBLIC SAFETY ADMINISTRATION"],
    "5": ["OFFICE OF BUDGET & MANAGEMENT"],
    "25": ["OFFICE OF CITY CLERK"],
    "28": ["CITY TREASURER'S OFFICE"],
    "1": ["OFFICE OF THE MAYOR"],
    "48": ["MAYORS OFFICE FOR PEOPLE WITH DISABILITIES"],
    "73": ["CHICAGO ANIMAL CARE AND CONTROL"],
    "30": ["DEPARTMENT OF ADMINISTRATIVE HEARINGS", "ADMINISTRATIVE ADJUDICATION"],
    "45": ["CHICAGO COMMISSION ON HUMAN RELATIONS"],
    "78": ["BOARD OF ETHICS"],
    "55": ["CHICAGO POLICE BOARD"],
    "77": ["LICENSE APPEAL COMMISSION", "LIC COMM & LOCAL LIQ CTRL COMM"],
    "3": ["OFFICE OF INSPECTOR GENERAL"],
    "39": ["BOARD OF ELECTION COMMISSIONERS"],
    "60": ["INDEPENDENT POLICE REVIEW AUTHORITY"],
    "99": ["FINANCE GENERAL"],
    "15": ["CITY COUNCIL"],
    "62": ["COMMUNITY COMMISSION FOR PUBLIC SAFETY AND ACCOUNTABILITY"],
}
ALIAS_TO_NUM = {a: n for n, names in DEPT_ALIASES.items() for a in names}
# Names that cannot be assigned to a 2026 department (reported, never guessed).
UNMAPPABLE = {"CITYWIDE/MULTIPLE", "OFFICE OF COMPLIANCE", "OFFICE OF CABLE COMMUNICATION ADM"}

PRED_NOTE = {
    "50": "includes Dept on Aging, Children & Youth Services, Workforce Development (predecessors)",
    "38": "includes Dept of General Services, Dept of Assets Information & Services, Dept of Fleet Mgmt",
    "6": "includes Dept of Business & Information Services, Dept of Innovation & Technology",
    "54": "includes Planning & Development, Zoning, Economic Development",
    "27": "includes Dept of Revenue, General Accounting",
    "85": "includes O'Hare Modernization Program",
}

# ---------------------------------------------------------------------------
# 2. Budget account -> account family (what kind of vendor-facing spend is it?)
# ---------------------------------------------------------------------------
FAMILIES = {
    "PROF": "Professional & technical services (0140-0148)",
    "IT": "IT services, software, hardware (0138, 0139, 0149, 0154, 0312, 0446)",
    "TELECOM": "Telephone, mobile, data circuits (0181, 0189-0197, 0423)",
    "DELEGATE": "Delegate agencies and program grants (0135 + 92xx program accounts)",
    "CONSTR": "Construction and capital (0540, 0521, 9097)",
    "FACILITY": "Facility, equipment and street repair, maintenance services (0125, 0160-0163, 0176, 0188, 0526)",
    "WASTE": "Waste disposal (0185)",
    "RENTAL": "Rental of property and equipment, leases (0155, 0157, 0159)",
    "UTIL": "Electricity, gas, water (0331, 0332, 0322, 0183, 0314, 0316)",
    "FUEL": "Fuel (0315, 0320, 0325, 0318)",
    "MATERIALS": "Materials, supplies, drugs (0300-0365 other)",
    "EQUIP": "Equipment and vehicles purchase (04xx)",
    "BENEFITS": "Employee health, insurance, workers comp (0029, 0042-0056, 0172, 0937 ...)",
    "LEGAL": "Judgments, claims, outside counsel (0931, 0934, 0145)",
    "DEVLOAN": "Housing / development loans and grants (9103, 0991, 9102)",
    "OTHER_VENDOR": "Other vendor-payable accounts",
    "LEGACY_UNTYPED": "(payments only) contracts imported from legacy systems with no contract type",
}
NONVENDOR = {
    "PERSONNEL": "Salaries, wages, overtime, premiums (0000-0099 labor accounts)",
    "PENSION": "Pension contributions and allocations",
    "DEBT": "Debt service (interest, principal, notes, bond fees)",
    "TRANSFER": "Internal transfers and reimbursements between funds",
    "RESERVE": "Reserve Balance (909A) and savings placeholders",
    "TAXES": "Loss in collection, refunds",
    "PASSTHRU": "Tax proceeds and contributions passed to the CTA (9189, 9205)",
}

BENEFIT_ACCTS = {"0029", "0042", "0043", "0045", "0049", "0051", "0052", "0056", "0172", "0937"}
DELEGATE_PROGRAM_ACCTS = {"0135", "9142", "9143", "9204", "921A", "9253", "9254", "9255", "9259", "9260", "9261",
                          "9262", "9263", "9267", "9283", "9291", "9296", "9299", "9241", "9225", "9219", "0999"}
TRANSFER_ACCTS = {"9438", "9441", "9454", "9470", "9481", "9484", "9610", "9611", "9635", "9636", "9640", "9645",
                  "9647", "9711", "9713", "9765", "9771", "9773", "9774", "9775", "9776", "9778"}
DEBT_ACCTS = {"0902", "0912", "0961", "0943", "0944", "0955", "0958", "0959"}
PASSTHRU_ACCTS = {"9205", "9189"}
TAX_ACCTS = {"0960", "0989", "0992", "0982"}
# labor accounts that look like benefits but are paid to people or governments, not vendors
LABOR_LIKE = {"0044", "9027", "9076", "0085", "0070", "0063", "0095", "0096", "002A"}


def account_family(code):
    """Return (kind, family). kind is 'vendor' or 'nonvendor'."""
    c = str(code).upper()
    if c in ("909A", "9333", "9046", "9646"):
        return ("nonvendor", "RESERVE")
    if c in TRANSFER_ACCTS or c in {"9980", "9981", "9982", "9983", "9984", "9985", "9986", "9987"}:
        return ("nonvendor", "TRANSFER")
    if c in {"0976", "097A"}:
        return ("nonvendor", "PENSION")
    if c in DEBT_ACCTS:
        return ("nonvendor", "DEBT")
    if c in PASSTHRU_ACCTS:
        return ("nonvendor", "PASSTHRU")
    if c in TAX_ACCTS:
        return ("nonvendor", "TAXES")
    if c in LABOR_LIKE:
        return ("nonvendor", "PERSONNEL")
    if c in DELEGATE_PROGRAM_ACCTS:
        return ("vendor", "DELEGATE")
    if c in BENEFIT_ACCTS:
        return ("vendor", "BENEFITS")
    if c in {"0931", "0934", "9005", "9006", "0145", "9121"}:
        return ("vendor", "LEGAL")
    if c in {"9103", "0991", "9102", "9211", "9212", "9213", "9224"}:
        return ("vendor", "DEVLOAN")
    if len(c) == 4 and c.isdigit() and c < "0100":
        return ("nonvendor", "PERSONNEL")
    if c in {"0138", "0139", "0149", "0154", "0312", "0446"}:
        return ("vendor", "IT")
    if c in {"0181", "0189", "0190", "0191", "0196", "0197", "0423"}:
        return ("vendor", "TELECOM")
    if c in {"0140", "0141", "0142", "0143", "0144", "0147", "0148", "0123", "0124", "0128", "0169", "0165"}:
        return ("vendor", "PROF")
    if c in {"0540", "0521", "9097"}:
        return ("vendor", "CONSTR")
    if c in {"0125", "0160", "0161", "0162", "0163", "0176", "0188", "0526", "9110", "9112", "9160"}:
        return ("vendor", "FACILITY")
    if c == "0185":
        return ("vendor", "WASTE")
    if c in {"0155", "0157", "0159", "0156"}:
        return ("vendor", "RENTAL")
    if c in {"0331", "0332", "0322", "0183", "0314", "0316", "0905"}:
        return ("vendor", "UTIL")
    if c in {"0315", "0320", "0325", "0318"}:
        return ("vendor", "FUEL")
    if c.startswith("03"):
        return ("vendor", "MATERIALS")
    if c in {"0455", "0450", "0451"} or c.startswith("04"):
        return ("vendor", "EQUIP")
    return ("vendor", "OTHER_VENDOR")


# ---------------------------------------------------------------------------
# 3. Payment / contract classification into the same families
# ---------------------------------------------------------------------------
CT_FAMILY = {
    "DELEGATE AGENCY": "DELEGATE", "Delegate Agency": "DELEGATE", "DPS DELEGATE AGENCY": "DELEGATE",
    "PRO SERV CONSULTING $250,000orABOVE": "PROF", "PRO SERV CONSULTING UNDER $250,000": "PROF",
    "PRO SERV": "PROF", "Professional Services": "PROF", "PRO SERV-AVIATION": "PROF", "PRO SERV-SMALL ORDERS": "PROF",
    "PRO SERV-BUSINESS CONSULTING": "PROF", "ARCH/ENGINEERING": "PROF", "ARCH/ENGINEERING-AVIATION": "PROF",
    "PRO SERV-SOFTWARE/HARDWARE": "IT", "SOFTWARE": "IT", "HARDWARE": "IT",
    "CONSTRUCTION-LARGE $3MILLIONorABOVE": "CONSTR", "CONSTRUCTION-LARGE $5MILLIONorABOVE": "CONSTR",
    "CONSTRUCTION-AVIATION": "CONSTR", "CONSTRUCTION-GENERAL": "CONSTR", "CONSTRUCTION": "CONSTR",
    "Construction": "CONSTR", "CONSTRUCTION SERVICES": "CONSTR", "JOC": "CONSTR", "DEMOLITION": "CONSTR",
    "Demolition": "CONSTR", "DEMOLITION-SMALL ORDERS": "CONSTR", "ROOFING": "CONSTR",
    "WORK SERVICES / FACILITIES MAINT.": "FACILITY", "WORK SERV-AVIATION": "FACILITY",
    "WORK SERVICES-SMALL ORDERS": "FACILITY", "HIRED TRUCK": "FACILITY", "Service Contract": "FACILITY",
    "COMMODITIES": "MATERIALS", "COMMODITIES-AVIATION": "MATERIALS", "COMMODITIES-SMALL ORDERS": "MATERIALS",
    "VEHICLES/HEAVY EQUIPMENT (CAPITAL)": "EQUIP",
    "TELECOMMUNICATIONS": "TELECOM", "UTILITIES-ELECTRICITY": "UTIL", "PROPERTY LEASE": "RENTAL",
}
IT_WORDS = re.compile(r"SOFTWARE|LICENS|SAAS|CLOUD|DATABASE|CYBER|NETWORK|INFORMATION TECHNOLOGY|\bIT\b|SYSTEM IMPLEMENT|"
                      r"APPLICATION|DATA CENTER|WEB ?SITE|ORACLE|MICROSOFT|SERVER", re.I)
CM_WORDS = re.compile(r"CONSTRUCTION MANAGEMENT AT.RISK|CM AT.RISK|CONSTRUCTION MANAGER AT.RISK", re.I)
RENT_WORDS = re.compile(r"RENTAL|LEASE|LEASING", re.I)
WASTE_WORDS = re.compile(r"WASTE|DISPOSAL|REFUSE|RECYCL|SWEEP|DUMP|TRANSFER STATION|SOLID", re.I)
FUEL_WORDS = re.compile(r"FUEL|GASOLINE|DIESEL|PROPANE", re.I)
UTIL_WORDS = re.compile(r"ELECTRIC|NATURAL GAS|ENERGY SUPPLY|POWER SUPPLY", re.I)
BENEFIT_WORDS = re.compile(r"BLUE CROSS|MEDICAL|DENTAL|PHARMACY|BENEFIT|INSURANCE|FLEXIBLE SPENDING|ACTUARIAL|"
                           r"WORKERS|CLAIMS ADMIN|VISION|SUBROGATION|EMPLOYEE", re.I)
DEV_WORDS = re.compile(r"REDEVELOPMENT|\bTIF\b|\bRDA\b|\bIGA\b|LOAN|\bHOME\b|CDBG|GRANT|BOARD OF EDUCATION|PARK DISTRICT|"
                       r"TRANSIT AUTHORITY|HOUSING|APARTMENT|\bLP\b|\bLLC\b|\bL\.P\.|AIRLINES|CONSORTIUM|REIMBURS", re.I)


def classify_contract(ctype, desc):
    desc = desc if isinstance(desc, str) else ""
    fam = CT_FAMILY.get(ctype)
    if fam == "PROF" and CM_WORDS.search(desc):
        return "CONSTR"   # e.g. "CONSTRUCTION MANAGEMENT AT-RISK SERVICES FOR O'HARE 21" is typed PRO SERV-AVIATION
    if fam == "PROF" and IT_WORDS.search(desc):
        return "IT"
    if fam in ("FACILITY",):
        if RENT_WORDS.search(desc):
            return "RENTAL"
        if WASTE_WORDS.search(desc):
            return "WASTE"
        return "FACILITY"
    if fam in ("MATERIALS", "EQUIP"):
        if FUEL_WORDS.search(desc):
            return "FUEL"
        if UTIL_WORDS.search(desc):
            return "UTIL"
        return fam
    if fam:
        return fam
    if ctype in ("COMPTROLLER-OTHER", "EXHIBIT-A", "EXHIBIT-B", "CONVERTED", "REVENUE", "Other"):
        if UTIL_WORDS.search(desc) and not DEV_WORDS.search(desc.replace("ELECTRIC", "")):
            return "UTIL"
        if BENEFIT_WORDS.search(desc):
            return "BENEFITS"
        if DEV_WORDS.search(desc):
            return "DEVLOAN"
        if IT_WORDS.search(desc):
            return "IT"
        return "OTHER_VENDOR"
    # Legacy rows with no type (imported before FMPS) and misc types
    if ctype in ("Modification", "Time Extension", "Term Agreement", "One Shot", "Add Line Item", "Emergency",
                 "RELEASE REQUISITION", "ONE SHOT", "Emergency"):
        return "OTHER_VENDOR"
    if ctype is None or (isinstance(ctype, float)):
        return "LEGACY_UNTYPED"
    return "OTHER_VENDOR"


# Contracts with a blank/unmappable department often carry the department in the description,
# e.g. "CDPH-RW-PA: Healthcare Access ...". Only prefixes seen in the data are used.
DESC_PREFIX_DEPT = {"CDPH": "41", "MOPD": "48", "OBM": "5", "DOF": "27", "DPD": "54"}
DESC_PREFIX = re.compile(r"^(CDPH|MOPD|OBM|DOF|DPD)\b", re.I)

# vendor-name rules for direct vouchers (no contract). Order matters, first match wins.
DV_RULES = [
    ("PENSION", r"PENSION|ANNUITY|RETIREMENT|POLICEMENS A|LABORERS & RET|NATIONWIDE RET"),
    ("DEBT_BANKS", r"BANK|TRUST CO|ZIONS|WELLS FARGO|AMALGAMATED|PNC|FIFTH THIRD|BNY|BANC"),
    ("TAX_COUNTY_STATE", r"COOK COUNTY (TREASURER|COLLECTOR)|STATE OF ILL|TREASURER|DEPARTMENT OF THE TREASURY|CLERK OF THE (CIRCUIT )?COURT|"
                         r"CLERK, U\.?S|EMP SECURI|COMPTROLLER"),
    ("UTILITIES", r"COMED|COMMONWEALTH|PEOPLE'?S GAS|NICOR|CITY OF CHICAGO DEPT OF WATER|WATER RECLAMATION|SANITARY|EXELON|"
                  r"CONSTELLATION|MANSFIELD|VERIZON|AT&T|COMCAST|T-MOBILE|SPRINT"),
    ("LEGAL_SETTLEMENT", r"LAW|ATTORNEY|LLP|L\.?L\.?P|\bP\.?C\.?\b|LTD|LIMITED|ASSOCIATES|ESTATE OF|SETTLEMENT|ANNUITY SERVICES|"
                         r"ASSIGNED|STRUCTURED|LIFE INSURANCE|LIFE & ANNUITY|ASSIGNMENT"),
    ("INSURANCE_ADMIN", r"INSURANCE|GALLAGHER|CCMSI|USI |BLUE CROSS|RISK"),
    ("TRANSIT_AGENCY", r"TRANS?IT|PUBLIC BUILDING COMMISSION|PARK DISTRICT|BOARD OF EDUCATION"),
]
DV_RULES = [(k, re.compile(p, re.I)) for k, p in DV_RULES]


def dv_class(vendor):
    v = vendor if isinstance(vendor, str) else ""
    for k, rx in DV_RULES:
        if rx.search(v):
            return k
    return "OTHER_DIRECT_VOUCHER"


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
SUFFIX = re.compile(r"\b(INC|INCORPORATED|LLC|L L C|LTD|LIMITED|CO|COMPANY|CORP|CORPORATION|LLP|LP|PC|P C|THE)\b")


def vendor_key(name):
    n = str(name).upper().split("|")[0]
    n = re.sub(r"[^A-Z0-9& ]", " ", n)
    n = SUFFIX.sub(" ", n)
    n = re.sub(r"\s+", " ", n).strip()
    return n or str(name).upper()


def norm_dept_name(n):
    if not isinstance(n, str):
        return None
    n = n.strip().upper()
    return ALIAS_TO_NUM.get(n)


def last_nonnull(s):
    s = s.dropna()
    return s.iloc[-1] if len(s) else None


def pct(a, b):
    return 0.0 if not b else 100.0 * a / b


def fm(x):
    return "${:,.1f}M".format(x / M)


def fb(x):
    return "${:,.2f}B".format(x / 1e9)


# ---------------------------------------------------------------------------
def main():
    out_md = []

    # ---- budget -----------------------------------------------------------
    a = pd.read_json(os.path.join(RAW, "city_appropriations_2026.json"), dtype=str)
    a["amt"] = pd.to_numeric(a["_ordinance_amount_"])
    a["dept"] = a["department_number"].astype(str).str.lstrip("0")
    a.loc[a["dept"] == "", "dept"] = "0"
    dept_names = a.drop_duplicates("dept").set_index("dept")["department_description"].to_dict()
    kf = a["appropriation_account"].map(account_family)
    a["kind"] = [k for k, f in kf]
    a["family"] = [f for k, f in kf]
    total_budget = a.amt.sum()
    # Sanity: every budget dept has an alias group
    missing_alias = [d for d in dept_names if d not in DEPT_ALIASES]

    # ---- contracts --------------------------------------------------------
    c = pd.read_csv(os.path.join(RC, "contracts_all.csv"), dtype=str)
    c["award"] = pd.to_numeric(c.award_amount)
    c["rev"] = pd.to_numeric(c.revision_number, errors="coerce")
    c = c.sort_values(["purchase_order_contract_number", "rev"])
    g = c.groupby("purchase_order_contract_number")
    cm = pd.DataFrame({
        "award_total": g.award.sum(),
        "n_rev": g.rev.size(),
        "ctype": g.contract_type.agg(last_nonnull),
        "cdept_raw": g.department.agg(last_nonnull),
        "cvendor": g.vendor_name.agg(last_nonnull),
        "desc": g.purchase_order_description.agg(last_nonnull),
        "proc_any": g.procurement_type.agg(lambda s: "|".join(sorted(set(s.dropna())))),
        "start": g.start_date.agg(last_nonnull),
        "end": g.end_date.agg(last_nonnull),
        "has_pdf": g.contract_pdf.agg(lambda s: bool(s.notna().any())),
    })
    cm["cdept"] = cm.cdept_raw.map(norm_dept_name)
    cm["family"] = [classify_contract(t, d) for t, d in zip(cm.ctype, cm.desc)]

    # ---- payments 2025 ----------------------------------------------------
    p = pd.read_csv(os.path.join(RAW, "city_payments_2025.csv"), dtype=str)
    p["amount"] = pd.to_numeric(p.amount)
    total_paid = p.amount.sum()
    p["is_dv"] = p.contract_number == "DV"
    pre = p.voucher_number.str.extract(r"^(PVCI|PVPR|PVBN|CVIP|PV\d\d|M|CV)")[0]
    p["vprefix"] = pre
    p["vdept"] = p.vprefix.where(p.vprefix.str.match(r"^PV\d\d$", na=False)).str[2:].str.lstrip("0")
    p.loc[p.vdept == "", "vdept"] = "0"
    p["name_dept"] = p.department_name.map(norm_dept_name)
    p = p.join(cm[["cdept", "family", "ctype", "desc", "proc_any", "award_total", "cdept_raw", "has_pdf"]],
               on="contract_number")
    p["matched"] = p.contract_number.isin(cm.index)

    # department resolution, record the route used
    def resolve(row):
        if isinstance(row.department_name, str):
            if row.name_dept:
                return row.name_dept, "payment dept name"
            return None, "payment dept name unmappable"
        if row.matched and row.cdept:
            return row.cdept, "contract join"
        if row.is_dv and isinstance(row.vdept, str):
            return row.vdept, "voucher prefix (direct voucher)"
        if row.matched:
            pre = DESC_PREFIX.match(row.desc) if isinstance(row.desc, str) else None
            if pre:
                return DESC_PREFIX_DEPT[pre.group(1).upper()], "contract description prefix (CDPH-, MOPD- ...)"
            return None, "contract join, contract dept unmappable/blank"
        return None, "unresolved"

    res = [resolve(r) for r in p.itertuples(index=False)]
    p["dept"] = [r[0] for r in res]
    p["route"] = [r[1] for r in res]
    # direct voucher special cases
    p.loc[p.vprefix == "PVPR", ["dept", "route"]] = ["99", "payroll deduction voucher (PVPR) -> Finance General"]
    p["dv_class"] = [dv_class(v) if d else None for v, d in zip(p.vendor_name, p.is_dv)]
    # PV27 direct vouchers are central Finance vouchers (pensions, debt, settlements, taxes)
    central_mask = p.is_dv & (p.vprefix == "PV27")
    p.loc[central_mask, "dept"] = "99"
    p.loc[central_mask, "route"] = "central Finance direct voucher (PV27) -> Finance General"
    p.loc[p.is_dv & (p.vprefix == "PVPR"), "route"] = "payroll deduction voucher (PVPR) -> Finance General"

    # family for each payment
    def pay_family(row):
        if row.is_dv and row.vprefix == "PVPR":
            return "X_PAYROLL_DEDUCTION"   # union dues, credit unions, deferred comp, pension remittances
        if row.is_dv:
            k = row.dv_class
            return {"PENSION": "X_PENSION", "DEBT_BANKS": "X_DEBT_BANK", "TAX_COUNTY_STATE": "X_TAX_GOV",
                    "LEGAL_SETTLEMENT": "LEGAL", "INSURANCE_ADMIN": "BENEFITS", "UTILITIES": "UTIL",
                    "TRANSIT_AGENCY": "X_PASSTHRU_AGENCY", "OTHER_DIRECT_VOUCHER": "OTHER_VENDOR"}.get(k, "OTHER_VENDOR")
        if row.matched:
            return row.family
        return "UNMATCHED"
    p["pfamily"] = [pay_family(r) for r in p.itertuples(index=False)]

    # vendor display name: contract vendor if matched (cleaned), else payment name
    p["vkey"] = p.vendor_name.map(vendor_key)

    # --- routing stats
    route_tab = p.groupby("route").amount.agg(["sum", "count"]).sort_values("sum", ascending=False)
    blank = p[p.department_name.isna()]
    blank_route = blank.groupby("route").amount.agg(["sum", "count"]).sort_values("sum", ascending=False)

    # voucher prefix agreement check on non-DV vouchers where both are known
    chk = p[(~p.is_dv) & p.name_dept.notna() & p.vdept.notna()]
    prefix_agree = (chk.name_dept == chk.vdept).mean() if len(chk) else float("nan")
    prefix_agree_amt = chk[chk.name_dept == chk.vdept].amount.sum() / chk.amount.sum() if len(chk) else float("nan")

    # ---- non-vendor bucket handling for payments -------------------------------
    p["nonvendor"] = p.pfamily.str.startswith("X_")
    vendor_pay = p[~p.nonvendor & (p.pfamily != "UNMATCHED")]

    # ---- budget by dept x family ----------------------------------------------
    bv = a[a.kind == "vendor"]
    b_df = bv.groupby(["dept", "family"]).amt.sum().unstack(fill_value=0)
    b_dept_vendor = bv.groupby("dept").amt.sum()
    b_dept_total = a.groupby("dept").amt.sum()
    b_dept_personnel = a[a.family == "PERSONNEL"].groupby("dept").amt.sum()
    b_dept_nonvendor_other = a[(a.kind == "nonvendor") & (a.family != "PERSONNEL")].groupby("dept").amt.sum()

    pay_df = vendor_pay[vendor_pay.dept.notna()].groupby(["dept", "pfamily"]).amount.sum().unstack(fill_value=0)

    rows = []
    for d in sorted(dept_names, key=lambda x: -b_dept_total.get(x, 0)):
        bud_v = b_dept_vendor.get(d, 0.0)
        pay = vendor_pay[vendor_pay.dept == d]
        paid_v = pay.amount.sum()
        # coverage per family capped at budget so one family cannot compensate another
        cov_capped = 0.0
        for fam in set(b_df.columns) | set(pay_df.columns):
            bb = b_df.loc[d, fam] if (d in b_df.index and fam in b_df.columns) else 0.0
            pp = pay_df.loc[d, fam] if (d in pay_df.index and fam in pay_df.columns) else 0.0
            cov_capped += min(bb, pp) if bb > 0 else 0.0
        rows.append({
            "dept": d, "name": dept_names[d], "budget_total": float(b_dept_total.get(d, 0)),
            "budget_personnel": float(b_dept_personnel.get(d, 0)),
            "budget_nonvendor_other": float(b_dept_nonvendor_other.get(d, 0)),
            "budget_vendor_payable": float(bud_v),
            "paid_2025_vendor": float(paid_v),
            "ratio_paid_to_budget": (paid_v / bud_v) if bud_v else None,
            "covered_capped_by_family": float(cov_capped),
            "covered_capped_pct": pct(cov_capped, bud_v),
        })
    cov = pd.DataFrame(rows)

    # ---- budget dollars explained by named contracts AND sitting in items under $1M ----
    # For each (dept, family): scale = min(1, budget / paid). Items are (vendor, contract).
    vpx = vendor_pay[vendor_pay.dept.notna()].copy()
    vpx["cn"] = vpx.contract_number.where(~vpx.is_dv, "DV")
    item = vpx.groupby(["dept", "pfamily", "vkey", "cn"]).amount.sum().reset_index()
    item = item[item.amount > 0]
    scaled_rows = []
    for (d, f), grp in item.groupby(["dept", "pfamily"]):
        bb = float(b_df.loc[d, f]) if (d in b_df.index and f in b_df.columns) else 0.0
        if bb <= 0:
            continue
        tot = grp.amount.sum()
        scale = min(1.0, bb / tot)
        under_amt = grp[grp.amount < M].amount.sum()
        scaled_rows.append({"dept": d, "family": f, "budget": bb, "paid": float(tot),
                            "explained": float(tot * scale), "explained_under_1M": float(under_amt * scale)})
    sc = pd.DataFrame(scaled_rows)
    explained = {
        "vendor_payable_budget": float(bv.amt.sum()),
        "explained_by_named_contracts": float(sc.explained.sum()),
        "explained_in_items_under_1M": float(sc.explained_under_1M.sum()),
        "by_family": {f: {"budget": float(g_.budget.sum()), "explained": float(g_.explained.sum()),
                          "explained_under_1M": float(g_.explained_under_1M.sum())} for f, g_ in sc.groupby("family")},
        "by_dept": {d: {"name": dept_names[d], "budget": float(g_.budget.sum()), "explained": float(g_.explained.sum()),
                        "explained_under_1M": float(g_.explained_under_1M.sum())} for d, g_ in sc.groupby("dept")},
    }
    # Pooled (citywide) version: budget owner and paying department often differ (health care is
    # budgeted in Finance General but paid by Dept of Finance, IT is budgeted in many departments but
    # paid through Technology & Innovation), so also match each family citywide.
    pooled = {}
    for f, grp in item.groupby("pfamily"):
        bb = float(bv[bv.family == f].amt.sum())
        tot = float(grp.amount.sum())
        if bb <= 0:
            continue
        scale = min(1.0, bb / tot)
        pooled[f] = {"budget": bb, "paid": tot, "explained": tot * scale,
                     "explained_under_1M": float(grp[grp.amount < M].amount.sum()) * scale}
    explained["pooled_citywide_by_family"] = pooled
    explained["pooled_citywide_total"] = {
        "budget": float(sum(v["budget"] for v in pooled.values())),
        "explained": float(sum(v["explained"] for v in pooled.values())),
        "explained_under_1M": float(sum(v["explained_under_1M"] for v in pooled.values())),
        "budget_in_families_without_payments": float(bv[~bv.family.isin(pooled)].amt.sum()),
    }
    # headline accounts called out by the plan
    HEAD = [("0140", "PROF"), ("0540", "CONSTR"), ("0135", "DELEGATE"), ("0138", "IT"), ("0162", "FACILITY"),
            ("0157", "RENTAL"), ("0331", "UTIL"), ("0340", "MATERIALS")]
    headline = []
    for acct, fam in HEAD:
        ab = a[a.appropriation_account == acct]
        # department by department: account budget vs family explained
        tot_b = float(ab.amt.sum())
        ex = 0.0
        exu = 0.0
        for d, bd in ab.groupby("dept").amt.sum().items():
            fam_b = float(b_df.loc[d, fam]) if (d in b_df.index and fam in b_df.columns) else 0.0
            r = sc[(sc.dept == d) & (sc.family == fam)]
            if r.empty or fam_b <= 0:
                continue
            share = bd / fam_b  # this account's share of the family budget in the dept
            ex += float(r.explained.iloc[0]) * share
            exu += float(r.explained_under_1M.iloc[0]) * share
        headline.append({"account": acct, "family": fam,
                         "description": ab.appropriation_account_description.iloc[0][:70],
                         "budget_2026": tot_b, "explained": ex, "explained_under_1M": exu})
    explained["headline_accounts"] = headline

    # ---- under-$1M analysis (2025 payments to vendors, dept resolved) -----------
    vp = vendor_pay[vendor_pay.dept.notna()].copy()
    vp["cn"] = vp.contract_number.where(~vp.is_dv, "DV")
    vp["month"] = vp.check_date.str[:2]
    vp["quarter"] = ((pd.to_numeric(vp.month) - 1) // 3 + 1).astype(str)

    def share_under(df, keys):
        s = df.groupby(keys).amount.sum()
        s = s[s > 0]
        return {
            "groups": int(len(s)), "groups_under_1M": int((s < M).sum()),
            "dollars": float(s.sum()), "dollars_in_groups_under_1M": float(s[s < M].sum()),
            "pct_dollars_under_1M": pct(s[s < M].sum(), s.sum()),
            "pct_groups_under_1M": pct((s < M).sum(), len(s)),
        }

    under = {
        "dept_vendor": share_under(vp, ["dept", "vkey"]),
        "dept_vendor_contract": share_under(vp, ["dept", "vkey", "cn"]),
        "dept_vendor_family": share_under(vp, ["dept", "pfamily", "vkey"]),
        "dept_vendor_contract_quarter": share_under(vp, ["dept", "vkey", "cn", "quarter"]),
        "dept_vendor_contract_month": share_under(vp, ["dept", "vkey", "cn", "month"]),
        "dept_voucher_line": share_under(vp, ["dept", "voucher_number", "contract_number", "vkey"]),
    }
    # single-voucher view: how many dollars sit in one voucher line of $1M or more (cannot be split further)
    vl = vp.groupby(["pfamily", "dept", "voucher_number", "contract_number", "vkey"]).amount.sum().reset_index()
    vl = vl[vl.amount > 0]
    voucher_big = {}
    for f_, df_ in vl.groupby("pfamily"):
        voucher_big[f_] = {"dollars": float(df_.amount.sum()),
                           "dollars_in_vouchers_1M_plus": float(df_[df_.amount >= M].amount.sum()),
                           "vouchers_1M_plus": int((df_.amount >= M).sum())}
    under["voucher_level_by_family"] = voucher_big
    under_by_dept = {}
    for d, df in vp.groupby("dept"):
        under_by_dept[d] = {
            "dept_vendor": share_under(df, ["vkey"]),
            "dept_vendor_contract": share_under(df, ["vkey", "cn"]),
        }
    under_by_family = {}
    for f, df in vp.groupby("pfamily"):
        under_by_family[f] = {
            "dept_vendor": share_under(df, ["dept", "vkey"]),
            "dept_vendor_contract": share_under(df, ["dept", "vkey", "cn"]),
        }

    # ---- findings -------------------------------------------------------------
    def top_vendors(df, n=40):
        t = df.groupby("vkey").agg(amount=("amount", "sum"), n=("amount", "size"),
                                   vname=("vendor_name", lambda s: s.value_counts().index[0]),
                                   depts=("dept", lambda s: sorted(set(s.dropna()))))
        t = t.sort_values("amount", ascending=False).head(n)
        return [{"vendor": r["vname"], "paid_2025": round(float(r["amount"]), 2), "payments": int(r["n"]),
                 "depts": [dept_names.get(x, x) for x in r["depts"]]} for _, r in t.iterrows()]

    cont_named = vendor_pay[vendor_pay.matched & ~vendor_pay.is_dv]
    findings = {
        "top_vendors_all_resolved": top_vendors(vendor_pay),
    }

    # sole source / emergency / non-competitive via contract procurement_type
    def has(pt, k):
        return isinstance(pt, str) and k in pt.split("|")
    cont_named = cont_named.assign(
        sole=[has(x, "SOLE SOURCE") for x in cont_named.proc_any],
        emerg=[has(x, "EMERGENCY") for x in cont_named.proc_any],
        known=[bool(x) for x in cont_named.proc_any],
    )
    named_total = cont_named.amount.sum()
    proc_cov = {
        "paid_on_contracts_2025": float(named_total),
        "with_procurement_type": float(cont_named[cont_named.known].amount.sum()),
        "pct_with_procurement_type": pct(cont_named[cont_named.known].amount.sum(), named_total),
        "sole_source_paid": float(cont_named[cont_named.sole].amount.sum()),
        "emergency_paid": float(cont_named[cont_named.emerg].amount.sum()),
    }
    proc_breakdown = {}
    for k in ["BID", "RFP", "RFQ", "MASTER AGREEMENT", "SOLE SOURCE", "EMERGENCY", "JOINT PURCHASE", "REFERENCE CONTRACT",
              "CONTRACT ASSIGNMENT/TRANSFER", "RFI", "CM", "INNOVATIVE PROCUREMENT"]:
        proc_breakdown[k] = float(cont_named[[has(x, k) for x in cont_named.proc_any]].amount.sum())
    proc_breakdown["(blank, mostly delegate agency, comptroller and legacy)"] = float(
        cont_named[~cont_named.known].amount.sum())

    def contract_rows(df, n=30):
        t = df.groupby("contract_number").agg(
            amount=("amount", "sum"), vendor=("vendor_name", lambda s: s.value_counts().index[0]),
            desc=("desc", "first"), dept=("dept", "first"), ctype=("ctype", "first"),
            proc=("proc_any", "first"), award=("award_total", "first")).sort_values("amount", ascending=False).head(n)
        return [{"contract": k, "vendor": r.vendor, "desc": (r.desc or "")[:110], "dept": dept_names.get(r.dept, r.dept),
                 "type": r.ctype, "procurement": r.proc, "paid_2025": round(float(r.amount), 2),
                 "award_total": None if pd.isna(r.award) else round(float(r.award), 2)} for k, r in t.iterrows()]

    findings["sole_source_top_contracts"] = contract_rows(cont_named[cont_named.sole])
    findings["emergency_top_contracts"] = contract_rows(cont_named[cont_named.emerg], 15)
    sole_by_dept = cont_named[cont_named.sole].groupby("dept").amount.sum()
    findings["sole_source_by_dept"] = {dept_names.get(d, d): round(float(v), 2) for d, v in
                                       sole_by_dept.sort_values(ascending=False).items()}
    findings["procurement_type_coverage"] = proc_cov
    findings["procurement_type_paid_breakdown"] = {k: round(v, 2) for k, v in proc_breakdown.items()}

    # consulting
    cons_mask = cont_named.ctype.fillna("").str.contains("CONSULT") | cont_named.desc.fillna("").str.contains("CONSULT", case=False)
    consult = cont_named[cons_mask]
    findings["consulting"] = {
        "definition": "contract_type contains CONSULT (PRO SERV CONSULTING over/under $250,000, PRO SERV-BUSINESS CONSULTING) or description contains CONSULT",
        "paid_2025": float(consult.amount.sum()),
        "contract_type_only_paid_2025": float(cont_named[cont_named.ctype.fillna("").str.contains("CONSULT")].amount.sum()),
        "by_dept": {dept_names.get(d, d): round(float(v), 2) for d, v in
                    consult.groupby("dept").amount.sum().sort_values(ascending=False).head(15).items()},
        "top_vendors": top_vendors(consult, 20),
        "top_contracts": contract_rows(consult, 20),
    }

    # Delegate agencies
    dele = vendor_pay[vendor_pay.pfamily == "DELEGATE"]
    dv_ = share_under(dele, ["dept", "vkey"])
    dc_ = share_under(dele.assign(cn=dele.contract_number), ["dept", "vkey", "cn"])
    dep_del = dele.groupby("dept").amount.sum().sort_values(ascending=False)
    findings["delegate_agencies"] = {
        "paid_2025": float(dele.amount.sum()),
        "agencies_dept_pairs": dv_, "agency_contract_groups": dc_,
        "by_dept": {dept_names.get(d, d): round(float(v), 2) for d, v in dep_del.items()},
        "top_agencies": top_vendors(dele, 25),
    }
    # DFSS program codes (description prefix), e.g. DFSS-CORP-YS-SYEP
    dfss = vendor_pay[(vendor_pay.pfamily == "DELEGATE") & (vendor_pay.dept == "50")].copy()
    dfss["prog"] = dfss.desc.fillna("").str.extract(r"^(DFSS-[A-Z0-9]+-[A-Z]+-[A-Z0-9]+)")[0].fillna("(other)")
    findings["dfss_programs"] = {k: round(float(v), 2) for k, v in
                                 dfss.groupby("prog").amount.sum().sort_values(ascending=False).head(25).items()}

    # Direct vouchers (no contract) by class
    dvp = p[p.is_dv]
    findings["direct_vouchers"] = {
        "total": float(dvp.amount.sum()), "count": int(len(dvp)),
        "by_class": {k: round(float(v), 2) for k, v in
                     dvp.groupby("dv_class").amount.sum().sort_values(ascending=False).items()},
        "by_prefix": {str(k): round(float(v), 2) for k, v in
                      dvp.groupby("vprefix").amount.sum().sort_values(ascending=False).head(12).items()},
        "top_vendors_excluding_pv27_pvpr": top_vendors(dvp[~dvp.vprefix.isin(["PV27", "PVPR"])], 15),
    }

    # Contract-type table for 2025 payments
    ct_tab = p[p.matched & ~p.is_dv].groupby(p.ctype.fillna("(no type, legacy)")).amount.agg(["sum", "count"]).sort_values("sum", ascending=False)

    # Account family totals: budget vs payments
    fam_rows = []
    for f in list(FAMILIES) + ["UNMATCHED"]:
        bb = float(a[(a.kind == "vendor") & (a.family == f)].amt.sum())
        pp = float(vendor_pay[vendor_pay.pfamily == f].amount.sum()) if f != "UNMATCHED" else float(p[p.pfamily == "UNMATCHED"].amount.sum())
        fam_rows.append({"family": f, "label": FAMILIES.get(f, "Payments on contracts not found in Contracts dataset"),
                         "budget_2026": bb, "paid_2025": pp})
    xf = {k: float(p[p.pfamily == k].amount.sum()) for k in ["X_PENSION", "X_DEBT_BANK", "X_TAX_GOV", "X_PASSTHRU_AGENCY", "X_PAYROLL_DEDUCTION"]}

    # Active contracts in 2026
    cm["s_year"] = pd.to_numeric(cm.start.astype(str).str[:4], errors="coerce")
    cm["e_year"] = pd.to_numeric(cm.end.astype(str).str[:4], errors="coerce")
    active = cm[(cm.s_year <= 2026) & ((cm.e_year >= 2026) | cm.e_year.isna()) & (cm.s_year >= 2015)]
    active_by_dept = active[active.cdept.notna()].groupby("cdept").agg(contracts=("award_total", "size"),
                                                                           award_total=("award_total", "sum"))

    # TIF
    tif_v = pd.read_csv(os.path.join(RC, "ijrh-ktm6.csv"), dtype=str)
    tif_v["payment"] = pd.to_numeric(tif_v.payment)
    tif_p = pd.read_csv(os.path.join(RC, "72uz-ikdv.csv"), dtype=str)
    tif_p["cp"] = pd.to_numeric(tif_p.current_year_payments, errors="coerce")
    tif_summary = {
        "vendor_payments_over_10k_by_report_year": {k: round(float(v), 2) for k, v in tif_v.groupby("report_year").payment.sum().items()},
        "project_payments_by_report_year": {k: round(float(v), 2) for k, v in tif_p.groupby("report_year").cp.sum().items()},
    }

    # Mid-year grants
    gr = pd.read_csv(os.path.join(RC, "midyear_grants.csv"), dtype=str)
    for col in ["budget", "encumbrances", "expended_project_to_date", "funds_available_project_to_date"]:
        gr[col] = pd.to_numeric(gr[col])
    gl = gr[gr.data_extract_as_of_date.str.startswith(gr.data_extract_as_of_date.max()[:10])]
    grants_summary = {
        "extract_date": gr.data_extract_as_of_date.max()[:10], "rows": int(len(gl)), "budget": float(gl.budget.sum()),
        "rows_under_1M": int((gl.budget < M).sum()), "budget_in_rows_under_1M": float(gl[gl.budget < M].budget.sum()),
        "by_dept_top": {k: round(float(v), 2) for k, v in gl.groupby("department_description").budget.sum().sort_values(ascending=False).head(12).items()},
    }

    # Overtime from payroll costing
    pc = pd.read_csv(os.path.join(RC, "payroll_costing_2025.csv"), dtype=str)
    pc["amount"] = pd.to_numeric(pc.amount)
    ot_elems = pc[pc.pay_element.str.startswith("OT") | (pc.appropriation_code == "A0020")]
    ot_by_dept = ot_elems.groupby(ot_elems.department_code.str[1:].str.lstrip("0")).amount.sum()
    ot_budget = a[a.appropriation_account == "0020"].groupby("dept").amt.sum()
    overtime = {"total_2025_ot_pay_elements": float(ot_elems.amount.sum()), "budget_2026_0020": float(ot_budget.sum()),
                "by_dept": {dept_names.get(d, d): {"paid_2025": round(float(ot_by_dept.get(d, 0)), 2),
                                                  "budget_2026": round(float(ot_budget.get(d, 0)), 2)}
                            for d in ot_budget.sort_values(ascending=False).index[:12]}}

    # ---- unmapped department names (never hidden) ---------------------------------
    unm = p[p.department_name.notna() & p.name_dept.isna()].groupby("department_name").amount.sum()
    cunm = cm[cm.cdept_raw.notna() & cm.cdept.isna()].cdept_raw.value_counts()

    # ---- write data files ----------------------------------------------------------
    items = vp.groupby(["dept", "pfamily", "vkey", "cn"]).agg(
        amount=("amount", "sum"), n=("amount", "size"), vendor=("vendor_name", lambda s: s.value_counts().index[0]),
        desc=("desc", "first"), ctype=("ctype", "first"), proc=("proc_any", "first"), award=("award_total", "first")
    ).reset_index()
    items = items[items.amount > 0].sort_values(["dept", "pfamily", "amount"], ascending=[True, True, False])
    tree = {}
    for r in items.itertuples(index=False):
        d = tree.setdefault(r.dept, {"name": dept_names.get(r.dept, r.dept), "families": {}})
        fam = d["families"].setdefault(r.pfamily, [])
        rec = [r.vendor, None if r.cn == "DV" else r.cn, round(float(r.amount), 2), int(r.n),
               (r.desc or "")[:90] if isinstance(r.desc, str) else "", r.ctype if isinstance(r.ctype, str) else None,
               r.proc if isinstance(r.proc, str) and r.proc else None]
        fam.append(rec)
    json.dump({
        "source": "Payments s4vu-giwb (check year 2025) joined to Contracts rsxa-ify5; budget dept numbers from 6694-f78c",
        "record_fields": ["vendor", "contract_number (null = direct voucher)", "paid_2025", "payments", "contract_description", "contract_type", "procurement_type"],
        "families": FAMILIES, "departments": tree}, open(os.path.join(DATA, "city_vendors_items_2025.json"), "w"),
        separators=(",", ":"))

    budget_by_kind = {}
    for (k_, f_), g_ in a.groupby(["kind", "family"]):
        budget_by_kind["{}:{}".format(k_, f_)] = float(g_.amt.sum())
    cov_out = {
        "budget_by_kind_family": budget_by_kind,
        "source": "2026 Budget Ordinance 6694-f78c vs 2025 Payments s4vu-giwb + Contracts rsxa-ify5",
        "definitions": {
            "budget_vendor_payable": "2026 appropriation lines whose account maps to a vendor-facing family (see families). Excludes personnel, pensions, debt, internal transfers, reserves, tax distributions.",
            "paid_2025_vendor": "2025 payments resolved to the department, excluding pension / bank / tax / pass-through direct vouchers and payments on contracts missing from the Contracts dataset",
            "covered_capped_by_family": "sum over families of min(2026 budget, 2025 paid) so over-payment in one family cannot hide a gap in another",
        },
        "families": FAMILIES, "nonvendor_kinds": NONVENDOR,
        "departments": cov.to_dict(orient="records"),
        "by_dept_family": {d: {"name": dept_names[d],
                                "budget_2026": {f: float(b_df.loc[d, f]) for f in b_df.columns if d in b_df.index and b_df.loc[d, f]},
                                "paid_2025": {f: float(pay_df.loc[d, f]) for f in pay_df.columns if d in pay_df.index and pay_df.loc[d, f]}}
                           for d in dept_names},
        "explained_by_named_contracts": explained,
        "family_totals": fam_rows, "nonvendor_direct_voucher_totals_2025": xf,
        "under_1M": {"overall": under, "by_dept": under_by_dept, "by_family": under_by_family},
        "active_contracts_2026_by_dept": {dept_names.get(d, d): {"contracts": int(r.contracts), "award_total": round(float(r.award_total), 2)} for d, r in active_by_dept.iterrows()},
        "dept_aliases": {dept_names.get(d, d): v for d, v in DEPT_ALIASES.items()},
    }
    json.dump(cov_out, open(os.path.join(DATA, "city_vendors_coverage_2026.json"), "w"), indent=1)
    findings.update({"tif": tif_summary, "mid_year_grants": grants_summary, "overtime": overtime,
                     "payment_routing_all": {k: {"amount": round(float(r["sum"]), 2), "rows": int(r["count"])} for k, r in route_tab.iterrows()},
                     "payment_routing_blank_dept": {k: {"amount": round(float(r["sum"]), 2), "rows": int(r["count"])} for k, r in blank_route.iterrows()},
                     "unmapped_payment_dept_names": {k: round(float(v), 2) for k, v in unm.items()},
                     "unmapped_contract_dept_names_contracts": {k: int(v) for k, v in cunm.items()},
                     "budget_depts_missing_alias": missing_alias,
                     "voucher_prefix_vs_dept_name_agreement": {"rows_pct": 100 * prefix_agree, "dollars_pct": 100 * prefix_agree_amt}})
    json.dump(findings, open(os.path.join(DATA, "city_vendors_findings_2025.json"), "w"), indent=1)

    # ---- markdown fragments ---------------------------------------------------------
    L = out_md.append
    L("## T1 routing\n")
    L("| Route used to assign a department | 2025 $ | Rows |\n|---|---:|---:|")
    for k, r in route_tab.iterrows():
        L("| {} | {} | {:,} |".format(k, fm(r["sum"]), int(r["count"])))
    L("\n## T2 blank-department payments\n")
    L("| How the blank-department payments were resolved | 2025 $ | Rows |\n|---|---:|---:|")
    for k, r in blank_route.iterrows():
        L("| {} | {} | {:,} |".format(k, fm(r["sum"]), int(r["count"])))
    L("\n## T3 coverage by department\n")
    L("| Dept | 2026 budget | Personnel | Non-vendor other | Vendor-payable budget | 2025 paid to named vendors (resolved) | Paid / budget | Covered (capped by family) |\n|---|---:|---:|---:|---:|---:|---:|---:|")
    for r in cov.itertuples():
        ratio = "n/a" if r.ratio_paid_to_budget is None else "{:.0f}%".format(100 * r.ratio_paid_to_budget)
        L("| {} | {} | {} | {} | {} | {} | {} | {:.0f}% |".format(
            r.name, fm(r.budget_total), fm(r.budget_personnel), fm(r.budget_nonvendor_other), fm(r.budget_vendor_payable),
            fm(r.paid_2025_vendor), ratio, r.covered_capped_pct))
    L("\n## T3b explained\n")
    L("| Family | 2026 budget (dept x family with any payments) | Explained by 2025 named contracts/vendors | Explained and in items under $1M |\n|---|---:|---:|---:|")
    for f, v in sorted(explained["by_family"].items(), key=lambda kv: -kv[1]["budget"]):
        L("| {} | {} | {} | {} |".format(f, fm(v["budget"]), fm(v["explained"]), fm(v["explained_under_1M"])))
    L("| (all vendor-payable budget, including lines with no payments) | {} | {} | {} |".format(
        fm(explained["vendor_payable_budget"]), fm(explained["explained_by_named_contracts"]),
        fm(explained["explained_in_items_under_1M"])))
    L("\n## T3e pooled citywide\n")
    L("| Family | 2026 budget (citywide) | 2025 paid (citywide) | Explained | Explained and under $1M |\n|---|---:|---:|---:|---:|")
    for f, v in sorted(pooled.items(), key=lambda kv: -kv[1]["budget"]):
        L("| {} | {} | {} | {} | {} |".format(f, fm(v["budget"]), fm(v["paid"]), fm(v["explained"]), fm(v["explained_under_1M"])))
    pt = explained["pooled_citywide_total"]
    L("| Total | {} | | {} | {} |".format(fm(pt["budget"]), fm(pt["explained"]), fm(pt["explained_under_1M"])))
    L("\n## T3c headline accounts\n")
    L("| Account | Budget 2026 | Explained | Explained and under $1M | Family used |\n|---|---:|---:|---:|---|")
    for h in headline:
        L("| {} {} | {} | {} | {} | {} |".format(h["account"], h["description"], fm(h["budget_2026"]), fm(h["explained"]),
                                                 fm(h["explained_under_1M"]), h["family"]))
    L("\n## T3d by dept explained\n")
    L("| Dept | Vendor-payable budget | Explained | Explained and under $1M |\n|---|---:|---:|---:|")
    for d, v in sorted(explained["by_dept"].items(), key=lambda kv: -kv[1]["budget"]):
        L("| {} | {} | {} | {} |".format(v["name"], fm(bv[bv.dept == d].amt.sum()), fm(v["explained"]), fm(v["explained_under_1M"])))
    L("\n## T3f merged department table\n")
    L("| Department | Vendor-payable budget 2026 | Paid 2025 to named vendors | Budget explained by named contracts | Explained and in items under $1M | Share of 2025 paid $ in (vendor, contract) items under $1M |\n|---|---:|---:|---:|---:|---:|")
    cov_i = cov.set_index("dept")
    for d_ in sorted(dept_names, key=lambda x: -cov_i.loc[x, "budget_vendor_payable"]):
        ex_ = explained["by_dept"].get(d_, {"explained": 0.0, "explained_under_1M": 0.0})
        u_ = under_by_dept.get(d_, {}).get("dept_vendor_contract")
        L("| {} | {} | {} | {} | {} | {} |".format(
            dept_names[d_], fm(cov_i.loc[d_, "budget_vendor_payable"]), fm(cov_i.loc[d_, "paid_2025_vendor"]),
            fm(ex_["explained"]), fm(ex_["explained_under_1M"]),
            "n/a" if not u_ else "{:.0f}%".format(u_["pct_dollars_under_1M"])))
    L("\n## T4 family totals\n")
    L("| Family | 2026 budget | 2025 paid (named, resolved) |\n|---|---:|---:|")
    for r in fam_rows:
        L("| {} | {} | {} |".format(r["label"], fm(r["budget_2026"]), fm(r["paid_2025"])))
    L("\n## T5 under 1M\n")
    L("| Item definition | Groups | Groups under $1M | $ total | $ in groups under $1M | % of $ under $1M |\n|---|---:|---:|---:|---:|---:|")
    for k, v in [(k_, v_) for k_, v_ in under.items() if k_ != "voucher_level_by_family"]:
        L("| {} | {:,} | {:,} | {} | {} | {:.1f}% |".format(k, v["groups"], v["groups_under_1M"], fm(v["dollars"]),
                                                            fm(v["dollars_in_groups_under_1M"]), v["pct_dollars_under_1M"]))
    L("\n## T0 budget by kind\n")
    for k_, v_ in sorted(budget_by_kind.items(), key=lambda kv: -kv[1]):
        L("| {} | {} |".format(k_, fm(v_)))
    L("\n## T5b voucher level by family\n")
    L("| Family | $ | $ in single vouchers of $1M or more | Count of such vouchers |\n|---|---:|---:|---:|")
    for f_, v_ in sorted(voucher_big.items(), key=lambda kv: -kv[1]["dollars"]):
        L("| {} | {} | {} | {:,} |".format(f_, fm(v_["dollars"]), fm(v_["dollars_in_vouchers_1M_plus"]), v_["vouchers_1M_plus"]))
    L("\n## T6 under 1M by dept (dept, vendor, contract)\n")
    L("| Dept | $ paid | Groups | % groups under $1M | % $ under $1M | (dept, vendor) % $ under $1M |\n|---|---:|---:|---:|---:|---:|")
    for d, v in sorted(under_by_dept.items(), key=lambda kv: -kv[1]["dept_vendor_contract"]["dollars"]):
        u = v["dept_vendor_contract"]
        L("| {} | {} | {:,} | {:.0f}% | {:.0f}% | {:.0f}% |".format(dept_names.get(d, d), fm(u["dollars"]), u["groups"],
                                                                       u["pct_groups_under_1M"], u["pct_dollars_under_1M"],
                                                                       v["dept_vendor"]["pct_dollars_under_1M"]))
    L("\n## T7 under 1M by family\n")
    L("| Family | $ paid | (dept, vendor, contract) groups | % $ under $1M | (dept, vendor) % $ under $1M |\n|---|---:|---:|---:|---:|")
    for f, v in sorted(under_by_family.items(), key=lambda kv: -kv[1]["dept_vendor_contract"]["dollars"]):
        u = v["dept_vendor_contract"]
        L("| {} | {} | {:,} | {:.0f}% | {:.0f}% |".format(f, fm(u["dollars"]), u["groups"], u["pct_dollars_under_1M"],
                                                            v["dept_vendor"]["pct_dollars_under_1M"]))
    L("\n## T8 top vendors\n")
    L("| Vendor | 2025 paid | Depts |\n|---|---:|---|")
    for r in findings["top_vendors_all_resolved"][:25]:
        L("| {} | {} | {} |".format(r["vendor"], fm(r["paid_2025"]), "; ".join(r["depts"][:3])))
    L("\n## T9 sole source\n")
    L("| Contract | Vendor | Dept | What | 2025 paid |\n|---|---|---|---|---:|")
    for r in findings["sole_source_top_contracts"][:20]:
        L("| {} | {} | {} | {} | {} |".format(r["contract"], r["vendor"], r["dept"], r["desc"].replace("|", "/"), fm(r["paid_2025"])))
    L("\n## T10 consulting vendors\n")
    L("| Vendor | 2025 paid | Depts |\n|---|---:|---|")
    for r in findings["consulting"]["top_vendors"][:15]:
        L("| {} | {} | {} |".format(r["vendor"], fm(r["paid_2025"]), "; ".join(r["depts"][:3])))
    L("\n## T11 contract types\n")
    L("| Contract type | 2025 paid | Payments |\n|---|---:|---:|")
    for k, r in ct_tab.head(18).iterrows():
        L("| {} | {} | {:,} |".format(k, fm(r["sum"]), int(r["count"])))
    L("\n## T12 direct vouchers\n")
    L("| Class (by vendor name rules) | 2025 $ |\n|---|---:|")
    for k, v in findings["direct_vouchers"]["by_class"].items():
        L("| {} | {} |".format(k, fm(v)))
    L("\n## T13 DFSS programs\n")
    for k, v in findings["dfss_programs"].items():
        L("| {} | {} |".format(k, fm(v)))
    L("\n## T14 delegate by dept\n")
    for k, v in findings["delegate_agencies"]["by_dept"].items():
        L("| {} | {} |".format(k, fm(v)))
    L("\n## T15 procurement type paid\n")
    for k, v in findings["procurement_type_paid_breakdown"].items():
        L("| {} | {} |".format(k, fm(v)))
    open(os.path.join(RC, "report_tables.md"), "w").write("\n".join(out_md))

    # ---- stdout summary -------------------------------------------------------
    print("budget total", total_budget, "paid 2025", total_paid)
    print("vendor-payable budget", float(a[a.kind == "vendor"].amt.sum()))
    print("paid vendors resolved", float(vendor_pay[vendor_pay.dept.notna()].amount.sum()),
          "unresolved dept vendor", float(vendor_pay[vendor_pay.dept.isna()].amount.sum()))
    print("unmatched contract payments", float(p[p.pfamily == 'UNMATCHED'].amount.sum()))
    print("nonvendor DV", xf)
    print("prefix agree", prefix_agree, prefix_agree_amt)
    print("unmapped names", dict(unm), dict(cunm.head(5)))
    print("missing alias", missing_alias)
    print(proc_cov)
    print(findings["consulting"]["paid_2025"], findings["consulting"]["contract_type_only_paid_2025"])
    print("explained", explained["vendor_payable_budget"], explained["explained_by_named_contracts"], explained["explained_in_items_under_1M"])
    print(grants_summary["budget"], tif_summary["vendor_payments_over_10k_by_report_year"].get("2025"))


if __name__ == "__main__":
    main()
