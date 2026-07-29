"""Stage 3: PoCol round-state, event-identity, difficulty, and finite-domain
semantics. Pure and deterministic (RNG is injected), so every function here is
unit-testable in isolation.

Design summary
--------------
Only miners whose disjoint nonce range actually contains a valid solution can
find a block ("finders"). Per round we therefore schedule at most a handful of
finder events (k ~ Poisson(S*p)) instead of one per miner — this both fixes the
Stage-1/2 "stale explosion" (loser miners were being credited with blocks they
could not have found) and removes the O(N) per-round event bloat.

Difficulty:  p = target / 2^256 ; for target interval B and aggregate hash rate
H, choose p = 1/(H*B) so the network success rate lambda = H*p gives
E[t_block] = 1/lambda = B, independent of the miner count.

Finite domain of size S:  P_success = 1-(1-p)^S,  P_exhaust = (1-p)^S. A round may
find NO solution (exhaustion) -> a new template generation is created; exhaustion
is NEVER a block or a stale block.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, asdict
from typing import Optional, List, Tuple, Dict

TWO_256 = 2 ** 256


# ---------------------------------------------------------------------------
# Difficulty / success-probability semantics
# ---------------------------------------------------------------------------
def per_header_success_probability(target: int) -> float:
    """p = T / 2^256 for a uniformly distributed 256-bit hash output."""
    return float(target) / TWO_256


def target_for_success_probability(p: float) -> int:
    """Inverse of :func:`per_header_success_probability` (rounded)."""
    return int(p * TWO_256)


def target_for_interval(h_total_hps: float, interval_s: float) -> Tuple[float, int]:
    """Return (p, target) so that E[t_block] = interval_s at aggregate rate H.

    p = 1 / (H * B); target = p * 2^256.
    """
    if h_total_hps <= 0 or interval_s <= 0:
        raise ValueError("h_total_hps and interval_s must be > 0")
    p = 1.0 / (h_total_hps * interval_s)
    return p, target_for_success_probability(p)


def network_success_rate(h_total_hps: float, p: float) -> float:
    """lambda = H_total * p  (per second). Depends on H_total, not miner count."""
    return h_total_hps * p


def expected_block_interval(h_total_hps: float, p: float) -> float:
    """E[t_block] = 1 / (H_total * p)."""
    lam = network_success_rate(h_total_hps, p)
    if lam <= 0:
        return math.inf
    return 1.0 / lam


def finite_domain_success_prob(p: float, S: float) -> float:
    """P_success = 1 - (1-p)^S, computed stably via log1p/expm1."""
    if S <= 0:
        return 0.0
    return -math.expm1(S * math.log1p(-p))


def finite_domain_exhaust_prob(p: float, S: float) -> float:
    """P_exhaust = (1-p)^S, computed stably."""
    if S <= 0:
        return 1.0
    return math.exp(S * math.log1p(-p))


def expected_solutions(p: float, S: float) -> float:
    """Expected number of solutions in a domain of size S: mu = p*S."""
    return float(p) * float(S)


# ---------------------------------------------------------------------------
# Event identity
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class EventIdentity:
    event_id: int
    event_generation_id: int
    round_id: int
    parent_block_id: int
    parent_height: int
    template_id: int
    template_generation_id: int
    miner_id: int
    scheduled_at: float
    fires_at: float
    target_version: int
    nonce_range_id: Optional[int] = None

    def as_dict(self) -> dict:
        return asdict(self)


# ---------------------------------------------------------------------------
# Event classification (categories A..H from the Stage-3 brief)
# ---------------------------------------------------------------------------
VALID_CURRENT = "VALID_CURRENT_EVENT"                 # A
LEGIT_COMPETITOR = "LEGITIMATE_PROPAGATION_COMPETITOR"  # B
OBSOLETE_ROUND = "OBSOLETE_ROUND_EVENT"               # C
OBSOLETE_PARENT = "OBSOLETE_PARENT_EVENT"             # D
OBSOLETE_TEMPLATE = "OBSOLETE_TEMPLATE_EVENT"         # E
OBSOLETE_GENERATION = "OBSOLETE_GENERATION_EVENT"     # F
OBSOLETE_DIFFICULTY = "OBSOLETE_DIFFICULTY_EVENT"     # F (target/difficulty version)
FINITE_DOMAIN_EXHAUSTION = "FINITE_DOMAIN_EXHAUSTION"  # G
INVALID_EVENT = "INVALID_EVENT"                       # H

OBSOLETE_CATEGORIES = frozenset({
    OBSOLETE_ROUND, OBSOLETE_PARENT, OBSOLETE_TEMPLATE,
    OBSOLETE_GENERATION, OBSOLETE_DIFFICULTY, INVALID_EVENT,
})


@dataclass
class CurrentState:
    """Snapshot used to classify an event when it fires."""
    miner_tip_id: int
    miner_generation_id: int
    current_round_id: int
    current_template_id: int
    current_template_generation_id: int
    current_target_version: int
    parent_already_advanced: bool
    consumed: bool = False


def classify_event(ev: EventIdentity, cur: CurrentState) -> str:
    """Classify a firing event. Order matters (most specific inconsistency first).

    A rejected obsolete event must NOT become a block, a stale block, a reward,
    or advance the round (enforced by the caller acting on the returned label).
    """
    if cur.consumed:
        return INVALID_EVENT                       # already processed / invalidated
    if ev.event_generation_id != cur.miner_generation_id:
        return OBSOLETE_GENERATION
    if ev.target_version != cur.current_target_version:
        return OBSOLETE_DIFFICULTY
    if ev.template_generation_id != cur.current_template_generation_id:
        return OBSOLETE_TEMPLATE
    if ev.parent_block_id != cur.miner_tip_id:
        return OBSOLETE_PARENT
    if ev.round_id != cur.current_round_id:
        return OBSOLETE_ROUND
    # structurally valid on the miner's current tip
    if cur.parent_already_advanced:
        return LEGIT_COMPETITOR
    return VALID_CURRENT


# ---------------------------------------------------------------------------
# Deterministic round draw (finder-based)
# ---------------------------------------------------------------------------
def poisson(rng, mu: float) -> int:
    """Knuth's Poisson sampler using an injected random.Random-like `rng`."""
    if mu <= 0:
        return 0
    L = math.exp(-mu)
    k = 0
    pp = 1.0
    while True:
        k += 1
        pp *= rng.random()
        if pp <= L:
            return k - 1


def miner_for_position(pos: int, ranges: List[Tuple[int, int, int]]) -> Optional[int]:
    """ranges: list of (miner_id, start, end_inclusive). Return owner of `pos`."""
    for mid, a, b in ranges:
        if a <= pos <= b:
            return mid
    return None


@dataclass
class Solution:
    miner_id: int
    nonce_pos: int
    finder_time_s: float     # time (from round start) at which this miner reaches nonce_pos


def draw_round_solutions(rng, p: float, S: int,
                         ranges: List[Tuple[int, int, int]],
                         rates_hps: Dict[int, float]) -> List[Solution]:
    """Draw the solutions present in this domain and the finder times.

    Number of solutions k ~ Poisson(p*S). Each solution sits at a uniform nonce
    position; its owner miner reaches it after (pos - range_start)/rate seconds
    (parallel per-miner search). Returns solutions sorted by finder_time
    (earliest = round winner). Empty list == finite-domain exhaustion.
    """
    mu = expected_solutions(p, S)
    k = poisson(rng, mu)
    if k == 0:
        return []
    starts = {mid: a for (mid, a, b) in ranges}
    sols: List[Solution] = []
    for _ in range(k):
        pos = rng.randrange(0, S)
        mid = miner_for_position(pos, ranges)
        if mid is None:
            continue
        rate = max(float(rates_hps.get(mid, 0.0)), 1e-12)
        finder_time = (pos - starts[mid]) / rate
        sols.append(Solution(miner_id=mid, nonce_pos=pos, finder_time_s=finder_time))
    sols.sort(key=lambda s: s.finder_time_s)
    return sols
