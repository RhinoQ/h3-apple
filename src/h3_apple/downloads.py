"""Resumable downloads checked against immutable sizes and SHA256 hashes."""

import os
from pathlib import Path
from urllib.request import Request, urlopen
from .io import digest


def partial_path(destination, checksum):
    return destination.with_name(destination.name + "." + checksum + ".partial")


def download(url, destination, expected_size, checksum):
    """Resume an immutable HTTPS source, verify it, then atomically publish the file."""
    destination = Path(destination)
    destination.parent.mkdir(parents=True, exist_ok=True)
    part = partial_path(destination, checksum)
    offset = part.stat().st_size if part.exists() else 0
    if offset > expected_size:
        raise ValueError(f"Oversized partial download: {part}")
    if offset < expected_size:
        headers = {"Accept-Encoding": "identity"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        with urlopen(Request(url, headers=headers), timeout=60) as response:
            if offset and (response.status != 206 or not response.headers.get("Content-Range", "").startswith(f"bytes {offset}-")):
                raise ValueError(f"Server did not honor download resume. Move {part} aside and review a new full-download plan.")
            with part.open("ab" if part.exists() else "xb") as stream:
                count = offset
                while chunk := response.read(min(4 * 1024**2, expected_size - count + 1)):
                    if count + len(chunk) > expected_size:
                        raise ValueError("Download exceeds the pinned source size.")
                    stream.write(chunk)
                    count += len(chunk)
                stream.flush()
                os.fsync(stream.fileno())
    if part.stat().st_size != expected_size or digest(part) != checksum:
        raise ValueError(f"Incomplete or corrupt download; retained at {part}")
    if destination.exists():
        if digest(destination) != checksum:
            raise FileExistsError(f"Different cached model already exists: {destination}")
        part.unlink()
    else:
        os.link(part, destination)
        part.unlink()
    return destination

