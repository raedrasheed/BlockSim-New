"""Per-miner power-state model with exact wall-clock energy integration.

State machine per miner: ACTIVE / IDLE / SLEEP. On every transition:

    elapsed   = current_time - last_state_change_time
    energy_j += power(previous_state) * elapsed
    if previous_state == ACTIVE:
        cumulative_hashes += hashrate_hps * elapsed
    last_state_change_time = current_time

E_i = P_active*t_active + P_idle*t_idle + P_sleep*t_sleep, network = sum(E_i).
Never divided by N, never charged per block, never double-charged.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

ACTIVE = "ACTIVE"
IDLE = "IDLE"
SLEEP = "SLEEP"
STATES = (ACTIVE, IDLE, SLEEP)

_J_PER_KWH = 3.6e6


@dataclass
class MinerState:
    miner_id: int
    hashrate_hps: float
    active_power_w: float
    idle_power_w: float
    sleep_power_w: float

    current_state: str = IDLE            # rounds activate miners explicitly
    last_state_change_time: float = 0.0

    active_time_s: float = 0.0
    idle_time_s: float = 0.0
    sleep_time_s: float = 0.0

    cumulative_hashes: float = 0.0
    cumulative_energy_j: float = 0.0

    evaluated_candidates: int = 0
    assigned_candidates: int = 0         # cumulative across templates/rounds
    exhausted_assignment: bool = False
    found_solution: bool = False
    wins: int = 0

    def _power(self, state):
        if state == ACTIVE:
            return self.active_power_w
        if state == IDLE:
            return self.idle_power_w
        if state == SLEEP:
            return self.sleep_power_w
        raise ValueError(f"unknown state {state!r}")

    def _integrate(self, current_time):
        elapsed = current_time - self.last_state_change_time
        if elapsed < -1e-9:
            raise ValueError(
                f"time reversed for miner {self.miner_id}: "
                f"{current_time} < {self.last_state_change_time}")
        if elapsed <= 0:
            return
        self.cumulative_energy_j += self._power(self.current_state) * elapsed
        if self.current_state == ACTIVE:
            self.active_time_s += elapsed
            self.cumulative_hashes += self.hashrate_hps * elapsed
        elif self.current_state == IDLE:
            self.idle_time_s += elapsed
        else:
            self.sleep_time_s += elapsed
        self.last_state_change_time = current_time

    def transition(self, new_state, current_time):
        """Charge the previous state up to current_time, then switch."""
        if new_state not in STATES:
            raise ValueError(f"unknown state {new_state!r}")
        self._integrate(current_time)
        self.last_state_change_time = current_time   # exact stamp even if elapsed==0
        self.current_state = new_state

    def finalize(self, sim_end):
        """Integrate the final open interval exactly to the simulation end."""
        self._integrate(sim_end)
        self.last_state_change_time = sim_end

    @property
    def cumulative_energy_kwh(self):
        return self.cumulative_energy_j / _J_PER_KWH

    @property
    def total_state_time_s(self):
        return self.active_time_s + self.idle_time_s + self.sleep_time_s

    def to_dict(self):
        d = asdict(self)
        d["cumulative_energy_kwh"] = self.cumulative_energy_kwh
        d["total_state_time_s"] = self.total_state_time_s
        return d


def build_miners(cfg):
    """N MinerState objects from a FixedRoundConfig (all initially IDLE at t=0;
    the round engine activates miners with non-empty assignments)."""
    r, p_active = cfg.per_miner_rate_power()
    p_idle = p_active * cfg.power.idle_ratio
    p_sleep = p_active * cfg.power.sleep_ratio
    return [MinerState(miner_id=i, hashrate_hps=r, active_power_w=p_active,
                       idle_power_w=p_idle, sleep_power_w=p_sleep)
            for i in range(cfg.N)]
