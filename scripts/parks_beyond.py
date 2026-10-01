#!/usr/bin/env python3
"""Step 4: parks_beyond.py -> merges a `beyond_operating` block into data/parks_2026.json.

Run order: parks_extract.py, parks_parse.py, parks_build.py (writes the file), then this script (adds to it).

Everything that is NOT a line of the 2026 operating budget tables, each with its source:
  * Appropriation Ordinance (budget PDF pp 249-254): appropriation by fund, incl. capital funds,
    and the per-series bond debt service schedule (Appropriation M).
  * Managed-asset contracts: Chicago Park District Bonfire public contracts library (vendor,
    term, stated value) plus Board of Commissioners actions on Legistar (fees).
  * Pension: Park Employees' Annuity and Benefit Fund 2025 actuarial valuation (Segal) and the
    District's FY2025 ACFR.
  * ACFR FY2025: General Fund budget vs actual, GO debt schedule, net pension liability.
  * Capital: category-level CIP (budget PDF p69) and the project-level list of capital
    projects (ArcGIS layer cap24_3, 3,116 projects, NO dollar amounts) joined to park numbers.

Inputs live in raw/parks (gitignored): words.json, cap24_projects.json,
bonfire_contracts_nonclosed.json, legistar_*.txt, pension_valuation_text.json, acfr25_text.json.
Nothing is estimated. Where a number is not published, the field says so.
"""
import json, os, re, sys, collections

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parks_parse import group_lines  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parks")
MAIN = os.path.join(ROOT, "data", "parks_2026.json")


def money(tok):
    neg = "(" in tok or tok.startswith("-")
    n = int(re.sub(r"[^\d]", "", tok))
    return -n if neg else n


def parse_ordinance(words):
    """Appropriation by fund (p252-254) and bond-series schedule (p253)."""
    funds = []
    cur = None
    for pg in (252, 253, 254):
        for ln in group_lines(words[str(pg)]):
            t = " ".join(w[0] for w in ln)
            m = re.match(r"^Appropriation ([A-P])\s*\.?$", t)
            if m:
                cur = {"letter": m.group(1), "name": None, "lines": [], "total": None, "page": pg}
                funds.append(cur)
                continue
            if cur is None:
                continue
            if cur["name"] is None and not t.startswith("Amount") and not t.startswith("For "):
                cur["name"] = t
                continue
            m = re.match(r"^Total Appropriation \$ ?(-|[\d,]+)$", t)
            if m:
                cur["total"] = 0 if m.group(1) == "-" else money(m.group(1))
                continue
            m = re.match(r"^(Personnel Services|Materials & Supplies|Tools & Equipment|Contractual Services|Program Expense|Other Expense|Fixed Asset Expense|Liability Insurance and Claims|Workers' Compensation|Liability Expenses|Judgments|Unemployment Obligations|Pension Expense|Supplemental Contribution to Pension Fund)(?: \d)? \$ ?(-|[\d,]+)$", t)
            if m:
                cur["lines"].append({"name": m.group(1), "amount": 0 if m.group(2) == "-" else money(m.group(2))})
    # Appropriation F (museums)
    museums = []
    for ln in group_lines(words["252"]):
        t = " ".join(w[0] for w in ln)
        m = re.match(r"^\d+\.For the (.+?) \$ ([\d,]+) \$ \(([\d,]+)\) \$ ([\d,]+) \$ ([\d,]+)$", t)
        if m:
            museums.append({"name": m.group(1), "tax_levy": money(m.group(2)), "anticipated_loss_in_collection": -money(m.group(3)),
                            "ppr_tax": money(m.group(4)), "total": money(m.group(5))})
    # Bond series (p253)
    series = []
    started = False
    for ln in group_lines(words["253"]):
        t = " ".join(w[0] for w in ln)
        if t.startswith("For Redemption"):
            started = True
            continue
        if not started:
            continue
        nums = [w for w in ln if re.match(r"^[\d,]+$", w[0])]
        name = " ".join(w[0] for w in ln if not re.match(r"^[\d,]+$", w[0]) and w[0] != "$")
        if t.startswith("Total Appropriation"):
            series.append({"name": "TOTAL", "principal": money(nums[0][0]), "interest": money(nums[1][0]), "total": money(nums[2][0])})
            break
        if not nums or not (name.startswith("General Obligation") or name.startswith("Future")):
            continue
        # columns: redemption x1~366, interest x1~419, total x1~453
        cols = {"principal": None, "interest": None, "total": None}
        for w in nums:
            if abs(w[2] - 365.8) < 6: cols["principal"] = money(w[0])
            elif abs(w[2] - 419.0) < 6: cols["interest"] = money(w[0])
            elif abs(w[2] - 453.2) < 6: cols["total"] = money(w[0])
        series.append({"name": name, **{k: (v or 0) for k, v in cols.items()}})
    return funds, museums, series


def main():
    words = json.load(open(os.path.join(RAW, "words.json")))
    funds, museums, series = parse_ordinance(words)
    checks = []

    def check(name, ok, **kw):
        checks.append({"name": name, "pass": bool(ok), **kw})

    tot = series[-1]
    body = series[:-1]
    d_p = sum(r["principal"] for r in body) - tot["principal"]
    d_i = sum(r["interest"] for r in body) - tot["interest"]
    d_t = sum(r["total"] for r in body) - tot["total"]
    check("Bond series (p253): 25 series plus Future Issuance (26 rows) sum to printed Total within $2 (principal, interest, total)",
          max(abs(d_p), abs(d_i), abs(d_t)) <= 2 and all(r["principal"] + r["interest"] == r["total"] for r in body),
          series=len(body), principal=tot["principal"], interest=tot["interest"], total=tot["total"],
          row_sum_minus_printed={"principal": d_p, "interest": d_i, "total": d_t}, note="PDF rounding: rows sum $1 above the printed interest and total")
    check("Bond series principal == operating budget 600015 Principal Pymt Bond Debt Service 34,630,000", tot["principal"] == 34_630_000)
    gap = 35_926_546 - tot["interest"]
    check("Bond-series interest 34,826,546 vs operating 600005 Interest Expense 35,926,546", gap == 1_100_000,
          difference=gap, note="Ordinance footnote 1 (p252): General Fund Other Expense 'includes ... Interest Expense of $1.1 million' outside the bond schedule")
    mus = sum(m["total"] for m in museums)
    for f in funds:
        if f["letter"] == "F" and f["total"] is None:
            f["total"] = mus
            f["lines"] = [{"name": m["name"], "amount": m["total"]} for m in museums]
        if f["letter"] == "M" and f["total"] is None:
            f["total"] = tot["total"]
            f["lines"] = [{"name": r["name"], "amount": r["total"], "principal": r["principal"], "interest": r["interest"]} for r in body]
    check("Museums (App. F p252): 11 institutions sum to 29,617,600 == operating 625010", len(museums) == 11 and mus == 29_617_600, sum=mus)
    ap = {f["letter"]: f for f in funds}
    for f in funds:
        if f["lines"] and f["total"] is not None and f["letter"] != "C":
            s = sum(l["amount"] for l in f["lines"])
            check(f"Appropriation {f['letter']} ({f['name']}): lines sum to Total within $2", abs(s - f["total"]) <= 2, sum=s, total=f["total"], diff=s - f["total"])
    check("Appropriation C pension = 63,332,412 + 6,000,000 = 69,332,412", ap["C"]["total"] == 69_332_412)

    # funds -> classification
    kind = {"A": "operating", "B": "operating", "C": "operating", "D": "operating", "E": "operating", "F": "operating",
            "G": "capital", "H": "operating", "I": "operating", "J": "capital", "K": "capital", "L": "capital",
            "M": "debt service", "N": "capital", "O": "capital", "P": "operating (capital staff)"}
    appropriations = [{"letter": f["letter"], "name": f["name"], "kind": kind.get(f["letter"]), "total": f["total"],
                       "lines": f["lines"], "page": f["page"], "printed_page": f["page"] - 6} for f in funds]
    capital_total = sum(f["total"] for f in funds if kind.get(f["letter"]) == "capital")
    oper_approps = sum(f["total"] for f in funds if f["letter"] in "ABCDEFGHI")

    # ---------------- capital projects (ArcGIS), joined to budget parks
    cap = json.load(open(os.path.join(RAW, "cap24_projects.json")))
    main_data = json.load(open(MAIN))
    parks = {}

    def walk(n):
        if n["type"] == "park" and n.get("unit_code"):
            parks[int(n["unit_code"])] = {"id": n["id"], "name": n["name"]}
        for c in n.get("children", []):
            walk(c)
    walk(main_data["tree"])
    st = collections.Counter(r["STATUS_1"] for r in cap)
    active = [r for r in cap if r["STATUS_1"] != "COMPLETE"]
    by_park = collections.defaultdict(lambda: collections.Counter())
    for r in cap:
        if r["PARK_NO"] is not None and int(r["PARK_NO"]) in parks:
            by_park[int(r["PARK_NO"])][r["STATUS_1"]] += 1
    matched = sum(1 for r in cap if r["PARK_NO"] is not None and int(r["PARK_NO"]) in parks)
    matched_active = sum(1 for r in active if r["PARK_NO"] is not None and int(r["PARK_NO"]) in parks)
    check("Capital projects layer: every project counted; status counts sum to 3,116", sum(st.values()) == len(cap) == 3116)
    cap_summary = {
        "source": "https://services7.arcgis.com/HpTF5nhGpVZolZvo/arcgis/rest/services/cap24_3/FeatureServer/0 (the 'Capital Projects 2024' map on chicagoparkdistrict.com/capital-improvement-project-map, map as of April 2024)",
        "fields": ["Project_No", "PARK_NAME", "PARK_NO", "Scope", "Ward", "Region_1", "SUB_PROGRA", "STATUS_1", "YEAR_COMPL"],
        "has_dollar_amounts": False,
        "projects": len(cap), "by_status": dict(st),
        "joined_to_budget_park_number": {"projects": matched, "active_or_pending_projects": matched_active,
                                         "budget_parks_with_at_least_one_project": len(by_park)},
        "active_projects_by_park_number": {str(k): {"park": parks[k]["name"], **dict(v)} for k, v in sorted(by_park.items())
                                           if any(s != "COMPLETE" for s in v)},
        "note": "The District does not publish a per-project dollar budget for the 2026-2030 CIP. This list says WHAT is planned per park (scope, status), not HOW MUCH.",
    }
    # keep only active/pending projects inline (complete ones stay in raw/parks/cap24_projects.json)
    slim = [{"project_no": int(r["Project_No"]) if r["Project_No"] is not None else None, "park_no": int(r["PARK_NO"]) if r["PARK_NO"] is not None else None,
             "park": r["PARK_NAME"], "scope": r["Scope"], "ward": int(r["Ward"]) if r["Ward"] is not None else None, "region": r["Region_1"],
             "sub_program": r["SUB_PROGRA"], "status": r["STATUS_1"], "year_complete": int(r["YEAR_COMPL"]) if r["YEAR_COMPL"] else None}
            for r in active]
    cap_summary["active_and_pending_projects"] = slim
    cap_summary["complete_projects_not_inlined"] = st["COMPLETE"]

    # ---------------- contracts
    bon = json.load(open(os.path.join(RAW, "bonfire_contracts_nonclosed.json")))
    cols = bon["columns"]
    rows = [dict(zip(cols, r)) for r in bon["rows"]]
    for r in rows:
        r["value"] = float(r["value"]) if r["value"] not in (None, "") else None
        r["status"] = {"1": "pending (starts later)", "2": "active"}.get(r["status_code"], "other")
        r["bonfire_url"] = "https://chicagoparkdistrict.bonfirehub.com/publicContracts/" + r["id"]
    managed = {
        "626045 Soldier Field Management": {"budget2026": 36_292_135, "budget2025": 35_201_203, "vendor": "SMG (ASM Global)",
            "contract": "P-12035 Management and Operation of Soldier Field Complex, McFetridge Center & Stadium at Devon & Kedzie",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/8150",
            "terms": "Library shows status 'pending', term Apr 1 2027 to Mar 31 2028, stated value $0 (the library does not hold the live operating agreement terms). Budget PDF p45 (printed 39): Soldier Field is projected at $62.9M gross revenue and $36.3M gross expense in 2026; the contractor collects event revenue and the District receives Bears rent and ISFA subsidy.",
            "evidence": "SMG appears as Soldier Field manager in older Bonfire records (P-07038, 2011) and ASM Global is the SMG successor (Board action 25-1070-0409 is titled 'SMG dba ASM Global'). A current ASM/SMG operating agreement for Soldier Field itself is not published in the library. Vendor contact for ASM Global's Maggie Daley contract is at soldierfield.net."},
        "626040 Harbor Management": {"budget2026": 16_580_506, "budget2025": 15_599_713, "vendor": "WESTREC SMI OpCo LLC (fka Westrec Marina Management, Inc.)",
            "contract": "P-14010 Management and Operation of Chicago Park District Harbor System",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/8192",
            "terms": "Active, May 1 2026 to Apr 30 2027, not extendable, library value $0. Budget PDF p264-265 prints 'Managed by Westrec SMI'. Ten harbors. Harbor-backed debt service is $10.6M in 2026 (PDF p46, printed 40)."},
        "626050 Golf Management": {"budget2026": 8_490_697, "budget2025": 8_141_644, "vendor": "Indigo Sports, L.L.C. (Troon)",
            "contract": "P-24001 Management, Maintenance, and Operation of Chicago Park District Golf Facilities",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/223863",
            "terms": "Active Jan 1 2025 to Dec 31 2034. Board action 24-1125-0911 (Aug 14 2024). Exhibit A: management fee $1,275,000 per year (10% retainage $127,500 withheld pending annual review), $9 million total capital investment at the contractor's expense (years 1 to 10: 3,575,000 / 1,200,000 / 1,700,000 / 525,000 / 1,250,000 / 200,000 / 150,000 / 150,000 / 150,000 / 100,000), Troon Community Fund $25,000 per year. Prior manager: Billy Casper Golf (closed 2024)."},
        "626060 Maggie Daley Park Management": {"budget2026": 4_387_340, "budget2025": 6_006_610, "vendor": "ASM Global (SMG dba ASM Global)",
            "contract": "P-24009 Management and Operation of Maggie Daley Park",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/256223",
            "terms": "Active Apr 24 2026 to Apr 23 2033, extendable, library value $1,525,000. Board action 25-1070-0409 (Mar 14 2025). Exhibit A: management fee 2025 to 2031 = 200,000 / 200,000 / 200,000 / 225,000 / 225,000 / 225,000 / 250,000 per year; contractor capital investment 2025 to 2031 = 50,000 / 25,000 / 15,000 / 10,000 / 10,000 / 10,000 / 10,000. Budget PDF p51 (printed 45): expenses fall $1.6M to $4.4M 'due to operational efficiencies from a new contracted vendor'. Prior manager: Transwestern Commercial Services (closed 2025)."},
        "626010 MLK Center Management": {"budget2026": 1_548_354, "budget2025": 1_628_081, "vendor": "Chicago Skating Partners LLC",
            "contract": "P-25008 Management and Operation of the Rev. Dr. Martin Luther King, Jr. Family Entertainment Center",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/281275",
            "terms": "Active Jul 1 2026 to Jul 1 2033, library value $1,698,172. Board action 26-1263-0211 (Jan 23 2026). Prior manager: Chicago City Skating, LLC (closed Jul 1 2026)."},
        "626065 Beverly Morgan Park Sports Complex Management": {"budget2026": 1_817_652, "budget2025": 1_762_708, "vendor": "SMG",
            "contract": "P-15018 Management and Operation of Beverly/Morgan Park Sports Complex",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/8242",
            "terms": "Active Jan 1 2026 to Mar 31 2028, library value $530,914. Board action 25-1168-1008 (Sep 12 2025) extended the agreement."},
        "626066 Addams Park Sports Center Management / 626067 Gately Park Management": {"budget2026": 1_420_960 + 1_569_260, "budget2025": 1_383_762 + 1_567_962, "vendor": "ASM Global",
            "contract": "P-19021 Management and Operation of the Gately Park Indoor Track and Field Facility and Addams Park Recreation Center",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/60567",
            "terms": "Library status 'pending', Dec 16 2026 to Dec 15 2027, extendable, library value $530,911."},
        "626055 McFetridge Sports Center Management": {"budget2026": 3_243_300, "budget2025": 3_057_100, "vendor": "SMG (per P-12035 which names the McFetridge Center)",
            "contract": "P-12035 (same agreement as Soldier Field Complex, McFetridge Center and Stadium at Devon and Kedzie)",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/8150", "terms": "See Soldier Field row."},
        "626005 Parking Management": {"budget2026": 1_691_052, "budget2025": 1_491_844, "vendor": "Standard Parking Corporation",
            "contract": "P-14012 Management and Operation of Surface Parking Lots and Pay and Display Machines",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/8193", "terms": "Library status 'pending', Oct 8 2026 to Oct 7 2027, library value $0."},
        "626030 Cellular Telecommunication Infrastructure Management": {"budget2026": 537_438, "budget2025": 0, "vendor": "SPAAN Tech Inc",
            "contract": "P-25001 Cellular and Internet Broadband Telecommunication Infrastructure Management",
            "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/255568",
            "terms": "Active Dec 18 2025 to Dec 18 2030, library value $2,847,329. Board action 25-1149-0910 (Aug 8 2025). Revenue side: 422035 Cell Phone Tower Revenue $1,363,573."},
        "626035 Concessions Management": {"budget2026": 929_159, "budget2025": 910_940, "vendor": "UCG Associates (prior P-20011, closed Jul 1 2026) and Unison Consulting, Inc. (Board action 26-1305-0513, Apr 9 2026, spec P-25006)",
            "contract": "P-20011 Concession Program Management (UCG, value $2,481,433) then P-25006 (Unison Consulting)", "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/62874",
            "terms": "Park concessions program manager only. Soldier Field food service is separate: P-23013 Levy Premium FoodService LP, Jul 1 2024 to Jul 1 2029, value $1,000,000, $12M contractor capital investment (Board action 24-1058-0410)."},
        "626015 Ice Skating Management": {"budget2026": 992_697, "budget2025": 983_305, "vendor": "Westrec SMI OpCo, LLC",
            "contract": "P-23010 / P-25021 Management and Operation of Outdoor Ice Rinks", "bonfire": "https://chicagoparkdistrict.bonfirehub.com/publicContracts/196888",
            "terms": "P-23010 value $675,000 (closed Mar 30 2026). Board action 26-1277-0311 (Feb 9 2026) awarded P-25021 to Westrec SMI OpCo, LLC."},
        "623185 Grant Park Music Festival": {"budget2026": 2_400_000, "budget2025": 2_900_000, "vendor": "Grant Park Music Festival (nonprofit)", "contract": "grant, no procurement contract", "bonfire": None, "terms": "Printed on its own department page (p97), 8440."},
        "626025 Landscape Services": {"budget2026": 8_107_327, "budget2025": 7_721_264, "vendor": "Christy Webber & Company, Clauss Brothers, Moore Landscapes and others (multiple contracts)", "contract": "P-23005 ($2,294,924), P-22004 The 606 ($1,619,654), P-23014 Osaka Garden ($500,000), P-23015 ($200,000), P-24012 Floral Gardens ($4,000,000), P-25010 Planting ($6,000,000)", "bonfire": None, "terms": "The library values are contract ceilings across several years, not annual spend. Mapping to the 626025 line is an inference from titles, not stated by the District."},
    }
    contracts = {
        "source": bon["source"], "fetched": bon["fetched"], "library_total_contracts": bon["total_contracts_in_library"],
        "closed": bon["closed"], "non_closed": bon["nonclosed"],
        "caveat": "The library's 'Value' is the contract amount or ceiling over the whole term (0 when the District did not enter one), not annual payments. Payment-level (vendor paid per year) data is NOT published by the Park District.",
        "managed_assets_vs_budget_lines": managed,
        "pool_contracts": bon["pool_contracts"],
        "non_closed_contracts": rows,
        "closed_reference_contracts": bon["closed_reference_contracts"],
    }
    big = [r for r in rows if r["value"] and r["value"] >= 1_000_000 and r["status_code"] in ("1", "2")]
    contracts["non_closed_contracts_stated_value_ge_1M"] = len(big)
    contracts["non_closed_stated_value_total_ge_1M_sum"] = round(sum(r["value"] for r in big), 2)

    # ---------------- pension
    val = json.load(open(os.path.join(RAW, "pension_valuation_text.json")))
    acfr = json.load(open(os.path.join(RAW, "acfr25_text.json")))
    adc = re.search(r"ADC based on the Board.s funding policy is \$([\d,]+)", val["9"])
    uaal = re.search(r"\(UAAL\).*?is \$([\d,]+)", val["9"], re.S)
    hist = {}
    for m in re.finditer(r"^(20\d\d) \$?([\d,]+) ([\d.]+)% \$?([\d,]+) ([\d.]+)% ([\d.]+)%\s*$", val["29"], re.M):
        hist[m.group(1)] = {"adc": money(m.group(2)), "aec_actual": money(m.group(4)), "percent_contributed": float(m.group(6))}
    ay = re.search(r"^2025 \$?([\d,]+)", val["29"], re.M)
    pension = {
        "fund": "Park Employees' and Retirement Board Employees' Annuity and Benefit Fund of Chicago (PEABF)", "website": "https://www.chicagoparkpension.org/",
        "budget_lines_2026": {"625020 Pension Expense (employer, statutory)": 63_332_412, "625023 Supplemental Contribution to Pension Fund (one-time, TIF surplus)": 6_000_000, "total": 69_332_412,
                              "ordinance_appropriation_C_p252": 69_332_412},
        "budget_lines_2025": {"625020 Pension Expense": 59_679_376},
        "actuarial_valuation_12_31_2025": {
            "source": "https://www.chicagoparkpension.org/wp-content/uploads/2026/06/Park-Employees-Annuity-and-Benefit-Fund-of-Chicago_Actuarial-Valuation-Report-as-of-12.31.2025.pdf (Segal, May 29 2026)",
            "funded_ratio_actuarial": 0.332, "funded_ratio_fair_value": 0.334,
            "actuarially_determined_contribution_fy2026_board_policy": money(adc.group(1)) if adc else None,
            "unfunded_actuarial_accrued_liability": money(uaal.group(1)) if uaal else None,
            "statute_note": "Actual employer contributions are set by statute (P.A. 102-0263): employer normal cost plus a 32-year closed amortization of the 12/31/2025 UAAL. The Board's own ADC policy is higher than the statutory payment."},
        "employer_contribution_history_adc_vs_actual": hist,
        "acfr_2025": {"employer_contribution_2025": 59_679_376, "plan_membership_12_31_2025": {"retirees_and_beneficiaries_receiving": 2701, "inactive_entitled_not_receiving": 206, "active": 3251, "total": 6158},
                      "net_pension_liability_measured_12_31_2024_thousands": {"total_pension_liability": 1_307_429, "plan_fiduciary_net_position": 417_978, "net_pension_liability": 889_451},
                      "net_pension_liability_per_fund_report_12_31_2025": 901_300_000,
                      "employee_contribution_rate": "9% (11% for those hired on or after Jan 1 2022)", "discount_rate": 0.07,
                      "source": "https://files.chicagoparkdistrict.com/2026-07/Chicago Park District_25 ACFR_Final.pdf Note 10 (printed pp 74-79)"},
        "deepest_split": "Employer contribution splits into normal cost and UAAL amortization inside the valuation report, but the District budget carries one line. Benefit payments to 2,701 retirees (about $86.0M in 2024 per ACFR Note 10) are made by the Fund, not the District.",
    }
    check("Pension valuation parsed: ADC 88,904,199 and 2025 actual contribution 59,679,376 == budget 2025 line", pension["actuarial_valuation_12_31_2025"]["actuarially_determined_contribution_fy2026_board_policy"] == 88_904_199 and hist.get("2025", {}).get("aec_actual") == 59_679_376, history_years=len(hist))
    check("Pension plan membership sums to 6,158", 2701 + 206 + 3251 == 6158)

    # ---------------- ACFR
    acfr_out = {
        "source": "https://files.chicagoparkdistrict.com/2026-07/Chicago Park District_25 ACFR_Final.pdf (FY ended Dec 31 2025, dated July 28 2026; 140 PDF pages, printed page = PDF page - 7)",
        "other_years": "FY2024 ACFR: https://files.chicagoparkdistrict.com/2025-10/Chicago Park District_24 ACFR_Final.pdf ; all years 2007-2025 on https://www.chicagoparkdistrict.com/comptroller",
        "general_fund_budget_vs_actual_2025_thousands": {
            "page": "ACFR printed p87", "revenues": {"original_budget": 416_974, "actual": 395_140, "variance": -21_834},
            "expenditures": {"original_budget": 416_974, "final_budget_total": 416_974, "actual": 435_798, "variance": -18_824},
            "by_category_actual": {"Personnel services": 225_312, "Materials and supplies": 7_992, "Small tools and equipment": 648, "Contractual services": 184_981, "Program expense": 416, "Other expense": 13_758, "Capital outlay": 2_691},
            "by_category_budget": {"Personnel services": 220_647, "Materials and supplies": 9_243, "Small tools and equipment": 670, "Contractual services": 175_994, "Program expense": 624, "Other expense": 9_796, "Capital outlay": 0},
            "revenue_actual_selected": {"Soldier Field": 74_567, "Property taxes": 157_809, "Harbor fees": 20_817, "Golf course fees": 10_535, "Parking fees": 6_789, "Concessions": 3_722},
            "note": "General Operating Fund only (budgetary basis), about $436M of the $598.5M all-funds 2025 budget. The budget document's 2025 column is all operating funds, so the two are not directly comparable."},
        "go_debt_12_31_2025_thousands": {"page": "ACFR printed p118", "park_improvement_bonds": 660_185, "alternate_revenue_bonds": {"PPRT": 78_605, "Harbor": 116_170, "SRA": 24_305, "subtotal": 219_080}, "total_go_and_alternate": 879_265,
                                        "bonded_debt_limit_2_3pct_of_EAV": 2_357_512, "eav_2024": 102_500_523, "matches_budget_pdf_p73_total_principal": 879_265_000},
        "total_district_debt_incl_premiums_leases_thousands": 965_593,
    }
    check("ACFR GO debt total 879,265 (thousands) == budget PDF p73 debt schedule principal total 879,265,000", acfr_out["go_debt_12_31_2025_thousands"]["total_go_and_alternate"] * 1000 == tot["principal"] or True)
    # (the budget-PDF schedule principal is from parks_build; compare directly)
    main_beyond = main_data["beyond_operating_from_budget_pdf"]["general_obligation_debt_schedule"]["rows"]
    pr_tot = next(r for r in main_beyond if r["period"] == "Total")["principal"]
    checks[-1] = {"name": "ACFR GO debt total 879,265 (thousands) == budget PDF p73 schedule total principal 879,265,000",
                  "pass": pr_tot == 879_265_000 == acfr_out["go_debt_12_31_2025_thousands"]["total_go_and_alternate"] * 1000}

    capital = {
        "cip_2026_2030_category_level": main_beyond and main_data["beyond_operating_from_budget_pdf"]["capital_improvement_plan_2026_2030"],
        "ordinance_capital_appropriations_2026": [a for a in appropriations if a["kind"] == "capital"],
        "ordinance_capital_appropriations_2026_total": capital_total,
        "capital_projects_list": cap_summary,
        "older_cips_with_per-project_scope": {"2011-2024 Capital Projects by Park (85-page table, no $)": "https://files.chicagoparkdistrict.com/2025-04/2011-2024 Capital Projects by Park - Table Format.pdf",
                                              "2021-2025 CIP (11 pages, category-level)": "https://files.chicagoparkdistrict.com/2025-04/2021-2025 Capital Improvement Plan.pdf"},
        "operating_to_capital_transfers_2026": {"625065 Transfer to Capital Projects": 10_523_042, "TIF surplus capital (ordinance fn 1)": 10_000_000, "capital_transfer_from_operating_CIP_2026": 5_500_000},
        "gap": "No 2026-2030 per-project list with dollar amounts is published. Individual featured projects with stated amounts appear in the budget narrative (PDF pp 69-72, printed 63-66): Cragin Park fieldhouse $7.1M TIF + $500K HUD, Kells Park $17M TIF + $1.5M state, and others.",
    }
    debt = {
        "operating_budget_2026": {"interest_600005": 35_926_546, "principal_600015": 34_630_000, "total": 70_556_546, "page": "PDF p62-63"},
        "ordinance_appropriation_M_by_bond_series_2026": {"rows": body, "total": tot, "page": "PDF p253 (printed 247)"},
        "ordinance_vs_operating_note": "Principal ties exactly (34,630,000). Interest differs by $1,100,000 which the ordinance (p252 footnote 1) says sits in the General Fund Other Expense, not in the bond schedule.",
        "go_schedule_by_period_from_budget_pdf_p73": main_beyond,
        "ratings": {"Fitch": "AA", "Kroll": "AA", "S&P": "AA-"},
        "harbor_revenue_backed_debt_service_2026": 10_600_000,
        "alternate_revenue_portion_of_debt": 219_080_000,
        "bond_authorizations_board_actions": ["25-1159-1008 Sep 9 2025: not to exceed $120,000,000 GO Limited Tax Park Bonds of 2025", "24-1047-0313 Feb 2024: not to exceed $160,000,000 GO Limited Tax Park Bonds of 2024", "24-1040-0313 Feb 2024: not to exceed $11,000,000 GO Unlimited Tax Park Bonds (SRA alternate revenue)"],
    }
    positions = {
        "source": "Detail tables of the Appropriations PDF (right-hand 'Positions' table beside each account table), parsed into data/parks_2026.json under each unit's 611005 Salary & Wages",
        "rows_parsed": main_data["reconciliation"]["positions"]["stats"].get("position_rows"),
        "fte_2026_sum_of_tables": main_data["reconciliation"]["positions"]["fte2026_sum_of_tables"],
        "budgeted_fte_printed_p58": 3213.0, "full_time": 1796, "hourly": 853, "summer_seasonal": 564,
        "no_individual_names": "The budget lists job titles, headcounts, and pay by title and unit, never individual employees.",
    }
    out = {
        "meta": {"generated_by": "scripts/parks_beyond.py", "note": "All figures sourced; see each block's 'source'/'page'. Nothing estimated."},
        "reconciliation_checks": checks,
        "appropriation_ordinance_by_fund_2026": {"funds": appropriations, "museums_appropriation_F": museums, "page": "PDF pp 252-254 (printed 246-248)",
                                                 "capital_funds_total": capital_total, "operating_funds_total_A_to_I": oper_approps},
        "capital": capital, "debt": debt, "pension": pension, "acfr_fy2025": acfr_out, "managed_asset_contracts": contracts, "positions": positions,
    }
    main_data["beyond_operating"] = out
    main_data["meta"]["beyond_operating_note"] = "See beyond_operating (scripts/parks_beyond.py)."
    json.dump(main_data, open(MAIN, "w"), separators=(",", ":"))
    n = sum(1 for c in checks if c["pass"])
    print(f"checks passed: {n}/{len(checks)}")
    for c in checks:
        print(("PASS " if c["pass"] else "FAIL ") + c["name"])
    print("bond series:", len(body), "| museums:", len(museums), "| funds:", len(funds), "| capital funds total:", capital_total)
    print("contracts >= $1M non-closed:", contracts["non_closed_contracts_stated_value_ge_1M"], contracts["non_closed_stated_value_total_ge_1M_sum"])


if __name__ == "__main__":
    main()
