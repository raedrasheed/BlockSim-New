"""Stage-2 named driver-event seating owners and the sim-driver intake.

Realises AG4/AH1-AH4/AI1-AI5/AI8: every driver wrapper has one named idempotent seating
owner; the seat owner publishes the reverse binding and drives PENDING -> SEATED
atomically with the seat; the intake checks round state + scope before seating.
"""
from __future__ import annotations

from typing import Any

from .events import (Driver, EventQueue, Outcome, ScheduleEvent, TerminalRotation,
                     CancelQueuedEvent, ordinary_dispatch_origin,
                     next_representable_simulation_time)
from .context import RunContext, EXACT_ROUND, NEXT_AVAILABLE_ROUND, RUN_LEVEL

# round states that admit each driver kind's event_type.
_TERMINAL = ("ROUND_ACCEPTED", "ROUND_ABORTED")
_REGISTRATION_ADMITTING = ("ROUND_INITIALISING", "TEMPLATE_COMMITMENT", "ASSIGNMENT")
_RESERVE_ADMITTING = ("SECURITY_RECOVERY", "ASSIGNMENT")


def _round_admits(kind: str, rc: Any) -> bool:
    if rc.round_state in _TERMINAL:
        return False
    if kind == "MINER_JOIN":
        return rc.round_state in _REGISTRATION_ADMITTING
    if kind == "ORDINARY_RESERVE_DEFICIT":
        return rc.round_state in _RESERVE_ADMITTING
    return False


def scope_admits(round_scope: Any, kind: str, rc: Any) -> str:
    """AI5: SCOPE_ADMIT | SCOPE_WAIT | SCOPE_STALE."""
    if round_scope == RUN_LEVEL:
        return "SCOPE_STALE"
    if round_scope == NEXT_AVAILABLE_ROUND:
        return "SCOPE_ADMIT" if _round_admits(kind, rc) else "SCOPE_WAIT"
    if isinstance(round_scope, tuple) and round_scope[0] == "EXACT_ROUND":
        rid = round_scope[1]
        if rid != rc.RoundID:
            return "SCOPE_STALE"
        return "SCOPE_ADMIT" if _round_admits(kind, rc) else "SCOPE_STALE"
    return "SCOPE_STALE"


def _legal_effective_time(run_ctx: RunContext, requested: float) -> float:
    """backlog-4: a legal effective seat time >= frontier and not finalised."""
    eq = run_ctx.event_queue
    frontier = run_ctx.last_finalised_event_time
    t = requested
    if frontier is not None and t <= frontier:
        t = next_representable_simulation_time(frontier)
    while t in eq.finalised_event_times:
        t = next_representable_simulation_time(t)
    return t


def SeatDriverEventTransaction(run_ctx: RunContext, key: Any, dr: Any, event_type: str,
                               target: float, microphase: str, payload: Any,
                               origin: Any) -> Outcome:
    """S2A-5: schedule + publish (reverse binding + PENDING->SEATED) as ONE transaction.

    Every step's result is captured and inspected.  If scheduler insertion succeeds but
    request publication fails, the newly queued event is cancelled and the reverse
    binding removed (compensating transaction), and a structured seat-publication failure
    is returned — the split happy-path publication is eliminated.
    """
    eq = run_ctx.event_queue
    r = ScheduleEvent(eq, run_ctx.current_round_context, event_type, target, microphase,
                      payload, origin)
    if r.kind != "scheduled":
        return Outcome("seat_scheduling_failed", reason=r)
    event_ref = r.event_ref
    # injection hook (tests only): scheduler committed, request publication now fails.
    if getattr(run_ctx, "force_seat_publication_failure", False):
        CancelQueuedEvent(eq, run_ctx, event_ref,
                          cancellation_reason="seat_publication_failure_compensation")
        run_ctx.driver_event_seat.pop(key, None)
        run_ctx.driver_request_by_seat_event_ref.pop(event_ref, None)
        return Outcome("seat_publication_failed", event_ref=event_ref,
                       reason=Outcome("forced_seat_publication_failure"))
    # publish the reverse binding, then drive PENDING -> SEATED; capture the result.
    run_ctx.driver_event_seat[key] = event_ref
    run_ctx.driver_request_by_seat_event_ref[event_ref] = dr.DriverRequestID
    dr.seated_event_ref = event_ref
    st = run_ctx.set_driver_request_status(
        dr.DriverRequestID, expected_status="PENDING", new_status="SEATED",
        disposition=Outcome("driver_request_seated", event_ref=event_ref))
    if st.kind != "driver_request_status_set":
        # compensate: remove the binding FIRST, then cancel the queued event.
        run_ctx.driver_event_seat.pop(key, None)
        run_ctx.driver_request_by_seat_event_ref.pop(event_ref, None)
        dr.seated_event_ref = None
        CancelQueuedEvent(eq, run_ctx, event_ref,
                          cancellation_reason="seat_publication_failure_compensation")
        return Outcome("seat_publication_failed", event_ref=event_ref, reason=st)
    run_ctx.pending_driver_request_index.discard(dr.DriverRequestID)
    return Outcome("seat_committed", event_ref=event_ref)


def _seat_live(run_ctx: RunContext, key: Any):
    er = run_ctx.driver_event_seat.get(key)
    if er is not None:
        rec = run_ctx.event_queue.queued_event_registry.get(er)
        if rec is not None and rec.queue_status in ("QUEUED", "DISPATCHING", "CONSUMED"):
            return er
    return None


# --------------------------------------------------------------------- SeatMinerRegister
def SeatMinerRegister(run_ctx: RunContext, driver_request: Any,
                      admission_mode: str) -> Outcome:
    """AG4/AH1/AI1: named owner for MinerRegisterEvent."""
    dr = driver_request
    eq = run_ctx.event_queue
    key = ("MINER_REGISTER", dr.DriverRequestID)
    live = _seat_live(run_ctx, key)
    if live is not None:
        return Outcome("miner_register_already_seated",
                       DriverRequestID=dr.DriverRequestID, event_ref=live)
    jr = dr.payload["join_request"]
    rid_at_seat = run_ctx.current_round_context.RoundID
    if admission_mode == "IN_DISPATCH_GENESIS":
        target = eq.current_event_time
        origin = ordinary_dispatch_origin(eq)
    else:  # DRIVER_INTAKE
        target = _legal_effective_time(run_ctx, dr.requested_event_time)
        dr.effective_event_time = target
        origin = Driver(driver_source_kind="MINER_JOIN",
                        driver_request_id=dr.DriverRequestID,
                        source_event_time=dr.driver_admission_time,
                        target_event_time=target,
                        intended_round_scope=dr.round_scope,
                        run_ctx=run_ctx, eq=eq)
    payload = {"join_request": jr, "DriverRequestID": dr.DriverRequestID,   # S2A-4 binding
               "round_scope": dr.round_scope, "RoundID_at_seat": rid_at_seat}
    tx = SeatDriverEventTransaction(run_ctx, key, dr, "MinerRegisterEvent", target,
                                    "REGISTRATION", payload, origin)
    if tx.kind == "seat_committed":
        return Outcome("miner_register_seated", DriverRequestID=dr.DriverRequestID,
                       event_ref=tx.event_ref)
    return Outcome("miner_register_seat_failed", DriverRequestID=dr.DriverRequestID,
                   reason=tx)


# --------------------------------------------------------------------- SeatReserveActivate
def SeatReserveActivate(run_ctx: RunContext, driver_request: Any) -> Outcome:
    """AG4/AH1: named owner for ReserveActivateEvent (always EXACT_ROUND, AI5)."""
    dr = driver_request
    eq = run_ctx.event_queue
    key = ("RESERVE_ACTIVATE", dr.DriverRequestID)
    live = _seat_live(run_ctx, key)
    if live is not None:
        return Outcome("reserve_activate_already_seated",
                       DriverRequestID=dr.DriverRequestID, event_ref=live)
    rc = run_ctx.current_round_context
    activation_seq = rc.reserve_activation_seq
    target = _legal_effective_time(run_ctx, dr.requested_event_time)
    dr.effective_event_time = target
    origin = Driver(driver_source_kind="ORDINARY_RESERVE_DEFICIT",
                    driver_request_id=dr.DriverRequestID,
                    source_event_time=dr.driver_admission_time,
                    target_event_time=target, intended_round_scope=dr.round_scope,
                    run_ctx=run_ctx, eq=eq)
    payload = {"RoundID_at_seat": dr.payload["RoundID_at_seat"],
               "deficit": dr.payload["deficit"], "activation_seq": activation_seq,
               "DriverRequestID": dr.DriverRequestID, "round_scope": dr.round_scope}  # S2A-4 binding
    tx = SeatDriverEventTransaction(run_ctx, key, dr, "ReserveActivateEvent", target,
                                    "RECOVERY_ACTIVATE", payload, origin)
    if tx.kind == "seat_committed":
        rc.reserve_activation_seq = activation_seq + 1
        return Outcome("reserve_activate_seated", DriverRequestID=dr.DriverRequestID,
                       event_ref=tx.event_ref)
    return Outcome("reserve_activate_seat_failed", DriverRequestID=dr.DriverRequestID,
                   reason=tx)


# --------------------------------------------------------------------- SeatNextRoundBootstrap
def SeatNextRoundBootstrap(run_ctx: RunContext) -> Outcome:
    """AG4/AH1/AH2/AH3/AI8: seat a round's RoundInitialiseEvent (DRIVER or TERMINAL_ROTATION)."""
    eq = run_ctx.event_queue
    br = run_ctx.current_bootstrap_request
    if br is None:
        return Outcome("round_bootstrap_no_request")
    key = ("ROUND_INITIALISE", br.BootstrapRequestID)
    live = _seat_live(run_ctx, key)
    if live is not None:
        return Outcome("round_bootstrap_already_seated",
                       BootstrapRequestID=br.BootstrapRequestID, event_ref=live)
    round_setup_seq = run_ctx.next_round_setup_seq
    if br.predecessor_round_id == "RUN_START":
        origin = Driver(driver_source_kind="RUN_BOOTSTRAP",
                        driver_request_id=br.BootstrapRequestID,
                        source_event_time=run_ctx.config.run_start_time,
                        target_event_time=br.target_time,
                        intended_round_scope=RUN_LEVEL, run_ctx=run_ctx, eq=eq)
    else:
        origin = TerminalRotation(bootstrap_request_id=br.BootstrapRequestID,
                                  predecessor_terminal_time=br.predecessor_terminal_time,
                                  target_event_time=br.target_time,
                                  run_ctx=run_ctx, eq=eq)
    r = ScheduleEvent(eq, run_ctx.current_round_context, "RoundInitialiseEvent",
                      br.target_time, "ROUND_SETUP",
                      {"round_setup_seq": round_setup_seq}, origin)
    if r.kind == "scheduled":
        run_ctx.driver_event_seat[key] = r.event_ref
        run_ctx.next_round_setup_seq = round_setup_seq + 1
        return Outcome("round_bootstrap_seated", event_ref=r.event_ref,
                       BootstrapRequestID=br.BootstrapRequestID,
                       round_setup_seq=round_setup_seq)
    return Outcome("round_bootstrap_seat_failed",
                   BootstrapRequestID=br.BootstrapRequestID, reason=r)


# --------------------------------------------------------------------- SeatPendingDriverRequests
def SeatPendingDriverRequests(run_ctx: RunContext) -> Outcome:
    """AG4/AH4/AI5: the sim-driver intake — scope-gate then route each PENDING request."""
    rc = run_ctx.current_round_context
    if rc is None:
        return Outcome("driver_intake_no_round")
    seated = 0
    rejected = 0
    for drid in sorted(run_ctx.pending_driver_request_index,
                       key=lambda x: (str(x[0]), x[1])):
        dr = run_ctx.driver_request_registry[drid]
        if dr.status != "PENDING":
            continue
        verdict = scope_admits(dr.round_scope, dr.kind, rc)
        if verdict == "SCOPE_STALE":
            run_ctx.set_driver_request_status(
                drid, expected_status="PENDING", new_status="REJECTED",
                disposition=Outcome("driver_request_scope_stale",
                                    round_scope=dr.round_scope, RoundID=rc.RoundID))
            run_ctx.pending_driver_request_index.discard(drid)
            rejected += 1
            continue
        if verdict == "SCOPE_WAIT":
            continue
        if dr.kind == "MINER_JOIN":
            res = SeatMinerRegister(run_ctx, dr, admission_mode="DRIVER_INTAKE")
        else:
            res = SeatReserveActivate(run_ctx, dr)
        if res.kind in ("miner_register_seated", "reserve_activate_seated"):
            seated += 1
        elif res.kind in ("miner_register_already_seated",
                          "reserve_activate_already_seated"):
            run_ctx.pending_driver_request_index.discard(drid)
        else:  # seat failed
            run_ctx.set_driver_request_status(
                drid, expected_status="PENDING", new_status="REJECTED",
                disposition=Outcome("driver_request_rejected", reason=res))
            run_ctx.pending_driver_request_index.discard(drid)
            rejected += 1
    return Outcome("driver_intake_completed", seated_count=seated,
                   rejected_count=rejected)
