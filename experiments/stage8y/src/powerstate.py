"""Stage 8Y — four-state power residency ledger for heterogeneous miners.

States
------
ACTIVE      hashing at the device's nominal h_i and drawing P_active,i
LOW_POWER   the miner completed its assigned useful range and has no further
            legitimate work in this epoch
STANDBY     the miner is a reserve that this policy has not activated
WAKING      a reserve is transitioning STANDBY/LOW_POWER -> ACTIVE. It performs
            NO hashing and (conservatively) draws full active power.

Enforced invariants (asserted by the Pilot and the test suite):
    t_active + t_low + t_standby + t_waking = T   for every miner
    no residence time is ever negative
    hashing happens only in ACTIVE (the engine schedules work only for ACTIVE miners)

The ledger also maintains the wall-clock integrals the brief requires:
    integral_H_active   = int H_active(t) dt      (hash-seconds; ACTIVE only)
    integral_P_active   = int P_active(t) dt      (watt-seconds; ACTIVE only)
    integral_P_waking   = int P_waking(t) dt      (watt-seconds; WAKING only)
    integral_P_parked   = int P_nominal_parked(t) dt  (watt-seconds at *nominal*
                          power for LOW_POWER + STANDBY; multiplied by alpha later)
"""

from __future__ import annotations

from typing import Dict, List, Sequence

ACTIVE = "ACTIVE"
LOW_POWER = "LOW_POWER"
STANDBY = "STANDBY"
WAKING = "WAKING"
STATES = (ACTIVE, LOW_POWER, STANDBY, WAKING)


class PowerStateLedger:
    def __init__(self, hashrates: Sequence[float], powers: Sequence[float],
                 horizon_s: float, initial: Sequence[str] = None) -> None:
        self.n = len(hashrates)
        self.h = list(hashrates)
        self.p = list(powers)
        self.horizon = float(horizon_s)
        self.h_total = sum(self.h)
        self.p_total = sum(self.p)

        self.state: List[str] = list(initial) if initial else [ACTIVE] * self.n
        self.since: List[float] = [0.0] * self.n
        self.t: List[Dict[str, float]] = [{s: 0.0 for s in STATES} for _ in range(self.n)]

        self.transitions: Dict[str, int] = {}
        self.low_episodes: List[float] = []
        self.standby_episodes: List[float] = []
        self.wake_events = 0
        self.entered_low = [False] * self.n
        self.entered_standby = [False] * self.n

        # running aggregates for the wall-clock integrals
        self._h_active_now = sum(self.h[i] for i in range(self.n)
                                 if self.state[i] == ACTIVE)
        self._p_active_now = sum(self.p[i] for i in range(self.n)
                                 if self.state[i] == ACTIVE)
        self._p_waking_now = 0.0
        self._p_parked_now = sum(self.p[i] for i in range(self.n)
                                 if self.state[i] in (LOW_POWER, STANDBY))
        self._last_t = 0.0
        self.integral_H_active = 0.0
        self.integral_P_active = 0.0
        self.integral_P_waking = 0.0
        self.integral_P_parked = 0.0
        self.min_h_active_fraction = (self._h_active_now / self.h_total
                                      if self.h_total else 0.0)
        #: piecewise-constant trace of (t, H_active/H_N, P_drawn/P_N) for figures
        self.trace: List[tuple] = [(0.0, self.min_h_active_fraction,
                                    self._p_active_now / self.p_total
                                    if self.p_total else 0.0)]

    # ---------------- internals ----------------
    def _advance(self, now: float) -> None:
        dt = float(now) - self._last_t
        if dt <= 0:
            self._last_t = float(now)
            return
        self.integral_H_active += self._h_active_now * dt
        self.integral_P_active += self._p_active_now * dt
        self.integral_P_waking += self._p_waking_now * dt
        self.integral_P_parked += self._p_parked_now * dt
        self._last_t = float(now)

    def _leave(self, i: int, now: float) -> None:
        s = self.state[i]
        dt = max(0.0, float(now) - self.since[i])
        self.t[i][s] += dt
        self.since[i] = float(now)
        if s == ACTIVE:
            self._h_active_now -= self.h[i]
            self._p_active_now -= self.p[i]
        elif s == WAKING:
            self._p_waking_now -= self.p[i]
        else:
            self._p_parked_now -= self.p[i]
        if s == LOW_POWER:
            self.low_episodes.append(dt)
        elif s == STANDBY:
            self.standby_episodes.append(dt)

    def _enter(self, i: int, s: str) -> None:
        self.state[i] = s
        if s == ACTIVE:
            self._h_active_now += self.h[i]
            self._p_active_now += self.p[i]
        elif s == WAKING:
            self._p_waking_now += self.p[i]
        else:
            self._p_parked_now += self.p[i]
        if s == LOW_POWER:
            self.entered_low[i] = True
        elif s == STANDBY:
            self.entered_standby[i] = True

    # ---------------- public API ----------------
    def transition(self, i: int, to_state: str, now: float) -> None:
        if to_state not in STATES:
            raise ValueError(f"unknown state {to_state!r}")
        if self.state[i] == to_state:
            return
        self._advance(now)
        key = f"{self.state[i]}->{to_state}"
        self.transitions[key] = self.transitions.get(key, 0) + 1
        if to_state == WAKING:
            self.wake_events += 1
        self._leave(i, now)
        self._enter(i, to_state)
        frac_h = self._h_active_now / self.h_total if self.h_total else 0.0
        frac_p = ((self._p_active_now + self._p_waking_now) / self.p_total
                  if self.p_total else 0.0)
        self.min_h_active_fraction = min(self.min_h_active_fraction, frac_h)
        self.trace.append((float(now), frac_h, frac_p))

    def close(self, end_time: float = None) -> None:
        t = self.horizon if end_time is None else float(end_time)
        self._advance(t)
        for i in range(self.n):
            self._leave(i, t)
            # keep state so summaries remain meaningful; residence is now closed
            if self.state[i] == ACTIVE:
                self._h_active_now += self.h[i]
                self._p_active_now += self.p[i]
            elif self.state[i] == WAKING:
                self._p_waking_now += self.p[i]
            else:
                self._p_parked_now += self.p[i]
        self.trace.append((t, self._h_active_now / self.h_total if self.h_total else 0.0,
                           (self._p_active_now + self._p_waking_now) / self.p_total
                           if self.p_total else 0.0))

    # ---------------- aggregates ----------------
    def miner_seconds(self, state: str) -> float:
        return sum(self.t[i][state] for i in range(self.n))

    def power_weighted(self, state: str) -> float:
        """sum_i P_i * t_{i,state}  (watt-seconds at nominal active power)."""
        return sum(self.p[i] * self.t[i][state] for i in range(self.n))

    def conservation_error(self) -> float:
        return max((abs(sum(self.t[i].values()) - self.horizon) for i in range(self.n)),
                   default=0.0)

    def min_residence(self) -> float:
        return min((v for row in self.t for v in row.values()), default=0.0)

    def summary(self) -> Dict[str, float]:
        n, T = self.n, self.horizon
        denom = n * T if n and T else 1.0
        eps_low = self.low_episodes
        eps_sb = self.standby_episodes
        parked_pw = self.power_weighted(LOW_POWER) + self.power_weighted(STANDBY)
        out = {
            "t_active_miner_s": self.miner_seconds(ACTIVE),
            "t_low_miner_s": self.miner_seconds(LOW_POWER),
            "t_standby_miner_s": self.miner_seconds(STANDBY),
            "t_waking_miner_s": self.miner_seconds(WAKING),
            "F_active": self.miner_seconds(ACTIVE) / denom,
            "F_low": self.miner_seconds(LOW_POWER) / denom,
            "F_standby": self.miner_seconds(STANDBY) / denom,
            "F_waking": self.miner_seconds(WAKING) / denom,
            "F_parked_minertime": (self.miner_seconds(LOW_POWER)
                                   + self.miner_seconds(STANDBY)) / denom,
            "F_parked_power_weighted": parked_pw / (self.p_total * T) if self.p_total else 0.0,
            "pw_active_Ws": self.power_weighted(ACTIVE),
            "pw_low_Ws": self.power_weighted(LOW_POWER),
            "pw_standby_Ws": self.power_weighted(STANDBY),
            "pw_waking_Ws": self.power_weighted(WAKING),
            "integral_H_active_hashes": self.integral_H_active,
            "integral_P_active_Ws": self.integral_P_active,
            "integral_P_waking_Ws": self.integral_P_waking,
            "integral_P_parked_nominal_Ws": self.integral_P_parked,
            "mean_h_active_fraction": (self.integral_H_active / (self.h_total * T)
                                       if self.h_total and T else 0.0),
            "mean_p_drawn_fraction": ((self.integral_P_active + self.integral_P_waking)
                                      / (self.p_total * T) if self.p_total and T else 0.0),
            "min_h_active_fraction": self.min_h_active_fraction,
            "wake_events": self.wake_events,
            "low_episodes": len(eps_low),
            "mean_low_episode_s": (sum(eps_low) / len(eps_low)) if eps_low else 0.0,
            "max_low_episode_s": max(eps_low) if eps_low else 0.0,
            "standby_episodes": len(eps_sb),
            "mean_standby_episode_s": (sum(eps_sb) / len(eps_sb)) if eps_sb else 0.0,
            "miners_entering_low": sum(1 for f in self.entered_low if f),
            "miners_entering_standby": sum(1 for f in self.entered_standby if f),
            "state_time_conservation_error_s": self.conservation_error(),
            "min_state_residence_s": self.min_residence(),
        }
        for k, v in self.transitions.items():
            out[f"trans_{k}"] = v
        return out
