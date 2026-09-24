// One shared navigation behavior; no changes to vehicle controls or analytics.
(() => {
  const links = [...document.querySelectorAll('.vehicle-jump')];
  const targets = links.map(a => document.querySelector(a.getAttribute('href'))).filter(Boolean);
  const header = document.querySelector('.site-header');
  const nav = document.querySelector('.nav');
  const resize = () => {
    nav.style.top = `${header.getBoundingClientRect().height}px`;
    const offset = header.getBoundingClientRect().height + nav.getBoundingClientRect().height + 16;
    document.documentElement.style.scrollPaddingTop = `${offset}px`;
    document.querySelectorAll('section[id]').forEach(section => { section.style.scrollMarginTop = '0px'; });
  };
  new ResizeObserver(resize).observe(header);
  resize();
  const update = () => {
    const offset = header.getBoundingClientRect().height + nav.getBoundingClientRect().height + 60;
    const current = targets.filter(x => x.getBoundingClientRect().top <= offset).sort((a,b) => b.getBoundingClientRect().top-a.getBoundingClientRect().top)[0];
    links.forEach(a => {
      const active = current && a.getAttribute('href') === `#${current.id}`;
      a.classList.toggle('is-current',!!active);
      if(active) a.setAttribute('aria-current','location'); else a.removeAttribute('aria-current');
    });
  };
  window.addEventListener('scroll', update, {passive:true});
  update();
})();
