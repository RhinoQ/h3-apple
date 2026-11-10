"use strict";
const player = document.querySelector("#player");
const nav = document.querySelector("#scenes");
const status = document.querySelector("#status");
let films = [];
let currentUrl = "";

function element(tag, text) {
  const node = document.createElement(tag);
  if (text !== undefined) node.textContent = text;
  return node;
}

function link(text, url) {
  const a = element("a", text);
  a.href = url;
  return a;
}

function show() {
  if (!films.length) return;
  const [id, version] = location.hash.slice(1).split("~");
  const film = films.find(item => item.id === id) || films[0];
  const upscaled = Boolean(version === "2x" && film.restored);
  const media = upscaled ? film.restored : film.native;
  if (currentUrl !== media.url) {
    player.pause();
    const source = element("source");
    source.type = "video/mp4";
    source.src = media.url;
    player.replaceChildren(source);
    if (film.id === "high-dialogue") {
      const track = element("track");
      Object.assign(track, {kind:"captions", label:"English dialogue", srclang:"en", src:"paintbrush.vtt"});
      player.append(track);
    }
    player.poster = film.native.poster;
    player.setAttribute("aria-label", film.title);
    player.classList.toggle("landscape", media.width > media.height);
    player.load();
    currentUrl = media.url;
  }
  document.title = film.title + " · 0.9.0 · h3-apple";
  document.querySelector("#mode").textContent = film.quality + " / " + film.model + " / " + film.steps + " steps";
  document.querySelector("#title").textContent = film.title;
  document.querySelector("#brief").textContent = film.brief;
  const delivery = upscaled ? "VOSR 2×" : film.x2 ? "544p + X2 decoder" : "Native 768p";
  const rows = [
    ["Output", media.width + " × " + media.height + " · " + delivery],
    ["Playback", film.duration + " s · 24 fps · stereo"],
    ["Generation", film.backend + " · " + film.refs + " references"],
    ["Seed", String(film.seed)]
  ];
  document.querySelector("#settings").replaceChildren(...rows.map(([key, value]) => {
    const row = element("div"); row.append(element("dt", key), element("dd", value)); return row;
  }));
  const files = document.querySelector("#files");
  const original = link("Open MP4", media.url);
  original.target = "_blank"; original.rel = "noopener";
  files.replaceChildren(original);
  if (film.restored) files.append(link(upscaled ? "Play native video" : "Play optional VOSR 2×", "#" + film.id + (upscaled ? "" : "~2x")));
  for (const tile of nav.children) {
    if (tile.hash === "#" + film.id) tile.setAttribute("aria-current", "true");
    else tile.removeAttribute("aria-current");
  }
}

function update(data) {
  if (data.version !== "0.9.0" || !Array.isArray(data.films) || !data.films.length) throw Error("Missing gallery");
  films = data.films;
  nav.replaceChildren(...films.map(film => {
    const a = link("", "#" + film.id); a.className = "tile";
    const img = element("img"); img.alt = ""; img.src = film.native.poster; img.loading = "lazy";
    const label = element("span"); label.append(element("strong", film.title), element("small", film.quality + " · " + film.duration + " s"));
    a.append(img, label);
    a.addEventListener("click", () => document.querySelector(".feature").scrollIntoView({block:"start"}));
    return a;
  }));
  status.textContent = "";
  show();
}

async function load(url) {
  const response = await fetch(url, {cache:"no-cache"});
  if (!response.ok) throw Error("Gallery unavailable");
  update(await response.json());
}
window.addEventListener("hashchange", show);
async function start() {
  try { await load("films.json"); } catch { status.textContent = "Loading films…"; }
  try {
    const branch = "https://raw.githubusercontent.com/RhinoQ/h3-apple/refs/heads/codex/v090-gallery-media/films.json";
    await load(branch + "?v=" + Math.floor(Date.now() / 60000));
  } catch {
    if (!films.length) status.textContent = "The video list could not load. Refresh to try again.";
  }
}
start();
