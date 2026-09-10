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
    else:
        line = phase.replace("_", " ").capitalize()
    print(line, file=sys.stderr, flush=True)


def parser():
    top = argparse.ArgumentParser(prog="h3", description="Generate MiniMax-H3 video with stereo audio on Apple Silicon.")
    top.add_argument("--version", action="version", version="h3-apple 0.1.0.dev0")
    commands = top.add_subparsers(dest="command", required=True)
    for name in ("generate", "resolve"):
        command = commands.add_parser(name)
        prompts = command.add_mutually_exclusive_group(required=True)
        prompts.add_argument("--prompt")
        prompts.add_argument("--prompt-file")
        command.add_argument("--preset", default="ours")
        command.add_argument("--resolution", default="768p", choices=("768p", "576p"))
        command.add_argument("--duration", type=float, default=15)
        command.add_argument("--seed", type=int)
        if name == "generate":
            command.add_argument("--output")
            command.add_argument("--model-dir")
            command.add_argument("--diagnostics", action="store_true")
            command.add_argument("--timeout", type=float, default=7200)
    doctor = commands.add_parser("doctor", help="Check the machine, runtime, media tools and models")
    doctor.add_argument("--model-dir")
    models = commands.add_parser("models").add_subparsers(dest="model_command", required=True)
    prepare = models.add_parser("prepare", help="Prepare a verified local model bundle")
    prepare.add_argument("--checkpoint", required=True, help="Existing converted FastH3 VSA checkpoint")
    prepare.add_argument("--components", required=True, help="Existing text encoder, tokenizer and VAEs")
    prepare.add_argument("--model-dir")
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
            result = asdict(generate(**args, on_progress=progress))
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
                result = import_assets(directory=directory, progress=progress, **args)
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
