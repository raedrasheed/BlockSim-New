"""Stage 5B1 three-tier hashing for exact + semantic deduplication.

  configuration_hash      : all configuration + labelling fields.
  execution_semantics_hash: only fields that change executable behaviour or
                            measured output (drops interpretation-only labels and
                            parameters proven inactive for the scenario).
  analysis_group_hash     : identifies planned paired / reused analysis groups.

Rule: no two planned physical runs may share one execution_semantics_hash + seed
unless documented as deliberate replication.
"""

from __future__ import annotations
import hashlib
import json

# scenarios that use disjoint ranges (allocation_policy is behaviour-affecting)
_DISJOINT = {"B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"}
# only C2 has an idle policy
_IDLE_SCEN = {"C2"}
# B3 and C1 share one underlying execution model
_EXEC_MODEL = {
    "B0": "independent_full_parallel", "B1": "common_from_zero",
    "B2": "common_random_start", "B3_C1_CONTINUOUS_DISJOINT": "common_disjoint_continuous",
    "C2": "common_disjoint_idle",
}


def _h(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


def idle_semantically_active(cfg: dict) -> bool:
    """C2 idle changes output only when a miner can complete its range early:
    heterogeneous rates with equal ranges, or mu < 1. Homogeneous equal-range
    with mu >= 1 has guaranteed zero idle -> idle_power_ratio is inactive."""
    if cfg.get("scenario_id") not in _IDLE_SCEN:
        return False
    hetero = str(cfg.get("hash_rate_distribution", "homogeneous")) != "homogeneous"
    equal = str(cfg.get("allocation_policy", "equal")).endswith("equal")
    small_mu = float(cfg.get("mu", 2.0)) < 1.0
    return small_mu or (hetero and equal)


def configuration_hash(cfg: dict) -> str:
    return _h(cfg)


def execution_semantics_hash(cfg: dict) -> str:
    scen = cfg.get("scenario_id")
    sem = dict(
        exec_model=_EXEC_MODEL.get(scen, scen),
        seed=cfg.get("seed"),
        miner_count=cfg.get("miner_count"),
        network_hash_rate_hps=cfg.get("network_hash_rate_hps"),
        efficiency_j_per_th=cfg.get("efficiency_j_per_th"),
        simulation_duration_s=cfg.get("simulation_duration_s"),
        target_block_interval_s=cfg.get("target_block_interval_s"),
        mu=cfg.get("mu"),
        hash_rate_distribution=cfg.get("hash_rate_distribution"),
        inactive_miner_fraction=cfg.get("inactive_miner_fraction"),
        propagation_delay_mean_s=cfg.get("propagation_delay_mean_s"),
    )
    # allocation matters only for disjoint scenarios
    if scen in _DISJOINT:
        sem["allocation_policy"] = cfg.get("allocation_policy")
    # idle ratio matters only when idle is semantically active
    if idle_semantically_active(cfg):
        sem["idle_power_ratio"] = cfg.get("idle_power_ratio")
    return _h(sem)


def analysis_group_hash(cfg: dict) -> str:
    grp = dict(
        exec_model=_EXEC_MODEL.get(cfg.get("scenario_id")),
        hypothesis=cfg.get("hypothesis_id"),
        matrix_class=cfg.get("matrix_class"),
        miner_count=cfg.get("miner_count"),
        hash_rate_distribution=cfg.get("hash_rate_distribution"),
        allocation_policy=cfg.get("allocation_policy") if cfg.get("scenario_id") in _DISJOINT else None,
        mu=cfg.get("mu"),
        propagation_delay_mean_s=cfg.get("propagation_delay_mean_s"),
        inactive_miner_fraction=cfg.get("inactive_miner_fraction"),
        idle_power_ratio=cfg.get("idle_power_ratio") if idle_semantically_active(cfg) else None,
    )
    return _h(grp)
