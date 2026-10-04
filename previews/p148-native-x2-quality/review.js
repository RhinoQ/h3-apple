
const manifest=JSON.parse(document.getElementById('manifest').textContent),key='p148-review-'+manifest.package_id;
const fields=[...document.querySelectorAll('[data-save]')],out=document.querySelector('#export-status');
let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
const collect=()=>Object.fromEntries(fields.map(e=>[e.id,e.type==='checkbox'?e.checked:e.value]));
const snapshot=()=>JSON.stringify({schema:'p148-labeled-review/v1',review_mode:'non_blind',methods_visible:true,package_id:manifest.package_id,recorded_utc:new Date().toISOString(),methods:manifest.methods,cases:manifest.cases.map(c=>({id:c.id,scope:c.scope})),answers:collect()},null,2);
for(const f of fields){if(f.id in saved){if(f.type==='checkbox')f.checked=saved[f.id];else f.value=saved[f.id]}for(const event of ['input','change'])f.addEventListener(event,()=>{try{localStorage.setItem(key,JSON.stringify(collect()))}catch(e){out.textContent='Local saving is unavailable. Copy your review before leaving.'}})}
for(const section of document.querySelectorAll('section[data-case]')){
 const videos=[...section.querySelectorAll('video')],status=section.querySelector('.status'),sound=section.querySelector('.sound');
 const pause=()=>videos.forEach(v=>v.pause()),audio=()=>videos.forEach((v,i)=>v.muted=i!==Number(sound.value));audio();sound.onchange=audio;
 section.querySelector('.play').onclick=async()=>{document.querySelectorAll('video').forEach(v=>{if(!videos.includes(v))v.pause()});const t=videos[0].ended?0:videos[0].currentTime;audio();try{videos.forEach(v=>v.currentTime=t);await Promise.all(videos.map(v=>v.play()));status.textContent='Playing together with one soundtrack.'}catch(e){if(e.name==='AbortError')return;pause();status.textContent='Use the individual player or original MP4 link.'}};
 section.querySelector('.pause').onclick=()=>{pause();status.textContent='Paused.'};
 section.querySelector('.reset').onclick=()=>{pause();videos.forEach(v=>v.currentTime=0);status.textContent='At the beginning.'};
 section.querySelector('.jump').onclick=()=>{pause();const n=Number(section.querySelector('.seek').value);if(!Number.isFinite(n))return;const t=Math.max(0,Math.min(Number(section.dataset.duration)-1/24,n));videos.forEach(v=>v.currentTime=t);status.textContent='Paused at '+t.toFixed(2)+' s.'};
 videos[0].addEventListener('timeupdate',()=>{if(!videos[0].paused)videos.slice(1).forEach(v=>{if(!v.paused&&Math.abs(v.currentTime-videos[0].currentTime)>.12)v.currentTime=videos[0].currentTime})});
 videos[0].addEventListener('ended',()=>{pause();status.textContent='Playback ended. Mark reviewed only after you have watched both originals.'});
 const detail=section.querySelector('.detail-frame'),img=section.querySelector('.detail-view img'),caption=section.querySelector('.detail-caption'),buttons=[...section.querySelectorAll('.detail-method')];let method='L';
 const update=()=>{img.src='detail/'+section.dataset.case+'-'+method+'-'+detail.value+'.png';img.alt=method+' lossless detail, frame '+detail.selectedOptions[0].dataset.frame;caption.textContent=method+' · '+manifest.methods[method]+' · '+detail.selectedOptions[0].textContent;buttons.forEach(b=>b.setAttribute('aria-pressed',String(b.dataset.method===method)))};
 buttons.forEach(b=>b.onclick=()=>{method=b.dataset.method;update()});detail.onchange=update;
}
const box=document.querySelector('#json-box'),raw=document.querySelector('#review-json');
const show=()=>{box.hidden=false;raw.value=snapshot();raw.focus();raw.select()};
document.querySelector('#show-json').onclick=show;
document.querySelector('#copy').onclick=async()=>{try{await navigator.clipboard.writeText(snapshot());out.textContent='Copied. Paste the review into the chat.'}catch(e){show();out.textContent='Select and copy the text below.'}};
document.querySelector('#export').onclick=()=>{const u=URL.createObjectURL(new Blob([snapshot()],{type:'application/json'}));const a=document.createElement('a');a.href=u;a.download='p148-'+manifest.package_id+'-review.json';a.click();setTimeout(()=>URL.revokeObjectURL(u),10000);out.textContent='Download requested. You can also copy the review text.'};
