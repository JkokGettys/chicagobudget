# Tree gap audit: the built data tree (not the research files)

Snapshot: `raw/treeaudit/budget_snapshot.db`, a copy of `data/budget.db` taken 2026-10-01 (build of 20:40 UTC). Box amounts and structure are unchanged since then, but the coordinator has since changed vendor side info (every row kept, individuals' names hidden, Finance General payments on the City root). Section 5 vendor numbers describe the snapshot. Scripts: `scripts/treeaudit_*.py` (read-only, run `treeaudit_common.py` helpers against the snapshot). Compared with `research/final_gap_audit.md` (the "audit").

## Verdict

The tree is honest and ties to the cent, but it ends on big boxes more often than the audit predicted. City ends on a box of $10M or more for **64.5%** of dollars (audit: 52.8%), CPS **38.6%** (audit 21.0%), Parks **25.9%** (audit 24.7%). About half of the City gap and most of the CPS gap are **counting differences**, not missing data. The rest is data that exists in `data/` but no build script attaches (about $2.9B at most for City, see section 3).

## 1. Coverage: share of dollars (absolute value) by the size of the box where clicking stops

"N x rate" boxes with a rate under $1M count as under $1M. Source: `treeaudit_coverage.py`.

| Government | Leaves | Total (abs) | Under $1M | $1M to $10M | $10M or more | Audit said $10M or more |
|---|---:|---:|---:|---:|---:|---:|
| City | 10,025 | $17,809M | 26.0% | 9.4% | **64.5%** | 52.8% |
| CPS | 20,075 | $11,184M | 46.6% | 14.8% | **38.6%** | 21.0% (29.6% counting offsets as absolute) |
| Parks | 6,110 | $678M | 40.5% | 33.6% | **25.9%** | 24.7% |
| City "counted twice" memo branch | 133 | $1,709M | 0.6% | 5.6% | 93.7% | not audited |

By basis ($M of leaves, abs, and where they end):

| Gov | Basis | Under $1M | $1M to $10M | $10M or more | Total | Share of gov |
|---|---|---:|---:|---:|---:|---:|
| City | budget | 294 | 1,419 | 6,120 | 7,832 | 44.0% |
| City | tied | 3,818 | 194 | 1,788 | 5,800 | 32.6% |
| City | proxy | 494 | 0 | 2,767 | 3,261 | 18.3% |
| City | residual | 0 | 0 | 492 | 492 | 2.8% |
| City | adjustment | 31 | 65 | 327 | 424 | 2.4% |
| CPS | budget | 1,647 | 1,106 | 3,075 | 5,828 | 52.1% |
| CPS | tied | 2,582 | 439 | 28 | 3,048 | 27.3% |
| CPS | proxy | 981 | 81 | 773 | 1,834 | 16.4% |
| CPS | adjustment | 0 | 21 | 445 | 465 | 4.2% |
| CPS | residual | 2 | 6 | 0 | 9 | 0.1% |
| Parks | budget | 273 | 178 | 107 | 557 | 82.2% |
| Parks | residual | 2 | 1 | 54 | 57 | 8.3% |
| Parks | tied | 0 | 40 | 0 | 40 | 5.8% |
| Parks | adjustment | 0 | 0 | 15 | 15 | 2.2% |
| Parks | proxy | 0 | 9 | 0 | 9 | 1.4% |

### Why the City tree shows 64.5% and the audit 52.8%

I matched all 202 City inventory lines in `data/leaves_over_10m.json` to tree nodes (all 202 found, `treeaudit_compare.py`) and recomputed the audit's own rules (`audit_tiers.py`, "with proxies") against the tree's leaves under each line. On those lines the audit has **$9,015M** at $10M or more and the tree **$11,320M** (+$2,305M). The other tree leaves at $10M or more are the OBM adjustment (-$117.0M) and "Less Corporate Fund Savings" (-$56.6M), both absolute in the tree. The $2,305M splits into (`treeaudit_bridge.py`):

| Cause | Lines | Audit $M | Tree $M | Tree minus audit |
|---|---:|---:|---:|---:|
| Pay, overtime and claims proxies (2025 pay by title). The audit counted them as "N people x average", under $1M. The tree kept one box because the 2025 pieces do not fit the 2026 line, or no script attaches them | 30 | 136 | 1,169 | +1,033 |
| Named vendor payments (2026 paid to date). The audit credited the part of each line explained by vendor payments. The tree keeps payments as side info (README rule 4). Net of +$1,202M (tree larger) and -$489M (audit counted a vendor group once on its largest line and its pieces exceeded that line) | 70 | 2,058 | 2,771 | +713 |
| CDBG-DR sewer plan: "26.0 miles x $8.5M". The audit counted it under $1M, the tree's unit is $8.5M so it is correctly a $10M+ box | 3 | 129 | 351 | +221 |
| Grant reserve lines where the audit credited named projects under $10M and the tree attached none | 15 | 1,320 | 1,530 | +210 |
| Salary lines: vacancy-savings boxes are negative, the tree counts them absolute | 37 | 0 | 127 | +127 |
| Bond series lines | 15 | 1,807 | 1,807 | 0 (but Midway and Sewer pieces sit on the wrong line, section 4) |
| No split in either | 32 | 3,565 | 3,565 | 0 |
| **All 202 lines** | 202 | **9,015** | **11,320** | **+2,305** |

Biggest single items (tree minus audit, $M, all "audit counted as split, tree has one box"): Scheduled Wage Adjustments, Finance General +262.3. CDBG-DR sewer +221.3. Police overtime +200.0 (2025 actual $236.3M exceeds the $200M line). IDOT highway construction +117.4. O'Hare FAA professional services +112.7. Fire Scheduled Wage Adjustments +98.0 (2025 actual $208.9M exceeds the $98.0M line). Police salary vacancy savings counted absolute +98.0. Fire overtime +86.4. Homeless Services +55.0, Youth Employment +48.9, Delegate agencies (IDHS) +48.9, Head Start +42.0. Offsetting the other way: O'Hare professional services -90.7, FHWA construction -77.5, Midway bond interest -77.5, Asset Management electricity -74.9, Police tort judgments -52.8. Denominators also differ: the audit used signed dollars on $16,959M, the tree uses absolute dollars on $17,809M. On signed dollars the tree is 63.7%.

### Why CPS shows 38.6% and the audit 21.0%

The audit's 21.0% counted offsets signed and counted split proxies as resolved. Like for like (offsets absolute) the audit says 29.6%. The remaining 9 points are mostly two counting rules (`treeaudit_cps_parks.py`, `treeaudit_extra.py`):

| Item | Tree $M at $10M or more | Audit treatment | Fix |
|---|---:|---|---|
| CTPF teacher pension: "Retired teachers (23,350 people)" $558.0M and "Families of teachers who died (3,399 people)" $37.3M | 595.2 | count x average, under $1M | The boxes have a count but an empty `unit_amount_cents`, so the depth rule cannot treat them as N x rate. Set unit = amount / count. Build bug, two lines |
| Charter school tuition, 28 leaves of $10M or more (26 are the only child of a "Tuition paid to charter schools" box that carries students x rate) | 427.8 (372.5 in the 26) | split_proxy (students x rate), under $1M | Put the count and rate on the leaf or fold the leaf into its parent |
| Non-teacher pension reserve (MEABF) $202.8M: retirees x average exist in `data/leaves_cps.json` pieces but only as side info | 202.8 | count x average | Attach pieces like the CTPF levy |
| Bond series (one box per series, principal and interest merged) | 989.1 (24 boxes) | principal and interest rows counted separately and also at $10M or more | none, same dollars |
| Pools "Other job titles (fewer than 5 positions each)" at $10M or more | 51.4 (3 boxes) | not counted | fine |

Fixing the first two rows alone moves CPS from 38.6% to **30.0%**, and attaching the MEABF pieces gives 28.2%. Parks matches the audit within 1.2 points (the tree adds the $22.3M Series 2023C loan box and counts the -$15.2M vacancy allowance absolute).

## 2. The 30 largest boxes of $10M or more per government

Full lists: `python3 scripts/treeaudit_tables.py 30 30`. The sentence column is a regex check (`treeaudit_top.py`) for a sentence that does not fit the box. City has 218 such boxes (count x rate boxes excluded) and **90 are flagged ($3.9B)**. CPS 112 boxes and 0 flagged. Parks 7 and 1 flagged. Flag counts for City: generic fallback 55 boxes ($2,149M), contracts sentence on grants to agencies, loans or services 21 ($676M), contracts sentence on supplies or utilities 8 ($298M), no sentence 6 ($327M, all adjustments, which the rule exempts), stale "contracts" sentence on highway construction lines 4 ($603M), construction sentence on non-construction grant reserves 4 ($139M).

Worst City sentences, in plain words:

| $M | Box | Problem |
|---:|---|---|
| 451.6, 117.4, 23.6, 10.0 | Highway, IDOT, DCEO, transit "Construction of Buildings and Other Structures" | Says "a few big companies each get one large contract payment" but no company box is attached. The audit wrote a different sentence ("no payment so far matches it to a company", section 5 of the audit) for the unmatched $256.1M, and it was not carried over |
| 124.7 | Emergency Medical Transportation | Same "big companies, contracts" sentence on a ledger line that is not a vendor contract |
| 65.6, 25.2, 15.5, 12.9, 11.7 | Rehabilitation Loans and Grants | Contracts sentence on housing loans and grants |
| 63.7, 55.0, 48.9, 48.9, 42.0 | Delegate Agencies, Homeless Services, Youth Employment, Head Start | Contracts sentence on money passed to partner agencies |
| 262.3 | Finance General Scheduled Wage Adjustments | Generic fallback, though the audit has a 145 job title proxy |
| 234.1, 112.7, 92.2, 55.2 | Professional and Technical Services (O'Hare, FAA grant, Finance General) | Generic fallback |
| 90.5 | Corporate Fund "For Payment of Bonds" | Says "yearly bill for many separate bonds". `data/debt_2026.json` marks this line `internal_transfer: true` (the subsidy that also appears as revenue of the Bond Redemption fund) |
| 48.5, 39.3, 29.0, 22.2 | HOME and CDC grant reserves | "Some named projects are single big construction jobs", wrong for HOME housing and CDC public health money |
| -117.0, -98.0 and 4 more adjustments | OBM unexplained adjustment, vacancy savings | No sentence at all, a reader who clicks "why" gets nothing |

CPS and Parks sentences fit their boxes. CPS reuses one "a few large companies" sentence on 18 boxes ($542M) including the State Preschool $88.1M line, where `leaves_cps.json` says provider awards were not found.


### Top 30 tables

### city: 218 leaves >= $10M, 90 with a flagged sentence ($3,895M)

| # | $M | Basis | Box (last two names) | Flag on the why sentence |
|---:|---:|---|---|---|
| 1 | 818.1 | proxy | For the City's Contribution to Emp > Paying down the shortfall (money promised but never  |  |
| 2 | 817.8 | proxy | For the City's Contribution to Emp > Paying down the shortfall (money promised but never  |  |
| 3 | 451.6 | budget | Federal Grant Fund > Construction of Buildings and Other Structures (DOT  | stale: 'no matched payee' sentence was written for this box  |
| 4 | 411.8 | budget | Federal Grant Fund > Reserve Balance (DOT - FAA - Airport Improvement Pro |  |
| 5 | 348.7 | proxy | For the City's Contribution to Emp > Paying down the shortfall (money promised but never  |  |
| 6 | 329.8 | proxy | Reserve Balance (DOT - FTA - Feder > State/Lake Loop Elevated Station (one named project) |  |
| 7 | 262.3 | budget | Corporate Fund > Scheduled Wage Adjustments | generic fallback |
| 8 | 234.1 | budget | Chicago O'Hare Airport Fund > For Professional and Technical Services and Other Th | generic fallback |
| 9 | 222.4 | tied | For the City's Contribution to Emp > Cost of pensions workers earn this year |  |
| 10 | 221.3 | proxy | Construction of Buildings and Othe > about 26.0 miles of local sewer x $8.5M per mile |  |
| 11 | 200.0 | budget | Corporate Fund > Overtime |  |
| 12 | 161.2 | tied | For the City's Advance Contributio > Extra payment above what the law requires |  |
| 13 | 146.9 | tied | For the City's Contribution to Emp > Cost of pensions workers earn this year |  |
| 14 | 124.7 | budget | Corporate Fund > Emergency Medical Transportation | contracts sentence on a non-contract box; contracts sentence |
| 15 | 124.1 | budget | State Grant Fund > Reserve Balance (IDOT - Highway Planning and Constru |  |
| 16 | 123.9 | budget | Federal Grant Fund > Reserve Balance (DOT - FAA - Airport Improvement Pro |  |
| 17 | 121.1 | proxy | Reserve Balance (DOT - FHWA - IDOT > named projects, unspent budget |  |
| 18 | 117.9 | budget | State Grant Fund > Reserve Balance (IDOT - Rebuild Illinois) |  |
| 19 | 117.4 | budget | State Grant Fund > Construction of Buildings and Other Structures (IDOT | stale: 'no matched payee' sentence was written for this box  |
| 20 | -117.0 | adjust |  > Adjustment the budget office makes that no line expl | NO SENTENCE |
| 21 | 112.7 | budget | Federal Grant Fund > For Professional and Technical Services and Other Th | generic fallback |
| 22 | 111.6 | residu | For Interest on Bonds > Other bonds (not printed one by one) |  |
| 23 | 109.9 | proxy | For the City's Contribution to Emp > Paying down the shortfall (money promised but never  |  |
| 24 | 108.4 | residu | For Payment of Bonds > Other bonds (not printed one by one) |  |
| 25 | -98.0 | adjust | Salaries and Wages - on Payroll > Budgeted turnover (vacancy savings), Corporate Fund | NO SENTENCE |
| 26 | 98.0 | budget | Corporate Fund > Scheduled Wage Adjustments |  |
| 27 | 93.0 | tied | For the City's Contribution to Emp > Cost of pensions workers earn this year |  |
| 28 | 92.2 | budget | Chicago O'Hare Airport Fund > For Professional and Technical Services and Other Th | generic fallback |
| 29 | 90.5 | budget | Corporate Fund > For Payment of Bonds |  |
| 30 | 86.4 | budget | Corporate Fund > Overtime | generic fallback |

### cps: 112 leaves >= $10M, 0 with a flagged sentence ($0M)

| # | $M | Basis | Box (last two names) | Flag on the why sentence |
|---:|---:|---|---|---|
| 1 | 558.0 | proxy | Teacher pension levy paid to the C > Retired teachers (23,350 people) |  |
| 2 | 256.5 | budget | Paying back loans > Bond series 2009G |  |
| 3 | 202.8 | budget | Pensions and Medicare tax > Reserve for non-teacher staff pensions (MEABF) |  |
| 4 | -143.3 | adjust | Teacher pay set-aside (budget only > Planned savings from jobs left unfilled (vacancy fac |  |
| 5 | 120.6 | budget | Pensions and Medicare tax > Pension reserve in the general fund (a reservation,  |  |
| 6 | 120.0 | budget | Money held back for later (conting > Contingency For Project Expansion (Contingency for G |  |
| 7 | 116.8 | proxy | Health insurance set-aside (budget > Medical plan share (HCSC) |  |
| 8 | 108.0 | budget | IT, Security and Other Projects > IT - Centralized (DC, CO etc.) |  |
| 9 | -100.0 | adjust | Money held back for later (conting > Other General Charges (General Education Fund) |  |
| 10 | 88.1 | budget | Professional and administrative se > Payment To Other Govt Units (State Preschool For All |  |
| 11 | 80.0 | budget | Facility Needs > Emergency/Unanticipated Facility Repairs |  |
| 12 | 66.7 | budget | Tuition for special education priv > Tuition for Special Education Private Programs (Spec |  |
| 13 | 62.6 | budget | Paying back loans > Bond series 1999A |  |
| 14 | 62.0 | budget | Paying back loans > Bond series 2018C |  |
| 15 | 59.0 | budget | Paying back loans > Bond series 1998B-1 |  |
| 16 | 57.0 | budget | Food > NSS - Lunch Program (Lunchroom Fund) |  |
| 17 | -56.7 | adjust | Staff pay set-aside (budget only) > Planned savings from jobs left unfilled (vacancy fac |  |
| 18 | 55.1 | budget | Paying back loans > Bond series 2018A |  |
| 19 | -52.9 | adjust | Money held back for later (conting > Other Instr Purposes Misc (General Education Fund) |  |
| 20 | 50.8 | budget | Paying back loans > Bond series 2016A |  |
| 21 | 50.4 | budget | Money held back for later (conting > Contingency For Project Expansion (Contingency for G |  |
| 22 | 50.1 | budget | Paying back loans > Bond series 2009E |  |
| 23 | 50.0 | budget | Money held back for later (conting > Special Income Fund 124 Contingency (Internal Accoun |  |
| 24 | 44.5 | budget | Salaries > Staff pay set-aside (budget only) |  |
| 25 | 44.4 | budget | Tuition paid to charter schools > Charter/Contract Per Pupil Revenue K-12 Tuition (Cha |  |
| 26 | 43.9 | budget | Supplies, food and utilities > Electricity |  |
| 27 | 43.6 | budget | Paying back loans > Bond series 2019A |  |
| 28 | 43.5 | budget | Paying back loans > Bond series CIT 2016 |  |
| 29 | 42.2 | budget | Supplies, food and utilities > Electricity delivery |  |
| 30 | 37.3 | proxy | Teacher pension levy paid to the C > Families of teachers who died (survivor benefits) (3 |  |

### parks: 7 leaves >= $10M, 1 with a flagged sentence ($15M)

| # | $M | Basis | Box (last two names) | Flag on the why sentence |
|---:|---:|---|---|---|
| 1 | 53.9 | residu | Regular yearly pension payment > Paying down the pension shortfall (budget payment mi |  |
| 2 | 36.3 | budget | Soldier Field, harbors, golf and o > Soldier Field |  |
| 3 | 22.3 | budget | Paying back loans > Series 2023C: refinancing loan |  |
| 4 | 16.7 | budget | Contracts, utilities and services > Water and sewer bills |  |
| 5 | 16.6 | budget | Soldier Field, harbors, golf and o > Boat harbors |  |
| 6 | -15.2 | adjust | Pay, benefits and savings reserves > Savings from jobs left unfilled (vacancy allowance) | NO SENTENCE |
| 7 | 14.8 | budget | Contracts, utilities and services > Electric bills |  |

## 3. Splits that exist in `data/` but did not reach the tree

| Source file | What is there | In tree? | $ that could still be attached | Why it was not attached |
|---|---|---|---:|---|
| `city_grants_2026.json` reserve_attribution (88 reserve lines, $1,909.8M) | Named projects or awards for 53 lines, "attributable" cap $902.4M | The build never reads this file. `leaves_grants.json` feeds 3 boxes ($450.9M: State/Lake station, 20.205 named projects, sewer plan) | 13 reserve lines left whole: **$243.2M** of named items would land under $10M, **$413.8M** more would be named items still at $10M or more (O'Hare FAA 26 awards, 10 of them $10M+, cap $218.3M of $411.8M; IDOT highway 42 items; Rebuild Illinois; Midway FAA; HOME x3; CDC; freight) | Caps are upper bounds (min of reserve and unspent), project lists are a 2026-05-31 snapshot against an Aug 2025 carryover, 35 of 88 lines have no project record at all |
| `leaves_over_10m.json` vendor pieces (70 lines, $2,771M) | Named 2026 YTD vendor payments per line (56 pieces of $10M+ = $1,454M, plus 833 "no matched payee") | Side info only (rule 4: actuals never inside budget amounts) | Net **$0.7B to $1.2B** would leave the $10M+ group (+$1,202M on lines where the audit credited vendors, -$489M where the audit counted a group once on its largest line and the pieces exceed it) | Policy: payments are cash to date, not budget. Group cap logic is not in the tree builder |
| `leaves_over_10m.json` pay proxies (18 lines, $945.3M) | 2025 actual pay by job title (`raw/leaves/payroll_2025_approp_dept_title.json`, 1,278 rows) | Not attached (only Police overtime and Fire 0003 as side info) | **$344.4M** fits inside its 2026 line (Scheduled Wage Adjustments $262.3M vs $242.5M, Comp Time $36.0M vs $29.0M, CTA detail $30.0M vs $21.7M, Specialty Pay $16.1M vs $14.1M). **$600.9M** exceeds the line or is unknown (Police overtime $200M vs $236.3M, Fire 0003 $98.0M vs $208.9M, Fire overtime, Duty Availability, others) | The build rule drops a proxy that exceeds its line. Largest title in Scheduled Wage Adjustments is $68.6M, so not all lands under $10M |
| `leaves_over_10m.json` EY health shares (10 lines, $224.0M) | Enrolled employees by union x average | Only the two Corporate Fund lines in `leaves_health.json` are attached ($408.7M, $85.2M) | **$224.0M** (O'Hare $36.4M, Water $25.9M, Vehicle Tax $14.6M, Library $11.1M and 6 more) | Same method, other funds, not run in `leaves_health.py` |
| `leaves_pensions.json` benefit_type_pieces (retirees x average) | 8 pension lines, $2,843M ($2,584M in $10M+ boxes plus $260M extra payments) | Tree splits by "earned this year" vs "shortfall"; retirees are side info | Up to **$2.8B** by rule (CPS does this for its levy) | Judgment: the levy is a contribution, not benefits. The audit kept it as tier B |
| `leaves_cps.json` A58275 (MEABF reserve) | 2 pieces, retired members x average, surviving spouses x average | Reserve is one $202.8M box, counts are side info | **$202.8M** | Pieces have no amounts, the CTPF code path was not copied |
| `city_bond_series_2026.json` | 104 series rows | 89 series boxes ($1,236M) | O'Hare residual $79.7M + $46.7M = $122.5M, Water $12.0M + $44.6M, Sewer $15.7M | No separate column printed in any fetched statement. Not splittable with data we hold |
| `debt_2026.json` GO per series | 6 GO series (all attached) and 6 STSC series ($119.6M, ACFR STSC total $449.3M) | GO attached. **STSC is nowhere in the tree** | GO residual stays **$220.0M** ($111.6M interest, $108.4M principal). STSC $449.3M is outside the ordinance | GO: ACFR Table 25 prints balances only for the 18 older issues, per-year schedules are on EMMA (not reachable). STSC: not in the ordinance, so it cannot sit in the City total |
| Midway and Sewer series | Midway 7 series print principal and interest combined ($125.2M). Sewer 1998A is $24.68M combined | Attached under the interest line only, so Midway shows a **-$64.1M "Difference" box** and an empty $77.5M principal leaf, Sewer a **-$19.4M** Difference box | Structure fix. Up to about $10M leaves the $10M+ group (only Midway 2024A/B are under $10M) | Combined columns were put on one of the two lines |
| `cps_debt_by_series_fy26.csv` | 34 series with principal and interest | One box per series, principal and interest merged | $29.6M (5 series where one half is under $10M) | Not split |
| `city_capital_2026.json` | 1,479 CIP projects, 1,643 Aldermanic Menu items under $413K, 253 TIF lines | Not read by any builder | $0 inside the City total (the CIP is a plan, not the ordinance). Adds below-$1M detail beside "Construction" lines | Needs its own "capital plan" branch |
| `comp_cps.json`, `comp_parks.json`, FY2024 and FY2025 CPS supplier files, 2025 vendor files, `context_*.json` | pay by unit and title, prior years, context | Not read | Side info only | Not built yet |

## 4. Structure problems a 13 year old would hit

| Problem | Count | Detail |
|---|---:|---|
| Boxes with exactly one child (a click that shows the same number) | **2,459** (City 722, CPS 1,410, Parks 254, memo 73) | All 2,459 have a child with the identical amount. Biggest groups: CPS spending type -> account 1,283 ($1,201M), City fund -> ordinance line 298 ($1,089M), Parks park -> fund 209, City org unit -> org unit 150, CPS account -> job title group 121. 16 child boxes repeat the parent's name. On average a leaf path crosses 0.31 such boxes in City, 0.07 CPS, 0.79 Parks |
| Deep paths | City **median 8 clicks, max 9** (6,795 of 10,025 leaves at 8 or more). CPS max 7, Parks max 6 | Typical: City > Keeping people safe > Police > Pay for workers > Corporate Fund > Salaries and Wages > Patrol Services > Areas - Districts > Police Officer > 2,148 positions x $111,252 |
| Boxes with more than 200 children | **0** | Widest: O'Hare airport org unit 175, CPS charter schools 121, CPS Facility Needs 86, Parks regions 82 each. 14 boxes have 51 to 200 |
| Same name, many boxes | "Corporate Fund" 224 times in City (every department has one), 969 City boxes end in "Fund". "Other job titles (fewer than 5 positions each)" 1,137 times ($968M), "Contracts and services" 717, "Salaries" 657 | The fund layer repeats in every department and its name tells a kid nothing |
| Duplicate sibling names | 18 groups, 43 boxes, all CPS capital | "Contingency For Project Expansion" x3 under one parent ($195.4M), "GATELY STADIUM" x2, "IT - Centralized" x2 |
| Long or coded names | 596 names over 90 characters (535 leaves), 455 leaves with a fund or grant code in brackets | e.g. "Construction of Buildings and Other Structures (DOT - FHWA - IDOT - CTY - Highway Planning and Construction (20.205))" |
| Negative boxes | **681**, -$1,214.5M | City 247 (-$483.3M, 243 are vacancy or turnover adjustments, 38 below -$1M), CPS 23 (-$705.7M, 15 below -$1M), Parks 411 (-$25.5M, 118 of them "rounding"), 5 negative parents |
| Tiny boxes | 441 leaves of $10 or less (Parks 379, of which 275 "rounding", CPS 57, City 5). 3,180 leaves of $1,000 or less | Parks "Not itemised on any department page" holds 17 boxes including "PDF rounding differences ($10 or less)" $1 and "Rounding in the printed budget" $3 |
| Residual bigger than all its siblings | 6 boxes over $1M, $414M | GO interest "Other bonds" $111.6M (9 siblings), GO principal $108.4M (3), O'Hare interest $79.7M (31), Parks pension shortfall $53.9M (1 sibling), Water principal $44.6M, Sewer principal $15.7M |

## 5. Data quality

Residual or difference boxes over $1M (14, $637M absolute), `treeaudit_quality.py`:

| $M | Government | Box | Parent |
|---:|---|---|---|
| 111.6 | City | Other bonds (not printed one by one) | GO interest |
| 108.4 | City | Other bonds | GO principal |
| 79.7 | City | Other bonds | O'Hare interest |
| -64.1 | City | Difference: detail sources exceed the budget line | Midway interest |
| 53.9 | Parks | Paying down the pension shortfall | Regular yearly pension payment |
| 46.7 | City | Other bonds | O'Hare principal |
| 44.6 | City | Other bonds | Water principal |
| 40.9 | City | Other / not itemised | FHWA 20.205 reserve |
| 32.9 | City | Other / not itemised | FTA 20.507 reserve |
| -19.4 | City | Difference | Sewer interest |
| 15.7 | City | Other bonds | Sewer principal |
| 12.0 | City | Other bonds | Water interest |
| 6.3 | CPS | Other teacher pay not listed by job title | Special education teachers |
| 1.1 | Parks | Interest paid outside the bond | Paying back loans |

Residual and difference boxes of any size: City 12 ($575.9M), Parks 21 ($57.4M), CPS 134 ($8.7M). The two negative Difference boxes are a build artifact (series put on the wrong line), not missing money.

Proxy dollars (abs, leaves):

| Government | Proxy boxes | $M | Share of dollars | Under $1M | $1M to $10M | $10M or more |
|---|---:|---:|---:|---:|---:|---:|
| City | 15 | 3,261 | 18.3% | 494 | 0 | 2,767 |
| CPS | 387 | 1,834 | 16.4% | 981 | 81 | 773 |
| Parks | 1 | 9.4 | 1.4% | 0 | 9.4 | 0 |

City proxy is mostly pension components $2,095M, grant projects $672M, health $494M. CPS proxy is the pension levy and reserves $1,057M, job-title pools $777M.

Side info coverage (snapshot, before the vendor change):

| Government | Vendor payments | Pay by job title | Other |
|---|---|---|---|
| City | All 39 departments ($4,716M vendors paid, 2026 to 9/28) | 37 of 39 departments, 2,329 of 4,107 job-title boxes ($3,540M of $3,815M). Missing: Police Board, License Appeal Commission | Retiree counts on 4 funds. **No prior-year budget or actual at all** |
| CPS | 33 boxes, 110 rows, $2,042M, FY26 "over $1M" supplier file has 278 rows, $3,333M (my name match finds $1,730M, charter schools such as Noble $197M look unmatched) | **None** (`comp_cps.json` unused) | Enrollment on 620 of 640 schools, prior-year actual on 744 boxes |
| Parks | 30 boxes, 115 rows, $723M, **calendar 2019 to 2022 only** | **None** (`comp_parks.json` unused) | Prior-year budget on 6,708 boxes, capital side info on one box |

Vendor payments went through a rebuild after this snapshot, so the City and CPS vendor rows above should be re-counted on the live DB.

## 6. Ranked fix list

Metric-only means the depth number changes but a reader would still land on the same box.

### A. Data we have but did not attach

| # | Change (build script) | $ moved below $10M | Effort |
|---:|---|---:|---|
| 1 | Fix the depth rule inputs. CTPF "Retired teachers" and "Families of teachers who died" boxes have a count but no `unit_amount_cents` (`cps_tree.py`). Give the 26 charter tuition leaves the students x rate their parent already holds | $595.2M + $372.5M (CPS 38.6% to 30.0%, metric-only) | Small |
| 2 | Copy the CTPF pieces code to the MEABF reserve $202.8M (`cps_tree.py`, `leaves_cps.json` A58275) | $202.8M | Small |
| 3 | Attach pay proxies that fit their 2026 line, with a residual: Scheduled Wage Adjustments, Comp Time, CTA detail, Specialty Pay (`city_tree.py` apply_proxy plus the payroll file) | up to $344M | Medium |
| 4 | Run the health method on the other 10 EY lines (`leaves_health.py` then `city_tree.py`) | up to $224M | Small to medium |
| 5 | Pay proxies that exceed the line (Police overtime, Fire 0003): scale 2025 shares to the 2026 line and label "proxy, scaled" instead of side info only | up to $601M | Medium, needs a ruling |
| 6 | Attach `reserve_attribution` named items under the 13 reserve lines still whole, scaled to the cap, residual for the rest (new reader in `city_tree.py`) | $243M, plus $414M named but still $10M+ | Medium |
| 7 | Vendor "paid so far" boxes under the 70 contract lines, labelled as cash to date, group cap respected | $0.7B to $1.2B | Large and a policy change to README rule 4 |
| 8 | City pension retirees x average nested under each 0976 component, as CPS does for its levy | up to $2.8B (metric, proxy) | Small, needs a ruling |
| 9 | Put Midway and Sewer combined principal and interest under one parent. Removes the -$64.1M and -$19.4M Difference boxes and the empty $77.5M leaf | about $10M, but removes 2 negative boxes | Small |
| 10 | Add STSC as a third memo branch (not in the City budget), 6 series $119.6M, ACFR total $449.3M | $0 | Small |
| 11 | CPS debt: split principal and interest per series | $29.6M | Small |
| 12 | Attach `comp_cps.json`, `comp_parks.json`, City 2025 ordinance, CIP plan as side info | $0 | Medium |

### B. Fixes that need no new data (clarity)

| # | Change | Effect | Effort |
|---:|---|---|---|
| 13 | Rewrite the 90 flagged why sentences (`city_tree.py` DEFAULT_WHY and `why_by_path`): carry over the audit's "no payment matches a company" sentence to the 4 highway construction lines ($603M), separate sentences for delegate agency and loan lines, fix the HOME and CDC reserve sentence, give Corporate "For Payment of Bonds" $90.5M its internal-transfer note, give adjustments a sentence | 90 boxes, $3.9B of labels | Small |
| 14 | Skip a level when a box has one child with the same amount (all 2,459 cases), starting with CPS spending type -> account and City fund -> line | removes about 2,400 pointless clicks | Medium |
| 15 | Shorten the City path: show the fund as a label, not a box, for departments with one fund. Median depth 8 to about 6 | fewer clicks | Medium |
| 16 | Merge Parks rounding boxes ($10 or less, 275) into one per parent, drop "$1 rounding" boxes | -275 boxes | Small |
| 17 | Name fixes: "Corporate Fund" boxes get the department in their label, "Other job titles" gets the unit, duplicated CPS capital project names get a project number | readability | Small |

### C. Data that does not exist publicly (or was not reachable)

| Item | $ | Status |
|---|---:|---|
| Finance General 0140 lines (O'Hare $92.2M, Corporate $55.2M) | $147.4M | No fund column in the payments file. OBM email |
| OBM deduction no line explains | $117.0M | OBM email |
| GO older series 2019A, 2020A, 2017A and earlier, per-year | $220.0M | Exists on EMMA, not reachable here. A balance-share guess is possible but would be invented detail |
| O'Hare 2010B and refunded remainders | $122.5M | No column in any fetched statement |
| Water and Sewer residuals | $68.8M, $15.7M | Same |
| CPS budget-only pension reserve, contingency lines ($120M, $100M, $52.9M), Preschool for All providers ($88.1M) | about $480M | No board report names a purchase |
| Parks Soldier Field, harbors, water, electric | $84.4M | No payee-to-line mapping |
| Reserve lines with no project record | 35 of 88 lines | No public project list |
| Pension fund payments to individual retirees, health claims by member | n/a | Privacy |

## Top 10 in one line each

1. CPS unit amounts (pension and charter): metric $968M, small. 2. MEABF pieces: $203M, small. 3. Fitting pay proxies: up to $344M, medium. 4. EY health on 10 more lines: up to $224M, small. 5. Reserve project items: $243M, medium. 6. Scaled over-line pay proxies: up to $601M, medium plus a ruling. 7. Vendor paid-to-date boxes: $0.7B to $1.2B, large plus a ruling. 8. City pension retirees x average: up to $2.8B, small plus a ruling. 9. Midway and Sewer structure fix: removes two negative boxes, small. 10. Rewrite 90 why sentences, then collapse the 2,459 one-child boxes: clarity, small then medium.
