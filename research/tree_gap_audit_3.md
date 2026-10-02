# Tree gap audit 3: after the Mid-Year contracts, bond series, special-ed and CDBG-DR rounds (build of 2026-10-02, 16:00)

Snapshot: `raw/treeaudit3/budget_snapshot.db`, a read-only copy of `data/budget.db` right after `bash build/build_all.sh` (it passed: City 15,406 boxes, CPS 24,894, Parks 7,046, 0 bad sums, 0 orphans, 0 boxes without a source, 0 big leaves without a why). "Previous" means the audit 2 snapshot, `raw/treeaudit2/budget_snapshot_audit.db` (built 2026-10-02 10:12), the one `research/tree_gap_audit_2.md` measured. Scripts: `scripts/treeaudit3_*.py` (copies of the audit 2 scripts, pointed at the new snapshot, plus `treeaudit3_names_wide.py` and `treeaudit3_appendix.py`). Nothing in `build/*.py` or `data/splits/*` was changed. Dollars are absolute leaf dollars unless a table says signed.

Two method notes. (1) Every "previous" column below was produced by running the same script on the audit 2 snapshot, so previous and now are like for like. Coverage matches audit 2 exactly. The person-like payee count does not: audit 2 printed 50 rows (27 couples, 22 contract-holding "First Last" worth $5.75M, 1 single), while the kept audit 2 snapshot gives 43 rows (27, 15, 1, $503,892 in all). I did not resolve why the contract-holder rows differ. (2) I refined the (a)/(b)/(c) tag rules in `treeaudit3_rank.py` so that leads that were finished since audit 2 are no longer called "(a) public data unused" (single bond series, IEPA loans, named vendor boxes). Both snapshots were re-tagged with the refined rules.

## Verdict

**Yes, the data is ready for the website, with three cheap fixes first and a clear statement about what the tree does not do.** All three totals still tie to the cent, 0 boxes fail "parent equals sum of children", the City gross check holds ($18,668,568,460), and 0 leaves of $10M or more lack a why sentence. The state of the four things audit 2 asked to fix: the State/Lake $102.1M question is settled (not a double count), same-name siblings are 0 (was 57 groups), the five unexplained negative boxes are explained, and 18 wrong why sentences are down to 1 by audit 2's rules.

**The honest reading of this round is diminishing returns.** Dollars that end in a box of $10M or more fell **City 45.0% to 43.7%, CPS 27.4% to 27.1%, Parks 17.5% to 17.5%**. That is $244M of City dead ends and $28M of CPS removed, out of $18.0B and $11.2B. A day of data rounds (Mid-Year contracts, bond series, CDBG-DR, special-ed, utilities) bought about 1.4 points on the City and nothing on Parks. The strict rule moved even less (City 70.8% to 69.5%). And the dollars that now end under $10M rest a little more on our estimates: City estimate or leftover share 19.0% to 20.7%.

Fix before launch:
1. **Privacy is not at 0 on a wider test.** By the audit 2 test (names check plus the person-like payee heuristic) the count is **0 person-like unhidden payees** (it was 43 rows, $503,892). But a wider sweep finds leftovers that the heuristic misses: about 41 couple-style payees ($68,057, 14 of them cut off like "FIRST LAST &"), about 23 artist-grant payees with one person's name ($178,650, nearly all Cultural Affairs), and 3 couple rows that match City roster surnames ($3,494). Two of the artist payees are now **box names** in the tree (two $6,000 boxes, from the new Mid-Year placement). Section 3 has the counts. Fix in `build/payee.py` (not touched here), then rebuild.
2. **Four wrong why sentences ($98.1M).** The Water and Sewer state loan lines (Water $39.7M and $14.1M, Sewer $32.6M and $11.7M) still say "lent or granted to many homeowners and builders". They are Illinois EPA loan repayments. The detailed side info was added by the IEPA split, but the sentence on the box was not replaced. One more box ($29.7M sewer cleaning) is on the generic fallback.
3. **Midyear placement lines.** Four lines now show payments above the line (-$4.5M), and one single contract ($12.3M Lion Apparel) is 1.56x its whole line, which is direct evidence the 2025 coding does not always carry to 2026. The "Budgeted but not spent yet" sentence on those 98 remainder boxes ($517M) overstates, because payments coded to another line or paid without a contract number would also be in it. Keep the box note on screen with the box.

**What is worth one more data round?** Only one thing is likely to move more than a point: **ask the Department of Finance for the same Mid-Year contracts file cut for 2026 invoices** (it is published for 2025 only, which is why 1,840 contracts and $1,252.8M of 2026 payments could not be placed). That is an ask, not a download (type b). The public sources that are left (type a) hold $434M of City dead ends and $121M of CPS, and about half of that is upper-bound "caps" or a pointer to a box that already exists. A manual read of EMMA by a person could move $176M of bond principal. I would not spend another public-data round. Details in section 5.

## 1. Coverage: where clicking stops (share of dollars)

| Government | Leaves previous | Leaves now | < $1M previous | now | $1M to $10M previous | now | >= $10M previous | **now** | Change |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| City | 11,423 | 11,827 | 41.7% | 42.2% | 13.2% | 14.2% | 45.0% | **43.7%** | -1.4 pts |
| CPS | 20,114 | 20,141 | 57.6% | 57.6% | 15.0% | 15.2% | 27.4% | **27.1%** | -0.2 pts |
| Parks | 6,124 | 6,124 | 48.5% | 48.5% | 33.9% | 33.9% | 17.5% | **17.5%** | 0.0 pts |
| City counted-twice branch | 133 | 133 | 0.6% | 0.6% | 5.6% | 5.6% | 93.7% | 93.7% | none |

Dollars in leaves of $10M or more: City $8,109M to $7,865M, CPS $3,064M to $3,036M, Parks $119M to $119M. Signed dollars (offsets netted): City 42.8% to 41.3%, CPS 21.2% to 20.9%, Parks 13.9% to 13.9%.

**Build rule versus strict rule** (the build rule counts "N people x rate" boxes under $1M as small; the strict rule judges every leaf by its own amount).

| Government | Build rule previous | now | Strict previous | now | Count x rate boxes of $1M or more counted small: previous | now |
|---|---:|---:|---:|---:|---|---|
| City | 45.0% | 43.7% | 70.8% | 69.5% | 494 boxes, $5,832M | 495 boxes, $5,862M (proxy $2,943M, tied $2,670M, gov_estimate $249M) |
| CPS | 27.4% | 27.1% | 43.7% | 43.4% | 951 boxes, $4,097M | 951 boxes, $4,097M |
| Parks | 17.5% | 17.5% | 25.7% | 25.7% | 24 boxes, $106M | 24 boxes, $106M |

**Published number or our estimate?** Of the dollars that end under $10M, how many rest on a published number (budget, tied, gov_estimate, paid_to_date) and how many on our estimate or leftover (proxy, residual, adjustment)?

| Government | Under $10M previous | published | estimate or leftover | Under $10M now | published | estimate or leftover |
|---|---:|---:|---:|---:|---:|---:|
| City | 55.0% | 35.9% | 19.0% | 56.3% | 35.6% | **20.7%** |
| CPS | 72.6% | 55.7% | 16.9% | 72.9% | 55.8% | 17.0% |
| Parks | 82.5% | 72.7% | 9.7% | 82.5% | 72.7% | 9.7% |

In dollars (leaves under $10M by their own amount, $M): City published $4,652M to $4,605M, proxy $395M to $452M, residual $90M to $299M, adjustment $125M to $129M. So the City gained $57M of proxy and $209M of residual below $10M, and lost $47M of published. CPS and Parks are flat.

**By basis** ($M of leaves, absolute; the second number is the part that ends at $10M or more).

| Gov | Basis | Total previous | now | >= $10M previous | now |
|---|---|---:|---:|---:|---:|
| City | budget | 4,472 | 3,570 | 2,911 | 2,228 |
| City | tied | 5,332 | 5,340 | 1,319 | 1,319 |
| City | gov_estimate | 1,301 | 1,310 | 764 | 764 |
| City | proxy | 3,717 | 4,058 | 505 | 759 |
| City | paid_to_date | 930 | 1,160 | 574 | 649 |
| City | residual | 1,730 | 2,048 | 1,640 | 1,749 |
| City | adjustment | 520 | 525 | 396 | 396 |
| CPS | budget | 4,666 | 4,547 | 1,549 | 1,430 |
| CPS | tied | 3,712 | 3,712 | 643 | 643 |
| CPS | proxy | 2,157 | 2,157 | 298 | 298 |
| CPS | paid_to_date | 78 | 193 | 33 | 136 |
| CPS | residual | 105 | 109 | 97 | 85 |
| CPS | adjustment | 465 | 465 | 444 | 444 |
| Parks | all bases | unchanged | unchanged | unchanged | unchanged |

Reading it: City "budget" fell $902M because whole budget lines were split into named vendors (paid_to_date +$230M), a "Budgeted but not spent yet" remainder (residual +$318M net), CDBG-DR equal shares (proxy +$159M net of the old miles proxy) and bond series (proxy +$182M, bonds-not-printed residual -$200M), among other moves. Of the City's $244M drop in dead ends, the churn behind it is larger: 28 boxes ($1,145M) left the list and 26 boxes ($901M) joined it. The Mid-Year lines net -$120.0M ($524M out, $404M in, mostly the "not spent yet" remainders). Bond series net -$94M. The CDBG-DR boxes are the same dollars with new names (only the $29.7M sewer cleaning line left the bucket). CPS: utilities and special-ed providers took $28M out.

**What the split files did** (`treeaudit3_splits.py`; 26 files now, audit 2 counted 15). New or changed since audit 2:

| File | Splits | Show as boxes | Side info only | $M of lines with boxes |
|---|---:|---:|---:|---:|
| city/paid_to_date_midyear.json | 102 | 102 | 0 | 743 (placed $230.1M) |
| city/midyear_2025_vendors.json | 1,127 | 0 | 1,127 | 0 |
| city/bond_series_round3.json | 4 | 4 | 0 | 181 |
| city/bond_series_round4.json | 1 | 1 | 0 | 59 |
| city/drgr_cdbgdr.json | 7 | 4 | 3 | 380 |
| city/iepa_loans.json | 4 | 0 | 4 | 0 |
| cps/utilities.json | 4 | 4 | 0 | 119 |
| cps/sped_isbe.json | 1 | 1 | 0 | 27 |
| city, cps, parks why_fixes.json | 25 | 0 | 25 | 0 |

The build log shows 4 skipped fixes in `city/why_fixes.json`. They were skipped before this audit too (noted in `research/public_leads_3.md`). All other split files apply with 0 skipped.

## 2. Data quality

| Check | Previous | Now | Verdict |
|---|---|---|---|
| Parent equals sum of children | 0 failures, 3 roots equal official totals | 0 failures, 3 roots equal official totals | Pass |
| Reconciliation leftovers of $1M or more | 48 boxes, $1,829M | **109 boxes, $2,135M** (City 102, $2,027M; CPS 6, $106M; Parks 1, $1.1M) | Honest, but read the next paragraph |
| Negative leaves | City 256 (-$580.0M), CPS 19 (-$465.3M), Parks 410 (-$20.2M). 5 of $1M or more had no note or sentence | City 260 (-$584.5M), CPS 19, Parks 410. **0** of $1M or more without a note or sentence | Pass |
| paid_to_date over the line | 10 lines, $176.5M over. 24 lines under the line (budget $823M, paid $516M) | **14 lines, $181.0M over.** 127 lines under (budget $1,703M, paid $848M) | Clear, see Midyear below |
| Proxies as boxes | City 357 ($3,717M), CPS 392 ($2,157M), Parks 7 ($63M) | City **378 ($4,058M)**, CPS 392 ($2,157M), Parks 7 ($63M) | Labelled. City proxy of $10M or more: 12 boxes ($505M) to 20 ($759M) |
| Proxy boxes with no method note | City 12 ($837M), CPS 248 ($635M) | City 11 ($615M), CPS 248 ($635M) | CPS ones are job-title FTE splits with an fte count in `extra`, no note text |
| Duplicated dollars | None proven, 3 risks | None found, State/Lake settled | Pass, see below |
| Stale or wrong why sentences (audit 2's rules) | 18 boxes, $538M | **1 box, $29.7M** | Pass, but I found 4 more by hand, below |
| Leaves of $10M or more without a why | 2 ($167M) | 0 | Pass |
| Individuals' names | 43 payee rows person-like and shown | 0 by the audit 2 test, but a wider sweep finds leftovers | **Fix**, section 3 |

**Why leftovers rose from 48 to 109.** The main cause is that 102 budget lines now show named vendors plus a "Budgeted but not spent yet" box, and that remainder is counted as residual: 75 City boxes of $1M or more, $710M (previous 17, $208M). That is the same dollars as before, now split into what was paid (named) and what was not. Others: grant reserve beyond named projects 16 boxes $585M (unchanged), federal airport carryover 3 boxes $412.5M (unchanged), police overtime beyond CPD targets $124.6M (unchanged), **bonds not printed one by one 7 boxes, $195.5M (previous 7, $395.3M)**, CPS not spent or unmatched 5 boxes $100.0M (previous 2, $96.6M). The four Parks boxes that print a total differing from the box by $79.6M (the managed-venues move) are unchanged.

**Midyear contract boxes (the new 2025-coding risk).** `paid_to_date_midyear.json` placed $230,055,800.08 of 2026 payments (380 vendor and contract leaves, 102 lines, 381 contracts) by how the City coded the same contract's 2025 invoices. The backtest in `research/midyear_contracts.md` says 95.5% of dollars stay on a line within 2025 and 90.1% from one budget year to the next, so about 5% to 10% of the placed dollars, **$10M to $23M**, may sit on the wrong line. What the tree shows:

| How much of its line the Mid-Year boxes cover | Lines | Placed $ |
|---|---:|---:|
| Under 25% | 49 | $36.0M |
| 25% to 50% | 26 | $107.1M |
| 50% to 90% | 21 | $58.4M |
| 90% or more | 6 | $28.4M |

By size of box: 5 boxes of $10M or more ($75.8M), 36 of $1M to $10M ($99.2M), 339 under $1M ($55.0M). Four lines have payments above the line and carry a negative "already spent more than the budget" box, -$4.51M in all: public-safety Professional and Technical Services (-$4.44M, one Fire contract, 283026, bunker gear, $12.3M on a $7.86M line), Accounting and Auditing (-$0.06M), Earned Income Tax Credit (-$0.01M), Stationery (-$0.002M). A contract that is 1.56x its whole line is the clearest sign of a coding mismatch. 49 contracts ($82.5M) that the older rule-based file placed disagree with the 2025 coding (three of them are $74.6M: O'Hare contracts 25743 and 27075 and Streets contract 151329). They were not moved, as `research/midyear_contracts.md` says. About 278 contracts ($138.1M) agree.

**Duplicate dollars.**

| Check | Result |
|---|---|
| Midyear versus rule-based paid_to_date | **No overlap.** 0 contracts appear in both files' leaves. 0 lines hold boxes from both. One vendor name is in both (A Safe Haven Foundation, $3.17M rule-based, $1.76M Mid-Year, different contracts and lines) |
| Same contract in two boxes inside one file | 3 contracts (2 in the rule file, 1 in the Mid-Year file), all the same organization under two spellings on one line, payment counts differ, $0.12M in all. Not copies |
| Same vendor name and amount twice, or same amount on two named boxes of $1M or more | 0 |
| Bond series versus older bond splits | **No series twice on one ordinance line.** Checked by series label, principal versus interest, within each line. One label overlap: "2010B" appears as the GO MSAC 2010B boxes ($442,387 interest, $6.24M principal) and the GO Taxable Project 2010B term bond ($16.05M interest, $213.6M balance). They are two different bonds (the MSAC balance is the $8.48M one in `research/bond_series.md` section 6), but the shared label will confuse a reader. O'Hare 2010B ($20.9M, older `aviation.json`) and the six series from `bond_series_round4.json` do not overlap. Each series box plus its leftover equals its line to the cent (the build checks it) |
| Ledger code and fund on more than one box | 2 pairs, same as audit 2 (CARES20DB/F033C, B3695/F0L98), different ledger budgets |
| Award and contract ids on more than one box | 0 |
| CPS project number repeated | 1 ("Space To Grow", two funding sources) |
| **State/Lake STP $102.1M next to $18.2M** | **Settled, no double count** (`research/state_lake_stp.md`: the older record is a separate December 2024 FTA obligation, never reversed, and the newer ledger plus three obligations it leaves out equals the award to $1). The note on the box now says so |
| Same project on several lines | **Fixed.** 31 projects, 75 boxes now carry "also on other lines, do not add them up" (previous 0) |
| CPS paid_to_date (utilities, special-ed providers) | 50 boxes, $193.4M. No repeated names. Payments are by vendor, not line, so a vendor total can include other contracts (stated in the notes) |

**Wrong or generic why sentences, previous rules and a hand check.** Audit 2's flag rules find 1 box now ($29.7M "2,100 blocks of sewer cleaning", generic fallback). Previous: 13 City boxes on the generic fallback ($237.1M), 4 CPS "a few large companies" boxes ($176.1M, two of them the preschool lines), Emergency Medical Transportation ($124.7M). All fixed. By hand I also found: the four Water and Sewer IEPA loan boxes ($98.1M) with a wrong "homeowners and builders" sentence (same text is correct on the 5 Housing loan boxes). Not verified, only noted: six CPS leaves of $78.4M (school safety, assessments, phone, classroom supplies, two Public Building Commission lines) use "a few large companies". Parents that now have children but still carry a leaf-style sentence: City 24 ($4,317M, previous 19, $4,077M), CPS 21 ($1,362M, previous 16, $1,216M), Parks 2 ($76.2M). Harmless if the site shows why only on leaves.

**Negative boxes, explained.** City: 212 vacancy-savings boxes (-$220.3M), 14 "paid beyond the line" boxes (-$181.0M, largest police settlements -$151.7M), OBM adjustment (-$117.0M), "Less Corporate Fund Savings" (-$56.6M). CPS: budget-only offsets (-$265.1M, 9 boxes; previous 6, -$244.5M) and the vacancy factor (-$200.0M). Parks vacancy allowance (-$15.2M). All have a note or sentence.

## 3. Privacy: individuals' names

| Check | Previous | Now |
|---|---:|---:|
| Vendor rows in side info | 16,819 | 16,819 |
| Hidden as "Individual (name hidden)" | 9,852 | 10,000 |
| **Person-like and shown, audit 2 test (`treeaudit3_names.py`)** | **43 rows** (27 couples $47,792, 15 contract-holder "First Last" $454,100, 1 single $2,000) | **0** |
| Two-word matches against 156,148 roster name patterns | 108 distinct, 127 places | 86 distinct, 106 places |
| of which vendor side info | 8 rows | 30 vendor items, 27 with a business word (JP Morgan Chase, law firms), **3 couples** ($3,494, roster surnames) |
| Wider sweep, couples ("A & B Surname", no contract number, law firms and trade names excluded by hand) | 113 payee strings, $195,910 | **41 payee strings, $68,057** (14 cut off after the "&", $25,434) |
| Wider sweep, one person's name on an artist grant, residency or exhibition contract | 70 payee strings, $483,184 | **23 payee strings, $178,650** (a hand review of two-to-three word payees with no business word finds 30 names in 34 rows, $283,700, 30 of the 34 rows with a contract number) |
| Person names used as **box names** in the tree | not checked | **2** ($6,000 each, Mid-Year artist grant boxes). No other node, side info label or why sentence carries a roster name that is a person |

The payee fix made after audit 2 (`83470a8`, couples and person-named contract holders) did its job: the wider sweep is down from 183 payee strings to 64. What is left is what its word lists cannot see: couples whose first names are not common roster names or whose name is cut off at the "&", and artist grants to people whose first name is not on the City roster. **So by the stated bar ("0 person-like unhidden payees"), the audit 2 test passes and the wider test does not.** Counts only here, names are in `raw/treeaudit3/names_wide_private.txt` (gitignored, not in this file). Suggested fix in `build/payee.py`: treat a name ending in "&" or starting with a first name and joined by "&" or "AND" as a couple even without roster first names, and hide any payee whose contract description says artist grant, residency or exhibition. The name scan in the build (0 possible hits against 46,408 roster names) did not fire, which is why this was not caught by the build.

## 4. Structure for a 13-year-old

| Check | Previous | Now | Note |
|---|---:|---:|---|
| Boxes with exactly one child | 525 (City 78, CPS 126, Parks 248, memo 73) | **580** (City 133, CPS 126, Parks 248, memo 73) | All have the same amount as the child. The 55 new ones are City vendor groups with one vendor (58, up from 5), a side effect of Mid-Year placement. Of one-child boxes, $10M or more: 24 to 26 |
| Boxes with more than 200 children | 0 | 0 | 17 boxes have 51 to 200, same ones (O'Hare organization unit 175, CPS charter schools 121, CPS Facility Needs 86, City "Other vendors (82)" 82) |
| Depth to a leaf | City median 8, max 9. CPS median 6, max 7. Parks median 5, max 6 | City median 8, max 9. CPS median 6, **max 8**. Parks median 5, max 6 | 51% of City leaves at depth 8 or 9 (previous 53%). 24 CPS leaves at depth 8. Dollar-weighted median: City 5, CPS 6, Parks 4 |
| Same parent, same name | 57 groups, 145 boxes, $946M | **0** | Fixed (fund or program label added). 76 City names now carry "(paid from: ...)" |
| Parent and child with the same name | 26 ($997M) | 7 ($277M) | Down. Left: Bureau of Counter-Terrorism, Detectives, Constitutional Policing, CPS tuition remainder |
| City boxes of $1M or more with a federal program code in the name | 153 ($2.95B) | 153 ($2.95B) | Unchanged. 25 "Reserve Balance (agency - program (14.239))" boxes of $10M or more ($1,746M), unchanged. All 105 City ordinance-line dead ends are named by the account only |
| CPS leaves of $1M or more with a fund code in the name | 0 | **7 ($251M)** | New. It looks like the sibling-name fix, which added "fund FG324-041008" to seven contingency names |
| Pay-rate leaves with "(grade D 01)" | 3,893 | 3,893 | Unchanged |
| "Other vendors (n)" groups | 26 | **112** | 86 new from Mid-Year. Each is under $1M per vendor (0 hold a vendor of $1M or more) |
| Names over 100 characters | 438 | 465 | Slightly worse |
| Most repeated name | "Other job titles (fewer than 5 positions each)" 1,137x, $968M | same | Privacy pooling. The name needs the unit |
| Rounding boxes and tiny leaves of $10 or less | 278 and 442 | 280 and 443 | Unchanged |

Nothing here blocks the site. The one-child boxes and long names are display decisions (collapse a box with one child into its parent).

## 5. Ranked remaining dead ends

Dead ends of $10M or more (a leaf, not an N x rate box under $1M): City **237 boxes, $7,865M** (previous 239, $8,109M), CPS **91 boxes, $3,036M** (91, $3,064M), Parks 6 boxes, $119M. Tags: (a) public data unused, (b) needs FOIA or the budget office, (c) truly one item. Rules are regexes in `treeaudit3_rank.py` (refined as the method note says), and 13 boxes ($174M) fall to the default (b). Previous columns use the same rules on the audit 2 snapshot, so they differ from the table printed in audit 2.

| Government | (a) previous | (a) now | (b) previous | (b) now | (c) previous | (c) now |
|---|---:|---:|---:|---:|---:|---:|
| City | 19 boxes, $653M (8.1%) | **15 boxes, $434M (5.5%)** | 99 boxes, $4,058M (50.1%) | 79 boxes, $3,505M (44.6%) | 121 boxes, $3,397M (41.9%) | 143 boxes, $3,926M (49.9%) |
| CPS | 6 boxes, $240M (7.8%) | **2 boxes, $121M (4.0%)** | 31 boxes, $846M (27.6%) | 31 boxes, $835M (27.5%) | 54 boxes, $1,977M (64.5%) | 58 boxes, $2,081M (68.5%) |
| Parks | 0 | 0 | 4 boxes, $84M (71.0%) | 4 boxes, $84M (71.0%) | 2 boxes, $35M (29.0%) | 2 boxes, $35M (29.0%) |

The (c) growth in the City is mostly **"Budgeted but not spent yet"** (17 boxes, $489M, previous 6, $161M), vendor boxes (paid so far, $649M, previous $573M) and bond series (now one box per series). Money not spent yet is not a dead end for good: it is one number because no payment exists. Revisit it when more of 2026 is paid.

### What is left that is public (type a), honestly

| # | Item | Boxes, $ | What I found | Worth a round? |
|---:|---|---:|---|---|
| 1 | Grant reserve lines with project lists in the City ledger (HOME $39.3M and $29.0M, CDC $22.2M and $11.6M, UASI four lines, COPS $15.6M, DCEO senior center $16.0M, SOS $10.1M) | 10, $195M | `data/city_grants_2026.json` `reserve_attribution` holds named projects for most (held, not attached). They are **upper-bound caps** from a 2026-05-31 ledger snapshot, not splits (`research/grants_capital.md`) | Maybe. Could show named projects as side info. Would not give exact boxes |
| 2 | Bond series principal and the GO interest left over: GO principal $108.4M, O'Hare older principal $46.7M, GO interest $20.8M | 3, $176M (previous 7, $395M) | EMMA rounds 3 and 4 moved about $200M into named series (`research/emma_bonds.md`), mostly derived (balance x coupon, labelled proxy). The rest needs per-series principal schedules after the 2025 tender and 2026 refunding. The EMMA terms bar automated access, so only a person reading pages by hand is allowed | Only as manual work. It would name series, but most are $10M to $60M, so little would drop under $10M |
| 3 | Sewer Fund "For Capital Construction" | 1, $52.4M | The City capital plan (held, 81 Sewer System and 256 Water System projects) is mostly bond, WIFIA and IEPA funded, and `research/grants_capital.md` says the plan cannot be reconciled to ordinance lines | No. Weak lead |
| 4 | CPS Preschool for All ($88.1M, $32.9M) | 2, $121M | Pointer to the City's Early Childhood delegate agency boxes. Not new dollars. The sentences are fixed | No (fix wording only, done) |

### Needs FOIA or the budget office (type b)

| # | Item | Ask | Boxes | $ (previous) |
|---:|---|---|---:|---|
| 1 | Ordinary contract and supply lines (O'Hare and Midway services, IT maintenance, rent, repair parts, loans and grants to agencies) | **Department of Finance: the Mid-Year contracts file cut for 2026 invoices** (same table as the public 2025 file). Also OBM Data Directory. What is unplaced: 1,840 contracts first paid in 2026 ($1,252.8M), contracts spread over several lines ($520.3M), under 95% on one line ($1,906.5M), direct vouchers with no contract ($699.1M) | 32 | $770M ($1,279M) |
| 2 | Highway and state reserves larger than any project list (federal $218.1M, Rebuild Illinois $57.3M, state $37.1M, other $40.9M, FTA $32.9M, HOME $32.8M) | CDOT or OBM: reserve by project | 6 | $419M (same) |
| 3 | Federal airport carryover tied to no award (O'Hare $282.2M, Midway $99.8M, Midway not yet awarded $30.5M) | Aviation or OBM: FAA grant ledger by award | 3 | $413M (same) |
| 4 | CPS contingencies (Grant Expansion $120.0M, $50.4M, $35.3M, $25.0M, Special Income Fund 124 $50.0M and $30.0M, and more) | CPS Budget Office: planned use | 12 | $406M (same) |
| 5 | CDBG-DR sewer, alleys, tanks (104 blocks $221.3M, 60 alleys $67.1M, 12 tanks $62.1M, planning $19.6M) | **Wait.** HUD DRGR (checked) has no activity list and its Q2 2026 report puts $390.3M under one activity. Re-check after the next quarterly report | 4 | $370M (was a miles x $8.5M proxy, now the City's own counts) |
| 6 | State/Lake station (rest of the federal award $127.6M, STP $102.1M, CMAQ $59.5M, STP $18.2M, CRP $15.0M) | CDOT, or FTA TrAMS line items for IL-2016-002 | 5 | $322M (same) |
| 7 | Union contract money (Scheduled Wage Adjustments $262.3M and three more) | OBM: contract settlement schedule | 4 | $321M (same) |
| 8 | City claims and benefits totals (workers' compensation $44.8M, Medicare $38.2M, loss in collection $32.5M, injured on duty $25.0M and more) | Finance and Risk Management: totals by type | 10 | $238M ($253M) |
| 9 | Water and Sewer state loans (Water $39.7M and $14.1M, Sewer $32.6M and $11.7M) | Water and Finance: loan repayment schedules (loan tables are attached, no public paper prints each loan's 2026 payment) | 4 | $98M (was tagged public) |
| 10 | One item each: Emergency Medical Transportation $124.7M (Finance ledger, account 9222), police overtime beyond CPD targets $124.6M (CPD or OBM), OBM adjustment that no line explains -$117.0M (OBM), CPS health set-aside $153.9M (Benefits claims), CPS meals $102.3M (CPS meals payments by meal type), Parks Soldier Field, harbors, utilities $84.4M | as listed | 12 | $707M (same) |

### Top 10 remaining items, one line each (by dollars, with tag)

1. **$770M, (b):** 32 ordinary contract and supply lines. Ask the Department of Finance for the 2026 cut of the Mid-Year contracts file. The only item with real upside. How much would fall under $10M is unknown until the file is read, since many named vendors are themselves over $10M.
2. $419M, (b): highway and state reserves with no project (CDOT or OBM).
3. $413M, (b): federal airport carryover with no award (Aviation or OBM).
4. $406M, (b): CPS contingencies (CPS Budget Office).
5. $370M, (b): CDBG-DR boxes. Nothing to fetch until the next HUD quarterly report.
6. $322M, (b): State/Lake station (CDOT or FTA).
7. $321M, (b): union contract money (OBM).
8. $238M, (b): City claims and benefits (Finance and Risk Management).
9. $195M, (a): grant reserve lines. Named projects as upper-bound side info from the held ledger. Not exact.
10. $176M, (a): bond principal and GO interest. Only by a person reading EMMA by hand.

Not dollars but cheaper than any of the above, and what I would do first: hide the leftover couple and artist-grant payees (and the two person-named boxes), replace the four IEPA why sentences and the sewer cleaning sentence, and add "2010B (MSAC)" to the two GO 2010B names so they cannot be confused.

## Appendix: top 30 dead ends per government, tagged, with previous rank

Source: `raw/treeaudit3/rank.json` and `raw/treeaudit3/prev/rank.json` through `treeaudit3_appendix.py`. "Prev #" is the same box's rank on the audit 2 snapshot, "new" means the box did not exist as a dead end then. Full lists are in `rank.json` (City 237, CPS 91, Parks 6). The box path is shortened.

**City of Chicago** (237 dead ends of $10M or more, $7,865M)

| # | Prev # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---:|---|---|:-:|---|
| 1 | 1 | 282.2 | Carryover not tied to a named FAA award > Still not tied to any FAA award, ... | residu | b | federal airport carryover no public record ties to a project |
| 2 | 2 | 262.3 | City's main fund (Corporate Fund) > Scheduled Wage Adjustments | budget | b | set aside for union contracts not yet settled, and the 2026 line is 9.3x last year's matching pay, so no public split fits |
| 3 | new | 221.3 | Construction > 104 blocks of new local sewer main (equal share of each block) | proxy | b | disaster recovery money split by the City's own unit counts, but the streets, alleys and tanks are not chosen yet |
| 4 | 4 | 218.1 | Construction > Federal highway money with no project in the regional plan f... | residu | b | reserve larger than any public project list |
| 5 | 5 | 161.2 | Extra payment above what the law requires > Two extra payments into the fun... | tied | c | one extra payment into a pension fund |
| 6 | 6 | -151.7 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses an... | adjust | c | payments so far are larger than the budget line, shown as a negative box |
| 7 | 7 | 127.6 | State/Lake Loop Elevated Station (one named project) > Rest of the federal ... | residu | b | one federal award, station cost breakdown not published |
| 8 | 8 | 124.7 | City's main fund (Corporate Fund) > Emergency Medical Transportation | budget | b | use of line unconfirmed |
| 9 | 9 | 124.6 | Overtime > Rest of police overtime: other units, events and projects, and m... | residu | b | CPD publishes targets for part of its overtime, not the rest |
| 10 | 10 | -117.0 | Adjustment the budget office makes that no line explains | adjust | b | OBM deduction no line explains |
| 11 | 12 | 108.4 | For Payment of Bonds > Other bonds (not printed one by one) | residu | a | bond series share not printed in the statements we hold |
| 12 | 13 | 102.1 | State/Lake Loop Elevated Station (one named project) > Surface Transportati... | gov_es | b | one federal award, station cost breakdown not published |
| 13 | 14 | 99.8 | Reserve Balance > Carryover not tied to a named FAA award | residu | b | federal airport carryover no public record ties to a project |
| 14 | 15 | -98.0 | Salaries and Wages - on Payroll > Budgeted turnover (vacancy savings), Corp... | adjust | c | planned saving that offsets pay lines |
| 15 | 17 | 91.8 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses an... | paid_t | c | settlement payments, each a separate court deal (cases involve private people) |
| 16 | 18 | 90.5 | Paying back loans > For Payment of Bonds | budget | c | one bond series, interest or principal |
| 17 | 19 | 90.0 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses an... | paid_t | c | settlement payments, each a separate court deal (cases involve private people) |
| 18 | 20 | 86.2 | 01-24-0017: Calumet River Bridges > Construction, State Match - Chicago | proxy | c | one named project or one federal award |
| 19 | 21 | 72.2 | Extra payment above what the law requires > Advance payment: City pays more... | tied | c | one extra payment into a pension fund |
| 20 | new | 67.1 | Construction > 60 permeable alleys (equal share of each) | proxy | b | disaster recovery money split by the City's own unit counts, but the streets, alleys and tanks are not chosen yet |
| 21 | 23 | 65.6 | Programs and other costs > Rehabilitation Loans and Grants (paid from: Neig... | budget | b | money passed to many agencies or people, contract-to-line link is not public |
| 22 | 24 | 64.8 | City's main fund (Corporate Fund) > For Professional Services for Informati... | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 23 | 25 | 62.8 | Other citywide costs > For Distribution of the Net Proceeds of the Real Pro... | budget | c | pass-through to the CTA |
| 24 | new | 62.1 | Construction > 12 wing storage tanks (equal share of each) | proxy | b | disaster recovery money split by the City's own unit counts, but the streets, alleys and tanks are not chosen yet |
| 25 | 28 | 59.5 | State/Lake Loop Elevated Station (one named project) > Congestion Mitigatio... | gov_es | b | one federal award, station cost breakdown not published |
| 26 | new | 59.2 | Operation, Repair or Maintenance of Facilities (Chicago-O'Hare Internationa... | residu | c | money not spent yet, so no payment exists |
| 27 | new | 59.1 | Professional services > Budgeted but not spent yet | residu | c | money not spent yet, so no payment exists |
| 28 | 29 | 58.9 | Local Public and Private Grant Fund > Professional services (SISTER AGENCY ... | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 29 | 31 | 57.3 | Reserve Balance > Rebuild Illinois money with no project in the City's gran... | residu | b | reserve larger than any public project list |
| 30 | 32 | 56.8 | For Interest on Bonds > O'Hare 2022A | tied | c | one bond series, interest or principal |

**Chicago Public Schools** (91 dead ends of $10M or more, $3,036M)

| # | Prev # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---:|---|---|:-:|---|
| 1 | 1 | 254.2 | Bond series 2009G > Series 2009G: final repayment of the loan (principal) | tied | c | one bond series (or one payment of it) |
| 2 | 2 | -143.3 | Teacher pay set-aside (budget only) > Planned savings from jobs left unfill... | adjust | c | planned offset or reserve counted elsewhere |
| 3 | 3 | 120.0 | Money held back for later (contingency) > Contingency For Project Expansion... | budget | b | money held back, no document itemises it |
| 4 | 4 | 116.8 | Health insurance set-aside (budget only) (All Other) > Medical plan share (... | proxy | b | reserve for bills that have not arrived |
| 5 | 5 | -100.0 | Money held back for later (contingency) > Other General Charges (General Ed... | adjust | c | planned offset or reserve counted elsewhere |
| 6 | 6 | 88.1 | Professional and administrative services > Payment To Other Govt Units (Sta... | budget | a | passes through the City (DFSS) to community providers, providers are in the City tree |
| 7 | 7 | 80.0 | Facility Needs > Emergency/Unanticipated Facility Repairs | budget | c | capital money not assigned to a project yet |
| 8 | 8 | 70.0 | IT - Centralized (DC, CO etc., District Priority) > IT money budgeted but n... | residu | c | capital money not assigned to a project yet |
| 9 | 9 | 61.3 | Pension reserve in the general fund (a reservation, not a payment) > CPS op... | proxy | c | one reserve or levy paid as one amount |
| 10 | 10 | 59.3 | Pension reserve in the general fund (a reservation, not a payment) > State'... | proxy | c | one reserve or levy paid as one amount |
| 11 | 11 | 57.0 | Food > NSS - Lunch Program (Lunchroom Fund) | budget | b | one food contract paid across several food lines |
| 12 | 12 | -56.7 | Staff pay set-aside (budget only) > Planned savings from jobs left unfilled... | adjust | c | planned offset or reserve counted elsewhere |
| 13 | 13 | -52.9 | Money held back for later (contingency) > Other Instr Purposes Misc (Genera... | adjust | c | planned offset or reserve counted elsewhere |
| 14 | 14 | 50.8 | Paying back loans > Bond series 2016A | budget | c | one bond series (or one payment of it) |
| 15 | 15 | 50.4 | Money held back for later (contingency) > Contingency For Project Expansion... | budget | b | money held back, no document itemises it |
| 16 | 16 | 50.0 | Money held back for later (contingency) > Special Income Fund 124 Contingen... | budget | b | money held back, no document itemises it |
| 17 | 17 | 48.8 | Bond series 2018C > Series 2018C: principal repaid (the loan itself) | tied | c | one bond series (or one payment of it) |
| 18 | 18 | 44.5 | Salaries > Staff pay set-aside (budget only) | budget | c | planned offset or reserve counted elsewhere |
| 19 | 19 | 44.4 | Tuition paid to charter schools > Charter/Contract Per Pupil Revenue K-12 T... | budget | c | one charter campus, one payment set by student count |
| 20 | 20 | 44.4 | Bond series 1998B-1 > Series 1998B-1: interest that built up since 1998 (ac... | tied | c | one bond series (or one payment of it) |
| 21 | 22 | 43.5 | Paying back loans > Bond series CIT 2016 | budget | c | one bond series (or one payment of it) |
| 22 | new | 37.4 | Electricity > Constellation NewEnergy (electricity supplier): paid in FY2026 | paid_t | c | one supplier's or provider's payments so far |
| 23 | 24 | 37.1 | Health insurance set-aside (budget only) (All Other) > Prescription plan sh... | proxy | b | reserve for bills that have not arrived |
| 24 | new | 35.9 | Electricity delivery > Commonwealth Edison, called ComEd (electricity deliv... | paid_t | c | one supplier's or provider's payments so far |
| 25 | 25 | 35.3 | Money held back for later (contingency) > Contingency Balancing Program (Co... | budget | c | planned offset or reserve counted elsewhere |
| 26 | 26 | 35.0 | Other charges > Labor And Employee Rels (General Education Fund) | budget | b | money held back, no document itemises it |
| 27 | 27 | -34.6 | Workers' compensation, unemployment and claims > Workers' compensation set-... | adjust | c | planned offset or reserve counted elsewhere |
| 28 | 28 | 34.5 | Bond series 2018A > Series 2018A: principal repaid (the loan itself) | tied | c | one bond series (or one payment of it) |
| 29 | 29 | 33.6 | Food > NSS - Breakfast Program (Lunchroom Fund) | budget | b | one food contract paid across several food lines |
| 30 | 30 | 32.9 | Professional and administrative services > PreK Instruction (State Preschoo... | budget | a | passes through the City (DFSS) to community providers, providers are in the City tree |

**Chicago Park District** (6 dead ends of $10M or more, $119M)

| # | Prev # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---:|---|---|:-:|---|
| 1 | 1 | 36.3 | Soldier Field, harbors, golf and other managed venues > Soldier Field | budget | b | run by a contractor, no operating budget published |
| 2 | 2 | 19.4 | Series 2023C: refinancing loan > Paying back the loan itself (principal) | tied | c | one bond payment |
| 3 | 3 | 16.7 | Contracts, utilities and services > Water and sewer bills | budget | b | per-park usage not published |
| 4 | 4 | 16.6 | Soldier Field, harbors, golf and other managed venues > Boat harbors | budget | b | run by a contractor, no operating budget published |
| 5 | 5 | -15.2 | Pay, benefits and savings reserves > Savings from jobs left unfilled (vacan... | adjust | c | planned offset |
| 6 | 6 | 14.8 | Contracts, utilities and services > Electric bills | budget | b | per-park usage not published |
