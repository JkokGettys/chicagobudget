# Tree gap audit 2: the follow-up (built tree, 2026-10-02 build)

Snapshot: `raw/treeaudit2/budget_snapshot.db`, a read-only copy of `data/budget.db` (build of 2026-10-02 13:53 UTC). "Previous" means the 2026-10-01 snapshot in `research/tree_gap_audit.md`. Scripts: `scripts/treeaudit2_*.py` (coverage, strict, deadends, rank, quality, names, structure, splits). Nothing in `build/*.py` or `data/splits/*` was changed. Dollars are absolute leaf dollars unless a table says signed.

## Verdict

**Yes, the data is detailed and robust enough to build the site, if the site does not claim that every dollar reaches a small box.** All three totals tie to the cent, 0 boxes fail "parent equals sum of children", and the City gross check (City + counted-twice branch + OBM adjustment = $18,668,568,460) holds. Dollars that end in a box of $10M or more fell to **City 45.0%, CPS 27.4%, Parks 17.5%** (previous 64.5%, 38.6%, 25.9%). But about three quarters of the City gain (19.5 points on the build rule, only 5.3 on the strict rule) comes from "N people x rate" boxes, many of them our estimates (pension retirees, health enrollment), so read the strict and published-versus-estimate tables too. Fix before launch: 27 payee rows that look like private people are not hidden, 18 why sentences are wrong or generic ($538M), and 57 groups of sibling boxes now share one name.

## 1. Coverage: where clicking stops (share of dollars)

| Government | Leaves | Total | < $1M | $1M to $10M | >= $10M now | >= $10M previous | Change |
|---|---:|---:|---:|---:|---:|---:|---:|
| City | 11,423 | $18,003M | 41.7% | 13.2% | **45.0%** | 64.5% | -19.5 pts |
| CPS | 20,114 | $11,184M | 57.6% | 15.0% | **27.4%** | 38.6% | -11.2 pts |
| Parks | 6,124 | $678M | 48.5% | 33.9% | **17.5%** | 25.9% | -8.4 pts |
| City counted-twice branch | 133 | $1,709M | 0.6% | 5.6% | 93.7% | 93.7% | none |

Signed dollars (offsets netted): City 42.8%, CPS 21.2%, Parks 13.9% at $10M or more.

**How much of the gain is real splitting?** The build rule counts a leaf with a count and a unit under $1M ("8,275 enrolled employees x $16,530") as small. The strict rule judges every leaf by its own amount.

| Government | Build rule previous | now | Strict previous | now | Count x rate boxes of $1M or more counted small (now) |
|---|---:|---:|---:|---:|---|
| City | 64.5% | 45.0% | 76.1% | 70.8% | 494 boxes, $5,832M (proxy $2,913M, tied $2,670M, gov_estimate $249M) |
| CPS | 38.6% | 27.4% | 44.4% | 43.7% | 951 boxes, $4,097M (proxy $1,664M, tied $1,616M, budget $817M) |
| Parks | 25.9% | 17.5% | 27.5% | 25.7% | 24 boxes, $106M |

Of the dollars that now end under $10M, how many rest on a published number (budget, tied, gov_estimate, paid_to_date) and how many on our estimate or a leftover (proxy, residual, adjustment)?

| Government | Under $10M previous | published | estimate or leftover | Under $10M now | published | estimate or leftover |
|---|---:|---:|---:|---:|---:|---:|
| City | 35.5% | 32.1% | 3.3% | 55.0% | 35.9% | **19.0%** |
| CPS | 61.4% | 51.6% | 9.8% | 72.6% | 55.7% | 16.9% |
| Parks | 74.1% | 72.3% | 1.8% | 82.5% | 72.7% | 9.7% |

By basis ($M of leaves, abs; the second number is the part that ends at $10M or more):

| Gov | Basis | Total now | >= $10M now | Total previous | >= $10M previous |
|---|---|---:|---:|---:|---:|
| City | budget | 4,472 | 2,911 | 7,832 | 6,120 |
| City | tied | 5,332 | 1,319 | 5,800 | 1,787 |
| City | gov_estimate | 1,301 | 764 | 0 | 0 |
| City | proxy | 3,717 | 505 | 3,261 | 2,767 |
| City | paid_to_date | 930 | 574 | 0 | 0 |
| City | residual | 1,730 | 1,640 | 492 | 492 |
| City | adjustment | 520 | 396 | 424 | 327 |
| CPS | budget | 4,666 | 1,549 | 5,828 | 3,075 |
| CPS | tied | 3,712 | 643 | 3,048 | 28 |
| CPS | proxy | 2,157 | 298 | 1,834 | 773 |
| CPS | paid_to_date | 78 | 33 | 0 | 0 |
| CPS | residual | 105 | 97 | 9 | 0 |
| CPS | adjustment | 465 | 444 | 465 | 444 |
| Parks | budget | 506 | 84 | 557 | 107 |
| Parks | tied | 91 | 19 | 40 | 0 |
| Parks | proxy | 63 | 0 | 9 | 0 |
| Parks | residual | 3 | 0 | 57 | 54 |
| Parks | adjustment | 15 | 15 | 15 | 15 |

What the 15 split files did (`treeaudit2_splits.py`): City pensions (12 splits, $2,843M of lines), CDOT (51 splits, 27 show boxes on $1,452M of lines, 24 are side facts), paid-to-date (26 splits, $709M of lines), pay estimates (13 of 14 show boxes, $608M), aviation (5 of 7), health (16 of 16, $138M), CPS bonds (11 of 33 show boxes, 22 are side facts), CPS reserves (1 of 10), Parks (11 of 31), `aviation_contracts.json` (12 of 12 side only, no boxes). The previous audit's two negative "Difference" boxes (Midway -$64.1M, Sewer -$19.4M) are gone.

## 2. Data quality of the new splits

| Check | Result | Verdict |
|---|---|---|
| Parent equals sum of children | 0 failures, 3 roots equal official totals | Pass |
| Reconciliation gaps over $1M | See table below. 48 leftover boxes of $1M or more, $1,829M abs (previous 14, $637M). The rise is honest: splits now show "not itemised" instead of hiding it inside whole boxes | Pass, but the leftovers are the dead-end list |
| Negative boxes | City 256 (-$580M), CPS 23 (-$706M), Parks 411 (-$25M, mostly rounding). 62 are $1M or larger, 5 of those have no note or sentence (City ARPA -$3.1M, Parks health -$1.2M, CPS -$8.0M, -$7.5M, -$5.2M) | Mostly clear, 5 small ones to fix |
| paid_to_date over the line | 10 lines, $176.5M over, each with a negative box and a note. 24 lines are under the line ($516M paid of $823M) | Clear, but see caution |
| Proxies as boxes | City 357 boxes $3,717M, CPS 392 $2,157M, Parks 7 $63M. All carry a method note except 12 City boxes ($837M, they have a why sentence) | Label is clear. The dollar size is the issue (section 1) |
| Duplicated dollars across split files | None proven. Three real risks, below | Watch |
| Stale or wrong why sentences | 18 boxes, $538M (previous audit: 90 boxes, $3.9B) | Fix |
| Names of individuals | None in box names. 27 payee rows not hidden, see below | Fix |

Reconciliation leftovers of $1M or more (boxes, $M abs): City grant reserve beyond named projects 16, $584.9M. Federal airport carryover 3, $412.5M. Bonds not printed one by one 7, $395.3M. Money not spent or not matched to a payment yet 17, $208.1M. Police overtime beyond CPD targets 1, $124.6M. CPS money not spent or unmatched 2, $96.6M, other 1, $6.3M. Parks bonds 1, $1.1M. Four Parks boxes print a total that differs from the box by $79.6M in all (Maggie Daley $4.4M, McFetridge $3.2M, Gately $1.6M, Revenue 9310 $70.4M, which carries the Soldier Field and harbor lines). That equals the managed-venues branch ($79,556,554), moved out on purpose and stated in each box note.

**Negative boxes, explained.** City: 212 vacancy-savings boxes (-$220.3M), 10 "paid beyond the line" boxes (-$176.5M, the largest is police settlements, -$151.7M, where payments so far are $234.3M against an $82.6M line), the OBM adjustment no line explains (-$117.0M, has a sentence now), "Less Corporate Fund Savings" (-$56.6M). CPS: budget-only offsets (-$244.5M) and the vacancy factor (-$200.0M), both with an official explanation. The settlements box has a note but no why sentence, as does the Parks vacancy allowance (-$15.2M). Those two are the only dead ends of $10M or more with no sentence (previous audit: 6).

**Payments over the line.** Ratios of paid to line: judgments 2.84x, HIV Ryan White 1.25x, Emergency Solutions 1.27x, Early Childhood Block Grant delegates 1.12x, waste disposal 1.11x, Head Start 1.11x. Payments carry no fund or line, so the match is by department, contract type and program code. An overshoot can mean a wrong match, not just a big year. Each negative box says so.

**Proxies as boxes versus side info.** Boxes: 12 City pay lines ($408M) where 2025 title shares are applied to the 2026 line. The 2026 line is 0.46x to 1.24x of 2025 actual pay on all 12 (Fire scheduled wage adjustments 0.46x, O'Hare overtime 0.70x). Side info only: Police overtime 2025 actual $236.3M against the $200M line, and Corporate Scheduled Wage Adjustments $262.3M, whose 2026 line is 9.28x the matching 2025 pay.

**Duplicated dollars.** Checked: ledger project and fund code on more than one box (2 pairs, different ledger budgets, so separate records: CARES20DB/F033C on three CDBG-CV lines $2.1M, $0.4M, $0.3M, and B3695/F0L98 on two lines $6.0M and $2.0M), award and contract ids on more than one box (0 of 21 FAA awards and 474 contracts), same vendor and amount twice (0), CPS project numbers (1 repeat, "Space To Grow", two funding sources). The real risks:
1. **State/Lake Surface Transportation Program money, $102.1M (older 2025-06-01 ledger extract) next to $18.2M (2026-05-31 extract).** `research/cdot_projects.md` says FTA later de-obligated $55.3M and $9.8M, so the older record may be a superseded slice of the newer ones. Possible double count of up to $102.1M inside the $329.8M piece. The box is labelled gov_estimate.
2. **The same real project on several lines.** Columbus Ave GS11 on four lines ($80.8M), Archer Ave GS09 on four ($50.4M), Canal Street Viaduct on three ($41.8M), Montrose Harbor on three ($13.4M). Different funds, so not a double count, but a reader who adds them up by name gets the project cost wrong. `cdot_projects.md` warns about it. The tree has no tag saying "other funding sources of this project are on other lines".
3. **Calumet River Bridges** appears as TIP spending boxes ($52.0M federal, $112.2M state) and as small ledger reserve boxes ($1.2M). Different lines, same warning.

**Stale or wrong why sentences** (previous audit's rules re-run, plus new checks): 13 City boxes still on the generic fallback ($237.1M, for example Hospital and Medical Expenses $25.0M, Rental of Property $22.8M, Reserve not matched to a project $32.8M). City Emergency Medical Transportation $124.7M says "ambulance trips and their billing", but `research/parks_misc_detail.md` says the use is unconfirmed. Four CPS boxes ($176.1M) say "a few large companies" but are reserves or the preschool pass-through to the City (Preschool for All $88.1M and $32.9M, Labor and Employee Relations $35.0M, School Transitions $20.0M). The previous audit's worst items (highway sentence on construction lines, no sentence on adjustments, HOME and CDC "construction jobs") are fixed. A further 37 boxes that now have children still carry a leaf-style why sentence ($5.4B of parents, mostly pension components and bond series). Harmless if the site shows why only on leaves.

**Individuals' names.** The build output was compared with 156,148 name patterns from `data/people/*.json` (City roster and payroll, CPS roster, Parks has no names). 108 two-word matches in 127 places, all explained: people's names that are also place or business names (parks named for people, 58 CPS schools, a federal program name, "John X Construction", engineering firms) or text inside vendor side info. 9,852 of 16,819 vendor rows are hidden as individuals and none of them still shows a roster name in vendor or description. Not hidden but person-like: **27 couple-style payees ("A & B Surname") with no contract number, $47,792, because `payee.py` treats any "&" as a business sign, and 22 "First Last" payees that hold a City contract number, $5.75M (development loans, delegate agencies, other), because any contract holder counts as a business.** One more "First Last" row, $2,000. Heuristic counts, names not copied here. Fix in `build/payee.py`: hide couples, and treat a two-token "First Last" with no business word as a person even with a contract.

## 3. Structure for a 13-year-old

| Check | Previous | Now | Note |
|---|---:|---:|---|
| Boxes with exactly one child | 2,459 | **525** (City 78, CPS 126, Parks 248, memo 73) | All have the same amount as the child. Left: Parks park to fund 208, CPS account to job group 121, City job title to one pay rate 53, memo fund to line 46. 24 of them are $10M or more (for example a $161.2M pension extra payment holding one payment) |
| Boxes with more than 200 children | 0 | 0 | 17 boxes have 51 to 200. Widest: O'Hare organization unit 175, CPS charter schools 121, CPS Facility Needs 86, Parks South Region 82, City "Other vendors (82)" |
| Depth to a leaf | City median 8, max 9 | City median 8, max 9. CPS median 6, max 7. Parks median 5, max 6 | Dollar-weighted median depth: City 5, CPS 6, Parks 4. 53% of City leaves are at depth 8 or 9, and all 2,652 depth-9 leaves are pay-rate rows ("4 positions x $113,568.00 (grade BX 18)") |
| Same parent, same name | 18 groups, 43 boxes | **57 groups, 145 boxes, $946M** | New problem. 39 City groups, 35 of them differ only by fund (three "Overtime" under Fire, six "For Loss in Collection of Taxes" under Other citywide costs $74.3M, three "Rehabilitation Loans and Grants"). The fund layer was removed, so the difference is no longer visible. Also CPS capital (3x "Contingency For Project Expansion" $195.4M) |
| Codes and jargon | 455 City leaves with a code | 153 City boxes of $1M or more carry a federal program code in the name ($2.95B), 323 pay-rate leaves carry "(grade D 01)". CPS 5 leaves of $1M or more | 25 City "Reserve Balance (agency - program (14.239))" boxes are $10M or more ($1.75B). All 127 City ordinance-line dead ends are named by the account only, with no department |
| Most repeated names | "Other job titles (fewer than 5 positions each)" 1,137x ($968M) | same | Privacy pooling, fine, but the name needs the unit |
| Rounding and tiny boxes | 275 and 441 | 274 and 442 | Unchanged |

## 4. Ranked list of what is left

Dead ends of $10M or more (a leaf, not an N x rate box under $1M): City 239 boxes $8,109M, CPS 91 $3,064M, Parks 6 $119M. Tags: (a) public data unused, (b) needs FOIA or OBM, (c) truly one item. Rules are regexes on the box name and path in `treeaudit2_rank.py`, and 13 boxes ($174M) fell to the default (b). (a) means a public source exists. Only the reachability of each URL was checked (HTTP 200 on 2026-10-02), not that it holds the split.

| Government | (a) public data unused | (b) needs FOIA or OBM | (c) truly one item |
|---|---:|---:|---:|
| City | 25 boxes, $792M (9.8%) | 95 boxes, $3,960M (48.8%) | 119 boxes, $3,357M (41.4%) |
| CPS | 7 boxes, $267M (8.7%) | 30 boxes, $820M (26.8%) | 54 boxes, $1,977M (64.5%) |
| Parks | 0 | 4 boxes, $84M (71.0%) | 2 boxes, $35M (29.0%) |

### Public data we could still fetch

| # | Item | Source | Boxes | Expected $ moved |
|---:|---|---|---:|---|
| 1 | Bond series shares inside "Other bonds" (GO $111.6M and $108.4M, O'Hare $58.7M and $46.7M, Water $44.6M, Midway $13.3M, Water interest $12.0M) | EMMA official statements and trustee schedules, https://emma.msrb.org/ (HTTP 200, but `research/bond_series.md` could not download documents without a browser) | 9 | $395M of leftover becomes named series. Most series are $10M to $60M, so little falls under $10M |
| 2 | CPS electricity and gas ($43.9M, $42.2M, $18.1M, $14.9M) | `data/cps_supplier_payments_fy2026_over1m.csv` (held): Constellation NewEnergy $37.4M, ComEd $35.9M, Peoples Gas $17.8M, Constellation gas $12.5M, together $103.5M against $119.1M of lines | 4 | $103.5M gets named payees. Each stays $10M or more. Cheap, no new fetch |
| 3 | CPS private special education tuition left over ($26.6M) | CPS supplier API, https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026 (HTTP 200, 4,353 vendors under $1M hold $223.7M) | 1 | Up to $26.6M, all under $10M |
| 4 | CPS Preschool for All ($88.1M, $32.9M) | Link to the City tree: "Delegate Agencies (ISBE - CPS - Early Childhood Block Grant)" has $71.6M of paid-to-date boxes. Board Reports 25-0925-EX2 and 26-0730-EX2 | 2 | $121M of pointer, not new dollars. Fix the sentence |
| 5 | Grant reserve lines with a project list in the City ledger (HOME $39.3M and $29.0M, CDC $22.2M and $11.6M, Homeland Security UASI four lines $61.7M, COPS $15.6M, DCEO senior center $16.0M) | `data/city_grants_2026.json` reserve_attribution (held, unattached). Ledger https://data.cityofchicago.org/resource/iyu8-jkf8 has only two extracts (2025-06-01, 280 rows, and 2026-05-31, 509 rows), so no newer one exists | 10 | $195M of lines. Named items would be caps from a 2026-05-31 snapshot |
| 6 | CDBG-DR sewer and stormwater plan (miles x $8.5M $221.3M, permeable alleys $67.1M, wing storage $62.1M, cleaning $29.7M, planning $19.6M) | HUD Disaster Recovery Grant Reporting, https://drgr.hud.gov/public/ (HTTP 200, not opened) | 5 | Up to $400M if activity lists exist. Unverified |
| 7 | Water and Sewer state loans (Water payment $39.7M, interest $14.1M, Sewer $32.6M and $11.7M) | Illinois EPA revolving fund, https://epa.illinois.gov/topics/grants-loans/state-revolving-fund.html (HTTP 200, not opened) | 4 | Up to $98M, one loan each. Unverified |
| 8 | Vendor to budget line mapping for ordinary contract and supply lines (O'Hare professional services $92.2M, IT, rental, repair, supplies, loans and grants to agencies) | OBM Mid-Year Report "Data Directory" Tableau, https://public.tableau.com/app/profile/obm.data.analytics/viz/Mid-YearReport-DataDirectory/DataDirectory-Mid-YearReport (page loads, data needs a browser, guessed CSV export gives 404). The report says it lists the funding line used | 50 | Up to $1.28B of line dollars could get named vendor pieces. Share under $10M unknown until the extract is read |

### Needs FOIA or the budget office

| # | Item | Ask | Boxes | $ |
|---:|---|---|---:|---:|
| 1 | Federal airport carryover tied to no award (O'Hare $282.2M and Midway $99.8M, plus Midway 2026 grant money not yet awarded $30.5M) | Aviation or OBM: AIP grant ledger by award. FAA FY2026 grant history is not published yet | 3 | $412.5M |
| 2 | Highway and state reserves larger than any project list (federal $218.1M, Rebuild Illinois $57.3M, state $37.1M, other $40.9M, FTA $32.9M, HOME $32.8M) | CDOT or OBM: reserve by project. Leads, not checked: FHWA FMIS, IDOT e-Project | 6 | $419.1M |
| 3 | CPS contingencies ($120.0M, $50.4M, $50.0M, $35.3M, and more) | CPS Budget Office: planned use by program | 12 | $406.2M |
| 4 | State/Lake station: rest of the federal award $127.6M and four funding boxes | CDOT, or FTA TrAMS line items for IL-2016-002 (FTA site returned 403 here) | 5 | $322.5M |
| 5 | Union contract money (Corporate Scheduled Wage Adjustments $262.3M and three more) | OBM: contract settlement schedule | 4 | $320.7M |
| 6 | City claims and benefits totals (workers' compensation $44.8M, injured on duty $25.0M, dental $15.2M, Medicare $38.2M, loss in collection $32.5M and more) | Finance and Risk Management: totals by type | 11 | $253.0M |
| 7 | Emergency Medical Transportation $124.7M | Finance: ledger for account 9222, or State HFS invoices | 1 | $124.7M |
| 8 | Police overtime beyond CPD's monthly targets | CPD or OBM: overtime by unit and event | 1 | $124.6M |
| 9 | OBM adjustment no line explains | OBM: how it is figured | 1 | $117.0M |
| 10 | CPS health set-aside (HCSC $116.8M, Caremark $37.1M) and food (lunch $57.0M, breakfast $33.6M, donated $11.7M) | CPS Benefits claims by plan, CPS meals payments by meal type | 5 | $256.2M |
| 11 | Parks Soldier Field $36.3M, harbors $16.6M, water and sewer $16.7M, electric $14.8M | Park District: operator budgets (P-12035, P-14010) and utility billing by account | 4 | $84.4M |

### Top 10 remaining items, one line each

1. OBM Data Directory extract: up to $1.28B of ordinary contract lines get vendors. Public but needs a browser, else ask OBM.
2. Federal airport carryover, $412.5M: Aviation or OBM.
3. Highway and state reserves with no project, $419.1M: CDOT or OBM.
4. CDBG-DR plan, $400M: HUD DRGR (public, not opened).
5. Bond series inside "Other bonds", $395M: EMMA (public, browser).
6. CPS contingencies, $406.2M: CPS Budget Office.
7. State/Lake station, $322.5M: CDOT or FTA.
8. Union contract money, $320.7M: OBM.
9. City claims and benefits, $253.0M: Finance.
10. CPS utilities named payees, $103.5M: data already held, small build change.

Not dollars but cheaper than any of the above: hide couple and contract-holding "First Last" payees, rewrite 18 why sentences, restore the fund label on same-name sibling lines, tag CDOT projects that appear on several lines, and decide whether State/Lake's older $102.1M STP record stays.

## Appendix: top 30 dead ends per government, tagged

Source: `raw/treeaudit2/deadends_*.json` via `treeaudit2_rank.py`. Full lists are in that file (City 239, CPS 91, Parks 6). The box path is shortened.

**City of Chicago** (239 dead ends of $10M or more, $8,109M)

| # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---|---|:-:|---|
| 1 | 282.2 | Carryover not tied to a named FAA award > Still not tied to any FAA award, ev... | residu | b | federal airport carryover no public record ties to a project |
| 2 | 262.3 | City's main fund (Corporate Fund) > Scheduled Wage Adjustments | budget | b | set aside for union contracts not yet settled, and the 2026 line is 9.3x last year's matching pay, so no public split fits |
| 3 | 221.3 | Construction > about 26.0 miles of local sewer x $8.5M per mile | proxy | b | disaster recovery plan has miles and a unit cost, streets not picked |
| 4 | 218.1 | Construction > Federal highway money with no project in the regional plan for... | residu | b | reserve larger than any public project list |
| 5 | 161.2 | Extra payment above what the law requires > Two extra payments into the fund'... | tied | c | one extra payment into a pension fund |
| 6 | -151.7 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses and ... | adjust | c | payments so far are larger than the budget line, shown as a negative box |
| 7 | 127.6 | State/Lake Loop Elevated Station (one named project) > Rest of the federal aw... | residu | b | one federal award, station cost breakdown not published |
| 8 | 124.7 | City's main fund (Corporate Fund) > Emergency Medical Transportation | budget | b | use of line unconfirmed |
| 9 | 124.6 | Overtime > Rest of police overtime: other units, events and projects, and mon... | residu | b | CPD publishes targets for part of its overtime, not the rest |
| 10 | -117.0 | Adjustment the budget office makes that no line explains | adjust | b | OBM deduction no line explains |
| 11 | 111.6 | For Interest on Bonds > Other bonds (not printed one by one) | residu | a | bond series share not printed in the statements we hold |
| 12 | 108.4 | For Payment of Bonds > Other bonds (not printed one by one) | residu | a | bond series share not printed in the statements we hold |
| 13 | 102.1 | State/Lake Loop Elevated Station (one named project) > Surface Transportation... | gov_es | b | one federal award, station cost breakdown not published |
| 14 | 99.8 | Reserve Balance > Carryover not tied to a named FAA award | residu | b | federal airport carryover no public record ties to a project |
| 15 | -98.0 | Salaries and Wages - on Payroll > Budgeted turnover (vacancy savings), Corpor... | adjust | c | planned saving that offsets pay lines |
| 16 | 92.2 | O'Hare airport money > Professional services | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 17 | 91.8 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses and ... | paid_t | c | settlement payments, each a separate court deal (cases involve private people) |
| 18 | 90.5 | Paying back loans > For Payment of Bonds | budget | c | one bond series, interest or principal |
| 19 | 90.0 | For the Payment of Tort and Non-Tort Judgments, Outside Counsel Expenses and ... | paid_t | c | settlement payments, each a separate court deal (cases involve private people) |
| 20 | 86.2 | 01-24-0017: Calumet River Bridges > Construction, State Match - Chicago | proxy | c | one named project or one federal award |
| 21 | 72.2 | Extra payment above what the law requires > Advance payment: City pays more t... | tied | c | one extra payment into a pension fund |
| 22 | 67.1 | Construction > Construction | budget | b | disaster recovery plan has miles and a unit cost, streets not picked |
| 23 | 65.6 | Programs and other costs > Rehabilitation Loans and Grants | budget | b | money passed to many agencies or people, contract-to-line link is not public |
| 24 | 64.8 | City's main fund (Corporate Fund) > For Professional Services for Information... | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 25 | 62.8 | Other citywide costs > For Distribution of the Net Proceeds of the Real Prope... | budget | c | pass-through to the CTA |
| 26 | 62.1 | Disaster Recovery Fund > Construction | budget | b | disaster recovery plan has miles and a unit cost, streets not picked |
| 27 | 61.3 | O'Hare airport money > Operation, Repair or Maintenance of Facilities (Chicag... | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 28 | 59.5 | State/Lake Loop Elevated Station (one named project) > Congestion Mitigation ... | gov_es | b | one federal award, station cost breakdown not published |
| 29 | 58.9 | Local Public and Private Grant Fund > Professional services (SISTER AGENCY / ... | budget | b | ordinary contract or supply line, vendor payments exist (side info) but carry no budget line |
| 30 | 58.7 | Other bonds (not printed one by one) > Rest of the older bonds (not printed o... | residu | a | bond series share not printed in the statements we hold |

**Chicago Public Schools** (91 dead ends of $10M or more, $3,064M)

| # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---|---|:-:|---|
| 1 | 254.2 | Bond series 2009G > Series 2009G: final repayment of the loan (principal) | tied | c | one bond series (or one payment of it) |
| 2 | -143.3 | Teacher pay set-aside (budget only) > Planned savings from jobs left unfilled... | adjust | c | planned offset or reserve counted elsewhere |
| 3 | 120.0 | Money held back for later (contingency) > Contingency For Project Expansion (... | budget | b | money held back, no document itemises it |
| 4 | 116.8 | Health insurance set-aside (budget only) (All Other) > Medical plan share (HCSC) | proxy | b | reserve for bills that have not arrived |
| 5 | -100.0 | Money held back for later (contingency) > Other General Charges (General Educ... | adjust | c | planned offset or reserve counted elsewhere |
| 6 | 88.1 | Professional and administrative services > Payment To Other Govt Units (State... | budget | a | passes through the City (DFSS) to community providers, providers are in the City tree |
| 7 | 80.0 | Facility Needs > Emergency/Unanticipated Facility Repairs | budget | c | capital money not assigned to a project yet |
| 8 | 70.0 | IT - Centralized (DC, CO etc.) > IT money budgeted but not spent on a named p... | residu | c | capital money not assigned to a project yet |
| 9 | 61.3 | Pension reserve in the general fund (a reservation, not a payment) > CPS oper... | proxy | c | one reserve or levy paid as one amount |
| 10 | 59.3 | Pension reserve in the general fund (a reservation, not a payment) > State's ... | proxy | c | one reserve or levy paid as one amount |
| 11 | 57.0 | Food > NSS - Lunch Program (Lunchroom Fund) | budget | b | one food contract paid across several food lines |
| 12 | -56.7 | Staff pay set-aside (budget only) > Planned savings from jobs left unfilled (... | adjust | c | planned offset or reserve counted elsewhere |
| 13 | -52.9 | Money held back for later (contingency) > Other Instr Purposes Misc (General ... | adjust | c | planned offset or reserve counted elsewhere |
| 14 | 50.8 | Paying back loans > Bond series 2016A | budget | c | one bond series (or one payment of it) |
| 15 | 50.4 | Money held back for later (contingency) > Contingency For Project Expansion (... | budget | b | money held back, no document itemises it |
| 16 | 50.0 | Money held back for later (contingency) > Special Income Fund 124 Contingency... | budget | b | money held back, no document itemises it |
| 17 | 48.8 | Bond series 2018C > Series 2018C: principal repaid (the loan itself) | tied | c | one bond series (or one payment of it) |
| 18 | 44.5 | Salaries > Staff pay set-aside (budget only) | budget | c | planned offset or reserve counted elsewhere |
| 19 | 44.4 | Tuition paid to charter schools > Charter/Contract Per Pupil Revenue K-12 Tui... | budget | c | one charter campus, one payment set by student count |
| 20 | 44.4 | Bond series 1998B-1 > Series 1998B-1: interest that built up since 1998 (accr... | tied | c | one bond series (or one payment of it) |
| 21 | 43.9 | Supplies, food and utilities > Electricity | budget | a | a few utility suppliers, payments public |
| 22 | 43.5 | Paying back loans > Bond series CIT 2016 | budget | c | one bond series (or one payment of it) |
| 23 | 42.2 | Supplies, food and utilities > Electricity delivery | budget | a | a few utility suppliers, payments public |
| 24 | 37.1 | Health insurance set-aside (budget only) (All Other) > Prescription plan shar... | proxy | b | reserve for bills that have not arrived |
| 25 | 35.3 | Money held back for later (contingency) > Contingency Balancing Program (Cont... | budget | c | planned offset or reserve counted elsewhere |
| 26 | 35.0 | Other charges > Labor And Employee Rels (General Education Fund) | budget | b | money held back, no document itemises it |
| 27 | -34.6 | Workers' compensation, unemployment and claims > Workers' compensation set-as... | adjust | c | planned offset or reserve counted elsewhere |
| 28 | 34.5 | Bond series 2018A > Series 2018A: principal repaid (the loan itself) | tied | c | one bond series (or one payment of it) |
| 29 | 33.6 | Food > NSS - Breakfast Program (Lunchroom Fund) | budget | b | one food contract paid across several food lines |
| 30 | 32.9 | Professional and administrative services > PreK Instruction (State Preschool ... | budget | a | passes through the City (DFSS) to community providers, providers are in the City tree |

**Chicago Park District** (6 dead ends of $10M or more, $119M)

| # | $M | Box | Basis | Tag | Why it stops |
|---:|---:|---|---|:-:|---|
| 1 | 36.3 | Soldier Field, harbors, golf and other managed venues > Soldier Field | budget | b | run by a contractor, no operating budget published |
| 2 | 19.4 | Series 2023C: refinancing loan > Paying back the loan itself (principal) | tied | c | one bond payment |
| 3 | 16.7 | Contracts, utilities and services > Water and sewer bills | budget | b | per-park usage not published |
| 4 | 16.6 | Soldier Field, harbors, golf and other managed venues > Boat harbors | budget | b | run by a contractor, no operating budget published |
| 5 | -15.2 | Pay, benefits and savings reserves > Savings from jobs left unfilled (vacancy... | adjust | c | planned offset |
| 6 | 14.8 | Contracts, utilities and services > Electric bills | budget | b | per-park usage not published |
