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


@pytest.mark.parametrize("change", ["file", "derivation"])
def test_manifest_content_identity_rejected(tmp_path, sources, change):
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    path = destination / "bundle.json"
    manifest = json.loads(path.read_text())
    if change == "file":
        manifest["files"][0]["sha256"] = "0" * 64
    else:
        manifest["derivation"]["converter"] = "changed converter"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="identity"):
        load_assets(destination)


def test_existing_v1_bundle_remains_readable(tmp_path, sources):
    from h3_apple.assets import bundle_identity
    destination = tmp_path / "models"
    import_assets(*sources, destination)
    path = destination / "bundle.json"
    manifest = json.loads(path.read_text())
    manifest["format_version"] = 1
    manifest.pop("derivation")
    manifest["identity"] = bundle_identity(manifest)
    path.write_text(json.dumps(manifest))
    assert load_assets(destination, verify=True)["identity"] == manifest["identity"]


def test_failed_import_does_not_publish_partial_bundle(tmp_path, sources, monkeypatch):
    import h3_apple.assets as assets
    original = assets.digest
    count = 0
    def fail_during_hash(path):
        nonlocal count
        count += 1
        if count == 2:
            raise OSError("simulated interrupted import")
        return original(path)
    monkeypatch.setattr(assets, "digest", fail_during_hash)
    destination = tmp_path / "models"
    with pytest.raises(OSError, match="interrupted"):
        import_assets(*sources, destination)
    assert not destination.exists()
    assert list(tmp_path.glob(".models-prepare-*"))


@pytest.fixture
def reference_sources(tmp_path, sources):
    checkpoint, components = sources
    (checkpoint / "ref2va_recipe.json").write_text(json.dumps(dict(
        schema="h3-apple-ref2va/v1", task="ref2va", lora_rank=128, lora_alpha=8,
        lora_tensors=624, gate_tensors=50, precision="int8_group64_bf16",
        fasth3_t2va_deltas_applied=False)))
    native = tmp_path / "source/native"
    for relative in ["processor/preprocessor_config.json", "tokenizer/tokenizer.json",
                     "text_encoder/config.json", "text_encoder/model.safetensors",
                     "video_vae/config.json", "video_vae/source/config.json",
                     "video_vae/source/model.safetensors"]:
        path = native / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b"{}")
    return checkpoint, components, native


def test_reference_bundle_owns_encoders_and_recipe(tmp_path, reference_sources):
    checkpoint, components, native = reference_sources
    destination = tmp_path / "bundle"
    imported = import_assets(checkpoint, components, destination, ref2va_native=native)
    shutil.rmtree(tmp_path / "source")
    loaded = load_assets(destination, verify=True)
    assert loaded["task"] == "ref2va" and loaded["format_version"] == 3
    assert loaded["identity"] == imported["identity"]
    assert Path(loaded["ref2va_native"], "text_encoder/model.safetensors").is_file()
    assert Path(loaded["checkpoint"], "ref2va_recipe.json").is_file()
    assert all(item["method"] == "hardlink" for item in loaded["files"])


def test_reference_checkpoint_cannot_be_imported_as_text(tmp_path, reference_sources):
    checkpoint, components, native = reference_sources
    with pytest.raises(ValueError, match="requires --ref2va-native"):
        import_assets(checkpoint, components, tmp_path / "bundle")


def test_reference_recipe_and_encoder_weights_are_required(tmp_path, reference_sources):
    checkpoint, components, native = reference_sources
    recipe_path = checkpoint / "ref2va_recipe.json"
    recipe = json.loads(recipe_path.read_text())
    recipe["gate_tensors"] = 0
    recipe_path.write_text(json.dumps(recipe))
    with pytest.raises(ValueError, match="four-step checkpoint"):
        import_assets(checkpoint, components, tmp_path / "bundle", ref2va_native=native)
    recipe["gate_tensors"] = 50
    recipe_path.write_text(json.dumps(recipe))
    (native / "text_encoder/model.safetensors").unlink()
    with pytest.raises(ValueError, match="weights"):
        import_assets(checkpoint, components, tmp_path / "bundle", ref2va_native=native)


def test_reference_directory_is_bound_to_bundle_identity(tmp_path, reference_sources):
    checkpoint, components, native = reference_sources
    destination = tmp_path / "bundle"
    import_assets(checkpoint, components, destination, ref2va_native=native)
    path = destination / "bundle.json"
    manifest = json.loads(path.read_text())
    manifest["ref2va_native"] = "components"
    path.write_text(json.dumps(manifest))
    with pytest.raises(ValueError, match="identity"):
        load_assets(destination)
