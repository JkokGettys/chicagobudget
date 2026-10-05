# Download the 2026 budget data

The complete versioned dataset is in [`public/2026/`](public/2026/). It is organized in three layers:

1. [`tree/`](public/2026/tree/) has City, CPS, Park District and a separate City cross-fund root. Start with [`tree/manifest.json`](public/2026/tree/manifest.json), then open `tree/<root>/<top-category>.json`. Each of the 47,360 box IDs also appears in [`tree/lookup.json`](public/2026/tree/lookup.json), which points to its full record and citation in `site/chunks/`.
2. [`site/`](public/2026/site/) contains every JSON file served by the production website, including the manifest, 296 box chunks, side facts, source citations, search indexes, staffing counts and vendor aggregates. These are exact copies of the built site data, not a second independently edited version.
3. [`sources/`](public/2026/sources/) holds exact source inputs and name-bearing records, preserving their original `raw/` and `data/people/` paths for traceability. These files preserve individuals' names and other public-source fields. The website intentionally omits individual names and pools individual payees. The [`catalog.json`](public/2026/catalog.json) gives each publication file's original path, byte count, SHA-256 checksum and source URL where available. The compressed [`budget.db.gz`](public/2026/budget.db.gz) is the SQLite working tree, not a substitute for the original name-bearing sources.

The site and source layers serve different purposes: do not infer that a named payee can be attributed to a specific budget box when the upstream payment data lacks that link. The City cross-fund view is not additive to the City's net total. Budgeted positions/FTEs are not the number of people currently on payroll. Amounts in the tree are integer cents. The original database is a generated artifact; use the catalog's sources and [`build/inputs.sha256`](../build/inputs.sha256) to inspect inputs. The source files retain their publishers' terms and are **not** relicensed by this project's CC BY 4.0 license. See [`LICENSES.md`](../LICENSES.md).

The City of Chicago requires the following notice for secondary applications using its data:

> This site provides applications using data that has been modified for use from its original source, www.cityofchicago.org, the official website of the City of Chicago. The City of Chicago makes no claims as to the content, accuracy, timeliness, or completeness of any of the data provided at this site. The data provided at this site is subject to change at any time. It is understood that the data provided at this site is being used at one’s own risk.

To verify the release against a local build: `python3 tests/check_public_dataset.py`. To regenerate it after a validated site build: `python3 scripts/publish_site_dataset.py`. Do not bulk-commit the exploratory `raw/` folder or treat an old snapshot as current-year spending.
