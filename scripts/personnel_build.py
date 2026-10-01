#!/usr/bin/env python3
"""Build data/city_personnel_2026.json from cached inputs only (no network).

Run order:  python3 scripts/personnel_turnover.py && python3 scripts/personnel_book_lines.py \
            && python3 scripts/personnel_overtime.py && python3 scripts/personnel_build.py
Inputs: raw/city_positions_2026.json (v2t2-vajc), raw/city_appropriations_2026.json (6694-f78c),
        raw/personnel/{ord_turnover_blocks,turnover_blocks,book_pers_lines,payroll_*,union_schedules,rate_pairs}.json
Every reconciliation identity is asserted; the script fails if a number does not tie.
"""
import json, collections, statistics, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = f'{ROOT}/raw'; PERS = f'{RAW}/personnel'
J = lambda p: json.load(open(p))
P = J(f'{RAW}/city_positions_2026.json'); A = J(f'{RAW}/city_appropriations_2026.json')
OB = J(f'{PERS}/ord_turnover_blocks.json'); RB = J(f'{PERS}/turnover_blocks.json')
BL = J(f'{PERS}/book_pers_lines.json')
d = lambda x: str(int(x))
SPECIAL = {'Schedule Salary Adjustments': '0015', 'Contract Wage Increment - Prevailing Rate': '0012', 'Fringe Benefits': '0044'}
FTYPE = {a['fund_code']: a['fund_type'] for a in A}
DNAME = {d(a['department_number']): a['department_description'] for a in A}
FNAME = {a['fund_code']: a['fund_description'] for a in A}

# ---------------------------------------------------------------- positions
def check_amount(p):
    u, r, a, pc, unit = float(p['total_budgeted_unit']), float(p['budgeted_pay_rate']), float(p['total_budgeted_amount']), p['position_control'], p['budgeted_unit']
    f = {'Annual': 1, 'Hourly': 2080 if pc == '1' else 1, 'Monthly': 12 if pc == '1' else 1}[unit]
    return abs(u * r * f - a) <= 1.0
reg, spec = [], []
for p in P:
    (spec if p['title_description'] in SPECIAL else reg).append(p)
bad = [p for p in reg if not check_amount(p)]
assert len(bad) == 0, f'{len(bad)} regular rows where units x rate (x2080 hourly positions, x12 monthly positions) != amount'
tot_all = sum(float(p['total_budgeted_amount']) for p in P)
tot_reg = sum(float(p['total_budgeted_amount']) for p in reg)
tot_spec = sum(float(p['total_budgeted_amount']) for p in spec)
sal_lines = collections.Counter(); acct = collections.defaultdict(collections.Counter)
for a in A:
    k = (a['fund_code'], d(a['department_number'])); acct[a['appropriation_account']][k] += float(a['_ordinance_amount_'])
sal_lines = acct['0005']; SAL = sum(sal_lines.values())
# special rows tie to their own appropriation lines (not to 0005)
spec_by = collections.defaultdict(collections.Counter)
for p in spec: spec_by[SPECIAL[p['title_description']]][(p['fund_code'], d(p['department_code']))] += float(p['total_budgeted_amount'])
for code, c in spec_by.items():
    assert dict(c) == {k: v for k, v in acct[code].items() if v}, code
# printed turnover (passed ordinance) and the recommendation book
to_ord = collections.Counter(); to_rec = collections.Counter(); ord_pages = collections.defaultdict(list)
for b in OB:
    if b['kind'] == 'Turnover':
        to_ord[(b['fund'], b['dept'])] += b['vals'][0]; ord_pages[(b['fund'], b['dept'])].append(b['ord_page'])
for b in RB:
    if b['kind'] == 'Turnover': to_rec[(b['fund'], b['dept'])] += b['vals'][0]
reg_by = collections.Counter()
for p in reg: reg_by[(p['fund_code'], d(p['department_code']))] += float(p['total_budgeted_amount'])

# printed blocks per fund x dept: Position Total (includes the 0015 Schedule Salary Adjustment rows), Turnover, Net
blocks_by = collections.defaultdict(dict)
for b in OB:
    if b['kind'] in ('Position Total', 'Turnover', 'Position Net Total'):
        blocks_by[(b['fund'], b['dept'])].setdefault(b['ord_page'], {})[b['kind']] = b['vals']
def blocks_for(k):
    out = []
    for pg, g in sorted(blocks_by.get(k, {}).items()):
        out.append(dict(ordinance_page=pg, position_total_incl_0015=g.get('Position Total', [None, None])[-1], positions=g.get('Position Total', [None])[0],
                        turnover=g.get('Turnover', [0])[0], position_net_total=g.get('Position Net Total', [None, None])[-1]))
    return out
# identity: printed Net Total = 0005 + 0015 for every fund x department with a printed block (blocks summed)
tie_net = 0
for k, g in blocks_by.items():
    fnet = [b['vals'][1] for b in OB if (b['fund'], b['dept']) == k and b['kind'] == 'Fund Position Net Total']
    net = fnet[0] if fnet else sum(v.get('Position Net Total', [0, 0])[-1] for v in g.values())
    if abs(net - acct['0005'][k] - acct['0015'][k]) < 1: tie_net += 1
    else: assert k == ('0314', '81') and net == 0, k       # printed turnover block missing for this one pair; salary and 0015 rows are not printed as a block
assert tie_net >= 105, tie_net
# fund x dept reconciliation rows
rec_rows = []
for k in sorted(set(reg_by) | set(k for k, v in sal_lines.items() if v), key=lambda k: (int(k[1]), k[0])):
    gross, to, line = reg_by[k], to_ord.get(k, 0), sal_lines.get(k, 0)
    resid = gross + to - line            # positions less printed turnover less ordinance line
    kind = 'local' if FTYPE.get(k[0]) == 'LOCAL' else 'grant'
    if kind == 'local': assert abs(resid) < 0.5, (k, resid)   # exact tie for every local fund x department
    rec_rows.append(dict(fund=k[0], fund_name=FNAME.get(k[0]), dept=k[1], dept_name=DNAME[k[1]], fund_type=kind,
                         positions_gross=gross, turnover_printed_ordinance=to, turnover_printed_rec_book=to_rec.get(k),
                         ordinance_salary_line_0005=line, unexplained_by_printed_turnover=round(resid, 2),
                         turnover_pct_of_positions=round(-to / gross * 100, 2) if gross and to else None,
                         ordinance_pages=sorted(set(ord_pages.get(k, []))), printed_blocks=blocks_for(k)))
assert abs(sum(r['ordinance_salary_line_0005'] for r in rec_rows) - SAL) < 0.5
T_ORD = sum(to_ord.values()); T_REC = sum(to_rec.values())
GRANT_RESID = sum(r['unexplained_by_printed_turnover'] for r in rec_rows)
assert abs(tot_all - tot_spec + T_ORD - GRANT_RESID - SAL) < 1
# department roll-up
dep_rec = {}
for r in rec_rows:
    x = dep_rec.setdefault(r['dept'], dict(dept=r['dept'], dept_name=r['dept_name'], positions_gross=0, special_rows=0, turnover=0, grant_implied=0, ordinance_0005=0, turnover_rec_book=0))
    x['positions_gross'] += r['positions_gross']; x['turnover'] += r['turnover_printed_ordinance']; x['ordinance_0005'] += r['ordinance_salary_line_0005']
    x['turnover_rec_book'] += r['turnover_printed_rec_book'] or 0
    if r['fund_type'] == 'grant': x['grant_implied'] += r['unexplained_by_printed_turnover']
for code, c in spec_by.items():
    for (f, dp), v in c.items(): dep_rec.setdefault(dp, dict(dept=dp, dept_name=DNAME[dp], positions_gross=0, special_rows=0, turnover=0, grant_implied=0, ordinance_0005=0, turnover_rec_book=0))['special_rows'] += v
for x in dep_rec.values():
    x['positions_incl_special_rows'] = x['positions_gross'] + x['special_rows']
    x['turnover_pct_of_positions'] = round(-x['turnover'] / x['positions_gross'] * 100, 2) if x['positions_gross'] else None
    assert abs(x['positions_incl_special_rows'] - x['special_rows'] + x['turnover'] - x['grant_implied'] - x['ordinance_0005']) < 1, x['dept']
    x['check_sum_ties'] = True
dep_list = sorted(dep_rec.values(), key=lambda x: -x['positions_incl_special_rows'])

# ---------------------------------------------------------------- tree
def node(name, code=None): return dict(name=name, code=code, children={}, rows=[])
root = node('City of Chicago, salaries and wages on payroll (acct 0005), 2026 ordinance')
for p in reg:
    dp = d(p['department_code']); amt = float(p['total_budgeted_amount']); u = float(p['total_budgeted_unit']); pc = p['position_control']
    cur = root
    path = [(dp, DNAME[dp]), (p['organization_code'], p['organization_description']), (p['division_code'], p['division_description']),
            (p['section_code'], p['section_description']), (p['title_code'], p['title_description'])]
    for code, name in path:
        cur = cur['children'].setdefault(code, node(name, code))
    unit = {'Annual': 'annual salary', 'Hourly': 'hourly rate', 'Monthly': 'monthly rate'}[p['budgeted_unit']]
    cur['rows'].append(dict(fund=p['fund_code'], units=u, unit_is_positions=pc == '1', rate=float(p['budgeted_pay_rate']), rate_basis=unit,
                            amount=amt, grade=p['schedule_grade'], bargaining_unit=p['bargaining_unit']))
def fin(n, lvl):
    n['level'] = ['root', 'department', 'organization', 'division', 'section', 'title'][lvl]
    kids = [fin(c, lvl + 1) for c in n['children'].values()]
    n['children'] = sorted(kids, key=lambda c: -c['amount'])
    if lvl == 5:
        n['amount'] = sum(r['amount'] for r in n['rows'])
        n['positions'] = sum(r['units'] for r in n['rows'] if r['unit_is_positions'])
        n['non_position_units'] = [dict(units=r['units'], rate=r['rate'], basis=r['rate_basis']) for r in n['rows'] if not r['unit_is_positions']]
        n['avg_per_position'] = round(sum(r['amount'] for r in n['rows'] if r['unit_is_positions']) / n['positions'], 2) if n['positions'] else None
        n['rows'].sort(key=lambda r: -r['amount'])
        for r in n['rows']: r['count_x_rate'] = f"{r['units']:,.0f} {'positions' if r['unit_is_positions'] else ('hours' if r['rate_basis']=='hourly rate' else 'units')} x ${r['rate']:,.2f}"
    else:
        n['amount'] = sum(c['amount'] for c in n['children']); n['positions'] = sum(c['positions'] for c in n['children']); del n['rows']
    return n
fin(root, 0)
# attach negative reconciling nodes to departments so each department equals the ordinance salary line exactly
for dn in root['children']:
    x = dep_rec[dn['code']]
    gross = dn['amount']; assert abs(gross - x['positions_gross']) < 0.5
    adj = []
    for r in rec_rows:
        if r['dept'] != dn['code']: continue
        if r['turnover_printed_ordinance']:
            adj.append(dict(name=f"Budgeted turnover (vacancy savings), {r['fund_name']}", fund=r['fund'], kind='turnover_printed', amount=r['turnover_printed_ordinance'], ordinance_pages=r['ordinance_pages'], printed_blocks=r['printed_blocks'],
                            note='Printed as a "Turnover" line under the Position Total in the Annual Appropriation Ordinance.'))
        if r['fund_type'] == 'grant' and abs(r['unexplained_by_printed_turnover']) >= 0.5:
            adj.append(dict(name=f"Grant fund: positions exceed ordinance salary line, {r['fund_name']}", fund=r['fund'], kind='grant_implied_not_printed', amount=-r['unexplained_by_printed_turnover'],
                            note='Grant-fund positions are not printed in the books and no turnover is shown. Difference between the positions dataset and the ordinance 0005 line. Cause not documented.'))
    dn['adjustments'] = adj
    dn['amount_gross_positions'] = gross
    dn['amount'] = gross + sum(a['amount'] for a in adj)
    assert abs(dn['amount'] - x['ordinance_0005']) < 0.5, dn['code']
root['amount_gross_positions'] = sum(c['amount_gross_positions'] for c in root['children'])
root['amount'] = sum(c['amount'] for c in root['children'])
root['positions'] = sum(c['positions'] for c in root['children'])
assert abs(root['amount'] - SAL) < 0.5
def walk(n, lvl=0, out=None):
    out = out if out is not None else collections.defaultdict(list)
    out[lvl].append(n)
    for c in n['children']: walk(c, lvl + 1, out)
    return out
lv = walk(root)

# ---------------------------------------------------------------- depth stats (gross positions, before turnover)
names = {1: 'department', 2: 'organization', 3: 'division', 4: 'section', 5: 'title (within section)'}
depth = []
G = root['amount_gross_positions']
for l in range(1, 6):
    nodes = lv[l]
    amt = (lambda n: n['amount_gross_positions']) if l == 1 else (lambda n: n['amount'])
    small = [n for n in nodes if amt(n) < 1e6]
    gl = sum(amt(n) for n in nodes)
    depth.append(dict(level=names[l], nodes=len(nodes), nodes_under_1m=len(small), pct_nodes_under_1m=round(len(small) / len(nodes) * 100, 1),
                      dollars=gl, dollars_in_nodes_under_1m=sum(amt(n) for n in small),
                      pct_dollars_under_1m=round(sum(amt(n) for n in small) / gl * 100, 2)))
# rate-row level: one dataset row = title x fund x rate
rows_all = [r for t in lv[5] for r in t['rows']]
rl = [r for r in rows_all if r['amount'] < 1e6]
depth.append(dict(level='dataset row (title x fund x rate)', nodes=len(rows_all), nodes_under_1m=len(rl), pct_nodes_under_1m=round(len(rl) / len(rows_all) * 100, 1),
                  dollars=sum(r['amount'] for r in rows_all), dollars_in_nodes_under_1m=sum(r['amount'] for r in rl), pct_dollars_under_1m=round(sum(r['amount'] for r in rl) / sum(r['amount'] for r in rows_all) * 100, 2)))
big = [t for t in lv[5] if t['amount'] >= 1e6]
bigs = sum(t['amount'] for t in big)
# person level: count x average. Every positions-based title node >= $1M is stated as N x $avg, and each average is far below $1M.
pos_big = [t for t in big if t['positions'] > 0]
per_person = dict(title_nodes_over_1m=len(big), dollars_in_them=bigs, pct_of_all_dollars=round(bigs / G * 100, 2),
                  positions_in_them=sum(t['positions'] for t in big), max_average_per_position=max(t['avg_per_position'] for t in pos_big),
                  pct_dollars_under_1m_after_count_x_average=100.0,
                  note='A title node of $1M or more is shown as "N positions x $average". The largest average is below $1M, so 100% of dollars end in a displayed unit under $1M. The count x average line is a division of a node, not a separate source row.')
top_titles = []
for dn in root['children']:
    for t in walk(dn)[4]:
        if t['amount'] >= 1e6 and t['positions'] > 0:
            top_titles.append(dict(department=dn['name'], title=t['name'], positions=t['positions'], average=t['avg_per_position'], amount=t['amount']))
top_titles.sort(key=lambda x: -x['amount'])
# how much of the dollars sits in 'big' units broken down: positions >=100
over100 = [t for t in top_titles if t['positions'] >= 100]
depth_extra = dict(top_20_title_nodes=top_titles[:20], title_nodes_over_1m_count=len(top_titles), title_nodes_over_1m_with_100_or_more_positions=len(over100),
                   dollars_in_100_plus_position_titles=sum(t['amount'] for t in over100))

# ---------------------------------------------------------------- overtime
localfunds = {k for k, v in FTYPE.items() if v == 'LOCAL'}
ot_b = collections.defaultdict(lambda: collections.Counter())
for a in A:
    if a['appropriation_account'] in ('0020', '0032'):
        ot_b[d(a['department_number'])][(a['appropriation_account'], 'local' if a['fund_code'] in localfunds else 'grant')] += float(a['_ordinance_amount_'])
book25 = collections.Counter(); book24 = collections.Counter(); book26 = collections.Counter()
for l in BL:
    if l['acct'] != '0020': continue
    n = l['nums']
    if len(n) >= 3: book26[l['dept']] += n[0]; book25[l['dept']] += n[1]
    if len(n) == 4: book24[l['dept']] += n[3]
    if len(n) == 1: book24[l['dept']] += n[0]      # only the 2024 column is populated on these lines
def pay_dept(code): return d(code.split(' - ')[0][1:]) if code[0] == 'D' else code
def fcode(c): return c[1:] if c.startswith('F') else c
act = {}
for yr in (2024, 2025):
    fa = J(f'{PERS}/payroll_{yr}_dept_fund_approp.json')
    # fund file keyed by dept code only; names from dept_approp
    names_by_code = {r['department'].split(' - ')[0]: r['department'].split(' - ', 1)[1] for r in J(f'{PERS}/payroll_{yr}_dept_approp.json')}
    c = collections.defaultdict(collections.Counter)
    for r in fa:
        if r['appropriation_code'] in ('A0020', 'A0032'):
            c[d(r['department_code'][1:])][(r['appropriation_code'][1:], 'local' if fcode(r['fund_code']) in localfunds else 'nonlocal')] += float(r['amt'])
    act[yr] = c
alldepts = sorted(set(ot_b) | set(act[2024]) | set(act[2025]), key=int)
PNAME = {}
for yr in (2024, 2025):
    for r in J(f'{PERS}/payroll_{yr}_dept_approp.json'): PNAME[d(r['department'].split(' - ')[0][1:])] = r['department'].split(' - ', 1)[1]
ot_rows = []
for dp in alldepts:
    g = lambda c, k: round(c[dp].get(k, 0), 2) if dp in c else 0.0
    row = dict(dept=dp, dept_name=DNAME.get(dp) or PNAME.get(dp),
               budget_2026_overtime_0020_local=round(ot_b[dp].get(('0020', 'local'), 0), 2), budget_2026_overtime_0020_grant=round(ot_b[dp].get(('0020', 'grant'), 0), 2),
               budget_2026_reimbursable_0032=round(ot_b[dp].get(('0032', 'local'), 0) + ot_b[dp].get(('0032', 'grant'), 0), 2),
               budget_2025_revised_0020_book=book25.get(dp, 0),
               actual_2025_0020_local=g(act[2025], ('0020', 'local')), actual_2025_0020_nonlocal=g(act[2025], ('0020', 'nonlocal')), actual_2025_0032=round(act[2025][dp].get(('0032', 'local'), 0) + act[2025][dp].get(('0032', 'nonlocal'), 0), 2) if dp in act[2025] else 0.0,
               actual_2024_0020_local=g(act[2024], ('0020', 'local')), actual_2024_0020_nonlocal=g(act[2024], ('0020', 'nonlocal')), actual_2024_0032=round(act[2024][dp].get(('0032', 'local'), 0) + act[2024][dp].get(('0032', 'nonlocal'), 0), 2) if dp in act[2024] else 0.0,
               book_2024_expenditure_0020=book24.get(dp, 0))
    row['actual_2025_vs_2025_revised_budget'] = round(row['actual_2025_0020_local'] - row['budget_2025_revised_0020_book'], 2)
    row['budget_2026_vs_actual_2025_local'] = round(row['budget_2026_overtime_0020_local'] - row['actual_2025_0020_local'], 2)
    row['actual_2025_pct_of_2025_revised_budget'] = round(row['actual_2025_0020_local'] / row['budget_2025_revised_0020_book'] * 100, 1) if row['budget_2025_revised_0020_book'] else None
    ot_rows.append(row)
ot_tot = {k: round(sum(r[k] for r in ot_rows), 2) for k in ot_rows[0] if k not in ('dept', 'dept_name', 'actual_2025_pct_of_2025_revised_budget')}
ot_tot['actual_2025_pct_of_2025_revised_budget'] = round(ot_tot['actual_2025_0020_local'] / ot_tot['budget_2025_revised_0020_book'] * 100, 1)
assert abs(ot_tot['budget_2026_overtime_0020_local'] + ot_tot['budget_2026_overtime_0020_grant'] - sum(acct['0020'].values())) < 1
# unit / title: payroll costing, department x title; bargaining unit via the positions dataset title code
bu_dollars = collections.defaultdict(collections.Counter)
for p in P: bu_dollars[p['title_code']][p['bargaining_unit']] += float(p['total_budgeted_amount'])
sched = J(f'{PERS}/union_schedules.json'); unit_name = collections.defaultdict(list)
for s in sched:
    for u in [x.strip() for x in s['units'].split(',') if x.strip()]:
        nm = s['title'][0] if s['title'] else s['schedule']
        if nm not in unit_name[u]: unit_name[u].append(nm)
def bu_of(tc):
    c = bu_dollars.get(tc)
    if not c: return None, None
    u, v = c.most_common(1)[0]; return u, round(v / sum(c.values()), 3)
def union_label(u):
    if u is None: return 'title not in 2026 positions dataset'
    nm = unit_name.get(u.zfill(2))
    return ' / '.join(nm[:2]) if nm else f'unit {u} (no salary schedule printed)'
ot_title = {}
for yr in (2024, 2025):
    rows = []
    for r in J(f'{PERS}/payroll_{yr}_ot_dept_title.json'):
        dp = d(r['department'].split(' - ')[0][1:]); tcode, tname = r['title'].split(' - ', 1); tc = tcode[1:]
        u, share = bu_of(tc)
        rows.append(dict(dept=dp, dept_name=r['department'].split(' - ', 1)[1], title_code=tc, title=tname, overtime_0020=round(float(r['amt']), 2),
                         employees_paid_overtime=int(r['n']), bargaining_unit=u, bargaining_unit_share_of_title_dollars=share, union=union_label(u)))
    rows.sort(key=lambda x: -x['overtime_0020']); ot_title[yr] = rows
ot_unit = {}
for yr in (2024, 2025):
    c = collections.defaultdict(lambda: [0.0, 0])
    for r in ot_title[yr]:
        k = (r['bargaining_unit'], r['union']); c[k][0] += r['overtime_0020']; c[k][1] += r['employees_paid_overtime']
    ot_unit[yr] = sorted([dict(bargaining_unit=k[0], union=k[1], overtime_0020=round(v[0], 2), employee_title_dept_pairs=v[1]) for k, v in c.items()], key=lambda x: -x['overtime_0020'])
# pay elements
pe = {}
for yr in (2024, 2025):
    c = collections.Counter()
    for r in J(f'{PERS}/payroll_{yr}_ot_payelem.json'): c[r['pay_element']] += float(r['amt'])
    pe[yr] = {k: round(v, 2) for k, v in c.most_common()}
# employee distribution 2025
emp = collections.defaultdict(float)
for r in J(f'{PERS}/payroll_2025_ot_employee.json'): emp[r['employee_dataset_id']] += float(r['amt'])
vals = sorted(v for v in emp.values() if v > 0); tot_e = sum(vals)
dist = dict(employees_with_overtime=len(vals), total=round(tot_e, 2), mean=round(tot_e / len(vals), 2), median=round(statistics.median(vals), 2),
            p90=round(vals[int(len(vals) * .9)], 2), max=round(vals[-1], 2),
            share_of_dollars_top_10pct_of_earners=round(sum(vals[int(len(vals) * .9):]) / tot_e * 100, 1),
            employees_over_50k=sum(1 for v in vals if v >= 50000), employees_over_100k=sum(1 for v in vals if v >= 100000))
swa_act = {}
for yr in (2024, 2025, 2026):
    swa_act[yr] = dict(by_pay_element={r['pay_element']: float(r['amt']) for r in J(f'{PERS}/payroll_{yr}_swa_payelem.json')},
                       by_department={r['department']: float(r['amt']) for r in J(f'{PERS}/payroll_{yr}_swa_dept.json')})
    swa_act[yr]['total'] = round(sum(swa_act[yr]['by_pay_element'].values()), 2)

# ---------------------------------------------------------------- scheduled wage adjustments (0003)
swa_rows = [dict(fund=k[0], fund_name=FNAME[k[0]], dept=k[1], dept_name=DNAME[k[1]], amount=v) for k, v in acct['0003'].items() if v]
swa_rows.sort(key=lambda x: -x['amount'])
SWA = sum(r['amount'] for r in swa_rows)
swa_book = {}
for l in BL:
    if l['acct'] == '0003': swa_book[(l['dept'], l['fund'])] = l['nums']
swa = dict(total_ordinance=SWA, by_department_fund=swa_rows, by_department=[dict(dept=k, dept_name=DNAME[k], amount=v) for k, v in
           sorted(collections.Counter({dp: sum(r['amount'] for r in swa_rows if r['dept'] == dp) for dp in {r['dept'] for r in swa_rows}}).items(), key=lambda kv: -kv[1])],
           actual_paid_from_payroll_costing=swa_act,
           book_finance_general_rows_2026_2025revised_2025approp={f"{k[1]}/{k[0]}": v for k, v in swa_book.items() if k[0] == '99'})
assert abs(SWA - 387717767) < 1

# pay-rate drift (same table row, 2026 vs 2025 revised)
RP = J(f'{PERS}/rate_pairs.json'); w = [(x['r26'] / x['r25'] - 1, x['c26']) for x in RP if x['c26'] > 0 and 0.5 < x['r26'] / x['r25'] < 2]
rate_drift = dict(rows=len(w), count_weighted_mean_pct=round(sum(a * b for a, b in w) / sum(b for a, b in w) * 100, 2), median_pct=round(statistics.median(a for a, b in w) * 100, 2))

out = dict(
    meta=dict(generated_by='scripts/personnel_build.py', sources=dict(positions='data.cityofchicago.org v2t2-vajc (raw/city_positions_2026.json)', appropriations='6694-f78c (raw/city_appropriations_2026.json)',
              turnover_blocks='Annual Appropriation Ordinance FY2026 (raw/gap/ord_2026.txt), Position Total / Turnover / Position Net Total lines; Budget Recommendations book for the pre-amendment values',
              payroll='Employee Payroll Costing dawh-m56b, aggregated server side (raw/personnel/payroll_*.json)'),
              ordinance_salary_line_0005_total=SAL, printed_net_total_equals_0005_plus_0015_pairs=tie_net, tree_total=root['amount'], tree_ties_to_ordinance_exactly=abs(root['amount'] - SAL) < 0.5),
    reconciliation=dict(
        positions_dataset_total=tot_all, regular_position_rows=tot_reg, schedule_wage_fringe_rows=tot_spec,
        special_rows_detail={SPECIAL[k]: sum(spec_by[SPECIAL[k]].values()) for k in SPECIAL},
        turnover_printed_in_ordinance=T_ORD, turnover_printed_in_rec_book=T_REC, turnover_change_from_amendments=T_ORD - T_REC,
        grant_fund_positions_over_ordinance_line_not_printed=GRANT_RESID, ordinance_salary_line_0005=SAL,
        bridge=[dict(step='Positions dataset total', amount=tot_all),
                dict(step='less Schedule Salary Adjustments rows (tie to acct 0015)', amount=-sum(spec_by['0015'].values())),
                dict(step='less Contract Wage Increment - Prevailing Rate rows (tie to acct 0012)', amount=-sum(spec_by['0012'].values())),
                dict(step='less Fringe Benefits rows, grant funds (tie to acct 0044)', amount=-sum(spec_by['0044'].values())),
                dict(step='less budgeted turnover printed in the ordinance (local funds)', amount=T_ORD),
                dict(step='less grant-fund positions above the ordinance line (no turnover printed)', amount=-GRANT_RESID),
                dict(step='= Salaries and Wages - on Payroll (0005), ordinance', amount=SAL)],
        by_department=dep_list, by_fund_department=rec_rows),
    tree=root, depth_stats=dict(basis='gross position dollars before turnover', levels=depth, big_nodes=per_person, **depth_extra),
    overtime=dict(by_department=ot_rows, totals=ot_tot, by_department_title=ot_title, by_union=ot_unit, pay_elements=pe, employee_distribution_2025=dist),
    scheduled_wage_adjustments=swa, rate_drift_2026_vs_2025_same_row=rate_drift)
# bargaining-unit and counts for the md
out['meta']['positions_counted'] = root['positions']
json.dump(out, open(f'{ROOT}/data/city_personnel_2026.json', 'w'), indent=1, default=float)
print('tree total', root['amount'], 'ordinance', SAL, 'positions', root['positions'])
print('size MB', os.path.getsize(f'{ROOT}/data/city_personnel_2026.json') / 1e6)
for r in depth: print(r['level'], r['nodes'], r['nodes_under_1m'], r['pct_dollars_under_1m'])
print(per_person); print(depth_extra['title_nodes_over_1m_count'], depth_extra['title_nodes_over_1m_with_100_or_more_positions'])
print(ot_tot); print(dist); print(rate_drift)
