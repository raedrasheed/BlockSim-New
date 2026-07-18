"""Disjoint-nonce worst-case experiment — deterministic tests and invariants.

Covers the core M=100/N=10 example (methodology section 2), the twelve required
invariants (section 11), and the partitioning edge cases (section 4).

This experiment is SEPARATE from the corrected continuous-mining comparison; it
does not touch results/corrected/ or the wall-clock energy model.

Run:  python -m pytest tests/test_nonce_partition.py -v
  or:  python tests/test_nonce_partition.py
"""
import os
import sys
import math

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from experiments.nonce_partition.partition import (
    partition_nonce_domain, range_size, ranges_are_disjoint, ranges_cover, owner_of,
)
from experiments.nonce_partition.model import (
    duplicate_full_domain, disjoint_partition,
    duplicate_full_domain_stochastic, disjoint_partition_stochastic,
    independent_candidate_headers_stochastic,
    compare_modes, assert_energy_methods_agree,
    energy_by_attempts, energy_by_power_time, bernoulli_p_from_target,
)

DIVISIBLE = [(100, 10), (1000, 10), (1000, 5), (1000, 2), (1000, 1),
             (1_000_000, 100), (1_000_000, 500)]


# ===========================================================================
# Core example (methodology section 2): M=100, N=10, valid nonce = 99
# ===========================================================================
def test_core_example_M100_N10():
    A = duplicate_full_domain(100, 10, solution="last")
    B = disjoint_partition(100, 10, solution="last")

    # baseline: every miner evaluates all 100 candidates
    assert all(m.attempts == 100 for m in A.miners)
    assert A.total_attempts == 1000
    assert A.total_energy == 1000.0

    # PoCol: every miner evaluates at most 10 candidates
    assert all(m.attempts <= 10 for m in B.miners)
    assert B.total_attempts == 100
    assert B.total_energy == 100.0

    cmp = compare_modes(A, B)
    assert math.isclose(cmp["attempts_ratio"], 0.1)
    assert math.isclose(cmp["energy_ratio"], 0.1)
    assert math.isclose(cmp["energy_reduction_pct"], 90.0)
    assert math.isclose(cmp["time_ratio"], 0.1)             # worst-case wall-clock = 1/10
    assert cmp["duplicate_evaluations_avoided"] == 900


# ===========================================================================
# Invariant 1 — baseline performs N*M attempts in the final-nonce worst case
# ===========================================================================
def test_inv1_baseline_is_N_times_M():
    for M, N in DIVISIBLE + [(100, 7), (100, 3)]:
        A = duplicate_full_domain(M, N, solution="last")
        assert A.total_attempts == N * M, (M, N, A.total_attempts)


# ===========================================================================
# Invariant 2 — PoCol performs exactly M attempts in the same worst case
# ===========================================================================
def test_inv2_pocol_is_exactly_M_when_divisible():
    for M, N in DIVISIBLE:
        B = disjoint_partition(M, N, solution="last")
        assert B.total_attempts == M, (M, N, B.total_attempts)


# ===========================================================================
# Invariant 3 — energy ratio == 1/N when M divisible by N
# ===========================================================================
def test_inv3_energy_ratio_is_one_over_N():
    for M, N in DIVISIBLE:
        A = duplicate_full_domain(M, N, solution="last")
        B = disjoint_partition(M, N, solution="last")
        assert math.isclose(B.total_energy / A.total_energy, 1.0 / N, rel_tol=1e-12)
        assert math.isclose(compare_modes(A, B)["energy_reduction_pct"],
                            100.0 * (1 - 1.0 / N), rel_tol=1e-9)


# ===========================================================================
# Invariant 4 — completion-time ratio == 1/N for equal hash rates
# ===========================================================================
def test_inv4_time_ratio_is_one_over_N():
    for M, N in DIVISIBLE:
        A = duplicate_full_domain(M, N, solution="last")
        B = disjoint_partition(M, N, solution="last")
        assert math.isclose(B.completion_time / A.completion_time, 1.0 / N, rel_tol=1e-12)


# ===========================================================================
# Invariant 5 — no PoCol nonce is evaluated by more than one miner
# ===========================================================================
def test_inv5_pocol_ranges_disjoint():
    for M, N in DIVISIBLE + [(100, 7), (3, 10), (10, 1)]:
        ranges = partition_nonce_domain(0, M, N)
        assert ranges_are_disjoint(ranges), (M, N)
        # cross-check: total distinct nonces covered == sum of range sizes
        assert sum(range_size(r) for r in ranges) == M


# ===========================================================================
# Invariant 6 — every PoCol nonce is evaluated when the domain is exhausted
# ===========================================================================
def test_inv6_full_coverage_on_exhaustion():
    for M, N in DIVISIBLE + [(100, 7)]:
        ranges = partition_nonce_domain(0, M, N)
        assert ranges_cover(ranges, 0, M), (M, N)
        # no-solution run: whole domain scanned exactly once
        B = disjoint_partition(M, N, solution="none")
        assert B.solution_found is False
        assert B.total_attempts == M
        assert all(m.exhausted for m in B.miners if m.range_size > 0)


# ===========================================================================
# Invariant 7 — global stopping prevents post-solution evaluations
# ===========================================================================
def test_inv7_global_stopping():
    # solution at the FIRST nonce -> discovery at step 1 -> every miner does 1 attempt
    A = duplicate_full_domain(1000, 10, solution="first")
    assert A.discovery_step == 1
    assert all(m.attempts == 1 for m in A.miners)
    assert A.total_attempts == 10                       # not 10*1000

    B = disjoint_partition(1000, 10, solution="first")
    assert B.discovery_step == 1
    assert all(m.attempts == 1 for m in B.miners)       # nobody scans past t*
    assert B.total_attempts == 10

    # middle solution: no miner exceeds t* attempts
    C = duplicate_full_domain(1000, 4, solution="middle")
    assert C.discovery_step == 500 + 1
    assert all(m.attempts == C.discovery_step for m in C.miners)


# ===========================================================================
# Invariant 8 — per-attempt and power-time energy accounting agree
# ===========================================================================
def test_inv8_energy_methods_agree():
    for M, N in DIVISIBLE + [(100, 7), (3, 10)]:
        for fn in (duplicate_full_domain, disjoint_partition):
            res = fn(M, N, solution="last")
            assert assert_energy_methods_agree(res)
            for m in res.miners:
                assert math.isclose(energy_by_attempts(m), energy_by_power_time(m),
                                    rel_tol=1e-9, abs_tol=1e-9)
    # stochastic paths too
    for seed in range(5):
        for fn in (duplicate_full_domain_stochastic, disjoint_partition_stochastic,
                   independent_candidate_headers_stochastic):
            assert assert_energy_methods_agree(fn(1_000_000, 50, 5e-6, seed))


# ===========================================================================
# Invariant 9 — one miner produces no saving
# ===========================================================================
def test_inv9_one_miner_no_saving():
    for M in (100, 1000, 1_000_000):
        A = duplicate_full_domain(M, 1, solution="last")
        B = disjoint_partition(M, 1, solution="last")
        cmp = compare_modes(A, B)
        assert A.total_attempts == B.total_attempts == M
        assert math.isclose(cmp["energy_reduction_pct"], 0.0)
        assert math.isclose(cmp["attempts_ratio"], 1.0)


# ===========================================================================
# Invariant 10 — independent headers are not treated as duplicate work
# ===========================================================================
def test_inv10_independent_is_not_duplicate():
    M, N, p = 1_000_000, 100, 5e-6
    dup_tot = ind_tot = 0
    for seed in range(30):
        dup = duplicate_full_domain_stochastic(M, N, p, seed)
        ind = independent_candidate_headers_stochastic(M, N, p, seed)
        # independent work must never be inflated to the N*shared duplicate count
        assert ind.total_attempts <= dup.total_attempts
        dup_tot += dup.total_attempts
        ind_tot += ind.total_attempts
    # on average independent avoids the ~N-fold duplication (well under half)
    assert ind_tot < 0.5 * dup_tot, (ind_tot, dup_tot)


def test_inv10_independent_comparable_to_disjoint_not_to_duplicate():
    """The saving is only vs the duplicate baseline: disjoint ~ independent scale,
    both far below duplicate. (This is the Finding-1 consistency check.)"""
    M, N, p = 1_000_000, 100, 5e-6
    dj = ind = dup = 0
    for seed in range(30):
        dj += disjoint_partition_stochastic(M, N, p, seed).total_attempts
        ind += independent_candidate_headers_stochastic(M, N, p, seed).total_attempts
        dup += duplicate_full_domain_stochastic(M, N, p, seed).total_attempts
    # disjoint and independent are the same order of magnitude (within ~1 decade)...
    assert 0.1 < (dj / ind) < 10.0, (dj, ind)
    # ...and both are far below the duplicate baseline (no N-fold duplication)
    assert dj < 0.2 * dup and ind < 0.2 * dup


# ===========================================================================
# Invariant 11 — very large domains handled analytically (no enumeration)
# ===========================================================================
def test_inv11_large_domains_analytical():
    # baseline count and coverage hold for arbitrarily large domains (no enumeration)
    for M in (2**32, 2**64, 2**128):
        N = 500
        A = duplicate_full_domain(M, N, solution="last")
        B = disjoint_partition(M, N, solution="last")
        assert A.total_attempts == N * M               # exact big-int product
        assert B.total_attempts <= M                   # covered at most once
        assert ranges_cover(partition_nonce_domain(0, M, N), 0, M)
    # divisible large domains give exactly M (2^32/256, 2^40/1024)
    for M, N in [(2**32, 256), (2**40, 1024)]:
        B = disjoint_partition(M, N, solution="last")
        assert B.total_attempts == M, (M, N, B.total_attempts)


def test_inv11_target_probability_bigint():
    p = bernoulli_p_from_target(2**224 - 1, bits=256)   # exact big-int arithmetic
    assert 0.0 < p < 1.0


# ===========================================================================
# Invariant 12 — fixed seeds reproduce identical results
# ===========================================================================
def test_inv12_seed_reproducibility():
    M, N, p = 1_000_000, 100, 5e-6
    for seed in (0, 1, 7, 42):
        for fn in (duplicate_full_domain_stochastic, disjoint_partition_stochastic,
                   independent_candidate_headers_stochastic):
            r1 = fn(M, N, p, seed).to_dict()
            r2 = fn(M, N, p, seed).to_dict()
            assert r1 == r2, (fn.__name__, seed)


def test_inv12_stochastic_A_and_B_are_paired():
    """A and B at the same seed see the SAME shared first-success position."""
    M, N, p = 1_000_000, 100, 5e-6
    for seed in range(10):
        A = duplicate_full_domain_stochastic(M, N, p, seed)
        B = disjoint_partition_stochastic(M, N, p, seed)
        assert A.winning_nonce == B.winning_nonce, seed


# ===========================================================================
# Partitioning edge cases (methodology section 4)
# ===========================================================================
def test_partition_divisible():
    r = partition_nonce_domain(0, 100, 10)
    assert [range_size(x) for x in r] == [10] * 10
    assert ranges_cover(r, 0, 100)


def test_partition_not_divisible():
    r = partition_nonce_domain(0, 100, 7)
    sizes = [range_size(x) for x in r]
    assert max(sizes) - min(sizes) <= 1          # differ by at most one
    assert sum(sizes) == 100
    assert ranges_cover(r, 0, 100)


def test_partition_M_less_than_N():
    r = partition_nonce_domain(0, 3, 10)
    sizes = [range_size(x) for x in r]
    assert sizes == [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
    assert ranges_cover(r, 0, 3)


def test_partition_one_miner():
    r = partition_nonce_domain(0, 100, 1)
    assert r == [(0, 100)]
    assert ranges_cover(r, 0, 100)


def test_partition_very_large_domain():
    M, N = 2**32, 500
    r = partition_nonce_domain(0, M, N)
    assert len(r) == N
    assert ranges_are_disjoint(r)
    assert ranges_cover(r, 0, M)
    assert max(range_size(x) for x in r) - min(range_size(x) for x in r) <= 1


def test_partition_no_overlap_and_coverage_random_sizes():
    for M, N in [(1, 1), (5, 5), (5, 3), (13, 4), (10**9, 333)]:
        r = partition_nonce_domain(0, M, N)
        assert ranges_are_disjoint(r), (M, N)
        assert ranges_cover(r, 0, M), (M, N)


def test_partition_invalid_inputs():
    try:
        partition_nonce_domain(0, 100, 0)
        assert False, "expected ValueError for miner_count=0"
    except ValueError:
        pass


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
