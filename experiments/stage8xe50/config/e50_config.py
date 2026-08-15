"""Stage 8X-E50 — frozen configuration.

Comparator discipline: the energy/service/coverage baseline is E50-MT100, the
same-template competitive PoW CONTROL. E50-CONV100 (conventional
independent-template PoW) is an external scientific reference only and is never
the denominator for any >50 % claim.

Difficulty (re-audited, not inherited): success per DISTINCT input is
Bernoulli(q); a network evaluating distinct inputs at rate R_d finds blocks at
R_d·q. The nominal 600 s interval is defined for the FULL conventional network
(distinct rate H_N = N·h), giving q_N = 1/(H_N·600), D_N = H_N·600/2^32.
One D_N per N is shared by all ten arms; PoCol active fractions are NEVER
retargeted (brief sections 13-14) — any block-rate consequence is a result.
"""

from __future__ import annotations

import hashlib
import json
import math
from typing import Dict, List, Tuple

# ---- domain and hardware (identical to Stage 8X-NR) ----------------------
S_NONCE: int = 2 ** 32
HASHRATE_HPS: int = 234_000_000_000_000
ACTIVE_POWER_W: float = 3510.0
EFFICIENCY_J_PER_TH: float = 15.0

N_GRID: List[int] = [100, 200, 300, 400, 500]
T_RUN_S: float = 10_000.0
I_TARGET_S: float = 600.0
T_RUN_TICKS: int = int(T_RUN_S) * HASHRATE_HPS

ALPHA_CASES: Dict[str, float] = {"LP0": 0.00, "LP10": 0.10, "LP25": 0.25, "LP50": 0.50}

# ---- scenarios -----------------------------------------------------------
ACTIVE_FRACTIONS: Dict[str, float] = {
    "E50-PC10": 0.10, "E50-PC20": 0.20, "E50-PC30": 0.30, "E50-PC40": 0.40,
    "E50-PC50": 0.50, "E50-PC60": 0.60, "E50-PC80": 0.80, "E50-PC100": 1.00,
}
ARM_CONV = "E50-CONV100"      # external reference only
ARM_MT = "E50-MT100"          # PRIMARY baseline (same-template control)
PC_ARMS: List[str] = list(ACTIVE_FRACTIONS)
ARMS: List[str] = [ARM_CONV, ARM_MT] + PC_ARMS

ARM_LABELS: Dict[str, str] = {
    ARM_CONV: "conventional independent-template PoW (external reference; "
              "NOT the >50% baseline)",
    ARM_MT: "same-template competitive PoW control (primary baseline; "
            "NOT Bitcoin mainnet)",
    **{a: f"PoCol disjoint allocation, active fraction {int(f*100)}% "
          "(inactive owners in low power; no reassignment)"
       for a, f in ACTIVE_FRACTIONS.items()},
}

# ---- preregistered feasibility constraints (brief section 38) ------------
COVERAGE_RETENTION_MIN = 0.95
BLOCK_RETENTION_MIN = 0.90
MEDIAN_LATENCY_RATIO_MAX = 1.20


def active_count(n_miners: int, arm: str) -> int:
    """k = ceil(A*N) for PoCol arms; N otherwise."""
    if arm in ACTIVE_FRACTIONS:
        return math.ceil(ACTIVE_FRACTIONS[arm] * n_miners)
    return n_miners


# ---- difficulty ----------------------------------------------------------
def q_per_candidate(n_miners: int) -> float:
    return 1.0 / (n_miners * HASHRATE_HPS * I_TARGET_S)


def difficulty(n_miners: int) -> float:
    return n_miners * HASHRATE_HPS * I_TARGET_S / S_NONCE


# ---- partition of 2^32 over the FULL population (brief section 10) -------
def partition(n_miners: int) -> List[Tuple[int, int]]:
    """Half-open [start, end) ranges; start_i = floor(i*S/N); spread <= 1."""
    return [(i * S_NONCE // n_miners, (i + 1) * S_NONCE // n_miners)
            for i in range(n_miners)]


def epoch_ticks_pc(n_miners: int) -> int:
    """PC epoch length: the longest assigned range (matched renewal rule)."""
    return max(e - s for s, e in partition(n_miners))


# ---- rotation (brief section 11) -----------------------------------------
def active_slots(n_miners: int, k: int, epoch_index: int) -> range:
    """Sliding window of k consecutive permutation slots, advancing one slot
    per epoch. Duty is exactly k/N for every miner over any N consecutive
    epochs; transitions are minimal (one activation episode of k consecutive
    epochs per N-epoch cycle)."""
    start = epoch_index % n_miners
    return range(start, start + k)      # slot s active iff s in window mod N


def is_slot_active(slot: int, n_miners: int, k: int, epoch_index: int) -> bool:
    start = epoch_index % n_miners
    return ((slot - start) % n_miners) < k


# ---- preregistered predictions (theory report section 4-6) ---------------
def predictions(n_miners: int, arm: str) -> Dict[str, float]:
    k = active_count(n_miners, arm)
    n = n_miners
    p: Dict[str, float] = {
        "unique_rate_per_h": (n if arm == ARM_CONV else
                              1 if arm == ARM_MT else k),
        "expected_blocks_per_run": (T_RUN_S / I_TARGET_S if arm == ARM_CONV
                                    else (T_RUN_S / I_TARGET_S) * (
                                        1 if arm == ARM_MT else k) / n),
        "rho_exact": ((n - 1) / n if arm == ARM_MT else 0.0),
        "coverage_retention_vs_MT": (float(n) if arm == ARM_CONV else
                                     1.0 if arm == ARM_MT else float(k)),
        "f_low": 0.0 if arm in (ARM_CONV, ARM_MT) else (n - k) / n,
    }
    for case, alpha in ALPHA_CASES.items():
        p[f"energy_saving_vs_MT_{case}"] = (
            0.0 if arm in (ARM_CONV, ARM_MT)
            else (1 - k / n) * (1 - alpha))
    return p


# ---- canonical config hash ----------------------------------------------
def config_dict() -> Dict[str, object]:
    return {
        "experiment": "stage8xe50",
        "S_nonce": S_NONCE, "hashrate_hps": HASHRATE_HPS,
        "active_power_w": ACTIVE_POWER_W,
        "efficiency_j_per_th": EFFICIENCY_J_PER_TH,
        "n_grid": N_GRID, "t_run_s": T_RUN_S, "i_target_s": I_TARGET_S,
        "alpha_cases": ALPHA_CASES, "arms": ARMS,
        "active_fractions": ACTIVE_FRACTIONS,
        "constraints": {"coverage": COVERAGE_RETENTION_MIN,
                        "blocks": BLOCK_RETENTION_MIN,
                        "latency": MEDIAN_LATENCY_RATIO_MAX},
        "difficulty": {str(n): difficulty(n) for n in N_GRID},
        "q": {str(n): q_per_candidate(n) for n in N_GRID},
        "epoch_ticks_pc": {str(n): epoch_ticks_pc(n) for n in N_GRID},
        "rotation": "sliding window, +1 slot per epoch, fixed run permutation",
        "renewal_rule": "epoch ends when every ACTIVE miner completes its "
                        "assigned traversal (MT: full domain; PC: own range)",
        "n_primary_seeds": 30, "n_pilot_seeds": 2,
        "pilot_n_grid": [100, 300, 500],
    }


def config_hash() -> str:
    return hashlib.sha256(
        json.dumps(config_dict(), sort_keys=True).encode()).hexdigest()


if __name__ == "__main__":
    print("config_hash:", config_hash())
    for n in (100, 500):
        for arm in (ARM_MT, "E50-PC10", "E50-PC50"):
            print(n, arm, predictions(n, arm))
