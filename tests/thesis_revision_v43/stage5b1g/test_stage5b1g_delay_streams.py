"""Stage 5B1G tests 11-17: propagation-delay stream identity (Section 4)."""

import os
import sys
import itertools
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, _delivery_delay, _resolve_stale_race)


CFG = EngineConfig("B2", seed=42, miner_count=10, propagation_delay_mean_s=5.0)


def _disc(pairs):
    return [dict(miner=m, offset=o, q=o, identity=o, time=Fraction(o + 1, 100)) for m, o in pairs]


# 11
def test_delay_is_reproducible():
    a = _delivery_delay(CFG, 7, "blk-3", 4, 9)
    b = _delivery_delay(CFG, 7, "blk-3", 4, 9)
    assert a == b


# 12
def test_delay_independent_per_recipient():
    a = _delivery_delay(CFG, 7, "blk-3", 4, 9)[0]
    b = _delivery_delay(CFG, 7, "blk-3", 4, 2)[0]
    assert a != b                                   # different recipient -> own stream


# 13
def test_stale_producers_order_independent():
    disc = _disc([(4, 20), (9, 50), (2, 80), (7, 110)])
    base = _resolve_stale_race([dict(x) for x in disc], CFG, 7, "blk-3")
    base_prod = sorted(p["miner"] for p in base["stale_producers"])
    base_delays = dict(base["delay_by"])
    for perm in itertools.permutations(disc):
        r = _resolve_stale_race([dict(x) for x in perm], CFG, 7, "blk-3")
        assert sorted(p["miner"] for p in r["stale_producers"]) == base_prod   # set not remapped
        assert dict(r["delay_by"]) == base_delays


# 14
def test_adding_recipient_does_not_shift_existing():
    disc = _disc([(4, 20), (9, 50), (2, 80), (7, 110)])
    base = _resolve_stale_race([dict(x) for x in disc], CFG, 7, "blk-3")["delay_by"]
    more = _disc([(4, 20), (9, 50), (2, 80), (7, 110), (5, 200)])
    now = _resolve_stale_race([dict(x) for x in more], CFG, 7, "blk-3")["delay_by"]
    for m in base:
        assert now[m] == base[m]


# 15
def test_same_winner_different_generation_differs():
    a = _delivery_delay(CFG, 7, "blk-3", 4, 9)[0]
    b = _delivery_delay(CFG, 8, "blk-4", 4, 9)[0]    # different gen + parent
    assert a != b


# 16
def test_zero_mean_gives_exact_zero_delay():
    cfg0 = EngineConfig("B2", seed=42, miner_count=10, propagation_delay_mean_s=0.0)
    assert _delivery_delay(cfg0, 7, "blk-3", 4, 9)[0] == Fraction(0)


# 17
def test_delivery_stream_key_recorded_and_matches():
    r = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                                  network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                                  propagation_delay_mean_s=60.0), emit_detail=True)
    recs = r["delivery_delay_records"]
    assert recs
    rec = recs[0]
    expect_key = (f"{5}|{rec['template_generation_id']}|{rec['parent_block_id']}"
                  f"|{rec['winner_miner_id']}|{rec['recipient_miner_id']}|propagation_delay")
    assert rec["delivery_stream_key"] == expect_key
    # the recorded delay reproduces from the identity alone
    cfg = EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                       network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                       propagation_delay_mean_s=60.0)
    d, _ = _delivery_delay(cfg, rec["template_generation_id"], rec["parent_block_id"],
                           rec["winner_miner_id"], rec["recipient_miner_id"])
    assert abs(float(d) - rec["propagation_delay_s"]) < 1e-12
