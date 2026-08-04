#!/usr/bin/env python3
"""Stage 7 — the frozen-execution scheduler: deterministic admission, genuine concurrency.

Refuses to start unless the resource preflight verdict is PASS *and* its durable paths are
usable.  Executes the **630 unique physical executions** behind the 660 frozen logical rows,
in the mandated priority order, under per-class concurrency limits taken from the verified
host record, with an atomic registry update after every completion.

    python run_stage7.py --preflight host.json [--dry-run] [--max-runs N]

Concurrency is real: workers are launched as non-blocking subprocesses and reaped as they
finish.  Admission order is deterministic (priority band, scenario, seed index); completion
order is not, and must not be, because a run's identity never depends on when it finished.

Priority: 1 SECURITY_FLOOR  2 REASSIGNMENT  3 C06 (full-domain no-block)  4 LIGHTWEIGHT
"""
from __future__ import annotations

import argparse
import json
import pathlib
import subprocess
import sys
import time

from _common import (COMPLETED, FAILED_INFRASTRUCTURE, FAILED_MODEL, PENDING,   # noqa: E402
                     RERUN_COMPLETED, RUNNING, TERMINAL_SUCCESS, ExecutionPaths,
                     Registry, build_physical_map, cost_class, executor_run_id,
                     frozen_rows, HERE)
import resource_preflight as PF                                                 # noqa: E402
import validate_run_output as V                                                 # noqa: E402
from compress_and_archive import compress_verify_reclaim                        # noqa: E402

PRIORITY = ("SECURITY_FLOOR", "REASSIGNMENT", "C06", "LIGHTWEIGHT")


def band(run_id: str, srows: dict, logical: dict) -> str:
    sid = logical[run_id]["scenario_id"]
    return "C06" if sid == "C06" else cost_class(srows[sid])


def admission_order(logical: dict, srows: dict, physical: dict) -> list:
    """Deterministic admission order over PHYSICAL executions, one entry per physical id."""
    out = []
    for pid, members in physical.items():
        ex = executor_run_id(members)
        out.append((PRIORITY.index(band(ex, srows, logical)),
                    logical[ex]["scenario_id"], int(logical[ex]["seed_index"]), pid, ex))
    return [(pid, ex) for _b, _s, _i, pid, ex in sorted(out)]


class Pool:
    """A bounded pool with SEPARATE active counts per cost class and a total process cap.

    The class limits come from the verified host record and are never exceeded.  Compressors
    occupy the same process budget as workers, because they are real processes with a real
    (measured) memory footprint.
    """

    def __init__(self, limits: dict, cpu_count: int, compressors: int = 0):
        self.limits = {k: int(v) for k, v in limits.items()}
        self.total_cap = max(1, int(cpu_count) - int(compressors))
        self.active = {}                       # pid -> (run_id, physical_id, band, popen, t0)

    def counts(self) -> dict:
        c = {}
        for _rid, _pid, b, _p, _t in self.active.values():
            c[b] = c.get(b, 0) + 1
        return c

    def can_admit(self, b: str) -> bool:
        if len(self.active) >= self.total_cap:
            return False
        limit_key = "LIGHTWEIGHT" if b == "C06" else b
        # C06 is unbenchmarked: it is scheduled against the SLOWEST measured class's budget
        if b == "C06":
            limit_key = "SECURITY_FLOOR"
        return self.counts().get(b, 0) < self.limits.get(limit_key, 0)

    def launch(self, run_id, physical_id, b, cmd):
        p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.active[p.pid] = (run_id, physical_id, b, p, time.time())

    def reap(self, timeout_s: float):
        """Return finished (run_id, physical_id, rc, stdout, elapsed); non-blocking."""
        done = []
        for key in list(self.active):
            rid, pid_, b, proc, t0 = self.active[key]
            if proc.poll() is None:
                if time.time() - t0 > timeout_s:
                    proc.kill()
                    proc.wait()
                    done.append((rid, pid_, 4, "", time.time() - t0))
                    del self.active[key]
                continue
            out, _err = proc.communicate()
            done.append((rid, pid_, proc.returncode, out, time.time() - t0))
            del self.active[key]
        return done


def _finalise(reg, paths, logical, physical, run_id, physical_id, rc, out, elapsed):
    """Validate -> checksum -> compress -> verify -> atomically update EVERY alias row."""
    end = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    members = sorted(physical[physical_id])
    log = paths.logs / f"{run_id}.attempt1.log"

    if rc != 0:
        status = FAILED_MODEL if rc == 3 else FAILED_INFRASTRUCTURE
        keep = paths.failed_attempts / run_id
        keep.mkdir(parents=True, exist_ok=True)
        if log.exists():
            (keep / log.name).write_bytes(log.read_bytes())
        for rid in members:
            reg.update(rid, run_status=status, end_timestamp=end,
                       wall_clock_seconds=f"{elapsed:.3f}", execution_log=str(log),
                       exception_type=("MODEL" if rc == 3 else "INFRASTRUCTURE"),
                       exception_detail=f"worker exit {rc}")
        return status

    info = json.loads(out.strip().splitlines()[-1])
    raw = pathlib.Path(info["result_file"])
    check = V.validate(raw)
    if not check["ok"]:
        for rid in members:
            reg.update(rid, run_status=FAILED_MODEL, end_timestamp=end,
                       exception_type="SCHEMA",
                       exception_detail="; ".join(check["problems"])[:400])
        return FAILED_MODEL

    dest = paths.archive / f"{physical_id}.json.xz"
    comp = compress_verify_reclaim(raw, dest, reclaim=True)
    # S7A-5: the raw file no longer exists. Record that fact rather than a dangling path.
    for rid in members:
        reg.update(rid, run_status=COMPLETED, end_timestamp=end,
                   wall_clock_seconds=f"{elapsed:.3f}",
                   physical_execution_id=physical_id,
                   shared_physical_execution=str(len(members) > 1).lower(),
                   alias_group_id=logical[rid]["alias_group_id"],
                   materialised_from_run_id=run_id,
                   raw_reclaimed="true", raw_sha256=comp["raw_sha256"],
                   compressed_file=str(dest), compressed_sha256=comp["compressed_sha256"],
                   archive_verified=str(comp["verified"]).lower(),
                   config_sha256=info["config_sha256"], execution_log=str(log))
    return COMPLETED


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--preflight", required=True)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-runs", type=int, default=None)
    ap.add_argument("--poll-seconds", type=float, default=2.0)
    a = ap.parse_args(argv)

    import scenarios as S                                                       # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = build_physical_map()
    logical, physical = m["logical"], m["physical"]

    if a.dry_run:
        paths = ExecutionPaths()
        rec = {"worker_limits_by_class": {"LIGHTWEIGHT": 3, "SECURITY_FLOOR": 1,
                                          "REASSIGNMENT": 1},
               "cpu_count": 4, "compressor_count": 0, "per_run_timeout": {"hours": 24}}
    else:
        rec = json.loads(pathlib.Path(a.preflight).read_text())
        PF.gate_or_die(pathlib.Path(a.preflight))          # refuses unless PASS *and* usable
        paths = ExecutionPaths.from_record(rec)
    paths.mkdirs()

    reg = Registry(paths.registry)
    n = reg.initialise(srows, logical)
    print(f"registry: {n} logical rows over {len(physical)} physical executions "
          f"({sum(1 for v in physical.values() if len(v) > 1)} alias groups)")

    state = {r["run_id"]: r for r in reg.read()}
    order = [(pid, ex) for pid, ex in admission_order(logical, srows, physical)
             if state[ex]["run_status"] not in TERMINAL_SUCCESS
             and state[ex]["run_status"] != FAILED_MODEL]
    print(f"to execute: {len(order)} physical executions, priority {PRIORITY}")
    limits = rec["worker_limits_by_class"]
    print(f"worker limits: {limits}; cpu {rec['cpu_count']}; "
          f"compressors {rec.get('compressor_count', 0)}")
    if a.dry_run:
        for pid, ex in order[:5]:
            print(f"  {ex:12s} {band(ex, srows, logical):15s} {pid}")
        print(f"  ... {len(order)} total; alias rows materialised without re-execution")
        return 0

    timeout_s = float(rec["per_run_timeout"]["hours"]) * 3600
    pool = Pool(limits, rec["cpu_count"], rec.get("compressor_count", 0))
    queue = list(order[:a.max_runs] if a.max_runs else order)
    admitted, stop_admission = 0, False

    while queue or pool.active:
        while queue and not stop_admission:
            pid, ex = queue[0]
            b = band(ex, srows, logical)
            if not pool.can_admit(b):
                break
            queue.pop(0)
            reg.update(ex, run_status=RUNNING, attempt=1,
                       physical_execution_id=pid,
                       start_timestamp=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
            pool.launch(ex, pid, b, [sys.executable, str(HERE / "worker.py"),
                                     "--run-id", ex, "--out-dir", str(paths.raw),
                                     "--log-dir", str(paths.logs),
                                     "--physical-execution-id", pid])
            admitted += 1
        for rid, pid, rc, out, elapsed in pool.reap(timeout_s):
            st = _finalise(reg, paths, logical, physical, rid, pid, rc, out, elapsed)
            print(f"  {rid:12s} {st}  ({elapsed:.1f}s)")
            if st == FAILED_MODEL:
                stop_admission = True
                print("MODEL FAILURE: admission stopped. Running workers will close safely. "
                      "The engine is NOT modified.")
        if pool.active and not (queue and not stop_admission):
            time.sleep(a.poll_seconds)
    print(json.dumps(reg.by_status(), indent=1, sort_keys=True))
    return 3 if stop_admission else 0


if __name__ == "__main__":
    raise SystemExit(main())
