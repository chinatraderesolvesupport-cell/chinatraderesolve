'use strict';
// Three bounded checks update mail status without reloading access codes or forms.
const mailSection=document.querySelector('#mailStatus');
if(mailSection?.querySelector('[data-mail-pending="yes"]')){
 let check=0;
 const delays=[3000,8000,20000];
 async function updateMail(){
  try{
   const response=await fetch(mailSection.dataset.progressUrl,{credentials:'same-origin',cache:'no-store'});
   if(!response.ok)return;
   const data=await response.json();
   mailSection.querySelectorAll('p').forEach(p=>p.remove());
   for(const mail of data.mail){const p=document.createElement('p');p.textContent=mail.label+': '+mail.text;mailSection.append(p);}
   if(!data.mail.some(mail=>mail.pending))return;
  }catch(error){return;}
  if(check<delays.length)setTimeout(updateMail,delays[check++]);
 }
 setTimeout(updateMail,delays[check++]);
}

// Show completion without reloading a page that may contain unsaved operator edits.
const researchSection=document.querySelector('#research');
if(researchSection&&['queued','running'].includes(researchSection.dataset.state)){
 let attempts=0;
 async function updateResearch(){
  try{
   const response=await fetch(researchSection.dataset.progressUrl,{credentials:'same-origin',cache:'no-store'});
   if(!response.ok)return;
   const data=await response.json();
   const status=researchSection.querySelector('[role="status"]');
   if(status)status.textContent=data.label;
   if(['ready','failed','stale'].includes(data.state)){
    const link=document.createElement('a');link.className='button';link.textContent=data.refresh;
    link.href=location.pathname+location.search+(data.state==='ready'?'#draft-review':'#research');
    researchSection.append(link);return;
   }
   if(!['queued','running'].includes(data.state))return;
  }catch(error){return;}
  if(++attempts<36)setTimeout(updateResearch,20000);
 }
 setTimeout(updateResearch,5000);
}
