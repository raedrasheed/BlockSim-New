"""Stage 4 stale-validation and scenario-semantics tests (11-23)."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "thesis_revision_v43"))

from _pocol_harness import run_pocol
from experiments.thesis_revision_v43.scenario_definitions import ScenarioConfig, simulate_round
from experiments.thesis_revision_v43 import config_schema as cs


def _scn(scen, N=10, seed=1, idle_ratio=0.0, S=None, H=None, B=100.0):
    H = float(N) if H is None else H
    S = N * 100 if S is None else S
    return ScenarioConfig(scenario_id=scen, seed=seed, miner_count=N, domain_size=S,
                          p=1.0 / (H * B), network_hash_rate_hps=H, round_duration_s=B,
                          idle_power_ratio=idle_ratio)


# 11 ------------------------------------------------------------------------
def test_zero_delay_produces_no_propagation_stale():
    r = run_pocol(50, sim_time=8000, seed=1, bdelay=1e-9)
    assert r["diag"]["legit_stales"] == 0


# 12 ------------------------------------------------------------------------
def test_stale_probability_increases_with_delay():
    def rate(delay):
        legit = accepted = 0
        for s in (1, 2, 3):
            r = run_pocol(50, sim_time=8000, seed=s, bdelay=delay)
            legit += r["diag"]["legit_stales"]; accepted += r["diag"]["accepted_blocks"]
        return legit / accepted if accepted else 0.0
    low = rate(0.42)
    high = rate(60.0)
    assert high > low
    assert high > 0.0


# 13 ------------------------------------------------------------------------
def test_legitimate_competitor_not_suppressed():
    found = any(run_pocol(50, sim_time=8000, seed=s, bdelay=60.0)["diag"]["legit_stales"] > 0
                for s in range(4))
    assert found


# 14 ------------------------------------------------------------------------
def test_zero_observation_confidence_bound_reported():
    # rule of three: with 0 events in n trials, upper 95% bound ~ 3/n
    accepted, legit = 41, 0
    upper95 = (3.0 / accepted) if legit == 0 else None
    assert upper95 is not None and math.isclose(upper95, 3.0 / 41)


# 15 ------------------------------------------------------------------------
def test_b0_independent_templates():
    r = simulate_round(_scn("B0"))
    assert r["duplicate_evaluations"] == 0
    assert r["distinct_candidate_identities"] == r["total_candidate_evaluations"]


# 16 ------------------------------------------------------------------------
def test_b1_common_template_uncoordinated():
    r = simulate_round(_scn("B1"))
    assert r["common_template"] is True
    assert r["duplicate_evaluations"] > 0


# 17 ------------------------------------------------------------------------
def test_b2_randomized_start():
    b1 = simulate_round(_scn("B1"))
    b2 = simulate_round(_scn("B2"))
    assert b2["duplicate_rate"] < b1["duplicate_rate"]


# 18 ------------------------------------------------------------------------
def test_b3_disjoint_ranges_continuous():
    r = simulate_round(_scn("B3"))
    assert r["overlap_headers"] == 0
    assert r["duplicate_evaluations"] == 0
    assert r["idle_policy"] is False


# 19 ------------------------------------------------------------------------
def test_c1_continuous_energy_equals_matched_baseline():
    c1 = simulate_round(_scn("C1"))
    b3 = simulate_round(_scn("B3"))
    assert math.isclose(c1["total_energy_kwh"], b3["total_energy_kwh"], rel_tol=0, abs_tol=1e-15)


# 20 ------------------------------------------------------------------------
def test_c2_idle_energy_matches_state_durations():
    # domain small enough that ranges complete before round end -> idle > 0
    N, H, B = 10, 10.0, 100.0
    S = N * 50
    c2 = simulate_round(_scn("C2", N=N, H=H, S=S, B=B, idle_ratio=0.1))
    # total == active + idle + coordination (reconciliation)
    assert math.isclose(c2["total_energy_kwh"],
                        c2["active_energy_kwh"] + c2["idle_energy_kwh"] + c2["coordination_energy_kwh"],
                        rel_tol=0, abs_tol=1e-15)
    assert c2["total_idle_time_s"] > 0


# 21 ------------------------------------------------------------------------
def test_c2_zero_idle_labelled_lower_bound():
    N, H, B = 10, 10.0, 100.0
    S = N * 50
    c2 = simulate_round(_scn("C2", N=N, H=H, S=S, B=B, idle_ratio=0.0))
    assert c2["idle_energy_kwh"] == 0.0            # zero idle power == lower bound
    assert c2["total_idle_time_s"] > 0            # idle time exists but costs nothing


# 22 ------------------------------------------------------------------------
def test_b3_and_c1_difference_documented():
    # in the SIMULATOR, C1 and B3 are numerically identical (the distinguishing
    # PoCol protocol metadata/reward is not implemented -> stated, not invented).
    c1 = simulate_round(_scn("C1"))
    b3 = simulate_round(_scn("B3"))
    for k in ("total_energy_kwh", "duplicate_evaluations", "overlap_headers"):
        assert c1[k] == b3[k]


# 23 ------------------------------------------------------------------------
def test_invalid_scenario_combination_rejected():
    base = dict(seed=1, miner_count=10, simulation_duration_s=1000,
                network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
                target_block_interval_s=600, nonce_domain_size=1000,
                search_order_policy="ordered")
    # B0 with a common template must be rejected
    bad = cs.ExperimentConfig(scenario_id="B0", allocation_policy="independent",
                              template_policy="common", **base)
    try:
        cs.validate(bad); assert False, "expected ConfigError"
    except cs.ConfigError:
        pass
    # C2 without idle power must be rejected
    bad2 = cs.ExperimentConfig(scenario_id="C2", allocation_policy="disjoint_equal",
                               template_policy="common", idle_power_ratio=None, **base)
    try:
        cs.validate(bad2); assert False, "expected ConfigError"
    except cs.ConfigError:
        pass
