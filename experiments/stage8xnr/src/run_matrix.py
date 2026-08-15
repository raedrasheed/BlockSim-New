"""Stage 8X-NR — pilot and primary matrix execution + CSV writers."""

from __future__ import annotations

import csv
import json
import os
import statistics
import time
from typing import Dict, List

from experiments.stage8xnr.config.nr_config import (
    ALPHA_CASES, ARMS, HASHRATE_HPS, S_NONCE, T_RUN_S, config_hash,
    derive_difficulty, predictions,
)
from experiments.stage8xnr.config.seeds import (
    pilot_seeds, primary_seeds, registry_dict,
)
from experiments.stage8xnr.src.engine_nr import RunResult, run_one

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
REPO = os.path.dirname(os.path.dirname(HERE))


def _run_row(r: RunResult, tag: str) -> Dict[str, object]:
    ivs = r.intervals_s
    row = {
        "tag": tag, "arm": r.arm, "N": r.n_miners, "seed": r.seed,
        "rounds": r.rounds, "accepted_blocks": r.accepted_blocks,
        "stale_blocks": r.stale_blocks,
        "mean_interval_s": statistics.mean(ivs) if ivs else "",
        "median_interval_s": statistics.median(ivs) if ivs else "",
        "p95_interval_s": (sorted(ivs)[max(0, int(0.95 * len(ivs)) - 1)]
                           if ivs else ""),
        "C_total_evaluations": r.C_total,
        "t_active_miner_s": r.t_active_miner_s,
        "t_low_miner_s": r.t_low_miner_s,
        "f_low_time": r.t_low_miner_s / (r.n_miners * T_RUN_S),
        "template_epochs_completed": r.template_epochs_completed,
        "nonce_domain_exhaustions": r.nonce_domain_exhaustions,
        "nonce_resets": r.nonce_resets,
        "state_time_conservation_rel": r.identity_errors[
            "state_time_conservation_rel"],
        "work_identity_rel": r.identity_errors["work_identity_rel"],
    }
    for sc in r.scope_rows:
        pre = {"NR-global-run": "run", "NR-template-epoch": "epoch"}[
            str(sc["scope"])]
        for k, v in sc.items():
            if k != "scope":
                row[f"{pre}_{k}"] = v
    # round-scope means from per-round rows
    if r.round_rows:
        for col in ("round_rho_nonce", "round_rho_exact", "round_U_nonce",
                    "round_M_ge2", "round_M_ge3", "round_m_max",
                    "round_mean_mult_reused", "round_O_mean", "round_O_median",
                    "round_O_p95", "round_O_max",
                    "subsweep_rho_nonce", "subsweep_rho_exact",
                    "subsweep_M_ge2", "subsweep_M_ge3", "subsweep_m_max",
                    "subsweep_mean_mult_reused",
                    "subsweep_O_mean", "subsweep_O_median", "subsweep_O_p95",
                    "subsweep_O_max", "subsweep_U_nonce", "subsweep_C_nonce"):
            vals = [float(rr[col]) for rr in r.round_rows]
            row[f"mean_{col}"] = sum(vals) / len(vals)
    return row


def _write_csv(path: str, rows: List[Dict[str, object]]) -> None:
    if not rows:
        return
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        for r in rows:
            w.writerow(r)


def execute(tag: str, n_grid: List[int], seeds: List[int],
            arms: List[str] = None, log_path: str = None) -> Dict[str, str]:
    os.makedirs(OUT, exist_ok=True)
    arms = arms or ARMS
    run_rows, round_rows, scope_rows, energy_rows, epoch_rows = [], [], [], [], []
    t0 = time.time()
    total = len(n_grid) * len(seeds) * len(arms)
    done = 0
    log = open(log_path, "a") if log_path else None
    for n in n_grid:
        for seed in seeds:
            base_energy = None
            for arm in arms:
                r = run_one(arm, n, seed, collect_rounds=True)
                run_rows.append(_run_row(r, tag))
                for rr in r.round_rows:
                    round_rows.append({"tag": tag, "arm": arm, "N": n,
                                       "seed": seed, **rr})
                for sc in r.scope_rows:
                    scope_rows.append({"tag": tag, "arm": arm, "N": n,
                                       "seed": seed, **sc})
                epoch_rows.append({
                    "tag": tag, "arm": arm, "N": n, "seed": seed,
                    "template_epochs_completed": r.template_epochs_completed,
                    "nonce_domain_exhaustions": r.nonce_domain_exhaustions,
                    "nonce_resets": r.nonce_resets,
                })
                if arm == "XNR-PW-CONV-OFFSET":
                    base_energy = r.energy_j(0.0)
                for case, alpha in ALPHA_CASES.items():
                    e = r.energy_j(alpha)
                    energy_rows.append({
                        "tag": tag, "arm": arm, "N": n, "seed": seed,
                        "alpha_case": case, "alpha": alpha, "energy_J": e,
                        "energy_kWh": e / 3.6e6,
                        "baseline_conv_offset_J": base_energy or "",
                        "saving_vs_conv_offset":
                            (1.0 - e / base_energy) if base_energy else "",
                    })
                done += 1
                if log:
                    log.write(f"{time.time()-t0:9.1f}s {done}/{total} "
                              f"{tag} N={n} seed={seed} {arm} "
                              f"blocks={r.accepted_blocks}\n")
                    log.flush()
    prefix = "stage8x_nr" if tag == "primary" else f"stage8x_nr_{tag}"
    paths = {
        "runs": os.path.join(OUT, f"{prefix}_physical_runs.csv"),
        "rounds": os.path.join(OUT, f"{prefix}_round_metrics.csv"),
        "nonce": os.path.join(OUT, f"{prefix}_nonce_reuse.csv"),
        "exact": os.path.join(OUT, f"{prefix}_exact_input_duplication.csv"),
        "pairwise": os.path.join(OUT, f"{prefix}_pairwise_overlap.csv"),
        "energy": os.path.join(OUT, f"{prefix}_energy_sensitivity.csv"),
        "epochs": os.path.join(OUT, f"{prefix}_template_epochs.csv"),
    }
    _write_csv(paths["runs"], run_rows)
    _write_csv(paths["rounds"], round_rows)
    nonce_cols = ("tag", "arm", "N", "seed", "scope", "C_nonce", "U_nonce",
                  "R_nonce", "rho_nonce", "M_ge2", "m_max", "O_mean",
                  "O_median", "O_max")
    exact_cols = ("tag", "arm", "N", "seed", "scope", "C_exact", "U_exact",
                  "R_exact", "rho_exact")
    _write_csv(paths["nonce"], [{k: r[k] for k in nonce_cols} for r in scope_rows])
    _write_csv(paths["exact"], [{k: r[k] for k in exact_cols} for r in scope_rows])
    # per-run pairwise-overlap / multiplicity table (round + subsweep scopes,
    # averaged over the run's rounds; every quantity exact per round)
    pair_rows = []
    for r in run_rows:
        for scope in ("round", "subsweep"):
            pair_rows.append({
                "tag": r["tag"], "arm": r["arm"], "N": r["N"],
                "seed": r["seed"], "scope": scope,
                "O_mean": r.get(f"mean_{scope}_O_mean", ""),
                "O_median": r.get(f"mean_{scope}_O_median", ""),
                "O_p95": r.get(f"mean_{scope}_O_p95", ""),
                "O_max": r.get(f"mean_{scope}_O_max", ""),
                "M_ge2": r.get(f"mean_{scope}_M_ge2", ""),
                "M_ge3": r.get(f"mean_{scope}_M_ge3", ""),
                "m_max": r.get(f"mean_{scope}_m_max", ""),
                "mean_mult_reused": r.get(f"mean_{scope}_mean_mult_reused", ""),
            })
    _write_csv(paths["pairwise"], pair_rows)
    _write_csv(paths["energy"], energy_rows)
    _write_csv(paths["epochs"], epoch_rows)
    # brief-canonical aliases (stage8xnr_*) alongside the original names
    if tag == "primary":
        import shutil
        for key, src in paths.items():
            dst = src.replace("stage8x_nr_", "stage8xnr_")
            shutil.copyfile(src, dst)
    if log:
        log.close()
    return paths


def write_seed_registry() -> str:
    os.makedirs(OUT, exist_ok=True)
    path = os.path.join(OUT, "stage8x_nr_seeds.json")
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
