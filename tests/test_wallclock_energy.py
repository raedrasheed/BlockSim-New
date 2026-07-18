"""Phase B1 — wall-clock energy integration invariants.

Enforces that energy is integrated once over simulation wall-clock time and is
independent of block/stale/event counts, for both the PoW baseline and PoCol.

Physical reference (NetworkHashRate_Hps=141e12, MinerEfficiency_J_per_TH=21.5,
simTime=10000):  P_network = 3031.5 W ;  E_continuous = 8.420833333 kWh,
independent of miner count.

Run:  python -m pytest tests/ -v   or   python tests/test_wallclock_energy.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node as PoWNode
from Models.PoCol.Node import Node as PoColNode

NET_HPS = 141e12
EFF_J_PER_TH = 21.5
SIM_TIME = 10000.0
P_NETWORK_W = NET_HPS * (EFF_J_PER_TH / 1e12)          # 3031.5 W
E_CONTINUOUS_KWH = P_NETWORK_W * SIM_TIME / 3_600_000.0  # 8.420833333 kWh
REL = 1e-9
MINER_COUNTS = [1, 50, 100, 200, 300, 400, 500]


def _install(node_cls, n):
    p.HashPowerIsShare = True
    p.NetworkHashRate_Hps = NET_HPS
    p.MinerEfficiency_J_per_TH = EFF_J_PER_TH
    p.GridEF_kgCO2e_per_kWh = 0.445
    p.simTime = SIM_TIME
    p.NODES = [node_cls(id=i, hashPower=1) for i in range(n)]
    return p.NODES


def _continuous_run(nodes, sim_time=SIM_TIME):
    """All miners ACTIVE for [0, sim_time], then finalized (as genesis+finalize do)."""
    for nd in nodes:
        nd.begin_mining(0.0)
    for nd in nodes:
        nd.finalize_energy(sim_time)


def _close(a, b, msg):
    assert abs(a - b) <= REL * max(abs(b), 1.0), f"{msg}: got {a}, expected {b}"


# 1. hash-rate conservation
def test_hashrate_conservation():
    for cls, name in [(PoWNode, "PoW"), (PoColNode, "PoCol")]:
        for n in MINER_COUNTS:
            nodes = _install(cls, n)
            agg = sum(nd._effective_hashrate_hps() for nd in nodes)
            _close(agg, NET_HPS, f"{name} sum H_i (N={n})")


# 2. power conservation
def test_power_conservation():
    for cls, name in [(PoWNode, "PoW"), (PoColNode, "PoCol")]:
        for n in MINER_COUNTS:
            nodes = _install(cls, n)
            for nd in nodes:
                nd.begin_mining(0.0)
            agg = sum(nd.power_watts for nd in nodes)
            _close(agg, P_NETWORK_W, f"{name} sum P_i (N={n})")


# 3 & 7. continuous mining == 8.420833 kWh for every N, both protocols
def test_continuous_energy_is_fixed_for_all_N():
    for cls, name in [(PoWNode, "PoW"), (PoColNode, "PoCol")]:
        for n in MINER_COUNTS:
            nodes = _install(cls, n)
            _continuous_run(nodes)
            agg_kwh = sum(nd.energy_kwh for nd in nodes)
            _close(agg_kwh, E_CONTINUOUS_KWH, f"{name} continuous energy (N={n})")


# 4. per-miner energy never exceeds P_i * simTime
def test_miner_energy_upper_bound():
    for cls in (PoWNode, PoColNode):
        nodes = _install(cls, 300)
        _continuous_run(nodes)
        for nd in nodes:
            assert nd.cumulative_active_time <= SIM_TIME + REL, "active_time exceeds simTime"
            assert nd.cumulative_energy_j <= nd.power_watts * SIM_TIME * (1 + REL) + 1e-6, \
                "miner energy exceeds P_i * simTime"


# 5. aggregate energy never exceeds the physical bound
def test_aggregate_energy_upper_bound():
    for cls in (PoWNode, PoColNode):
        for n in MINER_COUNTS:
            nodes = _install(cls, n)
            _continuous_run(nodes)
            agg = sum(nd.energy_kwh for nd in nodes)
            assert agg <= E_CONTINUOUS_KWH * (1 + 1e-9) + 1e-9, \
                f"aggregate energy {agg} exceeds bound {E_CONTINUOUS_KWH} (N={n})"


# 6. repeated/overlapping updates never re-charge an already-counted interval
def test_no_double_counting_on_repeated_updates():
    nodes = _install(PoColNode, 100)
    for nd in nodes:
        nd.begin_mining(0.0)
    # advance to 5000 via many out-of-order / repeated checkpoints
    for nd in nodes:
        nd.update_energy(1000.0)
        nd.update_energy(1000.0)   # same time: no-op
        nd.update_energy(500.0)    # backwards: no-op
        nd.update_energy(5000.0)
        nd.update_energy(2500.0)   # backwards: no-op
        nd.finalize_energy(SIM_TIME)
    agg = sum(nd.energy_kwh for nd in nodes)
    _close(agg, E_CONTINUOUS_KWH, "energy after repeated/backward updates")


# finalization actually closes the tail after the last checkpoint
def test_finalization_closes_tail():
    nodes = _install(PoColNode, 100)
    for nd in nodes:
        nd.begin_mining(0.0)
        nd.update_energy(6000.0)          # last "block" at t=6000
    before = sum(nd.energy_kwh for nd in nodes)
    for nd in nodes:
        nd.finalize_energy(SIM_TIME)      # close [6000, 10000]
    after = sum(nd.energy_kwh for nd in nodes)
    _close(before, P_NETWORK_W * 6000.0 / 3.6e6, "energy before finalize")
    _close(after, E_CONTINUOUS_KWH, "energy after finalize")
    assert after > before, "finalization must add the omitted tail interval"


# energy is independent of how many block events fire
def test_energy_independent_of_block_event_count():
    from Models.PoCol.Consensus import Consensus as C

    class _Blk:
        def __init__(s, t): s.id = 1; s.previous = 0; s.timestamp = t
    for n in (100, 300):
        nodes = _install(PoColNode, n)
        for nd in nodes:
            nd.begin_mining(0.0)
        # simulate 500 created-block checkpoints (incl. would-be stale ones)
        for k in range(500):
            C.apply_energy_for_created_block(_Blk(float(k * 20 % int(SIM_TIME))))
        for nd in nodes:
            nd.finalize_energy(SIM_TIME)
        agg = sum(nd.energy_kwh for nd in nodes)
        _close(agg, E_CONTINUOUS_KWH, f"energy vs 500 block events (N={n})")


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
