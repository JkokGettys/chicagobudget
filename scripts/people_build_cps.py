#!/usr/bin/env python3
"""CPS Employee Position Roster (12/31/2025) -> person-level (NAMES, gitignored) and aggregate (committed, no names) files.
Outputs:
  data/people/cps_positions_2025q4.json  (names, gitignored)
  data/comp_cps.json                     (no names)
Small-group rule: unit x job title groups under 5 positions are rolled into 'Other titles (groups under 5 positions)' per unit.
Per-position stats (median, mean, p90) are null when n < 5 (p90 when n < 10). Unit-level rows use positions that carry a salary.
Budget join: raw/cps/cps_2026_positions_unit_job.csv (FY26 budget book position rows by unit x job code).
"""
import csv, json, os, collections, xlrd
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_N, MIN_P90 = 5, 10
sh = xlrd.open_workbook(f'{ROOT}/raw/cps/roster_12312025.xls').sheet_by_index(0)
h = sh.row_values(0); ix = {k: i for i, k in enumerate(h)}
num = lambda v: float(v) if isinstance(v, float) else None
P = []
for i in range(1, sh.nrows):
    r = sh.row_values(i)
    P.append({'position_number': r[ix['Pos #']], 'name': (r[ix['Name']] or '').strip() or None, 'dept_id': r[ix['Dept ID']], 'department': r[ix['Department']],
              'fte': num(r[ix['FTE']]), 'class': r[ix['ClsIndc']], 'annual_salary': num(r[ix['Annual Salary']]), 'fte_annual_salary': num(r[ix['FTE Annual Salary']]),
              'annual_benefit_cost': num(r[ix['Annual Benefit Cost']]), 'job_code': r[ix['JobCode']], 'job_title': r[ix['Job Title']]})
json.dump({'meta': {'source': 'cps.edu Employee Position Roster, as of 12/31/2025 (raw/cps/roster_12312025.xls)', 'note': 'NAMES. Local analysis only, gitignored. Never publish.',
                    'fields': 'annual_salary = salary of the position as listed; fte_annual_salary = salary at the FTE listed; blank salary and name = reason not stated by CPS (likely vacant)'},
           'positions': P}, open(f'{ROOT}/data/people/cps_positions_2025q4.json', 'w'))

named = [p for p in P if p['name']]
sal = [p for p in P if p['fte_annual_salary'] is not None]
print('positions', len(P), 'named', len(named), 'with salary', len(sal))
print('salary-bearing positions with no name', sum(1 for p in sal if not p['name']), 'named without salary', sum(1 for p in named if p['fte_annual_salary'] is None))

BUD = collections.defaultdict(lambda: [0.0, 0.0])
for r in csv.DictReader(open(f'{ROOT}/raw/cps/cps_2026_positions_unit_job.csv')):
    b = BUD[(r['unit'], r['job_code'].replace('JC', ''))]; b[0] += float(r['fte']); b[1] += float(r['amount'])

def q(a, p): return round(float(np.percentile(a, p)), 0)
def stat(vals, label, out):
    n = len(vals); out[f'n_{label}'] = n
    if n >= MIN_N:
        out[f'median_{label}'] = q(vals, 50); out[f'mean_{label}'] = round(float(np.mean(vals)), 0); out[f'p90_{label}'] = q(vals, 90) if n >= MIN_P90 else None
    else: out[f'median_{label}'] = out[f'mean_{label}'] = out[f'p90_{label}'] = None

def agg(pl, base):
    o = dict(base)
    o['positions'] = len(pl); o['fte'] = round(sum(p['fte'] or 0 for p in pl), 2)
    sp = [p for p in pl if p['fte_annual_salary'] is not None]
    o['positions_with_salary'] = len(sp)
    o['fte_salary_total'] = round(sum(p['fte_annual_salary'] for p in sp), 0)
    o['annual_benefit_cost_total'] = round(sum(p['annual_benefit_cost'] or 0 for p in sp), 0)
    stat([p['fte_annual_salary'] for p in sp], 'fte_annual_salary', o)
    stat([p['annual_benefit_cost'] for p in sp if p['annual_benefit_cost'] is not None], 'annual_benefit_cost', o)
    return o

by_ut = collections.defaultdict(list)
for p in P: by_ut[(p['dept_id'], p['job_code'], p['job_title'], p['class'])].append(p)
by_unit = collections.defaultdict(list)
for k, v in by_ut.items(): by_unit[k[0]].append((k, v))
rows = []; units = []
for u, items in sorted(by_unit.items()):
    name = items[0][1][0]['department']
    shown = [(k, v) for k, v in items if len(v) >= MIN_N]
    rolled = [(k, v) for k, v in items if len(v) < MIN_N]
    while rolled and sum(len(v) for _, v in rolled) < MIN_N and shown:
        shown.sort(key=lambda kv: len(kv[1])); rolled.append(shown.pop(0))
    for k, v in sorted(shown, key=lambda kv: -sum(p['fte_annual_salary'] or 0 for p in kv[1])):
        b = BUD.get((f'U{u}', k[1]))
        o = agg(v, {'unit': f'U{u}', 'department': name, 'job_code': k[1], 'job_title': k[2], 'class': k[3]})
        o['budget_fy26_fte'] = round(b[0], 2) if b else None; o['budget_fy26_amount'] = round(b[1], 0) if b else None
        o['budget_fy26_avg_rate'] = round(b[1] / b[0], 0) if b and b[0] else None
        rows.append(o)
    allr = [p for _, v in rolled for p in v]
    if allr:
        bs = [BUD.get((f'U{u}', k[1])) for k, _ in rolled]
        o = agg(allr, {'unit': f'U{u}', 'department': name, 'job_code': None, 'job_title': 'Other titles (groups under 5 positions)', 'class': None})
        o['titles_rolled_up'] = len(rolled)
        o['budget_fy26_fte'] = round(sum(b[0] for b in bs if b), 2); o['budget_fy26_amount'] = round(sum(b[1] for b in bs if b), 0); o['budget_fy26_avg_rate'] = None
        if o['positions'] < MIN_N:
            for k in ('fte_salary_total', 'annual_benefit_cost_total'): o[k] = None
            o['suppressed'] = 'fewer than 5 positions'
        rows.append(o)
    us = agg([p for _, v in items for p in v], {'unit': f'U{u}', 'department': name})
    us['titles_shown'] = len(shown); us['titles_rolled_up'] = len(rolled)
    ub = [BUD.get((f'U{u}', k[1])) for k, _ in items]
    us['budget_fy26_fte'] = round(sum(b[0] for b in ub if b), 2); us['budget_fy26_amount'] = round(sum(b[1] for b in ub if b), 0)
    if us['positions_with_salary'] < MIN_N:
        for k in ('fte_salary_total', 'annual_benefit_cost_total'): us[k] = None
        us['suppressed'] = 'fewer than 5 positions'
    units.append(us)

# district-wide by job title (all units): titles with >= 5 positions
dt = collections.defaultdict(list)
for p in P: dt[(p['job_code'], p['job_title'])].append(p)
titles = []
for k, v in dt.items():
    if len(v) < MIN_N: continue
    o = agg(v, {'job_code': k[0], 'job_title': k[1], 'units': len({p['dept_id'] for p in v}), 'class': ','.join(sorted({p['class'] for p in v}))})
    sp = [p['fte_annual_salary'] for p in v if p['fte_annual_salary'] is not None]
    o['count_ge_200k'] = sum(1 for x in sp if x >= 2e5)
    titles.append(o)
titles.sort(key=lambda o: -(o['fte_salary_total'] or 0))
small_titles = [v for v in dt.values() if len(v) < MIN_N]
other = agg([p for v in small_titles for p in v], {'job_code': None, 'job_title': 'Other titles (groups under 5 positions)'})
other['titles_rolled_up'] = len(small_titles)
# findings by title only
sp_all = np.array([p['fte_annual_salary'] for p in sal])
ge = {str(t): int((sp_all >= t).sum()) for t in (150000, 200000)}
ge_by_title = collections.Counter((p['job_title']) for p in sal if p['fte_annual_salary'] >= 200000)
ge_list = [{'job_title': t, 'positions_ge_200k': n, 'positions_in_title': len(dt[[k for k in dt if k[1] == t][0]]) if False else sum(len(v) for k, v in dt.items() if k[1] == t)}
           for t, n in ge_by_title.most_common() if sum(len(v) for k, v in dt.items() if k[1] == t) >= MIN_N and n >= MIN_N]
ge_hidden = sum(n for t, n in ge_by_title.items() if not (n >= MIN_N and sum(len(v) for k, v in dt.items() if k[1] == t) >= MIN_N))
cls = {}
for c in ('T', 'E'):
    pl = [p for p in sal if p['class'] == c]
    o = {'positions': len(pl), 'fte_salary_total': round(sum(p['fte_annual_salary'] for p in pl), 0), 'annual_benefit_cost_total': round(sum(p['annual_benefit_cost'] or 0 for p in pl), 0)}
    stat([p['fte_annual_salary'] for p in pl], 'fte_annual_salary', o); cls[c] = o
tot = {'positions': len(P), 'fte': round(sum(p['fte'] or 0 for p in P), 1), 'positions_with_salary': len(sal), 'positions_without_salary': len(P) - len(sal),
       'fte_salary_total': round(sum(p['fte_annual_salary'] for p in sal), 0), 'annual_salary_total_as_listed': round(sum(p['annual_salary'] for p in sal if p['annual_salary'] is not None), 0),
       'annual_benefit_cost_total': round(sum(p['annual_benefit_cost'] or 0 for p in sal), 0), 'units': len(by_unit)}
fte_sal = {'fte_salary_total_incl_unsalaried_fte_weighted': None}
out = {'meta': {'generated_by': 'scripts/people_build_cps.py', 'names': False, 'source': 'CPS Employee Position Roster as of 2025-12-31 (cps.edu), budget join: FY26 budget book positions (cps_2026_positions_unit_job.csv)',
                'small_group_rule': 'unit x job title groups under 5 positions are rolled into "Other titles (groups under 5 positions)" per unit. Per-position stats null when n < 5, p90 null when n < 10. Unit totals suppressed when under 5 salaried positions.',
                'definitions': {'fte_annual_salary': 'roster "FTE Annual Salary" (salary at the FTE of the position). Positions with a blank salary have a blank name too and carry no cost columns. The roster does not say why (most likely vacant or unfilled positions), so they are counted separately and excluded from salary statistics',
                                'class': 'T = teacher/school-based positions, E = everyone else (roster ClsIndc)', 'annual_benefit_cost': 'roster "Annual Benefit Cost", employer cost per position'},
                'caveat': 'This is a position roster at one date, not payroll. No overtime, stipends, or actual earnings.'},
       'totals': tot, 'by_class': cls, 'thresholds_fte_annual_salary': ge, 'positions_ge_200k_by_title': ge_list, 'positions_ge_200k_in_titles_or_counts_under_5': ge_hidden,
       'districtwide_by_title': titles, 'districtwide_other_titles': other, 'units': units, 'unit_by_title': rows}
json.dump(out, open(f'{ROOT}/data/comp_cps.json', 'w'), indent=1)
print(json.dumps({'tot': tot, 'cls': cls, 'ge': ge, 'ge_list': ge_list[:10], 'hidden': ge_hidden}, indent=1))
print(len(rows), 'unit x title rows;', len(titles), 'district titles; size MB', os.path.getsize(f'{ROOT}/data/comp_cps.json') / 1e6)
