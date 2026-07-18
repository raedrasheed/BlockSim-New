"""Miner power-state model with state-based wall-clock energy integration.

A miner is always in exactly one of ACTIVE / IDLE / SLEEP. Energy is the integral
of the current state's power over wall-clock time — never tied to a block event,
never applied once per block, never divided by N.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field

ACTIVE = "ACTIVE"
IDLE = "IDLE"
SLEEP = "SLEEP"
STATES = (ACTIVE, IDLE, SLEEP)

_J_PER_KWH = 3.6e6


@dataclass
class Miner:
    miner_id: int
    hashrate_hps: float
    active_power_w: float
    idle_power_w: float
    sleep_power_w: float

    assigned_range_start: int = 0
    assigned_range_end: int = 0            # half-open [start, end)
    assigned_candidate_count: int = 0
    evaluated_candidate_count: int = 0

    current_state: str = ACTIVE
    last_state_change_time: float = 0.0

    active_time_s: float = 0.0
    idle_time_s: float = 0.0
    sleep_time_s: float = 0.0

    cumulative_energy_j: float = 0.0
    cumulative_hashes: float = 0.0

    exhausted_range: bool = False
    found_solution: bool = False

    def _state_power(self, state):
        if state == ACTIVE:
            return self.active_power_w
        if state == IDLE:
            return self.idle_power_w
        if state == SLEEP:
            return self.sleep_power_w
        raise ValueError(f"unknown state {state!r}")

    def _integrate_to(self, current_time):
        """Integrate energy (and hashes if ACTIVE) from last change to now."""
        elapsed = current_time - self.last_state_change_time
        if elapsed < 0:
            raise ValueError(f"time went backwards: {current_time} < {self.last_state_change_time}")
        p = self._state_power(self.current_state)
        self.cumulative_energy_j += p * elapsed
        if self.current_state == ACTIVE:
            self.active_time_s += elapsed
            self.cumulative_hashes += self.hashrate_hps * elapsed
        elif self.current_state == IDLE:
            self.idle_time_s += elapsed
        else:
            self.sleep_time_s += elapsed
        self.last_state_change_time = current_time

    def transition(self, new_state, current_time):
        """Close out the current state up to `current_time`, then switch."""
        if new_state not in STATES:
            raise ValueError(f"unknown state {new_state!r}")
        self._integrate_to(current_time)
        self.current_state = new_state

    def finalize(self, sim_time):
        """Integrate the final open interval up to the simulation horizon."""
        self._integrate_to(sim_time)

    @property
    def cumulative_energy_kwh(self):
        return self.cumulative_energy_j / _J_PER_KWH

    @property
    def total_state_time_s(self):
        return self.active_time_s + self.idle_time_s + self.sleep_time_s

    def to_dict(self):
        d = asdict(self)
        d["cumulative_energy_kwh"] = self.cumulative_energy_kwh
        return d
