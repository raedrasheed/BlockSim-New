#!/usr/bin/env python3
"""Stage 8S — deterministic generator for the seed registry and experiment matrix.
``--check`` verifies byte-identical regeneration."""
from __future__ import annotations

import argparse
import csv
import io
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import scenarios_8s as S8S                                                 # noqa: E402

REPO_ROOT = HERE.parents[2]
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08s"

HYPOTHESES = {
    "S00_NO_FLOOR": "H-S2(denominator);H-S4(reference-free control)",
    "S01_STAGE8R_STATIC_FLOOR": "H-S1(control);H-S3(control)",
    "S02_USEFUL_FLOOR": "component comparison (descriptive)",
    "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT": "H-S1;H-S2;H-S3;H-S4 (PRIMARY)",
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
    for i, s in enumerate(S8S.pilot_seeds_8s()):
        out.append({"seed_class": "PILOT_8S", "seed_index": i, "master_seed_decimal": s,
                    "derivation": f'SHA256("PoCol-v45-stage8s-pilot-{i}") first u64 BE',
                    "used_by": "structural pilot only (all four scenarios)"})
    for i, s in enumerate(S8S.confirmatory_seeds_8s()):
        out.append({"seed_class": "CONFIRMATORY_8S", "seed_index": i,
                    "master_seed_decimal": s,
                    "derivation":
                        f'SHA256("PoCol-v45-stage8s-confirmatory-{i}") first u64 BE',
                    "used_by": "S00;S01;S02;S03 (same 12 seeds in every scenario)"})
    out.append({"seed_class": "ANALYSIS_8S", "seed_index": 0,
                "master_seed_decimal": S8S.ANALYSIS_SEED_8S,
                "derivation": 'SHA256("PoCol-v45-stage8s-analysis-0") first u64 BE',
                "used_by": "bootstrap RNG root (analysis only; never a simulation seed)"})
    return out


def matrix_rows() -> list:
    out = []
    for row in S8S.SCENARIOS:
        cfg = S8S.build_config_8s(row, 0)
        out.append({
            "scenario_id": row["scenario_id"], "role": row["role"],
            **{k: S8S.CORE[k] for k in ("num_miners", "horizon_T", "nonce_domain_size",
                                        "difficulty", "batch_size", "base_hash_rate",
                                        "reserve_fraction")},
            "heterogeneous_hash_rates": True,
            "security_floor_enabled": row["security_floor"],
            "static_floor_minimum": (cfg.security_floor.minimum_active_hash_rate
                                     if row["security_floor"] else ""),
            "useful_floor_formula": ("min(0.80*H0, H_useful_available(t))"
                                     if row["security_floor"] else ""),
            "controller_mode": row["controller_mode"],
            "hysteresis_ratios": "0.78/0.80/0.82",
            "lookahead_cooldown": "activation_wake_latency (1.0 s)",
            "coarse_partition_rule": ("min(1+receivers, ceil(remaining/batch)) with "
                                      "no non-final chunk below one batch"
                                      if row["controller_mode"]
                                      == "USEFUL_FLOOR_COARSE_REASSIGNMENT" else ""),
            "range_leases": "DISABLED", "adversarial_model": "DISABLED",
            "incentive_model": "DISABLED", "dynamic_difficulty": "FORBIDDEN",
            "seeds": "confirmatory_8s[0..11]",
            "hypotheses": HYPOTHESES[row["scenario_id"]],
        })
    return out


TARGETS = {
    "STAGE_08S_SEED_REGISTRY.csv": lambda: csv_text(
        ["seed_class", "seed_index", "master_seed_decimal", "derivation", "used_by"],
        seed_rows()),
    "STAGE_08S_EXPERIMENT_MATRIX.csv": lambda: csv_text(
        ["scenario_id", "role", "num_miners", "horizon_T", "nonce_domain_size",
         "difficulty", "batch_size", "base_hash_rate", "reserve_fraction",
         "heterogeneous_hash_rates", "security_floor_enabled", "static_floor_minimum",
         "useful_floor_formula", "controller_mode", "hysteresis_ratios",
         "lookahead_cooldown", "coarse_partition_rule", "range_leases",
         "adversarial_model", "incentive_model", "dynamic_difficulty", "seeds",
         "hypotheses"],
        matrix_rows()),
}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args(argv)
    S8S.assert_seed_disjointness()
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
            print(f"FAIL: {bad}", file=sys.stderr)
            return 1
        print(f"OK: {len(TARGETS)} artifact(s) byte-identical to regeneration")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
