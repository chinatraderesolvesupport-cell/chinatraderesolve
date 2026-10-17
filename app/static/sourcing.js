'use strict';
const copy=JSON.parse(document.querySelector('#sourcingCopy')?.textContent||'{}');
const t=key=>copy[key];
const form=document.querySelector('#sourcingForm');
if(form){
 const $=id=>document.getElementById(id),files=$('photos'),service=$('service');let urls=[];
 function sync(){
  const search=service.value==='search',photo=search&&files.files.length>0,unknown=photo&&$('unknown').checked;
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
  $('product').required=!unknown;$('productHint').textContent=unknown?t('optional_name'):'*';
  $('requirements').required=!photo;$('requirements').minLength=photo?0:50;
  const length=$('requirements').value.trim().length;
  $('requirements').setCustomValidity(!photo&&length<50?t('js_min'):'');
  $('requirementsHint').textContent=photo?t('optional_photo'):t('min50');
  $('counter').textContent=photo?t('js_photo'):length<50?t('js_remaining').replace('{n}',50-length):t('js_done');
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
 form.addEventListener('input',sync);service.addEventListener('change',sync);
 form.addEventListener('submit',()=>{$('submitButton').disabled=true;$('submitStatus').textContent=t('js_sending');});
 window.addEventListener('pageshow',()=>{$('submitButton').disabled=false;$('submitStatus').textContent='';sync();});
 sync();
}

// A direct example link should reveal its contents, including on a fresh visit.
function revealSourcingExample(){
 if(window.location.hash!=='#sample-report')return;
 const example=document.getElementById('sample-report');
 if(example){example.open=true;example.scrollIntoView({block:'start'});}
}
window.addEventListener('hashchange',revealSourcingExample);
window.addEventListener('pageshow',revealSourcingExample);
revealSourcingExample();
