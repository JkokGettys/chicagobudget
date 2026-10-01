#!/usr/bin/env python3
"""Fetch person-level source data for research/employee_comp.md. Caches under raw/people/ (gitignored).
 - xzkq-xp2w  City current employees (names, salary/hourly, title, dept)
 - dawh-m56b  Payroll costing, grouped SERVER-SIDE by employee x pay_element x dept x title x fund x appropriation (2025),
              and by dept x title x fund x appropriation x pay_element (2024 and 2025, no employee key)
 - 9v3e-pcjs  Workforce Vacancies (positions, employees, vacancies by title)
Names are kept in raw/people and data/people only (both gitignored). Site-facing files never contain names.
"""
import json, os, time, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{ROOT}/raw/people'; os.makedirs(OUT, exist_ok=True)
SOC = 'https://data.cityofchicago.org/resource/'

def get(ds, params, tries=5):
    url = SOC + ds + '.json?' + urllib.parse.urlencode(params)
    for a in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=900) as r:
                return json.load(r)
        except Exception as e:
            print('retry', ds, e, flush=True); time.sleep(5 * (a + 1))
    raise SystemExit('failed ' + url[:200])

def fetch(name, ds, params, page=50000):
    path = f'{OUT}/{name}.json'
    if os.path.exists(path): return json.load(open(path))
    rows = []; off = 0
    while True:
        d = get(ds, dict(params, **{'$limit': page, '$offset': off}))
        rows += d; print(name, off, len(d), flush=True)
        if len(d) < page: break
        off += page
    json.dump(rows, open(path, 'w')); return rows

def grouped(name, keys, where, extra=''):
    k = ','.join(keys)
    return fetch(name, 'dawh-m56b', {'$select': k + ',sum(amount) as amt' + extra, '$where': where, '$group': k, '$order': k})

fetch('emp_current', 'xzkq-xp2w', {'$order': ':id'})
fetch('vacancies', '9v3e-pcjs', {'$order': ':id'})
# 'employee' = "<employee_dataset_id> - <LAST,  FIRST M>"
grouped('pay2025_emp', ['employee', 'pay_element', 'department_code', 'title_code', 'fund_code', 'appropriation_code'], 'payroll_year=2025')
K2 = ['department_code', 'title_code', 'fund_code', 'appropriation_code', 'pay_element']
for yr in (2024, 2025):
    grouped(f'pay{yr}_title', K2, f'payroll_year={yr}', ',count(distinct employee_dataset_id) as emps')
N = ['department_code', 'department', 'title_code', 'title', 'appropriation_code', 'appropriation', 'fund_code', 'fund']
fetch('names_2025', 'dawh-m56b', {'$select': ','.join(N), '$where': 'payroll_year=2025', '$group': ','.join(N), '$order': ','.join(N)})
# periods paid per employee in 2025 (to flag full-year vs partial-year); keyed by employee_dataset_id
fetch('pay2025_periods', 'dawh-m56b', {'$select': 'employee_dataset_id,count(distinct payroll_period) as periods,min(payroll_period) as first_p,max(payroll_period) as last_p',
      '$where': 'payroll_year=2025', '$group': 'employee_dataset_id', '$order': 'employee_dataset_id'})
# 2025 budget ordinance appropriations by account (for reconciling 2025 actual payroll)
fetch('ord2025_approp', 't59y-fr3k', {'$order': ':id'})
# distinct paid employees per dept x title (cannot be summed from the finer pay tables)
for yr in (2024, 2025):
    fetch(f'pay{yr}_dt_emps', 'dawh-m56b', {'$select': 'department_code,title_code,count(distinct employee_dataset_id) as emps,sum(amount) as amt',
          '$where': f'payroll_year={yr}', '$group': 'department_code,title_code', '$order': 'department_code,title_code'})
