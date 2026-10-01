# CPS FY2026: pushing the big nodes below $1M

Builds on `research/cps.md`. All numbers below were computed from the files named, nothing hand-typed unless marked "from PDF". Reproduce with the `scripts/cps_*.py` files listed at the end.

## 0. Bottom line

| | Share of the $10,253,327,463.68 in leaves under $1M |
|---|---|
| **Before** (BI unit x fund x program x account, 159,589 leaves) | **43.2%** ($4.433B). The 39% figure in the task brief was not reproduced. 43.2% is computed directly from the CSV. |
| **After**, adding only what public data can support (upper bound) | **54.8%** ($5.620B) |
| Left at >= $1M after all of this | ~45% of $ (includes -$470M of negative budget-only offset lines) |

The "after" number is an upper bound, because two of the four steps (job-title and roster splits of salaries) allocate public people data onto budget lines without a dollar-for-dollar tie. Table in `data/cps_depth_summary.csv`:

| Step | + $ moved under $1M | Tie to budget? |
|---|---|---|
| A. already < $1M | $4,433.0M | exact |
| B. capital: 131 named projects (72 of them < $1M) plus phase splits of 31 projects | + $75.8M only | project list $555,941,447 vs capital fund lines $555,945,321 (**$3,874 gap**, unexplained) |
| C. salaries: BI "unit x job title" rows (10,441, 864 still >= $1M) | + $345.1M | bound, positions file has no fund dimension |
| D. remaining salaries and school-side benefits: public CPS roster (highest single position is $335,000 FTE salary, so every person-level leaf is < $1M) | + $766.3M | approximate, roster is 12/31/2025 and totals $3.756B vs budgeted $3.670B |

What does **not** move: pensions, debt, charter tuition, capital and the vendor contract money (all explained below). 14.8% of dollars (139 leaves, $1.52B) are contract, utility, food, transport and contingency lines. Vendor payments exist per vendor, not per budget line, so these cannot be tied exactly.

## 1. Pension & Liability Insurance, City Wide ($1,102.7M, unit U12470)

File: `data/cps_pension_insurance_fy26.csv` (37 BI lines). Valuation facts: `data/cps_ctpf_valuation_2025.csv`.

| BI line | $M | What it is |
|---|---|---|
| Budget Only - Pensions, fund "CTPF Pension Levy" | 602.31 | property-tax levy paid to CTPF. Budget book p.35 says the levy raises $602.3M. |
| Budget Only - Pensions, General Education Fund | 120.57 | **Reservation, not a payment.** $120.57M less $59.31M = $61.26M, which equals the **$61.3M operating diversion** in budget book p.35. The other $59.31M is unexplained here: it equals the State's $363.09M less the $303.78M of teacher employer pension charged at school level (A57105 + A57110), but this is arithmetic, not a documented explanation. |
| Budget Only - Pension - ESP | 202.79 | non-teacher employer pension, see MEABF below |
| Budget Only - Hospitalization (two programs) | 166.83 | central health insurance reserve, $161.67M + $5.16M |
| Workers comp (net -11.57), unemployment (net -5.61), claims $11.17M, termination payouts $9.2M, other | rest | small lines, 22 of 37 lines are < $1M |

### CTPF (teachers), actuarial valuation 6/30/2025 (from PDF `ctpf.org/sites/files/2025-10/CTPF_FundingVal_2025_Final.pdf`, Executive Summary p.1, Table 11 p.44, State contribution table in Section C)
- FY2026 required employer contribution **$1,026,660,000** = Board of Education required $646,234,000 + Board additional (0.58% of pay) $17,332,000 + State additional (0.544% of pay) $16,256,000 + State normal cost $346,838,000.
- FY2027 required: $1,014,523,000 (Board $628,527,000 + $18,002,000; State $16,884,000 + $351,110,000).
- Members at 6/30/2025: 34,647 active (average salary $84,796), 23,350 retirees (average annual benefit $64,860, total $1,514,469,736), 408 disabled retirees, 3,399 beneficiaries, 7,135 vested inactive, 29,793 non-vested inactive.
- Assets and debt: actuarial accrued liability $27,190,208,516, actuarial assets $13,016,274,343, **UAAL $14,173,934,173, funded 47.87%** (market-value basis 50.23%).
- Normal cost vs unfunded: total normal cost $553.9M, of which employer share $283.4M ($348.4M with the $65M retiree health subsidy). Actuarially determined contribution would be $1,546.5M, statutory requirement is $1,014.5M (FY27).

**Tie to the BI budget** (computed from `cps_2026_exp_unit_fund_account.csv`): teacher pension accounts A58115 + A57105 + A57110 + A57135 = **$1,160.594M**, and CTPF total employer $1,026.660M + employee pickup in A57135 $133.934M = $1,160.594M. The whole teacher pension chain across the district, central and school, ties to the cent. The school-level pieces (A57105, A57110, A57135) are already below $1M per school. Only the $602.3M levy and $120.6M reservation are big leaves, and the CTPF valuation supplies the split of those two into **Board required vs State normal cost** (the State's $363.1M is paid by the state and appears on the revenue side, not as an expense here).

### MEABF (non-teacher staff) and the $175M
- BI: Budget Only - Pension - ESP **$202.79M** plus school-level ESP employer lines A57210 and A57215 = **$306,588,146**, and the revenue account A41310 "City Of Chicago Pension Contributions" is **$306,588,146**. So this is the on-behalf payment the City makes to MEABF for CPS non-teachers, booked as revenue and expense, exactly as budget book p.39 describes. It is not CPS cash.
- The **$175M** MEABF reimbursement to the City is **not in the budget**. Budget book pp.10, 39 state it is contingent on extra FY2026 state money or TIF surplus above the $379M assumption. No BI line carries it. Show as "$0 budgeted, up to $175M contingent".

### Insurance
- General liability premium $14.80M and claims $16.04M district-wide (accounts A54530, A54535). $11.17M of claims sits in this unit, $14.80M of premium in Risk Management (U12460). No carrier-level split is public in the budget. FY26 supplier payments to insurance-related vendors: Mesirow Insurance Services $14.1M and Cannon Cochran Management $46.4M (third-party claims administration, $120M authorized 1/2026 to 12/2029, in `cps_contract_awards_fy21_27.csv`). Standard Insurance $16.0M was paid in FY26 but its coverage line was not verified.
- Health: central hospitalization reserve $166.83M plus employer hospitalization in every unit ($514.57M, account A57305). FY26 supplier payments: **HCSC $550.0M**, CVS Caremark $174.7M, Delta Dental $20.8M. These are one vendor each, so health care is a named-vendor leaf.

Leftover: $722.9M "Budget Only - Pensions" and $202.8M ESP pension remain >= $1M. Their floor is the CTPF/MEABF actuarial numbers above: "34,647 active teachers, 23,350 retirees at $64,860 average" is as deep as public data goes.

## 2. Debt Services, City Wide ($1,040.3M, unit U12480)

Done to the bond-series level. File `data/cps_debt_by_series_fy26.csv` (34 funds, built by `cps_deep_debt.py`): one row per bond series with FY26 principal, interest, outstanding principal at 6/30/2025, fixed rate, final maturity and pledged source (from the budget book Tables 3 to 6, pp.225 to 230).

Tie-outs: BI principal **$494,481,180.40**, interest **$545,361,274.86**, fees $500,000 vs budget book Table 2 principal $494.5M, interest $545.4M, fees $0.5M, total **$1,040.3M**. The 33 series parsed from Table 3 sum to $9,083,805,522 outstanding, the printed total. Largest FY26 items: 2009G $256.5M (final maturity, paid from a sinking fund, so not new operating cost), 2016A $50.8M interest, 2018C $62.0M, 1998B-1 $59.0M, CIT 2016 $43.5M.

By pledged source: EBF $661.9M, IGA/PPRT $121.6M, CIT levy $79.7M, EBF/Federal subsidy $74.5M, IGA $43.6M, EBF/PPRT $36.0M, EBF/IGA $22.5M. Budget book p.222 says only about $395M of the total is paid from operating revenue, the rest was set aside the year before.

Of 45 BI rows in this unit, 44 are >= $1M. The only one < $1M is the $0.5M COP fee line. Splitting each series into principal and interest is the finest level in the budget system, and 10 of the 34 series total less than $10M. Below this level the items are payments to bondholders. **What is not available from this pass**: individual EMMA official statements and trustee payment schedules, and CPS Investor Relations pages (`cps.edu/about/finance/investor-relations` returns 404). The EMMA site returns HTTP 200 but I did not attempt document retrieval. Short-term borrowing: $450M TANs 2024A outstanding, about $23.2M appropriated for TAN interest in the operating budget (p.222), not in this unit.

## 3. Capital / Operations, City Wide ($556.6M) and the 1,559 projects

`cps_2026_capital_projects.csv` had 1,559 rows because it covers every project year since 2006 ($9.12B). For the FY26 budget year (Dim - Capital "Budget Year"=2026 and "Project Budget Year"=2026) there are **131 projects totaling $555,941,447**. In `data/cps_capital_projects_fy26.csv`, each with unit, school name, category, type, status, ward, alderman, source and a link to its public project PDF (`schoolreports.cps.edu/capitalplan/...`).

- Where it sits in the operating BI data: all of it is in unit Capital/Operations City Wide U12150 and four capital funds: Future Series Bond 2024 **$500.23M**, IGA and Other Capital $25.70M, Other State Capital Grants $25.00M, E-Rate $5.02M. Total **$555,945,321**.
- By category ($M): Facility Needs 340.7, IT/Security/Other 118.5, Educational Programming 28.7, Site Improvements 28.3, Management 23.0, Interior 16.7. By source: Needs Assessment 284.2, District Priority 177.3, External Funding 55.7, Others 33.0.
- 59 projects are >= $1M ($515.8M). The biggest: IT centralized $108.0M, emergency facility repairs $80.0M, state-outside-funded $25.0M, project support $23.0M, Gately Stadium $10M x 2. 72 projects are < $1M ($40.1M).
- Budget-year project PDFs exist for all 131. **31 PDFs carry a design/construction/environmental/management split** (e.g. King ES roof: $4.38M = design $438,000 + construction $3,482,100 + environmental $219,000 + management $240,900), and those phases sum exactly to the project budget for all 31. The other 28 big projects have no phase split. Examples are programs spanning many schools ("ADA program $9.86M", "Fire alarm replacement $15.0M"), whose PDFs list school names but **no per-school dollars**. Per-school dollars may exist in the Capital Expenditure subject area (project number x unit, FY26 expenditure, `/shared/CPS FY26 Capital Expenditure`), not pulled in this pass.
- School-side detail: 105 distinct unit codes, $209.7M at CPS Public Schools, $190.4M at citywide units, $113.0M central office, $20.0M stadium.
- Effect on depth: only +$75.8M moves under $1M. Project Type "Contingency" alone is $80.0M and "IT Initiatives" $113.0M, neither of which has a school-level split.

## 4. Vendor contracts: FOM, transportation, nutrition, OSD

**New and important: CPS publishes procurement data as JSON.** The pages at cps.edu/procurement/supplier-payments and /contracts-awarded are an Angular app (`schoolinfo.cps.edu/ProcurementWeb`) over an open JSON API at `https://api.cps.edu/procurement/` (no key, found in the app's JS bundle):
- `Supplier/GetSupplierPayments?reportyear=<FY>`: one row per vendor per fiscal year with total paid (FY2001 to FY2027). FY2026: 4,631 vendors, **$3,557.1M**, 278 vendors >= $1M hold $3,333.4M (93.7%). `data/cps_supplier_payments_fy2024/25/26_over1m.csv`.
- `contracthistory/GetContractAwards?reportyear=<FY>`: Board-approved contracts with Board Report number, vendor, amount, authorized amount, term. FY2021 to FY2027 = 1,464 awards, $10.7B authorized, in `data/cps_contract_awards_fy21_27.csv`. Each links to the cpsboe.org Board Report PDF, from which the script parses the sponsoring department code ("USER INFORMATION: 11880 - Facility Opers & Maint"), and these 5-digit codes equal BI unit codes (U11880). 315 of 1,464 awards carry a parseable department. 589 awards have no Board Report (delegated authority), 165 point to dead cpsboe.org PDFs, 395 PDFs lack a department block.
- Caveats: payments are per vendor, not per budget unit or program. A vendor can serve several units. CPS does not document the accounting basis of these totals (likely payments made in the fiscal year), and vendor rows are not budget lines. **Do not claim a tie.**

| Unit (FY26 budget) | Biggest budget accounts | Vendors that are public | Notes |
|---|---|---|---|
| Facility Opers & Maint U11880 ($483.0M) | Services: non-technical/laborer $163.8M, career-service salaries $113.8M (incl. $44.5M budget-only), electricity $86.1M (purchased $43.9M + transmission $42.2M), repair contracts $25.1M, gas $33.0M | **Jones Lang LaSalle $139.4M paid FY26** (facility management and building engineering. Authorized renewals: $299.6M for 7/2024 to 6/2026 (amends Board Report 24-0926-PR2) and $328.9M for 7/2026 to 6/2028), Constellation NewEnergy $37.4M + Gas $12.5M, ComEd $35.9M, Peoples Gas $17.8M, Cintas $22.8M (custodial supplies, $44.75M 10/2024 to 9/2027), Diverse Facility Solutions $7.4M, Total Facility Maintenance $5.8M. Custodial services were awarded to Aramark Management Services LP ($391M, 8/2021 to 6/2024), but no FY26 payment row under that name was located |  In-house: 2,464 roster positions, $101.7M. Custodial Workers 2,120 x $38,947 average = $82.6M. 23 roster job rows, only 6 job groups >= $1M. |
| School Transportation U11940 ($198.8M) | Pupil Transportation $166.0M, salaries $22.3M | 15 payment rows under bus, medical-transport and fleet vendor names paid **$159.0M** in FY26 (name match, may miss or over-include): Illinois Central School Bus $29.1M, Sunrise $26.2M, Alltown $22.3M, A.M. Bus $16.9M, First Student $15.2M, SCR Medical Transportation $12.4M, Compass $11.5M, United Quick $5.4M, Reliant $5.3M, Ammons $3.6M, Conway $3.2M, BJ's $1.8M... | The pooled bus contract (Board Report 22-0727-PR19, vendors selected under RFP 22-073, term to 7/31/2023, later renewals) lists 16 vendors but **no per-vendor amounts**. In-house: 696 School Bus Aides at $30,238 = $21.0M. CTA IGA $37.5M (2023 to 2028) is in unit 11870 Student Transportation. |
| Nutrition U12050 ($123.5M) | Food supplies $98.9M, donated food $11.7M, salaries $5.4M | Aramark Educational Services $69.4M (the 2021 renewal, $105M, is for "food service management services"), Trimark Marlinn ($6.0M renewal 7/2026 to 6/2028, $14.85M 2023 agreement, only $0.49M paid in FY26 under this name) | Open Kitchens ($26.1M paid FY26) is a likely meal vendor but I found no award record linking it to this unit. Vendor to unit link is not verifiable from the API. In-house: 106 positions $3.8M. |
| OSD RSP U11675 ($239.6M) | Teacher salaries $178.0M, hospitalization $20.5M, pensions $26.4M | Mostly **people, not vendors**: 1,748 roster positions: 678 School Social Workers x $96,192, 485 Speech Pathologists x $95,142, 262 School Psychologists x $106,002, 231 Occupational Therapists x $96,442 | Related OSD spending on private placements (Camelot Therapeutic Schools $19.3M, Menta Academy $14.7M, Pathways in Education $19.4M) is in the Instructional Supports unit U11674 ($101.1M), not RSP |

For these 4 units, **$1.045B total budget**. Vendor lines are named at the vendor level. This is real depth but the vendor to budget-line link is by inference. Treat as "vendors paid in FY26 related to this department" not as a split of the budget. Vendor-level payments also exist for 278 vendors >= $1M for general browsing.

The **Illinois Comptroller** (Warehouse/Illinois Open Checkbook) was not checked. CPS is a local government and its vendor data is already in the CPS API above. The Comptroller records state payments to CPS, not CPS spending.

## 5. Charter schools ($955.5M, 137 units with tuition)

File `data/cps_charter_by_school_fy26.csv`: per charter campus FY26 "Student Tuition - Charter Schools" budget, enrollment (CPS School Profile API `api.cps.edu/schoolprofile/CPS/AllSchoolProfiles`, 641 schools, FinanceID matches the BI unit code), per pupil.
- **137 units carry tuition, totaling $976.0M. 109 are >= $1M ($975.5M)**. 28 units are < $1M, and 25 of those are $0 (reason not established, three charter closures are listed in the budget book). Each charter campus is one BI unit, so "per-charter amounts" are already unit rows. They are not < $1M each, because a campus is $10M to $50M.
- Enrollment match: 114 of 137 units have a profile record. Among 94 campuses with >= 50 students and non-zero tuition, per pupil tuition ranges $9,977 to $45,256 (median $18,286), consistent with the budget book PCTC floor of $17,606 (independent facility) and $14,807 (CPS facility). Outliers are alternative and special programs (e.g. Youth Connection). Do not publish outliers without checking the profile enrollment.
- Budget book Table 4 (p.42): all charter and traditional contract schools $933.3M. Our $955.5M (all lines in charter units and the Charter Schools Network group) is not reconciled to the $933.3M. **Do not state they tie.**
- Payments cross-check (supplier payments FY26): Noble Street $197.4M paid vs $210.8M budgeted in Noble units, Acero $102.1M vs $115.7M, KIPP $49.0M vs $56.6M. Chicago International Charter School paid $121.1M is under a "Charter School Foundation" legal name, which the name search missed ($120.9M budgeted). Charter operators run many campuses, so paid amounts are per operator.
- The per-pupil tuition formula (PCTC) is in the budget book Appendix B, Table 5a (p.247): PCTC $20,352.85, 97% match $19,742.27, less on-behalf-of long-term debt $2,798.94, short-term debt $46.11, pension $2,089.80, direct minimum $17,606.36 (independent facility) or $14,807.42 (CPS facility). Special ed within PCTC is $4,098.83 per pupil.
- The **"Charter Schools Network" level-4 group ($238.8M)** that had a blank Unit Type in `cps.md` contains 46 charter campuses whose Unit Type is blank (e.g. Noble Speer, KIPP One). Together with the 76 typed charters, the group totals $955.5M.

## 6. Actuals vs budget

`scripts/cps_deep_actuals.py <Y>` pulls adopted, ending and actual spend per unit x fund x account. In the dataset of year Y, "Prior" measures are Y-2 actuals, "Original/Current/Encumbered" are Y-1 adopted, ending and projected. Files: `raw/cps/cps_2026_actuals_unit_fund_account.csv` (252,216 rows, FY24 actuals) and `cps_2027_actuals_unit_fund_account.csv` (FY25 actuals, "Encumbered" = FY26 projection). Also contains FY25 and FY26 numbers.

Totals (all funds, $M): FY24 adopted 9,430.0, ending 9,415.4, **actual 8,552.9**. By fund type FY24: operating adopted 8,489.5 / ending 8,478.0 / actual 7,632.1. Debt service 785.5 / 785.5 / 764.5. Capital 155.0 / 151.9 / 156.3. FY25 operating: adopted 8,433.0, ending 8,489.8, actual 5,798.7 (**FY25 actuals look incomplete: that data appears to be an in-year snapshot, so do not use it**). The audited FY25 operating (GOF) expenditure is **$8,459M** (CPS 2025 Popular Annual Financial Report p.12), vs the BI FY25 "actual" of $5,799M. FY24 BI operating actual $7,632M vs PAFR FY24 GOF $8,353M. **The BI "actual" columns understate audited GOF spending by about $0.7B (FY24) and $2.7B (FY25)**, cause not established. Use audited totals from the ACFR for top-level actuals, BI for unit-level patterns only.

Selected FY24 adopted/ending/actual ($M): Pension & Liability Insurance 1,084.3 / 1,080.1 / 985.2. Debt Services 785.5 / 785.5 / 593.0. Capital/Operations 153.8 / 58.5 / 27.6. Facility Operations 540.0 / 499.3 / 511.5. School Transportation 140.9 / 190.0 / 188.4. Nutrition 123.5 / 124.8 / 142.6. OSD RSP 277.8 / 258.5 / 238.1.

## 7. Sources and what we could not reach

| Sources used | URL |
|---|---|
| CTPF Actuarial Valuation 6/30/2025 | https://www.ctpf.org/sites/files/2025-10/CTPF_FundingVal_2025_Final.pdf |
| CTPF 2025 ACFR (downloaded, not parsed) | https://www.ctpf.org/sites/files/2026-01/2025%20ACFR_FINAL_v7.pdf |
| FY2026 Budget Book (pension ch. pp.34 to 39, debt pp.219 to 230, Appendix B, p.246+) | cps.edu/globalassets/cps-pages/about-cps/finance/budget/budget-2026/docs/fy2026-budget-book-final-approved-1.2.pdf |
| CPS Procurement JSON API | https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026 and .../contracthistory/GetContractAwards?reportyear=2026 |
| CPS School Profile API | https://api.cps.edu/schoolprofile/CPS/AllSchoolProfiles |
| Capital plan project PDFs | http://schoolreports.cps.edu/capitalplan/ (links in `cps_capital_projects_fy26.csv`) |
| Board Reports | http://www.cpsboe.org/content/actions/YYYY_MM/<number>.pdf |
| FY2025 Popular Annual Financial Report | cps.edu/globalassets/cps-global-media/banner-images/annual-financial-report/fy2025_pafr-7.22.26.pdf |

Not reached: EMMA official statements (needs browser; no CPS investor relations page found), full-text ACFR debt schedule (ACFR PDF was not downloaded, only the popular report), per-school capital dollars for the 28 multi-school programs, and Illinois Comptroller. No browser was used.

## 8. Recommendations for the site
1. Show the **54.8%** only as an upper bound, "under $1M after splitting salaries into job groups and people". For the other 45% label each node honestly: "Pension payment set by CTPF actuaries, 23,350 retirees", "Bond series 2016A, 5.00% to 2044", "Facility management contract with JLL, $139.4M paid".
2. Use `data/cps_debt_by_series_fy26.csv` and `data/cps_pension_insurance_fy26.csv` as ready leaves with source links to budget book pages.
3. Present vendor payments as a **separate "who got paid" view** (API data), not nested under budget lines, and note the basis is undocumented.
4. Ask the CPS finance team via FOIA for (a) FY26 payments by vendor x department, (b) per-school capital dollars for the multi-school programs.

## Scripts (all in `scripts/`)
`cps_obiee.py` (client), `cps_fetch.py`, `cps_fetch_capital.py`, `cps_fetch_roster.py`, `cps_fetch_isbe.py` (earlier), `cps_deep_capital.py` (projects + PDF phase parse), `cps_deep_debt.py` (bond series), `cps_deep_contracts.py` (procurement API + Board Report parse), `cps_deep_actuals.py` (budget vs actual), `cps_deep_depth.py` (before/after table), `cps_deep_pension_charter.py` (writes the `data/cps_*.csv` files).
