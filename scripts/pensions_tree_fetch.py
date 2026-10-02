#!/usr/bin/env python3
"""Fetch and cache the pension fund documents used by scripts/pensions_tree_build.py into raw/pensions_tree/ (gitignored).
Existing files are kept. Text is extracted page by page with '=====PAGE n=====' markers (n = PDF page index, 1 = cover)."""
import os, shutil, urllib.request
import pypdf
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "pensions_tree")
OLD = os.path.join(ROOT, "raw", "pensions_debt", "funds")
SOURCES = [
    ("PABF_val_2025", "https://chipabf.org/wp-content/uploads/2026/07/PABF_20251231_Final.pdf", "PABF_20251231_Final"),
    ("PABF_FS_2025", "https://chipabf.org/wp-content/uploads/2026/07/final_PABF_FS_2025.pdf", "PABF_FS_2025"),
    ("FABF_val_2025", "https://fabf.org/LinkClick.aspx?fileticket=G_bIYnMR31w%3d&portalid=0", "FABF_val_2025"),
    ("MEABF_val_2025", "https://www.meabf.org/wp-content/uploads/2026/06/MEABF_Actuarial-Valuation-Report-as-of-12.31.2025-06.26.2026.pdf", "MEABF_val_2025"),
    ("LABF_val_2025", "https://www.labfchicago.org/assets/1/7/GRS_2025_Val.pdf", "LABF_GRS_2025_Val"),
    ("LABF_FS_2025", "https://www.labfchicago.org/assets/1/7/2025_LABF_Issued_Financial_Statements.pdf", "LABF_FS_2025"),
]
os.makedirs(RAW, exist_ok=True)
for name, url, old in SOURCES:
    pdf = os.path.join(RAW, name + ".pdf")
    if not (os.path.exists(pdf) and os.path.getsize(pdf) > 10_000):
        if os.path.exists(os.path.join(OLD, old + ".pdf")):
            shutil.copy(os.path.join(OLD, old + ".pdf"), pdf)
        else:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=180) as r, open(pdf, "wb") as f:
                f.write(r.read())
        print("cached", name)
    txt = os.path.join(RAW, name + ".txt")
    if not (os.path.exists(txt) and os.path.getsize(txt) > 1000):
        rd = pypdf.PdfReader(pdf)
        with open(txt, "w") as f:
            for i, p in enumerate(rd.pages):
                f.write(f"\n=====PAGE {i + 1}=====\n{p.extract_text() or ''}")
        print("extracted", name, len(rd.pages), "pages")
