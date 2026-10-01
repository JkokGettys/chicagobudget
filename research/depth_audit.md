# Can users drill down below $1M? Depth audit (2026)

Short answer: **City: yes, mostly. Park District: yes. CPS: not yet.** The details and the fixes are below.

## City of Chicago ($17.15B after removing double counting)

**The budget ordinance alone is not deep enough.** It has 3,213 line items, but **706 of them are $1M or more, and those hold 98% of the money.** The biggest ones:

| Line item (all departments combined) | $ | Can we split it further? |
|---|---|---|
| Salaries | $3.55B | **Yes.** The Positions dataset (`v2t2-vajc`, 8,243 rows) lists every job title, headcount, and pay rate. Example: Police has 8,310 Police Officers = $898M. Splitting by department > section > title gets most items down to individual job groups. The few groups still over $1M, like "8,310 officers", can be shown as "8,310 people x $108K each". That's as deep as public data goes, short of individual names, which the Employee Salaries dataset also has. |
| Pensions | $2.84B | Partly. We can split it by fund, then use each fund's annual report for retiree counts and average benefits. The actual payments go to people, so the deepest level is "X retirees x $Y average". |
| "Reserve Balance" | $1.90B | **This is a problem.** It's mostly federal and state grant placeholders (Aviation $412M, CDOT $363M...). The money is real, but the city doesn't say ahead of time which projects it will fund. We can label it as such and link it to the Capital Improvement Program PDF. |
| Professional & technical services | $1.02B | **Yes, via Contracts and Payments.** |
| Debt interest + principal | $1.86B | Partly. The ACFR debt schedules list each bond issue (each about $10M to $300M). |
| Construction | $0.97B | Yes, through capital project lists and contracts. |
| Health insurance | $0.52B | No. It's one Blue Cross contract and claims. Deepest level is "X employees covered x $Y". |
| Overtime | $0.41B | We can split it by department, but not further. |
| Delegate agencies (nonprofit grants) | $0.35B | **Yes.** Each nonprofit grant shows up as a contract or payment, and most are under $1M. |

**Actual spending data (Payments dataset `s4vu-giwb`) is the strongest tool for depth.**
- 2025 has 115,810 payments totaling $10.66B.
- Grouped by department, vendor, and contract, 806 groups are $1M or more, and they hold 93% of the dollars. So even this reaches individual named vendors and contracts, not under-$1M amounts across the board.
- **One catch:** for $6.07B of 2025 payments, the department field is blank. These are mostly pension, bank (bond), and Cook County transfers. We'll match them to departments by contract number, using the Contracts dataset.
- Payments are past spending (2025). The 2026 budget is a plan. We'll show them side by side ("planned 2026" vs. "actually paid last year"), not mixed together.

## Chicago Park District ($637.6M)
**Deep enough.** The 274-page Appropriations PDF has line items by account for each department, region, and **individual park** (Mozart Park, Durkin Park, ...). Almost every park-level line is under $1M. The text extracts cleanly and includes printed totals we can check our numbers against. We need to build a parser.

## Chicago Public Schools ($10.25B total, $8.66B operating)
**Not deep enough from PDFs alone.**
- The budget book only goes as far as categories (Salaries $3.86B, Benefits $2.29B, Contracts $1.85B...) and about 40 central departments.
- **There are no school-by-school numbers in the PDFs.**
- The deep data (about 500 schools, line items per school) lives in CPS's Oracle BI interactive reports (biportal.cps.edu, public guest login). That tool requires a real browser, and pulling the data needs a browser-automation export. The Chrome bridge isn't connected right now.
- Backups: the Illinois Report Card public data has spending per pupil by school (ISBE Excel). CPS FOIA is another option.

## What we'll show when we can't go deeper
Any node still over $1M with no deeper public data gets a "Why can't I go deeper?" note, for example: "This is 8,310 police officers paid about $108K each. Individual pay is listed in the Employee Salaries dataset." Being honest about the limits is better than hiding them.

## Next steps
1. Build the city tree: ordinance + Positions (salaries) + Contracts/Payments (contracts and nonprofit grants).
2. Write the Park District PDF parser and check it against the printed totals.
3. CPS: connect the browser and export school-level reports from the BI portal. Fall back to ISBE data if that doesn't work.
