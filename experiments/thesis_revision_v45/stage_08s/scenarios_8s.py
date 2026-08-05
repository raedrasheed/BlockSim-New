#!/usr/bin/env python3
"""Stage 8S — scenarios, FRESH seeds and frozen constants (single source of truth).

The FINAL controller/operating-policy refinement cycle: the useful-work-aware idle and
reserve-control policy within PoCol, evaluated once, on fresh preregistered seeds, against
the frozen historical baselines.  If its gates fail there is no further tuning and no
further controller-refinement stage.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dataclasses                                                       # noqa: E402
import scenarios_8r as S8R                                               # noqa: E402
from generate_seed_registry import build_rows                            # noqa: E402
from Models.PoCol.stage2.config import Stage2Config                      # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy              # noqa: E402

CORE = dict(S8R.CORE)                    # the frozen reduced core, unchanged
H0_HET = 4000.0
STATIC_FLOOR = 0.80 * H0_HET
N_CONFIRMATORY_SEEDS = 12
N_PILOT_SEEDS = 2

#: Full diagnostic timelines are preserved ONLY for these three runs.
TIMELINE_RUNS = (("S01_STAGE8R_STATIC_FLOOR", 0), ("S02_USEFUL_FLOOR", 0),
                 ("S03_USEFUL_FLOOR_COARSE_REASSIGNMENT", 0))

SCENARIOS = [
    {"scenario_id": "S00_NO_FLOOR", "role": "CONFIRMATORY_CONTROL",
     "security_floor": False, "controller_mode": "LEGACY_REACTIVE",
     "description": "accepted M01-like heterogeneous idle-policy control; floor disabled"},
    {"scenario_id": "S01_STAGE8R_STATIC_FLOOR", "role": "CONFIRMATORY_BASELINE",
     "security_floor": True, "controller_mode": "STAGE8R_PREDICTIVE_STATIC_FLOOR",
     "description": "the accepted Stage-8R R02 controller, unchanged"},
    {"scenario_id": "S02_USEFUL_FLOOR", "role": "CONFIRMATORY_COMPONENT",
     "security_floor": True, "controller_mode": "USEFUL_FLOOR_ONLY",
     "description": "the useful-work-aware target without coarse reassignment"},
    {"scenario_id": "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT", "role": "CONFIRMATORY_PRIMARY",
     "security_floor": True, "controller_mode": "USEFUL_FLOOR_COARSE_REASSIGNMENT",
     "description": "PRIMARY candidate for the final structural-policy verdict: useful "
                    "target + work-conserving coarse suffix repartition + reserve "
                    "admission control"},
]


def _sha_seed(tag: str, index: int) -> int:
    return int.from_bytes(hashlib.sha256(f"{tag}{index}".encode("ascii")).digest()[:8],
                          "big")


def pilot_seeds_8s() -> list:
    return [_sha_seed("PoCol-v45-stage8s-pilot-", i) for i in range(N_PILOT_SEEDS)]


def confirmatory_seeds_8s() -> list:
    return [_sha_seed("PoCol-v45-stage8s-confirmatory-", i)
            for i in range(N_CONFIRMATORY_SEEDS)]


ANALYSIS_SEED_8S = _sha_seed("PoCol-v45-stage8s-analysis-", 0)


def previous_registry_seeds() -> set:
    """EVERY seed of every previous registry: the Stage-6 registry (used by 6M/7M/8M)
    plus the fresh Stage-8R pilot/confirmatory/analysis seeds."""
    prev = {int(r["master_seed_decimal"]) for r in build_rows()}
    prev |= set(S8R.pilot_seeds_8r()) | set(S8R.confirmatory_seeds_8r())
    prev.add(S8R.ANALYSIS_SEED_8R)
    return prev


def assert_seed_disjointness() -> dict:
    pilots = pilot_seeds_8s()
    conf = confirmatory_seeds_8s()
    prev = previous_registry_seeds()
    assert len(set(pilots)) == N_PILOT_SEEDS
    assert len(set(conf)) == N_CONFIRMATORY_SEEDS
    assert not (set(pilots) & set(conf))
    assert not (set(pilots) | set(conf) | {ANALYSIS_SEED_8S}) & prev, \
        "a fresh Stage-8S seed collides with a previous registry seed"
    return {"pilot": pilots, "confirmatory": conf,
            "previous_registry_size": len(prev), "all_disjoint": True}


def build_config_8s(row: dict, master_seed: int) -> Stage2Config:
    """One frozen Stage-8S config: the Stage-8R floor core with ONLY the controller mode
    as treatment (S00 additionally disables the floor).  Every non-treatment field
    matches; leases/adversarial/incentive stay disabled; difficulty fixed."""
    base_row = S8R.SCENARIOS[1] if row["security_floor"] else S8R.SCENARIOS[0]
    cfg = S8R.build_config_8r(base_row, master_seed)
    return dataclasses.replace(cfg, controller=ControllerPolicy(
        mode=row["controller_mode"],
        reactive_trigger_ratio=S8R.REACTIVE_TRIGGER_RATIO,
        central_target_ratio=S8R.CENTRAL_TARGET_RATIO,
        recovery_ratio=S8R.RECOVERY_RATIO,
        lookahead_seconds=None, cooldown_seconds=None,
        reassignment_chunk_nonces=S8R.REASSIGNMENT_CHUNK_NONCES))


if __name__ == "__main__":
    info = assert_seed_disjointness()
    print("fresh pilot seeds       :", info["pilot"])
    print("fresh confirmatory[0/11]:", info["confirmatory"][0], info["confirmatory"][-1])
    print("analysis seed           :", ANALYSIS_SEED_8S)
    print("previous registry seeds :", info["previous_registry_size"], "(all disjoint)")
    for row in SCENARIOS:
        cfg = build_config_8s(row, info["pilot"][0])
        print(f"{row['scenario_id']:40s} mode={cfg.controller.mode:34s} "
              f"floor={'on' if cfg.security_floor.enabled else 'off'}")
