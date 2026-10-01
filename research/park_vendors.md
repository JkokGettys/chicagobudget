# Chicago Park District: what was actually paid to vendors

Status as of 2026-10-01. Every number is read from a public source by script. Nothing is estimated. Where the District does not publish something, this file says so.

Files: `scripts/parkvend_ethics_parse.py` (parse the payment lists), `parkvend_build.py` (data/parks_vendors.json), `parkvend_legistar.py` and `parkvend_awards_fetch.py` (Board actions and exhibits), `parkvend_s3list.py` (bucket probe). Raw files are in `raw/parkvend/` (gitignored).

## 1. Bottom line

| Question | Answer |
|---|---|
| Does the District publish what it paid each vendor? | **Yes, but only for 2019 to 2022 and only as payee plus calendar-year total.** The Ethics Office page lists "current and former contractors who ... received ... payments totaling $10,000 or more in any 12-month period", sourced from the District ERP. |
| Where is it? | https://www.chicagoparkdistrict.com/ethics-office , four PDFs: [2019](https://www.chicagoparkdistrict.com/media/29071/download?inline), [2020](https://www.chicagoparkdistrict.com/media/29076/download?inline), [2021](https://www.chicagoparkdistrict.com/media/29081/download?inline), [2022](https://www.chicagoparkdistrict.com/media/29086/download?inline). Same files on the CDN: `https://files.chicagoparkdistrict.com/2025-05/<year> Vendor Payments - Ethics Ordinance Report.pdf`. |
| Anything for 2023, 2024, 2025? | **No.** The page still stops at 2022 on 2026-10-01. Media IDs after 29086 are unrelated images. A 2023 filename guess on the CDN returns 404. |
| Contract, department or account detail? | **No.** Two columns only: vendor name, amount. |
| Rows | 2019: 437, 2020: 345, 2021: 369, 2022: 440 payees. Totals $343.4M, $304.2M, $364.9M, $379.3M (sum of listed rows, includes pension and City of Chicago payees). |
| Can the data be tied to the FY2026 budget? | Partly, by named counterparty. See section 4. 48.0% of the $392.3M non-personnel 2026 budget sits in lines whose counterparty is named by a Board action, the ordinance or the budget, and for which a 2019-2022 paid amount exists. That is a statement about the budget line, not about 2026 spend. |
| Recommended next step | File the FOIA in section 6 for 2023 to 2025 in CSV with contract and account fields. |

## 2. What I checked (and what exists)

| Source | Result |
|---|---|
| District "Vendor Payments", "Checkbook", "Transparency" pages | `/vendor-payments` and `/transparency` are 404. Nothing on the Comptroller page (`/comptroller`) except ACFR and PAFR PDFs. |
| `/ethics-office` | **Found the 2019 to 2022 lists** (above). |
| files.chicagoparkdistrict.com | Public S3 bucket listing is open but the CDN ignores paging, so only the first 1,000 keys are visible. Within them, the only payment documents are the four ethics lists plus "View Payments" and "Update Payment Method" supplier guides. `scripts/parkvend_s3list.py`. |
| Supplier portal (Oracle Fusion) | Login only. Suppliers see their own payments. Not public. |
| Legistar API (`webapi.legistar.com/v1/chicagoparkdistrict`) | 1,432 matters downloaded. `MatterCost` is empty on all of them. 80 titles carry a dollar amount, almost all construction change orders and final payments (2013 to 2025). Contract award titles usually do not state a dollar value. 151 attachments from contract and agreement matters (2019 on) were fetched. The useful ones are the Exhibit A fee schedules (section 5). The rest are MBE/WBE forms. |
| Annual ACFRs | Read the FY2022 and FY2025 ACFR text: category totals only (General Fund contractual services $172.5M actual in FY2022, PDF p97), no vendor names. FY2019 to FY2021 downloaded, only the statement pages were checked. |
| Single Audit | Federal Audit Clearinghouse (https://api.fac.gov/general) has the District's reports. Total federal awards expended: 2025 $3.61M, 2024 $4.43M, 2023 $3.13M, 2022 $2.46M, 2021 $2.20M, 2020 $3.40M, 2019 $6.02M. These are program totals, tiny against the budget, and are not vendor payments. |
| City of Chicago payments dataset / vendor search | The District is a payee of the City, not a publisher. Nothing for District vendors. |
| OpenTheBooks | `openthebooks.com` returned HTTP 403 to curl. I could not confirm whether it holds a Park District checkbook. Not verified, not used. |
| MuckRock | Only FOIA logs for the District turned up (the District's own FOIA log requests). No vendor payment file found. |
| Illinois Comptroller local government warehouse | Landing page fetched only. I did not find a per-vendor payment file for the District. Not searched in depth. |
| Bonfire contracts library | Already in `research/park_district.md` section 3.4. Whole-term values only. Not payments. |

Not tried: the Chrome bridge (coordinator approval not requested, not needed).

## 3. How the lists were parsed

PDF text extraction by default scrambles long vendor names that run into the amount column (for example "CHICAGO-LAWNDALE AMACHI MENTORING PROG7R0A0M00"). `parkvend_ethics_parse.py` reads characters by x position and splits at the fixed amount column (x 274 in 2019, x 332 in 2020 to 2022). Result: 1,591 rows, 0 unparsed lines, 0 amounts under $10,000. Spot checks against the PDF characters: "LABORERS INT UNION OF N/A LOCAL1092" is a name ending in digits that belong to the name (the amount is 37,918.98 in 2022, an earlier version of the parser misread it as $109M). The same rule keeps "TEAMSTERS LOCAL UNION 700" and "OPERATING ENGINEERS LOCAL 399" correct.

Caveat on duplicates: the same company appears under several payee strings (for example "ADVANCED RESOURCES", "ADVANCED RESOURCES LLC", "ADVANCED RESOURCES, LLC" in 2022). I did not merge them. A vendor that fell under $10,000 in a year is absent that year.

## 4. Tying the payments to the $637.6M budget

Operating budget FY2026 $637,580,350. Personnel (class 610000) $245,230,929. **Non-personnel $392,349,421.** Of that, debt service (600005, 600015) is $70,556,546, leaving $321,792,875.

Mapping is by named counterparty only, in explicit rules in `parkvend_build.py` with a basis string for each. Paid amounts are reported once per group, never repeated across the lines in a group.

| Group (budget account) | 2026 budget | Paid 2019 | 2020 | 2021 | 2022 | Payee and basis |
|---|---|---|---|---|---|---|
| Soldier Field, McFetridge, Beverly/Morgan Park (626045, 626055, 626065) | $41,353,087 | $31,548,720 | $21,809,995 | $28,280,499 | $40,623,156 | SMG. One payee, cannot be split by facility. |
| Harbors and ice rinks (626040, 626015) | $17,573,203 | $18,421,396 | $15,889,972 | $20,661,739 | $17,532,599 | Westrec Marinas (all years) and Westrec SMI OpCo (2022 only, $6,038,136, purpose not stated). |
| Golf (626050) | $8,490,697 | $5,890,547 | $6,323,786 | $7,310,751 | $8,704,065 | Chicago Park Golf Management LLC. Operator behind the LLC not stated. Indigo Sports began 2025, so no Indigo payment is public. |
| MLK Center (626010) | $1,548,354 | none | none | none | $1,288,809 | Chicago City Skating LLC (2022 only). A separate payee "Chicago Skating LLC" ($1.6M, $1.1M, $1.1M, $0.2M) is not mapped. |
| Parking (626005) | $1,691,052 | $1,583,177 | $1,181,151 | $1,518,008 | $2,738,548 | Standard Parking Corp, then SP Plus. |
| Cellular infrastructure (626030) | $537,438 | none | $67,708 | $293,637 | $515,546 | SPAAN Tech Inc. |
| Concessions management (626035) | $929,159 | none | $17,500 | $590,464 | $1,118,362 | UCG Associates. Unison Consulting (Board action 26-1305-0513) not yet paid in the data. |
| Waste (623030) | $4,090,000 | $2,205,324 | $2,396,229 | $2,628,472 | $2,790,956 | Flood Bros Disposal. |
| Workers comp admin (625035) | $3,250,000 | $3,500,496 | $2,553,401 | $2,663,395 | $1,830,979 | CCMSI. Fees versus claims not stated. |
| Zoo (625005) | $6,751,687 | $5,590,000 | $5,590,000 | $5,837,158 | $5,696,210 | Lincoln Park Zoo. |
| Aquarium and Museums (625010) | $29,617,600 | $30,754,162 | $30,003,908 | $32,828,568 | $29,027,833 | 11 institutions named in ordinance Appropriation F, all 11 found. |
| Pension (625020, 625023) | $69,332,412 | $27,487,785 | $34,062,019 | $84,064,284 | $55,744,221 | Park Employees A&B Fund. Not vendor spending, kept separate. |
| Grant Park Music Festival (623185) | $2,400,000 | $2,900,000 | $1,450,000 | $2,600,000 | $2,900,000 | Grant Park Orchestral Association. |
| Parks Foundation, NeighborSpace, Garfield Conservatory Alliance (623170, 623175, 623180) | $830,000 | $971,887 | $865,498 | $925,691 | $1,316,030 | Named by the budget lines. |

Coverage of the FY2026 non-personnel budget ($392,349,421), 2026 appropriations in lines with a named payee:

| Mapping strength | Budget 2026 | % of non-personnel |
|---|---|---|
| A. Named contract counterparty (12 lines above, SMG to CCMSI) | $79,462,990 | 20.3% |
| A. Institution remittances and grants (Zoo, Museums, Grant Park, 3 small) | $39,599,287 | 10.1% |
| A. Pension contribution | $69,332,412 | 17.7% |
| **A total** | **$188,394,689** | **48.0%** (47.2% if pension and debt are excluded from both sides) |
| B. Payee class matched by name only: Maggie Daley (626060), landscape (626025), gas and electric (623070, 623075), telecom (623015), fleet leasing (626075) | $43,323,021 | 11.0% |
| A plus B | $231,717,710 | 59.1% |
| Not mapped | $160,631,711 | 40.9% |

Important limits:
- Coverage means "a named payee with a published paid amount for this line exists in 2019 to 2022". It does not mean the 2026 line is explained by those payees.
- B is weaker. "MAGGIE DALEY PARK" is a payee string that is a park name, with no operator named. Landscape and utility rows are matched by company type. Water and sewer (623080, $16.7M) is not mapped, it is probably paid to the City of Chicago but the list does not say.
- Of the 2022 list total of $379.3M, $196.3M is attached to a budget line above (A plus B) and $18.9M is "City of Chicago" with no stated purpose. The other **$164.0M** is named payees I could not tie to a line. Largest: Paschen All Joint Venture $35.3M (2021 $11.4M; Board actions show the Park 596 headquarters construction contract P-20015 with this joint venture, so this is capital), Blue Cross Blue Shield of Illinois $22.6M (health plan), OFMS EE Solutions $13.0M (purpose unknown), Robe Inc $7.7M, CVS/Caremark $6.4M, All-Bry Construction $4.3M, Mesirow Insurance $3.7M. Much of that is construction (capital funds, outside the operating budget), health benefits and IT.
- The ethics list is cash paid by the ERP for all funds. The operating budget excludes capital. Do not subtract one from the other.

## 5. Contract fee schedules from Board actions (terms, not payments)

| Vendor | Asset | Contract | Terms | Source |
|---|---|---|---|---|
| ASM Global (SMG dba) | Maggie Daley Park | P-24009, Board action 25-1070-0409 | Management fee 2025 to 2027 $200,000 a year, 2028 to 2030 $225,000, 2031 $250,000. Contractor capital $50,000 (2025), $25,000, $15,000, then $10,000 a year to 2031. | https://legistar2.granicus.com/chicagoparkdistrict/attachments/59187994-fdc6-4764-8b26-b29c8a5b1362.pdf |
| Indigo Sports, LLC | Golf courses | P-24001, Board action 24-1125-0911 | Management fee $1,275,000 a year. Contractor capital $9M over 10 years: $3,575,000, $1,200,000, $1,700,000, $525,000, $1,250,000, $200,000, $150,000, $150,000, $150,000, $100,000. Troon Community Fund $25,000 a year. | Exhibit A, matter 5963 on Legistar |
| Levy Premium Foodservice | Soldier Field food | P-23013, Board action 24-1058-0410 | $12M contractor capital, 3% of gross receipts to an equipment reserve. Commission schedule in the exhibit. | Exhibit A, matter 5896 |

For SMG at Soldier Field (P-12035), Westrec harbors (P-14010), Standard Parking (P-14012), and Chicago Skating Partners (P-25008), no fee schedule is attached to the Legistar matters I fetched. The Westrec ice rink (P-23010) and Chicago Skating Partners attachments are MBE/WBE forms only.

The management fee is small against the budget line. Maggie Daley's fee is $200,000 against a 2026 budget line of $4,387,340, and golf's fee is $1,275,000 against $8,490,697. The rest of those lines is the operator's operating cost reimbursed or budgeted by the District. The public files do not say how it splits.

## 6. Draft FOIA request (send to foia@chicagoparkdistrict.com)

Per the District's rules effective January 1, 2026, the full request must be in the body of the email, with no attachments or links. FOIA Officer: Karen Choudhury, Chicago Park District, 4830 S. Western Ave., Chicago, IL 60609, (312) 742-4789. Source: https://www.chicagoparkdistrict.com/freedom-information-act

```
Subject: FOIA request: vendor payment data, FY2023 through current

To the FOIA Officer, Chicago Park District:

Under the Illinois Freedom of Information Act, 5 ILCS 140, I request the following records in electronic, machine-readable form (CSV or XLSX, not PDF).

1. A payment-level extract from the District's Oracle ERP accounts payable module for every payment (check, EFT or wire) issued from January 1, 2023 through the date of processing of this request, with these fields where they exist: payment date, payment number, supplier name, supplier number, invoice number, invoice date, invoice amount, amount paid, purchase order number, contract or specification number (for example P-24001), department or cost center, fund, account code (for example 626045), project number if any, and payment description or invoice description.

2. The same data in summary form, if payment-level data is not available: total paid by supplier by calendar year (2023, 2024, 2025 and 2026 to date), with the contract or specification number, fund, department and account code for each total.

3. The Vendor Payments lists prepared under the Governmental Ethics Ordinance for reporting years 2023, 2024 and 2025 (the District has posted 2019 through 2022 at https://www.chicagoparkdistrict.com/ethics-office).

4. For these management agreements, the amounts actually paid to the contractor each calendar year from 2023 to date, split between management fee, reimbursed operating costs, incentive fees and any other payments: Soldier Field (P-12035, SMG/ASM Global), harbors (P-14010, Westrec), golf (P-07061 and P-24001, Troon/Indigo), Maggie Daley Park (P-24009), MLK Center (P-25008 and predecessor), McFetridge, Beverly/Morgan Park (P-15018), Addams and Gately (P-19021), ice rinks (P-23010, P-25021), parking (P-14012), and the Soldier Field food service agreement (P-23013).

I do not request personal information of individuals, bank account numbers, or taxpayer identification numbers. Please redact those fields if present and cite the exemption. This request is not for a commercial purpose. It is made for public-interest research and publication of budget information. I ask for a fee waiver because the records are in electronic form and disclosure is in the public interest. If any part is denied, please release the remainder and state the specific exemption for each redaction. If any part of the request is unclear, please contact me by email rather than delaying.

Name:
Mailing address:
Daytime phone:
Preferred delivery: email
```

Statutory clock: 5 business days, extendable by 5 more (5 ILCS 140/3(d)). Large extracts often get a written extension agreement.

## 7. Gaps

| Gap | Status |
|---|---|
| Payments for 2023, 2024, 2025, 2026 | Not published. FOIA above. |
| Payments by contract, department or account | Not published in any year. |
| Splits inside shared payees (SMG, Westrec) | Not published. |
| Fee-versus-reimbursement split for management contracts | Not published. Only Maggie Daley and golf fee schedules found. |
| OpenTheBooks checkbook | Site blocked curl (403). Worth a manual check in a browser. If a Park District checkbook exists there, it would fill 2023 onward. I did not confirm one exists. |
| Soldier Field SMG agreement terms | Not on Legistar matters fetched. |

## 8. Reproduce

```
pip3 install pdfplumber
python3 scripts/parkvend_ethics_parse.py   # downloads 4 PDFs, writes raw/parkvend/ethics_rows.json
python3 scripts/parkvend_legistar.py       # all Legistar matters
python3 scripts/parkvend_awards_fetch.py   # attachments for contract matters (about 5 minutes)
# FAC totals: curl -H "X-Api-Key: DEMO_KEY" "https://api.fac.gov/general?auditee_name=ilike.*Chicago%20Park%20District*&select=report_id,audit_year,total_amount_expended" > raw/parkvend/fac_general.json
python3 scripts/parkvend_build.py          # data/parks_vendors.json
```
