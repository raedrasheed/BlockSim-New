"""Stage 8X-ND — engine wrapper.

The three physical arms are exactly the frozen, 61-test-validated Stage 8X-NR
semantics (imported READ-ONLY; the protected baseline proves the module is
byte-identical):

    ND-PW         = XNR-PW-CONV-ZERO   (independent headers; every miner
                                        traverses 0..2^32-1 from 0; header
                                        renewal + nonce reset per sweep)
    ND-PW-OFFSET  = XNR-PW-CONV-OFFSET (secondary diagnostic)
    ND-PC         = XNR-PC             (common immutable template, disjoint
                                        partition of the same 2^32 domain,
                                        ACTIVE -> LOW_POWER after own range,
                                        no reassignment)

executed on fresh Stage 8X-ND seeds. ND-PC-NOLP is a DERIVED energy-policy
observation of the ND-PC physical trajectory: identical work, blocks, timing;
low-power miner-time priced at full active power (E = P * N * T exactly).

The trial-rate identity this experiment measures (theory TQ4): ND-PW's
distinct headers give N*h independent trials/s; ND-PC's disjoint ranges under
an N-times-faster common-template renewal also give N*h. Both engines realise
q_N = 1/(N*h*600) per distinct input, shared at each N.
"""

from __future__ import annotations

from typing import Dict

from experiments.stage8xnd.config.nd_config import (
    ACTIVE_POWER_W, ARM_PC, ARM_PC_NOLP, ARM_PW, ARM_PW_OFFSET, PHYSICAL_ARMS,
    T_RUN_S, XNR_ARM_OF,
)
from experiments.stage8xnr.src.engine_nr import RunResult, run_one as _xnr_run


def run_physical(arm: str, n: int, seed: int) -> RunResult:
    """One physical run of a Stage 8X-ND arm on a Stage 8X-ND seed."""
    if arm not in PHYSICAL_ARMS:
        raise ValueError(f"{arm!r} is not a physical arm")
    return _xnr_run(XNR_ARM_OF[arm], n, seed, collect_rounds=True)


def energy_j(res: RunResult, arm_policy: str, alpha: float) -> float:
    """Energy under a policy: ND-PC prices t_low at alpha*P; ND-PC-NOLP and
    the PoW arms price all miner-time at full active power."""
    if arm_policy == ARM_PC:
        return ACTIVE_POWER_W * (res.t_active_miner_s
                                 + alpha * res.t_low_miner_s)
    # ND-PC-NOLP / ND-PW / ND-PW-OFFSET: full power for the whole horizon
    return ACTIVE_POWER_W * (res.t_active_miner_s + res.t_low_miner_s)


def nolp_matches_physical(res: RunResult) -> Dict[str, float]:
    """Test-15 support: NOLP changes accounting only, never physics."""
    return {
        "same_C_total": float(res.C_total),
        "e_nolp_J": energy_j(res, ARM_PC_NOLP, 0.0),
        "e_nolp_equals_full": abs(
            energy_j(res, ARM_PC_NOLP, 0.0)
            - ACTIVE_POWER_W * res.n_miners * T_RUN_S),
    }
