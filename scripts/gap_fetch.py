"""Fetch the "gap" sources (things the other agents did not pull) into raw/gap/.

Everything here is public and unauthenticated. Idempotent: files that already exist
are skipped (delete a file to refresh it).

Usage: python3 scripts/gap_fetch.py [--only name,name]
Groups: socrata, obm, elms, cps, parks, cook

Needs: python3 stdlib + pypdf (for PDF to text).
"""
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw", "gap")
UA = {"User-Agent": "Mozilla/5.0"}
OBM = "https://www.chicago.gov/content/dam/city/depts/obm"


def path(*p):
    full = os.path.join(RAW, *p)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    return full


def get_bytes(url, timeout=120):
    req = urllib.request.Request(url, headers=UA)
    return urllib.request.urlopen(req, timeout=timeout).read()


def get_json(url, timeout=120):
    return json.loads(get_bytes(url, timeout))


def save(url, name):
    dest = path(name)
    if os.path.exists(dest) and os.path.getsize(dest) > 0:
        return dest
    try:
        data = get_bytes(url)
    except (urllib.error.URLError, OSError) as e:
        print(f"  FAIL {name}: {e}")
        return None
    open(dest, "wb").write(data)
    print(f"  saved {name} ({len(data):,} bytes)")
    return dest


def save_json(obj, name):
    json.dump(obj, open(path(name), "w"))
    print(f"  wrote {name}")


def pdf_to_text(pdf):
    """Write <pdf>.txt with '=====PAGE n=====' separators."""
    txt = pdf[:-4] + ".txt"
    if not pdf or os.path.exists(txt):
        return
    import pypdf
    r = pypdf.PdfReader(pdf)
    out = [f"=====PAGE {i + 1}=====\n" + (p.extract_text() or "") for i, p in enumerate(r.pages)]
    open(txt, "w").write("\n".join(out))
    print(f"  text  {os.path.basename(txt)} ({len(r.pages)} pages)")


def socrata_all(resource, name, order=":id"):
    dest = path(name)
    if os.path.exists(dest):
        return
    rows, off = [], 0
    while True:
        q = urllib.parse.urlencode({"$limit": 50000, "$offset": off, "$order": order})
        d = get_json(f"https://data.cityofchicago.org/resource/{resource}.json?{q}")
        rows += d
        if len(d) < 50000:
            break
        off += 50000
    save_json(rows, name)


# ---------------------------------------------------------------- socrata
def g_socrata():
    print("socrata")
    # Admin & Finance category scan. The category filter only works with search_context.
    if not os.path.exists(path("catalog_admin_finance.json")):
        out = []
        for off in (0, 200):
            q = urllib.parse.urlencode({
                "domains": "data.cityofchicago.org", "search_context": "data.cityofchicago.org",
                "categories": "Administration & Finance", "limit": 200, "offset": off,
                "only": "datasets,files,maps,charts,filters"})
            out += get_json("https://api.us.socrata.com/api/catalog/v1?" + q)["results"]
        save_json(out, "catalog_admin_finance.json")
    # Whole-portal catalog (all assets)
    if not os.path.exists(path("catalog_all.json")):
        out = []
        for off in range(0, 10000, 200):
            q = urllib.parse.urlencode({"domains": "data.cityofchicago.org",
                                        "search_context": "data.cityofchicago.org",
                                        "limit": 200, "offset": off})
            d = get_json("https://api.us.socrata.com/api/catalog/v1?" + q)["results"]
            out += d
            if len(d) < 200:
                break
        save_json(out, "catalog_all.json")
    socrata_all("axxr-vais", "recs_approp_2026.json")        # 2026 Budget Recommendations - Appropriations
    socrata_all("t59y-fr3k", "approp_2025.json")             # 2025 ordinance appropriations
    socrata_all("e5cq-t86i", "revenue_2025.json")            # 2025 ordinance revenue
    socrata_all("7x7d-3zgj", "budget_transfers_2026.json")   # Budget Transfer Report Source Data
    socrata_all("9v3e-pcjs", "workforce_vacancies.json")     # Workforce Vacancies (monthly)
    socrata_all("9yp3-9pdz", "arpa_summary.json")            # ARPA Road to Recovery grants summary


# -------------------------------------------------------------------- obm
OBM_PDFS = {
    "ord_2026.pdf": "supp_info/2026Budget/FY2026%20Annual%20Appropriation%20Ordinance.pdf",
    "tech_amend_2026.pdf": "supp_info/2026Budget/Combined%20Technical%20Amendments.pdf",
    "amend_pkg_rd2_2026.pdf": "supp_info/2026Budget/Combined_Amendment_package_rd2.pdf",
    "budget_floors_2026.pdf": "supp_info/2026Budget/Calculated%20Budget%20Floors.pdf",
    "midyear_report_2026.pdf": "supp_info/2026Budget/2026Mid-YearBudgetReport.pdf",
    "midyear_presentation_2026.pdf": "supp_info/Misc/2026%20Mid-Year%20Budget%20Presentation.pdf",
    "budget_execution_apr2026.pdf": "supp_info/Misc/FY2026_Budget_Execution_Presentation.pdf",
    "forecast_2027.pdf": "2027_Budget/Budget_Forecast/2027_Chicago_Budget_Forecast.pdf",
    "qbr_q1_2026.pdf": "supp_info/Quarterly%20Budget%20Report/2026/2026_Q1_QBR_City-of-Chicago.pdf",
    "transfer_q1_2026.pdf": "supp_info/Quarterly%20Budget%20Report/QuartelyTransferReports/Q1%202026%20Quarterly%20Transfer%20Report.pdf",
    "transfer_q2_2026.pdf": "supp_info/Quarterly%20Budget%20Report/QuartelyTransferReports/Q2%202026%20Quarterly%20Transfer%20Report.pdf",
    "menu_q1_2026.pdf": "supp_info/CIP_Archive/Aldermanic%20Menu/2026%20Q1%20Menu%20Report.pdf",
    "ord_2025.pdf": "supp_info/2025Budget/2025_Ordinance_Book_webVersion.pdf",
    "overview_2025.pdf": "supp_info/2025Budget/2025-Overview-DIGITAL.pdf",
}


def g_obm():
    print("obm")
    for name, rel in OBM_PDFS.items():
        pdf = save(f"{OBM}/{rel}", name)
        if pdf:
            pdf_to_text(pdf)


# ------------------------------------------------------------------- elms
def elms(path_, **q):
    u = "https://api.chicityclerkelms.chicago.gov/" + path_ + ("?" + urllib.parse.urlencode(q) if q else "")
    return get_json(u, 90)


def g_elms():
    """City Clerk eLMS: open JSON API, no key. search= is free text, filter= is OData-ish
    (e.g. fileYear eq 2026) and cannot be combined with search=."""
    print("elms")
    if not os.path.exists(path("elms_budget_search.json")):
        seen = {}
        for term in ["Appropriation", "Annual Appropriation Ordinance", "budget amendment",
                     "Aldermanic Menu", "Mid-Year"]:
            skip = 0
            while True:
                d = elms("matter", search=term, top=100, skip=skip)
                for m in d["data"]:
                    seen[m["matterId"]] = m
                skip += 100
                if skip >= d["meta"]["count"] or skip >= 1500:
                    break
        save_json(list(seen.values()), "elms_budget_search.json")
    # Download every 2026 appropriation-amendment attachment (PDF).
    meta_file = path("elms_2026_approp_meta.json")
    if not os.path.exists(meta_file):
        rows = [m for m in json.load(open(path("elms_budget_search.json")))
                if m["fileYear"] == 2026 and "Appropriation" in (m["title"] or "")
                and m["status"].startswith("90")]
        meta = []
        for m in sorted(rows, key=lambda m: m["introductionDate"]):
            full = elms("matter/" + m["matterId"])
            for a in full["attachments"]:
                fn = a["fileName"]
                if not fn.lower().endswith(".pdf"):
                    continue
                dest = path("elms_pdfs", re.sub(r"[^A-Za-z0-9_.-]", "_", fn))
                if not os.path.exists(dest):
                    try:
                        open(dest, "wb").write(get_bytes(a["path"], 90))
                    except (urllib.error.URLError, OSError) as e:
                        print("  FAIL", fn, e)
                        continue
                meta.append([m["recordNumber"], m["introductionDate"][:10], full["finalActionDate"],
                             m["title"], fn, dest])
        save_json(meta, "elms_2026_approp_meta.json")
    d = os.path.dirname(path("elms_pdfs", "x"))
    for f in sorted(os.listdir(d)):
        if f.endswith(".pdf") and ("Ordinance" in f or "Exhibit" in f or "925" in f):
            pdf_to_text(os.path.join(d, f))


# -------------------------------------------------------------------- cps
CPS_API = "https://api.cps.edu/procurement"


def g_cps():
    """CPS Department of Procurement app (schoolinfo.cps.edu/ProcurementWeb) is an Angular
    SPA over a public JSON API. The bundle ships a dev URL (dev.api.cps.edu, unreachable),
    but the same routes answer on api.cps.edu."""
    print("cps procurement")
    years = get_json(f"{CPS_API}/Supplier/GetFiscalYears")
    save_json(years, "cps_proc/fiscal_years.json")
    for y in years:
        dest = path("cps_proc", f"supplier_payments_{y}.json")
        if not os.path.exists(dest):
            open(dest, "wb").write(get_bytes(f"{CPS_API}/Supplier/GetSupplierPayments?reportyear={y}", 180))
            print(f"  supplier_payments_{y}")
    for y in [x["FISCAL_YEAR"] for x in get_json(f"{CPS_API}/contracthistory/GetFiscalYears")]:
        for ep, tag in (("GetContractAwards", "contract_awards"), ("GetPooledContractAwards", "pooled_awards")):
            dest = path("cps_proc", f"{tag}_{y}.json")
            if not os.path.exists(dest):
                open(dest, "wb").write(get_bytes(f"{CPS_API}/contracthistory/{ep}?reportyear={y}", 120))


# ------------------------------------------------------------------ parks
def g_parks():
    print("park district")
    # Bonfire public contracts: vendor, contract name, dates, NO dollar amounts.
    save("https://chicagoparkdistrict.bonfirehub.com/PublicPortal/getPublicContractsSectionData",
         "bonfire_contracts.json")
    # Board of Commissioners legislation (Legistar Web API, open). Matter metadata has no $.
    if not os.path.exists(path("cpd_legistar_matters_2025on.json")):
        q = urllib.parse.urlencode({"$filter": "MatterIntroDate ge datetime'2025-01-01'", "$top": 1000})
        save_json(get_json("https://webapi.legistar.com/v1/chicagoparkdistrict/matters?" + q),
                  "cpd_legistar_matters_2025on.json")


# ------------------------------------------------------------------- cook
def g_cook():
    print("cook county")
    save("https://www.cookcountyclerkil.gov/sites/default/files/2026-04/2024-agency-rate-report.xlsx",
         "agency_rate_2024.xlsx")


GROUPS = {"socrata": g_socrata, "obm": g_obm, "elms": g_elms, "cps": g_cps,
          "parks": g_parks, "cook": g_cook}

if __name__ == "__main__":
    only = None
    if "--only" in sys.argv:
        only = sys.argv[sys.argv.index("--only") + 1].split(",")
    for name, fn in GROUPS.items():
        if only is None or name in only:
            fn()
    print("done ->", os.path.abspath(RAW))
