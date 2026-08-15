"""Stage 8X-ND — tables ND-A..ND-N and paired statistics."""

from __future__ import annotations

import csv
import json
import math
import os
import statistics

from scipy import stats as sps

from experiments.stage8xnd.config.nd_config import (
    ACTIVE_POWER_W, ALPHA_CASES, ARM_PC, ARM_PC_NOLP, ARM_PW, ARM_PW_OFFSET,
    HASHRATE_HPS, N_GRID, NONCE_DOMAIN_SIZE, T_RUN_S, difficulty, partition,
    predictions, q_per_candidate, sweep_timing,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")
ALL_ARMS = [ARM_PW, ARM_PW_OFFSET, ARM_PC, ARM_PC_NOLP]


def _read(name):
    with open(os.path.join(OUT, name)) as fh:
        return list(csv.DictReader(fh))


def _write(name, rows):
    path = os.path.join(OUT, name)
    keys = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys, restval="")
        w.writeheader()
        w.writerows(rows)
    return path


def _vals(rows, arm, n, col, **flt):
    out = []
    for r in rows:
        if r["arm"] == arm and int(r["N"]) == n \
                and r.get(col, "") not in ("", "NA") \
                and all(str(r.get(k)) == str(v) for k, v in flt.items()):
            out.append(float(r[col]))
    return out


def _summ(vals):
    if not vals:
        return {"mean": "", "median": "", "sd": "", "iqr": "", "ci95_lo": "",
                "ci95_hi": "", "n": 0}
    n = len(vals)
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if n > 1 else 0.0
    qs = statistics.quantiles(vals, n=4) if n >= 4 else [min(vals), mean,
                                                        max(vals)]
    half = sps.t.ppf(0.975, n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": mean, "median": statistics.median(vals), "sd": sd,
            "iqr": qs[2] - qs[0], "ci95_lo": mean - half,
            "ci95_hi": mean + half, "n": n}


def build_all():
    phys = _read("stage8xnd_physical_runs.csv")
    noncem = _read("stage8xnd_nonce_domain_metrics.csv")
    epochm = _read("stage8xnd_epoch_metrics.csv")
    energym = _read("stage8xnd_energy_sensitivity.csv")
    svcm = _read("stage8xnd_service_metrics.csv")
    workm = _read("stage8xnd_work_metrics.csv")
    lowm = _read("stage8xnd_low_power_metrics.csv")
    pairm = _read("stage8xnd_paired_metrics.csv")
    paths = {}

    # ND-A scaling
    paths["A"] = _write("stage8xnd_tableA_scaling.csv", [
        {"N": n, "miner_hashrate_THs": 234.0, "miner_power_W": ACTIVE_POWER_W,
         "aggregate_hashrate_THs": 234.0 * n,
         "aggregate_power_W": ACTIVE_POWER_W * n,
         "difficulty_D_N": difficulty(n), "q": q_per_candidate(n)}
        for n in N_GRID])

    # ND-B PoW full-domain ownership
    paths["B"] = _write("stage8xnd_tableB_pw_domain.csv", [
        {"N": n, "per_miner_domain": NONCE_DOMAIN_SIZE,
         "domain_sweeps_per_miner_mean": _summ(
             _vals(noncem, ARM_PW, n, "domain_sweeps_per_miner"))["mean"],
         "cross_miner_m_max": _summ(
             _vals(noncem, ARM_PW, n, "cross_miner_m_max"))["mean"],
         "U_nonce_run": _summ(_vals(noncem, ARM_PW, n, "U_nonce_run"))["mean"]}
        for n in N_GRID])

    # ND-C PoCol partition sizes
    c_rows = []
    for n in N_GRID:
        sizes = [e - s + 1 for s, e in partition(n)]
        c_rows.append({"N": n, "range_min": min(sizes), "range_max": max(sizes),
                       "n_ranges": n, "sum": sum(sizes),
                       "spread": max(sizes) - min(sizes)})
    paths["C"] = _write("stage8xnd_tableC_pc_partition.csv", c_rows)

    # ND-D sweep timing
    paths["D"] = _write("stage8xnd_tableD_sweep_timing.csv", [
        {"N": n, **sweep_timing(n)} for n in N_GRID])

    # ND-E nonce-value reuse
    e_rows = []
    for n in N_GRID:
        for arm in (ARM_PW, ARM_PW_OFFSET, ARM_PC):
            e_rows.append({
                "N": n, "arm": arm,
                "C_nonce_mean": _summ(_vals(noncem, arm, n, "C_nonce"))["mean"],
                "U_nonce_run": _summ(_vals(noncem, arm, n, "U_nonce_run"))["mean"],
                "rho_nonce_mean": _summ(_vals(noncem, arm, n, "rho_nonce"))["mean"],
                "cross_miner_m_max": _summ(
                    _vals(noncem, arm, n, "cross_miner_m_max"))["mean"],
                "M_ge2": _summ(_vals(noncem, arm, n, "cross_miner_M_ge2"))["mean"],
                "rho_exact_secondary": _summ(
                    _vals(noncem, arm, n, "rho_exact_secondary"))["mean"],
            })
    paths["E"] = _write("stage8xnd_tableE_nonce_reuse.csv", e_rows)

    # ND-F low-power residency
    paths["F"] = _write("stage8xnd_tableF_low_power.csv", [
        {"N": n, "arm": arm,
         "F_low_mean": _summ(_vals(lowm, arm, n, "F_low"))["mean"],
         "F_low_predicted": (predictions(n)["f_low_expected"]
                             if arm == ARM_PC else 0.0),
         "T_low_s_mean": _summ(_vals(lowm, arm, n, "T_low_s"))["mean"],
         "T_active_s_mean": _summ(_vals(lowm, arm, n, "T_active_s"))["mean"]}
        for n in N_GRID for arm in ALL_ARMS])

    # ND-G energy
    g_rows = []
    for n in N_GRID:
        for arm in ALL_ARMS:
            for case in ALPHA_CASES:
                s = _summ(_vals(energym, arm, n, "energy_kWh",
                                alpha_case=case))
                sv = _summ(_vals(energym, arm, n, "saving_vs_ND_PW",
                                 alpha_case=case))
                g_rows.append({"N": n, "arm": arm, "alpha_case": case,
                               "energy_kWh_mean": s["mean"],
                               "saving_vs_ND_PW_mean": sv["mean"]})
    paths["G"] = _write("stage8xnd_tableG_energy.csv", g_rows)

    # ND-H blocks
    paths["H"] = _write("stage8xnd_tableH_blocks.csv", [
        {"N": n, "arm": arm,
         **{f"blocks_{k}": v for k, v in _summ(
             _vals(svcm, arm, n, "accepted_blocks")).items()},
         "pooled_blocks": sum(_vals(svcm, arm, n, "accepted_blocks"))}
        for n in N_GRID for arm in ALL_ARMS])

    # ND-I intervals / latency ratios
    i_rows = []
    for n in N_GRID:
        for arm in ALL_ARMS:
            row = {"N": n, "arm": arm}
            for col in ("mean_interval_s", "median_interval_s",
                        "p95_interval_s"):
                row[col] = _summ(_vals(svcm, arm, n, col))["mean"]
            if arm != ARM_PW:
                row["latency_ratio_mean"] = _summ(
                    _vals(pairm, arm, n, "latency_ratio"))["mean"]
            i_rows.append(row)
    paths["I"] = _write("stage8xnd_tableI_latency.csv", i_rows)

    # ND-J energy per block
    paths["J"] = _write("stage8xnd_tableJ_energy_per_block.csv", [
        {"N": n, "arm": arm, "alpha_case": case,
         "energy_per_block_J_mean": _summ(
             _vals(energym, arm, n, "energy_per_block_J",
                   alpha_case=case))["mean"],
         "energy_per_block_ratio_mean": (_summ(
             _vals(pairm, arm, n, f"energy_per_block_ratio_{case}"))["mean"]
             if arm != ARM_PW else 1.0)}
        for n in N_GRID for arm in ALL_ARMS for case in ("LP0", "LP50")])

    # ND-K physical evaluations
    paths["K"] = _write("stage8xnd_tableK_work.csv", [
        {"N": n, "arm": arm,
         "W_total_mean": _summ(_vals(workm, arm, n, "W_total"))["mean"],
         "W_unique_exact_secondary": _summ(
             _vals(workm, arm, n, "W_unique_exact_secondary"))["mean"],
         "exact_duplicates_secondary": _summ(
             _vals(workm, arm, n, "exact_duplicates_secondary"))["mean"]}
        for n in N_GRID for arm in (ARM_PW, ARM_PW_OFFSET, ARM_PC)])

    # ND-L hashes per block
    paths["L"] = _write("stage8xnd_tableL_hashes_per_block.csv", [
        {"N": n, "arm": arm,
         "hashes_per_block_mean": _summ(
             _vals(workm, arm, n, "hashes_per_block"))["mean"]}
        for n in N_GRID for arm in (ARM_PW, ARM_PC)])

    # ND-M paired differences
    m_rows = []
    for n in N_GRID:
        for arm in (ARM_PC, ARM_PC_NOLP, ARM_PW_OFFSET):
            for col in (["block_retention", "latency_ratio"]
                        + [f"saving_{c}" for c in ALPHA_CASES]
                        + ["energy_per_block_ratio_LP0"]):
                s = _summ(_vals(pairm, arm, n, col))
                m_rows.append({"N": n, "arm": arm, "metric": col, **s})
    paths["M"] = _write("stage8xnd_tableM_paired.csv", m_rows)

    # ND-N theory vs simulation
    n_rows = []
    for n in N_GRID:
        p = predictions(n)
        def add(q, pred, meas, tol, note=""):
            err = abs(meas - pred) / (abs(pred) if pred else 1.0)
            n_rows.append({"N": n, "quantity": q, "predicted": pred,
                           "measured": meas, "rel_error": err,
                           "within_tolerance": err <= tol, "tolerance": tol,
                           "note": note})
        add("block_retention (paired mean)", 1.0,
            _summ(_vals(pairm, ARM_PC, n, "block_retention"))["mean"], 0.02)
        add("latency_ratio (paired mean)", 1.0,
            _summ(_vals(pairm, ARM_PC, n, "latency_ratio"))["mean"], 0.02)
        add("F_low ND-PC", p["f_low_expected"],
            _summ(_vals(lowm, ARM_PC, n, "F_low"))["mean"], 1e-3)
        add("saving LP0 ND-PC", p["energy_saving_LP0"],
            _summ(_vals(pairm, ARM_PC, n, "saving_LP0"))["mean"], 1e-3)
        add("saving any-alpha ND-PC-NOLP", 0.0,
            _summ(_vals(pairm, ARM_PC_NOLP, n, "saving_LP0"))["mean"], 0.0,
            "exact zero required")
        add("blocks per run ND-PW", p["expected_blocks_per_run"],
            _summ(_vals(svcm, ARM_PW, n, "accepted_blocks"))["mean"], 0.10)
        add("energy_per_block_ratio LP0", 1.0,
            _summ(_vals(pairm, ARM_PC, n, "energy_per_block_ratio_LP0"))
            ["mean"], 1e-4)
        add("domain sweeps per PW miner", T_RUN_S * HASHRATE_HPS
            / NONCE_DOMAIN_SIZE,
            _summ(_vals(noncem, ARM_PW, n, "domain_sweeps_per_miner"))["mean"],
            1e-6)
    paths["N"] = _write("stage8xnd_tableN_theory_vs_sim.csv", n_rows)

    fails = [r for r in n_rows if not r["within_tolerance"]]
    summary = {"theory_checks": len(n_rows), "failures": len(fails),
               "failed": [{k: r[k] for k in ("N", "quantity", "predicted",
                                             "measured")} for r in fails]}
    with open(os.path.join(OUT, "stage8xnd_theory_check_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    paths["check"] = os.path.join(OUT, "stage8xnd_theory_check_summary.json")
    return paths


if __name__ == "__main__":
    for k, v in build_all().items():
        print(k, v)
