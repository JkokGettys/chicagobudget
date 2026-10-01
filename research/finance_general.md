# What's inside "Finance General" ($8.19B, 44% of the 2026 city budget)

Data: 2026 Budget Ordinance, data.cityofchicago.org dataset `6694-f78c`. Reproduce with `python3 scripts/finance_general.py`.
Checked against: [2026 Budget Overview](https://www.chicago.gov/content/dam/city/depts/obm/supp_info/2026Budget/2026%20Budget%20Overview.pdf), pp. 33 and 183-184.

> **Correction (2026-10-01):** the $16.6B below is the Mayor's *proposed* net total. The ordinance City Council passed prints **$16.84B** net, after deducting $1.826B. Our rule now also removes $7.8M of "Transfer..." lines, so the Finance General net is $6.662B. See `research/reconciliation.md`.

## The main finding: about $1.5B of it is counted twice

The city moves money between its own accounts. For example, the Corporate Fund sends $400M to the Municipal pension fund, and then the pension fund pays it out. The raw data lists both steps. The city's official totals remove these internal transfers ($1.80B citywide), which is why:
- the raw data adds up to **$18.67B**
- the official budget is **$16.6B**

Our site must remove the double counting. Otherwise every pension number is inflated by about 40%.

## The real breakdown (internal transfers removed: $6.67B)

| What | Amount | Plain English |
|---|---|---|
| Pensions | $2.84B | Retirement payments the city owes to police, fire, municipal, and laborer retirees |
| Debt payments | $1.97B | $1.04B interest + $0.92B paying back loans. About $940M of this is airport debt, paid by airline fees, not taxes |
| Employee health care & benefits | $0.81B | Health insurance ($658M), workers' comp ($81M), Medicare tax ($44M) |
| Raises not yet given to departments | $0.28B | Expected union pay raises, held centrally until contracts settle |
| Technology & outside services | $0.26B | IT maintenance and consulting contracts |
| Emergency medical transportation | $0.12B | |
| Taxes not expected to be collected | $0.07B | The city plans for unpaid property taxes |
| Money passed to the CTA and other agencies | $0.07B | |
| Lawsuits & settlements | $0.06B | Routine judgments ($48M). Big police settlements are often paid with bonds, so they show up as debt |
| Insurance + other | $0.17B | |

Pensions by fund (what each fund pays out): Police $1.11B, Municipal $1.13B, Fire $0.45B, Laborers $0.15B.

## Context worth showing on the site
- **The pension funds are about 28% funded.** They hold $14.2B against $50.6B owed, a gap of about $36.4B (2025 city financial report, plus [pensions.acitythatworks.org](https://pensions.acitythatworks.org)). That works out to roughly **$13,000 per Chicagoan**.
- About **$0.26B of the pension money is an "advance" payment**, more than state law requires. The Civic Federation praised this.
- **Most of Finance General isn't optional this year.** Pensions and debt are required by law and by contracts. A citizen who wants to cut costs should look at department programs, salaries, and contracts, plus the long-term choices that drive pension and debt growth.

## Still to do
- Split airport and water debt from tax-funded (General Obligation) debt using the ACFR debt schedules.
- Pull each pension fund's actuarial report (chipabf.org, meabf.org, fabf.org, labfchicago.org) for retiree counts and average benefits.
- Find what the $166.7M "Professional and Technical Services" line pays for, using the Contracts dataset.
- Find what the $283M of central raises is for, using union contract schedules in the Budget Recommendations book.
