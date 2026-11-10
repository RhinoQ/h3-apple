'use strict';
if (new URLSearchParams(location.search).get('release') === '0.9.0') {
  document.querySelector('link[rel=stylesheet]').disabled = true;
  document.querySelector('meta[name=description]').content = 'Videos generated with h3-apple 0.9.0 on a Mac, including optional 2× restoration.';
  const style = document.createElement('style');
  style.textContent = ":root{color-scheme:dark;--bg:#11161d;--surface:#1a232b;--ink:#f3f2eb;--muted:#afbec6;--line:#34434d;--mint:#9aead4;--mono:ui-monospace,SFMono-Regular,Menlo,monospace}\n*{box-sizing:border-box}\nbody{margin:0;color:var(--ink);background:var(--bg);font-family:-apple-system,BlinkMacSystemFont,\"Segoe UI\",sans-serif;line-height:1.5}\na{color:var(--mint);text-decoration-thickness:1px;text-underline-offset:.23em}\na:focus-visible,video:focus-visible{outline:3px solid var(--mint);outline-offset:4px}\n.skip{position:absolute;top:-100px;left:12px;background:var(--bg);padding:10px;z-index:2}.skip:focus{top:5px}\nheader{border-bottom:1px solid var(--line)}.bar,main,footer{width:min(1100px,calc(100% - 64px));margin:auto}\n.bar{display:flex;align-items:center;gap:19px;min-height:70px}.brand{font-weight:760;font-size:24px;letter-spacing:-1.3px;color:var(--ink);text-decoration:none}\n.edition{font:12px/1.4 var(--mono);border-left:1px solid var(--line);padding-left:19px;color:var(--muted)}.github{margin-left:auto;font-size:14px}\n.feature{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(250px,1fr);align-items:center;gap:clamp(28px,5.6vw,74px);margin:38px 0 40px}\n.theater{display:grid;place-items:center;background:#080b0e;border:1px solid var(--line);border-radius:10px;overflow:hidden;min-width:0}\nvideo{display:block;width:100%;height:clamp(330px,62svh,630px);object-fit:contain;background:#080b0e}\n.mode{color:var(--mint);margin:0 0 12px;font:13px/1.4 var(--mono)}\nh1{font-size:clamp(38px,5.3vw,73px);line-height:.99;letter-spacing:-.059em;font-weight:650;margin:0 0 20px;text-wrap:balance}\n.brief{font-size:clamp(16px,1.6vw,20px);color:var(--muted);margin:0 0 26px;max-width:42ch}\ndl{border-top:1px solid var(--line);margin:0}dl>div{display:flex;gap:15px;justify-content:space-between;align-items:baseline;border-bottom:1px solid var(--line);padding:7px 0}\ndt{color:var(--muted);font-size:13px}dd{margin:0;text-align:right;font:13px/1.45 var(--mono);overflow-wrap:anywhere}\n.files{display:flex;flex-wrap:wrap;gap:10px 18px;margin:18px 0 0}.files a{display:inline-flex;align-items:center;min-height:38px;font-size:14px}\n.collection{border-top:1px solid var(--line);padding:18px 0 0}h2{font-size:22px;letter-spacing:-.04em;margin:0 0 15px}\n#scenes{display:grid;grid-template-columns:repeat(auto-fill,minmax(185px,1fr));gap:10px}.tile{display:grid;grid-template-columns:50px minmax(0,1fr);align-items:center;gap:11px;color:var(--ink);background:var(--surface);text-decoration:none;border:1px solid var(--line);border-radius:6px;padding:5px 9px 5px 5px;min-height:64px;line-height:1.25}\n.tile[aria-current=true]{border-color:var(--mint)}.tile:hover{background:#24313a}.tile img{width:50px;height:52px;object-fit:cover;border-radius:3px}\n.tile strong,.tile small{display:block}.tile strong{font-size:14px;font-weight:620}.tile small{margin-top:4px;font:11px/1.3 var(--mono);color:var(--muted)}\n#status,.noscript{color:var(--muted)}footer{margin:32px auto 26px;border-top:1px solid var(--line);padding-top:15px;font-size:12px;color:var(--muted)}\n@media(max-width:680px){.bar,main,footer{width:calc(100% - 32px)}.bar{min-height:54px;gap:12px}.brand{font-size:20px}.edition{font-size:11px;padding-left:12px}.github{font-size:12px}.feature{display:flex;flex-direction:column;align-items:stretch;gap:20px;margin:17px 0 24px}.theater{border-radius:7px}video{height:min(53svh,500px)}video.landscape{height:auto;aspect-ratio:16/9}.mode{font-size:12px;margin-bottom:7px}h1{font-size:36px;line-height:1.02;margin-bottom:10px}.brief{margin-bottom:15px;font-size:16px}.files{margin-top:10px}#scenes{grid-template-columns:repeat(auto-fit,minmax(145px,1fr))}.tile{grid-template-columns:40px minmax(0,1fr);gap:8px}.tile img{width:40px;height:46px}.tile strong{font-size:13px}}\n@media(max-width:340px){.edition{border:0;padding:0}.bar{gap:8px}#scenes{grid-template-columns:1fr}}\n@media(max-width:680px){main{display:flex;flex-direction:column}.collection{order:-1;border:0;padding-top:12px}.collection h2{display:none}#scenes{display:flex;overflow-x:auto;overscroll-behavior-x:contain;padding:2px 1px 5px}.tile{flex:0 0 166px;min-height:48px}.tile img{height:40px}.feature{margin-top:9px}}\n\n.replay{margin:4px 0 36px;padding:22px 0 0;border-top:1px solid var(--line);scroll-margin-top:16px}\n.replay h2{font-size:clamp(24px,3vw,32px);margin:0 0 10px}\n.replay-overview{display:grid;grid-template-columns:1.5fr 1fr 1fr;gap:18px;margin:12px 0 8px}\n.replay-overview>div{display:block;padding:9px 0}.replay-overview dd{text-align:left;margin:3px 0;font-size:15px}\n.replay p{max-width:80ch;color:var(--muted);margin:8px 0 14px}\n.replay a,.replay summary{touch-action:manipulation}\n.replay .take{border-top:1px solid var(--line)}\n.replay .take:last-child{border-bottom:1px solid var(--line)}\n.replay summary{cursor:pointer;color:var(--ink);padding:13px 0}\n.take>summary::marker,.prompt>summary::marker{color:var(--mint)}\n.take>summary h3{display:inline;margin:0;font-size:17px}\n.take>summary small{display:inline-block;margin-left:14px;font:12px/1.5 var(--mono);color:var(--muted)}\n.take-body{max-width:960px;padding:0 0 22px 17px}\n.take-body h4{font-size:15px;margin:17px 0 8px}\n.prompt>summary{color:var(--mint);padding:8px 0}\n.prompt>a{font-size:14px}\n.replay pre{margin:4px 0 10px;padding:12px 15px;background:#090d11;border:1px solid var(--line);border-radius:6px;font:13px/1.55 var(--mono);white-space:pre-wrap;overflow-wrap:anywhere}\n.prompt pre{font-family:inherit;font-size:14px;line-height:1.65;max-width:86ch}\n.picture-list{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px;max-width:720px;list-style:none;margin:0 0 16px;padding:0}\n.picture-list a{display:block;text-decoration:none;color:var(--ink);line-height:1.35}\n.picture-list img{display:block;width:100%;aspect-ratio:9/16;object-fit:contain;background:#090d11;border-radius:5px;border:1px solid var(--line)}\n.picture-list small,.picture-list span{display:block}.picture-list small{margin:6px 0 2px;font:11px/1.45 var(--mono);color:var(--mint)}.picture-list span{font-size:14px}\n.command-bar{display:flex;flex-wrap:wrap;gap:12px;align-items:center;justify-content:space-between;margin-top:12px}\n.command-bar h4{margin:0}.command-bar button{background:transparent;border:0;padding:8px 2px;color:var(--mint);cursor:pointer;font:inherit;font-size:13px;text-decoration:underline;text-underline-offset:.2em}\n.replay :is(summary,button):focus-visible{outline:2px solid var(--mint);outline-offset:2px}\n@media(max-width:680px){.take-body{padding-left:0}.take>summary small{display:block;margin-left:17px}.picture-list{grid-template-columns:repeat(2,minmax(0,1fr));gap:12px}.replay pre{padding:9px;font-size:12px}.prompt pre{font-size:14px}.command-bar button{min-height:44px}}\n@media(max-width:680px){.replay-overview{grid-template-columns:1fr 1fr;gap:0 14px}.replay-overview>div:first-child{grid-column:1/-1}.replay-overview dd{font-size:14px}}\n.picture-list.wide img,video.landscape{height:auto;aspect-ratio:16/9}\n.picture-list.wide{grid-template-columns:repeat(2,minmax(0,1fr))}\n@media(min-width:681px){\n  .feature:has(video.landscape){grid-template-columns:1fr;gap:24px}\n  .feature:has(video.landscape) .notes{display:grid;grid-template-columns:minmax(0,1.3fr) minmax(270px,1fr);column-gap:clamp(32px,6vw,85px);align-items:start}\n  .feature:has(video.landscape) .notes>:is(.mode,h1,.brief){grid-column:1}\n  .feature:has(video.landscape) #settings{grid-column:2;grid-row:1/span 3}\n  .feature:has(video.landscape) .files{grid-column:1/-1;margin-top:0}\n}\n";
  document.head.append(style);
  document.body.innerHTML = "\n  <a href=\"#player\" class=\"skip\">Skip to video</a>\n  <header><div class=\"bar\"><a class=\"brand\" href=\"./\">h3-apple</a><span class=\"edition\">0.9.0 video gallery</span><a class=\"github\" href=\"https://github.com/RhinoQ/h3-apple\">GitHub \u2197</a></div></header>\n  <main>\n    <article class=\"feature\" aria-labelledby=\"title\">\n      <div class=\"theater\"><video id=\"player\" controls playsinline preload=\"metadata\" aria-label=\"Scene video\"></video></div>\n      <section class=\"notes\" aria-live=\"polite\">\n        <p id=\"mode\" class=\"mode\"></p>\n        <h1 id=\"title\">The paintbrush trade</h1>\n        <p id=\"brief\" class=\"brief\" aria-label=\"Scene prompt\">A rabbit asks \u201cMy turn?\u201d and trades an apple for a bear\u2019s paintbrush at a garden fence.</p>\n        <dl id=\"settings\"></dl>\n        <div id=\"files\" class=\"files\"></div>\n      </section>\n    </article>\n    <section id=\"replay\" class=\"replay\" aria-labelledby=\"replay-title\" hidden>\n      <h2 id=\"replay-title\" tabindex=\"-1\">Generation details</h2>\n      <div id=\"replay-content\"></div>\n    </section>\n    <section class=\"collection\" aria-labelledby=\"scenes-title\"><h2 id=\"scenes-title\">Scenes</h2><nav id=\"scenes\" aria-label=\"Select a scene\"></nav></section>\n    <p id=\"status\" role=\"status\"></p>\n    <noscript><p>Enable JavaScript to select a scene.</p></noscript>\n  </main>\n  <footer>Generated on a 40-core Apple M5 Max with 128 GiB of memory. Each scene is the first output from its prompt and seed.</footer>\n";
  document.documentElement.classList.remove('opening-gallery');
  const fallbackFilms = {"version":"0.9.0","films":[{"id":"high-dialogue","title":"The paintbrush trade","brief":"A rabbit asks “My turn?” and trades an apple for a bear’s paintbrush at a garden fence.","quality":"High","model":"Pika H3 Flex","backend":"Dense","steps":6,"refs":3,"duration":5.0,"seed":900103,"x2":false,"entrypoint":"API","native":{"width":768,"height":1366,"bytes":3035241,"sha256":"3a810a43738b99954b0ff5241630a9d8d64c4ca0cd3fe753b05d6348804d1377","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/5e13da47b8f204c7713cbb0454df527b2eafc997/films/3a810a43738b99954b0ff5241630a9d8d64c4ca0cd3fe753b05d6348804d1377.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/5e13da47b8f204c7713cbb0454df527b2eafc997/films/3a810a43738b99954b0ff5241630a9d8d64c4ca0cd3fe753b05d6348804d1377.jpg"},"restored":{"width":1536,"height":2732,"bytes":13613881,"sha256":"083125d7916df6f0860037c3ac13b2c1399f6c33fdda8c81b152e2b20de09ea8","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/0b4b7ba477d249de9c08654f4e8abcaa2c7c0f96/films/083125d7916df6f0860037c3ac13b2c1399f6c33fdda8c81b152e2b20de09ea8.mp4"}},{"id":"fast-long","title":"Four outfits, one room","brief":"A single overhead take follows a rabbit from sofa to rug as a wooden fan passes over four changes of clothes.","quality":"Fast","model":"LightX2V v1.0","backend":"VSA","steps":4,"refs":6,"duration":15.0,"seed":900101,"x2":true,"entrypoint":"CLI","native":{"width":1088,"height":1920,"bytes":19779237,"sha256":"61a564ef3da17fe66fb2b508087631a4d499e883b10a5aa036d8fb3d4f61b4e8","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/bae11790db3cea7c7c5a5e35090a3036839d2932/films/61a564ef3da17fe66fb2b508087631a4d499e883b10a5aa036d8fb3d4f61b4e8.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/bae11790db3cea7c7c5a5e35090a3036839d2932/films/61a564ef3da17fe66fb2b508087631a4d499e883b10a5aa036d8fb3d4f61b4e8.jpg"}},{"id":"medium-nine","title":"The navy suitcase","brief":"Nine references guide a packing scene with a tan coat, a blue scarf and a brass latch.","quality":"Medium","model":"LightX2V v1.0","backend":"VSA","steps":4,"refs":9,"duration":8.5,"seed":900102,"x2":false,"entrypoint":"API","native":{"width":768,"height":1366,"bytes":6960891,"sha256":"e93f875acb598e3cf304e5d3a4e695928de542da348a837a3956f60feff674fa","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/3b6c5cda4c4d62b188161b2d2f5b53afcce00cab/films/e93f875acb598e3cf304e5d3a4e695928de542da348a837a3956f60feff674fa.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/3b6c5cda4c4d62b188161b2d2f5b53afcce00cab/films/e93f875acb598e3cf304e5d3a4e695928de542da348a837a3956f60feff674fa.jpg"}},{"id":"sol-fast-pool","title":"Underwater handoff","brief":"Two swimmers reach for the same yellow ring beneath the surface of a tiled pool.","quality":"Fast","model":"LightX2V v1.0","backend":"SOL","steps":4,"refs":4,"duration":5.0,"seed":900104,"x2":true,"entrypoint":"CLI","native":{"width":1920,"height":1088,"bytes":12344836,"sha256":"a6a25ebeaed0182436d442ba36ce0d03641310a0fa62791686f8641897830141","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/ba85482c55751f2315a38ff949f596c0dbf9b7da/films/a6a25ebeaed0182436d442ba36ce0d03641310a0fa62791686f8641897830141.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/ba85482c55751f2315a38ff949f596c0dbf9b7da/films/a6a25ebeaed0182436d442ba36ce0d03641310a0fa62791686f8641897830141.jpg"}},{"id":"sol-medium-parcel","title":"Parcel 17B","brief":"Two dispatchers turn, pass and stamp a labeled parcel under blue light.","quality":"Medium","model":"LightX2V v1.0","backend":"SOL","steps":4,"refs":3,"duration":5.0,"seed":900105,"x2":false,"entrypoint":"API","native":{"width":1366,"height":768,"bytes":1978396,"sha256":"2b43d01f065d95036c55d7ad4c1ea9b83c19046412662ac4641721f84d355f3b","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/2f06fff016ee2b9b25d2374827633a409e502481/films/2b43d01f065d95036c55d7ad4c1ea9b83c19046412662ac4641721f84d355f3b.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/2f06fff016ee2b9b25d2374827633a409e502481/films/2b43d01f065d95036c55d7ad4c1ea9b83c19046412662ac4641721f84d355f3b.jpg"}},{"id":"high-jewelry-upscale","title":"The silver chain","brief":"A rabbit slides a jewelry box across the table. The bear opens it under a warm lamp and lifts the chain.","quality":"High","model":"Pika H3 Flex","backend":"Dense","steps":6,"refs":3,"duration":5.0,"seed":900106,"x2":false,"entrypoint":"CLI","native":{"width":768,"height":1366,"bytes":1908183,"sha256":"281b5e4cfeb2fcad4e8eba238572e2c771ddce0757bbea57f03284b2f60ea749","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/654bb0d8a943d2a69c0a4b8bd770c6ff645f2e7e/films/281b5e4cfeb2fcad4e8eba238572e2c771ddce0757bbea57f03284b2f60ea749.mp4","poster":"https://raw.githubusercontent.com/RhinoQ/h3-apple/654bb0d8a943d2a69c0a4b8bd770c6ff645f2e7e/films/281b5e4cfeb2fcad4e8eba238572e2c771ddce0757bbea57f03284b2f60ea749.jpg"},"restored":{"width":1536,"height":2732,"bytes":9569874,"sha256":"810b2405e4bd30c5607e380a011b49153972029f67286f1aeac83369856cf36e","url":"https://raw.githubusercontent.com/RhinoQ/h3-apple/d68d22ad057474f7c68c90ecd6cc4a7c175b5b30/films/810b2405e4bd30c5607e380a011b49153972029f67286f1aeac83369856cf36e.mp4"}}]};
const player = document.querySelector("#player");
const nav = document.querySelector("#scenes");
const status = document.querySelector("#status");
const footer = document.querySelector("footer");
const originalFooter = footer.textContent;
const featuredFilms = [{"id": "wind-it-up", "title": "Wind It Up", "brief": "A fingertip releases a die-cast rally car on a paper map. On the next bend, a full-size coupe throws snow across an Alpine pass.", "quality": "High", "model": "Pika H3 Flex", "backend": "Dense", "steps": 6, "shots": 3, "refs": "3 original images · 2 per shot", "duration": 13.0, "seeds": [901071, 901072, 901073], "x2": false, "production": "The three original reference stills were made with ImageGen. h3-apple generated the action and stereo audio on a 40-core Apple M5 Max with 128 GiB. The release title was added in the edit.", "native": {"url": "https://raw.githubusercontent.com/RhinoQ/h3-apple/15ceb7749aef752aa016e9b40723fb617facfbd1/films/09e72f6de2c04a019c207f81ab0b984be72ba085fc18d257cfe082961739c8a9.mp4", "sha256": "09e72f6de2c04a019c207f81ab0b984be72ba085fc18d257cfe082961739c8a9", "bytes": 7312972, "width": 1366, "height": 768, "poster": "https://raw.githubusercontent.com/RhinoQ/h3-apple/15ceb7749aef752aa016e9b40723fb617facfbd1/films/9995c443f190963fb3fba672b7324f03745653cb3069ff83a4c1820fd74a16cd.jpg"}, "replay": {"hardware": "Apple M5 Max, 40-core GPU, 128 GiB unified memory", "nativeSeconds": 2901.723509124713, "pictures": {"map.png": "The die-cast coupe on a paper map", "apex.png": "The full-size coupe on the mountain pass", "road.png": "The snowy hairpin from above"}, "shots": [{"title": "The wind-up", "start": 0.0, "duration": 3.5, "seconds": 957.6382657918148, "seed": 901071, "refs": ["map.png", "apex.png"], "promptFile": "prompts/01-wind.txt", "prompt": "subject_definitions:\n<Subject 1> is the chipped vermilion die-cast coupe in <Picture 1>, with a single ivory stripe down its hood and roof, two amber rally lamps and small black wheels. <Picture 1> gives the opening tabletop, scale, hand and warm lighting. <Picture 2> supplies the silhouette and stripe placement of the same car design.\n\nsummary:\nA fingertip winds a tiny pull-back rally car on a mountain map and lets it race across a red-penciled bend. A tactile, photoreal opening to a rally film.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - the one toy stays hand-sized on the paper.\n<Picture 1> ([Shot 1] first frame): fully_preserved - the amber desk lamp, aged paper, low camera and fingertip.\n<Picture 2> ([Shot 1] car design): attribute_transfer - retain the coupe's paint and proportions on the toy.\n\ndetailed_description:\n[Shot 1] One continuous low macro tracking shot, with moving shadows and shallow focus. Open tight on the index fingertip touching the roof, the nose pointed screen right. The finger pulls the little car back half a car length to the left. Its spring ticks. By the second second the finger lifts clear, leaving the car free. The car shoots toward screen right, black wheels spinning, bouncing lightly over a fold in the paper. The camera tracks level beside its near front wheel. Fine blue contour lines and the red ink bend race underneath. Finish still moving right at axle height. Warm practical light, ivory paper and tactile red enamel. Clean full-bleed photographic frame.\n\noverall_soundscape:\nClose, dry spring clicks on the pullback, a crisp release, tiny metal wheels buzzing along coarse paper. The whir builds in pitch as the car picks up speed. Quiet room underneath.\n\nnon_diegetic_music:\nOnly the mechanical sounds carry the rhythm. No dialogue or score.\n", "command": "h3 generate --quality high --no-upscale --duration 5 --aspect-ratio 16:9 \\\n  --seed 901071 --prompt-file prompts/01-wind.txt \\\n  --image refs/map.png \\\n  --image refs/apex.png \\\n  --output 01-wind.mp4 --timeout 7200"}, {"title": "The slide", "start": 3.5, "duration": 4.5, "seconds": 962.4090060000308, "seed": 901072, "refs": ["apex.png", "map.png"], "promptFile": "prompts/02-slide.txt", "prompt": "subject_definitions:\n<Subject 1> is the full-size vermilion rally coupe from <Picture 1>: a boxy two-door body, a single broad ivory stripe on the hood and roof, two amber lamps and dark wheels. <Picture 1> also anchors the low roadside view, Alpine pass and last pink light. <Picture 2> supplies the hue of the red enamel and the stripe as continuity with the miniature.\n\nsummary:\nCut from a toy to the real thing. A full-size rally driver powerslides an alpine hairpin and catches the slide, throwing a bright, sculptural wave of powder. One continuous live-action tracking shot.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - one recognizable real coupe and its lamps from approach through exit.\n<Picture 1> ([Shot 1] location and framing): fully_preserved - cold blue mountain shadows, the close front three-quarter angle and warm light on the body.\n<Picture 2> ([Shot 1] color and stripe): attribute_transfer - the same red and ivory design on the full-size body.\n\ndetailed_description:\n[Shot 1] Start in motion. At wheel height the red coupe charges through frame toward screen right. The camera pans alongside the near front fender, using the mountain peaks as a stable horizon. The nose turns into the bend as the rear wheels step outward; powder erupts behind the near rear tire in a single broad fan. The amber lamps briefly point almost into the lens. The driver countersteers and the rear settles back in line. In the last second the car gains distance, revealing fresh curved black tracks through a thinning cloud. Keep the action moving, weight in the suspension, blur on the road, sharp highlights on the red body; an uninterrupted roadside pass at blue hour.\n\noverall_soundscape:\nAn engine already at full throttle, a short gear change, tires scrubbing hard-packed snow, powder hissing past the microphone. The engine note falls away as the car exits. Wide alpine outdoor acoustics.\n\nnon_diegetic_music:\nEngine and tires make the soundtrack. No dialogue or score.\n", "command": "h3 generate --quality high --no-upscale --duration 5 --aspect-ratio 16:9 \\\n  --seed 901072 --prompt-file prompts/02-slide.txt \\\n  --image refs/apex.png \\\n  --image refs/map.png \\\n  --output 02-slide.mp4 --timeout 7200"}, {"title": "The road", "start": 8.0, "duration": 5.0, "seconds": 981.6762373328675, "seed": 901073, "refs": ["road.png", "apex.png"], "promptFile": "prompts/03-road.txt", "prompt": "subject_definitions:\n<Picture 1> sets the high aerial angle, blue alpine dusk and the great hairpin drawn in the snowy terrain. <Subject 1> is the one real red rally coupe on the lower leg of the road, also shown close in <Picture 2>, with a single ivory roof stripe, dark wheels and glowing amber lamps.\n\nsummary:\nFrom above, a red speck leaves an enormous white hairpin behind. Camera and car move downhill together, opening out the landscape until the road looks like the line on a paper map.\n\nretention_analysis:\n<Picture 1> ([Shot 1] first frame and landscape): fully_preserved - keep the curved road geometry and mountain scale, with dark pines along the left edge.\n<Subject 1> (appears in [Shot 1]): fully_preserved - the only car is the vermilion coupe, its hood pointing downhill.\n<Picture 2> ([Shot 1] car design): attribute_transfer - the real coupe's stripe, amber lamps and red body retain their identity at a distance.\n\ndetailed_description:\n[Shot 1] Open high and wide on <Picture 1>. The red car is already accelerating nose first downhill, following the lower leg of the hairpin toward the bottom of the image. Amber headlights skim the ice in front. A thread of lifted powder trails the rear wheels, then hangs over two dark tire marks. The camera flies smoothly backward above its path while gaining altitude. The car keeps to the road, visible lower-center, becoming smaller; the full sweep of the hairpin opens out behind it and the mountain pines throw long blue shadows. Let the composition breathe into the final second. A quiet, immense photographic closing image. Continuous shot, deep focus, no graphics.\n\noverall_soundscape:\nAn engine receding down the valley, its echo returning from the rocks, fine wind in the trees. Let the engine fade into mountain air at the tail. A spacious stereo exterior.\n\nnon_diegetic_music:\nOutdoor sound only. No dialogue, singing or score.\n", "command": "h3 generate --quality high --no-upscale --duration 5 --aspect-ratio 16:9 \\\n  --seed 901073 --prompt-file prompts/03-road.txt \\\n  --image refs/road.png \\\n  --image refs/apex.png \\\n  --output 03-road.mp4 --timeout 7200"}], "archive": "wind-it-up-inputs.zip", "archiveBytes": 5460112, "assemble": "python assemble.py wind-it-up.mp4", "edit": "The edit cuts between native frames, fades the generated stereo at the joins and overlays the release title on the aerial shot. The ZIP includes the edit decisions and the transparent title.", "inspiration": "https://dev.pika.art/models/pika/pika-h3-flex/reference-to-video/examples", "base": "https://raw.githubusercontent.com/RhinoQ/h3-apple/15ceb7749aef752aa016e9b40723fb617facfbd1/features/wind-it-up/"}}, {"id": "fan-wardrobe", "title": "Four looks under the fan", "brief": "A pink rabbit rolls off the sofa. A walnut ceiling fan sweeps past to reveal a floral skirt, a blue bubble dress, and an indigo denim look with a burgundy bow.", "quality": "High", "model": "Pika H3 Flex", "backend": "Dense", "steps": 6, "shots": 3, "refs": "6 original stills + 2 continuity frames", "duration": 15, "seeds": [910901, 910902, 910903], "x2": false, "production": "The final frames of shots 1 and 2 guide the following takes. The edit keeps all three generated stereo tracks.", "native": {"url": "https://raw.githubusercontent.com/RhinoQ/h3-apple/5f24ae4ee7ce44aa8ef82e6d067115d1341ee17a/films/2f06ad2f7f61fc97f9931aa13e11836e741e5c978172d8ac3db0398458a616e2.mp4", "sha256": "2f06ad2f7f61fc97f9931aa13e11836e741e5c978172d8ac3db0398458a616e2", "bytes": 7700109, "width": 768, "height": 1366, "poster": "https://raw.githubusercontent.com/RhinoQ/h3-apple/e7467186618f585fc43f408874357404f531a754/films/656b2bfd9d5d8b7758e8fa51da12f7b0aae6a2f81493e0d4cfec86717da4ce75.jpg"}, "preferred": "2x", "restored": {"url": "https://raw.githubusercontent.com/RhinoQ/h3-apple/cc40b9bd5b21a1ddbe27ed45c956f73092dcab87/films/b38e7a69518365ea3869f9b92ad2a608dc29b9d56dce0a67e177e630a537d4f4.mp4", "sha256": "b38e7a69518365ea3869f9b92ad2a608dc29b9d56dce0a67e177e630a537d4f4", "bytes": 32723817, "width": 1536, "height": 2732}, "replay": {"hardware": "Apple M5 Max, 40-core GPU, 128 GiB unified memory", "nativeSeconds": 3711.59460629127, "vosrSeconds": 3238.183, "earlierTakeSeconds": 1199.6487609159667, "pictures": {"01-rest-3d.png": "Trench coat on the sofa", "05-trench-rug-3d.png": "Trench coat on the rug", "02-floral-3d.png": "Floral skirt", "03-bubble-3d.png": "Blue bubble dress", "04-bow-3d.png": "Denim and burgundy bow", "06-wipe-3d.png": "Fan blade crossing the frame", "01-119.png": "Last frame of shot 1", "02-119.png": "Last frame of shot 2"}, "shots": [{"title": "Trench to floral", "start": 0, "duration": 5.0, "seconds": 1245.743835083209, "seed": 910901, "refs": ["01-rest-3d.png", "05-trench-rug-3d.png", "02-floral-3d.png", "06-wipe-3d.png"], "promptFile": "prompts/01-trench-to-floral.txt", "prompt": "subject_definitions:\n<Subject 1> is the one blush-pink plush rabbit in <Picture 1>, <Picture 2> and <Picture 3>. Short velvety fur, two long pink-lined ears, two matching dark bead eyes, rosy cheeks and a tiny closed stitched smile. Head, paws and boots belong to the same little body.\n<Subject 2> is the miniature room in <Picture 1>. An ivory button-tufted low sofa on the left meets a rust floral rug on the right. A broad polished walnut ceiling-fan blade rotates clockwise near the lens around a hub just outside the upper-left corner. Afternoon sunlight falls from the right.\n<Picture 1> is the opening composition and trench outfit. <Picture 2> shows her landing position on the rug in that same outfit. <Picture 3> shows the cream bow blouse, tiered floral skirt and brown Mary Janes to reveal. <Picture 4> shows the angle, wood grain and size of the foreground fan when it covers her.\n\nsummary:\n[reference generation + keyframe completion] A five-second portrait fashion film in a locked overhead shot. A pink plush rabbit rolls from the cushion onto the rug. A wooden ceiling fan sweeps across her and reveals the floral outfit. The same sunlit room fills the screen throughout.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - one pink rabbit with the same small face, fur and proportions.\n<Subject 2> (appears in [Shot 1]): fully_preserved - same sofa seam, rug edge, warm light and fan pivot.\n<Picture 1> ([Shot 1] opening): fully_preserved - face up in the tan trench and boots on the left cushion.\n<Picture 2> ([Shot 1] middle): fully_preserved - face up on the right-hand rug in the same trench.\n<Picture 3> ([Shot 1] ending): fully_preserved - cream blouse, floral skirt and brown shoes in the same room.\n<Picture 4> ([Shot 1] wipe): partially_preserved - one broad wooden paddle passes close to the lens, fully hiding the outfit for an instant.\n\ndetailed_description:\n[Shot 1] Look straight down as in <Picture 1>. Frame the rabbit from ears to boots and the cushion edge together. For the opening half-beat, her face and tan trench are clear on the sofa. She tucks her paws and knees. Her right shoulder dips over the low cushion edge, her torso and hips follow, the back of her coat and ears turn up toward us, then her opposite side meets the rug. By 2.7 seconds she has rolled through onto her back on the rug in the same trench, with the sofa still on her left. Let the hem and ears settle. The camera and rug border stay still.\nAt about 3.5 seconds a single solid walnut paddle turns through the foreground in a continuous clockwise arc, sweeping across her face, coat and boots. While the wood fills the view of her clothes they change. The trailing edge clears at about 4.2 seconds and reveals the same rabbit lying in the same spot, now wearing the cream bow blouse, tiered floral skirt and brown Mary Janes from <Picture 3>. Both paws release the skirt hem and rest beside it. Finish with her still fully visible in this outfit and the blade clear of her head. The entire image is the rendered room.\n\noverall_soundscape:\nSoft fan air and a low motor under the scene. Cloth brushes the cushion, then the rug gives a small padded thump on landing. A short wooden-blade whoosh accompanies the outfit reveal. No voices.\n\nnon_diegetic_music:\nAn original playful fashion instrumental in C major at 120 BPM, pizzicato strings, soft handclaps and warm plucked bass. A simple C–E–G–E four-note hook taps the beat. Keep the groove light and steady through the end.\n", "command": "h3 generate --quality high --duration 5 --aspect-ratio 9:16 \\\n  --seed 910901 --prompt-file prompts/01-trench-to-floral.txt \\\n  --image refs/01-rest-3d.png \\\n  --image refs/05-trench-rug-3d.png \\\n  --image refs/02-floral-3d.png \\\n  --image refs/06-wipe-3d.png \\\n  --output shot-01.mp4 --timeout 7200"}, {"title": "Floral to blue", "start": 5, "duration": 5.0, "seconds": 1224.1264672500547, "seed": 910902, "refs": ["01-119.png", "02-floral-3d.png", "03-bubble-3d.png", "06-wipe-3d.png"], "promptFile": "prompts/02-floral-to-blue.txt", "prompt": "subject_definitions:\n<Subject 1> is the single pastel-pink plush rabbit in <Picture 1>, <Picture 2> and <Picture 3>. Two upright pink-lined ears, even bead eyes, round pink cheeks, small closed stitched smile, soft short fibers.\n<Subject 2> is the exact sunlit miniature set in <Picture 1>. The fixed overhead camera sees the ivory button-tufted sofa on the left, the rust floral rug alongside it and one walnut ceiling fan close to the lens. Its hub stays just beyond the upper-left corner. Its blades turn clockwise in a flat circle.\n<Picture 1> is the first frame. Match where the rabbit, sofa seam, rug and shadows sit in this frame. <Picture 2> supplies the cream bow blouse, tiered floral skirt and brown shoes. <Picture 3> supplies the periwinkle-blue bubble dress, twin hip bows and blue Mary Janes. <Picture 4> shows the thick walnut paddle crossing in front of the rabbit.\n\nsummary:\n[reference generation + keyframe completion] A five-second portrait continuation. Lying on the rug in her floral outfit, the rabbit lifts one edge of the skirt like a little curtsy. A broad fan blade turns across her. When it clears she is wearing the blue bubble dress and raises one paw beside her cheek.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - the same one rabbit and small closed smile before and after the change.\n<Subject 2> (appears in [Shot 1]): fully_preserved - overhead camera, rug and cushion hold their positions, sunlight stays warm and still.\n<Picture 1> ([Shot 1] beginning): fully_preserved - actual opening pose, camera distance, framing and light.\n<Picture 2> ([Shot 1] first costume): fully_preserved - cream blouse, tiered print skirt and brown shoes.\n<Picture 3> ([Shot 1] second costume): fully_preserved - gathered blue dress, small bows and blue shoes.\n<Picture 4> ([Shot 1] wipe): partially_preserved - scale and solid shape of the nearby fan blade.\n\ndetailed_description:\n[Shot 1] Start exactly at <Picture 1>. From above, the rabbit lies on the rug where the cushion meets its border. Her whole face, both ears and shoes fit in frame. For the first two seconds her paws pinch and raise the sides of her floral skirt a little, spread the three tiers, then lower them back onto the rug. Her head and hips keep the same position. The overhead fan advances evenly around its upper-left pivot.\nAt about 2.5 seconds the wide end of the walnut paddle passes between the lens and her clothes. Its solid leading edge sweeps over her, shows uninterrupted wood grain across the outfit, then the trailing edge continues along the same arc. By 3.2 seconds her cream floral outfit has been replaced by the blue bubble dress and blue shoes of <Picture 3>. The outfit changes behind the wood. Her face, direction, scale and the background stay continuous. Hold the blue look in clear view for the last two beats. She raises one paw close to her cheek, points one blue shoe and looks up with both eyes open. The fan moves away toward the frame edge.\n\noverall_soundscape:\nQuiet fan air, one gentle woody whoosh on the pass and a small fabric rustle when the hem settles. No voices.\n\nnon_diegetic_music:\nContinue a light 120 BPM fashion groove in C major with pizzicato strings, soft handclaps and warm plucked bass. Repeat a four-note C–E–G–E hook. Start on the beat and carry the same gentle pulse past the reveal.\n", "command": "h3 generate --quality high --duration 5 --aspect-ratio 9:16 \\\n  --seed 910902 --prompt-file prompts/02-floral-to-blue.txt \\\n  --image refs/01-119.png \\\n  --image refs/02-floral-3d.png \\\n  --image refs/03-bubble-3d.png \\\n  --image refs/06-wipe-3d.png \\\n  --output shot-02.mp4 --timeout 7200"}, {"title": "Blue to denim", "start": 10, "duration": 5.0, "seconds": 1241.7243039580062, "seed": 910903, "refs": ["02-119.png", "03-bubble-3d.png", "06-wipe-3d.png", "04-bow-3d.png"], "promptFile": "prompts/03-blue-to-bow-final.txt", "prompt": "subject_definitions:\n<Subject 1> is the one small pastel-pink plush rabbit in <Picture 1>, <Picture 2> and <Picture 4>. Keep the same short fur, long pink-lined ears, pair of bead eyes, pink cheeks, little embroidered smile and soft paws.\n<Subject 2> is the sunlit miniature room in <Picture 1>. A stationary ivory tufted sofa fills the left side. A rust floral rug fills the right. A wide walnut ceiling paddle turns around a hub just beyond the upper-left corner.\n<Picture 1> is the exact opening frame, with the blue dress and the raised paw. <Picture 2> describes that blue bubble dress and its shoes. <Picture 3> is the single passing position of the wooden blade. <Picture 4> is the exact clear ending frame: the entire rabbit on the rug with its face, indigo jacket and shorts, large burgundy waist bow and matching red shoes visible. The last sliver of wood is confined to the upper-left corner.\n\nsummary:\n[reference generation + keyframe completion] The finale of a five-second vertical fashion film. A ceiling fan making its final slow turn wipes from a blue dress to a denim outfit. After one sweep the motor winds down. The rabbit waves and the film finishes on the fully clear burgundy bow pose in <Picture 4>.\n\nretention_analysis:\n<Subject 1> (appears in [Shot 1]): fully_preserved - one rabbit, consistent face and body, lying on the rug to the right of the sofa.\n<Subject 2> (appears in [Shot 1]): fully_preserved - same overhead room, scale, wood grain, shadows, cushion buttons and rug border.\n<Picture 1> ([Shot 1] first frame): fully_preserved - opening camera position and blue-dress pose.\n<Picture 2> ([Shot 1] opening outfit): fully_preserved - gathered pale-blue skirt, small bows and matching shoes.\n<Picture 3> ([Shot 1] one moving wipe): partially_preserved - broad near-camera wooden blade hiding the clothes for one beat.\n<Picture 4> ([Shot 1] last three seconds and final frame): fully_preserved - clear full figure with the indigo denim, burgundy bow, red shoes and closed smile.\n\ndetailed_description:\n[Shot 1] Locked straight overhead. Open with exactly the framing in <Picture 1>. The rabbit in blue lowers the paw from her cheek. A single broad ceiling-fan blade sweeps between her and the camera on its final clockwise turn. At about 1.0 seconds the solid walnut paddle covers her dress as in <Picture 3>. The paddling wood immediately carries on around the hub. As its trailing edge passes, show the indigo denim jacket, shorts, big burgundy bow and red shoes. By 2.0 seconds both ears, both shoes and the whole bow are plainly visible beside the sofa.\nThe fan motor clicks off. The blade finishes its arc and coasts to rest in the upper-left corner in exactly the position in <Picture 4>. Only the rabbit and her clothes move for the final three seconds. She opens one paw in a little wave, lowers it and relaxes her ears. Warm light catches the denim stitches and the red bow. The image ends on the uninterrupted, clear full-body pose of <Picture 4>, with her face and bow plainly visible, the room still and the blade parked up in the corner.\n\noverall_soundscape:\nOne gentle fan whoosh across the transition, a very quiet motor switch click, the motor sound winding down, then cloth shifting under the small wave. The room stays quiet. No voices.\n\nnon_diegetic_music:\nKeep the light 120 BPM C-major fashion instrumental, plucked bass and soft claps. The C–E–G–E pizzicato hook settles into a short C-major ending under the clear full-body pose.\n", "command": "h3 generate --quality high --duration 5 --aspect-ratio 9:16 \\\n  --seed 910903 --prompt-file prompts/03-blue-to-bow-final.txt \\\n  --image refs/02-119.png \\\n  --image refs/03-bubble-3d.png \\\n  --image refs/06-wipe-3d.png \\\n  --image refs/04-bow-3d.png \\\n  --output shot-03.mp4 --timeout 7200"}], "archive": "fan-wardrobe-inputs.zip", "archiveBytes": 17472821, "assemble": "python assemble.py fan-wardrobe.native.mp4 shot-01.mp4 shot-02.mp4 shot-03.mp4", "upscale": "h3 upscale --input fan-wardrobe.native.mp4 \\\n  --output fan-wardrobe.2x.mp4 --timeout 10800", "base": "https://raw.githubusercontent.com/RhinoQ/h3-apple/885a874c76664d0781337950d9ddc6ece0ee548e/features/fan-wardrobe/"}}];
const replaySection = document.querySelector("#replay");
let films = [];
let currentUrl = "";
let catalogKey = "";

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

function elapsed(seconds) {
  const total = Math.round(seconds);
  const hours = Math.floor(total / 3600);
  const minutes = Math.floor(total / 60) % 60;
  return (hours ? hours + "h " + String(minutes).padStart(2, "0") : minutes) + "m "
    + String(total % 60).padStart(2, "0") + "s";
}

function commandBlock(label, command) {
  const block = element("div");
  const bar = element("div");
  bar.className = "command-bar";
  const pre = element("pre");
  const code = element("code", command);
  pre.append(code);
  bar.append(element("h4", label));
  if (navigator.clipboard) {
    const copy = element("button", "Copy command");
    copy.type = "button";
    copy.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(command);
        copy.textContent = "Copied";
      } catch {
        const range = document.createRange();
        range.selectNodeContents(code);
        window.getSelection().removeAllRanges();
        window.getSelection().addRange(range);
        copy.textContent = "Command selected";
      }
    });
    bar.append(copy);
  }
  block.append(bar, pre);
  return block;
}

function showReplay(film) {
  const recipe = film.replay;
  replaySection.hidden = !recipe;
  if (!recipe || replaySection.dataset.film === film.id) return;
  replaySection.dataset.film = film.id;
  const src = path => recipe.base + path;
  const overview = element("dl");
  overview.className = "replay-overview";
  const stats = [["Hardware", recipe.hardware], ["Native generation · " + recipe.shots.length + " shots", elapsed(recipe.nativeSeconds)]];
  if (recipe.vosrSeconds != null) stats.push(["Optional VOSR 2×", elapsed(recipe.vosrSeconds)]);
  for (const [label, value] of stats) {
    const row = element("div");
    row.append(element("dt", label), element("dd", value));
    overview.append(row);
  }
  let timingText = "Native generation covers the selected takes with the models already on disk. Editing and encoding are separate.";
  if (recipe.earlierTakeSeconds) timingText += " An earlier take used another " + elapsed(recipe.earlierTakeSeconds) + ".";
  const timing = element("p", timingText);
  const download = link("Download prompts, reference PNGs and commands (ZIP, " + (recipe.archiveBytes / 1e6).toFixed(1) + " MB)", src(recipe.archive));
  const setup = element("p", "Unzip the files and run the commands in the " + film.id + " folder with h3-apple 0.9.0, FFmpeg and the prepared models.");
  const content = document.querySelector("#replay-content");
  content.replaceChildren(overview, timing, download, setup);
  if (recipe.inspiration) content.append(link("Creative references on Pika’s H3 Flex examples page", recipe.inspiration));
  recipe.shots.forEach((shot, i) => {
    const details = element("details");
    details.className = "take";
    details.open = i === 0;
    const summary = element("summary");
    summary.append(element("h3", "Shot " + (i + 1) + " · " + shot.title),
      element("small", shot.start + "–" + (shot.start + shot.duration) + " s · " + elapsed(shot.seconds) + " to generate"));
    const body = element("div");
    body.className = "take-body";
    const prompt = element("details");
    prompt.className = "prompt";
    prompt.append(element("summary", "Full generation prompt"), link("Open prompt as text", src(shot.promptFile)),
      element("pre", shot.prompt));
    const refs = element("ol");
    refs.className = film.native.width > film.native.height ? "picture-list wide" : "picture-list";
    shot.refs.forEach((name, index) => {
      const item = element("li");
      const picture = link("", src("refs/" + name));
      picture.target = "_blank"; picture.rel = "noopener";
      const img = element("img");
      img.src = src("thumbs/" + name.replace(/\.png$/, ".webp"));
      img.loading = "lazy"; img.decoding = "async"; img.alt = "";
      picture.append(img, element("small", "Picture " + (index + 1)), element("span", recipe.pictures[name]));
      item.append(picture); refs.append(item);
    });
    body.append(prompt, element("h4", "Reference images"), refs, commandBlock("Generation command", shot.command));
    details.append(summary, body); content.append(details);
  });
  const finish = element("details");
  finish.className = "take";
  const body = element("div");
  body.className = "take-body";
  body.append(element("p", recipe.edit || "The included assemble.py joins the shots and applies short fades to their generated stereo audio."),
    commandBlock("Join the shots", recipe.assemble));
  if (recipe.upscale) body.append(commandBlock("Optional VOSR 2×", recipe.upscale));
  finish.append(element("summary", recipe.upscale ? "Join the film and upscale" : "Edit the release film"), body);
  content.append(finish);
}

function focusReplay() {
  replaySection.scrollIntoView({block: "start"});
  document.querySelector("#replay-title").focus({preventScroll: true});
}

function show() {
  if (!films.length) return;
  const [id, version, part] = location.hash.slice(1).split("~");
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
      Object.assign(track, {kind:"captions", label:"English dialogue", srclang:"en", src:"data:text/vtt;charset=utf-8,WEBVTT%0A%0A00%3A00%3A00.300%20--%3E%2000%3A00%3A01.300%0AMy%20turn%3F%0A"});
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
  footer.textContent = film.production || originalFooter;
  const delivery = upscaled ? "VOSR 2×" : film.x2 ? "544p + X2 decoder" : "Native 768p";
  const rows = [
    ["Output", media.width + " × " + media.height + " · " + delivery],
    ["Playback", film.duration + " s · 24 fps · stereo"],
    ["Generation", film.backend + " · " + (film.shots ? film.shots + " shots" : film.refs + " references")]
  ];
  if (film.shots) rows.push(["References", film.refs]);
  rows.push(film.seeds ? ["Seeds", film.seeds.join(" · ")] : ["Seed", String(film.seed)]);
  document.querySelector("#settings").replaceChildren(...rows.map(([key, value]) => {
    const row = element("div"); row.append(element("dt", key), element("dd", value)); return row;
  }));
  const files = document.querySelector("#files");
  const original = link("Open MP4", media.url);
  original.target = "_blank"; original.rel = "noopener";
  files.replaceChildren(original);
  if (film.restored) files.append(link(upscaled ? "Play native video" : "Play optional VOSR 2×", "#" + film.id + (upscaled ? "" : "~2x")));
  showReplay(film);
  if (film.replay) {
    const jump = link("Generation details", "#" + film.id + (upscaled ? "~2x" : "~native") + "~generation");
    jump.addEventListener("click", () => { if (location.hash === jump.hash) focusReplay(); });
    files.append(jump);
    if (part === "generation") focusReplay();
  }
  for (const tile of nav.children) {
    if (tile.dataset.scene === film.id) tile.setAttribute("aria-current", "true");
    else tile.removeAttribute("aria-current");
  }
}

function update(data) {
  if (data.version !== "0.9.0" || !Array.isArray(data.films) || !data.films.length) throw Error("Missing gallery");
  const all = [...featuredFilms, ...data.films];
  if (all.length < films.length) return;
  if (films.some(old => old.restored && !all.find(film => film.id === old.id)?.restored)) return;
  const key = all.map(film => film.native.sha256 + (film.restored?.sha256 || "")).join("/");
  if (key === catalogKey) return;
  catalogKey = key;
  films = all;
  nav.replaceChildren(...all.map(film => {
    const a = link("", "#" + film.id + (film.preferred === "2x" ? "~2x" : "")); a.className = "tile";
    a.dataset.scene = film.id;
    const img = element("img"); img.alt = ""; img.src = film.native.poster; img.loading = "lazy";
    const label = element("span"); label.append(element("strong", film.title), element("small", film.quality + " · " + film.duration + " s"));
    a.append(img, label);
    a.addEventListener("click", () => {
      if (window.matchMedia("(min-width:681px)").matches) document.querySelector(".feature").scrollIntoView({block:"start"});
    });
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
document.querySelector(".skip").addEventListener("click", event => {
  event.preventDefault();
  player.focus();
});
window.addEventListener("hashchange", show);
async function refreshCatalog() {
  try {
    const branch = "https://raw.githubusercontent.com/RhinoQ/h3-apple/refs/heads/codex/v090-gallery-media/films.json";
    await load(branch + "?v=" + Math.floor(Date.now() / 60000));
  } catch {
    if (!films.length) status.textContent = "The video list could not load. Refresh to try again.";
  }
}
async function start() {
  update(fallbackFilms);
  const complete = () => films.length === 6 + featuredFilms.length
    && films.filter(film => film.restored && !featuredFilms.includes(film)).length === 2;
  if (complete()) return;
  await refreshCatalog();
  if (complete()) return;
  const timer = setInterval(() => {
    if (complete()) clearInterval(timer);
    else if (!document.hidden) refreshCatalog();
  }, 60000);
  document.addEventListener("visibilitychange", () => { if (!document.hidden && !complete()) refreshCatalog(); });
}
start();

} else {
const data = window.BENCHMARK, scores = window.SCORES;
const $ = id => document.getElementById(id);
const esc = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const dimensions = {action:'Action', count:'Subject / object count', detail:'Detail', framing:'Framing', geometry:'Geometry', identity:'Identity', temporal:'Temporal'};
const qualityNotes = {action:'Requested motion and interactions', count:'Correct number of subjects and objects', detail:'Fine visual detail', framing:'Requested composition and visible body parts', geometry:'Stable shapes and anatomy', identity:'Consistent character appearance', temporal:'Consistency from frame to frame'};
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
const percent = value => value.toFixed(1).replace(/\.0$/, '') + '%';
function renderShowcase() {
  const entries = data.showcase || [];
  $('showcase').hidden = !entries.length;
  $('showcase-cards').innerHTML = entries.map(s => {
    const seconds = Math.round(s.restoration_seconds), key = s.id.toLowerCase();
    return `<article class="showcase-card" id="showcase-${esc(s.id)}">
      <video controls playsinline preload="none" poster="${esc(s.poster)}" src="${esc(s.video.path)}" aria-label="${esc(s.title)} — five-second super-resolution showcase"></video>
      <div class="showcase-info"><p class="eyebrow">5 SECONDS</p><h3>${esc(s.title)}</h3>
      <p class="small">SOL · native 768p → VOSR 2× · ${Math.floor(seconds/60)}m ${String(seconds%60).padStart(2,'0')}s restoration${s.excerpt ? '<br>First five seconds of a 15-second generation.' : ''}</p>
      <details><summary>Prompt, reference & settings</summary>
      <p><a href="${esc(s.prompt_file)}" download>Prompt TXT ↓</a> · <a href="${esc(s.reference.url)}">Original reference ↗</a> · <a href="${esc(s.record)}">Run record ↗</a></p>
      <p class="small">Reference: <a href="${esc(s.reference.source)}">${esc(s.reference.credit)}</a> · ${s.reference.dimensions.join('×')}</p>
      <pre class="prompt">${esc(s.prompt)}</pre>
      <p class="small">Download the reference and prompt, then use h3-apple 0.8.0:</p>
      <pre class="code">h3 generate --image reference.${s.id === 'N8' ? 'png' : 'jpg'} --prompt-file showcase-${key}.txt \\\n  --mode SOL --resolution 768p --no-x2 --aspect-ratio 16:9 \\\n  --duration ${s.generation.duration} --seed ${s.generation.seed} --output ${s.id}-native.mp4
h3 upscale --input ${s.id}-native.mp4 --duration 5 --output ${s.id}-detailed.mp4</pre>
      <p class="small">Native sources were generated with 0.7.0; restoration uses the recipe adopted in 0.8.0. Complete human playback found no new issues versus FP32; fine-texture differences remain. <a href="README.md#showcases">Builds, review and reproduction ↗</a></p>
      </details></div></article>`;
  }).join('');
  for (const video of $('showcase-cards').querySelectorAll('video')) {
    video.onerror = () => notice('Showcase unavailable. Reload or download the video.');
  }
  if (location.hash.startsWith('#showcase-')) requestAnimationFrame(() => document.getElementById(location.hash.slice(1))?.scrollIntoView());
}
function barRow(mode, value, maximum, label, note = '', low = null) {
  const width = 100 * value / maximum;
  const fill = low === null ? `<span class="bar-fill" style="width:${width}%"></span>`
    : `<span class="bar-fill range-base" style="width:${width}%"></span><span class="bar-fill range-end" style="left:${100 * low / maximum}%;width:${100 * (value-low) / maximum}%"></span>`;
  return `<div class="bar-row ${mode.toLowerCase()}"><strong class="bar-mode">${mode}</strong><div class="bar-track" aria-hidden="true">${fill}</div><span class="bar-value">${esc(label)}${note ? `<small>${esc(note)}</small>` : ''}</span></div>`;
}
function axis(middle, end) {
  return `<div class="bar-axis" aria-hidden="true"><span>0</span><span>${esc(middle)}</span><span>${esc(end)}</span></div>`;
}
function renderComparisons() {
  $('scores').innerHTML = `<section class="chart-card task-chart" aria-labelledby="task-title"><div class="chart-heading"><h3 id="task-title">Complete task success</h3><span>↑ Higher is better</span></div>
    <p class="chart-note">Every visual requirement must pass. 12 scenes × 2 profiles = 24 videos per mode.</p>
    ${axis('50%', '100%')}${Object.entries(scores.modes).map(([mode,s]) => barRow(mode, s.score, 100, `${percent(s.score)} · ${s.confirmed_passes}/${s.total} passed`, `${s.counts.fail} failed · ${s.counts.borderline} borderline`)).join('')}
    <p class="chart-note">Borderline results do not count as passes.</p></section>`;
  const profiles = [['Standard · 768p', 'V768', 'S768'], ['Fast · 544p + X2', 'VX', 'SX']];
  const timeMax = Math.ceil(Math.max(...Object.values(scores.routes).map(s => s.median_seconds)) / 120) * 120;
  const memoryMax = Math.ceil(Math.max(...Object.values(scores.routes).map(s => s.physical_gib_range?.[1] ?? 0)) / 10) * 10;
  $('time-chart').innerHTML = profiles.map(([name,...arms]) => `<div class="profile-chart"><h4>${name}</h4>${axis(`${timeMax/120} min`, `${timeMax/60} min`)}${arms.map(arm => {
    const s = scores.routes[arm], seconds = Math.round(s.median_seconds);
    return barRow(arm.startsWith('V') ? 'VSA' : 'SOL', s.median_seconds, timeMax, `${Math.floor(seconds/60)}m ${String(seconds%60).padStart(2,'0')}s`);
  }).join('')}</div>`).join('');
  $('memory-chart').innerHTML = profiles.map(([name,...arms]) => `<div class="profile-chart"><h4>${name}</h4>${axis(`${memoryMax/2} GiB`, `${memoryMax} GiB`)}${arms.map(arm => {
    const mode = arm.startsWith('V') ? 'VSA' : 'SOL', range = scores.routes[arm].physical_gib_range;
    return range ? barRow(mode, range[1], memoryMax, `${range.map(v => v.toFixed(1)).join('–')} GiB`, '', range[0]) : `<p>${mode}: memory not recorded</p>`;
  }).join('')}</div>`).join('');
  $('time-summary').textContent = `SOL speedup over VSA: ${scores.paired_time['V768/S768'].median_speedup.toFixed(2)}× standard · ${scores.paired_time['VX/SX'].median_speedup.toFixed(2)}× fast. Paired medians; one run per configuration.`;
  $('quality').innerHTML = Object.entries(dimensions).map(([key,name]) => `<section class="quality-chart" aria-labelledby="quality-${key}"><h4 id="quality-${key}">${name}</h4><p class="chart-note">${qualityNotes[key]}</p>${axis('50%', '100%')}${['VSA','SOL'].map(mode => {
    const q = scores.modes[mode].quality[key];
    return q ? barRow(mode, q.no_major_defect_percent, 100, `${percent(q.no_major_defect_percent)} · ${q.none_or_minor}/${q.evaluated}`) : `<p>${mode}: unrated</p>`;
  }).join('')}</section>`).join('');
}
function renderScores() {
  $('version').textContent = 'v' + data.version;
  const rows = data.cases.flatMap(c => c.runs), complete = rows.filter(r => r.video).length;
  $('inventory').textContent = `${data.cases.length} scenes`;
  $('output-count').textContent = `${rows.length} videos`;
  $('unique-videos').textContent = complete === rows.length ? 'All results included' : `${complete} generated · ${rows.length - complete} pending`;
  $('scope').textContent = data.method.scope;
  $('source').textContent = `Product 0.7.0 · ${data.primary.product_commit} · Dataset ${data.version} · ${data.date}`;
  if (data.download_url) { $('download-bundle').href = data.download_url; $('download-bundle').hidden = false; }
  if (!scores) {
    $('scores').innerHTML = '<p class="empty">Scores appear when all registered outputs have been generated and reviewed.</p>';
    $('scored-tables').hidden = true;
    $('score-download').hidden = true;
    return;
  }
  renderComparisons();
  $('routes').innerHTML = Object.entries(scores.routes).map(([arm,s]) => `<tr><td>${routes[arm]}</td><td><strong>${percent(s.score)}</strong></td><td>${s.confirmed_passes} / ${s.total}${s.counts.borderline ? ` (${s.counts.borderline} borderline)` : ''}</td><td>${s.median_seconds.toFixed(1)} s</td><td>${s.physical_gib_range ? s.physical_gib_range.map(n => n.toFixed(1)).join('–') + ' GiB' : 'Not recorded'}</td></tr>`).join('');
  $('paired-time').textContent = 'Paired median speedups (baseline / candidate): ' + Object.values(scores.paired_time).map(p => `${p.baseline} / ${p.candidate}: ${p.median_speedup.toFixed(2)}×`).join(' · ') + '. One run per configuration.';
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
  $('match-count').textContent = `${cases.length} scenes · 4 configurations each. Filters do not affect scores.`;
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
  if (!run.video) return '<p class="small">Inputs and seed are fixed; generation is pending.</p>';
  return `<details><summary>Review and frames</summary>
    <p class="summary">${esc(review.excerpt_en || review.summary || 'Awaiting visual review.')}</p>
    <ol>${criteria.map((text,i) => { const vote = review.criteria_pass[i]; return `<li><strong>${vote === true ? 'Pass' : vote === false ? 'Fail' : 'Uncertain'}</strong> — ${esc(text)}</li>`; }).join('')}</ol>
    <ul>${review.observations.map(o => `<li><strong>${o.interval_seconds.map(t => Number(t).toFixed(2)).join('–')} s</strong> — ${esc(o.text)}</li>`).join('')}</ul>
    <p class="small">${esc(review.review_scope)}</p>
    <p class="small">Severity (0 none · 1 minor · 2 clear · 3 severe): ${Object.entries(review.severity).map(([key,value]) => `${dimensions[key]} ${value}`).join(' · ')}</p>
    <ul>${[...run.sources,...(review.records || [])].map((s,i) => `<li><a href="${esc(s.path)}" target="_blank" rel="noopener">Evidence ${i+1} ↗</a> · ${esc(s.original_sha256.slice(0,12))}</li>`).join('')}</ul>
    <p class="small">All 120 sequential frames: ${(run.frame_evidence || []).map((s,i) => `<a href="${esc(s.path)}" target="_blank" rel="noopener">${i*40}–${i*40+39} ↗</a>`).join(' · ')}</p>
    ${(run.extra_frame_evidence || []).map(s => `<p class="small"><a href="${esc(s.path)}" target="_blank" rel="noopener">${esc(s.label)} ↗</a></p>`).join('')}</details>
    <details><summary>Settings and sources</summary><pre>${esc(JSON.stringify({source_sha256:run.source_sha256, model_identity:run.model_identity, video_sha256:run.video.sha256, request:run.request},null,2))}</pre></details>
    <p class="small"><a href="${esc(run.video.path)}" download>Download MP4 ↓</a></p>`;
}
function renderCase() {
  document.querySelectorAll('video').forEach(v => v.pause());
  const c = data.cases.find(c => c.id === selected);
  if (!c) { $('case').innerHTML = '<p class="empty">No matching cases. Adjust the filters.</p>'; return; }
  const runs = Object.keys(routes).map(arm => c.runs.find(r => r.arm === arm));
  $('case').innerHTML = `<div class="case-head"><div class="chips"><span class="chip">${esc(c.category)}</span><span class="chip">${esc(c.aspect_ratio)} · 5 seconds</span><span class="chip">Seed ${c.runs[0].seed}</span></div><h3>${esc(c.title)}</h3><p class="small">${esc(c.id)}</p></div>
    <div class="controls"><button id="play" class="primary">Play together</button><button id="pause">Pause</button><button id="restart">Restart</button><label>Audio<select id="audio"><option value="-1">Muted</option>${runs.filter(r => r.video).map(r => `<option value="${esc(r.arm)}">${esc(routes[r.arm])}</option>`).join('')}</select></label><label class="seek">Shared time <output id="clock">0.00 s</output><input id="seek" type="range" min="0" max="5" step="0.0416666667" value="0" aria-label="Shared video time"></label></div>
    <div class="videos ${c.aspect_ratio === '9:16' ? 'portrait' : ''}">${runs.map(r => `<section class="video-card">${r.video ? `<video data-arm="${esc(r.arm)}" controls playsinline preload="none" poster="${esc(r.poster)}" src="${esc(r.video.path)}" aria-label="${esc(c.title+' '+routes[r.arm])}"></video>` : '<div class="pending-video">Awaiting new generation</div>'}<div class="info"><h4>${routes[r.arm]}</h4><p class="small">${r.request.model_width}×${r.request.model_height} → ${r.request.width}×${r.request.height} · 24 fps</p><p><span class="chip ${esc(r.review.status)}">${statusNames[r.review.status]}</span></p><p class="small">${r.seconds == null ? 'Time pending' : r.seconds.toFixed(2)+' s API time'}${r.peak_physical_gib == null ? '' : ' · '+r.peak_physical_gib.toFixed(1)+' GiB sampled peak'}</p>${reviewDetails(r, c.criteria)}</div></section>`).join('')}</div>
    <section class="details-block"><h4>Pass criteria</h4><ol>${c.criteria.map(text => `<li>${esc(text)}</li>`).join('')}</ol></section>
    <section class="details-block"><h4>Exact prompt</h4><button id="copy-prompt">Copy prompt</button> <a href="${esc(c.prompt.path)}" download>TXT ↓</a><pre class="prompt">${esc(c.prompt_text)}</pre></section>
    <section class="details-block"><h4>Reference images</h4><div class="references">${c.references.map((r,i) => `<figure class="reference"><a href="${esc(r.path)}" download><img src="${esc(r.path)}" loading="lazy" alt="Picture ${i+1}: ${esc(r.credit.title || 'Reference')}"></a><figcaption><strong>Picture ${i+1}</strong> · ${esc(r.credit.title || 'Reference')}<br>${esc(r.credit.author || 'Not recorded')} · ${esc(r.credit.license)}<br><a href="${esc(r.path)}" download>Download original</a></figcaption></figure>`).join('')}</div><details><summary>Input sources and prompt history</summary><p>${esc(c.selection_note || '')}</p><pre>${esc(JSON.stringify(c.provenance,null,2))}</pre></details></section>
    <section class="details-block"><h4>Reproduce this task</h4><p class="small">Use the <a href="README.md#reproduce">frozen build</a>. This command checks inputs; add <code>--execute</code> to generate.</p><div class="controls"><label>Mode<select id="replay-mode"><option>VSA</option><option>SOL</option></select></label><label>Profile<select id="profile"><option value="standard">Standard 768p</option><option value="fast">Fast 544p + X2</option></select></label><button id="copy-command">Copy command</button></div><pre id="command" class="code"></pre></section>`;
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
renderShowcase(); renderScores(); filters();

}
