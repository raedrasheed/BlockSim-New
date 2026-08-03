"""Stage-2A semantic test vectors TV325-TV338 (executable, EXACT semantics).

Each vector exercises one mandatory Stage-1AJ backlog fix or a frozen Stage-1 scheduler
contract against the *executable* PoCol core (not a renamed approximation).  The algorithm
is PoCol; the energy-saving mechanism is the idle policy within PoCol.

Coverage of the S2A-7 minimum list:

    TV325  partial genesis seating where the THIRD seat actually fails (compensation)
    TV326  TemplateCommit seat failure AFTER all genesis seats exist (structured abort)
    TV327  queued EXACT_ROUND registration cancelled before rotation
    TV328  NEXT_AVAILABLE effective round/time binding (requested immutable)
    TV329  future queued events during partial finalization are cancelled
    TV330  failure between ScheduleEvent commit and request publication (compensation)
    TV331  cancellation status-publication failure (coherent + declared mismatch captured)
    TV332  two distinct equal-deficit reserve incidents -> distinct identities
    TV333  exact replay returns status, EventRef and disposition
    TV334  foreign RunContext sharing the SAME EQ is rejected
    TV335  duplicate genesis configuration produces a structured failure (no raw assert)
    TV336  cancelled request event reaching dispatch performs NO domain effect
    TV337  driver target before the simulation frontier is rejected
    TV338  driver-binding validation: stale RoundID/scope at dispatch -> NO domain effect
"""
from __future__ import annotations

from Models.PoCol.stage2 import (
    Stage2Config, RunInitialise, RunEventLoopToHorizon, RoundContext, RoundAbort,
    SeatMinerRegister, SeatNextRoundBootstrap, ProcessEventTime, ScheduleEvent, Driver,
    Outcome, EXACT_ROUND, NEXT_AVAILABLE_ROUND, RUN_LEVEL, CancelQueuedEvent,
    FinalizeSimulationRunPartial, run_simulation, a1_continuous_control_kwh,
    A1_BASELINE_KWH,
)


def fresh_run(**kw):
    kw.setdefault("num_miners", 0)
    return RunInitialise(Stage2Config(**kw))


def admitting_round(run, rid="round-1", state="ASSIGNMENT", t=0.0):
    rc = RoundContext(RoundID=rid, run_context=run, round_state=state)
    run.current_round_context = rc
    run.event_queue.current_event_time = t
    return rc


def _seat_join(run, mid, scope, requested=0.0):
    a = run.admit_driver_request("MINER_JOIN", requested, scope,
                                 {"join_request": {"MinerID": mid}})
    dr = run.driver_request_registry[a.DriverRequestID]
    return dr


# ---------------------------------------------------------------- TV325
def test_tv325_partial_genesis_third_seat_fails_round_aborts_through_closure():
    """S2B-5: first two genesis seats commit, the THIRD seat fails, and the round aborts
    through the ONE closure owner — the two seated events become CANCELLED, all three
    requests terminalise, and nothing leaks to the next round."""
    run = RunInitialise(Stage2Config(num_miners=3, horizon_T=100.0))
    run.genesis_seat_fail_at = 3                            # the third genesis seat fails
    assert SeatNextRoundBootstrap(run).kind == "round_bootstrap_seated"
    ProcessEventTime(run, 0.0, is_horizon=False)
    rc = run.current_round_context
    assert rc.round_state == "ROUND_ABORTED"
    assert rc.terminal_disposition == "genesis_registration_seat_failed"
    reg = [r for r in run.event_queue.queued_event_registry.values()
           if r.event_type == "MinerRegisterEvent"]
    assert len(reg) == 3                                    # seats 1, 2 + the compensated 3rd
    assert all(r.queue_status == "CANCELLED" for r in reg)  # first two cancelled by closure
    assert not any(r.queue_status == "QUEUED" for r in reg)  # no seat leaks to the next round
    genesis_reqs = [d for d in run.driver_request_registry.values() if d.kind == "MINER_JOIN"]
    assert len(genesis_reqs) == 3
    assert all(d.status in ("CANCELLED", "REJECTED") for d in genesis_reqs)   # all terminal
    assert not run.pending_driver_request_index
    assert any(o.kind == "round_initialise_aborted" for o in run.log)


# ---------------------------------------------------------------- TV326
def test_tv326_template_commit_seat_failure_after_genesis_seats_exist():
    """All genesis seats exist, then TemplateCommit seating fails -> structured round abort."""
    run = RunInitialise(Stage2Config(num_miners=3, horizon_T=100.0))
    run.force_template_commit_seat_failure = True
    assert SeatNextRoundBootstrap(run).kind == "round_bootstrap_seated"
    ProcessEventTime(run, 0.0, is_horizon=False)           # dispatch the RoundInitialiseEvent
    rc = run.current_round_context
    assert rc.round_state == "ROUND_ABORTED"
    assert rc.terminal_disposition == "template_commit_seat_failed"
    # the three genesis MinerRegisterEvents existed (seated) and were cancelled by closure.
    reg = [r for r in run.event_queue.queued_event_registry.values()
           if r.event_type == "MinerRegisterEvent"]
    assert len(reg) == 3
    assert all(r.queue_status == "CANCELLED" for r in reg)
    assert any(o.kind == "round_initialise_aborted" for o in run.log)


# ---------------------------------------------------------------- TV327
def test_tv327_queued_exact_round_event_cancelled_before_rotation():
    """A queued EXACT_ROUND driver event is cancelled at closure — never carried on."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    dr = _seat_join(run, "MX", EXACT_ROUND("round-1"))
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    assert run.event_queue.queued_event_registry[er].queue_status == "QUEUED"
    run.event_queue.current_event_time = 5.0
    RoundAbort(run, rc, "test_abort", envelope={})
    assert run.event_queue.queued_event_registry[er].queue_status == "CANCELLED"
    assert er not in run.event_queue.event_queue           # gone from the pending frontier
    assert dr.status == "CANCELLED"                        # request coherently terminalised


# ---------------------------------------------------------------- TV328
def test_tv328_next_available_effective_round_time_binding():
    """NEXT_AVAILABLE_ROUND seats at a legal effective time; requested stays immutable."""
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=60.0)
    run.last_finalised_event_time = 50.0
    run.event_queue.finalised_event_times.add(50.0)
    dr = _seat_join(run, "MN", NEXT_AVAILABLE_ROUND, requested=50.0)
    res = SeatMinerRegister(run, dr, "DRIVER_INTAKE")
    assert res.kind == "miner_register_seated"
    assert dr.requested_event_time == 50.0                 # immutable original (backlog-5)
    assert dr.effective_event_time > 50.0                  # legal effective seat time (backlog-4)
    assert dr.effective_event_time not in run.event_queue.finalised_event_times
    assert res.event_ref.event_time == dr.effective_event_time


# ---------------------------------------------------------------- TV329
def test_tv329_future_events_during_partial_finalization_are_cancelled():
    """A future queued event is cancelled by the partial finalizer; no live state remains."""
    run = fresh_run(horizon_T=1000.0)
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    run.last_finalised_event_time = 10.0
    dr = _seat_join(run, "MF", EXACT_ROUND("round-1"), requested=500.0)
    future_er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    assert future_er.event_time == 500.0                   # genuinely in the future
    assert run.event_queue.queued_event_registry[future_er].queue_status == "QUEUED"
    res = FinalizeSimulationRunPartial(run, partial_end_time=100.0, reason="test_partial")
    assert res.kind == "run_finalised_partial"
    assert res.partial_end_time == 100.0
    assert run.event_queue.queued_event_registry[future_er].queue_status == "CANCELLED"
    assert dr.status == "CANCELLED"
    assert run.run_end_time == 100.0 and run.run_disposition == "test_partial"
    assert not any(r.queue_status in ("QUEUED", "DISPATCHING")
                   for r in run.event_queue.queued_event_registry.values())
    assert not any(d.status in ("PENDING", "SEATED")
                   for d in run.driver_request_registry.values())


# ---------------------------------------------------------------- TV330
def test_tv330_failure_between_schedule_commit_and_request_publication():
    """A publication failure after the scheduler commit compensates the queued event."""
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    run.force_seat_publication_failure = True
    dr = _seat_join(run, "MG", EXACT_ROUND("round-1"))
    res = SeatMinerRegister(run, dr, "DRIVER_INTAKE")
    assert res.kind == "miner_register_seat_failed"
    assert res.reason.kind == "seat_publication_failed"
    comp_er = res.reason.event_ref
    assert run.event_queue.queued_event_registry[comp_er].queue_status == "CANCELLED"
    assert comp_er not in run.event_queue.event_queue      # rolled back off the frontier
    assert dr.status == "PENDING"                          # request never advanced to SEATED
    assert comp_er not in run.driver_request_by_seat_event_ref
    assert ("MINER_REGISTER", dr.DriverRequestID) not in run.driver_event_seat


# ---------------------------------------------------------------- TV331
def test_tv331_cancellation_status_publication_coherent_and_failure_captured():
    """Cancellation publishes the request status coherently, and a declared failure is captured."""
    # (a) coherent: a SEATED request is reconciled to CANCELLED with the queue entry.
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    dr = _seat_join(run, "MC", EXACT_ROUND("round-1"))
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    out = CancelQueuedEvent(run.event_queue, run, er, "test_cancel")
    assert out.kind == "event_cancelled"
    assert out.reconcile is not None and out.reconcile.kind == "driver_request_status_set"
    assert run.event_queue.queued_event_registry[er].queue_status == "CANCELLED"
    assert dr.status == "CANCELLED"
    # (b) declared failure: the request is terminalised out-of-band, so the reconcile mismatches
    #     — the cancellation still cancels the event but SURFACES the integrity failure.
    run2 = fresh_run()
    admitting_round(run2, "round-1", "ASSIGNMENT", t=0.0)
    dr2 = _seat_join(run2, "MC2", EXACT_ROUND("round-1"))
    er2 = SeatMinerRegister(run2, dr2, "DRIVER_INTAKE").event_ref
    run2.set_driver_request_status(dr2.DriverRequestID, "SEATED", "CANCELLED",
                                   Outcome("out_of_band"))
    out2 = CancelQueuedEvent(run2.event_queue, run2, er2, "test_cancel")
    assert out2.kind == "event_cancelled"
    assert out2.reconcile is not None
    assert out2.reconcile.kind == "driver_request_status_mismatch"   # declared, not swallowed
    assert run2.event_queue.queued_event_registry[er2].queue_status == "CANCELLED"


# ---------------------------------------------------------------- TV332
def test_tv332_distinct_equal_deficit_reserve_incidents():
    """Two distinct reserve incidents with EQUAL deficit get DISTINCT DriverRequestIDs."""
    run = fresh_run()
    p1 = {"RoundID_at_seat": "round-1", "deficit": 5, "incident_id": "inc-1"}
    p2 = {"RoundID_at_seat": "round-1", "deficit": 5, "incident_id": "inc-2"}
    a1 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0, EXACT_ROUND("round-1"), p1)
    a2 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0, EXACT_ROUND("round-1"), p2)
    assert a1.kind == "driver_request_admitted" and a2.kind == "driver_request_admitted"
    assert a1.DriverRequestID != a2.DriverRequestID


# ---------------------------------------------------------------- TV333
def test_tv333_exact_replay_returns_status_eventref_disposition():
    """A replay of the same logical request resolves to the exact seated record."""
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    dr = _seat_join(run, "MR", EXACT_ROUND("round-1"))
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    replay = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                      {"join_request": {"MinerID": "MR"}})
    assert replay.kind == "driver_request_already_admitted"
    assert replay.DriverRequestID == dr.DriverRequestID
    resolved = run.driver_request_registry[replay.DriverRequestID]
    assert resolved is dr
    assert resolved.status == "SEATED"                     # status
    assert resolved.seated_event_ref == er                 # EventRef
    assert resolved.disposition.kind == "driver_request_seated"   # disposition
    assert resolved.disposition.event_ref == er


# ---------------------------------------------------------------- TV334
def test_tv334_foreign_run_context_sharing_eq_rejected():
    """A driver seat whose carried RunContext is not the EQ owner is rejected (backlog-11)."""
    run = fresh_run()
    eq = run.event_queue
    foreign = fresh_run()                                  # its own distinct EQ
    origin = Driver("MINER_JOIN", ("x", 1), 0.0, 0.0, NEXT_AVAILABLE_ROUND,
                    run_ctx=foreign, eq=eq)                # foreign ctx, SAME eq
    res = ScheduleEvent(eq, None, "MinerRegisterEvent", 0.0, "REGISTRATION",
                        {"join_request": {"MinerID": "MZ"}, "DriverRequestID": ("x", 1),
                         "round_scope": NEXT_AVAILABLE_ROUND, "RoundID_at_seat": "round-1"},
                        origin)
    assert res.kind == "rejected_driver_context_mismatch"


# ---------------------------------------------------------------- TV335
def test_tv335_duplicate_genesis_configuration_structured_failure():
    """A duplicate genesis config produces a STRUCTURED abort (never a raw assertion)."""
    run = RunInitialise(Stage2Config(num_miners=0, horizon_T=100.0))
    run.genesis_miner_registry = [
        {"join_request": {"MinerID": "DUP"}},
        {"join_request": {"MinerID": "DUP"}},              # duplicate join-request identity
    ]
    assert SeatNextRoundBootstrap(run).kind == "round_bootstrap_seated"
    ProcessEventTime(run, 0.0, is_horizon=False)
    aborts = [o for o in run.log if o.kind == "round_initialise_aborted"]
    assert aborts
    assert aborts[0].reason.kind == "genesis_admission_failed"
    rc = run.current_round_context
    assert rc.round_state == "ROUND_ABORTED"
    assert rc.terminal_disposition == "genesis_admission_failed"
    # S2B-5 cleanup: zero PENDING requests, zero QUEUED genesis registrations remain.
    assert not run.pending_driver_request_index
    assert not any(r.event_type == "MinerRegisterEvent" and r.queue_status == "QUEUED"
                   for r in run.event_queue.queued_event_registry.values())
    assert all(d.status in ("CANCELLED", "REJECTED")
               for d in run.driver_request_registry.values() if d.kind == "MINER_JOIN")


# ---------------------------------------------------------------- TV336
def test_tv336_cancelled_request_event_at_dispatch_no_domain_effect():
    """A seat whose request was cancelled out-of-band performs NO domain effect at dispatch."""
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    dr = _seat_join(run, "MZ", EXACT_ROUND("round-1"))
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    # cancel the REQUEST out of band, leaving the event QUEUED and its reverse binding intact.
    run.set_driver_request_status(dr.DriverRequestID, "SEATED", "CANCELLED",
                                  Outcome("out_of_band_cancel"))
    assert dr.status == "CANCELLED"
    ProcessEventTime(run, er.event_time, is_horizon=False)
    assert "MZ" not in run.miners                          # no miner was created
    no_effect = [o for o in run.log if o.kind == "miner_register_no_effect"]
    assert no_effect
    assert no_effect[0].reason.kind == "driver_binding_not_seated"
    assert dr.status == "CANCELLED"                        # not resurrected to CONSUMED


# ---------------------------------------------------------------- TV337
def test_tv337_driver_target_before_frontier_rejected():
    """AI2: a driver seat whose target is behind the simulation frontier is rejected."""
    run = fresh_run()
    run.last_finalised_event_time = 100.0
    origin = Driver("MINER_JOIN", ("x", 1), 50.0, 50.0, NEXT_AVAILABLE_ROUND,
                    run_ctx=run, eq=run.event_queue)       # source<=target but target<frontier
    res = ScheduleEvent(run.event_queue, None, "MinerRegisterEvent", 50.0, "REGISTRATION",
                        {"join_request": {"MinerID": "MB"}, "DriverRequestID": ("x", 1),
                         "round_scope": NEXT_AVAILABLE_ROUND, "RoundID_at_seat": "round-1"},
                        origin)
    assert res.kind == "rejected_driver_target_before_simulation_frontier"


# ---------------------------------------------------------------- TV338
def test_tv338_driver_binding_stale_round_scope_no_domain_effect():
    """S2A-4: at dispatch, a seat stale for the CURRENT round performs NO domain effect."""
    run = fresh_run()
    admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    dr = _seat_join(run, "MS", EXACT_ROUND("round-1"))
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    # a NEW round becomes current; the round-1-scoped seat is now stale for it.
    admitting_round(run, "round-2", "ASSIGNMENT", t=0.0)
    assert dr.status == "SEATED"                           # still seated, binding intact
    ProcessEventTime(run, er.event_time, is_horizon=False)
    assert "MS" not in run.miners
    no_effect = [o for o in run.log if o.kind == "miner_register_no_effect"]
    assert no_effect
    assert no_effect[0].reason.kind in ("driver_binding_scope_stale",
                                        "driver_binding_round_mismatch")
