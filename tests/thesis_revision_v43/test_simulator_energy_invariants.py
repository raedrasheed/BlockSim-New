"""Stage 2 integration tests exercising the REAL Node class (the `/100` fix and
the wall-clock ACTIVE accounting) via a deterministic Node-level harness — no
random event loop, so results are exact and fast.

These complement the module-level tests in ``test_wallclock_energy.py`` and
confirm that both the PoW (Bitcoin) and PoCol Node paths share the corrected
model.
"""

import os
import sys
import math
import contextlib

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node as BitcoinNode
from Models.PoCol.Node import Node as PoColNode

NET_HPS = 141e12
EFF = 21.5
T_SIM = 10000.0
EXPECTED_KWH = 3031.5 * 10000.0 / 3_600_000.0    # 8.420833333...
REL = 1e-9


@contextlib.contextmanager
def homogeneous_network(node_cls, n):
    """Temporarily install n homogeneous miners into InputsConfig."""
    saved = dict(NODES=getattr(p, "NODES", None),
                 NET=getattr(p, "NetworkHashRate_Hps", None),
                 EFF=getattr(p, "MinerEfficiency_J_per_TH", None),
                 SHARE=getattr(p, "HashPowerIsShare", None),
                 IDLEW=getattr(p, "IdlePowerW", None),
                 IDLER=getattr(p, "IdlePowerRatio", None))
    try:
        p.NetworkHashRate_Hps = NET_HPS
        p.MinerEfficiency_J_per_TH = EFF
        p.HashPowerIsShare = True
        p.IdlePowerW = None
        p.IdlePowerRatio = None
        p.NODES = [node_cls(id=i, hashPower=1) for i in range(n)]
        yield p.NODES
    finally:
        for k, v in saved.items():
            key = {"NODES": "NODES", "NET": "NetworkHashRate_Hps",
                   "EFF": "MinerEfficiency_J_per_TH", "SHARE": "HashPowerIsShare",
                   "IDLEW": "IdlePowerW", "IDLER": "IdlePowerRatio"}[k]
            setattr(p, key, v)


def _run_continuous(nodes, t_sim=T_SIM):
    """Every miner active [0, t_sim]; flush at cutoff; return total energy kWh."""
    for nd in nodes:
        nd.start_mining(nd.last_block().id if nd.blockchain else 0, 0.0)
    BitcoinNode.finalize_energy(t_sim)   # static: iterates p.NODES
    return sum(float(getattr(nd, "energy_kwh", 0.0)) for nd in nodes)


def test_node_pow_hashrate_sums_to_network_for_all_counts():
    for n in (100, 200, 300, 400, 500):
        with homogeneous_network(BitcoinNode, n) as nodes:
            total = sum(nd.hash_rate_hps() for nd in nodes)
            assert math.isclose(total, NET_HPS, rel_tol=1e-12), (n, total)
            # per-miner share is net/n, NOT net*1% (the old /100 bug)
            assert math.isclose(nodes[0].hash_rate_hps(), NET_HPS / n, rel_tol=1e-12)


def test_node_pow_wallclock_energy_invariant_all_counts():
    totals = []
    for n in (100, 200, 300, 400, 500):
        with homogeneous_network(BitcoinNode, n) as nodes:
            # each node needs a genesis-like block for last_block(); give one
            from Models.Block import Block
            for nd in nodes:
                nd.blockchain = [Block()]
            totals.append(_run_continuous(nodes))
    for t in totals:
        assert math.isclose(t, EXPECTED_KWH, rel_tol=REL), t
    assert max(totals) - min(totals) < 1e-9   # miner-count independent


def test_node_flush_idempotent_at_sim_level():
    with homogeneous_network(BitcoinNode, 100) as nodes:
        from Models.Block import Block
        for nd in nodes:
            nd.blockchain = [Block()]
            nd.start_mining(0, 0.0)
        BitcoinNode.finalize_energy(T_SIM)
        e1 = sum(nd.energy_kwh for nd in nodes)
        BitcoinNode.finalize_energy(T_SIM)   # idempotent
        BitcoinNode.finalize_energy(T_SIM)
        e2 = sum(nd.energy_kwh for nd in nodes)
        assert e1 == e2
        assert math.isclose(e1, EXPECTED_KWH, rel_tol=REL)


def test_node_no_energy_beyond_cutoff():
    with homogeneous_network(BitcoinNode, 100) as nodes:
        from Models.Block import Block
        for nd in nodes:
            nd.blockchain = [Block()]
            nd.start_mining(0, 0.0)
        BitcoinNode.finalize_energy(5000.0)     # cutoff halfway
        e_half = sum(nd.energy_kwh for nd in nodes)
        BitcoinNode.finalize_energy(10000.0)    # cannot extend closed intervals
        e_after = sum(nd.energy_kwh for nd in nodes)
        assert math.isclose(e_half, EXPECTED_KWH / 2.0, rel_tol=REL)
        assert e_after == e_half


def test_pocol_node_uses_same_wallclock_path():
    # PoCol miners inherit the corrected Node.hash_rate_hps and wall-clock
    # accounting; total energy equals the PoW invariant (not /N).
    totals = []
    for n in (100, 500):
        with homogeneous_network(PoColNode, n) as nodes:
            from Models.Block import Block
            for nd in nodes:
                nd.blockchain = [Block()]
            assert math.isclose(sum(nd.hash_rate_hps() for nd in nodes),
                                NET_HPS, rel_tol=1e-12)
            for nd in nodes:
                nd.start_mining(0, 0.0)
            PoColNode.finalize_energy(T_SIM)
            totals.append(sum(nd.energy_kwh for nd in nodes))
    for t in totals:
        assert math.isclose(t, EXPECTED_KWH, rel_tol=REL), t
    assert abs(totals[0] - totals[1]) < 1e-9


def test_pocol_apply_energy_hook_is_noop():
    # The deprecated block_time/N hook must not add energy.
    from Models.PoCol.Consensus import Consensus
    with homogeneous_network(PoColNode, 50) as nodes:
        from Models.Block import Block
        for nd in nodes:
            nd.blockchain = [Block()]
        before = sum(nd.energy_kwh for nd in nodes)
        b = Block(); b.previous = nodes[0].last_block().id; b.id = 12345
        assert Consensus.apply_energy_for_created_block(b) is None
        after = sum(nd.energy_kwh for nd in nodes)
        assert before == after == 0.0
