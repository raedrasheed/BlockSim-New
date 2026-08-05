#!/usr/bin/env python3
"""Stage 8U — scenarios, FRESH seeds and frozen constants (single source of truth).

The LAST, narrowly bounded PoCol operating-policy improvement (the single-handoff
useful-work policy within PoCol) and the matched same-template PoW comparison, evaluated
once on fresh preregistered seeds.  If the joint acceptance rule fails there is no further
tuning, no Stage 8V and no redefinition of any scenario, seed, target or margin.

Naming discipline: the two W-scenarios are the "matched same-template PoW control"
(population-matched and active-capacity-matched); they are never described as any
real-world network.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
for p in (str(REPO_ROOT),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r"),
          str(REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08s")):
    if p not in sys.path:
        sys.path.insert(0, p)

import dataclasses                                                       # noqa: E402
import scenarios_8r as S8R                                               # noqa: E402
import scenarios_8s as S8S                                               # noqa: E402
from Models.PoCol.stage2.config import Stage2Config                      # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy              # noqa: E402
from Models.PoCol.stage2.matched_pow import MatchedPoWConfig             # noqa: E402

CORE = dict(S8R.CORE)                    # the frozen reduced core, unchanged
H0_HET = 4000.0
STATIC_FLOOR = 0.80 * H0_HET
N_CONFIRMATORY_SEEDS = 12
N_PILOT_SEEDS = 2

#: Full diagnostic timelines are preserved ONLY for these runs (engine scenarios, seed 0).
TIMELINE_RUNS = (("P01_POCOL_STAGE8S_COARSE", 0), ("P02_POCOL_SINGLE_HANDOFF", 0))

#: Exactly five scenarios.  The two PoW controls are never merged: they answer different
#: questions (same population vs artificially matched active capacity).
SCENARIOS = [
    {"scenario_id": "W00_POW_POPULATION_MATCHED", "role": "CONFIRMATORY_POW_CONTROL",
     "engine": "MATCHED_POW", "pow_kind": "POW_POPULATION_MATCHED",
     "description": "matched same-template PoW control; all 20 nodes mine continuously"},
    {"scenario_id": "W01_POW_ACTIVE_CAPACITY_MATCHED",
     "role": "CONFIRMATORY_POW_CONTROL",
     "engine": "MATCHED_POW", "pow_kind": "POW_ACTIVE_CAPACITY_MATCHED",
     "description": "matched same-template PoW control; exactly the 16 initial active "
                    "miners mine, 4 non-mining standby nodes at P_reserve (explicitly "
                    "labelled artificial capacity-matched control)"},
    {"scenario_id": "P00_POCOL_NO_FLOOR", "role": "CONFIRMATORY_CONTROL",
     "engine": "POCOL", "security_floor": False, "controller_mode": "LEGACY_REACTIVE",
     "description": "accepted heterogeneous idle-policy PoCol control; floor disabled"},
    {"scenario_id": "P01_POCOL_STAGE8S_COARSE", "role": "CONFIRMATORY_BASELINE",
     "engine": "POCOL", "security_floor": True,
     "controller_mode": "USEFUL_FLOOR_COARSE_REASSIGNMENT",
     "description": "the accepted Stage-8S S03 coarse-reassignment controller, unchanged"},
    {"scenario_id": "P02_POCOL_SINGLE_HANDOFF", "role": "CONFIRMATORY_PRIMARY",
     "engine": "POCOL", "security_floor": True,
     "controller_mode": "USEFUL_FLOOR_SINGLE_HANDOFF",
     "description": "PRIMARY: the single-handoff useful-work policy within PoCol "
                    "(U1..U5: one handoff epoch per round, proportional two-chunk "
                    "split, single admission-checked reserve-wake fallback)"},
]


def _sha_seed(tag: str, index: int) -> int:
    return int.from_bytes(hashlib.sha256(f"{tag}{index}".encode("ascii")).digest()[:8],
                          "big")


def pilot_seeds_8u() -> list:
    return [_sha_seed("PoCol-v45-stage8u-pilot-", i) for i in range(N_PILOT_SEEDS)]


def confirmatory_seeds_8u() -> list:
    return [_sha_seed("PoCol-v45-stage8u-confirmatory-", i)
            for i in range(N_CONFIRMATORY_SEEDS)]


ANALYSIS_SEED_8U = _sha_seed("PoCol-v45-stage8u-analysis-", 0)


def previous_registry_seeds() -> set:
    """EVERY seed of every previous registry: the Stage-6 registry (6M/7M/8M), the fresh
    Stage-8R seeds and the fresh Stage-8S seeds (pilot + confirmatory + analysis)."""
    prev = set(S8S.previous_registry_seeds())               # Stage-6 registry + Stage-8R
    prev |= set(S8S.pilot_seeds_8s()) | set(S8S.confirmatory_seeds_8s())
    prev.add(S8S.ANALYSIS_SEED_8S)
    return prev


def assert_seed_disjointness() -> dict:
    pilots = pilot_seeds_8u()
    conf = confirmatory_seeds_8u()
    prev = previous_registry_seeds()
    assert len(set(pilots)) == N_PILOT_SEEDS
    assert len(set(conf)) == N_CONFIRMATORY_SEEDS
    assert not (set(pilots) & set(conf))
    assert not (set(pilots) | set(conf) | {ANALYSIS_SEED_8U}) & prev, \
        "a fresh Stage-8U seed collides with a previous registry seed"
    return {"pilot": pilots, "confirmatory": conf,
            "previous_registry_size": len(prev), "all_disjoint": True}


def build_config_8u(row: dict, master_seed: int) -> Stage2Config:
    """One frozen Stage-8U ENGINE config (P-scenarios): the identical frozen core with
    ONLY the controller mode as treatment.  P00 reproduces the Stage-8S S00 control
    config; P01 reproduces the Stage-8S S03 config exactly."""
    assert row["engine"] == "POCOL"
    base_row = S8R.SCENARIOS[1] if row["security_floor"] else S8R.SCENARIOS[0]
    cfg = S8R.build_config_8r(base_row, master_seed)
    return dataclasses.replace(cfg, controller=ControllerPolicy(
        mode=row["controller_mode"],
        reactive_trigger_ratio=S8R.REACTIVE_TRIGGER_RATIO,
        central_target_ratio=S8R.CENTRAL_TARGET_RATIO,
        recovery_ratio=S8R.RECOVERY_RATIO,
        lookahead_seconds=None, cooldown_seconds=None,
        reassignment_chunk_nonces=S8R.REASSIGNMENT_CHUNK_NONCES))


def build_pow_config_8u(row: dict, master_seed: int) -> MatchedPoWConfig:
    """One frozen matched-PoW config (W-scenarios), derived from the SAME frozen engine
    core for the SAME master seed — identical template stream (template_seed =
    child_seed(master_seed, "template")), difficulty, target, domain, horizon, batch,
    actual rates and power values as the paired P-scenario runs."""
    assert row["engine"] == "MATCHED_POW"
    base = S8R.build_config_8r(S8R.SCENARIOS[1], master_seed)
    ids = tuple(f"M{i:03d}" for i in range(base.num_miners))
    rates = tuple(base.hash_rate_for(i) for i in range(base.num_miners))
    common = dict(difficulty=base.difficulty, nonce_domain_size=base.nonce_domain_size,
                  horizon_seconds=base.horizon_T, batch_size=base.batch_size,
                  template_seed=base.template_seed, master_seed=master_seed,
                  P_hash=base.P_hash, P_reserve=base.P_reserve)
    if row["pow_kind"] == "POW_POPULATION_MATCHED":
        return MatchedPoWConfig(scenario_id=row["scenario_id"],
                                scenario_kind=row["pow_kind"],
                                miner_ids=ids, hash_rates=rates, **common)
    n_res = int(base.reserve_fraction * base.num_miners)
    return MatchedPoWConfig(scenario_id=row["scenario_id"],
                            scenario_kind=row["pow_kind"],
                            miner_ids=ids[:-n_res], hash_rates=rates[:-n_res],
                            standby_ids=ids[-n_res:], **common)


if __name__ == "__main__":
    info = assert_seed_disjointness()
    print("fresh pilot seeds       :", info["pilot"])
    print("fresh confirmatory[0/11]:", info["confirmatory"][0], info["confirmatory"][-1])
    print("analysis seed           :", ANALYSIS_SEED_8U)
    print("previous registry seeds :", info["previous_registry_size"], "(all disjoint)")
    for row in SCENARIOS:
        if row["engine"] == "POCOL":
            cfg = build_config_8u(row, info["pilot"][0])
            print(f"{row['scenario_id']:36s} POCOL mode={cfg.controller.mode:30s} "
                  f"floor={'on' if cfg.security_floor.enabled else 'off'}")
        else:
            pc = build_pow_config_8u(row, info["pilot"][0])
            print(f"{row['scenario_id']:36s} MATCHED_POW kind={pc.scenario_kind:28s} "
                  f"miners={len(pc.miner_ids)} standby={len(pc.standby_ids)}")
