"""Export an allowlisted, static gallery from private local generation records.

Run with the project's Conda Python. Reference URLs are linked and previewed at
their source. The user authorized publication of the exact run prompts.
Private paths, environment logs and the surrounding article stay local.
"""
from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import html
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote, urlparse

TITLES = [
    "Through the binoculars", "A jump into deep space", "The silent gateway", "Desert departure",
    "After the fire", "Jazz after midnight", "A guest in the kitchen", "After-hours laundry",
    "Cut to the beat", "Into a fairytale", "Artwork in motion", "Secrets in the snow",
    "Across the dinner table", "The forbidden wing", "Future in focus", "Made for the working day",
    "Equip. Confirm. Enter.", "Built for speed", "Lights on", "A product comes into view",
    "A leap over lava", "A hero in blue", "Meet the leading man", "At the perimeter",
    "Before and after the show", "A quiet evening", "Six assets, one sequence", "A voxel interruption",
    "From coffee to dunes", "Foam at the kitchen sink", "A new dancer", "Three capybaras",
    "A different voice", "A different companion", "One more teammate", "A change of cast",
    "A new world behind the action", "After sunset", "Beyond the window", "A different line",
    "Several changes, one scene", "New product. New sign. New line.", "A change of costume", "Drawn into the scene",
]
GROUPS = [
    (1, "Film & campaigns"), (6, "Motion & visual play"), (12, "Stories & performance"),
    (15, "Product studies"), (17, "Interfaces in motion"), (21, "Animation & games"),
    (27, "Mixed references"), (30, "Movement & identity"), (33, "Voice reference"),
    (34, "Cast & object edits"), (37, "Environment & lighting"), (40, "Dialogue"), (41, "Directed edits"),
]
BLOCKERS = {
    "requires_frame_conditioning": "First and last frame conditioning is not available in this product build.",
    "requires_multimodal_reference": "This request needs video or audio reference input support.",
    "requires_original_aspect_ratio": "The source uses a portrait canvas; the frozen product API accepts landscape output only.",
    "source_prompt_mentions_unpublished_reference_video": "The source prompt mentions a reference video that is not supplied on the page.",
}
SOURCE = "https://fal.ai/learn/devs/minimax-h3-prompting-guide"
RUNTIMES = {
    "0.1.0.dev2": {"version": "0.1.0.dev2", "commit": "f35a34ad06df0ba3f9403c317e853fdf3383ad0e",
                   "source_sha256": "b1b7b47891daf4fb5b5c76091004536865a26df2ae0b3525281adf5b04198ace", "directory": "h3-apple-dev2"},
    "0.1.0.dev3+guide2": {"version": "0.1.0.dev3+guide2", "commit": "40572ed48fa1904178453214b3afe7032e48b860",
                          "source_sha256": "faf953a71eeadd70b480049e6efd224d37504fb1cf1fde15936d67220a6ed916", "directory": "h3-apple-guide2"},
}


def esc(value):
    return html.escape(str(value), quote=True)


def runtime(seconds):
    seconds = round(seconds)
    return f"{seconds // 60} min {seconds % 60:02d} s"


def atomic(path, content):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(content)
    temporary.replace(path)


def reproduction(case, run):
    portrait = case["source_geometry"]["height"] > case["source_geometry"]["width"]
    frames = case["product_status"] == "requires_frame_conditioning"
    stable = case["product_status"].startswith("supported_") and not portrait and case["number"] != 15
    version = "0.1.0.dev2" if stable else "0.1.0.dev3+guide2"
    parameters = dict(seed=42, resolution="576p", duration=min(360, max(120, round(case["source_geometry"]["duration"] * 24))) / 24)
    if not stable:
        parameters["aspect_ratio"] = "9:16" if portrait else "16:9"
    references = []
    for key, kind in (("reference_images", "Image"), ("reference_videos", "Video"), ("reference_audio", "Audio")):
        for index, asset in enumerate(case[key], 1):
            url = asset["src"]
            parsed = urlparse(url)
            assert parsed.scheme == "https" and parsed.hostname == "v3b.fal.media"
            suffix = Path(parsed.path).suffix
            assert suffix in {".webp", ".jpg", ".jpeg", ".png", ".mp4", ".mov", ".wav", ".mp3", ".m4a"}
            argument = ("first_frame" if index == 1 else "last_frame") if frames else key
            label = ("First frame" if index == 1 else "Last frame") if frames else f"{kind} {index}"
            references.append(dict(label=label, argument=argument, index=index, media_type=kind.lower(),
                filename=f"{kind.lower()}-{index:02}{suffix}", url=url, sha256=asset["local"]["sha256"], bytes=asset["local"]["bytes"]))
    task = "fl2va" if frames else ("ref2va" if references else "t2va")
    if run["status"] == "generated":
        metadata = json.loads((Path(run["directory"]) / "output.run.json").read_text())
        assert hashlib.sha256(metadata["request"]["prompt"].encode()).hexdigest() == case["prompt_sha256"]
        assert metadata["package_source_sha256"] == RUNTIMES[version]["source_sha256"]
        assert metadata["request"]["task"] == task
        assert all(metadata["request"][key] == value for key, value in parameters.items() if key != "aspect_ratio")
        assert sorted(x["sha256"] for x in references) == sorted(x["sha256"] for x in metadata.get("reference_inputs", []))
    return dict(configuration_state="executed" if run["status"] == "generated" else "planned",
                runtime=RUNTIMES[version], parameters=parameters, references=references, task=task,
                model_manifest=f"models/{task}.json")


def reproduction_panel(record):
    number = record["case"]
    slug = f"{number:02}"
    recipe = record["reproduction"]
    parts = ['<div class="reproduction"><h4>Reproduce this video</h4>']
    if recipe["configuration_state"] != "executed":
        parts.append('<p class="small-note">Planned inputs and command. This case has not yet produced a validated result.</p>')
    parts.append(f'<div class="prompt-panel"><div class="command-header"><h5>Prompt</h5><button type="button" data-copy="prompt-{slug}">Copy prompt</button></div><pre class="prompt-text" id="prompt-{slug}">{esc(record["prompt"])}</pre><p class="small-note">Source: <a href="{esc(record["source"])}">fal’s H3 prompting guide ↗</a>. Exact text used for this local request.</p></div>')
    parts.append('<h5>Reference inputs · in supplied order</h5>')
    if not recipe["references"]:
        parts.append('<p class="small-note">Text only; no reference media.</p>')
    else:
        parts.append('<div class="reference-grid">')
        for item in recipe["references"]:
            url, label = esc(item["url"]), esc(item["label"])
            parts.append('<figure class="reference">')
            if item["media_type"] == "image":
                parts.append(f'<a href="{url}" target="_blank" rel="noopener noreferrer"><img src="{url}" alt="{label}, case {slug}" loading="lazy" decoding="async" referrerpolicy="no-referrer" width="320" height="180"></a>')
            elif item["media_type"] == "video":
                parts.append(f'<video controls playsinline preload="none" src="{url}" aria-label="{label}, case {slug}"></video>')
            else:
                parts.append(f'<audio controls preload="none" src="{url}" aria-label="{label}, case {slug}"></audio>')
            parts.append(f'<figcaption><strong>{label}</strong><a href="{url}">Open original ↗</a></figcaption></figure>')
        parts.append('</div><p class="small-note">References are served by the original publisher. Downloads verify their recorded SHA-256 hashes.</p>')
    environment = recipe["runtime"]["directory"]
    command = ("curl -fL https://rhinoq.github.io/h3-apple/reproduce.py -o reproduce.py\n"
               f"./{environment}/.local/envs/h3/bin/python reproduce.py inputs --case {number} --directory case-{slug}\n"
               f'./{environment}/.local/envs/h3/bin/python reproduce.py run --directory case-{slug} --model-dir "$HOME/Models/h3-apple-{recipe["task"]}" --output case-{slug}/run-01.mp4')
    parts.append(f'<div class="command-header"><h5>Generation command</h5><button type="button" data-copy="command-{slug}">Copy command</button></div><p class="small-note">First complete the <a href="https://github.com/RhinoQ/h3-apple/blob/gh-pages/REPRODUCE.md">runtime and model setup</a>. Required build: <a href="https://github.com/RhinoQ/h3-apple/tree/{recipe["runtime"]["commit"]}">{esc(recipe["runtime"]["version"])}</a>. Models are prepared separately; this command downloads only prompt and reference inputs.</p><pre class="command"><code id="command-{slug}">{esc(command)}</code></pre>')
    parts.append('<details class="api-call"><summary>Python API call and exact parameters</summary><pre><code>')
    kwargs = ["from pathlib import Path", "from h3_apple import generate", "from h3_apple.progress import ProgressBar", "", "generate(", f'    prompt=Path("case-{slug}/prompt.txt").read_text(),']
    kwargs += [f"    {key}={value!r}," for key, value in recipe["parameters"].items()]
    for argument in ("first_frame", "last_frame", "reference_images", "reference_videos", "reference_audio"):
        values = [f'case-{slug}/{item["filename"]}' for item in recipe["references"] if item["argument"] == argument]
        if values:
            kwargs.append(f"    {argument}={(values[0] if argument.endswith('_frame') else values)!r},")
    kwargs += [f'    model_dir=Path.home() / "Models/h3-apple-{recipe["task"]}",', f'    output="case-{slug}/run-01.mp4",', "    on_progress=ProgressBar(),", "    timeout=7200,", ")"]
    parts.append(esc("\n".join(kwargs)) + '</code></pre></details></div>')
    return "\n".join(parts)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inventory", type=Path, required=True)
    ap.add_argument("--state", type=Path, action="append", required=True)
    args = ap.parse_args()
    root = Path(__file__).resolve().parent
    inventory = json.loads(args.inventory.read_text())
    runs = {}
    for path in args.state:
        for record in json.loads(path.read_text())["cases"]:
            previous = runs.get(record["number"])
            if previous is None or previous["status"] != "generated":
                runs[record["number"]] = record
    assert len(inventory["cases"]) == len(TITLES) == 44
    (root / "media").mkdir(exist_ok=True)
    (root / "records").mkdir(exist_ok=True)
    template = (root / "layout.html").read_text()
    count = Counter(r["status"] for r in runs.values())
    nav = '<a href="#overview">Overview</a>' + "".join(f'<a href="#group-{n}">{esc(title)}</a>' for n, title in GROUPS)
    nav += '<a href="#method">Generation method</a><a href="#sources">Source &amp; attribution</a>'
    public_cases = []
    content = ['<section id="overview" class="overview"><div class="section-label">THE REPRODUCTION LOG</div><h2>Every case, accounted for.</h2>',
               f'<p class="collection-state"><strong>{count["generated"]} available</strong><span>{count["queued"] + count["running"] + count["cancelled"]} in the generation queue</span><span>{count["blocked"] + count["failed"]} need further work</span></p>',
               '<p>Watch the local results below, or open a case to see its current input requirements. The collection keeps the source order.</p></section>']
    starts = dict(GROUPS)
    for case in inventory["cases"]:
        number = case["number"]
        run = runs[number]
        slug = f'{number:02d}'
        if number in starts:
            content.append(f'<section class="case-group" id="group-{number}"><div class="section-label">{slug} / STUDIES</div><h2>{esc(starts[number])}</h2></section>')
        inputs = {k.removeprefix("reference_"): len(case[k]) for k in ("reference_images", "reference_videos", "reference_audio")}
        input_text = ", ".join(f'{n} {kind[:-1] if n == 1 and kind != "audio" else kind}' for kind, n in inputs.items() if n) or "Text only"
        if case["product_status"] == "requires_frame_conditioning":
            input_text = "First + last frame" if inputs["images"] == 2 else "First frame"
        source_link = SOURCE + "#:~:text=" + quote(case["source_title"], safe="")
        notes = [BLOCKERS.get(x, x) for x in run.get("blockers", []) + run.get("deviations", [])]
        record = {"case": number, "title": TITLES[number - 1], "source_case": case["source_title"], "source": source_link,
                  "status": run["status"], "required_inputs": inputs, "source_geometry": case["source_geometry"],
                  "prompt": case["prompt"], "prompt_sha256": case["prompt_sha256"], "notes": notes}
        assert hashlib.sha256(record["prompt"].encode()).hexdigest() == record["prompt_sha256"]
        record["reproduction"] = reproduction(case, run)
        status = {"generated": "Generated", "running": "Generating", "queued": "Queued", "cancelled": "Queued for restart", "blocked": "Input support required", "failed": "Generation failed"}[run["status"]]
        title = f'<span class="case-number">{slug}</span>{esc(TITLES[number - 1])}'
        if run["status"] == "generated":
            directory = Path(run["directory"])
            metadata = json.loads((directory / "output.run.json").read_text())
            r = metadata["request"]
            target = root / "media" / f"{slug}-output.mp4"
            if not target.exists():
                shutil.copyfile(directory / "output.mp4", target)
            poster = root / "media" / f"{slug}-poster.jpg"
            if not poster.exists():
                from h3_apple.media import tool
                subprocess.run([tool("ffmpeg"), "-v", "error", "-ss", "2", "-i", str(target), "-frames:v", "1", "-q:v", "3", str(poster)], check=True)
            record.update({k: metadata[k] for k in ("seed", "started_utc", "elapsed_seconds", "actual_nfe", "video_sha256", "package_source_sha256", "timings_seconds", "peak_memory_gib")})
            record["request"] = {k: r[k] for k in ("resolution", "duration", "width", "height", "num_frames", "fps", "num_steps", "preset_version", "task")}
            record["reused_verified_run"] = bool(run.get("reused_from"))
            record["model_identity"] = metadata["model_identity"]
            record["input_hashes"] = [{k: item[k] for k in ("kind", "index", "anchor", "sha256", "size") if k in item}
                                      for item in metadata.get("reference_inputs", [])]
            record["runtime_version"] = run.get("runtime_version", "0.1.0.dev2")
            conditioned = metadata.get("fl2va", metadata.get("ref2va", {}))
            record["attention"] = conditioned.get("attention", "vsa")
            record["experimental_input_support"] = bool(conditioned.get("experimental", False) or "guide" in record["runtime_version"])
            record["creative_quality_review"] = "Not independently rated for this collection"
            content.append(f'<section class="case" id="case-{slug}"><h3>{title}</h3><figure class="result"><video controls playsinline preload="none" poster="media/{slug}-poster.jpg" width="{r["width"]}" height="{r["height"]}" aria-label="{esc(TITLES[number-1])}, H3 Apple output"><source src="media/{slug}-output.mp4" type="video/mp4"></video><figcaption><span>H3 Apple output</span><span>{r["duration"]:g} s · {r["resolution"]} · {r["fps"]} fps · stereo</span></figcaption></figure>')
            content.append(f'<dl class="run-facts"><div><dt>Input</dt><dd>{esc(input_text)}</dd></div><div><dt>Sampling</dt><dd>{r["num_steps"]} steps · seed {r["seed"]}</dd></div><div><dt>Generation time</dt><dd>{runtime(metadata["elapsed_seconds"])}</dd></div></dl>')
            content.append(f'<p class="runtime-note">{esc(r["task"].upper())} · {esc(record["attention"].upper())} attention · H3 Apple {esc(record["runtime_version"])}</p>')
            if number == 15:
                notes = ["Generated with the three published reference images. The source prompt also mentions a reference video that the page does not provide; this input is missing from the local reproduction."]
            if case["source_geometry"]["duration"] < 5:
                notes.append("The source output is shorter than the runtime’s five-second minimum. This local reproduction is five seconds long.")
            if notes:
                content.append('<div class="case-note">' + ''.join(f'<p>{esc(note)}</p>' for note in notes) + '</div>')
            if run.get("reused_from"):
                note = "Reused from a verified earlier run; the original generation time is retained."
                if number == 1:
                    note += " Reference order follows the source page: architecture, person, flag, close-up."
                content.append(f'<div class="case-note"><p>{note}</p></div>')
        else:
            content.append(f'<details class="pending-case" id="case-{slug}"><summary><span class="pending-title">{title}</span><span class="status">{status}</span></summary><div class="pending-body"><p><strong>Required input:</strong> {esc(input_text)}.</p>')
            if not notes:
                notes = ["This fixed-seed generation is in progress." if run["status"] == "running" else "This case is waiting for the local generation worker."]
                if run["status"] == "failed":
                    notes = ["The attempt did not produce a validated output. Its failure remains in the experiment record."]
            content += [f'<p>{esc(note)}</p>' for note in notes]
        record["notes"] = notes
        content.append(reproduction_panel(record))
        content.append(f'<div class="case-links"><a href="{esc(source_link)}">Source prompt &amp; inputs ↗</a><a href="records/{slug}.json">Case record ↗</a></div>')
        content.append('</section>' if run["status"] == "generated" else '</div></details>')
        atomic(root / "records" / f"{slug}.json", json.dumps(record, ensure_ascii=False, indent=2) + "\n")
        public_cases.append(record)
    page = template.replace("{{CASES}}", "\n".join(content)).replace("{{CONTENTS}}", nav).replace("{{GENERATED}}", str(count["generated"]))
    assert "{{" not in page
    atomic(root / "index.html", page)
    atomic(root / "collection.json", json.dumps({"source": SOURCE, "status_counts": dict(count), "cases": public_cases}, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(count)))


if __name__ == "__main__":
    main()
