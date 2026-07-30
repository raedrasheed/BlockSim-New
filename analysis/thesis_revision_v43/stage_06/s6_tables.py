#!/usr/bin/env python3
"""Stage 6 — the 12 required publication tables (§16), all machine-readable CSV.

Every table records the physical-run sample size and never presents B3 and C1 as
separate independent samples (they are one physical dataset, label 'B3;C1').
Tables 2 (descriptive_long) and 4/5 (confirmatory_effects) are produced by s6_analysis;
this module writes the remaining tables plus a tables_index.json.
"""
import csv
import json
import os

import numpy as np

import s6_common as C
import s6_stats as S

runs = C.load_runs()
T = os.path.join(C.STAGE6, "tables")
os.makedirs(T, exist_ok=True)
bundle = json.load(open(os.path.join(C.STAGE6, "models", "analysis_bundle.json")))
IDX = []


def write(name, rows, cols):
    with open(os.path.join(T, name), "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=cols)
        w.writeheader()
        w.writerows(rows)
    IDX.append({"table": name, "n_rows": len(rows)})


def by(hid=None, **f):
    out = runs if hid is None else [r for r in runs if r["hypothesis_id"] == hid]
    return [r for r in out if all(r.get(k) == v for k, v in f.items())]


SCEN = [("B0", "B0"), ("B1", "B1"), ("B2", "B2"),
        ("B3;C1", "B3_C1_CONTINUOUS_DISJOINT"), ("C2", "C2")]
BLOCK_NORM = ["effective_block_interval_s", "energy_per_accepted_block_kwh",
              "confirmation_time_proxy_s", "single_height_stales_per_accepted_block"]


# T1 analysis population + NA
def t1():
    rows = []
    for lab, sc in SCEN:
        s = [r for r in runs if r["scenario_id"] == sc]
        zb = sum(1 for r in s if r["accepted_blocks"] == 0)
        row = {"scenario_label": lab, "scenario_id": sc, "physical_runs": len(s),
               "distinct_physical_seeds_note": "one physical run per seed; B3;C1 is one "
               "dataset with two interpretation labels (never double-counted)",
               "zero_block_runs": zb}
        for m in BLOCK_NORM:
            undef = sum(1 for r in s if r.get(m) is None)
            row[f"{m}__defined"] = len(s) - undef
            row[f"{m}__undefined"] = undef
        rows.append(row)
    cols = ["scenario_label", "scenario_id", "physical_runs",
            "distinct_physical_seeds_note", "zero_block_runs"] + \
           [f"{m}__{k}" for m in BLOCK_NORM for k in ("defined", "undefined")]
    write("table01_population_na.csv", rows, cols)


# T3 hypothesis -> test map
def t3():
    rows = [
        ["A1", "accounting invariant (former H2)", "verification (identity)",
         "total_energy_kwh", "B0/B1/B2/B3;C1 continuous, inactive=0, active", 1140,
         "none (deterministic identity)", "none"],
        ["H1", "confirmatory", "seed-CLUSTER permutation + cluster bootstrap CI + Wilcoxon",
         "duplicate_evaluation_rate", "H1;A1 CORE (B0/B1/B2/B3;C1 x5N)", 600,
         "Holm within H1 (3 ordered contrasts)",
         "seed-cluster: 150 physical pairs -> 30 independent seed clusters (uncertainty "
         "from 30 clusters, not 150); N-specific 30 pairs each as robustness"],
        ["H3", "confirmatory", "preregistered per-miner idle-saving identity (direct) + "
         "decomposition identity + magnitude",
         "active/idle/total energy; Sum idle_time*(P_active-P_idle)/3.6e6", 570,
         "n/a (identity)", "per-miner records; seed-matched where contrasted"],
        ["H4", "confirmatory", "equivalence-to-zero (dispersion, idle)",
         "completion_time_std_s, total_idle_time_s", "homogeneous+equal (incl C2 CORE)",
         "varies", "n/a", "n/a"],
        ["H5", "confirmatory", "paired permutation + bootstrap CI + Wilcoxon",
         "completion_time_std_s, total_idle_time_s, total_energy_kwh",
         "H5 SENS_HETERO (B3;C1 & C2, equal vs weighted)", 240,
         "Holm within H5", "seed-matched (miner_count,seed)"],
        ["H6", "confirmatory", "paired permutation + bootstrap CI + Wilcoxon",
         "inactive_domain, exhausted_rounds, effective_block_interval_s, "
         "accepted_blocks, total_energy_kwh, energy_per_accepted_block_kwh",
         "H6 SENS_INACTIVE vs H1;A1 baseline", 180,
         "Holm within H6", "seed-matched vs inactive=0 baseline"],
        ["H7", "SECONDARY DIAGNOSTIC (amended 5B1G)", "count-rate descriptives + seed/run"
         "-cluster bootstrap (NO binomial/Wilson on stale_count); separate binary "
         "any-stale-height diagnostic", "single_height_stales_per_accepted_block; "
         "heights_with_any_stale/accepted_heights",
         "H7 SENS_DELAY vs H1;A1 baseline", 240,
         "not confirmatory", "N kept separate (100,500); delay-matched to baseline"],
        ["H8", "confirmatory", "paired permutation + bootstrap CI + Wilcoxon",
         "exhausted_rounds, template refreshes, effective_block_interval_s",
         "H8 SENS_MU vs H1;A1 baseline", 120,
         "Holm within H8", "seed-matched vs mu=2.0 baseline"],
        ["H5x", "EXPLORATORY", "descriptive only", "completion_time_std_s",
         "H5x EXPLORATORY (hetero_high)", 60, "n/a", "n/a"],
    ]
    cols = ["id", "status", "test", "outcome(s)", "matrix_population",
            "physical_runs", "multiplicity_family", "pairing"]
    write("table03_hypothesis_test_map.csv",
          [dict(zip(cols, r)) for r in rows], cols)


# T6 robustness / sensitivity
def t6():
    rows = []
    for hk in ("H1", "H5", "H6", "H8"):
        for c in bundle[hk]["contrasts"]:
            if c.get("perm_deterministic"):
                stable = "deterministic (design identity)"
            else:
                pp, wp = c.get("perm_p"), c.get("wilcoxon_p")
                sig_perm = (pp is not None and pp < C.ALPHA)
                sig_wil = (wp is not None and wp < C.ALPHA)
                dir_mean = c["mean_diff"]
                dir_hl = c.get("median_diff_hl")
                dir_agree = (dir_mean == 0 and dir_hl == 0) or \
                            (dir_mean * (dir_hl or 0) >= 0)
                stable = "stable" if (sig_perm == sig_wil and dir_agree) else "check"
            rows.append({"hypothesis": hk, "label": c["label"], "outcome": c["outcome"],
                         "mean_diff": c["mean_diff"], "hl_median_diff": c.get("median_diff_hl"),
                         "perm_p": c.get("perm_p"), "wilcoxon_p": c.get("wilcoxon_p"),
                         "p_holm": c.get("p_holm"),
                         "deterministic": c.get("perm_deterministic"),
                         "mean_vs_median_direction_agree":
                             None if c.get("perm_deterministic") else dir_agree,
                         "robustness": stable})
    cols = ["hypothesis", "label", "outcome", "mean_diff", "hl_median_diff", "perm_p",
            "wilcoxon_p", "p_holm", "deterministic",
            "mean_vs_median_direction_agree", "robustness"]
    write("table06_robustness.csv", rows, cols)


# T7 energy decomposition
def t7():
    rows = []
    # A1 anchor row
    rows.append({"config": "continuous full-participation (B0/B1/B2/B3;C1)",
                 "physical_runs": bundle["A1"]["n_continuous_full_participation"],
                 "active_energy_kwh_mean": C.CONTINUOUS_ENERGY_ANCHOR_KWH,
                 "idle_energy_kwh_mean": 0.0, "coord_energy_kwh_mean": 0.0,
                 "total_energy_kwh_mean": C.CONTINUOUS_ENERGY_ANCHOR_KWH,
                 "saving_vs_anchor_kwh_mean": 0.0,
                 "note": "accounting invariant; total = P_total*T exactly"})
    # C2 by allocation x N (idle-bearing)
    for scen_alloc in [("equal", "idle triggers"), ("weighted", "idle ~ 0")]:
        for N in (100, 500):
            s = by("H5", scenario_id="C2", allocation_policy=scen_alloc[0], miner_count=N)
            if not s:
                continue
            ae = np.mean([r["active_energy_kwh"] for r in s])
            ie = np.mean([r["idle_energy_kwh"] for r in s])
            ce = np.mean([r["coordination_energy_kwh"] for r in s])
            te = np.mean([r["total_energy_kwh"] for r in s])
            rows.append({"config": f"C2 hetero {scen_alloc[0]} N={N} ({scen_alloc[1]})",
                         "physical_runs": len(s), "active_energy_kwh_mean": ae,
                         "idle_energy_kwh_mean": ie, "coord_energy_kwh_mean": ce,
                         "total_energy_kwh_mean": te,
                         "saving_vs_anchor_kwh_mean": C.CONTINUOUS_ENERGY_ANCHOR_KWH - te,
                         "note": "idle-driven saving; energy reduction attributable to "
                                 "reduced active power-time, not partitioning"})
    # C2 homogeneous equal (no idle) - saving 0
    hom = by("H3;H4")
    rows.append({"config": "C2 homogeneous equal (idle policy, no early finishers)",
                 "physical_runs": len(hom),
                 "active_energy_kwh_mean": np.mean([r["active_energy_kwh"] for r in hom]),
                 "idle_energy_kwh_mean": 0.0, "coord_energy_kwh_mean": 0.0,
                 "total_energy_kwh_mean": np.mean([r["total_energy_kwh"] for r in hom]),
                 "saving_vs_anchor_kwh_mean": 0.0,
                 "note": "idle never triggers under homogeneous+equal; saving = 0"})
    cols = ["config", "physical_runs", "active_energy_kwh_mean", "idle_energy_kwh_mean",
            "coord_energy_kwh_mean", "total_energy_kwh_mean",
            "saving_vs_anchor_kwh_mean", "note"]
    write("table07_energy_decomposition.csv", rows, cols)


# T8 candidate redundancy
def t8():
    rows = []
    for lab, sc in SCEN[:4]:
        s = by("H1;A1", scenario_id=sc)
        if not s:
            continue
        d_rate = S.describe([r["duplicate_evaluation_rate"] for r in s])
        rows.append({
            "scenario_label": lab, "physical_runs": len(s),
            "total_candidate_evaluations_mean":
                np.mean([r["total_candidate_evaluations"] for r in s]),
            "distinct_candidate_identities_mean":
                np.mean([r["distinct_candidate_identities"] for r in s]),
            "duplicate_evaluations_mean": np.mean([r["duplicate_evaluations"] for r in s]),
            "duplicate_evaluation_rate_mean": d_rate["mean"],
            "duplicate_evaluation_rate_median": d_rate["median"],
            "duplicate_evaluation_rate_ci_lo": d_rate["ci_lo"],
            "duplicate_evaluation_rate_ci_hi": d_rate["ci_hi"],
            "assumption": "idealized immutable common template + disjoint allocation; "
                          "zero duplicates (B3;C1) does NOT generalize to independently "
                          "changing real-world headers"})
    cols = ["scenario_label", "physical_runs", "total_candidate_evaluations_mean",
            "distinct_candidate_identities_mean", "duplicate_evaluations_mean",
            "duplicate_evaluation_rate_mean", "duplicate_evaluation_rate_median",
            "duplicate_evaluation_rate_ci_lo", "duplicate_evaluation_rate_ci_hi",
            "assumption"]
    write("table08_candidate_redundancy.csv", rows, cols)


# T9 allocation-policy comparisons (H5)
def t9():
    rows = [{"hypothesis": "H5", **{k: c.get(k) for k in (
        "label", "outcome", "n_pairs", "ref_mean", "trt_mean", "mean_diff",
        "median_diff_hl", "boot_ci_lo", "boot_ci_hi", "perm_p", "p_holm",
        "wilcoxon_p", "perm_deterministic", "direction_met")}}
            for c in bundle["H5"]["contrasts"]]
    cols = ["hypothesis", "label", "outcome", "n_pairs", "ref_mean", "trt_mean",
            "mean_diff", "median_diff_hl", "boot_ci_lo", "boot_ci_hi", "perm_p",
            "p_holm", "wilcoxon_p", "perm_deterministic", "direction_met"]
    write("table09_allocation_policy.csv", rows, cols)


# T10 inactive-miner analysis (H6)
def t10():
    rows = [{"hypothesis": "H6", **{k: c.get(k) for k in (
        "label", "outcome", "n_pairs", "ref_mean", "trt_mean", "mean_diff",
        "median_diff_hl", "boot_ci_lo", "boot_ci_hi", "perm_p", "p_holm",
        "perm_deterministic", "direction_met")}}
            for c in bundle["H6"]["contrasts"]]
    cols = ["hypothesis", "label", "outcome", "n_pairs", "ref_mean", "trt_mean",
            "mean_diff", "median_diff_hl", "boot_ci_lo", "boot_ci_hi", "perm_p",
            "p_holm", "perm_deterministic", "direction_met"]
    write("table10_inactive_miners.csv", rows, cols)


# T11 zero-block analysis
def t11():
    rows = []
    for lab, sc in SCEN:
        s = [r for r in runs if r["scenario_id"] == sc]
        k = sum(1 for r in s if r["accepted_blocks"] == 0)
        lo, hi = S.wilson_ci(k, len(s))
        rows.append({"scenario_label": lab, "physical_runs": len(s), "zero_block": k,
                     "zero_block_prob": k / len(s), "wilson_lo": lo, "wilson_hi": hi,
                     "na_metrics_when_zero_block":
                         "effective_block_interval_s, energy_per_accepted_block_kwh, "
                         "confirmation_time_proxy_s, single_height_stales_per_accepted_block",
                     "policy": "zero-block runs retained; block-normalised metrics NA "
                               "(not imputed); unconditional metrics use all 30 seeds"})
    cols = ["scenario_label", "physical_runs", "zero_block", "zero_block_prob",
            "wilson_lo", "wilson_hi", "na_metrics_when_zero_block", "policy"]
    write("table11_zero_block.csv", rows, cols)


# T12 secondary stale diagnostic (H7) — corrected count-rate framework, N kept separate
def t12():
    rows = []
    for lv in bundle["H7_secondary"]["levels"]:
        lo, hi = lv["mean_count_rate_cluster_boot_ci95"]
        alo, ahi = lv["any_stale_height_fraction_cluster_boot_ci95"]
        rows.append({
            "delay_s": lv["delay_s"], "miner_count": lv["miner_count"],
            "physical_runs": lv["n_runs"],
            "sh_stales_per_block_mean": lv["mean"],
            "sh_stales_per_block_median": lv["median"],
            "sh_stales_per_block_sd": lv["sd"], "sh_stales_per_block_iqr": lv["iqr"],
            "sh_stales_per_block_min": lv["min"], "sh_stales_per_block_max": lv["max"],
            "mean_count_rate_cluster_boot_lo": lo, "mean_count_rate_cluster_boot_hi": hi,
            "sh_stale_block_count_total": lv["sh_stale_block_count_total"],
            "accepted_heights_total": lv["accepted_heights_total"],
            "any_stale_height_fraction_mean": lv["any_stale_height_fraction_mean"],
            "any_stale_height_fraction_cluster_boot_lo": alo,
            "any_stale_height_fraction_cluster_boot_hi": ahi,
            "interval_method": "run-level count-rate; seed/run-cluster bootstrap (NO "
                               "binomial/Wilson/Clopper on stale_count/accepted_blocks)",
            "classification": "SECONDARY_DIAGNOSTIC_ONLY (single-height stale-race)"})
    cols = ["delay_s", "miner_count", "physical_runs", "sh_stales_per_block_mean",
            "sh_stales_per_block_median", "sh_stales_per_block_sd",
            "sh_stales_per_block_iqr", "sh_stales_per_block_min", "sh_stales_per_block_max",
            "mean_count_rate_cluster_boot_lo", "mean_count_rate_cluster_boot_hi",
            "sh_stale_block_count_total", "accepted_heights_total",
            "any_stale_height_fraction_mean", "any_stale_height_fraction_cluster_boot_lo",
            "any_stale_height_fraction_cluster_boot_hi", "interval_method", "classification"]
    write("table12_secondary_stale.csv", rows, cols)


def main():
    t1(); t3(); t6(); t7(); t8(); t9(); t10(); t11(); t12()
    # note tables 2/4/5 come from s6_analysis
    IDX.append({"table": "table02 = descriptive_long.csv (by s6_analysis)"})
    IDX.append({"table": "table04/05 = confirmatory_effects.csv (by s6_analysis)"})
    with open(os.path.join(T, "tables_index.json"), "w") as fh:
        json.dump(IDX, fh, indent=1)
        fh.write("\n")
    print("wrote tables:", sorted(os.listdir(T)))


if __name__ == "__main__":
    main()
