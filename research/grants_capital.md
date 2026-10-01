# City grant funds, "Reserve Balance", and capital spending: project-level detail

Date of research: 2026-09-30. Everything here is rebuilt by `python3 scripts/grants_build_all.py` (about 15 seconds with the raw cache, about 5 minutes for a cold USASpending pull). Raw downloads live in `raw/grants/` (gitignored).

Outputs: `data/city_grants_2026.json`, `data/city_capital_2026.json`. Scripts: `scripts/grants_*.py`.

## Bottom line

| Question | Answer |
|---|---|
| Can the $1.91B "Reserve Balance" be split into named grants? | **Yes, 98.2% ($1.875B of $1.910B).** The ordinance already names the grant in the "appropriation authority" column, and the budget book's Summary G lists the same grants by department with a dollar amount. The other $35.2M is $31M Protecting CARE Fund (Finance General) and $4.2M airport O&M reserves. |
| Can it be split into named projects? | **Partly. $902M (47.3%) is attributable to named projects or awards**, as an upper bound (details below). The biggest blocks: O'Hare/Midway FAA grants ($269M via USASpending awards), CDOT transit/highway/state grants ($423M via the Mid-Year Grants 925 dataset), HUD HOME housing ($110M). |
| Is there a 2026-2030 CIP? | **Not published as of 2026-09-30.** The newest CIP on chicago.gov is 2025-2029 (349 pages, 1,479 projects). It is parsed here. Its "2026" column is a plan, not the 2026 ordinance. |
| Can capital be taken below $1M? | Yes in many places. 40% of CIP projects (585 of 1,479) are under $1M 5-year cost. Aldermanic Menu items (1,643, all under $413K) and TIF obligations (146 of 253 lines under $1M) are deep. Big projects (for example the State/Lake Loop Elevated station) stay over $1M but have named awards and phases. |

## 1. Grant funds ($3.839B): Summary G grant detail, fully parsed

Source: 2026 Budget Recommendations, Summary G "Estimate of Grant Revenue" and "Grant Detail": [PDF](https://occprodstoragev1.blob.core.usgovcloudapi.net/matterattachmentspublic/ddaf5dca-b40a-4ed4-a99a-7a5962987d2b.pdf). PDF page 613 (printed p. 604) is the fund summary. **PDF pages 614-624 (printed pp. 605-615) are the grant-by-grant detail**, with columns 2025 Grant, 2026 Anticipated Grant, Carryover, 2026 Total.

Parser: `scripts/grants_summary_g.py`. Result: **284 grant lines, 2026 Total sums to $3,839,125,000, which matches the printed "Total - All Programs" exactly.** Department subtotals match for every department (two departments only have a 2025 amount and no 2026, which is expected).

| Grant fund (Summary G p. 604) | 2026 appropriation |
|---|---|
| 925F Federal Grant Fund | $2,265,097,000 |
| 925S State Grant Fund | $732,282,000 |
| 925D Disaster Recovery (CDBG-DR) | $426,610,000 |
| 925L Local public and private | $132,778,000 |
| 925C COVID-19 | $132,028,000 |
| 925E Entitlement (CDBG) | $81,092,000 |
| GA00 ARPA LFRF | $34,181,000 |
| 0075 Indirect Cost Recovery | $21,519,000 |
| 925P Program Income | $13,538,000 |
| **Total** | **$3,839,125,000** |

**Key fact about the $3.839B:** it is $1,891M new anticipated awards plus **$1,948M carryover** of unspent multi-year awards (Summary G p. 604 says carryover is calculated at August 1 of the prior fiscal year). So the money is mostly "not yet spent from awards we already have".

Largest departments (Summary G, 2026 Total): CDOT $1,597.4M, Aviation $746.5M, DFSS $439.2M, Water Mgmt $339.7M, Public Health $229.9M, Housing $155.5M.

### Join to the ordinance (dataset 6694-f78c)
Join key: `fund_code + department_number + appropriation_authority` (the authority code in the ordinance equals the grant code in Summary G, e.g. `925F:2810`). Of 284 Summary G lines, 271 match the ordinance total exactly, 10 differ, 3 have no ordinance row under that key.

| Difference | $ |
|---|---|
| Ordinance GRANTS funds total | $3,869,858,000 |
| Summary G total | $3,839,125,000 |
| Gap | $30.7M |
| of which ordinance lines with no Summary G grant code (Congress Theater Section 108 loan $25.25M, DOH legal services filed under code 2581 vs 2580 in Summary G $2.093M, one 0075 grants management line $0.16M) | $27.5M |
| remaining: 13 Summary G lines that differ from or are missing in the ordinance (10 differ, 3 absent, mostly ARPA, HOME and Senior Center), ordinance higher by | $3.2M net |

The site should treat the ordinance as the budget of record and use Summary G for grant names and the new-versus-carryover split. `unmatched_ordinance_grant_lines` and per-line `match` flags in the JSON document every difference.

### HUD entitlement detail: 2026 Annual Action Plan
Source: [2026 Annual Action Plan](https://www.chicago.gov/content/dam/city/depts/obm/supp_info/Grants_Management/2026%20Annual%20Action%20Plan%20Final.pdf), AP-15 (PDF pp. 19-24) and AP-38 project summaries (PDF pp. 33-80). Parser: `scripts/grants_action_plan.py`.

| HUD program | 2026 total | Source |
|---|---|---|
| CDBG | $75,608,434 ($74,108,434 allocation + $1.5M program income) | AP-15 p. 20 |
| HOME | $17,634,420 | p. 21 |
| HOPWA | $13,684,685 | p. 22 |
| ESG | $6,547,594 | p. 23 |

The 31 AP-38 projects add up to exactly these four totals (CDBG $75.61M, HOME $17.63M, HOPWA $13.68M, ESG $6.55M), so the Action Plan fully explains the new-money side of Entitlement. Each project names a department and a description (for example "05U Housing Counseling (DOH) $2,405,000", "03T Homeless Programs (DFSS) $11,079,000", "Right to Counsel $2,093,000"). Most project descriptions say the money goes to delegate agencies, but the Action Plan does not list those agencies. Agency-level grants appear in the Contracts and Payments datasets.

## 2. The $1.91B "Reserve Balance": what it really is

Ordinance account `909A Reserve Balance` has **86 lines, $1,905.6M**, and two `9046 O&M Reserve` lines add $4.2M. All but the last $35.2M sit inside the grant funds (925F $1,336M, 925S $356M, 925C $120M, 925L $55M, 925E $6.6M, 925P $1.7M).

**Finding: Reserve Balance is the carryover.** For 62 of the 85 Summary G grants that have a reserve line, the reserve equals the Summary G "Carryover" column to the dollar. The rest differ because the ordinance reserve and the book's carryover were cut at slightly different dates, or the ordinance moved part of the carryover into salaries/contracts lines (for example Public Health ELC: $11.6M reserve vs $14.5M carryover). So "Reserve Balance" means "money from an award we already hold, not yet assigned to an account".

The top reserve lines, all named by the ordinance and Summary G:

| Reserve | Grant (Summary G p.) | Dept |
|---|---|---|
| $411.8M | FAA Airport Improvement Program, O'Hare (ALN 20.106), PDF p. 616 | Aviation |
| $362.7M | FTA Federal Transit Formula Grants (20.507), p. 615 | CDOT |
| $162.0M | FHWA Highway Planning and Construction (20.205), p. 615 | CDOT |
| $124.1M | IDOT Highway Planning and Construction (state), p. 615 | CDOT |
| $123.9M | FAA Airport Improvement Program, Midway (20.106), p. 616 | Aviation |
| $117.9M | IDOT Rebuild Illinois, p. 615 | CDOT |
| $48.5M + $29.0M + $1.7M | HUD HOME (14.239) | Housing |
| $43.2M | EPA Superfund, Anadarko Streeterville Removal (66.802), p. 624 | Environment |
| $39.3M | HUD HOME (ARP) | Family and Support Services |
| $31.0M | Protecting CARE Fund (not a grant, Finance General) | Finance General |
| $31.0M + $22.8M | IDOT Aviation Fuel Tax, O'Hare and Midway | Aviation |

Everything in `data/city_grants_2026.json` under `reserve_attribution.lines` (88 lines, each with department, authority, grant name, Summary G page, method, named items).

## 3. Project-level attribution of the reserve (quantified)

Method (script `scripts/grants_reserve_attribution.py`): attributable = **min(reserve line, sum of UNSPENT budget of matched named projects)**. Unspent = budget minus expended to date (encumbered amounts count as unspent). No pro-rata splitting. These are caps, not exact splits, because Summary G is an Aug 2025 snapshot and the project list is a May 2026 snapshot.

| Basis | Source | Attributable |
|---|---|---|
| FAA O'Hare and Midway AIP | USASpending.gov awards to City of Chicago, FAA, place of performance zip 60666 (O'Hare) or 60638 (Midway), award period ending 2026 or later, obligated minus outlaid | **$269.4M** (O'Hare $218.3M over 26 awards, Midway $51.2M over 12 awards) |
| CDOT lines (FTA, FHWA, IDOT, Rebuild Illinois, INFRA, sister agency) | [Mid-Year Grants 925](https://data.cityofchicago.org/resource/iyu8-jkf8), snapshot 2026-05-31, matched by fund code or ALN | **$422.9M** |
| Other departments (HOME, CDC, UASI, COPS, etc.) | Mid-Year Grants 925 matched by department plus ALN, de-duplicated across lines | **$210.1M** |
| **Total attributable to named projects/awards** | | **$902.4M of $1,909.8M (47.3%)** |

What this gives the site, concretely:
- **Aviation O'Hare $411.8M reserve:** 26 named FAA awards, each with an award number, purpose text ("CONSTRUCT TAXIWAY ... 2,627 FOOT OF NEW TAXIWAY T AND R"), amount, period and a USASpending link. FAA award text gives purpose only, so the CIP (section 5) supplies the project name. The O'Hare/Midway FAA grants are **not** in the Mid-Year Grants 925 dataset at all (Aviation has zero rows there), so USASpending is the only public project-level source.
- **CDOT $362.7M FTA reserve:** only $101.5M is matched to public project records, and it is essentially one project, the **State/Lake Loop Elevated Station** ($164.4M budget plus a $15M FFY2025 Carbon Reduction piece, plus a $1.5M wayfinding plan). It is one named item well over $1M. The other $261M of the FTA reserve has no public project record and stays at grant level.
- **CDOT FHWA $162.0M reserve:** 38 named projects (Columbus Ave BRC grade separation, Milwaukee Ave Belmont to Logan, Montrose Harbor underpasses, Canal St viaduct, arterial resurfacing packages 93 to 98, and so on), with the unspent amount of each.
- **CDOT IDOT $124.1M and Rebuild Illinois $117.9M:** 42 and 13 named projects (OPC mobility improvements for South Lakefront $129.8M total, Chicago Ave bridge over the river $49M, Lake Shore Drive Grand to Hollywood, 95th St bascule bridge).

Of the 200 distinct named mid-year projects found, 134 have unspent budget under $1M, so those branches of the tree reach the bottom.

**Not attributable with public data** (the remaining $1.007B): IDOT Aviation Fuel Tax $53.8M (no project list published), EPA Superfund Streeterville $43.2M (single remediation project, named at grant level), Protecting CARE $31M, most of the FTA formula reserve, and many small lines where Summary G itself is the finest public level. Nearly all of these are single named grants, so they can be labelled honestly ("one federal grant, ALN 66.802, for Streeterville cleanup") even though no deeper breakdown exists.

## 4. Other capital funding sources checked

### Mid-Year Grants 925 dataset (`iyu8-jkf8`)
Project-level grant ledger (budget, expended, encumbered, funds available, agency, ALN, start/end dates) published with the OBM mid-year report. The 2026-05-31 snapshot has 509 records, $4.08B budget total. Department coverage differs from Summary G: it includes big ARPA ($1.17B in the Mayor's office, mostly already spent) and omits Aviation and Water entirely. A 2025-06-01 snapshot of 280 older records also exists in the same dataset id. Use `data_extract_as_of_date` to separate them.

### USASpending.gov (federal awards)
`scripts/grants_usaspending.py` pulls assistance awards with recipient names containing "City of Chicago" (FY2021 to FY2026, 265 award records, $5.18B including Board of Education records that must be excluded for the City). Examples: HUD CDBG-DR $426.6M (B-25-MU-17-0001, PDF match to Disaster Recovery fund $426.6M exactly), CDBG entitlement awards $74M to $76M a year, Head Start awards, CDC awards to CDPH, 48 FAA awards. The CDBG-DR $426,608,000 award equals the 925D appropriation of $426,610,000 within $2K, which is a strong confirmation of the Disaster Recovery fund.

### Illinois GATA / Comptroller
Not pulled. IDOT grants are visible indirectly through the CDOT lines above (fund codes F0L98, F0W32, F0W23, F0W24). The state-side public sources (GATA portal, Comptroller grant data) require interactive search and are a follow-up if the site wants the state's own view of the same grants.

### TIF
Dataset `fpsv-qjg3` (TIF Projections 2025-2034, published 2025-10-15, [PDF](https://www.chicago.gov/content/dam/city/depts/dcd/tif/projections/projection-report-1025.pdf)) lists each obligation by district. **253 named lines project $828.9M of TIF spending in 2026, and 146 of those lines are under $1M** (e.g. "CDOT - Bridge - Lake St - reconstruction", "DPD - RDA - 135 S. LaSalle"). TIF money is not appropriated by project in the ordinance (only TIF Administration fund 0B21, $23.4M, is), so this is a separate branch for the site, not a split of the ordinance. Related: `umwj-yc4m` (TIF annual report expenditures by category per district, 2017-2025) and `mex4-ppfc` (762 TIF-funded RDA/IGA projects with approved amounts).

## 5. Capital Improvement Program

Source: [City of Chicago 2025-2029 CIP](https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP/City%20of%20Chicago%202025-2029%20CIP.pdf), the latest on OBM's [Capital Publications page](https://www.chicago.gov/city/en/depts/obm/provdrs/budget/svcs/CapitalPublications.html) (checked 2026-09-30, no 2026-2030 edition). Parser: `scripts/grants_capital_cip.py`.

- **1,479 projects** with CIP project ID, name, design/construction years, each fund source with Total, Prior Years, 2025 and 2025-2029 amounts, and location. PDF project pages are pp. 30-348, interleaved with fund summary pages (pp. 28-29, 58-61, 116-120, 177, 199, 253-257, 281, 297-300, 340-347).
- Five-year total of all projects: **$18.10B**. 894 projects are $1M or more over five years, 585 are under $1M.
- **Check:** for 38 of the 48 subprograms the sum of project amounts equals the printed fund summary subtotal exactly, both the 2025 column and the five-year column. The other 10 (Aldermanic Menu years, Fleet small subprograms, New Meters, Information Technology, Alley Construction) have no parsed printed subtotal to compare against. None disagree.
- **Per-year limitation:** project pages only give the 2025 and 2025-2029 columns. A single 2026 number per project does not exist in this edition. Yearly 2026-2029 amounts are available per fund source in `fund_summary_rows` (627 rows). For projects the JSON gives `remaining_2026_2029` (five-year minus 2025).
- CIP 2026 column by program (plan): Aviation $1,445M, Water $697M, Transportation $607M, Sewer $340M, Neighborhood Infrastructure $284M, Economic Development $162M, Fleet $99M, Information Technology $68M, Lakefront $56M, CitySpace $54M, Municipal Facilities $54M. Total $3.93B, of which bond-funded $2.28B, federal $421M, TIF $261M, state IEPA loans $191M, WIFIA $159M, state $128M, city $86M.

### How CIP maps to the ordinance
The ordinance does **not** appropriate most capital by project:
- Ordinance "Construction" lines (account 0540 and "Capital Construction") total $1.03B, of which $0.97B is in grant funds (CDOT federal $464M, CDOT state $151M, CDOT CDBG-DR $67M, Water CDBG-DR $283M, Water CDBG $7M), $54M is Water/Sewer Fund "For Capital Construction" in Finance General, and $5M is Water Management "Maintenance and Construction".
- Airport capital (O'Hare Airport Fund and revenue bonds), water and sewer capital funded by revenue bonds and IEPA loans, and G.O. bond projects are authorized through bond ordinances and the CIP, not line by line in the annual appropriation. The CIP's $3.9B 2026 figure therefore cannot be reconciled to the ordinance. The site should show the CIP as its own "Capital plan" branch, labelled as a plan, and link the grant-funded parts to their grant lines.

### Aldermanic Menu (deepest capital data)
Source: [OBM Aldermanic Menu Q2 2026](https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CIP_Archive/Aldermanic%20Menu/Q2_2026_Ald_Menu_Report.pdf). Parser: `scripts/grants_aldermanic_menu.py`. 50 wards x $1.5M = $75M of 2026 menu budget (a $108M package in the CIP including ADA ramps and supplements). **1,643 line items totaling $54,553,293 committed, and for all 50 wards the items sum exactly to the printed ward total.** Largest item $412,752, so every item is under $1M. Packages: Street Resurfacing $28.0M, Sidewalk $7.5M, Alley Resurfacing $6.9M, Curb and Gutter $2.3M, and more, each with street locations.

### Federal and state share
CIP 2026 federal $421M and state $128M are separate from the ordinance reserve numbers (the ordinance carries multi-year carryover of $1.9B). Do not add the two.

## 6. Recommendations for the site tree

1. **Grants branch:** Fund type Grants > grant fund (925F, 925S, ...) > department > named grant (from Summary G, with "new award vs carryover" labelled) > account lines. All 284 grants are named. Label: "Estimated. Spending is allowed only if the award is received."
2. **Reserve Balance node:** show it as "Money from awards already received, not yet assigned" and split by grant (98% named). For the 47% with project data, add a level of named projects or FAA awards showing budget, spent so far, and unspent. Where only the grant is known, add the standard "Why can't I go deeper?" note.
3. **Capital branch (separate, plan):** Program > subprogram > CIP project > fund source, with the Aldermanic Menu, TIF obligations and Fleet as the deepest. Clearly label as "plan, 2025-2029 edition".
4. **Entitlement:** CDBG/HOME/ESG/HOPWA by Action Plan project (31 projects), then delegate agencies from the Contracts dataset.

## 7. Limits and follow-ups

- No 2026-2030 CIP exists yet. When OBM publishes it (the 2025-2029 edition came out in 2025), rerun `grants_capital_cip.py` with the new URL. The parser reads the same layout.
- Summary G amounts are authorization to spend up to the award, not revenue. Mid-Year Grants 925 is as of 2026-05-31.
- The attribution caps are upper bounds. They treat unspent budget in the project ledger as the thing the reserve will fund, which is correct in spirit (carryover is unspent award money) but timing differs by 9 months.
- USASpending FAA award text names the purpose, not the CIP project. A crosswalk to CIP project IDs (O'Hare 20 CIP projects, 5-year $676M federal) is a possible next step.
- Illinois GATA and Comptroller grant data, CDBG sub-recipient lists, and Water Department CDBG-DR project lists (stormwater, $283M) were not pulled. The CDBG-DR plan PDFs on chicago.gov name the sewer and alley projects and are the next best source for the $283M Water and $67M CDOT Disaster Recovery lines (all of those are already full-year appropriations, not reserve).
