"""Mid-Year Report contracts data (DOF) -> City tree detail.

Inputs : raw/midyear/DOF_Contracts_Data_for_2026_Mid-Year_Budget_Report.xlsx  (invoices created in 2025)
         raw/midyear/Mid-Year-Report_Contracts_Data_2025.xlsx                  (invoices Feb 2023 to Jul 2025)
         data/city_vendors_items_2026ytd.json   (deduplicated 2026 YTD payments by vendor and contract, through 09/28/2026)
         raw/city_appropriations_2026.json      (2026 ordinance lines, dataset 6694-f78c)
         build/out/city_tree.json               (built tree, used only to see which lines are still unsplit)
Outputs: data/splits/city/paid_to_date_midyear.json   boxes: 2026 YTD payments on single-line contracts, paid_to_date
         data/splits/city/midyear_2025_vendors.json   side info only: "in 2025 this line paid these companies" and a
                                                      labelled estimate for contracts the City spread over several lines
         data/midyear_contract_line_map.csv           contract number -> budget line(s), shares, class (no vendor names)
         data/midyear_report.json                     totals used in research/midyear_contracts.md
Run    : python3 scripts/midyear_build.py     (after one `bash build/build_all.sh` so build/out/city_tree.json exists;
         safe to rerun: lines that already carry this script's boxes stay eligible)

HOW A CONTRACT IS PLACED (guardrails, see research/midyear_contracts.md)
 1. Code mapping. A distribution row maps to an ordinance line when its Fund + department (first 3 digits of Cost Center)
    + Appr equal an ordinance (fund, department, appropriation account). If one authority has that triple, that is the line.
    If several do, the last 4 digits of Cost Center must equal one of them, else the row is unmapped. The row's 6-digit
    Account column is not used.
 2. Only the contract's invoices created in 2025 on a purchase order of budget year 2025 (BFY 025) are used.
 3. SINGLE_THRESHOLD: a contract is single-line only if 95% or more of those 2025 dollars sit on ONE mapped line.
 4. The line must exist in the 2026 ordinance (follows from 1) and still be an unsplit leaf of the tree.
 5. Contracts already placed by data/splits/city/paid_to_date.json are skipped (no payment shows twice).
 6. If the payments placed on a line are more than GUARD times the line, nothing is placed (match evidently wrong).
    Up to GUARD, a negative "Already spent more than the budget" box keeps the sum right.
Names: build/payee.py is_business(), one decision per payee, as build/city_tree.py does.
"""
import collections
import csv
import json
import os
import re
import sys

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "build"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import contracts_build as cb  # noqa: E402
import paidtodate_build as pt  # noqa: E402
from payee import is_business  # noqa: E402

P = lambda *a: os.path.join(ROOT, *a)  # noqa: E731
MID = P("raw/midyear")
SRC26 = os.path.join(MID, "DOF_Contracts_Data_for_2026_Mid-Year_Budget_Report.xlsx")
SRC25 = os.path.join(MID, "Mid-Year-Report_Contracts_Data_2025.xlsx")
SINGLE_THRESHOLD = 0.95
GUARD = 2.0
HIDDEN = "Individual (name hidden)"
NOTE_CODED = "Matched to this line using how the City coded this contract's 2025 invoices."
URL_PAGE = "https://www.chicago.gov/city/en/depts/fin/supp_info/mid-year-report-contracts-data.html"
TOP_N = 10


def load_file(xlsx, tag):
    """Read the workbook once into a lean CSV (26 columns, blank rows dropped), then the CSV."""
    csv_path = os.path.join(MID, f"contracts_{tag}.lean.csv")
    if not os.path.exists(csv_path):
        import openpyxl
        wb = openpyxl.load_workbook(xlsx, read_only=True)
        ws = wb.worksheets[0]
        with open(csv_path, "w", newline="") as f:
            w = csv.writer(f)
            for i, row in enumerate(ws.iter_rows(values_only=True)):
                row = list(row[:26])
                if i > 0 and not row[0]:
                    continue
                w.writerow(["" if v is None else v for v in row])
    d = pd.read_csv(csv_path, dtype=str, keep_default_na=False, na_values=[""])
    d.columns = [c.strip() for c in d.columns]
    d = d[d["Vendor Name"].notna()].copy()
    d["amt"] = d["AP Invoice Dist Amount"].astype(float)
    d["inv"] = d["AP Invoice Amount"].astype(float)
    d["dt"] = pd.to_datetime(d["AP Voucher Creation Date"])
    d["dept"] = d["Cost Center"].str[:3].astype(int).astype(str)
    d["cc4"] = d["Cost Center"].str[3:]
    d["contract"] = d["Contract or Agreement  Number"].str.strip()
    d["voucher"] = d["AP Batch / Voucher Number"]
    d["bfy"] = d["BFY"].map(lambda s: (2000 + int(s)) if int(s) < 50 else (1900 + int(s)))
    return d


def union_and_clean(d6, d5):
    """Union by voucher number (the 2026 file wins), then drop exact copies of a row only where that brings the
    invoice's distributions closer to the invoice amount (caveat 1 in research/midyear_contracts.md)."""
    d5x = d5[~d5["voucher"].isin(set(d6["voucher"]))]
    d6 = d6.assign(src="2026file")
    d5x = d5x.assign(src="2025file")
    a = pd.concat([d6, d5x], ignore_index=True)
    cols = list(d6.columns[:26]) + ["src"]
    key = ["voucher", "AP Invoice Number", "contract"]
    a["gid"] = a.groupby(key, sort=False).ngroup()
    dup = a.duplicated(subset=cols, keep="first")
    orig = a.groupby("gid").amt.sum()
    inv = a.groupby("gid").inv.first()
    dd = a[~dup].groupby("gid").amt.sum().reindex(orig.index).fillna(0)
    better = (dd - inv).abs() < (orig - inv).abs() - 0.005
    drop = dup & a["gid"].map(better)
    return a[~drop].copy(), int(drop.sum()), float(a[drop].amt.sum()), len(d6), len(d5x)


def ordinance():
    ap = json.load(open(P("raw/city_appropriations_2026.json")))
    by = collections.defaultdict(list)
    amt = {}
    names = {}
    for r in ap:
        dep = r["department_number"].lstrip("0") or "0"
        k = (r["fund_code"], dep, r["appropriation_authority"], r["appropriation_account"])
        by[(r["fund_code"], dep, r["appropriation_account"])].append(r["appropriation_authority"])
        amt[k] = int(round(float(r["_ordinance_amount_"]) * 100))
        names[k] = (r["department_description"], r["appropriation_account_description"], r["fund_description"])
    return by, amt, names


def map_rows(a, by):
    def res(f, dp, ac, cc):
        c = by.get((f, dp, ac))
        if not c:
            return None
        if len(c) == 1:
            return (f, dp, c[0], ac)
        if cc in c:
            return (f, dp, cc, ac)
        return None
    a["line"] = [res(*x) for x in zip(a["Fund"], a["dept"], a["Appr"], a["cc4"])]


def contract_map(a):
    """Per contract: 2025 dollars (BFY 2025 PO) by mapped line."""
    r = a[(a.dt >= "2025-01-01") & (a.dt < "2026-01-01") & (a.bfy == 2025)]
    out = {}
    for c, g in r.groupby("contract"):
        tot = float(g.amt.sum())
        sh = g[g.line.notna()].groupby("line").amt.sum()
        out[c] = {"total": tot, "shares": {k: float(v) for k, v in sh.items()}, "rows": len(g)}
    return out


def classify(m):
    t = m["total"]
    if t <= 0 or not m["shares"]:
        return "not_coded_to_a_2026_line", None
    top = max(m["shares"], key=m["shares"].get)
    if m["shares"][top] / t >= SINGLE_THRESHOLD:
        return "single", top
    if sum(m["shares"].values()) / t >= SINGLE_THRESHOLD and len(m["shares"]) > 1:
        return "multi", None
    return "low_coverage", None


def main():
    d6 = load_file(SRC26, "2026")
    d5 = load_file(SRC25, "2025ver")
    a, ndrop, ddrop, n6, n5x = union_and_clean(d6, d5)
    by, oamt, onames = ordinance()
    map_rows(a, by)
    cmap = contract_map(a)
    report = {"rows_2026file": int(len(d6)), "rows_2025file": int(len(d5)), "rows_2025file_vouchers_not_in_2026file": n5x,
              "exact_copy_rows_dropped": ndrop, "exact_copy_dollars_dropped": round(ddrop, 2),
              "rows_after_union_and_clean": int(len(a))}

    # ---- 2026 YTD items, same data and same name decisions as the vendor view and paid_to_date.json
    ven = json.load(open(P("data/city_vendors_items_2026ytd.json")))
    rem, npairs, nmiss = pt.alias_duplicate_corrections(ven)
    FULL = pt.full_descriptions() if os.path.exists(P("raw/contracts/contracts_all.csv")) else {}
    emp_path = P("data/people/city_employees_2026.json")
    emp = {e["name"].upper().strip() for e in json.load(open(emp_path))["current_employees"] if e.get("name")} if os.path.exists(emp_path) else set()
    has_contract = collections.defaultdict(bool)
    for dd in ven["departments"].values():
        for rows in dd["families"].values():
            for v in rows:
                has_contract[(v[0] or "").upper().strip()] |= bool(v[1])
    biz = {nm: is_business(nm, hc, emp) for nm, hc in has_contract.items()}
    items = []
    total_ytd = 0
    for d, dd in ven["departments"].items():
        for fam, rows in dd["families"].items():
            for v in rows:
                total_ytd += round(v[2] * 100)
                if not v[1] or v[2] <= 0:
                    continue
                name = (v[0] or "").upper().strip()
                desc = v[4] or ""
                fd = FULL.get(str(v[1]), "")
                if len(desc) >= 85 and fd.startswith(desc[:80]):
                    desc = fd
                items.append({"dept": d.lstrip("0") or "0", "family": fam, "vendor": v[0] or "", "contract": str(v[1]),
                              "amount": round(v[2] * 100), "payments": v[3], "desc": desc, "ctype": v[5], "biz": biz.get(name, False)})
    report["ytd_items_total_cents"] = total_ytd
    report["ytd_items_with_contract_cents"] = sum(i["amount"] for i in items)
    report["ytd_items_without_contract_cents"] = total_ytd - report["ytd_items_with_contract_cents"]

    # contracts already placed by the rule-based file
    prior = json.load(open(P("data/splits/city/paid_to_date.json")))
    prior_contracts = set()

    def walk(p):
        c = (p.get("extra") or {}).get("contract")
        if c:
            prior_contracts.add(str(c))
        for k in p.get("children") or []:
            walk(k)
    for s in prior["splits"]:
        for p in s["pieces"]:
            walk(p)

    # lines still available: leaf in the built tree, or already carrying this script's boxes
    tree = json.load(open(P("build/out/city_tree.json")))["rows"]
    avail = {}
    kids = collections.defaultdict(list)
    for r in tree:
        if r.get("parent_id"):
            kids[r["parent_id"]].append(r)
    for r in tree:
        if r["kind"] != "line" or not r["id"].startswith("city.") or not r["extra"]:
            continue
        e = json.loads(r["extra"])
        if "account" not in e:
            continue
        k = (e["fund"], e["dept_number"].lstrip("0") or "0", e["authority"], e["account"])
        mine = any('"midyear_contract"' in (c.get("extra") or "") or '"midyear_group"' in (c.get("extra") or "") for c in kids.get(r["id"], []))
        avail[k] = bool(r["is_leaf"]) or mine

    # ---- classify items
    cls_of = {}
    for c, m in cmap.items():
        cls_of[c] = classify(m)
    stats = collections.Counter()
    dollars = collections.Counter()
    assigned = collections.defaultdict(list)
    multi = collections.defaultdict(list)
    conflicts = []
    for it in items:
        c = it["contract"]
        if c not in cmap:
            k = "no_2025_invoices_in_files"
        else:
            k, line = cls_of[c]
            if k == "single":
                if c in prior_contracts:
                    k = "single_but_already_placed_by_rules"
                elif line not in oamt or oamt[line] <= 0:
                    k = "single_line_not_in_2026_ordinance"
                elif not avail.get(line, False):
                    k = "single_line_already_split_by_other_file"
                else:
                    assigned[line].append(it)
            elif k == "multi" and c not in prior_contracts:
                multi[c].append(it)
        stats[k] += 1
        dollars[k] += it["amount"]
        if k == "single_but_already_placed_by_rules":
            conflicts.append((c, it["amount"]))

    # guard
    placed_lines = {}
    dropped = []
    for line, its in list(assigned.items()):
        s = sum(i["amount"] for i in its)
        if s > GUARD * oamt[line]:
            dropped.append((line, s, oamt[line]))
            for i in its:
                dollars["single_line_but_paid_more_than_2x_the_line"] += i["amount"]
                stats["single_line_but_paid_more_than_2x_the_line"] += 1
                dollars["single"] -= i["amount"]
                stats["single"] -= 1
            del assigned[line]

    # ---- boxes
    splits = []
    for line, its in sorted(assigned.items(), key=lambda kv: -sum(i["amount"] for i in kv[1])):
        for i in its:
            i["rule"] = "midyear contracts data"
        f, d, au, ac = line
        sp = pt.make_split({"fund": f, "dept": d, "authority": au, "account": ac, "amount": oamt[line]}, its)
        placed = sp.pop("_placed")
        mark(sp["pieces"])
        sp["source"] = {"dataset": "s4vu-giwb", "name": "City of Chicago Payments (deduplicated, checks Jan 1 to 09/28/2026), "
                        "placed with the Department of Finance Mid-Year Report contracts data",
                        "url": URL_PAGE, "note": "research/midyear_contracts.md; payments: research/payments_dedupe.md"}
        sp["note"] = ("Vendor payments so far (checks Jan 1 to 09/28/2026, partial year) on contracts that the City coded to this exact budget line "
                      f"(same fund, department and account) on {SINGLE_THRESHOLD:.0%} or more of their 2025 invoice dollars (Department of Finance, "
                      "Contracts Data published with the 2026 Mid-Year Budget Report). " + NOTE_CODED + " The 2026 invoices themselves are not in that "
                      "file, so a few may be coded differently. Names of individual people are hidden.")
        sp["over"] = {"name": "Already spent more than the budget for this line",
                      "note": "Payments so far on contracts matched to this line are larger than the full-year budget line. " + NOTE_CODED +
                              " Some of this money may be charged to other lines in 2026, so this negative box keeps the boxes adding up to the budget."}
        sp["_amt"] = placed
        splits.append(sp)
    placed_total = sum(s.pop("_amt") for s in splits)
    json.dump({"meta": {"author": "midyear-contracts agent", "built_by": "scripts/midyear_build.py",
                        "description": "2026 YTD vendor payments (to 09/28/2026) on contracts that the City coded to exactly one 2026 budget line in 2025 "
                                       "(95%+ of the contract's 2025 invoice dollars). Source of the coding: DOF Mid-Year Report contracts data. See research/midyear_contracts.md."},
               "splits": splits}, open(P("data/splits/city/paid_to_date_midyear.json"), "w"), indent=1)

    # ---- who would be named: leak guard list
    hidden_names = {(it["vendor"] or "").upper().strip() for dd in ven["departments"].values() for rows in dd["families"].values()
                    for v in rows for it in [{"vendor": v[0]}] if not biz.get((v[0] or "").upper().strip(), False)}

    # ---- 2025 side info
    paid_lines = set(assigned)   # lines that now have boxes from this script
    prior_lines = set()
    for s in prior["splits"]:
        t = s["target"]
        prior_lines.add((t["fund"], t["dept"], t["authority"], t["account"]))
    # vendor decisions for 2025 names: has_contract only if the payee shows up with a contract in the payments
    pay_vk = {cb.vendor_key(n) for n, hc in has_contract.items() if hc}
    a25 = a[(a.dt >= "2025-01-01") & (a.dt < "2026-01-01") & a.line.notna()].copy()
    name_biz = {}
    for nm in a25["Vendor Name"].unique():
        name_biz[nm] = is_business(nm, cb.vendor_key(nm) in pay_vk, emp)
    a25["vk"] = [cb.vendor_key(n) if name_biz[n] else HIDDEN for n, in zip(a25["Vendor Name"])]
    a25["shown"] = [n if name_biz[n] else HIDDEN for n in a25["Vendor Name"]]
    for n in a25["Vendor Name"].unique():
        if not name_biz[n]:
            hidden_names.add(n.upper().strip())
    side_splits = []
    by_line = {k: g for k, g in a25.groupby("line")}
    vendor_kind_ok = lambda ac: cb.account_family(ac)[0] == "vendor" and cb.account_family(ac)[1] != "BENEFITS"  # noqa: E731
    # estimate for multi-line contracts, 2026 YTD dollars split by 2025 shares
    est = collections.defaultdict(lambda: collections.defaultdict(float))
    est_name = {}
    for c, its in multi.items():
        m = cmap[c]
        for it in its:
            for ln, v in m["shares"].items():
                est[ln][(c, it["vendor"] if it["biz"] else HIDDEN)] += it["amount"] * v / m["total"]
    n_side25 = n_sideest = 0
    for line in sorted(set(by_line) | set(est)):
        if line in paid_lines or line in prior_lines or line not in oamt or oamt[line] <= 0 or not avail.get(line, False):
            continue
        if not vendor_kind_ok(line[3]):
            continue
        side = []
        g = by_line.get(line)
        if g is not None and g.amt.sum() > 0:
            tot = float(g.amt.sum())
            vs = g.groupby("vk").agg(name=("shown", "first"), amt=("amt", "sum"), n=("voucher", "nunique")).sort_values("amt", ascending=False)
            vs = vs[vs.amt > 0]
            top = vs.head(TOP_N)
            rows_ = [{"vendor": r.name, "amount": int(round(r.amt * 100)), "vouchers": int(r.n)} for r in top.itertuples()]
            # hidden individuals are pooled into one row
            ind = vs[vs.name == HIDDEN]
            rows_ = [r for r in rows_ if r["vendor"] != HIDDEN]
            if len(ind):
                rows_.append({"vendor": HIDDEN, "amount": int(round(ind.amt.sum() * 100)), "vouchers": int(ind.n.sum()), "people": int(len(ind))})
            side.append({"kind": "paid_2025_vendors",
                         "label": f"In 2025 this line paid these companies (largest {len(rows_)} of {len(vs)} payees). Invoices created in 2025 whose City accounting codes (fund, department, account) match this line, from the Department of Finance contracts data.",
                         "amount": round(tot, 2), "period": "2025 invoices", "basis": "actual",
                         "source": {"doc": "Contracts Data as published with the 2026 Mid-Year Budget Report (Dept of Finance)", "url": URL_PAGE,
                                    "note": "research/midyear_contracts.md. Invoice amounts, not checks, so they can differ a little from the payments dataset. Names of individual people are hidden."},
                         "top_share": round(float(top.amt.sum() / tot), 4) if tot else None,
                         "items": rows_, "n_payees": int(len(vs))})
            n_side25 += 1
        if line in est and not (g is not None and False):
            e = sorted(est[line].items(), key=lambda kv: -kv[1])
            tot = sum(v for _, v in e)
            if tot >= 1000:
                side.append({"kind": "estimate_2026_multi_line_contracts",
                             "label": "ESTIMATE, not in the boxes. 2026 payments so far on contracts that the City split over several budget lines in 2025, divided by each contract's 2025 shares. The 2026 split may differ.",
                             "amount": round(tot, 2), "period": "paid Jan 1 to 09/28/2026 (partial year)", "basis": "proxy",
                             "source": {"doc": "Payments s4vu-giwb (deduplicated) with 2025 line shares from the Dept of Finance Mid-Year contracts data", "url": URL_PAGE},
                             "items": [{"vendor": nm, "contract": c, "amount": int(round(v * 100))} for (c, nm), v in e[:TOP_N]], "n_contracts": len(e)})
                n_sideest += 1
        if side:
            f, d, au, ac = line
            side_splits.append({"target": {"by": "ordinance_line", "fund": f, "dept": d, "authority": au, "account": ac},
                                "expect_amount": oamt[line] / 100, "mode": "side_only", "side": side})
    json.dump({"meta": {"author": "midyear-contracts agent", "built_by": "scripts/midyear_build.py",
                        "description": "Side info only (not added into any box): 2025 payees by budget line from the DOF Mid-Year contracts data, and labelled estimates for multi-line contracts."},
               "splits": side_splits}, open(P("data/splits/city/midyear_2025_vendors.json"), "w"), indent=1)

    # ---- leak guard on what we wrote
    blob = (open(P("data/splits/city/paid_to_date_midyear.json")).read() + open(P("data/splits/city/midyear_2025_vendors.json")).read()).upper()
    leaks = sorted(n for n in (hidden_names | emp) if len(n) > 8 and f'"{n}"' in blob)
    if leaks:
        print("FAIL: hidden or employee names written:", leaks[:5])
        sys.exit(1)

    # ---- contract -> line map (no vendor names)
    with open(P("data/midyear_contract_line_map.csv"), "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["contract", "class", "invoice_dollars_2025_bfy2025", "top_line", "top_share", "n_lines", "lines_with_dollars", "used_in_boxes"])
        placed_c = {i["contract"] for its in assigned.values() for i in its}
        for c, m in sorted(cmap.items(), key=lambda kv: -kv[1]["total"]):
            k, line = cls_of[c]
            top = max(m["shares"], key=m["shares"].get) if m["shares"] else None
            fmt = lambda l: "-".join(l)  # noqa: E731
            w.writerow([c, k, round(m["total"], 2), fmt(top) if top else "", round(m["shares"][top] / m["total"], 4) if top and m["total"] > 0 else "",
                        len(m["shares"]), ";".join(f"{fmt(l)}={round(v, 2)}" for l, v in sorted(m["shares"].items(), key=lambda kv: -kv[1])[:8]),
                        "yes" if c in placed_c else ""])
    report.update({
        "contracts_in_files_bfy2025": len(cmap),
        "contract_classes_all": dict(collections.Counter(k for k, _ in cls_of.values())),
        "item_stats": dict(stats), "item_dollars_cents": dict(dollars),
        "placed_cents": placed_total, "lines_with_boxes": len(splits), "contracts_placed": sum(len({i['contract'] for i in its}) for its in assigned.values()),
        "guard_dropped": [[list(l), s, a_] for l, s, a_ in dropped],
        "conflicts_with_rule_file": {"contracts": len(conflicts), "cents": sum(x for _, x in conflicts)},
        "side_2025_lines": n_side25, "side_estimate_lines": n_sideest,
    })
    json.dump(report, open(P("data/midyear_report.json"), "w"), indent=1, default=str)
    print(json.dumps({k: v for k, v in report.items() if k not in ("guard_dropped",)}, indent=1, default=str))
    print("guard dropped:", report["guard_dropped"])


def mark(pieces):
    """Tag every piece so a rerun can recognise this script's boxes, and say how the match was made."""
    for p in pieces:
        p["extra"] = dict(p.get("extra") or {})
        p["extra"]["midyear_contract"] = True
        if p.get("kind") == "vendor_group":
            p["extra"]["midyear_group"] = True
        p["note"] = ((p.get("note") or "") + " " + NOTE_CODED).strip()
        if p.get("children"):
            mark(p["children"])


if __name__ == "__main__":
    main()
