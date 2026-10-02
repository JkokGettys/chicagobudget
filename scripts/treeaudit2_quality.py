"""Audit 2, part 3: data-quality checks on the built tree snapshot (read-only).
Checks: negative boxes, paid_to_date boxes vs their line, proxies, duplicated dollars across split files,
stale why sentences, reconciliation gaps over $1M. (Individuals' names are in treeaudit2_names.py.)
Writes raw/treeaudit2/quality.json and prints the numbers used in research/tree_gap_audit_2.md."""
import json, re, collections
from treeaudit2_common import *

def jl(x):
    try: return json.loads(x) if x else {}
    except Exception: return {}

def load():
    rows = load_nodes(); by = {r["id"]: r for r in rows}; kids = children_map(rows)
    for r in rows: r["_e"] = jl(r["extra"]); r["_s"] = jl(r["source"])
    return rows, by, kids

# ---------------------------------------------------------------- 1. negative boxes
def negatives(rows, by, kids):
    neg = [r for r in rows if r["amount_cents"] < 0 and r["is_leaf"]]
    def kind_of(r):
        n = r["name"].lower()
        if "turnover" in n or "vacancy" in n: return "vacancy savings (planned)"
        if "paid beyond" in n or "already spent more" in n: return "paid so far beyond the line"
        if "obm" in r["id"] or "no line explains" in n: return "OBM unexplained adjustment"
        if "bond papers list more" in n: return "bond papers exceed line"
        if "budget only" in (r["note"] or "").lower() or "set-aside" in n or "planned cut" in (r["why_cant_go_deeper"] or "").lower(): return "CPS budget-only offset"
        if "savings" in n: return "other planned saving"
        return "other"
    out = collections.defaultdict(lambda: {"n": 0, "cents": 0, "n_ge1m": 0, "no_expl_ge1m": 0, "no_why_ge10m": 0})
    detail = []
    for r in neg:
        k = (r["gov"], kind_of(r)); o = out[k]
        o["n"] += 1; o["cents"] += r["amount_cents"]
        a = abs(r["amount_cents"])
        has_note = bool((r["note"] or "").strip()); has_why = bool((r["why_cant_go_deeper"] or "").strip())
        if a >= M:
            o["n_ge1m"] += 1
            if not (has_note or has_why): o["no_expl_ge1m"] += 1
            detail.append({"gov": r["gov"], "id": r["id"], "name": r["name"], "cents": r["amount_cents"], "kind": k[1], "note": has_note, "why": has_why,
                           "parent": by[r["parent_id"]]["name"] if r["parent_id"] else ""})
        if a >= 10 * M and not has_why: o["no_why_ge10m"] += 1
    # negative boxes that are not leaves (aggregates, e.g. CPS 'Salaries' group) for completeness
    agg = [r for r in rows if r["amount_cents"] < 0 and not r["is_leaf"] and abs(r["amount_cents"]) >= M]
    return out, detail, agg

# ---------------------------------------------------------------- 2. paid_to_date vs line
def paid_vs_line(rows, by, kids):
    groups = collections.defaultdict(list)
    for r in rows:
        if r["basis"] == "paid_to_date" and r["parent_id"] and by[r["parent_id"]]["basis"] != "paid_to_date":
            groups[r["parent_id"]].append(r)
    res = []
    for pid, L in groups.items():
        P = by[pid]
        paid = sum(c["amount_cents"] for c in L if c["amount_cents"] > 0)
        over = [c for c in kids[pid] if c["name"].startswith(("Already spent", "Paid beyond"))]
        if not over:
            continue
        # children add to the parent, so the parent amount is the line. The negative box is the part of paid that exceeds it.
        neg = sum(c["amount_cents"] for c in over)
        line = P["amount_cents"]
        res.append({"gov": P["gov"], "id": pid, "name": P["name"], "path": path_names(by, pid), "line_cents": line,
                    "paid_cents": paid, "over_cents": -neg, "ratio": paid / line if line else None, "note": bool(over[0]["note"])})
    res.sort(key=lambda x: -x["over_cents"])
    # sums per line where there is no negative box: paid share of the line
    ok = []
    for pid, L in groups.items():
        P = by[pid]
        if any(c["name"].startswith(("Already spent", "Paid beyond")) for c in kids[pid]): continue
        paid = sum(c["amount_cents"] for c in L if c["amount_cents"] > 0)
        ok.append((P["amount_cents"], paid))
    return res, ok

# ---------------------------------------------------------------- 3. proxies
def proxies(rows, by):
    px = [r for r in rows if r["basis"] == "proxy" and r["is_leaf"]]
    out = collections.defaultdict(lambda: {"n": 0, "cents": 0, "no_note": 0, "no_note_cents": 0, "ge10m": 0, "ge10m_cents": 0})
    for r in px:
        o = out[r["gov"]]; a = abs(r["amount_cents"]); o["n"] += 1; o["cents"] += a
        if not (r["note"] or "").strip():
            o["no_note"] += 1; o["no_note_cents"] += a
        if bucket(r) == "ge10m": o["ge10m"] += 1; o["ge10m_cents"] += a
    # proxy leaves of $1M or more with no note, by source doc
    srcs = collections.defaultdict(lambda: [0, 0])
    for r in px:
        if abs(r["amount_cents"]) >= M and not (r["note"] or "").strip():
            k = (r["gov"], (r["_s"].get("doc") or r["_s"].get("dataset") or "?")[:60])
            srcs[k][0] += 1; srcs[k][1] += abs(r["amount_cents"])
    # side info that is an estimate kept as side (not a box): count by kind
    return out, srcs

# ---------------------------------------------------------------- 4. duplicated dollars
def dupes(rows, by, kids):
    res = {}
    # (a) same ledger project code + fund code on more than one box
    k2 = collections.defaultdict(list)
    for r in rows:
        e = r["_e"]
        if e.get("grant_project_code"):
            for f in e.get("fund_codes") or []: k2[(e["grant_project_code"], f)].append(r)
    res["ledger_code_fund"] = [(k, [(x["amount_cents"], x["_e"].get("ledger_budget"), x["_e"].get("expended_to_date")) for x in v], [path_names(by, x["parent_id"])[-90:] for x in v])
                               for k, v in k2.items() if len(v) > 1]
    # (b) same award id or contract number on more than one box (paid boxes, awards)
    aw = collections.defaultdict(list)
    for r in rows:
        e = r["_e"]
        for key in ("award_id", "contract"):
            if e.get(key) and r["gov"] == "city" and r["amount_cents"] > 0 and r["kind"] in ("grant_award", "contract"):
                aw[(key, str(e[key]))].append(r)
    res["award_contract"] = [(k, len(v)) for k, v in aw.items() if len(v) > 1]
    # (c) same project name on several lines (split-file pieces, kind piece/project) with different parents
    nm = collections.defaultdict(list)
    for r in rows:
        if r["is_leaf"] and r["kind"] in ("piece", "project", "grant_award") and r["gov"] in ("city", "cps") and abs(r["amount_cents"]) >= M and r["basis"] in ("gov_estimate", "budget", "tied"):
            nm[(r["gov"], re.sub(r"[^a-z0-9]", "", r["name"].lower())[:50])].append(r)
    res["same_name_across_parents"] = [(k, [(x["amount_cents"], x["basis"]) for x in v]) for k, v in nm.items() if len({x["parent_id"] for x in v}) > 1]
    # (d) CPS same project number
    pn = collections.defaultdict(list)
    for r in rows:
        if r["gov"] == "cps" and r["kind"] == "project" and r["_e"].get("project_number") not in (None, "TBD"):
            pn[r["_e"]["project_number"]].append(r)
    res["cps_project_number"] = [(k, [(x["amount_cents"], x["parent_id"][-40:]) for x in v]) for k, v in pn.items() if len(v) > 1]
    # (e) reserve-line ledger projects vs 2026 spending-line TIP projects (same real-world project on two appropriations)
    tip = [r for r in rows if r["gov"] == "city" and "eTIP" in (r["_s"].get("doc") or "") and r["kind"] in ("piece", "project") and re.match(r"\d\d-\d\d-\d{4}", r["name"])]
    led = [r for r in rows if r["gov"] == "city" and "Mid-Year Grants" in (r["_s"].get("doc") or "") and r["kind"] in ("piece", "project")]
    words = {"calumet river bridges": "Calumet River Bridges", "bridge inspection": "Bridge Inspection", "cermak": "Cermak at Kenton", "navy pier": "Navy Pier Flyover",
             "streets for cycling": "Streets for Cycling", "wireless signal": "Wireless Signal Interconnect", "arterial resurfacing": "Arterial Resurfacing",
             "ogden": "Ogden Ave", "lasalle": "LaSalle St", "englewood": "Englewood Trail"}
    ov = []
    for key, label in words.items():
        t = [x for x in tip if key in x["name"].lower()]; l = [x for x in led if key in x["name"].lower()]
        if t and l: ov.append((label, sum(x["amount_cents"] for x in t), sum(x["amount_cents"] for x in l)))
    res["tip_vs_ledger_overlap"] = ov
    # (f) State/Lake: STP in two ledger extracts
    sl = [r for r in rows if "Surface Transportation Program money" in r["name"] and r["gov"] == "city"]
    res["state_lake_stp"] = [(r["name"][:70], r["amount_cents"]) for r in sl]
    return res

# ---------------------------------------------------------------- 5. stale why
GENERIC = ["The public budget lists this as one amount, and we could not find public records that split it further.",
           "The budget gives one amount for this kind of contract, and the public payment records do not split it into smaller pieces tied to this line.",
           "The budget sets aside one amount for building work, and the project-by-project list is not published with it.",
           "This is one budget amount for a kind of worker pay, and the City does not publish it split into smaller pieces.",
           "The budget gives this program one amount and does not list what each piece of it buys.",
           "Overtime is paid hour by hour as it happens, so the budget only sets one total for the year."]

def old_audit_flags(rows, by):
    """Re-apply the previous audit's sentence rules (scripts/treeaudit_top.py flag()) to the new tree, leaves of $10M or more."""
    import treeaudit_top
    res = []
    for r in rows:
        if r["is_leaf"] and r["gov"] in GOVS and abs(r["amount_cents"]) >= 10 * M and not (r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M):
            f = treeaudit_top.flag(r, path_names(by, r["id"]))
            if f and f != "NO SENTENCE": res.append((r, f))
    return res

def why_flags(rows, by, kids):
    flagged = []
    fewco = re.compile(r"a few (big|large) companies", re.I)
    for r in rows:
        w = (r["why_cant_go_deeper"] or "").strip()
        if not w: continue
        nm = (r["name"] + " " + path_names(by, r["id"])).lower()
        f = []
        if kids[r["id"]]: f.append("why sentence on a box that now has children")
        if w in GENERIC: f.append("generic fallback")
        if r["is_leaf"] and abs(r["amount_cents"]) >= 10 * M:
            if fewco.search(w) and re.search(r"delegate|homeless|youth|head start|loan|grant|preschool|reserve|pension|bond|interest|salar|overtime|labor|charter|tuition|food|lunch|breakfast", nm) and not re.search(r"electric|gas|water|supplies|food|lunch|breakfast|utilit", nm):
                f.append("'few companies' sentence on a non-vendor box")
            if "ambulance trips" in w: f.append("states a use that research/parks_misc_detail.md says is unconfirmed (EMT 9222)")
            if re.search(r"provider|preschool", nm) and fewco.search(w): f.append("preschool money goes to the City DFSS then ~88 agencies, not 'a few companies'")
            if re.search(r"construction", w, re.I) and re.search(r"cdc|home investment|public health|epidemiology|housing", nm): f.append("construction sentence on non-construction grant")
            if re.search(r"payments so far this year do not match it to one company", w) and re.search(r"permeable|wing storage|stormwater", nm) and False: pass
        if f: flagged.append((r, "; ".join(f)))
    return flagged

# ---------------------------------------------------------------- 6. reconciliation
def reconcile(rows, by, kids):
    res = {}
    c = con()
    res["checks"] = [dict(x) for x in c.execute("select gov,n_nodes,total_cents,expected_cents,problems from checks")]
    # parent = sum of children everywhere
    bad = []
    for r in rows:
        k = kids[r["id"]]
        if k and sum(x["amount_cents"] for x in k) != r["amount_cents"]: bad.append(r["id"])
    res["bad_sums"] = len(bad)
    # printed totals carried in extra
    pt = []
    for r in rows:
        p = r["_e"].get("printed_total_cents")
        if p is not None and abs(p - r["amount_cents"]) >= M: pt.append((r["id"], p, r["amount_cents"]))
    res["printed_total_gaps_ge1m"] = pt
    res["printed_total_nodes"] = sum(1 for r in rows if r["_e"].get("printed_total_cents") is not None)
    tw = [r for r in rows if r["id"] == "city-twice"]
    city = by["city"]["amount_cents"]; twice = tw[0]["amount_cents"] if tw else 0
    obm = by.get("city.obm-unexplained", {}).get("amount_cents", 0)
    res["gross_check"] = {"city": city, "twice": twice, "obm": obm, "gross": city + twice - obm, "ordinance_gross": 1866856846000}
    # residual / difference boxes over $1M by government (what the tree could not itemise)
    rd = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["is_leaf"] and (r["basis"] == "residual" or r["name"].startswith("Difference")) and abs(r["amount_cents"]) >= M and r["gov"] in GOVS:
            rd[r["gov"]][0] += 1; rd[r["gov"]][1] += abs(r["amount_cents"])
    res["residual_ge1m"] = dict(rd)
    # compare with the previous audit's equivalent for the Midway/Sewer difference boxes
    res["difference_boxes"] = [(r["gov"], r["name"][:60], r["amount_cents"]) for r in rows if r["name"].startswith("Difference") and abs(r["amount_cents"]) >= M]
    res["negative_ge1m_total"] = {g: sum(r["amount_cents"] for r in rows if r["gov"] == g and r["is_leaf"] and r["amount_cents"] <= -M) for g in GOVS}
    # what the residual boxes of $1M or more are made of
    def rkind(r):
        n = r["name"].lower()
        if "overtime" in n: return "police overtime beyond CPD targets"
        if n.startswith("budgeted but not spent") or "not spent yet" in n or "not spent on" in n or "not matched to a payment" in n: return "money not spent or not matched to a payment yet"
        if "bond" in n or "older bonds" in n: return "bonds not printed one by one"
        if "faa" in n or "carryover" in n or "not yet awarded" in n: return "federal airport carryover"
        if "reserve" in n or "project" in n or "not itemised" in n or "ledger" in n or "regional plan" in n or "federal award" in n: return "grant reserve beyond named projects"
        return "other"
    rk = collections.defaultdict(lambda: [0, 0])
    for r in rows:
        if r["is_leaf"] and (r["basis"] == "residual" or r["name"].startswith("Difference")) and abs(r["amount_cents"]) >= M and r["gov"] in GOVS:
            k = (r["gov"], rkind(r)); rk[k][0] += 1; rk[k][1] += abs(r["amount_cents"])
    res["residual_kinds"] = {f"{k[0]}|{k[1]}": v for k, v in rk.items()}
    # side info that exceeds its box (a payments total bigger than the line) is not a reconciliation gap; counted for transparency
    return res

def main():
    rows, by, kids = load()
    out = {}
    print("## 1. Negative leaf boxes by kind")
    neg, detail, agg = negatives(rows, by, kids)
    for k, o in sorted(neg.items(), key=lambda kv: kv[1]["cents"]):
        print(f"  {k[0]:5} {k[1]:30} n={o['n']:4} ${o['cents']/1e8:9.1f}M  >=1M: {o['n_ge1m']:3}  no note/why >=1M: {o['no_expl_ge1m']}  no why >=10M: {o['no_why_ge10m']}")
    print("  negative non-leaf boxes >= $1M (aggregates):", [(r["gov"], r["name"][:40], round(r["amount_cents"]/1e8, 1)) for r in agg])
    out["neg"] = {f"{k[0]}|{k[1]}": o for k, o in neg.items()}; out["neg_detail"] = detail
    print("\n## 2. paid_to_date boxes vs their line (lines where payments exceed the line)")
    over, ok = paid_vs_line(rows, by, kids)
    for x in over[:15]:
        print(f"  {x['gov']:5} line {x['line_cents']/1e8:7.1f}M paid {x['paid_cents']/1e8:7.1f}M over {x['over_cents']/1e8:6.2f}M ({x['ratio']:.2f}x) {x['name'][:50]} | {x['path'][-60:]}")
    print(f"  lines with a negative 'paid beyond' box: {len(over)}, over by ${sum(x['over_cents'] for x in over)/1e8:,.1f}M; lines with payments under the line: {len(ok)} (budget ${sum(a for a,_ in ok)/1e8:,.0f}M, paid ${sum(p for _,p in ok)/1e8:,.0f}M)")
    out["paid_over"] = over; out["paid_ok_n"] = len(ok)
    print("\n## 3. Proxy leaves")
    px, srcs = proxies(rows, by)
    for g, o in px.items(): print(f"  {g}: {o['n']} boxes ${o['cents']/1e8:,.0f}M, no note: {o['no_note']} (${o['no_note_cents']/1e8:,.0f}M), >=10M: {o['ge10m']} (${o['ge10m_cents']/1e8:,.0f}M)")
    for k, v in sorted(srcs.items(), key=lambda kv: -kv[1][1])[:8]: print("  no note >=1M:", k, v[0], round(v[1]/1e8, 1))
    out["proxy"] = {g: o for g, o in px.items()}; out["proxy_nonote_src"] = {f"{k[0]}|{k[1]}": v for k, v in srcs.items()}
    print("\n## 4. Duplicated dollars")
    d = dupes(rows, by, kids)
    for k, v in d.items(): print(f"  {k}: {len(v)}")
    for k in ("ledger_code_fund", "tip_vs_ledger_overlap", "state_lake_stp", "cps_project_number", "award_contract"): print("   ", k, str(d[k])[:600])
    out["dupes"] = {k: v for k, v in d.items()}
    print("\n## 5. Why sentences")
    fl = why_flags(rows, by, kids)
    c = collections.Counter(); cd = collections.Counter()
    for r, f in fl:
        for one in f.split("; "): c[(r["gov"], one)] += 1; cd[(r["gov"], one)] += abs(r["amount_cents"])
    for k, v in c.most_common(): print(f"  {k[0]:5} {v:3} ${cd[k]/1e8:8.1f}M  {k[1]}")
    out["why_flags"] = [{"gov": r["gov"], "id": r["id"], "name": r["name"], "cents": r["amount_cents"], "flag": f} for r, f in fl]
    # reuse of sentences on leaves >= 10M
    why = collections.Counter(); wd = collections.Counter()
    for r in rows:
        if r["is_leaf"] and abs(r["amount_cents"]) >= 10 * M and r["gov"] in GOVS and r["why_cant_go_deeper"]:
            why[(r["gov"], r["why_cant_go_deeper"])] += 1; wd[(r["gov"], r["why_cant_go_deeper"])] += abs(r["amount_cents"])
    big = [r for r in rows if r["is_leaf"] and abs(r["amount_cents"]) >= 10 * M and r["gov"] in GOVS]
    print(f"  leaves >= $10M: {len(big)}, without a why: {sum(1 for r in big if not r['why_cant_go_deeper'])} (${sum(abs(r['amount_cents']) for r in big if not r['why_cant_go_deeper'])/1e8:,.0f}M)")
    for k, v in why.most_common(6): print(f"  reused {v}x ${wd[k]/1e8:,.0f}M {k[0]} {k[1][:90]}")
    of = old_audit_flags(rows, by)
    oc = collections.Counter(r["gov"] for r, _ in of); od = collections.Counter()
    for r, _ in of: od[r["gov"]] += abs(r["amount_cents"])
    print("  previous audit's flag rules on the new tree:", {g: (oc[g], round(od[g]/1e8)) for g in oc})
    print("   by flag:", collections.Counter(f.split(";")[0][:60] for _, f in of).most_common(6))
    out["old_rules"] = {g: [oc[g], od[g]] for g in oc}
    out["why_reuse"] = [(k[0], k[1], v, wd[k]) for k, v in why.most_common(10)]
    out["why_missing"] = [{"gov": r["gov"], "name": r["name"], "cents": r["amount_cents"]} for r in big if not r["why_cant_go_deeper"]]
    print("\n## 6. Reconciliation")
    rc = reconcile(rows, by, kids)
    for k, v in rc.items(): print(f"  {k}: {str(v)[:400]}")
    out["recon"] = rc
    json.dump(out, open(f"{OUT}/quality.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
