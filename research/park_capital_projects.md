# Chicago Park District: dollars per capital project

Built 2026-10-01. Data: `data/parks_capital_projects.json`. Scripts: `scripts/parkcap_fetch.py`, `parkcap_schedules.py`, `parkcap_build.py` (run in that order). Raw files: `raw/parkcap/` (gitignored).

## Bottom line

The District publishes no project-level dollars for the 2026-2030 CIP ($681.4M) and none on its capital map. What can be built from public records is a partial project dollar list, and almost all of it is the **outside-funded TIF slice**. The District's own bond money ($200M of new G.O. bonds plus $74M of prior-year active projects) has **no per-project figure anywhere public**.

| Question | Answer |
|---|---|
| Does the capital map backend hide cost fields? | No. ArcGIS layer `cap24_3` has 16 fields: ids, park name and number, scope, ward, region, sub-program, status, year complete, x/y. No budget, cost or funding source. The web map (item 724b7231f21d4210ad4c4ce8028295bf, webmap 0c62969125724a59a676ca54a878449a) shows only those fields in its popup. Other CPD layers (parks, buildings, facilities, river projects) have no money either. |
| Named dollars inside the 2026-2030 CIP | **$108.9M of TIF** across 28 named project lines (City TIF Projections 2025-2034, 2026 to 2030 columns). That is **16.0% of the $681.4M** and **68.7% of the CIP's $158.5M TIF line**. Remaining ~$49.6M of the TIF line is unnamed or timed outside the window. |
| Named dollars for 2026 | TIF lines in the 2026 column total **$62.9M** across 27 projects. Compare with the $91.8M ordinance capital appropriation and the $53.5M District money in the CIP's 2026 column. These are different bases (City TIF cash schedule versus Park District appropriation versus plan), so do not subtract them. |
| Share of District-funded $225.5M with project names | About 0%. The 2026 bond reimbursement resolution (26-1262-0211) caps $40,000,000 for "the 2026 Parks Projects" with no list. Bond ordinance 25-1159-1008 (up to $120M) names no projects. |
| State, federal, private ($162.5M in CIP) | Named in public records: OSLAD $2.3M total over 3 rounds (one named: Northerly Island $600K), HUD Community Project Funding $2.75M (4 awards, FY22 and FY23), narrative mentions Kells $1.5M state and Cragin $0.5M HUD. Under 4% of the state, federal and private lines. |
| City grant line ($60.7M) | Aldermanic menu 2026 has only 6 Park District lines, **$163,585** total. The rest of the City line is not itemized by park. |

## Project counts by size

Counts depend on which record you call a "project". Records overlap (a TIF line, its IGA, and its construction award are the same project), so **do not add across rows**.

| Record set | n | under $1M | $1M to $10M | $10M and over | Sum |
|---|---|---|---|---|---|
| TIF projection lines, 2026-2030 amounts | 28 | 9 | 15 | 4 | $108.9M |
| TIF projection lines, 2026 column only | 27 | 12 | 14 | 1 | $62.9M |
| TIF IGA approvals since 2021 (approved TIF) | 53 | 29 | 20 | 4 | $127.4M |
| TIF IGA approvals since 2021 (total project cost) | 53 | 29 | 19 | 5 | $206.1M |
| Board awards and change orders 2018 on | 38 | 14 | 21 | 3 | $174.2M (mixes contracts and change orders) |
| Bonfire capital contracts with a stated value | 14 | 1 | 10 | 3 | $165.3M |
| Park level, largest single figure, 60 parks | 60 | 25 | 27 | 8 | exploratory only |

Read: of the named TIF projects, **9 of 28 are under $1M and 24 of 28 are under $10M**. Only four are $10M or more in the window: Kells Park fieldhouse ($15.0M), Ogden Park ($12.0M), Humboldt Park ($11.85M), Gately Stadium ($10.0M). The District says "over 25 facility restorations have standalone budgets of $1 million or more" (budget PDF p64), which is consistent with about 15 TIF projects in the $1M to $10M band plus others funded by bonds.

### Link to the 3,116 map projects

Dollars attach to a park and a named project, not to individual map rows (map rows have no cost, and their scope text rarely matches a funding line name). Of the **395 active or pending map projects**: 47 sit at one of the 23 parks with TIF dollars in 2026-2030, and 141 sit at one of 75 parks with any dollar record since 2021. 254 active projects (64%) have no dollar record of any kind. Park-level index: `by_park` in the JSON (129 parks, keyed by park number, joined to `budget_node_id` where the park has a node in `data/parks_2026.json`; 41 of the 129 are parks with no node in the 2026 budget park list, for example Kells 1040 and Park 598, because they have no 2026 operating unit yet).

## Largest named projects (2026-2030 TIF window, with other sources)

| Park (no.) | Project | TIF 2026-2030 | Other public figure |
|---|---|---|---|
| Kells (1040) | New fieldhouse | $15.0M | TIF IGA $16.4M (2024-09-18); budget PDF p65: $17M TIF + $1.5M state |
| Ogden (8) | Park improvements, new fieldhouse | $12.0M | Design contract (Booth Hansen) implied $1.65M, Nov 2025 |
| Humboldt (219) | Park improvement plus Cultural Center | $12.95M | none |
| Gately (244) | Stadium and park | $13.0M | Track and field center $56M complete 2020 |
| Moran (1051) | Fieldhouse | $9.0M | IGA $9.0M (2024-06-12) |
| Piotrowski (230) | Pool enclosure | $8.0M | design contract implied $0.71M, May 2025 |
| Chase (103) | Park improvements | $7.0M | none |
| Garfield (204) | Powerhouse, water garden, gold dome | $5.15M | children's garden $8.6M contract |
| Douglass (218) | Lower level renovation | $4.7M | design contract $0.60M implied |
| Hermosa (125) | Facility improvement | $4.25M | none |

Not in the TIF window but large and recent: Jackie Robinson fieldhouse (236) IGA total cost **$17.0M** (TIF $2M + state DCEO), construction award implied **$14.4M** (May 2024); Clarendon Community Center (1002) change order schedule implies $13.9M; Park 596 campus $64.5M Bonfire value (complete 2023).

## Sources tried and what each gave

1. **ArcGIS capital map** (`services7.arcgis.com/HpTF5nhGpVZolZvo/.../cap24_3/FeatureServer/0`). Count 3,116, no dollar field. Searched the org's 23 public items for cost data: nothing. Dead end.
2. **City TIF Projections 2025-2034**, https://data.cityofchicago.org/resource/fpsv-qjg3 (published 2025-10-15). **Best source.** 69 Park District lines after removing offsetting inter-TIF transfers and CDOT, CPS and CTA lines. Per-year dollars 2025 to 2034. 65 of 69 lines join to a park number (the 4 unjoined are unnumbered dog parks and the HQ line).
3. **City TIF agreements list**, https://data.cityofchicago.org/resource/mex4-ppfc. 138 IGAs with the Park District since 2006, with approved TIF and total project cost. 134 join to a park number.
4. **Legistar API** (https://webapi.legistar.com/v1/chicagoparkdistrict/matters). 1,432 matters, 2014 to 2026, `MatterCost` empty on every record. Titles carry amounts only for change orders and final payments (about 69 items). **Award amounts for 2023 onward are not in the record**, minutes list no dollars, and attachments are only MWBE schedules.
5. **MWBE Schedule A OCR** (`parkcap_schedules.py`). Each bid's schedule lists subcontractor dollars and percent of contract. dollars / percent gives the bid price. OCR (macOS Vision) of 48 capital award packets, **34 yielded an implied price** (at least 2 agreeing pairs within 4%). Accuracy check: Garfield children's garden implied $8,592,703 vs Bonfire stated $8,581,000 (0.1%), Park 596 campus implied $68,970,588 vs Bonfire $64,505,650 (6.9% high, probably because the bid included alternates). Treat as plus or minus 7%. Labelled `implied`, never as an award. 14 packets did not parse (blank fields or unusual layout). Example: Burnham Building restoration (Jackson 19, June 2026) implied $5,295,984.
6. **Bonfire public contracts** (`raw/gap/bonfire_contracts.json` plus detail API `internalApi/publicContracts/{id}`). 768 contracts, 305 with a nonzero value. Capital contracts with value are mostly pre-2020 (Maggie Daley $42.6M, Morgan Park Sports Center $17.2M, Park 596 $64.5M). 2023 onward construction awards (P-23001 General Contractor pool, 36 contracts) show value 0, so no help for the current plan.
7. **Older CIPs 2015-2019 to 2021-2025** (6 downloaded, plus the one already in raw/parks). Category-level tables and donor lists in bands ($10K-$99K up to $1M and above), **no project dollars**. The 2011-2024 Capital Projects by Park PDF has no dollar column. Dead end.
8. **Park District web**: featured capital projects page lists budgets for 9 completed projects (606 $91M, Gately $56M, Brighton Park $64M, Maggie Daley $60M, Addams $25M, La Villita $19M, Lakefront Trail $16M, Boat Houses $24M, Big Marsh $7.8M) and the 16-park **Chicago Grows Together** list ($5.0M total, $200K to $500K each, TIF surplus). Stay Cool Together AC pilot $1M. Budget narrative: Cragin $7.1M TIF + $0.5M HUD, Kells $17M TIF + $1.5M state, shoreline projects "over $8M", utility replacement "nearly $6M".
9. **OSLAD** (IDNR press lists): 2024-01-30 $700K, 2024-12-16 $1.0M, 2026-01-09 $600K (Northerly Island). Project names not given for the first two.
10. **USAspending**, recipient "CHICAGO PARK DISTRICT": 49 non-contract awards, $20.1M all time, **12 since 2021 totalling $4.5M**. HUD community project funding 2023 (4 awards, $2.75M) is the only capital-type federal money, and the award text does not name the parks. The rest is EPA and Fish and Wildlife habitat grants and VA sports programs.
11. **Bond documents**: ordinance 25-1159-1008 ($120M not-to-exceed, "Project of not less than $55,000,000") and reimbursement resolution for 2026 ($40M). Neither lists projects. Official statements on EMMA were not retrieved in this pass (no project list expected for G.O. limited tax bonds).
12. **Aldermanic menu Q2 2026**: 6 Park District lines ($10,000 to $55,000 each, $163,585 total, wards 11, 26, 33, 43, 49).

## Caveats

* TIF projection lines are the City's planned cash by year (as of Oct 2025). They are not the Park District's project budgets and can shift. Total project cost is only known where an IGA lists it.
* Chicago Grows Together ($5.0M) may sit inside TIF surplus lines already counted, so it is shown separately and not added.
* Park 596 IGA total cost ($69.4M) and the $1.25M 2025 change order are separate facts. Do not stack.
* Joins: park numbers come from the text ("Park 0122"), a unique name match, or a hand-verified table (`TEXT_OVERRIDE`, `BOARD_PARK`, `CGT_PARK` in `parkcap_build.py`). Contractor names (Paschen, Williams) caused false matches that were fixed by hand. "Foster" in Chicago Grows Together is assumed to be Foster (J. Frank) 26 (the other candidate is Austin Foster 285).
* No estimates are included. Where a field says `implied`, the rule is in `meta.implied_price_rule`.

## Recommended next steps

1. File the FOIA for the working CIP project list (foia@chicagoparkdistrict.com). It is the only way to get dollars for the G.O. bond projects. The ask: project number, name, park, funding source, budget by year, for the 2026-2030 CIP, matching the capital map `Project_No`.
2. Re-run `parkcap_fetch.py`, `parkcap_schedules.py`, `parkcap_build.py` after each monthly Board meeting (new awards land on Legistar with MWBE schedules, 2nd Wednesday).
3. For the explorer: show per-park "named dollars" from `by_park` with source badges (TIF plan, board award implied, stated budget) and say plainly that bond-funded projects have scope and status only.
