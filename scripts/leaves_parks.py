#!/usr/bin/env python3
"""Round 3: Park District leaves using data/parks_capital_projects.json, data/parks_vendors.json and the budget PDF text (raw/parks/txt/p252.txt Appropriation F, p007 budget message).
- Remittance to Aquarium and Museum 625010 ($29,617,600): Appropriation F lists 11 institutions, each tied to the dollar, all under $10M.
- Transfer to Capital Projects 625065 ($10,523,042): ordinance footnote says $10M is TIF surplus capital. Budget message (p.7) splits TIF surplus use: $5M Chicago Grows Together (16 parks, $200K to $500K each) and $5M priority infrastructure. Residual $523,042 derived.
- Soldier Field, harbors, utilities: one payee or one supplier per group (parks_vendors.json), cannot split by public data. Writes data/leaves_parks.json"""
import json, os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
txt = open(f"{ROOT}/raw/parks/txt/p252.txt").read()
inst = []
for ln in txt.splitlines():
    m = re.match(r"\s*(\d+)\.\s+For the (.+?)\s{2,}", ln)
    if m:
        nums = re.findall(r"\d{1,3}(?:,\d{3})+", ln)
        inst.append((m.group(2).strip(), int(nums[-1].replace(",", ""))))
tot_inst = sum(v for _, v in inst)
assert len(inst) == 11 and tot_inst == 29_617_600, (len(inst), tot_inst)
vend = json.load(open(f"{ROOT}/data/parks_vendors.json")); cap = json.load(open(f"{ROOT}/data/parks_capital_projects.json"))
cgt = cap["attribution"]["chicago_grows_together_total"]
leaves = [
 {"match_path_contains": ["625010"], "amount": 29_617_600, "proposed_status": "split_tied",
  "split_basis": "Park District 2026 Appropriations p.246 Appropriation F: 11 named institutions, each = tax levy less loss in collection plus personal property replacement tax. Sum ties to $29,617,600 exactly.",
  "pieces": [{"name": n, "amount": v, "basis": "tied", "source": "raw/parks/txt/p252.txt"} for n, v in inst], "pieces_over_10m_after": [],
  "why_cant_go_deeper": "State law sets one payment for each of 11 museums, and the largest is $4.6M, so there is nothing smaller to show."},
 {"match_path_contains": ["625065"], "amount": 10_523_042, "proposed_status": "split_tied",
  "split_basis": f"Ordinance footnote (p.246): Other Expense includes $10M of TIF surplus capital. Budget message (p.7): $5M funds Chicago Grows Together (16 parks, $200K to $500K each, total ${cgt:,}, data/parks_capital_projects.json) and $5M funds priority infrastructure (fieldhouse air conditioning, lead service line replacement, ADA upgrades for polling sites; no dollars per item). Residual $523,042 is derived.",
  "pieces": [{"name": "Chicago Grows Together: 16 parks x $200K to $500K", "amount": cgt, "basis": "tied", "source": "data/parks_capital_projects.json; raw/parks/txt/p007.txt"},
             {"name": "Priority infrastructure (AC, lead lines, ADA), no per-item dollars", "amount": 5_000_000, "basis": "tied", "source": "raw/parks/txt/p007.txt"},
             {"name": "Remaining operating transfer to capital (derived)", "amount": 10_523_042 - cgt - 5_000_000, "basis": "derived", "source": "10,523,042 minus the two named $5M items"}],
  "pieces_over_10m_after": [], "why_cant_go_deeper": "The District moved this money into its building fund, and the public plan names two $5M uses without a price for each repair."},
 {"match_path_contains": ["626045"], "amount": 36_292_135, "proposed_status": "unsplit",
  "split_basis": "parks_vendors.json: SMG (ASM Global) holds P-12035 Soldier Field and McFetridge, P-15018 Beverly/Morgan Park. The ERP payee list gives one SMG total ($40.6M in 2022 for accounts 626045, 626055, 626065), not by facility. The 2026 budget line is $36.3M for Soldier Field alone. No fee schedule is attached to the Legistar matters.",
  "pieces": [], "pieces_over_10m_after": [{"name": "SMG management of Soldier Field (one contract P-12035)", "amount": 36_292_135}],
  "why_cant_go_deeper": "One company runs Soldier Field for the Park District, and the District does not publish what it pays that company for each job."},
 {"match_path_contains": ["626040"], "amount": 16_580_506, "proposed_status": "unsplit",
  "split_basis": "parks_vendors.json: Westrec Marinas (P-14010) is the only payee mapped to harbor management ($11.5M in 2022). One contract.",
  "pieces": [], "pieces_over_10m_after": [{"name": "Westrec harbor management (one contract P-14010)", "amount": 16_580_506}],
  "why_cant_go_deeper": "One company runs all the boat harbors, and the District does not publish what it pays for each harbor."},
 {"match_path_contains": ["623080"], "amount": 16_707_439, "proposed_status": "unsplit",
  "split_basis": "parks_vendors.json: water and sewer payee not identified (probably the City of Chicago, 2022 list shows $18.9M to unmapped City of Chicago payees).",
  "pieces": [], "pieces_over_10m_after": [{"name": "Water and sewer bills (payee not identified)", "amount": 16_707_439}],
  "why_cant_go_deeper": "This is the water bill for all the parks, and the public list does not show how much each park used."},
 {"match_path_contains": ["623075"], "amount": 14_805_112, "proposed_status": "unsplit",
  "split_basis": "parks_vendors.json: electric and gas suppliers by name (Direct Energy, CenterPoint, Symmetry, ComEd) in 2019 to 2022 only. No 2026 supplier split.",
  "pieces": [], "pieces_over_10m_after": [{"name": "Electric bills (several suppliers, 2019 to 2022 lists only)", "amount": 14_805_112}],
  "why_cant_go_deeper": "This is the electric bill for all the parks, paid to a few power companies, and the public list does not show each park."}]
json.dump({"meta": {"generated_by": "scripts/leaves_parks.py", "sources_fetched": [{"url": "local: raw/parks/txt/p252.txt (https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf)", "http_status": "200 at round 1", "note": "Appropriation F"}]}, "leaves": leaves}, open(f"{ROOT}/data/leaves_parks.json", "w"), indent=1)
print(tot_inst, len(leaves))
