"""Stage 5B1 run utilities: atomic writes, run status, isolated output paths."""

from __future__ import annotations
import os
import json
import tempfile
import hashlib

STATUS_PLANNED = "PLANNED"
STATUS_RUNNING = "RUNNING"
STATUS_COMPLETED = "COMPLETED"
STATUS_FAILED = "FAILED"


def atomic_write_json(path: str, obj) -> str:
    """Write JSON atomically (temp file + os.replace) so partial writes are never
    observed as completed output."""
    d = os.path.dirname(path) or "."
    os.makedirs(d, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=d, suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(obj, f, indent=2, default=str, sort_keys=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)          # atomic on POSIX
    finally:
        if os.path.exists(tmp):
            os.remove(tmp)
    return path


def is_complete(manifest: dict) -> bool:
    return manifest.get("status") == STATUS_COMPLETED


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for c in iter(lambda: f.read(1 << 16), b""):
            h.update(c)
    return h.hexdigest()
