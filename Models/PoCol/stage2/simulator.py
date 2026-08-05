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
                       ReserveActivationRequest, ReserveMinerRecord, RangeSlice,
                       compute_h_effective, partition_primary_and_reserve,
                       select_reserves_to_cover, PRIMARY_ASSIGNMENT,
                       ACTIVATED_RESERVE_ASSIGNMENT, TERMINAL_RESERVE_STATUSES,
                       TERMINAL_REQUEST_STATUSES, FULL_DOMAIN_EXHAUSTED_NO_BLOCK,
                       ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN)
from .leases import (RangeLease, RangeProgress, RangeReassignmentDecision,
                     RangeReassignmentRequest, RangeLeaseObservation, ReassignmentWakeHandle,
                     ReassignmentCandidate,
                     lease_id as _mk_lease_id, reassignment_request_id as _mk_reassign_id,
                     select_reassignment_candidate, TERMINAL_LEASE_STATUSES,
                     TERMINAL_REASSIGN_REQUEST_STATUSES, REASSIGNED_PRIMARY_WORK,
                     REASSIGNED_RESERVE_WORK, LEASE_TRIGGERS)
# Stage 5: bounded adversarial-behaviour + parameterised incentive layer.  EVERY hook below is
# a no-op unless the Stage-5 model is explicitly enabled, so the accepted Stage-4C behaviour is
# preserved exactly (S5-01).  Stage 5 MODELS behaviours and MEASURES outcomes; it makes no
# incentive-compatibility, fairness, Sybil-resistance, selfish-mining-resistance,
# coalition-resistance, common-prefix, chain-quality or PoW-equivalent security claim.
from . import adversarial_runtime as _adv
from .adversarial import ADVERSARIAL_COVERAGE_GAP_NO_BLOCK
from .refinement import (ActivationBatch, BreachEpisode, CoarseRequest, PredictionRecord,
                         TERMINAL_EPISODE_STATUSES, h_pipeline as _r5_h_pipeline,
                         h_useful_available as _s8s_h_useful_available,
                         predict_h_future as _r4_predict_h_future)

#: S8S-4 evaluation-ledger kind for coarse-reassigned receiver work (a PRIMARY-domain
#: suffix taken over by an already-awake finished miner; never reserve-domain work).
COARSE_REASSIGNED_WORK = "COARSE_REASSIGNED_WORK"

_TERMINAL_ROUND = ("ROUND_ACCEPTED", "ROUND_ABORTED")

# S4A-1/S4A-2/S4A-3/S4B-1: a lease trigger -> (terminal lease status, lease_stats counter,
# terminal MINER state).  MINER_FAILED and MINER_CANCELLED are DISTINCT dispositions (a failure
# is an involuntary fault -> OFFLINE/REVOKED; a cancellation is a voluntary withdrawal ->
# LOW_POWER_LISTEN/CANCELLED).  A time-expiry / progress-timeout terminalises the lease EXPIRED
# and idles the miner to LOW_POWER_LISTEN.  A round-close terminalises to CANCELLED.  Whatever the
# disposition, the miner leaves ACTIVE_HASHING/WAKING at the terminalisation time (S4B-1) and the
# unfinished suffix is still handed to reassignment.
_TRIGGER_TERMINALISATION = {
    "LEASE_TIME_EXPIRED": ("EXPIRED", "leases_expired", "LOW_POWER_LISTEN"),
    "PROGRESS_TIMEOUT": ("EXPIRED", "leases_expired", "LOW_POWER_LISTEN"),
    "MINER_FAILED": ("REVOKED", "leases_revoked", "OFFLINE"),
    "MINER_CANCELLED": ("CANCELLED", "leases_cancelled", "LOW_POWER_LISTEN"),
    "ROUND_CLOSING": ("CANCELLED", "leases_cancelled", "LOW_POWER_LISTEN"),
}

# S4B-1: the miner states from which a lease terminalisation must actively idle the miner.
_LIVE_MINER_STATES = ("ACTIVE_HASHING", "WAKING", "EXHAUSTED_PENDING")

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
        # S5B-8: the security floor and reported-rate allocation now COMPOSE instead of the
        # allocation mode being silently dropped.  The reserve-domain slices keep exactly the
        # sizes the floor gave them; only the PRIMARY span is re-sized from reported rates, so
        # the domain stays fully covered and pairwise disjoint under both features at once.
        if _adv.reported_rate_allocation_enabled(run_ctx) and ranges:
            _adv.prematerialise_behaviours(run_ctx, rc, sorted(participants),
                                           lambda i, m: cfg.hash_rate_for(i))
            p_lo = min(lo for lo, _hi in ranges.values())
            p_hi = max(hi for _lo, hi in ranges.values())
            ranges = _adv.allocate_by_reported_rate(run_ctx, rc, p_hi - p_lo,
                                                    sorted(participants), start=p_lo)
    elif _adv.reported_rate_allocation_enabled(run_ctx):
        # S5A-3: size the ranges from the REPORTED rates.  Profiles must exist BEFORE sizing, so
        # they are pre-materialised here.  The total domain, disjointness and full coverage are
        # unchanged — only the SIZING uses reported rates, never the physical hash capacity.
        _adv.prematerialise_behaviours(run_ctx, rc, sorted(participants),
                                       lambda i, m: cfg.hash_rate_for(i))
        ranges = _adv.allocate_by_reported_rate(run_ctx, rc, cfg.nonce_domain_size,
                                                sorted(participants))
    else:
        ranges = partition_domain(cfg.nonce_domain_size, participants)
        # S4-10: when the range-lease layer is engaged (floor off), the whole domain still
        # goes to the primaries, but bare reserve records are registered so an AVAILABLE
        # reserve can be selected as a reassignee (via the accepted Stage-3 wake, Path B).
        if cfg.range_lease.enabled and reserve_ids:
            for j, mid in enumerate(reserve_ids):
                if (rc.RoundID, mid) not in run_ctx.reserve_records:
                    run_ctx.reserve_records[(rc.RoundID, mid)] = ReserveMinerRecord(
                        MinerID=mid, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
                        hash_rate=cfg.hash_rate_for(len(participants) + j),
                        reserve_status="AVAILABLE", activation_priority=j)
    rc.search_states = {}
    # S5-10: snapshot each miner's sanctioned-availability residency at round start so the
    # availability reward is a per-round DELTA, never the cumulative run total.
    _adv.snapshot_availability(run_ctx, rc, t)
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
        # S4-1/S4-3: give every primary assignment a RangeSlice + authoritative RangeProgress
        # + one ACTIVE RangeLease over its exact range.
        if run_ctx.config.range_lease.enabled:
            slice_id = f"PS-{rc.RoundID}-{mid}"
            _create_range_progress_and_lease(run_ctx, rc, mid, aid, version, slice_id,
                                             start, end, PRIMARY_ASSIGNMENT, t)
        # S5-1: materialise this participant's ROUND-BOUND immutable behaviour profile BEFORE
        # its wake is seated, so a free rider's reduced physical rate and a delayed waker's
        # extra latency both apply from the very first batch.  The physical search core always
        # runs on the ACTUAL (effective) rate; a reported rate never alters it (S5-4).
        _adv.materialise_behaviours(run_ctx, rc, [mid])
        _adv.record_allocation_projection(run_ctx, rc, mid, st)   # S5A-3
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
    # S4B-8: the primary leases were minted before this transition, so their initial deadline
    # events carry the pre-transition round-state version.  Re-arm them now so every armed
    # deadline's expected_round_state_version matches the SOLUTION_PROPAGATION state the deadline
    # handlers verify against.
    if run_ctx.config.range_lease.enabled:
        for mid in participants:
            slice_id = run_ctx.slice_of_miner.get((rc.RoundID, mid))
            prog = run_ctx.range_progress.get(slice_id) if slice_id else None
            lease = run_ctx.range_leases.get(prog.current_lease_id) if prog is not None else None
            if lease is not None and lease.lease_status == "ACTIVE":
                _rearm_lease_deadlines(run_ctx, rc, prog, lease, t)
    # S3A-2: take the FIRST security-floor observation as soon as the round begins expecting
    # capacity (all primaries WAKING, H_effective == 0) — do NOT wait for every primary to
    # finish WAKING.  Pending WAKING-primary capacity is accounted, so this observes (and
    # opens) the real initial below-floor interval without spuriously seating reserves.
    if pol.enabled:
        # measure-only at round start (no seat/abort until time advances past the ramp).
        EvaluateSecurityFloor(run_ctx, rc, t, "participants_prepared", decide=False)
    # S4-4: seat any injected lease-fault (miner failure) events for this round (test-only;
    # empty in confirmatory runs).  Each seats a MinerFailureEvent at its declared fail_time.
    if cfg.range_lease.enabled:
        _eq = run_ctx.event_queue
        for fault in cfg.injected_lease_faults:
            f_round_seq, f_mid, f_time, f_reason = fault
            if f_round_seq == run_ctx.round_seq and f_mid in rc.search_states:
                ScheduleEvent(_eq, rc, "MinerFailureEvent", f_time, "MINER_FAILURE",
                              {"MinerID": f_mid, "RoundID_at_seat": rc.RoundID,
                               "TemplateID_at_seat": rc.TemplateID_committed,
                               "fault_reason": f_reason}, ordinary_dispatch_origin(_eq))
        # S4A-3: injected VOLUNTARY cancellations (test-only; empty in confirmatory runs) — each
        # seats a MinerCancelledEvent (distinct disposition from a failure) at its declared time.
        for cxl in cfg.injected_lease_cancellations:
            c_round_seq, c_mid, c_time, c_reason = cxl
            if c_round_seq == run_ctx.round_seq and c_mid in rc.search_states:
                ScheduleEvent(_eq, rc, "MinerCancelledEvent", c_time, "MINER_CANCELLED",
                              {"MinerID": c_mid, "RoundID_at_seat": rc.RoundID,
                               "TemplateID_at_seat": rc.TemplateID_committed,
                               "cancellation_reason": c_reason}, ordinary_dispatch_origin(_eq))
    return Outcome("participant_set_prepared", participants=len(participants),
                   nonce_domain_size=cfg.nonce_domain_size,
                   reserve_slices=len(run_ctx.reserve_slices.get(rc.RoundID, [])))


def _start_wake(run_ctx: RunContext, rc: RoundContext, mid: Any, aid: Any,
                version: int) -> Outcome:
    """StartWake: seat a WakeCompleteEvent at now + wake_latency (H5/F5)."""
    eq = run_ctx.event_queue
    cfg = run_ctx.config
    target = eq.current_event_time + cfg.wake_latency
    # S5-7: a DELAYED_WAKE actor stays WAKING for an extra deterministic interval.  It is NOT
    # a free energy saving — the miner is charged P_wake over the whole extended interval and
    # contributes zero to H_effective for its entire duration.
    target += _adv.wake_extra_latency(run_ctx, rc, mid, target, eq.current_event_time,
                                      request_id=("PRIMARY_WAKE", mid, aid, version),
                                      lifecycle="PRIMARY_WAKE")
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
    _adv.complete_delayed_wake(run_ctx, rc, mid, t)        # S5-7: close the delayed-wake action
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
    # S4-3: when the range-lease layer is enabled, EVERY HashWorkEvent carries the current
    # LeaseID + lease generation so a stale event from a superseded lease is stale-safe.
    if run_ctx.config.range_lease.enabled:
        lease = _current_lease_for_miner(run_ctx, rc, st.MinerID)
        if lease is not None:
            payload["LeaseID"] = lease.LeaseID
            payload["lease_generation"] = lease.lease_generation
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
    # S4-3: verify the current lease BEFORE any mutation; a stale event from a superseded
    # (revoked / reassigned) lease performs NO effect (S4-09).
    lguard = _verify_hash_lease(run_ctx, rc, st, mid, payload)
    if lguard.kind != "hash_lease_ok":
        run_ctx.lease_stats["stale_old_lease_events"] += 1
        return Outcome("hash_work_no_effect", reason=lguard, MinerID=mid)
    # S5-9: an OUT_OF_RANGE actor attempts a nonce outside its own assigned range.  The attempt
    # is REJECTED before any accounting — it creates no evaluation-ledger record, no committed
    # frontier advance and no reward, only invalid-message penalty eligibility.
    _adv.maybe_out_of_range_attempt(run_ctx, rc, st, now)
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
    # S4-2/S4-3: advance the authoritative committed_frontier (monotonic, causal — planning
    # advanced nothing) and tag the ledger record with the lease provenance.
    slice_id = lease_gen = prog_gen = pred_lease = lease_ref = None
    if cfg.range_lease.enabled:
        slice_id = run_ctx.slice_of_miner.get((rc.RoundID, mid))
        prog = run_ctx.range_progress.get(slice_id) if slice_id else None
        if prog is not None:
            assert commit_end <= prog.range_end, "committed_frontier exceeds range_end"
            # S5A-1: record the PHYSICAL interval and advance any open re-evaluation window.
            _adv.note_physical_commit(run_ctx, rc, slice_id, cursor_start, commit_end, mid)
            _in_reeval = run_ctx.adv_reeval_window.get(slice_id) is not None or \
                commit_end < prog.committed_frontier
            if not _in_reeval:
                assert commit_end >= prog.committed_frontier, "committed_frontier decreased"
            advanced = commit_end > prog.committed_frontier
            # MONOTONIC: adversarially-induced re-evaluation below the frontier is real physical
            # work, but it is not new coverage and must NEVER rewind the accepted Stage-4C
            # authoritative frontier.
            prog.committed_frontier = max(prog.committed_frontier, commit_end)
            lease_ref = run_ctx.range_leases.get(prog.current_lease_id)
            if lease_ref is not None:
                lease_ref.committed_cursor = commit_end
                lease_gen = lease_ref.lease_generation
                pred_lease = lease_ref.predecessor_lease_id
            # S4B-8: EVERY causal committed-frontier advance increments progress_generation,
            # updates last_progress_time, increments timeout_generation and re-arms one fresh
            # expiry + timeout deadline with the current identity (planning a batch advances
            # nothing).  The old deadlines are superseded so any queued deadline is stale-safe.
            if advanced and lease_ref is not None and lease_ref.lease_status == "ACTIVE":
                prog.progress_generation += 1
                prog.last_progress_time = now
                _rearm_lease_deadlines(run_ctx, rc, prog, lease_ref, now)
            prog_gen = prog.progress_generation
    # S5B-8/S5B-6: count EVERY committed physical evaluation (range leases on or off) and map it
    # onto the committing assignment's subassignments.  This is the single accounting authority,
    # so a zero physical count can never sit beside a non-empty evaluation ledger.
    _adv.note_physical_evaluation(run_ctx, rc, st, cursor_start, commit_end, now)
    run_ctx.evaluation_ledger.append(EvaluationRecord(
        RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed, MinerID=mid,
        AssignmentID=st.AssignmentID, assignment_version=st.assignment_version,
        interval_start=cursor_start, interval_end=commit_end, completion_time=now,
        contained_solution=(winner_nonce is not None), winning_nonce=winner_nonce,
        event_ref=er, assignment_kind=kind, RangeSliceID=slice_id,
        LeaseID=(lease_ref.LeaseID if lease_ref is not None else None),
        lease_generation=lease_gen or 0, progress_generation=prog_gen or 0,
        predecessor_lease_id=pred_lease))
    if kind in (ACTIVATED_RESERVE_ASSIGNMENT, REASSIGNED_RESERVE_WORK):
        run_ctx.security_stats["activated_reserve_evaluation_count"] += committed
    run_ctx.final_searched[(rc.RoundID, mid)] = st.searched_count
    if winner_nonce is not None:                           # first valid solution in sim time
        # S5-6: a SOLUTION_WITHHOLDER does NOT publish the valid block it just found.  The real
        # solution is recorded as ground truth and NO acceptance is seated now; the round must
        # then reach its own honest disposition.  Withholding never alters the fixed SHA-256
        # target or difficulty, and the model makes no claim that it is detectable in a real
        # deployment.
        if _adv.maybe_withhold_solution(run_ctx, rc, st, winner_nonce,
                                        sha256_int(tpl.header_bytes, winner_nonce), now):
            st.completed = True
            st.completion_kind = "SOLUTION_WITHHELD"
            m = run_ctx.miners.get(mid)
            if m is not None and m.state == "ACTIVE_HASHING":
                run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", now)
            return Outcome("hash_work_solution_withheld", MinerID=mid,
                           searched=st.searched_count, committed=committed)
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
    # S5-5: a FALSE_EXHAUSTION_CLAIMER stops here and claims its range is finished.  When the
    # modeled audit does NOT detect the claim the miner idles with an uncovered suffix, and
    # that suffix is an explicit coverage gap which forbids a full-domain exhaustion label.
    # S5A-5: an IDLE_POLICY_DEFECTOR EXECUTES its declared abandonment here, leaving a real
    # uncovered suffix.  Only an executed action can ever attract an abandonment penalty.
    ab = _adv.maybe_abandon(run_ctx, rc, st, now)
    if ab is not None:
        # S5B-7: an executed abandonment REMOVES active capacity, so the operational security
        # floor must be re-evaluated at that capacity-change point exactly as any other one —
        # the floor may now be breached and a reserve may have to be activated.
        abort = EvaluateSecurityFloor(run_ctx, rc, now, "adversarial_abandonment",
                                      trigger=("ABANDONMENT", ab.ActionID))
        if abort is not None:
            return abort
        term = _maybe_terminate_no_block(run_ctx, rc)
        return term if term is not None else Outcome(
            "hash_work_intentionally_abandoned", MinerID=mid,
            abandoned_nonce_count=ab.abandoned_nonce_count())
    fe = _adv.maybe_false_exhaustion(run_ctx, rc, st, now)
    if fe is not None:
        term = _maybe_terminate_no_block(run_ctx, rc)
        return term if term is not None else fe
    # Stage-8R (R4): predictive wake-ahead check at each committed batch — the forecast
    # changes as cursors advance even though physical capacity did not.  Inert in
    # LEGACY_REACTIVE and HYSTERESIS_ONLY modes.
    if cfg.security_floor.enabled and cfg.controller.is_predictive():
        abort = _refined_predictive_check(run_ctx, rc, now)
        if abort is not None:
            return abort
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
    if run_ctx.config.range_lease.enabled:                  # S4-3: carry the current lease
        lease = _current_lease_for_miner(run_ctx, rc, st.MinerID)
        if lease is not None:
            payload["LeaseID"] = lease.LeaseID
            payload["lease_generation"] = lease.lease_generation
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
    # S4B-3: STRICT exhaust identity — the event must carry a LeaseID and have EXACTLY exhausted
    # the slice's CURRENT ACTIVE lease to its range_end (search state completed EXHAUSTED, cursor
    # and committed frontier == range_end, matching generations).  A missing / premature / stale
    # exhaust performs NO state, floor or termination effect (never idles the successor miner).
    lguard = _verify_exhaust_lease(run_ctx, rc, st, mid, payload)
    if lguard.kind != "exhaust_lease_ok":
        run_ctx.lease_stats["stale_exhaust_events"] += 1
        return Outcome("range_exhaust_no_effect", reason=lguard, MinerID=mid)
    m = run_ctx.miners.get(mid)
    t = run_ctx.event_queue.current_event_time
    if m is not None and m.state == "ACTIVE_HASHING":
        run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)   # idle policy
    # Stage-8S: a receiver exhausting its coarse chunk terminalises its request.
    if run_ctx.config.controller.is_coarse():
        _coarse_note_completion(run_ctx, rc, mid, t)
    # S4A-9: a reassignee that exhausts its suffix ends its reassigned ACTIVE_HASHING interval.
    if run_ctx.config.range_lease.enabled:
        _stamp_reassignee_active_end(run_ctx, rc, mid, t)
    # S4-2: a range searched to the end COMPLETES its lease and closes its RangeProgress at
    # the frontier (== range_end) — no reassignment for a completed lease.
    if run_ctx.config.range_lease.enabled:
        _complete_lease_at_exhaustion(run_ctx, rc, mid, t)
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
    # S4-12/S4-17/S4-18: with the range-lease layer engaged, RangeProgress is authoritative.
    # A reassignment still in flight means work is incoming (do not terminate); any lease
    # suffix left unfinished (or an unclaimed reserve-domain slice) forbids a full-domain
    # exhaustion claim — the round closes with an explicit unassigned/unused disposition.
    if run_ctx.config.range_lease.enabled:
        if _reassignment_in_flight(run_ctx, rc):
            return None
        progs = [p for p in run_ctx.range_progress.values() if p.RoundID == rc.RoundID]
        unfinished = [p for p in progs if p.committed_frontier < p.range_end]
        unclaimed_reserve = [sl for sl in run_ctx.reserve_slices.get(rc.RoundID, [])
                             if sl.status == "UNCLAIMED"]
        if unfinished or unclaimed_reserve:
            for p in unfinished:
                if p.terminal_status == "OPEN":
                    p.terminal_status = "UNASSIGNED_AT_ROUND_CLOSE"
            run_ctx.lease_stats["uncovered_range_count"] += len(unfinished)
            run_ctx.lease_stats["uncovered_nonce_count"] += sum(p.uncovered()
                                                                for p in unfinished)
            # S5B-7: an adversarially created coverage gap (executed abandonment, accepted false
            # exhaustion, withheld solution) is named EXPLICITLY rather than folded into the
            # generic unassigned-range disposition — the cause of the uncovered suffix is the
            # adversarial action, not an unfilled reassignment.
            if _adv.round_has_coverage_gap(run_ctx, rc):
                return RoundAbort(run_ctx, rc, reason=ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
                                  envelope={})
            if unclaimed_reserve:
                run_ctx.security_stats["unused_reserve_domain_count"] += 1
                return RoundAbort(run_ctx, rc, reason=ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN,
                                  envelope={})
            return RoundAbort(run_ctx, rc, reason="round_closed_with_unassigned_range",
                              envelope={})
        if _adv.round_has_coverage_gap(run_ctx, rc):
            return RoundAbort(run_ctx, rc, reason=ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
                              envelope={})
        run_ctx.security_stats["full_domain_exhausted_count"] += 1
        return RoundAbort(run_ctx, rc, reason=FULL_DOMAIN_EXHAUSTED_NO_BLOCK, envelope={})
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
    # S5-5/S5-6: an accepted false-exhaustion coverage gap or a withheld valid solution means
    # the domain was NOT honestly searched — such a round is never labelled a full-domain
    # exhaustion, whether or not reserve slices exist.
    if _adv.round_has_coverage_gap(run_ctx, rc):
        return RoundAbort(run_ctx, rc, reason=ADVERSARIAL_COVERAGE_GAP_NO_BLOCK, envelope={})
    if slices:
        # every primary AND reserve slice was evaluated: a true full-domain exhaustion.
        run_ctx.security_stats["full_domain_exhausted_count"] += 1
        return RoundAbort(run_ctx, rc, reason=FULL_DOMAIN_EXHAUSTED_NO_BLOCK, envelope={})
    return RoundAbort(run_ctx, rc, reason="round_exhausted_no_block", envelope={})


# ============================================================ Stage-4 range leases
def _residency(m: Any, state: str, t: Optional[float] = None) -> float:
    """S4C-1: a miner's cumulative residency (seconds) in one state AT time ``t``, 0.0 for a missing
    miner.  The residency ledger only accumulates CLOSED intervals, so when the miner is CURRENTLY
    in ``state`` its still-open interval ``[state_since, t]`` must be added — otherwise a snapshot
    taken mid-interval (e.g. an OFFLINE predecessor between revocation and round close) understates
    the true residency.  ``t`` omitted returns the closed-interval total only."""
    if m is None:
        return 0.0
    base = m.duration.get(state, 0.0)
    since = getattr(m, "state_since", None)
    if t is not None and m.state == state and since is not None and t >= since:
        base += (t - since)
    return base


def _stamp_lease_start_residency(run_ctx: RunContext, lease: Any, t: float) -> None:
    """S4C-1: snapshot the lease-holder's cumulative per-state residency AT lease start, so the
    predecessor active / idle energy is later charged over EXACTLY this lease's interval (a
    residency-ledger DELTA), never the miner's whole-run cumulative residency."""
    m = run_ctx.miners.get(lease.MinerID)
    lease.active_residency_at_lease_start = _residency(m, "ACTIVE_HASHING", t)
    lease.low_residency_at_lease_start = _residency(m, "LOW_POWER_LISTEN", t)
    lease.offline_residency_at_lease_start = _residency(m, "OFFLINE", t)


def _create_range_progress_and_lease(run_ctx: RunContext, rc: RoundContext, mid: Any,
                                     aid: Any, version: int, slice_id: str, start: int,
                                     end: int, kind: str, t: float) -> Any:
    """S4-1/S4-2: mint the authoritative RangeProgress + one ACTIVE RangeLease for a slice."""
    run_ctx.slice_of_miner[(rc.RoundID, mid)] = slice_id
    run_ctx.lease_generation_of_slice[slice_id] = 1
    lid = _mk_lease_id(rc.RoundID, rc.TemplateID_committed, slice_id, 1)
    prog = RangeProgress(
        RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed, RangeSliceID=slice_id,
        range_start=start, range_end=end, committed_frontier=start, current_lease_id=lid,
        progress_generation=0, terminal_status="OPEN", assignment_kind=kind,
        last_progress_time=t)
    run_ctx.range_progress[slice_id] = prog
    lease = RangeLease(
        LeaseID=lid, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        RangeSliceID=slice_id, lease_generation=1, AssignmentID=aid,
        assignment_version=version, MinerID=mid, assignment_kind=kind,
        lease_start_nonce=start, lease_end_nonce=end, committed_cursor=start,
        lease_start_time=t, lease_expiry_time=t + run_ctx.config.range_lease.lease_duration,
        lease_status="ACTIVE")
    run_ctx.range_leases[lid] = lease
    _stamp_lease_start_residency(run_ctx, lease, t)         # S4C-1
    run_ctx.lease_stats["leases_created"] += 1
    # S4A-1/S4A-2: arm the lease-time-expiry + progress-timeout deadlines for this ACTIVE lease.
    _seat_lease_expiry(run_ctx, rc, lease, prog, t)
    _refresh_progress_timeout(run_ctx, rc, prog, lease, t)
    return lease


def _seat_lease_expiry(run_ctx: RunContext, rc: RoundContext, lease: Any, prog: Any,
                       t: float) -> None:
    """S4A-1/S4B-8: (re)arm ONE RangeLeaseExpiryEvent at ``lease_expiry_time`` for an ACTIVE lease.

    The deadline time is fixed by ``lease_expiry_time``, but the payload identity
    (``expected_progress_generation`` / ``expected_committed_frontier`` / round state version) is
    REFRESHED on every re-arm so the expiry handler can verify EVERY declared field.  The prior
    expiry event is superseded first.  With the default effectively-unbounded ``lease_duration``
    the deadline is post-horizon and ``ScheduleEvent`` rejects it (no event is armed).
    """
    eq = run_ctx.event_queue
    if lease.expiry_event_ref is not None:                   # supersede the prior expiry event
        rec = eq.queued_event_registry.get(lease.expiry_event_ref)
        if rec is not None and rec.queue_status == "QUEUED":
            CancelQueuedEvent(eq, run_ctx, lease.expiry_event_ref,
                              cancellation_reason="expiry_re_armed")
        lease.expiry_event_ref = None
    payload = {"LeaseID": lease.LeaseID, "RoundID_at_seat": rc.RoundID,
               "TemplateID_at_seat": rc.TemplateID_committed, "RangeSliceID": lease.RangeSliceID,
               "MinerID": lease.MinerID, "lease_generation": lease.lease_generation,
               "expected_lease_status": "ACTIVE",
               "expected_progress_generation": prog.progress_generation,
               "expected_committed_frontier": prog.committed_frontier,
               "expected_round_state_version": rc.state_version}
    r = ScheduleEvent(eq, rc, "RangeLeaseExpiryEvent", lease.lease_expiry_time,
                      "RANGE_LEASE_EXPIRY", payload, ordinary_dispatch_origin(eq))
    lease.expiry_event_ref = r.event_ref if r.kind == "scheduled" else None


def _rearm_lease_deadlines(run_ctx: RunContext, rc: RoundContext, prog: Any, lease: Any,
                           t: float) -> None:
    """S4B-8: re-arm BOTH the expiry and the progress-timeout deadline with fresh identity after a
    causal frontier advance (the timeout deadline moves forward; the expiry deadline time is fixed
    but its expected-progress-generation / expected-committed-frontier are refreshed)."""
    _refresh_progress_timeout(run_ctx, rc, prog, lease, t)
    _seat_lease_expiry(run_ctx, rc, lease, prog, t)


def _refresh_progress_timeout(run_ctx: RunContext, rc: RoundContext, prog: Any, lease: Any,
                              t: float) -> None:
    """S4A-2: (re)arm the progress-timeout deadline at ``last_progress_time + progress_timeout``.

    Called at lease creation and on EVERY causal frontier advance (NOT on planning): the prior
    timeout event is cancelled, ``timeout_generation`` is bumped so any already-queued timeout
    event becomes stale, and a fresh RangeProgressTimeoutEvent is armed.  A default unbounded
    ``progress_timeout`` is post-horizon and arms nothing.
    """
    eq = run_ctx.event_queue
    if prog.timeout_event_ref is not None:
        rec = eq.queued_event_registry.get(prog.timeout_event_ref)
        if rec is not None and rec.queue_status == "QUEUED":
            CancelQueuedEvent(eq, run_ctx, prog.timeout_event_ref,
                              cancellation_reason="progress_advanced")
        prog.timeout_event_ref = None
    prog.timeout_generation += 1
    deadline = prog.last_progress_time + run_ctx.config.range_lease.progress_timeout
    payload = {"LeaseID": lease.LeaseID, "RoundID_at_seat": rc.RoundID,
               "TemplateID_at_seat": rc.TemplateID_committed, "RangeSliceID": prog.RangeSliceID,
               "MinerID": lease.MinerID, "lease_generation": lease.lease_generation,
               "expected_lease_status": "ACTIVE",         # S4C-5: BOTH deadlines carry it explicitly
               "expected_committed_frontier": prog.committed_frontier,
               "expected_progress_generation": prog.progress_generation,
               "timeout_generation": prog.timeout_generation,
               "expected_round_state_version": rc.state_version}
    r = ScheduleEvent(eq, rc, "RangeProgressTimeoutEvent", deadline, "RANGE_PROGRESS_TIMEOUT",
                      payload, ordinary_dispatch_origin(eq))
    prog.timeout_event_ref = r.event_ref if r.kind == "scheduled" else None


def _cancel_lease_deadlines(run_ctx: RunContext, lease: Any, prog: Any) -> None:
    """S4A-1/S4A-2: cancel any queued expiry / progress-timeout deadline of a terminalising lease."""
    eq = run_ctx.event_queue
    for ref in (getattr(lease, "expiry_event_ref", None),
                getattr(prog, "timeout_event_ref", None) if prog is not None else None):
        if ref is None:
            continue
        rec = eq.queued_event_registry.get(ref)
        if rec is not None and rec.queue_status == "QUEUED":
            CancelQueuedEvent(eq, run_ctx, ref, cancellation_reason="lease_terminalised")
    lease.expiry_event_ref = None
    if prog is not None:
        prog.timeout_event_ref = None


def _current_lease_for_miner(run_ctx: RunContext, rc: RoundContext, mid: Any) -> Any:
    slice_id = run_ctx.slice_of_miner.get((rc.RoundID, mid))
    if slice_id is None:
        return None
    prog = run_ctx.range_progress.get(slice_id)
    if prog is None or prog.current_lease_id is None:
        return None
    lease = run_ctx.range_leases.get(prog.current_lease_id)
    if lease is not None and lease.MinerID == mid and lease.lease_status == "ACTIVE":
        return lease
    return None


def _verify_hash_lease(run_ctx: RunContext, rc: RoundContext, st: Any, mid: Any,
                       payload: Dict[str, Any]) -> Outcome:
    """S4-3: verify the current lease BEFORE any search-state mutation."""
    if not run_ctx.config.range_lease.enabled:
        return Outcome("hash_lease_ok")
    lid = payload.get("LeaseID")
    if lid is None:
        return Outcome("hash_lease_missing")
    lease = run_ctx.range_leases.get(lid)
    if lease is None:
        return Outcome("hash_lease_unknown")
    if lease.lease_status != "ACTIVE":
        return Outcome("hash_lease_not_active", actual=lease.lease_status)
    if lease.RoundID != rc.RoundID or lease.TemplateID != rc.TemplateID_committed:
        return Outcome("hash_lease_round_mismatch")
    if lease.MinerID != mid:
        return Outcome("hash_lease_owner_mismatch")
    if lease.AssignmentID != payload["AssignmentID"] \
            or lease.assignment_version != payload["assignment_version"]:
        return Outcome("hash_lease_assignment_mismatch")
    if lease.lease_generation != payload.get("lease_generation"):
        return Outcome("hash_lease_generation_mismatch")
    prog = run_ctx.range_progress.get(lease.RangeSliceID)
    if prog is None:
        return Outcome("hash_lease_no_progress")
    if prog.current_lease_id != lid:                       # S4-09 superseded lease
        return Outcome("hash_lease_superseded")
    # S5A-1: normally the authoritative physical frontier.  While an adversarial re-evaluation
    # window is open the successor legitimately works BELOW that frontier (which is never
    # rewound), so the window's cursor is what the event must carry.
    _expected = _adv.expected_cursor_for_lease(run_ctx, prog)
    if payload["cursor_start"] != _expected:
        return Outcome("hash_lease_frontier_mismatch", expected=_expected,
                       got=payload["cursor_start"])
    now = run_ctx.event_queue.current_event_time
    if now is not None and now > lease.lease_expiry_time + run_ctx.config.range_lease.lease_tolerance:
        return Outcome("hash_lease_expired")
    return Outcome("hash_lease_ok")


def _verify_exhaust_lease(run_ctx: RunContext, rc: RoundContext, st: Any, mid: Any,
                          payload: Dict[str, Any]) -> Outcome:
    """S4B-3: STRICT RangeExhaust identity — the event has EXACTLY exhausted the slice's CURRENT
    ACTIVE lease, and nothing else, before any state / floor / termination effect.

    When range leases are enabled the event MUST carry a LeaseID (a missing LeaseID is rejected).
    A missing, premature (cursor / frontier not at range_end, search state not completed
    EXHAUSTED, stale search generation) or stale (superseded lease / generation) exhaust event
    performs NO effect.
    """
    if not run_ctx.config.range_lease.enabled:
        return Outcome("exhaust_lease_ok")
    lid = payload.get("LeaseID")
    if lid is None:                                          # S4B-3: reject a missing LeaseID
        return Outcome("exhaust_lease_missing")
    if "lease_generation" not in payload:
        return Outcome("exhaust_lease_generation_missing")
    lease = run_ctx.range_leases.get(lid)
    if lease is None:
        return Outcome("exhaust_lease_unknown")
    if lease.lease_status != "ACTIVE":
        return Outcome("exhaust_lease_not_active", actual=lease.lease_status)
    if lease.RoundID != rc.RoundID or lease.TemplateID != rc.TemplateID_committed:
        return Outcome("exhaust_lease_round_mismatch")
    if lease.MinerID != mid:
        return Outcome("exhaust_lease_owner_mismatch")
    if lease.AssignmentID != payload.get("AssignmentID") \
            or lease.assignment_version != payload.get("assignment_version"):
        return Outcome("exhaust_lease_assignment_mismatch")
    if lease.lease_generation != payload.get("lease_generation"):
        return Outcome("exhaust_lease_generation_mismatch")
    prog = run_ctx.range_progress.get(lease.RangeSliceID)
    if prog is None or prog.current_lease_id != lid:
        return Outcome("exhaust_lease_superseded")
    # premature-exhaust guards: the range must ACTUALLY be exhausted to its end.
    if st is None or not st.completed or st.completion_kind != "EXHAUSTED":
        return Outcome("exhaust_lease_not_exhausted")
    if st.search_generation != payload.get("expected_search_generation"):
        return Outcome("exhaust_lease_search_generation_mismatch")
    if st.cursor != st.range_end or prog.committed_frontier != prog.range_end:
        return Outcome("exhaust_lease_frontier_incomplete",
                       cursor=st.cursor, range_end=st.range_end,
                       frontier=prog.committed_frontier)
    return Outcome("exhaust_lease_ok")


def _stamp_request_terminal(run_ctx: RunContext, req: Any, t: float) -> None:
    """S4C-1: at a reassignment request's terminal time, CLOSE the predecessor's post-revocation
    idle/offline interval [revocation, terminal] with a residency snapshot, and — when the wake
    NEVER started — close the reassignee's standby interval at [seat, terminal] (its wake-start
    snapshots become the terminal residency).  Charging always uses the earlier of these interval
    ends, never the final run residency.  Idempotent: only the FIRST terminalisation stamps."""
    if req.terminal_time is not None:
        return
    req.terminal_time = t
    pm = run_ctx.miners.get(req.predecessor_MinerID)
    req.predecessor_low_residency_at_request_terminal = _residency(pm, "LOW_POWER_LISTEN", t)
    req.predecessor_offline_residency_at_request_terminal = _residency(pm, "OFFLINE", t)
    if req.started_at is None:                              # wake never began
        cm = run_ctx.miners.get(req.new_MinerID)
        req.reassignee_reserve_residency_at_wake_start = _residency(cm, "RESERVE", t)
        req.reassignee_low_residency_at_wake_start = _residency(cm, "LOW_POWER_LISTEN", t)
        req.reassignee_offline_residency_at_wake_start = _residency(cm, "OFFLINE", t)


def _stamp_reassignee_active_end(run_ctx: RunContext, rc: RoundContext, mid: Any,
                                 t: float) -> None:
    """S4A-9: close a reassignee's reassigned ACTIVE_HASHING interval at ``t`` (energy attribution).

    Only the reassignment lifecycle interval — not the reassignee's full residency (which may
    include its own earlier primary work) — is attributed to the reassignment.
    """
    m = run_ctx.miners.get(mid)
    for req in run_ctx.reassignment_requests.values():
        if req.RoundID == rc.RoundID and req.new_MinerID == mid \
                and req.status == "COMPLETED" \
                and req.reassigned_search_start_time is not None \
                and req.reassigned_search_end_time is None:
            req.reassigned_search_end_time = t
            # S4A-9: the reassignee just left ACTIVE_HASHING — the ledger's cumulative
            # ACTIVE_HASHING is now finalised for this interval (exact energy reconciliation).
            req.active_residency_at_search_end = m.duration.get("ACTIVE_HASHING", 0.0) \
                if m is not None else None


def _complete_lease_at_exhaustion(run_ctx: RunContext, rc: RoundContext, mid: Any,
                                  t: float) -> None:
    slice_id = run_ctx.slice_of_miner.get((rc.RoundID, mid))
    prog = run_ctx.range_progress.get(slice_id) if slice_id else None
    if prog is None:
        return
    lease = run_ctx.range_leases.get(prog.current_lease_id)
    if lease is not None and lease.lease_status == "ACTIVE" \
            and prog.committed_frontier >= prog.range_end:
        lease.lease_status = "COMPLETED"
        lease.disposition = Outcome("lease_completed_at_exhaustion")
        prog.terminal_status = "COMPLETED"
        run_ctx.lease_stats["leases_completed"] += 1


def _reassignment_in_flight(run_ctx: RunContext, rc: RoundContext) -> bool:
    for req in run_ctx.reassignment_requests.values():
        if req.RoundID == rc.RoundID and req.status in ("SEATED", "STARTED"):
            return True
    for (rid, _m), rr in run_ctx.reserve_records.items():   # Path-B reserve wake in flight
        if rid == rc.RoundID and rr.reserve_status in ("ACTIVATION_PENDING", "WAKING") \
                and str(rr.assigned_reserve_slice_id or "") in run_ctx.reassign_by_suffix_slice:
            return True
    return False


def _cancel_queued_hash_events(run_ctx: RunContext, mid: Any) -> int:
    """S4B-1: cancel a terminal lease/assignment's queued HashWork, RangeExhaust AND
    WakeCompleteEvent for ``mid`` — a lease that terminalises before WakeCompleteEvent must never
    later activate its miner.  Returns the number of cancelled WakeCompleteEvents."""
    eq = run_ctx.event_queue
    wakes_cancelled = 0
    for ref in list(eq.queued_event_registry.keys()):
        rec = eq.queued_event_registry[ref]
        if rec.queue_status == "QUEUED" \
                and rec.event_type in ("HashWorkEvent", "RangeExhaustEvent", "WakeCompleteEvent") \
                and rec.immutable_payload.get("MinerID") == mid:
            CancelQueuedEvent(eq, run_ctx, ref, cancellation_reason="lease_terminalised")
            if rec.event_type == "WakeCompleteEvent":
                wakes_cancelled += 1
    return wakes_cancelled


def _record_reassignment_decision(run_ctx: RunContext, rc: RoundContext, lease: Any,
                                  chosen: Any, result: str, new_gen: Any = None,
                                  projected_start: Any = None) -> Any:
    run_ctx.reassignment_decision_seq += 1
    prog = run_ctx.range_progress.get(lease.RangeSliceID)
    frontier = prog.committed_frontier if prog else lease.committed_cursor
    dec = RangeReassignmentDecision(
        DecisionID=(run_ctx.RunID, "RDEC", run_ctx.reassignment_decision_seq),
        RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed, RangeSliceID=lease.RangeSliceID,
        predecessor_lease_id=lease.LeaseID, predecessor_committed_frontier=frontier,
        selected_miner_id=(chosen.MinerID if chosen else None), new_lease_generation=new_gen,
        projected_start_time=projected_start,
        projected_hash_rate=(chosen.hash_rate if chosen else 0.0),
        residual_unassigned_work=(prog.uncovered() if prog else 0), policy_result=result)
    run_ctx.reassignment_decisions.append(dec)
    run_ctx.lease_stats["reassignment_decisions"] += 1
    return dec


def _eligible_reassignment_candidates(run_ctx: RunContext, rc: RoundContext, slice_id: str,
                                      revoked_owner: Any, frontier: int,
                                      obs_time: float) -> List[Any]:
    """S4-6: build the deterministic eligible-reassignee candidate list (one-lease-per-miner)."""
    cfg = run_ctx.config
    pol = cfg.range_lease
    prog = run_ctx.range_progress.get(slice_id)
    suffix = max(0, (prog.range_end - frontier) if prog else 0)
    cands: List[Any] = []
    # S4C-2: a miner that already has an IN-FLIGHT reassignment this round (a SEATED / STARTED
    # request not yet COMPLETED / FAILED / CANCELLED) is NOT available — it is between its own
    # reassignment seat and completion, so recruiting it again would double-book its single search
    # (and double-charge its ACTIVE residency to two requests).  One reassignment in flight per miner.
    in_flight = {r.new_MinerID for r in run_ctx.reassignment_requests.values()
                 if r.RoundID == rc.RoundID
                 and r.status not in TERMINAL_REASSIGN_REQUEST_STATUSES}
    # categories 0/1: alive miners (primary / activated-reserve) that EXHAUSTED their own range
    # (searched all of it, found no block) and are therefore genuinely free to help.
    for mid, st in rc.search_states.items():
        if mid == revoked_owner or not st.completed or mid in in_flight:
            continue
        # S4B-1: a miner whose OWN lease was terminalised (EXPIRED / REVOKED / CANCELLED) is marked
        # completed by RevokeRangeLeaseTransaction, but it is NOT an available reassignee — it was
        # idled by that terminalisation and must stay idled, never re-recruited (and never a miner
        # that found a SOLUTION, whose round is being decided).  Only a genuine own-range EXHAUSTED
        # completion makes a miner eligible to take over another slice's unfinished suffix.
        if st.completion_kind != "EXHAUSTED":
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state in ("OFFLINE", "DISQUALIFIED"):
            continue
        okind = run_ctx.search_assignment_kind.get((rc.RoundID, mid), PRIMARY_ASSIGNMENT)
        cat = 1 if okind in (ACTIVATED_RESERVE_ASSIGNMENT, REASSIGNED_RESERVE_WORK) else 0
        rate = st.hash_rate
        proj = obs_time + pol.reassignment_wake_latency + (suffix / rate if rate > 0 else 0.0)
        cands.append(ReassignmentCandidate(mid, cat, proj, 0, False, rate))
    # category 2: AVAILABLE reserves (never activated) requiring the accepted Stage-3 wake.
    for (rid, mid), rr in run_ctx.reserve_records.items():
        if rid != rc.RoundID or mid == revoked_owner or rr.reserve_status != "AVAILABLE" \
                or mid in in_flight:                       # S4C-2: not already reassigning
            continue
        m = run_ctx.miners.get(mid)
        if m is not None and m.state in ("OFFLINE", "DISQUALIFIED"):
            continue
        rate = rr.hash_rate
        proj = obs_time + cfg.security_floor.activation_wake_latency \
            + (suffix / rate if rate > 0 else 0.0)
        cands.append(ReassignmentCandidate(mid, 2, proj, rr.activation_priority, True, rate,
                                           reserve_record=rr))
    return cands


def _trigger_condition_satisfied(run_ctx: RunContext, rc: RoundContext, lease: Any, prog: Any,
                                 trigger: str, now: float) -> bool:
    """S4A-4: whether the observed trigger's condition ACTUALLY holds right now.

    A failure / cancellation is an EXPLICIT fact (the miner already transitioned); a time-expiry
    / progress-timeout is validated against the recorded deadline so a lease is never revoked
    merely because ``EvaluateRangeLease`` was called with a stale or premature deadline.
    """
    pol = run_ctx.config.range_lease
    m = run_ctx.miners.get(lease.MinerID)
    if trigger == "MINER_FAILED":
        return m is not None and m.state == "OFFLINE"
    if trigger == "MINER_CANCELLED":
        return m is not None and m.state != "ACTIVE_HASHING"
    if trigger == "LEASE_TIME_EXPIRED":
        return now + pol.lease_tolerance >= lease.lease_expiry_time
    if trigger == "PROGRESS_TIMEOUT":
        deadline = prog.last_progress_time + pol.progress_timeout
        return (now + pol.lease_tolerance >= deadline) \
            and prog.committed_frontier < prog.range_end
    if trigger == "ROUND_CLOSING":
        return True
    return True


def _append_lease_observation(run_ctx: RunContext, rc: RoundContext, lease: Any, prog: Any,
                              obs_time: float, reason: Any, cond: bool, decision_result: str,
                              status_before: str, frontier: int, pg: int,
                              observation_key: Any, reassignment_decision_id: Any) -> Any:
    """S4A-4: append the ONE authoritative, auditable RangeLeaseObservation for this observation."""
    run_ctx.lease_observation_seq += 1
    obs = RangeLeaseObservation(
        ObservationID=(run_ctx.RunID, "LOBS", run_ctx.lease_observation_seq),
        observation_key=observation_key, LeaseID=lease.LeaseID, RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed, observation_time=obs_time,
        observation_reason=str(reason), lease_status_before=status_before,
        committed_frontier=frontier, progress_generation=pg, condition_satisfied=cond,
        decision_result=decision_result, reassignment_decision_id=reassignment_decision_id)
    run_ctx.lease_observations.append(obs)
    run_ctx.lease_observation_record_by_key[observation_key] = obs
    run_ctx.lease_stats["lease_observation_count"] += 1
    return obs


def EvaluateRangeLease(run_ctx: RunContext, rc: RoundContext, lease_id_val: Any,
                       observation_time: float, trigger: str,
                       triggering_event_ref: Any = None,
                       observation_reason: Any = None) -> Optional[Outcome]:
    """S4-5/S4A-4: the ONE authoritative lease observation + reassignment decision.

    It is AUTHORITATIVE: it validates the trigger condition, records exactly one
    RangeLeaseObservation for every (non-replay) observation, and revokes / reassigns the
    unfinished suffix ONLY when the condition actually holds — never merely because it was
    called.  Terminal disposition follows the trigger (EXPIRED / REVOKED / CANCELLED), which is
    DISTINCT per cause (a failure vs a voluntary cancellation vs a deadline).
    """
    pol = run_ctx.config.range_lease
    if not pol.enabled:
        return None
    lease = run_ctx.range_leases.get(lease_id_val)
    if lease is None:
        return None
    # S4B-2/S4C-6: an unknown trigger is REJECTED before any mutation and the rejection path is
    # STATE-PURE — it changes NO protocol state (lease_stats, lease, progress, miner, decisions,
    # observations, queue, sequences) and there is NO default REVOKED fallback.  Only the DIAGNOSTIC
    # (non-protocol, metrics-excluded) counter records that a rejection was observed.
    if trigger not in LEASE_TRIGGERS:
        run_ctx.lease_diagnostics["unknown_trigger_rejections"] += 1
        return Outcome("range_lease_observation_rejected_unknown_trigger",
                       trigger=trigger, LeaseID=lease_id_val)
    if observation_reason is None:
        observation_reason = trigger
    trig = triggering_event_ref if triggering_event_ref is not None \
        else getattr(run_ctx.event_queue, "current_event_ref", None)
    key = _lease_observation_key(run_ctx, rc, lease, trig)
    if key in run_ctx.lease_observation_by_key:
        # S4B-2/S4C-6: an exact replay returns the COMPLETE stored result (observation,
        # decision-or-null, outcome-or-disposition) — never None — and is STATE-PURE: it mutates no
        # protocol state.  Only the DIAGNOSTIC counter records that a replay was observed.
        run_ctx.lease_diagnostics["lease_observation_replay_count"] += 1
        stored_obs, stored_dec, stored_outcome = run_ctx.lease_observation_by_key[key]
        return Outcome("range_lease_observation_already_exists", observation=stored_obs,
                       decision=stored_dec, outcome=stored_outcome)
    prog = run_ctx.range_progress.get(lease.RangeSliceID)
    status_before = lease.lease_status
    frontier = prog.committed_frontier if prog is not None else lease.committed_cursor
    pg_before = prog.progress_generation if prog is not None else -1
    n_dec_before = len(run_ctx.reassignment_decisions)

    def _finish(cond: bool, decision_result: str, outcome: Optional[Outcome] = None):
        rdid = (run_ctx.reassignment_decisions[-1].DecisionID
                if len(run_ctx.reassignment_decisions) > n_dec_before else None)
        obs = _append_lease_observation(run_ctx, rc, lease, prog, observation_time,
                                        observation_reason, cond, decision_result, status_before,
                                        frontier, pg_before, key, rdid)
        run_ctx.lease_observation_by_key[key] = (obs, rdid, outcome)
        return outcome

    if rc.round_state in _TERMINAL_ROUND:
        _record_reassignment_decision(run_ctx, rc, lease, None, "ROUND_ALREADY_TERMINAL")
        return _finish(False, "ROUND_ALREADY_TERMINAL")
    if prog is None or lease.lease_status in TERMINAL_LEASE_STATUSES:
        return _finish(False, "LEASE_ALREADY_TERMINAL")
    if frontier >= prog.range_end:
        lease.lease_status = "COMPLETED"
        prog.terminal_status = "COMPLETED"
        run_ctx.lease_stats["leases_completed"] += 1
        _cancel_lease_deadlines(run_ctx, lease, prog)
        _record_reassignment_decision(run_ctx, rc, lease, None, "SLICE_ALREADY_COMPLETED")
        return _finish(True, "LEASE_COMPLETED")
    # S4A-4: VALIDATE the trigger condition BEFORE terminalising; an unsatisfied condition leaves
    # the lease ACTIVE (this is what makes EvaluateRangeLease authoritative rather than a rubber
    # stamp for whoever called it).
    if not _trigger_condition_satisfied(run_ctx, rc, lease, prog, trigger, observation_time):
        return _finish(False, "LEASE_REMAINS_ACTIVE")
    # condition satisfied -> terminalise (trigger-specific disposition) + reassign the suffix.
    RevokeRangeLeaseTransaction(run_ctx, rc, lease, trigger)
    if not pol.reassignment_enabled:
        _record_reassignment_decision(run_ctx, rc, lease, None, "REASSIGNMENT_NOT_ALLOWED")
        return _finish(True, "REASSIGNMENT_NOT_ALLOWED", _apply_no_eligible_policy(run_ctx, rc, prog))
    if run_ctx.reassignments_per_slice.get(lease.RangeSliceID, 0) \
            >= pol.maximum_reassignments_per_slice:
        _record_reassignment_decision(run_ctx, rc, lease, None, "REASSIGNMENT_LIMIT_REACHED")
        return _finish(True, "REASSIGNMENT_LIMIT_REACHED", _apply_no_eligible_policy(run_ctx, rc, prog))
    cands = _eligible_reassignment_candidates(run_ctx, rc, lease.RangeSliceID, lease.MinerID,
                                              frontier, observation_time)
    chosen = select_reassignment_candidate(cands)
    if chosen is None:
        _record_reassignment_decision(run_ctx, rc, lease, None, "NO_ELIGIBLE_MINER")
        return _finish(True, "NO_ELIGIBLE_MINER", _apply_no_eligible_policy(run_ctx, rc, prog))
    out = SeatRangeReassignmentTransaction(run_ctx, rc, prog, lease, chosen,
                                           observation_time, trigger)
    return _finish(True, "REASSIGNMENT_REQUIRED", out)


def _lease_observation_key(run_ctx: RunContext, rc: RoundContext, lease: Any,
                           trigger: Any) -> Any:
    # S4A-4: the immutable identity of ONE observation event — the LeaseID already encodes
    # (round, template, slice, generation), and the triggering EventRef makes it unique per
    # observation.  It deliberately excludes mutable progress/state versions so that re-invoking
    # EvaluateRangeLease for the SAME triggering event is idempotent even after that observation
    # has mutated the slice progress.
    return (rc.RoundID, rc.TemplateID_committed, lease.LeaseID, trigger)


def RevokeRangeLeaseTransaction(run_ctx: RunContext, rc: RoundContext, lease: Any,
                                trigger: str) -> Outcome:
    """S4-9/S4A-1/S4A-3/S4B-1: terminalise a lease AND its miner with the trigger disposition.

    ``trigger`` is one of ``LEASE_TRIGGERS``.  A failure -> REVOKED/OFFLINE, a voluntary
    cancellation -> CANCELLED/LOW_POWER_LISTEN, a time-expiry / progress-timeout ->
    EXPIRED/LOW_POWER_LISTEN, a round close -> CANCELLED.  It cancels the exact HashWork,
    RangeExhaust, WakeComplete, expiry and timeout events; marks the search state terminal;
    transitions the miner OUT of ACTIVE_HASHING/WAKING/EXHAUSTED_PENDING immediately (so energy
    stops using P_hash/P_wake and a lease that expires before wake never activates its miner);
    and advances the slice progress a generation — all-or-none.
    """
    prog = run_ctx.range_progress.get(lease.RangeSliceID)
    status, counter, miner_state = _TRIGGER_TERMINALISATION.get(
        trigger, ("REVOKED", "leases_revoked", "LOW_POWER_LISTEN"))
    now = run_ctx.event_queue.current_event_time
    lease.lease_status = status
    lease.reassignment_reason = trigger
    lease.disposition = Outcome("lease_terminalised", trigger=trigger, status=status)
    run_ctx.lease_stats[counter] += 1
    if trigger == "MINER_CANCELLED":
        run_ctx.lease_stats["miner_cancellations"] += 1
    elif trigger == "PROGRESS_TIMEOUT":
        run_ctx.lease_stats["progress_timeouts"] += 1
    wakes = _cancel_queued_hash_events(run_ctx, lease.MinerID)
    run_ctx.lease_stats["wakes_cancelled_with_lease"] += wakes
    _cancel_lease_deadlines(run_ctx, lease, prog)
    st = rc.search_states.get(lease.MinerID)
    if st is not None and not st.completed:
        st.completed = True
        st.completion_kind = status
    # S4B-1: idle/terminalise the MINER with the lease so no expired/timed-out/cancelled/failed
    # miner is ever left ACTIVE_HASHING or WAKING.
    m = run_ctx.miners.get(lease.MinerID)
    if m is not None and m.state in _LIVE_MINER_STATES and now is not None:
        run_ctx.apply_miner_state_transition(lease.MinerID, miner_state, now)
        run_ctx.lease_stats["miners_terminalised_with_lease"] += 1
    if prog is not None:
        prog.current_lease_id = None
        prog.progress_generation += 1
    return Outcome("lease_revoked", LeaseID=lease.LeaseID, trigger=trigger, status=status)


def _reassignment_already_exists(run_ctx: RunContext, req_id: Any,
                                 predecessor_lease_id: Any) -> Outcome:
    """S4B-6: the COMPLETE stored reassignment-replay result (exact stored request, statuses,
    EventRefs, successor lease and disposition) — replay creates no event/request/decision/lease
    and increments no lifecycle counter."""
    req = run_ctx.reassignment_requests.get(req_id)
    successor = run_ctx.range_leases.get(req.new_lease_id) if req is not None else None
    return Outcome("range_reassignment_already_exists",
                   RangeReassignmentRequestID=req_id, predecessor_lease_id=predecessor_lease_id,
                   request=req, status=(req.status if req is not None else None),
                   start_event_ref=(req.start_event_ref if req is not None else None),
                   complete_event_ref=(req.complete_event_ref if req is not None else None),
                   successor_lease=successor,
                   disposition=(req.disposition if req is not None else None))


def _reassign_payload(run_ctx: RunContext, rc: RoundContext, req: Any, predecessor_lease: Any,
                      chosen: Any) -> Dict[str, Any]:
    prog = run_ctx.range_progress.get(req.RangeSliceID)
    return {"RangeReassignmentRequestID": req.RangeReassignmentRequestID,
            "DecisionID": req.DecisionID, "predecessor_lease_id": predecessor_lease.LeaseID,
            "new_lease_id": req.new_lease_id, "RoundID_at_seat": rc.RoundID,
            "TemplateID_at_seat": rc.TemplateID_committed, "RangeSliceID": req.RangeSliceID,
            "old_MinerID": predecessor_lease.MinerID, "new_MinerID": chosen.MinerID,
            "predecessor_committed_frontier": req.predecessor_committed_frontier,
            "new_lease_generation": req.new_lease_generation,
            "expected_old_lease_status": "REASSIGNED", "expected_new_request_status": "SEATED",
            "expected_progress_generation": prog.progress_generation if prog else -1,
            "expected_round_state_version": rc.state_version}


def SeatRangeReassignmentTransaction(run_ctx: RunContext, rc: RoundContext, prog: Any,
                                     predecessor_lease: Any, chosen: Any,
                                     observation_time: float, reason: str) -> Optional[Outcome]:
    """S4-9/S4A-7/S4A-8: seat a reassignment ALL-OR-NONE (request + event + counters).

    S4A-8: replay is NATURAL — a second observation of the SAME terminal predecessor lease
    returns ``range_reassignment_already_exists`` with no second request, no manual generation
    rewind.  S4A-7: a failed seat rolls back completely (no orphan slice / observation / decision
    / link) and registers a FAILED request for audit.
    """
    cfg = run_ctx.config
    eq = run_ctx.event_queue
    now = eq.current_event_time
    slice_id = prog.RangeSliceID
    frontier = prog.committed_frontier
    # S4A-8/S4B-6: NATURAL replay — the predecessor lease is terminalised exactly once, so a
    # second observation of it re-derives the same reassignment (no generation-counter
    # dependence) and returns the COMPLETE stored result with no side effect.
    existing = run_ctx.reassignment_by_predecessor.get(predecessor_lease.LeaseID)
    if existing is not None:
        run_ctx.lease_diagnostics["reassignment_replay_count"] += 1   # S4C-6: state-pure
        return _reassignment_already_exists(run_ctx, existing, predecessor_lease.LeaseID)
    new_gen = run_ctx.lease_generation_of_slice.get(slice_id,
                                                    predecessor_lease.lease_generation) + 1
    new_lease_id = _mk_lease_id(rc.RoundID, rc.TemplateID_committed, slice_id, new_gen)
    req_id = _mk_reassign_id(rc.RoundID, rc.TemplateID_committed, slice_id,
                             predecessor_lease.LeaseID, frontier, chosen.MinerID, new_gen)
    if req_id in run_ctx.reassignment_requests:              # defensive exact-id replay guard
        run_ctx.lease_diagnostics["reassignment_replay_count"] += 1   # S4C-6: state-pure
        return _reassignment_already_exists(run_ctx, req_id, predecessor_lease.LeaseID)
    result = "REASSIGNMENT_PENDING_WAKE" if chosen.needs_stage3_wake else "REASSIGNMENT_SEATED"
    projected_start = now + (cfg.security_floor.activation_wake_latency
                             if chosen.needs_stage3_wake else cfg.range_lease.reassignment_wake_latency)
    dec = _record_reassignment_decision(run_ctx, rc, predecessor_lease, chosen, result,
                                        new_gen=new_gen, projected_start=projected_start)
    # S4C-1: snapshot the predecessor's residency AT REVOCATION (its ACTIVE_HASHING is finalised by
    # the revoke idle transition) and the reassignee's standby residency AT SEATING, so every
    # per-request energy component is later charged over EXACTLY its own [start, end] interval.
    pm = run_ctx.miners.get(predecessor_lease.MinerID)
    cm = run_ctx.miners.get(chosen.MinerID)
    req = RangeReassignmentRequest(
        RangeReassignmentRequestID=req_id, DecisionID=dec.DecisionID, RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed, RangeSliceID=slice_id,
        predecessor_lease_id=predecessor_lease.LeaseID, predecessor_committed_frontier=frontier,
        new_MinerID=chosen.MinerID, new_lease_generation=new_gen, new_lease_id=new_lease_id,
        needs_stage3_wake=chosen.needs_stage3_wake, status="SEATED", seated_at=now,
        predecessor_MinerID=predecessor_lease.MinerID,
        revocation_time=now,
        predecessor_active_residency_at_revocation=_residency(pm, "ACTIVE_HASHING", now),
        predecessor_low_residency_at_revocation=_residency(pm, "LOW_POWER_LISTEN", now),
        predecessor_offline_residency_at_revocation=_residency(pm, "OFFLINE", now),
        reassignee_reserve_residency_at_seat=_residency(cm, "RESERVE", now),
        reassignee_low_residency_at_seat=_residency(cm, "LOW_POWER_LISTEN", now),
        reassignee_offline_residency_at_seat=_residency(cm, "OFFLINE", now))
    def _rollback_seat(reason: Any) -> Optional[Outcome]:
        # S4-9: a failed seat leaves a coherent state — the (revoked) predecessor is NOT
        # promoted to REASSIGNED, the FAILED request is registered for audit, the slice is
        # marked UNASSIGNED_PENDING_RETRY, and the slice generation is advanced so a later
        # retry mints a fresh request identity.
        run_ctx.lease_stats["reassignment_seat_rollback_count"] += 1
        run_ctx.lease_stats["reassignment_requests_failed"] += 1
        req.status = "FAILED"
        _stamp_request_terminal(run_ctx, req, now)          # S4C-1 close predecessor/standby
        req.disposition = Outcome("reassignment_seat_failed", reason=reason)
        prog.terminal_status = "UNASSIGNED_PENDING_RETRY"
        run_ctx.reassignment_requests[req_id] = req
        run_ctx.lease_generation_of_slice[slice_id] = new_gen
        return _apply_no_eligible_policy(run_ctx, rc, prog)

    if chosen.needs_stage3_wake:
        ok = _seat_reserve_reassignment_wake(run_ctx, rc, prog, req, chosen)
        if not ok:
            return _rollback_seat("reserve_wake_failed")
    else:
        payload = _reassign_payload(run_ctx, rc, req, predecessor_lease, chosen)
        if getattr(run_ctx, "force_reassignment_seat_failure", False):   # S4-15 injection
            r = Outcome("rejected_forced_reassignment_seat_failure")
        else:
            r = ScheduleEvent(eq, rc, "RangeReassignmentStartEvent", now,
                              "RANGE_REASSIGNMENT_START", payload, ordinary_dispatch_origin(eq))
        if r.kind != "scheduled":
            return _rollback_seat(r)
        req.start_event_ref = r.event_ref
    # COMMIT.
    predecessor_lease.lease_status = "REASSIGNED"
    run_ctx.lease_stats["leases_reassigned"] += 1
    run_ctx.reassignment_requests[req_id] = req
    run_ctx.reassignment_by_predecessor[predecessor_lease.LeaseID] = req_id   # S4A-8 natural replay
    run_ctx.reassignments_per_slice[slice_id] = \
        run_ctx.reassignments_per_slice.get(slice_id, 0) + 1
    run_ctx.lease_generation_of_slice[slice_id] = new_gen
    run_ctx.lease_stats["reassignment_requests_seated"] += 1
    return None


def _obj_activation_id(x: Any) -> Any:
    """S4B-4: the activation lifecycle id of either a reserve-DOMAIN RangeSlice or a NON-domain
    ReassignmentWakeHandle."""
    return x.WakeHandleID if isinstance(x, ReassignmentWakeHandle) else x.RangeSliceID


def _seat_reserve_reassignment_wake(run_ctx: RunContext, rc: RoundContext, prog: Any,
                                    req: Any, chosen: Any) -> bool:
    """S4B-4/S4B-5 Path B: wake a reserve reassignee via the ACCEPTED Stage-3 activation lifecycle
    using a NON-domain ``ReassignmentWakeHandle`` — NOT a RangeSlice.

    The wake handle carries NO nonce interval; the ORIGINAL ``RangeProgress`` remains the sole
    interval authority and the successor lease binds to it.  The activation is scoped
    ``REASSIGNMENT_WAKE_ONLY`` and references the OriginalRangeSliceID / RangeReassignmentRequestID
    / WakeHandleID.  It is registered ONLY in ``reassignment_wake_handles`` (never in
    ``reserve_slice_by_id`` / ``reserve_slices`` / any nonce-domain registry).  The whole wake is
    transactional — a failed activation seat rolls back the wake handle, the synthetic observation
    / decision and every link, leaving NO orphan.
    """
    slice_id = prog.RangeSliceID
    frontier = prog.committed_frontier
    rr = run_ctx.reserve_records.get((rc.RoundID, chosen.MinerID))
    if rr is None:
        return False
    assert prog.range_start <= frontier < prog.range_end, "reassignment suffix out of range"
    wake_handle_id = f"WH-{slice_id}-{req.new_lease_generation}"
    wake_handle = ReassignmentWakeHandle(
        WakeHandleID=wake_handle_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        OriginalRangeSliceID=slice_id, RangeReassignmentRequestID=req.RangeReassignmentRequestID,
        MinerID=chosen.MinerID, generation=req.new_lease_generation, status="UNCLAIMED")
    req.wake_handle_id = wake_handle_id
    # snapshot the pre-state so a failed activation seat rolls back to EXACTLY it (no orphans).
    obs_len = len(run_ctx.security_observations)
    dec_len = len(run_ctx.activation_decisions)

    def _rollback_wake() -> bool:
        del run_ctx.security_observations[obs_len:]
        del run_ctx.activation_decisions[dec_len:]
        run_ctx.reassignment_wake_handles.pop(wake_handle_id, None)
        run_ctx.reassign_by_suffix_slice.pop(wake_handle_id, None)
        req.wake_handle_id = None
        run_ctx.lease_stats["pathb_rollback_count"] += 1
        return False

    # register the wake handle ONLY as a wake handle (a NON-domain lifecycle token).
    run_ctx.reassignment_wake_handles[wake_handle_id] = wake_handle
    run_ctx.lease_stats["wake_handles_created"] += 1
    run_ctx.observation_seq += 1
    obs = SecurityFloorObservation(
        ObservationID=(run_ctx.RunID, "ROBS", run_ctx.observation_seq), RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed,
        observation_time=run_ctx.event_queue.current_event_time,
        observation_reason="range_reassignment_reserve_wake", effective_active_hash_rate=0.0,
        active_miner_count=0, minimum_required_hash_rate=0.0, minimum_required_miner_count=None,
        hash_rate_deficit=0.0, miner_count_deficit=0, breached=False)
    run_ctx.security_observations.append(obs)
    s3dec = ReserveActivationDecision(
        DecisionID=(run_ctx.RunID, "RDEC3", run_ctx.observation_seq),
        ObservationID=obs.ObservationID, selected_miners=[chosen.MinerID],
        selected_slices=[wake_handle_id], projected_hash_rate_after_wake=chosen.hash_rate,
        residual_deficit=0.0, policy_result="ACTIVATION_SEATED")
    run_ctx.activation_decisions.append(s3dec)
    obs.activation_decision_id = s3dec.DecisionID
    run_ctx.reassign_by_suffix_slice[wake_handle_id] = (req.RangeReassignmentRequestID, slice_id)
    act_req = SeatReserveActivationTransaction(
        run_ctx, rc, rr, wake_handle, obs, s3dec.DecisionID,
        activation_scope="REASSIGNMENT_WAKE_ONLY",
        range_reassignment_request_id=req.RangeReassignmentRequestID,
        wake_handle_id=wake_handle_id, original_range_slice_id=slice_id)   # S4C-4 explicit identity
    if not isinstance(act_req, ReserveActivationRequest):
        return _rollback_wake()
    req.reserve_activation_request_id = act_req.ReserveActivationRequestID
    return True


def _verify_reassignment_identity(run_ctx: RunContext, rc: RoundContext,
                                  payload: Dict[str, Any], lifecycle: str) -> Any:
    """S4-8: verify the complete predecessor/successor identity BEFORE any domain mutation."""
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("reassign_no_effect", reason="round_terminal")
    if payload["RoundID_at_seat"] != rc.RoundID:
        return Outcome("reassign_no_effect", reason="round_mismatch")
    if payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("reassign_no_effect", reason="template_mismatch")
    req = run_ctx.reassignment_requests.get(payload["RangeReassignmentRequestID"])
    if req is None:
        return Outcome("reassign_no_effect", reason="unknown_request")
    if req.status != payload["expected_new_request_status"]:
        return Outcome("reassign_no_effect", reason="request_lifecycle_mismatch",
                       actual=req.status)
    if req.RangeSliceID != payload["RangeSliceID"] or req.new_MinerID != payload["new_MinerID"] \
            or req.new_lease_generation != payload["new_lease_generation"] \
            or req.predecessor_lease_id != payload["predecessor_lease_id"] \
            or req.DecisionID != payload["DecisionID"]:
        return Outcome("reassign_no_effect", reason="request_identity_mismatch")
    pred = run_ctx.range_leases.get(payload["predecessor_lease_id"])
    if pred is None or pred.lease_status not in TERMINAL_LEASE_STATUSES:
        return Outcome("reassign_no_effect", reason="predecessor_not_terminal")
    if pred.lease_status != payload["expected_old_lease_status"]:
        return Outcome("reassign_no_effect", reason="old_lease_status_mismatch")
    prog = run_ctx.range_progress.get(payload["RangeSliceID"])
    if prog is None:
        return Outcome("reassign_no_effect", reason="no_progress")
    if prog.progress_generation != payload["expected_progress_generation"]:
        return Outcome("reassign_no_effect", reason="progress_generation_mismatch")
    if prog.committed_frontier != payload["predecessor_committed_frontier"]:
        return Outcome("reassign_no_effect", reason="frontier_changed")
    if payload["expected_round_state_version"] != rc.state_version:
        return Outcome("reassign_no_effect", reason="round_state_version_mismatch")
    cur = getattr(run_ctx.event_queue, "current_event_ref", None)
    recorded = req.start_event_ref if lifecycle == "START" else req.complete_event_ref
    if recorded is not None and cur is not None and cur != recorded:
        return Outcome("reassign_no_effect", reason="event_ref_mismatch")
    return Outcome("reassign_identity_ok", request=req, predecessor=pred, progress=prog)


def _handle_range_reassignment_start(run_ctx: RunContext, payload: Dict[str, Any],
                                     envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    guard = _verify_reassignment_identity(run_ctx, rc, payload, "START")
    if guard.kind != "reassign_identity_ok":
        return Outcome("range_reassignment_start_no_effect", reason=guard)
    req = guard.request
    prog = guard.progress
    mid = payload["new_MinerID"]
    eq = run_ctx.event_queue
    t = eq.current_event_time
    # S4A-9/S4B-7: snapshot the pre-wake cumulative WAKING + standby residency so the reassignment
    # wake interval (and the reassignee's standby-before-wake) is attributed EXACTLY.
    m = run_ctx.miners.get(mid)
    req.wake_residency_at_start = _residency(m, "WAKING", t)
    req.reassignee_reserve_residency_at_wake_start = _residency(m, "RESERVE", t)   # S4C-1
    req.reassignee_low_residency_at_wake_start = _residency(m, "LOW_POWER_LISTEN", t)
    req.reassignee_offline_residency_at_wake_start = _residency(m, "OFFLINE", t)
    run_ctx.apply_miner_state_transition(mid, "WAKING", t)
    req.status = "STARTED"
    req.started_at = t
    complete_time = t + run_ctx.config.range_lease.reassignment_wake_latency
    # S5B-4: the Path-A reassignment wake is a REAL wake lifecycle — consult the delayed-wake
    # policy here too, keyed on the reassignment request's own identity.
    complete_time += _adv.wake_extra_latency(
        run_ctx, rc, mid, complete_time, t,
        request_id=("PATH_A_REASSIGNMENT", req.RangeReassignmentRequestID,
                    req.new_lease_generation),
        lifecycle="PATH_A_REASSIGNMENT_WAKE")
    cpayload = dict(payload)
    cpayload["expected_new_request_status"] = "STARTED"
    cpayload["expected_round_state_version"] = rc.state_version
    cpayload["expected_progress_generation"] = prog.progress_generation
    if getattr(run_ctx, "force_reassignment_complete_seat_failure", False):   # S4-15 injection
        r = Outcome("rejected_forced_reassignment_complete_seat_failure")
    else:
        r = ScheduleEvent(eq, rc, "RangeReassignmentCompleteEvent", complete_time,
                          "RANGE_REASSIGNMENT_COMPLETE", cpayload, ordinary_dispatch_origin(eq))
    if r.kind != "scheduled":
        # S4-9: never strand the reassignee WAKING without a controller.
        run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)
        req.status = "FAILED"
        _rm = run_ctx.miners.get(mid)                       # S4C-1: close the failed wake interval
        if _rm is not None and req.wake_residency_at_start is not None:
            req.wake_residency_at_end = _residency(_rm, "WAKING", t)
        _stamp_request_terminal(run_ctx, req, t)            # S4C-1 close predecessor interval
        req.disposition = Outcome("reassignment_complete_seat_failed", reason=r)
        prog.terminal_status = "UNASSIGNED_PENDING_RETRY"
        run_ctx.lease_stats["reassignment_requests_failed"] += 1
        dec = _apply_no_eligible_policy(run_ctx, rc, prog)
        if isinstance(dec, Outcome):
            return dec
        return Outcome("range_reassignment_start_complete_seat_failed", MinerID=mid, reason=r)
    req.complete_event_ref = r.event_ref
    return Outcome("range_reassignment_started", MinerID=mid, complete_event_ref=r.event_ref)


def _handle_range_reassignment_complete(run_ctx: RunContext, payload: Dict[str, Any],
                                        envelope: Dict[str, Any]) -> Outcome:
    rc = run_ctx.current_round_context
    guard = _verify_reassignment_identity(run_ctx, rc, payload, "COMPLETE")
    if guard.kind != "reassign_identity_ok":
        return Outcome("range_reassignment_complete_no_effect", reason=guard)
    req = guard.request
    prog = guard.progress
    mid = payload["new_MinerID"]
    cfg = run_ctx.config
    t = run_ctx.event_queue.current_event_time
    old_st = rc.search_states.get(mid)
    rate = old_st.hash_rate if old_st is not None else cfg.base_hash_rate
    okind = run_ctx.search_assignment_kind.get((rc.RoundID, mid), PRIMARY_ASSIGNMENT)
    kind = REASSIGNED_RESERVE_WORK if okind in (ACTIVATED_RESERVE_ASSIGNMENT,
                                                REASSIGNED_RESERVE_WORK) else REASSIGNED_PRIMARY_WORK
    run_ctx.apply_miner_state_transition(mid, "ACTIVE_HASHING", t)
    _bind_reassigned_lease(run_ctx, rc, mid, prog, req.new_lease_id, req.new_lease_generation,
                           f"RA-{req.RangeSliceID}-{req.new_lease_generation}",
                           req.predecessor_lease_id, kind, rate, t)
    req.status = "COMPLETED"
    req.completed_at = t
    # S4A-9: the reassignee's reassigned ACTIVE_HASHING interval begins now (energy attribution);
    # snapshot its pre-reassignment cumulative ACTIVE_HASHING (and finalised WAKING) so the
    # wake/active intervals are attributed EXACTLY.
    req.reassigned_search_start_time = t
    _m = run_ctx.miners.get(mid)
    req.wake_residency_at_end = _m.duration.get("WAKING", 0.0) if _m is not None else None
    req.active_residency_at_search_start = _m.duration.get("ACTIVE_HASHING", 0.0) \
        if _m is not None else 0.0
    req.disposition = Outcome("reassignment_completed")
    run_ctx.lease_stats["reassignment_requests_completed"] += 1
    lat = t - req.seated_at
    run_ctx.lease_stats["total_reassignment_latency"] += lat
    if lat > run_ctx.lease_stats["maximum_reassignment_latency"]:
        run_ctx.lease_stats["maximum_reassignment_latency"] = lat
    return Outcome("range_reassignment_completed", MinerID=mid, ReassignedSlice=req.RangeSliceID)


def _bind_reassigned_lease(run_ctx: RunContext, rc: RoundContext, mid: Any, prog: Any,
                           new_lid: Any, new_gen: int, aid: str, pred_lease_id: Any,
                           kind: str, rate: float, t: float) -> None:
    cfg = run_ctx.config
    version = 1
    # S5-5: the successor lease restarts from the ACCEPTED committed frontier.  A progress
    # withholder's under-report (if the modeled audit misses it) lowers that accepted frontier
    # below what it actually searched, so the successor must re-evaluate the difference — real
    # duplicated physical work, recorded explicitly rather than hidden.
    accepted_start = _adv.apply_progress_withholding(run_ctx, rc, prog, pred_lease_id, t)
    # S5A-1: the successor resumes from the ACCEPTED frontier, which for an undetected
    # under-report is BELOW the physical committed frontier.  The physical frontier itself is
    # untouched — the difference is explicitly counted re-evaluation, not rewound coverage.
    start_nonce = accepted_start if accepted_start is not None else prog.committed_frontier
    _adv.note_reassignment_reeval(run_ctx, rc, prog.RangeSliceID, start_nonce,
                                  run_ctx.adv_actual_frontier.get(prog.RangeSliceID,
                                                                  prog.committed_frontier))
    st = MinerSearchState(MinerID=mid, AssignmentID=aid, assignment_version=version,
                          hash_rate=rate, range_start=start_nonce,
                          range_end=prog.range_end, active_power=cfg.P_hash,
                          idle_power=cfg.P_listen)
    st.active_start = t
    rc.search_states[mid] = st
    rc.assignments[aid] = {"MinerID": mid, "AssignmentID": aid, "assignment_version": version,
                           "range": (start_nonce, prog.range_end),
                           "RoundID": rc.RoundID, "TemplateID": rc.TemplateID_committed,
                           "coverage_state": "OPEN"}
    run_ctx.search_assignment_kind[(rc.RoundID, mid)] = kind
    run_ctx.slice_of_miner[(rc.RoundID, mid)] = prog.RangeSliceID
    lease = RangeLease(
        LeaseID=new_lid, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        RangeSliceID=prog.RangeSliceID, lease_generation=new_gen, AssignmentID=aid,
        assignment_version=version, MinerID=mid, assignment_kind=kind,
        lease_start_nonce=start_nonce, lease_end_nonce=prog.range_end,
        committed_cursor=start_nonce, lease_start_time=t,
        lease_expiry_time=t + cfg.range_lease.lease_duration, lease_status="ACTIVE",
        predecessor_lease_id=pred_lease_id)
    run_ctx.range_leases[new_lid] = lease
    _stamp_lease_start_residency(run_ctx, lease, t)         # S4C-1
    prog.current_lease_id = new_lid
    prog.progress_generation += 1
    prog.terminal_status = "OPEN"
    prog.last_progress_time = t
    run_ctx.lease_stats["leases_created"] += 1
    # S4A-1/S4A-2: arm the successor lease's expiry + progress-timeout deadlines.
    _seat_lease_expiry(run_ctx, rc, lease, prog, t)
    _refresh_progress_timeout(run_ctx, rc, prog, lease, t)
    r = _seat_hash_work(run_ctx, rc, st, at_time=t)
    if r.kind == "scheduled":
        run_ctx.round_first_completion[(rc.RoundID, mid)] = r.event_ref.event_time


def _bind_reserve_reassignment_if_any(run_ctx: RunContext, rc: RoundContext, mid: Any,
                                      sl: Any, t: float, st: Any = None) -> None:
    """S4B-4 Path B: when the woken reserve is a reassignment wake handle, bind the reassigned
    lease on the ORIGINAL RangeProgress and complete the reassignment request."""
    link = run_ctx.reassign_by_suffix_slice.get(_obj_activation_id(sl))
    if link is None:
        return
    req_id, orig_slice_id = link
    req = run_ctx.reassignment_requests.get(req_id)
    prog = run_ctx.range_progress.get(orig_slice_id)
    if req is None or prog is None:
        return
    new_lid = req.new_lease_id
    # S5B-3: Path B consults the SAME accepted-frontier authority as Path A.  An undetected
    # under-report lowers only the ACCEPTED frontier the reserve reassignee resumes from; the
    # ORIGINAL RangeProgress stays authoritative and its physical frontier never rewinds.
    _accepted = _adv.apply_progress_withholding(run_ctx, rc, prog, req.predecessor_lease_id, t)
    start_nonce = _accepted if _accepted is not None else prog.committed_frontier
    _adv.note_reassignment_reeval(run_ctx, rc, orig_slice_id, start_nonce,
                                  run_ctx.adv_actual_frontier.get(orig_slice_id,
                                                                  prog.committed_frontier))
    lease = RangeLease(
        LeaseID=new_lid, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        RangeSliceID=orig_slice_id, lease_generation=req.new_lease_generation,
        AssignmentID=f"AR-{rc.RoundID}-{mid}", assignment_version=1, MinerID=mid,
        assignment_kind=REASSIGNED_RESERVE_WORK, lease_start_nonce=start_nonce,
        lease_end_nonce=prog.range_end, committed_cursor=start_nonce,
        lease_start_time=t, lease_expiry_time=t + run_ctx.config.range_lease.lease_duration,
        lease_status="ACTIVE", predecessor_lease_id=req.predecessor_lease_id,
        reserve_activation_request_id=req.reserve_activation_request_id)
    run_ctx.range_leases[new_lid] = lease
    _stamp_lease_start_residency(run_ctx, lease, t)         # S4C-1
    prog.current_lease_id = new_lid
    prog.progress_generation += 1
    prog.terminal_status = "OPEN"
    prog.last_progress_time = t
    run_ctx.slice_of_miner[(rc.RoundID, mid)] = orig_slice_id
    run_ctx.search_assignment_kind[(rc.RoundID, mid)] = REASSIGNED_RESERVE_WORK
    # S5B-3: the reserve reassignee physically resumes from the ACCEPTED frontier (which may be
    # below the untouched physical frontier), so its search state and assignment record must
    # describe the range it actually works.
    if st is not None and start_nonce != st.range_start:
        st.range_start = start_nonce
        st.cursor = start_nonce
        a = rc.assignments.get(st.AssignmentID)
        if a is not None:
            a["range"] = (start_nonce, prog.range_end)
    run_ctx.lease_stats["leases_created"] += 1
    # S4A-1/S4A-2: arm the reassigned lease's expiry + progress-timeout deadlines.
    _seat_lease_expiry(run_ctx, rc, lease, prog, t)
    _refresh_progress_timeout(run_ctx, rc, prog, lease, t)
    req.status = "COMPLETED"
    req.completed_at = t
    # S4A-9: the reassignee's reassigned ACTIVE_HASHING interval begins now (energy attribution);
    # snapshot its pre-reassignment cumulative ACTIVE_HASHING (and finalised WAKING) so the
    # wake/active intervals are attributed EXACTLY.
    req.reassigned_search_start_time = t
    _m = run_ctx.miners.get(mid)
    req.wake_residency_at_end = _m.duration.get("WAKING", 0.0) if _m is not None else None
    req.active_residency_at_search_start = _m.duration.get("ACTIVE_HASHING", 0.0) \
        if _m is not None else 0.0
    req.complete_event_ref = getattr(run_ctx.event_queue, "current_event_ref", None)
    req.disposition = Outcome("reassignment_completed_via_reserve_wake")
    run_ctx.lease_stats["reassignment_requests_completed"] += 1
    lat = t - req.seated_at
    run_ctx.lease_stats["total_reassignment_latency"] += lat
    if lat > run_ctx.lease_stats["maximum_reassignment_latency"]:
        run_ctx.lease_stats["maximum_reassignment_latency"] = lat


def _handle_range_reassignment_retry(run_ctx: RunContext, payload: Dict[str, Any],
                                     envelope: Dict[str, Any]) -> Outcome:
    """S4-11 WAIT_FOR_ELIGIBLE_MINER: one bounded, idempotent retry (never spins in place)."""
    rc = run_ctx.current_round_context
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("range_reassignment_retry_no_effect", reason="round_terminal")
    if payload["RoundID_at_seat"] != rc.RoundID:
        return Outcome("range_reassignment_retry_no_effect", reason="round_mismatch")
    slice_id = payload["RangeSliceID"]
    prog = run_ctx.range_progress.get(slice_id)
    if prog is None or prog.current_lease_id is not None \
            or prog.committed_frontier >= prog.range_end:
        return Outcome("range_reassignment_retry_no_effect", reason="nothing_to_retry")
    pred = run_ctx.range_leases.get(payload["predecessor_lease_id"])
    if pred is None:
        return Outcome("range_reassignment_retry_no_effect", reason="unknown_predecessor")
    t = run_ctx.event_queue.current_event_time
    cands = _eligible_reassignment_candidates(run_ctx, rc, slice_id, pred.MinerID,
                                              prog.committed_frontier, t)
    chosen = select_reassignment_candidate(cands)
    if chosen is None:
        return _apply_no_eligible_policy(run_ctx, rc, prog, retrying=True)
    return SeatRangeReassignmentTransaction(run_ctx, rc, prog, pred, chosen, t, "retry")


def _apply_no_eligible_policy(run_ctx: RunContext, rc: RoundContext, prog: Any,
                              retrying: bool = False) -> Optional[Outcome]:
    """S4-11: the configured no-eligible-miner / seat-failure policy for an unfinished suffix."""
    policy = run_ctx.config.range_lease.no_eligible_miner_policy
    if policy == "ABORT_ROUND":
        return RoundAbort(run_ctx, rc, reason="range_reassignment_unavailable", envelope={})
    if policy == "WAIT_FOR_ELIGIBLE_MINER" and not retrying:
        eq = run_ctx.event_queue
        slice_id = prog.RangeSliceID
        n = run_ctx.reassignment_retry_seq.get(slice_id, 0) + 1
        run_ctx.reassignment_retry_seq[slice_id] = n
        if n <= 3:                                          # bounded retry (never spins)
            target = next_representable_simulation_time(
                eq.current_event_time + run_ctx.config.range_lease.reassignment_wake_latency)
            pred_id = run_ctx.range_leases and None
            # find the predecessor lease id from the last decision for this slice.
            pred_id = next((d.predecessor_lease_id for d in reversed(run_ctx.reassignment_decisions)
                            if d.RangeSliceID == slice_id), None)
            if target <= run_ctx.run_horizon_T and pred_id is not None:
                ScheduleEvent(eq, rc, "RangeReassignmentRetryEvent", target,
                              "RANGE_REASSIGNMENT_RETRY",
                              {"RangeSliceID": slice_id, "RoundID_at_seat": rc.RoundID,
                               "TemplateID_at_seat": rc.TemplateID_committed,
                               "predecessor_lease_id": pred_id, "retry_seq": n},
                              ordinary_dispatch_origin(eq))
                return None
    # CONTINUE_WITH_UNASSIGNED_RANGE: preserve the exact frontier; the uncovered suffix is
    # reported at round closure (it is NEVER labelled full-domain exhaustion).
    return None


def _handle_miner_failure(run_ctx: RunContext, payload: Dict[str, Any],
                          envelope: Dict[str, Any]) -> Outcome:
    """S4-4: an injected miner FAILURE (involuntary) revokes the current lease and reassigns.

    A failure is an involuntary fault: the miner goes OFFLINE and its lease terminalises REVOKED
    — DISTINCT from a voluntary MINER_CANCELLED (LOW_POWER_LISTEN / CANCELLED).
    """
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("miner_failure_no_effect", reason="round_terminal", MinerID=mid)
    if payload["RoundID_at_seat"] != rc.RoundID \
            or payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("miner_failure_no_effect", reason="stale", MinerID=mid)
    lease = _current_lease_for_miner(run_ctx, rc, mid)
    if lease is None:
        return Outcome("miner_failure_no_effect", reason="no_active_lease", MinerID=mid)
    t = run_ctx.event_queue.current_event_time
    if run_ctx.miners.get(mid) is not None:                 # MINER_FAILED -> OFFLINE
        run_ctx.apply_miner_state_transition(mid, "OFFLINE", t)
    dec = EvaluateRangeLease(run_ctx, rc, lease.LeaseID, t, "MINER_FAILED",
                             triggering_event_ref=run_ctx.event_queue.current_event_ref,
                             observation_reason=payload["fault_reason"])
    if isinstance(dec, Outcome):
        return dec
    return Outcome("miner_failed_lease_revoked", MinerID=mid, LeaseID=lease.LeaseID)


def _handle_miner_cancelled(run_ctx: RunContext, payload: Dict[str, Any],
                            envelope: Dict[str, Any]) -> Outcome:
    """S4A-3: a miner VOLUNTARILY cancels its lease — a disposition DISTINCT from a failure.

    The miner withdraws to LOW_POWER_LISTEN (it is NOT OFFLINE) and its lease terminalises
    CANCELLED (not REVOKED); the unfinished suffix is still handed to reassignment.
    """
    rc = run_ctx.current_round_context
    mid = payload["MinerID"]
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("miner_cancelled_no_effect", reason="round_terminal", MinerID=mid)
    if payload["RoundID_at_seat"] != rc.RoundID \
            or payload["TemplateID_at_seat"] != rc.TemplateID_committed:
        return Outcome("miner_cancelled_no_effect", reason="stale", MinerID=mid)
    lease = _current_lease_for_miner(run_ctx, rc, mid)
    if lease is None:
        return Outcome("miner_cancelled_no_effect", reason="no_active_lease", MinerID=mid)
    t = run_ctx.event_queue.current_event_time
    m = run_ctx.miners.get(mid)
    if m is not None and m.state in ("ACTIVE_HASHING", "WAKING", "EXHAUSTED_PENDING"):
        run_ctx.apply_miner_state_transition(mid, "LOW_POWER_LISTEN", t)   # voluntary withdrawal
    dec = EvaluateRangeLease(run_ctx, rc, lease.LeaseID, t, "MINER_CANCELLED",
                             triggering_event_ref=run_ctx.event_queue.current_event_ref,
                             observation_reason=payload["cancellation_reason"])
    term = _maybe_terminate_no_block(run_ctx, rc)
    if term is not None:
        return term
    if isinstance(dec, Outcome):
        return dec
    return Outcome("miner_cancelled_lease_terminalised", MinerID=mid, LeaseID=lease.LeaseID)


_MISSING = object()
_DEADLINE_REQUIRED = ("LeaseID", "MinerID", "RangeSliceID", "lease_generation",
                      "expected_lease_status", "expected_progress_generation",
                      "expected_committed_frontier", "expected_round_state_version",
                      "RoundID_at_seat", "TemplateID_at_seat")


def _verify_deadline_identity(run_ctx: RunContext, rc: RoundContext, payload: Dict[str, Any],
                              is_timeout: bool) -> Any:
    """S4C-5: TOTAL, SAFE verification of EVERY declared deadline-payload field before any effect.

    Both RangeLeaseExpiryEvent and RangeProgressTimeoutEvent payloads MUST explicitly carry
    LeaseID, MinerID, RangeSliceID, lease_generation, expected_lease_status,
    expected_progress_generation, expected_committed_frontier, expected_round_state_version,
    RoundID_at_seat, TemplateID_at_seat (+ timeout_generation for a timeout).  A MISSING declared
    field is treated as tampered identity (no default is substituted for expected_lease_status).
    Every field is read with safe extraction (no KeyError) and any missing / mismatched field —
    or a current EventRef that is not the lease's / progress's currently-armed deadline ref —
    performs NO effect.  Returns ``(lease, prog)`` only when EVERY check passes, else ``None``.
    """
    required = _DEADLINE_REQUIRED + (("timeout_generation",) if is_timeout else ())
    for k in required:                                     # a missing declared field is tampered
        if payload.get(k, _MISSING) is _MISSING:
            return None
    lease = run_ctx.range_leases.get(payload.get("LeaseID"))
    prog = run_ctx.range_progress.get(payload.get("RangeSliceID"))
    if lease is None or prog is None:
        return None
    cur_ref = getattr(run_ctx.event_queue, "current_event_ref", None)
    stored_ref = prog.timeout_event_ref if is_timeout else lease.expiry_event_ref
    if payload.get("RoundID_at_seat") != rc.RoundID \
            or payload.get("TemplateID_at_seat") != rc.TemplateID_committed \
            or lease.RangeSliceID != payload.get("RangeSliceID") \
            or lease.MinerID != payload.get("MinerID") \
            or lease.lease_generation != payload.get("lease_generation") \
            or lease.lease_status != payload.get("expected_lease_status") \
            or lease.lease_status != "ACTIVE" \
            or prog.current_lease_id != lease.LeaseID \
            or prog.progress_generation != payload.get("expected_progress_generation") \
            or prog.committed_frontier != payload.get("expected_committed_frontier") \
            or rc.state_version != payload.get("expected_round_state_version"):
        return None
    if is_timeout and prog.timeout_generation != payload.get("timeout_generation"):
        return None
    # S4C-5: the firing event must be the lease's / progress's CURRENTLY-armed deadline ref.
    if stored_ref is not None and cur_ref is not None and cur_ref != stored_ref:
        return None
    return (lease, prog)


def _handle_range_lease_expiry(run_ctx: RunContext, payload: Dict[str, Any],
                               envelope: Dict[str, Any]) -> Outcome:
    """S4A-1/S4B-8: an ACTIVE lease's expiry deadline fires — terminalise EXPIRED + reassign.

    Stale-safe: EVERY declared payload field is verified; a superseded / tampered deadline
    performs NO effect.  Work committing exactly AT the deadline commits first (HASH_WORK
    microphase precedes RANGE_LEASE_EXPIRY), so a range finished at the deadline is COMPLETED,
    not spuriously expired; the miner is idled by the terminalisation.
    """
    rc = run_ctx.current_round_context
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("range_lease_expiry_no_effect", reason="round_terminal")
    verified = _verify_deadline_identity(run_ctx, rc, payload, is_timeout=False)
    if verified is None:
        run_ctx.lease_stats["stale_expiry_events"] += 1
        return Outcome("range_deadline_no_effect", reason="missing_or_tampered_identity",
                       deadline="RangeLeaseExpiryEvent")
    lid = payload["LeaseID"]
    t = run_ctx.event_queue.current_event_time
    dec = EvaluateRangeLease(run_ctx, rc, lid, t, "LEASE_TIME_EXPIRED",
                             triggering_event_ref=run_ctx.event_queue.current_event_ref)
    # S4B-1/S4B-5: if the expiry idled the last live miner with no reassignment in flight, close
    # the round now rather than hang to the horizon.
    term = _maybe_terminate_no_block(run_ctx, rc)
    if term is not None:
        return term
    if isinstance(dec, Outcome):
        return dec
    return Outcome("range_lease_expired", LeaseID=lid)


def _handle_range_progress_timeout(run_ctx: RunContext, payload: Dict[str, Any],
                                   envelope: Dict[str, Any]) -> Outcome:
    """S4A-2/S4B-8: a slice's progress-timeout deadline fires — terminalise EXPIRED + reassign.

    Stale-safe: EVERY declared payload field (including ``timeout_generation``) is verified; a
    deadline superseded by a later causal frontier advance or a superseded lease performs NO
    effect.
    """
    rc = run_ctx.current_round_context
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return Outcome("range_progress_timeout_no_effect", reason="round_terminal")
    verified = _verify_deadline_identity(run_ctx, rc, payload, is_timeout=True)
    if verified is None:
        run_ctx.lease_stats["stale_timeout_events"] += 1
        return Outcome("range_deadline_no_effect", reason="missing_or_tampered_identity",
                       deadline="RangeProgressTimeoutEvent")
    lid = payload["LeaseID"]
    t = run_ctx.event_queue.current_event_time
    dec = EvaluateRangeLease(run_ctx, rc, lid, t, "PROGRESS_TIMEOUT",
                             triggering_event_ref=run_ctx.event_queue.current_event_ref)
    term = _maybe_terminate_no_block(run_ctx, rc)
    if term is not None:
        return term
    if isinstance(dec, Outcome):
        return dec
    return Outcome("range_progress_timed_out", LeaseID=lid)


def _close_lease_state(run_ctx: RunContext, rc: RoundContext, t: float) -> None:
    """S4-12/S4A-9: terminalise every lease + reassignment request; report unfinished suffixes;
    close any still-open reassignment ACTIVE_HASHING interval; and audit slice disjointness."""
    for lease in run_ctx.range_leases.values():
        if lease.RoundID != rc.RoundID:
            continue
        if lease.lease_status not in TERMINAL_LEASE_STATUSES:
            prog = run_ctx.range_progress.get(lease.RangeSliceID)
            if prog is not None and prog.committed_frontier >= prog.range_end:
                lease.lease_status = "COMPLETED"
                run_ctx.lease_stats["leases_completed"] += 1
            else:
                lease.lease_status = "CANCELLED"
                run_ctx.lease_stats["leases_cancelled"] += 1
            lease.disposition = Outcome("lease_terminalised_at_round_close")
            _cancel_lease_deadlines(run_ctx, lease, run_ctx.range_progress.get(lease.RangeSliceID))
    for req in run_ctx.reassignment_requests.values():
        if req.RoundID != rc.RoundID:
            continue
        # S4A-9: close any reassignment whose reassignee was still ACTIVE at round close (its
        # ACTIVE_HASHING interval was just closed by the round-closure idle transition, so the
        # ledger cumulative is finalised here for exact energy reconciliation).
        if req.status == "COMPLETED" and req.reassigned_search_start_time is not None \
                and req.reassigned_search_end_time is None:
            req.reassigned_search_end_time = t
            m = run_ctx.miners.get(req.new_MinerID)
            req.active_residency_at_search_end = _residency(m, "ACTIVE_HASHING", t)
        if req.status not in TERMINAL_REASSIGN_REQUEST_STATUSES:
            req.status = "CANCELLED"
            req.disposition = Outcome("reassignment_cancelled_at_round_close")
        # S4C-1: every request gets a terminal time + closed predecessor/standby snapshots.
        _stamp_request_terminal(run_ctx, req, t)
    # S4B-4: terminalise every wake handle of this round (no live UNCLAIMED/CLAIMED/ACTIVE handle).
    for wh in run_ctx.reassignment_wake_handles.values():
        if wh.RoundID == rc.RoundID and wh.status not in ("EXHAUSTED", "CANCELLED"):
            wh.status = "CANCELLED"
    for prog in run_ctx.range_progress.values():
        if prog.RoundID != rc.RoundID:
            continue
        if prog.current_lease_id is not None:
            lease = run_ctx.range_leases.get(prog.current_lease_id)
            if lease is None or lease.lease_status in TERMINAL_LEASE_STATUSES:
                prog.current_lease_id = None                # S4-9: no live current_lease_id
        if prog.committed_frontier >= prog.range_end:
            prog.terminal_status = "COMPLETED"
        elif prog.terminal_status == "OPEN":
            prog.terminal_status = "UNASSIGNED_AT_ROUND_CLOSE"
            run_ctx.lease_stats["uncovered_range_count"] += 1
            run_ctx.lease_stats["uncovered_nonce_count"] += prog.uncovered()
    _audit_slice_disjointness(run_ctx, rc)


def _audit_slice_disjointness(run_ctx: RunContext, rc: RoundContext) -> None:
    """S4B-4: prove the nonce-domain partition slices (primary ranges + reserve-DOMAIN slices)
    are pairwise disjoint.  Reassignment wake handles are NON-domain lifecycle tokens with NO
    nonce interval, so they can never be an overlapping domain slice (the ORIGINAL RangeProgress
    is the sole interval authority); each must merely reference a valid original slice of this
    round.  Any overlap increments ``overlapping_slice_count``."""
    intervals: List[Any] = []
    for mid, rng in run_ctx.round_ranges.get(rc.RoundID, {}).items():
        intervals.append((rng[0], rng[1]))
    for sl in run_ctx.reserve_slices.get(rc.RoundID, []):
        intervals.append((sl.range_start, sl.range_end))
    intervals.sort()
    overlaps = 0
    for i in range(1, len(intervals)):
        if intervals[i][0] < intervals[i - 1][1]:          # strict overlap of domain slices
            overlaps += 1
    # every wake handle of this round must reference a valid original slice (it holds no interval).
    for wh in run_ctx.reassignment_wake_handles.values():
        if wh.RoundID != rc.RoundID:
            continue
        prog = run_ctx.range_progress.get(wh.OriginalRangeSliceID)
        if prog is None or getattr(prog, "range_start", None) is None:
            overlaps += 1
    run_ctx.lease_stats["overlapping_slice_count"] += overlaps


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
            _adv.record_floor_breach_interval(run_ctx, rc.below_floor_since, observation_time)
            run_ctx.security_stats["total_duration_below_floor"] += dur
            if rc.below_floor_open_reason == "participants_prepared":
                run_ctx.security_stats["early_wake_below_floor_duration"] += dur
            rc.below_floor_since = None
            rc.below_floor_open_reason = None
            rc.current_breach_id = None
        if cfg.controller.is_refined():
            _refined_on_not_breached(run_ctx, rc, observation_time, h_eff)
        return None

    if round_terminal:
        _record_decision(run_ctx, obs, [], [], h_eff + inflight, hash_deficit,
                         "ROUND_ALREADY_TERMINAL")
        return None
    if not decide:
        # measure-only observation (round start): defer every activation/abort decision to a
        # capacity-change point where simulation time has advanced.
        return None

    if cfg.controller.is_refined():
        # Stage-8R: the revised controller replaces ONLY the decision tail — the observation,
        # measurement and below-floor interval semantics above are IDENTICAL in every mode.
        return _refined_floor_decide(run_ctx, rc, obs, observation_time, h_eff, active_count,
                                     inflight, inflight_count, pending_rate, pending_count)

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


# ============================================================ Stage-8R revised controller
# The revised idle and reserve-control policy within PoCol.  EVERY function below is inert
# under the default LEGACY_REACTIVE mode: nothing here runs, no registry fills, no counter
# advances, so the accepted Stage-8M controller is reproduced exactly (R-TEST-01).
def _current_episode(run_ctx: RunContext, rc: RoundContext) -> Any:
    eid = rc.current_episode_id
    if eid is None:
        return None
    ep = run_ctx.breach_episodes.get(eid)
    if ep is None or ep.status in TERMINAL_EPISODE_STATUSES:
        return None
    return ep


def _live_batch(run_ctx: RunContext, ep: Any) -> Any:
    """The episode's live activation batch, self-healing on missed terminalisation."""
    bid = ep.live_activation_batch_id
    if bid is None:
        return None
    batch = run_ctx.activation_batches.get(bid)
    if batch is None:
        ep.live_activation_batch_id = None
        return None
    if batch.status != "TERMINAL":
        reqs = [run_ctx.activation_requests.get(r) for r in batch.request_ids]
        if all(r is not None and r.status in TERMINAL_REQUEST_STATUSES for r in reqs):
            batch.status = "TERMINAL"
    if batch.status == "TERMINAL":
        ep.live_activation_batch_id = None
        return None
    return batch


def _open_episode(run_ctx: RunContext, rc: RoundContext, now: float, h_eff: float,
                  reason: str) -> Any:
    """R1: open ONE breach episode with immutable identity.  A reactive open in a
    predictive mode means the prediction missed — counted as a late wake."""
    ctrl = run_ctx.config.controller
    pol = run_ctx.config.security_floor
    run_ctx.episode_seq += 1
    gen = run_ctx.episodes_per_round.get(rc.RoundID, 0) + 1
    run_ctx.episodes_per_round[rc.RoundID] = gen
    ep = BreachEpisode(
        BreachEpisodeID=(run_ctx.RunID, "EPISODE", run_ctx.episode_seq),
        RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed, episode_generation=gen,
        opened_at=now, opened_h_effective=h_eff,
        target_hash_rate=pol.minimum_active_hash_rate,
        reactive_trigger_hash_rate=ctrl.trigger_rate(pol.minimum_active_hash_rate),
        recovery_hash_rate=ctrl.recovery_rate(pol.minimum_active_hash_rate),
        opened_reason=reason)
    run_ctx.breach_episodes[ep.BreachEpisodeID] = ep
    rc.current_episode_id = ep.BreachEpisodeID
    run_ctx.controller_stats["breach_episode_count"] += 1
    if reason == "REACTIVE" and ctrl.is_predictive():
        run_ctx.controller_stats["late_wake_count"] += 1
    return ep


def _update_pipeline_stats(run_ctx: RunContext, rc: RoundContext, now: float):
    """R5: piecewise-constant tracking of the H_pipeline REPORTING quantity.  H_pipeline is
    a scheduling forecast — never substituted for H_effective in any integrity check."""
    h_eff, _n, _ids = compute_h_effective(run_ctx, rc)
    pipe = _r5_h_pipeline(run_ctx, rc, h_eff)
    cs = run_ctx.controller_stats
    target = run_ctx.config.security_floor.minimum_active_hash_rate
    last_t = run_ctx._pipe_last_time
    if last_t is not None and now > last_t:
        dt = now - last_t
        cs["H_pipeline_time_integral"] += run_ctx._pipe_last_value * dt
        if run_ctx._pipe_last_value >= target and run_ctx._pipe_last_h_effective < target:
            cs["duration_pipeline_above_target_while_H_effective_below_target"] += dt
    run_ctx._pipe_last_time = now
    run_ctx._pipe_last_value = pipe
    run_ctx._pipe_last_h_effective = h_eff
    if pipe > cs["maximum_H_pipeline"]:
        cs["maximum_H_pipeline"] = pipe
    # Stage-8S: the useful-floor reporting quantities share the same touchpoints.
    _update_useful_stats(run_ctx, rc, now)
    return h_eff, pipe


def _resolve_due_predictions(run_ctx: RunContext, rc: RoundContext, now: float) -> None:
    """R4: fill each pending prediction with the ACTUAL H_effective at (or first touch
    after) its horizon.  A prediction of a closed round stays unresolved and is reported."""
    for pr in run_ctx.prediction_records:
        if pr.resolution_time is not None or pr.RoundID != rc.RoundID:
            continue
        if now >= pr.decision_time + pr.lookahead:
            h_eff, _n, _ids = compute_h_effective(run_ctx, rc)
            pr.resolution_time = now
            pr.actual_h_effective_at_horizon = h_eff
            pr.prediction_error = h_eff - pr.predicted_h_future
            target = run_ctx.config.security_floor.minimum_active_hash_rate
            pr.false_positive_wake = bool(pr.predicted_h_future < target <= h_eff)
            cs = run_ctx.controller_stats
            cs["resolved_prediction_count"] += 1
            cs["sum_absolute_prediction_error"] += abs(pr.prediction_error)
            if pr.false_positive_wake and pr.seated_batch_id is not None:
                cs["false_positive_wake_count"] += 1


def _refined_on_not_breached(run_ctx: RunContext, rc: RoundContext, now: float,
                             h_eff: float) -> None:
    """R2: recovery-side episode transitions.  RECOVERED requires the recovery threshold
    (0.82 x H0) AND no live activation batch still in flight; merely crossing the central
    0.80 target moves the episode to RECOVERY_IN_PROGRESS, never closes it."""
    ep = _current_episode(run_ctx, rc)
    if ep is None:
        return
    if run_ctx.config.controller.is_useful_floor():
        # USEFUL modes: recovery is judged against the CURRENT useful-work-aware reference.
        _m, _t, rec_now = _decision_reference(run_ctx, rc)
        ep.recovery_hash_rate = rec_now
    if h_eff >= ep.recovery_hash_rate and _live_batch(run_ctx, ep) is None:
        ep.status = "RECOVERED"
        ep.recovered_at = now
        ep.closed_at = now
        ep.disposition = "recovered_above_recovery_threshold"
        rc.current_episode_id = None
        cs = run_ctx.controller_stats
        cs["breach_episode_recovered_count"] += 1
        cs["total_episode_recovery_time_s"] += now - ep.opened_at
    else:
        ep.status = "RECOVERY_IN_PROGRESS"


def _refined_floor_decide(run_ctx: RunContext, rc: RoundContext, obs: Any, now: float,
                          h_eff: float, active_count: int, inflight: float,
                          inflight_count: int, pending_rate: float,
                          pending_count: int) -> Optional[Outcome]:
    """The refined REACTIVE decision at a breached, nonterminal, decide=True observation.

    Hysteresis (R2): a reactive episode opens only below 0.78 x H0 — the [0.78, 0.80)
    deadband is measured as breached (the measurement semantics are unchanged) but seats
    nothing.  One live activation batch per episode (R1/R3); deterministic cooldown (R3)."""
    ctrl = run_ctx.config.controller
    pol = run_ctx.config.security_floor
    # Stage-8S: USEFUL modes reference the useful-work-aware target; static modes keep the
    # exact Stage-8R numbers (the reference equals the static floor there).
    min_rate, trigger, _rec = _decision_reference(run_ctx, rc)
    _update_pipeline_stats(run_ctx, rc, now)
    _resolve_due_predictions(run_ctx, rc, now)
    covered = h_eff + inflight + pending_rate
    deficit = max(0.0, min_rate - covered)
    ep = _current_episode(run_ctx, rc)
    if ep is None:
        if h_eff >= trigger or rc.controller_reserves_exhausted:
            _record_decision(run_ctx, obs, [], [], covered, deficit,
                             "NO_ACTIVATION_REQUIRED")
            return None
        ep = _open_episode(run_ctx, rc, now, h_eff, "REACTIVE")
    live = _live_batch(run_ctx, ep)
    if covered + pol.floor_tolerance >= min_rate:
        # a sufficient live batch (plus pending capacity) already covers the target.
        if live is not None:
            run_ctx.controller_stats["duplicate_activation_batch_prevented_count"] += 1
        _record_decision(run_ctx, obs, [], [], covered, 0.0, "NO_ACTIVATION_REQUIRED")
        return None
    if live is not None:
        # R1/R3: at most ONE live activation batch per breach episode — never a second.
        run_ctx.controller_stats["duplicate_activation_batch_prevented_count"] += 1
        _record_decision(run_ctx, obs, [], [], covered, deficit, "NO_ACTIVATION_REQUIRED")
        return None
    if now < ep.cooldown_until and h_eff >= trigger:
        # R3 cooldown: no replacement batch for ordinary small oscillations; a new batch is
        # allowed only when the terminal batch left capacity below the frozen trigger.
        _record_decision(run_ctx, obs, [], [], covered, deficit, "NO_ACTIVATION_REQUIRED")
        return None
    return _seat_refined_batch(run_ctx, rc, ep, obs, now, covered, active_count,
                               inflight_count, pending_count, origin="REACTIVE",
                               seat_h_effective=h_eff, min_ref=min_rate)


def _seat_refined_batch(run_ctx: RunContext, rc: RoundContext, ep: Any, obs: Any,
                        now: float, covered: float, active_count: int, inflight_count: int,
                        pending_count: int, origin: str,
                        seat_h_effective: float = 0.0,
                        min_ref: Optional[float] = None) -> Optional[Outcome]:
    """R3: seat ONE activation batch sized to the capacity still missing from the target,
    using the accepted minimum-cardinality selection and the accepted all-or-none seating
    transaction.  Stale/cancelled/terminal requests never count toward sufficiency."""
    ctrl = run_ctx.config.controller
    pol = run_ctx.config.security_floor
    min_rate = pol.minimum_active_hash_rate if min_ref is None else min_ref
    min_count = pol.minimum_active_miner_count
    need = min_rate - covered
    need_count = 0 if min_count is None else max(
        0, min_count - (active_count + inflight_count + pending_count))
    seated_so_far = run_ctx.activations_per_round.get(rc.RoundID, 0)
    remaining = pol.maximum_activations_per_round - seated_so_far
    eligible = sorted([rr for rr in _reserve_records_for(run_ctx, rc)
                       if rr.reserve_status == "AVAILABLE"],
                      key=lambda r: (r.activation_priority, str(r.MinerID)))
    unclaimed = [sl for sl in run_ctx.reserve_slices.get(rc.RoundID, [])
                 if sl.status == "UNCLAIMED"]
    cap = min(len(eligible), len(unclaimed), max(0, remaining))
    cs = run_ctx.controller_stats
    if ctrl.is_useful_floor() and eligible and not unclaimed:
        # S8S-5 reserve admission control: eligible reserves exist but no useful work can
        # be atomically bound to a wake — record the rejection, wake nothing.
        cs["reserve_wakes_rejected_no_useful_work"] += len(eligible)
        run_ctx.log.append(Outcome("activation_rejected_no_useful_work",
                                   RoundID=rc.RoundID, eligible=len(eligible)))
    if cap <= 0:
        # the reserve pool of this round is spent: the episode terminalises UNATTAINABLE
        # and no further episode opens this round (the pool cannot refill inside a round).
        rc.controller_reserves_exhausted = True
        ep.status = "UNATTAINABLE"
        ep.closed_at = now
        ep.disposition = "no_eligible_reserve_or_unclaimed_slice"
        rc.current_episode_id = None
        cs["episode_unattainable_count"] += 1
        _record_decision(run_ctx, obs, [], [], covered, max(0.0, min_rate - covered),
                         "FLOOR_UNATTAINABLE")
        if ctrl.is_useful_floor():
            # the USEFUL counter is independent of the historical static counter.
            cs["useful_floor_unattainable_count"] += 1
            return None
        return _apply_floor_unattainable(run_ctx, rc, now)
    top = sorted((r.hash_rate for r in eligible), reverse=True)[:cap]
    max_projected = covered + sum(top)
    attainable = (max_projected + pol.floor_tolerance >= min_rate) \
        and (min_count is None
             or (active_count + inflight_count + pending_count + cap) >= min_count)
    if attainable:
        selected = select_reserves_to_cover(eligible, need, cap, need_count)
        policy = "ACTIVATION_SEATED"
    else:
        # CONTINUE_DEGRADED partial restoration: one bounded best-effort batch.
        selected = eligible[:cap]
        policy = "PARTIAL_RESTORATION"
        run_ctx.security_stats["partial_restoration_count"] += 1
    slices = unclaimed[:len(selected)]
    projected = covered + sum(r.hash_rate for r in selected)
    dec = _record_decision(run_ctx, obs, [r.MinerID for r in selected],
                           [s.RangeSliceID for s in slices], projected,
                           max(0.0, min_rate - projected), policy)
    run_ctx.batch_seq += 1
    batch = ActivationBatch(
        BatchID=(run_ctx.RunID, "BATCH", run_ctx.batch_seq),
        BreachEpisodeID=ep.BreachEpisodeID, RoundID=rc.RoundID, seated_at=now,
        status="LIVE", policy_result=policy, origin=origin,
        excess_activation_hash_rate=max(0.0, projected - min_rate),
        under_activation_hash_rate=max(0.0, min_rate - projected),
        seat_h_effective=seat_h_effective, seat_covered_capacity=covered)
    for rr, sl in zip(selected, slices):
        r = SeatReserveActivationTransaction(run_ctx, rc, rr, sl, obs, dec.DecisionID)
        if isinstance(r, Outcome):                     # seat failed and rolled back
            continue
        batch.request_ids.append(r.ReserveActivationRequestID)
        batch.miner_ids.append(rr.MinerID)
        batch.requested_hash_rate += float(rr.hash_rate)
        run_ctx.batch_by_request[r.ReserveActivationRequestID] = batch.BatchID
    if not batch.request_ids:
        return None                                    # nothing seated -> no batch exists
    run_ctx.activation_batches[batch.BatchID] = batch
    ep.live_activation_batch_id = batch.BatchID
    ep.activation_batch_ids.append(batch.BatchID)
    ep.cooldown_until = now + ctrl.cooldown(pol.activation_wake_latency)
    if ep.status == "OPEN":
        ep.status = "RECOVERY_IN_PROGRESS"
    cs["activation_batches_seated"] += 1
    if ctrl.is_useful_floor():
        cs["reserve_wakes_with_bound_work"] += len(batch.request_ids)
    cs["predictive_batches_seated" if origin == "PREDICTIVE"
       else "reactive_batches_seated"] += 1
    cs["requested_reserve_hash_rate_total"] += batch.requested_hash_rate
    cs["excess_activation_hash_rate_total"] += batch.excess_activation_hash_rate
    cs["under_activation_hash_rate_total"] += batch.under_activation_hash_rate
    if len(ep.activation_batch_ids) > cs["max_batches_per_episode"]:
        cs["max_batches_per_episode"] = len(ep.activation_batch_ids)
    return None


def _record_predictive_observation(run_ctx: RunContext, rc: RoundContext, now: float,
                                   trigger: Any) -> Any:
    """One authoritative floor observation for a predictive seat decision, with the SAME
    measurement semantics as EvaluateSecurityFloor (interval bookkeeping included)."""
    pol = run_ctx.config.security_floor
    key = _observation_key(run_ctx, rc, trigger)
    h_eff, active_count, _ = compute_h_effective(run_ctx, rc)
    min_rate = pol.minimum_active_hash_rate
    min_count = pol.minimum_active_miner_count
    hash_deficit = max(0.0, min_rate - h_eff)
    count_deficit = 0 if min_count is None else max(0, min_count - active_count)
    breached = (h_eff + pol.floor_tolerance < min_rate) \
        or (min_count is not None and active_count < min_count)
    run_ctx.observation_seq += 1
    obs = SecurityFloorObservation(
        ObservationID=(run_ctx.RunID, "OBS", run_ctx.observation_seq), RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed, observation_time=now,
        observation_reason="predictive_wake_ahead", effective_active_hash_rate=h_eff,
        active_miner_count=active_count, minimum_required_hash_rate=min_rate,
        minimum_required_miner_count=min_count, hash_rate_deficit=hash_deficit,
        miner_count_deficit=count_deficit, breached=breached, observation_key=key)
    run_ctx.observation_by_key[key] = obs
    run_ctx.security_observations.append(obs)
    run_ctx.security_stats["observation_count"] += 1
    if breached:
        run_ctx.security_stats["breach_observation_count"] += 1
        if hash_deficit > run_ctx.security_stats["max_hash_rate_deficit"]:
            run_ctx.security_stats["max_hash_rate_deficit"] = hash_deficit
        if rc.below_floor_since is None:
            rc.below_floor_since = now
            rc.below_floor_open_reason = "predictive_wake_ahead"
            rc.current_breach_id = obs.ObservationID
            run_ctx.security_stats["distinct_breach_count"] += 1
    elif rc.below_floor_since is not None:
        dur = now - rc.below_floor_since
        _adv.record_floor_breach_interval(run_ctx, rc.below_floor_since, now)
        run_ctx.security_stats["total_duration_below_floor"] += dur
        if rc.below_floor_open_reason == "participants_prepared":
            run_ctx.security_stats["early_wake_below_floor_duration"] += dur
        rc.below_floor_since = None
        rc.below_floor_open_reason = None
        rc.current_breach_id = None
    return obs


def _refined_predictive_check(run_ctx: RunContext, rc: RoundContext,
                              now: float) -> Optional[Outcome]:
    """R4 predictive wake-ahead, from OBSERVABLE progress only (never a future solution,
    round-end time or random draw).  Seats a predictive batch when the forecast capacity at
    the lookahead horizon falls below the central target and no sufficient live batch
    exists.  A prediction is an engineering estimate, not a security proof."""
    cfg = run_ctx.config
    ctrl = cfg.controller
    pol = cfg.security_floor
    if ctrl.is_useful_floor():
        # Stage-8S: USEFUL modes take their own path; the Stage-8R static-floor path below
        # stays byte-identical for STAGE8R_PREDICTIVE_STATIC_FLOOR / HYSTERESIS_PREDICTIVE.
        return _useful_predictive_check(run_ctx, rc, now)
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return None
    h_eff, _pipe = _update_pipeline_stats(run_ctx, rc, now)
    _resolve_due_predictions(run_ctx, rc, now)
    min_rate = pol.minimum_active_hash_rate
    look = ctrl.lookahead(pol.activation_wake_latency)
    h_future, det = _r4_predict_h_future(run_ctx, rc, now, look, min_rate)
    out: Optional[Outcome] = None
    if h_future + pol.floor_tolerance < min_rate and not rc.controller_reserves_exhausted:
        ep = _current_episode(run_ctx, rc)
        live = _live_batch(run_ctx, ep) if ep is not None else None
        in_cooldown = (ep is not None and now < ep.cooldown_until
                       and h_future >= ctrl.trigger_rate(min_rate))
        if live is None and not in_cooldown:
            if ep is None:
                ep = _open_episode(run_ctx, rc, now, h_eff, "PREDICTIVE")
            run_ctx.prediction_seq += 1
            pid = (run_ctx.RunID, "PRED", run_ctx.prediction_seq)
            obs = _record_predictive_observation(run_ctx, rc, now, ("PREDICTIVE", pid))
            pr = PredictionRecord(
                PredictionID=pid, RoundID=rc.RoundID, decision_time=now, lookahead=look,
                current_h_effective=h_eff, predicted_h_future=h_future,
                predicted_expiring_miners=list(det["expiring"]),
                live_incoming_capacity=det["live_incoming"],
                predicted_deficit=max(0.0, min_rate - h_future))
            run_ctx.prediction_records.append(pr)
            run_ctx.controller_stats["prediction_decision_count"] += 1
            _, active_count, _ids = compute_h_effective(run_ctx, rc)
            out = _seat_refined_batch(run_ctx, rc, ep, obs, now, h_future, active_count,
                                      0, 0, origin="PREDICTIVE",
                                      seat_h_effective=h_eff)
            pr.seated_batch_id = ep.live_activation_batch_id
            if pr.seated_batch_id is not None:
                pr.selected_reserve_set = list(
                    run_ctx.activation_batches[pr.seated_batch_id].miner_ids)
    # R6 (EXPLORATORY arm only): bounded suffix reassignment fallback.
    if out is None and ctrl.mode == "HYSTERESIS_PREDICTIVE_REASSIGNMENT":
        _maybe_controller_suffix_reassignment(run_ctx, rc, now, h_future)
    return out


def _maybe_controller_suffix_reassignment(run_ctx: RunContext, rc: RoundContext,
                                          now: float, h_future: float) -> None:
    """R6 (EXPLORATORY only): bounded suffix reassignment through the ACCEPTED Stage-4
    mechanism.  The controller seats a voluntary MinerCancelledEvent for a donor whose
    remaining unsearched suffix is at most the fixed 25-nonce chunk; the accepted lease
    machinery then terminalises the donor's lease and reassigns the EXACT remaining suffix
    (no overlap, no physical-frontier rewind, no duplicate honest work — the accepted
    Stage-4 gates enforce all three).  One immutable request per suffix lineage."""
    cfg = run_ctx.config
    ctrl = cfg.controller
    pol = cfg.security_floor
    if not cfg.range_lease.enabled:
        return
    if not any(b.RoundID == rc.RoundID for b in run_ctx.activation_batches.values()):
        return              # requires a live or completed controller reserve batch
    if h_future + pol.floor_tolerance >= pol.minimum_active_hash_rate:
        return              # predicted capacity is not below the target
    if _reassignment_in_flight(run_ctx, rc):
        run_ctx.controller_stats["controller_suffix_reassignment_skipped_in_flight"] += 1
        return
    chunk = ctrl.reassignment_chunk_nonces
    best = None
    for mid, st in rc.search_states.items():
        if st.completed:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":
            continue
        slice_id = run_ctx.slice_of_miner.get((rc.RoundID, mid))
        if slice_id is None or slice_id in run_ctx.controller_reassigned_slices:
            continue        # one immutable reassignment request per suffix lineage
        remaining = st.range_end - st.cursor
        if remaining <= 0 or remaining > chunk:
            continue        # fixed chunk bound: 25 nonces or the smaller remaining suffix
        t_rem = remaining / st.hash_rate if st.hash_rate > 0 else 0.0
        if best is None or t_rem > best[0]:
            best = (t_rem, str(mid), mid, slice_id)
    if best is None:
        return
    _t, _k, mid, slice_id = best
    run_ctx.controller_reassigned_slices.add(slice_id)
    run_ctx.controller_stats["controller_suffix_reassignment_count"] += 1
    eq = run_ctx.event_queue
    ScheduleEvent(eq, rc, "MinerCancelledEvent", now, "MINER_CANCELLED",
                  {"MinerID": mid, "RoundID_at_seat": rc.RoundID,
                   "TemplateID_at_seat": rc.TemplateID_committed,
                   "cancellation_reason": "controller_bounded_suffix_reassignment"},
                  ordinary_dispatch_origin(eq))


def _refined_note_request_terminal(run_ctx: RunContext, rc: RoundContext, req: Any,
                                   rate: float, completed: bool) -> None:
    """Batch bookkeeping when an activation request reaches a terminal status."""
    bid = run_ctx.batch_by_request.get(req.ReserveActivationRequestID)
    if bid is None:
        return
    batch = run_ctx.activation_batches.get(bid)
    if batch is None:
        return
    cs = run_ctx.controller_stats
    if completed:
        batch.completed_hash_rate += float(rate)
        cs["completed_reserve_hash_rate_total"] += float(rate)
    else:
        batch.cancelled_hash_rate += float(rate)
        cs["cancelled_reserve_hash_rate_total"] += float(rate)
    reqs = [run_ctx.activation_requests.get(r) for r in batch.request_ids]
    if all(r is not None and r.status in TERMINAL_REQUEST_STATUSES for r in reqs):
        batch.status = "TERMINAL"
        ep = run_ctx.breach_episodes.get(batch.BreachEpisodeID)
        if ep is not None and ep.live_activation_batch_id == batch.BatchID:
            ep.live_activation_batch_id = None


def _refined_close_round(run_ctx: RunContext, rc: RoundContext, t: float) -> None:
    """R1: round closure terminalises EVERY episode and activation batch of the round; no
    episode or activation may affect the next round."""
    cs = run_ctx.controller_stats
    _update_pipeline_stats(run_ctx, rc, t)
    for ep in run_ctx.breach_episodes.values():
        if ep.RoundID != rc.RoundID or ep.status in TERMINAL_EPISODE_STATUSES:
            continue
        if ep.live_activation_batch_id is not None:
            cs["episode_closed_with_live_activation_count"] += 1
        ep.status = "ROUND_CLOSED"
        ep.closed_at = t
        ep.disposition = "terminalised_at_round_close"
        ep.live_activation_batch_id = None
        cs["episode_round_closed_count"] += 1
    for batch in run_ctx.activation_batches.values():
        if batch.RoundID == rc.RoundID and batch.status != "TERMINAL":
            batch.status = "TERMINAL"
    rc.current_episode_id = None
    # ---- Stage-8S: terminalise every coarse-reassignment request of this round --------
    ctrl = run_ctx.config.controller
    if ctrl.is_coarse():
        for req in run_ctx.coarse_requests.values():
            if req.RoundID != rc.RoundID or req.status in ("COMPLETED", "CANCELLED"):
                continue
            st = rc.search_states.get(req.ReceiverMinerID)
            if st is not None and st.AssignmentID == req.AssignmentID and st.completed:
                req.status = "COMPLETED"
                req.completed_at = t
            else:
                req.status = "CANCELLED"
            run_ctx.coarse_live_by_receiver.pop(req.ReceiverMinerID, None)
            m = run_ctx.miners.get(req.ReceiverMinerID)
            if m is not None and m.state == "WAKING":
                run_ctx.apply_miner_state_transition(req.ReceiverMinerID,
                                                     "LOW_POWER_LISTEN", t)
    if ctrl.is_useful_floor():
        _update_useful_stats(run_ctx, rc, t)


# ============================================================ Stage-8S useful-work floor
# The useful-work-aware idle and reserve-control policy within PoCol.  Everything below is
# inert unless the controller mode is USEFUL_FLOOR_ONLY or USEFUL_FLOOR_COARSE_REASSIGNMENT;
# STAGE8R_PREDICTIVE_STATIC_FLOOR shares the unchanged Stage-8R code path exactly.
def _useful_target(run_ctx: RunContext, rc: RoundContext):
    """S8S-2: H_useful_target(t) = min(0.80 x H0, H_useful_available(t)).  The static floor
    is NEVER redefined — it stays reported as the historical secondary metric."""
    pol = run_ctx.config.security_floor
    avail, det = _s8s_h_useful_available(run_ctx, rc,
                                         run_ctx.config.controller.is_coarse())
    return min(pol.minimum_active_hash_rate, avail), avail, det


def _decision_reference(run_ctx: RunContext, rc: RoundContext):
    """The controller's decision reference: the static floor for static modes, the
    useful-work-aware target for USEFUL modes.  Measurement (observations, below-static-
    floor accounting) always stays on the static floor in every mode."""
    ctrl = run_ctx.config.controller
    pol = run_ctx.config.security_floor
    if not ctrl.is_useful_floor():
        m = pol.minimum_active_hash_rate
        return m, ctrl.trigger_rate(m), ctrl.recovery_rate(m)
    target, _avail, _det = _useful_target(run_ctx, rc)
    return target, ctrl.trigger_rate(target), ctrl.recovery_rate(target)


def _update_useful_stats(run_ctx: RunContext, rc: RoundContext, now: float) -> None:
    """S8S-2 reporting: piecewise-constant tracking of H_useful_available / H_useful_target
    and the useful-floor deficit.  Reporting only; never substituted into any integrity
    check.  Tracked in every refined mode with the floor enabled (zeros under LEGACY).

    The REPORTED availability always counts already-awake eligible receivers (the
    counterfactual "capacity that COULD usefully work"), so the useful-floor deficit is
    comparable across modes; the DECISION reference (`_useful_target`) counts receivers
    only when the mode's mechanism can actually deliver work to them."""
    if not run_ctx.config.security_floor.enabled:
        return
    pol = run_ctx.config.security_floor
    avail, det = _s8s_h_useful_available(run_ctx, rc, True)
    target = min(pol.minimum_active_hash_rate, avail)
    h_eff = det["h_effective"]
    cs = run_ctx.controller_stats
    last_t = run_ctx._useful_last_time
    if last_t is not None and now > last_t:
        dt = now - last_t
        cs["H_useful_available_time_integral"] += run_ctx._useful_last_available * dt
        cs["H_useful_target_time_integral"] += run_ctx._useful_last_target * dt
        if run_ctx._useful_last_h_effective < run_ctx._useful_last_target:
            cs["duration_below_useful_floor"] += dt
            cs["useful_floor_deficit_area"] += (
                run_ctx._useful_last_target - run_ctx._useful_last_h_effective) * dt
    run_ctx._useful_last_time = now
    run_ctx._useful_last_available = avail
    run_ctx._useful_last_target = target
    run_ctx._useful_last_h_effective = h_eff


def _coarse_note_completion(run_ctx: RunContext, rc: RoundContext, mid: Any,
                            t: float) -> None:
    """Mark a receiver's live coarse request COMPLETED when its chunk state completes."""
    crid = run_ctx.coarse_live_by_receiver.get(mid)
    if crid is None:
        return
    req = run_ctx.coarse_requests.get(crid)
    st = rc.search_states.get(mid)
    if req is not None and req.status == "ACTIVE" and st is not None and st.completed:
        req.status = "COMPLETED"
        req.completed_at = t
        del run_ctx.coarse_live_by_receiver[mid]


def _maybe_coarse_repartition(run_ctx: RunContext, rc: RoundContext, ep: Any,
                              now: float) -> float:
    """S8S-3/S8S-4: work-conserving deterministic coarse suffix repartition, receiver-first.

    Selects already-awake finished receivers FIRST; only then picks the donor with the
    LARGEST accepted unsearched suffix; partitions that suffix into deterministic,
    contiguous, near-equal chunks via the accepted integer apportionment rule (donor keeps
    the first chunk; at most one chunk per receiver; no non-final chunk below one batch —
    enforced by deterministic part-count reduction).  One repartition per donor lineage per
    breach episode; the chunk union equals the donor's accepted remaining suffix exactly
    and chunks are pairwise disjoint by construction.  Returns the receiver capacity added.
    """
    cfg = run_ctx.config
    batch = cfg.batch_size
    cs = run_ctx.controller_stats
    elig = []
    for mid, st in rc.search_states.items():
        if not st.completed or getattr(st, "completion_kind", None) != "EXHAUSTED":
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "LOW_POWER_LISTEN":
            continue
        if mid in run_ctx.coarse_live_by_receiver:
            cs["duplicate_reassignment_prevented_count"] += 1     # one live per receiver
            continue
        elig.append((float(st.hash_rate), str(mid), mid))
    elig.sort(key=lambda x: (-x[0], x[1]))
    if not elig:
        return 0.0
    best = None
    for mid, st in rc.search_states.items():
        if st.completed:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":
            continue
        a = rc.assignments.get(st.AssignmentID)
        if a is None or a.get("assignment_version") != st.assignment_version:
            continue
        remaining = st.range_end - st.cursor
        if remaining < 2 * batch:
            continue                       # donor must keep one batch and cede >= one
        key = (remaining, str(mid))
        if best is None or key > best[0]:
            best = (key, mid, st)
    if best is None:
        return 0.0
    _key, dmid, st_d = best
    lineage = (ep.BreachEpisodeID, st_d.AssignmentID)
    if lineage in run_ctx.coarse_lineage_by_episode:
        cs["donor_lineage_repartition_replay_count"] += 1         # exact replay: no effect
        return 0.0
    remaining = st_d.range_end - st_d.cursor
    part_count = min(1 + len(elig), -(-remaining // batch))       # ceil bound (S8S-4)
    while part_count > 1 and remaining // part_count < batch:
        part_count -= 1                    # no non-final chunk below one batch
    if part_count < 2:
        return 0.0
    base, rem = divmod(remaining, part_count)
    sizes = [base + (1 if i < rem else 0) for i in range(part_count)]
    bounds = []
    c = st_d.cursor
    for s in sizes:
        bounds.append((c, c + s))
        c += s
    assert c == st_d.range_end, "coarse chunk union must equal the accepted remaining suffix"
    # S8S-5 spirit — deterministic BENEFIT gate: repartition only when the post-split
    # makespan strictly beats the donor finishing alone (all inputs observable: rates,
    # chunk sizes; receivers start immediately because they are ALREADY AWAKE).
    donor_rate = float(st_d.hash_rate)
    alone = remaining / donor_rate if donor_rate > 0 else 0.0
    makespan = sizes[0] / donor_rate if donor_rate > 0 else 0.0
    for (c0, c1), (rate, _s, _m) in zip(bounds[1:], elig):
        makespan = max(makespan, (c1 - c0) / rate if rate > 0 else 0.0)
    if makespan >= alone:
        return 0.0                          # no useful speedup: leave the donor alone
    # -------- ATOMIC apply: receivers commit FIRST, the donor shrinks LAST; ANY seat
    # failure unwinds everything so a partial repartition can never orphan a chunk.
    # (Seating a receiver before the donor shrink is overlap-safe: the donor's queued
    # planned batch ends at most one batch past its cursor, inside its retained first
    # chunk, whose size is at least one batch.)
    committed = []
    added = 0.0
    ok = True
    for (c0, c1), (rate, _s, rmid) in zip(bounds[1:], elig):
        run_ctx.coarse_seq += 1
        crid = (run_ctx.RunID, "COARSE", run_ctx.coarse_seq)
        aid = f"CS-{rc.RoundID}-{rmid}"
        st_r = MinerSearchState(MinerID=rmid, AssignmentID=aid, assignment_version=1,
                                hash_rate=rate, range_start=c0, range_end=c1,
                                active_power=cfg.P_hash, idle_power=cfg.P_listen)
        prev_state = rc.search_states.get(rmid)
        prev_kind = run_ctx.search_assignment_kind.get((rc.RoundID, rmid))
        rc.search_states[rmid] = st_r
        rc.assignments[aid] = {"MinerID": rmid, "AssignmentID": aid,
                               "assignment_version": 1, "range": (c0, c1),
                               "RoundID": rc.RoundID,
                               "TemplateID": rc.TemplateID_committed,
                               "coverage_state": "OPEN"}
        run_ctx.search_assignment_kind[(rc.RoundID, rmid)] = COARSE_REASSIGNED_WORK
        # S8S-3 "immediately receive": the receiver is ALREADY AWAKE (LOW_POWER_LISTEN),
        # so it starts hashing its bound chunk synchronously — no wake transient, no
        # WAKING residency.  (A reserve, by contrast, always pays the accepted wake.)
        run_ctx.apply_miner_state_transition(rmid, "ACTIVE_HASHING", now)
        st_r.active_start = now
        r = _seat_hash_work(run_ctx, rc, st_r, at_time=now)
        if r.kind != "scheduled":
            if prev_state is not None:
                rc.search_states[rmid] = prev_state
            else:
                rc.search_states.pop(rmid, None)
            del rc.assignments[aid]
            if prev_kind is None:
                run_ctx.search_assignment_kind.pop((rc.RoundID, rmid), None)
            else:
                run_ctx.search_assignment_kind[(rc.RoundID, rmid)] = prev_kind
            run_ctx.apply_miner_state_transition(rmid, "LOW_POWER_LISTEN", now)
            ok = False
            break
        req = CoarseRequest(CoarseRequestID=crid, RoundID=rc.RoundID,
                            TemplateID=rc.TemplateID_committed,
                            BreachEpisodeID=ep.BreachEpisodeID, DonorMinerID=dmid,
                            DonorAssignmentID=st_d.AssignmentID, ReceiverMinerID=rmid,
                            AssignmentID=aid, chunk_start=c0, chunk_end=c1, seated_at=now,
                            status="ACTIVE", started_at=now)
        run_ctx.coarse_requests[crid] = req
        run_ctx.coarse_live_by_receiver[rmid] = crid
        committed.append((rmid, prev_state, prev_kind, req, aid))
        added += rate
    if ok:
        # donor retains the FIRST chunk: shrink under a fresh assignment version, cancel
        # the superseded planned batch and re-plan inside the new bound.
        prev_end = st_d.range_end
        prev_ver = st_d.assignment_version
        prev_gen = st_d.search_generation
        a = rc.assignments[st_d.AssignmentID]
        _cancel_queued_hash_events(run_ctx, dmid)
        st_d.range_end = bounds[0][1]
        st_d.assignment_version += 1
        st_d.search_generation += 1
        a["assignment_version"] = st_d.assignment_version
        a["range"] = (a["range"][0], st_d.range_end)
        rd = _seat_hash_work(run_ctx, rc, st_d, at_time=now)
        if rd.kind != "scheduled":
            st_d.range_end = prev_end
            st_d.assignment_version = prev_ver
            st_d.search_generation = prev_gen
            a["assignment_version"] = prev_ver
            a["range"] = (a["range"][0], prev_end)
            _seat_hash_work(run_ctx, rc, st_d, at_time=now)     # restore the donor's plan
            ok = False
    if not ok:
        for rmid, prev_state, prev_kind, req, aid in committed:
            _cancel_queued_hash_events(run_ctx, rmid)
            if prev_state is not None:
                rc.search_states[rmid] = prev_state
            else:
                rc.search_states.pop(rmid, None)
            rc.assignments.pop(aid, None)
            if prev_kind is None:
                run_ctx.search_assignment_kind.pop((rc.RoundID, rmid), None)
            else:
                run_ctx.search_assignment_kind[(rc.RoundID, rmid)] = prev_kind
            run_ctx.coarse_requests.pop(req.CoarseRequestID, None)
            run_ctx.coarse_live_by_receiver.pop(rmid, None)
            m = run_ctx.miners.get(rmid)
            if m is not None and m.state == "ACTIVE_HASHING":
                run_ctx.apply_miner_state_transition(rmid, "LOW_POWER_LISTEN", now)
        return 0.0
    # -------- COMMIT: only a fully-applied repartition marks the lineage and counters.
    run_ctx.coarse_lineage_by_episode.add(lineage)
    cs["coarse_repartition_count"] += 1
    for _rmid, _pstate, _pkind, req, _aid in committed:
        cs["coarse_reassignment_count"] += 1
        size = req.chunk_end - req.chunk_start
        cs["sum_coarse_chunk_size"] += size
        if cs["minimum_coarse_chunk_size"] == 0 or size < cs["minimum_coarse_chunk_size"]:
            cs["minimum_coarse_chunk_size"] = size
        if size > cs["maximum_coarse_chunk_size"]:
            cs["maximum_coarse_chunk_size"] = size
    donor_size = bounds[0][1] - bounds[0][0]
    if cs["minimum_coarse_chunk_size"] == 0 or donor_size < cs["minimum_coarse_chunk_size"]:
        cs["minimum_coarse_chunk_size"] = donor_size
    if donor_size > cs["maximum_coarse_chunk_size"]:
        cs["maximum_coarse_chunk_size"] = donor_size
    return added


def _useful_predictive_check(run_ctx: RunContext, rc: RoundContext,
                             now: float) -> Optional[Outcome]:
    """S8S-2/3/5: the USEFUL-mode predictive path — coarse reassignment FIRST, reserve wake
    only when already-awake reassignment cannot fill the useful deficit, and never a
    reserve wake without atomically bindable useful work."""
    cfg = run_ctx.config
    ctrl = cfg.controller
    pol = cfg.security_floor
    if rc is None or rc.round_state in _TERMINAL_ROUND:
        return None
    h_eff, _pipe = _update_pipeline_stats(run_ctx, rc, now)
    _resolve_due_predictions(run_ctx, rc, now)
    min_ref, trigger_ref, _rec = _decision_reference(run_ctx, rc)
    look = ctrl.lookahead(pol.activation_wake_latency)
    h_future, det = _r4_predict_h_future(run_ctx, rc, now, look, min_ref)
    if h_future + pol.floor_tolerance >= min_ref:
        return None
    ep = _current_episode(run_ctx, rc)
    live = _live_batch(run_ctx, ep) if ep is not None else None
    if live is not None:
        return None                                  # one live batch per episode (R3)
    if ep is not None and now < ep.cooldown_until and h_future >= trigger_ref:
        return None                                  # cooldown (R3)
    if ep is None:
        ep = _open_episode(run_ctx, rc, now, h_eff, "PREDICTIVE")
    added = 0.0
    if ctrl.is_coarse():
        added = _maybe_coarse_repartition(run_ctx, rc, ep, now)    # S8S-3: receivers first
    still_deficit = min_ref - (h_future + added)
    if still_deficit <= pol.floor_tolerance:
        return None                                  # already-awake reassignment filled it
    # reserve admission control (S8S-5): a reserve wake needs atomically bindable useful
    # work — an UNCLAIMED reserve-domain slice.  The accepted seating transaction claims
    # the slice and binds it to the wake request atomically; without one, no wake.
    eligible = [rr for rr in _reserve_records_for(run_ctx, rc)
                if rr.reserve_status == "AVAILABLE"]
    unclaimed = [sl for sl in run_ctx.reserve_slices.get(rc.RoundID, [])
                 if sl.status == "UNCLAIMED" and sl.size() > 0]
    if not eligible or not unclaimed:
        if eligible and not unclaimed:
            run_ctx.controller_stats["reserve_wakes_rejected_no_useful_work"] += len(eligible)
            run_ctx.log.append(Outcome("activation_rejected_no_useful_work",
                                       RoundID=rc.RoundID, eligible=len(eligible)))
        run_ctx.controller_stats["useful_floor_unattainable_count"] += 1
        return None
    run_ctx.prediction_seq += 1
    pid = (run_ctx.RunID, "PRED", run_ctx.prediction_seq)
    obs = _record_predictive_observation(run_ctx, rc, now, ("PREDICTIVE", pid))
    pr = PredictionRecord(
        PredictionID=pid, RoundID=rc.RoundID, decision_time=now, lookahead=look,
        current_h_effective=h_eff, predicted_h_future=h_future,
        predicted_expiring_miners=list(det["expiring"]),
        live_incoming_capacity=det["live_incoming"],
        predicted_deficit=max(0.0, min_ref - h_future))
    run_ctx.prediction_records.append(pr)
    run_ctx.controller_stats["prediction_decision_count"] += 1
    _, active_count, _ids = compute_h_effective(run_ctx, rc)
    out = _seat_refined_batch(run_ctx, rc, ep, obs, now, h_future + added, active_count,
                              0, 0, origin="PREDICTIVE", seat_h_effective=h_eff,
                              min_ref=min_ref)
    pr.seated_batch_id = ep.live_activation_batch_id
    if pr.seated_batch_id is not None:
        pr.selected_reserve_set = list(
            run_ctx.activation_batches[pr.seated_batch_id].miner_ids)
    return out


def SeatReserveActivationTransaction(run_ctx: RunContext, rc: RoundContext, rr: Any, sl: Any,
                                     obs: Any, decision_id: Any,
                                     activation_scope: str = "RESERVE_DOMAIN_CLAIM",
                                     range_reassignment_request_id: Any = None,
                                     wake_handle_id: Any = None,
                                     original_range_slice_id: Any = None) -> Any:
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
    sid = _obj_activation_id(sl)          # S4B-4: RangeSliceID (domain) or WakeHandleID (wake)
    req_id = ("RESERVE_ACTIVATION", rc.RoundID, rc.TemplateID_committed, obs.ObservationID,
              rr.MinerID, sid, rr.activation_generation)
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
    rr.assigned_reserve_slice_id = sid
    rr.activation_request_id = req_id
    payload = {"ReserveActivationRequestID": req_id, "SecurityFloorObservationID": obs.ObservationID,
               "ReserveActivationDecisionID": decision_id, "RoundID_at_seat": rc.RoundID,
               "TemplateID_at_seat": rc.TemplateID_committed, "MinerID": rr.MinerID,
               "ReserveSliceID": sid, "activation_generation": rr.activation_generation,
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
                       ReserveSliceID=sid)
    # COMMIT: publish the EventRef, create the SEATED request, advance the counter.
    ev = r.event_ref
    rr.activation_event_ref = ev
    req = ReserveActivationRequest(
        ReserveActivationRequestID=req_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        SecurityFloorBreachID=obs.ObservationID, DecisionID=decision_id, MinerID=rr.MinerID,
        ReserveSliceID=sid, activation_generation=rr.activation_generation,
        status="SEATED", start_event_ref=ev, seated_at=now,   # S5B-4: explicit seating time
        activation_scope=activation_scope,
        range_reassignment_request_id=range_reassignment_request_id,
        # S4C-4: explicit, auditable Path-B identity (ReserveSliceID is NOT overloaded as the wake
        # identity) — retained even after the wake handle is later removed.
        WakeHandleID=wake_handle_id, OriginalRangeSliceID=original_range_slice_id,
        RangeReassignmentRequestID=range_reassignment_request_id,
        disposition=Outcome("reserve_activation_seated"))
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
    # the request must exist and its immutable identity must match the payload exactly.
    req = run_ctx.activation_requests.get(payload["ReserveActivationRequestID"])
    if rr is None or req is None:
        return Outcome("activation_no_effect", reason="unknown_reserve_or_request")
    # S4B-4: a REASSIGNMENT_WAKE_ONLY activation resolves its ReserveSliceID to a NON-domain
    # ReassignmentWakeHandle; a RESERVE_DOMAIN_CLAIM to a reserve-domain RangeSlice.
    if req.activation_scope == "REASSIGNMENT_WAKE_ONLY":
        sl = run_ctx.reassignment_wake_handles.get(payload["ReserveSliceID"])
    else:
        sl = run_ctx.reserve_slice_by_id.get(payload["ReserveSliceID"])
    if sl is None:
        return Outcome("activation_no_effect", reason="unknown_reserve_or_slice")
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


def _terminalise_synthetic_activation_decision(run_ctx: RunContext, decision_id: Any,
                                               reason: Any) -> None:
    """S4C-3: give the synthetic Path-B activation decision an explicit terminal FAILURE
    disposition so no decision remains labelled ACTIVATION_SEATED without a recorded failed
    terminal outcome after its wake fails."""
    if decision_id is None:
        return
    for dec in run_ctx.activation_decisions:
        if dec.DecisionID == decision_id:
            dec.disposition = Outcome("reassignment_wake_activation_failed", reason=reason)
            break


def _clear_reserve_record_activation_fields(rr: Any) -> None:
    """S4C-3: clear EVERY reverse link a failed activation left on the reserve record."""
    if rr is None:
        return
    rr.assigned_reserve_slice_id = None
    rr.activation_request_id = None
    rr.activation_event_ref = None


def _fail_pathb_wake(run_ctx: RunContext, rc: RoundContext, act_req: Any, t: float,
                     reason: Any) -> Optional[Outcome]:
    """S4B-5/S4C-3: fully clean up a Path-B reassignment whose Stage-3 wake seat failed at a start
    / complete point — terminalise the linked ReserveActivationRequest AND RangeReassignmentRequest
    FAILED, close every wake/standby timestamp, remove the wake handle + every reverse link
    (``reassign_by_suffix_slice`` + reserve-record fields), give the synthetic activation decision a
    terminal failure disposition, preserve the committed frontier (``current_lease_id`` stays None
    from the revoke), and apply the no-eligible policy — leaving NO registry / reverse binding that
    still references the removed WakeHandleID."""
    # S4C-3: terminalise the activation request itself + clear the reserve record + the decision.
    act_req.status = "FAILED"
    act_req.disposition = Outcome("reserve_activation_wake_seat_failed", reason=reason)
    _terminalise_synthetic_activation_decision(run_ctx, act_req.DecisionID, reason)
    _clear_reserve_record_activation_fields(
        run_ctx.reserve_records.get((rc.RoundID, act_req.MinerID)))
    rreq = run_ctx.reassignment_requests.get(act_req.range_reassignment_request_id)
    prog = None
    if rreq is not None and rreq.status not in TERMINAL_REASSIGN_REQUEST_STATUSES:
        rreq.status = "FAILED"
        rm = run_ctx.miners.get(rreq.new_MinerID)          # close the failed wake-energy interval
        if rm is not None and rreq.wake_residency_at_start is not None:
            rreq.wake_residency_at_end = _residency(rm, "WAKING", t)
        _stamp_request_terminal(run_ctx, rreq, t)          # S4C-1 close predecessor/standby
        rreq.disposition = Outcome("reassignment_wake_seat_failed", reason=reason)
        run_ctx.lease_stats["reassignment_requests_failed"] += 1
        run_ctx.lease_stats["pathb_rollback_count"] += 1
        wh_id = rreq.wake_handle_id
        if wh_id is not None:                              # remove the wake handle + reverse links
            run_ctx.reassignment_wake_handles.pop(wh_id, None)
            run_ctx.reassign_by_suffix_slice.pop(wh_id, None)
            rreq.wake_handle_id = None
        prog = run_ctx.range_progress.get(rreq.RangeSliceID)
    if prog is not None:
        if prog.current_lease_id is None and prog.committed_frontier < prog.range_end:
            prog.terminal_status = "UNASSIGNED_PENDING_RETRY"
        return _apply_no_eligible_policy(run_ctx, rc, prog)
    return None


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
    # S4A-9 Path B: the reassignment's wake interval begins now (energy attribution) — the linked
    # reassignment request's WAKING window is [activation-start, activation-complete].
    if req.activation_scope == "REASSIGNMENT_WAKE_ONLY" \
            and req.range_reassignment_request_id is not None:
        rreq = run_ctx.reassignment_requests.get(req.range_reassignment_request_id)
        if rreq is not None and rreq.started_at is None:
            rreq.started_at = t
            rm = run_ctx.miners.get(mid)
            rreq.wake_residency_at_start = _residency(rm, "WAKING", t)   # S4C-1
            rreq.reassignee_reserve_residency_at_wake_start = _residency(rm, "RESERVE", t)
            rreq.reassignee_low_residency_at_wake_start = _residency(rm, "LOW_POWER_LISTEN", t)
            rreq.reassignee_offline_residency_at_wake_start = _residency(rm, "OFFLINE", t)
    complete_time = t + run_ctx.config.security_floor.activation_wake_latency
    # S5B-4: the reserve-activation wake is a REAL wake lifecycle and must consult the delayed-wake
    # policy exactly like the primary wake.  A Path-B reassignment reserve wake travels through this
    # same lifecycle with activation_scope REASSIGNMENT_WAKE_ONLY, so it is attributed to its OWN
    # lifecycle label and carries the linked reassignment-request identity.
    if req.activation_scope == "REASSIGNMENT_WAKE_ONLY":
        _wake_lc = "PATH_B_REASSIGNMENT_RESERVE_WAKE"
        _wake_rid = ("PATH_B_RESERVE_WAKE", req.ReserveActivationRequestID,
                     req.RangeReassignmentRequestID, req.WakeHandleID)
    else:
        _wake_lc = "RESERVE_ACTIVATION_WAKE"
        _wake_rid = ("RESERVE_ACTIVATION", req.ReserveActivationRequestID,
                     req.activation_generation)
    complete_time += _adv.wake_extra_latency(run_ctx, rc, mid, complete_time, t,
                                             request_id=_wake_rid, lifecycle=_wake_lc)
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
        _clear_reserve_record_activation_fields(rr)         # S4C-3: clear ALL reverse links
        sl.status = "UNCLAIMED"                             # declared slice-restore policy
        sl.claimed_by = None
        req.status = "FAILED"
        req.disposition = Outcome("reserve_activation_complete_seat_failed", reason=r)
        run_ctx.security_stats["activation_complete_seat_failure_count"] += 1
        # S4B-5 Path B: a failed CompleteEvent seat must ALSO fully clean the linked reassignment
        # (fail it, close the wake-energy interval, remove the wake handle + links, apply the
        # no-eligible policy) so no in-flight/orphan state hangs the round to the horizon.
        pathb = None
        if req.activation_scope == "REASSIGNMENT_WAKE_ONLY":
            run_ctx.lease_stats["wake_complete_seat_failures"] += 1
            pathb = _fail_pathb_wake(run_ctx, rc, req, t, r)
        dec = EvaluateSecurityFloor(run_ctx, rc, t, "reserve_activation_complete_seat_failed")
        if isinstance(dec, Outcome):
            return dec
        if isinstance(pathb, Outcome):
            return pathb
        term = _maybe_terminate_no_block(run_ctx, rc)
        if term is not None:
            return term
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
    if cfg.controller.is_refined():                         # Stage-8R batch bookkeeping
        _refined_note_request_terminal(run_ctx, rc, req, rr.hash_rate, completed=True)
    is_wake = isinstance(sl, ReassignmentWakeHandle)
    sid = _obj_activation_id(sl)
    # S4B-4: the reassignment wake handle carries NO interval; the reassignee's search range is
    # the ORIGINAL RangeProgress suffix [committed_frontier, range_end).  A reserve-domain claim
    # uses its own slice interval.
    if is_wake:
        sl.status = "ACTIVE"
        oprog = run_ctx.range_progress.get(sl.OriginalRangeSliceID)
        r_start = oprog.committed_frontier if oprog is not None else 0
        r_end = oprog.range_end if oprog is not None else 0
    else:
        r_start, r_end = sl.range_start, sl.range_end
    # S3-7: an activated reserve gets a NORMAL MinerSearchState over its exact search range.
    aid = f"AR-{rc.RoundID}-{mid}"
    version = 1
    st = MinerSearchState(MinerID=mid, AssignmentID=aid, assignment_version=version,
                          hash_rate=rr.hash_rate, range_start=r_start,
                          range_end=r_end, active_power=cfg.P_hash, idle_power=cfg.P_listen)
    st.active_start = t
    rc.search_states[mid] = st
    rc.assignments[aid] = {"MinerID": mid, "AssignmentID": aid, "assignment_version": version,
                           "range": (r_start, r_end),
                           "RoundID": rc.RoundID, "TemplateID": rc.TemplateID_committed,
                           "coverage_state": "OPEN"}
    run_ctx.search_assignment_kind[(rc.RoundID, mid)] = ACTIVATED_RESERVE_ASSIGNMENT
    run_ctx.security_stats["activations_completed"] += 1
    # S4-2/S4B-4: with the range-lease layer engaged, give this activated reserve a lease.
    # A REASSIGNMENT_WAKE_ONLY wake binds the reassigned lease on the ORIGINAL RangeProgress
    # (Path B); a normal reserve-domain activation gets its own RangeProgress + ACTIVE lease.
    if cfg.range_lease.enabled:
        if is_wake and sid in run_ctx.reassign_by_suffix_slice:
            _bind_reserve_reassignment_if_any(run_ctx, rc, mid, sl, t, st)
        elif not is_wake:
            _create_range_progress_and_lease(run_ctx, rc, mid, aid, version, sid,
                                             r_start, r_end, ACTIVATED_RESERVE_ASSIGNMENT, t)
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
    return Outcome("reserve_activation_completed", MinerID=mid, ReserveSliceID=sid)


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
        _adv.record_floor_breach_interval(run_ctx, rc.below_floor_since, t)
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
    # Stage-8R: terminalise every breach episode and batch BEFORE the request loop so an
    # episode closed while its batch is still live is counted truthfully.
    if run_ctx.config.controller.is_refined():
        _refined_close_round(run_ctx, rc, t)
    # S3A-6: every activation request of this closed round must be terminal.
    for req in run_ctx.activation_requests.values():
        if req.RoundID != rc.RoundID:
            continue
        if req.status not in TERMINAL_REQUEST_STATUSES:
            req.status = "CANCELLED"
            req.disposition = Outcome("reserve_activation_request_cancelled_at_round_close")
            if run_ctx.config.controller.is_refined():
                rr = run_ctx.reserve_records.get((rc.RoundID, req.MinerID))
                _refined_note_request_terminal(run_ctx, rc, req,
                                               rr.hash_rate if rr is not None else 0.0,
                                               completed=False)


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
    # S5-6/S5-11: record every accepted-block time so a withheld-then-released block is
    # distinguishable from one that was never accepted at all.
    run_ctx.acceptance_times.append(run_ctx.event_queue.current_event_time)
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
    # S4-12: terminalise every lease + reassignment request; report unfinished suffixes.
    if run_ctx.config.range_lease.enabled:
        _close_lease_state(run_ctx, rc, t)
    # S5-12: terminalise every Stage-5 adversarial action bound to this round (cancel queued
    # delayed-release events, close withheld solutions / claims / delayed wakes) and finalise
    # the round's reward + penalty ledger.  Nothing adversarial survives into the next round.
    _adv.close_adversarial_round(run_ctx, rc, t)
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


# ============================================================ Stage-5 withheld release
def _handle_withheld_release(run_ctx: RunContext, payload: Dict[str, Any],
                             envelope: Dict[str, Any]) -> Outcome:
    """S5-6: a DELAYED_RELEASE withholder finally publishes the block it has been sitting on.

    The release is subject to the SAME acceptance path and the SAME immutable identity checks
    as a prompt publication: it is accepted only if its round and template are still current and
    no block has already been accepted.  A release into a closed round, a rotated template, or a
    round that another miner has already won performs NO effect — the withholder simply loses
    the block.  Releasing never changes the fixed SHA-256 target or difficulty."""
    rc = run_ctx.current_round_context
    ws_id = payload["WithheldSolutionID"]
    rec = run_ctx.withheld_solutions.get(ws_id)
    now = run_ctx.event_queue.current_event_time
    if rec is None:
        return Outcome("withheld_release_unknown_noop", WithheldSolutionID=ws_id)
    if rec.status != "WITHHELD":                          # replay / already terminal (S5-12)
        return Outcome("withheld_release_replay_noop", WithheldSolutionID=ws_id,
                       status=rec.status)
    if rc is None or payload["RoundID_at_seat"] != rc.RoundID \
            or payload["TemplateID_at_seat"] != rc.TemplateID_committed \
            or rc.round_state in ("ROUND_ACCEPTED", "ROUND_ABORTED"):
        rec.status = "RELEASED_TOO_LATE"
        rec.release_time = now
        rec.disposition = Outcome("withheld_release_stale_noop")
        run_ctx.adversarial_stats["withheld_release_too_late_count"] += 1
        return Outcome("withheld_release_stale_noop", MinerID=rec.MinerID)
    if rc.block_accepted or rc.acceptance_seq > 0:        # another miner already won
        rec.status = "RELEASED_TOO_LATE"
        rec.release_time = now
        rec.disposition = Outcome("withheld_release_lost_race")
        run_ctx.adversarial_stats["withheld_release_too_late_count"] += 1
        return Outcome("withheld_release_lost_race", MinerID=rec.MinerID)
    rec.status = "RELEASED_ACCEPTED"
    rec.release_time = now
    rec.disposition = Outcome("withheld_release_accepted")
    run_ctx.adversarial_stats["withheld_released_count"] += 1
    run_ctx.adversarial_stats["withheld_total_hidden_duration"] += (now - rec.found_time)
    return _seat_acceptance(run_ctx, rc, at_time=now, winner=rec.MinerID,
                            winning_nonce=rec.nonce)


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
    "MinerFailureEvent": _handle_miner_failure,
    "MinerCancelledEvent": _handle_miner_cancelled,
    "RangeReassignmentStartEvent": _handle_range_reassignment_start,
    "RangeReassignmentCompleteEvent": _handle_range_reassignment_complete,
    "RangeReassignmentRetryEvent": _handle_range_reassignment_retry,
    "RangeLeaseExpiryEvent": _handle_range_lease_expiry,
    "RangeProgressTimeoutEvent": _handle_range_progress_timeout,
    "WithheldSolutionReleaseEvent": _handle_withheld_release,     # S5-6
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
