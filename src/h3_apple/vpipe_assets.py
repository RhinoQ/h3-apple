"""Register separately installed native vpipe assets without copying weights."""

import hashlib
import json
import os
from pathlib import Path

from .fl2va_recipe import FL12_SOURCE
from .ref2va_recipe import DARETIES_SOURCE
from .io import digest

SCHEMA = "h3-apple-vpipe/v1"
INTERFACE_COMMIT = "f34e2cc3a3adae759eea254419f436f5b7800057"


def sampling_recipe(partition):
    return dict(steps=4, graph_steps=5, video_shift=12.0 if partition == "ref2va" else 6.0,
                audio_shift=3.0, lora_scale=1.0)


def identity(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def file_record(path):
    path = Path(path).expanduser().resolve(strict=True)
    stat = path.stat()
    return dict(path=str(path), bytes=stat.st_size, mtime_ns=stat.st_mtime_ns, sha256=digest(path))


def model_partition(root):
    config = json.loads((root / "transformer/config.json").read_text())
    if (config.get("_class_name") != "MiniMaxH3DiTModel" or config.get("num_layers") != 50
            or config.get("quantization") != dict(bits=8, group_size=64)):
        raise ValueError("vpipe presets require an unmerged native H3 8-bit, group-64 transformer.")
    meta = json.loads((root / "model_index.json").read_text()).get("_minimax_h3", {})
    partition = meta.get("partition")
    if partition not in ("fl2va", "ref2va"):
        raise ValueError("Native model_index.json must declare the FL2VA or Ref2VA partition.")
    for name in ("transformer", "text_encoder", "tokenizer", "video_vae", "audio_vae"):
        if not (root / name / "config.json").is_file() and name != "tokenizer":
            raise ValueError(f"Incomplete native model component: {name}")
        if not (root / name).is_dir():
            raise ValueError(f"Missing native model component: {name}")
    for name in ("transformer", "text_encoder", "video_vae", "audio_vae"):
        if not list((root / name).glob("*.safetensors")):
            raise ValueError(f"Missing native weights: {name}")
    return partition


def import_vpipe_assets(*, model_dir, native_model, lora, vpipe_binary, vpipe_library, progress=None):
    """Hash local inputs once; subsequent runs recheck file sizes and timestamps."""
    destination = Path(model_dir).expanduser().resolve()
    if destination.exists():
        raise FileExistsError(f"Choose a new bundle directory: {destination}")
    root = Path(native_model).expanduser().resolve(strict=True)
    partition = model_partition(root)
    binary = Path(vpipe_binary).expanduser().resolve(strict=True)
    library = Path(vpipe_library).expanduser().resolve(strict=True)
    if not os.access(binary, os.X_OK):
        raise ValueError("vpipe_binary must be executable.")
    if (library.parent / "libvpipe.0.dylib").resolve() != library:
        raise ValueError("vpipe_library must match its adjacent libvpipe.0.dylib loader link.")
    adapter = file_record(lora)
    source = DARETIES_SOURCE if partition == "ref2va" else FL12_SOURCE
    if adapter["sha256"] != source["sha256"]:
        raise ValueError(f"Native {partition.upper()} requires the pinned adapter: {source['filename']}")
    files = []
    for path in sorted(root.rglob("*")):
        if path.is_file():
            if progress: progress(dict(phase="preparing", file=str(path.relative_to(root))))
            files.append(file_record(path))
    manifest = dict(schema=SCHEMA, native_model=str(root), partition=partition,
        tasks=["ref2va"] if partition == "ref2va" else ["t2va", "fl2va"],
        adapter=adapter, adapter_source=source, binary=file_record(binary), library=file_record(library),
        files=files, tested_interface_commit=INTERFACE_COMMIT,
        recipe=sampling_recipe(partition))
    manifest["identity"] = identity(manifest)
    destination.mkdir(parents=True, exist_ok=False)
    with (destination / "vpipe.json").open("x") as stream:
        json.dump(manifest, stream, indent=2); stream.write("\n")
    return dict(manifest, directory=str(destination))


def load_vpipe_assets(model_dir, *, verify=False):
    if model_dir is None:
        raise ValueError("The vpipe presets require --model-dir pointing to a bundle from h3 models import-vpipe.")
    directory = Path(model_dir).expanduser().resolve()
    path = directory / "vpipe.json"
    if not path.is_file():
        raise ValueError("Expected a native vpipe bundle; register it with h3 models import-vpipe.")
    data = json.loads(path.read_text())
    if (not isinstance(data, dict) or data.get("schema") != SCHEMA
            or data.get("identity") != identity({k:v for k,v in data.items() if k!="identity"})):
        raise ValueError("Native bundle manifest changed or is unsupported; register a new bundle.")
    partition = data.get("partition")
    source = DARETIES_SOURCE if partition == "ref2va" else FL12_SOURCE
    tasks = ["ref2va"] if partition == "ref2va" else ["t2va", "fl2va"]
    if (partition not in ("fl2va", "ref2va") or data.get("recipe") != sampling_recipe(partition)
            or data.get("tasks") != tasks or data.get("adapter", {}).get("sha256") != source["sha256"]):
        raise ValueError("The native bundle does not use the pinned task and four-step adapter recipe.")
    for entry in [*data["files"], data["adapter"], data["binary"], data["library"]]:
        file = Path(entry["path"]); stat = file.stat()
        if (stat.st_size, stat.st_mtime_ns) != (entry["bytes"], entry["mtime_ns"]):
            raise ValueError(f"Native asset changed; register a new bundle: {file}")
        if (verify or entry is data["binary"] or entry is data["library"]) and digest(file) != entry["sha256"]:
            raise ValueError(f"Native asset checksum differs: {file}")
    if model_partition(Path(data["native_model"])) != data["partition"]:
        raise ValueError("Native model partition changed.")
    return dict(data, directory=str(directory))
