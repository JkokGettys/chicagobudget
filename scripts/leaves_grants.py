#!/usr/bin/env python3
"""Round 3, item 2c: grant reserves and stormwater lines. Caps are UPPER BOUNDS (unspent obligation), not exact splits.
Reads raw/contracts/midyear_grants.csv (Mid-Year Grants, as of 2025-06-01 extract), raw/grants/usaspending_chicago_awards.json,
raw/leaves/usa_sub.json (USASpending sub-awards, fetched by scripts/leaves_usa_sub.py: 0 rows to the City for ALN 20.205/20.507),
raw/leaves/r3/faa_fy2025.xlsx (FAA FY2025 AIP grant list, https://www.faa.gov/sites/faa.gov/files/2025-11/FY_2025_AIP_Grants.xlsx, HTTP 200),
raw/leaves/r3/cdbgdr_plan.pdf text (CDBG-DR Action Plan, HTTP 200). Writes data/leaves_grants.json"""
import csv, json, os, warnings
warnings.filterwarnings("ignore")
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
T = 10_000_000
mg = list(csv.DictReader(open(f"{ROOT}/raw/contracts/midyear_grants.csv")))
usa = json.load(open(f"{ROOT}/raw/grants/usaspending_chicago_awards.json"))
sub = json.load(open(f"{ROOT}/raw/leaves/usa_sub.json"))
f = lambda x: float(x) if x not in (None, "") else 0.0
def projects(sel):
    out = {}
    for r in mg:
        if sel(r):
            k = r["grant_project_description"].strip().upper()[:70]
            out.setdefault(k, 0.0); out[k] += max(0.0, f(r["budget"]) - f(r["expended_project_to_date"]))
    return out
leaves = []
def pieces_from(pr, reserve, label):
    named = sorted(pr.items(), key=lambda x: -x[1]); tot = sum(v for _, v in named)
    att = min(reserve, tot)
    over = [{"name": f"{n} (unspent, Mid-Year Grants)", "amount": round(v)} for n, v in named if v >= T]
    small = [v for _, v in named if v < T]
    resid = reserve - att
    if resid >= T: over.append({"name": "reserve not covered by any Mid-Year project (unattributed)", "amount": round(resid)})
    return att, over, len(named), len(small), sum(small), resid
# ---- FHWA 20.205 (CDOT) reserve
att, over, n, ns, ss, resid = pieces_from(projects(lambda r: r["department_code"] == "D84" and r["aln_code"] == "20.205"), 162_040_000, "FHWA")
leaves.append({"match_path_contains": ["DOT - FHWA - IDOT - CTY", "909A"], "amount": 162_040_000, "proposed_status": "split_partial",
  "split_basis": f"Mid-Year Grants (extract 2025-06-01) projects with ALN 20.205 in CDOT: {n} projects, unspent budget sums to ${att/1e6:.1f}M (cap); {ns} of them are under $10M (${ss/1e6:.1f}M together).",
  "pieces": [{"name": "named projects, unspent budget", "amount": round(att), "basis": "cap_unspent_obligation", "source": "raw/contracts/midyear_grants.csv"}],
  "pieces_over_10m_after": over, "why_cant_go_deeper": "This is money the federal government promised for road and bridge jobs, and a few big jobs hold most of it while the rest has no job picked yet."})
# ---- FTA 20.507: one project, four funding sources
fta_mid = projects(lambda r: r["department_code"] == "D84" and r["aln_code"] == "20.507")
rows = [r for r in mg if r["department_code"] == "D84" and r["aln_code"] == "20.507"]
by_src = sorted(((r["fund_description"].strip(), max(0.0, f(r["budget"]) - f(r["expended_project_to_date"])), r["grant_project_description"][:40]) for r in rows), key=lambda x: -x[1])
award = next(a for a in usa if a["Award ID"] == "IL-2016-002")
usa_unspent = award["Award Amount"] - (award["Total Outlays"] or 0)
att_fta = min(362_703_000, usa_unspent)
pcs = [{"name": f"State/Lake Loop Elevated Station, {s} (Mid-Year unspent)", "amount": round(a)} for s, a, _ in by_src if a >= T]
other_in_award = att_fta - sum(a for _, a, _ in by_src)
pcs.append({"name": "State/Lake Loop Elevated Station: rest of FTA award IL-2016-002 not shown by funding source in Mid-Year Grants (cap, USASpending obligation minus outlays)", "amount": round(other_in_award)})
pcs.append({"name": "reserve above the one USASpending award (unattributed)", "amount": round(362_703_000 - att_fta)})
leaves.append({"match_path_contains": ["DOT - FTA - Federal Transit Formula", "909A"], "amount": 362_703_000, "proposed_status": "split_partial",
  "split_basis": f"USASpending prime award IL-2016-002 (State/Lake Loop Elevated Station): obligation ${award['Award Amount']/1e6:.1f}M minus outlays ${award['Total Outlays']/1e6:.1f}M = ${usa_unspent/1e6:.1f}M unspent (cap). Mid-Year Grants shows the same project in 4 funding sources (STP, CMAQ, CRP). USASpending sub-awards to the City for ALN 20.507 and 20.205: 0 rows (HTTP 200).",
  "pieces": [{"name": "State/Lake Loop Elevated Station (one named project)", "amount": round(att_fta), "basis": "cap_unspent_obligation", "source": "USASpending award IL-2016-002"}],
  "pieces_over_10m_after": pcs, "move_from_unattributed": round(261_200_000 - (362_703_000 - att_fta)),
  "why_cant_go_deeper": "Almost all of this money is for one big train station rebuild, and the public lists show it by where the money came from, not by what each dollar buys."})
# ---- FAA O'Hare reserve: verify named awards against the FAA FY2025 list
import openpyxl
wb = openpyxl.load_workbook(f"{ROOT}/raw/leaves/r3/faa_fy2025.xlsx", read_only=True)
faa = {}
for row in wb["Data"].iter_rows(min_row=4, values_only=True):
    if row[3] in ("ORD", "MDW") and row[5]:
        s = row[5].split("-"); faa["".join(s[:5])] = {"loc": row[3], "amount": row[17], "summary": row[18]}
grants = json.load(open(f"{ROOT}/data/city_grants_2026.json"))
oh = next(x for x in grants["reserve_attribution"]["lines"] if "O'Hare (20.106)" in x["grant_name"] and x["reserve_amount"] > 4e8)
named = []
for ni in oh["named_items"]:
    unspent = ni["obligation"] - (ni.get("outlay") or 0)
    fa = faa.get(ni["usaspending_award_id"])
    named.append({"award": ni["usaspending_award_id"], "unspent": round(unspent), "faa_project_summary": fa["summary"] if fa else None, "faa_list_amount": fa["amount"] if fa else None})
named.sort(key=lambda x: -x["unspent"])
over = [{"name": f"FAA grant {n['award']}: {n['faa_project_summary'] or 'see USASpending description'} (unspent obligation)", "amount": n["unspent"]} for n in named if n["unspent"] >= T]
res_unattr = oh["reserve_amount"] - oh["attributable"]
over.append({"name": "reserve not covered by any named FAA award (unattributed)", "amount": round(res_unattr)})
leaves.append({"match_path_contains": ["Airport Improvement Program - O'Hare (20.106)", "909A"], "amount": oh["reserve_amount"], "proposed_status": "split_partial",
  "split_basis": f"26 named FAA awards (USASpending, place of performance O'Hare). {sum(1 for n in named if n['faa_list_amount'])} of them verified against the FAA FY2025 AIP grant list (project type and amount). Unspent obligation caps.",
  "pieces": named[:30], "pieces_over_10m_after": over,
  "why_cant_go_deeper": "The airport has promises of federal money for runways and terminals, but not enough named jobs yet to explain the rest."})
# ---- CDBG-DR stormwater: tie to Action Plan table 38 and unit cost table 25
sewer_per_mile = 8_500_000
miles = 221_342_000 / sewer_per_mile
leaves.append({"match_path_contains": ["CDBG-DR - Stormwater Infrastructure - Local Sewer Line Construction", "0540"], "amount": 221_342_000, "proposed_status": "split_proxy",
  "split_basis": f"CDBG-DR Action Plan (HTTP 200, PDF p.50 Table 25) estimates local sewer rehab at $8,500,000 per mile. $221,342,000 / $8.5M = {miles:.1f} miles x $8.5M (count derived from the plan's own unit cost, PROXY). The plan names no street list. The six stormwater lines in the ordinance sum to $390,279,000 against the plan's $390,277,600 Infrastructure and Mitigation Program (Table 38, p.73), a $1,400 difference.",
  "pieces": [],  # 2026-10-02: superseded by data/splits/city/drgr_cdbgdr.json (104 blocks, City hearing deck p.14). The old proxy was miles x $8.5M.
  "pieces_over_10m_after": [{"name": "Local sewer line construction (no street list)", "amount": 221_342_000}], "why_cant_go_deeper": "The plan says how many miles of sewer it hopes to fix and what a mile costs, but the streets have not been picked yet."})
for tail, amt, why in (("Permeable Alleys", 67_104_000, "The city wants to make alleys soak up rain, but no list of which alleys has been published."), ("Wing Storage", 62_097_000, "Wing storage means big underground water tanks, and the plan does not say how many or where.")):
    leaves.append({"match_path_contains": [f"CDBG-DR - Stormwater Infrastructure - {tail}", "0540"], "amount": amt, "proposed_status": "unsplit",
      "split_basis": "CDBG-DR Action Plan (Table 38 p.73) names the program and the project types but gives no per-project budget or unit cost for this type. No split made.",
      "pieces": [], "pieces_over_10m_after": [{"name": f"{tail} (no project list)", "amount": amt}], "why_cant_go_deeper": why})
meta = {"generated_by": "scripts/leaves_grants.py", "sources_fetched": [
  {"url": "https://api.usaspending.gov/api/v2/search/spending_by_award/ (subawards:true, ALN 20.205 and 20.507, recipient City of Chicago)", "http_status": 200, "note": "0 sub-awards to the City, dead end (raw/leaves/usa_sub.json)"},
  {"url": "https://api.usaspending.gov/api/v2/search/spending_by_award/ (prime awards, recipient CDOT, ALN 20.507/20.205/20.500/20.934)", "http_status": 200, "note": "only IL-2016-002 State/Lake is large; no ALN 20.205 prime awards to CDOT because 20.205 passes through IDOT"},
  {"url": "https://www.faa.gov/sites/faa.gov/files/2025-11/FY_2025_AIP_Grants.xlsx", "http_status": 200, "note": "9 O'Hare and 2 Midway FY2025 grants, 9 of 9 O'Hare FAINs match the named awards"},
  {"url": "https://www.faa.gov/airports/aip/grant_histories/2026", "http_status": 404, "note": "FY2026 list not yet published"},
  {"url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/CoC%20CDBG-DR%20Action%20Plan_Website.pdf", "http_status": 200, "note": "Table 25 unit cost, Table 38 program $390,277,600"},
  {"url": "https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026Mid-YearBudgetReport.pdf", "http_status": 200, "note": "grant tables list project, not carryover by award"},
  {"url": "https://www.flychicago.com/ohare/ohare21 and 2 variants", "http_status": "403 or 404", "note": "O'Hare 21 project list not reachable by script"},
  {"url": "https://www.chicago.gov/city/en/depts/cdot/provdrs/infrastructure.html", "http_status": 404, "note": "CDOT capital list not found"}],
  "caveat": "All attributed amounts are caps (unspent obligation), not exact splits. Mid-Year Grants is the 2025-06-01 extract."}
json.dump({"meta": meta, "leaves": leaves}, open(f"{ROOT}/data/leaves_grants.json", "w"), indent=1)
for l in leaves: print(l["proposed_status"], l["match_path_contains"][0][:50], l["amount"], [round(p["amount"]/1e6,1) for p in l["pieces_over_10m_after"]][:8])
