"""Dependency and binary checks for the MLX generation and X2 runtime."""
import ctypes
import importlib.metadata
from pathlib import Path
import sys
from ..io import digest


def check_dependencies():
    if sys.version_info[:2] != (3, 11):
        raise RuntimeError("The MLX runtime requires Python 3.11; install h3-apple in a Python 3.11 Conda environment.")
    expected = {"mlx": "0.32.0", "mlx-metal": "0.32.0", "numpy": "2.4.6",
                "transformers": "5.14.1", "torch": "2.11.0", "torchvision": "0.26.0"}
    for name, version in expected.items():
        try:
            actual = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            actual = None
        if actual != version:
            raise RuntimeError(f"The MLX runtime requires {name}=={version}; install h3-apple in this Conda environment.")


def backend_identity():
    check_dependencies()
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
        raise RuntimeError("The loaded MLX backend differs from the pinned macOS 26 wheel. Reinstall h3-apple in a Python 3.11 Conda environment.")
    return dict(device=mx.device_info(), libmlx_sha256=checksum,
                metallib_sha256=digest(lib.parent / "mlx.metallib"),
                versions={n: importlib.metadata.version(n) for n in
                          ("mlx", "mlx-metal", "numpy", "transformers")})

