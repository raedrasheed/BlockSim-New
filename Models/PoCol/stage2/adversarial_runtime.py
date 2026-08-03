"""Stage-5 adversarial + incentive RUNTIME hooks for the PoCol core simulator.

Every function here is a NO-OP (or returns the honest default) unless the Stage-5 model is
explicitly enabled, so the accepted Stage-4C baseline is behaviourally unchanged (S5-01).

Stage 5 MODELS bounded behaviours and MEASURES outcomes.  No function here proves incentive
compatibility, fairness, Sybil resistance, selfish-mining resistance, coalition resistance,
common-prefix or chain-quality security, or Bitcoin/PoW-equivalent security.  The fixed
SHA-256 target and difficulty are NEVER changed by any Stage-5 parameter (S5-26).
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from .events import EventQueue, ScheduleEvent, CancelQueuedEvent, ordinary_dispatch_origin
from .events import Outcome
from .adversarial import (AdversarialEntity, MinerBehaviourProfile, ProgressClaim,
                          WithheldSolutionRecord, DelayedWakeAction, InvalidActionRecord,
                          IncentiveLedgerEntry, audit_draw, ADVERSARIAL_ACTOR_CLASSES,
                          AVAILABILITY_STATES)


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


def materialise_behaviours(run_ctx: Any, rc: Any, participants: List[Any]) -> None:
    """S5-1: materialise one ROUND-BOUND, IMMUTABLE MinerBehaviourProfile per participant and
    apply the physical effects (free-rider work fraction, hash-rate misreport bookkeeping).

    The physical search core ALWAYS runs on the actual (effective) hash rate; a reported hash
    rate never silently alters the physical rate (S5-4).  Re-materialisation for the same round
    is a no-op (replay-safe, S5-02)."""
    if not adversarial_enabled(run_ctx):
        return
    build_entities(run_ctx)
    pol = run_ctx.config.adversarial
    # per-miner declared behaviour sets (round_seq 0 => every round).
    declared: Dict[Any, tuple] = {}
    for (rseq, mid, flags) in pol.miner_behaviours:
        if rseq in (0, run_ctx.round_seq):
            declared[mid] = tuple(flags)
    for mid in participants:
        key = (rc.RoundID, mid)
        if key in run_ctx.behaviour_profiles:            # replay-safe
            continue
        st = rc.search_states.get(mid)
        if st is None:
            continue
        flags = declared.get(mid, ())
        actual_rate = st.hash_rate
        work_fraction = pol.free_rider_work_fraction if "FREE_RIDER" in flags else 1.0
        reported_rate = (actual_rate * pol.reported_hash_rate_multiplier
                         if "HASH_RATE_MISREPORTER" in flags else actual_rate)
        wake_mult = 1.0
        sol_policy = pol.solution_release_policy if "SOLUTION_WITHHOLDER" in flags \
            else "PROMPT_RELEASE"
        prog_policy = "WITHHOLD" if "PROGRESS_WITHHOLDER" in flags else "HONEST"
        exh_policy = "FALSE" if "FALSE_EXHAUSTION_CLAIMER" in flags else "HONEST"
        split_count = pol.assignment_split_count if "ASSIGNMENT_SPLITTER" in flags else 1
        prof = MinerBehaviourProfile(
            MinerID=mid, EntityID=_entity_for(run_ctx, mid), RoundID=rc.RoundID,
            behaviour_set=flags, actual_hash_rate=actual_rate, reported_hash_rate=reported_rate,
            work_fraction=work_fraction, wake_delay_multiplier=wake_mult,
            solution_release_policy=sol_policy, progress_reporting_policy=prog_policy,
            exhaustion_claim_policy=exh_policy, assignment_split_count=split_count,
            identity_group_id=_entity_for(run_ctx, mid),
            behaviour_generation=run_ctx.round_seq)
        run_ctx.behaviour_profiles[key] = prof
        # PHYSICAL effect of free riding: the effective actual rate reduces the physical
        # search capacity (availability remains a SEPARATE metric).  Ground truth actual rate
        # is preserved on the profile.
        if work_fraction < 1.0:
            st.hash_rate = actual_rate * work_fraction
            run_ctx.adversarial_stats["free_rider_count"] += 1
        if "HASH_RATE_MISREPORTER" in flags and reported_rate != actual_rate:
            run_ctx.adversarial_stats["hash_rate_misreport_count"] += 1
            run_ctx.adversarial_stats["actual_reported_divergence_count"] += 1
            ratio = reported_rate / actual_rate if actual_rate > 0 else 1.0
            run_ctx.adversarial_stats["allocation_distortion_max_ratio"] = max(
                run_ctx.adversarial_stats["allocation_distortion_max_ratio"], ratio)
        if split_count > 1:
            run_ctx.adversarial_stats["assignment_split_count"] += 1
    # arm the q_adv observation hook + take the first observation for this round.
    run_ctx.adversarial_share_hook = lambda t: observe_adversarial_share(run_ctx, t)
    observe_adversarial_share(run_ctx, run_ctx.event_queue.current_event_time)


# --------------------------------------------------------------------- S5-7 delayed wake
def wake_extra_latency(run_ctx: Any, rc: Any, mid: Any, honest_target: float,
                       now: float) -> float:
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
    action_id = (rc.RoundID, rc.TemplateID_committed, _entity_for(run_ctx, mid), mid,
                 "DELAYED_WAKE", "wake_start")

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
    """Record the actual wake time for a delayed-wake action when the wake finally completes."""
    if not adversarial_enabled(run_ctx):
        return
    for rec in run_ctx.delayed_wake_actions.values():
        if rec.RoundID == rc.RoundID and rec.MinerID == mid and rec.status == "PENDING":
            rec.actual_wake_time = now
            rec.status = "COMPLETED"
            rec.disposition = Outcome("delayed_wake_completed")


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
    run_ctx.adversarial_stats["false_exhaustion_attempted"] += 1
    claim = audit_claim(run_ctx, rc, lease_id, st.MinerID, st.cursor, st.range_end,
                        "EXHAUSTION_CLAIM")
    if claim.detected:
        run_ctx.adversarial_stats["false_exhaustion_detected"] += 1
        # rejected: retain the real lease/progress state; the miner continues honestly.
        return None
    # accepted false exhaustion: preserve actual ground truth, record the coverage gap.
    run_ctx.adversarial_stats["false_exhaustion_accepted"] += 1
    gap = st.range_end - st.cursor
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
                               t: float) -> None:
    """S5-5: a PROGRESS_WITHHOLDER under-reports how far it actually searched.

    Applied at the reassignment boundary, where the reported frontier is the value the protocol
    actually acts on.  The under-report goes through the SAME modeled audit as any other claim:
    a detected claim is rejected and the real frontier is retained; an undetected claim lowers
    the ACCEPTED frontier while the ACTUAL frontier is preserved separately as ground truth
    (S5-3).  The successor then re-evaluates the difference — a real, explicitly counted cost."""
    if not adversarial_enabled(run_ctx):
        return
    lease = run_ctx.range_leases.get(pred_lease_id)
    if lease is None:
        return
    prof = _profile(run_ctx, rc, lease.MinerID)
    if prof is None or prof.progress_reporting_policy != "WITHHOLD":
        return
    actual = prog.committed_frontier
    done = actual - lease.lease_start_nonce
    if done <= 0:
        return
    withheld = int(run_ctx.config.adversarial.progress_withholding_fraction * done)
    reported = actual - withheld
    if reported >= actual:
        return
    claim = audit_claim(run_ctx, rc, pred_lease_id, lease.MinerID, actual, reported,
                        "PROGRESS_REPORT")
    if claim.detected:                                   # rejected: the real frontier stands
        return
    run_ctx.adv_actual_frontier[prog.RangeSliceID] = actual
    run_ctx.adv_reeval_boundary[prog.RangeSliceID] = reported
    prog.committed_frontier = reported
    lease.committed_cursor = reported


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

    # ---- WORK_REWARD over unique accepted committed evaluations (dedup by range lineage) ----
    dedup_work: Dict[Any, int] = {}
    miner_of_lineage: Dict[Any, Any] = {}
    for rec in run_ctx.evaluation_ledger:
        if rec.RoundID != rc.RoundID:
            continue
        lineage = rec.RangeSliceID if rec.RangeSliceID is not None else rec.AssignmentID
        key = (lineage, rec.interval_start, rec.interval_end)
        if key in dedup_work:
            continue
        dedup_work[key] = rec.interval_end - rec.interval_start
        miner_of_lineage[key] = rec.MinerID
    for key, committed in dedup_work.items():
        mid = miner_of_lineage[key]
        eid = _entity_for(run_ctx, mid)
        entry = _emit(run_ctx, rc, eid, mid, "WORK_REWARD", +1, ip.r_work * committed,
                      source_event_id=key, range_lineage_id=key[0],
                      eligibility_reason="unique_accepted_committed_evaluations",
                      dedup_key=("WORK", rc.RoundID) + key)
        if entry is not None:
            st_stats["work_reward_total"] += entry.amount

    # ---- naive vs deduplicated entity accounting (S5-8) ----
    # naive: multiply the entity's work credit by its per-round assignment-split x identity
    # count (the modeled amplification EXPOSURE); deduplicated: one credit per range lineage.
    naive_total = 0.0
    dedup_entity_total = 0.0
    entity_work: Dict[Any, float] = {}
    for key, committed in dedup_work.items():
        mid = miner_of_lineage[key]
        eid = _entity_for(run_ctx, mid)
        entity_work[eid] = entity_work.get(eid, 0.0) + ip.r_work * committed
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

    # ---- ABANDONMENT_PENALTY only for INTENTIONAL abandonment (crash faults excluded
    # unless explicitly configured, S5-10) ----
    if ip.q_abandon > 0:
        for mid, prof in run_ctx.behaviour_profiles.items():
            if mid[0] != rc.RoundID:
                continue
            _rid, m_id = mid
            if "IDLE_POLICY_DEFECTOR" in prof.behaviour_set:
                eid = _entity_for(run_ctx, m_id)
                entry = _emit(run_ctx, rc, eid, m_id, "ABANDONMENT_PENALTY", -1, ip.q_abandon,
                              source_event_id=("ABANDON", m_id), range_lineage_id=None,
                              eligibility_reason="intentional_abandonment",
                              dedup_key=("ABANDON", rc.RoundID, m_id))
                if entry is not None:
                    st_stats["abandonment_penalty_total"] += entry.amount


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
            if ws.release_policy == "NEVER_RELEASE":
                run_ctx.adversarial_stats["withheld_never_released_count"] += 1
    for rec in run_ctx.delayed_wake_actions.values():
        if rec.RoundID == rc.RoundID and rec.status == "PENDING":
            rec.status = "CANCELLED_AT_CLOSE"
            rec.disposition = Outcome("delayed_wake_terminal_at_close")
    for claim in run_ctx.progress_claims:
        if claim.RoundID == rc.RoundID and claim.disposition is None:
            claim.disposition = Outcome("claim_terminal_at_close")
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
