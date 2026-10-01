#!/usr/bin/env python3
"""Fetch CPS capital budget (project level) from OBIEE subject area "CPS Capital Budget". Writes raw/cps/cps_2026_capital_projects.csv"""
import csv, os, sys
sys.path.insert(0, os.path.dirname(__file__))
from cps_obiee import logon, logical_sql
YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
OUT = os.path.join(os.path.dirname(__file__), "..", "raw", "cps"); os.makedirs(OUT, exist_ok=True)
s = logon()
cols = ["Unit", "Unit Name", "Project Number", "Project Name", "Project Budget Year", "Supplemental Flag", "Main Category", "Project Type", "Project Source", "Project Status", "Network Short Name", "Alderman"]
sql = 'SELECT %s,"Fact"."Budget" FROM "CPS Capital Budget" WHERE "Dim - Capital"."Budget Year"=%d' % (",".join('"Dim - Capital"."%s"' % c for c in cols), YEAR)
rows = logical_sql(s, sql, 5000)
p = os.path.join(OUT, "cps_%d_capital_projects.csv" % YEAR)
with open(p, "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols + ["budget"]); w.writerows(rows)
print(p, len(rows), sum(float(r[-1] or 0) for r in rows if r[4] == str(YEAR)), "(project budget year == %d)" % YEAR, sum(float(r[-1] or 0) for r in rows), "(all years)")
