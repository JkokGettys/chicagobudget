"""Public export invariants, including regression against the real database."""
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'build'))
from export_site import clean, coverage, formula, period_for, suppress_pay, DB, OUT
from validate_site_data import validate


class ExportTests(unittest.TestCase):
    def test_private_paths_and_file_keys_recursive(self):
        value = {'file': 'raw/secret.csv', 'source': [{'file': 'data/people/private.json', 'note': 'see raw/secret.csv'}], 'extra': {'file': 'raw/a'}}
        result = clean(value)
        self.assertNotIn('raw/', json.dumps(result))
        self.assertNotIn('data/people', json.dumps(result))
        self.assertNotIn('"file"', json.dumps(result))

    def test_all_pay_groups_suppressed_field_by_field(self):
        from export_site import PAY_FIELDS
        for count, fields in PAY_FIELDS.items():
            group = {count: 4, **{field: 123 for field in fields.split()}, 'budget_2026_total': 999}
            result = suppress_pay({'group': group})['group']
            self.assertEqual(result[count], 4)
            self.assertEqual(result['budget_2026_total'], 999)
            self.assertTrue(set(fields.split()).isdisjoint(result))

    def test_paid_period_is_own_source_and_unknown_fails(self):
        self.assertEqual(period_for({'doc': 'Judgments through 2026-07-31'}), 'city_law_2026_to_0731')
        self.assertEqual(period_for({'doc': 'supplier payments FY2026'}), 'cps_fy2026_vendor_total')
        self.assertEqual(period_for({'doc': 'Capital Expenditures FY2026'}), 'cps_fy2026_capital')
        with self.assertRaises(ValueError):
            period_for({'doc': 'Unknown 2027 payment file'})

    def test_strict_vs_build_coverage(self):
        leaves = [{'amount_cents': 200_000_000, 'count': 3, 'unit_amount_cents': 66_666_667}, {'amount_cents': -20_000_000, 'count': None, 'unit_amount_cents': None}]
        self.assertEqual(coverage(leaves)['lt1m'], .0909)
        self.assertEqual(coverage(leaves, True)['lt1m'], 1)

    def test_formula_never_claims_exact_for_non_exact(self):
        self.assertEqual(formula({'count': 2, 'unit_amount_cents': 10_000, 'amount_cents': 20_000}), 'exact')
        self.assertNotEqual(formula({'count': 2, 'unit_amount_cents': 10_000, 'amount_cents': 30_000}), 'exact')

    def test_real_export(self):
        if not DB.exists() or not (OUT / 'manifest.json').exists():
            self.skipTest('real database/export not present')
        validate(DB, OUT)


if __name__ == '__main__':
    unittest.main()
