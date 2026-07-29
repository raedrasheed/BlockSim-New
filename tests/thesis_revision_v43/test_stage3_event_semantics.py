"""Stage 3 tests: event identity, classification, obsolete-event rejection,
legitimate-stale semantics, and round transitions (tests 1-22)."""

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from Models.PoCol import round_state as rs
from Models.PoCol.round_state import EventIdentity, CurrentState
from _pocol_harness import run_pocol, cached_run

REQUIRED_ID_FIELDS = {
    "event_id", "event_generation_id", "round_id", "parent_block_id",
    "parent_height", "template_id", "template_generation_id", "miner_id",
    "scheduled_at", "fires_at", "target_version", "nonce_range_id",
}


def _ev(**over):
    base = dict(event_id=1, event_generation_id=5, round_id=5, parent_block_id=100,
                parent_height=3, template_id=7, template_generation_id=0, miner_id=2,
                scheduled_at=0.0, fires_at=10.0, target_version=1, nonce_range_id=2)
    base.update(over)
    return EventIdentity(**base)


def _cur(**over):
    base = dict(miner_tip_id=100, miner_generation_id=5, current_round_id=5,
                current_template_id=7, current_template_generation_id=0,
                current_target_version=1, parent_already_advanced=False, consumed=False)
    base.update(over)
    return CurrentState(**base)


# 1 -------------------------------------------------------------------------
def test_event_carries_required_identity():
    assert set(EventIdentity.__dataclass_fields__) >= REQUIRED_ID_FIELDS
    ev = _ev()
    for f in REQUIRED_ID_FIELDS:
        assert getattr(ev, f) is not None
    # a real run schedules events (each stamped with identity)
    assert cached_run(60)["diag"]["scheduled_events"] > 0


# baseline sanity: the matching case is VALID_CURRENT
def test_matching_event_is_valid_current():
    assert rs.classify_event(_ev(), _cur()) == rs.VALID_CURRENT


# 2 -------------------------------------------------------------------------
def test_old_round_event_rejected():
    # generation matches but the round has moved on
    assert rs.classify_event(_ev(round_id=5, event_generation_id=5),
                             _cur(current_round_id=6, miner_generation_id=5)) == rs.OBSOLETE_ROUND


# 3 -------------------------------------------------------------------------
def test_old_parent_event_rejected_after_parent_update():
    assert rs.classify_event(_ev(parent_block_id=100),
                             _cur(miner_tip_id=200)) == rs.OBSOLETE_PARENT


# 4 -------------------------------------------------------------------------
def test_old_template_event_rejected():
    assert rs.classify_event(_ev(template_generation_id=0),
                             _cur(current_template_generation_id=1)) == rs.OBSOLETE_TEMPLATE


# 5 -------------------------------------------------------------------------
def test_old_generation_event_rejected():
    assert rs.classify_event(_ev(event_generation_id=5),
                             _cur(miner_generation_id=6)) == rs.OBSOLETE_GENERATION


# 6 -------------------------------------------------------------------------
def test_difficulty_version_mismatch_rejected():
    assert rs.classify_event(_ev(target_version=1),
                             _cur(current_target_version=2)) == rs.OBSOLETE_DIFFICULTY


# 7 -------------------------------------------------------------------------
def test_invalidated_event_not_processed_twice():
    from Models.PoCol.Consensus import Consensus
    Consensus.configure()  # resets consumed set
    ev = _ev(event_id=42)
    assert not (42 in Consensus.consumed_events)
    Consensus.mark_consumed(ev)
    assert 42 in Consensus.consumed_events
    # a consumed event classifies as INVALID (won't be processed again)
    assert rs.classify_event(ev, _cur(consumed=True)) == rs.INVALID_EVENT


# 8 -------------------------------------------------------------------------
def test_event_invalidation_is_idempotent():
    from Models.PoCol.Consensus import Consensus
    Consensus.configure()
    ev = _ev(event_id=7)
    Consensus.mark_consumed(ev)
    n1 = len(Consensus.consumed_events)
    Consensus.mark_consumed(ev)
    Consensus.mark_consumed(ev)
    assert len(Consensus.consumed_events) == n1   # set: no duplicates


# 9 -------------------------------------------------------------------------
def test_obsolete_event_not_counted_as_stale():
    r = cached_run(100)
    obsolete_total = sum(r["diag"]["obsolete"].values())
    assert obsolete_total > 0                       # obsolete events did occur
    assert r["staleBlocks"] == r["diag"]["legit_stales"]   # stale == legit only
    assert r["staleBlocks"] == 0 or r["staleBlocks"] == r["diag"]["legit_stales"]


# 10 ------------------------------------------------------------------------
def test_obsolete_event_does_not_advance_round():
    r = cached_run(100)
    # every accepted block advances exactly one round -> mainBlocks == accepted
    assert r["mainBlocks"] == r["diag"]["accepted_blocks"]


# 11 ------------------------------------------------------------------------
def test_obsolete_event_does_not_create_reward():
    # rewards derive from main-chain blocks; obsolete events add no chain blocks
    r = cached_run(100)
    assert r["mainBlocks"] == r["diag"]["accepted_blocks"]
    assert r["diag"]["accepted_blocks"] > 0


# 12 ------------------------------------------------------------------------
def test_obsolete_event_does_not_create_block():
    r = cached_run(100)
    assert r["totalBlocks"] == r["diag"]["accepted_blocks"] + r["diag"]["legit_stales"]


# 13 ------------------------------------------------------------------------
def test_propagation_competitor_remains_valid_before_block_receipt():
    # parent still the miner's current tip, but a sibling already advanced
    assert rs.classify_event(_ev(), _cur(parent_already_advanced=True)) == rs.LEGIT_COMPETITOR


# 14 ------------------------------------------------------------------------
def test_legitimate_competing_block_counted_as_stale_when_it_loses():
    # with a large propagation delay, non-winner finders find before hearing the
    # winner -> genuine propagation stales appear, and stale == legit_stales.
    winner = None
    for seed in range(12):
        r = run_pocol(60, sim_time=10000, seed=seed, bdelay=300.0)
        assert r["staleBlocks"] == r["diag"]["legit_stales"]   # invariant always holds
        if r["diag"]["legit_stales"] > 0:
            winner = r
            break
    assert winner is not None, "expected a legitimate propagation stale under high delay"
    assert winner["staleBlocks"] == winner["diag"]["legit_stales"] > 0


# 15 ------------------------------------------------------------------------
def test_same_height_valid_competitors_not_deleted_as_artifacts():
    assert rs.LEGIT_COMPETITOR not in rs.OBSOLETE_CATEGORIES
    assert rs.VALID_CURRENT not in rs.OBSOLETE_CATEGORIES


# 16 ------------------------------------------------------------------------
def test_stale_classification_excludes_exhaustion():
    assert rs.FINITE_DOMAIN_EXHAUSTION not in rs.OBSOLETE_CATEGORIES
    r = cached_run(100)
    # exhausted rounds are tracked separately and never inflate stale/total
    assert isinstance(r["diag"]["exhausted_rounds"], int)
    assert r["totalBlocks"] == r["diag"]["accepted_blocks"] + r["diag"]["legit_stales"]


# 17 ------------------------------------------------------------------------
def test_stale_classification_excludes_failed_hashes():
    # loser miners (no solution) never schedule events -> cannot be stale.
    r = cached_run(500)
    assert r["diag"]["scheduled_events"] < r["n_miners"]   # << N, not one-per-miner
    assert r["staleBlocks"] == r["diag"]["legit_stales"]


# 18 ------------------------------------------------------------------------
def test_exactly_one_round_transition_per_accepted_block():
    r = cached_run(100)
    accepted_transitions = [t for t in r["transitions"]
                            if t["cause"].endswith("accepted_block")]
    assert len(accepted_transitions) == r["diag"]["accepted_blocks"]
    assert r["mainBlocks"] == r["diag"]["accepted_blocks"]


# 19 ------------------------------------------------------------------------
def test_round_transition_records_cause():
    r = cached_run(100)
    assert r["transitions"], "no transitions recorded"
    assert r["transitions"][0]["cause"] == "genesis"
    for t in r["transitions"]:
        assert "cause" in t and "old_round_id" in t and "new_round_id" in t
        assert t["cause"] in ("genesis", "accepted_block") or t["cause"].startswith("exhaustion+")


# 20 ------------------------------------------------------------------------
def test_exhaustion_creates_new_template_generation():
    # small domain factor -> mu<1 -> frequent exhaustion.
    r = run_pocol(50, sim_time=6000, seed=1, domain_factor=0.5)
    assert r["diag"]["exhausted_rounds"] > 0
    assert r["diag"]["template_refreshes"] > 0
    assert any(t["exhaust_refreshes"] > 0 and "exhaustion" in t["cause"]
               for t in r["transitions"])


# 21 ------------------------------------------------------------------------
def test_accepted_block_invalidates_prior_generation():
    # in a real run, prior-generation finder events are rejected as obsolete.
    r = cached_run(100)
    assert r["diag"]["obsolete"][rs.OBSOLETE_GENERATION] > 0
    # unit-level: an event from an older generation is OBSOLETE_GENERATION
    assert rs.classify_event(_ev(event_generation_id=3),
                             _cur(miner_generation_id=4)) == rs.OBSOLETE_GENERATION


# 22 ------------------------------------------------------------------------
def test_local_round_state_under_propagation_delay():
    ev = _ev(parent_block_id=100, event_generation_id=5, round_id=5)
    # miner A still on parent 100 (has not received the new block) -> valid/legit
    a = rs.classify_event(ev, _cur(miner_tip_id=100, miner_generation_id=5,
                                   current_round_id=5, parent_already_advanced=True))
    # miner B already advanced to 200 (received the new block) -> obsolete
    b = rs.classify_event(ev, _cur(miner_tip_id=200, miner_generation_id=6,
                                   current_round_id=6))
    assert a == rs.LEGIT_COMPETITOR
    assert b in rs.OBSOLETE_CATEGORIES
    assert a != b
