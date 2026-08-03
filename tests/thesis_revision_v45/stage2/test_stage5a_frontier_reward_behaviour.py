"""Stage-5A executable-correction tests S5A-01 .. S5A-12.

Stage 5A closes seven executable defects found in the Stage-5 acceptance review:

* S5A-1  the accepted frontier is SEPARATE from the accepted Stage-4C authoritative physical
         ``RangeProgress.committed_frontier``, which is monotonic and never rewound;
* S5A-2  WORK_REWARD is the UNION of unique physical nonce positions, so partially overlapping
         re-evaluations cannot be rewarded twice;
* S5A-3  reported-rate allocation is EXECUTABLE and changes range sizing only — never physical
         hash capacity;
* S5A-4  assignment splitting creates REAL subassignments under one entity capacity budget, and
         identity multiplication creates explicit virtual identities with no physical capacity;
* S5A-5  an ABANDONMENT_PENALTY requires an EXECUTED abandonment action;
* S5A-6  delayed-wake actions are unique per wake episode and their floor impact is measured
         from real observations;
* S5A-7  the declared action limit, false-exhaustion offset and alternative-solution-won field
         all have executable effects.

Stage 5A adds NO security, fairness, incentive-compatibility or Sybil-resistance claim.  The
algorithm remains PoCol and the energy-saving mechanism remains the idle policy within PoCol.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, RunInitialise, run_simulation,
                                 AdversarialPolicy, IncentivePolicy, RangeLease,
                                 MinerBehaviourProfile)
from Models.PoCol.stage2 import adversarial_runtime as adv

_HARD = 1 << 300
_TRIVIAL = 1
M0, M1, M2, M3 = "M000", "M001", "M002", "M003"
_ALL = (M0, M1, M2, M3)


def cfg(*, adversarial=None, incentive=None, difficulty=_HARD, D=400, horizon=60.0, n=4,
        reserve_fraction=0.0, batch=25, lease=None, **kw):
    extra = {"range_lease": lease} if lease is not None else {}
    return Stage2Config(num_miners=n, reserve_fraction=reserve_fraction, nonce_domain_size=D,
                        difficulty=difficulty, batch_size=batch, horizon_T=horizon,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **extra, **kw)


def attacker(flags, miners=(M0,), klass="BYZANTINE", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


def _withholding_fixture(fraction=0.5, detect=0.0):
    """A minimal, fully-controlled progress-withholding decision point."""
    run = RunInitialise(cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                                 audit_detection_probability=detect,
                                                 progress_withholding_fraction=fraction)))
    rc = type("RC", (), {"RoundID": "round-1", "TemplateID_committed": "tpl"})()
    run.behaviour_profiles[("round-1", M0)] = MinerBehaviourProfile(
        MinerID=M0, EntityID="E1", RoundID="round-1", behaviour_set=("PROGRESS_WITHHOLDER",),
        actual_hash_rate=100.0, reported_hash_rate=100.0, work_fraction=1.0,
        wake_delay_multiplier=1.0, solution_release_policy="PROMPT_RELEASE",
        progress_reporting_policy="WITHHOLD", exhaustion_claim_policy="HONEST",
        assignment_split_count=1, identity_group_id="E1", behaviour_generation=0)
    run.range_leases["L1"] = RangeLease(
        LeaseID="L1", RoundID="round-1", TemplateID="tpl", RangeSliceID="S1",
        lease_generation=1, AssignmentID="A", assignment_version=1, MinerID=M0,
        assignment_kind="PRIMARY_ASSIGNMENT", lease_start_nonce=0, lease_end_nonce=100,
        committed_cursor=80, lease_start_time=0.0, lease_expiry_time=1e18,
        lease_status="REVOKED")
    prog = type("P", (), {"RangeSliceID": "S1", "committed_frontier": 80, "range_end": 100})()
    return run, rc, prog


# ====================================================== S5A-1 frontier separation
def test_s5a_01_physical_frontier_stays_monotonic_after_an_accepted_withholding_claim():
    """S5A-01: an ACCEPTED progress-withholding claim never decreases the accepted Stage-4C
    authoritative physical ``RangeProgress.committed_frontier``."""
    run, rc, prog = _withholding_fixture()
    before = prog.committed_frontier
    start = adv.apply_progress_withholding(run, rc, prog, "L1", 5.0)
    assert start == 40                                  # the successor resumes from 40 ...
    assert prog.committed_frontier == before == 80      # ... the PHYSICAL frontier does not move
    assert run.adversarial_stats["physical_frontier_rewind_count"] == 0

    # replaying the identical claim returns the same decision and performs no second effect.
    again = adv.apply_progress_withholding(run, rc, prog, "L1", 5.0)
    assert again == start
    assert prog.committed_frontier == 80
    assert len(run.accepted_frontier_records) == 1
    assert run.adversarial_stats["accepted_frontier_record_count"] == 1

    # --- and END-TO-END, through a real Path-B reassignment in a real multi-round run ---
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)
    e2e = run_simulation(cfg(reserve_fraction=0.25, horizon=90.0, lease=lease,
                             incentive=IncentivePolicy(enabled=True, r_work=1.0),
                             adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                                  audit_detection_probability=0.0,
                                                  progress_withholding_fraction=0.5),
                             injected_lease_faults=((1, M0, 2.0, "fault"),)),
                         run_id="s5a-01-e2e")
    recs = e2e.accepted_frontier_records
    assert recs, "the reassignment path must produce an accepted-frontier record"
    for rec in recs:
        prog = e2e.range_progress.get(rec.RangeSliceID)
        assert rec.accepted_frontier < rec.actual_frontier
        # the PHYSICAL frontier never ends up below the actual frontier at the decision.
        assert prog is not None and prog.committed_frontier >= rec.actual_frontier
    assert e2e.adversarial_stats["physical_frontier_rewind_count"] == 0
    assert e2e.adversarial_stats["adversarial_reevaluation_count"] > 0
    assert e2e.adversarial_stats["duplicate_work_reward_prevented_count"] > 0
    assert e2e.adversarial_stats["work_reward_union_residual"] == pytest.approx(0.0)


def test_s5a_02_actual_reported_and_accepted_frontiers_are_independently_queryable():
    """S5A-02: all three frontier values are recorded separately and remain distinguishable,
    together with the reassignment start and the re-evaluation interval."""
    run, rc, prog = _withholding_fixture()
    adv.apply_progress_withholding(run, rc, prog, "L1", 5.0)
    rec = run.accepted_frontier_records[0]
    assert rec.actual_frontier == 80
    assert rec.reported_frontier == 40
    assert rec.accepted_frontier == 40
    assert rec.accepted_frontier < rec.actual_frontier
    assert rec.reassignment_start == 40
    assert rec.reevaluation_interval == (40, 80)
    assert rec.physical_committed_frontier_at_decision == 80
    # bound to round / template / slice / lease / assignment version.
    assert rec.RecordID == ("round-1", "tpl", "S1", "L1", 1)
    assert rec.RoundID == "round-1" and rec.TemplateID == "tpl"
    assert rec.RangeSliceID == "S1" and rec.LeaseID == "L1" and rec.assignment_version == 1
    # the reconciliation exposes every layer for audit.
    rows = adv.frontier_reconciliation(run)
    assert len(rows) == 1
    row = rows[0]
    for k in ("actual_frontier", "reported_frontier", "accepted_frontier",
              "reassignment_start", "physical_evaluation_intervals"):
        assert k in row
    assert (row["actual_frontier"], row["reported_frontier"], row["accepted_frontier"]) \
        == (80, 40, 40)

    # a DETECTED claim keeps the accepted frontier at the actual value and opens no window.
    run2, rc2, prog2 = _withholding_fixture(detect=1.0)
    assert adv.apply_progress_withholding(run2, rc2, prog2, "L1", 5.0) is None
    rec2 = run2.accepted_frontier_records[0]
    assert rec2.detected and rec2.accepted_frontier == rec2.actual_frontier == 80
    assert prog2.committed_frontier == 80
    assert "S1" not in run2.adv_reeval_window


# ====================================================== S5A-2 unique nonce union
def test_s5a_03_overlapping_intervals_reward_exactly_the_unique_nonce_union():
    """S5A-03: physical [0,80) plus adversarial re-evaluation [40,80) is 80 unique positions —
    not 120.  The exact-interval key used before Stage 5A would have rewarded both."""
    assert adv.interval_union([(0, 80), (40, 80)]) == [(0, 80)]
    assert sum(hi - lo for lo, hi in adv.interval_union([(0, 80), (40, 80)])) == 80
    # partial overlap, out-of-order input and adjacency all canonicalise correctly.
    assert adv.interval_union([(40, 80), (0, 50)]) == [(0, 80)]
    assert adv.interval_union([(0, 40), (40, 80)]) == [(0, 80)]
    assert adv.interval_union([(0, 20), (50, 60)]) == [(0, 20), (50, 60)]
    assert adv.interval_union([(10, 10), (0, 5)]) == [(0, 5)]      # empty intervals dropped

    inc = IncentivePolicy(enabled=True, r_work=1.0)
    run = RunInitialise(cfg(incentive=inc, adversarial=attacker(("PROGRESS_WITHHOLDER",))))
    rc = type("RC", (), {"RoundID": "r", "TemplateID_committed": "t",
                         "block_accepted": False, "winner_miner_id": None})()
    from Models.PoCol.stage2.context import EvaluationRecord
    for lo, hi in ((0, 80), (40, 80)):                  # the overlap scenario, verbatim
        run.evaluation_ledger.append(EvaluationRecord(
            RoundID="r", TemplateID="t", MinerID=M0, AssignmentID="A", assignment_version=1,
            interval_start=lo, interval_end=hi, completion_time=1.0, contained_solution=False,
            winning_nonce=None, event_ref=None, assignment_kind="PRIMARY_ASSIGNMENT",
            RangeSliceID="S1", LeaseID="L1", lease_generation=1, progress_generation=1,
            predecessor_lease_id=None))
    adv.finalise_incentives(run, rc, 10.0)
    work = [e for e in run.incentive_ledger if e.component == "WORK_REWARD"]
    assert len(work) == 1                               # one canonical union interval
    assert sum(e.amount for e in work) == pytest.approx(80.0)     # 80 positions, never 120
    assert run.adversarial_stats["unique_rewarded_nonce_count"] == 80


def test_s5a_04_union_residual_is_zero_and_forty_duplicate_rewards_are_prevented():
    """S5A-04: the reward reconciliation matches the exact union cardinality, and the overlap
    scenario records exactly 40 duplicate work rewards prevented (120 physical - 80 unique)."""
    inc = IncentivePolicy(enabled=True, r_work=1.0)
    run = RunInitialise(cfg(incentive=inc, adversarial=attacker(("PROGRESS_WITHHOLDER",))))
    rc = type("RC", (), {"RoundID": "r", "TemplateID_committed": "t",
                         "block_accepted": False, "winner_miner_id": None})()
    from Models.PoCol.stage2.context import EvaluationRecord
    for lo, hi in ((0, 80), (40, 80)):
        run.evaluation_ledger.append(EvaluationRecord(
            RoundID="r", TemplateID="t", MinerID=M0, AssignmentID="A", assignment_version=1,
            interval_start=lo, interval_end=hi, completion_time=1.0, contained_solution=False,
            winning_nonce=None, event_ref=None, assignment_kind="PRIMARY_ASSIGNMENT",
            RangeSliceID="S1", LeaseID="L1", lease_generation=1, progress_generation=1,
            predecessor_lease_id=None))
    adv.finalise_incentives(run, rc, 10.0)
    s = run.adversarial_stats
    assert s["work_reward_union_residual"] == pytest.approx(0.0)
    assert s["duplicate_work_reward_prevented_count"] == 40
    assert s["unique_rewarded_nonce_count"] == 80
    assert s["physical_evaluation_count"] == 0          # counted at commit time, not here
    # the physical re-evaluation itself remains fully visible in the execution ledger.
    assert sum(r.interval_end - r.interval_start for r in run.evaluation_ledger) == 120


# ====================================================== S5A-3 reported-rate allocation
def test_s5a_05_reported_rate_allocation_changes_range_size_but_not_physical_rate():
    """S5A-05: with reported-rate allocation ON, a miner reporting 3x its actual rate receives a
    DIFFERENT deterministic range, yet still executes at its ACTUAL rate."""
    base = cfg()
    honest = run_simulation(base, run_id="s5a-05-h")
    pol = attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                   reported_hash_rate_multiplier=5.0, coordinator_uses_reported_hash_rate=True)
    run = run_simulation(cfg(adversarial=pol), run_id="s5a-05-a")
    assert run.adversarial_stats["reported_rate_allocation_rounds"] > 0

    rid = run.current_round_context.RoundID
    sizes = {mid: run.adv_allocated_range_size[(rid, mid)]
             for mid in _ALL if (rid, mid) in run.adv_allocated_range_size}
    assert sizes, "allocation sizes must be recorded"
    honest_rid = honest.current_round_context.RoundID
    honest_size = honest.round_ranges[honest_rid][M0]
    honest_span = honest_size[1] - honest_size[0]
    # the misreporter's range SIZE changed ...
    assert sizes[M0] != honest_span
    assert run.adversarial_stats["allocation_range_size_distortion_max_ratio"] > 1.0
    # ... the total domain is unchanged and the ranges stay disjoint and fully covering.
    assert sum(sizes.values()) == base.nonce_domain_size
    spans = sorted(run.round_ranges[rid].values())
    assert spans[0][0] == 0 and spans[-1][1] == base.nonce_domain_size
    for a, b in zip(spans, spans[1:]):
        assert a[1] == b[0]                             # contiguous, pairwise disjoint
    # ... and the PHYSICAL hash rate is the actual rate, never the reported one.
    prof = run.behaviour_profiles[(rid, M0)]
    st = run.current_round_context.search_states.get(M0)
    assert prof.reported_hash_rate == pytest.approx(prof.actual_hash_rate * 5.0)
    if st is not None:
        assert st.hash_rate == pytest.approx(prof.actual_hash_rate)
    proj = run.adv_allocation_projection[(rid, M0)]
    assert proj["reported_hash_rate"] > proj["actual_hash_rate"]
    assert proj["projected_completion_seconds"] < proj["actual_completion_seconds"]

    # with the flag OFF the accepted allocation behaviour is preserved exactly.
    off = run_simulation(cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                                                  reported_hash_rate_multiplier=5.0)),
                         run_id="s5a-05-off")
    assert off.adversarial_stats["reported_rate_allocation_rounds"] == 0
    off_rid = off.current_round_context.RoundID
    assert off.round_ranges[off_rid] == honest.round_ranges[honest_rid]


# ====================================================== S5A-4 executable splitting
def test_s5a_06_splitting_creates_real_subassignments_within_one_capacity_budget():
    """S5A-06: an ASSIGNMENT_SPLITTER creates REAL subassignment records whose capacity shares
    sum EXACTLY to the unsplit entity capacity — splitting reorganises, it never multiplies."""
    run = run_simulation(cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                                  assignment_split_count=4)),
                         run_id="s5a-06")
    subs = [s for s in run.subassignments if s.MinerID == M0]
    assert subs, "splitting must create real subassignment records"
    assert run.adversarial_stats["subassignment_count"] >= 4
    by_parent = {}
    for s in subs:
        by_parent.setdefault(s.ParentAssignmentID, []).append(s)
    for parent, group in by_parent.items():
        assert len(group) == 4
        budget = group[0].entity_capacity_budget
        assert all(g.entity_capacity_budget == budget for g in group)
        # capacity conservation: the shares sum to the SINGLE entity budget.
        assert sum(g.capacity_share for g in group) == pytest.approx(budget)
        assert all(g.EntityID == "E1" for g in group)
        assert all(g.SubAssignmentID != o.SubAssignmentID
                   for i, g in enumerate(group) for o in group[i + 1:])
    assert run.adversarial_stats["subassignment_capacity_residual"] == pytest.approx(0.0)


def test_s5a_07_split_subranges_are_disjoint_and_do_not_increase_throughput():
    """S5A-07: subranges partition the parent range exactly (disjoint, union == original) and the
    entity's physical throughput is identical to the unsplit case."""
    plain = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                    free_rider_work_fraction=1.0)),
                           run_id="s5a-07-p")
    split = run_simulation(cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                                    assignment_split_count=4)),
                           run_id="s5a-07-s")
    subs = [s for s in split.subassignments if s.MinerID == M0]
    by_parent = {}
    for s in subs:
        by_parent.setdefault(s.ParentAssignmentID, []).append(s)
    for parent, group in by_parent.items():
        group.sort(key=lambda g: g.index)
        for a, b in zip(group, group[1:]):
            assert a.range_end == b.range_start        # disjoint AND contiguous
        # the union equals the parent's original allocated range.
        rid = group[0].RoundID
        assert (group[0].range_start, group[-1].range_end) == split.round_ranges[rid][M0]

    # PHYSICAL throughput is unchanged: the same number of nonces is actually evaluated.
    def evaluated(r):
        return sum(v for (_rid, mid), v in r.final_searched.items() if mid == M0)
    assert evaluated(split) == evaluated(plain)
    rid = split.current_round_context.RoundID
    assert adv.entity_physical_capacity(split, split.current_round_context, "E1") == \
        pytest.approx(split.behaviour_profiles[(rid, M0)].actual_hash_rate)


def test_s5a_08_virtual_identities_are_explicit_and_grant_no_physical_capacity():
    """S5A-08: identity multiplication creates explicit virtual identity records bound to one
    EntityID, and creates NO additional physical capacity, assignment or lease."""
    plain = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                    free_rider_work_fraction=1.0)),
                           run_id="s5a-08-p")
    run = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                  free_rider_work_fraction=1.0,
                                                  sybil_identity_count=5)),
                         run_id="s5a-08-v")
    vids = [v for v in run.virtual_identities if v.EntityID == "E1"]
    assert len(vids) >= 5
    assert run.adversarial_stats["virtual_identity_count"] >= 5
    assert all(v.grants_physical_capacity is False for v in vids)
    assert all(v.EntityID == "E1" for v in vids)
    assert len({v.VirtualIdentityID for v in vids}) == len(vids)
    # identity count is reported SEPARATELY from real miner / assignment count.
    ent = run.adversarial_entities["E1"]
    assert len(ent.controlled_miner_ids) == 1           # one real miner ...
    assert len({v.index for v in vids}) >= 5            # ... five declared identities
    # no additional physical capacity, and no additional assignment or lease.
    def evaluated(r):
        return sum(v for (_rid, mid), v in r.final_searched.items() if mid == M0)
    assert evaluated(run) == evaluated(plain)
    rid = run.current_round_context.RoundID
    assert len([a for a in run.current_round_context.assignments.values()
                if a["MinerID"] == M0]) == \
        len([a for a in plain.current_round_context.assignments.values()
             if a["MinerID"] == M0])


# ====================================================== S5A-5 executed abandonment
def test_s5a_09_a_defector_is_not_penalised_when_the_round_closes_before_the_action():
    """S5A-09: declaring IDLE_POLICY_DEFECTOR is NOT an abandonment.  A round that closes before
    any abandonment action executes yields no action and therefore no penalty."""
    inc = IncentivePolicy(enabled=True, q_abandon=11.0)
    # the horizon ends before the defector completes even its first batch, so nothing executes.
    run = run_simulation(cfg(incentive=inc, horizon=0.5,
                             adversarial=attacker(("IDLE_POLICY_DEFECTOR",))),
                         run_id="s5a-09")
    assert run.abandonment_actions == []
    assert run.adversarial_stats["abandonment_action_count"] == 0
    assert not [e for e in run.incentive_ledger if e.component == "ABANDONMENT_PENALTY"]
    assert run.adversarial_stats["abandonment_penalty_total"] == 0.0
    assert run.adversarial_stats["abandonment_penalty_without_action_count"] == 0
    # the profile flag WAS declared — it simply is not sufficient on its own.
    profs = [p for (rid, m), p in run.behaviour_profiles.items() if m == M0]
    assert profs and "IDLE_POLICY_DEFECTOR" in profs[0].behaviour_set


def test_s5a_10_an_executed_abandonment_creates_exactly_one_penalty_entry():
    """S5A-10: one EXECUTED abandonment action produces exactly one penalty entry, charged
    against that action's immutable identity."""
    inc = IncentivePolicy(enabled=True, q_abandon=11.0)
    run = run_simulation(cfg(incentive=inc, horizon=60.0,
                             adversarial=attacker(("IDLE_POLICY_DEFECTOR",))),
                         run_id="s5a-10")
    acts = [a for a in run.abandonment_actions if a.MinerID == M0]
    assert acts, "the defector must execute a real abandonment action"
    a0 = acts[0]
    assert a0.abandoned_suffix_start == a0.actual_frontier
    assert a0.abandoned_suffix_end > a0.abandoned_suffix_start
    assert a0.abandoned_nonce_count() > 0
    assert a0.status in ("EXECUTED", "TERMINAL_AT_CLOSE")
    pens = [e for e in run.incentive_ledger if e.component == "ABANDONMENT_PENALTY"]
    assert len(pens) == len(acts)                       # exactly one entry per executed action
    assert all(e.sign == -1 and e.amount == 11.0 for e in pens)
    assert all(e.eligibility_reason == "executed_intentional_abandonment" for e in pens)
    assert {e.source_event_id for e in pens} == {a.ActionID for a in acts}
    assert run.adversarial_stats["abandonment_penalty_without_action_count"] == 0
    # replaying finalisation adds no second penalty (dedup by the action identity).
    before = len(pens)
    adv.finalise_incentives(run, run.current_round_context, run.run_end_time)
    assert len([e for e in run.incentive_ledger
                if e.component == "ABANDONMENT_PENALTY"]) == before

    # a CRASH fault is not an intentional abandonment and creates no action or penalty.
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)
    crashed = run_simulation(cfg(incentive=inc, lease=lease, horizon=30.0,
                                 injected_lease_faults=((1, M0, 2.0, "crash"),)),
                             run_id="s5a-10-crash")
    assert crashed.abandonment_actions == []
    assert not [e for e in crashed.incentive_ledger if e.component == "ABANDONMENT_PENALTY"]


# ====================================================== S5A-6 wake identity + floor impact
def test_s5a_11_two_wake_episodes_create_two_distinct_delayed_wake_actions():
    """S5A-11: a miner woken twice in one round produces TWO distinct action records, each with
    its own independently measured floor overlap — the pre-Stage-5A identity collapsed them."""
    run = RunInitialise(cfg(adversarial=attacker(("DELAYED_WAKE",),
                                                 delayed_wake_extra_latency=5.0)))
    rc = type("RC", (), {"RoundID": "round-1", "TemplateID_committed": "tpl",
                         "block_accepted": False, "winner_miner_id": None})()
    run.behaviour_profiles[("round-1", M0)] = MinerBehaviourProfile(
        MinerID=M0, EntityID="E1", RoundID="round-1", behaviour_set=("DELAYED_WAKE",),
        actual_hash_rate=100.0, reported_hash_rate=100.0, work_fraction=1.0,
        wake_delay_multiplier=1.0, solution_release_policy="PROMPT_RELEASE",
        progress_reporting_policy="HONEST", exhaustion_claim_policy="HONEST",
        assignment_split_count=1, identity_group_id="E1", behaviour_generation=0)

    e1 = adv.wake_extra_latency(run, rc, M0, honest_target=1.0, now=0.0, request_id="REQ-A")
    e2 = adv.wake_extra_latency(run, rc, M0, honest_target=20.0, now=19.0, request_id="REQ-B")
    assert e1 == e2 == 5.0
    acts = [a for a in run.delayed_wake_actions.values() if a.MinerID == M0]
    assert len(acts) == 2, "each wake EPISODE must get its own action record"
    assert len({a.ActionID for a in acts}) == 2
    assert run.adversarial_stats["delayed_wake_count"] == 2
    byh = {a.honest_expected_wake_time: a for a in acts}
    assert set(byh) == {1.0, 20.0}
    assert byh[1.0].adversarial_scheduled_wake_time == 6.0
    assert byh[20.0].adversarial_scheduled_wake_time == 25.0

    # complete each episode independently, then measure REAL floor overlap.
    adv.complete_delayed_wake(run, rc, M0, 6.0)
    adv.complete_delayed_wake(run, rc, M0, 25.0)
    assert all(a.status == "COMPLETED" for a in acts)
    # a real observed breach covering only the FIRST added interval [1,6].
    adv.record_floor_breach_interval(run, 0.0, 4.0)
    adv.finalise_delayed_wake_impact(run, rc, 30.0)
    assert byh[1.0].below_floor_overlap == pytest.approx(3.0)    # [1,4] of [1,6]
    assert byh[20.0].below_floor_overlap == pytest.approx(0.0)   # disjoint from the breach
    assert run.adversarial_stats["attack_induced_floor_breach_duration"] == pytest.approx(3.0)
    P_wake = run.config.per_miner_power("WAKING")
    assert byh[1.0].incremental_wake_energy_j == pytest.approx(P_wake * 5.0)
    # the impact is measured once (idempotent).
    adv.finalise_delayed_wake_impact(run, rc, 30.0)
    assert run.adversarial_stats["attack_induced_floor_breach_duration"] == pytest.approx(3.0)


# ====================================================== S5A-7 declared-field enforcement
def test_s5a_12_action_limit_offset_and_alternative_solution_won_all_have_effects():
    """S5A-12: every retained declared field has an executable consumer."""
    # --- maximum_actions_per_round is enforced BEFORE a new action is created ---
    capped = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                     miners=_ALL,
                                                     audit_detection_probability=0.0,
                                                     maximum_actions_per_round=2)),
                            run_id="s5a-12-cap")
    assert capped.adversarial_stats["actions_rejected_over_limit"] > 0
    uncapped = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                       miners=_ALL,
                                                       audit_detection_probability=0.0)),
                              run_id="s5a-12-free")
    assert uncapped.adversarial_stats["actions_rejected_over_limit"] == 0
    assert capped.adversarial_stats["false_exhaustion_attempted"] < \
        uncapped.adversarial_stats["false_exhaustion_attempted"]

    # --- false_exhaustion_claim_offset derives the reported claim deterministically ---
    off = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                  audit_detection_probability=0.0,
                                                  false_exhaustion_claims_range_end=False,
                                                  false_exhaustion_claim_offset=10)),
                         run_id="s5a-12-off")
    claims = [c for c in off.progress_claims if c.claim_type == "EXHAUSTION_CLAIM"]
    assert claims
    for c in claims:                                    # reported == cursor + 10, capped
        assert c.reported_frontier - c.actual_frontier <= 10
        assert c.reported_frontier > c.actual_frontier
    assert off.adversarial_stats["coverage_gap_nonce_count"] > 0

    # a ZERO offset with range-end claiming disabled reports the TRUTH: no false claim at all.
    truthful = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                       audit_detection_probability=0.0,
                                                       false_exhaustion_claims_range_end=False,
                                                       false_exhaustion_claim_offset=0)),
                              run_id="s5a-12-zero")
    assert truthful.adversarial_stats["false_exhaustion_attempted"] == 0
    assert truthful.adversarial_stats["coverage_gap_nonce_count"] == 0

    # --- alternative_solution_won is set when another accepted block closes the round ---
    # M003 is the FASTEST miner, so it genuinely finds and withholds a solution first; a slower
    # honest miner then publishes and closes the round, and the withholder loses the race.
    race = run_simulation(cfg(difficulty=_TRIVIAL, horizon=30.0,
                              adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=(M3,),
                                                   solution_release_policy="NEVER_RELEASE")),
                          run_id="s5a-12-race")
    assert race.adversarial_stats["solution_withholding_count"] > 0
    assert len(race.acceptance_times) > 0        # an alternative block really closed a round
    lost = [w for w in race.withheld_solutions.values() if w.alternative_solution_won]
    assert lost, "a withholder beaten to the block must be marked as having lost the race"
    assert race.adversarial_stats["withheld_alternative_solution_won_count"] == len(lost)
    assert all(w.MinerID == M3 for w in lost)
    # the field is FALSE when no alternative block closed the round (all miners withhold).
    nobody = run_simulation(cfg(difficulty=_TRIVIAL, horizon=30.0,
                                adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=_ALL,
                                                     solution_release_policy="NEVER_RELEASE")),
                            run_id="s5a-12-norace")
    assert nobody.adversarial_stats["withheld_alternative_solution_won_count"] == 0
    assert all(not w.alternative_solution_won for w in nobody.withheld_solutions.values())
