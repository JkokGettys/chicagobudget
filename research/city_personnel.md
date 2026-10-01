# City personnel: salary tree, turnover, overtime, wage adjustments (2026)

Reproduce: `python3 scripts/personnel_turnover.py && python3 scripts/personnel_book_lines.py && python3 scripts/personnel_overtime.py && python3 scripts/personnel_build.py`. The first three reuse caches in `raw/personnel/` (`raw/` is gitignored; the turnover script also needs `raw/gap/ord_2026.txt` from `scripts/gap_fetch.py`) and the build script makes no network calls. Output: `data/city_personnel_2026.json` (department > organization > division > section > job title, rate rows under each title). Every tie-out below is an `assert` in `personnel_build.py`. All dollar tables are in $ millions unless stated.

## Short answers

1. **The tree totals $3,592,099,097, exactly the ordinance's "Salaries and Wages - on Payroll" (account 0005) total.** All 106 local fund x department pairs tie to the dollar. The $3.92B positions dataset is $3,919,431,759. The $327.3M gap is: $104.2M of rows in the same dataset that belong to other accounts (0015, 0012, 0044), $215.6M of budgeted turnover printed in the ordinance, and $7.5M that only exists in grant funds and is not explained by any printed turnover.
2. **Overtime (0020) is budgeted at $421.6M for 2026 and was actually paid at $466.1M in 2025 and $509.3M in 2024.** The 2025 book budget was $226.1M, so 2025 ran at 206% of it. The 2026 budget roughly doubled to be near actuals. Police is $203.9M of the 2026 budget, Fire $93.4M, Water $47.1M.
3. **Scheduled Wage Adjustments (0003) is $387.7M in the ordinance, not $386M.** $283.0M sits in Finance General and $104.7M in Fire. The books describe it only as contractual raises for unions still being settled. In practice, payroll costing shows the same account being used to pay retroactive back pay and lump sums ($243.2M in 2025).
4. **Depth: 19.7% of position dollars are in job-title nodes under $1M, and 2.8% in section nodes under $1M.** If the 382 title nodes of $1M or more are shown as count x average (or hours x rate), 100% of dollars end in a unit under $1M. The largest average is $205,591.

## 1. The tree and the reconciliation

### What the positions dataset contains

`v2t2-vajc` has 8,243 rows. Each row is a title x fund x pay rate with `total_budgeted_unit` (count) and `budgeted_pay_rate`. The columns mean different things by pay basis, and the script asserts the rule on all 7,283 regular salary rows (0 exceptions):

* **Annual**: amount = count x annual rate.
* **Hourly rows with `position_control = 1`**: amount = count x hourly rate x 2,080 hours. With `position_control = 0` the count is hours, not people (for example 12,571 booter hours at $45.32 = $569,718). 88 rows, $132.8M.
* **Monthly**: amount = count x monthly rate x 12 for position rows, count = months for the 2 non-position rows.
* Position rows sum to 34,232 positions (27,966 annual, 5,847 hourly, 419 monthly). The Budget Overview says 34,173 positions in all funds, for the proposed book. I did not chase the 59 difference.

**Three title names are not jobs.** They are rows with count 0 that carry money that belongs to other appropriation lines, and each ties to the dollar to its own line in the ordinance:

| Row title in positions dataset | Rows | $ | Ties to ordinance account |
|---|---:|---:|---|
| Schedule Salary Adjustments | 724 | 25,717,582 | 0015 Schedule Salary Adjustments, 25,717,582 |
| Contract Wage Increment - Prevailing Rate | 114 | 11,709,192 | 0012, 11,709,192 |
| Fringe Benefits (grant funds only) | 122 | 66,797,584 | 0044 Fringe Benefits, 66,797,584 |

These are excluded from the salary tree because they do not belong to account 0005. The first two are real pay and could be added to the tree as their own nodes with their own lines. That is a modelling choice for the site, not a data problem.

### How turnover works

The ordinance prints, for each fund x department (and per organization within it), `Position Total`, then a `Turnover` line (negative), then `Position Net Total`. The net total **is** the 0005 line. Turnover is the budget's assumed vacancy savings: the city budgets every authorized position, then cuts a lump sum because some are always empty. It is not tied to any job title in the books. The printed `Position Total` equals the positions dataset's regular rows **plus the Schedule Salary Adjustment (0015) rows**, and the printed `Position Net Total` equals account 0005 + account 0015. So 0005 = regular rows + turnover. This holds to the dollar for every local fund x department pair (105 pairs tie through the printed Net Total, and the 106th, fund 0314 x Streets and Sanitation, has no printed turnover and its regular rows plus 0015 equal its 0005 line). The 0012 Contract Wage Increment rows are not in the printed Position Total.

**Use the passed ordinance's turnover, not the recommendation book's.** The Budget Recommendations book turnover totals $207,407,371. Council's Technical Amendments (passed 2025-12-22, `LESS TURNOVER` lines, ordinance p. 317 etc.) changed it to $215,563,788, a $8,156,417 increase, mostly Police (-$97,986,868 vs -$90,731,393 in the book's Corporate Fund block). The 0005 lines in `6694-f78c` match the amended numbers. Using the recommendation book leaves a $8.2M error.

### The bridge, $3.92B to $3.59B

| Step | $ |
|---|---:|
| Positions dataset, all 8,243 rows | 3,919,431,759 |
| less Schedule Salary Adjustments rows (account 0015) | -25,717,582 |
| less Contract Wage Increment rows (account 0012) | -11,709,192 |
| less Fringe Benefits rows (account 0044, grant funds) | -66,797,584 |
| **Regular salary rows** | **3,815,207,401** |
| less budgeted turnover printed in the ordinance (local funds) | -215,563,788 |
| less grant-fund positions above the grant 0005 line (no turnover printed) | -7,544,516 |
| **Salaries and Wages - on Payroll, ordinance** | **3,592,099,097** |

So of the $223.1M between the regular rows and the ordinance line, **$215.6M (5.8% of the $3.70B of local-fund regular rows) is turnover** and $7.5M is a grant-fund difference. The "$3.92B vs $3.59B" gap is therefore $104.2M of rows belonging to other accounts, $215.6M of turnover, and $7.5M of grant-fund difference.

**The grant-fund $7.5M is not explained by turnover.** The 51 grant fund x department pairs have $119.7M of position rows and $112.1M in the ordinance line. The book prints no position tables or turnover for grant funds, so I cannot say why. Grant salaries are also the weakest part of the tree because grant awards change during the year (see `research/grants_capital.md`). In the tree it appears as a labelled adjustment, `grant_implied_not_printed`.

### By department

Turnover percent is printed turnover divided by regular position rows in that department (all funds). The "Grant-fund gap" column is the part of the gap that is not turnover.

| Dept | Department | Positions dataset, regular rows | Printed turnover | Grant-fund gap | = Ordinance 0005 line | Turnover % |
|---|---|---:|---:|---:|---:|---:|
| 57 | Chicago Police Department | 1,584.6 | -99.7 | -1.0 | 1,483.9 | 6.29% |
| 59 | Chicago Fire Department | 554.9 | -20.4 | -0.1 | 534.4 | 3.68% |
| 88 | Department of Water Management | 269.6 | -11.9 | 0.0 | 257.7 | 4.41% |
| 85 | Chicago Department of Aviation | 233.5 | -11.8 | 0.0 | 221.6 | 5.07% |
| 81 | Department of Streets and Sanitation | 213.8 | -12.1 | -0.0 | 201.6 | 5.67% |
| 84 | Chicago Department of Transportation | 165.3 | -7.2 | -0.0 | 158.0 | 4.37% |
| 38 | Department of Fleet and Facility Management | 115.7 | -6.7 | 0.0 | 109.0 | 5.76% |
| 41 | Chicago Department of Public Health | 77.9 | -6.6 | -2.1 | 69.2 | 8.46% |
| 91 | Chicago Public Library | 87.3 | -3.2 | -1.0 | 83.1 | 3.68% |
| 58 | Office of Emergency Management and Communications | 81.7 | -5.3 | -0.0 | 76.4 | 6.48% |
| 27 | Department of Finance | 56.2 | -3.5 | -1.0 | 51.8 | 6.21% |
| 50 | Department of Family and Support Services | 40.2 | -0.9 | -1.4 | 38.0 | 2.16% |
| 31 | Department of Law | 46.6 | -3.2 | -0.0 | 43.4 | 6.9% |
| 51 | Office of Public Safety Administration | 38.9 | -3.4 | -0.1 | 35.3 | 8.8% |
| 67 | Department of Buildings | 36.3 | -1.9 | 0.0 | 34.4 | 5.21% |
| 54 | Department of Planning and Development | 20.6 | -1.7 | -0.1 | 18.9 | 8.14% |
| 70 | Department of Business Affairs and Consumer Protection | 20.8 | -1.2 | -0.0 | 19.5 | 5.95% |
| 6 | Department of Technology and Innovation | 16.9 | -2.4 | -0.0 | 14.5 | 14.24% |
| 21 | Department of Housing | 12.2 | -0.7 | -0.3 | 11.2 | 5.48% |
| 60 | Civilian Office of Police Accountability | 15.9 | -2.0 | 0.0 | 13.9 | 12.74% |
| 35 | Department of Procurement Services | 13.7 | -1.6 | 0.0 | 12.0 | 11.96% |
| 1 | Office of the Mayor | 13.5 | -1.0 | -0.0 | 12.5 | 7.7% |
| 33 | Department of Human Resources | 12.7 | -1.0 | -0.0 | 11.7 | 8.05% |
| 3 | Office of Inspector General | 12.5 | -0.5 | 0.0 | 12.0 | 3.72% |
| 15 | City Council | 8.7 | -1.0 | 0.0 | 7.7 | 11.82% |
| 72 | Department of Environment | 7.6 | -1.5 | -0.2 | 5.9 | 19.63% |
| 25 | Office of City Clerk | 8.5 | -0.4 | 0.0 | 8.2 | 4.46% |
| 23 | Department of Cultural Affairs and Special Events | 8.4 | -0.5 | 0.0 | 7.9 | 5.82% |
| 39 | Board of Election Commissioners | 8.0 | -0.5 | 0.0 | 7.6 | 5.69% |
| 5 | Office of Budget and Management | 6.7 | -0.2 | -0.1 | 6.5 | 2.77% |
| 73 | Chicago Animal Care and Control | 6.8 | -0.5 | 0.0 | 6.3 | 7.9% |
| 48 | Mayor's Office for People with Disabilities | 4.0 | -0.2 | -0.1 | 3.7 | 6.24% |
| 28 | City Treasurer's Office | 4.5 | -0.2 | 0.0 | 4.2 | 5.42% |
| 30 | Department of Administrative Hearings | 3.6 | -0.2 | 0.0 | 3.4 | 5.56% |
| 62 | Community Commission for Public Safety and Accountability | 3.3 | -0.2 | 0.0 | 3.2 | 5.1% |
| 45 | Chicago Commission on Human Relations | 2.3 | -0.0 | -0.0 | 2.2 | 2.1% |
| 78 | Board of Ethics | 0.9 | -0.1 | 0.0 | 0.8 | 7.75% |
| 55 | Chicago Police Board | 0.2 | -0.0 | 0.0 | 0.2 | 3.0% |
| 77 | License Appeal Commission | 0.1 | -0.0 | 0.0 | 0.1 | 3.0% |
| | **Total** | **3,815.2** | **-215.6** | **-7.5** | **3,592.1** | 5.65% |

Police is $99.7M (6.3%), and the Corporate Fund Police line alone is $97,986,868. Highest rates: Environment 19.6%, Technology and Innovation 14.2%, Civilian Office of Police Accountability 12.7%, Procurement 12.0%, City Council 11.8%. Fire (3.7%) and Library (3.7%) are the lowest of the large departments. Of the 105 department x fund turnover lines, 29 are $1M or more and hold $202.1M of the $215.6M.

Note the 2025 revised turnover, shown in the recommendation book next to the 2026 figure, was $78.1M for Police Corporate, against $97.99M in 2026. The City is budgeting more vacancy savings in 2026, mostly in Police. The mid-year report (p. 45) reports personnel salvage so far in 2026 of ($82.6M) across all departments, meaning departments have not yet saved what turnover assumes, Police by $60.0M. I did not use that number in the tree.

### How the tree is built

`root > department (39) > organization (60) > division (184) > section (515) > job title (3,874) > rate rows (7,283 title x fund x rate)`. Each title node lists its rate rows as "N positions x $rate". Organization, division and section names come straight from the dataset (no code has two different names).

To make each department equal the ordinance line, every department carries an `adjustments` list: one negative "Budgeted turnover" node per fund (with the ordinance page) and, for grant funds, the labelled grant difference. Department `amount` = gross position dollars + adjustments = the ordinance 0005 total for that department. **Turnover is attached at department x fund, not below.** The 160 printed blocks are listed under each adjustment as `printed_blocks` (ordinance page, positions, position total, turnover, net). Each block covers one division, or a run of consecutive divisions, of the dataset (I checked this for 138 of the 160 blocks. The other 22 belong to 7 fund x department pairs that also print a fund-level total). The book never says which job titles carry the vacancies, so scaling each title down by turnover would be a pro-rata estimate and should be labelled as one. I did not do it.

## 2. Overtime

### Definitions and sources

* **Budget 2026**: ordinance account 0020 "Overtime" (local funds $421,639,124; grant funds $684,000), plus 0032 "Reimbursable Overtime" ($7,300,000, Police $7.0M and Buildings $0.3M). The mid-year report prints the same $421,639,124 as "Budgeted Overtime".
* **Budget 2025 (revised)** and **2024 expenditures** are the columns printed next to each 0020 line in the recommendation book (`personnel_book_lines.py`).
* **Actuals 2024 and 2025**: Employee Payroll Costing (`dawh-m56b`), `appropriation_code = A0020`, summed by department, pay element, and department x title. This is what employees were paid and charged to the overtime appropriation, not the City's accounting-system expenditure, and it is not the same thing as the book's 2024 expenditure (see gaps).
* Other premium pay that behaves like overtime has its own accounts and is not in these numbers: 0021 Holiday Premium, 0022 Duty Availability ($39M Police), 0024 Comp Time Payment, 0088 Furlough/Comp Time Buy-back. 2025 payroll for these: Duty Availability $60.1M, Holiday Premium $33.5M, Comp Time Payment $30.4M, Buy-back $28.7M.

### Budget vs actual by department ($M)

| Dept | Department | 2026 budget (0020, local) | 2025 revised budget (book) | 2025 actual | 2024 book expenditure | 2024 actual | 2025 actual as % of 2025 revised |
|---|---|---:|---:|---:|---:|---:|---:|
| 57 | Chicago Police Department | 203.9 | 102.8 | 236.3 | 243.2 | 273.6 | 229.8% |
| 59 | Chicago Fire Department | 93.4 | 46.0 | 90.9 | 87.3 | 89.2 | 197.8% |
| 88 | Department of Water Management | 47.1 | 26.7 | 47.8 | 46.8 | 46.8 | 179.0% |
| 85 | Chicago Department of Aviation | 24.4 | 13.2 | 28.2 | 26.0 | 26.1 | 213.7% |
| 81 | Department of Streets and Sanitation | 15.2 | 12.2 | 24.0 | 24.2 | 24.6 | 196.0% |
| 84 | Chicago Department of Transportation | 14.6 | 6.7 | 11.1 | 16.2 | 16.3 | 166.5% |
| 58 | Office of Emergency Management and Communications | 9.7 | 6.2 | 10.8 | 11.6 | 11.6 | 176.1% |
| 38 | Department of Fleet and Facility Management | 9.4 | 8.9 | 13.9 | 15.5 | 15.6 | 156.8% |
| 51 | Office of Public Safety Administration | 1.4 | 1.0 | 1.5 | 1.9 | 1.9 | 146.0% |
| 39 | Board of Election Commissioners | 0.8 | 0.1 | 0.0 | 0.9 | 0.9 | 12.0% |
| 67 | Department of Buildings | 0.6 | 1.2 | 0.3 | 0.8 | 0.8 | 29.2% |
| 91 | Chicago Public Library | 0.4 | 0.4 | 0.5 | 0.8 | 0.8 | 125.5% |
| 27 | Department of Finance | 0.2 | 0.3 | 0.3 | 0.5 | 0.5 | 85.9% |
| 73 | Chicago Animal Care and Control | 0.2 | 0.1 | 0.3 | 0.4 | 0.4 | 175.9% |
| 41 | Chicago Department of Public Health | 0.1 | 0.1 | 0.1 | 0.2 | 0.1 | 154.0% |
| 25 | Office of City Clerk | 0.1 | 0.1 | 0.0 | 0.0 | 0.0 | 17.7% |
| 72 | Department of Environment | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a |
| 60 | Civilian Office of Police Accountability | 0.0 | 0.1 | 0.0 | 0.1 | 0.1 | 33.9% |
| 31 | Department of Law | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 61.5% |
| 70 | Department of Business Affairs and Consumer Protection | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 19.9% |
| 62 | Community Commission for Public Safety and Accountability | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | 26.4% |
| 3 | Office of Inspector General | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a |
| 30 | Department of Administrative Hearings | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a |
| 45 | Chicago Commission on Human Relations | 0.0 | 0.0 | 0.0 | 0.0 | 0.0 | n/a |
| | **Total** | **421.6** | **226.1** | **466.1** | **476.4** | **509.3** | 206.1% |

Reading it:

* The 2025 revised budget was far under what was paid: every department with more than $1M of 2025 overtime ran 146% to 230% of its revised budget in 2025. The shortfall is paid out of salary savings and is routine (the mid-year report says "department overtime budgets were increased in the 2026 budget to account for higher contracted wage rates").
* The 2026 budget is close to past actuals. Compared with the 2025 actual: Police -$32.3M below, Fire +$2.5M above, Water -$0.7M below, Aviation -$3.8M, Streets -$8.8M, CDOT +$3.5M, Fleet -$4.6M. Total 2026 budget is $44.4M below the 2025 actual.
* **2026 year to date**: through the May accounting period the City spent $146.3M on overtime (all funds), 34.7% of the $421.6M budget at 42% of the year, versus $142.1M in the same period of 2025 (+2.9%). Police $59.5M (29.2% of $203.9M), Fire $34.0M (36.4%), Water $16.8M (35.6%). Mid-year report pp. 45 to 46.

### By pay element (2025)

OT 1.5x $163.6M, OT 1.0x (straight time on overtime hours) $144.3M, OT FLSA $102.6M, OT 2.0x $42.8M, comp time buy back $2.0M. Sum with the smaller categories is the $466.1M. Full list in the JSON (`overtime.pay_elements`).

### By union and job title (2025 actual)

Payroll costing has a title code and a department, not a union. I attach the union by looking up the title code in the 2026 positions dataset (`bargaining_unit`) and taking the unit with the most dollars for that title. 99.99% of 2025 overtime dollars (99.92% for 2024) found a title code in the 2026 positions. 5 of 1,297 title codes appear in more than one unit, so those few are approximate. Union names come from the salary schedule pages of the book (`union_schedules.json`). Some unit codes (12, 42, 32, 50, 23) have no schedule printed in the book and are shown by code.

| Union | Bargaining unit code | 2024 OT | 2025 OT |
|---|---|---:|---:|
| Sworn Police Personnel - Fraternal Order Of Police - Chicago Lodge No. 7 | 91 | 218.2 | 187.6 |
| Uniformed Fire Department Positions | 87 | 87.5 | 89.4 |
| Teamsters Local 726 | 8 | 33.4 | 38.6 |
| Sworn Police Personnel - Sergeants, Lieutenants And Captains | 71 | 41.5 | 35.2 |
| Public Safety Employees Union - Unit Ii | 2 | 18.2 | 16.3 |
| Unit 12 (No Salary Schedule Printed) | 12 | 16.9 | 16.1 |
| Laborers Local 1092 / Laborers Local 1001 | 54 | 16.8 | 12.1 |
| Laborers Local 1092 / Laborers Local 1001 | 53 | 10.2 | 11.1 |
| Unit 42 (No Salary Schedule Printed) | 42 | 9.3 | 10.6 |
| Unit 32 (No Salary Schedule Printed) | 32 | 8.6 | 8.4 |

Top 20 department x title lines, 2025:

| Department | Title | 2025 OT | Employees paid OT | Union (bargaining unit) |
|---|---|---:|---:|---|
| Chicago Police Department | Police Officer | 140.1 | 7,370 | Sworn Police Personnel - Fraternal Order Of Police (91) |
| Chicago Police Department | Sergeant | 35.1 | 1,327 | Sworn Police Personnel - Sergeants, Lieutenants An (71) |
| Chicago Police Department | Police Officer (Assigned As Detective) | 27.3 | 1,157 | Sworn Police Personnel - Fraternal Order Of Police (91) |
| Chicago Fire Department | Firefighter-Emt | 15.5 | 1,612 | Uniformed Fire Department Positions (87) |
| Chicago Fire Department | Lieutenant-Emt | 14.4 | 525 | Uniformed Fire Department Positions (87) |
| Chicago Fire Department | Fire Engineer-Emt | 9.1 | 444 | Uniformed Fire Department Positions (87) |
| Chicago Fire Department | Paramedic I/C | 8.7 | 285 | Uniformed Fire Department Positions (87) |
| Chicago Fire Department | Firefighter/Paramedic | 8.3 | 288 | Uniformed Fire Department Positions (87) |
| Department of Water Management | Construction Laborer | 8.1 | 437 | Laborers Local 1092 / Laborers Local 1001 (53) |
| Department of Streets and Sanitation | Motor Truck Driver | 8.0 | 425 | Teamsters Local 726 (8) |
| Chicago Police Department | Police Officer / Fld Trng Officer | 7.6 | 385 | Sworn Police Personnel - Fraternal Order Of Police (91) |
| Department of Aviation | Motor Truck Driver | 7.5 | 325 | Teamsters Local 726 (8) |
| Chicago Police Department | Lieutenant | 7.3 | 279 | Sworn Police Personnel - Sergeants, Lieutenants An (73) |
| Chicago Fire Department | Paramedic | 7.1 | 424 | Uniformed Fire Department Positions (87) |
| Chicago Fire Department | Captain-Emt | 6.0 | 185 | Uniformed Fire Department Positions (87) |
| Department of Water Management | Hoisting Engineer | 5.9 | 171 | Unit 42 (No Salary Schedule Printed) (42) |
| Department of Streets and Sanitation | Pool Motor Truck Driver | 5.7 | 540 | Teamsters Local 726 (8) |
| Department of Water Management | Motor Truck Driver | 5.6 | 245 | Teamsters Local 726 (8) |
| Department of Water Management | Operating Engineer-Group A | 4.9 | 82 | Unit 12 (No Salary Schedule Printed) (12) |
| Office of Emergency Management and Communications | Police Communications Operator Ii | 4.8 | 223 | Public Safety Employees Union - Unit Ii (2) |

The full lists (708 title lines for 2024, 633 for 2025, all departments) are in `overtime.by_department_title`. A title line with a nonzero count shows how many people were paid overtime, so the average is overtime / employees. **Concentration (2025, aggregated, no names):** 24,590 employees were paid overtime. Median $11,684, mean $18,955, 90th percentile $45,593, maximum $208,721. 2,009 people earned $50,000 or more in overtime and 192 earned $100,000 or more. The top 10% of earners got 35.3% of overtime dollars.

## 3. Scheduled Wage Adjustments (account 0003, $387,717,767)

**What the ordinance says it is.** Nothing beyond the name. The Budget Overview describes the 2026 Corporate Fund as "led primarily by personnel services as all major labor contracts are anticipated to be resolved" (Overview p. 34), says Corporate Fund personnel costs are up $496.1M "as the last collective bargaining agreements are finalized" and that "budgeted personnel expenses account for contractual, prevailing rate, and other wage increases for both union and non-union employees" (p. 39). It also says about 89% of employees are in unions, whose agreements "establish benefit plans and scheduled salary increases" (p. 34). The 2027 Budget Forecast (p. 15) refers to "a decrease in scheduled contractual wage adjustments compared to 2026" for 2027. None of these documents defines account 0003 or breaks it down by union.

**Where it sits.** 17 of 20 lines are in Finance General (department 99), $283.0M. Fire has three lines for $104.7M.

| Fund | Finance General | Fire |
|---|---:|---:|
| Corporate (0100) | 262.3 | 98.0 |
| O'Hare (0740) | 13.6 | 5.3 |
| Midway (0610) | 3.6 | 1.5 |
| Emergency Communication (0353) | 2.0 | n/a |
| 13 other funds (Water $0.39M, Library $0.12M, and others) | 1.4 combined | n/a |
| **Total** | **283.0** | **104.7** |

**What the book says changed.** The recommendation book had $360.5M in Finance General's Corporate Fund line and none in Fire. Council's Technical Amendments (2025-12-22) moved $104.7M of the Finance General lines (all three funds) into Fire's own lines: Corporate $97,974,157, Midway $1,452,422, O'Hare $5,303,224, and cut Finance General to $262,287,301 (Corporate), $3,642,578 (Midway), $13,621,776 (O'Hare). The recommendation-book total was $387,956,309, so the ordinance total is $238,542 lower. The Fire move lines up with the Fire Department agreement settled in 2025, with back pay to 2021, that the Overview (p. 54) says the City will finance with general obligation debt; the overview does not say the 0003 amounts are that payment. That link is my inference.

**Last two years' actual use of the same account (payroll costing, appropriation A0003).**

| Year | Total | Pay elements |
|---|---:|---|
| 2024 | $94.0M | retro pay (pension-covered) $60.0M, retro pay (not pension covered) $10.5M, CBA lump sum $23.5M. All in Finance General. |
| 2025 | $243.2M | prior-year retro (pension) $161.1M, retro (no pension) $51.7M, retro (pension) $13.8M, CBA lump sum $16.5M. $242.5M in Finance General, $0.6M Police. |
| 2026 through period 3 | $8.8M | prior-year retro $6.4M, retro $2.4M, CBA lump $8.5K. Finance General |

This account is, in practice, the pot for contract back pay and signing lump sums. It does not hold regular raises, which flow into 0005 as new pay rates in the tables. For comparison, the book's 2025 appropriation for the same Finance General line was $162.8M, and $243.2M was paid. **The 2026 budget of $387.7M is 1.6x last year's actual use, and nothing in the books I have explains why.** In the Corporate Fund, Finance General plus Fire is $360.3M in 2026 against $162.8M in the 2025 revised column, up $197.5M.

**Rates, a cross-check.** For 5,162 title rows that appear in both columns of the book's tables (same row, 2026 vs 2025 revised), the count-weighted average rate increase is 3.53% and the median row is 3.01%. That is what is already built into the 0005 line.

## 4. Depth: share of personnel dollars in nodes under $1M

Basis: the regular salary rows, $3,815,207,401 gross, before turnover. Node = the dollar total at that node.

| Level | Nodes | Nodes under $1M | % of nodes | $ in nodes under $1M (M) | % of dollars |
|---|---:|---:|---:|---:|---:|
| Department | 39 | 3 | 7.7% | 1.3 | 0.03% |
| Organization | 60 | 4 | 6.7% | 1.8 | 0.05% |
| Division | 184 | 73 | 39.7% | 23.2 | 0.61% |
| Section | 515 | 247 | 48.0% | 105.5 | 2.76% |
| Job title (within section) | 3,874 | 3,492 | 90.1% | 751.8 | 19.70% |
| Rate row (title x fund x rate) | 7,283 | 6,853 | 94.1% | 1,220.4 | 31.99% |

So without any averaging, **68% of personnel dollars are still in rate rows of $1M or more.** The remaining 382 title nodes of $1M or more hold $3.06B (80.3% of dollars). 32 of them have 100 or more positions and hold $2.0B (Police Officer, 7,395 x $108,000, $798.7M; Firefighter-EMT, 1,549 x $100,109, $155.1M; Detective, 1,085 x $134,201; Sergeant 923 x $145,521).

**With count x average (what you asked for).** A big title node is shown as "N positions x $average". The highest average anywhere is Managing Deputy Commissioner at $205,591 (7 positions). 366 of the 382 big nodes have position counts. The other 16 ($64.0M) are hourly seasonal or prevailing-wage jobs where the count is hours (for example Pool Motor Truck Driver, 248,560 hours x $48.73 = $12.1M). They also come out as count x rate, with rates from $15.40 to $66.80 per hour. After this step **100% of personnel dollars sit in units under $1M, and no individual can be seen.** The count x average line is the same dollars divided up, not new data. Individual pay does exist in the Employee Salaries dataset (`xzkq-xp2w`, names and salaries), which is the true floor. I stayed away from names and used aggregates only.

Two things the depth number does not cover: (1) the **turnover adjustments** are department-level nodes, 29 of the 105 are $1M or more (largest -$97,986,868) and cannot be split because the books never say where the vacancies are; (2) the **7.5M grant adjustment**.

## 5. Gaps and caveats

1. **$386M vs $387.7M.** The figure given for Scheduled Wage Adjustments does not match the ordinance (387,717,767) or the recommendation book (387,956,309). The only $386.7M I found is an unrelated number in the forecast appendix. I used the ordinance number.
2. **Scheduled Wage Adjustments has no printed definition or breakdown** beyond the name, the Overview text above, and what payroll costing shows being paid. The link to Fire back pay is inferred. A question to OBM would settle it.
3. **Turnover below department x fund** is not allocated (see section 1). Pro-rata to title is possible but would be an estimate.
4. **Grant funds**: no printed position tables or turnover. $7.5M of difference between the positions dataset and the 0005 grant lines is unexplained, and the 51 grant pairs are $112.1M of salary. The $66.8M Fringe Benefits rows belong to these grants (account 0044) and are not salaries.
5. **Payroll costing is not the accounting ledger.** The 2024 overtime from payroll costing is $509.3M but the book's 2024 expenditure column is $476.4M (Police $273.6M vs $243.2M, which accounts for $30.4M of the $32.9M difference). I did not find the reason. I show both. The 2025 book "revised" budget is the only 2025 budget column available. There is no book "2025 expenditure" yet, so the 2025 actual is the payroll number only.
6. **Overtime by union** relies on a title-code join to the 2026 positions. Titles that have been renamed or retired since 2024 would be missed, but 99.99% of 2025 and 99.92% of 2024 dollars matched. Five title codes appear in more than one unit and take the largest-dollar unit.
7. **Overtime is paid to people, and the data is aggregated on purpose.** Employee-level payroll data has names. The cached employee file `raw/personnel/payroll_2025_ot_employee.json` holds IDs and amounts only, is gitignored, and was used only for the distribution above.
8. **Positions vs payroll headcount.** 34,232 budgeted positions in 2026. Payroll costing 2025 had distinct employees in `A0005` per department (cached in `payroll_2025_dept_headcount.json`). I did not compare filled vs budgeted positions because payroll costing counts everyone paid during the year, including people who left, so it overstates.
9. **Mid-year 2026 amendments** are covered in `research/reconciliation.md`, which finds no amendment touched the departmental structure. The ward wage allowance cut is account 0017, not 0005. I did not re-check the 0005 lines beyond the ordinance dataset.
10. **Hourly "positions"** that carry `position_control = 0` are hours, not headcount, and the tree labels them so.
