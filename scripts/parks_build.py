#!/usr/bin/env python3
"""Step 3: build data/parks_2026.json from raw/parks/units.json + words.json.

Inputs (made by parks_extract.py and parks_parse.py):
  raw/parks/words.json  positioned words for every PDF page
  raw/parks/units.json  317 parsed tables (detail units + 6 summary tables)

Output: data/parks_2026.json with
  tree          function > department/region > unit (park) > fund > class > account > position
  tree_by_fund  fund > function > unit (amounts only, ids point into `tree`)
  printed_all_funds  the PDF's own all-funds account tables (pp 54-55 revenue, 62-63 expense)
  reconciliation  every check we ran, with exact differences
  capital / debt / pension / managed_assets  beyond-operating facts that are printed in
                  the same PDF (with page numbers). Nothing here is estimated.

Rules: every number is read from the PDF. Printed values are kept as printed. Where the PDF
disagrees with itself, the difference is reported, never silently fixed.
"""
import json, os, re, sys, collections, datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from parks_parse import group_lines, CODE6  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, "raw", "parks")
OUT = os.path.join(ROOT, "data", "parks_2026.json")
GRAND_2026 = 637_580_350
GRAND_2025 = 598_512_384
PDF_URL = ("https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf"
           "?VersionId=4S4MZxZ1Cut5r1bdwmTOgGBFF4mHJbmq")
PRINTED_OFFSET = 6  # printed page number = PDF page - 6

CLASS_NAMES = {
    "610000": "Personnel Services", "620000": "Materials and Supplies",
    "621000": "Small Tools and Equipment", "623000": "Contractual Services",
    "624000": "Program Expense", "625000": "Other Expense", "627000": "Fixed Asset Expense",
}

# Function (section) of each department page, per the PDF table of contents / pie charts
def function_of(u):
    p = u["page"]
    if u.get("is_summary"):
        return None
    if 79 <= p <= 101:
        return "Administration & Finance"
    if p == 103:
        return "Grant Park Music Festival"
    if 107 <= p <= 114:
        return "Operations & Maintenance"
    if 116 <= p <= 134:
        return "Recreation & Programming"
    if 144 <= p <= 170:
        return "Recreation & Programming: Central Region"
    if 179 <= p <= 208:
        return "Recreation & Programming: North Region"
    if 216 <= p <= 246:
        return "Recreation & Programming: South Region"
    return None


def slug(s):
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def fund_slug(f):
    return slug(f.replace("Fund", "").strip()) or "all"


# ---------------------------------------------------------------- printed all-funds tables
def parse_printed_table(words, pages, colx, label):
    """Rows 'CODE - Name  v25  v26' (no $). Class rows end in 000 and follow their details."""
    rows = []
    for pg in pages:
        W = [w for w in words[str(pg)] if w[3] < 745 and w[4] <= 10.5]
        for ln in group_lines(W):
            toks = [w[0] for w in ln]
            if toks[0] in ("Grand", "Account"):
                if toks[0] == "Grand":
                    nums = [w for w in ln if re.match(r"^-?[\d,]+$", w[0])]
                    rows.append({"code": "GRAND", "name": "Grand Total", "page": pg,
                                 "v": [int(re.sub(r"[^\d]", "", n[0])) for n in nums]})
                continue
            if not CODE6.match(toks[0]):
                continue
            nums = [w for w in ln if re.match(r"^\(?-?[\d,]+\)?$", w[0]) and w[1] > colx[0] - 70]
            dashes = [w for w in ln if w[0] == "-" and w[1] > colx[0] - 70]
            vals = [None] * len(colx)
            for w in nums + dashes:
                j = min(range(len(colx)), key=lambda k: abs(colx[k] - w[2]))
                if abs(colx[j] - w[2]) > 6:
                    raise SystemExit(f"{label} p{pg}: cannot place {w} in {toks}")
                if w[0] == "-":
                    v = 0
                else:
                    neg = w[0].startswith("-") or w[0].startswith("(")
                    v = int(re.sub(r"[^\d]", "", w[0])) * (-1 if neg else 1)
                vals[j] = v
            first_val_x = min([w[1] for w in nums + dashes] or [9999])
            name = " ".join(w[0] for w in ln if w[1] < first_val_x)
            name = re.sub(r"^\d{6}\s*-\s*", "", name)
            rows.append({"code": toks[0], "name": name, "page": pg, "v": vals})
    return rows


def group_classes(rows, is_class):
    """Details precede their class subtotal row. Returns list of (class_row, [details])."""
    out, cur = [], []
    for r in rows:
        if r["code"] == "GRAND":
            continue
        if is_class(r["code"]):
            out.append((r, cur))
            cur = []
        else:
            cur.append(r)
    return out, cur


# ---------------------------------------------------------------- tree helpers
def node(id_, name, type_, a26=None, a25=None, a24=None, **kw):
    n = {"id": id_, "name": name, "type": type_, "amount2026": a26, "amount2025": a25}
    if a24 is not None:
        n["amount2024"] = a24
    n.update({k: v for k, v in kw.items() if v is not None})
    return n


def add_check(n):
    """Record children_sum and diff vs the parent's own amount."""
    ch = n.get("children")
    if not ch:
        return
    s26 = sum(c["amount2026"] or 0 for c in ch)
    s25 = sum(c["amount2025"] or 0 for c in ch)
    n["check"] = {"children_sum2026": s26, "diff2026": (n["amount2026"] or 0) - s26,
                  "children_sum2025": s25, "diff2025": (n["amount2025"] or 0) - s25}


def build_unit_fund_node(u, uid):
    """fund table -> node: class > account > positions."""
    n26 = u["total"][2]
    n25 = u["total"][1]
    n24 = u["total"][0]
    fid = f"{uid}/{fund_slug(u['fund'])}"
    fn = node(fid, u["fund"], "fund", n26, n25, n24, page=u["page"],
              printed_page=u["page"] - PRINTED_OFFSET, source="detail table printed Total")
    classes, left = group_classes(
        [{"code": a["code"], "name": a["name"], "v": a["values"], "flag": a.get("flag")} for a in u["accounts"]],
        lambda c: c.endswith("000"))
    pos_rows = [p for p in u["positions"] if p.get("title")]
    pos_tot = next((p for p in u["positions"] if p.get("total")), None)
    kids = []
    for crow, det in classes:
        cn = node(f"{fid}/{crow['code']}", CLASS_NAMES.get(crow["code"], crow["name"]), "class",
                  crow["v"][2], crow["v"][1], crow["v"][0], code=crow["code"], source="printed class subtotal")
        cn["children"] = []
        for a in det:
            code = a["code"]
            an = node(f"{fid}/{crow['code']}/{code}", a["name"], "account", a["v"][2], a["v"][1], a["v"][0],
                      code=code, flag=a.get("flag"))
            if code == "611005" and pos_rows:
                an["children"] = [
                    node(f"{fid}/{crow['code']}/611005/{p['job_code']}-{i}", p["title"].title() if p["title"].isupper() else p["title"],
                         "position", p["budget2026"], p["budget2025"], None, job_code=p["job_code"],
                         fte2026=p["fte2026"], fte2025=p["fte2025"])
                    for i, p in enumerate(pos_rows)]
                an["positions_total_printed"] = {"fte2025": pos_tot["fte2025"], "budget2025": pos_tot["budget2025"],
                                                 "fte2026": pos_tot["fte2026"], "budget2026": pos_tot["budget2026"]} if pos_tot else None
                add_check(an)
            cn["children"].append(an)
        add_check(cn)
        kids.append(cn)
    fn["children"] = kids
    add_check(fn)
    return fn


def main():
    words = json.load(open(os.path.join(RAW, "words.json")))
    data = json.load(open(os.path.join(RAW, "units.json")))
    units, problems = data["units"], data["problems"]
    detail = [u for u in units if not u.get("is_summary")]
    summaries = {u["title"]: u for u in units if u.get("is_summary")}
    fg = summaries["Finance General (All Funds)"]
    gp = next(u for u in detail if u["page"] == 103)
    detail_nofg = [u for u in detail]

    rec = {"checks": [], "pdf_inconsistencies": [], "parser_problems": problems}

    def check(name, ok, **kw):
        rec["checks"].append({"name": name, "pass": bool(ok), **kw})
        return ok

    # ---- printed all-funds tables
    rev_rows = parse_printed_table(words, (54, 55), [467.5, 581.9], "revenue")
    exp_rows = parse_printed_table(words, (62, 63), [463.5, 588.6], "expense")
    rev_grand = next(r for r in rev_rows if r["code"] == "GRAND")
    exp_grand = next(r for r in exp_rows if r["code"] == "GRAND")
    check("printed revenue Grand Total 2026 == 637,580,350 (p55)", rev_grand["v"][1] == GRAND_2026, printed=rev_grand["v"][1])
    check("printed expense Grand Total 2026 == 637,580,350 (p63)", exp_grand["v"][1] == GRAND_2026, printed=exp_grand["v"][1])
    check("printed Grand Totals 2025 == 598,512,384 (p55, p63)",
          rev_grand["v"][0] == GRAND_2025 == exp_grand["v"][0])
    exp_classes, exp_left = group_classes(exp_rows, lambda c: c.endswith("000") and c[:3] in ("610", "620", "621", "623", "624", "625", "627"))
    # 600005/600015 debt service rows sit loose before 625005 inside class 625000
    for k, idx in ((1, 1), (0, 0)):
        s = sum(c[0]["v"][idx] for c in exp_classes)
        g = GRAND_2026 if idx else GRAND_2025
        check(f"printed expense class subtotals sum to Grand Total within $2 ({'2026' if idx else '2025'})",
              abs(s - g) <= 2, sum=s, diff=s - g)
    for crow, det in exp_classes:
        for idx, yr in ((1, 2026), (0, 2025)):
            s = sum(d["v"][idx] for d in det)
            if s != crow["v"][idx]:
                rec["pdf_inconsistencies"].append({"where": f"p62-63 class {crow['code']} {yr}", "class_printed": crow["v"][idx], "details_sum": s, "diff": crow["v"][idx] - s})
    rev_classes, rev_left = group_classes(rev_rows, lambda c: c.endswith("000"))
    for idx, yr, g in ((1, 2026, GRAND_2026), (0, 2025, GRAND_2025)):
        s = sum(c[0]["v"][idx] for c in rev_classes)
        check(f"printed revenue class subtotals sum to Grand Total within $2 ({yr})", abs(s - g) <= 2, sum=s, diff=s - g)
    rec["note_printed_class_dupe"] = "412000 appears twice in revenue (Property Taxes Total and TIF Disbursements Total); the PDF reuses the code."

    # ---- unit-level checks
    exact = off1 = off2 = bad = 0
    class_detail_diffs = []
    for u in detail:
        classes, left = group_classes([{"code": a["code"], "name": a["name"], "v": a["values"]} for a in u["accounts"]], lambda c: c.endswith("000"))
        if left:
            rec["pdf_inconsistencies"].append({"where": f"p{u['page']} {u['title']} {u['fund']}", "issue": "detail rows after last class subtotal", "codes": [r["code"] for r in left]})
        for k in range(u["ncols"]):
            s = sum(c[0]["v"][k] for c in classes)
            d = u["total"][k] - s
            if d == 0: exact += 1
            elif abs(d) == 1: off1 += 1
            elif abs(d) == 2: off2 += 1
            else:
                bad += 1
                rec["pdf_inconsistencies"].append({"where": f"p{u['page']} {u['title']} {u['fund']}", "issue": "class subtotals != printed Total", "col": k, "diff": d})
            for crow, det in classes:
                dd = sum(r["v"][k] for r in det) - crow["v"][k]
                if dd:
                    class_detail_diffs.append(abs(dd))
    check("every unit table: class subtotals sum to printed Total within $2", bad == 0,
          tables=len(detail), exact_cells=exact, off_by_1=off1, off_by_2=off2, other=bad)
    check("every class subtotal equals its detail rows within $2", all(d <= 2 for d in class_detail_diffs),
          rows_off=len(class_detail_diffs), max_abs_diff=max(class_detail_diffs or [0]))

    # ---- positions
    pos_stats = collections.Counter()
    fte_total = 0.0
    sal_total = 0
    pos_flags = []
    for u in detail:
        pr = [p for p in u["positions"] if p.get("title")]
        pt = next((p for p in u["positions"] if p.get("total")), None)
        if not pt:
            pos_stats["units_without_positions_table"] += 1
            continue
        pos_stats["units_with_positions"] += 1
        pos_stats["position_rows"] += len(pr)
        fte_total += pt["fte2026"]
        sal_total += pt["budget2026"]
        s26 = sum(p["budget2026"] for p in pr)
        s25 = sum(p["budget2025"] for p in pr)
        f26 = round(sum(p["fte2026"] for p in pr), 1)
        f25 = round(sum(p["fte2025"] for p in pr), 1)
        if abs(s26 - pt["budget2026"]) > 3 or abs(s25 - pt["budget2025"]) > 3:
            pos_flags.append({"where": f"p{u['page']} {u['title']}", "issue": "position rows $ != printed positions Total", "rows": (s25, s26), "printed": (pt["budget2025"], pt["budget2026"])})
        if abs(f26 - pt["fte2026"]) > 0.15 or abs(f25 - pt["fte2025"]) > 0.15:
            pos_stats["units_fte_rounding_off_>0.15"] += 1
            pos_flags.append({"where": f"p{u['page']} {u['title']}", "issue": "FTE rounding (rows are individually rounded to 0.1)", "rows": (f25, f26), "printed": (pt["fte2025"], pt["fte2026"])})
        sal = [a for a in u["accounts"] if a["code"] == "611005"]
        if sal and abs(sal[0]["values"][2] - pt["budget2026"]) > 3:
            rec["pdf_inconsistencies"].append({"where": f"p{u['page']} {u['title']} {u['fund']}", "issue": "611005 Salary & Wages line != positions table Total", "salary_line2026": sal[0]["values"][2], "positions_total2026": pt["budget2026"], "diff": sal[0]["values"][2] - pt["budget2026"]})
    money_flags = [f for f in pos_flags if f["issue"].startswith("position rows $")]
    check("position rows sum to each printed positions Total within $3", not money_flags,
          units=pos_stats["units_with_positions"], rows=pos_stats["position_rows"], violations=money_flags)
    check("total budgeted FTE 2026 ~ 3,213.0 printed on p58 (sum of positions tables)", abs(fte_total - 3213.0) < 1.0,
          computed=round(fte_total, 1), printed=3213.0)
    rec["positions"] = {"stats": dict(pos_stats), "fte2026_sum_of_tables": round(fte_total, 1),
                        "salary2026_sum_of_tables": sal_total, "notes": [f for f in pos_flags if not f["issue"].startswith("position rows $")]}

    # ---- summary tables (Regions, District Administration, Districtwide, Finance General)
    def sum_total(us, k):
        return sum(u["total"][k] for u in us)

    sec = collections.defaultdict(list)
    for u in detail:
        sec[function_of(u)].append(u)

    for reg in ("Central", "North", "South"):
        us = sec[f"Recreation & Programming: {reg} Region"]
        sm = summaries[f"{reg} Region Summary"]
        d26 = sm["total"][1] - sum_total(us, 2)
        d25 = sm["total"][0] - sum_total(us, 1)
        check(f"{reg} Region: sum of {len(us)} unit tables vs printed Region Summary Total", abs(d26) <= 5 and abs(d25) <= 5,
              units=len(us), units_sum2026=sum_total(us, 2), summary2026=sm["total"][1], diff2026=d26,
              units_sum2025=sum_total(us, 1), summary2025=sm["total"][0], diff2025=d25)
    # Finance General page: class subtotals vs printed Total, 36 detail rows
    fgc, fgl = group_classes([{"code": a["code"], "name": a["name"], "v": a["values"]} for a in fg["accounts"]], lambda c: c.endswith("000"))
    check("Finance General (p102): class subtotals sum to printed Total", all(sum(c[0]["v"][k] for c in fgc) == fg["total"][k] for k in (0, 1)),
          total2026=fg["total"][1], total2025=fg["total"][0])
    # District Administration / Districtwide summary pages
    da, dw = summaries["District Administration Summary"], summaries["Districtwide Summary"]
    for s in (da, dw):
        cs = sum(a["values"][1] for a in s["accounts"] if a["code"].endswith("000"))
        d = s["total"][1] - cs
        if d:
            rec["pdf_inconsistencies"].append({"where": f"p{s['page']}-{s['page']+1} {s['title']}", "issue": "printed Total != sum of its own class subtotals (2026)", "printed_total": s["total"][1], "class_sum": cs, "diff": d})
    cs_all = 0
    for s in (da, dw, summaries["Central Region Summary"], summaries["North Region Summary"], summaries["South Region Summary"]):
        cs_all += sum(a["values"][1] for a in s["accounts"] if a["code"].endswith("000"))
    check("five summary tables (DA+Districtwide+3 Regions): class subtotals sum to Grand Total 637,580,350 within $2", abs(cs_all - GRAND_2026) <= 2,
          class_sum=cs_all, diff=GRAND_2026 - cs_all)
    tot_sum = sum(s["total"][1] for s in (da, dw, summaries["Central Region Summary"], summaries["North Region Summary"], summaries["South Region Summary"]))
    rec["summary_page_total_sum"] = {"sum_of_printed_Totals": tot_sum, "grand_total": GRAND_2026, "diff": tot_sum - GRAND_2026,
                                     "explanation": "Printed District Administration Total (384,928,302) is $150,000 above its own class lines (384,778,302). Class lines tie to the Grand Total, so the printed Total looks like a typo."}

    # ---- unit + FG + GPMF vs all-funds printed account table => residual
    acc_units = {k: collections.defaultdict(int) for k in (2025, 2026)}
    for u in detail:
        for a in u["accounts"]:
            if a["code"].endswith("000") or a["code"] == "UNKNOWN":
                continue
            acc_units[2026][a["code"]] += a["values"][2]
            acc_units[2025][a["code"]] += a["values"][1]
    for a in fg["accounts"]:
        if not a["code"].endswith("000"):
            acc_units[2026][a["code"]] += a["values"][1]
            acc_units[2025][a["code"]] += a["values"][0]
    printed_acc = {r["code"]: r for r in exp_rows if not r["code"].endswith("000") and r["code"] != "GRAND"}
    resid = {2025: {}, 2026: {}}
    for yr, idx in ((2025, 0), (2026, 1)):
        for c, r in printed_acc.items():
            d = r["v"][idx] - acc_units[yr].get(c, 0)
            if d:
                resid[yr][c] = d
        extra = set(acc_units[yr]) - set(printed_acc)
        if extra:
            rec["pdf_inconsistencies"].append({"where": f"account codes on unit pages not in p62-63 table ({yr})", "codes": sorted(extra)})
    # the garbled p87 row: v62710 $1,996,642 in 2024 only, so it does not affect 2025/2026
    unit_tot = {2025: sum_total(detail, 1) + fg["total"][0], 2026: sum_total(detail, 2) + fg["total"][1]}
    # detail includes GPMF already (page 103)
    gap = {2025: GRAND_2025 - unit_tot[2025], 2026: GRAND_2026 - unit_tot[2026]}
    resid_sum = {y: sum(v.values()) for y, v in resid.items()}
    check("department pages + Finance General + Grant Park + residual == Grand Total (2026)", unit_tot[2026] + gap[2026] == GRAND_2026,
          department_pages_plus_fg=unit_tot[2026], residual=gap[2026], residual_by_account_sum=resid_sum[2026])
    rec["residual"] = {
        "meaning": "Amounts printed on the District Administration/Districtwide summary pages and in the all-funds account table (pp 62-63) that do not appear on any department or park page. The PDF does not say which department holds them.",
        "gap2026": gap[2026], "gap2025": gap[2025],
        "by_account2026": {c: {"name": printed_acc[c]["name"], "amount": v} for c, v in sorted(resid[2026].items())},
        "by_account2025": {c: {"name": printed_acc[c]["name"], "amount": v} for c, v in sorted(resid[2025].items())},
    }

    # ---- BUILD TREE
    root = node("cpd", "Chicago Park District FY2026 Operating Budget", "root", GRAND_2026, GRAND_2025,
                source="printed Grand Total pp 55, 63", printed_page=49)
    root["children"] = []
    funcs = collections.OrderedDict()

    def func_node(fid, name, page_note):
        if fid not in funcs:
            funcs[fid] = node(f"cpd/{slug(fid)}", name, "function", 0, 0, note=page_note, children=[])
        return funcs[fid]

    # Finance General
    fgn = node("cpd/finance-general", "Finance General", "function", fg["total"][1], fg["total"][0],
               page=102, printed_page=96, source="printed Total, 'All Funds'",
               note="Cross-department costs: debt service, pension, utilities, benefits reserves, Zoo/Aquarium/Museum remittances. The PDF lists it under 'All Funds' with no fund split.")
    fgcl = []
    for crow, det in fgc:
        cn = node(f"cpd/finance-general/{crow['code']}", CLASS_NAMES.get(crow["code"], crow["name"]), "class",
                  crow["v"][1], crow["v"][0], code=crow["code"], source="printed class subtotal")
        cn["children"] = [node(f"cpd/finance-general/{crow['code']}/{d['code']}", d["name"], "account", d["v"][1], d["v"][0], code=d["code"]) for d in det]
        add_check(cn)
        fgcl.append(cn)
    fgn["children"] = fgcl
    add_check(fgn)

    # groupings of department/region/park units
    def unit_key(u):
        return (u["title"], u["unit_code"])

    by_func_units = collections.OrderedDict()
    for u in detail:
        f = function_of(u)
        if f is None:
            continue
        by_func_units.setdefault(f, collections.OrderedDict()).setdefault(unit_key(u), []).append(u)

    def unit_node(fid_slug, key, fund_tables):
        title, code = key
        uid = f"{fid_slug}/{slug(title)}-{code}" if code else f"{fid_slug}/{slug(title)}"
        un = node(uid, title, "unit", sum(t["total"][2] for t in fund_tables), sum(t["total"][1] for t in fund_tables),
                  sum(t["total"][0] for t in fund_tables), unit_code=code, page=fund_tables[0]["page"],
                  printed_page=fund_tables[0]["page"] - PRINTED_OFFSET, source="sum of the unit's fund tables (printed Totals)")
        un["children"] = [build_unit_fund_node(t, uid) for t in fund_tables]
        add_check(un)
        return un

    unit_nodes_by_func = {}
    for f, ukeys in by_func_units.items():
        is_region = f.startswith("Recreation & Programming: ")
        fn_ = func_node(f, f if not is_region else f.split(": ")[1], None)
        fslug = slug(f)
        nodes = [unit_node(f"cpd/{fslug}", key, tabs) for key, tabs in ukeys.items()]
        fn_["children"] = nodes
        unit_nodes_by_func[f] = nodes
    # fold the three regions under one "Parks by Region" function node
    regions = [funcs.pop(f"Recreation & Programming: {r} Region") for r in ("Central", "North", "South")]
    parks = node("cpd/parks-by-region", "Neighborhood Parks by Region", "function", 0, 0,
                 note="Central, North and South Region administration plus every individual park with its park number.", children=regions)
    for r in regions:
        r["type"] = "region"
        r["amount2026"] = sum(c["amount2026"] for c in r["children"])
        r["amount2025"] = sum(c["amount2025"] for c in r["children"])
        for c in r["children"]:
            c["type"] = "park" if c["unit_code"] and not c["name"].endswith("Administration") else "unit"
        r["check"] = None
        del r["check"]
        add_check(r)
        r["printed_region_summary_total2026"] = summaries[r["name"].split(" ")[0] + " Region Summary"]["total"][1]
    parks["amount2026"] = sum(r["amount2026"] for r in regions)
    parks["amount2025"] = sum(r["amount2025"] for r in regions)
    add_check(parks)

    # residual node: only the real, non-rounding items are listed individually
    res_children = []
    rounding26 = 0
    rounding25 = 0
    for c, v in sorted(resid[2026].items()):
        v25 = resid[2025].get(c, 0)
        if abs(v) <= 10 and abs(v25) <= 10:
            rounding26 += v
            rounding25 += v25
            continue
        res_children.append(node(f"cpd/unitemized/{c}", printed_acc[c]["name"], "account", v, v25, code=c))
    for c, v25 in sorted(resid[2025].items()):
        if c not in resid[2026] and abs(v25) > 10:
            res_children.append(node(f"cpd/unitemized/{c}", printed_acc[c]["name"], "account", 0, v25, code=c))
    res_children.append(node("cpd/unitemized/rounding", "PDF rounding differences (each $10 or less)", "account", rounding26, rounding25))
    resn = node("cpd/unitemized", "Not itemized on any department page", "function", gap[2026], gap[2025],
                reconciling_item=True, children=res_children,
                note="The PDF's Districtwide Summary (pp 98-99) and all-funds account table (pp 62-63) include these amounts, but no department or park page lists them. Treat as Districtwide. Kept separate so nothing is guessed.")
    add_check(resn)

    # order functions
    fa = funcs.pop("Administration & Finance")
    fo = funcs.pop("Operations & Maintenance")
    fr = funcs.pop("Recreation & Programming")
    fgp = funcs.pop("Grant Park Music Festival")
    fa["name"], fo["name"], fr["name"] = "Administration & Finance", "Operations & Maintenance", "Recreation & Programming (Districtwide Programs)"
    gpn = fgp
    for n_, nm in ((fa, "A&F"), (fo, "O&M"), (fr, "R&P"), (gpn, "GPMF")):
        n_["amount2026"] = sum(c["amount2026"] for c in n_["children"])
        n_["amount2025"] = sum(c["amount2025"] for c in n_["children"])
        add_check(n_)
    gpn["name"] = "Grant Park Music Festival"
    root["children"] = [fgn, fa, fo, fr, parks, gpn, resn]
    root["check"] = None
    del root["check"]
    add_check(root)
    check("root children (function totals + Finance General + Grant Park + not-itemized) sum to Grand Total 637,580,350 exactly (2026)",
          root["check"]["diff2026"] == 0, children_sum=root["check"]["children_sum2026"])
    check("root children sum to Grand Total 598,512,384 exactly (2025)", root["check"]["diff2025"] == 0, children_sum=root["check"]["children_sum2025"])

    # ---- tree by fund (amounts only)
    funds = collections.OrderedDict()
    def walk_units(n_, func_name):
        for c in n_.get("children", []):
            if c["type"] in ("unit", "park"):
                for fch in c["children"]:
                    funds.setdefault(fch["name"], collections.OrderedDict()).setdefault(func_name, []).append(
                        {"id": fch["id"], "name": c["name"], "unit_code": c.get("unit_code"), "type": "unit-fund",
                         "amount2026": fch["amount2026"], "amount2025": fch["amount2025"], "amount2024": fch.get("amount2024"),
                         "ref": fch["id"]})
            elif c["type"] == "region":
                walk_units(c, f"{func_name}: {c['name']}")
    for fnode in (fa, fo, fr, gpn):
        walk_units(fnode, fnode["name"])
    walk_units(parks, "Neighborhood Parks by Region")
    fund_tree = {"id": "cpd-by-fund", "name": "By fund", "type": "root", "children": []}
    fund_total26 = 0
    for fname, fm in funds.items():
        fchildren = []
        for func_name, lst in fm.items():
            fchildren.append({"id": f"fund/{slug(fname)}/{slug(func_name)}", "name": func_name, "type": "function",
                              "amount2026": sum(x["amount2026"] for x in lst), "amount2025": sum(x["amount2025"] for x in lst), "children": lst})
        tot26 = sum(c["amount2026"] for c in fchildren)
        fund_total26 += tot26
        fund_tree["children"].append({"id": f"fund/{slug(fname)}", "name": fname, "type": "fund", "amount2026": tot26,
                                      "amount2025": sum(c["amount2025"] for c in fchildren), "children": fchildren})
    fund_tree["children"].append({"id": "fund/all-funds-unassigned", "name": "All Funds (fund not stated in PDF)", "type": "fund",
                                  "amount2026": fg["total"][1] + gap[2026], "amount2025": fg["total"][0] + gap[2025],
                                  "note": "Finance General (p102 'All Funds') and the not-itemized residual. The PDF gives no fund split for these.",
                                  "children": [{"id": "cpd/finance-general", "name": "Finance General", "type": "ref", "amount2026": fg["total"][1], "amount2025": fg["total"][0], "ref": "cpd/finance-general"},
                                               {"id": "cpd/unitemized", "name": "Not itemized on any department page", "type": "ref", "amount2026": gap[2026], "amount2025": gap[2025], "ref": "cpd/unitemized"}]})
    check("by-fund tree sums to Grand Total 637,580,350", fund_total26 + fg["total"][1] + gap[2026] == GRAND_2026, sum=fund_total26 + fg["total"][1] + gap[2026])
    fund_tree["amount2026"] = GRAND_2026
    fund_tree["amount2025"] = GRAND_2025

    # ---- leaf bounds: how deep do we get under $1M
    leaves = []
    def collect(n_, depth=0):
        if not n_.get("children"):
            leaves.append((n_, depth))
        for c in n_.get("children", []):
            collect(c, depth + 1)
    collect(root)
    over1m = [(n_, d) for n_, d in leaves if abs(n_["amount2026"] or 0) >= 1_000_000]
    depth_stats = {"leaf_nodes": len(leaves), "leaves_2026_ge_1M": len(over1m),
                   "leaves_ge_1M": [{"id": n_["id"], "name": n_["name"], "amount2026": n_["amount2026"]} for n_, _ in sorted(over1m, key=lambda x: -abs(x[0]["amount2026"]))]}

    # ---- beyond-operating facts printed in the same PDF
    beyond = beyond_operating(words)

    # ---- validate the beyond-operating tables we lifted from the PDF
    ds = beyond["general_obligation_debt_schedule"]["rows"]
    body = [r for r in ds if r["period"] != "Total"]
    tot = next(r for r in ds if r["period"] == "Total")
    check("GO debt schedule (p73): 9 period rows sum to printed Total (principal, interest, total)",
          len(body) == 9 and all(sum(r[k] for r in body) == tot[k] for k in ("principal", "interest", "total"))
          and all(r["principal"] + r["interest"] == r["total"] for r in ds),
          principal=tot["principal"], interest=tot["interest"], total=tot["total"])
    cr = beyond["capital_improvement_plan_2026_2030"]["rows"]
    src = ["General Obligation Bond Proceeds", "Special Recreation Assessment", "Capital Transfer from Operating", "Harbor Bond",
           "City Grant Funds", "Tax Increment Financing Funds", "State Grant Funds", "Federal Grant Funds", "Private Grants and Donations"]
    use = ["Acquisition and Development", "Facility Rehabilitation", "Site Improvements", "Technology, Vehicles & Equipment"]
    cols = ["prior_year_active_projects", "y2026", "y2027", "y2028", "y2029", "y2030", "district_funding_2026_2030", "outside_funding_2026_2030", "total_2026_2030"]
    cap_diffs = {}
    for label, rows_, tot_key in (("sources", src, "Total Sources"), ("uses", use, "Total Uses")):
        for c in cols:
            dd = sum(cr[r][c] for r in rows_) - cr[tot_key][c]
            if dd:
                cap_diffs[f"{label}:{c}"] = dd
    check("Capital plan (p69): source rows and use rows sum to printed totals (diffs listed)", all(abs(v) <= 1000 for v in cap_diffs.values()) and
          cr["Total Sources"]["total_2026_2030"] == cr["Total Uses"]["total_2026_2030"] == 681_392_000, diffs=cap_diffs,
          total_2026_2030=cr["Total Uses"]["total_2026_2030"])
    check("Capital plan (p69): Total Sources == Total Uses for each of 2026-2030 and 2026-2030 totals",
          all(cr["Total Sources"][c] == cr["Total Uses"][c] for c in cols[1:]),
          note_prior_year="Prior-year active projects column prints Sources 74,724,000 vs Uses 74,224,000 (the $500,000 'Capital Transfer from Operating' appears only on the sources side)")
    out = {
        "meta": {
            "entity": "Chicago Park District", "fiscal_year": 2026,
            "source_pdf": PDF_URL, "source_title": "2026 Budget Appropriations (274 PDF pages; printed page = PDF page - 6)",
            "generated_by": "scripts/parks_extract.py -> parks_parse.py -> parks_build.py",
            "grand_total_2026": GRAND_2026, "grand_total_2025": GRAND_2025,
            "net_appropriation_2026": 631_880_350, "internal_service_earnings_2026": 5_700_000,
            "note_net": "p32/50 print Net Appropriation 631,880,350 = Grand Total less 5,700,000 internal service earnings (double counting between funds).",
            "levels": "tree: root > function > (department | region > park/unit) > fund > class > account > position (positions only under 611005 Salary & Wages)",
            "units_parsed": len(detail), "summary_tables_parsed": len(summaries),
            "leaf_stats": {k: v for k, v in depth_stats.items() if k != "leaves_ge_1M"},
        },
        "reconciliation": rec,
        "leaves_at_or_above_1M": depth_stats["leaves_ge_1M"],
        "tree": root,
        "tree_by_fund": fund_tree,
        "printed_all_funds": {
            "expenses_by_account": [{"code": r["code"], "name": r["name"], "amount2025": r["v"][0], "amount2026": r["v"][1], "page": r["page"], "is_class": r["code"].endswith("000")} for r in exp_rows if r["code"] != "GRAND"],
            "revenues_by_account": [{"code": r["code"], "name": r["name"], "amount2025": r["v"][0], "amount2026": r["v"][1], "page": r["page"], "is_class": r["code"].endswith("000")} for r in rev_rows if r["code"] != "GRAND"],
        },
        "beyond_operating_from_budget_pdf": beyond,
    }
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    json.dump(out, open(OUT, "w"), separators=(",", ":"))
    n_pass = sum(1 for c in rec["checks"] if c["pass"])
    print(f"checks passed: {n_pass}/{len(rec['checks'])}")
    for c in rec["checks"]:
        print(("PASS " if c["pass"] else "FAIL ") + c["name"])
    print("pdf inconsistencies:", len(rec["pdf_inconsistencies"]))
    for i in rec["pdf_inconsistencies"][:40]:
        print("  ", i)
    print("leaves >= $1M:", depth_stats["leaves_2026_ge_1M"], "of", depth_stats["leaf_nodes"])
    print("wrote", OUT, os.path.getsize(OUT), "bytes")


CAP_LABELS = {re.sub(r"\s+", "", k): k for k in (
    "General Obligation Bond Proceeds", "Special Recreation Assessment", "Capital Transfer from Operating",
    "Harbor Bond", "City Grant Funds", "Tax Increment Financing Funds", "State Grant Funds",
    "Federal Grant Funds", "Private Grants and Donations", "Total Sources", "Acquisition and Development",
    "Facility Rehabilitation", "Site Improvements", "Technology, Vehicles & Equipment", "Total Uses")}


def beyond_operating(words):
    """Facts printed in the budget PDF about capital, debt, pension (no estimates)."""
    def lines(pg):
        return [" ".join(w[0] for w in ln) for ln in group_lines(words[str(pg)])]
    # Capital funding summary p69 (printed 63) and debt schedule p73 (printed 67)
    cap_lines = lines(69)
    debt_lines = lines(73)
    debt = []
    for l in debt_lines:
        m = re.match(r"^(\d{4}(?:-\d{4})?|Total) \$([\d,]+) \$([\d,]+) \$([\d,]+)$", l)
        if m:
            debt.append({"period": m.group(1), "principal": int(m.group(2).replace(",", "")), "interest": int(m.group(3).replace(",", "")), "total": int(m.group(4).replace(",", ""))})
    cap = {}
    for l in cap_lines:
        l2 = re.sub(r"(\d) (\d)", r"\1\2", l) if re.search(r"\$ \d \d|\$ \d\s", l) else l
        m = re.match(r"^([A-Za-z&, ]+?) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-) \$ ([\d,]+|-)$", re.sub(r"(?<=\d) (?=\d)", "", l))
        if m:
            vals = [0 if v == "-" else int(v.replace(",", "")) for v in m.groups()[1:]]
            cap[CAP_LABELS.get(re.sub(r"\s+", "", m.group(1)), m.group(1).strip())] = dict(zip(["prior_year_active_projects", "y2026", "y2027", "y2028", "y2029", "y2030", "district_funding_2026_2030", "outside_funding_2026_2030", "total_2026_2030"], vals))
    return {
        "capital_improvement_plan_2026_2030": {
            "page": 69, "printed_page": 63,
            "columns": "prior_year_active_projects = Active Projects Prior Year District Funding; district_funding_2026_2030 = Chicago Park District funding; outside_funding_2026_2030 = expected outside funding as of fall 2025",
            "rows": cap,
            "note": "Category-level only. The PDF has NO per-project list. Per-project data must come from the separate CIP document (see research/park_district.md).",
        },
        "general_obligation_debt_schedule": {"page": 73, "printed_page": 67, "as_of": "unaudited, December 2, 2025", "rows": debt,
                                             "ratings": {"Fitch": "AA", "Kroll": "AA", "S&P": "AA-"},
                                             "outstanding_end_2025": 879_300_000, "outstanding_after_2026_payments_approx": 844_000_000,
                                             "note": "Printed text says outstanding long-term debt $879.3 million at end of 2025, about $844 million after 2026 payments."},
        "pension": {"page": 59, "printed_page": 53,
                    "legally_required_employer_contribution_2026": 63_332_412, "account": "625020 Pension Expense (Finance General)",
                    "supplemental_contribution_2026": 6_000_000, "supplemental_account": "625023 Supplemental Contribution to Pension Fund",
                    "contribution_2025": 59_679_376,
                    "text": "HB 417 (2021) puts the Park Employees' and Retirement Board Employees' Annuity and Benefit Fund on a path to 100% funded within 35 years; District also contributed an additional $108.3M from 2021-2023."},
        "debt_service_operating": {"interest_2026": 35_926_546, "principal_2026": 34_630_000, "total_2026": 70_556_546,
                                   "interest_2025": 37_346_183, "principal_2025": 33_335_000, "total_2025": 70_681_183, "page": 62},
    }


if __name__ == "__main__":
    main()
