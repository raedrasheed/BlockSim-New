#!/usr/bin/env python3
"""Stage 8M — preregistered minimal analysis (executes the FROZEN Stage-6M plan verbatim).

Input: ONLY the frozen Stage-7M tables
    docs/thesis_revision_v45/stage_07m/STAGE_07M_CONFIRMATORY_DATASET.csv   (30 rows)
    docs/thesis_revision_v45/stage_07m/STAGE_07M_EXPLORATORY_SCALE_TABLE.csv (2 rows,
        DESCRIPTIVE ONLY — never enters any estimator, interval or test)

Estimators (frozen in STAGE_06M_ANALYSIS_PLAN.md):
    * exact paired sign-permutation over all 2^10 = 1024 sign assignments,
      one-sided in the preregistered direction (reduction);
    * paired bootstrap, 10 000 resamples of the 10 seeds with replacement,
      percentile 95 % CI (lower = 250th, upper = 9 750th order statistic);
    * analysis seed 13165134141831138817 (root); each named bootstrap uses
      random.Random(f"{ROOT_SEED}:{label}") so results are independent of evaluation order.

Decision rules (frozen in STAGE_06M_PREREGISTRATION.md §7):
    H-M1 PASS  iff  mean per-seed relative reduction >= 0.05
               AND  bootstrap 95 % lower bound of mean(d) > 0     (d = E_null − E_idle)
               AND  exact one-sided permutation p < 0.05
    H-M2       descriptive only (no pass/fail)
    H-M3       four limits; the two paired ratios are evaluated on the MEAN of per-seed
               ratios and ALSO reported per-seed worst-case; the two per-run limits are
               evaluated on EVERY M03 run (strict reading, reported both ways);
               floor_unattainable_count reported honestly.
    Energy claim licensed  iff  H-M1 PASS  AND  H-M3 within limits.

Writes: STAGE_08M_EFFECT_ESTIMATES.csv, STAGE_08M_HYPOTHESIS_DECISIONS.csv,
STAGE_08M_INTEGRITY_RESULTS.csv and stage8m_results.json (full numeric record).
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import pathlib
import random
import statistics
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
S7M = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_07m"
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08m"
DATASET = S7M / "STAGE_07M_CONFIRMATORY_DATASET.csv"
SCALE_TABLE = S7M / "STAGE_07M_EXPLORATORY_SCALE_TABLE.csv"

ROOT_SEED = 13165134141831138817
B = 10_000
N = 10
HORIZON_T = 300.0
BELOW_FLOOR_LIMIT_S = 0.05 * HORIZON_T          # 15 s

GATE_COLUMNS = [
    "maximum_energy_identity_residual_j", "maximum_residency_partition_residual_s",
    "duplicate_nonce_count", "post_round_evaluation_record_count",
    "post_round_evaluation_nonce_count", "evaluation_missing_terminal_time_count",
    "physical_frontier_rewind_count", "work_reward_union_residual",
    "nonterminal_lease_count", "nonterminal_reassignment_request_count",
    "adversarial_action_total", "nonterminal_activation_request_count",
    "power_null_equals_A1_residual_kwh", "offline_residency_s",
]


def load(path: pathlib.Path) -> list:
    with open(path, newline="") as fh:
        return list(csv.DictReader(fh))


def by_scenario(rows: list, sid: str) -> list:
    out = sorted((r for r in rows if r["scenario_id"] == sid),
                 key=lambda r: int(r["seed_index"]))
    assert len(out) == N and [int(r["seed_index"]) for r in out] == list(range(N))
    return out


# ------------------------------------------------------------------ frozen estimators
def exact_sign_permutation_p(d: list) -> float:
    """One-sided p over ALL 2^10 sign assignments: P(mean(s*d) >= mean(d))."""
    obs = statistics.fmean(d)
    count = 0
    for mask in range(1 << len(d)):
        m = statistics.fmean(x if (mask >> i) & 1 == 0 else -x
                             for i, x in enumerate(d))
        if m >= obs - 1e-15:            # observed assignment (all +1) always counts
            count += 1
    return count / (1 << len(d))


def percentile_ci_explicit(samples: list) -> tuple:
    s = sorted(samples)
    return s[249], s[9749]               # 250th and 9750th order statistics of 10 000


def paired_bootstrap(values_per_seed: list, label: str, stat=statistics.fmean) -> dict:
    rng = random.Random(f"{ROOT_SEED}:{label}")
    stats = []
    n = len(values_per_seed)
    for _ in range(B):
        idx = [rng.randrange(n) for _ in range(n)]
        stats.append(stat([values_per_seed[i] for i in idx]))
    lo, hi = percentile_ci_explicit(stats)
    return {"mean": statistics.fmean(values_per_seed),
            "median": statistics.median(values_per_seed),
            "ci95_lower": lo, "ci95_upper": hi, "resamples": B, "label": label}


def paired_contrast(rows: list, label_prefix: str) -> dict:
    """The within-run power-null contrast for one scenario's 10 paired seeds."""
    d = [float(r["E_power_null_kwh"]) - float(r["E_idle_kwh"]) for r in rows]
    rel = [float(r["relative_reduction"]) for r in rows]
    boot_d = paired_bootstrap(d, f"{label_prefix}:mean_abs_reduction_kwh")
    boot_rel = paired_bootstrap(rel, f"{label_prefix}:mean_relative_reduction")
    return {
        "n_seeds": len(d),
        "E_idle_kwh_per_seed": [float(r["E_idle_kwh"]) for r in rows],
        "E_power_null_kwh_per_seed": [float(r["E_power_null_kwh"]) for r in rows],
        "d_kwh_per_seed": d,
        "relative_reduction_per_seed": rel,
        "mean_d_kwh": boot_d["mean"], "median_d_kwh": statistics.median(d),
        "ci95_d_kwh": [boot_d["ci95_lower"], boot_d["ci95_upper"]],
        "mean_relative_reduction": boot_rel["mean"],
        "median_relative_reduction": boot_rel["median"],
        "ci95_relative_reduction": [boot_rel["ci95_lower"], boot_rel["ci95_upper"]],
        "exact_sign_permutation_p_one_sided": exact_sign_permutation_p(d),
        "permutation_assignments": 1 << len(d),
    }


# ------------------------------------------------------------------ integrity
def integrity_rows(rows: list) -> tuple:
    out, all_ok = [], True
    for r in rows:
        ok = (r["run_status"] == "COMPLETED" and r["all_integrity_gates_pass"] == "True")
        all_ok &= ok
        out.append({"run_id": r["run_id"], "scenario_id": r["scenario_id"],
                    "seed_index": r["seed_index"], "run_status": r["run_status"],
                    "all_integrity_gates_pass": r["all_integrity_gates_pass"],
                    **{c: r[c] for c in GATE_COLUMNS}})
    return out, all_ok


def main() -> int:
    rows = load(DATASET)
    assert len(rows) == 30, "the frozen confirmatory dataset must have exactly 30 rows"
    assert all(r["role"] == "CONFIRMATORY" for r in rows)
    scale = load(SCALE_TABLE)
    assert len(scale) == 2 and all(r["role"] == "EXPLORATORY_SCALE_CHECK" for r in scale)
    dataset_sha = hashlib.sha256(DATASET.read_bytes()).hexdigest()

    m01 = by_scenario(rows, "M01_HET_IDLE")
    m02 = by_scenario(rows, "M02_HOM_IDLE")
    m03 = by_scenario(rows, "M03_HET_IDLE_FLOOR")

    # ---- deterministic gates first: any failure blocks inference -------------------
    integ, integ_ok = integrity_rows(rows)
    if not integ_ok:
        print("STAGE_8M_BLOCKED — integrity gate failure in the frozen dataset")
        return 2

    # ---- H-M1 ----------------------------------------------------------------------
    hm1 = paired_contrast(m01, "HM1")
    hm1_pass_rel = hm1["mean_relative_reduction"] >= 0.05
    hm1_pass_ci = hm1["ci95_d_kwh"][0] > 0.0
    hm1_pass_p = hm1["exact_sign_permutation_p_one_sided"] < 0.05
    hm1_pass = hm1_pass_rel and hm1_pass_ci and hm1_pass_p

    # ---- H-M2 (descriptive) --------------------------------------------------------
    hm2 = paired_contrast(m02, "HM2")

    # ---- H-M3 ----------------------------------------------------------------------
    blocks_ratio = [int(t["rounds_accepted"]) / int(c["rounds_accepted"])
                    for t, c in zip(m03, m01)]
    dur_ratio = [float(t["median_round_duration"]) / float(c["median_round_duration"])
                 for t, c in zip(m03, m01)]
    below_floor = [float(t["total_duration_below_floor"]) for t in m03]
    unattain = [int(t["floor_unattainable_count"]) for t in m03]
    nonterm = [int(t["nonterminal_activation_request_count"]) for t in m03]
    boot_blocks = paired_bootstrap(blocks_ratio, "HM3:accepted_blocks_ratio")
    boot_dur = paired_bootstrap(dur_ratio, "HM3:median_round_duration_ratio")
    lim = {
        "accepted_blocks_ratio_mean_ge_0.90": boot_blocks["mean"] >= 0.90,
        "accepted_blocks_ratio_all_seeds_ge_0.90": min(blocks_ratio) >= 0.90,
        "median_round_duration_ratio_mean_le_1.10": boot_dur["mean"] <= 1.10,
        "median_round_duration_ratio_all_seeds_le_1.10": max(dur_ratio) <= 1.10,
        "total_duration_below_floor_le_15s_every_run": max(below_floor) <= BELOW_FLOOR_LIMIT_S,
        "total_duration_below_floor_le_15s_mean": (
            statistics.fmean(below_floor) <= BELOW_FLOOR_LIMIT_S),
        "nonterminal_activation_request_count_zero_every_run": max(nonterm) == 0,
    }
    # the preregistered verdict: mean reading for the two ratios, strict per-run reading
    # for the two per-run limits (the stricter reading is also reported above)
    hm3_within = (lim["accepted_blocks_ratio_mean_ge_0.90"]
                  and lim["median_round_duration_ratio_mean_le_1.10"]
                  and lim["total_duration_below_floor_le_15s_every_run"]
                  and lim["nonterminal_activation_request_count_zero_every_run"])
    hm3 = {
        "accepted_blocks_ratio_per_seed": blocks_ratio,
        "accepted_blocks_ratio": boot_blocks,
        "median_round_duration_ratio_per_seed": dur_ratio,
        "median_round_duration_ratio": boot_dur,
        "total_duration_below_floor_s_per_seed": below_floor,
        "total_duration_below_floor_s_mean": statistics.fmean(below_floor),
        "total_duration_below_floor_s_max": max(below_floor),
        "floor_unattainable_count_per_seed": unattain,
        "floor_unattainable_count_total": sum(unattain),
        "nonterminal_activation_request_count_per_seed": nonterm,
        "limits": lim, "within_limits": hm3_within,
    }

    energy_claim_licensed = hm1_pass and hm3_within

    # ---- scale checks: DESCRIPTIVE numbers only ------------------------------------
    scale_desc = [{
        "scenario_id": r["scenario_id"], "seed_class": r["seed_class"],
        "seed_index": r["seed_index"], "run_status": r["run_status"],
        "all_integrity_gates_pass": r["all_integrity_gates_pass"],
        "E_idle_kwh": float(r["E_idle_kwh"]),
        "E_power_null_kwh": float(r["E_power_null_kwh"]),
        "relative_reduction": float(r["relative_reduction"]),
        "rounds_accepted": int(r["rounds_accepted"]),
        "total_duration_below_floor": float(r["total_duration_below_floor"]),
        "floor_unattainable_count": int(r["floor_unattainable_count"]),
        "wall_clock_seconds": float(r["wall_clock_seconds"]),
        "peak_rss_mb": float(r["peak_rss_mb"]),
    } for r in scale]

    results = {
        "harness": "analyze_8m.py",
        "input_dataset": str(DATASET.relative_to(REPO_ROOT)),
        "input_dataset_sha256": dataset_sha,
        "analysis_seed_root": ROOT_SEED,
        "bootstrap_resamples": B,
        "percentile_convention": "lower = 250th, upper = 9750th order statistic of 10000",
        "H_M1": {**hm1, "criteria": {
            "mean_relative_reduction_ge_0.05": hm1_pass_rel,
            "bootstrap_ci95_lower_of_mean_d_gt_0": hm1_pass_ci,
            "exact_permutation_p_lt_0.05": hm1_pass_p},
            "decision": "PASS" if hm1_pass else "FAIL"},
        "H_M2": {**hm2, "decision": "DESCRIPTIVE_ONLY"},
        "H_M3": {**hm3, "decision": ("WITHIN_LIMITS" if hm3_within
                                     else "LIMITS_EXCEEDED")},
        "energy_claim_licensed": energy_claim_licensed,
        "integrity_all_pass": integ_ok,
        "exploratory_scale_checks_descriptive": scale_desc,
    }

    DOCS.mkdir(parents=True, exist_ok=True)
    (HERE / "stage8m_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True) + "\n")

    # ---- STAGE_08M_EFFECT_ESTIMATES.csv --------------------------------------------
    eff = []
    for name, c in (("H-M1 (M01 vs within-run power null)", hm1),
                    ("H-M2 (M02 vs within-run power null)", hm2)):
        eff.append({
            "contrast": name, "n_seeds": c["n_seeds"],
            "mean_abs_reduction_kwh": c["mean_d_kwh"],
            "median_abs_reduction_kwh": c["median_d_kwh"],
            "ci95_abs_lower_kwh": c["ci95_d_kwh"][0],
            "ci95_abs_upper_kwh": c["ci95_d_kwh"][1],
            "mean_relative_reduction": c["mean_relative_reduction"],
            "median_relative_reduction": c["median_relative_reduction"],
            "ci95_rel_lower": c["ci95_relative_reduction"][0],
            "ci95_rel_upper": c["ci95_relative_reduction"][1],
            "exact_sign_permutation_p_one_sided": c["exact_sign_permutation_p_one_sided"],
        })
    for name, b, per in (("H-M3 accepted_blocks ratio (M03/M01)", boot_blocks, blocks_ratio),
                         ("H-M3 median_round_duration ratio (M03/M01)", boot_dur, dur_ratio)):
        eff.append({"contrast": name, "n_seeds": N,
                    "mean_abs_reduction_kwh": "", "median_abs_reduction_kwh": "",
                    "ci95_abs_lower_kwh": "", "ci95_abs_upper_kwh": "",
                    "mean_relative_reduction": b["mean"],
                    "median_relative_reduction": b["median"],
                    "ci95_rel_lower": b["ci95_lower"], "ci95_rel_upper": b["ci95_upper"],
                    "exact_sign_permutation_p_one_sided": "deterministic limit (no p-value)"})
    write_csv(DOCS / "STAGE_08M_EFFECT_ESTIMATES.csv", eff)

    # ---- STAGE_08M_HYPOTHESIS_DECISIONS.csv ----------------------------------------
    dec = [
        {"hypothesis": "H-M1", "criterion": "mean relative reduction >= 5 %",
         "value": f"{hm1['mean_relative_reduction']:.6f}",
         "pass": hm1_pass_rel},
        {"hypothesis": "H-M1", "criterion": "paired-bootstrap 95 % lower bound of mean(d) > 0",
         "value": f"{hm1['ci95_d_kwh'][0]:.9f} kWh", "pass": hm1_pass_ci},
        {"hypothesis": "H-M1", "criterion": "exact one-sided sign-permutation p < 0.05",
         "value": f"{hm1['exact_sign_permutation_p_one_sided']:.6f}", "pass": hm1_pass_p},
        {"hypothesis": "H-M1", "criterion": "DECISION",
         "value": results["H_M1"]["decision"], "pass": hm1_pass},
        {"hypothesis": "H-M2", "criterion": "DESCRIPTIVE_ONLY (no pass/fail preregistered)",
         "value": f"mean rel {hm2['mean_relative_reduction']:.6f}", "pass": ""},
        {"hypothesis": "H-M3", "criterion": "accepted_blocks ratio mean >= 0.90",
         "value": f"{boot_blocks['mean']:.6f} (per-seed min {min(blocks_ratio):.6f})",
         "pass": lim["accepted_blocks_ratio_mean_ge_0.90"]},
        {"hypothesis": "H-M3", "criterion": "median_round_duration ratio mean <= 1.10",
         "value": f"{boot_dur['mean']:.6f} (per-seed max {max(dur_ratio):.6f})",
         "pass": lim["median_round_duration_ratio_mean_le_1.10"]},
        {"hypothesis": "H-M3", "criterion": "total_duration_below_floor <= 15 s (every run)",
         "value": f"max {max(below_floor):.6f} s, mean {statistics.fmean(below_floor):.6f} s",
         "pass": lim["total_duration_below_floor_le_15s_every_run"]},
        {"hypothesis": "H-M3", "criterion": "nonterminal_activation_request_count == 0",
         "value": str(max(nonterm)), "pass":
         lim["nonterminal_activation_request_count_zero_every_run"]},
        {"hypothesis": "H-M3", "criterion": "floor_unattainable_count (reported honestly)",
         "value": f"total {sum(unattain)} across 10 runs; per-seed {unattain}", "pass": ""},
        {"hypothesis": "H-M3", "criterion": "DECISION",
         "value": results["H_M3"]["decision"], "pass": hm3_within},
        {"hypothesis": "ENERGY CLAIM", "criterion": "H-M1 PASS AND H-M3 within limits",
         "value": "LICENSED" if energy_claim_licensed else "NOT LICENSED",
         "pass": energy_claim_licensed},
    ]
    write_csv(DOCS / "STAGE_08M_HYPOTHESIS_DECISIONS.csv", dec)

    # ---- STAGE_08M_INTEGRITY_RESULTS.csv -------------------------------------------
    write_csv(DOCS / "STAGE_08M_INTEGRITY_RESULTS.csv", integ)

    print(json.dumps({k: results[k] for k in
                      ("energy_claim_licensed", "integrity_all_pass")}, indent=1))
    print(f"H-M1: {results['H_M1']['decision']}  "
          f"mean rel {hm1['mean_relative_reduction']:.4f}  "
          f"p {hm1['exact_sign_permutation_p_one_sided']:.6f}  "
          f"CI(d) [{hm1['ci95_d_kwh'][0]:.6f}, {hm1['ci95_d_kwh'][1]:.6f}] kWh")
    print(f"H-M2: mean rel {hm2['mean_relative_reduction']:.4f}  "
          f"CI rel [{hm2['ci95_relative_reduction'][0]:.4f}, "
          f"{hm2['ci95_relative_reduction'][1]:.4f}]")
    print(f"H-M3: {results['H_M3']['decision']}  blocks ratio {boot_blocks['mean']:.4f}  "
          f"dur ratio {boot_dur['mean']:.4f}  below-floor max {max(below_floor):.2f}s  "
          f"unattainable {sum(unattain)}")
    return 0


def write_csv(dest: pathlib.Path, rows: list) -> None:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    dest.write_text(buf.getvalue())
    print(f"wrote {dest.relative_to(REPO_ROOT)} ({len(rows)} rows)")


if __name__ == "__main__":
    raise SystemExit(main())
