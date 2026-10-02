# Mid-Year Report contracts data (DOF): what it is and how it maps to our City tree

STATUS: final for this build (2026-10-02). Every number below was computed from the two files in `raw/midyear/` (gitignored, rerun to recreate). Nothing here is invented.

## 1. Sources

| File | Source | Rows with data | Voucher dates |
|---|---|---:|---|
| `DOF_Contracts_Data_for_2026_Mid-Year_Budget_Report.xlsx` | https://www.chicago.gov/city/en/depts/fin/supp_info/mid-year-report-contracts-data.html ("Contracts Data as published with the 2026 Mid-Year Budget Report", Dept of Finance) | 229,291 | 2025-01-02 to 2025-12-31 (12 stray rows dated 2022-09 and 2024) |
| `Mid-Year-Report_Contracts_Data.xlsx` (saved as `..._2025.xlsx`) | same page, "published with the 2025 Mid-Year Budget Report" | 421,585 | 2023-02-03 to 2025-07-28 |

The City page says the data is published because Municipal Code 2-4-055(a)(vi) requires the Mid-Year Report to list third-party contracts with the "applicable contract code or number and budget line item".

**The 2026 workbook has 356,941 data rows but 127,650 of them are completely blank** (they sit at the bottom, rows 229,292 on). The real file is 229,291 rows. The first sheet "Data" has 26 columns, and the sheet is declared 57 columns wide, with the extra 31 empty.

**Despite the title, the 2026 file is a 2025 file.** It holds invoices created in calendar 2025 (so "2022-09 to 2025-12-31" is only 1 stray row in 2022). The 2025 workbook holds 2023 to July 2025, mostly 2024.

## 2. What is in a row

One row = one accounting line ("distribution") of one invoice: vendor, contract number, department that leads the contract, contract type, budget fiscal year of the PO (BFY), then the codes **Fund, Cost Center, Appr, Account, Actv, Project, Rep Cat**, the amount ordered on the PO line, the voucher date and number, the invoice number and total, voucher type (PV or CV), and the amount of this distribution (`AP Invoice Dist Amount`).

2026 file totals (distribution amount): $5,421.8M in 229,291 rows. PV (regular vouchers) 181,011 rows, $5,087.7M. CV 48,280 rows, $334.1M. 2,527 rows are negative (-$2.4M), 2,483 of them CV.

2025 file totals: $9,611.1M in 421,585 rows. PV $8,811.2M, CV $800.0M. By voucher year: 2024 $6,098.2M, 2025 (Jan to Jul) $3,512.9M.

### What CV means (inference, not stated by the City)
Every CV row in the 2026 file has contract type DELEGATE AGENCY (48,280 of 48,280), almost all on blanket POs, and the lead departments are Family and Support Services (50) 32,504 rows, Public Health (41) 8,217, Housing (21) 1,580, Business Affairs (70) 1,572, Planning (54) 294, Disabilities (48) 169. In the payments dataset (s4vu-giwb) the same "CV" voucher prefix exists (2025: 24,963 rows, $587.8M). So CV looks like the voucher type the City uses to pay delegate agency (grant to nonprofit) contracts, and PV the type for everything else. The City does not define it on the page.

## 3. How the codes map to ordinance lines (dataset 6694-f78c)

An ordinance line is (fund, department, authority, account). The file has:

| File column | Meaning here | Evidence |
|---|---|---|
| Fund | ordinance `fund_code` | exact format match (0100, 0740, 925F... but the file also has 454 distinct funds, many not in the ordinance, for example capital and bond funds) |
| Cost Center | 3 digits department number + 4 digits | department part equals `PO Dist Dept No.` in 100% of rows. The last 4 digits are NOT the ordinance authority in general (they agree in only 58,832 of 140,604 rows where the authority is otherwise unique, 3.1% of dollars: for example the whole Aviation fund 0740 uses cost centers 4110, 4105... while the ordinance authority is 2015) |
| Appr | ordinance `appropriation_account` (4 characters) | matches an ordinance (fund, dept, account) in 171,852 rows, $3,078.1M. Matches with the `Account` column's last four digits only in 134,033 rows, so `Appr` is the one to use |
| Account | "22" plus 4 digits, a 6-character general ledger account | first two characters are always 22. It is the object being bought, not always the appropriation line, so we do not use it |

Resolution rule used (all 2026 file rows, $5,421.8M):

| Result | Rows | $ |
|---|---:|---:|
| (fund, dept, Appr) matches exactly one ordinance line ("unique") | 140,604 | $2,823.4M |
| matches several authorities and Cost Center's last 4 digits equal one of them ("cc") | 18,190 | $197.0M |
| matches several authorities and the cost center does not choose ("ambiguous") | 13,058 | $57.7M |
| no ordinance line with that fund, dept and account | 57,439 | $2,343.6M |

The "no line" $2.34B is real spending that the 2026 appropriation ordinance does not show as a line of the same fund and department. The biggest are Aviation capital and bond funds (0582, 0751, 0624, 0739, 0762, 0603), Finance General bond and pension funds, and funds such as 0F69 and 0C84 (fund names not checked). They are bond-funded or capital-fund spending that the ordinance books elsewhere. They cannot be placed on our tree.

## 4. Totals by year against the payments data (s4vu-giwb, deduplicated)

| | Payments data 2025 (deduped) | of which contract-numbered | of which direct vouchers (DV, no contract) | 2026 mid-year file (voucher dates 2025) |
|---|---:|---:|---:|---:|
| $ | $10,326.6M | $5,384.0M | $4,942.6M | $5,421.8M |

So the mid-year file covers the contract-numbered payments and none of the direct vouchers (pensions, banks, refunds, taxes...). It is not a duplicate of the payments data. Voucher-level tie: 55,184 vouchers appear in both. For 97.9% of them the total is equal to the cent. Their combined totals are $5,371.0M (mid-year) and $5,356.3M (payments). Vouchers only in the mid-year file: $50.8M. Payments vouchers with no mid-year row: $4,970.3M, of which $4,942.6M are the DV direct vouchers.

2026 YTD (checks to 09/28/2026): the mid-year files stop at 12/31/2025, so they carry no 2026 payments at all. Only 155 vouchers are shared with the 2026 YTD payments (checks dated early January for invoices created in late December). The 2026 YTD contract-numbered payments are $4,226.1M. $3,531.4M of them sit on contract numbers that appear anywhere in the two mid-year files, $713.5M on contracts that do not (new in 2026 or missing).

## 5. Caveats found

1. **Exact duplicate rows.** The 2026 file has 4,867 rows (after the first copy) that are identical in all 26 columns, $39.5M. Test: for each invoice (voucher + invoice number + contract) the distributions should add to the invoice amount. 907 invoices add to more than the invoice total (by $33.2M in all). Dropping exact copies makes 899 of those 907 tie. So most are real duplicates. We drop an exact-copy row only when dropping it brings that invoice closer to its invoice total (2,261 rows, $54.5M across both files).
2. **The two files overlap and neither contains the other.** For Jan to Jul 2025, 28,828 vouchers are in both (equal sum for all but 213). 12,498 vouchers ($848.0M, mostly delegate agency, large construction, aviation professional services) are only in the 2025 file, and 1,539 ($62.1M) only in the 2026 file. We take the union by voucher number, preferring the 2026 file.
3. Contract numbers repeat across budget fiscal years (BFY) and lines. We use the BFY 2025 rows of a contract for the 2026 line code, because that is the closest to 2026.
4. 2026 payments on contracts are not guaranteed to be coded to the same line as in 2025. Backtests (BFY 2025 contracts that sit on exactly one mapped line in Jan to Jun 2025 stay on it in Jul to Dec: 95.5% of dollars, 92% of contracts. BFY 2024 to BFY 2025: 90.1% of dollars, 89% of contracts).
5. Existing rule-based placements (`data/splits/city/paid_to_date.json`) disagree with the mid-year coding for some contracts. Final counts are in section 6 (276 agree, 49 do not). They were left as they are.
6. Vendor names: individuals must go through `build/payee.py is_business()`. With `has_contract=True` (every row here has a contract) 1,120 of 5,516 vendor numbers are hidden. We use the same decision the tree uses for payees found in the payments data (a payee with a City contract anywhere is a business) and otherwise pass the contract flag.

## 6. Contract to budget line map and what was placed

Script: `python3 scripts/midyear_build.py` (needs `build/out/city_tree.json` from one earlier build). It writes `data/midyear_contract_line_map.csv` (18,424 contracts with 2025 invoices on a BFY 2025 purchase order: class, top line, share, lines; no vendor names), `data/midyear_report.json`, and two split files in `data/splits/city/`.

**Rules (guardrails).**
1. A row maps to a 2026 ordinance line only if its Fund + department + Appr exist in the 2026 ordinance (6694-f78c). If more than one authority has that triple, the last 4 digits of Cost Center must pick one, else the row is unmapped.
2. Only the contract's invoices created in 2025 on a BFY 2025 purchase order are used.
3. **Single-line threshold: 95% or more of those 2025 dollars on one mapped line.** 15,582 of 18,424 contracts qualify. Others: 863 "multi" (95%+ mapped but spread over several lines), 193 low coverage, 1,786 not coded to any 2026 line (their funds are bond or capital funds, or not in the ordinance).
4. The line must still be an unsplit leaf, and the contract must not already be placed by `paid_to_date.json`.
5. Every box note says: "Matched to this line using how the City coded this contract's 2025 invoices." The line note also says the 2026 invoices are not in the file, so a few may be coded differently.
6. Payments above the line keep the negative "Already spent more than the budget" box, with a note. If payments on a line are more than 2x the line, nothing is placed (2 lines were dropped this way: Fleet 0740-2140-0176, $8.18M of payments on a $3.80M line, and Fleet 0300-2131-0140, $0.62M on a $0.04M line).

**Reliability of using 2025 coding for 2026 payments (backtests).** Contracts on one line in Jan to Jun 2025 stayed on it in Jul to Dec 2025 for 95.5% of dollars (92% of contracts). From BFY 2024 coding to BFY 2025 coding, 90.1% of dollars (89% of contracts). Applying a 2025 line to 2026 payments is therefore a good guess, not a fact. Expect roughly 5 to 10% of the placed dollars to be on another line.

**Where the 2026 YTD contract dollars went** (`data/city_vendors_items_2026ytd.json`, deduplicated, through 09/28/2026; total $4,900.2M, of which with a contract number $4,201.1M and direct vouchers without a contract $699.1M):

| Result | Items | 2026 YTD $ |
|---|---:|---:|
| **Placed in new boxes** (single line, `paid_to_date_midyear.json`, 102 lines, 381 contracts) | 382 | $230.1M |
| Single line, but already placed by the rule-based file | 327 | $220.6M |
| Single line, but that line was already split by another file | 58 | $62.0M |
| Single line, but payments above 2x the line (not placed) | 2 | $8.8M |
| Spread over several lines (side info estimate only) | 194 | $520.3M |
| Under 95% of dollars on any one line, or not coded to a 2026 line | 618 | $1,906.5M |
| Contract not in either file with 2025 invoices (new in 2026, or older) | 1,840 | $1,252.8M |
| Direct vouchers, no contract number (not in the mid-year files at all) | | $699.1M |

So **$230.1M of $4,900.2M (4.7%) of 2026 YTD vendor dollars was newly placed on a budget line**, on top of the $594.0M the rule-based file had placed.

**Disagreement with the rule-based placements.** Of the contracts in `paid_to_date.json` that the mid-year data calls single-line, 276 ($138.1M) agree with the rule-based line and 49 ($82.5M) do not (for example O'Hare contracts 25743 and 27075 are coded to Rental and Facility maintenance, not Professional services; the Streets waste contract 151329 is coded 0140). 520 have no single-line mid-year coding. We did not move the 49, because the rule-based file uses contract text and the mid-year file uses 2025 coding. Follow-up: review those 49 (listed by joining the CSV to `paid_to_date.json`).

**Side info "In 2025 this line paid these companies"** (kind `paid_2025_vendors`): 1,127 vendor-type lines that have no boxes from either file. It lists the top 10 payees by 2025 invoice dollars, the total, and the number of payees. These are invoice amounts for invoices created in 2025 (union of both files, exact copies removed), not checks, and not 2026 money. Individuals are pooled into one row "Individual (name hidden)" (274 lines have one).

**Estimate side info** (kind `estimate_2026_multi_line_contracts`, basis proxy): 428 lines. For contracts the City spread over several lines in 2025, the 2026 YTD payments divided by the contract's 2025 shares. Labelled ESTIMATE, not added into any box.

**Privacy.** Every vendor name goes through `build/payee.py is_business()`. Names of payees that appear in the payments data use the same decision the tree uses (a payee with a City contract anywhere is a business). Names that appear only in the mid-year files are tested with has_contract set only if the same vendor key has a contract in the 2026 payments, otherwise False (more cautious). The script also fails if any hidden or employee name appears in its output, and the tree build keeps its own leak scan.

## 7. Results (build of 2026-10-02, after `bash build/build_all.sh`)

All three totals still match to the cent (City $16,842,553,003.00, CPS $10,253,327,463.68, Parks $637,580,350.00), 0 bad sums, 0 orphans, no leaks.

| City (`treeaudit2_coverage.py` and the snapshot database) | Before | After |
|---|---:|---:|
| Leaves | 11,423 | 11,803 |
| Share of City dollars in leaves of $10M or more (build rule, the audit's headline) | 45.0% | **44.4%** (-0.6 pt) |
| Dollars in those leaves (count x rate boxes under $1M excluded) | $8,108.6M | $7,988.6M (-$120.0M) |
| paid_to_date leaves, total (absolute) | $930.3M | $1,160.4M (+$230.1M) |
| paid_to_date leaves of $10M or more | $574M | $649M |

**Dollars moved onto named vendor boxes: $230.1M**, on 102 budget lines (the lines total $794.8M, of which $524.1M had been in leaves of $10M or more before). That is exactly the 2026 YTD payments placed (section 6): the direct vendor, vendor-group and individual boxes under those lines add to $230,055,800.08. Only $120.0M left the $10M+ dead ends: many named vendors are themselves over $10M, and the "Budgeted but not spent yet" remainder usually stays one large box. The CPS and Parks figures did not change (CPS 27.4% to 27.3% only from another agent's concurrent CPS utilities change).

## 8. Caveats to remember

- The 2026 contracts file has no 2026 invoices. 2026 payments are matched by contract number to how those contracts were coded in 2025.
- Contracts first paid in 2026 (1,840 items, $1,252.8M, including AECOM Hunt / Clayco, Boschung America, and others) cannot be placed from this data.
- A line's remainder "Budgeted but not spent yet" is still the biggest box on most lines. Payments are Jan 1 to 09/28/2026 only.
- 4 lines show a negative "Already spent more than the budget" box totalling -$4.5M, mostly Finance General professional services (-$4.44M).
- The file's own definition of CV, and whether the file has duplicates on purpose, are not stated by the City (open question for the Department of Finance).
