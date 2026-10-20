"use strict";
// Reading is plain document flow. Editing grows with the actual text, including pasted reports.
const editor=document.getElementById('draftEditor');
function growReportFields(){
 if(!editor?.open)return;
 editor.classList.add('auto-grow');
 editor.querySelectorAll('textarea').forEach(field=>{field.style.height='auto';field.style.height=(field.scrollHeight+4)+'px';});
}
editor?.addEventListener('toggle',growReportFields);
editor?.addEventListener('input',growReportFields);
window.addEventListener('resize',growReportFields);
window.addEventListener('pageshow',growReportFields);
if(document.fonts)document.fonts.ready.then(growReportFields);
growReportFields();
