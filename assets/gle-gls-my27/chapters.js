(()=>{'use strict';
const menu=document.querySelector('.menu-toggle'),nav=document.querySelector('.global-nav');
menu.addEventListener('click',()=>{const open=menu.getAttribute('aria-expanded')!=='true';menu.setAttribute('aria-expanded',String(open));nav.classList.toggle('open',open)});
document.querySelectorAll('[data-hero]').forEach(b=>b.addEventListener('click',()=>{const gls=b.dataset.hero==='gls';const i=document.querySelector('.hero-photo>img');i.src=`assets/gle-gls-my27/${gls?'gls':'gle'}-hero.jpg`;i.alt=gls?'신형 GLS의 전면과 측면':'신형 GLE SUV의 전면과 측면';document.querySelector('#hero-caption').textContent=gls?'THE NEW GLS':'THE NEW GLE';document.querySelectorAll('[data-hero]').forEach(x=>x.setAttribute('aria-pressed',String(x===b)))}));
const data=JSON.parse(document.querySelector('#color-data').textContent);
document.querySelectorAll('[data-color-group]').forEach(group=>{
 const model=data[group.dataset.colorGroup],label=group.dataset.modelLabel;
 group.querySelectorAll('[data-color]').forEach(button=>button.addEventListener('click',()=>{
  const color=model.seats[Number(button.dataset.color)];
  for(const [selector,file,width,height,view] of [['.color-front',color.image,color.width,color.height,'앞좌석'],['.color-rear',color.rearImage,color.rearWidth,color.rearHeight,'뒷좌석']]){
   const image=group.querySelector(selector);image.src='assets/gle-gls-my27/'+file;image.width=width;image.height=height;image.alt=label+' '+color.name+' '+view+(view==='뒷좌석'&&group.dataset.colorGroup==='gls'?' · 7인승 예시':'');
  }
  group.querySelector('.selected-color').textContent=label+' · '+color.material+' · '+color.name;
  group.querySelectorAll('[data-color]').forEach(b=>b.setAttribute('aria-pressed',String(b===button)));
 }));
});
const chapterNav=document.querySelector('.chapter-nav'),picker=document.querySelector('#chapter-picker');
const chapters=[...document.querySelectorAll('.chapter-block')];
new ResizeObserver(()=>document.documentElement.style.setProperty('--chapter-offset',(chapterNav.offsetHeight+14)+'px')).observe(chapterNav);
picker.addEventListener('change',()=>{
 const target=document.getElementById(picker.value);if(!target)return;
 history.pushState(null,'','#'+picker.value);target.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
});
let scheduled=false;
function activeChapter(){scheduled=false;let current='lineup';const offset=chapterNav.offsetHeight+35;for(const section of chapters){if(section.getBoundingClientRect().top<=offset)current=section.id;else break}picker.value=current;document.querySelectorAll('[data-nav-chapter]').forEach(a=>{if(a.dataset.navChapter===current)a.setAttribute('aria-current','true');else a.removeAttribute('aria-current')})}
addEventListener('scroll',()=>{if(!scheduled){scheduled=true;requestAnimationFrame(activeChapter)}},{passive:true});addEventListener('resize',activeChapter);activeChapter();
// The site analytics configuration remains inactive in file/localhost previews.
if(['mb-hansdream.co.kr','www.mb-hansdream.co.kr','homanhan-glitch.github.io'].includes(location.hostname)){
 const start=()=>{window.dataLayer=window.dataLayer||[];function gtag(){window.dataLayer.push(arguments)}window.gtag=gtag;gtag('js',new Date());gtag('config','G-7T2ECBWN0K',{content_group:'신차 사전계약'});const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';document.head.append(s)};
 fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>{if(d.ip!=='59.7.219.188')start()}).catch(start);
}
})();
