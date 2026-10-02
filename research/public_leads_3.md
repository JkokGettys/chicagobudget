# Public leads 3: HUD DRGR, Illinois EPA loans, EMMA, CPS special education tuition

Date of work: 2026-10-02. All sources are public. No FOIA. Raw files are in `raw/pl3/` (gitignored, so rerun the scripts to rebuild them). Build stays exact: `bash build/build_all.sh` passes to the cent (City $16,842,553,003.00, CPS $10,253,327,463.68, Parks $637,580,350.00) with 0 skipped from the new files. The 4 `why_fixes.json` skips in the City build were there before this work (checked by stashing my changes).

## Result in one table

| Lead | What was found | What moved in the tree |
|---|---|---|
| 1. HUD DRGR, CDBG-DR sewer and stormwater | DRGR's public site has no Chicago activity list for the 2026 grant. The City's own posted documents (hearing deck, HUD quarterly report) have the project counts | Four boxes ($380.3M) now use the City's published counts, replacing the "miles x $8.5M" proxy. Admin/planning line gets the DRGR activity budgets as side info |
| 2. Illinois EPA loans (Water $39.7M and $14.1M, Sewer $32.6M and $11.7M) | Loan-by-loan tables (rate, last year, balance) exist. **No document prints each loan's 2026 payment** | No new boxes. Loan tables and published 2026 totals attached as side info to all four lines |
| 3. EMMA | Reachable with headless Chrome, but the site's Terms of Use forbid automated access | Nothing. Stopped, and deleted the script and captures |
| 4. CPS private special education tuition leftover ($26.6M) | The State Board of Education's directory of nonpublic special education schools matches 23 more providers in the CPS payments file | $11,858,311.70 moved out of the $26.6M leftover into 23 provider boxes. Leftover is now $14,744,848.46 |

## Coverage before and after

Command: `cp data/budget.db raw/treeaudit2/budget_snapshot.db && python3 scripts/treeaudit2_coverage.py` (the table's "previous" column is the older audit, so use the two "now" columns). Before was run on the build at the start of this task, after on the final build. Saved in `raw/treeaudit2/coverage_before_pl3.md` and `coverage_after_pl3.md`.

| Gov | Leaves before | Leaves after | Under $1M before | after | $10M or more before | after |
|---|---:|---:|---:|---:|---:|---:|
| City | 11,803 | 11,804 | 42.0% | 42.2% | 44.4% | 44.2% |
| CPS | 20,118 | 20,141 | 57.6% | 57.6% | 27.3% | 27.1% |
| Parks | 6,124 | 6,124 | 48.5% | 48.5% | 17.5% | 17.5% |

Honest reading: small gains. The audit counts a "count x rate" leaf as under $1M only when the rate is under $1M, and counts every other leaf by its own dollars. So only the sewer cleaning line ($29.7M at $14,160 a block) left the "$10M or more" bucket. The sewer, wing storage and alley boxes are now named by the City's own counts but are still single boxes of $62M to $221M. The point of those splits is that the numbers are the City's, not ours. Box counts: City 15,374 to 15,378, CPS 24,870 to 24,894.

## 1. HUD DRGR (https://drgr.hud.gov/public/)

**What the site is.** A JavaScript page that calls a plain public JSON service, `https://drgr.hud.gov/DRGRPublicService/rest/publicService/` (found in `js/drgr-public-config.js`). No browser was needed. Useful calls: `searchRecipients?query_string=Chicago&start_at=1&recipient_type=direct`, `directRecipient/197` (Chicago, IL), `searchRecipients?associated_recipient_id=197&recipient_type=sub&start_at=1`.

**What it has for Chicago (grantee id 197), saved as `raw/pl3/drgr_chicago_197.json`:**

| Grant | Year | Amount | Action plan on DRGR | Performance reports on DRGR |
|---|---|---:|---|---:|
| B-13-MS-17-0001 (Disaster Recovery CDBG, P.L. 113-2) | 2016 | $63,075,000 | yes | 15 |
| **B-25-MU-17-0001 (P.L. 118-158)** | **2026** | **$426,608,000** | **none posted** | **0** |
| NSP1, NSP2, NSP3 (housing, 2009 to 2011) | | $55.2M, $98.0M, $16.0M | yes | 37, 32, 26 |

So the 2026 flood grant has no activity list on the public portal. The "Responsible Organization Activities" report (`getRecipientActivities`, POST with `download_token`) returned a server error for the Chicago organizations, and every sub-recipient search showed `programs: []`. Dead end on DRGR itself.

**What worked instead.** The City's CDBG-DR page (https://www.chicago.gov/city/en/depts/obm/provdrs/grants/svcs/CDBG-DR.html) links the DRGR quarterly report and a public hearing deck:

- **HUD DRGR Quarterly Performance Report, Apr 1 to Jun 30 2026** (first report, submitted Aug 4 2026): https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/B-25-MU17-0001_QPR_Q2_2026.pdf . It lists the projects and activities with their budgets:
  - Administration (activities 01 and 02): $21,330,400 total budget. Activity 01, City staff, $7,641,172 (spent $281,544.33). Activity 02, "Planning & Admin - Contractor", responsible organization GUIDEHOUSE INC., $13,689,228 (spent $1,577,819.10). These tie to the Action Plan's $21,330,400 administration cap.
  - Public Services (Disaster Relief Assistance Program) $15,000,000, nothing spent.
  - Infrastructure and Mitigation: the whole **$390,277,600** is budgeted under one project, 882821 "New Sewer Main". The other activities (permeable alleys, plazas, grid cleaning, wing storage) show **$0 budgeted** and no activities yet. DRGR therefore has no per-activity infrastructure budget as of June 30 2026, and nothing drawn.
- **CDBG-DR Public Hearing Deck (May 2025)**: https://www.chicago.gov/content/dam/city/depts/obm/supp_info/CDBG/cdbg-dr/CDBG-DR%20Public%20Hearing%20Deck_Website.pdf . Page 11 gives federal plus local dollars by program and pages 14 to 18 give counts:

| Program (deck p.11) | Federal | Local | Total | City's count (pp.14-18) | Ordinance line (federal) |
|---|---:|---:|---:|---|---:|
| Sewer mains | $226,341,802 | $23,068,233 | $249,410,035 | 104 blocks of local sewer upgraded, 52 blocks of trunk sewer evaluated | $221,342,000 + $5,000,000 trunk |
| Wing storage | $62,096,736 | $15,524,184 | $77,620,920 | 12 units | $62,097,000 |
| Grid cleaning | $29,735,732 | none | $29,735,732 | 2,100 blocks cleaned | $29,736,000 |
| Permeable alleys | $67,103,330 | $13,420,670 | $80,524,000 | 60 alleys | $67,104,000 |
| Permeable plazas | $5,000,000 | none | $5,000,000 | 5 to 6 plazas | $5,000,000 |

The ordinance lines match the deck within $198 to $670 per line (the ordinance rounds to the thousand). The deck is the May 2025 draft, and the final plan moved $15M to the Disaster Relief program, so I used only the per-program figures that still tie to the ordinance.

**Tree changes (`scripts/public_leads3_drgr_build.py` writes `data/splits/city/drgr_cdbgdr.json`):**

- Local sewer line construction $221,342,000: old proxy was "26.0 miles x $8.5M" (Action Plan Table 25, which is the plan's *need* estimate for 71.4 miles, not the program). Now "104 blocks of new local sewer main", $2,128,288.46 each, plus a $0.16 rounding box. The deck (p.14) says the sewer job also includes resurfacing the streets and replacing about 2,500 to 3,000 lead service lines.
- Wing storage $62,097,000: 12 tanks at $5,174,750 (exact). Permeable alleys $67,104,000: 60 alleys at $1,118,400 (exact). Sewer cleaning $29,736,000: 2,100 blocks at $14,160 (exact).
- All four are basis **proxy**: the dollars are the City's, the equal share per unit is ours, and the deck says final projects, locations and amounts are still subject to engineering. The note on each box says so.
- Trunk sewer ($5M, 52 blocks evaluated), plazas ($5M) and the OBM admin contract line ($19.6M, Guidehouse and others) get notes and side info only, because splitting a $5M design line by an invented unit would be made up.
- `data/leaves_grants.json` and `scripts/leaves_grants.py` no longer carry the miles proxy.

**Leftover from this lead:** the "$19.6M planning" box is the OBM contractor line. The DRGR activity budget for the contractor ($13.7M) is for the life of the grant to 2031, so it is side info, not a box. The Action Plan itself says the City does not plan to spend CDBG-DR money on "planning" (p.73).

## 2. Illinois EPA state revolving fund

**Sources fetched:** the IEPA SRF pages (https://epa.illinois.gov/topics/grants-loans/state-revolving-fund.html and its wastewater and drinking water loan pages), the SFY2024 and SFY2025 annual reports, and the FY2026 and FY2027 intended use plans (IUP) for both loan programs. All HTTP 200, held in `raw/pl3/iepa/`.

**What they hold:**
- Annual reports list loans signed each year. The SFY2025 drinking water report lists Chicago loan L175652 ($60,000,000, signed 2025-06-30, watermain) and seven lead service line loans of about $2M each. The wastewater report has no Chicago loan lines.
- The IUPs list the *next* loans the City asked for, for example L17-6152 sewer improvements $63,030,662 and L17-7070 sewer lining $63,000,000 (FY2026 list), and L17-7069 $63,775,000, L17-7072 $12,000,000 and L17-5801 $14,000,000 (FY2027 list). These are new borrowing plans, not repayment schedules.
- None of the IEPA documents prints a repayment schedule for an existing loan.

**The City's own bond papers are the better source.** They list every existing loan with rate, last year and balance:
- Water: 2026ABC Official Statement p.34, 24 loans, $457,541,223 owed on 2026-04-01 (https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf). p.36 gives one number for all of them in 2026: **$42,045,045** of principal and interest, and the whole schedule to 2044.
- Sewer: FY2025 financial statements pp.41-42, 22 loans, $462,292K owed on 2025-12-31 (https://bondlink-cdn.com/1345/Sewer-Fund-Financial-Statements-2025.vcXRD2uoM.pdf). The 2024B Official Statement p.24 gives **$32,533,630** for 2026 (loans closed by mid 2024).

**Why there are no per-loan boxes.** I tested whether a standard payment formula (equal payments every six months from the printed balance, rate and last date) reproduces the published Water totals. It comes within 0.4% to 1% for 2026 to 2037 ($42.37M modelled vs $42.05M published for 2026) but drifts to 17% to 21% off by 2043 and 2044, so the City's real schedules use some other terms. Per-loan payments from that model would be invented numbers, so I did not use them. The test is kept in `raw/pl3/srf_model_test.py`.

**Tree changes** (`scripts/public_leads3_srf_build.py` writes `data/splits/city/iepa_loans.json`, side info only): on the four loan lines, a note and side rows with the aggregate 2026 figure and each loan's rate, last year and balance (24 Water loans, 22 Sewer loans). The notes also say the Water interest line covers the $141.3M WIFIA federal loan and a PNC credit line, and that the two Sewer lines ($44.4M) are larger than the $32.5M in the 2024 statement, probably because loans closed since then are not in it (the City had signed $166.5M more). That last point is my inference and is worded as "probably".

Moved: $0 into boxes. The four lines ($98.1M) are still single boxes of $10M or more, but they now carry the full loan list. A true split needs each loan's repayment schedule. I did not find one in any public source I could reach (the loan agreements themselves were not located).

## 3. EMMA (https://emma.msrb.org/)

What I did: used a throwaway headless Chrome (temp profile, same pattern as `scripts/tableau_capture.py`) and loaded the home page (clicking its cookie Accept button) and one security page, before I had read the terms. Both loaded (HTTP 200). The security page forwards to the **MSRB Website Terms of Use** (last updated 2026-01-01), which say you may not "use ... any data mining, crawling, 'scraping', robot or similar automated or data gathering or extraction method ... or otherwise systematically download or store Content", nor "bypass or circumvent ... measures intended to limit or prevent access". It also bans optical character recognition on imaged content.

What I did not do: I did not go further. Driving EMMA with a script to collect official statements would break those terms, so I stopped, deleted the capture script (`scripts/emma_capture.py` was never committed) and deleted the captured pages.

One more disclosure: before reading the terms I also made two plain `curl` requests, one for a single official statement PDF that an earlier session had already listed (HTTP 200, 8.4 MB) and one for a security page (HTTP 200, 113 KB), to see whether EMMA works without a browser. I discarded both files unread. That is three small automated requests in total, which I should have checked against the terms first. Earlier sessions also left `raw/pensions_debt/emma/` and `raw/grants_tree/emma.cookies` from similar probes. Nothing in the tree comes from EMMA.

What the "Other bonds" boxes would need, and legitimate routes:
- EMMA offers a paid subscription and a data feed (EMMA Dataport), which are the permitted ways to get data in bulk. Not used.
- The City's own BondLink pages (already used, `scripts/bonds_fetch.py`) hold the official statements and the audited financial statements. I re-listed all six issuer pages: besides official statements they carry only financial statements, budgets, monthly revenue reports and the CIP, no debt service schedules by series.
- A person can read a series' page on EMMA by hand. That is allowed and is the practical route for the nine "Other bonds" boxes.

## 4. CPS private special education tuition (https://api.cps.edu/procurement/Supplier/GetSupplierPayments?reportyear=2026)

The API returned 4,631 payment rows totalling $3,557,066,716.48. That is identical row for row to the file already held (`raw/cps/cps_supplier_payments_FY2026.json`), so there was no new data in the feed. The gain came from a better way to choose which vendors are private special education schools.

**New approach.** The earlier build picked 11 providers by hand from their own websites. I matched every vendor name against the **Illinois State Board of Education's 2025-26 Directory of Educational Entities, sheet "Non Pub Spec Ed"** (943 approved nonpublic special education entities; https://www.isbe.net/Pages/Data-Analysis-Directories.aspx, file `2025-26-Directory-Ed-Entities.xlsx`). 48 vendor names matched. Script: `scripts/public_leads3_sped_isbe.py`.

Of the 48:
- 8 were already boxes (Menta, Easterseals, Shankman, Cove, Elim, Acacia, Shrub Oak, Soaring Eagle).
- 10 are agencies that run many services (UCAN $5.9M, Esperanza $3.2M, Jewish Child and Family Services $3.0M, Rush University Medical Center $1.0M, Thresholds, Orchard Village, Little City, Family Guidance Centers, Maryville Academy, Anixter Center). The directory lists a school program, but most of CPS's payment is probably for other services, so I **left them out** on purpose.
- 6 looked like a different organization with a similar name (Discovery Education, Q & A Associates, Fusion Learning, NeuroRestorative in Houston, Walter Lawson Children's Home, Alexander Graham Bell Montessori in a different town), left out.
- 1 was dropped by the city check (Cherry Gulch, city spelled "Emmet" vs "Emmett", $10,212, left out to stay safe). That makes 8 + 10 + 6 + 1 = 25 left out.
- **23 kept**, $11,858,311.70, led by PACTT Learning Center $1,524,829.89, Anderson Center for Autism $1,163,225.84, Keshet $1,133,497.19, Merlin Day $1,039,434.82, Brain Box $984,348.21, Specialized Education of Illinois (New Hope Academy) $887,455.40. Each is a "paid so far" box taken out of the old "Tuition budgeted but not matched to a payment shown here" box.

Tree: that box was $26,603,160.16, now **$14,744,848.46**, so the line holds 11 + 23 provider boxes. All 23 new boxes are under $2M each. Same caveat as before: payments are by vendor, not by budget line, so a total can include other contracts with the same organization. Written to `data/splits/cps/sped_isbe.json`.

Not done: the leftover is still above $10M, and the remaining CPS payment file has no marker for special education placements, so I made no further match. The 4,353 small vendors under $1M ($223.7M in the earlier audit) are not all schools.

## Dead ends, in one list

- DRGR: no 2026 action plan or activity list on the public portal, activity report errors out, DRGR shows the $390.3M under one activity.
- IEPA: no per-loan repayment schedules anywhere public. Annual reports and IUPs list new loans only.
- EMMA: terms forbid automated access. Nothing taken.
- BondLink (City): no debt service by series for the nine "Other bonds" boxes.
- CPS API: same data as already held.

## Suggested next steps

1. A person reading EMMA series pages by hand for the nine "Other bonds" boxes (about $395M), or the City Finance Department's debt service schedule by series if it would share one without FOIA.
2. Watch the DRGR report each quarter (next due after Sep 30 2026). Once the City sets up infrastructure activities, their budgets replace the equal shares in `data/splits/city/drgr_cdbgdr.json`.
3. Look for each IEPA loan's repayment schedule in the loan agreements or the City's continuing disclosures. I did not find them, and I have not checked whether they are published.

## Reproduce

```
python3 scripts/public_leads3_drgr_build.py     # needs raw/pl3/hearing_deck.pdf and qpr_q2_2026.pdf only for reading, numbers are typed from them
python3 scripts/public_leads3_srf_build.py      # needs raw/bonds/txt/water_2026ABC_OS.txt and sewer_FS2025.txt
python3 scripts/public_leads3_sped_isbe.py      # needs raw/pl3/cps_supplier_2026.json and isbe_dir_2526.xlsx
bash build/build_all.sh
```
