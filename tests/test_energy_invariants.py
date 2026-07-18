"""Energy / hash-rate accounting invariants for the PoW baseline and PoCol.

These tests protect against the two accounting defects identified in the
examiner review of the thesis:

  1. PoW baseline hash-rate normalization.
     Each miner's absolute hash rate must be its FRACTION of the configured
     network hash rate, so that the aggregate equals the configured value for
     ANY miner count:  sum_i H_i == NetworkHashRate_Hps.
     (The previous base-Node implementation used a hardcoded `hp / 100.0`, which
     made the aggregate scale with N and be correct only at exactly 100 miners.)

  2. PoCol per-round energy.
     All miners search their disjoint nonce ranges concurrently, so for a round
     of wall-clock duration `block_time` the network energy is
         sum_i E_i == P_network * block_time,
     with NO extra division by the miner count. (The previous PoCol model charged
     block_time / N per miner, injecting an artificial ~1/N energy reduction.)

Run with:  python -m pytest tests/ -v
       or:  python tests/test_energy_invariants.py
"""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import InputsConfig as _cfg_mod
from InputsConfig import InputsConfig as p
from Models.Bitcoin.Node import Node as PoWNode
from Models.PoCol.Node import Node as PoColNode

NET_HPS = 141e12          # configured total network hash rate (H/s)
EFF_J_PER_TH = 21.5       # miner efficiency (J/TH)
EFF_J_PER_HASH = EFF_J_PER_TH / 1e12
P_NETWORK_W = NET_HPS * EFF_J_PER_HASH   # = 3031.5 W
REL = 1e-9

MINER_COUNTS = [1, 50, 100, 200, 300, 400, 500]


def _install_config(node_cls, n):
    """Configure the shared InputsConfig for a homogeneous n-miner network."""
    p.HashPowerIsShare = True
    p.NetworkHashRate_Hps = NET_HPS
    p.MinerEfficiency_J_per_TH = EFF_J_PER_TH
    p.GridEF_kgCO2e_per_kWh = 0.445
    p.NODES = [node_cls(id=i, hashPower=1) for i in range(n)]
    return p.NODES


def _assert_close(a, b, msg):
    assert abs(a - b) <= REL * max(abs(b), 1.0), f"{msg}: {a} != {b}"


def test_pow_aggregate_hashrate_is_fixed():
    """PoW baseline: sum_i H_i == NetworkHashRate_Hps for every miner count."""
    for n in MINER_COUNTS:
        nodes = _install_config(PoWNode, n)
        agg = sum(node._effective_hashrate_hps() for node in nodes)
        _assert_close(agg, NET_HPS, f"PoW aggregate hash rate (N={n})")


def test_pocol_aggregate_hashrate_is_fixed():
    """PoCol: sum_i H_i == NetworkHashRate_Hps for every miner count."""
    for n in MINER_COUNTS:
        nodes = _install_config(PoColNode, n)
        agg = sum(node.get_hashrate_hps() for node in nodes)
        _assert_close(agg, NET_HPS, f"PoCol aggregate hash rate (N={n})")


def test_pocol_aggregate_power_is_fixed():
    """PoCol: sum_i P_i == P_network for every miner count."""
    for n in MINER_COUNTS:
        nodes = _install_config(PoColNode, n)
        agg_w = sum(node.get_power_w() for node in nodes)
        _assert_close(agg_w, P_NETWORK_W, f"PoCol aggregate power (N={n})")


def test_pow_and_pocol_use_the_same_normalization():
    """The two models must agree on aggregate hash rate at every miner count."""
    for n in MINER_COUNTS:
        pow_nodes = _install_config(PoWNode, n)
        pow_agg = sum(node._effective_hashrate_hps() for node in pow_nodes)
        pocol_nodes = _install_config(PoColNode, n)
        pocol_agg = sum(node.get_hashrate_hps() for node in pocol_nodes)
        _assert_close(pow_agg, pocol_agg, f"PoW vs PoCol aggregate hash rate (N={n})")


def test_pocol_round_energy_has_no_artificial_1_over_N():
    """sum_i E_i == P_network * block_time (no extra /N in the time term).

    Reproduces the per-round charge that Consensus.apply_energy_for_created_block
    applies: each concurrently-active miner is charged over `time_share`, which
    must equal block_time (not block_time / N).
    """
    block_time = 123.4  # seconds (arbitrary round duration)
    for n in MINER_COUNTS:
        nodes = _install_config(PoColNode, n)
        # time_share as set by the corrected Consensus model:
        time_share = block_time  # NOT block_time / n
        total_kwh = 0.0
        for node in nodes:
            before = node.energy_kwh
            node.add_energy_for_round(
                parent_id=0, block_id=1, winner_id=0,
                block_time_s=block_time, time_share_s=time_share,
            )
            total_kwh += node.energy_kwh - before
        expected_kwh = (P_NETWORK_W * block_time) / 3_600_000.0
        _assert_close(total_kwh, expected_kwh, f"PoCol round energy (N={n})")


def test_consensus_module_no_longer_divides_time_by_miner_count():
    """Guard: the corrected source must not reintroduce block_time / N."""
    src = open(os.path.join(os.path.dirname(__file__), "..",
                            "Models", "PoCol", "Consensus.py"), encoding="utf-8").read()
    assert "time_share = block_time / float(N)" not in src, \
        "Consensus.py reintroduced the artificial 1/N energy division"


def _run_all():
    tests = [v for k, v in sorted(globals().items())
             if k.startswith("test_") and callable(v)]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"PASS  {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL  {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
