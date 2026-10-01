#!/usr/bin/env python3
"""Build City person-level (LOCAL, names, gitignored) and aggregate (committed, no names) compensation files.
Inputs (raw/people, from scripts/people_fetch.py): emp_current, pay2025_emp, pay2025_periods, pay2024_title, pay2025_title,
  pay2024_dt_emps, pay2025_dt_emps, names_2025, vacancies, ord2025_approp; raw/city_positions_2026.json, raw/city_appropriations_2026.json
Outputs:
  data/people/city_employees_2026.json   (NAMES, gitignored)
  data/comp_city_2025.json               (no names; groups under 5 people get no per-person stats)
Small-group rule: a dept x title group is shown only if >= 5 people (paid in 2025 or currently employed); smaller ones are rolled into
'Other titles (groups under 5 people)' per department. Per-person statistics need n >= 5, and p90 needs n >= 10.
"""
import json, os, re, collections, math, statistics
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
R = f'{ROOT}/raw/people'; os.makedirs(f'{ROOT}/data/people', exist_ok=True)
L = lambda n: json.load(open(f'{R}/{n}.json'))
MIN_N, MIN_P90 = 5, 10

pay = L('pay2025_emp'); cur = L('emp_current'); per = {r['employee_dataset_id']: r for r in L('pay2025_periods')}
names = L('names_2025'); vac = L('vacancies')
DN = {r['department_code']: r['department'].split(' - ', 1)[1] for r in names}
TN = {r['title_code']: r['title'].split(' - ', 1)[1] for r in names}
AN = {r['appropriation_code']: r['appropriation'].split(' - ', 1)[1] for r in names}
norm = lambda s: re.sub(r'\s+', ' ', (s or '').upper()).strip()

# ---------- pay element classification ----------
REG_EL = {'REGULAR SALARY', 'REGULAR TIME', 'REG 1_15', 'REG 1_125', 'TIME ENTRY WAGES'}
def category(ap, el):
    if ap == 'A0020': return 'overtime'
    if ap == 'A0003': return 'retro_lumpsum'
    if ap in ('A0005', 'A0017', 'A0000') and (el in REG_EL or (el.startswith('MULT ') and el.endswith(' RATE 1_0'))): return 'regular'
    return 'other_premium'
CATS = ('regular', 'overtime', 'other_premium', 'retro_lumpsum')

# ---------- payroll persons ----------
P = {}
for r in pay:
    eid, _, nm = r['employee'].partition(' - ')
    p = P.setdefault(eid, {'name': norm(nm), 'cat': collections.defaultdict(float), 'el': collections.defaultdict(float),
                           'dt': collections.defaultdict(float), 'dtall': collections.defaultdict(float)})
    a = float(r['amt']); c = category(r['appropriation_code'], r['pay_element'])
    p['cat'][c] += a; p['el'][f"{r['appropriation_code']}|{r['pay_element']}"] += a
    p['dtall'][(r['department_code'], r['title_code'])] += a
    if c != 'retro_lumpsum': p['dt'][(r['department_code'], r['title_code'])] += a
for eid, p in P.items():
    src = p['dt'] if p['dt'] else p['dtall']
    p['primary'] = max(src.items(), key=lambda kv: kv[1])[0]
    p['total'] = sum(p['cat'].values()); p['total_x'] = p['total'] - p['cat']['retro_lumpsum']
    pr = per[eid]; p['periods'] = int(pr['periods']); p['first'] = int(pr['first_p']); p['last'] = int(pr['last_p'])
print('payroll persons', len(P))

# ---------- join current roster -> payroll ids ----------
byname = collections.defaultdict(list)
for eid, p in P.items(): byname[p['name']].append(eid)
curn = collections.defaultdict(list)
for i, c in enumerate(cur): curn[norm(c['name'])].append(i)
# learn current-dept-name -> dept code from unambiguous 1:1 name matches
vote = collections.defaultdict(collections.Counter)
for n, idx in curn.items():
    if len(idx) == 1 and len(byname.get(n, [])) == 1:
        vote[norm(cur[idx[0]]['department'])][P[byname[n][0]]['primary'][0]] += 1
DMAP = {d: v.most_common(1)[0][0] for d, v in vote.items()}
print('dept map learned', len(DMAP), 'of', len({norm(c['department']) for c in cur}))
match = {}      # cur index -> eid
method = {}
for n, idx in curn.items():
    cands = byname.get(n, [])
    if not cands: continue
    if len(idx) == 1 and len(cands) == 1:
        match[idx[0]] = cands[0]; method[idx[0]] = 'unique_name'; continue
    def score(i, e):
        c = cur[i]; p = P[e]; s = 0
        if DMAP.get(norm(c['department'])) in {d for d, t in p['dtall']}: s += 2
        if norm(c['job_titles']) in {norm(TN.get(t, '')) for d, t in p['dtall']}: s += 1
        return s
    sc = {(i, e): score(i, e) for i in idx for e in cands}
    for (i, e), s in sorted(sc.items(), key=lambda kv: -kv[1]):
        if s < 2 or i in match or e in set(match.values()): continue
        best_i = max(sc[(i, x)] for x in cands); best_e = max(sc[(y, e)] for y in idx)
        ties_i = sum(1 for x in cands if sc[(i, x)] == s); ties_e = sum(1 for y in idx if sc[(y, e)] == s)
        if s == best_i == best_e and ties_i == 1 and ties_e == 1:
            match[i] = e; method[i] = 'name+dept_title'
print('matched current employees', len(match), 'of', len(cur))
matched_eids = set(match.values())

def annualize(c):
    if c.get('salary_or_hourly') == 'SALARY' and c.get('annual_salary'): return float(c['annual_salary'])
    if c.get('hourly_rate'):
        h = float(c.get('typical_hours') or 40); return float(c['hourly_rate']) * h * 52
    return None

def pay_block(p):
    return {'total': round(p['total'], 2), 'total_excl_retro_lumpsum': round(p['total_x'], 2),
            **{k: round(p['cat'][k], 2) for k in CATS}, 'periods_paid': p['periods'], 'first_period': p['first'], 'last_period': p['last'],
            'primary_dept': p['primary'][0], 'primary_title_code': p['primary'][1],
            'depts_titles_paid': sorted({f'{d}/{t}' for d, t in p['dtall']}),
            'by_pay_element': {k: round(v, 2) for k, v in sorted(p['el'].items(), key=lambda kv: -kv[1]) if abs(v) >= 0.005}}

people = []
for i, c in enumerate(cur):
    rec = {'name': c['name'], 'title': c['job_titles'], 'department': c['department'], 'full_or_part_time': c['full_or_part_time'],
           'pay_basis': c['salary_or_hourly'], 'typical_hours_per_week': c.get('typical_hours'), 'annual_salary': c.get('annual_salary'),
           'hourly_rate': c.get('hourly_rate'), 'annualized_base': annualize(c)}
    e = match.get(i)
    rec['payroll_employee_dataset_id'] = e; rec['join_method'] = method.get(i)
    rec['pay2025'] = pay_block(P[e]) if e else None
    people.append(rec)
others = [{'name': p['name'], 'payroll_employee_dataset_id': e, 'pay2025': pay_block(p)} for e, p in P.items() if e not in matched_eids]
json.dump({'meta': {'source_roster': 'data.cityofchicago.org xzkq-xp2w (current employees, snapshot at fetch time)',
                    'source_pay': 'dawh-m56b payroll costing 2025 grouped by employee x pay element x dept x title x fund x appropriation',
                    'categories': 'regular = A0005/A0017/A0000 regular salary/time and multi-rate straight time; overtime = A0020; retro_lumpsum = A0003; other_premium = everything else',
                    'note': 'NAMES. Local analysis only, gitignored. Never publish.'},
           'current_employees': people, 'paid_2025_not_matched_to_current_roster': others},
          open(f'{ROOT}/data/people/city_employees_2026.json', 'w'))

# ---------- budget (positions) ----------
pos = json.load(open(f'{ROOT}/raw/city_positions_2026.json'))
SPECIAL = {'Schedule Salary Adjustments', 'Contract Wage Increment - Prevailing Rate', 'Fringe Benefits'}
BUD = collections.defaultdict(lambda: {'positions': 0.0, 'amount': 0.0, 'hour_based_amount': 0.0})
for r in pos:
    if r['title_description'] in SPECIAL: continue
    k = ('D%02d' % int(r['department_code']), 'T' + r['title_code'].zfill(4))
    b = BUD[k]; amt = float(r['total_budgeted_amount'])
    if r['position_control'] == '1': b['positions'] += float(r['total_budgeted_unit']); b['amount'] += amt
    else: b['hour_based_amount'] += amt
VAC = collections.defaultdict(lambda: [0, 0, 0])
for v in vac:
    k = (v['department'], v['title_code']); x = VAC[k]
    x[0] += int(v['total_positions']); x[1] += int(v['employees_in_position']); x[2] += int(v['number_of_vacancies'])

# ---------- title-level tables from server-side aggregates ----------
def load_titlepay(yr):
    t = collections.defaultdict(lambda: collections.defaultdict(float))
    for r in L(f'pay{yr}_title'):
        t[(r['department_code'], r['title_code'])][category(r['appropriation_code'], r['pay_element'])] += float(r['amt'])
    return t
TP25, TP24 = load_titlepay(2025), load_titlepay(2024)
EM25 = {(r['department_code'], r['title_code']): int(r['emps']) for r in L('pay2025_dt_emps')}
EM24 = {(r['department_code'], r['title_code']): int(r['emps']) for r in L('pay2024_dt_emps')}

# persons by primary group
GP = collections.defaultdict(list)
for e, p in P.items(): GP[p['primary']].append(p)
# current employees by dept code + title code (via matched payroll primary, else title-name lookup)
name2codes = collections.defaultdict(set)
for t, n in TN.items(): name2codes[norm(n)].add(t)
GC = collections.defaultdict(list)
unk_cur = 0
for i, c in enumerate(cur):
    d = DMAP.get(norm(c['department']))
    if i in match:
        d2, t = P[match[i]]['primary']
        # the roster is current: prefer the roster's own title if it maps to exactly one code
        cs = name2codes.get(norm(c['job_titles']), set())
        if len(cs) == 1: t = next(iter(cs))
        d = d or d2
    else:
        cs = name2codes.get(norm(c['job_titles']), set())
        t = next(iter(cs)) if len(cs) == 1 else None
    if not d or not t: unk_cur += 1; continue
    GC[(d, t)].append(annualize(c))
print('current employees not keyed to a dept/title code', unk_cur)

def q(a, p): return round(float(np.percentile(a, p)), 2)
def dist(vals, label, out, p90=True):
    """per-person stats gated by group size."""
    n = len(vals)
    out[f'n_{label}'] = n
    if n >= MIN_N:
        out[f'median_{label}'] = q(vals, 50); out[f'mean_{label}'] = round(float(np.mean(vals)), 2)
        out[f'p90_{label}'] = q(vals, 90) if (p90 and n >= MIN_P90) else None
    else:
        out[f'median_{label}'] = out[f'mean_{label}'] = out[f'p90_{label}'] = None

def person_stats(plist, out):
    full = [p for p in plist if p['periods'] == 24]
    out['n_paid_primary'] = len(plist)
    dist([p['total_x'] for p in full], 'total_excl_retro_fullyear', out)
    dist([p['cat']['regular'] for p in full], 'regular_fullyear', out, p90=False)
    if len(full) >= MIN_N:
        out['mean_overtime_fullyear'] = round(float(np.mean([p['cat']['overtime'] for p in full])), 2)
        out['mean_other_premium_fullyear'] = round(float(np.mean([p['cat']['other_premium'] for p in full])), 2)
        out['pct_with_overtime_fullyear'] = round(100 * sum(1 for p in full if p['cat']['overtime'] > 0) / len(full), 1)
    else:
        out['mean_overtime_fullyear'] = out['mean_other_premium_fullyear'] = out['pct_with_overtime_fullyear'] = None

def sums(tp):
    return {f'{k}_2025': round(tp[k], 2) for k in CATS} | {'total_2025': round(sum(tp.values()), 2)}

keys = set(TP25) | set(TP24) | set(GC) | set(BUD) | {(d, t) for (d, t) in VAC}
keys = {k for k in keys if k[0] in DN}
groups = {}
for k in keys:
    d, t = k
    g = {'dept_code': d, 'dept': DN[d], 'title_code': t, 'title': TN.get(t) or next((v['title'].split(' - ', 1)[1] for v in vac if v['title_code'] == t), t)}
    b = BUD.get(k, {'positions': 0, 'amount': 0, 'hour_based_amount': 0})
    g['budget_2026_positions'] = b['positions']; g['budget_2026_amount'] = round(b['amount'], 2)
    g['budget_2026_avg_rate'] = round(b['amount'] / b['positions'], 2) if b['positions'] else None
    g['budget_2026_hour_based_amount'] = round(b['hour_based_amount'], 2) if b['hour_based_amount'] else 0
    v = VAC.get(k, [0, 0, 0]); g['vacancy_positions'], g['vacancy_filled'], g['vacancy_vacant'] = v
    g['n_paid_2025'] = EM25.get(k, 0); g['n_paid_2024'] = EM24.get(k, 0)
    g.update(sums(TP25.get(k, collections.defaultdict(float)))); 
    g['total_2024'] = round(sum(TP24.get(k, {}).values()), 2)
    g['overtime_2024'] = round(TP24.get(k, {}).get('overtime', 0), 2)
    cv = [x for x in GC.get(k, []) if x is not None]
    g['n_current'] = len(GC.get(k, []))
    dist(cv, 'current_annualized_base', g)
    person_stats(GP.get(k, []), g)
    groups[k] = g

SUM_KEYS = ['budget_2026_positions', 'budget_2026_amount', 'budget_2026_hour_based_amount', 'vacancy_positions', 'vacancy_filled', 'vacancy_vacant',
            'n_paid_2025', 'n_paid_2024', 'n_current', 'regular_2025', 'overtime_2025', 'other_premium_2025', 'retro_lumpsum_2025', 'total_2025', 'total_2024', 'overtime_2024']
def small(g): return 0 < max(g['n_paid_2025'], g['n_current']) < MIN_N or (g['n_paid_2025'] == 0 and g['n_current'] == 0 and False)
rows = []; deptsum = {}
bydept = collections.defaultdict(list)
for k, g in groups.items(): bydept[k[0]].append(g)
for d, gl in sorted(bydept.items()):
    shown = [g for g in gl if not small(g)]
    rolled = [g for g in gl if small(g)]
    # complementary-disclosure guard: dept total minus shown titles equals the bucket, so the bucket itself must hold >= 5 people.
    # If it does not, pull the smallest shown titles into the bucket. If the whole dept is under 5, dept totals are suppressed below.
    hc_ = lambda gs: sum(max(g['n_paid_2025'], g['n_current']) for g in gs)
    while rolled and hc_(rolled) < MIN_N and shown:
        shown.sort(key=lambda g: max(g['n_paid_2025'], g['n_current'])); rolled.append(shown.pop(0))
    rows += sorted(shown, key=lambda g: -g['total_2025'])
    if rolled:
        o = {'dept_code': d, 'dept': DN[d], 'title_code': None, 'title': 'Other titles (groups under 5 people)', 'titles_rolled_up': len(rolled)}
        for sk in SUM_KEYS: o[sk] = round(sum(g[sk] for g in rolled), 2)
        pool = [p for g in rolled for p in GP.get(g['dept_code'] and (g['dept_code'], g['title_code']), [])]
        cvp = [x for g in rolled for x in GC.get((g['dept_code'], g['title_code']), []) if x is not None]
        o['budget_2026_avg_rate'] = None
        dist(cvp, 'current_annualized_base', o); person_stats(pool, o)
        o['n_current'] = int(o['n_current']); o['n_paid_2025'] = int(o['n_paid_2025'])
        if max(o['n_paid_2025'], o['n_current']) < MIN_N:  # tiny departments: no actual-pay dollars for fewer than 5 people
            for sk in ('regular_2025', 'overtime_2025', 'other_premium_2025', 'retro_lumpsum_2025', 'total_2025', 'total_2024', 'overtime_2024'): o[sk] = None
            o['suppressed'] = 'fewer than 5 people'
        rows.append(o)
    allp = [p for g in gl for p in GP.get((g['dept_code'], g['title_code']), [])]
    ds = {'dept_code': d, 'dept': DN[d], 'titles_shown': len(shown), 'titles_rolled_up': len(rolled)}
    for sk in SUM_KEYS: ds[sk] = round(sum(g[sk] for g in gl), 2)
    ds['n_paid_2025_distinct'] = len({e for e, p in P.items() if p['primary'][0] == d})
    if ds['n_paid_2025_distinct'] < MIN_N:  # dept total would reveal individual pay
        for sk in ('regular_2025', 'overtime_2025', 'other_premium_2025', 'retro_lumpsum_2025', 'total_2025', 'total_2024', 'overtime_2024'): ds[sk] = None
        ds['suppressed'] = 'fewer than 5 people'
    deptsum[d] = ds

# ---------- citywide findings (by title only) ----------
tot = {k: round(sum(p['cat'][k] for p in P.values()), 2) for k in CATS}
tot['total'] = round(sum(p['total'] for p in P.values()), 2)
ot = np.array([p['cat']['overtime'] for p in P.values() if p['cat']['overtime'] > 0])
ots = np.sort(ot)[::-1]
conc = {'persons_paid_overtime_A0020': int(len(ot)), 'median': q(ot, 50), 'mean': round(float(ot.mean()), 2), 'p90': q(ot, 90), 'p99': q(ot, 99),
        'persons_ge_50k': int((ot >= 5e4).sum()), 'persons_ge_100k': int((ot >= 1e5).sum()), 'total': round(float(ot.sum()), 2),
        'share_of_ot_dollars_to_top_10pct_of_ot_earners': round(float(ots[:math.ceil(len(ots) * .1)].sum() / ots.sum() * 100), 1),
        'share_of_ot_dollars_to_top_1pct_of_ot_earners': round(float(ots[:math.ceil(len(ots) * .01)].sum() / ots.sum() * 100), 1)}
# dept concentration of OT
otd = collections.defaultdict(float)
for p in P.values(): otd[p['primary'][0]] += p['cat']['overtime']
conc['top_depts_by_ot_primary_assignment'] = [{'dept': DN[d], 'overtime_2025': round(v, 2), 'pct_of_total': round(100 * v / ots.sum(), 1)} for d, v in sorted(otd.items(), key=lambda kv: -kv[1])[:6]]
tot_pay = np.array([p['total'] for p in P.values()]); tot_x = np.array([p['total_x'] for p in P.values()])
full_x = np.array([p['total_x'] for p in P.values() if p['periods'] == 24]); full_t = np.array([p['total'] for p in P.values() if p['periods'] == 24])
above = {}
for th in (150000, 200000, 250000, 300000):
    above[str(th)] = {'persons_total_pay': int((tot_pay >= th).sum()), 'persons_excl_retro_lumpsum': int((tot_x >= th).sum()),
                      'fullyear_persons_total_pay': int((full_t >= th).sum()), 'fullyear_persons_excl_retro_lumpsum': int((full_x >= th).sum())}
# who is above 200K, by title (titles with >= 5 people only)
t200 = collections.Counter(); 
for p in P.values():
    if p['total_x'] >= 200000: t200[p['primary']] += 1
t200l = []; hid = 0
for k, n in t200.most_common():
    if len(GP[k]) >= MIN_N and n >= MIN_N: t200l.append({'dept': DN[k[0]], 'title': TN.get(k[1], k[1]), 'persons_ge_200k_excl_retro': n, 'persons_in_title': len(GP[k]),
                                        'pct_of_title': round(100 * n / len(GP[k]), 1)})
    else: hid += n
ot100 = collections.Counter(max((kv for kv in P[e]['dt'].items()), key=lambda kv: kv[1])[0] if P[e]['dt'] else P[e]['primary'] for e in P if P[e]['cat']['overtime'] >= 1e5)
ot100_list = [{'dept': DN[k[0]], 'title': TN.get(k[1], k[1]), 'persons_with_overtime_ge_100k': n} for k, n in ot100.most_common() if n >= MIN_N]
ot100_hidden = sum(n for n in ot100.values() if n < MIN_N)
d200 = collections.Counter(p['primary'][0] for p in P.values() if p['total_x'] >= 200000)
# gaps pay vs base (full-year, n>=10)
gap = []
for g in groups.values():
    k = (g['dept_code'], g['title_code']); full = [p for p in GP.get(k, []) if p['periods'] == 24]
    if len(full) < 10: continue
    reg = np.mean([p['cat']['regular'] for p in full]); ot_ = np.mean([p['cat']['overtime'] for p in full]); oth = np.mean([p['cat']['other_premium'] for p in full])
    if reg < 20000: continue
    gap.append({'dept': g['dept'], 'title': g['title'], 'n_fullyear': len(full), 'mean_regular': round(float(reg), 0), 'mean_overtime': round(float(ot_), 0),
                'mean_other_premium': round(float(oth), 0), 'premium_pct_of_regular': round(100 * float(ot_ + oth) / float(reg), 1),
                'premium_dollars_per_person': round(float(ot_ + oth), 0), 'budget_2026_avg_rate': g['budget_2026_avg_rate'],
                'median_current_annualized_base': g.get('median_current_annualized_base')})
gap_pct = sorted(gap, key=lambda x: -x['premium_pct_of_regular'])[:15]
gap_usd = sorted(gap, key=lambda x: -x['premium_dollars_per_person'])[:15]
# regular vs budget rate (title with budget rate, n>=10)
rb = []
for r in gap:
    if r['budget_2026_avg_rate']:
        rb.append(dict(r, regular_vs_budget_rate_pct=round(100 * (r['mean_regular'] / r['budget_2026_avg_rate'] - 1), 1)))
rb_under = sorted(rb, key=lambda x: x['regular_vs_budget_rate_pct'])[:10]; rb_over = sorted(rb, key=lambda x: -x['regular_vs_budget_rate_pct'])[:10]
# top 15 titles by OT dollars
tt = sorted(((k, g) for k, g in groups.items() if not small(g)), key=lambda kv: -kv[1]['overtime_2025'])[:15]
top_ot_titles = [{'dept': g['dept'], 'title': g['title'], 'overtime_2025': g['overtime_2025'], 'n_paid': g['n_paid_2025'],
                  'pct_with_overtime_fullyear': g.get('pct_with_overtime_fullyear'), 'mean_overtime_fullyear': g.get('mean_overtime_fullyear')} for k, g in tt]

# ---------- reconciliation: payroll costing 2025 vs ordinance ----------
def ordinance(path_or_rows):
    d = collections.defaultdict(float); loc = collections.defaultdict(float)
    for r in path_or_rows:
        a = r['appropriation_account']; v = float(r['_ordinance_amount_']); d[a] += v
        if r['fund_type'] == 'LOCAL': loc[a] += v
    return d, loc
O25, O25L = ordinance(L('ord2025_approp')); O26, O26L = ordinance(json.load(open(f'{ROOT}/raw/city_appropriations_2026.json')))
PA = collections.defaultdict(float)
for r in pay: PA[r['appropriation_code'][1:]] += float(r['amt'])
fundtype = {}
for r in L('ord2025_approp'): fundtype[r['fund_code']] = r['fund_type']
PAL = collections.defaultdict(float)
for r in pay:
    if fundtype.get(r['fund_code'][1:]) == 'LOCAL': PAL[r['appropriation_code'][1:]] += float(r['amt'])
for r in json.load(open(f'{ROOT}/raw/city_appropriations_2026.json')) + L('ord2025_approp'): AN.setdefault('A' + r['appropriation_account'], r['appropriation_account_description'].upper())
accts = sorted(set(PA) | set(O25) | set(O26), key=lambda a: -(PA.get(a, 0)))
rec_rows = []
for a in accts:
    if abs(PA.get(a, 0)) < 1e5 and O25.get(a, 0) < 1e6 and O26.get(a, 0) < 1e6: continue
    rec_rows.append({'account': a, 'name': AN.get('A' + a), 'payroll_actual_2025_all_funds': round(PA.get(a, 0), 0), 'payroll_actual_2025_local_funds': round(PAL.get(a, 0), 0),
                     'ordinance_2025_all_funds': O25.get(a), 'ordinance_2025_local': O25L.get(a), 'ordinance_2026_all_funds': O26.get(a), 'ordinance_2026_local': O26L.get(a),
                     'actual_vs_2025_ordinance_pct': round(100 * PA.get(a, 0) / O25[a], 1) if O25.get(a) else None})
# salary-type accounts total
SAL = ['0005', '0015', '0003', '0012', '0017', '0000']
# headcount reconciliation by department
cc = collections.Counter(DMAP.get(norm(c['department'])) for c in cur)
a0005 = collections.defaultdict(set)
for r in pay:
    if r['appropriation_code'] == 'A0005': a0005[r['department_code']].add(r['employee'].split(' - ')[0])
hc = []
for d in sorted(DN):
    vv = [v for v in vac if v['department'] == d]
    bp = sum(BUD[k]['positions'] for k in BUD if k[0] == d)
    hc.append({'dept_code': d, 'dept': DN[d], 'current_roster_employees': cc.get(d, 0), 'budget_2026_positions_position_control': bp,
               'vacancy_dataset_positions': sum(int(v['total_positions']) for v in vv), 'vacancy_dataset_employees': sum(int(v['employees_in_position']) for v in vv),
               'vacancy_dataset_vacancies': sum(int(v['number_of_vacancies']) for v in vv),
               'paid_2025_on_A0005_distinct': len(a0005.get(d, ())),
               'vacancy_rate_pct': round(100 * sum(int(v['number_of_vacancies']) for v in vv) / max(1, sum(int(v['total_positions']) for v in vv)), 1) if vv else None})
hct = {k: sum(x[k] or 0 for x in hc) for k in ('current_roster_employees', 'budget_2026_positions_position_control', 'vacancy_dataset_positions', 'vacancy_dataset_employees', 'vacancy_dataset_vacancies', 'paid_2025_on_A0005_distinct')}

hours_note = collections.Counter(c['typical_hours'] for c in cur if c['salary_or_hourly'] == 'HOURLY')
out = {
    'meta': {'generated_by': 'scripts/people_fetch.py then scripts/people_build_city.py', 'names': False,
             'sources': {'roster': 'xzkq-xp2w', 'payroll': 'dawh-m56b (payroll_year 2024, 2025)', 'vacancies': '9v3e-pcjs (report_date %s)' % vac[0]['report_date'][:10],
                         'budget_positions': 'v2t2-vajc (2026)', 'ordinance': '6694-f78c (2026), t59y-fr3k (2025)'},
             'small_group_rule': 'dept x title groups under 5 people (paid 2025 or currently employed) are rolled into "Other titles (groups under 5 people)" per department. Per-person stats are null when n < 5; p90 is null when n < 10. Department totals are suppressed when under 5 people.',
             'definitions': {'regular': 'A0005/A0017/A0000 regular salary, regular time, regular at other rates (MULT n RATE 1_0), REG 1_15, REG 1_125, time entry wages',
                             'overtime': 'appropriation A0020 (all OT pay elements)', 'retro_lumpsum': 'appropriation A0003 (retro pay and CBA lump sums)',
                             'other_premium': 'everything else: duty availability, holiday, comp time and vacation payouts, specialty, uniform allowance, A0032 reimbursable OT, other A0005 elements',
                             'fullyear': 'persons paid in all 24 pay periods of 2025', 'primary_group': 'each payroll person is assigned to the dept x title with the most non-retro pay in 2025; sums by group include every dollar charged to that group, so sums can include pay of people whose primary group is another title',
                             'annualized_base': 'annual salary, or hourly rate x typical weekly hours x 52', 'n_current': 'rows of the current-employee roster keyed to a dept and title code'},
             'counts': {'payroll_persons_2025': len(P), 'current_roster': len(cur), 'roster_matched_to_payroll': len(match), 'roster_not_keyed_to_code': unk_cur,
                        'fullyear_persons': int((np.array([p['periods'] for p in P.values()]) == 24).sum())}},
    'totals_2025': tot,
    'departments': list(deptsum.values()),
    'groups': rows,
    'findings': {'overtime_concentration_2025': conc, 'pay_thresholds': above, 'persons_ge_200k_excl_retro_by_title': t200l,
                 'persons_ge_200k_excl_retro_in_other_titles_(group_or_count_under_5)': hid, 'persons_ge_200k_excl_retro_by_dept': [{'dept': DN[d], 'persons': n} for d, n in d200.most_common() if n >= MIN_N],
                 'persons_with_overtime_ge_100k_by_title': ot100_list, 'persons_with_overtime_ge_100k_in_titles_under_5': ot100_hidden,
                 'persons_ge_200k_excl_retro_in_depts_under_5': sum(n for d, n in d200.items() if n < MIN_N),
                 'top_titles_by_overtime_dollars': top_ot_titles, 'largest_premium_pct_of_regular_titles_n10': gap_pct, 'largest_premium_dollars_per_person_titles_n10': gap_usd,
                 'regular_pay_vs_budgeted_rate_lowest': rb_under, 'regular_pay_vs_budgeted_rate_highest': rb_over},
    'reconciliation': {'payroll_vs_ordinance_by_account': rec_rows, 'payroll_total_2025': tot['total'], 'headcount_by_department': hc, 'headcount_totals': hct},
}
json.dump(out, open(f'{ROOT}/data/comp_city_2025.json', 'w'), indent=1)
print('wrote', len(rows), 'group rows', len(deptsum), 'depts')
print(json.dumps({'tot': tot, 'conc': conc, 'above': above, 'hct': hct}, indent=1))
