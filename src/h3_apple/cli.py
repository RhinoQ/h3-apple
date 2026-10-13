"""Small commands for preparing H3 and generating videos from images."""

import argparse
from dataclasses import asdict
import json
import sys

from .api import DownloadApprovalRequired, generate, resolve


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
        command.add_argument("--quality", choices=("fast", "medium", "high"),
                             help="fast: SOL 544p + X2 (default); medium: VSA 768p; high: Dense 768p + VOSR (128 GiB)")
        command.add_argument("--duration", type=float, default=5,
                             help="Any 5–15 seconds aligned to a frame at 24 fps, e.g. 7 or 8.5 (default: 5)")
        command.add_argument("--aspect-ratio", choices=("16:9", "9:16"), default="16:9")
        advanced = command.add_argument_group("Advanced settings")
        advanced.add_argument("--resolution", choices=("544p", "576p", "768p"),
                             help="Sampling size (automatic with --quality; otherwise 544p, or 768p with --upscale)")
        advanced.add_argument("--x2", action=argparse.BooleanOptionalAction,
                             default=None,
                             help="Double decoded dimensions (automatic with --quality; otherwise on, or off with --upscale)")
        advanced.add_argument("--seed", type=int)
        advanced.add_argument("--mode", choices=("SOL", "VSA"),
                             help="Generation mode (automatic with --quality; otherwise SOL)")
        advanced.add_argument("--attention", choices=("vsa", "dense"),
                             help="Attention for VSA models (default: vsa; dense requires native 768p and 128 GiB)")
        advanced.add_argument("--upscale", action=argparse.BooleanOptionalAction, default=None,
                             help="Restore native video 2x with VOSR (automatic with --quality high; 128 GiB)")
        if name == "generate":
            command.add_argument("--output", help="New .mp4 path (default: unique folder in runs/)")
            advanced.add_argument("--model-dir")
            advanced.add_argument("--x2-model-dir", help="Optional X2 model directory (separate from generation models)")
            advanced.add_argument("--upscale-model-dir", help="Optional restoration model directory; requires --upscale")
            advanced.add_argument("--diagnostics", action="store_true", help="Keep working files for debugging")
            advanced.add_argument("--timeout", type=float, default=7200, help="Generation timeout in seconds")
            advanced.add_argument("--upscale-timeout", type=float, default=14400, help="Restoration timeout in seconds")
            advanced.add_argument("--no-progress", action="store_true")
            advanced.add_argument("--json", action="store_true", help="Print result JSON (automatic when stdout is redirected)")
            advanced.add_argument("--allow-large-download", action="store_true",
                                 help="Confirm first-run model downloads exceeding 20 GB")
    prepare = commands.add_parser("prepare", help="Download or reuse models and prepare H3 once")
    prepare.add_argument("--model-dir")
    prepare.add_argument("--mode", choices=("SOL", "VSA"), default="SOL")
    prepare.add_argument("--reuse-dir", action="append", default=[], dest="reuse_dirs",
                         help="Reuse a source snapshot or an existing H3 model installation")
    prepare.add_argument("--plan", action="store_true", help="Check download and disk requirements only")
    prepare.add_argument("--allow-large-download", action="store_true", help="Confirm downloads exceeding 20 GB")
    for name in ("doctor", "verify"):
        command = commands.add_parser(name, help="Check installation" if name == "doctor" else "Verify all model checksums")
        command.add_argument("--model-dir")
        command.add_argument("--mode", choices=("SOL", "VSA"), default="SOL")
    prepare_x2 = commands.add_parser("prepare-x2", help="Prepare the 5.25 GB X2 decoder")
    prepare_x2.add_argument("--model-dir")
    prepare_x2.add_argument("--reuse-dir", action="append", default=[], dest="reuse_dirs")
    prepare_x2.add_argument("--plan", action="store_true")
    upscale = commands.add_parser("upscale", help="Double H3 video dimensions with VOSR2, including X2 output")
    upscale.add_argument("--input", required=True)
    upscale.add_argument("--output", help="New .mp4 path (default: unique folder in runs/)")
    upscale.add_argument("--duration", type=float, help="Upscale only the first N seconds")
    upscale.add_argument("--model-dir")
    upscale.add_argument("--diagnostics", action="store_true")
    upscale.add_argument("--timeout", type=float, default=14400)
    upscale.add_argument("--no-progress", action="store_true")
    upscale.add_argument("--json", action="store_true", help="Print result JSON (automatic when stdout is redirected)")
    prepare_vosr = commands.add_parser("prepare-vosr", help="Prepare the 6.97 GB VOSR2 models")
    prepare_vosr.add_argument("--model-dir")
    prepare_vosr.add_argument("--reuse-dir", action="append", default=[], dest="reuse_dirs")
    prepare_vosr.add_argument("--plan", action="store_true")
    return top


def main(argv=None):
    args = vars(parser().parse_args(argv))
    command = args.pop("command")
    json_output = args.pop("json", False)
    try:
        if command == "upscale":
            from .upscale import upscale
            from .progress import ProgressBar
            with ProgressBar(enabled=not args.pop("no_progress")) as display:
                result = asdict(upscale(**args, on_progress=display))
        elif command == "generate":
            from .progress import ProgressBar
            with ProgressBar(enabled=not args.pop("no_progress")) as display:
                try:
                    result = asdict(generate(**args, on_progress=display))
                except DownloadApprovalRequired as error:
                    if not sys.stdin.isatty():
                        raise
                    print(f"\n{error}", file=sys.stderr)
                    print("Download these model files? [y/N] ", end="", file=sys.stderr, flush=True)
                    if sys.stdin.readline().strip().lower() not in ("y", "yes"):
                        raise RuntimeError("Model download cancelled. No model files were downloaded.") from None
                    args["allow_large_download"] = True
                    result = asdict(generate(**args, on_progress=display))
        elif command == "resolve":
            result = resolve(**args).to_dict()
        elif command == "doctor":
            from .host import doctor
            result = doctor(**args)
            print(json.dumps(result, indent=2, default=str))
            return 0 if result["ready"] else 1
        elif command == "verify":
            if args["mode"] == "VSA":
                from .vsa_assets import load_assets
            else:
                from .assets import load_assets
            data = load_assets(args["model_dir"], verify=True)
            result = dict(status="verified", directory=data["directory"], identity=data["identity"])
        elif command == "prepare-x2":
            from .x2_assets import plan, prepare
            show_plan = args.pop("plan")
            result = plan(**args) if show_plan else prepare(**args, on_progress=progress)
        elif command == "prepare-vosr":
            from .super_resolution.assets import plan, prepare
            show_plan = args.pop("plan")
            result = plan(**args) if show_plan else prepare(**args, on_progress=progress)
        else:
            if args.pop("mode") == "VSA":
                from .vsa_preparation import plan, prepare, LIMIT
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
        if command in ("generate", "upscale") and sys.stdout.isatty() and not json_output:
            print(f"Saved video: {result['video_path']}")
            if result.get("native_video_path"):
                print(f"Native video: {result['native_video_path']}")
        else:
            print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
        return 0
    except KeyboardInterrupt as error:
        print("Cancelled. Working files were preserved.", file=sys.stderr)
        if str(error):
            print(str(error), file=sys.stderr)
        return 130
    except (OSError, ValueError, RuntimeError, TimeoutError) as error:
        print(f"h3: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
