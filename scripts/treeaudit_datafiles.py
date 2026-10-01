"""Audit 3: splits that exist in data/ files but did not reach the tree. Read-only.
 a) City lines the final gap audit counted as 'split_proxy' that are still one >= $10M leaf in the tree (does the proxy fit inside the line?)
 b) reserve_attribution named items, size of each item (would they land < $10M?)
 c) bond series / debt_2026 (GO, STSC) vs tree
 d) leaves_pensions benefit_type_pieces, leaves_cps pieces."""
import json, re, collections
from treeaudit_common import *

def a_proxy_lines():
    o = json.load(open(f"{OUT}/compare_city.json"))
    rows = []
    for x in o:
        if x["status"] != "split_proxy": continue
        if x["tree"]["ge10"] < 0.999 * x["amount"]: continue          # tree did attach a split
        m = re.search(r"was \$([\d.,]+)M", x["split_source"] + " " + json.load(open(f"{ROOT}/data/leaves_over_10m.json")) .__class__.__name__) 
        rows.append(x)
    d = {l["path"]: l for l in json.load(open(f"{ROOT}/data/leaves_over_10m.json"))["leaves"]}
    out = []
    for x in rows:
        l = d[x["path"]]
        note = l.get("note") or ""
        m = re.search(r"\$([\d.]+)M", note)
        actual = float(m.group(1)) * 1e6 if m else None
        out.append({"path": x["path"].split(" > ", 2)[2], "line": x["amount"], "actual": actual, "src": l["split_source"][:70], "fits": (actual is not None and actual <= x["amount"] * 1.0001),
                    "pieces": len(l.get("round3_pieces") or []), "note": note[:110]})
    return out

def b_reserve():
    g = json.load(open(f"{ROOT}/data/city_grants_2026.json"))["reserve_attribution"]
    gr = json.load(open(f"{OUT}/grants_reserve.json")) if False else None
    res = []
    for l in g["lines"]:
        items = l.get("named_items") or []
        if not items: continue
        vals = []
        for it in items:
            v = it.get("unspent_budget")
            if v is None: v = it.get("obligation") or it.get("budget") or 0
            vals.append(v)
        cap = l.get("attributable") or 0
        s = sum(vals)
        scale = min(1.0, cap / s) if s else 0
        lt = sum(v * scale for v in vals if v * scale < 10e6); ge = sum(v * scale for v in vals if v * scale >= 10e6)
        res.append({"authority": l["ordinance_authority"][:55], "reserve": l["reserve_amount"], "cap": cap, "n_items": len(items), "items_ge10": sum(1 for v in vals if v * scale >= 10e6),
                    "named_lt10": lt, "named_ge10": ge, "basis": l.get("attribution_basis")})
    return res

if __name__ == "__main__":
    print("== (a) audit split_proxy lines still a single leaf in the tree")
    rows = a_proxy_lines()
    tot = sum(r["line"] for r in rows)
    print(f"{len(rows)} lines, ${tot/1e6:,.1f}M")
    for r in sorted(rows, key=lambda r: -r["line"]):
        a = f"{r['actual']/1e6:,.1f}" if r["actual"] else "?"
        print(f"  {r['line']/1e6:7.1f} actual {a:>7} fits={r['fits']!s:5} pieces={r['pieces']} {r['path'][:80]} | {r['src'][:45]}")
    print("\n   fits inside line:", f"${sum(r['line'] for r in rows if r['fits'])/1e6:,.1f}M", " exceed or unknown:", f"${sum(r['line'] for r in rows if not r['fits'])/1e6:,.1f}M")
    print("\n== (b) reserve_attribution named items: where would they land (cap-scaled)?")
    rr = b_reserve()
    o = json.load(open(f"{OUT}/grants_reserve.json"))
    att = {(x["authority"], x["reserve"]): x for x in o}
    T_lt = T_ge = 0; unatt = []
    for r in rr:
        a = att.get((r["authority"] if False else None, None))
    for r, x in zip(sorted(rr, key=lambda r: -r["reserve"]), []): pass
    byk = {(x["authority"][:55], x["reserve"]): x for x in o}
    for r in sorted(rr, key=lambda r: -r["cap"]):
        x = byk.get((r["authority"], r["reserve"]))
        if x and x["tree_attached"] == 0 and (x["tree_left_ge10"] or 0) > 0:
            T_lt += r["named_lt10"]; T_ge += r["named_ge10"]; unatt.append((r, x))
            print(f"  reserve {r['reserve']/1e6:6.1f} cap {r['cap']/1e6:6.1f} named<10M {r['named_lt10']/1e6:6.1f} named>=10M {r['named_ge10']/1e6:6.1f} items {r['n_items']} ({r['items_ge10']}>=10M) {r['authority']}")
    print(f"  total over lines the tree left whole: named items under $10M ${T_lt/1e6:,.1f}M; items still >= $10M ${T_ge/1e6:,.1f}M")
    json.dump({"proxy_lines": rows, "reserve": rr}, open(f"{OUT}/datafiles.json", "w"), indent=1, default=str)
