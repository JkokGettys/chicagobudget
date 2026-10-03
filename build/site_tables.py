#!/usr/bin/env python3
"""Add sourced comparison and deduplicated City payment tables to budget.db.

Run after all three tree builders. Dollars are summed from the deduplicated payment
CSV only, never from proxy side facts. Individual payees are pooled by period.
"""
import csv
import json
import sqlite3
from collections import defaultdict
from decimal import Decimal
from pathlib import Path

from payee import is_business

ROOT = Path(__file__).resolve().parent.parent
PERIODS = {2025: 'city_2025', 2026: 'city_2026_payments'}


def add_context(db):
    data = json.loads((ROOT / 'data/context_resident_2026.json').read_text())
    pop, enrollment, tax = data['population'], data['cps_enrollment'], data['tax_bill']
    rows = [
        ('chicago_population', pop['chicago_population'], {'name': pop['source'], 'url': pop['source_url'], 'table_ids': pop['census_table_ids'], 'geoid': pop['geoid']}),
        ('chicago_households', pop['households'], {'name': pop['source'], 'url': pop['source_url'], 'table_ids': pop['census_table_ids'], 'geoid': pop['geoid']}),
        ('cps_students_fy2026', enrollment['sy2025_26_20th_day'], {'name': 'CPS SY2025-26 20th-day enrollment', 'url': enrollment['source_urls'][0]}),
        ('tax_year', tax['tax_year'], {'name': 'Cook County Clerk 2025 Tax Rate Report', 'url': tax['source_url']}),
        ('tax_composite_rate_pct', tax['total_composite_rate_pct'], {'name': 'Cook County Clerk 2025 Tax Rate Report', 'url': tax['source_url']}),
    ]
    rows.extend((f'tax_rate_pct:{name}', value, {'name': 'Cook County Clerk 2025 Tax Rate Report', 'url': tax['source_url'], 'tax_year': tax['tax_year']}) for name, value in sorted(tax['rates_pct_by_agency'].items()))
    rows.extend((f'tax_bill_share:{name}', value, {'name': 'Cook County Clerk 2025 Tax Rate Report', 'url': tax['source_url'], 'tax_year': tax['tax_year'], 'method': 'agency rate divided by composite rate'}) for name, value in sorted(tax['group_share_of_bill'].items()))
    db.execute('DROP TABLE IF EXISTS context')
    db.execute('CREATE TABLE context (key TEXT PRIMARY KEY, value REAL NOT NULL, source TEXT NOT NULL)')
    db.executemany('INSERT INTO context VALUES (?,?,?)', ((k, v, json.dumps(s, sort_keys=True)) for k, v, s in rows))


def add_vendors(db):
    # Name matching is a navigation aid, not a claim that all invoices can be
    # assigned to one budget line. Unmatched rows remain in the table.
    by_name = defaultdict(set)
    for node_id, name, kind, extra in db.execute("SELECT id,name,kind,extra FROM nodes WHERE gov='city' AND kind IN ('vendor','contract')"):
        by_name[name.upper().strip()].add(node_id)
    db.execute('DROP TABLE IF EXISTS vendors')
    db.execute('''CREATE TABLE vendors (
        payee_display TEXT NOT NULL, is_individual INTEGER NOT NULL CHECK(is_individual IN (0,1)),
        period TEXT NOT NULL, amount_cents INTEGER NOT NULL, n_payments INTEGER NOT NULL,
        contract_number TEXT NOT NULL, department TEXT NOT NULL,
        linked_node_ids TEXT NOT NULL, PRIMARY KEY (payee_display, period, contract_number, department)
    )''')
    totals = defaultdict(lambda: [0, 0])
    individual_names = defaultdict(set)
    for year, period in PERIODS.items():
        path = ROOT / f'raw/contracts/payments_{year if year == 2025 else "2026ytd"}_dedup.csv'
        with path.open(newline='') as fh:
            for row in csv.DictReader(fh):
                name = row['vendor_name'].strip()
                contract = row['contract_number'].strip()
                individual = not is_business(name, bool(contract and contract != 'DV'))
                if individual:
                    key = ('Individuals (names hidden)', 1, period, '', '')
                    individual_names[period].add(name)
                else:
                    key = (name, 0, period, contract, row['department_name'].strip())
                cents = int((Decimal(row['amount']) * 100).to_integral_exact())
                totals[key][0] += cents
                totals[key][1] += 1
    records = []
    for (name, individual, period, contract, department), (amount, count) in sorted(totals.items()):
        ids = set() if individual else by_name[name.upper()]
        records.append((name, individual, period, amount, count, contract, department, json.dumps(sorted(ids))))
    db.executemany('INSERT INTO vendors VALUES (?,?,?,?,?,?,?,?)', records)
    db.execute('CREATE INDEX IF NOT EXISTS vendors_period ON vendors(period)')
    print('vendors:', len(records), 'rows, individual payees pooled:', dict((k, len(v)) for k, v in individual_names.items()))
    print('context:', db.execute('SELECT count(*) FROM context').fetchone()[0], 'rows')


def main():
    with sqlite3.connect(ROOT / 'data/budget.db') as db:
        add_context(db)
        add_vendors(db)


if __name__ == '__main__':
    main()
