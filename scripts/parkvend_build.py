#!/usr/bin/env python3
"""Build data/parks_vendors.json from:
  - raw/parkvend/ethics_rows.json   (parkvend_ethics_parse.py: District 'Vendor Payments' lists 2019-2022, vendors paid >= $10,000)
  - data/parks_2026.json            (FY2026 budget, account level)
  - raw/parkvend/legistar_matters_all.json, award_index.json (contract/fee terms, titles)
  - raw/parkvend/fac_general.json   (Federal Audit Clearinghouse totals)
Nothing is estimated. Vendor-to-budget-line mapping is explicit below, with a basis string for each rule."""
import json, os, re, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parkvend")
YEARS = (2019, 2020, 2021, 2022)
ETHICS_URLS = {
    2019: "https://www.chicagoparkdistrict.com/media/29071/download?inline",
    2020: "https://www.chicagoparkdistrict.com/media/29076/download?inline",
    2021: "https://www.chicagoparkdistrict.com/media/29081/download?inline",
    2022: "https://www.chicagoparkdistrict.com/media/29086/download?inline",
}

rows = json.load(open(os.path.join(RAW, "ethics_rows.json")))
budget = json.load(open(os.path.join(ROOT, "data", "parks_2026.json")))
acct = {x["code"]: x for x in budget["printed_all_funds"]["expenses_by_account"] if not x["is_class"]}
classes = {x["code"]: x for x in budget["printed_all_funds"]["expenses_by_account"] if x["is_class"]}
GRAND = budget["meta"]["grand_total_2026"]
PERSONNEL = classes["610000"]["amount2026"]
NONPERS = GRAND - PERSONNEL

# vendor -> year -> amount (exact payee strings are kept; same payee repeated in one year is summed)
pay = collections.defaultdict(lambda: collections.defaultdict(float))
for r in rows:
    pay[r["vendor"]][r["year"]] += r["amount"]
year_total = {y: round(sum(d.get(y, 0) for d in pay.values()), 2) for y in YEARS}

# ---- mapping rules: (budget account codes, regex over payee, basis)
# tier "A": the payee is named as the counterparty for that budget line in a Board action, the budget PDF,
#           the ordinance, or the contracts library (see research/park_vendors.md for citations).
# tier "B": line is served by a class of payees (utilities, landscape, telecom). Payee recognised by name only.
# Each rule is a GROUP: one set of payee strings covering one or more budget lines. Paid amounts are
# reported once per group (never repeated per line). kind: contract | institution | pension
RULES = [
    ("A", "contract", ["626045", "626055", "626065"], r"^SMG$", "SMG (ASM Global) holds P-12035 Soldier Field and McFetridge, and P-15018 Beverly/Morgan Park. The ERP list gives one payee total, not split by facility. The payee 'SMNG A LTD' ($0.2M to $0.4M a year) is not assumed to be SMG and is left unmapped."),
    ("A", "contract", ["626040", "626015"], r"^WESTREC (MARINAS|SMI OPCO, LLC)$", "Westrec holds harbor management P-14010 (budget PDF p264). Ice rinks P-23010 (Board action 23-1103-0913, Sep 2023) are also Westrec SMI OpCo. The payee WESTREC SMI OPCO, LLC appears only in 2022 and the list does not say which service it paid for, so harbors and ice rinks are reported as one group."),
    ("A", "contract", ["626050"], r"^CHICAGO PARK GOLF MANAGEMENT LLC$", "Golf management payee by name. The operator behind this LLC is not stated in the list. Indigo Sports P-24001 began Jan 2025 (Board action 24-1125-0911), so no payment to Indigo is published."),
    ("A", "contract", ["626010"], r"^CHICAGO CITY SKATING LLC$", "Predecessor operator of the MLK Center per the contracts library (research/park_district.md). Only the 2022 payee string matches exactly. 'CHICAGO SKATING LLC' (2019-2022) is NOT included because the list does not say which facility it ran."),
    ("A", "contract", ["626005"], r"^STANDARD PARKING CORP$|^SP PLUS CORPORATION$", "Parking management P-14012 (Standard Parking Corporation, now SP Plus)."),
    ("A", "contract", ["626030"], r"^SPAAN TECH INC$", "Cellular infrastructure management P-19014-R and P-25001 (Board actions 19-1121-0115, 25-1149-0910)."),
    ("A", "contract", ["626035"], r"^UCG ASSOCIATES, INC$", "Concession program management P-20011 (Board action 20-1212-1014)."),
    ("A", "contract", ["623030"], r"^FLOOD BROS DISPOSAL CO$", "Waste disposal contract (Flood Bros, library value $3.8M). Lakeshore Recycling also appears on the list, not counted."),
    ("A", "contract", ["625035"], r"^CCMSI$", "Third-party workers compensation administrator, Cannon Cochran Management Services Inc (P-22017, Board action 23-1096-0809), payee string CCMSI. Whether the payments are fees or claims is not stated."),
    ("A", "institution", ["625005"], r"^LINCOLN PARK ZOO$", "Ordinance Appropriation F: remittance to the Zoo."),
    ("A", "institution", ["625010"], r"^(THE\s+ART INSTITUTE OF CHICAGO|FIELD MUSEUM OF NATURAL HISTORY|MUSEUM OF SCIENCE & INDUSTRY|SHEDD AQUARIUM SOCIETY|ADLER PLANETARIUM|CHICAGO HISTORICAL SOCIETY|MUSEUM OF CONTEMPORARY ART|NATIONAL MUSEUM OF MEXICAN ART|DUSABLE MUSEUM|CHICAGO ACADEMY OF SCIENCES|INSTITUTE\s+OF PUERTO RICAN\s+ARTS & CULTURE)$", "Ordinance Appropriation F lists 11 Aquarium and Museum institutions. Payee names match all 11."),
    ("A", "pension", ["625020", "625023"], r"^PARK EMPLOYEES A&B FUND$", "Pension Fund statutory contribution (ordinance Appropriation C). 2021 includes extra supplemental payments. One payee covers both lines."),
    ("A", "institution", ["623185"], r"^GRANT PARK ORCHESTRAL ASSOCIATION$", "Grant Park Music Festival grant line."),
    ("A", "institution", ["623170"], r"^CHICAGO PARKS FOUNDATION$", "Budget line is named for this payee."),
    ("A", "institution", ["623175"], r"^NEIGHBOR\s?SPACE$", "Budget line is named for this payee."),
    ("A", "institution", ["623180"], r"^GARFIELD PARK CONSERVATORY ALLIANCE$", "Budget line is named for this payee."),
    ("B", "contract", ["626060"], r"^MAGGIE DALEY PARK$", "Payee string is the park name, not a company. Operator in 2019-2022 is not named in the list. Name match only."),
    ("B", "contract", ["626025"], r"^(MOORE LANDSCAPES, LLC|SPEEDY GONZALEZ LANDSCAPING INC|CHRISTY WEBBER (LANDSCAPES|& CO)|CLAUSS BROTHERS INC)$", "Landscape contractors. Mapping to 626025 is by contractor type (inference). Other landscape vendors may exist."),
    ("B", "contract", ["623070", "623075"], r"^(PEOPLES GAS-PAYMENT PROCESSING|COMED|COMMONWEALTH EDISON CO|DIRECT ENERGY BUSINESS|CENTERPOINT ENERGY SERVICES INC|SYMMETRY ENERGY SOLUTIONS, LLC|CENTRIO ENERGY CHICAGO LLC)$", "Gas and electric suppliers, by name. Water and sewer 623080 is not mapped (payee not identified)."),
    ("B", "contract", ["623015"], r"^(AT&T|COMCAST|VERIZON WIRELESS|WINDSTREAM)$", "Telecom carriers, by name."),
    ("B", "contract", ["626075"], r"^(ENTERPRISE FLEET MANAGEMENT|ENTERPRISE LEASING)$", "Vehicle leasing (City contract 126710, Board action 25-1200-1119). Fleet fuel and repairs are via City DFFM IGA 25-1145-0910, not visible here."),
]
# Payees that appear on the list but are NOT vendor spending in the operating budget sense
NOT_VENDOR = [
    (r"^PARK EMPLOYEES A&B FUND$", "pension contribution (mapped to 625020/625023 above)"),
    (r"^CITY OF CHICAGO$", "City of Chicago, purpose not stated in the list"),
]

def norm_rows():
    out = []
    for v, d in pay.items():
        out.append((v, {y: round(d.get(y, 0), 2) for y in YEARS}))
    return out

SHARED = {}
groups = []
payee_used = collections.defaultdict(list)
for tier, kind, codes, rx, basis in RULES:
    pat = re.compile(rx)
    hits = {v: a_ for v, a_ in norm_rows() if pat.search(v)}
    for v in hits:
        payee_used[v].append(codes)
    groups.append({
        "accounts": codes,
        "account_names": [acct[c]["name"] for c in codes],
        "kind": kind, "tier": tier,
        "budget2026": sum(acct[c]["amount2026"] for c in codes),
        "budget2025": sum(acct[c]["amount2025"] for c in codes),
        "basis": basis,
        "payees": [{"payee": v, "paid_by_year": a_} for v, a_ in sorted(hits.items(), key=lambda kv: -sum(kv[1].values()))],
        "paid_by_year": sumy(hits) if False else {y: round(sum(a_[y] for a_ in hits.values()), 2) for y in YEARS},
    })
lines = groups

def line_budget(codes):
    return sum(acct[c]["amount2026"] for c in codes)

def gcodes(**kw):
    out = []
    for g in groups:
        if all(g[k] == v for k, v in kw.items()) and any(p for p in g["payees"]):
            out += g["accounts"]
    return out

tierA_codes = gcodes(tier="A")
tierB_codes = gcodes(tier="B")
tierA_nopay = [g["accounts"] for g in groups if g["tier"] == "A" and not g["payees"]]
A_contract = gcodes(tier="A", kind="contract")
A_inst = gcodes(tier="A", kind="institution")
A_pension = gcodes(tier="A", kind="pension")

# Non-personnel buckets that are not vendor spending by nature
DEBT = acct["600005"]["amount2026"] + acct["600015"]["amount2026"]
TRANSFERS = acct["625065"]["amount2026"] + acct["625060"]["amount2026"]
JUDG = acct["625015"]["amount2026"]
vendor_like = NONPERS - DEBT
def pct(x, base):
    return round(100 * x / base, 1)

cov = {
    "grand_total_2026": GRAND,
    "personnel_610000": PERSONNEL,
    "non_personnel_2026": NONPERS,
    "of_which_debt_service_600005_600015": DEBT,
    "non_personnel_excluding_debt": vendor_like,
    "budget_2026_by_mapping": {
        "A_contract_named_counterparty": {"accounts": A_contract, "budget_2026": line_budget(A_contract), "pct_of_non_personnel": pct(line_budget(A_contract), NONPERS)},
        "A_institution_remittances_and_grants": {"accounts": A_inst, "budget_2026": line_budget(A_inst), "pct_of_non_personnel": pct(line_budget(A_inst), NONPERS)},
        "A_pension_contribution": {"accounts": A_pension, "budget_2026": line_budget(A_pension), "pct_of_non_personnel": pct(line_budget(A_pension), NONPERS)},
        "B_payee_class_by_name_only": {"accounts": tierB_codes, "budget_2026": line_budget(tierB_codes), "pct_of_non_personnel": pct(line_budget(tierB_codes), NONPERS)},
    },
    "tier_A_total_budget_2026": line_budget(tierA_codes),
    "tier_A_pct_of_non_personnel": pct(line_budget(tierA_codes), NONPERS),
    "tier_A_pct_of_non_personnel_excl_debt_and_pension": pct(line_budget(tierA_codes) - line_budget(A_pension), vendor_like - line_budget(A_pension)),
    "tier_A_plus_B_budget_2026": line_budget(tierA_codes) + line_budget(tierB_codes),
    "tier_A_plus_B_pct_of_non_personnel": pct(line_budget(tierA_codes) + line_budget(tierB_codes), NONPERS),
    "unmapped_non_personnel_budget_2026": NONPERS - line_budget(tierA_codes) - line_budget(tierB_codes),
    "paid_2022_tier_A": round(sum(g["paid_by_year"][2022] for g in groups if g["tier"] == "A"), 2),
    "caveats": [
        "Paid amounts are calendar 2019-2022 only (latest list published). They are not 2026 spend.",
        "Budget dollars are 2026 appropriations for lines whose counterparty the sources name. They are not paid amounts.",
        "The list only shows payees paid $10,000 or more in a 12-month period and has no contract, department or account detail.",
        "Coverage here means 'a named payee with a published paid amount exists for this budget line in 2019-2022', not that the 2026 line is explained by those payees.",
    ],
}
# Payee-level view: all 2022 payees, flagged
def classify(v):
    for rx, why in NOT_VENDOR:
        if re.search(rx, v):
            return why
    return None

all_payees = []
for v, a in norm_rows():
    all_payees.append({"payee": v, "paid_by_year": a, "mapped_budget_lines": sorted({c for g in payee_used.get(v, []) for c in g}),
                       "note": classify(v) or ""})
all_payees.sort(key=lambda x: -(x["paid_by_year"][2022] or max(x["paid_by_year"].values())))

mapped_payees_2022 = sum(p["paid_by_year"][2022] for p in all_payees if p["mapped_budget_lines"])
notv_2022 = sum(p["paid_by_year"][2022] for p in all_payees if p["note"] and not p["mapped_budget_lines"])
list_cov = {
    "list_total_by_year": year_total,
    "payee_rows_by_year": {y: sum(1 for r in rows if r["year"] == y) for y in YEARS},
    "2022_total": year_total[2022],
    "2022_mapped_to_a_budget_line": round(mapped_payees_2022, 2),
    "2022_city_of_chicago_payee_unmapped": round(notv_2022, 2),
    "2022_other_unmapped": round(year_total[2022] - mapped_payees_2022 - notv_2022, 2),
}

# ACFR comparators (General Fund, budgetary basis, $ thousands, FY2022 ACFR printed p89)
acfr = {
    "source": "FY2022 ACFR, Required Supplementary Information, General Fund budget vs actual (PDF p97, printed p89)",
    "url": "https://files.chicagoparkdistrict.com/2025-04/2022%20Annual%20Comprehensive%20Financial%20Report.pdf",
    "fy2022_general_fund_actual_thousands": {"personnel_services": 168243, "materials_supplies": 5848, "small_tools_equipment": 454, "contractual_services": 172498, "program_expense": 369, "other_expense": 6743, "supplemental_pension": 15000, "principal_retirement": 21962, "total": 391117},
}
# the ethics list is cash paid to payees in the ERP, ACFR is accrual on the General Fund, so they are not compared line by line

fac = json.load(open(os.path.join(RAW, "fac_general.json")))
fac_out = [{"audit_year": x["audit_year"], "report_id": x["report_id"], "total_federal_expended": x["total_amount_expended"], "accepted": x["fac_accepted_date"]} for x in fac]

# Management fee terms from Board exhibits
fees = [
    {"vendor": "ASM Global (SMG dba)", "asset": "Maggie Daley Park", "contract": "P-24009", "board_action": "25-1070-0409",
     "url": "https://legistar2.granicus.com/chicagoparkdistrict/attachments/59187994-fdc6-4764-8b26-b29c8a5b1362.pdf",
     "management_fee_by_year": {"2025": 200000, "2026": 200000, "2027": 200000, "2028": 225000, "2029": 225000, "2030": 225000, "2031": 250000},
     "capital_investment_by_year": {"2025": 50000, "2026": 25000, "2027": 15000, "2028": 10000, "2029": 10000, "2030": 10000, "2031": 10000},
     "kind": "contract schedule, not payments"},
    {"vendor": "Indigo Sports, LLC", "asset": "golf courses", "contract": "P-24001", "board_action": "24-1125-0911",
     "management_fee_per_year": 1275000, "contractor_capital_by_year": {"1": 3575000, "2": 1200000, "3": 1700000, "4": 525000, "5": 1250000, "6": 200000, "7": 150000, "8": 150000, "9": 150000, "10": 100000},
     "kind": "contract schedule, not payments"},
]

out = {
    "meta": {
        "generated_by": "scripts/parkvend_build.py",
        "question": "What did the Chicago Park District actually pay each vendor?",
        "answer": "Only one public source exists: the Ethics Ordinance 'Vendor Payments' lists for calendar years 2019, 2020, 2021 and 2022 (payee and amount, vendors paid $10,000 or more in a 12-month period). Nothing later than 2022 is published. No contract, department or account is shown.",
        "source_urls": ETHICS_URLS,
        "source_page": "https://www.chicagoparkdistrict.com/ethics-office",
        "file_urls_on_cdn": {y: f"https://files.chicagoparkdistrict.com/2025-05/{y}%20Vendor%20Payments%20-%20Ethics%20Ordinance%20Report.pdf" for y in YEARS},
    },
    "coverage": cov,
    "list_coverage": list_cov,
    "mapping_groups": groups,
    "payees": all_payees,
    "contract_fee_schedules_from_board_exhibits": fees,
    "acfr_context": acfr,
    "federal_single_audit_totals": {"source": "https://api.fac.gov/general (Federal Audit Clearinghouse)", "rows": fac_out,
                                    "note": "Totals of federal awards the District spent. Not vendor payments."},
}
json.dump(out, open(os.path.join(ROOT, "data", "parks_vendors.json"), "w"), indent=1)

# ---- checks
print("year totals", year_total)
print("non-personnel 2026", NONPERS, "excl debt", vendor_like)
print(json.dumps(cov["budget_2026_by_mapping"], indent=1))
print("A", cov["tier_A_total_budget_2026"], cov["tier_A_pct_of_non_personnel"], "% | excl pension:", cov["tier_A_pct_of_non_personnel_excl_debt_and_pension"])
print("A+B", cov["tier_A_plus_B_budget_2026"], cov["tier_A_plus_B_pct_of_non_personnel"], "% unmapped", cov["unmapped_non_personnel_budget_2026"])
print("no payees", tierA_nopay)
print(json.dumps(list_cov, indent=1))
for g in groups:
    print(g["accounts"], g["tier"], g["kind"], g["budget2026"], g["paid_by_year"])
# payee double-use check
dups = {v: c for v, c in payee_used.items() if len(c) > 1}
print("payees in >1 group:", dups)
