#!/usr/bin/env python3
"""Inventory every leaf >= $10M in the three budgets (City, CPS, Park District) and say what could split it.

Run:  python3 scripts/leaves_fetch.py   (once, payroll costing aggregate into raw/leaves/)
      python3 scripts/leaves_inventory.py
Output: data/leaves_over_10m.json  plus totals printed to the screen.

"Before" = the best tree the team has today, with no splits applied:
  City : raw/city_appropriations_2026.json (6694-f78c) with the finance_general.py transfer rule applied.
  CPS  : raw/cps/cps_2026_exp_unit_fund_program_account.csv (|amount| >= $10M, negative offsets included).
  Parks: data/parks_2026.json tree leaves.
"After" applies only splits the team already built (never new numbers):
  split_tied    ties to the dollar and every piece (or "count x average") is under $10M
  split_proxy   count x average or vendor/award list from a different basis (2025 pay, benefit rolls, 2025 payments)
  split_partial some pieces are still >= $10M, those pieces are counted as the remaining leaves
  unsplit_*     nothing usable yet
Round 3 additions:
  accepted_single_obligation  one bond series (or one loan) x principal or interest: already the lowest level, accepted even if >= $10M
  data/leaves_*.json          override files written by scripts/leaves_*.py (each record names its leaf with match_path_contains)
  data/city_bond_series_2026.json (other agent) is ingested when present
"""
import csv, json, os, re, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from finance_general import classify  # noqa: E402

T = 10_000_000
D = lambda p: json.load(open(os.path.join(ROOT, p)))
leaves = []


def add(budget, path, amount, source, status, remaining=None, note="", explain="", group_cap=None):
    """remaining = list of {name, amount} pieces still >= $10M after the split (for partial splits)."""
    leaves.append({"budget": budget, "path": path, "amount": amount, "split_source": source,
                   "status": status, "remaining_pieces_over_10m": remaining or [],
                   "note": note, "why_cant_go_deeper": explain, **({"group_cap": group_cap} if group_cap else {})})


# ------------------------------------------------------------------ City
ords = D("raw/city_appropriations_2026.json")
pers = D("data/city_personnel_2026.json")
vend = D("data/city_vendors_items_2025.json")
cov = D("data/city_vendors_coverage_2026.json")
grants = D("data/city_grants_2026.json")
debt = D("data/debt_2026.json")
pens = D("data/pensions_2026.json")
payroll = json.load(open(f"{ROOT}/raw/leaves/payroll_2025_approp_dept_title.json"))

from contracts_build import account_family  # noqa: E402

# salary tree rows by (dept number, fund)
sal_rows = defaultdict(list)
def walk(n, dept=None):
    if n["level"] == "department":
        dept = n["code"]
    if n["level"] == "title":
        for r in n["rows"]:
            sal_rows[(dept, r["fund"])].append((n["name"], r))
    for c in n.get("children", []):
        walk(c, dept)
walk(pers["tree"])

# premium pay (payroll costing 2025): (dept number, account) -> employees, dollars, rows
prem = defaultdict(lambda: {"amt": 0.0, "titles": 0, "max_title": 0.0, "n_max": 0})
for r in payroll:
    dn = str(int(re.match(r"D(\d+)", r["department"]).group(1)))
    ac = re.match(r"A(\w+)", r["appropriation"]).group(1)
    p = prem[(dn, ac)]
    a = float(r["amt"]); p["amt"] += a; p["titles"] += 1
    if a > p["max_title"]: p["max_title"] = a; p["n_max"] = int(r["n"])

# vendor items grouped by (dept number, family)
name2num = {d["name"]: d["dept"] for d in cov["departments"]}
items_by = defaultdict(list)
for _, d in vend["departments"].items():
    num = name2num.get(d["name"])
    for fam, its in d["families"].items():
        for it in its:
            items_by[(num, fam)].append(it)
budget_by = defaultdict(float)
rows = []
deducted = []
for r in ords:
    a = int(r["_ordinance_amount_"])
    tr = False
    if r["department_description"] == "Finance General":
        tr = classify(r["appropriation_account_description"], r["fund_description"])[2]
    if tr:
        continue
    # Round 3: remove the OTHER named pieces of OBM's printed deduction (research/reconciliation.md section 3, research/transfer_residual.md):
    #  Library term notes (proceeds of debt, printed separately), matching grant funds (ordinance p.557 says inside the deduction),
    #  Finance General "Transfer ..." lines, Appendix A and B "For Services Provided by ..." lines. The remaining $116,988,502 is NOT attributable to any line.
    desc = r["appropriation_account_description"]
    if (r["appropriation_account"] == "0961" and "Library" in r["fund_description"]) or desc.startswith("To Provide for Matching and Supplementary Grant") \
       or (r["department_description"] == "Finance General" and desc.startswith("Transfer")) \
       or (r["department_description"] != "Finance General" and desc.startswith("For Services Provided by")):
        deducted.append((a, r["fund_description"], r["department_description"], desc[:60]))
        continue
    kind, fam = account_family(r["appropriation_account"])
    rows.append((a, r, kind, fam))
    if kind == "vendor":
        budget_by[(r["department_number"], fam)] += a
city_before_total = sum(a for a, *_ in rows)

# reserve attribution lines keyed by fund/dept/authority
res = {(l["fund_code"], l["dept_number"].lstrip("0"), l["authority_code"]): l for l in grants["reserve_attribution"]["lines"]}
# map ordinance fund names to 925x codes through the grants list
fundcode = {}
for g in grants["grants"]:
    fundcode[(g["dept_number"].lstrip("0"), g["authority_code"])] = g["fund_code"]

PREM_ACCTS = {"0020", "0021", "0022", "0024", "0060", "0088", "0027", "0091", "0003", "0006", "0015"}
HEALTH = {"0042", "0029"}
pool_cache = {}

def pooled(fam):
    """Citywide vendor items for a family (used for health care paid by Finance and judgments paid via Finance General)."""
    if fam not in pool_cache:
        its = []; b = 0.0
        for (dn, f), x in items_by.items():
            if f == fam: its.extend(x)
        for (dn, f), v in budget_by.items():
            if f == fam: b += v
        pool_cache[fam] = (its, b)
    return pool_cache[fam]

big = [(a, r, k, f) for a, r, k, f in rows if a >= T]
group_l10 = defaultdict(float)
for a, r, k, f in big:
    if k == "vendor":
        group_l10[(r["department_number"], "POOL:" + f if f in ("BENEFITS", "LEGAL") else f)] += a

pending = defaultdict(list)
for a, r, kind, fam in sorted(big, key=lambda x: -x[0]):
    dn = r["department_number"]; ac = r["appropriation_account"]
    path = f"City > {r['fund_type'].title()} > {r['fund_description']} > {r['department_description']} > {r['appropriation_authority_description']} > {ac} {r['appropriation_account_description'][:60]}"
    # 1. payroll salaries
    if ac == "0005":
        rr = sal_rows.get((dn, r["fund_code"]))
        if rr:
            add("City", path, a, "data/city_personnel_2026.json (positions dataset v2t2-vajc, ties to the dollar incl. turnover)",
                "split_tied", note="count x average per job title and pay rate row; largest row 2,148 Police Officers x $111,252")
            continue
    # 2. premium pay
    if ac in PREM_ACCTS and (dn, ac) in prem:
        p = prem[(dn, ac)]
        add("City", path, a, "payroll costing dawh-m56b 2025 actual by job title (raw/leaves via scripts/leaves_fetch.py)",
            "split_proxy", note=f"2025 actual pay on this account in the department was ${p['amt']/1e6:.1f}M over {p['titles']} job titles, largest title {p['n_max']} employees ${p['max_title']/1e6:.1f}M. Count x average, a different year than the 2026 budget.")
        continue
    # 3. pensions
    if ac in ("0976", "097A"):
        key = {"Policemen's": "PABF", "Municipal": "MEABF", "Firemen's": "FABF", "Laborers'": "LABF"}
        fk = next(v for k, v in key.items() if r["fund_description"].startswith(k))
        f = pens["funds"][fk]
        add("City", path, a, "data/pensions_2026.json: actuarial valuation 12/31/2025 (retirees and average benefit)",
            "split_proxy", note=f"{f['summary']['retirees_and_beneficiaries']:,} retirees and beneficiaries, {f['summary']['active_members']:,} active members. The contribution is not the benefit payment, so this is context, not a split of the dollars.",
            explain="The City sends one statutory payment to the retirement fund, and the fund then pays thousands of retirees.")
        continue
    # 4. reserves
    if ac == "909A":
        l = res.get((r["fund_code"], dn, r["appropriation_authority"]))
        if l and l["named_items"]:
            its = []
            for ni in l["named_items"]:
                amt = ni.get("unspent_budget") if ni.get("unspent_budget") is not None else (ni.get("obligation", 0) - (ni.get("outlay") or 0))
                its.append((ni["project"][:70], amt))
            over = [{"name": n, "amount": round(x)} for n, x in its if x >= T]
            att = l["attributable"]
            resid = a - att
            if resid >= T: over.append({"name": "not attributable to a named project", "amount": round(resid)})
            add("City", path, a, l["method"], "split_partial", remaining=over,
                note=f"{att/1e6:.1f}M of {a/1e6:.1f}M attributable to {len(its)} named projects/awards (caps, not exact)",
                explain="" if not over else "Some named projects are single big construction jobs, and the rest of the grant has no public project list yet.")
        else:
            add("City", path, a, "Summary G names the grant; no public project list found", "unsplit_no_source",
                explain="This is money from one grant that the City has been promised but has not yet decided how to spend.")
        continue
    # 5. debt
    if kind == "nonvendor" and fam == "DEBT":
        src = "ACFR Table 25 series balances and official statements; series P&I only for 12 groups (data/debt_2026.json per_series_2026)"
        if "Library" in r["fund_description"]:
            add("City", path, a, "none (short-term library notes rolled over yearly)", "unsplit_no_source",
                explain="These are short-term notes that get paid and re-borrowed every year, so there is no list of separate loans.")
        elif "Bond Redemption" in r["fund_description"] and "Interest" in r["appropriation_account_description"]:
            got = sum(s["interest_2026"] for s in debt["per_series_2026"]["series"] if s["type"] == "General Obligation")
            add("City", path, a, src, "split_partial", remaining=[{"name": "GO series with 2026 interest known (6 groups)", "amount": got},
                {"name": "older GO series, schedule not usable", "amount": a - got}],
                note=f"${got/1e6:.1f}M of ${a/1e6:.1f}M sits in 6 series groups, the rest is older series. Source to try: GO series debt-service tables per series on cityofchicagoinvestors.com / EMMA.",
                explain="This is the yearly bill for many separate bonds, and the budget lists the total but not each bond's share.")
        else:
            add("City", path, a, src, "unsplit_source_known",
                note="Series-level debt service for O'Hare, Midway, Water and Sewer series is on EMMA (msrb.org), not reachable by script.",
                explain="This is the yearly bill for many separate bonds, and the City publishes the total but not each bond's share in the budget.")
        continue
    # 6. vendor families
    if kind == "vendor":
        gkey = (dn, fam)
        pool = fam in ("BENEFITS", "LEGAL")
        if ac in HEALTH:
            kk = "health_enrollment"
            enrolled = {"0042": ("PPO and other medical", 0.77), "0029": ("HMO", 0.12)}[ac]
            cnt = round(32011 * enrolled[1])
            add("City", path, a, "EY Financial and Strategic Reform Options (published Oct 16 2025) p.46: 32,011 active workforce, 77% PPO, 12% HMO",
                "split_proxy", note=f"about {cnt:,} enrolled employees x about ${a/cnt:,.0f} each (this line only). Percentages are rounded, so counts are approximate, and the line is spread across departments by fund.")
            continue
        if ac in ("0049", "0056", "0172", "0937"):
            add("City", path, a, "none public by claim or policy (EY report p.43-45 gives savings ideas, not claim lists)", "unsplit_no_source",
                explain="These are insurance and injury claims paid one person at a time, and privacy rules keep each claim out of public budget data.")
            continue
        its, B = (pooled(fam) if pool else (items_by.get(gkey, []), budget_by[gkey]))
        if not its or B == 0:
            add("City", path, a, "no matching 2025 payments for this department and account family", "unsplit_no_source",
                explain="Nobody has published who gets paid from this line yet.")
            continue
        pending[("POOL:" + fam) if pool else gkey].append((a, path, ac, B, its))
        continue
    # 7. rest of non-vendor
    why = {
        "TAXES": "The City sets aside this money because some property taxes are never paid, and nobody knows in advance whose.",
        "PASSTHRU": "The City collects this tax and hands the whole amount to another agency in one payment.",
        "PERSONNEL": "This is money set aside for union raises that are not settled yet, so nobody can say yet which workers will get how much.",
        "TRANSFER": "This is money moving between City accounts, so there is no one to pay.",
    }.get(fam, "Public records stop at this level.")
    add("City", path, a, "none found", "unsplit_no_source", explain=why)

# vendor groups: each (department, account family) is listed ONCE, vendor amounts are unscaled 2025 payments
for gk, lines in pending.items():
    lines.sort(key=lambda x: -x[0])
    B, its = lines[0][3], lines[0][4]
    paid = sum(i[2] for i in its)
    big_budget = sum(x[0] for x in lines)
    pieces = [{"name": f"{i[0][:48]} (contract {i[1] or 'direct voucher'}), 2025 payments", "amount": round(i[2])} for i in sorted(its, key=lambda i: -i[2]) if i[2] >= T]
    resid = max(0.0, big_budget * (1 - min(B, paid) / B))
    if resid >= T: pieces.append({"name": "budget with no matched 2025 payee (group residual)", "amount": round(resid)})
    for n, (a, path, ac, _, _) in enumerate(lines):
        first = n == 0
        add("City", path, a, "payments s4vu-giwb 2025 joined to contracts rsxa-ify5 (data/city_vendors_items_2025.json)", "split_partial",
            remaining=pieces if first else [], group_cap=big_budget if first else None,
            note=(f"group {gk}: 2025 named payments ${paid/1e6:.0f}M vs 2026 budget ${B/1e6:.0f}M; vendor items listed once on the largest line of the group, amounts are 2025 payments, not scaled"
                  if first else "vendor items for this department and account family are listed on the largest line of the group"),
            explain="" if not pieces else "A few big companies each get one large contract payment, and the City does not publish smaller pieces of one contract.")

# ------------------------------------------------------------------ CPS
U = {r["Unit"]: r for r in csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_dim_unit.csv"))}
A = {r["Account"]: r for r in csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_dim_account.csv"))}
F = {r["Fund Grant"]: r for r in csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_dim_fund.csv"))}
P = {r["Program"]: r for r in csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_dim_program.csv"))}
charter = {r["unit"]: r for r in csv.DictReader(open(f"{ROOT}/data/cps_charter_by_school_fy26.csv"))}
caps = list(csv.DictReader(open(f"{ROOT}/data/cps_capital_projects_fy26.csv")))
cps_total = 0.0
cap_listed = []
transp_listed = []
cps_rows = list(csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_exp_unit_fund_program_account.csv")))
cap_lines_total = sum(float(r['fy_new_budget']) for r in csv.DictReader(open(f'{ROOT}/raw/cps/cps_2026_exp_unit_fund_program_account.csv')) if r['account'] == 'A56310')
cap_proj_over = [{"name": c["project_name"][:60], "amount": round(float(c["budget"]))} for c in caps if float(c["budget"]) >= T]
for r in cps_rows:
    cps_total += float(r["fy_new_budget"])
    a = float(r["fy_new_budget"])
    if abs(a) < T: continue
    u = U.get(r["unit"], {}); ac = A.get(r["account"], {}); fd = F.get(r["fund_grant"], {}); pg = P.get(r["program"], {})
    adesc = ac.get("Account Description", r["account"])
    path = f"CPS > {u.get('Level 2 Unit Description','?')} > {u.get('Unit Description','?')} > {fd.get('Fund Grant Description','?')[:40]} > {pg.get('Program Description','?')} > {r['account']} {adesc}"
    c = r["account"]; major = ac.get("Major Category", "")
    if a < 0:
        add("CPS", path, a, "none (budget-only offset)", "unsplit_no_source",
            explain="This is a planned cut that offsets spending counted elsewhere, so there is nothing to itemize.")
    elif adesc.startswith("Capitalized Construction"):
        first_cap = not cap_listed
        cap_listed.append(1)
        add("CPS", path, a, "data/cps_capital_projects_fy26.csv (131 projects, $555.94M vs $555.945M fund lines)", "split_partial",
            remaining=cap_proj_over if first_cap else [], group_cap=cap_lines_total if first_cap else None,
            note="the 4 capital fund lines are replaced jointly by the 131 projects; projects >= $10M are listed once, on the first of the 4 lines",
            explain="" if not first_cap else "Several big programs (like fixing fire alarms in many schools) are one budgeted amount, and CPS does not publish the dollars for each school.")
    elif c in ("A57805", "A57810"):
        add("CPS", path, a, "data/cps_debt_by_series_fy26.csv (already one bond series x principal or interest)", "accepted_single_obligation",
            explain="This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself.")
    elif c == "A54320" and u.get("Unit") in ("",) or c == "A54320" and r["unit"][1:] in {k[1:] for k in charter}:
        ch = charter.get(r["unit"])
        if ch and ch["students_profile_api"]:
            add("CPS", path, a, "data/cps_charter_by_school_fy26.csv: CPS school profile enrollment x per-pupil tuition", "split_proxy",
                note=f"{int(float(ch['students_profile_api'])):,} students x ${float(ch['per_pupil']):,.0f} per student")
        else:
            add("CPS", path, a, "none (no enrollment match)", "unsplit_source_known", explain="One charter campus gets one tuition payment that depends on its student count.")
    elif c == "A54320":
        add("CPS", path, a, "none", "unsplit_no_source", explain="One tuition budget for students placed in charter programs.")
    elif major == "TOTAL EMPLOYEE COMPENSATION" and not adesc.startswith("Budget Only") and c.startswith(("A51", "A52", "A57")):
        add("CPS", path, a, "raw/cps/cps_2026_positions_unit_job.csv and CPS public roster (cps_roster_dept_job.csv): FTE x average", "split_proxy",
            note="job title x people x average; roster dated 12/31/2025, not a dollar-for-dollar tie")
    elif c == "A58115" and "CTPF" in fd.get("Fund Grant Description", ""):
        add("CPS", path, a, "CTPF actuarial valuation 6/30/2025 (data/cps_ctpf_valuation_2025.csv)", "split_proxy",
            note="34,647 active teachers, 23,350 retirees at $64,860 average. Levy, not benefit payments, so context only.",
            explain="The Board sends one pension payment set by state law, and the pension fund pays the retirees.")
    elif c == "A58195":
        add("CPS", path, a, "FY25 ACFR Note 11 p.92 (pdf p.92): self-insured medical claims paid $703.1M in FY25, claims IBNR $116.3M; supplier payments FY26 HCSC $550.0M, CVS Caremark $174.7M", "unsplit_source_known",
            note="the budget line is a reserve for the whole district, the ACFR gives total claims paid, not a split of this line",
            explain="CPS pays most health bills as they come in, so the reserve is a guess at claims that have not happened yet.")
    elif c in ("A58115", "A58275", "A58195", "A58190", "A58185", "A58210", "A58110"):
        add("CPS", path, a, "budget book pp.34-39, CTPF/MEABF valuations (data/cps_pension_insurance_fy26.csv)", "unsplit_source_known",
            explain="This is a reserve the district sets aside for pensions, health insurance or claims, and the real bills arrive later from the insurers and pension funds.")
    elif c == "A54210":
        first_t = not transp_listed
        transp_listed.append(1)
        add("CPS", path, a, "CPS procurement API supplier payments FY26 (bus vendors, name match)", "split_partial",
            group_cap=(146_700_000 + 13_000_000) if first_t else None,
            explain="The bus companies are paid by contract, and CPS publishes each company's yearly total but not each route.",
            remaining=[] if not first_t else [{"name": "Illinois Central School Bus", "amount": 29054591}, {"name": "Sunrise Transportation", "amount": 26211316},
                       {"name": "Alltown Bus Service", "amount": 22299690}, {"name": "A.M. Bus", "amount": 16900000},
                       {"name": "First Student", "amount": 15200000}, {"name": "SCR Medical Transportation", "amount": 12400000}, {"name": "Compass", "amount": 11500000}],
            note="vendor amounts are FY26 payments from research/cps_deep.md section 4 (rounded to $0.1M where the doc rounds), not a split of this line")
    elif c == "A57915":
        add("CPS", path, a, "none", "unsplit_no_source",
            explain="This is money held back for things that have not been decided yet, so it has no purchases to list.")
    else:
        add("CPS", path, a, "CPS procurement API supplier payments FY26, Board Reports, FY25 ACFR (vendor to budget line link is inferred only)", "unsplit_source_known",
            explain="The money goes to a few large companies, and CPS publishes what each was paid but not which budget line it came from.")

# ------------------------------------------------------------------ Parks
parks = D("data/parks_2026.json")
ser = parks["beyond_operating"]["debt"]["ordinance_appropriation_M_by_bond_series_2026"]["rows"]
pr_over = [{"name": s["name"], "amount": s["principal"]} for s in ser if s["principal"] >= T]
in_over = [{"name": s["name"], "amount": s["interest"]} for s in ser if s["interest"] >= T]
sum_pr = sum(s["principal"] for s in ser); sum_in = sum(s["interest"] for s in ser)
for l in parks["leaves_at_or_above_1M"]:
    a = l["amount2026"]
    if a < T: continue
    path = "Parks > " + l["id"].replace("/", " > ") + " > " + l["name"]
    n = l["name"]
    if "Pension" in n:
        add("Parks", path, a, "PEABF actuarial valuation 12/31/2025 and ACFR Note 10 (2,701 retirees, ~$86.0M benefits 2024)", "split_proxy",
            note="benefits paid by the fund to retirees, not the District contribution", explain="The District makes one legal payment to its pension fund, and the fund pays about 2,700 retirees.")
    elif n == "Interest Expense":
        add("Parks", path, a, "Park District ordinance Appendix M by bond series (26 series)",
            "split_tied" if not in_over and sum_in == a else ("accepted_single_obligation" if sum_in == a else "split_partial"), remaining=[] if sum_in == a else in_over, note=f"series interest sums to ${sum_in:,} vs line ${a:,}; each remaining piece is one bond series", explain="This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself.")
    elif n.startswith("Principal"):
        add("Parks", path, a, "Park District ordinance Appendix M by bond series (26 series)",
            "split_tied" if not pr_over and sum_pr == a else ("accepted_single_obligation" if sum_pr == a else "split_partial"), remaining=[] if sum_pr == a else pr_over, note=f"series principal sums to ${sum_pr:,} vs line ${a:,}; each remaining piece is one bond series", explain="This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself.")
    elif "Laborer" in n:
        add("Parks", path, a, "Park District Appropriations PDF position tables (187 FTE)", "split_tied", note="187 FTE x about $56,250 average")
    elif "Soldier Field" in n or "Harbor" in n or "Utility" in n:
        add("Parks", path, a, "Park vendor payments agent (running now) and Bonfire contract library", "other_agent",
            explain="One company runs this place or one utility sends the bill, and the Park District does not publish payments by vendor.")
    elif "Transfer to Capital" in n:
        add("Parks", path, a, "Park capital project dollars agent (running now)", "other_agent")
    elif "Aquarium" in n:
        add("Parks", path, a, "none: 11 museums share the subsidy under state law; per-museum shares not published", "unsplit_no_source",
            explain="State law sets one museum payment, and the Park District does not publish how it is divided among the 11 museums.")
    else:
        add("Parks", path, a, "none", "unsplit_no_source")

# ------------------------------------------------------------------ Round 3: newly landed data and per-leaf overrides
import glob
STATUS_MAP = {"split_tied": "split_tied", "split_proxy": "split_proxy", "split_partial": "split_partial", "accepted_single_obligation": "accepted_single_obligation",
              "unsplit": "unsplit_no_source"}
round3_log = {"overrides": [], "bond_series": None, "parks_inputs": [], "deducted_from_city_base": {"count": len(deducted), "dollars": sum(d[0] for d in deducted)}}

def find(match, amount=None):
    out = []
    for l in leaves:
        if all(m in l["path"] for m in match) and (amount is None or abs(abs(l["amount"]) - amount) < 1):
            out.append(l)
    return out

def apply_override(l, rec, src):
    new = STATUS_MAP[rec["proposed_status"]]
    old = l["status"]
    l["status"] = new
    l["split_source"] = src + ": " + rec.get("split_basis", "")[:400]
    l["remaining_pieces_over_10m"] = rec.get("pieces_over_10m_after", [])
    if new == "unsplit_no_source" and not l["remaining_pieces_over_10m"]:
        l["remaining_pieces_over_10m"] = []
    if "why_cant_go_deeper" in rec: l["why_cant_go_deeper"] = rec["why_cant_go_deeper"]
    l["note"] = (rec.get("split_basis", "") if not l.get("note") or new != old else l["note"])[:700]
    l["round3_pieces"] = rec.get("pieces", [])
    l["group_cap"] = abs(l["amount"])
    for k in ("components", "benefit_type_pieces", "benefit_total_annual_valuation", "acfr_benefits_paid_2025", "by_vendor_2025_payments", "enrolled_total", "average_per_enrollee", "move_from_unattributed"):
        if k in rec: l["round3_" + k] = rec[k]
    round3_log["overrides"].append({"path_tail": l["path"][-80:], "amount": l["amount"], "from": old, "to": new})

for fn in sorted(glob.glob(f"{ROOT}/data/leaves_*.json")):
    if fn.endswith("leaves_over_10m.json") or os.environ.get("LEAVES_NO_OVERRIDES"): continue  # LEAVES_NO_OVERRIDES=1 gives the "step 1" numbers
    d = json.load(open(fn)); src = "data/" + os.path.basename(fn)
    for rec in d.get("leaves", []):
        if "match_path_contains" not in rec: continue
        for l in find(rec["match_path_contains"], rec.get("amount")):
            if abs(l["amount"]) < T: continue
            if rec.get("amount") is None and l["status"] not in ("unsplit_no_source", "unsplit_source_known", "split_partial", "split_proxy"): continue
            apply_override(l, rec, src)

# Park District: capital and vendor files landed (round 3), reported only, the Parks overrides above come from scripts/leaves_parks.py
for l in leaves:
    if l["budget"] == "Parks" and l["status"] == "other_agent":
        l["status"] = "unsplit_no_source"; l["split_source"] = "data/parks_vendors.json: one payee per group (round 3 check)"
round3_log["parks_inputs"] = ["data/parks_capital_projects.json", "data/parks_vendors.json"]

# City bond series (other agent): data/city_bond_series_2026.json. ASSUMED schema (tolerant): top-level list under "series" or "rows", each row
# {fund | fund_description, kind | type ("interest"|"principal"|"loan"), amount | amount_2026 | total_2026, series}. A single series is accepted as a leaf even if >= $10M.
bp = f"{ROOT}/data/city_bond_series_2026.json"
if os.path.exists(bp):
    B = json.load(open(bp)); rows_ = B.get("series") or B.get("rows") or (B if isinstance(B, list) else [])
    FUND_KEY = {"O'Hare": "Chicago O'Hare Airport Fund", "Midway": "Chicago Midway Airport Fund", "Water": "Water Fund", "Sewer": "Sewer Fund", "GO": "Bond Redemption and Interest Series Fund"}
    ACC = {"0902": "interest", "0912": "principal", "0944": "loan"}
    got = defaultdict(list)
    for r_ in rows_:
        f_ = r_.get("fund") or r_.get("fund_description") or ""; k_ = (r_.get("kind") or r_.get("type") or "").lower()
        a_ = r_.get("amount") or r_.get("amount_2026") or r_.get("total_2026") or 0
        for key, fd in FUND_KEY.items():
            if key.lower() in f_.lower() or fd.lower() in f_.lower():
                got[(fd, "interest" if "int" in k_ else "principal" if "prin" in k_ else "loan" if "loan" in k_ else k_)].append((r_.get("series", "series"), a_))
    used = 0
    for l in leaves:
        if l["budget"] != "City": continue
        for ac, kind in ACC.items():
            if f"> {ac} " in l["path"]:
                for (fd, k_), ser in got.items():
                    if k_ == kind and f"> {fd} >" in l["path"]:
                        tot_ = sum(a for _, a in ser)
                        l["status"] = "accepted_single_obligation" if abs(tot_ - abs(l["amount"])) < max(1000, 0.002 * abs(l["amount"])) else "split_partial"
                        l["remaining_pieces_over_10m"] = [] if l["status"] == "accepted_single_obligation" else [{"name": "bond series not in data/city_bond_series_2026.json", "amount": round(abs(l["amount"]) - tot_)}]
                        l["split_source"] = "data/city_bond_series_2026.json (other agent): %d series, $%.1fM of $%.1fM" % (len(ser), tot_ / 1e6, abs(l["amount"]) / 1e6)
                        l["round3_pieces"] = [{"name": n, "amount": a} for n, a in ser]
                        l["why_cant_go_deeper"] = "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself."
                        used += 1
    round3_log["bond_series"] = {"file": "data/city_bond_series_2026.json", "rows": len(rows_), "leaves_updated": used}
else:
    round3_log["bond_series"] = "file not present yet; inventory will pick it up on the next run"

# ------------------------------------------------------------------ totals
def over_after(l, mode):
    """dollars and count still >= $10M after splits. mode 'strict' resolves split_tied only, 'team' resolves tied+proxy and replaces partial by remaining pieces."""
    s = l["status"]; amt = abs(l["amount"])
    if s in ("split_tied", "accepted_single_obligation"): return []
    if mode == "team":
        if s == "split_proxy": return []
        if s == "split_partial":
            pcs = [abs(p["amount"]) for p in l["remaining_pieces_over_10m"]]
            cap = l.get("group_cap", amt)
            tot = sum(pcs)
            return pcs if tot <= cap else [x * cap / tot for x in pcs]  # never count more than the dollars in the budget lines concerned
    return [amt]

summary = {}
for b in ("City", "CPS", "Parks"):
    ls = [l for l in leaves if l["budget"] == b]
    s = {"before_count": len(ls), "before_dollars": sum(abs(l["amount"]) for l in ls)}
    for mode in ("strict", "team"):
        pieces = [x for l in ls for x in over_after(l, mode)]
        s[f"after_{mode}_count"] = len(pieces); s[f"after_{mode}_dollars"] = sum(pieces)
    s["by_status"] = {st: {"count": sum(1 for l in ls if l["status"] == st), "dollars": sum(abs(l["amount"]) for l in ls if l["status"] == st)}
                      for st in sorted({l["status"] for l in ls})}
    summary[b] = s
summary["bases"] = {"city_net_total": city_before_total, "cps_total": cps_total, "parks_total": parks["meta"]["grand_total_2026"]}
# remaining pieces >= $10M after team splits (what is left), largest first
remaining = []
for l in leaves:
    pcs = over_after(l, "team")
    names = [p["name"] for p in l["remaining_pieces_over_10m"]] if l["status"] == "split_partial" else [None] * len(pcs)
    for n, x in zip(names or [None] * len(pcs), pcs):
        remaining.append({"budget": l["budget"], "amount": round(x), "status": l["status"], "leaf_path": l["path"], "piece": n, "why_cant_go_deeper": l["why_cant_go_deeper"]})
remaining.sort(key=lambda r: -r["amount"])
summary["remaining_over_10m"] = {"count": len(remaining), "dollars": sum(r["amount"] for r in remaining)}
round3_log["remaining_top"] = remaining[:40]
if os.environ.get("LEAVES_NO_OVERRIDES"):
    OUT = f"{ROOT}/raw/leaves/leaves_step1.json"
else:
    OUT = f"{ROOT}/data/leaves_over_10m.json"
json.dump({"threshold": T, "summary": summary, "round3": round3_log, "remaining_pieces_over_10m": remaining, "leaves": sorted(leaves, key=lambda l: (l["budget"], -abs(l["amount"])))},
          open(OUT, "w"), indent=1)

print(f"{'budget':6} {'before':>18} {'after: tied only':>22} {'after: team splits':>22}")
for b in ("City", "CPS", "Parks"):
    s = summary[b]
    print(f"{b:6} {s['before_count']:>4} ${s['before_dollars']/1e9:6.2f}B   {s['after_strict_count']:>4} ${s['after_strict_dollars']/1e9:6.2f}B   {s['after_team_count']:>4} ${s['after_team_dollars']/1e9:6.2f}B")
for b in ("City", "CPS", "Parks"):
    print(b, {k: (v["count"], round(v["dollars"]/1e6)) for k, v in summary[b]["by_status"].items()})
