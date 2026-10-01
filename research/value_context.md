# "Is this good value?" context data for the budget explorer

Gap: value context to attach to budget nodes. Everything here is public, has a URL, and is produced by a script in `scripts/context_*.py` that writes `data/context_*.json`. Raw downloads live in `raw/context/` (gitignored). Reproduce everything with:

```
python3 scripts/context_revenue.py        # where the money comes from
python3 scripts/context_resident.py       # per resident / per student, property tax bill split
python3 scripts/context_service_metrics.py  # 311, potholes, inspections, permits (slow: about 2 minutes)
python3 scripts/context_peers.py          # NYC, LA, Houston, Philadelphia per resident
python3 scripts/context_settlements.py    # police misconduct payouts, 2019 to 2025
python3 scripts/context_oversight.py      # 32 findings, every quote machine-checked
python3 scripts/context_dept_map.py       # the 40-department map (run last)
```

Needs only Python 3 and `pypdf`. Scripts fail loudly if a pattern or quote is not found in the source.

## Read this first: what the data can and cannot tell a resident

1. **Almost nothing here measures whether a department got good results.** Chicago publishes lots of "how much did it spend" and "how many requests came in", very little "did it work". Of the 40 departments, **4 have several independent measures, 19 have partial ones, 17 have nothing beyond the department's own description.** "Nothing found" is not "performs well". The site should say so on those nodes.
2. **The measures we have are mostly about speed and measurement, not outcomes.** The biggest recurring Inspector General finding is that departments cannot show whether their programs work (Fire response times, rat control, HR assistance program, mental health clinic data, vendor payment timeliness).
3. **Self-reported results are not audited.** The 2026 Budget Overview has a "2025 KEY RESULTS" block for 38 of 40 departments, written by the departments themselves.
4. **Do not total peer-city numbers.** Compare one function at a time (police vs police).

## 1. Where the money comes from (revenue)

Source: 2026 Budget Ordinance, Revenue, dataset [`nydj-5nax`](https://data.cityofchicago.org/d/nydj-5nax), found with the Socrata catalog API (`https://api.us.socrata.com/api/catalog/v1?domains=data.cityofchicago.org&q=revenue`). 156 rows. Output: `data/context_revenue_2026.json`.

**Scope: local funds only, $14.62B.** The $3.87B of grants (federal, state) is not in this dataset. The local revenue estimate is $175M below the local appropriations ($14.80B). Do not force them to match. Also, the Corporate Fund alone is $6.25B.

| Source (all local funds) | $ | Notes |
|---|---|---|
| Other City taxes (utility, hotel, parking, amusement, transportation, real estate transfer, and more) | $3.45B | Includes the $1.23B personal property lease tax ("tax on big tech") |
| Airport fees and airline charges | $2.49B | O'Hare $2.06B, Midway $0.43B. Paid by airlines and passengers, not by residents' taxes |
| Property tax (City's share, net of abatement) | $1.86B | About $683 per resident. Goes to pensions ($1.41B), debt ($0.31B) and the library ($0.13B), not to day-to-day operations |
| Water and sewer bills | $1.50B | |
| Fines, fees, permits, licenses, charges | $1.45B | Fines alone $0.48B in the Corporate Fund |
| Moved between city funds (pension allocations, reimbursements) | $1.71B | **Same money counted twice.** The roughly $1.8B double counting in `research/finance_general.md` is a different measurement on the spending side, so the two are close but not identical |
| State money (income tax share, replacement tax) | $0.75B | |
| City's share of sales tax | $0.59B | |
| Other dedicated funds | $0.50B | |
| Borrowing and one-time transfers | $0.32B | |

So **about $12.9B of the $14.6B is "real" new money**, once you take out transfers between city funds.

Property tax levy detail (from the same dataset, adds to $1.858B): Police pension $814M, Fire pension $367M, Municipal pension $177M, Laborers pension $55M, debt $315M, library $131M. The Budget Overview (p.59) says the $1.8B base levy "will help fund $2.7 billion in pension payments", so property tax covers only part of pensions.

Corporate Fund top sources: personal property lease tax 19.8%, state income tax 8.7%, sales tax securitization residual 7.9%, fines 7.7%, safety charges 5.7%, amusement tax 4.9%.

## 2. Property tax bill: who gets what

Source: Cook County Clerk, [2025 Tax Rate Report](https://www.cookcountyclerkil.gov/publication/2025-tax-rate-report) (tax year 2025, billed in 2026, newest). Output: `data/context_resident_2026.json`. The script checks that the agency rates add to the Clerk's printed total of 6.853152%.

| Agency | Rate | **Share of a typical Chicago bill** | On a $250,000 home* |
|---|---|---|---|
| Chicago Public Schools (Board of Education) | 3.8330% | **55.9%** | $2,520 |
| City of Chicago (corporate levy plus library) | 1.6666% | **24.3%** | $1,096 |
| City of Chicago, School Building and Improvement Fund | 0.1313% | 1.9% | $86 |
| Cook County and Forest Preserve | 0.4230% | 6.2% | $278 |
| Chicago Park District | 0.3055% | 4.5% | $201 |
| Water Reclamation District | 0.3366% | 4.9% | $221 |
| City Colleges | 0.1573% | 2.3% | $103 |

\*Illustration using the Clerk's own method: ($250,000 x 10% x equalization factor 3.0300 - $10,000 homeowner exemption) x 6.853152% = **$4,506**. Real bills depend on the home's assessed value, exemptions and special districts. The Cook County Treasurer reports the median Chicago residential bill for tax year 2024 was $4,457 (+16.7%) ([source](https://www.cookcountytreasurer.com/pdfs/taxbillanalysisandstatistics/taxyear2024analysisenglishversion.pdf)).

**Two ways to say "share", which differ.** Share of the tax *rate* (a typical home): CPS 55.9%, City about 26%. Share of the *dollars billed in Chicago* ($9.07B): CPS $4.16B (45.8%), City $1.95B (21.5%), County $0.82B (9.0%). The dollar shares are lower because tax on property inside TIF districts goes to the TIF fund. A rough check using the tax year 2024 TIF total ($1.59B, WTTW, not the same year) gives CPS about 55.6%, close to the 55.9%. Use the rate share for "what does my bill pay for". The Budget Overview (p.59) says the City's portion "represents approximately one-fifth of the total property tax bill", which is close to the 21.5% dollar share and lower than the 26% rate share (the City's own figure probably excludes the School Building fund and TIF effects, but the book does not say).

The City of Chicago's property tax and the City's budget are different sizes: the Clerk's $1.95B City extension (includes the Library and School Building funds, before collection losses) is about 10% of the $18.7B budget. The revenue dataset shows $1.86B for the City levy net of abatement, a slightly different measure.

## 3. Per resident and per student

Source: ACS 2024 1-year, Chicago city (geoid 16000US1714000), via Census Reporter because the Census API now requires a key. CPS 20th day enrollment from CPS workbooks.

- **Residents: 2,721,326** (margin of error 60). Households 1,172,455. Median household income $80,613. Median home value $341,200.
- **CPS enrollment: 316,224 (SY2025-26, September 2025)** and **304,687 (SY2026-27)**, a 3.65% drop. CPS's own stats page lists the new year at 304,687 (https://www.cps.edu/about/stats-facts/). Includes charter and contract schools. Use 316,224 for the FY2026 budget (July 2025 to June 2026).

Worked examples (all computed from the data files): City gross appropriations $18.67B is **$6,860 per resident** ($15,923 per household). The $16.6B net figure is $6,100 per resident. CPS total budget $10.25B is **$32,414 per enrolled student**, CPS operating budget $8.66B is $27,386 per student (CPS's stats page lists 304,687 students for the current school year, SY2026-27, which would give $28,423). Park District $637.6M is $234 per resident.

**Warning on per-resident numbers:** a department's cost per resident treats everyone as using the service equally. Aviation ($612 per resident) is funded by the O'Hare and Midway airport funds for 55% of its $1.67B (airline and passenger charges) and by federal and state grants for 45% (appropriations dataset), so it is not mainly Chicagoans' taxes. Finance General ($3,010 per resident) is pensions and debt, not a service. Per resident is a size measure, not a price tag.

## 4. Service performance (what we can actually check)

Source: Chicago open data, calendar 2025. Output: `data/context_service_metrics_2025.json`. Datasets: 311 Service Requests [`v6vf-nfxy`](https://data.cityofchicago.org/d/v6vf-nfxy), Potholes Patched [`wqdh-9gek`](https://data.cityofchicago.org/d/wqdh-9gek), Food Inspections [`4ijn-s7e5`](https://data.cityofchicago.org/d/4ijn-s7e5), Building Permits [`ydr8-5enu`](https://data.cityofchicago.org/d/ydr8-5enu).

Completed 311 requests, share closed within 5 and 7 days (the City's own clock, "Completed" status only):

| Request type | Completed in 2025 | Within 5 days | Within 7 days | Average days |
|---|---|---|---|---|
| Graffiti removal | 89,034 | 99.4% | 99.7% | 1.1 |
| Water in basement | 17,739 | 98.3% | 98.6% | 1.3 |
| Tree emergency | 25,330 | 91.0% | 94.6% | 2.9 |
| Traffic signal out | 23,751 | 85.1% | 86.9% | 8.1 |
| Street light out | 31,368 | 80.6% | 86.2% | 7.6 |
| Rat baiting complaint | 43,053 | 66.8% | 79.7% | 4.1 |
| Pothole in street | 28,230 | 46.2% | 53.3% | 26.5 |
| Abandoned vehicle | 52,601 | 36.0% | 42.0% | 19.7 |
| Garbage cart maintenance | 47,681 | 17.1% | 22.4% | 24.2 |
| Building violation | 18,477 | 27.1% | 31.0% | 46.6 |
| Alley pothole | 5,556 | 22.3% | 28.2% | 52.6 |
| Blue recycling cart | 20,726 | 2.9% | 4.1% | 34.6 |

- **Checking the department's own claims:** the Budget Overview says graffiti is removed "within five days" (99.4% in 311 data, so the claim holds) and rodent baiting is "maintaining a five-day response time" (66.8% within 5 days, 4.1 day average, so the claim holds only on average).
- **Potholes:** 25,633 blocks patched and 248,541 potholes filled in 2025, down from 39,649 blocks and 489,943 potholes in 2022. The average time from request to patch in 2025 was 35.2 days. Fewer potholes patched is not clearly worse (it could mean fewer potholes) and we cannot tell which.
- **Food inspections:** 19,205 in 2025 (19,052 in 2019). **Building permits issued:** 32,032 in 2025 (48,544 in 2019).
- **Volume:** Streets and Sanitation 483,252 requests, CDOT 144,702, Water 77,565, Animal Care 38,736, Buildings 37,578. Aviation's 364,926 requests are all aircraft noise complaints and Finance's 20,377 are all parking ticket reviews. They are not service speed measures.
- **Animal Care:** of 11,694 stray animal complaints, 9,800 were marked Canceled and 1,870 Completed. We do not know why.

## 5. Peer cities

Source: U.S. Census Bureau, 2024 Annual Survey of State and Local Government Finances, Individual Unit Files ([zip](https://www2.census.gov/programs-surveys/gov-finances/tables/2024/2024_Individual_Unit_Files.zip)). Same definitions for every city, which a budget book cannot give. Output: `data/context_peers_2024.json`. Dollars per resident, current operation, fiscal year ending in 2024.

| Function | Chicago | Peer average (NYC, LA, Houston, Philadelphia) | Chicago vs peers | Chicago rank of 5 (1 = highest) |
|---|---|---|---|---|
| Police | $840 | $649 | +29% | 2 |
| Fire | $262 | $330 | -21% | 3 |
| Garbage and solid waste | $69 | $152 | -55% | 4 |
| Streets and highways | $158 | $136 | +16% | 3 |
| Water utility | $155 | $135 | +15% | 2 |
| Libraries | $45 | $42 | +7% | 2 |
| Parks and recreation | $22 | $93 | -76% | 5 |
| Sewerage | $37 | $145 | -75% | 5 |
| Public health | $115 | $613 | -81% | 4 |
| Housing and community development | $4 | $429 | -99% | 5 |
| Protective inspection | $16 | $52 | -69% | 5 |

**Why not to over-read this.** (a) City government only: NYC's city runs schools, hospitals and welfare, Chicago's does not, so the big gaps in health and housing are mostly who runs what. (b) Chicago parks are the Park District, a separate government, so the $22 for parks is just the City's small part, and likewise CPS for schools. (c) We did NOT verify whether police and fire pensions sit inside each city's police and fire lines. Chicago books them in Finance General. (d) Census uses a population of 2,665,039 for Chicago, below the ACS 2.72M, so Chicago per resident would be about 2% lower with ACS. (e) Peer-city numbers are 2024, not FY2026. (f) The "Financial administration" line is $1,675 per resident for Chicago versus $546 for peers, an outlier we think is Finance General bookkeeping but have not confirmed, so we do not compare it.

The best matches are police, fire, libraries, streets and water. Treat the rest as context only.

## 6. Police misconduct settlements

Source: City Department of Law, annual CPD Litigation Reports required by the Consent Decree ([index](https://www.chicago.gov/city/en/depts/dol/supp_info/CPDAnnLitReports.html)). Output: `data/context_settlements_2019_2025.json`. Each total is found in the PDF text by a pattern, with the matching sentence saved.

| Year | Total payouts | Outside counsel fees |
|---|---|---|
| 2019 | $46.8M | $25.5M |
| 2020 | $40.5M | n/a |
| 2021 | $122.5M | $24.1M |
| 2022 | $86.3M | n/a |
| 2023 | $81.4M | $28.6M |
| 2024 | $84.0M | $34.8M |
| 2025 | **$259.0M** ($360.3M including the Watts settlements) | $36.1M |

- 2025: $193.3M (74.7%) was wrongful convictions, $54.4M vehicle pursuits. The Watts settlements ($101.3M) were approved in 2025 but paid mostly in 2026. The report text says City Council approved settling 176 Watts lawsuits while its footnote counts 184 cases, so the case count is uncertain (the dollar figure is stated once).
- **That is $95 per resident in 2025 ($132 including Watts), or $221 per household,** compared with the 2026 budget line for police judgments of $82.6M and Fire $12.0M (appropriations dataset). Finance General also holds a $48.0M citywide judgments line.
- **What this does not cover:** only cases naming CPD conduct (civil rights and police pursuits) that closed that year. Wrongful convictions are paid decades after the event. It is not every City payout.
- **Unresolved:** WTTW says taxpayers paid $472.4M in 2021 to 2025. The sum of the Law Department's single-year totals is $633.2M. We tried two reconciliations (settlements only, restated 2021) and neither matches. **Do not publish a 5-year total until this is resolved.** Single-year totals are each stated in the Law Department reports. The Law Department also restated 2021 upward to $126.1M in its 2022 report.
- WTTW reports CPD spent only $131.1M on police misconduct suits according to the City's 2025 annual financial report, leaving about $127.8M unexplained. We did not check the ACFR. Treat as "reported by WTTW".

## 7. Outside reviews (Inspector General, COFA, Civic Federation)

Output: `data/context_oversight_findings.json`, 32 findings (15 concern, 5 mixed, 1 positive, 11 context). **Every quote is verified as a substring of the downloaded source.** `verified=true` means the quote is in the source, not that the claim is true. Findings from the Civic Federation and EY are their estimates, flagged `is_estimate_not_audited`.

Highlights:

| Department | Finding | Source |
|---|---|---|
| Fire | OIG: CFD has not implemented corrective actions on response-time measurement. CFD blames budget office denial of analyst staff. | [OIG 2025](https://igchicago.org/publications/second-follow-up-audit-cfd-response-times/) |
| Fire | Only 16.8% of buildings in the inspection database were inspected within 12 months. | [OIG 2025](https://igchicago.org/publications/audit-cfd-fpb/) |
| Fire | COFA: cutting engine and truck crews from 5 to 4 could save up to $69.43M a year (needs union agreement). 5,141 positions, 80 ambulances for 2.7M people, $90.9M overtime in 2025. | [COFA](https://www.chicago.gov/content/dam/city/depts/COFA/RevenueResources/COFA_Savings%20Resource_CFD%20Manning_FY26%20Mid%20Year%20Update2.pdf) |
| Police | CPD reports 71% homicide clearance, 416 homicides. The Inspector General calls clearance "a tricky metric". | [CPD](https://www.chicagopolice.org/wp-content/uploads/2025-in-Review.pdf) |
| Police | COFA: overtime budgeted $200M for 2026, actual typically about 2x budget. | [COFA](https://www.chicago.gov/content/dam/city/depts/COFA/ProposedBudget/Presentations_ProposedBudget/COFA_Budget%20Recommendation%20Summary_Final.pdf) |
| Streets and Sanitation | OIG: rat control is complaint-driven and does not measure whether it works ($12.5M budget). | [OIG 2026](https://igchicago.org/publications/dss-rat-abatement-audit/) |
| Streets and Sanitation | OIG: auto pound records unreliable for 15% of a sample. Over $223M in contracts to the towing contractor since 1997. | [OIG 2026](https://igchicago.org/publications/dss-auto-pounds-audit/) |
| Finance | OIG: about $8.1B is owed to the City and no one tracks all of it (a floor). City cannot tell whether it pays vendors in 30 days. | [OIG 2026](https://igchicago.org/publications/dof-debt-management-audit/) |
| Water | OIG: meters are accurate (2,200 tests), but billing and service-order processes can cause or worsen spikes. | [OIG 2026](https://igchicago.org/publications/water-billing-audit/) |
| Family Services | OIG: 94.1% of encampment residents at a housing event entered stable housing (78.6% still housed at check). The one clearly good outcome. | [OIG 2023](https://igchicago.org/publications/audit-dfss-encampments-outreach/) |
| Fleet and Facility | EY via Civic Federation: average City vehicle driven 7,000 miles a year, one vehicle per 17 employees, $16M to $31M possible savings. | [Civic Federation](https://www.civicfed.org/blog/which-cuts-didnt-make-cut-efficiency-opportunities-chicagos-fy2026-budget) |
| Finance General | EY via Civic Federation: $80M to $103M a year possible from aligning benefits with peers. | same |

Civic Federation on the adopted budget: "Uses debt, rather than operating revenue, to cover the cost of legal police settlements and retroactive salaries for firefighters." This is an opinion from a civic watchdog.

**No dollars-waste total from the Inspector General.** I searched for dollar figures in OIG's Q4 2025 quarterly report and in the full text of six audits (debt, payment timeliness, auto pounds, rats, 311, water billing), and read the executive summaries of about eight more (CDPH, DFSS x2, Buildings, HR, workers' comp, COFA, CFD). That is roughly 15 of the 17 audits OIG published since 2022. I did not read the TIF Sunshine audit (2022) or the original construction debris recycling audit (2023). The audits describe process weaknesses and rarely give a dollar amount of waste. I did not find an "OIG identified $X waste" figure and did not invent one. The dollar figures we do have (above) are either amounts at risk or someone else's estimates.

**Not verified:** a CWB Chicago article says only 140 of CPD's 296 cleared homicides were cleared by charging someone. The page blocked our script (HTTP 403), so this is a search snippet only and is listed under `unverified_leads`.

## 8. Mapping to the 40 departments

Output: `data/context_dept_map.json`. One entry per department (names exactly as in dataset 6694-f78c) with budget, per resident, staff, 311, peers, settlements, findings, the Budget Overview self-reported results and a plain-language note on what a resident can check. "have" means several independent measures, "partial" means some, "none" means nothing beyond the department's own description.

| # | Department | 2026 budget | Per resident | Staff (FTE) | Coverage | Main things we have |
|---|---|---|---|---|---|---|
| 1 | Office of the Mayor | $16.4M | $6 | 112 | none | self-reported |
| 3 | Office of Inspector General | $14.3M | $5 | 118 | partial | self-reported |
| 5 | Office of Budget and Management | $38.6M | $14 | 56 | none | self-reported |
| 6 | Department of Technology and Innovation | $76.4M | $28 | 144 | none | self-reported |
| 15 | City Council | $37.8M | $14 | 265 | none | 1 finding |
| 21 | Department of Housing | $173.3M | $64 | 122 | partial | 311, peer, self-reported |
| 23 | Department of Cultural Affairs and Special Events | $62.0M | $23 | 80 | none | self-reported |
| 25 | Office of City Clerk | $15.2M | $6 | 93 | partial | 311, self-reported |
| 27 | Department of Finance | $127.8M | $47 | 654 | partial | 311, 4 findings, self-reported |
| 28 | City Treasurer's Office | $6.5M | $2 | 40 | none | self-reported |
| 30 | Department of Administrative Hearings | $8.4M | $3 | 39 | none | self-reported |
| 31 | Department of Law | $48.0M | $18 | 418 | partial | settlements, self-reported |
| 33 | Department of Human Resources | $13.0M | $5 | 119 | partial | 2 findings, self-reported |
| 35 | Department of Procurement Services | $13.9M | $5 | 126 | partial | 1 finding, self-reported |
| 38 | Department of Fleet and Facility Management | $503.5M | $185 | 1,031 | partial | 2 findings, self-reported |
| 39 | Board of Election Commissioners | $27.9M | $10 | 122 | none | self-reported |
| 41 | Chicago Department of Public Health | $335.0M | $123 | 764 | partial | 311, peer, 1 finding, food inspections, self-reported |
| 45 | Chicago Commission on Human Relations | $2.8M | $1 | 20 | none | self-reported |
| 48 | Mayor's Office for People with Disabilities | $9.7M | $4 | 40 | none | self-reported |
| 50 | Department of Family and Support Services | $653.4M | $240 | 433 | partial | 2 findings, self-reported |
| 51 | Office of Public Safety Administration | $135.6M | $50 | 373 | none | self-reported |
| 54 | Department of Planning and Development | $146.5M | $54 | 194 | partial | self-reported |
| 55 | Chicago Police Board | $0.5M | $0 | 2 | none | self-reported |
| 57 | Chicago Police Department | $2.1B | $775 | 13,792 | have | peer, settlements, 7 findings, self-reported |
| 58 | Office of Emergency Management and Communications | $99.9M | $37 | 970 | partial | 2 findings, self-reported |
| 59 | Chicago Fire Department | $901.7M | $331 | 5,141 | partial | 311, peer, settlements, 6 findings, self-reported |
| 60 | Civilian Office of Police Accountability | $15.8M | $6 | 150 | partial | 1 finding, self-reported |
| 62 | Community Commission for Public Safety and Accountability | $4.0M | $1 | 29 | none | self-reported |
| 67 | Department of Buildings | $39.4M | $14 | 279 | have | 311, peer, 1 finding, permits, self-reported |
| 70 | Department of Business Affairs and Consumer Protection | $36.8M | $14 | 213 | partial | 311, self-reported |
| 72 | Department of Environment | $52.5M | $19 | 79 | none | self-reported |
| 73 | Chicago Animal Care and Control | $8.2M | $3 | 79 | partial | 311, self-reported |
| 77 | License Appeal Commission | $0.2M | $0 | 1 | none | self-reported |
| 78 | Board of Ethics | $0.9M | $0 | 8 | none | self-reported |
| 81 | Department of Streets and Sanitation | $349.9M | $129 | 2,204 | have | 311, peer, 5 findings, self-reported |
| 84 | Chicago Department of Transportation | $1.8B | $675 | 1,481 | have | 311, potholes, peer, self-reported |
| 85 | Chicago Department of Aviation | $1.7B | $612 | 2,445 | none | noise complaints only, self-reported |
| 88 | Department of Water Management | $772.7M | $284 | 2,492 | partial | 311, peer, 2 findings, self-reported |
| 91 | Chicago Public Library | $116.0M | $43 | 1,033 | partial | peer, self-reported |
| 99 | Finance General | $8.2B | $3,010 | n/a | partial | settlements line, 2 findings |

Notes on this table:
- "2026 budget" is the dataset's total including grants. It sums to $18.67B across 40 departments (the gross figure before removing double counting).
- "Staff (FTE)" comes from COFA's FY2026 Budget Recommendations Summary ([PDF](https://www.chicago.gov/content/dam/city/depts/COFA/ProposedBudget/Presentations_ProposedBudget/COFA_Budget%20Recommendation%20Summary_Final.pdf)). The positions dataset undercounts because it also holds hourly and monthly rows, so use COFA's number.
- City Council and Finance General have no Budget Overview "key results" block. Many departments' "self-reported" text has odd spacing from PDF extraction, so quote it from the PDF page printed in `data/context_dept_map.json` rather than copying the text.
- 311 data appears for 12 owner departments. Fire only has 282 requests, so 311 says almost nothing about Fire.

## 9. Gaps, caveats and what to do next

**Not done in this pass**
- **CPS and Park District value context.** The task covered City departments. CPS has per-student math (above) but no outcome metrics (test scores, graduation, attendance) were gathered. CPS enrollment fell 3.65% in one year, which matters for per-student cost. Illinois Report Card (ISBE) and CPS's own data portal would be the sources.
- **Park District** peer comparison is not fair from Census because Parks is a separate government.
- **Crime counts, CPD response times, COPA case outcomes, library visits since 2019, public health indicators, affordable housing units, TIF performance.** All datasets exist on the portal (see `data/context_dept_map.json` notes for IDs), none analyzed here.
- **Historical comparison against peers** (only 2024 is used).
- **All-City legal payout total** is not published in one place.

**Known weaknesses**
- I read the "2025 KEY RESULTS" text closely for only a few departments (Streets and Sanitation, CDOT, Police, Fire, Library). The other blocks are saved as extracted and not interpreted. Extraction leaves odd spacing.
- The 311 "within X days" figures use only requests the City marked Completed, so slow or never-completed requests are excluded from the share. For example, 9,800 of 11,694 stray animal complaints were Canceled and are not in the speed number.
- The 5-year settlements discrepancy with WTTW (section 6).
- The Census peer comparison's pension treatment is unverified (section 5).

**Verified in this work (spot checks)**
- Clerk tax rates add exactly to the printed 6.853152%.
- Settlement patterns raise an error if a number is not found in a Law Department PDF.
- All 32 oversight quotes found verbatim in downloaded sources. The check caught one bad quote while building (a sentence with a line-wrapped hyphen, "re-\nchecks"), now handled by normalizing the hyphen in both the source and the quote.
- The 40-department list matches dataset 6694-f78c, and department totals sum to $18,668,568,460, the same as the appropriations file total.
- A number I first assumed (Aviation's 311 requests are information calls) turned out to be wrong, and was corrected after checking the raw data (they are all aircraft noise complaints).
