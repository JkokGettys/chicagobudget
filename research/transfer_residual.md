# The unexplained part of "Deduct Transfers between Funds"

Author: residual-hunter agent, 2026-10-01. Follow-up to `research/reconciliation.md`.

## Bottom line

I could **not** explain the $116,988,502 (or $152,502,787 before matching funds). I tested twelve families of hypotheses, with exact subset-sum searches over every revenue and appropriation line in up to five books, and none produced a rule that reproduces the printed deduction. I would rather say that than invent a rule. Section 6 has a ready-to-send question to OBM.

What I did add, all exact and reproducible:

1. **The residual is not new in 2026.** It exists in every book I could test. It sat at about $60M in both 2025 books and about $66M in the 2024 ordinance, then stepped up in 2026 (section 2). A one-year coincidence is unlikely. This looks like a standing OBM adjustment whose size changed in 2026.
2. **The revenue-side "reimbursement" lines add nothing new.** Corporate Fund Internal Service Earnings from Enterprise Funds ($202,689,118) equals, to the dollar, the sum of the "To Reimburse the Corporate Fund..." lines in the four enterprise funds already inside the Finance General total (section 4).
3. **Several plausible explanations are ruled out** (section 5), so nobody repeats them.
4. **The 2025 residual is the same in the recommendations and the ordinance** (about $60.6M), even though the Finance General line moved by exactly $300,000,000 between them. So Council's pension changes flowed through the deduction dollar for dollar, and the residual did not move. That is consistent with the residual being a separate, fixed item.

## 1. Targets

All from the printed books. `scripts/residual_checks.py` asserts every figure.

| Book | Printed "Deduct Transfers" | FG interfund line (data = printed) | Appendix A+B internal | **Residual** | Matching funds (ord p. 557) | Residual after matching |
|---|---:|---:|---:|---:|---:|---:|
| 2024 ordinance (approx.) | ~1,451,400,000 | 1,366,944,558 | 18,480,973 (proxy) | ~65,974,000 | 35,309,645 | ~30,665,000 |
| 2025 recommendations (approx.) | ~1,322,500,000 | 1,243,512,195 | not fetched, 2025 ord used | ~60,613,000 | 23,999,259 | ~36,614,000 |
| 2025 ordinance | 1,622,468,611 | 1,543,512,195 | 18,374,786 | **60,581,630** | 23,999,259 | 36,582,371 |
| 2026 recommendations | 1,679,051,626 | 1,389,476,663 | 19,927,176 | **269,647,787** | 35,514,285 | 234,133,502 |
| 2026 ordinance | 1,700,089,446 | 1,528,907,883 | 18,678,776 | **152,502,787** | 35,514,285 | **116,988,502** |

Notes on the approximate rows. The 2025 Overview (p. 29) prints the 2024 and 2025-proposed deductions only to $0.1M (the $1,439.6M footnote less $117.1M debt gives $1,322.5M, and $1,568.6M less $117.1M gives $1,451.4M). Those residuals are good to about plus or minus $60,000. For the 2024 appendix I used the same "For Services Provided by" data rule that reproduces Appendix A+B exactly in 2025 and 2026. I could not fetch the 2024 or 2025 recommendation books from chicago.gov (the guessed URLs returned 404 and the OBM page for those years was not in `raw/gap`), so those two rows are labelled approximate everywhere.

Datasets used for prior years, fetched by `scripts/residual_fetch.py`: `x394-e874` (2024 ordinance), `rrdf-6mjk` (2024 recs), `miyk-k49p` (2025 recs), `rmi8-cugu` / `at79-usba` / `u72v-5iyn` (revenue).

## 2. What the multi-year pattern says

`scripts/residual_yoy.py` prints the table above plus:

- 2025: deduction recommendations to ordinance changed by about +$299,968,611 while the FG line changed by exactly +$300,000,000 (the Council raised Corporate Fund pension allocation revenue lines: Policemen's +$216.3M, Firemen's +$57.6M, Municipal +$26.1M). The residual stayed at $60.6M. Within the $0.1M rounding of the recommendation figure, **the residual did not change.**
- 2026: the recommendations residual was $269.6M and fell by **exactly $117,145,000** in the ordinance. This is the identity already in `gap_reconcile.py`. I searched all 131 lines that changed between the two books (appropriations by numeric account code, revenue by fund and source, advance-pension lines removed) for any subset of up to three that sums to -117,145,000 or +117,145,000 (`scripts/residual_recdelta.py`): **zero hits**, and zero decoy hits, so the search is not drowning in coincidences. The only line equal to 117,145,000 is the Library "Payment of Term Notes" line in the recommendations, which is what the earlier note already observed. In the ordinance that line is $125,926,011 and nothing is equal to $117,145,000.
- So the picture is: roughly a $60M standing item in 2024 and 2025, and in 2026 an extra roughly $92M (ordinance) or $209M (recommendations) on top. In the recommendations the extra equals the ordinance extra plus exactly the Library term-note amount.

I tried to explain the 2026 step-up (ordinance: $91,921,157 above 2025) from the rounded narrative figures. The 2026 Overview (p. 38) and the 2027 Forecast (Revenue Projection section) say the 2026 Corporate Fund includes $166.0M of one-time borrowing in "Proceeds and Transfers in - Other" (2025 had only $28.0M there, which is Skyway and meter interest) and an assumed $89.6M "from the sale of City debt" in the Fines line. $91,921,157 minus $89.6M is $2,321,157. That is close but is not distinguishable from chance: the same near-match test finds 4,655 pairs of changed lines within $50,000 of that leftover versus 1,465 for a decoy target (`scripts/residual_debt2026.py`). **I am not claiming it.** It is a lead for OBM to confirm or kill: if some of the 2026 one-time borrowing is deducted as "transfer" rather than as "proceeds of debt", the step-up would be explained.

## 3. Searches run, and what each found

Every search runs against exact targets and a decoy target (same size, shifted by $1,000,003 or more) so a reader can see how many hits chance alone gives. Zero decoy hits with zero real hits means the search space was too sparse to hit by luck and the true composition is outside it.

| # | Script | Candidate space | Target | Result |
|---|---|---|---|---|
| 1 | `residual_subsetsum.py` | 26 named interfund-like lines (Internal Service Earnings lines, Proceeds and Transfers In, Transfers In, TIF admin reimbursement, bond fund subsidy, casino pension, Water and Sewer Utility Tax, capital funding, indirect costs, tuition reimbursement, grant-side matching...) all 2^26 subsets, 2025 and 2026 ordinance together | residual; residual minus matching | 0 hits. Delta version (rule may change by year): 0 hits |
| 2 | `residual_broad.py` | 1,205 lines (every revenue line plus every appropriation grouped by fund and account text), size 1 to 3 | same two, plus minus Corporate "Transfers Out" | 0 hits |
| 3 | `residual_codes.py` | 2,717 lines keyed on numeric account codes so the **recommendations book works too**, 3 books at once (2025 ord, 2026 rec, 2026 ord), size 1 to 3 | residual; minus matching; minus Transfers Out | 0 hits, 0 decoy |
| 4 | `residual_fundtotals.py` | 581 aggregates: per fund, per fund and department, per revenue group, per 94xx to 96xx object code, per Internal Service Earnings line, non-levy revenue in the property-tax funds | residual; minus matching; deduction minus pension revenue | 0 hits, 0 decoy |
| 5 | `residual_revside.py` | Whole deduction defined from the revenue side: four bases (nothing; pension revenue lines; plus Enterprise and Special Revenue Internal Service Earnings; plus all four) plus up to 4 more revenue lines, 3 books at once | printed deduction in all three books | 0 hits, 0 decoy |
| 6 | `residual_2024.py` | 3,596 lines, 2024 ordinance added as a tolerant third book (plus or minus $100,000) | residual; minus matching | 0 hits, 0 decoy |
| 7 | `residual_yoy.py` | 1,420 changed lines, size 1 to 3 | residual jump 2025 to 2026, ordinance ($91,921,157) and recommendations ($209,066,157) | 0 hits |
| 8 | `residual_recdelta.py` | 131 lines that changed between recs and ordinance | plus or minus 117,145,000 | 0 hits, 0 decoy |
| 9 | `residual_appendix_grants.py` | 12 named items incl. Appendix A/B "External Reimbursements" ($54.6M in 2026), Fund 0075 indirect cost recovery grants, grant-side matching, all subsets | residual; minus matching | 0 hits |
| 10 | `residual_debt2026.py` | Rounded debt narrative figures ($166.0M, $89.6M, $28.0M...) within plus or minus $150,000 | residual forms | 0 hits |
| 11 | `residual_stable.py` | 3,145 lines unchanged between recs and ordinance, size 1 to 4 | $152,502,787; $116,988,502; minus 350k | **Hits exist but are not evidence.** 255 hits for the first target against 149 and 145 decoy hits, and 396 against 5,411 and 2,194 for the second. Four-line searches over 3,145 lines hit by chance. I list the method so it is not mistaken for a finding. |

Search 11 is the only one that returned hits, and its decoy counts show they are noise. Searches 3 to 6 are the strong ones, because requiring the same rule to hit 2025 and 2026 (and the recommendations) at once makes chance matches vanishingly unlikely, and they returned nothing.

## 4. New exact facts worth keeping

**4a. The revenue-side reimbursement lines double the lines we already remove.** `scripts/residual_appendix_grants.py` asserts:

- Corporate Fund revenue "Internal Service Earnings: Enterprise Funds" = **$202,689,118** = the sum of the Finance General "To Reimburse the Corporate Fund..." appropriations in Water, Sewer, Midway and O'Hare funds, exactly.
- "Internal Service Earnings: Special Revenue Funds" = $93,416,483 versus $97,591,223 of "To Reimburse" lines in the other funds. The $4,174,740 difference is the Corporate Fund's own $4,427,507 reimbursements to the Midway Fund for Fire Department salaries and benefits (appropriated in the Corporate Fund, so not revenue to the Corporate Fund) and the data then leaves the Corporate Fund's revenue line $252,767 above the sum of the other funds' reimbursement lines, which I cannot explain. Treat the special revenue match as near-exact, not exact.
- So Internal Service Earnings are the revenue mirror of lines already inside the FG interfund total. Searching the revenue side for the residual finds nothing because the revenue-side transfers are already counted.

**4b. The rule that ties to the dollar for the Finance General line and Appendix A/B holds in every book.** 2025 ordinance, 2026 recommendations and 2026 ordinance reproduce both pieces exactly. The 2024 ordinance is only printed to $0.1M, so it gives a residual of about $66M under the same rule, which is the same order of size. So the explained part of the deduction uses one stable definition, and the residual is a separate quantity.

**4c. Gross totals reproduce.** The data sums to the printed gross in all three books checked ($18,842,061,980; $18,350,767,715; $18,668,568,460), asserted in `residual_checks.py`. The residual is not a data-extraction error.

## 5. Hypotheses ruled out

| Hypothesis | Why not |
|---|---|
| Corporate Fund subsidy to the bond fund ($90,493,270) | Already rejected in the earlier note. $144.7M in 2025 exceeds the entire 2025 residual. Re-tested inside search 1 and 3: no combination. |
| Revenue-side transfers (Internal Service Earnings, Proceeds and Transfers In, Library and bond fund Transfers In, TIF admin reimbursement, Vehicle Tax Other Reimbursements) | Searches 1, 5 and 9. Also 4a: they are the mirror of lines already counted. |
| Casino pension revenue, Water and Sewer Utility Tax to the Municipal fund | In search 1 and 9 candidate lists: no combination. |
| Appendix A/B "External Reimbursements" | These are GO bond, grant and TIF reimbursements, not fund-to-fund. Search 9: no combination. |
| Grant side: Fund 0075 indirect cost recovery, grant-side matching | Search 1 and 9. Grant-side matching ($15,622,000) is already inside the $35,514,285 matching-funds step. |
| A single fund-level or department-level total | Search 4. |
| Mid-year ordinance amendments | The residual is in the passed ordinance and in 2024 and 2025 books, so it predates them. |
| Library term notes counted twice in the recommendations | Not testable beyond the exact numeric match already recorded. Nothing else changed by that amount (search 8). |

## 6. Question for OBM (ready to send)

To: budget@cityofchicago.org  (or the Budget Director's office, with a FOIA to `obm_foia` as fallback)

Subject: Question on the composition of "Deduct Transfers between Funds" in the 2026 Annual Appropriation Ordinance

> Hello,
>
> I am building a public explorer of the City's budget using the open data portal datasets and the published books. I would appreciate help understanding one line.
>
> The Annual Appropriation Ordinance for 2026 (Summary B and Summary G, page 544) deducts $1,700,089,446 for "Transfers between Funds" and $125,926,011 for "Proceeds of Debt", giving a net total of $16,842,553,003. From the appropriation data I can account for $1,547,586,659 of the transfer deduction:
>
> - Finance General "Interfund Transfers and Reimbursements" (pension allocations and advance payments, "To Reimburse..." and "Transfer..." lines): $1,528,907,883, which matches your own figure for the Recommendations ($1,389,476,663, 2026 Budget Overview p. 182) and for 2025 ($1,543,512,195) to the dollar under the same rule.
> - Appendix A and B "Internal Transfers": $18,678,776 ($7,766,967 plus $10,911,809).
>
> That leaves **$152,502,787** that I cannot trace to any appropriation or revenue line. The ordinance text (Grant Detail, p. 557) says required City matching funds are included in this deduction. I find $35,514,285 of lines named "To Provide for Matching and Supplementary Grant Funds"; if all of that is in the deduction, **$116,988,502** is still unexplained.
>
> The same remainder is about $60.6M in the 2025 ordinance and about the same in the 2025 recommendations, so it looks like a standing item. In the 2026 Recommendations it was $269,647,787, and it fell by exactly $117,145,000 (the Library term note amount) between the Recommendations and the ordinance.
>
> Could you tell me:
> 1. Which accounts, funds or transactions make up this remaining amount, and is there a schedule?
> 2. Whether the matching funds in the deduction are the full $35,514,285 or a different amount.
> 3. Whether the Corporate Fund's 2026 one-time borrowing (about $166M in "Proceeds and Transfers in - Other") or other debt proceeds are treated as a transfer or as proceeds of debt, and why the Recommendations deducted $269.6M to the ordinance's $152.5M here.
>
> A pointer to a schedule, or a one-line definition of the deduction, would be plenty. Thank you for the work that goes into these books.

Questions 1 to 3 are in decreasing order of value. Question 3 is the only lead from the multi-year pattern (section 2) and is phrased as a question, not a claim.

## 7. What the site should do now

No change to `research/reconciliation.md` section 5 is needed. The conclusion stands: remove the itemised pieces, then show the remaining **$116,988,502** (or $152,502,787 if the matching-fund step is not adopted) as an explicit "unitemised adjustment OBM applies" line on a reconciliation page. Add one fact from this note to that page: the same adjustment was about $60.6M in 2025, so it is not a 2026 anomaly, and the 2026 increase is not explained by any line in the books.

## 8. Reproduce

`python3 scripts/residual_fetch.py` (prior-year datasets into `raw/residual/`, gitignored), then any `scripts/residual_*.py`. Shared loader: `scripts/residual_pool.py`. Each script is self-contained, prints its result, and asserts the printed figures it relies on. Run times are under 20 seconds each. Logs from the run that produced this note are in `raw/residual/out/` (gitignored).

| Script | Section |
|---|---|
| `residual_checks.py` | 1 |
| `residual_yoy.py` | 1, 2 |
| `residual_recdelta.py` | 2, 3 (search 8) |
| `residual_debt2026.py` | 2, 3 (search 10) |
| `residual_subsetsum.py`, `residual_broad.py`, `residual_codes.py`, `residual_fundtotals.py`, `residual_revside.py`, `residual_2024.py`, `residual_appendix_grants.py`, `residual_stable.py` | 3, 4, 5 |

## 9. Limits

- Two of the five books (2024 ordinance, 2025 recommendations) have deductions printed only to $0.1M, so their residuals are approximate. I could not fetch those books' PDFs. If someone can, the exact 2025 recommendation deduction would sharpen the 2025 recommendations-to-ordinance finding in section 2.
- The searches only see what the open data shows. If OBM computes the adjustment from the financial system (for example actual interfund journal entries, or a fund-level netting), no appropriation or revenue line can reproduce it, and only OBM can resolve it.
- I did not test sums of more than four lines in the broad searches. With 1,000 to 3,000 candidate lines, any five-line search would produce chance hits (as search 11 shows already at four), so a deeper search cannot be told apart from noise.
