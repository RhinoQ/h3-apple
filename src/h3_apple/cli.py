"""Small commands for preparing H3 and generating videos from images."""

import argparse
from dataclasses import asdict
import json
import sys

from .api import generate, resolve


def progress(event):
    if event.get("phase") == "model_plan":
        line = (f"Download: {event['download_bytes'] / 10**9:.2f} GB; "
                f"additional disk required: {event['additional_disk_bytes'] / 10**9:.2f} GB")
    else:
        line = event.get("message") or event.get("phase", "preparing").replace("_", " ").capitalize()
        if event.get("file"):
            line += ": " + event["file"]
    print(line, file=sys.stderr, flush=True)


def parser():
    from . import __version__
    top = argparse.ArgumentParser(prog="h3", description="Turn reference images and a prompt into video with stereo audio.")
    top.add_argument("--version", action="version", version=f"h3-apple {__version__}")
    commands = top.add_subparsers(dest="command", required=True)
    for name in ("generate", "resolve"):
        command = commands.add_parser(name, help="Generate a video" if name == "generate" else "Check inputs without generating")
        prompts = command.add_mutually_exclusive_group(required=True)
        prompts.add_argument("--prompt")
        prompts.add_argument("--prompt-file")
        command.add_argument("--image", action="append", required=True, dest="reference_images",
                             help="Reference image; repeat in picture-number order (1–9)")
        command.add_argument("--duration", type=float, default=15, help="5–15 seconds (default: 15)")
        command.add_argument("--resolution", choices=("576p", "768p"), default="576p")
        command.add_argument("--aspect-ratio", choices=("16:9", "9:16"), default="16:9")
        command.add_argument("--seed", type=int)
        if name == "generate":
            command.add_argument("--output", help="New .mp4 path (default: unique folder in runs/)")
            command.add_argument("--model-dir")
            command.add_argument("--diagnostics", action="store_true", help="Keep working files for debugging")
            command.add_argument("--timeout", type=float, default=7200)
            command.add_argument("--no-progress", action="store_true")
    prepare = commands.add_parser("prepare", help="Download or reuse models and prepare H3 once")
    prepare.add_argument("--model-dir")
    prepare.add_argument("--reuse-dir", action="append", default=[], dest="reuse_dirs",
                         help="Reuse a source snapshot or an existing H3 model installation")
    prepare.add_argument("--plan", action="store_true", help="Check download and disk requirements only")
    prepare.add_argument("--allow-large-download", action="store_true", help="Confirm downloads exceeding 20 GB")
    for name in ("doctor", "verify"):
        commands.add_parser(name, help="Check installation" if name == "doctor" else "Verify all model checksums").add_argument("--model-dir")
    return top


def main(argv=None):
    args = vars(parser().parse_args(argv))
    command = args.pop("command")
    try:
        if command == "generate":
            from .progress import ProgressBar
            with ProgressBar(enabled=not args.pop("no_progress")) as display:
                result = asdict(generate(**args, on_progress=display))
        elif command == "resolve":
            result = resolve(**args).to_dict()
        elif command == "doctor":
            from .host import doctor
            result = doctor(**args)
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["ready"] else 1
        elif command == "verify":
            from .assets import load_assets
            data = load_assets(args["model_dir"], verify=True)
            result = dict(status="verified", directory=data["directory"], identity=data["identity"])
        else:
            from .preparation import plan, prepare, LIMIT
            show_plan = args.pop("plan")
            allowed = args.pop("allow_large_download")
            spec = plan(**args, progress=progress)
            progress(dict(spec, phase="model_plan"))
            if show_plan:
                result = {k: v for k, v in spec.items() if k not in ("groups", "prepared")}
            else:
                if spec["download_bytes"] > LIMIT and not allowed and sys.stdin.isatty():
                    allowed = input("Download these model files? [y/N] ").strip().lower() in ("y", "yes")
                data = prepare(spec, allow_large_download=allowed, progress=progress)
                result = dict(status="ready", directory=data["directory"], identity=data["identity"])
        print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0
    except KeyboardInterrupt:
        print("Cancelled. Working files were preserved.", file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"h3: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
