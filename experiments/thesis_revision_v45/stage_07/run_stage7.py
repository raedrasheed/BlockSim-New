#!/usr/bin/env python3
"""Stage 7 — the frozen-execution scheduler.

Refuses to start unless the resource preflight verdict is PASS.  Executes the 660 FROZEN run
identities in the mandated priority order, under memory-aware concurrency, with an atomic
registry update after every run.

    python run_stage7.py --preflight host.json [--chunk-size 30] [--dry-run]

Priority order (slowest and longest first, so the binding path starts immediately):
    1 SECURITY_FLOOR   2 REASSIGNMENT   3 C06 (full-domain, no block)   4 LIGHTWEIGHT
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

from _common import (ARCHIVE, CHUNKS, DATA, FAILED, LOGS, RAW, Registry,       # noqa: E402
                     COMPLETED, FAILED_INFRASTRUCTURE, FAILED_MODEL, PENDING,
                     RERUN_COMPLETED, RUNNING, TERMINAL_SUCCESS, cost_class,
                     frozen_rows, sha256_file, HERE)
import resource_preflight as PF                                                # noqa: E402
import validate_run_output as V                                                # noqa: E402
from compress_and_archive import compress_verify_reclaim                       # noqa: E402

PRIORITY = ("SECURITY_FLOOR", "REASSIGNMENT", "C06", "LIGHTWEIGHT")


def priority_key(row: dict, srows: dict) -> tuple:
    c = cost_class(srows[row["scenario_id"]])
    band = "C06" if row["scenario_id"] == "C06" else c
    return (PRIORITY.index(band), row["scenario_id"], int(row["seed_index"]))


def ordered_runs(registry: Registry, srows: dict) -> list:
    state = {r["run_id"]: r for r in registry.read()}
    todo = [r for r in frozen_rows()
            if state[r["run_id"]]["run_status"] not in TERMINAL_SUCCESS
            and state[r["run_id"]]["run_status"] != FAILED_MODEL]
    return sorted(todo, key=lambda r: priority_key(r, srows))


def execute_one(reg: Registry, run_id: str, attempt: int, timeout_s: float) -> str:
    reg.update(run_id, run_status=RUNNING, attempt=attempt,
               start_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    cmd = [sys.executable, str(HERE / "worker.py"), "--run-id", run_id,
           "--out-dir", str(RAW), "--log-dir", str(LOGS), "--attempt", str(attempt)]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout_s)
        rc, out = p.returncode, p.stdout
    except subprocess.TimeoutExpired:
        rc, out = 4, ""
    elapsed = time.time() - t0
    end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    log = LOGS / f"{run_id}.attempt{attempt}.log"

    if rc != 0:
        status = FAILED_MODEL if rc == 3 else FAILED_INFRASTRUCTURE
        keep = FAILED / run_id / f"attempt{attempt}"
        keep.mkdir(parents=True, exist_ok=True)
        if log.exists():
            (keep / log.name).write_bytes(log.read_bytes())
        reg.update(run_id, run_status=status, end_timestamp=end,
                   wall_clock_seconds=f"{elapsed:.3f}", execution_log=str(log),
                   exception_type=("MODEL" if rc == 3 else "INFRASTRUCTURE"),
                   exception_detail=f"worker exit {rc}")
        return status

    info = json.loads(out.strip().splitlines()[-1])
    raw = pathlib.Path(info["result_file"])
    check = V.validate(raw)
    if not check["ok"]:
        reg.update(run_id, run_status=FAILED_MODEL, end_timestamp=end,
                   exception_type="SCHEMA", exception_detail="; ".join(check["problems"])[:400])
        return FAILED_MODEL
    comp = compress_verify_reclaim(raw, ARCHIVE / f"{run_id}.json.xz", reclaim=True)
    status = RERUN_COMPLETED if attempt > 1 else COMPLETED
    reg.update(run_id, run_status=status, end_timestamp=end,
               wall_clock_seconds=f"{elapsed:.3f}", result_file=str(raw),
               result_sha256=comp["raw_sha256"],
               compressed_file=str(ARCHIVE / f"{run_id}.json.xz"),
               compressed_sha256=comp["compressed_sha256"],
               config_sha256=info["config_sha256"], execution_log=str(log))
    return status


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--chunk-size", type=int, default=30)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-runs", type=int, default=None)
    a = ap.parse_args(argv)

    import scenarios as S                                                      # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    for d in (DATA, RAW, LOGS, CHUNKS, ARCHIVE, FAILED):
        d.mkdir(parents=True, exist_ok=True)
    reg = Registry()
    n = reg.initialise(srows)
    print(f"registry: {n} frozen run identities")

    pf = PF.gate_or_die(pathlib.Path(a.preflight)) if not a.dry_run else None
    if a.dry_run:
        print("DRY RUN — the preflight gate is NOT bypassed for real execution")
    todo = ordered_runs(reg, srows)
    print(f"to execute: {len(todo)} runs, priority order {PRIORITY}")
    for i, r in enumerate(todo[:6]):
        print(f"  {i+1:3d} {r['run_id']:12s} {cost_class(srows[r['scenario_id']])}")
    if a.dry_run:
        by = {}
        for r in todo:
            by[cost_class(srows[r["scenario_id"]])] = by.get(
                cost_class(srows[r["scenario_id"]]), 0) + 1
        print(f"  ... chunk size {a.chunk_size}, "
              f"{(len(todo) + a.chunk_size - 1)//a.chunk_size} chunks; by class {by}")
        return 0

    timeout_s = float(json.loads(pathlib.Path(a.preflight).read_text())
                      ["per_run_timeout"]["hours"]) * 3600
    done = 0
    for r in todo:
        if a.max_runs and done >= a.max_runs:
            break
        state = {x["run_id"]: x for x in reg.read()}[r["run_id"]]
        attempt = int(state["attempt"] or 0) + 1
        st = execute_one(reg, r["run_id"], attempt, timeout_s)
        done += 1
        print(f"  {r['run_id']:12s} {st}")
        if st == FAILED_MODEL:
            print("FROZEN EXECUTION STOPPED: model/scientific failure. The engine is NOT "
                  "modified. Report the exact blocker.")
            return 3
    print(json.dumps(reg.by_status(), indent=1, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
