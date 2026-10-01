#!/usr/bin/env python3
"""Round 3, item 2b: City health care lines by plan, covered lives and bargaining unit.
Sources (all fetched/verified, see meta): EY 'Financial and Strategic Reform Options' p.46 (published on chicago.gov, md5 7e1255c5...),
City ACFR 2025 note 12 (PPO self-insured, HMO partially insured), Payments s4vu-giwb 2025 (raw/city_payments_2025.csv) by vendor and check.
No public document gives claims by plan or covered lives by plan. The split below is COUNT x AVERAGE where the count comes from EY enrollment shares
by bargaining unit and the average is the line divided by enrolled employees (equal per enrollee, a PROXY, not a rate sheet).
Output: data/leaves_health.json"""
import csv, json, os
from collections import defaultdict
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EY = {  # EY p.46 table: active workforce, % PPO, % HMO, % waive
 "Fire": (4715, .85, .09, .07), "Police": (9970, .83, .12, .06), "Other union": (13834, .72, .15, .13), "Non-union": (3492, .71, .08, .21)}
rows = list(csv.DictReader(open(f"{ROOT}/raw/city_payments_2025.csv")))
vend = defaultdict(lambda: [0.0, 0, 0.0]); vo = defaultdict(float)
for r in rows:
    n = r["vendor_name"].strip()
    if n in ("BLUE CROSS & BLUE SHIELD", "CAREMARK INC", "BLUE CROSS BLUE SHIELD OF ILL", "DAVIS VISION INC", "METLIFE ASSIGNMENT COMPANY, INC.", "AETNA", "CIGNA HEALTHCARE", "UNITED HEALTHCARE"):
        v = vend[n]; a = float(r["amount"]); v[0] += a; v[1] += 1; v[2] = max(v[2], a)
leaves = []
def line(amount, plan_idx, label, path_contains):
    enr = {u: round(w[0] * w[plan_idx]) for u, w in EY.items()}
    tot = sum(enr.values()); avg = amount / tot
    pieces = [{"name": f"{u}: {n:,} enrolled employees x ${avg:,.0f}", "count": n, "average": round(avg), "amount": round(n * avg), "basis": "count_x_average", "source": "EY report p.46 enrollment shares x active workforce; average = line / enrolled (proxy, equal per enrollee)"} for u, n in enr.items()]
    return {"match_path_contains": path_contains, "amount": amount, "proposed_status": "split_proxy",
            "split_basis": f"{label}: enrolled employees by bargaining unit (EY p.46, rounded percentages) x equal average per enrollee. PROXY. Counts cover employees only, not dependents (39% family coverage means covered lives are higher). The line is citywide across funds.",
            "pieces": pieces, "pieces_over_10m_after": [], "enrolled_total": tot, "average_per_enrollee": round(avg)}
l1 = line(408_653_865, 1, "PPO and other medical (self-insured plan)", ["0042", "Hospital"])
l1["by_vendor_2025_payments"] = {k: {"paid": round(v[0]), "checks": v[1], "largest_check": round(v[2])} for k, v in vend.items() if v[0] > 0}
l1["why_cant_go_deeper"] = "The City pays hospital and doctor bills for thousands of workers as the bills come in, and it does not publish who each worker is or what each claim cost."
l1["note"] = "2025 payments: Blue Cross $610.0M in 68 checks (14 checks of $10M or more, largest $43.6M) and Caremark (pharmacy) $129.6M in 53 checks. Dental, vision and life premium vendors (Delta Dental, Davis Vision, MetLife) are small or not in this line. These payments are all funds, 2025, so they do not tie to the $408.7M Corporate Fund line."
l2 = line(85_169_477, 2, "HMO premiums (partially insured plan)", ["0029", "Health Maintenance"])  # ordinance 6694-f78c, Corporate Fund Finance General
l2["why_cant_go_deeper"] = "The City pays one monthly price per worker to the health plan, and the price list is not published."
leaves += [l1, l2]
meta = {"generated_by": "scripts/leaves_health.py",
        "sources_fetched": [{"url": "raw/leaves/ey_reform_published.pdf (https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/Financial and Strategic Reform Options - City of Chicago.pdf)", "http_status": "200 (round 2)", "note": "p.46 demographics and enrollment by bargaining unit; p.43 to 45 savings ideas, no claims by plan"},
                           {"url": "https://www.chicago.gov/city/en/depts/dhr/provdrs/benefits.html and 3 variants", "http_status": "404", "note": "no public DHR rate sheet found at these URLs (probed 2026-10-01)"},
                           {"url": "raw/pensions_debt/acfr2025.txt note 12 p.104", "http_status": "local", "note": "PPO self-insured, HMO partially insured"}],
        "not_found": "A published rate sheet with enrolled counts per plan, dental/vision/prescription spend by plan, and covered lives by unit. EY p.43 says the savings columns are redacted."}
json.dump({"meta": meta, "leaves": leaves}, open(f"{ROOT}/data/leaves_health.json", "w"), indent=1)
print(l1["enrolled_total"], l1["average_per_enrollee"], l2["enrolled_total"], l2["average_per_enrollee"])
