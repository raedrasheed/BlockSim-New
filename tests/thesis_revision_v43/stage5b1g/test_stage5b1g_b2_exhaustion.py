"""Stage 5B1G tests 28-34: exact B2 exhaustion closure (Section 7)."""

import os
import sys
import math
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import coverage as cov
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario

CASES = [
    (20, [0, 5, 10, 15], [1, 1, 1, 1]),
    (30, [0, 7, 20], [2, 1, 3]),
    (12, [3, 3, 3], [1, 1, 1]),
    (17, [0, 5, 9, 13], [3, 2, 5, 1]),
    (100, [0, 25, 50, 75], [7, 3, 11, 5]),
    (7, [0, 3, 5], [1, 1, 1]),
]


# 28
def test_exact_matches_small_domain_reference():
    for S, starts, rates in CASES:
        exh = cov.b2_exhaustion_time_exact(starts, rates, S)
        t_ex = Fraction(exh["b2_exhaustion_time_fraction_numerator"],
                        exh["b2_exhaustion_time_fraction_denominator"])
        ref = cov.exhaustion_time_reference_small(starts, rates, S)
        assert math.isclose(float(t_ex), ref, rel_tol=0, abs_tol=1e-12)


# 29
def test_exact_exhaustion_verified_true():
    for S, starts, rates in CASES:
        exh = cov.b2_exhaustion_time_exact(starts, rates, S)
        assert exh["exact_exhaustion_verified"] is True


# 30
def test_coverage_proof_pair():
    for S, starts, rates in CASES:
        exh = cov.b2_exhaustion_time_exact(starts, rates, S)
        assert exh["coverage_before_exhaustion"] < S           # not yet covered at t_prev
        assert exh["coverage_at_exhaustion"] == S              # covered exactly at t_ex


# 31
def test_fraction_time_is_exact_rational():
    S, starts, rates = 100, [0, 25, 50, 75], [7, 3, 11, 5]
    exh = cov.b2_exhaustion_time_exact(starts, rates, S)
    num = exh["b2_exhaustion_time_fraction_numerator"]
    den = exh["b2_exhaustion_time_fraction_denominator"]
    # the exact rational (50/7 here) reconstructs the reported float time
    assert math.isclose(num / den, exh["b2_exhaustion_time_s"], rel_tol=0, abs_tol=1e-12)
    # and it is genuinely non-terminating in decimal (not a rounded 6-dp value)
    assert den == 7 and num == 50


# 32
def test_no_six_decimal_rounding():
    # 50/7 = 7.142857142857..., which a 6-decimal rounding would truncate to 7.142857.
    exh = cov.b2_exhaustion_time_exact([0, 25, 50, 75], [7, 3, 11, 5], 100)
    t = Fraction(exh["b2_exhaustion_time_fraction_numerator"],
                 exh["b2_exhaustion_time_fraction_denominator"])
    assert t != Fraction(str(round(float(t), 6)))              # exact != 6-dp rounded


# 33
def test_overlap_delays_exhaustion():
    spread = cov.b2_exhaustion_time_exact([0, 10], [1, 1], 20)
    overlap = cov.b2_exhaustion_time_exact([0, 1], [1, 1], 20)
    ts = Fraction(spread["b2_exhaustion_time_fraction_numerator"],
                  spread["b2_exhaustion_time_fraction_denominator"])
    to = Fraction(overlap["b2_exhaustion_time_fraction_numerator"],
                  overlap["b2_exhaustion_time_fraction_denominator"])
    assert to > ts                                             # overlap wastes work


# 34
def test_engine_b2_exhaustion_records_exact_fields():
    # a low-mu B2 run hits k==0 exhaustion generations; each must carry the exact
    # closure fields with exact_exhaustion_verified True.
    r = run_scenario(EngineConfig("B2", seed=11, miner_count=8, mu=0.5), emit_detail=True)
    exh_rows = [t for t in r["per_template"]
                if t["exhausted"] and t["exact_exhaustion_verified"] is not None]
    assert exh_rows, "expected at least one B2 exhaustion generation"
    for t in exh_rows:
        assert t["exact_exhaustion_verified"] is True
        assert t["coverage_at_exhaustion"] == r["domain_size"]
        assert t["coverage_before_exhaustion"] < r["domain_size"]
        assert t["b2_exhaustion_time_fraction_denominator"] >= 1
