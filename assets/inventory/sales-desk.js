/* Aggregate-only sales desk. New-company and legacy histories never mix. */
(async () => {
  'use strict';
  const root=document.getElementById('bd-sales-desk'), $=id=>root.querySelector('#'+id);
  const fmt=n=>Number(n||0).toLocaleString('ko-KR');
  const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const legacy=new URLSearchParams(location.search).get('history')==='motorone';
  $('bd-source').value=legacy?'legacy':'current';
  $('bd-source').onchange=e=>{location.href='BenzDream_Inventory.html'+(e.target.value==='legacy'?'?history=motorone':'')};
  const response=await fetch((legacy?'contracts_web_legacy_20261022.json':'contracts_web.json')+'?v='+Date.now(),{cache:'no-store'});
  if(!response.ok)throw Error('데이터 응답 '+response.status);
  const D=await response.json(), dates=Object.keys(D.daily).sort(), last=dates.at(-1),cur=D.daily[last];
  if(!last||!D.rows?.length)throw Error('재고 자료가 비어 있습니다.');
  const net=p=>legacy?(p.mo_new||0)+(p.nat_other||0):(p.net||0);
  const own=p=>legacy?p.mo_new||0:p.own_new||0;
  const cancel=p=>legacy?p.mo_cancel||0:p.own_cancel||0;
  const outgoing=p=>legacy?p.nat_other||0:p.national_out||0;
  const returned=p=>legacy?0:p.national_return||0;
  const company=legacy?'모터원':'효성';
  const label=legacy?'계약 추정 · 과거 원집계':'순계약 추정';
  const recentWeek=legacy?D.weekly.at(-1):D.recent.week;
  const recentMonth=legacy?D.monthly.at(-1):D.recent.month;
  let period='daily',analysis='week',cat='전체',query='',all=false,selected='E 300 4MATIC AMG Line';
  root.querySelector('.bd-date').textContent='데이터 기준 '+last;
  $('bd-baseline').textContent=legacy?'기존 이력 보존본 · 새 회사 실적과 합산하지 않음':D.baseline+'부터 관측 · 첫날은 기준선 · 이후 파일 간 변동 집계';
  root.querySelector('.bd-footer').textContent=legacy
    ?'이전 모터원 자료의 원래 집계를 그대로 보관합니다. 당시 계약 추정은 신규계약과 재고 이탈의 합계로, 새 자료의 순계약 추정과 정의가 다릅니다.'
    :D.method+' 파일 사이 실제 계약일·타 딜러 계약 여부는 확인되지 않아 주·월 합계는 관측일 기준입니다. 배정 제한 차량은 상담 확인이 필요합니다.';
  const range=p=>p.start+' ~ '+p.end;
  const previous=D.daily[dates.at(-2)],delta=previous?cur.sell-previous.sell:0;
  $('bd-kpis').innerHTML=[
    ['전국 판매가능 재고',D.sellable_now,`직전 자료 대비 ${delta>0?'+':''}${fmt(delta)}대`],
    ['최근일 전국 '+label,net(cur),cur.baseline?'비교 시작 기준선':last+' · 관측 구간 '+cur.gap+'일'],
    ['최근 1주 전국 '+label,net(recentWeek),range(recentWeek)],
    ['최근 1개월 전국 '+label,net(recentMonth),range(recentMonth)]
  ].map(([k,n,sub])=>`<div class="bd-stat"><label>${esc(k)}</label><strong>${fmt(n)}<span style="font-size:13px;margin-left:5px">대</span></strong><small>${esc(sub)}</small></div>`).join('');
  function selectedPeriod(){return period==='daily'?cur:period==='weekly'?D.weekly.at(-1):D.monthly.at(-1)}
  function periodDates(){return period==='daily'?[last]:selectedPeriod().days}
  function count(r){const heat=D.heat[r.cat+'|'+r.model]||{};return periodDates().reduce((sum,d)=>{const a=heat[d]||[];return sum+(a[0]||0)+(a[1]||0)-(legacy?0:(a[2]||0)+(a[3]||0))},0)}
  function breakdown(p){return `<span>${company} 입고 차량 계약 전환 <b>${fmt(own(p))}건</b></span><span>전국 재고 이탈 추정 <b>${fmt(outgoing(p))}대</b></span>`+(legacy?'':`<span>계약 해제 <b>−${fmt(cancel(p))}건</b></span><span>이탈 차량 재등장 <b>−${fmt(returned(p))}대</b></span>`)}
  function chart(){
    const series=period==='daily'?dates.slice(-9).map(d=>({label:d.slice(5).replace('-','/'),...D.daily[d]})):D[period].slice(-8).map(p=>({...p,label:period==='weekly'?p.start.slice(5)+'~':p.start.slice(0,7)}));
    const maximum=Math.max(1,...series.map(x=>Math.abs(net(x))));
    $('bd-chart').innerHTML=series.map(p=>`<div class="bd-baritem"><div class="bd-value">${p.baseline?'기준선':fmt(net(p))}</div><div class="bd-bar" style="height:${Math.max(2,88*Math.abs(net(p))/maximum)}px;${net(p)<0?'background:#ac5264':''}"></div><div class="bd-label">${esc(p.label)}</div></div>`).join('');
    $('bd-chart').setAttribute('aria-label','기간별 전국 '+label);
    $('bd-chartcaption').textContent=legacy?'이전 모터원 관측 이력 · 원래 집계 보존':'신규 계약 전환과 재고 이탈에서 계약 해제·재등장을 차감';
    $('bd-flowfoot').innerHTML=breakdown(selectedPeriod());
    $('bd-colperiod').textContent=(period==='daily'?'최근일':period==='weekly'?'최근 주':'최근 월')+(legacy?' 계약 추정':' 순계약 추정');
  }
  function yearGroups(r){return D.year_stock?.[r.cat+'|'+r.model]||{}}
  function yearLabel(r){const years=Object.keys(yearGroups(r)).filter(y=>y!=='unknown');return years.length>1?' · '+years.sort().map(y=>'MY'+esc(y.slice(-2))).join(' / '):''}
  function combosHtml(combos){return Object.entries(combos).sort((a,b)=>b[1]-a[1]).map(([color,n])=>{const[e,i]=color.split('|');return `<div class="bd-combo"><div class="bd-cn">${esc(e)}<small>${esc(i||'미기재')}</small></div><b>${fmt(n)}대</b></div>`}).join('')}
  function detail(){
    const r=D.rows.find(x=>x.model===selected);if(!r)return;
    const groups=yearGroups(r),ys=Object.keys(groups).sort(),yearInfo=ys.length>1?ys.map(y=>`<details open style="margin-top:12px"><summary style="cursor:pointer;color:var(--bd-accent);font-size:12px">${y==='unknown'?'연식 미확인':esc(y)+'년식'} · ${fmt(groups[y].stock)}대</summary>${combosHtml(groups[y].combos)}</details>`).join(''):combosHtml(r.combos);
    $('bd-detail').innerHTML=`<div class="bd-detailtop">선택한 차종 · ${esc(r.cat)}${yearLabel(r)}</div><h3>${esc(r.model)}</h3><div class="bd-detailnums"><div><span>판매가능 재고</span><b>${fmt(r.stock)}<small style="font-size:12px"> 대</small></b></div><div><span>${$('bd-colperiod').textContent}</span><b>${fmt(count(r))}<small style="font-size:12px"> 대</small></b></div><div><span>색상 조합</span><b>${Object.keys(r.combos).length}<small style="font-size:12px"> 종</small></b></div></div><div class="bd-tag">외장 / 내장별 재고</div>${yearInfo}`;
  }
  function list(){
    const rows=D.rows.filter(r=>r.stock>0&&(cat==='전체'||r.cat===cat)&&(!query||(r.model+' '+r.cat).toLowerCase().includes(query))).sort((a,b)=>b.stock-a.stock);
    $('bd-count').textContent=`${rows.length}개 트림 · ${fmt(rows.reduce((s,r)=>s+r.stock,0))}대`;
    if(rows.length&&!rows.some(r=>r.model===selected))selected=rows[0].model;
    $('bd-models').innerHTML=(all?rows:rows.slice(0,7)).map(r=>`<button class="bd-model" type="button" data-model="${esc(r.model)}" aria-pressed="${selected===r.model}"><span><small>${esc(r.cat)}${yearLabel(r)}</small><strong>${esc(r.model)}</strong></span><span class="bd-n">${fmt(r.stock)}</span><span class="bd-n">${fmt(count(r))}</span></button>`).join('')||'<div class="bd-empty">일치하는 차종이 없습니다.</div>';
    $('bd-more').hidden=rows.length<=7;$('bd-more').textContent=all?'접기 ↑':`전체 ${rows.length}개 트림 보기 ↓`;
    if(rows.length)detail();else $('bd-detail').innerHTML='';
  }
  function categories(){const cats=['전체',...D.cat_order.filter(c=>D.rows.some(r=>r.cat===c&&r.stock>0))];$('bd-categories').innerHTML=cats.map(c=>`<button class="bd-chip" data-cat="${esc(c)}" type="button" aria-pressed="${cat===c}">${esc(c)}</button>`).join('')}
  function analysisPanel(){
    const p=analysis==='week'?recentWeek:recentMonth,title=analysis==='week'?'최근 1주':'최근 1개월';
    $('bd-analysis-caption').textContent=title+' · '+range(p)+' · 확보된 관측일 기준';
    $('bd-analysis').innerHTML=[
      ['전국 '+label,fmt(net(p))+'대',legacy?'이전 이력 원집계':'계약 해제·재등장 차감 후'],
      [company+' 입고 차량 계약 전환',fmt(own(p))+'건',`계약 해제 ${fmt(cancel(p))}건`],
      ['전국 재고 이탈 추정',fmt(outgoing(p))+'대',legacy?'전국 미배정 재고 이탈 기준':`재등장 ${fmt(returned(p))}대 · 확정 계약 아님`],
      ['판매가능 재고 증감',(p.sell_delta>0?'+':'')+fmt(p.sell_delta)+'대',legacy?`신규 입고 ${fmt(p.new_stock)}대`:`대상 편입 ${fmt(p.stock_in)}대 · 대상 이탈 ${fmt(p.stock_out)}대`]
    ].map(([k,n,sub])=>`<div class="bd-analysis-stat"><span>${esc(k)}</span><b>${esc(n)}</b><span>${esc(sub)}</span></div>`).join('')+
    `<div class="bd-analysis-rank"><h3>${title} 전국 ${label} 상위 차종</h3>${p.top_models.slice(0,5).map((r,i)=>`<div class="bd-rank-row"><span>${i+1}</span><strong>${esc(r.model)}</strong><b>${fmt(r.n)}대</b></div>`).join('')||'<p>비교할 계약 변동이 없습니다.</p>'}</div>`;
  }
  const toggle=(id,selector,b)=>$(id).querySelectorAll(selector).forEach(x=>x.setAttribute('aria-pressed',x===b));
  $('bd-period').onclick=e=>{const b=e.target.closest('[data-period]');if(!b)return;period=b.dataset.period;toggle('bd-period','button',b);chart();list()};
  $('bd-analysis-period').onclick=e=>{const b=e.target.closest('[data-analysis-period]');if(!b)return;analysis=b.dataset.analysisPeriod;toggle('bd-analysis-period','button',b);analysisPanel()};
  $('bd-categories').onclick=e=>{const b=e.target.closest('[data-cat]');if(!b)return;cat=b.dataset.cat;categories();list()};
  $('bd-search').oninput=e=>{query=e.target.value.trim().toLowerCase();list()};
  $('bd-models').onclick=e=>{const b=e.target.closest('[data-model]');if(!b)return;selected=b.dataset.model;list()};
  $('bd-more').onclick=()=>{all=!all;list()};
  chart();categories();list();analysisPanel();
})().catch(error=>{const root=document.getElementById('bd-sales-desk');const p=document.createElement('p');p.setAttribute('role','alert');p.textContent='데이터를 불러오지 못했습니다. 잠시 후 새로고침해 주세요. '+error.message;root.querySelector('.bd-main').prepend(p);root.querySelector('.bd-date').textContent='데이터 확인 실패'});
