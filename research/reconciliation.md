# Reconciling $18.67B (ordinance) to the official budget total

Author: gap-hunter agent, 2026-09-30. Everything here is reproducible: `python3 scripts/gap_fetch.py && python3 scripts/gap_reconcile.py && python3 scripts/gap_midyear.py`. Each script asserts the numbers quoted below and fails loudly if they change. Outputs: `data/gap_reconciliation.json`, `data/gap_midyear.json`. Raw files in `raw/gap/` (gitignored).

## Short answer

1. **The "$16.6B official" figure is not the ordinance's figure.** $16,554,571,089 is the *Mayor's Budget Recommendations* (Oct 2025) net total. The ordinance City Council actually **passed on 2025-12-20** prints **$16,842,553,003** as its own "Net Total - All Functions" (ordinance p. 544, Summary G). Our $18,668,568,460 gross is the passed ordinance, so the matching official figure is **$16.84B**, not $16.6B. Gross rose $317.8M between the two books (18,350,767,715 to 18,668,568,460), and the deduction rose only $21.0M.
2. **The gap between our rule and the printed deduction is $304,869,006, not $0.28B.** The ordinance removes $1,700,089,446 (transfers) plus $125,926,011 (debt proceeds) = $1,826,015,457. Our rule removes $1,521,146,451.
3. Of that $304.9M: **$152.4M** is named lines I can reproduce to the dollar (Finance General "Transfer" lines $7.8M, Appendix A/B department-side reimbursements $18.7M, and the Library term-note "proceeds of debt" $125.9M), **$35.5M** is matching grant funds that the ordinance text says are inside the deduction, and **$117.0M is unexplained**. OBM prints that $117.0M inside the single "Deduct Transfers between Funds" number, and I could not build it from any account in the data. I would rather say that than invent a rule.

## 1. Which total is which

| Book | Gross | Deduct transfers | Deduct debt proceeds | Net |
|---|---:|---:|---:|---:|
| Budget Recommendations (rec book p. 603; Overview pp. 32 and 34, "$16.6B") | 18,350,767,715 | 1,679,051,626 | 117,145,000 | **16,554,571,089** |
| **Passed ordinance** (p. 544, Summary G) | **18,668,568,460** | **1,700,089,446** | **125,926,011** | **16,842,553,003** |

Both gross figures are reproduced to the dollar from the open datasets (`6694-f78c` ordinance; `axxr-vais` recommendations, not previously pulled). The "$16.6B" and "$1.80B" quoted in `PLAN.md` and `research/finance_general.md` come from the Overview, which describes the *proposed* budget. Note the $1.80B itself is the sum of transfers ($1,679.1M) and debt proceeds ($117.1M) in that book (Overview p. 34: $1,796.2M). It is not "internal transfers" alone.

**Recommendation:** label the site total "$16.84B (as passed)" and footnote that the Mayor's proposal said $16.6B. Do not force our number to $16.6B. Our $18.67B gross is the right base.

## 2. What the printed deduction is made of

Printed "Deduct Transfers between Funds" is a single number. The books give three visible pieces:

**(a) Finance General "Interfund Transfers and Reimbursements"** (Overview p. 182, a printed line). Reproduced to the dollar from the data in all three books:

| Book | Pension allocations + advance payments | "To Reimburse ..." lines | "Transfer ..." lines | Total | Printed? |
|---|---:|---:|---:|---:|---|
| 2025 ordinance | 1,256,927,474 | 278,432,506 | 8,152,215 | 1,543,512,195 | 2026 Overview p. 182, 2025 column: **1,543,512,195 exact** |
| 2026 recommendations | 1,081,434,890 | 300,280,341 | 7,761,432 | 1,389,476,663 | 2026 Overview p. 182: **1,389,476,663 exact** |
| 2026 passed ordinance | 1,220,866,110 | 300,280,341 | 7,761,432 | **1,528,907,883** | not printed, same rule |

The rule: sum every Finance General line whose account contains "Pension Allocation" or "Advance Pension Payment", starts with "To Reimburse", or starts with "Transfer". The one exception, which matches OBM to the dollar both years, is the Corporate Fund's $350,000 "Transfers Out" line (OBM leaves it out). The pension piece was $139.4M higher in the passed ordinance than in the recommendations because Council raised the advance pension payments (Combined Technical Amendments package, dated 2025-12-22, raises the five advance-payment revenue and expense lines).

**Our current rule misses $7,761,432 here.** `scripts/finance_general.py` removes pension and "To Reimburse" lines but not the "Transfer ..." lines. Those are small ($8.1M gross), spread across Water, Sewer, Vehicle Tax, Special Events and Midway funds, plus two "Transfer to Specified Operating Funds for Administration" lines at the Houseshare surcharge funds. They are all genuine fund-to-fund moves:

| Line | $ |
|---|---:|
| Midway Fund, transfer to O'Hare Fund for administrative salaries | 3,000,000 |
| Water Fund, transfer for services provided by Police | 1,470,301 |
| Houseshare Surcharge funds, transfer to operating funds for administration | 1,467,862 |
| Special Events Fund, transfers for services (6 lines) | 354,200 |
| Water Fund, transfer for contractual services | 625,000 |
| Water, Sewer, Vehicle Tax funds, transfer for services provided by OEMC | 455,000 |
| Wheelchair Accessible Vehicle Fund, transfers out | 389,069 |
| (Corporate Fund "Transfers Out", excluded by OBM) | (350,000) |

**(b) Appendix A and B, "Internal Transfers"** (rec book pp. 616 and 619; ordinance pp. 558 and 561): **$7,766,967 + $10,911,809 = $18,678,776** in the passed ordinance ($9,015,367 + $10,911,809 = $19,927,176 in the recommendations). This is money other funds pay the Corporate Fund and Vehicle Tax Fund for services. It lives in **non-Finance-General departments** as appropriations named "For Services Provided by ..." (Fleet and Facility Management, Streets and Sanitation, Public Health, CDOT, Planning, Business Affairs). I reproduced the appendix to the dollar from the data: the sum of LOCAL-fund appropriations named "For Services Provided by <City department>" outside Finance General is **exactly $18,678,776**. The Appendix's "External Reimbursements" ($54.6M) are not deductions (General Obligation bond proceeds and similar, not fund transfers). So the answer to "search non-Finance-General departments too" is: yes, there are $18.68M there, and they are exactly the Appendix A/B internal transfers. One look-alike to ignore: the Library's "For Services Provided by Performers and Exhibitors" ($99,582) is a vendor class, not a City department.

**(c) Matching grant funds.** The ordinance's own text (Grant Detail section, p. 557) says: "Required City matching funds for grant awards are reflected under both 925-Grant Funds and Finance General. The total required City match amounts are included in the Deduct Transfer between Funds line in Summary B." In the data these are accounts named "To Provide for Matching and Supplementary Grant Funds": **$35,514,285** in 2026 ($19,892,285 in Finance General funds 0100, 0300, 0353, 0355, plus $15,622,000 in grant funds, mostly a $15M CDBG-DR line at the Department of Family and Support Services). It was $23,999,259 in 2025. This is **documented in print but is not in our rule**, and it is not a Finance General interfund line, so it adds to (b) rather than being part of (a).

## 3. The exact bridge from our number to the printed net (passed ordinance)

| Step | Removed so far | Net remaining | This step |
|---|---:|---:|---:|
| Our rule today (pension allocations + "To Reimburse") | 1,521,146,451 | 17,147,422,009 | |
| + Finance General "Transfer ..." lines (OBM def.) | 1,528,907,883 | 17,139,660,577 | 7,761,432 |
| + Appendix A and B (non-FG "For Services Provided by") | 1,547,586,659 | 17,120,981,801 | 18,678,776 |
| + Proceeds of debt (printed separately, Library term notes) | 1,673,512,670 | 16,995,055,790 | 125,926,011 |
| + Matching grant funds (documented in ordinance text) | 1,709,026,955 | 16,959,541,505 | 35,514,285 |
| + **Unexplained** | 1,826,015,457 | **16,842,553,003** | **116,988,502** |

`gap_reconcile.py` asserts that the three named pieces (7,761,432 + 18,678,776 + 125,926,011) plus the 152,502,787 residual sum to the 304,869,006 gap exactly. The matching funds are carved out of that 152,502,787, and I have only the ordinance's sentence (not an itemised OBM schedule) that they sit inside the deduction, so treat that step as documented but unverified in amount.

About the debt-proceeds step: $125,926,011 equals both the Library Fund's "Proceeds of Debt" revenue line (fund 0346) and the Library Property Tax Levy Fund's "For Payment of Term Notes" appropriation (fund 0521). OBM's footnote says debt proceeds are deducted "to more accurately reflect the City appropriation". This is OBM's convention. I have not shown it is a duplicate of any other appropriation line (the Library Fund spends the borrowed money and the levy fund repays the notes, which are two separate flows). Adopting it is a judgment call. If the site adopts it, say so on the page.

## 4. The unexplained $116,988,502 to $152,502,787

What I tested and rejected, so nobody repeats it:

- **Corporate Fund subsidy to the debt-service fund ($90,493,270).** Fund 0510 shows it as revenue and the Corporate Fund shows it as "For Payment of Bonds", same dollars on both sides. It looks like an interfund transfer. But in 2025 that line was $144,705,349, which is larger than the *entire* 2025 residual ($60,581,630), so it cannot be a component under one consistent rule. Rejected.
- **Revenue-side lines** (Internal Service Earnings from enterprise and special revenue funds, "Transfers In", TIF administrative reimbursement, casino pension transfers, Vehicle Tax "Other Reimbursements"). An exhaustive search over combinations of these, with and without the pension revenue lines, found **no combination equal to the printed deduction in 2025, 2026 recommendations and 2026 passed ordinance simultaneously.** Single-year hits exist only by coincidence with 15 to 20 items.
- **Interest income, land sales, sales-tax securitization residual:** not transfers, no fit.

What the three printed residuals look like once pieces (a), (b) are removed:

| Year/book | Printed deduct transfers | minus FG line | minus Appendix A+B | Residual |
|---|---:|---:|---:|---:|
| 2025 ordinance | 1,622,468,611 | 1,543,512,195 | 18,374,786 | 60,581,630 |
| 2026 recommendations | 1,679,051,626 | 1,389,476,663 | 19,927,176 | 269,647,787 |
| 2026 passed ordinance | 1,700,089,446 | 1,528,907,883 | 18,678,776 | 152,502,787 |

It is not stable (60.6M, 269.6M, 152.5M), which suggests it is mostly a plug OBM computes from the financial system rather than from appropriation lines. One exact fact about it: **it fell by exactly $117,145,000 between the recommendations and the ordinance** (269,647,787 to 152,502,787). `gap_reconcile.py` asserts the identity `change in deduction = change in advance pension payments + change in Appendix A - 117,145,000`, which holds to the dollar. $117,145,000 is also the recommendations-book amount of the Library term-note line, which both books already deduct separately as "Proceeds of Debt" (117,145,000 then, 125,926,011 in the ordinance). One possible reading is that the recommendations deducted the term notes twice (once in each line) and the ordinance stopped doing so. That is a guess from an exact numeric match, not something OBM states, and I could not test it further.

**What to ask OBM** (if a precise answer is needed): the composition of "Deduct Transfers between Funds" in Summary B. A single email to the Budget Director or a FOIA to `obm_foia` would settle it. Until then, the site should say: "The City subtracts about $0.15B of other internal charges that it does not itemise in the budget books."

## 5. What I recommend the site does

Remove, in this order, with the label "money counted twice":

1. Pension allocations and advance payments, $1,220,866,110 (already done).
2. "To Reimburse ..." lines, $300,280,341 (already done).
3. **New:** Finance General "Transfer ..." lines except the Corporate "Transfers Out", $7,761,432.
4. **New:** non-FG "For Services Provided by <City dept>" lines, $18,678,776. These are small per line (the largest is $9.26M, Sewer Fund paying Streets and Sanitation) and the deduction is by fund so it does not distort department totals.
5. **New, OBM convention (judgment call):** Library "Proceeds of Debt" deduction, $125,926,011, labelled as borrowed money rather than spending.
6. **New, labelled "grant match, counted in both the city and grant funds":** matching funds, $35,514,285.

That takes the site from $17,147,422,009 to **$16,959,541,505**, which is $116,988,502 above the printed $16,842,553,003. Show that last $117M as an explicit "unitemised adjustment OBM applies" line on a reconciliation page rather than burying it. All numbers then tie to a printed total and the reader can see exactly what is and is not explained.

Do not bring the total down to $16.6B by any rule. The $16.6B is the proposal and does not describe the data in `6694-f78c`.

## 6. Did mid-year 2026 amendments change the ordinance?

Yes, in small ways. `gap_midyear.py` checks each against the Council record (City Clerk eLMS API) and against the Mid-Year Budget Report (data as of 2026-05-31, `raw/gap/midyear_report_2026.pdf`).

| Change | Amount | Evidence |
|---|---:|---|
| **Grant appropriations (Fund 925), 8 Council amendments Jan to Sep 2026** | **+$72,201,330** (grants $3,869,858,000 to $3,942,059,330) | Each ordinance's "hereby appropriated" text. **Through 2026-05-31 the sum is $33,006,330, and 3,869,858,000 + 33,006,330 = 3,902,864,330 is the exact figure printed in the Mid-Year Report p. 27.** |
| Ward wage allowance cut (SO2026-0023373, passed 2026-03-18) | -$258,100 (29 wards x $8,900) | Mid-Year Report ward table: 29 of 50 wards at $440,270 vs $449,170 |
| Dozens of aldermanic and committee line transfers (within-fund) | $0 net | 24 BFY2026 rows, $834,627, none cross fund or department (dataset `7x7d-3zgj`) |
| Public Health appropriation code change (O2026-0022416) | $0 | Reclassification only |

The Mid-Year Report's own "Grand Total" budget ($14,952,722,619) equals the ordinance's local funds ($14,798,710,460) **plus $147,770,259 (Motor Fuel Tax Fund printed at 2x) plus $6,500,000 (Parking Meters Fund printed at 2x) minus $258,100 (ward cut)**, to the dollar. The report prints every Motor Fuel Tax and Parking Meters Fund line at exactly twice the ordinance amount (for example CDOT Motor Fuel Tax $213,338,012 vs $106,669,006 in the ordinance), so do not use its department-by-fund budget column as a budget figure for those two funds. Nothing else changed the local-fund total. No amendment touched the departmental structure.

Practical effect for the site: the **ordinance dataset is still correct for local funds**, and **grants are now $3.94B, not $3.87B**. Show the +$72.2M as an "amended since adoption" overlay for Fund 925 (list is in `data/gap_midyear.json`).

One more item to watch: a proposed Council ordinance (O2026-0027487, in committee) would order further advance pension payments by 2026-10-31. Not passed, so no change yet.

## 7. Files

| File | What |
|---|---|
| `scripts/gap_fetch.py` | Downloads everything cited (OBM PDFs, Socrata datasets, eLMS amendment PDFs, CPS procurement API) to `raw/gap/`. Idempotent. |
| `scripts/gap_reconcile.py` | Section 1 to 5. Asserts every printed number it uses. |
| `scripts/gap_midyear.py` | Section 6. |
| `data/gap_reconciliation.json`, `data/gap_midyear.json` | Machine-readable outputs. |
