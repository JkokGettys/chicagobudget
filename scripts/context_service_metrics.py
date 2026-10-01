"""Service performance metrics from Chicago open data (calendar year 2025 by default).

Datasets (data.cityofchicago.org):
- 311 Service Requests            v6vf-nfxy  (requests, completion time by type and owner department)
- Potholes Patched                wqdh-9gek  (blocks patched, potholes filled, request-to-completion days)
- Food Inspections                4ijn-s7e5  (inspections per year)
- Building Permits                ydr8-5enu  (permits issued per year)

Honest limits (also written into the output):
- 'Days to close' is closed_date minus created_date on 311. It is the City's own clock, and some request
  types close the same day by design (info calls) so those are excluded from the by-type list.
- Not every request is for a service (Aviation, 311 City Services, Finance are excluded from the by-type list).
- Status 'Completed' is the City's label. We do not audit whether the work was done well.

Usage: python3 scripts/context_service_metrics.py -> data/context_service_metrics_2025.json
"""
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from context_common import socrata, write_json  # noqa: E402

YEAR = 2025
WHERE_YEAR = ("created_date between '%d-01-01T00:00:00' and '%d-12-31T23:59:59' and duplicate=false" % (YEAR, YEAR))

# Map the 311 'owner_department' labels to the budget department names in dataset 6694-f78c.
OWNER_TO_BUDGET = {
    "Streets and Sanitation": "Department of Streets and Sanitation",
    "CDOT - Department of Transportation": "Chicago Department of Transportation",
    "DWM - Department of Water Management": "Department of Water Management",
    "Animal Care and Control": "Chicago Animal Care and Control",
    "DOB - Buildings": "Department of Buildings",
    "BACP - Business Affairs and Consumer Protection": "Department of Business Affairs and Consumer Protection",
    "City Clerk's Office": "Office of City Clerk",
    "Health": "Chicago Department of Public Health",
    "Fire": "Chicago Fire Department",
    "Department of Housing": "Department of Housing",
    "Finance": "Department of Finance",
    "Aviation": "Chicago Department of Aviation",
    "311 City Services": None,
    "Outside Agencies": None,
}

FOCUS_TYPES = [
    "Pothole in Street Complaint", "Alley Pothole Complaint", "Rodent Baiting/Rat Complaint",
    "Graffiti Removal Request", "Street Light Out Complaint", "Traffic Signal Out Complaint",
    "Garbage Cart Maintenance", "Abandoned Vehicle Complaint", "Missed Garbage Pick-Up Complaint",
    "Fly Dumping Complaint", "Tree Emergency", "Blue Recycling Cart", "Water in Basement Complaint",
    "Stray Animal Complaint", "Building Violation",
]


def main():
    # 1) Volume and average days to close, by owner department
    dept = socrata("v6vf-nfxy", {
        "$select": "owner_department,count(*) as n,avg(date_diff_d(closed_date,created_date)) as avg_days",
        "$where": WHERE_YEAR, "$group": "owner_department", "$order": "n DESC",
    }, cache="sr_%d_by_dept.json" % YEAR)

    # 2) By type, with status (excluding the 3 owner depts that are not field services)
    bytype = socrata("v6vf-nfxy", {
        "$select": "owner_department,sr_type,status,count(*) as n,avg(date_diff_d(closed_date,created_date)) as avg_days",
        "$where": WHERE_YEAR + " and owner_department not in ('311 City Services','Aviation','Finance')",
        "$group": "owner_department,sr_type,status", "$order": "n DESC", "$limit": 2000,
    }, cache="sr_%d_by_type.json" % YEAR)

    # 3) Share completed within 7 days, for the focus types
    types_sql = ",".join("'%s'" % t.replace("'", "''") for t in FOCUS_TYPES)
    within = socrata("v6vf-nfxy", {
        "$select": "owner_department,sr_type,count(*) as n,"
                   "sum(case(date_diff_d(closed_date,created_date)<=5,1,true,0)) as within5,"
                   "sum(case(date_diff_d(closed_date,created_date)<=7,1,true,0)) as within7,"
                   "avg(date_diff_d(closed_date,created_date)) as avg_days",
        "$where": WHERE_YEAR + " and status='Completed' and sr_type in (%s)" % types_sql,
        "$group": "owner_department,sr_type", "$order": "n DESC",
    }, cache="sr_%d_within7.json" % YEAR)

    types_out = defaultdict(lambda: {"requests": 0, "completed": 0, "open": 0, "canceled": 0})
    for r in bytype:
        k = (r["owner_department"], r["sr_type"])
        n = int(r["n"])
        types_out[k]["requests"] += n
        st = r["status"].lower()
        if st in ("completed", "open", "canceled"):
            types_out[k][st] += n
    top_types = sorted(types_out.items(), key=lambda x: -x[1]["requests"])[:40]

    within_rows = []
    for r in within:
        n = int(r["n"])
        within_rows.append({
            "owner_department": r["owner_department"], "sr_type": r["sr_type"],
            "completed_requests": n, "completed_within_5_days": int(r["within5"]),
            "share_within_5_days": round(int(r["within5"]) / n, 4),
            "completed_within_7_days": int(r["within7"]),
            "share_within_7_days": round(int(r["within7"]) / n, 4),
            "avg_days_to_close": round(float(r["avg_days"]), 1),
        })

    # 4) Potholes patched per year (blocks and potholes filled)
    potholes = socrata("wqdh-9gek", {
        "$select": "date_extract_y(completion_date) as yr,count(*) as blocks,sum(number_of_potholes_filled_on_block) as filled",
        "$where": "completion_date between '2019-01-01T00:00:00' and '2026-12-31T23:59:59'",
        "$group": "yr", "$order": "yr",
    }, cache="potholes_by_year.json")
    pot_days = socrata("wqdh-9gek", {
        "$select": "avg(date_diff_d(completion_date,request_date)) as avg_days,count(*) as n",
        "$where": "completion_date between '%d-01-01T00:00:00' and '%d-12-31T23:59:59'" % (YEAR, YEAR),
    }, cache="potholes_days_%d.json" % YEAR)

    # 5) Inspections and permits volume
    food = socrata("4ijn-s7e5", {
        "$select": "date_extract_y(inspection_date) as yr,count(*) as n",
        "$where": "inspection_date>='2019-01-01T00:00:00'", "$group": "yr", "$order": "yr",
    }, cache="food_inspections_by_year.json")
    permits = socrata("ydr8-5enu", {
        "$select": "date_extract_y(issue_date) as yr,count(*) as n",
        "$where": "issue_date>='2019-01-01T00:00:00'", "$group": "yr", "$order": "yr",
    }, cache="permits_by_year.json")

    out = {
        "year": YEAR,
        "datasets": {
            "311 Service Requests": "https://data.cityofchicago.org/d/v6vf-nfxy",
            "Potholes Patched": "https://data.cityofchicago.org/d/wqdh-9gek",
            "Food Inspections": "https://data.cityofchicago.org/d/4ijn-s7e5",
            "Building Permits": "https://data.cityofchicago.org/d/ydr8-5enu",
        },
        "limits": [
            "Days to close is closed_date minus created_date, the City's own clock. Same-day closes (for example info calls) are common for some types.",
            "Status 'Completed' is the City's label. This does not measure quality.",
            "311 counts are service requests (duplicates removed), not all work a department does.",
            "Aviation, 311 City Services and Finance owner departments are excluded from the by-type table because their requests are not field services (Aviation: aircraft noise complaints, Finance: parking ticket reviews, 311 City Services: information calls).",
            "Data pulled on the date in the file's generated_at. 311 data keeps updating, so numbers move a little between pulls.",
        ],
        "owner_department_to_budget_department": OWNER_TO_BUDGET,
        "requests_by_owner_department": [
            {"owner_department": r["owner_department"], "budget_department": OWNER_TO_BUDGET.get(r["owner_department"]),
             "requests": int(r["n"]), "avg_days_to_close": round(float(r["avg_days"]), 1)}
            for r in dept
        ],
        "top_request_types": [
            {"owner_department": k[0], "sr_type": k[1], **v,
             "share_completed": round(v["completed"] / v["requests"], 4)}
            for k, v in top_types
        ],
        "completed_within_7_days_focus_types": sorted(within_rows, key=lambda x: -x["completed_requests"]),
        "potholes_patched_by_year": [{"year": int(r["yr"]), "blocks_patched": int(r["blocks"]),
                                       "potholes_filled": int(r["filled"])} for r in potholes],
        "potholes_avg_days_request_to_patch_%d" % YEAR: round(float(pot_days[0]["avg_days"]), 1),
        "potholes_rows_with_completion_%d" % YEAR: int(pot_days[0]["n"]),
        "food_inspections_by_year": [{"year": int(r["yr"]), "inspections": int(r["n"])} for r in food],
        "building_permits_issued_by_year": [{"year": int(r["yr"]), "permits": int(r["n"])} for r in permits],
    }
    import datetime
    today = datetime.date.today()

    def flag(rows, key):
        for r in rows:
            r["partial_year"] = (r["year"] == today.year)
        return rows

    out["potholes_patched_by_year"] = flag(out["potholes_patched_by_year"], "year")
    out["food_inspections_by_year"] = flag(out["food_inspections_by_year"], "year")
    out["building_permits_issued_by_year"] = flag(out["building_permits_issued_by_year"], "year")
    out["limits"].append("Rows marked partial_year=true cover only part of the year. Do not compare them with full years.")
    out["limits"].append("avg_days_to_close of 0.0 for '311 City Services', 'Aviation' and 'Finance' means the requests are closed when created. Checked: Aviation's 364,926 requests in 2025 are all 'Aircraft Noise Complaint', and Finance's 20,377 are all 'Finance Parking Code Enforcement Review' (parking ticket reviews). They are not a measure of fast service.")
    out["generated_at"] = today.isoformat()
    write_json("context_service_metrics_%d.json" % YEAR, out)
    print("owner depts:", len(out["requests_by_owner_department"]), "types:", len(out["top_request_types"]))


if __name__ == "__main__":
    main()
