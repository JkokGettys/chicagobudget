# Employee compensation: City, CPS, Park District (people-level data and title aggregates)

Reproduce: `python3 scripts/people_fetch.py && python3 scripts/people_build_city.py && python3 scripts/people_build_cps.py && python3 scripts/people_build_parks.py`. Fetch caches go to `raw/people/` (gitignored). Dollar figures are exact sums from the sources unless marked otherwise. Pay is calendar 2025 from payroll costing, and base pay is the roster as fetched on 2026-10-01.

## Decision on names

**The website omits names; the public source records are not subject to that display rule.** At this snapshot, the full records with names live in `data/people/` (gitignored and not yet committed): `city_employees_2026.json`, `cps_positions_2025q4.json`, `parks_positions.json` (no names exist for the Park District), plus `data/people/README.md` with field definitions. The site shows **job titles only**, from three committed files with no names: `data/comp_city_2025.json`, `data/comp_cps.json`, `data/comp_parks.json`. The fact that these local source extracts are not yet on GitHub does not mean public records must have names removed before publication; provenance, upstream terms and other fields still require review.

**Small-group rule for the website-facing aggregate files.** A department x title group (CPS: unit x job title) with fewer than 5 people is rolled into "Other titles (groups under 5 people)" within its department. Median, mean and p90 are shown only for groups of 5 or more (p90 needs 10). If the rolled-up bucket itself holds fewer than 5 people, the smallest shown titles are pulled in until it has 5, so a subtraction cannot reveal one person. Departments and CPS units with fewer than 5 people have no pay dollars (Police Board, License Appeal Commission, and 44 small CPS units). "Top earner" findings are by title only. Title counts below 5 are folded into an "other" count. No single-person maximum is published anywhere.

## 1. Sources and coverage

| Government | Source | What it has | Coverage |
|---|---|---|---|
| City | Current Employee Names, Salaries, and Position Titles, `xzkq-xp2w` | name, title, department, F/P, salary or hourly rate, typical weekly hours | 31,875 rows (matches the stated count), 6,947 hourly and 24,928 salaried. Portal "updated" 2026-10-01 |
| City | Employee Payroll Costing, `dawh-m56b` | actual dollars per employee per pay period, with pay element, fund, department, appropriation, title code | Years 2023 to 2026 (2026 through period 6). 2025: 1,512,358 rows, $4,393,823,734, 37,507 distinct employees. Pulled server-side with `$group` (employee x pay element x department x title x fund x appropriation: 227,532 grouped rows, 5 pages). 2024 and 2025 also grouped without the employee key |
| City | Workforce Vacancies, `9v3e-pcjs` | positions, employees, vacancies by title and section, report date 2026-08-31 | 1,310 rows, 26,321 positions |
| City | 2026 Positions & Salaries `v2t2-vajc`; Appropriations 2026 `6694-f78c` and 2025 `t59y-fr3k` | budgeted counts, rates and account totals | already in the repo |
| CPS | Employee Position Roster, 12/31/2025 (`raw/cps/roster_12312025.xls`) | position number, unit, FTE, class, salary, FTE salary, benefit cost, job code and title, name | 48,806 positions, 46,408 with a name and salary, 2,398 blank (name, salary and benefit all blank) |
| Park District | none found | see below | budget tables only |

**Park District: person-level pay is not published where I could look.** Checked: the District's transparency, comptroller, financial services and FOIA pages (the FOIA page only describes how to file a request), the Illinois Comptroller's site (it has an OpenBook and a Salary Database link, but I could not tell from the page whether local governments like the Park District are in the salary database, and I did not query it), the Chicago Data Portal (44 Park District datasets, none on pay), and the Park District's own 2025 ACFR text (no per-person disclosure). Third-party salary aggregators (govsalaries.com, OpenGovPay, OpenTheBooks) turned up in search results showing a 2018 listing (3,203 employees), and their pages blocked automated access (HTTP 403), so I did not verify or use them. A FOIA request to foia@chicagoparkdistrict.com is the remaining route. What exists is the budget's positions tables (2,180 rows, title, job code, FTE, budgeted dollars by unit and fund, 2025 and 2026), already in `data/parks_2026.json`. `data/comp_parks.json` aggregates those by title: 317 distinct titles, 85 with at least 5 budgeted FTE shown, 232 smaller titles (360.7 FTE, $38.4M) in "Other titles". This is budget, not actual pay. Rows sum to 3,212.4 FTE and $220,590,509 (the budget text prints 3,213.0 FTE).

**Pension benefit payments by retiree: not pursued.** I found no free public per-retiree listing from the Chicago pension funds in the time available. Not verified either way.

## 2. How the City join works

The roster has no employee ID. The payroll dataset's `employee` field is `<id> - <NAME>` and its ID is a dataset-specific hash. The portal posted a change notice about this ID in July 2025, and I could not read its details, so I did not rely on IDs to link people across years. I joined on normalized name. Names that are unique on both sides join directly (29,640 rows). Duplicate names join only when exactly one candidate matches both department and title (611 rows). Everything else stays unmatched instead of being guessed. **30,251 of 31,875 roster rows (94.9%) carry 2025 pay.** I did not investigate why the 1,624 roster rows are unmatched (likely 2026 hires and name spelling differences between the two datasets). 7,256 payroll people have no roster row (likely separations during or after 2025, and possibly people on leave, which the roster description says it can exclude). Of those, 3,386 were paid through the last period of 2025 and 3,870 stopped earlier. Unmatched payroll people hold $455M of the $4,394M. 387 payroll names are shared by more than one ID, so a few name-based matches inside the matched set could still be wrong, but the department-and-title check is required for those.

Pay categories (defined in `meta.definitions` in the file): **regular** (A0005 / A0017 / A0000 regular salary, regular time, multi-rate straight time), **overtime** (appropriation A0020), **retro and lump sum** (A0003, which in 2025 is mostly retroactive back pay, $243.2M), **other premium** (everything else: duty availability, holiday, comp-time and vacation payouts, specialty pay, uniform allowance, reimbursable overtime A0032). 2025 totals: regular $3,376.1M, overtime $466.1M, other premium $308.4M, retro and lump sum $243.2M. Each person is assigned to the department x title where they received the most non-retro pay. People who moved titles during 2025 are counted once, in their main title. Group-level dollar sums, however, include every dollar charged to that title, so they can include some pay of people whose main title is different.

## 3. Reconciliation

### 3a. Payroll costing 2025 vs the ordinance personnel lines

| Account | Payroll costing 2025 (all funds) | 2025 ordinance | 2026 ordinance | Actual / 2025 ordinance |
|---|---:|---:|---:|---:|
| 0005 Salaries and Wages, on payroll | $3,382.5M | $3,499.0M | $3,592.1M | 96.7% |
| 0020 Overtime | $466.1M | $226.7M | $422.3M | 205.6% |
| 0003 Scheduled Wage Adjustments | $243.2M | $178.5M | $387.7M | 136.2% |
| 0022 Duty Availability | $60.1M | $59.2M | $59.2M | 101.5% |
| 0060 Specialty Pay | $35.1M | $36.2M | $36.2M | 96.9% |
| 0021 Holiday Premium | $33.5M | $33.0M | $33.0M | 101.5% |
| 0024 Comp Time Payment | $30.4M | $38.1M | $38.1M | 79.8% |
| 0091 Uniform Allowance | $30.1M | $31.4M | $31.1M | 95.9% |
| 0088 Furlough/Comp Time Buy-back | $28.7M | $30.3M | $30.3M | 94.8% |
| 0006 Salary Provision | $21.7M | $62.7M | $69.1M | 34.6% |
| 0017 Ward staff wage allowance | $15.1M | none in 2025 file | $16.4M | n/a |
| 0027 Supervisors Quarterly Payment | $14.3M | $12.4M | $12.4M | 114.7% |
| 0032 Reimbursable Overtime | $13.2M | $7.3M | $7.3M | 180.6% |

(Full list with local-fund splits in `reconciliation.payroll_vs_ordinance_by_account`.) The personnel-type accounts in the payroll file total $4,392.8M of the $4,393.8M. Reading it:

* **Overtime ran at about 2.06 times the 2025 ordinance line** ($466.1M paid vs $226.7M). The 2026 ordinance ($422.3M) is $43.8M below what was paid in 2025. This matches `research/city_personnel.md`.
* **Base salary ran 3.3% under the 2025 ordinance line** (the ordinance includes budgeted turnover and is not a pure salary roll). Against the 2026 line the 2025 payroll is $209.6M lower, partly because 2026 contains raises.
* **Scheduled wage adjustments** were paid as back pay and lump sums, not as scheduled raises: $161.1M prior-year retro with pension, $51.7M retro without pension, $16.5M CBA lump sum, $13.8M other retro.
* Accounts 0015 (Schedule Salary Adjustments, $26.5M in the 2025 ordinance) and 0012 (Contract Wage Increment, $11.3M) have no payroll dollars under those codes in payroll costing. I did not trace where that pay is charged, so comparing 0005 + 0015 + 0012 as a group is the likelier like-for-like test, but I did not verify it.
* Salary Provision (0006) paid $21.7M vs $62.7M budgeted. Mostly the CTA special-employee pay element ($20.9M).

### 3b. Employees vs budgeted positions (vacancies)

| Measure | Count |
|---|---:|
| 2026 budgeted positions with position control (positions dataset, excl. hour-based rows) | 34,232 |
| Vacancy dataset: total positions (report date 2026-08-31) | 26,321 |
| Vacancy dataset: employees in position | 22,464 |
| Vacancy dataset: vacancies | 3,857 (14.7% of its positions) |
| Current employee roster | 31,875 |
| Distinct people paid on A0005 in 2025 | 35,808 |

**The datasets do not use the same scope, so they do not add up to one headcount.** The vacancy dataset covers fewer positions than the budget (26,321 vs 34,232). Its counts for a few departments are well below the roster, for example Police 11,707 employees vs 12,244 on the roster (96%), Fire 2,589 vs 4,779 (54%), Water 1,022 vs 2,046 (50%), Finance 250 vs 556 (45%). I did not find the dataset's rule for which titles appear. 216 department x title groups with budgeted positions (1,556 positions, for example 42 Fire Paramedic Field Chiefs and 30 Hoisting Engineer-Mechanics in Fleet and Facility Management) are absent from it, which explains only a small part of the 7,911 gap. Treat its vacancy rate as a lower bound on coverage, not a citywide number. Within what it covers, the largest vacancy counts are Police Officer (732 of 8,573 positions), Fire recruits (169 of 670), Police detectives (130 of 1,282), Sergeants (107 of 1,327), Field Training Officers (107 of 449). By department, vacancy rates among the large departments are highest in Public Health (42.4%), Water (22.1%), OEMC (20.6%) and CDOT (19.3%), and lowest in Streets and Sanitation (9.9%) and Police (10.6%). On the budget side the roster is 2,357 (6.9%) below budgeted position control (the roster includes some hourly and part-time rows, so this is approximate), and the 2025 payroll counts more people than the roster because it includes anyone paid at any time in the year.

`data/comp_city_2025.json` carries budget positions, vacancy-dataset positions/employees/vacancies, current roster count, and 2025 paid-person counts at the title level for each department x title, so a drill-down can show "budgeted x, filled y, vacant z".

## 4. Findings (stated factually, by title or in aggregate)

**Overtime concentration (2025, appropriation A0020, $466.1M).**
* 24,590 people (65.6% of the 37,507 paid) received overtime. Median $11,684, mean $18,955, 90th percentile $45,591, 99th percentile $95,026.
* 2,009 people received $50,000 or more, and 192 received $100,000 or more. The top 10% of overtime earners received 35.3% of overtime dollars, the top 1% received 6.2%.
* By department, Police received 50.7% ($236.2M), Fire 19.5% ($91.0M), Water 10.2% ($47.4M), Aviation 6.0%, Streets and Sanitation 5.2%, Fleet and Facility Management 3.0%.
* Top titles by overtime dollars: Police Officer $140.1M (8,992 people paid, 91% of full-year officers received overtime, mean $17,933 for those paid all year), Sergeant $35.1M (mean $26,797), Police Officer (Assigned as Detective) $27.3M (mean $24,078), Firefighter-EMT $15.5M, Lieutenant-EMT $14.4M (mean $31,308).
* People with $100,000 or more in overtime, by title: Sergeant 42, Police Officer 32, Police Officer (Assigned as Detective) 13, Ambulance Commander (Fire) 13, Operating Engineer Group A (Water) 13, Assistant Chief Operating Engineer (Water) 11, SWAT officers 8, Lieutenant 7, Security Specialist officers 6, Operating Engineer Group C 5. Another 42 are in titles with fewer than 5 such people each.

**Total pay above $200,000 (2025).**
* Counting regular, overtime and other premium pay but excluding the retro/lump-sum account (A0003): **2,194 people** (5.8% of everyone paid in 2025). Including retro and lump sums it is 3,386. Thresholds in the file: $150K 8,531 (excl. retro) and 10,758 (incl.), $250K 372 and 991, $300K 61 and 203.
* By department (excl. retro): Police 1,459, Fire 563, Water 100, Fleet and Facility Management 18, Aviation 14, OEMC 8, Streets and Sanitation 7, CDOT 7, Law 7. 11 more people are in departments with fewer than 5 such people each, not listed.
* By title (people over $200K, share of the title): Police Sergeant 490 (28% of 1,724), Police Officer 277 (3%), Police Detective 269 (21%), Police Lieutenant 209 (49%), Fire Captain-EMT 129 (75%), Fire Lieutenant-EMT 98 (21%), Fire Battalion Chief 93 (92%), Fire Ambulance Commander 44 (46%), Paramedic Field Chief 32 (74%), Water Operating Engineer Group A 26 (31%). Full list: `findings.persons_ge_200k_excl_retro_by_title`.
* The highest total in the payroll data is under $420,000, so every person-level amount is under $1M.

**Biggest gaps between regular pay and total pay, by title** (titles with 10 or more people paid all 24 periods; premium = overtime + other premium as a share of regular pay):
* Police Officer (Assigned as Security Specialist), 19 people: regular $132.5K, overtime $85.9K, other $19.7K, premium 80% of regular.
* Water Assistant Chief Operating Engineer, 37: regular $139.7K, overtime $82.0K, 59%.
* Fire Firefighter (Per Arbitrators Award)-Paramedic, 12: 56%. Fire Ambulance Commander, 88: regular $138.8K, premium $72.9K, 53%.
* Police Canine Handler, 12: 52%. SWAT officers, 59: 52%. Explosives Technician I, 20: 50%. Water Operating Engineer Group A, 77: 50%. Fire Firefighter/Paramedic, 275: 46%. Police Captain, 31: $79.9K premium on $177.4K regular (45%).
* Across all of the city's full-year employees, the median total (excl. retro) is $128,191 and the 90th percentile $189,977 (29,062 people paid in all 24 periods).

**Actual regular pay vs budgeted rate.** In the 66 titles with at least 50 budgeted positions and at least 10 full-year people, mean regular pay is 1.3% below the budgeted average rate at the median title (0.4% below, weighted by people). Among all titles with at least 10 full-year people and a budgeted rate, the furthest below the budgeted rate are Senior Environmental Inspector (Public Health, -8.5%), Library Associate (-7.9%), Traffic Control Aide (OEMC, -7.7%). The titles furthest above are City Council Legislative Aide (+58%, see caveat), Police Community Organizer-CAPS (+16%), Police Training Officer (+15%).

**CPS (roster of 12/31/2025, positions not payroll).** 48,806 positions, 46,408 with a salary. FTE salary total $3,756.2M, annual benefit cost $1,204.3M. Teacher-class positions (T, 26,631): median $101,608, 90th percentile $124,543, $2,704.3M. Other (E, 19,777): median $49,271, 90th percentile $78,389. By title: Regular Teacher 13,911 positions (median $100,596), Special Education Teacher 5,325 (median $96,622), Special Ed Classroom Assistant 7,771 (median $49,271), Principal 484 (median $176,139, 90th percentile $189,617), Assistant Principal 649 (median $145,411), Custodial Worker 2,120 (median $47,154). 788 positions have a salary of $150,000 or more and 26 have $200,000 or more. Those 26 are spread over 24 titles, so no title has 5 of them and `positions_ge_200k_by_title` is empty by design. The roster budget join (FY26 budget book positions by unit and job code) covers $3,638.6M of the $3,670.1M in the budget file.

**Park District.** Budgeted 3,212.4 FTE and $220.6M in salary lines. Largest title groups by budgeted dollars: Park Supervisor of Recreation 143 FTE, $13.2M ($92.6K per FTE), Physical Instructor (M) 171 FTE, $11.9M ($69.6K), Laborer (Maintenance) 187 FTE, $10.5M ($56.3K), Attendant (M) 185 FTE, $10.3M ($55.9K), Recreation Leader 199 FTE, $9.1M. Note that dollars per FTE is a budget rate and includes seasonal and hourly mixes. No actual-pay data exists for the Park District here.

## 5. Caveats

* **Actual vs budget.** Payroll costing is cash paid and charged in 2025. The budget is a plan, and the ordinance includes budgeted turnover (vacancy savings) of $215.6M. They are not meant to match line by line. Payroll costing is not the same as the City's accounting expenditure (see `research/city_personnel.md`).
* **Prior year.** 2024 payroll costing totals $4,139.8M (2025: $4,393.8M) and 2024 overtime was $509.3M (2025: $466.1M). Title-level 2024 totals and overtime are in the City file for comparison.
* **Partial-year people.** 8,445 of 37,507 people were paid in fewer than 24 periods (hires, separations, leaves), and 1,779 appear in only one period. Their 2025 totals understate an annual rate. All per-person distributions in the aggregate files use people paid in all 24 periods ("full-year"). Counts (n_paid) and dollar sums include everyone.
* **Pay periods.** 24 periods per year. The retro/lump-sum payments in 2025 (A0003) are one-time and are shown separately, and "total excl. retro" is the better measure of what a job normally pays.
* **Title and department assignment.** Payroll lets a person be charged to several departments and titles in one year. Each person is assigned a main title. Sums by title include all dollars charged to it. Some pay of people with a different main title is therefore in a title's dollar sum while not in its distribution.
* **Roster vs payroll.** The roster is a current snapshot (2026-10-01) and payroll is 2025, so people hired in 2026 have no 2025 pay, and people who left in 2025 have no roster row. Hourly base pay is annualized as rate x typical weekly hours x 52, which overstates pay for part-year hourly workers.
* **Budget-rate comparison.** City Council Legislative Aide shows +58% over the budgeted rate. Ward staff are paid through the aldermanic wage allowance (A0017, $15.1M) and are not all in the positions dataset at those rates. I did not resolve this.
* **Vacancy dataset scope** is incomplete relative to the roster (section 3b).
* **CPS roster** is a point-in-time position list. It has no overtime, stipends or other earnings, and 2,398 rows with no name or salary (not explained by CPS, probably vacant). Salaries are shown at the position's FTE.
* **Pension benefits** are not covered.

## 6. Name display

Decision made: **titles only on the site; public source data may retain names.** The present local extracts are in `data/people/` (gitignored), but this is a publication-status fact, not a permanent requirement to redact public-source names. Groups under 5 people get no per-person statistics on the site and roll into "other titles" within their department or unit. Top earners are reported by title. The City and CPS source datasets are public and name-level; the display decision is about what this site amplifies, not about secrecy.

## 7. Files

| File | Committed? | Contents |
|---|---|---|
| `data/comp_city_2025.json` | yes, no names | 1,819 dept x title rows (40 are rolled-up "other titles" buckets, one per department), department summaries, findings, reconciliation |
| `data/comp_cps.json` | yes, no names | 2,539 unit x title rows, 657 unit summaries, 204 districtwide titles with 5 or more positions |
| `data/comp_parks.json` | yes, no names | 85 titles plus "other", by function |
| `data/people/*.json`, `README.md` | no, gitignored | named records |
| `scripts/people_fetch.py`, `people_build_city.py`, `people_build_cps.py`, `people_build_parks.py` | yes | rebuild |
