"""Native interface, delivery and cancellation checks without loading weights."""
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import time

from PIL import Image
import pytest

from h3_apple import resolve
from h3_apple import process as runner
from h3_apple import vpipe, vpipe_assets
from h3_apple.io import digest
from h3_apple.media import finish_native, tool, validate


def assets():
    return dict(native_model="/native",adapter=dict(path="/adapter"),recipe=dict(
        video_shift=6.0,audio_shift=3.0,lora_scale=1.0,graph_steps=5))


@pytest.mark.parametrize("preset", ["ultrafast", "vpipe-dense"])
def test_modes_preserve_full_prompt_and_explicit_switches(preset):
    prompt="Picture 1 → picture 2.\nFull dialogue and soundscape, unchanged."
    request=resolve(prompt,preset=preset,seed=0).to_dict()
    graph=vpipe.build_graph(request,assets(),[],"/output.mp4")
    nodes={s["id"]:s for s in graph["stages"]}
    assert nodes["text-prompt"]["config"]["text"]==prompt
    config=nodes["generate-video"]["config"]
    assert config["steps"]==5 and config["i8_gemm"] is True
    assert config["sol_attn"]==config["sage_attn"]==(preset=="ultrafast")
    assert resolve("Default").preset=="ours"
    seen=set()
    for node in graph["stages"]:
        assert all(not p["src"] or p["src"] in seen for p in node["iports"])
        seen.add(node["id"])


@pytest.mark.parametrize("anchors", [("first",),("last",),("first","last")])
def test_keyframe_ports_keep_first_and_last_roles(tmp_path, anchors):
    image=tmp_path/"image.png"; Image.new("RGB",(64,32)).save(image)
    request=resolve("Anchor test",preset="ultrafast",**{a+"_frame":image for a in anchors}).to_dict()
    prepared=vpipe.prepare_inputs(request,dict(image_paths=[str(image)]*len(anchors),anchors=list(anchors)),tmp_path)
    graph=vpipe.build_graph(request,assets(),prepared,tmp_path/"out.mp4")
    ports=next(s for s in graph["stages"] if s["id"]=="generate-video")["iports"]
    assert ports[5]["src"]==("encode-first" if "first" in anchors else "")
    assert ports[6]["src"]==("encode-last" if "last" in anchors else "")
    assert [p["anchor"] for p in prepared]==list(anchors)


def test_reference_order_and_resizing_are_shared(tmp_path):
    paths=[tmp_path/"z.png",tmp_path/"a.png"]
    for path,color in zip(paths,("red","blue")):Image.new("RGB",(960,544),color).save(path)
    request=resolve("Picture 1 red, picture 2 blue",preset="ultrafast",reference_images=paths,reference_resize="match").to_dict()
    prepared=vpipe.prepare_inputs(request,dict(image_paths=paths,pixel_budget=960*544),tmp_path)
    graph=vpipe.build_graph(request,assets(),prepared,tmp_path/"out.mp4")
    config=next(s for s in graph["stages"] if s["id"]=="video-ref-encoder")["config"]
    assert config["references"]==[p["path"] for p in prepared]
    assert [Image.open(p["path"]).getpixel((0,0)) for p in prepared]==[(255,0,0),(0,0,255)]
    assert all(p["width"]==960 and p["height"]==544 for p in prepared)


@pytest.mark.parametrize("text", ["", "baked AdaLN for 4 steps", "baked AdaLN for 4 steps\nSol-Attn ON\nSageAttention ON",
    "baked AdaLN for 4 steps\nSol-Attn ON\nSageAttention ON\nSol-Attn kept\nsage_attn is off at 200 rows"])
def test_ultrafast_never_reports_success_for_missing_or_fallback_acceleration(text):
    with pytest.raises(RuntimeError): vpipe.audit_log(text,"ultrafast")


def test_native_progress_uses_four_actual_forwards():
    from h3_apple.progress import ProgressBar
    import io
    output = io.StringIO()
    display = ProgressBar(output)
    for complete, total in ((0, 250), (25, 250), (50, 200), (200, 200)):
        event = vpipe.progress_event(f"[PROGRESS] 0% of 'denoise' completed at 12:00 ({complete}/{total})")
        display(event)
    assert "100%  Step 4/4" in output.getvalue()
    assert "Step 5/" not in output.getvalue()
    assert vpipe.progress_event("ordinary native diagnostic") is None


@pytest.mark.parametrize("frames", [120,124,157,240,360])
def test_native_delivery_has_sample_accurate_endpoints(tmp_path,frames):
    count=((frames-5+16)//17)*17+5
    request=dict(width=64,height=64,model_width=96,model_height=64,num_frames=frames,
        model_num_frames=count,fps=24,audio_sample_rate=32000,audio_channels=2,duration=frames/24)
    source=tmp_path/"native.mp4"; output=tmp_path/"output.mp4"
    subprocess.run([tool("ffmpeg"),"-v","error","-nostdin","-n","-f","lavfi","-i",f"testsrc2=size=96x64:rate=24:duration={count/24}",
        "-f","lavfi","-i",f"sine=sample_rate=32000:duration={count/24}","-frames:v",str(count),"-c:v","libx264",
        "-preset","ultrafast","-c:a","aac","-ac","2","-t",str(count/24),str(source)],check=True,timeout=20)
    finish_native(source,output,request)
    validate(output,request)


def native_fixture(tmp_path,monkeypatch):
    root=tmp_path/"model";root.mkdir()
    for name in ("transformer","text_encoder","tokenizer","video_vae","audio_vae"):
        component=root/name; component.mkdir();(component/"model.safetensors").write_bytes(b"test-only")
        (component/"config.json").write_text("{}")
    (root/"transformer/config.json").write_text(json.dumps(dict(_class_name="MiniMaxH3DiTModel",num_layers=50,quantization=dict(bits=8,group_size=64))))
    (root/"model_index.json").write_text(json.dumps(dict(_minimax_h3=dict(partition="fl2va"))))
    lora=tmp_path/"lora";lora.write_bytes(b"test adapter")
    monkeypatch.setattr(vpipe_assets,"FL12_SOURCE",dict(filename="test-adapter",sha256=digest(lora)))
    binary=tmp_path/"vpipe";binary.write_text("#!/bin/sh\nexit 0\n");binary.chmod(0o755)
    library=tmp_path/"libvpipe.0.1.dylib";library.write_bytes(b"test library")
    (tmp_path/"libvpipe.0.dylib").symlink_to(library)
    return dict(model_dir=tmp_path/"bundle",native_model=root,lora=lora,vpipe_binary=binary,vpipe_library=library)


def test_registered_assets_reject_mutation_and_never_overwrite(tmp_path,monkeypatch):
    options=native_fixture(tmp_path,monkeypatch)
    manifest=vpipe_assets.import_vpipe_assets(**options)
    assert vpipe_assets.load_vpipe_assets(options["model_dir"],verify=True)["identity"]==manifest["identity"]
    with pytest.raises(FileExistsError):vpipe_assets.import_vpipe_assets(**options)
    path=options["vpipe_library"];stat=path.stat();path.write_bytes(b"fake library")
    os.utime(path,ns=(stat.st_atime_ns,stat.st_mtime_ns))
    with pytest.raises(ValueError,match="checksum"):
        vpipe_assets.load_vpipe_assets(options["model_dir"])


def test_wrong_lora_fails_before_registering_bundle(tmp_path,monkeypatch):
    options=native_fixture(tmp_path,monkeypatch);options["lora"].write_bytes(b"wrong adapter")
    with pytest.raises(ValueError,match="pinned adapter"):vpipe_assets.import_vpipe_assets(**options)
    assert not options["model_dir"].exists()


def test_native_video_vae_source_directory_is_registered(tmp_path, monkeypatch):
    options = native_fixture(tmp_path, monkeypatch)
    vae = options["native_model"] / "video_vae"
    source = vae / "source"
    source.mkdir()
    (vae / "model.safetensors").rename(source / "model.safetensors")
    (source / "config.json").write_text("{}")
    manifest = vpipe_assets.import_vpipe_assets(**options)
    weights = source / "model.safetensors"
    assert any(entry["path"] == str(weights) and entry["sha256"] == digest(weights)
               for entry in manifest["files"])
    vpipe_assets.load_vpipe_assets(options["model_dir"], verify=True)
    weights.unlink()
    with pytest.raises(ValueError, match="Missing native weights: video_vae"):
        vpipe_assets.model_partition(options["native_model"])


def test_hand_edited_recipe_is_rejected_even_with_new_manifest_checksum(tmp_path, monkeypatch):
    options = native_fixture(tmp_path, monkeypatch)
    vpipe_assets.import_vpipe_assets(**options)
    path = options["model_dir"] / "vpipe.json"
    data = json.loads(path.read_text())
    data["recipe"]["video_shift"] = 12
    data["identity"] = vpipe_assets.identity({k:v for k,v in data.items() if k != "identity"})
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError, match="four-step adapter recipe"):
        vpipe_assets.load_vpipe_assets(options["model_dir"])


def test_unintegrated_native_reference_media_is_rejected(tmp_path, monkeypatch):
    from h3_apple import media
    image = tmp_path / "image.png"
    Image.new("RGB", (32, 32)).save(image)
    monkeypatch.setattr(media, "probe_reference", lambda *_args: {})
    for options in (dict(reference_videos=[tmp_path / "video.mp4"]),
                    dict(reference_images=[image], reference_audio=[tmp_path / "sound.wav"])):
        with pytest.raises(ValueError, match="use ours"):
            resolve("Complete input", preset="ultrafast", **options)


def test_native_task_mismatch_fails_before_worker(tmp_path,monkeypatch):
    monkeypatch.setattr(vpipe_assets,"load_vpipe_assets",lambda _:dict(identity="fixture",tasks=["ref2va"]))
    with pytest.raises(ValueError,match="T2VA model bundle"):
        runner.run_generation(resolve("Text",preset="ultrafast"),output=tmp_path/"out.mp4")
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("mode", ["timeout","callback"])
def test_cancellation_reaps_native_descendant(tmp_path,monkeypatch,mode):
    # A real two-process worker tree exercises the same group used by vpipe.
    worker=tmp_path/"worker.py"
    worker.write_text("import subprocess,sys,json,pathlib,time\n"
        "s=json.loads(sys.stdin.readline())\n"
        "p=subprocess.Popen([sys.executable,'-c',\"import time,signal;signal.signal(signal.SIGTERM,signal.SIG_IGN);print('ready',flush=True);time.sleep(60)\"],stdout=subprocess.PIPE)\n"
        "p.stdout.readline()\n"
        "pathlib.Path(s['workspace'],'native.pid').write_text(str(p.pid))\n"
        "print(json.dumps({'phase':'native_generation'}),flush=True)\ntime.sleep(60)\n")
    real_popen=subprocess.Popen
    monkeypatch.setattr(vpipe_assets,"load_vpipe_assets",lambda _:dict(identity="fixture",tasks=["t2va"]))
    monkeypatch.setattr(runner.subprocess,"Popen",lambda args,**kw:real_popen([sys.executable,str(worker)],**kw))
    def cancel(_event):raise KeyboardInterrupt()
    output=tmp_path/"out.mp4"
    with pytest.raises(TimeoutError if mode=="timeout" else KeyboardInterrupt):
        runner.run_generation(resolve("Text",preset="ultrafast"),output=output,timeout=0.5,
            on_progress=cancel if mode=="callback" else None)
    record=json.loads(output.with_suffix(".run.json").read_text())
    assert record["status"]==("failed" if mode=="timeout" else "cancelled")
    assert not output.exists()
    pid=int(Path(record["workspace"],"native.pid").read_text())
    for _ in range(20):
        status=subprocess.run(["ps","-o","stat=","-p",str(pid)],capture_output=True,text=True).stdout.strip()
        if not status or status.startswith("Z"):break
        time.sleep(.05)
    assert not status or status.startswith("Z")
