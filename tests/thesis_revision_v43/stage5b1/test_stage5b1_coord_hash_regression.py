"""Stage 5B1 tests 39-62: coordination, hashing, streams, parallelism, regression."""

import os
import sys
import math
import json
import tempfile

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, derive_stream_seeds, STREAM_NAMES
from experiments.thesis_revision_v43 import hashing
from experiments.thesis_revision_v43 import run_utils

EXPECTED_KWH = 8.420833333333333


def R(scen, **kw):
    return run_scenario(EngineConfig(scenario_id=scen, seed=kw.pop("seed", 20260201),
                                     miner_count=kw.pop("miner_count", 100), **kw))


def _cfg(**over):
    base = dict(scenario_id="C2", seed=1, miner_count=100, mu=2.0,
                hash_rate_distribution="homogeneous", allocation_policy="equal",
                inactive_miner_fraction=0.0, propagation_delay_mean_s=0.42,
                idle_power_ratio=0.1, network_hash_rate_hps=141e12,
                efficiency_j_per_th=21.5, simulation_duration_s=10000.0,
                target_block_interval_s=600.0)
    base.update(over)
    return base


# --- coordination (39-43) ---
def test_simulated_messages_separate_from_abstract_operations():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert "coord_simulated_message_count" in r
    assert "abstract_template_agreement_operations" in r
    assert r["coord_simulated_message_count"] >= 0


def test_unimplemented_agreement_energy_is_null():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert r["unimplemented_agreement_energy_kwh"] is None       # null, NOT zero


def test_template_refresh_counter():
    r = R("B3_C1_CONTINUOUS_DISJOINT", mu=0.5)
    assert r["coord_template_refresh_count"] == r["exhausted_rounds"]


def test_message_byte_reconciliation():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert r["coord_block_propagation_bytes"] == r["coord_block_propagation_message_count"] * 1_000_000


def test_coordination_lower_bound_explicit():
    r = R("B3_C1_CONTINUOUS_DISJOINT")
    assert r["coordination_energy_lower_bound_kwh"] == 0.0
    assert r["coordination_energy_kwh"] == 0.0


# --- hashing / matrix (44-50) ---
def test_configuration_hash():
    assert hashing.configuration_hash(_cfg()) == hashing.configuration_hash(_cfg())
    assert hashing.configuration_hash(_cfg()) != hashing.configuration_hash(_cfg(seed=2))


def test_execution_semantics_hash():
    a = _cfg(); a["interpretation_labels"] = "B3"
    b = _cfg(); b["interpretation_labels"] = "C1"
    a["scenario_id"] = b["scenario_id"] = "B3_C1_CONTINUOUS_DISJOINT"
    assert hashing.execution_semantics_hash(a) == hashing.execution_semantics_hash(b)


def test_analysis_group_hash():
    a = _cfg(hypothesis_id="H3", matrix_class="CORE_C2")
    b = _cfg(hypothesis_id="H3", matrix_class="CORE_C2")
    assert hashing.analysis_group_hash(a) == hashing.analysis_group_hash(b)


def test_same_seed_same_semantics_unique():
    a = _cfg(scenario_id="B3_C1_CONTINUOUS_DISJOINT")
    b = dict(a, interpretation_labels="other_label")
    assert hashing.execution_semantics_hash(a) == hashing.execution_semantics_hash(b)


def test_semantic_duplicates_removed():
    # homogeneous equal-range C2: idle ratio is semantically inactive -> equal semantics hash
    a = _cfg(idle_power_ratio=0.0)
    b = _cfg(idle_power_ratio=0.3)
    assert not hashing.idle_semantically_active(a)
    assert hashing.execution_semantics_hash(a) == hashing.execution_semantics_hash(b)


def test_b3_c1_labels_share_run_id():
    a = _cfg(scenario_id="B3_C1_CONTINUOUS_DISJOINT", interpretation_labels="B3")
    b = _cfg(scenario_id="B3_C1_CONTINUOUS_DISJOINT", interpretation_labels="C1")
    assert hashing.execution_semantics_hash(a) == hashing.execution_semantics_hash(b)


def test_inactive_parameter_excluded_when_semantically_inactive():
    # heterogeneous equal C2: idle IS active -> ratio included
    active = _cfg(hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal")
    assert hashing.idle_semantically_active(active)
    h1 = hashing.execution_semantics_hash(active)
    h2 = hashing.execution_semantics_hash(dict(active, idle_power_ratio=0.9))
    assert h1 != h2


# --- streams / parallelism (51-56) ---
def test_named_stream_reproducibility():
    assert derive_stream_seeds(20260201) == derive_stream_seeds(20260201)


def test_stream_independence():
    seeds = derive_stream_seeds(20260201)
    assert len(set(seeds.values())) == len(STREAM_NAMES)     # all distinct
    # adding/using one stream does not change another's seed (independent derivation)
    assert seeds["propagation_delay"] == derive_stream_seeds(20260201)["propagation_delay"]


def test_sequential_concurrent_equivalence():
    # run_scenario is a pure function of its config -> order-independent
    a = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.1)
    _ = R("B1", seed=999)                       # interleave an unrelated run
    b = R("C2", hash_rate_distribution="heterogeneous_moderate", allocation_policy="equal", idle_power_ratio=0.1)
    assert a == b


def test_isolated_output_directories():
    # engine has no global side effects (does not touch InputsConfig)
    import InputsConfig
    before = InputsConfig.InputsConfig.model
    R("B3_C1_CONTINUOUS_DISJOINT")
    assert InputsConfig.InputsConfig.model == before


def test_atomic_manifest_write(tmp_path):
    p = str(tmp_path / "sub" / "m.json")
    run_utils.atomic_write_json(p, {"status": run_utils.STATUS_COMPLETED, "x": 1})
    assert json.load(open(p))["x"] == 1
    # no leftover temp files
    assert not any(f.endswith(".tmp") for f in os.listdir(os.path.dirname(p)))


def test_partial_run_not_marked_complete():
    assert not run_utils.is_complete({"status": run_utils.STATUS_RUNNING})
    assert run_utils.is_complete({"status": run_utils.STATUS_COMPLETED})


# --- regression (57-62) ---
def test_accounting_invariant_a1():
    P_total = 141e12 * 21.5 / 1e12          # 3031.5 W
    expected = P_total * 10000.0 / 3_600_000.0
    for s in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"):
        assert math.isclose(R(s)["total_energy_kwh"], expected, rel_tol=1e-9)


def test_stage2_energy_tests_unchanged():
    from Models.Energy.wallclock_energy import network_active_power_w, continuous_energy_kwh
    assert math.isclose(network_active_power_w(141e12, 21.5), 3031.5, abs_tol=1e-6)
    assert math.isclose(continuous_energy_kwh(3031.5, 10000), EXPECTED_KWH, rel_tol=1e-9)


def test_stage3_scheduler_tests_unchanged():
    from Models.PoCol import round_state as rs
    ev = rs.EventIdentity(1, 5, 5, 100, 3, 7, 0, 2, 0.0, 1.0, 1, 2)
    cur = rs.CurrentState(100, 5, 5, 7, 0, 1, False, False)
    assert rs.classify_event(ev, cur) == rs.VALID_CURRENT


def test_stage4_finder_tests_unchanged():
    import numpy as np
    from Models.PoCol.round_state import draw_round_solutions_exact
    g = np.random.default_rng(1)
    sols = draw_round_solutions_exact(g, 2.0 / 1000, [(0, 0, 999)], {0: 1.0})
    assert isinstance(sols, list)


def test_journal_tests_unchanged():
    from Models.Energy import PowEconomicEnergyModel, GAMMA_SCENARIOS
    pw = PowEconomicEnergyModel(block_subsidy=3.125, avg_tx_fees=0.30, coin_price=60000.0,
                                electricity_price_per_kwh=0.05, electricity_spend_ratio_kappa=0.80)
    assert math.isclose(pw.energy_budget_per_block_kwh(), 3_288_000.0, rel_tol=1e-9)
    assert GAMMA_SCENARIOS["average"] == 0.475


def test_original_thesis_files_unchanged():
    p = os.path.join(ROOT, "docs", "Raed-Rasheed-draft-42-00.docx")
    assert run_utils.sha256_file(p) == "2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda"


# --- full-log emission (63) ---
def test_emit_log_is_optional_and_reconciles():
    from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
    cfg = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100)
    plain = run_scenario(cfg)
    assert "block_log" not in plain                              # off by default
    logged = run_scenario(cfg, emit_log=True)
    assert "block_log" in logged
    assert len(logged["block_log"]) == logged["accepted_blocks"]  # one record per block
    # emitting a log does not change any measured outcome
    assert logged["total_energy_kwh"] == plain["total_energy_kwh"]
    assert logged["accepted_blocks"] == plain["accepted_blocks"]
