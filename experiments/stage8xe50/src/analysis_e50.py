"""Stage 8X-E50 — analysis: tables E50-A..E50-M, preregistered feasibility
filter, paired statistics.

Feasibility (frozen before Pilot): a point (N, A) is feasible iff
UniqueCoverageRetention >= 0.95 AND pooled BlockRetention >= 0.90 AND pooled
MedianLatencyRatio <= 1.20. Savings are then evaluated per alpha. Per-seed
paired block/latency ratios are NA when the paired MT100 run has zero blocks;
pooled cell values carry explicit block counts so sparse MT100 denominators
(MT100 often has 0-3 blocks in 30 runs at large N) are visible, not hidden.
"""

from __future__ import annotations

import csv
import json
import math
import os
import statistics
from typing import Dict, List

from scipy import stats as sps

from experiments.stage8xe50.config.e50_config import (
    ACTIVE_FRACTIONS, ACTIVE_POWER_W, ALPHA_CASES, ARM_CONV, ARM_MT, ARMS,
    BLOCK_RETENTION_MIN, COVERAGE_RETENTION_MIN, EFFICIENCY_J_PER_TH,
    HASHRATE_HPS, MEDIAN_LATENCY_RATIO_MAX, N_GRID, PC_ARMS, S_NONCE, T_RUN_S,
    active_count, difficulty, epoch_ticks_pc, predictions, q_per_candidate,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")


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


def _vals(rows, arm, n, col, extra=None):
    out = []
    for r in rows:
        if r["arm"] == arm and int(r["N"]) == n and r.get(col, "") not in ("", "NA"):
            if extra and any(r.get(k) != v for k, v in extra.items()):
                continue
            out.append(float(r[col]))
    return out


def _summ(vals):
    if not vals:
        return {"mean": "", "median": "", "sd": "", "iqr": "",
                "ci95_lo": "", "ci95_hi": "", "n": 0}
    n = len(vals)
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if n > 1 else 0.0
    qs = statistics.quantiles(vals, n=4) if n >= 4 else [min(vals), mean, max(vals)]
    half = sps.t.ppf(0.975, n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": mean, "median": statistics.median(vals), "sd": sd,
            "iqr": qs[2] - qs[0], "ci95_lo": mean - half,
            "ci95_hi": mean + half, "n": n}


def build_all():
    runs = _read("stage8xe50_physical_runs.csv")
    cov = _read("stage8xe50_unique_coverage.csv")
    dup = _read("stage8xe50_exact_duplication.csv")
    energy = _read("stage8xe50_energy_sensitivity.csv")
    svc = _read("stage8xe50_service_metrics.csv")
    fair = _read("stage8xe50_fairness.csv")
    pair = _read("stage8xe50_pairwise_seed_metrics.csv")
    paths = {}

    # ---- pooled service per cell (blocks + intervals) --------------------
    pooled = {}
    for n in N_GRID:
        for arm in ARMS:
            blocks = sum(int(r["accepted_blocks"]) for r in svc
                         if r["arm"] == arm and int(r["N"]) == n)
            ivs = []
            for r in svc:
                if r["arm"] == arm and int(r["N"]) == n and r["median_interval_s"]:
                    ivs.append(float(r["median_interval_s"]))
            pooled[(n, arm)] = {
                "blocks": blocks,
                "median_interval": statistics.median(ivs) if ivs else None,
                "runs_with_blocks": len(ivs),
            }

    # ---- E50-A parameters ------------------------------------------------
    a_rows = []
    for n in N_GRID:
        a_rows.append({
            "N": n, "miner_hashrate_THs": 234.0,
            "miner_power_W": ACTIVE_POWER_W, "eta_J_per_TH": EFFICIENCY_J_PER_TH,
            "aggregate_hashrate_THs": 234.0 * n, "difficulty_D_N": difficulty(n),
            "q_per_candidate": q_per_candidate(n),
            "epoch_ticks_MT": S_NONCE, "epoch_ticks_PC": epoch_ticks_pc(n),
            **{f"k_{arm}": active_count(n, arm) for arm in PC_ARMS},
        })
    paths["A"] = _write("stage8xe50_tableA_parameters.csv", a_rows)

    # ---- E50-B MT100 duplication and coverage ---------------------------
    b_rows = []
    for n in N_GRID:
        s_rho = _summ(_vals(dup, ARM_MT, n, "rho_exact"))
        s_u = _summ(_vals(cov, ARM_MT, n, "U_exact"))
        s_c = _summ(_vals(dup, ARM_MT, n, "C_total"))
        b_rows.append({
            "N": n, "C_total_mean": s_c["mean"], "U_exact_mean": s_u["mean"],
            "rho_exact_mean": s_rho["mean"], "rho_exact_sd": s_rho["sd"],
            "rho_exact_predicted": (n - 1) / n,
            "unique_rate_per_s": s_u["mean"] / T_RUN_S,
            "unique_rate_predicted_per_s": HASHRATE_HPS,
        })
    paths["B"] = _write("stage8xe50_tableB_mt100.csv", b_rows)

    # ---- E50-C PoCol coverage by fraction -------------------------------
    c_rows = []
    for n in N_GRID:
        for arm in PC_ARMS:
            s = _summ(_vals(cov, arm, n, "U_exact"))
            c_rows.append({"N": n, "arm": arm, "k": active_count(n, arm),
                           "U_exact_mean": s["mean"],
                           "U_predicted": active_count(n, arm) * HASHRATE_HPS
                           * T_RUN_S,
                           "rho_exact": _summ(_vals(dup, arm, n, "rho_exact"))
                           ["mean"]})
    paths["C"] = _write("stage8xe50_tableC_pocol_coverage.csv", c_rows)

    # ---- E50-D coverage retention ---------------------------------------
    d_rows = []
    for n in N_GRID:
        for arm in PC_ARMS + [ARM_CONV]:
            vals = _vals(cov, arm, n, "coverage_retention_vs_MT100")
            s = _summ(vals)
            d_rows.append({
                "N": n, "arm": arm, **{f"retention_{k}": v for k, v in s.items()},
                "fraction_seeds_ge_095":
                    sum(1 for v in vals if v >= COVERAGE_RETENTION_MIN)
                    / len(vals) if vals else "",
            })
    paths["D"] = _write("stage8xe50_tableD_coverage_retention.csv", d_rows)

    # ---- E50-E energy saving --------------------------------------------
    e_rows = []
    for n in N_GRID:
        for arm in PC_ARMS:
            for case in ALPHA_CASES:
                s = _summ(_vals(energy, arm, n, "saving_vs_MT100",
                                {"alpha_case": case}))
                e_rows.append({"N": n, "arm": arm, "alpha_case": case,
                               "saving_mean": s["mean"], "saving_sd": s["sd"],
                               "saving_predicted":
                               predictions(n, arm)[f"energy_saving_vs_MT_{case}"]})
    paths["E"] = _write("stage8xe50_tableE_energy_saving.csv", e_rows)

    # ---- E50-F block retention (pooled + per-seed NA accounting) --------
    f_rows = []
    for n in N_GRID:
        mtb = pooled[(n, ARM_MT)]["blocks"]
        for arm in PC_ARMS + [ARM_CONV]:
            b = pooled[(n, arm)]["blocks"]
            per_seed = [r for r in pair if r["arm"] == arm and int(r["N"]) == n]
            defined = [float(r["block_ratio"]) for r in per_seed
                       if r["block_ratio"] not in ("", "NA")]
            f_rows.append({
                "N": n, "arm": arm, "pooled_blocks": b, "pooled_MT100_blocks": mtb,
                "pooled_block_retention": b / mtb if mtb else "NA",
                "per_seed_ratios_defined": len(defined),
                "per_seed_ratios_NA": len(per_seed) - len(defined),
                "per_seed_ratio_median": statistics.median(defined)
                if defined else "NA",
            })
    paths["F"] = _write("stage8xe50_tableF_block_retention.csv", f_rows)

    # ---- E50-G latency ---------------------------------------------------
    g_rows = []
    for n in N_GRID:
        mt = pooled[(n, ARM_MT)]
        for arm in PC_ARMS + [ARM_CONV]:
            p = pooled[(n, arm)]
            ratio = (p["median_interval"] / mt["median_interval"]
                     if p["median_interval"] and mt["median_interval"] else "NA")
            g_rows.append({
                "N": n, "arm": arm,
                "pooled_median_interval_s": p["median_interval"] or "NA",
                "MT100_pooled_median_interval_s": mt["median_interval"] or "NA",
                "median_latency_ratio": ratio,
                "runs_with_blocks": p["runs_with_blocks"],
                "MT100_runs_with_blocks": mt["runs_with_blocks"],
                "sparse_MT_denominator": mt["runs_with_blocks"] < 5,
            })
    paths["G"] = _write("stage8xe50_tableG_latency.csv", g_rows)

    # ---- E50-H energy per block -----------------------------------------
    h_rows = []
    for n in N_GRID:
        for arm in ARMS:
            for case in ("LP0", "LP50"):
                vals = _vals(energy, arm, n, "energy_per_block_J",
                             {"alpha_case": case})
                s = _summ(vals)
                mtv = _vals(energy, ARM_MT, n, "energy_per_block_J",
                            {"alpha_case": case})
                h_rows.append({
                    "N": n, "arm": arm, "alpha_case": case,
                    "energy_per_block_J_mean": s["mean"],
                    "runs_with_blocks": s["n"],
                    "ratio_vs_MT100": (s["mean"] / statistics.mean(mtv))
                    if s["n"] and mtv else "NA",
                })
    paths["H"] = _write("stage8xe50_tableH_energy_per_block.csv", h_rows)

    # ---- E50-I low-power residency --------------------------------------
    i_rows = []
    for n in N_GRID:
        for arm in ARMS:
            s = _summ(_vals(runs, arm, n, "F_low"))
            fr = [r for r in fair if r["arm"] == arm and int(r["N"]) == n]
            i_rows.append({
                "N": n, "arm": arm, "F_low_mean": s["mean"],
                "F_low_predicted": (0.0 if arm in (ARM_CONV, ARM_MT)
                                    else 1 - active_count(n, arm) / n),
                "transitions_total_mean": statistics.mean(
                    [float(r["transitions_total"]) for r in fr]),
                "active_episode_s": float(fr[0]["active_episode_s"]),
                "low_episode_s": float(fr[0]["low_episode_s"]),
            })
    paths["I"] = _write("stage8xe50_tableI_low_power.csv", i_rows)

    # ---- E50-J fairness --------------------------------------------------
    j_rows = []
    for n in N_GRID:
        for arm in PC_ARMS:
            fr = [r for r in fair if r["arm"] == arm and int(r["N"]) == n]
            j_rows.append({
                "N": n, "arm": arm,
                "duty_mean_expected": active_count(n, arm) / n,
                "duty_min": float(fr[0]["duty_min"]),
                "duty_max": float(fr[0]["duty_max"]),
                "duty_sd": float(fr[0]["duty_sd"]),
                "jain_index": float(fr[0]["jain_index"]),
                "duty_max_min_ratio": float(fr[0]["duty_max_min_ratio"]),
            })
    paths["J"] = _write("stage8xe50_tableJ_fairness.csv", j_rows)

    # ---- E50-K feasibility filter (preregistered) -----------------------
    k_rows = []
    feasible_points = []
    for n in N_GRID:
        mtb = pooled[(n, ARM_MT)]["blocks"]
        mtmi = pooled[(n, ARM_MT)]["median_interval"]
        for arm in PC_ARMS:
            covr = _summ(_vals(cov, arm, n, "coverage_retention_vs_MT100"))["mean"]
            b = pooled[(n, arm)]["blocks"]
            bret = b / mtb if mtb else None
            mi = pooled[(n, arm)]["median_interval"]
            lat = mi / mtmi if (mi and mtmi) else None
            ok_cov = covr >= COVERAGE_RETENTION_MIN
            ok_blk = bret is not None and bret >= BLOCK_RETENTION_MIN
            ok_lat = lat is not None and lat <= MEDIAN_LATENCY_RATIO_MAX
            feasible = ok_cov and ok_blk and ok_lat
            row = {"N": n, "arm": arm,
                   "coverage_retention": covr, "ok_coverage": ok_cov,
                   "pooled_block_retention": bret if bret is not None else "NA",
                   "ok_blocks": ok_blk,
                   "median_latency_ratio": lat if lat is not None else "NA",
                   "ok_latency": ok_lat,
                   "MT100_pooled_blocks": mtb,
                   "feasible": feasible}
            for case in ALPHA_CASES:
                row[f"saving_{case}"] = _summ(
                    _vals(energy, arm, n, "saving_vs_MT100",
                          {"alpha_case": case}))["mean"]
            k_rows.append(row)
            if feasible:
                feasible_points.append(row)
    paths["K"] = _write("stage8xe50_tableK_feasible_points.csv", k_rows)

    # ---- E50-L MaxEnergySaving under constraints ------------------------
    l_rows = []
    for case in ALPHA_CASES:
        if feasible_points:
            best = max(feasible_points, key=lambda r: r[f"saving_{case}"])
            l_rows.append({"alpha_case": case,
                           "max_energy_saving": best[f"saving_{case}"],
                           "at_N": best["N"], "at_arm": best["arm"],
                           "exceeds_50pct": best[f"saving_{case}"] > 0.50})
        else:
            l_rows.append({"alpha_case": case, "max_energy_saving": "NA",
                           "at_N": "", "at_arm": "", "exceeds_50pct": False})
    paths["L"] = _write("stage8xe50_tableL_max_saving.csv", l_rows)

    # ---- E50-M MaxBlockRetentionAt50 ------------------------------------
    m_rows = []
    for case in ALPHA_CASES:
        qual = [r for r in k_rows
                if r[f"saving_{case}"] != "" and r[f"saving_{case}"] >= 0.50
                and r["pooled_block_retention"] not in ("NA",)]
        if qual:
            best = max(qual, key=lambda r: r["pooled_block_retention"])
            m_rows.append({"alpha_case": case,
                           "max_block_retention_at_50": best[
                               "pooled_block_retention"],
                           "at_N": best["N"], "at_arm": best["arm"],
                           "saving_there": best[f"saving_{case}"],
                           "feasible_there": best["feasible"]})
        else:
            m_rows.append({"alpha_case": case,
                           "max_block_retention_at_50": "NA (no scenario "
                           "reaches 50% saving)", "at_N": "", "at_arm": "",
                           "saving_there": "", "feasible_there": ""})
    paths["M"] = _write("stage8xe50_tableM_retention_at_50.csv", m_rows)

    # ---- paired statistics (per scenario vs MT100) ----------------------
    p_rows = []
    for n in N_GRID:
        for arm in PC_ARMS:
            for col in ("coverage_retention", "saving_LP0", "saving_LP50"):
                vals = [float(r[col]) for r in pair
                        if r["arm"] == arm and int(r["N"]) == n
                        and r[col] not in ("", "NA")]
                s = _summ(vals)
                p_rows.append({"N": n, "arm": arm, "metric": col, **s})
            bvals = [r["block_ratio"] for r in pair
                     if r["arm"] == arm and int(r["N"]) == n]
            defined = [float(v) for v in bvals if v not in ("", "NA")]
            p_rows.append({"N": n, "arm": arm, "metric": "block_ratio_per_seed",
                           **_summ(defined),
                           })
    paths["paired"] = _write("stage8xe50_paired_stats.csv", p_rows)

    summary = {"feasible_points": len(feasible_points),
               "total_points": len(k_rows),
               "max_saving": {r["alpha_case"]: r["max_energy_saving"]
                              for r in l_rows},
               "exceeds_50": {r["alpha_case"]: r["exceeds_50pct"]
                              for r in l_rows}}
    with open(os.path.join(OUT, "stage8xe50_feasibility_summary.json"), "w") as fh:
        json.dump(summary, fh, indent=2)
    paths["summary"] = os.path.join(OUT, "stage8xe50_feasibility_summary.json")
    return paths


if __name__ == "__main__":
    for k, v in build_all().items():
        print(k, v)
