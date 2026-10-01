# Data tree build plan (v1)

Goal: one clickable tree per government (City, CPS, Park District) where every level adds up exactly, every number has a label and a source, and every place you can't click further explains why.

## 1. Shape: what the user clicks through

The top levels are organized by **what the money is for**, not by accounting codes, so a 13-year-old can follow them:

```
Chicago (all three, side by side)
├─ City of Chicago  $16.84B
│   ├─ Public Safety  (Police, Fire, OEMC...)
│   │   └─ Chicago Police Department
│   │       ├─ People (salaries)  → section → job title → "8,310 officers × $108K"
│   │       ├─ Overtime            → by job title (2025 actual, labeled)
│   │       ├─ Contracts & supplies → vendor → contract → 2026 payments so far
│   │       └─ ...
│   ├─ Retirement (pensions)  → 4 funds → normal cost / paying down the shortfall
│   ├─ Paying back loans       → airport / water / sewer / city → bond series
│   ├─ Employee health care    → plan (estimate)
│   ├─ Grants                  → grant → project (where known)
│   └─ Money counted twice     (shown separately, not in the $16.84B)
├─ Chicago Public Schools  $10.25B
│   ├─ Schools → network → school → (teachers, aides, supplies...) → job title
│   ├─ Central offices → department → account
│   ├─ Teacher pensions, Debt (bond series), Building projects (project list)
└─ Chicago Park District  $637.6M
    ├─ Parks → region → park → account / job title
    ├─ Citywide departments, Pensions, Debt (25 series), Capital (TIF projects)
```

The levels come from the City budget's own categories (Public Safety, Infrastructure, etc. from the Budget Overview), then department, then a **"what kind of spending"** layer (people, overtime, contracts, debt...). Below that we attach the detail files the agents built.

## 2. One node format for everything

Every box on the site is the same kind of object:

```json
{
  "id": "city.public-safety.police.salaries.patrol.police-officer",
  "name": "Police Officer",
  "kid_name": "Police officers",
  "amount": 898059954,
  "basis": "budget_2026 | tied | proxy | actual_2026_ytd | actual_2025",
  "count": 8310, "unit_amount": 108070,
  "source": {"dataset": "v2t2-vajc", "url": "...", "page": null},
  "why_cant_go_deeper": null,
  "tier": "A | B | C | null",
  "children": [...]
}
```

- **basis** drives the label on every number (Budget, Exact split, Estimate, Paid so far in 2026).
- **Leaf nodes** of $10M or more always have a `why_cant_go_deeper` sentence (already written in `data/leaves_over_10m.json`).
- **Side info**, such as 2026-so-far payments or "budgeted 732, filled 650" vacancies, goes on the node as extra panels and doesn't count toward the totals. This keeps actual payments from being mixed into budget totals.

## 3. How it gets built (one script per government, plus checks)

| Step | Script | Input | What it does |
|---|---|---|---|
| 1 | `build/city_tree.py` | ordinance `6694-f78c`, transfer rule | Builds the base: function → department → spending type → line. Moves the double-counted transfers into a separate "counted twice" branch |
| 2 | (same) | `city_personnel_2026.json` | Replaces each salary line with section → title → count × rate (exact) |
| 3 | (same) | `city_bond_series_2026.json`, `debt_2026.json` | Replaces debt lines with bond series plus an "other series" leftover |
| 4 | (same) | `leaves_pensions.json`, `pensions_2026.json` | Splits pensions (labeled estimate where it is one) |
| 5 | (same) | `city_grants_2026.json`, `leaves_grants.json` | Splits grant reserves by named grant and project |
| 6 | (same) | `city_vendors_items_2026ytd.json`, `leaves_contracts.json` | Attaches vendors and contracts as side info (not added into totals) |
| 7 | `build/cps_tree.py` | CPS BI CSVs + `cps_*` split files | School and department tree, roster job titles, debt series, capital projects |
| 8 | `build/parks_tree.py` | `parks_2026.json` + capital and vendor files | Already a validated tree, so mostly reshaping |
| 9 | `build/check_tree.py` | all three trees | **The checks (below). Build fails if any check fails** |
| 10 | `build/export.py` | trees | Writes the site files |

**Split rule:** when a detail file splits a line, the pieces must add up to the line exactly. If they don't, the difference becomes a visible "other / not itemized" child with a note. We never stretch or shrink numbers to make them fit.

## 4. Automatic checks (the build stops if any fail)

1. **Every parent equals the sum of its children**, to the dollar.
2. **Top totals match the official printed numbers:** City $16,842,553,003 (with the $117.0M unexplained adjustment shown as its own line), CPS $10,253,327,463.68, Parks $637,580,350.
3. **Department totals match the ordinance or budget book.**
4. **Every node has a source and a basis.** Every leaf of $10M or more has a "why can't I go deeper?" sentence.
5. **No names anywhere in site files.** The build scans the exported files against the names in `data/people/` and fails on any match. Groups with fewer than 5 people have no average.
6. **No actual-payment amounts inside budget totals** (they can only be side info).
7. **A report is printed:** % of each budget under $1M / $1M to $10M / $10M or more, which should match the final audit.

## 5. Output for the website

- One small file per top-level box (`site/data/city.json`, `city/police.json`, ...), loaded when the user clicks. The full tree is too big for one file because CPS alone has 159K lines.
- A search index (department, school, park, vendor and job title names → node id).
- Precomputed **"per Chicagoan"** amounts (÷ 2,721,326 residents) and, for CPS, **"per student"** (÷ 316,224).

## 6. Known cleanups handled during the build

- Fields named `paid_2025` that actually hold 2026 numbers: read the file's `meta.label`, not the field name.
- Never add up the vendor `by_family` totals (they're $524M short). Use `vendor_payable_budget`.
- Treat old research notes that quote outdated numbers as history. The build only reads the data files.
- CPS fiscal year is July 2025 to June 2026. The City and Parks use the calendar year. Every box shows its own dates.

## 7. Order of work

1. City tree + checks (largest and most complex). 2. Parks (quick, already validated). 3. CPS. 4. Export + search index. 5. Then the website on top.

## 8. Choices I'm making unless you object

- Top level is organized by what the money is for (Public Safety, Schools, Parks...), not by fund.
- Double-counted money appears in its own clearly labeled branch, not hidden and not added into the total.
- 2026 payments so far and 2025 overtime appear as side info on each box, never added into budget totals.
