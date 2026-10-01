"""Where does the City's FY2026 money come from? (revenue side)

Source: 2026 Budget Ordinance - Revenue, data.cityofchicago.org dataset nydj-5nax
(found with the Socrata catalog API: https://api.us.socrata.com/api/catalog/v1?domains=data.cityofchicago.org&q=revenue).
It covers LOCAL funds only (not the ~$3.87B of grants).

Usage: python3 scripts/context_revenue.py  -> data/context_revenue_2026.json
"""
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(__file__))
from context_common import fetch, load_json, money, read_text, socrata, write_json  # noqa: E402

DATASET = "nydj-5nax"
PENSION_FUNDS = ("Municipal Employees", "Laborers", "Policemen", "Firemen")


def bucket(r):
    """Plain-English bucket for one revenue row. Order matters."""
    src = r["revenue_source"]
    fund = r["fund_name"]
    grp = r.get("revenue_group_type")
    cat = r.get("revenue_category")
    if "Pension Allocation" in src or "Advance Pension Payment" in src or "Pension Residual Allocation" in src:
        return "Moved between city funds (pension payments)", True
    if src in ("Corporate Fund Subsidy", "Transfers In") or cat == "Internal Service Earnings":
        return "Moved between city funds (reimbursements and subsidies)", True
    if src in ("Property Tax Levy (Net Abatement)", "Library Property Tax Levy"):
        return "Property tax (City's share)", False
    if "Sales Tax Securitization" in src or "Chicago Sales Tax" in src:
        return "Sales tax (City's share)", False
    if fund in ("Water Fund", "Sewer Fund") and ("Rates" in src):
        return "Water and sewer bills", False
    if src == "Water and Sewer Utility Tax":
        return "Water and sewer bills", False
    if fund in ("Chicago O'Hare Airport Fund", "Chicago Midway Airport Fund"):
        return "Airport fees and airline charges", False
    if grp == "Local Tax":
        return "Other City taxes (sales, utility, hotel, parking, amusement, etc.)", False
    if grp == "Intergovernmental Revenue":
        return "State money (income tax share, replacement tax)", False
    if "Proceeds" in src or grp == "Proceeds and Transfers In" or src == "Proceeds of Debt":
        return "Borrowing and one-time transfers", False
    if grp == "Local Non-Tax Revenue":
        return "Fines, fees, permits, licenses, charges", False
    if "Tax" in src or "Surcharge" in src:
        return "Other City taxes (sales, utility, hotel, parking, amusement, etc.)", False
    return "Other dedicated-fund revenue", False


def main():
    rows = socrata(DATASET, {"$limit": 50000}, cache="revenue_2026.json")
    total = sum(money(r["estimated_revenue"]) for r in rows)

    by_fund = defaultdict(float)
    by_bucket = defaultdict(float)
    by_bucket_interfund = {}
    corp_by_group = defaultdict(float)
    corp_by_cat = defaultdict(float)
    corp_rows = []
    for r in rows:
        v = money(r["estimated_revenue"])
        by_fund[r["fund_name"]] += v
        b, inter = bucket(r)
        by_bucket[b] += v
        by_bucket_interfund[b] = inter
        if r["fund_name"] == "Corporate Fund":
            corp_by_group[r.get("revenue_group_type")] += v
            corp_by_cat[(r.get("revenue_group_type"), r.get("revenue_category"), r["revenue_source"])] += v

    corp_total = by_fund["Corporate Fund"]
    prop_rows = [r for r in rows if r["revenue_source"] in ("Property Tax Levy (Net Abatement)", "Library Property Tax Levy")]
    prop_tax = sum(money(r["estimated_revenue"]) for r in prop_rows)
    prop_by_use = defaultdict(float)
    for r in prop_rows:
        prop_by_use[r["fund_name"]] += money(r["estimated_revenue"])

    # Appropriation totals for context (same Local scope)
    approps = json.load(open(os.path.join(os.path.dirname(__file__), "..", "raw", "city_appropriations_2026.json")))
    local_app = sum(float(a["_ordinance_amount_"]) for a in approps if a["fund_type"] == "LOCAL")
    grant_app = sum(float(a["_ordinance_amount_"]) for a in approps if a["fund_type"] == "GRANTS")

    interfund_total = sum(v for k, v in by_bucket.items() if by_bucket_interfund[k])
    out = {
        "source": "https://data.cityofchicago.org/resource/%s.json" % DATASET,
        "source_page": "https://data.cityofchicago.org/d/%s" % DATASET,
        "catalog_search": "https://api.us.socrata.com/api/catalog/v1?domains=data.cityofchicago.org&q=revenue",
        "scope": "LOCAL funds only. Grants (federal/state/other, ~$%.2fB in the appropriations) are not in this dataset." % (grant_app / 1e9),
        "total_local_revenue": total,
        "total_local_appropriations": local_app,
        "gap_revenue_minus_appropriations": total - local_app,
        "note_gap": "Revenue estimate and appropriations differ by this amount. Do not force them to match. Appropriations include prior-year balances, and revenue includes some transfers.",
        "corporate_fund_total": corp_total,
        "bucket_totals_all_local_funds": {k: v for k, v in sorted(by_bucket.items(), key=lambda x: -x[1])},
        "bucket_is_interfund_transfer": by_bucket_interfund,
        "interfund_transfer_total": interfund_total,
        "total_excluding_interfund": total - interfund_total,
        "property_tax_levy_net_abatement_total": prop_tax,
        "property_tax_levy_by_fund": dict(prop_by_use),
        "property_tax_levy_note": "Budget Overview p.59: base levy $1.8B funds $2.7B of pensions and $534.7M of debt service and library. https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf",
        "corporate_fund_by_group": {str(k): v for k, v in sorted(corp_by_group.items(), key=lambda x: -x[1])},
        "corporate_fund_top_sources": [
            {"group": k[0], "category": k[1], "source": k[2], "amount": v,
             "share_of_corporate_fund": v / corp_total}
            for k, v in sorted(corp_by_cat.items(), key=lambda x: -x[1])[:25]
        ],
        "by_fund": {k: v for k, v in sorted(by_fund.items(), key=lambda x: -x[1])},
        "caveats": [
            "Interfund transfers (pension allocations, reimbursements) are counted in the dataset total and are the same money counted twice. See research/finance_general.md ($1.80B).",
            "Corporate Fund 'Sales Tax Securitization Corporation Residual' is the City's share of the Chicago sales tax after bond payments (see Budget Overview).",
            "Property tax shown is the City levy net of abatement, not the whole property tax bill. CPS, Parks, County, etc. are separate governments. See data/context_resident_2026.json for the tax bill split.",
        ],
    }
    write_json("context_revenue_2026.json", out)
    print("total %.0f  corp %.0f  prop tax %.0f" % (total, corp_total, prop_tax))


if __name__ == "__main__":
    main()
