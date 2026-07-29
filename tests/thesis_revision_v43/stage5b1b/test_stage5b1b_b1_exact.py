"""Stage 5B1B tests 1-10: exact B1 zero-block model, reference, and event-loop CI."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario

H, T, TGT, MU = 141e12, 10000.0, 600.0, 2.0


# 1
def test_b1_exact_unique_evaluation_count():
    ex = bx.exact_zero_block(H, 100, T, TGT, MU)
    assert math.isclose(ex["unique_search_rate_hps"], H / 100, rel_tol=1e-12)
    assert math.isclose(ex["expected_unique_candidate_evaluations"], (H / 100) * T, rel_tol=1e-9)


# 2
def test_b1_exact_probability_small_domain():
    # tiny domain: exact (1-p)^M checked against direct product
    H2, N2, T2, tgt2, mu2 = 1000.0, 10, 100.0, 1.0, 1.0
    ex = bx.exact_zero_block(H2, N2, T2, tgt2, mu2)
    p = 1.0 / (H2 * tgt2)
    M = (H2 / N2) * T2
    assert math.isclose(ex["expected_zero_block_probability_exact"], (1 - p) ** M, rel_tol=1e-9)


# 3
def test_b1_exact_probability_multiple_template_generations():
    # force M > S so full generations occur (small target -> large p, small S)
    H2, N2, T2, tgt2, mu2 = 100.0, 2, 1000.0, 1.0, 5.0
    ex = bx.exact_zero_block(H2, N2, T2, tgt2, mu2)
    assert ex["expected_full_template_generations"] >= 1
    total = ex["expected_full_template_generations"] * ex["full_domain_size"] \
        + ex["expected_partial_generation_candidates"]
    assert math.isclose(total, ex["expected_unique_candidate_evaluations"], rel_tol=1e-9)


# 4
def test_b1_partial_final_generation():
    ex = bx.exact_zero_block(H, 100, T, TGT, MU)
    # our production configs cover < one domain -> 0 full generations, 1 partial
    assert ex["expected_full_template_generations"] == 0
    assert math.isclose(ex["expected_partial_generation_candidates"],
                        ex["expected_unique_candidate_evaluations"], rel_tol=1e-12)


# 5
def test_b1_log_probability_numerical_stability():
    # exp(sum log1p) must not underflow to 0 or exceed 1
    for N in (100, 500):
        ex = bx.exact_zero_block(H, N, T, TGT, MU)
        p0 = ex["expected_zero_block_probability_exact"]
        assert 0.0 < p0 < 1.0


# 6
def test_b1_poisson_approximation_reported_separately():
    ex = bx.exact_zero_block(H, 100, T, TGT, MU)
    assert "expected_zero_block_probability_poisson" in ex
    assert "poisson_absolute_error" in ex and "poisson_relative_error" in ex
    # exact and Poisson differ (here only ~1e-17) but are distinct fields
    assert ex["poisson_absolute_error"] >= 0.0


# 7
def test_b1_direct_reference_independent_of_engine():
    # the reference sampler must agree with the exact value WITHOUT the engine
    import inspect
    src = inspect.getsource(bx.direct_reference_sampler)
    assert "run_scenario" not in src and "_discover" not in src
    for N in (100, 500):
        ex = bx.exact_zero_block(H, N, T, TGT, MU)
        dr = bx.direct_reference_sampler(H, N, T, TGT, MU, 100_000, seed=1234 + N)
        lo, hi = bx.clopper_pearson(dr["zeros"], 100_000, 0.01)
        assert lo <= ex["expected_zero_block_probability_exact"] <= hi


# 8
def test_b1_event_loop_zero_frequency_within_99ci():
    seeds = [20261001 + i for i in range(30)]           # disjoint from frozen schedule
    for N in (100, 300, 500):
        zeros = sum(1 for s in seeds
                    if run_scenario(EngineConfig("B1", seed=s, miner_count=N))["accepted_blocks"] == 0)
        p0 = bx.exact_zero_block(H, N, T, TGT, MU)["expected_zero_block_probability_exact"]
        lo, hi = bx.clopper_pearson(zeros, len(seeds), 0.01)
        assert lo <= p0 <= hi, (N, zeros, p0, lo, hi)


# 9
def test_b1_zero_probability_monotone_with_miner_count():
    tab = bx.b1_exact_table()
    p0 = [r["expected_zero_block_probability_exact"] for r in tab]
    assert all(p0[i] < p0[i + 1] for i in range(len(p0) - 1))


# 10
def test_b1_matrix_zero_fields_exact():
    from experiments.thesis_revision_v43 import build_matrix_5b1b as b
    final, _, _ = b.build()
    b1 = [r for r in final if r["scenario_id"] == "B1"]
    for r in b1:
        assert r["expected_zero_block_probability_exact"] is not None
        assert r["expected_zero_block_probability_poisson"] is not None
        assert r["analytical_model_version"] == "b1-exact-1"
        assert r["expected_full_template_generations"] == 0
