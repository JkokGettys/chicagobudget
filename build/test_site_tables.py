"""Regression checks for site-only database prerequisites."""
import csv
import json
import sqlite3
import unittest
from decimal import Decimal
from pathlib import Path

from build.payee import is_business, people_by_description

ROOT = Path(__file__).resolve().parent.parent


class SiteTablesTest(unittest.TestCase):
    def test_real_tables_reconcile_to_deduplicated_payments(self):
        with sqlite3.connect(ROOT / 'data/budget.db') as db:
            for suffix, period in [('2025', 'city_2025'), ('2026ytd', 'city_2026_payments')]:
                with (ROOT / f'raw/contracts/payments_{suffix}_dedup.csv').open(newline='') as fh:
                    rows = list(csv.DictReader(fh))
                expected_cents = sum(int(Decimal(row['amount']) * 100) for row in rows)
                actual_cents, actual_count = db.execute(
                    'SELECT sum(amount_cents), sum(n_payments) FROM vendors WHERE period=?', (period,)
                ).fetchone()
                self.assertEqual((actual_cents, actual_count), (expected_cents, len(rows)))
                anonymous = db.execute('SELECT payee_display, contract_number, department, linked_node_ids FROM vendors WHERE period=? AND is_individual=1', (period,)).fetchall()
                self.assertEqual(anonymous, [('Individuals (names hidden)', '', '', '[]')])
            context = dict(db.execute('SELECT key,value FROM context'))
            source = json.loads((ROOT / 'data/context_resident_2026.json').read_text())
            self.assertEqual(context['chicago_population'], source['population']['chicago_population'])
            self.assertEqual(context['cps_students_fy2026'], source['cps_enrollment']['sy2025_26_20th_day'])
            for key, raw in db.execute('SELECT key,source FROM context'):
                self.assertTrue(json.loads(raw)['url'].startswith('https://'), key)
            for (ids,) in db.execute('SELECT linked_node_ids FROM vendors WHERE linked_node_ids != ?', ('[]',)):
                self.assertTrue(all(db.execute('SELECT 1 FROM nodes WHERE id=?', (node_id,)).fetchone() for node_id in json.loads(ids)))

    def test_upstream_hidden_payees_and_employee_rosters_are_not_businesses(self):
        items = json.loads((ROOT / 'data/city_vendors_items_2026ytd.json').read_text())
        city_path = ROOT / 'data/people/city_employees_2026.json'
        people = set()
        if city_path.exists():
            city = json.loads(city_path.read_text())
            people |= {e['name'].upper().strip() for group in ('current_employees', 'paid_2025_not_matched_to_current_roster')
                       for e in city.get(group, []) if e.get('name')}
        cps_path = ROOT / 'data/people/cps_positions_2025q4.json'
        if cps_path.exists():
            people |= {e['name'].upper().strip() for e in json.loads(cps_path.read_text()).get('positions', []) if e.get('name')}
        payees = [(v[0], v[1], v[4]) for department in items['departments'].values()
                  for family in department['families'].values() for v in family]
        people |= people_by_description((name, description) for name, _, description in payees)
        contracts = {}
        for name, contract, _ in payees:
            key = (name or '').upper().strip()
            contracts[key] = contracts.get(key, False) or bool(contract)
        hidden = {name for name, contract in contracts.items() if not is_business(name, contract, people)}
        with sqlite3.connect(ROOT / 'data/budget.db') as db:
            exposed = {name.upper().strip() for (name,) in db.execute('SELECT DISTINCT payee_display FROM vendors WHERE is_individual=0')}
        self.assertFalse(exposed & hidden, 'City-tree hidden payees leaked in vendors')
        self.assertFalse(exposed & people, 'employee roster names leaked in vendors')


if __name__ == '__main__':
    unittest.main()
