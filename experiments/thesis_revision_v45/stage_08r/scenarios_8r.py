#!/usr/bin/env python3
"""Stage 8R — scenarios, FRESH seeds and frozen constants (single source of truth).

The algorithm remains PoCol; this experiment tests the REVISED idle and reserve-control
policy within PoCol against the accepted legacy controller and the no-floor control, at the
same reduced core scale as Stage 6M, on FRESH seeds that are provably disjoint from every
previous pilot and confirmatory registry.

Frozen BEFORE the new pilot (never tuned afterwards): 0.78 / 0.80 / 0.82 hysteresis,
lookahead = cooldown = activation wake latency (1.0 s), 25-nonce reassignment chunk.
"""
from __future__ import annotations

import hashlib
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE6 = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"
STAGE6M = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06m"
for p in (str(REPO_ROOT), str(STAGE6), str(STAGE6M)):
    if p not in sys.path:
        sys.path.insert(0, p)

from Models.PoCol.stage2.config import Stage2Config                       # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy               # noqa: E402
from Models.PoCol.stage2.leases import RangeLeasePolicy                   # noqa: E402
from generate_seed_registry import build_rows, child_seed                 # noqa: E402
from scenarios import floor_policy, initial_active_primary_hash_rate      # noqa: E402

# ------------------------------------------------------------------ frozen core (= Stage 6M)
CORE = dict(num_miners=20, horizon_T=300.0, nonce_domain_size=1600, difficulty=1000,
            batch_size=25, base_hash_rate=100.0, reserve_fraction=0.20,
            P_hash=21.5, P_listen=2.15, P_reserve=2.15, P_wake=10.75, P_offline=0.0)
H0_HET = 4000.0
FLOOR_FRACTION = 0.80
FLOOR_MINIMUM = FLOOR_FRACTION * H0_HET          # 3200.0

# frozen controller constants (declared before the pilot; not tunable afterwards)
REACTIVE_TRIGGER_RATIO = 0.78
CENTRAL_TARGET_RATIO = 0.80
RECOVERY_RATIO = 0.82
REASSIGNMENT_CHUNK_NONCES = 25

N_CONFIRMATORY_SEEDS = 12
N_PILOT_SEEDS = 2

#: Full diagnostic timelines are preserved ONLY for these three runs.
TIMELINE_RUNS = (("R01_LEGACY_FLOOR", 0), ("R02_REVISED_CONTROLLER", 0),
                 ("R03_REVISED_PLUS_REASSIGNMENT", 0))

SCENARIOS = [
    {"scenario_id": "R00_NO_FLOOR", "role": "CONFIRMATORY_CONTROL",
     "security_floor": False, "controller_mode": "LEGACY_REACTIVE", "range_leases": False,
     "description": "accepted M01-like heterogeneous idle-policy control; floor disabled"},
    {"scenario_id": "R01_LEGACY_FLOOR", "role": "CONFIRMATORY_BASELINE",
     "security_floor": True, "controller_mode": "LEGACY_REACTIVE", "range_leases": False,
     "description": "accepted M03 legacy controller; 0.80 x H0 floor, zero tolerance"},
    {"scenario_id": "R02_REVISED_CONTROLLER", "role": "CONFIRMATORY_TREATMENT",
     "security_floor": True, "controller_mode": "HYSTERESIS_PREDICTIVE",
     "range_leases": False,
     "description": "revised policy: hysteresis 0.78/0.80/0.82, predictive wake-ahead, "
                    "one live batch per episode, cooldown = lookahead = wake latency"},
    {"scenario_id": "R03_REVISED_PLUS_REASSIGNMENT", "role": "EXPLORATORY",
     "security_floor": True, "controller_mode": "HYSTERESIS_PREDICTIVE_REASSIGNMENT",
     "range_leases": True,
     "description": "EXPLORATORY: R02 plus bounded 25-nonce suffix reassignment; never "
                    "determines the main policy verdict"},
]


# ------------------------------------------------------------------ fresh seeds
def _sha_seed(tag: str, index: int) -> int:
    """First unsigned 64-bit big-endian value of SHA256(tag + str(index))."""
    digest = hashlib.sha256(f"{tag}{index}".encode("ascii")).digest()
    return int.from_bytes(digest[:8], "big")


def pilot_seeds_8r() -> list:
    return [_sha_seed("PoCol-v45-stage8r-pilot-", i) for i in range(N_PILOT_SEEDS)]


def confirmatory_seeds_8r() -> list:
    return [_sha_seed("PoCol-v45-stage8r-confirmatory-", i)
            for i in range(N_CONFIRMATORY_SEEDS)]


ANALYSIS_SEED_8R = _sha_seed("PoCol-v45-stage8r-analysis-", 0)


def previous_registry_seeds() -> set:
    """EVERY seed of every previous pilot and confirmatory registry (Stage 6 registry,
    reused unchanged by Stages 6M/7M/8M)."""
    return {int(r["master_seed_decimal"]) for r in build_rows()}


def assert_seed_disjointness() -> dict:
    pilots = pilot_seeds_8r()
    conf = confirmatory_seeds_8r()
    prev = previous_registry_seeds()
    assert len(set(pilots)) == N_PILOT_SEEDS
    assert len(set(conf)) == N_CONFIRMATORY_SEEDS
    assert not (set(pilots) & set(conf)), "pilot seeds intersect confirmatory seeds"
    assert not (set(pilots) | set(conf)) & prev, \
        "a fresh Stage-8R seed collides with a previous registry seed"
    return {"pilot": pilots, "confirmatory": conf,
            "previous_registry_size": len(prev), "all_disjoint": True}


# ------------------------------------------------------------------ config builder
def build_config_8r(row: dict, master_seed: int) -> Stage2Config:
    """One frozen Stage-8R config.  Adversarial/incentive stay disabled (defaults);
    dynamic difficulty does not exist.  Every non-treatment field matches exactly."""
    kwargs = dict(CORE)
    kwargs["heterogeneous_hash_rates"] = True
    kwargs["template_seed"] = child_seed(master_seed, "template")
    if row["security_floor"]:
        kwargs["security_floor"] = floor_policy(
            FLOOR_FRACTION * initial_active_primary_hash_rate(
                CORE["num_miners"], CORE["reserve_fraction"], CORE["base_hash_rate"], True),
            None)
        kwargs["floor_unattainable_policy"] = "CONTINUE_DEGRADED"
    kwargs["controller"] = ControllerPolicy(
        mode=row["controller_mode"],
        reactive_trigger_ratio=REACTIVE_TRIGGER_RATIO,
        central_target_ratio=CENTRAL_TARGET_RATIO,
        recovery_ratio=RECOVERY_RATIO,
        lookahead_seconds=None,            # None == activation wake latency (frozen rule)
        cooldown_seconds=None,
        reassignment_chunk_nonces=REASSIGNMENT_CHUNK_NONCES)
    if row["range_leases"]:
        kwargs["range_lease"] = RangeLeasePolicy(enabled=True)
    return Stage2Config(**kwargs)


# ------------------------------------------------------------------ role-state decomposition
PRIMARY_IDS = tuple(f"M{i:03d}" for i in range(16))
RESERVE_IDS = tuple(f"M{i:03d}" for i in range(16, 20))
JOULES_PER_KWH = 3_600_000.0

#: The declared role-state components.  Reserve/wake saving is NEVER combined with the
#: range-idle saving in one unlabeled component.
COMPONENTS = ("PRIMARY_ACTIVE_HASHING", "PRIMARY_LOW_POWER_LISTEN", "RESERVE_STANDBY",
              "RESERVE_WAKING", "ACTIVATED_RESERVE_HASHING", "OFFLINE",
              "COORDINATION_AND_VERIFICATION")


def _component(role: str, state: str) -> str:
    if state in ("OFFLINE", "DISQUALIFIED"):
        return "OFFLINE"
    if role == "primary":
        if state in ("ACTIVE_HASHING", "EXHAUSTED_PENDING"):
            return "PRIMARY_ACTIVE_HASHING"
        if state == "LOW_POWER_LISTEN":
            return "PRIMARY_LOW_POWER_LISTEN"
        return "COORDINATION_AND_VERIFICATION"        # REGISTERED + primary WAKING
    if state in ("ACTIVE_HASHING", "EXHAUSTED_PENDING"):
        return "ACTIVATED_RESERVE_HASHING"
    if state == "WAKING":
        return "RESERVE_WAKING"
    return "RESERVE_STANDBY"                          # RESERVE + reserve listen/registered


def energy_time_decomposition(run, cfg: Stage2Config) -> dict:
    """Per-run energy and residency by role-state component, plus the component-wise
    within-run power-null differences (exact identity: their sum equals
    E_power_null − E_idle because (P_hash − P_state) is priced per state)."""
    res_s = {c: 0.0 for c in COMPONENTS}
    e_idle_j = {c: 0.0 for c in COMPONENTS}
    diff_j = {c: 0.0 for c in COMPONENTS}
    for mid in run.miners:
        role = "primary" if mid in PRIMARY_IDS else "reserve"
        for state, dur in run.miners[mid].duration.items():
            c = _component(role, state)
            p = cfg.per_miner_power(state)
            res_s[c] += dur
            e_idle_j[c] += p * dur
            if state not in ("OFFLINE", "DISQUALIFIED"):
                diff_j[c] += (cfg.P_hash - p) * dur
    out = {}
    for c in COMPONENTS:
        out[f"residency_{c}_s"] = res_s[c]
        out[f"energy_{c}_kwh"] = e_idle_j[c] / JOULES_PER_KWH
        out[f"power_null_difference_{c}_kwh"] = diff_j[c] / JOULES_PER_KWH
    out["range_idle_energy_difference_kwh"] = diff_j["PRIMARY_LOW_POWER_LISTEN"] / JOULES_PER_KWH
    out["reserve_standby_energy_difference_kwh"] = diff_j["RESERVE_STANDBY"] / JOULES_PER_KWH
    out["wake_energy_difference_kwh"] = diff_j["RESERVE_WAKING"] / JOULES_PER_KWH
    out["activated_reserve_energy_kwh"] = e_idle_j["ACTIVATED_RESERVE_HASHING"] / JOULES_PER_KWH
    out["total_low_power_state_difference_kwh"] = sum(diff_j.values()) / JOULES_PER_KWH
    return out


if __name__ == "__main__":
    info = assert_seed_disjointness()
    print("fresh pilot seeds       :", info["pilot"])
    print("fresh confirmatory[0/11]:", info["confirmatory"][0], info["confirmatory"][-1])
    print("analysis seed           :", ANALYSIS_SEED_8R)
    print("previous registry seeds :", info["previous_registry_size"], "(all disjoint)")
    for row in SCENARIOS:
        cfg = build_config_8r(row, info["pilot"][0])
        print(f"{row['scenario_id']:32s} mode={cfg.controller.mode:34s} "
              f"floor={'on' if cfg.security_floor.enabled else 'off'} "
              f"leases={'on' if cfg.range_lease.enabled else 'off'}")
