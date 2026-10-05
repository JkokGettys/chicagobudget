# Chicago Budget Explorer

Explore where money goes in the 2026 budgets of the City of Chicago, Chicago Public Schools (CPS), and the Chicago Park District. The project builds a database of nested budget boxes and a website for opening them. Every parent box equals its children to the cent. Planned budgets are not actual spending.

| Budget | Official total | Source |
|---|---:|---|
| City | $16,842,553,003 | Passed 2026 ordinance, net total, p. 544 |
| CPS | $10,253,327,463.68 | CPS FY2026 budget |
| Park District | $637,580,350 | 2026 appropriations grand total |

## Rebuild and check

Use Python 3.11 or newer, SQLite, and the [pinned raw inputs](build/inputs.sha256). The builders require the City appropriations file and CPS extracts under `raw/cps/`. Those files are not in git yet. Until a checked release archive is available, ask a maintainer for the public-source extracts. Do not commit the full `raw/` directory without reviewing its contents and source terms. Public-source data may include individuals' names; the website omits those names, but that display rule does not require redacting the underlying public records. Once the inputs are present:

```sh
python3 -m pip install -r requirements.txt
bash build/fetch_inputs.sh
build/build_all.sh
sqlite3 data/budget.db "select id, name, amount_cents / 100.0 from nodes where name like '%Overtime%' limit 10;"
```

The build writes `data/budget.db` and checks totals, sums and website-display privacy. Without the locally held `data/people/` roster, its website name-leak scan is **skipped**, not passed. Other checks still run. Never deploy the website without the maintainer's local display-name check. Public-source data can retain names even when the website omits them.

Found a wrong number? [Report it](.github/ISSUE_TEMPLATE/number.yml) with the box id and an official source, or read [how to contribute](CONTRIBUTING.md). For a name visible on the website, **do not open a public issue**. Use a private GitHub security advisory.

`build/` contains builders and checks, `data/splits/` contains sourced detail, `data/` contains processed inputs, `research/` explains decisions, `scripts/` processes sources, and `site/` contains the website. Public-record names can occur in committed source data. The website omits individuals' names, while preserving business names and amounts. The complete generated database and site data are not on GitHub yet; downloadable website JSON is served directly by the site. See [licenses and attribution](LICENSES.md): code is MIT, and this project's original data work and writing are CC BY 4.0. Upstream records keep their own terms.
