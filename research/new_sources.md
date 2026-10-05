# New sources: what the other research files did not use

Author: gap-hunter agent (second pass), 2026-10-01. Scope: sources not already used in an earlier planning draft or the other `research/*.md` files and not already read by `scripts/*.py`. Downloads are in `raw/gap/` (gitignored). The quick checks behind the "Verified" column are in `scripts/gap_sources.py` (re-runnable, read only, no big downloads).

**Verified** means I fetched the URL or queried the API in this session and looked at the response (status, row counts, or file text). **Not verified** means I only know the link from a page I read, or I could not get at the data. I have not invented any URL. Every URL below comes from a downloaded page, a script, a catalog record, or a fetch I ran.

## 1. Headline findings

1. **CPS FY2027 is already adopted.** `cps.edu/about/finance/budget/budget-2027/` is live with an approved FY2027 Budget Book PDF and FY27 interactive BI reports. CPS fiscal years run July to June, so the site's "CPS FY2026" is a year that ended 2026-06-30. Decide whether the CPS branch should move to FY2027 (same OBIEE portal, new path). Verified.
2. **Best new depth for the City: Workforce Vacancies `9v3e-pcjs`.** Downloaded by the earlier agent but never used. 1,310 rows by department, fund, division, section and job title, with budgeted positions, filled and vacant counts as of 2026-08-31. Joins to the Positions dataset by title and section code. Verified.
3. **Best new depth for revenue and incentives: the TIF and DPD incentive datasets.** Named recipients, almost all under $1M (details in section 3, row 4). Verified.
4. **Biggest missing bridge, but blocked:** the Mid-Year Report says every 2025 third-party contract payment, with the *funding line used*, is in an OBM Tableau "Data Directory" dashboard. A funding line is the missing key that `contracts_vendors.md` had to infer. I could not reach the data without a browser (the Tableau CSV export URL I tried returned 404 and the page is a shell). Not verified.
5. **Cook County Clerk agency file adds 63 City special service areas** (SSAs, about $32.3M of 2024 levy). They are not in the ordinance (zero "service area" hits in the 3,268 appropriation rows). All but 7 are under $1M. This is a small, clean "under $1M" branch, and it also lets us show the City, CPS and Park District property tax lines from one printed source. Verified.
6. **One cross-check worth noting for `reconciliation.md`:** in the Clerk 2024 file, the City's "NOTE REDEMPTION LIBRARY FUND" levy is exactly $117,145,000, the same number as the Library term-note line in the Recommendations book. That is an exact match and nothing more. I have not shown it explains the unitemised $117M. Verified (file read).

## 2. Ranked inventory (summary)

Rank is by value toward "every node under $1M with public data", then by effort. Effort: **S** under half a day, **M** one to two days, **L** more, or needs a browser.

| # | Source | Format | Explains | Gets below $1M? | Effort | Verified |
|---|---|---|---|---|---|---|
| 1 | Workforce Vacancies `9v3e-pcjs` | Socrata JSON | Filled vs vacant positions under every salary line | Yes, title x section x fund | S | Yes |
| 2 | Budget ordinances 2011-2025 (appropriations, positions, recommendations) | Socrata JSON | 15-year trend for every node | Same depth as 2026 | S | Yes (IDs and row counts) |
| 3 | CPS FY2027 Budget Book, FY27 BI, FY2025 ACFR | PDF, OBIEE | CPS year update, audited actuals, debt schedules | Same as CPS today | M | Yes (URLs) |
| 4 | TIF and DPD incentive datasets (`iekz-rtng`, `etqr-sz5x`, `rym7-49n8`, `v7gx-e2v6`, `syk7-tkvr`, `j7ew-b73u`, `cnna-nmxx`) | Socrata JSON | Named TIF and incentive recipients | Yes, most rows | S | Yes |
| 5 | ARPA expenditure ledger `7tg5-i782` + program details `m9g9-cj96` | Socrata JSON | The $1.86B of ARPA spending (OBM, DFSS, CDPH...) | Partly | S | Yes |
| 6 | Mid-Year Report tables not yet parsed (pp. 16-46, 59-65) | PDF text | YTD actuals by dept x fund, overtime vs salvage, efficiency targets, special events, 2025 bond issues | Partly | M | Yes (file read) |
| 7 | Cook County Clerk agency rate file (City SSAs, levy by fund) | XLSX | City SSAs, property tax lines for all three governments | Yes for SSAs | S | Yes |
| 8 | CPS procurement API: payments tail, pooled awards, non-Board sheets | JSON, CSV | Small CPS vendors, pooled contracts | Yes (tail) | S | Yes |
| 9 | Mid-Year Report "Data Directory" Tableau (contract payments with funding line) | Tableau | Vendor to budget line link | Yes | L (browser) | Page only |
| 10 | Calculated Budget Floors (fringe rate 55.96%) | PDF | Fully loaded cost of OIG, COPA, CCPSA | No | S | Yes |
| 11 | OBM Monthly Revenue Reports Jan-Aug 2026 | PDF | Revenue by line, month by month | Partly | M | Yes (Aug, May) |
| 12 | Park District: Budget Recommendations book (matter 6223), Legistar attachments, participatory budgeting page | PDF, JSON, HTML | Proposed vs adopted, contract fee terms, a $500K pilot | Yes (small items) | M | Yes (URLs) |
| 13 | Ordinance Violations `6br9-quuz` | Socrata JSON | Fines side of "Fines, Forfeitures and Penalties" | Yes | S | Yes |
| 14 | OBM CIP "Map and Funding Summary" Tableau | Tableau | Possibly a newer CIP than the 2025-2029 PDF | Unknown | L (browser) | Page link only |
| 15 | CPS capital expenditure reports FY12-FY25, bond official statements | OBIEE, PDF | Actual capital spending, debt maturity | Yes (projects) | M-L | Page links verified |
| 16 | Low value or redundant (Q1 QBR, Q1 menu, April execution deck, reform options, engagement report, transfer PDFs, OIG portal) | mixed | see section 4 | No | n/a | Mostly |

## 3. Details by source

### 1. Workforce Vacancies, `9v3e-pcjs` (verified)
- URL: https://data.cityofchicago.org/resource/9v3e-pcjs.json (API answered 200). Local copy `raw/gap/workforce_vacancies.json`. Fetched by `scripts/gap_fetch.py` but no script or research file reads it (`grep` for `9v3e` hits only the fetch script).
- Content: 1,310 rows, one snapshot, `report_date` 2026-08-31. Fields: department, fund, division, section, sub-section, `title_code`, `total_positions`, `employees_in_position`, `number_of_vacancies`. Totals in the file: 26,321 positions, 3,857 vacancies, 620 title codes, 359 section codes. Example: department D57 shows 13,100 positions and 1,393 vacancies.
- Explains: the headcount behind each salary line in the Positions dataset (`v2t2-vajc`) and the "turnover/salvage" lines. Pair with Mid-Year Report pp. 40-46 for the narrative.
- Depth: title x section x fund. Under $1M when multiplied by the pay rate for all but the largest titles. Caveat: these are position counts. The position count (26,321) is not the same unit as the ordinance row count (8,243 rows), so do not compare them without the join.
- Effort: S. Join on `title_code` and section code to `v2t2-vajc`. Check the match rate first.

### 2. Budget history 2011-2025 (verified IDs and row counts via API today)
Earlier research mentioned many IDs, but no file listed them and no script read anything older than 2025. Appropriations ordinance dataset per year (row count):

| Year | Appropriations | Rows | Positions | Rows |
|---|---|---:|---|---:|
| 2011 | `drv3-jzqp` | 4,271 | `g398-fhbm` | 8,216 |
| 2012 | `8ix6-nb7q` | 3,894 | `4n2t-us8h` | 6,645 |
| 2013 | `b24i-nwag` | 3,591 | `78az-bt2s` | 7,215 |
| 2014 | `ub6s-xy6e` | 3,602 | `etzw-ycze` | 7,260 |
| 2015 | `qnek-cfpp` | 3,707 | `f338-e9ns` | 7,702 |
| 2016 | `36y7-5nnf` | 3,620 | `ipsp-k4xh` | 7,671 |
| 2017 | `7jem-9wyw` | 3,320 | `vcfx-7p4u` | 7,158 |
| 2018 | `6g7p-xnsy` | 3,401 | `9d7d-7f2b` | 7,311 |
| 2019 | `h9rt-tsn7` | 3,507 | `7zkb-yr4j` | 7,445 |
| 2020 | `fyin-2vyd` | 3,509 | `txys-725h` | 7,343 |
| 2021 | `6tbx-h7y2` | 3,384 | `gcwx-xm5a` | 7,100 |
| 2022 | `2cr6-8u6w` | 3,446 | `v2mx-icwv` | 7,404 |
| 2023 | `xbjh-7zvh` | 3,447 | `pkjy-hzin` | 7,873 |
| 2024 | `x394-e874` | 3,584 | `jeta-egyx` | 8,126 |
| 2025 | `t59y-fr3k` (already used) | 3,477 | `2bp7-w85v` | 8,259 |

Revenue ordinances exist only for 2024 (`rmi8-cugu`, 151 rows), 2025 (`e5cq-t86i`, 143) and 2026 (`nydj-5nax`, 156) in the catalog. Recommendations ("proposed") versions exist for 2012 to 2026 in `catalog_admin_finance.json` (for example 2025 `miyk-k49p`, 2026 `axxr-vais` already used, 2026 positions `wd4x-2xf8`).
- Explains: "+X% since 2016" for each department and appropriation line, and year-over-year change in positions.
- Depth: same as the 2026 ordinance.
- Effort: S for totals by department. M if account names or department numbers changed across years. **I did not check whether column names or department codes are stable across years.** Test two or three years before promising a line-level trend.

### 3. CPS FY2027 and audited actuals (verified URLs)
- FY2027 Approved Budget Book, 7.7 MB PDF, HTTP 200: https://www.cps.edu/globalassets/cps-pages/about-cps/finance/budget/budget-2027/docs/fy2027-budget-book-final-approved-2.2.pdf
- FY2027 page with the FY27 interactive BI link (same OBIEE host as `cps_obiee.py`, path `CPS FY27 Budget`): https://www.cps.edu/about/finance/budget/budget-2027/ (200). Also lists FY27 department narratives, fact sheet and FAQ PDFs. The BI endpoint itself I did not query.
- FY2025 ACFR (audited), 2.1 MB PDF, HTTP 200: https://www.cps.edu/globalassets/cps-global-media/banner-images/annual-financial-report/fy25-acfr-final.pdf. `cps_deep.md` says the ACFR was not downloaded and only the popular report was used. The ACFR is the right source for audited actuals, because the BI "actual" columns understate audited spending by about $0.7B (FY24) and $2.7B (FY25) per `cps_deep.md`.
- The ACFR index page lists ACFRs back to FY2007: https://www.cps.edu/about/finance/annual-financial-report/ (200).
- Explains: CPS budget vs actual, debt schedules, pension notes, and the FY27 update.
- Depth: no deeper than the existing CPS tree (school level already comes from BI). ACFR is category level.
- Effort: M (a re-run of `cps_fetch.py` with the FY27 parameter, plus ACFR table parsing).

### 4. TIF and DPD incentive datasets (verified by API count and sum today)

| Dataset | ID | Rows | Sum of `incentive_amount` | Rows under $1M |
|---|---|---:|---:|---:|
| Financial Incentive Projects, TIF-Funded Economic Development | `iekz-rtng` | 40 | $1,364,203,923 | 6 ($3.96M) |
| Small Business Improvement Fund | `etqr-sz5x` | 2,260 | $158,290,850 | 2,260 (all) |
| Neighborhood Opportunity Fund, Small | `rym7-49n8` | 126 | $19,845,903 | 126 (all) |
| TIF Works | `v7gx-e2v6` | 411 | $24,119,488 | 409 ($20.1M) |
| Property Tax Abatement | `syk7-tkvr` | 191 | $345,805,955 | 110 ($46.3M) |
| Neighborhood Opportunity Fund, Large | `j7ew-b73u` | 6 | $7,370,334 | 2 ($1.27M) |
| PACE | `cnna-nmxx` | 1 | $21,250,000 | 0 |

Companions already known but not these: `ijrh-ktm6`, `72uz-ikdv`, `mex4-ppfc`, `fpsv-qjg3`, `umwj-yc4m` (used in `contracts_vendors.md` and `grants_capital.md`). Fields: applicant, project name, ward, TIF district, approval date, project cost, other public funding, jobs.
- Explains: a named, sub-$1M leaf for the TIF and Planning and Development branch (SBIF, NOF, TIF Works). These are approved incentives over many years, **not 2026 spending**, so label them as "deals approved", the same way `mex4-ppfc` is treated.
- Effort: S.

### 5. ARPA "Road to Recovery" expenditure ledger (verified by API)
- `7tg5-i782` ARPA Road to Recovery Expenditure Report: 50,961 rows, `amount_expended` totals $1,859,400,552, latest expense date 2026-06-30, 69 cost centers, minimum row -$931,000 (reversals exist). Fields: `cost_center`, `expense_date`, `amount_expended`. https://data.cityofchicago.org/resource/7tg5-i782.json
- `m9g9-cj96` Program Details: 77 rows (program name, policy pillar, department, cost center). `9yp3-9pdz` Summary (67 programs, already pulled to `raw/gap/arpa_summary.json`, allocated $1,886.6M, expended $1,859.4M, so the ledger total equals the summary's expended total).
- Also `vn8e-3k8d` KPIs and `7fmw-nndy` geographic impact, both updated 2026-09-18, not read.
- Explains: the "ARPA" part of the Mayor's Office grants ($1.17B per `grants_capital.md`). One cost center, 0054774 "Essential City Services" (OBM), holds $1,172,217,159 in 17 rows, including a single $782.2M row in 2021 and a $385.0M row in 2022. That is revenue replacement, not purchases, so it cannot be split.
- Depth: by cost center total only 13 of 69 are under $1M. By cost center x month, 1,803 of 1,905 groups are under $1M but they hold only $258.3M (14%) of the dollars. **This is history (2021 to 2026), not the 2026 budget.**
- Effort: S.

### 6. Mid-Year Budget Report: tables nobody has parsed yet (file read)
File: `raw/gap/midyear_report_2026.pdf` (URL in `gap_fetch.py`: https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026Mid-YearBudgetReport.pdf, previous agent downloaded it). `gap_midyear.py` used only the grants pages. Unused sections:
- **pp. 16-38 Year-to-date expenditures, department x fund,** through May 2026, local funds only: budget, expenses, encumbrances, % spent. My quick regex found 162 department-by-fund rows, 48 with a budget under $1M, and $3.50B of expenses. This is a rough parse and is not reconciled. `raw/gap/midyear_dept_fund_budget.json` has the earlier agent's budget-only parse (159 rows). Reminder from `reconciliation.md`: the report prints Motor Fuel Tax and Parking Meters funds at twice the ordinance amount.
- **pp. 44-46 Hiring, attrition, overtime and salvage:** 2026 YTD external hires 770, internal hires 634, attrition 714, net +56. Overtime across all funds $146.3M through May vs $142.1M a year earlier. 39 department rows of overtime spent vs budgeted vs personnel salvage.
- **p. 25 Efficiency initiatives** (targets vs realised through May): land sales target $14,044,685 with $3,120,716 realised, fleet target $3,378,607, special events cost recovery target $6,986,491 with $344K realised, benefits target $2,000,000 with $2,857,232.91 saved, procurement target $10,000,000 with about $9,831,071. Monthly status reports exist for February to August 2026 (section 3 row 11 link style, below).
- **pp. 59-62 Bonds issued in 2025:** 7 GO series (2025A to 2025G, for example 2025A $393,395,000 at 6.00%), 3 Sales Tax Securitization series, 6 O'Hare series (2025A to E and G, including 2025E $1,101,570,000) and 2 Midway series. Overlaps with the untracked `pensions_debt_*` work, so check there first.
- **pp. 64-65 Special events cost-benefit:** 11 events, total City cost $14,040,075, recovered $4,893,340, unrecovered $9,146,735. Per event City cost: Mexican Independence Day $3,364,910, Marathon $2,663,540, Lollapalooza $2,655,137, NASCAR $2,190,149, Magnificent Mile Lights $1,006,405, then six events under $1M. A rare place with event-level City cost.
- Depth: partly below $1M (event level, many dept x fund rows).
- Effort: M (table parsing, then the reconciliation caveats).

### 7. Cook County Clerk agency rate file (verified: file opened, page fetched)
- `raw/gap/agency_rate_2024.xlsx` (1.1 MB, downloaded from https://www.cookcountyclerkil.gov/sites/default/files/2026-04/2024-agency-rate-report.xlsx). Sheets "Overview 2024" (947 agencies) and "Detail 2024" (8,060 fund rows). `value_context.md` cites the Clerk's 2025 tax rate report PDF (https://www.cookcountyclerkil.gov/publication/2025-tax-rate-report, fetched 200) but this xlsx is not cited anywhere.
- The page https://www.cookcountyclerkil.gov/property-taxes/tax-extension-and-rates lists a 2025 xlsx at `.../2026-08/2025-agency-rate-report-tables-updated.xlsx`. **That URL returned 404 when I fetched it**, so use the 2024 file or the 2025 PDF.
- City special service areas: 63 rows named "CITY OF CHICAGO SPEC... SERVICE AREA" (name match, my filter). 58 have a positive 2024 final extension, summing to $32.32M. Largest is SSA 1-2015 at $3.70M. Seven are at or above $1M. None appear in the 2026 ordinance (0 hits for "service area" in fund or department text). Treat as a separate "levied by the City, spent by service providers" branch.
- Property tax lines for all three governments from one table (2024 tax year, "Grand Total Ext"): City of Chicago $1,773,379,217, Board of Education $3,987,335,357, Park District $323,084,985. City fund lines include Police A&B levy $780,977,000, Fire $352,289,000, Municipal Employees $159,971,000, Laborers $53,723,000 and Library note redemption $117,145,000.
- Effort: S.

### 8. CPS procurement API: pieces not yet used (verified)
`api.cps.edu/procurement/` is already in `cps_deep.md`, but the saved CSVs keep only vendors paid $1M or more. In `raw/gap/cps_proc/`:
- `supplier_payments_<FY>.json` for FY2001 to FY2027 (the FY2027 endpoint answers 200, 847 KB): https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2027. The long tail: FY2026 has 4,631 vendors paid $3,557.1M of which 4,353 vendors under $1M hold $223.7M. FY2025: 6,371 rows, $3,588.4M, 6,080 under $1M hold $253.9M. FY2024 has 39,718 rows, $3,873.5M, 39,421 under $1M hold $280.0M. The jump in row count from FY2025 to FY2024 is unexplained, so check before comparing years.
- `pooled_awards_<FY>.json` (Board report number, authorized amount, title, **no vendor**). Verified: https://api.cps.edu/procurement/contracthistory/GetPooledContractAwards?reportyear=2026 returns 200. `cps_deep.md` used one pooled contract.
- `sheet_0.csv` (60 rows, "Non-Board Report and Non-CPOR Contract Awards") and `sheet_209654715.csv` (COVID-19 Emergency Authority as of May 11, 2023, 165 rows with a parseable total of $447.9M). **I do not know their original URL.** `gap_fetch.py` does not fetch them and I did not find the link. Treat as a lead from the CPS procurement app.
- Depth: this is the only place the CPS "who got paid" view reaches under $1M. Still by vendor, not by budget line.
- Effort: S.

### 9. Mid-Year "Data Directory" Tableau (not verified, access blocked)
- Link from OBM's data page: https://public.tableau.com/app/profile/obm.data.analytics/viz/Mid-YearReport-DataDirectory/DataDirectory-Mid-YearReport?publish=yes. Mid-Year Report p. 57 describes it: every third-party payment Jan 1 to Dec 31, 2025, with vendor, estimated contract value, department, payment amount **and the funding line used**, from the Department of Finance. Data limitation per the report: PO and invoice amounts repeat across rows, so columns cannot be summed.
- I fetched the page (HTTP 200) but it is a 1.8 KB shell behind a bot challenge. Guessed CSV export URLs returned 404. So I do not know if the extract is downloadable.
- Why it matters: it would replace the inferred vendor-to-line mapping in `contracts_vendors.md` with the City's own mapping. Ask OBM for the extract if a browser run fails.
- Effort: L.

### 10. Calculated Budget Floors (verified, file read)
`raw/gap/budget_floors_2026.pdf` (https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/Calculated%20Budget%20Floors.pdf). Gives the legal floors and **the fringe rate OBM uses: 55.96% of personnel cost** (2025 fringe, from Finance General benefit spending).
- OIG: floor $20,189,281, budget $14,297,022 + fringe $6,865,735 + indirect $2,267,313 - sister agency $208,750 = $23,221,320.
- COPA: floor $20,233,036, budget $15,781,027 + fringe $7,913,490 = $23,694,517.
- CCPSA: floor $4,451,268, budget $4,026,765 + fringe $1,792,862 = $5,819,627.
- Use: a documented way to show "true cost" of a department by allocating Finance General benefits (the black box in `finance_general.md`). It is one rate for all, so label it an average.
- Effort: S. Depth: no.

### 11. OBM monthly revenue and efficiency reports (verified for two PDFs)
- Monthly Revenue Reports, January to August 2026, all linked on https://www.chicago.gov/city/en/depts/obm/provdrs/budget/svcs/BudgetPublications.html (saved as `raw/gap/BudgetPublications.html`). Fetched 200: August https://www.chicago.gov/content/dam/city/depts/obm/2027_Operations/Monthly_Revenue_Report/Monthly_Revenue_Report_August_2026.pdf (6 pages), May https://www.chicago.gov/content/dam/city/depts/obm/supp_info/RevenueReports/Monthly%20Revenue%20Report%20May%202026.pdf. Corporate Fund budget vs actual by revenue category, then a month-by-month table by line (example: Hotel Accommodation Tax $91,914K and Checkout Bag Tax $23,393K for January to August).
- Monthly Efficiency Initiative Status Reports, February to August 2026 (August fetched 200, 224 KB): https://www.chicago.gov/content/dam/city/depts/obm/2027_Operations/Monthly_Efficiency_Report/City_Council_Efficiency_Priority_Monthly_Status_Report-August_2026.pdf. Narrative per workstream (real estate, fees and fines, fleet). Numbers are in the Mid-Year Report p. 25 instead.
- Explains: actual-to-date for the revenue side, which `value_context.md` shows only as budget. Corporate Fund only.
- Effort: M for tables by month. The efficiency reports are low value.

### 12. Park District: unread or thin sources (verified URLs)
- **FY2026 Budget Recommendations (proposed) book**, matter 6223, 13 MB PDF, HTTP 200: https://legistar2.granicus.com/chicagoparkdistrict/attachments/66541197-6851-4854-8a35-68b0350e93f8.pdf. `park_district.md` lists it as "not read" for the unexplained $880,099 and any change vs adopted.
- **Legistar matters 2025 on:** 281 matters (145 Action Items), all with an empty `MatterCost`. Only one title contains a dollar figure (the $120,000,000 not-to-exceed 2025 park bond ordinance). So amounts live in the attachments. I sampled 6 approved action items and 2 had an attachment. API: https://webapi.legistar.com/v1/chicagoparkdistrict/matters/<MatterId>/attachments (answers 200). Already partly used for contract fee terms in `park_district.md`. Next step would be a crawl of attachments for the 126 approved or passed action items, to get contract award amounts.
- **Participatory budgeting:** https://www.chicagoparkdistrict.com/participatory-budgeting (200). Page states a $500,000 pilot and about nine projects of roughly $50,000 each. A tiny but real sub-$1M item.
- **Bonfire public contracts** (`raw/gap/bonfire_contracts.json`, 768 contracts, one organization): list has name, vendor id and dates only, no dollars. Already used in `park_district.md`. Nothing new.
- Effort: M for the Legistar crawl, S for the rest.

### 13. Ordinance Violations, `6br9-quuz` (verified by API)
824,275 rows, $833.8M total `imposed_fine`. Revenue-side source for the "Fines, Forfeitures and Penalties" line ($481.7M in the Corporate Fund budget per the Mid-Year Report). Data quality: the violation date field contains impossible years (minimum 0119, maximum 6111), so clean the dates before slicing by year. Related and unread: Red Light `spqx-js37` and Speed Camera `hhkd-xvj4` violations (counts per camera and day, no dollar field in the catalog columns), Building Violations `22u3-xenr`, Vacant Building Violations `kc9i-wq85` (5,012 rows, has total paid), DOE Environmental Enforcement `yqn4-3th2` (38,078 rows, fine amount).
- Effort: S to M.

### 14. OBM Tableau dashboards (links only, not verified)
From `raw/gap/BudgetData.html`: Budget at a Glance, Workforce Vacancies Report, **CIP Map and Funding Summary** (https://public.tableau.com/app/profile/obm.data.analytics/viz/CIPMapandFundingSummary/CIP-Programming). `grants_capital.md` says no 2026-2030 CIP PDF exists. This dashboard might hold newer CIP data. I did not load it.

### 15. CPS capital expenditure reports and bond official statements (page links verified)
- https://www.cps.edu/about/finance/capital-expenditures/ lists FY12 to FY25 "Expenditure Report" links into the same BI host (actual capital spending). Page fetched 200. Reports not queried.
- Official statements for long-term bonds, for example Series 2025B/C (5.5 MB PDF, 200): https://www.cps.edu/globalassets/cps-pages/about-cps/finance/official-statements-for-long-term-bonds/final-offical-statement---cps-series-2025bc---2025-11-07.pdf. Page: https://www.cps.edu/about/finance/official-statements-for-long-term-bonds/. Gives maturity schedules per series. `cps_deep.md` already has debt by series from the budget book.
- Effort: M to L.

## 4. Looked at and rejected, or low value

| Source | Why |
|---|---|
| Q1 2026 Quarterly Budget Report (`qbr_q1_2026.pdf`, 16 pages) | Department and fund percent spent for Q1 only. The Mid-Year Report covers through May. Redundant. |
| Q1 2026 Aldermanic Menu (`menu_q1_2026.pdf`) | `grants_aldermanic_menu.py` already parses the newer Q2 report. Only useful to show change between quarters. |
| April 2026 Budget Execution deck (`budget_execution_apr2026.pdf`, 8.6 MB) | The text layer is almost empty (943 bytes), so it is images. Would need OCR. Two numbers visible in the text: $586.9M and $118.6M of Department of Finance revenue initiatives. |
| Quarterly Transfer Reports Q1 and Q2 2026 PDFs | 9 + 15 = 24 rows, which equals the 24 BFY2026 rows in `7x7d-3zgj` that `gap_midyear.py` used. No new information. |
| eLMS search (`elms_budget_search.json`, 4,073 matters, 1,551 in 2026) and the 128 eLMS files (ward transfer ordinances, grant amendments) | Already used by `gap_midyear.py`. The ward transfers are $500 type moves and are in `7x7d-3zgj`. |
| "Financial and Strategic Reform Options" (`reform_options.pdf`, 101 pages) | **The copy in `raw/gap` is stamped "CONFIDENTIAL - DRAFT - PREDECISIONAL AND DELIBERATIVE" and "[Publication website here]", October 2025, and `gap_fetch.py` does not fetch it.** Provenance unknown. Do not cite it. The Mid-Year Report refers to a published "Financial and Strategic Reform Options Report (2025)". Find that public version first. **Coordinator note (2026-10-01):** the EY report was publicly released on 2025-10-16 and was the subject of City Council hearings (see https://www.chicago.gov/content/dam/city/sites/committeeonthebudget/2025/BGO-Notices-2025/CBGO-NOTICE-AGENDA-SMH20251110.pdf). The local copy is a pre-release draft (author metadata EY Parthenon, dated 2025-10-14), so it may differ from the final. Cite only the published version, and download it from chicago.gov. It is high value for "what could be cut" context. |
| 2027 Budget Forecast (`forecast_2027.pdf`) | Already used by `pensions_debt_fetch.py` and `pensions_debt_build.py` (untracked scripts). |
| Combined Amendment Package, round 2 (`amend_pkg_rd2_2026.pdf`, 8 pages) | Line-level changes between the Recommendations and the ordinance: Finance General `.929E` Community Violence Intervention +$18,000,000, DFSS Delegate Agencies $3,940,000 to $5,890,000, Library Fund proceeds of debt $126,291,928 to $125,926,011, advance pension payments cut (Municipal $141,787,975 to $128,823,928, Police $77,833,884 to $70,717,328, and others). The same differences can be computed from `axxr-vais` vs `6694-f78c`, which `reconciliation.md` already did. |
| OBM 2026 Budget Engagement Report (33 MB PDF, 200) | Resident survey results. Context for a kids' site, no dollars below $1M. Low value. |
| OIG Information Portal "City Finances" dashboards (https://igchicago.org/information-portal/city-finance-dashboards/, 200) | Dashboards over City purchase agreements and TIF. Built on the Contracts and TIF datasets we already use. |
| Cook County Clerk TIF reports page | Page loads. County side of TIF. City TIF datasets cover our need. |
| DoIT MCA Contracts `g8y8-fryq`, Contracts PDF Present `kzv2-52bx`, Number of Employees by Department chart `atdi-52tt`, salary/hourly/part-time filters of `xzkq-xp2w` | Saved views of datasets we already use. |
| Employee Reimbursements Through Payroll `tnbd-5zz7` (95,612 rows) | Not the same as `g5h3-jkgt` (5,870 rows, $10.8M). Likely small travel and mileage claims. Not read. Low value. |
| Lending Equity, Lobbyist, FOIA logs, Business Licenses, Taxi, Performance Metrics 2011-2012, Budget Survey 2020/2021 (`drbg-ny73`, `h6r6-h5c9`) | Not budget spending, stale, or both. |
| Employee Indebtedness to the City `pasx-mnuv`, Contractor Business Diversity `a5x7-5y4m` (400 rows), Illinois Income Tax LGDF `czxm-mzs7` (19,559 rows) | Not spending. LGDF is state revenue sharing by local government (columns suggest foregone revenue by year). Relevance not checked. |

## 5. Catalog scan method and result

Files: `raw/gap/catalog_all.json` (2,024 assets in the portal catalog) and `catalog_admin_finance.json` (302, "Administration & Finance" category). I compared every 4-4 character dataset id against IDs mentioned in an earlier planning draft, `research/*.md` and `scripts/*.py`. Then I filtered unused datasets by name, by description (budget, expenditure, appropriation, spending, "amount paid") and by column names containing amount, cost, payment, paid, fee, fine, salary, budget, expend or award.

Result: no unused dataset is a *spending ledger* for the City. The only unused ones with dollar columns that touch City spending are ARPA expenditures (row 5), the incentive datasets (row 4), `tnbd-5zz7` reimbursements, and the fines and enforcement sets (row 13). The Payments dataset `s4vu-giwb` has these columns only: amount, contract_number, vendor_name, voucher_number, department_name, check_date. It has **no funding-line or appropriation field**, which is why row 9 (Tableau) matters. Everything else in the portal is operational (permits, 311, crashes), or a saved view of a dataset we use.

## 6. Verification log (what I actually did)

- API calls today (HTTP 200 with data): `7tg5-i782`, `m9g9-cj96`, `9v3e-pcjs`, `iekz-rtng`, `a5x7-5y4m`, `g8y8-fryq`, `umwj-yc4m`, and count queries for all 15 appropriations and positions ordinances in section 3 row 2, `tnbd-5zz7`, `czxm-mzs7`, `6br9-quuz`, `pubx-yq2d`, `kc9i-wq85`, `yqn4-3th2`.
- Sums and counts computed server-side or from local files: ARPA ledger, incentive datasets, vacancies, CPS supplier payments by year, Cook SSA rows.
- Files opened and read: Budget Floors, Mid-Year Report pp. 4-5, 16-17, 24-25, 44-46, 57-65, amendment package, the Q1 QBR, the August revenue report, the August efficiency report, `reform_options.pdf` cover and executive summary, the Cook xlsx.
- URLs returning HTTP 200 (bytes where noted): CPS FY2027 book (7.7 MB), CPS FY25 ACFR (2.1 MB), CPS 2025B/C official statement (5.5 MB), CPS budget-2027, capital-expenditures, covid-19-spending, official-statements, report-of-the-chief-financial-officer and annual-financial-report pages, Monthly Revenue Reports for May and August 2026, Monthly Efficiency Report August 2026, Budget Recommendation Book (6.1 MB), Engagement Report (33 MB), Park District Recommendations book (13 MB), Park District participatory budgeting page, Legistar bodies and attachments endpoints, Bonfire list endpoint, OIG city finance and employee dashboards pages, Cook Clerk 2025 tax rate report PDF.
- Failed: Cook Clerk 2025 agency rate xlsx (404). Tableau CSV export guesses (404, bot challenge).
- Not verified: Tableau dashboards' data (rows 9, 14), CPS BI FY27 and capital expenditure reports, the origin of the two CPS sheet CSVs, column stability of the 2011-2023 budget datasets, and the 2024 estimate of taxes to be levied PDF linked from the CPS finance page.

## 7. Suggested order of work

1. Workforce Vacancies join (S) and budget history totals by department (S).
2. TIF and incentive leaves (S), ARPA ledger leaves (S), Cook SSAs and levy table (S).
3. Decide on CPS FY2027, then fetch the FY27 BI and the FY25 ACFR (M).
4. Parse the Mid-Year Report tables (M), then ask OBM, or run a browser session, for the Data Directory extract (L).
