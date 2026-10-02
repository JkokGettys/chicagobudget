#!/usr/bin/env python3
"""Writes data/splits/city/pay_estimates.json (Tasks A and B) and data/splits/city/health_more.json (Task C).

TASK A, government estimates first
  * Police overtime 0100/57/1005/0020 ($200,000,000): CPD's own published 2026 overtime budget, from the CPD Overtime
    Dashboard (Tableau, version 260520). The 22 district budgets are pieces (gov_estimate). CPD's monthly targets and its
    January to August budget by category are side facts (they are not all in the same period as the district budgets).
    Cached by scripts/govest_cpd_tableau.py in raw/govest/cpd_dashboard_*.json and t_*.png.
  * Finance General and Fire Scheduled Wage Adjustments: no government split exists (the Budget Overview, Forecast and
    Technical Amendments name the Fire contract but give no split). Those become Task B proxies and the government
    facts that do exist are side info.
TASK B, careful proxies, only where no government split exists
  * The 2026 line is split by each job title's share of 2025 actual pay on the same account and department
    (payroll costing, data/raw leaves file). 2025 dollars are shown in the piece note, never as the piece amount.
    Titles with fewer than 5 people are pooled (pool itself has at least 5 people). No averages are shown.
TASK C, health on the other funds
  * Same method as scripts/leaves_health.py: budgeted positions of the fund (2026 positions dataset v2t2-vajc) grouped
    Fire / Police / Other union / Non-union, times EY p.46 plan enrollment shares, times an equal average per enrollee.
    Groups with fewer than 5 enrolled people are left in the residual box (no count or average shown).
Run:  python3 scripts/govest_build.py
"""
import collections
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
P = lambda *a: os.path.join(ROOT, *a)
OUT_DIR = P("data", "splits", "city")

# ---------------------------------------------------------------- sources
SRC_CPD = {"doc": "CPD Overtime Dashboard 2026 (Budget and Spending pt I, pt II, District Budgets), version 260520",
           "url": "https://www.chicagopolice.org/statistics-data/data-dashboards/overtime-dashboard/",
           "page": "tabs: District Budgets, Budget and Spending pt II. Fetched 2026-10-01 (raw/govest/cpd_dashboard_*.json, t_*.png)"}
SRC_PAYROLL = {"doc": "Employee Payroll Costing 2025 (City of Chicago data portal dawh-m56b), by appropriation, department and job title",
               "url": "https://data.cityofchicago.org/resource/dawh-m56b.json",
               "note": "PROXY: the 2026 budget line split by each job title's share of 2025 actual pay on the same account and department"}
SRC_EY = {"doc": "EY, Financial and Strategic Reform Options (City of Chicago, 2026 budget supplement), p.46 demographics and enrollment",
          "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/Financial and Strategic Reform Options - City of Chicago.pdf",
          "page": 46, "note": "PROXY: budgeted positions of the fund (positions dataset v2t2-vajc) x EY plan enrollment shares x equal average per enrollee"}


def r2(x):
    return round(x + 0.0, 2)


# ================================================================ TASK A: Police overtime from CPD's own numbers
def cpd_numbers():
    d = json.load(open(P("raw", "govest", "cpd_dashboard_DistrictBudgets.json")))
    seg = d["chunks"][1]["secondaryInfo"]["presModelMap"]["dataDictionary"]["presModelHolder"]["genDataDictionaryPresModel"]["dataSegments"]["0"]["dataColumns"]
    real = [c for c in seg if c["dataType"] == "real"][0]["dataValues"]
    cs = [c for c in seg if c["dataType"] == "cstring"][0]["dataValues"]
    codes = cs[:22]
    k = cs.index("Violent Index Crime Incidents")
    names = cs[k + 1:k + 23]
    districts = list(zip(codes, names, real[:22]))
    m = json.load(open(P("raw", "govest", "cpd_dashboard_BudgetandSpendingptII.json")))
    seg = m["chunks"][1]["secondaryInfo"]["presModelMap"]["dataDictionary"]["presModelHolder"]["genDataDictionaryPresModel"]["dataSegments"]["0"]["dataColumns"]
    real2 = [c for c in seg if c["dataType"] == "real"][0]["dataValues"]
    cs2 = [c for c in seg if c["dataType"] == "cstring"][0]["dataValues"]
    months = cs2[:12]           # December ... January
    budget_by_month = dict(zip(months, real2[:12]))
    spend = dict(zip(months[4::][:8] if False else ["August", "July", "June", "May", "April", "March", "February", "January"], real2[12:20]))
    p1 = json.load(open(P("raw", "govest", "cpd_dashboard_BudgetandSpendingptI.json")))
    seg = p1["chunks"][1]["secondaryInfo"]["presModelMap"]["dataDictionary"]["presModelHolder"]["genDataDictionaryPresModel"]["dataSegments"]["0"]["dataColumns"]
    r1 = [c for c in seg if c["dataType"] == "real"][0]["dataValues"]
    cat = {"bud_ei": r1[0], "bud_ud": r1[1], "bud_total": r1[4], "spend_ei": r1[5], "spend_ud": r1[6], "spend_total": r1[9]}
    return districts, budget_by_month, spend, cat


def ordinal_name(n):
    # "25TH DISTRICT - GRAND CENTRAL" -> "25th District: Grand Central"
    head, _, tail = n.partition(" DISTRICT - ")
    return f"{head.lower()} District: {tail.title()}"


def police_overtime_split():
    districts, bmonth, spend, cat = cpd_numbers()
    jan_aug = sum(bmonth[m] for m in ["January", "February", "March", "April", "May", "June", "July", "August"])
    assert abs(jan_aug - cat["bud_total"]) < 1, (jan_aug, cat["bud_total"])   # ties to CPD's own donut chart
    year_targets = sum(bmonth.values())
    dist_total = sum(b for _, _, b in districts)
    kids = [{"name": ordinal_name(n), "amount": r2(b), "basis": "gov_estimate", "source": SRC_CPD,
             "note": f"CPD district code {c}. CPD's chart label is '2026 District Overtime Budget'."} for c, n, b in districts]
    why_rest = ("CPD did not publish what the rest of its overtime money is planned for unit by unit. It only says part of it is for special events and "
                "projects and part is for other units, and the City reports overtime by job title, not by person.")
    side = [
        {"kind": "cpd_monthly_budget_targets", "label": "CPD's own monthly targets for the non-reimbursable, non-comp-time overtime budget (Budget and Spending pt II). "
         "They add to less than the $200M line, so part of the line has no monthly target.", "amount": r2(year_targets), "period": "2026 full year",
         "basis": "gov_estimate", "source": SRC_CPD, "items": [{"month": m, "budget": r2(bmonth[m])} for m in
                                                               ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]]},
        {"kind": "cpd_budget_by_category", "label": "CPD budget January to August 2026 by category (Budget and Spending pt I). This is a part-year figure, so it is not added into the boxes.",
         "amount": r2(cat["bud_total"]), "period": "2026 Jan-Aug", "basis": "gov_estimate", "source": SRC_CPD,
         "items": [{"category": "Unit Discretionary (districts and other units)", "budget": r2(cat["bud_ud"])},
                   {"category": "Events and Initiatives", "budget": r2(cat["bud_ei"])}]},
        {"kind": "cpd_spend_to_date", "label": "What CPD says it spent January to August 2026 on the same non-reimbursable, non-comp-time overtime (actual, estimated by CPD).",
         "amount": r2(cat["spend_total"]), "period": "2026 Jan-Aug", "basis": "paid_to_date", "source": SRC_CPD,
         "items": [{"category": "Unit Discretionary", "spend": r2(cat["spend_ud"])}, {"category": "Events and Initiatives", "spend": r2(cat["spend_ei"])}]},
        {"kind": "mid_year_report", "label": "Mid-Year Budget Report 2026 p.45: Police overtime budget $203,944,513 (all funds), $59,536,929 spent through the May accounting period (29.2%).",
         "amount": 59536929, "period": "2026 Jan-May", "basis": "paid_to_date",
         "source": {"doc": "Mid-Year Budget Report 2026 (OBM)", "page": 45, "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026Mid-YearBudgetReport.pdf"}},
        {"kind": "budget_overview_cap", "label": "Budget Overview 2026 (p.12): the 2026 budget includes a cap on police overtime. COFA (budget summary, p.13): any overtime above $200M needs City Council approval.",
         "period": "2026", "basis": "gov_estimate", "source": {"doc": "2026 Budget Overview (OBM) and COFA FY2026 Budget Recommendation Summary", "page": "Overview p.12, COFA p.13"}},
    ]
    return {
        "target": {"by": "ordinance_line", "fund": "0100", "dept": "57", "authority": "1005", "account": "0020"},
        "expect_amount": 200000000, "mode": "budget_split",
        "pieces": [{"name": "Overtime budgets of the 22 police districts", "amount": r2(dist_total), "basis": "gov_estimate", "source": SRC_CPD, "children": kids,
                    "note": "CPD published one overtime budget per district for 2026. The 22 add to $75.4M. The dashboard does not say how its district figures relate to the monthly targets, so they are shown as published."}],
        "residual": {"name": "Rest of police overtime: other units, events and projects, and money with no monthly target",
                     "why": why_rest},
        "note": "Source: CPD's own overtime dashboard. CPD's monthly targets add to $%s of the $200M, so $%s has no monthly target. 2025 actual police overtime by job title (payroll) is side info on this line, not part of the amounts." % (
            f"{year_targets:,.0f}", f"{200000000 - year_targets:,.0f}"),
        "side": side}


# ================================================================ TASK B: title-share proxies
def load_payroll():
    p = json.load(open(P("raw", "leaves", "payroll_2025_approp_dept_title.json")))
    out = collections.defaultdict(list)
    for r in p:
        acct = r["appropriation"].split(" ")[0][1:]       # A0020 -> 0020
        dept = r["department"].split(" ")[0][1:].lstrip("0")  # D57 -> 57
        out[(acct, dept)].append({"title": r["title"].split(" - ", 1)[1].title(), "code": r["title"].split(" ")[0], "amt": float(r["amt"]), "n": int(r["n"])})
    return out


def pool_titles(rows, fire_only=None):
    """Titles with >=5 people and positive pay stay; the rest pool into one box that also has >=5 people."""
    rows = [r for r in rows if fire_only is None or fire_only(r)]
    keep = [r for r in rows if r["n"] >= 5 and r["amt"] > 0]
    rest = [r for r in rows if not (r["n"] >= 5 and r["amt"] > 0)]
    keep.sort(key=lambda r: r["amt"])  # smallest first so we can pull them into the pool
    pool_amt = sum(r["amt"] for r in rest); pool_n = sum(r["n"] for r in rest); pooled = len(rest)
    while rest and pool_n < 5 and keep:
        r = keep.pop(0); rest.append(r); pool_amt += r["amt"]; pool_n += r["n"]; pooled += 1
    keep.sort(key=lambda r: -r["amt"])
    return keep, (pool_amt, pool_n, pooled)


WHY = {
    "0020": "Overtime is paid hour by hour as it happens, so the budget gives one yearly total. This box is our estimate using last year's pattern, and it is the smallest piece the public records allow.",
    "0003": "This money is set aside for pay raises and back pay under union contracts. The City has not said which workers get how much, so this box is our estimate from who was paid on this account last year.",
    "0006": "This is pay set aside for special pay arrangements. The City reports last year's actual pay by job title, so this box is our estimate from that pattern.",
    "default": "This is a yearly pay budget for one kind of extra pay. The City reports last year's actual pay by job title, so this box is our estimate from that pattern.",
}
ACCT_NAME = {"0020": "overtime", "0003": "scheduled wage adjustment pay", "0006": "salary provision pay", "0021": "holiday premium pay", "0022": "duty availability pay",
             "0024": "compensatory time payments", "0027": "supervisors quarterly payments", "0060": "specialty pay", "0088": "furlough and comp time buy-back pay",
             "0091": "uniform allowance"}


def proxy_split(payroll, fund, dept, auth, acct, amount, title_filter=None, extra_note="", side_extra=None, fire_exclude=False):
    rows = payroll.get((acct, dept))
    if not rows:
        return None
    if fire_exclude:
        rows = [r for r in rows if r["code"][1:3] not in ("87", "88")]
    keep, (pool_amt, pool_n, pooled) = pool_titles(rows, title_filter)
    base = sum(r["amt"] for r in keep) + (pool_amt if pool_amt > 0 else 0)
    if base <= 0:
        return None
    total_2025 = base
    pieces = []
    for r in keep:
        pieces.append({"name": r["title"], "share": r["amt"] / base, "a25": r["amt"], "n25": r["n"]})
    if pool_amt > 0:
        pieces.append({"name": f"Other job titles ({pooled} titles with fewer than 5 people each)", "share": pool_amt / base, "a25": pool_amt, "n25": pool_n})
    acc_name = ACCT_NAME.get(acct, "this pay")
    # allocate in cents so the pieces add up to the line exactly (the last, smallest piece takes the rounding)
    cents_total = round(amount * 100); alloc = []; used = 0
    for i, p in enumerate(pieces):
        c = round(p["share"] * cents_total) if i < len(pieces) - 1 else cents_total - used
        alloc.append(c); used += c
    out = []
    for p, c in zip(pieces, alloc):
        amt = c / 100
        d = {"name": p["name"], "amount": amt, "basis": "proxy", "source": SRC_PAYROLL,
             "note": (f"Proxy: this title paid {p['share']*100:.1f}% of all 2025 {acc_name} on this line's department, so it gets that share of the 2026 line. "
                      f"2025 actual (not 2026): ${p['a25']:,.0f} paid to {p['n25']:,} people.")}
        if amt >= 10_000_000:
            d["why"] = WHY.get(acct, WHY["default"])
        out.append(d)
    split = {"target": {"by": "ordinance_line", "fund": fund, "dept": dept, "authority": auth, "account": acct}, "expect_amount": amount,
             "mode": "budget_split", "pieces": out,
             "note": (f"Estimate, not a government split: the 2026 line is divided by each job title's share of 2025 actual {acc_name} (payroll costing, all funds of the department). "
                      f"2025 actual total used: ${total_2025:,.0f}; the 2026 line is {amount/total_2025:.2f}x that. " + extra_note).strip(),
             "side": [{"kind": "pay_2025_actual", "label": f"2025 ACTUAL {acc_name} paid, all funds of this department, by job title (not 2026). Titles with fewer than 5 people are pooled.",
                       "amount": r2(total_2025), "period": "2025", "basis": "actual", "source": SRC_PAYROLL,
                       "items": [{"title": p["name"], "paid_2025": r2(p["a25"]), "people_paid": p["n25"]} for p in pieces]}] + (side_extra or [])}
    return split


FIRE_FACTS = [
    {"kind": "gov_fire_contract", "label": "Budget Overview 2026 p.55: the City will issue general obligation debt to pay retroactive wages owed to Fire Department members under the contract settled in 2025 (raises back to 2021).",
     "period": "2026", "basis": "gov_estimate", "source": {"doc": "2026 Budget Overview (OBM)", "page": 55, "url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026BudgetOverview.pdf"}},
    {"kind": "gov_fire_borrowing", "label": "2027 Budget Forecast p.15: $166.0 million one-time borrowing in 2026 to finance one-time retroactive collective bargaining payments.",
     "amount": 166000000, "period": "2026", "basis": "gov_estimate", "source": {"doc": "2027 Budget Forecast (OBM)", "page": 15}},
    {"kind": "gov_fire_retro_total", "label": "COFA FY2026 budget summary p.13: new short-term bonds planned to cover back pay of Fire members (2021 to 2025). Council committee chair (Sun-Times, 2025-10-07): total retroactive pay $185 million, paid in 2026. This is not a split of the $98.0M line.",
     "amount": 185000000, "period": "2021-2025 raises, paid 2026", "basis": "gov_estimate",
     "source": {"doc": "COFA FY2026 Budget Recommendation Summary p.13; Chicago Sun-Times 2025-10-07 (cached raw/govest/news_city-council-committee-ratification-firefighter-co.txt)"}},
    {"kind": "gov_fire_contract_terms", "label": "Local 2 contract (Council ordinance O2025-0019993, approved 2025-10-16): six-year deal, raises about 3% a year on average (21% to 25% over the term), $2,500 bonus. The term sheet in the ordinance is a scanned image and was cached but not read (raw/govest/local2_ordinance_term_sheet.pdf).",
     "period": "2021-2027", "basis": "gov_estimate", "source": {"doc": "Chicago Sun-Times / WTTW coverage of ordinance O2025-0019993", "url": "https://news.wttw.com/2025/10/16/chicago-city-council-approves-new-firefighters-union-contract"}},
    {"kind": "technical_amendment", "label": "Technical Amendments passed 2025-12-22 (p.L-22 and L-43) moved $104.7M of Scheduled Wage Adjustments from Finance General into the Fire Department lines ($97,974,157 Corporate, $5,303,224 O'Hare, $1,452,422 Midway).",
     "amount": 97974157, "period": "2026", "basis": "gov_estimate", "source": {"doc": "Technical Amendments, passed December 22, 2025", "page": "L-22 (Fire), L-43 (Finance General)"}},
]


def pay_splits():
    payroll = load_payroll()
    s = [police_overtime_split()]
    # Fire overtime (no government split by unit exists: Mid-Year Report p.45 gives department totals only)
    fire_ot = proxy_split(payroll, "0100", "59", "2005", "0020", 86400000,
                          extra_note="The Mid-Year Budget Report 2026 p.45 gives Fire only as one total ($93.4M all funds). COFA (midyear, p.30) says Fire paid $90.94M overtime in 2025, $8.33M of it to the Firefighter/Paramedic title.")
    s.append(fire_ot)
    # Scheduled Wage Adjustments
    fg = proxy_split(payroll, "0100", "99", "2005", "0003", 262287301, fire_exclude=True,
                     extra_note="Fire titles are left out because the Technical Amendments moved the Fire contract money into the Fire Department's own line. The 2026 line is far bigger than last year's matching pay, so treat these shares as rough. The Budget Overview p.34 and p.39 say the line covers contractual, prevailing rate and other wage increases for union and non-union workers as the last contracts are settled.",
                     side_extra=FIRE_FACTS[-1:])
    s.append(fg)
    # Coordinator rule: the 2025 matching pay ($28.3M) is only about 1/9 of this $262.3M line, so its job-title
    # shares are too weak to show as boxes. Keep them as side info, labelled, and leave the line whole.
    if fg:
        fg["side"] = [{"kind": "rough_shares_2025", "basis": "proxy", "period": "2025",
                       "label": "Rough guide only (not boxes): who was paid on this account in 2025, by job title. "
                                "2025 pay was about 1/9 of this 2026 line, so these shares may not match where the 2026 money goes.",
                       "items": [{"name": p["name"], "amount_2026_if_same_share": p["amount"]} for p in fg["pieces"]]}] + fg.get("side", [])
        fg["mode"] = "side_only"
        fg["pieces"] = []
    fire3 = proxy_split(payroll, "0100", "59", "2005", "0003", 97974157, title_filter=lambda r: r["code"][1:3] in ("87", "88") or True,
                        extra_note="2025 pay on this account to Fire titles was contract back pay and lump sums (payroll costing), so the 2025 shares are a rough guide to who the 2026 money goes to.",
                        side_extra=FIRE_FACTS)
    # 2025 Fire A0003 pay sits under Finance General (department 99), not Fire: reuse the Fire titles from there
    rows99 = [r for r in payroll[("0003", "99")] if r["code"][1:3] in ("87", "88")]
    payroll[("0003", "59")] = rows99
    fire3 = proxy_split(payroll, "0100", "59", "2005", "0003", 97974157,
                        extra_note="The 2025 pay on this account to Fire titles was booked under Finance General: it was contract back pay and lump sums (payroll costing). Those 2025 shares are a rough guide to who the 2026 money goes to.",
                        side_extra=FIRE_FACTS)
    s.append(fire3)
    # other big pay lines (>= $10M, Corporate Fund)
    for dept, auth, acct, amt in [("57", "1005", "0022", 39000000), ("57", "1005", "0024", 36000000), ("57", "1005", "0091", 21500000),
                                  ("57", "1005", "0088", 20000000), ("57", "1005", "0060", 16100000), ("57", "1005", "0027", 12250000),
                                  ("59", "2005", "0021", 23045000), ("59", "2005", "0060", 18102553), ("59", "2005", "0022", 17993000)]:
        sp = proxy_split(payroll, "0100", dept, auth, acct, amt)
        if sp:
            s.append(sp)
    sp = proxy_split(payroll, "0740", "85", "2015", "0020", 19827682)
    if sp:
        s.append(sp)
    return [x for x in s if x]


# ================================================================ TASK C: health on the other funds
EY = {"Fire": (4715, .85, .09), "Police": (9970, .83, .12), "Other union": (13834, .72, .15), "Non-union": (3492, .71, .08)}
UNIT_GROUP = {}
for u in ("80", "87", "89"): UNIT_GROUP[u] = "Fire"
for u in ("91", "71", "73", "75"): UNIT_GROUP[u] = "Police"
for u in ("0", "9", "10", "20", "99"): UNIT_GROUP[u] = "Non-union"


def fund_positions():
    pos = json.load(open(P("raw", "city_positions_2026.json")))
    out = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in pos:
        if r["position_control"] != "1" or r["fund_type"] != "LOCAL":
            continue
        out[r["fund_code"]][UNIT_GROUP.get(r["bargaining_unit"], "Other union")] += float(r["total_budgeted_unit"])
    return out


def health_splits():
    fp = fund_positions()
    app = json.load(open(P("raw", "city_appropriations_2026.json")))
    res = []
    for acct, idx, label, why in [("0042", 1, "PPO and other medical (self-insured plan)", "The City pays hospital and doctor bills as they come in, and it does not publish what each worker's claims cost."),
                                  ("0029", 2, "HMO premiums (partially insured plan)", "The City pays the health plan one monthly price per worker, and the price list is not published.")]:
        for r in app:
            if r["appropriation_account"] != acct or r["department_number"] != "99" or r["fund_code"] == "0100":
                continue
            amt = int(r["_ordinance_amount_"])
            if amt < 1_000_000 or r["fund_code"] not in fp:
                continue
            enr = {g: round(n * EY[g][idx]) for g, n in fp[r["fund_code"]].items() if g in EY}
            tot = sum(enr.values())
            if not tot:
                continue
            avg = amt / tot
            pieces = []
            amt_c = amt * 100
            used_c = 0
            groups = [(g, n) for g, n in sorted(enr.items(), key=lambda x: -x[1]) if n >= 5]
            for i, (g, n) in enumerate(groups):
                # allocate in whole cents with the remainder on the last group, so pieces never exceed the line
                c = round(n * avg * 100) if i < len(groups) - 1 or sum(x[1] for x in groups) != tot else amt_c - used_c
                c = min(c, amt_c - used_c)
                used_c += c
                d = {"name": f"{g}: {n:,} enrolled employees x ${avg:,.0f}", "amount": c / 100, "basis": "proxy", "source": SRC_EY, "count": n,
                     "unit_amount": round(avg), "unit_label": "enrolled employees",
                     "note": f"Proxy: {n:,} budgeted positions in this fund's {g} group enrolled (EY p.46 shares) x an equal average of ${avg:,.0f}. Employees only, not family members."}
                if amt * n / tot >= 10_000_000:
                    d["why"] = why
                pieces.append(d)
            res.append({"target": {"by": "ordinance_line", "fund": r["fund_code"], "dept": "99", "authority": r["appropriation_authority"], "account": acct},
                        "expect_amount": amt, "mode": "budget_split", "pieces": pieces,
                        "residual": {"name": "Other / groups with fewer than 5 enrolled workers", "why": why},
                        "note": f"{label}: estimate, not a rate sheet. Counts come from this fund's budgeted positions grouped as Fire, Police, Other union and Non-union, times EY's plan enrollment shares (citywide), with an equal average per enrollee. Enrolled in this fund: {tot:,}.",
                        "side": [{"kind": "health_enrollment_basis", "label": "Budgeted positions in this fund by group (2026 positions dataset), before applying enrollment shares",
                                  "period": "2026", "basis": "budget", "source": SRC_EY,
                                  "items": [{"group": g, "positions": n} for g, n in sorted(fp[r["fund_code"]].items(), key=lambda x: -x[1]) if n >= 5]}]})
    return res


def write(name, desc, splits):
    meta = {"author": "gov-estimates agent", "description": desc, "built_by": "scripts/govest_build.py"}
    json.dump({"meta": meta, "splits": splits}, open(os.path.join(OUT_DIR, name), "w"), indent=1)
    print(name, len(splits), "splits")


if __name__ == "__main__":
    os.makedirs(OUT_DIR, exist_ok=True)
    write("pay_estimates.json", "Police overtime from CPD's own published budget (gov_estimate), plus careful title-share proxies for Fire overtime, Scheduled Wage Adjustments and other big pay lines. 2025 actuals are in notes and side info, never as 2026 amounts.", pay_splits())
    write("health_more.json", "Health lines of the other funds, same method as data/leaves_health.json (EY p.46 enrollment shares x fund positions x equal average).", health_splits())
