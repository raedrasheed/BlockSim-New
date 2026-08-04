#!/usr/bin/env python3
"""Stage 6 — capture a RIGHT-CENSORED pilot run without disturbing it.

The Stage-6 freeze was closed under an explicit, user-authorised time constraint while one
Tier-2 run was still executing.  That run is NOT terminated, NOT restarted and NOT reported as
completed.  Everything observable about it is recorded here, together with the exact censoring
interpretation, so a partial observation is never mistaken for a finished measurement.

    python capture_censored_run.py --pid 12496 --scenario B02 --seed-index 6
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import pathlib
import subprocess
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                       # noqa: E402
from generate_seed_registry import build_rows               # noqa: E402
from sample_run_resources import read_proc                  # noqa: E402

CENSORED_STATUS = "RIGHT_CENSORED_RUNNING_AT_STAGE6_FREEZE"


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else "ABSENT"


def simulated_time(pid: int) -> float | None:
    """Read the live event time from the running process without perturbing it."""
    try:
        out = subprocess.run(["py-spy", "dump", "--pid", str(pid), "--locals"],
                             capture_output=True, text=True, timeout=90).stdout
    except Exception:
        return None
    import re
    m = re.findall(r'"event_time": ([0-9.]+)|observation_time: ([0-9.]+)', out)
    for a, b in m:
        return float(a or b)
    return None


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--pid", type=int, required=True)
    ap.add_argument("--scenario", required=True)
    ap.add_argument("--seed-index", type=int, required=True)
    ap.add_argument("--out", default=None)
    args = ap.parse_args(argv)

    seed = [r["master_seed_decimal"] for r in build_rows()
            if r["seed_class"] == "PILOT"][args.seed_index]
    row = {r["scenario_id"]: r for r in S.confirmatory_rows()}[args.scenario]
    cfg = S.build_config(row, seed, S.TIER2)
    cfg_repr = json.dumps({k: str(v) for k, v in sorted(vars(cfg).items())}, sort_keys=True)
    cfg_sha = hashlib.sha256(cfg_repr.encode()).hexdigest()

    proc = read_proc(args.pid)
    sim_t = simulated_time(args.pid)
    t2 = HERE / "pilot" / "tier2"
    log = t2 / f"{args.scenario}.log"
    ckpt = t2 / f"{args.scenario}.json"
    sampler = t2 / f"{args.scenario}.resources.json"

    rec = {
        "scenario_id": args.scenario,
        "tier": "TIER2",
        "run_status": CENSORED_STATUS,
        "censoring": {
            "reason": ("Stage 6 was closed under an explicit user-authorised time constraint; "
                       "the remaining run required approximately 9-10 further wall-clock hours. "
                       "The run was NOT stopped, NOT restarted and NOT replaced, and the "
                       "decision was made without reference to the direction or magnitude of "
                       "any effect."),
            "elapsed_wall_seconds_is": "LOWER_BOUND on total runtime",
            "vm_hwm_is": "LOWER_BOUND on final peak memory",
            "output_bytes_is": "LOWER_BOUND on final output size",
            "projected_completion_is": "OPERATIONAL ESTIMATE, not a completed measurement",
            "scientific_use": ("NONE — no treatment effect, no energy quantity and no "
                               "hypothesis outcome is inferred from the partial run"),
            "permitted_later_use": ("Stage-7 resource preflight only; it may not change the "
                                    "frozen hypotheses, matrix, seeds, outcomes, margins or "
                                    "analysis plan"),
        },
        "pid": args.pid,
        "master_seed": seed,
        "seed_index": args.seed_index,
        "config_sha256": cfg_sha,
        "config_num_miners": cfg.num_miners,
        "config_horizon_T": cfg.horizon_T,
        "config_difficulty": cfg.difficulty,
        "config_batch_size": cfg.batch_size,
        "config_template_seed": cfg.template_seed,
        "config_adversarial_seed": cfg.adversarial.deterministic_seed,
        "observation_unix_time": time.time(),
        "process_start_unix_time": time.time() - proc["wall_seconds"],
        "elapsed_wall_seconds_LOWER_BOUND": proc["wall_seconds"],
        "cpu_seconds_LOWER_BOUND": proc["cpu_seconds"],
        "user_cpu_seconds": proc["utime_s"],
        "system_cpu_seconds": proc["stime_s"],
        "cpu_over_wall_ratio": proc["cpu_seconds"] / proc["wall_seconds"],
        "vm_hwm_mb_LOWER_BOUND": proc.get("vm_hwm_kb", 0) / 1024.0,
        "vm_rss_mb_at_observation": proc.get("vm_rss_kb", 0) / 1024.0,
        "simulated_time_seconds": sim_t,
        "horizon_T": S.TIER2["horizon_T"],
        "simulated_fraction": (sim_t / S.TIER2["horizon_T"]) if sim_t else None,
        "checkpoint_bytes_LOWER_BOUND": ckpt.stat().st_size if ckpt.exists() else 0,
        "checkpoint_exists": ckpt.exists(),
        "event_count": "NOT_AVAILABLE_UNTIL_COMPLETION",
        "round_count": "NOT_AVAILABLE_UNTIL_COMPLETION",
        "zero_block_indicator": "NOT_AVAILABLE_UNTIL_COMPLETION",
        "results_json_bytes": "NOT_AVAILABLE_UNTIL_COMPLETION",
        "log_path": str(log.relative_to(REPO_ROOT)),
        "log_sha256": sha256_file(log),
        "sampler_path": str(sampler.relative_to(REPO_ROOT)),
        "sampler_sha256": sha256_file(sampler),
        "checkpoint_path": str(ckpt.relative_to(REPO_ROOT)),
        "checkpoint_sha256": sha256_file(ckpt),
        "resource_limits": {"cpu_count": os.cpu_count()},
    }
    out = pathlib.Path(args.out or (t2 / f"{args.scenario}.censored.json"))
    out.write_text(json.dumps(rec, indent=1, sort_keys=True, default=str) + "\n")
    print(f"{args.scenario}: {CENSORED_STATUS}")
    print(f"  elapsed  >= {proc['wall_seconds']:,.0f}s   cpu >= {proc['cpu_seconds']:,.0f}s   "
          f"cpu/wall {proc['cpu_seconds'] / proc['wall_seconds']:.3f}")
    print(f"  VmHWM    >= {proc.get('vm_hwm_kb', 0) / 1024:,.0f} MB")
    print(f"  sim time  = {sim_t} of {S.TIER2['horizon_T']}  "
          f"({100 * sim_t / S.TIER2['horizon_T']:.1f}%)" if sim_t else "  sim time unavailable")
    print(f"  config sha256 {cfg_sha}")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
