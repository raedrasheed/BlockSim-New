"""Stage 8X-E50 — pilot and primary execution + the nine raw outputs.

alpha is accounting-only: state-time is recorded once per physical run and the
four energy values are derived (test 20 asserts no trajectory difference).
Per-seed paired ratios versus E50-MT100 use NA when the paired MT100 run has
zero accepted blocks (preregistered rule; NA is reported, never imputed).
"""

from __future__ import annotations

import csv
import json
import os
import statistics
import time
from typing import Dict, List

from experiments.stage8xe50.config.e50_config import (
    ALPHA_CASES, ARM_CONV, ARM_MT, ARMS, T_RUN_S, config_hash,
)
from experiments.stage8xe50.config.seeds import pilot_seeds, primary_seeds, registry_dict
from experiments.stage8xe50.src.engine_e50 import RunResult, run_one

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
REPO = os.path.dirname(os.path.dirname(HERE))


def _write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    keys: List[str] = []
    for r in rows:
        for kk in r:
            if kk not in keys:
                keys.append(kk)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)


def _median(xs):
    return statistics.median(xs) if xs else ""


def execute(tag: str, n_grid: List[int], seeds: List[int],
            log_path: str = None) -> Dict[str, str]:
    os.makedirs(OUT, exist_ok=True)
    runs_r, epoch_r, cov_r, dup_r, energy_r, svc_r, fair_r, pair_r = (
        [], [], [], [], [], [], [], [])
    t0 = time.time()
    total = len(n_grid) * len(seeds) * len(ARMS)
    done = 0
    log = open(log_path, "a") if log_path else None
    for n in n_grid:
        for seed in seeds:
            results: Dict[str, RunResult] = {}
            for arm in ARMS:
                results[arm] = run_one(arm, n, seed)
                done += 1
                if log:
                    r = results[arm]
                    log.write(f"{time.time()-t0:8.1f}s {done}/{total} {tag} "
                              f"N={n} seed={seed} {arm} blk={r.accepted_blocks}"
                              f" U={r.U_exact:.3e}\n")
                    log.flush()
            mt = results[ARM_MT]
            for arm, r in results.items():
                base = {"tag": tag, "arm": arm, "N": n, "seed": seed,
                        "k_active": r.k_active}
                runs_r.append({**base,
                    "rounds": r.rounds, "accepted_blocks": r.accepted_blocks,
                    "C_total": r.C_total, "U_exact": r.U_exact,
                    "R_exact": r.R_exact, "rho_exact": r.rho_exact,
                    "t_active_miner_s": r.t_active_miner_s,
                    "t_low_miner_s": r.t_low_miner_s,
                    "F_low": r.t_low_miner_s / (n * T_RUN_S),
                    "epochs_completed": r.epochs_completed,
                    "exhaustions": r.exhaustions,
                    "state_time_conservation_rel":
                        r.identity_errors["state_time_conservation_rel"],
                    "work_identity_rel": r.identity_errors["work_identity_rel"],
                })
                epoch_r.append({**base,
                    "epochs_completed": r.epochs_completed,
                    "exhaustions": r.exhaustions,
                    "unique_per_epoch":
                        r.U_exact / r.epochs_completed if r.epochs_completed else "",
                    "epoch_seconds":
                        (T_RUN_S / r.epochs_completed) if r.epochs_completed else "",
                })
                cov_r.append({**base,
                    "U_exact": r.U_exact,
                    "unique_coverage_rate_per_s": r.U_exact / T_RUN_S,
                    "coverage_retention_vs_MT100":
                        r.U_exact / mt.U_exact if mt.U_exact else "",
                })
                dup_r.append({**base,
                    "C_total": r.C_total, "U_exact": r.U_exact,
                    "R_exact": r.R_exact, "rho_exact": r.rho_exact,
                })
                for case, alpha in ALPHA_CASES.items():
                    e = r.energy_j(alpha)
                    eb = mt.energy_j(alpha)
                    energy_r.append({**base,
                        "alpha_case": case, "alpha": alpha, "energy_J": e,
                        "energy_kWh": e / 3.6e6,
                        "saving_vs_MT100": 1.0 - e / eb,
                        "energy_per_block_J":
                            e / r.accepted_blocks if r.accepted_blocks else "",
                    })
                svc_r.append({**base,
                    "accepted_blocks": r.accepted_blocks,
                    "mean_interval_s": (statistics.mean(r.intervals_s)
                                        if r.intervals_s else ""),
                    "median_interval_s": _median(r.intervals_s),
                    "p95_interval_s": (sorted(r.intervals_s)[
                        max(0, int(0.95 * len(r.intervals_s)) - 1)]
                        if r.intervals_s else ""),
                    "stale_blocks": 0,
                })
                fair_r.append({**base,
                    "duty_min": r.duty_min, "duty_max": r.duty_max,
                    "duty_sd": r.duty_sd, "jain_index": r.jain_index,
                    "duty_max_min_ratio":
                        r.duty_max / r.duty_min if r.duty_min else "",
                    "transitions_total": r.transitions_total,
                    "active_episode_s": r.active_episode_s,
                    "low_episode_s": r.low_episode_s,
                })
                if arm != ARM_MT:
                    row = {**base,
                        "coverage_retention":
                            r.U_exact / mt.U_exact if mt.U_exact else "",
                        "block_ratio": (r.accepted_blocks / mt.accepted_blocks
                                        if mt.accepted_blocks else "NA"),
                        "median_latency_ratio":
                            (_median(r.intervals_s) / _median(mt.intervals_s)
                             if r.intervals_s and mt.intervals_s else "NA"),
                    }
                    for case, alpha in ALPHA_CASES.items():
                        row[f"saving_{case}"] = \
                            1.0 - r.energy_j(alpha) / mt.energy_j(alpha)
                    pair_r.append(row)
    prefix = "stage8xe50" if tag == "primary" else f"stage8xe50_{tag}"
    paths = {}
    for name, rows in (("physical_runs", runs_r), ("epoch_metrics", epoch_r),
                       ("unique_coverage", cov_r), ("exact_duplication", dup_r),
                       ("energy_sensitivity", energy_r),
                       ("service_metrics", svc_r), ("fairness", fair_r),
                       ("pairwise_seed_metrics", pair_r)):
        paths[name] = os.path.join(OUT, f"{prefix}_{name}.csv")
        _write_csv(paths[name], rows)
    if log:
        log.close()
    return paths


def write_seed_registry() -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "stage8xe50_seeds.json")
    with open(path, "w") as fh:
        json.dump(registry_dict(REPO), fh, indent=2)
    return path


if __name__ == "__main__":
    import sys
    which = sys.argv[1] if len(sys.argv) > 1 else "pilot"
    write_seed_registry()
    if which == "pilot":
        p = execute("pilot", [100, 300, 500], pilot_seeds(),
                    log_path=os.path.join(OUT, "pilot_progress.log"))
    else:
        p = execute("primary", [100, 200, 300, 400, 500], primary_seeds(),
                    log_path=os.path.join(OUT, "primary_progress.log"))
    print(json.dumps(p, indent=2))
    print("config_hash:", config_hash())
