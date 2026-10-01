#!/usr/bin/env python3
"""Round 3, item 2d: scheduled wage adjustments (0003) and CPD overtime (0020), count x average by job title from payroll costing dawh-m56b (2025 actual).
Reads raw/leaves/payroll_2025_approp_dept_title.json (fetched by scripts/leaves_fetch.py). PROXY: 2025 actual pay on the same account, a different year than the 2026 budget.
Fire 0003: the City moved $104.7M of Finance General 0003 into Fire lines in Dec 2025 (research/city_personnel.md section 3), so Fire 0003 is shown with the 2025 titles under Finance General 0003 that are Fire titles.
Writes data/leaves_wages.json"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
p = json.load(open(f"{ROOT}/raw/leaves/payroll_2025_approp_dept_title.json"))
FIRE = re.compile(r"FIREFIGHTER|FIRE |PARAMEDIC|AMBULANCE|EMT|BATTALION|LIEUTENANT-EMT|CAPTAIN-EMT|MARINE", re.I)
def pieces(rows, top=8):
    rows = sorted(rows, key=lambda r: -float(r["amt"]))
    out = [{"name": r["title"].split(" - ", 1)[1], "count": int(r["n"]), "average": round(float(r["amt"]) / int(r["n"])), "amount": round(float(r["amt"])), "basis": "count_x_average"} for r in rows[:top]]
    rest = rows[top:]
    out.append({"name": f"{len(rest)} other job titles", "count": sum(int(r["n"]) for r in rest), "amount": round(sum(float(r["amt"]) for r in rest)), "basis": "count_x_average"})
    return out
fire = [r for r in p if r["appropriation"].startswith("A0003") and r["department"].startswith("D99") and FIRE.search(r["title"].split(" - ", 1)[1])]
op = [r for r in p if r["appropriation"].startswith("A0020") and r["department"].startswith("D57")]
leaves = [
 {"match_path_contains": ["Chicago Fire Department", "0003"], "amount": 97_974_157, "proposed_status": "split_proxy",
  "split_basis": f"PROXY. 2025 actual pay on account 0003 for {len(fire)} Fire job titles (under Finance General, payroll costing dawh-m56b) was ${sum(float(r['amt']) for r in fire)/1e6:.1f}M. It was back pay and lump sums after the 2025 Fire contract, not scheduled raises. 2026 amounts are not yet paid out by title.",
  "pieces": pieces(fire), "pieces_over_10m_after": [], "why_cant_go_deeper": "This is money set aside for firefighter raises and back pay under a new contract, and nobody can say yet which firefighters will get how much."},
 {"match_path_contains": ["Chicago Police Department", "0020", "Overtime"], "amount": 200_000_000, "proposed_status": "split_proxy",
  "split_basis": f"PROXY. 2025 actual Police overtime was ${sum(float(r['amt']) for r in op)/1e6:.1f}M over {len(op)} job titles (payroll costing dawh-m56b). Count x average, e.g. 7,370 police officers x $19,005. 2026 mid-year report: CPD budget $203.9M, $59.5M spent through period 5 (29.2%).",
  "pieces": pieces(op), "pieces_over_10m_after": [], "why_cant_go_deeper": "Officers earn overtime when extra work comes up, so the total depends on how many extra hours were worked, and the City reports totals by job, not by person."}]
json.dump({"meta": {"generated_by": "scripts/leaves_wages.py", "sources_fetched": [{"url": "https://data.cityofchicago.org/resource/dawh-m56b.json (aggregate by appropriation, department, title)", "http_status": "200 at round 2", "note": "raw/leaves/payroll_2025_approp_dept_title.json"},
   {"url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026Mid-YearBudgetReport.pdf", "http_status": 200, "note": "overtime by department table p.45"}]}, "leaves": leaves}, open(f"{ROOT}/data/leaves_wages.json", "w"), indent=1)
print(len(fire), sum(float(r['amt']) for r in fire)/1e6)
