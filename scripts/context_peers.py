"""Peer-city spending per resident: Chicago vs New York City, Los Angeles, Houston, Philadelphia.

Source: U.S. Census Bureau, 2024 Annual Survey of State and Local Government Finances, Individual Unit
Files (public use). One record per government and item code, in thousands of dollars.
  https://www2.census.gov/programs-surveys/gov-finances/tables/2024/2024_Individual_Unit_Files.zip
Population for each city is the Census file's own population field (Fin_PID_2024.txt).

Why Census and not each city's budget book: Census applies the same definitions to every city,
so police in one city means the same thing as police in another. A city budget book does not.

Important comparability limits (written into the output):
- These are CITY GOVERNMENT only. In NYC, the city runs schools, hospitals, transit funding, welfare and
  housing, which Chicago does not (CPS, CTA, Cook County and the Housing Authority are separate). In
  Houston, Chicago and LA, other governments also provide services. So do NOT add up all categories and
  compare totals. Compare single functions (police, fire, parks, etc.) only.
- 'Current operation' excludes capital construction and interest. Whether pension costs for police and fire
  sit inside the police line differs by city and is NOT verified here. Chicago pays pensions through
  Finance General, not through CPD.
- Census year is each city's fiscal year ending in 2024 (June for NYC, LA, Houston, Philadelphia).
  Chicago is calendar 2024. These are 2024 dollars, not FY2026.
- Philadelphia has a combined city-county government, so its 'health' and 'welfare' lines include
  county-type services.

Usage: python3 scripts/context_peers.py -> data/context_peers_2024.json
"""
import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from context_common import fetch, raw_path, write_json  # noqa: E402

URL = "https://www2.census.gov/programs-surveys/gov-finances/tables/2024/2024_Individual_Unit_Files.zip"

# Census unit IDs (state FIPS + type + county + unit). Verified against Fin_PID_2024.txt names.
CITIES = {
    "Chicago": "172031162236",
    "New York City": "362061194805",
    "Los Angeles": "062037161174",
    "Houston": "482201176169",
    "Philadelphia": "422101133602",
}

# Item codes (from the 2024 Technical Documentation): current operation only.
ITEMS = {
    "E62": "Police protection",
    "E24": "Fire protection",
    "E81": "Garbage and solid waste (sanitation)",
    "E80": "Sewerage",
    "E91": "Water utility",
    "E44": "Streets and highways (regular highways)",
    "E61": "Parks and recreation",
    "E52": "Libraries",
    "E32": "Public health",
    "E50": "Housing and community development",
    "E79": "Public welfare (other)",
    "E01": "Airports",
    "E23": "Financial administration",
    "E29": "Central staff services",
    "E66": "Protective inspection and regulation (permits, inspections)",
    "E25": "Judicial and legal",
    "E89": "General expenditure not elsewhere classified",
}
# Services Chicago does not run itself (so zero or missing is expected), shown for context.
FOOTNOTES = {
    "E94": "Transit utilities: NYC and LA run transit; Chicago's CTA is a separate government.",
    "E36": "Hospitals: NYC runs public hospitals; Chicago does not.",
}
TOTAL_ITEM_NOTE = "Not provided: we do not add categories into a 'total', see comparability limits."


def main():
    zpath = fetch(URL, "census_2024_units.zip", timeout=300)
    z = zipfile.ZipFile(zpath)
    names = z.namelist()
    fin = [n for n in names if "FinEstDAT" in n][0]
    pid = [n for n in names if n.endswith("Fin_PID_2024.txt")][0]

    # Population + names
    pops = {}
    pid_name = {}
    fy_end = {}
    with z.open(pid) as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            uid = line[:12]
            if uid in CITIES.values():
                pid_name[uid] = line[12:76].strip()
                pops[uid] = int(line[116:125].strip())
                fy_end[uid] = line[140:144]  # MMDD, e.g. 1231 or 0630
    # Amounts
    amt = {uid: {} for uid in CITIES.values()}
    with z.open(fin) as f:
        for line in io.TextIOWrapper(f, encoding="latin-1"):
            uid = line[:12]
            if uid in amt:
                code = line[12:15]
                thousands = int(line[15:27])
                flag = line[31:33].strip()
                amt[uid][code] = (thousands * 1000, flag)

    cities = {}
    for city, uid in CITIES.items():
        items = {}
        for code, label in ITEMS.items():
            if code in amt[uid]:
                dollars, flag = amt[uid][code]
                items[code] = {"label": label, "dollars": dollars,
                               "per_resident": round(dollars / pops[uid], 2), "census_flag": flag}
            else:
                items[code] = {"label": label, "dollars": None, "per_resident": None, "census_flag": "not reported"}
        cities[city] = {
            "census_unit_id": uid, "census_name": pid_name[uid], "population_census_file": pops[uid],
            "fiscal_year_end_mmdd_2024": fy_end[uid],
            "items": items,
        }

    # Compare Chicago to the average of the 4 peers, for items where all 5 report
    NOT_COMPARABLE = {"E23", "E29", "E89"}
    comparisons = {}
    for code, label in ITEMS.items():
        if code in NOT_COMPARABLE:
            continue
        vals = {c: cities[c]["items"][code]["per_resident"] for c in CITIES}
        if all(v is not None for v in vals.values()):
            peers = [v for c, v in vals.items() if c != "Chicago"]
            comparisons[code] = {
                "label": label, "chicago_per_resident": vals["Chicago"],
                "peer_average_per_resident": round(sum(peers) / len(peers), 2),
                "peer_min": min(peers), "peer_max": max(peers),
                "chicago_vs_peer_average_pct": round((vals["Chicago"] / (sum(peers) / len(peers)) - 1) * 100, 1),
                "rank_among_5_highest_first": sorted(vals.values(), reverse=True).index(vals["Chicago"]) + 1,
            }

    out = {
        "source": "U.S. Census Bureau, 2024 Annual Survey of State and Local Government Finances, Individual Unit Files",
        "source_url": URL,
        "technical_documentation": "Inside the zip: '2024 S&L Public Use Files Technical Documentation.pdf' (item codes E62 police, E24 fire, E81 solid waste, etc.)",
        "dollar_year": "Fiscal year ending in 2024 (Chicago: Dec 2024. NYC, LA, Houston, Philadelphia: June 2024).",
        "comparability_limits": [
            "City government only. NYC's city government also runs schools, hospitals and welfare, Chicago's does not, so never compare all-in totals.",
            "Current operation only: excludes construction and debt interest. NOT VERIFIED: whether each city's police and fire pension payments land inside or outside the police and fire lines. Chicago budgets them in Finance General, not CPD, so Chicago police per resident may look lower than a city that books pensions inside police. Treat police and fire gaps as approximate.",
            "Chicago's population in the Census file (2,665,039) is an older estimate than the ACS 2024 figure (2,721,326) used elsewhere, so per-resident numbers here would be about 2% lower with the ACS figure. We use the Census file's own population for all five cities for a fair comparison.",
            "These are 2024 numbers, not FY2026.",
            "Philadelphia is a combined city-county, so health and welfare include county-type services.",
            "Items E23 (financial administration), E29 (central staff) and E89 (general, not elsewhere classified) are catch-alls. Chicago's E23 is $4.46B, about 3x the peer average per resident. That is an inference, not a Census statement: Chicago's Finance General costs (pensions, benefits, debt-related) are probably coded there. We keep them per city but do NOT compare them (comparable=false).",
            "Each city's budget books define 'police' differently. Census uses one definition for all, but it still cannot see whether a city pays police pensions inside or outside the police line.",
            "Census marks each value with a flag, R means reported. The flag is saved on every number in cities.*.items.*.census_flag.",
        ],
        "footnotes": FOOTNOTES,
        "cities": cities,
        "chicago_vs_peers": comparisons,
    }
    write_json("context_peers_2024.json", out)
    for code, c in comparisons.items():
        print("%-4s %-45s CHI %7.0f  peers avg %7.0f  (%+.0f%%)  rank %d" % (
            code, c["label"][:45], c["chicago_per_resident"], c["peer_average_per_resident"],
            c["chicago_vs_peer_average_pct"], c["rank_among_5_highest_first"]))
    print({c: cities[c]["population_census_file"] for c in cities})


if __name__ == "__main__":
    main()
