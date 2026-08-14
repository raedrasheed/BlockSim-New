"""Stage 8X — network-size-coupled difficulty / target derivation.

Unlike experiment families that pin the aggregate hash rate, Stage 8X grows the
aggregate rate with the miner population (H_N = N * 234 TH/s). The difficulty must
therefore be coupled to N so that the *matched PoW baseline* keeps the nominal
600 s block interval at every N.

Derivation (exact, no hand-wavy multipliers)
--------------------------------------------
Bitcoin-style PoW accepts a candidate when

        SHA256d(header || extranonce || nonce)  <=  target                     (1)

Treating the double-SHA-256 output as uniform on [0, 2^256), the per-candidate
success probability is

        q = target / 2^256                                                     (2)

Using the standard difficulty convention  expected_hashes_per_block = D * 2^32,

        q = 1 / (D * 2^32)                                                     (3)

A network hashing at H_N candidates/second therefore produces blocks as a Poisson
process of rate  H_N * q, so the expected block interval is

        E[I] = 1 / (H_N * q) = D * 2^32 / H_N                                  (4)

Setting E[I] = I_target = 600 s and solving for D gives the frozen rule

        D_N = H_N * I_target / 2^32                     (difficulty)           (5)
        q_N = 1 / (H_N * I_target)                      (per-candidate prob.)  (6)
        target_N = 2^256 * q_N = 2^256 / (D_N * 2^32)   (256-bit target)       (7)

so that D_N is proportional to H_N, exactly as required. Because a single D_N is
computed per N and handed to *both* protocols, D^PoW_N == D^PoCol_N identically:
there is no separate PoCol calibration anywhere in Stage 8X.

Nonce domain
------------
The per-epoch candidate domain is derived from the same parameters rather than
being tuned:

        S_N = H_N * tau_epoch = D_N * 2^32 * (tau_epoch / I_target)            (8)
        L   = S_N / N = h * tau_epoch    (per-miner range, identical for all N) (9)

With the frozen primary choice tau_epoch = I_target = 600 s, one epoch's domain
holds exactly one block's expected work, so

        P(no solution in an epoch) = exp(-q_N * S_N) = exp(-1) = 0.36788        (10)

and the expected number of winning candidates per epoch is exactly 1. Equation
(10) is the *predicted* epoch-turnover rate that the Pilot verifies empirically.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List

from experiments.stage8x.config.asic import ASICProfile, S21_PRO

HASHES_PER_DIFFICULTY = 2 ** 32          # Bitcoin convention: E[hashes/block] = D * 2^32
TWO_256 = 2 ** 256


@dataclass(frozen=True)
class DifficultySpec:
    """Everything derived from (N, profile, target interval, epoch sweep time)."""

    n_miners: int
    target_interval_s: float
    epoch_sweep_s: float
    aggregate_hashrate_hps: float
    difficulty: float          # D_N, eq. (5)
    q_per_candidate: float     # q_N, eq. (6)
    target_int: int            # 256-bit integer target, eq. (7)
    nonce_domain: int          # S_N, eq. (8)  [candidates per epoch, network-wide]
    range_per_miner: int       # L,   eq. (9)  [candidates per epoch, per miner]

    @property
    def expected_hashes_per_block(self) -> float:
        return self.difficulty * HASHES_PER_DIFFICULTY

    @property
    def expected_winners_per_epoch(self) -> float:
        """lambda = q * S : expected winning candidates per epoch domain."""
        return self.q_per_candidate * self.nonce_domain

    @property
    def p_epoch_exhaustion(self) -> float:
        """Predicted probability that an epoch domain contains no solution, eq. (10)."""
        import math

        return math.exp(-self.expected_winners_per_epoch)

    @property
    def lambda_per_miner_range(self) -> float:
        """Expected winning candidates inside one miner's range (= 1/N at tau=I)."""
        return self.q_per_candidate * self.range_per_miner

    @property
    def target_hex(self) -> str:
        return f"0x{self.target_int:064x}"


def derive(
    n_miners: int,
    target_interval_s: float = 600.0,
    epoch_sweep_s: float = 600.0,
    profile: ASICProfile = S21_PRO,
) -> DifficultySpec:
    """Apply equations (5)-(9) for one network size."""
    if n_miners <= 0:
        raise ValueError("n_miners must be > 0")
    if target_interval_s <= 0 or epoch_sweep_s <= 0:
        raise ValueError("intervals must be > 0")

    h_total = profile.aggregate_hashrate_hps(n_miners)          # H_N  [candidates/s]
    difficulty = h_total * target_interval_s / HASHES_PER_DIFFICULTY   # eq. (5)
    q = 1.0 / (h_total * target_interval_s)                     # eq. (6)
    target_int = TWO_256 // (int(difficulty * HASHES_PER_DIFFICULTY))  # eq. (7)

    domain = int(round(h_total * epoch_sweep_s))                # eq. (8)
    per_miner = int(round(profile.hashrate_hps * epoch_sweep_s))  # eq. (9)
    # Keep the partition exact: N disjoint equal ranges must tile the domain.
    domain = per_miner * n_miners

    return DifficultySpec(
        n_miners=n_miners,
        target_interval_s=float(target_interval_s),
        epoch_sweep_s=float(epoch_sweep_s),
        aggregate_hashrate_hps=h_total,
        difficulty=difficulty,
        q_per_candidate=q,
        target_int=target_int,
        nonce_domain=domain,
        range_per_miner=per_miner,
    )


def disjoint_ranges(spec: DifficultySpec) -> List[tuple]:
    """Deterministic static disjoint allocation: miner i owns [i*L, (i+1)*L).

    Returns a list of half-open (start, end) candidate-index ranges, one per miner,
    which tile [0, S_N) exactly and pairwise intersect in the empty set.
    """
    L = spec.range_per_miner
    return [(i * L, (i + 1) * L) for i in range(spec.n_miners)]


def difficulty_table(
    network_sizes: List[int],
    target_interval_s: float = 600.0,
    epoch_sweep_s: float = 600.0,
    profile: ASICProfile = S21_PRO,
) -> List[dict]:
    rows = []
    for n in network_sizes:
        s = derive(n, target_interval_s, epoch_sweep_s, profile)
        rows.append(
            {
                "N": n,
                "aggregate_hashrate_Hps": s.aggregate_hashrate_hps,
                "difficulty": s.difficulty,
                "target_hex": s.target_hex,
                "q_per_candidate": s.q_per_candidate,
                "expected_hashes_per_block": s.expected_hashes_per_block,
                "nonce_domain": s.nonce_domain,
                "range_per_miner": s.range_per_miner,
                "expected_winners_per_epoch": s.expected_winners_per_epoch,
                "p_epoch_exhaustion_predicted": s.p_epoch_exhaustion,
            }
        )
    return rows
