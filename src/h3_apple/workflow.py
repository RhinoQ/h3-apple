"""Compose the existing generation and restoration paths without changing inference."""

import json
import math
import shlex

from .api import DownloadApprovalRequired, GenerationResult
from .io import automatic_output, write_json
from .preparation import LIMIT
from .process import run_generation
from .super_resolution import assets
from .upscale import check_environment, output_paths, upscale


def generate_upscaled(request, *, output, model_dir, on_progress, diagnostics,
                      timeout, allow_large_download, upscale_model_dir, upscale_timeout):
    for value in (timeout, upscale_timeout):
        if isinstance(value, bool) or not math.isfinite(value) or value <= 0:
            raise ValueError("Timeouts must be positive and finite.")
    if type(diagnostics) is not bool or type(allow_large_download) is not bool:
        raise ValueError("diagnostics and allow_large_download must be booleans.")
    video, _ = output_paths(automatic_output() if output is None else output)
    native_path, _ = output_paths(video.with_name(f"{video.stem}.native.mp4"))
    check_environment(video)
    if request.mode == "VSA":
        from .vsa_preparation import plan
    else:
        from .preparation import plan
        from .runtime.backend import check_dependencies
        check_dependencies()
    base = plan(model_dir, progress=on_progress)
    restoration = assets.plan(upscale_model_dir)
    combined = {key: base[key] + restoration[key]
                for key in ("download_bytes", "additional_disk_bytes")}
    if on_progress:
        on_progress(dict(phase="workflow", message=(
            "Generate native video, then upscale 2x. Requires 128 GiB memory; "
            "restoration adds about 20 minutes per 5 seconds of 768p video (M5 Max).")))
        on_progress(dict(combined, phase="model_plan"))
    if combined["download_bytes"] > LIMIT and not allow_large_download:
        raise DownloadApprovalRequired(combined)
    # Discover unavailable/corrupt restoration models before spending time on generation.
    assets.prepare(upscale_model_dir, on_progress=on_progress)
    native = run_generation(request, output=native_path, model_dir=model_dir,
        on_progress=on_progress, diagnostics=diagnostics, timeout=timeout,
        allow_large_download=allow_large_download)
    retry = f"h3 upscale --input {shlex.quote(str(native.video_path))}"
    try:
        if on_progress:
            on_progress(dict(phase="workflow", message=f"Native video saved: {native.video_path}. Starting super-resolution."))
        restored = upscale(native.video_path, output=video, model_dir=upscale_model_dir,
            on_progress=on_progress, diagnostics=diagnostics, timeout=upscale_timeout)
    except KeyboardInterrupt:
        raise KeyboardInterrupt(f"Native video saved: {native.video_path}. Resume with: {retry}") from None
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        raise RuntimeError(f"Native video saved: {native.video_path}. Retry with: {retry}. "
                           f"Super-resolution failed: {error}") from error
    record = json.loads(restored.metadata_path.read_text())
    elapsed = native.elapsed_seconds + restored.elapsed_seconds
    record["generation"] = dict(video_path=str(native.video_path), metadata_path=str(native.metadata_path),
                                elapsed_seconds=native.elapsed_seconds, seed=native.seed)
    record["total_elapsed_seconds"] = elapsed
    write_json(restored.metadata_path, record)
    return GenerationResult(restored.video_path, restored.metadata_path, elapsed,
                            native.seed, native.video_path)
