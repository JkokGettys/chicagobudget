# Contributing

Thank you for helping. This project explains the 2026 budgets of the City of Chicago, Chicago Public Schools and the Chicago Park District in plain language. Fixes to numbers, sources, wording and code are all welcome.

Data contributions fix numbers, add detail or improve explanations. Site contributions improve code, writing or accessibility. Add data detail in `data/splits/<gov>/`, not by changing a builder; read `build/SPLITS.md`. Site code lives in `site/` and must pass the site checks.

## Local setup and a split example

Use Python 3.11+, SQLite and `python3 -m pip install -r requirements.txt`. Site work also needs Node 20+. The builders currently need public-source extracts under `raw/` that are not committed. See the root README for this reproducibility limitation. Never commit `raw/` or `data/people/`.

Find a box with `sqlite3 data/budget.db "select id, amount_cents from nodes where name like '%Overtime%' limit 10;"`. A split file targets one existing box and names its exact expected dollar amount:

```json
{
  "meta": {"author": "your name", "description": "Documented overtime breakdown"},
  "splits": [{
    "target": {"by": "id", "id": "replace-with-real-box-id"},
    "expect_amount": 12000000,
    "pieces": [{"name": "Documented portion", "amount": 3000000, "basis": "tied",
      "source": {"doc": "Public budget document", "url": "https://example.org/budget", "page": 12}}],
    "residual": {"name": "Other overtime not itemised", "why": "The public document does not break this part down further."}
  }]
}
```

Replace the example id, figures and URL with real public evidence. Amounts are dollars, with cents allowed. A City ordinance line may be targeted by fund, department, authority and account instead. Every piece needs a public source URL (and page where applicable). Add a `why` sentence to an unsplit piece of $10M or more. Pieces cannot exceed the target; the remainder becomes a visible residual. Mismatched expected amounts and invalid splits are logged and skipped, never forced. Use one file per topic.

Run `build/build_all.sh`: the builders check exact parent sums and official root totals, basis and source, explanations for large leaves, unique sibling names, finite amounts and available privacy scans. `build/verify_db.py` checks the finished database again. If the site exporter and validator are present, also run `python3 build/export_site.py` and `python3 build/validate_site_data.py`. For site changes, use `npm ci` and the scripts available in `site/package.json`.

## Ground rules

- Every number needs a public source. Never guess a number. If something is our estimate, it must be labeled as an estimate.
- Write in plain language a 13-year-old can follow.
- Do not add names of private individuals to anything the website shows.
- Report problems as GitHub issues.
- Use only public documents and datasets with URLs. Do not scale a number to fit. Prefer official figures; label an estimate `proxy` and explain its method.
- Never put an individual's name in a box label, note, explanation or side label. Business names are okay. Public source files may contain public-record names, but the site hides individuals.
- Keep site numbers generated from data, not hand-typed in components. Use plain language and avoid em dashes.

## Review and sensitive reports

A maintainer reviews each pull request and checks at least one changed data piece against its source. Include changed box ids, source links and local test results in the PR template. The private roster leak check runs only on the maintainer's machine; CI cannot substitute for it, and merge does not deploy. If a person's name appears on the website, report it privately through a [GitHub security advisory](../../security/advisories/new), not a public issue. The maintainer aims to fix confirmed exposure within a day.

## Contributor agreement

By sending a contribution to this repository (a pull request, a commit, an issue with text or data meant to be included, or any other material), you agree that:

1. You wrote it yourself or have the right to submit it, and it does not copy anyone else's work in a way that breaks their terms.
2. Code you contribute is licensed under the MIT License (`LICENSE`), and data and writing you contribute are licensed under CC BY 4.0 (`LICENSE-DATA`), the same as the rest of the project.
3. You also grant Getty Hill, the project owner, a permanent, worldwide, free, non-exclusive right to use, change, and relicense your contribution as part of this project, including under different license terms in the future.
4. You keep the copyright in your own contribution. This agreement only gives the permissions above.

If you do not agree, please do not send the contribution.
