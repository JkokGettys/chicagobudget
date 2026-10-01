# Chicago Public Schools FY2026: data sources and depth

**Bottom line: school-level and line-item data is obtainable with no browser.** The CPS Oracle BI portal exposes a public SOAP web service for the same guest account CPS publishes. One script pulls the whole FY2026 budget at **unit x fund x program x account** grain (159,589 rows, 976 budget units including 517 schools), and it ties out to the penny with the official $10.25B and $8.66B operating totals.

## 1. Primary source: CPS Budget BI portal (OBIEE 12c)

- Portal: `https://biportal.cps.edu/analytics/saw.dll?Portal...` with guest login `cpsbiguest` / `hell0cpsb1` (published by CPS on cps.edu).
- **Plain curl does not work for the UI**: saw.dll returns "browser not supported" without a browser User-Agent, and the Go/Catalog URLs only render a JavaScript shell.
- **What works**: the SOAP endpoint `https://biportal.cps.edu/analytics-ws/saw.dll?SoapImpl=<service>` (WSDL at `/analytics-ws/saw.dll/wsdl/v12`). Services used: `nQSessionService.logon`, `webCatalogService.getSubItems/readObjects`, `metadataService.describeSubjectArea`, `xmlViewService.executeSQLQuery/executeXMLQuery/fetchNext`. We send **logical SQL** straight to the subject areas, so we are not limited to what the interactive reports show.
- Client: `scripts/cps_obiee.py`. Fetchers: `scripts/cps_fetch.py` (budget), `scripts/cps_fetch_capital.py` (capital projects).
- Catalog walked: `/shared/CPS FY26 Budget/...` (about 90 saved reports, `_portal/Chicago Public Schools FY26 Budget Interactive Reports`), also FY14 to FY25 and **FY27** folders (FY27 budget is already staged, last modified 2026-08-07). Catalog listing saved at `raw/cps/catalog_fy26.txt`.
- Subject area `"CPS FY14 Budget Book"` holds **FY2014 through FY2027** (the name is legacy). Dimensions: Unit (6 to 7 level hierarchy), Account (6 levels), Fund Grant, Program, Positions (job title), Revenues. Measures: Original Budget, Current Budget, Encumbered Expenses (projected spend), New Budget Amount (FY26 approved), FTEs, Prior Adopted, Prior Approved, Prior Expenditures. Gotcha: every dimension has its own `Budget Year` column and you must filter all of them (Unit, Account, Fund Grant, Program), otherwise rows multiply. Column nulls are omitted from SOAP rows, so the parser pads to the SELECT width.
- Large 4-dimension pulls crash the server (`std::bad_alloc`), so `cps_fetch.py` chunks by unit-code prefix. Full run takes about 5 minutes.
- Subject area `"CPS Capital Budget"` holds the capital program (FY14 to FY26) by project.
- Data is **unauthenticated public guest data**. Nothing here is personal.

### Files produced (raw/cps/, gitignored)
| File | Rows | Grain |
|---|---|---|
| `cps_2026_dim_unit.csv` | 2,690 | Unit code, name, type (CPS Public School / Charter / AUSL / Central Office / City Wide...), grade type, 6-level parent hierarchy (Board > CEO > School Networks > Network N > school) |
| `cps_2026_dim_account.csv` | 525 | Account code, description, group (Expenditures/Revenue), subgroup (Salary, Benefits, Contracts, Commodities, Equipment, Transportation, Contingencies), levels |
| `cps_2026_dim_fund.csv` | 5,858 | Fund/grant code, description, fund group, subgroup, parent fund |
| `cps_2026_dim_program.csv` | 1,338 | Program code, description, ISBE state function code |
| `cps_2026_exp_unit_fund_account.csv` | 154,683 | unit x fund x account, with FY26 approved, FY26 FTE, FY25 adopted, FY25 ending, FY25 projected spend |
| `cps_2026_exp_unit_fund_program_account.csv` | 159,589 | **deepest grain**: unit x fund x program x account, FY26 approved + FTE |
| `cps_2026_positions_unit_job.csv` | 10,441 | unit x job title: FTE and budgeted salary (FY26) |
| `cps_2026_rev_fund_account.csv` | 154 | revenue by account x fund (district level only, not by school) |
| `cps_2026_capital_projects.csv` | 1,559 | project level capital budget, all project years, with school (unit), category, type, source, status |
| `cps_roster_dept_job.csv` | 10,708 | public employee position roster (12/31/2025) aggregated to department x job title (names dropped) |
| `cps_isbe_2025_school_finance.csv` | 622 | ISBE Report Card finance tab, CPS district + 621 schools |

## 2. Reconciliation (all computed from downloaded CSVs)

| Check | Result |
|---|---|
| FY26 approved expenditure total, 3 grains (unit x fund x account; unit x fund x program x account; direct logical SQL) | **$10,253,327,463.68** each time. Matches the $10.25B headline. |
| Per-unit sums, 2 grains | 0 mismatches across 976 units |
| FTE | 44,957.4 (sum of FY26 Approved Positions in the BI data, the budget-book count was not separately checked) |
| General Operating Funds | **$8,657,039,687.42** = the $8.66B operating budget |
| Debt-Service Funds | $1,040,342,455.26 |
| Capital Funds | $555,945,321.00 (capital project list for project-year 2026 sums to $555,941,447, a $3,874 difference, likely rounding or a late amendment; unexplained, do not hide) |
| By account subgroup | Salary $3,860.40M, Benefits $2,287.79M (+ $300 stray), Contracts $1,671.88M, Contingencies $1,319.30M, Equipment $568.06M, Commodities $363.85M, Transportation $182.02M, Others $19,000. Salary $3.86B and benefits $2.29B agree with the category totals quoted in the task brief. |
| Revenue (leaf accounts) | $9,389,861,911 = $9,364,861,911 total revenues + $25,000,000 fund balance appropriated. Revenue here is the operating funds only, it is not meant to equal $10.25B. Local $4.24B property tax net, EBF $1.82B, etc. |
| Positions file (FY26) | 44,957.4 FTE and $3,670.06M salary rows, same FTE as the budget fact table. |

Caveat on "$10.25B": it includes $1.04B debt service and $0.56B capital, and some inter-fund items. We did not look for double counting inside CPS (for example the City-funded pension line shows in both revenue and expense). Flag if the site wants a net figure.

## 3. How deep does it go?

Budget-line nodes at each grain (FY26 approved, nonzero rows):

| Grain | Nodes | Nodes >= $1M | Share of $ sitting in >= $1M nodes |
|---|---|---|---|
| Unit | 976 | 722 | 99.9% |
| Unit x account | 26,085 | 1,302 | 86.6% |
| Unit x fund x account | 154,683 | 1,172 | 71.1% |
| **Unit x fund x program x account** | 159,589 | **698** | **56.8%** |
| Unit x job title (positions) | 10,441 | 864 | 60.5% of the $3.67B salary $ |

So 99.6% of 159,589 leaf rows are already under $1M, but 56.8% of dollars still sit in 698 big rows. Where they are (>= $1M leaf rows, $M): City Wide units 209 rows $4,580M, Charter schools 80 rows $668M, central office 75 rows $197M, **CPS public schools only 211 rows $311M** (so school budgets drill below $1M almost everywhere).

The remaining big rows are mostly central, with nothing deeper in this dataset, e.g. CTPF pension levy $602M, Future Series Bond 2024 capitalized construction $500M, bond principal and interest lines ($254M, $51M, $49M...), ESP pension $203M, hospitalization $162M, special ed transportation $147M, PBC facilities O&M $147M and $65M, Grant contingency $120M and $50M, state Pre-K payments $88M, special ed tuition $67M. For these:
- Debt: each bond series is its own fund line (e.g. "CIP Series 2009G"), so it is already at bond level. ACFR has the debt schedule.
- Pensions: CTPF ACFR gives members and retirees (see section 5).
- Facilities: capital project list and PBC lease give project level.
- Contingencies ($1.32B) are placeholders with no deeper public data: label as "money held back, not yet assigned".
- Charter schools: each is one unit, up to $49.5M, rows are mostly per-pupil payments by account. No internal charter budget is public in this source.

### The school layer
- 517 units of type CPS Public School (484), AUSL (23), Alternative (5), Contract (5). 508 have >= $1M in FY26, total $4,208M. Charter 76 units $715M. Non-public school units exist but carry $0 (these are scholarship/placeholder units).
- Hierarchy in the Unit dimension: Board of Trustees > CEO > School Networks ($5,276M) > Network 1..17 / Charter Schools Network ($956M) / Independent Schools Network ($384M) > school. Other level-3 offices: Chief Operating Officer $1,562M, Pensions and District-Wide Set-Asides $1,289M, Finance $1,109M, Chief Education Office $905M, Talent $63M, Law $15M.
- Example school (Beulah Shoesmith, U25371): lines like Regular Teacher salaries $1.60M (16 FTE) split further by fund, program, and job title (18 Regular Teachers $1.79M, 5 Special Ed Teachers $0.48M, 1 Principal $157,496...).

### Positions and salary depth
- Positions by unit x job title are in the BI data. The CPS **Employee Position Roster** (cps.edu, XLS, 48,806 positions, includes names) is also public. Dept IDs in the roster map 1:1 to BI unit codes (all 657 dept IDs match `U<dept id>`). The roster XLS covers 12/31/2025 and has total $3.756B FTE annual salary, vs FY26 budgeted salaries $3.670B in positions (different dates, vacancies and rate changes: do not expect equality). We aggregate and drop names to avoid publishing individuals. If the site wants "X people x $Y", use `cps_roster_dept_job.csv`.

## 4. Other sources found (URLs)

| Source | URL | Format | Notes |
|---|---|---|---|
| FY2026 Budget Book | cps.edu/globalassets/cps-pages/about-cps/finance/budget/budget-2026/docs/fy2026-budget-book-final-approved-1.2.pdf | PDF | central departments and categories only, not deeper than BI |
| FY26 hearing decks, department narratives | same folder: `081925cpsbudget_1st-hearing.pdf`, `081925cpsbudget_full_2nd-hearing.pdf`, `fy2026_department_narratives.pdf` | PDF | department plain-English descriptions for the site |
| Employee Position Roster (quarterly since 2013) | cps.edu/globalassets/cps-pages/about-cps/finance/employee-position-files/employeepositionroster_12312025.xls (also `_12312024.xls`, `_09302024.xls`, ... back to 2013) | XLS | pos #, dept ID, FTE, class, salary, benefit cost, job code, title, name. Fetcher: `scripts/cps_fetch_roster.py` |
| ISBE Illinois Report Card 2025 public data set | isbe.net/_layouts/Download.aspx?SourceUrl=/Documents/2025-Report-Card-Public-Data-Set.xlsx (40 MB, tab "Finance") | XLSX | per-pupil spending by school, FY2024 school-year actuals. Fetcher: `scripts/cps_fetch_isbe.py`. CPS district: 327,467 enrollment, total expenditures SBER $8.910B, AFR $9.151B, per pupil $19,798. 621 schools, 619 with per-pupil data (includes charters). Weighted per-pupil x enrollment for schools = $6.38B, i.e. site-level plus central allocation, not the full district total. School name join to BI units needs a crosswalk (RCDTS vs unit code). Not done. |
| CPS FY2025 ACFR (audited) | cps.edu/about/finance/annual-financial-report/ ; ACFR text posted by CPS on publicnow.com; Board action 26-0423-CO1 (cpsboe.org) | PDF | actuals vs budget, debt schedules, pension notes. Not parsed yet. FY2025 popular report: cps.edu/globalassets/cps-global-media/banner-images/annual-financial-report/fy2025_pafr-7.22.26.pdf (3.3 MB, HTTP 200) |
| CTPF Annual Comprehensive Financial Report 2025 | ctpf.org/forms-publications/financial-investments-reports/annual-comprehensive-financial-report-acfr | PDF | members, retirees, average benefit, employer contribution. Not parsed yet |
| CPS capital plan | BI subject area "CPS Capital Budget" (done) | SOAP | project-level |
| Board of Education actions | cpsboe.org/content/actions/... | PDF | budget resolutions, contract approvals |

## 5. Gaps and next steps
1. **No school-level revenue.** Revenue is district-wide by account and fund only.
2. **Actuals by school**: BI has FY25 projected expenditure and FY24 expenditures per unit x account (measures `Encumbered Expenses`, `Prior Expenditures`); already in `exp_unit_fund_account.csv` for FY25 projected. FY24 actuals can be pulled the same way (not done).
3. **History**: the same subject area spans FY2014 to FY2027, so a multi-year school trend is one parameter change (`python3 scripts/cps_fetch.py 2025`). Note the FY27 budget is already in the catalog.
4. **ISBE crosswalk, ACFR, CTPF**: not parsed. ISBE gives an independent per-pupil check on the school layer, ACFR gives actual spending, CTPF gives retiree counts.
5. **Unit labels with no type** (147 units, $772M): mainly Charter Schools Network ($239M), College & Career Success ($134M), OSD ($129M), network offices. Treat as central programs. Unit type is blank in the source.
6. Budget facts are stored only at leaf units, so the CSVs do not double count (verified: they sum to the total). The dim_unit file also lists roll-up ("... Total", Leaf Unit = 0) units, use its parent columns to build the tree.
7. Accounts named "Budget Only - ..." (for example "Budget Only - Pensions") are budget-only accounts that CPS uses for central set-asides, not actual payments.
8. Credential hygiene: the guest password is public from CPS, so it is hardcoded in `cps_obiee.py`. If CPS rotates it, update the constants.
