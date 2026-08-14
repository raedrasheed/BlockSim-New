"""Stage 8Z — six-state workload/power residency ledger.

States (brief section 23)
-------------------------
ACTIVE_OWN            hashing candidates from the miner's originally assigned slot
ACTIVE_REASSIGNED     hashing candidates received through dynamic reassignment
LOW_POWER_POST_RANGE  finished all available work in this epoch
STANDBY_RESERVE       not selected by the policy for this epoch
WAKING                STANDBY/LOW_POWER -> ACTIVE transition; no hashing, full power
TEMPLATE_WAIT         waiting for the refreshed common template

Hashing occurs only in the two ACTIVE_* states. Full active power is drawn in the two
ACTIVE_* states and in WAKING (the conservative choice). The remaining states are
priced at ``alpha * P_active``.

    sum_s t_{i,s} = T   for every miner, enforced and asserted.

The ledger also maintains the wall-clock integrals and the hash-floor deficit, which
must be measured continuously rather than sampled.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

ACTIVE_OWN = "ACTIVE_OWN"
ACTIVE_REASSIGNED = "ACTIVE_REASSIGNED"
LOW_POWER_POST_RANGE = "LOW_POWER_POST_RANGE"
STANDBY_RESERVE = "STANDBY_RESERVE"
WAKING = "WAKING"
TEMPLATE_WAIT = "TEMPLATE_WAIT"

STATES = (ACTIVE_OWN, ACTIVE_REASSIGNED, LOW_POWER_POST_RANGE, STANDBY_RESERVE,
          WAKING, TEMPLATE_WAIT)
HASHING_STATES = (ACTIVE_OWN, ACTIVE_REASSIGNED)
FULL_POWER_STATES = (ACTIVE_OWN, ACTIVE_REASSIGNED, WAKING)
PARKED_STATES = (LOW_POWER_POST_RANGE, STANDBY_RESERVE, TEMPLATE_WAIT)


class WorkloadLedger:
    def __init__(self, hashrates: Sequence[float], powers: Sequence[float],
                 horizon_s: float, initial: Sequence[str],
                 hash_floor: float = 0.0) -> None:
        self.n = len(hashrates)
        self.h = list(hashrates)
        self.p = list(powers)
        self.horizon = float(horizon_s)
        self.h_total = sum(self.h)
        self.p_total = sum(self.p)
        self.floor_abs = float(hash_floor) * self.h_total

        self.state: List[str] = list(initial)
        self.since: List[float] = [0.0] * self.n
        self.t: List[Dict[str, float]] = [{s: 0.0 for s in STATES} for _ in range(self.n)]
        self.transitions: Dict[str, int] = {}
        self.episodes: Dict[str, List[float]] = {s: [] for s in STATES}
        self.entered: Dict[str, List[bool]] = {s: [False] * self.n for s in STATES}
        for i, s in enumerate(initial):
            self.entered[s][i] = True
        self.wake_events = 0

        self._h_now = sum(self.h[i] for i in range(self.n)
                          if self.state[i] in HASHING_STATES)
        self._p_full = sum(self.p[i] for i in range(self.n)
                           if self.state[i] in FULL_POWER_STATES)
        self._p_parked = self.p_total - self._p_full
        self._last = 0.0

        self.integral_H = 0.0
        self.integral_P_full = 0.0
        self.integral_P_parked_nominal = 0.0
        self.hash_floor_deficit = 0.0
        self.time_below_95 = 0.0
        self.time_below_90 = 0.0
        self.time_below_80 = 0.0
        self.time_below_floor = 0.0
        self.min_h_fraction = self._h_now / self.h_total if self.h_total else 0.0
        self.trace: List[tuple] = [(0.0, self.min_h_fraction,
                                    self._p_full / self.p_total if self.p_total else 0.0)]

    # ---------------- internals ----------------
    def _advance(self, now: float) -> None:
        dt = float(now) - self._last
        if dt <= 0:
            self._last = float(now)
            return
        self.integral_H += self._h_now * dt
        self.integral_P_full += self._p_full * dt
        self.integral_P_parked_nominal += self._p_parked * dt
        frac = self._h_now / self.h_total if self.h_total else 0.0
        if self._h_now < self.floor_abs:
            self.hash_floor_deficit += (self.floor_abs - self._h_now) * dt
            self.time_below_floor += dt
        if frac < 0.95:
            self.time_below_95 += dt
        if frac < 0.90:
            self.time_below_90 += dt
        if frac < 0.80:
            self.time_below_80 += dt
        self._last = float(now)

    def transition(self, i: int, to_state: str, now: float) -> None:
        if to_state not in STATES:
            raise ValueError(f"unknown state {to_state!r}")
        old = self.state[i]
        if old == to_state:
            return
        self._advance(now)
        dt = max(0.0, float(now) - self.since[i])
        self.t[i][old] += dt
        self.episodes[old].append(dt)
        self.since[i] = float(now)
        key = f"{old}->{to_state}"
        self.transitions[key] = self.transitions.get(key, 0) + 1
        if to_state == WAKING:
            self.wake_events += 1
        if old in HASHING_STATES:
            self._h_now -= self.h[i]
        if old in FULL_POWER_STATES:
            self._p_full -= self.p[i]
            self._p_parked += self.p[i]
        self.state[i] = to_state
        self.entered[to_state][i] = True
        if to_state in HASHING_STATES:
            self._h_now += self.h[i]
        if to_state in FULL_POWER_STATES:
            self._p_full += self.p[i]
            self._p_parked -= self.p[i]
        frac = self._h_now / self.h_total if self.h_total else 0.0
        self.min_h_fraction = min(self.min_h_fraction, frac)
        self.trace.append((float(now), frac,
                           self._p_full / self.p_total if self.p_total else 0.0))

    def close(self, end_time: float = None) -> None:
        t = self.horizon if end_time is None else float(end_time)
        self._advance(t)
        for i in range(self.n):
            dt = max(0.0, t - self.since[i])
            self.t[i][self.state[i]] += dt
            self.episodes[self.state[i]].append(dt)
            self.since[i] = t
        self.trace.append((t, self._h_now / self.h_total if self.h_total else 0.0,
                           self._p_full / self.p_total if self.p_total else 0.0))

    # ---------------- aggregates ----------------
    def miner_seconds(self, state: str) -> float:
        return sum(self.t[i][state] for i in range(self.n))

    def power_weighted(self, states: Sequence[str]) -> float:
        return sum(self.p[i] * sum(self.t[i][s] for s in states)
                   for i in range(self.n))

    def conservation_error(self) -> float:
        return max((abs(sum(self.t[i].values()) - self.horizon)
                    for i in range(self.n)), default=0.0)

    def min_residence(self) -> float:
        return min((v for row in self.t for v in row.values()), default=0.0)

    def summary(self) -> Dict[str, float]:
        T, n = self.horizon, self.n
        denom = n * T if n and T else 1.0
        out = {
            "pw_full_power_Ws": self.power_weighted(FULL_POWER_STATES),
            "pw_parked_Ws": self.power_weighted(PARKED_STATES),
            "pw_active_own_Ws": self.power_weighted([ACTIVE_OWN]),
            "pw_active_reassigned_Ws": self.power_weighted([ACTIVE_REASSIGNED]),
            "pw_waking_Ws": self.power_weighted([WAKING]),
            "pw_low_post_range_Ws": self.power_weighted([LOW_POWER_POST_RANGE]),
            "pw_standby_Ws": self.power_weighted([STANDBY_RESERVE]),
            "pw_template_wait_Ws": self.power_weighted([TEMPLATE_WAIT]),
            "integral_H_active_hashes": self.integral_H,
            "integral_P_full_Ws": self.integral_P_full,
            "mean_h_active_fraction": (self.integral_H / (self.h_total * T)
                                       if self.h_total and T else 0.0),
            "mean_p_drawn_fraction": (self.integral_P_full / (self.p_total * T)
                                      if self.p_total and T else 0.0),
            "min_h_active_fraction": self.min_h_fraction,
            "hash_floor_deficit_hash_s": self.hash_floor_deficit,
            "hash_floor_deficit_normalised": (
                self.hash_floor_deficit / (self.floor_abs * T)
                if self.floor_abs and T else 0.0),
            "time_below_floor_s": self.time_below_floor,
            "time_below_95_s": self.time_below_95,
            "time_below_90_s": self.time_below_90,
            "time_below_80_s": self.time_below_80,
            "wake_events": self.wake_events,
            "state_time_conservation_error_s": self.conservation_error(),
            "min_state_residence_s": self.min_residence(),
        }
        for s in STATES:
            out[f"t_{s}_miner_s"] = self.miner_seconds(s)
            out[f"F_{s}"] = self.miner_seconds(s) / denom
            out[f"miners_entering_{s}"] = sum(1 for f in self.entered[s] if f)
        for k, v in self.transitions.items():
            out[f"trans_{k}"] = v
        return out
