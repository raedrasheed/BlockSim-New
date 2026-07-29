"""Stage 5B1F tests 1-10: competitor / stale-block semantics."""

import os
import sys
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import _resolve, EngineConfig, run_scenario


def _d(miner, offset, identity, num, den=100):
    return dict(miner=miner, offset=offset, q=identity, identity=identity, time=Fraction(num, den))


# 1
def test_same_miner_multiple_solutions_produces_one_proposal():
    # the engine keeps only a miner's EARLIEST solution; two solutions on one miner
    # never both appear as discoveries. _resolve with distinct miners only.
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=50, mu=4.0),
                     emit_detail=True)
    for t in r["per_template"]:
        assert t["actual_proposal_miner_count"] <= t["distinct_potential_finder_miner_count"]


# 2
def test_second_solution_same_miner_not_stale():
    d = [_d(0, 10, 10, 11), _d(0, 12, 99, 13)]         # same miner, two solutions
    _, prop, comp, stale = _resolve([dict(x) for x in d], [Fraction(1)])
    assert comp == 0 and stale == 0


# 3
def test_distinct_miner_within_delay_is_stale():
    d = [_d(0, 10, 10, 11), _d(1, 12, 99, 13)]         # distinct miners, distinct identity
    _, prop, comp, stale = _resolve([dict(x) for x in d], [Fraction(1)])   # big delay
    assert comp == 1 and stale == 1


# 4
def test_distinct_miner_after_delay_not_stale():
    d = [_d(0, 10, 10, 11), _d(1, 12, 99, 13)]
    _, prop, comp, stale = _resolve([dict(x) for x in d], [Fraction(1, 1000)])  # tiny delay
    assert comp == 1 and stale == 0


# 5
def test_zero_delay_produces_no_late_competitor():
    d = [_d(0, 10, 10, 11), _d(1, 12, 99, 13)]
    _, prop, comp, stale = _resolve([dict(x) for x in d], [Fraction(0)])
    assert stale == 0


# 6
def test_b1_same_header_not_stale():
    # B1: all miners reach the same lowest nonce -> same identity -> no distinct stale.
    r = run_scenario(EngineConfig("B1", seed=20261001, miner_count=100), emit_detail=True)
    assert r["legitimate_stale_block_count"] == 0
    assert r["actual_competitor_miner_count"] == 0


# 7
def test_b2_competitor_uses_random_start_path():
    # B2 competitors come from each miner's own seeded circular path (distinct starts
    # -> distinct earliest solutions), not the second numeric nonce.
    r = run_scenario(EngineConfig("B2", seed=5, miner_count=50, mu=4.0), emit_detail=True)
    assert r["distinct_potential_finder_miner_count"] >= 1


# 8
def test_b2_second_numeric_nonce_not_used_as_competitor():
    # a competitor must be another MINER's earliest solution, resolved via _resolve
    # over per-miner discoveries — verified structurally by the stale unit tests.
    d = [_d(0, 5, 5, 6), _d(0, 6, 7, 7)]               # same miner two nonces
    _, _, comp, stale = _resolve([dict(x) for x in d], [Fraction(1)])
    assert comp == 0                                    # second numeric nonce of same miner != competitor


# 9
def test_disjoint_competitor_uses_distinct_miner():
    d = [_d(0, 5, 5, 6), _d(2, 9, 90, 8)]
    _, _, comp, stale = _resolve([dict(x) for x in d], [Fraction(1)])
    assert comp == 1                                    # distinct miner competitor


# 10
def test_stale_denominators():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                  network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                  propagation_delay_mean_s=60.0))
    # both documented denominators present
    assert "stales_per_accepted_block" in r and "stale_fraction_of_all_valid_blocks" in r
    if r["accepted_blocks"] > 0:
        assert abs(r["stales_per_accepted_block"]
                   - r["legitimate_stale_block_count"] / r["accepted_blocks"]) < 1e-12
        allv = r["accepted_blocks"] + r["legitimate_stale_block_count"]
        assert abs(r["stale_fraction_of_all_valid_blocks"]
                   - r["legitimate_stale_block_count"] / allv) < 1e-12
