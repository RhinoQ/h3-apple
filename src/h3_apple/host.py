"""macOS device coordination and resource checks without a monitoring service."""

from contextlib import contextmanager
import ctypes
import fcntl
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

from .media import tool


def command(*args):
    return subprocess.check_output(args, text=True, timeout=10).strip()


def thermal_status():
    """Read NSProcessInfo directly; no helper binary or PyObjC dependency."""
    ctypes.CDLL("/System/Library/Frameworks/Foundation.framework/Foundation")
    objc = ctypes.CDLL("/usr/lib/libobjc.A.dylib")
    objc.objc_getClass.argtypes = [ctypes.c_char_p]
    objc.objc_getClass.restype = ctypes.c_void_p
    objc.sel_registerName.argtypes = [ctypes.c_char_p]
    objc.sel_registerName.restype = ctypes.c_void_p
    pointer_call = ctypes.CFUNCTYPE(ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)(
        ("objc_msgSend", objc))
    integer_call = ctypes.CFUNCTYPE(ctypes.c_long, ctypes.c_void_p, ctypes.c_void_p)(
        ("objc_msgSend", objc))
    process = pointer_call(objc.objc_getClass(b"NSProcessInfo"), objc.sel_registerName(b"processInfo"))
    state = integer_call(process, objc.sel_registerName(b"thermalState"))
    low_power = integer_call(process, objc.sel_registerName(b"isLowPowerModeEnabled"))
    return dict(state={0: "nominal", 1: "fair", 2: "serious", 3: "critical"}.get(state, "unknown"),
                low_power_mode=bool(low_power))


def snapshot():
    if platform.system() != "Darwin":
        return {"system": platform.system(), "machine": platform.machine(), "swap_bytes": None}
    swap = command("/usr/sbin/sysctl", "-n", "vm.swapusage")
    match = re.search(r"used\s*=\s*([0-9.]+)M", swap)
    if match is None:
        raise RuntimeError("Cannot read macOS swap usage.")
    return dict(system="Darwin", machine=platform.machine(), macos=platform.mac_ver()[0],
                chip=command("/usr/sbin/sysctl", "-n", "machdep.cpu.brand_string"),
                memory_bytes=int(command("/usr/sbin/sysctl", "-n", "hw.memsize")),
                swap_bytes=int(float(match[1]) * 1024**2),
                power=command("/usr/bin/pmset", "-g", "batt"), thermal=thermal_status())


def check_machine(info, request=None):
    if info["system"] != "Darwin" or info["machine"] != "arm64":
        raise RuntimeError("H3 Apple requires an Apple Silicon Mac.")
    if "M5" not in info["chip"]:
        raise RuntimeError("This H3 Apple version requires M5 GPU kernels; other chips are not validated.")
    if tuple(map(int, info["macos"].split(".")[:2])) < (26, 2):
        raise RuntimeError("The H3 engine requires macOS 26.2 or later.")
    if info["memory_bytes"] < 64 * 1024**3:
        raise RuntimeError("H3 Apple requires at least 64 GiB unified memory.")
    if (request is not None and request["resolution"] == "768p"
            and request["duration"] > 5 and info["memory_bytes"] < 96 * 1024**3):
        raise RuntimeError("768p videos longer than 5 seconds require at least 96 GiB unified memory. "
                           "On a 64 GiB Mac, use --duration 5 or --resolution 576p.")


@contextmanager
def device_lock(path=None):
    path = Path(path or os.environ.get("H3_DEVICE_LOCK", Path.home() /
                                     ".cache/h3-apple/device.lock"))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+") as stream:
        try:
            fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError("Another H3 job holds the device lock; wait for it to finish.") from error
        try:
            yield
        finally:
            fcntl.flock(stream, fcntl.LOCK_UN)


def doctor(model_dir=None):
    info = snapshot()
    errors = []
    try:
        check_machine(info)
    except RuntimeError as error:
        errors.append(str(error))
    for name in ("ffmpeg", "ffprobe"):
        try:
            info[name] = tool(name)
        except RuntimeError as error:
            errors.append(str(error))
    from .assets import load_assets
    try:
        assets = load_assets(model_dir)
        info["models"] = {k: assets[k] for k in ("directory", "identity")}
        info["engine"] = {k: assets[k] for k in ("binary", "library", "tested_interface_commit")}
    except (OSError, ValueError, RuntimeError) as error:
        errors.append(str(error))
    info["free_disk_bytes"] = shutil.disk_usage(Path.cwd()).free
    info["errors"] = errors
    info["ready"] = not errors
    return info
