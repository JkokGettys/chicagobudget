# Linking non-salary City budget lines to vendors, contracts and nonprofits

Research for the Chicago budget explorer. Scope: City of Chicago only (the CPS and Park District work lives elsewhere). Everything below is computed by `scripts/contracts_build.py` from public Chicago Open Data. Nothing is typed in by hand except the mapping tables, and those are documented here.

## Short answer

1. **Yes, the non-salary City budget can be tied to named vendors, but only to a point.** The 2026 ordinance has **$5.37B of "vendor-payable" budget** (28.8% of $18.67B). Matching it to 2025 payments on named contracts explains **$3.08B (57%) department by department**, and **$5.07B (94%) when each account family is matched citywide**. The gap between the two is mostly a department-name problem (health care is budgeted in Finance General but paid by the Department of Finance, IT is budgeted in 35 departments but mostly paid through Technology & Innovation). It is not missing data.
2. **The contract level does not get most dollars under $1M.** Only **$440M of the $5.37B (8.2%)** is both explained and sitting in a (department, vendor, contract) item under $1M (citywide matching: $530M, 9.9%). About 90% of vendor-payable dollars are in vendor contracts of $1M or more. Splitting further by month gets 28% of paid dollars under $1M, and splitting down to the single voucher gets 43%. **56.8% of paid dollars ($3.65B in 1,096 vouchers) sit in single vouchers of $1M or more, so a hard floor exists** for professional services, construction, health care and development deals.
3. **Delegate agencies (nonprofits) are the one family that drills well.** $621M paid in 2025 to 639 (department, agency) pairs. 82% of the pairs and 21% of the dollars are under $1M. At (agency, contract) level, 93% of items and 42% of dollars are under $1M. At voucher level only $48M (7.7%) is in vouchers of $1M or more.
4. **The $6.07B of blank-department payments resolve almost completely.** $6.04B (99.5%) gets a department or a Finance General bucket by rule. $12.7M (0.2%) is unresolved, $12.8M (0.2%) is on contracts whose own department is blank or unmappable.

## Datasets checked

| Dataset | ID | Rows | Verdict |
|---|---|---:|---|
| Contracts | `rsxa-ify5` | 186,101 (89,045 contract numbers, 14,152 vendor ids) | **Core.** One row per revision. Updated daily. |
| Payments | `s4vu-giwb` | 468,630 all years (115,810 in check year 2025, $10.66B) | **Core.** Row level since 2022, rolled up before that. Checked: 2025 rows re-pulled from the full file equal the local `city_payments_2025.csv` (115,810 rows). |
| 2026 Budget Ordinance | `6694-f78c` | 3,268 | **Core.** $18,668,568,460. |
| Mid-Year Grants report | `iyu8-jkf8` | 509 rows at 2026-05-31 ($4.08B) | **Useful.** Project level grants by fund. Explains CDOT, DFSS, CDPH, Housing, Police, Fire grants. Nothing for Aviation or Environment. |
| TIF Annual Report, vendors paid over $10K | `ijrh-ktm6` | 561 rows for 2025 ($559.4M) | **Useful** for TIF district spending. 82% of rows but only 14.5% of dollars are under $1M. |
| TIF Annual Report, projects | `72uz-ikdv` | 543 rows for 2025 ($386.9M) | Useful. |
| TIF funded RDA and IGA projects | `mex4-ppfc` | 762 deals, $6.45B approved | Useful as a deal list. Approved amounts, not annual spend. |
| Vendor Payments, New Arrivals | `gxzc-43gg` | 4,206 rows, $639.6M (2022 to 2025) | Useful. Favorite Healthcare Staffing alone is $400.4M. 86 vendors. |
| Employee Payroll Data (payroll costing) | `dawh-m56b` | 4.86M rows | **Overtime source.** Too big to export, so we pull a 2025 aggregate. OT pay elements total $467.0M in 2025 against $422.3M budgeted in account 0020 for 2026. Police $236.3M vs $204.6M budget, Fire $90.9M vs $93.4M. |
| Current Employee Names, Salaries | `xzkq-xp2w` | 31,880 | Salary side, belongs with the personnel work. |
| Employee Overtime and Supplemental Earnings | 2012 to 2022 only | by year | Stale. Use payroll costing instead. |
| DFSS Delegate Agencies | `jmw7-ijg5` | 1,354 | **Stale (2015)**, site list only, no dollars. Not useful. |
| List of Contractors Doing Business with the City | `5wd9-d675` | 4,989 | **Stale (2014).** Not useful. |
| Employee Reimbursements | `g5h3-jkgt` | 5,870 ($10.8M) | Tiny, travel reimbursements. |
| Debarred Firms | `y93d-d9e3` | 164 | Not needed for budget depth. |
| Minority and Women Business Payments | `fa8m-mqz6` | 18 quarters | Aggregates only. |
| ARPA Road to Recovery grants | `9yp3-9pdz` | 67 programs | Program totals only. |
| City Vendor, Contract and Payment Search web app | `webapps.cityofchicago.org/VCSearchWeb` | n/a | A form front end over the same Payments and Contracts data (the Payments dataset description says it is extracted from it). It has no API, so it adds nothing for bulk work. Contract PDFs are linked from Contracts (`contract_pdf`) for 45% of contract numbers. |

There is **no separate delegate agency award dataset**. Delegate agency awards are rows in Contracts with `contract_type = DELEGATE AGENCY` (67,618 rows plus 1,110 "Delegate Agency"). The DFSS program is encoded in the contract description (for example `DFSS-CORP-YS-SYEP`, `DFSS-ECBG-CS-CEL`).

## Mapping approach

### 1. Department names

Contracts has 71 distinct department spellings, Payments 42 (2025) and the 2026 ordinance 40 departments. `scripts/contracts_build.py` holds an alias table that maps every spelling to a 2026 department number. Rules:

- Predecessor departments go to their 2026 successor: General Services, Assets Information & Services and Fleet Mgmt go to Fleet and Facility Management (38). Business & Information Services and Innovation & Technology go to Technology and Innovation (6). Planning & Development, Zoning and Economic Development go to Planning and Development (54). Dept on Aging, Children & Youth Services and Workforce Development go to Family and Support Services (50). Revenue and General Accounting go to Finance (27). O'Hare Modernization Program goes to Aviation (85).
- Typos are handled (`DEPARTMENT OF ENVIROMENT`).
- **Result:** 0 of the department names in Payments are unmappable. In Contracts, three names cannot be placed and are reported rather than guessed: Office of Compliance (101 rows), Office of Cable Communication Adm (32), Citywide/Multiple (23).
- Note that **City Council (15) and the Community Commission for Public Safety and Accountability (62)** appear in the budget but not by name in Payments. They are reached by voucher prefix (below).

### 2. Resolving the blank department on payments

62,585 rows and $6.07B of 2025 payments have no department. Resolution order, with 2025 dollars:

| Route | $ | Rows |
|---|---:|---:|
| Central Finance direct voucher (voucher prefix `PV27`) assigned to Finance General | $3,847.2M | 7,512 |
| Contract number join to Contracts, take that contract's department | $1,069.1M | 14,840 |
| Payroll deduction voucher (`PVPR`: union dues, credit unions, deferred comp, pension remittances) | $701.8M | 2,416 |
| Direct voucher, department read from the voucher prefix | $392.7M | 34,368 |
| Contract join, department from a prefix in the contract description (`CDPH-`, `MOPD-`, `OBM-`, `DOF-`, `DPD-`) | $29.3M | 1,406 |
| Contract join, but the contract's own department is blank or unmappable | $12.8M | 175 |
| Unresolved (includes $9.5M on contract numbers not in Contracts) | $12.7M | 1,868 |

The **voucher prefix** is the useful discovery: voucher numbers like `PV84258411725` start with `PV` plus the two digit budget department number (84 is CDOT, 88 Water, 85 Aviation, 38 Fleet and Facility, 06 Technology, 27 Finance). Where a payment has both a department name and a prefix, they agree on **98.5% of dollars (85.7% of rows)**, so the prefix is a sound fallback for direct vouchers. Capital vouchers (`PVCI…`, `CVIP…`) carry no department in the number, so those need the contract join.

Of the $4.94B of direct vouchers (contract number `DV`, no contract), vendor names split into these classes (regex rules in `DV_RULES`, name based and approximate):

| Class | 2025 $ |
|---|---:|
| Pension funds, annuity and retirement payees | $1,934.9M (of which $536.8M are `PVPR` payroll remittances) |
| Cook County and State of Illinois treasurers, courts | $1,000.6M |
| Banks and bond trustees (debt service) | $979.5M |
| Other (small vendors, each under $1M in total for most) | $448.5M |
| Law firms and settlements | $336.9M |
| CTA, PBC, Park District, CPS pass-through | $134.6M |
| Insurance administrators | $66.6M |
| Utilities | $43.4M |

Pensions, bank/debt, tax remittances, payroll deductions and agency pass-throughs ($4.21B in total) are **not** vendor spending and are excluded from the vendor coverage numbers. They belong to the Pensions, Debt service and Finance General work.

### 3. Contract type to budget account family

The ordinance does not say which vendor is behind an account, so we map in two steps. First every 2026 account code goes to a family (`account_family()`). Second every contract goes to the same family from its `contract_type`, with description keywords refining a few types (`classify_contract()`).

| Family | Budget accounts | Contract types and rules |
|---|---|---|
| PROF Professional & technical | 0140 to 0148, 0123, 0124, 0128, 0165, 0169 | `PRO SERV CONSULTING` (over and under $250K), `PRO SERV`, `PRO SERV-AVIATION`, `ARCH/ENGINEERING*` |
| IT | 0138, 0139, 0149, 0154, 0312, 0446 | `SOFTWARE`, `HARDWARE`, or PRO SERV with IT words in the description |
| TELECOM | 0181, 0189 to 0197, 0423 | `TELECOMMUNICATIONS` |
| DELEGATE | 0135 plus program accounts 9142, 9143, 92xx | `DELEGATE AGENCY`, `DPS DELEGATE AGENCY` |
| CONSTR | 0540, 0521, 9097 | `CONSTRUCTION*`, `JOC`, `DEMOLITION`, `ROOFING`, and PRO SERV whose description is "construction management at risk" (O'Hare 21) |
| FACILITY | 0125, 0160 to 0163, 0176, 0188, 0526, 9112 | `WORK SERVICES / FACILITIES MAINT.`, `WORK SERV-AVIATION`, `HIRED TRUCK` |
| WASTE, RENTAL | 0185 / 0155, 0157, 0159 | Facility contracts whose description has waste or rental words |
| UTIL, FUEL | 0331, 0332, 0322, 0183 / 0315, 0320 | Commodities with fuel words, or electricity and gas supply contracts |
| MATERIALS, EQUIP | 03xx / 04xx | `COMMODITIES*`, `VEHICLES/HEAVY EQUIPMENT (CAPITAL)` |
| BENEFITS | 0029, 0042 to 0056, 0172, 0937 | `COMPTROLLER-OTHER` with medical, dental, pharmacy, insurance words |
| LEGAL | 0931, 0934, 0145 | Direct vouchers to law firms and settlement payees |
| DEVLOAN | 9103, 0991, 9102 | `COMPTROLLER-OTHER` with RDA, TIF, loan, IGA, CPS, Park District, CTA words |

Excluded from the vendor side (non-vendor kinds): personnel, pensions, debt, reserves, internal transfers, loss in collection and CTA tax pass-throughs.

Budget by kind (2026): personnel $4,941.7M, pension $2,843.2M, debt $1,975.2M, reserve $1,850.1M, transfers $1,547.9M, **vendor-payable $5,369.2M**, taxes and pass-throughs $141.2M.

Facts that shaped the rules (all tested):

- **`award_amount` is incremental.** Each revision row is a change, so a contract's total is the sum over revisions. For contracts with 3 or more revisions and 2025+ payments, payments were at or below the summed award 88.6% of the time (max revision: 52%, last revision: 3%). `COMPTROLLER-OTHER` (ordinance based agreements) is the biggest type: **$1.74B paid in 2025**, led by Blue Cross $610M, Caremark $129.6M, Constellation energy $92.2M and many TIF/RDA developer deals.
- 44,585 contract rows (24%) have no contract type (legacy imports). Payments touching them are small. 2025 payments are $5.72B on 3,819 contracts plus $4.94B of direct vouchers. **Only $9.5M (0.09% of 2025 payments) are on contract numbers missing from Contracts.**

## Coverage: how much of each department's non-salary budget is explained

Definitions. *Vendor-payable budget* is the 2026 ordinance lines in vendor families. *Explained* is, for each department and family, `min(2026 budget, 2025 paid on named vendors)`, so overspending in one family never hides a shortfall in another. *Under $1M* means the explained dollars that sit in (vendor, contract) items under $1M. Both years differ, and payments are checks (cash), not appropriations, so read these as plausibility checks and not exact reconciliation.

| Department | Vendor-payable budget 2026 | Paid 2025 to named vendors | Explained | Explained and under $1M | Share of paid $ in items under $1M |
|---|---:|---:|---:|---:|---:|
| Finance General | $1,367.2M | $418.6M | $187.0M | $26.8M | 10% |
| Chicago Department of Transportation | $827.3M | $788.8M | $641.1M | $35.8M | 8% |
| Chicago Department of Aviation | $824.2M | $1,319.5M | $584.8M | $20.5M | 3% |
| Family and Support Services | $511.6M | $486.8M | $436.7M | $151.6M | 34% |
| Water Management | $434.9M | $464.2M | $357.9M | $21.7M | 8% |
| Fleet and Facility Management | $375.3M | $645.5M | $334.8M | $20.8M | 6% |
| Public Health | $151.9M | $153.9M | $123.5M | $74.9M | 60% |
| Police | $148.5M | $35.5M | $22.9M | $10.6M | 43% |
| Streets and Sanitation | $126.0M | $119.9M | $75.0M | $2.4M | 8% |
| Planning and Development | $126.0M | $560.0M | $121.3M | $10.4M | 10% |
| Office of Public Safety Administration | $79.6M | $47.1M | $26.5M | $5.2M | 13% |
| Finance | $68.7M | $865.3M | $30.9M | $3.4M | 1% |
| Housing | $54.9M | $38.4M | $18.4M | $7.9M | 21% |
| Technology and Innovation | $50.3M | $183.0M | $46.6M | $1.4M | 4% |
| Cultural Affairs and Special Events | $46.2M | $49.2M | $20.4M | $17.9M | 62% |
| Fire | $44.4M | $32.4M | $6.0M | $1.5M | 34% |
| Office of Budget and Management | $29.9M | $13.7M | $3.4M | $0.9M | 8% |
| Board of Election Commissioners | $18.5M | $9.9M | $1.4M | $0.9M | 48% |
| Public Library | $16.4M | $12.5M | $12.2M | $5.3M | 44% |
| Business Affairs and Consumer Protection | $14.9M | $18.9M | $5.4M | $5.4M | 87% |
| City Council | $6.9M | $3.7M | $3.6M | $3.6M | 100% |
| Office of City Clerk | $6.8M | $2.9M | $2.6M | $2.6M | 100% |
| OEMC | $5.8M | $34.2M | $5.6M | $1.0M | 10% |
| Mayor's Office for People with Disabilities | $5.1M | $7.4M | $4.6M | $1.8M | 40% |
| Administrative Hearings | $4.9M | $2.9M | $0.1M | $0.1M | 100% |
| Law | $4.2M | $78.6M | $2.8M | $1.4M | 25% |
| Buildings | $3.6M | $10.9M | $1.1M | $1.1M | 38% |
| Office of the Mayor | $3.4M | $2.2M | $0.6M | $0.6M | 100% |
| City Treasurer | $2.2M | $2.2M | $0.3M | $0.3M | 100% |
| Inspector General | $2.0M | $1.9M | $0.2M | $0.0M | 5% |
| Animal Care and Control | $1.6M | $0.8M | $0.1M | $0.1M | 100% |
| Procurement Services | $1.6M | $1.0M | $0.7M | $0.7M | 100% |
| COPA | $1.6M | $0.6M | $0.5M | $0.5M | 100% |
| Environment | $1.4M | $2.2M | $0.9M | $0.9M | 100% |
| Human Resources | $0.7M | $7.2M | $0.5M | $0.3M | 41% |
| Community Commission for Public Safety | $0.3M | $0.6M | $0.1M | $0.1M | 100% |
| Police Board | $0.2M | $0.2M | $0.0M | $0.0M | 100% |
| Commission on Human Relations | $0.1M | $0.1M | $0.0M | $0.0M | 100% |
| License Appeal Commission | $0.1M | $0.0M | $0.0M | $0.0M | 100% |
| Board of Ethics | $0.1M | $0.0M | $0.0M | $0.0M | 100% |

How to read the oddities:

- **Finance General explains only $187M of $1,367M** because $787M of its vendor-payable budget is employee health care, which is *paid* through the Department of Finance (Blue Cross $610M, Caremark $129.6M). The Department of Finance therefore shows $865M paid against a $69M budget. Matched citywide, benefits are $831.1M budget against $833.7M paid, a near exact match.
- **Aviation paid $1.32B against $824M** of budget. The Aviation budget holds $589M as Reserve Balance (grant placeholders) and the O'Hare 21 construction management teams (Turner Paschen $122.3M, AECOM Hunt/Clayco $122.0M, Clark-W.E. O'Neil $105.2M) are typed `PRO SERV-AVIATION` and reclassified to construction by the description rule.
- **Planning and Development paid $560M against $126M** because TIF and housing deals (RDAs, CTA, CPS and Park District IGAs, loans) are paid on `COMPTROLLER-OTHER` contracts. Those payments are described as TIF and RDA deals in the contract text. The budget ordinance does not show them as vendor lines.
- **Police explains only $23M of $149M** because $82.6M of its vendor-payable budget is judgments and settlements, which are *paid* by Finance (voucher prefix 27).
- **Technology and Innovation paid $183M against $50M** while the IT budget sits in other departments (Aviation $91.3M, Public Safety Administration $36.8M, Finance $33.0M, Finance General $93.0M). Citywide, IT is $312.3M budget against $187.2M paid.

### By account family, citywide

| Family | 2026 budget | 2025 paid | Explained | Explained and under $1M |
|---|---:|---:|---:|---:|
| Professional & technical | $1,075.0M | $1,032.7M | $1,032.7M | $82.1M |
| Construction | $1,030.7M | $1,297.3M | $1,030.7M | $19.1M |
| Employee health and insurance | $831.1M | $833.7M | $831.1M | $4.0M |
| Delegate agencies and programs | $593.4M | $621.2M | $593.4M | $251.3M |
| IT | $312.3M | $187.2M | $187.2M | $8.8M |
| Facility and equipment repair | $306.5M | $274.3M | $274.3M | $33.1M |
| Other vendor-payable | $236.1M | $624.3M | $236.1M | $74.2M |
| Housing and development loans | $191.6M | $510.3M | $191.6M | $13.7M |
| Materials | $180.7M | $225.6M | $180.7M | $17.7M |
| Utilities | $160.8M | $174.4M | $160.8M | $6.4M |
| Judgments and outside counsel | $154.3M | $336.9M | $154.3M | $14.4M |
| Rental | $133.7M | $53.8M | $53.8M | $3.0M |
| Waste | $66.2M | $93.3M | $66.2M | $0.9M |
| Fuel | $40.7M | $35.9M | $35.9M | $1.3M |
| Telecom | $36.3M | $16.8M | $16.8M | $0.0M |
| Equipment and vehicles | $20.0M | $105.1M | $20.0M | $0.5M |
| **Total** | **$5,369.2M** | | **$5,065.4M** | **$530.4M** |

### The big accounts you asked about (department-by-department matching)

| Account | 2026 budget | Explained | Explained and under $1M |
|---|---:|---:|---:|
| 0140 Professional & technical services | $1,055.0M | $698.8M (66%) | $51.6M |
| 0540 Construction | $971.5M | $723.7M (74%) | $16.7M |
| 0135 Delegate agencies | $360.5M | $340.4M (94%) | $146.8M |
| 0138 IT maintenance | $221.8M | $22.9M (10%) | $0.9M |
| 0162 Repair/maintenance of equipment | $104.7M | $75.5M (72%) | $9.9M |
| 0331 Electricity | $90.1M | $89.9M (100%) | $3.8M |
| 0157 Rental of equipment and services | $89.0M | $8.1M (9%) | $0.4M |
| 0340 Material and supplies | $81.3M | $60.4M (74%) | $5.9M |

The low IT and rental rows are the department-name problem above (IT is budgeted in 35 departments but mostly paid centrally) plus the fact that many rental and software vendors are paid on direct vouchers or `COMPTROLLER-OTHER` contracts with no usable type. Construction at 74% reflects that $680M of the budget is a CDOT grant placeholder and $290M sits in Water Management, against $505M and $223M actually paid.

## What share ends up in items under $1M

Using the $6.42B of 2025 payments that resolve to a department and a vendor family (department-resolved, non-pension, non-debt):

| Item definition | Items | Under $1M | % of items | % of dollars under $1M |
|---|---:|---:|---:|---:|
| (department, vendor) | 18,563 | 17,953 | 96.7% | 7.2% |
| (department, vendor, contract) | 20,383 | 19,638 | 96.3% | **11.2%** |
| (department, vendor, contract, quarter) | 31,281 | 30,224 | 96.6% | 19.9% |
| (department, vendor, contract, month) | 44,222 | 42,929 | 97.1% | 28.1% |
| single voucher line | 94,110 | 93,014 | 98.8% | **43.2%** |

By family at (department, vendor, contract) level the share of dollars under $1M is: delegate 42%, other vendor-payable 31%, facility 12%, materials 10%, legal 9%, professional 8%, development 7%, IT 5%, utilities 4%, construction 2%, health care 0.5%.

Single vouchers of $1M or more, by family (this is the floor of the payment data):

| Family | Paid | In single vouchers of $1M or more | Count |
|---|---:|---:|---:|
| Construction | $1,297.3M | $915.4M | 303 |
| Health care and insurance | $833.7M | $773.8M | 63 |
| Professional services | $1,032.7M | $562.8M | 260 |
| Development loans and deals | $510.3M | $405.4M | 121 |
| Other vendor-payable | $624.3M | $275.1M | 95 |
| Judgments | $336.9M | $257.5M | 33 |
| Utilities | $174.4M | $120.3M | 34 |
| Delegate agencies | $621.2M | $47.6M | 35 |
| All families | $6,422.8M | $3,648.2M | 1,096 |

**Implication for the site.** A budget line like "Professional Services, Aviation, $422M" can drill: Account > Vendor > Contract > Month > Voucher. At the voucher level it still ends in single payments of $1M to $30M (for example, one construction check). Those are real and cannot be split by public data. They should carry a "why can't I go deeper" note: "This was one check to X on contract Y for Z". Delegate agencies, small departments (City Council, Clerk, Mayor, Treasurer, Procurement, OIG all 100% under $1M or close) and Cultural Affairs, Public Health and Business Affairs get below $1M at the contract level.

## Notable findings

### Largest vendors, 2025 (named, resolved, excludes pensions and banks)

| Vendor | 2025 paid | Main department |
|---|---:|---|
| Blue Cross & Blue Shield | $610.0M | Finance (employee health plans) |
| F.H. Paschen, S.N. Nielsen & Associates | $332.7M | Fleet and Facility, CDOT, Environment |
| Board of Education of the City of Chicago | $146.9M | Planning and Development IGAs for school construction, Public Health, OBM |
| Loevy & Loevy Attorneys at Law | $134.5M | Finance General (direct vouchers, judgments and settlements) |
| Caremark Inc | $129.6M | Finance (pharmacy benefits manager) |
| Turner Paschen Aviation Partners | $122.3M | Aviation (O'Hare 21 construction management at risk) |
| AECOM Hunt / Clayco JV | $122.0M | Aviation (O'Hare 21) |
| Clark-W.E. O'Neil JV | $105.2M | Aviation |
| Constellation NewEnergy | $92.2M | Fleet and Facility (electricity) |
| Bigane Paving Company | $71.9M | CDOT, Water |
| CDW Government | $71.0M | Technology and Innovation |
| Pan-Oceanic Engineering | $67.7M | CDOT, Water |
| Sumit Construction | $62.9M | CDOT, Water |
| K.L.E.O. Community Family Life Center | $59.5M | Family and Support Services, Planning (nonprofit) |
| AOR Transit | $56.3M | Aviation (O'Hare airport transit system) |
| SDI Presence | $55.5M | Technology, Fleet, Aviation |

Concentration: of all $10.66B paid in 2025, the top 10 payee names take 37.8% and the top 100 take 76.3%. There are 17,685 distinct payee names. Payments carries no vendor id, so name matching is the only join. Contracts has `vendor_id` (14,152 vendors), so **a contract-number join (not a name match) should be the vendor key** for the site.

### Sole source and emergency

- **$81.6M** was paid in 2025 on contracts flagged `SOLE SOURCE`, led by Securitas security services at Fleet and Facility ($15.5M), Axon (Tasers) for Police ($13.2M), two Bell helicopters for Public Safety Administration ($11.9M), AT&T for the 911 system ($8.3M) and Siemens at Aviation ($5.4M). By department: Public Safety Administration $21.4M, Fleet and Facility $17.8M, Police $13.6M, Aviation $7.7M, Technology $6.1M.
- Emergency-flagged contracts show **$0** in 2025 payments (485 emergency contracts exist, mostly from 2011 and 2020).
- **The flag is incomplete.** `procurement_type` is blank for **$2.21B (38.8%) of 2025 contract dollars**, mostly `COMPTROLLER-OTHER` ($1.74B) and delegate agency ($415M), which are ordinance or grant based and are not normally bid. So $81.6M is a floor for non-competitive spending, not a total. Competitive methods on the rest: Bid $1,545M, RFP $1,041M, RFQ $585M, Master Agreement $121M, Contract Assignment $135M.

### Consulting

Using the contract type label (`PRO SERV CONSULTING` over and under $250K, plus business consulting) and "consult" in the description: **$631M** in 2025 (contract type alone: $521M). Caution: **the type label is a procurement category and not literal advice.** The largest "consulting" payees are CDW Government ($70.1M, an IT equipment reseller), AOR Transit ($56.3M, running the O'Hare airport train), SDI Presence ($43.5M, IT infrastructure), Genuine Parts ($39.0M, vehicle parts supply), CNECT ($34.1M, program management for capital projects), Transwestern ($28.7M) and CBRE ($27.1M, property management), Kyndryl ($25.4M, violation and noticing system) and Worldpay ($18.7M). True advisory work is smaller: Ricondo & Associates $17.4M and Landrum & Brown $11.7M (airport planning), NTT Data $10.0M. By department: Technology $147.0M, Fleet and Facility $124.9M, Aviation $108.8M, Finance $83.8M, CDOT $65.3M.

### Delegate agencies and DFSS

- $621.2M paid in 2025, of which DFSS $466.6M, Public Health $114.3M, Housing $15.5M, Business Affairs $8.5M, MOPD $7.2M, Planning $4.1M, Cultural Affairs $2.4M.
- Top agencies: K.L.E.O. Community Family Life Center $41.5M, All Chicago Making Homelessness History $30.4M, After School Matters $25.7M, Open Kitchens $24.1M, Metropolitan Family Services $17.8M, Equitable Social Solutions $14.7M, SGA Youth & Family Services $12.7M, El Valor $11.6M, AIDS Foundation of Chicago $11.4M.
- Top DFSS program codes (decoded from the description): ECBG-CS-CEL $86.4M, HHS-CS-CEL $58.2M, CORP-YS-SYEP (Summer Youth Employment) $28.2M, CORP-HL-EFSP $27.6M, CORP-HL-SPC $25.2M, IDOA-SS-HDM (home delivered meals) $19.5M, CORP-HL-RRP $18.9M, CORP-YS-OST (out of school time) $17.4M. These codes give a free program layer between department and agency.
- **Migrant response** (`gxzc-43gg`): $639.6M to 86 vendors from 2022 to 2025. Favorite Healthcare Staffing $400.4M, Equitable Social Solutions $129.0M, Open Kitchens $25.0M, Seventy-Seven Communities Meal Services $21.2M.

### TIF and grants

- TIF annual reports list **561 vendors paid over $10K in 2025 totaling $559.4M** and project payments of $386.9M. Of the 561, 82% are under $1M but they hold only 14.5% of dollars. The 762 RDA and IGA deals total $6.45B approved (183 under $1M).
- The **Mid-Year Grants report** (509 projects, $4.08B budget at 2026-05-31) is the best source to break up the $1.91B Reserve Balance (909A). CDOT's $834.7M reserve compares with 196 projects worth $1,003.9M (74 under $1M), DFSS 68 projects, Public Health 83, Fire 17, Police 29. Aviation ($589.5M reserve) and Environment ($44.1M) have no project rows. The largest rows are ARPA Local Fiscal Recovery ($1.17B at OBM, $130M Fire, $110M DFSS), mostly not part of the ordinance reserve. Only 1.6% of the grants-report dollars sit in projects under $1M, so grants will mostly stay above $1M until broken down by the Capital Improvement Program.

### Data quality notes

- **1,056 exact duplicate rows ($371.0M)** exist in the 2025 Payments file (rows identical in voucher, amount, date, contract and vendor), including three identical pension fund checks. Some may be two legitimate lines on one voucher. We did **not** remove them. They are flagged here so the site can show the count. Confirm with the Comptroller if they should be netted.
- 200 negative payments (voids) total -$0.47M.
- Vendor names in Contracts sometimes end with `|CLEANED-UP` (8,900 rows). The build strips it.
- Many payee names are fragmented (for example "DAYSPRING PROFESSIONAL JANITOR" and "DAYSPRING PROFESSIONAL JANITOR AEROFUND FINANCIAL"). Naive suffix cleanup only removes 69 names of 17,685, so use contract vendor ids.
- Contract `department` is the *latest* revision's department. 3,738 of 89,045 contracts have none.
- The Contracts dataset has 45 duplicate (contract, revision) pairs that were summed as listed.

## Recommended next steps

1. **Use the contract number as the vendor spine.** Join Payments to Contracts, take vendor id and department from the contract, and use direct voucher prefix only for `DV`. Done in `contracts_build.py`.
2. **Show actuals next to the budget, not mixed into it.** The tree should say "2025 actual payments to vendors in this area" next to each 2026 line, with the family match shown above. For same-year comparison, rerun on 2026 year to date: `raw/contracts/payments_all.csv` already holds January to September 2026 (85,720 rows, $8.06B).
3. **Build a department-by-family reconciliation** (shipped in `data/city_vendors_coverage_2026.json`) so the UI can say "Finance General health care is paid through the Department of Finance".
4. **Add month and voucher levels** under each vendor contract to get 28% and 43% of paid dollars under $1M, and flag the 1,096 vouchers of $1M or more as "single payment, cannot split further".
5. **Pull TIF and the Capital Improvement Program** for the CDOT, Water and Aviation reserves, since those are the only way to get construction under $1M.
6. **Ask for** the Comptroller's confirmation on the duplicate payment rows and whether the City will publish a vendor id on Payments.

## Files

| File | What |
|---|---|
| `scripts/contracts_fetch.py` | Downloads all datasets above into `raw/contracts/` (gitignored). Retries on Socrata 503s. |
| `scripts/contracts_build.py` | Department normalization, voucher prefix resolution, account family mapping, coverage, under-$1M shares, findings. Runs in about 25 seconds. |
| `scripts/contracts_grants_check.py` | Cross check of Reserve Balance vs the Mid-Year Grants report. |
| `data/city_vendors_items_2025.json` | 20,384 items: department, family, vendor, contract number, paid 2025, payment count, description, contract type, procurement type. This is the layer to attach under the budget tree. |
| `data/city_vendors_coverage_2026.json` | Department by family budget vs paid, explained and under-$1M numbers, department aliases, budget by kind. |
| `data/city_vendors_findings_2025.json` | Top vendors, sole source, consulting, delegates, DFSS programs, TIF, grants, overtime, routing totals. |
