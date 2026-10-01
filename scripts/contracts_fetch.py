"""Download the public Chicago Open Data datasets used to link budget lines to vendors.

Writes CSVs into raw/contracts/ (gitignored). Nothing is hand typed: every file is a
straight export from the Socrata API on data.cityofchicago.org.

Usage: python3 scripts/contracts_fetch.py [--force]

Datasets (id: what it is):
  rsxa-ify5  Contracts and modifications (one row per revision)
  s4vu-giwb  Payments (every check, 1996 to present, row level since 2022)
  ijrh-ktm6  TIF annual report, vendors paid more than $10,000
  72uz-ikdv  TIF annual report, projects
  mex4-ppfc  TIF funded RDA and IGA projects
  jmw7-ijg5  DFSS delegate agency sites (2015, stale, list of agencies only)
  5wd9-d675  List of contractors doing business with the city (2018, stale)
  y93d-d9e3  Debarred firms and individuals
  iyu8-jkf8  Mid-year grants report (budget/expended by grant, 789 rows)
  g5h3-jkgt  Employee reimbursements
  xzkq-xp2w  Current employee names, salaries, titles
  gxzc-43gg  Vendor payments for the migrant (New Arrivals) response, 2022-2025
  dawh-m56b  Payroll costing (4.9M rows). Too big to export, we pull a 2025 aggregate instead (below)
"""
import os
import sys
import time
import urllib.parse
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "..", "raw", "contracts")
BASE = "https://data.cityofchicago.org/resource/{}.csv"

DATASETS = {
    "contracts_all.csv": ("rsxa-ify5", 1_000_000),
    "payments_all.csv": ("s4vu-giwb", 2_000_000),
    "ijrh-ktm6.csv": ("ijrh-ktm6", 100_000),
    "72uz-ikdv.csv": ("72uz-ikdv", 100_000),
    "mex4-ppfc.csv": ("mex4-ppfc", 100_000),
    "jmw7-ijg5.csv": ("jmw7-ijg5", 100_000),
    "5wd9-d675.csv": ("5wd9-d675", 100_000),
    "y93d-d9e3.csv": ("y93d-d9e3", 100_000),
    "midyear_grants.csv": ("iyu8-jkf8", 100_000),
    "employee_reimb.csv": ("g5h3-jkgt", 200_000),
    "salaries_current.csv": ("xzkq-xp2w", 100_000),
    "new_arrivals.csv": ("gxzc-43gg", 100_000),
}


def fetch(name, dsid, limit, force):
    path = os.path.join(RAW, name)
    if os.path.exists(path) and os.path.getsize(path) > 200 and not force:
        print("skip (exists)", name)
        return
    q = urllib.parse.urlencode({"$limit": limit, "$order": ":id"})
    url = BASE.format(dsid) + "?" + q
    for attempt in range(5):
        try:
            with urllib.request.urlopen(url, timeout=600) as r, open(path, "wb") as f:
                f.write(r.read())
            n = sum(1 for _ in open(path, "rb")) - 1
            print("ok", name, n, "rows")
            return
        except Exception as e:  # Socrata sometimes returns 503, just retry
            print("retry", name, attempt, e)
            time.sleep(5 * (attempt + 1))
    raise SystemExit("failed " + name)


PAYROLL_URL = "https://data.cityofchicago.org/resource/dawh-m56b.csv"


def fetch_payroll_2025(force):
    """2025 payroll costing aggregated by department, appropriation and pay element (OT lives here)."""
    path = os.path.join(RAW, "payroll_costing_2025.csv")
    if os.path.exists(path) and os.path.getsize(path) > 200 and not force:
        print("skip (exists)", path)
        return
    q = urllib.parse.urlencode({
        "$select": "department_code,appropriation_code,pay_element,sum(amount) as amount,count(*) as n",
        "$where": "payroll_year=2025", "$group": "department_code,appropriation_code,pay_element", "$limit": 50000})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(PAYROLL_URL + "?" + q, timeout=900) as r, open(path, "wb") as f:
                f.write(r.read())
            print("ok payroll_costing_2025.csv")
            return
        except Exception as e:
            print("retry payroll", attempt, e)
            time.sleep(10 * (attempt + 1))
    raise SystemExit("failed payroll aggregate")


def main():
    force = "--force" in sys.argv
    os.makedirs(RAW, exist_ok=True)
    for name, spec in DATASETS.items():
        if spec is None:
            continue
        fetch(name, spec[0], spec[1], force)
    fetch_payroll_2025(force)


if __name__ == "__main__":
    main()
