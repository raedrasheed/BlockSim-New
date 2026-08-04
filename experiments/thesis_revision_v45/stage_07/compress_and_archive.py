#!/usr/bin/env python3
"""Stage 7 — streaming compression, verified round-trip, and temporary-raw reclamation.

Compression is STREAMING by measurement, not by API name: xz -9 allocates a fixed ~706 MB
match-finder dictionary, so peak memory is a large constant that does NOT grow with payload.
That constant is a per-compressing-process scheduling input and enters the memory equation.

The raw file is deleted ONLY after the compressed copy has been decompressed and its digest
compared against the original.
"""
from __future__ import annotations

import argparse
import hashlib
import lzma
import pathlib

CHUNK = 1 << 20
PRESET = 9


def compress(raw: pathlib.Path, dest: pathlib.Path) -> dict:
    dest.parent.mkdir(parents=True, exist_ok=True)
    h_raw = hashlib.sha256()
    comp = lzma.LZMACompressor(preset=PRESET)
    with open(raw, "rb") as src, open(dest, "wb") as out:
        for block in iter(lambda: src.read(CHUNK), b""):
            h_raw.update(block)
            piece = comp.compress(block)
            if piece:
                out.write(piece)
        out.write(comp.flush())
    return {"raw_sha256": h_raw.hexdigest(), "raw_bytes": raw.stat().st_size,
            "compressed_bytes": dest.stat().st_size,
            "ratio": raw.stat().st_size / max(1, dest.stat().st_size),
            "compressed_sha256": hashlib.sha256(dest.read_bytes()).hexdigest()}


def verify(dest: pathlib.Path, expect_raw_sha: str) -> bool:
    """Decompress in a streaming fashion and compare the digest.  No full copy is held."""
    h = hashlib.sha256()
    d = lzma.LZMADecompressor()
    with open(dest, "rb") as fh:
        for block in iter(lambda: fh.read(CHUNK), b""):
            h.update(d.decompress(block))
    return h.hexdigest() == expect_raw_sha


def compress_verify_reclaim(raw: pathlib.Path, dest: pathlib.Path,
                            reclaim: bool = True) -> dict:
    info = compress(raw, dest)
    info["verified"] = verify(dest, info["raw_sha256"])
    if not info["verified"]:
        dest.unlink(missing_ok=True)
        raise RuntimeError(f"compressed round-trip FAILED for {raw}; raw retained")
    if reclaim:
        raw.unlink()
        info["raw_reclaimed"] = True
    return info


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("raw")
    ap.add_argument("dest")
    ap.add_argument("--keep-raw", action="store_true")
    a = ap.parse_args(argv)
    i = compress_verify_reclaim(pathlib.Path(a.raw), pathlib.Path(a.dest), not a.keep_raw)
    print(f"{i['raw_bytes']:,} -> {i['compressed_bytes']:,} bytes ({i['ratio']:.1f}x), "
          f"verified={i['verified']}, raw_reclaimed={i.get('raw_reclaimed', False)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
