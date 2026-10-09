# SPDX-License-Identifier: Apache-2.0
# Graph interface follows tgo-app-dev/vpipe, Apache-2.0, pinned in data/engine.json.
"""Native H3 adapter. vpipe owns all inference and Metal kernels."""

import json
import os
from pathlib import Path
import re
import subprocess
import time

from PIL import Image

from .image_inputs import prepare_reference_image
from .io import digest, write_json
from .media import ffmpeg_libraries, finish_native
from . import compute


def _attention_switches(diagnostic_attention):
    # Internal causal controls; the public API keeps its fixed recipe.
    if diagnostic_attention not in (None, "sage-only", "dense"):
        raise ValueError("Unknown native attention diagnostic.")
    return dict(sol_attn=diagnostic_attention is None,
                sage_attn=diagnostic_attention != "dense")


def build_graph(request, assets, prepared, output, *, diagnostic_attention=None, conditioning=None):
    attention = _attention_switches(diagnostic_attention)
    stages = []
    def add(name, kind=None, inputs=(), **config):
        stages.append(dict(id=name, type=kind or name,
                           iports=[dict(src=source, oport=port) for source,port in inputs], config=config))
    add("model-select", hf_dir=assets["native_model"])
    add("text-prompt", text=request["prompt"])
    recipe=assets["recipe"]
    add("minimax-h3-model-config", video_shift=recipe["video_shift"], audio_shift=recipe["audio_shift"],
        lora=assets["adapter"]["path"], lora_scale=recipe["lora_scale"])
    ports=[("",0)]*10; ports[2]=("model-select",0); ports[9]=("minimax-h3-model-config",0)
    add("video-ref-encoder", inputs=(("text-prompt",0),("model-select",0)),
        references=[p["path"] for p in prepared], frames=request["model_num_frames"],
        reference_image_short_edge=0, reference_image_max_pixels=0, unload_when_idle="auto")
    ports[0]=("video-ref-encoder",0); ports[7]=("video-ref-encoder",1); ports[8]=("video-ref-encoder",2)
    for kind, value in (conditioning or {}).items():
        name = "diagnostic-" + kind
        add(name, "load-tensor", path=value["packed"]["path"], sideband=value["sideband"])
        ports[{"text": 0, "video": 7}[kind]] = (name, 0)
    add("generate-video",inputs=ports,width=request["model_width"],height=request["model_height"],
        frames=request["model_num_frames"],fps=request["fps"],steps=recipe["graph_steps"],seed=request["seed"],
        i8_gemm=True,**attention,sol_tau=1.0,sol_dense_layers=1,
        sol_local_radius=1,sage_dense_layers=0,unload_when_idle="always")
    if request.get("x2"):
        add("audio-vae-decode",inputs=(("generate-video",1),("model-select",0)))
        add("save-video", inputs=(("audio-vae-decode",0),), output_url=str(output),
            enable_video=False, enable_audio=True, audio_codec="pcm_f32le", format="wav")
    else:
        add("vae-decode",inputs=(("generate-video",0),("model-select",0)))
        add("audio-vae-decode",inputs=(("generate-video",1),("model-select",0)))
        add("rgb-to-video",inputs=(("vae-decode",0),),fps=request["fps"])
        add("save-video",inputs=(("rgb-to-video",0),("audio-vae-decode",0)),output_url=str(output),enable_video=True,enable_audio=True)
    return dict(id="h3-apple",stages=stages,subpipelines=[])


def prepare_inputs(request, references, directory):
    prepared=[]
    if references is None: return prepared
    for index,path in enumerate(references["image_paths"]):
        with Image.open(path) as image:
            pixels=prepare_reference_image(image,references["pixel_budget"])
        target=directory/f"prepared-{index+1}.png"; pixels.save(target)
        entry=dict(index=index+1,path=str(target),width=pixels.width,height=pixels.height,sha256=digest(target))
        prepared.append(entry)
    return prepared



def audit_log(text, *, diagnostic_attention=None):
    switches = _attention_switches(diagnostic_attention)
    if "baked AdaLN for 4 steps" not in text:
        raise RuntimeError("H3 engine did not confirm the expected four denoising steps; keep the native log.")
    for key, label in (("sol_attn", "Sol-Attn ON"), ("sage_attn", "SageAttention ON")):
        if switches[key] and label not in text:
            raise RuntimeError(f"H3 engine did not confirm the requested attention mode: {label}")
        if not switches[key] and label in text:
            raise RuntimeError(f"H3 engine enabled an excluded attention mode: {label}")
    if switches["sol_attn"] != ("Sol-Attn kept" in text) or re.search(r"sage_attn.*(off at|no matrix cores|requested but)",text):
        raise RuntimeError("H3 attention acceleration fell back; the run was not completed.")


def progress_event(line):
    match = re.search(r"\[PROGRESS\] (\d+)% of '([^']+)' completed.*\((\d+)/(\d+)\)", line)
    if match is None:
        return None
    _percent, phase, completed, total = match.groups()
    completed, total = int(completed), int(total)
    if phase == "denoise" and total in (200, 250) and 0 <= completed <= 200:
        # vpipe initially includes the terminal zero-sigma row in its estimate.
        # The pinned four-step recipe executes exactly 200 transformer blocks.
        step = min(4, completed // 50 + 1)
        return dict(phase="denoise", step=step, steps=4,
                    block=completed - (step - 1) * 50, blocks=50)
    if phase == "vae decode":
        return dict(phase="video_decode", tiles_completed=completed)
    return dict(phase="conditioning" if "encod" in phase else "native_generation")


def runtime_environment(assets):
    # Never inherit experimental noise, allocator or kernel overrides.
    environment={k:v for k,v in os.environ.items() if not k.startswith(("VPIPE_","DYLD_","MTL_","MLX_","FASTVIDEO_"))}
    environment.update(VPIPE_FFMPEG_DIR=str(ffmpeg_libraries()),
        DYLD_LIBRARY_PATH=str(Path(assets["library"]["path"]).parent))
    return environment


def prepare_video_noise(request, prepared, entry, workspace):
    """Bind a diagnostic generated-only array before native RNG replacement.

    Native reference rows overwrite the placeholder prefix after loading noise.
    The native RNG still draws audio before reading this video override.
    """
    import numpy as np
    from ._vendor.fastvideo_mlx.minimax_h3 import video_latent_num_frames
    if not isinstance(entry, dict) or set(entry) != {"path", "sha256"}:
        raise ValueError("Diagnostic video noise needs a path and SHA256.")
    source = Path(entry["path"]).resolve(strict=True)
    checksum = digest(source)
    if checksum != entry["sha256"]:
        raise ValueError("Diagnostic video noise checksum differs.")
    shape = (video_latent_num_frames(request["model_num_frames"])
             * (request["model_height"] // 32) * (request["model_width"] // 32), 96)
    video = np.load(source, allow_pickle=False)
    if (not isinstance(video, np.ndarray) or video.dtype != np.dtype("<f4")
            or video.shape != shape or not np.isfinite(video).all()):
        raise ValueError("Diagnostic video noise has invalid dtype, shape or values.")
    prefix = sum((p["height"] // 32) * (p["width"] // 32) for p in prepared)
    packed = np.concatenate((np.zeros((prefix, 96), dtype="<f4"), video), axis=0)
    target = Path(workspace) / "diagnostic-video-noise.f32"
    with target.open("xb") as stream:
        packed.tofile(stream)
    return dict(source=dict(path=str(source), sha256=checksum), shape=list(shape),
                prefix_rows=prefix, native_floats=int(packed.size),
                packed=dict(path=str(target), sha256=digest(target)))


def run(request, assets, workspace, emit, *, references=None, diagnostics=False,
        replay_plan=None, diagnostic_attention=None, diagnostic_video_noise=None,
        diagnostic_conditioning=None):
    _attention_switches(diagnostic_attention)
    if request["num_steps"]!=4: raise ValueError("H3 requires four denoising steps.")
    workspace=Path(workspace); native=workspace/("native.wav" if request.get("x2") else "native.mp4")
    prepared=prepare_inputs(request,references,workspace)
    conditioning = None
    if diagnostic_conditioning is not None:
        from .conditioning_diagnostic import prepare
        conditioning = prepare(diagnostic_conditioning, prepared, workspace)
    graph=build_graph(request,assets,prepared,native,diagnostic_attention=diagnostic_attention,
                      conditioning=conditioning)
    graph_path=workspace/"input.vpipeline"; write_json(graph_path,graph)
    (workspace/"db").mkdir(); write_json(workspace/"session.json",dict(db=dict(path=str(workspace/"db"))))
    environment=runtime_environment(assets)
    compute_request = request if diagnostic_attention is None else dict(
        request, diagnostic_attention=diagnostic_attention)
    if conditioning is not None:
        compute_request = dict(compute_request, diagnostic_conditioning={
            k: dict(sha256=v["source"]["sha256"], shape=v["shape"], dtype=v["dtype"],
                    sideband=v["sideband"]) for k, v in conditioning.items()})
    noise = None
    if diagnostic_video_noise is not None:
        noise = prepare_video_noise(request, prepared, diagnostic_video_noise, workspace)
        compute_request = dict(compute_request, diagnostic_video_noise=dict(
            sha256=noise["source"]["sha256"], shape=noise["shape"], prefix_rows=noise["prefix_rows"]))
        environment["VPIPE_H3_NOISE_VID"] = noise["packed"]["path"]
    compute_plan, replay = compute.prepare(compute_request, assets, prepared, workspace,
                                           environment, replay=replay_plan)
    if request.get("x2") or diagnostics:
        # The checked native artifact exports normalized channel-first f32.
        # Only this run-owned path is supplied; user environment overrides are dropped.
        environment["VPIPE_H3_LATENT_DUMP"] = str(workspace / "video-latent.f32")
    if diagnostics:
        environment["VPIPE_H3_COND_DUMP"] = str(workspace / "text-conditioning.f32")
    command=[assets["binary"]["path"],"--config",str(workspace/"session.json"),"--launch",str(graph_path)]
    emit(dict(phase="native_generation",message="Generating with h3-apple"))
    start=time.monotonic(); process=None
    try:
        with (workspace/"native.log").open("x") as log:
            # Same process group as the isolated worker: API cancellation kills both.
            process=subprocess.Popen(command,cwd=workspace,env=environment,stdin=subprocess.DEVNULL,
                                     stdout=subprocess.PIPE,stderr=subprocess.STDOUT,text=True,errors='backslashreplace')
            for line in process.stdout:
                log.write(line); log.flush()
                event = progress_event(line)
                if event is not None:
                    emit(event)
            if process.wait()!=0: raise RuntimeError(f"H3 engine exited {process.returncode}; see native.log in the preserved workspace.")
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:process.wait(timeout=5)
            except subprocess.TimeoutExpired:process.kill();process.wait(timeout=10)
        if process is not None and process.stdout is not None:
            process.stdout.close()
    native_seconds=time.monotonic()-start
    log=(workspace/"native.log").read_text()
    audit_log(log, diagnostic_attention=diagnostic_attention)
    if noise is not None:
        confirmation = f"loaded video initial noise ({noise['native_floats']} floats) from {noise['packed']['path']}"
        if log.count(confirmation) != 1:
            raise RuntimeError("Native diagnostic video noise was not confirmed.")
    compute_plan = compute.complete(compute_plan, replay, log, workspace)
    timings=dict(native_generation=native_seconds)
    bridge = {}
    if conditioning is not None:
        bridge["diagnostic_conditioning"] = conditioning
    if noise is not None:
        bridge["diagnostic_video_noise"] = noise
    if request.get("x2"):
        from .runtime.sol_x2 import finish
        bridge.update(finish(request, assets, workspace, log, emit,
                             diagnostics=diagnostics))
        timings.update(bridge.pop("timings_seconds"))
        delivery = dict(kind="normalized-sol-latent-to-mlx-x2", audio="native-float32-pcm")
    else:
        emit(dict(phase="delivery_adapter")); start=time.monotonic()
        delivery=finish_native(native,workspace/"output.mp4",request)
        timings["delivery_adapter"]=time.monotonic()-start
    if diagnostics:
        directory=workspace/"diagnostics"; directory.mkdir(exist_ok=True)
        write_json(directory/"native-run.json",dict(graph=graph,command=command,delivery_command=delivery))
    acceleration = {None: "i8-sol-sage", "sage-only": "i8-sage", "dense": "i8"}[diagnostic_attention]
    return dict(bridge, actual_nfe=4,acceleration=acceleration,
        compute_plan=compute_plan,
        timings_seconds=timings,diagnostics_enabled=diagnostics,diagnostic_export_seconds=0,
        backend=dict(name="h3-apple",upstream="vpipe",binary=assets["binary"],library=assets["library"],tested_interface_commit=assets["tested_interface_commit"]),
        native=dict(graph=graph,graph_sha256=digest(graph_path),log_sha256=digest(workspace/"native.log"),
            prepared_inputs=prepared,recipe=assets["recipe"],adapter=assets["adapter"],
            switches=next(s for s in graph["stages"] if s["id"]=="generate-video")["config"],
            runtime_confirmation=[line for line in log.splitlines() if any(word in line for word in ("Sol-Attn","SageAttention","baked AdaLN","PRELOADED","memory-plan","i8"))],
            rng="Native engine RNG; strict replay also binds the recorded compute plan, inputs and execution environment.",delivery_command=delivery))
