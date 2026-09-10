"""Private process entry point. Receives one request, emits progress and a result."""

import hashlib
import json
import logging
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import traceback

from .host import backend_identity, check_machine, device_lock, snapshot
from .io import digest
from .media import validate


class ResourceStop(BaseException):
    pass


def emit(value):
    print(json.dumps(value, ensure_ascii=False, allow_nan=False), flush=True)


def source_identity():
    root = Path(__file__).parent
    hashes = {str(path.relative_to(root)): digest(path) for path in sorted(root.rglob("*"))
              if path.is_file() and path.suffix in (".py", ".metal", ".npz", ".json", ".txt")}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def main():
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(asctime)s %(levelname)s %(message)s")
    done = threading.Event()
    resource_error = []
    samples = []
    try:
        spec = json.loads(sys.stdin.readline())
        workspace = Path(spec["workspace"])
        with device_lock():
            initial = snapshot()
            check_machine(initial)
            if shutil.disk_usage(workspace).free < 20 * 1024**3:
                raise OSError("Generation requires at least 20 GiB free disk space.")

            def stop(_signum, _frame):
                raise ResourceStop(resource_error[-1] if resource_error else "Resource limit exceeded.")

            def watch():
                while not done.wait(5):
                    try:
                        current = snapshot()
                        samples.append(current)
                        if current["swap_bytes"] - initial["swap_bytes"] > 2 * 1024**3:
                            raise ResourceStop("Swap usage grew by more than 2 GiB.")
                        if current["thermal"]["state"] in ("serious", "critical"):
                            raise ResourceStop("macOS reports serious or critical thermal pressure.")
                        if shutil.disk_usage(workspace).free < 20 * 1024**3:
                            raise ResourceStop("Free disk space fell below 20 GiB.")
                    except BaseException as error:
                        resource_error.append(str(error))
                        os.kill(os.getpid(), signal.SIGUSR1)
                        return

            signal.signal(signal.SIGUSR1, stop)
            threading.Thread(target=watch, daemon=True).start()
            emit({"phase": "loading", "message": "Checking the runtime and preparing generation"})
            backend = backend_identity()
            from .runtime.engine import run
            result = run(spec["request"], spec["assets"], workspace / "output.mp4", emit,
                         workspace / "diagnostics" if spec["diagnostics"] else None)
            emit({"phase": "validating"})
            media = validate(workspace / "output.mp4", spec["request"])
            result.update(backend=backend, initial_host=initial, final_host=snapshot(),
                          resource_samples=samples, media=media,
                          video_sha256=digest(workspace / "output.mp4"),
                          package_source_sha256=source_identity())
            emit({"kind": "result", "result": result})
        return 0
    except BaseException as error:
        traceback.print_exc(file=sys.stderr)
        emit({"kind": "error", "error": str(error) or type(error).__name__})
        return 1
    finally:
        done.set()


if __name__ == "__main__":
    raise SystemExit(main())
