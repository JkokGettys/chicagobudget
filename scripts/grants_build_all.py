#!/usr/bin/env python3
"""Rebuild data/city_grants_2026.json and data/city_capital_2026.json from public sources, in dependency order."""
import os, subprocess, sys
here = os.path.dirname(os.path.abspath(__file__))
for s in ['grants_summary_g.py', 'grants_action_plan.py', 'grants_capital_cip.py', 'grants_aldermanic_menu.py', 'grants_usaspending.py', 'grants_reserve_attribution.py']:
    print('==', s); subprocess.check_call([sys.executable, os.path.join(here, s)])
