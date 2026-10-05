## What changed?

- Box IDs changed (if any):
- Public source URL and page (for data):
- Does this add any person's name to a website-facing field? No / Explain:
- Does this intentionally change the versioned `data/public/2026/` release? No / Explain:

## Checks

- [ ] `build/build_all.sh` passed locally using the published input snapshot
- [ ] For site changes: `cd site && npm ci && npm run check && npm test && npm run build`
- [ ] For site changes: `python3 tests/check_site_dist.py site/dist`
- [ ] Only intended files are staged; no generated database, site build, raw cache or markdown plans
- [ ] I read the contributor agreement in `CONTRIBUTING.md`

CI rebuilds budgets and checks website-display privacy using published rosters. Maintainers also check a source manually and inspect the deployed site before release. CI does not deploy.
