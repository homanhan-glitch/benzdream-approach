document.querySelectorAll('.edition-color-choice').forEach(choice=>{
  choice.addEventListener('click',()=>{
    const card=choice.closest('.edition-color-card');
    const zoom=card.querySelector('[data-zoom]');
    const img=zoom.querySelector('img');
    const caption=choice.dataset.colorCaption;
    img.src=choice.dataset.colorSrc;
    img.alt=caption;
    zoom.dataset.zoom=choice.dataset.colorSrc;
    zoom.dataset.caption=caption;
    zoom.setAttribute('aria-label',`${caption} 이미지 크게 보기`);
    card.querySelector('figcaption').textContent=choice.dataset.colorNote;
    card.querySelectorAll('.edition-color-choice').forEach(button=>button.setAttribute('aria-pressed',String(button===choice)));
  });
});
