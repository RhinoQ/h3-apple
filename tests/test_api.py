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


def test_prompt_file_is_preserved(tmp_path):
    prompt = '清晨的街道。She says, "Good morning."\nA bicycle passes.\n'
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
