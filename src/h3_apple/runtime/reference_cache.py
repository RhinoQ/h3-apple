"""Explicit, immutable conditioning snapshots for paired reference experiments."""

import json
from pathlib import Path

import numpy as np

from ..io import digest
from ..media import VIDEO_REFERENCE_CANVAS


def cache_contract(request, options):
    # Snapshot paths differ between workers; ordered bytes carry their meaning.
    omitted = {"reference_images", "reference_videos", "reference_audio"}
    media = []
    for kind in ("image", "audio", "video"):
        media.extend(dict(kind=kind, sha256=digest(path))
                     for path in options.get(f"{kind}_paths", []))
    return dict(request={k: v for k, v in request.items() if k not in omitted},
                media=media, pixel_budget=options["pixel_budget"],
                video_audio=options.get("video_audio", True),
                video_reference_canvas=dict(VIDEO_REFERENCE_CANVAS),
                model_identity=options["cache_model_identity"],
                source_identity=options["cache_source_identity"])


def load_or_build(directory, contract, build):
    """Read back the first snapshot too, so both arms use serialized arrays.

    An existing incomplete or mismatched directory fails closed. There is no
    eviction, overwrite, implicit cache search, or pickle deserialization.
    """
    directory = Path(directory)
    created = not directory.exists()
    if created:
        directory.mkdir(parents=True, exist_ok=False)
        arrays, metadata = build()
        with (directory / "arrays.npz").open("xb") as stream:
            np.savez(stream, **arrays)
        document = dict(schema="h3-reference-pair/v1", contract=contract, metadata=metadata,
                        arrays_sha256=digest(directory / "arrays.npz"))
        with (directory / "manifest.json").open("x") as stream:
            json.dump(document, stream, sort_keys=True, allow_nan=False)
            stream.write("\n")
    document = json.loads((directory / "manifest.json").read_text())
    if document.get("schema") != "h3-reference-pair/v1" or document.get("contract") != contract:
        raise ValueError("Conditioning cache request, media, model or runtime mismatch.")
    if digest(directory / "arrays.npz") != document["arrays_sha256"]:
        raise ValueError("Conditioning cache array checksum mismatch.")
    with np.load(directory / "arrays.npz", allow_pickle=False) as archive:
        arrays = {key: archive[key].copy() for key in archive.files}
    if not all(np.isfinite(value).all() for value in arrays.values()):
        raise ValueError("Conditioning cache contains nonfinite arrays.")
    metadata = document["metadata"]
    metadata["conditioning_cache"] = dict(path=str(directory), created=created,
        arrays_sha256=document["arrays_sha256"], manifest_sha256=digest(directory / "manifest.json"))
    return arrays, metadata
