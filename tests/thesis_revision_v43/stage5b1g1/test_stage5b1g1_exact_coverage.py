"""Stage 5B1G.1 tests 1-4: exact Fraction/integer B2 coverage — no float time is
used to derive candidate counts (§1)."""

import os
import sys
import math
import inspect
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import coverage as cov
from experiments.thesis_revision_v43 import scenario_engine
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, _completed


# 1
def test_b2_fraction_time_not_converted_to_float_for_counts():
    src = inspect.getsource(scenario_engine._sim_frontier)
    # the float length path is gone; candidate counts come from the exact rational
    # lengths list fed straight into the exact circular union.
    assert "lengths_from_winner_time" not in src            # float-length path removed
    assert "lengths_at_time_exact" in src                   # exact rational lengths used
    assert "b2_coverage_exact(starts, active_lengths" in src  # exact lengths feed coverage
    # eff_end is only ever floated for TIME-output fields, never inside a candidate-count
    # expression: no `float(eff_end)` appears as an argument to a coverage/length call.
    assert "lengths_at_time_exact([rates_int[i] for i in active_ids], eff_end, S)" in src


# 2
def test_b2_exact_lengths_match_per_miner_rows():
    # lengths_at_time_exact is exactly the per-miner-row formula _completed(rate, t, S)
    S = 10 ** 9
    for t in (Fraction(1, 49), Fraction(2, 3), Fraction(123, 7), Fraction(5, 1)):
        rates = [49, 3, 7, 1000, 999999937]
        exact = cov.lengths_at_time_exact(rates, t, S)
        for i, r in enumerate(rates):
            assert exact[i] == _completed(r, t, S)


# 3
def test_b2_network_total_equals_generation_rows_exactly():
    for seed in (5, 7, 11):
        r = run_scenario(EngineConfig("B2", seed=seed, miner_count=12, mu=3.0),
                         emit_detail=True, emit_generation_detail=True)
        s = sum(g["candidates_evaluated_this_generation"] for g in r["per_miner_generation"])
        assert s == r["total_candidate_evaluations"]         # exact integer identity
        assert (r["total_candidate_evaluations"]
                == r["distinct_candidate_identities"] + r["duplicate_evaluations"])


# 4
def test_b2_adversarial_fraction_boundary():
    # rate * t is exactly an integer, but float(t)*rate underflows below it.
    S = 100
    r, t = 49, Fraction(1, 49)                           # 49 * 1/49 == 1 exactly
    exact = cov.lengths_at_time_exact([r], t, S)[0]
    floaty = math.floor(r * float(t))
    assert exact == 1
    assert floaty == 0                                   # float path would undercount
    assert exact != floaty                               # exact arithmetic is required
    # coverage built on the exact lengths agrees with the exact length
    covx = cov.b2_coverage_exact([0], [exact], S)
    assert covx["total_candidate_evaluations"] == 1
