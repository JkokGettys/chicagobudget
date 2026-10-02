"""Audit 2, part 1b: stricter coverage views, previous snapshot vs now.
(1) strict: no count x rate exemption (a leaf is judged by its own amount).
(2) how much of the dollars now sitting in boxes under $10M rest on a published number (budget, tied, gov_estimate, paid_to_date)
    versus our own estimate (proxy) or leftover (residual, adjustment).
(3) counting differences: leaves with a count and a unit under $1M but an amount of $1M or more.
Writes raw/treeaudit2/strict.json."""
import json
from treeaudit2_common import *

def view(path):
    rows = load_nodes(path); res = {}
    for g in GOVS:
        L = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g]
        T = sum(abs(r["amount_cents"]) for r in L)
        strict = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
        small_by_basis = collections.defaultdict(int)   # leaves under $10M by their own amount, by basis
        for r in L:
            a = abs(r["amount_cents"]); b = "lt1m" if a < M else ("1m_10m" if a < 10 * M else "ge10m")
            strict[b] += a
            if b != "ge10m": small_by_basis[r["basis"]] += a
        cr = [r for r in L if r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M and abs(r["amount_cents"]) >= M]
        # counted with the build rule
        rule = {"lt1m": 0, "1m_10m": 0, "ge10m": 0}
        for r in L: rule[bucket(r)] += abs(r["amount_cents"])
        res[g] = {"total": T, "strict": strict, "rule": rule, "small_by_basis": dict(small_by_basis), "countrate_n": len(cr), "countrate_cents": sum(abs(r["amount_cents"]) for r in cr),
                  "signed_total": sum(r["amount_cents"] for r in L), "signed_ge10m_rule": sum(r["amount_cents"] for r in L if bucket(r) == "ge10m")}
    return res

def main():
    now = view(DB); prev = view(DB_PREV)
    json.dump({"now": now, "prev": prev}, open(f"{OUT}/strict.json", "w"), indent=1)
    print("| Gov | build rule >= $10M prev | now | strict (own amount) >= $10M prev | now | count x rate boxes >= $1M counted small (now) |")
    print("|---|---:|---:|---:|---:|---:|")
    for g in GOVS:
        n, p = now[g], prev[g]
        f = lambda d, k: 100 * d[k]["ge10m"] / d["total"]
        print(f"| {g} | {f(p,'rule'):.1f}% | {f(n,'rule'):.1f}% | {f(p,'strict'):.1f}% | {f(n,'strict'):.1f}% | {n['countrate_n']:,} boxes, ${n['countrate_cents']/1e8:,.0f}M ({100*n['countrate_cents']/n['total']:.0f}% of the government) |")
    print("\nDollars in leaves under $10M by their own amount, by basis ($M), now vs previous; published = budget+tied+gov_estimate+paid_to_date")
    for g in GOVS:
        for lab, d in (("prev", prev[g]), ("now", now[g])):
            sb = d["small_by_basis"]; pub = sum(sb.get(k, 0) for k in ("budget", "tied", "gov_estimate", "paid_to_date"))
            print(f"  {g} {lab}: published {pub/1e8:,.0f}M, proxy {sb.get('proxy',0)/1e8:,.0f}M, residual {sb.get('residual',0)/1e8:,.0f}M, adjustment {sb.get('adjustment',0)/1e8:,.0f}M; total under $10M {sum(sb.values())/1e8:,.0f}M of {d['total']/1e8:,.0f}M")
    print("\nBuild-rule view: share of each government's dollars that end under $10M, split by whether the box rests on a published number")
    print("| Gov | under $10M prev | of which published | of which estimate or leftover | under $10M now | of which published | of which estimate or leftover |")
    print("|---|---:|---:|---:|---:|---:|---:|")
    for g in GOVS:
        cells = []
        for path in (DB_PREV, DB):
            rows = load_nodes(path); L = [r for r in rows if r["is_leaf"] and root_of(r["id"]) == g]
            T = sum(abs(r["amount_cents"]) for r in L)
            pub = sum(abs(r["amount_cents"]) for r in L if bucket(r) != "ge10m" and r["basis"] in ("budget", "tied", "gov_estimate", "paid_to_date"))
            est = sum(abs(r["amount_cents"]) for r in L if bucket(r) != "ge10m" and r["basis"] in ("proxy", "residual", "adjustment"))
            cells += [100*(pub+est)/T, 100*pub/T, 100*est/T]
        print(f"| {g} | {cells[0]:.1f}% | {cells[1]:.1f}% | {cells[2]:.1f}% | {cells[3]:.1f}% | {cells[4]:.1f}% | {cells[5]:.1f}% |")
    print("\nCount x rate leaves of $1M or more that the build rule counts as small, by basis ($M, now)")
    rows = load_nodes()
    for g in GOVS:
        d = collections.defaultdict(lambda: [0, 0])
        for r in rows:
            if r["is_leaf"] and root_of(r["id"]) == g and r["count"] and r["unit_amount_cents"] is not None and abs(r["unit_amount_cents"]) < M and abs(r["amount_cents"]) >= M:
                d[r["basis"]][0] += 1; d[r["basis"]][1] += abs(r["amount_cents"])
        print(f"  {g}: " + ", ".join(f"{b} {n} boxes ${a/1e8:,.0f}M" for b, (n, a) in sorted(d.items(), key=lambda kv: -kv[1][1])))
    print("\nsigned: ", {g: (round(now[g]['signed_total']/1e8), round(100*now[g]['signed_ge10m_rule']/now[g]['signed_total'], 1)) for g in GOVS})

if __name__ == "__main__":
    main()
