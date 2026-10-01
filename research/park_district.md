# Chicago Park District FY2026: data research

Status as of 2026-09-30. Page numbers are PDF pages unless marked "printed" (printed page = PDF page minus 6 in the budget, minus 7 in the ACFR). Every number below is read from a public source and checked by script. Nothing is estimated. Where the District does not publish something, this file says so.

Files:
- `scripts/parks_extract.py`, `parks_parse.py`, `parks_build.py`, `parks_beyond.py` (run in that order)
- `data/parks_2026.json` (2.2 MB, the single deliverable)
- `raw/parks/` (gitignored: the PDF, word positions, contracts crawl, pension and ACFR PDFs)

## 1. Bottom line

| Question | Answer |
|---|---|
| Is the $637.6M operating budget parsed and exact? | Yes. The tree sums to the printed Grand Total **$637,580,350** (2026) and **$598,512,384** (2025) with zero difference. |
| How deep does it go? | function > department or region > park > fund > account class > account > job title (under Salary & Wages). 6,091 leaf nodes. |
| How many leaves are still $1M or more? | 71 leaves, holding $428.6M. Reasons in section 4. |
| Individual parks | 230 parks with park numbers (Central 68, North 81, South 81). 210 are under $1M in total, 20 are over. Even those 20 split below $1M at the account level except three management-contract lines: Maggie Daley $4.39M, McFetridge $3.24M, Gately $1.57M (626xxx). |
| Beyond operating | Capital, debt, pension, vendors, ACFR all found. Gaps: no per-project capital dollars, no vendor payment data. See section 3 and 5. |

## 2. Operating budget parser (task 1)

Source: https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf (274 PDF pages, printed page = PDF page minus 6). Saved as `raw/parks/approp.pdf`.

How the layout works (all handled by the parser):
- Each unit block has a title (12pt department, 16pt park, "Mozart - 0128"), a fund line, an account table on the left (columns 2024 actual, 2025 budget, 2026 budget) and a Positions table on the right.
- Negative values print as `($21,498)`, and once as `$(5,332,865)` (p102). Zero cells print `$0` or `-`.
- Class subtotal rows (610000, 620000 ...) come AFTER their detail rows. Membership is positional.
- Long names wrap onto a second line with the numbers between the two lines (p94, p87). Amounts are matched to columns by right edge, not by token order.
- Number fragments split across glyphs (`$42,` `33` `4,115` on p102) are re-joined.
- 2024-actual cell is sometimes missing but the 2025 and 2026 cells print. Blank cells are assigned by x-position, never by order.
- Page 103 (Grant Park Music Festival) is a wide 8pt table with `--` separators and has its own parser.
- Summary pages (District Administration pp76-77, Finance General p102, Districtwide pp104-105, three Region summaries) have only 2 columns.
- Rotated sidebar text is dropped.

Parsed: **317 tables** (311 unit/fund tables, 6 summary tables), **4,217 account rows**, **2,180 position rows**, 306 positions tables.

### Tree

```
Chicago Park District FY2026                         637,580,350
  Finance General (p102, "All Funds")                230,534,079
  Administration & Finance (22 units)                127,780,763
  Operations & Maintenance (8 units)                 122,680,109
  Recreation & Programming, districtwide (12)         31,980,512
  Neighborhood Parks by Region                       121,324,788
    Central Region (68 parks + admin)                 42,276,369
    North Region (81 parks + admin)                   40,008,335
    South Region (81 parks + admin)                   39,040,084
  Grant Park Music Festival                            2,400,000
  Not itemized on any department page                    880,099   (reconciling item, see below)
```

Each unit node has children by fund (Corporate, Special Recreation Activity, Liability, Capital Project Administration, Operating Grants), then class, then account, then job titles under 611005. A second tree, `tree_by_fund`, regroups the same unit-fund amounts by fund. Every node carries `amount2026`, `amount2025`, page, and a `check` block (children sum and difference).

### Reconciliation results (23 of 23 checks pass)

| Check | Result |
|---|---|
| Printed Grand Total, revenue table p55 and expense table p63 | 637,580,350 both, 598,512,384 for 2025 |
| Printed expense and revenue class subtotals vs Grand Total | Within $1 (PDF rounding). Exact diffs stored. |
| Every one of 311 unit tables: class subtotals vs printed Total | all within $2 (most exact) |
| Every class subtotal vs its detail rows | within $2 |
| Position rows vs each printed positions Total (306 tables, 2,180 rows) | within $3, no violations |
| Sum of positions-table FTE vs printed 3,213.0 (PDF p58) | 3,212.7 (rows are rounded to 0.1) |
| Central Region, 78 tables vs printed Region Summary Total | diff $1 (2026) |
| North Region, 88 tables vs printed Region Summary | diff $1 |
| South Region, 91 tables vs printed Region Summary | diff $4 |
| Finance General p102 classes vs Total | exact (230,534,079 and 208,238,576) |
| Five summary tables (DA, Districtwide, 3 Regions): class lines vs Grand Total | within $2 |
| Tree root: children sum vs Grand Total | **exact, both years** |
| By-fund tree vs Grand Total | exact |

Cross-check by account code: summing every account across department pages and Finance General and comparing to the printed all-funds account table (pp62-63) leaves a gap of **$880,099 (2026)** and **$11,205 (2025)**. This is real. The Districtwide Summary (pp98-99) includes amounts that appear on no department page. The biggest pieces, by account: 623130 General Contractual Services $319,080, 627012 Building Improvement $300,000, 620075 General Supplies $47,675, 624005 Special Program $55,641, 623195 Travel $43,000, 625060 Internal Transfers $50,000, 620020 Bldgs/Maint Supplies $20,000, 620010 Beach/Pool Supplies $15,000, 623093 Transportation $15,000, 623020 Professional Services $10,000, and about $5,000 of rounding. I put it in its own node "Not itemized on any department page" instead of guessing a department. The site should show it as a small Districtwide line with a note.

### Things the PDF gets wrong (kept as printed, reported)

1. p76-77 District Administration Summary prints Total **$384,928,302** but its own class lines add to $384,778,302. $150,000 difference. Class lines tie to the Grand Total, so the printed Total is a typo.
2. p87 Information Technology has a garbled row: code printed as `v62710`, no name, $1,996,642 in **2024 only** (a Fixed Asset item). Kept with `code: UNKNOWN`. No 2025 or 2026 effect.
3. p107 Facilities Management Specialty Trades: 611005 Salary line is $31,974,639 but its Positions table totals $31,882,866 ($91,773 gap). Both numbers are kept.
4. Five account codes appear on unit pages but not in the all-funds table (623100, 625040, 627070, 627075, 627100). All are 2024-actual only.
5. Printed revenue reuses code 412000 for both Property Taxes Total and TIF Disbursements Total.
6. Park name typos kept as printed ("Shabbona" and "Shabonna" on PDF p204).

### Depth

- Individual parks: **all 230 listed** with 4-digit park numbers. Park numbers match the District's capital project layer (215 of the 230 parks have projects, see section 3).
- Smallest meaningful unit: account line per park per fund, e.g. "Mozart 0128, Corporate Fund, 623130 General Contractual Services, $1,196".
- Positions: job title + job code + FTE + dollars per unit (no individual names, ever).

## 3. Beyond operating (task 2)

### 3.1 Capital Improvement Plan 2026-2030

- Printed in the budget PDF p69 (printed 63), **category level only**: $681.4M total, $225.5M District money (including $200M of new G.O. bonds, $40M a year), $381.7M expected outside funding. By outside source: City $60.68M, TIF $158.51M, State $52.28M, Federal $86.02M, Private $24.18M. By use: Acquisition and Development $296.8M, Facility Rehabilitation $171.5M, Site Improvements $188.6M, Technology/Vehicles/Equipment $24.5M. Parsed into `beyond_operating_from_budget_pdf.capital_improvement_plan_2026_2030`, validated (sources = uses for each year).
- Ordinance capital appropriations 2026 (pp253-254): Capital Grant Fund $30,000,000, Capital Improvement Fund $22,954,266, Reserve for Park Improvements $38,849,424 = **$91,803,690**. Harbor Capital, Special Recreation Capital, Park Replacement are $0.
- **No per-project dollar list for 2026-2030 is published.** Checked: the CIP page (https://www.chicagoparkdistrict.com/capital-improvement-plan) links only older CIPs (2015-2019 through 2021-2025, summary level) and "2011-2024 Capital Projects by Park" (85 pages, 2,887 rows, no dollar column).
- What does exist is the project list behind the District's capital map: ArcGIS layer `cap24_3` (https://services7.arcgis.com/HpTF5nhGpVZolZvo/arcgis/rest/services/cap24_3/FeatureServer/0, map "as of April 2024"). **3,116 projects** with park number, park name, scope, ward, region, sub-program, status, year complete. No dollars. 2,348 join to a budget park number (215 parks). 395 are not complete (CONSTRUCTION 120, DESIGN 101, PRE-DESIGN 57, PLANNING 45, PENDING FUNDING 39, BID/AWARD 33), 319 of them match a budget park. The 395 active projects are embedded in `beyond_operating.capital.capital_projects_list.active_and_pending_projects`. The full 3,116 are in `raw/parks/cap24_projects.json` (re-fetch with the URL above).
- Featured projects with dollars in the budget narrative (PDF pp 69-72, printed 63-66): Cragin Park fieldhouse $7.1M TIF + $500K HUD, Kells Park $17M TIF + $1.5M State, Park 598 (TIF + DCEO), DuSable Park (Open Space Impact Fees + private), Moran Park, Ogden Park, shoreline protection over $8M (Calumet, Montrose, Oakwood), about $6M of utility infrastructure in 2026, Piotrowski pool enclosure.
- Operating money going to capital in 2026: 625065 Transfer to Capital Projects $10,523,042 (the ordinance footnote calls $10M of it "TIF Surplus Capital"), plus $5.5M "Capital Transfer from Operating" in the CIP.
- Next step if per-project dollars are required: Board of Commissioners reports (Legistar) for individual contract awards, or an Illinois FOIA to foia@chicagoparkdistrict.com for the working capital plan.

### 3.2 Debt service

- Operating budget 2026: interest $35,926,546 (600005) + principal $34,630,000 (600015) = **$70,556,546**. 2025: $37,346,183 + $33,335,000.
- Ordinance Appropriation M (p253) lists **25 bond series plus a "Future Issuance" row**: principal $34,630,000, interest $34,826,546, total $69,456,546. Principal ties exactly to the operating line. Interest is $1,100,000 below the operating line, and the ordinance footnote says that $1.1M of interest sits in General Fund Other Expense outside the bond schedule. Largest series: Limited Tax Refunding Bonds 2023C $22.3M, Refunding Taxable 2020F-2 (Harbor ARS) $8.4M, Park Bonds 2016A $5.6M, 2023A $3.9M. 25 of the 26 rows are under $10M (only 2023C, $22.3M, is over).
- GO debt outstanding: $879,265,000 at 12/31/2025 (budget PDF p73 and ACFR printed p118 agree exactly). Schedule by period to 2047 is in the JSON (principal + interest = $1,300,788,378 total). About $219.1M is alternate-revenue debt (PPRT $78.6M, Harbor $116.2M, SRA $24.3M). Ratings AA (Fitch), AA (Kroll), AA- (S&P). Harbor revenue backs $10.6M of 2026 debt service.
- Bond authorizations by Board action: up to $120M (Sep 2025), up to $160M (Feb 2024), up to $11M SRA (Feb 2024). Total District debt including premiums and leases: $965.6M (ACFR p119).

### 3.3 Pension (Park Employees' Annuity and Benefit Fund, "PEABF")

- 2026 budget: 625020 Pension Expense **$63,332,412** plus 625023 Supplemental Contribution **$6,000,000** (one-time, from TIF surplus) = **$69,332,412** (ordinance Appropriation C). 2025 was $59,679,376. These are in Finance General.
- Fund's own numbers (actuarial valuation as of 12/31/2025, Segal, https://www.chicagoparkpension.org/wp-content/uploads/2026/06/Park-Employees-Annuity-and-Benefit-Fund-of-Chicago_Actuarial-Valuation-Report-as-of-12.31.2025.pdf): funded ratio **33.2%** (33.4% on fair value), unfunded liability **$903,648,276**, Board-policy actuarially determined contribution for 2026 **$88,904,199**. The statute (P.A. 102-0263) sets the actual payment, which is lower. History of Board-policy requirement vs actual contribution 2016 to 2025 is in the JSON, e.g. 2025: required $83,030,259, paid $59,679,376 (71.9%). Parsed and cross-checked to the budget's 2025 line.
- Members at 12/31/2025: 2,701 retirees and beneficiaries, 206 inactive, 3,251 active, 6,158 total. Net pension liability measured 12/31/2024: $889.5M (total $1,307.4M less assets $418.0M). The Fund's own report puts it at $901.3M at 12/31/2025.
- Deepest public split: statutory contribution = employer normal cost + a 32-year amortization of the unfunded liability. Retiree payments (about $86.0M in 2024) are made by the Fund, so on the site the District's share stops at "$63.3M + $6.0M".
- The Fund publishes its own ACFR, valuation, President's Report, investment provider list and vendor listing at https://www.chicagoparkpension.org/about-us/annual-reports/ (the site blocks plain scripts, works in a browser).

### 3.4 Vendors and managed assets

Source: the District's public contracts library, https://chicagoparkdistrict.bonfirehub.com/portal/?tab=publicContracts. It is JavaScript-rendered, so I read it through a browser: 768 contracts, 569 closed, 199 not closed (active or pending), details saved to `raw/parks/bonfire_contracts_nonclosed.json` and the JSON. JSON endpoints used: `/PublicPortal/getPublicContractsSectionData` (list) and `/internalApi/publicContracts/{id}` (detail with Value). The library is rate limited, so crawl one request at a time. **Caveat: "Value" is the whole-term contract amount or ceiling (often $0), not annual spend.**

The 626xxx lines of the budget (all in Revenue department and Finance, mostly under 623000 Contractual Services), mapped to vendors:

| Budget line (2026) | $ | Vendor | Contract |
|---|---|---|---|
| 626045 Soldier Field Management | 36,292,135 | SMG (now ASM Global) | P-12035 (also covers McFetridge and the Devon/Kedzie stadium). Library shows pending Apr 2027 to Mar 2028, value $0. Older P-07038 (2011) names SMG. |
| 626040 Harbor Management | 16,580,506 | Westrec SMI OpCo LLC | P-14010, active May 2026 to Apr 2027. Budget PDF p264 prints "Managed by Westrec SMI". |
| 626050 Golf Management | 8,490,697 | Indigo Sports, L.L.C. (Troon) | P-24001, Jan 2025 to Dec 2034. Fee $1,275,000 per year, $9M contractor capital over 10 years, $25K per year community fund (Board action 24-1125-0911). Prior: Billy Casper Golf. |
| 626060 Maggie Daley Park | 4,387,340 | ASM Global | P-24009, Apr 2026 to Apr 2033, value $1,525,000. Fee 2026 $200,000 rising to $250,000 in 2031 (Board action 25-1070-0409). Prior: Transwestern. Budget fell $1.6M on the switch. |
| 626055 McFetridge Sports Center | 3,243,300 | SMG | under P-12035 |
| 626005 Parking Management | 1,691,052 | Standard Parking Corporation | P-14012, pending Oct 2026 to Oct 2027 |
| 626065 Beverly/Morgan Park Sports Complex | 1,817,652 | SMG | P-15018, Jan 2026 to Mar 2028, value $530,914 |
| 626066 Addams + 626067 Gately | 1,420,960 + 1,569,260 | ASM Global | P-19021, pending, value $530,911 |
| 626010 MLK Center | 1,548,354 | Chicago Skating Partners LLC | P-25008, Jul 2026 to Jul 2033, value $1,698,172 (prior: Chicago City Skating) |
| 626015 Ice Skating | 992,697 | Westrec SMI OpCo | P-23010 $675,000, P-25021 awarded Feb 2026 |
| 626030 Cellular infrastructure | 537,438 | SPAAN Tech Inc | P-25001, Dec 2025 to Dec 2030, value $2,847,329 |
| 626035 Concessions | 929,159 | UCG Associates, then Unison Consulting (Board action Apr 2026) | P-20011 value $2,481,433 |
| 626025 Landscape Services | 8,107,327 | Christy Webber & Company, Moore Landscapes, Clauss Brothers and others | mapping is my inference from titles |
| 623185 Grant Park Music Festival | 2,400,000 | Grant Park Music Festival (nonprofit grant) | no procurement contract |

Also relevant: Soldier Field food service is separate. **Levy Premium FoodService LP**, P-23013, Jul 2024 to Jul 2029, value $1,000,000, $12M contractor capital, commission schedule in Board action 24-1058-0410 (prior: Aramark). Revenue side contracts (no cost to the District): Chicago Bears lease through 2033 (about $7.0M a year per ACFR), Lollapalooza (C3 Presents, through 2032), Live Nation at Northerly Island, NASCAR, Riot Fest.

Revenue facts from the budget narrative (PDF pp 45-51, printed 39-45): Soldier Field is projected at $62.9M gross revenue and $36.3M gross expense in 2026, harbors $31.5M revenue and $16.6M expense, golf $9.9M revenue and $8.5M expense, parking $9.4M and $1.7M.

Non-closed contracts with stated value of $1M or more: 22 contracts, $71.6M total. Largest: Stantec natural area services $10.5M, F.H. Paschen Garfield Park Conservatory children's garden $8.6M, Christy Webber planting $6.0M, McField roofing supplies $5.0M, Midco electrical supplies $4.9M, Moore floral gardens $4.0M, Flood Bros waste $3.8M. Three big pools list vendors with no stated value: A&E (67 firms), General Contractor (36), Rapid Response Construction (19).

**Vendor payments: not published.** The Park District is not in the City's payments dataset, has no open data portal for spending, and its own site has no vendor payment or check register page. The supplier portal is registration only. Paths to payments: FOIA, or the ACFR for totals.

### 3.5 Positions and salaries

Published inside the same PDF: title, job code, FTE and dollars for 2025 and 2026 per unit and fund. 306 tables, 2,180 rows, summing to 3,212.7 FTE and $220,590,557 (the 611005 total is $220,682,330, difference is item 3 of the PDF errors above). Budget text: 3,213.0 FTE = 1,796 full time, 853 hourly, 564 summer seasonal (PDF p58). 89% of positions are union. No individual employee names or salaries in the budget. Not found on the portal.

### 3.6 ACFR and actual vs budget

- FY2025 ACFR (dated July 28 2026, 140 pages): https://files.chicagoparkdistrict.com/2026-07/Chicago%20Park%20District_25%20ACFR_Final.pdf . FY2024 ACFR and Popular Annual Financial Reports back to 2007 are on https://www.chicagoparkdistrict.com/comptroller .
- General Fund budget vs actual 2025 (ACFR printed p87, $ thousands): revenues budget 416,974 vs actual 395,140 (property taxes 157,809 vs 199,355 because Cook County's second installment came December 15), Soldier Field actual 74,567 vs 56,838 budget, expenditures budget 416,974 vs actual 435,798 (personnel 225,312 vs 220,647, contractual 184,981 vs 175,994), deficit $40.7M budgetary basis. Stored in `beyond_operating.acfr_fy2025`. It is General Fund only, so it does not line up with the $598.5M all-funds budget column. Use it for the "planned vs actual" panel at category level, not per account.
- The 2025 ACFR reports the General Fund finished $24.3M under on a GAAP basis (letter, p3).

### 3.7 Open data

- Chicago Data Portal (data.cityofchicago.org) has 44 Park District-related datasets, all operational: permits `pk66-w54g`, activities `tn7v-6rnw`, parks `ejsh-fztr`, buildings `vcti-mbcd`, facilities `eix4-gf83`, beach water quality. **No budget, payments, contracts or salary dataset.** (The only budget-adjacent ones are 2012-era performance metrics, e.g. Comptroller accounts payable aging `q93p-dagd`.)
- Board of Commissioners records are on Legistar with a public API: https://webapi.legistar.com/v1/chicagoparkdistrict/matters . Contract award reports with Exhibit A fee terms are attached (used above). Budget ordinance attachments: matters 6232 and 6223.
- The District's ArcGIS hub has parks, buildings, natural areas and the capital project layer. Nothing financial.

## 4. Why 71 leaves are still over $1M (the "why can't I go deeper" notes)

| Group | Leaves | $ | What a user should be told |
|---|---|---|---|
| Finance General accounts | 16 | $225.2M | Pension $63.3M (one statutory payment), debt interest $35.9M and principal $34.6M (25 bond series exist in the ordinance and can be attached), Zoo $6.75M and Aquarium and Museum $29.6M (11 institutions listed in ordinance Appropriation F, each $1.7M to $4.6M, so they split but stay over $1M for 7 of 11), utilities (water and sewer $16.7M, electric $14.8M, gas $6.1M, no account-level detail), vacancy allowance (a negative budget adjustment of $15.2M), transfer to capital $10.5M. |
| Managed-asset 626xxx lines | 12 | $92.4M | One management contract each (Soldier Field, harbors, golf, Maggie Daley, etc.), vendor named in 3.4. The District publishes the contract, not what the contractor spends the money on. |
| Job-title lines (headcount x pay) | 22 | $54.1M | e.g. Laborer (Maintenance) $10.5M, Operating Engineer (M) $5.5M, Security Officer $3.4M. Split by FTE and pay per title is already included. Individual pay is not public in the budget. |
| Other account lines | 21 | $56.8M | Health benefits, insurance $7.2M, IT professional services $4.6M, waste disposal $4.1M, workers comp $3.25M, judgments $3.25M. Contract-level splits come from the contracts table where one exists (waste: Flood Bros $3.8M ceiling). |

Everything else (6,020 leaves) is under $1M.

## 5. Gaps and how to close them

| Gap | Status | Next step |
|---|---|---|
| Per-project capital dollars, 2026-2030 | Not published | FOIA for the working CIP, or Board reports for individual awards. Meanwhile show 395 active projects per park (scope, status, no dollars). |
| Vendor payments (actual spend per vendor) | Not published | FOIA. Contracts table gives ceilings and terms only. |
| Which department holds the $880,099 | Not stated in the PDF | Could be answered by the FY2026 Budget Recommendations at https://legistar2.granicus.com/chicagoparkdistrict/attachments/66541197-6851-4854-8a35-68b0350e93f8.pdf (proposed budget, matter 6223) if it differs. Not read. |
| Soldier Field operating agreement terms (SMG) | Library lists the agreement as pending with value $0, no terms | Board reports from 2011-2013 (P-12035) are in Legistar. Not read. |
| Fund split for Finance General | PDF says "All Funds" | Ordinance Appropriation C (pension), M (debt), F (museums) give the fund for those lines. |
| Actuals by park | Page tables include **2024 Actual** per account per park, parsed into `amount2024` | Already available for the three years 2024, 2025, 2026. |

## 6. Reproduce

```
pip3 install pdfplumber pypdf
python3 scripts/parks_extract.py     # downloads the PDF, writes raw/parks/words.json (40s)
python3 scripts/parks_parse.py       # raw/parks/units.json
python3 scripts/parks_build.py       # data/parks_2026.json, prints 23 checks
python3 scripts/parks_beyond.py      # adds beyond_operating, prints 16 checks
```

`parks_beyond.py` also reads files fetched during research and kept in `raw/parks/`: `cap24_projects.json`, `bonfire_contracts_nonclosed.json`, `acfr25_text.json`, `pension_valuation_text.json` (re-create from the URLs above).
