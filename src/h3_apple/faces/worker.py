"""Isolated optional-restoration process, sharing H3's single-device lock."""

import json
import os
from pathlib import Path
import shutil
import signal
import sys
import threading
import traceback

from ..host import check_machine, device_lock, snapshot
from ..io import source_identity
from ..worker import emit, ResourceStop


def main():
    done = threading.Event()
    errors, samples = [], []
    try:
        spec = json.loads(sys.stdin.readline())
        workspace = Path(spec["workspace"])
        with device_lock():
            initial = snapshot()
            check_machine(initial)
            def check(current):
                if current["swap_bytes"] - initial["swap_bytes"] > 2 * 1024**3:
                    raise ResourceStop("Swap usage grew by more than 2 GiB.")
                if current["thermal"]["state"] in ("serious", "critical"):
                    raise ResourceStop("macOS reports serious or critical thermal pressure.")
                if "AC Power" not in current["power"] or current["thermal"]["low_power_mode"]:
                    raise ResourceStop("Connect AC power and disable Low Power Mode for face enhancement.")
                if shutil.disk_usage(workspace).free < 20 * 1024**3:
                    raise ResourceStop("Face enhancement requires at least 20 GiB free disk space.")
            check(initial)
            def stop(_signal, _frame):
                raise ResourceStop(errors[-1] if errors else "Resource limit exceeded.")
            def watch():
                while not done.wait(5):
                    try:
                        current = snapshot()
                        samples.append(current)
                        check(current)
                    except BaseException as error:
                        errors.append(str(error))
                        os.kill(os.getpid(), signal.SIGUSR1)
                        return
            signal.signal(signal.SIGUSR1, stop)
            thread = threading.Thread(target=watch, daemon=True)
            thread.start()
            from .assets import verify, manifest
            emit(dict(phase="face_models", message="Verifying local face model checksums"))
            root = verify(spec["model_dir"])
            from .pipeline import run
            result = run(workspace, root, emit, spec["diagnostics"])
            result.update(initial_host=initial, final_host=snapshot(), resource_samples=samples,
                          package_source_sha256=source_identity(), model_identity=manifest())
            emit(dict(kind="result", result=result))
        return 0
    except BaseException as error:
        traceback.print_exc(file=sys.stderr)
        emit(dict(kind="error", error=str(error) or type(error).__name__))
        return 1
    finally:
        done.set()


if __name__ == "__main__":
    raise SystemExit(main())
