# Leaves of $10M or more: inventory, what splits them, what cannot

Target: every lowest-level number on the site is under $10M ("count x average" counts, for example 8,310 officers x $108K). Under $1M stays the stretch goal.

Reproduce: `python3 scripts/leaves_fetch.py && python3 scripts/leaves_inventory.py` (and `python3 scripts/leaves_hunt.py` for the payment-floor numbers). Output: `data/leaves_over_10m.json` (one record per leaf: budget, path, amount, split source, status, remaining pieces, why-not note). Raw files are in `raw/leaves/` (gitignored). Nothing here is invented: every dollar comes from a file the team already built or from a source fetched in this pass.

## 1. Before and after

"Before" is the best tree the team has today with no splits applied. The City base is the 6694-f78c ordinance with the `finance_general.py` transfer rule applied ($17.14B, the same rule as `reconciliation.md` step 2, so the unexplained $117M is not touched). CPS is the 159,589-row unit x fund x program x account file ($10.25B, negative offset lines counted by absolute value). Parks is the `data/parks_2026.json` tree.

Two "after" columns:
* **Tied only**: leaves whose split ties to the dollar and has no piece of $10M or more (salary tree, Park salary table).
* **With team splits**: also counts "count x average" and "named vendor / award list" splits as done. A leaf that is only partly split is replaced by the pieces that are still $10M or more. This is the number to quote, but read the caveats in section 5.

| Budget | Before: leaves >= $10M | Before: dollars | After, tied only | After, with team splits | Dollars left, with team splits |
|---|---:|---:|---:|---:|---:|
| City | 205 | $15.08B | 168 ($11.87B) | **184** | **$6.61B** |
| CPS | 117 | $5.13B | 117 ($5.13B) | **91** | **$3.53B** |
| Park District | 10 | $0.27B | 9 ($0.26B) | **7** | **$0.14B** |
| **Total** | **332** | **$20.47B** | 294 ($17.26B) | **282** | **$10.29B** |

Why the count barely moves while the dollars drop: a $450M grant line with one $60M named project and a $390M unnamed remainder turns 1 leaf into 2. The dollars that remain at or above $10M are what matter. Of the $10.29B left, **$5.82B sits in whole lines nobody has split at all** (City 46 lines $2.58B, CPS 75 lines $3.11B, Parks 6 lines $0.12B) and $4.47B in named pieces that are themselves $10M or more (mostly single construction contracts and single named grants).

Status of the 332 original leaves (`data/leaves_over_10m.json`, field `status`):

| Status | City | CPS | Parks |
|---|---:|---:|---:|
| split_tied (ties to the dollar) | 37 / $3.20B | 0 | 1 / $0.01B |
| split_proxy (count x average from another year or basis) | 31 / $4.27B | 37 / $1.31B | 1 / $0.06B |
| split_partial (some pieces still >= $10M) | 91 / $5.02B | 5 / $0.71B | 2 / $0.07B |
| unsplit, a source exists but could not be used | 14 / $1.55B | 59 / $2.32B | 0 |
| unsplit, no source found | 32 / $1.03B | 16 / $0.79B | 1 / $0.03B |
| owned by another agent right now | 0 | 0 | 5 / $0.09B |

What each status rests on:
* **City salaries** (e.g. 0005 Police $1.44B, Fire $499M): `data/city_personnel_2026.json`, 7,283 rate rows, ties to the ordinance. Largest single row is 2,148 Police Officers x $111,252 = $239M. This is "count x average" and is accepted under the new target.
* **City premium pay** (overtime, duty availability, holiday, comp time, specialty pay, uniform allowance, wage adjustments): payroll costing `dawh-m56b`, 2025 actuals by department x job title, fetched by `leaves_fetch.py`. It is a different year than the 2026 budget, so it is a proxy. Police overtime, for example, is $200M budget against $236M paid in 2025 over many titles.
* **City pensions** (four 0976 lines and four 097A lines): `data/pensions_2026.json`. This only gives retiree counts and average benefit ("14,895 retirees, $81,154 average service pension"). The City's contribution is not the same as the benefits the fund pays, so it is context, not a split. Marked proxy.
* **City health** (0042 $409M, 0029 $85M and the fund-level copies): EY report page 46, see section 3. Proxy.
* **Grant reserves** (909A, $1.91B): `data/city_grants_2026.json` `reserve_attribution`. 47.3% attributed to named projects/awards as caps. The named pieces over $10M are listed in the JSON.
* **Vendor lines** (professional services, construction, utilities, delegate agencies, repair, IT, rental, waste): the 2025 payments joined to contracts. Each (department, account family) is listed once, on its largest line, with each vendor contract of $10M or more as a remaining piece.
* **CPS**: salary and benefit lines by job title and the public roster (proxy, from `cps_deep.md`), 25 charter campuses as students x per-pupil, capital as 131 projects, bus contracts as vendor totals.
* **Park District**: operating salaries tie; debt by 26 series from the ordinance (Appendix M); pension by retiree count. Four lines belong to the vendor and capital agents.

## 2. Ranked remaining gaps (after team splits)

Largest remaining leaves, largest first. "Whole line" means nothing splits it yet. All amounts are 2026 budget dollars unless noted.

| # | $M | Budget | Leaf | Best known next step |
|---:|---:|---|---|---|
| 1 | 496 | City | O'Hare Airport Fund, interest on bonds | Per-series debt service table in each O'Hare official statement |
| 2 | 303 | City | O'Hare Airport Fund, principal on bonds | Same |
| 3 | 261 | City | CDOT FTA transit formula reserve, part with no named project | CDOT project list (not found, see section 3) |
| 4 | 254 | CPS | Series 2009G principal (final maturity) | Already one bond series, cannot go lower |
| 5 | 203 | CPS | Budget-only pension reserve, non-teacher staff (MEABF) | None public |
| 6 | 193 | City | O'Hare FAA grant reserve, part with no named award | FAA awards list, O'Hare 21 project list |
| 7 | 173 | City | CDOT construction group, no matching 2025 payee | Mid-Year Grants dataset by project |
| 8 | 85 | City | State/Lake Loop Elevated station (one named FTA project) | One project, see section 4 item 5 |
| 9 | 162 | CPS | Budget-only hospitalization reserve | ACFR gives total claims only |
| 10 | 147 | CPS | Facility operations laborer/engineer services, Public Building Commission O&M | JLL contract paid $139.4M in FY26 |
| 11 | 143 | CPS | Vacancy factor (a negative offset to teacher salaries) | None, it is a planned cut |
| 12 | 143 / 142 | City | GO bond interest: 6 series groups known / older series not | Per-series schedules (EMMA) |
| 13 | 132 | City | GO bond principal | Same |
| 14 | 126 | City | Library term notes | None, rolled over yearly |
| 15 | 121 | CPS | Budget-only teacher pension reserve | CTPF valuation (levy, not payments) |
| 16 | 120, 100 | CPS | Contingency lines | None, held back for undecided needs |
| 17 | 108 | CPS | Capital: centralized IT project | Project PDF has no sub-split |
| 18 | 102 | City | CDOT construction, F.H. Paschen / S.N. Nielsen contract 283596 | One contract, see section 4 item 5 |
| 19 | 98 | City | Fire scheduled wage adjustments | Union contracts not settled |
| 20 | 93, 87, 90 | City | Water, Corporate (subsidy) bond lines | EMMA series schedules |
| 21 | 92 | City | O'Hare professional services in Finance General | None found |
| 22 | 88 | CPS | Preschool for All professional services (payment to other governments) | Provider awards, not found |

Full list: `data/leaves_over_10m.json`, filter `status` not in (`split_tied`, `split_proxy`).

Where the remaining $10.29B sits, by kind:

| Kind | Pieces | $M |
|---|---:|---:|
| City grant reserves (not attributable, or a single named project) | 48 | 1,550 |
| City bond interest | 7 | 1,139 |
| CPS bonds (one series x principal or interest) | 30 | 982 |
| CPS pension, insurance, claims reserves | 11 | 831 |
| City construction | 27 | 731 |
| City bond principal | 6 | 727 |
| City professional services | 22 | 726 |
| CPS contracts (facility, buses, tuition, food) | 23 | 755 |
| CPS contingency | 12 | 542 |
| CPS capital (programs and the big IT and emergency repair projects) | 9 | 287 |
| City utilities and materials | 16 | 293 |
| Everything else (City other lines $785M, IT, Parks, judgments, loans, wage adjustments, delegate agencies, claims, CPS charter tuition and other) | 71 | 1,725 |

## 3. Sources hunted and verified

Every row below was fetched in this session. HTTP status and a note on what was inside are from the fetch, not from memory.

| Source | Result | Used? |
|---|---|---|
| EY "Financial and Strategic Reform Options" PUBLISHED version. Link found on chicago.gov/city/en/depts/obm/provdrs/budget.html: `/content/dam/city/depts/obm/supp_info/2026Budget/Financial and Strategic Reform Options - City of Chicago.pdf` | **200, 3.47 MB, 101 pages. Byte-identical (md5 7e1255c5...) to `raw/gap/reform_options.pdf`.** The published file on chicago.gov is itself stamped "CONFIDENTIAL - DRAFT ... [Publication website here]" on page 1, with PDF metadata dated 2025-10-14. So the earlier "local copy may be a draft" worry is resolved: the City posted that file. It is safe to cite as the published report. | Yes, p.46 workforce and enrollment table, pp.43 to 45 benefit options |
| ... what it gives for the health leaves | Active workforce 32,011 (Fire 4,715, Police 9,970, other union 13,834, non-union 3,492). 77% enrolled in PPO, 12% HMO, 11% waive coverage. 41% employee-only, 20% employee+1, 39% family coverage. Average salary $104,000. The procurement section shows the Corporate Fund 2024 "Medical" addressable spend of $248M, but the savings columns are redacted. **It does not give claims by category or by plan.** | Used to express the $409M and $85M health lines as "about 24,600 employees on PPO x about $16.6K" and "about 3,800 on HMO x about $22K". These are rounded-percentage estimates and the lines cover all funds, so they are labelled approximate. |
| CPS FY2025 ACFR (`cps.edu/.../fy25-acfr-final.pdf`) | **200, 226 pages.** Note 11 (pp.91 to 92): self-insured medical claims paid $703.1M in FY25 (up from $616.5M), medical claims reserve $116.3M, workers' compensation claims paid $22.1M, general and auto claims $22.3M. Bond authorizations by series with outstanding principal (pp.169 to 173). I did not find a year-by-year debt service table by series in the pages I read. | Used for the CPS hospitalization reserve note. Gives totals, not a split of the $161.7M line. |
| CPS procurement API `api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026` | **200, 1.75 MB.** Same data already in `data/cps_supplier_payments_*`. | Already used |
| CPS pooled contract awards `GetPooledContractAwards?reportyear=2026` | **200, 19 KB.** Board report number, title, authorized amount, no vendor. | Not useful for splitting |
| Socrata `9v3e-pcjs` (Workforce Vacancies), `xzkq-xp2w` (Employee Salaries), `dawh-m56b` (payroll costing) | All **200**. Payroll costing is the one that splits premium pay: aggregates by appropriation x department x title for 2025 fetched (1,278 rows). Vacancies (26,321 positions, 3,857 vacant) only explains turnover, which is already in the salary tree. Employee Salaries gives individual names, which is below any budget line and not needed. | payroll costing yes |
| Socrata `7tg5-i782` (ARPA expenditures) | **200.** History 2021 to 2026, not 2026 budget. | No |
| O'Hare bonds site (`cityofchicagoinvestors.com/ohareairportbonds`) | Documents page **200**, lists 50 downloadable documents including 2026B/C/D Official Statements (Sept 2026), the 2025 financial statement and the 2025C to 2025G statements. **The download links return the BondLink web page, not the PDF, when fetched by script** (80 KB HTML), so the series tables could not be pulled. This is the single most valuable unfetched source for the $496M and $303M leaves. | No (blocked) |
| EMMA (`emma.msrb.org`) | **200** but only the home page shell, as `pensions_debt.md` already found. | No |
| OBM Tableau "Mid-Year Report Data Directory" | **200**, 2 KB bot-challenge shell. No data without a browser. | No |
| CDOT capital project list (`chicago.gov/.../cdot/.../capital-improvement-program.html`) | **404.** | No |
| O'Hare / flychicago.com CIP page | **404.** | No |
| Chicago public payments (`s4vu-giwb`, 2025) | Already local. New in `leaves_hunt.py`: of vendor contracts, 134 are still $10M or more at (vendor, contract) level ($4.25B), 85 at vendor x contract x month ($1.92B), and **59 single vouchers are $10M or more ($1.29B)** after dropping direct vouchers to pension funds, banks and governments. Biggest single check: $90,000,000 to F.H. Paschen / S.N. Nielsen on contract 283596 (CDOT). Blue Cross checks are about $38M to $44M each. | Yes, the "payment floor" |

Not done in this pass (so no claim made): CPS Board Reports (needs a per-report fetch and parse), Mid-Year Report tables, TIF project list and the Mid-Year Grants dataset re-run (both already used by the grants work, see `grants_capital.md`), a bond-series O'Hare/Water/Sewer/Midway schedule (blocked, above), and any CDOT or O'Hare 21 project list newer than the 2025 to 2029 CIP already parsed.

### Finding that matters for the health lines
No public document gives City health insurance by plan or claims category. The deepest public numbers are enrollment shares (EY p.46) and the payments to Blue Cross ($610M in 2025) and Caremark ($129.6M). The Blue Cross payments are checks of roughly $38M to $44M each, so even the payment ledger stays above $10M per check.

## 4. What this changes, and what the target needs

1. **Salaries are done.** 37 City leaves, $3.2B, and all of CPS and Parks salary dollars become "N people x $average" and are under $10M per row (the largest is $239M for a pay rate row, but 2,148 people x $111K is a count x average).
2. **Premium pay, pensions, health and charter tuition can use the same device**, with the caveat that they are other-year or rounded proxies.
3. **Bonds are the biggest hole.** City + CPS + Parks bond lines are about $3.9B of the remaining $10.3B. Series-level schedules exist (official statements) but the O'Hare/Water/Sewer/Midway ones could not be fetched by script. Doing that by hand from the 50 documents on the O'Hare site, plus EMMA for Water and Sewer, would clear most of $1.6B. Each CPS series is already the lowest level (one bond), see section 5.
4. **Grant reserves ($1.6B left) need project lists** from CDOT and Aviation that are not published in a form the team has found.
5. **Single contracts and checks over $10M** (Paschen $90M check, Blue Cross, Turner Paschen at O'Hare) cannot be split by public payment data. Payment data stops at the check.

## 5. Caveats on the "after" numbers

* Pieces from vendor groups are 2025 payments, not 2026 budget, and are capped at the budget dollars in the lines they sit under so they never count more than the budget. A 2025 payment to a vendor is not proof that vendor gets paid from this exact line in 2026.
* "Count x average" for premium pay and charter tuition uses other-year or other-source counts. If the site requires a tie to the dollar, use the "tied only" column ($11.87B left in City, $5.13B in CPS).
* CPS bond lines are counted as unsplit because the series is already the lowest level. They are leaves of the accounting, and a leaf of a single bond payment is the correct place to stop, so an exception for single-bond lines is recommended (30 pieces, $982M).
* The CPS capital lines were joined to the 131 projects as a group. The project list differs from the fund lines by $3,874 (see `cps_deep.md`).
* Parks lines for Soldier Field, harbors, utilities and the capital transfer ($95M) are being worked by other agents, and the inventory leaves them as "other_agent".
* The City "before" count uses the ordinance line as the leaf. The salary lines are leaves only until the personnel tree is attached, so this is the most pessimistic starting point.

## 6. "Why we can't go deeper": one sentence each

For the site, per kind of leaf. These are also stored per leaf in `data/leaves_over_10m.json` (`why_cant_go_deeper`).

| Kind | Sentence |
|---|---|
| Bond interest or principal (City and CPS) | "This is the yearly bill for many separate bonds, and the budget lists the total but not each bond's share." (CPS single bond: "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself.") |
| Library term notes | "These are short-term notes that get paid and re-borrowed every year, so there is no list of separate loans." |
| Pensions (City, CPS, Parks) | "The City sends one payment set by law to the retirement fund, and the fund then pays thousands of retirees." |
| Grant reserve with no project list | "This is money from one grant the City has been promised but has not yet decided how to spend." |
| Single big construction or professional contract | "A few big companies each get one large contract payment, and the City does not publish smaller pieces of one contract." |
| Claims (workers' comp, injury, insurance) | "These are insurance and injury claims paid one person at a time, and privacy rules keep each claim out of public budget data." |
| Wage adjustments held centrally | "This is money set aside for union raises that are not settled yet, so nobody can say yet which workers will get how much." |
| Taxes the City expects not to collect | "The City sets aside this money because some property taxes are never paid, and nobody knows in advance whose." |
| Tax passed to another agency (CTA, sanitary district) | "The City collects this tax and hands the whole amount to another agency in one payment." |
| CPS budget-only reserves (pension, insurance, claims) | "This is a reserve the district sets aside for pensions, health insurance or claims, and the real bills arrive later from the insurers and pension funds." |
| CPS health reserve | "CPS pays most health bills as they come in, so the reserve is a guess at claims that have not happened yet." |
| CPS vacancy factor and negative offsets | "This is a planned cut that offsets spending counted elsewhere, so there is nothing to itemize." |
| CPS contingency | "This is money held back for things that have not been decided yet, so it has no purchases to list." |
| CPS bus companies | "The bus companies are paid by contract, and CPS publishes each company's yearly total but not each route." |
| CPS multi-school capital programs | "Several big programs (like fixing fire alarms in many schools) are one budgeted amount, and CPS does not publish the dollars for each school." |
| CPS vendor contracts | "The money goes to a few large companies, and CPS publishes what each was paid but not which budget line it came from." |
| Parks museum subsidy | "State law sets one museum payment, and the Park District does not publish how it is divided among the 11 museums." |
| Parks managed assets (Soldier Field, harbors) | "One company runs this place and the Park District does not publish payments by vendor." |

## 7. Files

| File | What |
|---|---|
| `scripts/leaves_inventory.py` | Builds the inventory and the totals above |
| `scripts/leaves_fetch.py` | Fetches the 2025 payroll costing aggregate (`dawh-m56b`) into `raw/leaves/` |
| `scripts/leaves_hunt.py` | Payment floor numbers (`raw/leaves/leaves_payment_floor.json`) |
| `data/leaves_over_10m.json` | 332 leaves with split source, status, remaining pieces and the one-sentence reason |
| `raw/leaves/` (gitignored) | Payroll aggregate, EY report text, CPS ACFR text, O'Hare document pages, OBM page |

---

# Round 3 (2026-10-01): decisions applied, more splits, what is left

Reproduce: `python3 scripts/leaves_usa_sub.py; for s in pensions health grants cps wages parks contracts; do python3 scripts/leaves_$s.py; done; python3 scripts/leaves_inventory.py`. Add `LEAVES_NO_OVERRIDES=1` to the last command to print the step 1 numbers (writes `raw/leaves/leaves_step1.json`, not the data file). New split files: `data/leaves_pensions.json`, `leaves_health.json`, `leaves_grants.json`, `leaves_cps.json`, `leaves_wages.json`, `leaves_parks.json`, `leaves_contracts.json`. Each record names its leaf with `match_path_contains`, and `scripts/leaves_inventory.py` ingests them. Work was done by one agent (the swarm tool refused sub-agents for a worker), so no parallel workers were used.

## R3.1 Before and after

Rules now in the inventory: (1) one bond series x principal or interest, or one loan, is `accepted_single_obligation` even when over $10M. (2) The City base now also removes the named pieces of OBM's printed deduction that `research/transfer_residual.md` and `reconciliation.md` can reproduce: Library term notes $125.9M, matching grant funds, Finance General "Transfer ..." lines and Appendix A/B "For Services Provided by" lines, 66 lines and $180.6M of leaves. The unexplained $117.0M is not attributable to any line, so it is not removed. City base moves from $17.14B to $16.96B. (3) Park capital and vendor files and the budget PDF were used. (4) `data/city_bond_series_2026.json` did not exist when this ran. The inventory ingests it when present, using an assumed schema (`series` or `rows`, each with fund, kind and amount), so a different schema needs a small edit in the "City bond series" block.

| Stage | City leaves >= $10M | CPS | Parks | Total count | Total dollars |
|---|---:|---:|---:|---:|---:|
| Round 2 (team splits) | 184 / $6.61B | 91 / $3.53B | 7 / $0.14B | 282 | $10.29B |
| Step 1: decisions, residual pieces, parks files, no new splits | 181 / $6.46B | 61 / $2.55B | 6 / $0.12B | 248 | $9.13B |
| **Step 2: with the Round 3 splits** | **177 / $6.29B** | **53 / $2.06B** | **4 / $0.08B** | **234** | **$8.44B** |
| Step 2, tied-only column | 165 / $11.72B | 87 / $4.15B | 6 / $0.18B | 258 | $16.05B |

Step 1 drops CPS by $0.98B because the 30 single-series bond leaves are accepted. The step 2 drop of $0.7B is mostly proxy splits (count x average, labelled), so read it as "explained at a person or project level, with a proxy", not "tied to the dollar". The tied-only column barely moves because pension, health and wage splits are proxies by nature. Park museums (11 institutions, ties exactly) and the capital transfer (named uses and a derived residual) are tied.

Where the $8.44B sits now (234 pieces):

| Kind | Pieces | $M |
|---|---:|---:|
| City grant reserves and grant-funded construction | 76 | 2,290 |
| City bonds and loans (O'Hare, Water, Sewer, Midway, older GO, term notes: waiting on the bond agent) | 15 | 1,824 |
| City professional services, utilities, judgments (single contracts, vouchers) | 38 | 1,356 |
| CPS reserves, vacancy factor, contingency | 23 | 1,162 |
| City other lines (taxes not collected, Medicare, workers' comp, IT, etc.) | 48 | 823 |
| CPS contracts, tuition, other | 21 | 609 |
| CPS capital (programs, central IT, emergency repairs) | 9 | 287 |
| Park District | 4 | 84 |

The 15 bond pieces ($1.82B) become `accepted_single_obligation` leaves once the bond agent's file lands, which would take the total to about $6.6B and about 219 pieces. Nothing was done to those lines here.

## R3.2 What each attack found

**a. City pensions ($2.84B, 8 lines, `scripts/leaves_pensions.py`).** Per fund the valuation prints total normal cost, member contributions and net employer normal cost, and the ADC with its amortization payment. Statutory contribution minus net employer normal cost is the part that pays down the unfunded liability. Derived: PABF $1,040.3M = $222.4M net normal cost + $817.8M toward the $13.8B unfunded liability. MEABF $965.0M = $146.9M + $818.1M. FABF $441.7M = $93.0M + $348.7M. LABF $136.6M = $26.6M + $109.9M. All four statutory amounts are far below the ADC (PABF short $376.4M, MEABF $385.4M, FABF $147.0M, LABF $33.8M, derived). The advance (097A) lines are one voluntary payment each. Benefit types are counts x averages: PABF 11,271 service annuities x $81,154, 3,068 widows, 166 children, 177 duty disability, plus refunds $11.7M and death benefits $2.0M from the fund's 2025 statements. MEABF 21,874 retired x $49,104, 3,714 spouses x $19,536, 119 reversionary x $4,932. FABF 4,006 x $96,516, 1,191 spouses x $37,284. LABF 2,506 x $65,230, 934 spouses x $21,301. **The contribution is not the benefit payment**, so benefit-type dollars are a proxy allocation by share of benefit dollars and the status is `split_proxy`. The $818M "remainder" is still a big number as dollars and is not smaller than $10M. It is the debt payment set by state law. Parks pension: employer normal cost $9.4M, remainder $53.9M (Segal valuation, ADC policy $88.9M).

**b. City health care (`scripts/leaves_health.py`).** No public document splits claims by plan, covered lives or bargaining unit. What exists: EY p.46 enrollment shares by unit (Fire 4,715 staff, 85% PPO, 9% HMO, 7% waive; Police 9,970, 83/12/6; other union 13,834, 72/15/13; non-union 3,492, 71/8/21), City ACFR note 12 (PPO self-insured, HMO partially insured), and Payments. The $408.7M line is shown as 24,722 PPO enrollees x $16,530 by unit, the $85.2M HMO line as 3,974 enrollees x $21,432 (equal per enrollee, rounded shares, employees not dependents, so proxy). Payments to Blue Cross in 2025 were $610.0M in 68 checks and 14 of those are $10M or more (largest $43.6M), Caremark $129.6M in 53 checks. Probed 4 chicago.gov DHR benefits URLs, all 404, so no rate sheet.

**c. Grants (`scripts/leaves_grants.py`).** Fetched and used: FAA FY2025 AIP grant list (HTTP 200): 9 of 9 O'Hare FAINs match the named awards and give the project type (runway, taxiway, terminal, service road). USASpending sub-awards to the City for ALN 20.205 and 20.507: 200 but 0 rows (IDOT passes money through without City-level sub-awards). USASpending prime awards to CDOT: only IL-2016-002 State/Lake Loop Elevated Station ($414.6M obligated, $84.8M outlays) is large. Mid-Year Grants (2025-06-01 extract): the FTA reserve is one project funded from four sources (STP $102.1M, CMAQ $59.5M, STP $18.2M, carbon reduction $15.0M unspent, caps). That moves $261M "not attributable" in the FTA reserve down to $32.9M above the one award. FHWA reserve: 50 projects, four of them $10M or more (Columbus Ave grade separation $36.2M, Canal Street viaduct $19.4M, Montrose Harbor underpasses $10.9M, Columbus Ave second record $10.0M). CDBG-DR Action Plan: the six stormwater lines sum to $390,279,000 against the plan's $390,277,600 program (Table 38), a $1,400 gap. Local sewer line construction $221.3M becomes about 26 miles x the plan's $8.5M per mile (proxy, no street list). Permeable alleys ($67.1M) and wing storage ($62.1M) have no unit costs, so they stay unsplit. Not reachable: flychicago.com O'Hare 21 pages (403, 404), CDOT capital list (404), FAA FY2026 list (404). The O'Hare unattributed remainder stays $193.5M, FHWA unattributed $40.9M, Midway unattributed $72.7M. All attributed amounts are caps, not exact splits.

**d. Wages and overtime (`scripts/leaves_wages.py`).** Police overtime $200M (budget): 2025 actual by title, 7,370 police officers x $19,005, 1,327 sergeants x $26,440, 1,157 detectives x $23,584, 51 titles. Mid-Year report: CPD overtime budget $203.9M and $59.5M spent through period 5 (29.2%). Fire 0003 $98.0M: Fire titles in the 2025 Finance General 0003 account totalled $208.9M, firefighter-EMT 1,815 x $37,820 and so on, which was contract back pay and lump sums. Status proxy. The $262.3M Finance General line already had a payroll-costing proxy.

**e. CPS (`scripts/leaves_cps.py`).** Pension levy $602.3M: CTPF valuation Table 11 counts x averages (23,350 retirees x $64,860, 408 disabled x $47,128, 3,399 beneficiaries x $29,749) and the FY26 required contribution components ($646.2M Board, $17.3M additional Board, $16.3M additional State, $346.8M State normal cost). ESP pension $202.8M: MEABF counts x averages, with the finding that the budget book makes a $175M reimbursement to the City contingent on new revenue (bb26 p.15). Hospitalization $161.7M: shares by FY26 vendor payments (HCSC $550.0M, Caremark $174.7M, Delta Dental $20.8M, Standard $16.0M), proxy. Special education transportation $146.7M: about 1,200 routes, 14,000 students, 20 vendors from the budget book, so about $122K per route, proxy. PBC O&M $146.6M: one Jones Lang LaSalle contract, 803 buildings, about $183K per building (equal share, proxy), Board Report 26-0319-PR5 authorizes $328.87M for 2026 to 2028. **Not split:** the three contingency lines ($120M, $100M, $52.9M), no Board Report names a spend. Preschool for All $88.1M, no provider awards found. Budget-only A58115 reserve $120.6M. Vacancy factor $143.3M.

**f. Single large contracts (`scripts/leaves_contracts.py`, `data/leaves_contracts.json`).** For every 2025 vendor x contract total of $10M or more (122 items), vouchers (checks) were summed and listed. **52 single vouchers are still $10M or more, $1.15B in total**: Blue Cross 14 checks, Loevy & Loevy 6, Paschen contracts 5, Clark-O'Neil 4, AECOM/Hunt/Clayco 3, Caremark 3 and others. Revision history from Contracts rsxa-ify5 (HTTP 200 for all 14): contract 283596 State/Lake station is $444.3M at revision 0 plus $103.9M at revision 2 (2026-06-30), total $548.2M, with $176.7M paid across all years in 32 vouchers and one $90.0M check on 2025-06-17. Other revision histories: 69568 Connect Chicago $210M + $30M + $92M, 25743 AOR Transit 13 revisions $644.0M, 27075 Skyline 16 revisions $239.7M, 52685 CNECT 5 revisions $259.0M. A voucher is the lowest public level, and no task-order or project field exists in Payments, so these cannot go below the check.

## R3.3 Remaining leaf reasons

Every remaining leaf carries a one-sentence `why_cant_go_deeper` in `data/leaves_over_10m.json`, and the same sentences are in `remaining_pieces_over_10m`. Round 3 added sentences for pensions, health, grant reserves, stormwater, CPS reserves, buses, building contracts, Soldier Field, harbors and utilities. Examples:

* Soldier Field: "One company runs Soldier Field for the Park District, and the District does not publish what it pays that company for each job."
* Pensions: "The City sends one payment set by law to the retirement fund, and the fund then pays thousands of retirees, so the public records stop at how many retirees there are and what the average one gets."
* Health: "The City pays hospital and doctor bills for thousands of workers as the bills come in, and it does not publish who each worker is or what each claim cost."
* Stormwater: "The plan says how many miles of sewer it hopes to fix and what a mile costs, but the streets have not been picked yet."

## R3.4 Honest limits

* Without FOIA the biggest remaining gaps ($8.4B) are 76 grant pieces with no project list, single vouchers and contracts, bond series (waiting on the other agent), CPS reserves and a handful of Finance General lines with no public detail. The $10M goal is not reachable from public data on these.
* "Team" counts treat count x average proxies as resolved. If you want only exact splits, use the tied-only row ($16.05B across 258 leaves).
* Park Museum remittance and the capital transfer are the only new dollar-for-dollar ties. Pension, health, transport and PBC splits are equal-share or share-of-dollars proxies, each labelled in its JSON.
* New files: `scripts/leaves_{pensions,health,grants,cps,wages,parks,contracts,usa_sub}.py`, `data/leaves_{pensions,health,grants,cps,wages,parks,contracts}.json`. Raw in `raw/leaves/` and `raw/leaves/r3/` (gitignored).
