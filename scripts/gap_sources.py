"""Quick, read-only verification of the sources listed in research/new_sources.md.

No downloads are saved. Socrata checks use server-side aggregates, URL checks read only the
status line and size. Usage: python3 scripts/gap_sources.py
Needs: python3 stdlib only. Network access to data.cityofchicago.org, chicago.gov, cps.edu.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

UA = {"User-Agent": "Mozilla/5.0"}


def soql(dataset, **params):
    url = f"https://data.cityofchicago.org/resource/{dataset}.json?" + urllib.parse.urlencode(params)
    return json.load(urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=90))


def head(url):
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40)
        return r.status, r.headers.get("Content-Length") or "?"
    except urllib.error.HTTPError as e:
        return e.code, "-"
    except Exception as e:  # network trouble
        return "ERR", str(e)[:40]


def main():
    print("== Socrata counts (and sums where there is a dollar field)")
    for ds, field in [("9v3e-pcjs", None), ("7tg5-i782", "amount_expended"), ("m9g9-cj96", None),
                      ("iekz-rtng", "incentive_amount"), ("etqr-sz5x", "incentive_amount"),
                      ("rym7-49n8", "incentive_amount"), ("v7gx-e2v6", "incentive_amount"),
                      ("syk7-tkvr", "incentive_amount"), ("j7ew-b73u", "incentive_amount"),
                      ("cnna-nmxx", "incentive_amount"), ("6br9-quuz", "imposed_fine"),
                      ("tnbd-5zz7", None), ("kc9i-wq85", None), ("yqn4-3th2", None)]:
        sel = "count(*) as n" + (f",sum({field}) as s" if field else "")
        print(ds, soql(ds, **{"$select": sel})[0])

    print("== Budget ordinance history row counts")
    ids = {2011: "drv3-jzqp", 2012: "8ix6-nb7q", 2013: "b24i-nwag", 2014: "ub6s-xy6e", 2015: "qnek-cfpp",
           2016: "36y7-5nnf", 2017: "7jem-9wyw", 2018: "6g7p-xnsy", 2019: "h9rt-tsn7", 2020: "fyin-2vyd",
           2021: "6tbx-h7y2", 2022: "2cr6-8u6w", 2023: "xbjh-7zvh", 2024: "x394-e874", 2025: "t59y-fr3k"}
    for y, ds in ids.items():
        print(y, ds, soql(ds, **{"$select": "count(*) as n"})[0]["n"])

    print("== ARPA ledger by cost center x month, share of rows under $1M")
    rows = soql("7tg5-i782", **{"$select": "cost_center,date_trunc_ym(expense_date) as m,sum(amount_expended) as s",
                                "$group": "cost_center,m", "$limit": "50000"})
    vals = [float(r["s"]) for r in rows]
    small = [v for v in vals if v < 1e6]
    print(len(vals), "groups,", len(small), "under $1M holding", round(sum(small) / 1e6, 1), "M")

    print("== URL status")
    urls = [
        "https://www.cps.edu/about/finance/budget/budget-2027/",
        "https://www.cps.edu/globalassets/cps-pages/about-cps/finance/budget/budget-2027/docs/fy2027-budget-book-final-approved-2.2.pdf",
        "https://www.cps.edu/globalassets/cps-global-media/banner-images/annual-financial-report/fy25-acfr-final.pdf",
        "https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2027",
        "https://api.cps.edu/procurement/contracthistory/GetPooledContractAwards?reportyear=2026",
        "https://www.chicago.gov/content/dam/city/depts/obm/2027_Operations/Monthly_Revenue_Report/Monthly_Revenue_Report_August_2026.pdf",
        "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/Calculated%20Budget%20Floors.pdf",
        "https://legistar2.granicus.com/chicagoparkdistrict/attachments/66541197-6851-4854-8a35-68b0350e93f8.pdf",
        "https://webapi.legistar.com/v1/chicagoparkdistrict/bodies",
        "https://www.chicagoparkdistrict.com/participatory-budgeting",
        "https://www.cookcountyclerkil.gov/sites/default/files/2026-04/2024-agency-rate-report.xlsx",
        "https://www.cookcountyclerkil.gov/sites/default/files/2026-08/2025-agency-rate-report-tables-updated.xlsx",
        "https://public.tableau.com/app/profile/obm.data.analytics/viz/Mid-YearReport-DataDirectory/DataDirectory-Mid-YearReport",
    ]
    for u in urls:
        print(head(u), u)


if __name__ == "__main__":
    main()
