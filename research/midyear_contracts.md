# Mid-Year Report contracts data (DOF): what it is and how it maps to our City tree

STATUS: DRAFT, written mid-work on 2026-10-02. Sections marked TODO are not finished. Every number below was computed from the two files in `raw/midyear/` (gitignored, rerun to recreate). Nothing here is invented.

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

The "no line" $2.34B is real spending that the 2026 appropriation ordinance does not show as a line of the same fund and department. The biggest are Aviation capital and bond funds (0582, 0751, 0624, 0739, 0762, 0603), Finance General bond and pension funds, and funds such as 0F69 and 0C84 (Capital Projects, per our fund list: TODO confirm names). They are bond-funded or capital-fund spending that the ordinance books elsewhere. They cannot be placed on our tree.

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
5. Existing rule-based placements (`data/splits/city/paid_to_date.json`, 847 contract items, $594.0M) disagree with the mid-year codes for about 77 of the contracts we can check (examples: O'Hare contracts 25743 and 27075 are coded 0157 Rental and 0161 Facility maintenance, not 0140 Professional services; Streets waste contract 151329 is coded 0140 not 0185). 275 agree and 9 agree in multi-line cases. TODO: decide whether to correct them or only add.
6. Vendor names: individuals must go through `build/payee.py is_business()`. With `has_contract=True` (every row here has a contract) 1,120 of 5,516 vendor numbers are hidden. We use the same decision the tree uses for payees found in the payments data (a payee with a City contract anywhere is a business) and otherwise pass the contract flag.

## 6. Contract to budget line map (TODO: finish)

Contracts with 2026 YTD payments and a contract number: 3,417 contracts, $4,201.1M (`data/city_vendors_items_2026ytd.json`). Classes using BFY 2025 mid-year rows (draft counts):

| Class | Contracts | 2026 YTD paid |
|---|---:|---:|
| Fully coded (99%+), exactly one ordinance line | 735 | $406.5M |
| Fully coded, several lines (shares from 2025) | 207 | $495.6M |
| Less than 99% of dollars land on an ordinance line | 636 | $2,046.2M |
| No BFY 2025 rows in the files | 448 | $539.3M |

Plan: single-line contracts go onto that line as paid-to-date boxes (file `data/splits/city/paid_to_date_midyear.json`, applied after `paid_to_date.json`, skipping contracts already placed and lines already split). Multi-line contracts: 2025 shares as side info only. Lines with no 2026 match: side info "In 2025 this line paid these companies".

## 7. Results (TODO)

Before/after coverage numbers go here after the rebuild. Baseline (2026-10-02 build before this work): City dollars in boxes of $10M or more = 45.0% of $18,003M.
