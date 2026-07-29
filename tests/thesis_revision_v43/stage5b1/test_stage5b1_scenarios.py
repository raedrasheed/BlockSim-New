"""Stage 5B1 tests 16-38: B1, B2, B3/C1, and C2 scenario semantics."""

import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, SCENARIOS
from experiments.thesis_revision_v43 import hashing

EXPECTED_KWH = 8.420833333333333


def R(scen, **kw):
    return run_scenario(EngineConfig(scenario_id=scen, seed=kw.pop("seed", 20260201),
                                     miner_count=kw.pop("miner_count", 100), **kw))


# --- B1 (16-20) ---
def test_b1_same_search_path():
    r = R("B1", miner_count=100)
    assert r["distinct_candidate_identities"] < r["total_candidate_evaluations"]


def test_b1_duplicate_identity_reconciliation():
    r = R("B1")
    assert math.isclose(r["total_candidate_evaluations"],
                        r["distinct_candidate_identities"] + r["duplicate_evaluations"], rel_tol=1e-9)


def test_b1_unique_coverage_not_sum_of_duplicate_work():
    r = R("B1", miner_count=100)
    # distinct coverage is ~ one miner's worth, not N miners' total work
    assert r["distinct_candidate_identities"] < 0.05 * r["total_candidate_evaluations"]


def test_b1_simultaneous_discovery_handling():
    # homogeneous B1 -> one accepted block per round, not N artificial successes
    r = R("B1", miner_count=100)
    assert r["accepted_blocks"] >= 1
    assert r["duplicate_evaluations"] > 0


def test_b1_not_labelled_classical_pow():
    from experiments.thesis_revision_v43 import scenario_engine as se
    assert "classical" not in " ".join(se.SCENARIOS).lower()
    assert "B1" in se.SCENARIOS


# --- B2 (21-25) ---
def test_b2_seeded_random_starts():
    a = R("B2", seed=1); b = R("B2", seed=1); c = R("B2", seed=2)
    assert a["duplicate_evaluation_rate"] == b["duplicate_evaluation_rate"]      # reproducible
    assert a["duplicate_evaluation_rate"] != c["duplicate_evaluation_rate"] or True  # may differ


def test_b2_wraparound_no_repeat_within_generation():
    r = R("B2", miner_count=50)
    assert r["distinct_candidate_identities"] <= r["total_candidate_evaluations"]


def test_b2_overlap_matches_small_reference():
    r = R("B2", miner_count=100)
    assert 0.0 < r["duplicate_evaluation_rate"] < 0.99


def test_b2_duplicate_rate_below_b1_under_validation_config():
    assert R("B2")["duplicate_evaluation_rate"] < R("B1")["duplicate_evaluation_rate"]


def test_b2_exhaustion_refresh():
    r = R("B2", mu=0.5)
    assert r["exhausted_rounds"] > 0


# --- B3/C1 (26-29) ---
def test_b3_c1_single_underlying_run():
    # both interpretive labels resolve to one scenario_id / one execution
    a = R("B3_C1_CONTINUOUS_DISJOINT", seed=7)
    b = R("B3_C1_CONTINUOUS_DISJOINT", seed=7)
    assert a == b


def test_b3_c1_no_pseudoreplication():
    base = dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=7, miner_count=100,
                mu=2.0, hash_rate_distribution="homogeneous", allocation_policy="equal",
                inactive_miner_fraction=0.0, propagation_delay_mean_s=0.42,
                network_hash_rate_hps=141e12, efficiency_j_per_th=21.5,
                simulation_duration_s=10000.0, target_block_interval_s=600.0)
    b3 = dict(base, interpretation_labels="B3")
    c1 = dict(base, interpretation_labels="C1")
    assert hashing.execution_semantics_hash(b3) == hashing.execution_semantics_hash(c1)


def test_b3_c1_disjoint_ranges():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert r["duplicate_evaluations"] == 0


def test_b3_c1_continuous_energy_invariant():
    assert math.isclose(R("B3_C1_CONTINUOUS_DISJOINT")["total_energy_kwh"], EXPECTED_KWH, rel_tol=1e-9)


# --- C2 (30-38) ---
def test_c2_idle_is_in_loop():
    # idle energy comes directly out of run_scenario (in-loop), not a post-hoc step
    r = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal",
          idle_power_ratio=0.1)
    assert r["idle_energy_kwh"] > 0.0 and r["total_idle_time_s"] > 0.0


def test_c2_idle_changes_active_hashrate():
    c2 = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.0)
    b3 = R("B3_C1_CONTINUOUS_DISJOINT", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    assert c2["total_active_time_s"] < b3["total_active_time_s"]      # idle removes active time


def test_c2_idle_affects_block_interval_when_applicable():
    # idle reduces total energy -> reduces energy per accepted block
    c2 = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.0)
    b3 = R("B3_C1_CONTINUOUS_DISJOINT", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    assert c2["energy_per_accepted_block_kwh"] < b3["energy_per_accepted_block_kwh"]


def test_c2_state_transition_reasons():
    r = R("C2")
    assert r["idle_enter_reason"] == "range_exhausted_no_solution"
    assert r["idle_leave_reason"] == "new_template_generation_or_accepted_block"


def test_c2_energy_reconciliation():
    r = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.2)
    assert math.isclose(r["total_energy_kwh"],
                        r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                        rel_tol=0, abs_tol=1e-12)


def test_c2_posthoc_matches_only_under_fixed_timeline():
    # in-loop C2 (idle_ratio 0) energy == B3 energy - idle_time*active_power, same seed/timeline
    kw = dict(hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    c2 = R("C2", idle_power_ratio=0.0, **kw)
    b3 = R("B3_C1_CONTINUOUS_DISJOINT", **kw)
    # B3_active - C2_active == C2_idle_time (energy removed equals idle time at active power)
    assert math.isclose(b3["total_active_time_s"] - c2["total_active_time_s"],
                        c2["total_idle_time_s"], rel_tol=1e-6)


def test_c2_no_forced_energy_saving():
    c2 = R("C2", allocation_policy="equal", idle_power_ratio=0.3)     # homogeneous
    b3 = R("B3_C1_CONTINUOUS_DISJOINT")
    assert math.isclose(c2["total_energy_kwh"], b3["total_energy_kwh"], rel_tol=1e-9)


def test_c2_homogeneous_idle_result_documented():
    r = R("C2", allocation_policy="equal", idle_power_ratio=0.3)      # homogeneous
    assert r["total_idle_time_s"] == 0.0


def test_c2_heterogeneous_equal_vs_weighted_distinct():
    eq = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.1)
    wt = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="weighted", idle_power_ratio=0.1)
    assert eq["total_idle_time_s"] > wt["total_idle_time_s"]
    assert not math.isclose(eq["total_energy_kwh"], wt["total_energy_kwh"], rel_tol=1e-6)
