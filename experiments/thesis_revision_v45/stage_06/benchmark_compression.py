#!/usr/bin/env python3
"""Stage 6 — compression benchmark for the Stage-7 archive path (FEASIBILITY ONLY).

The archive plan claims a compression ratio and a streaming write path.  Both are claims about
cost, so both are measured here rather than assumed:

    * ratio for gzip -9 and xz -9
    * compression wall-clock time and CPU time
    * compression PEAK MEMORY, measured with tracemalloc around the compressor only
    * whether the path is TRULY STREAMING — i.e. whether peak memory stays bounded as payload
      size grows, rather than scaling with it
    * temporary disk requirement of the streaming path

"Streaming" is not asserted from the API name, and it is NOT decided by comparing peak memory
against the payload size.  That first criterion was wrong: xz -9 allocates a fixed ~64 MiB
match-finder dictionary, so its peak is a large CONSTANT unrelated to buffering, and at a small
payload it would report "not streaming" for a path that buffers nothing.  The property that
actually matters is whether peak memory GROWS with payload size, so it is measured at several
payload sizes and the slope d(peak)/d(payload) is taken.  The fixed encoder cost is reported
separately because it is a per-process scheduling input, not a defect.

    python experiments/thesis_revision_v45/stage_06/benchmark_compression.py \
        --horizon 1200 --out pilot/compression_benchmark.json

Writes a JSON record.  It executes a PILOT seed only and produces no confirmatory output.
"""
from __future__ import annotations

import argparse
import gzip
import json
import lzma
import os
import pathlib
import resource
import sys
import tempfile
import time
import tracemalloc

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                                  # noqa: E402
from generate_seed_registry import build_rows                          # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation               # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                 # noqa: E402

CHUNK = 1 << 20          # 1 MiB streaming chunk


def peak_rss_kb() -> int:
    return resource.getrusage(resource.RUSAGE_SELF).ru_maxrss


def cpu_now() -> float:
    r = resource.getrusage(resource.RUSAGE_SELF)
    return r.ru_utime + r.ru_stime


def bench_one_shot(name: str, fn, raw: bytes) -> dict:
    tracemalloc.start()
    t0, c0 = time.time(), cpu_now()
    out = fn(raw)
    wall, cpu = time.time() - t0, cpu_now() - c0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"codec": name, "mode": "one_shot", "raw_bytes": len(raw),
            "compressed_bytes": len(out), "ratio": len(raw) / len(out),
            "wall_seconds": wall, "cpu_seconds": cpu,
            "peak_traced_bytes": peak,
            "peak_over_payload": peak / len(raw)}


def bench_streaming_xz(raw: bytes, tmpdir: pathlib.Path) -> dict:
    """Incremental compression straight to a file — the path Stage 7 would actually use."""
    dest = tmpdir / "stream.xz"
    tracemalloc.start()
    t0, c0 = time.time(), cpu_now()
    comp = lzma.LZMACompressor(preset=9)
    written = 0
    with open(dest, "wb") as fh:
        for i in range(0, len(raw), CHUNK):
            block = comp.compress(raw[i:i + CHUNK])
            if block:
                written += fh.write(block)
        tail = comp.flush()
        written += fh.write(tail)
    wall, cpu = time.time() - t0, cpu_now() - c0
    _cur, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    size = dest.stat().st_size
    dest.unlink()
    return {"codec": "xz -9", "mode": "streaming_incremental", "chunk_bytes": CHUNK,
            "raw_bytes": len(raw), "compressed_bytes": size, "ratio": len(raw) / size,
            "wall_seconds": wall, "cpu_seconds": cpu, "bytes_written": written,
            "peak_traced_bytes": peak, "peak_over_payload": peak / len(raw)}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--horizon", type=float, default=1200.0)
    ap.add_argument("--scenario", default="C04")
    ap.add_argument("--seed-index", type=int, default=7)
    ap.add_argument("--out", default=str(HERE / "pilot" / "compression_benchmark.json"))
    args = ap.parse_args(argv)

    S.assert_reference_matches_baseline()
    rows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    seed = [r["master_seed_decimal"] for r in build_rows()
            if r["seed_class"] == "PILOT"][args.seed_index]
    tier = dict(S.TIER2)
    tier["horizon_T"] = args.horizon
    cfg = S.build_config(rows[args.scenario], seed, tier)

    t0 = time.time()
    run = run_simulation(cfg, run_id=f"bench-{args.scenario}-{args.horizon:.0f}")
    res = results_schema(run, cfg)
    raw = json.dumps(res, default=str).encode("utf-8")
    gen_wall = time.time() - t0
    print(f"payload: {args.scenario} @ {args.horizon:.0f}s -> {len(raw):,} bytes "
          f"({len(run.round_terminal_times)} rounds, {gen_wall:.1f}s to generate)", flush=True)

    results = [bench_one_shot("gzip -9", lambda b: gzip.compress(b, 9), raw),
               bench_one_shot("xz -9", lambda b: lzma.compress(b, preset=9), raw)]
    with tempfile.TemporaryDirectory() as td:
        stream = bench_streaming_xz(raw, pathlib.Path(td))
    results.append(stream)

    one_shot_xz = next(r for r in results if r["mode"] == "one_shot" and r["codec"] == "xz -9")

    # ---- streaming is decided by MEMORY SCALING, not by an absolute threshold -------------
    # A first attempt used "peak < 0.25 x payload".  That criterion is wrong for LZMA: xz -9
    # allocates a fixed ~64 MiB match-finder dictionary, so its peak is dominated by a CONSTANT
    # that has nothing to do with how much payload is buffered.  At a 4.7 MB payload the
    # constant is ~150x the payload and the test would report "not streaming" for a path that
    # buffers nothing.  The property that actually matters is whether peak memory GROWS with
    # payload size.  So it is measured at several sizes and the slope is taken.
    scaling = []
    with tempfile.TemporaryDirectory() as td:
        tdp = pathlib.Path(td)
        for frac in (0.25, 0.50, 1.00):
            part = raw[:int(len(raw) * frac)]
            s = bench_streaming_xz(part, tdp)
            g = bench_one_shot("gzip -9", lambda b: gzip.compress(b, 9), part)
            scaling.append({"fraction": frac, "payload_bytes": len(part),
                            "xz_stream_peak_bytes": s["peak_traced_bytes"],
                            "xz_stream_rss_peak_kb": peak_rss_kb(),
                            "gzip_peak_bytes": g["peak_traced_bytes"]})
    lo, hi = scaling[0], scaling[-1]
    d_payload = hi["payload_bytes"] - lo["payload_bytes"]
    d_peak_xz = hi["xz_stream_peak_bytes"] - lo["xz_stream_peak_bytes"]
    d_peak_gz = hi["gzip_peak_bytes"] - lo["gzip_peak_bytes"]
    slope_xz = d_peak_xz / d_payload if d_payload else 0.0
    slope_gz = d_peak_gz / d_payload if d_payload else 0.0
    # bounded memory <=> peak grows by much less than the payload does
    truly_streaming = slope_xz < 0.25
    fixed_cost_bytes = lo["xz_stream_peak_bytes"] - slope_xz * lo["payload_bytes"]
    payload = {
        "harness": "benchmark_compression.py",
        "purpose": "FEASIBILITY ONLY — archive cost; no scientific quantity",
        "scenario": args.scenario, "seed_index": args.seed_index, "master_seed": seed,
        "horizon_T": args.horizon, "rounds": len(run.round_terminal_times),
        "note": ("measured on a REDUCED-HORIZON payload; the ratio is not claimed to be "
                 "universal and the archive plan applies a declared safety factor to it"),
        "payload_generation_wall_seconds": gen_wall,
        "cpu_count": os.cpu_count(),
        "results": results,
        "streaming_verdict": {
            "truly_streaming": bool(truly_streaming),
            "criterion": ("d(peak memory)/d(payload bytes) < 0.25 measured across payload sizes "
                          "— an ABSOLUTE threshold is invalid for LZMA because its peak is "
                          "dominated by a fixed match-finder dictionary, not by buffering"),
            "memory_scaling_samples": scaling,
            "xz_stream_peak_slope": slope_xz,
            "gzip_peak_slope": slope_gz,
            "xz_fixed_encoder_cost_bytes": fixed_cost_bytes,
            "xz_fixed_encoder_cost_mb": fixed_cost_bytes / 1e6,
            "scheduling_note": ("the xz fixed encoder cost is per-compressing-process and MUST "
                                "be added to the memory equation if compression runs alongside "
                                "simulation workers; gzip's cost is negligible by comparison"),
            "temporary_disk_bytes": stream["compressed_bytes"],
            "temporary_disk_note": ("the streaming path writes only the compressed stream; the "
                                    "raw payload never needs to exist as a file"),
        },
    }
    out = pathlib.Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")

    for r in results:
        print(f"  {r['codec']:8s} {r['mode']:22s} {r['compressed_bytes']:>10,} B  "
              f"ratio {r['ratio']:6.1f}x  wall {r['wall_seconds']:6.2f}s  "
              f"cpu {r['cpu_seconds']:6.2f}s  peak {r['peak_traced_bytes'] / 1e6:7.2f} MB  "
              f"({r['peak_over_payload']:.3f} x payload)", flush=True)
    for s in scaling:
        print(f"  scale {s['fraction']:.2f}: payload {s['payload_bytes']:>10,} B  "
              f"xz peak {s['xz_stream_peak_bytes'] / 1e6:7.1f} MB  "
              f"gzip peak {s['gzip_peak_bytes'] / 1e6:6.2f} MB", flush=True)
    print(f"  d(peak)/d(payload): xz {slope_xz:.4f}  gzip {slope_gz:.4f}")
    print(f"  xz fixed encoder cost: {fixed_cost_bytes / 1e6:.1f} MB per process")
    print(f"  truly streaming (bounded memory): {truly_streaming}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
