"""Pinned model downloads, local reuse and one isolated conversion process."""

from collections import defaultdict
from importlib.resources import files
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from urllib.parse import quote
from urllib.request import Request, urlopen

from .assets import import_assets, load_assets, model_directory
from .host import check_machine, device_lock, snapshot
from .io import digest, write_json

LIMIT = 20_000_000_000
RESERVE = 2 * 1024**3


def source_manifest():
    return json.loads(files("h3_apple").joinpath("data/model-sources.json").read_text())


def cache_path(cache, entry):
    return cache / entry["repo"].replace("/", "--") / entry["revision"] / entry["filename"]


def partial_path(destination, checksum):
    return destination.with_name(destination.name + "." + checksum + ".partial")


def candidates(entry, cache, reuse_dirs):
    from huggingface_hub import try_to_load_from_cache
    yield cache_path(cache, entry)
    name = Path(entry["filename"])
    for directory in reuse_dirs:
        root = Path(directory).expanduser().resolve()
        yield root / name
        yield root / entry["repo"].replace("/", "--") / name
        if name.parts[0] == "FL2VA":
            yield root / Path(*name.parts[1:])
    path = try_to_load_from_cache(entry["repo"], entry["filename"], revision=entry["revision"])
    if isinstance(path, str):
        yield Path(path)


def plan(directory=None, cache_dir=None, reuse_dirs=(), progress=None):
    directory = model_directory(directory)
    if (directory / "bundle.json").exists():
        assets = load_assets(directory)
        return {"status": "ready", "directory": str(directory), "identity": assets["identity"],
                "download_bytes": 0, "additional_disk_bytes": 0}
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"Model destination is not empty: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    cache = Path(cache_dir).expanduser().resolve() if cache_dir else directory.parent / ".h3-apple-sources"
    cache.mkdir(parents=True, exist_ok=True)
    manifest = source_manifest()
    by_hash = defaultdict(list)
    for entry in manifest["sources"]:
        by_hash[entry["sha256"]].append(entry)
    groups = []
    downloaded = copied = 0
    for checksum, entries in by_hash.items():
        expected = entries[0]["bytes"]
        if any(x["bytes"] != expected for x in entries):
            raise ValueError("Source manifest has inconsistent content sizes.")
        source = None
        checked = set()
        for entry in entries:
            for candidate in candidates(entry, cache, reuse_dirs):
                if not candidate.is_file():
                    continue
                candidate = candidate.resolve()
                if candidate in checked:
                    continue
                checked.add(candidate)
                is_cached = candidate == cache_path(cache, entry).resolve()
                if candidate.stat().st_size != expected:
                    if is_cached:
                        raise ValueError(f"Cached model size changed: {candidate}")
                    continue
                if progress:
                    progress({"phase": "checking_local_models", "file": str(candidate)})
                before = candidate.stat()
                checksum_actual = digest(candidate)
                after = candidate.stat()
                if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                    raise ValueError(f"Local model changed during verification: {candidate}")
                if checksum_actual == checksum:
                    source = str(candidate)
                    break
                if is_cached:
                    raise ValueError(f"Cached model SHA256 changed: {candidate}")
            if source:
                break
        destination = cache_path(cache, entries[0])
        part = partial_path(destination, checksum)
        resumable = part.stat().st_size if part.is_file() else 0
        if resumable > expected:
            raise ValueError(f"Oversized partial download; preserve/move it before retrying: {part}")
        if source is None:
            downloaded += expected - resumable
        elif Path(source).stat().st_dev != cache.stat().st_dev:
            copied += expected
        groups.append(dict(sha256=checksum, bytes=expected, source=source, files=entries,
                           source_mtime_ns=Path(source).stat().st_mtime_ns if source else None,
                           partial_bytes=resumable if source is None else 0))
    # Converted DiT/decoder plus headroom for metadata and serialization. Raw sources stay reusable.
    converted_peak = sum(manifest["converted_sizes"].values()) + 1024**3
    separate_filesystems = directory.parent.stat().st_dev != cache.stat().st_dev
    bundle_copy = 0
    if separate_filesystems:
        bundle_copy = sum(g["bytes"] for g in groups if any(
            x["filename"].startswith(("FL2VA/text_encoder/", "FL2VA/tokenizer/"))
            or x["filename"] == "FL2VA/audio_vae/model.safetensors" for x in g["files"]))
    destination_required = converted_peak + bundle_copy + RESERVE
    cache_required = downloaded + copied + RESERVE
    if not separate_filesystems:
        destination_required += downloaded + copied
        cache_required = destination_required
    return dict(status="preparation_required", directory=str(directory), cache_dir=str(cache),
                download_bytes=downloaded, cross_volume_copy_bytes=copied + bundle_copy,
                additional_disk_bytes=destination_required,
                destination_free_bytes=shutil.disk_usage(directory.parent).free,
                cache_additional_disk_bytes=cache_required, cache_free_bytes=shutil.disk_usage(cache).free,
                unique_source_bytes=sum(g["bytes"] for g in groups),
                estimated_retained_sources_and_converted_bytes=sum(g["bytes"] for g in groups) + converted_peak,
                large_download_requires_confirmation=downloaded > LIMIT,
                source_manifest=manifest, groups=groups)


def download(url, destination, expected_size, checksum):
    """Resume an immutable HTTPS source, verify it, then atomically publish the file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = partial_path(destination, checksum)
    offset = part.stat().st_size if part.exists() else 0
    if offset > expected_size:
        raise ValueError(f"Oversized partial download: {part}")
    if offset < expected_size:
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        with urlopen(Request(url, headers=headers), timeout=60) as response:
            if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                raise ValueError(f"Server did not honor download resume. Move {part} aside and review a new full-download plan.")
            with part.open("ab" if part.exists() else "xb") as stream:
                count = offset
                while chunk := response.read(min(4 * 1024**2, expected_size - count + 1)):
                    if count + len(chunk) > expected_size:
                        raise ValueError("Download exceeds the pinned source size.")
                    stream.write(chunk)
                    count += len(chunk)
                stream.flush()
                os.fsync(stream.fileno())
    if part.stat().st_size != expected_size or digest(part) != checksum:
        raise ValueError(f"Incomplete or corrupt download; retained at {part}")
    if destination.exists():
        if digest(destination) != checksum:
            raise FileExistsError(f"Different cached model already exists: {destination}")
        part.unlink()
    else:
        os.link(part, destination)
        part.unlink()
    return destination


def materialize(spec, progress):
    cache = Path(spec["cache_dir"])
    for group in spec["groups"]:
        source = Path(group["source"]) if group["source"] else None
        if source is not None and (source.stat().st_size != group["bytes"]
                or source.stat().st_mtime_ns != group["source_mtime_ns"]):
            raise ValueError(f"Reusable source changed after planning: {source}")
        if source is None:
            entry = group["files"][0]
            url = f"https://huggingface.co/{entry['repo']}/resolve/{entry['revision']}/{quote(entry['filename'], safe='/')}"
            progress({"phase": "downloading_models", "file": entry["filename"]})
            source = download(url, cache_path(cache, entry), group["bytes"], group["sha256"])
        for entry in group["files"]:
            destination = cache_path(cache, entry)
            destination.parent.mkdir(parents=True, exist_ok=True)
            if destination.exists():
                if destination.resolve() != source.resolve() and digest(destination) != group["sha256"]:
                    raise ValueError(f"Different cached source: {destination}")
                source = destination
                continue
            if source.stat().st_dev == destination.parent.stat().st_dev:
                os.link(source, destination)
            else:
                shutil.copy2(source, destination)
                if digest(destination) != group["sha256"]:
                    raise ValueError(f"Copied model failed verification: {destination}")
            # Aliases share the first cache copy, including when reuse crosses volumes.
            source = destination
    return cache


def prepare(directory=None, cache_dir=None, reuse_dirs=(), *, allow_large_download=False, progress=None):
    progress = progress or (lambda event: None)
    directory = model_directory(directory)
    if (directory / "bundle.json").exists():
        return load_assets(directory)
    check_machine(snapshot())
    cache = Path(cache_dir).expanduser().resolve() if cache_dir else directory.parent / ".h3-apple-sources"
    cache.mkdir(parents=True, exist_ok=True)
    with device_lock(cache / "preparation.lock"):
        spec = plan(directory, cache, reuse_dirs, progress)
        if spec["status"] == "ready":
            return load_assets(directory)
        progress({"phase": "model_plan", "download_bytes": spec["download_bytes"],
                  "additional_disk_bytes": spec["additional_disk_bytes"],
                  "cache_additional_disk_bytes": spec["cache_additional_disk_bytes"]})
        if spec["download_bytes"] > LIMIT and not allow_large_download:
            raise ValueError(f"Preparation needs {spec['download_bytes'] / 1024**3:.2f} GiB of downloads. "
                "Review `h3 models prepare --plan` and rerun with --allow-large-download to confirm downloads over 20 GB.")
        if (spec["destination_free_bytes"] < spec["additional_disk_bytes"]
                or spec["cache_free_bytes"] < spec["cache_additional_disk_bytes"]):
            raise OSError("Insufficient free disk for the source cache and conversion peak; see --plan.")
        cache = materialize(spec, progress)
        native_entry = next(x for x in spec["source_manifest"]["sources"] if x["filename"] == "FL2VA/transformer/config.json")
        native = cache_path(cache, native_entry).parent.parent
        adapter_entry = next(x for x in spec["source_manifest"]["sources"] if x["filename"] == "vsa-datafree/adapter_model.safetensors")
        work = Path(tempfile.mkdtemp(prefix=f".{directory.name}-conversion-", dir=directory.parent))
        write_json(work / "plan.json", spec)
        command = [sys.executable, "-m", "h3_apple.conversion", "--native", str(native),
                   "--adapter", str(cache_path(cache, adapter_entry)), "--output", str(work / "output")]
        environment = dict(os.environ, MLX_ENABLE_TF32="0", FASTVIDEO_MLX_DQ_GEMM="1",
                           HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1")
        progress({"phase": "converting_models", "file": str(work / "conversion.log")})
        initial = snapshot()
        started = time.monotonic()
        with (work / "conversion.log").open("w") as log:
            child = subprocess.Popen(command, env=environment, stdin=subprocess.DEVNULL,
                                     stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
            try:
                while child.poll() is None:
                    if time.monotonic() - started > 1800:
                        raise TimeoutError(f"Model conversion exceeded 1800 seconds; see {work}")
                    current = snapshot()
                    if current["swap_bytes"] - initial["swap_bytes"] > 2 * 1024**3:
                        raise RuntimeError("Model conversion stopped: swap grew more than 2 GiB.")
                    if current["thermal"]["state"] in ("serious", "critical"):
                        raise RuntimeError("Model conversion stopped: serious thermal pressure.")
                    if shutil.disk_usage(work).free < RESERVE:
                        raise OSError("Model conversion stopped: less than 2 GiB free disk remains.")
                    try:
                        child.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        pass
                code = child.returncode
                if code:
                    raise RuntimeError(f"Model conversion exited {code}; see {work / 'conversion.log'}")
            except BaseException:
                from .process import _stop
                _stop(child)
                raise
        receipt = json.loads((work / "output/conversion.json").read_text())
        result = import_assets(work / "output/dit", work / "output/components", directory,
                               progress=progress, download_bytes=spec["download_bytes"],
                               provenance={"recipe": spec["source_manifest"]["recipe"],
                                   "sources": spec["source_manifest"]["sources"], "conversion": receipt,
                                   "source_copy_bytes": spec["cross_volume_copy_bytes"]})
        # Completed converted files now have their own links in the committed bundle.
        shutil.rmtree(work / "output")
        write_json(work / "result.json", {"directory": result["directory"], "identity": result["identity"],
                   "conversion": receipt, "source_cache": str(cache)})
        return result
