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
import hashlib
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

# The derived run-level outcomes use the ACCEPTED Stage-5D / Stage-6 definitions verbatim,
# imported rather than reimplemented so the two can never drift.  The engine is not modified:
# these are computed in the worker from the returned RunContext, before serialisation.
from run_pilot import (post_round_audit, residency_and_energy_identity,        # noqa: E402
                       round_durations, nonterminal_activation_request_count,
                       ENERGY_IDENTITY_TOLERANCE_J, RESIDENCY_PARTITION_TOLERANCE_S)

#: Every preregistered run-level outcome that results_schema does NOT emit.  Absence of any of
#: these in a produced payload is a MODEL failure, never a silently-missing field.
DERIVED_REQUIRED = (
    "round_duration_values", "median_round_duration",
    "post_round_evaluation_record_count", "post_round_evaluation_nonce_count",
    "evaluation_missing_terminal_time_count", "nonterminal_activation_request_count",
    "maximum_energy_identity_residual_j", "maximum_residency_partition_residual_s",
)


def derived_outcomes(run, cfg) -> dict:
    """Compute every preregistered run-level outcome not emitted by the accepted adapter.

    Also returns a compact AUDIT summary — exact counts and a digest of the inputs — so the
    derived values can be independently re-checked without retaining the whole RunContext.
    """
    durs, monotonic = round_durations(run, cfg)
    ident = residency_and_energy_identity(run, cfg)
    audit = post_round_audit(run)
    med = (sorted(durs)[len(durs) // 2] if durs else None)
    out = {
        "round_duration_values": [float(d) for d in durs],
        "median_round_duration": (float(med) if med is not None else None),
        "round_terminal_times_strictly_increasing": bool(monotonic),
        "nonterminal_activation_request_count": nonterminal_activation_request_count(run),
        "maximum_energy_identity_residual_j": ident["maximum_energy_identity_residual_j"],
        "maximum_residency_partition_residual_s":
            ident["maximum_residency_partition_residual_s"],
        "residency_by_state_s": ident["residency_by_state_s"],
        "waking_residency_s": ident["waking_residency_s"],
        "offline_or_disqualified_residency_s": ident["offline_or_disqualified_residency_s"],
    }
    out.update(audit)
    # auditable provenance for the derived values
    terminal = sorted(run.round_terminal_times.items(), key=lambda kv: kv[1])
    out["derived_audit"] = {
        "round_count": len(durs),
        "evaluation_ledger_entries": len(run.evaluation_ledger),
        "miner_count": len(run.miners),
        "run_start_time": float(cfg.run_start_time),
        "run_end_time": float(run.run_end_time),
        "round_terminal_times_sha256": hashlib.sha256(
            json.dumps([[k, float(v)] for k, v in terminal], sort_keys=True).encode()
        ).hexdigest(),
        "energy_identity_tolerance_j": ENERGY_IDENTITY_TOLERANCE_J,
        "residency_partition_tolerance_s": RESIDENCY_PARTITION_TOLERANCE_S,
        "definitions": "accepted Stage-5D audit / Stage-6 outcome dictionary, imported verbatim",
    }
    missing = [k for k in DERIVED_REQUIRED if out.get(k) is None]
    if missing:
        raise RuntimeError(f"derived run-level outcomes missing: {missing}")
    return out


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
    ap.add_argument("--physical-execution-id", default=None)
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
        derived = derived_outcomes(run, cfg)      # BEFORE the RunContext is discarded
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
        "physical_execution_id": args.physical_execution_id or "",
        "results": res,
        "derived": derived,
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
