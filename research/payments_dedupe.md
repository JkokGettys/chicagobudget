# Duplicate payment rows in City Payments (s4vu-giwb), and the 2026 YTD vendor view

All numbers are computed by `scripts/payments_dedupe.py` (report: `data/payments_dedupe_report.json`) and `scripts/contracts_build.py`. 2026 YTD means checks dated Jan 1 to **09/28/2026**, partial year, never annualized.

## 1. Rule chosen

**Same payment line = same voucher_number + amount + check_date + vendor_name + contract_number. Department is ignored. Keep one row (the one with a department). Never drop a row of $99,000,000 or more.**

| Rule | 2025 rows | 2025 $ | 2026 YTD rows | 2026 YTD $ |
|---|---:|---:|---:|---:|
| A. Exact full row (audit) | 1,056 | 371.0M | 819 | 433.3M |
| B. Loose key, ignoring department | 3,042 | 457.7M | 2,286 | 485.0M |
| C. A plus the $99M exemption | 1,053 | 74.0M | 815 | 37.3M |
| **D. B plus the $99M exemption (chosen)** | **3,039** | **160.7M** | **2,282** | **89.0M** |

| Payments file | Rows before | Rows after | $ before | $ after |
|---|---:|---:|---:|---:|
| 2025 (`payments_2025_dedup.csv`) | 115,810 | 112,771 | 10,663.0M | 10,502.2M |
| 2026 YTD (`payments_2026ytd_dedup.csv`) | 85,720 | 83,438 | 8,056.1M | 7,967.1M |

Negative rows (voids) removed: 8 in 2025, 5 in 2026. After the rule, no repeated key remains below $99M in either file.

## 2. Why this rule

**Two different kinds of repeat.** Of the 3,042 extra rows in 2025, 1,056 are copies identical in every column and 1,986 are the same payment listed twice, once with the department filled and once blank (every one of the 1,986 groups is exactly one filled plus one blank). The audit's exact test missed the second kind because the blank department made the rows differ.

**Evidence the repeats are duplicates, not multi-line vouchers.** Test: contracts that started on or after 2022-06-01 (so every payment is in the voucher-level era), have an award, and have no rolled-up older rows (2,345 contracts). Total paid since 2022 should not exceed the total award across all revisions.

| Group of contracts | Count | Share paid above total award |
|---|---:|---:|
| No repeated rows (baseline) | 2,248 | 0.6% |
| Have repeated rows, raw | 97 | 29.9% |
| Same, after rule A (exact only) | 97 | 22.7% |
| Same, after rule B or D | 97 | **0.0%** |

Only the loose key brings repeats back to the baseline, so the department-blank copies are real duplicates. TranSystems 47314 is the clearest case: award $79.4M over all revisions, raw payments all years $107.0M, after the rule $70.0M.

**Why the $99M exemption.** Rule B would also drop 3 of the 7 $99.0M lines to the Municipal Employees' Annuity and Benefit Fund (MEABF) in 2025 (-$297.0M) and 4 of the 6 in 2026 (-$396.0M). These sit in central Finance vouchers (PV27) that hold two or three identical $99,000,000 lines, which looks like one large wire split into capped checks. Dedup without the exemption would make MEABF 2025 PV27 payments $648.5M. Raw is $945.5M, the 2025 ACFR reports the City contributing $1,124.0M to MEABF, and the 2026 ordinance appropriates $965.0M statutory plus $161.2M advance. Raw is the figure that fits. This is a judgment from totals, not a City statement. Dropping the exemption is one constant (`CHECK_CAP`) in the script.

**Documentation checked.** The dataset description (data.cityofchicago.org/d/s4vu-giwb) and the City's Vendor, Contract and Payment Search say only that the data is "extracted from" that app and that DV means direct voucher. Neither says whether identical rows can be legitimate, so the evidence above is empirical. Open question for the Department of Finance: does one voucher line ever appear twice on purpose?

**What stays.** Same voucher with several different lines, same vendor paid the same amount on different dates or on different vouchers, and the $99M lines. Remaining risk: a genuinely repeated identical line on one voucher (for example two identical invoices) would be removed.  The award test cannot detect that case, because a repeated invoice would also leave payments within the award. Treat the removed dollars as the upper end for contracts with large awards.

## 3. Biggest effects (rule D)

| Contract | Vendor | 2025 raw | 2025 after | 2026 YTD raw | 2026 YTD after |
|---|---|---:|---:|---:|---:|
| 47314 | TranSystems | 37.2M | 12.1M | 18.0M | 6.1M |
| 296396 | K.L.E.O. Community Family Life Center | 27.6M | 13.8M | | |
| 33959 | CBRE | 25.2M | 12.6M | 11.4M | 5.7M |
| 232050 | K.L.E.O. Community Family Life Center | 18.0M | 9.0M | | |
| 91165 | Ozinga Ready Mix | 17.0M | 8.5M | 13.4M | 6.7M |
| 117688 | Verizon Wireless | 12.9M | 6.5M | 18.7M | 9.3M |
| 332942 | Sacred Apartments Owner | | | 13.8M | 7.5M |
| 355798 | CLIHTF | | | 11.0M | 5.5M |

Top 20 vendors and contracts per year, with before and after, are in `data/payments_dedupe_report.json`.

## 4. How the vendor pieces changed

| Measure | Before (raw 2025) | 2025 deduped | 2026 YTD deduped |
|---|---:|---:|---:|
| TranSystems piece (contract 47314) | $37.2M | $12.1M | $6.1M (below $10M, no longer a piece) |
| Named vendor pieces of $10M or more (City leaves) | 75, $1,571.0M | 73, $1,528.5M | 56, $1,226.3M |
| City leaves still over $10M, team-split basis | 175, $5,194.6M | 173, $5,158.9M | 159, $5,103.5M |
| Remaining over-$10M pieces (all budgets) | 232, $7,336.3M | 230, $7,300.6M | 216, $7,245.3M |
| Vendor-item payments resolved to a department | $6,422.7M | $6,262.1M | $5,102.5M |
| Budget explained by named contracts, dept by dept (of $5,369.2M) | $3,080.7M | $3,067.6M | $2,729.5M |
| Same, citywide by family | $5,065.4M | $4,987.0M | $4,212.8M |
| Vendor-contract items over $10M with a voucher check (`leaves_contracts`) | 122 | | 99 |
| Vouchers still $10M or more | 52 | | 51 |

Other pieces that dropped out of 2025 after dedupe: K.L.E.O. contract 232050 ($10.9M) and 1237 N. California contract 299798 ($7.2M, was already below the line). The 2026 YTD view is a partial year of nine months, so counts and coverage fall mostly because fewer months are paid, not because of dedupe. Use the same-dates table below to compare.

## 5. 2026 YTD against 2025, same dates (Jan 1 to 9/28), deduped

| Measure | 2025 same dates | 2026 YTD | Change |
|---|---:|---:|---:|
| All payments, deduped | 8,003.7M | 7,967.1M | -0.5% |
| Vendor items (department resolved, excl. pension, bank, tax, pass-through) | 4,690.3M | 5,102.5M | +8.8% |
| Distinct vendors in items | 14,855 | 14,137 | -4.8% |
| Top 25 vendors, ranked by 2026 YTD | 1,797.2M | 2,184.4M | +21.5% |

`PLAN.md` quotes $7.57B vs $7.77B (-2.5%) for the same months. I did not reproduce that basis. The figures here come straight from the two deduped files and include the $99M lines.

Top 25 vendors by 2026 YTD ($M, vendor items, names as in the data; "from" means a 2025 base under $5M):

| # | Vendor | 2025 Jan 1 to 9/28 | 2026 YTD to 9/28 | Change |
|---:|---|---:|---:|---:|
| 1 | BLUE CROSS & BLUE SHIELD | 530.3 | 400.8 | -24% |
| 2 | F.H. PASCHEN S.N. NIELSEN & ASSOCIATES, LLC | 234.3 | 329.7 | +41% |
| 3 | AECOM HUNT / CLAYCO, A JOINT VENTURE | 55.7 | 272.7 | +390% |
| 4 | LOEVY & LOEVY ATTORNEYS AT LAW | 95.4 | 132.4 | +39% |
| 5 | CAREMARK INC | 98.6 | 97.2 | -1% |
| 6 | CLARK-W.E. ONEIL JV | 71.8 | 93.4 | +30% |
| 7 | PAN-OCEANIC ENGINEERING CO INC | 43.4 | 88.1 | +103% |
| 8 | CHICAGO TRANSITY AUTHORITY. | 44.2 | 75.9 | +72% |
| 9 | CDW GOVERNMENT, LLC. | 64.4 | 70.2 | +9% |
| 10 | CONSTELLATION NEWENERGY INC | 66.7 | 55.2 | -17% |
| 11 | TURNER PASCHEN AVIATION PARTNERS | 104.4 | 51.1 | -51% |
| 12 | AOR TRANSIT | 37.2 | 47.3 | +27% |
| 13 | SUMIT CONSTRUCTION CO., INC. | 43.3 | 43.7 | +1% |
| 14 | SDI PRESENCE LLC | 43.4 | 42.8 | -1% |
| 15 | GRANITE CONSTRUCTION COMPANY. | 21.8 | 41.3 | +90% |
| 16 | GENUINE PARTS COMPANY | 21.4 | 40.8 | +90% |
| 17 | BOSCHUNG AMERICA, LLC | 0.6 | 39.2 | from 0.6 |
| 18 | RELIABLE CONTRACTING & EQUIPMENT COMPANY | 35.1 | 38.7 | +10% |
| 19 | ALLIED WASTE TRANSPORTATION INC | 30.5 | 35.4 | +16% |
| 20 | AMERICAN AIRLINES 01 | 11.6 | 34.5 | +196% |
| 21 | SALVI, SCHOSTOK & PRITCHARD, P.C. | 1.0 | 32.0 | from 1.0 |
| 22 | AECOM-DBS | 27.4 | 31.4 | +15% |
| 23 | USI INSURANCE SERVICES LLC. | 30.8 | 31.4 | +2% |
| 24 | BIGANE PAVING COMPANY | 51.7 | 29.8 | -42% |
| 25 | CHICAGO AIRLINES TERMINAL CONSORTIUM | 32.3 | 29.5 | -9% |

Big movers are real payment timing or new work, not dedupe: AECOM Hunt / Clayco (+$217M), F.H. Paschen (+$95M), Boschung America (+$39M), Salvi, Schostok & Pritchard (+$31M), against Blue Cross (-$130M) and Turner Paschen (-$53M). I have not checked the causes.

## 6. Files and how to rerun

| What | File |
|---|---|
| Dedupe | `python3 scripts/payments_dedupe.py` writes `raw/contracts/payments_2025_dedup.csv`, `payments_2026ytd_dedup.csv`, `data/payments_dedupe_report.json` (`raw/` is gitignored, so rerun to recreate) |
| Vendor build, default | `python3 scripts/contracts_build.py` (basis `2026ytd`, deduped): `data/city_vendors_items_2026ytd.json`, `city_vendors_findings_2026ytd.json`, `city_vendors_coverage_2026.json` |
| 2025 comparison | `--basis 2025`: `city_vendors_items_2025.json`, `city_vendors_findings_2025.json`, `city_vendors_coverage_2026_on_2025pay.json` |
| 2025 same dates | `--basis 2025samedates`: `city_vendors_items_2025_samedates.json` and matching findings and coverage files |
| Old behaviour | add `--raw` (reproduces the pre-dedupe items and findings exactly, checked) |
| Leaves | `python3 scripts/leaves_contracts.py` (default 2026ytd, `--basis 2025` writes `leaves_contracts_2025basis.json`), then `python3 scripts/leaves_inventory.py` (`VENDOR_BASIS=2025` for the 2025 view) |

Schema note: `city_vendors_items_2026ytd.json` has the same record layout as the 2025 file. The dollar field keeps the name `paid_2025` in coverage and findings JSON (to avoid breaking readers) and holds the basis's dollars, so read `meta.label` ("paid Jan 1 to 09/28/2026, partial year") before labelling anything. The items file names the field `paid_2026ytd` in `record_fields`. Coverage fractions on the 2026 basis are understated against a full-year budget because nothing is annualized.
