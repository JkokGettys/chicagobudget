#!/usr/bin/env python3
"""CPS actuals vs budget from the BI subject area. In the FY<Y> dataset the 'Prior' measures describe FY<Y-2>:
   Prior Adopted Budget, Prior Approved Budget (ending), Prior Expenditures (actual).
 and 'Original Budget'/'Current Budget'/'Encumbered Expenses' describe FY<Y-1> (adopted, ending, projected spend).
Pulls unit x fund x account for dataset year Y (default 2026) -> raw/cps/cps_<Y>_actuals_unit_fund_account.csv
Usage: python3 scripts/cps_deep_actuals.py [Y]"""
import csv, os, sys, string, time
sys.path.insert(0, os.path.dirname(__file__))
from cps_obiee import logon, logical_sql
Y = int(sys.argv[1]) if len(sys.argv) > 1 else 2026
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps")
SA = '"CPS FY14 Budget Book"'
YF = '"Unit"."Budget Year"=%d AND "Account"."Budget Year"=%d AND "Fund Grant"."Budget Year"=%d' % (Y, Y, Y)
MEAS = ['"Fact"."Prior Adopted Budget"', '"Fact"."Prior Approved Budget"', '"Fact"."Prior Expenditures"', '"Fact"."Original Budget"', '"Fact"."Current Budget"', '"Fact"."Encumbered Expenses"', '"Fact"."New Budget Amount"']
H = ["adopted_Ym2", "ending_Ym2", "actual_Ym2", "adopted_Ym1", "ending_Ym1", "projected_Ym1", "budget_Y"]
sid = logon()
out = []
for pre in ["U%d" % i for i in range(0, 10)]:
    sql = 'SELECT "Unit"."Unit","Fund Grant"."Fund Grant","Account"."Account",%s FROM %s WHERE %s AND "Account"."Account Group"=\'Expenditures\' AND "Unit"."Unit" LIKE \'%s%%\' AND ("Fact"."Prior Expenditures"<>0 OR "Fact"."Prior Approved Budget"<>0 OR "Fact"."Prior Adopted Budget"<>0 OR "Fact"."New Budget Amount"<>0 OR "Fact"."Original Budget"<>0 OR "Fact"."Current Budget"<>0 OR "Fact"."Encumbered Expenses"<>0)' % (",".join(MEAS), SA, YF, pre)
    try:
        r = logical_sql(sid, sql, 5000)
    except Exception as e:
        # server runs out of memory on big prefixes: split to 2 digits
        r = []
        for d in string.digits:
            sql2 = sql.replace("LIKE '%s%%'" % pre, "LIKE '%s%s%%'" % (pre, d))
            r += logical_sql(sid, sql2, 5000)
    print(pre, len(r), flush=True); out += r
p = os.path.join(D, "cps_%d_actuals_unit_fund_account.csv" % Y)
with open(p, "w", newline="") as f:
    w = csv.writer(f); w.writerow(["unit", "fund_grant", "account"] + H); w.writerows(out)
tot = [sum(float(r[3 + i] or 0) for r in out) for i in range(7)]
print("wrote", p, len(out)); print(dict(zip(H, [round(t, 2) for t in tot])))
