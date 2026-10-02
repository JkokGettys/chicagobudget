"""Audit 3, part 1: share of dollars (absolute value) by the size of the box where clicking stops,
per government and by basis, now vs the previous audit snapshot (raw/treeaudit2/budget_snapshot_audit.db).
Writes raw/treeaudit3/coverage.json and prints markdown tables."""
import json, os
from treeaudit3_common import *

def cover(path):
    rows = load_nodes(path)
    res = {}
    for g in GOVS:
        leaves = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g]
        tot = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
        by_basis = {}
        for r in leaves:
            b = bucket(r); a = abs(r["amount_cents"])
            tot[b] += a
            bb = by_basis.setdefault(r["basis"], {"lt1m": 0, "1m_10m": 0, "ge10m": 0})
            bb[b] += a
        res[g] = {"leaves": len(leaves), "total": sum(tot.values()), "buckets": tot, "by_basis": by_basis,
                  "boxes": sum(1 for r in rows if root_of(r["id"]) == g)}
    return res

def pct(x, t): return f"{100*x/t:.1f}%" if t else "0.0%"

def main():
    now = cover(DB)
    prev = cover(DB_PREV) if os.path.exists(DB_PREV) else None
    json.dump({"now": now, "prev": prev}, open(f"{OUT}/coverage.json", "w"), indent=1)
    print("### Where clicking stops (share of absolute leaf dollars)\n")
    print("| Gov | Leaves | Total | < $1M | $1M-$10M | >= $10M | >= $10M previous | Change |")
    print("|---|---:|---:|---:|---:|---:|---:|---:|")
    for g in GOVS:
        n = now[g]; T = n["total"]; p = prev[g] if prev else None
        pp = 100*p["buckets"]["ge10m"]/p["total"] if p else None
        nn = 100*n["buckets"]["ge10m"]/T
        print(f"| {g} | {n['leaves']:,} | {T/1e8:,.0f}M | {pct(n['buckets']['lt1m'],T)} | {pct(n['buckets']['1m_10m'],T)} | **{pct(n['buckets']['ge10m'],T)}** | {pp:.1f}% | {nn-pp:+.1f} pts |")
    print("\n### Same, previous audit in full\n")
    print("| Gov | < $1M | $1M-$10M | >= $10M |\n|---|---:|---:|---:|")
    for g in GOVS:
        p = prev[g]; T = p["total"]
        print(f"| {g} | {pct(p['buckets']['lt1m'],T)} | {pct(p['buckets']['1m_10m'],T)} | {pct(p['buckets']['ge10m'],T)} |")
    print("\n### By basis ($M of leaves, now; and share of the government >= $10M with previous in brackets)\n")
    print("| Gov | Basis | < $1M | $1M-$10M | >= $10M | Total | Share of gov | Total prev | >= $10M prev |")
    print("|---|---|---:|---:|---:|---:|---:|---:|---:|")
    for g in GOVS:
        n = now[g]; T = n["total"]
        order = [b for b in BASES if b in n["by_basis"] or (prev and b in prev[g]["by_basis"])]
        for b in order:
            v = n["by_basis"].get(b, {"lt1m": 0, "1m_10m": 0, "ge10m": 0}); s = sum(v.values())
            pv = prev[g]["by_basis"].get(b, {"lt1m": 0, "1m_10m": 0, "ge10m": 0}) if prev else {"lt1m":0,"1m_10m":0,"ge10m":0}
            print(f"| {g} | {b} | {v['lt1m']/1e8:,.0f} | {v['1m_10m']/1e8:,.0f} | {v['ge10m']/1e8:,.0f} | {s/1e8:,.0f} | {pct(s,T)} | {sum(pv.values())/1e8:,.0f} | {pv['ge10m']/1e8:,.0f} |")
    # memo branch
    rows = load_nodes()
    memo = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == "city-twice"]
    t = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
    for r in memo: t[bucket(r)] += abs(r["amount_cents"])
    T = sum(t.values())
    print(f"\nCity 'counted twice' memo branch: {len(memo)} leaves, {T/1e8:,.0f}M, < $1M {pct(t['lt1m'],T)}, $1M-$10M {pct(t['1m_10m'],T)}, >= $10M {pct(t['ge10m'],T)}")
    # signed and denominators
    for g in GOVS:
        lv = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g]
        signed_ge = sum(r["amount_cents"] for r in lv if bucket(r) == "ge10m")
        signed_tot = sum(r["amount_cents"] for r in lv)
        print(f"{g}: signed total {signed_tot/1e8:,.1f}M, signed >= $10M {signed_ge/1e8:,.1f}M = {100*signed_ge/signed_tot:.1f}% (signed basis)")
    # count x rate boxes counted under 1M although amount >= 1M
    for g in GOVS:
        cr = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g and r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M and abs(r["amount_cents"]) >= M]
        print(f"{g}: count x rate leaves with amount >= $1M but unit < $1M: {len(cr)}, ${sum(abs(r['amount_cents']) for r in cr)/1e8:,.0f}M")

if __name__ == "__main__":
    main()
