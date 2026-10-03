"""Regression checks for site-only database prerequisites."""
import csv
import json
import sqlite3
import unittest
from decimal import Decimal
from pathlib import Path

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


if __name__ == '__main__':
    unittest.main()
