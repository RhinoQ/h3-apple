"""Packed reference semantics against fixed, independently generated upstream data."""
from dataclasses import asdict
import hashlib
import json
from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from h3_apple.runtime.ref2va import (
    ReferenceGeometry, build_ref2va_layout, build_ref2va_timesteps, generated_rows,
    prepare_reference_image, reference_image_size,
)

FIXTURES = Path(__file__).parent / "data"
SPEC = json.loads((FIXTURES / "ref2va_layouts.json").read_text())


@pytest.fixture(scope="module")
def authority():
    path = FIXTURES / "ref2va_layouts.npz"
    assert hashlib.sha256(path.read_bytes()).hexdigest() == SPEC["fixture_sha256"]
    with np.load(path, allow_pickle=False) as archive:
        yield archive


@pytest.mark.parametrize("case", SPEC["cases"], ids=lambda case: case["name"])
def test_layout_and_timesteps_equal_fixed_official_cpu_reference(case, authority):
    layout = build_ref2va_layout(case["text_token_tags"],
        [ReferenceGeometry(**item) for item in case["references"]], *case["target"])
    for field, value in asdict(layout).items():
        if field == "reference_prefix_segments":
            continue  # Local VSA metadata is checked separately against ordered reference boundaries.
        np.testing.assert_array_equal(value, authority[case["name"] + "__" + field])
    assert layout.position_ids.dtype == np.float64
    for index, (video, audio) in enumerate(SPEC["steps"]):
        values, inverse = build_ref2va_timesteps(layout, video, audio)
        np.testing.assert_array_equal(values, authority[f"{case['name']}__step{index}_values"])
        np.testing.assert_array_equal(inverse, authority[f"{case['name']}__step{index}_inverse"])


def test_generated_only_handoff_discards_every_reference_and_rejects_bad_lengths():
    refs = [ReferenceGeometry("image", 1, 4, 6), ReferenceGeometry("audio", has_audio=True, num_audio_latents=3)]
    layout = build_ref2va_layout([1, 0, 1], refs, 2, 4, 6, 5)
    video = np.full((len(layout.video_indices), 96), 2, np.float32)
    audio = np.full((len(layout.audio_indices), 32), 3, np.float32)
    video[:layout.num_condition_video_rows] = -101
    audio[:layout.num_condition_audio_rows] = -202
    v, a = generated_rows(video, audio, layout)
    np.testing.assert_array_equal(v, np.full((12, 96), 2, np.float32))
    np.testing.assert_array_equal(a, np.full((10, 32), 3, np.float32))
    for bad_video, bad_audio in [(video[:-1], audio), (video, audio[:-1]), (v, a), (video[:, :24], audio)]:
        with pytest.raises(ValueError):
            generated_rows(bad_video, bad_audio, layout)


@pytest.mark.parametrize("tags,refs,target", [
    ([1, 2], [ReferenceGeometry("image", 1, 4, 6)], (2, 4, 6, 5)),
    ([[1, 0]], [ReferenceGeometry("image", 1, 4, 6)], (2, 4, 6, 5)),
    ([1, 0], [], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("other", 1, 4, 6)], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("image", 1, 3, 6)], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("image", 2, 4, 6)], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("audio")], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("video", 2, 4, 6, True, 0)], (2, 4, 6, 5)),
    ([1, 0], [ReferenceGeometry("image", 1, 4, 6)], (2, 4, 5, 5)),
    ([1, 0], [ReferenceGeometry("image", 1, 4, 6)], (2, 4, 6, 0)),
])
def test_invalid_geometry_is_rejected(tags, refs, target):
    with pytest.raises(ValueError):
        build_ref2va_layout(tags, refs, *target)


@pytest.mark.parametrize("size,expected", [
    ((2688, 1536), (384, 672)), ((1536, 2688), (672, 384)),
    ((2048, 2048), (512, 512)), ((320, 192), (192, 320)),
])
def test_reference_budget_keeps_each_aspect_and_small_images(size, expected):
    # Fixed expected dimensions from Sol's reference_image_match contract tests.
    assert reference_image_size(*size, 672 * 384) == expected


def test_orientation_precedes_reference_geometry(tmp_path):
    image = Image.new("RGB", (320, 192), "red")
    exif = image.getexif()
    exif[274] = 6
    path = tmp_path / "oriented.png"
    image.save(path, exif=exif)
    with Image.open(path) as original:
        actual = prepare_reference_image(original, 672 * 384)
    assert actual.size == (192, 320)
    assert actual.mode == "RGB"
    assert actual.getpixel((0, 0)) == (255, 0, 0)


@pytest.mark.parametrize("values", [(0, 32, 1024), (32, 32, 0), (32, 200, 1024), (True, 32, 1024)])
def test_bad_reference_budget_or_aspect_is_rejected(values):
    with pytest.raises(ValueError):
        reference_image_size(*values)
