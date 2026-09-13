/* BenzDream consultation intent. Does not initialize GA or override internal-traffic filtering. */
(() => {
 'use strict';
 if(window.__bdContactTracking || !['mb-hansdream.co.kr','www.mb-hansdream.co.kr','homanhan-glitch.github.io'].includes(location.hostname))return;
 window.__bdContactTracking=true;
 const measurement='G-7T2ECBWN0K';
 const seen=new WeakSet();
 function configured(){return (window.dataLayer||[]).some(entry=>entry&&entry[0]==='config'&&entry[1]===measurement);}
 function emit(payload,attempt=0){
  if(configured()){
   (function(){window.dataLayer.push(arguments);})('event','contact_click',payload);
  }else if(attempt<15)setTimeout(()=>emit(payload,attempt+1),200);
 }
 document.addEventListener('click',event=>{
  if(seen.has(event))return;
  const link=event.target.closest?.('a[href]');if(!link)return;
  let url;try{url=new URL(link.getAttribute('href'),location.href);}catch{return;}
  let method='';
  if(url.protocol==='tel:')method='phone';
  else if(url.hostname==='pf.kakao.com')method=url.pathname.endsWith('/chat')?'kakao_chat':'kakao_channel';
  else if(url.hostname==='forms.gle'&&url.pathname==='/Qmn8ktsg9G2ZWFHY9')method='consultation_form';
  if(!method)return;
  seen.add(event);
  emit({send_to:measurement,contact_method:method,page_path:'/quotes/',link_url:method==='phone'?'tel:':url.origin+url.pathname,button_location:link.closest('header,.bd-site-header,.site-header')?'header':link.closest('footer,.bd-site-footer,.site-footer')?'footer':'body',transport_type:'beacon'});
 },true);
})();
