# Final gap audit: is there enough data to start building?

Author: gap finder (final audit), 2026-10-01. Numbers come from `scripts/leaves_inventory.py` (re-run), `scripts/audit_tiers.py` and `scripts/audit_payments_dupes.py` (both new, read-only). Percentages use the budget totals you gave: City $16.84B net, CPS $10.25B, Parks $637.6M.

## Verdict

**Yes, start building v1.** The three budgets tie to printed totals, and every dollar can be reached by clicking. What is not finished is depth below $10M for about **54% of City, 30% of CPS and 30% of Parks dollars**. The site should show those as honest dead ends with a reason, not hide them. More research will not move those numbers much without FOIA requests or OBM answers.

## 1. Where the dollars stop (items of $10M or more a user cannot click past)

Tiers: **A** = one bond series or loan, one named contract or payee, one named award or project. **B** = purpose named, no breakdown (pension contribution, unnamed grant reserve, bond residual, contingency, claims). **C** = a reader cannot tell what it is for.

| Budget | A items | A $M | A % | B items | B $M | B % | C items | C $M | C % | Total $M | % of budget |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| City | 157 | 3,600 | 21.4% | 72 | 5,400 | 32.1% | 2 | 147 | 0.9% | 9,148 | **54.3%** |
| CPS | 35 | 1,071 | 10.4% | 44 | 1,784 | 17.4% | 4 | 186 | 1.8% | 3,040 | **29.6%** |
| Parks | 3 | 88 | 13.7% | 4 | 101 | 15.8% | 0 | 0 | 0% | 188 | **29.5%** |

Tier C is small: City $147M is two Finance General "professional services" lines (O'Hare Fund $92.2M, Corporate Fund $55.2M) with no matching payments. CPS $186M is $120.6M of "Budget Only - Pensions" (only $61.3M of it is explained by the budget book's operating diversion, so $59.3M is genuinely unexplained), $35M "Labor and Employee Relations", $30M of Special Education budget-only lines. **Also tier C: the $117.0M OBM deduction no line explains (0.69% of City).** City tier B is mostly pension contributions $2.84B, unnamed grant reserves about $1.5B, bond residuals $0.54B, a $56.6M planned savings offset. Offsets are counted by absolute value here.

How the earlier "team splits" number maps: City 175 leaves / $5.19B, CPS 53 / $2.06B, Parks 4 / $0.08B. Those exclude single bond series, named bond pieces and pension pieces that are still $10M or more, which is why the table above is higher. Tier rules are in the script and are my judgment, so argue with them if you like.

## 2. Coverage: share of each budget's dollars by the size of the item the user ends on

"Tied" = ties to the dollar or is a printed obligation. "With proxies" adds count x average (another year or basis) and vendor lists from 2025 payments. Salary rows count as person level (under $1M each). Only leaves of $10M or more were re-split, so the $1M to $10M band is as published.

| Budget | View | < $1M | $1M to $10M | >= $10M |
|---|---|---:|---:|---:|
| City | tied only | 20.9% | 10.4% | 68.8% |
| City | with proxies | 31.2% | 15.5% | 53.3% |
| CPS | tied only | 43.2% | 15.4% | 41.3% |
| CPS | with proxies | 60.8% | 18.2% | 21.0% |
| Parks | tied only | 34.5% | 33.6% | 31.9% |
| Parks | with proxies | 34.5% | 40.7% | 24.7% |

CPS "21.0% >= $10M" counts the offsets signed, which is why it is lower than the 29.6% above (absolute). `research/cps_deep.md` says 54.8% under $1M as an upper bound, using proxies on $1M+ salary leaves too.

## 3. Data quality issues that could embarrass the site

Reconciliation gaps over $1M (all documented, none hidden):

| # | Gap | $ | Where | UI treatment |
|---|---|---:|---|---|
| 1 | OBM "Deduct Transfers" part no line explains (after $35.5M matching funds). Same item was about $60.6M in 2025 | **116,988,502** | `transfer_residual.md` | Explicit "unitemised OBM adjustment" line. OBM email is drafted, not sent |
| 2 | Matching funds assumed inside the deduction, amount unverified (ordinance sentence only) | 35,514,285 | `reconciliation.md` | Label "documented, not verified" |
| 3 | Library term notes removed as debt proceeds, OBM convention | 125,926,011 | `reconciliation.md` | Say it is a convention |
| 4 | Grants: ordinance vs Summary G | 30.7M ($27.5M no grant code, $3.2M net) | `grants_capital.md` | Footnote |
| 5 | Grants amended after adoption | +72.2M (3.87B to 3.94B) | `reconciliation.md` | Overlay "amended since adoption" |
| 6 | City salary: grant-fund positions vs line, unexplained | 7.5M | `city_personnel.md` | Footnote |
| 7 | Bond ordinance vs official statement: O'Hare 3.86M, Midway 4.20M, Sewer 7.43M (Sewer OS includes defeased 2008C), GO ordinance vs ACFR 29.9M, STSC ACFR vs Overview 11.3M | 56.7M total | `bond_series.md`, `pensions_debt.md` | Show series as "from official statements, differ from budget by x" |
| 8 | O'Hare 2024A/2024B gross of capitalized interest, true cash lower by up to | 23.1M | `bond_series.md` | Flag on those two series |
| 9 | CPS budget-only pension, part unexplained | 59.3M | `cps_deep.md` | Tier C label |
| 10 | CPS roster vs budget salary (3.756B vs 3.670B) | 86M | `cps_deep.md` | "Roster allocation, approximate" |
| 11 | Overview vs ordinance: debt service +8.88M not itemized. Pension +82.95M is explained (Council raised advance payments) | 8.9M | `pensions_debt.md` | Footnote |
| 12 | Parks "not itemized on any department page" (under the $1M line, listed for completeness) | 0.88M | `park_district.md` | Own small node |
| 13 | CPS capital project list vs fund lines | $3,874 (rounding) | `cps.md` | None |

Also: the inventory's City tree is $16,959M, $117M above the printed $16,843M (that is gap 1). The Mayor's "$16.6B" is the proposal, so the site total must say "$16.84B as passed".

**Proxy vs tied.** Tied: City salaries (37 leaves, $3.2B, ties exactly), Parks museums and capital transfer, Parks laborers, pension net normal cost and funding remainder (derived from valuations, not payments). Proxy (count x average from another year or basis): premium pay and overtime (2025 payroll), health (rounded enrollment shares), pensions by benefit type, CPS pensions, buses, JLL per building, charter tuition, 2025 vendor lists. Proxies are about $4.6B City and $1.8B CPS before splits, labelled in each record.

**Stale or mismatched dates.** Vendor pieces and the $0.64B "no matched payee" residual use **2025** payments against **2026** budget: named pieces $1.57B. Premium pay uses 2025 payroll. CPS roster is 12/31/2025, CTPF valuation 6/30/2025, parks pension 12/31/2025, Mid-Year grants extract 2025-06-01 and 2026-05-31, O'Hare and Midway series use bond year ending Jan 1 2027 while Water and Sewer use calendar 2026. CPS FY2026 is July 2025 to June 2026 and has already ended, while the City is calendar 2026. Grand total of 2025 payments is $10.66B, and **$6.07B has no department** (pensions, banks, county).

**Duplicates.** `audit_payments_dupes.py` confirms **1,056 exact duplicate rows, $371.0M**. $297.0M of it is three identical $99M checks to the Municipal Employee Pension Fund (each appears twice), which the leaf work already drops. **$34.1M sits inside named vendor pieces**, mostly TranSystems contract 47314 ($25.1M duplicated, so its $37.2M piece may really be $12.1M), Delaware Cars $3.0M, 1237 N. California $3.3M. Same-voucher repeats may be legitimate multi-line vouchers, so I did not remove them. Negatives (voids) total only -$0.47M. All 115,810 rows are dated 2025, so no stray-year rows.

## 4. Cheap remaining wins (each under 1 hour)

I could not run web searches (search engine blocked), so these come from the existing notes, not new research.

| Win | Expected $ impact |
|---|---|
| Swap vendor pieces to **2026 YTD payments** (`raw/contracts/payments_all.csv`, 85,720 rows, $8.06B, already local) | Removes the stale label on $1.57B of City named pieces. No tier change |
| Drop or flag duplicate rows in the vendor join | Corrects up to $34M, TranSystems from $37.2M to $12.1M (moves it under $10M, tier A to A) |
| Move $61.3M of CPS "Budget Only - Pensions" from tier C to B (book p.35 explains it) | $61M C to B |
| Parse the already downloaded Sewer, Water and GO 2012B/2014B statements | Up to $60M Sewer and part of $118M Water residual into series. Unproven, layouts differ |
| Send the drafted OBM email (`transfer_residual.md` section 6) | Could close $117M, answer time unknown, costs 5 minutes |
| Try joining the two Finance General "0140 professional services" lines ($147M, tier C) to Aviation and Corporate contracts by fund | Unverified lead, up to $147M C to A or B |

Not cheap: O'Hare $122M residual (needs EMMA or trustee files), grant project lists for O'Hare and CDOT (pages 404 or blocked), CPS contingency ($0.54B, no source exists), health by plan (no source exists).

## 5. Recommendation and caveats the UI must show

**Build v1 now** with City, CPS and Parks. The main risks are honesty of presentation, not missing data. Must-have UI behavior:

1. **Totals:** "$16.84B as passed", gross $18.67B, with a reconciliation page listing the bridge and the **$117.0M unitemised OBM adjustment** (and the $125.9M and $35.5M conventions).
2. **Badge every number** as Budget (2026), Tied, Proxy, or 2025 actual. Never mix actuals into plan totals.
3. **"Why can't I go deeper?"** sentence on every terminal item of $10M or more (already stored in `data/leaves_over_10m.json`). Tier B and C items should look different from A.
4. **Pensions** must say "the City's legal payment, not what retirees receive". The $818M-type remainder is debt payment set by state law.
5. **Bond series** say "from official statements, split between principal and interest is approximate for O'Hare" and show residuals as "other series".
6. **Grant reserves** say "estimate, caps not exact splits", with the $72.2M amended-since-adoption overlay.
7. **Duplicates** footnote on vendor pages: 1,056 repeated rows, $371M, not removed.
8. **Dates:** show the year of every proxy, and note CPS FY ends June.
9. **People:** job titles only, groups under 5 rolled up (already decided).

## 6. Inventory bugs fixed in this audit

`scripts/leaves_inventory.py` ingested `data/city_bond_series_2026.json` with three errors, now fixed: (1) fund matching used a substring, so "GO" matched "Chicago O'Hare" and "Chicago Midway", making the GO leaf show $571M of series against a $285M line. (2) Midway's combined principal and interest rows were read as interest only. (3) The six GO series groups from `debt_2026.json` were dropped when the file landed. Effect: City after team splits moves from $5.50B (committed run) to **$5.19B**, 175 leaves. CPS and Parks are unchanged. `data/leaves_over_10m.json` is regenerated.
