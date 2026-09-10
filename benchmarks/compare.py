#!/usr/bin/env python3
"""Run three existing CLIs, with a common cold-process delivery timer.

No models are downloaded or installed here. See local.example.json and README.md.
"""

import argparse
from contextlib import nullcontext
from dataclasses import asdict
from datetime import datetime, timezone
import copy
import csv
import json
import os
from pathlib import Path
import signal
import shutil
import subprocess
import sys
import time
import uuid

from h3_apple import resolve
from h3_apple.host import device_lock, snapshot
from h3_apple.io import digest
from h3_apple.media import tool, validate

HERE = Path(__file__).resolve().parent
METHODS = ("ours", "fastvideo", "vpipe")


def write_json(path, value):
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")
    temporary.replace(path)


def git_state(directory):
    def git(*args):
        return subprocess.check_output(["git", "-C", str(directory), *args],
                                       text=True, timeout=30).strip()
    return {"commit": git("rev-parse", "HEAD"), "tracked_changes": git("diff", "HEAD"),
            "status": git("status", "--porcelain")}


def verify_assets(method):
    """Recheck immutable preparation receipts; do not hash 100 GB during timing."""
    identities = []
    for receipt in method["asset_receipts"]:
        path = Path(receipt["path"])
        if digest(path) != receipt["sha256"]:
            raise ValueError(f"Asset receipt changed: {path}")
        data = json.loads(path.read_text())
        root = Path(receipt.get("root", path.parent)).resolve()
        for item in data["files"]:
            file = (root / item["path"]).resolve()
            if not file.is_relative_to(root):
                raise ValueError(f"Asset path escapes receipt root: {file}")
            stat = file.stat()
            if stat.st_size != item.get("bytes", item.get("size")):
                raise ValueError(f"Asset size changed: {file}")
            if stat.st_mtime_ns != item["mtime_ns"]:
                raise ValueError(f"Asset modification time changed: {file}")
            if len(item["sha256"]) != 64:
                raise ValueError(f"Missing preparation checksum: {file}")
        identities.append({"path": str(path), "sha256": receipt["sha256"],
                           "files": len(data["files"]),
                           "verification": "preparation SHA256; current size and mtime"})
    if not identities:
        raise ValueError("An audited asset receipt is required before comparison.")
    return identities


def preflight(method):
    command = method["command"]
    if not isinstance(command, list) or not command or not all(isinstance(x, str) for x in command):
        raise ValueError("command must be an argv array, not a shell string.")
    executable = Path(command[0])
    if not executable.is_absolute() or not executable.is_file() or not os.access(executable, os.X_OK):
        raise ValueError(f"Missing absolute executable: {executable}")
    if not Path(method["cwd"]).is_absolute() or not Path(method["cwd"]).is_dir():
        raise ValueError("cwd must be an existing absolute directory.")
    source = git_state(method["source_repo"])
    if source["commit"] != method["commit"] or source["tracked_changes"]:
        raise ValueError("Source differs from the configured clean commit.")
    for file in method.get("required_files", []):
        if not Path(file).is_file():
            raise ValueError(f"Missing required file: {file}")
    assets = verify_assets(method)
    if method["id"] == "vpipe" and digest(Path(method["pipeline_template"])) != method["pipeline_template_sha256"]:
        raise ValueError("Official vpipe template changed.")
    environment = None
    if executable.name.startswith("python"):
        environment = subprocess.check_output([str(executable), "-m", "pip", "freeze", "--all"],
                                              text=True, timeout=60).splitlines()
    return {"source": source, "executable_sha256": digest(executable),
            "assets": assets, "python_packages": environment,
            "weights": method["weights"], "recipe": method["recipe"],
            "local_patches": method.get("local_patches", [])}


def load_cases(path):
    suite = json.loads(path.read_text())
    cases = []
    names = set()
    for item in suite["cases"]:
        if item["id"] in names or not item["id"].replace("-", "").isalnum():
            raise ValueError("Case IDs must be unique simple names.")
        names.add(item["id"])
        prompt_file = (path.parent / item["prompt_file"]).resolve()
        if digest(prompt_file) != item["prompt_sha256"]:
            raise ValueError(f"Public prompt changed: {prompt_file}")
        request = asdict(resolve(prompt_file=prompt_file, seed=item["seed"],
                                 resolution=suite["resolution"], duration=suite["duration"]))
        cases.append({**item, "request": request, "prompt_file": str(prompt_file)})
    return suite, cases


def vpipe_input(method, request, output, destination):
    path = Path(method["pipeline_template"])
    if digest(path) != method["pipeline_template_sha256"]:
        raise ValueError("Official vpipe template changed.")
    template = json.loads(path.read_text())
    pipeline = copy.deepcopy(template)
    stages = {s["id"]: s for s in pipeline["stages"]}
    changes = {"text-prompt": {"text": request["prompt"]},
               "generate-video": {"width": request["model_width"],
                                  "height": request["model_height"],
                                  "frames": request["model_num_frames"], "seed": request["seed"]},
               "save-video": {"output_url": str(output)}}
    if method.get("model_key"):
        changes["model-select"] = {"hf_dir": method["model_key"]}
    for stage, values in changes.items():
        if stage not in stages or stages[stage]["type"] != stage:
            raise ValueError(f"Unexpected official template stage: {stage}")
        stages[stage]["config"].update(values)
    write_json(destination, pipeline)
    return changes


def expand_command(method, case, directory):
    request = case["request"]
    output = directory / ("output.mp4" if method["id"] == "ours" else "native.mp4")
    prompt_file = directory / "prompt.txt"
    # Copy exact bytes, including the original line ending; never shorten a prompt.
    prompt_file.write_bytes(Path(case["prompt_file"]).read_bytes())
    context = {"prompt": request["prompt"], "prompt_file": str(prompt_file),
               "seed": str(request["seed"]), "output": str(output),
               "prompt_cache": str(directory / "empty-prompt-cache"),
               "pipeline": str(directory / "input.vpipeline"),
               **{k: str(request[k]) for k in ("model_width", "model_height", "model_num_frames")}}
    changes = None
    if method["id"] == "vpipe":
        changes = vpipe_input(method, request, output, Path(context["pipeline"]))
    Path(context["prompt_cache"]).mkdir()
    command = [part.format_map(context) for part in method["command"]]
    return command, output, changes


def wait_ready(timeout):
    started = time.monotonic()
    while True:
        info = snapshot()
        if info["system"] != "Darwin":
            raise RuntimeError("The public comparison requires an Apple Silicon Mac.")
        if ("AC Power" in info["power"] and info["thermal"]["state"] == "nominal"
                and not info["thermal"]["low_power_mode"]):
            return info, time.monotonic() - started
        if time.monotonic() - started >= timeout:
            raise TimeoutError("Start conditions unmet: require AC, nominal thermals and low power off.")
        time.sleep(5)


def stop(process):
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
        process.wait(timeout=15)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.wait(timeout=15)
    except ProcessLookupError:
        process.wait(timeout=15)


def finish_native(source, destination, request):
    """Only center-crop and trim. Preserve the original official output beside it."""
    native = {**request, "width": request["model_width"], "height": request["model_height"],
              "num_frames": request["model_num_frames"]}
    validate(source, native)
    left = (native["width"] - request["width"]) // 2
    top = (native["height"] - request["height"]) // 2
    command = [tool("ffmpeg"), "-v", "error", "-nostdin", "-n", "-i", str(source),
               "-map", "0:v:0", "-map", "0:a:0", "-vf",
               f"format=rgb24,crop={request['width']}:{request['height']}:{left}:{top},setsar=1",
               "-frames:v", str(request["num_frames"]), "-t", str(request["duration"]),
               "-c:v", "libx264", "-preset", "fast", "-crf", "18", "-pix_fmt", "yuv420p",
               "-c:a", "aac", "-b:a", "192k", "-ar", "32000", "-ac", "2",
               "-movflags", "+faststart", str(destination)]
    subprocess.run(command, check=True, capture_output=True, timeout=300)
    return command


def run_job(method, case, directory, timeout, cooldown_timeout):
    directory.mkdir()
    row = {"method": method["id"], "label": method["label"], "case": case["id"],
           "status": "preflight", "elapsed_seconds": None, "quality_review": "pending",
           "directory": directory.name, "request": case["request"],
           "prompt_sha256": case["prompt_sha256"], "actual_nfe": None,
           "timings_seconds": None, "peak_memory_gib": None}
    process, started = None, None
    samples = []
    try:
        row["identity"] = preflight(method)
        command, output, changes = expand_command(method, case, directory)
        row.update(command=command, cwd=method["cwd"], pipeline_workload_changes=changes)
        write_json(directory / "run.json", row)
        # Ours' WORKER holds the same lock; acquiring it again here would deadlock.
        with (nullcontext() if method["id"] == "ours" else device_lock()):
            first, waiting = wait_ready(cooldown_timeout)
            row.update(initial_host=first, preparation_wait_seconds=waiting,
                       started_utc=datetime.now(timezone.utc).isoformat(), status="running")
            write_json(directory / "run.json", row)
            environment = {**os.environ, "HF_HUB_OFFLINE": "1", "TRANSFORMERS_OFFLINE": "1",
                           **method.get("env", {})}
            with (directory / "command.log").open("wb") as log:
                started = time.monotonic()
                process = subprocess.Popen(command, cwd=method["cwd"], env=environment,
                                           stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                           start_new_session=True)
                row["pid"] = process.pid
                while process.poll() is None:
                    if time.monotonic() - started >= timeout:
                        raise TimeoutError(f"Generation exceeded {timeout} seconds.")
                    sample = snapshot()
                    samples.append({"elapsed_seconds": time.monotonic() - started, **sample})
                    if sample["swap_bytes"] - first["swap_bytes"] > 2 * 1024**3:
                        raise RuntimeError("Swap grew more than 2 GiB.")
                    if sample["thermal"]["state"] in ("serious", "critical"):
                        raise RuntimeError("Thermal stop condition reached.")
                    if "AC Power" not in sample["power"] or sample["thermal"]["low_power_mode"]:
                        raise RuntimeError("Power conditions changed during generation.")
                    if shutil.disk_usage(directory).free < 20 * 1024**3:
                        raise RuntimeError("Less than 20 GiB free disk space remains.")
                    try:
                        process.wait(timeout=min(5, max(0.01, timeout - (time.monotonic() - started))))
                    except subprocess.TimeoutExpired:
                        pass
                row["returncode"] = process.returncode
                if process.returncode:
                    raise RuntimeError(f"Official/user CLI exited with {process.returncode}; see command.log.")
            final_output = directory / "output.mp4"
            if method["id"] != "ours":
                row["delivery_command"] = finish_native(output, final_output, case["request"])
            row["media"] = validate(final_output, case["request"])
            row["elapsed_seconds"] = time.monotonic() - started
            row["video"] = f"{directory.name}/output.mp4"
            row["video_sha256"] = digest(final_output)
            row["final_host"] = snapshot()
            if method["id"] == "ours":
                detail = json.loads((directory / "output.run.json").read_text())
                for field in ("actual_nfe", "timings_seconds", "peak_memory_gib", "vsa",
                              "package_source_sha256", "model_identity", "backend"):
                    row[field] = detail.get(field)
            else:
                row["internal_metrics_note"] = "Unknown unless the official entry reports them; see raw log."
            # Changes during execution invalidate the result rather than passing as a stable version.
            verify_assets(method)
            state = git_state(method["source_repo"])
            if state["commit"] != method["commit"] or state["tracked_changes"]:
                raise RuntimeError("Source changed during the run.")
            row["status"] = "complete"
    except KeyboardInterrupt:
        row.update(status="cancelled", error="Cancelled by user.", elapsed_seconds=None)
    except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
        row.update(status="failed" if started else "unavailable", error=str(error), elapsed_seconds=None)
    finally:
        if process is not None:
            stop(process)
            row["returncode"] = process.returncode
        if started is not None:
            row["attempt_seconds"] = time.monotonic() - started
        write_json(directory / "resources.json", samples)
        write_json(directory / "run.json", row)
    return row


def summarize(directory, results):
    write_json(directory / "results.json", results)
    fields = ("case", "method", "status", "elapsed_seconds", "quality_review", "video", "error")
    with (directory / "results.csv").open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(results["runs"])
    lines = ["# H3 comparison", "", "One cold process per case; timer ends after complete media validation.",
             "These are previously seen public inputs, not a held-out quality evaluation.", "",
             "| Prompt | Method | Status | Seconds | Video | Quality review |",
             "| --- | --- | --- | ---: | --- | --- |"]
    for row in results["runs"]:
        seconds = "—" if row["elapsed_seconds"] is None else f"{row['elapsed_seconds']:.3f}"
        video = f"[Play]({row['video']})" if row.get("video") else "—"
        label = row["label"].replace("|", "\\|")
        lines.append(f"| {row['case']} | {label} | {row['status']} | {seconds} | {video} | pending |")
    lines += ["", "See `results.json`, each `run.json`, and the original logs for identities and failures.",
              "Only complete deliveries have a time. A media pass is not human quality acceptance.", ""]
    for row in results["runs"]:
        if row.get("error"):
            lines.append(f"- {row['case']} / {row['method']}: {row['error']}")
    (directory / "README.md").write_text("\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=HERE / "local.json")
    parser.add_argument("--suite", type=Path, default=HERE / "suites/motion-bakery.json")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--methods", nargs="+", choices=METHODS, default=list(METHODS))
    parser.add_argument("--preflight", action="store_true", help="Check setup without running models.")
    args = parser.parse_args(argv)
    try:
        config = json.loads(args.config.read_text())
        for field in ("timeout_seconds", "cooldown_timeout_seconds"):
            if field in config and (type(config[field]) not in (int, float) or not 0 < config[field] < 86400):
                raise ValueError(f"{field} must be positive and less than one day.")
        suite, cases = load_cases(args.suite)
        methods = {x["id"]: x for x in config["methods"]}
        if set(methods) != set(METHODS) or len(config["methods"]) != 3:
            raise ValueError("Configure exactly Ours, official FastH3 and vpipe.")
        if args.preflight:
            checks = {}
            for name in args.methods:
                try:
                    checks[name] = {"ready": True, **preflight(methods[name])}
                except (OSError, ValueError, KeyError, RuntimeError, subprocess.SubprocessError) as error:
                    checks[name] = {"ready": False, "error": str(error)}
            print(json.dumps(checks, ensure_ascii=False, indent=2))
            return 0 if all(x["ready"] for x in checks.values()) else 1
        directory = (args.output or HERE.parent / ".local/comparisons" /
                     (datetime.now().strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6])).resolve()
        directory.mkdir(parents=True, exist_ok=False)
        write_json(directory / "config.json", config)
        write_json(directory / "suite.json", suite)
        results = {"schema_version": 1, "suite": suite, "runs": [],
                   "timer": "fresh process launch through complete AV validation; no cache deletion",
                   "comparison": "systems with their declared recipes, not an attention-only ablation"}
        summarize(directory, results)
        for case in cases:
            for name in args.methods:
                print(f"{case['id']} / {name}: starting; evidence {directory}", flush=True)
                row = run_job(methods[name], case, directory / f"{case['id']}-{name}",
                              config.get("timeout_seconds", 10800),
                              config.get("cooldown_timeout_seconds", 1800))
                results["runs"].append(row)
                summarize(directory, results)
                print(f"{case['id']} / {name}: {row['status']}", flush=True)
                if row["status"] == "cancelled":
                    return 130
        print(directory / "README.md")
        return 0 if all(row["status"] == "complete" for row in results["runs"]) else 1
    except (OSError, ValueError, KeyError, subprocess.SubprocessError) as error:
        print(f"Comparison setup: {error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
