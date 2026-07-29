"""Stage 5B1A analytical B1 zero-block model.

B1: every miner searches the SAME ordered candidate path from nonce 0. Only the
leading (fastest) miner advances the unique frontier, so the effective unique
coverage rate is:

    homogeneous   :  H_unique = H_total / N
    heterogeneous :  H_unique = max_i H_i      (all share one ordered path)

(For homogeneous rates max_i H_i = H_total / N, so the two agree.)

Over duration T with per-candidate success probability p:

    expected_unique_evaluations = H_unique * T
    lambda (expected accepted blocks, Poisson) = p * H_unique * T
    P(accepted_blocks = 0) = exp(-lambda)                 [memoryless closed form]

This is the SPECIFIED closed-form model. The discrete engine draws a finite set
of solutions per generation (min of ~mu uniform positions) rather than a
memoryless Bernoulli stream, so its empirical zero-block frequency is slightly
BELOW exp(-lambda); the gap is documented and bounded, and both agree in
magnitude and in the monotone increase with N.
"""

from __future__ import annotations
import math
from typing import List, Dict


def h_unique(rates: List[float], homogeneous: bool) -> float:
    """Unique-frontier hash rate for B1 (max over miners; == H_total/N homogeneous)."""
    return max(rates) if rates else 0.0


def zero_block_probability(p: float, h_unique_hps: float, T: float) -> float:
    lam = p * h_unique_hps * T
    return math.exp(-lam)


def b1_row(network_hash_rate_hps: float, N: int, T: float, target_interval_s: float) -> Dict:
    """Analytical B1 zero-block row for miner count N (homogeneous)."""
    p = 1.0 / (network_hash_rate_hps * target_interval_s)
    Hu = network_hash_rate_hps / N                     # H_total / N (homogeneous)
    lam = p * Hu * T
    p0 = math.exp(-lam)
    return dict(
        miner_count=N, h_unique_hps=Hu, p=p,
        expected_unique_evaluations=Hu * T,
        expected_accepted_blocks=lam,
        zero_block_probability=p0,
        zero_block_risk_category=risk_category(p0))


def risk_category(p0: float) -> str:
    if p0 >= 0.90:
        return "very_high"
    if p0 >= 0.50:
        return "high"
    if p0 >= 0.10:
        return "moderate"
    return "low"


def b1_table(network_hash_rate_hps: float = 141e12, T: float = 10000.0,
             target_interval_s: float = 600.0,
             counts=(100, 200, 300, 400, 500)) -> List[Dict]:
    return [b1_row(network_hash_rate_hps, N, T, target_interval_s) for N in counts]
