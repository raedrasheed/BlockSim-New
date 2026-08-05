#!/usr/bin/env python3
"""Stage 8S — frozen analysis (executes STAGE_08S_PREREGISTRATION.md verbatim).

Input: ONLY the frozen 48-row STAGE_08S_RUN_DATASET.csv.  n = 12 fresh paired seeds; 4096
exact sign assignments; 10 000 paired bootstrap resamples; percentile 95 % CI; bootstrap
root 16767666002914861861; Holm at alpha = 0.05 over exactly {H-S1 accepted_blocks,
H-S3 activation-request contrast, H-S3 incomplete-request contrast}.
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
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08s"
DATASET = DOCS / "STAGE_08S_RUN_DATASET.csv"
sys.path.insert(0, str(HERE))
import scenarios_8s as S8S                                                 # noqa: E402
sys.path.insert(0, str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r"))
from scenarios_8r import COMPONENTS                                        # noqa: E402

ROOT_SEED = S8S.ANALYSIS_SEED_8S
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


def exact_p(d: list) -> float:
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


def paired(treat, ctrl, field, direction, label) -> dict:
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
            "exact_p_one_sided": exact_p(oriented),
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
    s00, s01, s02, s03 = (by["S00_NO_FLOOR"], by["S01_STAGE8R_STATIC_FLOOR"],
                          by["S02_USEFUL_FLOOR"],
                          by["S03_USEFUL_FLOOR_COARSE_REASSIGNMENT"])
    integrity_ok = all(r["run_status"] == "COMPLETED"
                       and r["all_integrity_gates_pass"] == "True"
                       for rs in by.values() for r in rs)
    if not integrity_ok:
        print("STAGE_8S_BLOCKED — integrity failure in the frozen dataset")
        return 2

    # ---- H-S1 throughput recovery: S03 vs S01, accepted_blocks, greater ------------
    hs1 = paired(s03, s01, "rounds_accepted", "greater", "HS1:accepted_blocks")

    # ---- H-S3 churn: deterministic bound + two Holm contrasts ----------------------
    reass_rate = [float(r["reassignments_per_closed_round"]) for r in s03]
    hs3_requests = paired(s03, s01, "activation_requests_seated", "less", "HS3:requests")
    hs3_incomplete = paired(s03, s01, "incomplete_activation_request_count", "less",
                            "HS3:incomplete")
    rejected = [float(r["reserve_wakes_rejected_no_useful_work"]) for r in s03]

    holm_out = holm({"H-S1(accepted_blocks)": hs1["exact_p_one_sided"],
                     "H-S3(activation_requests_seated)": hs3_requests["exact_p_one_sided"],
                     "H-S3(incomplete_requests)": hs3_incomplete["exact_p_one_sided"]})

    hs3_checks = {
        "mean_reassignments_per_closed_round_le_1.0":
            (statistics.fmean(reass_rate), statistics.fmean(reass_rate) <= 1.0),
        "mean_activation_requests_seated_lt_S01":
            (hs3_requests["treatment_mean"],
             hs3_requests["treatment_mean"] < hs3_requests["control_mean"]),
        "holm_reject_activation_requests_contrast":
            (holm_out["H-S3(activation_requests_seated)"]["p"],
             holm_out["H-S3(activation_requests_seated)"]["reject_null"]),
        "mean_incomplete_requests_lt_S01":
            (hs3_incomplete["treatment_mean"],
             hs3_incomplete["treatment_mean"] < hs3_incomplete["control_mean"]),
        "holm_reject_incomplete_requests_contrast":
            (holm_out["H-S3(incomplete_requests)"]["p"],
             holm_out["H-S3(incomplete_requests)"]["reject_null"]),
    }
    hs3_pass = all(ok for _v, ok in hs3_checks.values())

    # ---- H-S2 operational usefulness: S03 vs S00 (deterministic) -------------------
    blocks_ratio = [int(t["rounds_accepted"]) / int(c["rounds_accepted"])
                    for t, c in zip(s03, s00)]
    dur_ratio = [float(t["median_round_duration"]) / float(c["median_round_duration"])
                 for t, c in zip(s03, s00)]
    below_useful = [float(t["duration_below_useful_floor"]) for t in s03]
    per_run_zero = {
        "nonterminal_activation_request_count": max(
            int(r["nonterminal_activation_request_count"]) for r in s03),
        "nonterminal_reassignment_request_count": max(
            int(r["nonterminal_reassignment_request_count"]) for r in s03),
        "nonterminal_lease_count": max(int(r["nonterminal_lease_count"]) for r in s03),
        "duplicate_nonce_count": max(int(r["duplicate_nonce_count"]) for r in s03),
        "post_round_evaluation_record_count": max(
            int(r["post_round_evaluation_record_count"]) for r in s03),
        "physical_frontier_rewind_count": max(
            int(r["physical_frontier_rewind_count"]) for r in s03),
    }
    hs2_checks = {
        "mean_accepted_blocks_ratio_S03_over_S00_ge_0.90":
            (statistics.fmean(blocks_ratio), statistics.fmean(blocks_ratio) >= 0.90),
        "mean_median_round_duration_ratio_le_1.10":
            (statistics.fmean(dur_ratio), statistics.fmean(dur_ratio) <= 1.10),
        "mean_duration_below_useful_floor_le_15s":
            (statistics.fmean(below_useful),
             statistics.fmean(below_useful) <= 0.05 * HORIZON),
        **{f"{k}_zero_every_run": (v, v == 0) for k, v in per_run_zero.items()},
    }
    hs2_pass = all(ok for _v, ok in hs2_checks.values())

    # ---- H-S4 retained energy benefit (S03 within-run power null) ------------------
    rel = [float(r["relative_reduction"]) for r in s03]
    absd = [float(r["absolute_reduction_kwh"]) for r in s03]
    b_rel = boot(rel, "HS4:relative")
    b_abs = boot(absd, "HS4:absolute")
    hs4_pass = (b_rel["mean"] >= 0.20) and (b_abs["ci95_lower"] > 0.0)
    components = {name: statistics.fmean(float(r[name]) for r in s03)
                  for name in ("range_idle_energy_difference_kwh",
                               "reserve_standby_energy_difference_kwh",
                               "wake_energy_difference_kwh",
                               "activated_reserve_energy_kwh")}

    licensed = hs2_pass and hs3_pass and hs4_pass and integrity_ok

    def desc(rows):
        num = lambda f: statistics.fmean(float(r[f]) for r in rows)
        return {f: num(f) for f in (
            "rounds_accepted", "rounds_executed", "accepted_blocks_per_closed_round",
            "median_round_duration", "mean_round_duration", "p95_round_duration",
            "unclosed_final_tail_s", "duration_below_static_floor",
            "duration_below_useful_floor", "static_floor_deficit_area_hash_s",
            "useful_floor_deficit_area", "static_floor_unattainable_count",
            "useful_floor_unattainable_count", "H_useful_available_time_weighted",
            "H_useful_target_time_weighted", "activation_requests_seated",
            "activation_requests_completed", "incomplete_activation_request_count",
            "activations_per_closed_round", "reassignments_per_closed_round",
            "coarse_repartition_count", "coarse_reassignment_count",
            "mean_coarse_chunk_size", "minimum_coarse_chunk_size",
            "maximum_coarse_chunk_size", "donor_lineage_repartition_replay_count",
            "duplicate_reassignment_prevented_count",
            "reserve_wakes_rejected_no_useful_work", "reserve_wakes_with_bound_work",
            "reserve_wake_useful_completion_ratio", "E_idle_kwh", "relative_reduction",
            "range_idle_energy_difference_kwh", "reserve_standby_energy_difference_kwh",
            "wake_energy_difference_kwh", "activated_reserve_energy_kwh",
            "breach_episode_count", "activation_batches_seated",
            "duplicate_activation_batch_prevented_count", "prediction_decision_count",
            "maximum_H_pipeline", "time_weighted_H_pipeline")}
    means = {sid: desc(rs) for sid, rs in by.items()}

    results = {
        "harness": "analyze_8s.py",
        "input_dataset_sha256": hashlib.sha256(DATASET.read_bytes()).hexdigest(),
        "analysis_seed_root": ROOT_SEED, "bootstrap_resamples": B, "n_seeds": N,
        "H_S1": {**hs1, "holm": holm_out["H-S1(accepted_blocks)"]},
        "H_S2": {"checks": {k: {"value": v, "pass": ok} for k, (v, ok) in hs2_checks.items()},
                 "decision": "PASS" if hs2_pass else "FAIL",
                 "blocks_ratio_per_seed": blocks_ratio},
        "H_S3": {"checks": {k: {"value": v, "pass": ok} for k, (v, ok) in hs3_checks.items()},
                 "requests_contrast": hs3_requests, "incomplete_contrast": hs3_incomplete,
                 "reserve_wakes_rejected_no_useful_work_mean": statistics.fmean(rejected),
                 "decision": "PASS" if hs3_pass else "FAIL"},
        "H_S4": {"mean_relative": b_rel, "mean_absolute_kwh": b_abs,
                 "components_mean_kwh": components,
                 "decision": "PASS" if hs4_pass else "FAIL"},
        "holm_family": holm_out,
        "structural_policy_claim_licensed": licensed,
        "integrity_all_pass": integrity_ok,
        "scenario_means_descriptive": means,
    }
    (HERE / "stage8s_results.json").write_text(
        json.dumps(results, indent=1, sort_keys=True, default=str) + "\n")

    # ---- decision CSV ---------------------------------------------------------------
    dec = []
    def add(h, crit, val, ok):
        dec.append({"hypothesis": h, "criterion": crit, "value": val, "pass": ok})
    add("H-S1", "accepted_blocks S03 > S01 (Holm)",
        f"{hs1['paired_mean_difference']:+.3f} (CI {hs1['ci95_difference']}), "
        f"p={hs1['exact_p_one_sided']:.6f}", holm_out["H-S1(accepted_blocks)"]["reject_null"])
    for k, (v, ok) in hs2_checks.items():
        add("H-S2", k, f"{v:.4f}" if isinstance(v, float) else str(v), ok)
    add("H-S2", "DECISION", results["H_S2"]["decision"], hs2_pass)
    for k, (v, ok) in hs3_checks.items():
        add("H-S3", k, f"{v:.4f}" if isinstance(v, float) else str(v), ok)
    add("H-S3", "reserve_wakes_rejected_no_useful_work (reported)",
        f"mean {statistics.fmean(rejected):.2f}", "")
    add("H-S3", "DECISION", results["H_S3"]["decision"], hs3_pass)
    add("H-S4", "mean relative low-power-state difference >= 0.20",
        f"{b_rel['mean']:.4f} (CI [{b_rel['ci95_lower']:.4f}, {b_rel['ci95_upper']:.4f}])",
        b_rel["mean"] >= 0.20)
    add("H-S4", "bootstrap lower bound of mean absolute difference > 0",
        f"{b_abs['ci95_lower']:.6f} kWh", b_abs["ci95_lower"] > 0.0)
    add("H-S4", "DECISION", results["H_S4"]["decision"], hs4_pass)
    add("OVERALL", "structural-policy claim (H-S2 AND H-S3 AND H-S4 AND integrity)",
        "LICENSED" if licensed else "NOT LICENSED", licensed)
    write_csv(DOCS / "STAGE_08S_HYPOTHESIS_DECISIONS.csv", dec)

    # ---- static + useful floor results ----------------------------------------------
    rows = []
    for sid, m in sorted(means.items()):
        rows.append({"scenario_id": sid,
                     **{k: m[k] for k in (
                         "duration_below_static_floor", "static_floor_deficit_area_hash_s",
                         "static_floor_unattainable_count", "duration_below_useful_floor",
                         "useful_floor_deficit_area", "useful_floor_unattainable_count",
                         "H_useful_available_time_weighted",
                         "H_useful_target_time_weighted")}})
    write_csv(DOCS / "STAGE_08S_STATIC_AND_USEFUL_FLOOR_RESULTS.csv", rows)

    # ---- reassignment report ---------------------------------------------------------
    rows = []
    for sid, m in sorted(means.items()):
        rows.append({"scenario_id": sid,
                     **{k: m[k] for k in (
                         "coarse_repartition_count", "coarse_reassignment_count",
                         "reassignments_per_closed_round", "mean_coarse_chunk_size",
                         "minimum_coarse_chunk_size", "maximum_coarse_chunk_size",
                         "donor_lineage_repartition_replay_count",
                         "duplicate_reassignment_prevented_count",
                         "activation_requests_seated", "incomplete_activation_request_count",
                         "reserve_wakes_rejected_no_useful_work",
                         "reserve_wake_useful_completion_ratio")}})
    write_csv(DOCS / "STAGE_08S_REASSIGNMENT_REPORT.csv", rows)

    # ---- energy decomposition --------------------------------------------------------
    rows = []
    for sid, rs in sorted(by.items()):
        for c in COMPONENTS:
            rows.append({"scenario_id": sid, "component": c,
                         "mean_residency_s": statistics.fmean(
                             float(r[f"residency_{c}_s"]) for r in rs),
                         "mean_energy_kwh": statistics.fmean(
                             float(r[f"energy_{c}_kwh"]) for r in rs),
                         "mean_power_null_difference_kwh": statistics.fmean(
                             float(r[f"power_null_difference_{c}_kwh"]) for r in rs)})
    write_csv(DOCS / "STAGE_08S_ENERGY_DECOMPOSITION.csv", rows)

    print(json.dumps({"licensed": licensed,
                      "H_S2": results["H_S2"]["decision"],
                      "H_S3": results["H_S3"]["decision"],
                      "H_S4": results["H_S4"]["decision"],
                      "holm": {k: v["reject_null"] for k, v in holm_out.items()}}, indent=1))
    print(f"H-S1: S03 {hs1['treatment_mean']:.1f} vs S01 {hs1['control_mean']:.1f} "
          f"d={hs1['paired_mean_difference']:+.2f} p={hs1['exact_p_one_sided']:.5f}")
    print(f"H-S2: blocks ratio {statistics.fmean(blocks_ratio):.4f}  dur ratio "
          f"{statistics.fmean(dur_ratio):.4f}  below-useful {statistics.fmean(below_useful):.2f}s")
    print(f"H-S3: requests {hs3_requests['treatment_mean']:.1f} vs "
          f"{hs3_requests['control_mean']:.1f} (p={hs3_requests['exact_p_one_sided']:.5f}); "
          f"incomplete {hs3_incomplete['treatment_mean']:.1f} vs "
          f"{hs3_incomplete['control_mean']:.1f} (p={hs3_incomplete['exact_p_one_sided']:.5f}); "
          f"reass/round {statistics.fmean(reass_rate):.3f}")
    print(f"H-S4: rel {b_rel['mean']:.4f}  abs CI lower {b_abs['ci95_lower']:.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
