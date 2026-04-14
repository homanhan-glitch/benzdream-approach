"""
Aggregate daily snapshots into history.json with day-over-day diffs.

history.json schema:
{
  "generated_at": "ISO8601",
  "dates": ["2026-04-10", "2026-04-14", ...],
  "snapshots": [
    {
      "date": "...",
      "sellable_total": int,
      "assigned_total": int,
      # day-over-day (null on first day)
      "national_contract": int,  # prev.sellable VINs that left sellable pool (전국계약)
      "national_cancel": int,    # VINs in curr.sellable that were previously disappeared (타사해약복귀)
      "motorone_contract": int,  # prev.sellable ∩ curr.assigned (전국→배정)
      "motorone_cancel": int,    # prev.assigned ∩ curr.sellable (배정→전국)
      "motorone_delivered": int, # prev.assigned, gone entirely (배정→출고완료)
      "new_in": int,             # curr.sellable not seen in prev.all
      # per model
      "model_contracts": {canon: int},   # national contracts by model
      "model_motorone": {canon: int},    # motorone contracts by model
      "models": {canon: {cat, sellable, assigned}},  # current state
    }
  ]
}

Additionally maintains `all_seen_vins` cumulative across history for national_cancel tracking.
"""
import json, os
from pathlib import Path
from datetime import datetime

SNAP_DIR = Path(__file__).parent / "snapshots"
REPO = Path(__file__).parent.parent
OUT = REPO / "inventory_history.json"
OUT_STOCK = REPO / "latest_stock.json"

def load_snapshots():
    files = sorted(SNAP_DIR.glob("*.json"))
    snaps = []
    for f in files:
        snaps.append(json.load(open(f, encoding='utf-8')))
    return snaps

def build():
    snaps = load_snapshots()
    if not snaps:
        raise SystemExit("no snapshots")

    cumulative_seen = set()       # all VINs ever observed (sellable or assigned)
    cumulative_disappeared = set()# VINs that have left sellable pool at some prior point
    history = []
    prev = None

    for s in snaps:
        date = s['date']
        sellable = set(s['sellable_vins'])
        assigned = set(s['assigned_vins'])
        all_today = sellable | assigned

        entry = {
            "date": date,
            "sellable_total": s['sellable_total'],
            "assigned_total": s['assigned_total'],
            "national_contract": None,
            "national_cancel": None,
            "motorone_contract": None,
            "motorone_cancel": None,
            "motorone_delivered": None,
            "new_in": None,
            "model_contracts": {},
            "model_motorone": {},
            "models": {mn: {"cat":d["cat"],"sellable":d["sellable"],"assigned":d["assigned"]} for mn,d in s['models'].items()},
        }

        if prev is not None:
            prev_sellable = set(prev['sellable_vins'])
            prev_assigned = set(prev['assigned_vins'])
            prev_all = prev_sellable | prev_assigned

            # National contract = prev sellable VINs no longer in sellable pool today
            left_sellable = prev_sellable - sellable
            entry['national_contract'] = len(left_sellable)

            # Of those, how many moved into assigned (motorone contract)
            mt_contract_vins = left_sellable & assigned
            entry['motorone_contract'] = len(mt_contract_vins)

            # Motorone cancel = prev assigned → now sellable
            mt_cancel_vins = prev_assigned & sellable
            entry['motorone_cancel'] = len(mt_cancel_vins)

            # Motorone delivered = prev assigned, gone entirely
            entry['motorone_delivered'] = len(prev_assigned - all_today)

            # New sellable = in current sellable, not in prev's combined set (truly new VIN)
            fresh_vins = sellable - prev_all
            # National cancel = in current sellable, was previously disappeared (but not new)
            returned = (sellable - prev_sellable) & cumulative_disappeared - fresh_vins
            entry['national_cancel'] = len(returned)
            entry['new_in'] = len(fresh_vins - cumulative_seen)  # truly never seen

            # Per-model contracts (national + motorone breakdown)
            prev_vin_to_model = prev.get('vin_model', {})

            from collections import Counter
            nc_by_model = Counter()
            mt_by_model = Counter()
            for v in left_sellable:
                m = prev_vin_to_model.get(v, "기타")
                nc_by_model[m] += 1
            for v in mt_contract_vins:
                m = prev_vin_to_model.get(v, "기타")
                mt_by_model[m] += 1
            entry['model_contracts'] = dict(nc_by_model)
            entry['model_motorone'] = dict(mt_by_model)

            # Update cumulative disappeared: add any VINs that left the system or sellable pool
            cumulative_disappeared |= left_sellable
            # Remove VINs that came back to sellable
            cumulative_disappeared -= sellable

        # Update cumulative seen
        cumulative_seen |= all_today

        history.append(entry)
        prev = s

    # Latest motorone (assigned) details for drilldown
    latest_snap = snaps[-1]
    latest_assigned = latest_snap.get('assigned_details', {})

    out = {
        "generated_at": datetime.now().isoformat(timespec='seconds'),
        "dates": [e['date'] for e in history],
        "snapshots": history,
        "latest_assigned": latest_assigned,
    }
    with open(OUT, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)
    print(f"✓ saved {OUT}")

    # Latest stock (with colors) for customer page
    latest = snaps[-1]
    stock = {
        "date": latest['date'],
        "sellable_total": latest['sellable_total'],
        "models": {mn: {"cat":d["cat"],"sellable":d["sellable"],"colors":d["colors"]}
                   for mn,d in latest['models'].items() if d["sellable"] > 0},
    }
    with open(OUT_STOCK, 'w', encoding='utf-8') as f:
        json.dump(stock, f, ensure_ascii=False, indent=2)
    print(f"✓ saved {OUT_STOCK}  ({len(stock['models'])} sellable models)")
    for e in history:
        print(f"  {e['date']}: sellable={e['sellable_total']}, assigned={e['assigned_total']}, "
              f"nat_contract={e['national_contract']}, mt_contract={e['motorone_contract']}, "
              f"mt_cancel={e['motorone_cancel']}, new={e['new_in']}")

if __name__ == "__main__":
    build()
