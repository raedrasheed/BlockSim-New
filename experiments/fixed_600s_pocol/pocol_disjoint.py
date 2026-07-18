"""PoCol disjoint-nonce allocation under fixed 600-second rounds.

The complete domain [0, M) is physically partitioned into mutually disjoint,
collectively exhaustive subranges; every miner evaluates ONLY its own subrange
and never continues into another miner's range. A miner idles the moment it
exhausts its subrange; the first discovery stops everyone; all wait IDLE until
the boundary where the buffered block commits.

Discovery uses each miner's LOCAL position: local_success_i = (nonce - start_i
+ 1) for the valid nonces inside range i, and the network discovery is the
minimum LOCAL step — the numerically smallest valid nonce is not necessarily
the wall-clock-earliest.
"""
from __future__ import annotations

from .round_state import TemplateOutcome
from .nonce_partition import partition_nonce_domain, range_size
from .deterministic_template import valid_nonces


def deterministic_provider(cfg):
    M = cfg.effective_M()
    N = cfg.N
    ranges = partition_nonce_domain(0, M, N)
    sizes = [range_size(r) for r in ranges]
    ns = valid_nonces(cfg, M)

    local = [None] * N
    nonceval = [None] * N
    for g in ns:                                  # each miner's FIRST owned success
        for i, (s, e) in enumerate(ranges):
            if s <= g < e:
                step = g - s + 1
                if local[i] is None or step < local[i]:
                    local[i] = step
                    nonceval[i] = g
                break

    def provider(_cfg, _round_id, _template_index):
        return TemplateOutcome(
            template_id=f"POCOL-det-{_round_id}-{_template_index}",
            sizes=list(sizes),
            local_success=list(local),
            nonce_value=list(nonceval),
        )
    return provider


def provider_for(cfg):
    """Deterministic or stochastic provider by config (stochastic arrives with
    the stochastic_template module)."""
    if cfg.p_success is None:
        return deterministic_provider(cfg)
    from .stochastic_template import stochastic_provider
    return stochastic_provider(cfg)
