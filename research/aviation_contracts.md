# Aviation: operating lines other than professional services (contracts matching)

Built by `scripts/aviation_contracts_build.py` into `data/splits/city/aviation_contracts.json`. 12 splits, all `side_only`, 0 skipped.
Result: **no payment could be placed as a box**. Delivering zero boxes is the honest answer, and the side lists show what was found.

## Lines covered

O'Hare (fund 0740, authority 2015) and Midway (fund 0610, authority 2010), department 85 Aviation, accounts:
0138 IT maintenance ($55.0M O'Hare, $9.9M Midway), 0157 rental of equipment and services ($41.8M, $14.9M), 0161 operation, repair or maintenance of facilities ($61.3M, $29.4M),
0162 repair or maintenance of equipment ($29.8M, $32.1M), 0163 streets and pavements ($14.4M, $6.1M), 0183 water ($12.0M, $1.7M).
Lines 0340 and 0446 (supplies and IT hardware) were also looked at: no contract of the commodity type names an airport clearly and the payments have no account, so they are not touched.
The professional services lines (0140) belong to the other aviation files (`aviation.json`, `paid_to_date.json`) and are not touched.

## Data and joins

- Payments: `raw/contracts/payments_2026ytd_dedup.csv` (dataset s4vu-giwb, checks 2026-01-01 to 09/28/2026). Columns: voucher, amount, check date, department, contract number, vendor. No fund and no account.
- Contracts: `raw/contracts/contracts_all.csv` (dataset rsxa-ify5), latest revision per contract number, the FULL description (the items file cuts at 90 characters).
- Aviation payments: 3,979 rows with department "CHICAGO DEPARTMENT OF AVIATION", $990.2M. A further 1,213 rows on PV85 vouchers have a blank department. Of those, a few are contract payments to Aviation contracts and many are direct vouchers (contract "DV", no contract text): Department of Aviation Midway $22.7M, Alliant Insurance $13.4M, City Department of Water $9.5M, ComEd and Commonwealth Edison $9.8M, MWRD $3.9M and others.

## Why nothing is placed (the rule, same as scripts/paidtodate_build.py)

A payment is placed only if one line is left after every clue. Here:
1. **Fund (airport).** The fund is the airport, and it must come from the contract text. In 2026, of $40.2M paid on maintenance-type Aviation contracts (snow, doors, roofing, landscape, repair, electrical, fire alarm), $11.4M is for contracts naming both O'Hare and Midway and $8.5M names neither (Preform, Terrazzo, Builders expansion joints, and others). Only $9.4M names O'Hare alone and $1.4M names Midway alone.
2. **Account.** Even when one airport is named, the family has several accounts (0160, 0161, 0162 for maintenance and repair, 0157 for rental). Nothing in the contract text says which. Example: O'Hare automatic doors maintenance (Builders Chicago Corporation, contract 102725, $4.6M), O'Hare airside snow removal (Plote 114934, J S Reimer 112501, Snow Systems 325581). They could be 0161 (facilities) or 0162 (equipment), or 0163 for the pavement part.
3. **Shuttle buses.** The O'Hare shuttle buses (Delaware Cars/T.R. Harmsen 15304, $10.9M paid) and Midway shuttle (Continental Air Transport 194124, $6.0M) each name one airport, but the line is either 0157 rental of equipment and services or 0161. One airport and two plausible accounts: not placed.
4. **Pavement.** Pavement contracts (Rossi 102520 and 102390, Sanchez 103256) name both airports. Preform striping (343540) names neither. Not placed.
5. **IT.** The IT contracts name both airports (SDI Presence 46733 integrated safety and security command systems, $10.5M; Catalyst 89748, $2.7M), or are too small. Not placed.
6. **Water.** The City Department of Water was paid $9.5M on Aviation vouchers (45 direct vouchers). The voucher says nothing about the airport. The O'Hare water line is $12.0M and the Midway water line $1.7M, so the amount cannot be divided with any evidence, and it is more than the Midway line alone. Not placed.
7. **Boschung snow equipment (contract 341673, $39.0M for Midway and O'Hare).** Names both airports and is a purchase of equipment (0440 or vehicles), not a maintenance line. Not placed and not counted in the maintenance family.
8. **Construction contracts** (Paschen East Taxiway 263824 $13.6M, Grade Separated Roadway 308592 $16.2M and West Taxiways 339016 $5.7M at O'Hare, K-Five/Plote Midway Runway 13C-31C 304043 $17.0M, Blinderman RSIP 307284 $10.0M, Rausch Parking Lot B, Courtesy Electric Ring Tunnel) are capital work paid from grants (see `aviation_awards.json`, several are described as "Federally Funded"), airport bond money or airline money. They are not paid from these operating accounts. Not placed.
9. Reimbursable agreements with airlines (CATCO, Midway Airlines' Terminal Consortium, American Airlines, Spirit; contract type COMPTROLLER) are pass-through agreements. Not placed.

## What the side lists show

Each line carries side facts (not added to amounts), basis "actual", source dataset s4vu-giwb joined to rsxa-ify5:
- the contracts of the line's family that name only that airport, paid in 2026 (up to 8, by amount);
- one row for the same family where both airports or neither is named, with the amount NOT divided.

Note this means a reader sees $11.4M and $8.5M of facility work "not divided" next to both airports' lines. The total of that row is shared by the two airports and is not a per-airport number. Totals of the same family appear on the 0161 and 0162 lines because the contract text does not choose between them. This is stated in the note on each line.

## Gaps and next steps

- The City's own Vendor, Contract and Payment Search (not the open data copy) may show the fund and the account for a payment. Nothing public does.
- The Budget Book does not list contracts by account. A request to the Department of Aviation for the 2026 voucher distribution file would settle it.
- Direct vouchers (contract DV) of $80M with blank department on PV85 vouchers carry no contract text. ComEd and Commonwealth Edison ($9.8M) are probably the electricity line (0331, which has no leaf of its own under Aviation in this tree: it belongs to Fleet and Facility Management's electricity line).
