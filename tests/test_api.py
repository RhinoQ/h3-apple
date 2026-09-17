import json
from pathlib import Path
import subprocess
import sys

import pytest

from h3_apple import resolve


@pytest.mark.parametrize("resolution,duration,expected", [
    ("768p", 15, (1366, 768, 360, 1376, 362)),
    ("576p", 5, (1024, 576, 120, 1024, 124)),
    ("768p", 10, (1366, 768, 240, 1376, 243)),
])
def test_resolved_delivery_and_native_geometry(resolution, duration, expected):
    r = resolve("Free user prompt", resolution=resolution, duration=duration, seed=7)
    assert (r.width, r.height, r.num_frames, r.model_width, r.model_num_frames) == expected
    assert (r.fps, r.audio_channels, r.num_steps) == (24, 2, 4)


@pytest.mark.parametrize("resolution", ["576p", "768p"])
@pytest.mark.parametrize("duration", [5, 10.125, 15])
def test_portrait_transposes_both_canvases_and_preserves_recipe(resolution, duration):
    landscape = resolve("A portrait.", resolution=resolution, duration=duration, seed=7).to_dict()
    explicit = resolve("A portrait.", resolution=resolution, duration=duration, seed=7, aspect_ratio="16:9")
    assert explicit.to_dict() == landscape
    portrait = resolve("A portrait.", resolution=resolution, duration=duration, seed=7, aspect_ratio="9:16")
    expected = dict(landscape, width=landscape["height"], height=landscape["width"],
                    model_width=landscape["model_height"], model_height=landscape["model_width"])
    assert portrait.to_dict() == expected


@pytest.mark.parametrize("value", ["1:1", "16:10", "portrait", "", None, True, 9/16, []])
def test_invalid_aspect_ratio_fails_before_opening_references(value):
    with pytest.raises(ValueError, match="aspect_ratio"):
        resolve("Portrait.", aspect_ratio=value, reference_images=["missing.png"])


def test_generate_forwards_portrait_geometry_to_worker(monkeypatch, tmp_path):
    from h3_apple import generate
    from h3_apple import process
    seen = []
    def capture(request, **kwargs):
        seen.append((request, kwargs))
        return "sentinel"
    monkeypatch.setattr(process, "run_generation", capture)
    assert generate("Portrait.", aspect_ratio="9:16", duration=5, seed=2, output=tmp_path/"portrait.mp4") == "sentinel"
    assert (seen[0][0].width, seen[0][0].height, seen[0][0].model_width, seen[0][0].model_height) == (768,1366,768,1376)


def test_portrait_resolution_does_not_load_mlx(tmp_path):
    subprocess.run([sys.executable, "-c",
        "import h3_apple,sys; r=h3_apple.resolve('portrait',aspect_ratio='9:16'); "
        "assert (r.width,r.height)==(768,1366); assert 'mlx.core' not in sys.modules"],
        cwd=tmp_path, check=True)


def test_prompt_file_is_preserved(tmp_path):
    prompt = 'A café at dawn. She says, "Good morning."\nA bicycle passes.\n'
    path = tmp_path / "prompt.txt"
    path.write_text(prompt)
    assert resolve(prompt_file=path).prompt == prompt
    with pytest.raises(ValueError, match="exactly one"):
        resolve(prompt, prompt_file=path)


@pytest.mark.parametrize("kwargs", [
    {"duration": 0}, {"duration": 16}, {"duration": float("nan")},
    {"duration": float("inf")}, {"duration": "abc"}, {"duration": True},
    {"duration": 5.01}, {"seed": -1}, {"seed": 2**32}, {"seed": True},
    {"seed": 1.5}, {"resolution": "1080p"}, {"preset": "vpipe"},
])
def test_invalid_request_rejected_before_runtime(kwargs):
    with pytest.raises(ValueError):
        resolve("User text", **kwargs)


@pytest.mark.parametrize("prompt", [None, "", "  \n", "bad\x00text"])
def test_empty_and_invalid_prompt(prompt):
    with pytest.raises(ValueError):
        resolve(prompt)


def test_installed_api_does_not_import_mlx(tmp_path):
    result = subprocess.run([sys.executable, "-c",
                             "import h3_apple,sys; h3_apple.resolve('free text'); "
                             "assert 'mlx.core' not in sys.modules; print(h3_apple.__file__)"],
                            cwd=tmp_path, text=True, capture_output=True, check=True)
    assert "site-packages" in result.stdout


def test_cli_installed_outside_checkout(tmp_path):
    result = subprocess.run([sys.executable, "-m", "h3_apple", "resolve", "--prompt", "A boat.",
                             "--duration", "5", "--seed", "123"], cwd=tmp_path,
                            text=True, capture_output=True, check=True)
    assert json.loads(result.stdout)["seed"] == 123


def test_ordered_references_and_task_defaults(tmp_path):
    from PIL import Image
    paths = [tmp_path / "second.png", tmp_path / "first.png"]
    for path in paths:
        Image.new("RGB", (32, 48)).save(path)
    request = resolve("Use picture 1 then picture 2.\n", reference_images=paths)
    assert request.reference_images == tuple(map(str, paths))
    assert (request.task, request.resolution, request.preset_version) == ("ref2va", "576p", "ours-ref2va-v1")
    assert request.prompt == "Use picture 1 then picture 2.\n"
    assert resolve("Text").resolution == "768p"
    assert resolve("Text", reference_images=paths, resolution="768p").resolution == "768p"


@pytest.mark.parametrize("references", [[], ["x"] * 10, "x.png", [None], [""]])
def test_invalid_reference_lists_rejected(references):
    with pytest.raises(ValueError, match="reference|Reference"):
        resolve("Text", reference_images=references)


def test_animation_is_not_a_still_reference(tmp_path):
    from PIL import Image
    path = tmp_path / "animated.gif"
    Image.new("RGB", (32, 32), "red").save(path, save_all=True,
        append_images=[Image.new("RGB", (32, 32), "blue")], duration=100)
    with pytest.raises(ValueError, match="still images"):
        resolve("Text", reference_images=[path])
