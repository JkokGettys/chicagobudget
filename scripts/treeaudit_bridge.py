"""Audit 1b: bridge from the final gap audit's City '>= $10M' share (~52.8%) to the tree's 64.5%.
Uses raw/treeaudit/compare_city.json (run treeaudit_compare.py first). Prints $M per cause and the biggest items."""
import json, collections
from treeaudit_common import *

def cause(x):
    s = x["split_source"]; st = x["status"]
    if st == "split_tied": return "salary lines: vacancy-savings boxes (negative) counted as absolute dollars in the tree"
    if s.startswith("payments"): return "named vendor payments (2026 YTD): audit credited the part under $10M, tree attaches none"
    if "bond_series" in s or "ACFR" in s or "bond" in s.lower(): return "bond series: tree vs audit rounding / Difference boxes"
    if "Mid-Year" in s or "USASpending" in s or "leaves_grants" in s:
        return "grant projects: audit credited the part under $10M, tree attaches none" if st == "split_partial" else "grant proxy (count x rate): audit counted < $1M"
    if "leaves_wages" in s or "payroll costing" in s or "EY" in s: return "pay / overtime / claims proxies (count x average): audit counted < $1M, tree has one leaf"
    if "leaves_health" in s: return "health proxy"
    return "other"

def main():
    o = json.load(open(f"{OUT}/compare_city.json"))
    c = collections.defaultdict(lambda: [0, 0.0, 0.0])
    for x in o:
        k = cause(x)
        c[k][0] += 1
        c[k][1] += x["audit"]["ge10"]
        c[k][2] += x["tree"]["ge10_abs"]
    print("| Cause | lines | audit >= $10M ($M) | tree >= $10M ($M) | tree minus audit |")
    for k, v in sorted(c.items(), key=lambda kv: -(kv[1][2] - kv[1][1])):
        print(f"| {k} | {v[0]} | {v[1]/1e6:,.0f} | {v[2]/1e6:,.0f} | {(v[2]-v[1])/1e6:+,.0f} |")
    A = sum(v[1] for v in c.values()); T = sum(v[2] for v in c.values())
    print(f"| all 202 inventory lines | 202 | {A/1e6:,.0f} | {T/1e6:,.0f} | {(T-A)/1e6:+,.0f} |")
    # denominators
    print("\nitem list (|diff| >= $10M), tree minus audit:")
    for x in sorted(o, key=lambda x: -abs(x["tree"]["ge10_abs"] - x["audit"]["ge10"])):
        d = x["tree"]["ge10_abs"] - x["audit"]["ge10"]
        if abs(d) < 10e6: break
        print(f"{d/1e6:+8.1f} | line {x['amount']/1e6:7.1f} | audit {x['audit']['ge10']/1e6:6.1f} tree {x['tree']['ge10_abs']/1e6:6.1f} | {cause(x)[:34]:34} | {x['path'].split(' > ',2)[2][-85:]}")
    json.dump({k: v for k, v in c.items()}, open(f"{OUT}/bridge.json", "w"), indent=1)

if __name__ == "__main__":
    main()
