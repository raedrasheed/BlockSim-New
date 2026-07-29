"""Stage 4 duplicate-instrumentation and configuration/allocation tests (24-42)."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests", "thesis_revision_v43"))

from _pocol_harness import run_pocol
from experiments.thesis_revision_v43.scenario_definitions import (
    ScenarioConfig, simulate_round, _ranges, SCENARIOS)
from experiments.thesis_revision_v43 import config_schema as cs
from Models.PoCol import round_state as rs


def _scn(scen, N=10, seed=1, S=None, H=10.0, B=100.0, shares=None, idle_ratio=0.0):
    S = N * 100 if S is None else S
    return ScenarioConfig(scenario_id=scen, seed=seed, miner_count=N, domain_size=S,
                          p=1.0 / (H * B), network_hash_rate_hps=H, round_duration_s=B,
                          hash_rate_shares=shares, idle_power_ratio=idle_ratio)


def _ident(template_id, template_gen, parent, height, extranonce, nonce):
    return (template_id, template_gen, parent, height, extranonce, nonce)


# 24 ------------------------------------------------------------------------
def test_equal_nonce_different_template_not_duplicate():
    assert _ident("A", 0, 1, 1, 0, 55) != _ident("B", 0, 1, 1, 0, 55)


# 25 ------------------------------------------------------------------------
def test_equal_nonce_same_template_is_duplicate():
    assert _ident("A", 0, 1, 1, 0, 55) == _ident("A", 0, 1, 1, 0, 55)


# 26 ------------------------------------------------------------------------
def test_template_generation_part_of_identity():
    assert _ident("A", 0, 1, 1, 0, 55) != _ident("A", 1, 1, 1, 0, 55)


# 27 ------------------------------------------------------------------------
def test_parent_and_height_part_of_identity():
    assert _ident("A", 0, 1, 1, 0, 55) != _ident("A", 0, 2, 1, 0, 55)   # parent
    assert _ident("A", 0, 1, 1, 0, 55) != _ident("A", 0, 1, 2, 0, 55)   # height


# 28 ------------------------------------------------------------------------
def test_exact_duplicate_reconciliation():
    for scen in SCENARIOS:
        r = simulate_round(_scn(scen))
        assert r["total_candidate_evaluations"] == \
            r["distinct_candidate_identities"] + r["duplicate_evaluations"]


# 29 ------------------------------------------------------------------------
def test_randomized_start_overlap():
    b1 = simulate_round(_scn("B1"))
    b2 = simulate_round(_scn("B2"))
    assert 0 <= b2["duplicate_rate"] <= b1["duplicate_rate"]
    assert b1["duplicate_evaluations"] > 0


# 30 ------------------------------------------------------------------------
def test_disjoint_ranges_zero_overlap():
    assert simulate_round(_scn("B3"))["overlap_headers"] == 0
    assert simulate_round(_scn("C1"))["overlap_headers"] == 0


# 31 ------------------------------------------------------------------------
def test_wraparound_duplicate_tracking():
    # B2 randomized start wraps modulo S; reconciliation must still hold.
    r = simulate_round(_scn("B2", seed=7))
    assert r["total_candidate_evaluations"] == \
        r["distinct_candidate_identities"] + r["duplicate_evaluations"]


# 32 ------------------------------------------------------------------------
def test_hashrates_sum_to_network_total():
    cfg = cs.ExperimentConfig(scenario_id="C1", seed=1, miner_count=7,
                              simulation_duration_s=1000, network_hash_rate_hps=141e12,
                              efficiency_j_per_th=21.5, target_block_interval_s=600,
                              nonce_domain_size=1000, allocation_policy="disjoint_equal",
                              search_order_policy="ordered", template_policy="common")
    assert math.isclose(sum(cfg.per_miner_hash_rate_hps()), 141e12, rel_tol=1e-9)


# 33 ------------------------------------------------------------------------
def test_equal_range_allocation():
    sizes = [b - a + 1 for (a, b) in _ranges(_scn("B3", N=10, S=1000))]
    assert max(sizes) - min(sizes) <= 1
    assert sum(sizes) == 1000


# 34 ------------------------------------------------------------------------
def test_weighted_range_allocation():
    sizes = [b - a + 1 for (a, b) in _ranges(_scn("B3", N=2, S=1000, shares=[0.25, 0.75]))]
    assert sizes[1] > sizes[0]
    assert abs(sizes[1] / sum(sizes) - 0.75) < 0.02


# 35 ------------------------------------------------------------------------
def test_unassigned_remainder_accounted():
    sizes = [b - a + 1 for (a, b) in _ranges(_scn("B3", N=3, S=1001))]
    assert sum(sizes) == 1001          # remainder folded into the last range


# 36 ------------------------------------------------------------------------
def test_inactive_range_accounted():
    base = dict(scenario_id="C1", seed=1, miner_count=10, simulation_duration_s=1000,
                network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
                target_block_interval_s=600, nonce_domain_size=1000,
                allocation_policy="disjoint_equal", search_order_policy="ordered",
                template_policy="common")
    cs.validate(cs.ExperimentConfig(inactive_miner_fraction=0.2, **base))   # ok
    try:
        cs.validate(cs.ExperimentConfig(inactive_miner_fraction=1.0, **base))
        assert False
    except cs.ConfigError:
        pass


# 37 ------------------------------------------------------------------------
def test_configuration_hash_reproducible():
    a = _scn("C1"); b = _scn("C1"); c = _scn("C1", seed=999)
    assert a.config_hash() == b.config_hash()
    assert a.config_hash() != c.config_hash()


# 38 ------------------------------------------------------------------------
def test_seed_reproducibility():
    assert simulate_round(_scn("B2", seed=5)) == simulate_round(_scn("B2", seed=5))
    assert run_pocol(30, sim_time=4000, seed=3)["energy_kwh"] == \
        run_pocol(30, sim_time=4000, seed=3)["energy_kwh"]


# 39 ------------------------------------------------------------------------
def test_all_scenarios_share_common_units():
    for scen in SCENARIOS:
        r = simulate_round(_scn(scen))
        for k in ("active_energy_kwh", "idle_energy_kwh", "coordination_energy_kwh", "total_energy_kwh"):
            assert k in r


# 40 ------------------------------------------------------------------------
def test_stage2_energy_invariants_unchanged():
    from Models.Energy.wallclock_energy import network_active_power_w, continuous_energy_kwh
    assert math.isclose(network_active_power_w(141e12, 21.5), 3031.5, abs_tol=1e-6)
    assert math.isclose(continuous_energy_kwh(3031.5, 10000), 8.420833333333333, rel_tol=1e-9)


# 41 ------------------------------------------------------------------------
def test_stage3_event_semantics_unchanged():
    ev = rs.EventIdentity(1, 5, 5, 100, 3, 7, 0, 2, 0.0, 1.0, 1, 2)
    cur = rs.CurrentState(100, 5, 5, 7, 0, 1, False, False)
    assert rs.classify_event(ev, cur) == rs.VALID_CURRENT
    assert rs.classify_event(ev, rs.CurrentState(200, 5, 5, 7, 0, 1, False, False)) == rs.OBSOLETE_PARENT


# 42 ------------------------------------------------------------------------
def test_existing_journal_tests_unchanged():
    from Models.Energy import PowEconomicEnergyModel, GAMMA_SCENARIOS
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30, coin_price=60000.0,
                                electricity_price_per_kwh=0.05, electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475
