(()=>{'use strict';
const $=id=>document.getElementById(id),menu=document.querySelector('.menu-toggle'),nav=document.querySelector('.global-nav');
menu?.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('open',open)});
const picker=$('v-picker'),jump=document.querySelector('.v-jump');
picker.addEventListener('change',()=>{const target=$(picker.value);if(target){history.pushState(null,'','#'+picker.value);target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion:reduce)').matches?'instant':'smooth'})}});
const sections=[...picker.options].map(o=>$(o.value));let pending=false;
function active(){pending=false;let id=sections[0].id;for(const s of sections){if(s.getBoundingClientRect().top<=jump.offsetHeight+30)id=s.id}picker.value=id;document.querySelectorAll('.v-jump-links a').forEach(a=>{if(a.hash==='#'+id)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current')})}
addEventListener('scroll',()=>{if(!pending){pending=true;requestAnimationFrame(active)}},{passive:true});active();
document.querySelectorAll('[data-gallery]').forEach(g=>g.querySelectorAll('[data-image]').forEach(b=>b.addEventListener('click',()=>{const i=g.querySelector('figure img');i.src=b.dataset.image;i.alt='V클래스 '+b.dataset.caption;g.querySelector('figcaption').textContent=b.dataset.caption;g.querySelectorAll('button').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))})));
const kst=()=>new Intl.DateTimeFormat('en-CA',{timeZone:'Asia/Seoul',year:'numeric',month:'2-digit',day:'2-digit'}).format(new Date());
const money=n=>{let m=n/10000;return (m>=10000?Math.floor(m/10000)+'억 '+(m%10000?new Intl.NumberFormat('ko-KR').format(m%10000)+'만원':'원'):new Intl.NumberFormat('ko-KR').format(m)+'만원')};
const load=async url=>{const r=await fetch(url,{cache:'no-store',signal:AbortSignal.timeout(10000)});if(!r.ok)throw Error('data unavailable');return r.json()};
load('assets/current-promotions.json').then(data=>{
 const p=data.prices?.find(p=>p.nst==='44781313-KR1'&&p.year==='MY27');
 if(p&&Number.isFinite(p.price)&&p.price>0){document.querySelectorAll('[data-price]').forEach(e=>e.textContent=money(p.price));$('roof-total').textContent=money(p.price+5900000);$('price-date').textContent=(p.date||data.price_date)+' 가격 기준 · 부가세 포함'}
 const month=kst().slice(0,7),sourceMonth=String(data.month).replace('.','-');
 if(sourceMonth!==month)return;
 const offer=data.offers?.find(o=>o.nst==='44781313-KR1'&&o.year==='MY27');
 if(offer?.condition){$('offer-title').textContent=Number(month.slice(5))+'월 구매 혜택';$('offer-copy').textContent=offer.condition+' · 적용 대상과 금융비용은 상담으로 확인해 주세요.';$('offer-date').textContent=(data.updated||data.source_date||month)+' 기준'}
}).catch(()=>{});
load('latest_stock.json').then(data=>{
 const normalize=s=>String(s).toUpperCase().replace(/[^A-Z0-9]/g,'');
 const entries=Object.entries(data.models||{}).filter(([name])=>/^V300D4M(ATIC)?(EXCLUSIVE|EXC)?$/.test(normalize(name)));
 const override=(data.availability_overrides||[]).find(rule=>{try{return String(rule.year)==='2027'&&entries.some(([name])=>new RegExp(rule.model_pattern).test(name))}catch{return false}});
 const date=/^\d{4}-\d{2}-\d{2}$/.test(data.date||'')?data.date:null;
 const age=date?(Date.parse(kst()+'T00:00:00Z')-Date.parse(date+'T00:00:00Z'))/86400000:Infinity;
 const colors=new Set();if(!override)entries.forEach(([,m])=>Object.entries(m.year_groups?.['2027']?.colors||{}).forEach(([name,n])=>{if(Number(typeof n==='number'?n:n?.total)>0)colors.add(name)}));
 const fresh=age>=0&&age<=1;
 $('stock-title').textContent=colors.size?(fresh?'확인 가능한 외장·실내 조합':'색상·출고 일정 재확인'):'색상·출고 일정 상담';
 $('stock-note').textContent=(date?date+' 재고 기준. ':'')+(colors.size?(fresh?'아래 색상 조합을 상담할 수 있습니다. 배정·출고 가능 여부는 별도 확인해 주세요.':'지난 자료의 색상 조합입니다. 현재 배정 가능 여부와 출고 일정을 확인해 주세요.'):'원하시는 조합의 배정 가능 차량과 입항 예정 차량을 개별 안내해 드립니다.');
 colors.forEach(name=>{const tag=document.createElement('span');tag.textContent=name.replaceAll('|',' / ');$('stock-colors').append(tag)});
}).catch(()=>{$('stock-note').textContent='재고를 불러오지 못했습니다. 원하시는 색상을 알려주시면 배정 가능 차량과 출고 일정을 안내해 드립니다.'});
if(['mb-hansdream.co.kr','www.mb-hansdream.co.kr','homanhan-glitch.github.io'].includes(location.hostname)){
 const start=()=>{window.dataLayer=window.dataLayer||[];function gtag(){window.dataLayer.push(arguments)}window.gtag=gtag;gtag('js',new Date());gtag('config','G-7T2ECBWN0K',{content_group:'차종별 가이드',model_name:'V-Class'});const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';document.head.append(s)};
 fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>{if(d.ip!=='59.7.219.188')start()}).catch(start);
}
})();
