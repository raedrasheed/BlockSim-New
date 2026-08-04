#!/usr/bin/env python3
"""Stage 6M — deterministic artifact generator (matrix, seed registry, outcome dictionary,
checksum manifest).  ``--check`` verifies byte-identical regeneration."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
sys.path.insert(0, str(HERE))
import scenarios_6m as M                                                       # noqa: E402

DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_06m"

MATRIX_FIELDS = ["scenario_id", "role", "num_miners", "horizon_T", "nonce_domain_size",
                 "difficulty", "batch_size", "base_hash_rate", "reserve_fraction",
                 "heterogeneous_hash_rates", "security_floor_enabled",
                 "minimum_active_hash_rate", "floor_unattainable_policy",
                 "range_leases", "reassignment", "adversarial_model", "incentive_model",
                 "dynamic_difficulty", "seeds", "hypotheses"]

OUTCOMES = [
    # name, definition, source, unit, role
    ("E_idle_kwh", "sum over states of P_state * t_state from the run's residency ledger",
     "energy_pair_kwh", "kWh", "PRIMARY_INPUT"),
    ("E_power_null_kwh", "P_hash*(t_hash+t_listen+t_reserve+t_wake) + P_offline*t_offline "
     "from the SAME residency ledger (within-run counterfactual; no separate simulation)",
     "energy_pair_kwh", "kWh", "PRIMARY_INPUT"),
    ("absolute_reduction_kwh", "E_power_null_kwh - E_idle_kwh", "derived", "kWh", "PRIMARY"),
    ("relative_reduction", "(E_power_null_kwh - E_idle_kwh) / E_power_null_kwh",
     "derived", "fraction", "PRIMARY"),
    ("rounds_accepted", "accepted block count", "results_schema", "count", "SERVICE"),
    ("median_round_duration", "median of per-round durations from round_terminal_times",
     "round_durations", "s", "SERVICE"),
    ("rounds_executed", "closed round count", "run.round_terminal_times", "count", "SERVICE"),
    ("zero_block_indicator", "1 if rounds_accepted == 0 (retained, never excluded)",
     "derived", "indicator", "SERVICE"),
    ("total_duration_below_floor", "accepted Stage-3 below-floor duration",
     "results_schema", "s", "OPERATIONAL"),
    ("floor_unattainable_count", "accepted Stage-3 unattainable count (reported honestly)",
     "results_schema", "count", "OPERATIONAL"),
    ("security_floor_observation_count", "floor observations", "results_schema", "count",
     "OPERATIONAL"),
    ("reserve_activations_seated", "reserve activations seated", "results_schema", "count",
     "OPERATIONAL"),
    ("reserve_activations_completed", "reserve activations completed", "results_schema",
     "count", "OPERATIONAL"),
    ("nonterminal_activation_request_count", "activation requests left non-terminal",
     "nonterminal_activation_request_count", "count", "INTEGRITY"),
    ("maximum_energy_identity_residual_j", "IP-H2 identity residual (gate <= 1e-8 J)",
     "residency_and_energy_identity", "J", "INTEGRITY"),
    ("maximum_residency_partition_residual_s", "IP-H2 partition residual (gate <= 1e-9 s)",
     "residency_and_energy_identity", "s", "INTEGRITY"),
    ("duplicate_nonce_count", "gate == 0", "results_schema", "count", "INTEGRITY"),
    ("post_round_evaluation_record_count", "gate == 0", "post_round_audit", "count",
     "INTEGRITY"),
    ("post_round_evaluation_nonce_count", "gate == 0", "post_round_audit", "count",
     "INTEGRITY"),
    ("evaluation_missing_terminal_time_count", "gate == 0", "post_round_audit", "count",
     "INTEGRITY"),
    ("physical_frontier_rewind_count", "gate == 0", "results_schema", "count", "INTEGRITY"),
    ("work_reward_union_residual", "gate == 0", "results_schema", "count", "INTEGRITY"),
    ("nonterminal_lease_count", "gate == 0 (leases disabled -> vacuously 0, still checked)",
     "results_schema", "count", "INTEGRITY"),
    ("nonterminal_reassignment_request_count", "gate == 0 (reassignment disabled)",
     "results_schema", "count", "INTEGRITY"),
    ("adversarial_action_total", "sum of all adversarial action counters; the adversarial "
     "model is DISABLED so the gate is == 0 (maps the directive's "
     "nonterminal_adversarial_action_count onto the accepted schema, which has no field of "
     "that literal name)", "results_schema", "count", "INTEGRITY"),
    ("power_null_equals_A1_residual_kwh", "|E_power_null_kwh - A1_core| given zero "
     "offline residency (gate <= 1e-9 kWh)", "derived", "kWh", "INTEGRITY"),
]


def matrix_rows() -> list:
    out = []
    for row in M.CONFIRMATORY + M.EXPLORATORY:
        base = M.SCALE if row["role"] == "EXPLORATORY_SCALE_CHECK" else M.CORE
        cfg = M.build_config_6m(row, 0)
        out.append({
            "scenario_id": row["scenario_id"], "role": row["role"],
            **{k: base[k] for k in ("num_miners", "horizon_T", "nonce_domain_size",
                                    "difficulty", "batch_size", "base_hash_rate",
                                    "reserve_fraction")},
            "heterogeneous_hash_rates": row["heterogeneous_hash_rates"],
            "security_floor_enabled": row["security_floor"],
            "minimum_active_hash_rate": (cfg.security_floor.minimum_active_hash_rate
                                         if row["security_floor"] else ""),
            "floor_unattainable_policy": ("CONTINUE_DEGRADED" if row["security_floor"] else ""),
            "range_leases": "DISABLED", "reassignment": "DISABLED",
            "adversarial_model": "DISABLED", "incentive_model": "DISABLED",
            "dynamic_difficulty": "FORBIDDEN",
            "seeds": ("confirmatory[0..9]" if row["role"] == "CONFIRMATORY"
                      else f"pilot[{M.SCALE_CHECK_PILOT_SEED_INDEX[row['scenario_id']]}]"),
            "hypotheses": row["hypotheses"],
        })
    return out


def csv_text(fields, rows) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def seed_rows() -> list:
    out = []
    for i, s in enumerate(M.confirmatory_seeds()):
        out.append({"seed_class": "CONFIRMATORY", "seed_index": i, "master_seed_decimal": s,
                    "provenance": "Stage-6 registry PoCol-v45-stage7-confirmatory-, unchanged",
                    "used_by": "M01;M02;M03"})
    p = M.pilot_seeds()
    for i in M.STRUCTURAL_PILOT_SEED_INDEXES:
        out.append({"seed_class": "PILOT", "seed_index": i, "master_seed_decimal": p[i],
                    "provenance": "Stage-6 registry PoCol-v45-stage6-pilot-, unchanged",
                    "used_by": "structural pilot (M01;M02;M03)"})
    for sid, i in sorted(M.SCALE_CHECK_PILOT_SEED_INDEX.items()):
        out.append({"seed_class": "PILOT", "seed_index": i, "master_seed_decimal": p[i],
                    "provenance": "Stage-6 registry PoCol-v45-stage6-pilot-, unchanged",
                    "used_by": sid})
    return out


TARGETS = {
    "STAGE_06M_MINIMAL_MATRIX.csv": lambda: csv_text(MATRIX_FIELDS, matrix_rows()),
    "STAGE_06M_SEED_REGISTRY.csv": lambda: csv_text(
        ["seed_class", "seed_index", "master_seed_decimal", "provenance", "used_by"],
        seed_rows()),
    "STAGE_06M_OUTCOME_DICTIONARY.csv": lambda: csv_text(
        ["outcome", "definition", "source", "unit", "role"],
        [dict(zip(("outcome", "definition", "source", "unit", "role"), o))
         for o in OUTCOMES]),
}

MANIFEST_INCLUDE = ["docs/thesis_revision_v45/stage_06m", 
                    "experiments/thesis_revision_v45/stage_06m",
                    "tests/thesis_revision_v45/stage_06m"]
MANIFEST_NAME = "STAGE_06M_CHECKSUM_MANIFEST.sha256"


def manifest_text() -> str:
    lines = []
    for root in MANIFEST_INCLUDE:
        for p in sorted((REPO_ROOT / root).rglob("*")):
            if not p.is_file() or "__pycache__" in p.parts or p.name == MANIFEST_NAME:
                continue
            digest = hashlib.sha256(p.read_bytes()).hexdigest()
            lines.append(f"{digest}  {p.relative_to(REPO_ROOT)}")
    return "\n".join(sorted(lines)) + "\n"


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--manifest", action="store_true",
                    help="write/check the checksum manifest (run LAST)")
    args = ap.parse_args(argv)
    M.assert_core_matches_directive()
    DOCS.mkdir(parents=True, exist_ok=True)
    targets = ({MANIFEST_NAME: manifest_text} if args.manifest else TARGETS)
    bad = []
    for name, fn in targets.items():
        text = fn()
        dest = DOCS / name
        if args.check:
            if not dest.exists() or dest.read_text() != text:
                bad.append(name)
        else:
            dest.write_text(text)
            print(f"wrote {dest.relative_to(REPO_ROOT)}")
    if args.check:
        if bad:
            print(f"FAIL: differs from regeneration: {bad}", file=sys.stderr)
            return 1
        print(f"OK: {len(targets)} artifact(s) byte-identical to regeneration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
