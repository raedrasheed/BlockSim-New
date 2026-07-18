"""Difficulty selection: hash-rate policy (H1/H2) x difficulty mode (D1/D2/D3).

The ONLY place initial difficulty is decided. Rules:
- D1 CONSTANT: target frozen at the REFERENCE work (reference_hashrate * T),
  regardless of N. Under H2 this demonstrates un-retargeted dilution (600/N).
- D2 SCALED: target recomputed from the CURRENT aggregate hash rate
  (W = H_network(N) * T). Under H1 this equals D1 by construction, because the
  aggregate never changes -- difficulty must NOT scale with N there.
- D3 RETARGET: initial target = d3_initial_factor * reference work; subsequent
  changes only via retarget.Retargeter on accepted-block timestamps.
"""
from __future__ import annotations

from .configuration import (
    DiffExpConfig, D1_CONSTANT, D2_SCALED, D3_RETARGET, HW_H1, HW_H2,
    AGG_HASHRATE_HPS,
)
from . import target as tg


def initial_work(cfg: DiffExpConfig) -> float:
    """Expected work (hashes/block) the run STARTS with, per policy x mode."""
    mode = cfg.difficulty.mode
    if mode == D1_CONSTANT:
        return tg.expected_work(cfg.reference_hashrate(), cfg.t_target)
    if mode == D2_SCALED:
        return tg.expected_work(cfg.network_hashrate(), cfg.t_target)
    if mode == D3_RETARGET:
        return (tg.expected_work(cfg.reference_hashrate(), cfg.t_target)
                * float(cfg.difficulty.d3_initial_factor))
    raise ValueError(f"unknown difficulty mode {mode!r}")


def initial_target(cfg: DiffExpConfig) -> int:
    return tg.target_from_work(initial_work(cfg))


def difficulty_ratio_vs_reference(cfg: DiffExpConfig) -> float:
    """D_N / D_reference for the run's INITIAL difficulty."""
    ref_w = tg.expected_work(cfg.reference_hashrate(), cfg.t_target)
    return tg.difficulty_from_target(initial_target(cfg)) / \
        tg.difficulty_from_target(tg.target_from_work(ref_w))


def difficulty_by_population(miner_counts, hardware, mode,
                             h2_miner_hashrate_hps=1.41e12, t_target=600.0):
    """Analytic table rows: difficulty/target/expected interval per N."""
    rows = []
    for N in miner_counts:
        cfg = DiffExpConfig(N=N, hardware=hardware,
                            h2_miner_hashrate_hps=h2_miner_hashrate_hps)
        from .configuration import DifficultyConfig
        cfg = DiffExpConfig(N=N, hardware=hardware,
                            difficulty=DifficultyConfig(mode=mode),
                            h2_miner_hashrate_hps=h2_miner_hashrate_hps,
                            t_target=t_target)
        t = initial_target(cfg)
        d = tg.difficulty_from_target(t)
        rows.append({
            "hardware": hardware, "difficulty_mode": mode, "N": N,
            "per_miner_hashrate_hps": cfg.per_miner_hashrate(),
            "network_hashrate_hps": cfg.network_hashrate(),
            "target": str(t),                    # big int -> string for CSV
            "target_bits": t.bit_length(),
            "difficulty_expected_hashes": d,
            "difficulty_ratio_vs_reference": difficulty_ratio_vs_reference(cfg),
            "p_success": tg.p_from_target(t),
            "expected_block_interval_s": tg.expected_block_time(t, cfg.network_hashrate()),
        })
    return rows
