"""Immutable local model bundles, with explicit content identity and reuse."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .io import digest, write_json


def model_directory(value=None):
    return Path(value or os.environ.get("H3_MODEL_DIR", Path.home() / "Models/h3-apple")).expanduser().resolve()


def _files(checkpoint, components):
    checkpoint, components = Path(checkpoint).resolve(), Path(components).resolve()
    manifest = checkpoint / "mlx_h3_dit.json"
    config = json.loads(manifest.read_text())
    if (not config.get("vsa", {}).get("capable") or config.get("num_blocks") != 50
            or config.get("quantization") != {"mode": "affine", "bits": 8, "group_size": 64}):
        raise ValueError("Ours requires the 50-block affine INT8/group64 FastH3 VSA checkpoint.")
    paths = {"dit/mlx_h3_dit.json": manifest,
             "dit/mlx_h3_dit.safetensors": checkpoint / "mlx_h3_dit.safetensors"}
    for name in ("text_encoder", "tokenizer", "vae", "audio_vae"):
        source = (components / name).resolve()
        if not source.is_dir():
            raise FileNotFoundError(f"Missing component directory: {source}")
        for path in sorted(source.rglob("*")):
            if path.is_file() and path.suffix in (".json", ".safetensors", ".txt", ".jinja"):
                paths[f"components/{name}/{path.relative_to(source)}"] = path.resolve()
    required = ["components/tokenizer/tokenizer.json", "components/text_encoder/config.json",
                "components/vae/config.json", "components/audio_vae/config.json"]
    if any(name not in paths for name in required):
        raise ValueError("Model bundle is missing required tokenizer or component configuration.")
    for name in ("text_encoder", "vae", "audio_vae"):
        if not any(p.startswith(f"components/{name}/") and p.endswith(".safetensors") for p in paths):
            raise ValueError(f"Missing {name} weights.")
    for path in paths.values():
        if not path.is_file():
            raise FileNotFoundError(path)
    return paths


def import_assets(checkpoint, components, directory=None, *, progress=None):
    directory = model_directory(directory)
    if (directory / "bundle.json").exists():
        raise FileExistsError(f"A model bundle already exists at {directory}; use another directory.")
    paths = _files(checkpoint, components)
    directory.mkdir(parents=True, exist_ok=True)
    if any((directory / name).exists() for name in ("dit", "components")):
        raise FileExistsError("Model destination contains an incomplete or existing bundle.")
    for source in paths.values():
        if directory == source or directory in source.parents:
            raise ValueError("Model destination must not contain the source assets.")
    copy_bytes = sum(p.stat().st_size for p in paths.values()
                     if p.stat().st_dev != directory.stat().st_dev)
    if shutil.disk_usage(directory).free < copy_bytes + 2 * 1024**3:
        raise OSError(f"Insufficient disk space for {copy_bytes} bytes of model copies.")
    staging = Path(tempfile.mkdtemp(prefix=".prepare-", dir=directory))
    entries = []
    try:
        for relative, source in paths.items():
            if progress is not None:
                progress({"phase": "model_import", "file": relative})
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            before = source.stat()
            checksum = digest(source)
            after = source.stat()
            if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
                raise ValueError(f"Source asset changed while hashing: {source}")
            if source.stat().st_dev == staging.stat().st_dev:
                os.link(source, destination)
                method = "hardlink"
            else:
                shutil.copy2(source, destination)
                if digest(destination) != checksum:
                    raise ValueError(f"Model copy failed verification: {relative}")
                method = "copy"
            stat = destination.stat()
            entries.append(dict(path=relative, sha256=checksum, size=stat.st_size,
                                mtime_ns=stat.st_mtime_ns, method=method))
        identity = hashlib.sha256(json.dumps([{k: e[k] for k in ("path", "sha256", "size")}
                                              for e in entries], sort_keys=True).encode()).hexdigest()
        manifest = dict(format_version=1, preset="ours", identity=identity, files=entries,
                        checkpoint="dit", components="components",
                        download_bytes=0, copied_bytes=copy_bytes)
        for name in ("dit", "components"):
            (staging / name).rename(directory / name)
        write_json(directory / "bundle.json", manifest)
    except BaseException:
        # Preserve partial assets and their paths for diagnosis; never overwrite them on retry.
        raise
    else:
        staging.rmdir()
    return load_assets(directory)


def load_assets(directory=None, *, verify=False):
    directory = model_directory(directory)
    path = directory / "bundle.json"
    if not path.is_file():
        raise FileNotFoundError(f"Models are not prepared at {directory}. Run h3 models prepare.")
    data = json.loads(path.read_text())
    if data.get("format_version") != 1 or data.get("preset") != "ours" or not data.get("files"):
        raise ValueError("Unsupported or empty model bundle.")
    for name in ("checkpoint", "components"):
        target = directory / data[name]
        if not target.resolve().is_relative_to(directory) or not target.is_dir():
            raise ValueError(f"Invalid {name} directory in the model bundle.")
    identity = hashlib.sha256(json.dumps([{k: e[k] for k in ("path", "sha256", "size")}
                                          for e in data["files"]], sort_keys=True).encode()).hexdigest()
    if identity != data.get("identity"):
        raise ValueError("Model bundle identity does not match its file manifest.")
    for entry in data["files"]:
        target = directory / entry["path"]
        if not target.resolve().is_relative_to(directory):
            raise ValueError("Model manifest contains a path outside its bundle.")
        stat = target.stat()
        if (stat.st_size, stat.st_mtime_ns) != (entry["size"], entry["mtime_ns"]):
            raise ValueError(f"Model asset changed: {target}; verify or prepare the bundle again.")
        if verify and digest(target) != entry["sha256"]:
            raise ValueError(f"Model SHA256 mismatch: {target}")
    return dict(data, directory=str(directory), checkpoint=str(directory / data["checkpoint"]),
                components=str(directory / data["components"]))
