"""Phase B2 — round termination and stale-block event semantics.

Verifies that once a round is won, pending create-events for that round are
lazily rejected (not counted, not charged, not propagated, no new round), while
the invalidation is narrowly scoped to the exact (parent_id, round_id) so that
genuine competing blocks on other branches/rounds remain countable.

Run:  python -m pytest tests/ -v   or   python tests/test_round_semantics.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from InputsConfig import InputsConfig as p
from Models.PoCol.Node import Node as PoColNode
from Models.PoCol.Consensus import Consensus as C
from Models.PoCol.BlockCommit import BlockCommit
from Statistics import Statistics
from Event import Queue


def _fresh(n=5):
    p.model = 3
    p.HashPowerIsShare = True
    p.NetworkHashRate_Hps = 141e12
    p.MinerEfficiency_J_per_TH = 21.5
    p.GridEF_kgCO2e_per_kWh = 0.445
    p.simTime = 10000.0
    p.hasTrans = False
    p.NODES = [PoColNode(id=i, hashPower=1) for i in range(n)]
    C.round_id = 0
    C._closed_rounds = set()
    C.active_parent_id = None
    C.active_round_status = "ACTIVE"
    Statistics.totalBlocks = 0
    Queue.event_list = []
    Queue._seq_counter = 0
    PoColNode.generate_gensis_block()
    return p.NODES


class _Evt:
    def __init__(self, block, t):
        self.block = block; self.time = t; self.node = block.miner; self.type = "create_block"


class _Blk:
    def __init__(self, miner, previous, bid, round_id, t):
        self.miner = miner; self.previous = previous; self.id = bid
        self.round_id = round_id; self.timestamp = t; self.depth = 1
        self.transactions = None; self.usedgas = 0


def test_open_and_close_round():
    _fresh()
    C._open_round(parent_id=42)
    rid = C.round_id
    assert C.active_round_status == "ACTIVE"
    assert not C.is_round_closed(42, rid)
    C.close_round(42, rid, winning_block_id=999, winning_miner_id=1, t=123.0)
    assert C.is_round_closed(42, rid)
    assert C.active_round_status == "CLOSED"
    assert C.winning_block_id == 999 and C.winning_miner_id == 1
    assert C.round_end_time == 123.0


def test_new_round_has_new_id_and_is_open():
    _fresh()
    C._open_round(parent_id=1); r1 = C.round_id
    C.close_round(1, r1, 111, 0, 10.0)
    C._open_round(parent_id=222); r2 = C.round_id   # new parent, next round
    assert r2 == r1 + 1
    assert not C.is_round_closed(222, r2)
    assert C.is_round_closed(1, r1)          # old round stays closed


def test_invalidation_is_scoped_to_parent_and_round():
    """Genuine competing blocks on a different parent/round are NOT rejected."""
    _fresh()
    C._open_round(parent_id=5); r = C.round_id
    C.close_round(5, r, 1, 0, 1.0)
    assert C.is_round_closed(5, r)            # this exact round is closed
    assert not C.is_round_closed(5, r + 1)    # a different round on same parent
    assert not C.is_round_closed(6, r)        # a different parent
    assert not C.is_round_closed(6, None)     # models without rounds never closed


def test_first_block_closes_round_second_is_rejected():
    nodes = _fresh(n=5)
    parent = nodes[0].last_block().id
    C._open_round(parent_id=parent); rid = C.round_id

    # winner creates a valid block on the tip
    winner = nodes[0]
    b1 = _Blk(miner=winner.id, previous=parent, bid=1001, round_id=rid, t=100.0)
    BlockCommit.generate_block(_Evt(b1, 100.0))
    assert Statistics.totalBlocks == 1
    assert C.is_round_closed(parent, rid)
    assert winner.last_block().id == 1001

    # a loser's event for the SAME closed round is rejected
    before_blocks = Statistics.totalBlocks
    loser = nodes[1]
    before_tip = loser.last_block().id
    before_energy = loser.energy_kwh
    b2 = _Blk(miner=loser.id, previous=parent, bid=1002, round_id=rid, t=105.0)
    BlockCommit.generate_block(_Evt(b2, 105.0))
    assert Statistics.totalBlocks == before_blocks, "rejected event must not count a block"
    assert loser.last_block().id == before_tip, "rejected event must not append a block"
    assert 1002 not in [b.id for b in loser.blockchain], "rejected event must not be committed"
    # energy is wall-clock (B1); a rejected event must not add a per-round charge
    assert loser.energy_kwh == before_energy, "rejected event must not charge energy"


def test_rejected_event_does_not_propagate():
    nodes = _fresh(n=5)
    parent = nodes[0].last_block().id
    C._open_round(parent_id=parent); rid = C.round_id
    C.close_round(parent, rid, 1, 0, 1.0)     # pre-close the round
    Queue.event_list = []; Queue._seq_counter = 0
    b = _Blk(miner=nodes[2].id, previous=parent, bid=2002, round_id=rid, t=50.0)
    BlockCommit.generate_block(_Evt(b, 50.0))
    assert Queue.isEmpty(), "rejected event must not schedule receive/propagation events"
    assert Statistics.totalBlocks == 0


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
