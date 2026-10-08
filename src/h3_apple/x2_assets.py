"""Pinned optional X2 weights and notices; never downloaded at import or resolve."""

import errno
import json
import os
from pathlib import Path
import shutil

from .downloads import download, partial_path
from .host import device_lock
from .io import digest


def manifest():
    return json.loads((Path(__file__).parent / "data/x2-model-sources.json").read_text())


def directory(model_dir=None):
    return Path(model_dir or Path.home() / "Models/h3-apple/x2").expanduser().resolve()


def verified(path, item):
    return path.is_file() and path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]


def plan(model_dir=None, reuse_dirs=()):
    root = directory(model_dir)
    files = []
    download_bytes = additional_disk_bytes = 0
    for item in manifest()["files"]:
        target = root / item["path"]
        source = None
        if os.path.lexists(target):
            if not verified(target, item):
                raise ValueError(f"X2 model checksum mismatch: {target}. Move it aside before preparing again.")
            source = target
        else:
            for reuse in reuse_dirs:
                candidate = Path(reuse).expanduser().resolve() / item["path"]
                if verified(candidate, item):
                    source = candidate
                    break
        partial = partial_path(target, item["sha256"])
        offset = partial.stat().st_size if partial.is_file() else 0
        if offset > item["bytes"]:
            raise ValueError(f"Oversized partial X2 download: {partial}")
        if source is None:
            download_bytes += item["bytes"] - offset
        if source != target:
            # Conservatively allow a full copy when reusing across filesystems.
            additional_disk_bytes += item["bytes"] - (offset if source is None else 0)
        files.append(dict(item, reuse=str(source) if source else None))
    return dict(directory=str(root), recipe=manifest()["recipe"], files=files,
                download_bytes=download_bytes,
                additional_disk_bytes=additional_disk_bytes + (2 * 1024**3 if additional_disk_bytes else 0))


def prepare(model_dir=None, reuse_dirs=(), *, on_progress=None):
    with device_lock():
        spec = plan(model_dir, reuse_dirs)
        # The fixed optional package is below 20 GB; generate checks its combined
        # download with the selected generation models before preparing either package.
        if spec["download_bytes"] > 20_000_000_000:
            raise ValueError("Unexpected X2 download above 20 GB; inspect the package manifest.")
        root = Path(spec["directory"])
        root.mkdir(parents=True, exist_ok=True)
        if shutil.disk_usage(root).free < spec["additional_disk_bytes"]:
            raise OSError("Insufficient free disk for X2 preparation; see h3 prepare-x2 --plan.")
        for item in spec["files"]:
            target = root / item["path"]
            source = Path(item["reuse"]) if item["reuse"] else None
            if source == target:
                continue
            if on_progress:
                on_progress(dict(phase="x2_models", message="Reusing" if source else "Downloading",
                                 file=item["path"]))
            if source is None:
                download(item["url"], target, item["bytes"], item["sha256"])
            else:
                try:
                    os.link(source, target)
                except OSError as error:
                    if error.errno != errno.EXDEV:
                        raise
                    with source.open("rb") as inp, target.open("xb") as out:
                        shutil.copyfileobj(inp, out)
                if not verified(target, item):
                    raise ValueError(f"X2 reuse source changed during preparation: {target}")
        checkpoint = next(item for item in spec["files"] if item["path"].endswith(".safetensors"))
        return dict(status="ready", checkpoint=str(root / checkpoint["path"]),
                    sha256=checkpoint["sha256"], bytes=checkpoint["bytes"],
                    recipe=spec["recipe"], revision=manifest()["revision"],
                    download_bytes=spec["download_bytes"])
