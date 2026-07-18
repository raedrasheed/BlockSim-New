"""Run ONE continuous distributed-effort scenario in a fresh interpreter.

Deterministic final-nonce worst case (no p) or stochastic (with --p). Prints one
JSON metrics record. This is the fresh-subprocess unit used by run_matrix.py so
no global state leaks between runs.

Example:
  python experiments/continuous_distributed_effort/run_scenario.py \
      --mode POCOL_DISJOINT_NONCE --N 10 --M 6000 --schedule FIXED_SLOT_IDLE \
      --hardware H2_FIXED_PER_MINER_HARDWARE --idle 0.1
"""
import os
import sys
import json
import argparse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from experiments.continuous_distributed_effort.configuration import (
    ExperimentConfig, PowerConfig, MODES, SCHEDULES, HARDWARE,
)
from experiments.continuous_distributed_effort.round_model import (
    simulate_continuous, deterministic_outcome, stochastic_outcome,
)


def run(mode, N, M, schedule, hardware, idle_ratio=0.10, sleep_ratio=0.0,
        use_sleep=False, seed=0, p=None, sim=10000.0, slot=600.0,
        h2_active_power_w=100.0):
    cfg = ExperimentConfig(
        N=N, M=M, mode=mode, schedule=schedule, hardware=hardware,
        power=PowerConfig(idle_ratio=idle_ratio, sleep_ratio=sleep_ratio, use_sleep=use_sleep),
        sim_seconds=sim, slot_seconds=slot, seed=seed, p_success=p,
        h2_active_power_w=h2_active_power_w)
    outcome_fn = stochastic_outcome if p is not None else deterministic_outcome
    metrics, _ = simulate_continuous(cfg, outcome_fn)
    metrics["seed"] = seed
    metrics["p_success"] = p
    metrics["deterministic"] = p is None
    return metrics


def _build_parser():
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", required=True, choices=MODES)
    ap.add_argument("--N", type=int, required=True)
    ap.add_argument("--M", type=int, required=True)
    ap.add_argument("--schedule", required=True, choices=SCHEDULES)
    ap.add_argument("--hardware", required=True, choices=HARDWARE)
    ap.add_argument("--idle", type=float, default=0.10)
    ap.add_argument("--sleep", type=float, default=0.0)
    ap.add_argument("--use-sleep", action="store_true")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--p", type=float, default=None)
    ap.add_argument("--sim", type=float, default=10000.0)
    ap.add_argument("--slot", type=float, default=600.0)
    ap.add_argument("--h2-power", type=float, default=100.0)
    return ap


if __name__ == "__main__":
    a = _build_parser().parse_args()
    rec = run(a.mode, a.N, a.M, a.schedule, a.hardware, idle_ratio=a.idle,
              sleep_ratio=a.sleep, use_sleep=a.use_sleep, seed=a.seed, p=a.p,
              sim=a.sim, slot=a.slot, h2_active_power_w=a.h2_power)
    print(json.dumps(rec))
