"""Stage 5B1G tests 18-23: per-miner-generation stale-race output (Section 5)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import schemas


def _stale_run():
    return run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                     network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                     propagation_delay_mean_s=60.0),
                        emit_detail=True, emit_generation_detail=True)


# 18
def test_generation_schema_complete():
    r = _stale_run()
    assert r["per_miner_generation"]
    for g in r["per_miner_generation"][:300]:
        assert schemas.validate_fields(g, schemas.PER_MINER_GENERATION_FIELDS) == []
        assert g["stop_reason"] in schemas.GENERATION_STOP_REASONS


# 19
def test_winner_row_populated():
    r = _stale_run()
    winners = [g for g in r["per_miner_generation"]
               if g["generated_block_id"] is not None]
    assert winners
    for g in winners:
        assert g["stop_reason"] == "solution_found"
        assert g["received_winner_time_s"] is not None     # winner receives its own solution
        assert g["produced_stale_block"] is False


# 20
def test_stale_producer_row_populated():
    r = _stale_run()
    producers = [g for g in r["per_miner_generation"] if g["produced_stale_block"]]
    assert producers                                        # regime produces stales
    for g in producers:
        assert g["stale_block_id"] is not None
        assert g["stop_reason"] == "stale_block_generated"
        assert g["propagation_delay_s"] is not None
        assert g["received_winner_time_s"] is not None
        assert g["found_competing_solution_before_receipt"] is True


# 21
def test_non_producing_competitor_row():
    r = _stale_run()
    # a non-winning miner that received the winner without producing a stale: it had a
    # reachable solution (same-identity or found after receipt) -> "winner_received".
    # (No-solution recipients also receive the winner but keep "no_reachable_solution".)
    comp = [g for g in r["per_miner_generation"] if g["stop_reason"] == "winner_received"]
    assert comp
    for g in comp:
        assert g["received_winner_time_s"] is not None
        assert not g["produced_stale_block"]
        assert g["generated_block_id"] is None
        assert g["propagation_delay_s"] is not None


# 22
def test_no_reachable_solution_row():
    r = _stale_run()
    nrs = [g for g in r["per_miner_generation"] if g["stop_reason"] == "no_reachable_solution"]
    assert nrs                                              # some miners have no reachable solution
    for g in nrs:
        assert g["earliest_solution_position"] is None
        assert g["generated_block_id"] is None
        assert g["produced_stale_block"] is False


# 23
def test_main_vs_stale_propagation_counted_separately():
    r = _stale_run()
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    per_block = max(n_active - 1, 0)
    # main-block propagation: one broadcast per accepted block to every other active
    # miner. Stale-block propagation: one broadcast PER admitted stale (a height with
    # several stales contributes several) -> can exceed main propagation.
    assert r["main_block_propagation_message_count"] == r["accepted_heights"] * per_block
    assert r["stale_block_propagation_message_count"] == r["stale_block_count"] * per_block
    assert r["stale_block_propagation_message_count"] > r["main_block_propagation_message_count"]
    # a no-stale run has zero stale propagation, non-zero main propagation
    r0 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                   network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                   propagation_delay_mean_s=0.0), emit_detail=True)
    assert r0["stale_block_propagation_message_count"] == 0
    assert r0["main_block_propagation_message_count"] > 0
