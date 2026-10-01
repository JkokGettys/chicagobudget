# Final gap audit (re-audit): is there enough data to start building?

Re-audit 2026-10-01, after the payment dedupe, the switch to 2026 YTD vendor data (checks to 09/28/2026) and bond round 2 (+$137.4M split into series). Scripts re-run: `leaves_inventory.py`, `audit_tiers.py`, `audit_payments_dupes.py`. "Previous" = the first audit (commit be3c173), re-computed by running today's `audit_tiers.py` on that commit's `leaves_over_10m.json`, so both columns use the same rules. Budgets: City $16.84B, CPS $10.25B, Parks $637.6M.

## Verdict

**Still yes, start building v1.** City dollars in terminal items of $10M or more went from 54.3% to **53.9%**. CPS (29.6%) and Parks (29.5%) did not move. Duplicates and the stale vendor year are fixed. I found and fixed one new inventory bug (below). What is left (depth below $10M) needs OBM or FOIA answers, not more searching.

## Changes since previous audit

* **Duplicates resolved.** Both deduped files have no repeated lines except 3 (2025) and 4 (2026 YTD) identical $99M pension checks kept on purpose ($297M, $396M). Named vendor pieces hold $0.00M of repeats (was $34M).
* **Vendor pieces now 2026 YTD** (9 months, not annualized). Named pieces of $10M or more: 75 / $1,571M to **56 / $1,226M**. About $43M of the drop is dedupe, about $302M is the partial year (`payments_dedupe.md`).
* **Bond round 2:** City series-level items (tier A) 43 / $1,053M to 47 / $1,202M. Bond residuals $550M to $416M.
* **Bug fixed (`leaves_inventory.py`):** the Midway combined principal+interest block also grabbed the new Sewer 1998A row and overwrote both Sewer leaves with that one series, creating an $89.4M Sewer leftover that does not exist. Sewer's 8 series (15 rows, $117.8M) now compare to both Sewer lines ($114.1M). City after splits: 158 pieces / $5.05B before the fix, **157 / $4.97B** after. Also fixed two wrong "why can't I go deeper" sentences and a stale "2025 payee" label (section 5). `audit_tiers.py` needed no fix. `audit_payments_dupes.py` was rewritten: it only read raw 2025, so it tested 2026 pieces against the wrong year.

## 1. Tiers: terminal items of $10M or more

A = one series, contract, award or project. B = purpose named, no breakdown. C = reader cannot tell what it is for.

| Budget | Tier | Previous: items / $M / % | Now: items / $M / % |
|---|---|---|---|
| City | A | 157 / 3,600 / 21.4% | **142 / 3,404 / 20.2%** |
| City | B | 72 / 5,400 / 32.1% | **73 / 5,520 / 32.8%** |
| City | C | 2 / 147 / 0.9% | 2 / 147 / 0.9% |
| City | **Total** | 231 / 9,148 / **54.3%** | **217 / 9,072 / 53.9%** |
| CPS | A, B, C | 35 / 1,071 / 10.4%, 44 / 1,784 / 17.4%, 4 / 186 / 1.8% | unchanged, **total 83 / 3,040 / 29.6%** |
| Parks | A, B, C | 3 / 88 / 13.7%, 4 / 101 / 15.8%, 0 | unchanged, **total 7 / 188 / 29.5%** |

Why City moved ($M):

| Piece | Previous | Now | Change |
|---|---:|---:|---:|
| A: named vendor contracts | 1,571 | 1,226 | -345 |
| A: bond series and fully series-split lines | 1,053 | 1,202 | +149 |
| B: bond residual (many series) | 550 | 416 | -134 |
| B: "no matched payee" budget (less paid so far, more unmatched) | 643 | 832 | +189 |
| B: Finance General IT line 0138, no 2026 payments | 0 | 65 | +65 |
| **Net** | 9,148 | 9,072 | **-76** |

Tier C is unchanged: City = two Finance General 0140 lines (O'Hare Fund $92.2M, Corporate Fund $55.2M). CPS = $120.6M "Budget Only - Pensions", $35M Labor and Employee Relations, $30M special education budget-only. Also C, outside the table: the $117.0M OBM deduction no line explains (0.69% of City).

## 2. Coverage: share of each budget's dollars by size of the item the user ends on

| Budget | View | < $1M prev / now | $1M to $10M prev / now | >= $10M prev / now |
|---|---|---|---|---|
| City | tied only | 20.9 / 20.9 | 10.4 / 10.4 | 68.8 / 68.8 |
| City | with proxies | 31.2 / 31.2 | 15.5 / **16.0** | 53.3 / **52.8** |
| CPS | tied only | 43.2 / 43.2 | 15.4 / 15.4 | 41.3 / 41.3 |
| CPS | with proxies | 60.8 / 60.8 | 18.2 / 18.2 | 21.0 / 21.0 |
| Parks | tied only | 34.5 / 34.5 | 33.6 / 33.6 | 31.9 / 31.9 |
| Parks | with proxies | 34.5 / 34.5 | 40.7 / 40.7 | 24.7 / 24.7 |

Tied-only did not move (bond series and vendor lists are obligations or proxies). The City proxy gain is bond series moving from the $10M-plus group into $1M to $10M. CPS 21.0% counts offsets signed, 29.6% above counts them absolute.

## 3. Data-quality list

**Resolved:** duplicate rows (verified 0 non-exempt repeats in both files). Named vendor pieces on 2025 payments (now 2026 YTD).

**Remaining, unchanged:** $117.0M OBM deduction with no line (email drafted, not sent). $35.5M matching-funds assumption. $125.9M library notes convention. Grants: $30.7M ordinance vs Summary G, +$72.2M amended. $7.5M salary vs grant positions. Official statements vs ordinance $56.7M total. O'Hare 2024A/B capitalized interest up to $23.1M. CPS roster vs budget $86M. Debt service overview gap $8.9M. CPS pension $59.3M (section 4). Premium pay on 2025 payroll, CPS roster 12/31/2025, CTPF 6/30/2025, CPS fiscal year ends June. GO still has $220.0M unsplit (Tax Levy bonds, no per-series column), Water $68.8M, O'Hare $122M.

**New or newly found:**

| # | Issue | Size | UI or doc action |
|---|---|---:|---|
| 1 | **Partial year makes vendor coverage look smaller.** Budget explained by named contracts: 57.1% on full 2025, **50.8%** on 2026 YTD ($2,730M of $5,369M). Same dates of 2025: 47.4%. So it is the calendar, not worse data | -6.3 pts | Label "Jan 1 to 9/28/2026, not annualized" |
| 2 | **Key names lie.** `paid_2025` holds 2026 YTD dollars in coverage and findings JSON (167 lines in findings, 212 in `leaves_contracts.json`). Only the items file says `paid_2026ytd` | whole vendor layer | Adapter reads `meta.label`. Do not rename now |
| 3 | **Stale docs.** `contracts_vendors.md` (edited 9/30 22:15) still quotes raw 2025: $3.08B / 57%, "1,056 duplicates, not removed", Blue Cross $610M. `leaves_over_10m.md` quotes 184 leaves / $6.61B. `payments_dedupe.md` section 4 quotes City 159 / $5,103.5M, now 157 / $4,970M | docs only | Treat as history, use this file |
| 4 | **`by_family` budgets do not sum to the headline.** $4,846M vs $5,369M (YTD file), $4,957M (2025 file). Pairs with budget but no payments are dropped, $523.6M in the YTD file | $523.6M | Use `vendor_payable_budget`, never sum `by_family` |
| 5 | **$99M exemption is a judgment** (fits the ACFR, never confirmed by the City) | $297M / $396M | Footnote, one constant `CHECK_CAP` |
| 6 | **Dedupe could remove a truly repeated identical line.** Open question for Finance | unknown | Footnote |
| 7 | **Cash vs budget:** 9 months of checks beside a full-year budget | 56 pieces | Badge "paid to date" |
| 8 | **Sewer** now counts as 2 items / $114M though its 8 series are mostly under $10M (series file is $3.7M above the ordinance lines, so no residual shows, while `bond_series.md` still lists a $15.6M Sewer residual against the official statement total) | $114M | Upper bound for City A |

**Reconciliation gaps over $1M: none new.** Bond round 2 parsers tied to printed totals within $5.

## 4. Cheap wins, one fresh try (about 15 minutes)

One direct fetch (chicago.gov OBM page) worked but only listed publications. The rest used local files.

| Lead | Result |
|---|---|
| Join the 0140 lines ($92.2M O'Hare, $55.2M Corporate) to Aviation and Corporate contracts by fund | **Not possible: the payments file has no fund column** (voucher, amount, date, department, contract, vendor only), and no department is "Finance General". By department: Aviation professional-service payments are $355.5M YTD against a $422.2M budget, so nothing overflows into an O'Hare FG line. Eight departments paid $97.0M more than their professional-services budget YTD (Fleet $33.2M, Finance $28.7M, Water $16.6M), but nothing links that to the Corporate FG line. Two near-matches are coincidence: Constellation electricity contract 198906 (Assets, Information and Services) paid $92.25M in 2025 and $55.17M YTD, but the O'Hare line is steady at $91.6M to $93.1M for 2024 to 2026 while Constellation swung $54M to $92M, and the Corporate line was $51.7M and $44.4M in 2024 and 2025. The Council amendment (L-38) raised Corporate from $53.4M to $55.2M, and the account is titled "...Other Third Party Benefit Agreements". **Stays tier C. Add to the OBM email.** |
| CPS $59.3M budget-only pension | Now explained by arithmetic: $120.57M = $61.3M operating diversion (book p.34 to 35) + $59.31M, and $59.31M = State Pension Aid revenue A43005 ($363.10M) minus school-level teacher pension ($303.78M), within $9.7K. Reading: CPS books the State's on-behalf payment as expense. **This is inference, no document says it.** If accepted, CPS tier C falls from $186M to about $65M (0.6%) and B rises by $120.6M. I did not change the tier rules |

## 5. The 15 largest remaining terminal leaves and their stored sentence

P = "The City sends one payment set by law to the retirement fund, and the fund then pays thousands of retirees, so the public records stop at how many retirees there are and what the average one gets."

| # | $M | Budget | Tier | Leaf | Stored sentence |
|---:|---:|---|---|---|---|
| 1 | 818.1 | City | B | Municipal pension, unfunded remainder | P |
| 2 | 817.8 | City | B | Police pension, unfunded remainder | P |
| 3 | 348.7 | City | B | Fire pension, unfunded remainder | P |
| 4 | 256.1 | City | B | CDOT highway grant (20.205) construction, no matched payee | "The City set this money aside for contracts, but no payment so far this year matches it to a company, so there is no one to name yet." (new, replaced a wrong one) |
| 5 | 254.2 | CPS | A | CIP Series 2009G principal | "This is one bond's yearly payment to the people who lent the money, and it is already as small as the bond itself." |
| 6 | 222.4 | City | B | Police pension, net normal cost | P |
| 7 | 193.5 | City | B | O'Hare FAA grant reserve, no named award | "The airport has promises of federal money for runways and terminals, but not enough named jobs yet to explain the rest." |
| 8 | 161.2 | City | B | Municipal pension, advance payment | "This is one extra payment the City chose to make to the retirement fund on top of what the law requires." |
| 9 | 146.9 | City | B | Municipal pension, net normal cost | P |
| 10 | 143.3 | CPS | B | Vacancy factor (planned cut to teacher pay) | "This is a planned cut that offsets spending counted elsewhere, so there is nothing to itemize." |
| 11 | 126.1 | City | A | State/Lake Loop station, rest of FTA award | "Almost all of this money is for one big train station rebuild, and the public lists show it by where the money came from, not by what each dollar buys." |
| 12 | 121.9 | City | A | F.H. Paschen / S.N. Nielsen contract 310789 (CDOT), paid 2026 YTD | "A few big companies each get one large contract payment, and the City does not publish smaller pieces of one contract." |
| 13 | 120.6 | CPS | C | Budget Only - Pensions (General Education Fund) | "This is a reserve the district sets aside for pensions, health insurance or claims, and the real bills arrive later from the insurers and pension funds." |
| 14 | 120.0 | CPS | B | Contingency for grant expansion | "This is money held back for things that have not been decided yet, so it has no purchases to list." |
| 15 | 116.8 | CPS | B | Hospitalization reserve (HCSC share, proxy) | "CPS pays most health bills as they come in, so this reserve is a guess at bills that have not arrived yet, and the insurers do not publish who each claim was for." |

Next: GO interest residual $111.6M and principal residual $108.4M. Their sentence used to say "one bond's yearly payment", wrong for many series. Now: "Several older bonds share this line, and the public statements we found do not print each bond's share for 2026." Items 1 to 3, 6, 8, 9 are pensions, so the pension caveat below must sit beside them.

## 6. Recommendation and UI caveats

**Build v1 now** with City, CPS and Parks. The risk is honest presentation, not missing data. Optional, not blocking: send the OBM email (add the 0140 question), and decide whether to relabel CPS $59.3M as "inferred".

1. **Totals:** "$16.84B as passed" (gross $18.67B), with a reconciliation page showing the **$117.0M unitemised OBM adjustment** and the $125.9M and $35.5M conventions.
2. **Badge every number:** Budget (2026), Tied, Proxy, Paid to date, or 2025 actual. Never mix actuals into plan totals.
3. **Vendor numbers:** "paid Jan 1 to 9/28/2026, not annualized, duplicates removed". Read `meta.label`, not key names. Never compare coverage percentages with full-year ones.
4. **"Why can't I go deeper?"** on every terminal item of $10M or more (in `data/leaves_over_10m.json`). Tiers A, B, C look different.
5. **Pensions:** "the City's legal payment, not what retirees receive".
6. **Bonds:** "from official statements". Show GO ($220M), Water ($69M) and O'Hare residuals as "other series". O'Hare principal/interest split is approximate.
7. **Grant reserves:** "estimate, caps not exact splits", with the +$72.2M amended overlay.
8. **Duplicates:** footnote that repeated lines were removed and three or four $99M pension checks were kept on purpose.
9. **Dates:** show the year of every proxy (premium pay 2025, CPS roster 12/31/2025, CTPF 6/30/2025). CPS fiscal year ends June.
10. **People:** job titles only, groups under 5 rolled up.

Commit note: per instructions only this file, `scripts/audit_payments_dupes.py` and `data/leaves_over_10m.json` are committed. The inventory fixes are in `scripts/leaves_inventory.py`, **left uncommitted**, so the committed JSON cannot be regenerated from HEAD until that file is committed too.
