"""Audit 1c: CPS and Parks. Match the final gap audit's terminal items >= $10M (audit_tiers.py section 5 logic) to tree leaves by amount,
then list tree leaves >= $10M the audit did not count (and the reverse). Read-only."""
import json, re, collections
from treeaudit_common import *
T = 10_000_000.0

def audit_terminals(budget):
    d = json.load(open(f"{ROOT}/data/leaves_over_10m.json"))
    leaves, rem = d["leaves"], d["remaining_pieces_over_10m"]
    out = []
    for p in rem:
        if p["budget"] != budget: continue
        if budget == "CPS" and ("A58115" in p["leaf_path"] or "A58275" in p["leaf_path"]) and p["status"] == "split_proxy": continue
        out.append((p["amount"], "remaining piece: " + (p["piece"] or "")[:50] + " | " + p["leaf_path"][-60:]))
    for l in leaves:
        if l["budget"] != budget: continue
        if l["status"] == "accepted_single_obligation": out.append((abs(l["amount"]), "single obligation: " + l["path"][-70:]))
        if l["status"] == "split_proxy" and budget == "CPS" and ("A58115" in l["path"] or "A58275" in l["path"]):
            for p in l.get("round3_pieces", []):
                if p.get("amount", 0) >= T: out.append((p["amount"], "pension piece: " + p["name"][:60]))
        if l["status"] == "split_proxy" and budget == "Parks" and "Pension" in l["path"]:
            for p in l.get("round3_pieces", []):
                if p.get("amount", 0) >= T: out.append((p["amount"], "pension piece: " + p["name"][:60]))
    return out

def main(root, budget):
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    tl = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == root and bucket(r) == "ge10m"]
    aud = audit_terminals(budget)
    unused = list(tl)
    matched = []
    for amt, desc in sorted(aud, key=lambda x: -x[0]):
        hit = next((r for r in unused if abs(abs(r["amount_cents"]) / 100 - amt) < 2.0), None)
        if hit: unused.remove(hit); matched.append((amt, desc, hit))
    miss_aud = [(a, d) for a, d in aud if not any(m[1] == d and m[0] == a for m in matched)]
    print(f"\n=== {budget}: audit terminal items >= $10M: {len(aud)} (${sum(a for a,_ in aud)/1e6:,.0f}M abs). Tree leaves >= $10M: {len(tl)} (${sum(abs(r['amount_cents']) for r in tl)/1e8:,.0f}M abs)")
    print(f"matched by amount: {len(matched)} (${sum(m[0] for m in matched)/1e6:,.0f}M)")
    print(f"tree >= $10M leaves the audit did not list as terminal: {len(unused)} (${sum(abs(r['amount_cents']) for r in unused)/1e8:,.0f}M)")
    for r in sorted(unused, key=lambda r: -abs(r["amount_cents"]))[:25]:
        print(f"   {r['amount_cents']/1e8:8.1f}M {r['basis']:10} {path_names(by, r['id'])[-110:]}")
    print(f"audit terminal items with no tree leaf of the same amount: {len(miss_aud)} (${sum(a for a,_ in miss_aud)/1e6:,.0f}M)")
    for a, dsc in sorted(miss_aud, reverse=True)[:15]: print(f"   {a/1e6:8.1f}M {dsc[:120]}")
    return unused

if __name__ == "__main__":
    main("cps", "CPS"); main("parks", "Parks")
