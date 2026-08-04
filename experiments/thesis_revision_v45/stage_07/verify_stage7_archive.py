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

from _common import ARCHIVE, MANIFESTS, Registry, TERMINAL_SUCCESS, _atomic_write  # noqa: E402


def verify_all() -> dict:
    reg = [r for r in Registry().read() if r["run_status"] in TERMINAL_SUCCESS]
    ok, bad, missing, lines = 0, [], [], []
    for r in reg:
        x = ARCHIVE / f"{r['run_id']}.json.xz"
        if not x.exists():
            missing.append(r["run_id"])
            continue
        h = hashlib.sha256()
        d = lzma.LZMADecompressor()
        with open(x, "rb") as fh:
            for block in iter(lambda: fh.read(1 << 20), b""):
                h.update(d.decompress(block))
        if h.hexdigest() == r["result_sha256"]:
            ok += 1
            lines.append(f"{hashlib.sha256(x.read_bytes()).hexdigest()}  "
                         f"{x.relative_to(ARCHIVE.parents[3])}")
        else:
            bad.append(r["run_id"])
    if lines:
        _atomic_write(MANIFESTS / "stage07_archive.sha256", "\n".join(sorted(lines)) + "\n")
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
