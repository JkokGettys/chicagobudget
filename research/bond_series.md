# Bond series: 2026 principal and interest by series

Outputs: `data/city_bond_series_2026.json`. Reproduce with `python3 scripts/bonds_fetch.py get` (plus the extra fetches listed in `bonds_parse.py` specs, run as `get <issuer> <name fragment>`) and `python3 scripts/bonds_parse.py`. Every parsed row is checked: the printed columns must add to the printed total within $5, or the script stops. `python3 scripts/bonds_fetch.py list <issuer>` prints every document on an issuer page, and `manifest` writes `raw/bonds/manifest.json` mapping local names to CDN URLs. Page numbers are PDF page indexes.

## 1. What was found

BondLink documents download with plain curl from `https://bondlink-cdn.com/<client>/<file>`. The `Debt Service Schedules` document type (id 2404) is empty on the O'Hare page: its category list shows only Agreements, Basic Financial Statements, Loan Agreement, Official Statements and Indenture. So per-series numbers come from each official statement (OS).

Every recent O'Hare and Midway OS prints a table of the new series in its own column next to one combined column for everything else outstanding. Reading one OS per series therefore gives a series column, and 36 O'Hare series were read this way. Water and Sewer OSs do the same for the newest series only.

## 2. Window convention

O'Hare, Midway and GO tables are labelled "Bond Year Ending January 1". The row 2027 holds principal and interest paid January 2 2026 through January 1 2027 (O'Hare 2026CD OS p.65 note 2, Midway 2025 OS p.60 note 3). Water and Sewer tables are fiscal (calendar) years, so the row 2026 is used. Older GO statements label the row by payment calendar year, so the row 2026 is used there (it is the same Jan 1 2027 payment: the 2021AB statement row 2026 shows $5,645,000 principal, equal to the 2027 maturity on its cover, p.2).

## 3. Reconciliation per credit

All ordinance figures are Finance General lines in `raw/city_appropriations_2026.json`.

### O'Hare Airport Fund (interest $496,066,181 + principal $303,172,911 = $799,239,092; fees $3,231,068 are separate)

| Piece | 2026 | Source |
|---|---:|---|
| Senior lien total net debt service, bond year ending Jan 1 2027 | 771,416,782 | ohare_2026CD_OS p.65 |
| CFC Series 2023 bonds (interest only) | 8,786,000 | ohare_FS2025 p.51 |
| TIFIA loan (principal 4,336,000 + interest 10,835,000) | 15,171,000 | ohare_FS2025 p.52 |
| PFC Series 2012AB | 4,000 | ohare_FS2025 p.51 |
| **Total of the pieces** | **795,377,782** | |
| Ordinance | 799,239,092 | |
| **Gap, ordinance higher** | **3,861,310 (0.5%)** | |

The $3.86M gap is not explained by any document. The senior lien table is net of capitalized interest and uses the actual bond year, while the ordinance is a cash appropriation, so a small difference is expected.

Of the $771.4M senior lien total, **$648,938,919 is split into 28 individual series** (2017D, 2018A, 2018B, 2020A-E, 2022A-D, 2024A-F, 2025A-E, 2025G, 2026A-D). With CFC, TIFIA and PFC that is **$672,899,919 in 31 series-level leaves** (28 bond series, the CFC bonds, the TIFIA loan and PFC 2012AB). The remaining **$122,477,863 is a residual** that cannot be split: the 2026CD OS prints one combined "outstanding" column, and the following series are inside it: 2010B (BAB, $328M par, p.64), and the post-refunding remainder of 2016D, 2016E, 2016F, 2016G, 2017A, 2017B, 2017C and 2018C. For those eight the series' own old statement still prints a column, but it is an upper bound only (2016F and 2017B were fully refunded by 2026CD, p.64, and 2018C was partly defeased by 2025C, FS p.50), so they are listed with status `stale` and no amount. Their printed upper bounds sum to $166,249,176.

Principal versus interest split: the table prints P+I together. Principal is read from serial maturities on each OS cover (maturing January 1 2027) and interest is total minus principal. Term bond sinking fund installments are not on the cover, so principal is a **lower bound** and interest an **upper bound** for series with term bonds (2022A, 2024A, 2024B, 2018B, 2018C, 2025A, 2025B, 2025E, 2026A show principal 0 because the first printed maturity is later than 2027; this is stated in each row's `principal_basis`). Total P+I per series is exact. Series 2022A could not be read from its cover for the same reason and is reported as 0 principal with a note. Across the 31 O'Hare leaves the principal read is $256.5M of the $672.9M (a lower bound). Treat the principal/interest split as indicative, the total as firm.

2024A and 2024B: the 2024AB statement's table (p.57) subtracts one combined capitalized interest amount for both series together. In the row for the bond year ending 2027 that amount is $23,081,315. The series columns shown are gross of that. If capitalized interest is applied to 2024A and 2024B, the true cash amount is lower by up to $23.1M, and this is not allocated between the two. This is the largest known overstatement among the O'Hare series leaves.

### Midway Airport Fund (interest $61,100,475 + principal $77,455,000 = $138,555,475; fees $6,147,941 separate)

| Piece | 2026 |
|---|---:|
| Total, bond year ending Jan 1 2027 (midway_2025AB_OS p.60) | 134,355,876 |
| of which named series 2023A, 2023B, 2023C, 2024A, 2024B, 2025A, 2025B | 125,242,814 |
| residual (2014B, 2014C, 2018A, per p.59 list) | 9,113,062 |
| FY2025 financial statement, calendar 2026 (p.82) | 127,835,000 |
| Ordinance minus OS total | 4,199,599 (ordinance higher) |

The series columns come from four different OSs (2025AB p.60, 2024AB p.32, 2023C p.36, 2023AB p.40) and their "outstanding" columns differ because each is a snapshot at its own date, so the series amounts and the residual are not from one snapshot. The 2025AB table shows the whole portfolio at one date and its residual (2014B, 2014C, 2018A) is $9,113,062 after subtracting the 2023 and 2024 columns taken from their own statements. That mixes snapshot dates and the residual is approximate. Variable rate bonds are assumed at 3.00% (p.60 note 5). Midway P+I is not split into principal and interest in the file. The ordinance minus OS gap of $4.2M is not explained. The calendar-2026 financial statement row ($127.8M) differs by $6.5M from the bond-year row because the window shifts by one day.

### Water Fund (bonds: interest $92,769,138 + principal $86,685,000 = $179,454,138; loans: $53,802,304; together $233,256,442)

| Piece | 2026 |
|---|---:|
| Total debt service requirement, fiscal 2026 (water_2026ABC_OS p.36) | 233,775,541 |
| Ordinance bonds plus loans | 233,256,442 |
| **Difference** | **519,099 (0.2%)** |

Series level: 2026A/B/C (printed together) $22,511,703; 2024A $23,553,000 (2024A OS p.25); 2023A $13,676,838; 2023B $13,926,050 (2023AB OS p.32). That is $73,667,591 in four leaves. A residual of $118,062,905 covers 2001, 2004, 2010B, 2010C, 2016A-1, 2017, 2017-2 and 2023C (the WIFIA loan), with the list taken from water_2026_supplement p.5. IEPA subordinate loans are $42,045,045 in aggregate. The ordinance splits bonds $179.5M and loans $53.8M; the OS splits second lien $191.7M and IEPA $42.0M. The two classifications differ (the WIFIA loan is a second-lien bond in the OS, and the ordinance probably books it as a loan), so only the total reconciles. Water 2026ABC debt service is net of capitalized interest and its principal is only $2,780,000 for 2026 because those bonds were sold in May 2026.

### Sewer Fund (bonds $114,067,119 + loans $44,361,561 = $158,428,680)

| Piece | 2026 |
|---|---:|
| Total debt service requirement, fiscal 2026 (wastewater_2024B_OS p.24) | 165,855,677 |
| Ordinance | 158,428,680 |
| **OS higher by** | **7,426,997 (4.7%)** |

The OS is the 2024B statement (Nov 2024). The City's 2025 financial statement (sewer_FS2025 p.44) shows $176,757K for 2026. The 2008C bonds were defeased in 2025 (FS p.44), which the OS table predates. The OS table therefore contains debt service for bonds that no longer exist, and the ordinance is lower. Series level: 2024B $7,729,250, 2024A $17,791,000 (2024A OS p.23), 2023A $13,749,390, 2023B $9,623,500 (2023AB OS p.30). That is $48,893,140 in four leaves. A residual of $59,748,907 remains (second-lien series not named in any fetched OS, including the defeased 2008C, so this residual is overstated), plus senior lien bonds $24,680,000 (OS column not named by series) and IEPA loans $32,533,630. The OSs for 2017AB, 2015, 2014, 2012 and earlier were downloaded but not parsed.

### GO Bond Redemption and Interest Series Fund ($285,429,137 interest + $132,090,000 principal = $417,519,137)

New series-level leaf: GO 2021A and 2021B, principal $5,645,000 and interest $29,585,510 (2021AB OS p.115, row 2026). The statement's remaining principal is $1,220,000 above current outstanding, so it is flagged `current_with_caveat`. The existing 12 groups in `data/debt_2026.json` per_series_2026 are unchanged.

Not usable, status `stale`, no amount in the leaf list: 2020A, 2019A, 2017A/B, 2015B and 2015C. Each statement's remaining principal exceeds what is outstanding now by $74.7M, $84.5M, $560.0M, $875.8M and $95.8M, because of the 2025 tenders and refundings. The GO 2012B and 2014B statements were downloaded but their tables are in a different layout and were not parsed. Printed 2026 upper bounds are kept in the JSON as `printed_upper_bound_*`.

**Library term notes ($125,926,011 principal and $2,200,000 interest):** no official statement or schedule exists on the BondLink pages. Not covered.

## 4. Dollars moved into series-level leaves

| Credit | Series-level $ (principal + interest) | Leaves | Still not split |
|---|---:|---:|---:|
| O'Hare | 672,899,919 | 31 | 122,477,863 residual + 3,861,310 unexplained gap |
| Midway | 125,242,814 | 7 | 9,113,062 residual |
| Water | 73,667,591 | 4 | 118,062,905 residual, 42,045,045 IEPA loans |
| Sewer | 48,893,140 | 4 | 59,748,907 residual, 24,680,000 senior, 32,533,630 IEPA loans |
| GO | 35,230,510 | 1 | rest of the $417.5M |
| **Total** | **955,933,974** | **47** | |

These are the leaves with status `current`, `current_group` or `current_with_caveat`. In the flat `series` list used by the inventory, 87 rows exist: principal and interest rows per series, and one `principal_and_interest` row for each of the 7 Midway series. Principal rows sum to $282.2M and interest rows to $548.5M (Midway's $125.2M is combined, not in either sum). Several of these are still over $10M, which is accepted by the user decision that one series is a leaf.

## 5. Gaps and cautions

1. O'Hare principal versus interest split is derived from serial maturities only and understates principal. Totals are exact.
2. O'Hare 2024A and 2024B are gross of $23.1M of capitalized interest allocated to the pair (bond year ending 2027). The true cash is lower by up to that amount.
3. Residuals are by subtraction and mix statements from different dates (Midway, Water, Sewer). They are labelled `residual_by_subtraction` and are not series leaves.
4. Sewer residual includes defeased 2008C debt service and is overstated.
5. The O'Hare residual of $122.5M still holds 2010B ($328M par BAB, no separate column in any fetched OS) and the refunded remainders of eight series. A per-series split needs EMMA or the 2026CD trustee schedules.
6. Library term notes are not covered.
7. Ordinance versus OS gaps: O'Hare $3.9M, Midway $4.2M, Water $0.5M, Sewer $7.4M. Fees ($3.2M O'Hare, $6.1M Midway) are separate ordinance lines and are not in any series.
8. Variable rate assumptions: Midway 3.00% (p.60 note 5). The O'Hare financial statement imputes variable rates at the 12/31/2025 effective rate (FS p.51). The O'Hare OS table does not state a variable rate assumption in the notes I read.
9. PFC and CFC: 2016F, 2017B, 2020C, 2020E, 2024E, 2024F and 2025D carry a PFC pledge (ohare_2026CD_OS p.190 note 19), 2026D a subordinate PFC pledge. The airport consultant shows PFCs of $111,658K applied to 2026 GARB debt service (Table B-4, p.320), so a part of the O'Hare ordinance line is paid with PFCs and not airline rates. This was not allocated by series.
10. Numbers from `raw/` are not committed (gitignored); rerun the fetch to rebuild.
