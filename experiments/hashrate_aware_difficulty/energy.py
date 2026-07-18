"""Energy accounting for the difficulty experiment.

Re-uses the audited wall-clock state-integration model
(experiments/fixed_600s_pocol/miner_state.MinerState): ACTIVE/IDLE/SLEEP,
E_i = P_a*t_a + P_i*t_i + P_s*t_s, hashes only while ACTIVE, exact finalization.
Never divided by N, never a 1/N multiplier, never computed from block count.
"""
from __future__ import annotations

from experiments.fixed_600s_pocol.miner_state import (  # noqa: F401 (re-export)
    MinerState, ACTIVE, IDLE, SLEEP,
)


def build_miners(cfg):
    """N equal miners from a DiffExpConfig (initially IDLE; engine activates)."""
    r = cfg.per_miner_hashrate()
    p_active = cfg.per_miner_power_w()
    p_idle = p_active * cfg.power.idle_ratio
    p_sleep = p_active * cfg.power.sleep_ratio
    return [MinerState(miner_id=i, hashrate_hps=r, active_power_w=p_active,
                       idle_power_w=p_idle, sleep_power_w=p_sleep)
            for i in range(cfg.N)]
