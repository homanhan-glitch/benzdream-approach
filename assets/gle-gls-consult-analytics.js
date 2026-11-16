(()=>{
if(['mb-hansdream.co.kr','www.mb-hansdream.co.kr','homanhan-glitch.github.io'].includes(location.hostname)){
 const start=()=>{window.dataLayer=window.dataLayer||[];function gtag(){window.dataLayer.push(arguments)}window.gtag=gtag;gtag('js',new Date());gtag('config','G-7T2ECBWN0K',{content_group:'신차 사전계약'});const s=document.createElement('script');s.async=true;s.src='https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';document.head.append(s)};
 fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>{if(d.ip!=='59.7.219.188')start()}).catch(start);
}

})();
