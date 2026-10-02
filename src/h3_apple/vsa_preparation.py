"""Prepare VSA from pinned Ref2VA sources or a verified original MLX bundle."""
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time

from .assets import data_file
from .host import check_machine, device_lock, snapshot
from .io import write_json
from .preparation import LIMIT, RESERVE, cache_path, materialize, source_plan
from .vsa_assets import import_assets, load_assets, model_directory


def ensure_ready(model_dir=None, *, allow_large_download=False, progress=None, request=None):
    from .api import DownloadApprovalRequired
    from .media import check_runtime
    from .runtime.backend import check_dependencies
    if type(allow_large_download) is not bool:
        raise ValueError("allow_large_download must be a boolean.")
    check_machine(snapshot(), request)
    check_dependencies()
    progress = progress or (lambda event: None)
    spec = plan(model_dir, progress=progress)
    if spec["download_bytes"] > LIMIT and not allow_large_download:
        raise DownloadApprovalRequired(spec)
    check_runtime()
    if spec["status"] != "ready":
        progress(dict(spec, phase="model_plan"))
    return prepare(spec, allow_large_download=allow_large_download, progress=progress)


def plan(model_dir=None, reuse_dirs=(), progress=None):
    progress = progress or (lambda event: None)
    directory = model_directory(model_dir)
    if (directory / "bundle.json").is_file():
        data = load_assets(directory)
        return dict(status="ready", directory=str(directory), identity=data["identity"],
                    download_bytes=0, additional_disk_bytes=0)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"Choose an empty VSA model directory: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    roots = [Path(p).expanduser().resolve() for p in reuse_dirs]
    if not roots:
        roots = sorted((Path.home() / "Models").glob("h3-apple*"))
    for root in roots:
        if not (root / "bundle.json").is_file():
            continue
        try:
            data = load_assets(root)
        except (OSError, ValueError):
            continue
        progress(dict(phase="checking_local_models", file=str(root)))
        data = load_assets(root, verify=True)
        copies = sum(e["size"] for e in data["files"]
                     if (root / e["path"]).stat().st_dev != directory.parent.stat().st_dev)
        return dict(status="reuse_prepared", directory=str(directory), prepared=data,
                    download_bytes=0, additional_disk_bytes=copies + RESERVE)
    entries = data_file("model-sources.json")["sources"] + data_file("vsa-gates.json")
    cache = directory.parent / ".sources"
    groups, downloads, copies = source_plan(entries, cache, reuse_dirs, progress)
    # Original BF16 text and image-encoder files are hard-linked from the source
    # cache. Allow conversion scratch plus a full independent bundle as headroom.
    return dict(status="preparation_required", directory=str(directory), cache_dir=str(cache),
                groups=groups, download_bytes=downloads,
                additional_disk_bytes=downloads + copies + 190 * 10**9 + RESERVE)


def convert(native, adapter, gates, work, progress):
    from .process import _stop
    output = work / "converted"
    command = [sys.executable, "-m", "h3_apple.vsa_conversion", "--native", str(native),
               "--adapter", str(adapter), "--gate-source", str(gates), "--output", str(output)]
    env = dict(os.environ, MLX_ENABLE_TF32="0", MLX_METAL_GPU_ARCH="",
               HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
    initial, started = snapshot(), time.monotonic()
    progress(dict(phase="preparing_models", file=str(work / "preparation.log")))
    with (work / "preparation.log").open("x") as log:
        child = subprocess.Popen(command, env=env, stdin=subprocess.DEVNULL,
                                 stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
        try:
            while child.poll() is None:
                if time.monotonic() - started > 3600:
                    raise TimeoutError(f"VSA conversion exceeded one hour; see {work}")
                current = snapshot()
                if current["swap_bytes"] - initial["swap_bytes"] > 2 * 1024**3:
                    raise RuntimeError("VSA conversion stopped: swap grew more than 2 GiB.")
                if current["thermal"]["state"] in ("serious", "critical"):
                    raise RuntimeError("VSA conversion stopped: serious thermal pressure.")
                if shutil.disk_usage(work).free < RESERVE:
                    raise OSError("VSA conversion stopped: insufficient disk space.")
                try:
                    child.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    pass
            if child.returncode:
                raise RuntimeError(f"VSA conversion failed; see {work / 'preparation.log'}")
        finally:
            _stop(child)
    return output


def prepare(spec, *, allow_large_download=False, progress=None):
    from .media import check_runtime
    from .runtime.backend import check_dependencies
    from .api import DownloadApprovalRequired
    if spec["download_bytes"] > LIMIT and not allow_large_download:
        raise DownloadApprovalRequired(spec)
    check_machine(snapshot())
    check_dependencies()
    check_runtime()
    progress = progress or (lambda event: None)
    directory = Path(spec["directory"])
    if shutil.disk_usage(directory.parent).free < spec["additional_disk_bytes"]:
        raise OSError("Insufficient free disk for VSA preparation; see h3 prepare --mode VSA --plan.")
    with device_lock():
        if (directory / "bundle.json").is_file():
            return load_assets(directory)
        if spec["status"] == "reuse_prepared":
            source = load_assets(spec["prepared"]["directory"])
            if source["identity"] != spec["prepared"]["identity"]:
                raise ValueError("VSA reuse source changed after planning.")
            return import_assets(source["checkpoint"], source["components"], source["ref2va_native"],
                                 directory, progress=progress,
                                 provenance=dict(kind="verified_local_reuse", source_identity=source["identity"]))
        work = Path(tempfile.mkdtemp(prefix=".h3-VSA-prepare-", dir=directory.parent))
        write_json(work / "plan.json", spec)
        cache = materialize(spec, progress)
        base = next(e for e in data_file("model-sources.json")["sources"]
                    if e["filename"] == "Ref2VA/model_index.json")
        native = cache_path(cache, base).parent
        adapter = cache_path(cache, data_file("prepared-model.json")["adapter"])
        gate = next(e for e in data_file("vsa-gates.json") if e["filename"].endswith(".safetensors"))
        converted = convert(native, adapter, cache_path(cache, gate), work, progress)
        import json
        receipt = json.loads((converted / "conversion.json").read_text())
        data = import_assets(converted / "dit", converted / "components", native, directory,
                             progress=progress, provenance=dict(kind="source_preparation", conversion=receipt,
                             sources=data_file("model-sources.json")["sources"] + data_file("vsa-gates.json")))
        # Published files are verified hard links. Only successful scratch output
        # is removed; failed conversions and their diagnostics remain available.
        shutil.rmtree(converted)
        return data
