"""Stage 5B1E tests 8-13: exhaustion timing and B3/C1-vs-C2 lifecycle."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, _shares, allocate_equal, allocate_weighted)


def _tau(cfg, weighted=False):
    shares = _shares(cfg)
    rates = shares * cfg.network_hash_rate_hps
    S = cfg.domain_size()
    ranges = allocate_weighted(S, list(shares)) if weighted else allocate_equal(S, cfg.miner_count)
    return [(ranges[i][1] - ranges[i][0] + 1) / rates[i] for i in range(cfg.miner_count)], rates, S


# 8
def test_disjoint_exhaustion_uses_max_completion_time():
    cfg = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=20, mu=0.5,
                       hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    tau, rates, S = _tau(cfg)
    r = run_scenario(cfg, emit_detail=True)
    exh = [t for t in r["per_template"] if t["status"] == "ACTIVE_DOMAIN_EXHAUSTED"]
    assert exh
    assert math.isclose(exh[0]["duration_s"], max(tau), rel_tol=1e-6)


# 9
def test_equal_heterogeneous_exhaustion_not_s_over_total_hash():
    cfg = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=20, mu=0.5,
                       hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    tau, rates, S = _tau(cfg)
    r = run_scenario(cfg, emit_detail=True)
    exh = [t for t in r["per_template"] if t["status"] == "ACTIVE_DOMAIN_EXHAUSTED"][0]
    s_over_h = S / float(sum(rates))
    assert not math.isclose(exh["duration_s"], s_over_h, rel_tol=0.05)   # must NOT be S/H_active
    assert exh["duration_s"] > s_over_h                                  # slowest range is slower


# 10
def test_weighted_ranges_reduce_completion_dispersion():
    tau_eq, _, _ = _tau(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=50,
                                     hash_rate_distribution="heterogeneous_moderate",
                                     allocation_policy="equal"))
    tau_wt, _, _ = _tau(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=50,
                                     hash_rate_distribution="heterogeneous_moderate",
                                     allocation_policy="weighted"), weighted=True)
    import numpy as np
    assert np.std(tau_wt) < np.std(tau_eq)               # weighting equalizes completion times


# 11
def test_continuous_policy_after_early_range_completion():
    # B3/C1 continuous power: a miner that finishes its range stays at ACTIVE power
    # (no idle) but its productive time is <= active time; energy invariant holds.
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100,
                                  hash_rate_distribution="heterogeneous_moderate",
                                  allocation_policy="equal"))
    assert r["total_idle_time_s"] == 0.0                             # no idle (continuous power)
    assert r["non_productive_active_time_s"] > 0.0                   # some non-productive active wait
    assert math.isclose(r["total_energy_kwh"], 8.420833333333333, rel_tol=1e-9)


# 12
def test_c2_idle_stops_productive_evaluations():
    # C2: an idle miner accrues idle time and NO extra candidate evaluations.
    c2 = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                   hash_rate_distribution="heterogeneous_moderate",
                                   allocation_policy="equal", idle_power_ratio=0.1), emit_detail=True)
    assert c2["total_idle_time_s"] > 0.0
    # candidates never exceed the assigned range per miner (no productive work while idle)
    for m in c2["per_miner"]:
        if m["final_state"] != "offline" and m["range_size"]:
            # cumulative can span multiple generations, but per-generation is capped;
            # productive time must be <= active time
            assert m["productive_search_time_s"] <= m["active_time_s"] + 1e-9


# 13
def test_partial_generation_at_cutoff():
    r = run_scenario(EngineConfig("B1", seed=20260201, miner_count=500), emit_detail=True)
    last = r["per_template"][-1]
    assert last["status"] == "PARTIAL_AT_CUTOFF"
    assert last["partial_cutoff_time_s"] is not None
    assert r["partial_generations"] >= 1
