const data = window.COMPARISONS;
const byId = id => document.getElementById(id);
const make = (tag, text) => {
  const el = document.createElement(tag);
  if (text !== undefined) el.textContent = text;
  return el;
};
const option = (value, label) => new Option(label, value);
const pairs = byId('comparison'), scenes = byId('scene'), mobile = window.matchMedia('(max-width:700px)');
let current = [], selected = 0;
data.comparisons.forEach(c => pairs.add(option(c.id, c.title)));
function duration(seconds) {
  const n = Math.round(seconds);
  return Math.floor(n / 60) + 'm ' + String(n % 60).padStart(2, '0') + 's';
}
function selectClip(index, carry) {
  const was = current[selected], next = current[index];
  const time = carry && !was.video.ended ? was.video.currentTime : 0;
  const resume = carry && !was.video.paused;
  if (was !== next) was.video.pause();
  selected = index;
  current.forEach((row, i) => {
    row.card.classList.toggle('selected', i === index);
    row.button.setAttribute('aria-pressed', String(i === index));
  });
  if (carry && was !== next) {
    const seek = () => { next.video.currentTime = Math.min(time, Math.max(0, next.video.duration - .04)); };
    if (next.video.readyState >= 1) seek();
    else next.video.addEventListener('loadedmetadata', seek, {once:true});
    if (resume) next.video.play().catch(() => {});
  }
}
function displayCase() {
  const c = data.comparisons.find(x => x.id === pairs.value);
  const row = data.scenes.find(x => x.id === scenes.value);
  current.forEach(v => v.video.pause());
  byId('players').replaceChildren(); byId('switch').replaceChildren();
  selected = 0;
  current = [row.media[c.left], row.media[c.right]].map((media, index) => {
    const card = make('article'), video = make('video'), button = make('button', media.label);
    video.playsInline = true; video.controls = true; video.preload = 'metadata';
    video.src = media.url; video.setAttribute('aria-label', media.label);
    video.addEventListener('play', () => current.forEach(other => { if (other.video !== video) other.video.pause(); }));
    button.type = 'button'; button.onclick = () => selectClip(index, true);
    const meta = make('p'); meta.className = 'meta';
    const link = make('a', 'Open video'); link.href = media.url; link.target = '_blank'; link.rel = 'noopener';
    meta.append(make('span', media.width+'×'+media.height+' · '+duration(media.seconds)+' '+media.timing), link);
    card.append(make('h3', media.label), video, meta);
    byId('switch').append(button); byId('players').append(card);
    return {card, video, button};
  });
  selectClip(0, false);
  byId('title').textContent = row.title;
  byId('refs').replaceChildren(...row.refs.map((ref, i) => {
    const a = make('a'), img = make('img'); a.href = ref.original; a.target = '_blank'; a.rel = 'noopener';
    img.src = ref.thumbnail; img.alt = 'Open reference '+(i+1); a.append(img); return a;
  }));
  byId('prompt').textContent = row.prompt;
  byId('beats').replaceChildren(...row.beats.map(b => make('li', b)));
  history.replaceState(null, '', '#'+c.id+'/'+row.id);
}
function chooseScene(desired) {
  const c = data.comparisons.find(x => x.id === pairs.value);
  const available = data.scenes.filter(row => row.media[c.left] && row.media[c.right]);
  scenes.replaceChildren(...available.map(row => option(row.id, row.title)));
  if (available.some(row => row.id === desired)) scenes.value = desired;
  byId('coverage').textContent = available.length+' of '+c.total+' scenes';
  displayCase();
}
function locationChoice() {
  const [kind, scene] = location.hash.slice(1).split('/');
  if (data.comparisons.some(c => c.id === kind)) pairs.value = kind;
  chooseScene(scene);
}
pairs.onchange = () => chooseScene(scenes.value);
scenes.onchange = displayCase;
mobile.addEventListener('change', () => {
  const i = current.findIndex(row => !row.video.paused);
  if (i !== -1) selectClip(i, false);
});
window.addEventListener('hashchange', locationChoice);
locationChoice();
