"""Stage-2 PoCol core simulator: RunInitialise, the round-lifecycle handlers, the
ProcessEventTime dispatcher, the run loop, and the full/partial finalizers.

Realises the mandatory core execution path across MULTIPLE rounds:

    RunInitialise -> first-round bootstrap -> genesis admission -> TemplateCommit
    -> participant preparation -> assignment creation -> StartWake -> WakeCompleteEvent
    -> ACTIVE_HASHING -> hash-work scheduling -> acceptance OR round abort
    -> round closure -> next-round bootstrap -> second round -> horizon or partial termination

The energy-saving mechanism is the idle policy within PoCol: reserve/idle/waking
residency is charged at low power (P_listen / P_wake), never nonce partitioning; no
dynamic difficulty is used.
"""
from __future__ import annotations

import math
from typing import Any, Dict, List, Optional

from .config import Stage2Config
from .events import (CancelQueuedEvent, EventQueue, Outcome, ScheduleEvent,
                     ordinary_dispatch_origin, next_representable_simulation_time,
                     candidate_template_id)
from .context import (BootstrapRequest, RunContext, RoundContext, EXACT_ROUND,
                      NEXT_AVAILABLE_ROUND)
from .driver import (SeatNextRoundBootstrap, SeatPendingDriverRequests, SeatMinerRegister)


# ============================================================ RunInitialise
def RunInitialise(config: Stage2Config, run_id: Any = "R") -> RunContext:
    """Create ALL per-run state ONCE and register the RUN_START bootstrap request."""
    rc = RunContext(run_id, config)
    rc.genesis_miner_registry = [
        {"join_request": {"MinerID": f"M{i:03d}"}} for i in range(config.num_miners)
    ]
    first = BootstrapRequest(BootstrapRequestID="RUN_START",
                             predecessor_round_id="RUN_START",
                             predecessor_terminal_time=None,
                             target_time=config.run_start_time)
    rc.bootstrap_request_registry["RUN_START"] = first
    rc.current_bootstrap_request = first
    return rc


# ============================================================ round-lifecycle handlers
def _handle_round_initialise(run_ctx: RunContext, payload: Dict[str, Any],
                             envelope: Dict[str, Any]) -> Outcome:
    cfg = run_ctx.config
    run_ctx.round_seq += 1
    rid = f"round-{run_ctx.round_seq}"
    prior = run_ctx.prior_round_terminal_state
    rc = RoundContext(RoundID=rid, run_context=run_ctx)
    run_ctx.current_round_context = rc
    t0 = run_ctx.event_queue.current_event_time

    # AI1/AI5: first round admits the genesis miner set (EXACT_ROUND) + barrier.
    if prior is None and run_ctx.genesis_miner_registry:
        expected = set()
        for g in sorted(run_ctx.genesis_miner_registry,
                        key=lambda e: e["join_request"]["MinerID"]):
            adm = run_ctx.admit_driver_request(
                kind="MINER_JOIN", requested_event_time=t0,
                round_scope=EXACT_ROUND(rid),
                payload={"join_request": g["join_request"]})
            if adm.kind != "driver_request_admitted":
                # backlog-12: structured outcome, never a raw assertion.
                rc.transition("ROUND_ABORTED")
                rc.terminal_disposition = "genesis_admission_failed"
                return Outcome("round_initialise_aborted", RoundID=rid,
                               reason=Outcome("genesis_admission_failed", detail=adm))
            expected.add(g["join_request"]["MinerID"])
        rc.barrier_expected = expected
        rc.barrier_registered = set()
        rc.barrier_satisfied = False
        run_ctx.genesis_miner_registry = []
        # AI1: seat each genesis MinerRegisterEvent SYNCHRONOUSLY at the non-finalised t0.
        for drid in sorted(list(run_ctx.pending_driver_request_index),
                           key=lambda x: (str(x[0]), x[1])):
            dr = run_ctx.driver_request_registry[drid]
            if dr.status != "PENDING" or dr.kind != "MINER_JOIN" \
                    or dr.round_scope != EXACT_ROUND(rid):
                continue
            gseat = SeatMinerRegister(run_ctx, dr, admission_mode="IN_DISPATCH_GENESIS")
            if gseat.kind == "miner_register_seat_failed":
                run_ctx.set_driver_request_status(
                    drid, expected_status="PENDING", new_status="REJECTED",
                    disposition=Outcome("driver_request_rejected", reason=gseat.reason))
                run_ctx.pending_driver_request_index.discard(drid)
                rc.transition("ROUND_ABORTED")
                rc.terminal_disposition = "genesis_registration_seat_failed"
                return Outcome("round_initialise_aborted", RoundID=rid,
                               reason=Outcome("genesis_registration_seat_failed_round_abort",
                                              detail=gseat))

    rc.transition("ROUND_INITIALISING")
    rc.transition("TEMPLATE_COMMITMENT")
    # AG4 step 3: seat TemplateCommitEvent (ORDINARY_DISPATCH — inside this dispatch).
    tc = _seat_template_commit(run_ctx, rid)
    if tc.kind == "template_commit_seat_failed":
        rc.transition("ROUND_ABORTED")
        rc.terminal_disposition = "template_commit_seat_failed"
        _close_and_publish(run_ctx, rc, "ROUND_ABORTED", envelope)
        return Outcome("round_initialise_aborted", RoundID=rid, reason=tc)
    return Outcome("round_initialised", RoundID=rid)


def _seat_template_commit(run_ctx: RunContext, rid: Any) -> Outcome:
    eq = run_ctx.event_queue
    key = ("TEMPLATE_COMMIT", rid)
    if key in run_ctx.driver_event_seat:
        return Outcome("template_commit_already_seated")
    template = {"id": f"tpl-{rid}"}
    r = ScheduleEvent(eq, run_ctx.current_round_context, "TemplateCommitEvent",
                      eq.current_event_time, "TEMPLATE_COMMIT",
                      {"RoundID_at_seat": rid, "candidate_template": template},
                      ordinary_dispatch_origin(eq))
    if r.kind == "scheduled":
        run_ctx.driver_event_seat[key] = r.event_ref
        return Outcome("template_commit_seated", event_ref=r.event_ref)
    return Outcome("template_commit_seat_failed", reason=r)


def _handle_miner_register(run_ctx: RunContext, payload: Dict[str, Any],
                           envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    jr = payload["join_request"]
    mid = jr["MinerID"]
    t = run_ctx.event_queue.current_event_time
    if mid not in run_ctx.miners:
        run_ctx.create_miner(mid, at_time=t, state="REGISTERED")
    # AH5/AI7: initial-registration barrier bookkeeping + participant-setup inspection.
    if mid not in rc.barrier_expected:
        return Outcome("miner_registered", MinerID=mid)
    rc.barrier_registered.add(mid)
    if not rc.barrier_registered >= rc.barrier_expected or rc.barrier_satisfied:
        return Outcome("miner_registered_barrier_pending", MinerID=mid)
    rc.barrier_satisfied = True
    if not (rc.round_state == "ASSIGNMENT" and rc.TemplateID_committed is not None):
        return Outcome("miner_registered_barrier_pending", MinerID=mid)
    ps = _seat_participant_setup_or_abort(run_ctx, rc)
    if ps.kind == "participant_setup_seated":
        return Outcome("miner_registered_participant_setup_seated", MinerID=mid)
    if ps.kind == "participant_setup_already_seated":
        return Outcome("miner_registered_participant_setup_already_seated", MinerID=mid)
    return Outcome("miner_registered_participant_setup_aborted", MinerID=mid, reason=ps)


def _handle_template_commit(run_ctx: RunContext, payload: Dict[str, Any],
                            envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    if payload["RoundID_at_seat"] != rc.RoundID:
        return Outcome("template_commit_stale_noop")
    rc.TemplateID_committed = candidate_template_id(payload["candidate_template"])
    rc.transition("ASSIGNMENT")
    if not rc.barrier_satisfied:
        return Outcome("template_committed_participant_setup_deferred", RoundID=rc.RoundID)
    ps = _seat_participant_setup_or_abort(run_ctx, rc)
    if ps.kind in ("participant_setup_seated", "participant_setup_already_seated"):
        return Outcome("template_committed", RoundID=rc.RoundID)
    return Outcome("template_commit_participant_setup_aborted", RoundID=rc.RoundID, reason=ps)


def _seat_participant_setup_or_abort(run_ctx: RunContext, rc: RoundContext) -> Outcome:
    eq = run_ctx.event_queue
    key = ("PREPARE_PARTICIPANTS", rc.RoundID, rc.TemplateID_committed)
    if key in run_ctx.driver_event_seat:
        return Outcome("participant_setup_already_seated")
    r = ScheduleEvent(eq, rc, "PrepareParticipantsEvent", eq.current_event_time,
                      "ASSIGNMENT_SETUP",
                      {"RoundID_at_seat": rc.RoundID,
                       "TemplateID_at_seat": rc.TemplateID_committed},
                      ordinary_dispatch_origin(eq))
    if r.kind == "scheduled":
        run_ctx.driver_event_seat[key] = r.event_ref
        return Outcome("participant_setup_seated", event_ref=r.event_ref)
    return Outcome("participant_setup_aborted", reason=r)


def _handle_prepare_participants(run_ctx: RunContext, payload: Dict[str, Any],
                                 envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    if payload["RoundID_at_seat"] != rc.RoundID \
            or payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("participant_setup_stale_noop")
    rc.participant_setup_seated = True
    cfg = run_ctx.config
    # designate the reserve pool once (idle policy: reserve draws P_listen, never hashes).
    all_ids = sorted(run_ctx.miners.keys())
    if not hasattr(run_ctx, "reserve_miner_ids"):
        n_reserve = int(math.floor(cfg.reserve_fraction * len(all_ids)))
        run_ctx.reserve_miner_ids = set(all_ids[len(all_ids) - n_reserve:]) if n_reserve else set()
    participants = [mid for mid in all_ids if mid not in run_ctx.reserve_miner_ids]
    if not participants:
        participants = all_ids[:1]
    rc.leader_miner_id = participants[0]
    t = run_ctx.event_queue.current_event_time
    # reserve miners -> RESERVE (low-power standby); participants -> WAKING then wake-complete.
    for mid in run_ctx.reserve_miner_ids:
        m = run_ctx.miners[mid]
        if m.state != "RESERVE":
            run_ctx.apply_miner_state_transition(mid, "RESERVE", t)
    aseq = 0
    for mid in participants:
        aid = f"A-{rc.RoundID}-{mid}"
        version = 1
        rc.assignments[aid] = {"MinerID": mid, "AssignmentID": aid,
                               "assignment_version": version, "coverage_state": "OPEN"}
        run_ctx.apply_miner_state_transition(mid, "WAKING", t)
        _start_wake(run_ctx, rc, mid, aid, version)
        aseq += 1
    rc.transition("SOLUTION_PROPAGATION")
    return Outcome("participant_set_prepared", participants=len(participants))


def _start_wake(run_ctx: RunContext, rc: RoundContext, mid: Any, aid: Any,
                version: int) -> Outcome:
    """StartWake: seat a WakeCompleteEvent at now + wake_latency (H5/F5)."""
    eq = run_ctx.event_queue
    cfg = run_ctx.config
    target = eq.current_event_time + cfg.wake_latency
    r = ScheduleEvent(eq, rc, "WakeCompleteEvent", target, "WAKE_COMPLETE",
                      {"MinerID": mid, "AssignmentID": aid, "assignment_version": version},
                      ordinary_dispatch_origin(eq))
    return r


def _handle_wake_complete(run_ctx: RunContext, payload: Dict[str, Any],
                          envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    aid = payload["AssignmentID"]
    if rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("wake_complete_stale_noop", MinerID=mid)
    if aid not in rc.assignments or run_ctx.miners[mid].state != "WAKING":
        return Outcome("wake_complete_stale_noop", MinerID=mid)
    t = run_ctx.event_queue.current_event_time
    run_ctx.apply_miner_state_transition(mid, "ACTIVE_HASHING", t)
    if mid == rc.leader_miner_id:
        _seat_hash_work(run_ctx, rc, mid, aid, unit_index=0, at_time=t)
    return Outcome("wake_completed", MinerID=mid)


def _seat_hash_work(run_ctx: RunContext, rc: RoundContext, mid: Any, aid: Any,
                    unit_index: int, at_time: float) -> Outcome:
    eq = run_ctx.event_queue
    r = ScheduleEvent(eq, rc, "HashWorkEvent", at_time, "HASH_WORK",
                      {"MinerID": mid, "AssignmentID": aid, "unit_index": unit_index},
                      ordinary_dispatch_origin(eq) if eq.current_event_ref is not None
                      else _post_wake_origin(run_ctx, at_time))
    return r


def _post_wake_origin(run_ctx: RunContext, at_time: float):  # pragma: no cover
    # HashWork is always seated from inside a dispatch (WakeComplete or a prior HashWork),
    # so this fallback is unused; kept for defensive clarity.
    from .events import PostEpilogue
    return PostEpilogue(source_event_time=at_time - 1e-9, run_ctx=run_ctx,
                        eq=run_ctx.event_queue)


def _handle_hash_work(run_ctx: RunContext, payload: Dict[str, Any],
                      envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    if rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("hash_work_stale_noop")
    cfg = run_ctx.config
    mid = payload["MinerID"]
    aid = payload["AssignmentID"]
    idx = payload["unit_index"]
    t = run_ctx.event_queue.current_event_time
    if idx + 1 >= cfg.solution_after_units:
        # scenario injection: a designated round aborts instead of accepting (E2E-2).
        if run_ctx.round_seq in cfg.abort_round_seqs:
            return RoundAbort(run_ctx, rc, reason="forced_abort_scenario", envelope={})
        # solution discovered: seat AcceptanceEvent at a strictly-later time.
        return _seat_acceptance(run_ctx, rc, at_time=t + cfg.hash_step_time)
    return _seat_hash_work(run_ctx, rc, mid, aid, unit_index=idx + 1,
                           at_time=t + cfg.hash_step_time)


def _seat_acceptance(run_ctx: RunContext, rc: RoundContext, at_time: float) -> Outcome:
    if rc.block_accepted or rc.acceptance_seq > 0:
        return Outcome("acceptance_already_seated")
    eq = run_ctx.event_queue
    seq = rc.acceptance_seq
    rc.acceptance_seq += 1
    r = ScheduleEvent(eq, rc, "AcceptanceEvent", at_time, "ACCEPTANCE_FINALIZE",
                      {"RoundID_at_seat": rc.RoundID, "acceptance_seq": seq},
                      ordinary_dispatch_origin(eq))
    if r.kind == "scheduled":
        return Outcome("acceptance_seated", event_ref=r.event_ref)
    return Outcome("acceptance_seat_failed", reason=r)


def _handle_acceptance(run_ctx: RunContext, payload: Dict[str, Any],
                       envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    if payload["RoundID_at_seat"] != rc.RoundID or rc.block_accepted \
            or rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("acceptance_stale_noop")
    rc.block_accepted = True
    rc.transition("ROUND_ACCEPTED")                       # terminal BEFORE closure (AH2)
    rc.terminal_disposition = "ROUND_ACCEPTED"
    clo = _close_and_publish(run_ctx, rc, "ROUND_ACCEPTED", envelope,
                             at_time=run_ctx.event_queue.current_event_time)
    return Outcome("accepted_block", publication_result=clo.publication_result)


# ============================================================ closure + publication
def RoundAbort(run_ctx: RunContext, rc: RoundContext, reason: str,
               envelope: Dict[str, Any]) -> Outcome:
    if rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("round_already_terminal")
    rc.transition("ROUND_ABORTED")                        # terminal BEFORE closure (AH2)
    rc.terminal_disposition = reason
    clo = _close_and_publish(run_ctx, rc, "ROUND_ABORTED", envelope,
                             at_time=run_ctx.event_queue.current_event_time)
    return Outcome("round_aborted", RoundID=rc.RoundID, reason=reason,
                   publication_result=clo.publication_result)


def _close_and_publish(run_ctx: RunContext, rc: RoundContext, disposition: str,
                       envelope: Dict[str, Any], at_time: Optional[float] = None) -> Outcome:
    """CloseRoundAssignments + PublishTerminalRoundAndSeatNext (AH2/AI6)."""
    eq = run_ctx.event_queue
    t = at_time if at_time is not None else eq.current_event_time
    # move ACTIVE_HASHING / WAKING participants off active into the idle state (idle policy).
    for aid, a in rc.assignments.items():
        mid = a["MinerID"]
        m = run_ctx.miners.get(mid)
        if m is None:
            continue
        if m.state in ("ACTIVE_HASHING", "WAKING", "EXHAUSTED_PENDING"):
            run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)
    # cancel every QUEUED event belonging to this round (AE2); leakage guard.
    for ref in list(eq.queued_event_registry.keys()):
        rec = eq.queued_event_registry[ref]
        if rec.queue_status != "QUEUED":
            continue
        pl = rec.immutable_payload
        belongs = (pl.get("RoundID_at_seat") == rc.RoundID
                   or (rec.event_type in ("WakeCompleteEvent", "HashWorkEvent")
                       and str(pl.get("AssignmentID", "")).startswith(f"A-{rc.RoundID}-")))
        if belongs:
            CancelQueuedEvent(eq, run_ctx, ref, cancellation_reason="round_closed")
    # backlog-3: terminate PENDING + SEATED driver_requests EXACT_ROUND-scoped to this round.
    for drid, dr in list(run_ctx.driver_request_registry.items()):
        if dr.round_scope != EXACT_ROUND(rc.RoundID):
            continue
        if dr.status == "PENDING":
            run_ctx.set_driver_request_status(
                drid, "PENDING", "CANCELLED",
                disposition=Outcome("driver_request_round_closed", RoundID=rc.RoundID))
            run_ctx.pending_driver_request_index.discard(drid)
        elif dr.status == "SEATED":
            # cancel the still-QUEUED seat event through the queue owner; CancelQueuedEvent
            # reconciles the exact driver_request to CANCELLED via the reverse binding (AI4).
            if dr.seated_event_ref is not None and \
                    eq.queued_event_registry.get(dr.seated_event_ref) is not None and \
                    eq.queued_event_registry[dr.seated_event_ref].queue_status == "QUEUED":
                CancelQueuedEvent(eq, run_ctx, dr.seated_event_ref,
                                  cancellation_reason="round_closed")
            else:
                run_ctx.set_driver_request_status(
                    drid, "SEATED", "CANCELLED",
                    disposition=Outcome("driver_request_round_closed", RoundID=rc.RoundID))
    pub = _publish_terminal_and_seat_next(run_ctx, rc, disposition, envelope, t)
    run_ctx.terminal_publication_result = pub
    if pub.kind == "terminal_round_published_seat_failed":
        run_ctx.next_round_bootstrap_status = "NEXT_ROUND_BOOTSTRAP_FAILED"
    return Outcome("closure_record", publication_result=pub)


def _publish_terminal_and_seat_next(run_ctx: RunContext, rc: RoundContext,
                                    disposition: str, envelope: Dict[str, Any],
                                    at_time: float) -> Outcome:
    """AH2/AI6/AI8: the ONE terminal-round publication + next-bootstrap owner."""
    assert rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED")
    t = at_time
    rc.round_terminal_time = t
    run_ctx.prior_round_terminal_state = {"RoundID": rc.RoundID, "round_terminal_time": t,
                                          "disposition": disposition}
    if envelope.get("envelope_namespace") == "RUN_HOOK":
        return Outcome("terminal_round_published_no_seat", RoundID=rc.RoundID)
    next_target = next_representable_simulation_time(t)
    if not (next_target <= run_ctx.run_horizon_T):
        return Outcome("terminal_round_published_no_seat", RoundID=rc.RoundID)
    brid = (rc.RoundID, t, "NEXT_ROUND")
    next_br = BootstrapRequest(BootstrapRequestID=brid, predecessor_round_id=rc.RoundID,
                               predecessor_terminal_time=t, target_time=next_target)
    run_ctx.bootstrap_request_registry[brid] = next_br
    run_ctx.current_bootstrap_request = next_br
    if getattr(run_ctx, "force_bootstrap_seat_failure", False):  # E2E-5 injection hook
        return Outcome("terminal_round_published_seat_failed", BootstrapRequestID=brid,
                       reason=Outcome("forced_seat_failure"))
    boot = SeatNextRoundBootstrap(run_ctx)
    if boot.kind in ("round_bootstrap_seated", "round_bootstrap_already_seated"):
        return Outcome("terminal_round_published_and_seated", BootstrapRequestID=brid,
                       event_ref=boot.event_ref)
    return Outcome("terminal_round_published_seat_failed", BootstrapRequestID=brid,
                   reason=boot)


def _close_round_at_horizon(run_ctx: RunContext, rc: RoundContext) -> Outcome:
    hook_env = {"envelope_namespace": "RUN_HOOK", "event_time": run_ctx.run_horizon_T,
                "delta_cycle": 0, "event_seq": 0, "hook_id": "HorizonHookID"}
    rc.transition("ROUND_ABORTED")
    rc.terminal_disposition = "closed_at_horizon"
    _close_and_publish(run_ctx, rc, "ROUND_ABORTED", hook_env,
                       at_time=run_ctx.run_horizon_T)
    return Outcome("round_closed_at_horizon", RoundID=rc.RoundID)


# ============================================================ dispatch table
_HANDLERS = {
    "RoundInitialiseEvent": _handle_round_initialise,
    "MinerRegisterEvent": _handle_miner_register,
    "TemplateCommitEvent": _handle_template_commit,
    "PrepareParticipantsEvent": _handle_prepare_participants,
    "WakeCompleteEvent": _handle_wake_complete,
    "HashWorkEvent": _handle_hash_work,
    "AcceptanceEvent": _handle_acceptance,
}


# ============================================================ ProcessEventTime
def ProcessEventTime(run_ctx: RunContext, t: float, is_horizon: bool = False) -> Outcome:
    """The SOLE event-loop driver for one event_time (I-02/AF5)."""
    eq = run_ctx.event_queue
    assert t not in eq.finalised_event_times
    while True:
        dc = eq.smallest_delta_cycle_at(t)
        if dc is None:
            break
        while True:
            er = eq.pop_front_at(t, dc)
            if er is None:
                break
            rec = eq.queued_event_registry[er]
            assert rec.queue_status == "QUEUED"
            rec.queue_status = "DISPATCHING"
            eq.current_event_time = er.event_time
            eq.current_delta_cycle = er.delta_cycle
            eq.current_microphase = er.microphase
            eq.current_event_seq = er.seq
            eq.current_event_ref = er
            handler = _HANDLERS.get(rec.event_type)
            if handler is None:
                handler_result = Outcome("no_handler", event_type=rec.event_type)
            else:
                handler_result = handler(run_ctx, rec.immutable_payload,
                                         rec.dispatch_envelope)
            run_ctx.log.append(handler_result)
            rec.queue_status = "CONSUMED"
            eq.current_event_time = None
            eq.current_delta_cycle = None
            eq.current_microphase = None
            eq.current_event_seq = None
            eq.current_event_ref = None
            # AI4: complete the exact bound driver_request (if this was a driver seat).
            run_ctx.complete_driver_request_on_dispatch(
                er, disposition=Outcome("driver_request_consumed",
                                        handler_result=handler_result))
    # horizon closure: close a nonterminal round at T (O1/P1).
    rc = run_ctx.current_round_context
    if is_horizon and rc is not None and rc.round_state not in ("ROUND_ACCEPTED",
                                                                "ROUND_ABORTED"):
        _close_round_at_horizon(run_ctx, rc)
    # finalise t and advance the authoritative frontier (AI2).
    eq.finalised_event_times.add(t)
    if run_ctx.last_finalised_event_time is None or t > run_ctx.last_finalised_event_time:
        run_ctx.last_finalised_event_time = t
    return Outcome("event_time_finalised", t=t)


# ============================================================ finalizers
def FinalizeSimulationRun(run_ctx: RunContext, end_time: float,
                          disposition: str) -> Outcome:
    if run_ctx.run_finalised:
        return Outcome("run_already_finalised")
    run_ctx.settle_residency_to(end_time)
    run_ctx.run_finalised = True
    run_ctx.run_end_time = end_time
    run_ctx.run_disposition = disposition
    return Outcome("run_finalised", end_time=end_time, disposition=disposition)


def FinalizeSimulationRunNoRound(run_ctx: RunContext, reason: str) -> Outcome:
    if run_ctx.run_finalised:
        return Outcome("run_already_finalised")
    run_ctx.event_queue.finalised_event_times.add(run_ctx.run_horizon_T)
    run_ctx.settle_residency_to(run_ctx.run_horizon_T)
    run_ctx.run_finalised = True
    run_ctx.run_end_time = run_ctx.run_horizon_T
    run_ctx.run_disposition = reason
    return Outcome("run_finalised_no_round", reason=reason)


# ============================================================ RunEventLoopToHorizon
def RunEventLoopToHorizon(run_ctx: RunContext) -> Outcome:
    """The RUN-LEVEL driver (O1/P1/AH4/AH6/AI6)."""
    eq = run_ctx.event_queue
    T = run_ctx.run_horizon_T
    boot0 = SeatNextRoundBootstrap(run_ctx)
    if boot0.kind == "round_bootstrap_seat_failed":
        FinalizeSimulationRunNoRound(run_ctx, reason="bootstrap_seat_failed_run_abort")
        return Outcome("run_aborted_no_round", reason=boot0)
    while True:
        SeatPendingDriverRequests(run_ctx)
        if run_ctx.next_round_bootstrap_status == "NEXT_ROUND_BOOTSTRAP_FAILED":
            # AI6: deterministic terminate-partial at the declared partial end time.
            partial_end = (run_ctx.prior_round_terminal_state or {}).get(
                "round_terminal_time", eq.earliest_time() or T)
            FinalizeSimulationRun(run_ctx, end_time=partial_end,
                                  disposition="next_round_bootstrap_failed")
            return Outcome("run_completed_partial",
                           partial_end_time=partial_end,
                           terminal_publication_result=run_ctx.terminal_publication_result)
        if not eq.has_pending_before(T):
            break
        t = eq.earliest_time()
        if t is None or t >= T:
            break
        ProcessEventTime(run_ctx, t, is_horizon=False)
    if T not in eq.finalised_event_times:
        ProcessEventTime(run_ctx, T, is_horizon=True)
    FinalizeSimulationRun(run_ctx, end_time=T, disposition="run_completed")
    return Outcome("run_completed", end_time=T)


# ============================================================ convenience
def run_simulation(config: Optional[Stage2Config] = None, run_id: Any = "R") -> RunContext:
    """RunInitialise + RunEventLoopToHorizon; returns the finalised RunContext."""
    cfg = config or Stage2Config()
    run_ctx = RunInitialise(cfg, run_id=run_id)
    result = RunEventLoopToHorizon(run_ctx)
    run_ctx.loop_result = result
    return run_ctx
