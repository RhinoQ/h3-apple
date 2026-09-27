"""Optional restoration assets, separate from generation and never fetched at import."""

import json
import os
from pathlib import Path
import shutil

from ..downloads import download
from ..io import digest


def manifest():
    return json.loads((Path(__file__).parents[1] / "data/face-model-sources.json").read_text())


def directory(model_dir=None):
    return Path(model_dir or Path.home() / "Models/h3-apple/faces").expanduser().resolve()


def verified(path, item):
    return path.is_file() and path.stat().st_size == item["bytes"] and digest(path) == item["sha256"]


def plan(model_dir=None, reuse_dirs=()):
    root = directory(model_dir)
    roots = [Path(p).expanduser().resolve() for p in reuse_dirs]
    files = []
    for item in manifest()["files"]:
        target = root / item["path"]
        source = None
        if target.exists() or target.is_symlink():
            if not verified(target, item):
                raise ValueError(f"Face model checksum mismatch: {target}. Move it aside before preparing again.")
            source = target
        else:
            for reuse in roots:
                candidate = reuse / item["path"]
                if verified(candidate, item):
                    source = candidate
                    break
        files.append(dict(item, reuse=str(source) if source else None))
    return dict(directory=str(root), recipe=manifest()["recipe"], files=files,
                download_bytes=sum(f["bytes"] for f in files if not f["reuse"]),
                total_model_bytes=sum(f["bytes"] for f in files))


def prepare(model_dir=None, reuse_dirs=(), *, on_progress=None):
    spec = plan(model_dir, reuse_dirs)
    # This fixed optional package is 7.08 GB; the main H3 download policy is separate.
    if spec["download_bytes"] > 20 * 10**9:
        raise ValueError("Unexpected face asset download above 20 GB; inspect the package manifest.")
    root = Path(spec["directory"])
    root.mkdir(parents=True, exist_ok=True)
    if shutil.disk_usage(root).free < spec["total_model_bytes"] + 2 * 1024**3:
        raise OSError("Face model preparation needs space for the 7.08 GB package plus 2 GiB reserve.")
    for item in spec["files"]:
        target = root / item["path"]
        if on_progress:
            on_progress(dict(phase="face_models", message="Reusing" if item["reuse"] else "Downloading", file=item["path"]))
        if item["reuse"]:
            source = Path(item["reuse"])
            if source == target:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            try:
                os.link(source, target)
            except OSError as error:
                import errno
                if error.errno != errno.EXDEV:
                    raise
                with source.open("rb") as inp, target.open("xb") as out:
                    shutil.copyfileobj(inp, out)
        else:
            download(item["url"], target, item["bytes"], item["sha256"])
    return dict(status="ready", directory=str(root), recipe=spec["recipe"], download_bytes=spec["download_bytes"])


def verify(model_dir=None):
    root = directory(model_dir)
    for item in manifest()["files"]:
        if not verified(root / item["path"], item):
            raise ValueError(f"Missing or corrupt face model: {root / item['path']}. Run h3 prepare-faces --model-dir {root}")
    return root
