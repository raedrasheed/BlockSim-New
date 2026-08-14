"""Stage 8Y — difficulty / target and nonce-domain derivation.

Difficulty (identical rule to Stage 8X, generalised to heterogeneous populations)
--------------------------------------------------------------------------------
Acceptance is ``SHA256d(header || extranonce || nonce) <= target``. Treating the
digest as uniform on [0, 2^256) gives a per-candidate success probability
``q = target / 2^256 = 1 / (D * 2^32)``, so a network hashing at ``H_N`` candidates
per second produces blocks at rate ``H_N * q`` and

        D_{N,H} = H_N * I_target / 2^32                                       (1)
        q_{N,H} = 1 / (H_N * I_target)                                        (2)
        target  = 2^256 / (D * 2^32)                                          (3)

with ``H_N = sum_i h_i`` taken over the **full installed hardware population**.

The single ``D_{N,H}`` produced here is handed unchanged to the traditional PoW
comparator and to every PoCol policy. There is no PoCol-specific difficulty path
anywhere in Stage 8Y, and difficulty is never reduced because a policy activates
fewer miners.

Nonce domain (the decision that matters, brief section 19)
----------------------------------------------------------
The per-epoch candidate domain is derived from **full installed capacity**:

        S_{N,H} = H_N * tau_epoch,   tau_epoch = I_target = 600 s             (4)

and is partitioned into one disjoint slot per *installed* miner:

        hash-proportional   L_i = S * h_i / H_N = h_i * tau                   (5)
        equal               L_i = S / N                                       (6)

Consequences, all fixed before execution:

* Every miner's slot exists whether or not the policy activates it, so **reducing
  the active set never reduces the amount of search the network must perform**.
  Parking a miner leaves its slot unscanned; it does not shrink the domain.
* Under (5) every miner needs exactly ``tau`` seconds to sweep its own slot,
  independently of ``h_i``, so hash-proportional allocation equalises completion
  times by construction.
* Under (6) a miner needs ``tau * (H_N/N) / h_i`` seconds, so fast miners finish
  early and slow miners finish late — which is precisely the effect policy P1 is
  designed to expose.

The alternative semantics (sizing ``S`` from the *active* rather than the installed
capacity) would covertly reduce the work requirement in PoCol's favour. It is
therefore not used for the primary experiment; it is available only as an
explicitly labelled secondary sensitivity condition.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import List

from experiments.stage8y.config.hardware import Population, build_population

HASHES_PER_DIFFICULTY = 2 ** 32
TWO_256 = 2 ** 256

DOMAIN_INSTALLED = "installed"   # frozen primary semantics, eq. (4)
DOMAIN_ACTIVE = "active"         # secondary sensitivity only


@dataclass(frozen=True)
class DifficultySpec:
    composition: str
    n_miners: int
    target_interval_s: float
    epoch_sweep_s: float
    total_hashrate_hps: float
    total_power_w: float
    difficulty: float
    q_per_candidate: float
    target_int: int
    nonce_domain: int
    domain_semantics: str

    @property
    def expected_hashes_per_block(self) -> float:
        return self.difficulty * HASHES_PER_DIFFICULTY

    @property
    def expected_winners_per_epoch(self) -> float:
        return self.q_per_candidate * self.nonce_domain

    @property
    def p_epoch_exhaustion(self) -> float:
        return math.exp(-self.expected_winners_per_epoch)

    @property
    def target_hex(self) -> str:
        return f"0x{self.target_int:064x}"


def derive(composition: str, n_miners: int, target_interval_s: float = 600.0,
           epoch_sweep_s: float = 600.0,
           domain_semantics: str = DOMAIN_INSTALLED,
           population: Population = None) -> DifficultySpec:
    """Apply equations (1)-(4) for one (N, composition)."""
    pop = population or build_population(composition, n_miners)
    h_total = pop.total_hashrate_hps
    difficulty = h_total * target_interval_s / HASHES_PER_DIFFICULTY
    q = 1.0 / (h_total * target_interval_s)
    target_int = TWO_256 // int(difficulty * HASHES_PER_DIFFICULTY)
    domain = int(round(h_total * epoch_sweep_s))
    return DifficultySpec(
        composition=composition, n_miners=n_miners,
        target_interval_s=float(target_interval_s),
        epoch_sweep_s=float(epoch_sweep_s),
        total_hashrate_hps=h_total, total_power_w=pop.total_power_w,
        difficulty=difficulty, q_per_candidate=q, target_int=target_int,
        nonce_domain=domain, domain_semantics=domain_semantics,
    )


def slot_lengths(pop: Population, spec: DifficultySpec, allocation: str) -> List[int]:
    """Disjoint per-installed-miner slot lengths, eq. (5)/(6).

    ``allocation`` is ``"hash"`` (proportional) or ``"equal"``. Slots tile
    ``[0, S)`` exactly; slot i starts at the cumulative sum of the preceding ones.
    """
    n = pop.n_miners
    if allocation == "equal":
        base = spec.nonce_domain // n
        lengths = [base] * n
        lengths[-1] += spec.nonce_domain - base * n
    elif allocation == "hash":
        h_total = pop.total_hashrate_hps
        lengths = [int(spec.nonce_domain * m.hashrate_hps / h_total) for m in pop.miners]
        lengths[-1] += spec.nonce_domain - sum(lengths)
    else:
        raise ValueError(f"unknown allocation {allocation!r}")
    return lengths


def slot_bounds(lengths: List[int]) -> List[tuple]:
    """Half-open [start, end) bounds; pairwise disjoint, tiling [0, S)."""
    out, cur = [], 0
    for L in lengths:
        out.append((cur, cur + L))
        cur += L
    return out


def difficulty_table(compositions: List[str], sizes: List[int],
                     target_interval_s: float = 600.0,
                     epoch_sweep_s: float = 600.0) -> List[dict]:
    rows = []
    for comp in compositions:
        for n in sizes:
            pop = build_population(comp, n)
            s = derive(comp, n, target_interval_s, epoch_sweep_s, population=pop)
            rows.append({
                "composition": comp, "N": n,
                "H_N_Hps": s.total_hashrate_hps,
                "H_N_THs": s.total_hashrate_hps / 1e12,
                "P_N_W": s.total_power_w,
                "eta_network_J_per_TH": pop.network_efficiency_j_per_th,
                "difficulty_D": s.difficulty,
                "target": s.target_hex,
                "q_per_candidate": s.q_per_candidate,
                "expected_hashes_per_block": s.expected_hashes_per_block,
                "nonce_domain_S": s.nonce_domain,
                "domain_semantics": s.domain_semantics,
                "expected_winners_per_epoch": s.expected_winners_per_epoch,
                "p_epoch_exhaustion_predicted": s.p_epoch_exhaustion,
            })
    return rows
