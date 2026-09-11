const search=document.getElementById('model-search');
if(search)search.addEventListener('input',()=>{const term=search.value.trim().toLowerCase().replace(/[\s-]/g,'');let count=0;document.querySelectorAll('.model-card').forEach(card=>{const match=card.textContent.toLowerCase().replace(/[\s-]/g,'').includes(term);card.hidden=!match;if(match)count++;});document.getElementById('no-results').hidden=count>0;});
const stage=document.querySelector('.brand-stage');
const cinematic=document.querySelector('.cinematic-header');
if(cinematic){const button=cinematic.querySelector('.cinematic-pause');const reduce=matchMedia('(prefers-reduced-motion: reduce)');function setPaused(paused){cinematic.classList.toggle('is-paused',paused);button.textContent=paused?'▶':'Ⅱ';button.setAttribute('aria-label',paused?'배경 움직임 재생':'배경 움직임 일시정지');}setPaused(reduce.matches);button.addEventListener('click',()=>setPaused(!cinematic.classList.contains('is-paused')));reduce.addEventListener('change',()=>setPaused(reduce.matches));}
if(stage){
  const slides=[...stage.querySelectorAll('[data-slide]')],choices=[...stage.querySelectorAll('[data-slide-to]')],pause=document.getElementById('stage-pause');
  const motion=window.matchMedia('(prefers-reduced-motion: reduce)');
  let current=0,paused=motion.matches,timer;
  function show(index){current=index;slides.forEach((slide,i)=>{slide.classList.toggle('is-active',i===index);slide.setAttribute('aria-hidden',String(i!==index));if(slide.tagName==='A')slide.tabIndex=i===index?0:-1;});choices.forEach((button,i)=>button.setAttribute('aria-pressed',String(i===index)));}
  function schedule(){clearInterval(timer);if(!paused&&!document.hidden)timer=setInterval(()=>show((current+1)%slides.length),8000);}
  function sync(){stage.classList.toggle('is-paused',paused);pause.textContent=paused?'▶':'Ⅱ';pause.setAttribute('aria-label',paused?'자동 전환 재생':'자동 전환 일시정지');schedule();}
  choices.forEach(button=>button.addEventListener('click',()=>{show(Number(button.dataset.slideTo));paused=true;sync();}));
  pause.addEventListener('click',()=>{paused=!paused;sync();});
  stage.addEventListener('focusin',()=>clearInterval(timer));
  stage.addEventListener('focusout',()=>{if(!stage.contains(document.activeElement))schedule();});
  stage.addEventListener('mouseenter',()=>clearInterval(timer));stage.addEventListener('mouseleave',schedule);
  document.addEventListener('visibilitychange',schedule);
  motion.addEventListener('change',()=>{paused=motion.matches;sync();});
  sync();
}
