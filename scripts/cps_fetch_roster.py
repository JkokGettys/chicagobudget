#!/usr/bin/env python3
"""Download CPS Employee Position Roster (public, quarterly) and aggregate by Dept ID x Job Title (no names kept).
Usage: python3 scripts/cps_fetch_roster.py [employeepositionroster_12312025.xls]
Outputs raw/cps/roster_12312025.xls and raw/cps/cps_roster_dept_job.csv"""
import csv, os, subprocess, sys, collections, xlrd
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps"); os.makedirs(D, exist_ok=True)
name = sys.argv[1] if len(sys.argv) > 1 else "employeepositionroster_12312025.xls"
X = os.path.join(D, "roster_" + name.split("_")[-1])
if not os.path.exists(X):
    subprocess.check_call(["curl", "-sL", "-A", "Mozilla/5.0", "-o", X, "https://www.cps.edu/globalassets/cps-pages/about-cps/finance/employee-position-files/" + name])
sh = xlrd.open_workbook(X).sheet_by_index(0)
h = sh.row_values(0); ix = {k: i for i, k in enumerate(h)}
agg = collections.defaultdict(lambda: [0, 0.0, 0.0, 0.0])
num = lambda v: v if isinstance(v, float) else 0.0
for i in range(1, sh.nrows):
    r = sh.row_values(i)
    k = (r[ix["Dept ID"]], r[ix["Department"]], r[ix["JobCode"]], r[ix["Job Title"]], r[ix["ClsIndc"]])
    a = agg[k]; a[0] += 1; a[1] += num(r[ix["FTE"]]); a[2] += num(r[ix["FTE Annual Salary"]]); a[3] += num(r[ix["Annual Benefit Cost"]])
with open(os.path.join(D, "cps_roster_dept_job.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["dept_id", "department", "job_code", "job_title", "class", "positions", "fte", "fte_annual_salary", "annual_benefit_cost"])
    for k, a in sorted(agg.items()): w.writerow(list(k) + a)
print(len(agg), "groups;", sum(a[0] for a in agg.values()), "positions;", sum(a[2] for a in agg.values()), "salary")
