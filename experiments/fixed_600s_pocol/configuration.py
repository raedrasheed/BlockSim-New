"""Configuration for the fixed 600-second round experiment.

Scientific definitions (methodology §1):
- ROUND_DURATION_SECONDS = 600. Each round has one immutable template (per search
  phase), one RoundID, and — in the primary deterministic experiment — exactly one
  accepted block, committed AT the round boundary:
      block_commit_time = round_start_time + 600
  even if the valid nonce is discovered earlier (the block is buffered).
- DISCOVERY TIME (when a miner finds the valid nonce) is recorded separately from
  BLOCK COMMIT TIME (the boundary).
- Bitcoin targets an AVERAGE interval; this exact fixed slot is a controlled
  simulation design, not a literal model of Bitcoin timing.
"""
from __future__ import annotations

from dataclasses import dataclass, field

ROUND_DURATION_SECONDS = 600.0

# ---- physical constants (H1) ----
AGG_HASHRATE_HPS = 141e12                    # 141 TH/s
EFF_J_PER_TH = 21.5                          # J per TH
AGG_ACTIVE_POWER_W = 141.0 * EFF_J_PER_TH    # 3031.5 W
GRID_EF_KG_PER_KWH = 0.445

# ---- protocols ----
PROTO_DUP = "common_template_duplicate_pow"      # Mode A: duplicate-search baseline
PROTO_IND = "independent_header_pow"             # Mode C: independent-header control
PROTO_POCOL = "pocol_disjoint_nonce"             # PoCol disjoint allocation
PROTOCOLS = (PROTO_DUP, PROTO_IND, PROTO_POCOL)

# ---- hardware policies ----
HW_H1 = "H1_FIXED_AGGREGATE_NETWORK_HASHRATE"
HW_H2 = "H2_FIXED_PER_MINER_HARDWARE"
HARDWARE = (HW_H1, HW_H2)

# ---- valid-nonce placements (deterministic) ----
PLACEMENTS = ("first", "p25", "middle", "p75", "last")

# ---- round state machine states ----
ROUND_INITIALIZING = "ROUND_INITIALIZING"
ROUND_SEARCHING = "ROUND_SEARCHING"
SOLUTION_FOUND = "SOLUTION_FOUND"
ROUND_WAITING = "ROUND_WAITING"
ROUND_COMMITTING = "ROUND_COMMITTING"
ROUND_CLOSED = "ROUND_CLOSED"


@dataclass(frozen=True)
class PowerConfig:
    active_ratio: float = 1.0
    idle_ratio: float = 0.0      # q = 0 is the idealized upper bound (documented)
    sleep_ratio: float = 0.0
    use_sleep: bool = False      # finished/stopped miners go to SLEEP instead of IDLE


@dataclass(frozen=True)
class FixedRoundConfig:
    N: int
    protocol: str = PROTO_POCOL
    hardware: str = HW_H1
    M: int = None                        # nonce-domain size; None => calibrated
    power: PowerConfig = field(default_factory=PowerConfig)
    round_seconds: float = ROUND_DURATION_SECONDS
    sim_seconds: float = 10200.0         # exact multiple of 600 (17 rounds)
    placement: str = "last"              # deterministic valid-nonce position
    explicit_nonces: tuple = None        # explicit valid-nonce set (overrides placement)
    p_success: float = None              # stochastic Bernoulli p (None => deterministic)
    seed: int = 0
    txs_per_block: int = 2000            # identical payload for every committed block
    h2_hashrate_hps: float = None        # H2 per-miner rate; None => M/round_seconds
    h2_active_power_w: float = 100.0

    def per_miner_rate_power(self):
        """(hashrate in candidates(=hashes)/s, active power W) for one miner."""
        if self.hardware == HW_H1:
            return AGG_HASHRATE_HPS / self.N, AGG_ACTIVE_POWER_W / self.N
        if self.hardware == HW_H2:
            r = self.h2_hashrate_hps
            if r is None:
                r = float(self.effective_M()) / self.round_seconds
            return float(r), float(self.h2_active_power_w)
        raise ValueError(f"unknown hardware {self.hardware!r}")

    def effective_M(self):
        """Domain size: explicit M, or calibrated so ONE miner's full-domain scan
        takes exactly one round (M = r_i * round_seconds), rounded down to a
        multiple of N so PoCol shares are integral where possible."""
        if self.M is not None:
            return int(self.M)
        if self.hardware == HW_H1:
            m = int((AGG_HASHRATE_HPS / self.N) * self.round_seconds)
        else:
            r = self.h2_hashrate_hps if self.h2_hashrate_hps is not None else 1000.0
            m = int(r * self.round_seconds)
        return max(self.N, m - (m % self.N))

    def n_rounds(self):
        import math
        return int(math.floor(self.sim_seconds / self.round_seconds + 1e-9))


def resolve_placement(placement, M):
    """Map a placement token to the 0-based valid-nonce index in [0, M)."""
    if placement == "first":
        return 0
    if placement == "p25":
        return (M - 1) // 4
    if placement == "middle":
        return (M - 1) // 2
    if placement == "p75":
        return (3 * (M - 1)) // 4
    if placement == "last":
        return M - 1
    raise ValueError(f"unknown placement {placement!r}")
