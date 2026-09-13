"""Reference boundaries and gate isolation; trained and quality evidence are separate."""

from dataclasses import replace
from types import SimpleNamespace

import numpy as np
import pytest

from h3_apple.conversion import ref2va_gate_plan
from h3_apple.runtime.ref2va import ReferenceGeometry, build_ref2va_layout
from h3_apple._vendor.fastvideo_mlx.minimax_h3_vsa import (
    prefix_segments_from_layout, build_h3_tile_geometry, build_block_mask,
)


def gates():
    return SimpleNamespace(tensors={
        f"transformer_blocks.{i}.attn.to_gate_compress.set_weight":
        SimpleNamespace(shape=(7168, 5376)) for i in range(50)})


def test_transplant_selects_only_gates_from_full_fasth3_adapter():
    header = gates()
    header.tensors["transformer_blocks.0.attn.to_q.lora_A.weight"] = SimpleNamespace(shape=(64, 5376))
    header.tensors["proj_in.diff"] = SimpleNamespace(shape=(5376, 96))
    plans = ref2va_gate_plan(header)
    assert len(plans) == 50
    assert all(key.endswith(".attn.to_gate_compress.weight") for key in plans)
    assert set(plans.values()) == {f"transformer_blocks.{i}.attn.to_gate_compress.set_weight" for i in range(50)}


@pytest.mark.parametrize("problem", ["missing", "duplicate", "extra", "shape", "unknown_suffix"])
def test_incomplete_or_ambiguous_gate_files_fail(problem):
    header = gates()
    name = "transformer_blocks.0.attn.to_gate_compress.set_weight"
    if problem == "missing": del header.tensors[name]
    elif problem == "duplicate": header.tensors["blocks.0.attn.to_gate_compress.weight"] = header.tensors[name]
    elif problem == "extra": header.tensors[name.replace("blocks.0", "blocks.50")] = header.tensors[name]
    elif problem == "shape": header.tensors[name].shape = (5376, 7168)
    else: header.tensors[name + ".other"] = header.tensors.pop(name)
    with pytest.raises(ValueError): ref2va_gate_plan(header)


def test_each_ordered_reference_and_audio_segment_has_its_own_tiles():
    refs = [ReferenceGeometry("image", 1, 4, 6), ReferenceGeometry("video", 2, 4, 6, True, 3)]
    layout = build_ref2va_layout([1, 0, 1], refs, 5, 10, 18, 4)
    expected = (3, 6, 6, 12, 8)
    assert prefix_segments_from_layout(layout, (1, 2, 2)) == expected
    geometry = build_h3_tile_geometry(expected, (5, 5, 9))
    cuts = np.cumsum((0, *expected))
    occupied = []
    for start, end in zip(cuts[:-1], cuts[1:]):
        occupied.append(set(geometry.untile_combined_index[start:end] // 64))
    for index, tiles in enumerate(occupied):
        assert all(not (tiles & previous) for previous in occupied[:index])
    assert sum(geometry.variable_block_sizes) == layout.sequence_length
    assert len(np.unique(geometry.untile_combined_index)) == layout.sequence_length


def test_malformed_prefix_or_nonfinal_generated_video_is_rejected():
    layout = build_ref2va_layout([1, 0, 1], [ReferenceGeometry("image", 1, 4, 6)], 2, 4, 6, 4)
    bad = [replace(layout, reference_prefix_segments=(17,)),
           replace(layout, video_indices=layout.video_indices[::-1])]
    for value in bad:
        with pytest.raises(ValueError): prefix_segments_from_layout(value, (1, 2, 2))


def test_kablex_rounding_adjacent_blocks_and_boundary_ties():
    # Nine non-sink blocks: round(9 * .25) = 2, plus forced diagonal +/- 1.
    scores = np.broadcast_to(np.arange(13, dtype=np.float32), (1, 13, 13)).copy()
    mask = build_block_mask(scores, 4, 9, .75, True, routing_mode="kablex")
    assert np.flatnonzero(mask[0, 4]).tolist() == [0, 1, 2, 3, 4, 5, 11, 12]
    assert mask[:, :4].all() and mask[:, :, :4].all()
    tied = build_block_mask(np.zeros_like(scores), 4, 9, .75, True, routing_mode="kablex")
    assert tied.all()
