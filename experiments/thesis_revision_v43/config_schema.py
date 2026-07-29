"""Stage 4 shared, validated configuration schema for scenarios B0-B3 / C1-C2.

One schema drives every scenario; `validate()` rejects scientifically
incompatible combinations so a fair comparison cannot be misconfigured.
"""

from __future__ import annotations

from dataclasses import dataclass, field, asdict
from typing import List, Optional
import hashlib
import json

SCENARIOS = ["B0", "B1", "B2", "B3", "C1", "C2"]
DISJOINT_SCENARIOS = {"B3", "C1", "C2"}
COMMON_TEMPLATE_SCENARIOS = {"B1", "B2", "B3", "C1", "C2"}
IDLE_SCENARIOS = {"C2"}


@dataclass
class ExperimentConfig:
    scenario_id: str
    seed: int
    miner_count: int
    simulation_duration_s: float
    network_hash_rate_hps: float
    efficiency_j_per_th: float
    target_block_interval_s: float
    nonce_domain_size: int
    allocation_policy: str            # "independent" | "from_zero" | "randomized_start" | "disjoint_equal" | "disjoint_weighted"
    search_order_policy: str          # "ordered" | "randomized_start"
    template_policy: str              # "independent" | "common"
    # optional / policy-dependent
    miner_hash_rate_distribution: str = "homogeneous"   # or "heterogeneous:<name>"
    hash_rate_shares: Optional[List[float]] = None
    idle_power_ratio: Optional[float] = None            # required for C2
    coordination_energy_model: str = "excluded_zero"    # or "configured"
    coordination_energy_kwh: float = 0.0
    randomized_start_policy: str = "none"               # "none" | "uniform"
    template_refresh_policy: str = "reallocate"         # for continuous exhaustion
    propagation_delay_model: str = "expovariate"
    propagation_delay_mean_s: float = 0.42
    topology: str = "gossip_full"
    transaction_arrival_model: str = "none"
    block_capacity: int = 0
    inactive_miner_fraction: float = 0.0
    logging_level: str = "summary"
    code_commit: str = ""

    # ---- derived ----
    def resolved_shares(self) -> List[float]:
        if self.hash_rate_shares is not None:
            tot = sum(self.hash_rate_shares)
            return [x / tot for x in self.hash_rate_shares]
        return [1.0 / self.miner_count] * self.miner_count

    def per_miner_hash_rate_hps(self) -> List[float]:
        return [sh * self.network_hash_rate_hps for sh in self.resolved_shares()]

    def configuration_hash(self) -> str:
        d = asdict(self)
        d["hash_rate_shares"] = self.resolved_shares()
        return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()

    def expected_solutions_mu(self) -> float:
        p = 1.0 / (self.network_hash_rate_hps * self.target_block_interval_s)
        return p * self.nonce_domain_size


class ConfigError(ValueError):
    pass


def validate(cfg: ExperimentConfig) -> None:
    """Raise ConfigError on any scientifically incompatible setting."""
    if cfg.scenario_id not in SCENARIOS:
        raise ConfigError(f"unknown scenario_id {cfg.scenario_id!r}")
    if cfg.miner_count <= 0:
        raise ConfigError("miner_count must be > 0")
    if cfg.network_hash_rate_hps <= 0 or cfg.efficiency_j_per_th <= 0:
        raise ConfigError("hash rate and efficiency must be > 0")
    if cfg.target_block_interval_s <= 0 or cfg.simulation_duration_s <= 0:
        raise ConfigError("durations must be > 0")
    if cfg.nonce_domain_size <= 0:
        raise ConfigError("nonce_domain_size must be > 0")

    # per-miner hash rates must sum to the network total
    total = sum(cfg.per_miner_hash_rate_hps())
    if abs(total - cfg.network_hash_rate_hps) / cfg.network_hash_rate_hps > 1e-9:
        raise ConfigError("per-miner hash rates must sum to network_hash_rate_hps")

    # template consistency
    is_common = cfg.template_policy == "common"
    if cfg.scenario_id == "B0" and is_common:
        raise ConfigError("B0 (independent-template PoW) must NOT use a common template")
    if cfg.scenario_id in COMMON_TEMPLATE_SCENARIOS and not is_common:
        raise ConfigError(f"{cfg.scenario_id} requires a common template")
    if cfg.scenario_id == "B0" and cfg.allocation_policy != "independent":
        raise ConfigError("B0 must use the independent allocation")

    # disjoint scenarios
    if cfg.scenario_id in DISJOINT_SCENARIOS and not cfg.allocation_policy.startswith("disjoint"):
        raise ConfigError(f"{cfg.scenario_id} requires a disjoint allocation policy")
    if cfg.allocation_policy.startswith("disjoint") and cfg.scenario_id not in DISJOINT_SCENARIOS:
        raise ConfigError(f"disjoint allocation is only valid for {sorted(DISJOINT_SCENARIOS)}")

    # randomized start only for B2
    if cfg.scenario_id == "B2" and cfg.randomized_start_policy == "none":
        raise ConfigError("B2 requires randomized_start_policy != 'none'")

    # idle policy only for C2, and it MUST define idle power
    if cfg.scenario_id in IDLE_SCENARIOS:
        if cfg.idle_power_ratio is None:
            raise ConfigError("C2 must define idle_power_ratio (0.0 == explicit lower bound)")
        if not (0.0 <= cfg.idle_power_ratio <= 1.0):
            raise ConfigError("idle_power_ratio must be in [0, 1]")
    else:
        if cfg.idle_power_ratio not in (None, 0.0):
            raise ConfigError(f"{cfg.scenario_id} is continuous and must not set a nonzero idle_power_ratio")

    # coordination energy: never invented
    if cfg.coordination_energy_model == "excluded_zero" and cfg.coordination_energy_kwh != 0.0:
        raise ConfigError("coordination_energy_model=excluded_zero requires coordination_energy_kwh == 0")

    # B0 cannot share a serialized-header duplicate identity across miners
    if cfg.scenario_id == "B0" and is_common:
        raise ConfigError("B0 cannot use a shared serialized-header duplicate identity")

    if not (0.0 <= cfg.inactive_miner_fraction < 1.0):
        raise ConfigError("inactive_miner_fraction must be in [0, 1)")
