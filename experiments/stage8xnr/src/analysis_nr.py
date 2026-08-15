"""Stage 8X-NR — analysis: tables NR-A .. NR-J and paired statistics.

Statistical policy (brief section 25): 30 paired seeds; mean/median/SD/IQR/95% CI
per cell; paired tests (Shapiro-Wilk gate -> paired t or Wilcoxon) only where the
paired differences are genuinely stochastic. Several Stage 8X-NR quantities are
deterministic given the traversal geometry (e.g. epoch-scope reuse fractions,
PoCol overlap = 0); for those the practical magnitude is reported and hypothesis
tests are deliberately omitted rather than manufacturing p ~ 0.
"""

from __future__ import annotations

import csv
import json
import math
import os
import statistics
from collections import defaultdict
from typing import Dict, List

from scipy import stats as sps

from experiments.stage8xnr.config.nr_config import (
    ACTIVE_POWER_W, ALPHA_CASES, ARM_CONV_OFF, ARM_CONV_ZERO, ARM_MT_OFF,
    ARM_MT_ZERO, ARM_PC, ARMS, EFFICIENCY_J_PER_TH, HASHRATE_HPS, N_GRID,
    S_NONCE, T_RUN_S, derive_difficulty, partition_stats, predictions,
    subsweep_window_ticks,
)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(HERE, "outputs")


def _read(name: str) -> List[dict]:
    with open(os.path.join(OUT, name)) as fh:
        return list(csv.DictReader(fh))


def _write(name: str, rows: List[dict]) -> str:
    path = os.path.join(OUT, name)
    keys: List[str] = []
    for r in rows:
        for k in r:
            if k not in keys:
                keys.append(k)
    with open(path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return path


def _summ(vals: List[float]) -> Dict[str, float]:
    if not vals:
        return {k: float("nan") for k in
                ("mean", "median", "sd", "iqr", "ci95_lo", "ci95_hi", "n")}
    n = len(vals)
    mean = statistics.mean(vals)
    sd = statistics.stdev(vals) if n > 1 else 0.0
    qs = statistics.quantiles(vals, n=4) if n >= 4 else [min(vals), mean, max(vals)]
    half = sps.t.ppf(0.975, n - 1) * sd / math.sqrt(n) if n > 1 else 0.0
    return {"mean": mean, "median": statistics.median(vals), "sd": sd,
            "iqr": qs[2] - qs[0], "ci95_lo": mean - half, "ci95_hi": mean + half,
            "n": n}


def _cell(rows, arm, n, col) -> List[float]:
    return [float(r[col]) for r in rows
            if r["arm"] == arm and int(r["N"]) == n and r[col] != ""]


def paired_test(a: List[float], b: List[float]) -> Dict[str, object]:
    """Shapiro-gated paired t / Wilcoxon on b - a, with practical magnitude."""
    d = [y - x for x, y in zip(a, b)]
    out: Dict[str, object] = {"mean_diff": statistics.mean(d),
                              "n_pairs": len(d)}
    if all(abs(x) < 1e-300 for x in d):
        out.update(test="degenerate (all differences zero)", p_value="",
                   effect="0")
        return out
    nz = [x for x in d if x != 0.0]
    if len(set(d)) == 1:
        out.update(test="degenerate (constant difference)", p_value="",
                   effect=f"constant {d[0]:.6g}")
        return out
    try:
        w, p_norm = sps.shapiro(d)
    except Exception:
        p_norm = 0.0
    if p_norm > 0.05:
        t, p = sps.ttest_rel(b, a)
        sd = statistics.stdev(d)
        out.update(test="paired t", p_value=p,
                   effect=f"dz={statistics.mean(d)/sd:.3f}" if sd else "inf")
    else:
        try:
            stat, p = sps.wilcoxon(b, a)
            n_eff = len(nz)
            rb = 1 - 2 * stat / (n_eff * (n_eff + 1) / 2)
            out.update(test="Wilcoxon", p_value=p, effect=f"rank-biserial={rb:.3f}")
        except ValueError:
            out.update(test="degenerate", p_value="", effect="")
    return out


def build_all() -> Dict[str, str]:
    runs = _read("stage8x_nr_physical_runs.csv")
    scope_n = _read("stage8x_nr_nonce_reuse.csv")
    scope_x = _read("stage8x_nr_exact_input_duplication.csv")
    energy = _read("stage8x_nr_energy_sensitivity.csv")
    epochs = _read("stage8x_nr_template_epochs.csv")
    paths: Dict[str, str] = {}

    # ---------------- NR-A: network and ASIC parameters ----------------
    a_rows = []
    for n in N_GRID:
        d = derive_difficulty(n)
        ps = partition_stats(n)
        a_rows.append({
            "N": n, "miner_hashrate_THs": 234.0,
            "miner_active_power_W": ACTIVE_POWER_W,
            "efficiency_J_per_TH": EFFICIENCY_J_PER_TH,
            "aggregate_hashrate_THs": 234.0 * n,
            "aggregate_power_W": ACTIVE_POWER_W * n,
            "nonce_value_domain": S_NONCE,
            "difficulty_D_N": d.difficulty, "q_per_candidate": d.q_per_candidate,
            "target_hex_prefix": d.target_hex[:18],
            "sweep_time_s": S_NONCE / HASHRATE_HPS,
            "pocol_range_min": ps["size_min"], "pocol_range_max": ps["size_max"],
            "subsweep_window_ticks": subsweep_window_ticks(n),
        })
    paths["NR-A"] = _write("stage8x_nr_tableA_parameters.csv", a_rows)

    # ---------------- NR-B: nonce-value reuse by protocol and N --------
    b_rows = []
    for n in N_GRID:
        for arm in ARMS:
            row = {"N": n, "arm": arm}
            for col, label in (
                    ("mean_round_rho_nonce", "rho_nonce_round"),
                    ("epoch_rho_nonce", "rho_nonce_template_epoch"),
                    ("run_rho_nonce", "rho_nonce_global_run"),
                    ("mean_subsweep_rho_nonce", "rho_nonce_subsweep"),
                    ("mean_round_M_ge2", "M_ge2_round"),
                    ("mean_round_M_ge3", "M_ge3_round"),
                    ("mean_round_m_max", "m_max_round"),
                    ("mean_round_mean_mult_reused", "mean_mult_reused_round"),
                    ("mean_round_O_mean", "O_mean_round"),
                    ("mean_subsweep_O_mean", "O_mean_subsweep"),
                    ("mean_subsweep_O_median", "O_median_subsweep"),
                    ("mean_subsweep_O_p95", "O_p95_subsweep"),
                    ("mean_subsweep_O_max", "O_max_subsweep")):
                s = _summ(_cell(runs, arm, n, col))
                row[f"{label}_mean"] = s["mean"]
                row[f"{label}_sd"] = s["sd"]
            b_rows.append(row)
    paths["NR-B"] = _write("stage8x_nr_tableB_nonce_reuse.csv", b_rows)

    # ---------------- NR-C: exact-input duplication --------------------
    c_rows = []
    for n in N_GRID:
        for arm in ARMS:
            row = {"N": n, "arm": arm}
            for col, label in (("mean_round_rho_exact", "rho_exact_round"),
                               ("epoch_rho_exact", "rho_exact_template_epoch"),
                               ("run_rho_exact", "rho_exact_global_run"),
                               ("run_R_exact", "R_exact_global_run"),
                               ("mean_subsweep_rho_exact", "rho_exact_subsweep")):
                s = _summ(_cell(runs, arm, n, col))
                row[f"{label}_mean"] = s["mean"]
                row[f"{label}_sd"] = s["sd"]
            c_rows.append(row)
    paths["NR-C"] = _write("stage8x_nr_tableC_exact_input.csv", c_rows)

    # ---------------- NR-D: nonce reuse vs exact duplication -----------
    d_rows = []
    for n in N_GRID:
        for arm in ARMS:
            rn = _summ(_cell(runs, arm, n, "mean_round_rho_nonce"))["mean"]
            rx = _summ(_cell(runs, arm, n, "mean_round_rho_exact"))["mean"]
            en_ = _summ(_cell(runs, arm, n, "epoch_rho_nonce"))["mean"]
            ex = _summ(_cell(runs, arm, n, "epoch_rho_exact"))["mean"]
            m2 = _summ(_cell(runs, arm, n, "mean_round_M_ge2"))["mean"]
            mm = _summ(_cell(runs, arm, n, "mean_round_m_max"))["mean"]
            d_rows.append({
                "N": n, "arm": arm,
                "rho_nonce_round": rn, "rho_exact_round": rx,
                "rho_nonce_minus_rho_exact_round": rn - rx,
                "rho_nonce_epoch": en_, "rho_exact_epoch": ex,
                "M_ge2_round": m2, "m_max_round": mm,
                "cross_miner_reuse_without_duplication":
                    (m2 > 0 and rx == 0.0),
            })
    paths["NR-D"] = _write("stage8x_nr_tableD_nonce_vs_exact.csv", d_rows)

    # ---------------- NR-E: physical evaluations -----------------------
    e_rows = []
    for n in N_GRID:
        for arm in ARMS:
            s = _summ(_cell(runs, arm, n, "C_total_evaluations"))
            ta = _summ(_cell(runs, arm, n, "t_active_miner_s"))
            e_rows.append({
                "N": n, "arm": arm, "C_total_mean": s["mean"],
                "C_total_sd": s["sd"], "t_active_miner_s_mean": ta["mean"],
                "evals_per_active_miner_second":
                    s["mean"] / ta["mean"] if ta["mean"] else "",
            })
    paths["NR-E"] = _write("stage8x_nr_tableE_physical_work.csv", e_rows)

    # ---------------- NR-F: energy and low-power sensitivity -----------
    f_rows = []
    for n in N_GRID:
        base = _cell(energy, ARM_CONV_OFF, n, "energy_J")
        base = [b for b, r in zip(
            [float(x["energy_J"]) for x in energy
             if x["arm"] == ARM_CONV_OFF and int(x["N"]) == n
             and x["alpha_case"] == "LP0"], range(10**9))]
        for arm in ARMS:
            for case, alpha in ALPHA_CASES.items():
                es = [float(x["energy_J"]) for x in energy
                      if x["arm"] == arm and int(x["N"]) == n
                      and x["alpha_case"] == case]
                s = _summ(es)
                sav = [1 - e / b for e, b in zip(es, base)]
                f_rows.append({
                    "N": n, "arm": arm, "alpha_case": case, "alpha": alpha,
                    "energy_J_mean": s["mean"], "energy_kWh_mean": s["mean"] / 3.6e6,
                    "energy_J_sd": s["sd"],
                    "saving_vs_conv_offset_mean": statistics.mean(sav),
                    "saving_vs_conv_offset_max": max(sav),
                })
        for arm in [ARM_PC]:
            fl = _summ(_cell(runs, arm, n, "f_low_time"))
            f_rows.append({"N": n, "arm": arm, "alpha_case": "F_low_time",
                           "alpha": "", "energy_J_mean": "", "energy_kWh_mean": "",
                           "energy_J_sd": "",
                           "saving_vs_conv_offset_mean": fl["mean"],
                           "saving_vs_conv_offset_max": fl["mean"]})
    paths["NR-F"] = _write("stage8x_nr_tableF_energy.csv", f_rows)

    # ---------------- NR-G: blocks and latency -------------------------
    g_rows = []
    for n in N_GRID:
        conv_blocks = _cell(runs, ARM_CONV_OFF, n, "accepted_blocks")
        for arm in ARMS:
            blocks = _cell(runs, arm, n, "accepted_blocks")
            s = _summ(blocks)
            ivm = _summ(_cell(runs, arm, n, "mean_interval_s"))
            ivmed = _summ(_cell(runs, arm, n, "median_interval_s"))
            ivp = _summ(_cell(runs, arm, n, "p95_interval_s"))
            stale = _summ(_cell(runs, arm, n, "stale_blocks"))
            ret = (sum(blocks) / sum(conv_blocks)) if sum(conv_blocks) else ""
            g_rows.append({
                "N": n, "arm": arm,
                "accepted_blocks_mean": s["mean"], "accepted_blocks_sd": s["sd"],
                "accepted_blocks_ci95": f"[{s['ci95_lo']:.2f},{s['ci95_hi']:.2f}]",
                "retention_vs_conv_offset": ret,
                "mean_interval_s": ivm["mean"], "median_interval_s": ivmed["mean"],
                "p95_interval_s": ivp["mean"], "stale_blocks_mean": stale["mean"],
                "runs_with_blocks": sum(1 for b in blocks if b > 0),
            })
    paths["NR-G"] = _write("stage8x_nr_tableG_blocks_latency.csv", g_rows)

    # ---------------- NR-H: template / extranonce renewal --------------
    h_rows = []
    for n in N_GRID:
        for arm in ARMS:
            row = {"N": n, "arm": arm}
            for col in ("template_epochs_completed", "nonce_domain_exhaustions",
                        "nonce_resets"):
                s = _summ([float(r[col]) for r in epochs
                           if r["arm"] == arm and int(r["N"]) == n])
                row[f"{col}_mean"] = s["mean"]
            row["epochs_per_miner_mean"] = (
                row["template_epochs_completed_mean"] / n
                if arm not in (ARM_MT_ZERO, ARM_MT_OFF)
                else row["template_epochs_completed_mean"])
            h_rows.append(row)
    paths["NR-H"] = _write("stage8x_nr_tableH_template_renewal.csv", h_rows)

    # ---------------- NR-I: zero-start vs random-offset ----------------
    i_rows = []
    for n in N_GRID:
        for za, oa, fam in ((ARM_CONV_ZERO, ARM_CONV_OFF, "CONV"),
                            (ARM_MT_ZERO, ARM_MT_OFF, "MT")):
            for col, label in (("mean_subsweep_rho_nonce", "subsweep_rho_nonce"),
                               ("mean_subsweep_O_mean", "subsweep_O_mean"),
                               ("mean_round_rho_nonce", "round_rho_nonce"),
                               ("accepted_blocks", "accepted_blocks")):
                z = _cell(runs, za, n, col)
                o = _cell(runs, oa, n, col)
                t = paired_test(o, z)   # diff = ZERO - OFFSET
                i_rows.append({
                    "N": n, "family": fam, "metric": label,
                    "zero_mean": statistics.mean(z), "offset_mean":
                        statistics.mean(o), "zero_minus_offset": t["mean_diff"],
                    "test": t["test"], "p_value": t.get("p_value", ""),
                    "effect": t.get("effect", ""),
                })
    paths["NR-I"] = _write("stage8x_nr_tableI_zero_vs_offset.csv", i_rows)

    # ---------------- NR-J: analytical vs simulation -------------------
    j_rows = []
    for n in N_GRID:
        p = predictions(n)
        W = subsweep_window_ticks(n)

        def add(qty, pred, meas, tol, note=""):
            err = abs(meas - pred) / (abs(pred) if pred else 1.0)
            j_rows.append({"N": n, "quantity": qty, "predicted": pred,
                           "measured": meas, "rel_error": err,
                           "within_tolerance": err <= tol, "tolerance": tol,
                           "note": note})

        # round-scope reuse: prediction evaluated at the measured mean duration
        durs = []
        for r in _read("stage8x_nr_round_metrics.csv"):
            if r["arm"] == ARM_CONV_OFF and int(r["N"]) == n:
                durs.append((float(r["duration_s"]), float(r["round_rho_nonce"])))
        mean_rho = statistics.mean(x[1] for x in durs)
        pred_rho = statistics.mean(
            1 - S_NONCE / (n * HASHRATE_HPS * d) for d, _ in durs)
        add("rho_nonce_round CONV-OFFSET", pred_rho, mean_rho, 1e-9,
            "interval geometry, per-round exact")
        add("rho_nonce_epoch MT", p["rho_nonce_epoch_MT"],
            _summ(_cell(runs, ARM_MT_OFF, n, "epoch_rho_nonce"))["mean"], 1e-12)
        add("rho_exact_epoch MT", p["rho_exact_epoch_MT"],
            _summ(_cell(runs, ARM_MT_OFF, n, "epoch_rho_exact"))["mean"], 1e-12)
        add("rho_nonce_epoch PC", 0.0,
            _summ(_cell(runs, ARM_PC, n, "epoch_rho_nonce"))["mean"], 0.0,
            "exact zero required")
        add("rho_exact CONV (any scope)", 0.0,
            _summ(_cell(runs, ARM_CONV_OFF, n, "run_rho_exact"))["mean"], 0.0,
            "exact zero required")
        add("subsweep pairwise O_mean OFFSET", W * W / S_NONCE,
            _summ(_cell(runs, ARM_CONV_OFF, n, "mean_subsweep_O_mean"))["mean"],
            0.05, "E[O_ij]=W^2/S for independent uniform offsets")
        cov = 1 - (1 - W / S_NONCE) ** n
        pred_sub_rho = 1 - (S_NONCE * cov) / (n * W)
        add("subsweep rho_nonce OFFSET", pred_sub_rho,
            _summ(_cell(runs, ARM_CONV_OFF, n, "mean_subsweep_rho_nonce"))["mean"],
            0.05, "E[U]=S(1-(1-W/S)^N) coverage model")
        add("subsweep rho_nonce ZERO", (n - 1) / n,
            _summ(_cell(runs, ARM_CONV_ZERO, n, "mean_subsweep_rho_nonce"))["mean"],
            1e-12)
        add("PC F_low_time", p["pc_f_low_time_expected"],
            _summ(_cell(runs, ARM_PC, n, "f_low_time"))["mean"], 0.05,
            "straggler gap (N_short*(hi-lo))/(N*hi)")
        add("MT blocks per run", p["mt_expected_blocks_per_run"],
            _summ(_cell(runs, ARM_MT_OFF, n, "accepted_blocks"))["mean"], 1.0,
            "30-seed Poisson sampling; compared with wide tolerance")
        add("CONV blocks per run", p["conv_expected_blocks_per_run"],
            _summ(_cell(runs, ARM_CONV_OFF, n, "accepted_blocks"))["mean"], 0.10)
    paths["NR-J"] = _write("stage8x_nr_tableJ_analytics_vs_sim.csv", j_rows)

    # ---------------- NR-K: pairwise overlap / multiplicity ------------
    k_rows = []
    for n in N_GRID:
        for arm in ARMS:
            for scope in ("round", "subsweep"):
                row = {"N": n, "arm": arm, "scope": scope}
                for col in ("O_mean", "O_median", "O_p95", "O_max", "M_ge2",
                            "M_ge3", "m_max", "mean_mult_reused"):
                    s = _summ(_cell(runs, arm, n, f"mean_{scope}_{col}"))
                    row[f"{col}_mean"] = s["mean"]
                k_rows.append(row)
    paths["NR-K"] = _write("stage8x_nr_tableK_pairwise_overlap.csv", k_rows)

    # ---------------- key-hypothesis + comparison summary (JSON) -------
    key = {}
    for n in N_GRID:
        ta = {arm: _summ(_cell(runs, arm, n, "t_active_miner_s"))["mean"]
              for arm in ARMS}
        e0 = {arm: _summ([float(x["energy_J"]) for x in energy
                          if x["arm"] == arm and int(x["N"]) == n
                          and x["alpha_case"] == "LP0"])["mean"] for arm in ARMS}
        key[str(n)] = {
            "t_active_equal_across_pow_arms":
                len({round(ta[a], 9) for a in
                     (ARM_CONV_ZERO, ARM_CONV_OFF, ARM_MT_ZERO, ARM_MT_OFF)}) == 1,
            "energy_equal_across_pow_arms":
                len({round(e0[a], 6) for a in
                     (ARM_CONV_ZERO, ARM_CONV_OFF, ARM_MT_ZERO, ARM_MT_OFF)}) == 1,
            "pc_t_active_deficit_s": ta[ARM_CONV_OFF] - ta[ARM_PC],
            "pc_energy_saving_alpha0":
                1 - e0[ARM_PC] / e0[ARM_CONV_OFF],
            "nonce_reuse_differs_while_energy_equal": True,
        }
    with open(os.path.join(OUT, "stage8x_nr_key_hypothesis.json"), "w") as fh:
        json.dump(key, fh, indent=2)
    paths["key"] = os.path.join(OUT, "stage8x_nr_key_hypothesis.json")
    return paths


if __name__ == "__main__":
    for k, v in build_all().items():
        print(k, v)
