# Public data publication plan

Status: **plan only**. No additional raw files, databases, or generated datasets have been published by this document.

## Goal and honest boundary

Make every **publicly publishable input and output used by the Chicago Budget site** findable on GitHub, organized by budget and by stable tree ID, with a fresh-clone reproduction path and links from site boxes to their data and sources. Do not equate this with publishing identifiable employee/payee records. The private roster and payroll-name inputs remain excluded, and any data that cannot legally or safely be mirrored must have a source URL, checksum, reason for exclusion, and a safe derived alternative. A rebuild that needs private records must be labeled as such until a public-safe replacement exists.

Current state (2026-10-05): `main` tracks 78 processed files in `data/`, 37 research files, and builders. It does **not** track `raw/` (3.2 GB locally), `data/people/` (44 MB), `data/budget.db` (67 MB), or `site/public/data/` (78 MB, about 351 JSON files plus directories). The live site already serves the privacy-filtered JSON export, including 47,360 boxes in 296 chunks. `build/inputs.sha256` pins 12 essential raw inputs, but a new clone cannot fetch all of them without the unpublished input archive. Never `git add -f raw/` or unignore these paths wholesale.

## Proposed layout

Keep existing `data/*.json`, `data/*.csv`, and `data/splits/` as processed evidence for now; document their roles and migrate references only with tested compatibility. Introduce a versioned public release directory whose budget hierarchy is navigable without guessing hash filenames:

```text
data/
  README.md                         # what is public, how to rebuild, privacy boundary
  catalog.json                      # inventory, status, checksums, licenses, upstream links
  public/2026/
    manifest.json                   # snapshot/commit, counts, roots, checksums, schema version
    sources.json                    # stable source IDs, URLs, dates, licenses, local evidence paths
    tree-index.json                 # every node ID -> root, parent ID, display path, chunk path
    tree/
      city/<function>/<department-or-owner-id>.json
      cps/<function>/<unit-or-owner-id>.json
      parks/<function>/<unit-or-owner-id>.json
      city-twice/<owner-id>.json     # separate cross-fund view, never added to net City total
    facts/{jobs,schools,parks,vendors,context,gaps,headcounts}.json
    search/                         # derived index, if needed for byte-for-byte site parity
    side/                           # larger per-box supplemental records
    CHECKSUMS.sha256
  inputs/2026/
    README.md                       # curated input inventory, not a copy of all raw/
    ...                             # only cleared, name-free, reasonably sized input files
```

The exact chunk boundaries and folder slugs should be generated from current `manifest.json` owner IDs, not hand-edited. Preserve each box's canonical `id`, `parent_id`, `root`, signed `amount_cents`, `basis`, source IDs, and child arithmetic. `tree-index.json` should map every ID to its GitHub path and the corresponding `/city|cps|parks/box/<id>/` URL. Record `city-twice` as its own root to avoid double counting. A single canonical safe export should feed both this directory and `site/public/data/`; do not maintain two drifting copies. If changing runtime chunk URLs is too risky, keep the existing hash-named runtime files and add a generated human-readable index/path mapping in GitHub first, then change the site loader separately.

## Phased implementation

1. **Inventory and classification before any upload.** Generate a machine-readable catalog of every file actually read by `build/build_all.sh`, every processed `data/` input, and every emitted site JSON. For each file record role, budget root(s), upstream URL/publisher, retrieval date, format, SHA-256, size, license/redistribution assessment, personal-data risk, and disposition: Git-tracked, GitHub Release asset, upstream-only with fetch recipe, derived/redacted substitute, or private. Include the 12 pinned files, source PDFs/CSVs used in transformations, and the roster-dependent steps. Resolve missing provenance, not by silently omitting inputs. Distinguish source evidence from temporary downloads, audit snapshots, duplicate intermediates, and caches in the 3.2 GB `raw/` directory.
2. **Privacy and rights gate.** Audit the whole candidate publication, including SQLite tables, raw CSV/PDF text, source notes, JSON nested fields, filenames, metadata and any binary/release asset. Retain `data/people/` and `raw/people/` outside public artifacts. Publish only privacy-filtered payee and aggregate job-title outputs with small-group suppression, no roster names, identifiers or identifying descriptions. Review third-party source terms separately; this project's CC BY 4.0 license does not relicense upstream records. Run an independent leak review and maintainer sign-off **before** uploading any candidate artifact, since Git history and release assets can persist after deletion.
3. **Publish the safe snapshot as the source of truth.** Promote the validated public export to `data/public/2026/`, generate the navigable index, schema/field dictionary, checksums and machine-readable source catalog. Include `headcounts.json`, currently generated through the Astro endpoint, in the same snapshot and compare its deployed bytes/records. Ensure every site-consumed data file has one checked GitHub counterpart. Automate the build step that copies or transforms this snapshot to `site/public/data/`, keeping site URLs stable. Add a release tag such as `data-2026-v1`; future corrections get a new immutable version and a changelog, not silent replacement.
4. **Provide reproducible inputs, not an unreviewed raw dump.** Move only cleared, minimal public input files into `data/inputs/2026/`; preserve `build/inputs.sha256` and update `build/inputs.py` to fetch the exact checked versions from GitHub and/or official upstream URLs. For large cleared files or a sanitized SQLite convenience snapshot, attach versioned, checksummed assets to a GitHub Release rather than placing huge binaries in ordinary Git. GitHub warns above 50 MiB and blocks files above 100 MiB; the current 67 MB database deserves a release asset **only after** a table-by-table privacy audit, preferably regenerated solely from the safe export. Do not publish local audit databases, 3.2 GB of exploratory raw files, or named rosters merely to claim completeness. If a private input affects output, either replace that dependency with a public-safe aggregate artifact plus documented method, or explicitly mark that portion not publicly reproducible.
5. **Connect GitHub, site, and users.** Add `Data & methods` documentation and stable download links for City, CPS, Parks, cross-fund City, sources, and the complete snapshot. On each box, link to its tree chunk/ID and cited source. Explain planned budget vs actual payment, dollars stored as integer cents, negative adjustments, FTE vs people, time periods, and why City cross-fund entries are not additive. Keep a direct link to the exact data tag/commit used by the current deployment.
6. **Prove publication in CI and from a fresh clone.** With public inputs only, run fetch/checksum, `build/build_all.sh`, `build/verify_db.py`, `build/export_site.py`, `build/validate_site_data.py`, the site build, and `tests/check_site_dist.py`. If roster-based scans need a private maintainer runner, show them as **not run** in public CI and require a separate signed release gate. Check all 47,360 IDs, four roots, 296 chunk owners, parent-child sums, provenance and source links; fail on missing/extra files, private paths, identifying names, wrong root totals, or differing site and repository snapshot checksums. Test public GitHub URLs and deployed JSON URLs from an unauthenticated session, then verify the site links on City/CPS/Parks and deep pages. Publish only when all gates pass.

## Release criteria

- A visitor can start from GitHub's `data/README.md`, select City/CPS/Parks, find any site box by ID, inspect its dollars/basis and source, and download the entire safe machine-readable snapshot.
- Every JSON response consumed by the deployed site is generated from that same tagged public snapshot and is covered by a checksum or a documented deterministic transform.
- A fresh clone can reproduce the published safe tree from published inputs; any still-private dependency is listed prominently as an explicit exception rather than called reproducible.
- Privacy/redistribution review and automated data/tree/site validation pass. Production deployment remains separate from this data-publication change until verified.

## Decision before implementation

Confirm whether “all underlying data” means **everything needed to reproduce the public, de-identified site** (recommended), not publication of identifiable third-party rosters or every downloaded public-record copy. The latter would conflict with the current privacy policy and involve separate redistribution review. Proceed with the safe scope by default; report any irreducible private dependencies honestly rather than publishing them.
