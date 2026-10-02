# CPS FY2026 tree: pushing the biggest dead ends one level deeper

Built by `scripts/cpsdeep_build.py`, which writes four split files in `data/splits/cps/` (`cpsdeep_bonds.json`, `cpsdeep_reserves.json`, `cpsdeep_capital.json`, `cpsdeep_services.json`). Verified with `python3 build/cps_tree.py`: 50 splits applied, 0 skipped, 0 problems, total still $10,253,327,463.68. No builder file was edited. Builds on `research/cps.md`, `research/cps_deep.md` and `research/tree_gap_audit.md`.

Method rules used: published numbers get basis `tied` or `gov_estimate`, supplier payments get `paid_to_date`, our own arithmetic gets `proxy` with the method in the note. Where no source supports pieces, the split is `side_only`: the official explanation goes on the box, no pieces are invented.

New raw files (gitignored `raw/`): `raw/cps/cps_2026_capital_expenditures.csv` (BI "CPS Capital Expenditures" subject area, FY2026 spending by project, 2,979 rows, $226.1M), `raw/cps/os/*.pdf` and text (CPS official statements for 21 bond issues, from https://www.cps.edu/about/finance/official-statements-for-long-term-bonds/).

## 1. Bond series (33 splits, 100% of the bond box)

Every series with principal now has a principal box and an interest box, from `data/cps_debt_by_series_fy26.csv` (budget book Tables 2 and 3, pp.223 to 227). Series with no principal this year stay one box and get side info plus a note. Every series carries three side facts: principal still owed on 6/30/2025, rate and last payment date, and the pledged revenue.

Checked against the official statements (OS). The two payments that are one date each tie to the dollar:
- **2009G, $256.46M.** $254,240,000 principal plus $2,224,600 interest. Principal equals the OS size and 12/15/2025 maturity. Interest equals $254.24M x 1.75% x half a year. Budget book Table 2 note 2 and p.219: paid from a sinking fund funded since FY2011, "did not add to the District's annual debt service costs funded by operations".
- **1998B-1, $59.0M.** All capital appreciation bonds. OS maturity table, 2025: original principal $14,606,630.00, value at maturity $59,000,000 ($1,237.85 per $5,000). So principal $14,606,630 plus accreted interest $44,393,370 equals the budget line exactly.
- **1999A, $62.64M.** OS: zero-coupon bonds due 12/1/2025, original principal $8,215,896.00, $1,239.20 per $5,000, so $33,150,000 at maturity. Sinking fund on the 5.5% term bonds due 2026: $27,165,000 on 12/1/2025 and $28,690,000 on 12/1/2026. Principal = $8,215,896 + $27,165,000 = $35,380,896 (matches the budget). Interest = $24,934,104 accreted + $2,324,987.50 coupon (5.5% x half year on $55,855,000, plus a half year on $28,690,000) = $27,259,091.50 (matches).

Single-rate series (2018C, 2017C, 2019B, 2017D and the interest-only ones) reproduce the budget interest exactly as outstanding x rate: December half-year on the full balance plus June half-year on the balance after principal. Examples: 2018C $13,126,875.00, 2016A $50,750,000.00. Three series differ by tiny amounts that are probably rounding in the CPS schedule (2010C $2,571, 2010D $1,250, 2015E $1,000). These were not used as pieces.

Revenue that pays each series (budget book p.220 and Table 3): EBF state aid for most series, City IGA revenue plus PPRT for 1998B-1 and 1999A (OS 1999A confirms IGA revenues and Pledged Replacement Tax Revenues), IGA for 2019A, federal interest subsidy for the BABs and QSCBs (2009E, 2010C, 2010D), and the Capital Improvement Tax levy only for the four CIT series (not alternate revenue bonds). All alternate revenue bonds have a second pledge: a property tax levy that is abated while the first source is available. FY2026 funding: EBF $394.8M, PPRT $10.2M, IGA $142.3M, federal subsidy $23.8M, CIT $79.7M (Table 2). All series pay interest June 1 and December 1, except the CIT series (April 1 and October 1), checked in the official statements.

Not done: step-rate series (2018A, 2009E, 2019A and others) could not be split into dated coupon pieces from the data in hand, because their maturity tables need per-maturity parsing and the only sources are scanned or irregular PDFs. Their principal and interest split uses the budget numbers. EMMA was not used: the CPS-hosted official statements above contain what EMMA would. Trustee payment records were not found.

## 2. Pension general-fund reserve ($120.6M)

Official explanation (budget book pp.35 to 37): CPS owes $663.6M to the teachers' pension fund (CTPF). $602.3M is raised by the pension levy and $61.3M comes from operating revenue (the "operating diversion", down from $142.7M in FY2024 and $102.9M in FY2025). The State pays another $363.1M.

Split (basis `proxy`, our arithmetic from published numbers):
- **$61,256,335 operating diversion** = Board required $646,234,000 + additional Board $17,332,000 (CTPF valuation 6/30/2025 p.1) minus the $602,309,665 levy. Matches the "$61.3 million".
- **$59,314,005 remainder** = the State's share ($346,838,000 + $16,256,000 = $363,094,000) minus the $303,780,006 of teacher employer pension already charged to schools (accounts A57105 + A57110). The two differ by $11, so it ties. This matches the earlier finding in `research/cps_deep.md` that the remainder equals State aid less what schools carry. It remains our reading: no CPS document says this line holds the State share. The note says so.

## 3. Contingencies and the vacancy factor

No itemised use exists for any of them (Board resolutions and the budget book name none), so these are `side_only` boxes with the official wording.
- Budget book p.15 to 16 defines contingencies as money "budgeted but not yet allocated to specific accounts or units", that schools "can hold some in contingency", and that grant funds are held "particularly if the grant is not yet confirmed". The contingency budget fell $155M, "driven largely by the expiry of pandemic-era grant funding".
- Matching revenue found in `cps_2026_rev_fund_account.csv`: fund 324 income "Others" $136.2M against the $120M contingency, fund 367 Title I School Improvement income $77.3M against $50.4M, fund 124 "Payments From Schools" $50.0M against $50.0M, and fund 130 "Fund Balance Appropriated" $25.0M against $25.0M. The fund 130 link is by amount only (the budget book says a $25M philanthropic gift helped close the deficit, but does not name the fund).
- Vacancy factor: one program, P109981, -$200,000,000 in the General Education Fund (-$143,275,556 teacher salaries, -$56,724,444 career service). The same fund had -$123.3M and -$5.7M adopted in FY2025. Budget book glossary: "the anticipated savings resulting from the delay in staffing new and vacant positions". The books give no staffing math behind the $200M.
- The $120.6M is also described next to the $175M MEABF City reimbursement, which is not in the budget (see `research/cps_deep.md`).

## 4. Capital

- **IT centralized $108.0M.** Project sheet: cybersecurity, data warehouse, ITS roadmap, generative AI pilot, digital curriculum, Bridge-ERP, school network upgrades. The whole program is $113,015,321 ($108.0M CPS plus $5,015,321 E-Rate). The BI capital expenditure data lists 12 IT projects with $37,955,241 spent in FY2026: Program Bridge $17.94M, Safari Montage $6.70M, LAN data network upgrades $4.54M, STREAM $4.42M and smaller ones (paid_to_date). That leaves $70.0M as "budgeted but not spent on a named project yet". Caveat: expenditure data is by project, not by funding source, so the $38.0M may include the E-Rate part. Board Reports show the IT contracts are mostly paid from other funds: Oracle ERP $9M and IBM integrator $24M in FY26 are charged to Fund 115 (operating), so they are side info only. Sentinel network upgrades (25-0320-PR6) have FY26 authority of $17.5M plus $4.5M E-Rate.
- **Emergency/Unanticipated Facility Repairs $80M.** Official purpose: "unanticipated/emergency projects throughout FY26". No school list by design. 40 FY2026 jobs with "emergency" in the name total $1.07M, paid from other capital and repair lines, so they are side info.
- **Potentially Outside Funded State Projects $25M.** The outside-funded part of a $30M program; the budget book capital revenue table shows $25.0M of State grants.
- **Capital Project Support Services $23M.** Project sheet and budget book p.216: facility condition assessments, estimating, scheduling and capital planning. $31.3M of "CIP Management" project spending in FY2026, mostly one citywide project, is side info because it is shared across funds.

## 5. State Preschool for All, $88.1M (side only)

No per-provider amounts are public. The money is a sub-grant of the Illinois Early Childhood Block Grant to the City's Department of Family and Support Services (DFSS), which funds community providers. Board Report 25-0925-EX2: up to $99,624,439 for about 90 agencies, fifth and final renewal. Amended by 26-0730-EX2: FY2026 cut to $95,624,439, $4,000,000 moved to FY2027, about 88 agencies, term to 8/31/2026. A new agreement for FY2027 (25-1218-EX4) is $49.1M for about 55 agencies, because oversight is now shared with five other City Head Start grantees. CPS paid "CITY OF CHICAGO" $93.7M in FY2026 (vendor total, all agreements). The $88.1M budget line is below the Board's $95.6M limit and the sources do not explain the gap. The DFSS delegate list and award amounts are behind a login (childrenserviceschicago.org) and the City's contract data in `raw/contracts` only has five 2024+ DFSS early-learning rows, so provider boxes would be invented. ISBE's Preschool for All grant by provider was not found.

## 6. Lunch, $57.0M (side only)

CPS meals are run by Aramark Educational Services and Open Kitchens under one Board contract (specification 21-224). Board Report 25-0424-PR6: third renewal, $116,000,000 for FY2026 (original 22-0525-PR15 was $88.5M; FY27 renewal 26-0423-PR4 is $123,000,000). Payments FY2026: Aramark $69.4M, Open Kitchens $26.1M (total $95.6M). The payments cover breakfast, lunch, snacks and supper across about 700 sites, and the budget splits food into separate lines (lunch $57.0M, breakfast $33.6M, donated food $11.7M, other). So the vendor payments cannot be split onto the lunch line, and they are shown as side info. Federal reimbursement is the main source: $214M expected in FY2026 (budget book), because every school serves free meals under the Community Eligibility Provision. No official per-meal count was found. A press and advocacy figure of about 75 million meals a year was seen but not used.

## 7. Special education private tuition, $66.7M

Matched to supplier payments (paid_to_date), $40.05M over 11 providers: Menta Academy $14.67M, Easterseals Academy $6.21M, Sonia Shankman Orthogenic School $4.54M, The Cove School $2.75M, Lawrence Hall $2.43M, Elim Christian School $2.15M, New Horizon Center $1.84M, Redwood Schools $1.82M, Acacia Academy $1.34M, Shrub Oak International School $1.26M, Soaring Eagle Academy $1.04M. Only providers whose own pages or ISBE listings say they are ISBE-approved private special education programs were included. The remaining $26.6M is a visible "budgeted but not matched" box. Excluded on purpose: Pathways in Education ($19.4M), Ombudsman ($12.7M) (both CPS alternative high schools with their own budget units), and Camelot ($19.3M, whose Board Reports are for alternative safe school contracts). Earlier research (`cps_deep.md` section 4) had listed Camelot, Menta and Pathways as related to this line. Payments are by vendor, so a provider total can include other contracts, which each box note states. Individual student placements (Shrub Oak) are shown only by provider.

## What is still a dead end

| Box | Why |
|---|---|
| Bond principal and interest boxes of $10M or more (2009G principal $254.2M and others) | A principal payment to bondholders is the finest level. |
| Contingencies $120M, $50.4M, $50M and the vacancy factor | No document itemises them. |
| IT "not spent yet" $70.0M and Emergency repairs $80M | Not yet assigned to projects. |
| Preschool $88.1M | Provider list behind a DFSS login. |
| Lunch $57.0M | Meal vendors are paid across all food lines. |

Ask for by FOIA: the DFSS delegate awards for the Early Childhood Block Grant, and Aramark and Open Kitchens payments by meal type.

## Reproduce

`python3 scripts/cpsdeep_build.py && python3 build/cps_tree.py`. The BI capital expenditure pull used `scripts/cps_obiee.py` with logical SQL on "CPS Capital Expenditures" (fields Project Number, Unit, Project Fiscal Year, Period Year, Original Budget, Expenditure).
