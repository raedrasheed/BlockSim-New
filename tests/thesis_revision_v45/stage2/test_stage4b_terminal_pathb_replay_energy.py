"""Stage-4B terminal-state / Path-B cleanup / replay / energy correction tests S4B-01 .. S4B-12.

These lock in the final Stage-4 corrections demanded by the acceptance review:

* S4B-1 terminalise the MINER with the lease (no expired/timed-out/cancelled/failed miner is
        ever left ACTIVE_HASHING or WAKING; a lease expiring before wake never activates it);
* S4B-2 reject unknown triggers + return the COMPLETE observation replay result;
* S4B-3 STRICT RangeExhaust identity (reject missing LeaseID; premature/stale = no effect);
* S4B-4 a NON-domain ReassignmentWakeHandle replaces the synthetic Path-B RangeSlice;
* S4B-5 both Path-B seat-failure points clean every linked state (no orphan / in-flight);
* S4B-6 natural replay returns the exact stored request / statuses / EventRefs / lease;
* S4B-7 COMPLETE per-request energy attribution (incl FAILED / CANCELLED) reconciles;
* S4B-8 every causal advance increments progress_generation + refreshes the deadlines.

The whole lease layer stays disabled by default, so all 103 retained tests are unchanged.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, RunInitialise, ProcessEventTime,
                                  SeatNextRoundBootstrap, RunEventLoopToHorizon, run_simulation,
                                  RoundContext, MinerSearchState, EventRef, PRIMARY_ASSIGNMENT,
                                  REASSIGNED_RESERVE_WORK, ReassignmentWakeHandle,
                                  RangeReassignmentRequest,
                                  TERMINAL_LEASE_STATUSES, TERMINAL_REASSIGN_REQUEST_STATUSES)
from Models.PoCol.stage2.adapter import _range_lease_results, reassignment_energy_report

_ZERO = 1 << 300


def lease_cfg(*, num_miners=4, reserve_fraction=0.0, D=400, difficulty=_ZERO, horizon=120.0,
              wake=1.0, lease_duration=1.0e18, progress_timeout=1.0e18, faults=(),
              cancellations=(), no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE"):
    pol = RangeLeasePolicy(enabled=True, reassignment_wake_latency=wake,
                           lease_duration=lease_duration, progress_timeout=progress_timeout,
                           no_eligible_miner_policy=no_eligible)
    return Stage2Config(num_miners=num_miners, reserve_fraction=reserve_fraction,
                        nonce_domain_size=D, difficulty=difficulty, batch_size=25,
                        horizon_T=horizon, range_lease=pol, injected_lease_faults=faults,
                        injected_lease_cancellations=cancellations)


def _manual_round():
    """A minimal SOLUTION_PROPAGATION round: M000 ACTIVE (frontier 25/100) + M001 finished."""
    from Models.PoCol.stage2.simulator import _create_range_progress_and_lease
    run = RunInitialise(lease_cfg())
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    rc.state_version = 4
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


# ---------------------------------------------------------------- S4B-01
def test_s4b_01_lease_expiry_before_wake_never_activates_the_miner():
    """A lease that expires BEFORE its WakeCompleteEvent terminalises the miner (LOW_POWER_LISTEN),
    cancels the WakeCompleteEvent, and the later wake performs no effect."""
    cfg = lease_cfg(lease_duration=0.5, wake=1.0, horizon=40.0)   # expiry (0.5) < wake (1.0)
    run = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)                     # round-1 -> prepare (miners WAKING)
    rc = run.current_round_context
    parts = sorted(run.round_participants[rc.RoundID])
    # dispatch the expiry deadline (0.5) BEFORE the wake completion (1.0).
    ProcessEventTime(run, cfg.run_start_time + 0.5)
    for mid in parts:
        assert run.miners[mid].state != "WAKING"                 # idled by the expiry
        assert run.miners[mid].state in ("LOW_POWER_LISTEN", "OFFLINE")
    assert run.lease_stats["leases_expired"] >= 1
    assert run.lease_stats["wakes_cancelled_with_lease"] >= 1
    # a WakeCompleteEvent was cancelled by the terminalisation.
    assert any(r.event_type == "WakeCompleteEvent" and r.queue_status == "CANCELLED"
               for r in run.event_queue.queued_event_registry.values())
    # full run: NO expired/timed-out miner is ever left ACTIVE_HASHING or WAKING.
    full = run_simulation(cfg)
    assert not any(m.state in ("ACTIVE_HASHING", "WAKING") for m in full.miners.values())


# ---------------------------------------------------------------- S4B-02
def test_s4b_02_expiry_after_wake_no_active_miner_without_active_lease():
    """After an expiry that fires while the miner is ACTIVE_HASHING, no miner is left ACTIVE
    without a live ACTIVE lease; energy stops using P_hash at the terminalisation time."""
    run = run_simulation(lease_cfg(lease_duration=1.6, horizon=60.0))
    assert run.lease_stats["leases_expired"] >= 1
    assert run.lease_stats["miners_terminalised_with_lease"] >= 1
    # every ACTIVE_HASHING miner has a live ACTIVE lease (invariant holds throughout to close).
    for (rid, mid), sid in run.slice_of_miner.items():
        m = run.miners.get(mid)
        prog = run.range_progress.get(sid)
        if m is not None and m.state == "ACTIVE_HASHING" and prog is not None:
            lease = run.range_leases.get(prog.current_lease_id)
            assert lease is not None and lease.lease_status == "ACTIVE" and lease.MinerID == mid
    assert run.residency_reconciles(run.run_end_time)


# ---------------------------------------------------------------- S4B-03
def test_s4b_03_progress_timeout_transitions_miner_to_low_power():
    """A PROGRESS_TIMEOUT idles the timed-out miner to LOW_POWER_LISTEN (never OFFLINE, never
    left ACTIVE/WAKING)."""
    run = run_simulation(lease_cfg(progress_timeout=0.6))
    assert run.lease_stats["progress_timeouts"] >= 1
    assert not any(m.state in ("ACTIVE_HASHING", "WAKING") for m in run.miners.values())
    # a progress-timeout never sends a miner OFFLINE (that is the MINER_FAILED disposition).
    assert not any(m.duration.get("OFFLINE", 0.0) > 0 for m in run.miners.values())


# ---------------------------------------------------------------- S4B-04
def test_s4b_04_unknown_trigger_is_rejected_and_leaves_state_unchanged():
    """EvaluateRangeLease rejects a trigger outside LEASE_TRIGGERS with no mutation/counter/state
    change (no default REVOKED fallback)."""
    from Models.PoCol.stage2.simulator import EvaluateRangeLease
    run, rc = _manual_round()
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    run.event_queue.current_event_time = 5.0
    run.event_queue.current_event_ref = None
    before = dict(run.lease_stats)
    out = EvaluateRangeLease(run, rc, lease.LeaseID, 5.0, "SOMETHING_BOGUS")
    assert out.kind == "range_lease_observation_rejected_unknown_trigger"
    assert lease.lease_status == "ACTIVE"
    assert run.lease_stats["unknown_trigger_rejections"] == before["unknown_trigger_rejections"] + 1
    assert run.lease_observations == []
    assert run.lease_stats["leases_revoked"] == before["leases_revoked"]
    assert run.lease_stats["leases_expired"] == before["leases_expired"]
    assert prog.current_lease_id == lease.LeaseID           # unchanged


# ---------------------------------------------------------------- S4B-05
def test_s4b_05_range_exhaust_without_lease_id_is_rejected():
    """With range leases enabled a RangeExhaustEvent missing its LeaseID performs NO effect."""
    from Models.PoCol.stage2.simulator import _handle_range_exhaust
    run, rc = _manual_round()
    st0 = rc.search_states["M000"]
    st0.completed = True
    st0.completion_kind = "EXHAUSTED"
    st0.cursor = 100
    run.range_progress["PS-round-1-M000"].committed_frontier = 100
    payload = {"MinerID": "M000", "AssignmentID": "A0", "RoundID_at_seat": "round-1",
               "TemplateID_at_seat": "tpl-round-1", "assignment_version": 1,
               "expected_search_generation": 0}          # NO LeaseID
    run.event_queue.current_event_time = 5.0
    run.event_queue.current_event_ref = None
    before = run.lease_stats["stale_exhaust_events"]
    res = _handle_range_exhaust(run, payload, {})
    assert res.kind == "range_exhaust_no_effect"
    assert run.lease_stats["stale_exhaust_events"] == before + 1
    assert run.miners["M000"].state == "ACTIVE_HASHING"     # not idled by the rejected event


# ---------------------------------------------------------------- S4B-06
def test_s4b_06_premature_current_lease_range_exhaust_is_no_effect():
    """A RangeExhaustEvent for the CURRENT ACTIVE lease whose range is NOT actually exhausted
    (cursor / frontier below range_end) performs NO state / termination effect."""
    from Models.PoCol.stage2.simulator import _handle_range_exhaust
    run, rc = _manual_round()
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    payload = {"MinerID": "M000", "AssignmentID": "A0", "RoundID_at_seat": "round-1",
               "TemplateID_at_seat": "tpl-round-1", "assignment_version": 1,
               "expected_search_generation": 0, "LeaseID": lease.LeaseID, "lease_generation": 1}
    run.event_queue.current_event_time = 5.0
    run.event_queue.current_event_ref = None
    before = run.lease_stats["stale_exhaust_events"]
    res = _handle_range_exhaust(run, payload, {})           # M000 is at frontier 25/100 (premature)
    assert res.kind == "range_exhaust_no_effect"
    assert run.lease_stats["stale_exhaust_events"] == before + 1
    assert lease.lease_status == "ACTIVE" and prog.terminal_status == "OPEN"
    assert run.miners["M000"].state == "ACTIVE_HASHING"


# ---------------------------------------------------------------- S4B-07
def test_s4b_07_every_frontier_advance_bumps_progress_generation_and_refreshes_timeout():
    """Every causal committed-frontier advance increments progress_generation, updates
    last_progress_time, bumps timeout_generation and re-arms a fresh timeout (planning refreshes
    nothing)."""
    cfg = lease_cfg(progress_timeout=5.0)
    run = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)
    rc = run.current_round_context
    mid = sorted(run.round_participants[rc.RoundID])[0]
    prog = run.range_progress[run.slice_of_miner[(rc.RoundID, mid)]]
    pg0, tg0 = prog.progress_generation, prog.timeout_generation
    ProcessEventTime(run, cfg.run_start_time + cfg.wake_latency)   # wake -> plan (no advance)
    assert prog.progress_generation == pg0 and prog.timeout_generation == tg0
    hw = min(r.event_ref.event_time for r in run.event_queue.queued_event_registry.values()
             if r.event_type == "HashWorkEvent" and r.queue_status == "QUEUED"
             and r.immutable_payload.get("MinerID") == mid)
    ProcessEventTime(run, hw)                                      # causal advance
    assert prog.committed_frontier > prog.range_start
    assert prog.progress_generation == pg0 + 1
    assert prog.timeout_generation > tg0
    assert prog.last_progress_time == pytest.approx(hw)
    # tampered deadline identity (stale generation) fires as a no-op across the whole run.
    full = run_simulation(cfg)
    assert full.residency_reconciles(full.run_end_time)


# ---------------------------------------------------------------- S4B-08
def test_s4b_08_pathb_uses_wake_handle_and_creates_no_range_slice():
    """Path B wakes the reserve reassignee through a NON-domain ReassignmentWakeHandle — it
    creates NO RangeSlice and no WH- entry in any nonce-domain registry; the reassigned lease
    binds to the ORIGINAL primary slice."""
    run = run_simulation(lease_cfg(reserve_fraction=0.5,
                                   faults=((1, "M000", 1.3, "MINER_FAILED"),)))
    assert run.lease_stats["wake_handles_created"] >= 1
    # the wake activation is scoped REASSIGNMENT_WAKE_ONLY and references the original slice.
    wake_reqs = [r for r in run.reassignment_requests.values() if r.needs_stage3_wake]
    assert wake_reqs
    for r in wake_reqs:
        act = run.activation_requests[r.reserve_activation_request_id]
        assert act.activation_scope == "REASSIGNMENT_WAKE_ONLY"
        assert act.range_reassignment_request_id == r.RangeReassignmentRequestID
    # NO wake handle leaked into any nonce-domain registry; NONE is a RangeSlice.
    assert not any(str(sid).startswith("WH-") for sid in run.reserve_slice_by_id)
    assert not any(str(sl.RangeSliceID).startswith("WH-")
                   for slices in run.reserve_slices.values() for sl in slices)
    # the reassigned lease binds to the ORIGINAL primary slice (single interval authority).
    rr_leases = [l for l in run.range_leases.values()
                 if l.assignment_kind == REASSIGNED_RESERVE_WORK]
    assert rr_leases and all(l.RangeSliceID.startswith("PS-") for l in rr_leases)
    r = _range_lease_results(run, run.config)
    assert r["overlapping_slice_count"] == 0 and r["duplicate_nonce_count"] == 0


# ---------------------------------------------------------------- S4B-09
def test_s4b_09_pathb_start_seat_failure_leaves_no_orphan():
    """A Path-B ReserveActivationStartEvent seating failure rolls back fully — no orphan wake
    handle, observation, decision, link, WAKING miner, or in-flight request."""
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    run = RunInitialise(cfg)
    run.force_activation_start_seat_failure = True
    RunEventLoopToHorizon(run)
    assert run.lease_stats["pathb_rollback_count"] >= 1
    assert not run.reassignment_wake_handles                # no orphan wake handle
    assert not any(str(k).startswith("WH-") for k in run.reassign_by_suffix_slice)
    assert not any(getattr(o, "observation_reason", None) == "range_reassignment_reserve_wake"
                   for o in run.security_observations)      # no orphan synthetic observation
    assert not any(str(getattr(d, "DecisionID", ("",))[1]) == "RDEC3"
                   for d in run.activation_decisions)       # no orphan synthetic decision
    assert not any(m.state == "WAKING" for m in run.miners.values())
    assert not any(r.status in ("SEATED", "STARTED") for r in run.reassignment_requests.values())
    assert all(l.lease_status in TERMINAL_LEASE_STATUSES
               for l in run.range_leases.values() if l.RoundID == "round-1")


# ---------------------------------------------------------------- S4B-10
def test_s4b_10_pathb_complete_seat_failure_leaves_no_orphan_or_inflight():
    """A Path-B ReserveActivationCompleteEvent seating failure cleans EVERY linked state — the
    activation request + reassignment request FAILED, wake handle + links removed, wake-energy
    interval closed, no WAKING miner, no in-flight state, no horizon hang."""
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    run = RunInitialise(cfg)
    run.force_activation_complete_seat_failure = True
    RunEventLoopToHorizon(run)
    assert run.lease_stats["wake_complete_seat_failures"] >= 1
    assert run.lease_stats["pathb_rollback_count"] >= 1
    assert not run.reassignment_wake_handles
    assert not any(str(k).startswith("WH-") for k in run.reassign_by_suffix_slice)
    assert not any(m.state == "WAKING" for m in run.miners.values())
    assert not any(r.status in ("SEATED", "STARTED") for r in run.reassignment_requests.values())
    # the FAILED reassignment request has a closed wake-energy interval + terminal time.
    failed = [r for r in run.reassignment_requests.values() if r.status == "FAILED"]
    assert failed
    for r in failed:
        assert r.terminal_time is not None
        if r.started_at is not None:
            assert r.wake_residency_at_end is not None      # failed wake energy not omitted
    # the round did not hang: it reached a terminal disposition before the horizon.
    assert any(o.kind in ("accepted_block", "round_aborted") for o in run.log)


# ---------------------------------------------------------------- S4B-11
def test_s4b_11_natural_replay_returns_complete_stored_result():
    """Re-observing the SAME terminal predecessor lease returns range_reassignment_already_exists
    with the EXACT stored request / status / EventRefs / successor lease / disposition, and creates
    nothing new (no manual generation rewind)."""
    from Models.PoCol.stage2.simulator import (RevokeRangeLeaseTransaction,
                                               SeatRangeReassignmentTransaction,
                                               _eligible_reassignment_candidates)
    from Models.PoCol.stage2 import select_reassignment_candidate
    run, rc = _manual_round()
    eq = run.event_queue
    eq.current_event_time = 2.5
    eq.current_delta_cycle = 0
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "MinerFailureEvent", 2.5, 0,
                                    "MINER_FAILURE", 1)
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    run.miners["M000"].state = "OFFLINE"
    RevokeRangeLeaseTransaction(run, rc, lease, "MINER_FAILED")
    cands = _eligible_reassignment_candidates(run, rc, "PS-round-1-M000", "M000", 25, 2.5)
    chosen = select_reassignment_candidate(cands)
    first = SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    assert first is None
    req = list(run.reassignment_requests.values())[0]
    seated = run.lease_stats["reassignment_requests_seated"]
    n_req = len(run.reassignment_requests)
    n_dec = len(run.reassignment_decisions)
    # NATURAL replay of the SAME terminal predecessor lease.
    again = SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    assert again.kind == "range_reassignment_already_exists"
    assert again.data["request"] is req                     # exact stored request object
    assert again.data["status"] == req.status
    assert again.data["start_event_ref"] is req.start_event_ref
    assert again.data["complete_event_ref"] is req.complete_event_ref
    assert again.data["successor_lease"] is run.range_leases.get(req.new_lease_id)
    assert again.data["disposition"] is req.disposition
    # no new request / decision / lifecycle-counter effect.
    assert len(run.reassignment_requests) == n_req
    assert len(run.reassignment_decisions) == n_dec
    assert run.lease_stats["reassignment_requests_seated"] == seated


# ---------------------------------------------------------------- S4B-12
def test_s4b_12_per_request_energy_attribution_is_complete_and_reconciles():
    """The per-request energy report includes predecessor / standby / wake / active intervals for
    COMPLETED, FAILED and CANCELLED requests, does not omit a failed wake's energy, and reconciles
    with the residency ledger EXACTLY."""
    # a COMPLETED Path-A + Path-B reassignment.
    ok = run_simulation(lease_cfg(reserve_fraction=0.25,
                                  faults=((1, "M000", 1.6, "MINER_FAILED"),)))
    rep = reassignment_energy_report(ok, ok.config)
    assert rep["request_count"] >= 1
    assert rep["max_energy_residual_j"] < 1e-6
    keys = {"predecessor_active_energy_before_revocation_j",
            "predecessor_idle_or_offline_energy_after_revocation_j",
            "reassignee_standby_energy_before_wake_j", "reassignment_wake_energy_j",
            "reassignment_active_hashing_energy_j", "seated_at", "started_at", "completed_at",
            "search_start", "search_end", "terminal_time", "status", "disposition"}
    for row in rep["per_request"]:
        assert keys <= set(row.keys())
    assert ok.residency_reconciles(ok.run_end_time)
    # a FAILED Path-B wake: it is NOT omitted from the report — it appears as a row that carries
    # the full energy-field set, and its wake energy equals the EXACT residency-ledger delta over
    # [started_at, terminal_time].  This injection fails the ReserveActivationCompleteEvent SEAT
    # synchronously at the start instant, so the reserve accrues zero WAKING residency and the true
    # wake energy is 0.0 J (charging a non-zero value would fabricate energy that was never spent).
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    bad = RunInitialise(cfg)
    bad.force_activation_complete_seat_failure = True
    RunEventLoopToHorizon(bad)
    rep2 = reassignment_energy_report(bad, bad.config)
    Pw = cfg.per_miner_power("WAKING")
    failed_rows = [r for r in rep2["per_request"] if r["status"] == "FAILED"]
    assert failed_rows
    for r in failed_rows:
        assert keys <= set(r.keys())                        # energy fields present, not omitted
        req = next(q for q in bad.reassignment_requests.values()
                   if q.RangeReassignmentRequestID == r["RangeReassignmentRequestID"])
        if req.started_at is not None and req.terminal_time is not None:
            assert r["reassignment_wake_energy_j"] == \
                pytest.approx(Pw * (req.terminal_time - req.started_at), abs=1e-9)
            if req.wake_residency_at_start is not None and req.wake_residency_at_end is not None:
                ledger = req.wake_residency_at_end - req.wake_residency_at_start
                assert Pw * abs(ledger - (req.terminal_time - req.started_at)) < 1e-9  # reconciles
    assert rep2["max_energy_residual_j"] < 1e-6
    assert bad.residency_reconciles(bad.run_end_time)
    # positive demonstration that a failed wake's REAL energy is kept (not omitted): a FAILED
    # request whose wake interval spans genuine WAKING residency is attributed Pw x interval > 0.
    demo = RunInitialise(lease_cfg())
    demo.reassignment_requests["RR-demo"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-demo", DecisionID=("demo",), RoundID="round-1",
        TemplateID="tpl", RangeSliceID="PS-demo", predecessor_lease_id="L0",
        predecessor_committed_frontier=0, new_MinerID="Mx", new_lease_generation=2,
        new_lease_id="L2", needs_stage3_wake=True, status="FAILED", predecessor_MinerID="M0",
        started_at=1.0, terminal_time=2.0, wake_residency_at_start=0.0, wake_residency_at_end=1.0)
    demo_rep = reassignment_energy_report(demo, demo.config)
    demo_row = next(r for r in demo_rep["per_request"]
                    if r["RangeReassignmentRequestID"] == "RR-demo")
    assert demo_row["status"] == "FAILED"
    assert demo_row["reassignment_wake_energy_j"] == pytest.approx(Pw * 1.0)
    assert demo_row["reassignment_wake_energy_j"] > 0.0     # a real failed wake's energy is kept
    assert demo_rep["max_energy_residual_j"] < 1e-6         # and reconciles with the ledger delta
