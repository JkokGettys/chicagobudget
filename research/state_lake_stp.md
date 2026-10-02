# State/Lake: is the $102.1M older STP ledger record superseded?

**Verdict: no. It is not a leftover copy of the newer $18.2M record, and the tree is not double counting it. The box stays at $102,140,573. What changed is its note, which used to say it "may have been re-coded into newer records" (that guess is now answered).** The earlier guess in `research/cdot_projects.md` (that FTA de-obligations of $55.3M and $9.8M might have cancelled it) was wrong: they were cancelled and re-obligated in the same month.

All numbers below are printed by `python3 scripts/state_lake_stp_check.py` from cached files. `scripts/cdot_build.py` imports the same checks and stops if any of them stops being true.

## The question

The State/Lake Loop Elevated Station box ($329,801,213, ledger project D1209) has two Surface Transportation Program (STP) children:

| Box | Amount | Ledger record | Extract |
|---|---:|---|---|
| STP money, older extract | $102,140,573 | F0W16-D1209-P842115-2024, grant start 2024-10-04, budget $102,140,573, spent $0 | 2025-06-01 only |
| STP money, newer extract | $18,190,500 | F0W16-D1209-P842125-2016, grant start 2016-07-18, budget $34,080,000, spent $15,889,500 | 2026-05-31 only |

If the newer record replaced the older one, the $102.1M would be money that was re-coded or paid, and counting it again would overstate the piece by up to $102.1M.

## Evidence

**1. The two ledger records are different grants, not a record and its update.** They have different record ids, grant start dates (2024-10-04 and 2016-07-18) and budgets. The two ledger extracts share no record ids at all (0 of 280 and 509 rows), so a record cannot be followed from one extract to the other by id. Only 9 of 229 and 379 fund and project pairs appear in both. For those 9, the grant start dates differ in 8 and the budgets differ in 4 (including this one, whose two records are D1209 fund F0W16 at $102,140,573 and $34,080,000). So the ledger cannot be followed from one extract to the next, and absence from the newer extract proves nothing by itself.

**2. Each record matches a different FTA obligation on award IL-2016-002** (USASpending award funding history; FTA months run October = 1):

| FTA obligation | Amount | Matches |
|---|---:|---|
| FY2023, two obligations ($28,968,000 and $5,112,000) | $34,080,000 | Newer STP record, to the dollar |
| FY2025 period 3 (December 2024), one obligation | $102,140,573 | Older STP record, to the dollar, and CDOT's FFY2024 STP programming for State/Lake ($77,140,573 + $25,000,000 redistribution) |
| FY2025 period 11 (August 2025) | $85,000,000 | CDOT's FFY2025 STP programming ($68,552,719 + $16,447,281), not in either ledger extract |

**3. The January 2025 de-obligations did not touch the $102.1M.** In FTA period 4 of FY2025 (January 2025) the history shows -$55,300,000 and -$9,774,524 (together -$65,074,524) and new obligations of $6,820,501 and $58,254,023 (together $65,074,524). The net is exactly zero. Cumulative obligations are $260,580,572 both after December 2024 and after January 2025. The December 2024 obligation is never reversed.

**4. The newer ledger plus three obligations it leaves out equals the award.**

| Piece | Amount |
|---|---:|
| 2026-05-31 ledger, FTA records of project D1209 (budget) | $179,440,000 |
| + December 2024 STP, only in the 2025-06-01 extract | $102,140,573 |
| + August 2025 STP, in neither extract | $85,000,000 |
| + August 2025 other obligation, in neither extract (USASpending does not name its fund, we read it as CMAQ because the STP amount is already placed) | $48,040,000 |
| **Total** | **$414,620,573** |
| Award obligated (USASpending) | $414,620,572 |

The difference is $1. If the older record were already inside the newer ledger, this sum would overshoot the award by $102.1M. It does not. The CIP (PDF p. 168) agrees: its federal STP fund 0W16 totals $221,220,573, which is $34,080,000 + $102,140,573 + $85,000,000 to the dollar. The 2026 ledger's other FTA records also match obligations (FY2024 $65,430,000, August 2025 $15,000,000 in two pieces, and the direct record of $64,930,000, which is $2.0M + $3.0M + $53.93M of FY2023 obligations plus $6.0M, the amount the award page counts that the account-level history does not).

**5. Money is not double counted in the tree.** The tree has no other box of $102,140,573 and no other box for ledger project D1209 outside this piece. Searching every box and side fact for the amount finds only this box and one side fact that lists the obligation history.

## What the evidence cannot settle

- **How much of the $102.1M has been spent since 2025-06-01.** The ledger showed $0 spent then. The newer extract has no record for it, so there is no later spent figure. The City paid the construction contractor (contract 283596) $0 through 2025-06-01 and $72.9M through 2026-05-31, and the newer ledger already shows $79.4M spent on the FTA records of D1209 (which also includes the older FY2016 to FY2024 grants). Some of that spending after June 2025 could be charged to the December 2024 STP money, but no public record says how much. The box is therefore an **upper bound** on unspent money, the same status it had, now with the right reason.
- **The $48,040,000 label.** USASpending does not name the fund of this August 2025 obligation. Calling it CMAQ is our reading. It does not change the conclusion, because the sum in section 4 works whatever it is called.

## What changed in the tree

- The older STP box keeps its amount ($102,140,573, basis `gov_estimate`) and gets a rewritten note that states the evidence above, replacing "may have been re-coded into newer records".
- The piece total ($329,801,213), the "rest of the award" box ($127,618,674) and every sum are unchanged.
- `scripts/state_lake_stp_check.py` is new. `scripts/cdot_build.py` now asserts the four equalities (December 2024 obligation equals the older record, January 2025 swap nets to zero, FY2023 tranches equal the newer record, ledger plus three obligations equals the award within $1) before it writes the note.

## A bonus finding about the "rest of the award" box ($127,618,674)

That box is the award minus the ledger's unspent money. It is almost exactly the two August 2025 obligations that are in no ledger extract, $85,000,000 + $48,040,000 = $133,040,000, less the gap between USASpending outlays (as of the August 2025 pull, $84,819,359) and the ledger's spent figure ($79,398,034), which is $5,421,325: $133,040,000 - $5,421,325 = $127,618,675, one dollar from the box. So the "rest" is mostly new money obligated after the ledger records were made, not a mystery. It still cannot be split further. The timing mismatch (outlays in August 2025, ledger spent in May 2026) means this is an observation, not a rebuilt box, and no box was changed.

## Sources

- City Mid-Year Grants 925 ledger, https://data.cityofchicago.org/resource/iyu8-jkf8 (extracts 2025-06-01 and 2026-05-31), project D1209.
- USASpending award ASST_NON_IL-2016-002_069, https://www.usaspending.gov/award/ASST_NON_IL-2016-002_069 (funding history cached in `raw/cdot/usaspending_IL2016002_funding.json`). Re-checked live on 2026-10-02: total obligation $414,620,572 and 75 account-level lines whose obligations add to $408,620,572 (the page's "transaction obligated amount"), as before.
- CDOT FFY2024-2029 STP Program (updated 2026-02-10), https://cmap.illinois.gov/wp-content/uploads/CDOT_2025-2029-STP-Program-20260210.pdf, p. 1.
- City of Chicago 2025-2029 Capital Improvement Program, project 40492, PDF p. 168 (`data/city_capital_2026.json`).
- City payments dataset s4vu-giwb, contract 283596 (`raw/contracts/payments_*_dedup.csv`).
