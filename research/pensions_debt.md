# Pensions and debt: what the City owes, who pays, and what it bought

Outputs: `data/debt_2026.json`, `data/pensions_2026.json`. Reproduce with `python3 scripts/pensions_debt_fetch.py && python3 scripts/pensions_debt_build.py`. The fetch script keeps files that already exist in `raw/pensions_debt/` (gitignored). The build script asserts every number it quotes against the source text, so a wrong digit fails loudly.

Page numbers are **PDF page indexes** (page 1 is the cover), not the printed page labels. Source keys used below:

| Key | Document | URL |
|---|---|---|
| ORD | FY2026 Annual Appropriation Ordinance | https://bondlink-cdn.com/1338/FY2026-Annual-Appropriation-Ordinance.Vsr9wxc2u.pdf |
| 6694 | Open data, 2026 ordinance appropriations | https://data.cityofchicago.org/resource/6694-f78c.json (copy in `raw/city_appropriations_2026.json`) |
| ACFR | City ACFR FY2025 | https://www.chicago.gov/content/dam/city/depts/fin/supp_info/CAFR/2025CAFR/2025%20ANNUAL%20COMPREHENSIVE%20FINANCIAL%20REPORT__v2.pdf |
| OVW | 2026 Budget Overview | https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf |
| FCST | 2027 Budget Forecast | https://www.chicago.gov/content/dam/city/depts/obm/2027_Budget/Budget_Forecast/2027_Chicago_Budget_Forecast.pdf |
| GO26 | GO Taxable 2026A/B official statement | https://bondlink-cdn.com/1338/ILChicago02a-FIN.D8Ebm0ZNE.pdf |
| GO25AE | GO 2025A-E OS | https://bondlink-cdn.com/1338/OS.GE3zX31VR.pdf |
| GO25FG | GO 2025F/G OS | https://bondlink-cdn.com/1338/OS.Uxunte2ez.pdf |
| GO24A | GO 2024A OS | https://bondlink-cdn.com/1338/General-Obligation-Bonds-Series-2024A.qIfFSWQzr.pdf |
| GO24B | GO Refunding 2024B supplement | https://bondlink-cdn.com/1338/Supplement-to-the-Supplement-to-the-OS--Dated-12.19.2024.5KuWH6GRr.pdf |
| GO23 | GO 2023A/B OS | https://bondlink-cdn.com/1338/GO-2023AB-OS.TQ3FvIUd3.pdf |
| W26 | Water Revenue Bonds 2026A/B/C OS | https://bondlink-cdn.com/1344/ILChicago04a-FIN.yO9Z1Tmxh.pdf |
| ST25 / ST24 / ST23 | STSC offering circulars 2025, 2024, 2023 | https://bondlink-cdn.com/2925/ILSalesTax01a-FIN.ouftBIpEZ.pdf , https://bondlink-cdn.com/2925/OC.XFXm0gZ8C.pdf , https://bondlink-cdn.com/2925/Final-OC.qnWB3nNOk.pdf |
| STFS | STSC FY2025 financial statements | https://bondlink-cdn.com/2925/FY25-STSC-Financial-Statements---Issued--1.sdgdZJ5QA.pdf |
| OHFS / MDFS | O'Hare, Midway 2025 financial statements | https://bondlink-cdn.com/1348/O-Hare-International-Airport-Financial-Statement-2025.0sROg23GQ.pdf , https://bondlink-cdn.com/1351/Midway-International-Airport-Financial-Statement-2025.4TGhWWzsT.pdf |
| PABF / FABF / MEABF / LABF | Actuarial valuations as of 12/31/2025 | https://chipabf.org/wp-content/uploads/2026/07/PABF_20251231_Final.pdf , https://fabf.org/LinkClick.aspx?fileticket=G_bIYnMR31w%3d&portalid=0 , https://www.meabf.org/wp-content/uploads/2026/06/MEABF_Actuarial-Valuation-Report-as-of-12.31.2025-06.26.2026.pdf , https://www.labfchicago.org/assets/1/7/GRS_2025_Val.pdf |

---

## 1. Debt

### 1.1 Reconciliation to the ordinance Finance General debt lines

All three target figures are reproduced to the dollar from dataset 6694 and tie to the ordinance Summary C "Debt Service" column (ORD p.14, "Total - All Funds", $1,975,204,416).

| Check | Ours | Target | Difference |
|---|---:|---:|---:|
| Interest on Bonds + Interest on Loans | 1,038,548,680 | 1,038,548,680 | 0 |
| Principal (Payment of Bonds + Term Notes + on Loans) | 924,869,427 | 924,869,427 | 0 |
| Bond Fees and Costs | 9,486,309 | 9,486,309 | 0 |
| Sum of the three | 1,972,904,416 | | |
| + Interest on Library Financing (Library Fund) | 2,200,000 | | |
| + Water Pipe Extension Certificates | 100,000 | | |
| **All Finance General debt lines = ORD Summary C debt column** | **1,975,204,416** | 1,975,204,416 | 0 |

`data/debt_2026.json` calls the interest total $1,040,748,680 because it includes the $2.2M library line. The $1,038,548,680 figure is bonds + loans only.

**Double counts inside the $1.975B.** Two lines are the same dollars seen twice or borrowed money that rolls over:

| Item | Amount | Evidence |
|---|---:|---|
| Corporate Fund "For Payment of Bonds" = Corporate Fund Subsidy revenue of the Bond Redemption fund | 90,493,270 | ORD p.34 (fund 0510 revenue). It is a transfer, so it appears as principal in the Corporate Fund and again inside the GO fund appropriation. |
| Library term notes "For Payment of Term Notes" = Library Fund "Proceeds of Debt" | 125,926,011 | ORD p.34. Notes are refinanced each year. |

Net of the Corporate Fund double count, debt service in the ordinance is $1,884,711,146. If the Library term notes are treated as rolled over, cash debt service is lower still. The JSON keeps both lines and flags them.

### 1.2 Debt service by type and payer (ordinance, 2026)

Source for all ordinance amounts: dataset 6694, Finance General department, fund and account as shown. ACFR and financial-statement columns are the contractual schedule row for 2026.

| Debt type | Who pays | Ordinance principal | Ordinance interest | Ordinance fees | Schedule principal | Schedule interest | Schedule source |
|---|---|---:|---:|---:|---:|---:|---|
| General Obligation bonds (Bond Redemption fund) | Taxpayers: property tax levy $314.6M, Corporate Fund subsidy $90.5M, transfers in $25.0M (ORD p.34) | 132,090,000 | 285,429,137 | 0 | 94,932,000 | 292,676,208 | ACFR Table 22, p.247 |
| Water revenue bonds and IEPA/WIFIA loans | Water ratepayers (water fees are 92% of Water Fund revenue, OVW p.47) | 126,352,255 | 106,904,187 | 49,500 | 120,574,139 | 98,676,334 | ACFR Table 24, p.250 |
| Wastewater bonds and IEPA loans | Sewer ratepayers (sewer charge is 100% of the water charge, OVW p.47) | 69,379,980 | 89,048,700 | 57,800 | 72,214,088 | 104,542,733 | ACFR Table 24, p.250 |
| O'Hare revenue, CFC, PFC bonds and TIFIA loan | Airlines and airport users, residual rate basis, no property tax (OVW p.47) | 303,172,911 | 496,066,181 | 3,231,068 | 268,586,000 | 520,793,000 | OHFS pp.51-52 |
| Midway revenue bonds | Airlines and airport users (OVW p.47) | 77,455,000 | 61,100,475 | 6,147,941 | 63,100,000 | 64,735,000 | MDFS p.45 |
| Library term notes and library financing | Taxpayers (library levy) | 125,926,011 | 2,200,000 | 0 | none | none | short-term notes, not in ACFR Table 22 |
| Corporate Fund subsidy (same dollars as GO row) | Taxpayers | 90,493,270 | 0 | 0 | | | ORD p.34 |
| Sales Tax Securitization (STSC), outside the ordinance | Sales tax collected by the State, withheld before it reaches the City | 0 | 0 | 0 | 191,839,000 | 257,412,044 | ACFR Table 22 p.247, STFS p.24 |

STSC total for 2026 is $449,251,000 in the schedule. The Overview says $438.0 million is projected for STSC bond payments and operating expenses in 2026 (OVW p.55). Those two do not match and I did not force them to.

By payer, net of the Corporate Fund double count (ordinance): airlines and airport users $947,173,576; taxpayers $545,645,148; water ratepayers $233,405,942; sewer ratepayers $158,486,480. Total $1,884,711,146. About half of ordinance debt service ($947M of $1.885B) is not paid by taxes. The Motor Fuel Tax fund has no debt service line in 2026 (see gaps).

### 1.3 Ordinance lines, every one

| Fund | Account | 2026 |
|---|---|---:|
| Chicago O'Hare Airport Fund | For Interest on Bonds | 496,066,181 |
| Chicago O'Hare Airport Fund | For Payment of Bonds | 303,172,911 |
| Bond Redemption and Interest Series Fund | For Interest on Bonds | 285,429,137 |
| Bond Redemption and Interest Series Fund | For Payment of Bonds | 132,090,000 |
| Library Property Tax Levy Fund | For Payment of Term Notes | 125,926,011 |
| Water Fund | For Interest on Bonds | 92,769,138 |
| Corporate Fund | For Payment of Bonds | 90,493,270 |
| Water Fund | For Payment of Bonds | 86,685,000 |
| Chicago Midway Airport Fund | For Payment of Bonds | 77,455,000 |
| Sewer Fund | For Interest on Bonds | 77,313,314 |
| Chicago Midway Airport Fund | For Interest on Bonds | 61,100,475 |
| Water Fund | For Payment on Loans | 39,667,255 |
| Sewer Fund | For Payment of Bonds | 36,753,805 |
| Sewer Fund | For Payment on Loans | 32,626,175 |
| Water Fund | For Interest on Loans | 14,135,049 |
| Sewer Fund | For Interest on Loans | 11,735,386 |
| Chicago Midway Airport Fund | For Bond Fees and Costs | 6,147,941 |
| Chicago O'Hare Airport Fund | For Bond Fees and Costs | 3,231,068 |
| Library Fund | Interest on Library Financing | 2,200,000 |
| Water Fund | For Payment of Water Pipe Extension Certificates | 100,000 |
| Sewer Fund | For Bond Fees and Costs | 57,800 |
| Water Fund | For Bond Fees and Costs | 49,500 |
| **Total** | | **1,975,204,416** |

### 1.4 Every outstanding series (ACFR Table 25, balance at 12/31/2025)

The JSON `outstanding_issues.acfr_table25_issues` lists all 136 rows (original principal, balance, rate range, section, payer, page). Section totals, in $ thousands, tie to the printed totals (the parser asserts it):

| Section | Rows | Outstanding 12/31/2025 ($000) | ACFR page |
|---|---:|---:|---:|
| General Obligation bonds | 22 | 5,302,735 | 252 |
| General Obligation alternate revenue (Modern Schools 2010B, 2020A-3) | 2 | 8,480 | 252 |
| General Obligation line of credit | 1 | 551,833 | 253 |
| Sales Tax Securitization bonds | 10 | 5,776,648 | 253 |
| Water revenue bonds and loans | 37 | 2,300,696 | 253 to 254 |
| O'Hare revenue bonds | 17 | 11,364,380 | 254 to 255 |
| O'Hare CFC bonds | 1 | 171,800 | 255 |
| O'Hare PFC bonds | 1 | 100 | 255 |
| O'Hare TIFIA loan | 1 | 282,839 | 255 |
| O'Hare revolving line of credit | 1 | 0 | 255 |
| Midway revenue bonds | 10 | 1,495,285 | 255 to 256 |
| Wastewater bonds and loans | 33 | 1,944,813 | 256 to 257 |

Series-level GO detail after the March 2026 sale (36 series, total $5,823,140,179, GO26 p.24) is in `outstanding_issues.go_series_after_2026ab`, and the 10 STSC series with 2025 activity (total $5,776,648K) are in `stsc_series_12_31_2025` (STFS p.23). Lines of credit at 12/31/2025: RBC $325.0M, Wells Fargo $174.8M, Bank of America $52.0M, total outstanding $551.833M (ACFR p.85 and p.253). $165.0M was drawn in 2025 to fund court settlements and judgments (ACFR p.85).

### 1.5 Series with their own 2026 principal and interest

Official statements print a series-only column for these. Window: payments from Jan 2 2026 through Jan 1 2027 (the row headed "Year Ending January 1, 2027"). I checked the convention two ways. The total GO principal row for 2027 in GO26 p.26 ($94,932,000) equals ACFR Table 22's 2026 GO principal, and the 2025 and 2026 series' capitalized interest footnotes equal the sum of the two relevant rows exactly.

| Series | 2026 principal | 2026 interest | Source (page) | Note |
|---|---:|---:|---|---|
| GO Taxable 2026A and 2026B | 0 | 23,542,227 | GO26 p.26 | Capitalized, paid from bond proceeds. $54,249,479 total capitalized, equals the 2027 plus 2028 rows. |
| GO 2025A, B, C, D, E | 0 | 40,273,738 | GO25AE p.32 | Capitalized, $60,522,478 total equals the 2026 plus 2027 rows. Principal matches current outstanding. |
| GO 2025F and 2025G | 0 | 4,916,385 | GO25FG p.27 | Capitalized, $7,388,234 total. Statement shows $1,305,000 more principal than is outstanding now ($82,550,000 original vs $81,245,000 outstanding, ACFR p.252), so interest is slightly overstated. |
| GO 2024A | 0 | 32,626,875 | GO24A p.22 | Not capitalized in this row. Principal matches current outstanding. |
| GO Refunding 2024B | 0 | 14,030,250 | GO24B p.33 | Principal cell is blank until 2029. Principal not cross-checked. |
| GO 2023A and 2023B | 0 | 27,577,325 | GO23 p.131 | Statement was printed in 2023. Current outstanding is $64,620,000 lower ($523,800,000 original, $459,180,000 outstanding, ACFR p.252, GO26 p.24), so printed interest overstates what is due. Which bonds were retired is not stated in the sources fetched. |
| STSC Senior 2025A and 2025B | 0 | 11,576,409 | ST25 p.47 | |
| STSC Second Lien 2025A | 0 | 9,531,500 | ST25 p.47 | |
| STSC Senior 2024A | 0 | 10,107,500 | ST24 p.47 | |
| STSC Second Lien 2024A and 2024B | 4,490,000 | 28,254,264 | ST24 p.47 | |
| STSC Senior 2023A, B, C | 10,319,000 | 11,095,841 | ST23 p.82 | |
| STSC Second Lien 2023A and 2023B | 15,470,000 | 18,780,338 | ST23 p.82 | |

I did not add these up to a GO total. Older GO series (2012 to 2021, 2014B, 2015, 2017) are not included because their statements are years old and the principal they show no longer matches what is outstanding (for example 2021A/B shows $655,387,000 of principal at 2026 vs $654,167,000 outstanding in ACFR p.252). See gaps.

### 1.6 What the borrowing paid for (documented uses)

Every amount below is verified against the page text by the build script. "Capitalized interest" means the City paid the first interest payments out of the bond proceeds.

| Borrowing | Use of proceeds | Source (page) |
|---|---|---|
| GO Taxable 2026A, $485.625M (Mar 2026) | Retroactive wage increases for the Fire Department contract $166,000,000; settlements and judgments $267,342,155.83 (part of it repaid the bank lines of credit that had paid settlements earlier); capitalized interest $49,336,919.98; issuance costs $2,945,924.19 | GO26 p.13 |
| GO Taxable 2026B, $26.3M | Capital improvements $23,358,657.64; capitalized interest $2,779,054.93; issuance $162,287.43 | GO26 p.13 |
| GO 2025A, $393.395M | Chicago Works program $61,444,528; refinance lines of credit $306,139,748; capitalized interest $35,471,116; issuance $4,270,948 | GO25AE p.14 |
| GO 2025B, $175.075M | Chicago Works program $167,018,255; capitalized interest $13,907,025; issuance $1,112,905 | GO25AE p.14 |
| GO 2025C, $42.875M | Chicago Recovery Plan $40,440,000; capitalized interest $3,709,119; issuance $293,289 | GO25AE p.14 |
| GO 2025D taxable, $8.05M | Chicago Recovery Plan $7,290,000; capitalized interest $713,744; issuance $46,256 | GO25AE p.14 |
| GO 2025E, $75.985M | Replacing lead service lines $72,000,000; capitalized interest $6,721,474; issuance $842,558 | GO25AE p.14 |
| GO 2025F, $66.46M | Housing and economic development projects $62,305,000; capitalized interest $5,959,416; issuance $784,382 | GO25FG p.13 |
| GO Taxable 2025G | Housing and economic development projects $14,492,088; capitalized interest $1,428,819; issuance $169,093 | GO25FG p.13 |
| GO 2024A, $646.56M | Chicago Works and Recovery Plan projects $187,258,942; refinance lines of credit $451,401,411; capitalized interest $42,177,617; issuance $4,696,773.95 | GO24A p.12 |
| GO 2023A, $503.69M, and 2023B, $20.11M | 2023A: Chicago Works projects $65,000,000, refinance line of credit $450,000,000, capitalized interest $6,541,429.37, issuance $4,196,294.03. 2023B: Chicago Recovery Plan $21,000,000, issuance $169,037.10 | GO23 p.23 |
| STSC 2025A/B and Second Lien 2025A, $454.375M (Dec 2025) | A refunding. $81,773,476.02 conveyed to the City to refund GO bonds, $317,513,160.64 conveyed to buy back GO bonds by tender, $20,902,918.09 to refund STSC bonds, $57,611,313.66 to tender STSC senior bonds, $4,997,143.19 issuance. Moves debt from the property tax levy to sales tax, not new spending. | ST25 p.15 |
| Water Revenue 2026A/B/C, $943.135M (sold May 5 2026) | Water system project costs $661,353,159.91; refund second-lien bonds $167,309,209.23; purchase tendered bonds $150,041,737.05; issuance $6,895,662.56. Paid by water rates. | W26 p.19 |
| O'Hare 2025A, $211.2M | Repay revolving line of credit $211.7M; capitalized interest $16.9M; issuance $1.6M | OHFS p.48 |
| O'Hare 2025B, $121.0M | Repay line of credit $129.0M; capitalized interest $5.0M; issuance $1.0M | OHFS p.49 |
| O'Hare 2025E, $1,101.6M | Airport projects $919.0M; repay line of credit $62.9M; debt service reserve $54.5M; capitalized interest $99.4M; issuance $8.4M | OHFS p.49 |
| O'Hare Refunding 2025C, $429.5M | Partly defeased 2016B, 2016D, 2017A, 2017C and 2018C bonds ($472.6M); issuance $3.6M. The statement says total debt service fell by $66.9M. | OHFS p.49 |
| Midway 2025A, $98.1M | Partly defeased 2016A and 2016B bonds $79.8M; airport projects $20.7M; capitalized interest $1.9M; reserve $1.6M; issuance $0.8M | MDFS p.44 |
| O'Hare lines of credit, $403.6M drawn in 2025 | Airport capital projects, repaid by the 2025A, 2025B and 2025E bonds | OHFS p.48 |

What the settlement borrowing is about: GO26 p.107 says the Watts coordinated pretrial proceedings (police misconduct) would require the City to pay $101.8 million in total to the plaintiffs. This is context for the $267M settlements line, not an itemized breakdown of it.

"Scoop and toss" does not appear in any document fetched. What is documented is bank line of credit refinancing: 2023A $450.0M, 2024A $451.4M, 2025A $306.1M.

### 1.7 Reconciliation results (all checks in `reconciliation`)

| Check | Result |
|---|---|
| Finance General debt lines vs ORD Summary C debt column (p.14) | Equal, $1,975,204,416 |
| The three target figures vs data | Equal (see 1.1) |
| Corporate Fund subsidy vs Bond Redemption fund revenue line (ORD p.34) | Equal, $90,493,270 |
| Library term notes vs Library "Proceeds of Debt" (ORD p.34) | Equal, $125,926,011 |
| Bond Redemption fund appropriation + $12,584,133 loss-in-collection reserve vs Overview GO debt service $430.1M (OVW p.55) | Within $3,270 (rounding of the $430.1M) |
| OVW Finance General "Debt Service" program $1,966,323,405 (OVW p.185) vs ordinance $1,975,204,416 | **Not equal, ordinance is $8,881,011 higher.** The Overview is the October 2025 proposal. No public document itemizes the change. |
| Bond Redemption fund P+I ($417,519,137) vs ACFR 2026 GO schedule row ($387,608,208) | **Not equal, budget is $29,910,929 higher.** Principal is $37.2M higher in the budget, interest $7.2M lower. No public explanation. |
| Water, wastewater, O'Hare, Midway budget vs schedule | Budget and contractual schedule differ by $3M to $35M per line in both directions (table in `budget_vs_schedule`). They are not the same basis (budget is a cash appropriation, the schedule is a contractual window and uses imputed variable rates). |
| GO series total GO26 p.24 ($5,823,140,179) vs ACFR 2026 + $511,925,000 | Off by $1, rounding |
| Sum of ACFR Table 25 section rows vs printed section totals | Equal for every section |

---

## 2. Pensions

### 2.1 The four funds

All four valuations are dated 12/31/2025. "City contribution 2026" is the ordinance Finance General appropriation (statutory line 0976 plus advance line 097A). Ordinance totals: statutory $2,583,594,734, advance $259,626,680, total **$2,843,221,414**, which ties to ORD Summary C pension column (p.13). The 2026 contribution is the 2026 tax levy year contribution that is paid to the funds in 2027 (ACFR p.92 and each valuation footnote). What each fund receives in calendar 2026 is the 2025 levy year amount, shown in the last column.

| Fund | Statutory | Advance | **Ordinance total** | ORD page | Paid in calendar 2026 (levy 2025), valuation page |
|---|---:|---:|---:|---:|---:|
| Policemen's (PABF) | 1,040,273,100 | 72,249,824 | **1,112,522,924** | 534 | 1,042,582,000 (p.13) |
| Firemen's (FABF) | 441,746,521 | 11,583,144 | **453,329,665** | 535 | 443,683,274 (p.12) |
| Municipal Employees' (MEABF) | 965,001,553 | 161,218,894 | **1,126,220,447** | 532 | 955,738,601 (p.11) |
| Laborers' (LABF) | 136,573,560 | 14,574,818 | **151,148,378** | 533 | 136,089,914 (p.29) |
| **Total** | 2,583,594,734 | 259,626,680 | **2,843,221,414** | 13 | |

The statutory line in the ordinance equals the statutory contribution printed in each valuation for levy year 2026 for all four funds (the build asserts it).

| Fund | Retirees and beneficiaries | Page | Active members | Page | Avg annual benefit, service retirees | Basis and page |
|---|---:|---:|---:|---:|---:|---|
| PABF | 14,895 | 44 | 11,639 | 43 | $81,154 | 11,271 service retirees, annual payments $914,683,048 divided by count, equals printed Exhibit N (pp.50, 62) |
| FABF | 5,557 | 18 | 4,674 | 12 | $96,516 | Printed average monthly $8,043 x 12 (p.35). Survivors average $3,107 a month. |
| MEABF | 25,771 | 18 | 39,379 | 33 | $49,104 | Printed average monthly $4,092 x 12 (p.33). Surviving spouses $1,628 a month. |
| LABF | 3,545 | 11 | 2,780 | 16 | $65,230 | Printed average annual benefit for retirees (p.16). Surviving spouses $21,301. |
| Total | 49,768 | | 58,472 | | | |

Average across all beneficiaries (total annual benefits divided by all retirees and beneficiaries, derived by me): PABF $69,290, FABF $81,705, MEABF $44,524, LABF $52,775. These dilute the service retiree average with survivors and children, so use the service retiree column for "a typical retired officer".

LABF count note: the valuation counts 3,545 receiving benefits including 57 on disability. The ACFR (p.92) shows 3,488 for LABF because it treats the disabled as active. FABF and MEABF counts agree with the ACFR.

| Fund | Funded ratio (actuarial assets) | Funded ratio (market assets) | Funded ratio (GASB, ACFR) | Unfunded liability (actuarial) | Unfunded liability (market) | Valuation page |
|---|---:|---:|---:|---:|---:|---:|
| PABF | 26.08% | 26.66% | 26.44% | 13,845,585,000 | 13,736,211,000 | 12 |
| FABF | 24.67% | 25.25% | 25.25% | 6,048,701,965 | 6,002,550,922 | 12 |
| MEABF | 27.42% | 28.17% | 28.18% | 14,927,708,891 | 14,772,917,377 | 11 |
| LABF | 43.48% | 44.33% | 44.10% | 1,771,186,323 | 1,744,533,257 | 9 |

GASB net pension liability in the ACFR (FY2025, $ thousands, ACFR p.97): PABF 13,893,194, FABF 6,002,550, MEABF 14,769,878, LABF 1,760,939. Total 36,426,561, which agrees with the roughly $36.4B in `research/finance_general.md`. Fiduciary net position and benefit payments by fund are in the JSON (`acfr_fy2025`).

Funding gap versus the statutory contribution (levy year 2026, from each valuation): actuarially determined contribution minus statute is PABF $376,376,900, FABF $146,973,856, MEABF $385,381,976, LABF $33,769,124. Total $942,501,856. These come from the page cited in the JSON (`actuarially_determined_contribution_plan_year_2026`). The statutes set the City's payment below what the actuaries say would pay off the liabilities.

Retiree age and benefit-band breakdowns (PABF age bands, FABF age bands for annuitants and spouses, MEABF monthly benefit bands) are in the JSON.

### 2.2 Who funds the four pension appropriations (ORD p.35)

The ordinance's pension fund revenue detail shows where the $2.9B comes from, before the $56,477,077 loss-in-collection reserve:

| Source | Amount |
|---|---:|
| Property tax levy | 1,416,557,000 |
| Corporate Fund (matches "Pension Costs $907.8M", FCST p.14) | 907,784,727 |
| Water and sewer utility tax | 222,357,381 |
| O'Hare Airport Fund | 125,212,586 |
| Water Fund | 91,887,492 |
| Casino gaming tax (PABF and FABF only) | 44,610,000 |
| Sewer Fund | 33,532,950 |
| 911 surcharge fund | 28,985,604 |
| Midway Airport Fund | 28,770,751 |
| Total | 2,899,698,491 |

Total less the reserve equals $2,843,221,414 exactly.

### 2.3 Reconciliation results

| Check | Result |
|---|---|
| Four-fund Finance General lines vs ORD Summary C | Equal, $2,843,221,414 |
| Advance payments in the four funds ($259,626,680) vs FCST "supplemental payments $259.6 million" | Within $26,680, rounding of $259.6M |
| Pension fund revenue minus loss reserve vs contributions | Equal |
| Pension allocation and advance lines booked in other funds vs ORD non-property-tax pension column | Equal |
| OVW Finance General "Pension Funds" $2,760,267,271 (p.185) vs ordinance $2,843,221,414 | **Not equal, ordinance is $82,954,143 higher.** The Overview is the October 2025 proposal ($120.2M advance). The adopted ordinance has $259.6M of advance payments. FCST p.23 confirms $2.843B for 2026. No document itemizes the change by fund. |

### 2.4 Other context

CPS non-teacher staff are about 64% of active MEABF members, and the Forecast estimates they drive about 49% of the MEABF statutory employer contribution (FCST). The City budget assumes no reimbursement from the Board of Education in 2026 (OVW p.36), so the City carries that share of the $965.0M statutory MEABF line.

---

## 3. Gaps and caveats

1. **Per-series 2026 principal and interest is complete for only 12 groups of series (section 1.5).** Not covered: GO 2012B, 2014B, 2015B, 2017A/B, 2019A, 2020A, 2021A/B and older series (the 2017, 2019, 2020 and 2021 official statements do print a series column, but they are 5 to 9 years old and predate the 2025 tender and refunding transactions, so their 2026 rows would not reflect what is due today. I checked the 2021 statement and its remaining principal does not match ACFR outstanding. I did not use them); all individual Water, Wastewater, O'Hare and Midway series (the financial statements give only a total debt service schedule by fund); and the STSC 2017 to 2021 series. The type-level totals in 1.2 do cover them. EMMA (emma.msrb.org) has per-CUSIP schedules but is not reachable from automated clients, so I did not use it.
2. **Stale official statements.** The GO 2023A/B row (printed in 2023) and the 2025F/G row overstate interest because bonds have since been retired (principal in the statement exceeds current outstanding by $64,620,000 and $1,305,000 respectively, flagged in the JSON). 2024B principal was not cross-checked.
3. **Ordinance vs ACFR basis differences are unexplained.** GO P+I is $29.9M higher in the ordinance than in the ACFR schedule row, and the other four funds differ by $3M to $35M. The schedule windows (Jan 2 to Jan 1 for governmental debt, and calendar year for business-type debt, ACFR p.88) and imputed rates for variable debt explain part of it but no public document reconciles it.
4. **Overview vs ordinance:** Debt Service is $8.88M higher and Pension Funds is $82.95M higher in the adopted ordinance than in the October 2025 Overview. The differences are not itemized anywhere I found. The pension difference follows the Council raising the advance payment, per `research/reconciliation.md`.
5. **STSC in 2026:** ACFR schedule $449.3M vs Overview projection $438.0M (OVW p.55). The gap is unexplained.
6. **Water bonds sold in May 2026** ($943.1M, W26 p.19) are after the ACFR date. Their effect on 2026 water debt service is not shown in any budget document I have. The ordinance water lines were set in 2025.
7. **Use of proceeds is documented only for series issued in 2023 or later, for O'Hare and Midway 2025 issues, and for the May 2026 water bonds.** Older GO series (2008 to 2021) are on cityofchicagoinvestors.com but I did not parse them. Wastewater bond uses were not found. The $267M settlements line is not itemized by case beyond the Watts figure.
8. **Motor Fuel Tax debt:** the 2026 ordinance has no MFT debt service line. OVW p.44 mentions "MFT-backed loans" but none is budgeted.
9. **The "debt payments" figure elsewhere ($1,972,904,416 in `research/finance_general.md`)** equals bonds + loans interest, principal and bond fees only. It omits $2.2M library interest and $0.1M of water pipe certificates. `data/debt_2026.json` includes both so it matches ORD Summary C.
10. **Pension counts are not individual data.** The deepest public level is count and dollars by age or benefit band (PABF, FABF, MEABF). LABF has no band exhibit parsed. Average benefits for FABF, MEABF and LABF are printed averages or derived as stated. Retirees' average benefit is not available by retirement year.
11. **Not parsed:** the pension funds' own audited FY2025 financial statements for FABF and MEABF (the valuations and the ACFR already give assets, liabilities and benefits paid). `funds/` also holds the PABF, LABF and MEABF financial statements and GASB reports that were not mined for this file.
12. **Timing.** The City's "2026 contribution" in the ordinance is the 2026 levy year amount paid in 2027. Calendar-2026 cash to the funds is the 2025 levy year column in section 2.1. The advance payment is paid on a separate schedule (FABF valuation p.10 and MEABF valuation p.10 give 2026 supplemental amounts, in the JSON).
13. **A proposed ordinance (O2026-0027487, in committee per `research/reconciliation.md`) would order further advance pension payments.** Not passed, so not included.
