(() => {
 'use strict';
 const esc=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const month=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit'}).format(new Date());
 const norm=s=>String(s||'').normalize('NFKD').replace(/Mercedes-Benz/g,'').replace(/Mercedes-AMG/g,'AMG').replace(/Mercedes-Maybach/g,'Maybach').toLowerCase().replace(/[^a-z0-9+]/g,'');
 const money=v=>(Math.floor(v/10000)).toLocaleString('ko-KR')+'만원';
 const url=o=>/^BenzDream_PriceAndPromotion_2026\.html(?:#[\w-]+)?$/.test(o?.url||'')?o.url:'BenzDream_PriceAndPromotion_2026.html#price-models';
 function match(offers,t){
  const list=offers.filter(o=>o.year===t.year);
  const exact=list.find(o=>o.nst===t.nst&&norm(o.name)===norm(t.name));if(exact)return exact;
  if(t.nst){const byCode=list.filter(o=>o.nst===t.nst);if(byCode.length&&new Set(byCode.map(url)).size===1)return byCode[0];}
  const byName=list.filter(o=>norm(o.name)===norm(t.name));return byName.length&&new Set(byName.map(url)).size===1?byName[0]:null;
 }
 function render(el,t,o,m){
  if(!el)return;
  const current=m===month();o=current?o:null;
  const prices=o?.conditional_prices?.length?o.conditional_prices:(o&&Number.isFinite(o.rate)&&t.price?[{condition:o.rate?'표기된 할인 조건 기준':'권장가 기준 · 추가 혜택 별도',rate:o.rate,price:Math.floor(t.price*(100-o.rate)/100/10000)*10000}]:[]);
  el.classList.add('bd-linked-promotion');
  el.innerHTML=`<p class="bd-promo-label">${esc(t.year)} · ${esc(t.name)}</p><h3>${o?esc(o.display_label||(o.rate?o.rate+'% 할인':'기본 정률 할인 없음')):'최신 구매 조건 상담'}</h3><p>${o?esc(o.condition):'현재 확인된 이 연식·트림의 할인 조건이 없습니다. 다른 연식의 할인율을 적용하지 않으며, 선택 차량의 조건을 개별 안내합니다.'}</p>${prices.length?`<dl>${prices.map(p=>`<div><dt>${esc(p.condition)}${p.rate&&!String(p.condition).includes(p.rate+'%')?' · '+p.rate+'%':''}</dt><dd>${money(p.price)}</dd></div>`).join('')}</dl>`:''}<p class="bd-promo-small">${o?esc(m.replace('-','.'))+' 프로모션 · ':''}VAT 포함 · 만원 미만 절삭. 차량·금융·고객 조건별로 적용되며 등록비·금융비용은 별도입니다.</p><a href="${url(o)}">해당 차종 가격·적용 조건 확인 ↗</a>`;
 }
 window.BenzDreamPromotions={match,render};
 const style=document.createElement('style');style.textContent='.bd-linked-promotion{box-sizing:border-box;padding:22px;margin:18px 0;border:1px solid #bcd2c5;background:#edf6f0;color:#1d3428;text-align:left;min-width:0;overflow-wrap:anywhere}.bd-linked-promotion h3{font-size:24px;line-height:1.4;margin:8px 0}.bd-linked-promotion p,.bd-linked-promotion a{font-size:18px;line-height:1.65}.bd-linked-promotion .bd-promo-label,.bd-linked-promotion .bd-promo-small{font-size:16px}.bd-linked-promotion dl{margin:12px 0}.bd-linked-promotion dl>div{padding:12px 0;border-top:1px solid #cbdcd1}.bd-linked-promotion dt{font-size:17px;line-height:1.5}.bd-linked-promotion dd{margin:4px 0;font-size:28px;font-weight:700}.bd-linked-promotion a{display:inline-block;padding:10px 0;text-underline-offset:4px}.bd-live-promo-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.bd-live-promo-grid .bd-linked-promotion{margin:0}@media(max-width:650px){.bd-live-promo-grid{grid-template-columns:1fr}.bd-linked-promotion{padding:18px}}';document.head.append(style);
 let data=null;
 function draw(){document.querySelectorAll('[data-promotion-model]').forEach(el=>{const t={name:el.dataset.promotionModel,year:el.dataset.promotionYear,price:Number(el.dataset.promotionPrice)};render(el,t,data?match(data.offers,t):null,data?.month);});}
 async function load(){try{const res=await fetch('assets/current-promotions.json?v='+Date.now(),{cache:'no-store'});if(!res.ok)throw Error('source');const next=await res.json();if(!Array.isArray(next.offers))throw Error('data');data=next;}catch{data=null;}draw();}
 if(document.querySelector('[data-promotion-model]')){draw();load();setInterval(load,300000);document.addEventListener('visibilitychange',()=>{if(!document.hidden)load();});}
})();
