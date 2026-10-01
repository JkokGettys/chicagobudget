"""Did anything change the 2026 appropriation ordinance after adoption (2025-12-20)?

Checks, all reproducible from raw/gap (run scripts/gap_fetch.py first):
  1. Mid-Year Budget Report (OBM, data as of 2026-05-31) "Grand Total" budget column vs the ordinance.
  2. Council amendments found through the City Clerk eLMS API (2026 "Annual Appropriation" matters).
  3. Grants (Fund 925) amendments: sum of each ordinance's "hereby appropriated" amount.

Usage: python3 scripts/gap_midyear.py   -> prints findings, writes data/gap_midyear.json
"""
import json
import os
import re
from collections import defaultdict

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "..", "raw")
GAP = os.path.join(RAW, "gap")
OUT = os.path.join(HERE, "..", "data", "gap_midyear.json")

ORD = json.load(open(os.path.join(RAW, "city_appropriations_2026.json")))
ord_local = sum(int(x["_ordinance_amount_"]) for x in ORD if x["fund_type"] == "LOCAL")
ord_grants = sum(int(x["_ordinance_amount_"]) for x in ORD if x["fund_type"] == "GRANTS")
ord_by_fund = defaultdict(int)
for x in ORD:
    ord_by_fund[x["fund_code"]] += int(x["_ordinance_amount_"])

# ---- 1. mid-year report ------------------------------------------------------------------
txt = open(os.path.join(GAP, "midyear_report_2026.txt")).read()
m = re.search(r"Grand Total \$([\d,]+) \$([\d,]+) \$([\d,]+) \$([\d,]+) ([\d.]+)%", txt)
midyear_budget = int(m.group(1).replace(",", ""))
assert midyear_budget == 14_952_722_619

# Motor Fuel Tax (F0310) and Parking Meters (F0B26): the report lists them at exactly 2x the ordinance.
mft_lines = [int(a.replace(",", "")) for a in re.findall(r"F0310 - Motor Fuel Tax Fund \$([\d,]+)", txt)]
pm_lines = [int(a.replace(",", "")) for a in re.findall(r"F0B26 - Chicago Parking Meters Fund \$([\d,]+)", txt)]
mft_extra = sum(mft_lines) - ord_by_fund["0310"]
pm_extra = sum(pm_lines) - ord_by_fund["0B26"]
assert sum(mft_lines) == 2 * ord_by_fund["0310"] and sum(pm_lines) == 2 * ord_by_fund["0B26"]

# Ward Council Office lines: 449,170 in the ordinance, 440,270 for 29 wards after SO2026-0023373.
wards = re.findall(r"Ward (\d\d) Council Office \$([\d,]+) \$([\d,]+)", txt)
assert len(wards) == 50 and all(a == "449,170" for _, a, _ in wards)
ward_cut = sum(449_170 - int(b.replace(",", "")) for _, _, b in wards)
n_cut = sum(1 for _, _, b in wards if b == "440,270")

identity = ord_local + mft_extra + pm_extra - ward_cut
assert identity == midyear_budget, (identity, midyear_budget)
print(f"ordinance local funds                     {ord_local:>16,}")
print(f"+ Motor Fuel Tax listed twice             {mft_extra:>16,}")
print(f"+ Parking Meters Fund listed twice        {pm_extra:>16,}")
print(f"- ward wage allowance cut ({n_cut} wards x 8,900) {-ward_cut:>12,}")
print(f"= mid-year report 'Grand Total' (printed) {midyear_budget:>16,}   MATCHES EXACTLY\n")

# ---- 2/3. eLMS amendments ------------------------------------------------------------------
meta = json.load(open(os.path.join(GAP, "elms_2026_approp_meta.json")))
by_rec = {}
for rec, intro, final, title, fn, p in meta:
    by_rec.setdefault(rec, {"intro": intro, "final": final[:10] if final else None, "title": title, "files": []})
    by_rec[rec]["files"].append(p)

g925 = []
for rec, d in sorted(by_rec.items(), key=lambda kv: kv[1]["final"] or ""):
    if "Fund No. 925" not in d["title"]:
        continue
    amt = None
    for f in d["files"]:
        f = f if os.path.isabs(f) or os.path.exists(f) else os.path.join(GAP, f)
        t = f[:-4] + ".txt"
        if os.path.exists(t):
            mm = re.search(r"amount of \$\s?([\d,]+) is hereby appropriated", open(t).read())
            if mm:
                amt = int(mm.group(1).replace(",", ""))
                break
    g925.append((rec, d["final"], amt, d["title"][:90]))
tot_may = sum(a for r, f, a, t in g925 if a and f <= "2026-05-31")
tot_all = sum(a for r, f, a, t in g925 if a)
assert 3_869_858_000 + tot_may == 3_902_864_330   # printed in Mid-Year Report p. 27
print("Fund 925 grant amendments (Council passed; amount from each ordinance text):")
for r, f, a, t in g925:
    print(f"  {r:14} passed {f}  {'(no $ parsed)' if a is None else f'{a:>12,}'}  {t}")
print(f"through 2026-05-31: {tot_may:,}  -> 3,869,858,000 + {tot_may:,} = {3_869_858_000 + tot_may:,}"
      f"  (Mid-Year Report p. 27 prints 3,902,864,330: MATCHES)")
print(f"through 2026-09-23: {tot_all:,}  -> grants appropriation now {3_869_858_000 + tot_all:,}")

# Budget Transfer Report Source Data (7x7d-3zgj): within-fund moves only, no change to totals
tr = json.load(open(os.path.join(GAP, "budget_transfers_2026.json")))
bfy26 = [r for r in tr if r["bfy"] == "2026"]
cross = [r for r in tr if r["budget_authority_line_from"].split(".")[1] != r["budget_authority_line_to"].split(".")[1]
         or r["budget_authority_line_from"].split(".")[2] != r["budget_authority_line_to"].split(".")[2]]
print(f"\nBudget Transfer Report dataset: {len(tr)} rows, BFY2026 {len(bfy26)} rows = "
      f"{sum(float(r['transfer_amount']) for r in bfy26):,.0f}; rows that cross fund or department: {len(cross)}")

out = {
    "ordinance_local": ord_local, "ordinance_grants": ord_grants,
    "midyear_grand_total": midyear_budget, "mft_double": mft_extra, "parking_meters_double": pm_extra,
    "ward_wage_cut_total": ward_cut, "wards_cut": n_cut,
    "grant_925_amendments": [{"record": r, "passed": f, "amount": a, "title": t} for r, f, a, t in g925],
    "grant_925_through_may": tot_may, "grant_925_through_sep": tot_all,
    "grants_appropriation_after_amendments": 3_869_858_000 + tot_all,
    "budget_transfers_bfy2026_rows": len(bfy26),
    "budget_transfers_bfy2026_total": sum(float(r["transfer_amount"]) for r in bfy26),
    "budget_transfers_cross_fund_or_dept": len(cross),
}
json.dump(out, open(OUT, "w"), indent=1)
print("wrote", os.path.relpath(OUT))
