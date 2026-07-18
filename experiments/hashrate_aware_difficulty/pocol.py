"""PoCol disjoint-nonce protocol under hash-rate-aware difficulty.

One immutable template per search phase with ONE target for the whole round;
the finite domain [0, M_total) (M_total = H_network * budget) is partitioned
into disjoint, collectively exhaustive subranges; each miner searches only its
range; no complete candidate header is evaluated by two miners; a miner idles
individually on exhaustion; the first valid candidate stops everyone; the block
commits IMMEDIATELY and the next template starts at once (methodology §6).
"""
from .configuration import DiffExpConfig, PROTO_POCOL
from .mining_round import simulate


def run(cfg: DiffExpConfig, retargeter=None):
    assert cfg.protocol == PROTO_POCOL, f"pocol.run got {cfg.protocol!r}"
    return simulate(cfg, retargeter=retargeter)
