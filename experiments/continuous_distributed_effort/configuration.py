"""Configuration for the continuous distributed-effort experiment.

Defines the modes, scheduling policies, hardware normalization policies, and
power configuration, and builds per-miner hardware from a scenario.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from .power_states import Miner, ACTIVE

# ---- physical constants (H1, matching the corrected experiment) ----
AGG_HASHRATE_HPS = 141e12                 # 141 TH/s
EFF_J_PER_TH = 21.5                       # J per TH
AGG_ACTIVE_POWER_W = 141.0 * EFF_J_PER_TH  # 141 TH/s * 21.5 J/TH = 3031.5 W
GRID_EF_KG_PER_KWH = 0.445

# ---- experiment enumerations ----
MODE_A = "COMMON_TEMPLATE_DUPLICATE_BASELINE"
MODE_B = "POCOL_DISJOINT_NONCE"
MODE_C1 = "INDEPENDENT_HEADERS_EQUAL_TOTAL_BUDGET"
MODE_C2 = "INDEPENDENT_HEADERS_FULL_PER_MINER_BUDGET"
MODES = (MODE_A, MODE_B, MODE_C1, MODE_C2)

SCHED_IMMEDIATE = "IMMEDIATE_RESTART"
SCHED_FIXED_SLOT = "FIXED_SLOT_IDLE"
SCHEDULES = (SCHED_IMMEDIATE, SCHED_FIXED_SLOT)

HW_H1 = "H1_FIXED_AGGREGATE_NETWORK_HASHRATE"
HW_H2 = "H2_FIXED_PER_MINER_HARDWARE"
HARDWARE = (HW_H1, HW_H2)


@dataclass(frozen=True)
class PowerConfig:
    active_ratio: float = 1.0
    idle_ratio: float = 0.10
    sleep_ratio: float = 0.0
    use_sleep: bool = False          # if True, finished miners go to SLEEP not IDLE


@dataclass(frozen=True)
class ExperimentConfig:
    N: int
    M: int
    mode: str = MODE_B
    schedule: str = SCHED_FIXED_SLOT
    hardware: str = HW_H1
    power: PowerConfig = field(default_factory=PowerConfig)
    slot_seconds: float = 600.0
    sim_seconds: float = 10000.0
    # H2 per-miner hardware defaults (fixed, independent of N)
    h2_active_power_w: float = 100.0
    seed: int = 0

    def per_miner_hashrate_power(self):
        """Return (hashrate_hps, active_power_w) for one miner under the policy."""
        if self.hardware == HW_H1:
            return AGG_HASHRATE_HPS / self.N, AGG_ACTIVE_POWER_W / self.N
        elif self.hardware == HW_H2:
            # calibrated so a full-domain scan takes exactly one slot: r = M / T
            return self.M / self.slot_seconds, self.h2_active_power_w
        raise ValueError(f"unknown hardware policy {self.hardware!r}")

    def calibrated_M_for_slot(self):
        """The domain size for which a full-domain scan fills exactly one slot
        under this policy (used by the primary deterministic fixed-slot runs)."""
        r, _ = self.per_miner_hashrate_power()
        return int(round(r * self.slot_seconds))


def build_miners(cfg: ExperimentConfig):
    """Create N Miner objects with idle/sleep powers derived from the ratios.

    All miners start ACTIVE at t=0 (they begin searching immediately).
    """
    r, p_active = cfg.per_miner_hashrate_power()
    p_idle = p_active * cfg.power.idle_ratio
    p_sleep = p_active * cfg.power.sleep_ratio
    miners = []
    for i in range(cfg.N):
        miners.append(Miner(
            miner_id=i, hashrate_hps=r,
            active_power_w=p_active, idle_power_w=p_idle, sleep_power_w=p_sleep,
            current_state=ACTIVE, last_state_change_time=0.0))
    return miners
