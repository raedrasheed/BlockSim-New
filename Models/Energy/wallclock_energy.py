"""Wall-clock, state-based energy accounting for the PoCol thesis simulator path.

This module is the **authoritative** energy model for the thesis (Stage 2 of the
scientific revision). It replaces two artifacts in the previous accounting:

  * the PoW `/100` hash-rate normalization (energy grew with miner count), and
  * the PoCol `block_time / N` division (energy shrank with miner count).

Both are replaced by an explicit wall-clock state model:

    E_total = Σ_i ( P_i_active · t_i_active
                  + P_i_idle   · t_i_idle
                  + E_i_coordination )

Energy is derived from **actual state duration**, never divided or multiplied by
the number of miners, and never scaled by a redundancy factor.

Unit conventions (explicit in every public name):
    *_hps   : hashes per second (H/s)
    *_j_per_th : joules per terahash (J/TH)
    *_power_w  : watts (W)
    *_time_s   : seconds (s)
    *_energy_j : joules (J)
    *_energy_kwh : kilowatt-hours (kWh)

Fixed conversions:
    1 TH/s = 1e12 hashes/s
    1 kWh  = 3_600_000 J
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Fixed physical conversions
# ---------------------------------------------------------------------------
J_PER_KWH: float = 3_600_000.0
HASHES_PER_TH: float = 1e12

# Miner energy states
ACTIVE = "ACTIVE"
IDLE = "IDLE"
OFFLINE = "OFFLINE"
_VALID_STATES = (ACTIVE, IDLE, OFFLINE)


# ---------------------------------------------------------------------------
# Pure unit-conversion / invariant helpers
# ---------------------------------------------------------------------------
def joules_to_kwh(energy_j: float) -> float:
    """J -> kWh."""
    return float(energy_j) / J_PER_KWH


def kwh_to_joules(energy_kwh: float) -> float:
    """kWh -> J."""
    return float(energy_kwh) * J_PER_KWH


def th_per_s_to_hps(rate_th_per_s: float) -> float:
    """TH/s -> H/s."""
    return float(rate_th_per_s) * HASHES_PER_TH


def efficiency_j_per_hash(efficiency_j_per_th: float) -> float:
    """J/TH -> J/hash."""
    return float(efficiency_j_per_th) / HASHES_PER_TH


def active_power_w(hash_rate_hps: float, efficiency_j_per_th: float) -> float:
    """Active mining power (W) = H/s * J/hash.

    For the thesis baseline: 141e12 H/s * (21.5 / 1e12) J/hash = 3031.5 W.
    """
    return float(hash_rate_hps) * efficiency_j_per_hash(efficiency_j_per_th)


def network_active_power_w(network_hash_rate_hps: float,
                           efficiency_j_per_th: float) -> float:
    """Total network active power (W) for a fixed aggregate hash rate."""
    return active_power_w(network_hash_rate_hps, efficiency_j_per_th)


def continuous_energy_kwh(power_w: float, seconds: float) -> float:
    """Energy (kWh) for continuous operation at `power_w` for `seconds`."""
    return float(power_w) * float(seconds) / J_PER_KWH


def hashes_to_energy_j(hashes: float, efficiency_j_per_th: float) -> float:
    """Energy (J) implied by a hash count (power-independent cross-check)."""
    return float(hashes) * efficiency_j_per_hash(efficiency_j_per_th)


def equal_hash_rates_hps(network_hash_rate_hps: float, n_miners: int) -> List[float]:
    """Split a fixed aggregate hash rate into `n_miners` equal shares.

    Guarantees Σ_i H_i == network_hash_rate_hps (identity partition).
    """
    if n_miners <= 0:
        raise ValueError("n_miners must be > 0")
    per = float(network_hash_rate_hps) / n_miners
    return [per] * n_miners


# ---------------------------------------------------------------------------
# Per-miner wall-clock energy state machine
# ---------------------------------------------------------------------------
@dataclass
class MinerEnergyState:
    """Tracks one miner's active/idle/offline durations and coordination energy.

    Invariants enforced:
      * at most one interval is open at any time (no active/idle overlap);
      * a transition closes the preceding interval before opening the next;
      * time is non-decreasing;
      * flushing never accounts beyond the flush time and is idempotent.
    """
    miner_id: int
    hash_rate_hps: float
    efficiency_j_per_th: float
    idle_power_w: float = 0.0            # 0.0 == explicit theoretical lower bound

    # accumulated durations (s)
    active_time_s: float = 0.0
    idle_time_s: float = 0.0
    offline_time_s: float = 0.0
    # coordination energy (J), recorded separately; never invented
    coordination_energy_j: float = 0.0

    # open-interval bookkeeping (private)
    _open_state: Optional[str] = field(default=None, repr=False)
    _open_start_s: Optional[float] = field(default=None, repr=False)

    # ---- derived, unit-explicit ----
    @property
    def active_power_w(self) -> float:
        return active_power_w(self.hash_rate_hps, self.efficiency_j_per_th)

    def _add_duration(self, state: str, dt: float) -> None:
        if dt < 0:
            raise ValueError("negative duration")
        if state == ACTIVE:
            self.active_time_s += dt
        elif state == IDLE:
            self.idle_time_s += dt
        elif state == OFFLINE:
            self.offline_time_s += dt

    def _close_open(self, t: float) -> None:
        """Close the currently open interval at time t (no-op if none open)."""
        if self._open_state is None:
            return
        if self._open_start_s is not None:
            if t < self._open_start_s:
                raise ValueError(
                    f"time went backwards: t={t} < start={self._open_start_s}")
            self._add_duration(self._open_state, t - self._open_start_s)
        self._open_state = None
        self._open_start_s = None

    def transition_to(self, new_state: str, t: float) -> None:
        """Close the current interval at t, then open `new_state` at t."""
        if new_state not in _VALID_STATES:
            raise ValueError(f"invalid state {new_state!r}")
        self._close_open(t)                 # close-before-open (no overlap)
        self._open_state = new_state
        self._open_start_s = float(t)

    # convenience wrappers
    def begin_active(self, t: float) -> None:
        self.transition_to(ACTIVE, t)

    def begin_idle(self, t: float) -> None:
        self.transition_to(IDLE, t)

    def go_offline(self, t: float) -> None:
        self.transition_to(OFFLINE, t)

    def close(self, t: float) -> None:
        """Close any open interval at t. Idempotent."""
        self._close_open(t)

    def add_coordination_energy_j(self, energy_j: float) -> None:
        if energy_j < 0:
            raise ValueError("coordination energy must be >= 0")
        self.coordination_energy_j += float(energy_j)

    def flush_at(self, t_sim: float) -> None:
        """Close any open interval at the simulation cutoff. Idempotent.

        Never accounts time beyond `t_sim`: if the open interval started after
        `t_sim` (should not happen), zero time is added.
        """
        if self._open_state is None:
            return
        start = self._open_start_s if self._open_start_s is not None else t_sim
        dt = float(t_sim) - float(start)
        if dt < 0.0:
            dt = 0.0        # never account beyond t_sim; never negative
        self._add_duration(self._open_state, dt)
        self._open_state = None
        self._open_start_s = None

    # ---- energy accessors ----
    def active_energy_j(self) -> float:
        return self.active_time_s * self.active_power_w

    def idle_energy_j(self) -> float:
        return self.idle_time_s * self.idle_power_w

    def energy_j(self) -> float:
        """Total = active + idle + coordination (offline contributes 0 W)."""
        return self.active_energy_j() + self.idle_energy_j() + self.coordination_energy_j

    def energy_kwh(self) -> float:
        return joules_to_kwh(self.energy_j())

    # ---- hash cross-check ----
    def total_hashes(self) -> float:
        return self.hash_rate_hps * self.active_time_s

    def hash_based_active_energy_j(self) -> float:
        """Active energy computed from hash count (power-independent path)."""
        return hashes_to_energy_j(self.total_hashes(), self.efficiency_j_per_th)

    # ---- conservation ----
    def accounted_time_s(self) -> float:
        return self.active_time_s + self.idle_time_s + self.offline_time_s


# ---------------------------------------------------------------------------
# Network-level accountant
# ---------------------------------------------------------------------------
class WallClockEnergyAccountant:
    """Manages per-miner :class:`MinerEnergyState` objects for one network."""

    def __init__(self, efficiency_j_per_th: float):
        self.efficiency_j_per_th = float(efficiency_j_per_th)
        self.miners: Dict[int, MinerEnergyState] = {}

    def add_miner(self, miner_id: int, hash_rate_hps: float,
                  idle_power_w: float = 0.0) -> MinerEnergyState:
        st = MinerEnergyState(miner_id=miner_id, hash_rate_hps=hash_rate_hps,
                              efficiency_j_per_th=self.efficiency_j_per_th,
                              idle_power_w=idle_power_w)
        self.miners[miner_id] = st
        return st

    def add_equal_miners(self, n_miners: int, network_hash_rate_hps: float,
                         idle_power_w: float = 0.0) -> None:
        for i, h in enumerate(equal_hash_rates_hps(network_hash_rate_hps, n_miners)):
            self.add_miner(i, h, idle_power_w=idle_power_w)

    # transitions
    def transition(self, miner_id: int, state: str, t: float) -> None:
        self.miners[miner_id].transition_to(state, t)

    def close(self, miner_id: int, t: float) -> None:
        self.miners[miner_id].close(t)

    def flush_all(self, t_sim: float) -> None:
        for st in self.miners.values():
            st.flush_at(t_sim)

    # aggregates
    def sum_hash_rate_hps(self) -> float:
        return sum(st.hash_rate_hps for st in self.miners.values())

    def total_active_power_w(self) -> float:
        return sum(st.active_power_w for st in self.miners.values())

    def total_energy_j(self) -> float:
        return sum(st.energy_j() for st in self.miners.values())

    def total_energy_kwh(self) -> float:
        return joules_to_kwh(self.total_energy_j())

    def per_miner_energy_kwh(self) -> Dict[int, float]:
        return {mid: st.energy_kwh() for mid, st in self.miners.items()}
