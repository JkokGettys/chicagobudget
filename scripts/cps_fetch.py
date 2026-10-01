#!/usr/bin/env python3
"""Fetch CPS FY2026 budget data (school/unit level, line-item) from the public CPS OBIEE portal
(biportal.cps.edu, guest login published by CPS) via the OBIEE SOAP web service.
Writes CSVs to raw/cps/. Usage: python3 scripts/cps_fetch.py [year=2026]
"""
import csv, os, sys, time
sys.path.insert(0, os.path.dirname(__file__))
from cps_obiee import logon, logical_sql

YEAR = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
OUT = os.path.join(os.path.dirname(__file__), "..", "raw", "cps")
os.makedirs(OUT, exist_ok=True)
SA = '"CPS FY14 Budget Book"'   # subject area (holds FY2014-FY2027)
YF = ('"Unit"."Budget Year"=%d AND "Account"."Budget Year"=%d AND "Fund Grant"."Budget Year"=%d' % (YEAR, YEAR, YEAR))
YFP = YF + ' AND "Program"."Budget Year"=%d' % YEAR
EXP = '"Account"."Account Group"=\'Expenditures\''
NZ = '"Fact"."New Budget Amount" <> 0'

sid = logon()
def run(sql, maxrows=2000, retries=3):
    for i in range(retries):
        try:
            return logical_sql(sid, sql, maxrows)
        except Exception as e:
            print("  retry", i, str(e)[300:500].replace("\n", " "), flush=True)
            time.sleep(2)
            globals()["sid"] = logon()
    raise SystemExit("query failed: " + sql[:300])

def save(name, header, rows):
    p = os.path.join(OUT, "cps_%d_%s.csv" % (YEAR, name))
    with open(p, "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)
    print("wrote", p, len(rows), flush=True)

# ---- dimensions ----
ucols = ["Unit", "Unit Description", "Unit Category Description", "Unit Type", "Network Name", "Grade Type", "Leaf Unit", "Unit Level", "Parent Unit",
         "Level 1 Unit Description", "Level 2 Unit Description", "Level 3 Unit Description", "Level 4 Unit Description", "Level 5 Unit Description", "Level 6 Unit Description",
         "Unit Admin", "Unit Location Group", "Region Code", "Network Unit", "Network Number", "Area Number", "Cluster Number", "Demographics Flag"]
rows = run('SELECT %s FROM %s WHERE "Unit"."Budget Year"=%d' % (",".join('"Unit"."%s"' % c for c in ucols), SA, YEAR), 5000)
save("dim_unit", ucols, rows)

acols = ["Account", "Account Description", "Account Group", "Account SubGroup", "Level 1 Account Description", "Level 2 Account Description", "Level 3 Account Description", "Level 4 Account Description", "Leaf Account", "Major Category", "Sub Category", "Parent Account"]
rows = run('SELECT %s FROM %s WHERE "Account"."Budget Year"=%d' % (",".join('"Account"."%s"' % c for c in acols), SA, YEAR), 5000)
save("dim_account", acols, rows)

fcols = ["Fund Grant", "Fund Grant Description", "Fund Group", "Fund Subgroup", "Fund Type", "Parent Fund", "Parent Fund Description", "Leaf Fund Grant", "Fund Category Name"]
rows = run('SELECT %s FROM %s WHERE "Fund Grant"."Budget Year"=%d' % (",".join('"Fund Grant"."%s"' % c for c in fcols), SA, YEAR), 10000)
save("dim_fund", fcols, rows)

pcols = ["Program", "Program Description", "State Function Code", "State Function Description", "Leaf Program", "Level 1 Program Description", "Level 2 Program Description", "Level 3 Program Description"]
rows = run('SELECT %s FROM %s WHERE "Program"."Budget Year"=%d' % (",".join('"Program"."%s"' % c for c in pcols), SA, YEAR), 5000)
save("dim_program", pcols, rows)

# ---- facts ----
MEAS = ['"Fact"."New Budget Amount"', '"Fact"."New Budget FTE"', '"Fact"."Original Budget"', '"Fact"."Current Budget"', '"Fact"."Encumbered Expenses"']
MH = ["fy_new_budget", "fy_new_fte", "prev_original", "prev_current", "prev_projected_exp"]
WNZ = ('("Fact"."New Budget Amount" <> 0 OR "Fact"."Original Budget" <> 0 OR "Fact"."Current Budget" <> 0)')

# unit x fund x account (expenditures)
rows = run('SELECT "Unit"."Unit","Fund Grant"."Fund Grant","Account"."Account",%s FROM %s WHERE %s AND %s AND %s' % (",".join(MEAS), SA, YF, EXP, WNZ), 5000)
save("exp_unit_fund_account", ["unit", "fund_grant", "account"] + MH, rows)

# unit x fund x program x account (expenditures, current-year budget only), chunked by unit prefix
import string
allrows = []
for ch in string.digits:
    for ch2 in string.digits:
        pre = "U%s%s" % (ch, ch2)
        r = run('SELECT "Unit"."Unit","Fund Grant"."Fund Grant","Program"."Program","Account"."Account","Fact"."New Budget Amount","Fact"."New Budget FTE" FROM %s WHERE %s AND %s AND %s AND "Unit"."Unit" LIKE \'%s%%\'' % (SA, YFP, EXP, NZ, pre), 5000)
        allrows += r
        print(pre, len(r), flush=True)
save("exp_unit_fund_program_account", ["unit", "fund_grant", "program", "account", "fy_new_budget", "fy_new_fte"], allrows)

# revenue by account (district-wide) and by fund
rows = run('SELECT "Account"."Account","Fund Grant"."Fund Grant","Fact"."New Budget Amount","Fact"."Original Budget","Fact"."Current Budget" FROM %s WHERE %s AND "Account"."Account Group"=\'Revenue\' AND %s' % (SA, YF, WNZ), 5000)
save("rev_fund_account", ["account", "fund_grant", "fy_new_budget", "prev_original", "prev_current"], rows)

# positions: unit x job title
rows = run('SELECT "Unit"."Unit","Positions"."Job Code","Positions"."Job Title","Positions"."Position Class","Fact - Proposed Positions"."FTE","Fact - Proposed Positions"."Approriation Amount" FROM %s WHERE "Unit"."Budget Year"=%d' % (SA, YEAR), 5000)
save("positions_unit_job", ["unit", "job_code", "job_title", "position_class", "fte", "amount"], rows)
