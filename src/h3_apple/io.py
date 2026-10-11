"""Small file helpers shared by the command and worker."""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import uuid


def automatic_output(filename="output.mp4"):
    """Choose a fresh run directory without creating it or reserving files."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return Path.cwd() / "runs" / f"{stamp}-{uuid.uuid4().hex[:8]}" / filename


def digest(path):
    checksum = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(8 * 1024**2), b""):
            checksum.update(chunk)
    return checksum.hexdigest()


def source_identity():
    """Bind replay to the installed wrapper and its packaged policy data."""
    root = Path(__file__).parent
    hashes = {str(path.relative_to(root)): digest(path) for path in sorted(root.rglob("*"))
              if path.is_file() and path.suffix in (".py", ".metal", ".npz", ".json", ".txt")}
    return hashlib.sha256(json.dumps(hashes, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    path = Path(path)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w") as stream:
            json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
