(()=>{
 const search=document.getElementById('model-search');if(!search)return;
 const normal=s=>s.toLowerCase().replace(/마이바흐/g,'maybach').replace(/[\s·-]/g,'');
 search.addEventListener('input',()=>{
  let count=0;const term=normal(search.value.trim());
  document.querySelectorAll('#models .model-card').forEach(card=>{card.hidden=!normal(card.dataset.name+' '+card.textContent).includes(term);if(!card.hidden)count++;});
  document.querySelectorAll('#models .landing-model-group').forEach(g=>g.hidden=![...g.querySelectorAll('.model-card')].some(c=>!c.hidden));
  document.getElementById('no-results').hidden=count>0;
 });
})();
