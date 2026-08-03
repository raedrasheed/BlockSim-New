"""Stage-5 adversarial + incentive RUNTIME hooks for the PoCol core simulator.

Every function here is a NO-OP (or returns the honest default) unless the Stage-5 model is
explicitly enabled, so the accepted Stage-4C baseline is behaviourally unchanged (S5-01).

Stage 5 MODELS bounded behaviours and MEASURES outcomes.  No function here proves incentive
compatibility, fairness, Sybil resistance, selfish-mining resistance, coalition resistance,
common-prefix or chain-quality security, or Bitcoin/PoW-equivalent security.  The fixed
SHA-256 target and difficulty are NEVER changed by any Stage-5 parameter (S5-26).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from .events import EventQueue, ScheduleEvent, CancelQueuedEvent, ordinary_dispatch_origin
from .events import Outcome
from .adversarial import (AdversarialEntity, MinerBehaviourProfile, ProgressClaim,
                          WithheldSolutionRecord, DelayedWakeAction, InvalidActionRecord,
                          IncentiveLedgerEntry, AcceptedFrontierRecord, SubAssignmentRecord,
                          VirtualIdentityRecord, AbandonmentActionRecord,
                          audit_draw, ADVERSARIAL_ACTOR_CLASSES, AVAILABILITY_STATES)


# --------------------------------------------------------------------- helpers
def adversarial_enabled(run_ctx: Any) -> bool:
    return bool(run_ctx.config.adversarial.enabled)


def incentive_enabled(run_ctx: Any) -> bool:
    return bool(run_ctx.config.incentive.enabled)


def _entity_for(run_ctx: Any, mid: Any) -> Any:
    return run_ctx.entity_of_miner.get(mid, mid)


def _profile(run_ctx: Any, rc: Any, mid: Any) -> Optional[MinerBehaviourProfile]:
    return run_ctx.behaviour_profiles.get((rc.RoundID, mid))


def availability_residency(run_ctx: Any, mid: Any, t: float) -> float:
    """Time-aware sanctioned-availability residency for ``mid`` at time ``t``.

    The residency ledger accumulates only CLOSED intervals, so the miner's still-open interval
    ``[state_since, t]`` must be added explicitly or a miner that is availability-resident at
    round closure is credited zero.  Mirrors the Stage-4C exact-interval energy rule."""
    m = run_ctx.miners.get(mid)
    if m is None:
        return 0.0
    total = sum(m.duration.get(s, 0.0) for s in AVAILABILITY_STATES)
    if m.state in AVAILABILITY_STATES and t > m.state_since:
        total += t - m.state_since
    return total


def interval_union(intervals) -> List[Tuple[int, int]]:
    """S5A-2: the canonical, sorted, NON-OVERLAPPING union of half-open intervals.

    ``[(0,80), (40,80)]`` unions to ``[(0,80)]`` — 80 unique positions, not 120.  Adjacent
    intervals are merged so the representation is canonical and its cardinality is exactly the
    number of distinct nonce positions covered.
    """
    out: List[List[int]] = []
    for lo, hi in sorted(intervals):
        if hi <= lo:
            continue
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


def charge_action_budget(run_ctx: Any, rc: Any, kind: str) -> bool:
    """S5A-7: enforce the declared ``maximum_actions_per_round`` BEFORE a new adversarial action
    is created.  Returns False (and counts the rejection) once the round's budget is spent."""
    if not adversarial_enabled(run_ctx):
        return False
    limit = run_ctx.config.adversarial.maximum_actions_per_round
    used = run_ctx.adv_actions_this_round.get(rc.RoundID, 0)
    if used >= limit:
        run_ctx.adversarial_stats["actions_rejected_over_limit"] += 1
        return False
    run_ctx.adv_actions_this_round[rc.RoundID] = used + 1
    return True


def is_adversarial_miner(run_ctx: Any, mid: Any) -> bool:
    eid = run_ctx.entity_of_miner.get(mid)
    ent = run_ctx.adversarial_entities.get(eid) if eid is not None else None
    return bool(ent is not None and ent.actor_class in ADVERSARIAL_ACTOR_CLASSES)


def register_action(run_ctx: Any, action_id: Any, factory) -> Any:
    """S5-12: replay-idempotent adversarial-action registry.  Exact replay of the same
    immutable AdversarialActionID returns the existing record and performs no second effect."""
    existing = run_ctx.adversarial_actions.get(action_id)
    if existing is not None:
        return existing
    rec = factory()
    run_ctx.adversarial_actions[action_id] = rec
    return rec


# --------------------------------------------------------------------- S5-1 behaviours
def build_entities(run_ctx: Any) -> None:
    """Materialise the declared adversarial entities ONCE (run-level).  Miners not owned by a
    declared entity are their own HONEST entity."""
    if run_ctx.adversarial_entities:
        return
    for (eid, klass, mids, coal) in run_ctx.config.adversarial.entities:
        ent = AdversarialEntity(EntityID=eid, actor_class=klass,
                                controlled_miner_ids=tuple(mids), coalition_id=coal)
        run_ctx.adversarial_entities[eid] = ent
        for mid in mids:
            run_ctx.entity_of_miner[mid] = eid


def _declared_flags(run_ctx: Any, mid: Any) -> tuple:
    """The behaviour flags declared for ``mid`` this round (round_seq 0 => every round)."""
    for (rseq, m, flags) in run_ctx.config.adversarial.miner_behaviours:
        if m == mid and rseq in (0, run_ctx.round_seq):
            return tuple(flags)
    return ()


def ensure_profile(run_ctx: Any, rc: Any, mid: Any, actual_rate: float) -> Any:
    """S5-1/S5A-3: build the ROUND-BOUND IMMUTABLE profile for ``mid`` if it does not yet exist.

    Split out from the physical-effect application so a profile can be materialised BEFORE range
    sizing (which reported-rate allocation mode requires) as well as at the normal point.
    Idempotent: an existing profile is returned unchanged.
    """
    key = (rc.RoundID, mid)
    existing = run_ctx.behaviour_profiles.get(key)
    if existing is not None:
        return existing
    pol = run_ctx.config.adversarial
    flags = _declared_flags(run_ctx, mid)
    work_fraction = pol.free_rider_work_fraction if "FREE_RIDER" in flags else 1.0
    reported_rate = (actual_rate * pol.reported_hash_rate_multiplier
                     if "HASH_RATE_MISREPORTER" in flags else actual_rate)
    prof = MinerBehaviourProfile(
        MinerID=mid, EntityID=_entity_for(run_ctx, mid), RoundID=rc.RoundID,
        behaviour_set=flags, actual_hash_rate=actual_rate, reported_hash_rate=reported_rate,
        work_fraction=work_fraction, wake_delay_multiplier=1.0,
        solution_release_policy=(pol.solution_release_policy if "SOLUTION_WITHHOLDER" in flags
                                 else "PROMPT_RELEASE"),
        progress_reporting_policy="WITHHOLD" if "PROGRESS_WITHHOLDER" in flags else "HONEST",
        exhaustion_claim_policy="FALSE" if "FALSE_EXHAUSTION_CLAIMER" in flags else "HONEST",
        assignment_split_count=(pol.assignment_split_count if "ASSIGNMENT_SPLITTER" in flags
                                else 1),
        identity_group_id=_entity_for(run_ctx, mid), behaviour_generation=run_ctx.round_seq)
    run_ctx.behaviour_profiles[key] = prof
    return prof


def prematerialise_behaviours(run_ctx: Any, rc: Any, participants: List[Any],
                              rate_of) -> None:
    """S5A-3: build profiles BEFORE range sizing, using a rate callable rather than a search
    state.  Required by reported-rate allocation mode, where the reported rate must be known
    before ranges are computed.  No physical effect is applied here."""
    if not adversarial_enabled(run_ctx):
        return
    build_entities(run_ctx)
    for idx, mid in enumerate(participants):
        ensure_profile(run_ctx, rc, mid, rate_of(idx, mid))


def materialise_behaviours(run_ctx: Any, rc: Any, participants: List[Any]) -> None:
    """S5-1: ensure the ROUND-BOUND IMMUTABLE profile exists for each participant and apply its
    PHYSICAL effects exactly once (free-rider work fraction, misreport bookkeeping).

    The physical search core ALWAYS runs on the actual (effective) hash rate; a reported hash
    rate never alters the physical rate (S5-4/S5A-3).  Replay-safe: physical effects are applied
    at most once per (round, miner)."""
    if not adversarial_enabled(run_ctx):
        return
    build_entities(run_ctx)
    for mid in participants:
        st = rc.search_states.get(mid)
        if st is None:
            continue
        # when the profile was pre-materialised for allocation its actual_hash_rate is
        # authoritative; otherwise the search state's rate is the actual rate.
        prof = ensure_profile(run_ctx, rc, mid, st.hash_rate)
        key = (rc.RoundID, mid)
        if key in run_ctx.adv_physical_applied:          # replay-safe: effects applied once
            continue
        run_ctx.adv_physical_applied.add(key)
        flags = prof.behaviour_set
        actual_rate = prof.actual_hash_rate
        # PHYSICAL effect of free riding: the effective actual rate reduces physical search
        # capacity.  The ground-truth actual rate is preserved on the immutable profile.
        if prof.work_fraction < 1.0:
            st.hash_rate = actual_rate * prof.work_fraction
            run_ctx.adversarial_stats["free_rider_count"] += 1
        else:
            st.hash_rate = actual_rate
        if "HASH_RATE_MISREPORTER" in flags and prof.reported_hash_rate != actual_rate:
            run_ctx.adversarial_stats["hash_rate_misreport_count"] += 1
            run_ctx.adversarial_stats["actual_reported_divergence_count"] += 1
            ratio = prof.reported_hash_rate / actual_rate if actual_rate > 0 else 1.0
            run_ctx.adversarial_stats["allocation_distortion_max_ratio"] = max(
                run_ctx.adversarial_stats["allocation_distortion_max_ratio"], ratio)
        if prof.assignment_split_count > 1:
            run_ctx.adversarial_stats["assignment_split_count"] += 1
        create_subassignments(run_ctx, rc, mid, st, prof)   # S5A-4
    create_virtual_identities(run_ctx, rc)                  # S5A-4
    # arm the q_adv observation hook + take the first observation for this round.
    run_ctx.adversarial_share_hook = lambda t: observe_adversarial_share(run_ctx, t)
    observe_adversarial_share(run_ctx, run_ctx.event_queue.current_event_time)


# --------------------------------------------------------------------- S5A-3 reported allocation
def reported_rate_allocation_enabled(run_ctx: Any) -> bool:
    """S5A-3: is deterministic range sizing driven by REPORTED rates for this run?"""
    return bool(adversarial_enabled(run_ctx)
                and run_ctx.config.adversarial.coordinator_uses_reported_hash_rate)


def allocate_by_reported_rate(run_ctx: Any, rc: Any, domain_size: int,
                              participants: List[Any]) -> Dict[Any, Tuple[int, int]]:
    """S5A-3: size the participants' ranges by their REPORTED hash rates.

    The total nonce domain is unchanged, ranges stay pairwise disjoint and contiguous, and every
    nonce in ``[0, domain_size)`` is covered exactly once.  Only the SIZING uses reported rates —
    the physical search rate remains each miner's actual effective rate, so over-reporting buys a
    larger range but no extra hashing capacity.
    """
    ordered = sorted(participants)
    weights = []
    for mid in ordered:
        prof = run_ctx.behaviour_profiles.get((rc.RoundID, mid))
        w = prof.reported_hash_rate if prof is not None and prof.reported_hash_rate > 0 else 1.0
        weights.append(float(w))
    total_w = sum(weights) or float(len(ordered))
    ranges: Dict[Any, Tuple[int, int]] = {}
    cursor = 0
    for i, mid in enumerate(ordered):
        if i == len(ordered) - 1:
            end = domain_size                            # last participant absorbs the remainder
        else:
            end = cursor + int(domain_size * weights[i] / total_w)
            end = max(cursor, min(end, domain_size))
        ranges[mid] = (cursor, end)
        cursor = end
    run_ctx.adversarial_stats["reported_rate_allocation_rounds"] += 1
    # record the honest-vs-reported sizing distortion (equal split is the honest reference).
    honest_size = domain_size / max(1, len(ordered))
    for mid in ordered:
        lo, hi = ranges[mid]
        run_ctx.adv_allocated_range_size[(rc.RoundID, mid)] = hi - lo
        if honest_size > 0:
            run_ctx.adversarial_stats["allocation_range_size_distortion_max_ratio"] = max(
                run_ctx.adversarial_stats["allocation_range_size_distortion_max_ratio"],
                (hi - lo) / honest_size)
    return ranges


def record_allocation_projection(run_ctx: Any, rc: Any, mid: Any, st: Any) -> None:
    """S5A-3: the completion time the coordinator would PROJECT from the reported rate, against
    the completion time the miner's ACTUAL rate will really produce."""
    if not adversarial_enabled(run_ctx):
        return
    prof = run_ctx.behaviour_profiles.get((rc.RoundID, mid))
    if prof is None:
        return
    span = st.range_end - st.range_start
    projected = span / prof.reported_hash_rate if prof.reported_hash_rate > 0 else None
    actual = span / st.hash_rate if st.hash_rate > 0 else None
    run_ctx.adv_allocation_projection[(rc.RoundID, mid)] = {
        "allocated_range_size": span,
        "reported_hash_rate": prof.reported_hash_rate,
        "actual_hash_rate": st.hash_rate,
        "projected_completion_seconds": projected,
        "actual_completion_seconds": actual,
    }


# --------------------------------------------------------------------- S5A-4 splitting/identities
def create_subassignments(run_ctx: Any, rc: Any, mid: Any, st: Any, prof: Any) -> None:
    """S5A-4: create REAL subassignment records for an ASSIGNMENT_SPLITTER.

    Subranges partition the miner's allocated range exactly (disjoint, union == original), and
    the per-subassignment capacity shares sum to the entity's single actual physical capacity.
    Splitting therefore reorganises how work is accounted; it never multiplies physical
    throughput.  This is an accounting / sensitivity model, NOT a Sybil defence.
    """
    n = prof.assignment_split_count
    if n <= 1:
        return
    eid = _entity_for(run_ctx, mid)
    lo, hi = st.range_start, st.range_end
    span = hi - lo
    if span <= 0:
        return
    n = min(n, span)                                     # never more parts than nonces
    budget = prof.actual_hash_rate                       # the ENTITY's real physical capacity
    share = budget / n
    cursor = lo
    for i in range(n):
        end = hi if i == n - 1 else cursor + span // n
        sub_id = (rc.RoundID, rc.TemplateID_committed, st.AssignmentID, i)
        if sub_id in run_ctx.subassignment_by_id:        # replay-safe
            cursor = end
            continue
        rec = SubAssignmentRecord(
            SubAssignmentID=sub_id, ParentAssignmentID=st.AssignmentID, RoundID=rc.RoundID,
            TemplateID=rc.TemplateID_committed, EntityID=eid, MinerID=mid, index=i,
            range_start=cursor, range_end=end, capacity_share=share,
            entity_capacity_budget=budget,
            lineage_id=run_ctx.slice_of_miner.get((rc.RoundID, mid), st.AssignmentID),
            disposition=Outcome("subassignment_created"))
        run_ctx.subassignments.append(rec)
        run_ctx.subassignment_by_id[sub_id] = rec
        run_ctx.adversarial_stats["subassignment_count"] += 1
        cursor = end
    # capacity conservation: the shares must sum EXACTLY to the entity's physical budget.
    subs = [s for s in run_ctx.subassignments
            if s.RoundID == rc.RoundID and s.ParentAssignmentID == st.AssignmentID]
    if subs:
        resid = abs(sum(s.capacity_share for s in subs) - budget)
        run_ctx.adversarial_stats["subassignment_capacity_residual"] = max(
            run_ctx.adversarial_stats["subassignment_capacity_residual"], resid)


def create_virtual_identities(run_ctx: Any, rc: Any) -> None:
    """S5A-4: materialise explicit virtual identity records bound to one EntityID.

    A virtual identity holds no assignment and no lease and grants NO physical capacity; it
    exists so identity count can be reported separately from real miner/entity count."""
    n = run_ctx.config.adversarial.sybil_identity_count
    if n <= 1:
        return
    for eid, ent in sorted(run_ctx.adversarial_entities.items(), key=lambda kv: str(kv[0])):
        backing = ent.controlled_miner_ids[0] if ent.controlled_miner_ids else None
        for i in range(n):
            vid = (rc.RoundID, eid, i)
            if vid in run_ctx.virtual_identity_by_id:    # replay-safe
                continue
            rec = VirtualIdentityRecord(
                VirtualIdentityID=vid, EntityID=eid, RoundID=rc.RoundID, index=i,
                backing_miner_id=backing, grants_physical_capacity=False,
                disposition=Outcome("virtual_identity_declared"))
            run_ctx.virtual_identities.append(rec)
            run_ctx.virtual_identity_by_id[vid] = rec
            run_ctx.adversarial_stats["virtual_identity_count"] += 1


def entity_physical_capacity(run_ctx: Any, rc: Any, eid: Any) -> float:
    """The entity's TOTAL actual physical capacity this round — the quantity that neither
    assignment splitting nor identity multiplication may increase (S5A-4)."""
    total = 0.0
    for (rid, mid), prof in run_ctx.behaviour_profiles.items():
        if rid == rc.RoundID and _entity_for(run_ctx, mid) == eid:
            st = rc.search_states.get(mid)
            total += st.hash_rate if st is not None else prof.actual_hash_rate
    return total


# --------------------------------------------------------------------- S5A-5 abandonment
def maybe_abandon(run_ctx: Any, rc: Any, st: Any, now: float) -> Optional[Any]:
    """S5A-5: an IDLE_POLICY_DEFECTOR EXECUTES one declared abandonment.

    The miner stops with an uncovered suffix and an ``AbandonmentActionRecord`` is written.  A
    penalty may be charged ONLY against such a record — a profile flag alone is never enough, so
    a round that closes before this executes yields no action and no penalty.
    """
    if not adversarial_enabled(run_ctx):
        return None
    prof = _profile(run_ctx, rc, st.MinerID)
    if prof is None or "IDLE_POLICY_DEFECTOR" not in prof.behaviour_set or st.completed:
        return None
    if st.cursor <= st.range_start or st.cursor >= st.range_end:
        return None                                      # nothing done yet, or genuinely finished
    key = (rc.RoundID, rc.TemplateID_committed, st.MinerID, st.AssignmentID)
    if key in run_ctx.abandonment_by_id:                 # replay-safe: one action per assignment
        return run_ctx.abandonment_by_id[key]
    if not charge_action_budget(run_ctx, rc, "ABANDONMENT"):
        return None
    slice_id = run_ctx.slice_of_miner.get((rc.RoundID, st.MinerID))
    prog = run_ctx.range_progress.get(slice_id) if slice_id else None
    lease_id = prog.current_lease_id if prog is not None else None
    rec = AbandonmentActionRecord(
        ActionID=key, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        EntityID=_entity_for(run_ctx, st.MinerID), MinerID=st.MinerID, LeaseID=lease_id,
        actual_frontier=st.cursor, abandoned_suffix_start=st.cursor,
        abandoned_suffix_end=st.range_end, action_time=now,
        disposition=Outcome("abandonment_executed"))
    run_ctx.abandonment_actions.append(rec)
    run_ctx.abandonment_by_id[key] = rec
    run_ctx.adversarial_stats["abandonment_action_count"] += 1
    run_ctx.adversarial_stats["abandoned_nonce_count"] += rec.abandoned_nonce_count()
    st.completed = True
    st.completion_kind = "INTENTIONALLY_ABANDONED"
    m = run_ctx.miners.get(st.MinerID)
    if m is not None and m.state == "ACTIVE_HASHING":
        run_ctx.apply_miner_state_transition(st.MinerID, "LOW_POWER_LISTEN", now)
    return rec


# --------------------------------------------------------------------- S5-7 delayed wake
def wake_extra_latency(run_ctx: Any, rc: Any, mid: Any, honest_target: float,
                       now: float, request_id: Any = None) -> float:
    """S5-7: extra deterministic wake latency for a DELAYED_WAKE miner (0 otherwise).  Records a
    round-bound, replay-safe DelayedWakeAction; the miner stays WAKING and contributes zero to
    H_effective over the whole actual interval (residency accounts wake energy over it)."""
    if not adversarial_enabled(run_ctx):
        return 0.0
    prof = _profile(run_ctx, rc, mid)
    if prof is None or "DELAYED_WAKE" not in prof.behaviour_set:
        return 0.0
    extra = run_ctx.config.adversarial.delayed_wake_extra_latency
    if extra <= 0:
        return 0.0
    if not charge_action_budget(run_ctx, rc, "DELAYED_WAKE"):
        return 0.0                                       # S5A-7: declared per-round action limit
    # S5A-6: every wake EPISODE gets a distinct identity.  A miner legitimately woken more than
    # once in one round (ordinary wake, then a reassignment or activation wake) must produce
    # DISTINCT action records, so the identity carries a per-(round, miner) wake generation and
    # the request identity that caused this wake.
    ep_key = (rc.RoundID, mid)
    gen = run_ctx.adv_wake_generation.get(ep_key, 0) + 1
    run_ctx.adv_wake_generation[ep_key] = gen
    action_id = (rc.RoundID, rc.TemplateID_committed, _entity_for(run_ctx, mid), mid,
                 "DELAYED_WAKE", gen, request_id)

    def _mk():
        run_ctx.adversarial_stats["delayed_wake_count"] += 1
        return DelayedWakeAction(
            ActionID=action_id, RoundID=rc.RoundID, MinerID=mid,
            honest_expected_wake_time=honest_target,
            adversarial_scheduled_wake_time=honest_target + extra, extra_delay=extra)
    rec = register_action(run_ctx, action_id, _mk)
    run_ctx.delayed_wake_actions[action_id] = rec
    return extra


def complete_delayed_wake(run_ctx: Any, rc: Any, mid: Any, now: float) -> None:
    """Record the actual wake time for the OLDEST pending delayed-wake action of this miner."""
    if not adversarial_enabled(run_ctx):
        return
    for rec in run_ctx.delayed_wake_actions.values():
        if rec.RoundID == rc.RoundID and rec.MinerID == mid and rec.status == "PENDING":
            rec.actual_wake_time = now
            rec.status = "COMPLETED"
            rec.disposition = Outcome("delayed_wake_completed")
            return                                       # one episode per completion


def record_floor_breach_interval(run_ctx: Any, start: float, end: float) -> None:
    """S5A-6: record one CLOSED security-floor breach interval so delayed-wake impact can be
    measured against REAL observations rather than a constant."""
    if not adversarial_enabled(run_ctx) or start is None or end is None or end <= start:
        return
    run_ctx.adv_floor_breach_intervals.append((start, end))


def finalise_delayed_wake_impact(run_ctx: Any, rc: Any, t: float) -> None:
    """S5A-6: compute each delayed-wake action's REAL impact once the round's floor-breach
    intervals are known.

    ``below_floor_overlap`` is the measured overlap of the ADDED waking interval
    ``[honest_expected_wake, actual_wake]`` with the union of observed breach intervals;
    ``another_reserve_activated`` records whether a reserve activation was actually seated inside
    that interval; ``attack_induced_floor_breach_duration`` aggregates the overlaps.  None of
    these is a constant.
    """
    if not adversarial_enabled(run_ctx):
        return
    breaches = interval_union_float(run_ctx.adv_floor_breach_intervals)
    seated = [req for req in run_ctx.activation_requests.values()
              if getattr(req, "RoundID", None) == rc.RoundID]
    for rec in run_ctx.delayed_wake_actions.values():
        if rec.RoundID != rc.RoundID or rec.impact_finalised:
            continue
        rec.impact_finalised = True
        end = rec.actual_wake_time if rec.actual_wake_time is not None else t
        lo, hi = rec.honest_expected_wake_time, end
        if hi <= lo:
            continue
        overlap = 0.0
        for b_lo, b_hi in breaches:
            overlap += max(0.0, min(hi, b_hi) - max(lo, b_lo))
        rec.below_floor_overlap = overlap
        run_ctx.adversarial_stats["attack_induced_floor_breach_duration"] += overlap
        for req in seated:
            seat_t = getattr(req, "seated_time", None)
            if seat_t is not None and lo <= seat_t <= hi and req.MinerID != rec.MinerID:
                rec.another_reserve_activated = True
                break
        P_wake = run_ctx.config.per_miner_power("WAKING")
        rec.incremental_wake_energy_j = P_wake * rec.extra_delay


def interval_union_float(intervals) -> List[Tuple[float, float]]:
    """Canonical non-overlapping union over REAL-valued (time) intervals."""
    out: List[List[float]] = []
    for lo, hi in sorted(intervals):
        if hi <= lo:
            continue
        if out and lo <= out[-1][1]:
            out[-1][1] = max(out[-1][1], hi)
        else:
            out.append([lo, hi])
    return [(lo, hi) for lo, hi in out]


# --------------------------------------------------------------------- S5-6 solution withholding
def maybe_withhold_solution(run_ctx: Any, rc: Any, st: Any, winner_nonce: int,
                            digest: int, now: float) -> bool:
    """S5-6: consult the finder's behaviour profile BEFORE accepting a valid block.

    Returns True when the solution is WITHHELD (the caller must NOT seat acceptance).  Records a
    WithheldSolutionRecord; DELAYED_RELEASE schedules a WithheldSolutionReleaseEvent at
    found_time + delay; NEVER_RELEASE keeps it hidden until closure.  Withholding NEVER changes
    the target or difficulty; the model does not claim withholding is detectable in a real
    deployment."""
    if not adversarial_enabled(run_ctx):
        return False
    prof = _profile(run_ctx, rc, st.MinerID)
    if prof is None or prof.solution_release_policy == "PROMPT_RELEASE":
        return False
    pol = run_ctx.config.adversarial
    ws_id = (rc.RoundID, rc.TemplateID_committed, st.MinerID, st.AssignmentID, winner_nonce)
    if ws_id in run_ctx.withheld_solutions:              # replay-safe
        return True
    policy = prof.solution_release_policy
    scheduled = (now + pol.solution_withholding_delay) if policy == "DELAYED_RELEASE" else None
    rec = WithheldSolutionRecord(
        WithheldSolutionID=ws_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        MinerID=st.MinerID, AssignmentID=st.AssignmentID,
        assignment_version=st.assignment_version, nonce=winner_nonce, digest=digest,
        found_time=now, release_policy=policy, scheduled_release_time=scheduled)
    run_ctx.withheld_solutions[ws_id] = rec
    run_ctx.adversarial_stats["solution_withholding_count"] += 1
    action_id = (rc.RoundID, rc.TemplateID_committed, _entity_for(run_ctx, st.MinerID),
                 st.MinerID, "SOLUTION_WITHHOLDER", winner_nonce)
    register_action(run_ctx, action_id, lambda: rec)
    if policy == "DELAYED_RELEASE":
        eq = run_ctx.event_queue
        payload = {"WithheldSolutionID": ws_id, "RoundID_at_seat": rc.RoundID,
                   "TemplateID_at_seat": rc.TemplateID_committed, "MinerID": st.MinerID,
                   "nonce": winner_nonce}
        r = ScheduleEvent(eq, rc, "WithheldSolutionReleaseEvent", scheduled,
                          "WITHHELD_SOLUTION_RELEASE", payload, ordinary_dispatch_origin(eq))
        rec.release_event_ref = r.event_ref if r.kind == "scheduled" else None
    return True


# --------------------------------------------------------------------- S5-5 progress / exhaustion
def audit_claim(run_ctx: Any, rc: Any, lease_id: Any, mid: Any, actual_frontier: int,
                reported_frontier: int, claim_type: str) -> ProgressClaim:
    """S5-3/S5-5: run one miner claim through the MODELED audit abstraction and record it.

    ``detected`` follows a deterministic seeded draw against ``audit_detection_probability``;
    a detected claim is rejected (real state retained), an undetected claim is accepted (its
    reported value becomes the accepted value, ground truth preserved separately).  Exact
    replay is idempotent."""
    pol = run_ctx.config.adversarial
    claim_id = (rc.RoundID, rc.TemplateID_committed, lease_id, mid, claim_type, reported_frontier)
    if claim_id in run_ctx.progress_claim_by_id:
        return run_ctx.progress_claim_by_id[claim_id]
    draw = audit_draw(pol.deterministic_seed, claim_id)
    p = pol.audit_detection_probability
    is_false = reported_frontier > actual_frontier or reported_frontier < actual_frontier
    detected = bool(is_false and draw < p)
    accepted = not detected
    accepted_frontier = actual_frontier if detected else reported_frontier
    claim = ProgressClaim(
        ClaimID=claim_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        LeaseID=lease_id, MinerID=mid, actual_frontier=actual_frontier,
        reported_frontier=reported_frontier, claim_type=claim_type, audit_draw=draw,
        detection_probability=p, detected=detected, accepted=accepted,
        accepted_frontier=accepted_frontier,
        disposition=Outcome("claim_detected" if detected else "claim_accepted"))
    run_ctx.progress_claims.append(claim)
    run_ctx.progress_claim_by_id[claim_id] = claim
    if reported_frontier != actual_frontier:
        run_ctx.adversarial_stats["actual_reported_divergence_count"] += 1
    if accepted_frontier != actual_frontier:
        run_ctx.adversarial_stats["reported_accepted_divergence_count"] += 1
    return claim


def maybe_false_exhaustion(run_ctx: Any, rc: Any, st: Any, now: float) -> Optional[Outcome]:
    """S5-5: a FALSE_EXHAUSTION_CLAIMER that has NOT actually reached range_end claims exhaustion.

    Returns an Outcome (and idles / records a coverage gap) when the claim is ACCEPTED so the
    caller stops the miner's honest search; returns None (miner continues honestly) when the
    claim is detected+rejected or the miner is honest.  A round with an accepted false-exhaustion
    coverage gap must NOT be labelled FULL_DOMAIN_EXHAUSTED_NO_BLOCK (enforced by
    ``adversarial_coverage_gap`` in ``_maybe_terminate_no_block``)."""
    if not adversarial_enabled(run_ctx):
        return None
    prof = _profile(run_ctx, rc, st.MinerID)
    if prof is None or prof.exhaustion_claim_policy != "FALSE" or st.completed:
        return None
    if st.cursor >= st.range_end:                        # genuinely exhausted — nothing false
        return None
    slice_id = run_ctx.slice_of_miner.get((rc.RoundID, st.MinerID))
    lease = None
    if slice_id is not None:
        prog = run_ctx.range_progress.get(slice_id)
        lease = run_ctx.range_leases.get(prog.current_lease_id) if prog is not None else None
    lease_id = lease.LeaseID if lease is not None else None
    # S5A-7: derive the reported claim DETERMINISTICALLY from the declared offset, capped to the
    # range end.  ``false_exhaustion_claims_range_end`` (the default) models the strongest
    # overstatement; otherwise the miner overstates by exactly ``false_exhaustion_claim_offset``
    # nonces.  A zero offset with range-end claiming disabled reports the TRUTH, which is not a
    # false claim and creates no coverage gap.
    pol = run_ctx.config.adversarial
    if pol.false_exhaustion_claims_range_end:
        reported = st.range_end
    else:
        reported = min(st.range_end, st.cursor + pol.false_exhaustion_claim_offset)
    if reported <= st.cursor:                            # a truthful claim is not a false claim
        return None
    if not charge_action_budget(run_ctx, rc, "FALSE_EXHAUSTION"):
        return None                                      # S5A-7: declared per-round action limit
    run_ctx.adversarial_stats["false_exhaustion_attempted"] += 1
    claim = audit_claim(run_ctx, rc, lease_id, st.MinerID, st.cursor, reported,
                        "EXHAUSTION_CLAIM")
    if claim.detected:
        run_ctx.adversarial_stats["false_exhaustion_detected"] += 1
        # rejected: retain the real lease/progress state; the miner continues honestly.
        return None
    # accepted false exhaustion: preserve actual ground truth, record the coverage gap.
    run_ctx.adversarial_stats["false_exhaustion_accepted"] += 1
    gap = reported - st.cursor
    run_ctx.adversarial_stats["coverage_gap_nonce_count"] += gap
    run_ctx.adv_round_coverage_gap[rc.RoundID] = \
        run_ctx.adv_round_coverage_gap.get(rc.RoundID, 0) + gap
    run_ctx.adv_actual_frontier[slice_id] = st.cursor
    st.completed = True
    st.completion_kind = "FALSE_EXHAUSTION_ACCEPTED"
    m = run_ctx.miners.get(st.MinerID)
    if m is not None and m.state == "ACTIVE_HASHING":
        run_ctx.apply_miner_state_transition(st.MinerID, "LOW_POWER_LISTEN", now)
    return Outcome("false_exhaustion_accepted", MinerID=st.MinerID,
                   coverage_gap_nonce_count=gap)


def round_has_coverage_gap(run_ctx: Any, rc: Any) -> bool:
    """S5-5/S5-11: True when this round holds an accepted-false-exhaustion coverage gap OR a
    withheld valid solution — either forbids a clean FULL_DOMAIN_EXHAUSTED_NO_BLOCK label."""
    if not adversarial_enabled(run_ctx):
        return False
    gap = run_ctx.adv_round_coverage_gap.get(rc.RoundID, 0) > 0 or \
        any(w.RoundID == rc.RoundID and w.status == "WITHHELD"
            for w in run_ctx.withheld_solutions.values())
    if gap and rc.RoundID not in run_ctx.adv_gap_rounds_counted:
        run_ctx.adv_gap_rounds_counted.add(rc.RoundID)
        run_ctx.adversarial_stats["adversarial_coverage_gap_round_count"] += 1
    return gap


def apply_progress_withholding(run_ctx: Any, rc: Any, prog: Any, pred_lease_id: Any,
                               t: float) -> Optional[int]:
    """S5A-1: a PROGRESS_WITHHOLDER under-reports how far it actually searched.

    Applied at the reassignment boundary, where the reported frontier is the value the protocol
    acts on.  The under-report goes through the SAME modeled audit as any other claim.

    CRITICAL (S5A-1): recording an accepted frontier BELOW the actual frontier NEVER rewinds the
    accepted Stage-4C authoritative physical ``RangeProgress.committed_frontier``.  That frontier
    is monotonic ground truth and is left untouched; the protocol's ACCEPTED view lives in a
    separate ``AcceptedFrontierRecord``.  Returns the reassignment start (the accepted frontier)
    when an under-report was accepted, else ``None``.
    """
    if not adversarial_enabled(run_ctx):
        return None
    lease = run_ctx.range_leases.get(pred_lease_id)
    if lease is None:
        return None
    prof = _profile(run_ctx, rc, lease.MinerID)
    if prof is None or prof.progress_reporting_policy != "WITHHOLD":
        return None
    rec_id = (rc.RoundID, rc.TemplateID_committed, prog.RangeSliceID, pred_lease_id,
              lease.assignment_version)
    existing = run_ctx.accepted_frontier_by_id.get(rec_id)
    if existing is not None:                             # replay: same decision, no new effect
        return existing.reassignment_start
    actual = prog.committed_frontier                     # the PHYSICAL committed truth
    done = actual - lease.lease_start_nonce
    if done <= 0:
        return None
    withheld = int(run_ctx.config.adversarial.progress_withholding_fraction * done)
    reported = actual - withheld
    if reported >= actual:
        return None
    if not charge_action_budget(run_ctx, rc, "PROGRESS_WITHHOLD"):
        return None                                      # S5A-7: declared per-round action limit
    claim = audit_claim(run_ctx, rc, pred_lease_id, lease.MinerID, actual, reported,
                        "PROGRESS_REPORT")
    accepted = actual if claim.detected else reported    # detected => the real frontier stands
    rec = AcceptedFrontierRecord(
        RecordID=rec_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        RangeSliceID=prog.RangeSliceID, LeaseID=pred_lease_id,
        assignment_version=lease.assignment_version, MinerID=lease.MinerID,
        EntityID=_entity_for(run_ctx, lease.MinerID), actual_frontier=actual,
        reported_frontier=reported, accepted_frontier=accepted,
        physical_committed_frontier_at_decision=prog.committed_frontier,
        detected=claim.detected,
        disposition=Outcome("accepted_frontier_rejected" if claim.detected
                            else "accepted_frontier_below_actual"))
    run_ctx.accepted_frontier_records.append(rec)
    run_ctx.accepted_frontier_by_id[rec_id] = rec
    run_ctx.adv_actual_frontier[prog.RangeSliceID] = actual
    run_ctx.adversarial_stats["accepted_frontier_record_count"] += 1
    if claim.detected:
        return None
    run_ctx.adversarial_stats["accepted_below_actual_count"] += 1
    run_ctx.adv_reeval_boundary[prog.RangeSliceID] = accepted
    rec.reassignment_start = accepted
    rec.reevaluation_interval = (accepted, actual)
    # The successor re-searches [accepted, actual).  Open an EXPLICIT re-evaluation window so the
    # successor can legitimately execute below the physical frontier WITHOUT that frontier ever
    # being rewound (S5A-1).
    run_ctx.adv_reeval_window[prog.RangeSliceID] = {
        "accepted": accepted, "actual": actual, "cursor": accepted,
        "RoundID": rc.RoundID, "TemplateID": rc.TemplateID_committed, "RecordID": rec_id}
    return accepted


def expected_cursor_for_lease(run_ctx: Any, prog: Any) -> int:
    """S5A-1: the cursor a HashWorkEvent must carry for this slice.

    Normally the accepted Stage-4C authoritative physical frontier — identical to the accepted
    behaviour.  While an adversarial re-evaluation window is open the successor is legitimately
    working BELOW that frontier, so the window's own cursor is authoritative for the guard.
    """
    if not adversarial_enabled(run_ctx):
        return prog.committed_frontier
    w = run_ctx.adv_reeval_window.get(prog.RangeSliceID)
    if w is not None and w["cursor"] < w["actual"]:
        return w["cursor"]
    return prog.committed_frontier


def note_physical_commit(run_ctx: Any, rc: Any, slice_id: Any, lo: int, hi: int,
                         mid: Any) -> None:
    """S5A-1/S5A-2: record one PHYSICAL evaluation interval and advance any open re-evaluation
    window.  Work inside the window is adversarially-induced RE-evaluation: it is real physical
    work (visible in the execution and energy ledgers) but it is not new coverage."""
    if not adversarial_enabled(run_ctx):
        return
    run_ctx.adversarial_stats["physical_evaluation_count"] += max(0, hi - lo)
    w = run_ctx.adv_reeval_window.get(slice_id)
    if w is None:
        return
    overlap = max(0, min(hi, w["actual"]) - max(lo, w["accepted"]))
    if overlap > 0:
        run_ctx.adversarial_stats["adversarial_reevaluation_count"] += overlap
    if hi > w["cursor"]:
        w["cursor"] = hi
    if w["cursor"] >= w["actual"]:                       # window consumed; back to normal flow
        run_ctx.adv_reeval_window.pop(slice_id, None)


def frontier_reconciliation(run_ctx: Any) -> List[Dict[str, Any]]:
    """S5A-1: one auditable row per adversarial claim showing the actual, reported and accepted
    frontiers, the reassignment start and the physical evaluation ledger coverage."""
    rows = []
    for rec in run_ctx.accepted_frontier_records:
        physical = sorted((r.interval_start, r.interval_end) for r in run_ctx.evaluation_ledger
                          if r.RoundID == rec.RoundID and r.RangeSliceID == rec.RangeSliceID)
        rows.append({
            "RecordID": list(rec.RecordID) if isinstance(rec.RecordID, tuple) else rec.RecordID,
            "MinerID": rec.MinerID, "EntityID": rec.EntityID,
            "actual_frontier": rec.actual_frontier,
            "reported_frontier": rec.reported_frontier,
            "accepted_frontier": rec.accepted_frontier,
            "reassignment_start": rec.reassignment_start,
            "physical_committed_frontier_at_decision":
                rec.physical_committed_frontier_at_decision,
            "reevaluation_interval": list(rec.reevaluation_interval)
                if rec.reevaluation_interval else None,
            "detected": rec.detected,
            "physical_evaluation_intervals": [list(i) for i in physical],
        })
    return rows


def note_reassignment_reeval(run_ctx: Any, rc: Any, slice_id: Any, accepted_frontier: int,
                             actual_frontier: int) -> None:
    """S5-5: when a reassignment restarts from an accepted frontier BELOW the actual searched
    frontier (progress withholding), record the adversarially-induced physical re-evaluation
    explicitly — do NOT hide it and do NOT corrupt actual ground truth."""
    if not adversarial_enabled(run_ctx):
        return
    if actual_frontier > accepted_frontier:
        run_ctx.adversarial_stats["adversarial_duplicate_evaluation_count"] += \
            (actual_frontier - accepted_frontier)
        run_ctx.adversarial_stats["progress_withholding_count"] += 1


# --------------------------------------------------------------------- S5-9 invalid / out-of-range
def record_invalid_action(run_ctx: Any, rc: Any, mid: Any, action_type: str,
                          attempted_nonce: Optional[int], attempted_assignment_id: Any,
                          now: float) -> InvalidActionRecord:
    """S5-9: record a REJECTED invalid/out-of-range attempt.  It creates no accepted ledger
    entry, no accepted frontier progress and no reward — only invalid-message penalty
    eligibility.  Replay-idempotent."""
    inv_id = (rc.RoundID, rc.TemplateID_committed, mid, action_type, attempted_nonce,
              attempted_assignment_id)
    if inv_id in run_ctx.invalid_actions:
        return run_ctx.invalid_actions[inv_id]
    rec = InvalidActionRecord(
        InvalidActionID=inv_id, RoundID=rc.RoundID, TemplateID=rc.TemplateID_committed,
        MinerID=mid, action_type=action_type, attempted_nonce=attempted_nonce,
        attempted_assignment_id=attempted_assignment_id, detected_at=now, rejected=True,
        penalty_eligible=True, disposition=Outcome("invalid_action_rejected"))
    run_ctx.invalid_actions[inv_id] = rec
    run_ctx.adversarial_stats["invalid_action_rejection_count"] += 1
    if action_type == "OUT_OF_RANGE":
        run_ctx.adversarial_stats["out_of_range_attempt_count"] += 1
    return rec


def maybe_out_of_range_attempt(run_ctx: Any, rc: Any, st: Any, now: float) -> Optional[Any]:
    """S5-9: an OUT_OF_RANGE_ACTOR attempts one nonce outside its own assigned range.

    The attempt is REJECTED by range ownership before any accounting: it never enters the
    evaluation ledger, never advances a committed frontier and never earns a reward — it only
    becomes invalid-message penalty eligible.  Returns the record when an attempt was made."""
    if not adversarial_enabled(run_ctx):
        return None
    prof = _profile(run_ctx, rc, st.MinerID)
    if prof is None or "OUT_OF_RANGE_ACTOR" not in prof.behaviour_set:
        return None
    attempted = st.range_end + run_ctx.config.adversarial.out_of_range_nonce_offset
    if st.range_start <= attempted < st.range_end:        # not actually out of range
        return None
    return record_invalid_action(run_ctx, rc, st.MinerID, "OUT_OF_RANGE", attempted,
                                 st.AssignmentID, now)


# --------------------------------------------------------------------- S5-11 q_adv(t)
def observe_adversarial_share(run_ctx: Any, t: float) -> None:
    """S5-11: piecewise-constant q_adv(t) accumulation over ACTUAL active hash rates.

    q_adv(t) = H_adversarial(t) / H_active(t) when H_active(t) > 0, else NA (never compared).
    The interval [last_time, t] is credited with the PREVIOUS interval's q / active flags so
    the accumulation is exact and causal."""
    if not adversarial_enabled(run_ctx) or t is None:
        return                                               # no event time => nothing to credit
    state = run_ctx.q_adv_state
    if state["last_time"] is not None and t > state["last_time"]:
        dt = t - state["last_time"]
        if state["last_active"] > 0 and state["last_q"] is not None:
            state["q_time_integral"] += state["last_q"] * dt
            state["active_duration"] += dt
            if state["last_q"] >= run_ctx.config.adversarial.q_adv_threshold:
                state["above_threshold_duration"] += dt
        else:
            state["na_duration"] += dt
    # snapshot the CURRENT composition using actual active hash rates.
    h_adv = h_active = 0.0
    rc = run_ctx.current_round_context
    states = getattr(rc, "search_states", {}) if rc is not None else {}
    for mid, st in states.items():
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":
            continue
        rate = st.hash_rate                             # ACTUAL (effective) physical rate
        h_active += rate
        if is_adversarial_miner(run_ctx, mid):
            h_adv += rate
    q = (h_adv / h_active) if h_active > 0 else None
    state["last_time"] = t
    state["last_q"] = q
    state["last_active"] = h_active
    if q is not None:
        state["max_q"] = q if state["max_q"] is None else max(state["max_q"], q)


def q_adv_summary(run_ctx: Any) -> Dict[str, Any]:
    """S5-11: the reportable q_adv metrics.  time_weighted_q_adv is NA (None) when no active
    interval was ever observed (H_active == 0 throughout)."""
    s = run_ctx.q_adv_state
    tw = (s["q_time_integral"] / s["active_duration"]) if s["active_duration"] > 0 else None
    return {"maximum_q_adv": s["max_q"], "time_weighted_q_adv": tw,
            "duration_above_q_adv_threshold": s["above_threshold_duration"],
            "q_adv_active_duration": s["active_duration"], "q_adv_na_duration": s["na_duration"]}


# --------------------------------------------------------------------- S5-10 incentive ledger
def _emit(run_ctx: Any, rc: Any, entity_id: Any, mid: Any, component: str, sign: int,
          amount: float, source_event_id: Any, range_lineage_id: Any,
          eligibility_reason: str, dedup_key: Any) -> Optional[IncentiveLedgerEntry]:
    """One replay-idempotent ledger write (S5-10).  A duplicate deduplication_key is ignored
    (no reward/penalty is ever counted twice)."""
    if dedup_key in run_ctx.incentive_ledger_by_key:
        return None
    run_ctx.incentive_entry_seq += 1
    entry = IncentiveLedgerEntry(
        EntryID=(rc.RoundID, run_ctx.incentive_entry_seq), RoundID=rc.RoundID,
        TemplateID=rc.TemplateID_committed, EntityID=entity_id, MinerID=mid,
        component=component, source_event_id=source_event_id, range_lineage_id=range_lineage_id,
        amount=amount, sign=sign, eligibility_reason=eligibility_reason,
        deduplication_key=dedup_key, disposition=Outcome("incentive_entry"))
    run_ctx.incentive_ledger.append(entry)
    run_ctx.incentive_ledger_by_key[dedup_key] = entry
    return entry


def finalise_incentives(run_ctx: Any, rc: Any, t: float) -> None:
    """S5-10: emit the round's reward + penalty ledger entries at closure.

    WORK_REWARD is based ONLY on unique accepted committed evaluations in the executable
    evaluation ledger, deduplicated by (RangeSliceID/assignment lineage, interval) — one reward
    per unique accepted physical evaluation, never per synthetic assignment split or extra
    identity.  Both the NAIVE-identity and ENTITY/LINEAGE-DEDUPLICATED reward totals are computed
    so the amplification exposure is measured at both levels (S5-8)."""
    if not incentive_enabled(run_ctx):
        return
    ip = run_ctx.config.incentive
    st_stats = run_ctx.adversarial_stats

    # ---- WORK_REWARD over the UNION of unique physical nonce positions (S5A-2) ----
    # An exact-interval key is NOT sufficient: partially overlapping intervals such as [0,80)
    # and [40,80) are DIFFERENT keys and would be rewarded twice (120 positions instead of 80).
    # Reward is therefore computed from the canonical non-overlapping interval UNION per
    # (RoundID, TemplateID, range lineage), so one nonce position earns at most one work reward
    # per template and adversarially-induced re-evaluation earns nothing extra.  The physical
    # re-evaluation itself remains fully visible in the execution and energy ledgers.
    raw_by_lineage: Dict[Any, List[Tuple[int, int]]] = {}
    miner_of_lineage: Dict[Any, Any] = {}
    physical_positions = 0
    for rec in run_ctx.evaluation_ledger:
        if rec.RoundID != rc.RoundID:
            continue
        lineage = rec.RangeSliceID if rec.RangeSliceID is not None else rec.AssignmentID
        raw_by_lineage.setdefault(lineage, []).append((rec.interval_start, rec.interval_end))
        miner_of_lineage.setdefault(lineage, rec.MinerID)
        physical_positions += max(0, rec.interval_end - rec.interval_start)
    union_by_lineage = {lin: interval_union(iv) for lin, iv in raw_by_lineage.items()}
    unique_positions = sum(hi - lo for u in union_by_lineage.values() for lo, hi in u)
    rewarded_positions = 0
    for lineage, union in sorted(union_by_lineage.items(), key=lambda kv: str(kv[0])):
        mid = miner_of_lineage[lineage]
        eid = _entity_for(run_ctx, mid)
        for lo, hi in union:
            entry = _emit(run_ctx, rc, eid, mid, "WORK_REWARD", +1, ip.r_work * (hi - lo),
                          source_event_id=(lineage, lo, hi), range_lineage_id=lineage,
                          eligibility_reason="unique_physical_nonce_union",
                          dedup_key=("WORK", rc.RoundID, rc.TemplateID_committed,
                                     lineage, lo, hi))
            if entry is not None:
                st_stats["work_reward_total"] += entry.amount
                rewarded_positions += (hi - lo)
    st_stats["unique_rewarded_nonce_count"] += rewarded_positions
    st_stats["duplicate_work_reward_prevented_count"] += max(0, physical_positions
                                                             - unique_positions)
    # exact reconciliation: the ledger's rewarded position count must equal the union cardinality.
    st_stats["work_reward_union_residual"] = max(
        st_stats["work_reward_union_residual"],
        abs(float(rewarded_positions) - float(unique_positions)))

    # ---- naive vs deduplicated entity accounting (S5-8) ----
    # BOTH views use the SAME physical work definition (the unique-nonce union); they differ only
    # in whether an entity's identities / assignment splits are collapsed.
    naive_total = 0.0
    dedup_entity_total = 0.0
    entity_work: Dict[Any, float] = {}
    for lineage, union in union_by_lineage.items():
        mid = miner_of_lineage[lineage]
        eid = _entity_for(run_ctx, mid)
        credit = ip.r_work * sum(hi - lo for lo, hi in union)
        entity_work[eid] = entity_work.get(eid, 0.0) + credit
    for eid, amt in entity_work.items():
        dedup_entity_total += amt
        ent = run_ctx.adversarial_entities.get(eid)
        if ent is None or not adversarial_enabled(run_ctx):
            # an undeclared single-identity miner multiplies nothing.  Crediting it with the
            # adversary's declared identity count would attribute the exposure to the wrong
            # entity and overstate the aggregate.
            naive_total += amt
            continue
        # amplification factor for THIS entity = its widest per-round assignment split x the
        # number of identities it actually controls (at least its declared Sybil count).
        split = 1
        for mid in ent.controlled_miner_ids:
            p = run_ctx.behaviour_profiles.get((rc.RoundID, mid))
            if p is not None:
                split = max(split, p.assignment_split_count)
        identities = max(len(ent.controlled_miner_ids),
                         run_ctx.config.adversarial.sybil_identity_count)
        naive_total += amt * max(1, split) * max(1, identities)
    st_stats["naive_identity_reward_total"] += naive_total
    st_stats["deduplicated_entity_reward_total"] += dedup_entity_total

    # ---- AVAILABILITY_REWARD over sanctioned availability residency ----
    if ip.r_avail > 0:
        for mid in sorted(run_ctx.miners.keys()):
            resid = availability_residency(run_ctx, mid, t)
            snap = run_ctx.availability_snapshot.get((rc.RoundID, mid), 0.0)
            delta = max(0.0, resid - snap)
            if delta <= 0:
                continue
            eid = _entity_for(run_ctx, mid)
            entry = _emit(run_ctx, rc, eid, mid, "AVAILABILITY_REWARD", +1, ip.r_avail * delta,
                          source_event_id=("AVAIL", mid), range_lineage_id=None,
                          eligibility_reason="sanctioned_availability_residency",
                          dedup_key=("AVAIL", rc.RoundID, mid))
            if entry is not None:
                st_stats["availability_reward_total"] += entry.amount

    # ---- WINNER_REWARD only to the solver of the accepted block ----
    if ip.r_win > 0 and rc.block_accepted and rc.winner_miner_id is not None:
        mid = rc.winner_miner_id
        eid = _entity_for(run_ctx, mid)
        entry = _emit(run_ctx, rc, eid, mid, "WINNER_REWARD", +1, ip.r_win,
                      source_event_id=("WIN", rc.RoundID), range_lineage_id=None,
                      eligibility_reason="accepted_block_solver",
                      dedup_key=("WIN", rc.RoundID))
        if entry is not None:
            st_stats["winner_reward_total"] += entry.amount

    # ---- RESERVE_ACTIVATION_REWARD once per completed activation request ----
    if ip.r_reserve > 0:
        for req in run_ctx.activation_requests.values():
            if req.RoundID != rc.RoundID or req.status != "COMPLETED":
                continue
            eid = _entity_for(run_ctx, req.MinerID)
            entry = _emit(run_ctx, rc, eid, req.MinerID, "RESERVE_ACTIVATION_REWARD", +1,
                          ip.r_reserve, source_event_id=req.ReserveActivationRequestID,
                          range_lineage_id=None,
                          eligibility_reason="completed_reserve_activation",
                          dedup_key=("RESV", req.ReserveActivationRequestID))
            if entry is not None:
                st_stats["reserve_activation_reward_total"] += entry.amount

    # ---- REASSIGNMENT_REWARD once per completed reassignment (per lineage/request) ----
    if ip.r_reassign > 0:
        for req in run_ctx.reassignment_requests.values():
            if req.RoundID != rc.RoundID or req.status != "COMPLETED":
                continue
            eid = _entity_for(run_ctx, req.new_MinerID)
            entry = _emit(run_ctx, rc, eid, req.new_MinerID, "REASSIGNMENT_REWARD", +1,
                          ip.r_reassign, source_event_id=req.RangeReassignmentRequestID,
                          range_lineage_id=req.RangeSliceID,
                          eligibility_reason="completed_reassignment_service",
                          dedup_key=("REASSIGN", req.RangeReassignmentRequestID))
            if entry is not None:
                st_stats["reassignment_reward_total"] += entry.amount

    # ---- FALSE_CLAIM_PENALTY only for a modeled-audit-detected false claim ----
    if ip.q_false > 0:
        for claim in run_ctx.progress_claims:
            if claim.RoundID != rc.RoundID or not claim.detected:
                continue
            eid = _entity_for(run_ctx, claim.MinerID)
            entry = _emit(run_ctx, rc, eid, claim.MinerID, "FALSE_CLAIM_PENALTY", -1, ip.q_false,
                          source_event_id=claim.ClaimID, range_lineage_id=claim.LeaseID,
                          eligibility_reason="detected_false_claim",
                          dedup_key=("FALSE", claim.ClaimID))
            if entry is not None:
                st_stats["false_claim_penalty_total"] += entry.amount

    # ---- INVALID_MESSAGE_PENALTY only for a rejected invalid/out-of-range action ----
    if ip.q_invalid > 0:
        for inv in run_ctx.invalid_actions.values():
            if inv.RoundID != rc.RoundID or not inv.penalty_eligible:
                continue
            eid = _entity_for(run_ctx, inv.MinerID)
            entry = _emit(run_ctx, rc, eid, inv.MinerID, "INVALID_MESSAGE_PENALTY", -1,
                          ip.q_invalid, source_event_id=inv.InvalidActionID,
                          range_lineage_id=None, eligibility_reason="rejected_invalid_action",
                          dedup_key=("INVALID", inv.InvalidActionID))
            if entry is not None:
                st_stats["invalid_message_penalty_total"] += entry.amount

    # ---- ABANDONMENT_PENALTY only against an EXECUTED abandonment action (S5A-5) ----
    # A behaviour flag in a profile is NOT an abandonment.  The penalty is charged strictly
    # per AbandonmentActionRecord, so a round that closes before the action executes yields no
    # penalty at all.  Crash and failure paths never create such a record unless explicitly
    # configured to be penalised.
    if ip.q_abandon > 0:
        for rec in run_ctx.abandonment_actions:
            if rec.RoundID != rc.RoundID or not rec.penalty_eligible:
                continue
            entry = _emit(run_ctx, rc, rec.EntityID, rec.MinerID, "ABANDONMENT_PENALTY", -1,
                          ip.q_abandon, source_event_id=rec.ActionID,
                          range_lineage_id=rec.LeaseID,
                          eligibility_reason="executed_intentional_abandonment",
                          dedup_key=("ABANDON", rec.ActionID))
            if entry is not None:
                st_stats["abandonment_penalty_total"] += entry.amount
        # audit: a declared defector that never executed an action must never be charged.
        for (rid, m_id), prof in run_ctx.behaviour_profiles.items():
            if rid != rc.RoundID or "IDLE_POLICY_DEFECTOR" not in prof.behaviour_set:
                continue
            executed = any(r.RoundID == rc.RoundID and r.MinerID == m_id
                           for r in run_ctx.abandonment_actions)
            charged = any(e.component == "ABANDONMENT_PENALTY" and e.MinerID == m_id
                          and e.RoundID == rc.RoundID for e in run_ctx.incentive_ledger)
            if charged and not executed:
                st_stats["abandonment_penalty_without_action_count"] += 1


# --------------------------------------------------------------------- S5-12 round closure
def close_adversarial_round(run_ctx: Any, rc: Any, t: float) -> None:
    """S5-12: terminalise every Stage-5 action for the closing round so nothing can affect the
    next round.  Cancel queued delayed-release events; mark withheld solutions / claims / wake
    actions terminal; preserve all audit + incentive ledgers (S5-10)."""
    if not adversarial_enabled(run_ctx):
        # the incentive layer is independently switchable (S5-13 needs an all-honest,
        # incentive-enabled control), so the ledger still finalises for the closing round.
        finalise_incentives(run_ctx, rc, t)
        return
    eq = run_ctx.event_queue
    for ws in run_ctx.withheld_solutions.values():
        if ws.RoundID != rc.RoundID:
            continue
        if ws.status == "WITHHELD":
            if ws.release_event_ref is not None:
                rec = eq.queued_event_registry.get(ws.release_event_ref)
                if rec is not None and rec.queue_status == "QUEUED":
                    CancelQueuedEvent(eq, run_ctx, ws.release_event_ref,
                                      cancellation_reason="round_closed")
            ws.status = "HIDDEN_AT_CLOSE" if ws.release_policy == "NEVER_RELEASE" \
                else "CANCELLED_AT_CLOSE"
            ws.disposition = Outcome("withheld_solution_terminal_at_close")
            # S5A-7: an accepted block closed the round before this solution was ever released,
            # so the withholder demonstrably lost the race to an alternative solution.
            if rc.block_accepted and rc.winner_miner_id != ws.MinerID:
                ws.alternative_solution_won = True
                run_ctx.adversarial_stats["withheld_alternative_solution_won_count"] += 1
            if ws.release_policy == "NEVER_RELEASE":
                run_ctx.adversarial_stats["withheld_never_released_count"] += 1
    for rec in run_ctx.delayed_wake_actions.values():
        if rec.RoundID == rc.RoundID and rec.status == "PENDING":
            rec.status = "CANCELLED_AT_CLOSE"
            rec.disposition = Outcome("delayed_wake_terminal_at_close")
    for claim in run_ctx.progress_claims:
        if claim.RoundID == rc.RoundID and claim.disposition is None:
            claim.disposition = Outcome("claim_terminal_at_close")
    for rec in run_ctx.abandonment_actions:              # S5A-5: terminalise executed actions
        if rec.RoundID == rc.RoundID and rec.status == "EXECUTED":
            rec.status = "TERMINAL_AT_CLOSE"
    # S5A-6: measure each delayed wake's REAL floor impact now that this round's breach
    # intervals are complete, then close any still-open re-evaluation window.
    finalise_delayed_wake_impact(run_ctx, rc, t)
    for sid in [s for s, w in run_ctx.adv_reeval_window.items() if w["RoundID"] == rc.RoundID]:
        run_ctx.adv_reeval_window.pop(sid, None)
    # finalise incentives for the round (rewards/penalties over the closed round's ledgers).
    finalise_incentives(run_ctx, rc, t)
    # take a final q_adv observation at closure so the last interval is credited.
    observe_adversarial_share(run_ctx, t)


def snapshot_availability(run_ctx: Any, rc: Any, t: float) -> None:
    """Record each miner's availability residency at round start so the availability reward is a
    per-round DELTA (never the whole-run cumulative)."""
    if not incentive_enabled(run_ctx):
        return
    for mid in sorted(run_ctx.miners.keys()):
        key = (rc.RoundID, mid)
        if key not in run_ctx.availability_snapshot:
            run_ctx.availability_snapshot[key] = availability_residency(run_ctx, mid, t)


# --------------------------------------------------------------------- reconciliation
def incentive_reconciliation_residual(run_ctx: Any) -> float:
    """S5-10: the reconciliation residual between the per-component stat totals and the immutable
    ledger (0.0 when every entry is accounted exactly once)."""
    ledger_by_component: Dict[str, float] = {}
    for e in run_ctx.incentive_ledger:
        ledger_by_component[e.component] = ledger_by_component.get(e.component, 0.0) + e.amount
    stat = run_ctx.adversarial_stats
    pairs = [("WORK_REWARD", "work_reward_total"),
             ("AVAILABILITY_REWARD", "availability_reward_total"),
             ("WINNER_REWARD", "winner_reward_total"),
             ("RESERVE_ACTIVATION_REWARD", "reserve_activation_reward_total"),
             ("REASSIGNMENT_REWARD", "reassignment_reward_total"),
             ("ABANDONMENT_PENALTY", "abandonment_penalty_total"),
             ("FALSE_CLAIM_PENALTY", "false_claim_penalty_total"),
             ("INVALID_MESSAGE_PENALTY", "invalid_message_penalty_total")]
    resid = 0.0
    for comp, stat_key in pairs:
        resid = max(resid, abs(ledger_by_component.get(comp, 0.0) - stat[stat_key]))
    return resid
