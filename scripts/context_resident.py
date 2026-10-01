"""Per-resident / per-student math and the Chicago property tax bill split.

Sources (all public, fetched live and cached in raw/context/):
- Population, median income, households, median home value:
  ACS 2024 1-year, table B01003/B19013/B11001/B25077 for Chicago city (geoid 16000US1714000),
  read through the Census Reporter API (the Census API itself now needs a free key).
- CPS 20th-day enrollment SY2025-26 (316,224) and SY2026-27 (304,687):
  CPS demographics workbooks on cps.edu.
- Property tax rates: Cook County Clerk 2025 Tax Rate Report PDF (tax year 2025, newest) and the
  2024 report (tax year 2024), "City of Chicago 2024/2025 Tax Rates" table.
- Total tax billed: same Clerk reports, "Quick Facts" page.

Usage: python3 scripts/context_resident.py -> data/context_resident_2026.json
"""
import json
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(__file__))
from context_common import (fetch, load_json, norm, pdf_text, read_text, write_json)  # noqa: E402

CR_URL = ("https://api.censusreporter.org/1.0/data/show/latest?table_ids=B01003,B19013,B11001,B25077"
          "&geo_ids=16000US1714000")
CPS_SY26 = ("https://www.cps.edu/globalassets/cps-pages/about-cps/district-data/demographics/"
            "demographics_racialethnic_20thday_sy2026_forweb.xlsx")
CPS_SY27 = ("https://www.cps.edu/globalassets/cps-pages/about-cps/district-data/demographics/"
            "2026-27-demographics-racial-ethnic-20th-day-report.xlsx")
TR2025 = "https://www.cookcountyclerkil.gov/publication/2025-tax-rate-report"
TR2024 = "https://www.cookcountyclerkil.gov/publication/2024-tax-rate-report"


def xlsx_district_total(path):
    """Read the 'District Total' row of the Schools sheet without openpyxl."""
    z = zipfile.ZipFile(path)
    ss = []
    if "xl/sharedStrings.xml" in z.namelist():
        x = z.read("xl/sharedStrings.xml").decode("utf8")
        for si in re.findall(r"<si>(.*?)</si>", x, flags=re.S):
            ss.append("".join(re.findall(r"<t[^>]*>(.*?)</t>", si, flags=re.S)))
    wb = z.read("xl/workbook.xml").decode()
    names = re.findall(r'<sheet [^>]*name="([^"]+)"', wb)
    idx = names.index("District") + 1
    x = z.read("xl/worksheets/sheet%d.xml" % idx).decode("utf8")
    for r in re.findall(r"<row [^>]*>(.*?)</row>", x, flags=re.S):
        cells = []
        for a, b in re.findall(r"<c ([^>]*?)(?:/>|>(.*?)</c>)", r, flags=re.S):
            v = re.search(r"<v>(.*?)</v>", b or "")
            val = v.group(1) if v else ""
            if 't="s"' in a and val:
                val = ss[int(val)]
            cells.append(val)
        if cells and cells[0].startswith("District Total"):
            return int(float(cells[1]))
    raise RuntimeError("District Total not found in " + path)


def parse_rates(txt, year):
    """Pull the 'City of Chicago <year> Tax Rates' rows we care about."""
    out = {}
    pat = {
        "Chicago Board of Education (CPS)": r"^BOARD OF EDUCATION\s+([0-9.]+)\s+([0-9.]+)\s",
        "City of Chicago (corporate levy)": r"^CITY OF CHICAGO CORPORATE\s+([0-9.]+)\s+([0-9.]+)\s",
        "City of Chicago Library Fund": r"^CITY OF CHICAGO LIBRARY FUND\s+([0-9.]+)\s+([0-9.]+)\s",
        "City of Chicago School Building and Improvement Fund": r"^CITY OF CHICAGO SCHOOL BLDG & IMP FUND\s+([0-9.]+)\s+([0-9.]+)\s",
        "Chicago Park District": r"^CHICAGO PARK DISTRICT\s+([0-9.]+)\s+([0-9.]+)\s",
        "Forest Preserve District": r"^FOREST PRESERVE DISTRICT OF COOK COUNTY\s+([0-9.]+)\s+([0-9.]+)\s",
        "Metropolitan Water Reclamation District": r"^METRO WATER RECLAMATION DIST OF GR CHGO\s+([0-9.]+)\s+([0-9.]+)\s",
        "City Colleges (District 508)": r"^CHICAGO COMMUNITY COLLEGE DISTRICT 508\s+([0-9.]+)\s+([0-9.]+)\s",
    }
    for line in txt.split("\n"):
        line = line.strip()
        for k, p in pat.items():
            m = re.match(p, line)
            if m and k not in out:
                out[k] = (float(m.group(1)), float(m.group(2)))
        # County row is glued together in the PDF text: "COUNTY OF COOK 0.3559540.390469 -8.84%"
        m = re.match(r"^COUNTY OF COOK\s+(\d\.\d{6})(\d\.\d{6})\s", line)
        if m and "Cook County (and Consolidated Elections)" not in out:
            out["Cook County (and Consolidated Elections)"] = (float(m.group(1)), float(m.group(2)))
    return out


def main():
    # ---- ACS population ----
    p = fetch(CR_URL, "acs_chicago_cr.json")
    acs = json.load(open(p))
    g = acs["data"]["16000US1714000"]
    pop = int(g["B01003"]["estimate"]["B01003001"])
    pop_moe = int(g["B01003"]["error"]["B01003001"])
    med_income = int(g["B19013"]["estimate"]["B19013001"])
    households = int(g["B11001"]["estimate"]["B11001001"])
    med_home = int(g["B25077"]["estimate"]["B25077001"])
    release = acs.get("release", {})

    # ---- CPS enrollment ----
    e26 = xlsx_district_total(fetch(CPS_SY26, "demographics_racialethnic_20thday_sy2026_forweb.xlsx"))
    e27 = xlsx_district_total(fetch(CPS_SY27, "2026-27-demographics-racial-ethnic-20th-day-report.xlsx"))

    # ---- Tax rates ----
    t25 = pdf_text(fetch(TR2025, "taxrate2025.pdf"))
    t24 = pdf_text(fetch(TR2024, "taxrate2024.pdf"))
    r25 = parse_rates(t25, 2025)
    r24 = parse_rates(t24, 2024)
    # In the Clerk's "City of Chicago Tax Rates" table each row prints "<this year> <prior year> <% change>".
    # We do not trust column order: below we pick the column whose sum equals the printed composite rate.
    composite25 = float(re.search(r"6\.618606%\s+([0-9.]+)%", t25).group(1))

    def pick(rates, idx):
        return {k: v[idx] for k, v in rates.items()}
    s25 = sum(pick(r25, 1).values())
    s25_alt = sum(pick(r25, 0).values())
    # Choose the column whose sum equals the printed 2025 composite.
    if abs(s25 - composite25) < 1e-6:
        rates2025 = pick(r25, 1)
        rates2024_from25 = pick(r25, 0)
    elif abs(s25_alt - composite25) < 1e-6:
        rates2025 = pick(r25, 0)
        rates2024_from25 = pick(r25, 1)
    else:
        raise RuntimeError("2025 rates do not sum to printed composite %.6f (got %.6f / %.6f)" % (composite25, s25, s25_alt))
    total2025 = sum(rates2025.values())

    # ---- Total tax billed (Quick Facts) ----
    def grab(txt, label):
        m = re.search(label + r"[^\n]*?\$([0-9,]+)\s+\$([0-9,]+)", txt)
        return int(m.group(2).replace(",", "")) if m else None
    billed_chi_2025 = grab(t25, r"Total Tax Billed in Chicago:")
    billed_cook_2025 = grab(t25, r"Total Tax Billed in Cook County:")
    ext_cps_2025 = grab(t25, r"Chicago Board of Education")
    ext_city_2025 = grab(t25, r"City of Chicago3")
    ext_county_2025 = grab(t25, r"Cook County\s+\(and Consolidated Elections\)")
    eav_chi_2025 = grab(t25, r"City of Chicago EAV \(in Cook County\)")
    eav = re.search(r"City of Chicago EAV \(in Cook County\)\s+\$([0-9,]+)\s+\$([0-9,]+)", t25)
    eav_chi_2025 = int(eav.group(2).replace(",", ""))

    # Share of a typical Chicago bill by agency (rate / total rate). This is "share of the rate".
    shares = {k: v / total2025 for k, v in rates2025.items()}
    city_total_rate = (rates2025["City of Chicago (corporate levy)"] + rates2025["City of Chicago Library Fund"])
    groups = {
        "Chicago Public Schools (Board of Education)": rates2025["Chicago Board of Education (CPS)"],
        "City of Chicago (corporate levy plus library fund)": city_total_rate,
        "City of Chicago School Building and Improvement Fund (separate City levy, listed apart)": rates2025["City of Chicago School Building and Improvement Fund"],
        "Cook County (county + forest preserve)": (rates2025["Cook County (and Consolidated Elections)"]
                                                   + rates2025["Forest Preserve District"]),
        "Chicago Park District": rates2025["Chicago Park District"],
        "City Colleges": rates2025["City Colleges (District 508)"],
        "Water Reclamation District (stormwater and sewage treatment)": rates2025["Metropolitan Water Reclamation District"],
    }
    group_share = {k: v / total2025 for k, v in groups.items()}

    # Worked example: Clerk's own sample bill method. 2025 sample from the report, if present.
    example_ev = 250000
    # Method printed by the Clerk: (Market value x 10% x equalization factor - $10,000 homeowner exemption) x rate.
    eq_factor_2025 = float(re.search(r"Equalization Factor:\s+[0-9.]+\s+([0-9.]+)", t25).group(1))
    eav_after_ex = example_ev * 0.10 * eq_factor_2025 - 10000
    example_bill = eav_after_ex * total2025 / 100.0
    example_split = {k: eav_after_ex * v / 100.0 for k, v in groups.items()}

    out = {
        "generated_by": "scripts/context_resident.py",
        "population": {
            "chicago_population": pop,
            "margin_of_error_90pct": pop_moe,
            "median_household_income": med_income,
            "households": households,
            "median_home_value": med_home,
            "source": "American Community Survey " + release.get("name", "ACS 2024 1-year"),
            "source_url": CR_URL,
            "census_table_ids": ["B01003", "B19013", "B11001", "B25077"],
            "geoid": "16000US1714000",
            "note": "The Census API now requires a free key, so this reads the same ACS table through Census Reporter (https://censusreporter.org).",
        },
        "cps_enrollment": {
            "sy2025_26_20th_day": e26,
            "sy2026_27_20th_day": e27,
            "change_pct": round((e27 - e26) / e26 * 100, 2),
            "source_urls": [CPS_SY26, CPS_SY27, "https://www.cps.edu/about/stats-facts/"],
            "note": "20th-day counts include district-run, charter and contract schools (CPS 'enrollment'). FY2026 budget (Jul 2025 to Jun 2026) lines up with SY2025-26.",
        },
        "per_resident_divisors": {
            "per_resident": pop,
            "per_household": households,
            "per_cps_student_fy2026": e26,
            "per_cps_student_latest": e27,
        },
        "tax_bill": {
            "tax_year": 2025,
            "note_timing": "Tax year 2025 rates, collected in calendar 2026 (Treasurer convention: tax year N is billed in N+1). Overlaps the City FY2026 budget year.",
            "source_url": TR2025,
            "source_also": TR2024,
            "total_composite_rate_pct": total2025,
            "printed_composite_rate_pct": composite25,
            "rates_pct_by_agency": rates2025,
            "tax_year_2024_rates_pct_by_agency": rates2024_from25,
            "share_of_rate_by_agency": shares,
            "groups_rate_pct": groups,
            "group_share_of_bill": group_share,
            "total_tax_billed_in_chicago_2025": billed_chi_2025,
            "total_tax_billed_in_cook_county_2025": billed_cook_2025,
            "extension_cps_2025": ext_cps_2025,
            "extension_city_2025": ext_city_2025,
            "extension_cook_county_2025": ext_county_2025,
            "extension_share_of_total_billed_in_chicago": {
                "cps": ext_cps_2025 / billed_chi_2025,
                "city_incl_library_and_school_bldg": ext_city_2025 / billed_chi_2025,
                "cook_county_and_elections": ext_county_2025 / billed_chi_2025,
                "note": "Dollar shares of the $9.07B billed in Chicago. They are lower than the rate shares (CPS 55.9%) mostly because the billed total includes tax on property inside TIF districts, which goes to the TIF fund and not to these governments. Check: CPS extension $4.155B divided by ($9.066B billed minus about $1.59B TIF) = 55.6%, close to the 55.9% rate share. The $1.59B is the Clerk's tax year 2024 TIF total as reported by WTTW (https://news.wttw.com/2026/01/22/share-chicago-property-tax-revenues-claimed-tif-funds-grew-166-2024-report). It is NOT the tax year 2025 TIF total, so treat this as an approximate check. Parks, City Colleges, Water Reclamation and Forest Preserve are also in the billed total but not in these three lines. For 'what does a typical home's bill pay for', use group_share_of_bill. For 'how many dollars does each government levy', use the extension numbers.",
                "approx_check_cps_share_ex_tif_using_tax_year_2024_tif": ext_cps_2025 / (billed_chi_2025 - 1_590_000_000),
            },
            "chicago_eav_2025": eav_chi_2025,
            "equalization_factor_2025": eq_factor_2025,
            "worked_example": {
                "market_value": example_ev,
                "method": "(market value x 10% assessment x equalization factor - $10,000 homeowner exemption) x total tax rate. Same method as the Clerk's sample bill.",
                "taxable_value_after_exemption": round(eav_after_ex, 2),
                "total_bill": round(example_bill, 2),
                "split": {k: round(v, 2) for k, v in example_split.items()},
                "caveat": "Illustration only. Real bills depend on the home's assessed value, exemptions, and any special districts (mosquito, SSAs, etc.). This example uses the general composite rate, not a sample of real homes.",
            },
            "caveats": [
                "Share of the bill = agency tax rate divided by total rate. Typical Chicago bill excludes special service areas and other special districts (Clerk's 'typical taxpayer').",
                "The Clerk lists the School Building and Improvement Fund as a City of Chicago levy (and the Clerk's own 'City of Chicago' extension total of $1.95B includes it plus the Library Fund). We show it on its own line so the City operating share is not overstated. The City's pension and debt levies are inside the corporate rate. Budget Overview p.59 says the City's portion is about one-fifth of the bill.",
                "Property tax is only part of City revenue. See data/context_revenue_2026.json.",
            ],
        },
        "treasurer_median_bill_tax_year_2024": {
            "chicago_median_residential_bill": 4457,
            "increase_pct": 16.7,
            "source_url": "https://www.cookcountytreasurer.com/pdfs/taxbillanalysisandstatistics/taxyear2024analysisenglishversion.pdf",
            "note": "Cook County Treasurer tax bill analysis, tax year 2024. A median is the bill in the middle, so half of homes pay more.",
        },
    }
    write_json("context_resident_2026.json", out)
    print("pop", pop, "households", households, "CPS", e26, e27)
    print("composite", total2025, "printed", composite25)
    for k, v in group_share.items():
        print("  %5.1f%%  %s" % (v * 100, k))
    print("example bill", round(example_bill, 2))


if __name__ == "__main__":
    main()
