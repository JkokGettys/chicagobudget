"""Compare the final gap audit's City view (scripts/audit_tiers.py 'with proxies' rules) with the built tree, line by line.
For each ordinance line in data/leaves_over_10m.json: audit dollars in each size bucket (<$1M, $1M-$10M, >=$10M, signed)
versus the tree's leaves under the matching node. Writes raw/treeaudit/compare_city.json. Read-only."""
import json, collections, re
from treeaudit_common import *
T = 10_000_000.0

def bin_of(x):
    x = abs(x)
    return "lt1" if x < 1e6 else "lt10" if x < T else "ge10"

def over_after(l):
    amt = abs(l["amount"]); s = l["status"]
    if s in ("split_tied", "accepted_single_obligation", "split_proxy"): return []
    if s == "split_partial":
        pcs = [abs(p["amount"]) for p in l["remaining_pieces_over_10m"]]
        cap = l.get("group_cap", amt); tot = sum(pcs)
        return pcs if tot <= cap else [x * cap / tot for x in pcs]
    return [amt]

def audit_alloc(l):
    """Replica of audit_tiers.coverage('proxy') for one inventory line, signed dollars."""
    r = {"lt1": 0.0, "lt10": 0.0, "ge10": 0.0}
    a = l["amount"]; st = l["status"]; pcs = l.get("round3_pieces") or []
    if st == "split_tied" and not pcs: r["lt1"] += a
    elif st == "split_tied":
        for p in pcs: r[bin_of(p["amount"])] += p["amount"]
    elif st == "split_proxy":
        if pcs and not all(p.get("basis") == "count_x_average" for p in pcs):
            s = sum(q["amount"] for q in pcs)
            for p in pcs: r[bin_of(p["amount"])] += p["amount"] * (a / s if s else 1)
        else: r["lt1"] += a
    elif st == "split_partial":
        rem_ = sum(over_after(l)); r["ge10"] += rem_
        if any(f"> {c} " in l["path"] for c in ("0902", "0912")) and pcs:
            got = sum(p["amount"] for p in pcs)
            for p in pcs: r[bin_of(p["amount"])] += p["amount"]
            r["lt10"] += a - rem_ - got
        else: r["lt10"] += a - rem_
    else: r["ge10"] += a
    return r

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    idx = collections.defaultdict(list)
    for r in rows:
        if r["gov"] == "city" and r["extra"] and '"fund_name"' in r["extra"]:
            e = json.loads(r["extra"])
            idx[(e["fund_name"], e["authority_name"], e["account"])].append(r)
    def sub_leaves(nid):
        out, st = [], [nid]
        while st:
            x = st.pop()
            if kids[x]: st.extend(c["id"] for c in kids[x])
            else: out.append(by[x])
        return out
    d = json.load(open(f"{ROOT}/data/leaves_over_10m.json"))
    out = []
    for l in d["leaves"]:
        if l["budget"] != "City": continue
        parts = l["path"].split(" > ")
        k = (parts[2], parts[4], parts[5][:4])
        cands = idx.get(k, [])
        amt_c = round(l["amount"] * 100)
        pick = [c for c in cands if c["amount_cents"] == amt_c] or cands
        if len(pick) != 1:
            dept = parts[3].lower()
            p2 = [c for c in pick if dept in path_names(by, c["id"]).lower()]
            if len(p2) == 1: pick = p2
        if len(pick) != 1:
            print("UNMATCHED", l["path"]); continue
        node = pick[0]
        t = {"lt1": 0.0, "lt10": 0.0, "ge10": 0.0, "ge10_abs": 0.0}
        for x in sub_leaves(node["id"]):
            b = bucket(x); t[{"lt1m": "lt1", "1m_10m": "lt10", "ge10m": "ge10"}[b]] += x["amount_cents"] / 100
            if b == "ge10m": t["ge10_abs"] += abs(x["amount_cents"]) / 100
        out.append({"path": l["path"], "node": node["id"], "amount": l["amount"], "status": l["status"],
                    "audit": audit_alloc(l), "tree": t, "split_source": (l.get("split_source") or "")[:200]})
    json.dump(out, open(f"{OUT}/compare_city.json", "w"), indent=1)
    A = sum(o["audit"]["ge10"] for o in out); Tt = sum(o["tree"]["ge10"] for o in out)
    print(f"inventory lines: {len(out)}   audit >=10M ${A/1e6:,.1f}M   tree >=10M ${Tt/1e6:,.1f}M   diff ${(Tt-A)/1e6:,.1f}M")
    for o in sorted(out, key=lambda o: -abs(o["tree"]["ge10"] - o["audit"]["ge10"]))[:45]:
        dd = o["tree"]["ge10"] - o["audit"]["ge10"]
        if abs(dd) < 1e6: break
        print(f"{dd/1e6:8.1f}M audit {o['audit']['ge10']/1e6:7.1f} tree {o['tree']['ge10']/1e6:7.1f} line {o['amount']/1e6:7.1f} {o['status'][:14]:14} {o['path'].split(' > ',2)[2][:100]}")

if __name__ == "__main__":
    main()
