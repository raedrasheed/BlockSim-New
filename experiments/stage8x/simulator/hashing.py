"""Stage 8X — SHA-256 candidate semantics and the rate-abstraction scaling model.

Why an abstraction is required
------------------------------
A single S21 Pro performs 2.34e14 candidate evaluations per second; the primary
matrix spans 300 runs of 10 000 simulated seconds at up to 500 miners, i.e. of the
order of 1e21 candidate evaluations. Executing those as literal Python SHA-256
calls is impossible, and the brief forbids pretending otherwise.

The scaling model (documented conversion)
-----------------------------------------
1.  **Candidate identity.** A candidate is the exact serialized hash input

        header_bytes(template) || extranonce (4 B, BE) || nonce (4 B, BE)

    indexed by the integer ``candidate_index = extranonce * 2**32 + nonce``.
    Two evaluations are *exact duplicates* iff they share ``(template_id,
    candidate_index)``. Equal ``nonce`` values under different templates are NOT
    duplicates and are counted separately as nonce-value reuse.

2.  **Acceptance.** A candidate is a winner iff ``sha256d(candidate) <= target``.
    Modelling ``sha256d`` as uniform on [0, 2**256) gives an i.i.d. Bernoulli(q)
    field over candidate indices with ``q = target / 2**256``.

3.  **Winner oracle instead of enumeration.** Because the field is i.i.d.
    Bernoulli(q), the *set of winning indices* inside a domain of size ``M`` is a
    binomial point process, which for the q and M used here is numerically exact
    as ``K ~ Poisson(q*M)`` winners at i.i.d. uniform positions in ``[0, M)``.
    Stage 8X samples that oracle once per template domain and then advances each
    miner's cursor deterministically at its physical rate ``h``.

    This is *equivalent to enumerating every candidate* while costing O(K) draws,
    and — crucially — it keeps the field **consistent between miners**: if two
    miners evaluate the same ``(template_id, candidate_index)``, they get the same
    answer. That consistency is what makes duplicate work genuinely wasteful in
    the matched-template comparator instead of silently doubling the block rate.

4.  **Validation.** ``monte_carlo_success_rate`` performs *real* double SHA-256 over
    real serialized candidates at an artificially easy target and checks that the
    empirical success rate matches ``q = target / 2**256``. That pins step 2 to
    true SHA-256 semantics without enumerating the operational domain.
"""

from __future__ import annotations

import hashlib
import math
import random
import struct
from dataclasses import dataclass
from typing import List, Sequence, Tuple

TWO_32 = 2 ** 32
TWO_256 = 2 ** 256


# --------------------------------------------------------------------------
# Real candidate serialisation + double SHA-256 (used for validation only)
# --------------------------------------------------------------------------
def template_header(template_id: str) -> bytes:
    """A deterministic 76-byte pseudo-header standing in for the block template.

    The exact field layout is irrelevant to the physics; what matters is that a
    template maps to a fixed byte prefix and that distinct templates map to
    distinct prefixes (so distinct templates cannot produce duplicate candidates).
    """
    digest = hashlib.sha256(template_id.encode("utf-8")).digest()
    return (digest + digest + digest)[:76]


#: Serialisation width of the extranonce field, in bits. Stage 8X uses an 8-byte
#: extranonce (Stratum extranonce2 is commonly 4-8 bytes and the coinbase can carry
#: more), giving a per-template candidate space of 2**96. A 4-byte extranonce is
#: *not* wide enough here: one PoCol epoch domain is S_N = N * 1.404e17 candidates,
#: which exceeds 2**64 for N >= 132. This is a serialisation-width choice, not a
#: scientific parameter — it changes no probability, rate, or energy quantity.
EXTRANONCE_BITS = 64
MAX_CANDIDATE_INDEX = 2 ** (EXTRANONCE_BITS + 32)


def candidate_bytes(template_id: str, candidate_index: int) -> bytes:
    """Exact serialized hash input for ``(template_id, candidate_index)``."""
    idx = int(candidate_index)
    if not (0 <= idx < MAX_CANDIDATE_INDEX):
        raise ValueError("candidate_index outside the representable candidate space")
    extranonce, nonce = divmod(idx, TWO_32)
    return (template_header(template_id)
            + extranonce.to_bytes(EXTRANONCE_BITS // 8, "big")
            + struct.pack(">I", nonce))


def sha256d(data: bytes) -> int:
    """Bitcoin-style double SHA-256, interpreted as a big-endian 256-bit integer."""
    return int.from_bytes(hashlib.sha256(hashlib.sha256(data).digest()).digest(), "big")


def is_winner(template_id: str, candidate_index: int, target: int) -> bool:
    """True iff SHA256d(header || extranonce || nonce) <= target."""
    return sha256d(candidate_bytes(template_id, candidate_index)) <= target


def monte_carlo_success_rate(target: int, trials: int, seed: int = 0) -> Tuple[int, float]:
    """Empirical success rate of real double-SHA-256 against ``target``.

    Returns ``(successes, q_theoretical)``. Used by the validation suite to confirm
    the ``q = target / 2**256`` mapping on genuinely hashed candidates.
    """
    rng = random.Random(seed)
    hits = 0
    for _ in range(trials):
        idx = rng.randrange(0, 2 ** 48)
        if is_winner("stage8x-validation-template", idx, target):
            hits += 1
    return hits, target / TWO_256


# --------------------------------------------------------------------------
# Winner oracle over a candidate domain
# --------------------------------------------------------------------------
def _poisson(rng: random.Random, lam: float) -> int:
    """Knuth / inversion Poisson sampler (lam is <= 1 in every Stage 8X use)."""
    if lam <= 0.0:
        return 0
    if lam < 30.0:
        limit = math.exp(-lam)
        k, prod = 0, rng.random()
        while prod > limit:
            k += 1
            prod *= rng.random()
        return k
    # Normal approximation guard; never reached with Stage 8X parameters.
    return max(0, int(round(rng.gauss(lam, math.sqrt(lam)))))


def sample_winners(rng: random.Random, domain_size: int, q: float) -> List[int]:
    """Winning candidate offsets inside ``[0, domain_size)`` — sorted, de-duplicated.

    ``K ~ Poisson(q * domain_size)`` winners at i.i.d. uniform offsets. This is the
    exact law of the Bernoulli(q) field restricted to the domain (to within the
    binomial->Poisson identity, whose error is O(q) ~ 1e-19 here).
    """
    lam = q * float(domain_size)
    k = _poisson(rng, lam)
    if k == 0:
        return []
    offsets = sorted({rng.randrange(domain_size) for _ in range(k)})
    return offsets


def first_winner_at_or_after(winners: Sequence[int], cursor: int):
    """Smallest winning offset >= cursor, or ``None``."""
    lo, hi = 0, len(winners)
    while lo < hi:
        mid = (lo + hi) // 2
        if winners[mid] < cursor:
            lo = mid + 1
        else:
            hi = mid
    return winners[lo] if lo < len(winners) else None


# --------------------------------------------------------------------------
# Exact-duplicate accounting over scanned candidate intervals
# --------------------------------------------------------------------------
@dataclass
class ScanLedger:
    """Records scanned candidate intervals and computes exact duplicate work.

    A scan is a half-open interval ``[start, end)`` of candidate indices under one
    ``template_id``. Total work is the sum of interval lengths; unique work is the
    measure of their union *per template*; duplicate work is the difference. This
    is exact and never materialises individual candidate indices.
    """

    def __init__(self) -> None:
        self._by_template = {}      # template_id -> list[(start, end)]
        self._total = 0

    def record(self, template_id, start: int, end: int) -> None:
        if end <= start:
            return
        self._by_template.setdefault(template_id, []).append((int(start), int(end)))
        self._total += int(end) - int(start)

    @property
    def total_evaluations(self) -> int:
        return self._total

    def unique_evaluations(self) -> int:
        total = 0
        for intervals in self._by_template.values():
            intervals.sort()
            cur_s, cur_e = intervals[0]
            for s, e in intervals[1:]:
                if s > cur_e:
                    total += cur_e - cur_s
                    cur_s, cur_e = s, e
                else:
                    cur_e = max(cur_e, e)
            total += cur_e - cur_s
        return total

    def duplicate_evaluations(self) -> int:
        return self._total - self.unique_evaluations()

    def distinct_nonce_values(self) -> int:
        """Distinct 32-bit ``nonce`` values touched anywhere in the run.

        Reported to keep nonce-value reuse strictly separate from exact-input
        duplication (brief section 15). An interval at least 2**32 long touches every
        nonce value, which is the normal case at S21-Pro rates.
        """
        segments = []
        for intervals in self._by_template.values():
            for s, e in intervals:
                if e - s >= TWO_32:
                    return TWO_32
                a, b = s % TWO_32, e % TWO_32
                if a < b:
                    segments.append((a, b))
                else:
                    segments.append((a, TWO_32))
                    segments.append((0, b))
        if not segments:
            return 0
        segments.sort()
        total = 0
        cur_s, cur_e = segments[0]
        for s, e in segments[1:]:
            if s > cur_e:
                total += cur_e - cur_s
                cur_s, cur_e = s, e
            else:
                cur_e = max(cur_e, e)
        total += cur_e - cur_s
        return total

    def n_templates(self) -> int:
        return len(self._by_template)
