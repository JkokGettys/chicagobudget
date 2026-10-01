#!/usr/bin/env python3
"""CPS public procurement data (api.cps.edu/procurement, the JSON API behind cps.edu/procurement pages).
 1. Supplier payments per vendor per fiscal year (FY2001-FY2027)   -> raw/cps/cps_supplier_payments_FY<y>.json
 2. Board-approved contract awards per fiscal year                  -> raw/cps/cps_contract_awards_FY<y>.json
 3. For awards in the target years, download each Board Report PDF (cpsboe.org) and parse the
    'USER INFORMATION' unit code (maps to BI unit U<code>), vendor, amount, term -> raw/cps/cps_contract_awards_parsed.csv
Usage: python3 scripts/cps_deep_contracts.py [fy ...]   (default 2026 2025)"""
import csv, json, os, re, subprocess, sys, urllib.request
from pypdf import PdfReader
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps"); PD = os.path.join(D, "board_reports"); os.makedirs(PD, exist_ok=True)
API = "https://api.cps.edu/procurement"
def get(path):
    return json.loads(urllib.request.urlopen(urllib.request.Request(API + path, headers={"User-Agent": "Mozilla/5.0"}), timeout=300).read())
years = [int(a) for a in sys.argv[1:]] or [2026, 2025]
money = lambda s: float(re.sub(r"[^\d.\-]", "", s)) if s and re.search(r"\d", s) else 0.0
rows = []
for y in years:
    sp = get("/Supplier/GetSupplierPayments?reportyear=%d" % y)
    json.dump(sp, open(os.path.join(D, "cps_supplier_payments_FY%d.json" % y), "w"))
    ca = get("/contracthistory/GetContractAwards?reportyear=%d" % y)
    json.dump(ca, open(os.path.join(D, "cps_contract_awards_FY%d.json" % y), "w"))
    print("FY%d supplier payment rows %d ($%.1fM), awards %d" % (y, len(sp), sum(x["PaymentAmount"] for x in sp) / 1e6, len(ca)))
    for a in ca:
        fn = os.path.join(PD, a["BOARD_REPORT_NUMBER"] + ".pdf")
        units, pm = [], ""
        if not a["DOCUMENT_URL"]:
            pm = "NO_DOC_URL"      # delegated-authority / non-board items have no Board Report PDF
        elif not os.path.exists(fn):
            subprocess.run(["curl", "-sL", "-A", "Mozilla/5.0", "-o", fn, a["DOCUMENT_URL"]])
        if pm:
            pass
        elif open(fn, "rb").read(5) != b"%PDF-":
            pm = "PDF_404"         # cpsboe.org returns an HTML 404 for some old reports
        else:
          try:
            txt = "\n".join((p.extract_text() or "") for p in PdfReader(fn).pages)
            i = txt.find("USER INFORMATION")
            seg = txt[i:i + 600] if i >= 0 else ""
            units = re.findall(r"\b(\d{5})\s*-\s*([^\n]+)", seg)
            pm = ";".join("%s %s" % u for u in units) or "NO_USER_UNIT"
          except Exception as e:
            pm = "PDF_ERR"
        rows.append([y, a["BOARD_REPORT_NUMBER"], a["CONTRACT_NUMBER"], a["VENDOR"], money(a["CONTRACT_AMOUNT"]), money(a["AUTHORIZED_AMOUNT"]),
                     a["ACTUAL_START_DATE"], a["ESTIMATED_COMPLETION_DATE"], a["SECRETARY_SIGNED_DISPLAY_DATE"], pm, re.sub(r"\s+", " ", a["PROJECT_NAME"] or "").strip()])
with open(os.path.join(D, "cps_contract_awards_parsed.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(["fy", "board_report", "contract_number", "vendor", "contract_amount", "authorized_amount", "start", "end", "signed", "user_units", "project_name"]); w.writerows(rows)
print("wrote", len(rows), "awards;", sum(1 for r in rows if r[9] and r[9] != "PDF_ERR"), "with user unit code (after excluding status flags below)")
