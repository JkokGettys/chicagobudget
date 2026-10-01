"""Cross check: Mid-Year Grants report (iyu8-jkf8) vs the 2026 ordinance Reserve Balance (909A)
and GRANTS fund lines, by department. Shows whether the grants report can explain the $1.9B
"Reserve Balance" placeholder at project level.

Run: python3 scripts/contracts_grants_check.py   (prints markdown tables)
"""
import os

import pandas as pd

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
a = pd.read_json(os.path.join(ROOT, "raw", "city_appropriations_2026.json"), dtype=str)
a["amt"] = pd.to_numeric(a["_ordinance_amount_"])
g = pd.read_csv(os.path.join(ROOT, "raw", "contracts", "midyear_grants.csv"), dtype=str)
for c in ["budget", "expended_project_to_date", "funds_available_project_to_date"]:
    g[c] = pd.to_numeric(g[c])
g = g[g.data_extract_as_of_date.str.startswith("2026")]


def key(s):
    # the grants report drops the leading "Chicago" (Department of Public Health vs Chicago Department of ...)
    return (s.str.lower().str.replace("&", "and").str.replace(r"[^a-z ]", "", regex=True).str.strip()
            .str.replace(r"^chicago ", "", regex=True))


a["k"] = key(a.department_description)
g["k"] = key(g.department_description)
res = a[a.appropriation_account == "909A"].groupby("k").amt.sum().rename("reserve_909A")
gr = a[a.fund_type == "GRANTS"].groupby("k").amt.sum().rename("grants_funds_total")
mg = g.groupby("k").agg(midyear_budget=("budget", "sum"), midyear_available=("funds_available_project_to_date", "sum"),
                        projects=("budget", "size"), under_1M=("budget", lambda s: int((s < 1e6).sum())))
t = pd.concat([res, gr, mg], axis=1).fillna(0).sort_values("grants_funds_total", ascending=False)
names = a.drop_duplicates("k").set_index("k").department_description
print("| Dept | 2026 Reserve Balance (909A) | 2026 GRANTS-fund lines | Mid-year grants report budget (May 2026) | Projects | Projects under $1M |")
print("|---|---:|---:|---:|---:|---:|")
for k, r in t.head(14).iterrows():
    print("| {} | ${:,.1f}M | ${:,.1f}M | ${:,.1f}M | {:,.0f} | {:,.0f} |".format(
        names.get(k, k), r.reserve_909A / 1e6, r.grants_funds_total / 1e6, r.midyear_budget / 1e6, r.projects, r.under_1M))
print("| Total | ${:,.1f}M | ${:,.1f}M | ${:,.1f}M | {:,.0f} | {:,.0f} |".format(
    t.reserve_909A.sum() / 1e6, t.grants_funds_total.sum() / 1e6, t.midyear_budget.sum() / 1e6, t.projects.sum(), t.under_1M.sum()))
