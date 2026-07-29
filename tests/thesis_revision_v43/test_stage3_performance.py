"""Stage 3 tests: performance/regression and seeded block-interval validation
(tests 39-44 + section 13)."""

import os
import sys
import math
import inspect
import random as _random
import statistics as _stats

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Models.PoCol import round_state as rs
from _pocol_harness import run_pocol, cached_run

H = 141e12
B = 600.0
EXPECTED_KWH = 3031.5 * 10000.0 / 3_600_000.0     # 8.420833...


# 39 ------------------------------------------------------------------------
def test_event_queue_does_not_grow_from_repeated_obsolete_generations():
    for n in (100, 500):
        r = cached_run(n)
        # peak is O(N) (a single propagation burst), not O(N * blocks)
        assert r["diag"]["queue_peak"] <= 2 * n + 200, (n, r["diag"]["queue_peak"])
        # processed events are a small multiple of accepted blocks, not N per round
        assert r["diag"]["scheduled_events"] < n


# 40 ------------------------------------------------------------------------
def test_buffered_logging_preserves_event_counts():
    # energy log is buffered in memory and is deterministic for a fixed seed;
    # identical seeded runs preserve the exact row count (nothing dropped).
    a = run_pocol(80, sim_time=8000, seed=11)
    b = run_pocol(80, sim_time=8000, seed=11)
    assert a["energylog_rows"] == b["energylog_rows"] > 0


# 41 ------------------------------------------------------------------------
def test_high_miner_count_diagnostic_completes():
    r = run_pocol(300, sim_time=10000, seed=0)   # previously did not complete
    assert r["mainBlocks"] > 0
    assert r["staleBlocks"] == r["diag"]["legit_stales"]
    assert r["diag"]["queue_peak"] <= 2 * 300 + 200


# 42 ------------------------------------------------------------------------
def test_stage2_energy_invariants_unchanged():
    for n in (100, 500):
        r = cached_run(n)
        assert math.isclose(r["energy_kwh"], EXPECTED_KWH, rel_tol=1e-6), (n, r["energy_kwh"])


# 43 ------------------------------------------------------------------------
def test_existing_journal_tests_unchanged():
    from Models.Energy import (PowEconomicEnergyModel, PosValidatorEnergyModel,
                               CarbonFootprintModel, GAMMA_SCENARIOS)
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30,
                                coin_price=60000.0, electricity_price_per_kwh=0.05,
                                electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475
    pos = PosValidatorEnergyModel(validator_count=1000, validator_power_watts=100.0,
                                  simulation_time_hours=24.0, uptime_ratio=1.0)
    assert math.isclose(pos.total_energy_kwh(), 2400.0, rel_tol=1e-9)


# 44 ------------------------------------------------------------------------
def test_original_pow_semantics_not_accidentally_replaced_by_pocol_logic():
    import Models.Bitcoin.Consensus as btc
    import Models.PoCol.Consensus as pocol
    btc_src = inspect.getsource(btc)
    pocol_src = inspect.getsource(pocol)
    # PoW keeps its unbounded exponential waiting-time abstraction
    assert "expovariate" in btc_src
    # PoCol uses the finite-domain finder model (distinct code path)
    assert "draw_round_solutions" in inspect.getsource(pocol) or "start_round" in pocol_src
    # PoW consensus does not import or depend on the PoCol round model
    assert "round_state" not in btc_src
    assert "PoCol" not in btc_src


# ---- Section 13: seeded block-interval validation ------------------------
def interval_validation(seed=20260729, n_samples=200_000):
    """Sample the unbounded exponential waiting-time abstraction (lambda=H*p=1/B)
    and report mean/SE/CI vs the target interval B."""
    p, _ = rs.target_for_interval(H, B)
    lam = rs.network_success_rate(H, p)     # = 1/B
    rng = _random.Random(seed)
    xs = [rng.expovariate(lam) for _ in range(n_samples)]
    mean = _stats.fmean(xs)
    sd = _stats.pstdev(xs)
    se = sd / math.sqrt(n_samples)
    return dict(seed=seed, n_samples=n_samples, expected_mean=1.0 / lam,
                observed_mean=mean, std=sd, standard_error=se,
                ci95_low=mean - 1.96 * se, ci95_high=mean + 1.96 * se,
                rel_error=abs(mean - 1.0 / lam) / (1.0 / lam))


def test_block_interval_analytical_matches_target():
    p, _ = rs.target_for_interval(H, B)
    assert math.isclose(rs.expected_block_interval(H, p), B, rel_tol=1e-12)


def test_block_interval_seeded_sampling_consistent():
    rep = interval_validation()
    # observed mean within 4 standard errors of the configured target
    assert abs(rep["observed_mean"] - B) <= 4.0 * rep["standard_error"]
    assert rep["rel_error"] < 0.01
    assert rep["ci95_low"] <= B <= rep["ci95_high"]
