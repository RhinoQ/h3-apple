"""macOS device coordination and resource checks without a monitoring service."""

from contextlib import contextmanager
import ctypes
import fcntl
import importlib.metadata
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess

from .io import digest
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


def check_machine(info):
    if info["system"] != "Darwin" or info["machine"] != "arm64":
        raise RuntimeError("Ours requires an Apple Silicon Mac.")
    if "M5" not in info["chip"]:
        raise RuntimeError("This Ours version requires M5 GPU kernels; other chips are not validated.")
    if tuple(map(int, info["macos"].split(".")[:2])) < (26, 2):
        raise RuntimeError("The fixed MLX Metal build requires macOS 26.2 or later.")
    if info["memory_bytes"] < 96 * 1024**3:
        raise RuntimeError("This Ours preset requires at least 96 GiB unified memory; tested on 128 GiB.")


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


def backend_identity():
    import mlx.core as mx
    dist = importlib.metadata.distribution("mlx-metal")
    lib = Path(dist.locate_file("mlx/lib/libmlx.dylib")).resolve()
    dyld = ctypes.CDLL(None)
    count = dyld._dyld_image_count
    count.restype = ctypes.c_uint32
    name = dyld._dyld_get_image_name
    name.argtypes = [ctypes.c_uint32]
    name.restype = ctypes.c_char_p
    loaded = [Path(name(i).decode()).resolve() for i in range(count())]
    checksum = digest(lib)
    if lib not in loaded or checksum != "1876795e05b3434925e745fbf6e9f0c8c0446b666224c9d881609ab353e94e51":
        raise RuntimeError("The loaded MLX backend differs from the pinned macOS 26 wheel. Run ./install.sh.")
    return dict(device=mx.device_info(), libmlx_sha256=checksum,
                metallib_sha256=digest(lib.parent / "mlx.metallib"),
                versions={n: importlib.metadata.version(n) for n in
                          ("mlx", "mlx-metal", "numpy", "transformers")})


def doctor(model_dir=None):
    info = snapshot()
    errors = []
    try:
        check_machine(info)
        os.environ["MLX_ENABLE_TF32"] = "0"
        os.environ["MLX_METAL_GPU_ARCH"] = ""
        info["backend"] = backend_identity()
    except Exception as error:
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
    except (OSError, ValueError) as error:
        errors.append(str(error))
    info["free_disk_bytes"] = shutil.disk_usage(Path.cwd()).free
    info["errors"] = errors
    info["ready"] = not errors
    return info
