"""
Consensus-aware energy and carbon models for BlockSim.

This module implements four standalone, well-documented models that make the
energy drivers of each consensus family explicit, as requested by the reviewers:

    * PowEconomicEnergyModel    -- economically driven Proof-of-Work energy
    * PosValidatorEnergyModel   -- validator-count driven Proof-of-Stake energy
    * CommunicationEnergyModel  -- message-level communication energy
    * CarbonFootprintModel      -- C = E * gamma (configurable grid intensity)

The models are deliberately decoupled from the BlockSim event loop so they can
be (a) unit tested in isolation, (b) driven by the experiment scripts, and
(c) embedded into the discrete-event simulation as accounting hooks.

Unit conventions
----------------
* Energy is reported in kWh unless a name ends in `_j` (Joules).
* Power is in Watts (W).
* Carbon intensity (gamma) is in kgCO2e/kWh.
* Prices are in fiat (USD by default); the model is currency agnostic.

1 kWh = 3.6e6 J.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Dict, List

J_PER_KWH = 3_600_000.0
HASHES_PER_DIFFICULTY = 2 ** 32  # Bitcoin-style: expected hashes/block = difficulty * 2^32


# ---------------------------------------------------------------------------
# C1. Proof-of-Work Economic Energy Model
# ---------------------------------------------------------------------------
@dataclass
class PowEconomicEnergyModel:
    """Economically driven PoW energy model.

    The central reviewer concern is that PoW energy is *not* simply a function
    of the number of miners: it is bounded by what rational miners are willing
    to spend on electricity, which is driven by the fiat value of the block
    reward.  This class makes the expected reward and the coin price explicit
    inputs.

    Economic chain of reasoning (per block, time index t):

        R_t      = (B_t + F_t) * P_t                  (expected reward, fiat)
        E_budget = kappa * R_t / C_elec               (economic energy, kWh)

    Optionally, if hardware-level parameters are supplied, a *technical* upper
    bound is also computed:

        H_block      = difficulty * 2^32  (or expected_hashes_per_block)
        E_technical  = H_block * j_per_hash / 3.6e6   (kWh)

    The network per-block energy is then::

        E_PoW = min(E_technical, E_budget)   if both are modeled
              = E_budget                     otherwise (economic upper bound)

    Miner i receives a share s_i of this energy::

        E_i = s_i * E_PoW
    """

    # --- economic inputs (always required) ---
    block_subsidy: float                 # B_t : native coin per block
    avg_tx_fees: float                   # F_t : native coin per block
    coin_price: float                    # P_t : fiat per coin
    electricity_price_per_kwh: float     # C_elec : fiat / kWh
    electricity_spend_ratio_kappa: float = 1.0   # kappa in [0, 1]

    # --- optional technical / hardware inputs ---
    mining_efficiency_j_per_hash: Optional[float] = None  # J / hash
    mining_efficiency_j_per_th: Optional[float] = None    # J / TH (1 TH = 1e12 hash)
    difficulty: Optional[float] = None                    # network difficulty
    expected_hashes_per_block: Optional[float] = None     # overrides difficulty*2^32
    network_hashrate_hps: Optional[float] = None          # H/s (for retargeting)

    # --- difficulty retargeting (optional scenario) ---
    enable_difficulty_retargeting: bool = False
    target_block_interval_s: float = 600.0

    def __post_init__(self):
        if not (0.0 <= self.electricity_spend_ratio_kappa <= 1.0):
            raise ValueError("electricity_spend_ratio_kappa (kappa) must be in [0, 1].")
        if self.electricity_price_per_kwh <= 0:
            raise ValueError("electricity_price_per_kwh must be > 0.")

    # ---- economic side ----
    def expected_block_reward_fiat(self) -> float:
        """R_t = (B_t + F_t) * P_t."""
        return (self.block_subsidy + self.avg_tx_fees) * self.coin_price

    def energy_budget_per_block_kwh(self) -> float:
        """E_budget = kappa * R_t / C_elec  (economic upper bound, kWh/block)."""
        return (self.electricity_spend_ratio_kappa
                * self.expected_block_reward_fiat()
                / self.electricity_price_per_kwh)

    # ---- technical side (optional) ----
    def _j_per_hash(self) -> Optional[float]:
        if self.mining_efficiency_j_per_hash is not None:
            return self.mining_efficiency_j_per_hash
        if self.mining_efficiency_j_per_th is not None:
            return self.mining_efficiency_j_per_th / 1e12
        return None

    def expected_hashes_block(self) -> Optional[float]:
        if self.expected_hashes_per_block is not None:
            return self.expected_hashes_per_block
        if self.difficulty is not None:
            return self.difficulty * HASHES_PER_DIFFICULTY
        if self.network_hashrate_hps is not None:
            return self.network_hashrate_hps * self.target_block_interval_s
        return None

    def technical_energy_per_block_kwh(self) -> Optional[float]:
        """E_technical = H_block * j_per_hash / 3.6e6  (kWh/block) or None."""
        jph = self._j_per_hash()
        hpb = self.expected_hashes_block()
        if jph is None or hpb is None:
            return None
        return hpb * jph / J_PER_KWH

    def retarget_difficulty(self, observed_hashrate_hps: float) -> None:
        """Adjust difficulty so expected block time matches the target interval.

        difficulty_new = observed_hashrate * target_interval / 2^32
        """
        if not self.enable_difficulty_retargeting:
            return
        self.difficulty = (observed_hashrate_hps * self.target_block_interval_s
                           / HASHES_PER_DIFFICULTY)

    # ---- combined network / miner energy ----
    def network_energy_per_block_kwh(self) -> float:
        """E_PoW per block = min(technical, budget) if both modeled, else budget."""
        budget = self.energy_budget_per_block_kwh()
        technical = self.technical_energy_per_block_kwh()
        if technical is None:
            return budget
        return min(technical, budget)

    def network_energy_kwh(self, num_blocks: float) -> float:
        return self.network_energy_per_block_kwh() * float(num_blocks)

    def miner_energy_kwh(self, hashpower_share: float, num_blocks: float) -> float:
        """E_i = s_i * E_PoW."""
        return hashpower_share * self.network_energy_kwh(num_blocks)

    def allocate_to_miners(self, shares: Sequence[float], num_blocks: float) -> List[float]:
        total = self.network_energy_kwh(num_blocks)
        return [s * total for s in shares]


# ---------------------------------------------------------------------------
# C2. Proof-of-Stake Validator Energy Model
# ---------------------------------------------------------------------------
@dataclass
class PosValidatorEnergyModel:
    """Validator-count driven PoS energy model.

    Unlike PoW, PoS energy does not depend on coin price: it is essentially the
    aggregate idle/active power of the validator machines kept online.  Following
    Platt et al. (2021):

        E_PoS = sum_v ( P_v * T * u_v / 1000 ) + E_comm        (kWh)

    where P_v is per-validator power (W), T is the horizon in hours, u_v is the
    validator uptime/utilization in [0, 1], and E_comm is communication energy.
    """

    validator_count: int
    validator_power_watts: float                 # P_v (homogeneous default)
    simulation_time_hours: float                 # T
    uptime_ratio: float = 1.0                     # u_v in [0, 1]
    # Optional per-validator heterogeneity (overrides the homogeneous values)
    per_validator_power_watts: Optional[Sequence[float]] = None
    per_validator_uptime: Optional[Sequence[float]] = None
    communication_energy_kwh: float = 0.0         # E_comm

    def __post_init__(self):
        if not (0.0 <= self.uptime_ratio <= 1.0):
            raise ValueError("uptime_ratio must be in [0, 1].")
        if self.validator_count < 0:
            raise ValueError("validator_count must be >= 0.")

    def consensus_energy_kwh(self) -> float:
        """Validator hardware energy only (excludes communication)."""
        if self.per_validator_power_watts is not None:
            powers = list(self.per_validator_power_watts)
            ups = (list(self.per_validator_uptime)
                   if self.per_validator_uptime is not None
                   else [self.uptime_ratio] * len(powers))
            return sum(p * self.simulation_time_hours * u / 1000.0
                       for p, u in zip(powers, ups))
        return (self.validator_count * self.validator_power_watts
                * self.simulation_time_hours * self.uptime_ratio / 1000.0)

    def total_energy_kwh(self) -> float:
        """E_PoS = consensus energy + communication energy."""
        return self.consensus_energy_kwh() + self.communication_energy_kwh

    def energy_per_validator_kwh(self) -> float:
        if self.validator_count == 0:
            return 0.0
        return self.consensus_energy_kwh() / self.validator_count


# ---------------------------------------------------------------------------
# C3. Communication Energy Model
# ---------------------------------------------------------------------------
@dataclass
class CommunicationEnergyModel:
    """Message-level communication energy with explicit counters.

    Energy per message can optionally scale with message size (per-byte term),
    following packet-level radio/network energy models (Feeney & Nilsson 2001).

        E_comm = sum_msg ( e_fixed + e_per_byte * size_bytes )      (Joules)

    Counters are exposed so experiments can report *how many* block/transaction
    messages were transmitted and received, separately from the energy total.
    """

    tx_energy_per_message_j: float = 0.0          # fixed TX cost per message (J)
    rx_energy_per_message_j: float = 0.0          # fixed RX cost per message (J)
    tx_energy_per_byte_j: float = 0.0             # optional per-byte TX cost (J/byte)
    rx_energy_per_byte_j: float = 0.0             # optional per-byte RX cost (J/byte)

    # counters
    block_messages_tx: int = 0
    block_messages_rx: int = 0
    tx_messages_tx: int = 0
    tx_messages_rx: int = 0
    bytes_tx: float = 0.0
    bytes_rx: float = 0.0
    energy_j: float = 0.0

    def reset(self) -> None:
        self.block_messages_tx = self.block_messages_rx = 0
        self.tx_messages_tx = self.tx_messages_rx = 0
        self.bytes_tx = self.bytes_rx = 0.0
        self.energy_j = 0.0

    def record_transmit(self, kind: str = "block", size_bytes: float = 0.0, count: int = 1) -> None:
        if kind == "block":
            self.block_messages_tx += count
        else:
            self.tx_messages_tx += count
        self.bytes_tx += size_bytes * count
        self.energy_j += count * (self.tx_energy_per_message_j
                                  + self.tx_energy_per_byte_j * size_bytes)

    def record_receive(self, kind: str = "block", size_bytes: float = 0.0, count: int = 1) -> None:
        if kind == "block":
            self.block_messages_rx += count
        else:
            self.tx_messages_rx += count
        self.bytes_rx += size_bytes * count
        self.energy_j += count * (self.rx_energy_per_message_j
                                  + self.rx_energy_per_byte_j * size_bytes)

    @property
    def total_messages(self) -> int:
        return (self.block_messages_tx + self.block_messages_rx
                + self.tx_messages_tx + self.tx_messages_rx)

    def total_energy_kwh(self) -> float:
        return self.energy_j / J_PER_KWH

    # --- analytical helper for gossip broadcast over a P2P overlay ---
    def account_broadcast(self, num_messages: int, num_nodes: int, peer_degree: int,
                          kind: str = "block", size_bytes: float = 0.0) -> None:
        """Account a flooding/gossip broadcast.

        In a gossip overlay, each of `num_messages` items is forwarded by every
        node to its `peer_degree` neighbours; each forward is one TX and one RX.
        Total directed messages ~= num_messages * num_nodes * peer_degree.
        """
        directed = int(num_messages) * int(num_nodes) * int(peer_degree)
        self.record_transmit(kind=kind, size_bytes=size_bytes, count=directed)
        self.record_receive(kind=kind, size_bytes=size_bytes, count=directed)


# ---------------------------------------------------------------------------
# C4. Carbon Footprint Model
# ---------------------------------------------------------------------------
# Representative grid emission factors (kgCO2e/kWh).
#   low     : low-carbon grid (hydro / nuclear dominated, e.g. Sweden/Norway)
#   average : global average grid intensity
#   high    : high-carbon grid (coal dominated, e.g. parts of CN/KZ/PL)
# Values are scenario anchors, consistent with IEA/IPCC ranges.
GAMMA_SCENARIOS: Dict[str, float] = {
    "low": 0.050,
    "average": 0.475,
    "high": 0.820,
}


@dataclass
class CarbonFootprintModel:
    """Carbon model: C = E * gamma.

    gamma can be given directly or selected from a named scenario
    ('low', 'average', 'high').
    """

    emission_factor_gamma: Optional[float] = None
    scenario: Optional[str] = None

    def __post_init__(self):
        if self.emission_factor_gamma is None:
            name = self.scenario or "average"
            if name not in GAMMA_SCENARIOS:
                raise ValueError(f"Unknown gamma scenario '{name}'. "
                                 f"Choose from {list(GAMMA_SCENARIOS)} or pass a number.")
            self.emission_factor_gamma = GAMMA_SCENARIOS[name]
            self.scenario = name

    def carbon_kg(self, energy_kwh: float) -> float:
        """C = E * gamma."""
        return float(energy_kwh) * self.emission_factor_gamma

    def carbon_per_block_kg(self, energy_kwh: float, num_blocks: float) -> float:
        return self.carbon_kg(energy_kwh) / num_blocks if num_blocks else 0.0

    def carbon_per_tx_kg(self, energy_kwh: float, num_tx: float) -> float:
        return self.carbon_kg(energy_kwh) / num_tx if num_tx else 0.0

    @classmethod
    def all_scenarios(cls) -> Dict[str, "CarbonFootprintModel"]:
        return {name: cls(emission_factor_gamma=g) for name, g in GAMMA_SCENARIOS.items()}
