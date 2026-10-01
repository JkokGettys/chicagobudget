"""Audit extras: bridge numbers, pay-proxy fit, CPS charter/pension unit gap, one-child path exposure, CPS vendor coverage, unused data files."""
import json, re, collections, os
from treeaudit_common import *

def main():
    rows = load_nodes(); by = {r["id"]: r for r in rows}
    kids = collections.defaultdict(list)
    for r in rows:
        if r["parent_id"]: kids[r["parent_id"]].append(r)
    o = json.load(open(f"{OUT}/compare_city.json"))
    A = sum(x["audit"]["ge10"] for x in o) - 56.6e6
    tree = sum(abs(r["amount_cents"]) for r in rows if r["gov"] == "city" and r["is_leaf"] and bucket(r) == "ge10m" and not r["id"].startswith("city-twice")) / 100
    print(f"audit >= $10M signed incl. -56.6M savings box: ${A/1e6:,.1f}M  ({100*A/16_959e6:.1f}% of 16,959M);  tree abs ${tree/1e6:,.1f}M ({100*tree/17_809.1e6:.1f}% of 17,809M)")
    # pay proxies: fit
    pay = [x for x in o if x["status"] == "split_proxy" and ("payroll" in x["split_source"] or "leaves_wages" in x["split_source"]) and x["tree"]["ge10_abs"] >= 0.999 * x["amount"]]
    d = {l["path"]: l for l in json.load(open(f"{ROOT}/data/leaves_over_10m.json"))["leaves"]}
    fit = nofit = 0; rowsf = []
    for x in pay:
        note = d[x["path"]].get("note") or d[x["path"]].get("split_source") or ""
        m = re.search(r"\$([\d.]+)M", note)
        act = float(m.group(1)) * 1e6 if m else None
        ok = act is not None and act <= x["amount"] * 1.0001
        fit += x["amount"] if ok else 0; nofit += 0 if ok else x["amount"]
        rowsf.append((x["amount"], act, ok, x["path"].split(" > ", 2)[2][-70:]))
    print(f"pay/overtime proxy lines left whole: {len(pay)} ${sum(x['amount'] for x in pay)/1e6:,.1f}M; 2025 actual fits inside 2026 line: ${fit/1e6:,.1f}M; exceeds or unknown: ${nofit/1e6:,.1f}M")
    ey = [x for x in o if "EY" in x["split_source"] and x["tree"]["ge10_abs"] >= 0.999 * x["amount"]]
    print(f"EY health-claims shares left whole: {len(ey)} lines ${sum(x['amount'] for x in ey)/1e6:,.1f}M")
    g3 = [x for x in o if x["status"] == "split_proxy" and "leaves_grants" in x["split_source"]]
    for x in g3: print("   grant proxy line", round(x["amount"]/1e6, 1), x["path"].split(" > ", 2)[2][-80:], "tree ge10", round(x["tree"]["ge10_abs"]/1e6, 1))
    # CPS charter: parent with count, leaf without
    ch = [r for r in rows if r["gov"] == "cps" and r["is_leaf"] and bucket(r) == "ge10m" and "Charter/Contract Per Pupil" in r["name"]]
    withparent = [r for r in ch if by[r["parent_id"]]["count"]]
    print(f"CPS charter tuition leaves >= $10M: {len(ch)} (${sum(r['amount_cents'] for r in ch)/1e8:,.1f}M); parent carries students x rate: {len(withparent)}")
    ex = ch[0]; p = by[ex["parent_id"]]
    print("   example parent:", p["name"], p["count"], p["unit_amount_cents"], p["unit_label"], "leaf", ex["name"][:40], ex["count"])
    # leaves under a one-child chain: exposure
    def exposure(g):
        n = tot = 0
        for r in rows:
            if r["is_leaf"] and root_of(r["id"]) == g:
                tot += 1; a = by.get(r["parent_id"]); c = 0
                while a:
                    if len(kids[a["id"]]) == 1: c += 1
                    a = by.get(a["parent_id"])
                n += c
        return n / tot
    print("avg single-child boxes on the way to a leaf:", {g: round(exposure(g), 2) for g in ("city", "cps", "parks")})
    # CPS vendors
    import csv
    sup = list(csv.DictReader(open(f"{ROOT}/data/cps_supplier_payments_fy2026_over1m.csv")))
    c = con()
    labels = [r[0] for r in c.execute("select label from side_info where kind='vendor_payment' and node_id like 'cps%'")]
    attached = 0; miss = []
    for s in sup:
        v = s["vendor"].upper()[:18]
        if any(v in (l or "").upper() for l in labels): attached += float(s["payment_amount"])
        else: miss.append((float(s["payment_amount"]), s["vendor"][:50]))
    tot = sum(float(s["payment_amount"]) for s in sup)
    print(f"CPS FY26 supplier payments >$1M file: {len(sup)} rows ${tot/1e6:,.0f}M; found in side_info labels ${attached/1e6:,.0f}M; not found {len(miss)} rows ${sum(a for a,_ in miss)/1e6:,.0f}M; top missing:", sorted(miss, reverse=True)[:6])
    # pay_2025 coverage by dollars
    jt = [r for r in rows if r["gov"] == "city" and r["kind"] == "job_title"]
    hasp = {r[0] for r in c.execute("select node_id from side_info where kind='pay_2025'")}
    print(f"City job_title boxes {len(jt)} (${sum(abs(r['amount_cents']) for r in jt)/1e8:,.0f}M), with pay_2025: {sum(1 for r in jt if r['id'] in hasp)} (${sum(abs(r['amount_cents']) for r in jt if r['id'] in hasp)/1e8:,.0f}M)")
    # files not read by builders
    src = "".join(open(f"{ROOT}/build/{f}").read() for f in ("city_tree.py", "cps_tree.py", "parks_tree.py"))
    for f in sorted(os.listdir(f"{ROOT}/data")):
        if f.endswith((".json", ".csv")) and f not in src and f != "budget.db": print("   data file not named in any build script:", f, os.path.getsize(f"{ROOT}/data/{f}")//1024, "KB")

if __name__ == "__main__":
    main()
