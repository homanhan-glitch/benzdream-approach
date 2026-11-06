(()=>{'use strict';
const menu=document.querySelector('.menu-toggle'),nav=document.querySelector('.global-nav');
menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('open',open)});
document.querySelectorAll('[data-hero]').forEach(b=>b.addEventListener('click',()=>{const gls=b.dataset.hero==='gls';const i=document.querySelector('.hero-photo>img');i.src=`assets/gle-gls-my27/${gls?'gls':'gle'}-hero.jpg`;i.alt=gls?'신형 GLS의 전면과 측면':'신형 GLE SUV의 전면과 측면';document.querySelector('#hero-caption').textContent=gls?'THE NEW GLS':'THE NEW GLE';document.querySelectorAll('[data-hero]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))}));
const data=JSON.parse(document.querySelector('#color-data').textContent);let model='gle';
function seat(index){
 const d=data[model],s=d.seats[index];
 const front=document.querySelector('.seat-image'),rear=document.querySelector('.seat-rear-image');
 front.src='assets/gle-gls-my27/'+s.image;
 front.alt=d.label+' '+s.name+' '+s.material+' 앞좌석';
 front.width=s.width;front.height=s.height;
 rear.src='assets/gle-gls-my27/'+s.rearImage;
 rear.alt=d.label+' '+s.name+' '+s.material+' 뒷좌석'+(model==='gls'?' · 7인승 예시':'');
 rear.width=s.rearWidth;rear.height=s.rearHeight;
 document.querySelector('#seat-rear-caption').textContent=model==='gls'?'뒷좌석 · 7인승 색상 예시':'뒷좌석';
 document.querySelector('#seat-label').textContent=d.label+' · '+s.material+' · '+s.name;
 document.querySelectorAll('[data-seat]').forEach(b=>b.setAttribute('aria-pressed',String(Number(b.dataset.seat)===index)));
}
function choose(key){model=key;const d=data[key];document.querySelector('.paint-solid').src='assets/gle-gls-my27/'+d.exterior;document.querySelector('.paint-metallic').src='assets/gle-gls-my27/'+d.metallic;document.querySelector('.paint-solid').alt=(key==='gls'?'GLS':'GLE 쿠페')+' 솔리드 외장 색상 예시';document.querySelector('.paint-metallic').alt=(key==='gls'?'GLS':'GLE 쿠페')+' 메탈릭 외장 색상 예시';document.querySelector('#exterior-caption').textContent=d.exteriorCaption;document.querySelector('#interior-title').textContent=d.label+'의 실내';const box=document.querySelector('#seat-buttons');box.replaceChildren();d.seats.forEach((s,i)=>{const b=document.createElement('button');b.textContent=s.name;b.dataset.seat=i;b.addEventListener('click',()=>seat(i));box.append(b)});document.querySelectorAll('[data-model]').forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.model===key)));seat(0)}
document.querySelectorAll('[data-model]').forEach(b=>b.addEventListener('click',()=>choose(b.dataset.model)));choose('gle');
// Keep local previews out of production analytics; retain the site's internal-IP exclusion.
if(['mb-hansdream.co.kr','www.mb-hansdream.co.kr','homanhan-glitch.github.io'].includes(location.hostname)){
 const start=()=>{window.dataLayer=window.dataLayer||[];function gtag(){window.dataLayer.push(arguments)}window.gtag=gtag;gtag('js',new Date());gtag('config','G-7T2ECBWN0K',{content_group:'신차 사전계약'});const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';document.head.append(s)};
 fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>{if(d.ip!=='59.7.219.188')start()}).catch(start);
}
})();
