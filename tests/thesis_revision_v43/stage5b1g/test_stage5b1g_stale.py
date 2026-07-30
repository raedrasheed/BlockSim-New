"""Stage 5B1G tests 1-10 + correction tests: single-height stale-race lifecycle and
actual/potential taxonomy (Sections 1-3, 8).

Corrected model: ONE stale per MINER per height, but MANY distinct miners may each
produce a stale at the same height -> stale_block_count in 0..N_active-1. There is NO
global one-stale-per-height cap.
"""

import os
import sys
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, _resolve_stale_race, _delivery_delay)
from experiments.thesis_revision_v43 import schemas

# a small-domain, high-delay regime that reliably produces MANY stales per height
STALE_CFG = dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                 network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                 propagation_delay_mean_s=60.0)


def _stale_run():
    return run_scenario(EngineConfig(**STALE_CFG), emit_detail=True, emit_generation_detail=True)


def _beating_discoveries(cfg, gen, parent, winner_miner, comp_miners):
    """Construct discoveries where every listed competitor is GUARANTEED to discover
    before receiving the winner (deterministic, delay-magnitude independent): each
    competitor's time = winner_time + its own delay - 1e-9 < received_winner_time."""
    wt = Fraction(1, 1000)
    disc = [dict(miner=winner_miner, offset=0, q="W", identity="WIN", time=wt)]
    for m in comp_miners:
        delay, _ = _delivery_delay(cfg, gen, parent, winner_miner, m)
        disc.append(dict(miner=m, offset=5, q=m, identity=f"id{m}",
                         time=wt + delay - Fraction(1, 10 ** 9)))
    return disc


CFG = EngineConfig("B2", seed=42, miner_count=10, propagation_delay_mean_s=5.0)


# ---- correction tests (explicitly required) ----

# test_two_distinct_miners_can_produce_two_stales_same_height
def test_two_distinct_miners_can_produce_two_stales_same_height():
    disc = _beating_discoveries(CFG, 7, "blk-3", 0, [1, 2])
    race = _resolve_stale_race(disc, CFG, 7, "blk-3")
    assert len(race["stale_producers"]) == 2
    assert {p["miner"] for p in race["stale_producers"]} == {1, 2}


# test_three_stale_producers_counted_individually
def test_three_stale_producers_counted_individually():
    disc = _beating_discoveries(CFG, 7, "blk-3", 0, [1, 2, 3])
    race = _resolve_stale_race(disc, CFG, 7, "blk-3")
    assert len(race["stale_producers"]) == 3
    assert sorted(p["miner"] for p in race["stale_producers"]) == [1, 2, 3]


# test_each_miner_at_most_one_stale_per_height
def test_each_miner_at_most_one_stale_per_height():
    # two beating discoveries for the SAME competitor miner -> collapsed to one stale
    disc = _beating_discoveries(CFG, 7, "blk-3", 0, [1])
    dup = dict(disc[1]); dup["offset"] = 9; dup["q"] = 999; dup["identity"] = "id1b"
    dup["time"] = disc[1]["time"] + Fraction(1, 10 ** 6)          # later, same miner
    race = _resolve_stale_race(disc + [dup], CFG, 7, "blk-3")
    ids = [p["miner"] for p in race["stale_producers"]]
    assert ids.count(1) == 1                                     # miner 1 stales at most once


# test_stale_block_count_equals_stale_producer_count
def test_stale_block_count_equals_stale_producer_count():
    r = _stale_run()
    for t in r["per_template"]:
        assert t["stale_block_count"] == t["actual_stale_producer_miner_count"]
        assert t["stale_block_count"] == len(t["stale_producer_miner_ids"])
        assert t["stale_block_count"] == len(t["stale_block_ids"])


# test_actual_proposal_count_equals_one_plus_all_stales
def test_actual_proposal_count_equals_one_plus_all_stales():
    r = _stale_run()
    for t in r["per_template"]:
        if t["accepted"]:
            assert t["actual_proposal_miner_count"] == 1 + t["stale_block_count"]


# test_height_has_any_stale_is_only_boolean_indicator
def test_height_has_any_stale_is_only_boolean_indicator():
    r = _stale_run()
    # the boolean indicator equals (count>0) and is NOT the count itself
    assert any(t["stale_block_count"] > 1 and t["height_has_any_stale"] is True
               for t in r["per_template"])
    for t in r["per_template"]:
        assert t["height_has_any_stale"] == (t["stale_block_count"] > 0)
    assert r["heights_with_any_stale"] < r["stale_block_count"]   # indicator sum != total stales


# test_no_global_one_stale_cap
def test_no_global_one_stale_cap():
    r = _stale_run()
    assert max(t["stale_block_count"] for t in r["per_template"]) > 1


# test_multiple_stale_block_ids_are_unique
def test_multiple_stale_block_ids_are_unique():
    r = _stale_run()
    all_ids = []
    for t in r["per_template"]:
        assert len(set(t["stale_block_ids"])) == len(t["stale_block_ids"])   # unique per height
        all_ids.extend(t["stale_block_ids"])
    assert len(set(all_ids)) == len(all_ids)                     # globally unique


# ---- taxonomy / lifecycle tests ----

# 1
def test_stale_count_within_active_bound():
    r = _stale_run()
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    for t in r["per_template"]:
        assert 0 <= t["stale_block_count"] <= n_active - 1


# 2
def test_b1_same_identity_zero_stale():
    r = run_scenario(EngineConfig("B1", seed=20261001, miner_count=100,
                                  propagation_delay_mean_s=60.0), emit_detail=True)
    assert r["stale_block_count"] == 0
    assert r["actual_competitor_miner_count"] == 0


# 3
def test_zero_delay_produces_no_stale():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                  network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                  propagation_delay_mean_s=0.0), emit_detail=True)
    assert r["stale_block_count"] == 0


# 4
def test_actual_competitor_equals_stale_producer():
    r = _stale_run()
    for t in r["per_template"]:
        assert t["actual_competitor_miner_count"] == t["actual_stale_producer_miner_count"]


# 5
def test_no_block_zero_taxonomy():
    r = _stale_run()
    for t in r["per_template"]:
        if not t["accepted"]:
            assert t["actual_proposal_miner_count"] == 0
            assert t["actual_competitor_miner_count"] == 0
            assert t["stale_block_count"] == 0


# 6
def test_potential_at_least_actual():
    r = _stale_run()
    for t in r["per_template"]:
        if t["accepted"]:
            assert t["potential_competitor_miner_count"] >= t["actual_competitor_miner_count"]


# 7
def test_run_level_stale_sum_reconciles():
    r = _stale_run()
    assert sum(t["stale_block_count"] for t in r["per_template"]) == r["stale_block_count"]
    rec = schemas.reconcile_stale_diagnostic(r, r["per_template"], n_active=20)
    assert rec["passed"], rec


# 8
def test_stale_race_energy_not_integrated():
    r = _stale_run()
    assert r["stale_race_energy_not_integrated"] is True
    assert r["stale_race_candidate_evaluations"] > 0
    assert (r["total_candidate_evaluations"]
            == r["distinct_candidate_identities"] + r["duplicate_evaluations"])


# 9
def test_deprecated_alias_mapping():
    r = _stale_run()
    m = r["deprecated_stale_alias_map"]
    assert m["legitimate_stale_block_count"] == "single_height_stale_block_count"
    assert r["legitimate_stale_block_count"] == r["single_height_stale_block_count"] == r["stale_block_count"]
    assert r["stales_per_accepted_block"] == r["single_height_stales_per_accepted_block"]
    assert (r["stale_fraction_of_all_valid_blocks"]
            == r["single_height_stale_fraction_of_valid_proposals"])


# 10
def test_stale_producer_ids_match_generation_rows():
    r = _stale_run()
    by_gen = {}
    for g in r["per_miner_generation"]:
        if g["produced_stale_block"]:
            by_gen.setdefault(g["template_generation_id"], set()).add(g["miner_id"])
    for t in r["per_template"]:
        gen = t["template_generation_id"]
        assert by_gen.get(gen, set()) == set(t["stale_producer_miner_ids"])
