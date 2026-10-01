#!/usr/bin/env python3
"""Quantify how much of the CPS FY26 budget sits in leaves < $1M, before and after each extra source.
Reads raw/cps CSVs made by cps_fetch.py, cps_deep_*.py, cps_fetch_roster.py. Writes raw/cps/cps_depth_summary.csv and prints a table."""
import csv, os, collections, json
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps")
rd = lambda n: list(csv.DictReader(open(os.path.join(D, n))))
f = lambda x: float(x) if x else 0.0
ad = {r["Account"]: r for r in rd("cps_2026_dim_account.csv")}
p = rd("cps_2026_exp_unit_fund_program_account.csv")
pos = rd("cps_2026_positions_unit_job.csv")
cap = rd("cps_2026_capital_projects_detail.csv")
ph = rd("cps_2026_capital_phases.csv")
T = sum(f(r["fy_new_budget"]) for r in p)
CAPF = {"FG455-000000", "FG436-000000", "FG425-000000", "FG496-000000"}
small = sum(f(r["fy_new_budget"]) for r in p if abs(f(r["fy_new_budget"])) < 1e6)
big = [r for r in p if abs(f(r["fy_new_budget"])) >= 1e6]
out = []
def add(name, dollars, note):
    out.append([name, round(dollars, 2), round(100 * dollars / T, 2), note])
add("A. Leaves < $1M today (unit x fund x program x account)", small, "%d of %d rows" % (sum(1 for r in p if abs(f(r["fy_new_budget"])) < 1e6), len(p)))
# B. capital: replace the 4 capital-fund leaves by project rows (external ties exactly; bond-funded differs by rounding)
capbi = sum(f(r["fy_new_budget"]) for r in big if r["fund_grant"] in CAPF)
proj_small = sum(f(r["budget"]) for r in cap if f(r["budget"]) < 1e6)
phk = collections.defaultdict(list)
for r in ph: phk[(r["unit"], r["project_number"], r["project_name"])].append(f(r["amount"]))
phase_small = sum(sum(x for x in phk[(r["Unit"], r["Project Number"], r["Project Name"])] if x < 1e6) for r in cap if f(r["budget"]) >= 1e6 and (r["Unit"], r["Project Number"], r["Project Name"]) in phk)
add("B. + capital projects < $1M and project phases < $1M", proj_small + phase_small, "capital-fund leaves $%.1fM replaced by %d projects; project list sums to $%.0f vs fund lines $%.0f" % (capbi / 1e6, len(cap), sum(f(r["budget"]) for r in cap), capbi))
# C. salary via BI positions (unit x job title). Upper bound per unit: min(big salary leaves in unit, job-title rows < $1M in unit)
sb = collections.defaultdict(float)
for r in big:
    if ad[r["account"]]["Account SubGroup"] == "Salary" and f(r["fy_new_budget"]) > 0: sb[r["unit"]] += f(r["fy_new_budget"])
ps = collections.defaultdict(float)
for r in pos:
    if abs(f(r["amount"])) < 1e6: ps[r["unit"]] += f(r["amount"])
add("C. + big salary leaves covered by BI job-title rows < $1M (upper bound, unit level)", sum(min(v, ps[u]) for u, v in sb.items()), "positions file is by unit x job title, not by fund, so this is a bound not a tie")
# D. all salary and school-side benefits to person level via public roster (every person < $1M)
bb = sum(f(r["fy_new_budget"]) for r in big if ad[r["account"]]["Account SubGroup"] == "Benefits" and r["unit"] != "U12470" and f(r["fy_new_budget"]) > 0)
sal_all = sum(sb.values())
def _is_sb(r):
    a = ad[r["account"]]
    return f(r["fy_new_budget"]) > 0 and r["unit"] not in ("U12480", "U12470") and r["fund_grant"] not in CAPF and "Charter" not in a["Account Description"] and a["Account SubGroup"] in ("Salary", "Benefits")
sb_bucket = sum(f(r["fy_new_budget"]) for r in big if _is_sb(r))
sb = collections.defaultdict(float)
for r in big:
    if _is_sb(r) and ad[r["account"]]["Account SubGroup"] == "Salary": sb[r["unit"]] += f(r["fy_new_budget"])
C = sum(min(v, ps[u]) for u, v in sb.items()); out[-1][1] = round(C, 2); out[-1][2] = round(100 * C / T, 2)
add("D. + remaining big salary and employer-benefit leaves via public roster (person level)", sb_bucket - C, "roster max FTE salary $335,000; roster date 12/31/2025 so approximate, not a reconciled tie")
# remaining buckets (not drillable below $1M from public data found)
def bucket(r):
    a = ad[r["account"]]; u = r["unit"]
    if f(r["fy_new_budget"]) < 0: return "negative offset lines (budget-only reductions, e.g. U12670, U12470)"
    if _is_sb(r): return "salary/benefits (see C, D)"
    if u == "U12480": return "debt series (named bond, principal or interest)"
    if r["fund_grant"] in CAPF: return "capital (see B)"
    if u == "U12470": return "central pension/insurance/health set-aside"
    if "Charter" in a["Account Description"]: return "charter tuition (per school)"
    if a["Account SubGroup"] in ("Salary", "Benefits"): return "salary/benefits (see C, D)"
    return "other contracts, utilities, food, transport, contingency"
rem = collections.defaultdict(float); cnt = collections.Counter()
for r in big:
    b = bucket(r); rem[b] += f(r["fy_new_budget"]); cnt[b] += 1
for b in sorted(rem, key=lambda k: -rem[k]):
    out.append(["Leaves >= $1M: " + b, round(rem[b], 2), round(100 * rem[b] / T, 2), "%d rows" % cnt[b]])
AFTER = sum(o[1] for o in out[:4])
out.insert(0, ["BEFORE: share of $ in leaves < $1M", out[0][1], out[0][2], "same as row A"])
out.insert(5, ["AFTER: A + B + C + D", round(AFTER, 2), round(100 * AFTER / T, 2), "upper bound: C and D assume the public positions and roster files can be allocated to each leaf"])
w = csv.writer(open(os.path.join(D, "cps_depth_summary.csv"), "w", newline="")); w.writerow(["item", "dollars", "pct_of_total", "note"]); w.writerows(out)
print("TOTAL %.2f" % T)
for o in out: print("%-95s %16s %7s%%  %s" % tuple(o))
