"""Stage 8X-ND — frozen configuration.

The protocol nonce field is 32-bit unsigned: NONCE_DOMAIN_SIZE = 2**32 values,
MAX_NONCE = 2**32 - 1. Conventional miners each own the FULL domain
(D_i = D for all i); PoCol partitions the same domain into disjoint
miner-owned ranges. The domain is never enlarged; the internal expanded search
coordinate (template epoch) stays separate from nonce32.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, List, Tuple

NONCE_DOMAIN_SIZE: int = 2 ** 32
MAX_NONCE: int = 2 ** 32 - 1

HASHRATE_HPS: int = 234_000_000_000_000
ACTIVE_POWER_W: float = 3510.0
EFFICIENCY_J_PER_TH: float = 15.0

N_GRID: List[int] = [100, 200, 300, 400, 500]
T_RUN_S: float = 10_000.0
I_TARGET_S: float = 600.0

ALPHA_CASES: Dict[str, float] = {"LP0": 0.00, "LP10": 0.10, "LP25": 0.25, "LP50": 0.50}

# ---- arms ----------------------------------------------------------------
ARM_PW = "ND-PW"              # primary control: zero-start full-domain sweeps
ARM_PW_OFFSET = "ND-PW-OFFSET"  # secondary diagnostic
ARM_PC = "ND-PC"              # PoCol partition + post-range low power
ARM_PC_NOLP = "ND-PC-NOLP"    # derived energy-policy observation of ND-PC

PHYSICAL_ARMS: List[str] = [ARM_PW, ARM_PW_OFFSET, ARM_PC]
PRIMARY_ARMS: List[str] = [ARM_PW, ARM_PC, ARM_PC_NOLP]

#: mapping onto the frozen Stage 8X-NR engine semantics (read-only reuse)
XNR_ARM_OF: Dict[str, str] = {
    ARM_PW: "XNR-PW-CONV-ZERO",
    ARM_PW_OFFSET: "XNR-PW-CONV-OFFSET",
    ARM_PC: "XNR-PC",
}

ARM_LABELS: Dict[str, str] = {
    ARM_PW: "conventional PoW: independent headers, every miner traverses the "
            "full 32-bit nonce-value domain 0..2^32-1 sequentially from 0",
    ARM_PW_OFFSET: "conventional PoW, independent seeded offsets (secondary "
                   "traversal-sensitivity diagnostic)",
    ARM_PC: "PoCol: one common immutable template per epoch, deterministic "
            "disjoint partition of the same 32-bit domain, post-range low "
            "power, no reassignment",
    ARM_PC_NOLP: "PoCol partitioning with completed miners priced at full "
                 "active power (derived observation; separates partitioning "
                 "from low-power policy)",
}


def per_miner_domain(n_miners: int, arm: str, miner: int) -> int:
    """|D_i| for PoW (full domain) or |R_i| for PoCol."""
    if arm in (ARM_PC, ARM_PC_NOLP):
        return ((miner + 1) * NONCE_DOMAIN_SIZE // n_miners
                - miner * NONCE_DOMAIN_SIZE // n_miners)
    return NONCE_DOMAIN_SIZE


def partition(n_miners: int) -> List[Tuple[int, int]]:
    """[start_i, end_i] inclusive, start_i = floor(i*S/N)."""
    return [(i * NONCE_DOMAIN_SIZE // n_miners,
             (i + 1) * NONCE_DOMAIN_SIZE // n_miners - 1)
            for i in range(n_miners)]


def q_per_candidate(n_miners: int) -> float:
    return 1.0 / (n_miners * HASHRATE_HPS * I_TARGET_S)


def difficulty(n_miners: int) -> float:
    return n_miners * HASHRATE_HPS * I_TARGET_S / NONCE_DOMAIN_SIZE


# ---- timing facts (Table ND-D; theory report TQ1-TQ3) --------------------
def sweep_timing(n_miners: int) -> Dict[str, float]:
    t_full = NONCE_DOMAIN_SIZE / HASHRATE_HPS
    sizes = [e - s + 1 for s, e in partition(n_miners)]
    hi = max(sizes)
    t_range = hi / HASHRATE_HPS
    return {
        "t_full_sweep_s": t_full,
        "full_sweeps_per_second": 1.0 / t_full,
        "range_nonces_min": min(sizes), "range_nonces_max": hi,
        "t_range_sweep_s": t_range,
        "range_sweeps_per_second": 1.0 / t_range,
        "full_sweeps_per_600s": I_TARGET_S / t_full,
        "pc_epochs_per_600s": I_TARGET_S / t_range,
    }


# ---- preregistered predictions (theory report) ---------------------------
def predictions(n_miners: int) -> Dict[str, float]:
    sizes = [e - s + 1 for s, e in partition(n_miners)]
    hi, lo = max(sizes), min(sizes)
    n_short = sum(1 for s in sizes if s == lo)
    f_low = (n_short * (hi - lo)) / (n_miners * hi)
    return {
        "block_retention_expected": 1.0,
        "latency_ratio_expected": 1.0,
        "energy_per_block_ratio_expected": 1.0,
        "f_low_expected": f_low,
        **{f"energy_saving_{c}": f_low * (1 - a)
           for c, a in ALPHA_CASES.items()},
        "expected_blocks_per_run": T_RUN_S / I_TARGET_S,
        "trial_rate_identity": 1.0,   # ND-PC trial rate / ND-PW trial rate
    }


def config_dict() -> Dict[str, object]:
    return {
        "experiment": "stage8xnd",
        "nonce_domain_size": NONCE_DOMAIN_SIZE, "max_nonce": MAX_NONCE,
        "hashrate_hps": HASHRATE_HPS, "active_power_w": ACTIVE_POWER_W,
        "efficiency_j_per_th": EFFICIENCY_J_PER_TH,
        "n_grid": N_GRID, "t_run_s": T_RUN_S, "i_target_s": I_TARGET_S,
        "alpha_cases": ALPHA_CASES,
        "physical_arms": PHYSICAL_ARMS, "primary_arms": PRIMARY_ARMS,
        "xnr_arm_map": XNR_ARM_OF,
        "difficulty": {str(n): difficulty(n) for n in N_GRID},
        "q": {str(n): q_per_candidate(n) for n in N_GRID},
        "timing": {str(n): sweep_timing(n) for n in N_GRID},
        "n_primary_seeds": 30, "n_pilot_seeds": 2,
        "pilot_n_grid": [100, 300, 500],
    }


def config_hash() -> str:
    return hashlib.sha256(
        json.dumps(config_dict(), sort_keys=True).encode()).hexdigest()


if __name__ == "__main__":
    print("config_hash:", config_hash())
    for n in N_GRID:
        t = sweep_timing(n)
        p = predictions(n)
        print(n, f"t_range={t['t_range_sweep_s']:.4e}s "
                 f"epochs/600s={t['pc_epochs_per_600s']:.3e} "
                 f"F_low={p['f_low_expected']:.3e}")
