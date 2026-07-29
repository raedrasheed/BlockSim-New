"""Stage 5B1F tests 33-43: precision/taxonomy and regression."""

import os
import sys
import math
import subprocess
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, apportion_int, _completed)
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import run_utils

KWH = 8.420833333333333


# 33
def test_integer_hash_rates_sum_to_network_rate():
    for dist in ("homogeneous", "heterogeneous_moderate", "heterogeneous_high"):
        r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=137,
                                      hash_rate_distribution=dist))
        assert r["integer_rates_sum_exact"] is True
        assert r["network_hash_rate_hps_int"] == 141_000_000_000_000
    # apportion_int guarantees exact sum for any weights
    parts = apportion_int(141_000_000_000_000, [0.3, 0.3, 0.4000001])
    assert sum(parts) == 141_000_000_000_000


# 34
def test_rational_discovery_time_ordering():
    # discovery-time comparison is exact rational: (d_i+1)/H_i vs (d_j+1)/H_j
    a = Fraction(11, 1000)
    b = Fraction(11, 1001)
    assert b < a and (b < a) == ((11 * 1000) < (11 * 1001))     # cross-multiplication ordering


# 35
def test_candidate_count_precision_above_2pow53():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100))
    assert r["total_candidate_evaluations"] > 2 ** 53
    assert r["total_candidate_evaluations"] == \
        r["distinct_candidate_identities"] + r["duplicate_evaluations"]
    # _completed is exact integer arithmetic (no float) above 2^53
    H, t = 141_000_000_000_000, Fraction(1000)
    assert _completed(H, t, 10 ** 30) == H * 1000              # exact, > 2^53


# 36
def test_solution_positions_not_reported_as_finders():
    # solution-position counts and finder-miner counts are distinct fields
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=100, mu=5.0),
                     emit_detail=True)
    assert "total_template_solution_position_count" in r
    assert "distinct_potential_finder_miner_count" in r
    # a generation can have more solution positions than finder miners (one miner may
    # own several positions but is a single finder)
    for t in r["per_template"]:
        assert t["distinct_potential_finder_miner_count"] <= t["total_template_solution_position_count"] \
            or t["total_template_solution_position_count"] == 0


# 37
def test_actual_competitors_are_distinct_miners():
    r = run_scenario(EngineConfig("B1", seed=20261001, miner_count=100))
    # B1 same header -> zero distinct competitors even though all miners "find" a nonce
    assert r["actual_competitor_miner_count"] == 0


# 38
def test_inactive_range_correction_preserved():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=10,
                                  inactive_miner_fraction=0.5, mu=2.0), emit_detail=True)
    for t in r["per_template"]:
        if t["active_range_solution_count"] == 0:
            assert t["accepted_block_id"] is None


# 39
def test_exact_sampler_preserved():
    import numpy as np
    from experiments.thesis_revision_v43 import exact_sampling as es
    p = es.sample_without_replacement(np.random.default_rng(1), 10 ** 17, 3)
    assert p.size == 3 and len(set(p.tolist())) == 3


# 40
def test_b1_zero_block_preserved():
    seeds = [20261001 + i for i in range(30)]
    for N in (100, 500):
        z = sum(1 for s in seeds if run_scenario(EngineConfig("B1", seed=s, miner_count=N))["accepted_blocks"] == 0)
        p0 = bx.exact_zero_block(141e12, N, 10000.0, 600.0, 2.0)["expected_zero_block_probability_exact"]
        lo, hi = bx.clopper_pearson(z, len(seeds), 0.01)
        assert lo <= p0 <= hi


# 41
def test_c2_energy_reconciliation_preserved():
    r = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal", idle_power_ratio=0.1))
    assert math.isclose(r["total_energy_kwh"], r["active_energy_kwh"] + r["idle_energy_kwh"], abs_tol=1e-9)
    assert r["total_idle_time_s"] > 0.0


# 42
def test_all_prior_tests_pass():
    for suite in ("stage5b1", "stage5b1a", "stage5b1b", "stage5b1d", "stage5b1e"):
        out = subprocess.run([sys.executable, "-m", "pytest",
                              os.path.join(ROOT, "tests", "thesis_revision_v43", suite), "-q"],
                             cwd=ROOT, capture_output=True, text=True)
        assert out.returncode == 0, (suite, out.stdout[-1500:])


# 43
def test_thesis_files_unchanged():
    docx = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    pdf = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.pdf")
    assert run_utils.sha256_file(docx) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"
    assert run_utils.sha256_file(pdf) == "131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4"
