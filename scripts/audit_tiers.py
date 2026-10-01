#!/usr/bin/env python3
"""Final gap audit: tier every leaf >= $10M (after team splits) as A / B / C, and compute size-bucket coverage per budget.
Reads data/leaves_over_10m.json (run scripts/leaves_inventory.py first). Read-only. Prints markdown tables.
Tier rules (judgment, written down so they can be argued with):
  A  single bond series or loan, single named contract / vendor payment, single named grant award or named project, count x average people splits
     (A-tied = ties to the dollar or is an exact obligation; A-proxy = count x average or vendor list from another year or basis)
  B  purpose is named, no breakdown (contingency, unnamed grant reserve, claims, bond residual of many series, pension contribution, budget programs)
  C  a reader cannot tell what the money is for, or part of it is unexplained
"""
import csv, json, os, re, sys, collections
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE); sys.path.insert(0, HERE)
T = 10_000_000
d = json.load(open(f"{ROOT}/data/leaves_over_10m.json"))
leaves, rem = d["leaves"], d["remaining_pieces_over_10m"]
BASE = {"City": 16_842_553_003, "CPS": 10_253_327_463.68, "Parks": 637_580_350}   # totals the user gave
inv_base = d["summary"]["bases"]

def tier_remaining(p):
    b, lp, pc = p["budget"], (p["leaf_path"] or ""), (p["piece"] or "")
    L = lp.lower(); P = pc.lower()
    if b == "City":
        if "(contract" in P or "contract direct voucher" in P: return "A"      # one named vendor contract or payee
        if "faa grant" in P or "home investment" in P or "home program" in P or "state/lake" in P or "columbus" in P or "canal street" in P \
           or "archer" in P or "montrose" in P or "chicago ave bridge" in P or "purpose:" in P or "strengthening u.s." in P: return "A"   # one named award or project
        if "anadarko" in L: return "A"
        if "9112 property maintenance contract" in L: return "A"
        if "bond series not in" in P: return "B"
        if "group residual" in P: return "B"
        if "not attributable" in P or "unattributed" in P or "not covered by any" in P or "no named project" in P: return "B"
        if "0140 for professional and technical services" in L and "finance general > finance general" in L: return "C"
        return "B"
    if b == "CPS":
        if "gately" in P: return "A"
        if "aramark" in L: return "A"
        if "a54320" in L and "charter/contract per pupil" in L: return "A"      # one charter campus tuition
        if "a58115" in L and "general education fund" in L: return "C"         # $59.3M of $120.6M unexplained (cps_deep.md)
        if "labor and employee rels" in L: return "C"
        if "a58210" in L and "special education fund" in L: return "C"
        if "a58110" in L and "special education fund" in L: return "C"
        return "B"
    if b == "Parks":
        if "soldier field" in L or "harbor" in L: return "A"
        return "B"

def kind_resolved(l):
    s, L = l["status"], l["path"]
    if l["budget"] == "City" and re.search(r"> (0976) ", L): return "B"     # pension contribution: count x average of retirees is context, not a split
    if l["budget"] == "CPS" and ("A58115" in L or "A58275" in L) and s == "split_proxy": return "B"
    if l["budget"] == "Parks" and "Pension" in L: return "B"
    if s in ("split_tied", "accepted_single_obligation"): return "A_tied"
    if s == "split_proxy": return "A_proxy"
    if s == "split_partial":
        if any(f"> {a} " in L for a in ("0902", "0912", "0943", "0944")) or "capitalized construction" in L.lower(): return "A_tied"
        return "A_proxy"
    return None

def over_after(l):
    amt = abs(l["amount"]); s = l["status"]
    if s in ("split_tied", "accepted_single_obligation", "split_proxy"): return []
    if s == "split_partial":
        pcs = [abs(p["amount"]) for p in l["remaining_pieces_over_10m"]]; cap = l.get("group_cap", amt); tot = sum(pcs)
        return pcs if tot <= cap else [x * cap / tot for x in pcs]
    return [amt]

# 1. tiers
tab = {b: collections.defaultdict(lambda: [0, 0.0]) for b in BASE}
tot_leaf = collections.Counter(); chk = collections.Counter()
for l in leaves:
    b = l["budget"]; amt = abs(l["amount"]); tot_leaf[b] += amt
    rem_l = sum(over_after(l)); k = kind_resolved(l)
    if k and k == "B":
        tab[b]["B"][0] += 1; tab[b]["B"][1] += amt; continue            # whole leaf in B (pension)
    if k:   # resolved part, count one item per resolved leaf (unsplit pieces are counted below)
        res = amt - rem_l
        if res > 0: tab[b][k][0] += 1; tab[b][k][1] += res
        else: tab[b][k][1] += res        # group first line carries the pieces: negative balance is cancelled by its siblings
for p in rem:
    l = next(x for x in leaves if x["leaf_path"] == p["leaf_path"]) if False else None
rem_by_leaf = {}
for p in rem:
    t = tier_remaining(p); b = p["budget"]
    # a remaining piece of a pension leaf is already counted whole under B above, skip it
    if b == "City" and re.search(r"> 0976 ", p["leaf_path"] or ""): continue
    if b == "CPS" and ("A58115" in p["leaf_path"] or "A58275" in p["leaf_path"]) and p["status"] in ("split_proxy",): continue
    if t == "A": t = "A_named"   # remaining single named contract / award pieces (2025 payments or award caps), still >= $10M each
    tab[b][t][0] += 1; tab[b][t][1] += p["amount"]
print("## Tiers, leaves >= $10M after team splits (count, $M, % of the budget total)\n")
print("| Budget | Tier | Pieces | $M | % of budget |\n|---|---|---:|---:|---:|")
for b in BASE:
    s = 0
    for t in ("A_tied", "A_proxy", "A_named", "B", "C"):
        n, v = tab[b][t]; s += v
        print(f"| {b} | {t} | {n} | {v/1e6:,.0f} | {100*v/BASE[b]:.1f}% |")
    print(f"| {b} | **all >= $10M leaves (sum of tiers)** | | {s/1e6:,.0f} | {100*s/BASE[b]:.1f}% |")
    print(f"| {b} | check: inventory before-split leaf dollars | | {tot_leaf[b]/1e6:,.0f} | |")
print()
print("Remaining unresolved pieces by tier (what is still >= $10M after splits, no A_tied resolved parts):\n")
rt = collections.defaultdict(lambda: [0, 0.0])
for p in rem:
    if p["budget"] == "City" and re.search(r"> 0976 ", p["leaf_path"] or ""): continue
    t = tier_remaining(p); rt[(p["budget"], t)][0] += 1; rt[(p["budget"], t)][1] += p["amount"]
print("| Budget | Tier | Pieces | $M | % of budget |\n|---|---|---:|---:|---:|")
for b in BASE:
    for t in "ABC":
        n, v = rt[(b, t)]; print(f"| {b} | {t} | {n} | {v/1e6:,.0f} | {100*v/BASE[b]:.1f}% |")
# list C pieces
print("\nTier C pieces:")
for p in sorted(rem, key=lambda p: -p["amount"]):
    if tier_remaining(p) == "C": print(f"  {p['budget']:5} {p['amount']/1e6:7.1f}M  {(p['leaf_path'] or '').split(' > ',1)[-1][-110:]}")

# 2. size-bucket coverage before any split
print("\n## Size buckets of the published leaves (before any split), signed dollars, share of the base used by the inventory\n")
sys.path.insert(0, HERE)
from finance_general import classify
ords = json.load(open(f"{ROOT}/raw/city_appropriations_2026.json"))
city = []
for r in ords:
    a = int(r["_ordinance_amount_"])
    if r["department_description"] == "Finance General" and classify(r["appropriation_account_description"], r["fund_description"])[2]: continue
    desc = r["appropriation_account_description"]
    if (r["appropriation_account"] == "0961" and "Library" in r["fund_description"]) or desc.startswith("To Provide for Matching and Supplementary Grant") \
       or (r["department_description"] == "Finance General" and desc.startswith("Transfer")) \
       or (r["department_description"] != "Finance General" and desc.startswith("For Services Provided by")): continue
    city.append(a)
cps = [float(r["fy_new_budget"]) for r in csv.DictReader(open(f"{ROOT}/raw/cps/cps_2026_exp_unit_fund_program_account.csv"))]
parks_tree = json.load(open(f"{ROOT}/data/parks_2026.json"))
pk = []
def walk(n):
    if not n.get("children"): pk.append(n.get("amount2026", 0))
    for c in n.get("children", []): walk(c)
walk(parks_tree["tree"])
print("| Budget | Leaves | Base $M | < $1M | $1M to $10M | >= $10M |\n|---|---:|---:|---:|---:|---:|")
for name, xs in (("City", city), ("CPS", cps), ("Parks", pk)):
    tot = sum(xs); lo = sum(x for x in xs if abs(x) < 1e6); mid = sum(x for x in xs if 1e6 <= abs(x) < T); hi = sum(x for x in xs if abs(x) >= T)
    print(f"| {name} | {len(xs):,} | {tot/1e6:,.0f} | {100*lo/tot:.1f}% | {100*mid/tot:.1f}% | {100*hi/tot:.1f}% |")
print("\n## After splits: share of the user-given budget total still in leaves >= $10M\n")
sm = d["summary"]
print("| Budget | Before | Tied only (proxies and unsplit stay >= $10M) | With team splits (proxy counted as split) | Of which still tier B/C |\n|---|---:|---:|---:|---:|")
for b in BASE:
    s = sm[b]; bc = sum(rt[(b, t)][1] for t in "BC")
    print(f"| {b} | {100*s['before_dollars']/BASE[b]:.1f}% | {100*s['after_strict_dollars']/BASE[b]:.1f}% | {100*s['after_team_dollars']/BASE[b]:.1f}% | {100*bc/BASE[b]:.1f}% |")

# 3. Terminal items >= $10M that the "team splits" column quietly treats as resolved (single obligations and pension pieces)
print("\n## Terminal items >= $10M hidden inside 'resolved' leaves (dollars, $M)\n")
hid = collections.defaultdict(lambda: collections.defaultdict(float)); hidn = collections.defaultdict(lambda: collections.Counter())
for l in leaves:
    b = l["budget"]; L = l["path"]
    if l["status"] == "accepted_single_obligation":
        hid[b]["single bond series or loan, accepted leaf"] += abs(l["amount"]); hidn[b]["single bond series or loan, accepted leaf"] += 1
    if l["status"] == "split_partial" and any(f"> {a} " in L for a in ("0902", "0912", "0944")) and l["budget"] == "City":
        for p in l.get("round3_pieces", []):
            if p["amount"] >= T: hid[b]["named bond series pieces"] += p["amount"]; hidn[b]["named bond series pieces"] += 1
    if l["status"] == "split_proxy" and (re.search(r"> (0976|097A) ", L) or (b == "Parks" and "Pension" in L)):
        for p in l.get("round3_pieces", []):
            if p.get("amount", 0) >= T: hid[b]["pension pieces (net normal cost, unfunded-liability payment, advance payment)"] += p["amount"]; hidn[b]["pension pieces (net normal cost, unfunded-liability payment, advance payment)"] += 1
print("| Budget | What | Items | $M | % of budget |\n|---|---|---:|---:|---:|")
H = {}
for b in BASE:
    H[b] = sum(hid[b].values())
    for k, v in hid[b].items(): print(f"| {b} | {k} | {hidn[b][k]} | {v/1e6:,.0f} | {100*v/BASE[b]:.1f}% |")

# 4. Coverage by terminal size, signed dollars, base = sum of the inventory's own budget tree (City $16.96B before OBM's unexplained $117M)
def bin_of(x): x = abs(x); return "lt1" if x < 1e6 else "lt10" if x < T else "ge10"
pubbin = {}
for name, xs in (("City", city), ("CPS", cps), ("Parks", pk)):
    # Parks (Vacancy Allowance -$15.2M) and City (Less Corporate Fund Savings -$56.6M) negative offsets of $10M or more are NOT in the leaves inventory (it only keeps positive Parks leaves), so seed them here.
    pubbin[name] = {"lt1": sum(x for x in xs if abs(x) < 1e6), "lt10": sum(x for x in xs if 1e6 <= abs(x) < T),
                    "ge10": sum(x for x in xs if x <= -T) if name in ("Parks", "City") else 0.0, "tot": sum(xs)}
def coverage(mode):
    out = {}
    for b in BASE:
        r = dict(pubbin[b]); tot = r.pop("tot")
        for l in leaves:
            if l["budget"] != b: continue
            a = l["amount"]; st = l["status"]; pcs = l.get("round3_pieces") or []
            if st == "split_tied" and (not pcs):
                r["lt1"] += a                                   # salary rows, count x pay rate, person level
            elif st == "split_tied":
                for p in pcs: r[bin_of(p["amount"])] += p["amount"]
            elif mode == "proxy" and st == "split_proxy":
                if pcs and not all(p.get("basis") == "count_x_average" for p in pcs):
                    for p in pcs: r[bin_of(p["amount"])] += p["amount"] * (a / sum(q["amount"] for q in pcs) if sum(q["amount"] for q in pcs) else 1)
                else: r["lt1"] += a                              # count x average, person or student level
            elif mode == "proxy" and st == "split_partial":
                rem_ = sum(over_after(l)); r["ge10"] += rem_
                if any(f"> {c} " in l["path"] for c in ("0902", "0912")) and pcs:
                    got = sum(p["amount"] for p in pcs)
                    for p in pcs: r[bin_of(p["amount"])] += p["amount"]
                    r["lt10"] += a - rem_ - got                  # rounding between series file and line, goes to $1M-$10M
                else:
                    r["lt10"] += a - rem_                        # named pieces under $10M, not separated into under $1M
            else:
                r["ge10"] += a                                   # unsplit, accepted single obligations, or (tied view) proxy and partial leaves
        out[b] = (r, tot)
    return out
print("\n## Coverage: share of each budget's dollars by the size of the item the user ends on\n")
print("Base is the inventory tree total (City $16,959M, which is $117M above the printed $16,843M). Offsets are counted signed. 'lt $10M' in the proxy view is cumulative below-$10M only for the ordinance named pieces, not separated from under $1M.\n")
print("| Budget | View | < $1M | $1M to $10M | >= $10M | Sum |\n|---|---|---:|---:|---:|---:|")
for mode, label in (("tied", "tied only"), ("proxy", "with proxies")):
    cv = coverage(mode)
    for b in BASE:
        r, tot = cv[b]
        print(f"| {b} | {label} | {100*r['lt1']/tot:.1f}% | {100*r['lt10']/tot:.1f}% | {100*r['ge10']/tot:.1f}% | {100*(r['lt1']+r['lt10']+r['ge10'])/tot:.1f}% |")

# 5. THE headline table: every terminal item >= $10M a user can land on, by tier
print("\n## TERMINAL ITEMS >= $10M BY TIER (the table the audit quotes)\n")
print("A = one bond series or loan, one named contract/payee, one named award or project. B = named purpose, no breakdown (includes pension contributions, unnamed grant reserves, bond residuals, contingency). C = cannot tell what it is for.\n")
term = collections.defaultdict(lambda: [0, 0.0])
for p in rem:                                    # unresolved pieces
    if b_ := p["budget"]:
        if b_ == "City" and re.search(r"> 0976 ", p["leaf_path"] or ""): continue
        t = tier_remaining(p); t = "A" if t == "A" else t
        term[(b_, t)][0] += 1; term[(b_, t)][1] += p["amount"]
for l in leaves:                                  # terminal items inside leaves the team counts as resolved
    b = l["budget"]; L = l["path"]
    if l["status"] == "accepted_single_obligation":
        term[(b, "A")][0] += 1; term[(b, "A")][1] += abs(l["amount"])
    if b == "City" and l["status"] == "split_partial" and any(f"> {a} " in L for a in ("0902", "0912", "0944")):
        for p in l.get("round3_pieces", []):
            if p["amount"] >= T: term[(b, "A")][0] += 1; term[(b, "A")][1] += p["amount"]
    if l["status"] == "split_proxy" and (re.search(r"> (0976|097A) ", L) or (b == "Parks" and "Pension" in L)):
        for p in l.get("round3_pieces", []):
            if p.get("amount", 0) >= T: term[(b, "B")][0] += 1; term[(b, "B")][1] += p["amount"]
# negative offsets of $10M or more outside the leaves inventory (Parks vacancy allowance, City "Less Corporate Fund Savings")
term[("City", "B")][0] += 1; term[("City", "B")][1] += 56_600_000       # absolute value, a planned savings offset
term[("Parks", "B")][0] += 1; term[("Parks", "B")][1] += 15_171_602
print("| Budget | Tier | Items | $M | % of budget total |\n|---|---|---:|---:|---:|")
grand = {}
for b in BASE:
    s = 0
    for t in "ABC":
        n, v = term[(b, t)]; s += v
        print(f"| {b} | {t} | {n} | {v/1e6:,.0f} | {100*v/BASE[b]:.1f}% |")
    grand[b] = s
    print(f"| {b} | all terminal >= $10M | {sum(term[(b,t)][0] for t in 'ABC')} | {s/1e6:,.0f} | {100*s/BASE[b]:.1f}% |")
print("\nNot in the table: the $116,988,502 OBM deduction that no line explains (City tier C by definition, 0.69% of $16.84B).")
