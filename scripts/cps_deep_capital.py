#!/usr/bin/env python3
"""CPS FY26 capital budget at project level, plus phase split parsed from each project's public PDF.
Outputs raw/cps/cps_2026_capital_projects_detail.csv and raw/cps/cps_2026_capital_phases.csv
Run: python3 scripts/cps_deep_capital.py"""
import csv, os, re, sys, subprocess, urllib.parse, io
sys.path.insert(0, os.path.dirname(__file__))
from cps_obiee import logon, logical_sql
from pypdf import PdfReader
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps"); PD = os.path.join(D, "capital_pdfs"); os.makedirs(PD, exist_ok=True)
YEAR = 2026
cols = ["Unit", "Unit Name", "Project Number", "Project Name", "Project Type", "Main Category", "Sub Category", "Project Source", "Project Status", "Address", "Ward Number", "Alderman", "PDF URL", "Budget Source"]
sql = 'SELECT %s,"Fact"."Budget" FROM "CPS Capital Budget" WHERE "Dim - Capital"."Budget Year"=%d AND "Dim - Capital"."Project Budget Year"=%d' % (",".join('"Dim - Capital"."%s"' % c for c in cols), YEAR, YEAR)
rows = logical_sql(logon(), sql, 5000)
phase_rows = []
ok = 0
for r in rows:
    url = r[12] or ""
    ph = {}
    if url.startswith("http"):
        fn = os.path.join(PD, re.sub(r"[^A-Za-z0-9_.-]", "_", url.split("/")[-1]))
        if not os.path.exists(fn):
            subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "-o", fn, urllib.parse.quote(url, safe=":/%")], check=False)
        try:
            txt = "\n".join((p.extract_text() or "") for p in PdfReader(fn).pages)
            m = re.search(r"Budget Amount:\s*\$([\d,]+)", txt)
            # phase lines look like "$3,482,100Construction"
            for amt, name in re.findall(r"\$([\d,]+)(Design|Construction|Environmental|Management|Equipment|Contingency|Planning|Other)", txt):
                ph[name] = ph.get(name, 0) + int(amt.replace(",", ""))
            if ph: ok += 1
        except Exception as e:
            print("pdf err", fn, e)
    for k, v in ph.items():
        phase_rows.append([r[0], r[2], r[3], k, v])
# the "Original Budget" figure printed before phases is the first-phase line; keep raw so reviewers can check
with open(os.path.join(D, "cps_2026_capital_projects_detail.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(cols + ["budget"]); w.writerows(rows)
with open(os.path.join(D, "cps_2026_capital_phases.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["unit", "project_number", "project_name", "phase", "amount"]); w.writerows(phase_rows)
print(len(rows), "projects;", ok, "with parsed phases;", len(phase_rows), "phase rows")
