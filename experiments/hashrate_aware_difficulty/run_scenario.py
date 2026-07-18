"""Run ONE hashrate-aware-difficulty scenario; print one JSON record.

Fresh-subprocess unit for run_matrix.py.

  python experiments/hashrate_aware_difficulty/run_scenario.py \
      pocol_disjoint_nonce 100 --hardware H1 --mode D2 --seed 3
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from experiments.hashrate_aware_difficulty.configuration import (
    DiffExpConfig, DifficultyConfig, PowerConfig, PROTOCOLS,
    HW_H1, HW_H2, D1_CONSTANT, D2_SCALED, D3_RETARGET,
)
from experiments.hashrate_aware_difficulty.mining_round import simulate
from experiments.hashrate_aware_difficulty.difficulty import initial_target

_HW = {"H1": HW_H1, "H2": HW_H2}
_MODE = {"D1": D1_CONSTANT, "D2": D2_SCALED, "D3": D3_RETARGET}


def run(protocol, N, hardware="H1", mode="D2", seed=0, sim=10200.0,
        h2_rate=1.41e12, budget=1200.0, window=10, clamp_min=0.25,
        clamp_max=4.0, initial_factor=1.0, idle=0.0, want_blocks=False):
    cfg = DiffExpConfig(
        N=N, protocol=protocol, hardware=_HW.get(hardware, hardware),
        difficulty=DifficultyConfig(
            mode=_MODE.get(mode, mode), d3_window_blocks=window,
            d3_clamp_min=clamp_min, d3_clamp_max=clamp_max,
            d3_initial_factor=initial_factor),
        power=PowerConfig(idle_ratio=idle),
        seed=seed, sim_seconds=sim, h2_miner_hashrate_hps=h2_rate,
        domain_time_budget=budget)
    retargeter = None
    if cfg.difficulty.mode == D3_RETARGET:
        from experiments.hashrate_aware_difficulty.retarget import Retargeter
        retargeter = Retargeter(initial_target(cfg), window_blocks=window,
                                clamp_min=clamp_min, clamp_max=clamp_max,
                                t_target=cfg.t_target)
    metrics, miners, blocks = simulate(cfg, retargeter=retargeter)
    metrics["mean_target_str"] = repr(int(metrics.pop("mean_target")))
    if want_blocks:
        metrics["_blocks"] = [{
            "height": b.height, "commit_time": b.commit_time,
            "winner_id": b.winner_id, "template_index": b.template_index,
            "target_bits": b.target.bit_length(),
            "difficulty": b.difficulty,
            "attempts_this_template": b.attempts_this_template,
        } for b in blocks]
    return metrics


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("protocol", choices=PROTOCOLS)
    ap.add_argument("N", type=int)
    ap.add_argument("--hardware", choices=["H1", "H2"], default="H1")
    ap.add_argument("--mode", choices=["D1", "D2", "D3"], default="D2")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--sim", type=float, default=10200.0)
    ap.add_argument("--h2-rate", type=float, default=1.41e12)
    ap.add_argument("--budget", type=float, default=1200.0)
    ap.add_argument("--window", type=int, default=10)
    ap.add_argument("--initial-factor", type=float, default=1.0)
    ap.add_argument("--idle", type=float, default=0.0)
    ap.add_argument("--blocks", action="store_true")
    a = ap.parse_args()
    print(json.dumps(run(a.protocol, a.N, hardware=a.hardware, mode=a.mode,
                         seed=a.seed, sim=a.sim, h2_rate=a.h2_rate,
                         budget=a.budget, window=a.window,
                         initial_factor=a.initial_factor, idle=a.idle,
                         want_blocks=a.blocks)))
