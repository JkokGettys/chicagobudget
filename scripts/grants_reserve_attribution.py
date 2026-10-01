#!/usr/bin/env python3
"""Split ordinance 'Reserve Balance' (account 909A) grant lines into named projects/awards using public project-level sources.

Inputs (all public, cached in raw/grants/, gitignored):
  - data/city_grants_2026.json  (Summary G grants joined to ordinance 6694-f78c)
  - Mid-Year Grants 925 dataset, Chicago Data Portal iyu8-jkf8, snapshot as of 2026-05-31 (project level: budget, expended, encumbered)
  - FAA awards from USASpending.gov (faa_awards_detail.json) for Aviation
  - Chicago Data Portal TIF Projections 2025-2034 (fpsv-qjg3) for TIF project lines
Outputs: adds 'reserve_attribution' to data/city_grants_2026.json and 'tif_2026_projected_lines' and
         'ordinance_construction_vs_cip' to data/city_capital_2026.json.

Method (conservative, never invents numbers):
  attributable = min(reserve line $, sum of UNSPENT budget (budget - expended) of matched named project records)
  Matching key: (department, ALN) for federal lines; fund-code map for CDOT state lines (see CDOT_STATE_MAP).
  Unspent budget is used (not full budget) because Summary G carryover is money not yet spent.
"""
import json, os, re, collections, urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW = os.path.join(ROOT, 'raw', 'grants')
G = os.path.join(ROOT, 'data', 'city_grants_2026.json')
C = os.path.join(ROOT, 'data', 'city_capital_2026.json')


def fetch(ds, cache):
    p = os.path.join(RAW, cache)
    if not os.path.exists(p):
        urllib.request.urlretrieve(f'https://data.cityofchicago.org/resource/{ds}.json?$limit=50000', p)
    return json.load(open(p))


def num(x):
    return float(x or 0)


mid_all = fetch('iyu8-jkf8', 'midyear925.json')
mid = [r for r in mid_all if r['data_extract_as_of_date'].startswith('2026')]  # 2026-05-31 snapshot
tif = fetch('fpsv-qjg3', 'ds_fpsv-qjg3.json')

# CDOT state/other lines in Summary G have no ALN, so map them to the mid-year fund codes
CDOT_STATE_MAP = {
    ('925S', '084', '280E'): {'fund_codes': ['F0L98', 'F0W23'], 'why': 'IDOT highway funds: F0L98 IDOT Transportation Funds and F0W23 Illinois Competitive Freight Program'},
    ('925S', '084', '280Q'): {'fund_codes': ['F0W32'], 'why': 'Rebuild Illinois = fund F0W32'},
    ('925S', '084', '280M'): {'fund_codes': ['F0W24'], 'why': 'DCEO grants = fund F0W24'},
    ('925L', '084', '281T'): {'fund_codes': ['FG413', 'F0W03', 'F0W01', 'F0M09'], 'why': 'Sister agency/private = private grants, Cook County Highway Program, CTA, other local'},
}


def norm_dept(d):
    return 'D' + str(int(d)).zfill(2)


def aln_of(name):
    m = re.findall(r'\((\d\d\.\d{3})\)', name)
    return m[-1] if m else None


def unspent(r):
    return max(num(r.get('budget')) - num(r.get('expended_project_to_date')), 0.0)


def group_projects(rows):
    g = collections.OrderedDict()
    for r in rows:
        k = (r['grant_project_description'] or '').strip()
        v = g.setdefault(k, {'project': k, 'budget': 0.0, 'expended': 0.0, 'encumbered': 0.0, 'unspent_budget': 0.0, 'fund_codes': set(), 'aln': set(), 'agency': set(),
                              'end_dates': set(), 'records': 0})
        v['budget'] += num(r.get('budget')); v['expended'] += num(r.get('expended_project_to_date')); v['encumbered'] += num(r.get('encumbrances'))
        v['unspent_budget'] += unspent(r); v['records'] += 1
        v['fund_codes'].add(r['fund_code']); v['aln'].add(r.get('aln_code') or ''); v['agency'].add(r.get('grant_agency') or '')
        if r.get('grant_end_date'): v['end_dates'].add(r['grant_end_date'][:10])
    out = []
    for v in g.values():
        out.append({'project': v['project'], 'budget': round(v['budget'], 2), 'expended_to_date': round(v['expended'], 2), 'encumbered': round(v['encumbered'], 2),
                    'unspent_budget': round(v['unspent_budget'], 2), 'fund_codes': sorted(v['fund_codes']), 'aln': sorted(a for a in v['aln'] if a),
                    'grant_agency': sorted(a for a in v['agency'] if a), 'latest_end_date': max(v['end_dates']) if v['end_dates'] else None, 'records': v['records']})
    return sorted(out, key=lambda x: -x['unspent_budget'])


def main():
    g = json.load(open(G))
    faa = json.load(open(os.path.join(RAW, 'faa_awards_detail.json')))
    for a in faa:
        a['airport'] = {'60666': "O'Hare", '60638': 'Midway'}.get(a.get('zip5'), 'unknown')
    # Reserve lines come from ordinance (909A). One entry per Summary G grant key with reserve > 0.
    ord_rows = json.load(open(os.path.join(ROOT, 'raw', 'city_appropriations_2026.json')))
    lines = collections.OrderedDict()
    for o in ord_rows:
        if o['appropriation_account'] == '909A' or o['appropriation_account'] == '9046':
            k = (o['fund_code'], str(int(o['department_number'])).zfill(3), o['appropriation_authority'])
            v = lines.setdefault(k, {'fund_code': k[0], 'dept_number': k[1], 'authority_code': k[2], 'ordinance_dept': o['department_description'],
                                     'ordinance_authority': o['appropriation_authority_description'], 'reserve_amount': 0})
            v['reserve_amount'] += int(float(o['_ordinance_amount_']))
    sg = {(r['fund_code'], r['dept_number'], r['authority_code']): r for r in g['grants']}
    used_mid = set()
    results = []
    for k, ln in lines.items():
        sgr = sg.get(k)
        name = sgr['grant_name'] if sgr else ln['ordinance_authority']
        d = norm_dept(k[1]); aln = aln_of(name)
        entry = {**ln, 'grant_name': name, 'summary_g_page': sgr['pdf_page'] if sgr else None, 'aln': aln, 'method': None, 'named_items': [], 'attributable': 0, 'note': None}
        if k[1] == '085' and k[0] in ('925F',):
            ap = "O'Hare" if k[2] in ('2810', '2827') else 'Midway'
            awards = [a for a in faa if a['airport'] == ap and (a['end'] or '') >= '2026-01-01']
            items = [{'project': (a['description'] or '')[:160], 'usaspending_award_id': a['award_id'], 'obligation': a['total_obligation'], 'outlay': a['total_outlay'],
                      'period': f"{a['start']} to {a['end']}", 'url': a['usaspending_url']} for a in sorted(awards, key=lambda a: -a['total_obligation'])]
            # open (not yet fully outlaid) obligation = obligation - outlay (outlay may be null for brand new awards)
            open_amt = sum(max((a['total_obligation'] or 0) - (a['total_outlay'] or 0), 0) for a in awards)
            entry.update(method='USASpending FAA grant awards with place of performance %s (zip %s), period ending 2026 or later' % (ap, '60666' if ap == "O'Hare" else '60638'),
                         named_items=items, attributable=int(min(ln['reserve_amount'], open_amt)),
                         note='Open obligation (obligated minus outlaid) of FAA awards, capped at the reserve line. Awards are named by purpose only (e.g. CONSTRUCT TAXIWAY); project names come from the CIP. Aviation grants are absent from the Mid-Year Grants 925 dataset.')
        elif k in CDOT_STATE_MAP or (k[1] == '084' and aln):
            if k in CDOT_STATE_MAP:
                rows = [r for r in mid if r['department_code'] == 'D84' and r['fund_code'] in CDOT_STATE_MAP[k]['fund_codes']]
                how = 'Mid-Year Grants 925 (iyu8-jkf8, as of 2026-05-31), CDOT records with fund codes %s. %s' % (CDOT_STATE_MAP[k]['fund_codes'], CDOT_STATE_MAP[k]['why'])
            else:
                fed_funds = {'20.205': ['F0W16', 'F0W02', 'F0W05', 'F0W15', 'F0W21', 'FG627'], '20.507': ['F0W02', 'F0W16', 'FG665'], '20.934': ['FG378']}.get(aln)
                rows = [r for r in mid if r['department_code'] == 'D84' and r.get('aln_code') == aln and (fed_funds is None or r['fund_code'] in fed_funds)]
                how = 'Mid-Year Grants 925 (iyu8-jkf8, as of 2026-05-31), CDOT records with ALN %s' % aln
            projects = group_projects(rows)
            for r in rows: used_mid.add(r['record_id'])
            un = sum(p['unspent_budget'] for p in projects)
            entry.update(method=how, named_items=projects, attributable=int(min(ln['reserve_amount'], un)),
                         note='Attributable = min(reserve, unspent budget of matched projects). Unspent = budget minus expended to date; encumbered amounts are still unspent.')
        elif aln:
            rows = [r for r in mid if r['department_code'] == d and r.get('aln_code') == aln and r['record_id'] not in used_mid]
            if rows:
                projects = group_projects(rows)
                un = sum(p['unspent_budget'] for p in projects)
                entry.update(method='Mid-Year Grants 925 (iyu8-jkf8, as of 2026-05-31), same department and ALN %s' % aln, named_items=projects, attributable=int(min(ln['reserve_amount'], un)))
            else:
                entry.update(method='No project-level record found in public sources', note='Grant is itself the named item at Summary G level.')
        else:
            entry.update(method='No project-level record found in public sources')
        # The Summary G line is itself a named grant; flag when it is a single named project (no further split needed)
        if entry['attributable'] == 0 and sgr:
            entry['named_at_grant_level'] = True
        results.append(entry)

    # many Summary G lines share an ALN within one department (e.g. HOME in DOH and DFSS). Avoid double counting attributable across lines
    seen = collections.defaultdict(float)
    for e in sorted(results, key=lambda e: -e['reserve_amount']):
        pool_key = (e['dept_number'], e['aln'], tuple(sorted({i.get('project') for i in e['named_items']})[:3]))
        if e['named_items'] and e['aln'] and e['dept_number'] != '085':
            cap = sum(i['unspent_budget'] for i in e['named_items'] if 'unspent_budget' in i)
            avail = max(cap - seen[pool_key], 0)
            e['attributable'] = int(min(e['reserve_amount'], avail))
            seen[pool_key] += e['attributable']
    for e in results:
        if e['attributable'] == 0:
            e['attribution_basis'] = 'named_grant_only'
        elif e['dept_number'] == '085':
            e['attribution_basis'] = 'award_level_usaspending'
        elif (e['fund_code'], e['dept_number'], e['authority_code']) in CDOT_STATE_MAP or e['dept_number'] == '084':
            e['attribution_basis'] = 'project_level_midyear_fund_or_aln_match'
        else:
            e['attribution_basis'] = 'project_pool_midyear_dept_aln_match'
    total = sum(e['reserve_amount'] for e in results)
    attr = sum(e['attributable'] for e in results)
    by_basis = collections.Counter()
    for e in results:
        by_basis[e['attribution_basis']] += e['attributable'] if e['attributable'] else 0
    named_grant = sum(e['reserve_amount'] for e in results if e.get('named_at_grant_level') or e['attributable'] > 0)
    g['reserve_attribution'] = {
        'description': 'Ordinance Reserve Balance (909A) and Operations and Maintenance Reserve (9046) lines mapped to named grants (Summary G) and, where public project-level data exists, to named projects.',
        'sources': {'summary_g': g['source']['url'], 'midyear_grants_925': 'https://data.cityofchicago.org/resource/iyu8-jkf8 (snapshot 2026-05-31)',
                    'usaspending': 'https://api.usaspending.gov/api/v2/search/spending_by_award/', 'ordinance': 'https://data.cityofchicago.org/resource/6694-f78c'},
        'attributable_by_basis': dict(by_basis),
        'caveat': 'attributable is an UPPER-BOUND cap (min of reserve and unspent budget of matched named projects). Summary G carryover is calculated Aug 1 2025 and Mid-Year Grants 925 is a 2026-05-31 snapshot, so project lists are indicative. Named items carry their own sourced budget/expended/unspent figures. No pro-rata allocation is made.',
        'totals': {'reserve_lines_total': total, 'lines': len(results), 'attributable_to_named_projects': attr,
                   'pct_attributable_to_named_projects': round(100 * attr / total, 1) if total else None,
                   'reserve_in_summary_g_named_grants': sum(e['reserve_amount'] for e in results if e['summary_g_page']),
                   'reserve_not_in_summary_g': sum(e['reserve_amount'] for e in results if not e['summary_g_page'])},
        'lines': sorted(results, key=lambda e: -e['reserve_amount'])}
    json.dump(g, open(G, 'w'), indent=1)
    print('reserve lines', len(results), 'total', total, 'attributable to named projects', attr, round(100 * attr / total, 1), '%')
    for e in sorted(results, key=lambda e: -e['reserve_amount'])[:14]:
        print(' ', e['fund_code'], e['dept_number'], e['authority_code'], e['reserve_amount'], e['attributable'], e['grant_name'][:50], len(e['named_items']))

    # ---- capital: TIF 2026 projected lines + ordinance construction vs CIP
    c = json.load(open(C))
    f = lambda x: float(x or 0)
    tl = []
    for r in tif:
        if r['category_description'] in ('Current Obligations', 'Proposed Projects', 'TRR - Hold', 'TRR - Preliminary Agenda', 'TRR - First Look Hold') and f(r['_2026']) != 0:
            tl.append({'tif_district': r['tif_district_name'], 'tif_id': r['tif_district_id'], 'category': r['category_description'], 'line_item': r['line_item_description'],
                       'projected_2026': -f(r['_2026'])})
    tl.sort(key=lambda x: -x['projected_2026'])
    c['tif_2026_projected_lines'] = {'source': {'url': 'https://data.cityofchicago.org/resource/fpsv-qjg3.json', 'document': 'TIF Projections 2025-2034 (OBM/DPD, published 2025-10-15)',
                                                'pdf': 'https://www.chicago.gov/content/dam/city/depts/dcd/tif/projections/projection-report-1025.pdf'},
                                     'note': 'Projected 2026 TIF spending by named obligation. TIF funds are not appropriated in the budget ordinance (only TIF administration, fund 0B21, is), so these do not map onto ordinance lines. Positive = projected spending.',
                                     'total_projected_2026': round(sum(x['projected_2026'] for x in tl), 2), 'lines_count': len(tl),
                                     'lines_under_1m': sum(1 for x in tl if abs(x['projected_2026']) < 1e6), 'lines': tl}
    print('TIF lines', len(tl), 'total', c['tif_2026_projected_lines']['total_projected_2026'])
    # ordinance construction lines
    cons = collections.OrderedDict()
    for o in ord_rows:
        if o['appropriation_account'] == '0540' or 'onstruction' in o['appropriation_account_description']:
            k = (o['fund_code'], o['fund_description'], o['department_number'], o['department_description'], o['appropriation_authority'], o['appropriation_authority_description'], o['appropriation_account_description'])
            cons[k] = cons.get(k, 0) + int(float(o['_ordinance_amount_']))
    rows = [{'fund_code': k[0], 'fund': k[1], 'dept_number': k[2], 'department': k[3], 'authority_code': k[4], 'authority': k[5], 'account': k[6], 'amount': v} for k, v in cons.items()]
    rows.sort(key=lambda x: -x['amount'])
    prog26 = {x['program']: x['y2026'] for x in c['fund_summary_totals'] if x['level'] == 'program'}
    c['ordinance_construction_vs_cip'] = {
        'note': 'Ordinance construction-type lines (account 0540 and any account containing "onstruction"). CIP 2026 column is the 2025-2029 CIP plan (the 2026-2030 CIP was not published as of 2026-09-30) and includes bond and revenue-bond funded work that the ordinance does not appropriate by project.',
        'ordinance_construction_total': sum(x['amount'] for x in rows), 'ordinance_lines': rows, 'cip_2026_by_program': prog26, 'cip_2026_total': sum(prog26.values())}
    json.dump(c, open(C, 'w'), indent=1)


if __name__ == '__main__':
    main()
