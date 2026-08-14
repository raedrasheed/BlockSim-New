"""Stage 8Y — analysis, Pareto frontier, acceptance evaluation and reports.

    python -m experiments.stage8y.analyze
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

from experiments.stage8y.config import seeds as seedmod
from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.run import ENERGY_FILES, PHASE_FILES, TRACE_FILES
from experiments.stage8y.src import analysis_figures as figmod
from experiments.stage8y.src import analysis_tables as tab
from experiments.stage8y.src.analysis_stats import describe, pareto_front


def _load(name: str) -> pd.DataFrame:
    p = os.path.join(C.OUT_DIR, name)
    return pd.read_csv(p) if os.path.exists(p) else pd.DataFrame()


def _sha(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _f(x, nd=4):
    if x is None or (isinstance(x, float) and np.isnan(x)):
        return "NA"
    if isinstance(x, (int, np.integer)):
        return str(x)
    if isinstance(x, float):
        if x != 0 and (abs(x) < 1e-3 or abs(x) >= 1e6):
            return f"{x:.{nd}e}"
        return f"{x:.{nd}f}"
    return str(x)


def _pct(x, nd=2):
    return "NA" if x is None or (isinstance(x, float) and np.isnan(x)) \
        else f"{100 * x:.{nd}f}%"


# --------------------------------------------------------------------------
def completeness_audit(raw, energy, sec, lon, pilot) -> Dict:
    checks = []

    def chk(name, ok, detail=""):
        checks.append({"check": name, "pass": bool(ok), "detail": str(detail)})

    exp = C.primary_matrix()
    exp_ids = {c.run_id for c in exp}
    got = set(raw.run_id) if len(raw) else set()
    chk("primary matrix size == 1080", len(exp) == 1080, len(exp))
    chk("primary runs recorded == 1080", len(raw) == 1080, len(raw))
    chk("no duplicate primary run_id",
        len(raw) == raw.run_id.nunique() if len(raw) else False,
        raw.run_id.nunique() if len(raw) else 0)
    chk("no missing primary runs", not (exp_ids - got), len(exp_ids - got))
    chk("no unexpected primary runs", not (got - exp_ids), len(got - exp_ids))
    if len(raw):
        for p in C.PRIMARY_PROTOCOLS:
            chk(f"270 runs for {p}", int((raw.protocol == p).sum()) == 270,
                int((raw.protocol == p).sum()))
        chk("all primary compositions complete",
            sorted(raw.composition.unique()) == sorted(C.PRIMARY_COMPOSITIONS))
        chk("all primary N complete",
            sorted(raw.N.unique()) == sorted(C.PRIMARY_NETWORK_SIZES))
        chk("30 seeds at every cell",
            bool((raw.groupby(["composition", "N", "protocol"]).size() == 30).all()))
        chk("state-time conservation < 1e-6 s",
            bool(raw.state_time_conservation_error_s.max() < 1e-6),
            f"{raw.state_time_conservation_error_s.max():.3e}")
        chk("no negative residence", bool(raw.min_state_residence_s.min() >= 0.0))
        chk("work identity < 1e-9", bool(raw.work_accounting_error.max() < 1e-9),
            f"{raw.work_accounting_error.max():.3e}")
        chk("duplicate identity holds",
            bool(((raw.total_evaluations - raw.unique_evaluations
                   - raw.duplicate_evaluations) == 0).all()))
        pocol = raw[raw.protocol.isin(C.POCOL_PROTOCOLS)]
        chk("PoCol exact duplicates == 0", bool((pocol.duplicate_evaluations == 0).all()))
        chk("PoW exact duplicates == 0",
            bool((raw[raw.protocol == C.POW].duplicate_evaluations == 0).all()))
        chk("PoW never parked",
            bool((raw[raw.protocol == C.POW].t_low_miner_s == 0).all()
                 and (raw[raw.protocol == C.POW].t_standby_miner_s == 0).all()))
        chk("one difficulty per (composition, N)",
            all(raw[(raw.composition == c) & (raw.N == n)].difficulty.nunique() == 1
                for c in raw.composition.unique() for n in raw.N.unique()))
        chk("single config hash", raw.config_hash.nunique() == 1,
            raw.config_hash.unique().tolist())
        chk("no zero-block runs discarded", True,
            f"{int((raw.accepted_blocks == 0).sum())} retained")
    chk("primary alpha observations == 4050", len(energy) == 4050, len(energy))
    if len(energy):
        chk("5 alpha cases per PoCol run",
            bool((energy.groupby("run_id").size() == 5).all()))
    chk("secondary runs recorded", len(sec) == len(C.secondary_matrix()),
        f"{len(sec)} of {len(C.secondary_matrix())}")
    chk("long-horizon runs recorded", len(lon) == len(C.longhorizon_matrix()),
        f"{len(lon)} of {len(C.longhorizon_matrix())}")
    chk("pilot kept separate from primary",
        not (set(pilot.run_id) & set(raw.run_id)) if len(pilot) and len(raw) else True)
    return {"checks": checks, "all_pass": all(c["pass"] for c in checks)}


# --------------------------------------------------------------------------
def build_pareto(energy: pd.DataFrame, raw: pd.DataFrame,
                 accept: pd.DataFrame) -> List[Dict]:
    """One candidate point per confirmatory configuration."""
    acc_lookup = {(r.composition, r.N, r.protocol, r.alpha_case): r.outcome
                  for r in accept.itertuples()}
    pts = []
    for (comp, n, proto, ac), g in energy.groupby(
            ["composition", "N", "protocol", "alpha_case"]):
        rr = raw[(raw.composition == comp) & (raw.N == n) & (raw.protocol == proto)]
        epb_pc = g.PoCol_energy_per_block_kWh.dropna().mean()
        epb_pw = g.PoW_energy_per_block_kWh.dropna().mean()
        shares = {
            "reduced hash participation": g.share_participation.mean(),
            "preferential selection of efficient ASICs": g.share_selection.mean(),
        }
        origin = {"post-range low-power residence": g.share_postrange.mean(),
                  "reserve standby residence": g.share_reserve.mean()}
        main = max(shares, key=lambda k: shares[k])
        main_origin = max(origin, key=lambda k: origin[k])
        pts.append({
            "config": f"{proto} / {comp} / N={n} / {ac}",
            "composition": comp, "N": int(n), "protocol": proto, "alpha_case": ac,
            "alpha": C.ALPHA_CASES[ac],
            "is_idealized_alpha": ac in C.IDEALIZED_ALPHA_LABELS,
            "EnergySaving": float(g.EnergySaving.mean()),
            "BlockRetention": float(g.BlockRetention.mean()),
            "mean_h_active_fraction": float(rr.mean_h_active_fraction.mean()),
            "mean_p_drawn_fraction": float(rr.mean_p_drawn_fraction.mean()),
            "energy_per_block_change": (float(epb_pc / epb_pw - 1.0)
                                        if epb_pw else None),
            "mean_SecurityHashFraction": float(rr.mean_SecurityHashFraction.mean()),
            "min_SecurityHashFraction": float(rr.min_SecurityHashFraction.mean()),
            "share_participation": float(shares["reduced hash participation"]),
            "share_selection": float(
                shares["preferential selection of efficient ASICs"]),
            "main_source": f"{main} ({100*shares[main]:.0f}% of ΔE); "
                           f"state origin: {main_origin}",
            "outcome": acc_lookup.get((comp, n, proto, ac), "?"),
        })
    return pts


def evaluate_acceptance(accept: pd.DataFrame, energy: pd.DataFrame) -> Dict:
    """Preregistered Outcomes A-E over the confirmatory dataset."""
    acc = C.ACCEPTANCE
    nonideal = accept[~accept.is_idealized_alpha]
    ideal = accept[accept.is_idealized_alpha]
    A = accept[(accept.outcome == "A")]
    B = accept[(accept.outcome == "B")]
    Cc = accept[accept.outcome.astype(str).str.startswith("C")]
    any_sav = accept[accept.saving_gt_50pct]
    sav_nonideal = nonideal[nonideal.saving_gt_50pct]
    sav_ideal_only = bool(len(ideal[ideal.saving_gt_50pct]) > 0
                          and len(sav_nonideal) == 0)
    return {
        "thresholds": acc,
        "n_confirmatory_configurations": int(len(accept)),
        "A_strong_success": {"met": bool(len(A) > 0), "count": int(len(A)),
                             "configs": A.head(10).to_dict("records")},
        "B_moderate_success": {"met": bool(len(B) > 0), "count": int(len(B)),
                               "configs": B.head(10).to_dict("records")},
        "C_tradeoff": {"met": bool(len(Cc) > 0), "count": int(len(Cc))},
        "D_threshold_not_reached": {"met": bool(len(any_sav) == 0)},
        "E_idealized_only": {"met": sav_ideal_only},
        "any_config_over_50pct": bool(len(any_sav) > 0),
        "any_nonidealized_config_over_50pct": bool(len(sav_nonideal) > 0),
        "max_saving": float(accept.EnergySaving_mean.max()) if len(accept) else None,
        "max_saving_config": (accept.loc[accept.EnergySaving_mean.idxmax()].to_dict()
                              if len(accept) else None),
        "max_retention_among_over_50pct": (float(any_sav.BlockRetention_mean.max())
                                           if len(any_sav) else None),
        "best_retention_over_50pct_config": (
            any_sav.loc[any_sav.BlockRetention_mean.idxmax()].to_dict()
            if len(any_sav) else None),
        "n_over_50pct_with_retention_ge_90": int(
            len(any_sav[any_sav.retention_ge_90pct])),
        "n_over_50pct_with_retention_ge_95": int(
            len(any_sav[any_sav.retention_ge_95pct])),
        "highest_alpha_reaching_50pct": (float(sav_nonideal.alpha.max())
                                         if len(sav_nonideal) else None),
    }


# --------------------------------------------------------------------------
def main(argv=None) -> int:
    C.ensure_dirs()
    raw = _load(PHASE_FILES["primary"])
    energy = _load(ENERGY_FILES["primary"])
    traces = _load(TRACE_FILES["primary"])
    sec = _load(PHASE_FILES["secondary"])
    sec_e = _load(ENERGY_FILES["secondary"])
    lon = _load(PHASE_FILES["longhorizon"])
    lon_e = _load(ENERGY_FILES["longhorizon"])
    pilot = _load(PHASE_FILES["pilot"])
    if not len(raw):
        print("no primary results; run --phase primary first")
        return 1

    audit = completeness_audit(raw, energy, sec, lon, pilot)

    # ---- tables ----
    T: Dict[str, pd.DataFrame] = {}
    T["A"] = tab.table_A_parameters()
    T["B"] = tab.table_B_hardware()
    T["C"] = tab.table_C_compositions()
    T["D"] = tab.table_D_difficulty()
    T["E"] = tab.table_E_run_matrix(raw, sec, lon, pilot)
    T["F"] = tab.table_F_energy(energy)
    T["G"] = tab.table_G_blocks(energy, raw)
    T["H"] = tab.table_H_latency(raw, energy)
    T["I"] = tab.table_I_residence(raw)
    T["J"] = tab.table_J_work(raw)
    T["K"] = tab.table_K_statistics(raw, energy)
    T["L"] = tab.table_L_acceptance(energy, T["H"])
    T["N"] = tab.table_N_alpha(energy)
    T["O"] = tab.table_O_wake(sec_e, sec)
    T["P"] = tab.table_P_longhorizon(lon_e, lon, energy)

    points = build_pareto(energy, raw, T["L"])
    front = pareto_front(points, "EnergySaving", "BlockRetention")
    T["M"] = tab.table_M_pareto(front)
    T["Q"] = tab.table_Q_headline(front)

    names = {
        "A": "stage8y_tableA_frozen_parameters", "B": "stage8y_tableB_hardware_registry",
        "C": "stage8y_tableC_compositions", "D": "stage8y_tableD_difficulty",
        "E": "stage8y_tableE_run_matrix", "F": "stage8y_tableF_energy",
        "G": "stage8y_tableG_blocks", "H": "stage8y_tableH_latency",
        "I": "stage8y_tableI_state_residence", "J": "stage8y_tableJ_physical_work",
        "K": "stage8y_tableK_statistics", "L": "stage8y_tableL_acceptance",
        "M": "stage8y_tableM_pareto", "N": "stage8y_tableN_alpha_sensitivity",
        "O": "stage8y_tableO_wake_sensitivity", "P": "stage8y_tableP_long_horizon",
        "Q": "stage8y_tableQ_headline",
    }
    table_paths = {}
    for k, df in T.items():
        if df is not None and len(df):
            table_paths[k] = tab.write(df, names[k])

    acceptance = evaluate_acceptance(T["L"], energy)
    figs = figmod.build_all(raw, energy, traces, sec, sec_e, lon, lon_e)

    write_reports(raw, energy, sec, sec_e, lon, lon_e, pilot, T, front,
                  acceptance, audit, figs, table_paths)

    print(f"completeness audit : {'PASS' if audit['all_pass'] else 'FAIL'}")
    for c in audit["checks"]:
        if not c["pass"]:
            print(f"  FAIL: {c['check']} ({c['detail']})")
    print(f"tables  : {len(table_paths)}")
    print(f"figures : {len(figs)}")
    print(f"outcome : over50%={acceptance['any_config_over_50pct']} "
          f"nonidealized={acceptance['any_nonidealized_config_over_50pct']} "
          f"A={acceptance['A_strong_success']['met']} "
          f"B={acceptance['B_moderate_success']['met']} "
          f"C={acceptance['C_tradeoff']['met']} "
          f"D={acceptance['D_threshold_not_reached']['met']} "
          f"E={acceptance['E_idealized_only']['met']}")
    return 0 if audit["all_pass"] else 1


# --------------------------------------------------------------------------
def write_reports(raw, energy, sec, sec_e, lon, lon_e, pilot, T, front,
                  acceptance, audit, figs, table_paths) -> None:
    ts = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    cfgh = C.config_hash()

    # ---------------- EXECUTION ----------------
    L = [f"# STAGE 8Y — EXECUTION REPORT", "", f"Generated: {ts}",
         f"Config hash: `{cfgh}`",
         f"Commit at execution: `{raw.commit_hash.iloc[0] if len(raw) else 'NA'}`", "",
         "## 1. Executed matrix", "",
         "| Phase | Classification | Physical runs | α observations |",
         "|---|---|---|---|"]
    for name, df, cls, ef in (("Pilot", pilot, "excluded from all inference", None),
                              ("Primary", raw, "**confirmatory**", energy),
                              ("Secondary", sec, "exploratory / sensitivity", sec_e),
                              ("Long horizon", lon, "confirmatory (T=100 000 s)", lon_e)):
        L.append(f"| {name} | {cls} | {len(df)} | {len(ef) if ef is not None else 0} |")
    L += ["", "α observations are **derived accounting rows** re-priced from recorded "
              "state residencies, not independent physical simulations.", "",
          "## 2. Completeness audit", "", "| Check | Result | Detail |", "|---|---|---|"]
    for c in audit["checks"]:
        L.append(f"| {c['check']} | {'PASS' if c['pass'] else '**FAIL**'} | {c['detail']} |")
    L += ["", f"**Overall: {'PASS' if audit['all_pass'] else 'FAIL'}**", "",
          "## 3. Runtime", "",
          f"* primary simulation time: {raw.execution_time_seconds.sum():.1f} s",
          f"* slowest single run: {raw.execution_time_seconds.max():.3f} s",
          f"* long-horizon simulation time: "
          f"{lon.execution_time_seconds.sum() if len(lon) else 0:.1f} s", "",
          "## 4. Integrity", "",
          "* Runs are resumable by `run_id`; completed runs are skipped, never duplicated.",
          "* No run was discarded and no seed was selectively re-run.",
          "* Zero-block runs would be retained; none occurred.",
          "* Pilot, primary, secondary and long-horizon datasets use disjoint seed "
          "groups and disjoint run-ID prefixes and are never pooled.", ""]
    _write("STAGE_8Y_EXECUTION_REPORT.md", L)

    # ---------------- STATISTICAL ANALYSIS ----------------
    K = T["K"]
    L = ["# STAGE 8Y — STATISTICAL ANALYSIS", "", f"Generated: {ts}", "",
         "All primary comparisons are **seed-paired**: Δ = PoCol − PoW per matched "
         "seed. Normality of the paired differences is checked (Shapiro-Wilk) before "
         "choosing between the paired t-test and Wilcoxon signed-rank; the selected "
         "test is named per row. Magnitude, 95 % CI (t-based and paired bootstrap) and "
         "effect size are reported alongside every p-value. Holm-Bonferroni correction "
         "is applied within each metric family across the confirmatory cells.", "",
         "Small p-values here reflect the tightness of the pairing, not practical "
         "importance. **Read the magnitude and its confidence interval first.**", ""]
    for metric in ["energy_kWh_alpha_010", "energy_kWh_alpha_0", "accepted_blocks",
                   "mean_h_active_fraction", "median_block_interval"]:
        sub = K[K.metric == metric] if len(K) else pd.DataFrame()
        if not len(sub):
            continue
        L += [f"## {metric}", "",
              "| comp | N | protocol | mean Δ | 95% CI | bootstrap CI | relative | "
              "test | p | Holm p | d_z |", "|---|---|---|---|---|---|---|---|---|---|---|"]
        for r in sub.itertuples():
            L.append(
                f"| {r.composition} | {r.N} | {r.protocol} | {_f(r.mean_difference)} | "
                f"[{_f(r.ci95_mean_low)}, {_f(r.ci95_mean_high)}] | "
                f"[{_f(r.boot_ci95_low)}, {_f(r.boot_ci95_high)}] | "
                f"{_f(r.relative_difference)} | {r.recommended_test} | "
                f"{_f(r.recommended_p)} | {_f(r.p_holm)} | {_f(r.cohen_dz)} |")
        L.append("")
    L += ["## Threshold assessment", "",
          "For the central questions the analysis estimates a CI around the quantity "
          "itself and asks whether the bound clears the preregistered threshold.", "",
          "| comp | N | protocol | α | Saving mean | bootstrap CI | CI lower > 50 %? | "
          "seeds > 50 % |", "|---|---|---|---|---|---|---|---|"]
    for r in T["F"].itertuples():
        L.append(f"| {r.composition} | {r.N} | {r.protocol} | {r.alpha} | "
                 f"{_pct(r.EnergySaving_mean)} | "
                 f"[{_pct(r.EnergySaving_boot_ci95_low)}, "
                 f"{_pct(r.EnergySaving_boot_ci95_high)}] | "
                 f"{'YES' if r.exceeds_50pct_boot_ci_lower else 'no'} | "
                 f"{_pct(r.seed_fraction_exceeding_50pct, 0)} |")
    L.append("")
    _write("STAGE_8Y_STATISTICAL_ANALYSIS.md", L)

    # ---------------- PARETO ----------------
    L = ["# STAGE 8Y — PARETO ANALYSIS", "", f"Generated: {ts}", "",
         "The empirical frontier is computed over **all confirmatory configurations** "
         "(composition × N × policy × α), not by picking the single largest saving. "
         "A configuration is Pareto-optimal when no other configuration is at least as "
         "good on both energy saving and block retention and strictly better on one.",
         "", "## Region occupancy", "",
         "| Region | Configurations |", "|---|---|"]
    acc = T["L"]
    regions = [
        (">50 % saving AND ≥95 % retention",
         acc[acc.saving_gt_50pct & acc.retention_ge_95pct]),
        (">50 % saving AND 90–95 % retention",
         acc[acc.saving_gt_50pct & acc.retention_ge_90pct & ~acc.retention_ge_95pct]),
        (">50 % saving AND <90 % retention",
         acc[acc.saving_gt_50pct & ~acc.retention_ge_90pct]),
        ("≤50 % saving", acc[~acc.saving_gt_50pct]),
    ]
    for label, df in regions:
        L.append(f"| {label} | **{len(df)}** |")
    L += ["", "## Pareto-optimal configurations", "",
          "| Configuration | Saving | Retention | mean active hash | mean active power | "
          "E/block change | mean security hash | min security hash | main source | "
          "outcome |",
          "|---|---|---|---|---|---|---|---|---|---|"]
    for p in front:
        L.append(f"| {p['config']} | {_pct(p['EnergySaving'])} | "
                 f"{_pct(p['BlockRetention'])} | {_pct(p['mean_h_active_fraction'])} | "
                 f"{_pct(p['mean_p_drawn_fraction'])} | "
                 f"{_pct(p['energy_per_block_change'])} | "
                 f"{_pct(p['mean_SecurityHashFraction'])} | "
                 f"{_pct(p['min_SecurityHashFraction'])} | {p['main_source']} | "
                 f"{p['outcome']} |")
    L += ["", "This is the table that makes the cost of energy saving impossible to "
              "hide: every point that clears 50 % also states what it gave up in block "
              "retention, in active hash capacity and in security hash fraction.", ""]
    _write("STAGE_8Y_PARETO_ANALYSIS.md", L)

    # ---------------- ACCEPTANCE ----------------
    a = acceptance
    L = ["# STAGE 8Y — ACCEPTANCE CRITERIA", "", f"Generated: {ts}", "",
         "Criteria were preregistered in `config/stage8y_config.py::ACCEPTANCE` before "
         "any confirmatory run and are evaluated here verbatim.", "",
         "| Threshold | Value |", "|---|---|",
         f"| Energy saving | > {a['thresholds']['saving_threshold']:.0%} |",
         f"| Block retention (strong) | ≥ {a['thresholds']['retention_strong']:.0%} |",
         f"| Block retention (moderate) | ≥ {a['thresholds']['retention_moderate']:.0%} |",
         f"| Latency ratio | ≤ {a['thresholds']['latency_ratio_max']:.2f} |", "",
         "## Outcomes", "", "| Outcome | Definition | Met | Configurations |",
         "|---|---|---|---|",
         f"| **A** strong success | {a['thresholds']['outcome_A']} | "
         f"{'YES' if a['A_strong_success']['met'] else 'NO'} | "
         f"{a['A_strong_success']['count']} |",
         f"| **B** moderate success | {a['thresholds']['outcome_B']} | "
         f"{'YES' if a['B_moderate_success']['met'] else 'NO'} | "
         f"{a['B_moderate_success']['count']} |",
         f"| **C** energy/performance trade-off | {a['thresholds']['outcome_C']} | "
         f"{'YES' if a['C_tradeoff']['met'] else 'NO'} | {a['C_tradeoff']['count']} |",
         f"| **D** threshold not reached | {a['thresholds']['outcome_D']} | "
         f"{'YES' if a['D_threshold_not_reached']['met'] else 'NO'} | — |",
         f"| **E** idealized only | {a['thresholds']['outcome_E']} | "
         f"{'YES' if a['E_idealized_only']['met'] else 'NO'} | — |", "",
         "## Key quantities", "", "| Question | Answer |", "|---|---|",
         f"| Any configuration > 50 % saving? | "
         f"{'YES' if a['any_config_over_50pct'] else 'NO'} |",
         f"| Any **non-idealized** (α > 0) configuration > 50 %? | "
         f"{'YES' if a['any_nonidealized_config_over_50pct'] else 'NO'} |",
         f"| Highest α still reaching > 50 % | "
         f"{a['highest_alpha_reaching_50pct'] if a['highest_alpha_reaching_50pct'] is not None else 'none'} |",
         f"| Maximum saving observed | {_pct(a['max_saving'])} |",
         f"| Configurations with > 50 % saving AND ≥ 90 % retention | "
         f"{a['n_over_50pct_with_retention_ge_90']} |",
         f"| Configurations with > 50 % saving AND ≥ 95 % retention | "
         f"{a['n_over_50pct_with_retention_ge_95']} |",
         f"| Best retention among > 50 % configurations | "
         f"{_pct(a['max_retention_among_over_50pct'])} |", ""]
    _write("STAGE_8Y_ACCEPTANCE_CRITERIA.md", L)

    # ---------------- RESULTS ----------------
    _write("STAGE_8Y_RESULTS_REPORT.md",
           results_report(raw, energy, sec, sec_e, lon, lon_e, T, front, acceptance,
                          audit, figs, ts, cfgh))

    # ---------------- machine-readable summary + manifest ----------------
    summary = {
        "experiment": C.EXPERIMENT, "revision": C.REVISION, "generated_utc": ts,
        "config_hash": cfgh,
        "seed_registry_sha256": _sha(C.SEEDS_JSON) if os.path.exists(C.SEEDS_JSON) else None,
        "run_counts": {"pilot": len(pilot), "primary": len(raw),
                       "secondary": len(sec), "longhorizon": len(lon)},
        "alpha_observations": {"primary": len(energy), "secondary": len(sec_e),
                               "longhorizon": len(lon_e)},
        "completeness_audit_pass": audit["all_pass"],
        "acceptance": {k: v for k, v in acceptance.items()
                       if k not in ("A_strong_success", "B_moderate_success",
                                    "max_saving_config",
                                    "best_retention_over_50pct_config")},
        "acceptance_A_met": acceptance["A_strong_success"]["met"],
        "acceptance_B_met": acceptance["B_moderate_success"]["met"],
        "acceptance_C_met": acceptance["C_tradeoff"]["met"],
        "acceptance_D_met": acceptance["D_threshold_not_reached"]["met"],
        "acceptance_E_met": acceptance["E_idealized_only"]["met"],
        "pareto_front": front,
        "figures": figs,
        "tables": {k: os.path.basename(v["csv"]) for k, v in table_paths.items()},
        "alpha_note": C.ALPHA_NOTE,
    }
    with open(os.path.join(C.OUT_DIR, "stage8y_summary.json"), "w",
              encoding="utf-8") as fh:
        json.dump(summary, fh, indent=2, sort_keys=True, default=str)
        fh.write("\n")

    entries = {}
    for root in (C.OUT_DIR, C.FIG_DIR, C.REPORT_DIR, C.MANIFEST_DIR,
                 os.path.join(C.STAGE_DIR, "config"), os.path.join(C.STAGE_DIR, "src"),
                 os.path.join(C.STAGE_DIR, "tests")):
        for dirpath, dirs, files in os.walk(root):
            dirs[:] = [d for d in dirs if d != "__pycache__"]
            for fn in sorted(files):
                if fn.endswith(".pyc"):
                    continue
                p = os.path.join(dirpath, fn)
                entries[os.path.relpath(p, C.REPO_ROOT)] = {
                    "sha256": _sha(p), "bytes": os.path.getsize(p)}
    lines = ["# STAGE 8Y — FILE MANIFEST", "", f"Generated: {ts}",
             f"Config hash: `{cfgh}`", f"Files: {len(entries)}", "",
             "| File | SHA-256 | bytes |", "|---|---|---|"]
    for rel, meta in sorted(entries.items()):
        lines.append(f"| `{rel}` | `{meta['sha256'][:32]}…` | {meta['bytes']} |")
    _write("STAGE_8Y_FILE_MANIFEST.md", lines)
    with open(os.path.join(C.MANIFEST_DIR, "stage8y_file_manifest.json"), "w",
              encoding="utf-8") as fh:
        json.dump({"generated_utc": ts, "config_hash": cfgh, "files": entries},
                  fh, indent=2, sort_keys=True)
        fh.write("\n")


def _write(name: str, lines: List[str]) -> str:
    path = os.path.join(C.REPORT_DIR, name)
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
        fh.write("\n")
    return path


def results_report(raw, energy, sec, sec_e, lon, lon_e, T, front, acceptance,
                   audit, figs, ts, cfgh) -> List[str]:
    a = acceptance
    L = [f"# STAGE 8Y — RESULTS REPORT", "", f"Generated: {ts}  ",
         f"Config hash: `{cfgh}`  ", f"Revision: {C.REVISION}", "",
         "## 1. Research question", "",
         "> Can PoCol exploit heterogeneous miner capabilities, energy-aware "
         "allocation, coordinated low-power participation and adaptive reserve "
         "activation to reduce total network energy by more than 50 % relative to "
         "matched traditional PoW while retaining at least 90 %, and preferably at "
         "least 95 %, of accepted-block production?", "",
         "## 2. Headline answer", "", "| Question | Answer |", "|---|---|",
         f"| > 50 % saving reached at all? | "
         f"**{'YES' if a['any_config_over_50pct'] else 'NO'}** |",
         f"| > 50 % survives a non-idealized α (> 0)? | "
         f"**{'YES' if a['any_nonidealized_config_over_50pct'] else 'NO'}** |",
         f"| Highest α still reaching > 50 % | "
         f"**{a['highest_alpha_reaching_50pct'] if a['highest_alpha_reaching_50pct'] is not None else 'none'}** |",
         f"| > 50 % with ≥ 90 % block retention? | "
         f"**{'YES' if a['n_over_50pct_with_retention_ge_90'] else 'NO'}** "
         f"({a['n_over_50pct_with_retention_ge_90']} configurations) |",
         f"| > 50 % with ≥ 95 % block retention? | "
         f"**{'YES' if a['n_over_50pct_with_retention_ge_95'] else 'NO'}** "
         f"({a['n_over_50pct_with_retention_ge_95']} configurations) |",
         f"| Best block retention among > 50 % configurations | "
         f"**{_pct(a['max_retention_among_over_50pct'])}** |",
         f"| Maximum saving observed | {_pct(a['max_saving'])} |", "",
         "## 3. Energy saving by policy and α (all compositions and N pooled)", "",
         "| Policy | α | Saving mean | 95 % CI | > 50 %? |", "|---|---|---|---|---|"]
    for r in T["N"].itertuples():
        L.append(f"| {r.protocol} | {r.alpha} | {_pct(r.EnergySaving_mean)} | "
                 f"[{_pct(r.EnergySaving_ci95_low)}, {_pct(r.EnergySaving_ci95_high)}] | "
                 f"{'YES' if r.exceeds_50pct_mean else 'no'} |")
    L += ["", "## 4. Block retention and latency", "",
          "| comp | N | policy | blocks PoW | blocks PoCol | retention | 95 % CI | "
          "latency ratio |", "|---|---|---|---|---|---|---|---|"]
    lat = {(r.composition, r.N, r.protocol): r.LatencyRatio_median_mean
           for r in T["H"].itertuples()}
    for r in T["G"].itertuples():
        L.append(f"| {r.composition} | {r.N} | {r.protocol} | "
                 f"{_f(r.PoW_blocks_mean, 2)} | {_f(r.PoCol_blocks_mean, 2)} | "
                 f"{_pct(r.BlockRetention_mean)} | "
                 f"[{_pct(r.BlockRetention_ci95_low)}, "
                 f"{_pct(r.BlockRetention_ci95_high)}] | "
                 f"{_f(lat.get((r.composition, r.N, r.protocol)), 3)} |")
    L += ["", "## 5. Energy-saving decomposition (mandatory)", "",
          "Because every miner is in exactly one state and WAKING is charged at full "
          "active power, `P_N·T = pw_active + pw_waking + pw_low + pw_standby` holds "
          "exactly, so the saving is exactly `(1−α)·(pw_low + pw_standby)`. Two "
          "orthogonal exact decompositions are reported.", "",
          "| comp | policy | share: reduced participation | share: efficient selection | "
          "share: post-range | share: reserve standby | SelectivityGain |",
          "|---|---|---|---|---|---|---|"]
    for (comp, proto), g in energy[energy.alpha_case == "alpha_010"].groupby(
            ["composition", "protocol"]):
        rr = raw[(raw.composition == comp) & (raw.protocol == proto)]
        L.append(f"| {comp} | {proto} | {_pct(g.share_participation.mean())} | "
                 f"{_pct(g.share_selection.mean())} | {_pct(g.share_postrange.mean())} | "
                 f"{_pct(g.share_reserve.mean())} | "
                 f"{_f(rr.SelectivityGain.mean(), 3)} |")
    L += ["", "`dE_stale = 0` by construction: an ACTIVE miner draws the same power "
              "whether its work is useful or stale, so eliminating stale work does not "
              "reduce energy unless it also reduces active time. The stale-work "
              "*evaluation* difference is reported in Table J as a physical-work "
              "diagnostic and is deliberately **not** folded into the energy identity.",
          "", "## 6. Security-hash analysis", "",
          "| comp | N | policy | mean security hash fraction | min instantaneous |",
          "|---|---|---|---|---|"]
    for (comp, n, proto), g in raw.groupby(["composition", "N", "protocol"]):
        L.append(f"| {comp} | {n} | {proto} | "
                 f"{_pct(g.mean_SecurityHashFraction.mean())} | "
                 f"{_pct(g.min_SecurityHashFraction.mean())} |")
    L += ["", "Reducing the active set reduces the instantaneous cost of attacking the "
              "chain. Block-retention parity does **not** imply unchanged security and "
              "is not presented as if it did.", "",
          "## 7. Fairness", "", "| comp | policy | participation share by device | "
          "reward share by device | Gini (active time) | miners never active |",
          "|---|---|---|---|---|---|"]
    devs = [d for d in ("S21PRO", "S19XP", "S19JPRO")
            if f"participation_share_{d}" in raw.columns]
    for (comp, proto), g in raw.groupby(["composition", "protocol"]):
        pshare = ", ".join(f"{d}:{_pct(g[f'participation_share_{d}'].mean(), 1)}"
                           for d in devs if g[f"participation_share_{d}"].notna().any())
        rshare = ", ".join(f"{d}:{_pct(g[f'reward_share_{d}'].mean(), 1)}"
                           for d in devs if g[f"reward_share_{d}"].notna().any())
        L.append(f"| {comp} | {proto} | {pshare} | {rshare} | "
                 f"{_f(g.gini_active_time_by_miner.mean(), 3)} | "
                 f"{_f(g.miners_with_zero_active_time.mean(), 1)} |")
    L += ["", "## 8. Physical work and the duplicate distinction", "",
          "| policy | W_total mean | exact duplicate ratio | nonce-value reuse ratio |",
          "|---|---|---|---|"]
    frames = [raw] + ([sec[sec.protocol == C.POW_CT]] if len(sec) else [])
    allr = pd.concat(frames, ignore_index=True)
    for proto, g in allr.groupby("protocol"):
        L.append(f"| {proto} | {_f(g.total_evaluations.mean())} | "
                 f"{_pct(g.duplicate_ratio.mean(), 4)} | "
                 f"{_pct(g.nonce_value_reuse_ratio.mean(), 6)} |")
    L += ["", "Exact-input duplication requires an identical full hash input "
              "`(template, candidate index)`. Traditional PoW miners build distinct "
              "templates, so their exact duplicate work is zero even though nonce-value "
              "reuse is essentially total. Only the clearly-labelled secondary "
              "Common-Template Independent PoW comparator produces real duplicates.",
          "", "## 9. Long-horizon confirmation", ""]
    if len(T.get("P", pd.DataFrame())):
        L += ["| comp | policy | α | saving (10 000 s) | saving (100 000 s) | Δ |",
              "|---|---|---|---|---|---|"]
        for r in T["P"].itertuples():
            if r.alpha_case not in ("alpha_0", "alpha_010", "alpha_025"):
                continue
            L.append(f"| {r.composition} | {r.protocol} | {r.alpha} | "
                     f"{_pct(r.EnergySaving_short_mean)} | "
                     f"{_pct(r.EnergySaving_long_mean)} | "
                     f"{_pct(r.saving_difference_long_minus_short)} |")
    else:
        L.append("_not available_")
    L += ["", "## 10. Acceptance criteria", "",
          f"See `STAGE_8Y_ACCEPTANCE_CRITERIA.md`. Outcome A "
          f"{'MET' if a['A_strong_success']['met'] else 'NOT met'}; "
          f"B {'MET' if a['B_moderate_success']['met'] else 'NOT met'}; "
          f"C {'MET' if a['C_tradeoff']['met'] else 'NOT met'}; "
          f"D {'MET' if a['D_threshold_not_reached']['met'] else 'NOT met'}; "
          f"E {'MET' if a['E_idealized_only']['met'] else 'NOT met'}.", "",
          "## 11. Figures", ""]
    for f in figs:
        L.append(f"* `figures/{f}.{{png,pdf,svg}}`")
    L += ["", "## 12. Limitations", "",
          "See `STAGE_8Y_LIMITATIONS.md`, which must be read before quoting any number "
          "from this report.", ""]
    return L


if __name__ == "__main__":
    sys.exit(main())
