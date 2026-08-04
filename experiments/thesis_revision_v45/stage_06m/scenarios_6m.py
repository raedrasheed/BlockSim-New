#!/usr/bin/env python3
"""Stage 6M — resource-minimal confirmatory design (single source of truth).

SUPERSESSION.  The previous Stage-6 preregistration (22 scenarios x 30 seeds = 660 logical
rows, 630 physical executions) is superseded BEFORE data collection: zero confirmatory seeds
were executed, the redesign was caused solely by measured compute infeasibility (124 days of
resource-aware execution against a host with no lifetime guarantee), and no effect size or
outcome direction informed it.  The engine, search core, target and difficulty are unchanged.

The algorithm remains PoCol.  The energy-saving mechanism remains THE IDLE POLICY WITHIN
PoCol.  Nonce-domain partitioning alone is never an energy-saving mechanism.
"""
from __future__ import annotations

import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
STAGE6 = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_06"
for p in (str(REPO_ROOT), str(STAGE6), str(HERE)):
    if p not in sys.path:
        sys.path.insert(0, p)

from Models.PoCol.stage2.config import Stage2Config, a1_continuous_control_kwh  # noqa: E402
from generate_seed_registry import build_rows, child_seed                       # noqa: E402
from scenarios import floor_policy, initial_active_primary_hash_rate            # noqa: E402

# ------------------------------------------------------------------ the minimal core
#: Exact frozen core.  Range leases, reassignment, the adversarial model and the incentive
#: model are DISABLED (never configured); dynamic difficulty is forbidden (the engine has no
#: such mechanism and the difficulty below is fixed).
CORE = dict(num_miners=20, horizon_T=300.0, nonce_domain_size=1600, difficulty=1000,
            batch_size=25, base_hash_rate=100.0, reserve_fraction=0.20,
            P_hash=21.5, P_listen=2.15, P_reserve=2.15, P_wake=10.75, P_offline=0.0)

#: Analytical continuous-power reference for the core: 20 x 21.5 W x 300 s / 3.6e6.
A1_CORE_KWH = 0.035833333333333335
A1_TOLERANCE_KWH = 1e-9

#: Exploratory full-scale sanity checks (NON-INFERENTIAL; never enter any test or interval).
SCALE = dict(num_miners=141, horizon_T=300.0, nonce_domain_size=4000, difficulty=1000,
             batch_size=50, base_hash_rate=100.0, reserve_fraction=0.20,
             P_hash=21.5, P_listen=2.15, P_reserve=2.15, P_wake=10.75, P_offline=0.0)

#: The operational floor minimum: 0.80 x the initial active-primary ACTUAL hash rate.
FLOOR_FRACTION = 0.80

CONFIRMATORY = [
    {"scenario_id": "M01_HET_IDLE", "role": "CONFIRMATORY",
     "heterogeneous_hash_rates": True, "security_floor": False,
     "hypotheses": "H-M1;H-M3(control)"},
    {"scenario_id": "M02_HOM_IDLE", "role": "CONFIRMATORY",
     "heterogeneous_hash_rates": False, "security_floor": False,
     "hypotheses": "H-M2"},
    {"scenario_id": "M03_HET_IDLE_FLOOR", "role": "CONFIRMATORY",
     "heterogeneous_hash_rates": True, "security_floor": True,
     "hypotheses": "H-M3"},
]
EXPLORATORY = [
    {"scenario_id": "X01_SCALE_HET_IDLE", "role": "EXPLORATORY_SCALE_CHECK",
     "heterogeneous_hash_rates": True, "security_floor": False, "hypotheses": "NONE"},
    {"scenario_id": "X02_SCALE_HET_IDLE_FLOOR", "role": "EXPLORATORY_SCALE_CHECK",
     "heterogeneous_hash_rates": True, "security_floor": True, "hypotheses": "NONE"},
]

# ------------------------------------------------------------------ seeds
N_CONFIRMATORY_SEEDS = 10          # the FIRST 10 existing confirmatory seeds, indexes 0..9
STRUCTURAL_PILOT_SEED_INDEXES = (0, 1)      # PILOT class; disjoint from all confirmatory seeds
SCALE_CHECK_PILOT_SEED_INDEX = {"X01_SCALE_HET_IDLE": 2, "X02_SCALE_HET_IDLE_FLOOR": 3}
#: Full detailed ledgers are preserved ONLY for these two audit runs (Stage 7M).
AUDIT_RUNS = (("M01_HET_IDLE", 0), ("M03_HET_IDLE_FLOOR", 0))


def confirmatory_seeds() -> list:
    """The first 10 seeds of the EXISTING Stage-6 confirmatory registry, unchanged."""
    rows = [r for r in build_rows() if r["seed_class"] == "CONFIRMATORY"]
    rows.sort(key=lambda r: int(r["seed_index"]))
    return [int(r["master_seed_decimal"]) for r in rows[:N_CONFIRMATORY_SEEDS]]


def pilot_seeds() -> list:
    rows = [r for r in build_rows() if r["seed_class"] == "PILOT"]
    rows.sort(key=lambda r: int(r["seed_index"]))
    return [int(r["master_seed_decimal"]) for r in rows]


def build_config_6m(row: dict, master_seed: int) -> Stage2Config:
    """One frozen config.  Leases / reassignment / adversarial / incentive stay at their
    DISABLED defaults: no kwarg is ever passed for them, so all scenarios share the identical
    disabled objects and the ONLY treatment differences are the two declared factors."""
    base = SCALE if row["role"] == "EXPLORATORY_SCALE_CHECK" else CORE
    hetero = bool(row["heterogeneous_hash_rates"])
    kwargs = dict(base)
    kwargs["heterogeneous_hash_rates"] = hetero
    kwargs["template_seed"] = child_seed(master_seed, "template")
    if row["security_floor"]:
        minimum = FLOOR_FRACTION * initial_active_primary_hash_rate(
            base["num_miners"], base["reserve_fraction"], base["base_hash_rate"], hetero)
        kwargs["security_floor"] = floor_policy(minimum, None)
        kwargs["floor_unattainable_policy"] = "CONTINUE_DEGRADED"
    return Stage2Config(**kwargs)


# ------------------------------------------------------------------ within-run power null
#: State partition for the power-null counterfactual, taken verbatim from the accepted
#: ``Stage2Config.per_miner_power`` mapping.  ACTIVE-priced group = every state whose accepted
#: price is P_hash/P_listen/P_reserve/P_wake; OFFLINE-priced group = OFFLINE, DISQUALIFIED.
NULL_ACTIVE_STATES = ("REGISTERED", "RESERVE", "ACTIVE_HASHING", "EXHAUSTED_PENDING",
                      "LOW_POWER_LISTEN", "WAKING")
NULL_OFFLINE_STATES = ("OFFLINE", "DISQUALIFIED")
JOULES_PER_KWH = 3_600_000.0


def energy_pair_kwh(run, cfg: Stage2Config) -> dict:
    """E_idle and E_power_null from the SAME residency ledger of one executed run.

    No separate power-control simulation is executed: the event path is provably invariant
    under idle-price substitution (test_s6m_04), so substituting prices in the accounting is
    exact, not approximate.
    """
    e_idle_j = e_null_j = 0.0
    residency = {}
    unknown = []
    for mid in run.miners:
        for state, dur in run.miners[mid].duration.items():
            residency[state] = residency.get(state, 0.0) + dur
            e_idle_j += cfg.per_miner_power(state) * dur
            if state in NULL_ACTIVE_STATES:
                e_null_j += cfg.P_hash * dur
            elif state in NULL_OFFLINE_STATES:
                e_null_j += cfg.P_offline * dur
            else:
                unknown.append(state)
    if unknown:
        raise RuntimeError(f"unmapped residency states {sorted(set(unknown))}: the power-null "
                           f"partition would be wrong (MODEL failure)")
    e_idle, e_null = e_idle_j / JOULES_PER_KWH, e_null_j / JOULES_PER_KWH
    return {"E_idle_kwh": e_idle, "E_power_null_kwh": e_null,
            "absolute_reduction_kwh": e_null - e_idle,
            "relative_reduction": (e_null - e_idle) / e_null if e_null else None,
            "offline_residency_s": sum(residency.get(s, 0.0) for s in NULL_OFFLINE_STATES),
            "residency_by_state_s": {k: v for k, v in sorted(residency.items())}}


def assert_core_matches_directive() -> None:
    cfg = build_config_6m(CONFIRMATORY[0], 0)
    a1 = a1_continuous_control_kwh(cfg)
    if abs(a1 - A1_CORE_KWH) > A1_TOLERANCE_KWH:
        raise SystemExit(f"STAGE_6M_BLOCKED — A1 core mismatch: {a1!r} != {A1_CORE_KWH!r}")
    for k, v in CORE.items():
        if getattr(cfg, k) != v:
            raise SystemExit(f"STAGE_6M_BLOCKED — core drift: {k}={getattr(cfg, k)!r} != {v!r}")


if __name__ == "__main__":
    assert_core_matches_directive()
    m01 = build_config_6m(CONFIRMATORY[0], 0)
    m03 = build_config_6m(CONFIRMATORY[2], 0)
    print(f"core OK; A1_core = {A1_CORE_KWH}")
    print(f"confirmatory seeds: {len(confirmatory_seeds())} -> "
          f"{confirmatory_seeds()[0]} .. {confirmatory_seeds()[-1]}")
    print(f"M03 floor minimum : {m03.security_floor.minimum_active_hash_rate} "
          f"(H0 het = {initial_active_primary_hash_rate(20, 0.2, 100.0, True)})")
    print(f"runs: {len(CONFIRMATORY)} x {N_CONFIRMATORY_SEEDS} = "
          f"{len(CONFIRMATORY) * N_CONFIRMATORY_SEEDS} confirmatory + {len(EXPLORATORY)} scale checks")
