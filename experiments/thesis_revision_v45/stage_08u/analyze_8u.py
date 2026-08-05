#!/usr/bin/env python3
"""Stage 8U — frozen analysis (executes STAGE_08U_PREREGISTRATION.md §5–§6 verbatim).

Input: ONLY the frozen 60-row STAGE_08U_RUN_DATASET.csv.  n = 12 fresh paired seeds; all
4096 exact sign assignments (two-sided); 10 000 paired bootstrap resamples; percentile
95% CIs; analysis root 17618529829928476883; Holm at alpha = 0.05 over EXACTLY the four
declared contrasts.  Runs are the unit of analysis.
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
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08u"
DATASET = DOCS / "STAGE_08U_RUN_DATASET.csv"
sys.path.insert(0, str(HERE))
import scenarios_8u as S8U                                                 # noqa: E402

ROOT_SEED = S8U.ANALYSIS_SEED_8U
B = 10_000
N = 12
ALPHA = 0.05

W00, W01 = "W00_POW_POPULATION_MATCHED", "W01_POW_ACTIVE_CAPACITY_MATCHED"
P00, P01, P02 = "P00_POCOL_NO_FLOOR", "P01_POCOL_STAGE8S_COARSE", "P02_POCOL_SINGLE_HANDOFF"


def load() -> dict:
    with open(DATASET, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 60
    by = {}
    for r in rows:
        by.setdefault(r["scenario_id"], []).append(r)
    assert set(by) == {W00, W01, P00, P01, P02}
    for sid, rs in by.items():
        rs.sort(key=lambda r: int(r["seed_index"]))
        assert [int(r["seed_index"]) for r in rs] == list(range(N)), sid
    return by


def exact_p_two_sided(d: list) -> float:
    obs = abs(statistics.fmean(d))
    count = 0
    for mask in range(1 << len(d)):
        m = statistics.fmean(x if (mask >> i) & 1 == 0 else -x for i, x in enumerate(d))
        if abs(m) >= obs - 1e-15:
            count += 1
    return count / (1 << len(d))


def boot(values: list, label: str) -> dict:
    rng = random.Random(f"{ROOT_SEED}:{label}")
    n = len(values)
    stats = sorted(statistics.fmean([values[rng.randrange(n)] for _ in range(n)])
                   for _ in range(B))
    return {"mean": statistics.fmean(values), "median": statistics.median(values),
            "ci95_lower": stats[249], "ci95_upper": stats[9749]}


def paired(treat, ctrl, field, label) -> dict:
    t = [float(x[field]) for x in treat]
    c = [float(x[field]) for x in ctrl]
    d = [a - b for a, b in zip(t, c)]
    bd = boot(d, f"{label}:d")
    return {"field": field,
            "treatment_mean": statistics.fmean(t), "control_mean": statistics.fmean(c),
            "paired_mean_difference": bd["mean"],
            "paired_median_difference": statistics.median(d),
            "ci95_difference": [bd["ci95_lower"], bd["ci95_upper"]],
            "exact_p_two_sided": exact_p_two_sided(d),
            "per_seed_difference": d}


def holm(named: dict) -> dict:
    items = sorted(named.items(), key=lambda kv: kv[1])
    out = {}
    prior = True
    for i, (name, p) in enumerate(items):
        thr = ALPHA / (len(items) - i)
        reject = prior and (p <= thr)
        out[name] = {"p": p, "holm_threshold": thr, "reject_null": reject}
        prior = prior and reject
    return out


def write_csv(dest, rows):
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    dest.write_text(buf.getvalue())
    print(f"wrote {dest.relative_to(REPO_ROOT)} ({len(rows)} rows)")


def main() -> int:
    by = load()
    w00, w01, p00, p01, p02 = by[W00], by[W01], by[P00], by[P01], by[P02]
    integrity_ok = all(r["run_status"] == "COMPLETED"
                       and r["all_integrity_gates_pass"] == "True"
                       for rs in by.values() for r in rs)
    if not integrity_ok:
        print("STAGE_8U_BLOCKED — integrity failure in the frozen dataset")
        return 2

    # ---- Holm family: EXACTLY the four preregistered contrasts ---------------------
    c_req = paired(p02, p01, "activation_requests_seated", "HOLM1:requests")
    c_inc = paired(p02, p01, "incomplete_activation_request_count", "HOLM2:incomplete")
    c_blocks = paired(p02, w01, "rounds_accepted", "HOLM3:blocks")
    c_energy = paired(p02, w01, "E_idle_kwh", "HOLM4:energy")
    holm_out = holm({
        "P02_vs_P01(activation_requests_seated)": c_req["exact_p_two_sided"],
        "P02_vs_P01(incomplete_requests)": c_inc["exact_p_two_sided"],
        "P02_vs_W01(accepted_blocks)": c_blocks["exact_p_two_sided"],
        "P02_vs_W01(total_energy)": c_energy["exact_p_two_sided"]})

    # ---- H-U1 churn (P02 vs P01) ----------------------------------------------------
    reass = [float(r["reassignments_per_closed_round"]) for r in p02]
    hu1_checks = {
        "mean_reassignments_per_closed_round_le_1.0":
            (statistics.fmean(reass), statistics.fmean(reass) <= 1.0),
        "mean_activation_requests_lt_P01":
            (c_req["treatment_mean"], c_req["treatment_mean"] < c_req["control_mean"]),
        "mean_incomplete_requests_lt_P01":
            (c_inc["treatment_mean"], c_inc["treatment_mean"] < c_inc["control_mean"]),
    }
    hu1_pass = all(ok for _v, ok in hu1_checks.values())

    # ---- H-U2 service vs W01 --------------------------------------------------------
    blocks_ratio = c_blocks["treatment_mean"] / c_blocks["control_mean"]
    med_p02 = statistics.fmean(float(r["median_round_duration"]) for r in p02)
    med_w01 = statistics.fmean(float(r["median_round_duration"]) for r in w01)
    dur_ratio = med_p02 / med_w01
    hu2_checks = {
        "mean_accepted_blocks_ratio_P02_over_W01_ge_0.90":
            (blocks_ratio, blocks_ratio >= 0.90),
        "mean_median_round_duration_ratio_P02_over_W01_le_1.10":
            (dur_ratio, dur_ratio <= 1.10),
    }
    hu2_pass = all(ok for _v, ok in hu2_checks.values())

    # ---- H-U3 energy vs W01 ---------------------------------------------------------
    rel = [(float(c["E_idle_kwh"]) - float(t["E_idle_kwh"])) / float(c["E_idle_kwh"])
           for t, c in zip(p02, w01)]
    b_rel = boot(rel, "HU3:relative")
    hu3_checks = {
        "mean_paired_relative_energy_reduction_ge_0.20":
            (b_rel["mean"], b_rel["mean"] >= 0.20),
        "bootstrap_ci95_lower_bound_gt_0":
            (b_rel["ci95_lower"], b_rel["ci95_lower"] > 0.0),
    }
    hu3_pass = all(ok for _v, ok in hu3_checks.values())

    # ---- H-U4 sensitivity vs W00 (NEVER a licensing gate) ---------------------------
    s_energy = paired(p02, w00, "E_idle_kwh", "HU4:energy")
    s_blocks = paired(p02, w00, "rounds_accepted", "HU4:blocks")
    s_med = paired(p02, w00, "median_round_duration", "HU4:median")
    s_tot = paired(p02, w00, "total_physical_evaluations", "HU4:total_evals")
    s_uni = paired(p02, w00, "unique_physical_evaluations", "HU4:unique_evals")
    s_dup = paired(p02, w00, "duplicate_physical_evaluations", "HU4:dup_evals")
    s_epb = paired(p02, w00, "energy_per_accepted_block_kwh", "HU4:energy_per_block")
    rel_w00 = [(float(c["E_idle_kwh"]) - float(t["E_idle_kwh"])) / float(c["E_idle_kwh"])
               for t, c in zip(p02, w00)]
    b_rel_w00 = boot(rel_w00, "HU4:relative")
    hu4 = {"note": "DESCRIPTIVE + INFERENTIAL SENSITIVITY ONLY — never a licensing gate",
           "energy": s_energy, "blocks": s_blocks, "median_duration": s_med,
           "total_evaluations": s_tot, "unique_evaluations": s_uni,
           "duplicate_evaluations": s_dup, "energy_per_accepted_block": s_epb,
           "paired_relative_energy_reduction": b_rel_w00}

    # ---- H-U5 structural health of P02 ----------------------------------------------
    below_useful = [float(r["duration_below_useful_floor"]) for r in p02]
    per_run_zero = {
        "nonterminal_handoff_epoch_count": max(
            int(r["nonterminal_handoff_epoch_count"]) for r in p02),
        "nonterminal_activation_request_count": max(
            int(r["nonterminal_activation_request_count"]) for r in p02),
        "nonterminal_lease_count": max(int(r["nonterminal_lease_count"]) for r in p02),
        "nonterminal_reassignment_request_count": max(
            int(r["nonterminal_reassignment_request_count"]) for r in p02),
        "duplicate_nonce_count": max(int(r["duplicate_nonce_count"]) for r in p02),
        "post_round_evaluation_record_count": max(
            int(r["post_round_evaluation_record_count"]) for r in p02),
        "physical_frontier_rewind_count": max(
            int(r["physical_frontier_rewind_count"]) for r in p02),
    }
    hu5_checks = {
        "mean_duration_below_useful_floor_le_15s":
            (statistics.fmean(below_useful), statistics.fmean(below_useful) <= 15.0),
        **{f"{k}_zero_every_run": (v, v == 0) for k, v in per_run_zero.items()},
    }
    hu5_pass = all(ok for _v, ok in hu5_checks.values())

    licensed = hu1_pass and hu2_pass and hu3_pass and hu5_pass and integrity_ok

    # ---- descriptive scenario means -------------------------------------------------
    def num(rows, f):
        vals = [float(r[f]) for r in rows if r.get(f) not in ("", None, "None")]
        return statistics.fmean(vals) if vals else None

    DESC_FIELDS = (
        "E_idle_kwh", "rounds_executed", "rounds_accepted",
        "accepted_blocks_per_closed_round", "median_round_duration",
        "mean_round_duration", "p95_round_duration", "total_physical_evaluations",
        "unique_physical_evaluations", "duplicate_physical_evaluations",
        "blocks_per_million_physical_evaluations", "energy_per_accepted_block_kwh",
        "activation_requests_seated", "incomplete_activation_request_count",
        "activations_per_closed_round", "reassignments_per_closed_round",
        "handoffs_per_closed_round", "duration_below_static_floor",
        "static_floor_deficit_area_hash_s", "duration_below_useful_floor",
        "useful_floor_deficit_area", "handoff_epoch_count", "handoff_committed_count",
        "handoff_completed_count", "handoff_cancelled_count",
        "duplicate_handoff_prevented_count", "single_reserve_requests_seated",
        "reserve_wake_rejected_short_useful_window",
        "reserve_wake_rejected_awake_receiver_available",
        "reserve_wake_rejected_no_bound_work", "relative_reduction")
    means = {sid: {f: num(rs, f) for f in DESC_FIELDS} for sid, rs in by.items()}

    results = {
        "harness": "analyze_8u.py",
        "input_dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "analysis_seed_root": ROOT_SEED, "bootstrap_resamples": B, "n_seeds": N,
        "holm_family": holm_out,
        "contrasts": {"P02_vs_P01_requests": c_req, "P02_vs_P01_incomplete": c_inc,
                      "P02_vs_W01_blocks": c_blocks, "P02_vs_W01_energy": c_energy},
        "H_U1": {"checks": {k: {"value": v, "pass": ok}
                            for k, (v, ok) in hu1_checks.items()},
                 "decision": "PASS" if hu1_pass else "FAIL"},
        "H_U2": {"checks": {k: {"value": v, "pass": ok}
                            for k, (v, ok) in hu2_checks.items()},
                 "decision": "PASS" if hu2_pass else "FAIL"},
        "H_U3": {"checks": {k: {"value": v, "pass": ok}
                            for k, (v, ok) in hu3_checks.items()},
                 "paired_relative_reduction": b_rel,
                 "decision": "PASS" if hu3_pass else "FAIL"},
        "H_U4_sensitivity": hu4,
        "H_U5": {"checks": {k: {"value": v, "pass": ok}
                            for k, (v, ok) in hu5_checks.items()},
                 "decision": "PASS" if hu5_pass else "FAIL"},
        "single_handoff_policy_claim_licensed": licensed,
        "integrity_all_pass": integrity_ok,
        "scenario_means_descriptive": means,
    }
    (HERE / "stage8u_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True, default=str) + "\n")

    # ---- hypothesis decision CSV ----------------------------------------------------
    dec = []

    def add(h, crit, val, ok):
        dec.append({"hypothesis": h, "criterion": crit, "value": val, "pass": ok})

    for k, (v, ok) in hu1_checks.items():
        add("H-U1", k, f"{v:.4f}", ok)
    add("H-U1", "DECISION", results["H_U1"]["decision"], hu1_pass)
    for k, (v, ok) in hu2_checks.items():
        add("H-U2", k, f"{v:.4f}", ok)
    add("H-U2", "DECISION", results["H_U2"]["decision"], hu2_pass)
    for k, (v, ok) in hu3_checks.items():
        add("H-U3", k, f"{v:.4f}", ok)
    add("H-U3", "DECISION", results["H_U3"]["decision"], hu3_pass)
    add("H-U4", "sensitivity_only_no_gate",
        f"rel energy vs W00 {b_rel_w00['mean']:.4f} "
        f"(CI [{b_rel_w00['ci95_lower']:.4f}, {b_rel_w00['ci95_upper']:.4f}])", "")
    for k, (v, ok) in hu5_checks.items():
        add("H-U5", k, f"{v:.4f}" if isinstance(v, float) else str(v), ok)
    add("H-U5", "DECISION", results["H_U5"]["decision"], hu5_pass)
    for name, h in holm_out.items():
        add("HOLM", name, f"p={h['p']:.6f} thr={h['holm_threshold']:.6f}",
            h["reject_null"])
    add("OVERALL", "single-handoff policy claim "
        "(H-U1 AND H-U2 AND H-U3 AND H-U5 AND integrity)",
        "LICENSED" if licensed else "NOT LICENSED", licensed)
    write_csv(DOCS / "STAGE_08U_HYPOTHESIS_DECISIONS.csv", dec)

    # ---- POW_POCOL_COMPARISON_TABLE.csv ---------------------------------------------
    kind = {W00: ("MATCHED_POW_CONTROL", "population-matched"),
            W01: ("MATCHED_POW_CONTROL", "active-capacity-matched (artificial)"),
            P00: ("POCOL_CONTROL", "same frozen core, floor disabled"),
            P01: ("POCOL_BASELINE", "same frozen core, Stage-8S coarse policy"),
            P02: ("POCOL_PRIMARY", "same frozen core, single-handoff policy")}
    limits = {
        W00: "controlled simulator control; not a claim about any deployed network",
        W01: "ARTIFICIAL capacity-matched construction; answers a different question "
             "from W00; never merged with it",
        P00: "PoCol control without the operational floor",
        P01: "frozen Stage-8S baseline re-run on fresh Stage-8U seeds",
        P02: "the single-handoff useful-work policy within PoCol"}
    rows = []
    for sid in (W00, W01, P00, P01, P02):
        m = means[sid]
        rows.append({
            "scenario_id": sid, "comparison_type": kind[sid][0],
            "matching_kind": kind[sid][1], "same_seed_set": "TRUE",
            "same_target_and_difficulty": "TRUE", "same_horizon": "TRUE",
            "same_power_values": "TRUE",
            "primary_or_sensitivity": ("PRIMARY_GATE_CONTROL" if sid == W01 else
                                       "SENSITIVITY" if sid == W00 else
                                       "PRIMARY" if sid == P02 else "CONTEXT"),
            "mean_total_energy_kwh": m["E_idle_kwh"],
            "mean_accepted_blocks": m["rounds_accepted"],
            "mean_closed_rounds": m["rounds_executed"],
            "mean_median_round_duration_s": m["median_round_duration"],
            "mean_p95_round_duration_s": m["p95_round_duration"],
            "mean_total_physical_evaluations": m["total_physical_evaluations"],
            "mean_unique_physical_evaluations": m["unique_physical_evaluations"],
            "mean_duplicate_physical_evaluations": m["duplicate_physical_evaluations"],
            "mean_blocks_per_million_evaluations":
                m["blocks_per_million_physical_evaluations"],
            "mean_energy_per_accepted_block_kwh": m["energy_per_accepted_block_kwh"],
            "interpretation_limit": limits[sid]})
    write_csv(DOCS / "POW_POCOL_COMPARISON_TABLE.csv", rows)

    # ---- POW_POCOL_EFFECT_ESTIMATES.csv ---------------------------------------------
    rows = []

    def eff(label, contrast, ctrl_sid, primary, holm_name=None):
        h = holm_out.get(holm_name) if holm_name else None
        rows.append({
            "contrast": label, "field": contrast["field"],
            "treatment": P02, "control": ctrl_sid,
            "matching_kind": kind[ctrl_sid][1],
            "same_seed_pairing": "TRUE", "same_target_and_difficulty": "TRUE",
            "same_horizon": "TRUE", "same_power_values": "TRUE",
            "primary_or_sensitivity": primary,
            "treatment_mean": contrast["treatment_mean"],
            "control_mean": contrast["control_mean"],
            "paired_mean_difference": contrast["paired_mean_difference"],
            "ci95_lower": contrast["ci95_difference"][0],
            "ci95_upper": contrast["ci95_difference"][1],
            "exact_p_two_sided": contrast["exact_p_two_sided"],
            "holm_reject": (h["reject_null"] if h else ""),
            "interpretation_limit": limits[ctrl_sid]})

    eff("P02 vs P01 activation requests", c_req, P01, "PRIMARY(Holm)",
        "P02_vs_P01(activation_requests_seated)")
    eff("P02 vs P01 incomplete requests", c_inc, P01, "PRIMARY(Holm)",
        "P02_vs_P01(incomplete_requests)")
    eff("P02 vs W01 accepted blocks", c_blocks, W01, "PRIMARY(Holm)",
        "P02_vs_W01(accepted_blocks)")
    eff("P02 vs W01 total energy", c_energy, W01, "PRIMARY(Holm)",
        "P02_vs_W01(total_energy)")
    eff("P02 vs W00 total energy", s_energy, W00, "SENSITIVITY")
    eff("P02 vs W00 accepted blocks", s_blocks, W00, "SENSITIVITY")
    eff("P02 vs W00 median round duration", s_med, W00, "SENSITIVITY")
    eff("P02 vs W00 total evaluations", s_tot, W00, "SENSITIVITY")
    eff("P02 vs W00 unique evaluations", s_uni, W00, "SENSITIVITY")
    eff("P02 vs W00 duplicate evaluations", s_dup, W00, "SENSITIVITY")
    eff("P02 vs W00 energy per accepted block", s_epb, W00, "SENSITIVITY")
    write_csv(DOCS / "POW_POCOL_EFFECT_ESTIMATES.csv", rows)

    print(json.dumps({"licensed": licensed,
                      "H_U1": results["H_U1"]["decision"],
                      "H_U2": results["H_U2"]["decision"],
                      "H_U3": results["H_U3"]["decision"],
                      "H_U5": results["H_U5"]["decision"],
                      "holm": {k: v["reject_null"] for k, v in holm_out.items()}},
                     indent=1))
    print(f"H-U1: reass/round {statistics.fmean(reass):.3f}; requests "
          f"{c_req['treatment_mean']:.1f} vs {c_req['control_mean']:.1f} "
          f"(p={c_req['exact_p_two_sided']:.5f}); incomplete "
          f"{c_inc['treatment_mean']:.1f} vs {c_inc['control_mean']:.1f} "
          f"(p={c_inc['exact_p_two_sided']:.5f})")
    print(f"H-U2: blocks ratio {blocks_ratio:.4f}  median-duration ratio {dur_ratio:.4f}")
    print(f"H-U3: paired rel reduction {b_rel['mean']:.4f} "
          f"(CI [{b_rel['ci95_lower']:.4f}, {b_rel['ci95_upper']:.4f}])")
    print(f"H-U5: below-useful {statistics.fmean(below_useful):.2f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
