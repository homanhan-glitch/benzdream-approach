(() => {
  if (!['mb-hansdream.co.kr','www.mb-hansdream.co.kr'].includes(location.hostname) || window.__bdQuoteAnalytics) return;
  window.__bdQuoteAnalytics = true;
  window.dataLayer = window.dataLayer || [];
  window.gtag = window.gtag || function(){window.dataLayer.push(arguments);};
  let initialized = false;
  function initialize(){
    if (initialized) return;
    initialized = true;
    const script = document.createElement('script');
    script.async = true;
    script.src = 'https://www.googletagmanager.com/gtag/js?id=G-7T2ECBWN0K';
    document.head.appendChild(script);
    gtag('js', new Date());
    gtag('config','G-7T2ECBWN0K', {content_group:'견적서',page_title:'BenzDream 견적서',page_location:'https://mb-hansdream.co.kr/quotes/',page_referrer:'',ignore_referrer:true});
  }
  fetch('https://api.ipify.org?format=json').then(r=>r.json()).then(d=>{
    if (['59.7.219.188'].includes(d.ip)) return;
    initialize();
  }).catch(initialize);
})();
