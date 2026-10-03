#!/usr/bin/env python3
"""Export public, privacy-filtered site data from budget.db only."""
import collections
import gzip
import hashlib
import json
import re
import sqlite3
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / 'data/budget.db'
OUT = ROOT / 'site/public/data'
EXTRA_KEYS = set('official_name money_comes_from_cents program_areas_cents budget_lines fte fte_2025 enrollment_2024_25 park_number region midyear_contract midyear_group also_on_other_lines titles_in_group printed_total_cents ward pdf_url principal_cents interest_cents fixed_rate final_maturity series coupon_percent contract contracts payments status'.split())
PAY_FIELDS = {'n_paid_2025': 'regular_2025 overtime_2025 other_premium_2025 retro_lumpsum_2025 total_2025', 'n_paid_2024': 'total_2024 overtime_2024', 'n_current': 'median_current_annualized_base mean_current_annualized_base p90_current_annualized_base', 'n_current_annualized_base': 'median_current_annualized_base mean_current_annualized_base p90_current_annualized_base', 'n_total_excl_retro_fullyear': 'median_total_excl_retro_fullyear mean_total_excl_retro_fullyear p90_total_excl_retro_fullyear', 'n_regular_fullyear': 'median_regular_fullyear mean_regular_fullyear p90_regular_fullyear mean_overtime_fullyear mean_other_premium_fullyear pct_with_overtime_fullyear'}
PERIODS = {'city_2026_to_0928': 'Jan 1 to Sep 28, 2026, partial year', 'city_law_2026_to_0731': 'Jan 1 to Jul 31, 2026, partial year, unaudited', 'cps_fy2026_vendor_total': 'CPS fiscal year 2026 (Jul 2025 to Jun 2026), vendor total', 'cps_fy2026_capital': 'CPS fiscal year 2026 (Jul 2025 to Jun 2026), project spending'}
NEUTRAL = ('Payment to an individual', 'Individual (name hidden)')


def clean(value):
    """Recursively strip private/local file metadata, including nested side payloads."""
    if isinstance(value, dict):
        return {k: clean(v) for k, v in value.items() if k != 'file'}
    if isinstance(value, list):
        return [clean(v) for v in value]
    if isinstance(value, str):
        return re.sub(r'(?<![\w/])(?:raw/|data/people/)[^\s;,)]*', '[private source]', value)
    return value


def parsed(value):
    if not value:
        return {}
    try:
        return clean(json.loads(value))
    except (ValueError, TypeError):
        return value


def suppress_pay(extra):
    group = extra.get('group') if isinstance(extra, dict) else None
    if isinstance(group, dict):
        for count, fields in PAY_FIELDS.items():
            if isinstance(group.get(count), (int, float)) and group[count] < 5:
                for field in fields.split():
                    group.pop(field, None)
    return extra


def period_for(source):
    text = json.dumps(source, ensure_ascii=False) if not isinstance(source, str) else source
    if 'through 2026-07-31' in text:
        return 'city_law_2026_to_0731'
    if 'supplier payments FY2026' in text:
        return 'cps_fy2026_vendor_total'
    if 'Capital Expenditures' in text and 'FY2026' in text:
        return 'cps_fy2026_capital'
    if 'Jan 1 to 09/28/2026' in text:
        return 'city_2026_to_0928'
    raise ValueError(f'Unknown paid-to-date source: {text[:180]}')


def formula(row):
    count, unit, amount = row['count'], row['unit_amount_cents'], row['amount_cents']
    if not count or unit is None or not count * unit:
        return 'none'
    expected = count * unit
    if abs(expected - amount) <= 100:
        return 'exact'
    ratio = amount / expected
    if 2070 <= ratio <= 2090:
        return 'hourly'
    if 11.9 <= ratio <= 12.1:
        return 'monthly'
    if abs(expected - amount) <= abs(amount) * .005:
        return 'about'
    return 'none'


def hash_id(value):
    return hashlib.sha1(value.encode()).hexdigest()[:16]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(clean(value), ensure_ascii=False, separators=(',', ':'), sort_keys=True), encoding='utf-8')


def coverage(leaves, build=False):
    sums = [0, 0, 0]
    for n in leaves:
        amount = abs(n['amount_cents'])
        size = 0 if build and n['count'] is not None and n['unit_amount_cents'] is not None and abs(n['unit_amount_cents']) < 100_000_000 else amount
        sums[0 if size < 100_000_000 else 1 if size < 1_000_000_000 else 2] += amount
    total = sum(sums)
    return dict(zip(('lt1m', '1m_10m', 'ge10m'), (round(x / total, 4) if total else 0 for x in sums)))


def export(db=DB, out=OUT):
    out.mkdir(parents=True, exist_ok=True)
    for old in out.rglob('*.json'):
        old.unlink()
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    tables = {x[0] for x in con.execute("select name from sqlite_master where type='table'")}
    assert {'nodes', 'side_info', 'checks'} <= tables
    nodes = {r['id']: dict(r) for r in con.execute('select * from nodes')}
    children = collections.defaultdict(list)
    for n in nodes.values():
        if n['parent_id']:
            children[n['parent_id']].append(n['id'])
    sides = collections.defaultdict(list)
    sources, source_ids = [], {}

    def source_index(raw):
        value = parsed(raw)
        key = json.dumps(value, sort_keys=True, ensure_ascii=False)
        if key not in source_ids:
            source_ids[key] = len(sources)
            sources.append(value)
        return source_ids[key]

    for row in con.execute('select * from side_info'):
        s = dict(row)
        s['source'] = source_index(s['source'])
        s['extra'] = suppress_pay(parsed(s['extra'])) if s['kind'] == 'pay_2025' else parsed(s['extra'])
        if isinstance(s['extra'], dict) and s['extra'].get('is_individual'):
            s['extra']['contract'] = ''
            if s['extra'].get('description') and not str(s['extra']['description']).startswith(NEUTRAL):
                raise ValueError(f'Non-neutral individual description on {s["node_id"]}')
        kind = s['kind'] or ''
        s['section'] = ('Paid so far' if kind in ('vendors_paid', 'contract_family_paid_2026', 'paid_to_date') else 'Last year' if kind in ('pay_2025', 'pay_2025_actual', 'prior_year_budget', 'prior_year_actual') else 'More facts')
        sides[s['node_id']].append(s)

    records = {}
    periods = collections.Counter()
    for id, n in nodes.items():
        root = 'city-twice' if id.startswith('city-twice') else n['gov']
        extra = parsed(n['extra'])
        extra = {k: v for k, v in extra.items() if k in EXTRA_KEYS} if isinstance(extra, dict) else {}
        source = parsed(n['source'])
        period = period_for(source) if n['basis'] == 'paid_to_date' else None
        if period:
            periods[period] += 1
        name = n['name']
        short = name[:name.rfind(' ', 0, 80)] + '…' if len(name) > 100 and name.rfind(' ', 0, 80) > 0 and not name.endswith('…') else None
        ancestors = []
        p = n['parent_id']
        while p:
            ancestors.append(nodes[p]['name'])
            p = nodes[p]['parent_id']
        ancestors.reverse()
        chain = id
        while len(children[chain]) == 1:
            chain = children[chain][0]
        records[id] = {'id': id, 'parent_id': n['parent_id'], 'root': root, 'gov': n['gov'], 'kind': n['kind'] or 'box', 'name': name, 'official_name': extra.get('official_name'), 'short_name': short, 'amount_cents': n['amount_cents'], 'basis': n['basis'], 'period': period, 'period_label': PERIODS.get(period), 'caveats': [key for key, yes in (('midyear_2025_coding', extra.get('midyear_contract')), ('cps_vendor_total', period == 'cps_fy2026_vendor_total'), ('also_on_other_lines', extra.get('also_on_other_lines'))) if yes], 'count': n['count'], 'unit_amount_cents': n['unit_amount_cents'], 'unit_label': n['unit_label'], 'formula_kind': formula(n), 'why': n['why_cant_go_deeper'], 'note': n['note'] or ('Our estimate. The build did not record how this was worked out; see the box above.' if n['basis'] == 'proxy' else None), 'source': source_index(n['source']), 'is_leaf': bool(n['is_leaf']), 'n_children': n['n_children'], 'depth': n['depth'], 'path': ancestors, 'collapse_into': chain if chain != id else None, 'extra': extra, 'side': sides[id], 'side_ref': None}

    # A parent and its immediate children always travel together. Cut on estimated
    # subtree bytes, then place the cut root in its parent's chunk as a stub.
    weights = {id: len(json.dumps(r, ensure_ascii=False, default=str)) for id, r in records.items()}
    subweights = {}
    for id in sorted(nodes, key=lambda x: nodes[x]['depth'], reverse=True):
        subweights[id] = weights[id] + sum(subweights[c] for c in children[id])
    roots = [id for id, n in nodes.items() if not n['parent_id']]
    chunk_roots = set(roots)
    for id in sorted(nodes, key=lambda x: nodes[x]['depth']):
        if subweights[id] > 300_000:
            for child in children[id]:
                if subweights[child] > 300_000 or sum(weights[c] for c in children[id]) > 200_000:
                    chunk_roots.add(child)
    # Split large side payloads before writing chunks.
    for id, r in records.items():
        if len(json.dumps(r['side'], ensure_ascii=False)) > 20_000:
            filename = f'side/{hash_id(id)}.json'
            dump(out / filename, r['side'])
            r['side_ref'], r['side'] = filename, []
    chunks = collections.defaultdict(list)
    stubs = collections.defaultdict(list)
    owner = {}
    for id in sorted(nodes, key=lambda x: nodes[x]['depth']):
        parent = nodes[id]['parent_id']
        owner[id] = id if id in chunk_roots else owner[parent]
        chunks[owner[id]].append(records[id])
        if parent and owner[id] != owner[parent]:
            stubs[owner[parent]].append({k: records[id][k] for k in ('id', 'name', 'amount_cents', 'basis', 'is_leaf', 'n_children')})
    chunk_index = {}
    for id, group in chunks.items():
        filename = f'chunks/{hash_id(id)}.json'
        chunk_index[id] = filename
        dump(out / filename, {'root': id, 'ancestors': records[id]['path'], 'nodes': group, 'stubs': stubs[id]})
    spine = [{**{k: r[k] for k in ('id', 'parent_id', 'name', 'amount_cents', 'basis', 'kind', 'is_leaf', 'n_children', 'depth')}, 'chunk': chunk_index[owner[id]]} for id, r in records.items() if r['depth'] <= 3]
    dump(out / 'spine.json', spine)
    dump(out / 'sources.json', sources)
    source_roots = collections.defaultdict(set)
    for r in records.values():
        source_roots[r['source']].add(r['root'])
    dump(out / 'source_index.json', {str(index): sorted(roots) for index, roots in source_roots.items()})
    for root in ('city', 'city-twice', 'cps', 'parks'):
        entries = [{'id': r['id'], 'name': r['name'], 'path': r['path'], 'amount_cents': r['amount_cents']} for r in records.values() if r['root'] == root and 'name hidden' not in r['name'].lower() and not r['extra'].get('is_individual')]
        parts = max(1, (len(entries) + 3999) // 4000)
        filenames = [f'{root}-{i}.json' for i in range(parts)]
        dump(out / 'search' / f'{root}.json', {'parts': filenames})
        for i, filename in enumerate(filenames):
            dump(out / 'search' / filename, entries[i * 4000:(i + 1) * 4000])
    coverage_by_root = {}
    for root in roots:
        leaves = [n for n in nodes.values() if (n['id'].startswith('city-twice') and root == 'city-twice') or (root != 'city-twice' and n['gov'] == root and not n['id'].startswith('city-twice')) if n['is_leaf']]
        coverage_by_root[root] = {'strict': coverage(leaves), 'build': coverage(leaves, True)}
    checks = {r['gov']: json.loads(r['depth']) for r in con.execute('select * from checks')}
    for root in ('city', 'cps', 'parks'):
        if root in checks:
            for key in ('lt1m', '1m_10m', 'ge10m'):
                if abs(coverage_by_root[root]['build'][key] - checks[root][key]) > .0001:
                    raise ValueError(f'Coverage mismatch {root} {key}')
    totals = {root: nodes[root]['amount_cents'] for root in roots}
    gaps = {root: sorted([{'id': r['id'], 'amount_cents': r['amount_cents'], 'basis': r['basis'], 'why': r['why'], 'path': r['path']} for r in records.values() if r['root'] == root and r['is_leaf'] and abs(r['amount_cents']) >= 1_000_000_000], key=lambda r: -abs(r['amount_cents'])) for root in roots}
    dump(out / 'gaps.json', gaps)
    for filename, predicate in [('jobs.json', lambda r: r['count'] is not None), ('schools.json', lambda r: r['id'].startswith('cps.schools.') and r['kind'] == 'school'), ('parks.json', lambda r: r['id'].startswith('parks.') and r['kind'] == 'park')]:
        dump(out / filename, [{'id': r['id'], 'name': r['name'], 'amount_cents': r['amount_cents']} for r in records.values() if predicate(r)])
    vendor_rows = [dict(row) for row in con.execute('select * from vendors')] if 'vendors' in tables else []
    grouped = collections.defaultdict(list)
    for row in vendor_rows:
        if row.get('is_individual'):
            continue
        row['linked_node_ids'] = parsed(row['linked_node_ids']) if row.get('linked_node_ids') else []
        grouped[row['payee_display']].append(clean(row))
    vendors = [{'slug': hash_id(name), 'payee_display': name, 'rows': rows,
                'totals': {period: sum(r['amount_cents'] for r in rows if r['period'] == period)
                           for period in {r['period'] for r in rows}}}
               for name, rows in sorted(grouped.items())]
    individuals = [clean(row) for row in vendor_rows if row.get('is_individual')]
    dump(out / 'vendors_individuals.json', [{'period': period, 'amount_cents': sum(r['amount_cents'] for r in individuals if r['period'] == period), 'n_payments': sum(r['n_payments'] for r in individuals if r['period'] == period)} for period in sorted({r['period'] for r in individuals})])
    dump(out / 'vendors.json', vendors)
    dump(out / 'search/vendors.json', {'parts': ['vendors-0.json', 'vendors-1.json']})
    for part in range(2):
        dump(out / 'search' / f'vendors-{part}.json', [[r['slug'], r['payee_display']] for r in vendors if int(r['slug'][0], 16) % 2 == part])
    # Vendor detail is already in vendors.json and rendered HTML. Avoid 6,792 redundant files.
    if 'context' in tables:
        dump(out / 'context.json', [clean({k: parsed(v) if k in ('value', 'source') else v for k, v in dict(row).items()}) for row in con.execute('select * from context')])
    manifest = {'commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(), 'run_at': con.execute('select run_at from checks limit 1').fetchone()[0], 'totals': totals, 'gross_city_cents': totals['city'] + totals['city-twice'] + 11_698_850_200, 'coverage': coverage_by_root, 'periods': {key: {'label': PERIODS[key], 'count': count} for key, count in periods.items()}, 'chunks': chunk_index, 'id_hashes': {id: hash_id(id) for id in nodes if len(id) > 255}, 'counts': {'nodes': len(nodes), 'chunks': len(chunks), 'sources': len(sources), 'vendors': len(vendors)}, 'output_file_count': len(list(out.rglob('*.json'))) + 1}
    dump(out / 'manifest.json', manifest)
    con.close()
    return manifest


if __name__ == '__main__':
    print(json.dumps(export()['counts']))
