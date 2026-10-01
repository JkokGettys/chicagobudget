#!/usr/bin/env python3
"""Download ISBE 2025 Illinois Report Card public data set and extract Chicago SD 299 school finance (per-pupil spending).
Outputs raw/cps/rc2025.xlsx and raw/cps/cps_isbe_2025_school_finance.csv"""
import csv, os, subprocess, openpyxl
D = os.path.join(os.path.dirname(__file__), "..", "raw", "cps"); os.makedirs(D, exist_ok=True)
X = os.path.join(D, "rc2025.xlsx")
if not os.path.exists(X):
    subprocess.check_call(["curl", "-sL", "-A", "Mozilla/5.0", "-o", X, "https://www.isbe.net/_layouts/Download.aspx?SourceUrl=/Documents/2025-Report-Card-Public-Data-Set.xlsx"])
wb = openpyxl.load_workbook(X, read_only=True)
it = wb["Finance"].iter_rows(values_only=True)
hdr = [str(h).strip() if h else "" for h in next(it)]
n = 0
with open(os.path.join(D, "cps_isbe_2025_school_finance.csv"), "w", newline="") as f:
    w = csv.writer(f); w.writerow(hdr)
    for r in it:
        if r[1] and str(r[1]).startswith("15-016-2990") or (r[4] and "Chicago" in str(r[4]) and "299" in str(r[4])):
            w.writerow(r); n += 1
print("rows", n)
