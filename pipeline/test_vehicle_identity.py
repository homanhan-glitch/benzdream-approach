import unittest
from unittest.mock import patch
import pandas as pd
import parse_contracts as contracts
from vehicle_identity import commission_id, normalize_interior_color
from parse_inventory_v3 import build_snapshot
from build_stock import validate_source_coverage


class CommissionTests(unittest.TestCase):
    def row(self, vin=None, com=123, state='미배정'):
        return {'커미션 번호': com, '차대 번호': vin, '모델명': 'E 200',
                '판매 상태': state, '재고구분': '전국재고', '재고 유형': '입고 물량'}

    def load(self, rows):
        with patch.object(contracts.pd, 'read_excel', return_value=pd.DataFrame(rows)):
            return contracts.load('test.xlsx')

    def test_excel_number_normalization(self):
        self.assertEqual(commission_id(123.0), '123')
        self.assertEqual(commission_id(' 00123 '), '00123')
        self.assertIsNone(commission_id(float('nan')))

    def test_artico_beige_is_not_classified_as_black(self):
        self.assertEqual(normalize_interior_color('ARTICO man-made leather beige'), '베이지 인조가죽')
        self.assertEqual(normalize_interior_color('black ARTICO man-made leather'), '블랙 인조가죽')
        self.assertEqual(contracts.clean_int_color('ARTICO man-made leather beige'), '베이지 인조가죽')

    def test_vin_disappears_without_false_new_or_depleted(self):
        previous = self.load([self.row('OLDVIN')])
        current = self.load([self.row(None, state='계약 확정')])
        event = contracts.diff(previous, current, '2026-09-21', '2026-09-18')
        self.assertEqual(event['models']['E클래스|E 200'], {'mo_new': 1})

    def test_missing_and_duplicate_commission_fail(self):
        for rows in [[self.row(com=None)], [self.row(com=123), self.row(com='123.0')]]:
            with self.assertRaises(ValueError):
                self.load(rows)

    def test_migration_preserves_previous_values(self):
        previous = {'OLDVIN': ['previous status']}
        with patch.object(contracts.pd, 'read_excel', return_value=pd.DataFrame([self.row('OLDVIN')])):
            self.assertEqual(contracts.migrate_identity(previous, ['old.xlsx']), {'123': ['previous status']})
        with self.assertRaises(ValueError):
            contracts.migrate_identity(previous, [])
        self.assertEqual(previous, {'OLDVIN': ['previous status']})

    def test_unknown_state_not_assumed_sellable(self):
        row = self.row(state=None)
        row['재고 유형'] = None
        self.assertEqual(contracts.snapshot_stock(self.load([row])), {})

    def test_customer_stock_without_vin_and_cross_sheet_duplicate(self):
        row = dict(com='123', vin=None, model='E 200', is_virtual=False,
                   car_status='판매 가능', sale_status='미배정', inv_class='전국재고',
                   source='allocation', pdd=None, ext_color='블랙', int_color='브라운',
                   salesman='', customer='', branch='')
        snap = build_snapshot({'date':'2026-09-21', 'filename':'test.xlsx',
                               'rows':[row, dict(row, source='위탁재고')]})
        self.assertEqual(snap['sellable_total'], 1)
        self.assertEqual(snap['models']['E 200']['colors']['블랙|브라운']['total'], 1)
        self.assertEqual(snap['models']['E 200']['sellable_years']['unknown']['블랙|브라운'], 1)
        validate_source_coverage({'rows':[row, dict(row, source='위탁재고')]}, snap)

    def test_customer_stock_keeps_model_year_separate(self):
        base = dict(com='123', vin=None, model='GLC 300', is_virtual=False,
                    car_status='판매 가능', sale_status='미배정', inv_class='전국재고',
                    source='allocation', pdd=None, ext_color='폴라 화이트', int_color='블랙',
                    salesman='', customer='', branch='')
        rows = [dict(base, com='123', model_year='2026'), dict(base, com='124', model_year='2027')]
        snap = build_snapshot({'date':'2026-09-21', 'filename':'test.xlsx', 'rows':rows})
        years = snap['models']['GLC 300']['sellable_years']
        self.assertEqual(years['2026']['폴라 화이트|블랙'], 1)
        self.assertEqual(years['2027']['폴라 화이트|블랙'], 1)
        validate_source_coverage({'rows':rows}, snap)

    def test_coverage_check_rejects_missing_commission(self):
        row = dict(com='123', vin=None, model='E 200', is_virtual=False,
                   car_status='판매 가능', sale_status='미배정', inv_class='전국재고',
                   source='allocation', pdd=None, ext_color='폴라 화이트', int_color='베이지 인조가죽',
                   salesman='', customer='', branch='')
        snap = build_snapshot({'date':'2026-09-21', 'filename':'test.xlsx', 'rows':[row]})
        snap['sellable_commissions'] = []
        with self.assertRaisesRegex(ValueError, 'commission coverage'):
            validate_source_coverage({'rows':[row]}, snap)


if __name__ == '__main__':
    unittest.main()
