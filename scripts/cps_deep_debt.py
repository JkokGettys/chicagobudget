#!/usr/bin/env python3
"""CPS FY26 debt service by bond series: BI fund-level lines (principal/interest) joined to
Budget Book Table 3 (outstanding principal, rate, maturity, pledged source).
Needs raw/cps/bb26.pdf.txt (text of FY2026 budget book) and cps_2026_exp_unit_fund_program_account.csv.
Outputs raw/cps/cps_2026_debt_by_series.csv"""
import csv, os, re, collections
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps")
f = lambda x: float(x) if x else 0.0
# ---- Table 3 from the budget book text ----
txt = open(os.path.join(D, "bb26.pdf.txt")).read()
i = txt.find("Maturity \nDate"); i = txt.find("ULT GO Series \n1998B-1*")
j = txt.find("Total Principal \nOutstanding")
blk = txt[i:j]
blk = re.sub(r"=====PAGE \d+=====|\n\s*\d{3}\n", "\n", blk)
t3 = {}
flat = re.sub(r"\s*\n\s*", " ", blk)
for m in re.finditer(r"(ULT GO(?: BAB| QSCB)? Series|CIT Series) (\S+?)\*? (\d\d/\d\d/\d\d) (\d\d/\d\d/\d\d) \$?([\d,]+) ([\d.%\-]+) ((?:EBF|IGA|CIT|PPRT|Federal|/|\s|Subsidy)+?)(?= ULT| CIT|$)", flat):
    kind, ser, issued, mat, prin, rate, src = m.groups()
    t3[("CIT " if kind.startswith("CIT") else "") + ser] = dict(kind=kind, issued=issued, maturity=mat, principal_outstanding=int(prin.replace(",", "")), rate=rate, pledged=src.strip())
# ---- BI lines ----
fd = {r["Fund Grant"]: r for r in csv.DictReader(open(os.path.join(D, "cps_2026_dim_fund.csv")))}
ad = {r["Account"]: r for r in csv.DictReader(open(os.path.join(D, "cps_2026_dim_account.csv")))}
agg = collections.defaultdict(lambda: {"principal": 0.0, "interest": 0.0, "other": 0.0})
for r in csv.DictReader(open(os.path.join(D, "cps_2026_exp_unit_fund_program_account.csv"))):
    if r["unit"] != "U12480": continue
    desc = ad[r["account"]]["Account Description"]
    k = (r["fund_grant"], fd[r["fund_grant"]]["Fund Grant Description"])
    kind = "principal" if "Principal" in desc else "interest" if "Interest" in desc else "other"
    agg[k][kind] += f(r["fy_new_budget"])
def series_key(desc):
    m = re.search(r"(\d{4}[A-Z]?(?:-\d)?)", desc)
    if not m: return None
    s = m.group(1)
    return ("CIT " + s) if "CIT" in desc else s
out = []
for (fg, desc), v in sorted(agg.items(), key=lambda x: -(x[1]["principal"] + x[1]["interest"] + x[1]["other"])):
    s = series_key(desc); t = t3.get(s) or (t3.get(s + "E") if s and s.startswith("2015C") else None) or {}
    out.append([fg, desc, s or "", round(v["principal"], 2), round(v["interest"], 2), round(v["other"], 2), round(sum(v.values()), 2),
                t.get("principal_outstanding", ""), t.get("rate", ""), t.get("maturity", ""), t.get("pledged", "")])
with open(os.path.join(D, "cps_2026_debt_by_series.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["fund_grant", "bi_fund_description", "series_key", "fy26_principal", "fy26_interest", "fy26_other", "fy26_total", "principal_outstanding_6_30_2025", "fixed_rate", "final_maturity", "pledged_source"]); w.writerows(out)
print("table3 series parsed:", len(t3), "| BI series funds:", len(out), "| matched:", sum(1 for o in out if o[7] != ""), "| total", round(sum(o[6] for o in out), 2))
print("principal", round(sum(o[3] for o in out), 2), "interest", round(sum(o[4] for o in out), 2), "other", round(sum(o[5] for o in out), 2))
print("table3 total principal outstanding:", sum(t["principal_outstanding"] for t in t3.values()))
