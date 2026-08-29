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
from parse_inventory_v3 import parse_excel, build_snapshot

fp = sys.argv[1]
out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(os.path.dirname(__file__), '..', 'latest_stock.json')

parsed = parse_excel(fp)
snap = build_snapshot(parsed)

models_out = {}
for name, m in snap['models'].items():
    if m['sellable'] <= 0:
        continue
    colors = {combo: v['total'] for combo, v in m['colors'].items()}
    models_out[name] = {
        'cat': m['cat'],
        'colors': colors,
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

print(f"date={result['date']} sellable_total={result['sellable_total']} models={len(models_out)}")
