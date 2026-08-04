#!/usr/bin/env python3
"""Stage 6 — confirmatory and exploratory scenario-matrix generator.

Emits, deterministically and byte-reproducibly:

    docs/thesis_revision_v45/stage_06/STAGE_06_CONFIRMATORY_MATRIX.csv
    docs/thesis_revision_v45/stage_06/STAGE_06_EXPLORATORY_MATRIX.csv
    experiments/thesis_revision_v45/stage_06/confirmatory/confirmatory_run_registry.csv
    experiments/thesis_revision_v45/stage_06/confirmatory/frozen_configs/<scenario>.json

The matrix rows come from ``scenarios.py``, the single executable source of truth.  Every
per-row parameter written here is read back out of a materialised ACCEPTED ``Stage2Config``,
so the CSV can never disagree with what Stage 7 would actually run.

Stage 6 writes CONFIGURATIONS AND REGISTRIES ONLY.  It executes no confirmatory seed and
writes no run output.

Usage:
    python experiments/thesis_revision_v45/stage_06/generate_confirmatory_matrix.py [--check]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios as S                                          # noqa: E402
from generate_seed_registry import build_rows, child_seed      # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06"
CONF = HERE / "confirmatory"
FROZEN = CONF / "frozen_configs"

#: The minimum row schema the directive fixes, in order.
MATRIX_FIELDS = [
    "scenario_id", "block_id", "confirmatory_or_exploratory", "paired_control_id",
    "hypothesis_ids", "num_miners", "horizon_T", "P_hash", "P_listen", "P_reserve",
    "P_wake", "P_offline", "nonce_domain_size", "difficulty", "batch_size", "base_hash_rate",
    "heterogeneous_hash_rates", "reserve_fraction", "security_floor_policy",
    "range_lease_policy", "adversarial_policy", "incentive_policy", "fault_schedule",
    "primary_outcomes", "secondary_outcomes", "expected_NA_fields", "notes",
]

REGISTRY_FIELDS = [
    "run_id", "scenario_id", "block_id", "pair_id", "master_seed", "seed_index",
    "condition", "control_or_treatment", "template_seed", "adversarial_seed",
    "num_miners", "horizon_T", "difficulty", "config_sha256",
]

#: Per-block declared outcomes, resolved against the ACCEPTED adapter schema (see
#: STAGE_06_OUTCOME_DICTIONARY.csv for the full field-by-field resolution).
PRIMARY_OUTCOMES = {
    "A": "total_energy_kwh",
    "B": "total_duration_below_floor;accepted_blocks_per_horizon",
    "C": "duplicate_nonce_count;work_reward_union_residual",
    "D": "adversarial_reevaluation_count;coverage_gap_nonce_count",
}
SECONDARY_OUTCOMES = {
    "A": "relative_energy_reduction_percent;accepted_blocks;median_round_duration",
    "B": "breach_count;maximum_hash_rate_deficit;reserve_activations_completed;"
         "floor_unattainable_count;median_round_duration",
    "C": "leases_reassigned;reassignment_requests_completed;wake_handles_created;"
         "coverage_gap_nonce_count",
    "D": "total_energy_kwh;accepted_blocks;incentive_reconciliation_residual;"
         "maximum_q_adv;time_weighted_q_adv",
}


def expected_na(row: dict) -> str:
    """Fields preregistered to be NA for this row (NA is never imputed as zero)."""
    na = []
    if row["adversarial_policy"] == "DISABLED":
        na.append("maximum_q_adv")
        na.append("time_weighted_q_adv")
    if row["security_floor_policy"] == "DISABLED":
        na.append("maximum_hash_rate_deficit_when_floor_disabled")
    if row["paired_control_id"] == "NONE":
        # No matched control exists, so every PAIRED quantity is undefined for this row.
        # Note this is NOT a zero-denominator NA: accepted_blocks_per_horizon stays DEFINED
        # (its denominator is horizon_T, which is never zero) and is 0 for a zero-block run.
        na.append("relative_energy_reduction_percent")
    return ";".join(na) if na else "NONE"


def matrix_row(row: dict, cfg) -> dict:
    """Build one CSV row, reading every parameter back out of the materialised config."""
    b = row["block_id"]
    return {
        "scenario_id": row["scenario_id"],
        "block_id": b,
        "confirmatory_or_exploratory": row["confirmatory_or_exploratory"],
        "paired_control_id": row["paired_control_id"],
        "hypothesis_ids": row["hypothesis_ids"],
        "num_miners": cfg.num_miners,
        "horizon_T": cfg.horizon_T,
        "P_hash": cfg.P_hash,
        "P_listen": cfg.P_listen,
        "P_reserve": cfg.P_reserve,
        "P_wake": cfg.P_wake,
        "P_offline": cfg.P_offline,
        "nonce_domain_size": cfg.nonce_domain_size,
        "difficulty": cfg.difficulty,
        "batch_size": cfg.batch_size,
        "base_hash_rate": cfg.base_hash_rate,
        "heterogeneous_hash_rates": cfg.heterogeneous_hash_rates,
        "reserve_fraction": cfg.reserve_fraction,
        "security_floor_policy": row["security_floor_policy"],
        "range_lease_policy": row["range_lease_policy"],
        "adversarial_policy": row["adversarial_policy"],
        "incentive_policy": row["incentive_policy"],
        "fault_schedule": row["fault_schedule"],
        "primary_outcomes": PRIMARY_OUTCOMES.get(b, "NONE"),
        "secondary_outcomes": SECONDARY_OUTCOMES.get(b, "NONE"),
        "expected_NA_fields": expected_na(row),
        "notes": row["notes"],
    }


def config_payload(row: dict, cfg) -> dict:
    """The frozen, seed-independent configuration record for one scenario."""
    return {
        "scenario_id": row["scenario_id"],
        "block_id": row["block_id"],
        "confirmatory_or_exploratory": row["confirmatory_or_exploratory"],
        "paired_control_id": row["paired_control_id"],
        "hypothesis_ids": row["hypothesis_ids"],
        "num_miners": cfg.num_miners,
        "horizon_T": cfg.horizon_T,
        "run_start_time": cfg.run_start_time,
        "P_hash": cfg.P_hash, "P_listen": cfg.P_listen, "P_reserve": cfg.P_reserve,
        "P_wake": cfg.P_wake, "P_offline": cfg.P_offline,
        "wake_latency": cfg.wake_latency,
        "nonce_domain_size": cfg.nonce_domain_size,
        "difficulty": cfg.difficulty,
        "batch_size": cfg.batch_size,
        "base_hash_rate": cfg.base_hash_rate,
        "heterogeneous_hash_rates": cfg.heterogeneous_hash_rates,
        "reserve_fraction": cfg.reserve_fraction,
        "floor_unattainable_policy": cfg.floor_unattainable_policy,
        "security_floor": {
            "enabled": cfg.security_floor.enabled,
            "minimum_active_hash_rate": cfg.security_floor.minimum_active_hash_rate,
            "minimum_active_miner_count": cfg.security_floor.minimum_active_miner_count,
            "activation_trigger_mode": cfg.security_floor.activation_trigger_mode,
            "reserve_selection_policy": cfg.security_floor.reserve_selection_policy,
            "activation_wake_latency": cfg.security_floor.activation_wake_latency,
            "floor_tolerance": cfg.security_floor.floor_tolerance,
        },
        "range_lease": {
            "enabled": cfg.range_lease.enabled,
            "reassignment_enabled": cfg.range_lease.reassignment_enabled,
            "reassignment_selection_policy": cfg.range_lease.reassignment_selection_policy,
            "reassignment_wake_latency": cfg.range_lease.reassignment_wake_latency,
            "lease_duration": cfg.range_lease.lease_duration,
            "progress_timeout": cfg.range_lease.progress_timeout,
            "exhaustion_policy": cfg.range_lease.exhaustion_policy,
            "no_eligible_miner_policy": cfg.range_lease.no_eligible_miner_policy,
        },
        "adversarial": {
            "enabled": cfg.adversarial.enabled,
            "entities": [list(e[:3]) for e in cfg.adversarial.entities],
            "behaviour_flags": sorted({f for _, _, fl in cfg.adversarial.miner_behaviours
                                       for f in fl}),
            "behaviour_miner_count": len(cfg.adversarial.miner_behaviours),
            "audit_detection_probability": cfg.adversarial.audit_detection_probability,
            "solution_release_policy": cfg.adversarial.solution_release_policy,
            "delayed_wake_extra_latency": cfg.adversarial.delayed_wake_extra_latency,
            "progress_withholding_fraction": cfg.adversarial.progress_withholding_fraction,
            "maximum_actions_per_round": cfg.adversarial.maximum_actions_per_round,
            "deterministic_seed": "PER_MASTER_SEED",
        },
        "incentive": {
            "enabled": cfg.incentive.enabled, "r_work": cfg.incentive.r_work,
            "r_avail": cfg.incentive.r_avail, "r_win": cfg.incentive.r_win,
            "r_reserve": cfg.incentive.r_reserve, "r_reassign": cfg.incentive.r_reassign,
            "q_abandon": cfg.incentive.q_abandon, "q_false": cfg.incentive.q_false,
            "q_invalid": cfg.incentive.q_invalid,
            "reward_deduplication_policy": cfg.incentive.reward_deduplication_policy,
        },
        "fault_schedule_name": row["fault_schedule"],
        "injected_lease_fault_count": len(cfg.injected_lease_faults),
        "injected_lease_fault_miners": sorted({f[1] for f in cfg.injected_lease_faults}),
        "injected_lease_fault_phases": list(S.FAULT_PHASES) if cfg.injected_lease_faults else [],
        "injected_lease_fault_round_prefix": (S.FAULT_ROUND_PREFIX
                                              if cfg.injected_lease_faults else 0),
        "template_seed": "PER_MASTER_SEED",
        "notes": row["notes"],
    }


def render_csv(fields, rows) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n", extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def build_all():
    """Return (confirmatory_csv, exploratory_csv, registry_csv, {path: json_text})."""
    S.assert_reference_matches_baseline()
    conf_rows = S.confirmatory_rows()
    expl_rows = S.exploratory_rows()

    # A representative master seed is needed only to MATERIALISE a config; every field written
    # is seed-independent (the two seed fields are written as PER_MASTER_SEED placeholders).
    probe_seed = 0
    conf_csv_rows, configs = [], {}
    for row in conf_rows:
        cfg = S.build_config(row, probe_seed, S.TIER2)
        conf_csv_rows.append(matrix_row(row, cfg))
        payload = config_payload(row, cfg)
        configs[row["scenario_id"]] = json.dumps(payload, indent=1, sort_keys=True) + "\n"

    expl_csv_rows = []
    for row in expl_rows:
        r = dict(row)
        r.setdefault("security_floor_policy", "DISABLED")
        r.setdefault("range_lease_policy", "ENABLED")
        r.setdefault("adversarial_policy", "DISABLED")
        r.setdefault("incentive_policy", "ENABLED")
        r.setdefault("fault_schedule", "NONE")
        cfg = S.build_config(r, probe_seed, S.TIER2)
        mr = matrix_row(r, cfg)
        mr["primary_outcomes"] = "NONE_EXPLORATORY"
        mr["secondary_outcomes"] = "NONE_EXPLORATORY"
        expl_csv_rows.append(mr)

    # The Stage-7 run registry: one row per PHYSICAL RUN (scenario x confirmatory master seed).
    seeds = [r for r in build_rows() if r["seed_class"] == "CONFIRMATORY"]
    reg_rows = []
    for row in conf_rows:
        sid = row["scenario_id"]
        control = row["paired_control_id"]
        arm = "CONTROL" if control in ("SELF", "NONE") else "TREATMENT"
        cfg_text = configs[sid]
        cfg_sha = hashlib.sha256(cfg_text.encode("utf-8")).hexdigest()
        for s in seeds:
            master = s["master_seed_decimal"]
            reg_rows.append({
                "run_id": f"{sid}-S{s['seed_index']:02d}",
                "scenario_id": sid,
                "block_id": row["block_id"],
                # Both arms of a contrast share a pair_id under the SAME master seed.
                "pair_id": (f"{sid}-S{s['seed_index']:02d}" if arm == "CONTROL"
                            else f"{control}-S{s['seed_index']:02d}"),
                "master_seed": master,
                "seed_index": s["seed_index"],
                "condition": sid,
                "control_or_treatment": arm,
                "template_seed": child_seed(master, "template"),
                "adversarial_seed": child_seed(master, "adversarial"),
                "num_miners": S.TIER2["num_miners"],
                "horizon_T": S.TIER2["horizon_T"],
                "difficulty": row["difficulty"],
                "config_sha256": cfg_sha,
            })

    return (render_csv(MATRIX_FIELDS, conf_csv_rows),
            render_csv(MATRIX_FIELDS, expl_csv_rows),
            render_csv(REGISTRY_FIELDS, reg_rows),
            configs)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="verify committed artefacts match regeneration byte-for-byte")
    args = ap.parse_args(argv)

    conf_csv, expl_csv, reg_csv, configs = build_all()
    targets = {
        DOCS / "STAGE_06_CONFIRMATORY_MATRIX.csv": conf_csv,
        DOCS / "STAGE_06_EXPLORATORY_MATRIX.csv": expl_csv,
        CONF / "confirmatory_run_registry.csv": reg_csv,
    }
    for sid, text in configs.items():
        targets[FROZEN / f"{sid}.json"] = text

    if args.check:
        bad = []
        for path, text in sorted(targets.items(), key=lambda kv: str(kv[0])):
            if not path.exists():
                bad.append(f"missing: {path.relative_to(REPO_ROOT)}")
            elif path.read_bytes() != text.encode("utf-8"):
                bad.append(f"differs: {path.relative_to(REPO_ROOT)}")
        if bad:
            print("FAIL: generated artefacts differ from committed:", file=sys.stderr)
            for b in bad:
                print("  " + b, file=sys.stderr)
            return 1
        print(f"OK: all {len(targets)} generated artefacts are byte-identical to regeneration")
    else:
        for path, text in targets.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(text.encode("utf-8"))
        print(f"wrote {len(targets)} artefacts")

    n_conf = conf_csv.count("\n") - 1
    n_expl = expl_csv.count("\n") - 1
    n_reg = reg_csv.count("\n") - 1
    print(f"  confirmatory scenarios : {n_conf}")
    print(f"  exploratory scenarios  : {n_expl}")
    print(f"  frozen configs         : {len(configs)}")
    print(f"  expected Stage-7 runs  : {n_reg}")
    print(f"  confirmatory matrix sha256 : "
          f"{hashlib.sha256(conf_csv.encode()).hexdigest()}")
    print(f"  run registry sha256        : {hashlib.sha256(reg_csv.encode()).hexdigest()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
