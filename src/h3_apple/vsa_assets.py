"""Verified original LightX2V model bundles for the VSA runtime."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import tempfile

from .assets import data_file
from .io import digest, write_json


def model_directory(value=None):
    return Path(value or os.environ.get("H3_VSA_MODEL_DIR") or
                Path.home() / "Models/h3-apple/VSA").expanduser().resolve()


def bundle_identity(manifest):
    content = {"files": [{k: e[k] for k in ("path", "sha256", "size")}
                         for e in manifest["files"]],
               **{key: manifest[key] for key in
                  ("derivation", "task", "checkpoint", "components", "ref2va_native")}}
    return hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest()


def load_assets(directory=None, *, verify=False):
    directory = model_directory(directory)
    path = directory / "bundle.json"
    if not path.is_file():
        raise FileNotFoundError(f"VSA models are not prepared at {directory}. Run h3 prepare --mode VSA.")
    data = json.loads(path.read_text())
    expected = dict(format_version=3, preset="ours", task="ref2va", checkpoint="dit",
                    components="components", ref2va_native="ref2va")
    if any(data.get(k) != v for k, v in expected.items()) or not data.get("files"):
        raise ValueError("VSA requires an original LightX2V Ref2VA model bundle.")
    if bundle_identity(data) != data.get("identity"):
        raise ValueError("VSA model identity differs from its manifest.")
    records = {entry["path"]: entry for entry in data["files"]}
    if len(records) != len(data["files"]):
        raise ValueError("Duplicate model manifest paths.")
    for expected in data_file("vsa-prepared-model.json")["files"]:
        actual = records.get(expected["path"], {})
        if any(actual.get(k) != expected[k] for k in ("size", "sha256")):
            raise ValueError(f"VSA original LightX2V model differs: {expected['path']}")
    checked = set()
    for entry in data["files"]:
        target = directory / entry["path"]
        if not target.resolve().is_relative_to(directory):
            raise ValueError("Model manifest contains a path outside its bundle.")
        stat = target.stat()
        if (stat.st_size, stat.st_mtime_ns) != (entry["size"], entry["mtime_ns"]):
            raise ValueError(f"Model asset changed: {target}")
        key = (stat.st_dev, stat.st_ino, entry["sha256"])
        if verify and key not in checked and digest(target) != entry["sha256"]:
            raise ValueError(f"Model SHA256 mismatch: {target}")
        checked.add(key)
    recipe_path = directory / "dit/ref2va_recipe.json"
    if "dit/ref2va_recipe.json" not in records:
        raise ValueError("Missing VSA recipe receipt.")
    recipe = json.loads(recipe_path.read_text())
    expected = dict(schema="h3-apple-ref2va/v1", task="ref2va", lora_rank=128,
                    lora_alpha=8, lora_tensors=624, gate_tensors=50,
                    precision="int8_group64_bf16", fasth3_t2va_deltas_applied=False)
    if any(recipe.get(k) != v for k, v in expected.items()):
        raise ValueError("Expected original LightX2V four-step recipe and 50 VSA gates.")
    return dict(data, directory=str(directory),
                **{name: str(directory / data[name]) for name in
                   ("checkpoint", "components", "ref2va_native")})


def import_assets(checkpoint, components, native, directory, *, progress=None, provenance=None):
    """Publish a new verified bundle; retain the conversion directory on failure."""
    directory = model_directory(directory)
    if directory.exists() and any(directory.iterdir()):
        raise FileExistsError(f"VSA model destination is not empty: {directory}")
    directory.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{directory.name}-prepare-", dir=directory.parent))
    files, hashes = [], {}
    for prefix, root in (("dit", checkpoint), ("components", components), ("ref2va", native)):
        root = Path(root)
        subdirs = [root] if prefix == "dit" else [root / n for n in
            (("text_encoder", "tokenizer", "vae", "audio_vae") if prefix == "components"
             else ("processor", "tokenizer", "text_encoder", "video_vae"))]
        for subdir in subdirs:
            for source in sorted(subdir.rglob("*")):
                if not source.is_file() or source.suffix not in (".json", ".safetensors", ".txt", ".jinja"):
                    continue
                relative = f"{prefix}/{source.relative_to(root)}"
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                source = source.resolve()
                if progress:
                    progress(dict(phase="model_import", file=relative))
                stat = source.stat()
                key = (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
                checksum = hashes.get(key) or digest(source)
                if (source.stat().st_size, source.stat().st_mtime_ns) != (stat.st_size, stat.st_mtime_ns):
                    raise ValueError(f"Source asset changed while hashing: {source}")
                hashes[key] = checksum
                if stat.st_dev == staging.stat().st_dev:
                    os.link(source, destination)
                else:
                    shutil.copy2(source, destination)
                    if digest(destination) != checksum:
                        raise ValueError(f"Model copy failed: {relative}")
                files.append(dict(path=relative, size=stat.st_size, sha256=checksum,
                                  mtime_ns=destination.stat().st_mtime_ns))
    for name in ("LICENSE", "NOTICE"):
        source = Path(components) / name
        if source.is_file():
            shutil.copy2(source, staging / name)
            stat = (staging / name).stat()
            files.append(dict(path=name, size=stat.st_size, sha256=digest(staging / name), mtime_ns=stat.st_mtime_ns))
    manifest = dict(format_version=3, preset="ours", task="ref2va", checkpoint="dit",
                    components="components", ref2va_native="ref2va", files=files,
                    derivation=provenance or {"input": "verified local VSA bundle"})
    manifest["identity"] = bundle_identity(manifest)
    write_json(staging / "bundle.json", manifest)
    load_assets(staging)
    staging.rename(directory)
    return load_assets(directory)
