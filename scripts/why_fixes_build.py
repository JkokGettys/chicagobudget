"""Writes the 'why' split files that replace stale or generic why sentences and explain negative boxes
(launch fix 1). Run from the repo root: python3 scripts/why_fixes_build.py
Output: data/splits/city/why_fixes.json, data/splits/cps/why_fixes.json, data/splits/parks/why_fixes.json
Every sentence uses only facts already in the repo (cited in each entry's 'evidence'). No numbers are new."""
import json, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

ORD = "2026 Annual Appropriation Ordinance, dataset 6694-f78c"
def ol(fund, dept, auth, acct, amount, why, note=None, evidence=None):
    d = {"target": {"by": "ordinance_line", "fund": fund, "dept": dept, "authority": auth, "account": acct},
         "expect_amount": amount, "mode": "side_only", "why": why}
    if note: d["note"] = note
    if evidence: d["evidence"] = evidence
    return d
def byid(i, amount, why, note=None, evidence=None):
    d = {"target": {"by": "id", "id": i}, "expect_amount": amount, "mode": "side_only", "why": why}
    if note: d["note"] = note
    if evidence: d["evidence"] = evidence
    return d

PAYREC = "the City's payment records show what each company or group was paid but not which budget line paid it"

city = [
 ol("0100", 57, "1005", "0937", 25000000,
    "This pays the medical bills of Police Department employees who were hurt on the job and are not covered by workers' compensation. The budget gives one total, and we found no public list of the bills.",
    evidence="Line name in " + ORD),
 ol("0200", 88, "2020", "0020", 11866140,
    "This is overtime pay for crews in the Bureau of Water Supply. The City reports 2025 overtime for the whole Water Department ($47.8 million over 95 job titles) but not for each bureau, so we cannot split this line.",
    evidence="data/leaves_over_10m.json note for the Water overtime lines (2025 payroll costing dawh-m56b)"),
 ol("0200", 88, "2025", "0020", 19314459,
    "This is overtime pay for crews in the Bureau of Operations and Distribution. The City reports 2025 overtime for the whole Water Department ($47.8 million over 95 job titles) but not for each bureau, so we cannot split this line.",
    evidence="data/leaves_over_10m.json note for the Water overtime lines (2025 payroll costing dawh-m56b)"),
 ol("0B93", 50, "2005", "9263", 11192277,
    "This pays for homeless services and is paid from a fund set aside for that purpose (the Houseshare Surcharge Homeless Services Fund). The budget gives one total, and " + PAYREC + ".",
    evidence="Fund name in " + ORD + "; payment records carry no budget line"),
 byid("city.city-development.department-of-housing.grant-money-not-yet-assigned-to-projects.925f-federal-grant-fund.925f-2833-909a.other-not-itemised", 32755405.69,
    "This is part of the federal HOME housing grant money the City expects to receive. The City's grant ledger (dated 2026-05-31) names projects for only part of it, and this rest is not matched to any named project.",
    evidence="Parent note: named projects come from the City's Mid-Year Grants ledger, dated 2026-05-31 (research/cdot_projects.md, other reserve lines)"),
 ol("0100", 6, "2150", "0149", 14942252,
    "This pays for software upkeep and licenses used across City departments. The budget gives one total, and " + PAYREC + ".",
    evidence="Line name in " + ORD),
 ol("0100", 38, "2131", "0155", 22807498,
    "This is rent the City pays for space and property it leases. The budget gives one total, and " + PAYREC + ".",
    evidence="Line name in " + ORD),
 ol("0355", 38, "2126", "9188", 10159160,
    "This pays part of the cost of running Millennium Park. Two other budget lines also pay for it (the main fund has $5.38 million and the special events fund has $3.83 million in Cultural Affairs), and " + PAYREC + ".",
    evidence="Three account 9188 lines in " + ORD + ": fund 0100 dept 38 $5,380,000, fund 0355 dept 23 authority 2015 $3,830,000, fund 0355 dept 38 $10,159,160"),
 byid("city.citywide.corporate-fund.0100-2005-0931.not-spent-yet", 36144850.99,
    "This is the part of the full-year settlements budget that has not been matched to a payment yet. The Law Department payment list we have only runs from 2026-01-02 to 2026-07-31 and places payments here by department only, so more may be paid later or sit on another line.",
    evidence="Note on the parent line (Law Department payments report, 2026-01-02 to 2026-07-31, unaudited)"),
 ol("0100", 99, "2005", "9222", 124725187,
    "The budget does not say what this line pays for. It is listed under Finance General as 'purposes as specified' and has stayed near $125 million since 2024. Our best guess is a payment to the State linked to the ambulance Medicaid program, but no City document confirms it, so treat the use as unconfirmed.",
    evidence="research/parks_misc_detail.md section 6 (account 9222: 'I could not establish what this line pays for')"),
 ol("0100", 41, "1005", "9646", -3085466,
    "This is a credit, not a payment: the ordinance prints it as a negative amount that lowers the Public Health Department's main-fund total. Its name refers to American Rescue Plan 'revenue replacement', which is federal pandemic aid used in place of lost City revenue. The ordinance does not say how this line is figured.",
    evidence="Line name in " + ORD + "; research/new_sources.md section 5 (ARPA money used as revenue replacement)"),
 byid("city.public-safety.chicago-police-department.programs-and-other-costs.0100-corporate-fund.0100-1005-0931.over-budget-so-far", -151741708.64,
    "Settlement payments so far this year ($234.3 million through 2026-07-31) are bigger than the $82.6 million budgeted for this line. This negative box keeps the boxes adding up to the budget, and the City plans to borrow to cover the extra.",
    evidence="Sibling paid_to_date boxes sum to $234,299,708.64 against the $82,558,000 line; the 2026 Budget Overview financing statement is quoted in the parent box note"),
]

cps = [
 byid("cps.citywide.set-asides.u12670.reserves.a57940.fg115-000000-p231601-0", 35000000,
    "This is a central CPS amount in a 'miscellaneous charges' account under the Labor and Employee Relations program. It sits with the district's central set-asides, not with a list of purchases, and we found no CPS document that says what it will be used for.",
    evidence="Fund, program and account in the CPS FY2026 budget data; research/final_gap_audit.md tier C"),
 byid("cps.citywide.set-asides.u12670.reserves.a57940.fg115-005058-p009546-1", 20000000,
    "This is money CPS holds centrally under a program called School Transitions, in a fund called New and Expansion School Funding. It sits with the district's central set-asides, not with a list of purchases, and we found no list of which schools get it.",
    evidence="Fund and program names in the CPS FY2026 budget data"),
 byid("cps.citywide.set-asides.u12670.contracts.a54125.fg362-376690-p119027-0", 32912073.49,
    "This is State Preschool for All money for ages 3 to 5, booked as outside services. We could not find where CPS sends it. The similar $88.1 million line for ages 0 to 3 is passed to the City, which pays community preschool programs, but no document says this line works the same way.",
    note="Related City boxes: the City's 'For Delegate Agencies (ISBE - CPS - Early Childhood Block Grant)' line under Family and Support Services lists the community programs the City pays from the same kind of state grant. Whether any of this $32.9 million reaches them is not stated in the sources.",
    evidence="research/cps_tree_deep.md section 5 and data/splits/cps/cpsdeep_services.json"),
 byid("cps.citywide.early-childhood.u11385.contracts.a54125.fg362-376689-p410001-0", 88143619,
    "CPS passes this State Preschool for All money to the City's Family and Support Services department, which pays about 88 community preschool and infant and toddler programs. The programs are in the City part of this tree, so there is nothing smaller to show here.",
    note="Where the money lands: in the City tree, Family and Support Services > For Delegate Agencies (ISBE - CPS - Early Childhood Block Grant). That City line is $63.7 million and payments to named programs so far this year are $71.6 million.",
    evidence="Board Reports 25-0925-EX2 and 26-0730-EX2 (data/splits/cps/cpsdeep_services.json); City tree boxes under 925s-2962-0135 (paid_to_date $71,617,007.54 against a $63,664,481 line)"),
 byid("cps.citywide.set-asides.u12670.reserves.a57915.fg114-000000-p111086-12", -8000000,
    "This is a planned cut, not a payment. It is a negative amount in CPS's contingency account that offsets spending counted on other lines, and CPS does not explain this particular line.",
    evidence="Negative budget-only offsets, research/cps_deep.md; same wording as the inventory sentence for account A57915"),
 byid("cps.citywide.set-asides.u12670.reserves.a57915.fg114-000000-p127725-13", -7500000,
    "This is a planned cut, not a payment. It is a negative amount in CPS's contingency account that offsets spending counted on other lines, and CPS does not explain this particular line.",
    evidence="Negative budget-only offsets, research/cps_deep.md; same wording as the inventory sentence for account A57915"),
 byid("cps.citywide.set-asides.u12670.reserves.a57915.fg353-041008-p888888-14", -5161994.31,
    "This is a planned cut, not a payment. It is a negative amount in CPS's contingency account that offsets spending counted on other lines, and CPS does not explain this particular line.",
    evidence="Negative budget-only offsets, research/cps_deep.md; same wording as the inventory sentence for account A57915"),
]

parks = [
 byid("parks.maintaining-the-parks.facilities-management-specialty-trades-8485.corporate-fund.611010", -1151021,
    "The District's official name for this account is 'Employee Health Care Contribution'. We read the negative amount as the share of health insurance cost that employees pay themselves, which lowers the District's cost.",
    evidence="Official account name in extra.official_name (Park District 2026 Budget Appropriations, p. 107)"),
 byid("parks.utilities-benefits-and-shared-costs.610000.611011", -15171602,
    "The District assumes some jobs will sit empty for part of the year, so it subtracts the pay it expects not to spend. The pay lines elsewhere in the tree are the full-year pay for every job.",
    evidence="Official name 'Vacancy Allowance', account 611011 (Park District 2026 Budget Appropriations)"),
]

def write(gov, splits, desc):
    path = os.path.join(ROOT, "data", "splits", gov, "why_fixes.json")
    json.dump({"meta": {"author": "launch fix 1", "description": desc, "built_by": "scripts/why_fixes_build.py"},
               "splits": splits}, open(path, "w"), indent=1)
    print(path, len(splits))

write("city", city, "Plain-English why sentences replacing generic or stale ones, and explanations for negative boxes (no boxes added, amounts unchanged)")
write("cps", cps, "Plain-English why sentences for reserve and preschool boxes that wrongly said 'a few large companies', plus negative contingency boxes")
write("parks", parks, "Explanations for the two negative Parks boxes")
