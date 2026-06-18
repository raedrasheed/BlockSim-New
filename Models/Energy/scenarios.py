"""
Scenario definitions, seed-based stochastic runners, and statistics helpers
for the consensus-aware energy/carbon evaluation.

The energy models in `energy_models.py` are deterministic given their inputs.
To produce honest standard deviations and 95% confidence intervals (as required
by the reviewers) we introduce *scenario* stochasticity: across random seeds we
draw plausible variation in the quantities a designer cannot fix exactly, e.g.

    PoW  : number of blocks in the horizon (Poisson around T / block_interval),
           average transaction fees per block, small coin-price jitter,
           and the distribution of hashpower shares across miners (Dirichlet).
    PoS  : per-validator uptime jitter and message activity.
    Comm : peer-degree and per-message size jitter.

This makes the reported mean/std/CI reflect genuine scenario uncertainty rather
than fake noise added to a closed-form number.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Sequence, Optional

from Models.Energy.energy_models import (
    PowEconomicEnergyModel,
    PosValidatorEnergyModel,
    CommunicationEnergyModel,
    CarbonFootprintModel,
    GAMMA_SCENARIOS,
)

# ---------------------------------------------------------------------------
# Statistics helpers
# ---------------------------------------------------------------------------
def mean(xs: Sequence[float]) -> float:
    xs = list(xs)
    return sum(xs) / len(xs) if xs else 0.0


def std(xs: Sequence[float], ddof: int = 1) -> float:
    xs = list(xs)
    n = len(xs)
    if n <= ddof:
        return 0.0
    m = mean(xs)
    return math.sqrt(sum((x - m) ** 2 for x in xs) / (n - ddof))


# Two-sided 95% t critical values (df = n-1); fallback to 1.96 for large n.
_T95 = {1: 12.706, 2: 4.303, 3: 3.182, 4: 2.776, 5: 2.571, 6: 2.447, 7: 2.365,
        8: 2.306, 9: 2.262, 10: 2.228, 15: 2.131, 20: 2.086, 25: 2.060,
        29: 2.045, 30: 2.042, 40: 2.021, 60: 2.000, 120: 1.980}


def t_critical_95(n: int) -> float:
    df = max(n - 1, 1)
    if df in _T95:
        return _T95[df]
    keys = sorted(_T95)
    for k in keys:
        if df <= k:
            return _T95[k]
    return 1.96


def ci95_halfwidth(xs: Sequence[float]) -> float:
    """Half-width of the 95% confidence interval of the mean."""
    xs = list(xs)
    n = len(xs)
    if n < 2:
        return 0.0
    return t_critical_95(n) * std(xs) / math.sqrt(n)


def summarize(xs: Sequence[float]) -> Dict[str, float]:
    xs = list(xs)
    return {
        "mean": mean(xs),
        "std": std(xs),
        "ci95_halfwidth": ci95_halfwidth(xs),
        "n": len(xs),
        "min": min(xs) if xs else 0.0,
        "max": max(xs) if xs else 0.0,
    }


def make_seeds(count: int, base: int = 20260101) -> List[int]:
    """Deterministic, reproducible seed list: base + i for i in [0, count)."""
    return [base + i for i in range(count)]


# ---------------------------------------------------------------------------
# Named baseline scenarios (paper defaults)
# ---------------------------------------------------------------------------
# Bitcoin-like PoW baseline (historical, illustrative anchors).
POW_BITCOIN_BASE = dict(
    block_subsidy=3.125,          # BTC per block (post-2024 halving)
    avg_tx_fees=0.30,             # BTC per block (scenario value)
    coin_price=60000.0,           # USD / BTC (medium scenario)
    electricity_price_per_kwh=0.05,   # USD / kWh (industrial mining)
    electricity_spend_ratio_kappa=0.80,
    mining_efficiency_j_per_th=21.5,  # Antminer S19 XP class
    block_interval_s=600.0,
)

# Historical Ethereum-like PoW configuration (pre-Merge; clearly labelled).
POW_ETH_HISTORICAL_BASE = dict(
    block_subsidy=2.0,            # ETH per block (pre-Merge era)
    avg_tx_fees=0.10,             # ETH per block
    coin_price=2000.0,           # USD / ETH
    electricity_price_per_kwh=0.10,
    electricity_spend_ratio_kappa=0.80,
    mining_efficiency_j_per_th=200.0,  # GPU-class efficiency (much worse than ASIC)
    block_interval_s=13.0,
)

# Coin-price sensitivity anchors (USD).
POW_PRICE_LEVELS = {"low": 20000.0, "medium": 60000.0, "high": 100000.0}

# Validator hardware classes for PoS (Watts).
POS_VALIDATOR_POWER = {
    "low_power_node": 10.0,       # SBC / NUC class
    "standard_server": 100.0,     # typical staking server
    "high_power_server": 500.0,   # over-provisioned / redundant setup
}

# Ethereum PoS reference (post-Merge).
POS_ETH_BASE = dict(
    validator_power_watts=100.0,
    uptime_ratio=0.99,
    simulation_time_hours=24.0,
)


# ---------------------------------------------------------------------------
# PoW stochastic scenario runner
# ---------------------------------------------------------------------------
@dataclass
class PowScenarioResult:
    network_energy_kwh: float
    energy_per_block_kwh: float
    num_blocks: float
    expected_reward_fiat: float
    energy_budget_per_block_kwh: float
    technical_energy_per_block_kwh: Optional[float]
    miner_energy_kwh: List[float] = field(default_factory=list)


def run_pow_scenario(seed: int,
                     miner_count: int,
                     horizon_s: float = 86400.0,
                     price_jitter: float = 0.05,
                     fee_jitter: float = 0.40,
                     **base) -> PowScenarioResult:
    """One stochastic PoW scenario realization for a given seed.

    Stochastic draws (seeded):
      * num_blocks ~ Poisson(horizon / block_interval)
      * coin_price *= 1 + N(0, price_jitter)
      * avg_tx_fees *= 1 + N(0, fee_jitter)  (clamped >= 0)
      * hashpower shares ~ Dirichlet(ones(miner_count))
    """
    rng = random.Random(seed)
    cfg = dict(POW_BITCOIN_BASE)
    cfg.update(base)
    block_interval_s = cfg.pop("block_interval_s", 600.0)

    # number of blocks in horizon (Poisson around the deterministic expectation)
    lam = max(horizon_s / block_interval_s, 1e-9)
    num_blocks = _poisson(rng, lam)
    num_blocks = max(num_blocks, 1)

    # jitter price and fees
    cfg["coin_price"] = max(cfg["coin_price"] * (1.0 + rng.gauss(0, price_jitter)), 1e-6)
    cfg["avg_tx_fees"] = max(cfg["avg_tx_fees"] * (1.0 + rng.gauss(0, fee_jitter)), 0.0)

    model = PowEconomicEnergyModel(**cfg)

    # hashpower shares ~ Dirichlet(1,...,1)
    shares = _dirichlet_ones(rng, miner_count)
    miner_energy = model.allocate_to_miners(shares, num_blocks)

    return PowScenarioResult(
        network_energy_kwh=model.network_energy_kwh(num_blocks),
        energy_per_block_kwh=model.network_energy_per_block_kwh(),
        num_blocks=num_blocks,
        expected_reward_fiat=model.expected_block_reward_fiat(),
        energy_budget_per_block_kwh=model.energy_budget_per_block_kwh(),
        technical_energy_per_block_kwh=model.technical_energy_per_block_kwh(),
        miner_energy_kwh=miner_energy,
    )


# ---------------------------------------------------------------------------
# PoS stochastic scenario runner
# ---------------------------------------------------------------------------
@dataclass
class PosScenarioResult:
    total_energy_kwh: float
    consensus_energy_kwh: float
    communication_energy_kwh: float
    energy_per_validator_kwh: float
    validator_count: int


def run_pos_scenario(seed: int,
                     validator_count: int,
                     validator_power_watts: float = 100.0,
                     uptime_ratio: float = 0.99,
                     simulation_time_hours: float = 24.0,
                     uptime_jitter: float = 0.01,
                     power_jitter: float = 0.10,
                     msg_rate_per_validator_hz: float = 5.0,
                     comm_model: Optional[CommunicationEnergyModel] = None,
                     ) -> PosScenarioResult:
    """One stochastic PoS realization. Per-validator power and uptime are jittered."""
    rng = random.Random(seed)
    powers = [max(validator_power_watts * (1.0 + rng.gauss(0, power_jitter)), 0.0)
              for _ in range(validator_count)]
    uptimes = [min(max(uptime_ratio + rng.gauss(0, uptime_jitter), 0.0), 1.0)
               for _ in range(validator_count)]

    # Communication energy from validator messaging (attestations/gossip).
    comm_kwh = 0.0
    if comm_model is not None:
        cm = CommunicationEnergyModel(**asdict_comm(comm_model))
        n_msgs = int(msg_rate_per_validator_hz * simulation_time_hours * 3600.0
                     * validator_count)
        cm.record_transmit(kind="tx", count=n_msgs)
        cm.record_receive(kind="tx", count=n_msgs)
        comm_kwh = cm.total_energy_kwh()

    model = PosValidatorEnergyModel(
        validator_count=validator_count,
        validator_power_watts=validator_power_watts,
        simulation_time_hours=simulation_time_hours,
        per_validator_power_watts=powers,
        per_validator_uptime=uptimes,
        communication_energy_kwh=comm_kwh,
    )
    return PosScenarioResult(
        total_energy_kwh=model.total_energy_kwh(),
        consensus_energy_kwh=model.consensus_energy_kwh(),
        communication_energy_kwh=comm_kwh,
        energy_per_validator_kwh=model.energy_per_validator_kwh(),
        validator_count=validator_count,
    )


def asdict_comm(cm: CommunicationEnergyModel) -> Dict[str, float]:
    return dict(
        tx_energy_per_message_j=cm.tx_energy_per_message_j,
        rx_energy_per_message_j=cm.rx_energy_per_message_j,
        tx_energy_per_byte_j=cm.tx_energy_per_byte_j,
        rx_energy_per_byte_j=cm.rx_energy_per_byte_j,
    )


# ---------------------------------------------------------------------------
# Small seeded RNG primitives (avoid heavy numpy dependency in the core)
# ---------------------------------------------------------------------------
def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth's algorithm for small/medium lambda; normal approx for large lambda."""
    if lam > 30:
        # normal approximation, rounded and clamped
        return max(int(round(rng.gauss(lam, math.sqrt(lam)))), 0)
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def _dirichlet_ones(rng: random.Random, n: int) -> List[float]:
    """Sample from Dirichlet(1,...,1) via normalized Exponential(1) draws."""
    if n <= 0:
        return []
    gs = [-math.log(max(rng.random(), 1e-12)) for _ in range(n)]
    s = sum(gs)
    return [g / s for g in gs]
