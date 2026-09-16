"""Small user-facing commands for Ours generation and local model preparation."""

import argparse
from dataclasses import asdict
import json
import sys

from .api import generate, resolve


def progress(event):
    phase = event.get("phase", "progress")
    if "block" in event:
        line = f"Denoise {event['step']}/{event['steps']}, block {event['block']}/{event['blocks']}"
    elif "file" in event:
        line = f"Preparing {event['file']}"
    elif "tiles_completed" in event:
        line = f"Video decode: {event['tiles_completed']} tiles complete"
    elif phase == "model_plan":
        line = (f"Missing downloads: {event['download_bytes'] / 1024**3:.2f} GiB; "
                f"additional space including conversion: {event['additional_disk_bytes'] / 1024**3:.2f} GiB; "
                f"source-cache space requirement: {event['cache_additional_disk_bytes'] / 1024**3:.2f} GiB")
    else:
        line = phase.replace("_", " ").capitalize()
    print(line, file=sys.stderr, flush=True)


def parser():
    top = argparse.ArgumentParser(prog="h3", description="Generate MiniMax-H3 video with stereo audio on Apple Silicon.")
    from . import __version__
    top.add_argument("--version", action="version", version=f"h3-apple {__version__}")
    commands = top.add_subparsers(dest="command", required=True)
    for name in ("generate", "resolve"):
        command = commands.add_parser(name)
        prompts = command.add_mutually_exclusive_group(required=True)
        prompts.add_argument("--prompt")
        prompts.add_argument("--prompt-file")
        command.add_argument("--preset", default="ours")
        command.add_argument("--task", choices=("t2va", "fl2va", "ref2va"),
                             help="Infer from inputs when omitted; reject mismatched task and inputs")
        command.add_argument("--first-frame", help="FL2VA first-frame image")
        command.add_argument("--last-frame", help="FL2VA last-frame image; may be used alone")
        command.add_argument("--reference-resize", choices=("legacy", "match"), default="legacy",
                             help="Ref2VA images: legacy 0.258 MP, or match the output canvas area")
        command.add_argument("--resolution", choices=("768p", "576p"),
                             help="Default: 768p for text or keyframes, 576p with Ref2VA images")
        command.add_argument("--duration", type=float, default=15)
        command.add_argument("--seed", type=int)
        command.add_argument("--reference-image", action="append", dest="reference_images",
                             help="Reference image; repeat in picture-number order (1–9 images)")
        if name == "generate":
            command.add_argument("--output")
            command.add_argument("--model-dir")
            command.add_argument("--diagnostics", action="store_true")
            command.add_argument("--timeout", type=float, default=7200)
            command.add_argument("--no-progress", action="store_true", help="Hide the stderr progress bar")
    doctor = commands.add_parser("doctor", help="Check the machine, runtime, media tools and models")
    doctor.add_argument("--model-dir")
    models = commands.add_parser("models").add_subparsers(dest="model_command", required=True)
    prepare = models.add_parser("prepare", help="Prepare a verified local model bundle")
    prepare.add_argument("--checkpoint", help="Existing converted T2VA, FL2VA or Ref2VA VSA checkpoint")
    prepare.add_argument("--components", help="Existing text encoder, tokenizer and VAEs")
    prepare.add_argument("--ref2va-native", help="Native Ref2VA processor, tokenizer, text encoder and image VAE; use with a converted Ref2VA checkpoint")
    prepare.add_argument("--fl2va-native", help="Native FL2VA processor, tokenizer, text encoder and image VAE; use with a converted FL2VA v1.2 checkpoint")
    prepare.add_argument("--model-dir")
    prepare.add_argument("--cache-dir", help="Reusable source files; defaults beside the model bundle")
    prepare.add_argument("--reuse-dir", action="append", default=[], dest="reuse_dirs",
                         help="Search an existing source snapshot or FL2VA directory; repeat as needed")
    prepare.add_argument("--plan", action="store_true", help="Show download and disk requirements without downloading")
    prepare.add_argument("--allow-large-download", action="store_true",
                         help="Explicitly confirm the displayed downloads when they exceed 20 GB")
    for name in ("status", "verify"):
        command = models.add_parser(name)
        command.add_argument("--model-dir")
    return top


def main(argv=None):
    args = vars(parser().parse_args(argv))
    command = args.pop("command")
    try:
        if command == "resolve":
            result = resolve(**args).to_dict()
        elif command == "generate":
            from .progress import ProgressBar
            with ProgressBar(enabled=not args.pop("no_progress")) as display:
                result = asdict(generate(**args, on_progress=display))
        elif command == "doctor":
            from .host import doctor
            result = doctor(**args)
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
            return 0 if result["ready"] else 1
        else:
            from .assets import import_assets, load_assets
            name = args.pop("model_command")
            directory = args.pop("model_dir")
            if name == "prepare":
                checkpoint, components = args.pop("checkpoint"), args.pop("components")
                native = args.pop("ref2va_native")
                fl_native = args.pop("fl2va_native")
                if native and fl_native:
                    raise ValueError("Choose only one native conditioned model task.")
                if bool(checkpoint) != bool(components):
                    raise ValueError("Provide both --checkpoint and --components to import converted assets.")
                if (native or fl_native) and not checkpoint:
                    raise ValueError("--ref2va-native / --fl2va-native requires --checkpoint and --components.")
                show_plan = args.pop("plan")
                if checkpoint:
                    if show_plan or args["cache_dir"] or args["reuse_dirs"] or args["allow_large_download"]:
                        raise ValueError("Source-download options cannot be combined with converted-asset import.")
                    result = import_assets(checkpoint, components, directory, progress=progress,
                                           ref2va_native=native, fl2va_native=fl_native)
                else:
                    from .preparation import plan, prepare
                    if show_plan:
                        args.pop("allow_large_download")
                        result = plan(directory, progress=progress, **args)
                        print(json.dumps(result, indent=2, ensure_ascii=False))
                        return 0
                    result = prepare(directory, progress=progress, **args)
            else:
                result = load_assets(directory, verify=name == "verify")
            result = {key: result[key] for key in ("directory", "identity", "checkpoint", "components")}
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0
    except KeyboardInterrupt:
        print("Generation cancelled.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError) as error:
        print(f"h3: {error}", file=sys.stderr)
        return 1
