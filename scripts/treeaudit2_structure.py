"""Audit 2, part 4: structure for a 13-year-old. One-child boxes, boxes with more than 200 children, depth, confusing names.
Read-only on raw/treeaudit2/budget_snapshot.db. Writes raw/treeaudit2/structure.json."""
import json, re, collections, statistics
from treeaudit2_common import *

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}; kids = children_map(rows)
    out = {}
    print("## One-child boxes (a click that shows one box)")
    only = [r for r in rows if len(kids[r["id"]]) == 1]
    for g in GOVS + ["city-twice"]:
        o = [r for r in only if root_of(r["id"]) == g]
        same = [r for r in o if kids[r["id"]][0]["amount_cents"] == r["amount_cents"]]
        diff = [r for r in o if kids[r["id"]][0]["amount_cents"] != r["amount_cents"]]
        print(f"  {g}: {len(o):,} one-child boxes ({len(same):,} child equals parent amount, {len(diff):,} child differs). ${sum(abs(r['amount_cents']) for r in o)/1e8:,.0f}M abs")
        out.setdefault("one_child", {})[g] = {"n": len(o), "same": len(same), "diff": len(diff)}
    kc = collections.Counter((root_of(r["id"]), r["kind"], kids[r["id"]][0]["kind"]) for r in only)
    print("  top parent kind -> child kind:", kc.most_common(10))
    # why do they remain: group by whether the one child is a split piece (basis not budget) or structural
    st = collections.Counter(); sd = collections.Counter()
    for r in only:
        c = kids[r["id"]][0]
        k = (root_of(r["id"]), "child is a leaf" if c["is_leaf"] else "child has children", c["basis"])
        st[k] += 1; sd[k] += abs(r["amount_cents"])
    print("  by (gov, child leaf?, child basis):")
    for k, v in st.most_common(12): print(f"    {k}: {v:,} (${sd[k]/1e8:,.0f}M)")
    # one-child boxes where the child is a leaf with a different name than the parent's (more clicks to reach the same leaf)
    chains = []
    for r in rows:
        if len(kids[r["id"]]) == 1 and (not r["parent_id"] or len(kids[r["parent_id"]]) != 1):
            n, ln = r, 0
            while len(kids[n["id"]]) == 1: n = kids[n["id"]][0]; ln += 1
            chains.append((ln, r, n))
    chains.sort(key=lambda x: -x[0])
    print("  longest one-child chains:", [(c[0], root_of(c[1]["id"])) for c in chains[:6]])
    # one-child boxes of $10M+ (the user clicks and sees nothing new)
    big = sorted([r for r in only if abs(r["amount_cents"]) >= 10 * M], key=lambda r: -abs(r["amount_cents"]))
    print(f"  one-child boxes of $10M or more: {len(big)}")
    for r in big[:8]: print(f"    {r['amount_cents']/1e8:8.1f}M [{r['gov']}] {r['name'][:45]} -> {kids[r['id']][0]['name'][:45]}")
    out["one_child_big"] = [{"gov": r["gov"], "name": r["name"], "child": kids[r["id"]][0]["name"], "cents": r["amount_cents"]} for r in big]
    # one-child where child name differs (a real change of kind) vs same name
    samename = sum(1 for r in only if kids[r["id"]][0]["name"] == r["name"])
    print(f"  of these the child has the same name: {samename:,}")
    out["one_child_samename"] = samename

    print("\n## Boxes with more than 200 children")
    wide = sorted([(len(kids[r["id"]]), r) for r in rows if len(kids[r["id"]]) > 200], key=lambda x: -x[0])
    print(f"  {len(wide)} boxes (and {sum(1 for r in rows if 50 < len(kids[r['id']]) <= 200)} with 51 to 200)")
    for n, r in wide[:12]: print(f"   {n:5,} kids ${r['amount_cents']/1e8:8.1f}M [{r['gov']}] {r['kind']} {path_names(by, r['id'])[-80:]}")
    out["wide"] = [{"n": n, "gov": r["gov"], "name": r["name"], "kind": r["kind"], "cents": r["amount_cents"], "path": path_names(by, r["id"])[-100:]} for n, r in wide]
    # how many of the wide boxes' children are tiny
    for n, r in wide[:6]:
        ch = kids[r["id"]]; small = sum(1 for c in ch if abs(c["amount_cents"]) < M)
        print(f"     {r['name'][:40]}: {small} of {n} children under $1M; largest child {max(abs(c['amount_cents']) for c in ch)/1e8:.1f}M")

    print("\n## Depth (clicks from the government box to the leaf; city-twice excluded)")
    for g in GOVS:
        L = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g]
        d = sorted(r["depth"] for r in L); dd = sorted(r["depth"] for r in rows if root_of(r["id"]) == g)
        # dollar-weighted median
        wd = sorted((r["depth"], abs(r["amount_cents"])) for r in L); tot = sum(a for _, a in wd); acc = 0; wmed = None
        for dep, a in wd:
            acc += a
            if acc >= tot / 2: wmed = dep; break
        deep = sum(1 for x in d if x >= 8)
        print(f"  {g}: max depth {d[-1]}, median leaf depth {statistics.median(d)}, dollar-weighted median {wmed}, leaves at depth >= 8: {deep:,} of {len(d):,} ({100*deep/len(d):.0f}%), >= 10: {sum(1 for x in d if x>=10):,}")
        out.setdefault("depth", {})[g] = {"max": d[-1], "median": statistics.median(d), "wmedian": wmed, "ge8": deep, "leaves": len(d), "ge10": sum(1 for x in d if x >= 10)}
    # by kind of leaf: where does the depth come from
    for g in GOVS:
        c = collections.Counter(); 
        for r in rows:
            if r["is_leaf"] and root_of(r["id"]) == g and r["depth"] >= 9: c[r["kind"]] += 1
        print(f"  {g} leaves at depth >= 9 by kind: {c.most_common(6)}")
    deepest = sorted([r for r in rows if r["is_leaf"] and root_of(r["id"]) in GOVS], key=lambda r: -r["depth"])[:4]
    for r in deepest: print(f"   depth {r['depth']}: {path_names(by, r['id'])[-150:]}")
    out["deepest"] = [{"depth": r["depth"], "path": path_names(by, r["id"])} for r in deepest]

    print("\n## Confusing names")
    # 1. identical sibling names
    sib = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: sib[(r["parent_id"], r["name"])].append(r)
    dups = [(k, v) for k, v in sib.items() if len(v) > 1]
    print(f"  same parent, same name: {len(dups)} groups, {sum(len(v) for _, v in dups)} boxes, ${sum(abs(x['amount_cents']) for _, v in dups for x in v)/1e8:,.0f}M abs")
    kd = collections.Counter((v[0]["gov"], v[0]["kind"]) for _, v in dups)
    print("   by (gov, kind):", kd.most_common(8))
    for k, v in sorted(dups, key=lambda kv: -sum(abs(x['amount_cents']) for x in kv[1]))[:6]:
        print(f"   {len(v)}x '{k[1][:60]}' under {path_names(by, k[0])[-50:]} ${sum(x['amount_cents'] for x in v)/1e8:,.1f}M")
    out["dup_siblings"] = {"groups": len(dups), "boxes": sum(len(v) for _, v in dups)}
    # 2. jargon: codes, grant numbers, abbreviations in box names of $10M+ and $1M+
    jargon = re.compile(r"\(\d{2}\.\d{3}|\b(CDBG-DR|CDBG|HUD|CPD|FHWA|IDOT|FAA|FTA|OST|DOJ|OJP|HRSA|ACF|ALN|CMAQ|STP|TIF|ISBE|DFSS|OBM|CTPF|MEABF|PABF|FABF|LABF|IGA|PPRT|EBF|NSS|MEP|ROF|BRM|FAS|ADA|STK)\b|\bF[0-9A-Z]{4}\b|\bA\d{5}\b|\bFG\d{3}|\bBX\b|\(grade")
    for g in GOVS:
        L = [r for r in rows if root_of(r["id"]) == g and r["is_leaf"] and abs(r["amount_cents"]) >= M]
        j = [r for r in L if jargon.search(r["name"])]
        print(f"  {g}: leaves >= $1M with jargon, codes or abbreviations in the name: {len(j):,} of {len(L):,} (${sum(abs(r['amount_cents']) for r in j)/1e8:,.0f}M)")
        out.setdefault("jargon", {})[g] = {"n": len(j), "of": len(L), "cents": sum(abs(r["amount_cents"]) for r in j)}
        ex = sorted(j, key=lambda r: -abs(r["amount_cents"]))[:3]
        for r in ex: print(f"      e.g. {r['name'][:95]}")
    # 3. names that say nothing without the parent (generic names repeated many times)
    gen = collections.Counter(); gd = collections.Counter()
    for r in rows:
        if r["gov"] in GOVS: gen[r["name"]] += 1; gd[r["name"]] += abs(r["amount_cents"])
    print("  most repeated names (count, $M):", [(n[:38], c, round(gd[n]/1e8)) for n, c in gen.most_common(10)])
    out["repeated_names"] = [(n, c, gd[n]) for n, c in gen.most_common(25)]
    # 4. very long names
    longn = [r for r in rows if len(r["name"]) > 100 and r["gov"] in GOVS]
    print(f"  names longer than 100 characters: {len(longn):,} (>=$10M leaves: {sum(1 for r in longn if r['is_leaf'] and abs(r['amount_cents'])>=10*M)})")
    out["long_names"] = len(longn)
    # 5. grant lines in city: 'Reserve Balance (DOT - FAA ...' names at $10M+
    rb = [r for r in rows if r["gov"] == "city" and r["name"].startswith("Reserve Balance") and abs(r["amount_cents"]) >= 10 * M]
    print(f"  City 'Reserve Balance (agency - program (ALN))' boxes of $10M or more: {len(rb)}  ${sum(abs(r['amount_cents']) for r in rb)/1e8:,.0f}M")
    out["reserve_balance_names"] = len(rb)
    # 6. 'Corporate Fund' style names with no department in the label
    cf = [r for r in rows if r["gov"] == "city" and r["kind"] in ("line", "budget_line") and abs(r["amount_cents"]) >= 10 * M and r["is_leaf"]]
    print(f"  City ordinance-line leaves >= $10M: {len(cf)}; names that are the account name only (no department): {sum(1 for r in cf if not re.search(r'[A-Z][a-z]+ (Department|Police|Fire)', r['name']))}")
    json.dump(out, open(f"{OUT}/structure.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
