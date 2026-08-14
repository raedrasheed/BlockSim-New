"""Stage 8Y — summary tables A-P.

Raw CSVs are never rounded; rounding is applied only here. Every table is written
as CSV and as a Markdown/LaTeX-friendly pipe table.
"""

from __future__ import annotations

import os
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import hardware as hw
from experiments.stage8y.config import policies as pol
from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.src.analysis_stats import describe, holm, paired_comparison


def write(df: pd.DataFrame, stem: str) -> Dict[str, str]:
    csv_path = os.path.join(C.OUT_DIR, f"{stem}.csv")
    md_path = os.path.join(C.OUT_DIR, f"{stem}.md")
    df.to_csv(csv_path, index=False)
    with open(md_path, "w", encoding="utf-8") as fh:
        fh.write(df.round(6).to_markdown(index=False))
        fh.write("\n")
    return {"csv": csv_path, "md": md_path}


# --------------------------------------------------------------------------
def table_A_parameters() -> pd.DataFrame:
    fp = C.frozen_parameters()
    rows = [
        ("experiment", C.EXPERIMENT), ("revision", C.REVISION),
        ("primary_network_sizes", str(list(C.PRIMARY_NETWORK_SIZES))),
        ("secondary_network_sizes", str(list(C.SECONDARY_NETWORK_SIZES))),
        ("primary_compositions", str(list(C.PRIMARY_COMPOSITIONS))),
        ("primary_protocols", str(list(C.PRIMARY_PROTOCOLS))),
        ("horizon_s", C.HORIZON_S), ("long_horizon_s", C.LONG_HORIZON_S),
        ("target_interval_s", C.TARGET_INTERVAL_S),
        ("epoch_sweep_s", C.EPOCH_SWEEP_S),
        ("prop_delay_mean_s", C.BLOCK_PROP_DELAY_MEAN_S),
        ("difficulty_rule", fp["difficulty_rule"]),
        ("nonce_domain_rule", fp["nonce_domain_rule"]),
        ("domain_semantics", C.DOMAIN_SEMANTICS),
        ("confirmatory_selection_rule", C.CONF_SELECTION_RULE),
        ("confirmatory_target_hash_fraction", C.CONF_TARGET_HASH_FRACTION),
        ("confirmatory_reserve_schedule", str(list(C.CONF_RESERVE_SCHEDULE))),
        ("confirmatory_trigger_s", C.CONF_TRIGGER_S),
        ("confirmatory_wake_s", C.CONF_WAKE_S),
        ("wake_power_ratio", C.WAKE_POWER_RATIO),
        ("alpha_cases", str(C.ALPHA_CASES)), ("alpha_note", C.ALPHA_NOTE),
        ("n_primary_seeds", C.N_PRIMARY_SEEDS),
        ("saving_threshold", C.ACCEPTANCE["saving_threshold"]),
        ("retention_strong", C.ACCEPTANCE["retention_strong"]),
        ("retention_moderate", C.ACCEPTANCE["retention_moderate"]),
        ("latency_ratio_max", C.ACCEPTANCE["latency_ratio_max"]),
        ("config_hash", C.config_hash()),
    ]
    return pd.DataFrame(rows, columns=["parameter", "value"])


def table_B_hardware() -> pd.DataFrame:
    reg = hw.registry_raw()
    rows = []
    for d in reg["devices"]:
        rows.append({
            "key": d["key"], "manufacturer": d["manufacturer"], "model": d["model"],
            "generation": d["generation"], "hashrate_THs": d["hashrate_THs"],
            "active_power_W": d["active_power_W"],
            "efficiency_J_per_TH_stated": d["efficiency_J_per_TH_stated"],
            "efficiency_J_per_TH_derived": d["efficiency_J_per_TH_derived"],
            "efficiency_consistent": d["efficiency_consistent"],
            "manufacturer_certified": d["manufacturer_certified"],
            "low_power_W_documented": "none published",
            "source_url": d["source_url"], "retrieval_date": d["retrieval_date"],
        })
    return pd.DataFrame(rows)


def table_C_compositions() -> pd.DataFrame:
    rows = hw.composition_table(list(C.ALL_COMPOSITIONS), list(C.ALL_NETWORK_SIZES))
    df = pd.DataFrame(rows)
    df["rationale"] = df.composition.map(hw.COMPOSITION_RATIONALE)
    return df


def table_D_difficulty() -> pd.DataFrame:
    return pd.DataFrame(diffmod.difficulty_table(
        list(C.ALL_COMPOSITIONS), list(C.ALL_NETWORK_SIZES),
        C.TARGET_INTERVAL_S, C.EPOCH_SWEEP_S))


def table_E_run_matrix(raw: pd.DataFrame, sec: pd.DataFrame,
                       lon: pd.DataFrame, pilot: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for name, df, classification in (
            ("pilot", pilot, "Pilot - excluded from all inference"),
            ("primary", raw, "Primary confirmatory"),
            ("secondary", sec, "Secondary / exploratory sensitivity"),
            ("longhorizon", lon, "Long-horizon confirmatory")):
        if df is None or not len(df):
            rows.append({"phase": name, "classification": classification,
                         "physical_runs": 0})
            continue
        rows.append({
            "phase": name, "classification": classification,
            "physical_runs": len(df),
            "protocols": ", ".join(sorted(df.protocol.unique())),
            "compositions": ", ".join(sorted(df.composition.unique())),
            "network_sizes": ", ".join(str(x) for x in sorted(df.N.unique())),
            "seeds": df.seed_index.nunique(),
            "horizon_s": ", ".join(str(int(x)) for x in sorted(df.horizon_s.unique())),
            "alpha_observations": (len(df[df.protocol.isin(C.POCOL_PROTOCOLS)])
                                   * len(C.ALPHA_CASES)),
        })
    return pd.DataFrame(rows)


def table_F_energy(energy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (comp, n, proto, ac), g in energy.groupby(
            ["composition", "N", "protocol", "alpha_case"]):
        s = describe(g.EnergySaving.tolist(),
                     threshold=C.ACCEPTANCE["saving_threshold"])
        rows.append({
            "composition": comp, "N": n, "protocol": proto, "alpha_case": ac,
            "alpha": C.ALPHA_CASES[ac],
            "is_idealized_alpha": ac in C.IDEALIZED_ALPHA_LABELS,
            "pairs": s["n"],
            "PoW_energy_kWh_mean": g.PoW_energy_kWh.mean(),
            "PoCol_energy_kWh_mean": g.PoCol_energy_kWh.mean(),
            "EnergySaving_mean": s["mean"], "EnergySaving_median": s["median"],
            "EnergySaving_sd": s["sd"],
            "EnergySaving_ci95_low": s["ci95_low"],
            "EnergySaving_ci95_high": s["ci95_high"],
            "EnergySaving_boot_ci95_low": s["boot_ci95_low"],
            "EnergySaving_boot_ci95_high": s["boot_ci95_high"],
            "exceeds_50pct_mean": s.get("mean_exceeds_threshold"),
            "exceeds_50pct_ci_lower": s.get("ci_lower_exceeds_threshold"),
            "exceeds_50pct_boot_ci_lower": s.get("boot_ci_lower_exceeds_threshold"),
            "one_sided_p_greater_50pct": s.get("one_sided_p_greater"),
            "seed_fraction_exceeding_50pct": s.get("fraction_of_seeds_exceeding"),
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol", "alpha"]).reset_index(drop=True)


def table_G_blocks(energy: pd.DataFrame, raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = energy[energy.alpha_case == "alpha_0"]
    for (comp, n, proto), g in sub.groupby(["composition", "N", "protocol"]):
        ret = describe(g.BlockRetention.tolist(),
                       threshold=C.ACCEPTANCE["retention_moderate"])
        ret95 = describe(g.BlockRetention.tolist(),
                         threshold=C.ACCEPTANCE["retention_strong"])
        hr = describe(g.HashRetention.tolist())
        pw = raw[(raw.composition == comp) & (raw.N == n) & (raw.protocol == C.POW)]
        pc = raw[(raw.composition == comp) & (raw.N == n) & (raw.protocol == proto)]
        rows.append({
            "composition": comp, "N": n, "protocol": proto, "pairs": ret["n"],
            "PoW_blocks_mean": pw.accepted_blocks.mean(),
            "PoCol_blocks_mean": pc.accepted_blocks.mean(),
            "BlockRetention_mean": ret["mean"], "BlockRetention_median": ret["median"],
            "BlockRetention_sd": ret["sd"],
            "BlockRetention_ci95_low": ret["ci95_low"],
            "BlockRetention_ci95_high": ret["ci95_high"],
            "BlockRetention_boot_ci95_low": ret["boot_ci95_low"],
            "BlockRetention_boot_ci95_high": ret["boot_ci95_high"],
            "meets_90pct_mean": ret.get("mean_exceeds_threshold"),
            "meets_90pct_ci_lower": ret.get("ci_lower_exceeds_threshold"),
            "meets_95pct_mean": ret95.get("mean_exceeds_threshold"),
            "meets_95pct_ci_lower": ret95.get("ci_lower_exceeds_threshold"),
            "HashRetention_mean": hr["mean"],
            "PoW_stale_blocks": int(pw.stale_blocks.sum()),
            "PoCol_stale_blocks": int(pc.stale_blocks.sum()),
            "zero_block_runs": int((pc.accepted_blocks == 0).sum()),
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol"]).reset_index(drop=True)


def table_H_latency(raw: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    sub = energy[energy.alpha_case == "alpha_0"]
    for (comp, n, proto), g in sub.groupby(["composition", "N", "protocol"]):
        pw = raw[(raw.composition == comp) & (raw.N == n) & (raw.protocol == C.POW)]
        pc = raw[(raw.composition == comp) & (raw.N == n) & (raw.protocol == proto)]
        lat = describe(g.LatencyRatio_median.tolist())
        rows.append({
            "composition": comp, "N": n, "protocol": proto,
            "PoW_mean_interval_s": pw.mean_block_interval.mean(),
            "PoCol_mean_interval_s": pc.mean_block_interval.mean(),
            "PoW_median_interval_s": pw.median_block_interval.mean(),
            "PoCol_median_interval_s": pc.median_block_interval.mean(),
            "PoW_p95_interval_s": pw.p95_block_interval.mean(),
            "PoCol_p95_interval_s": pc.p95_block_interval.mean(),
            "LatencyRatio_median_mean": lat["mean"],
            "LatencyRatio_ci95_low": lat["ci95_low"],
            "LatencyRatio_ci95_high": lat["ci95_high"],
            "LatencyRatio_n_defined": lat["n"],
            "LatencyRatio_n_NA": len(g) - lat["n"],
            "meets_latency_1p10": (lat["mean"] is not None
                                   and lat["mean"] <= C.ACCEPTANCE["latency_ratio_max"]),
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol"]).reset_index(drop=True)


def table_I_residence(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (comp, n, proto), g in raw.groupby(["composition", "N", "protocol"]):
        rows.append({
            "composition": comp, "N": n, "protocol": proto, "runs": len(g),
            "F_active": g.F_active.mean(), "F_low": g.F_low.mean(),
            "F_standby": g.F_standby.mean(), "F_waking": g.F_waking.mean(),
            "F_parked_minertime": g.F_parked_minertime.mean(),
            "F_parked_power_weighted": g.F_parked_power_weighted.mean(),
            "mean_h_active_fraction": g.mean_h_active_fraction.mean(),
            "mean_p_drawn_fraction": g.mean_p_drawn_fraction.mean(),
            "min_h_active_fraction": g.min_h_active_fraction.mean(),
            "wake_events_mean": g.wake_events.mean(),
            "reserve_activations_mean": g.reserve_activations.mean(),
            "mean_low_episode_s": g.mean_low_episode_s.mean(),
            "max_low_episode_s": g.max_low_episode_s.max(),
            "miners_entering_low_mean": g.miners_entering_low.mean(),
            "miners_entering_standby_mean": g.miners_entering_standby.mean(),
            "state_time_conservation_error_max_s": g.state_time_conservation_error_s.max(),
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol"]).reset_index(drop=True)


def table_J_work(raw: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (comp, n, proto), g in raw.groupby(["composition", "N", "protocol"]):
        rows.append({
            "composition": comp, "N": n, "protocol": proto, "runs": len(g),
            "W_total_mean": g.total_evaluations.mean(),
            "W_unique_mean": g.unique_evaluations.mean(),
            "W_duplicate_mean": g.duplicate_evaluations.mean(),
            "duplicate_ratio_mean": g.duplicate_ratio.mean(),
            "distinct_nonce_values_mean": g.distinct_nonce_values.mean(),
            "nonce_value_reuse_ratio_mean": g.nonce_value_reuse_ratio.mean(),
            "stale_evaluations_mean": g.stale_evaluations.mean(),
            "useful_chain_evaluations_mean": g.useful_chain_evaluations.mean(),
            "work_accounting_error_max": g.work_accounting_error.max(),
            "n_templates_mean": g.n_templates.mean(),
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol"]).reset_index(drop=True)


def table_K_statistics(raw: pd.DataFrame, energy: pd.DataFrame) -> pd.DataFrame:
    """Primary paired comparisons with Holm correction across the primary family."""
    rows = []
    for comp in sorted(raw.composition.unique()):
        for n in sorted(raw.N.unique()):
            pw = raw[(raw.composition == comp) & (raw.N == n)
                     & (raw.protocol == C.POW)].sort_values("seed_index")
            for proto in [p for p in C.PRIMARY_PROTOCOLS if p != C.POW]:
                pc = raw[(raw.composition == comp) & (raw.N == n)
                         & (raw.protocol == proto)].sort_values("seed_index")
                if not len(pc) or not len(pw):
                    continue
                for metric, a, b in (
                        ("accepted_blocks", pc.accepted_blocks, pw.accepted_blocks),
                        ("total_evaluations", pc.total_evaluations, pw.total_evaluations),
                        ("mean_h_active_fraction", pc.mean_h_active_fraction,
                         pw.mean_h_active_fraction),
                        ("median_block_interval", pc.median_block_interval,
                         pw.median_block_interval)):
                    c = paired_comparison(a.tolist(), b.tolist(),
                                          f"{proto} {comp} N={n} {metric}")
                    c.update({"composition": comp, "N": n, "protocol": proto,
                              "metric": metric, "family": metric})
                    rows.append(c)
                for ac in C.ALPHA_CASES:
                    g = energy[(energy.composition == comp) & (energy.N == n)
                               & (energy.protocol == proto)
                               & (energy.alpha_case == ac)].sort_values("seed_index")
                    if not len(g):
                        continue
                    c = paired_comparison(g.PoCol_energy_kWh.tolist(),
                                          g.PoW_energy_kWh.tolist(),
                                          f"{proto} {comp} N={n} energy {ac}")
                    c.update({"composition": comp, "N": n, "protocol": proto,
                              "metric": f"energy_kWh_{ac}", "family": f"energy_{ac}"})
                    rows.append(c)
    df = pd.DataFrame(rows)
    if not len(df):
        return df
    df["p_holm"] = np.nan
    for fam in df.family.unique():
        for proto in df[df.family == fam].protocol.unique():
            mask = (df.family == fam) & (df.protocol == proto)
            df.loc[mask, "p_holm"] = holm(df.loc[mask, "recommended_p"].tolist())
    keep = ["composition", "N", "protocol", "metric", "family", "n_pairs",
            "mean_control", "mean_treatment", "mean_difference", "median_difference",
            "sd_difference", "iqr_difference", "ci95_mean_low", "ci95_mean_high",
            "boot_ci95_low", "boot_ci95_high", "relative_difference",
            "n_negative", "n_zero", "n_positive", "shapiro_p", "normality_ok",
            "ttest_t", "ttest_p", "wilcoxon_W", "wilcoxon_p", "recommended_test",
            "recommended_p", "p_holm", "cohen_dz", "rank_biserial"]
    return df[[c for c in keep if c in df.columns]]


def table_L_acceptance(energy: pd.DataFrame, latency: pd.DataFrame) -> pd.DataFrame:
    """Per-configuration evaluation of the preregistered acceptance criteria."""
    acc = C.ACCEPTANCE
    lat_lookup = {(r.composition, r.N, r.protocol): r.LatencyRatio_median_mean
                  for r in latency.itertuples()}
    rows = []
    for (comp, n, proto, ac), g in energy.groupby(
            ["composition", "N", "protocol", "alpha_case"]):
        sav = describe(g.EnergySaving.tolist(), threshold=acc["saving_threshold"])
        ret = describe(g.BlockRetention.tolist())
        lat = lat_lookup.get((comp, n, proto))
        idealized = ac in C.IDEALIZED_ALPHA_LABELS
        s_ok = bool(sav["mean"] is not None and sav["mean"] > acc["saving_threshold"])
        s_ok_ci = bool(sav.get("boot_ci_lower_exceeds_threshold"))
        r95 = bool(ret["mean"] is not None and ret["mean"] >= acc["retention_strong"])
        r90 = bool(ret["mean"] is not None and ret["mean"] >= acc["retention_moderate"])
        l_ok = bool(lat is not None and lat <= acc["latency_ratio_max"])
        if s_ok and r95 and l_ok and not idealized:
            outcome = "A"
        elif s_ok and r90 and not idealized:
            outcome = "B"
        elif s_ok and not r90:
            outcome = "C (idealized alpha)" if idealized else "C"
        elif s_ok and idealized:
            outcome = "E"
        else:
            outcome = "D"
        rows.append({
            "composition": comp, "N": n, "protocol": proto, "alpha_case": ac,
            "alpha": C.ALPHA_CASES[ac], "is_idealized_alpha": idealized,
            "EnergySaving_mean": sav["mean"],
            "EnergySaving_boot_ci_low": sav["boot_ci95_low"],
            "saving_gt_50pct": s_ok, "saving_gt_50pct_ci_lower": s_ok_ci,
            "BlockRetention_mean": ret["mean"],
            "retention_ge_90pct": r90, "retention_ge_95pct": r95,
            "LatencyRatio_median": lat, "latency_le_1p10": l_ok,
            "outcome": outcome,
        })
    return pd.DataFrame(rows).sort_values(
        ["composition", "N", "protocol", "alpha"]).reset_index(drop=True)


def table_M_pareto(front: List[Dict]) -> pd.DataFrame:
    return pd.DataFrame(front)


def table_N_alpha(energy: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for (proto, ac), g in energy.groupby(["protocol", "alpha_case"]):
        s = describe(g.EnergySaving.tolist(), threshold=C.ACCEPTANCE["saving_threshold"])
        rows.append({
            "protocol": proto, "alpha_case": ac, "alpha": C.ALPHA_CASES[ac],
            "is_idealized_alpha": ac in C.IDEALIZED_ALPHA_LABELS,
            "P_low_note": "model assumption; not a manufacturer-certified mode",
            "n": s["n"], "EnergySaving_mean": s["mean"],
            "EnergySaving_ci95_low": s["ci95_low"],
            "EnergySaving_ci95_high": s["ci95_high"],
            "exceeds_50pct_mean": s.get("mean_exceeds_threshold"),
            "exceeds_50pct_ci_lower": s.get("ci_lower_exceeds_threshold"),
            "configs_exceeding_50pct": int(sum(
                1 for _k, gg in g.groupby(["composition", "N"])
                if gg.EnergySaving.mean() > C.ACCEPTANCE["saving_threshold"])),
        })
    return pd.DataFrame(rows).sort_values(["protocol", "alpha"]).reset_index(drop=True)


def table_O_wake(sec_energy: pd.DataFrame, sec_raw: pd.DataFrame) -> pd.DataFrame:
    if not len(sec_raw):
        return pd.DataFrame()
    wake = sec_raw[sec_raw.tag.astype(str).str.startswith("wake")]
    if not len(wake):
        return pd.DataFrame()
    rows = []
    for (tag, ac), g in sec_energy[
            sec_energy.tag.astype(str).str.startswith("wake")].groupby(
            ["tag", "alpha_case"]):
        wr = sec_raw[sec_raw.tag == tag]
        s = describe(g.EnergySaving.tolist(), threshold=C.ACCEPTANCE["saving_threshold"])
        rows.append({
            "tag": tag, "wake_s": wr.wake_s.iloc[0], "alpha_case": ac,
            "alpha": C.ALPHA_CASES[ac], "n": s["n"],
            "EnergySaving_mean": s["mean"],
            "EnergySaving_ci95_low": s["ci95_low"],
            "EnergySaving_ci95_high": s["ci95_high"],
            "BlockRetention_mean": g.BlockRetention.mean(),
            "t_waking_miner_s_mean": wr.t_waking_miner_s.mean(),
            "wake_events_mean": wr.wake_events.mean(),
            "exceeds_50pct": s.get("mean_exceeds_threshold"),
        })
    df = pd.DataFrame(rows)
    return (df.sort_values(["wake_s", "alpha"]).reset_index(drop=True)
            if len(df) else df)


def table_P_longhorizon(lon_energy: pd.DataFrame, lon_raw: pd.DataFrame,
                        primary_energy: pd.DataFrame) -> pd.DataFrame:
    if not len(lon_energy):
        return pd.DataFrame()
    rows = []
    for (comp, proto, ac), g in lon_energy.groupby(
            ["composition", "protocol", "alpha_case"]):
        s = describe(g.EnergySaving.tolist(), threshold=C.ACCEPTANCE["saving_threshold"])
        ret = describe(g.BlockRetention.tolist())
        short = primary_energy[(primary_energy.composition == comp)
                               & (primary_energy.protocol == proto)
                               & (primary_energy.alpha_case == ac)
                               & (primary_energy.N == C.LONG_HORIZON_N)]
        rows.append({
            "composition": comp, "N": C.LONG_HORIZON_N, "protocol": proto,
            "alpha_case": ac, "alpha": C.ALPHA_CASES[ac],
            "horizon_s": C.LONG_HORIZON_S, "n": s["n"],
            "EnergySaving_long_mean": s["mean"],
            "EnergySaving_long_ci95_low": s["ci95_low"],
            "EnergySaving_long_ci95_high": s["ci95_high"],
            "EnergySaving_short_mean": short.EnergySaving.mean() if len(short) else None,
            "saving_difference_long_minus_short": (
                s["mean"] - short.EnergySaving.mean() if len(short) and s["mean"]
                is not None else None),
            "BlockRetention_long_mean": ret["mean"],
            "BlockRetention_short_mean": (short.BlockRetention.mean()
                                          if len(short) else None),
            "blocks_long_mean": g.PoCol_accepted_blocks.mean(),
            "exceeds_50pct": s.get("mean_exceeds_threshold"),
        })
    df = pd.DataFrame(rows)
    return (df.sort_values(["composition", "protocol", "alpha"]).reset_index(drop=True)
            if len(df) else df)


def table_Q_headline(front: List[Dict]) -> pd.DataFrame:
    """The most important table: one row per Pareto-optimal confirmatory config."""
    rows = []
    for p in front:
        rows.append({
            "Configuration": p["config"],
            "EnergySaving": p["EnergySaving"],
            "BlockRetention": p["BlockRetention"],
            "MeanActiveHashFraction": p["mean_h_active_fraction"],
            "MeanActivePowerFraction": p["mean_p_drawn_fraction"],
            "EnergyPerBlock_change_vs_PoW": p["energy_per_block_change"],
            "MeanSecurityHashFraction": p["mean_SecurityHashFraction"],
            "MinSecurityHashFraction": p["min_SecurityHashFraction"],
            "MainSourceOfSaving": p["main_source"],
            "Outcome": p["outcome"],
        })
    return pd.DataFrame(rows)
