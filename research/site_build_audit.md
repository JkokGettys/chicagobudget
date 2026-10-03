# Website build and privacy audit, 2026-10-03

This is a local build audit, not a launch sign-off. Nothing has been published or deployed.

## What passed

- The real database export validated all 47,360 boxes and four separate roots. Parent sums, official totals, source references, paid-so-far periods and both coverage rules passed.
- `python3 -m unittest build/test_site_tables.py -q` passed 2 tests. `python3 -m unittest discover -s tests -p test_site_export.py -q` passed 8 tests.
- `npm --prefix site run check` had zero errors, warnings or hints. The Astro build produced 17,411 pages.
- `python3 tests/check_site_dist.py` checked 17,767 static files and 42,740 distinct links, with no broken local links, forbidden local paths or em dashes. The file count and sizes fit the planned Cloudflare Pages limits.
- An independent read-only scan checked every built JSON string and HTML text/data attribute against 83,405 full roster names and 9,873 payees hidden by the City tree's policy. It found no private-name matches. One conservative name-policy match was the public venue Soldier Field, not a person.
- All 1,618 paid-to-date boxes had the correct source period: 1,552 City through September 28, 16 City Law through July 31, 38 CPS fiscal-year vendor totals and 12 CPS fiscal-year capital boxes. All 558 actual-pay groups with a count below five suppressed the mapped statistics.
- All 47,360 box IDs resolved to a chunk, including the 79 IDs longer than 255 characters. All 47,357 budget search entries mapped to existing IDs. Search and a deep-link shell were exercised against real built data in a local source-level DOM harness.

## Privacy bugs found and fixed before publication

1. Nested facts for hidden individuals retained 118 unique contract IDs, which could have identified them through public contract records. Commit `0975f52` recursively removes identifiers and adds a validator regression. The final built output contained zero nonempty contract identifiers among 10,537 nested-individual occurrences inspected.
2. The new vendors table used a weaker individual classifier than the City tree. Five exact employee-roster names and a broader set of payees hidden under the City's policy appeared as businesses in the first local build. Commit `3145964` uses roster names, payment-description identification and the upstream classification, with tests comparing the hidden sets. The final built output had no private-name matches.

The first generated site was unsafe and must never be uploaded. Only rebuild from the fixed commits and rerun the checks above.

## Before launch

- A real browser keyboard and screen-reader walkthrough remains. The local search and deep-link tests used a harness, not a full browser session.
- Confirm Cloudflare Pages rewrite behavior on a preview deployment. The static site uses `/city/box/*`, `/cps/box/*` and `/parks/box/*` rewrites for deep boxes.
- Create the public repository and publish the checksummed raw-input release asset. CI data and site jobs are intentionally skipped until `CHICAGO_BUDGET_INPUTS_URL` points to that asset. Set `PUBLIC_REPO_URL` once the repository URL is real.
- Set `PUBLIC_CF_ANALYTICS_TOKEN` only after Cloudflare Web Analytics is configured. The build currently sends no analytics beacon.
- Repeat the final privacy scan and build-output checks on the exact artifact that will be deployed. Do not treat this local audit as approval to publish.
