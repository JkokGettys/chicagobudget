"""Audit 2, part 2: list the largest remaining dead ends (leaf >= $10M, not a count x rate box under $1M).
Prints id, amount, basis, path, why. Writes raw/treeaudit2/deadends_<gov>.json (full list, all of them)."""
import json, sys
from treeaudit2_common import *

def deadends():
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    out = {}
    for g in GOVS:
        L = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g and bucket(r) == "ge10m"]
        L.sort(key=lambda r: -abs(r["amount_cents"]))
        out[g] = [{"id": r["id"], "amount_cents": r["amount_cents"], "basis": r["basis"], "name": r["name"],
                   "path": path_names(by, r["id"]), "why": r["why_cant_go_deeper"], "note": r["note"]} for r in L]
    return out

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 30
    out = deadends()
    for g, L in out.items():
        json.dump(L, open(f"{OUT}/deadends_{g}.json", "w"), indent=1)
        tot = sum(abs(x["amount_cents"]) for x in L)
        print(f"\n## {g}: {len(L)} dead ends >= $10M, {tot/1e8:,.0f}M abs; top {n} = {sum(abs(x['amount_cents']) for x in L[:n])/1e8:,.0f}M")
        for i, x in enumerate(L[:n], 1):
            print(f"{i:2}. {x['amount_cents']/1e8:8.1f}M [{x['basis']}] {x['path'][-150:]}\n      id={x['id'][-60:]}\n      WHY: {(x['why'] or 'NONE')[:260]}")
