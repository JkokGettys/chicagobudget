#!/usr/bin/env bash
# Rebuild the whole budget tree (City, Park District, CPS) into data/budget.db.
# Each builder exits non-zero if any check fails, and this script stops at the first failure.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f data/budget.db
python3 build/city_tree.py
python3 build/parks_tree.py
python3 build/cps_tree.py
python3 build/verify_db.py
