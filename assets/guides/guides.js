(() => {
  'use strict';
  const $ = id => document.getElementById(id);
  const esc = s => String(s ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const kst = () => new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
  const normalize = s => s.normalize('NFKD').replace(/Mercedes-Benz/g,'').replace(/Mercedes-AMG/g,'AMG').replace(/Mercedes-Maybach/g,'Maybach').toLowerCase().replace(/[^a-z0-9+]/g,'');
  const production = ['mb-hansdream.co.kr','www.mb-hansdream.co.kr'].includes(location.hostname);
  if(production){
    window.dataLayer=window.dataLayer||[];window.gtag=function(){window.dataLayer.push(arguments)};
    window.gtag('js',new Date());window.gtag('config','G-7T2ECBWN0K',{content_group:'차종별 통합 가이드'});
    const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';document.head.append(s);
  }
  let vehicle=null, selected=null;
  const track=(name,extra={})=>{if(production&&window.gtag)window.gtag('event',name,{model:vehicle?.family,model_year:selected?.year,trim:selected?.name,...extra})};
  document.querySelectorAll('[data-track]').forEach(a=>a.addEventListener('click',()=>track(a.dataset.track,{destination:a.getAttribute('href')})));
  $('model-jump')?.addEventListener('change',e=>{track('vehicle_navigation',{destination:e.target.value});location.href=e.target.value});
  if($('model-search')){
    let category='전체';
    const filter=()=>{const q=$('model-search').value.toLowerCase().replace('마이바흐','maybach');let count=0;
      document.querySelectorAll('.model-card').forEach(card=>{card.hidden=!((category==='전체'||card.dataset.category===category)&&card.dataset.search.toLowerCase().includes(q));if(!card.hidden)count++});
      document.querySelectorAll('.model-group').forEach(group=>{const visible=[...group.querySelectorAll('.model-card')].filter(card=>!card.hidden).length;group.hidden=!visible;group.querySelector('.group-count').textContent=visible;});
      $('model-count').textContent=count+'개 차종 가이드';$('no-models').hidden=count>0;};
    $('model-search').addEventListener('input',filter);document.querySelectorAll('button[data-category]').forEach(b=>b.addEventListener('click',()=>{category=b.dataset.category;document.querySelectorAll('button[data-category]').forEach(a=>a.setAttribute('aria-pressed',a===b));filter()}));
  }
  if(!$('vehicle-data'))return;
  vehicle=JSON.parse($('vehicle-data').textContent);let stock=null, offers=[],reportMonth='',reportUrl='BenzDream_MonthlyReport_latest.html';
  selected=vehicle.trims[0];
  const statenames={length_mm:'전장 (mm)',width_mm:'전폭 (mm)',height_mm:'전고 (mm)',wheelbase_mm:'휠베이스 (mm)',engine_cc:'배기량 (cc)',power_ps:'최고출력 (PS)',torque_nm:'최대토크 (Nm)',torque_kgfm:'최대토크 (kg·m)',drive:'구동 방식',transmission:'변속기',zero_to_100_s:'0–100 km/h (초)',combined_efficiency:'복합 연비·전비',battery_kwh:'배터리 용량 (kWh)',certified_range_km:'국내 인증 주행거리 (km)',battery_cell_maker:'배터리 셀 제조사'};
  function renderSpecs(){
    const items=Object.entries(selected.specs||{}).filter(([,v])=>v);
    $('selected-specs').innerHTML=items.length?`<h3>${esc(selected.year+' '+selected.name)}</h3>${selected.spec_note?`<p class="small">${esc(selected.spec_note)}</p>`:''}<dl class="spec-lines">${items.map(([k,v])=>`<div><dt>${esc(statenames[k])}</dt><dd>${esc(v)}</dd></div>`).join('')}</dl>`:`<p class="notice">${esc(selected.year+' '+selected.name)}의 국내 제원 확인이 필요한 항목은 아래 연식이 표시된 참고 제원과 구분해 보세요.</p>`;
  }
  function renderOptions(){
    if(vehicle.customer_compare){renderEquipmentOverview();renderCustomerOptions();return;}
    const rows=selected.options||[];
    $('option-year-note').textContent=rows.length?selected.year+' · '+selected.name+' 기준입니다. 기본 / 선택 / 유료 선택 / 미적용을 구분했습니다.':selected.year+' 상세 옵션표는 보완 예정입니다. 아래 연식이 표시된 카탈로그·비교 자료를 함께 확인하세요.';
    const keys=rows.filter(r=>!/^[0-9]{3}[AU]$/.test(r.code)&&/헤드업|사운드|선루프|서스펜션|스티어링|라이트|통풍|카메라|시트|MBUX/.test(r.name)).slice(0,15);
    $('option-summary').innerHTML=keys.length?`<div class="option-list">${keys.map(r=>`<div><strong>${esc(r.name)}</strong><span>${esc(r.state)}</span></div>`).join('')}</div>`:'';
    const same=vehicle.trims.filter(t=>t.year===selected.year && t.options.length);
    const all=new Map();same.forEach(t=>t.options.forEach(r=>{const k=r.code+'|'+r.name;if(!all.has(k))all.set(k,r)}));
    const q=$('option-search').value.toLowerCase();const entries=[...all.entries()].filter(([,r])=>(r.code+' '+r.name).toLowerCase().includes(q));
    $('option-table').innerHTML=entries.length?`<div class="table-scroll" role="region" tabindex="0" aria-label="트림별 전체 옵션 비교"><table class="option-matrix"><caption>${esc(selected.year)} 장비·옵션 비교 · 옆으로 이동해 다른 트림을 확인하세요.</caption><thead><tr><th scope="col">장비</th>${same.map(t=>`<th scope="col" class="${t.id===selected.id?'selected':''}">${esc(t.name)}<br><small>${esc(t.nst)}</small></th>`).join('')}</tr></thead><tbody>${entries.map(([key,r])=>`<tr><th scope="row">${esc(r.name)}<br><small>${esc(r.code)}</small></th>${same.map(t=>{const v=t.options.find(x=>x.code+'|'+x.name===key);return `<td class="${t.id===selected.id?'selected':''}">${esc(v?.state||'확인 필요')}</td>`}).join('')}</tr>`).join('')}</tbody></table></div>`:'<p class="notice">일치하는 장비 항목이 없습니다. 아래 참고 자료 또는 상담으로 확인해 주세요.</p>';
  }

  const equipmentCategories=['주행·승차감','안전·주차','시트·공간','디스플레이·오디오','실내 편의','외관·생활 편의','충전·전기차 기능'];
  function equipmentGroups(rows,prefix,reference=false){
    const merged=new Map();rows.forEach(r=>{const key=[r.category,r.label,r.state].join('|');if(!merged.has(key))merged.set(key,{...r,scopes:[]});if(r.scope&&!merged.get(key).scopes.includes(r.scope))merged.get(key).scopes.push(r.scope)});
    return '<div class="equipment-sections">'+equipmentCategories.map((cat,i)=>{const items=[...merged.values()].filter(r=>r.category===cat);if(!items.length)return '';return `<section class="equipment-category" id="${prefix}-${i}"><h4>${esc(cat)}</h4><ul>${items.map(r=>`<li><span>${esc(r.label)}${r.scopes.length?`<small>${esc(r.scopes.join(' · '))}</small>`:''}</span>${reference&&r.state==='구성별 확인'?'':`<span class="equipment-state ${r.state==='기본'?'is-standard':''}">${esc(r.state)}</span>`}</li>`).join('')}</ul></section>`}).join('')+'</div>';
  }
  function renderEquipmentOverview(){
    if(!vehicle.equipment||!$('equipment-overview'))return;
    const entry=vehicle.equipment.trims[selected.id],rows=entry?.rows||[],ref=vehicle.equipment.reference;
    $('equipment-trim').innerHTML=vehicle.trims.filter(t=>t.year===selected.year).map(t=>`<option value="${esc(t.id)}" ${t.id===selected.id?'selected':''}>${esc(t.display_name||t.name)}</option>`).join('');
    $('equipment-trim').onchange=e=>selectTrim(e.target.value);
    $('equipment-selected-name').textContent=selected.year+' · '+(selected.display_name||selected.name);
    $('equipment-note').textContent=entry.matrix?'기본 장비와 선택 가능한 장비를 분야별로 모았습니다. 선택 사양의 주문 조합은 별도로 확인해 주세요.':'아래 차종 주요 장비도 함께 살펴보세요. 트림별 적용 여부는 구분해 안내합니다.';
    const nav='<nav class="equipment-nav" aria-label="주요 장비 분야">'+equipmentCategories.map((c,i)=>rows.some(r=>r.category===c)?`<a href="#equipment-${i}">${esc(c)}</a>`:'').join('')+'</nav>';
    $('equipment-primary').innerHTML=rows.length?nav+equipmentGroups(rows,'equipment'):'<p class="notice">이 구성의 확정 장비 목록은 보완 중입니다. 아래 연식과 구성 안내를 함께 확인해 주세요.</p>';
    const reference=!entry.matrix&&ref.rows.length>0;
    $('equipment-reference').hidden=!reference;
    $('equipment-reference-title').textContent=(ref.year+' '+vehicle.family+' 주요 장비').trim();
    $('equipment-reference-note').textContent=(ref.year!==selected.year?`선택한 ${selected.year}와 다른 ${ref.year} 참고 안내입니다. `:'')+'트림에 따라 기본·선택 적용이 달라집니다. 항목 아래에 표시된 구성도 함께 확인해 주세요.';
    const refnav='<nav class="equipment-nav" aria-label="차종 주요 장비 분야">'+equipmentCategories.map((c,i)=>ref.rows.some(r=>r.category===c)?`<a href="#equipment-reference-${i}">${esc(c)}</a>`:'').join('')+'</nav>';
    $('equipment-reference-list').innerHTML=reference?refnav+equipmentGroups(ref.rows,'equipment-reference',true):'';
    const alternatives=vehicle.trims.filter(t=>t.year!==selected.year&&vehicle.equipment.trims[t.id]?.matrix).filter((t,i,a)=>a.findIndex(x=>x.year===t.year)===i);
    $('equipment-year-links').innerHTML=!entry.matrix&&!reference&&alternatives.length?'<p>다른 연식의 주요 장비도 확인할 수 있습니다.</p>'+alternatives.map(t=>`<button class="equipment-other-year" data-equipment-trim="${esc(t.id)}">${esc(t.year)} 주요 장비 보기 ↗</button>`).join(''):'';
    $('equipment-year-links').querySelectorAll('[data-equipment-trim]').forEach(b=>b.onclick=()=>selectTrim(b.dataset.equipmentTrim));
  }

  let comparePair=null,compareYear=null;
  const trimLabel=t=>(t.display_name||t.name)+(t.price?'':' · 가격 안내 전');
  const activeComparison=()=>vehicle.customer_compare.years[selected.year];
  const customerValue=(t,f)=>f.values?.[t.id]||'확인 필요';
  const unknown=v=>/확인 필요|개별 확인/.test(v);
  function renderCustomerOptions(){
    const config=activeComparison(),trims=vehicle.trims.filter(t=>t.year===selected.year);
    const available=config.features.length>0||config.common.length>0;
    $('customer-comparison').hidden=!available;
    document.querySelector('.common-equipment').hidden=!config.common.length;
    $('common-heading').textContent=selected.year+' 주요 공통 기본 사양';
    $('common-list').innerHTML=config.common.map(f=>`<li><span aria-hidden="true">✓</span>${esc(f.values?Object.values(f.values)[0]:f.label)}</li>`).join('');
    const missing=trims.filter(t=>!config.coverage[t.id]);
    $('option-year-note').textContent=selected.year+' · 주요 장비 전체를 살펴보고, 트림별 차이도 비교하세요.';
    $('customer-previous-year').hidden=!missing.length;
    $('customer-previous-year').textContent=available?'트림에 따라 기본·선택 사양과 주문 가능한 조합이 다릅니다.':'선택 연식의 트림별 적용 여부는 추가 확인이 필요합니다. 위 주요 장비 안내의 연식과 구성을 함께 확인해 주세요.';
    $('catalog-equipment-reference').hidden=true;
    const single=trims.length===1;
    $('comparison-heading').textContent=single?'이 트림의 주요 장비.':'고민 중인 두 트림을 비교하세요.';
    document.querySelector('.compare-pickers').hidden=single;document.querySelector('.compare-tools').hidden=single;
    if(compareYear!==selected.year){comparePair=[...config.default_pair];compareYear=selected.year;$('differences-only').checked=false;}
    for(const [i,id] of ['compare-left','compare-right'].entries()){
      const el=$(id);el.innerHTML=trims.map(t=>`<option value="${esc(t.id)}" ${t.id===comparePair[i]?'selected':''}>${esc(trimLabel(t))}</option>`).join('');
      el.onchange=()=>{comparePair[i]=el.value;renderCustomerTable();track('vehicle_comparison_select',{comparison_side:i})};
    }
    $('differences-only').onchange=renderCustomerTable;renderCustomerTable();
  }
  function renderCustomerTable(){
    const config=activeComparison(),[left,right]=comparePair.map(id=>vehicle.trims.find(t=>t.id===id));
    const single=vehicle.trims.filter(t=>t.year===selected.year).length===1;
    const common=config.common.map(f=>({...f,values:f.values||Object.fromEntries(vehicle.trims.filter(t=>t.year===selected.year).map(t=>[t.id,'기본 적용']))}));
    const all=[...config.features,...common].map(f=>({...f,values:[customerValue(left,f),customerValue(right,f)]}));
    const differs=f=>!f.values.some(unknown)&&f.values[0]!==f.values[1];
    const differences=all.filter(differs),pending=all.filter(f=>f.values.some(unknown));
    const shown=single?all:($('differences-only').checked?all.filter(f=>differs(f)||f.values.some(unknown)):all);
    $('difference-count').textContent=left.id===right.id&&!single?'같은 트림을 선택했습니다.':`확인된 주요 사양 ${differences.length}가지 차이${pending.length?' · '+pending.length+'개 확인 필요':''}`;
    const price=t=>t.price?(t.price/10000).toLocaleString('ko-KR')+'만원':'가격 안내 전';
    const delta=!single&&left.price&&right.price?`<p class="comparison-price">권장 소비자가 차이 <strong>${(Math.abs(left.price-right.price)/10000).toLocaleString('ko-KR')}만원</strong></p>`:'';
    $('customer-option-table').innerHTML=delta+`<div class="table-scroll customer-table-scroll"><table class="customer-matrix ${single?'single-trim':''}"><caption>${esc(selected.year)} 주요 사양 · 가격은 2026.09.25 기준</caption><thead><tr><th scope="col">주요 항목</th><th scope="col">${esc(left.display_name||left.name)}</th>${single?'':`<th scope="col">${esc(right.display_name||right.name)}</th>`}</tr></thead><tbody><tr class="price-row"><th scope="row">권장 소비자가</th><td>${price(left)}</td>${single?'':`<td>${price(right)}</td>`}</tr>${shown.map(f=>`<tr class="${!single&&differs(f)?'is-different':f.values.some(unknown)?'is-pending':'is-common'}"><th scope="row">${esc(f.label)}${!single&&differs(f)?'<span class="difference-label">차이</span>':''}</th>${(single?f.values.slice(0,1):f.values).map(v=>`<td>${esc(v)}</td>`).join('')}</tr>`).join('')}</tbody></table></div>${shown.length?'':`<p class="notice">${all.length?'선택한 주요 사양은 같습니다. 다른 트림을 선택하거나 전체 주요 사양을 펼쳐 보세요.':'트림별 주요 장비 확인 후 비교 항목을 추가하겠습니다.'}</p>`}`;
  }
  const swatch=name=>{const a=[[/화이트|white/i,'#edece6'],[/블랙|black/i,'#242625'],[/베이지|beige/i,'#c5b28d'],[/브라운|brown/i,'#785440'],[/블루|blue/i,'#224969'],[/레드|red/i,'#813b42'],[/실버|silver/i,'#b7babe'],[/그레이|grey|gray/i,'#858b89'],[/그린|green|베르데/i,'#73867b']];return a.find(([r])=>r.test(name))?.[1]||'#a7a5a2'};
  function showColor(c){
    const img=(selected.color_override?.images||vehicle.color_images)[c.code]||c.image;
    $('color-stage').hidden=false;$('color-stage').innerHTML=`<div class="color-stage-visual">${img?`<img src="${esc(img)}" alt="${esc(vehicle.family+' '+c.name)}">`:`<span class="color-swatch" style="--color:${swatch(c.name)}"></span>`}</div><div><p class="eyebrow">${esc(c.code)}</p><h3>${esc(c.name)}</h3><p>${esc(c.state)}</p><p class="small">${img?esc(selected.color_override?.year||vehicle.catalog_year||'카탈로그')+' 컬러 이미지 · 선택 연식의 휠·장비는 다를 수 있습니다.':'실차 사진 미확보 · 색상칩은 참고용입니다.'}</p></div>`;
    document.querySelectorAll('[data-color]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.color===c.code));
  }
  function renderColors(){
    let colors=selected.options.filter(r=>(/^[0-9]{3}[AU]$/.test(r.code)||(/^C\d{2}$/.test(r.code)&&/투톤.*페인트/.test(r.name)))&&!['미적용','개별 확인'].includes(r.state));
    const fallback=!colors.length;
    if(fallback)colors=selected.color_override?.colors||vehicle.catalog_colors||[];
    $('color-year-note').textContent=fallback?`${selected.color_override?.year||vehicle.catalog_year||'보관 카탈로그'}의 ${vehicle.family} 컬러입니다. ${selected.year} 선택 트림의 주문 가능 조합은 확인이 필요합니다.`:selected.year+' · '+selected.name+'의 선택 색상입니다. 일부 조합은 함께 선택할 수 없습니다.';
    $('color-stage').hidden=true;
    for(const [id,ending] of [['exterior-colors','U'],['interior-colors','A']]){
      const cs=colors.filter(c=>ending==='A'?c.code.endsWith('A'):(c.code.endsWith('U')||/^C\d{2}$/.test(c.code)));$(id).innerHTML=cs.length?cs.map(c=>{const img=(selected.color_override?.images||vehicle.color_images)[c.code]||c.image;return `<button class="color-card" data-color="${esc(c.code)}" aria-pressed="false">${img?`<img src="${esc(img)}" alt="${esc(c.name)}" loading="lazy" width="115" height="90">`:`<span class="color-swatch" style="--color:${swatch(c.name)}"></span>`}<span><strong>${esc(c.name)}</strong><small>${esc(c.code)} · ${esc(c.state)}</small></span></button>`}).join(''):'<p class="notice">해당 트림의 선택 색상은 추가 확인 후 안내하겠습니다.</p>';
      $(id).querySelectorAll('[data-color]').forEach(b=>b.addEventListener('click',()=>{const c=cs.find(x=>x.code===b.dataset.color);showColor(c);track('vehicle_color_select',{color_code:c.code})}));
    }
    if(colors.length)showColor(colors[0]);
  }
  function renderBuying(){
    $('selected-name').textContent=selected.year+' · '+selected.name;
    $('current-price').textContent=selected.price?(selected.price/10000).toLocaleString('ko-KR')+'만원':'가격 확인 중';
    $('price-date').textContent=selected.price?'2026.09.25 권장 소비자가 · VAT 포함':'선택 연식의 공식 가격 확인 후 안내';
    const offer=reportMonth===kst().slice(0,7)?offers.find(x=>x.year===selected.year&&normalize(x.name)===normalize(selected.name)):null;
    $('offer-rate').textContent=offer?offer.rate+'%':'개별 조건 확인';
    $('offer-note').textContent=offer?`${reportMonth.replace('-','.')} · ${selected.year} 안내 조건. 금융상품·대상 차량 등 세부 적용 조건은 리포트에서 확인하세요.`:'이번 달 리포트에서 연식과 금융 이용 조건을 확인하세요. 이전 월 할인율은 표시하지 않습니다.';
    $('report-link').href=reportUrl;
    $('stock-link').href='BenzDream_Stock.html?model='+encodeURIComponent(selected.name);
    $('stock-colors').replaceChildren();
    if(!stock){$('stock-value').textContent='재고 확인 필요';$('stock-note').textContent='재고 연결을 확인 중입니다. 전국 재고 페이지에서 확인할 수 있습니다.';return;}
    const age=(Date.parse(kst()+'T00:00:00Z')-Date.parse(stock.date+'T00:00:00Z'))/86400000;
    const entries=Object.entries(stock.models||{}).filter(([n])=>normalize(n)===normalize(selected.name));
    const match=entries.length===1?entries[0][1]:null;
    $('stock-value').textContent=age>1?'최신 재고 재확인':match?'색상 조합 확인':'개별 재고 확인';
    $('stock-note').textContent=`${stock.date} 공개 재고 기준. ${age>1?'지난 자료이므로 현재 출고 가능 여부를 확인해 주세요. ':''}${match?'동일 모델명 기준이며 연식·배정 가능 여부는 별도 확인이 필요합니다.':'일치 항목이 없더라도 재고가 없다는 뜻은 아닙니다.'}`;
    if(match)Object.entries(match.colors||{}).filter(([,v])=>Number(typeof v==='number'?v:v?.total)>0).slice(0,8).forEach(([name])=>{const span=document.createElement('span');span.textContent=name.replace('|',' / ');$('stock-colors').append(span)});
  }
  function selectTrim(id,send=true){
    selected=vehicle.trims.find(t=>t.id===id)||vehicle.trims[0];
    document.querySelectorAll('[data-trim]').forEach(b=>{const on=b.dataset.trim===selected.id;b.setAttribute('aria-pressed',on);b.hidden=b.dataset.modelYear!==selected.year||(b.dataset.pricePending==='true'&&$('pending-trims')?.getAttribute('aria-expanded')!=='true');b.querySelector('.trim-action').textContent=on?'선택한 트림 ✓':'이 트림 선택 ↗'});
    if($('pending-trims')){const hasPending=vehicle.trims.some(t=>t.year===selected.year&&!t.price);$('pending-trims').hidden=!hasPending;document.querySelector('.pending-note').hidden=!hasPending;}
    document.querySelectorAll('[data-year]').forEach(b=>b.setAttribute('aria-pressed',b.dataset.year===selected.year));
    renderSpecs();renderOptions();renderColors();renderBuying();if(send)track('vehicle_trim_select');
  }
  document.querySelectorAll('[data-trim]').forEach(b=>b.addEventListener('click',()=>selectTrim(b.dataset.trim)));
  document.querySelectorAll('[data-year]').forEach(b=>b.addEventListener('click',()=>selectTrim(vehicle.trims.find(t=>t.year===b.dataset.year).id)));
  $('option-search')?.addEventListener('input',renderOptions);
  $('pending-trims')?.addEventListener('click',()=>{const open=$('pending-trims').getAttribute('aria-expanded')!=='true';$('pending-trims').setAttribute('aria-expanded',open);$('pending-trims').textContent=open?'추가 구성 접기':'가격 안내 전 추가 구성 보기';document.querySelectorAll('[data-price-pending]').forEach(b=>b.hidden=!open||b.dataset.modelYear!==selected.year)});
  document.querySelectorAll('[data-video]').forEach(b=>b.addEventListener('click',()=>{const id=b.dataset.video;if(!/^[\w-]{11}$/.test(id))return;const frame=document.createElement('iframe');frame.src='https://www.youtube-nocookie.com/embed/'+id+'?autoplay=1&rel=0';frame.title=b.getAttribute('aria-label');frame.className='video-frame';frame.allow='autoplay; encrypted-media; picture-in-picture';frame.allowFullscreen=true;b.replaceWith(frame);track('video_play',{video_id:id})}));
  selectTrim(selected.id,false);
  async function getText(url){const r=await fetch(url,{cache:'no-store'});if(!r.ok)throw Error(r.status);return r.text()}
  async function loadOffers(){
    const landing=new DOMParser().parseFromString(await getText('BenzDream_Landing.html'),'text/html');
    const current=[...landing.querySelectorAll('a[href]')].map(a=>a.getAttribute('href')).filter(u=>/BenzDream_MonthlyReport_\d{6}\.html/.test(u)).sort().reverse()[0];
    if(!current)return;const stamp=current.match(/_(\d{4})(\d{2})\.html/);reportMonth=stamp[1]+'-'+stamp[2];reportUrl=current;
    if(reportMonth!==kst().slice(0,7)){renderBuying();return;}
    const doc=new DOMParser().parseFromString(await getText(current),'text/html');
    doc.querySelectorAll('table').forEach(tab=>{
      const headers=[...tab.querySelectorAll('thead th')].map(x=>x.textContent.trim());
      if(headers.includes('MY26')&&headers.includes('MY27')){
        tab.querySelectorAll('tbody tr').forEach(tr=>{const cells=[...tr.querySelectorAll('td')];['MY26','MY27'].forEach(year=>{const value=cells[headers.indexOf(year)]?.textContent.trim();if(/^\d+(?:\.\d+)?%$/.test(value||''))offers.push({name:cells[0].textContent.trim(),year,rate:parseFloat(value)})})});
      }else if(headers.some(x=>/실효 할인/.test(x))){
        const caption=tab.closest('.ptbl-wrap')?.querySelector('.ptbl-head-label')?.textContent||'';const ym=caption.match(/MY2[67]/);if(!ym)return;
        tab.querySelectorAll('tbody tr').forEach(tr=>{const cells=[...tr.querySelectorAll('td')];const value=cells[headers.findIndex(x=>/실효 할인/.test(x))]?.textContent.trim();if(/^\d+(?:\.\d+)?%$/.test(value||''))offers.push({name:cells[0].textContent.split('·')[0].trim(),year:ym[0],rate:parseFloat(value)})});
      }
    });renderBuying();
  }
  Promise.allSettled([
    fetch('latest_stock.json?v='+Date.now(),{cache:'no-store'}).then(r=>{if(!r.ok)throw Error(r.status);return r.json()}).then(d=>{if(!/^\d{4}-\d{2}-\d{2}$/.test(d.date)||!d.models)throw Error('invalid stock');stock=d;renderBuying()}),
    loadOffers()
  ]).then(()=>renderBuying());
  // Refresh retained pages when the customer returns and every five minutes.
  setInterval(()=>{fetch('latest_stock.json?v='+Date.now(),{cache:'no-store'}).then(r=>r.json()).then(d=>{if(/^\d{4}-\d{2}-\d{2}$/.test(d.date)&&d.models){stock=d;renderBuying()}}).catch(()=>{stock=null;renderBuying()});offers=[];loadOffers().catch(()=>renderBuying())},300000);
})();
