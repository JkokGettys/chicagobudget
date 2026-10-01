# Chicago Budget Explorer: Data Research Plan

Goal: a site a 13 year old can use. It starts with the whole budget and lets you click down level by level until every item is under $1M. To get there, the data has to be accurate and complete, and it has to be possible to check it against official numbers.

## What we already confirmed (live check, 2026-09-30)

Chicago's Open Data Portal (data.cityofchicago.org) has a free API with:

| Dataset | ID | What it gives us |
|---|---|---|
| 2026 Budget Ordinance - Appropriations | `6694-f78c` | 3,268 line items, **$18.67B total** |
| 2026 Budget Ordinance - Positions & Salaries | `v2t2-vajc` | Every budgeted job title, pay rate, and headcount |
| 2025 Budget Ordinance - Revenue | `e5cq-t86i` | Where the money comes from |
| Budget Ordinances 2011-2025 | many IDs | 15 years of history for trends |
| Payments | `s4vu-giwb` | Every check the city wrote (vendor, amount, date), updated daily |
| Contracts | `rsxa-ify5` | Every contract, the vendor, and its value |

The appropriations data already nests the way we need:
**Fund type (Local/Grants) > Fund (45) > Department (40) > Appropriation authority (program) > Account (line item, e.g. "Salaries")**

Only 752 of 3,268 line items are $1M or more. So most branches already get below $1M within 4 to 5 clicks.

## Known problems to solve

1. **"Finance General" is a $8.2B black box (44% of the budget).** It holds pensions, debt payments, employee health care, and similar costs. We need to break it apart using the Budget Recommendations book PDF and the pension fund reports.
2. **Budget is not the same as spending.** The ordinance shows what the city *planned* to spend. To show what it *actually* spent, we need the Payments data and the Annual Comprehensive Financial Report (ACFR).
3. **Big line items are vague.** "Salaries and Wages - $1.5B" in Police is still over $1M. The Positions dataset breaks that into job titles x headcount, which takes it below $1M. "Contractual Services" can be broken into individual contracts and vendors using the Contracts and Payments data.
4. **Sister agencies are not in this budget.** CPS ($9B+), CTA, Park District, Housing Authority, and City Colleges are separate governments. People expect to see them, so we should either show them on their own clearly labeled pages or explain why they're missing.
5. **Grant money is an estimate.** The $3.87B in grants depends on federal and state awards. It needs a label saying so.

## Research phases

### Phase 1: Core budget tree (most valuable, mostly done)
- Pull all 2026 appropriations and build the tree.
- Check it against official totals in the 2026 Budget Overview PDF (chicago.gov/obm). The fund and department totals should match exactly.
- Write a short plain-English description for each of the 40 departments, sourced from the Budget Recommendations book.

### Phase 2: Go deeper than $1M
- **Salaries:** join with Positions & Salaries (`v2t2-vajc`) so each salary line splits into job titles ("Police Officer: 9,000 x $X").
- **Contracts:** map department contracts (`rsxa-ify5`) to "Contractual Services" lines.
- **Finance General:** split it into pensions (4 funds: Police, Fire, Municipal, Laborers), debt service, health care, and so on, using the budget book and the pension funds' annual reports.
- Rule: keep splitting any node over $1M until no more source data exists. Mark any node we can't split with "why we can't break this down further."

### Phase 3: Actual spending vs. plan
- Add up Payments (`s4vu-giwb`) by department and year, and compare to budget.
- Pull "budget vs. actual" tables from the ACFR PDFs for the last ~5 years.
- Show the top vendors paid by each department.

### Phase 4: "Is this good value?" context
- **Per resident:** divide every amount by Chicago's population (~2.7M, Census API). "$X per person per year" means more to a 13 year old than "$2.1 billion."
- **History:** use the 2011-2026 ordinances to show "+X% since 2016."
- **Results:** use department performance metrics from the budget book (response times, potholes filled) and Inspector General audit findings (igchicago.org).
- **Peer cities:** per-capita spending in NYC, LA, and Houston from their own open data. This is optional and comes later.

### Phase 5: Revenue (where the money comes from)
- Revenue ordinance datasets: property tax, sales tax, fees, fines, and so on. This lets users see both sides.

## How we keep the data accurate
- A script pulls straight from the official API. No hand-typed numbers.
- Automatic checks: children always add up to their parent, and totals match the official PDF.
- Every number on the site links back to its source dataset or PDF page.
- The data refreshes each year when the new budget passes (around November).

## Proposed build after the data work
- Static site (fast, free to host), with data pre-built into JSON.
- Main screen: a clickable treemap or bubble chart, a breadcrumb trail ("All > Police > Salaries"), a plain-English blurb, a per-person cost, and a trend arrow.

## Scope decision: three budgets
The site will show the City, Chicago Public Schools, and the Chicago Park District.

| Agency | 2026 size | Best data source | Format |
|---|---|---|---|
| City of Chicago | $16.84B net per passed ordinance ($18.67B gross; $16.55B was the Mayor's proposal) | Open Data API `6694-f78c` | Clean API |
| Chicago Public Schools | $10.25B | FY2026 Budget Book PDF + CPS interactive budget reports (biportal.cps.edu, has school-level data) | PDF / BI portal |
| Chicago Park District | ~$0.6B operating | 2026 Budget Appropriations PDF (274 pages, line items by account, region, and park) | PDF, text extracts cleanly |

CPS and the Park District have no open data API, so we'll build PDF parsers and check them against the PDF's printed totals.

## Rule: remove double counting
City funds move money to each other (pension allocations, reimbursements). The passed ordinance deducts $1.826B (transfers $1.700B + debt proceeds $0.126B) to reach its printed net of $16,842,553,003. Our rule reproduces $1.529B plus named lines; $117.0M of OBM's single deduction figure is not reproducible from line items. See `research/reconciliation.md`. Grants were amended +$72.2M mid-year (now $3.94B).

## Open questions for you
0. ~~Show employee names?~~ Decided 2026-10-01: **job-title totals only, no names.** Groups with fewer than 5 people don't show averages; they are rolled into "other titles".
1. ~~Sister agencies?~~ Decided: City + CPS + Park District.
2. Should we start with the 2026 budget only and add history later?
3. Planned budget first, or actual spending first?
