"use strict";
// Daily events only: never read or transmit names, email addresses, descriptions or files.
(()=>{
 const form=document.getElementById('caseForm');
 if(!form?.dataset.statisticsToken)return;
 const sent=new Set(),pending=new Set();let queue=Promise.resolve();
 function metric(event){
  if(sent.has(event)||pending.has(event)||navigator.doNotTrack==='1'||navigator.globalPrivacyControl)return;
  pending.add(event);
  const body=new URLSearchParams({csrf_token:form.dataset.statisticsToken,event});
  queue=queue.then(()=>fetch('/api/dispute-events',{method:'POST',body,credentials:'same-origin',keepalive:true})
   .then(response=>{if(response.ok)sent.add(event);}).catch(()=>{}).finally(()=>pending.delete(event)));
 }
 if('IntersectionObserver' in window){
  new IntersectionObserver(entries=>{if(entries.some(entry=>entry.isIntersecting))metric('open');},{threshold:0.1}).observe(form);
 }
 for(const kind of ['input','change'])form.addEventListener(kind,event=>{if(event.isTrusted)metric('start');});
 form.addEventListener('invalid',event=>{if(event.isTrusted)metric('error');},true);
 const step=document.getElementById('stepTwo');
 if(step)new MutationObserver(()=>{if(step.classList.contains('active'))metric('step2');}).observe(step,{attributes:true,attributeFilter:['class']});
 document.addEventListener('ctr:dispute-attempt',()=>metric('attempt'));
 document.addEventListener('ctr:dispute-error',()=>metric('error'));
 const security=document.getElementById('applicationTurnstileStatus');
 if(security)new MutationObserver(()=>{if(security.dataset.state==='error')metric('error');}).observe(security,{attributes:true,attributeFilter:['data-state']});
})();
