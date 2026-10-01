#!/usr/bin/env python3
"""Fetch ACTUAL 2024/2025 payroll aggregates from Employee Payroll Data (FMPS Payroll
Costing), Socrata dataset dawh-m56b, grouped server-side. Raw responses cached in
raw/personnel/payroll_*.json. Used for overtime-by-department/unit and actual vs budget.
"""
import json, os, sys, time, urllib.parse, urllib.request
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = f'{ROOT}/raw/personnel'
BASE = 'https://data.cityofchicago.org/resource/dawh-m56b.json'
os.makedirs(OUT, exist_ok=True)

def q(name, select, where, group, order=None, limit=50000):
    path = f'{OUT}/payroll_{name}.json'
    if os.path.exists(path):
        return json.load(open(path))
    params = {'$select': select, '$where': where, '$group': group, '$limit': str(limit)}
    if order: params['$order'] = order
    url = BASE + '?' + urllib.parse.urlencode(params)
    for attempt in range(4):
        try:
            with urllib.request.urlopen(url, timeout=600) as r:
                d = json.load(r)
            json.dump(d, open(path, 'w'))
            print(name, len(d), 'rows', flush=True)
            return d
        except Exception as e:
            print('retry', name, e, flush=True); time.sleep(5)
    raise SystemExit('failed ' + name)

for yr in (2025, 2024):
    w = f'payroll_year={yr}'
    q(f'{yr}_dept_approp', 'department,appropriation,sum(amount) as amt,count(distinct employee_dataset_id) as n', w, 'department,appropriation')
    q(f'{yr}_dept_fund_approp', 'fund_code,department_code,appropriation_code,sum(amount) as amt', w, 'fund_code,department_code,appropriation_code')
    # overtime appropriation A0020 and OT pay elements by department x title
    q(f'{yr}_ot_dept_title', 'department,title,sum(amount) as amt,count(distinct employee_dataset_id) as n',
      w + " AND appropriation_code='A0020'", 'department,title')
    q(f'{yr}_dept_payelem', 'department,pay_element,sum(amount) as amt', w, 'department,pay_element')

# Scheduled Wage Adjustments (A0003) actually paid, by pay element and department
for yr in (2025, 2024):
    w = f"payroll_year={yr} AND appropriation_code='A0003'"
    q(f'{yr}_swa_payelem', 'pay_element,sum(amount) as amt', w, 'pay_element')
    q(f'{yr}_swa_dept', 'department,sum(amount) as amt', w, 'department')
# Employee Payroll counts of distinct employees by dept in 2025 (for filled-vs-budgeted)
q('2025_dept_headcount', 'department,count(distinct employee_dataset_id) as n', 'payroll_year=2025 AND appropriation_code=\'A0005\'', 'department')

# Employee-level OT totals (aggregate stats only are published in our outputs)
for yr in (2025,):
    q(f'{yr}_ot_employee', 'department,employee_dataset_id,sum(amount) as amt',
      f"payroll_year={yr} AND appropriation_code='A0020'", 'department,employee_dataset_id', limit=100000)

# Current employee roster aggregated by department x title (xzkq-xp2w). Aggregates only, no names.
def roster():
    path = f'{OUT}/emp_dept_title.json'
    if os.path.exists(path):
        return
    params = {'$select': 'department,job_titles,salary_or_hourly,full_or_part_time,count(*) as n,sum(annual_salary) as sal,avg(annual_salary) as avg_sal',
              '$group': 'department,job_titles,salary_or_hourly,full_or_part_time', '$limit': '50000'}
    url = 'https://data.cityofchicago.org/resource/xzkq-xp2w.json?' + urllib.parse.urlencode(params)
    with urllib.request.urlopen(url, timeout=600) as r:
        json.dump(json.load(r), open(path, 'w'))
roster()

# Overtime appropriation by pay element (A0020 only)
for yr in (2025, 2024):
    q(f'{yr}_ot_payelem', 'department,pay_element,sum(amount) as amt', f"payroll_year={yr} AND appropriation_code='A0020'", 'department,pay_element')

# 2026 year to date (payroll periods 1 to 6 at fetch time): Scheduled Wage Adjustments by pay element and department
w26 = "payroll_year=2026 AND appropriation_code='A0003'"
q('2026_swa_payelem', 'pay_element,sum(amount) as amt,max(payroll_period) as last_period', w26, 'pay_element')
q('2026_swa_dept', 'department,sum(amount) as amt', w26, 'department')
