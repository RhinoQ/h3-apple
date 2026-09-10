import json
import os
from pathlib import Path
import shutil

import pytest

from h3_apple.assets import import_assets, load_assets


@pytest.fixture
def sources(tmp_path):
    checkpoint, components = tmp_path / "source/dit", tmp_path / "source/components"
    checkpoint.mkdir(parents=True)
    (checkpoint / "mlx_h3_dit.json").write_text(json.dumps({
        "num_blocks": 50, "vsa": {"capable": True},
        "quantization": {"mode": "affine", "bits": 8, "group_size": 64},
    }))
    (checkpoint / "mlx_h3_dit.safetensors").write_bytes(b"file-manager fixture, not real model weights")
    for name in ("text_encoder", "tokenizer", "vae", "audio_vae"):
        folder = components / name
        folder.mkdir(parents=True)
        (folder / "config.json").write_text("{}")
        (folder / ("tokenizer.json" if name == "tokenizer" else "model.safetensors")).write_bytes(name.encode())
    return checkpoint, components


def test_import_survives_removal_of_source_names(tmp_path, sources):
    destination = tmp_path / "models"
    imported = import_assets(*sources, destination)
    assert imported["download_bytes"] == 0
    assert imported["copied_bytes"] == 0
    assert all(e["method"] == "hardlink" for e in imported["files"])
    shutil.rmtree(tmp_path / "source")
    assert load_assets(destination, verify=True)["identity"] == imported["identity"]


def test_changed_asset_rejected(tmp_path, sources):
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    (destination / "dit/mlx_h3_dit.safetensors").write_bytes(b"changed")
    with pytest.raises(ValueError, match="asset changed"):
        load_assets(destination)


def test_hash_verify_detects_unchanged_size_and_time(tmp_path, sources):
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    path = destination / "components/tokenizer/tokenizer.json"
    stat = path.stat()
    path.write_bytes(b"x" * stat.st_size)
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns))
    with pytest.raises(ValueError, match="SHA256 mismatch"):
        load_assets(destination, verify=True)


def test_existing_bundle_not_overwritten(tmp_path, sources):
    destination = tmp_path / "models"
    first = import_assets(*sources, destination)
    with pytest.raises(FileExistsError):
        import_assets(*sources, destination)
    assert load_assets(destination)["identity"] == first["identity"]


def test_manifest_directory_escape_rejected(tmp_path, sources):
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    path = destination / "bundle.json"
    manifest = json.loads(path.read_text())
    manifest["checkpoint"] = "../source/dit"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="Invalid checkpoint"):
        load_assets(destination)


def test_manifest_content_identity_rejected(tmp_path, sources):
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    path = destination / "bundle.json"
    manifest = json.loads(path.read_text())
    manifest["files"][0]["sha256"] = "0" * 64
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="identity"):
        load_assets(destination)
