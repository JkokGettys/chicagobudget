"""Map each of the 40 City departments (dataset 6694-f78c) to the value-context metrics we found.

Inputs (all produced by the other context_*.py scripts or the raw project files):
- raw/city_appropriations_2026.json      budget by department (LOCAL vs GRANTS)
- raw/city_positions_2026.json           headcount (Annual positions) by department
- data/context_resident_2026.json        population and households
- data/context_service_metrics_2025.json 311 volume, speed, potholes, inspections
- data/context_oversight_findings.json   OIG / COFA / Civic Federation / CPD findings (quotes verified)
- data/context_peers_2024.json           Census peer-city per-resident spending by function
- data/context_settlements_2019_2025.json
- raw/context/budget_overview_2026.pdf   each department's '2025 KEY RESULTS' (self-reported)
- raw/context/cofa_budget_rec_summary_fy26.pdf  COFA FTE counts and page references

Output: data/context_dept_map.json

For every department the output says what we HAVE, what is only PARTIAL, and what is MISSING, so nobody
mistakes "we found no metric" for "the department performs well".

Usage: python3 scripts/context_dept_map.py
"""
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from context_common import ROOT, RAW, load_json, norm, pdf_text, raw_path, write_json  # noqa: E402

BUDGET_OVERVIEW_URL = "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf"
COFA_REC_URL = "https://www.chicago.gov/content/dam/city/depts/COFA/ProposedBudget/Presentations_ProposedBudget/COFA_Budget%20Recommendation%20Summary_Final.pdf"

# Budget Overview heading -> dataset department name. Headings are matched after normalizing.
HEADING_TO_DEPT = {
    "OFFICE OF THE MAYOR": "Office of the Mayor",
    "OFFICE OF BUDGET AND MANAGEMENT": "Office of Budget and Management",
    "DEPARTMENT OF TECHNOLOGY AND INNOVATION": "Department of Technology and Innovation",
    "OFFICE OF THE CITY CLERK": "Office of City Clerk",
    "DEPARTMENT OF FINANCE": "Department of Finance",
    "CITY TREASURER'S OFFICE": "City Treasurer's Office",
    "DEPARTMENT OF ADMINISTRATIVE HEARINGS": "Department of Administrative Hearings",
    "DEPARTMENT OF LAW": "Department of Law",
    "DEPARTMENT OF HUMAN RESOURCES": "Department of Human Resources",
    "DEPARTMENT OF PROCUREMENT SERVICES": "Department of Procurement Services",
    "DEPARTMENT OF FLEET AND FACILITY MANAGEMENT": "Department of Fleet and Facility Management",
    "DEPARTMENT OF STREETS AND SANITATION": "Department of Streets and Sanitation",
    "CHICAGO DEPARTMENT OF TRANSPORTATION": "Chicago Department of Transportation",
    "CHICAGO DEPARTMENT OF AVIATION": "Chicago Department of Aviation",
    "DEPARTMENT OF WATER MANAGEMENT": "Department of Water Management",
    "CHICAGO POLICE BOARD": "Chicago Police Board",
    "CHICAGO POLICE DEPARTMENT": "Chicago Police Department",
    "OFFICE OF EMERGENCY MANAGEMENT AND COMMUNICATIONS": "Office of Emergency Management and Communications",
    "CHICAGO FIRE DEPARTMENT": "Chicago Fire Department",
    "CIVILIAN OFFICE OF POLICE ACCOUNTABILITY": "Civilian Office of Police Accountability",
    "COMMUNITY COMMISSION FOR PUBLIC SAFETY AND ACCOUNTABILITY": "Community Commission for Public Safety and Accountability",
    "CHICAGO DEPARTMENT OF PUBLIC HEALTH": "Chicago Department of Public Health",
    "COMMISSION ON HUMAN RELATIONS": "Chicago Commission on Human Relations",
    "MAYOR'S OFFICE FOR PEOPLE WITH DISABILITIES": "Mayor's Office for People with Disabilities",
    "DEPARTMENT OF FAMILY AND SUPPORT SERVICES": "Department of Family and Support Services",
    "CHICAGO PUBLIC LIBRARY": "Chicago Public Library",
    "DEPARTMENT OF HOUSING": "Department of Housing",
    "DEPARTMENT OF CULTURAL AFFAIRS AND SPECIAL EVENTS": "Department of Cultural Affairs and Special Events",
    "DEPARTMENT OF PLANNING AND DEVELOPMENT": "Department of Planning and Development",
    "OFFICE OF THE INSPECTOR GENERAL": "Office of Inspector General",
    "DEPARTMENT OF BUILDINGS": "Department of Buildings",
    "DEPARTMENT OF BUSINESS AFFAIRS AND CONSUMER PROTECTION": "Department of Business Affairs and Consumer Protection",
    "DEPARTMENT OF ENVIRONMENT": "Department of Environment",
    "CHICAGO ANIMAL CARE AND CONTROL": "Chicago Animal Care and Control",
    "LICENSE APPEAL COMMISSION": "License Appeal Commission",
    "BOARD OF ETHICS": "Board of Ethics",
    "BOARD OF ELECTION COMMISSIONERS": "Board of Election Commissioners",
    "OFFICE OF PUBLIC SAFETY ADMINISTRATION": "Office of Public Safety Administration",
}

# COFA heading (short) -> dataset department name
COFA_TO_DEPT = {
    "Office of the Mayor": "Office of the Mayor", "Office of Budget & Management": "Office of Budget and Management",
    "Department of Technology & Innovation": "Department of Technology and Innovation", "City Clerk": "Office of City Clerk",
    "Department of Finance": "Department of Finance", "Office of the City Treasurer": "City Treasurer's Office",
    "Department of Administrative Hearings": "Department of Administrative Hearings", "Department of Law": "Department of Law",
    "Department of Human Resources": "Department of Human Resources", "Department of Procurement Services": "Department of Procurement Services",
    "Department of Fleet & Facility Management": "Department of Fleet and Facility Management", "City Council": "City Council",
    "Board of Election Commissioners": "Board of Election Commissioners", "Department of Housing": "Department of Housing",
    "Department of Cultural Affairs & Special Events": "Department of Cultural Affairs and Special Events",
    "Department of Planning & Development": "Department of Planning and Development", "Department of Public Health": "Chicago Department of Public Health",
    "Commission on Human Relations": "Chicago Commission on Human Relations", "Mayor's Office for People with Disabilities": "Mayor's Office for People with Disabilities",
    "Department of Family & Support Services": "Department of Family and Support Services", "Chicago Public Library": "Chicago Public Library",
    "Office of Public Safety Administration": "Office of Public Safety Administration", "Police Board": "Chicago Police Board",
    "Chicago Police Department": "Chicago Police Department", "Office of Emergency Management & Communications": "Office of Emergency Management and Communications",
    "Chicago Fire Department": "Chicago Fire Department", "Civilian Office of Police Accountability": "Civilian Office of Police Accountability",
    "Community Commission on Public Safety & Accountability": "Community Commission for Public Safety and Accountability",
    "Office of the Inspector General": "Office of Inspector General", "Department of Buildings": "Department of Buildings",
    "Department of Business Affairs & Consumer Protection": "Department of Business Affairs and Consumer Protection",
    "Department of Environment": "Department of Environment", "Department of Animal Care & Control": "Chicago Animal Care and Control",
    "License Appeal Commission": "License Appeal Commission", "Board of Ethics": "Board of Ethics",
    "Department of Streets & Sanitation": "Department of Streets and Sanitation", "Department of Transportation": "Chicago Department of Transportation",
    "Department of Aviation": "Chicago Department of Aviation", "Department of Water Management": "Department of Water Management",
}

# Census peer-comparison function per department. Only where the Census definition is a fair match.
PEER_FUNCTION = {
    "Chicago Police Department": ("E62", "Police protection", "approximate"),
    "Chicago Fire Department": ("E24", "Fire protection", "approximate"),
    "Department of Streets and Sanitation": ("E81", "Garbage and solid waste", "approximate"),
    "Chicago Department of Transportation": ("E44", "Streets and highways", "approximate"),
    "Department of Water Management": ("E91", "Water utility", "approximate"),
    "Chicago Public Library": ("E52", "Libraries", "good"),
    "Chicago Department of Public Health": ("E32", "Public health", "weak: Chicago has a separate Cook County health system"),
    "Department of Housing": ("E50", "Housing and community development", "weak: NYC and Philadelphia run housing programs Chicago leaves to the CHA and county"),
    "Department of Buildings": ("E66", "Protective inspection and regulation", "approximate"),
}

# Which 311 owner_department label maps to each budget department
OWNER_FOR = {
    "Department of Streets and Sanitation": "Streets and Sanitation",
    "Chicago Department of Transportation": "CDOT - Department of Transportation",
    "Department of Water Management": "DWM - Department of Water Management",
    "Chicago Animal Care and Control": "Animal Care and Control",
    "Department of Buildings": "DOB - Buildings",
    "Department of Business Affairs and Consumer Protection": "BACP - Business Affairs and Consumer Protection",
    "Office of City Clerk": "City Clerk's Office",
    "Chicago Department of Public Health": "Health",
    "Chicago Fire Department": "Fire",
    "Department of Housing": "Department of Housing",
    "Department of Finance": "Finance",
    "Chicago Department of Aviation": "Aviation",
}

# Hand-written notes on what a resident can check and what is missing. No numbers here, just guidance.
GUIDE = {
    "Office of the Mayor": ("none", "No public outcome measure. Judge by staffing and by what the Mayor's office budget line pays for."),
    "Office of Budget and Management": ("none", "No outcome measure. COFA and the Civic Federation are the outside check on its budget forecasts."),
    "Department of Technology and Innovation": ("none", "311 site availability datasets exist but are old (2011). No current outcome measure found."),
    "Office of City Clerk": ("partial", "City sticker violation 311 requests are available (4,510 in 2025). No outcome measure for the clerk's other work."),
    "Department of Finance": ("partial", "OIG audits on debt ($8.1B owed to the City) and vendor payment timeliness. Revenue collected is a result measure we did not find."),
    "City Treasurer's Office": ("none", "No outcome measure found in this pass."),
    "Department of Administrative Hearings": ("none", "No outcome measure found in this pass. The Budget Overview describes it as adjudicating ordinance violations."),
    "Department of Law": ("partial", "Cost side only: police settlement and outside-counsel totals from the Law Department's CPD litigation reports. No measure of how well the department does its work. An all-City payout total is not published in one place."),
    "Department of Human Resources": ("partial", "OIG found HR cannot show its Employee Assistance Program works. No hiring-speed measure found."),
    "Department of Procurement Services": ("partial", "EY (via Civic Federation) says 49% of City spending is not managed by procurement. A City auctions dataset exists (s9wg-6is6)."),
    "Department of Fleet and Facility Management": ("partial", "EY (via Civic Federation): average vehicle driven 7,000 miles a year and one vehicle per 17 employees. Not audited."),
    "City Council": ("none", "No outcome measure. COFA, a Council office, was itself audited by OIG."),
    "Board of Election Commissioners": ("none", "No outcome measure found in this pass. OIG audited it in 2019 and published a follow-up in 2020."),
    "Department of Housing": ("partial", "Affordable Rental Housing Developments dataset (s6ha-ppgi) exists but was not analyzed in this pass."),
    "Department of Cultural Affairs and Special Events": ("none", "No outcome measure found. Event permit data not analyzed."),
    "Department of Planning and Development": ("partial", "TIF datasets exist on the data portal (for example qm7s-3ctt, the TIF annual report) but were not analyzed here. No outcome measure found."),
    "Chicago Department of Public Health": ("partial", "311 volume only (3,532 requests). OIG mental health audit. Public health indicator datasets exist (iqnk-2tcu) but not analyzed here."),
    "Chicago Commission on Human Relations": ("none", "No outcome measure found in this pass."),
    "Mayor's Office for People with Disabilities": ("none", "No outcome measure found in this pass."),
    "Department of Family and Support Services": ("partial", "One OIG outcome (94.1% of encampment residents who attended a housing event entered stable housing). Youth services utilization dataset exists (xczi-kmtf), not analyzed."),
    "Chicago Public Library": ("partial", "Library visitor and circulation datasets exist by branch (2014-2019 only). Peer comparison is a good match."),
    "Office of Public Safety Administration": ("none", "No outcome measure found in this pass."),
    "Chicago Police Board": ("none", "No outcome measure found in this pass."),
    "Chicago Police Department": ("have", "Homicide clearance (71% self-reported, with the Inspector General's warning), crime totals, settlements, overtime, peer per-resident. Missing: response times (OIG says data gaps), complaint outcomes."),
    "Office of Emergency Management and Communications": ("partial", "OIG audit of 311 and 911 response-time data follow-up. No 911 answer-time measure found."),
    "Chicago Fire Department": ("partial", "CFD does not report response times publicly (OIG, COFA). Overtime, staffing and inspection findings exist. Total emergency events (365,573 in 2025) from COFA."),
    "Civilian Office of Police Accountability": ("partial", "OIG review of its backlog initiative. COPA Cases datasets exist (mft5-nfa8), not analyzed."),
    "Community Commission for Public Safety and Accountability": ("none", "No outcome measure found in this pass."),
    "Office of Inspector General": ("partial", "OIG publishes audits and dashboards. A dollars-saved total was not found in the reports we read. Budget Overview lists its results."),
    "Department of Buildings": ("have", "311 building violation requests and speed, permits issued per year, OIG inspection audit."),
    "Department of Business Affairs and Consumer Protection": ("partial", "311 volume and speed. Business license performance dataset exists (emvs-38e6), not analyzed."),
    "Department of Environment": ("none", "No outcome measure found in this pass."),
    "Chicago Animal Care and Control": ("partial", "311 request volume and speed. For stray animal complaints, 1,870 of 11,694 are marked Completed and 9,800 are marked Canceled (2025). We do not know why so many are canceled."),
    "License Appeal Commission": ("none", "No outcome measure found in this pass."),
    "Board of Ethics": ("none", "Old performance datasets exist (2012). No current outcome measure found."),
    "Department of Streets and Sanitation": ("have", "311 volume and speed for graffiti, rats, carts, abandoned cars. Two OIG audits (rats, auto pounds). Peer garbage spending per resident."),
    "Chicago Department of Transportation": ("have", "Potholes patched per year and days to patch, 311 street light, signal and pothole speed, peer streets spending."),
    "Chicago Department of Aviation": ("none", "311 volume is mostly information calls. No outcome measure found. Airport costs are paid by airline and passenger fees."),
    "Department of Water Management": ("partial", "OIG water billing audit. 311 water complaints and speed. Peer water and sewer per resident."),
    "Finance General": ("partial", "Not a service department. See research/finance_general.md. Pension and debt costs have no service outcome. Civic Federation and COFA comment on its savings options."),
}


def parse_budget_overview():
    """Find each department's '2025 KEY RESULTS' block in the Budget Overview text.

    The PDF text has quirks: some pages put chart labels before the heading (Fleet and Facility, OPSA),
    and words are sometimes split by a stray line break ('RESUL\\nTS', 'INITIA\\nTIVES'). So we locate the
    department by finding its heading right before the 'KEY FUNCTIONS' line, using the known heading list.
    """
    t = pdf_text(raw_path("budget_overview_2026.pdf"))
    pages = t.split("=====PAGE=====")
    heads_longest_first = sorted(HEADING_TO_DEPT, key=len, reverse=True)
    out = {}
    for i, p in enumerate(pages):
        flat = re.sub(r"\s+", " ", p).replace("\u2019", "'").replace("FAMIL Y", "FAMILY")
        if "KEY FUNCTIONS" not in flat:
            continue
        before = flat[:flat.index("KEY FUNCTIONS")].upper()
        dept = None
        best = -1
        for h in heads_longest_first:
            pos = before.rfind(h)
            if pos > best:
                best, dept = pos, HEADING_TO_DEPT[h]
        if dept is None or best < 0 or dept in out:
            continue
        # The PDF splits marker words in varied places ('RESUL TS', 'RESULT S', 'INITIA TIVES'), so allow
        # an optional space between any two letters of the markers.
        def loose(word):
            return r"\s?".join(re.escape(c) for c in word)
        m = re.search(r"2025 " + loose("KEY") + r" " + loose("RESULTS") + r"(.*?)2026 " + loose("INITIATIVES"),
                      flat, flags=re.S)
        res = None
        if m:
            res = norm(m.group(1))
        pn = re.search(r"PROGRAM AND BUDGET SUMMARIES BY DEPARTMENT\s+(?:[A-Z &]+ )?(\d+)", flat)
        out[dept] = {"printed_page": int(pn.group(1)) if pn else None, "pdf_page_index": i, "key_results_text": res}
    return out


def parse_cofa():
    t = pdf_text(raw_path("cofa_budget_rec_summary_fy26.pdf"))
    pages = t.split("=====PAGE=====")
    out = {}
    for i, p in enumerate(pages):
        m = re.search(r"FTEs Budgeted\s+([0-9,]+)", p)
        h = re.match(r"\s*(\d{3}) [\u2013-] (.+?) Council Office of Financial Analysis (\d+)", re.sub(r"\s+", " ", p))
        if m and h:
            name = COFA_TO_DEPT.get(h.group(2).strip())
            if name:
                out[name] = {"cofa_code": h.group(1), "ftes_budgeted": int(m.group(1).replace(",", "")),
                             "cofa_printed_page": int(h.group(3))}
    return out


def main():
    approps = json.load(open(os.path.join(ROOT, "raw", "city_appropriations_2026.json")))
    positions = json.load(open(os.path.join(ROOT, "raw", "city_positions_2026.json")))
    res = load_json("context_resident_2026.json")
    svc = load_json("context_service_metrics_2025.json")
    over = load_json("context_oversight_findings.json")
    peers = load_json("context_peers_2024.json")
    sett = load_json("context_settlements_2019_2025.json")
    pop = res["population"]["chicago_population"]

    dept_num, local, grants = {}, defaultdict(float), defaultdict(float)
    for a in approps:
        d = a["department_description"]
        dept_num[d] = a["department_number"]
        v = float(a["_ordinance_amount_"])
        (local if a["fund_type"] == "LOCAL" else grants)[d] += v
    depts = sorted(dept_num, key=lambda d: int(dept_num[d]))
    assert len(depts) == 40, len(depts)

    pos_annual = defaultdict(float)
    pos_other_rows = defaultdict(int)
    for r in positions:
        if r["budgeted_unit"] == "Annual":
            pos_annual[r["department_description"]] += float(r["total_budgeted_unit"])
        else:
            pos_other_rows[r["department_description"]] += 1

    bo = parse_budget_overview()
    cofa = parse_cofa()

    svc_dept = {r["owner_department"]: r for r in svc["requests_by_owner_department"]}
    within = defaultdict(list)
    for r in svc["completed_within_7_days_focus_types"]:
        within[r["owner_department"]].append(r)
    top_types = defaultdict(list)
    for r in svc["top_request_types"]:
        top_types[r["owner_department"]].append(r)

    findings_by = defaultdict(list)
    for f in over["findings"]:
        for d in f["departments"]:
            findings_by[d].append(f["id"])
    unknown = [d for d in findings_by if d not in dept_num]
    assert not unknown, "finding references unknown department: %s" % unknown

    out_depts = []
    for d in depts:
        total = local[d] + grants[d]
        entry = {
            "department_number": dept_num[d],
            "department": d,
            "budget_2026": {"total": total, "local_funds": local[d], "grants": grants[d],
                            "per_resident_total": round(total / pop, 2),
                            "per_resident_local": round(local[d] / pop, 2),
                            "per_household_total": round(total / res["population"]["households"], 2)},
            "headcount": {
                "annual_positions_budgeted_positions_dataset": pos_annual.get(d, 0),
                "hourly_or_monthly_position_rows_not_counted": pos_other_rows.get(d, 0),
                "cofa_ftes_budgeted": cofa.get(d, {}).get("ftes_budgeted"),
                "cofa_printed_page": cofa.get(d, {}).get("cofa_printed_page"),
                "note": "The positions dataset counts 'Annual' positions only. COFA's FTE figure (from the City's Budget Recommendations) is the better headcount where it exists.",
            },
        }
        # Budget overview self-reported results
        if d in bo:
            entry["self_reported_results_budget_overview"] = {
                "printed_page": bo[d]["printed_page"], "pdf_url": BUDGET_OVERVIEW_URL,
                "text_as_extracted": bo[d]["key_results_text"],
                "caveat": "Written by the department's own budget office. PDF text extraction leaves some odd spacing. Not audited.",
            }
        # 311
        owner = OWNER_FOR.get(d)
        if owner and owner in svc_dept:
            s = svc_dept[owner]
            entry["service_311_2025"] = {
                "owner_department_label": owner, "requests": s["requests"], "avg_days_to_close": s["avg_days_to_close"],
                "requests_per_1000_residents": round(s["requests"] / pop * 1000, 1),
                "requests_per_budget_dollar_note": "Not computed. Requests are a tiny part of what a department does.",
                "focus_types_completed_speed": [
                    {k: r[k] for k in ("sr_type", "completed_requests", "share_within_5_days", "share_within_7_days", "avg_days_to_close")}
                    for r in within.get(owner, [])],
                "top_request_types": [{k: r[k] for k in ("sr_type", "requests", "completed", "open", "canceled", "share_completed")}
                                      for r in top_types.get(owner, [])[:8]],
                "caveat": "Average days to close of 0.0 means the request is closed on creation (info calls). Not a speed measure.",
            }
        if d == "Chicago Department of Transportation":
            entry["potholes"] = {
                "patched_by_year": svc["potholes_patched_by_year"],
                "avg_days_request_to_patch_2025": svc["potholes_avg_days_request_to_patch_2025"],
                "source": "https://data.cityofchicago.org/d/wqdh-9gek",
            }
        if d == "Department of Buildings":
            entry["permits_issued_by_year"] = svc["building_permits_issued_by_year"]
        if d == "Department of Public Health":
            pass
        if d == "Chicago Department of Public Health":
            entry["food_inspections_by_year"] = svc["food_inspections_by_year"]
            entry["food_inspections_note"] = "Food Inspections dataset (4ijn-s7e5) is run by CDPH Food Protection. Counts are inspections, not outcomes."
        # Peer
        if d in PEER_FUNCTION:
            code, label, quality = PEER_FUNCTION[d]
            c = peers["chicago_vs_peers"].get(code)
            if c:
                entry["peer_comparison_census_2024"] = {
                    "census_item": code, "function": label, "match_quality": quality,
                    "chicago_per_resident": c["chicago_per_resident"], "peer_average_per_resident": c["peer_average_per_resident"],
                    "chicago_vs_peer_average_pct": c["chicago_vs_peer_average_pct"], "rank_of_5_highest_first": c["rank_among_5_highest_first"],
                    "peer_cities": ["New York City", "Los Angeles", "Houston", "Philadelphia"],
                    "source": peers["source_url"], "caveats": "See comparability_limits in data/context_peers_2024.json. Census 2024, not FY2026. City government only.",
                }
        # Settlements
        if d == "Chicago Police Department":
            y25 = sett["by_year"]["2025"]
            entry["settlements"] = {
                "payout_2025_excluding_watts": y25["total_payout"], "payout_2025_including_watts": y25["total_payout_including_watts"],
                "outside_counsel_2025": y25["outside_counsel_fees"],
                "budget_2026_for_judgments_line": sett["budget_2026_money_set_aside_for_judgments_by_department"].get(d),
                "per_resident_2025_excluding_watts": sett["per_resident_2025_total_payout_excluding_watts"],
                "source": "data/context_settlements_2019_2025.json",
            }
        if d == "Chicago Fire Department":
            entry["settlements"] = {"budget_2026_for_judgments_line": sett["budget_2026_money_set_aside_for_judgments_by_department"].get(d),
                                    "note": "Fire's judgments line is $12M in the 2026 appropriations. We found no public fire-specific payout total."}
        if d == "Department of Law":
            entry["settlements"] = {"note": "The Law Department files the annual CPD litigation report. See police entry and data/context_settlements_2019_2025.json.",
                                    "department_of_law_total_2026": sett["budget_2026_department_of_law_total"]}
        if d == "Finance General":
            entry["settlements"] = {"budget_2026_for_judgments_line": sett["budget_2026_money_set_aside_for_judgments_by_department"].get(d),
                                    "note": "Finance General holds the citywide 'tort and non-tort judgments' line ($48.0M by our sum of the appropriations)."}
        # Findings
        entry["oversight_finding_ids"] = findings_by.get(d, [])
        status, guide = GUIDE[d]
        entry["value_metric_coverage"] = status
        entry["what_a_resident_can_check"] = guide
        entry["missing"] = None
        out_depts.append(entry)

    # Coverage summary
    cov = defaultdict(list)
    for e in out_depts:
        cov[e["value_metric_coverage"]].append(e["department"])
    summary = {k: {"count": len(v), "departments": v} for k, v in cov.items()}
    n_with_findings = sum(1 for e in out_depts if e["oversight_finding_ids"])
    n_bo = sum(1 for e in out_depts if "self_reported_results_budget_overview" in e)

    out = {
        "generated_by": "scripts/context_dept_map.py",
        "dataset": "https://data.cityofchicago.org/resource/6694-f78c.json",
        "population_used": pop,
        "coverage_meaning": {
            "have": "Several independent measures (activity data, outside reviews, comparisons).",
            "partial": "Some activity data or an outside review, but no direct measure of results.",
            "none": "Nothing found in this pass except the department's own description. This does NOT mean the department performs well or badly.",
        },
        "coverage_summary": summary,
        "departments_with_oversight_findings": n_with_findings,
        "departments_with_budget_overview_key_results": n_bo,
        "departments_missing_budget_overview_key_results": [e["department"] for e in out_depts
                                                              if "self_reported_results_budget_overview" not in e],
        "departments": out_depts,
    }
    write_json("context_dept_map.json", out)
    print({k: v["count"] for k, v in summary.items()}, "with findings", n_with_findings, "with BO key results", n_bo)
    print("missing key results:", out["departments_missing_budget_overview_key_results"])


if __name__ == "__main__":
    main()
