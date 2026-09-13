"""Input and integrity tests; no network, model weights, or machine fixtures."""
import hashlib
import argparse
import json
from pathlib import Path

import pytest

import reproduce


def test_prompt_parser_preserves_paragraphs_and_unicode():
    prompt = "Synthetic <fixture> café.\n\nSecond paragraph."
    record = {"source_case": "Fixture study", "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest()}
    page = "<h4>Fixture study</h4><p>prompt</p><p>Synthetic &lt;fixture&gt; café.</p><p>Second paragraph.</p><p>reference images</p><p>Not prompt</p><h4>Next study</h4><p>prompt</p><p>Other text</p>"
    assert reproduce.prompt_from_html(page, record) == prompt
    with pytest.raises(ValueError, match="changed"):
        reproduce.prompt_from_html(page.replace("café", "changed"), record)


def test_reference_arguments_preserve_image_video_audio_order(tmp_path):
    prompt = tmp_path / "prompt.txt"
    prompt.write_text("Synthetic fixture")
    references = []
    for argument, filenames in (("reference_images", ["one.png", "two.png"]),
                                ("reference_videos", ["motion.mp4"]),
                                ("reference_audio", ["voice.wav"])):
        for name in filenames:
            path = tmp_path / name
            path.write_bytes(name.encode())
            references.append(dict(argument=argument, filename=name, label=name, sha256=reproduce.digest(path)))
    record = {"prompt_sha256": reproduce.digest(prompt), "reproduction": {
        "parameters": {"seed": 42, "duration": 5}, "references": references}}
    kwargs = reproduce.generation_kwargs(record, tmp_path)
    assert [Path(p).name for p in kwargs["reference_images"]] == ["one.png", "two.png"]
    assert Path(kwargs["reference_videos"][0]).name == "motion.mp4"
    assert Path(kwargs["reference_audio"][0]).name == "voice.wav"
    (tmp_path / "two.png").write_bytes(b"Changed")
    with pytest.raises(ValueError, match="Reference"):
        reproduce.generation_kwargs(record, tmp_path)


def test_keyframes_are_scalar_arguments_and_old_files_are_preserved(tmp_path):
    (tmp_path / "prompt.txt").write_text("Synthetic fixture")
    frame = tmp_path / "first.png"
    frame.write_bytes(b"Frame")
    record = {"prompt_sha256": reproduce.digest(tmp_path / "prompt.txt"), "reproduction": {
        "parameters": {}, "references": [{"argument": "first_frame", "filename": "first.png", "label": "First", "sha256": reproduce.digest(frame)}]}}
    assert reproduce.generation_kwargs(record, tmp_path)["first_frame"] == str(frame.resolve())
    with pytest.raises(FileExistsError):
        reproduce.write_once(frame, b"Replacement")
    assert frame.read_bytes() == b"Frame"


def test_rejects_paths_and_unexpected_remote_sources(tmp_path):
    with pytest.raises(ValueError):
        reproduce.safe_file(tmp_path, "../outside.png")
    with pytest.raises(ValueError):
        reproduce.fetch("https://example.invalid/untrusted", 100)


def test_published_prompt_needs_no_source_page_fetch(tmp_path, monkeypatch):
    prompt = "Synthetic exact prompt.\n\nSecond paragraph."
    record = {"case": 1, "prompt": prompt, "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
              "reproduction": {"references": [], "model_manifest": "models/t2va.json"}}
    record_path = tmp_path / "record.json"
    record_path.write_text(json.dumps(record))
    def fetch(url, limit):
        assert url == reproduce.SITE + "models/t2va.json"
        return b'{"files": []}'
    monkeypatch.setattr(reproduce, "fetch", fetch)
    destination = tmp_path / "inputs"
    reproduce.download_inputs(argparse.Namespace(case=1, record=record_path, directory=destination,
                                                 prompt_file=None, guide_html=None))
    assert (destination / "prompt.txt").read_text() == prompt
