#!/usr/bin/env python3
"""Park District: budgeted positions by title (data/parks_2026.json, from the 2026 Budget Appropriations PDF). No names or per-person pay are published
(see research/employee_comp.md), so this is budget data: FTE and budgeted salary dollars per unit x fund x job title.
Outputs:
  data/people/parks_positions.json  (position rows by unit/fund, no names exist; gitignored with the rest of data/people for consistency)
  data/comp_parks.json              (title aggregates; titles with fewer than 5 budgeted FTE are rolled into 'Other titles'; no per-position stats exist)
"""
import json, os, collections
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MIN_FTE = 5
d = json.load(open(f'{ROOT}/data/parks_2026.json'))
rows = []
def walk(n, path):
    """path = names from the function node down to the parent of this node."""
    if n.get('type') == 'position':
        rows.append({'function': path[0], 'path': path[:], 'job_code': n['job_code'], 'title': n['name'],
                     'fte2026': n['fte2026'], 'fte2025': n['fte2025'], 'budget2026': n['amount2026'], 'budget2025': n['amount2025']}); return
    for c in n.get('children', []): walk(c, path + [n['name']])
for f in d['tree']['children']: walk(f, [])
json.dump({'meta': {'source': d['meta']['source_pdf'], 'note': 'No names or individual salaries are published by the Park District. Budgeted FTE and salary dollars per position row. 2026 and 2025 budget columns.'}, 'positions': rows},
          open(f'{ROOT}/data/people/parks_positions.json', 'w'))
print(len(rows), 'position rows', sum(r['fte2026'] for r in rows), 'FTE', sum(r['budget2026'] for r in rows), '$')
bt = collections.defaultdict(lambda: {'fte2026': 0.0, 'fte2025': 0.0, 'b2026': 0, 'b2025': 0, 'rows': 0, 'units': set(), 'codes': set(), 'fte_rows': []})
for r in rows:
    t = bt[r['title']]; t['fte2026'] += r['fte2026']; t['fte2025'] += r['fte2025'] or 0; t['b2026'] += r['budget2026']; t['b2025'] += r['budget2025'] or 0
    t['rows'] += 1; t['units'].add(tuple(r['path'][:3])); t['codes'].add(r['job_code'])
    if r['fte2026']: t['fte_rows'].append((r['budget2026'] / r['fte2026'], r['fte2026']))
titles = []; other = {'fte2026': 0.0, 'fte2025': 0.0, 'budget2026': 0, 'budget2025': 0, 'titles': 0}
for name, t in bt.items():
    if t['fte2026'] < MIN_FTE:
        other['fte2026'] += t['fte2026']; other['fte2025'] += t['fte2025']; other['budget2026'] += t['b2026']; other['budget2025'] += t['b2025']; other['titles'] += 1; continue
    titles.append({'title': name, 'job_codes': sorted(t['codes']), 'budget_rows': t['rows'], 'units': len(t['units']), 'fte2026': round(t['fte2026'], 1), 'fte2025': round(t['fte2025'], 1),
                   'budget2026': t['b2026'], 'budget2025': t['b2025'], 'budgeted_dollars_per_fte_2026': round(t['b2026'] / t['fte2026']) if t['fte2026'] else None,
                   'budgeted_dollars_per_fte_2025': round(t['b2025'] / t['fte2025']) if t['fte2025'] else None})
titles.sort(key=lambda x: -x['budget2026'])
fn = collections.defaultdict(lambda: {'fte2026': 0.0, 'budget2026': 0})
for r in rows: fn[r['function']]['fte2026'] += r['fte2026']; fn[r['function']]['budget2026'] += r['budget2026']
tot_f = sum(r['fte2026'] for r in rows); tot_b = sum(r['budget2026'] for r in rows)
out = {'meta': {'generated_by': 'scripts/people_build_parks.py', 'names': False, 'source': d['meta']['source_pdf'],
                'basis': 'BUDGET: budgeted positions and salary dollars in the 2026 Budget Appropriations, not actual pay. The Park District publishes no names, individual salaries, overtime or payroll data that we could find.',
                'small_group_rule': 'titles with fewer than 5 budgeted FTE district-wide are rolled into "Other titles". Budgeted dollars per FTE is a budget rate, not an individual salary.',
                'ties': 'rows in data/parks_2026.json sum to 3,212.4 FTE and $220,590,509. research/park_district.md section 3.5 reports 3,212.7 FTE and $220,590,557 from the raw parse. Printed total is 3,213.0 FTE.'},
       'totals': {'position_rows': len(rows), 'fte2026': round(tot_f, 1), 'budget2026': tot_b, 'distinct_titles': len(bt), 'titles_shown': len(titles)},
       'by_function': [{'function': k, 'fte2026': round(v['fte2026'], 1), 'budget2026': v['budget2026']} for k, v in sorted(fn.items(), key=lambda kv: -kv[1]['budget2026'])],
       'by_title': titles, 'other_titles': {k: (round(v, 1) if isinstance(v, float) else v) for k, v in other.items()}}
json.dump(out, open(f'{ROOT}/data/comp_parks.json', 'w'), indent=1)
print(json.dumps(out['totals']), out['other_titles'])
for t in titles[:8]: print(t['title'], t['fte2026'], t['budget2026'], t['budgeted_dollars_per_fte_2026'], t['units'])
print(out['by_function'])
