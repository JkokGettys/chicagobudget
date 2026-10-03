#!/usr/bin/env python3
"""Validate the public export against the database and privacy/size invariants."""
import gzip
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

from export_site import DB, OUT, PAY_FIELDS, PERIODS, ROOT, coverage, safe_repo_path
from payee import ALLOWED_INDIVIDUAL_DESCRIPTIONS

BASIS = {'budget', 'tied', 'paid_to_date', 'proxy', 'adjustment', 'residual', 'gov_estimate'}
TOTALS = {'city': 1_684_255_300_300, 'city-twice': 170_902_695_500, 'cps': 1_025_332_746_368, 'parks': 63_758_035_000}


def validate_individuals(value, location='root'):
    """Reject identifying fields in an individual row at any nesting level."""
    if isinstance(value, list):
        for index, item in enumerate(value):
            validate_individuals(item, f'{location}[{index}]')
    elif isinstance(value, dict):
        if value.get('is_individual') or value.get('vendor') == 'Individual (name hidden)':
            for key in ('contract', 'contract_number'):
                assert not value.get(key), f'{location}: individual {key} leaked'
            if 'description' in value:
                assert value['description'] in ALLOWED_INDIVIDUAL_DESCRIPTIONS, f'{location}: identifying description'
        for key, item in value.items():
            validate_individuals(item, f'{location}.{key}')


def validate(db=DB, out=OUT):
    manifest = json.loads((out / 'manifest.json').read_text())
    assert manifest['totals'] == TOTALS, 'official root totals'
    assert manifest['gross_city_cents'] == 1_866_856_846_000, 'gross reconciliation'
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    originals = {r['id']: dict(r) for r in con.execute('select * from nodes')}
    sources = json.loads((out / 'sources.json').read_text())
    tracked = set(subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().strip('\0').split('\0'))
    for source in sources:
        if isinstance(source, dict) and 'repo_path' in source:
            assert safe_repo_path(source['repo_path'], tracked) == source['repo_path'], source['repo_path']
    records = {}
    for root, filename in manifest['chunks'].items():
        chunk = json.loads((out / filename).read_text())
        assert chunk['root'] == root
        for item in chunk['nodes']:
            assert item['id'] not in records, f'duplicate {item["id"]}'
            records[item['id']] = item
        for stub in chunk['stubs']:
            assert stub['id'] in originals
            assert stub['amount_cents'] == originals[stub['id']]['amount_cents']
    assert records.keys() == originals.keys(), 'missing or extra chunk records'
    assert manifest['counts']['nodes'] == len(records)
    for id, r in records.items():
        assert re.fullmatch(r'[a-z0-9.-]+', id), id
        assert r['basis'] in BASIS, id
        assert r['source'] is not None and sources[r['source']], id
        assert r['amount_cents'] == originals[id]['amount_cents'], id
        if r['is_leaf'] and abs(r['amount_cents']) >= 1_000_000_000 and r['basis'] != 'adjustment':
            assert r['why'], id
        if r['basis'] == 'paid_to_date':
            assert r['period'] in PERIODS and r['period_label'] == PERIODS[r['period']], id
        if r['formula_kind'] == 'exact':
            assert abs(r['count'] * r['unit_amount_cents'] - r['amount_cents']) <= 100, id
        if r['side_ref']:
            assert not r['side']
            side = json.loads((out / r['side_ref']).read_text())
        else:
            side = r['side']
        for fact in side:
            assert isinstance(fact['source'], int) and 0 <= fact['source'] < len(sources)
            if fact['kind'] == 'pay_2025':
                group = fact['extra'].get('group', {})
                for field, protected in PAY_FIELDS.items():
                    if isinstance(group.get(field), (float, int)) and group[field] < 5:
                        assert not set(protected.split()) & group.keys(), (id, field)
    children = {}
    for r in records.values():
        if r['parent_id']:
            children.setdefault(r['parent_id'], []).append(r)
    for id, group in children.items():
        assert sum(r['amount_cents'] for r in group) == records[id]['amount_cents'], id
        assert records[id]['n_children'] == len(group), id
    for root in TOTALS:
        leaves = [r for r in originals.values() if r['is_leaf'] and (r['id'].startswith('city-twice') if root == 'city-twice' else r['gov'] == root and not r['id'].startswith('city-twice'))]
        assert manifest['coverage'][root]['strict'] == coverage(leaves), root
        assert manifest['coverage'][root]['build'] == coverage(leaves, True), root
    checks = {r['gov']: json.loads(r['depth']) for r in con.execute('select * from checks')}
    for root in ('city', 'cps', 'parks'):
        for key in ('lt1m', '1m_10m', 'ge10m'):
            assert abs(manifest['coverage'][root]['build'][key] - checks[root][key]) <= .0001, root
    periods = {}
    for r in records.values():
        if r['period']:
            periods[r['period']] = periods.get(r['period'], 0) + 1
    assert manifest['periods'] == {key: {'label': PERIODS[key], 'count': count} for key, count in periods.items()}
    files = list(out.rglob('*.json'))
    assert len(files) == manifest['output_file_count']
    for file in files:
        assert len(file.name) <= 100, file
        text = file.read_text()
        assert '—' not in text, file
        assert not re.search(r'data/people|raw/|"file"\s*:', text), file
        data = json.loads(text)
        validate_individuals(data, str(file))
        if file.parent.name == 'search':
            assert 'name hidden' not in text.lower(), file
        size = len(gzip.compress(text.encode(), compresslevel=6))
        ceiling = 100_000 if file.parent.name == 'chunks' else 60_000 if file.name == 'spine.json' else 40_000 if file.name == 'sources.json' else 150_000 if file.parent.name in ('side', 'search') else None
        if ceiling:
            assert size <= ceiling, f'{file}: {size} > {ceiling}'
    print(f'Validated {len(records)} boxes, {len(files)} JSON files, 4 separate coverage roots')
    con.close()


if __name__ == '__main__':
    validate(Path(sys.argv[1]) if len(sys.argv) > 1 else DB, Path(sys.argv[2]) if len(sys.argv) > 2 else OUT)
