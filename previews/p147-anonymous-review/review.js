
const packageId=document.body.dataset.package,key='p147-review-'+packageId;
const fields=[...document.querySelectorAll('[data-save]')];
const output=document.querySelector('#export-status');
let saved={};try{saved=JSON.parse(localStorage.getItem(key)||'{}')}catch(e){}
function collect(){return Object.fromEntries(fields.map(e=>[e.id,e.type==='checkbox'?e.checked:e.value]))}
function snapshot(){return JSON.stringify({schema:'p147-anonymous-review/v1',package_id:packageId,review_set:document.body.dataset.set,recorded_utc:new Date().toISOString(),answers:collect()},null,2)}
function save(){try{localStorage.setItem(key,JSON.stringify(collect()))}catch(e){output.textContent='Local saving is unavailable. Copy or download your review before leaving.'}}
for(const e of fields){if(e.id in saved){if(e.type==='checkbox')e.checked=saved[e.id];else e.value=saved[e.id]}e.addEventListener('input',save);e.addEventListener('change',save)}
for(const section of document.querySelectorAll('section[data-duration]')){
 const videos=[...section.querySelectorAll('video')],sound=section.querySelector('.sound'),status=section.querySelector('.status');
 const audio=()=>videos.forEach((v,i)=>v.muted=i!==Number(sound.value));audio();sound.onchange=audio;
 const pause=()=>videos.forEach(v=>v.pause());
 section.querySelector('.play').onclick=async()=>{document.querySelectorAll('video').forEach(v=>{if(!videos.includes(v))v.pause()});const t=videos[0].ended?0:videos[0].currentTime;audio();try{videos.forEach(v=>v.currentTime=t);await Promise.all(videos.map(v=>v.play()));status.textContent='Playing together. Only the selected sample has sound.'}catch(e){pause();status.textContent='This browser could not play the group. Use Listen to this sample or the original MP4 link.'}};
 section.querySelector('.pause').onclick=()=>{pause();status.textContent='Paused.'};
 section.querySelector('.reset').onclick=()=>{pause();videos.forEach(v=>v.currentTime=0);status.textContent='At the beginning.'};
 section.querySelector('.jump').onclick=()=>{pause();const n=Number(section.querySelector('.seek').value);if(!Number.isFinite(n))return;const t=Math.max(0,Math.min(Number(section.dataset.duration)-1/24,n));videos.forEach(v=>v.currentTime=t);status.textContent='Paused at '+t.toFixed(2)+' s.'};
 section.querySelectorAll('.listen').forEach((button,i)=>button.onclick=async()=>{document.querySelectorAll('video').forEach(v=>v.pause());sound.value=String(i);audio();const v=videos[i];if(v.ended)v.currentTime=0;try{await v.play();status.textContent='Playing sample '+button.dataset.label+' with its original sound.'}catch(e){status.textContent='Use the video controls or original MP4 link to play this sample.'}});
 videos[0].addEventListener('timeupdate',()=>{if(!videos[0].paused)videos.slice(1).forEach(v=>{if(!v.paused&&Math.abs(v.currentTime-videos[0].currentTime)>.15)v.currentTime=videos[0].currentTime})});
 videos[0].addEventListener('ended',()=>{pause();status.textContent='Playback ended. Mark watching and listening only if you actually completed them.'});
 for(const v of videos)v.addEventListener('error',()=>status.textContent='A video could not load. Try its original MP4 link.');
}
const raw=document.querySelector('#review-json'),rawBox=document.querySelector('#json-box');
function show(text){rawBox.hidden=false;raw.value=text;raw.focus();raw.select()}
document.querySelector('#show-json').onclick=()=>{show(snapshot());output.textContent='Select and copy this text, then paste it in the chat.'};
document.querySelector('#copy').onclick=async()=>{const text=snapshot();try{await navigator.clipboard.writeText(text);output.textContent='Review copied. Paste it in the chat.'}catch(e){show(text);output.textContent='Automatic copy is unavailable. Select and copy the text below.'}};
document.querySelector('#export').onclick=()=>{const url=URL.createObjectURL(new Blob([snapshot()],{type:'application/json'}));const a=document.createElement('a');a.href=url;a.download='p147-'+document.body.dataset.set+'-'+packageId+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),10000);output.textContent='Download requested. You can also copy the review text and paste it in the chat.'};
