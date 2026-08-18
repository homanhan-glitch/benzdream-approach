#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BenzDream 계약·재고 파이프라인 v1  (2026-08-18)

VIN 단위 상태 전이로 일자별·차종별·트림별 계약/소진을 산출한다.

  python3 parse_contracts.py <xlsx> [<xlsx> ...]     # 신규 파일 반영 (append)
  python3 parse_contracts.py --bootstrap <dir>       # 폴더 전체로 처음부터 재구축

산출물
  pipeline/contracts_state.json.gz  전일 VIN 스냅샷 (diff 계산용, 1개만 유지)
  pipeline/contracts_daily.json     일자별 집계 (append-only, 절대 rebuild 금지)
  contracts_web.json                웹 대시보드용 경량 데이터

핵심 정의
  모터원 신규계약 : 전국재고/미배정 → 가계약 체결·계약 확정·결제 완료
  타 파트너 소진  : 전국재고/미배정 VIN 이 파일에서 사라짐 (타 딜러 계약분)
  출고 완료       : 모터원 계약 상태 VIN 이 사라짐
  신규 입고       : 이전 스냅샷에 없던 VIN (본사 재고 오픈)
  ※ 배정 완료(전시차·위탁)는 고객 계약이 아니므로 계약에서 제외
"""
import pandas as pd, json, gzip, os, re, sys, glob, warnings
from collections import defaultdict, Counter
from datetime import datetime, date
warnings.filterwarnings('ignore')

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(HERE, 'contracts_state.json.gz')
DAILY = os.path.join(HERE, 'contracts_daily.json')
WEB   = os.path.join(ROOT, 'contracts_web.json')

CONTRACT = {'가계약 체결', '계약 확정', '결제 완료'}
CAT_ORDER = ['A클래스','CLA','C클래스','E클래스','CLE','S클래스','AMG GT·SL',
             'GLA·GLB','GLC','GLE','GLS','G클래스','전동화 EQ','Maybach','기타']

def categorize(m):
    m = str(m)
    if 'Maybach' in m or 'MAYBACH' in m: return 'Maybach'
    if m.startswith('EQ') or re.search(r'\bEQ[ABES]\b', m): return '전동화 EQ'
    if 'GLS' in m: return 'GLS'
    if 'GLE' in m: return 'GLE'
    if 'GLC' in m: return 'GLC'
    if 'GLA' in m or 'GLB' in m: return 'GLA·GLB'
    if 'AMG G 63' in m or 'G 580' in m or m.startswith('G '): return 'G클래스'
    if 'AMG SL' in m or m.startswith('SL ') or 'AMG GT' in m: return 'AMG GT·SL'
    if m.startswith('S ') or 'AMG S ' in m: return 'S클래스'
    if 'CLE' in m: return 'CLE'
    if m.startswith('E ') or 'AMG E ' in m: return 'E클래스'
    if 'CLA' in m: return 'CLA'
    if m.startswith('C ') or 'AMG C ' in m: return 'C클래스'
    if m.startswith('A ') or 'AMG A ' in m: return 'A클래스'
    return '기타'

def clean_int_color(s):
    s = str(s).strip()
    for p in ['MAYBACH 익스클루시브 나파 가죽,','MANUFAKTUR 익스클루시브 나파 가죽,',
              'MANUFAKTUR 나파 가죽,','AMG 나파 가죽,','나파 가죽,','아티코 인조 가죽,',
              '아티코 가죽 / 마이크로컷 마이크로파이버 ','아티코 가죽/다이나미카 ',
              '아티코 가죽,','가죽,']:
        if s.startswith(p):
            s = s[len(p):].strip()
            if p == '아티코 가죽/다이나미카 ': s = '다이나미카 ' + s
            break
    if 'ARTICO' in s or 'man-made' in s: s = '블랙 인조가죽'
    return s.strip(' ,') or '기타'

def pdd_month(v):
    if pd.isna(v): return None
    try: return pd.to_datetime(v).strftime('%Y-%m')
    except Exception: return None

def date_of(path):
    m = re.search(r'(20\d{2})[-_.]?(\d{2})[-_.]?(\d{2})', os.path.basename(path))
    return f'{m.group(1)}-{m.group(2)}-{m.group(3)}' if m else None

def load(path):
    """xlsx → {vin: [state, grp, sr, model, cat, ext, intr, itype, pddm]}"""
    df = pd.read_excel(path, sheet_name='allocation')
    df.columns = [str(c).replace('\n', ' ').strip() for c in df.columns]
    df = df[df['차대 번호'].notna()].drop_duplicates('차대 번호')
    out = {}
    for r in df.itertuples(index=False):
        g = lambda c, d='': getattr(r, c, d)
        d_ = dict(zip(df.columns, r))
        model = str(d_.get('모델명', '')).strip()
        out[str(d_['차대 번호']).strip()] = [
            d_.get('판매 상태') if pd.notna(d_.get('판매 상태')) else '미배정',
            d_.get('재고구분') if pd.notna(d_.get('재고구분')) else '전국재고',
            (d_.get('배정 전시장') if pd.notna(d_.get('배정 전시장')) else ''),
            model, categorize(model),
            (str(d_.get('외장 색상')).strip() if pd.notna(d_.get('외장 색상')) else '기타'),
            clean_int_color(d_.get('내장 색상')) if pd.notna(d_.get('내장 색상')) else '기타',
            d_.get('재고 유형') if pd.notna(d_.get('재고 유형')) else '입고 물량',
            pdd_month(d_.get('차량 출고 가능일(PDD)')),
        ]
    return out

S_STATE, S_GRP, S_SR, S_MODEL, S_CAT, S_EXT, S_INT, S_ITYPE, S_PDD = range(9)

def diff(prev, cur, d, pd_):
    """전일→금일 이벤트 산출"""
    agg = defaultdict(Counter)
    srd = Counter(); srm = Counter(); cdem = defaultdict(Counter)
    for vin, r in cur.items():
        p = prev.get(vin)
        k = f'{r[S_CAT]}|{r[S_MODEL]}'
        now_c = r[S_STATE] in CONTRACT
        if p is None:
            agg[k]['new_stock'] += 1
            if now_c:
                agg[k]['mo_new'] += 1
                srd[r[S_SR] or '미지정'] += 1; srm[(r[S_SR] or '미지정', r[S_CAT])] += 1
                cdem[k][f'{r[S_EXT]}|{r[S_INT]}'] += 1
            continue
        was_c = p[S_STATE] in CONTRACT
        if not was_c and now_c:
            agg[k]['mo_new'] += 1
            srd[r[S_SR] or '미지정'] += 1; srm[(r[S_SR] or '미지정', r[S_CAT])] += 1
            cdem[k][f'{r[S_EXT]}|{r[S_INT]}'] += 1
        elif was_c and not now_c:
            agg[k]['mo_cancel'] += 1
        elif was_c and now_c and p[S_STATE] == '가계약 체결' and r[S_STATE] in ('계약 확정', '결제 완료'):
            agg[k]['mo_confirm'] += 1
    for vin, p in prev.items():
        if vin in cur: continue
        k = f'{p[S_CAT]}|{p[S_MODEL]}'
        if p[S_STATE] in CONTRACT:
            agg[k]['mo_delivered'] += 1
        elif p[S_STATE] == '미배정' and p[S_ITYPE] == '입고 물량':
            agg[k]['nat_other'] += 1
            cdem[k][f'{p[S_EXT]}|{p[S_INT]}'] += 1
        else:
            agg[k]['other_out'] += 1
    gap = (date(*map(int, d.split('-'))) - date(*map(int, pd_.split('-')))).days
    sell = sum(1 for r in cur.values()
               if r[S_ITYPE] == '입고 물량' and r[S_STATE] == '미배정' and r[S_GRP] == '전국재고')
    return dict(
        gap=gap, prev=pd_, sell=sell,
        models={k: dict(v) for k, v in agg.items()},
        sr={k: v for k, v in srd.items()},
        sr_model={f'{a}|{b}': v for (a, b), v in srm.items()},
        color={k: dict(v) for k, v in cdem.items()},
    )

def snapshot_stock(cur):
    st = {}
    for r in cur.values():
        if not (r[S_ITYPE] == '입고 물량' and r[S_STATE] == '미배정' and r[S_GRP] == '전국재고'):
            continue
        k = f'{r[S_CAT]}|{r[S_MODEL]}'
        e = st.setdefault(k, dict(total=0, combos=Counter(), pdd=Counter()))
        e['total'] += 1; e['combos'][f'{r[S_EXT]}|{r[S_INT]}'] += 1
        if r[S_PDD]: e['pdd'][r[S_PDD]] += 1
    return {k: dict(total=v['total'], combos=dict(v['combos']), pdd=dict(v['pdd']))
            for k, v in st.items()}

def build_web(store, last_cur):
    daily = store['daily']
    dates = sorted(daily)
    ndays = sum(daily[d]['gap'] for d in dates) or 1
    stock = snapshot_stock(last_cur)
    keys = sorted(set(stock) | {k for d in dates for k in daily[d]['models']})

    rows, heat = [], {}
    for k in keys:
        cat, model = k.split('|', 1)
        a = Counter()
        for d in dates:
            m = daily[d]['models'].get(k)
            if not m: continue
            a.update(m)
            if m.get('mo_new') or m.get('nat_other'):
                heat.setdefault(k, {})[d] = [m.get('mo_new', 0), m.get('nat_other', 0)]
        st = stock.get(k, dict(total=0, combos={}, pdd={}))
        dem = a['mo_new'] + a['nat_other']
        vel = dem / ndays
        dos = st['total'] / vel if vel > 0.05 else None
        rows.append(dict(
            cat=cat, model=model, mo_new=a['mo_new'], mo_cancel=a['mo_cancel'],
            mo_confirm=a['mo_confirm'], mo_deliv=a['mo_delivered'], nat=a['nat_other'],
            new_stock=a['new_stock'], stock=st['total'], pdd=st['pdd'],
            combos=dict(sorted(st['combos'].items(), key=lambda x: -x[1])[:14]),
            vel=round(vel, 2), dos=(round(dos, 1) if dos is not None and dos < 999 else None),
            share=(round(100 * a['mo_new'] / dem, 1) if dem else None)))

    sr_daily, sr_model, color_dem = defaultdict(dict), defaultdict(Counter), defaultdict(Counter)
    for d in dates:
        for sr, n in daily[d].get('sr', {}).items(): sr_daily[sr][d] = n
        for kk, n in daily[d].get('sr_model', {}).items():
            sr, c = kk.split('|', 1); sr_model[sr][c] += n
        for k, cc in daily[d].get('color', {}).items(): color_dem[k].update(cc)

    web = dict(
        generated_at=datetime.now().strftime('%Y-%m-%d %H:%M'),
        dates=dates, first=store.get('first', dates[0]), last=dates[-1],
        ndays=ndays, cat_order=CAT_ORDER, rows=rows, heat=heat,
        daily={d: dict(gap=daily[d]['gap'], sell=daily[d]['sell'],
                       **{x: sum(m.get(x, 0) for m in daily[d]['models'].values())
                          for x in ['mo_new','mo_confirm','mo_cancel','mo_delivered','nat_other','new_stock']})
               for d in dates},
        sr_daily={k: v for k, v in sr_daily.items()},
        sr_model={k: dict(v) for k, v in sr_model.items()},
        color_dem={k: dict(v.most_common(14)) for k, v in color_dem.items()},
        mo_open=sum(1 for r in last_cur.values() if r[S_STATE] in CONTRACT),
        mo_by_sr=dict(Counter(r[S_SR] for r in last_cur.values()
                              if r[S_STATE] in CONTRACT and r[S_SR])),
        sellable_now=sum(v['total'] for v in stock.values()),
    )
    json.dump(web, open(WEB, 'w'), ensure_ascii=False, separators=(',', ':'))
    return web

def main():
    args = sys.argv[1:]
    if not args:
        print(__doc__); sys.exit(1)

    if args[0] == '--bootstrap':
        files = sorted(glob.glob(os.path.join(args[1], '*.xlsx')))
        store = dict(daily={}, first=None)
        prev = prev_d = None
    else:
        files = sorted(args, key=lambda f: date_of(f) or '')
        store = json.load(open(DAILY)) if os.path.exists(DAILY) else dict(daily={}, first=None)
        prev, prev_d = None, store.get('last_date')
        if os.path.exists(STATE):
            with gzip.open(STATE, 'rt', encoding='utf-8') as fh:
                s = json.load(fh); prev, prev_d = s['vins'], s['date']

    cur = None
    for f in files:
        d = date_of(f)
        if not d:
            print('  skip (날짜 없음):', os.path.basename(f)); continue
        if d in store['daily'] or (prev_d and d <= prev_d):
            print('  skip (이미 반영):', d); continue
        cur = load(f)
        if prev is None:
            store['first'] = d
            print(f'  기준 스냅샷 {d}  VIN {len(cur)}')
        else:
            store['daily'][d] = diff(prev, cur, d, prev_d)
            t = store['daily'][d]
            n = sum(m.get('mo_new', 0) for m in t['models'].values())
            o = sum(m.get('nat_other', 0) for m in t['models'].values())
            print(f'  {d}  판매가능 {t["sell"]:>5}  모터원 +{n:<3} 타파트너 {o:<4} (gap {t["gap"]}일)')
        prev, prev_d = cur, d

    if cur is None:
        print('반영할 신규 파일이 없습니다.'); 
        if os.path.exists(STATE) and os.path.exists(DAILY):
            with gzip.open(STATE, 'rt', encoding='utf-8') as fh: cur = json.load(fh)['vins']
            build_web(json.load(open(DAILY)), cur); print('웹 데이터만 재생성 완료.')
        return

    store['last_date'] = prev_d
    json.dump(store, open(DAILY, 'w'), ensure_ascii=False, separators=(',', ':'))
    with gzip.open(STATE, 'wt', encoding='utf-8') as fh:
        json.dump(dict(date=prev_d, vins=prev), fh, ensure_ascii=False, separators=(',', ':'))
    w = build_web(store, prev)
    print(f'\n완료: {w["first"]} ~ {w["last"]} · 영업일 {w["ndays"]}일 · 트림 {len(w["rows"])}개')
    print(f'      판매가능 {w["sellable_now"]:,}대 · 미출고 계약 {w["mo_open"]}건 · {w["mo_by_sr"]}')

if __name__ == '__main__':
    main()
