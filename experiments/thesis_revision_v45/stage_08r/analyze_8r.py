#!/usr/bin/env python3
"""Stage 8R — preregistered analysis (executes STAGE_08R_PREREGISTRATION.md verbatim).

Input: ONLY the frozen 48-row STAGE_08R_RUN_DATASET.csv.
n = 12 paired fresh seeds; all 2^12 = 4096 exact sign assignments (one-sided in the
preregistered direction); 10 000 paired bootstrap resamples; percentile 95 % CI
(lower = 250th, upper = 9 750th order statistic); bootstrap RNG root 5792508466225871155
with labeled substreams; Holm correction within the primary family {H-R1, H-R2, H-R3}.
R03 is EXPLORATORY: its rows enter descriptive tables only, never an estimator or verdict.
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
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08r"
DATASET = DOCS / "STAGE_08R_RUN_DATASET.csv"

sys.path.insert(0, str(HERE))
import scenarios_8r as S8                                                  # noqa: E402

ROOT_SEED = S8.ANALYSIS_SEED_8R          # 5792508466225871155 (frozen)
B = 10_000
N = 12
ALPHA = 0.05
HORIZON = 300.0


def load() -> dict:
    with open(DATASET, newline="") as fh:
        rows = list(csv.DictReader(fh))
    assert len(rows) == 48
    by = {}
    for r in rows:
        by.setdefault(r["scenario_id"], []).append(r)
    for sid, rs in by.items():
        rs.sort(key=lambda r: int(r["seed_index"]))
        assert [int(r["seed_index"]) for r in rs] == list(range(N)), sid
    return by


def exact_p_one_sided(d: list) -> float:
    """P(mean(s*d) >= mean(d)) over ALL 2^n sign assignments (direction: positive)."""
    obs = statistics.fmean(d)
    count = 0
    for mask in range(1 << len(d)):
        m = statistics.fmean(x if (mask >> i) & 1 == 0 else -x for i, x in enumerate(d))
        if m >= obs - 1e-15:
            count += 1
    return count / (1 << len(d))


def boot(values: list, label: str) -> dict:
    rng = random.Random(f"{ROOT_SEED}:{label}")
    n = len(values)
    stats = sorted(statistics.fmean([values[rng.randrange(n)] for _ in range(n)])
                   for _ in range(B))
    return {"mean": statistics.fmean(values), "median": statistics.median(values),
            "ci95_lower": stats[249], "ci95_upper": stats[9749]}


def paired(treat: list, ctrl: list, field: str, direction: str, label: str) -> dict:
    """Paired contrast; ``direction`` is the PREREGISTERED expected direction of
    treatment-minus-control ('greater' or 'less').  The one-sided p is computed in that
    direction by orienting d so the expected direction is positive."""
    t = [float(x[field]) for x in treat]
    c = [float(x[field]) for x in ctrl]
    d = [a - b for a, b in zip(t, c)]
    oriented = d if direction == "greater" else [-x for x in d]
    bd = boot(d, f"{label}:d")
    return {"field": field, "direction_expected": direction,
            "treatment_mean": statistics.fmean(t), "control_mean": statistics.fmean(c),
            "paired_mean_difference": bd["mean"],
            "paired_median_difference": statistics.median(d),
            "ci95_difference": [bd["ci95_lower"], bd["ci95_upper"]],
            "exact_p_one_sided": exact_p_one_sided(oriented),
            "direction_observed": ("greater" if bd["mean"] > 0
                                   else "less" if bd["mean"] < 0 else "equal"),
            "per_seed_difference": d}


def holm(named_ps: dict) -> dict:
    items = sorted(named_ps.items(), key=lambda kv: kv[1])
    m = len(items)
    out = {}
    all_prior = True
    for i, (name, p) in enumerate(items):
        threshold = ALPHA / (m - i)
        reject = all_prior and (p <= threshold)
        out[name] = {"p": p, "holm_threshold": threshold, "reject_null": reject}
        all_prior = all_prior and reject
    return out


def write_csv(dest: pathlib.Path, rows: list) -> None:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=list(rows[0].keys()), lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    dest.write_text(buf.getvalue())
    print(f"wrote {dest.relative_to(REPO_ROOT)} ({len(rows)} rows)")


def main() -> int:
    by = load()
    dataset_sha = hashlib.sha256(DATASET.read_bytes()).hexdigest()
    r00, r01, r02, r03 = (by["R00_NO_FLOOR"], by["R01_LEGACY_FLOOR"],
                          by["R02_REVISED_CONTROLLER"],
                          by["R03_REVISED_PLUS_REASSIGNMENT"])

    # ---- integrity gates first ------------------------------------------------------
    integrity_ok = all(r["run_status"] == "COMPLETED"
                       and r["all_integrity_gates_pass"] == "True"
                       for rs in by.values() for r in rs)
    if not integrity_ok:
        print("STAGE_8R_BLOCKED — integrity failure in the frozen dataset")
        return 2

    # ---- H-R1 service recovery (R02 vs R01, direction greater) ----------------------
    hr1 = paired(r02, r01, "rounds_accepted", "greater", "HR1:accepted_blocks")

    # ---- H-R2 floor recovery (R02 vs R01, direction less) ---------------------------
    hr2 = {f: paired(r02, r01, f, "less", f"HR2:{f}")
           for f in ("total_duration_below_floor", "floor_deficit_area_hash_s",
                     "floor_unattainable_count")}

    # ---- H-R3 activation churn (R02 vs R01, direction less) -------------------------
    # R01's batch equivalent: every legacy seated request is its own decision batch
    # (declared in the preregistration), so the batch contrast uses R01's request count.
    r01_batches = [dict(r, activation_batches_seated=r["activation_requests_seated"])
                   for r in r01]
    hr3 = {
        "activation_batches_seated": paired(r02, r01_batches, "activation_batches_seated",
                                            "less", "HR3:batches"),
        "activation_requests_seated": paired(r02, r01, "activation_requests_seated",
                                             "less", "HR3:requests"),
        "incomplete_activation_request_count": paired(
            r02, r01, "incomplete_activation_request_count", "less", "HR3:incomplete"),
        "activations_per_closed_round": paired(
            r02, r01, "activations_per_closed_round", "less", "HR3:per_round"),
    }

    # ---- Holm within the primary family (declared inputs) ---------------------------
    family = {"H-R1(accepted_blocks)": hr1["exact_p_one_sided"],
              "H-R2(total_duration_below_floor)":
                  hr2["total_duration_below_floor"]["exact_p_one_sided"],
              "H-R3(activation_requests_seated)":
                  hr3["activation_requests_seated"]["exact_p_one_sided"]}
    holm_out = holm(family)

    # ---- H-R4 operational acceptance (deterministic; vs R00 same seed) --------------
    blocks_ratio = [int(t["rounds_accepted"]) / int(c["rounds_accepted"])
                    for t, c in zip(r02, r00)]
    dur_ratio = [float(t["median_round_duration"]) / float(c["median_round_duration"])
                 for t, c in zip(r02, r00)]
    below = [float(t["total_duration_below_floor"]) for t in r02]
    hr4_checks = {
        "mean_accepted_blocks_ratio_R02_over_R00_ge_0.90":
            (statistics.fmean(blocks_ratio), statistics.fmean(blocks_ratio) >= 0.90),
        "mean_median_round_duration_ratio_R02_over_R00_le_1.10":
            (statistics.fmean(dur_ratio), statistics.fmean(dur_ratio) <= 1.10),
        "mean_total_duration_below_floor_R02_le_15s":
            (statistics.fmean(below), statistics.fmean(below) <= 0.05 * HORIZON),
        "nonterminal_activation_request_count_zero_every_run":
            (max(int(r["nonterminal_activation_request_count"]) for r in r02), True)
            if max(int(r["nonterminal_activation_request_count"]) for r in r02) == 0
            else (max(int(r["nonterminal_activation_request_count"]) for r in r02), False),
        "duplicate_nonce_count_zero_every_run":
            (max(int(r["duplicate_nonce_count"]) for r in r02),
             max(int(r["duplicate_nonce_count"]) for r in r02) == 0),
        "post_round_evaluation_record_count_zero_every_run":
            (max(int(r["post_round_evaluation_record_count"]) for r in r02),
             max(int(r["post_round_evaluation_record_count"]) for r in r02) == 0),
    }
    hr4_pass = all(ok for _v, ok in hr4_checks.values())

    # ---- H-R5 retained energy benefit (R02 within-run power null) -------------------
    rel = [float(r["relative_reduction"]) for r in r02]
    absd = [float(r["absolute_reduction_kwh"]) for r in r02]
    b_rel = boot(rel, "HR5:relative")
    b_abs = boot(absd, "HR5:absolute")
    hr5_pass = (b_rel["mean"] >= 0.20) and (b_abs["ci95_lower"] > 0.0)
    hr5 = {"mean_relative_reduction": b_rel["mean"],
           "ci95_relative": [b_rel["ci95_lower"], b_rel["ci95_upper"]],
           "mean_absolute_reduction_kwh": b_abs["mean"],
           "ci95_absolute_kwh": [b_abs["ci95_lower"], b_abs["ci95_upper"]],
           "criteria": {"mean_relative_ge_0.20": b_rel["mean"] >= 0.20,
                        "ci95_lower_of_mean_abs_gt_0": b_abs["ci95_lower"] > 0.0},
           "decision": "PASS" if hr5_pass else "FAIL"}

    licensed = hr4_pass and hr5_pass and integrity_ok

    # ---- descriptive per-scenario means (final-report table; R03 descriptive) -------
    def desc(rows):
        num = lambda f: statistics.fmean(float(r[f]) for r in rows)
        return {f: num(f) for f in (
            "rounds_accepted", "rounds_executed", "accepted_blocks_per_closed_round",
            "median_round_duration", "mean_round_duration", "p95_round_duration",
            "unclosed_final_tail_s", "total_duration_below_floor",
            "floor_deficit_area_hash_s", "floor_unattainable_count",
            "activation_requests_seated", "activation_requests_completed",
            "activation_requests_cancelled", "incomplete_activation_request_count",
            "activations_per_closed_round", "activation_batches_seated",
            "breach_episode_count", "duplicate_activation_batch_prevented_count",
            "mean_activation_batches_per_episode", "prediction_decision_count",
            "mean_absolute_prediction_error", "false_positive_wake_count",
            "late_wake_count", "maximum_H_pipeline", "time_weighted_H_pipeline",
            "duration_pipeline_above_target_while_H_effective_below_target",
            "controller_suffix_reassignment_count",
            "E_idle_kwh", "E_power_null_kwh", "relative_reduction",
            "range_idle_energy_difference_kwh", "reserve_standby_energy_difference_kwh",
            "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
            "total_low_power_state_difference_kwh", "duplicate_nonce_count",
            "post_round_evaluation_record_count")}
    scenario_means = {sid: desc(rs) for sid, rs in by.items()}

    results = {
        "harness": "analyze_8r.py",
        "input_dataset_sha256": dataset_sha,
        "analysis_seed_root": ROOT_SEED, "bootstrap_resamples": B, "n_seeds": N,
        "H_R1": hr1, "H_R2": hr2, "H_R3": hr3,
        "holm_family_alpha_0.05": holm_out,
        "H_R4": {"checks": {k: {"value": v, "pass": ok}
                            for k, (v, ok) in hr4_checks.items()},
                 "decision": "PASS" if hr4_pass else "FAIL",
                 "blocks_ratio_per_seed": blocks_ratio, "dur_ratio_per_seed": dur_ratio},
        "H_R5": hr5,
        "revised_policy_claim_licensed": licensed,
        "integrity_all_pass": integrity_ok,
        "scenario_means_descriptive": scenario_means,
        "R03_note": "EXPLORATORY — descriptive only; excluded from every estimator, "
                    "Holm family and the verdict",
    }
    (HERE / "stage8r_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True, default=str) + "\n")

    # ---- STAGE_08R_HYPOTHESIS_DECISIONS.csv -----------------------------------------
    dec = []
    def add(h, crit, val, ok):
        dec.append({"hypothesis": h, "criterion": crit, "value": val, "pass": ok})
    add("H-R1", "accepted_blocks R02 > R01 (paired mean diff; Holm-corrected)",
        f"{hr1['paired_mean_difference']:+.3f} (CI {hr1['ci95_difference']}), "
        f"p={hr1['exact_p_one_sided']:.6f}",
        holm_out["H-R1(accepted_blocks)"]["reject_null"])
    for f, c in hr2.items():
        add("H-R2", f"{f} R02 < R01",
            f"{c['paired_mean_difference']:+.3f} (CI {c['ci95_difference']}), "
            f"p={c['exact_p_one_sided']:.6f}",
            (holm_out["H-R2(total_duration_below_floor)"]["reject_null"]
             if f == "total_duration_below_floor" else ""))
    for f, c in hr3.items():
        add("H-R3", f"{f} R02 < R01",
            f"{c['paired_mean_difference']:+.3f} (CI {c['ci95_difference']}), "
            f"p={c['exact_p_one_sided']:.6f}",
            (holm_out["H-R3(activation_requests_seated)"]["reject_null"]
             if f == "activation_requests_seated" else ""))
    for k, (v, ok) in hr4_checks.items():
        add("H-R4", k, f"{v:.4f}" if isinstance(v, float) else str(v), ok)
    add("H-R4", "DECISION", results["H_R4"]["decision"], hr4_pass)
    add("H-R5", "mean relative low-power-state reduction >= 0.20",
        f"{b_rel['mean']:.4f} (CI [{b_rel['ci95_lower']:.4f}, {b_rel['ci95_upper']:.4f}])",
        b_rel["mean"] >= 0.20)
    add("H-R5", "95% bootstrap lower bound of mean absolute reduction > 0",
        f"{b_abs['ci95_lower']:.6f} kWh", b_abs["ci95_lower"] > 0.0)
    add("H-R5", "DECISION", hr5["decision"], hr5_pass)
    add("OVERALL", "revised-policy claim licensed (H-R4 AND H-R5 AND integrity)",
        "LICENSED" if licensed else "NOT LICENSED", licensed)
    write_csv(DOCS / "STAGE_08R_HYPOTHESIS_DECISIONS.csv", dec)

    # ---- STAGE_08R_ENERGY_DECOMPOSITION.csv -----------------------------------------
    rows = []
    for sid, rs in sorted(by.items()):
        for c in S8.COMPONENTS:
            rows.append({
                "scenario_id": sid, "component": c,
                "mean_residency_s": statistics.fmean(
                    float(r[f"residency_{c}_s"]) for r in rs),
                "mean_energy_kwh": statistics.fmean(
                    float(r[f"energy_{c}_kwh"]) for r in rs),
                "mean_power_null_difference_kwh": statistics.fmean(
                    float(r[f"power_null_difference_{c}_kwh"]) for r in rs)})
        for named in ("range_idle_energy_difference_kwh",
                      "reserve_standby_energy_difference_kwh",
                      "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
                      "total_low_power_state_difference_kwh"):
            rows.append({"scenario_id": sid, "component": f"NAMED:{named}",
                         "mean_residency_s": "",
                         "mean_energy_kwh": "",
                         "mean_power_null_difference_kwh": statistics.fmean(
                             float(r[named]) for r in rs)})
    write_csv(DOCS / "STAGE_08R_ENERGY_DECOMPOSITION.csv", rows)

    # ---- STAGE_08R_ACTIVATION_LIFECYCLE_REPORT.csv ----------------------------------
    rows = []
    for sid, rs in sorted(by.items()):
        m = scenario_means[sid]
        rows.append({
            "scenario_id": sid,
            "mean_activation_requests_seated": m["activation_requests_seated"],
            "mean_activation_requests_completed": m["activation_requests_completed"],
            "mean_activation_requests_cancelled": m["activation_requests_cancelled"],
            "mean_incomplete_requests": m["incomplete_activation_request_count"],
            "completion_ratio": (m["activation_requests_completed"]
                                 / m["activation_requests_seated"]
                                 if m["activation_requests_seated"] else ""),
            "mean_activations_per_closed_round": m["activations_per_closed_round"],
            "mean_activation_batches_seated": m["activation_batches_seated"],
            "mean_breach_episode_count": m["breach_episode_count"],
            "mean_batches_per_episode": m["mean_activation_batches_per_episode"],
            "mean_duplicate_batch_prevented": m["duplicate_activation_batch_prevented_count"],
            "mean_prediction_decisions": m["prediction_decision_count"],
            "mean_absolute_prediction_error": m["mean_absolute_prediction_error"],
            "mean_false_positive_wakes": m["false_positive_wake_count"],
            "mean_late_wakes": m["late_wake_count"],
            "mean_suffix_reassignments": m["controller_suffix_reassignment_count"],
        })
    write_csv(DOCS / "STAGE_08R_ACTIVATION_LIFECYCLE_REPORT.csv", rows)

    print(json.dumps({"licensed": licensed, "H_R4": results["H_R4"]["decision"],
                      "H_R5": hr5["decision"], "holm": {k: v["reject_null"]
                                                        for k, v in holm_out.items()}},
                     indent=1))
    print(f"H-R1 accepted: R02 {hr1['treatment_mean']:.1f} vs R01 "
          f"{hr1['control_mean']:.1f}  d={hr1['paired_mean_difference']:+.2f}  "
          f"p={hr1['exact_p_one_sided']:.5f}")
    print(f"H-R2 below-floor: R02 {hr2['total_duration_below_floor']['treatment_mean']:.1f}"
          f" vs R01 {hr2['total_duration_below_floor']['control_mean']:.1f}  "
          f"p={hr2['total_duration_below_floor']['exact_p_one_sided']:.5f}")
    print(f"H-R3 requests: R02 {hr3['activation_requests_seated']['treatment_mean']:.1f} "
          f"vs R01 {hr3['activation_requests_seated']['control_mean']:.1f}  "
          f"p={hr3['activation_requests_seated']['exact_p_one_sided']:.5f}")
    print(f"H-R4 ratios: blocks {statistics.fmean(blocks_ratio):.4f}  "
          f"dur {statistics.fmean(dur_ratio):.4f}  below-floor {statistics.fmean(below):.1f}s")
    print(f"H-R5: rel {b_rel['mean']:.4f}  abs CI lower {b_abs['ci95_lower']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
