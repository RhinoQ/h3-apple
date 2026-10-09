"""Internal, hash-bound native conditioning crossovers (image references only)."""

import struct
from pathlib import Path

from .io import digest


def prepare(entries, prepared, workspace):
    import numpy as np
    if (not isinstance(entries, dict) or not entries
            or set(entries) - {"text", "video"} or not prepared):
        raise ValueError("Diagnostic conditioning needs text/video arrays and image references.")
    result = {}
    for kind, entry in entries.items():
        if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
            raise ValueError("Diagnostic conditioning needs a path and SHA256.")
        source = Path(entry["path"]).resolve(strict=True)
        checksum = digest(source)
        if checksum != entry["sha256"]:
            raise ValueError("Diagnostic conditioning checksum differs.")
        with np.load(source, allow_pickle=False) as arrays:
            if set(arrays.files) != ({"values", "tags"} if kind == "text" else {"values"}):
                raise ValueError("Unexpected diagnostic conditioning arrays.")
            values = arrays["values"]
            if (values.dtype != np.dtype("<f4") or values.ndim != 2
                    or not np.isfinite(values).all()):
                raise ValueError("Invalid diagnostic conditioning dtype, shape or values.")
            sideband = {}
            if kind == "text":
                tags = arrays["tags"]
                if (values.shape[1] != 5120 or not 0 < len(values) <= 16384
                        or tags.shape != (len(values),) or tags.dtype.kind not in "iu"
                        or not np.isin(tags, (0, 1)).all()):
                    raise ValueError("Invalid diagnostic text shape or token tags.")
                # IEEE round-to-nearest-even; native consumes BF16 conditioning.
                bits = values.view(np.uint32)
                payload = ((bits + 0x7fff + ((bits >> 16) & 1)) >> 16).astype("<u2")
                if np.any((payload & 0x7fff) == 0x7f80):
                    raise ValueError("Diagnostic text overflows BF16.")
                dtype = 2
                sideband = dict(partition="ref2va", token_tags=tags.tolist(), references=[
                    dict(kind="image", latent_frames=1, latent_height=p["height"] // 16,
                         latent_width=p["width"] // 16, audio_latents=0) for p in prepared])
            else:
                rows = sum((p["height"] // 32) * (p["width"] // 32) for p in prepared)
                if values.shape != (rows, 96):
                    raise ValueError("Diagnostic reference rows disagree with image geometry.")
                payload, dtype = values, 3
            target = Path(workspace) / f"diagnostic-{kind}.tensor"
            with target.open("xb") as stream:
                stream.write(struct.pack("<8sIIIIQ", b"VPTENSOR", 1, dtype, 2, 0, values.size))
                stream.write(struct.pack("<qq", *values.shape))
                stream.write(payload.tobytes(order="C"))
            result[kind] = dict(source=dict(path=str(source), sha256=checksum),
                shape=list(values.shape), dtype=dtype, sideband=sideband,
                packed=dict(path=str(target), sha256=digest(target)))
    return result
