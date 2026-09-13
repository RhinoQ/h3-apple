"""Download a study's public inputs, verify them, and run its pinned H3 build.

The source prompt is fetched from fal on the reader's machine. This script does
not contain the source article or its prompts. Input downloads never load model
weights; model preparation is a separate, explicit step in REPRODUCE.md.
"""
from __future__ import annotations

import argparse
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

SITE = "https://rhinoq.github.io/h3-apple/"
GUIDE = "https://fal.ai/learn/devs/minimax-h3-prompting-guide"
PATH_FIELDS = {"base_directory", "adapter_path", "gate_source"}


def digest(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(url, limit):
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname not in {"fal.ai", "v3b.fal.media", "rhinoq.github.io"}:
        raise ValueError("Unexpected source URL")
    request = Request(url, headers={"User-Agent": "H3-Apple-Reproduction/1.0"})
    with urlopen(request, timeout=90) as response:
        data = response.read(limit + 1)
    if len(data) > limit:
        raise ValueError("Source exceeded its expected size")
    return data


class PromptParser(HTMLParser):
    def __init__(self, title):
        super().__init__(convert_charrefs=True)
        self.title, self.current, self.field = title, False, ""
        self.capture, self.parts, self.paragraphs = None, [], []

    def handle_starttag(self, tag, attrs):
        if tag in {"h2", "h3", "h4", "p"}:
            self.capture, self.parts = tag, []

    def handle_data(self, data):
        if self.capture:
            self.parts.append(data)

    def handle_endtag(self, tag):
        if tag != self.capture:
            return
        value = "".join(self.parts).strip()
        self.capture = None
        if tag in {"h2", "h3", "h4"}:
            self.current = tag == "h4" and value == self.title
            self.field = ""
        elif self.current:
            if value.lower() in {"prompt", "reference images", "reference image", "reference video",
                    "reference videos", "source video", "source videos", "reference audio", "endpoint"}:
                self.field = value.lower()
            elif self.field == "prompt":
                self.paragraphs.append(value)


def prompt_from_html(page, record):
    parser = PromptParser(record["source_case"])
    parser.feed(page)
    prompt = "\n\n".join(parser.paragraphs)
    if hashlib.sha256(prompt.encode()).hexdigest() != record["prompt_sha256"]:
        raise ValueError("The source prompt changed or could not be extracted. Supply the original --prompt-file; do not silently run different text.")
    return prompt


def safe_file(directory, name):
    if Path(name).name != name or name in {"", ".", ".."}:
        raise ValueError("Unsafe input filename")
    return directory / name


def write_once(path, data):
    if path.exists():
        if path.read_bytes() != data:
            raise FileExistsError(f"Different content already exists: {path}")
        return
    with path.open("xb") as stream:
        stream.write(data)


def download_inputs(args):
    record_bytes = (args.record.read_bytes() if args.record else
                    fetch(urljoin(SITE, f"records/{args.case:02}.json"), 200_000))
    record = json.loads(record_bytes)
    if record["case"] != args.case:
        raise ValueError("Case and record disagree")
    if args.prompt_file:
        prompt = args.prompt_file.read_text()
        if hashlib.sha256(prompt.encode()).hexdigest() != record["prompt_sha256"]:
            raise ValueError("Prompt file does not match the recorded input")
    else:
        page = args.guide_html.read_text() if args.guide_html else fetch(GUIDE, 4_000_000).decode()
        prompt = prompt_from_html(page, record)
    references = record["reproduction"]["references"]
    if sum(item["bytes"] for item in references) > 500_000_000:
        raise ValueError("Unexpectedly large reference download")
    args.directory.mkdir(parents=True, exist_ok=True)
    write_once(args.directory / "case.json", record_bytes)
    write_once(args.directory / "prompt.txt", prompt.encode())
    for item in references:
        path = safe_file(args.directory, item["filename"])
        if path.exists():
            if digest(path) != item["sha256"]:
                raise ValueError(f"Existing input does not match: {path}")
            continue
        data = fetch(item["url"], item["bytes"])
        if len(data) != item["bytes"] or hashlib.sha256(data).hexdigest() != item["sha256"]:
            raise ValueError(f"Reference changed: {item['label']}")
        write_once(path, data)
    model = record["reproduction"]["model_manifest"]
    write_once(args.directory / "model.json", fetch(urljoin(SITE, model), 500_000))
    print(f"Verified case {args.case:02}: prompt + {len(references)} references in {args.directory}")
    print("Open prompt.txt to read it, or load it into this case's prompt panel on the gallery. No text is uploaded.")


def generation_kwargs(record, directory):
    prompt_path = directory / "prompt.txt"
    if digest(prompt_path) != record["prompt_sha256"]:
        raise ValueError("Prompt does not match the recorded generation")
    kwargs = dict(record["reproduction"]["parameters"], prompt=prompt_path.read_text())
    for item in record["reproduction"]["references"]:
        path = safe_file(directory, item["filename"]).resolve()
        if digest(path) != item["sha256"]:
            raise ValueError(f"Reference does not match: {item['label']}")
        key = item["argument"]
        if key in {"first_frame", "last_frame"}:
            kwargs[key] = str(path)
        elif key in {"reference_images", "reference_videos", "reference_audio"}:
            kwargs.setdefault(key, []).append(str(path))
        else:
            raise ValueError("Unsupported reference argument")
    return kwargs


def run(args):
    from h3_apple import __version__, generate, resolve
    from h3_apple.assets import load_assets
    from h3_apple.progress import ProgressBar
    from h3_apple.worker import source_identity

    record = json.loads((args.directory / "case.json").read_text())
    runtime = record["reproduction"]["runtime"]
    if __version__ != runtime["version"] or source_identity() != runtime["source_sha256"]:
        raise ValueError(f"Install the recorded runtime commit {runtime['commit']} first; see REPRODUCE.md.")
    expected = json.loads((args.directory / "model.json").read_text())
    model = load_assets(args.model_dir)
    actual = {f["path"]: (f["sha256"], f["size"]) for f in model["files"]}
    if any(actual.get(f["path"]) != (f["sha256"], f["size"]) for f in expected["files"]):
        raise ValueError("Model files differ from the recorded study; see REPRODUCE.md.")
    if expected.get("recipe_file"):
        recipe = json.loads((args.model_dir / expected["recipe_file"]).read_text())
        if {k: v for k, v in recipe.items() if k not in PATH_FIELDS} != expected["recipe"]:
            raise ValueError("Conditioning recipe differs from the recorded study")
    kwargs = generation_kwargs(record, args.directory)
    resolved = resolve(**kwargs)
    if resolved.task != record["reproduction"]["task"]:
        raise ValueError("Resolved task differs from the record")
    if args.check_only:
        print(f"Case {record['case']:02}: inputs, runtime source, model manifest and request PASS; no model generation performed.")
        return
    generate(**kwargs, model_dir=args.model_dir, output=args.output, on_progress=ProgressBar(), timeout=7200)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="action", required=True)
    inputs = commands.add_parser("inputs", help="Fetch only the prompt and reference media")
    inputs.add_argument("--case", type=int, choices=range(1, 45), required=True)
    inputs.add_argument("--directory", type=Path, required=True)
    inputs.add_argument("--record", type=Path, help="Use an already downloaded case record")
    inputs.add_argument("--guide-html", type=Path, help="Use a saved copy of the original guide")
    inputs.add_argument("--prompt-file", type=Path, help="Use the exact recorded prompt instead of extracting it")
    generate = commands.add_parser("run", help="Generate using an already prepared model")
    generate.add_argument("--directory", type=Path, required=True)
    generate.add_argument("--model-dir", type=Path, required=True)
    generate.add_argument("--output", type=Path)
    generate.add_argument("--check-only", action="store_true")
    args = parser.parse_args()
    if args.action == "inputs":
        download_inputs(args)
    else:
        if not args.check_only and args.output is None:
            parser.error("run requires --output unless --check-only is used")
        run(args)


if __name__ == "__main__":
    main()
