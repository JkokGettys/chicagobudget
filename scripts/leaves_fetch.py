#!/usr/bin/env python3
"""Fetch the extra public sources used by scripts/leaves_inventory.py into raw/leaves/ (gitignored).

1. Payroll costing (dawh-m56b) 2025: premium-pay appropriations (overtime, duty availability, holiday,
   comp time, specialty pay, wage adjustments, uniform allowance ...) by department x job title with
   distinct employee counts. Lets a big premium-pay budget line be shown as "N employees x $average".
2. Current Employee Names, Salaries (xzkq-xp2w) is NOT needed (we use positions).
3. Probe log: HTTP status of every candidate source URL the hunt tried (leaves_sources_probe.json).
Idempotent: skips files that exist.
"""
import json, os, sys, time, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{ROOT}/raw/leaves'
os.makedirs(OUT, exist_ok=True)
BASE = 'https://data.cityofchicago.org/resource/dawh-m56b.json'

def get(url, timeout=600):
    req = urllib.request.Request(url, headers={'User-Agent': 'chicago-budget-research/1.0'})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()

def payroll(year):
    path = f'{OUT}/payroll_{year}_approp_dept_title.json'
    if os.path.exists(path):
        return
    params = {
        '$select': 'appropriation,department,title,sum(amount) as amt,count(distinct employee_dataset_id) as n',
        '$where': f"payroll_year={year} AND appropriation_code in ('A0020','A0021','A0022','A0024','A0060','A0088','A0027','A0091','A0003','A0006','A0015')",
        '$group': 'appropriation,department,title', '$limit': '50000'}
    url = BASE + '?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            d = json.loads(get(url))
            json.dump(d, open(path, 'w'))
            print('payroll', year, len(d), 'rows')
            return
        except Exception as e:
            print('retry', e); time.sleep(5)

if __name__ == '__main__':
    for y in (2025,):
        payroll(y)
