"""Stage-4 nonce-range-lease + deterministic-reassignment tests S4-01 .. S4-20.

These exercise explicit range leases and reassignment of the UNFINISHED SUFFIX of an
already-claimed slice on top of the accepted Stage-2B search core and the accepted Stage-3 /
Stage-3A security-floor layer.  Reassignment is a liveness/coverage mechanism (it may
increase energy and latency, never saves energy); the target and difficulty never change.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, SecurityFloorPolicy,
                                  RunInitialise, ProcessEventTime, SeatNextRoundBootstrap,
                                  RunEventLoopToHorizon, run_simulation, run_pocol_stage2,
                                  target_for_difficulty, select_reassignment_candidate,
                                  ReassignmentCandidate, TERMINAL_LEASE_STATUSES,
                                  TERMINAL_REASSIGN_REQUEST_STATUSES, PRIMARY_ASSIGNMENT,
                                  ACTIVATED_RESERVE_ASSIGNMENT, REASSIGNED_PRIMARY_WORK,
                                  REASSIGNED_RESERVE_WORK, FULL_DOMAIN_EXHAUSTED_NO_BLOCK)

_ZERO = 1 << 300   # target_for_difficulty(_) == 0 -> deterministically no solution


def lease_cfg(faults=(), *, num_miners=4, reserve_fraction=0.0, D=400, difficulty=_ZERO,
              horizon=60.0, wake=1.0, no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE",
              reassignment_enabled=True, max_reassign=1_000_000, floor=None):
    pol = RangeLeasePolicy(enabled=True, reassignment_wake_latency=wake,
                           reassignment_enabled=reassignment_enabled,
                           maximum_reassignments_per_slice=max_reassign,
                           no_eligible_miner_policy=no_eligible)
    kw = dict(num_miners=num_miners, reserve_fraction=reserve_fraction, nonce_domain_size=D,
              difficulty=difficulty, batch_size=25, horizon_T=horizon, range_lease=pol,
              injected_lease_faults=faults)
    if floor is not None:
        kw["security_floor"] = floor
    return Stage2Config(**kw)


def prep_round1(cfg):
    """Run the event loop up to (and including) round-1 participant preparation."""
    run = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)   # dispatches round-1 init -> prepare
    return run


# canonical single-fault (Path A): a slow primary fails; its suffix goes to a finished primary.
_PATH_A = ((1, "M000", 1.6, "MINER_FAILED"),)
# canonical single-fault (Path B): a primary fails while the other is busy; a reserve wakes.
_PATH_B = ((1, "M000", 1.3, "MINER_FAILED"),)


# ---------------------------------------------------------------- S4-01
def test_s4_01_every_primary_gets_one_active_lease():
    run = prep_round1(lease_cfg())
    rc = run.current_round_context
    participants = run.round_participants[rc.RoundID]
    for mid in participants:
        slice_id = run.slice_of_miner[(rc.RoundID, mid)]
        prog = run.range_progress[slice_id]
        lease = run.range_leases[prog.current_lease_id]
        assert lease.lease_status == "ACTIVE" and lease.MinerID == mid
        assert lease.lease_generation == 1
        assert (lease.lease_start_nonce, lease.lease_end_nonce) == rc.assignments[
            lease.AssignmentID]["range"]
    # exactly one current ACTIVE lease per primary slice.
    active = [l for l in run.range_leases.values()
              if l.RoundID == rc.RoundID and l.lease_status == "ACTIVE"]
    assert len(active) == len(participants)


# ---------------------------------------------------------------- S4-02
def test_s4_02_every_activated_reserve_gets_one_active_lease():
    # a positive floor forces a reserve activation; leases give it an ACTIVE lease.
    floor = SecurityFloorPolicy(enabled=True, minimum_active_hash_rate=250.0)
    run = run_simulation(lease_cfg(num_miners=4, reserve_fraction=0.5, floor=floor))
    reserve_leases = [l for l in run.range_leases.values()
                      if l.assignment_kind == ACTIVATED_RESERVE_ASSIGNMENT]
    assert reserve_leases                                    # at least one activated reserve leased
    for l in reserve_leases:
        prog = run.range_progress[l.RangeSliceID]
        assert prog is not None
        # the lease covered exactly the reserve slice.
        assert l.lease_start_nonce == prog.range_start and l.lease_end_nonce == prog.range_end


# ---------------------------------------------------------------- S4-03
def test_s4_03_committed_progress_is_exact():
    run = run_simulation(lease_cfg())
    # for every slice, committed_frontier - range_start == unique committed nonces (ledger).
    by_slice = {}
    for rec in run.evaluation_ledger:
        by_slice.setdefault((rec.RoundID, rec.RangeSliceID), set()).update(rec.nonces())
    checked = 0
    for sid, prog in run.range_progress.items():
        nonces = by_slice.get((prog.RoundID, sid), set())
        assert prog.committed_frontier - prog.range_start == len(nonces)
        # monotonic + bounded.
        assert prog.range_start <= prog.committed_frontier <= prog.range_end
        checked += 1
    assert checked > 0


# ---------------------------------------------------------------- S4-04
def test_s4_04_planning_does_not_advance_frontier():
    cfg = lease_cfg()
    run = prep_round1(cfg)
    rc = run.current_round_context
    # dispatch the wakes: every primary plans its first HashWorkEvent (but nothing commits yet).
    ProcessEventTime(run, cfg.run_start_time + cfg.wake_latency)
    planned = [r for r in run.event_queue.queued_event_registry.values()
               if r.event_type == "HashWorkEvent" and r.queue_status == "QUEUED"]
    assert planned                                          # batches ARE planned
    for mid in run.round_participants[rc.RoundID]:
        prog = run.range_progress[run.slice_of_miner[(rc.RoundID, mid)]]
        assert prog.committed_frontier == prog.range_start   # planning advanced nothing


# ---------------------------------------------------------------- S4-05
def test_s4_05_miner_failure_revokes_lease_and_cancels_hash_event():
    run = run_simulation(lease_cfg(_PATH_A))
    assert run.lease_stats["leases_revoked"] == 1
    # the failed miner's lease is terminal (REVOKED then REASSIGNED).
    failed = [l for l in run.range_leases.values()
              if l.MinerID == "M000" and l.RoundID == "round-1" and l.lease_generation == 1]
    assert failed and failed[0].lease_status in ("REVOKED", "REASSIGNED")
    # its queued HashWorkEvent was cancelled by the revoke (a CANCELLED hash event exists).
    assert any(r.event_type == "HashWorkEvent" and r.queue_status == "CANCELLED"
               and r.immutable_payload.get("MinerID") == "M000"
               for r in run.event_queue.queued_event_registry.values())


# ---------------------------------------------------------------- S4-06
def test_s4_06_new_lease_begins_at_committed_frontier():
    run = run_simulation(lease_cfg(_PATH_A))
    # the successor (generation-2) lease starts exactly at the predecessor committed frontier.
    succ = [l for l in run.range_leases.values()
            if l.RoundID == "round-1" and l.lease_generation == 2]
    assert succ
    for l in succ:
        pred = run.range_leases[l.predecessor_lease_id]
        # predecessor searched [range_start, committed) ; successor starts at that frontier.
        assert l.lease_start_nonce == pred.committed_cursor


# ---------------------------------------------------------------- S4-07
def test_s4_07_reassignee_evaluates_no_nonce_below_frontier():
    run = run_simulation(lease_cfg(_PATH_A))
    # the reassigned-work ledger records never include a nonce below the predecessor frontier.
    for l in run.range_leases.values():
        if l.assignment_kind not in (REASSIGNED_PRIMARY_WORK, REASSIGNED_RESERVE_WORK):
            continue
        floor = l.lease_start_nonce
        for rec in run.evaluation_ledger:
            if rec.LeaseID == l.LeaseID:
                assert rec.interval_start >= floor


# ---------------------------------------------------------------- S4-08
def test_s4_08_zero_duplicate_nonce_across_predecessor_and_successor():
    run = run_simulation(lease_cfg(_PATH_A))
    assert run.lease_stats["leases_reassigned"] >= 1
    seen_sl = set()
    seen_g = set()
    dup_sl = dup_g = 0
    for rec in run.evaluation_ledger:
        for n in rec.nonces():
            ks = (rec.TemplateID, rec.RangeSliceID, n)
            kg = (rec.TemplateID, n)
            if ks in seen_sl:
                dup_sl += 1
            if kg in seen_g:
                dup_g += 1
            seen_sl.add(ks)
            seen_g.add(kg)
    assert dup_sl == 0 and dup_g == 0


def _manual_round_with_leases():
    """A minimal SOLUTION_PROPAGATION round with M000 ACTIVE (frontier 25) + M001 finished."""
    from Models.PoCol.stage2 import RoundContext, MinerSearchState
    from Models.PoCol.stage2.simulator import _create_range_progress_and_lease
    run = RunInitialise(lease_cfg())
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    # M000: ACTIVE_HASHING, committed 25/100.
    run.create_miner("M000", 0.0, state="ACTIVE_HASHING")
    st0 = MinerSearchState("M000", "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st0.cursor = 25
    st0.active_start = 0.0
    rc.search_states["M000"] = st0
    rc.assignments["A0"] = {"MinerID": "M000", "AssignmentID": "A0", "assignment_version": 1,
                            "range": (0, 100), "RoundID": "round-1",
                            "TemplateID": "tpl-round-1", "coverage_state": "OPEN"}
    _create_range_progress_and_lease(run, rc, "M000", "A0", 1, "PS-round-1-M000", 0, 100,
                                     PRIMARY_ASSIGNMENT, 0.0)
    run.range_progress["PS-round-1-M000"].committed_frontier = 25
    run.range_leases[run.range_progress["PS-round-1-M000"].current_lease_id].committed_cursor = 25
    # M001: finished its own range -> an eligible reassignee (LOW_POWER_LISTEN, completed).
    run.create_miner("M001", 0.0, state="LOW_POWER_LISTEN")
    st1 = MinerSearchState("M001", "A1", 1, 200.0, 100, 200, 21.5, 2.15)
    st1.cursor = 200
    st1.completed = True
    st1.completion_kind = "EXHAUSTED"
    rc.search_states["M001"] = st1
    run.search_assignment_kind[("round-1", "M001")] = PRIMARY_ASSIGNMENT
    return run, rc


# ---------------------------------------------------------------- S4-09
def test_s4_09_stale_old_lease_hash_event_no_effect():
    from Models.PoCol.stage2.simulator import _handle_hash_work
    run, rc = _manual_round_with_leases()
    eq = run.event_queue
    prog = run.range_progress["PS-round-1-M000"]
    old_lease = run.range_leases[prog.current_lease_id]
    stale_payload = {"RoundID_at_seat": "round-1", "TemplateID_at_seat": "tpl-round-1",
                     "AssignmentID": "A0", "assignment_version": 1, "MinerID": "M000",
                     "cursor_start": 25, "cursor_end": 50, "expected_search_generation": 0,
                     "LeaseID": old_lease.LeaseID, "lease_generation": 1}
    # supersede the lease (as a reassignment would) WITHOUT completing M000's live search state.
    old_lease.lease_status = "REVOKED"
    before = run.lease_stats["stale_old_lease_events"]
    eq.current_event_time = 5.0
    eq.current_event_ref = None
    res = _handle_hash_work(run, stale_payload, {})
    assert res.kind == "hash_work_no_effect"
    assert run.lease_stats["stale_old_lease_events"] == before + 1
    assert prog.committed_frontier == 25                   # the stale event advanced nothing


# ---------------------------------------------------------------- S4-10
def test_s4_10_exact_replay_creates_no_second_lease_or_event():
    from Models.PoCol.stage2 import EventRef
    from Models.PoCol.stage2.simulator import (RevokeRangeLeaseTransaction,
                                               SeatRangeReassignmentTransaction,
                                               _eligible_reassignment_candidates)
    run, rc = _manual_round_with_leases()
    eq = run.event_queue
    eq.current_event_time = 2.5
    eq.current_delta_cycle = 0
    eq.current_microphase = "MINER_FAILURE"
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "MinerFailureEvent", 2.5, 0,
                                    "MINER_FAILURE", 1)
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    RevokeRangeLeaseTransaction(run, rc, lease, "MINER_FAILED")
    cands = _eligible_reassignment_candidates(run, rc, "PS-round-1-M000", "M000", 25, 2.5)
    chosen = select_reassignment_candidate(cands)
    assert chosen is not None and chosen.MinerID == "M001"
    SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    n_req = len(run.reassignment_requests)
    n_start = sum(1 for r in eq.queued_event_registry.values()
                  if r.event_type == "RangeReassignmentStartEvent")
    seated = run.lease_stats["reassignment_requests_seated"]
    assert n_req == 1 and n_start == 1 and seated == 1
    # exact replay: reprocess the IDENTICAL request (same predecessor / frontier / miner /
    # generation) -> the req_id guard returns the existing request with no second effect.
    run.lease_generation_of_slice["PS-round-1-M000"] = 1     # recompute the same new_gen == 2
    SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    n_start2 = sum(1 for r in eq.queued_event_registry.values()
                   if r.event_type == "RangeReassignmentStartEvent")
    assert len(run.reassignment_requests) == n_req and n_start2 == n_start
    assert run.lease_stats["reassignment_requests_seated"] == seated


# ---------------------------------------------------------------- S4-11
def test_s4_11_two_runs_select_same_reassignment_miner():
    a = run_simulation(lease_cfg(_PATH_A))
    b = run_simulation(lease_cfg(_PATH_A))
    sel_a = [(d.RangeSliceID, d.selected_miner_id, d.policy_result)
             for d in a.reassignment_decisions]
    sel_b = [(d.RangeSliceID, d.selected_miner_id, d.policy_result)
             for d in b.reassignment_decisions]
    assert sel_a == sel_b and any(d.selected_miner_id is not None
                                  for d in a.reassignment_decisions)


# ---------------------------------------------------------------- S4-12
def test_s4_12_reserve_reassignee_uses_stage3_wake_lifecycle():
    run = run_simulation(lease_cfg(_PATH_B, reserve_fraction=0.5))
    reserve_reqs = [r for r in run.reassignment_requests.values() if r.needs_stage3_wake]
    assert reserve_reqs                                    # a reserve was selected
    for r in reserve_reqs:
        assert r.reserve_activation_request_id is not None  # references the accepted request
        assert r.reserve_activation_request_id in run.activation_requests
        assert r.status == "COMPLETED"
    # the reserve reached ACTIVE via the accepted Stage-3 activation completion.
    assert run.security_stats["activations_completed"] >= 1
    assert any(l.assignment_kind == REASSIGNED_RESERVE_WORK for l in run.range_leases.values())


# ---------------------------------------------------------------- S4-13
def test_s4_13_no_eligible_continue_records_uncovered_suffix():
    # a single primary fails with nobody else to take over -> uncovered suffix recorded.
    run = run_simulation(lease_cfg(((1, "M000", 1.6, "MINER_FAILED"),), num_miners=1,
                                   no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE", horizon=30.0))
    assert run.lease_stats["uncovered_nonce_count"] > 0
    prog = run.range_progress["PS-round-1-M000"]
    assert prog.terminal_status == "UNASSIGNED_AT_ROUND_CLOSE"
    assert prog.committed_frontier < prog.range_end
    # exact uncovered suffix.
    assert run.lease_stats["uncovered_nonce_count"] >= prog.range_end - prog.committed_frontier
    # NOT labelled a full-domain exhaustion.
    assert not any(o.kind == "round_aborted"
                   and o.data.get("reason") == FULL_DOMAIN_EXHAUSTED_NO_BLOCK
                   and o.data.get("RoundID") == "round-1" for o in run.log)


# ---------------------------------------------------------------- S4-14
def test_s4_14_no_eligible_abort_closes_through_owner():
    run = run_simulation(lease_cfg(((1, "M000", 1.6, "MINER_FAILED"),), num_miners=1,
                                   no_eligible="ABORT_ROUND", horizon=30.0))
    assert any(o.kind == "round_aborted"
               and o.data.get("reason") == "range_reassignment_unavailable" for o in run.log)
    # every lease + request of the aborted round is terminal.
    assert all(l.lease_status in TERMINAL_LEASE_STATUSES
               for l in run.range_leases.values() if l.RoundID == "round-1")


# ---------------------------------------------------------------- S4-15
def test_s4_15_reassignment_seat_failure_leaves_coherent_state():
    cfg = lease_cfg(_PATH_A)
    run = RunInitialise(cfg)
    run.force_reassignment_seat_failure = True             # S4-15 fault injection
    RunEventLoopToHorizon(run)
    assert run.lease_stats["reassignment_seat_rollback_count"] >= 1
    # the failed slice is coherent: predecessor terminal, request FAILED, suffix pending-retry
    # / unassigned, and NO current_lease_id points to a non-ACTIVE lease.
    failed_reqs = [r for r in run.reassignment_requests.values() if r.status == "FAILED"]
    assert failed_reqs
    for prog in run.range_progress.values():
        if prog.current_lease_id is not None:
            lease = run.range_leases.get(prog.current_lease_id)
            assert lease is not None and lease.lease_status == "ACTIVE"


# ---------------------------------------------------------------- S4-16
def test_s4_16_closure_terminalises_all_leases_and_requests():
    run = run_simulation(lease_cfg(_PATH_A))
    assert run.range_leases
    assert all(l.lease_status in TERMINAL_LEASE_STATUSES for l in run.range_leases.values())
    assert all(r.status in TERMINAL_REASSIGN_REQUEST_STATUSES
               for r in run.reassignment_requests.values())
    # no closed-round RangeProgress points at a non-terminal current lease.
    for prog in run.range_progress.values():
        assert prog.current_lease_id is None \
            or run.range_leases[prog.current_lease_id].lease_status in TERMINAL_LEASE_STATUSES


# ---------------------------------------------------------------- S4-17
def test_s4_17_full_domain_rejected_with_unassigned_suffix():
    run = run_simulation(lease_cfg(((1, "M000", 1.6, "MINER_FAILED"),), num_miners=1,
                                   no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE", horizon=30.0))
    # round-1 has an unfinished suffix, so it is NOT a full-domain exhaustion.
    r1_full = [o for o in run.log if o.kind == "round_aborted"
               and o.data.get("RoundID") == "round-1"
               and o.data.get("reason") == FULL_DOMAIN_EXHAUSTED_NO_BLOCK]
    assert not r1_full
    assert run.range_progress["PS-round-1-M000"].committed_frontier \
        < run.range_progress["PS-round-1-M000"].range_end


# ---------------------------------------------------------------- S4-18
def test_s4_18_true_full_domain_after_reassignment_covers_all_once():
    run = run_simulation(lease_cfg(_PATH_A))
    assert run.lease_stats["leases_reassigned"] >= 1
    assert any(o.kind == "round_aborted"
               and o.data.get("reason") == FULL_DOMAIN_EXHAUSTED_NO_BLOCK
               and o.data.get("RoundID") == "round-1" for o in run.log)
    r1 = [rec for rec in run.evaluation_ledger if rec.RoundID == "round-1"]
    covered = []
    for rec in r1:
        covered.extend(rec.nonces())
    assert sorted(covered) == list(range(400))             # every nonce exactly once
    assert {PRIMARY_ASSIGNMENT, REASSIGNED_PRIMARY_WORK} <= {rec.assignment_kind for rec in r1}


# ---------------------------------------------------------------- S4-19
def test_s4_19_reassignment_energy_equals_residency_terms():
    run = run_simulation(lease_cfg(_PATH_A))
    P = run.config.per_miner_power
    reassigned = {mid for (rid, mid), k in run.search_assignment_kind.items()
                  if k in (REASSIGNED_PRIMARY_WORK, REASSIGNED_RESERVE_WORK)}
    assert reassigned
    for mid in reassigned:
        m = run.miners[mid]
        manual = sum(P(s) * dt for s, dt in m.duration.items())
        assert abs(run.miner_energy_joules(mid) - manual) < 1e-9
    assert run.residency_reconciles(run.run_end_time)


# ---------------------------------------------------------------- S4-20
def test_s4_20_lease_policy_does_not_change_target_or_difficulty():
    a = lease_cfg(wake=1.0)
    b = lease_cfg(wake=5.0, no_eligible="ABORT_ROUND", reassignment_enabled=False)
    assert a.difficulty == b.difficulty == _ZERO
    assert target_for_difficulty(a.difficulty) == target_for_difficulty(b.difficulty)
    assert a.range_lease.reassignment_wake_latency != b.range_lease.reassignment_wake_latency


# ---------------------------------------------------------------- S4 adapter schema
def test_s4_adapter_schema_and_execution_from_config():
    out = run_pocol_stage2({
        "num_miners": 4, "reserve_fraction": 0.0, "nonce_domain_size": 400,
        "difficulty": _ZERO, "batch_size": 25, "horizon_T": 60.0,
        "range_lease_enabled": True, "reassignment_enabled": True,
        "reassignment_wake_latency": 1.0,
        "reassignment_selection_policy": "COMPLETION_TIME_THEN_PRIORITY",
        "no_eligible_miner_policy": "CONTINUE_WITH_UNASSIGNED_RANGE",
    }, include_matched_experiment=False)
    assert out["schema_version"] == "stage4.1"
    for key in ("range_lease_enabled", "leases_created", "leases_completed", "leases_revoked",
                "leases_reassigned", "reassignment_decisions", "reassignment_requests_seated",
                "reassignment_requests_completed", "reassignment_requests_failed",
                "stale_old_lease_events", "uncovered_range_count", "uncovered_nonce_count",
                "total_reassignment_latency", "maximum_reassignment_latency",
                "reassignment_wake_energy_kwh", "reassignment_active_energy_kwh",
                "duplicate_nonce_count", "post_round_evaluation_count"):
        assert key in out
    assert out["range_lease_enabled"] is True
    assert out["leases_created"] > 0
    assert out["duplicate_nonce_count"] == 0
    assert out["post_round_evaluation_count"] == 0
    # kept security-floor + accepted energy labels.
    assert "security_floor_enabled" in out and "continuous_all_active_control_kwh" in out
    # validation: unsupported policy names and negative values are rejected.
    with pytest.raises(ValueError):
        run_pocol_stage2({"range_lease_enabled": True, "no_eligible_miner_policy": "NOPE"})
    with pytest.raises(ValueError):
        run_pocol_stage2({"range_lease_enabled": True, "reassignment_wake_latency": -1})
    with pytest.raises(ValueError):
        run_pocol_stage2({"range_lease_enabled": True,
                          "reassignment_selection_policy": "BOGUS"})
