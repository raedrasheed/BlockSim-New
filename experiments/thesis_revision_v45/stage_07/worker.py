#!/usr/bin/env python3
"""Stage 7 — execute exactly ONE frozen confirmatory run, as its own process.

The worker is deliberately dumb: it takes a run_id, rebuilds that run's FROZEN configuration
from the Stage-6 artefacts, executes the ACCEPTED engine, and writes its result and log.  It
performs no scheduling, no retry and no registry mutation — the scheduler owns those, so a
killed worker can never leave the registry inconsistent.

    python worker.py --run-id A01-S00 --out-dir <raw> --log-dir <logs>

Exit codes:  0 COMPLETED   3 FAILED_MODEL   4 FAILED_INFRASTRUCTURE
"""
from __future__ import annotations

import argparse
import json
import os
import pathlib
import resource
import time
import traceback

from _common import (FROZEN_CONFIGS, config_sha256, cost_class, frozen_rows,  # noqa: E402
                     sha256_file)

import scenarios as S                                                          # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation                       # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                         # noqa: E402


def build(run_id: str):
    """Rebuild the exact frozen configuration for one run identity.  Nothing is regenerated."""
    row = next((r for r in frozen_rows() if r["run_id"] == run_id), None)
    if row is None:
        raise KeyError(f"{run_id} is not one of the 660 frozen run identities")
    srow = {r["scenario_id"]: r for r in S.confirmatory_rows()}[row["scenario_id"]]
    cfg = S.build_config(srow, int(row["master_seed"]), S.TIER2)
    return row, srow, cfg


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--run-id", required=True)
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--log-dir", required=True)
    ap.add_argument("--attempt", type=int, default=1)
    args = ap.parse_args(argv)

    out_dir, log_dir = pathlib.Path(args.out_dir), pathlib.Path(args.log_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    log_dir.mkdir(parents=True, exist_ok=True)
    log = log_dir / f"{args.run_id}.attempt{args.attempt}.log"

    def note(msg):
        with open(log, "a") as fh:
            fh.write(f"{time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())} {msg}\n")

    started = time.time()
    try:
        row, srow, cfg = build(args.run_id)
    except Exception:
        note("CONFIG_ERROR\n" + traceback.format_exc())
        return 3
    csha = config_sha256(cfg)
    note(f"run_id={args.run_id} scenario={row['scenario_id']} seed={row['master_seed']} "
         f"class={cost_class(srow)} config_sha256={csha} pid={os.getpid()}")

    # The frozen config on disk is the authority: a drift here is a MODEL failure, not a retry.
    frozen = FROZEN_CONFIGS / f"{row['scenario_id']}.json"
    if frozen.exists():
        declared = json.loads(frozen.read_text())
        for k, v in declared.items():
            if k in ("template_seed", "adversarial_seed", "master_seed", "deterministic_seed"):
                continue            # per-seed fields, not scenario-level
            if hasattr(cfg, k) and str(getattr(cfg, k)) != str(v):
                note(f"FROZEN_CONFIG_DRIFT {k}: built {getattr(cfg, k)!r} != frozen {v!r}")
                return 3

    try:
        run = run_simulation(cfg, run_id=args.run_id)
        res = results_schema(run, cfg)
    except MemoryError:
        note("FAILED_INFRASTRUCTURE MemoryError\n" + traceback.format_exc())
        return 4
    except Exception:
        note("FAILED_MODEL\n" + traceback.format_exc())
        return 3

    elapsed = time.time() - started
    payload = {
        "run_id": args.run_id, "scenario_id": row["scenario_id"],
        "master_seed": int(row["master_seed"]), "seed_index": int(row["seed_index"]),
        "pair_id": row["pair_id"], "cost_class": cost_class(srow),
        "config_sha256": csha, "attempt": args.attempt,
        "wall_clock_seconds": elapsed,
        "peak_rss_mb": resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
        "rounds_executed": len(run.round_terminal_times),
        "log_event_count": len(run.log),
        "results": res,
    }
    dest = out_dir / f"{args.run_id}.json"
    dest.write_text(json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    note(f"COMPLETED {elapsed:.1f}s rss={payload['peak_rss_mb']:.0f}MB "
         f"rounds={payload['rounds_executed']} bytes={dest.stat().st_size} "
         f"sha256={sha256_file(dest)}")
    print(json.dumps({"run_id": args.run_id, "status": "COMPLETED",
                      "wall_clock_seconds": elapsed, "result_file": str(dest),
                      "result_sha256": sha256_file(dest), "config_sha256": csha,
                      "execution_log": str(log)}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
