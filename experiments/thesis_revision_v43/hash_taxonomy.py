"""Stage 5B1B corrected hash taxonomy.

The Stage-5B1 `execution_semantics_hash` conflated scientific execution semantics
with the stochastic seed (it INCLUDED the seed), so it could not group the 30 seeds
of one scientific configuration. Stage 5B1B separates the layers:

  A. scientific_semantics_hash  -- ONLY fields that define scientific execution
     semantics (executable scenario, sizes, rates, policies, engine version).
     EXCLUDES seed/stream seeds/run_id/path/timestamp/worker/B3-vs-C1 labels/
     retention flags/presentation. Repeats across the 30 seeds of a config.
  B. run_execution_hash         -- scientific_semantics_hash + master seed + all
     derived stream seeds + engine version + dependency-lock checksum. Identifies
     ONE stochastic physical run (unique across the whole matrix).
  C. interpretation_hash        -- interpretive labels + reporting role. B3 and C1
     differ here but share one run_execution_hash.
  D. analysis_group_hash        -- the intended statistical / paired comparison
     group (hypothesis + matrix class + design factors). May be coarser than a
     scientific-semantics group when a design pools several configs; in this matrix
     each analysis cell is one scientific config, so both partitions coincide (63).
"""

from __future__ import annotations
import hashlib
import json

from experiments.thesis_revision_v43.hashing import _EXEC_MODEL, idle_semantically_active, _DISJOINT
from experiments.thesis_revision_v43.scenario_engine import derive_stream_seeds, ENGINE_VERSION


def _h(d: dict) -> str:
    return hashlib.sha256(json.dumps(d, sort_keys=True, default=str).encode()).hexdigest()[:16]


def scientific_semantics_hash(cfg: dict, engine_version: str = ENGINE_VERSION) -> str:
    """Layer A: scientific execution semantics only. NO seed, NO labels."""
    scen = cfg.get("scenario_id")
    sem = dict(
        exec_model=_EXEC_MODEL.get(scen, scen),
        miner_count=cfg.get("miner_count"),
        simulation_duration_s=cfg.get("simulation_duration_s"),
        network_hash_rate_hps=cfg.get("network_hash_rate_hps"),
        efficiency_j_per_th=cfg.get("efficiency_j_per_th"),
        target_block_interval_s=cfg.get("target_block_interval_s"),
        mu=cfg.get("mu"),
        hash_rate_distribution=cfg.get("hash_rate_distribution"),
        inactive_miner_fraction=cfg.get("inactive_miner_fraction"),
        propagation_delay_mean_s=cfg.get("propagation_delay_mean_s"),
        block_size_bytes=cfg.get("block_size_bytes", 1_000_000),
        engine_version=engine_version,
    )
    if scen in _DISJOINT:
        sem["allocation_policy"] = cfg.get("allocation_policy")
    if idle_semantically_active(cfg):
        sem["idle_power_ratio"] = cfg.get("idle_power_ratio")
    return _h(sem)


def run_execution_hash(cfg: dict, dependency_lock_sha256: str,
                       engine_version: str = ENGINE_VERSION) -> str:
    """Layer B: one stochastic physical run (semantics + seed + streams + code + deps)."""
    seed = cfg.get("seed")
    streams = derive_stream_seeds(int(seed)) if seed is not None else {}
    payload = dict(
        scientific_semantics_hash=scientific_semantics_hash(cfg, engine_version),
        master_seed=seed,
        stream_seeds=streams,
        engine_version=engine_version,
        dependency_lock_sha256=dependency_lock_sha256,
    )
    return _h(payload)


def interpretation_hash(cfg: dict) -> str:
    """Layer C: interpretive labels + reporting role (does NOT create a physical run)."""
    return _h(dict(interpretation_labels=cfg.get("interpretation_labels"),
                   hypothesis_id=cfg.get("hypothesis_id"),
                   matrix_class=cfg.get("matrix_class")))


def analysis_group_hash(cfg: dict) -> str:
    """Layer D: intended statistical comparison / paired group."""
    scen = cfg.get("scenario_id")
    grp = dict(
        exec_model=_EXEC_MODEL.get(scen),
        hypothesis=cfg.get("hypothesis_id"),
        matrix_class=cfg.get("matrix_class"),
        miner_count=cfg.get("miner_count"),
        hash_rate_distribution=cfg.get("hash_rate_distribution"),
        allocation_policy=cfg.get("allocation_policy") if scen in _DISJOINT else None,
        mu=cfg.get("mu"),
        propagation_delay_mean_s=cfg.get("propagation_delay_mean_s"),
        inactive_miner_fraction=cfg.get("inactive_miner_fraction"),
        idle_power_ratio=cfg.get("idle_power_ratio") if idle_semantically_active(cfg) else None,
    )
    return _h(grp)


def stream_seed_columns(seed: int) -> dict:
    """Named stream seeds flattened for the matrix CSV."""
    return {f"stream_seed_{name}": val for name, val in derive_stream_seeds(int(seed)).items()}
