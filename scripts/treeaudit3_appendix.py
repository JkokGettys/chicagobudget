"""Audit 3 appendix: top 30 dead ends per government, tagged, with the previous (audit 2 snapshot) rank for the same box.
Reads raw/treeaudit3/rank.json (now) and raw/treeaudit3/prev/rank.json (audit-2 snapshot re-tagged with the same rules).
Matches a box to the previous list by id, else by name and amount. Writes raw/treeaudit3/appendix.md."""
import json, re, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "raw", "treeaudit3")
now = json.load(open(f"{D}/rank.json"))["rows"]; prev = json.load(open(f"{D}/prev/rank.json"))["rows"]
SHORT = {"Construction of Buildings and Other Structures": "Construction", "For Professional and Technical Services and Other Third Party Benefit Agreements": "Professional services", "Paid from: ": ""}
def label(r):
    nm = r["path"].split(" > "); nm = " > ".join(nm[-2:]) if len(nm) > 1 else nm[0]
    nm = re.sub(r"\s*\((?:[A-Za-z]+ - )+[^()]*(?:\([^()]*\))?[^()]*\)", "", nm)
    for a, b in SHORT.items(): nm = nm.replace(a, b)
    return (nm if len(nm) <= 78 else nm[:75] + "...").replace("|", "/")
out = []
for g, title in (("city", "City of Chicago"), ("cps", "Chicago Public Schools"), ("parks", "Chicago Park District")):
    byid = {r["id"]: r for r in prev[g]}; byna = {(r["name"], r["cents"]): r for r in prev[g]}
    tot = sum(abs(r["cents"]) for r in now[g])
    out.append(f"**{title}** ({len(now[g])} dead ends of $10M or more, ${tot/1e8:,.0f}M)\n")
    out.append("| # | Prev # | $M | Box | Basis | Tag | Why it stops |\n|---:|---:|---:|---|---|:-:|---|")
    for r in now[g][:30]:
        p = byid.get(r["id"]) or byna.get((r["name"], r["cents"]))
        pr = f"{p['rank']}" if p else "new"
        out.append(f"| {r['rank']} | {pr} | {r['cents']/1e8:,.1f} | {label(r)} | {r['basis'][:6]} | {r['tag']} | {r['why']} |")
    out.append("")
open(f"{D}/appendix.md", "w").write("\n".join(out))
print("\n".join(out))
