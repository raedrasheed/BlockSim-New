"""Stage-5B executable-correction tests S5B-01 .. S5B-12.

Stage 5B closes eight executable defects found in the Stage-5A acceptance review:

* S5B-1  WORK_REWARD ownership is the FIRST PHYSICAL EVALUATOR of each nonce position, not
         whichever miner happened to open the lineage;
* S5B-2  ``finalise_incentives`` is fully replay-idempotent — a second call leaves the ledger
         AND every derived metric byte-for-byte unchanged;
* S5B-3  accepted-frontier separation applies on BOTH reassignment paths, including the Path-B
         reserve wake, which previously started from the physical frontier;
* S5B-4  the delayed-wake policy is consulted from EVERY real wake lifecycle, each action
         carries the real request identity and a wake generation, and the incremental wake
         energy is charged over the REALISED added interval;
* S5B-5  one action-registration authority covers all six action types;
* S5B-6  effective physical capacity is conserved under splitting, and subassignment /
         virtual-identity accounting is DERIVED from the records;
* S5B-7  an executed abandonment records its real unsearched suffix and its round can never
         close as ordinary or full-domain exhaustion;
* S5B-8  the adapter maps every declared field and the physical evaluation count reconciles
         with the evaluation ledger with range leases enabled AND disabled.

Stage 5B adds NO security, fairness, incentive-compatibility or Sybil-resistance claim.  The
algorithm remains PoCol, the energy-saving mechanism remains the idle policy within PoCol, and
the security floor remains an operational active-capacity floor only.
"""
from __future__ import annotations

import copy

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, SecurityFloorPolicy,
                                 RunInitialise, run_simulation, AdversarialPolicy,
                                 IncentivePolicy, MinerSearchState, MinerBehaviourProfile,
                                 ADVERSARIAL_COVERAGE_GAP_NO_BLOCK, RESULT_SCHEMA_VERSION)
from Models.PoCol.stage2 import adversarial_runtime as adv
from Models.PoCol.stage2.adapter import (results_schema, stage2config_from_blocksim,
                                         run_pocol_stage2)
from Models.PoCol.stage2.context import EvaluationRecord

_HARD = 1 << 300          # unreachable target: the whole domain is searched, no block is found
M0, M1, M2, M3 = "M000", "M001", "M002", "M003"
_ALL = (M0, M1, M2, M3)


def cfg(*, adversarial=None, incentive=None, difficulty=_HARD, D=400, horizon=60.0, n=4,
        reserve_fraction=0.0, batch=25, lease=None, floor=None, **kw):
    extra = {}
    if lease is not None:
        extra["range_lease"] = lease
    if floor is not None:
        extra["security_floor"] = floor
    return Stage2Config(num_miners=n, reserve_fraction=reserve_fraction, nonce_domain_size=D,
                        difficulty=difficulty, batch_size=batch, horizon_T=horizon,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **extra, **kw)


def attacker(flags, miners=(M0,), klass="BYZANTINE", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


def _rc(round_id="r", template="t"):
    return type("RC", (), {"RoundID": round_id, "TemplateID_committed": template,
                           "block_accepted": False, "winner_miner_id": None,
                           "round_terminal_time": None})()


def _eval(run, mid, lo, hi, t, *, lineage="S1", aid="A", version=1):
    """Append one physical EvaluationRecord to the immutable execution ledger."""
    run.evaluation_ledger.append(EvaluationRecord(
        RoundID="r", TemplateID="t", MinerID=mid, AssignmentID=aid, assignment_version=version,
        interval_start=lo, interval_end=hi, completion_time=t, contained_solution=False,
        winning_nonce=None, event_ref=None, assignment_kind="PRIMARY_ASSIGNMENT",
        RangeSliceID=lineage, LeaseID="L1", lease_generation=1, progress_generation=1,
        predecessor_lease_id=None))


def _profile(run, mid, flags, *, rate=100.0, round_id="r", **kw):
    kw.setdefault("reported_hash_rate", rate)
    kw.setdefault("work_fraction", 1.0)
    kw.setdefault("solution_release_policy", "PROMPT_RELEASE")
    kw.setdefault("progress_reporting_policy", "HONEST")
    kw.setdefault("exhaustion_claim_policy", "HONEST")
    kw.setdefault("assignment_split_count", 1)
    run.behaviour_profiles[(round_id, mid)] = MinerBehaviourProfile(
        MinerID=mid, EntityID="E1", RoundID=round_id, behaviour_set=tuple(flags),
        actual_hash_rate=rate, wake_delay_multiplier=1.0, identity_group_id="E1",
        behaviour_generation=0, **kw)
    return run.behaviour_profiles[(round_id, mid)]


# ============================================================ S5B-1 reward ownership
def test_s5b_01_unique_suffix_work_belongs_to_the_reassignee_predecessor_keeps_its_own():
    """S5B-01: one lineage, predecessor [0,80) then successor [40,100).

    The predecessor earns 80 (it evaluated [0,80) first), the successor earns exactly the 20
    unique positions it added, the total is 100, and 40 duplicate rewards are prevented.  The
    pre-Stage-5B ``setdefault(lineage, MinerID)`` handed the WHOLE union to whichever miner
    opened the lineage, so the successor's real work earned nothing.
    """
    run = RunInitialise(cfg(incentive=IncentivePolicy(enabled=True, r_work=1.0),
                            adversarial=attacker(("PROGRESS_WITHHOLDER",))))
    rc = _rc()
    _eval(run, M0, 0, 80, 1.0)                      # predecessor searched [0, 80) FIRST
    _eval(run, M1, 40, 100, 2.0)                    # successor re-evaluated [40,80), added [80,100)

    adv.finalise_incentives(run, rc, 10.0)
    work = [e for e in run.incentive_ledger if e.component == "WORK_REWARD"]
    by_miner = {}
    for e in work:
        by_miner[e.MinerID] = by_miner.get(e.MinerID, 0.0) + e.amount
    assert by_miner == {M0: 80.0, M1: 20.0}         # exact first-physical-evaluator ownership
    assert sum(by_miner.values()) == pytest.approx(100.0)

    s = run.adversarial_stats
    assert s["unique_rewarded_nonce_count"] == 100
    assert s["duplicate_work_reward_prevented_count"] == 40      # 140 physical - 100 unique
    assert s["work_reward_union_residual"] == pytest.approx(0.0)
    assert all(e.eligibility_reason == "first_physical_evaluator_unique_nonce" for e in work)

    # the reconciliation table names the owner and the prevented duplicates per interval.
    rows = adv.ownership_reconciliation(run)
    assert rows, "an ownership reconciliation row is required for every evaluated interval"
    for row in rows:
        for key in ("nonce_interval", "first_evaluator", "later_evaluators", "reward_owner",
                    "rewarded_count", "duplicate_reward_prevented_count"):
            assert key in row, key
    assert sum(r["rewarded_count"] for r in rows) == 100
    assert sum(r["duplicate_reward_prevented_count"] for r in rows) == 40
    owners = {r["reward_owner"] for r in rows if r["reward_owner"] is not None}
    assert owners == {M0, M1}
    # the later evaluator of an already-covered interval is recorded and rewarded nothing.
    dup = [r for r in rows if r["duplicate_reward_prevented_count"] > 0]
    assert dup and all(r["rewarded_count"] == 0 and r["later_evaluators"] == [M1] for r in dup)


def test_s5b_01b_both_accounting_views_use_the_same_ownership_map():
    """S5B-01 (companion): naive-identity and entity-deduplicated accounting are computed from
    the SAME first-physical-evaluator ownership map — they differ only in whether an entity's
    identities are collapsed, never in who owns a nonce position."""
    inc = IncentivePolicy(enabled=True, r_work=1.0)
    run = RunInitialise(cfg(incentive=inc,
                            adversarial=attacker(("PROGRESS_WITHHOLDER",), miners=(M0, M1))))
    rc = _rc()
    _eval(run, M0, 0, 80, 1.0)
    _eval(run, M1, 40, 100, 2.0)
    adv.finalise_incentives(run, rc, 10.0)
    s = run.adversarial_stats
    # both miners belong to entity E1, so the deduplicated entity total is the union total.
    assert s["deduplicated_entity_reward_total"] == pytest.approx(100.0)
    assert s["naive_identity_reward_total"] >= s["deduplicated_entity_reward_total"]


# ============================================================ S5B-2 replay idempotence
def test_s5b_02_second_finalisation_changes_neither_the_ledger_nor_any_derived_metric():
    """S5B-02: calling ``finalise_incentives`` twice leaves the COMPLETE ledger and EVERY
    Stage-5 metric unchanged.  Before Stage 5B the second call re-incremented the duplicate,
    unique-nonce and naive/dedup totals, so the residual that certifies correctness blew up."""
    run = RunInitialise(cfg(incentive=IncentivePolicy(enabled=True, r_work=1.0, r_avail=0.1,
                                                      r_win=100.0),
                            adversarial=attacker(("PROGRESS_WITHHOLDER",))))
    rc = _rc()
    _eval(run, M0, 0, 80, 1.0)
    _eval(run, M1, 40, 100, 2.0)

    adv.finalise_incentives(run, rc, 10.0)
    ledger_1 = [(e.EntityID, e.MinerID, e.component, e.sign, e.amount, e.eligibility_reason)
                for e in run.incentive_ledger]
    stats_1 = copy.deepcopy(run.adversarial_stats)
    rounds_1 = copy.deepcopy(run.round_incentive_result)

    adv.finalise_incentives(run, rc, 10.0)          # exact replay
    ledger_2 = [(e.EntityID, e.MinerID, e.component, e.sign, e.amount, e.eligibility_reason)
                for e in run.incentive_ledger]

    assert ledger_2 == ledger_1                     # not one extra entry, not one changed amount
    assert run.adversarial_stats == stats_1         # EVERY derived metric, not a chosen subset
    assert run.round_incentive_result == rounds_1
    for key in ("duplicate_work_reward_prevented_count", "unique_rewarded_nonce_count",
                "naive_identity_reward_total", "deduplicated_entity_reward_total",
                "work_reward_union_residual", "work_reward_total", "availability_reward_total",
                "winner_reward_total", "abandonment_penalty_total"):
        assert run.adversarial_stats[key] == stats_1[key], key
    assert run.adversarial_stats["duplicate_work_reward_prevented_count"] == 40
    assert run.adversarial_stats["work_reward_union_residual"] == pytest.approx(0.0)

    # a THIRD call is equally inert (idempotence is not a one-shot property).
    adv.finalise_incentives(run, rc, 10.0)
    assert run.adversarial_stats == stats_1
    assert len(run.incentive_ledger) == len(ledger_1)


# ============================================================ S5B-3 Path-B frontier separation
def _path_b_run():
    """A GENUINE Path-B reserve reassignment under an undetected progress-withholding claim."""
    return run_simulation(
        cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",), audit_detection_probability=0.0,
                                 progress_withholding_fraction=0.5),
            incentive=IncentivePolicy(enabled=True, r_work=1.0),
            reserve_fraction=0.5, horizon=120.0,
            lease=RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                                   lease_duration=1e18, progress_timeout=1e18),
            injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)),
        run_id="s5b-03-pathb")


def test_s5b_03_a_true_path_b_reserve_reassignment_applies_accepted_frontier_separation():
    """S5B-03: the Path-B reserve wake starts the reassignee at the ACCEPTED frontier.

    Every assertion below must hold before this scenario may be called Path B: a Stage-3 wake is
    required, the selected miner was an AVAILABLE reserve, a ReserveActivationRequest carries the
    wake, the accepted frontier is strictly below the actual one, the physical frontier never
    rewinds, real re-evaluation happens and the duplicate reward is prevented.  Before Stage 5B
    ``_bind_reserve_reassignment_if_any`` started from the PHYSICAL frontier, so the accepted
    view was silently discarded on this path.
    """
    run = _path_b_run()

    # (1) it is really Path B: a Stage-3 wake through a non-domain wake handle.
    assert run.lease_stats["wake_handles_created"] >= 1
    wake_reqs = [r for r in run.reassignment_requests.values() if r.needs_stage3_wake]
    assert wake_reqs, "Path B requires needs_stage3_wake == True"
    req = wake_reqs[0]
    assert req.needs_stage3_wake is True

    # (2) the selected miner was an AVAILABLE reserve, not an already-alive primary.
    rr = run.reserve_records.get((req.RoundID, req.new_MinerID))
    assert rr is not None, "the Path-B reassignee must be a reserve miner"

    # (3) a ReserveActivationRequest carries the wake, scoped REASSIGNMENT_WAKE_ONLY.
    act = run.activation_requests[req.reserve_activation_request_id]
    assert act.activation_scope == "REASSIGNMENT_WAKE_ONLY"
    assert act.RangeReassignmentRequestID == req.RangeReassignmentRequestID
    assert act.seated_at is not None                    # S5B-4: seating time is recorded

    # (4) accepted < actual, and the successor really starts at the accepted frontier.
    recs = [r for r in run.accepted_frontier_records if r.accepted_frontier < r.actual_frontier]
    assert recs, "Path B must consult the same accepted-frontier authority as Path A"
    rec = recs[0]
    assert rec.reassignment_start == rec.accepted_frontier < rec.actual_frontier
    assert rec.reevaluation_interval == (rec.accepted_frontier, rec.actual_frontier)

    # (5) the PHYSICAL frontier is monotonic and never rewound.
    assert run.adversarial_stats["physical_frontier_rewind_count"] == 0
    prog = run.range_progress.get(rec.RangeSliceID)
    assert prog is not None and prog.committed_frontier >= rec.actual_frontier

    # (6) real re-evaluation occurred and earned no second reward.
    assert run.adversarial_stats["adversarial_reevaluation_count"] > 0
    assert run.adversarial_stats["duplicate_work_reward_prevented_count"] > 0
    assert run.adversarial_stats["work_reward_union_residual"] == pytest.approx(0.0)

    # the ORIGINAL RangeProgress stays the single interval authority.
    assert req.RangeSliceID == rec.RangeSliceID
    assert not any(str(sid).startswith("WH-") for sid in run.range_progress)


# ============================================================ S5B-4 wake lifecycles
def _wake_cfg(*, reserve_fraction, minrate, faults, extra=2.0, horizon=90.0):
    return cfg(adversarial=attacker(("DELAYED_WAKE",), miners=_ALL,
                                    delayed_wake_extra_latency=extra,
                                    maximum_actions_per_round=100),
               reserve_fraction=reserve_fraction, horizon=horizon,
               floor=SecurityFloorPolicy(enabled=minrate > 0,
                                         minimum_active_hash_rate=minrate),
               lease=RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                                      lease_duration=1e18, progress_timeout=1e18),
               injected_lease_faults=faults)


def test_s5b_04_initial_reserve_path_a_and_path_b_wakes_all_consult_delayed_wake_policy():
    """S5B-04: all four REAL wake lifecycles consult the delayed-wake policy.

    Every action is produced by ACTUAL queued events in executed runs — no helper is called
    directly.  Three runs are needed because one execution cannot simultaneously present an
    exhausted primary (Path A) and an unused available reserve (Path B) for the same fault.
    """
    # (a) reserve activation + Path B (early fault: no primary has exhausted yet).
    run_b = run_simulation(_wake_cfg(reserve_fraction=0.5, minrate=150.0,
                                     faults=((1, M0, 1.3, "MINER_FAILED"),)), run_id="s5b-04-b")
    # (b) Path A (late fault: another primary has exhausted its own range and is free to help).
    run_a = run_simulation(_wake_cfg(reserve_fraction=0.0, minrate=0.0,
                                     faults=((1, M0, 3.5, "MINER_FAILED"),)), run_id="s5b-04-a")
    # (c) initial primary wake alone.
    run_p = run_simulation(_wake_cfg(reserve_fraction=0.0, minrate=0.0, faults=()),
                           run_id="s5b-04-p")

    covered = {
        "PRIMARY_WAKE": max(r.adversarial_stats["delayed_wake_primary_count"]
                            for r in (run_p, run_a, run_b)),
        "RESERVE_ACTIVATION_WAKE": run_b.adversarial_stats[
            "delayed_wake_reserve_activation_count"],
        "PATH_A_REASSIGNMENT_WAKE": run_a.adversarial_stats[
            "delayed_wake_path_a_reassignment_count"],
        "PATH_B_REASSIGNMENT_RESERVE_WAKE": run_b.adversarial_stats[
            "delayed_wake_path_b_reserve_count"],
    }
    for lifecycle, n in covered.items():
        assert n > 0, f"{lifecycle} never consulted the delayed-wake policy"
    assert set(covered) | {"UNSPECIFIED"} == set(adv.WAKE_LIFECYCLES)

    for run in (run_p, run_a, run_b):
        s = run.adversarial_stats
        # every wake in an EXECUTED run is attributed to a real lifecycle and a real request.
        assert s["delayed_wake_unspecified_lifecycle_count"] == 0
        assert s["delayed_wake_unattributed_refused"] == 0
        gens = set()
        for rec in run.delayed_wake_actions.values():
            assert rec.wake_lifecycle in adv.WAKE_LIFECYCLES
            assert rec.wake_request_identity is not None      # real request identity / EventRef
            assert rec.wake_generation >= 1                   # and a wake generation
            assert rec.ActionID[-1] == rec.wake_request_identity
            assert rec.ActionID[-2] == rec.wake_generation
            gens.add(rec.ActionID)
        assert len(gens) == len(run.delayed_wake_actions)     # identities never collide


def test_s5b_04b_exact_wake_replay_returns_the_same_action_and_consumes_no_budget():
    """S5B-04 (companion): replaying the SAME wake request returns the same action, does not
    increment the wake generation and does not charge the budget a second time."""
    run = RunInitialise(cfg(adversarial=attacker(("DELAYED_WAKE",),
                                                 delayed_wake_extra_latency=5.0)))
    rc = _rc("round-1", "tpl")
    _profile(run, M0, ("DELAYED_WAKE",), round_id="round-1")
    rid = ("PRIMARY_WAKE", M0, "A0", 1)

    first = adv.wake_extra_latency(run, rc, M0, 1.0, 0.0, request_id=rid,
                                   lifecycle="PRIMARY_WAKE")
    assert first == 5.0
    gen_after_first = run.adv_wake_generation[("round-1", M0)]
    used_after_first = run.adv_actions_this_round["round-1"]
    n_after_first = len(run.delayed_wake_actions)

    again = adv.wake_extra_latency(run, rc, M0, 1.0, 0.0, request_id=rid,
                                   lifecycle="PRIMARY_WAKE")
    assert again == first                                        # same action, same latency
    assert run.adv_wake_generation[("round-1", M0)] == gen_after_first
    assert run.adv_actions_this_round["round-1"] == used_after_first
    assert len(run.delayed_wake_actions) == n_after_first
    assert run.adversarial_stats["delayed_wake_replay_no_effect_count"] == 1
    assert run.adversarial_stats["delayed_wake_count"] == 1

    # a DIFFERENT request identity is a different wake episode with its own generation.
    other = adv.wake_extra_latency(run, rc, M0, 20.0, 19.0,
                                   request_id=("RESERVE_ACTIVATION", "REQ-9", 1),
                                   lifecycle="RESERVE_ACTIVATION_WAKE")
    assert other == 5.0
    assert run.adv_wake_generation[("round-1", M0)] == gen_after_first + 1
    assert len(run.delayed_wake_actions) == n_after_first + 1


def test_s5b_05_a_real_delayed_wake_triggers_another_reserve_activation():
    """S5B-05: a delayed wake that keeps active capacity below the operational floor really
    causes ANOTHER reserve activation inside the added interval, and the action records it.

    Before Stage 5B ``finalise_delayed_wake_impact`` read a ``seated_time`` attribute that does
    not exist on ``ReserveActivationRequest``, so ``another_reserve_activated`` could never
    become true no matter what the run did.
    """
    run = run_simulation(
        cfg(adversarial=attacker(("DELAYED_WAKE",), delayed_wake_extra_latency=5.0,
                                 maximum_actions_per_round=50),
            reserve_fraction=0.25, horizon=60.0,
            floor=SecurityFloorPolicy(enabled=True, minimum_active_hash_rate=150.0)),
        run_id="s5b-05")
    recs = list(run.delayed_wake_actions.values())
    assert recs, "the scenario must produce real delayed-wake actions"
    flagged = [r for r in recs if r.another_reserve_activated]
    assert flagged, "another_reserve_activated must be reachable and true here"

    seated = [(req.MinerID, req.seated_at) for req in run.activation_requests.values()
              if req.seated_at is not None]
    assert seated, "the seating time must be recorded on the activation request"
    for rec in flagged:
        lo = rec.honest_expected_wake_time
        hi = rec.actual_wake_time if rec.actual_wake_time is not None else run.run_end_time
        assert any(mid != rec.MinerID and lo <= t <= hi for mid, t in seated), \
            "the flag must be backed by a real activation seated inside the added interval"
    # the measured floor overlap is a REAL observation, not a constant.
    assert run.adversarial_stats["attack_induced_floor_breach_duration"] > 0.0
    assert sum(r.below_floor_overlap for r in recs) > 0.0


def test_s5b_06_a_wake_cancelled_before_its_delay_ends_charges_only_the_realised_delay():
    """S5B-06: a delayed wake still pending when the round closes is charged over the interval
    it ACTUALLY realised, not the configured extra latency.

    ``incremental_wake_energy_j`` was ``P_wake * configured_extra_delay`` — an energy figure the
    simulation never spent.  It is now ``P_wake * realised_extra_delay``.
    """
    extra, horizon = 50.0, 20.0
    run = run_simulation(cfg(adversarial=attacker(("DELAYED_WAKE",), miners=_ALL,
                                                  delayed_wake_extra_latency=extra,
                                                  maximum_actions_per_round=100),
                             horizon=horizon), run_id="s5b-06")
    recs = list(run.delayed_wake_actions.values())
    assert recs
    cancelled = [r for r in recs if r.actual_wake_time is None]
    assert cancelled, "the scenario must leave a wake pending at round closure"
    p_wake = run.config.per_miner_power("WAKING")
    for rec in cancelled:
        assert rec.extra_delay == extra
        assert 0.0 < rec.realised_extra_delay < extra                # only what really elapsed
        assert rec.incremental_wake_energy_j == pytest.approx(p_wake * rec.realised_extra_delay)
        assert rec.incremental_wake_energy_j < p_wake * extra        # never the configured delay

    # a wake that DOES complete realises its full configured delay.
    done = run_simulation(cfg(adversarial=attacker(("DELAYED_WAKE",), miners=_ALL,
                                                   delayed_wake_extra_latency=5.0,
                                                   maximum_actions_per_round=100),
                              horizon=60.0), run_id="s5b-06-complete")
    completed = [r for r in done.delayed_wake_actions.values() if r.actual_wake_time is not None]
    assert completed
    assert all(r.realised_extra_delay == pytest.approx(r.extra_delay) for r in completed)


# ============================================================ S5B-5 centralised action budget
def test_s5b_07_a_zero_action_budget_blocks_every_action_type_and_replay_costs_nothing():
    """S5B-07: ``maximum_actions_per_round = 0`` prevents solution withholding and out-of-range
    actions (and every other action type), and an exact replay consumes no budget."""
    run = RunInitialise(cfg(adversarial=attacker(("SOLUTION_WITHHOLDER", "OUT_OF_RANGE_ACTOR"),
                                                 solution_release_policy="NEVER_RELEASE",
                                                 out_of_range_nonce_offset=5,
                                                 maximum_actions_per_round=0)))
    rc = _rc("round-1", "tpl")
    _profile(run, M0, ("SOLUTION_WITHHOLDER", "OUT_OF_RANGE_ACTOR"), round_id="round-1",
             solution_release_policy="NEVER_RELEASE")
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25

    # solution withholding: refused, with NO protocol effect (no withheld record, no acceptance
    # suppression) — the caller therefore seats acceptance normally.
    assert adv.maybe_withhold_solution(run, rc, st, 30, 0, 1.0) is False
    assert run.withheld_solutions == {}
    # out-of-range attempt: refused, and no invalid-action record is created.
    assert adv.maybe_out_of_range_attempt(run, rc, st, 1.0) is None
    assert run.invalid_actions == {}
    assert run.adversarial_stats["solution_withholding_count"] == 0
    assert run.adversarial_stats["out_of_range_attempt_count"] == 0
    assert run.adversarial_stats["actions_rejected_over_limit"] >= 2
    assert run.adv_actions_this_round.get("round-1", 0) == 0

    # ONE action authority: the same limit governs every action type, including the delayed wake.
    _profile(run, M1, ("DELAYED_WAKE",), round_id="round-1")
    assert adv.wake_extra_latency(run, rc, M1, 1.0, 0.0, request_id=("PRIMARY_WAKE", M1, "A1", 1),
                                  lifecycle="PRIMARY_WAKE") == 0.0
    assert run.delayed_wake_actions == {}

    # with a budget of 1, the first action is charged and its EXACT replay costs nothing more.
    run2 = RunInitialise(cfg(adversarial=attacker(("SOLUTION_WITHHOLDER",),
                                                  solution_release_policy="NEVER_RELEASE",
                                                  maximum_actions_per_round=1)))
    rc2 = _rc("round-1", "tpl")
    _profile(run2, M0, ("SOLUTION_WITHHOLDER",), round_id="round-1",
             solution_release_policy="NEVER_RELEASE")
    st2 = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st2.cursor = 25
    assert adv.maybe_withhold_solution(run2, rc2, st2, 30, 0, 1.0) is True
    assert run2.adv_actions_this_round["round-1"] == 1
    assert adv.maybe_withhold_solution(run2, rc2, st2, 30, 0, 1.0) is True     # exact replay
    assert run2.adv_actions_this_round["round-1"] == 1                        # no second charge
    assert len(run2.withheld_solutions) == 1

    # materialising a behaviour profile is NOT an executed action and is never charged.
    run3 = RunInitialise(cfg(adversarial=attacker(("FREE_RIDER",),
                                                  maximum_actions_per_round=0)))
    rc3 = _rc("round-1", "tpl")
    adv.ensure_profile(run3, rc3, M0, 100.0)
    assert (("round-1", M0) in run3.behaviour_profiles)
    assert run3.adv_actions_this_round.get("round-1", 0) == 0
    assert run3.adversarial_stats["actions_rejected_over_limit"] == 0


# ============================================================ S5B-6 capacity conservation
def test_s5b_08_free_riding_at_one_half_and_splitting_four_ways_conserves_effective_capacity():
    """S5B-08: FREE_RIDER work_fraction 0.5 combined with ASSIGNMENT_SPLITTER x4 must budget the
    EFFECTIVE 50 nonces/s across four subassignments — never the pre-reduction nominal 100.

    ``create_subassignments`` used ``prof.actual_hash_rate`` as the budget, so a free rider that
    also split its assignment appeared to hold its full undiminished capacity.
    """
    run = run_simulation(cfg(adversarial=attacker(("FREE_RIDER", "ASSIGNMENT_SPLITTER"),
                                                  klass="RATIONAL",
                                                  free_rider_work_fraction=0.5,
                                                  assignment_split_count=4),
                             incentive=IncentivePolicy(enabled=True, r_work=1.0), horizon=30.0),
                         run_id="s5b-08")
    rc = run.current_round_context
    subs = [s for s in run.subassignments if s.RoundID == rc.RoundID and s.MinerID == M0]
    assert len(subs) == 4
    assert all(s.entity_capacity_budget == pytest.approx(50.0) for s in subs)
    assert sum(s.capacity_share for s in subs) == pytest.approx(50.0)     # 100 * 0.5, not 100
    assert all(s.capacity_share == pytest.approx(12.5) for s in subs)
    assert run.adversarial_stats["subassignment_capacity_residual"] == pytest.approx(0.0)

    # the physical search state really runs at the reduced effective rate.
    assert rc.search_states[M0].hash_rate == pytest.approx(50.0)
    acct = adv.subassignment_accounting(run, rc)
    row = next(r for r in acct["rows"] if r["EntityID"] == "E1")
    assert row["derived_physical_capacity"] == pytest.approx(50.0)
    assert row["effective_entity_hash_rate"] == pytest.approx(50.0)
    assert acct["max_physical_capacity_residual"] == pytest.approx(0.0)

    # HASH_RATE_MISREPORTER + ASSIGNMENT_SPLITTER: over-reporting buys no physical capacity.
    mis = run_simulation(cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",
                                                   "ASSIGNMENT_SPLITTER"), klass="RATIONAL",
                                                  reported_hash_rate_multiplier=5.0,
                                                  assignment_split_count=4),
                             incentive=IncentivePolicy(enabled=True, r_work=1.0), horizon=30.0),
                         run_id="s5b-08-misreport")
    mrc = mis.current_round_context
    msubs = [s for s in mis.subassignments if s.RoundID == mrc.RoundID and s.MinerID == M0]
    assert sum(s.capacity_share for s in msubs) == pytest.approx(100.0)   # the ACTUAL rate
    assert mis.behaviour_profiles[(mrc.RoundID, M0)].reported_hash_rate == pytest.approx(500.0)
    assert adv.subassignment_accounting(mis, mrc)["max_physical_capacity_residual"] \
        == pytest.approx(0.0)


def test_s5b_09_subassignment_and_identity_accounting_derive_from_records_without_extra_work():
    """S5B-09: the accounting is DERIVED from SubAssignmentRecords and VirtualIdentityRecords —
    every physical evaluation maps to exactly one subassignment — and splitting plus identity
    multiplication adds no throughput at all."""
    split = cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                     assignment_split_count=4, sybil_identity_count=3),
                incentive=IncentivePolicy(enabled=True, r_work=1.0), horizon=30.0)
    control = cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                       free_rider_work_fraction=1.0),
                  incentive=IncentivePolicy(enabled=True, r_work=1.0), horizon=30.0)
    run = run_simulation(split, run_id="s5b-09")
    ctl = run_simulation(control, run_id="s5b-09-control")
    rc = run.current_round_context

    # throughput is IDENTICAL to the unsplit control: splitting reorganises accounting only.
    assert run.adversarial_stats["physical_evaluation_count"] == \
        ctl.adversarial_stats["physical_evaluation_count"]
    assert len(run.evaluation_ledger) == len(ctl.evaluation_ledger)

    # every mapped position lands in exactly one subassignment; nothing is lost or double-counted.
    assert run.adversarial_stats["subassignment_unmapped_evaluation_count"] == 0
    assert run.adversarial_stats["subassignment_mapped_evaluation_count"] > 0
    subs = [s for s in run.subassignments if s.RoundID == rc.RoundID and s.MinerID == M0]
    assert len(subs) == 4
    mapped = sum(s.evaluated_nonce_count for s in subs)
    own_ledger = sum(r.interval_end - r.interval_start for r in run.evaluation_ledger
                     if r.RoundID == rc.RoundID and r.MinerID == M0)
    assert mapped == own_ledger                      # derived from the records, not a constant
    # the subranges partition the parent range exactly.
    ordered = sorted(subs, key=lambda s: s.range_start)
    assert ordered[0].range_start == rc.search_states[M0].range_start
    assert ordered[-1].range_end == rc.search_states[M0].range_end
    for a, b in zip(ordered, ordered[1:]):
        assert a.range_end == b.range_start

    # virtual identities are explicit records that grant NO physical capacity.
    ident = adv.virtual_identity_accounting(run, rc)
    assert ident["physical_capacity_granted_by_identities"] == 0.0
    assert run.adversarial_stats["virtual_identity_physical_capacity_granted"] == 0.0
    e1 = next(r for r in ident["rows"] if r["EntityID"] == "E1")
    assert e1["virtual_identity_count"] == 3 and e1["real_miner_count"] == 1
    assert e1["effective_entity_hash_rate"] == pytest.approx(100.0)
    assert all(v.grants_physical_capacity is False for v in run.virtual_identities)
    assert all(v.VirtualIdentityID in run.virtual_identity_by_id for v in run.virtual_identities)

    # multiple controlled miners with declared identities still conserve the entity's capacity.
    multi = run_simulation(cfg(adversarial=attacker(("ASSIGNMENT_SPLITTER",), miners=(M0, M1),
                                                    klass="RATIONAL", assignment_split_count=2,
                                                    sybil_identity_count=4),
                               incentive=IncentivePolicy(enabled=True, r_work=1.0),
                               horizon=30.0), run_id="s5b-09-multi")
    mrc = multi.current_round_context
    acct = adv.subassignment_accounting(multi, mrc)
    row = next(r for r in acct["rows"] if r["EntityID"] == "E1")
    assert sorted(row["split_miner_ids"]) == [M0, M1]
    assert row["derived_physical_capacity"] == pytest.approx(300.0)   # 100 + 200, unchanged
    assert row["physical_capacity_residual"] == pytest.approx(0.0)
    assert multi.adversarial_stats["subassignment_unmapped_evaluation_count"] == 0
    assert multi.adversarial_stats["entity_physical_capacity_residual"] == pytest.approx(0.0)


# ============================================================ S5B-7 coverage separation
def test_s5b_10_abandoning_seventy_five_nonces_records_a_gap_and_forbids_ordinary_exhaustion():
    """S5B-10: an executed abandonment with 75 unsearched nonces records a 75-nonce coverage gap,
    and its round can never close as ordinary or full-domain exhaustion.

    The Stage-5A evidence reported ``abandoned_nonce_count = 3000`` beside
    ``coverage_gap_nonce_count = 0`` and a ``round_exhausted_no_block`` closure.  That
    combination is now impossible.
    """
    run = RunInitialise(cfg(adversarial=attacker(("IDLE_POLICY_DEFECTOR",),
                                                 maximum_actions_per_round=10)))
    rc = _rc("round-1", "tpl")
    _profile(run, M0, ("IDLE_POLICY_DEFECTOR",), round_id="round-1")
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25                                   # 25 searched, 75 left

    rec = adv.maybe_abandon(run, rc, st, 5.0)
    assert rec is not None
    assert rec.actual_frontier == 25
    assert rec.actual_unsearched_suffix() == 75      # range_end - actual_frontier
    assert rec.abandoned_nonce_count() == 75
    assert run.adversarial_stats["coverage_gap_nonce_count"] == 75
    assert run.adv_round_coverage_gap["round-1"] == 75
    assert run.adversarial_stats["abandonment_coverage_gap_rounds"] == 1
    assert adv.round_has_coverage_gap(run, rc) is True

    # END TO END: a round holding abandonment gaps never closes as exhaustion.
    e2e = run_simulation(cfg(adversarial=attacker(("IDLE_POLICY_DEFECTOR",), miners=_ALL,
                                                  maximum_actions_per_round=50),
                             incentive=IncentivePolicy(enabled=True, r_work=1.0, q_abandon=11.0),
                             horizon=60.0), run_id="s5b-10-e2e")
    s = e2e.adversarial_stats
    assert s["abandonment_action_count"] > 0
    assert s["abandoned_nonce_count"] > 0
    assert s["coverage_gap_nonce_count"] >= s["abandoned_nonce_count"]     # never zero beside it
    assert s["abandonment_coverage_gap_rounds"] > 0
    reasons = {o.data.get("reason") for o in e2e.log if o.kind == "round_aborted"}
    assert "round_exhausted_no_block" not in reasons
    assert "full_domain_exhausted_no_block" not in reasons
    assert ADVERSARIAL_COVERAGE_GAP_NO_BLOCK in reasons
    # the operational security floor is re-evaluated at the abandonment capacity-change point.
    floor_run = run_simulation(cfg(adversarial=attacker(("IDLE_POLICY_DEFECTOR",), miners=_ALL,
                                                        maximum_actions_per_round=50),
                                   reserve_fraction=0.25, horizon=60.0,
                                   floor=SecurityFloorPolicy(enabled=True,
                                                             minimum_active_hash_rate=150.0)),
                               run_id="s5b-10-floor")
    assert any(getattr(o, "observation_reason", None) == "adversarial_abandonment"
               for o in floor_run.security_observations)


def test_s5b_11_a_false_claim_separates_overstatement_from_the_real_unsearched_suffix():
    """S5B-11: a false claim from an actual frontier of 25 to a reported 35 records a claim
    overstatement of 10 and an actual unsearched suffix of 75 — and the coverage gap and round
    closure use the SUFFIX, not the overstatement."""
    run = RunInitialise(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                 audit_detection_probability=0.0,
                                                 false_exhaustion_claims_range_end=False,
                                                 false_exhaustion_claim_offset=10,
                                                 maximum_actions_per_round=10)))
    rc = _rc("round-1", "tpl")
    _profile(run, M0, ("FALSE_EXHAUSTION_CLAIMER",), round_id="round-1",
             exhaustion_claim_policy="FALSE")
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25

    out = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    assert out is not None and out.kind == "false_exhaustion_accepted"
    claim = run.progress_claims[-1]
    assert claim.actual_frontier == 25 and claim.reported_frontier == 35
    assert claim.claim_overstatement == 10                  # reported - actual
    assert claim.actual_unsearched_suffix == 75             # range_end - actual
    assert run.adversarial_stats["claim_overstatement_total"] == 10
    # the GAP is the real unsearched suffix, never the (smaller) overstatement.
    assert out.data["coverage_gap_nonce_count"] == 75
    assert run.adversarial_stats["coverage_gap_nonce_count"] == 75
    assert run.adv_round_coverage_gap["round-1"] == 75
    assert adv.round_has_coverage_gap(run, rc) is True


# ============================================================ S5B-8 adapter + metric semantics
def test_s5b_12_adapter_exposes_the_range_end_flag_and_reconciles_the_physical_count():
    """S5B-12: the adapter maps ``false_exhaustion_claims_range_end`` and
    ``false_exhaustion_claim_offset`` so a configured offset has the SAME effect through every
    entry point, and ``physical_evaluation_count`` matches the evaluation ledger with range
    leases enabled AND disabled."""
    # --- the range-end flag and the offset both travel through the BlockSim mapping ---
    b = {"adversarial_enabled": True,
         "adversarial_entities": [("E1", "BYZANTINE", (M0,), None)],
         "miner_behaviours": [(0, M0, ("FALSE_EXHAUSTION_CLAIMER",))],
         "false_exhaustion_claims_range_end": False,
         "false_exhaustion_claim_offset": 10,
         "audit_detection_probability": 0.0,
         "num_miners": 4, "nonce_domain_size": 400, "horizon_T": 30.0, "batch_size": 25}
    mapped = stage2config_from_blocksim(b)
    assert mapped.adversarial.false_exhaustion_claims_range_end is False
    assert mapped.adversarial.false_exhaustion_claim_offset == 10
    # the default is preserved when the key is absent (no silent behaviour change).
    assert stage2config_from_blocksim(
        {k: v for k, v in b.items()
         if k != "false_exhaustion_claims_range_end"}).adversarial \
        .false_exhaustion_claims_range_end is True

    # a configured offset produces the SAME reported claim through all three entry points.
    def _claim(config):
        run = RunInitialise(config)
        rc = _rc("round-1", "tpl")
        _profile(run, M0, ("FALSE_EXHAUSTION_CLAIMER",), round_id="round-1",
                 exhaustion_claim_policy="FALSE")
        st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
        st.cursor = 25
        adv.maybe_false_exhaustion(run, rc, st, 5.0)
        return run.progress_claims[-1].reported_frontier

    direct = cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                      audit_detection_probability=0.0,
                                      false_exhaustion_claim_offset=10,
                                      maximum_actions_per_round=10))
    assert _claim(direct) == 35                      # offset is honoured, not silently ignored
    assert _claim(mapped) == 35                      # ... identically through the adapter

    # and the offset survives the full run_pocol_stage2 entry point.
    res = run_pocol_stage2(dict(b, horizon_T=20.0), run_id="s5b-12-adapter")
    assert res["false_exhaustion_claim_offset"] == 10
    assert res["false_exhaustion_claims_range_end"] is False
    assert res["schema_version"] == RESULT_SCHEMA_VERSION == "stage5b.1"

    # --- the physical evaluation count reconciles with the ledger, leases ON and OFF ---
    for leases in (False, True):
        lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                                 lease_duration=1e18, progress_timeout=1e18) if leases else None
        run = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                      free_rider_work_fraction=0.5),
                                 incentive=IncentivePolicy(enabled=True, r_work=1.0),
                                 horizon=30.0, lease=lease),
                             run_id=f"s5b-12-leases-{leases}")
        out = results_schema(run, run.config)
        ledger_total = sum(r.interval_end - r.interval_start for r in run.evaluation_ledger)
        assert run.evaluation_ledger, "the run must actually evaluate nonces"
        assert out["physical_evaluation_count"] == ledger_total > 0
        assert out["evaluation_ledger_nonce_total"] == ledger_total
        assert out["physical_evaluation_ledger_residual"] == 0

    # --- the security floor and reported-rate allocation EXECUTE TOGETHER ---
    combo = run_simulation(cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",), klass="RATIONAL",
                                                    reported_hash_rate_multiplier=5.0,
                                                    coordinator_uses_reported_hash_rate=True),
                               reserve_fraction=0.25, horizon=20.0,
                               floor=SecurityFloorPolicy(enabled=True,
                                                         minimum_active_hash_rate=1.0)),
                           run_id="s5b-12-combo")
    out = results_schema(combo, combo.config)
    assert out["reported_rate_allocation_enabled"] is True
    assert out["reported_rate_allocation_rounds"] > 0            # NOT silently ignored
    assert out["allocation_range_size_distortion_max_ratio"] > 1.0
    rc = combo.current_round_context
    ranges = sorted(v["range"] for v in rc.assignments.values())
    assert ranges[0][0] == 0
    for a, b_ in zip(ranges, ranges[1:]):
        assert a[1] == b_[0]                                     # disjoint and contiguous
    slices = combo.reserve_slices.get(rc.RoundID, [])
    assert slices, "the floor must still carve reserve-domain slices"
    assert slices[0].range_start == ranges[-1][1]                # primaries then reserve domain
    assert slices[-1].range_end == combo.config.nonce_domain_size
    # physical capacity still comes from the ACTUAL rate, never the reported one.
    assert rc.search_states[M0].hash_rate == pytest.approx(100.0)
    assert combo.behaviour_profiles[(rc.RoundID, M0)].reported_hash_rate == pytest.approx(500.0)
