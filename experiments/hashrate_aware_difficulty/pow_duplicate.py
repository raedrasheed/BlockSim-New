"""Common-template duplicate-search baseline (NOT normal Bitcoin mining).

Every miner scans the identical complete domain in the same order under the
same target, so complete-header evaluations repeat N-fold; the first success in
numeric order stops everyone; unique vs duplicate attempts are reported
separately. Shares the per-template success set with PoCol (paired seeds).
"""
from .configuration import DiffExpConfig, PROTO_DUP
from .mining_round import simulate


def run(cfg: DiffExpConfig, retargeter=None):
    assert cfg.protocol == PROTO_DUP, f"pow_duplicate.run got {cfg.protocol!r}"
    return simulate(cfg, retargeter=retargeter)
