# The budget tree (data/budget.db)

One SQLite database holds the 2026 budgets of the **City of Chicago**, **Chicago Public Schools** and the **Chicago Park District** as trees of boxes. A box always equals the sum of the boxes inside it, to the cent.

Rebuild from the source files with one command (about 5 seconds):

```
build/build_all.sh
```

The build stops if any check fails. `build/verify_db.py` then re-checks the finished database on its own.

## What's in it (2026-10-01 build)

| Government | Boxes | Total | Matches official figure |
|---|---:|---:|---|
| City of Chicago | 13,718 (incl. 238 in the "counted twice" branch) | $16,842,553,003.00 | Passed ordinance net total, p. 544 |
| Chicago Public Schools | 26,090 | $10,253,327,463.68 | FY2026 budget, to the cent |
| Chicago Park District | 7,027 | $637,580,350.00 | 2026 Appropriations grand total |

Share of dollars by the size of the box where clicking stops:

| | Under $1M | $1M to $10M | $10M or more |
|---|---:|---:|---:|
| City | 26.0% | 9.4% | 64.5% |
| CPS | 46.6% | 14.8% | 38.6% |
| Parks | 40.5% | 33.6% | 25.9% |

"N people x rate" boxes count as under $1M (each person is under $1M). These shares are stricter than `research/final_gap_audit.md`, because estimates that don't fit inside the 2026 budget line (for example 2025 overtime by title) are kept as side info, not as boxes.

## Tables

**`nodes`**: one row per box.

| Column | Meaning |
|---|---|
| `id`, `parent_id` | Tree links (`city.public-safety.chicago-police-department...`). Roots: `city`, `cps`, `parks`, plus `city-twice` (memo) |
| `gov` | `city`, `cps` or `parks` |
| `name` | Kid-friendly name. The official name is in `extra.official_name` |
| `amount_cents` | Integer cents. Negative for offsets (vacancy savings, the unexplained OBM adjustment) |
| `basis` | `budget` (printed in the budget), `tied` (a split that adds up exactly), `proxy` (estimate, e.g. count x average), `residual` (the part a split could not itemize), `adjustment` (offsets and rounding) |
| `count`, `unit_amount_cents`, `unit_label` | For "2,148 positions x $111,252" boxes |
| `why_cant_go_deeper` | A plain-English sentence on every leaf of $10M or more |
| `source` | JSON: dataset or document, URL, page |
| `kind`, `tier`, `note`, `extra`, `is_leaf`, `depth` | Helpers |

**`side_info`**: facts attached to a box that are **not** added into its amount. Kinds include 2026 vendor payments so far, 2025 actual pay by job title, prior-year budget or actuals, retiree counts, capital project lists, and enrollment.

**`checks`**: one row per build with totals and the depth report.

## Rules the build enforces

1. Parent = sum of children, exactly. A split that doesn't fit the line gets a visible "Other / not itemised" or "Difference" box. Nothing is stretched to fit.
2. Each root equals the official printed total.
3. Every box has a basis and a source. Every leaf of $10M or more has a why-sentence.
4. Actual payments are never inside budget amounts. They are only side info.
5. **No individual names.** Vendor payments to individual people are pooled per department ("Payments to N individual people"). Job titles with fewer than 5 positions in a CPS unit are pooled. The build scans its output against the private name lists in `data/people/` (gitignored) and fails on any match.

## Known judgment calls

- **City "counted twice" branch ($1,709,026,955).** Internal transfers, re-borrowed library notes, matching funds and Appendix A/B services. City total + this branch + the $116,988,502 unexplained OBM adjustment = the gross ordinance $18,668,568,460, to the dollar.
- **City salary vacancy savings.** These are printed once per department and fund. Where a department's salaries are split across divisions, each division shows its share as "Budgeted vacancy savings and other differences".
- **Pension splits.** "Cost earned this year" vs. "paying down the shortfall" is derived from the funds' valuations. Retiree counts are side info.
- **Proxy splits that exceed the 2026 line** (CPD overtime 2025 actual $236M vs. the $200M budget, Fire back pay) stay as side info on the line.
- **CPS.** Fund and program are stored in `extra` (`money_comes_from`, `program_areas`) instead of as extra tree levels. 130 of 1,141 salary-by-title splits don't tie exactly and are labelled proxy with a residual.
- **Parks.** 275 tiny "rounding in the printed budget" boxes ($10 or less). The Specialty Trades salary line is $91,771 more than its title table, shown as its own box.

## Useful queries

```sql
-- top level of each government
select gov, name, amount_cents/100.0 from nodes where parent_id in ('city','cps','parks') order by gov, amount_cents desc;
-- biggest dead ends
select gov, name, amount_cents/100.0, why_cant_go_deeper from nodes
 where is_leaf=1 and abs(amount_cents)>=1000000000 order by abs(amount_cents) desc limit 20;
-- everything under the Police Department
select name, amount_cents/100.0, basis from nodes where id like 'city.public-safety.chicago-police-department%' and depth<=5;
```
