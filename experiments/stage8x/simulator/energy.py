"""Stage 8X — energy accounting: state x power x time.

    E_PoW        = sum_i  P_active * t_active,i
    E_PoCol(a)   = sum_i [P_active * t_active,i + a * P_active * t_low,i]

Energy is derived exclusively from recorded state residencies. It is never inferred
from duplicate-hash percentages, block counts, or any other proxy.

alpha affects **energy accounting only**. The physical event trajectory for a given
(N, seed) is simulated once, and the four sensitivity cases are re-priced from the
same recorded residencies — hence 300 physical runs and 600 PoCol energy
observations, not 1200 simulations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict

from experiments.stage8x.config.asic import ALPHA_CASES, J_PER_KWH


@dataclass(frozen=True)
class EnergyResult:
    alpha: float
    p_low_w: float
    active_energy_j: float
    low_power_energy_j: float

    @property
    def total_energy_j(self) -> float:
        return self.active_energy_j + self.low_power_energy_j

    @property
    def total_energy_kwh(self) -> float:
        return self.total_energy_j / J_PER_KWH

    @property
    def active_energy_kwh(self) -> float:
        return self.active_energy_j / J_PER_KWH

    @property
    def low_power_energy_kwh(self) -> float:
        return self.low_power_energy_j / J_PER_KWH

    def energy_per_block_kwh(self, accepted_blocks: int):
        """kWh per accepted block; ``None`` (NA) when no block was accepted."""
        return self.total_energy_kwh / accepted_blocks if accepted_blocks else None

    def energy_per_round_kwh(self, closed_rounds: int):
        return self.total_energy_kwh / closed_rounds if closed_rounds else None


def account(
    active_miner_seconds: float,
    low_power_miner_seconds: float,
    active_power_w: float,
    alpha: float,
) -> EnergyResult:
    """E = P_act * t_active + alpha * P_act * t_low, from measured residencies."""
    if not (0.0 <= alpha <= 1.0):
        raise ValueError("alpha must lie in [0, 1]")
    p_low = alpha * active_power_w
    return EnergyResult(
        alpha=float(alpha),
        p_low_w=p_low,
        active_energy_j=active_power_w * float(active_miner_seconds),
        low_power_energy_j=p_low * float(low_power_miner_seconds),
    )


def account_all_alphas(
    active_miner_seconds: float,
    low_power_miner_seconds: float,
    active_power_w: float,
) -> Dict[str, EnergyResult]:
    """Re-price one recorded trajectory under every declared alpha case."""
    return {
        label: account(active_miner_seconds, low_power_miner_seconds,
                       active_power_w, alpha)
        for label, alpha in ALPHA_CASES.items()
    }


def energy_saving_fraction(e_pocol_kwh: float, e_pow_kwh: float):
    """EnergySaving_alpha = 1 - E_PoCol / E_PoW; ``None`` (NA) if the baseline is 0."""
    if not e_pow_kwh:
        return None
    return 1.0 - (e_pocol_kwh / e_pow_kwh)
