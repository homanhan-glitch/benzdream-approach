// Enable only after a successful Apps Script deployment and end-to-end test.
// Set the verified /exec URL here. This file is NOT in the public release yet.
(()=>{'use strict';
const endpoint='https://script.google.com/macros/s/AKfycbwAzETA4AJ3M7w33LgpfaMEK6m98r6T2zUZSiLR5f1LA2BLOi4he2CddiYLH9DI9oUt/exec';
if(!/^https:\/\/script\.google\.com\/macros\/s\/[A-Za-z0-9_-]+\/exec$/.test(endpoint))return;
const form=document.getElementById('request'),button=document.getElementById('submit'),status=document.getElementById('status');
let pending=false,requestId='',timer,lastPayload='';
button.disabled=false;button.textContent='사전예약 상담 신청하기';
form.addEventListener('submit',async e=>{e.preventDefault();e.stopImmediatePropagation();if(pending||!form.reportValidity())return;
const phone=document.getElementById('phone').value.replace(/\D/g,'');if(!/^0\d{8,10}$/.test(phone)){status.textContent='연락처를 확인해 주세요.';return;}
const fingerprint=JSON.stringify(['model','exterior','interior','name'].map(id=>document.getElementById(id).value).concat(phone));
if(fingerprint!==lastPayload){requestId='';lastPayload=fingerprint;}
requestId=requestId||crypto.randomUUID();pending=true;button.disabled=true;status.textContent='신청 내용을 접수하고 있습니다.';
const values={responseFormat:"json",requestId,model:document.getElementById('model').value,exterior:document.getElementById('exterior').value,interior:document.getElementById('interior').value,name:document.getElementById('name').value.trim(),phone,consent:'yes',consentVersion:'2026-11-16-v1',website:''};
try{
const response=await fetch(endpoint,{method:'POST',body:new URLSearchParams(values),credentials:'omit',redirect:'follow',signal:AbortSignal.timeout(30000)});
const data=await response.json();
if(!response.ok||data.type!=='benzdream-intake'||data.requestId!==requestId||data.ok!==true)throw new Error('unconfirmed');
status.textContent='상담 신청이 접수되었습니다. 입력하신 연락처로 안내드리겠습니다.';button.textContent='접수 완료';button.disabled=true;document.getElementById('name').value='';document.getElementById('phone').value='';document.getElementById('consent').checked=false;window.gtag?.('event','generate_lead',{content_group:'GLE GLS 사전예약',model_id:values.model,method:'website_form'});
}catch(error){button.disabled=false;status.textContent='접수 결과를 확인하지 못했습니다. 다시 시도하거나 전화로 문의해 주세요. 같은 신청은 중복 저장되지 않습니다.';}finally{pending=false;}
},true);
})();
