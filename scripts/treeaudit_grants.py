"""Audit 3a: city_grants_2026.json reserve_attribution (88 reserve lines) vs what the tree attached under each reserve line.
'attributable' in the file is an upper-bound cap (min of reserve and unspent budget of matched named projects).
Writes raw/treeaudit/grants_reserve.json and prints a summary. Read-only."""
import json, collections
from treeaudit_common import *

def main():
    rows = load_nodes()
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    idx = collections.defaultdict(list)
    for r in rows:
        if r["gov"] == "city" and r["extra"] and '"fund"' in r["extra"] and '"authority"' in r["extra"]:
            e = json.loads(r["extra"])
            if "dept_number" in e:
                idx[(e["fund"], e["dept_number"].lstrip("0"), e["authority"], e["account"])].append(r)
    g = json.load(open(f"{ROOT}/data/city_grants_2026.json"))["reserve_attribution"]
    out = []
    for l in g["lines"]:
        cands = idx.get((l["fund_code"], l["dept_number"].lstrip("0"), l["authority_code"], "909A"), []) + \
                idx.get((l["fund_code"], l["dept_number"].lstrip("0"), l["authority_code"], "9046"), [])
        want = round(l["reserve_amount"] * 100)
        ex = [c for c in cands if c["amount_cents"] == want]
        cands = ex or cands
        row = {"authority": l["ordinance_authority"], "dept": l["ordinance_dept"], "fund": l["fund_code"], "reserve": l["reserve_amount"],
               "attributable": l.get("attributable") or 0, "basis": l.get("attribution_basis"), "named_items": l.get("named_items") if isinstance(l.get("named_items"), int) else len(l.get("named_items") or [])}
        if not cands:
            row.update(node=None, tree_attached=0.0, tree_left_ge10=None); out.append(row); continue
        n = cands[0]
        ch = kids[n["id"]]
        attached = sum(c["amount_cents"] for c in ch if c["basis"] != "residual" and c["kind"] == "grant_project") / 100
        # leaf buckets under this node
        st = [n["id"]]; leaves = []
        by = {r["id"]: r for r in rows}
        while st:
            x = st.pop()
            if kids[x]: st.extend(c["id"] for c in kids[x])
            else: leaves.append(by[x])
        ge = sum(abs(x["amount_cents"]) for x in leaves if bucket(x) == "ge10m") / 100
        row.update(node=n["id"], node_amount=n["amount_cents"] / 100, tree_attached=attached, tree_left_ge10=ge, n_children=len(ch))
        out.append(row)
    json.dump(out, open(f"{OUT}/grants_reserve.json", "w"), indent=1)
    return g, out

if __name__ == "__main__":
    g, out = main()
    print(f"88 reserve lines, ${sum(o['reserve'] for o in out)/1e6:,.1f}M; file says attributable ${g['totals']['attributable_to_named_projects']/1e6:,.1f}M")
    miss = [o for o in out if not o["node"]]
    print("not found in tree:", len(miss), f"${sum(o['reserve'] for o in miss)/1e6:,.1f}M")
    print(f"tree attached as grant_project boxes: ${sum(o['tree_attached'] for o in out)/1e6:,.1f}M")
    print("\nauthority | reserve | attributable (cap) | tree attached | tree dollars still in leaves >= $10M | basis")
    for o in sorted(out, key=lambda o: -(o["attributable"] - o["tree_attached"])):
        gap = o["attributable"] - o["tree_attached"]
        if gap < 1e6: break
        print(f"{o['authority'][:60]:60} {o['reserve']/1e6:7.1f} {o['attributable']/1e6:7.1f} {o['tree_attached']/1e6:7.1f} {((o['tree_left_ge10'] or 0))/1e6:7.1f} {o['basis']}")
    print("\nsum of unattached attributable (cap) where the tree attached nothing:", f"${sum(o['attributable']-o['tree_attached'] for o in out if o['attributable']-o['tree_attached']>0)/1e6:,.1f}M")
