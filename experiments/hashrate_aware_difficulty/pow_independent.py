"""Independent-header PoW control: distinct per-miner header streams, budgets
equal to the PoCol shares (controlled aggregate budget), zero duplicate
complete-header work. The realistic control -- PoCol superiority may only be
claimed against THIS mode under equal difficulty and equal block output.
"""
from .configuration import DiffExpConfig, PROTO_IND
from .mining_round import simulate


def run(cfg: DiffExpConfig, retargeter=None):
    assert cfg.protocol == PROTO_IND, f"pow_independent.run got {cfg.protocol!r}"
    return simulate(cfg, retargeter=retargeter)
