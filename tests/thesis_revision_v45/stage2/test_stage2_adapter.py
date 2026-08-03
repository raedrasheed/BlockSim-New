"""Stage-2B BlockSim integration adapter test (S2A-8 / S2B-6).

The adapter maps a BlockSim-style configuration to a Stage2Config, runs the PoCol core,
and returns round/block/energy results in the declared schema — without touching the
legacy simulator or any frozen Stage-1 document.  Energy labelling is scientifically
correct (S2B-6): the continuous full-participation reference is
``continuous_all_active_control_kwh`` (NOT a matched saving basis), and the constructed
matched identity experiment is exposed separately.
"""
from __future__ import annotations

from Models.PoCol.stage2 import (run_pocol_stage2, stage2config_from_blocksim,
                                  results_schema, RESULT_SCHEMA_VERSION, Stage2Config,
                                  run_simulation, a1_continuous_control_kwh, SUCCESS_MODEL)


def test_adapter_maps_blocksim_config():
    """BlockSim-style keys map onto Stage2Config; unknown keys are ignored."""
    cfg = stage2config_from_blocksim({"Nn": 10, "simTime": 250.0, "nonce_domain_size": 900,
                                      "difficulty": 800, "unknown_key": 123})
    assert isinstance(cfg, Stage2Config)
    assert cfg.num_miners == 10
    assert cfg.horizon_T == 250.0
    assert cfg.nonce_domain_size == 900
    assert cfg.difficulty == 800


def test_adapter_returns_declared_schema():
    """run_pocol_stage2 returns the declared round/block/energy schema (S2B-6 labels)."""
    out = run_pocol_stage2({"num_miners": 8, "horizon_T": 300.0, "nonce_domain_size": 1200,
                            "reserve_fraction": 0.25})
    assert out["schema_version"] == RESULT_SCHEMA_VERSION == "stage3.1"   # S3: schema bump
    assert out["algorithm"] == "PoCol"
    assert out["mechanism"] == "idle policy within PoCol"
    assert out["success_model"] == SUCCESS_MODEL == "TARGET_COUPLED_SHA256_DIGEST_LEQ_TARGET"
    for key in ("rounds_executed", "rounds_accepted", "rounds_no_block", "run_disposition",
                "run_end_time", "energy_kwh", "continuous_all_active_control_kwh",
                "residency_reconciles", "evaluation_ledger_entries", "per_miner_energy_kwh",
                "queue_terminal_state_counts", "driver_request_terminal_state_counts"):
        assert key in out
    # S2B-6: the run energy vs the continuous all-active reference is NOT labelled a saving.
    assert "matched_control_kwh" not in out
    assert out["rounds_executed"] >= 1
    assert out["residency_reconciles"] is True
    assert out["evaluation_ledger_entries"] > 0
    assert 0.0 < out["energy_kwh"] < out["continuous_all_active_control_kwh"]
    assert set(out["queue_terminal_state_counts"]) <= {"CONSUMED", "CANCELLED"}
    assert set(out["driver_request_terminal_state_counts"]) <= {"CONSUMED", "CANCELLED",
                                                                 "REJECTED"}
    # S2B-6: the constructed matched identity experiment is exposed SEPARATELY.
    m = out["matched_identity_experiment"]
    assert m["scenario"] == "constructed_matched_identity_validation"
    assert "not a general PoCol saving" in m["note"]
    assert m["max_abs_identity_residual_j"] < 1e-6


def test_adapter_default_config_is_canonical_a1_reference():
    """The empty BlockSim config yields the canonical A1 accounting reference (8.420833333 kWh)."""
    cfg = stage2config_from_blocksim({})
    assert abs(a1_continuous_control_kwh(cfg) - 8.420833333) < 1e-9


def test_results_schema_directly():
    """results_schema over a finished run exposes the declared keys."""
    cfg = Stage2Config(num_miners=6, horizon_T=200.0, nonce_domain_size=900,
                       reserve_fraction=0.34)
    run = run_simulation(cfg)
    schema = results_schema(run, cfg)
    assert schema["schema_version"] == RESULT_SCHEMA_VERSION
    assert schema["config"]["num_miners"] == 6
    assert schema["loop_result"] == "run_completed"
    assert "continuous_all_active_control_kwh" in schema
