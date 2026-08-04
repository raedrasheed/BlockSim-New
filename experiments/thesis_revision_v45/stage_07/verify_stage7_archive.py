#!/usr/bin/env python3
"""Stage 7 — verify the durable archive: every compressed result decompresses to its digest.

Verification is a round-trip, not a filename check: each archive member is decompressed in a
streaming fashion and its SHA-256 compared against the digest the registry recorded at the
moment the run completed.
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
import pathlib

from _common import ExecutionPaths, Registry, TERMINAL_SUCCESS, _atomic_write      # noqa: E402


def verify_all(paths=None) -> dict:
    paths = paths or ExecutionPaths()
    reg = [r for r in Registry(paths.registry).read()
           if r["run_status"] in TERMINAL_SUCCESS]
    # one archive member per PHYSICAL execution; alias rows share it by design
    seen = set()
    ok, bad, missing, lines = 0, [], [], []
    for r in reg:
        pid = r.get("physical_execution_id") or r["run_id"]
        if pid in seen:
            ok += 1
            continue
        seen.add(pid)
        x = paths.archive / f"{pid}.json.xz"
        if not x.exists():
            missing.append(pid)
            continue
        h = hashlib.sha256()
        d = lzma.LZMADecompressor()
        with open(x, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(d.decompress(block))
        if h.hexdigest() == (r.get("raw_sha256") or r.get("result_sha256")):
            ok += 1
            lines.append(f"{hashlib.sha256(x.read_bytes()).hexdigest()}  {x.name}")
        else:
            bad.append(pid)
    if lines:
        _atomic_write(paths.manifests / "stage07_archive.sha256",
                      "\n".join(sorted(lines)) + "\n")
    return {"verified": ok, "digest_mismatch": bad, "missing": missing,
            "expected": len(reg)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.parse_args(argv)
    r = verify_all()
    print(f"archive: {r['verified']} of {r['expected']} verified by round-trip; "
          f"{len(r['digest_mismatch'])} digest mismatches; {len(r['missing'])} missing")
    return 0 if not r["digest_mismatch"] and not r["missing"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
