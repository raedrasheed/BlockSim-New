"""Stage 8X — per-miner power-state residency ledger.

Energy in Stage 8X is *measured*, never asserted: it is state x power x time. This
module owns the state machine and the residency timers, and enforces the
conservation identity

        t_active,i + t_low,i = T          for every miner i

within a documented numerical tolerance.

States
------
ACTIVE      the ASIC is hashing at its full 234 TH/s and drawing P_active.
LOW_POWER   PoCol only: the miner has completed its assigned useful nonce range and
            has no further legitimate work in the current round/epoch. It draws
            ``alpha * P_active`` (an experimental sensitivity assumption).

Traditional PoW never enters LOW_POWER: a PoW miner rolls its own extranonce
locally and instantly, so it always has legitimate work.
"""

from __future__ import annotations

from typing import Dict, List

ACTIVE = "ACTIVE"
LOW_POWER = "LOW_POWER"
STATES = (ACTIVE, LOW_POWER)


class PowerStateLedger:
    """Tracks state residency and transitions for every miner over [0, T]."""

    def __init__(self, n_miners: int, horizon_s: float) -> None:
        self.n = int(n_miners)
        self.horizon = float(horizon_s)
        self.state: List[str] = [ACTIVE] * self.n
        self.since: List[float] = [0.0] * self.n
        self.t_active: List[float] = [0.0] * self.n
        self.t_low: List[float] = [0.0] * self.n

        # transition counters
        self.n_active_to_low = 0
        self.n_low_to_active = 0
        # low-power episode durations (closed episodes only, plus the tail at T)
        self.low_episodes: List[float] = []
        self.entered_low_once = [False] * self.n
        # simultaneity trace: (time, count_in_low) after each transition
        self._low_count = 0
        self._trace: List[tuple] = [(0.0, 0)]

    # ---------------- core transitions ----------------
    def _accrue(self, i: int, now: float) -> float:
        dt = max(0.0, float(now) - self.since[i])
        if self.state[i] == ACTIVE:
            self.t_active[i] += dt
        else:
            self.t_low[i] += dt
        self.since[i] = float(now)
        return dt

    def to_low_power(self, i: int, now: float) -> None:
        if self.state[i] == LOW_POWER:
            return
        self._accrue(i, now)
        self.state[i] = LOW_POWER
        self.n_active_to_low += 1
        self.entered_low_once[i] = True
        self._low_count += 1
        self._trace.append((float(now), self._low_count))

    def to_active(self, i: int, now: float) -> None:
        if self.state[i] == ACTIVE:
            return
        dt = self._accrue(i, now)
        self.low_episodes.append(dt)
        self.state[i] = ACTIVE
        self.n_low_to_active += 1
        self._low_count -= 1
        self._trace.append((float(now), self._low_count))

    def close(self, end_time: float = None) -> None:
        """Close every open residency at the horizon."""
        t = self.horizon if end_time is None else float(end_time)
        for i in range(self.n):
            was_low = self.state[i] == LOW_POWER
            dt = self._accrue(i, t)
            if was_low:
                self.low_episodes.append(dt)
        self._trace.append((t, self._low_count))

    # ---------------- aggregates ----------------
    @property
    def active_miner_seconds(self) -> float:
        return float(sum(self.t_active))

    @property
    def low_power_miner_seconds(self) -> float:
        return float(sum(self.t_low))

    @property
    def total_miner_seconds(self) -> float:
        return self.active_miner_seconds + self.low_power_miner_seconds

    @property
    def low_power_fraction(self) -> float:
        """F_low = sum_i t_low,i / (N * T)."""
        denom = self.n * self.horizon
        return self.low_power_miner_seconds / denom if denom else 0.0

    def conservation_error(self) -> float:
        """max_i |t_active,i + t_low,i - T| (seconds)."""
        return max(
            (abs(self.t_active[i] + self.t_low[i] - self.horizon) for i in range(self.n)),
            default=0.0,
        )

    def mean_simultaneous_low(self) -> float:
        """Time-weighted mean number of miners simultaneously in LOW_POWER."""
        if len(self._trace) < 2:
            return 0.0
        area, prev_t, prev_c = 0.0, self._trace[0][0], self._trace[0][1]
        for t, c in self._trace[1:]:
            area += prev_c * max(0.0, t - prev_t)
            prev_t, prev_c = t, c
        return area / self.horizon if self.horizon else 0.0

    def max_simultaneous_low(self) -> int:
        return max((c for _, c in self._trace), default=0)

    def summary(self) -> Dict[str, float]:
        eps = self.low_episodes
        eps_sorted = sorted(eps)
        n_ep = len(eps_sorted)
        median = 0.0
        if n_ep:
            mid = n_ep // 2
            median = (eps_sorted[mid] if n_ep % 2
                      else 0.5 * (eps_sorted[mid - 1] + eps_sorted[mid]))
        return {
            "active_miner_seconds": self.active_miner_seconds,
            "low_power_miner_seconds": self.low_power_miner_seconds,
            "low_power_fraction": self.low_power_fraction,
            "active_to_low_transitions": self.n_active_to_low,
            "low_to_active_transitions": self.n_low_to_active,
            "low_episodes": n_ep,
            "mean_low_duration_s": (sum(eps) / n_ep) if n_ep else 0.0,
            "median_low_duration_s": median,
            "max_low_duration_s": max(eps) if eps else 0.0,
            "miners_entering_low": sum(1 for f in self.entered_low_once if f),
            "fraction_miners_entering_low": (
                sum(1 for f in self.entered_low_once if f) / self.n if self.n else 0.0
            ),
            "mean_simultaneous_low_miners": self.mean_simultaneous_low(),
            "max_simultaneous_low_miners": self.max_simultaneous_low(),
            "state_time_conservation_error_s": self.conservation_error(),
        }
