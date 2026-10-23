'use strict';
const copy=JSON.parse(document.querySelector('#sourcingCopy')?.textContent||'{}');
const t=key=>copy[key];
const form=document.querySelector('#sourcingForm');
if(form){
 const $=id=>document.getElementById(id),files=$('photos'),service=$('service');let urls=[],lastService=null;
 function sync(){
  const check=service.value==='check',search=service.value==='search',photo=files.files.length>0,unknown=search&&photo&&$('unknown').checked;
  if(lastService!==service.value){$('purchaseFields').open=!check;lastService=service.value;}
  $('checkPreview').hidden=!check;$('clearPhotos').hidden=!photo;
  $('sampleLink').href=check?'#checkExample':'#sample-report';$('sampleLink').textContent=t(check?'check_example_title':'u_sample_link');
  $('purchaseSummary').textContent=t(check?'purchase_optional':'purchase_details');
  $('serviceHeadline').textContent=t(check?'check_headline':'headline');
  $('serviceLead').textContent=t(check?'check_lead':'lead');
  $('submitButton').textContent=t(check?'check_submit':'submit');
  for(const id of ['quantity','destination']){$(id).required=!check;$(id+'Hint').textContent=check?t('optional'):'*';}
  $('searchFields').hidden=!search;
  $('searchFields').querySelectorAll('input,select').forEach(el=>el.disabled=!search);
  const alternative=search&&$('alternatives').checked;
  $('alternativeFields').hidden=!alternative;
  $('alternativeFields').querySelectorAll('textarea').forEach(el=>el.disabled=!alternative);
  $('goal').required=alternative;
  $('goal').setCustomValidity(alternative&&!$('goal').value.trim()?t('js_goal'):'');
  const docs=service.value==='prepare';$('documentFields').hidden=!docs;
  $('documentFields').querySelectorAll('textarea,input').forEach(el=>el.disabled=!docs);
  $('supplier').required=!search;$('supplierHint').textContent=search?t('optional'):'*';
  $('product').required=!check&&!unknown;$('productHint').textContent=check?t('optional'):unknown?t('optional_name'):'*';
  $('requirements').required=!check&&!photo;$('requirements').minLength=check||photo?0:50;
  $('requirementsLabel').textContent=check?t('check_question'):copy.requirements;
  const length=$('requirements').value.trim().length;
  $('requirements').setCustomValidity(!check&&!photo&&length<50?t('js_min'):'');
  $('requirementsHint').textContent=check?t('optional'):photo?t('optional_photo'):t('min50');
  $('counter').textContent=check?'':photo?t('js_photo'):length<50?t('js_remaining').replace('{n}',50-length):t('js_done');
 }
 files.addEventListener('change',()=>{
  urls.forEach(URL.revokeObjectURL);urls=[];$('preview').replaceChildren();
  const selected=Array.from(files.files);let error='';
  if(selected.length>5)error=t('js_count');
  else if(selected.some(f=>!['image/jpeg','image/png','image/webp'].includes(f.type)))error=t('js_format');
  else if(selected.some(f=>f.size>8*1024*1024))error=t('js_size');
  else if(selected.reduce((n,f)=>n+f.size,0)>25*1024*1024)error=t('js_total');
  files.setCustomValidity(error);$('photoError').textContent=error;
  if(!error)selected.forEach(file=>{const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');const url=URL.createObjectURL(file);urls.push(url);img.src=url;img.alt=t('photo_alt');caption.textContent=file.name;figure.append(img,caption);$('preview').append(figure);});
  sync();
 });
 $('clearPhotos').addEventListener('click',()=>{files.value='';files.dispatchEvent(new Event('change'));});
 // A completed request marks the event sent. Network failures can retry on the next interaction.
 const counted=new Set(),pending=new Set();
 function metric(event){
  if(counted.has(event)||pending.has(event)||navigator.doNotTrack==='1'||navigator.globalPrivacyControl)return;
  pending.add(event);
  const body=new URLSearchParams({csrf_token:form.elements.namedItem('csrf_token').value,event});
  fetch('/sourcing/form-start',{method:'POST',body,credentials:'same-origin',keepalive:true})
   .then(response=>{if(response.ok)counted.add(event);}).catch(()=>{}).finally(()=>pending.delete(event));
 }
 function started(event){if(event.isTrusted)metric('start');}
 form.addEventListener('input',started);form.addEventListener('change',started);
 form.addEventListener('invalid',event=>{
  if(!event.isTrusted)return;
  metric('invalid');$('validationStatus').hidden=false;
  event.target.setAttribute('aria-invalid','true');
  const details=event.target.closest('details');if(details)details.open=true;
 },true);
 form.addEventListener('input',event=>{
  if(event.target.matches('input,textarea,select')&&event.target.validity.valid)event.target.removeAttribute('aria-invalid');
  if(!form.querySelector('[aria-invalid="true"]'))$('validationStatus').hidden=true;
 });
 form.addEventListener('input',sync);service.addEventListener('change',sync);
 form.addEventListener('submit',()=>{$('submitButton').disabled=true;$('submitStatus').textContent=t('js_sending');});
 window.addEventListener('pageshow',()=>{$('submitButton').disabled=false;$('submitStatus').textContent='';sync();});
 sync();metric('interactive');
}

// A direct example link should reveal its contents, including on a fresh visit.
function revealSourcingExample(){
 if(!['#sample-report','#checkExample'].includes(window.location.hash))return;
 const example=document.getElementById(window.location.hash.slice(1));
 if(example){example.open=true;example.scrollIntoView({block:'start'});}
}
window.addEventListener('hashchange',revealSourcingExample);
window.addEventListener('pageshow',revealSourcingExample);
revealSourcingExample();

// Translate an open request in place. Do not store drafts or move file/CAPTCHA controls.
if(form){
 let changingLanguage=false;
 function translateTree(current,incoming){
  if(!current||!incoming||current.nodeType!==incoming.nodeType)return;
  if(current.nodeType===Node.TEXT_NODE){current.textContent=incoming.textContent;return;}
  if(current.nodeType!==Node.ELEMENT_NODE)return;
  if(current.id==='preview'||current.id==='sourcingCopy'||current.matches('.cf-turnstile,iframe,script'))return;
  if(current.matches('input,textarea')){
   if(incoming.hasAttribute('placeholder'))current.setAttribute('placeholder',incoming.getAttribute('placeholder'));
   return;
  }
  if(current.tagName==='SELECT'){
   Array.from(current.options).forEach(option=>{const translated=Array.from(incoming.options).find(other=>other.value===option.value);if(translated)option.textContent=translated.textContent;});return;
  }
  for(const name of ['href','lang','aria-label','aria-current']){
   if(incoming.hasAttribute(name))current.setAttribute(name,incoming.getAttribute(name));
   else if(current.hasAttribute(name))current.removeAttribute(name);
  }
  Array.from(current.childNodes).forEach((child,index)=>translateTree(child,incoming.childNodes[index]));
 }
 document.addEventListener('click',async event=>{
  const link=event.target.closest('.languages a');
  if(!link||event.button!==0||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey)return;
  event.preventDefault();if(changingLanguage)return;changingLanguage=true;
  try{
   const url=new URL(link.href);url.hash=location.hash;url.searchParams.set('service',form.elements.namedItem('service').value);
   const response=await fetch(url,{credentials:'same-origin'});
   if(!response.ok)throw new Error('language response');
   const incoming=new DOMParser().parseFromString(await response.text(),'text/html');
   if(!incoming.querySelector('#sourcingForm'))throw new Error('missing form');
   const nextCopy=JSON.parse(incoming.querySelector('#sourcingCopy').textContent);
   for(const selector of ['header','.languages','main','footer'])translateTree(document.querySelector(selector),incoming.querySelector(selector));
   for(const name of ['csrf_token','submission'])form.elements.namedItem(name).value=incoming.querySelector('#sourcingForm').elements.namedItem(name).value;
   Object.assign(copy,nextCopy);document.documentElement.lang=incoming.documentElement.lang;document.title=incoming.title;
   history.replaceState(null,'',url);form.dispatchEvent(new Event('input'));
   document.getElementById('submitStatus').textContent='';
  }catch(error){document.getElementById('submitStatus').textContent=t('js_language_error');}
  finally{changingLanguage=false;}
 });
}
const feedbackForm=document.querySelector('[data-feedback-form]');
if(feedbackForm){
 const kind=feedbackForm.querySelector('[name="kind"]');
 function syncFeedback(){
  const review=kind.value==='review';
  feedbackForm.querySelectorAll('.review-only').forEach(group=>{group.hidden=!review;group.querySelectorAll('input,select').forEach(control=>{control.disabled=!review;if(!review){if(control.type==='checkbox')control.checked=false;else control.value='';}});});
 }
 kind.addEventListener('change',syncFeedback);syncFeedback();
}
