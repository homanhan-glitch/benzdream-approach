/* A readable mobile view derived from the same table, never separate vehicle data. */
(() => {
  'use strict';
  const clean = el => (el?.textContent || '').replace(/\s+/g, ' ').trim();
  const make = (tag, cls, text) => { const n = document.createElement(tag); n.className = cls; if (text) n.textContent = text; return n; };
  function convert(root = document) {
    root.querySelectorAll('.table-scroll > table').forEach(table => {
      const wrap = table.parentElement;
      if (wrap.nextElementSibling?.classList.contains('mobile-table-view')) wrap.nextElementSibling.remove();
      let headers = [...table.querySelectorAll('thead tr:last-child > th')].slice(1).map(clean);
      const rows = [...table.querySelectorAll('tbody > tr')];
      if (!headers.length && /^(항목|사양|비교 항목)$/.test(clean(rows[0]?.firstElementChild))) {
        headers = [...rows.shift().children].slice(1).map(clean);
      }
      if (!headers.length) return; // Never guess the model attached to an unlabeled column.
      const mobile = make('div', 'mobile-table-view');
      mobile.setAttribute('aria-label', clean(table.caption) || '차량별 항목 비교');
      if (table.caption) mobile.append(make('p', 'mobile-table-caption', clean(table.caption)));
      rows.forEach(row => {
        const cells = [...row.children], label = cells.shift();
        const card = make('section', 'mobile-data-row ' + row.className);
        const title = label.cloneNode(true); title.querySelectorAll('.difference-label').forEach(n => n.remove());
        const h = make('h4', 'mobile-data-label', clean(title));
        if (row.classList.contains('is-different')) h.append(make('span', 'mobile-difference', '차이'));
        card.append(h);
        const dl = make('dl', 'mobile-data-values');
        cells.forEach((cell, i) => {
          const item = make('div', 'mobile-data-value');
          item.append(make('dt', '', headers[i] || '추가 안내'), make('dd', '', clean(cell) || '—'));
          dl.append(item);
        });
        card.append(dl); mobile.append(card);
      });
      wrap.classList.add('has-mobile-view'); wrap.after(mobile);
    });
    filterComparison();
  }
  function filterComparison() {
    const field = document.getElementById('comparison-query');
    if (!field) return;
    const q = field.value.trim().toLocaleLowerCase();
    const root = document.getElementById('customer-option-table');
    root?.querySelectorAll('tbody tr, .mobile-data-row').forEach(row => {
      row.hidden = !!q && !clean(row).toLocaleLowerCase().includes(q);
    });
    const n = [...(root?.querySelectorAll('tbody tr') || [])].filter(row => !row.hidden).length;
    document.getElementById('comparison-query-result').textContent = q ? `${n}개 항목` : '';
    document.getElementById('comparison-empty').hidden = !q || n > 0;
  }
  const comparison = document.getElementById('customer-option-table');
  if (comparison) {
    const label = make('label', 'search-label comparison-search', '비교 항목 찾기'); label.htmlFor = 'comparison-query';
    const input = make('input', ''); input.id = 'comparison-query'; input.type = 'search'; input.placeholder = '예: 시트, 주차, 헤드업';
    label.append(input); comparison.before(label);
    const result = make('p', 'small'); result.id = 'comparison-query-result'; result.setAttribute('role','status'); label.after(result);
    const empty = make('p', 'notice', '일치하는 항목이 없습니다. 검색어를 지우거나 다른 항목을 입력해 주세요.'); empty.id='comparison-empty'; empty.hidden=true; comparison.after(empty);
    input.addEventListener('input',filterComparison);
    const settings=make('details','comparison-settings');
    settings.append(make('summary','','비교 차량 변경 · 차이만 보기 · 검색'));
    comparison.before(settings);
    for(const node of [document.querySelector('.compare-pickers'),document.querySelector('.compare-tools'),label,result])if(node)settings.append(node);
    const mobileQuery=matchMedia('(max-width:760px)');
    settings.open=!mobileQuery.matches;
    mobileQuery.addEventListener('change',e=>settings.open=!e.matches);
    new MutationObserver(records => {
      if (records.some(r => [...r.addedNodes].some(n => n.nodeType === 1 && (n.matches('table,.table-scroll') || n.querySelector('table'))))) convert(comparison);
    }).observe(comparison,{childList:true,subtree:true});
  }
  const specPicker = document.getElementById('spec-reference-model');
  if(specPicker) {
    const showSpec = () => document.querySelectorAll('#spec-reference .reference-model').forEach(n => n.hidden=n.id!==specPicker.value);
    specPicker.addEventListener('change',showSpec); showSpec();
  }
  convert();
})();
