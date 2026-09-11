const edHeader=document.querySelector('.ed-header');
const edSubnav=document.querySelector('.ed-subnav');
function edOffsets(){document.documentElement.style.setProperty('--ed-header',`${edHeader.offsetHeight}px`);document.documentElement.style.setProperty('--ed-subnav',`${edSubnav.offsetHeight}px`);}
new ResizeObserver(edOffsets).observe(edHeader);new ResizeObserver(edOffsets).observe(edSubnav);edOffsets();
const edMenu=document.querySelector('.ed-mobile-menu');
edMenu.querySelectorAll('a').forEach(a=>a.addEventListener('click',()=>{edMenu.open=false;}));
document.addEventListener('click',e=>{if(!edMenu.contains(e.target))edMenu.open=false;});
document.addEventListener('keydown',e=>{if(e.key==='Escape'&&edMenu.open){edMenu.open=false;edMenu.querySelector('summary').focus();}});
const edDialog=document.getElementById('ed-lightbox');
document.querySelectorAll('[data-zoom]').forEach(button=>button.addEventListener('click',()=>{edDialog.querySelector('img').src=button.dataset.zoom;edDialog.querySelector('img').alt=button.dataset.caption;edDialog.querySelector('p').textContent=button.dataset.caption;edDialog.showModal();}));
edDialog.querySelector('.close-lightbox').addEventListener('click',()=>edDialog.close());
edDialog.addEventListener('click',e=>{if(e.target===edDialog){const r=edDialog.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)edDialog.close();}});
const edPanorama=document.querySelector('.ed-panorama');const edPause=document.querySelector('.ed-motion');const edReduced=matchMedia('(prefers-reduced-motion: reduce)');
function edSetPaused(paused){edPanorama.classList.toggle('is-paused',paused);edPause.textContent=paused?'▶':'Ⅱ';edPause.setAttribute('aria-label',paused?'배경 움직임 재생':'배경 움직임 일시정지');}
edSetPaused(edReduced.matches);edPause.addEventListener('click',()=>edSetPaused(!edPanorama.classList.contains('is-paused')));edReduced.addEventListener('change',()=>edSetPaused(edReduced.matches));
const edLinks=[...edSubnav.querySelectorAll('a')];let edFrame=false;
function edActive(){let active=edLinks[0];const offset=edHeader.offsetHeight+edSubnav.offsetHeight+90;for(const a of edLinks){const s=document.querySelector(a.getAttribute('href'));if(s&&s.getBoundingClientRect().top<=offset)active=a;}for(const a of edLinks){a.classList.toggle('active',a===active);if(a===active)a.setAttribute('aria-current','location');else a.removeAttribute('aria-current');}edFrame=false;}
document.addEventListener('scroll',()=>{if(!edFrame){edFrame=true;requestAnimationFrame(edActive);}},{passive:true});edActive();
