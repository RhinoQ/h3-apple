"""Reference-file order and legacy single-image input boundaries."""

import numpy as np
from PIL import Image
import pytest

from h3_apple.runtime.ref2va_pipeline import prepare_images


def test_ordered_files_reach_both_encoders_as_distinct_rgb_images(tmp_path):
    paths = []
    for index, size in enumerate(((64, 32), (32, 64), (64, 64), (96, 32))):
        path = tmp_path / f"{index}.png"
        Image.new("RGB", size, (index * 50, 20, 30)).save(path)
        paths.append(str(path))
    images = prepare_images(dict(image_paths=[paths[i] for i in (2, 0, 3, 1)], pixel_budget=8192))
    assert [image.getpixel((0, 0))[0] for image in images] == [100, 0, 150, 50]
    assert [image.size for image in images] == [(64, 64), (64, 32), (96, 32), (32, 64)]
    single = prepare_images(dict(image_path=paths[0], pixel_budget=8192))
    listed = prepare_images(dict(image_paths=[paths[0]], pixel_budget=8192))
    np.testing.assert_array_equal(single[0], listed[0])


@pytest.mark.parametrize("options", [dict(), dict(image_path="a", image_paths=["b"]),
    dict(image_paths=[]), dict(image_paths=["a"] * 10), dict(image_paths="a"),
    dict(image_paths=[None]), dict(image_paths=[""])])
def test_invalid_image_collections_fail_before_file_reads(options):
    with pytest.raises(ValueError):
        prepare_images(dict(options, pixel_budget=8192))
