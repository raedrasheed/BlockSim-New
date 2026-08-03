"""Stage-2 confirmatory configuration for the PoCol core simulator.

The algorithm is **PoCol**; the energy-saving mechanism is **the idle policy within
PoCol** (residency in low-power / idle states, never nonce partitioning).

The A1 accounting invariant (STAGE_01_ENERGY_MODEL_SPECIFICATION.md) fixes the
continuous full-participation control:

    141 miners x 21.5 W x 10_000 s / 3_600_000  ==  8.420833333 kWh

so the per-miner active (hashing) power is ``P_hash = 21.5 W`` and the horizon is
``T = 10_000 s``.  The idle-policy powers obey the canonical ordering
``P_offline <= P_listen = P_reserve = P_registered <= P_hash`` (``P_wake`` transient).
No dynamic difficulty is used in the confirmatory core.
"""
from __future__ import annotations

from dataclasses import dataclass

from .security import SecurityFloorPolicy

# A1 accounting invariant — the frozen matched control (kWh).
A1_BASELINE_KWH = 8.420833333
JOULES_PER_KWH = 3_600_000.0


@dataclass(frozen=True)
class Stage2Config:
    """Immutable per-run configuration for the Stage-2 PoCol core."""

    # --- horizon & population ---
    run_start_time: float = 0.0
    horizon_T: float = 10_000.0
    num_miners: int = 141

    # --- canonical state-to-power mapping (watts, per miner) ---
    # A1 fixes P_hash = 21.5 W (141 TH/s over 141 miners at 21.5 J/TH).
    P_hash: float = 21.5
    P_listen: float = 2.15      # == P_registered == P_reserve (low-power standby/listen)
    P_wake: float = 10.75       # transient waking draw
    P_offline: float = 0.0      # == P_disqualified

    # --- deterministic round timing (seconds) ---
    wake_latency: float = 1.0             # StartWake -> WakeCompleteEvent latency

    # --- scientific search core (S2B-1/S2B-2) ---
    # Success is coupled to the fixed target: a nonce succeeds iff SHA256(header||nonce)
    # <= target_for_difficulty(difficulty).  No dynamic difficulty; no sampled/placed
    # winner; no stored-but-unused success field.
    nonce_domain_size: int = 4000         # explicit finite nonce domain [0, D)
    difficulty: int = 1000               # fixed confirmatory difficulty (sets the work target)
    batch_size: int = 50                 # declared nonce batch planned per HashWorkEvent
    base_hash_rate: float = 100.0        # base nonces/second per miner
    heterogeneous_hash_rates: bool = True  # vary hash rate by miner to exercise the idle policy
    template_seed: int = 20260803        # deterministic template-header seed

    def hash_rate_for(self, index: int) -> float:
        """Deterministic per-miner hash rate (heterogeneous so ranges finish at different times)."""
        if not self.heterogeneous_hash_rates:
            return self.base_hash_rate
        return self.base_hash_rate * (1.0 + (index % 4))   # 1x .. 4x

    # --- participation (idle policy) ---
    reserve_fraction: float = 0.2   # fraction of genesis miners held in RESERVE (reserve pool)
    P_reserve: float = 2.15         # reserve standby power (== P_listen by default)

    # --- Stage-3 security floor + reserve activation (disabled by default) ---
    security_floor: SecurityFloorPolicy = SecurityFloorPolicy()
    floor_unattainable_policy: str = "CONTINUE_DEGRADED"   # or ABORT_ROUND

    # --- scenario injection (tests only; empty in confirmatory runs) ---
    abort_round_seqs: frozenset = frozenset()   # round seqs that abort instead of accepting

    # --- bounds ---
    maximum_setup_retries: int = 3

    def per_miner_power(self, state: str) -> float:
        """Canonical single residency power for a miner state (STAGE_01 s.1.0)."""
        return {
            "REGISTERED": self.P_listen,
            "RESERVE": self.P_reserve,
            "ACTIVE_HASHING": self.P_hash,
            "EXHAUSTED_PENDING": self.P_hash,
            "LOW_POWER_LISTEN": self.P_listen,
            "WAKING": self.P_wake,
            "OFFLINE": self.P_offline,
            "DISQUALIFIED": self.P_offline,
        }[state]


def a1_continuous_control_kwh(cfg: Stage2Config) -> float:
    """The A1 continuous full-participation control energy for ``cfg`` (kWh).

    Every miner ACTIVE_HASHING for the whole horizon.  With the default config this
    is exactly ``A1_BASELINE_KWH`` (8.420833333 kWh) — the matched control against
    which the idle policy's saving is measured.  It is invariant to nonce partitioning.
    """
    joules = cfg.num_miners * cfg.P_hash * cfg.horizon_T
    return joules / JOULES_PER_KWH
