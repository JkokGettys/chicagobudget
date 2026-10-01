"""Audit 4 and 5: structure and data quality of the built tree (snapshot). Prints markdown-ready tables, writes raw/treeaudit/structure.json."""
import json, collections, re
from treeaudit_common import *

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    res = {}
    # ---- only children
    only = [r for r in rows if len(kids[r["id"]]) == 1]
    chains = []
    for r in rows:
        if len(kids[r["id"]]) == 1 and (r["parent_id"] is None or len(kids[r["parent_id"]]) != 1):
            n, ln = r, 0
            while len(kids[n["id"]]) == 1:
                n = kids[n["id"]][0]; ln += 1
            chains.append((ln, r, n))
    print("== boxes with exactly one child, by government")
    by_g = collections.Counter(root_of(r["id"]) for r in only)
    for g in ROOTS: print(f"  {g}: {by_g[g]:,} boxes ({sum(1 for r in rows if root_of(r['id'])==g):,} total)")
    # kinds of only-children
    kc = collections.Counter(); kd = collections.Counter()
    for r in only:
        c = kids[r["id"]][0]
        key = (root_of(r["id"]), r["kind"], c["kind"])
        kc[key] += 1; kd[key] += abs(r["amount_cents"])
    print("  top (gov, parent kind -> child kind):")
    for k, v in kc.most_common(14): print(f"    {k} {v:,} (${kd[k]/1e8:,.0f}M)")
    # same-amount: child equals parent amount
    same = [r for r in only if kids[r["id"]][0]["amount_cents"] == r["amount_cents"]]
    print(f"  of which the child has the identical amount: {len(same):,}")
    # same name as child
    samename = [r for r in only if kids[r["id"]][0]["name"] == r["name"]]
    print(f"  of which the child has the identical name: {len(samename):,}")
    # chains >=3
    long_chains = sorted(chains, key=lambda x: -x[0])
    print("  longest one-child chains:", [(c[0], root_of(c[1]['id'])) for c in long_chains[:8]])
    # one-child by gov at depth where the user would click
    res["only_child"] = dict(by_g)
    res["only_child_same_amount"] = len(same)
    # ---- depth
    dep = collections.Counter((root_of(r["id"]), r["depth"]) for r in rows if r["is_leaf"])
    mx = {g: max((d for (gg, d) in dep if gg == g), default=0) for g in ROOTS}
    print("\n== depth (clicks from the top; id dot count)")
    for g in ROOTS:
        ds = sorted(d for (gg, d) in dep if gg == g)
        tot = sum(v for (gg, d), v in dep.items() if gg == g)
        deep = sum(v for (gg, d), v in dep.items() if gg == g and d >= 8)
        print(f"  {g}: max depth {mx[g]}, leaves at depth >= 8: {deep:,} of {tot:,}; median leaf depth {sorted(sum(([d]*v for (gg,d),v in dep.items() if gg==g), []))[tot//2]}")
    deepest = sorted([r for r in rows if r["is_leaf"]], key=lambda r: -r["depth"])[:5]
    for r in deepest: print(f"   depth {r['depth']}: {path_names(by, r['id'])[-170:]}")
    # actual hop depth via parent chain length
    def hops(r):
        n = 0
        while r["parent_id"]: r = by[r["parent_id"]]; n += 1
        return n
    # ---- wide
    wide = sorted([(len(kids[r["id"]]), r) for r in rows if len(kids[r["id"]]) > 200], key=lambda x: -x[0])
    print(f"\n== boxes with more than 200 children: {len(wide)}")
    for n, r in wide[:25]:
        print(f"   {n:6,} kids ${r['amount_cents']/1e8:9,.1f}M [{r['gov']}] {path_names(by, r['id'])[-110:]}")
    res["wide"] = [(n, r["id"], r["amount_cents"]) for n, r in wide]
    w50 = sum(1 for r in rows if 50 < len(kids[r["id"]]) <= 200)
    print(f"   (and {w50} boxes with 51 to 200 children)")
    # ---- names
    print("\n== duplicate sibling names (same parent, same name)")
    sib = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: sib[(r["parent_id"], r["name"])].append(r)
    dups = [(k, v) for k, v in sib.items() if len(v) > 1]
    print(f"   {len(dups)} groups, {sum(len(v) for _, v in dups)} boxes")
    for k, v in sorted(dups, key=lambda kv: -sum(abs(x['amount_cents']) for x in kv[1]))[:8]:
        print(f"   {len(v)}x '{k[1][:60]}' under {path_names(by, k[0])[-60:]} ${sum(x['amount_cents'] for x in v)/1e8:,.1f}M")
    print("\n== most repeated box names (whole tree), top 25")
    nm = collections.Counter(); nd = collections.Counter()
    for r in rows: nm[r["name"]] += 1; nd[r["name"]] += abs(r["amount_cents"])
    for k, v in nm.most_common(25): print(f"   {v:5,}x '{k[:70]}' (${nd[k]/1e8:,.0f}M)")
    res["names"] = nm.most_common(60)
    # generic names a child would not understand: names of kind line that are official strings with long length or codes
    longn = [r for r in rows if len(r["name"]) > 90]
    print(f"\n   names longer than 90 chars: {len(longn):,} ({sum(1 for r in longn if r['is_leaf'])} leaves)")
    codey = [r for r in rows if re.match(r"^[A-Z]\d{4,5}\b", r["name"]) or re.search(r"\b\d{4}-\d{4}\b", r["name"])]
    print(f"   names starting with an account/fund code: {len(codey):,}")
    sib2 = [r for r in rows if re.search(r"\(.*Fund\)|\(\d\d\.\d{3}\)", r["name"]) and r["is_leaf"]]
    print(f"   leaf names with a fund or grant code in parentheses: {len(sib2):,}")
    # ---- negatives
    print("\n== negative boxes")
    neg = [r for r in rows if r["amount_cents"] < 0]
    print(f"   {len(neg):,} boxes, ${sum(r['amount_cents'] for r in neg)/1e8:,.1f}M; leaves {sum(1 for r in neg if r['is_leaf'])}")
    for g in ROOTS:
        ng = [r for r in neg if root_of(r['id']) == g]
        print(f"   {g}: {len(ng):,} boxes ${sum(r['amount_cents'] for r in ng)/1e8:,.1f}M; below -$1M: {sum(1 for r in ng if r['amount_cents'] <= -M)}; named by kind: {collections.Counter(r['kind'] for r in ng).most_common(3)}")
    # negative non-leaf containers
    print("   negative containers (parents) :", sum(1 for r in neg if not r["is_leaf"]))
    # ---- tiny
    tiny = [r for r in rows if r["is_leaf"] and abs(r["amount_cents"]) <= 10_00]
    print(f"\n== tiny leaves (<= $10): {len(tiny):,}; by kind {collections.Counter(r['kind'] for r in tiny).most_common(4)}; by gov {collections.Counter(r['gov'] for r in tiny)}")
    tiny1k = [r for r in rows if r["is_leaf"] and abs(r["amount_cents"]) <= 1000_00]
    print(f"   leaves <= $1,000: {len(tiny1k):,}")
    tiny_res = [r for r in rows if r["is_leaf"] and r["basis"] in ("residual", "adjustment") and abs(r["amount_cents"]) <= 100_00]
    print(f"   residual/adjustment leaves <= $100: {len(tiny_res):,} (${sum(abs(r['amount_cents']) for r in tiny_res)/100:,.0f}); kinds {collections.Counter(r['kind'] for r in tiny_res).most_common(4)}")
    for g in ROOTS:
        t = [r for r in tiny if root_of(r['id']) == g]
        print(f"   {g}: {len(t)} leaves <= $10")
    res["tiny"] = len(tiny)
    # ---- residual larger than siblings
    print("\n== residual (Other / not itemised, Difference) boxes bigger than every sibling")
    big_res = []
    for r in rows:
        if r["basis"] in ("residual",) and r["is_leaf"] and r["parent_id"]:
            sibs = [s for s in kids[r["parent_id"]] if s["id"] != r["id"]]
            if sibs and abs(r["amount_cents"]) > max(abs(s["amount_cents"]) for s in sibs) and abs(r["amount_cents"]) >= M:
                big_res.append((abs(r["amount_cents"]), r, len(sibs)))
    big_res.sort(key=lambda x: -x[0])
    print(f"   {len(big_res)} residual leaves >= $1M bigger than all their siblings, ${sum(x[0] for x in big_res)/1e8:,.0f}M")
    for a, r, ns in big_res[:12]:
        print(f"   ${a/1e8:7.1f}M vs {ns} siblings [{r['gov']}] {path_names(by, r['parent_id'])[-85:]}")
    res["big_res"] = [(a, r["id"]) for a, r, _ in big_res]
    json.dump(res, open(f"{OUT}/structure.json", "w"), indent=1, default=str)

if __name__ == "__main__":
    main()
