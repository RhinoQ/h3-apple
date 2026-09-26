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


def build_graph(request, assets, prepared, output):
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
    add("generate-video",inputs=ports,width=request["model_width"],height=request["model_height"],
        frames=request["model_num_frames"],fps=request["fps"],steps=recipe["graph_steps"],seed=request["seed"],
        i8_gemm=True,sol_attn=True,sage_attn=True,sol_tau=1.0,sol_dense_layers=1,
        sol_local_radius=1,sage_dense_layers=0,unload_when_idle="always")
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



def audit_log(text):
    if "baked AdaLN for 4 steps" not in text:
        raise RuntimeError("H3 engine did not confirm the expected four denoising steps; keep the native log.")
    for label in ("Sol-Attn ON","SageAttention ON"):
        if label not in text:
            raise RuntimeError(f"H3 engine did not confirm the requested attention mode: {label}")
    if "Sol-Attn kept" not in text or re.search(r"sage_attn.*(off at|no matrix cores|requested but)",text):
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


def run(request, assets, workspace, emit, *, references=None, diagnostics=False,
        replay_plan=None):
    if request["num_steps"]!=4: raise ValueError("H3 requires four denoising steps.")
    workspace=Path(workspace); native=workspace/"native.mp4"
    prepared=prepare_inputs(request,references,workspace)
    graph=build_graph(request,assets,prepared,native)
    graph_path=workspace/"input.vpipeline"; write_json(graph_path,graph)
    (workspace/"db").mkdir(); write_json(workspace/"session.json",dict(db=dict(path=str(workspace/"db"))))
    environment=runtime_environment(assets)
    compute_plan, replay = compute.prepare(request, assets, prepared, workspace,
                                           environment, replay=replay_plan)
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
    log=(workspace/"native.log").read_text(); audit_log(log)
    compute_plan = compute.complete(compute_plan, replay, log, workspace)
    emit(dict(phase="delivery_adapter")); start=time.monotonic()
    delivery=finish_native(native,workspace/"output.mp4",request)
    timings=dict(native_generation=native_seconds,delivery_adapter=time.monotonic()-start)
    if diagnostics:
        directory=workspace/"diagnostics"; directory.mkdir()
        write_json(directory/"native-run.json",dict(graph=graph,command=command,delivery_command=delivery))
    return dict(actual_nfe=4,acceleration="i8-sol-sage",
        compute_plan=compute_plan,
        timings_seconds=timings,diagnostics_enabled=diagnostics,diagnostic_export_seconds=0,
        backend=dict(name="h3-apple",upstream="vpipe",binary=assets["binary"],library=assets["library"],tested_interface_commit=assets["tested_interface_commit"]),
        native=dict(graph=graph,graph_sha256=digest(graph_path),log_sha256=digest(workspace/"native.log"),
            prepared_inputs=prepared,recipe=assets["recipe"],adapter=assets["adapter"],
            switches=next(s for s in graph["stages"] if s["id"]=="generate-video")["config"],
            runtime_confirmation=[line for line in log.splitlines() if any(word in line for word in ("Sol-Attn","SageAttention","baked AdaLN","PRELOADED","memory-plan","i8"))],
            rng="Native engine RNG; strict replay also binds the recorded compute plan, inputs and execution environment.",delivery_command=delivery))
