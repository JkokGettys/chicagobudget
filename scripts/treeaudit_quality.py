"""Audit 5: residual and difference boxes over $1M, proxy dollars by government, side_info coverage by department/school/park."""
import json, collections, re
from treeaudit_common import *

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    c = con()
    # ---- residual / difference
    res = [r for r in rows if (r["basis"] == "residual" or r["name"].startswith("Difference")) and abs(r["amount_cents"]) >= M]
    res.sort(key=lambda r: -abs(r["amount_cents"]))
    print(f"== residual or difference boxes >= $1M: {len(res)}  (${sum(abs(r['amount_cents']) for r in res)/1e8:,.0f}M abs)")
    by_g = collections.defaultdict(lambda: [0, 0.0])
    for r in rows:
        if r["basis"] == "residual" or r["name"].startswith("Difference"):
            by_g[root_of(r["id"])][0] += 1; by_g[root_of(r["id"])][1] += abs(r["amount_cents"])
    print("   all residual/difference boxes:", {k: (v[0], round(v[1]/1e8, 1)) for k, v in by_g.items()})
    out = []
    for r in res:
        sib = kids[r["parent_id"]] if r["parent_id"] else []
        out.append({"gov": r["gov"], "amount": r["amount_cents"] / 100, "basis": r["basis"], "name": r["name"][:50], "parent_amount": by[r["parent_id"]]["amount_cents"] / 100 if r["parent_id"] else None,
                    "path": path_names(by, r["parent_id"])[-110:] if r["parent_id"] else "", "n_siblings": len(sib) - 1, "why": (r["why_cant_go_deeper"] or "")[:60]})
        print(f"   {r['amount_cents']/1e8:8.1f}M [{r['gov']:5}] {r['name'][:30]:30} in {path_names(by, r['parent_id'])[-85:]}")
    json.dump(out, open(f"{OUT}/residuals.json", "w"), indent=1)
    # ---- proxy by gov
    print("\n== proxy dollars (abs, leaves) by government and size bucket ($M)")
    for g in ROOTS:
        d = collections.Counter(); n = collections.Counter()
        for r in rows:
            if r["is_leaf"] and root_of(r["id"]) == g and r["basis"] == "proxy":
                d[bucket(r)] += abs(r["amount_cents"]); n[bucket(r)] += 1
        tot = sum(abs(r["amount_cents"]) for r in rows if r["is_leaf"] and root_of(r["id"]) == g)
        print(f"   {g}: proxy leaves {sum(n.values()):,} ${sum(d.values())/1e8:,.1f}M = {100*sum(d.values())/max(tot,1):.1f}% of dollars; <1M {d['lt1m']/1e8:.1f} 1-10M {d['1m_10m']/1e8:.1f} >=10M {d['ge10m']/1e8:.1f}")
    print("   proxy leaves by kind (top):")
    pk = collections.Counter(); pd = collections.Counter()
    for r in rows:
        if r["is_leaf"] and r["basis"] == "proxy": pk[(r["gov"], r["kind"])] += 1; pd[(r["gov"], r["kind"])] += abs(r["amount_cents"])
    for k, v in sorted(pd.items(), key=lambda kv: -kv[1])[:12]: print(f"     {k}: {pk[k]:,} boxes ${v/1e8:,.1f}M")
    # ---- side info coverage
    print("\n== side_info kinds")
    for r in c.execute("select kind,count(*) n,count(distinct node_id) nodes,sum(amount_cents) a from side_info group by kind order by n desc"):
        print(f"   {r['kind']:28} rows {r['n']:6,} nodes {r['nodes']:6,}")
    nk = collections.defaultdict(set)
    for r in c.execute("select node_id,kind from side_info"): nk[r["node_id"]].add(r["kind"])
    def roll_kinds(nid):
        s = set(); st = [nid]
        while st:
            x = st.pop(); s |= nk.get(x, set()); st.extend(k["id"] for k in kids[x])
        return s
    # City departments
    depts = [r for r in rows if r["gov"] == "city" and r["kind"] == "department" and not r["id"].startswith("city-twice")]
    print(f"\n   City departments: {len(depts)}")
    has_v = [d for d in depts if "vendors_paid" in nk.get(d["id"], set())]
    has_p = [d for d in depts if "pay_2025" in roll_kinds(d["id"])]
    print(f"     with vendor payments (own box): {len(has_v)} (${sum(d['amount_cents'] for d in has_v)/1e8:,.0f}M of dept budgets)")
    print(f"     with 2025 pay by title (anywhere below): {len(has_p)} (${sum(d['amount_cents'] for d in has_p)/1e8:,.0f}M)")
    nov = [d for d in depts if "vendors_paid" not in nk.get(d["id"], set())]
    nop = [d for d in depts if "pay_2025" not in roll_kinds(d["id"])]
    print("     NO vendor info:", [(d["name"][:36], round(d["amount_cents"]/1e8, 1)) for d in sorted(nov, key=lambda d: -d["amount_cents"])][:14])
    print("     NO pay info:", [(d["name"][:36], round(d["amount_cents"]/1e8, 1)) for d in sorted(nop, key=lambda d: -d["amount_cents"])][:14])
    # amount of City vendor side-info
    v = c.execute("select sum(amount_cents) from side_info where kind='vendors_paid' and node_id like 'city%'").fetchone()[0]
    print(f"     vendors paid total on City boxes ${v/1e8:,.0f}M; budget of departments having vendors ${sum(d['amount_cents'] for d in has_v)/1e8:,.0f}M")
    # Vendor payments on Finance General / root
    fgv = [r for r in c.execute("select node_id,amount_cents from side_info where kind='vendors_paid' and node_id not in (select id from nodes where kind='department')")]
    print("     vendors_paid on non-department boxes:", [(x['node_id'], round(x['amount_cents']/1e8, 1)) for x in fgv])
    # CPS
    schools = [r for r in rows if r["gov"] == "cps" and r["kind"] == "school"]
    units = [r for r in rows if r["gov"] == "cps" and r["kind"] == "org_unit"]
    kk = collections.Counter()
    for s in schools:
        for k in roll_kinds(s["id"]): kk[k] += 1
    print(f"\n   CPS schools: {len(schools)}; side_info kinds under schools: {dict(kk)}")
    ku = collections.Counter()
    for s in units:
        for k in roll_kinds(s["id"]): ku[k] += 1
    print(f"   CPS org units: {len(units)}; {dict(ku)}")
    cps_kinds = c.execute("select kind,count(*),count(distinct node_id) from side_info where node_id like 'cps%' group by 1").fetchall()
    print("   all CPS side_info kinds:", [tuple(x) for x in cps_kinds])
    # which CPS top boxes have vendor payments
    cv = c.execute("select node_id,amount_cents from side_info where node_id like 'cps%' and kind like '%vendor%'").fetchall()
    print("   CPS vendor side info rows:", len(cv), "total", sum(x[1] or 0 for x in cv) / 1e8, [x[0][:60] for x in cv[:3]])
    # CPS vendor payment budget lines: how many CPS accounts >= 1M have no vendor
    pk_kinds = c.execute("select kind,count(*),count(distinct node_id) from side_info where node_id like 'parks%' group by 1").fetchall()
    print("   all Parks side_info kinds:", [tuple(x) for x in pk_kinds])
    parks = [r for r in rows if r["gov"] == "parks" and r["kind"] == "park"]
    kp = collections.Counter()
    for s in parks:
        for k in roll_kinds(s["id"]): kp[k] += 1
    print(f"   Parks (kind park): {len(parks)}; kinds below: {dict(kp)}")
    # total City budget in lines >= $1M of kind 'contracts' with no vendors anywhere
    print("\n   share of dollars with prior_year_budget side info:", )
    for g in ("city", "cps", "parks"):
        r = c.execute(f"select count(distinct node_id) from side_info where kind in ('prior_year_budget','prior_year_actual') and node_id like '{g}%'").fetchone()[0]
        print(f"     {g}: {r:,} boxes have prior-year info")

if __name__ == "__main__":
    main()
