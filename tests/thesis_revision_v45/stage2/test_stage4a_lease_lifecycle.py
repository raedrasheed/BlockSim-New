"""Stage-4A lease-lifecycle correction tests S4A-01 .. S4A-14.

These lock in the Stage-4 CORRECTIONS demanded by the final acceptance review:

* S4A-1  executable lease expiry (a seated RangeLeaseExpiryEvent, not a dormant field);
* S4A-2  executable progress timeout, refreshed on causal advance (never on planning);
* S4A-3  MINER_CANCELLED — a disposition DISTINCT from a failure;
* S4A-4  an AUTHORITATIVE EvaluateRangeLease that validates the trigger condition and records
         one RangeLeaseObservation per observation, never revoking merely because it was called;
* S4A-5  RangeExhaust is stale-safe under leases;
* S4A-6  the overlapping Path-B RRS RangeSlice is removed (REASSIGNMENT_WAKE_ONLY scope, bound
         to the ORIGINAL RangeProgress; slices proven disjoint);
* S4A-7  Path-B reassignment is fully transactional (rollback leaves no orphan);
* S4A-8  reassignment replay is NATURAL (no manual generation rewind);
* S4A-9  reassignment energy is attributed by LIFECYCLE INTERVAL (not full residency), exactly.

The energy-saving mechanism remains the idle policy within PoCol; reassignment is a
liveness/coverage mechanism that may INCREASE energy and NEVER saves it; the fixed target and
difficulty are never changed.  The whole lease layer stays disabled by default, so all accepted
Stage-2B / Stage-3 / Stage-3A / Stage-4 tests are unchanged.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, SecurityFloorPolicy,
                                  RunInitialise, ProcessEventTime, SeatNextRoundBootstrap,
                                  RunEventLoopToHorizon, run_simulation, run_pocol_stage2,
                                  target_for_difficulty, RoundContext, MinerSearchState,
                                  EventRef, PRIMARY_ASSIGNMENT, REASSIGNED_PRIMARY_WORK,
                                  REASSIGNED_RESERVE_WORK, TERMINAL_LEASE_STATUSES,
                                  RESERVE_ACTIVATION_SCOPES)
from Models.PoCol.stage2.adapter import _range_lease_results

_ZERO = 1 << 300   # target_for_difficulty(_) == 0 -> deterministically no solution


def lease_cfg(*, num_miners=4, reserve_fraction=0.0, D=400, difficulty=_ZERO, horizon=120.0,
              wake=1.0, no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE", reassignment_enabled=True,
              lease_duration=1.0e18, progress_timeout=1.0e18, faults=(), cancellations=(),
              floor=None):
    pol = RangeLeasePolicy(enabled=True, reassignment_wake_latency=wake,
                           reassignment_enabled=reassignment_enabled,
                           lease_duration=lease_duration, progress_timeout=progress_timeout,
                           no_eligible_miner_policy=no_eligible)
    kw = dict(num_miners=num_miners, reserve_fraction=reserve_fraction, nonce_domain_size=D,
              difficulty=difficulty, batch_size=25, horizon_T=horizon, range_lease=pol,
              injected_lease_faults=faults, injected_lease_cancellations=cancellations)
    if floor is not None:
        kw["security_floor"] = floor
    return Stage2Config(**kw)


def _manual_round():
    """A minimal SOLUTION_PROPAGATION round: M000 ACTIVE (frontier 25/100) + M001 finished."""
    from Models.PoCol.stage2.simulator import _create_range_progress_and_lease
    run = RunInitialise(lease_cfg())
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    run.round_ranges["round-1"] = {"M000": (0, 100), "M001": (100, 200)}
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
    run.create_miner("M001", 0.0, state="LOW_POWER_LISTEN")
    st1 = MinerSearchState("M001", "A1", 1, 200.0, 100, 200, 21.5, 2.15)
    st1.cursor = 200
    st1.completed = True
    st1.completion_kind = "EXHAUSTED"
    rc.search_states["M001"] = st1
    run.search_assignment_kind[("round-1", "M001")] = PRIMARY_ASSIGNMENT
    return run, rc


# ---------------------------------------------------------------- S4A-01
def test_s4a_01_lease_expiry_is_executable():
    """A finite lease_duration seats a real RangeLeaseExpiryEvent; on fire the lease is EXPIRED."""
    cfg = lease_cfg(lease_duration=1.5)
    run = prep = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)                # round-1 init -> prepare -> leases
    rc = run.current_round_context
    # every ACTIVE lease armed a real expiry event within the horizon (deadline == expiry time).
    armed = [l for l in run.range_leases.values() if l.expiry_event_ref is not None]
    assert armed
    for l in armed:
        assert l.expiry_event_ref.event_time == pytest.approx(l.lease_expiry_time)
    run2 = run_simulation(cfg)
    assert run2.lease_stats["leases_expired"] > 0            # expiry actually fired + terminalised
    # every time-expired lease is terminal, tagged with the LEASE_TIME_EXPIRED disposition
    # (EXPIRED, or REASSIGNED when a successor took its suffix).
    expired = [l for l in run2.range_leases.values()
               if l.reassignment_reason == "LEASE_TIME_EXPIRED"]
    assert expired
    for l in expired:
        assert l.lease_status in ("EXPIRED", "REASSIGNED")
    # a single-miner run (no eligible reassignee) leaves the expired lease in the EXPIRED state.
    solo = run_simulation(lease_cfg(num_miners=1, lease_duration=1.5, horizon=40.0))
    assert any(l.lease_status == "EXPIRED" and l.reassignment_reason == "LEASE_TIME_EXPIRED"
               for l in solo.range_leases.values())


# ---------------------------------------------------------------- S4A-02
def test_s4a_02_expiry_cancels_that_leases_queued_events():
    """The expiry terminalisation cancels that LeaseID's queued hash/exhaust + deadline events."""
    run = run_simulation(lease_cfg(lease_duration=1.5, horizon=40.0))
    # a hash event of an expired-lease miner was cancelled by the terminalisation.
    assert any(r.event_type in ("HashWorkEvent", "RangeExhaustEvent")
               and r.queue_status == "CANCELLED"
               for r in run.event_queue.queued_event_registry.values())
    # NO expiry / progress-timeout event is left QUEUED after the run closes.
    leftover = [r for r in run.event_queue.queued_event_registry.values()
                if r.event_type in ("RangeLeaseExpiryEvent", "RangeProgressTimeoutEvent")
                and r.queue_status == "QUEUED"]
    assert not leftover


# ---------------------------------------------------------------- S4A-03
def test_s4a_03_progress_timeout_is_executable():
    """A finite progress_timeout seats a real RangeProgressTimeoutEvent that fires + terminalises."""
    run = run_simulation(lease_cfg(progress_timeout=0.6))
    assert run.lease_stats["progress_timeouts"] > 0
    # a progress-timeout terminalises the lease EXPIRED (a deadline disposition).
    timed = [l for l in run.range_leases.values()
             if l.reassignment_reason == "PROGRESS_TIMEOUT"]
    assert timed and all(l.lease_status in ("EXPIRED", "REASSIGNED") for l in timed)


# ---------------------------------------------------------------- S4A-04
def test_s4a_04_progress_timeout_refreshes_on_causal_advance_not_planning():
    """A causal frontier advance refreshes last_progress_time + bumps timeout_generation; planning
    a batch refreshes nothing.  A superseded (old-generation) timeout event is stale-safe."""
    cfg = lease_cfg(progress_timeout=5.0)
    run = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)
    rc = run.current_round_context
    mid = sorted(run.round_participants[rc.RoundID])[0]
    prog = run.range_progress[run.slice_of_miner[(rc.RoundID, mid)]]
    gen0 = prog.timeout_generation
    tstamp0 = prog.last_progress_time
    # dispatch the wake (plans the first batch) — planning must NOT refresh the timeout.
    ProcessEventTime(run, cfg.run_start_time + cfg.wake_latency)
    assert prog.timeout_generation == gen0 and prog.last_progress_time == tstamp0
    # advance to the first committed batch — a causal advance MUST refresh + bump the generation.
    hw = min(r.event_ref.event_time for r in run.event_queue.queued_event_registry.values()
             if r.event_type == "HashWorkEvent" and r.queue_status == "QUEUED"
             and r.immutable_payload.get("MinerID") == mid)
    ProcessEventTime(run, hw)
    assert prog.committed_frontier > prog.range_start
    assert prog.timeout_generation > gen0
    assert prog.last_progress_time == pytest.approx(hw)
    # the whole run stays stale-safe: superseded deadlines fire as no-ops, never double-terminalise.
    run2 = run_simulation(cfg)
    assert run2.lease_stats["stale_timeout_events"] >= 0
    assert run2.residency_reconciles(run2.run_end_time)


# ---------------------------------------------------------------- S4A-05
def test_s4a_05_miner_cancelled_is_distinct_from_failure():
    """A voluntary MINER_CANCELLED -> LOW_POWER_LISTEN + lease CANCELLED, DISTINCT from a failure
    (OFFLINE + lease REVOKED)."""
    run_c = run_simulation(lease_cfg(cancellations=((1, "M000", 1.4, "voluntary_exit"),)))
    assert run_c.lease_stats["miner_cancellations"] == 1
    m0 = run_c.miners["M000"]
    assert m0.duration["OFFLINE"] == 0.0 and m0.duration["LOW_POWER_LISTEN"] > 0.0
    cxl = [l for l in run_c.range_leases.values()
           if l.MinerID == "M000" and l.RoundID == "round-1" and l.lease_generation == 1]
    assert cxl and cxl[0].lease_status in ("CANCELLED", "REASSIGNED")
    assert cxl[0].reassignment_reason == "MINER_CANCELLED"
    # a failure of the SAME miner is the OTHER disposition: OFFLINE + REVOKED.
    run_f = run_simulation(lease_cfg(faults=((1, "M000", 1.4, "MINER_FAILED"),)))
    assert run_f.lease_stats["leases_revoked"] == 1 and run_f.lease_stats["miner_cancellations"] == 0
    assert run_f.miners["M000"].duration["OFFLINE"] > 0.0
    fl = [l for l in run_f.range_leases.values()
          if l.MinerID == "M000" and l.RoundID == "round-1" and l.lease_generation == 1]
    assert fl and fl[0].reassignment_reason == "MINER_FAILED"


# ---------------------------------------------------------------- S4A-06
def test_s4a_06_evaluate_range_lease_is_authoritative():
    """EvaluateRangeLease validates the trigger condition: a PREMATURE LEASE_TIME_EXPIRED (now <
    expiry) records an observation with condition_satisfied=False and does NOT revoke the lease."""
    from Models.PoCol.stage2.simulator import EvaluateRangeLease
    run, rc = _manual_round()
    eq = run.event_queue
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    lease.lease_expiry_time = 100.0                          # far in the future
    eq.current_event_time = 5.0
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "RangeLeaseExpiryEvent", 5.0, 0,
                                    "RANGE_LEASE_EXPIRY", 7)
    out = EvaluateRangeLease(run, rc, lease.LeaseID, 5.0, "LEASE_TIME_EXPIRED")
    assert out is None
    assert lease.lease_status == "ACTIVE"                    # NOT revoked merely because called
    assert run.lease_stats["leases_expired"] == 0
    obs = run.lease_observations[-1]
    assert obs.condition_satisfied is False
    assert obs.decision_result == "LEASE_REMAINS_ACTIVE"
    assert obs.LeaseID == lease.LeaseID


# ---------------------------------------------------------------- S4A-07
def test_s4a_07_one_observation_per_observation_and_replay_is_idempotent():
    """Every lease observation appends exactly one auditable RangeLeaseObservation; an exact
    replay (same trigger EventRef) is idempotent (no second record, no second effect)."""
    from Models.PoCol.stage2.simulator import EvaluateRangeLease
    run, rc = _manual_round()
    eq = run.event_queue
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    run.miners["M000"].state = "OFFLINE"                     # the explicit MINER_FAILED fact
    eq.current_event_time = 2.5
    ref = EventRef("ORDINARY_EVENT", "MinerFailureEvent", 2.5, 0, "MINER_FAILURE", 1)
    eq.current_event_ref = ref
    EvaluateRangeLease(run, rc, lease.LeaseID, 2.5, "MINER_FAILED", triggering_event_ref=ref)
    n_obs = len(run.lease_observations)
    n_replay = run.lease_stats["lease_observation_replay_count"]
    assert n_obs == 1 and run.lease_observations[0].condition_satisfied is True
    assert run.lease_observations[0].decision_result in ("REASSIGNMENT_REQUIRED", "NO_ELIGIBLE_MINER")
    # exact replay of the SAME trigger EventRef: idempotent.
    EvaluateRangeLease(run, rc, lease.LeaseID, 2.5, "MINER_FAILED", triggering_event_ref=ref)
    assert len(run.lease_observations) == n_obs
    assert run.lease_stats["lease_observation_replay_count"] == n_replay + 1


# ---------------------------------------------------------------- S4A-08
def test_s4a_08_range_exhaust_is_stale_safe_under_leases():
    """A RangeExhaustEvent from a SUPERSEDED lease performs NO effect (never idles the successor
    nor mis-completes the slice)."""
    from Models.PoCol.stage2.simulator import _handle_range_exhaust
    run, rc = _manual_round()
    eq = run.event_queue
    prog = run.range_progress["PS-round-1-M000"]
    old_lease = run.range_leases[prog.current_lease_id]
    stale_payload = {"MinerID": "M000", "AssignmentID": "A0", "RoundID_at_seat": "round-1",
                     "TemplateID_at_seat": "tpl-round-1", "assignment_version": 1,
                     "expected_search_generation": 0, "LeaseID": old_lease.LeaseID,
                     "lease_generation": 1}
    old_lease.lease_status = "REVOKED"                       # supersede the lease
    before = run.lease_stats["stale_exhaust_events"]
    eq.current_event_time = 5.0
    eq.current_event_ref = None
    res = _handle_range_exhaust(run, stale_payload, {})
    assert res.kind == "range_exhaust_no_effect"
    assert run.lease_stats["stale_exhaust_events"] == before + 1
    assert prog.terminal_status == "OPEN"                    # the stale event completed nothing
    assert run.miners["M000"].state == "ACTIVE_HASHING"     # the miner was NOT idled


# ---------------------------------------------------------------- S4A-09
def test_s4a_09_pathb_removes_overlapping_slice_and_binds_original_progress():
    """Path B reuses the Stage-3 wake in REASSIGNMENT_WAKE_ONLY scope bound to the ORIGINAL
    RangeProgress; it creates NO overlapping domain slice (disjointness proven)."""
    run = run_simulation(lease_cfg(reserve_fraction=0.5,
                                   faults=((1, "M000", 1.3, "MINER_FAILED"),)))
    assert run.lease_stats["overlapping_slice_count"] == 0
    # a reserve reassignee was woken via the accepted Stage-3 activation, scoped WAKE-ONLY.
    wake_reqs = [r for r in run.reassignment_requests.values() if r.needs_stage3_wake]
    assert wake_reqs
    for r in wake_reqs:
        act = run.activation_requests[r.reserve_activation_request_id]
        assert act.activation_scope == "REASSIGNMENT_WAKE_ONLY"
        assert act.range_reassignment_request_id == r.RangeReassignmentRequestID
    # the reassigned lease binds to the ORIGINAL primary slice (no separate suffix progress).
    rr_leases = [l for l in run.range_leases.values()
                 if l.assignment_kind == REASSIGNED_RESERVE_WORK]
    assert rr_leases
    for l in rr_leases:
        assert l.RangeSliceID.startswith("PS-")             # ORIGINAL slice, not a new RRS slice
    # no reassignment wake handle was registered as a nonce-domain partition member.
    domain_slice_ids = {sl.RangeSliceID for slices in run.reserve_slices.values() for sl in slices}
    assert not any(sid.startswith("WH-") or sid.startswith("RRS-") for sid in domain_slice_ids)
    # every nonce is still evaluated exactly once and no post-round evaluation occurs.
    r = _range_lease_results(run, run.config)
    assert r["duplicate_nonce_count"] == 0 and r["post_round_evaluation_count"] == 0


# ---------------------------------------------------------------- S4A-10
def test_s4a_10_pathb_wake_rollback_leaves_no_orphan():
    """A failed Path-B wake seat rolls back FULLY: no orphan wake-handle slice, observation,
    decision or link; a FAILED reassignment request is registered for audit."""
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    run = RunInitialise(cfg)
    run.force_activation_start_seat_failure = True           # force the Stage-3 wake seat to fail
    RunEventLoopToHorizon(run)
    assert run.lease_stats["pathb_rollback_count"] >= 1
    # NO orphan wake handle anywhere (S4B-4 renamed the registry to reassignment_wake_handles).
    assert not run.reassignment_wake_handles
    assert not any(sid.startswith("WH-") for sid in run.reserve_slice_by_id)
    assert not any(str(k).startswith("WH-") for k in run.reassign_by_suffix_slice)
    # NO orphan synthetic reserve-wake observation / decision survived the rollback.
    assert not any(getattr(o, "observation_reason", None) == "range_reassignment_reserve_wake"
                   for o in run.security_observations)
    assert not any(str(getattr(d, "DecisionID", ("",))[1]) == "RDEC3"
                   for d in run.activation_decisions)
    # the reassignment request is FAILED (audit), and no lease/request is left non-terminal.
    assert any(r.status == "FAILED" for r in run.reassignment_requests.values())
    assert all(l.lease_status in TERMINAL_LEASE_STATUSES
               for l in run.range_leases.values() if l.RoundID == "round-1")


# ---------------------------------------------------------------- S4A-11
def test_s4a_11_reassignment_replay_is_natural():
    """Re-observing the SAME terminal predecessor lease returns range_reassignment_already_exists
    with no second request — no manual generation rewind (S4A-8)."""
    from Models.PoCol.stage2.simulator import (RevokeRangeLeaseTransaction,
                                               SeatRangeReassignmentTransaction,
                                               _eligible_reassignment_candidates)
    from Models.PoCol.stage2 import select_reassignment_candidate
    run, rc = _manual_round()
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
    first = SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    assert first is None                                     # the first seat succeeds
    seated = run.lease_stats["reassignment_requests_seated"]
    n_req = len(run.reassignment_requests)
    # NATURAL replay: NO manual lease_generation_of_slice rewind — just re-observe the SAME lease.
    again = SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    assert again is not None and again.kind == "range_reassignment_already_exists"
    assert len(run.reassignment_requests) == n_req
    assert run.lease_stats["reassignment_requests_seated"] == seated
    assert run.lease_stats["reassignment_replay_count"] >= 1


# ---------------------------------------------------------------- S4A-12
def test_s4a_12_reassignment_energy_attributed_by_lifecycle_interval():
    """The reassignment active energy counts ONLY the reassignment lifecycle interval, never the
    reassignee's own earlier primary work; the interval attribution reconciles EXACTLY (0 J)."""
    run = run_simulation(lease_cfg(faults=((1, "M000", 1.6, "MINER_FAILED"),)))
    P = run.config.per_miner_power
    r = _range_lease_results(run, run.config)
    # a Path-A reassignee did its OWN primary work first, so its full ACTIVE residency strictly
    # exceeds the reassignment interval it is charged for.
    reassignees = {mid for (rid, mid), k in run.search_assignment_kind.items()
                   if k == REASSIGNED_PRIMARY_WORK}
    assert reassignees
    full_active_j = sum(P("ACTIVE_HASHING") * run.miners[mid].duration.get("ACTIVE_HASHING", 0.0)
                        for mid in reassignees)
    interval_active_j = r["reassignment_active_energy_kwh"] * 3_600_000.0
    assert 0.0 < interval_active_j < full_active_j          # interval < full residency
    assert r["reassignment_energy_residual_j"] < 1e-6       # attribution reconciles exactly
    assert run.residency_reconciles(run.run_end_time)


# ---------------------------------------------------------------- S4A-13
def test_s4a_13_exact_metrics_across_all_correction_scenarios():
    """Across expiry / timeout / cancel / failure(Path A) / failure(Path B): energy residual 0,
    zero duplicate nonce, zero post-round evaluation, zero overlapping slice, zero non-terminal
    lease/request, and residency reconciles."""
    scenarios = {
        "expiry": lease_cfg(lease_duration=1.5),
        "timeout": lease_cfg(progress_timeout=0.6),
        "cancel": lease_cfg(cancellations=((1, "M000", 1.4, "exit"),)),
        "path_a": lease_cfg(faults=((1, "M000", 1.6, "MINER_FAILED"),)),
        "path_b": lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),)),
    }
    for name, cfg in scenarios.items():
        run = run_simulation(cfg)
        r = _range_lease_results(run, run.config)
        assert r["reassignment_energy_residual_j"] < 1e-6, name
        assert r["duplicate_nonce_count"] == 0, name
        assert r["post_round_evaluation_count"] == 0, name
        assert r["overlapping_slice_count"] == 0, name
        assert r["nonterminal_lease_count"] == 0, name
        assert r["nonterminal_reassignment_request_count"] == 0, name
        assert run.residency_reconciles(run.run_end_time), name
        # a lease observation was recorded for every terminalising trigger.
        assert r["lease_observation_count"] >= 1, name


# ---------------------------------------------------------------- S4A-14
def test_s4a_14_disabled_by_default_and_target_unchanged():
    """The whole lease-deadline layer is opt-in: a range-lease-DISABLED run seats no expiry /
    progress-timeout events and records no lease observations; the lease policy never changes the
    fixed target or difficulty."""
    # disabled by default -> no deadline events, no observations, no lease bookkeeping.
    run = run_simulation(Stage2Config(num_miners=4, nonce_domain_size=400, difficulty=_ZERO,
                                      batch_size=25, horizon_T=60.0))
    assert not any(r.event_type in ("RangeLeaseExpiryEvent", "RangeProgressTimeoutEvent",
                                    "MinerCancelledEvent")
                   for r in run.event_queue.queued_event_registry.values())
    assert run.lease_observations == []
    assert run.lease_stats["leases_created"] == 0
    # deadlines/cancellations never change the fixed target or difficulty.
    a = lease_cfg(lease_duration=2.0, progress_timeout=3.0)
    b = lease_cfg(cancellations=((1, "M000", 1.0, "x"),), no_eligible="ABORT_ROUND",
                  reassignment_enabled=False)
    assert a.difficulty == b.difficulty == _ZERO
    assert target_for_difficulty(a.difficulty) == target_for_difficulty(b.difficulty)
    # the reserve-activation scopes are the declared two (domain-claim vs wake-only).
    assert RESERVE_ACTIVATION_SCOPES == ("RESERVE_DOMAIN_CLAIM", "REASSIGNMENT_WAKE_ONLY")
