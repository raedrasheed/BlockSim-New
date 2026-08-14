"""Stage 8X-NR — frozen configuration.

Corrected nonce-domain semantics
--------------------------------
The explicit block-header nonce is a 32-bit unsigned field, so the nonce-value
domain has exactly ``S_NONCE = 2**32`` values, 0 .. 2**32-1. This is the domain on
which nonce-value reuse is measured. It is NOT the entire search capability of a
miner: search extends past it through extranonce-induced template renewal, which
the engine models explicitly as template epochs. The internal expanded coordinate
is ``position = template_epoch * 2**32 + nonce32`` with ``nonce32 = position mod
2**32``; every output preserves 32-bit header-nonce semantics.

Difficulty derivation (re-derived, not inherited from Stage 8X)
---------------------------------------------------------------
A candidate is accepted iff SHA256d(header || nonce32) <= target. Modelling the
double-SHA output as uniform on [0, 2^256) gives per-candidate success probability
q = target / 2^256, i.i.d. across DISTINCT hash inputs. A network evaluating
distinct inputs at rate R_d inputs/second therefore finds blocks at rate R_d * q.
With every miner active, conventional PoW's distinct-input rate is R_d = H_N
(distinct templates make every evaluation a fresh input), so requiring
E[interval] = 1/(H_N q) = 600 s yields

    q_N      = 1 / (H_N * 600)
    D_N      = H_N * 600 / 2^32          (Bitcoin convention E[hashes/block] = D*2^32)
    target_N = 2^256 * q_N

which confirms the Stage 8X formula D_N = H_N * I / 2^32 against the simulator's
actual probability semantics. One D_N per N is shared by all five arms; PoCol is
never calibrated separately.

Time base
---------
All work is counted in integer TICKS of one candidate evaluation per miner:
1 tick = 1/h seconds (h = 2.34e14 evals/s), so counts are exact integers and
``nonce32`` phases are exact residues mod 2**32. T = 10 000 s = 2.34e18 ticks.
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Dict, List, Tuple

# ---- explicit 32-bit nonce-value domain ----------------------------------
S_NONCE: int = 2 ** 32                     # exactly 4 294 967 296 values

# ---- hardware (Bitmain Antminer S21 Pro, as in Stage 8X) -----------------
HASHRATE_HPS: int = 234_000_000_000_000    # 234 TH/s, exact integer evals/s
ACTIVE_POWER_W: float = 3510.0
EFFICIENCY_J_PER_TH: float = 15.0

# ---- experiment frame ----------------------------------------------------
N_GRID: List[int] = [100, 200, 300, 400, 500]
T_RUN_S: float = 10_000.0
I_TARGET_S: float = 600.0
T_RUN_TICKS: int = int(T_RUN_S) * HASHRATE_HPS          # 2.34e18, exact
SWEEP_TICKS: int = S_NONCE                              # one full nonce-field sweep
SWEEP_SECONDS: float = S_NONCE / HASHRATE_HPS           # 18.355 us

ALPHA_CASES: Dict[str, float] = {"LP0": 0.00, "LP10": 0.10, "LP25": 0.25, "LP50": 0.50}

# ---- protocol / traversal arms ------------------------------------------
ARM_CONV_ZERO = "XNR-PW-CONV-ZERO"      # per-miner templates, all start nonce 0
ARM_CONV_OFF = "XNR-PW-CONV-OFFSET"     # per-miner templates, random offsets (primary)
ARM_MT_ZERO = "XNR-PW-MT-ZERO"          # common template, zero-start (worst-case bound)
ARM_MT_OFF = "XNR-PW-MT-OFFSET"         # common template, random offsets (primary)
ARM_PC = "XNR-PC"                       # PoCol disjoint allocation of the 2^32 domain

ARMS: List[str] = [ARM_CONV_ZERO, ARM_CONV_OFF, ARM_MT_ZERO, ARM_MT_OFF, ARM_PC]
PRIMARY_ARMS: List[str] = [ARM_CONV_OFF, ARM_MT_OFF, ARM_PC]
DIAGNOSTIC_ARMS: List[str] = [ARM_CONV_ZERO, ARM_MT_ZERO]

ARM_LABELS: Dict[str, str] = {
    ARM_CONV_ZERO: "conventional independent-template PoW, zero-start "
                   "(deliberately synchronized worst-case control)",
    ARM_CONV_OFF: "conventional independent-template PoW, independently offset "
                  "sequential traversal (primary conventional model)",
    ARM_MT_ZERO: "matched common-template competitive PoW, zero-start "
                 "(synchronized diagnostic bound; NOT Bitcoin mainnet behaviour)",
    ARM_MT_OFF: "matched common-template competitive PoW, random offsets "
                "(controlled comparator; NOT Bitcoin mainnet behaviour)",
    ARM_PC: "PoCol common immutable template, deterministic disjoint nonce "
            "allocation, post-range low power",
}

#: Sub-sweep diagnostic window (ticks). Round- and run-scoped nonce coverage
#: saturates for any scope longer than one 18.4 us sweep, so traversal-policy
#: sensitivity (Comparison C) is measured on the first W ticks of each round with
#: W = floor(S / (2N)) < S/N, where offset arcs collide only occasionally.
def subsweep_window_ticks(n_miners: int) -> int:
    return S_NONCE // (2 * n_miners)


# ---- difficulty ----------------------------------------------------------
@dataclass(frozen=True)
class NRDifficulty:
    n_miners: int
    aggregate_hashrate_hps: int
    q_per_candidate: float
    difficulty: float
    target_int: int
    expected_winners_per_template_domain: float   # lambda = q * 2^32

    @property
    def target_hex(self) -> str:
        return f"0x{self.target_int:064x}"


def derive_difficulty(n_miners: int) -> NRDifficulty:
    if n_miners <= 0:
        raise ValueError("n_miners must be > 0")
    h_total = n_miners * HASHRATE_HPS
    q = 1.0 / (h_total * I_TARGET_S)
    difficulty = h_total * I_TARGET_S / S_NONCE
    target_int = (2 ** 256) // int(h_total * int(I_TARGET_S))
    return NRDifficulty(
        n_miners=n_miners,
        aggregate_hashrate_hps=h_total,
        q_per_candidate=q,
        difficulty=difficulty,
        target_int=target_int,
        expected_winners_per_template_domain=q * S_NONCE,
    )


# ---- PoCol partition of the 32-bit domain (brief section 20) -------------
def pocol_partition(n_miners: int) -> List[Tuple[int, int]]:
    """Half-open ranges [start_i, end_i_exclusive) with start_i = floor(i*S/N).

    Sizes differ by at most one nonce; the union tiles [0, 2^32) exactly and the
    ranges are pairwise disjoint. 2^32 is NOT assumed divisible by N.
    """
    return [
        (i * S_NONCE // n_miners, (i + 1) * S_NONCE // n_miners)
        for i in range(n_miners)
    ]


def partition_stats(n_miners: int) -> Dict[str, int]:
    sizes = [e - s for s, e in pocol_partition(n_miners)]
    return {
        "n": n_miners,
        "size_min": min(sizes),
        "size_max": max(sizes),
        "n_long_ranges": sum(1 for s in sizes if s == max(sizes)),
        "n_short_ranges": sum(1 for s in sizes if s == min(sizes)),
        "total": sum(sizes),
    }


# ---- preregistered analytic predictions (brief section 18) ---------------
def predictions(n_miners: int) -> Dict[str, float]:
    """Analytical expectations frozen before execution (Table NR-J inputs)."""
    st = partition_stats(n_miners)
    hi, lo = st["size_max"], st["size_min"]
    n_short = st["n_short_ranges"]
    # PoCol epoch lasts hi ticks; short-range miners idle (hi - lo) <= 1 tick.
    f_low_time = (n_short * (hi - lo)) / (n_miners * hi)
    round_evals = n_miners * HASHRATE_HPS * I_TARGET_S   # E[C_nonce] per round
    w = subsweep_window_ticks(n_miners)
    return {
        "sweep_seconds": SWEEP_SECONDS,
        "sweeps_per_round": I_TARGET_S / SWEEP_SECONDS,
        "rho_nonce_round_expected": 1.0 - S_NONCE / round_evals,
        "rho_nonce_epoch_MT": (n_miners - 1) / n_miners,
        "rho_exact_epoch_MT": (n_miners - 1) / n_miners,
        "rho_nonce_epoch_PC": 0.0,
        "rho_exact_epoch_PC": 0.0,
        "rho_exact_CONV": 0.0,
        "pc_f_low_time_expected": f_low_time,
        "pc_energy_saving_alpha0_expected": f_low_time,
        "mt_expected_blocks_per_run": T_RUN_S / (I_TARGET_S * n_miners),
        "conv_expected_blocks_per_run": T_RUN_S / I_TARGET_S,
        "subsweep_window_ticks": float(w),
        "subsweep_pair_overlap_expected_offset": (w * w) / S_NONCE,
        "subsweep_pair_overlap_zero": float(w),
        "occupancy_EU_coeff": 1.0,   # E[U] = S(1-(1-1/S)^m), evaluated where applicable
    }


# ---- canonical config hash ----------------------------------------------
def config_dict() -> Dict[str, object]:
    return {
        "experiment": "stage8xnr",
        "S_nonce": S_NONCE,
        "hashrate_hps": HASHRATE_HPS,
        "active_power_w": ACTIVE_POWER_W,
        "efficiency_j_per_th": EFFICIENCY_J_PER_TH,
        "n_grid": N_GRID,
        "t_run_s": T_RUN_S,
        "i_target_s": I_TARGET_S,
        "alpha_cases": ALPHA_CASES,
        "arms": ARMS,
        "primary_arms": PRIMARY_ARMS,
        "subsweep_window": {str(n): subsweep_window_ticks(n) for n in N_GRID},
        "difficulty": {
            str(n): {
                "q": derive_difficulty(n).q_per_candidate,
                "D": derive_difficulty(n).difficulty,
                "target_hex": derive_difficulty(n).target_hex,
            }
            for n in N_GRID
        },
        "partition": {str(n): partition_stats(n) for n in N_GRID},
        "n_primary_seeds": 30,
        "n_pilot_seeds": 2,
        "pilot_n_grid": [100, 300, 500],
    }


def config_hash() -> str:
    return hashlib.sha256(
        json.dumps(config_dict(), sort_keys=True).encode()
    ).hexdigest()


if __name__ == "__main__":
    print("config_hash:", config_hash())
    for n in N_GRID:
        d = derive_difficulty(n)
        p = predictions(n)
        print(n, f"D={d.difficulty:.6e} q={d.q_per_candidate:.6e} "
                 f"lam_domain={d.expected_winners_per_template_domain:.3e} "
                 f"F_low={p['pc_f_low_time_expected']:.3e} "
                 f"MT_blocks={p['mt_expected_blocks_per_run']:.4f}")
