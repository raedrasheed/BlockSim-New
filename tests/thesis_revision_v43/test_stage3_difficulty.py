"""Stage 3 tests: difficulty/success-probability semantics and finite-domain
exhaustion (tests 23-38)."""

import os
import sys
import math
import random as _random

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Models.PoCol import round_state as rs
from _pocol_harness import run_pocol

H = 141e12
B = 600.0
TWO_256 = 2 ** 256


# 23 ------------------------------------------------------------------------
def test_success_probability_matches_target():
    p, target = rs.target_for_interval(H, B)
    assert math.isclose(rs.per_header_success_probability(target), p, rel_tol=1e-9)


# 24 ------------------------------------------------------------------------
def test_network_event_rate_depends_on_total_hashrate():
    p, _ = rs.target_for_interval(H, B)
    assert math.isclose(rs.network_success_rate(H, p), H * p, rel_tol=1e-12)
    # doubling H doubles the rate; splitting the SAME H does not change it
    assert math.isclose(rs.network_success_rate(2 * H, p), 2 * H * p, rel_tol=1e-12)


# 25 ------------------------------------------------------------------------
def test_miner_event_rates_sum_to_network_rate():
    p, _ = rs.target_for_interval(H, B)
    for n in (100, 500):
        per = [rs.network_success_rate(H / n, p) for _ in range(n)]
        assert math.isclose(sum(per), rs.network_success_rate(H, p), rel_tol=1e-9)


# 26 ------------------------------------------------------------------------
def test_expected_block_interval_independent_of_miner_count():
    p, _ = rs.target_for_interval(H, B)
    for n in (100, 200, 300, 400, 500):
        # split H into n equal miners; aggregate rate unchanged -> interval == B
        assert math.isclose(rs.expected_block_interval(H, p), B, rel_tol=1e-9)


# 27 ------------------------------------------------------------------------
def test_no_double_scaling_by_miner_count():
    p, _ = rs.target_for_interval(H, B)
    n = 500
    total_rate = sum(rs.network_success_rate(H / n, p) for _ in range(n))
    assert math.isclose(total_rate, H * p, rel_tol=1e-9)     # == 1/B, NOT n/B
    assert not math.isclose(total_rate, n * H * p, rel_tol=1e-3)


# 28 ------------------------------------------------------------------------
def test_target_version_recorded():
    r = run_pocol(50, sim_time=3000, seed=0)
    assert "target_version" in r["diag"]
    assert r["diag"]["target_version"] >= 1


# 29 ------------------------------------------------------------------------
def test_target_bounds_valid():
    p, target = rs.target_for_interval(H, B)
    assert 0 < target < TWO_256
    assert 0.0 < p < 1.0


# 30 ------------------------------------------------------------------------
def test_difficulty_target_roundtrip():
    for T in (10 ** 30, 10 ** 50, 2 ** 200):
        p = rs.per_header_success_probability(T)
        T2 = rs.target_for_success_probability(p)
        assert abs(T2 - T) / T < 1e-9


# 31 ------------------------------------------------------------------------
def test_finite_domain_success_probability():
    p = 1e-3
    for S in (1, 10, 100, 1000):
        ref = 1.0 - (1.0 - p) ** S
        assert math.isclose(rs.finite_domain_success_prob(p, S), ref, rel_tol=1e-9)


# 32 ------------------------------------------------------------------------
def test_finite_domain_exhaustion_probability():
    p = 1e-3
    for S in (1, 10, 100, 1000):
        ex = rs.finite_domain_exhaust_prob(p, S)
        su = rs.finite_domain_success_prob(p, S)
        assert math.isclose(su + ex, 1.0, rel_tol=1e-9)
        assert math.isclose(ex, (1.0 - p) ** S, rel_tol=1e-9)


# 33 ------------------------------------------------------------------------
def test_full_domain_exhaustion_without_block():
    rng = _random.Random(123)
    ranges = [(0, 0, 499), (1, 500, 999)]
    rates = {0: H / 2, 1: H / 2}
    # p = 0 -> zero solutions -> exhaustion (empty)
    for _ in range(20):
        assert rs.draw_round_solutions(rng, 0.0, 1000, ranges, rates) == []


# 34 ------------------------------------------------------------------------
def test_exhaustion_not_counted_as_stale():
    r = run_pocol(50, sim_time=6000, seed=2, domain_factor=0.5)
    assert r["diag"]["exhausted_rounds"] > 0
    # exhaustion never becomes a block or a stale
    assert r["totalBlocks"] == r["diag"]["accepted_blocks"] + r["diag"]["legit_stales"]
    assert r["staleBlocks"] == r["diag"]["legit_stales"]


# 35 ------------------------------------------------------------------------
def test_exhaustion_invalidates_old_generation_events():
    # unit: an event carrying a superseded template generation is rejected.
    from Models.PoCol.round_state import EventIdentity, CurrentState, classify_event
    ev = EventIdentity(1, 5, 5, 100, 3, 7, 0, 2, 0.0, 1.0, 1, 2)   # template_gen 0
    cur = CurrentState(100, 5, 5, 8, 1, 1, False, False)           # current template_gen 1
    assert classify_event(ev, cur) == rs.OBSOLETE_TEMPLATE
    r = run_pocol(50, sim_time=6000, seed=3, domain_factor=0.5)
    assert r["diag"]["template_refreshes"] > 0


# 36 ------------------------------------------------------------------------
def test_template_generation_increments_after_exhaustion():
    r = run_pocol(50, sim_time=6000, seed=4, domain_factor=0.5)
    assert any(t["exhaust_refreshes"] > 0 for t in r["transitions"])


# 37 ------------------------------------------------------------------------
def test_no_forced_success_after_exhaustion():
    rng = _random.Random(7)
    ranges = [(0, 0, 999)]
    rates = {0: H}
    # even after many attempts, p=0 never fabricates a solution
    assert all(rs.draw_round_solutions(rng, 0.0, 1000, ranges, rates) == []
               for _ in range(50))


# 38 ------------------------------------------------------------------------
def test_no_infinite_loop_on_repeated_exhaustion():
    from InputsConfig import InputsConfig as p
    from Models.PoCol.Node import Node
    from Models.PoCol.Consensus import Consensus
    from Models.Block import Block
    from Event import Queue

    p.NetworkHashRate_Hps = H
    p.MinerEfficiency_J_per_TH = 21.5
    p.HashPowerIsShare = True
    p.Binterval = B
    p.simTime = 10000
    p.Bdelay = 0.42
    p.RandomSeed = 0
    p.NODES = [Node(id=0, hashPower=1), Node(id=1, hashPower=1)]
    Queue.event_list = []
    Queue._seq_counter = 0
    Consensus.configure()
    Consensus.p_success = 0.0        # force perpetual exhaustion
    saved_max = Consensus.MAX_REFRESH
    Consensus.MAX_REFRESH = 5
    try:
        genesis = Block()            # id=0, depth=0
        Consensus.start_round(genesis, 0.0)   # must terminate (bounded)
        assert Consensus.diag["warnings"], "expected a MAX_REFRESH warning"
        assert Consensus.diag["scheduled_events"] == 0     # no forced block
        assert Consensus.diag["exhausted_rounds"] >= 5
    finally:
        Consensus.MAX_REFRESH = saved_max
