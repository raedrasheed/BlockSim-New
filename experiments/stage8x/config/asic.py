"""Stage 8X — fixed per-miner ASIC hardware profile.

Every simulated miner represents exactly ONE physical mining unit whose active
specifications are those of the Bitmain **Antminer S21 Pro**:

    h      = 234 TH/s      (nominal hash rate per unit)
    P_act  = 3510 W        (nominal active wall power per unit)
    eta    = 15 J/TH       (nominal efficiency)

Source note
-----------
The three active values above are the official Bitmain nominal specification for
the Antminer S21 Pro. They are internally consistent:  234 TH/s x 15 J/TH = 3510 W.

The low-power figures used in this experiment are **not** vendor-certified S21 Pro
operating modes. They are experimental sensitivity assumptions of the form
``P_low = alpha * P_active`` and are labelled as such everywhere they appear.

Stage 8X deliberately does NOT reuse the repository-wide
``InputsConfig.NetworkHashRate_Hps = 141e12`` / ``MinerEfficiency_J_per_TH = 21.5``
constants: those belong to a different experiment family with a fixed aggregate
network budget. This module never imports ``InputsConfig``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

# --- units -----------------------------------------------------------------
TH = 1.0e12                      # hashes per terahash
J_PER_KWH = 3.6e6                # 1 kWh = 3.6e6 J  (mirrors Models.Energy.energy_models)

# --- Bitmain Antminer S21 Pro nominal specification ------------------------
S21PRO_HASHRATE_THS: float = 234.0        # TH/s per unit
S21PRO_ACTIVE_POWER_W: float = 3510.0     # W per unit
S21PRO_EFFICIENCY_J_PER_TH: float = 15.0  # J/TH

#: alpha values for the low-power sensitivity model, P_low = alpha * P_active.
#: LP0 is an idealized lower-bound / best-case energy state; LP10/LP25/LP50 are
#: non-zero sensitivity assumptions. None is a manufacturer-certified mode.
ALPHA_CASES: Dict[str, float] = {
    "LP0": 0.00,
    "LP10": 0.10,
    "LP25": 0.25,
    "LP50": 0.50,
}

ALPHA_LABELS: Dict[str, str] = {
    "LP0": "idealized lower bound (0 W); not a vendor-certified mode",
    "LP10": "10% of active power; not a vendor-certified mode",
    "LP25": "25% of active power; not a vendor-certified mode",
    "LP50": "50% of active power; not a vendor-certified mode",
}


@dataclass(frozen=True)
class ASICProfile:
    """An immutable, self-consistent ASIC hardware profile."""

    name: str = "Bitmain Antminer S21 Pro"
    hashrate_ths: float = S21PRO_HASHRATE_THS
    active_power_w: float = S21PRO_ACTIVE_POWER_W
    efficiency_j_per_th: float = S21PRO_EFFICIENCY_J_PER_TH

    # ---- derived per-unit quantities ----
    @property
    def hashrate_hps(self) -> float:
        """Per-miner hash rate in hashes per second (candidate evaluations / s)."""
        return self.hashrate_ths * TH

    @property
    def implied_power_w(self) -> float:
        """P = h[TH/s] * eta[J/TH]. Must equal the nominal active power."""
        return self.hashrate_ths * self.efficiency_j_per_th

    def consistency_error_w(self) -> float:
        """|h*eta - P_active| in W; zero for a self-consistent profile."""
        return abs(self.implied_power_w - self.active_power_w)

    def low_power_w(self, alpha: float) -> float:
        """P_low = alpha * P_active (experimental sensitivity assumption)."""
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("alpha must lie in [0, 1]")
        return alpha * self.active_power_w

    # ---- network aggregates (computed, never tabulated) ----
    def aggregate_hashrate_ths(self, n_miners: int) -> float:
        """H(N) = N * h.  Grows with N: Stage 8X has no fixed network budget."""
        if n_miners < 0:
            raise ValueError("n_miners must be >= 0")
        return n_miners * self.hashrate_ths

    def aggregate_hashrate_hps(self, n_miners: int) -> float:
        return self.aggregate_hashrate_ths(n_miners) * TH

    def aggregate_active_power_w(self, n_miners: int) -> float:
        """P(N) = N * P_active."""
        if n_miners < 0:
            raise ValueError("n_miners must be >= 0")
        return n_miners * self.active_power_w

    def full_active_energy_j(self, n_miners: int, horizon_s: float) -> float:
        """Energy if every miner is ACTIVE for the whole horizon: N * P_act * T."""
        return self.aggregate_active_power_w(n_miners) * float(horizon_s)


#: The single frozen profile used by every Stage 8X run.
S21_PRO = ASICProfile()


def scaling_table(profile: ASICProfile, network_sizes: List[int]) -> List[dict]:
    """Programmatically derived hardware/network scaling table (Table A)."""
    rows = []
    for n in network_sizes:
        rows.append(
            {
                "N": n,
                "miner_hashrate_THs": profile.hashrate_ths,
                "active_power_W_per_miner": profile.active_power_w,
                "efficiency_J_per_TH": profile.efficiency_j_per_th,
                "aggregate_hashrate_THs": profile.aggregate_hashrate_ths(n),
                "aggregate_hashrate_PHs": profile.aggregate_hashrate_ths(n) / 1000.0,
                "aggregate_hashrate_Hps": profile.aggregate_hashrate_hps(n),
                "aggregate_full_power_W": profile.aggregate_active_power_w(n),
                "aggregate_full_power_kW": profile.aggregate_active_power_w(n) / 1e3,
                "aggregate_full_power_MW": profile.aggregate_active_power_w(n) / 1e6,
            }
        )
    return rows
