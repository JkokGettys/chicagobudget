"""Build the City of Chicago FY2026 budget tree.

Base: 2026 Annual Appropriation Ordinance (data.cityofchicago.org 6694-f78c, raw copy
raw/city_appropriations_2026.json). Detail attached under ordinance lines with
treelib.split(), so every box always equals the sum of what's inside it.

Top of tree (what the money is for):
  City of Chicago (net, $16,842,553,003 as printed in the passed ordinance)
    Public Safety / Infrastructure / Community Services / City Development /
    Regulatory / Finance and Administration / Legislative and Elections   (departments)
    Retirement (pensions) / Paying back loans / Employee health and benefits /
    Other citywide costs                                                   (Finance General)
    Adjustment: OBM deduction not explained by any line (negative)
  Shown separately, NOT part of the City total:
    Money counted twice (internal transfers and debt proceeds)

Run: python3 build/city_tree.py   (exit 1 if any check fails)
"""
import json
import re
import os
import sys
from collections import defaultdict
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(__file__))
from treelib import Node, cents, check, depth_report, split, save_json, to_rows, side_rows, load_into_db, slug  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), "..")
P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731

ORD = {"dataset": "6694-f78c", "name": "2026 Annual Appropriation Ordinance",
       "url": "https://data.cityofchicago.org/Administration-Finance/Budget-2026-Budget-Ordinance-Appropriations/6694-f78c"}
OFFICIAL_NET = 16_842_553_003       # ordinance p.544, Summary G "Net Total - All Functions"
OFFICIAL_GROSS = 18_668_568_460
UNEXPLAINED = 116_988_502           # research/transfer_residual.md

FUNCTION = {
    "Public Safety": ["51", "55", "57", "58", "59", "60", "62"],
    "Infrastructure Services": ["81", "84", "85", "88"],
    "Community Services": ["41", "45", "48", "50", "91"],
    "City Development": ["21", "23", "54"],
    "Regulatory": ["3", "67", "70", "72", "73", "77", "78"],
    "Finance and Administration": ["1", "5", "6", "27", "28", "30", "31", "33", "35", "38"],
    "Legislative and Elections": ["15", "25", "39"],
}
KID_FUNCTION = {
    "Public Safety": "Keeping people safe",
    "Infrastructure Services": "Streets, water, trash and airports",
    "Community Services": "Health, families and libraries",
    "City Development": "Housing, neighborhoods and culture",
    "Regulatory": "Inspections and rules",
    "Finance and Administration": "Running the city government",
    "Legislative and Elections": "City Council and elections",
}
DEPT_FUNC = {d: f for f, ds in FUNCTION.items() for d in ds}

# spending type by account code (first digits), for a kid-readable layer
def spend_type(acct, desc):
    a = acct
    if a in ("0005", "0006", "0015", "0017", "0012", "0000"):
        return "Pay for workers"
    if a in ("0020", "0032"):
        return "Overtime"
    if a == "0003":
        return "Raises and back pay"
    if a[:2] == "00":
        return "Other worker pay and benefits"
    if a[:2] == "01":
        return "Contracts and services"
    if a[:2] == "02":
        return "Travel"
    if a[:2] in ("03", "04"):
        return "Supplies and equipment"
    if a[:2] == "05":
        return "Construction"
    if desc == "Reserve Balance" or a == "909A":
        return "Grant money not yet assigned to projects"
    if a[:2] in ("94", "97") or desc.startswith("For Services Provided by"):
        return "Paying other city departments"
    return "Programs and other costs"


# ---------------------------------------------------------------- load
app = json.load(open(P("raw/city_appropriations_2026.json")))
assert sum(int(r["_ordinance_amount_"]) for r in app) == OFFICIAL_GROSS, "ordinance gross changed"

sys.path.insert(0, P("scripts"))
from finance_general import classify  # noqa: E402  (the agreed transfer rule)


def deduction_kind(r):
    """Return None if the line is real spending, else which deduction it belongs to."""
    desc = r["appropriation_account_description"]
    if r["department_description"] == "Finance General":
        if classify(desc, r["fund_description"])[2]:
            return "transfer"
    if r["appropriation_account"] == "0961" and "Library" in r["fund_description"]:
        return "debt_proceeds"
    if desc.startswith("To Provide for Matching and Supplementary Grant"):
        return "matching"
    if r["department_description"] != "Finance General" and desc.startswith("For Services Provided by") \
            and r["fund_type"] == "LOCAL" and "Performers and Exhibitors" not in desc:
        # Appendix A/B internal transfers: reproduces $18,678,776 to the dollar (scripts/gap_reconcile.py step 8).
        # The Library's "Performers and Exhibitors" line is a vendor class, and the 925 grant-fund line is external.
        return "services_between_funds"
    return None


# ---------------------------------------------------------------- base tree
city = Node("city", "City of Chicago", gov="city", basis="budget", source=ORD, kind="government",
            note="2026 budget as passed by City Council (net of money counted twice).")
twice = Node("city-twice", "Money counted twice (not part of the City total)", gov="city",
             basis="budget", source=ORD, kind="memo",
             note="Money one city fund sends to another, plus re-borrowed library notes. Listing it "
                  "would count the same dollar twice, so the official total removes it.")

func_nodes = {}
for f in FUNCTION:
    func_nodes[f] = city.add(slug(f), KID_FUNCTION[f], kind="function", extra={"official_name": f})
FG = {
    "pension": city.add("retirement", "Retirement (pensions)", kind="function",
                        note="Payments the City must make into four worker retirement funds."),
    "debt": city.add("loans", "Paying back loans", kind="function",
                     note="Interest and principal on bonds and loans."),
    "health": city.add("health", "Employee health care and benefits", kind="function"),
    "other": city.add("citywide", "Other citywide costs", kind="function",
                      note="Costs the budget keeps in one place for all departments (Finance General)."),
}

ordline = {}   # (fund_code, dept_num, auth, acct) -> leaf node
dept_nodes = {}

def fg_bucket(desc, acct):
    d = desc
    if "Annuity and Benefit" in d:
        return "pension", None
    if d.startswith(("For Interest", "For Payment of Bonds", "For Payment of Term Notes",
                     "For Payment on Loans", "For Bond Fees")) or "Bond Fees" in d:
        return "debt", None
    if any(k in d for k in ("Hospital and Medical", "HMO", "Dental", "Workers' Compensation",
                            "Medicare", "Unemployment", "Deferred Compensation", "Employee Contractual",
                            "Vision", "Life Insurance")):
        return "health", None
    return "other", None


for r in app:
    a = int(r["_ordinance_amount_"])
    if a == 0:
        continue
    dk = deduction_kind(r)
    fund, dnum, auth, acct = r["fund_code"], r["department_number"], r["appropriation_authority"], r["appropriation_account"]
    desc = r["appropriation_account_description"]
    src = dict(ORD, line=f"fund {fund} dept {dnum} authority {auth} account {acct}")
    if dk:
        grp = {"transfer": "Pension money and reimbursements moved between city funds",
               "debt_proceeds": "Library notes paid with new borrowing",
               "matching": "City matching money for grants (counted inside grants)",
               "services_between_funds": "One city fund paying another for services"}[dk]
        g = twice.add(dk, grp, kind="group")
        dn = g.add(r["department_description"], r["department_description"], kind="department")
        fn = dn.add(f"{fund}-{r['fund_description']}", r["fund_description"], kind="fund")
        fn.add(f"{auth}-{acct}", desc, amount=cents(a), kind="line", source=src,
               extra={"fund": fund, "fund_name": r["fund_description"], "authority": auth,
                      "authority_name": r["appropriation_authority_description"], "account": acct})
        continue
    if r["department_description"] == "Finance General":
        b, _ = fg_bucket(desc, acct)
        parent = FG[b]
        if b == "pension":
            g = parent.add(r["fund_description"], r["fund_description"].replace("Annuity and Benefit Fund", "retirement fund"), kind="group")
        elif b == "debt":
            g = parent.add(r["fund_description"], r["fund_description"], kind="group")
        else:
            g = parent.add(r["fund_description"], r["fund_description"], kind="fund")
        line_parent = g
    else:
        f = DEPT_FUNC[dnum]
        dn = dept_nodes.get(dnum) or func_nodes[f].add(r["department_description"], r["department_description"],
                                                       kind="department", extra={"dept_number": dnum})
        dept_nodes[dnum] = dn
        st = dn.add(spend_type(acct, desc), spend_type(acct, desc), kind="spend_type")
        line_parent = st.add(f"{fund}-{r['fund_description']}", r["fund_description"], kind="fund")
    name = desc if r["appropriation_authority_description"] in (r["department_description"], "Finance General") \
        else f"{desc} ({r['appropriation_authority_description']})"
    n = line_parent.add(f"{fund}-{auth}-{acct}", name, amount=cents(a), kind="line", source=src,
                        extra={"fund": fund, "fund_name": r["fund_description"], "dept_number": dnum,
                               "authority": auth, "authority_name": r["appropriation_authority_description"],
                               "account": acct, "official_name": desc})
    ordline[(fund, dnum.lstrip("0"), auth, acct)] = n

city.add("obm-unexplained", "Adjustment the budget office makes that no line explains",
         amount=-cents(UNEXPLAINED), basis="adjustment", kind="adjustment",
         source={"doc": "research/transfer_residual.md",
                 "note": "Part of OBM's printed 'Deduct Transfers between Funds' that no ordinance line reproduces. "
                         "About $60.6M in 2025."},
         note="The official total subtracts this much more than we can match to any line. It is shown so "
              "the boxes add up to the official $16,842,553,003.")

# ---------------------------------------------------------------- detail: salaries
pers = json.load(open(P("data/city_personnel_2026.json")))
PERS_SRC = {"dataset": "v2t2-vajc", "name": "2026 Budget Ordinance Positions and Salaries",
            "url": "https://data.cityofchicago.org/d/v2t2-vajc"}



def build_salary(line, dept_tree, fund, dept_num, division_code=None):
    """Replace one salary line (account 0005, one fund, optionally one division/authority) with
    division > section > title pieces. Each title keeps its pay-rate rows as count x rate children
    when a title has several rates, so big titles (8,000 officers) end in 'N positions x $rate' boxes."""
    pieces = []
    def rec(n, path, in_div):
        for c in n.get("children", []):
            here = in_div or (division_code is None) or (c.get("level") == "division" and c.get("code") == division_code)
            if c.get("level") == "title":
                if not here:
                    continue
                rows = [x for x in c.get("rows", []) if x.get("fund") == fund]
                if not rows:
                    continue
                amt = cents(sum(x["amount"] for x in rows))
                units = sum(x["units"] for x in rows)
                pos = all(x.get("unit_is_positions") for x in rows)
                rate = round(amt / units) if units else None
                pieces.append((path, c, amt, units, pos, rate, rows))
            elif c.get("level") == "division" and division_code is not None and c.get("code") != division_code:
                continue
            else:
                rec(c, path + [c["name"]], here)
    rec(dept_tree, [], division_code is None)
    if not pieces:
        return False
    adjust = [x for x in dept_tree.get("adjustments", []) if x.get("fund") == fund] if division_code is None else []
    for path, c, amt, units, pos, rate, rows in pieces:
        parent = line
        for pname in path[-2:]:   # keep the two most specific org levels (division > section)
            parent = parent.add(pname, pname, kind="org_unit")
        label = "positions" if pos else "hours"
        n = parent.add(f"{c['code']}-{c['name']}", c["name"].title(), amount=amt, basis="tied",
                       kind="job_title", count=units, unit_amount=rate, unit_label=label, source=PERS_SRC,
                       extra={"title_code": c["code"]})
        if len(rows) > 1:
            # one box per pay rate: "2,148 positions x $111,252"
            by_rate = defaultdict(lambda: [0, 0, None])
            for x in rows:
                k = (x["rate"], x.get("grade"))
                by_rate[k][0] += x["units"]; by_rate[k][1] += x["amount"]; by_rate[k][2] = x.get("unit_is_positions")
            for (rt, gr), (u, a, isp) in sorted(by_rate.items(), key=lambda kv: -kv[1][1]):
                lbl = "positions" if isp else "hours"
                n.add(f"rate-{rt}-{gr}", f"{u:,.0f} {lbl} x ${rt:,.2f}" + (f" (grade {gr})" if gr else ""),
                      amount=cents(a), basis="tied", kind="pay_rate", count=u, unit_amount=cents(rt), unit_label=lbl)
            if sum(ch.amount for ch in n.children) != n.amount:
                n.add("rounding", "Rounding", amount=n.amount - sum(ch.amount for ch in n.children), basis="adjustment")
    for x in adjust:
        line.add(x["name"], x["name"], amount=cents(x["amount"]), basis="adjustment", kind="adjustment",
                 source={"doc": "2026 Annual Appropriation Ordinance", "page": x.get("ordinance_pages")},
                 note=x.get("note"))
    # container amounts: org_unit nodes have no amount yet; compute then check vs line
    def roll(n):
        if not n.children:
            return n.amount
        s = sum(roll(c) for c in n.children)
        if n is not line:
            n.amount = s
        return s
    tot = roll(line)
    if tot != line.amount:
        multi = division_code is not None
        line.add("difference",
                 "Budgeted vacancy savings and other differences" if multi else "Difference between positions list and budget line",
                 amount=line.amount - tot, basis="adjustment", kind="adjustment",
                 source={"doc": "research/city_personnel.md"},
                 note=("The budget prints vacancy savings (turnover) once per department and fund, not per division, "
                       "so this division's share shows here." if multi else
                       "Positions times rates do not add up exactly to the budget line for this fund."))
    return True


n_sal = 0
for d in pers["tree"]["children"]:
    dnum = d["code"].lstrip("0")
    # collect funds present under this dept
    fs = set()
    stack = [d]
    while stack:
        n = stack.pop()
        for x in n.get("rows", []) or []:
            fs.add(x["fund"])
        stack.extend(n.get("children", []))
    for x in d.get("adjustments", []):
        fs.add(x.get("fund"))
    for fund in fs:
        auths = [k for k in ordline if k[0] == fund and k[1] == dnum and k[3] == "0005"]
        if not auths:
            continue
        if len(auths) == 1:
            if build_salary(ordline[auths[0]], d, fund, dnum):
                n_sal += 1
            continue
        # several authorities (divisions) for this fund: split each by its own division;
        # department-level turnover goes on the largest line.
        biggest = max(auths, key=lambda k: ordline[k].amount)
        for k in auths:
            line = ordline[k]
            ok = build_salary(line, d, fund, dnum, division_code=k[2])
            if ok and k == biggest:
                for x in [x for x in d.get("adjustments", []) if x.get("fund") == fund]:
                    pass  # handled below via difference child (turnover is printed per department)
            n_sal += 1 if ok else 0
print(f"salary lines split: {n_sal}")

# ---------------------------------------------------------------- detail: pensions
pen = json.load(open(P("data/leaves_pensions.json")))["leaves"]
PEN_SRC = {"doc": "data/leaves_pensions.json (fund actuarial valuations 12/31/2025)"}
for rec_ in pen:
    fundword, acct = rec_["match_path_contains"]
    if fundword == "Parks":
        continue
    hits = [n for k, n in ordline.items() if k[3] == acct and fundword in (n.extra.get("fund_name") or "")]
    if len(hits) != 1:
        print("pension match problem", fundword, acct, len(hits))
        continue
    line = hits[0]
    assert line.amount == cents(rec_["amount"]), (line.id, line.amount, rec_["amount"])
    why = rec_.get("why_cant_go_deeper")
    pcs = []
    for p in rec_["pieces"]:
        b = "tied" if p.get("basis") == "tied" else "proxy"
        nm = p["name"]
        kid = ("Paying down the shortfall (money promised but never saved)" if "unfunded" in nm.lower()
               else "Cost of pensions workers earn this year" if "normal cost" in nm.lower()
               else "Extra payment above what the law requires" if "Advance" in nm else nm)
        pcs.append({"key": kid, "name": kid, "amount": cents(p["amount"]), "basis": b, "kind": "component",
                    "source": PEN_SRC, "why": why if cents(p["amount"]) >= 1_000_000_000 else None,
                    "extra": {"official_name": nm}})
    split(line, pcs)
    bt = rec_.get("benefit_type_pieces")
    if bt:
        line.side.append({"kind": "retirees", "label": "Who the fund pays (latest valuation, count x average)",
                          "period": "valuation 12/31/2025", "basis": "proxy", "source": PEN_SRC,
                          "items": bt})

# ---------------------------------------------------------------- detail: bonds
bonds = json.load(open(P("data/city_bond_series_2026.json")))
BOND_SRC = {"doc": "Official statements, see data/city_bond_series_2026.json"}
FUNDNAME = {"ohare": "Chicago O'Hare Airport Fund", "midway": "Chicago Midway Airport Fund",
            "water": "Water Fund", "wastewater": "Sewer Fund", "go": "Bond Redemption and Interest Series Fund"}
by_fund_kind = defaultdict(list)
for s in bonds["series"]:
    if s.get("amount"):
        by_fund_kind[(s["fund"], s["kind"])].append(s)
# Add GO/STSC series from debt_2026.json per_series (GO only; STSC is outside the ordinance)
debt = json.load(open(P("data/debt_2026.json")))
have_go = {s["series"] for s in bonds["series"] if s["credit"] == "go"}
for s in debt["per_series_2026"]["series"]:
    if s["type"] != "General Obligation" or s["series"] in have_go:
        continue
    for kind, amt in (("principal", s["principal_2026"]), ("interest", s["interest_2026"])):
        if amt:
            by_fund_kind[("Bond Redemption and Interest Series Fund", kind)].append(
                {"series": s["series"], "amount": amt, "status": "current", "cite": s.get("cite"), "kind": kind})

WHY_BOND = "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself."
WHY_BOND_REST = "Several older bonds share this line, and the public statements we found do not print each bond's share for 2026."
debt_lines = [n for n in FG["debt"].walk() if not n.children and n.kind == "line"]
n_bond = 0
# Funds where some series are printed only as principal + interest together (Midway, Sewer 1998A):
# put that fund's bond interest and bond principal lines under one "Bonds" box and split the box,
# so combined series are not forced into the interest line (which made negative "difference" boxes).
for fund_name in sorted({f for (f, k) in by_fund_kind if k == "principal_and_interest"}):
    li = [n for n in debt_lines if n.extra["fund_name"] == fund_name and n.extra["official_name"].startswith(("For Interest on Bonds", "For Payment of Bonds"))]
    if len(li) != 2:
        continue
    grp = li[0].parent
    box = Node(f"{grp.id}.bonds", "Bonds: interest and principal together", gov="city", kind="line",
               amount=sum(n.amount for n in li), basis="budget", source=ORD,
               note="The budget has one line for interest and one for principal. The bond papers print some bonds "
                    "only as one yearly payment, so the two lines are shown together here.",
               extra={"fund_name": fund_name, "official_name": "For Interest on Bonds + For Payment of Bonds",
                      "merged_lines": [{"name": n.extra["official_name"], "amount_cents": n.amount, "account": n.extra["account"]} for n in li]})
    for n in li:
        grp.children.remove(n)
        debt_lines.remove(n)
    grp.adopt(box)
    ser = by_fund_kind.get((fund_name, "interest"), []) + by_fund_kind.get((fund_name, "principal"), []) \
        + by_fund_kind.get((fund_name, "principal_and_interest"), [])
    # combine interest + principal of the same series into one box with two children
    by_series = defaultdict(dict)
    for s in ser:
        by_series[s["series"]][s["kind"]] = s
    pcs = []
    for sname, parts in by_series.items():
        if "principal_and_interest" in parts:
            s = parts["principal_and_interest"]
            pcs.append({"key": sname, "name": f"{sname} (principal and interest)", "amount": cents(s["amount"]),
                        "basis": "tied", "kind": "bond_series", "source": dict(BOND_SRC, cite=s.get("cite")),
                        "why": WHY_BOND if cents(s["amount"]) >= 1_000_000_000 else None})
        else:
            tot_s = sum(cents(p["amount"]) for p in parts.values())
            pcs.append({"key": sname, "name": sname, "amount": tot_s, "basis": "tied", "kind": "bond_series",
                        "source": BOND_SRC})
    made = split(box, pcs, residual_name="Other bonds (not printed one by one)", residual_why=WHY_BOND_REST, allow_over=True)
    for m in made:
        if m.id.endswith(".difference"):
            m.name = "Bond papers list more than the budget (older bonds paid off early)"
            m.note = ("The bond papers were printed before some older bonds were paid off early in 2025 "
                      "(research/bond_series.md), so the bonds listed add up to a bit more than the 2026 budget line. "
                      "This negative box keeps the total equal to the budget.")
        parts = by_series.get(m.name, {})
        if m.kind == "bond_series" and "principal_and_interest" not in parts and len(parts) == 2:
            for kk in ("principal", "interest"):
                m.add(kk, kk.title(), amount=cents(parts[kk]["amount"]), basis="tied", kind="bond_part",
                      source=dict(BOND_SRC, cite=parts[kk].get("cite")))
    n_bond += 1
    for k in list(by_fund_kind):
        if k[0] == fund_name and k[1] in ("interest", "principal", "principal_and_interest"):
            del by_fund_kind[k]
for line in debt_lines:
    fund = line.extra["fund_name"]
    d = line.extra["official_name"]
    kind = "interest" if d.startswith("For Interest on Bonds") else "principal" if d.startswith("For Payment of Bonds") else None
    if not kind:
        continue
    ser = by_fund_kind.get((fund, kind), []) + (by_fund_kind.get((fund, "principal_and_interest"), []) if kind == "interest" else [])
    if not ser:
        continue
    pcs = [{"key": s["series"] + ("" if s["kind"] == kind else " (principal and interest)"),
            "name": s["series"] + ("" if s["kind"] == kind else " (principal and interest)"),
            "amount": cents(s["amount"]), "basis": "tied", "kind": "bond_series",
            "source": dict(BOND_SRC, cite=s.get("cite")), "why": WHY_BOND if cents(s["amount"]) >= 1_000_000_000 else None,
            "extra": {"status": s.get("status")}} for s in ser]
    tot = sum(p["amount"] for p in pcs)
    if tot > line.amount:
        split(line, pcs, allow_over=True)
    else:
        split(line, pcs, residual_name="Other bonds (not printed one by one)", residual_why=WHY_BOND_REST)
    n_bond += 1
print(f"bond lines split: {n_bond}")

# ---------------------------------------------------------------- detail: health, wages/overtime, grants (proxy files)
def match_line(contains, amount):
    want = cents(amount)
    hits = []
    for k, n in ordline.items():
        txt = " ".join([n.extra.get("fund_name", ""), n.extra.get("authority_name", ""), n.extra.get("official_name", ""),
                        k[3], n.parent.name if n.parent else "", n.id])
        dept = n.id
        if all(c.lower() in (txt + " " + dept).lower() or c in k for c in contains):
            hits.append(n)
    exact = [n for n in hits if n.amount == want]
    return exact[0] if len(exact) == 1 else (hits[0] if len(hits) == 1 else None), hits


def apply_proxy(file, kind_label):
    data = json.load(open(P(file)))["leaves"]
    for rec_ in data:
        pieces = [p for p in rec_.get("pieces", []) if p.get("amount")]
        if not pieces:
            continue
        line, hits = match_line(rec_["match_path_contains"], rec_["amount"])
        if not line or line.children:
            print(f"  {file}: no unique free line for {rec_['match_path_contains']} ({len(hits)} hits)")
            continue
        pcs = []
        for i, p in enumerate(pieces):
            b = "tied" if p.get("basis") in ("tied",) else "proxy"
            pcs.append({"key": f"{i}-{p['name'][:40]}", "name": p["name"], "amount": cents(p["amount"]),
                        "basis": b, "kind": kind_label, "count": p.get("count"),
                        "unit_amount": cents(p["average"]) if p.get("average") else None,
                        "unit_label": "people" if p.get("count") else None,
                        "source": {"doc": file, "note": rec_.get("split_basis")},
                        "why": rec_.get("why_cant_go_deeper") if cents(p["amount"]) >= 1_000_000_000 else None})
        tot = sum(p["amount"] for p in pcs)
        if tot > line.amount:
            # proxy pieces that exceed the line (e.g. 2025 actuals vs 2026 budget) go to side info only
            line.side.append({"kind": kind_label, "label": rec_.get("split_basis", "")[:200], "basis": "proxy",
                              "source": {"doc": file}, "items": pieces})
            line.why = line.why or rec_.get("why_cant_go_deeper")
            continue
        split(line, pcs, residual_why=rec_.get("why_cant_go_deeper"))


apply_proxy("data/leaves_health.json", "health_plan")
apply_proxy("data/leaves_wages.json", "job_title")
apply_proxy("data/leaves_grants.json", "grant_project")

# ---------------------------------------------------------------- detail from split files (build/SPLITS.md)
from treelib import apply_split_file  # noqa: E402
_by_id = None


def resolve_city(t):
    global _by_id
    if t.get("by") == "ordinance_line":
        return ordline.get((t["fund"], str(t["dept"]).lstrip("0"), t["authority"], t["account"]))
    if t.get("by") == "id":
        if _by_id is None:
            _by_id = {n.id: n for n in city.walk()}
        return _by_id.get(t["id"])
    return None


SPLIT_DIR = P("data/splits/city")
if os.path.isdir(SPLIT_DIR):
    for fn in sorted(os.listdir(SPLIT_DIR)):
        if fn.endswith(".json"):
            a, s = apply_split_file(os.path.join(SPLIT_DIR, fn), resolve_city)
            _by_id = None
            print(f"split file {fn}: {a} applied, {s} skipped")

# ---------------------------------------------------------------- side info: vendors paid 2026 YTD
# Every payment row is kept. Payees that are individual people (refunds, reimbursements, small
# grants, jurors, sole practitioners) keep their amount, contract, family and payment count,
# but their name is replaced with a placeholder. Business and organization names are shown.
from payee import is_business, people_by_description, neutral_description, ALLOWED_INDIVIDUAL_DESCRIPTIONS  # noqa: E402
ven = json.load(open(P("data/city_vendors_items_2026ytd.json")))
VEN_LABEL = ven["meta"]["label"]
_pp = json.load(open(P("data/people/city_employees_2026.json"))) if os.path.exists(P("data/people/city_employees_2026.json")) else {"current_employees": []}
EMP_NAMES = {e["name"].upper().strip() for e in _pp["current_employees"] if e.get("name")}
HIDDEN = "Individual (name hidden)"


n_hidden = 0
HIDDEN_NAMES = set()   # used by the leak check below
# Decide once per payee name: a payee with a City contract anywhere is a business everywhere.
_has_contract = defaultdict(bool)
for dd in ven["departments"].values():
    for rows in dd["families"].values():
        for v in rows:
            _has_contract[(v[0] or "").upper().strip()] |= bool(v[1])
EMP_NAMES = EMP_NAMES | people_by_description(
    (v[0], v[4]) for dd in ven["departments"].values() for rows in dd["families"].values() for v in rows)
IS_BIZ = {nm: is_business(nm, hc, EMP_NAMES) for nm, hc in _has_contract.items()}
for dnum, dd in ven["departments"].items():
    # Finance General payments (pensions, health insurer, banks...) and the rare voucher prefix with
    # no budget department (e.g. one $4,725 row under "29") go on the City root so every row is reachable.
    dn = dept_nodes.get(dnum.lstrip("0")) or city
    if not dn:
        print(f"  vendor payments for department {dnum} not attached (no department box)")
        continue
    items = []
    for fam, rows in dd["families"].items():
        for v in rows:
            biz = IS_BIZ[(v[0] or "").upper().strip()]
            if not biz:
                n_hidden += 1
                HIDDEN_NAMES.add((v[0] or "").upper().strip())
            items.append({"family": fam, "vendor": v[0] if biz else HIDDEN, "is_individual": not biz,
                          "contract": v[1], "amount": cents(v[2]), "payments": v[3],
                          # Individuals get a neutral label only (contract family). The original text can hold a
                          # role or a name fragment that would point to one person (build/payee.py).
                          "description": v[4] if biz else neutral_description(fam)})
    items.sort(key=lambda x: -x["amount"])
    dn.side.append({"kind": "vendors_paid", "label": VEN_LABEL, "period": VEN_LABEL, "basis": "actual",
                    "amount": sum(i["amount"] for i in items),
                    "source": {"dataset": "s4vu-giwb", "note": "deduplicated, research/payments_dedupe.md. "
                               "Names of individual people are hidden (build/payee.py)."},
                    "items": items, "n_items": len(items),
                    "n_individuals": sum(1 for i in items if i["is_individual"])})
print(f"vendor rows with name hidden (individual people): {n_hidden:,}")

# ---------------------------------------------------------------- side info: 2025 pay and vacancies by title
comp = json.load(open(P("data/comp_city_2025.json")))
gidx = {}
for g in comp.get("groups", []):
    gidx[(str(g.get("dept_code") or g.get("department_code") or "").lstrip("D0"), str(g.get("title_code") or "").lstrip("T"))] = g
n_comp = 0
for n in city.walk():
    if n.kind == "job_title":
        a = n.parent
        while a is not None and a.kind != "department":
            a = a.parent
        if not a:
            continue
        key = (a.extra.get("dept_number", ""), str(n.extra.get("title_code", "")))
        g = gidx.get(key)
        if g:
            n.side.append({"kind": "pay_2025", "label": "Actual pay in 2025 for this job title (no names)",
                           "period": "2025", "basis": "actual", "source": {"dataset": "dawh-m56b, xzkq-xp2w, 9v3e-pcjs"},
                           "group": {k: v for k, v in g.items() if k not in ("names",)}})
            n_comp += 1
print(f"job titles with 2025 pay side info: {n_comp}")

# ---------------------------------------------------------------- why sentences for remaining big leaves
WHY_TWICE = ("This money moves from one city account to another before it is spent, so counting it here "
             "would count the same dollar twice. It is spent (and counted) where it lands.")
for n in twice.walk():
    if not n.children:
        n.why = WHY_TWICE
lv = json.load(open(P("data/leaves_over_10m.json")))["leaves"]
# exact match on the inventory's path: City > Local|Grants > fund > department > authority > "acct desc"
why_by_path = {}
for l in lv:
    if l["budget"] == "City" and l.get("why_cant_go_deeper"):
        why_by_path[l["path"]] = l["why_cant_go_deeper"]
for r in app:
    k = (r["fund_code"], r["department_number"].lstrip("0"), r["appropriation_authority"], r["appropriation_account"])
    n = ordline.get(k)
    if n is not None:
        n.extra["inv_path"] = " > ".join(["City", r["fund_type"].title(), r["fund_description"], r["department_description"],
                                          r["appropriation_authority_description"],
                                          f"{r['appropriation_account']} {r['appropriation_account_description']}"])
DEFAULT_WHY = {
    "Grant money not yet assigned to projects": "The City has promises of grant money, but it has not published which projects each dollar will pay for yet.",
    "Contracts and services": "The budget gives one amount for this kind of contract, and the public payment records do not split it into smaller pieces tied to this line.",
    "Construction": "The budget sets aside one amount for building work, and the project-by-project list is not published with it.",
    "Overtime": "Overtime is paid hour by hour as it happens, so the budget only sets one total for the year.",
    "Other worker pay and benefits": "This is one budget amount for a kind of worker pay, and the City does not publish it split into smaller pieces.",
    "Programs and other costs": "The budget gives this program one amount and does not list what each piece of it buys.",
}
# Sentences chosen by what the line actually is (account name), checked before the generic ones.
WHY_BY_ACCOUNT = [
    (("For Interest on Loans", "For Payment on Loans"), "This repays low-interest loans the City took from the State of Illinois (Illinois EPA) to fix water and sewer pipes. The State publishes each loan's rate and balance, which are shown beside this box, but not how much of each loan is paid this year, so it stays one total."),
    (("Delegate Agencies",), "This money goes out as grants to many neighborhood nonprofits. The budget gives one total, and the list of which group gets what is decided during the year."),
    (("Rehabilitation Loans and Grants", "Loans and Grants", "Loan"), "This money is lent or granted to many homeowners and builders during the year, so the budget can only give one total."),
    (("Emergency Medical Transportation",), "This pays for ambulance trips and their billing for the whole year, so it is one total in the budget, not a list of trips."),
    (("Scheduled Wage Adjustments",), "This is money set aside for raises and back pay in union contracts. Who gets how much is worked out when the contracts are settled, so the budget only shows one total."),
    (("Professional and Technical Services",), "This pays outside experts and companies for many different jobs. The budget gives one amount, and the City does not publish which contract each dollar of this line pays for."),
    (("Information Technology",), "This pays for computer systems and their upkeep. The budget gives one amount, and the City does not list each system's cost on this line."),
    (("Electricity", "Natural Gas", "Water", "Fuel", "Gasoline", "Diesel"), "This is a utility or fuel bill for the whole year. It is paid as it is used, so the budget only gives one total."),
    (("Material and Supplies", "Supplies"), "This buys supplies all year long in many small orders, so the budget only gives one total."),
    (("Rental of Equipment", "Repair/Maintenance", "Repair or Maintenance", "Maintenance of Equipment"), "This pays for renting and fixing equipment and buildings as needs come up during the year, so the budget only gives one total."),
    (("Construction of Buildings", "Construction"), "This is money for building projects. Payments so far this year do not match it to one company yet, and the City does not publish a project-by-project list with this line."),
    (("For Payment of Bonds",), "This pays back the main amount of money the City borrowed through bonds this year. The bonds behind this line are not printed one by one in the public papers we found."),
    (("For Interest on Bonds",), "This is the interest the City pays this year to the people who lent it money through bonds. The bonds behind this line are not printed one by one in the public papers we found."),
    (("Claims", "Judgments"), "This pays legal claims and court judgments as they are settled during the year, so the budget only gives one total."),
    (("Insurance",), "This pays insurance bills for the whole year, so the budget gives one total."),
    (("Reserve Balance",), "The City has promises of grant money for this program, but it has not published which projects each dollar will pay for yet."),
    (("Net Proceeds of the Real Property Transfer Tax - CTA",), "This is the CTA's share of a tax people pay when they sell a home or building. The City passes it straight to the CTA, so there is nothing smaller to show here."),
    (("Salary Provision",), "This is pay set aside for jobs and pay changes that are not yet tied to a specific job title, so the budget only shows one total."),
    (("Fire Stations and Training Facilities",), "This is one fund for fixing and improving fire stations and training buildings. The list of which station gets what is decided during the year."),
    (("Property Maintenance Contract",), "This is one yearly contract to run and maintain the building. The contract does not split its price into smaller public pieces."),
]
WHY_BY_KIND = {
    "bond_part": "This is one bond's yearly interest or principal payment, already as small as the bond itself.",
}
WHY_ADJ = {
    "Budgeted turnover": "This is a planned saving: the budget expects some jobs to be empty for part of the year, so it subtracts the pay it will not need.",
    "Adjustment the budget office": "The official total subtracts this much more than we could match to any budget line. We asked how it is figured and show it here so the boxes add up to the official total.",
    "Budgeted vacancy savings": "This is this division's share of the planned saving from jobs that will be empty for part of the year.",
    "Less Corporate Fund Savings": "This is a planned saving the budget subtracts from the City's main fund.",
    "Bond papers list more": "The bond papers were printed before some older bonds were paid off early, so they list a little more than the budget. This box keeps the total equal to the budget.",
}


def why_for(n, st):
    nm = (n.extra or {}).get("official_name") or n.name
    for keys, sentence in WHY_BY_ACCOUNT:
        if any(k.lower() in nm.lower() for k in keys):
            return sentence
    return DEFAULT_WHY.get(st)


for n in city.walk():
    if n.children or n.amount is None or abs(n.amount) < 1_000_000_000:
        continue
    if n.eff("basis") == "adjustment":
        if not n.why:
            n.why = next((s for k, s in WHY_ADJ.items() if n.name.startswith(k)), None)
        continue
    if n.why:
        continue
    if n.kind in ("pay_rate", "job_title") and n.count:
        n.why = (f"These are {n.count:,.0f} {n.unit_label or 'positions'} paid the same rate. Each one is well under "
                 f"$1 million, and we do not show the names of individual workers.")
        continue
    if n.kind == "bond_series":
        n.why = WHY_BOND
        continue
    if n.kind in WHY_BY_KIND:
        n.why = WHY_BY_KIND[n.kind]
        continue
    if n.name == "For Payment of Bonds" and n.extra.get("fund") == "0100":
        n.why = ("This is money from the City's main fund that pays part of the City's general bonds. The same "
                 "bonds are listed under the bond fund, so this line is the main fund's share.")
        continue
    if n.name.startswith("Less Corporate Fund Savings"):
        n.why = WHY_ADJ["Less Corporate Fund Savings"]
        continue
    st = n.parent.parent.name if n.parent is not None and n.parent.parent is not None else ""
    # specific-by-account sentences first; the inventory's sentence is used only when it was written
    # for this same line, then generic ones.
    inv = why_by_path.get((n.extra or {}).get("inv_path", ""))
    n.why = why_for(n, st) if (n.kind == "line") else (inv or why_for(n, st))
    n.why = n.why or inv or "The public budget lists this as one amount, and we could not find public records that split it further."

# ---------------------------------------------------------------- cleanup (after all splits)
from treelib import cleanup, tag_projects_on_several_lines  # noqa: E402
city.rollup()
# Tag a project that is a box on several budget lines. The TIP project 01-24-0017 (Calumet River Bridges) covers four
# bridges. The City's grant ledger has a record for one of them (106th Street, project E9293), matched by the name
# in the TIP description, so the note says so.
tag_projects_on_several_lines(city, same_project={"01-24-0017": (
    "E9293", "The grant ledger record (project E9293) is for the 106th Street bridge only. The regional plan project "
             "01-24-0017 covers four Calumet River bridges (92nd, 95th, 100th and 106th Streets), so the ledger amount is part "
             "of the same bridge program, matched by name.")})
cleanup(city)
from treelib import disambiguate_siblings  # noqa: E402
print(f"memo branch: {disambiguate_siblings(twice)} same-name siblings relabelled")

# ---------------------------------------------------------------- checks + save
twice.rollup()
city.rollup()
problems = check(city, expected_total_cents=cents(OFFICIAL_NET))
problems += check(twice)
# twice + city + unexplained must equal the gross ordinance
gross_check = city.amount + twice.amount + cents(UNEXPLAINED)
if gross_check != cents(OFFICIAL_GROSS):
    problems.append(f"city + twice + unexplained = {gross_check/100:,.2f} != gross {OFFICIAL_GROSS:,}")
# no actuals in amounts
for n in city.walk():
    if n.eff("basis") == "actual":
        problems.append(f"actual basis inside totals at {n.id}")
# privacy check: every payment to a hidden individual carries only a neutral description label
n_ind_rows = 0
for n in city.walk():
    for sd in n.side:
        for it in sd.get("items") or []:
            if isinstance(it, dict) and (it.get("is_individual") or it.get("vendor") == HIDDEN):
                n_ind_rows += 1
                # pooled rows ("Individual (name hidden)", amount, vouchers) carry no description at all
                if ("description" in it or it.get("is_individual")) \
                        and it.get("description") not in ALLOWED_INDIVIDUAL_DESCRIPTIONS:
                    problems.append(f"individual payment with a non-neutral description at {n.id}")
                    break
print(f"privacy check: {n_ind_rows:,} hidden-individual rows, no description other than a neutral label"
      if not any("non-neutral" in x for x in problems) else "privacy check FAILED")
# names check: tokenise every string in the output and look for exact employee-name strings
blob_strings = set()
for row in to_rows(city) + side_rows(city) + to_rows(twice):
    for v in row.values():
        if isinstance(v, str):
            for m in re.findall(r'"([^"]{6,80})"', v):
                blob_strings.add(m.upper().strip())
            blob_strings.add(v.upper().strip())
leak = sorted(nm for nm in (EMP_NAMES | HIDDEN_NAMES) if len(nm) > 8 and nm in blob_strings)
if leak:
    problems.append(f"{len(leak)} employee names in output, e.g. {leak[:3]}")

dr = depth_report(city)
print("depth:", json.dumps(dr))
print("top level:")
for c in city.children:
    print(f"   {c.amount/100:>18,.2f}  {c.name}")
print(f"   {twice.amount/100:>18,.2f}  {twice.name} (memo)")
if problems:
    print(f"FAILED: {len(problems)} problems")
    for p in problems[:40]:
        print("  -", p)
    sys.exit(1)

os.makedirs(P("build/out"), exist_ok=True)
save_json(city, P("build/out/city_tree.json"))
save_json(twice, P("build/out/city_twice_tree.json"))
db = P("data/budget.db")
rows = to_rows(city) + to_rows(twice)
for r in rows:
    if r["id"].startswith("city-twice"):
        r["gov"] = "city"
load_into_db(db, "city", rows, side_rows(city) + side_rows(twice),
             ("city", datetime.now(timezone.utc).isoformat(), len(rows), city.amount, cents(OFFICIAL_NET), 0, json.dumps(dr)))
print(f"OK: {len(rows):,} rows written to {db}")
