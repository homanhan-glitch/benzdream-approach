#!/usr/bin/env python3
"""
rebuild_history_v3.py — 모든 엑셀 파일을 새 구조로 일괄 파싱하고
inventory_history_v3.json (메인 트렌드) + vin_states/ (VIN 상태 추적용) 생성.

새 지침:
- 차종 중심, G클래스 제외 (별도 보관)
- Virtual + Actual 합산 + Virtual 비율 별도 노출
- 위탁/전시차 일반 재고와 합산
- 주간/월간 트렌드 (일별은 보조)
- 타사 해약은 백엔드 감지만, UI 노출 X
"""

import sys
import os
import re
import json
import glob
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from parse_inventory_v3 import parse_excel, build_snapshot, is_g_class, categorize


SOURCE_DIR = '/sessions/fervent-gracious-brahmagupta/mnt/재고표 코워크 작업 폴더'
OUT_DIR = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/v3_snapshots'
PROGRESS = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/rebuild_progress.txt'
HISTORY_OUT = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/inventory_history_v3.json'

os.makedirs(OUT_DIR, exist_ok=True)

# 이상치 파일 (축소 버전 — 정상 ~12,000~16,000대 대비 1,000대 이하)
OUTLIER_DATES = ['2026-04-16', '2026-04-22']


def log(msg):
    with open(PROGRESS, 'a') as f:
        f.write(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}\n')
    print(msg, flush=True)


def find_files():
    """SOURCE_DIR에서 날짜 추출 가능한 .xlsx 파일 찾기. 같은 날짜는 더 큰 파일 사용."""
    by_date = {}
    for fp in glob.glob(f'{SOURCE_DIR}/*.xlsx'):
        m = re.search(r'(\d{4}-\d{2}-\d{2})', os.path.basename(fp))
        if not m: continue
        date = m.group(1)
        sz = os.path.getsize(fp)
        if date not in by_date or sz > by_date[date][1]:
            by_date[date] = (fp, sz)
    return [(d, by_date[d][0], by_date[d][1]) for d in sorted(by_date)]


def parse_one(date, fp):
    """단일 파일 파싱 → 스냅샷 JSON 저장 + VIN states 별도 저장."""
    out_snap = f'{OUT_DIR}/{date}_snap.json'
    out_vins = f'{OUT_DIR}/{date}_vins.json'

    if os.path.exists(out_snap) and os.path.exists(out_vins):
        log(f'  스킵 (이미 완료): {date}')
        return True

    try:
        log(f'  파싱 시작: {date}  ({os.path.basename(fp)})')
        parsed = parse_excel(fp)
        snap = build_snapshot(parsed)

        vins_meta = snap.pop('vins_meta')
        with open(out_snap, 'w', encoding='utf-8') as f:
            json.dump(snap, f, ensure_ascii=False, default=str)
        with open(out_vins, 'w', encoding='utf-8') as f:
            json.dump(vins_meta, f, ensure_ascii=False, default=str)

        log(f'  완료: {date}  레코드{snap["total_records"]}  G제외{snap["sellable_total"]}  G{snap["g_class"]["sellable"]}')
        return True
    except Exception as e:
        log(f'  실패: {date}  {e}')
        return False


def parse_all_files(file_subset=None):
    """모든 파일 파싱. file_subset이 주어지면 해당 날짜들만."""
    files = find_files()
    if file_subset:
        files = [f for f in files if f[0] in file_subset]

    log(f'대상 파일 {len(files)}개')
    for date, fp, sz in files:
        if date in OUTLIER_DATES:
            log(f'  이상치 스킵: {date}  ({sz//1024}KB)')
            continue
        parse_one(date, fp)


def compare_snapshots(prev_vins, curr_vins, prev_snap, curr_snap):
    """전일 vs 당일 비교 → 계약/해약/신규/모델별 계약 등 분석.

    - 계약 = 전일 미배정 → 당일 배정 (sale_status가 미배정→가계약/계약확정/배정)
    - 해약 = 전일 배정 → 당일 미배정
    - 신규 = 전일에 없던 VIN이 당일 등장 (Actual VIN 기준 — Virtual은 매일 변동 가능성)
    - 출고 = 전일에 있던 VIN이 당일 사라짐 (배정상태였던 것만)
    - 모델별 계약 카운트 (G클래스 제외)
    """
    prev_vin_set = set(prev_vins.keys())
    curr_vin_set = set(curr_vins.keys())

    contracted = 0
    cancelled = 0
    delivered = 0
    new_actual = 0
    new_virtual = 0
    motorone_contract = 0
    external_contract = 0  # 타딜러 계약 (VIN 소실)

    model_contracts = {}  # G제외
    g_contracts = 0

    # 신규 등장 VIN
    for v in curr_vin_set - prev_vin_set:
        cm = curr_vins[v]
        if cm.get('is_g'): continue  # G는 별도 카운트만
        if cm.get('is_virtual'):
            new_virtual += 1
        else:
            new_actual += 1

    # 사라진 VIN — 출고 또는 타딜러 계약
    disappeared = prev_vin_set - curr_vin_set
    for v in disappeared:
        pm = prev_vins[v]
        was_assigned = pm.get('sale_status') in ('가계약', '계약 확정', '배정')
        is_g = pm.get('is_g')

        if was_assigned:
            delivered += 1
        else:
            # 미배정이었는데 사라짐 → 타딜러 계약 또는 시스템 변동
            if not is_g:
                external_contract += 1

    # 상태 변화
    for v in prev_vin_set & curr_vin_set:
        pm = prev_vins[v]
        cm = curr_vins[v]
        was_un = pm.get('sale_status') in ('미배정', None, '')
        now_assigned = cm.get('sale_status') in ('가계약', '계약 확정', '배정')

        if was_un and now_assigned:
            contracted += 1
            if cm.get('is_g'):
                g_contracts += 1
            else:
                model = cm.get('model', '')
                model_contracts[model] = model_contracts.get(model, 0) + 1
                # 모터원 배정인지 확인
                if '배정재고' in (cm.get('inv_class') or '') or cm.get('branch') in ('모터원고양', '고양', '일산', '의정부', '파주'):
                    motorone_contract += 1
        elif (not was_un) and (cm.get('sale_status') in ('미배정', None, '')):
            cancelled += 1

    return {
        'contracted': contracted,
        'g_contracts': g_contracts,
        'national_contract': contracted - g_contracts,  # G제외 전국 계약
        'motorone_contract': motorone_contract,
        'external_contract': external_contract,
        'cancelled': cancelled,
        'delivered': delivered,
        'new_actual': new_actual,
        'new_virtual': new_virtual,
        'model_contracts': model_contracts,
    }


def build_history_v3():
    """모든 스냅샷 파일을 읽어 inventory_history_v3.json 생성.

    - 일별 데이터: 모델별 재고 + 일별 계약/해약
    - 주간 누적: 최근 7일/지난주
    - 월간 누적: 이번 달
    """
    snap_files = sorted(glob.glob(f'{OUT_DIR}/*_snap.json'))
    vin_files = {Path(f).stem.replace('_vins',''): f for f in glob.glob(f'{OUT_DIR}/*_vins.json')}

    daily_snapshots = []
    prev_vins = None
    prev_snap = None

    for sf in snap_files:
        date = Path(sf).stem.replace('_snap','')
        with open(sf, 'r', encoding='utf-8') as f:
            snap = json.load(f)

        vin_path = vin_files.get(date)
        curr_vins = {}
        if vin_path:
            with open(vin_path, 'r', encoding='utf-8') as f:
                curr_vins = json.load(f)

        # 모델별 집계 (G 제외, 메인 데이터)
        # JSON에서 dict의 키가 문자열인지 확인
        models = snap['models']  # {모델명: {cat, total, virtual, actual, sellable, ...}}
        g_class = snap.get('g_class', {})

        compare = None
        if prev_vins:
            compare = compare_snapshots(prev_vins, curr_vins, prev_snap, snap)

        entry = {
            'date': date,
            'total_records': snap['total_records'],
            'sellable_total': snap['sellable_total'],   # G 제외
            'virtual_total': snap['virtual_total'],     # G 제외
            'actual_total': snap['actual_total'],       # G 제외
            'models': models,
            'g_class': g_class,
            'compare': compare,
        }
        daily_snapshots.append(entry)
        prev_vins = curr_vins
        prev_snap = snap

    # ===== 주간/월간 누적 계산 =====
    # 최근 데이터 기준으로 주간(이번주, 7일), 월간(이번 달) 합계
    def week_start(date_str):
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return (d - timedelta(days=d.weekday())).strftime('%Y-%m-%d')

    def month_start(date_str):
        d = datetime.strptime(date_str, '%Y-%m-%d')
        return d.replace(day=1).strftime('%Y-%m-%d')

    weekly_agg = {}   # week_start -> {model_contracts, total_contract}
    monthly_agg = {}  # month_start -> {model_contracts, total_contract}

    for s in daily_snapshots:
        if not s.get('compare'): continue
        c = s['compare']
        d = s['date']
        ws = week_start(d)
        ms = month_start(d)

        for agg_dict, k in [(weekly_agg, ws), (monthly_agg, ms)]:
            if k not in agg_dict:
                agg_dict[k] = {
                    'period_start': k,
                    'days': [],
                    'total_contract': 0,
                    'total_external': 0,
                    'total_motorone': 0,
                    'total_cancelled': 0,
                    'total_delivered': 0,
                    'model_contracts': {},
                }
            a = agg_dict[k]
            a['days'].append(d)
            a['total_contract'] += c['national_contract']
            a['total_external'] += c['external_contract']
            a['total_motorone'] += c['motorone_contract']
            a['total_cancelled'] += c['cancelled']
            a['total_delivered'] += c['delivered']
            for mn, cnt in c['model_contracts'].items():
                a['model_contracts'][mn] = a['model_contracts'].get(mn, 0) + cnt

    history = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'version': 'v3',
        'note': '직판제 이후 (4/9~) 기준. G클래스 별도 분리. 차종 중심.',
        'snapshots': daily_snapshots,
        'weekly': sorted(weekly_agg.values(), key=lambda x: x['period_start']),
        'monthly': sorted(monthly_agg.values(), key=lambda x: x['period_start']),
    }

    with open(HISTORY_OUT, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, default=str)

    log(f'\n=== 히스토리 생성 완료 ===')
    log(f'스냅샷: {len(daily_snapshots)}일')
    log(f'주간: {len(weekly_agg)}개 주')
    log(f'월간: {len(monthly_agg)}개 월')
    log(f'출력: {HISTORY_OUT}')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if cmd == 'parse':
        # 특정 날짜 1-2개씩 파싱
        dates = sys.argv[2:] if len(sys.argv) > 2 else None
        parse_all_files(file_subset=dates)
    elif cmd == 'build':
        # 누적된 스냅샷으로 history 빌드
        build_history_v3()
    else:
        # 모두 파싱 + 빌드
        parse_all_files()
        build_history_v3()
