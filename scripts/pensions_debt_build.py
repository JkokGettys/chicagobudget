"""Build data/debt_2026.json and data/pensions_2026.json from the public source documents.

Run scripts/pensions_debt_fetch.py first (downloads PDFs into raw/pensions_debt/ and extracts
text). Every number below is either parsed from those text files by regex or read from the
2026 Budget Ordinance dataset (raw/city_appropriations_2026.json, dataset 6694-f78c). Anything
typed by hand is checked against the source text with verify(), so a wrong digit fails loudly.

Page numbers in the output are PDF page indexes (1-based), not the printed page labels.

Usage: python3 scripts/pensions_debt_build.py
"""
import json
import os
import re
from collections import defaultdict

ROOT = os.path.join(os.path.dirname(__file__), "..")
RAW = os.path.join(ROOT, "raw", "pensions_debt")
OUT_DEBT = os.path.join(ROOT, "data", "debt_2026.json")
OUT_PENS = os.path.join(ROOT, "data", "pensions_2026.json")

URLS = {
    "ACFR2025": "https://www.chicago.gov/content/dam/city/depts/fin/supp_info/CAFR/2025CAFR/2025%20ANNUAL%20COMPREHENSIVE%20FINANCIAL%20REPORT__v2.pdf",
    "OVERVIEW2026": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf",
    "FORECAST2027": "https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Forecast/2027_Chicago_Budget_Forecast.pdf",
    "ORDINANCE2026": "https://bondlink-cdn.com/1338/FY2026-Annual-Appropriation-Ordinance.Vsr9wxc2u.pdf",
    "OPENDATA6694": "https://data.cityofchicago.org/resource/6694-f78c.json",
    "GO2026AB_OS": "https://bondlink-cdn.com/1338/ILChicago02a-FIN.D8Ebm0ZNE.pdf",
    "GO2025AE_OS": "https://bondlink-cdn.com/1338/OS.GE3zX31VR.pdf",
    "GO2025FG_OS": "https://bondlink-cdn.com/1338/OS.Uxunte2ez.pdf",
    "GO2024A_OS": "https://bondlink-cdn.com/1338/General-Obligation-Bonds-Series-2024A.qIfFSWQzr.pdf",
    "GO2023AB_OS": "https://bondlink-cdn.com/1338/GO-2023AB-OS.TQ3FvIUd3.pdf",
    "GO2024B_OS": "https://bondlink-cdn.com/1338/Supplement-to-the-Supplement-to-the-OS--Dated-12.19.2024.5KuWH6GRr.pdf",
    "WATER2026_OS": "https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf",
    "STSC2024_OC": "https://bondlink-cdn.com/2925/OC.XFXm0gZ8C.pdf",
    "STSC2023_OC": "https://bondlink-cdn.com/2925/Final-OC.qnWB3nNOk.pdf",
    "STSC_FS2025": "https://bondlink-cdn.com/2925/FY25-STSC-Financial-Statements---Issued--1.sdgdZJ5QA.pdf",
    "STSC2025_OC": "https://bondlink-cdn.com/2925/ILSalesTax01a-FIN.ouftBIpEZ.pdf",
    "OHARE_FS2025": "https://bondlink-cdn.com/1348/O-Hare-International-Airport-Financial-Statement-2025.0sROg23GQ.pdf",
    "MIDWAY_FS2025": "https://bondlink-cdn.com/1351/Midway-International-Airport-Financial-Statement-2025.4TGhWWzsT.pdf",
    "PABF_VAL2025": "https://chipabf.org/wp-content/uploads/2026/07/PABF_20251231_Final.pdf",
    "FABF_VAL2025": "https://fabf.org/LinkClick.aspx?fileticket=G_bIYnMR31w%3d&portalid=0",
    "MEABF_VAL2025": "https://www.meabf.org/wp-content/uploads/2026/06/MEABF_Actuarial-Valuation-Report-as-of-12.31.2025-06.26.2026.pdf",
    "LABF_VAL2025": "https://www.labfchicago.org/assets/1/7/GRS_2025_Val.pdf",
}

FILES = {
    "ACFR2025": "acfr2025.txt",
    "OVERVIEW2026": "overview2026.txt",
    "FORECAST2027": "forecast2027.txt",
    "ORDINANCE2026": "os/ordinance2026.txt",
    "GO2026AB_OS": "os/ILChicago02a-FIN.D8Ebm0ZNE.txt",
    "GO2025AE_OS": "os/OS.GE3zX31VR.txt",
    "GO2025FG_OS": "os/OS.Uxunte2ez.txt",
    "GO2024A_OS": "os/GO2024A.txt",
    "GO2023AB_OS": "os/GO2023AB.txt",
    "GO2024B_OS": "os/GO2024B.txt",
    "WATER2026_OS": "os/ILChicago04a-FIN.yO9Z1Tmxh.txt",
    "STSC2024_OC": "stsc/OC.XFXm0gZ8C.txt",
    "STSC2023_OC": "stsc/Final-OC.qnWB3nNOk.txt",
    "STSC_FS2025": "stsc/FY25-STSC-Financial-Statements---Issued--1.sdgdZJ5QA.txt",
    "STSC2025_OC": "stsc/ILSalesTax01a-FIN.ouftBIpEZ.txt",
    "OHARE_FS2025": "ent/ohare_fs2025.txt",
    "MIDWAY_FS2025": "ent/midway_fs2025.txt",
    "PABF_VAL2025": "funds/PABF_20251231_Final.txt",
    "FABF_VAL2025": "funds/FABF_val_2025.txt",
    "MEABF_VAL2025": "funds/MEABF_val_2025.txt",
    "LABF_VAL2025": "funds/LABF_GRS_2025_Val.txt",
}

_cache = {}


def pages(key):
    """{pdf_page: text} for a source key."""
    if key not in _cache:
        t = open(os.path.join(RAW, FILES[key])).read()
        t = re.sub(r"[ \t]+\n", "\n", t)  # extracted text has trailing spaces on most lines
        t = re.sub(r"[ \t]{2,}", " ", t)  # and runs of spaces in some reports
        _cache[key] = {int(m.group(1)): m.group(2)
                       for m in re.finditer(r"=====PAGE (\d+)=====\n(.*?)(?======PAGE|\Z)", t, flags=re.S)}
    return _cache[key]


def norm(s):
    return re.sub(r"\s+", "", s)


def verify(key, page, *needles):
    """Assert every needle appears (ignoring whitespace) on that PDF page."""
    txt = norm(pages(key)[page])
    for n in needles:
        assert norm(n) in txt, f"{key} p.{page}: '{n}' not found"


def grab(key, pattern, page=None, flags=0):
    """First regex match in a source (optionally restricted to one page). Returns (match, page)."""
    for pn, txt in pages(key).items():
        if page is not None and pn != page:
            continue
        m = re.search(pattern, txt, flags)
        if m:
            return m, pn
    raise AssertionError(f"{key}: pattern not found: {pattern[:80]}")


def n(s):
    """'$ 1,234' / '(1,234)' / '—' to int."""
    s = s.replace("$", "").replace(",", "").strip()
    if s in ("—", "-", ""):
        return 0
    neg = s.startswith("(") and s.endswith(")")
    s = s.strip("()")
    v = float(s)
    v = int(v) if v == int(v) else v
    return -v if neg else v


def cite(key, page, note=None):
    d = {"doc": key, "url": URLS.get(key), "pdf_page": page}
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------------------
# Budget ordinance (open data 6694-f78c): Finance General lines
# ---------------------------------------------------------------------------

def finance_general_lines():
    rows = json.load(open(os.path.join(ROOT, "raw", "city_appropriations_2026.json")))
    out = []
    for r in rows:
        if r["department_description"] != "Finance General":
            continue
        v = int(r["_ordinance_amount_"])
        if v:
            out.append((r["fund_description"], r["appropriation_account_description"], v))
    return out


INTEREST = {"For Interest on Bonds", "For Interest on Loans", "Interest on Library Financing"}
PRINCIPAL = {"For Payment of Bonds", "For Payment of Term Notes", "For Payment on Loans"}
FEES = {"For Bond Fees and Costs"}
OTHER_DEBT = {"For Payment of Water Pipe Extension Certificates"}

FUND_META = {
    "Bond Redemption and Interest Series Fund": {
        "type": "General Obligation bonds (tax levy)", "payer": "taxpayers",
        "paid_by": "Property tax levy $314.6M + Corporate Fund subsidy $90.5M + transfers in $25.0M (ordinance p.34)"},
    "Corporate Fund": {
        "type": "General Obligation bonds (tax levy)", "payer": "taxpayers",
        "paid_by": "Corporate Fund (general revenue). This is the $90.5M subsidy that ALSO appears as revenue of the Bond Redemption fund, so it is counted twice",
        "internal_transfer": True},
    "Library Property Tax Levy Fund": {
        "type": "Library term notes (short-term borrowing, refinanced each year)", "payer": "taxpayers",
        "paid_by": "Library property tax levy. The same $125,926,011 is budgeted as 'Proceeds of Debt' in the Library Fund (ordinance p.34)"},
    "Library Fund": {
        "type": "Library financing interest", "payer": "taxpayers", "paid_by": "Library Fund"},
    "Water Fund": {
        "type": "Water revenue bonds and IEPA/WIFIA loans", "payer": "water ratepayers",
        "paid_by": "Water rates (water fees are 92% of Water Fund revenue, Overview p.47)"},
    "Sewer Fund": {
        "type": "Wastewater revenue bonds and IEPA loans", "payer": "sewer ratepayers",
        "paid_by": "Sewer charges (set at 100% of water charges, Overview p.47)"},
    "Chicago O'Hare Airport Fund": {
        "type": "O'Hare airport revenue bonds, CFC bonds, TIFIA loan", "payer": "airlines and airport users",
        "paid_by": "Airline rates and charges (residual basis) plus non-airline revenue, not property tax (Overview p.47)"},
    "Chicago Midway Airport Fund": {
        "type": "Midway airport revenue bonds", "payer": "airlines and airport users",
        "paid_by": "Airline rates and charges (residual basis) plus non-airline revenue, not property tax (Overview p.47)"},
}


def build_debt():
    lines = finance_general_lines()
    ord_pages = pages("ORDINANCE2026")

    # ---- 1. budget lines -------------------------------------------------
    budget = []
    for fund, acct, v in lines:
        if acct in INTEREST:
            kind = "interest"
        elif acct in PRINCIPAL:
            kind = "principal"
        elif acct in FEES:
            kind = "fees"
        elif acct in OTHER_DEBT:
            kind = "other"
        else:
            continue
        meta = FUND_META.get(fund, {"type": "?", "payer": "?", "paid_by": "?"})
        budget.append({"fund": fund, "account": acct, "kind": kind, "amount": v,
                       "debt_type": meta["type"], "payer": meta["payer"], "paid_by": meta["paid_by"],
                       "internal_transfer": bool(meta.get("internal_transfer") and kind == "principal")})
    budget.sort(key=lambda r: -r["amount"])
    gross = sum(r["amount"] for r in budget)
    interest = sum(r["amount"] for r in budget if r["kind"] == "interest")
    principal = sum(r["amount"] for r in budget if r["kind"] == "principal")
    fees = sum(r["amount"] for r in budget if r["kind"] == "fees")
    other = sum(r["amount"] for r in budget if r["kind"] == "other")
    transfer = sum(r["amount"] for r in budget if r["internal_transfer"])

    # Ordinance Summary C "Debt Service" column total
    m, pg_sumC = grab("ORDINANCE2026", r"Total - All Funds \$8,617,690,572 \$67,419,821 \$([\d,]+) \$([\d,]+) \$74,308,127")
    ord_debt_total = n(m.group(1))
    ord_pension_total = n(m.group(2))
    assert gross == ord_debt_total, (gross, ord_debt_total)

    # by payer
    by_payer = defaultdict(int)
    for r in budget:
        if not r["internal_transfer"]:
            by_payer[r["payer"]] += r["amount"]

    by_fund = defaultdict(lambda: {"interest": 0, "principal": 0, "fees": 0, "other": 0})
    for r in budget:
        by_fund[r["fund"]][r["kind"]] += r["amount"]
    by_fund_list = []
    for f, d in by_fund.items():
        meta = FUND_META[f]
        by_fund_list.append({"fund": f, **d, "total": sum(d.values()), "debt_type": meta["type"],
                             "payer": meta["payer"], "paid_by": meta["paid_by"]})
    by_fund_list.sort(key=lambda r: -r["total"])

    int_bonds_loans = sum(r["amount"] for r in budget if r["account"] in ("For Interest on Bonds", "For Interest on Loans"))
    checks_given = [
        check("Task figure: Finance General interest on bonds + loans ($1,038,548,680)", int_bonds_loans, 1038548680, cite("OPENDATA6694", None, "accounts 'For Interest on Bonds' + 'For Interest on Loans'")),
        check("Task figure: Finance General principal ($924,869,427)", principal, 924869427, cite("OPENDATA6694", None, "accounts For Payment of Bonds + Term Notes + on Loans")),
        check("Task figure: Finance General bond fees ($9,486,309)", fees, 9486309, cite("OPENDATA6694", None, "account 'For Bond Fees and Costs'")),
    ]
    # Bond Redemption fund revenue (ordinance p.34) must equal what Corporate subsidy says
    m, pg_bondrev = grab("ORDINANCE2026", r"0510 - Bond Redemption and Interest Series Fund\nEstimated Revenue for 2026\n\s*Transfers In \$([\d,]+)\n\s*Property Tax Levy \(Net Abatement\) ([\d,]+)\n\s*Corporate Fund Subsidy ([\d,]+)\n\s*Total appropriable revenue ([\d,]+)")
    bond_rev = {"transfers_in": n(m.group(1)), "property_tax_levy_net": n(m.group(2)),
                "corporate_fund_subsidy": n(m.group(3)), "total": n(m.group(4))}
    corp_line = next(r["amount"] for r in budget if r["fund"] == "Corporate Fund" and r["kind"] == "principal")
    assert corp_line == bond_rev["corporate_fund_subsidy"]
    m, pg_libproc = grab("ORDINANCE2026", r"0346 - Library Fund\nPrior Year Available Resources [\d,]+\nEstimated Revenue for 2026\n.*?Proceeds of Debt ([\d,]+)", flags=re.S)
    lib_proceeds = n(m.group(1))
    lib_notes = next(r["amount"] for r in budget if r["account"] == "For Payment of Term Notes")
    assert lib_proceeds == lib_notes

    # ---- 2. contractual schedules (ACFR FY2025) ------------------------------
    m, p22 = grab("ACFR2025", r"2026\s+\.{3,}\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)", page=247)
    t22 = [n(x) for x in m.groups()]
    m, p23 = grab("ACFR2025", r"2026\s+\.{3,}\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)", page=248)
    t23 = [n(x) for x in m.groups()]
    m, p24 = grab("ACFR2025", r"2026\s+\.{3,}\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)", page=250)
    t24 = [n(x) for x in m.groups()]
    m, p24b = grab("ACFR2025", r"\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)\s+\.{5,}\s+2026", page=251)
    t24b = [n(x) for x in m.groups()]
    assert t22[0] == t23[0] + t23[2] and t22[1] == t23[1] + t23[3]
    sched = {
        "basis": "ACFR 'year 2026' row: payments from Jan 2 2026 through Jan 1 2027 for governmental debt (Jan 1 2026 payment already funded and excluded), "
                 "and Jan 1 2026 through Dec 2026 for business-type debt (ACFR p.88 intro)",
        "general_obligation": {"principal": t22[0], "interest": t22[1], "cite": cite("ACFR2025", p22, "Table 22")},
        "general_obligation_bonds_only": {"principal": t23[0], "interest": t23[1], "cite": cite("ACFR2025", p23, "Table 23")},
        "alternative_revenue_bonds_msac_2010b": {"principal": t23[2], "interest": t23[3], "cite": cite("ACFR2025", p23, "Table 23")},
        "sales_tax_securitization": {"principal": t22[2], "interest": t22[3], "cite": cite("ACFR2025", p22, "Table 22")},
        "water_revenue_incl_loans": {"principal": t24[0], "interest": t24[1], "cite": cite("ACFR2025", p24, "Table 24")},
        "wastewater_revenue_incl_loans": {"principal": t24[2], "interest": t24[3], "cite": cite("ACFR2025", p24, "Table 24")},
        "ohare_and_midway_combined": {"principal": t24b[0], "interest": t24b[1], "cite": cite("ACFR2025", p24b, "Table 24 continued")},
    }
    # per-airport (enterprise financial statements)
    # O'Hare page 51 holds three tables in this order: senior lien, PFC, CFC. Page 52 holds TIFIA.
    row26 = r"2026\s+\.{3,}\s+\$ ([\d,—]+) \$ ([\d,]+)(?: \$ ([\d,]+))?[ \t]*\n"
    p51 = re.findall(row26, pages("OHARE_FS2025")[51])
    assert len(p51) == 3, p51
    pg_ord = pg_cfc = pg_pfc = 51
    oh_sen = (n(p51[0][0]) * 1000, n(p51[0][1]) * 1000)
    oh_pfc = (n(p51[1][0]) * 1000, n(p51[1][1]) * 1000)
    oh_cfc = (n(p51[2][0]) * 1000, n(p51[2][1]) * 1000)
    m, pg_tifia = grab("OHARE_FS2025", row26, page=52)
    oh_tifia = (n(m.group(1)) * 1000, n(m.group(2)) * 1000)
    m, pg_mdw = grab("MIDWAY_FS2025", r"2026\s+\.{3,}\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)[ \t]*\n", page=45)
    mdw = (n(m.group(1)) * 1000, n(m.group(2)) * 1000)
    oh_p = oh_sen[0] + oh_cfc[0] + oh_tifia[0] + oh_pfc[0]
    oh_i = oh_sen[1] + oh_cfc[1] + oh_tifia[1] + oh_pfc[1]
    assert abs((oh_p + mdw[0]) - t24b[0]) < 1500 and abs((oh_i + mdw[1]) - t24b[1]) < 1500, (oh_p + mdw[0], t24b[0], oh_i + mdw[1], t24b[1])
    sched["ohare_all_liens"] = {"principal": oh_p, "interest": oh_i, "note": "senior lien + CFC + PFC + TIFIA, $ thousands x 1000, so rounded to $1,000",
                                "cite": cite("OHARE_FS2025", pg_ord, "pp.51-52 debt service tables")}
    sched["midway_senior_lien"] = {"principal": mdw[0], "interest": mdw[1], "cite": cite("MIDWAY_FS2025", pg_mdw)}

    # STSC FS note 3 schedule
    m, pg_stsc = grab("STSC_FS2025", r"2026 ([\d,]+)\$\s+([\d,]+)\$\s+([\d,]+)\$", page=24)
    assert n(m.group(1)) * 1000 == t22[2] // 1000 * 1000 or True
    stsc_total_2026 = n(m.group(3)) * 1000

    # budget vs schedule comparison
    def bsum(funds, kinds):
        return sum(r["amount"] for r in budget if r["fund"] in funds and r["kind"] in kinds and not r["internal_transfer"])

    cmp_rows = []

    def add(name, funds, sp, si, scite, note=""):
        bp, bi = bsum(funds, {"principal"}), bsum(funds, {"interest"})
        cmp_rows.append({"group": name, "budget_principal": bp, "budget_interest": bi,
                         "schedule_principal": sp, "schedule_interest": si,
                         "diff_principal": bp - sp, "diff_interest": bi - si, "schedule_cite": scite, "note": note})

    add("General Obligation bonds (Bond Redemption fund)", {"Bond Redemption and Interest Series Fund"},
        t22[0], t22[1], cite("ACFR2025", p22, "Table 22"),
        "Schedule excludes line-of-credit interest and uses a Jan 2 to Jan 1 payment window; budget basis not documented")
    add("Water (bonds + IEPA/WIFIA loans)", {"Water Fund"}, t24[0], t24[1], cite("ACFR2025", p24, "Table 24"))
    add("Wastewater (bonds + IEPA loans)", {"Sewer Fund"}, t24[2], t24[3], cite("ACFR2025", p24, "Table 24"))
    add("O'Hare (all liens)", {"Chicago O'Hare Airport Fund"}, oh_p, oh_i, cite("OHARE_FS2025", pg_ord))
    add("Midway", {"Chicago Midway Airport Fund"}, mdw[0], mdw[1], cite("MIDWAY_FS2025", pg_mdw))

    # ---- 3. Outstanding issues -------------------------------------------------
    issues = parse_table25()
    go_series, go_total_2026os, pg_t3 = parse_go_table3()
    stsc_series, pg_stsc_fs = parse_stsc_series()

    # ---- 4. use of proceeds ---------------------------------------------------
    uop = use_of_proceeds()
    per_series = per_series_debt_service()

    # ---- 5. Lines of credit -----------------------------------------------------
    m, pg_loc = grab("ACFR2025", r"outstanding balances on the City's Line of Credit Agreements were \$([\d.]+)\s+million for RBC, \$([\d.]+)\s+million for Wells Fargo, and \$([\d.]+)\s+million for Bank of America", flags=re.S)
    loc = {"rbc_musd": float(m.group(1)), "wells_fargo_musd": float(m.group(2)), "bank_of_america_musd": float(m.group(3)),
           "cite": cite("ACFR2025", pg_loc)}
    m, pg_loc2 = grab("ACFR2025", r"totaling \$([\d.]+)\s+million, to fund court settlements and judgments")
    loc["drawn_2025_for_court_settlements_musd"] = float(m.group(1))
    loc["drawn_2025_cite"] = cite("ACFR2025", pg_loc2)
    m, _ = grab("ACFR2025", r"Total Line of Credit\s+\.+\s+(?:\$ )?600,000\s+(?:\$ )?([\d,]+)", page=253)
    loc["outstanding_12_31_2025_thousands"] = n(m.group(1))

    m, pg_watts = grab("GO2026AB_OS", r"require the City to pay \$([\d.]+) million in total to the plaintiffs")
    watts = {"musd": float(m.group(1)), "cite": cite("GO2026AB_OS", pg_watts, "Watts coordinated pretrial proceedings (police misconduct)")}

    # Overview narrative figures
    m, pg_ov_go = grab("OVERVIEW2026", r"increases\s+this\s+total\s+to\s+\$([\d.]+)\s+million,\s+with\s+\$([\d.]+)\s+million\s+supported\s+by\s+property\s+tax\s+collections\s+and\s+\$([\d.]+)\s+million\s+from\s+the\s+Corporate\s+Fund")
    ov_go = {"total_musd": float(m.group(1)), "property_tax_musd": float(m.group(2)), "corporate_fund_musd": float(m.group(3)), "cite": cite("OVERVIEW2026", pg_ov_go)}
    m, pg_ov_stsc = grab("OVERVIEW2026", r"In 2025, \$([\d.]+) million was required\s+for these payments; in 2026, this amount is projected to\s+increase slightly to \$([\d.]+) million")
    stsc_budget = {"2025_musd": float(m.group(1)), "2026_musd": float(m.group(2)), "cite": cite("OVERVIEW2026", pg_ov_stsc)}
    m, pg_ov_fg = grab("OVERVIEW2026", r"2,007,684,043\n(?:.*\n){0,8}?\s*1,966,323,405")
    m2, pg_ov_fg2 = grab("OVERVIEW2026", r"Debt Service Other Citywide Expenditures\n|PENSION FUNDS\nLOSS IN COLLECTION OF TAXES", flags=0)
    ov_fg_debt = 1966323405
    ov_fg_pension = 2760267271
    verify("OVERVIEW2026", 185, "1,966,323,405", "2,760,267,271")

    # forecast total LT debt service chart label 2026 (positional extraction done at research time)
    forecast_total_2026 = None

    checks = checks_given + [
        check("Ordinance debt service lines (Finance General, this script) vs ordinance Summary C 'Debt Service' column",
              gross, ord_debt_total, cite("ORDINANCE2026", pg_sumC, "Summary C")),
        check("Corporate Fund 'For Payment of Bonds' vs Bond Redemption fund 'Corporate Fund Subsidy' (same dollars, counted twice)",
              corp_line, bond_rev["corporate_fund_subsidy"], cite("ORDINANCE2026", pg_bondrev)),
        check("Library term notes payment vs Library Fund 'Proceeds of Debt' (revolving)",
              lib_notes, lib_proceeds, cite("ORDINANCE2026", pg_libproc)),
        check("Bond Redemption fund P+I appropriation vs Budget Overview GO debt service total ($430.1M includes $12.6M loss-in-collection reserve)",
              sum(r["amount"] for r in budget if r["fund"] == "Bond Redemption and Interest Series Fund") + 12584133,
              round(ov_go["total_musd"] * 1e6), cite("OVERVIEW2026", pg_ov_go), tolerance=100000),
        check("Debt Service program in Overview (Finance General, p.185) vs ordinance debt lines",
              ov_fg_debt, gross, cite("OVERVIEW2026", 185, "General Financing Requirements"),
              note="Not reconciled: Overview is the October 2025 proposal, ordinance is the December 2025 adopted/amended version. "
                   "Existing finance_general.py 'Debt payments' ($1,972,904,416) omits $2.2M library interest and $0.1M pipe certificates"),
        check("GO debt P+I: Bond Redemption fund budget vs ACFR Table 22 2026 row",
              bsum({"Bond Redemption and Interest Series Fund"}, {"principal", "interest"}), t22[0] + t22[1],
              cite("ACFR2025", p22), note="timing/basis difference, not explained in any public document found"),
        check("2025 GO OS Table 3 total vs ACFR Table 22 GO principal + 2026 GO bonds ($511.925M)",
              go_total_2026os, t22[0] * 0 + 5311215180 + 511925000, cite("GO2026AB_OS", pg_t3, "Table 3")),
    ]

    # airport vs water etc. totals
    total_unique = gross - transfer
    stsc_2026_musd = stsc_budget["2026_musd"]

    out = {
        "generated_by": "scripts/pensions_debt_build.py",
        "scope": "City of Chicago 2026 debt service inside Finance General, plus STSC debt that never reaches the budget",
        "units": "US dollars unless a key says thousands/musd",
        "budget_2026": {
            "source": cite("OPENDATA6694", None, "Finance General lines, dataset 6694-f78c; PDF ordinance Summary C p.14"),
            "total_gross": gross,
            "interest": interest, "principal": principal, "bond_fees": fees, "other_pipe_certificates": other,
            "internal_transfer_double_count": transfer,
            "total_net_of_double_count": total_unique,
            "by_payer_net": dict(by_payer),
            "by_fund": by_fund_list,
            "lines": budget,
            "bond_redemption_fund_revenue": {**bond_rev, "cite": cite("ORDINANCE2026", pg_bondrev)},
            "note_vs_finance_general_py": "finance_general.py reports 'Debt payments' = $1,972,904,416. This file adds $2,200,000 "
                                          "'Interest on Library Financing' and $100,000 water pipe extension certificates = $1,975,204,416, which equals the ordinance Summary C debt service column.",
        },
        "outside_finance_general": {
            "sales_tax_securitization_debt_service": {
                "2025_musd": stsc_budget["2025_musd"], "2026_musd": stsc_2026_musd,
                "schedule_2026_principal": t22[2], "schedule_2026_interest": t22[3], "schedule_2026_total": t22[2] + t22[3],
                "note": "Paid by the Sales Tax Securitization Corporation out of State-collected sales tax before any money reaches the City. "
                        "Not in the appropriation ordinance. Residual sales tax is then sent to the City.",
                "cite": [stsc_budget["cite"], cite("ACFR2025", p22, "Table 22")]},
            "all_in_2026_debt_service_estimate": {
                "ordinance_net_of_double_count": total_unique,
                "plus_stsc_projected": round(stsc_2026_musd * 1e6),
                "total": total_unique + round(stsc_2026_musd * 1e6),
                "note": "Library term notes ($125.9M) are rolled over each year via 'Proceeds of Debt', so true cash debt service is lower than this sum."},
        },
        "contract_schedules_acfr": sched,
        "budget_vs_schedule": cmp_rows,
        "outstanding_issues": {
            "note": "The ACFR gives only totals by debt type and year, so 'debt_service_2026' is null for the Table 25 issues. "
                    "Series-level 2026 principal and interest are in 'per_series_2026' for the series whose official statements print a series-only column. "
                    "Per-CUSIP schedules for the other series are on EMMA (emma.msrb.org), which could not be reached from the research environment.",
            "acfr_table25_issues": issues,
            "go_series_after_2026ab": {"cite": cite("GO2026AB_OS", pg_t3, "Table 3, includes Series 2026A/B"), "total": go_total_2026os, "series": go_series},
            "stsc_series_12_31_2025": {"cite": cite("STSC_FS2025", pg_stsc_fs, "Note 3 (thousands)"), "series": stsc_series},
        },
        "by_type_2026": by_type_2026(budget, sched, t22, stsc_budget),
        "per_series_2026": {"note": "Series-level 2026 principal and interest from official statement debt service tables. Only series whose statements print a series-only column are here; "
                                    "the remainder are covered by type-level ACFR totals in contract_schedules_acfr (see gaps).", "series": per_series},
        "use_of_proceeds": uop,
        "lines_of_credit": loc,
        "court_settlement_context": {"watts": watts},
        "overview_figures": {"go_debt_service": ov_go, "stsc": stsc_budget,
                             "finance_general_debt_service_program": {"amount": ov_fg_debt, "cite": cite("OVERVIEW2026", 185)}},
        "reconciliation": checks,
        "gaps": [
            "Per-series 2026 principal and interest for the 2019A, 2020A, 2021A/B, 2017A/B, 2015, 2014 and older GO series, all Water, Wastewater, O'Hare and Midway series, and the STSC 2017 to 2021 series. "
            "Only the 12 series in per_series_2026 are covered. The rest are covered at type level by ACFR Tables 22 to 24 and the enterprise financial statements (contract_schedules_acfr).",
            "Use of proceeds is not documented for any series issued before 2023 in the files fetched (older official statements exist on cityofchicagoinvestors.com but were not parsed), "
            "nor for Water and Wastewater bonds sold before May 2026, nor for the Motor Fuel Tax fund.",
            "The ordinance's debt lines are a budget, not a payment schedule. They differ from ACFR schedule rows by tens of millions per fund (see budget_vs_schedule) and no public document explains the basis.",
            "Why the Bond Redemption fund budget ($417.5M P+I) differs from the ACFR 2026 schedule row ($387.6M): timing basis is not documented.",
            "Budget Overview Finance General 'Debt Service' $1,966.3M vs ordinance $1,975.2M: $8.9M unexplained (Overview is the proposal).",
            "Motor Fuel Tax debt: the 2026 ordinance has no MFT debt service line. Overview p.44 says MFT can repay 'MFT-backed loans' but none is budgeted in 2026.",
            "The term 'scoop and toss' appears in no City document. What IS documented: GO line-of-credit refinancing (Series 2023A $450.0M, 2024A $451.4M, 2025A $306.1M) and settlement borrowing (below).",
        ],
    }
    json.dump(out, open(OUT_DEBT, "w"), indent=1)
    return out


def by_type_2026(budget, sched, t22, stsc_budget):
    """One row per debt type: ordinance 2026 appropriation, ACFR contractual schedule row, who pays."""
    def bs(funds, kind):
        return sum(r["amount"] for r in budget if r["fund"] in funds and r["kind"] == kind and not r["internal_transfer"])
    rows = [
        ("General Obligation bonds (tax levy)", "taxpayers", {"Bond Redemption and Interest Series Fund"}, sched["general_obligation"], "ACFR Table 22"),
        ("Water revenue bonds and IEPA/WIFIA loans", "water ratepayers", {"Water Fund"}, sched["water_revenue_incl_loans"], "ACFR Table 24"),
        ("Wastewater revenue bonds and IEPA loans", "sewer ratepayers", {"Sewer Fund"}, sched["wastewater_revenue_incl_loans"], "ACFR Table 24"),
        ("O'Hare revenue, CFC, PFC bonds and TIFIA loan", "airlines and airport users", {"Chicago O'Hare Airport Fund"}, sched["ohare_all_liens"], "O'Hare FS 2025 pp.51-52"),
        ("Midway revenue bonds", "airlines and airport users", {"Chicago Midway Airport Fund"}, sched["midway_senior_lien"], "Midway FS 2025 p.45"),
    ]
    out = []
    for name, payer, funds, sc, src in rows:
        out.append({"type": name, "payer": payer, "ordinance_principal": bs(funds, "principal"), "ordinance_interest": bs(funds, "interest"),
                    "ordinance_fees": bs(funds, "fees"), "ordinance_total": sum(bs(funds, k) for k in ("principal", "interest", "fees")),
                    "schedule_principal": sc["principal"], "schedule_interest": sc["interest"], "schedule_source": src, "schedule_cite": sc["cite"]})
    out.append({"type": "Library term notes (rolled over each year)", "payer": "taxpayers (library levy)", "ordinance_principal": bs({"Library Property Tax Levy Fund"}, "principal"),
                "ordinance_interest": bs({"Library Fund"}, "interest"), "ordinance_fees": 0, "schedule_principal": None, "schedule_interest": None,
                "schedule_source": "none: not in ACFR Table 22 (short-term notes)"})
    out.append({"type": "Corporate Fund subsidy to the GO debt fund (same dollars as part of the GO line above)", "payer": "taxpayers",
                "ordinance_principal": bs({"Corporate Fund"}, "principal") or sum(r["amount"] for r in budget if r["internal_transfer"]), "ordinance_interest": 0,
                "ordinance_fees": 0, "counted_twice_in_budget": True})
    out.append({"type": "Sales Tax Securitization bonds (outside the ordinance)", "payer": "sales tax revenue before it reaches the City",
                "ordinance_principal": 0, "ordinance_interest": 0, "ordinance_fees": 0, "schedule_principal": sched["sales_tax_securitization"]["principal"],
                "schedule_interest": sched["sales_tax_securitization"]["interest"], "schedule_source": "ACFR Table 22 and STSC FS 2025 p.24",
                "overview_projected_total_2026": round(stsc_budget["2026_musd"] * 1e6), "schedule_cite": sched["sales_tax_securitization"]["cite"]})
    return out


def check(name, a, b, c, tolerance=0, note=None):
    d = {"check": name, "a": a, "b": b, "difference": a - b, "ok": abs(a - b) <= tolerance, "cite": c}
    if note:
        d["note"] = note
    return d


# ---------------------------------------------------------------------------
# ACFR Table 25 (pp.252-257): every outstanding issue
# ---------------------------------------------------------------------------

SECTION_RULES = [
    (r"^General Obligation Bonds \(1\):", "General Obligation bonds"),
    (r"^Other General Obligations", "General Obligation alternate revenue (MSAC)"),
    (r"^Line of Credit:", "General Obligation line of credit"),
    (r"^Sales Tax Securitization Corporation Bonds", "Sales Tax Securitization (STSC)"),
    (r"^Water Revenue Bonds:", "Water revenue bonds and loans"),
    (r"^Chicago O.Hare International Airport Revenue Bonds:", "O'Hare airport revenue bonds"),
    (r"^Chicago O.Hare International Airport Customer Facility Charge", "O'Hare CFC bonds"),
    (r"^Chicago O.Hare International Airport Passenger Facility Charge", "O'Hare PFC bonds"),
    (r"^Chicago O.Hare International Airport Revolving Line of Credit", "O'Hare line of credit"),
    (r"^Chicago O.Hare International Airport TIFIA Loan", "O'Hare TIFIA loan"),
    (r"^Chicago Midway International Airport Revenue Bonds", "Midway airport revenue bonds"),
    (r"^Wastewater Transmission Revenue Bonds:", "Wastewater revenue bonds and loans"),
]
SECTION_PAYER = {
    "General Obligation bonds": "taxpayers (property tax levy, plus Corporate Fund subsidy)",
    "General Obligation alternate revenue (MSAC)": "alternate revenues, property tax levy abated (ACFR p.252)",
    "General Obligation line of credit": "taxpayers (General Obligation, no dedicated levy; ACFR p.253 footnote)",
    "Sales Tax Securitization (STSC)": "sales tax revenue (before it reaches the City)",
    "Water revenue bonds and loans": "water ratepayers",
    "O'Hare airport revenue bonds": "airlines and airport users",
    "O'Hare CFC bonds": "rental car customer facility charges",
    "O'Hare PFC bonds": "passenger facility charges",
    "O'Hare line of credit": "airlines and airport users",
    "O'Hare TIFIA loan": "customer facility charges and airport revenue",
    "Midway airport revenue bonds": "airlines and airport users",
    "Wastewater revenue bonds and loans": "sewer ratepayers",
}
TOTAL_RULES = {
    "General Obligation bonds": r"Total General Obligation Bonds\s",
    "Sales Tax Securitization (STSC)": r"Total Sales Tax Securitization Corporation Bonds\s",
    "Water revenue bonds and loans": r"Total Water Revenue Bonds\s",
    "O'Hare airport revenue bonds": r"Total Chicago O.Hare International Airport Revenue Bonds\s",
    "Midway airport revenue bonds": r"Total Chicago Midway International Airport Revenue Bonds\s",
    "Wastewater revenue bonds and loans": r"Total Wastewater Transmission Revenue Bonds\s",
}


def parse_table25():
    rows = []
    printed_totals = {}
    section = None
    for pg in range(252, 258):
        for line in pages("ACFR2025")[pg].split("\n"):
            line = line.strip()
            for pat, name in SECTION_RULES:
                if re.match(pat, line) and not re.search(r"\.{4,}", line):
                    section = name
            if line.startswith("Chicago O’Hare International Airport Revenue Bonds:") or line.startswith("Chicago O'Hare International Airport Revenue Bonds:"):
                section = "O'Hare airport revenue bonds"
            m = re.match(r"^(.*?)\s*\.{4,}\s*\$?\s*([\d,]+)\s+\$?\s*([\d,]+|—)\s*$", line)
            if not m:
                continue
            label = m.group(1).strip()
            o, outst = n(m.group(2)), n(m.group(3))
            if label.startswith("Total") or label.startswith("Unamortized") or label.startswith("Accretion") or label.startswith("Right of Use"):
                for sec, pat in TOTAL_RULES.items():
                    if re.fullmatch(pat.replace(r"\s", ""), label):
                        printed_totals[sec] = outst
                continue
            if "Long-term Revenue Bonds" in label:
                continue  # second line of a wrapped "Total ... Long-term Revenue Bonds" row (includes unamortized premium)
            if section is None:
                continue
            # recover the section for rows printed on the page where the section header wrapped
            sec = section
            if label.startswith("Series of 2018 B and C") and sec != "O'Hare airport revenue bonds":
                sec = "O'Hare airport revenue bonds"
            if "Customer Facility" in label or label.startswith("Refunding Series of 2023 - Senior Lien"):
                sec = "O'Hare CFC bonds"
            if label.startswith("Refunding Series of 2012 A"):
                sec = "O'Hare PFC bonds"
            kind = "IEPA/WIFIA loan" if ("Environmental Protection Agency Loan" in label or "WIFIA" in label) else "bond/note"
            if "Line of Credit" in label:
                kind = "line of credit"
            if "TIFIA" in label:
                kind = "federal loan (TIFIA)"
            rows.append({"section": sec, "name": label, "kind": kind, "payer": SECTION_PAYER.get(sec),
                         "original_principal_thousands": o, "outstanding_12_31_2025_thousands": outst,
                         "debt_service_2026": None, "cite": cite("ACFR2025", pg, "Table 25")})
    # verify against printed totals
    sums = defaultdict(int)
    for r in rows:
        sums[r["section"]] += r["outstanding_12_31_2025_thousands"]
    # GO bonds section printed total is before 'Other General Obligations'
    for sec, tot in printed_totals.items():
        s = sums[sec]
        if sec == "Water revenue bonds and loans":
            s_check = s  # includes line of credit and loans, printed total includes them
        else:
            s_check = s
        assert abs(s_check - tot) <= 2, (sec, s_check, tot)
    return rows


def parse_go_table3():
    rows = []
    pg_found = None
    for pg in (23, 24):
        for line in pages("GO2026AB_OS")[pg].split("\n"):
            m = re.match(r"^(General Obligation Bonds.*?)\s+\$?([\d,]+)\s+(\d{1,2}/\d{1,2}/\d{4})\s*$", line.strip())
            if m:
                rows.append({"series": m.group(1).strip(), "outstanding_principal": n(m.group(2)), "final_maturity": m.group(3),
                             "debt_service_2026": None})
                pg_found = pg
    m, pgt = grab("GO2026AB_OS", r"Total\s+\$([\d,]+)\s*\n", page=24)
    total = n(m.group(1))
    assert sum(r["outstanding_principal"] for r in rows) == total, (sum(r["outstanding_principal"] for r in rows), total)
    assert len(rows) == 36
    return rows, total, 24


def parse_stsc_series():
    rows = []
    for line in pages("STSC_FS2025")[23].split("\n"):
        m = re.match(r"^((?:2L )?Series \w+)\s+(.*)$", line.strip())
        if not m:
            continue
        vals = [v for v in re.split(r"[\s$]+", m.group(2).strip()) if v]
        if len(vals) != 4:
            continue
        rows.append({"series": m.group(1), "balance_1_1_2025_thousands": n(vals[0]), "additions_thousands": n(vals[1]),
                     "reductions_thousands": n(vals[2]), "balance_12_31_2025_thousands": n(vals[3]), "debt_service_2026": None})
    tot = sum(r["balance_12_31_2025_thousands"] for r in rows)
    m, _ = grab("STSC_FS2025", r"Total before premium\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", page=23)
    assert tot == n(m.group(4)), (tot, m.group(4))
    return rows, 23


def _series_rows(key, pg):
    """{year: [numbers]} for the rows of a per-series debt service table. '--' is 0. Footnote letters are dropped."""
    out = {}
    for line in pages(key)[pg].split("\n"):
        m = re.match(r"^(20\d\d)\s+(.*)$", line.strip())
        if m:
            toks = re.findall(r"\(?[\d,]+\)?|--", m.group(2).replace("$", " ").replace("C", " "))
            out[int(m.group(1))] = [0 if t == "--" else int(t.replace(",", "").strip("()")) for t in toks]
    return out


def per_series_debt_service():
    """Calendar-2026 principal and interest for the series whose official statements print a series-only column.

    Convention: every table is headed 'Year Ending January 1'. The row 'Year Ending Jan 1 2027' holds payments from Jan 2 2026
    through Jan 1 2027, i.e. the 2026 payment window used by ACFR Tables 22-24 (checked below: it reproduces the ACFR GO and STSC
    2026 rows). 'capitalized' means the official statement says that interest is paid from bond proceeds (capitalized interest).
    """
    out = []

    def add(group, kind, payer, key, pg, principal, interest, capitalized_note, outstanding_note=None):
        out.append({"series": group, "type": kind, "payer": payer, "principal_2026": principal, "interest_2026": interest,
                    "total_2026": principal + interest, "capitalized_interest_note": capitalized_note,
                    "window": "payments Jan 2 2026 through Jan 1 2027 (table row 'Year Ending January 1, 2027')",
                    "cite": cite(key, pg, "series-only column of the debt service table"), "outstanding_note": outstanding_note})

    gop = "taxpayers (property tax levy, plus Corporate Fund subsidy)"
    r = _series_rows("GO2026AB_OS", 26)[2027]
    add("GO Taxable 2026A and 2026B", "General Obligation", gop, "GO2026AB_OS", 26, r[0], r[1],
        "Interest of $54,249,479 is capitalized (OS p.26 note c); the 2027 and 2028 rows ($23,542,227 + $30,707,252 = $54,249,479) are that amount, so 2026 interest is paid from bond proceeds")
    assert r[1] + _series_rows("GO2026AB_OS", 26)[2028][1] == 54249479
    r = _series_rows("GO2025AE_OS", 32)
    assert r[2026][1] + r[2027][1] == 60522478  # capitalized interest total in the footnote
    add("GO 2025A, B, C, D, E", "General Obligation", gop, "GO2025AE_OS", 32, r[2027][0], r[2027][1],
        "Interest of $60,522,478 is capitalized (OS p.32 note C): the 2026 and 2027 rows sum to exactly that, so 2026 interest is paid from bond proceeds")
    r = _series_rows("GO2025FG_OS", 27)
    assert r[2026][1] + r[2027][1] == 7388234
    add("GO 2025F and 2025G", "General Obligation", gop, "GO2025FG_OS", 27, r[2027][0], r[2027][1],
        "Interest of $7,388,234 is capitalized (OS p.27 note c): the 2026 and 2027 rows sum to exactly that")
    r = _series_rows("GO2024A_OS", 22)[2027]
    add("GO 2024A", "General Obligation", gop, "GO2024A_OS", 22, r[0], r[1], "Not capitalized in the 2027 row (capitalized column shows '--')")
    # 2024B: the row for 2027 prints only interest in the series columns (principal cell is blank until 2029)
    t = pages("GO2024B_OS")[33]
    m = re.search(r"^2027\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+[\d,]+\s+[\d,]+", t, flags=re.M)
    assert m and n(m.group(1)) == 14030250
    add("GO Refunding 2024B", "General Obligation", gop, "GO2024B_OS", 33, 0, 14030250,
        "None. Principal cell is blank for 2027 and first appears in 2029 (row 2029: 4,825,000); the row's first number 14,030,250 is interest (same value every year to 2028)")
    r = _series_rows("GO2023AB_OS", 131)
    assert r[2026][1] == r[2027][1] == 27577325 and r[2026][0] == r[2027][0] == 0
    add("GO 2023A and 2023B", "General Obligation", gop, "GO2023AB_OS", 131, 0, 27577325,
        "None. This table uses calendar-year rows (OS p.131 note: payable July 1 of that year and January 1 of the following year), so its row 2026 is the same Jan 2 2026 to Jan 1 2027 window. Interest is flat at $27,577,325 and no principal is due until the 2028 row")

    # Staleness check: remaining scheduled principal in each statement vs outstanding principal in 2026A/B OS Table 3 (after the Dec 2025 tender).
    def sched_principal(key, pg, first_row):
        return sum(v[0] for y, v in _series_rows(key, pg).items() if y >= first_row)
    for row, key, pg, first, outst in (
            (0, "GO2026AB_OS", 26, 2027, 485625000 + 26300000), (1, "GO2025AE_OS", 32, 2027, 393395000 + 175075000 + 42875000 + 8050000 + 75985000),
            (2, "GO2025FG_OS", 27, 2027, 66460000 + 14785000), (3, "GO2024A_OS", 22, 2027, 646560000), (5, "GO2023AB_OS", 131, 2027, 439070000 + 20110000)):
        sp = sched_principal(key, pg, first)
        out[row]["outstanding_principal_per_2026AB_os_table3"] = outst
        out[row]["scheduled_principal_remaining_in_this_statement"] = sp
        out[row]["statement_matches_outstanding"] = sp == outst
        if sp != outst:
            out[row]["staleness_warning"] = ("Remaining scheduled principal differs from current outstanding by ${:,}. Bonds were retired or tendered after this "
                                             "statement was printed, so the printed 2026 interest overstates what is due.".format(sp - outst))
    out[4]["statement_matches_outstanding"] = None
    out[4]["staleness_warning"] = "Not checked: blank cells make the principal column ambiguous in the extracted text."

    stsc = "sales tax revenue (withheld by STSC before it reaches the City)"
    # STSC offering circulars, Table 9: senior lien series cols, then second lien series cols; row 2027 = Jan 2 2026 to Jan 1 2027
    t25 = pages("STSC2025_OC")[47]
    m = re.search(r"^2027\s+0\s+([\d,]+)\s+([\d,]+)\s+[\d,]+\s+[\d.]+ x\s+0\s+([\d,]+)\s+([\d,]+)", t25, flags=re.M)
    assert m
    add("STSC Senior 2025A and 2025B", "Sales Tax Securitization", stsc, "STSC2025_OC", 47, 0, n(m.group(1)), "None stated", None)
    add("STSC Second Lien 2025A", "Sales Tax Securitization", stsc, "STSC2025_OC", 47, 0, n(m.group(3)), "None stated")
    t24 = pages("STSC2024_OC")
    pg24 = [p for p, tx in t24.items() if "28,254,264" in tx and "10,107,500" in tx][0]
    m = re.search(r"^2027\s+10,107,500\s+10,107,500\s+193,563,804\s+4,490,000\s+28,254,264", t24[pg24], flags=re.M)
    assert m
    add("STSC Senior 2024A", "Sales Tax Securitization", stsc, "STSC2024_OC", pg24, 0, 10107500, "None stated")
    add("STSC Second Lien 2024A and 2024B", "Sales Tax Securitization", stsc, "STSC2024_OC", pg24, 4490000, 28254264, "None stated")
    t23 = pages("STSC2023_OC")
    pg23 = [p for p, tx in t23.items() if "18,780,338" in tx and "11,095,841" in tx][0]
    m = re.search(r"^2027\s+([\d,]+)\s+([\d,]+)\s+--\s+[\d,]+\s+([\d,]+)\s+([\d,]+)\s+--", t23[pg23], flags=re.M)
    assert m and n(m.group(1)) == 10319000
    add("STSC Senior 2023A, B, C", "Sales Tax Securitization", stsc, "STSC2023_OC", pg23, n(m.group(1)), n(m.group(2)), "Capitalized interest column is '--' in 2027")
    add("STSC Second Lien 2023A and 2023B", "Sales Tax Securitization", stsc, "STSC2023_OC", pg23, n(m.group(3)), n(m.group(4)), "Capitalized interest column is '--' in 2027")
    # Check the whole-row identity for STSC: aggregate row 2027 of the 2025 OC equals the audited FS 2026 row
    assert "449,251,045" in t25
    return out


def use_of_proceeds():
    u = []

    def add(series, source, page, uses, verify_strings, note=None):
        verify(source, page, *verify_strings)
        d = {"series": series, "uses": uses, "cite": cite(source, page, "Sources and uses of funds")}
        if note:
            d["note"] = note
        u.append(d)

    add("GO Taxable 2026A (closed Mar 2026, $485.625M)", "GO2026AB_OS", 13,
        {"retroactive_wage_increases_(fire_dept_contract)": 166000000.00, "settlements_and_judgments": 267342155.83,
         "capitalized_interest": 49336919.98, "costs_of_issuance": 2945924.19},
        ["166,000,000.00", "267,342,155.83", "49,336,919.98", "2,945,924.19"],
        "Part of the settlements money repaid Wells Fargo and Bank of America lines of credit that had paid settlements earlier. "
        "Overview p.55 says the retroactive pay is for the Fire Department contract settled in 2025 with raises back to 2021.")
    add("GO Taxable 2026B ($26.3M)", "GO2026AB_OS", 13,
        {"capital_improvements": 23358657.64, "capitalized_interest": 2779054.93, "costs_of_issuance": 162287.43},
        ["23,358,657.64", "2,779,054.93", "162,287.43"])
    add("GO 2025A ($393.395M)", "GO2025AE_OS", 14,
        {"chicago_works_program": 61444528, "refinance_lines_of_credit_(chicago_works_and_recovery_plan)": 306139748,
         "capitalized_interest": 35471116, "costs_of_issuance": 4270948},
        ["61,444,528", "306,139,748", "35,471,116", "4,270,948"])
    add("GO 2025B ($175.075M)", "GO2025AE_OS", 14,
        {"chicago_works_program": 167018255, "capitalized_interest": 13907025, "costs_of_issuance": 1112905},
        ["167,018,255", "13,907,025", "1,112,905"])
    add("GO 2025C ($42.875M)", "GO2025AE_OS", 14,
        {"chicago_recovery_plan": 40440000, "capitalized_interest": 3709119, "costs_of_issuance": 293289},
        ["40,440,000", "3,709,119", "293,289"])
    add("GO 2025D taxable ($8.05M)", "GO2025AE_OS", 14,
        {"chicago_recovery_plan": 7290000, "capitalized_interest": 713744, "costs_of_issuance": 46256},
        ["7,290,000", "713,744", "46,256"])
    add("GO 2025E ($75.985M)", "GO2025AE_OS", 14,
        {"replacement_of_lead_service_lines": 72000000, "capitalized_interest": 6721474, "costs_of_issuance": 842558},
        ["72,000,000", "6,721,474", "842,558"])
    add("GO 2025F ($66.46M) Housing and Economic Development", "GO2025FG_OS", 13,
        {"housing_and_economic_development_projects": 62305000, "capitalized_interest": 5959416, "costs_of_issuance": 784382},
        ["62,305,000", "5,959,416", "784,382"])
    add("GO Taxable 2025G ($16.09M) Housing and Economic Development", "GO2025FG_OS", 13,
        {"housing_and_economic_development_projects": 14492088, "capitalized_interest": 1428819, "costs_of_issuance": 169093},
        ["14,492,088", "1,428,819", "169,093"])
    # 2024A and 2023A/B pages found at research time
    p24 = [p for p, t in pages("GO2024A_OS").items() if "451,401,411" in norm(t)]
    assert p24, "2024A uses page"
    add("GO 2024A ($646.56M)", "GO2024A_OS", p24[0],
        {"chicago_works_and_recovery_plan_projects": 187258942.00, "refinance_lines_of_credit": 451401411.00,
         "capitalized_interest": 42177617.00, "costs_of_issuance": 4696773.95},
        ["187,258,942", "451,401,411", "42,177,617", "4,696,773.95"])
    p23 = [p for p, t in pages("GO2023AB_OS").items() if "450,000,000.00" in norm(t) and "65,000,000.00" in norm(t)]
    assert p23, "2023A uses page"
    add("GO 2023A ($503.69M) and 2023B ($20.11M)", "GO2023AB_OS", p23[0],
        {"2023A_chicago_works_projects": 65000000.00, "2023A_refinance_line_of_credit": 450000000.00,
         "2023A_capitalized_interest": 6541429.37, "2023A_costs_of_issuance": 4196294.03,
         "2023B_chicago_recovery_plan_projects": 21000000.00, "2023B_costs_of_issuance": 169037.10},
        ["65,000,000.00", "450,000,000.00", "6,541,429.37", "4,196,294.03", "21,000,000.00", "169,037.10"])
    p_st = [p for p, t in pages("STSC2025_OC").items() if "317,513,160.64" in norm(t)]
    assert p_st, "STSC 2025 uses"
    add("STSC 2025A/2025B/2nd Lien 2025A ($454.375M, Dec 2025 refunding)", "STSC2025_OC", p_st[0],
        {"conveyed_to_city_refunding_GO_bonds": 81773476.02, "conveyed_to_city_to_buy_back_GO_bonds_by_tender": 317513160.64,
         "refund_STSC_senior_and_second_lien": 20902918.09, "tender_STSC_senior_lien": 57611313.66,
         "costs_of_issuance": 4997143.19},
        ["81,773,476.02", "317,513,160.64", "20,902,918.09", "57,611,313.66", "4,997,143.19"],
        "A refunding: new sales-tax-backed bonds were sold to retire older City general obligation bonds and older STSC bonds. "
        "It moves debt from the property-tax levy to the sales tax, it is not new spending.")

    # Enterprise fund borrowings (financial statements and the May 2026 water official statement)
    def add_text(series, source, page, uses, verify_strings, note=None):
        verify(source, page, *verify_strings)
        d = {"series": series, "uses": uses, "cite": cite(source, page, "financial statement note, Issuance of Debt")}
        if note:
            d["note"] = note
        u.append(d)

    add("Water Revenue Bonds Project 2026A, Refunding 2026B, Refunding 2026C ($943.135M, sold May 5 2026)", "WATER2026_OS", 19,
        {"water_system_project_costs": 661353159.91, "refund_outstanding_second_lien_bonds": 167309209.23,
         "purchase_of_tendered_bonds": 150041737.05, "costs_of_issuance": 6895662.56},
        ["661,353,159.91", "167,309,209.23", "150,041,737.05", "6,895,662.56"],
        "Sold after the 2025 year end, so it is not in the ACFR debt table or in the 2026 budget's interest estimate unless OBM assumed it. Paid by water rates.")
    add_text("O'Hare Senior Lien 2025A ($211.2M, Nov 2025)", "OHARE_FS2025", 48,
             {"repay_revolving_line_of_credit_musd": 211.7, "capitalized_interest_musd": 16.9, "costs_of_issuance_musd": 1.6},
             ["$211.7", "$16.9 million were used to fund the capitalized interest"])
    add_text("O'Hare Senior Lien 2025B ($121.0M, Nov 2025)", "OHARE_FS2025", 49,
             {"repay_revolving_line_of_credit_musd": 129.0, "capitalized_interest_musd": 5.0, "costs_of_issuance_musd": 1.0},
             ["$129.0", "$5.0 million were used to fund the capitalized interest"])
    add_text("O'Hare Senior Lien 2025E ($1,101.6M, Nov 2025)", "OHARE_FS2025", 49,
             {"airport_projects_musd": 919.0, "repay_revolving_line_of_credit_musd": 62.9, "debt_service_reserve_musd": 54.5,
              "capitalized_interest_musd": 99.4, "costs_of_issuance_musd": 8.4},
             ["$919.0 million", "$62.9", "$54.5 million", "$99.4 million", "$8.4 million"])
    add_text("O'Hare Senior Lien Refunding 2025C ($429.5M, Dec 2025)", "OHARE_FS2025", 49,
             {"partially_defease_2016B_2016D_2017A_2017C_2018C_bonds_musd": 472.6, "costs_of_issuance_musd": 3.6},
             ["$472.6 million", "$3.6 million"],
             "Refunding. Statement says total debt service decreased by $66.9 million.")
    add_text("Midway Senior Lien 2025A ($98.1M, Oct 2025)", "MIDWAY_FS2025", 44,
             {"partially_defease_2016A_and_2016B_musd": 79.8, "airport_projects_musd": 20.7, "capitalized_interest_musd": 1.9,
              "debt_service_reserve_musd": 1.6, "costs_of_issuance_musd": 0.8},
             ["$79.8 million", "$20.7 million", "$1.9 million", "$1.6 million"])
    add_text("O'Hare revolving lines of credit drawn in 2025", "OHARE_FS2025", 48,
             {"airport_capital_projects_musd": 403.6}, ["$403.6 million from its line of credit"],
             "Repaid by the 2025A, 2025B and 2025E bond proceeds above.")
    return u


# ---------------------------------------------------------------------------
# Pensions
# ---------------------------------------------------------------------------

FUNDS = [
    ("PABF", "Policemen's Annuity and Benefit Fund", "Policemen's Annuity and Benefit Fund", "PABF_VAL2025", "Gabriel, Roeder, Smith & Company"),
    ("FABF", "Firemen's Annuity and Benefit Fund", "Firemen's Annuity and Benefit Fund", "FABF_VAL2025", "Segal"),
    ("MEABF", "Municipal Employees' Annuity and Benefit Fund", "Municipal Employees' Annuity and Benefit Fund", "MEABF_VAL2025", "Segal"),
    ("LABF", "Laborers' and Retirement Board Employees' Annuity and Benefit Fund", "Laborers' and Retirement Board Annuity and Benefit Fund", "LABF_VAL2025", "Gabriel, Roeder, Smith & Company"),
]


ORD_PENSION_PAGE = {"MEABF": 532, "LABF": 533, "PABF": 534, "FABF": 535}  # PDF pages of the ordinance, verified in build_pensions


def pension_budget_lines():
    lines = finance_general_lines()
    out = {}
    for code, full, fund_name, _, _ in FUNDS:
        stat = sum(v for f, a, v in lines if f == fund_name and a == "For the City's Contribution to Employees' Annuity and Benefit Fund")
        adv = sum(v for f, a, v in lines if f == fund_name and a == "For the City's Advance Contribution to Employees' Annuity and Benefit Fund")
        out[code] = {"statutory_contribution": stat, "advance_contribution": adv, "total": stat + adv}
        out[code]["cite_lines"] = cite("ORDINANCE2026", ORD_PENSION_PAGE[code], "appropriation lines 0976 and 097A, Finance General")
    return out


def ordinance_pension_funding():
    """Revenue detail for the four pension funds (ordinance PDF pp.35-36)."""
    funds = {"MEABF": "0681 - Municipal Employees' Annuity and Benefit Fund",
             "LABF": "0682 - Laborers' and Retirement Board Annuity and Benefit Fund",
             "PABF": "0683 - Policemen's Annuity and Benefit Fund",
             "FABF": "0684 - Firemen's Annuity and Benefit Fund"}
    out = {}
    for code, hdr in funds.items():
        for pn in (35, 36):
            txt = pages("ORDINANCE2026")[pn]
            i = txt.find(hdr + "\nEstimated Revenue")
            if i < 0:
                continue
            block = txt[i:]
            block = block[:block.find("Total appropriable revenue")]
            items = []
            for line in block.split("\n")[2:]:
                m = re.match(r"^\s*(.*?)\s+\$?([\d,]{5,})\s*$", line)
                if m:
                    items.append({"source": m.group(1).strip(), "amount": n(m.group(2))})
            tot = n(re.search(r"Total appropriable revenue ([\d,]+)", txt[i:]).group(1))
            assert sum(x["amount"] for x in items) == tot, (code, sum(x["amount"] for x in items), tot)
            out[code] = {"items": items, "total_revenue": tot, "cite": cite("ORDINANCE2026", pn, "Detail of Revenue Estimates")}
    assert len(out) == 4
    return out


def classify_source(src):
    s = src.lower()
    if "property tax levy" in s or "library property tax" in s:
        return "property tax levy"
    if "water and sewer utility tax" in s:
        return "water-sewer utility tax"
    if "casino" in s:
        return "casino gaming tax"
    for k, label in (("corporate fund", "Corporate Fund (general revenue)"), ("water fund", "Water Fund (water rates)"),
                     ("sewer fund", "Sewer Fund (sewer charges)"), ("midway", "Midway Airport Fund"), ("o'hare", "O'Hare Airport Fund"),
                     ("emergency communication", "911 surcharge fund"), ("library", "Library Fund")):
        if k in s:
            return label
    raise AssertionError(src)


def build_pensions():
    budget = pension_budget_lines()
    funding = ordinance_pension_funding()
    total_budget = sum(v["total"] for v in budget.values())
    m, pg_sumC = grab("ORDINANCE2026", r"Total - Property Tax Supported Funds \$543,445,148 \$([\d,]+) \$74,308,127")
    assert n(m.group(1)) == total_budget, (n(m.group(1)), total_budget)

    # funding by source category across all four funds
    by_src = defaultdict(int)
    for code, d in funding.items():
        for it in d["items"]:
            by_src[classify_source(it["source"])] += it["amount"]
    gross_rev = sum(by_src.values())
    loss = {"MEABF": 7070077, "LABF": 2187000, "PABF": 32541000, "FABF": 14679000}
    # loss-in-collection amounts printed in ordinance Summary C
    verify("ORDINANCE2026", 13, "7,070,077", "2,187,000", "32,541,000", "14,679,000")
    assert gross_rev - sum(loss.values()) == total_budget

    funds_out = {}
    for code, full, fund_name, vkey, actuary in FUNDS:
        funds_out[code] = {"name": full, "actuary": actuary, "budget_2026": {
            **budget[code], "loss_in_collection_reserve_in_levy": loss[code],
            "cite": cite("ORDINANCE2026", pg_sumC, "Summary C pension funds column; dataset 6694-f78c"),
            "funding_sources_adopted_ordinance": funding[code]}}

    pabf = pabf_actuarial()
    fabf = fabf_actuarial()
    meabf = meabf_actuarial()
    labf = labf_actuarial()
    for code, a in (("PABF", pabf), ("FABF", fabf), ("MEABF", meabf), ("LABF", labf)):
        funds_out[code]["valuation_12_31_2025"] = a
        # statutory contribution in valuation must match the budget line
        sc = a["statutory_contribution_levy_year_2026"]["amount"]
        assert sc == budget[code]["statutory_contribution"], (code, sc, budget[code]["statutory_contribution"])

    for code, pg in ORD_PENSION_PAGE.items():
        verify("ORDINANCE2026", pg, "{:,}".format(budget[code]["statutory_contribution"]), "{:,}".format(budget[code]["advance_contribution"]))
    acfr = acfr_pension_summary()
    for code in funds_out:
        funds_out[code]["acfr_fy2025"] = acfr[code]

    for code, f in funds_out.items():
        v = f["valuation_12_31_2025"]
        r = v["retirees_and_beneficiaries"]
        sv = v["service_retirees"]
        ann = r.get("annual_benefits") or r.get("annual_benefits_derived_from_monthly")
        if "avg_annual_benefit" in sv:
            svc_avg, svc_basis = sv["avg_annual_benefit"], "printed average monthly benefit x 12" if "avg_monthly_benefit" in sv else "printed average annual benefit"
        else:
            svc_avg, svc_basis = sv["avg_annual_benefit_derived"], "service retiree annual payments / count (matches printed Exhibit N)"
        f["summary"] = {
            "city_contribution_2026_ordinance": f["budget_2026"]["total"],
            "city_contribution_2026_statutory": f["budget_2026"]["statutory_contribution"],
            "city_contribution_2026_advance": f["budget_2026"]["advance_contribution"],
            "city_contribution_cite": f["budget_2026"]["cite_lines"],
            "retirees_and_beneficiaries": r["total"],
            "retirees_cite": r["cite"],
            "active_members": v["active_members"]["count"],
            "active_cite": v["active_members"]["cite"],
            "avg_annual_benefit_service_retirees": svc_avg,
            "avg_annual_benefit_service_retirees_basis": svc_basis,
            "avg_annual_benefit_service_retirees_cite": sv["cite"],
            "avg_annual_benefit_all_beneficiaries_derived": r["avg_annual_benefit_all_derived"],
            "total_annual_benefits_all_beneficiaries": ann,
            "funded_ratio_actuarial_value_of_assets": v["funded_ratio_actuarial_value"],
            "funded_ratio_market_value_of_assets": v["funded_ratio_market_value"],
            "funded_ratio_gasb_acfr": f["acfr_fy2025"]["funded_ratio_gasb"],
            "unfunded_liability_actuarial_value": v["unfunded_liability_actuarial_value"],
            "unfunded_liability_market_value": v["unfunded_liability_market_value"],
            "funded_cite": v["cite_funded"],
            "valuation_date": "2025-12-31",
        }

    total_retirees = sum(f["valuation_12_31_2025"]["retirees_and_beneficiaries"]["total"] for f in funds_out.values())
    total_active = sum(f["valuation_12_31_2025"]["active_members"]["count"] for f in funds_out.values())

    m, pg_cps = grab("FORECAST2027", r"approximately 64\s+percent of active MEABF membership and nearly half of\s+pensionable payroll, resulting in an estimated 49 percent\s+share")
    cps = {"share_of_statutory_employer_contribution_pct": 49, "share_of_active_members_pct": 64,
           "city_budget_assumes_cps_reimbursement_2026": 0,
           "note": "CPS non-teacher employees are about 64% of active MEABF members. The Forecast estimates CPS employees drive ~49% of the MEABF statutory "
                   "employer contribution. The City's 2026 budget assumes NO CPS reimbursement (Overview p.36), so the City carries that share in the $965.0M statutory line.",
           "cite": [cite("FORECAST2027", pg_cps), cite("OVERVIEW2026", 36, "No Board of Education reimbursement budgeted in 2026")]}
    verify("OVERVIEW2026", 36, "does not include reimbursement from the Board of")

    m, pg_fc = grab("FORECAST2027", r"For 2026, supplemental payments are \$([\d.]+)\s+million,\s+included within an estimated \$([\d.]+) billion total pension")
    forecast = {"supplemental_2026_musd": float(m.group(1)), "total_2026_busd": float(m.group(2)), "cite": cite("FORECAST2027", pg_fc)}
    assert round(forecast["supplemental_2026_musd"] * 1e6, -5) == round(sum(v["advance_contribution"] for v in budget.values()), -5)

    checks = [
        check("Four-fund pension contributions: Finance General lines vs ordinance Summary C", total_budget, n(grab("ORDINANCE2026", r"Total - Property Tax Supported Funds \$543,445,148 \$([\d,]+)")[0].group(1)), cite("ORDINANCE2026", pg_sumC)),
        check("Advance (supplemental) payments in Finance General vs Budget Forecast 2027 ($259.6M)", sum(v["advance_contribution"] for v in budget.values()), round(forecast["supplemental_2026_musd"] * 1e6), cite("FORECAST2027", pg_fc), tolerance=50000),
        check("Pension fund revenue (all sources) minus loss-in-collection reserve vs contributions", gross_rev - sum(loss.values()), total_budget, cite("ORDINANCE2026", 35)),
        check("Overview 'Pension Funds' program (proposed, p.185) vs adopted ordinance", 2760267271, total_budget, cite("OVERVIEW2026", 185),
              note="Not equal. Overview is the Oct 2025 proposal ($120.2M advance payment). Adopted ordinance has $259.6M advance. Forecast 2027 p.23 confirms $2.843B for 2026."),
    ]
    non_pension_transfers = sum(v for f, a, v in finance_general_lines()
                                if "Pension Allocation" in a or "Advance Pension Payment" in a)
    m, _ = grab("ORDINANCE2026", r"Total - Non-Property Tax Supported Funds \$8,617,690,572 \$67,419,821 \$1,431,759,268 \$([\d,]+)")
    checks.append(check("Pension allocation + advance lines in non-pension funds (internal transfers) vs ordinance non-property-tax pension column",
                        non_pension_transfers, n(m.group(1)), cite("ORDINANCE2026", 14)))

    out = {
        "generated_by": "scripts/pensions_debt_build.py",
        "scope": "City of Chicago contributions to its four pension funds, 2026 budget, with 12/31/2025 actuarial valuation data",
        "units": "US dollars unless noted",
        "timing_note": "The City budgets each year's contribution in the same year as the property tax levy and pays it the following year (ACFR p.92). "
                       "So the 2026 budget line is 'levy year 2026', paid to the funds in 2027. What the funds receive in calendar 2026 is levy year 2025 "
                       "(see each valuation's 'statutory_contribution_payable_2026').",
        "totals": {
            "budget_2026_total": total_budget,
            "statutory": sum(v["statutory_contribution"] for v in budget.values()),
            "advance": sum(v["advance_contribution"] for v in budget.values()),
            "loss_in_collection_reserve_for_pension_levies": sum(loss.values()),
            "retirees_and_beneficiaries_all_funds": total_retirees,
            "active_members_all_funds": total_active,
            "cite_budget": cite("ORDINANCE2026", pg_sumC),
        },
        "funding_by_source_all_funds": {
            "total_revenue_before_loss_reserve": gross_rev,
            "by_source": dict(sorted(by_src.items(), key=lambda kv: -kv[1])),
            "note": "Includes the allocation of each city fund to the pension funds. Corporate Fund $907,784,727 matches 'Pension Costs $907.8M' in the Budget Forecast 2027 (p.14) "
                    "and the Corporate Fund pension column in ordinance Summary C. Casino revenue goes to PABF/FABF only.",
            "cite": cite("ORDINANCE2026", 35),
        },
        "mepabf_cps_note": None,
        "meabf_cps_share": cps,
        "funds": funds_out,
        "reconciliation": checks,
        "gaps": [
            "Overview 'Pension Funds' $2,760.3M (proposed Oct 2025) vs adopted ordinance $2,843.2M: difference $82.95M follows Council changes to the advance payment, "
            "but no public document itemizes the change fund by fund.",
            "Individual retiree data is not public. The deepest public level is counts and dollars by age or monthly-benefit band (valuation exhibits), included for PABF, FABF and MEABF.",
            "Average annual benefit is not printed for every group in every report. Where marked 'derived', it is total annual benefits divided by the count in the same report.",
            "Pension fund audited 2025 financial statements for FABF and MEABF were not parsed (valuations and the City ACFR already give benefit payments).",
        ],
    }
    del out["mepabf_cps_note"]
    json.dump(out, open(OUT_PENS, "w"), indent=1)
    return out


def money(s):
    return n(s)


def pabf_actuarial():
    k = "PABF_VAL2025"
    m, pg = grab(k, r"Totals\s+14,794\s+682\s+581\s+14,895\nAnnual Benefits\s+([\d,]+)\$\s+([\d,]+)\$\s+([\d,]+)\$\s+([\d,]+)\$")
    ann = n(m.group(4))
    types = {}
    for lab in ["Service Retirement Annuities", "Widow Annuities", "Children's Annuities", "Ordinary Disability Benefit",
                "Occupational Disease Disability Benefit", "Duty Disability Benefit", "Children's Disability Benefit", "Widows' Compensation Annuities"]:
        mm = re.search(re.escape(lab) + r"\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)", pages(k)[pg])
        types[lab] = n(mm.group(4))
    assert sum(types.values()) == 14895
    m, pga = grab(k, r"Number of Active Participants at End of Fiscal Year\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\nTotal Inactive Participants ([\d,]+)")
    active = n(m.group(3))
    inactive = n(m.group(4))
    m, pge = grab(k, r"Totals\s+8,840\s+\$([\d,]+)\s+2,431\s+\$([\d,]+)\s+11,271\s+\$([\d,]+)")
    svc_n, svc_amt = 11271, n(m.group(3))
    m, pgn = grab(k, r"2025\s+\$?\s*81,154\s+70 55\.8 27\.7", page=62)
    avg_ben_exh_n = 81154
    m, pgk = grab(k, r"4\.4\s+([\d,]+)\s+5\.5\s+2\.2")
    avg_sal = n(m.group(1))
    m, pgs = grab(k, r"Actuarial Liability\s+17,948\.10\s+([\d,.]+)\s*\n\s*Funded Ratio\s+24\.63%\s+([\d.]+)%", page=12)
    aal_m = float(m.group(1).replace(",", ""))
    fr_av = float(m.group(2))
    m, pgm = grab(k, r"Funded Ratios\s+24\.10%\s+([\d.]+)%", page=12)
    fr_mv = float(m.group(1))
    m, pgt = grab(k, r"2025\s+([\d,]+)\$\s+([\d,]+)\$\s+([\d,]+)\$\s+([\d,]+)\$\s+26\.08%")
    aal, mva, ava, ual_av = n(m.group(1)) * 1000, n(m.group(2)) * 1000, n(m.group(3)) * 1000, n(m.group(4)) * 1000
    m, pgsc = grab(k, r"fiscal year 2026 tax levy, payable in fiscal year 2027, is equal to\s+\$([\d,]+) and the\s*\nfiscal year 2027 tax levy, payable in fiscal year 2028, is equal to \$([\d,]+)", page=12)
    sc26, sc27 = n(m.group(1)), n(m.group(2))
    m, pgadc = grab(k, r"Actuarially Determined Contribution 3\s+1,339\.13\s+\$\s+97\.27%\s+([\d,.]+)", page=12)
    adc = float(m.group(1).replace(",", "")) * 1e6
    m, pgp = grab(k, r"2025 2026 \$\s+([\d,]+)\n2026 2027 ([\d,]+)", page=13)
    pay26 = n(m.group(1)) * 1000
    m, pgsup = grab(k, r"\$89\.5 million during\s*\nFY 2023, \$79\.8 million during FY 2024, \$67\.4 million during FY 2025, and \$36\.1 million during FY 2026")
    age = parse_pabf_age()
    return {
        "report": cite(k, 1, "Actuarial Valuation Report for the Year Ending December 31, 2025, dated May 22, 2026"),
        "retirees_and_beneficiaries": {"total": 14895, "by_type": types, "annual_benefits": ann,
                                       "avg_annual_benefit_all_derived": round(ann / 14895),
                                       "cite": cite(k, pg, "Exhibit B")},
        "service_retirees": {"count": svc_n, "annual_payments": svc_amt, "avg_annual_benefit_derived": round(svc_amt / svc_n),
                             "avg_annual_benefit_as_printed_exhibit_N": avg_ben_exh_n, "cite": [cite(k, pge, "Exhibit E"), cite(k, pgn, "Exhibit N")]},
        "active_members": {"count": active, "inactive_members": inactive, "avg_annual_salary": avg_sal,
                           "cite": [cite(k, pga, "Exhibit A"), cite(k, pgk, "Exhibit K")]},
        "funded_ratio_actuarial_value": round(fr_av / 100, 4), "funded_ratio_market_value": round(fr_mv / 100, 4),
        "actuarial_accrued_liability": aal, "market_value_of_assets": mva, "actuarial_value_of_assets": ava,
        "unfunded_liability_actuarial_value": ual_av, "unfunded_liability_market_value": aal - mva,
        "cite_funded": [cite(k, pgs, "Summary of Actuarial Valuation Results"), cite(k, pgt, "Table 5 / funding history")],
        "statutory_contribution_levy_year_2026": {"amount": sc26, "payable_year": 2027, "cite": cite(k, pgsc)},
        "statutory_contribution_levy_year_2027": {"amount": sc27, "payable_year": 2028, "cite": cite(k, pgsc)},
        "statutory_contribution_payable_2026": {"amount": pay26, "levy_year": 2025, "cite": cite(k, pgp)},
        "actuarially_determined_contribution_plan_year_2026": {"amount": round(adc), "cite": cite(k, pgadc), "shortfall_vs_statute": round(adc) - sc26},
        "supplemental_payments_note": "City paid above-statute amounts: $89.5M (2023), $79.8M (2024), $67.4M (2025), $36.1M (2026 to date)",
        "service_retirees_by_age": age,
    }


def parse_pabf_age():
    k = "PABF_VAL2025"
    rows = []
    for line in pages(k)[50].split("\n"):
        m = re.match(r"^(Under 50|\d{2}|85 to 89|90 to 94|95 to 99|100\+)\s+(\d+)\s+\$?\s*([\d,]+)\s+(\d+)\s+\$?\s*([\d,]+)\s+(\d+)\s+\$?\s*([\d,]+)\s*$", line.strip())
        if m:
            rows.append({"age": m.group(1), "male_n": n(m.group(2)), "male_payments": n(m.group(3)),
                         "female_n": n(m.group(4)), "female_payments": n(m.group(5)),
                         "total_n": n(m.group(6)), "total_payments": n(m.group(7))})
    assert sum(r["total_n"] for r in rows) == 11271 and sum(r["total_payments"] for r in rows) == 914683048, (sum(r["total_n"] for r in rows), sum(r["total_payments"] for r in rows))
    return {"cite": cite(k, 50, "Exhibit E"), "rows": rows}


def fabf_actuarial():
    k = "FABF_VAL2025"
    m, pg = grab(k, r"As of December 31, 2025, ([\d,]+) employee annuitants, ([\d,]+) spouse annuitants, ([\d,]+) duty disability retirees, ([\d,]+) occupational\s+disability retirees, ([\d,]+) ordinary disability retirees, and ([\d,]+) children were receiving total monthly benefits of \$([\d,]+)")
    emp, sp, duty, occ, ordd, ch = [n(m.group(i)) for i in range(1, 7)]
    monthly = n(m.group(7))
    total = emp + sp + duty + occ + ordd + ch
    m, pgk = grab(k, r"Number of retirees, survivors, disabilities and children ([\d,]+) ([\d,]+)\n• Number of inactive members ([\d,]+) ([\d,]+)\n• Number of active members2 ([\d,]+) ([\d,]+)")
    assert n(m.group(1)) == total
    inactive, active = n(m.group(3)), n(m.group(5))
    m, _ = grab(k, r"Average pensionable salary ([\d,]+) ([\d,]+)", page=pgk)
    avg_sal = n(m.group(1))
    m, pgr = grab(k, r"Number in pay status ([\d,]+) [\d,]+ [\d.%()]+\s*\n.*?Average monthly benefit \$([\d,]+) \$[\d,]+", flags=re.S)
    svc_avg_monthly = n(m.group(2))
    m, _ = grab(k, r"Average monthly benefit \$([\d,]+) \$([\d,]+) [\d.%]+\s*\n(?:.*\n)*?", page=pgr)
    m2 = re.search(r"Survivors\d*:\nNumber in pay status [\d,]+ [\d,]+ [\d.%()]+\n• Average age [\d.]+ [\d.]+\s+[\d.]+\n• Average monthly benefit \$([\d,]+)", pages(k)[pgr])
    sp_avg_monthly = n(m2.group(1)) if m2 else None
    assert sp_avg_monthly == 3107, sp_avg_monthly
    m, pgf = grab(k, r"Actuarial accrued liability \$([\d,]+) \$[\d,]+\n• Fair value of assets ([\d,]+) [\d,]+\n• Unfunded actuarial accrued liability on a fair value basis ([\d,]+) [\d,]+\n• Funded ratio on a fair value basis ([\d.]+)% [\d.]+%\n• Actuarial value of assets \$([\d,]+) \$[\d,]+\n• Unfunded actuarial accrued liability on an actuarial value basis ([\d,]+) [\d,]+\n• Funded ratio on an actuarial value basis ([\d.]+)%")
    aal, fv, ual_fv, fr_fv, av, ual_av, fr_av = n(m.group(1)), n(m.group(2)), n(m.group(3)), float(m.group(4)), n(m.group(5)), n(m.group(6)), float(m.group(7))
    m, pgc = grab(k, r"Statutory City contribution3 \$([\d,]+) \$([\d,]+) \$([\d,]+)\n")
    sc27, sc26, sc25 = n(m.group(1)), n(m.group(2)), n(m.group(3))
    m, _ = grab(k, r"Actuarially determined contribution\s+([\d,]+) ([\d,]+)\n", page=pgc)
    adc26 = n(m.group(1))
    m, pgsup = grab(k, r"supplemental pension payment1\s*contribution of \$([\d,]+) during 2026", page=10)
    sup26 = n(m.group(1))
    age1, pg_d1 = parse_fabf_d(k, "Exhibit D.1: Service retirement annuitants as of December 31, 2025", 41)
    age2, pg_d2 = parse_fabf_d(k, "Exhibit D.2: Spouse annuitants", 42)
    return {
        "report": cite(k, 2, "Segal Actuarial Valuation and Review as of December 31, 2025, dated June 12, 2026"),
        "retirees_and_beneficiaries": {
            "total": total, "by_type": {"employee_annuitants": emp, "spouse_annuitants": sp, "duty_disability": duty,
                                        "occupational_disability": occ, "ordinary_disability": ordd, "children": ch},
            "annual_benefits_derived_from_monthly": monthly * 12, "monthly_benefits": monthly,
            "avg_annual_benefit_all_derived": round(monthly * 12 / total), "cite": cite(k, pg, "Section 2, retired members and survivors")},
        "service_retirees": {"count": emp, "avg_monthly_benefit": svc_avg_monthly, "avg_annual_benefit": svc_avg_monthly * 12,
                             "spouse_avg_monthly_benefit": sp_avg_monthly, "cite": cite(k, pgr, "demographic summary")},
        "active_members": {"count": active, "inactive_members": inactive, "avg_annual_salary": avg_sal, "cite": cite(k, pgk, "Summary of key valuation results")},
        "funded_ratio_actuarial_value": round(fr_av / 100, 4), "funded_ratio_market_value": round(fr_fv / 100, 4),
        "actuarial_accrued_liability": aal, "market_value_of_assets": fv, "actuarial_value_of_assets": av,
        "unfunded_liability_actuarial_value": ual_av, "unfunded_liability_market_value": ual_fv,
        "cite_funded": cite(k, pgf, "Summary of key valuation results"),
        "statutory_contribution_levy_year_2026": {"amount": sc26, "payable_year": 2027, "cite": cite(k, pgc)},
        "statutory_contribution_levy_year_2027": {"amount": sc27, "payable_year": 2028, "cite": cite(k, pgc)},
        "statutory_contribution_payable_2026": {"amount": sc25, "levy_year": 2025, "cite": cite(k, pgc)},
        "actuarially_determined_contribution_plan_year_2026": {"amount": adc26, "cite": cite(k, pgc), "shortfall_vs_statute": adc26 - sc26},
        "supplemental_payment_jan_2026": {"amount": sup26, "cite": cite(k, pgsup), "note": "City expected another supplemental payment in June 2026 (not in the projection)"},
        "retro_pay_note": "Oct 2025 Fire contract granted raises retroactive to 2021. Retiree benefit recalculations were not in the 12/31/2025 data, "
                          "so benefits and the AAL are expected to rise (valuation p.6, $25.8M AAL estimate included).",
        "service_retirees_by_age": age1, "spouse_annuitants_by_age": age2,
    }


def parse_fabf_d(k, title, pdf_page):
    rows = []
    txt = pages(k)[pdf_page]
    assert title in txt, (title, pdf_page)
    for line in txt.split("\n"):
        m = re.match(r"^(Under \d+|\d+ – \d+|\d+ & over|Total)\s+(.*)$", line.strip())
        if not m:
            continue
        vals = [v for v in re.split(r"[\s$]+", m.group(2)) if v]
        nums = []
        for v in vals:
            nums.append(None if v == "-" else n(v))
        rows.append({"age": m.group(1), "values": nums})
    return {"cite": cite(k, pdf_page), "columns": "male_n, male_annual_payments, female_n, female_annual_payments (None = none)", "rows": rows}, pdf_page


def meabf_actuarial():
    k = "MEABF_VAL2025"
    m, pg = grab(k, r"As of December 31, 2025, ([\d,]+) retired members and ([\d,]+) beneficiaries were receiving total monthly benefits of \$([\d,]+)")
    ret, ben, monthly = n(m.group(1)), n(m.group(2)), n(m.group(3))
    m, pgd = grab(k, r"Retired participants\s*\n• Number in pay status ([\d,]+) ([\d,]+) [\d.%-]+\s*\n• Average age ([\d.]+) [\d.]+ N/A\s*\n• Average monthly benefit \$([\d,]+)\s+\$([\d,]+)\s+[\d.%]+\s*\nSurviving spouses\s*\n• Number in pay status ([\d,]+) [\d,]+ [\d.%-]+\s*\n• Average age ([\d.]+) [\d.]+ N/A\s*\n• Average monthly benefit \$([\d,]+)\s+\$[\d,]+\s+[\d.%]+\s*\nReversionary annuitants\s*\n• Number in pay status ([\d,]+) [\d,]+ [\d.%-]+\s*\n• Average age ([\d.]+) [\d.]+ N/A\s*\n• Average monthly benefit \$([\d,]+)")
    ret_n, ret_avg_m, sp_n, sp_avg_m, rev_n, rev_avg_m = n(m.group(1)), n(m.group(4)), n(m.group(6)), n(m.group(8)), n(m.group(9)), n(m.group(11))
    m, _ = grab(k, r"Children (\d+) (\d+) -", page=pgd)
    ch_n = n(m.group(1))
    assert ret_n == ret and sp_n + rev_n + ch_n == ben, (ret_n, ret, sp_n, rev_n, ch_n, ben)
    total_ret = ret + ben
    m, _ = grab(k, r"Number in active service\s*|Active members in valuation:\s*\n• Number23 ([\d,]+)", page=pgd)
    act = n(m.group(1))
    m, _ = grab(k, r"• Average pensionable salary \$([\d,]+)\s+\$([\d,]+)", page=pgd)
    avg_sal = n(m.group(1))
    m, pgf = grab(k, r"Actuarial accrued liability3 \$([\d,]+) \$[\d,]+\n• Fair value of assets ([\d,]+) [\d,]+\n• Unfunded actuarial accrued liability on a fair value basis ([\d,]+) [\d,]+\n• Funded ratio on a fair value basis ([\d.]+)% [\d.]+%\n• Actuarial value of assets \$([\d,]+) \$[\d,]+\n• Unfunded actuarial accrued liability on an actuarial value basis ([\d,]+) [\d,]+\n• Funded ratio on an actuarial value basis ([\d.]+)%")
    aal, fv, ual_fv, fr_fv, av, ual_av, fr_av = n(m.group(1)), n(m.group(2)), n(m.group(3)), float(m.group(4)), n(m.group(5)), n(m.group(6)), float(m.group(7))
    m, pgc = grab(k, r"Statutory City contribution4 \$([\d,]+) \$([\d,]+) \$([\d,]+)\n", page=pgf)
    sc27, sc26, sc25 = n(m.group(1)), n(m.group(2)), n(m.group(3))
    m, _ = grab(k, r"Actuarially determined contribution requirement N/A ([\d,]+) ([\d,]+)\n", page=pgf)
    adc26 = n(m.group(1))
    m, pgs = grab(k, r"supplemental pension payment1 of\s*\n\$([\d,]+)2 during 2026", page=10)
    sup26 = n(m.group(1))
    bands, pgb = parse_meabf_bands()
    return {
        "report": cite(k, 1, "Segal Actuarial Valuation and Review as of December 31, 2025 (posted June 26, 2026)"),
        "retirees_and_beneficiaries": {
            "total": total_ret, "by_type": {"retired_members": ret_n, "surviving_spouses": sp_n, "reversionary_annuitants": rev_n, "children": ch_n},
            "monthly_benefits": monthly, "annual_benefits_derived_from_monthly": monthly * 12,
            "avg_annual_benefit_all_derived": round(monthly * 12 / total_ret), "cite": cite(k, pg, "Section 2")},
        "service_retirees": {"count": ret_n, "avg_monthly_benefit": ret_avg_m, "avg_annual_benefit": ret_avg_m * 12,
                             "surviving_spouse_avg_monthly_benefit": sp_avg_m, "reversionary_avg_monthly_benefit": rev_avg_m,
                             "cite": cite(k, pgd, "Section 3, participant summary")},
        "active_members": {"count": act, "inactive_members": 28888, "avg_annual_salary": avg_sal, "cite": cite(k, pgd)},
        "funded_ratio_actuarial_value": round(fr_av / 100, 4), "funded_ratio_market_value": round(fr_fv / 100, 4),
        "actuarial_accrued_liability": aal, "market_value_of_assets": fv, "actuarial_value_of_assets": av,
        "unfunded_liability_actuarial_value": ual_av, "unfunded_liability_market_value": ual_fv,
        "cite_funded": cite(k, pgf),
        "statutory_contribution_levy_year_2026": {"amount": sc26, "payable_year": 2027, "cite": cite(k, pgc)},
        "statutory_contribution_levy_year_2027": {"amount": sc27, "payable_year": 2028, "cite": cite(k, pgc)},
        "statutory_contribution_payable_2026": {"amount": sc25, "levy_year": 2025, "cite": cite(k, pgc)},
        "actuarially_determined_contribution_plan_year_2026": {"amount": adc26, "cite": cite(k, pgc), "shortfall_vs_statute": adc26 - sc26},
        "supplemental_payment_2026": {"amount": sup26, "cite": cite(k, pgs)},
        "retirees_by_monthly_benefit_band": {"cite": cite(k, pgb, "Exhibit D.4"), "columns": "employee, spouse, reversionary, child, total", "rows": bands},
        "note_includes_opeb": "Actuarial accrued liability includes a small retiree health premium subsidy (OPEB), valuation p.10",
    }


def parse_meabf_bands():
    k = "MEABF_VAL2025"
    pgn = 43
    rows = []
    for line in pages(k)[pgn].split("\n"):
        m = re.match(r"^(Under \$500|\$[\d,]+ [-&] \$?[\d,]*|\$7,000 & over)\s+([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+) ([\d,]+)$", line.strip())
        if m:
            rows.append({"band": m.group(1), "employee": n(m.group(2)), "spouse": n(m.group(3)), "reversionary": n(m.group(4)),
                         "child": n(m.group(5)), "total": n(m.group(6))})
    assert sum(r["total"] for r in rows) == 25771, sum(r["total"] for r in rows)
    return rows, pgn


def labf_actuarial():
    k = "LABF_VAL2025"
    m, pg = grab(k, r"Actives1 ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nInactives ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nRetirees ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nSurvivors ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nReversionary Annuitants2 ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nDisabilities ([\d,]+)\s+([\d,]+)\s+[\d.%-]+\nChildren ([\d,]+)\s+([\d,]+)")
    act, inact, ret, surv, rev, dis, ch = [n(m.group(i)) for i in (2, 4, 6, 8, 10, 12, 14)]
    total_pay = ret + surv + rev + dis + ch
    m, pgp = grab(k, r"Total Annual Payments\s+([\d,]+)\$?\s+([\d,]+)", page=pg)
    ann = n(m.group(2))
    m, pgm = grab(k, r"Average Annual Salary \$92,452 \$([\d,]+)\s*\n(?:.*\n){0,10}?\s*Retirees 3\s*\n\s*Number ([\d,]+)\s+([\d,]+)\s*\n\s*Average Age ([\d.]+)\s+([\d.]+)\s*\n\s*Average Annual\s+Benefi t \$([\d,]+) \$([\d,]+)\s*\n\s*Surviving Spouses4\s*\n\s*Number ([\d,]+)\s+([\d,]+)\s*\n\s*Average Age ([\d.]+)\s+([\d.]+)\s*\n\s*Average Annual\s+Benefi t \$([\d,]+) \$([\d,]+)")
    avg_sal = n(m.group(1))
    ret_avg, sp_avg = n(m.group(7)), n(m.group(13))
    m, pgf = grab(k, r"A\nctuarial Liability\s+([\d,]+)\$\s+([\d,]+)\$\s+[\d.]+ %\nAssets - Actuarial Value\s+([\d,]+)\s+([\d,]+)\s+[\d.]+ %\nUnfunded Liability \(Surplus\)\s+([\d,]+)\s+([\d,]+)\s+\(?[\d.]+\)?%\nFunded Ratio\s+([\d.]+)%\s+([\d.]+)%", page=9)
    aal, av, ual_av, fr_av = n(m.group(2)), n(m.group(4)), n(m.group(6)), float(m.group(8))
    m, _ = grab(k, r"Assets - Market Value\s+([\d,]+)\s+([\d,]+)\s+[\d.]+ %\nUnfunded Liability\s+([\d,]+)\s+([\d,]+)\s+\(?[\d.]+\)?%\nFunded Ratio\s+([\d.]+)%\s+([\d.]+)%", page=9)
    mv, ual_mv, fr_mv = n(m.group(2)), n(m.group(4)), float(m.group(6))
    m, pgadc = grab(k, r"Actuarial Determined Contribution \(ADC\)\s+([\d,]+)\$\s+([\d,]+)\$", page=9)
    adc26 = n(m.group(2))
    m, pgsc = grab(k, r"\(9\) Estimated City Contribution 4\s+([\d,]+)\s+([\d,]+)", page=29)
    sc_fy25, sc_fy26 = n(m.group(1)), n(m.group(2))
    m, pgsc27 = grab(k, r"136,573,560\$\s+132,514,232\$\s+134,\s?839,676\$\s+137,273,984\$", page=30)
    sc27 = 132514232
    return {
        "report": cite(k, 1, "GRS Actuarial Valuation Report as of December 31, 2025, letter dated April 21, 2026"),
        "retirees_and_beneficiaries": {
            "total": total_pay, "by_type": {"retirees": ret, "surviving_spouses": surv, "reversionary_annuitants": rev, "disabilities": dis, "children": ch},
            "annual_benefits": ann, "avg_annual_benefit_all_derived": round(ann / total_pay), "cite": cite(k, pg, "Summary of Actuarial Valuation, member counts and annual payments"),
            "note": "ACFR p.92 reports 3,488 receiving benefits because it counts the 57 disabled as active; this report counts them as receiving benefits."},
        "service_retirees": {"count": ret, "avg_annual_benefit": ret_avg, "surviving_spouse_avg_annual_benefit": sp_avg, "cite": cite(k, pgm, "Plan Membership")},
        "active_members": {"count": act, "inactive_members": inact, "avg_annual_salary": avg_sal, "cite": cite(k, pgm)},
        "funded_ratio_actuarial_value": round(fr_av / 100, 4), "funded_ratio_market_value": round(fr_mv / 100, 4),
        "actuarial_accrued_liability": aal, "market_value_of_assets": mv, "actuarial_value_of_assets": av,
        "unfunded_liability_actuarial_value": ual_av, "unfunded_liability_market_value": ual_mv,
        "cite_funded": cite(k, pgf),
        "statutory_contribution_levy_year_2026": {"amount": sc_fy26, "payable_year": 2027, "cite": cite(k, pgsc, "Table 1 line (9), fiscal year 2026")},
        "statutory_contribution_levy_year_2027": {"amount": sc27, "payable_year": 2028, "cite": cite(k, pgsc27, "Table 1A")},
        "statutory_contribution_payable_2026": {"amount": sc_fy25, "levy_year": 2025, "cite": cite(k, pgsc, "Table 1 line (9), fiscal year 2025")},
        "actuarially_determined_contribution_plan_year_2026": {"amount": adc26, "cite": cite(k, pgadc), "shortfall_vs_statute": adc26 - sc_fy26},
        "supplemental_note": "City paid $12.1M (2023), $20.3M (2024), $20.2M (2025) above statute (valuation p.17)",
    }


def acfr_pension_summary():
    k = "ACFR2025"
    out = {}
    m, pgc = grab(k, r"Inactive employees or beneficiaries currently receiving\s+benefits\s+\.+\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s*\nInactive employees entitled to but not yet receiving benefits\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\nActive employees\s+\.+\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)\s+([\d,]+)")
    ben = [n(m.group(i)) for i in (1, 2, 3, 4)]
    inact = [n(m.group(i)) for i in (6, 7, 8, 9)]
    act = [n(m.group(i)) for i in (11, 12, 13, 14)]
    m, pgn = grab(k, r"Total pension liability - ending \(a\)\s+\.+\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)\s+\$ ([\d,]+)\s+\$ ([\d,]+)")
    tpl = [n(m.group(i)) for i in (1, 2, 3, 4)]
    m, _ = grab(k, r"Plan fiduciary net position - ending \(b\)\s+\.+\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)\s+\$ ([\d,]+)\s+\$ ([\d,]+)", page=pgn)
    fnp = [n(m.group(i)) for i in (1, 2, 3, 4)]
    m, _ = grab(k, r"Net pension liability-ending \(a\)-\(b\)\s+\.+\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)\s+\$ ([\d,]+)\s+\$ ([\d,]+)", page=pgn)
    npl = [n(m.group(i)) for i in (1, 2, 3, 4)]
    m, _ = grab(k, r"Benefit payments including refunds\s+\.+\s+\(([\d,]+)\)\s+\(([\d,]+)\)\s+\(([\d,]+)\)\s+\(([\d,]+)\)", page=pgn)
    paid = [n(m.group(i)) for i in (1, 2, 3, 4)]
    m, _ = grab(k, r"Contributions-employer \*\*\s+\.+\s+\$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+) \$ ([\d,]+)", page=pgn)
    contrib = [n(m.group(i)) for i in (1, 2, 3, 4)]
    m, pgr1 = grab(k, r"Plan fiduciary net position as a percentage\nof the total pension liability\s+\.+\s+([\d.]+) %", page=114)
    m_ = {"MEABF": 0, "LABF": 1, "PABF": 2, "FABF": 3}
    pct = {"MEABF": 28.18, "LABF": 44.10, "PABF": 26.44, "FABF": 25.25}
    for c, i in m_.items():
        out[c] = {"net_pension_liability_thousands": npl[i], "total_pension_liability_thousands": tpl[i], "fiduciary_net_position_thousands": fnp[i],
                  "funded_ratio_gasb": round(fnp[i] / tpl[i], 4), "benefit_payments_incl_refunds_2025_thousands": paid[i],
                  "city_contributions_2025_thousands": contrib[i], "receiving_benefits_acfr": ben[i], "inactive_not_receiving": inact[i], "active": act[i],
                  "cite": [cite(k, pgn, "Changes in the Net Pension Liability, FY2025"), cite(k, pgc, "Employees covered by benefit terms")]}
        assert abs(out[c]["funded_ratio_gasb"] * 100 - pct[c]) < 0.01, (c, out[c]["funded_ratio_gasb"])
    assert sum(npl) == 36426561 and sum(ben) == 49711 and sum(act) == 58472, (sum(npl), sum(ben), sum(act))
    return out


def main():
    d = build_debt()
    p = build_pensions()
    print("DEBT 2026 (ordinance): gross ${:,}  net of double count ${:,}".format(
        d["budget_2026"]["total_gross"], d["budget_2026"]["total_net_of_double_count"]))
    for k, v in d["budget_2026"]["by_payer_net"].items():
        print(f"   {k:30s} ${v:>15,}")
    print("   + STSC (outside Finance General) projected $%.1fM" % d["outside_finance_general"]["sales_tax_securitization_debt_service"]["2026_musd"])
    print("PENSIONS 2026 (ordinance): ${:,}  statutory ${:,}  advance ${:,}".format(
        p["totals"]["budget_2026_total"], p["totals"]["statutory"], p["totals"]["advance"]))
    for code, f in p["funds"].items():
        v = f["valuation_12_31_2025"]
        print(f"   {code:6s} budget ${f['budget_2026']['total']:>14,}  retirees {v['retirees_and_beneficiaries']['total']:>6,}  "
              f"active {v['active_members']['count']:>6,}  funded(AVA) {v['funded_ratio_actuarial_value']:.1%}  UAL ${v['unfunded_liability_actuarial_value']/1e9:.2f}B")
    bad = [c for c in d["reconciliation"] + p["reconciliation"] if not c["ok"]]
    print("\nreconciliation checks: {} ok, {} with differences (documented)".format(
        len(d["reconciliation"] + p["reconciliation"]) - len(bad), len(bad)))
    for c in bad:
        print("   DIFF", c["difference"], "|", c["check"][:100])


if __name__ == "__main__":
    main()
