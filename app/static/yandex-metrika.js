(() => {
  "use strict";
  const script = document.currentScript;
  const id = script && script.dataset ? script.dataset.counterId : "";
  if (!/^\d{4,20}$/.test(id) || window.ym) return;
  window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
  window.ym.l = Date.now();
  const tag = document.createElement("script");
  tag.async = true;
  tag.src = "https://mc.yandex.ru/metrika/tag.js";
  tag.onload = () => window.ym(Number(id), "init", {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: false
  });
  document.head.appendChild(tag);
})();
