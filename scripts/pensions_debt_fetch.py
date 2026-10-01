"""Download the public source PDFs for the pensions + debt research and extract text.

Everything lands in raw/pensions_debt/ (gitignored). Existing files are kept, so this is
safe to re-run. Text extraction writes one .txt next to each PDF, with page markers of the
form "=====PAGE n=====" (n is the 1-based PDF page index, not the printed page label).

Usage: python3 scripts/pensions_debt_fetch.py
Requires: python3 + pypdf. Network access to chicago.gov, bondlink-cdn.com, and the four
pension fund sites. EMMA (emma.msrb.org) is NOT used: it times out from automated clients
and needs an interactive disclaimer click, so per-CUSIP data is listed as a gap in
research/pensions_debt.md.
"""
import os
import urllib.request

import pypdf

RAW = os.path.join(os.path.dirname(__file__), "..", "raw", "pensions_debt")

# (relative path under raw/pensions_debt, url)
SOURCES = [
    # City ACFR FY2025 (debt Tables 22-25, notes 10-11, pension RSI)
    ("acfr2025.pdf",
     "https://www.chicago.gov/content/dam/city/depts/fin/supp_info/CAFR/2025CAFR/"
     "2025%20ANNUAL%20COMPREHENSIVE%20FINANCIAL%20REPORT__v2.pdf"),
    # 2026 Budget Overview (OBM)
    ("overview2026.pdf",
     "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf"),
    # 2027 Budget Forecast (OBM, August 2026)
    ("forecast2027.pdf",
     "https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Forecast/2027_Chicago_Budget_Forecast.pdf"),
    # FY2026 Annual Appropriation Ordinance (BondLink copy of the City document)
    ("os/FY2026-Annual-Appropriation-Ordinance.Vsr9wxc2u.pdf",
     "https://bondlink-cdn.com/1338/FY2026-Annual-Appropriation-Ordinance.Vsr9wxc2u.pdf"),
    # GO official statements (use of proceeds)
    ("os/ILChicago02a-FIN.D8Ebm0ZNE.pdf",  # GO Taxable 2026A/B, March 2026
     "https://bondlink-cdn.com/1338/ILChicago02a-FIN.D8Ebm0ZNE.pdf"),
    ("os/OS.GE3zX31VR.pdf",  # GO 2025A-E
     "https://bondlink-cdn.com/1338/OS.GE3zX31VR.pdf"),
    ("os/OS.Uxunte2ez.pdf",  # GO 2025F/G (Housing and Economic Development)
     "https://bondlink-cdn.com/1338/OS.Uxunte2ez.pdf"),
    ("os/GO2024A.pdf",
     "https://bondlink-cdn.com/1338/General-Obligation-Bonds-Series-2024A.qIfFSWQzr.pdf"),
    ("os/GO2023AB.pdf",
     "https://bondlink-cdn.com/1338/GO-2023AB-OS.TQ3FvIUd3.pdf"),
    ("os/GO2024B.pdf",
     "https://bondlink-cdn.com/1338/Supplement-to-the-Supplement-to-the-OS--Dated-12.19.2024.5KuWH6GRr.pdf"),
    # Water Revenue Bonds 2026A/B/C (sold May 2026)
    ("os/ILChicago04a-FIN.yO9Z1Tmxh.pdf",
     "https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf"),
    # Sales Tax Securitization Corporation
    ("stsc/FY25-STSC-Financial-Statements---Issued--1.sdgdZJ5QA.pdf",
     "https://bondlink-cdn.com/2925/FY25-STSC-Financial-Statements---Issued--1.sdgdZJ5QA.pdf"),
    ("stsc/ILSalesTax01a-FIN.ouftBIpEZ.pdf",
     "https://bondlink-cdn.com/2925/ILSalesTax01a-FIN.ouftBIpEZ.pdf"),
    ("stsc/OC.XFXm0gZ8C.pdf", "https://bondlink-cdn.com/2925/OC.XFXm0gZ8C.pdf"),
    ("stsc/Final-OC.qnWB3nNOk.pdf", "https://bondlink-cdn.com/2925/Final-OC.qnWB3nNOk.pdf"),
    # Enterprise fund financial statements 2025
    ("ent/ohare_fs2025.pdf",
     "https://bondlink-cdn.com/1348/O-Hare-International-Airport-Financial-Statement-2025.0sROg23GQ.pdf"),
    ("ent/midway_fs2025.pdf",
     "https://bondlink-cdn.com/1351/Midway-International-Airport-Financial-Statement-2025.4TGhWWzsT.pdf"),
    ("ent/water_fs2025.pdf",
     "https://bondlink-cdn.com/1344/Water-Fund-Financial-Statement-2025.DkesDt8Gu.pdf"),
    ("ent/sewer_fs2025.pdf",
     "https://bondlink-cdn.com/1345/Sewer-Fund-Financial-Statements-2025.vcXRD2uoM.pdf"),
    # Pension fund actuarial valuations as of 12/31/2025
    ("funds/PABF_20251231_Final.pdf",
     "https://chipabf.org/wp-content/uploads/2026/07/PABF_20251231_Final.pdf"),
    ("funds/FABF_val_2025.pdf",
     "https://fabf.org/LinkClick.aspx?fileticket=G_bIYnMR31w%3d&portalid=0"),
    ("funds/MEABF_val_2025.pdf",
     "https://www.meabf.org/wp-content/uploads/2026/06/"
     "MEABF_Actuarial-Valuation-Report-as-of-12.31.2025-06.26.2026.pdf"),
    ("funds/LABF_GRS_2025_Val.pdf",
     "https://www.labfchicago.org/assets/1/7/GRS_2025_Val.pdf"),
]


def download(rel, url):
    path = os.path.join(RAW, rel)
    if os.path.exists(path) and os.path.getsize(path) > 10_000:
        return path
    os.makedirs(os.path.dirname(path), exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=180) as r, open(path, "wb") as f:
        f.write(r.read())
    print("downloaded", rel)
    return path


ALIASES = {"os/FY2026-Annual-Appropriation-Ordinance.Vsr9wxc2u.pdf": "os/ordinance2026.txt"}


def extract_text(pdf_path, txt=None):
    txt = txt or pdf_path[:-4] + ".txt"
    if os.path.exists(txt) and os.path.getsize(txt) > 1000:
        return txt
    reader = pypdf.PdfReader(pdf_path)
    with open(txt, "w") as f:
        for i, p in enumerate(reader.pages):
            f.write(f"\n=====PAGE {i + 1}=====\n{p.extract_text() or ''}")
    print("extracted", os.path.relpath(txt, RAW), len(reader.pages), "pages")
    return txt


def main():
    for rel, url in SOURCES:
        alias = ALIASES.get(rel)  # the ordinance text is read under a stable name by the build script
        extract_text(download(rel, url), os.path.join(RAW, alias) if alias else None)


if __name__ == "__main__":
    main()
