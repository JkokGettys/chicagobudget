#!/usr/bin/env python3
"""Build small committed tables in data/:
  data/cps_pension_insurance_fy26.csv   BI lines for 'Pension & Liability Insurance - City Wide' (U12470) + district-wide pension/health accounts
  data/cps_ctpf_valuation_2025.csv      CTPF 6/30/2025 actuarial valuation key figures (parsed from ctpf_val2025.txt, page refs)
  data/cps_charter_by_school_fy26.csv   per charter unit: FY26 tuition budget, enrollment (CPS school profile API), per pupil
  data/cps_debt_by_series_fy26.csv      copy of raw/cps/cps_2026_debt_by_series.csv
  data/cps_capital_projects_fy26.csv    131 FY26 capital projects (+ phase split where the project PDF has one)
  data/cps_depth_summary.csv            copy of depth table
Needs raw/cps/* from cps_fetch.py, cps_deep_*.py, ctpf_val2025.pdf text."""
import csv, json, os, re, shutil, subprocess, collections
ROOT = os.path.join(os.path.dirname(__file__), "..")
D = os.path.join(ROOT, "raw", "cps"); O = os.path.join(ROOT, "data"); os.makedirs(O, exist_ok=True)
rd = lambda n: list(csv.DictReader(open(os.path.join(D, n))))
f = lambda x: float(x) if x else 0.0
ad = {r["Account"]: r for r in rd("cps_2026_dim_account.csv")}
fd = {r["Fund Grant"]: r for r in rd("cps_2026_dim_fund.csv")}
pd = {r["Program"]: r for r in rd("cps_2026_dim_program.csv")}
ud = {r["Unit"]: r for r in rd("cps_2026_dim_unit.csv")}
p = rd("cps_2026_exp_unit_fund_program_account.csv")

# ---- pension / insurance central unit ----
with open(os.path.join(O, "cps_pension_insurance_fy26.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["unit", "fund_grant", "fund", "program", "account", "account_description", "fy26_budget"])
    for r in sorted([r for r in p if r["unit"] == "U12470" and f(r["fy_new_budget"]) != 0], key=lambda r: -f(r["fy_new_budget"])):
        w.writerow([r["unit"], r["fund_grant"], fd[r["fund_grant"]]["Fund Grant Description"], pd.get(r["program"], {}).get("Program Description", r["program"]), r["account"], ad[r["account"]]["Account Description"], round(f(r["fy_new_budget"]), 2)])

# ---- CTPF valuation, regex on pdf text ----
txt = open(os.path.join(D, "ctpf_val2025.txt")).read()
def grab(label, nth=0):
    m = re.findall(re.escape(label) + r"[^\n$\d-]*\$?([\d,\.]+%?)\$?\s+\$?([\d,\.]+%?)", txt)
    return m[nth] if m else None
rows = []
for label, fy in [("Required Board of Education Contributions", "p.1 Exec Summary"), ("Additional Board of Education Contributions (0.58 percent of pay)", "p.1"),
                  ("Additional State Contributions (0.544 percent of pay)", "p.1"), ("State Contributions Pursuant to P.A. 100-0465 (Normal Cost)a", "p.1"),
                  ("Total Required Employer Contributions", "p.1"), ("Active Membersc", "p.1"), ("Members Receiving Payments", "p.1"),
                  ("Covered Payroll as of the Actuarial Valuation Date", "p.1"), ("Annualized Benefit Payments", "p.1"),
                  ("Fair Value of Assets (FVA)", "p.1"), ("Actuarial Value of Assets (AVA)", "p.1"), ("Actuarial Accrued Liability (AAL)", "p.1"),
                  ("Unfunded Actuarial Accrued Liability (UAAL)", "p.1"), ("Funded Ratio based on Actuarial Value of Assets", "p.1"),
                  ("Total Normal Cost Amount (Including Admin. Expenses)", "p.1"), ("Employer's Normal Cost Amount (Including Admin. Expenses)", "p.1")]:
    g = grab(label)
    rows.append([label.rstrip("abcd") if label.endswith(("c", "a")) and "Members" in label or "Normal Cost)a" in label else label, g[0] if g else "", g[1] if g else "", fy])
extra = [("Retirees: number / average annual benefit / total annual benefit", "23,350 / $64,860 / $1,514,469,736", "23,556 / $63,312 / $1,491,374,326", "Table 11 p.44"),
         ("Disabled retirees: number / average / total", "408 / $47,128 / $19,228,116", "415 / $45,853 / $19,028,934", "Table 11 p.44"),
         ("Beneficiaries: number / average / total", "3,399 / $29,749 / $101,118,302", "3,388 / $28,685 / $97,185,601", "Table 11 p.44"),
         ("Active members: average salary", "$84,796", "$85,362", "Table 11 p.44")]
with open(os.path.join(O, "cps_ctpf_valuation_2025.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["item", "col_1 (left col in PDF)", "col_2 (right col in PDF)", "source", "note"])
    for r in rows: w.writerow([r[0], r[1], r[2], "CTPF Actuarial Valuation 6/30/2025 " + r[3], "columns: FY2027 req. / FY2026 req. for contributions; valuation 6/30/2025 / 6/30/2024 for membership, assets"])
    for r in extra: w.writerow([r[0], r[1], r[2], "CTPF Actuarial Valuation 6/30/2025 " + r[3], "valuation 6/30/2025 / 6/30/2024"])

# ---- charters ----
prof_path = os.path.join(D, "sprof.json")
if not os.path.exists(prof_path):
    subprocess.check_call(["curl", "-s", "-A", "Mozilla/5.0", "-o", prof_path, "https://api.cps.edu/schoolprofile/CPS/AllSchoolProfiles"])
prof = {("U%05d" % x["FinanceID"]): x for x in json.load(open(prof_path)) if x["FinanceID"]}
a = rd("cps_2026_exp_unit_fund_account.csv")
tu = collections.defaultdict(float)
for r in a:
    if "Charter" in ad[r["account"]]["Account Description"]: tu[r["unit"]] += f(r["fy_new_budget"])
with open(os.path.join(O, "cps_charter_by_school_fy26.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["unit", "name", "unit_type", "network_unit_group", "fy26_charter_tuition_budget", "students_profile_api", "per_pupil", "profile_governance"])
    for u, v in sorted(tu.items(), key=lambda x: -x[1]):
        x = prof.get(u); n = x["StudentCount"] if x else ""
        w.writerow([u, ud[u]["Unit Description"], ud[u]["Unit Type"], ud[u]["Level 4 Unit Description"], round(v, 2), n, round(v / n, 2) if n else "", x["Governance"] if x else ""])

# ---- capital ----
ph = collections.defaultdict(dict)
for r in rd("cps_2026_capital_phases.csv"): ph[(r["unit"], r["project_number"], r["project_name"])][r["phase"]] = r["amount"]
with open(os.path.join(O, "cps_capital_projects_fy26.csv"), "w", newline="") as fh:
    w = csv.writer(fh); w.writerow(["unit", "unit_name", "project_number", "project_name", "project_type", "main_category", "sub_category", "source", "status", "ward", "alderman", "budget", "design", "construction", "environmental", "management", "pdf_url"])
    for r in rd("cps_2026_capital_projects_detail.csv"):
        q = ph.get((r["Unit"], r["Project Number"], r["Project Name"]), {})
        w.writerow([r["Unit"], r["Unit Name"], r["Project Number"], r["Project Name"], r["Project Type"], r["Main Category"], r["Sub Category"], r["Project Source"], r["Project Status"], r["Ward Number"], r["Alderman"], r["budget"], q.get("Design", ""), q.get("Construction", ""), q.get("Environmental", ""), q.get("Management", ""), r["PDF URL"]])
for src, dst in [("cps_2026_debt_by_series.csv", "cps_debt_by_series_fy26.csv"), ("cps_depth_summary.csv", "cps_depth_summary.csv")]:
    shutil.copy(os.path.join(D, src), os.path.join(O, dst))
# ---- procurement: vendor payments >= $1M per FY and parsed board awards ----
for y in (2024, 2025, 2026):
    sp = json.load(open(os.path.join(D, "cps_supplier_payments_FY%d.json" % y)))
    with open(os.path.join(O, "cps_supplier_payments_fy%d_over1m.csv" % y), "w", newline="") as fh:
        w = csv.writer(fh); w.writerow(["fiscal_year", "supplier_id", "vendor", "city", "state", "payment_amount"])
        for x in sorted([x for x in sp if x["PaymentAmount"] >= 1e6], key=lambda x: -x["PaymentAmount"]):
            w.writerow([y, x["SupplierID"], x["Name"], x["City"], x["State"], x["PaymentAmount"]])
shutil.copy(os.path.join(D, "cps_contract_awards_parsed.csv"), os.path.join(O, "cps_contract_awards_fy21_27.csv"))
print("ok")
