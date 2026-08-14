"""Stage 8X — publication/thesis-ready summary tables (A-G, plus secondaries).

Raw CSVs are never rounded. Rounding is applied only here, at publication level.
"""

from __future__ import annotations

import os
from typing import Dict

import numpy as np
import pandas as pd

from experiments.stage8x.analysis.stats import describe, holm_correction, paired_comparison
from experiments.stage8x.config import difficulty as diffmod
from experiments.stage8x.config import stage8x_config as C
from experiments.stage8x.config.asic import ALPHA_CASES, ALPHA_LABELS, S21_PRO, scaling_table

ROUND = 6


def _w(df: pd.DataFrame, name: str) -> str:
    path = os.path.join(C.OUT_DIR, name)
    df.to_csv(path, index=False)
    return path


# --------------------------------------------------------------------------
def table_a() -> pd.DataFrame:
    """Table A — hardware and network scaling parameters (all derived)."""
    rows = scaling_table(S21_PRO, list(C.NETWORK_SIZES))
    dif = {r["N"]: r for r in diffmod.difficulty_table(
        list(C.NETWORK_SIZES), C.TARGET_INTERVAL_S, C.EPOCH_SWEEP_S, S21_PRO)}
    for r in rows:
        d = dif[r["N"]]
        r.update({
            "difficulty_D_N": d["difficulty"],
            "target": d["target_hex"],
            "q_per_candidate": d["q_per_candidate"],
            "expected_hashes_per_block": d["expected_hashes_per_block"],
            "nonce_domain_S_N": d["nonce_domain"],
            "range_per_miner_L": d["range_per_miner"],
            "p_epoch_exhaustion_predicted": round(d["p_epoch_exhaustion_predicted"], 5),
            "target_block_interval_s": C.TARGET_INTERVAL_S,
            "horizon_s": C.HORIZON_S,
        })
    return pd.DataFrame(rows)


def table_b(raw: pd.DataFrame) -> pd.DataFrame:
    """Table B — physical-work results by N and protocol."""
    out = []
    for n in C.NETWORK_SIZES:
        for proto in C.PRIMARY_PROTOCOLS:
            s = raw[(raw.N == n) & (raw.protocol == proto)]
            out.append({
                "N": n, "protocol": proto,
                "protocol_label": C.PROTOCOL_LABELS[proto],
                "runs": len(s),
                "W_total_mean": s.total_evaluations.mean(),
                "W_total_sd": s.total_evaluations.std(ddof=1),
                "W_unique_mean": s.unique_evaluations.mean(),
                "W_duplicate_mean": s.duplicate_evaluations.mean(),
                "duplicate_ratio_mean": s.duplicate_ratio.mean(),
                "duplicate_ratio_max": s.duplicate_ratio.max(),
                "distinct_nonce_values_mean": s.distinct_nonce_values.mean(),
                "nonce_value_reuse_ratio_mean": s.nonce_value_reuse_ratio.mean(),
                "active_miner_seconds_mean": s.active_miner_seconds.mean(),
                "W_per_active_miner_second": (s.total_evaluations.sum()
                                              / s.active_miner_seconds.sum()),
            })
    return pd.DataFrame(out)


def table_c(energy: pd.DataFrame) -> pd.DataFrame:
    """Table C — energy results by N and alpha (paired-seed statistics)."""
    out = []
    for n in C.NETWORK_SIZES:
        for label, alpha in ALPHA_CASES.items():
            s = energy[(energy.N == n) & (energy.alpha_case == label)]
            sav = describe(s.paired_energy_saving_fraction.tolist())
            epb_pc = describe(s.PoCol_energy_per_accepted_block_kWh.tolist())
            epb_pw = describe(s.PoW_energy_per_accepted_block_kWh.tolist())
            out.append({
                "N": n, "alpha_case": label, "alpha": alpha,
                "alpha_note": ALPHA_LABELS[label],
                "P_low_W_per_miner": alpha * S21_PRO.active_power_w,
                "pairs": len(s),
                "PoW_energy_kWh_mean": s.PoW_energy_kWh.mean(),
                "PoCol_energy_kWh_mean": s.PoCol_energy_kWh.mean(),
                "PoCol_active_energy_kWh_mean": s.PoCol_active_energy_kWh.mean(),
                "PoCol_low_power_energy_kWh_mean": s.PoCol_low_power_energy_kWh.mean(),
                "paired_energy_difference_kWh_mean": s.paired_energy_difference_kWh.mean(),
                "energy_saving_fraction_mean": sav["mean"],
                "energy_saving_fraction_median": sav["median"],
                "energy_saving_fraction_sd": sav["sd"],
                "energy_saving_ci95_low": sav["ci95_low"],
                "energy_saving_ci95_high": sav["ci95_high"],
                "energy_saving_pct_mean": None if sav["mean"] is None else 100 * sav["mean"],
                "PoW_energy_per_block_kWh_mean": epb_pw["mean"],
                "PoCol_energy_per_block_kWh_mean": epb_pc["mean"],
                "low_power_fraction_mean": s.low_power_fraction.mean(),
            })
    return pd.DataFrame(out)


def table_d(raw: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    """Table D — service and latency results by N."""
    out = []
    for n in C.NETWORK_SIZES:
        row = {"N": n}
        for proto, tag in ((C.PROTO_POW, "PoW"), (C.PROTO_POCOL, "PoCol")):
            s = raw[(raw.N == n) & (raw.protocol == proto)]
            blocks = describe(s.accepted_blocks.tolist())
            med = describe(s.median_block_interval.tolist())
            mean_i = describe(s.mean_block_interval.tolist())
            row.update({
                f"{tag}_accepted_blocks_mean": blocks["mean"],
                f"{tag}_accepted_blocks_sd": blocks["sd"],
                f"{tag}_accepted_blocks_ci95_low": blocks["ci95_low"],
                f"{tag}_accepted_blocks_ci95_high": blocks["ci95_high"],
                f"{tag}_closed_rounds_mean": s.closed_rounds.mean(),
                f"{tag}_blocks_per_hour_mean": s.blocks_per_hour.mean(),
                f"{tag}_mean_block_interval_mean": mean_i["mean"],
                f"{tag}_median_block_interval_mean": med["mean"],
                f"{tag}_sd_block_interval_mean": s.sd_block_interval.mean(),
                f"{tag}_p95_block_interval_mean": s.p95_block_interval.mean(),
                f"{tag}_stale_blocks_total": int(s.stale_blocks.sum()),
                f"{tag}_stale_rate_mean": s.stale_rate.mean(),
            })
        e = energy[(energy.N == n) & (energy.alpha_case == "LP0")]
        br = describe(e.block_retention.tolist())
        lr = describe(e.latency_ratio.tolist())
        row.update({
            "block_retention_mean": br["mean"], "block_retention_median": br["median"],
            "block_retention_ci95_low": br["ci95_low"],
            "block_retention_ci95_high": br["ci95_high"],
            "block_retention_n_defined": br["n"],
            "latency_ratio_mean": lr["mean"], "latency_ratio_median": lr["median"],
            "latency_ratio_ci95_low": lr["ci95_low"],
            "latency_ratio_ci95_high": lr["ci95_high"],
            "latency_ratio_n_defined": lr["n"],
            "latency_ratio_n_undefined_NA": len(e) - lr["n"],
        })
        out.append(row)
    return pd.DataFrame(out)


def table_e(raw: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    """Table E — paired PoCol-vs-PoW differences with 95 % CI and effect sizes."""
    rows = []

    def _paired(n, metric, series_pc, series_pw, family):
        cmp_ = paired_comparison(series_pc, series_pw, label=f"{metric} N={n}")
        cmp_.update({"N": n, "metric": metric, "family": family})
        rows.append(cmp_)

    for n in C.NETWORK_SIZES:
        pw = raw[(raw.N == n) & (raw.protocol == C.PROTO_POW)].sort_values("seed_index")
        pc = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)].sort_values("seed_index")
        _paired(n, "accepted_blocks", pc.accepted_blocks.tolist(),
                pw.accepted_blocks.tolist(), "service")
        _paired(n, "total_evaluations", pc.total_evaluations.tolist(),
                pw.total_evaluations.tolist(), "work")
        _paired(n, "unique_evaluations", pc.unique_evaluations.tolist(),
                pw.unique_evaluations.tolist(), "work")
        _paired(n, "duplicate_evaluations", pc.duplicate_evaluations.tolist(),
                pw.duplicate_evaluations.tolist(), "work")
        _paired(n, "active_miner_seconds", pc.active_miner_seconds.tolist(),
                pw.active_miner_seconds.tolist(), "active_time")
        _paired(n, "median_block_interval", pc.median_block_interval.tolist(),
                pw.median_block_interval.tolist(), "latency")
        for label in ALPHA_CASES:
            e = energy[(energy.N == n) & (energy.alpha_case == label)].sort_values("seed_index")
            _paired(n, f"energy_kWh_{label}", e.PoCol_energy_kWh.tolist(),
                    e.PoW_energy_kWh.tolist(), f"energy_{label}")

    df = pd.DataFrame(rows)
    # Holm correction within each metric family across the five N values
    df["p_holm"] = np.nan
    for fam in df.family.unique():
        for metric in df[df.family == fam].metric.unique():
            mask = (df.family == fam) & (df.metric == metric)
            adj = holm_correction(df.loc[mask, "recommended_p"].tolist())
            df.loc[mask, "p_holm"] = adj
    keep = ["N", "metric", "family", "n_pairs", "mean_control", "mean_treatment",
            "mean_difference", "median_difference", "sd_difference", "iqr_difference",
            "q1_difference", "q3_difference", "ci95_mean_low", "ci95_mean_high",
            "ci95_median_low", "ci95_median_high", "relative_difference",
            "n_negative", "n_zero", "n_positive", "shapiro_p", "normality_ok",
            "ttest_t", "ttest_p", "wilcoxon_W", "wilcoxon_p", "recommended_test",
            "recommended_p", "p_holm", "cohen_dz", "rank_biserial"]
    return df[[c for c in keep if c in df.columns]]


def table_f(raw: pd.DataFrame) -> pd.DataFrame:
    """Table F — PoCol low-power residency results by N."""
    out = []
    for n in C.NETWORK_SIZES:
        s = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)]
        f = describe(s.low_power_fraction.tolist())
        out.append({
            "N": n, "runs": len(s),
            "active_to_low_transitions_mean": s.active_to_low_transitions.mean(),
            "low_to_active_transitions_mean": s.low_to_active_transitions.mean(),
            "transitions_balanced": bool(
                (s.active_to_low_transitions == s.low_to_active_transitions).all()),
            "low_power_miner_seconds_mean": s.low_power_miner_seconds.mean(),
            "active_miner_seconds_mean": s.active_miner_seconds.mean(),
            "F_low_mean": f["mean"], "F_low_sd": f["sd"],
            "F_low_ci95_low": f["ci95_low"], "F_low_ci95_high": f["ci95_high"],
            "F_low_min": f["min"], "F_low_max": f["max"],
            "mean_low_duration_s": s.mean_low_duration_s.mean(),
            "median_low_duration_s": s.median_low_duration_s.mean(),
            "max_low_duration_s": s.max_low_duration_s.max(),
            "miners_entering_low_mean": s.miners_entering_low.mean(),
            "fraction_miners_entering_low_mean": s.fraction_miners_entering_low.mean(),
            "mean_simultaneous_low_miners": s.mean_simultaneous_low_miners.mean(),
            "max_simultaneous_low_miners": s.max_simultaneous_low_miners.max(),
        })
    return pd.DataFrame(out)


def table_g(raw: pd.DataFrame) -> pd.DataFrame:
    """Table G — nonce exhaustion / round-completion diagnostics."""
    out = []
    for n in C.NETWORK_SIZES:
        spec = diffmod.derive(n, C.TARGET_INTERVAL_S, C.EPOCH_SWEEP_S, S21_PRO)
        for proto in C.PRIMARY_PROTOCOLS:
            s = raw[(raw.N == n) & (raw.protocol == proto)]
            exh = s.epoch_exhaustions.mean()
            blocks = s.accepted_blocks.mean()
            out.append({
                "N": n, "protocol": proto,
                "range_completions_mean": s.range_completions.mean(),
                "range_completions_per_miner_mean": s.range_completions.mean() / n,
                "global_domain_exhaustions_mean": exh,
                "accepted_blocks_mean": blocks,
                "epochs_mean": exh + blocks,
                "observed_exhaustion_share": (exh / (exh + blocks)) if (exh + blocks) else None,
                "predicted_exhaustion_probability": spec.p_epoch_exhaustion,
                "simulator_artifact_exhaustions_total": int(
                    s.domain_artifact_exhaustions.sum()),
                "state_time_conservation_error_max_s": s.state_time_conservation_error_s.max(),
                "work_accounting_error_max": s.work_accounting_error.max(),
                "zero_block_runs": int((s.accepted_blocks == 0).sum()),
            })
    return pd.DataFrame(out)


def table_h_secondary_matched_template(secondary: pd.DataFrame,
                                       raw: pd.DataFrame) -> pd.DataFrame:
    """Secondary S1 — common-template PoW comparator (duplicate-work axis)."""
    mt = secondary[secondary.protocol == C.PROTO_POW_MT]
    out = []
    for n in sorted(mt.N.unique()):
        s = mt[mt.N == n]
        pw = raw[(raw.N == n) & (raw.protocol == C.PROTO_POW)]
        pc = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)]
        out.append({
            "N": n, "runs": len(s),
            "MT_duplicate_ratio_mean": s.duplicate_ratio.mean(),
            "MT_duplicate_ratio_sd": s.duplicate_ratio.std(ddof=1),
            "MT_duplicate_evaluations_mean": s.duplicate_evaluations.mean(),
            "MT_unique_evaluations_mean": s.unique_evaluations.mean(),
            "MT_accepted_blocks_mean": s.accepted_blocks.mean(),
            "PoW_accepted_blocks_mean": pw.accepted_blocks.mean(),
            "PoCol_accepted_blocks_mean": pc.accepted_blocks.mean(),
            "PoCol_duplicate_ratio_mean": pc.duplicate_ratio.mean(),
            "PoW_duplicate_ratio_mean": pw.duplicate_ratio.mean(),
            "MT_mean_block_interval": s.mean_block_interval.mean(),
            "PoW_mean_block_interval": pw.mean_block_interval.mean(),
            "blocks_lost_to_duplication_vs_PoW": (
                1.0 - s.accepted_blocks.mean() / pw.accepted_blocks.mean()
                if pw.accepted_blocks.mean() else None),
            # N miners each scan L candidates inside a shared domain S = N*L at
            # independent uniform offsets. E[union] = S*(1-(1-1/N)^N), so
            # E[duplicate ratio] = 1 - union/total = (1-1/N)^N -> e^-1 = 0.3679.
            "theoretical_duplicate_ratio": (1.0 - 1.0 / n) ** n,
        })
    return pd.DataFrame(out)


def table_i_secondary_epoch_sensitivity(secondary: pd.DataFrame,
                                        raw: pd.DataFrame) -> pd.DataFrame:
    """Secondary S2 — PoCol epoch-allocation sensitivity (energy/throughput frontier)."""
    sub = secondary[secondary.protocol == C.PROTO_POCOL]
    out = []
    for n in sorted(sub.N.unique()):
        pw = raw[(raw.N == n) & (raw.protocol == C.PROTO_POW)]
        pw_blocks = pw.accepted_blocks.mean()
        base = raw[(raw.N == n) & (raw.protocol == C.PROTO_POCOL)]
        frames = [(C.EPOCH_SWEEP_S, base)] + [
            (tau, sub[(sub.N == n) & (sub.epoch_sweep_s == tau)])
            for tau in sorted(sub[sub.N == n].epoch_sweep_s.unique(), reverse=True)
        ]
        for tau, s in frames:
            if not len(s):
                continue
            flow = s.low_power_fraction.mean()
            row = {
                "N": n, "tau_epoch_s": tau, "runs": len(s),
                "is_frozen_primary": bool(tau == C.EPOCH_SWEEP_S),
                "range_per_miner_L": int(s.range_per_miner.iloc[0]),
                "F_low_mean": flow,
                "accepted_blocks_mean": s.accepted_blocks.mean(),
                "PoW_accepted_blocks_mean": pw_blocks,
                "block_retention_mean": (s.accepted_blocks.mean() / pw_blocks
                                         if pw_blocks else None),
                "mean_block_interval": s.mean_block_interval.mean(),
                "epoch_exhaustions_mean": s.epoch_exhaustions.mean(),
                "duplicate_ratio_mean": s.duplicate_ratio.mean(),
            }
            for label, alpha in ALPHA_CASES.items():
                row[f"energy_saving_{label}"] = flow * (1.0 - alpha)
            out.append(row)
    return pd.DataFrame(out)


# --------------------------------------------------------------------------
def build_all(raw: pd.DataFrame, energy: pd.DataFrame,
              secondary: pd.DataFrame = None) -> Dict[str, str]:
    paths = {}
    paths["A"] = _w(table_a(), "stage8x_tableA_hardware_scaling.csv")
    paths["B"] = _w(table_b(raw), "stage8x_tableB_physical_work.csv")
    paths["C"] = _w(table_c(energy), "stage8x_tableC_energy.csv")
    paths["D"] = _w(table_d(raw, energy), "stage8x_tableD_service_latency.csv")
    paths["E"] = _w(table_e(raw, energy), "stage8x_tableE_paired_differences.csv")
    paths["F"] = _w(table_f(raw), "stage8x_tableF_low_power_residency.csv")
    paths["G"] = _w(table_g(raw), "stage8x_tableG_exhaustion_diagnostics.csv")
    if secondary is not None and len(secondary):
        paths["H"] = _w(table_h_secondary_matched_template(secondary, raw),
                        "stage8x_tableH_secondary_matched_template.csv")
        paths["I"] = _w(table_i_secondary_epoch_sensitivity(secondary, raw),
                        "stage8x_tableI_secondary_epoch_sensitivity.csv")
    return paths
