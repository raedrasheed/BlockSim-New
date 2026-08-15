"""Stage 8X-ND — execution + the nine required raw outputs (brief section 37).

Physical runs: ND-PW, ND-PW-OFFSET (secondary), ND-PC. Derived energy-policy
observations: ND-PC-NOLP rows are computed from the ND-PC trajectories and are
flagged run_kind="derived" — they are never separate simulations.
"""

from __future__ import annotations

import csv
import json
import os
import statistics
import time
from typing import Dict, List

from experiments.stage8xnd.config.nd_config import (
    ALPHA_CASES, ARM_PC, ARM_PC_NOLP, ARM_PW, ARM_PW_OFFSET, HASHRATE_HPS,
    NONCE_DOMAIN_SIZE, PHYSICAL_ARMS, T_RUN_S, config_hash, partition,
    per_miner_domain,
)
from experiments.stage8xnd.config.seeds import pilot_seeds, primary_seeds, registry_dict
from experiments.stage8xnd.src.engine_nd import energy_j, run_physical

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
REPO = os.path.dirname(os.path.dirname(HERE))


def _w(path, rows):
    if not rows:
        return
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)


def _med(xs):
    return statistics.median(xs) if xs else ""


def execute(tag: str, n_grid: List[int], seeds: List[int], log_path=None):
    os.makedirs(OUT, exist_ok=True)
    phys, noncem, epochm, energym, svcm, workm, lowm, pairm = ([] for _ in range(8))
    t0 = time.time()
    log = open(log_path, "a") if log_path else None
    done, total = 0, len(n_grid) * len(seeds) * len(PHYSICAL_ARMS)
    for n in n_grid:
        for seed in seeds:
            res = {}
            for arm in PHYSICAL_ARMS:
                res[arm] = run_physical(arm, n, seed)
                done += 1
                if log:
                    log.write(f"{time.time()-t0:7.1f}s {done}/{total} {tag} "
                              f"N={n} seed={seed} {arm} "
                              f"blk={res[arm].accepted_blocks}\n")
                    log.flush()
            pw, pc = res[ARM_PW], res[ARM_PC]
            for arm in PHYSICAL_ARMS + [ARM_PC_NOLP]:
                r = res.get(arm, pc)                      # NOLP <- PC physics
                kind = "derived" if arm == ARM_PC_NOLP else "physical"
                base = {"tag": tag, "arm": arm, "N": n, "seed": seed,
                        "run_kind": kind}
                sr = {sc["scope"]: sc for sc in r.scope_rows}
                run_sc = sr["NR-global-run"]
                phys.append({**base,
                    "rounds": r.rounds, "accepted_blocks": r.accepted_blocks,
                    "W_total": r.C_total,
                    "t_active_miner_s": (r.t_active_miner_s if arm != ARM_PC_NOLP
                                         else r.t_active_miner_s + r.t_low_miner_s),
                    "t_low_miner_s": (r.t_low_miner_s if arm != ARM_PC_NOLP
                                      else 0.0),
                    "F_low": (r.t_low_miner_s / (n * T_RUN_S)
                              if arm == ARM_PC else 0.0),
                    "state_time_conservation_rel":
                        r.identity_errors["state_time_conservation_rel"],
                    "work_identity_rel": r.identity_errors["work_identity_rel"],
                })
                noncem.append({**base,
                    "per_miner_domain_size": per_miner_domain(n, arm, 0),
                    "per_miner_domain_size_max": max(
                        per_miner_domain(n, arm, i) for i in range(n)),
                    "C_nonce": r.C_total,
                    "U_nonce_run": run_sc["U_nonce"],
                    "R_nonce": run_sc["R_nonce"],
                    "rho_nonce": run_sc["rho_nonce"],
                    "cross_miner_m_max": run_sc["m_max"],
                    "cross_miner_M_ge2": run_sc["M_ge2"],
                    "rho_exact_secondary": run_sc["rho_exact"],
                    "domain_sweeps_per_miner":
                        r.template_epochs_completed / n,
                })
                epochm.append({**base,
                    "template_epochs_completed": r.template_epochs_completed,
                    "header_renewals": r.template_epochs_completed,
                    "nonce_domain_exhaustions": r.nonce_domain_exhaustions,
                    "nonce_resets": r.nonce_resets,
                })
                for case, alpha in ALPHA_CASES.items():
                    e = energy_j(r, arm if arm == ARM_PC else ARM_PC_NOLP, alpha)
                    e_pw = energy_j(pw, ARM_PW, alpha)
                    energym.append({**base,
                        "alpha_case": case, "alpha": alpha,
                        "energy_J": e, "energy_kWh": e / 3.6e6,
                        "saving_vs_ND_PW": 1.0 - e / e_pw,
                        "energy_per_block_J":
                            e / r.accepted_blocks if r.accepted_blocks else "",
                    })
                svcm.append({**base,
                    "accepted_blocks": r.accepted_blocks,
                    "closed_rounds": r.rounds,
                    "mean_interval_s": (statistics.mean(r.intervals_s)
                                        if r.intervals_s else ""),
                    "median_interval_s": _med(r.intervals_s),
                    "p95_interval_s": (sorted(r.intervals_s)[
                        max(0, int(0.95 * len(r.intervals_s)) - 1)]
                        if r.intervals_s else ""),
                    "blocks_per_hour": r.accepted_blocks / (T_RUN_S / 3600),
                    "stale_blocks": r.stale_blocks,
                })
                workm.append({**base,
                    "W_total": r.C_total,
                    "hashes_per_block": (r.C_total / r.accepted_blocks
                                         if r.accepted_blocks else ""),
                    "W_unique_exact_secondary": run_sc["U_exact"],
                    "exact_duplicates_secondary": run_sc["R_exact"],
                })
                lowm.append({**base,
                    "T_active_s": (r.t_active_miner_s if arm != ARM_PC_NOLP
                                   else r.t_active_miner_s + r.t_low_miner_s),
                    "T_low_s": (r.t_low_miner_s if arm == ARM_PC else 0.0),
                    "F_low": (r.t_low_miner_s / (n * T_RUN_S)
                              if arm == ARM_PC else 0.0),
                })
                if arm != ARM_PW:
                    row = {**base,
                        "block_retention":
                            (r.accepted_blocks / pw.accepted_blocks
                             if pw.accepted_blocks else "NA"),
                        "latency_ratio":
                            (_med(r.intervals_s) / _med(pw.intervals_s)
                             if r.intervals_s and pw.intervals_s else "NA"),
                    }
                    for case, alpha in ALPHA_CASES.items():
                        e = energy_j(r, arm if arm == ARM_PC else ARM_PC_NOLP,
                                     alpha)
                        row[f"saving_{case}"] = 1 - e / energy_j(pw, ARM_PW,
                                                                 alpha)
                        eb = (e / r.accepted_blocks if r.accepted_blocks else None)
                        eb_pw = (energy_j(pw, ARM_PW, alpha) / pw.accepted_blocks
                                 if pw.accepted_blocks else None)
                        row[f"energy_per_block_ratio_{case}"] = (
                            eb / eb_pw if eb and eb_pw else "NA")
                    pairm.append(row)
    prefix = "stage8xnd" if tag == "primary" else f"stage8xnd_{tag}"
    paths = {}
    for name, rows in (("physical_runs", phys),
                       ("nonce_domain_metrics", noncem),
                       ("epoch_metrics", epochm),
                       ("energy_sensitivity", energym),
                       ("service_metrics", svcm),
                       ("work_metrics", workm),
                       ("low_power_metrics", lowm),
                       ("paired_metrics", pairm)):
        paths[name] = os.path.join(OUT, f"{prefix}_{name}.csv")
        _w(paths[name], rows)
    if log:
        log.close()
    return paths


def write_seed_registry() -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "stage8xnd_seeds.json")
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
