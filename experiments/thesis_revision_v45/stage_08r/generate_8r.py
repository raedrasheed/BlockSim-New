#!/usr/bin/env python3
"""Stage 8R — deterministic generator for the seed registry and experiment matrix.
``--check`` verifies byte-identical regeneration."""
from __future__ import annotations

import argparse
import csv
import io
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenarios_8r as S8                                                  # noqa: E402

REPO_ROOT = HERE.parents[2]
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08r"

HYPOTHESES = {
    "R00_NO_FLOOR": "H-R4(denominator);H-R5(reference-free control)",
    "R01_LEGACY_FLOOR": "H-R1(control);H-R2(control);H-R3(control)",
    "R02_REVISED_CONTROLLER": "H-R1;H-R2;H-R3;H-R4;H-R5",
    "R03_REVISED_PLUS_REASSIGNMENT": "NONE (EXPLORATORY; never determines the verdict)",
}


def csv_text(fields, rows) -> str:
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue()


def seed_rows() -> list:
    out = []
    for i, s in enumerate(S8.pilot_seeds_8r()):
        out.append({"seed_class": "PILOT_8R", "seed_index": i, "master_seed_decimal": s,
                    "derivation": f'SHA256("PoCol-v45-stage8r-pilot-{i}") first u64 BE',
                    "used_by": "structural pilot only (all four scenarios)"})
    for i, s in enumerate(S8.confirmatory_seeds_8r()):
        out.append({"seed_class": "CONFIRMATORY_8R", "seed_index": i,
                    "master_seed_decimal": s,
                    "derivation": f'SHA256("PoCol-v45-stage8r-confirmatory-{i}") first u64 BE',
                    "used_by": "R00;R01;R02;R03 (same 12 seeds in every scenario)"})
    out.append({"seed_class": "ANALYSIS_8R", "seed_index": 0,
                "master_seed_decimal": S8.ANALYSIS_SEED_8R,
                "derivation": 'SHA256("PoCol-v45-stage8r-analysis-0") first u64 BE',
                "used_by": "bootstrap RNG root (analysis only; never a simulation seed)"})
    return out


def matrix_rows() -> list:
    out = []
    for row in S8.SCENARIOS:
        cfg = S8.build_config_8r(row, 0)
        out.append({
            "scenario_id": row["scenario_id"], "role": row["role"],
            **{k: S8.CORE[k] for k in ("num_miners", "horizon_T", "nonce_domain_size",
                                       "difficulty", "batch_size", "base_hash_rate",
                                       "reserve_fraction")},
            "heterogeneous_hash_rates": True,
            "security_floor_enabled": row["security_floor"],
            "minimum_active_hash_rate": (cfg.security_floor.minimum_active_hash_rate
                                         if row["security_floor"] else ""),
            "floor_unattainable_policy": ("CONTINUE_DEGRADED" if row["security_floor"]
                                          else ""),
            "controller_mode": row["controller_mode"],
            "reactive_trigger_ratio": S8.REACTIVE_TRIGGER_RATIO,
            "central_target_ratio": S8.CENTRAL_TARGET_RATIO,
            "recovery_ratio": S8.RECOVERY_RATIO,
            "lookahead_seconds": "activation_wake_latency (1.0)",
            "cooldown_seconds": "activation_wake_latency (1.0)",
            "reassignment_chunk_nonces": (S8.REASSIGNMENT_CHUNK_NONCES
                                          if row["range_leases"] else ""),
            "range_leases": "ENABLED" if row["range_leases"] else "DISABLED",
            "adversarial_model": "DISABLED", "incentive_model": "DISABLED",
            "dynamic_difficulty": "FORBIDDEN",
            "seeds": "confirmatory_8r[0..11]",
            "hypotheses": HYPOTHESES[row["scenario_id"]],
        })
    return out


TARGETS = {
    "STAGE_08R_SEED_REGISTRY.csv": lambda: csv_text(
        ["seed_class", "seed_index", "master_seed_decimal", "derivation", "used_by"],
        seed_rows()),
    "STAGE_08R_EXPERIMENT_MATRIX.csv": lambda: csv_text(
        ["scenario_id", "role", "num_miners", "horizon_T", "nonce_domain_size",
         "difficulty", "batch_size", "base_hash_rate", "reserve_fraction",
         "heterogeneous_hash_rates", "security_floor_enabled", "minimum_active_hash_rate",
         "floor_unattainable_policy", "controller_mode", "reactive_trigger_ratio",
         "central_target_ratio", "recovery_ratio", "lookahead_seconds", "cooldown_seconds",
         "reassignment_chunk_nonces", "range_leases", "adversarial_model",
         "incentive_model", "dynamic_difficulty", "seeds", "hypotheses"],
        matrix_rows()),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    S8.assert_seed_disjointness()
    DOCS.mkdir(parents=True, exist_ok=True)
    bad = []
    for name, fn in TARGETS.items():
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
        print(f"OK: {len(TARGETS)} artifact(s) byte-identical to regeneration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
