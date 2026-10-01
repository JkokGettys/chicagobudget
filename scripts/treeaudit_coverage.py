"""Audit 1: share of dollars (abs) in leaves < $1M, $1M-$10M, >= $10M, per government and by basis."""
import json
from treeaudit_common import *

def run():
    rows = load_nodes()
    res = {}
    for root in ROOTS:
        leaves = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == root]
        tot = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
        by_basis = {}
        n = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
        for r in leaves:
            b = bucket(r)
            a = abs(r["amount_cents"])
            tot[b] += a
            n[b] += 1
            bb = by_basis.setdefault(r["basis"], {"lt1m": 0, "1m_10m": 0, "ge10m": 0})
            bb[b] += a
        T = sum(tot.values())
        res[root] = {"abs_total_cents": T, "leaves": len(leaves), "buckets": tot, "counts": n, "by_basis": by_basis,
                     "signed_total_cents": sum(r["amount_cents"] for r in leaves)}
    json.dump(res, open(f"{OUT}/coverage.json", "w"), indent=1)
    for root, d in res.items():
        T = d["abs_total_cents"]
        print(f"\n## {root}: {d['leaves']:,} leaves, abs total {usd(T,1)}, signed {usd(d['signed_total_cents'],1)}")
        print("bucket       $M      %   leaves")
        for k in ("lt1m", "1m_10m", "ge10m"):
            print(f"{k:8} {d['buckets'][k]/100/1e6:10.1f} {100*d['buckets'][k]/T:6.1f} {d['counts'][k]:7,}")
        print("basis         <1M     1-10M    >=10M   (all $M)  share of total")
        for b, v in sorted(d["by_basis"].items(), key=lambda x: -sum(x[1].values())):
            s = sum(v.values())
            print(f"{str(b):11} {v['lt1m']/1e8:8.1f} {v['1m_10m']/1e8:8.1f} {v['ge10m']/1e8:8.1f}  {s/1e8:8.1f}  {100*s/T:5.1f}%")

if __name__ == "__main__":
    run()
