# Parks and City misc lines: what was found, what was attached, what is still missing

Built 2026-10-01. Script: `scripts/parksmisc_build.py` (writes `data/splits/parks/misc.json` and `data/splits/city/misc.json`, nothing in `build/*.py` was edited). Cached downloads are in `raw/parksmisc/` (gitignored, the script re-fetches the settlements spreadsheet if missing). Verification: `python3 build/parks_tree.py` gives "31 applied, 0 skipped", 0 problems, total $637,580,350.00. `python3 build/city_tree.py` gives "7 applied, 0 skipped", 0 problems, total $16,842,553,003.00.

Effect on depth: Parks boxes of $10M or more fell from 25.9% to 17.5% of dollars (the 2023C, pension and bond boxes now end in pieces under $10M, or stay whole where noted below).

No names of individuals appear anywhere. Settlements are summed by department and type of case. A scan of both split files for "Last, First" patterns found only document titles.

## 1. What was attached

| Line | $ | What the tree now shows | Basis |
|---|---:|---|---|
| Parks pension shortfall | 53,913,236 | 6 boxes by who the fund pays: retirees (2,125) $44.57M, surviving spouses (574) $7.62M, children (2) $1,355, disability $210K, death benefits $111K, refunds $1.40M | proxy |
| Parks bond series (10 of 25 with both principal and interest) | e.g. 2023C 22,264,000 | principal $19,365,000 + interest $2,899,000, plus side facts for 26 series (original size, still owed, rate, years) | tied |
| Parks Soldier Field, harbors, golf, water and sewer, electric | 36.3M, 16.6M, 8.5M, 16.7M, 14.8M | no boxes, notes and side facts only (sections 3 and 4) | side_only |
| City Police judgments 0931 | 82,558,000 | 2026 settlements paid so far, 6 boxes, plus a negative "paid beyond the budget line" box of -$151,741,709 | paid_to_date |
| City Fire 0931 | 12,000,000 | 4 boxes, $3.26M paid so far | paid_to_date |
| City Finance General 0931 (Corporate) | 40,785,387 | 4 boxes, $4.64M paid so far | paid_to_date |
| City Water and Sewer fund 0931 | 6.8M, 383K | one box each | paid_to_date |
| City Emergency Medical Transportation 9222 | 124,725,187 | note and side facts only | side_only |
| City CTA share of transfer tax 9205 | 62,789,053 | note and side facts only | side_only |

## 2. Pension (Park Employees' Annuity and Benefit Fund)

Method is the same as the City funds: the District's payment is shared out by each benefit group's share of the dollars the fund paid in 2025. It is labelled proxy on every box, and the note says the District's payment is not the same as benefits paid (the fund also has member contributions and investment income).

2025 benefits and refunds by type (fund annual report, statement of changes, PDF p21): retirement $72,365,184, spousal $12,368,913, child $2,200, disability $341,323, death $180,500, refunds $2,267,404. Total $87,525,524, which equals Exhibit F of the Segal valuation (PDF p39). Administrative expense ($1,976,961) is excluded from the shares.

Counts at 12/31/2025: 2,125 retirees (average $34,793, total in force $73,935,252), 574 surviving spouses (average $20,655, total $11,856,109), 2 children, 3,251 active (average pay $58,371), 206 inactive vested, 5,530 inactive owed a refund (valuation Exhibits A and D, fund report PDF pp148 to 157). The fund report counts 574 spouses and the valuation 576 "beneficiaries" (574 spouses plus 2 children).

The $53.9M is the part of the $63.3M payment above the $9.4M employer normal cost. The fund's own policy asks for $88,904,199 in 2026, $25,571,787 more than budgeted. Statute P.A. 102-0263 sets the real payment and a 2057 goal for 100 percent funded.

Not found: a split of the benefit dollars by tier (Tier 1, 2, 3) or by years of service. The fund reports only counts and averages for new retirees by service band (fund report PDF p162).

## 3. Soldier Field, harbors, golf and other managed venues

None of these could be split into boxes, because the District publishes no operating budget for any contractor. Everything below is attached as side info or a note.

**Soldier Field, $36,292,135.** The budget book (PDF p45, narrative) says the stadium is projected at $62.9M gross revenue and $36.3M gross expenses in 2026. Revenue accounts (PDF p54): event and stadium $48,955,346, other income $6,907,552, Bears/NFL contribution $7,036,456, total $62,899,354 against $56,838,270 budgeted for 2025. The FY2025 ACFR (PDF p94, $ thousands) shows $74,567 actual against $56,838 budget, a $17.7M favorable variance, and says contractual services ran $7M over budget because of the extra events (PDF pp35, 40).

*Management agreement.* The Board approved a new 10-year SMG contract on 2013-02-13 for Soldier Field, McFetridge and the Devon and Kedzie ballpark. Reported terms: management fee $600,000 to $684,000 a year, $2.5M contribution from SMG, $1M marketing fund (Chicago Tribune, 2013-02-13). Legistar matters 2985 (2008) and 3196 (2014 scoreboards) carry no text or attachments on the API, and the contract itself is not public. The Bonfire contract library lists P-12035 as pending 2027-04-01 to 2028-03-31 with value $0. The 2023 Park District budget accounts show a separate account 623095 "Management Contract Incentive Fee" of $1,183,983 in 2026, so some fees may be outside the 626045 line. **I could not find a published fee schedule current to 2026 and I could not determine what part of the $36.3M is the fee. The press-reported fee would be under 2 percent of the line.** Fee schedules would require the contract (FOIA, see `research/park_vendors.md` section 6, item 4).

*Bears lease* (Permit and Operating Agreement, Marquette Sports Law summary of sections 3.1, 14.1, 19.2, 27.1): term through the 2033 season, annual facility fee $4,700,000 for 2004 to 2007, then raised every fifth anniversary of 1/1/2008 by 50 percent of the CPI change, plus a separate parking allotment fee. The District pays routine maintenance and insurance. The ACFR (PDF p78) says the Bears paid $7.0M in 2025 and the Chicago Fire soccer club $3.0M (lease ended 2025). Press reports put break-the-lease cost at about $84M to $90M (Sun-Times 2021). The 2019 Fire agreement is Board action 19-1086-0911. I did not find published lease amendments.

*Food service* (separate contract P-23013, Levy Premium Foodservice, action 24-1058-0410): $12M contractor capital, 3 percent of gross receipts to an equipment reserve, 1 percent of District concession sales to a community fund, District commission of 48 percent on the first $13M of concessions, 50 percent to $20M, 52 percent above. This is money to the District, not part of the 626045 line.

**Harbors, $16,580,506.** Budget book: gross revenue $31.5M, gross expenses $16.6M, harbor-backed debt service $10.6M (narrative PDF p46). Harbor fees $31,527,107 budgeted (PDF p54), $31,029K received in 2025 (ACFR p50). Operator Westrec under Board action 14-2148-1112 (2014-11-12), specification P-14010, the only Legistar attachment being a minority-business form. The budget book prints the 2026 harbor fee schedule and "Managed by Westrec SMI" (PDF pp263 to 265). No management fee or operating budget found.

**Golf, $8,490,697.** Budget book: gross revenue $9.9M, expenses $8.5M. Contract P-24001 (Indigo Sports, Troon), action 24-1125-0911: fee $1,275,000 a year (10 percent, $127,500, held back until a review), $9M contractor capital over ten years, $25,000 a year community fund (exhibit text in `raw/parks/legistar_golf_exhA.txt`). The fee is about 15 percent of the line, and the rest is operator cost the District does not itemise.

Other venues (Maggie Daley fee schedule, McFetridge, Beverly/Morgan Park, Addams, Gately, MLK) were already attached in `research/park_vendors.md` and are untouched.

## 4. Utilities

**Water and sewer $16,707,439 and electric $14,805,112: no per-park usage is published.** Checked: the District's budget book, sustainability report (district-wide percentages only), the Ethics vendor payment lists (2019 to 2022, no water payee, electricity under Direct Energy, ComEd, Constellation-type suppliers, already attached), the City payments file (no District water bills), and the City energy benchmarking dataset (`xq83-jr8c`). Benchmarking has electricity and gas for only a handful of District buildings, none later than 2020 except Henry Crown Field House (a University of Chicago facility) and nothing for water. Soldier Field reported 108,529,613 kBtu of electricity and 16,899,451 kBtu of gas for 2015 only, with no dollars. A split would be invented, so none was made.

What is attached: City water rate $37.18 per 1,000 cubic feet from 2026-06-01 (up 1.85 percent), sewer charge 100 percent of water, plus a water-sewer tax (rate not found on the City's pages), total utilities $37.6M or 5.9 percent of the budget, electricity up $823,180, hedging savings about $1.5M a year (budget book PDF p60). The water and sewer line equals its 2025 budget exactly.

## 5. Bond series

Principal and interest come from ordinance Appropriation M (budget PDF p253), which ties exactly to the budget's principal line. Interest is $1.1M below the operating line, already shown as "Interest paid outside the bond schedule". Ten series have both principal and interest in 2026 and are split. The other 15 have interest only, so no split exists. Side facts come from ACFR Note 8 (PDF p77): original size, balance at 12/31/2025, rate, years. Series 2023C: $93,780K original and outstanding, 5 percent, 2026 to 2040, this year $19,365,000 principal plus $2,899,000 interest. 2016A shows $2,615K still owed but pays $2,890,000 of principal in 2026, because of the defeasance in December 2025 of $56,675K of it (ACFR p77), so the two do not conflict.

## 6. City: Emergency Medical Transportation (9222), $124,725,187

**I could not establish what this line pays for, and no City document says.** The budget book lists it under Finance General "Purposes as Specified". The existing tree sentence "this pays for ambulance trips and their billing" is not supported. Facts found:

- The ambulance billing vendor (Advanced Data Processing, contract 54815, Department of Finance, awarded 2018-04-13 for up to $17,572,176, fee 3.95 percent of collections at award down from 7 percent) was paid $7,713,575 in 2025 and $2,780,182 in 2026 to 9/28. That is about 6 percent of this line, and those payments sit under the Department of Finance, not Finance General.
- The line was $143.0M (2020), $77.4M (2021, 2022), $96.0M (2023), $125.0M (2024), $127.6M (2025), $124.7M (2026), spent $117.0M in 2024 and $115.3M in 2025. It jumped after Chicago joined the Illinois GEMT supplemental Medicaid program in 2020.
- The City says low 2025 non-tax revenue came from "lower reimbursements from the federally funded Ground Emergency Medical Transportation (GEMT) program" (2026 Budget Forecast p21), and in July 2026 Charges for Service were $34.3M below budget "mainly due to lower-than-expected Medicaid reimbursements for Emergency Medical Transport services" (monthly revenue report).
- The State's GEMT agreement requires the local government to send the State 50 percent of the supplemental payments (HFS IGA Article II).

**My reading, not confirmed by any City document:** account 9222 is the City's payment to the State for its share of the GEMT supplement. It fits the size and timing, but the budget does not say so. It is written into the note as our reading with "ask the Office of Budget and Management". Because of that the tree has no boxes. Next step: ask OBM or request the Finance General account ledger for 9222 (FOIA to the Department of Finance), or the HFS invoices for the City.

The budget book does not split the line. COFA has no note on it that I found.

## 7. City: CTA share of the real property transfer tax (9205), $62,789,053

One pass-through, so no boxes. Added: rate $1.50 per $500 for the CTA portion, on top of the $3.75 City portion ($5.25 total), in effect since 2008-04-01 (Municipal Code 3-33-030(F), Department of Finance page). The City keeps $634,233 for collection costs (line 9640). The CTA FY2026 budget book (PDF pp60, 62, 144) says the CTA gets 100 percent of the $1.50 increase as operating funding. Receipts also secure the 2008A and 2008B Sales and Transfer Tax Receipts bonds ($1.94B for pension and retiree health care, debt service $156,574,793 in 2026, paid in the CTA operating budget). The CTA forecasts $67.0M for 2026, $65.1M for 2025, which are higher than the City's $63.4M estimate, and I could not reconcile the two (a different timing or a different base). The State adds 25 percent through the Public Transportation Fund ($17.2M to the CTA). 2025 budgetary actual was $58,728,049.

## 8. City: judgments and settlements

The Law Department posts the "Judgment/Verdict and Settlement Report", 2026 payments through 2026-07-31, unaudited (the City data portal has no such dataset, only the CPD litigation reports already in `data/context_settlements_2019_2025.json`). 755 rows, summed by department and primary cause. The report has no fund or account column, so each department's payments are placed on that department's 0931 line, and the notes say so.

| Department in report | Paid so far | Placed on |
|---|---:|---|
| Police (including $90,000,000 Watts) | $234,299,709 | Police 0931, $82,558,000 |
| Fire | $3,262,991 | Fire 0931, $12,000,000 |
| Others (mostly Transportation) | $4,640,536 | Finance General 0931 Corporate, $40,785,387 |
| Water Management | $297,047 | Water and Sewer 0931 |
| Aviation and "Dept of Water" | $9,804 | not placed |

Police payments exceed the line by $151.7M, shown as a negative "paid beyond the budget line" box so the tree still adds up. The 2026 Budget Overview (PDF p55) says amounts above budgeted resources will be financed and repaid over five years, and the Civic Federation says the budget uses debt for police settlements. The report says nothing on which fund or bond pays.

The Watts block: the report's own total cell says $85,402,413 for "Total Global Watts Settlement". 22 amounts in the sheet are typed as text, so its SUM formulas skip them. Adding them back gives exactly $90,000,000.00, which is what the City Council approved on 2025-09-15. The 364 rows were identified by their approval date, not row position (both tests agree). The bigger payments outside Watts are 10 reversed-conviction payments $91.8M, 6 vehicle-chase payments $45.2M (two $20M).

Cross-check with the 2025 ACFR (budgetary comparison): Police 0931 actual $131,088,495 against $82,558,000 budget, Fire $14,828,284 against $12,000,000, Finance General $38,906,432 against $44,358,000. The Law Department's separate CPD litigation report puts 2025 payouts at $258,956,775 plus $101.3M for Watts, and WTTW reported CPD spent $131.1M in 2025 according to the ACFR. These do not match because the reports count by closing date, not by payment date, which I did not try to reconcile.

Also attached as context: a proposed $260.8M global settlement for 16 lawsuits was on the Finance Committee agenda for 2026-10-05 (Sun-Times, 2026-10-01). It is a proposal and is not counted in any box.

## 9. What is still missing

| Item | Status |
|---|---|
| SMG fee schedule and Soldier Field operating budget | Not public. Contract P-12035 text and any amendments need FOIA. |
| Soldier Field expense, by type | Not public |
| Harbor operating budget and Westrec fee | Not public |
| Park water, sewer and electric by park | Not published anywhere found |
| Water-sewer tax rate | Not found on the City's pages |
| What account 9222 pays | Not stated, see section 6 |
| Park pension benefits by tier | Not published |
| Judgments by fund (which fund pays each payment) | Report has department only |
| Why CTA forecast and City estimate of the transfer tax differ | Not resolved |
| Bears lease amendments and the current facility fee in dollars | Only the $7.0M total from the ACFR |

## 10. Sources

- Chicago Park District 2026 Budget Appropriations, https://files.chicagoparkdistrict.com/2025-12/2026%20Budget%20Appropriations.pdf (PDF pp45 to 51, 54, 60, 62 to 63, 94, 253, 263 to 265)
- Chicago Park District FY2025 ACFR, https://files.chicagoparkdistrict.com/2026-07/Chicago%20Park%20District_25%20ACFR_Final.pdf (PDF pp35, 40, 50, 76 to 78, 94, 139)
- Park Employees' and Retirement Board Employees' Annuity and Benefit Fund FY2025 annual report and Segal valuation at 12/31/2025 (https://www.chicagoparkpension.org/about-us/annual-reports/)
- Chicago Bears lease summary, https://law.marquette.edu/assets/sports-law/pdf/Chicago%20Bears%20Lease%20Summary.pdf
- Chicago Tribune 2013-02-13, https://www.chicagotribune.com/2013/02/13/soldier-field-management-gets-another-contract/
- Chicago Park District Legistar (matters 2985, 3168, 3196, 4275, 5896, 5963), https://webapi.legistar.com/v1/chicagoparkdistrict/matters
- City of Chicago Law Department, Judgment and Settlement Payment Requests, https://www.chicago.gov/city/en/depts/dol/supp_info/judgment-and-settlement-payments-requests.html (file "Finance Cmte 2026 JS through 7.31.26.xlsx")
- City of Chicago 2025 ACFR, https://www.chicago.gov/city/en/depts/fin/supp_info/comprehensive_annualfinancialstatements/2025-financial-statements.html (PDF pp146 to 149, 187)
- City of Chicago 2026 Budget Overview, Recommendations and Forecast, 2026 July Revenue Report (OBM)
- City ordinance datasets 2020 to 2026 for account 9222 (data.cityofchicago.org ids in the split file)
- City contract 54815, https://webapps1.chicago.gov/vcsearch/city/contracts/54815; Chicago Sun-Times 2018-04-16; Illinois HFS GEMT intergovernmental agreement 2025; DoltHub, "The Chicago Ambulance Caper", 2026-03-11 (third-party analysis, used only for the 2020 start date)
- City Finance pages on the Real Property Transfer Tax and Water and Sewer Rates; CTA FY2026 Budget Book (PDF pp60 to 62, 116 to 117, 144)
- Law Department Report on 2025 CPD Litigation, https://www.chicago.gov/content/dam/city/depts/dol/CPDLitigationReports/2025/2025%20Annual%20Litigation%20Report%206.30.26.pdf; Chicago Sun-Times 2026-10-01 ($260.8M proposal)
