# CDOT project-level detail for the grant construction and reserve lines

Date of research: 2026-10-02. Build: `python3 scripts/cdot_build.py` writes `data/splits/city/cdot_projects.json` (51 splits, all applied, 0 skipped by `python3 build/city_tree.py`, city check 0 problems, total unchanged at $16,842,553,003.00). Raw cache (gitignored): `raw/cdot/`. Refresh the CMAP data with `python3 scripts/cdot_etip_fetch.py 3488 16811 cdot`.

## Bottom line: dollars now attached to a named project, per line

"Attached" means inside a named project box. The remainder is a visible "not itemised" box with a plain-English reason.

| Line (fund, authority, account) | Line amount | Attached | Share | Source of the project amounts |
|---|---:|---:|---:|---|
| 925F 281S 0540 Federal highway construction | $451,646,229 | $233,519,343 (14 projects) | 51.7% | CMAP eTIP, TIP 2026-2030, FFY2026 column |
| 925S 280E 0540 IDOT state construction | $117,368,000 | $112,191,494 (1 project) | 95.6% | CMAP eTIP, FFY2026 State Match |
| 925S 280Q 0540 Rebuild Illinois construction | $9,500,000 | $9,313,253 (1 project) | 98.0% | CMAP eTIP, FFY2026 Rebuild Illinois |
| 925S 280E 909A IDOT reserve | $124,113,000 | $87,025,183 (36 projects) | 70.1% | City Mid-Year Grants ledger, fund F0L98 |
| 925S 280Q 909A Rebuild Illinois reserve | $117,880,000 | $60,547,611 (13 projects) | 51.4% | Ledger, fund F0W32 |
| FHWA reserve "named projects" piece (existing $121.1M proxy) | $121,122,530 | $121,122,530 (39 projects) | 100% | Ledger, ALN 20.205, both extracts |
| State/Lake piece (existing $329.8M proxy) | $329,801,213 | $202,182,539 (5 funding sources) | 61.3% | Ledger project D1209, five funding records |
| 19 other non-airport reserve lines with boxes (handed over by the coordinator), plus 22 side-only | see below | $91,639,354 | | Ledger by department and grant |

Total placed in boxes by this file: **$917.5M** (the table above, plus the other reserve lines).

Basis labels. TIP and ledger amounts are published numbers, so they are `gov_estimate`. The two state construction lines (280E, 280Q) are labelled `proxy`, because the amounts are the TIP's own but which project sits on which budget line is our choice (by fund type). Every box of $10M or more has a `why` sentence.

## What each number is (read this before quoting anything)

- **TIP amounts** are CMAP eTIP "programmed" dollars in the **FY2026 column of TIP 2026-2030, which is federal fiscal year 2026 (Oct 2025 to Sep 2026)**, not City calendar 2026 and not an appropriation. They are what the regional plan says will be obligated for that phase and fund source. The TIP does not say which City budget line a fund pays through. We match by fund type: federal-highway funds (STP-L, TAP-L, CMAQ, STP shared and redistribution, National Highway Freight) to 925F 281S, state-type funds to the 925S lines. "Other - Federal", "Community Project Funding", "Local Funds" are left off those lines and listed as side facts.
- **Ledger amounts** (reserve lines) are **budget minus expended to date** from the City's Mid-Year Grants 925 dataset, extract 2026-05-31 (money on order but not yet paid still counts as unspent). The reserve itself is carryover cut about Aug 1 2025, so there is a timing gap of about 10 months. These are upper bounds, not exact shares.
- **State/Lake** boxes are unspent amounts by federal funding source. The ledger project is D1209.

## Sources, with what was verified

1. **CMAP eTIP** (the best source). Public site https://etip.cmap.illinois.gov/ (redirects to https://cmap.ecointeractive.com/). The site is a single-page app. It has no download link we could use, so `scripts/cdot_etip_fetch.py` calls the same public JSON API the page itself calls (`api-pwi-prod.ecointeractive.com`, using the two keys the site's own `tenantConfig.json` serves to every visitor). Plan cycles available: TIP 2027-2031 (id 3639, a draft out for comment until 2026-10-13), **TIP 2026-2030 (id 3488, used)**, prior TIP 2022-2025 (id 3477). Lead agency CDOT is organization id 16811. Result: **108 CDOT projects, 28 with money in FFY2026, $823,628,352 programmed in FFY2026 across all fund sources** (federal highway $233.5M, state-type $200.7M, local $368.5M, other federal and Rebuild Illinois the rest). Each project has phase, fund source, prior, FY2026 to FY2030, future, total. TIP 2027-2031 has only 11 CDOT projects so far, so it was not used. Cited in the file as "CMAP eTIP, TIP 2026-2030, project <TIP ID>, fund table, column FY2026".
2. **City Mid-Year Grants 925** (dataset `iyu8-jkf8`, https://data.cityofchicago.org/resource/iyu8-jkf8). Two extracts, 2025-06-01 (60 CDOT records) and 2026-05-31 (196 CDOT records), no record in both. Verified record counts and fund codes locally.
3. **USASpending** award IL-2016-002 (FTA, State/Lake), https://www.usaspending.gov/award/ASST_NON_IL-2016-002_069. Live check today: obligation $414,620,572, outlays $89,265,482 (our cache from Aug 2025 says $84,819,359, which is where the existing $329.8M cap comes from). The cached cap was left unchanged.
4. **IDOT FY2026 Annual Highway Improvement Program**, https://idot.illinois.gov/content/dam/soi/en/web/idot/documents/transportation-system/maps---charts/proposed-improvements/fy2026/FY26_Annual_Highway_Program_Combined_Final_092325.pdf (byte-identical to `raw/grants_tree/idot_fy26_annual_highway_program.pdf`). 19 Chicago-sponsored local-system projects are carried as side facts on 925F 281S 0540 with PDF page numbers (pages 72 to 85), for example Ewing Ave bridge over the Calumet River $100.0M (p. 76), 95th St bridge $43.0M (p. 73), "Various locations in Chicago" $50.0M state-funded (p. 84), Canal St viaduct Harrison to Taylor $23.88M (p. 75). These are IDOT "estimated cost" for IDOT's fiscal year 2026 (Jul 2025 to Jun 2026), whole-project phase costs, and they are **not** split by City budget line, so they are not boxes. The Multi-Year Program (`idot_myp_fy26_31.pdf`, 1,249 pages, text now in `raw/cdot/idot_myp_fy26_31.txt`) has only narrative mentions of Chicago. Its district project lists are on public.powerdms.com and were not pulled (see gaps).
5. **CDOT FFY2024-2029 STP Program** (updated 2026-02-10), https://cmap.illinois.gov/wp-content/uploads/CDOT_2025-2029-STP-Program-20260210.pdf, page 1. Its FFY2026 total is $76,775,306 for six projects. It is cited as a side fact. It agrees with the TIP: Canal St Harrison to Taylor $40,123,000, Signal Controller #1 $4,000,000, Bridge Painting #11 $2,480,000.
6. **City CIP 2025-2029** (`data/city_capital_2026.json`, PDF page 168 for State/Lake, project 40492, total $495,647,401).
7. Contracts and payments (`contracts_all.csv`, payments dataset `s4vu-giwb`, verified live) for State/Lake.

## State/Lake Loop Elevated Station (the $329.8M piece)

What is public, and where it stops:

| Fact | Amount | Source |
|---|---:|---|
| Reported total project cost (CDOT says over 90% federally funded; was $180M in 2021, $75M in 2017) | $444M | Chicago Sun-Times 2025-12-04; Block Club 2025-08-20 |
| Construction contract 283596, F.H. Paschen S.N. Nielsen & Associates, original award 2025-01-15 | $444,347,400 | City contract search, https://webapps1.chicago.gov/vcsearch/city/contracts/283596 |
| Same contract, modification 2 on 2026-06-30 (current award $548,215,560) | +$103,868,160 | same page |
| Paid to that contractor in 2025 (7 payments) | $51,072,112 | payments dataset, our deduped copy |
| Paid in 2026 through 09/28 (9 payments) | $37,295,302 | same |
| Design engineers: TranSystems contract 100786 (original $9,999,991, revision 1 $1,350,000) | | contracts dataset |
| CIP 2025-2029 total, all funds | $495,647,401 | CIP p. 168 |
| CMAP TIP 01-02-0030 total programmed, all in prior years, **$0 in FFY2026** | $481,925,718 | eTIP |
| FTA award IL-2016-002 obligated | $414,620,572 | USASpending |

Children of the $329.8M piece (all `gov_estimate`, unspent = budget minus expended, from ledger records for project D1209): Surface Transportation Program money $102,140,573 (older 2025-06-01 extract only, nothing spent then, equal to CDOT's own FFY2024 STP programming of $77,140,573 plus $25,000,000 redistribution, to the dollar), Congestion Mitigation and Air Quality money $59,516,918, STP $18,190,500, Carbon Reduction $15,000,000, direct FTA CMAQ $7,334,548. Together $202,182,539. The remaining **$127,618,674 is shown as not itemised.** Caution: the $102.1M record exists only in the 2025 extract, so it may have been re-coded or paid since. It is flagged in the box note as an upper bound.

**Gap, stated plainly:** no public cost breakdown of the station, track, utilities or contingency was found. The bid book (spec 1269715, Book 2, 90 pages, cached) has a Schedule of Prices (PDF pages 22 and 23) with 15 work items, but only four carry a number, the City-fixed allowances (track flagging $3.5M, track access $3.5M, regulated-substance disposal $0.25M, utility service $0.25M, together $7.5M). The other 11 are bidder lump sums (civil, structural, architectural, plumbing, mechanical, electrical, communications, track, traction power, signal and train control, mobilization) and the winner's prices are not public. We posted the allowances as side facts. The City bid-tabulation search (https://webapps1.chicago.gov/vcsearch/bidtabs, driven with its CSRF form) returned "No Records Found" for specification 1269715, by number, description, bidder and date. The statelakestation.com page carries no numbers. The CTA does not publish a separate line. The best partition available is by funding source, which is what the boxes show.

## Other reserve lines (coordinator handover)

Method: each ledger row (2026-05-31) is placed on one reserve line when its department and grant match (ALN, or fund codes for CDOT lines with no ALN) and the row maps to a single line, using the ledger's composite fund code when several lines share a department and ALN. A row that could belong to several lines is not placed. If the matched projects add up to more than the reserve, they are **not** boxes (we cannot say which part of each project the reserve covers) and become side facts through a `side_only` split. This avoids the over-count that the earlier `named_items` list had (for example one HOME project list was counted on three reserve lines, $71.2M of projects against $48.5M, $29.0M and $1.7M of reserve).

Boxes created: Housing HOME 925F $15.7M of $48.5M (one project, HOME FY25), CDOT 925L sister agency/private $18.7M of $23.7M (28 projects), INFRA $19.1M of $19.1M (Archer at Kenton, CREATE GS09), HOPWA $9.1M of $18.8M, Fleet EPA clean vehicles $7.3M of $7.3M, FHWA research $6.0M of $6.0M, Reconnecting Communities $2.0M of $2.0M, and 12 smaller lines. Side-only (projects exceed or could sit on several lines): HOME 925C and 925P, CDC strengthening public health (925C), CDC ELC, COPS hiring, DCEO state highway (925S 280M, matched $10.1M against a $7.2M reserve), ARPA CDOT, and others. Airports (dept 85) were skipped as instructed. Lines with no ledger record stay at grant level: Superfund $43.2M, UASI, Finance General $31.0M, Senior Center $16.0M, aviation fuel tax (airports).

Duplicate-name caution: Columbus Ave GS11, Canal Street viaduct, Archer at Kenton, OPC South Lakefront and Montrose appear on several reserve lines because several funding sources pay each project. Within one line a project appears once. Across lines they are different money.

## Findings that change earlier numbers

1. The existing `named projects, unspent budget` piece of $121,122,530 was built from **both** ledger extracts at once (2026-05-31 gives $114,253,868 and 2025-06-01 gives $6,868,661, sum $121,122,529). Its children are now shown, and only one old record is also in the new extract. The research note in `grants_capital.md` says $77.7M attributable for this line, the tree piece says $121.1M, so the tree piece is the larger. The children add to the piece within $0.47.
2. The IDOT reserve `named_items` list (42 items, $123.6M) mixes in the Illinois Competitive Freight Program (fund F0W23, federal ALN 20.205, $36.6M unspent). Those rows are federal highway money already counted in the FHWA reserve, so here the state line uses fund F0L98 only: **$87.0M** attached, not $123.6M.
3. The TIP lists far more state-type money in FFY2026 ($200.7M) than the $117.4M state construction line. Only Calumet River Bridges ($112.2M, State Match, FFY2026) fits inside. The rest is a side fact. Matching is by fund type and could be wrong.
4. The federal 0540 line ($451.6M) is $218.1M above what the TIP programs for federal-highway funds in FFY2026. That gap is the realistic maximum of what the TIP can explain. Candidates for the rest are the carryover of multi-year awards, other federal funds (Safe Streets, Reconnecting Communities, Bridge Investment Program), and phases the TIP shows as prior-year costs.

## Gaps: what was tried in the second pass, and what is still open

**Federal highway money with no 2026 TIP project, $218,126,886 (925F 281S 0540). Still not itemised.** Three public views of 2026 federal road money for Chicago exist and none adds to the line:

| View | Amount |
|---|---:|
| City ordinance line (Summary G anticipated 2026 grant $452,121,000, p. 606) | $451,646,229 |
| CMAP TIP, federal-highway funds programmed in FFY2026 (the 14 boxes) | $233,519,343 |
| IDOT FY2026 annual program, 19 Chicago local-system projects with federal-type funds | $291,533,000 |

The IDOT figure includes $143,000,000 for two Calumet River bridges (Ewing Ave $100.0M, 95th St $43.0M, IDOT PDF pp. 73 and 76) that IDOT labels discretionary grant. They fit the federal Bridge Investment Program grant 693JJ22440000Y17FILJ498286, which USASpending shows awarded to **IDOT** ($144,000,000 federal, $145,500,000 match, $289,500,000 total, $34,274 spent, signed 2024-08-29). The grant text names exactly those four Calumet bridges. We cannot tell how much of it runs through the City's 925F line, so it is a side fact and not a box. A box would assume the City books money that IDOT holds. IDOT's multi-year program (October 2025, PDF pp. 336 to 361, file identical to the IDOT publication) adds Chicago local projects in 2027 to 2031 (for example Jeffrey Dr $60.0M, 100th St bridge $39.2M, California Ave bridge $26.7M, Ogden Ave $19.9M). They are side facts, labelled as later years. The multi-year program lists IDOT's own project numbers, so the $218.1M cannot be tied to named jobs from it either. I also checked the City's budget book text (660 pages cached): it has no narrative on what the $452.1M pays for.

**The rest of the State/Lake award, $127,618,674. Still not itemised, and no better split exists in public data.** What was added this pass: the award's obligation history by FTA fiscal year (USASpending, total $408,620,572 in account-level records against $414,620,572 on the award page), which shows the $102,140,573 record that exists only in the 2025 ledger extract is a real obligation posted in March 2025. FTA then de-obligated $55,300,000 and $9,774,524 and obligated new amounts in April and November 2025, so the older ledger record may be a superseded slice of the newer ones. Corrected earlier statement: the bid book **does** contain a Schedule of Prices (PDF pp. 22 and 23). Four of 15 items are City-fixed allowances (track flagging $3.5M, track access $3.5M, regulated-substance disposal $0.25M, utility service $0.25M, together $7.5M) and are posted as side facts. The other 11 items (mobilization, civil, structural, architectural, plumbing, mechanical, electrical, communications, track, traction power, signal and train control) are bidder lump sums. The City's bid-tabulation search (https://webapps1.chicago.gov/vcsearch/bidtabs, driven with its CSRF form) returned "No Records Found" for the specification number, description, bidder and date window, and the bid book has no engineer's estimate. So the $444M cannot be split by trade from public files.

**Unplaced lines, resolved this pass.**
- **925F 281K 0140 Safe Streets and Roads for All, $20,928,000: now a box.** The TIP programs $20,927,748 of Safe Streets money for Ogden Avenue, Pulaski to Roosevelt (project 01-22-0043), $252 below the line. It is the only Safe Streets grant in the ordinance. The TIP puts the money in FFY2027 (Oct 2026 to Sep 2027) while the City budgets it in 2026. The TIP's other Safe Streets project, North Avenue Kostner to Kedzie, $20,010,000 (01-23-0005), is a side fact. The USASpending award for this grant could not be found by name or ALN 20.939 (no award to the City, only to CMAP and East Chicago), so the match rests on the amount.
- **925F 281U 0540 FTA formula, $10,000,000: stays one box, with a note.** No project list is public. The Pedway job ($3,236,583 of CMAQ) is posted as a fact only.
- **925S 280M 0540 DCEO, $23,600,000: stays one box, with a note.** The ledger shows DCEO road projects only as small ward-level jobs ($16.2M budget in total) and the TIP has no DCEO fund source.
- Still unplaced and small: 925F 281N and 280G ($1,000,000 each, NHTSA safety).

**IDOT District 1 project lists.** The District 1 local project list is inside the multi-year program PDF already cached (pages 336 to 361 for Chicago local highways), and the annual program covers IDOT's fiscal year 2026. Both are used as side facts. The separate PowerDMS copies (public.powerdms.com/IDOT/documents/3179143 and the District 1 documents) were not fetched because they carry the same project list. State-system projects in Chicago (I-290 bridges, Kennedy, I-55, I-94) are IDOT's own spending and are not City appropriations, so they were not matched to City lines.

**Other open items**
- TIP "Local Funds" ($368.5M in FFY2026, including Division Street $70.0M, Elston-Armitage right of way $75.3M, Burley Avenue $30.0M) is City money and sits in capital and bond lines, not on these grant lines.
- The TIP FY2026 column is the program as adopted, not obligations. Obligated and spent amounts by TIP project are in IDOT's e-Project and FHWA FMIS and were not available.
- USASpending sub-awards: an earlier pull (`raw/leaves/usa_sub.json`) found 0 rows to the City for ALN 20.205 and 20.507.
- Search engines were blocked for part of this pass (anti-bot page), so a search for FTA grant line-item data (TrAMS) and CTA board documents was not completed. The FTA TrAMS activity line items for IL-2016-002 would be the best remaining source for a station, track and utility split.

## Reproduce

```
python3 scripts/cdot_etip_fetch.py 3488 16811 cdot   # about 4 minutes, 108 project JSON files
python3 scripts/cdot_build.py
python3 build/city_tree.py                            # expect: cdot_projects.json 51 applied, 0 skipped, OK
```
