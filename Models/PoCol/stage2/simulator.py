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
from .context import (BootstrapRequest, RunContext, RoundContext, EvaluationRecord,
                      EXACT_ROUND, NEXT_AVAILABLE_ROUND)
from .driver import (SeatNextRoundBootstrap, SeatPendingDriverRequests, SeatMinerRegister,
                     scope_admits)
from .search import make_template, partition_domain, MinerSearchState, sha256_int
from .security import (SecurityFloorObservation, ReserveActivationDecision,
                       ReserveActivationRequest, ReserveMinerRecord,
                       compute_h_effective, partition_primary_and_reserve,
                       select_reserves_to_cover, PRIMARY_ASSIGNMENT,
                       ACTIVATED_RESERVE_ASSIGNMENT, TERMINAL_RESERVE_STATUSES,
                       TERMINAL_REQUEST_STATUSES, FULL_DOMAIN_EXHAUSTED_NO_BLOCK,
                       ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN)

_TERMINAL_ROUND = ("ROUND_ACCEPTED", "ROUND_ABORTED")

# S2B-2: declared causal-accounting rounding tolerance (nonces) for the searched-count
# vs elapsed-hash-time bound (floats are exact to <1 nonce, so 1 is a safe integer slack).
_SEARCH_COUNT_TOL = 1


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
                # S2B-5: route the structured failure through the ONE round-closure owner
                # so every PENDING/SEATED round request is terminalised (no leak).
                run_ctx.genesis_miner_registry = []
                return _abort_round_initialise(run_ctx, rc, "genesis_admission_failed",
                                               detail=adm, envelope=envelope)
            expected.add(g["join_request"]["MinerID"])
        rc.barrier_expected = expected
        rc.barrier_registered = set()
        rc.barrier_satisfied = False
        run_ctx.genesis_miner_registry = []
        # AI1: seat each genesis MinerRegisterEvent SYNCHRONOUSLY at the non-finalised t0.
        seat_count = 0
        for drid in sorted(list(run_ctx.pending_driver_request_index),
                           key=lambda x: (str(x[0]), x[1])):
            dr = run_ctx.driver_request_registry[drid]
            if dr.status != "PENDING" or dr.kind != "MINER_JOIN" \
                    or dr.round_scope != EXACT_ROUND(rid):
                continue
            seat_count += 1
            if getattr(run_ctx, "genesis_seat_fail_at", None) == seat_count:  # TV325 injection
                run_ctx.force_seat_publication_failure = True
                gseat = SeatMinerRegister(run_ctx, dr, admission_mode="IN_DISPATCH_GENESIS")
                run_ctx.force_seat_publication_failure = False
            else:
                gseat = SeatMinerRegister(run_ctx, dr, admission_mode="IN_DISPATCH_GENESIS")
            if gseat.kind == "miner_register_seat_failed":
                # S2B-5: the closure owner cancels the already-seated genesis events and
                # terminalises every EXACT_ROUND request for this round.
                return _abort_round_initialise(run_ctx, rc, "genesis_registration_seat_failed",
                                               detail=gseat, envelope=envelope)

    rc.transition("ROUND_INITIALISING")
    rc.transition("TEMPLATE_COMMITMENT")
    # AG4 step 3: seat TemplateCommitEvent (ORDINARY_DISPATCH — inside this dispatch).
    tc = _seat_template_commit(run_ctx, rid)
    if tc.kind == "template_commit_seat_failed":
        return _abort_round_initialise(run_ctx, rc, "template_commit_seat_failed",
                                       detail=tc, envelope=envelope)
    return Outcome("round_initialised", RoundID=rid)


def _abort_round_initialise(run_ctx: RunContext, rc: RoundContext, reason_kind: str,
                            detail: Any, envelope: Dict[str, Any]) -> Outcome:
    """S2B-5: abort a failed round-initialise through the ONE round-closure owner.

    ``RoundAbort`` cancels every QUEUED event of the round, terminalises every
    PENDING/SEATED EXACT_ROUND request, publishes the terminal-round result and seats the
    next round when legal — so a genesis admission or seat failure leaves NO live seat or
    request (S2B-5).
    """
    ab = RoundAbort(run_ctx, rc, reason_kind, envelope)
    pub = ab.data.get("publication_result") if isinstance(ab, Outcome) else None
    return Outcome("round_initialise_aborted", RoundID=rc.RoundID,
                   reason=Outcome(reason_kind, detail=detail), publication_result=pub)


def _seat_template_commit(run_ctx: RunContext, rid: Any) -> Outcome:
    eq = run_ctx.event_queue
    key = ("TEMPLATE_COMMIT", rid)
    if key in run_ctx.driver_event_seat:
        return Outcome("template_commit_already_seated")
    if getattr(run_ctx, "force_template_commit_seat_failure", False):   # TV326 injection
        return Outcome("template_commit_seat_failed",
                       reason=Outcome("forced_template_commit_seat_failure"))
    template = {"id": f"tpl-{rid}"}
    r = ScheduleEvent(eq, run_ctx.current_round_context, "TemplateCommitEvent",
                      eq.current_event_time, "TEMPLATE_COMMIT",
                      {"RoundID_at_seat": rid, "candidate_template": template},
                      ordinary_dispatch_origin(eq))
    if r.kind == "scheduled":
        run_ctx.driver_event_seat[key] = r.event_ref
        return Outcome("template_commit_seated", event_ref=r.event_ref)
    return Outcome("template_commit_seat_failed", reason=r)


def _verify_driver_binding(run_ctx: RunContext, rc: RoundContext, payload: Dict[str, Any],
                           er: Any, kind: str) -> Outcome:
    """S2A-4: verify exact request / round ownership BEFORE any domain mutation."""
    drid = payload.get("DriverRequestID")
    dr = run_ctx.driver_request_registry.get(drid)
    if dr is None:
        return Outcome("driver_binding_unknown_request", DriverRequestID=drid)
    if dr.status != "SEATED":
        return Outcome("driver_binding_not_seated", DriverRequestID=drid, status=dr.status)
    if run_ctx.driver_request_by_seat_event_ref.get(er) != drid:
        return Outcome("driver_binding_reverse_mismatch", DriverRequestID=drid, event_ref=er)
    if scope_admits(payload.get("round_scope"), kind, rc) != "SCOPE_ADMIT":
        return Outcome("driver_binding_scope_stale", round_scope=payload.get("round_scope"),
                       RoundID=rc.RoundID)
    if payload.get("RoundID_at_seat") != rc.RoundID:
        return Outcome("driver_binding_round_mismatch",
                       RoundID_at_seat=payload.get("RoundID_at_seat"), RoundID=rc.RoundID)
    return Outcome("driver_binding_ok", DriverRequestID=drid)


def _handle_miner_register(run_ctx: RunContext, payload: Dict[str, Any],
                           envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    er = run_ctx.event_queue.current_event_ref
    # S2A-4: a stale / cancelled / mismatched request performs NO domain effect.
    guard = _verify_driver_binding(run_ctx, rc, payload, er, kind="MINER_JOIN")
    if guard.kind != "driver_binding_ok":
        return Outcome("miner_register_no_effect", reason=guard)
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
    cfg = run_ctx.config
    # S2A-1: commit the IMMUTABLE common block template + explicit finite nonce domain.
    rc.template = make_template(RoundID=rc.RoundID, difficulty=cfg.difficulty,
                                nonce_domain_size=cfg.nonce_domain_size,
                                seed=cfg.template_seed + run_ctx.round_seq)
    rc.TemplateID_committed = rc.template.TemplateID
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
    # participation/reserve policy (SEPARATE from the idle policy): a fixed reserve pool
    # is held in RESERVE (low-power standby); every other registered miner is an ACTIVE
    # participant that is assigned a disjoint nonce range and MUST hash.
    all_ids = sorted(run_ctx.miners.keys())
    if not hasattr(run_ctx, "reserve_miner_ids"):
        n_reserve = int(math.floor(cfg.reserve_fraction * len(all_ids)))
        run_ctx.reserve_miner_ids = set(all_ids[len(all_ids) - n_reserve:]) if n_reserve else set()
    participants = [mid for mid in all_ids if mid not in run_ctx.reserve_miner_ids]
    if not participants:
        participants = all_ids[:1]
    reserve_ids = sorted(mid for mid in run_ctx.reserve_miner_ids if mid not in participants)
    t = run_ctx.event_queue.current_event_time
    for mid in reserve_ids:
        if run_ctx.miners[mid].state != "RESERVE":
            run_ctx.apply_miner_state_transition(mid, "RESERVE", t)
    pol = cfg.security_floor
    # S3-2: with the floor enabled, split the finite domain into PRIMARY ranges plus
    # UNCLAIMED reserve-domain slices; otherwise keep the accepted Stage-2B behaviour
    # (whole domain to the active participants; reserves held in RESERVE with no slice).
    if pol.enabled and reserve_ids:
        ranges, reserve_slices = partition_primary_and_reserve(
            cfg.nonce_domain_size, participants, reserve_ids, rc.RoundID)
        run_ctx.reserve_slices[rc.RoundID] = reserve_slices
        for sl in reserve_slices:
            run_ctx.reserve_slice_by_id[sl.RangeSliceID] = sl
        for j, mid in enumerate(reserve_ids):
            rr = ReserveMinerRecord(
                MinerID=mid, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
                hash_rate=cfg.hash_rate_for(len(participants) + j),
                reserve_status="AVAILABLE", activation_priority=j)
            run_ctx.reserve_records[(rc.RoundID, mid)] = rr
    else:
        ranges = partition_domain(cfg.nonce_domain_size, participants)
    rc.search_states = {}
    for idx, mid in enumerate(sorted(participants)):
        start, end = ranges[mid]
        aid = f"A-{rc.RoundID}-{mid}"
        version = 1
        st = MinerSearchState(MinerID=mid, AssignmentID=aid, assignment_version=version,
                              hash_rate=cfg.hash_rate_for(idx), range_start=start,
                              range_end=end, active_power=cfg.P_hash, idle_power=cfg.P_listen)
        rc.search_states[mid] = st
        rc.assignments[aid] = {"MinerID": mid, "AssignmentID": aid,
                               "assignment_version": version, "range": (start, end),
                               "RoundID": rc.RoundID, "TemplateID": rc.TemplateID_committed,
                               "coverage_state": "OPEN"}
        run_ctx.search_assignment_kind[(rc.RoundID, mid)] = PRIMARY_ASSIGNMENT
        run_ctx.apply_miner_state_transition(mid, "WAKING", t)
        _start_wake(run_ctx, rc, mid, aid, version)
        # S2B-7 (SCI-3): an EXPECTED first-batch completion time, so a participant whose
        # round ends before it even wakes still has a justifiable zero-work interval; the
        # actual completion overwrites this at WakeCompleteEvent dispatch.
        expected_first = (t + cfg.wake_latency
                          + min(cfg.batch_size, st.range_size()) / st.hash_rate)
        run_ctx.round_first_completion[(rc.RoundID, mid)] = expected_first
    # S2B-4/S2B-7: record per-round scientific provenance for the ledger tests.
    run_ctx.round_participants[rc.RoundID] = set(participants)
    run_ctx.round_ranges[rc.RoundID] = {mid: ranges[mid] for mid in participants}
    rc.transition("SOLUTION_PROPAGATION")
    # S3A-2: take the FIRST security-floor observation as soon as the round begins expecting
    # capacity (all primaries WAKING, H_effective == 0) — do NOT wait for every primary to
    # finish WAKING.  Pending WAKING-primary capacity is accounted, so this observes (and
    # opens) the real initial below-floor interval without spuriously seating reserves.
    if pol.enabled:
        # measure-only at round start (no seat/abort until time advances past the ramp).
        EvaluateSecurityFloor(run_ctx, rc, t, "participants_prepared", decide=False)
    return Outcome("participant_set_prepared", participants=len(participants),
                   nonce_domain_size=cfg.nonce_domain_size,
                   reserve_slices=len(run_ctx.reserve_slices.get(rc.RoundID, [])))


def _start_wake(run_ctx: RunContext, rc: RoundContext, mid: Any, aid: Any,
                version: int) -> Outcome:
    """StartWake: seat a WakeCompleteEvent at now + wake_latency (H5/F5)."""
    eq = run_ctx.event_queue
    cfg = run_ctx.config
    target = eq.current_event_time + cfg.wake_latency
    return ScheduleEvent(eq, rc, "WakeCompleteEvent", target, "WAKE_COMPLETE",
                         {"MinerID": mid, "AssignmentID": aid,
                          "assignment_version": version}, ordinary_dispatch_origin(eq))


def _handle_wake_complete(run_ctx: RunContext, payload: Dict[str, Any],
                          envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    if rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("wake_complete_stale_noop", MinerID=mid)
    st = rc.search_states.get(mid)
    if st is None or run_ctx.miners[mid].state != "WAKING":
        return Outcome("wake_complete_stale_noop", MinerID=mid)
    t = run_ctx.event_queue.current_event_time
    run_ctx.apply_miner_state_transition(mid, "ACTIVE_HASHING", t)
    st.active_start = t
    # S2B-2: EVERY active miner plans its first batch-completion event (not just one leader).
    r = _seat_hash_work(run_ctx, rc, st, at_time=t)
    if r.kind == "scheduled":                              # S2B-7 SCI-3 zero-work justification
        run_ctx.round_first_completion[(rc.RoundID, mid)] = r.event_ref.event_time
    # S3A-2: observe the floor at EVERY primary WakeCompleteEvent (a genuine capacity change),
    # never waiting for the all-primary-active point.  Pending WAKING-primary capacity is
    # accounted so the ramp is measured as a real below-floor interval yet the imminent wakes
    # are not over-activated against.
    if run_ctx.config.security_floor.enabled:
        dec = EvaluateSecurityFloor(run_ctx, rc, t, "primary_wake_complete")
        if isinstance(dec, Outcome):     # ABORT_ROUND floor-unattainable closed the round
            return dec
    return Outcome("wake_completed", MinerID=mid)


def _first_solution_in(tpl: Any, start: int, end: int) -> Optional[int]:
    """First nonce in ``[start, end)`` whose real digest satisfies ``<= target`` (S2B-1)."""
    for nonce in range(start, end):
        if sha256_int(tpl.header_bytes, nonce) <= tpl.target:
            return nonce
    return None


def _seat_hash_work(run_ctx: RunContext, rc: RoundContext, st: Any,
                    at_time: float) -> Outcome:
    """S2B-2 design B: seat a PLANNED batch-completion event at its completion time.

    The read-only scan here determines ONLY the event completion time (it commits nothing).
    If the planned batch contains a solution, the event fires at the winning nonce's exact
    completion time (so the acceptance is causal); otherwise at the full-batch completion
    time.  Cursor, searched_count and the ledger are mutated ONLY at dispatch.
    """
    eq = run_ctx.event_queue
    tpl = rc.template
    cursor_start = st.cursor
    cursor_end = min(cursor_start + run_ctx.config.batch_size, st.range_end)
    if cursor_end <= cursor_start:
        return Outcome("hash_work_nothing_to_plan", MinerID=st.MinerID)
    winner = _first_solution_in(tpl, cursor_start, cursor_end)  # timing determination only
    effective_end = (winner + 1) if winner is not None else cursor_end
    completion_time = st.active_start + (effective_end - st.range_start) / st.hash_rate
    if not (completion_time > at_time):                 # causal-forward guard (defensive)
        completion_time = next_representable_simulation_time(at_time)
    payload = {"RoundID_at_seat": rc.RoundID, "TemplateID_at_seat": rc.TemplateID_committed,
               "AssignmentID": st.AssignmentID, "assignment_version": st.assignment_version,
               "MinerID": st.MinerID, "cursor_start": cursor_start, "cursor_end": cursor_end,
               "expected_search_generation": st.search_generation}
    return ScheduleEvent(eq, rc, "HashWorkEvent", completion_time, "HASH_WORK", payload,
                         ordinary_dispatch_origin(eq))


def _verify_hash_identity(rc: RoundContext, st: Any, payload: Dict[str, Any]) -> Outcome:
    """S2B-3: full immutable-identity verification BEFORE any search-state mutation."""
    if payload["RoundID_at_seat"] != rc.RoundID:
        return Outcome("hash_identity_round_mismatch")
    if payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("hash_identity_template_mismatch")
    if st is None:
        return Outcome("hash_identity_no_assignment")
    if st.completed:
        return Outcome("hash_identity_already_completed")
    if st.AssignmentID != payload["AssignmentID"]:
        return Outcome("hash_identity_assignment_mismatch")
    if st.assignment_version != payload["assignment_version"]:
        return Outcome("hash_identity_version_mismatch")
    if st.MinerID != payload["MinerID"]:
        return Outcome("hash_identity_owner_mismatch")
    if st.cursor != payload["cursor_start"]:
        return Outcome("hash_identity_cursor_mismatch", expected=st.cursor,
                       got=payload["cursor_start"])
    if st.search_generation != payload["expected_search_generation"]:
        return Outcome("hash_identity_generation_mismatch", expected=st.search_generation,
                       got=payload["expected_search_generation"])
    return Outcome("hash_identity_ok")


def _handle_hash_work(run_ctx: RunContext, payload: Dict[str, Any],
                      envelope: Dict[str, Any]) -> Outcome:
    """S2B-2/3/4: commit ONE planned batch at its completion time (causal accounting)."""
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    eq = run_ctx.event_queue
    er = eq.current_event_ref
    now = eq.current_event_time
    # a batch whose round already closed (e.g. another miner won first) commits zero work.
    if rc is None or rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("hash_work_no_effect", reason="round_terminal", MinerID=mid)
    st = rc.search_states.get(mid)
    guard = _verify_hash_identity(rc, st, payload)          # S2B-3: replay/superseded guard
    if guard.kind != "hash_identity_ok":
        return Outcome("hash_work_no_effect", reason=guard, MinerID=mid)
    cfg = run_ctx.config
    tpl = rc.template
    cursor_start = payload["cursor_start"]
    planned_end = payload["cursor_end"]
    # PERFORM the real work over the planned interval and commit through the first solution.
    winner_nonce = _first_solution_in(tpl, cursor_start, planned_end)
    commit_end = (winner_nonce + 1) if winner_nonce is not None else planned_end
    committed = commit_end - cursor_start
    st.cursor = commit_end
    st.searched_count += committed
    st.search_generation += 1
    # S2B-2 causal-accounting assertion: no work is counted beyond elapsed hash time / round end.
    rtt = rc.round_terminal_time if rc.round_terminal_time is not None else now
    bound = math.floor(st.hash_rate * (min(rtt, now) - st.active_start)) + _SEARCH_COUNT_TOL
    assert st.searched_count <= bound, ("searched_count exceeds causal bound",
                                        mid, st.searched_count, bound)
    resid = abs(st.searched_count - st.hash_rate * (now - st.active_start))
    if resid > run_ctx.max_search_time_residual:
        run_ctx.max_search_time_residual = resid
    # S2B-4 / S3-7: append the executable evaluation-ledger record, tagged PRIMARY vs
    # ACTIVATED_RESERVE so the ledger tests can prove zero duplicate evaluation across both.
    kind = run_ctx.search_assignment_kind.get((rc.RoundID, mid), PRIMARY_ASSIGNMENT)
    run_ctx.evaluation_ledger.append(EvaluationRecord(
        RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed, MinerID=mid,
        AssignmentID=st.AssignmentID, assignment_version=st.assignment_version,
        interval_start=cursor_start, interval_end=commit_end, completion_time=now,
        contained_solution=(winner_nonce is not None), winning_nonce=winner_nonce,
        event_ref=er, assignment_kind=kind))
    if kind == ACTIVATED_RESERVE_ASSIGNMENT:
        run_ctx.security_stats["activated_reserve_evaluation_count"] += committed
    run_ctx.final_searched[(rc.RoundID, mid)] = st.searched_count
    if winner_nonce is not None:                           # first valid solution in sim time
        st.completed = True
        st.completion_kind = "SOLUTION"
        if run_ctx.round_seq in cfg.abort_round_seqs:      # E2E-2 injection
            return RoundAbort(run_ctx, rc, reason="forced_abort_scenario", envelope={})
        return _seat_acceptance(run_ctx, rc, at_time=now, winner=mid,
                                winning_nonce=winner_nonce)
    if st.cursor >= st.range_end:                          # full range exhausted, no solution
        st.completed = True
        st.completion_kind = "EXHAUSTED"
        _seat_range_exhaust(run_ctx, rc, st, at_time=now)
        return Outcome("hash_work_range_exhausted", MinerID=mid, searched=st.searched_count)
    _seat_hash_work(run_ctx, rc, st, at_time=now)          # plan the next batch
    return Outcome("hash_work_committed", MinerID=mid, searched=st.searched_count,
                   committed=committed)


def _seat_range_exhaust(run_ctx: RunContext, rc: RoundContext, st: Any,
                        at_time: float) -> Outcome:
    eq = run_ctx.event_queue
    payload = {"MinerID": st.MinerID, "AssignmentID": st.AssignmentID,
               "RoundID_at_seat": rc.RoundID, "TemplateID_at_seat": rc.TemplateID_committed,
               "assignment_version": st.assignment_version,
               "expected_search_generation": st.search_generation}
    return ScheduleEvent(eq, rc, "RangeExhaustEvent", at_time, "RANGE_EXHAUST_ADJUDICATE",
                         payload, ordinary_dispatch_origin(eq))


def _handle_range_exhaust(run_ctx: RunContext, payload: Dict[str, Any],
                          envelope: Dict[str, Any]) -> Outcome:
    """POST-RANGE IDLE POLICY (+ no-block termination when the whole domain exhausts)."""
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    if rc is None or rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        return Outcome("range_exhaust_no_effect", reason="round_terminal", MinerID=mid)
    st = rc.search_states.get(mid)
    # S2B-3: identity verification (assignment + version + owner + round + template).
    if st is None or st.AssignmentID != payload["AssignmentID"] \
            or st.assignment_version != payload["assignment_version"] \
            or st.MinerID != payload["MinerID"] \
            or payload["RoundID_at_seat"] != rc.RoundID \
            or payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("range_exhaust_no_effect", reason="identity_mismatch", MinerID=mid)
    m = run_ctx.miners.get(mid)
    t = run_ctx.event_queue.current_event_time
    if m is not None and m.state == "ACTIVE_HASHING":
        run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)   # idle policy
    # S3-4: a primary exhaustion drops H_effective -> re-evaluate the security floor (it may
    # seat a reserve activation to restore capacity before declaring the round exhausted).
    if run_ctx.config.security_floor.enabled:
        dec = EvaluateSecurityFloor(run_ctx, rc, t, "range_exhaust")
        if isinstance(dec, Outcome):     # ABORT_ROUND floor-unattainable already closed
            return dec
    # S2B-1/S3-2: terminate no-block only when no live work AND no in-flight reserve remains.
    term = _maybe_terminate_no_block(run_ctx, rc)
    if term is not None:
        return term
    return Outcome("range_exhausted_idle", MinerID=mid)


def _maybe_terminate_no_block(run_ctx: RunContext, rc: RoundContext) -> Optional[Outcome]:
    """No-block round termination with CORRECT reserve-domain exhaustion semantics (S3A-7).

    Terminates only when there is no live search work, no block was found, and no reserve
    activation is pending or waking (so no further capacity can arrive).  It then classifies
    the no-block closure honestly:

    * ``FULL_DOMAIN_EXHAUSTED_NO_BLOCK`` — every primary AND reserve slice was searched (all
      reserve slices EXHAUSTED); a genuine whole-domain exhaustion claim.
    * ``ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN`` — reserve slices are still UNCLAIMED (the
      floor did not require them, e.g. ``min_rate == 0``); the reserve domain is NOT searched,
      so this is NEVER labelled a full-domain exhaustion.
    * ``round_exhausted_no_block`` — the accepted Stage-2B path when the floor is disabled and
      there are no reserve slices at all.
    """
    if rc.round_state in _TERMINAL_ROUND or rc.block_accepted or rc.acceptance_seq > 0:
        return None
    states = list(getattr(rc, "search_states", {}).values())
    if not states:
        return None
    if any(not s.completed for s in states):
        return None
    if any(s.completion_kind == "SOLUTION" for s in states):
        return None                                       # a block is pending acceptance
    for (rid, _mid), rr in run_ctx.reserve_records.items():
        if rid == rc.RoundID and rr.reserve_status in ("ACTIVATION_PENDING", "WAKING"):
            return None                                   # reserve capacity still incoming
    slices = run_ctx.reserve_slices.get(rc.RoundID, [])
    unclaimed = [sl for sl in slices if sl.status == "UNCLAIMED"]
    if unclaimed:
        # S3A-7: the reserve domain is NOT fully searched — never claim full-domain
        # exhaustion.  The exhaustion observation just taken already gave the floor its
        # chance to activate; reaching here with UNCLAIMED slices means the floor did not
        # require them, so close with the explicit unused-reserve-domain disposition.
        run_ctx.security_stats["unused_reserve_domain_count"] += 1
        return RoundAbort(run_ctx, rc, reason=ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN,
                          envelope={})
    if slices:
        # every primary AND reserve slice was evaluated: a true full-domain exhaustion.
        run_ctx.security_stats["full_domain_exhausted_count"] += 1
        return RoundAbort(run_ctx, rc, reason=FULL_DOMAIN_EXHAUSTED_NO_BLOCK, envelope={})
    return RoundAbort(run_ctx, rc, reason="round_exhausted_no_block", envelope={})


# ============================================================ Stage-3 security floor
def _record_decision(run_ctx: RunContext, obs: Any, selected_miners: List[Any],
                     selected_slices: List[str], projected: float, residual: float,
                     result: str) -> Any:
    run_ctx.decision_seq += 1
    dec = ReserveActivationDecision(
        DecisionID=(run_ctx.RunID, "DEC", run_ctx.decision_seq), ObservationID=obs.ObservationID,
        selected_miners=list(selected_miners), selected_slices=list(selected_slices),
        projected_hash_rate_after_wake=projected, residual_deficit=residual,
        policy_result=result)
    run_ctx.activation_decisions.append(dec)
    run_ctx.security_stats["decision_count"] += 1
    obs.activation_decision_id = dec.DecisionID
    return dec


def _reserve_records_for(run_ctx: RunContext, rc: RoundContext) -> List[Any]:
    return [rr for (rid, _m), rr in run_ctx.reserve_records.items() if rid == rc.RoundID]


def _pending_primary_capacity(run_ctx: RunContext, rc: RoundContext):
    """S3A-2: primary miners still WAKING with a live current assignment.

    They will imminently become ACTIVE_HASHING, so their capacity is counted only when
    deciding whether to seat reserves — never in ``H_effective`` — so the WAKING ramp is a
    real below-floor interval that is nonetheless not over-activated against.
    """
    rate = 0.0
    count = 0
    for mid, st in getattr(rc, "search_states", {}).items():
        if st.completed:
            continue
        if run_ctx.search_assignment_kind.get((rc.RoundID, mid)) != PRIMARY_ASSIGNMENT:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "WAKING":
            continue
        a = rc.assignments.get(st.AssignmentID)
        if a is None or a.get("assignment_version") != st.assignment_version \
                or a.get("RoundID") != rc.RoundID:
            continue
        rate += st.hash_rate
        count += 1
    return rate, count


def _observation_key(run_ctx: RunContext, rc: RoundContext, trigger: Any) -> Any:
    """S3A-2 immutable SecurityFloorObservationKey."""
    trig = trigger if trigger is not None else getattr(run_ctx.event_queue,
                                                       "current_event_ref", None)
    return (rc.RoundID, rc.TemplateID_committed, trig, rc.state_version,
            run_ctx.capacity_state_version)


def EvaluateSecurityFloor(run_ctx: RunContext, rc: RoundContext, observation_time: float,
                          observation_reason: str, trigger: Any = None,
                          decide: bool = True) -> Optional[Outcome]:
    """S3-4 / S3A-2..5: the ONE authoritative security-floor observation + activation decision.

    Records a SecurityFloorObservation keyed by an immutable SecurityFloorObservationKey
    (idempotent replay), measures the duration below the floor FROM THE REAL FIRST BREACH,
    and — when breached and the round is open — deterministically activates the true
    minimum-cardinality reserve subset (S3A-3) via an all-or-none seating transaction
    (S3A-4).  Returns ``None`` normally, or a ``RoundAbort`` Outcome when the configured
    floor-unattainable policy is ABORT_ROUND.

    ``decide=False`` is a MEASURE-ONLY observation (used at ``participants_prepared``, when
    the round has not yet advanced in time): it records the observation and opens the real
    initial below-floor interval, but seats no reserve and takes no abort — every actionable
    decision is deferred to a capacity-change point (wake-complete onward) where simulation
    time has advanced, so a round is never terminated at its own start time.
    """
    cfg = run_ctx.config
    pol = cfg.security_floor
    if not pol.enabled:
        return None
    # S3A-2: idempotent replay — the same key returns the existing observation/decision and
    # seats nothing new (no counters advance, no second activation).
    key = _observation_key(run_ctx, rc, trigger)
    if key in run_ctx.observation_by_key:
        run_ctx.security_stats["observation_replay_count"] += 1
        return None

    h_eff, active_count, _ = compute_h_effective(run_ctx, rc)
    inflight = 0.0
    inflight_count = 0
    for rr in _reserve_records_for(run_ctx, rc):
        if rr.reserve_status in ("ACTIVATION_PENDING", "WAKING"):
            inflight += rr.hash_rate
            inflight_count += 1
    pending_rate, pending_count = _pending_primary_capacity(run_ctx, rc)
    min_rate = pol.minimum_active_hash_rate
    min_count = pol.minimum_active_miner_count
    hash_deficit = max(0.0, min_rate - h_eff)
    count_deficit = 0 if min_count is None else max(0, min_count - active_count)
    breached = (h_eff + pol.floor_tolerance < min_rate) \
        or (min_count is not None and active_count < min_count)
    round_terminal = rc.round_state in _TERMINAL_ROUND

    run_ctx.observation_seq += 1
    obs = SecurityFloorObservation(
        ObservationID=(run_ctx.RunID, "OBS", run_ctx.observation_seq), RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed, observation_time=observation_time,
        observation_reason=observation_reason, effective_active_hash_rate=h_eff,
        active_miner_count=active_count, minimum_required_hash_rate=min_rate,
        minimum_required_miner_count=min_count, hash_rate_deficit=hash_deficit,
        miner_count_deficit=count_deficit, breached=breached, observation_key=key)
    run_ctx.observation_by_key[key] = obs
    run_ctx.security_observations.append(obs)
    run_ctx.security_stats["observation_count"] += 1

    # S3-13 / S3A-2: measure the duration below the floor from the FIRST breached observation.
    if breached:
        run_ctx.security_stats["breach_observation_count"] += 1
        if hash_deficit > run_ctx.security_stats["max_hash_rate_deficit"]:
            run_ctx.security_stats["max_hash_rate_deficit"] = hash_deficit
        # a terminal-round observation never OPENS a breach interval (the round is over);
        # an already-open interval is closed by _close_security_state at closure.
        if rc.below_floor_since is None and not round_terminal:
            rc.below_floor_since = observation_time
            rc.below_floor_open_reason = observation_reason
            rc.current_breach_id = obs.ObservationID
            run_ctx.security_stats["distinct_breach_count"] += 1
    else:
        if rc.below_floor_since is not None:
            dur = observation_time - rc.below_floor_since
            run_ctx.security_stats["total_duration_below_floor"] += dur
            if rc.below_floor_open_reason == "participants_prepared":
                run_ctx.security_stats["early_wake_below_floor_duration"] += dur
            rc.below_floor_since = None
            rc.below_floor_open_reason = None
            rc.current_breach_id = None
        return None

    if round_terminal:
        _record_decision(run_ctx, obs, [], [], h_eff + inflight, hash_deficit,
                         "ROUND_ALREADY_TERMINAL")
        return None
    if not decide:
        # measure-only observation (round start): defer every activation/abort decision to a
        # capacity-change point where simulation time has advanced.
        return None

    # remaining need beyond in-flight reserve AND pending WAKING-primary capacity
    # (idempotence: imminent wakes/activations already cover part of the deficit).
    need = min_rate - (h_eff + inflight + pending_rate)
    need_count = 0 if min_count is None else max(
        0, min_count - (active_count + inflight_count + pending_count))
    if need <= pol.floor_tolerance and need_count <= 0:
        _record_decision(run_ctx, obs, [], [], h_eff + inflight + pending_rate, 0.0,
                         "NO_ACTIVATION_REQUIRED")
        return None

    seated_so_far = run_ctx.activations_per_round.get(rc.RoundID, 0)
    remaining = pol.maximum_activations_per_round - seated_so_far
    eligible = sorted([rr for rr in _reserve_records_for(run_ctx, rc)
                       if rr.reserve_status == "AVAILABLE"],
                      key=lambda r: (r.activation_priority, str(r.MinerID)))
    unclaimed = [sl for sl in run_ctx.reserve_slices.get(rc.RoundID, [])
                 if sl.status == "UNCLAIMED"]
    cap = min(len(eligible), len(unclaimed), max(0, remaining))
    base = h_eff + inflight + pending_rate
    if cap <= 0:
        # nothing may be seated (limit reached, no eligible reserve, or no unclaimed slice).
        _record_decision(run_ctx, obs, [], [], base, hash_deficit, "FLOOR_UNATTAINABLE")
        return _apply_floor_unattainable(run_ctx, rc, observation_time)

    top_cap_rates = sorted((r.hash_rate for r in eligible), reverse=True)[:cap]
    max_projected = base + sum(top_cap_rates)
    attainable = (max_projected + pol.floor_tolerance >= min_rate) \
        and (min_count is None
             or (active_count + inflight_count + pending_count + cap) >= min_count)
    if attainable:
        selected = select_reserves_to_cover(eligible, need, cap, need_count)
        slices = unclaimed[:len(selected)]
        projected = base + sum(r.hash_rate for r in selected)
        dec = _record_decision(run_ctx, obs, [r.MinerID for r in selected],
                               [s.RangeSliceID for s in slices], projected,
                               max(0.0, min_rate - projected), "ACTIVATION_SEATED")
        for rr, sl in zip(selected, slices):
            SeatReserveActivationTransaction(run_ctx, rc, rr, sl, obs, dec.DecisionID)
        return None

    # the bounded pool cannot restore the floor this round.
    if cfg.floor_unattainable_policy == "ABORT_ROUND":
        _record_decision(run_ctx, obs, [], [], max_projected,
                         max(0.0, min_rate - max_projected), "FLOOR_UNATTAINABLE")
        return _apply_floor_unattainable(run_ctx, rc, observation_time)
    # CONTINUE_DEGRADED: seat every reserve we legally can (PARTIAL_RESTORATION) and keep the
    # round executable so the reserve domain is progressively searched.
    seatable = eligible[:cap]
    slices = unclaimed[:cap]
    projected = base + sum(r.hash_rate for r in seatable)
    dec = _record_decision(run_ctx, obs, [r.MinerID for r in seatable],
                           [s.RangeSliceID for s in slices], projected,
                           max(0.0, min_rate - projected), "PARTIAL_RESTORATION")
    run_ctx.security_stats["partial_restoration_count"] += 1
    for rr, sl in zip(seatable, slices):
        SeatReserveActivationTransaction(run_ctx, rc, rr, sl, obs, dec.DecisionID)
    return None


def _apply_floor_unattainable(run_ctx: RunContext, rc: RoundContext,
                              observation_time: float) -> Optional[Outcome]:
    """S3-9: the configured floor-unattainable policy when the pool cannot restore the floor."""
    run_ctx.security_stats["floor_unattainable_count"] += 1
    if run_ctx.config.floor_unattainable_policy == "ABORT_ROUND":
        return RoundAbort(run_ctx, rc, reason="security_floor_unattainable", envelope={})
    return None   # CONTINUE_DEGRADED: keep the round executable; duration keeps accumulating.


def SeatReserveActivationTransaction(run_ctx: RunContext, rc: RoundContext, rr: Any, sl: Any,
                                     obs: Any, decision_id: Any) -> Any:
    """S3A-4: seat a reserve activation ALL-OR-NONE on its immutable request identity.

    Idempotent replay of an exact request returns the existing request with no second
    effect (S3-10).  The slice claim, reserve-status transition, request creation, StartEvent
    scheduling, EventRef publication and activation-counter increment COMMIT TOGETHER; if
    ``ScheduleEvent`` fails the slice is restored to UNCLAIMED, the reserve to AVAILABLE,
    every request/slice/event field is cleared, the counter is NOT incremented, and a
    ``reserve_activation_seat_failed`` Outcome is returned.
    """
    if rr.activation_generation == 0:
        rr.activation_generation = 1
    req_id = ("RESERVE_ACTIVATION", rc.RoundID, rc.TemplateID_committed, obs.ObservationID,
              rr.MinerID, sl.RangeSliceID, rr.activation_generation)
    existing = run_ctx.activation_requests.get(req_id)
    if existing is not None:                                # S3-10 exact replay: no 2nd effect
        return existing
    eq = run_ctx.event_queue
    now = eq.current_event_time
    # snapshot the pre-state so a failed seat rolls back to EXACTLY it.
    prev_slice_status = sl.status
    prev_slice_claimed_by = sl.claimed_by
    prev_reserve_status = rr.reserve_status
    prev_slice_id = rr.assigned_reserve_slice_id
    prev_request_id = rr.activation_request_id
    prev_event_ref = rr.activation_event_ref
    # tentatively claim + mark pending.
    sl.status = "CLAIMED"
    sl.claimed_by = rr.MinerID
    rr.reserve_status = "ACTIVATION_PENDING"
    rr.assigned_reserve_slice_id = sl.RangeSliceID
    rr.activation_request_id = req_id
    payload = {"ReserveActivationRequestID": req_id, "SecurityFloorObservationID": obs.ObservationID,
               "ReserveActivationDecisionID": decision_id, "RoundID_at_seat": rc.RoundID,
               "TemplateID_at_seat": rc.TemplateID_committed, "MinerID": rr.MinerID,
               "ReserveSliceID": sl.RangeSliceID, "activation_generation": rr.activation_generation,
               "expected_reserve_status": "ACTIVATION_PENDING",
               "expected_round_state_version": rc.state_version}
    if getattr(run_ctx, "force_activation_start_seat_failure", False):   # S3A-05 injection
        r = Outcome("rejected_forced_activation_seat_failure")
    else:
        r = ScheduleEvent(eq, rc, "ReserveActivationStartEvent", now, "RESERVE_ACTIVATION_START",
                          payload, ordinary_dispatch_origin(eq))
    if r.kind != "scheduled":
        # ROLLBACK: restore the pre-state exactly; commit nothing.
        sl.status = prev_slice_status
        sl.claimed_by = prev_slice_claimed_by
        rr.reserve_status = prev_reserve_status
        rr.assigned_reserve_slice_id = prev_slice_id
        rr.activation_request_id = prev_request_id
        rr.activation_event_ref = prev_event_ref
        run_ctx.security_stats["activation_seat_rollback_count"] += 1
        return Outcome("reserve_activation_seat_failed", reason=r, MinerID=rr.MinerID,
                       ReserveSliceID=sl.RangeSliceID)
    # COMMIT: publish the EventRef, create the SEATED request, advance the counter.
    ev = r.event_ref
    rr.activation_event_ref = ev
    req = ReserveActivationRequest(
        ReserveActivationRequestID=req_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        SecurityFloorBreachID=obs.ObservationID, DecisionID=decision_id, MinerID=rr.MinerID,
        ReserveSliceID=sl.RangeSliceID, activation_generation=rr.activation_generation,
        status="SEATED", start_event_ref=ev, disposition=Outcome("reserve_activation_seated"))
    run_ctx.activation_requests[req_id] = req
    run_ctx.activations_per_round[rc.RoundID] = run_ctx.activations_per_round.get(rc.RoundID, 0) + 1
    run_ctx.security_stats["activations_seated"] += 1
    return req


# Backward-compatible alias for the exported seating entry point (S3-10 test / __init__).
SeatReserveActivation = SeatReserveActivationTransaction


def _verify_activation_identity(run_ctx: RunContext, rc: RoundContext, payload: Dict[str, Any],
                                expected_status: str, expected_request_status,
                                lifecycle: str) -> Any:
    """S3A-5: COMPLETE activation-event identity verification BEFORE any domain mutation.

    Verifies the whole request -> observation -> decision chain, the reserve/slice binding,
    the recorded start/complete EventRef, the expected reserve status, the expected round
    state version, and the request lifecycle status.  A tampered request / observation /
    decision id, state version or EventRef performs NO effect.
    """
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("activation_no_effect", reason="round_terminal")
    if payload["RoundID_at_seat"] != rc.RoundID:
        return Outcome("activation_no_effect", reason="round_mismatch")   # S3-11 cross-round
    if payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("activation_no_effect", reason="template_mismatch")
    rr = run_ctx.reserve_records.get((rc.RoundID, payload["MinerID"]))
    sl = run_ctx.reserve_slice_by_id.get(payload["ReserveSliceID"])
    if rr is None or sl is None:
        return Outcome("activation_no_effect", reason="unknown_reserve_or_slice")
    # the request must exist and its immutable identity must match the payload exactly.
    req = run_ctx.activation_requests.get(payload["ReserveActivationRequestID"])
    if req is None:
        return Outcome("activation_no_effect", reason="unknown_request")
    if req.RoundID != rc.RoundID or req.TemplateID != rc.TemplateID_committed \
            or req.MinerID != payload["MinerID"] or req.ReserveSliceID != payload["ReserveSliceID"] \
            or req.activation_generation != payload["activation_generation"]:
        return Outcome("activation_no_effect", reason="request_identity_mismatch")
    # request belongs to the stated observation, and the observation to the stated decision.
    if req.SecurityFloorBreachID != payload["SecurityFloorObservationID"]:
        return Outcome("activation_no_effect", reason="observation_mismatch")
    obs = next((o for o in run_ctx.security_observations
                if o.ObservationID == payload["SecurityFloorObservationID"]), None)
    if obs is None or obs.activation_decision_id != payload["ReserveActivationDecisionID"]:
        return Outcome("activation_no_effect", reason="decision_mismatch")
    if req.DecisionID != payload["ReserveActivationDecisionID"]:
        return Outcome("activation_no_effect", reason="request_decision_mismatch")
    dec = next((d for d in run_ctx.activation_decisions
                if d.DecisionID == payload["ReserveActivationDecisionID"]), None)
    if dec is None or payload["MinerID"] not in dec.selected_miners \
            or payload["ReserveSliceID"] not in dec.selected_slices:
        return Outcome("activation_no_effect", reason="decision_selection_mismatch")
    if rr.activation_request_id != req.ReserveActivationRequestID:
        return Outcome("activation_no_effect", reason="reserve_request_link_mismatch")
    # lifecycle + status + version + slice-claim checks.
    if req.status != expected_request_status:
        return Outcome("activation_no_effect", reason="request_lifecycle_mismatch",
                       actual=req.status)
    if rr.reserve_status != expected_status:
        return Outcome("activation_no_effect", reason="reserve_status_mismatch",
                       actual=rr.reserve_status)
    if rr.activation_generation != payload["activation_generation"]:
        return Outcome("activation_no_effect", reason="generation_mismatch")
    if payload["expected_round_state_version"] != rc.state_version:
        return Outcome("activation_no_effect", reason="round_state_version_mismatch")
    if sl.status != "CLAIMED" or sl.claimed_by != payload["MinerID"]:
        return Outcome("activation_no_effect", reason="slice_claim_mismatch")
    # the current EventRef must match the recorded start/complete EventRef.
    cur = getattr(run_ctx.event_queue, "current_event_ref", None)
    recorded = req.start_event_ref if lifecycle == "START" else req.complete_event_ref
    if recorded is not None and cur is not None and cur != recorded:
        return Outcome("activation_no_effect", reason="event_ref_mismatch")
    return Outcome("activation_identity_ok", reserve=rr, slice=sl, request=req)


def _handle_reserve_activation_start(run_ctx: RunContext, payload: Dict[str, Any],
                                     envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    guard = _verify_activation_identity(run_ctx, rc, payload, "ACTIVATION_PENDING",
                                        "SEATED", "START")
    if guard.kind != "activation_identity_ok":
        return Outcome("reserve_activation_start_no_effect", reason=guard)
    rr = guard.reserve
    sl = guard.slice
    req = guard.request
    mid = payload["MinerID"]
    eq = run_ctx.event_queue
    t = eq.current_event_time
    rr.reserve_status = "WAKING"                            # S3-6: WAKING at activation start
    run_ctx.apply_miner_state_transition(mid, "WAKING", t)
    req.status = "STARTED"
    req.started_at = t
    complete_time = t + run_ctx.config.security_floor.activation_wake_latency
    cpayload = dict(payload)
    cpayload["expected_reserve_status"] = "WAKING"
    cpayload["expected_round_state_version"] = rc.state_version
    if getattr(run_ctx, "force_activation_complete_seat_failure", False):   # S3A-06 injection
        r = Outcome("rejected_forced_complete_seat_failure")
    else:
        r = ScheduleEvent(eq, rc, "ReserveActivationCompleteEvent", complete_time,
                          "RESERVE_ACTIVATION_COMPLETE", cpayload, ordinary_dispatch_origin(eq))
    if r.kind != "scheduled":
        # S3A-4: a failed CompleteEvent seat must NEVER strand the miner WAKING without a
        # controller — terminalise the request + reserve, restore the slice (declared policy:
        # UNCLAIMED so its capacity can be recovered), return the miner to LOW_POWER_LISTEN,
        # and re-evaluate the floor (which may seat another reserve or apply the policy).
        run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)
        rr.reserve_status = "CANCELLED"
        rr.disposition = Outcome("reserve_activation_complete_seat_failed", reason=r)
        rr.activation_request_id = None
        sl.status = "UNCLAIMED"                             # declared slice-restore policy
        sl.claimed_by = None
        req.status = "FAILED"
        req.disposition = Outcome("reserve_activation_complete_seat_failed", reason=r)
        run_ctx.security_stats["activation_complete_seat_failure_count"] += 1
        dec = EvaluateSecurityFloor(run_ctx, rc, t, "reserve_activation_complete_seat_failed")
        if isinstance(dec, Outcome):
            return dec
        return Outcome("reserve_activation_start_complete_seat_failed", MinerID=mid, reason=r)
    ev = r.event_ref
    req.complete_event_ref = ev
    rr.activation_event_ref = ev
    return Outcome("reserve_activation_started", MinerID=mid, complete_event_ref=ev)


def _handle_reserve_activation_complete(run_ctx: RunContext, payload: Dict[str, Any],
                                        envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    guard = _verify_activation_identity(run_ctx, rc, payload, "WAKING", "STARTED", "COMPLETE")
    if guard.kind != "activation_identity_ok":
        return Outcome("reserve_activation_complete_no_effect", reason=guard)
    rr = guard.reserve
    sl = guard.slice
    req = guard.request
    mid = payload["MinerID"]
    cfg = run_ctx.config
    eq = run_ctx.event_queue
    t = eq.current_event_time
    rr.reserve_status = "ACTIVE"                            # S3-6: ACTIVE only at completion
    run_ctx.apply_miner_state_transition(mid, "ACTIVE_HASHING", t)
    req.status = "COMPLETED"
    req.completed_at = t
    req.disposition = Outcome("reserve_activation_completed")
    # S3-7: an activated reserve gets a NORMAL MinerSearchState over its exact reserve slice.
    aid = f"AR-{rc.RoundID}-{mid}"
    version = 1
    st = MinerSearchState(MinerID=mid, AssignmentID=aid, assignment_version=version,
                          hash_rate=rr.hash_rate, range_start=sl.range_start,
                          range_end=sl.range_end, active_power=cfg.P_hash, idle_power=cfg.P_listen)
    st.active_start = t
    rc.search_states[mid] = st
    rc.assignments[aid] = {"MinerID": mid, "AssignmentID": aid, "assignment_version": version,
                           "range": (sl.range_start, sl.range_end),
                           "RoundID": rc.RoundID, "TemplateID": rc.TemplateID_committed,
                           "coverage_state": "OPEN"}
    run_ctx.search_assignment_kind[(rc.RoundID, mid)] = ACTIVATED_RESERVE_ASSIGNMENT
    run_ctx.security_stats["activations_completed"] += 1
    r = _seat_hash_work(run_ctx, rc, st, at_time=t)
    if r.kind == "scheduled":
        run_ctx.round_first_completion[(rc.RoundID, mid)] = r.event_ref.event_time
    # capacity increased -> re-evaluate the floor (may close the breach interval).
    dec = EvaluateSecurityFloor(run_ctx, rc, t, "reserve_activation_completed")
    if isinstance(dec, Outcome):
        return dec
    term = _maybe_terminate_no_block(run_ctx, rc)
    if term is not None:
        return term
    return Outcome("reserve_activation_completed", MinerID=mid, ReserveSliceID=sl.RangeSliceID)


def _close_security_state(run_ctx: RunContext, rc: RoundContext, t: float) -> None:
    """S3-10 / S3A-2 / S3A-6: closure observation + reserve/slice/request terminalisation.

    A closed round leaves NO reserve record ACTIVE or AVAILABLE and NO activation request in
    a non-terminal status; every queued activation event was already CANCELLED via the
    round's QUEUED-event loop (they carry ``RoundID_at_seat``).
    """
    # S3A-2: a final security-floor observation at closure (the round is already terminal, so
    # this seats nothing and only records the terminal capacity state).
    EvaluateSecurityFloor(run_ctx, rc, t, "round_closure",
                          trigger=("CLOSURE", rc.RoundID, rc.state_version))
    if rc.below_floor_since is not None:                    # close the open breach interval
        dur = t - rc.below_floor_since
        run_ctx.security_stats["total_duration_below_floor"] += dur
        if rc.below_floor_open_reason == "participants_prepared":
            run_ctx.security_stats["early_wake_below_floor_duration"] += dur
        rc.below_floor_since = None
        rc.below_floor_open_reason = None
        rc.current_breach_id = None
    for rr in _reserve_records_for(run_ctx, rc):
        if rr.reserve_status in ("ACTIVATION_PENDING", "WAKING"):
            rr.reserve_status = "CANCELLED"
            rr.disposition = Outcome("reserve_cancelled_at_round_close")
            run_ctx.security_stats["activations_cancelled"] += 1
            m = run_ctx.miners.get(rr.MinerID)
            if m is not None and m.state == "WAKING":
                run_ctx.apply_miner_state_transition(rr.MinerID, "LOW_POWER_LISTEN", t)
        elif rr.reserve_status == "AVAILABLE":
            rr.reserve_status = "UNUSED_AT_ROUND_CLOSE"
        elif rr.reserve_status == "ACTIVE":
            # S3A-6: a closed-round record is NEVER left ACTIVE.
            st = rc.search_states.get(rr.MinerID)
            rr.reserve_status = "EXHAUSTED" if (st is not None and st.completed) \
                else "CLOSED_AT_ROUND_CLOSE"
    for sl in run_ctx.reserve_slices.get(rc.RoundID, []):
        if sl.status == "UNCLAIMED":
            sl.status = "UNUSED_AT_ROUND_CLOSE"
        elif sl.status == "CLAIMED":
            st = rc.search_states.get(sl.claimed_by)
            if st is not None and st.completed and st.cursor >= st.range_end:
                sl.status = "EXHAUSTED"          # searched to the end by an activated reserve
            else:
                sl.status = "UNUSED_AT_ROUND_CLOSE"   # claimed but not fully searched
    # S3A-6: every activation request of this closed round must be terminal.
    for req in run_ctx.activation_requests.values():
        if req.RoundID != rc.RoundID:
            continue
        if req.status not in TERMINAL_REQUEST_STATUSES:
            req.status = "CANCELLED"
            req.disposition = Outcome("reserve_activation_request_cancelled_at_round_close")


def _seat_acceptance(run_ctx: RunContext, rc: RoundContext, at_time: float,
                     winner: Any = None, winning_nonce: Any = None) -> Outcome:
    if rc.block_accepted or rc.acceptance_seq > 0:
        return Outcome("acceptance_already_seated")
    eq = run_ctx.event_queue
    seq = rc.acceptance_seq
    rc.acceptance_seq += 1
    rc.winner_miner_id = winner
    rc.winning_nonce = winning_nonce
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
    # S2B-4: snapshot the final per-miner searched_count for the round (ledger cross-check).
    for mid, st in getattr(rc, "search_states", {}).items():
        run_ctx.final_searched[(rc.RoundID, mid)] = st.searched_count
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
    # S3-10: reserve/slice cleanup + security-floor metric snapshot (activation events were
    # cancelled above via the QUEUED-event loop since they carry RoundID_at_seat).
    _close_security_state(run_ctx, rc, t)
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
    run_ctx.round_terminal_times[rc.RoundID] = t          # S2B-4 ledger cross-check
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
    "RangeExhaustEvent": _handle_range_exhaust,
    "AcceptanceEvent": _handle_acceptance,
    "ReserveActivationStartEvent": _handle_reserve_activation_start,
    "ReserveActivationCompleteEvent": _handle_reserve_activation_complete,
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


def FinalizeSimulationRunPartial(run_ctx: RunContext, partial_end_time: float,
                                 reason: str) -> Outcome:
    """S2A-6: a legal partial-run finalizer — leaves NO future live event/request.

    Cancels every remaining QUEUED event (reconciling any bound driver request via the
    queue owner), terminalises every non-terminal driver request, closes current
    assignments, settles residency ONLY through ``partial_end_time``, asserts no live
    event/request remains, and records a partial-run disposition (never a full-horizon run).
    """
    if run_ctx.run_finalised:
        return Outcome("run_already_finalised")
    eq = run_ctx.event_queue
    # cancel every remaining QUEUED event through the ONE queue owner (reconciles bindings).
    cancelled = 0
    for ref in list(eq.queued_event_registry.keys()):
        if eq.queued_event_registry[ref].queue_status == "QUEUED":
            res = CancelQueuedEvent(eq, run_ctx, ref, cancellation_reason="partial_finalization")
            if res.kind == "event_cancelled":
                cancelled += 1
    # terminalise every still-live driver request (PENDING -> CANCELLED; SEATED -> CANCELLED).
    for drid, dr in list(run_ctx.driver_request_registry.items()):
        if dr.status == "PENDING":
            run_ctx.set_driver_request_status(drid, "PENDING", "CANCELLED",
                                              Outcome("driver_request_partial_finalized"))
            run_ctx.pending_driver_request_index.discard(drid)
        elif dr.status == "SEATED":
            run_ctx.set_driver_request_status(drid, "SEATED", "CANCELLED",
                                              Outcome("driver_request_partial_finalized"))
    # close the current round's assignments (any still-active miner -> idle at partial end).
    rc = run_ctx.current_round_context
    if rc is not None:
        for a in rc.assignments.values():
            m = run_ctx.miners.get(a["MinerID"])
            if m is not None and m.state in ("ACTIVE_HASHING", "WAKING", "EXHAUSTED_PENDING"):
                run_ctx.apply_miner_state_transition(a["MinerID"], "LOW_POWER_LISTEN",
                                                     partial_end_time)
    # settle residency + attribute energy ONLY through partial_end_time.
    run_ctx.settle_residency_to(partial_end_time)
    # assertions: no live event/request remains.
    assert not any(r.queue_status in ("QUEUED", "DISPATCHING")
                   for r in eq.queued_event_registry.values()), "live queued event after partial"
    assert not any(dr.status in ("PENDING", "SEATED")
                   for dr in run_ctx.driver_request_registry.values()), "live request after partial"
    run_ctx.run_finalised = True
    run_ctx.run_end_time = partial_end_time
    run_ctx.run_disposition = reason
    return Outcome("run_finalised_partial", partial_end_time=partial_end_time, reason=reason,
                   cancelled_events=cancelled)


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
            # AI6/S2A-6: deterministic terminate-partial at the declared partial end time.
            partial_end = (run_ctx.prior_round_terminal_state or {}).get(
                "round_terminal_time", eq.earliest_time() or T)
            FinalizeSimulationRunPartial(run_ctx, partial_end_time=partial_end,
                                         reason="next_round_bootstrap_failed")
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
