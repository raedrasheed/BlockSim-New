"""Stage 5B1G.1 tests 10-13, 16: a winner delivery is generated for EVERY active
non-winning miner, regardless of solution/identity/stale outcome (§3)."""

import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario


def _disjoint_low_mu():
    # low mu + small delay -> some no-solution miners and some non-stale competitors
    return run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=40, mu=1.0,
                                     propagation_delay_mean_s=0.42),
                        emit_detail=True, emit_generation_detail=True)


def _b1_small():
    return run_scenario(EngineConfig("B1", seed=5, miner_count=20, mu=4.0,
                                     network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                     propagation_delay_mean_s=60.0),
                        emit_detail=True, emit_generation_detail=True)


# 10
def test_delivery_record_for_every_active_nonwinner():
    r = _disjoint_low_mu()
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    assert r["stale_race_records"]
    for x in r["stale_race_records"]:
        assert x["active_nonwinner_delivery_count"] == n_active - 1     # winner delivers to all others
    # delivery records per accepted height each number n_active-1
    from collections import Counter
    per_gen = Counter(d["template_generation_id"] for d in r["delivery_delay_records"])
    accepted_gens = {x["template_generation_id"] for x in r["stale_race_records"]}
    for g in accepted_gens:
        assert per_gen[g] == n_active - 1


# 11
def test_b1_same_identity_miners_receive_winner():
    r = _b1_small()
    assert r["accepted_heights"] > 0
    assert r["stale_block_count"] == 0                    # identical headers -> no stale
    db = r["delivery_delay_records"]
    assert db
    assert all(d["same_identity_independent_discovery"] for d in db)
    assert all(d["received_winner_time_s"] is not None for d in db)   # every non-winner receives
    assert all(d["stop_reason"] == "winner_received" for d in db)
    assert all(not d["produced_stale_block"] for d in db)


# 12
def test_no_solution_miner_receives_winner():
    r = _disjoint_low_mu()
    no_sol = [d for d in r["delivery_delay_records"] if d["recipient_discovery_time_s"] is None]
    assert no_sol                                         # some miners had no reachable solution
    for d in no_sol:
        assert d["received_winner_time_s"] is not None    # yet still receive the winner
        assert d["propagation_delay_s"] is not None
        assert d["delivery_stream_key"]
        assert d["produced_stale_block"] is False
        assert d["potential_competitor"] is False
        assert d["stop_reason"] == "no_reachable_solution"


# 13
def test_nonstale_competitor_receives_winner():
    r = _disjoint_low_mu()
    nonstale = [d for d in r["delivery_delay_records"]
                if d["potential_competitor"] and not d["produced_stale_block"]]
    assert nonstale                                       # distinct-identity, discovered after receipt
    for d in nonstale:
        assert d["received_winner_time_s"] is not None
        assert d["stop_reason"] == "winner_received"
        assert d["recipient_discovery_time_s"] is not None
        # a non-producer competitor did NOT discover before receipt
        assert not (d["recipient_discovery_time_s"] < d["received_winner_time_s"])


# 16
def test_same_identity_discovery_not_stale():
    r = _b1_small()
    # every B1 non-winner has the winner's identity -> never a stale, never a competitor
    for d in r["delivery_delay_records"]:
        assert d["same_identity_independent_discovery"] is True
        assert d["produced_stale_block"] is False
        assert d["potential_competitor"] is False
    assert r["actual_competitor_miner_count"] == 0
