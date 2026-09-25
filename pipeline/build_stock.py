#!/usr/bin/env python3
"""latest_stock.json 생성 — parse_inventory_v3.build_snapshot() 결과를
BenzDream_Stock.html이 기대하는 스키마로 변환.

스키마 (기존 08-25 latest_stock.json과 동일):
{
  "date": "YYYY-MM-DD",
  "sellable_total": N,
  "models": {
    "모델명": {
      "cat": "카테고리",
      "colors": {"외장|내장": count, ...},
      "year_groups": {"2026": {"colors": {"외장|내장": count}}, ...},
      "pdd_buckets": {"YYYY-MM": count, ...},
      "pdd_total": N
    }
  }
}
G클래스는 build_snapshot()이 이미 별도 분리하므로 자동 제외됨.
Virtual VIN은 car_status가 '판매 가능'이 되지 않으므로 자동 제외됨.
"""
import sys, json
import os; sys.path.insert(0, os.path.dirname(__file__))
from collections import Counter
from parse_inventory_v3 import parse_excel, build_snapshot, is_g_class
from vehicle_identity import commission_id


def validate_source_coverage(parsed, snap):
    """Fail before publishing when a commission or color combination is omitted."""
    seen = set()
    expected_ids = []
    expected_combos = Counter()
    expected_year_combos = Counter()
    for row in parsed['rows']:
        key = commission_id(row['com'])
        if not key:
            raise ValueError('Missing commission number')
        if key in seen:
            # allocation is parsed first; a later consign row is the same vehicle.
            if row['source'] == 'allocation':
                raise ValueError(f'Duplicate allocation commission number: {key}')
            continue
        seen.add(key)
        if row['car_status'] == '판매 가능' and not is_g_class(row['model']):
            expected_ids.append(key)
            expected_combos[(row['model'], row['ext_color'], row['int_color'])] += 1
            expected_year_combos[(row['model'], row.get('model_year') or 'unknown', row['ext_color'], row['int_color'])] += 1

    actual_ids = snap.get('sellable_commissions', [])
    if Counter(actual_ids) != Counter(expected_ids):
        raise ValueError('Sellable commission coverage mismatch')

    actual_combos = Counter()
    for model, data in snap['models'].items():
        for combo, value in data['colors'].items():
            ext, interior = combo.split('|', 1)
            actual_combos[(model, ext, interior)] += value['total']
    if actual_combos != expected_combos:
        raise ValueError('Sellable model/color coverage mismatch')
    if sum(actual_combos.values()) != snap['sellable_total']:
        raise ValueError('Sellable total mismatch')

    actual_year_combos = Counter()
    for model, data in snap['models'].items():
        for year, colors in data.get('sellable_years', {}).items():
            for combo, count in colors.items():
                ext, interior = combo.split('|', 1)
                actual_year_combos[(model, year, ext, interior)] += count
    if actual_year_combos != expected_year_combos:
        raise ValueError('Sellable model/year/color coverage mismatch')

def main():
    fp = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'latest_stock.json')

    parsed = parse_excel(fp)
    snap = build_snapshot(parsed)
    validate_source_coverage(parsed, snap)

    models_out = {}
    for name, m in snap['models'].items():
        if m['sellable'] <= 0:
            continue
        colors = {combo: v['total'] for combo, v in m['colors'].items()}
        models_out[name] = {
            'cat': m['cat'],
            'colors': colors,
            'year_groups': {
                year: {'colors': dict(sorted(year_colors.items()))}
                for year, year_colors in sorted(m.get('sellable_years', {}).items())
            },
            'pdd_buckets': m['sellable_pdd'],
            'pdd_total': m['sellable'],
        }

    result = {
        'date': snap['date'],
        'sellable_total': snap['sellable_total'],
        'models': models_out,
    }

    with open(out, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False)

    # Keep crawler-readable HTML and the browser JSON on the same source date.
    from render_stock_snapshot import render_snapshot
    render_snapshot(out)

    print(f"date={result['date']} sellable_total={result['sellable_total']} models={len(models_out)}")


if __name__ == '__main__':
    main()
