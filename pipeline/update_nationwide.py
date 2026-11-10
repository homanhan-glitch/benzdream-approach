"""Validated HS nationwide adapter. Legacy allocation history is never written.

python pipeline/update_nationwide.py --source-dir C:/Users/user/Downloads
    --state-dir <private directory OUTSIDE repository> --report <private QA json>

Public output contains aggregate counts only. Commit/push only after review of QA.
The first observed snapshot is a baseline, not a day of new contracts.
"""
import argparse
import hashlib
import json
import re
import sys
from io import BytesIO
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
from pathlib import Path
from openpyxl import load_workbook
from parse_contracts import categorize, clean_int_color, CAT_ORDER
from vehicle_identity import commission_id
from render_stock_snapshot import render_snapshot

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = {'가계약 체결', '계약 확정', '결제 완료'}
FIELDS = ['own_new', 'own_cancel', 'national_out', 'national_return', 'own_confirm',
          'contract_row_exit', 'stock_in', 'stock_out', 'first_seen_physical', 'net']
REQUIRED = {'커미션 번호', '모델명', '모델 연도', '외장 색상', '내장 색상',
            '판매 상태', '재고 유형', '차량 상태', '가용 여부', '배정 전시장',
            '데이터 검증', '차량 출고 가능일', '차량 용도', '외장 색상 2 (투톤)'}

def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def text(v):
    return '' if v is None else str(v).strip()

def valid_row(r):
    return not r['issues']

def physical(r):
    return valid_row(r) and r['type'] == '입고 물량' and r['purpose'] not in {'Virtual VIN', 'Pre-Order VIN'}

def saleable(r):
    return (physical(r) and r['sale'] == '미배정' and r['vehicle'] == '판매 가능'
            and r['availability'] == '판매 가능' and r['dealer'] == 'Mercedes Benz Korea'
            and r['purpose'] not in {'전시차', 'MPC 위탁 재고'})

def own_contract(r):
    return physical(r) and r['sale'] in CONTRACT and '효성' in r['dealer']

def modelkey(r):
    return r['cat'] + '|' + r['model']

def load_source(path):
    # Snapshot source bytes and close the workbook even when validation rejects it.
    raw=Path(path).read_bytes()
    with BytesIO(raw) as data:
        wb=load_workbook(data,read_only=True,data_only=True)
        try:
            result=_load_source(path,wb)
            if result[2]['sha256']!=hashlib.sha256(raw).hexdigest() or result[2]['size']!=len(raw):
                raise ValueError('Source changed while being read; retry after download completes')
            return result
        finally:
            wb.close()

def _load_source(path, wb):
    path = Path(path)
    if not {'Sheet1', 'Stock Balance Report'} <= set(wb.sheetnames):
        raise ValueError('Required sheets missing: ' + path.name)
    report = wb['Stock Balance Report']
    report_date = report.cell(2, 2).value
    if isinstance(report_date, datetime):
        day = report_date.date()
    else:
        day = datetime.strptime(str(report_date).strip(), '%d-%b-%y').date()
    match = re.fullmatch(r'전국재고_(\d{4})(?: \(\d+\))?\.xlsx', path.name)
    if not match or match[1] != day.strftime('%m%d'):
        raise ValueError('Filename/report date mismatch: ' + path.name)
    if report.cell(5, 2).value != 'HS HYOSUNG The Class Corp.':
        raise ValueError('Unexpected company scope: ' + path.name)
    iterator = wb['Sheet1'].iter_rows(values_only=True)
    headers = [text(x) for x in next(iterator)]
    if not REQUIRED <= set(headers):
        raise ValueError('Required columns missing: ' + str(REQUIRED - set(headers)))
    rows = {}; types = Counter(); problems = Counter(); sales = Counter()
    for line, values in enumerate(iterator, 2):
        if not any(v is not None and v != '' for v in values):
            continue
        source = dict(zip(headers, values))
        key = commission_id(source['커미션 번호'])
        if not key or key in rows or not re.fullmatch(r'(?:\d{10}|DKR\d+)', key):
            raise ValueError(f'{path.name}: invalid/missing/duplicate commission at row {line}')
        g = lambda name: text(source.get(name))
        model = re.sub(r'\s+', ' ', g('모델명').replace('Mercedes-AMG', 'AMG').replace('Mercedes-Maybach', 'Maybach').replace('Mercedes-Benz ', ''))
        ext = g('외장 색상')
        if g('외장 색상 2 (투톤)') and g('외장 색상 2 (투톤)') != ext:
            ext += ' / ' + g('외장 색상 2 (투톤)')
        year = g('모델 연도').removesuffix('.0')
        issues = []
        if g('데이터 검증') != '유효': issues.append('source_validation')
        if g('재고 유형') not in {'입고 물량', '예정 물량'}: issues.append('stock_type')
        if not model or not re.fullmatch(r'20\d{2}', year) or not g('외장 색상') or not g('내장 색상'): issues.append('model_year_color')
        expected = {'미배정': {'판매 가능', '판매 불가'}, '가계약 체결': {'가계약'}, '계약 확정': {'계약 확정'}, '결제 완료': {'판매 완료'}, '배정 완료': {'판매 가능', '판매 불가'}}
        if g('판매 상태') not in expected or g('차량 상태') not in expected[g('판매 상태')]: issues.append('state_conflict')
        pdd = g('차량 출고 가능일')
        month = pdd[:7] if re.match(r'^20\d{2}-\d{2}-\d{2}', pdd) else 'unknown'
        r = dict(model=model,cat=categorize(model),year=year,ext=ext,interior=clean_int_color(g('내장 색상')),
                 sale=g('판매 상태'),type=g('재고 유형'),vehicle=g('차량 상태'),availability=g('가용 여부'),
                 dealer=g('배정 전시장'),purpose=g('차량 용도'),pdd=month,issues=issues)
        rows[key] = r
        types[r['type'] or '미기재'] += 1; sales[r['sale']] += 1; problems.update(issues)
    # Balance report is another view of the same physical records, never additional stock.
    balance_ids = []
    for values in report.iter_rows(values_only=True):
        if len(values) > 3 and re.fullmatch(r'[A-HJ-NPR-Z0-9]{17}', text(values[0])) and values[3] == 1:
            balance_ids.append(commission_id(values[1]))
    if len(balance_ids) != len(set(balance_ids)) or not set(balance_ids) <= rows.keys():
        raise ValueError('Balance report identity overlap failed: ' + path.name)
    wb.close()
    if not rows: raise ValueError('Empty source')
    meta = dict(file=path.name,size=path.stat().st_size,sha256=digest(path),date=day.isoformat(),
                company='HS HYOSUNG The Class Corp.',rows=len(rows),types=dict(types),sales=dict(sales),
                issues=dict(problems),quarantined=sum(not valid_row(r) for r in rows.values()),
                balance_report_rows=len(balance_ids),balance_report_additional=0,
                missing_commissions=0,duplicate_commissions=0,saleable=sum(saleable(r) for r in rows.values()))
    return day.isoformat(), rows, meta

def transition(prev, cur, outstanding):
    """Physical state changes only; quarantined/present rows cannot become exits.

    An outstanding nationwide disappearance is reversed once on reappearance.
    Contract cancellation/recontract are separate signed events, not unique sales.
    """
    events = defaultdict(Counter)
    def add(r, field): events[modelkey(r)][field] += 1
    for key, r in cur.items():
        if key in outstanding:
            add(outstanding.pop(key), 'national_return')
        p = prev.get(key)
        if not p:
            if physical(r): add(r, 'first_seen_physical')
            # First observation already contracted is not proof of a new contract.
            continue
        if not valid_row(p) or not valid_row(r): continue
        if physical(p) and physical(r):
            if p['sale'] not in CONTRACT and own_contract(r): add(r, 'own_new')
            if own_contract(p) and r['sale'] not in CONTRACT: add(p, 'own_cancel')
            if own_contract(p) and own_contract(r) and p['sale']=='가계약 체결' and r['sale'] in {'계약 확정','결제 완료'}: add(r, 'own_confirm')
    for key, p in prev.items():
        if key not in cur:
            if saleable(p):
                add(p, 'national_out'); outstanding[key] = p
            if own_contract(p): add(p, 'contract_row_exit')
    a = {k for k,r in prev.items() if saleable(r)}
    b = {k for k,r in cur.items() if saleable(r)}
    for k in b-a: add(cur[k], 'stock_in')
    for k in a-b: add(prev[k], 'stock_out')
    for values in events.values():
        values['net'] = values['own_new'] - values['own_cancel'] + values['national_out'] - values['national_return']
    total = {f:sum(v[f] for v in events.values()) for f in FIELDS}
    assert len(a) + total['stock_in'] - total['stock_out'] == len(b)
    # Reconcile the own physical contract scope including source/quality transfers.
    pa = {k for k,r in prev.items() if own_contract(r)}; pb = {k for k,r in cur.items() if own_contract(r)}
    scope_in=Counter(); scope_out=Counter()
    for key in pb-pa:
        p=prev.get(key)
        if p and physical(p) and p['sale'] not in CONTRACT: continue
        reason='first_seen_contracted' if not p else 'quality_restored' if not valid_row(p) else 'planned_to_physical' if not physical(p) else 'company_transfer_in'
        scope_in[reason]+=1
    for key in pa-pb:
        r=cur.get(key)
        if not r or (physical(r) and r['sale'] not in CONTRACT): continue
        reason='quality_quarantine' if not valid_row(r) else 'physical_to_planned' if not physical(r) else 'company_transfer_out'
        scope_out[reason]+=1
    adjustment = sum(scope_in.values())-sum(scope_out.values())
    balance = dict(stock_before=len(a),stock_in=total['stock_in'],stock_out=total['stock_out'],stock_after=len(b),
                   own_before=len(pa),own_after=len(pb),own_scope_adjustment=adjustment,
                   own_new=total['own_new'],own_cancel=total['own_cancel'],own_row_exit=total['contract_row_exit'],
                   scope_in=dict(scope_in),scope_out=dict(scope_out))
    assert len(pa)+total['own_new']-total['own_cancel']-total['contract_row_exit']+adjustment==len(pb)
    return {k:dict(v) for k,v in events.items()}, total, balance

def stock_snapshot(rows, day):
    models = {}
    for r in rows.values():
        if not saleable(r): continue
        m = models.setdefault(r['model'], dict(cat=r['cat'], colors=Counter(),year_groups={},pdd_buckets=Counter(),pdd_total=0))
        color = r['ext']+'|'+r['interior']
        m['colors'][color] += 1
        m['year_groups'].setdefault(r['year'],dict(colors=Counter()))['colors'][color] += 1
        m['pdd_buckets'][r['pdd']] += 1; m['pdd_total'] += 1
    # Independent source projection checks every model/year/exterior/interior, not just the grand total.
    expected = Counter((r['model'],r['year'],r['ext']+'|'+r['interior']) for r in rows.values() if saleable(r))
    actual = Counter({(name,year,color):n for name,m in models.items() for year,g in m['year_groups'].items() for color,n in g['colors'].items()})
    assert expected == actual
    for m in models.values():
        agg = Counter()
        for g in m['year_groups'].values(): agg.update(g['colors'])
        assert agg == m['colors'] and sum(agg.values()) == m['pdd_total'] == sum(m['pdd_buckets'].values())
    return dict(date=day,source_format='hs_nationwide_v1',scope='전국 미배정 입고·판매가능·가용 차량',
                sellable_total=sum(expected.values()),models=models)

def customer_snapshot(rows, day, rules=None):
    """Apply confirmed display corrections without inventing contract transitions."""
    if rules is None:
        path=ROOT/'pipeline/customer_stock_overrides.json'
        rules=json.loads(path.read_text(encoding='utf-8'))['rules'] if path.exists() else []
    active=[r for r in rules if r.get('active') and r['status']=='unavailable']
    def blocked(row):
        return any(row['year']==rule['year'] and re.search(rule['model_pattern'],row['model']) for rule in active)
    result=stock_snapshot({k:r for k,r in rows.items() if not blocked(r)},day)
    result['source_sellable_total']=sum(saleable(r) for r in rows.values())
    result['display_excluded_total']=sum(saleable(r) and blocked(r) for r in rows.values())
    result['availability_overrides']=[{k:r[k] for k in ['id','model_pattern','year','status','confirmed_date','label']} for r in active]
    assert result['source_sellable_total']-result['display_excluded_total']==result['sellable_total']
    return result

def build_web(daily, stock, rows):
    dates = sorted(daily); heat = defaultdict(dict)
    for d in dates:
        for key, counts in daily[d]['models'].items():
            heat[key][d] = [counts.get('own_new',0), counts.get('national_out',0), counts.get('own_cancel',0), counts.get('national_return',0)]
    webrows=[]; yearstock={}
    for name,m in stock['models'].items():
        key=m['cat']+'|'+name
        webrows.append(dict(cat=m['cat'],model=name,stock=sum(m['colors'].values()),combos=m['colors'],pdd=m['pdd_buckets']))
        yearstock[key]={y:dict(stock=sum(g['colors'].values()),combos=g['colors']) for y,g in m['year_groups'].items()}
    def period(days):
        total={f:sum(daily[d][f] for d in days) for f in FIELDS}
        rank=Counter()
        for d in days:
            for k,v in daily[d]['models'].items(): rank[k]+=v.get('net',0)
        prevdates=[d for d in dates if d<days[0]]
        startstock=daily[prevdates[-1]]['sell'] if prevdates else daily[days[0]]['sell']
        return dict(start=days[0],end=days[-1],days=days,ndays=len(days),sell_start=startstock,sell_end=daily[days[-1]]['sell'],
                    sell_delta=daily[days[-1]]['sell']-startstock,**total,
                    top_models=[dict(cat=k.split('|')[0],model=k.split('|')[1],n=n) for k,n in rank.most_common() if n>0])
    grouped={}
    for kind in ['weekly','monthly']:
        groups=defaultdict(list)
        for d in dates:
            dt=date.fromisoformat(d)
            key=(dt-timedelta(days=dt.weekday())).isoformat() if kind=='weekly' else d[:7]+'-01'
            groups[key].append(d)
        grouped[kind]=[period(ds) for ds in groups.values()]
    last=date.fromisoformat(dates[-1])
    recent={k:period([d for d in dates if date.fromisoformat(d)>last-timedelta(days=n)]) for k,n in [('week',7),('month',30)]}
    return dict(schema='hs_nationwide_v1',company_label='효성더클래스',generated_at=datetime.now().isoformat(timespec='seconds'),
                dates=dates,first=dates[0],last=dates[-1],ndays=len(dates),cat_order=CAT_ORDER,rows=webrows,
                daily={d:{k:v for k,v in daily[d].items() if k not in ['models','source']} for d in dates},heat=heat,
                sellable_now=stock['sellable_total'],year_stock=yearstock,recent=recent,**grouped,
                own_open=sum(own_contract(r) for r in rows.values()),
                baseline=dates[0],legacy_url='contracts_web_legacy_20261022.json',
                method='전국 순계약 추정 = 효성 입고 차량의 신규 계약 전환 - 계약 해제 + 전국 판매가능 재고의 원본 이탈 - 이탈 차량 재등장. 계약 확정 건수가 아닙니다. 가상·예정·전시·위탁 차량은 제외하며 처음부터 계약 상태인 차량은 신규계약에 넣지 않습니다.')

def write_json(path, data):
    path=Path(path); path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+'.tmp'); tmp.write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8'); tmp.replace(path)

def run(source_dir, state_dir, report_path):
    state_dir=Path(state_dir).resolve()
    if state_dir.is_relative_to(ROOT): raise ValueError('Commission state must be OUTSIDE public repository')
    state_file=state_dir/'state.json'
    daily_path=ROOT/'pipeline/nationwide_daily.json'
    legacy_paths=[ROOT/'pipeline/contracts_daily.json',ROOT/'pipeline/contracts_state.json.gz']
    legacy_hashes={str(p.relative_to(ROOT)):digest(p) for p in legacy_paths}
    state=json.loads(state_file.read_text(encoding='utf-8')) if state_file.exists() else None
    daily=json.loads(daily_path.read_text(encoding='utf-8')) if daily_path.exists() else {}
    if bool(state)!=bool(daily) or (state and state['date']!=max(daily)):
        raise ValueError('Private state/public daily ledger mismatch; restore verified state before proceeding')
    previous=state['rows'] if state else None; outstanding=state['outstanding'] if state else {}
    metas=[]; sources={}; filepaths=sorted(Path(source_dir).glob('전국재고_*.xlsx'))
    known={v['source']['sha256'] for v in daily.values()}
    for path in filepaths:
        if digest(path) in known: continue
        d, rows, meta=load_source(path)
        if d in sources:
            if meta['sha256']!=sources[d][1]['sha256']: raise ValueError('Conflicting same-day source files')
            continue
        sources[d]=(rows,meta)
    if not sources:
        print(json.dumps({'status':'no_new_source'},ensure_ascii=False)); return
    for d,(rows,meta) in sorted(sources.items()):
        if daily and d<=max(daily): raise ValueError('Historical source correction requires explicit review; no automatic rewrite')
        if previous is None:
            events={}; total={f:0 for f in FIELDS}; balance={'baseline':True}; gap=0
        else:
            events,total,balance=transition(previous,rows,outstanding)
            gap=(date.fromisoformat(d)-date.fromisoformat(max(daily))).days
        stock=stock_snapshot(rows,d)
        assert stock['sellable_total']==meta['saleable']
        daily[d]=dict(**total,sell=stock['sellable_total'],gap=gap,baseline=previous is None,models=events,source=meta,balance=balance)
        meta['balance']=balance; metas.append(meta); previous=rows
    web=build_web(daily,stock,rows)
    assert sum(r['stock'] for r in web['rows'])==stock['sellable_total']
    archive=ROOT/'contracts_web_legacy_20261022.json'
    oldweb=ROOT/'contracts_web.json'
    if not archive.exists():
        old=json.loads(oldweb.read_text(encoding='utf-8'))
        if old.get('schema')=='hs_nationwide_v1': raise ValueError('Legacy archive missing')
        archive.write_bytes(oldweb.read_bytes())
    qa=dict(status='validated',sources=metas,latest=stock['date'],sellable=stock['sellable_total'],
            model_count=len(stock['models']),year_totals=dict(Counter({y:sum(sum(m['year_groups'].get(y,{}).get('colors',{}).values()) for m in stock['models'].values()) for y in sorted({y for m in stock['models'].values() for y in m['year_groups']})})),
            legacy_preserved=legacy_hashes,legacy_web_sha256=digest(archive),commission_missing=0,commission_duplicate=0,
            model_year_color_coverage=True,stock_balance=True,own_contract_balance=True,
            notes=['Stock Balance Report is a duplicate view, not summed','Baseline has zero new contracts','No source identifiers or customer data in public aggregates'])
    # All validations complete before publishing any generated data. Git deploys the set atomically.
    customer=customer_snapshot(rows,stock['date'])
    qa['customer_display_total']=customer['sellable_total']
    qa['customer_display_excluded']=customer['display_excluded_total']
    write_json(daily_path,daily); write_json(ROOT/'latest_stock.json',customer); write_json(oldweb,web)
    render_snapshot(ROOT/'latest_stock.json')
    write_json(state_file,dict(date=stock['date'],rows=rows,outstanding=outstanding))
    write_json(report_path,qa)
    assert legacy_hashes=={str(p.relative_to(ROOT)):digest(p) for p in legacy_paths}
    print(json.dumps(qa,ensure_ascii=False))

if __name__=='__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    p=argparse.ArgumentParser();p.add_argument('--source-dir',required=True);p.add_argument('--state-dir',required=True);p.add_argument('--report',required=True)
    args=p.parse_args();run(args.source_dir,args.state_dir,args.report)
