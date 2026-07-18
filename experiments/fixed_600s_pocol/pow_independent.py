"""Mode C — independent-header PoW control.

Each miner searches a DISTINCT candidate block header (its own independent
stream), so no complete candidate-header evaluation is ever duplicated. The
aggregate candidate-evaluation budget is CONTROLLED: equal to PoCol's total
budget M, split as the same partition sizes (M/N each for equal miners). All
miners stop at the first valid candidate and stay IDLE until the boundary.

Deterministic modeling choice (documented): the first success lands in the
stream of the miner that would own the valid nonce under the PoCol partition,
at step ceil(f * budget) where f = (g+1)/M is the placement fraction. This
keeps the deterministic control comparable without pretending its streams share
nonces with the common-template modes (they do not; nonce_value is None).
"""
from __future__ import annotations

import math

from .round_state import TemplateOutcome
from .nonce_partition import partition_nonce_domain, range_size, owner_of
from .deterministic_template import valid_nonces


def deterministic_provider(cfg):
    M = cfg.effective_M()
    N = cfg.N
    ranges = partition_nonce_domain(0, M, N)
    sizes = [range_size(r) for r in ranges]
    g = min(valid_nonces(cfg, M))
    f = (g + 1) / M
    winner = owner_of(ranges, g)
    if winner is None or sizes[winner] == 0:
        winner = max(range(N), key=lambda i: sizes[i])
    step = max(1, min(sizes[winner], math.ceil(f * sizes[winner])))

    def provider(_cfg, _round_id, _template_index):
        ls = [None] * N
        ls[winner] = step
        return TemplateOutcome(
            template_id=f"IND-det-{_round_id}-{_template_index}",
            sizes=list(sizes),
            local_success=ls,
            nonce_value=[None] * N,       # distinct headers: no shared nonce identity
        )
    return provider
