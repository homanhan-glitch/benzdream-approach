import copy
import unittest
import tempfile
from pathlib import Path
from openpyxl import Workbook
from update_nationwide import transition, saleable, stock_snapshot, build_web, load_source, REQUIRED
from vehicle_identity import commission_id

def row(**updates):
    r=dict(model='E 200 AMG Line',cat='E클래스',year='2026',ext='폴라 화이트',interior='베이지',
           sale='미배정',type='입고 물량',vehicle='판매 가능',availability='판매 가능',
           dealer='Mercedes Benz Korea',purpose='',pdd='2026-11',issues=[])
    r.update(updates);return r

def contracted(**updates):
    return row(sale='가계약 체결',vehicle='가계약',dealer='HS효성더클래스 강남대로',**updates)

class NationwideTests(unittest.TestCase):
    def fixture(self, keys, name='전국재고_1110.xlsx', company='HS HYOSUNG The Class Corp.'):
        folder=tempfile.TemporaryDirectory();self.addCleanup(folder.cleanup)
        path=Path(folder.name)/name;w=Workbook();s=w.active;s.title='Sheet1'
        headers=sorted(REQUIRED);s.append(headers)
        data={'모델명':'E 200 AMG Line','모델 연도':'2027','외장 색상':'화이트','내장 색상':'베이지','판매 상태':'미배정',
              '재고 유형':'입고 물량','차량 상태':'판매 가능','가용 여부':'판매 가능','배정 전시장':'Mercedes Benz Korea','데이터 검증':'유효'}
        for key in keys:s.append([key if h=='커미션 번호' else data.get(h,'') for h in headers])
        b=w.create_sheet('Stock Balance Report');b.cell(2,2,'10-Nov-26');b.cell(5,2,company);w.save(path);return path

    def test_source_rejects_missing_duplicate_and_bad_ids(self):
        for keys in [[None],['0123456789','0123456789'],['123456789']]:
            with self.assertRaises(ValueError):load_source(self.fixture(keys))

    def test_source_checks_date_and_company(self):
        for path in [self.fixture(['0123456789'],name='전국재고_1109.xlsx'),self.fixture(['0123456789'],company='Other company')]:
            with self.assertRaises(ValueError):load_source(path)

    def test_source_keeps_commission_prefix_and_zero(self):
        d,rows,meta=load_source(self.fixture(['0123456789','DKR1234567']))
        self.assertEqual(set(rows),{'0123456789','DKR1234567'});self.assertEqual(d,'2026-11-10')

    def test_identity_preserves_source(self):
        self.assertEqual(commission_id('0123456789'),'0123456789')
        self.assertEqual(commission_id('DKR1234567'),'DKR1234567')
        self.assertNotEqual(commission_id('0123456789'),commission_id('123456789'))

    def test_only_saleable_physical(self):
        self.assertTrue(saleable(row()))
        for change in [dict(type='예정 물량'),dict(purpose='Virtual VIN'),dict(purpose='Pre-Order VIN'),
                       dict(purpose='전시차'),dict(purpose='MPC 위탁 재고'),dict(type=''),
                       dict(availability='판매 불가'),dict(issues=['state_conflict']),dict(dealer='딜러')]:
            self.assertFalse(saleable(row(**change)))

    def test_cancel_recontract_net(self):
        outstanding={}; start={'0123456789':row()}; contract={'0123456789':contracted()}
        a=transition(start,contract,outstanding)[1]
        b=transition(contract,start,outstanding)[1]
        c=transition(start,contract,outstanding)[1]
        self.assertEqual([a['net'],b['net'],c['net']],[1,-1,1])
        self.assertEqual(a['net']+b['net']+c['net'],1)

    def test_disappear_return_deducted_once(self):
        outstanding={}; start={'0123456789':row()}
        self.assertEqual(transition(start,{},outstanding)[1]['net'],1)
        self.assertEqual(transition({},start,outstanding)[1]['net'],-1)
        self.assertEqual(transition(start,start,outstanding)[1]['net'],0)
        self.assertEqual(outstanding,{})

    def test_existing_invalid_is_not_sale(self):
        a={'0123456789':row()}; b={'0123456789':row(issues=['stock_type'],type='')}
        result=transition(a,b,{})[1]
        self.assertEqual(result['national_out'],0)
        self.assertEqual(result['net'],0)
        self.assertEqual(result['stock_out'],1)

    def test_virtual_exit_is_not_contract(self):
        a={'DKR1234567':row(type='예정 물량',purpose='Virtual VIN')}
        self.assertEqual(transition(a,{}, {})[1]['net'],0)

    def test_first_seen_contract_and_scope_transfer_not_new(self):
        a={'0123456789':contracted(type='예정 물량')}; b={'0123456789':contracted()}
        self.assertEqual(transition({},b,{})[1]['own_new'],0)
        self.assertEqual(transition(a,b,{})[1]['own_new'],0)
        self.assertEqual(transition(a,b,{})[2]['own_scope_adjustment'],1)

    def test_confirm_not_counted_twice(self):
        a={'0123456789':contracted()};b={'0123456789':row(sale='계약 확정',vehicle='계약 확정',dealer='HS효성더클래스 강남대로')}
        result=transition(a,b,{})[1]
        self.assertEqual(result['net'],0);self.assertEqual(result['own_confirm'],1)

    def test_new_color_and_model_year_coverage(self):
        a={'0123456789':row(),'0223456789':row(year='2027'), '0323456789':row(ext='그라파이트 그레이',interior='브라운')}
        s=stock_snapshot(a,'2026-11-10');m=s['models']['E 200 AMG Line']
        self.assertEqual(s['sellable_total'],3)
        self.assertEqual(m['colors']['폴라 화이트|베이지'],2)
        self.assertEqual(m['year_groups']['2027']['colors']['폴라 화이트|베이지'],1)
        self.assertEqual(m['colors']['그라파이트 그레이|브라운'],1)

if __name__=='__main__':unittest.main()
