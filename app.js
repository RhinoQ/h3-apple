'use strict';
const data = window.BENCHMARK, scores = window.SCORES;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dimensions = {action:'Action', count:'Subject / object count', detail:'Detail', framing:'Framing', geometry:'Geometry', identity:'Identity', temporal:'Temporal'};
const routes = {V768:'VSA · Standard 768p', S768:'SOL · Standard 768p', VX:'VSA · Fast 544p + X2', SX:'SOL · Fast 544p + X2'};
const statusNames = {pass:'Pass', fail:'Fail', borderline:'Borderline', unrated:'Awaiting review', pending:'Awaiting generation'};
let selected = location.hash.startsWith('#case=') ? decodeURIComponent(location.hash.slice(6)) : data.cases[0]?.id;
let noticeTimer;

function notice(message) {
  $('notice').textContent = message;
  $('notice').style.display = 'block';
  clearTimeout(noticeTimer);
  noticeTimer = setTimeout(() => $('notice').style.display = 'none', 4000);
}
async function copy(value) {
  try { await navigator.clipboard.writeText(value); notice('Copied'); }
  catch { notice('Clipboard unavailable. Select and copy the text.'); }
}
function renderScores() {
  $('version').textContent = 'v' + data.version;
  const rows = data.cases.flatMap(c => c.runs), complete = rows.filter(r => r.video).length;
  $('inventory').textContent = `${data.cases.length} / ${rows.length}`;
  $('unique-videos').textContent = `${complete} freshly generated · ${rows.length - complete} pending`;
  $('scope').textContent = data.method.scope;
  $('source').textContent = `Product 0.7.0 · ${data.primary.product_commit} · Dataset ${data.version} · ${data.date}`;
  if (data.download_url) { $('download-bundle').href = data.download_url; $('download-bundle').hidden = false; }
  if (!scores) {
    $('scores').innerHTML = '<p class="empty">Generation and evaluation in progress. Final scores appear only after every registered result has been reviewed.</p>';
    $('scored-tables').hidden = true;
    $('score-download').hidden = true;
    return;
  }
  $('scores').innerHTML = Object.entries(scores.modes).map(([mode,s]) => `<div class="score-card"><h3>${mode}</h3><div class="value">${s.score.toFixed(0)}<small> / 100</small></div><p>${s.confirmed_passes} / ${s.total} confirmed passes · ${scores.coverage.cases} cases at two profiles</p></div>`).join('');
  $('routes').innerHTML = Object.entries(scores.routes).map(([arm,s]) => `<tr><td>${routes[arm]}</td><td><strong>${s.score.toFixed(0)}%</strong></td><td>${s.confirmed_passes} / ${s.total}${s.counts.borderline ? ` (${s.counts.borderline} borderline)` : ''}</td><td>${s.median_seconds.toFixed(1)} s</td><td>${s.physical_gib_range ? s.physical_gib_range.map(n => n.toFixed(1)).join('–') + ' GiB' : 'Not recorded'}</td></tr>`).join('');
  $('quality').innerHTML = Object.entries(dimensions).map(([key,name]) => `<tr><td>${name}</td>${['VSA','SOL'].map(mode => { const q = scores.modes[mode].quality[key]; return `<td>${q ? q.no_major_defect_percent.toFixed(0) + '% · ' + q.none_or_minor + '/' + q.evaluated : 'Unrated'}</td>`; }).join('')}</tr>`).join('');
  $('paired-time').textContent = 'Paired median time ratios (baseline / candidate, >1 means faster): ' + Object.values(scores.paired_time).map(p => `${p.baseline} / ${p.candidate}: ${p.median_speedup.toFixed(2)}×`).join(' · ') + '. One run per slot.';
}
function filtered() {
  const query = $('search').value.toLowerCase().trim();
  return data.cases.filter(c => (!query || [c.id,c.title,c.category,c.prompt_text].join(' ').toLowerCase().includes(query))
    && (!$('category').value || c.category === $('category').value)
    && (!$('orientation').value || c.aspect_ratio === $('orientation').value)
    && (!$('status').value || c.runs.some(r => r.review.status === $('status').value)));
}
function filters() {
  const cases = filtered();
  $('match-count').textContent = `${cases.length} matching cases. Each retains all four routes; filters do not change the score.`;
  if (!cases.some(c => c.id === selected)) {
    selected = cases[0]?.id;
    if (selected) history.replaceState(null,'','#case=' + encodeURIComponent(selected));
  }
  renderList(cases); renderCase();
}
function renderList(cases) {
  $('case-list').replaceChildren();
  for (const c of cases) {
    const button = document.createElement('button');
    button.className = 'case-link';
    button.setAttribute('aria-current', String(c.id === selected));
    button.innerHTML = `<img src="${esc(c.references[0].path)}" alt="" loading="lazy"><strong>${esc(c.title)}</strong><span>${esc(c.category)} · ${esc(c.aspect_ratio)} · 5 s</span>`;
    button.onclick = () => { selected = c.id; history.replaceState(null,'','#case=' + encodeURIComponent(c.id)); renderList(cases); renderCase(); };
    $('case-list').append(button);
  }
}
function reviewDetails(run, criteria) {
  const review = run.review;
  if (!run.video) return '<p class="small">Registered input and seed are frozen. This output has not been generated yet.</p>';
  return `<p class="summary">${esc(review.excerpt_en || review.summary || 'Awaiting visual review.')}</p>
    <details><summary>Judgments and frame evidence</summary>
    <ol>${criteria.map((text,i) => { const vote = review.criteria_pass[i]; return `<li><strong>${vote === true ? 'Pass' : vote === false ? 'Fail' : 'Uncertain'}</strong> — ${esc(text)}</li>`; }).join('')}</ol>
    <ul>${review.observations.map(o => `<li><strong>${o.interval_seconds.map(t => Number(t).toFixed(2)).join('–')} s</strong> — ${esc(o.text)}</li>`).join('')}</ul>
    <p class="small">${esc(review.review_scope)}</p>
    <p class="small">Severity (0 none · 1 minor · 2 clear · 3 severe): ${Object.entries(review.severity).map(([key,value]) => `${dimensions[key]} ${value}`).join(' · ')}</p>
    <ul>${[...run.sources,...(review.records || [])].map((s,i) => `<li><a href="${esc(s.path)}" target="_blank" rel="noopener">Evidence ${i+1} ↗</a> · ${esc(s.original_sha256.slice(0,12))}</li>`).join('')}</ul>
    <p class="small">All 120 sequential frames: ${(run.frame_evidence || []).map((s,i) => `<a href="${esc(s.path)}" target="_blank" rel="noopener">${i*40}–${i*40+39} ↗</a>`).join(' · ')}</p>
    ${(run.extra_frame_evidence || []).map(s => `<p class="small"><a href="${esc(s.path)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a></p>`).join('')}</details>
    <details><summary>Run settings and provenance</summary><pre>${esc(JSON.stringify({source_sha256:run.source_sha256, model_identity:run.model_identity, request:run.request},null,2))}</pre></details>
    <p class="small"><a href="${esc(run.video.path)}" download>Original MP4 ↓</a> · SHA256 ${esc(run.video.sha256.slice(0,16))}…</p>`;
}
function renderCase() {
  document.querySelectorAll('video').forEach(v => v.pause());
  const c = data.cases.find(c => c.id === selected);
  if (!c) { $('case').innerHTML = '<p class="empty">No matching cases. Adjust the filters.</p>'; return; }
  const runs = Object.keys(routes).map(arm => c.runs.find(r => r.arm === arm));
  $('case').innerHTML = `<div class="case-head"><div class="chips"><span class="chip">${esc(c.category)}</span><span class="chip">${esc(c.aspect_ratio)} · 5 seconds</span><span class="chip">Seed ${c.runs[0].seed}</span></div><h3>${esc(c.title)}</h3><p class="small">${esc(c.id)} · ${esc(c.selection_note || 'All outputs generated for this edition on the same frozen product source.')}</p></div>
    <div class="controls"><button id="play" class="primary">Play together</button><button id="pause">Pause</button><button id="restart">Restart</button><label>Audio<select id="audio"><option value="-1">Muted</option>${runs.filter(r => r.video).map(r => `<option value="${esc(r.arm)}">${esc(r.arm)} · ${esc(r.mode)}</option>`).join('')}</select></label><label class="seek">Shared time <output id="clock">0.00 s</output><input id="seek" type="range" min="0" max="5" step="0.0416666667" value="0" aria-label="Shared video time"></label></div>
    <div class="videos ${c.aspect_ratio === '9:16' ? 'portrait' : ''}">${runs.map(r => `<section class="video-card">${r.video ? `<video data-arm="${esc(r.arm)}" controls playsinline preload="none" poster="${esc(r.poster)}" src="${esc(r.video.path)}" aria-label="${esc(c.title+' '+routes[r.arm])}"></video>` : '<div class="pending-video">Awaiting new generation</div>'}<div class="info"><h4>${routes[r.arm]}</h4><p class="small">Sample ${r.request.model_width}×${r.request.model_height} → deliver ${r.request.width}×${r.request.height} · 120 frames / 24 fps</p><p><span class="chip ${esc(r.review.status)}">${statusNames[r.review.status]}</span></p><p class="small">${r.seconds == null ? 'Time pending' : r.seconds.toFixed(2)+' s · complete public API call'}${r.peak_physical_gib == null ? '' : ' · '+r.peak_physical_gib.toFixed(1)+' GiB sampled peak'}</p>${reviewDetails(r, c.criteria)}</div></section>`).join('')}</div>
    <section class="details-block"><h4>Complete visual task criteria</h4><ol>${c.criteria.map(text => `<li>${esc(text)}</li>`).join('')}</ol><p class="small">All criteria must pass. Borderline is not a confirmed pass. Audio is available to play but subjective audio quality is unscored.</p></section>
    <section class="details-block"><h4>Exact prompt</h4><button id="copy-prompt">Copy prompt</button> <a href="${esc(c.prompt.path)}" download>TXT ↓</a><pre class="prompt">${esc(c.prompt_text)}</pre></section>
    <section class="details-block"><h4>Unmodified references · Picture order</h4><div class="references">${c.references.map((r,i) => `<figure class="reference"><a href="${esc(r.path)}" download><img src="${esc(r.path)}" loading="lazy" alt="Picture ${i+1}: ${esc(r.credit.title || 'Reference')}"></a><figcaption><strong>Picture ${i+1}</strong> · ${esc(r.credit.title || 'Reference')}<br>${esc(r.credit.author || 'Not recorded')} · ${esc(r.credit.license)}<br><a href="${esc(r.path)}" download>Download input</a> · ${esc(r.sha256.slice(0,16))}…</figcaption></figure>`).join('')}</div><details><summary>Input provenance and prompt changes</summary><pre>${esc(JSON.stringify(c.provenance,null,2))}</pre></details></section>
    <section class="details-block"><h4>Reproduce this task</h4><p class="small">Use the recorded product build in a dedicated Conda environment. The command validates inputs; add --execute to generate. <a href="README.md">Setup and scope</a>.</p><div class="controls"><label>Mode<select id="replay-mode"><option>VSA</option><option>SOL</option></select></label><label>Profile<select id="profile"><option value="standard">Standard 768p</option><option value="fast">Fast 544p + X2</option></select></label><button id="copy-command">Copy command</button></div><pre id="command" class="code"></pre></section>`;
  const videos = [...$('case').querySelectorAll('video')];
  for (const video of videos) { video.muted = true; video.onerror = () => notice('Video unavailable. Download or reload the complete bundle.'); }
  for (const id of ['play','pause','restart','audio','seek']) $(id).disabled = !videos.length;
  function jump(time) {
    for (const video of videos) {
      if (video.readyState) video.currentTime = Math.min(time,Number.isFinite(video.duration) ? video.duration : time);
      else { video.addEventListener('loadedmetadata',() => video.currentTime = Math.min(time,video.duration),{once:true}); video.load(); }
    }
  }
  $('play').onclick = async () => { jump(Number($('seek').value)); const results = await Promise.allSettled(videos.map(v => v.play())); if (results.some(r => r.status === 'rejected')) notice('Use individual play controls for any video that did not start.'); };
  $('pause').onclick = () => videos.forEach(v => v.pause());
  $('restart').onclick = () => { videos.forEach(v => v.pause()); jump(0); $('seek').value = 0; $('clock').textContent = '0.00 s'; };
  $('seek').oninput = e => { videos.forEach(v => v.pause()); jump(Number(e.target.value)); $('clock').textContent = Number(e.target.value).toFixed(2)+' s'; };
  $('audio').onchange = e => videos.forEach(v => v.muted = v.dataset.arm !== e.target.value);
  videos[0]?.addEventListener('timeupdate',() => { const lead = videos[0]; if (lead.paused) return; $('seek').value = lead.currentTime; $('clock').textContent = lead.currentTime.toFixed(2)+' s'; for (const v of videos.slice(1)) if (!v.paused && v.readyState && Math.abs(v.currentTime-lead.currentTime) > .12) v.currentTime = lead.currentTime; });
  $('copy-prompt').onclick = () => copy(c.prompt_text);
  function command() { const mode = $('replay-mode').value, profile = $('profile').value; $('command').textContent = `python replay.py --case ${c.id} --mode ${mode} --profile ${profile} --seed ${c.runs[0].seed} --model-dir /path/to/${mode} ${profile === 'fast' ? '--x2-model-dir /path/to/x2 ' : ''}--output runs/${c.id}-${mode}-${profile}.mp4`; }
  $('replay-mode').onchange = command; $('profile').onchange = command; $('copy-command').onclick = () => copy($('command').textContent); command();
}
for (const category of [...new Set(data.cases.map(c => c.category))]) { const option = document.createElement('option'); option.value = category; option.textContent = category; $('category').append(option); }
for (const id of ['search','category','status','orientation']) $(id).addEventListener(id === 'search' ? 'input' : 'change',filters);
renderScores(); filters();
