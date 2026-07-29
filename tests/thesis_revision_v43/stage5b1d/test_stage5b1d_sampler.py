"""Stage 5B1D tests 1-17: exact without-replacement sampler."""

import os
import sys
import inspect
from math import comb
from itertools import combinations

import numpy as np

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43 import exact_sampling as es
from experiments.thesis_revision_v43.scenario_engine import rng, EngineConfig, run_scenario


def _g(seed=1):
    return np.random.default_rng(seed)


# 1
def test_exact_position_count_equals_k():
    for S, k in [(10, 3), (100, 7), (10 ** 15, 4), (10 ** 17, 2)]:
        assert es.sample_without_replacement(_g(), S, k).size == k


# 2
def test_solution_positions_are_unique():
    for S, k in [(10, 3), (50, 25), (10 ** 12, 6)]:
        pos = es.sample_without_replacement(_g(3), S, k)
        assert len(set(pos.tolist())) == k


# 3
def test_k_zero():
    p = es.sample_without_replacement(_g(), 10, 0)
    assert p.size == 0 and p.dtype == np.int64


# 4
def test_k_one():
    p = es.sample_without_replacement(_g(5), 10 ** 17, 1)
    assert p.size == 1 and 0 <= int(p[0]) < 10 ** 17


# 5
def test_k_equals_domain_size():
    p = es.sample_without_replacement(_g(), 8, 8)
    assert sorted(p.tolist()) == list(range(8))


# 6
def test_k_near_domain_size():
    p = es.sample_without_replacement(_g(2), 10, 9)
    assert p.size == 9 and len(set(p.tolist())) == 9


# 7
def test_invalid_k_negative_rejected():
    try:
        es.sample_without_replacement(_g(), 10, -1)
        assert False
    except ValueError:
        pass


# 8
def test_invalid_k_above_domain_rejected():
    try:
        es.sample_without_replacement(_g(), 10, 11)
        assert False
    except ValueError:
        pass


# 9
def test_large_domain_small_k_without_domain_allocation():
    # if this allocated an array of size 1e17 it would OOM/hang; it must be O(k)
    p = es.sample_without_replacement(_g(9), 10 ** 17, 3)
    assert p.size == 3 and all(0 <= int(x) < 10 ** 17 for x in p)


# 10
def test_same_named_stream_reproducible():
    a = es.sample_without_replacement(rng(7, "solution_positions"), 10 ** 9, 5)
    b = es.sample_without_replacement(rng(7, "solution_positions"), 10 ** 9, 5)
    assert np.array_equal(a, b)


# 11
def test_different_streams_change_sample():
    a = es.sample_without_replacement(rng(7, "solution_positions"), 10 ** 9, 5)
    c = es.sample_without_replacement(rng(8, "solution_positions"), 10 ** 9, 5)
    assert not np.array_equal(a, c)


# 12
def test_uniform_subsets_s5_k2():
    from scipy.stats import chi2
    S, k, N = 5, 2, 200_000
    counts = {frozenset(c): 0 for c in combinations(range(S), k)}
    g = rng(4242, "solution_positions")
    for _ in range(N):
        counts[frozenset(es.sample_without_replacement(g, S, k).tolist())] += 1
    exp = N / comb(S, k)
    chisq = sum((o - exp) ** 2 / exp for o in counts.values())
    assert chisq < float(chi2.ppf(0.999, comb(S, k) - 1))


# 13
def test_uniform_subsets_s6_k3():
    from scipy.stats import chi2
    S, k, N = 6, 3, 300_000
    counts = {frozenset(c): 0 for c in combinations(range(S), k)}
    g = rng(4242, "solution_positions")
    for _ in range(N):
        counts[frozenset(es.sample_without_replacement(g, S, k).tolist())] += 1
    exp = N / comb(S, k)
    chisq = sum((o - exp) ** 2 / exp for o in counts.values())
    assert chisq < float(chi2.ppf(0.999, comb(S, k) - 1))


# 14
def test_minimum_position_distribution():
    # P(min = m) = C(S-1-m, k-1)/C(S,k); compare empirical to exact combinatorial
    S, k, N = 10, 3, 200_000
    g = rng(99, "solution_positions")
    mins = {}
    for _ in range(N):
        m = int(es.sample_without_replacement(g, S, k)[0])
        mins[m] = mins.get(m, 0) + 1
    tot = comb(S, k)
    err = max(abs(mins.get(m, 0) / N - comb(S - 1 - m, k - 1) / tot) for m in range(S - k + 1))
    assert err < 0.01


# 15
def test_no_sorted_oversample_truncation():
    src = inspect.getsource(es)
    assert "size=k * 2" not in src and "size=k*2" not in src
    eng = inspect.getsource(__import__(
        "experiments.thesis_revision_v43.scenario_engine", fromlist=["run_scenario"]).run_scenario)
    assert "[:k]" not in eng


# 16
def test_no_with_replacement_unique_dedup():
    eng = inspect.getsource(__import__(
        "experiments.thesis_revision_v43.scenario_engine", fromlist=["run_scenario"]).run_scenario)
    # the engine must NOT sample positions via np.unique(integers(...))
    assert "np.unique(r_solpos.integers" not in eng
    assert "sample_without_replacement" in eng


# 17
def test_binomial_count_equals_position_count():
    S = int(round(2.0 / (1.0 / (141e12 * 600)))); p = 1.0 / (141e12 * 600)
    for s in range(500):
        gk = rng(20260201 + s, "solution_count"); gp = rng(20260201 + s, "solution_positions")
        k = int(gk.binomial(S, p))
        if k == 0:
            continue
        pos = es.sample_without_replacement(gp, S, k)
        assert pos.size == k == len(set(pos.tolist()))
