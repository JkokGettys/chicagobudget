"""Print markdown tables of the 30 largest leaves >= $10M per government (audit 2). Run after treeaudit_top.py."""
import json, sys
from treeaudit_common import *
def main(n_city=30, n_cps=30):
    d = json.load(open(f"{OUT}/top_leaves.json"))
    for g, n in (("city", n_city), ("cps", n_cps), ("parks", 7)):
        print(f"\n### {g}: {d[g]['n_ge10_leaves']} leaves >= $10M, {d[g]['n_flagged']} with a flagged sentence (${d[g]['flag_dollars_cents']/1e8:,.0f}M)\n")
        print("| # | $M | Basis | Box (last two names) | Flag on the why sentence |\n|---:|---:|---|---|---|")
        for i, t in enumerate(d[g]["top"][:n], 1):
            a, b = (t["path"].split(" > ")[-2:] if " > " in t["path"] else ("", t["path"]))
            p = (a[:34] + " > " + b[:52]).replace("|", "/")
            print(f"| {i} | {t['amount']/1e6:,.1f} | {t['basis'][:6]} | {p} | {t['flag'][:60]} |")
if __name__ == "__main__":
    main(*(int(a) for a in sys.argv[1:3]))
