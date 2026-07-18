"""Configuration for the hash-rate-aware difficulty experiment."""
from __future__ import annotations

from dataclasses import dataclass, field

T_TARGET_SECONDS = 600.0

# ---- physical constants ----
AGG_HASHRATE_HPS = 141e12            # H1 fixed aggregate network hash rate
EFF_J_PER_HASH = 21.5e-12            # 21.5 J/TH
GRID_EF_KG_PER_KWH = 0.445

# ---- protocols ----
PROTO_DUP = "common_template_duplicate_baseline"
PROTO_IND = "independent_header_pow"
PROTO_POCOL = "pocol_disjoint_nonce"
PROTOCOLS = (PROTO_DUP, PROTO_IND, PROTO_POCOL)

# ---- hash-rate policies (never mixed) ----
HW_H1 = "H1_FIXED_AGGREGATE_NETWORK_HASHRATE"
HW_H2 = "H2_FIXED_PER_MINER_HASHRATE"
HARDWARE = (HW_H1, HW_H2)

# ---- difficulty modes ----
D1_CONSTANT = "D1_CONSTANT_DIFFICULTY"
D2_SCALED = "D2_HASHRATE_SCALED_DIFFICULTY"
D3_RETARGET = "D3_DYNAMIC_RETARGET"
DIFFICULTY_MODES = (D1_CONSTANT, D2_SCALED, D3_RETARGET)


@dataclass(frozen=True)
class PowerConfig:
    idle_ratio: float = 0.0
    sleep_ratio: float = 0.0
    use_sleep: bool = False


@dataclass(frozen=True)
class DifficultyConfig:
    mode: str = D2_SCALED
    # D1: difficulty frozen at the reference work (reference_hashrate * T)
    # D2: difficulty follows the CURRENT aggregate hash rate
    # D3: starts from initial_factor * (H_network*T) and retargets on a window
    reference_hashrate_hps: float = None   # None => single-miner rate (H2) / aggregate (H1)
    d3_window_blocks: int = 10             # 10 tests / 100 experiments / 2016 Bitcoin-like
    d3_clamp_min: float = 0.25
    d3_clamp_max: float = 4.0
    d3_initial_factor: float = 1.0


@dataclass(frozen=True)
class DiffExpConfig:
    N: int
    protocol: str = PROTO_POCOL
    hardware: str = HW_H1
    difficulty: DifficultyConfig = field(default_factory=DifficultyConfig)
    power: PowerConfig = field(default_factory=PowerConfig)
    t_target: float = T_TARGET_SECONDS
    sim_seconds: float = 10200.0
    seed: int = 0
    txs_per_block: int = 2000
    h2_miner_hashrate_hps: float = 1.41e12   # H2: fixed per-miner rate (agg grows with N)
    # finite nonce-domain TIME budget (seconds of whole-network scanning): the
    # domain size is M_total = H_network * domain_time_budget. This is a domain
    # SIZE knob only — difficulty lives exclusively in the target (section 3).
    domain_time_budget: float = 1200.0       # 2*T => P(domain has no success)=e^-2

    # ---- hash-rate policy (section 2) ----
    def per_miner_hashrate(self):
        if self.hardware == HW_H1:
            return AGG_HASHRATE_HPS / self.N
        if self.hardware == HW_H2:
            return self.h2_miner_hashrate_hps
        raise ValueError(f"unknown hardware {self.hardware!r}")

    def network_hashrate(self):
        """H_network = sum of ACTIVE miners' rates (equal miners here)."""
        return self.per_miner_hashrate() * self.N

    def per_miner_power_w(self):
        return self.per_miner_hashrate() * EFF_J_PER_HASH

    def reference_hashrate(self):
        """The hash rate that defines the REFERENCE difficulty D_1 (D1/D3)."""
        if self.difficulty.reference_hashrate_hps is not None:
            return float(self.difficulty.reference_hashrate_hps)
        if self.hardware == HW_H2:
            return self.h2_miner_hashrate_hps        # single-miner reference
        return AGG_HASHRATE_HPS                      # H1: aggregate is the reference
