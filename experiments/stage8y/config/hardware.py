"""Stage 8Y — heterogeneous ASIC population model.

Loads the manufacturer-sourced hardware registry and builds concrete, deterministic
miner populations for each declared heterogeneity composition.

Key invariants (asserted in tests):
    H_N = sum_i h_i          aggregate hash rate, never held constant across N
    P_N = sum_i P_i          aggregate nominal active power
    eta_network = P_N / H_N  population-level efficiency

``(h_i, P_i)`` are the primary quantities; ``eta_i = P_i / h_i`` is derived, so
``E = P * t`` is exact by construction.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Dict, List, Tuple

TH = 1.0e12
J_PER_KWH = 3.6e6

HERE = os.path.dirname(os.path.abspath(__file__))
REGISTRY_PATH = os.path.join(HERE, "hardware_registry.json")


@dataclass(frozen=True)
class Device:
    key: str
    manufacturer: str
    model: str
    generation: str
    hashrate_ths: float
    active_power_w: float
    efficiency_stated: float
    manufacturer_certified: str
    source_url: str

    @property
    def hashrate_hps(self) -> float:
        return self.hashrate_ths * TH

    @property
    def efficiency_j_per_th(self) -> float:
        """Derived eta = P / h. This is the value used everywhere."""
        return self.active_power_w / self.hashrate_ths


def load_registry(path: str = REGISTRY_PATH) -> Dict[str, Device]:
    with open(path, encoding="utf-8") as fh:
        body = json.load(fh)
    out: Dict[str, Device] = {}
    for d in body["devices"]:
        out[d["key"]] = Device(
            key=d["key"], manufacturer=d["manufacturer"], model=d["model"],
            generation=d["generation"], hashrate_ths=d["hashrate_THs"],
            active_power_w=d["active_power_W"],
            efficiency_stated=d["efficiency_J_per_TH_stated"],
            manufacturer_certified=d["manufacturer_certified"],
            source_url=d["source_url"],
        )
    return out


def registry_raw(path: str = REGISTRY_PATH) -> Dict:
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


DEVICES = load_registry()

# --------------------------------------------------------------------------
# Declared heterogeneity compositions (fractions by MINER COUNT, not by hash)
# --------------------------------------------------------------------------
#: Each composition maps device key -> share of the miner population.
#: Shares are applied by largest-remainder so the counts sum exactly to N and the
#: allocation is deterministic for every N.
COMPOSITIONS: Dict[str, Dict[str, float]] = {
    "H0": {"S21PRO": 1.00},
    "H1": {"S21PRO": 0.75, "S19JPRO": 0.25},
    "H2": {"S21PRO": 0.50, "S19JPRO": 0.50},
    "H3": {"S21PRO": 0.25, "S19JPRO": 0.75},
    "H4": {"S21PRO": 0.20, "S19XP": 0.30, "S19JPRO": 0.50},
}

COMPOSITION_RATIONALE: Dict[str, str] = {
    "H0": "Homogeneous control: 100% S21 Pro. Reproduces the Stage 8X hardware model "
          "so that any Stage 8Y effect attributable to heterogeneity can be separated "
          "from effects present without it.",
    "H1": "Low heterogeneity: 75/25 newest/older. A network that has largely, but not "
          "completely, refreshed to the current generation.",
    "H2": "Medium heterogeneity: 50/50. The balanced two-generation reference case.",
    "H3": "High heterogeneity: 25/75. A network dominated by older, less efficient "
          "capacity, with a high-efficiency minority.",
    "H4": "Multi-generation realistic skew: 20% S21 Pro, 30% S19 XP, 50% S19j Pro. "
          "Three generations with the newest as a minority, reflecting the fact that "
          "hardware turnover is gradual and older units keep running while they remain "
          "marginally profitable. It spans the full efficiency range available in the "
          "registry (15.0 to 29.5 J/TH) with an intermediate class in between. The "
          "shares were fixed on this turnover argument BEFORE any Stage 8Y run was "
          "executed and were not adjusted toward or away from any energy threshold.",
}


def _largest_remainder(shares: Dict[str, float], n: int) -> Dict[str, int]:
    """Deterministic integer apportionment summing exactly to n."""
    raw = {k: v * n for k, v in shares.items()}
    counts = {k: int(v) for k, v in raw.items()}
    remaining = n - sum(counts.values())
    order = sorted(raw, key=lambda k: (-(raw[k] - counts[k]), k))
    for i in range(remaining):
        counts[order[i % len(order)]] += 1
    return counts


@dataclass(frozen=True)
class Miner:
    """One physical mining unit."""
    id: int
    device_key: str
    hashrate_hps: float
    active_power_w: float

    @property
    def efficiency_j_per_th(self) -> float:
        return self.active_power_w / (self.hashrate_hps / TH)


@dataclass(frozen=True)
class Population:
    composition: str
    n_miners: int
    miners: Tuple[Miner, ...]
    counts: Dict[str, int]

    @property
    def total_hashrate_hps(self) -> float:
        """H_N = sum_i h_i."""
        return sum(m.hashrate_hps for m in self.miners)

    @property
    def total_hashrate_ths(self) -> float:
        return self.total_hashrate_hps / TH

    @property
    def total_power_w(self) -> float:
        """P_N = sum_i P_i."""
        return sum(m.active_power_w for m in self.miners)

    @property
    def network_efficiency_j_per_th(self) -> float:
        """eta_network = P_N / H_N."""
        return self.total_power_w / self.total_hashrate_ths

    def by_device(self) -> Dict[str, List[Miner]]:
        out: Dict[str, List[Miner]] = {}
        for m in self.miners:
            out.setdefault(m.device_key, []).append(m)
        return out


def build_population(composition: str, n_miners: int,
                     devices: Dict[str, Device] = None) -> Population:
    """Deterministically construct the miner population for (composition, N).

    Miner ids are assigned in a fixed device order so that the same (composition, N)
    always yields the identical population, and so PoW and every PoCol policy receive
    exactly the same hardware.
    """
    devices = devices or DEVICES
    shares = COMPOSITIONS[composition]
    counts = _largest_remainder(shares, n_miners)
    miners: List[Miner] = []
    mid = 0
    for key in sorted(shares):                     # deterministic device order
        dev = devices[key]
        for _ in range(counts[key]):
            miners.append(Miner(id=mid, device_key=key,
                                hashrate_hps=dev.hashrate_hps,
                                active_power_w=dev.active_power_w))
            mid += 1
    assert len(miners) == n_miners
    return Population(composition=composition, n_miners=n_miners,
                      miners=tuple(miners), counts=counts)


def composition_table(compositions: List[str], sizes: List[int]) -> List[dict]:
    rows = []
    for comp in compositions:
        for n in sizes:
            pop = build_population(comp, n)
            row = {
                "composition": comp, "N": n,
                "H_N_THs": pop.total_hashrate_ths,
                "H_N_PHs": pop.total_hashrate_ths / 1000.0,
                "P_N_W": pop.total_power_w,
                "P_N_kW": pop.total_power_w / 1e3,
                "eta_network_J_per_TH": pop.network_efficiency_j_per_th,
            }
            for key in sorted(DEVICES):
                row[f"n_{key}"] = pop.counts.get(key, 0)
                sub = [m for m in pop.miners if m.device_key == key]
                row[f"hash_share_{key}"] = (
                    sum(m.hashrate_hps for m in sub) / pop.total_hashrate_hps)
                row[f"power_share_{key}"] = (
                    sum(m.active_power_w for m in sub) / pop.total_power_w)
            rows.append(row)
    return rows
