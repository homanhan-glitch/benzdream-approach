"""Render the public fallback from the same stock JSON used by the browser."""
import json
import re
from datetime import date
from html import escape
from pathlib import Path

START = '<!-- STOCK SNAPSHOT START -->'
END = '<!-- STOCK SNAPSHOT END -->'

def render_snapshot(stock_path, page_path=None):
    stock_path = Path(stock_path)
    page_path = Path(page_path) if page_path else stock_path.with_name('BenzDream_Stock.html')
    data = json.loads(stock_path.read_text(encoding='utf-8'))
    stamp = data['date']
    if date.fromisoformat(stamp).isoformat() != stamp or not isinstance(data['models'], dict):
        raise ValueError('Invalid stock date/models; do not publish')
    rows = []
    for name, model in data['models'].items():
        colors = model['colors']
        if not isinstance(colors, dict):
            raise ValueError('Invalid stock colors; do not publish')
        names = [escape(k.replace('|', ' / ')) for k in colors]
        rows.append('<li><strong>' + escape(name) + '</strong><br>' + ' · '.join(names) + '</li>')
    block = START + '\n<section id="stockSnapshot" data-date="' + stamp + '">\n'
    block += '<details><summary>' + stamp + ' 기준 차종·색상 목록</summary><p>재고는 변동될 수 있습니다. 현재 배정 가능 여부는 상담으로 확인해 주세요.</p><ul>'
    block += ''.join(rows) + '</ul></details></section>\n' + END
    page = page_path.read_text(encoding='utf-8')
    if START not in page or END not in page:
        raise ValueError('Stock snapshot markers missing; do not publish')
    page = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: block, page, flags=re.S)
    page, count = re.subn(r'(<div\b[^>]*\bid="updatedBadge"[^>]*>).*?(</div>)', lambda m: m[1] + '재고 기준일 ' + stamp + m[2], page, count=1, flags=re.S)
    if count != 1:
        raise ValueError('Stock date element missing; do not publish')
    page_path.write_text(page, encoding='utf-8')
    return stamp

if __name__ == '__main__':
    import sys
    print(render_snapshot(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None))
