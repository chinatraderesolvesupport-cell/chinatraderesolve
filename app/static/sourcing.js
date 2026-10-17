'use strict';
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
  $('goal').setCustomValidity(alternative&&!$('goal').value.trim()?'Опишите задачу.':'');
  const docs=service.value==='prepare';$('documentFields').hidden=!docs;
  $('documentFields').querySelectorAll('textarea,input').forEach(el=>el.disabled=!docs);
  $('supplier').required=!search;$('supplierHint').textContent=search?'— если есть':'*';
  $('product').required=!unknown;$('productHint').textContent=unknown?'— можно не указывать':'*';
  $('requirements').required=!photo;$('requirements').minLength=photo?0:50;
  const length=$('requirements').value.trim().length;
  $('requirements').setCustomValidity(!photo&&length<50?'Добавьте описание: минимум 50 символов.':'');
  $('requirementsHint').textContent=photo?'— необязательно, есть фото':'* — не менее 50 символов без фото';
  $('counter').textContent=photo?'Можно ориентироваться на фото. Укажите важные отличия, если знаете.':length<50?'Осталось минимум '+(50-length)+' символов.':'Описание заполнено.';
 }
 files.addEventListener('change',()=>{
  urls.forEach(URL.revokeObjectURL);urls=[];$('preview').replaceChildren();
  const selected=Array.from(files.files);let error='';
  if(selected.length>5)error='Выберите не больше 5 фото.';
  else if(selected.some(f=>!['image/jpeg','image/png','image/webp'].includes(f.type)))error='Нужны JPG, PNG или WebP. HEIC преобразуйте в JPG.';
  else if(selected.some(f=>f.size>8*1024*1024))error='Каждое фото должно быть не больше 8 МБ.';
  else if(selected.reduce((n,f)=>n+f.size,0)>25*1024*1024)error='Суммарно — до 25 МБ.';
  files.setCustomValidity(error);$('photoError').textContent=error;
  if(!error)selected.forEach(file=>{const figure=document.createElement('figure'),img=document.createElement('img'),caption=document.createElement('figcaption');const url=URL.createObjectURL(file);urls.push(url);img.src=url;img.alt='Фото товара';caption.textContent=file.name;figure.append(img,caption);$('preview').append(figure);});
  sync();
 });
 $('clearPhotos').addEventListener('click',()=>{files.value='';files.dispatchEvent(new Event('change'));});
 form.addEventListener('input',sync);service.addEventListener('change',sync);
 form.addEventListener('submit',()=>{$('submitButton').disabled=true;$('submitStatus').textContent='Отправляем заявку и фотографии. Дождитесь страницы заявки.';});
 window.addEventListener('pageshow',()=>{$('submitButton').disabled=false;$('submitStatus').textContent='';sync();});
 sync();
}
