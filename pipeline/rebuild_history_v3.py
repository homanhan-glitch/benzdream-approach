#!/usr/bin/env python3
"""rebuild_history_v3.py — v3 새 구조 빌드 (전국 계약 = 사라진 VIN)."""

import sys, os, re, json, glob
from pathlib import Path
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(__file__))
from parse_inventory_v3 import parse_excel, build_snapshot, is_g_class, categorize


SOURCE_DIR = '/sessions/fervent-gracious-brahmagupta/mnt/재고표 코워크 작업 폴더'
OUT_DIR = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/v3_snapshots'
PROGRESS = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/rebuild_progress.txt'
HISTORY_OUT = '/sessions/fervent-gracious-brahmagupta/mnt/outputs/inventory_history_v3.json'

os.makedirs(OUT_DIR, exist_ok=True)

OUTLIER_DATES = ['2026-04-16', '2026-04-22']


def log(msg):
    with open(PROGRESS, 'a') as f:
        f.write(f'[{datetime.now().strftime("%H:%M:%S")}] {msg}\n')
    print(msg, flush=True)


def find_files():
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
    files = find_files()
    if file_subset:
        files = [f for f in files if f[0] in file_subset]
    log(f'대상 파일 {len(files)}개')
    for date, fp, sz in files:
        if date in OUTLIER_DATES:
            log(f'  이상치 스킵: {date}  ({sz//1024}KB)')
            continue
        parse_one(date, fp)


def compare_snapshots(prev_vins, curr_vins):
    """전국 계약 = 사라진 VIN (G외). 모터원 visible = 미배정→배정 변화."""
    prev_set = set(prev_vins.keys())
    curr_set = set(curr_vins.keys())

    new_actual = new_virtual = new_g = 0
    for v in curr_set - prev_set:
        cm = curr_vins[v]
        if cm.get('is_g'):
            new_g += 1
        elif cm.get('is_virtual'):
            new_virtual += 1
        else:
            new_actual += 1

    # 사라진 VIN = 전국 계약
    national_contract = 0
    g_contracts = 0
    model_contracts = {}
    for v in prev_set - curr_set:
        pm = prev_vins[v]
        if pm.get('is_g'):
            g_contracts += 1
        else:
            national_contract += 1
            mn = pm.get('model', '')
            if mn:
                model_contracts[mn] = model_contracts.get(mn, 0) + 1

    # 모터원 visible (미배정→배정)
    motorone_contract = 0
    motorone_contract_g = 0
    motorone_model_contracts = {}
    cancelled = 0
    for v in prev_set & curr_set:
        pm, cm = prev_vins[v], curr_vins[v]
        was_un = pm.get('sale_status') in ('미배정', None, '')
        now_assigned = cm.get('sale_status') in ('가계약', '계약 확정', '배정')
        if was_un and now_assigned:
            if cm.get('is_g'):
                motorone_contract_g += 1
            else:
                motorone_contract += 1
                mn = cm.get('model', '')
                if mn:
                    motorone_model_contracts[mn] = motorone_model_contracts.get(mn, 0) + 1
        elif (not was_un) and (cm.get('sale_status') in ('미배정', None, '')):
            cancelled += 1

    external_contract = max(0, national_contract - motorone_contract)

    return {
        'national_contract': national_contract,
        'g_contracts': g_contracts,
        'motorone_contract': motorone_contract,
        'motorone_contract_g': motorone_contract_g,
        'external_contract': external_contract,
        'cancelled': cancelled,
        'new_actual': new_actual,
        'new_virtual': new_virtual,
        'new_g': new_g,
        'model_contracts': model_contracts,
        'motorone_model_contracts': motorone_model_contracts,
    }


def build_history_v3():
    snap_files = sorted(glob.glob(f'{OUT_DIR}/*_snap.json'))
    vin_files = {Path(f).stem.replace('_vins',''): f for f in glob.glob(f'{OUT_DIR}/*_vins.json')}

    daily_snapshots = []
    prev_vins = None

    for sf in snap_files:
        date = Path(sf).stem.replace('_snap','')
        with open(sf, 'r', encoding='utf-8') as f:
            snap = json.load(f)
        vin_path = vin_files.get(date)
        curr_vins = {}
        if vin_path:
            with open(vin_path, 'r', encoding='utf-8') as f:
                curr_vins = json.load(f)

        compare = None
        if prev_vins:
            compare = compare_snapshots(prev_vins, curr_vins)

        entry = {
            'date': date,
            'total_records': snap['total_records'],
            'sellable_total': snap['sellable_total'],
            'virtual_total': snap['virtual_total'],
            'actual_total': snap['actual_total'],
            'models': snap['models'],
            'g_class': snap.get('g_class', {}),
            'compare': compare,
        }
        daily_snapshots.append(entry)
        prev_vins = curr_vins

    def week_start(d):
        dd = datetime.strptime(d, '%Y-%m-%d')
        return (dd - timedelta(days=dd.weekday())).strftime('%Y-%m-%d')

    def month_start(d):
        return datetime.strptime(d, '%Y-%m-%d').replace(day=1).strftime('%Y-%m-%d')

    weekly_agg = {}
    monthly_agg = {}
    for s in daily_snapshots:
        if not s.get('compare'): continue
        c = s['compare']
        d = s['date']
        for agg, k in [(weekly_agg, week_start(d)), (monthly_agg, month_start(d))]:
            if k not in agg:
                agg[k] = {'period_start': k, 'days': [], 'total_contract': 0,
                         'total_external': 0, 'total_motorone': 0, 'total_cancelled': 0,
                         'total_new_actual': 0, 'total_new_virtual': 0,
                         'model_contracts': {}, 'motorone_model_contracts': {}}
            a = agg[k]
            a['days'].append(d)
            a['total_contract'] += c['national_contract']
            a['total_external'] += c['external_contract']
            a['total_motorone'] += c['motorone_contract']
            a['total_cancelled'] += c['cancelled']
            a['total_new_actual'] += c.get('new_actual', 0)
            a['total_new_virtual'] += c.get('new_virtual', 0)
            for mn, cnt in c['model_contracts'].items():
                a['model_contracts'][mn] = a['model_contracts'].get(mn, 0) + cnt
            for mn, cnt in c.get('motorone_model_contracts', {}).items():
                a['motorone_model_contracts'][mn] = a['motorone_model_contracts'].get(mn, 0) + cnt

    history = {
        'generated_at': datetime.now().isoformat(timespec='seconds'),
        'version': 'v3.1',
        'note': '직판제 이후 (4/9~). G클래스 별도. 전국계약=사라진VIN(G외). 모터원=미배정→배정 visible.',
        'snapshots': daily_snapshots,
        'weekly': sorted(weekly_agg.values(), key=lambda x: x['period_start']),
        'monthly': sorted(monthly_agg.values(), key=lambda x: x['period_start']),
    }

    with open(HISTORY_OUT, 'w', encoding='utf-8') as f:
        json.dump(history, f, ensure_ascii=False, default=str)

    log(f'\n=== 히스토리 생성 완료 ===')
    log(f'스냅샷: {len(daily_snapshots)}일 / 주간: {len(weekly_agg)}개 / 월간: {len(monthly_agg)}개')


if __name__ == '__main__':
    cmd = sys.argv[1] if len(sys.argv) > 1 else 'all'
    if cmd == 'parse':
        dates = sys.argv[2:] if len(sys.argv) > 2 else None
        parse_all_files(file_subset=dates)
    elif cmd == 'build':
        build_history_v3()
    else:
        parse_all_files()
        build_history_v3()
