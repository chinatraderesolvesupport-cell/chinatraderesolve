(() => {
  "use strict";
  const script = document.currentScript;
  const id = script && script.dataset ? script.dataset.counterId : "";
  if (!/^\d{4,20}$/.test(id) || window.ym) return;
  window.ym = window.ym || function () { (window.ym.a = window.ym.a || []).push(arguments); };
  window.ym.l = Date.now();
  const counterId = Number(id);
  const sentOnce = new Set();
  const sendGoal = (name, once = false) => {
    const goal = String(name || "").trim().toLowerCase();
    if (!/^[a-z0-9_]{1,64}$/.test(goal)) return;
    if (once && sentOnce.has(goal)) return;
    if (once) sentOnce.add(goal);
    window.ym(counterId, "reachGoal", goal);
  };
  window.ctrMetrikaGoal = sendGoal;
  const tag = document.createElement("script");
  tag.async = true;
  tag.src = "https://mc.yandex.ru/metrika/tag.js";
  tag.onload = () => window.ym(counterId, "init", {
    clickmap: true,
    trackLinks: true,
    accurateTrackBounce: true,
    webvisor: false
  });
  document.head.appendChild(tag);

  document.addEventListener("click", (event) => {
    const target = event.target instanceof Element ? event.target.closest("a,button") : null;
    if (!target) return;
    const explicitGoal = target.dataset ? target.dataset.metrikaGoal : "";
    if (explicitGoal) {
      sendGoal(explicitGoal);
      return;
    }
    if (target.matches('a[href*="#submit"]')) sendGoal("application_cta_click");
    else if (target.matches('a[href^="/support"]')) sendGoal("support_open");
    else if (target.matches('a[href*="/guides/"]')) sendGoal("guide_open");
  }, { capture: true });

  document.addEventListener("ctr:form-engaged", () => sendGoal("application_start", true));
})();
