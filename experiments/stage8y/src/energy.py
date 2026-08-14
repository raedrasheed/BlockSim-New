"""Stage 8Y — wall-clock, state-resident energy accounting.

    E_i = P_active,i * t_active,i
        + P_low,i    * t_low,i
        + P_standby,i* t_standby,i
        + P_wake,i   * t_wake,i

    E_network = sum_i E_i

with the frozen modelling choices

    P_low,i     = alpha * P_active,i          (model assumption, not a vendor mode)
    P_standby,i = alpha * P_active,i          (no vendor data distinguishes the two;
                                               residence is still tracked separately)
    P_wake,i    = WAKE_POWER_RATIO * P_active,i, ratio = 1.0 (conservative)

Energy is never inferred from hash counts. It is always
state x nominal device power x wall-clock residence.

alpha does not affect any dynamics, so a physical trajectory is simulated once and
re-priced for every alpha. ``t_wake`` DOES affect dynamics and is therefore a
simulated parameter, not an accounting one.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional

J_PER_KWH = 3.6e6


@dataclass(frozen=True)
class EnergyResult:
    alpha: float
    active_J: float
    waking_J: float
    low_J: float
    standby_J: float

    @property
    def total_J(self) -> float:
        return self.active_J + self.waking_J + self.low_J + self.standby_J

    @property
    def total_kWh(self) -> float:
        return self.total_J / J_PER_KWH

    @property
    def parked_J(self) -> float:
        return self.low_J + self.standby_J

    def per_block_kWh(self, blocks: int) -> Optional[float]:
        return self.total_kWh / blocks if blocks else None

    def per_round_kWh(self, rounds: int) -> Optional[float]:
        return self.total_kWh / rounds if rounds else None


def account(pw_active_Ws: float, pw_waking_Ws: float, pw_low_Ws: float,
            pw_standby_Ws: float, alpha: float,
            wake_power_ratio: float = 1.0) -> EnergyResult:
    """Price one recorded trajectory.

    The ``pw_*`` inputs are power-weighted residencies ``sum_i P_active,i * t_{i,s}``
    in watt-seconds, i.e. exactly what the ledger accumulates.
    """
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha must lie in [0, 1]")
    return EnergyResult(alpha=float(alpha),
                        active_J=float(pw_active_Ws),
                        waking_J=wake_power_ratio * float(pw_waking_Ws),
                        low_J=alpha * float(pw_low_Ws),
                        standby_J=alpha * float(pw_standby_Ws))


def account_all(pw_active_Ws: float, pw_waking_Ws: float, pw_low_Ws: float,
                pw_standby_Ws: float, alpha_cases: Dict[str, float],
                wake_power_ratio: float = 1.0) -> Dict[str, EnergyResult]:
    return {label: account(pw_active_Ws, pw_waking_Ws, pw_low_Ws, pw_standby_Ws,
                           a, wake_power_ratio)
            for label, a in alpha_cases.items()}


def saving_fraction(e_pocol_kwh: float, e_pow_kwh: float) -> Optional[float]:
    """Saving = 1 - E_PoCol / E_PoW; None (NA) when the baseline is zero."""
    if not e_pow_kwh:
        return None
    return 1.0 - (e_pocol_kwh / e_pow_kwh)


def full_active_energy_J(total_power_w: float, horizon_s: float) -> float:
    """Reference: every installed miner ACTIVE for the whole horizon, P_N * T."""
    return float(total_power_w) * float(horizon_s)
