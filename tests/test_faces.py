"""Optional restoration boundaries; synthetic media and detections only."""
import copy
import hashlib
import json
from pathlib import Path

import pytest

from h3_apple import enhance_faces
from h3_apple.cli import parser
from h3_apple.faces import assets


def test_face_cli_is_a_separate_operation():
    args = parser().parse_args(["enhance-faces", "--input", "a.mp4", "--output", "b.mp4"])
    assert args.video == "a.mp4" and args.output == "b.mp4" and args.timeout == 7200
    assert parser().parse_args(["prepare-faces", "--plan"]).plan


@pytest.mark.parametrize("options", [{"timeout": 0}, {"timeout": True}, {"timeout": float("nan")}, {"diagnostics": 1}])
def test_face_api_rejects_invalid_options_without_loading(options):
    with pytest.raises(ValueError):
        enhance_faces("missing.mp4", **options)


def test_face_api_never_overwrites_input_or_dangling_link(tmp_path):
    source = tmp_path / "source.mp4"
    source.write_bytes(b"source")
    with pytest.raises(FileExistsError):
        enhance_faces(source, output=source)
    out = tmp_path / "out.mp4"
    out.symlink_to(tmp_path / "missing")
    with pytest.raises(FileExistsError):
        enhance_faces(source, output=out)
    assert source.read_bytes() == b"source"


def test_face_assets_reuse_verified_files_and_reject_corruption(tmp_path, monkeypatch):
    reuse, target = tmp_path / "reuse", tmp_path / "target"
    reuse.mkdir()
    (reuse / "weights").write_bytes(b"fixed")
    item = dict(path="weights", bytes=5, sha256=hashlib.sha256(b"fixed").hexdigest(), url="https://example.invalid/no-network")
    monkeypatch.setattr(assets, "manifest", lambda: dict(recipe="test", files=[item]))
    assert assets.plan(target, [reuse])["download_bytes"] == 0
    monkeypatch.setattr(assets, "download", lambda *a, **k: pytest.fail("Must reuse without downloading"))
    assets.prepare(target, [reuse])
    assert assets.verify(target) == target
    (target / "weights").unlink()
    (target / "weights").write_bytes(b"wrong")
    with pytest.raises(ValueError, match="checksum mismatch"):
        assets.plan(target, [reuse])


def geometry():
    pytest.importorskip("numpy")
    from h3_apple.faces import geometry
    return geometry


BOX = [30., 40., 110., 140., .99]
def row(frame, boxes, cut=False):
    return dict(frame=frame, boxes=boxes, cut=cut)


def test_one_gap_is_filled_without_modifying_observed_boxes():
    rows = [row(0, [BOX.copy()]), row(1, []), row(2, [[32., 40., 112., 140., .98]])]
    observed = copy.deepcopy([rows[0], rows[2]])
    geometry().fill_single_gaps(rows)
    assert rows[1]["boxes"] == [[31., 40., 111., 140., .98]]
    assert [rows[0], rows[2]] == observed


@pytest.mark.parametrize("rows", [
    [row(0, [BOX]), row(1, [], True), row(2, [BOX])],
    [row(0, [BOX]), row(1, []), row(2, [BOX], True)],
    [row(0, [BOX]), row(1, []), row(2, []), row(3, [BOX])],
    [row(0, [BOX, BOX]), row(1, []), row(2, [BOX])],
    [row(0, [BOX]), row(1, []), row(2, [[330., 40., 410., 140., .99]])],
])
def test_unsafe_gaps_are_not_filled(rows):
    before = copy.deepcopy(rows)
    geometry().fill_single_gaps(rows)
    assert rows == before


def test_profile_box_track_does_not_require_eye_landmarks():
    rows = [row(i, [[2., 20., 52., 130., .99]], i == 0) for i in range(8)]
    selected, tracks = geometry().association(rows, 1024, 576)
    assert len(selected) == 8 and len(tracks) == 1
    assert all(r["crop"][0] == 0 for r in selected)


def test_large_faces_short_tracks_and_cuts():
    g = geometry()
    assert not g.association([row(i, [[20., 20., 220., 260., .99]], i == 0) for i in range(8)], 1024, 576)[0]
    assert not g.association([row(i, [BOX], i == 0) for i in range(4)], 1024, 576)[0]
    selected, tracks = g.association([row(i, [BOX], i in (0, 6)) for i in range(12)], 1024, 576)
    assert len(selected) == 12 and len(tracks) == 2
    assert selected[5]["track"] != selected[6]["track"]


def test_composite_changes_only_source_derived_mask():
    np = pytest.importorskip("numpy")
    from PIL import Image
    g = geometry()
    original = Image.new("RGB", (1024, 576), "gray")
    rec = dict(source_box=BOX[:4], crop=[0, 0, 256, 256])
    restored = Image.new("RGB", (256, 256), "red")
    result = np.asarray(g.composite(original, restored, rec))
    mask = np.zeros((576, 1024), dtype=bool)
    mask[:256, :256] = g.alpha_mask(rec) > 0
    assert np.array_equal(result[~mask], np.asarray(original)[~mask])
    assert not np.array_equal(result[mask], np.asarray(original)[mask])
