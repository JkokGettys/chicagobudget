#!/usr/bin/env bash
# Rebuild the whole budget tree (City, Park District, CPS) into data/budget.db.
# Each builder exits non-zero if any check fails, and this script stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."
bash build/fetch_inputs.sh
rm -f data/budget.db
python3 build/city_tree.py
python3 build/parks_tree.py
python3 build/cps_tree.py
python3 build/site_tables.py
python3 build/verify_db.py
python3 build/export_site.py
python3 build/validate_site_data.py
