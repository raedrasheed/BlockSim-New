"""Stage-5C executable-correction tests S5C-01 .. S5C-07.

Stage 5C closes four executable defects found in the Stage-5B acceptance review:

* S5C-1  identity and split amplification are DERIVED FROM EXECUTED RECORDS
         (``SubAssignmentRecord`` / ``VirtualIdentityRecord``), never from the REQUESTED
         ``assignment_split_count`` / ``sybil_identity_count``;
* S5C-2  ``physical_evaluation_count`` is GLOBAL and ledger-derived, so an honest
         Stage-5-disabled control reports its real physical evaluations instead of a hard zero
         beside a non-empty evaluation ledger;
* S5C-3  false-exhaustion replay is completely state-pure for BOTH the detected/rejected and
         the undetected/accepted disposition;
* S5C-4  the ownership reconciliation is INTERVAL-EXACT — every evaluation interval is split
         into already-covered and newly-covered atomic subintervals.

Every Stage-5B correction is preserved: the physical frontier never rewinds, unique physical
work is rewarded once, the canonical [0,80) + [40,100) example still pays 80/20,
``finalise_incentives`` stays replay-idempotent, and Stage 5 remains disabled by default.

Stage 5C adds NO security, fairness, incentive-compatibility or Sybil-resistance claim.  The
record-derived accounting is an exploratory SENSITIVITY model of how a naive scheme could be
inflated; it is never presented as Sybil resistance.
"""
from __future__ import annotations

import copy

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, RunInitialise, run_simulation,
                                 AdversarialPolicy, IncentivePolicy, MinerSearchState,
                                 MinerBehaviourProfile, RESULT_SCHEMA_VERSION)
from Models.PoCol.stage2 import adversarial_runtime as adv
from Models.PoCol.stage2.adapter import results_schema
from Models.PoCol.stage2.context import EvaluationRecord

_HARD = 1 << 300          # unreachable target: the whole domain is searched, no block is found
M0, M1, M2, M3 = "M000", "M001", "M002", "M003"


def cfg(*, adversarial=None, incentive=None, difficulty=_HARD, D=400, horizon=30.0, n=4,
        reserve_fraction=0.0, batch=25, lease=None, **kw):
    extra = {"range_lease": lease} if lease is not None else {}
    return Stage2Config(num_miners=n, reserve_fraction=reserve_fraction, nonce_domain_size=D,
                        difficulty=difficulty, batch_size=batch, horizon_T=horizon,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **extra, **kw)


def splitter(miners=(M0,), *, split=1, sybil=1, klass="RATIONAL"):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, ("ASSIGNMENT_SPLITTER",))
                                                    for m in miners),
                             assignment_split_count=split, sybil_identity_count=sybil)


def _entity_row(run, eid="E1"):
    rows = [r for r in adv.entity_reconciliation(run) if r["EntityID"] == eid]
    assert rows, f"no record-derived reconciliation row for {eid}"
    return rows[-1]


def _rc(round_id="r", template="t"):
    return type("RC", (), {"RoundID": round_id, "TemplateID_committed": template,
                           "block_accepted": False, "winner_miner_id": None,
                           "round_terminal_time": None})()


def _eval(run, mid, lo, hi, t, *, lineage="S1", aid="A"):
    run.evaluation_ledger.append(EvaluationRecord(
        RoundID="r", TemplateID="t", MinerID=mid, AssignmentID=aid, assignment_version=1,
        interval_start=lo, interval_end=hi, completion_time=t, contained_solution=False,
        winning_nonce=None, event_ref=None, assignment_kind="PRIMARY_ASSIGNMENT",
        RangeSliceID=lineage, LeaseID="L1", lease_generation=1, progress_generation=1,
        predecessor_lease_id=None))


# ================================================ S5C-1 record-derived identity amplification
def test_s5c_01_one_real_miner_plus_three_virtual_records_is_four_represented_identities():
    """S5C-01: one real miner plus three ``VirtualIdentityRecord``s yields FOUR represented
    identities and the naive reward uses four — the real miner is itself an identity.

    Before Stage 5C the factor was ``max(len(controlled_miner_ids), sybil_identity_count)``, a
    REQUESTED figure that both ignored the executed records and swallowed the real miner.
    """
    run = run_simulation(cfg(adversarial=splitter((M0,), split=1, sybil=3),
                             incentive=IncentivePolicy(enabled=True, r_work=1.0)),
                         run_id="s5c-01")
    rc = run.current_round_context
    row = _entity_row(run)
    assert row["real_miner_count"] == 1
    assert row["virtual_identity_record_count"] == 3
    assert row["total_identity_count"] == 4                      # 1 real + 3 virtual, not 3
    assert row["identity_amplification_ratio"] == 4.0

    # the records really exist and the count is read off them, not off the config.
    vids = [v for v in run.virtual_identities if v.RoundID == rc.RoundID and v.EntityID == "E1"]
    assert len(vids) == 3 and all(v.grants_physical_capacity is False for v in vids)
    assert row["virtual_identity_record_count"] == len(vids)

    # the naive view is exactly the unique physical work multiplied by the record-derived factors.
    assert row["naive_identity_reward"] == pytest.approx(
        row["unique_physical_work_reward"] * row["split_amplification_ratio"]
        * row["identity_amplification_ratio"])
    assert row["deduplicated_entity_reward"] == pytest.approx(row["unique_physical_work_reward"])
    assert run.adversarial_stats["identity_multiplication_amplification_ratio"] == 4.0


def test_s5c_02_two_real_miners_plus_five_virtual_records_is_seven_represented_identities():
    """S5C-02: two real miners plus five ``VirtualIdentityRecord``s yields SEVEN represented
    identities."""
    run = run_simulation(cfg(adversarial=splitter((M0, M1), split=1, sybil=5),
                             incentive=IncentivePolicy(enabled=True, r_work=1.0)),
                         run_id="s5c-02")
    rc = run.current_round_context
    row = _entity_row(run)
    assert row["real_miner_count"] == 2
    assert row["virtual_identity_record_count"] == 5
    assert row["total_identity_count"] == 7                      # 2 + 5, not 5
    assert row["identity_amplification_ratio"] == 7.0
    vids = [v for v in run.virtual_identities if v.RoundID == rc.RoundID and v.EntityID == "E1"]
    assert len(vids) == 5
    assert run.adversarial_stats["identity_multiplication_amplification_ratio"] == 7.0
    # identities still grant NO physical capacity — this is accounting, not capability.
    assert run.adversarial_stats["virtual_identity_physical_capacity_granted"] == 0.0


def test_s5c_03_a_split_request_larger_than_the_span_uses_the_records_actually_created():
    """S5C-03: a requested split count greater than the nonce span uses the ACTUAL number of
    ``SubAssignmentRecord``s created — a request can never override the executed records."""
    requested, span = 8, 3
    # 4 miners over a 12-nonce domain gives each miner a 3-nonce range; 8 parts cannot exist.
    run = run_simulation(cfg(adversarial=splitter((M0,), split=requested),
                            incentive=IncentivePolicy(enabled=True, r_work=1.0),
                            D=12, horizon=10.0, batch=25), run_id="s5c-03")
    rc = run.current_round_context
    subs = [s for s in run.subassignments if s.RoundID == rc.RoundID and s.EntityID == "E1"]
    assert len(subs) == span < requested                         # 3 records, not 8
    assert run.config.adversarial.assignment_split_count == requested   # the REQUEST is intact

    row = _entity_row(run)
    assert row["subassignment_record_count"] == span
    assert row["actual_split_units"] == span
    assert row["split_amplification_ratio"] == float(span)       # 3.0, never 8.0
    assert run.adversarial_stats["assignment_split_amplification_ratio"] == float(span)
    # the subranges still partition the parent range exactly (one nonce each here).
    ordered = sorted(subs, key=lambda s: s.range_start)
    assert ordered[0].range_start == rc.search_states[M0].range_start
    assert ordered[-1].range_end == rc.search_states[M0].range_end
    for a, b in zip(ordered, ordered[1:]):
        assert a.range_end == b.range_start


# ================================================ S5C-2 global ledger-derived physical count
def test_s5c_04_the_disabled_honest_control_reports_its_real_physical_evaluation_count():
    """S5C-04: the honest Stage-5-DISABLED control has a non-empty evaluation ledger and reports
    ``physical_evaluation_count == evaluation_ledger_nonce_total > 0`` with a zero residual.

    Reporting zero physical evaluations beside a populated ledger made the disabled control
    unusable as a comparison baseline.  Counting executed work is a REPORT, not a protocol
    effect: the disabled run still creates no adversarial action, claim, reward or penalty.
    """
    config = cfg()
    run = run_simulation(config, run_id="s5c-04")
    out = results_schema(run, config)

    assert run.evaluation_ledger, "the honest control must really evaluate nonces"
    ledger_total = sum(r.interval_end - r.interval_start for r in run.evaluation_ledger)
    assert out["evaluation_ledger_nonce_total"] == ledger_total > 0
    assert out["physical_evaluation_count"] == ledger_total          # NOT zero
    assert out["physical_evaluation_ledger_residual"] == 0

    # Stage 5 disabled still means NO adversarial action, claim, reward or penalty.
    assert config.adversarial.enabled is False and config.incentive.enabled is False
    assert run.behaviour_profiles == {} and run.adversarial_entities == {}
    assert run.incentive_ledger == [] and run.progress_claims == []
    assert run.withheld_solutions == {} and run.invalid_actions == {}
    assert run.abandonment_actions == [] and run.delayed_wake_actions == {}
    assert run.subassignments == [] and run.virtual_identities == []
    assert run.adversarial_stats["false_exhaustion_attempted"] == 0
    assert run.adversarial_stats["coverage_gap_nonce_count"] == 0
    assert run.adversarial_stats["work_reward_total"] == 0.0


def test_s5c_05_the_ledger_equality_holds_enabled_and_with_leases_on_and_off():
    """S5C-05: the same equality holds with Stage 5 ENABLED and with range leases both enabled
    and disabled — four independent executions, one reconciliation rule."""
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)
    attacker = AdversarialPolicy(enabled=True,
                                 entities=(("E1", "RATIONAL", (M0,), None),),
                                 miner_behaviours=((0, M0, ("FREE_RIDER",)),),
                                 free_rider_work_fraction=0.5)
    cases = {
        "disabled_no_leases": cfg(),
        "disabled_with_leases": cfg(lease=lease),
        "enabled_no_leases": cfg(adversarial=attacker,
                                 incentive=IncentivePolicy(enabled=True, r_work=1.0)),
        "enabled_with_leases": cfg(adversarial=attacker, lease=lease,
                                   incentive=IncentivePolicy(enabled=True, r_work=1.0)),
    }
    for label, config in cases.items():
        run = run_simulation(config, run_id=f"s5c-05-{label}")
        out = results_schema(run, config)
        ledger_total = sum(r.interval_end - r.interval_start for r in run.evaluation_ledger)
        assert ledger_total > 0, label
        assert out["physical_evaluation_count"] == ledger_total, label
        assert out["evaluation_ledger_nonce_total"] == ledger_total, label
        assert out["physical_evaluation_ledger_residual"] == 0, label
    assert RESULT_SCHEMA_VERSION == "stage5c.1"


# ================================================ S5C-3 state-pure false-exhaustion replay
def _false_exhaustion_fixture(detect):
    pol = AdversarialPolicy(enabled=True,
                            entities=(("E1", "BYZANTINE", (M0,), None),),
                            miner_behaviours=((0, M0, ("FALSE_EXHAUSTION_CLAIMER",)),),
                            audit_detection_probability=detect,
                            false_exhaustion_claims_range_end=False,
                            false_exhaustion_claim_offset=10,
                            maximum_actions_per_round=10)
    run = RunInitialise(cfg(adversarial=pol))
    rc = _rc("round-1", "tpl")
    run.behaviour_profiles[("round-1", M0)] = MinerBehaviourProfile(
        MinerID=M0, EntityID="E1", RoundID="round-1",
        behaviour_set=("FALSE_EXHAUSTION_CLAIMER",), actual_hash_rate=100.0,
        reported_hash_rate=100.0, work_fraction=1.0, wake_delay_multiplier=1.0,
        solution_release_policy="PROMPT_RELEASE", progress_reporting_policy="HONEST",
        exhaustion_claim_policy="FALSE", assignment_split_count=1,
        identity_group_id="E1", behaviour_generation=0)
    st = MinerSearchState(M0, "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st.cursor = 25
    return run, rc, st


def _snapshot(run, st):
    """The FULL protocol + metrics snapshot the directive requires to be unchanged."""
    return {
        "stats": copy.deepcopy(run.adversarial_stats),
        "adv_actions_this_round": dict(run.adv_actions_this_round),
        "progress_claims": [(c.ClaimID, c.detected, c.accepted, c.actual_frontier,
                             c.reported_frontier, c.accepted_frontier, c.claim_overstatement,
                             c.actual_unsearched_suffix) for c in run.progress_claims],
        "adversarial_actions": sorted(map(str, run.adversarial_actions)),
        "coverage_gap": dict(run.adv_round_coverage_gap),
        "actual_frontier": dict(run.adv_actual_frontier),
        "event_queue": len(run.event_queue.queued_event_registry),
        "search_state": (st.cursor, st.completed, st.completion_kind, st.searched_count),
        "miner_states": {m: r.state for m, r in run.miners.items()},
    }


@pytest.mark.parametrize("detect,label", [(1.0, "detected"), (0.0, "accepted")])
def test_s5c_06_exact_false_exhaustion_replay_leaves_the_whole_snapshot_unchanged(detect, label):
    """S5C-06: exact replay of one false-exhaustion claim leaves the full protocol and metrics
    snapshot unchanged, and returns the SAME stored result.

    A DETECTED claim leaves the search state running, so before Stage 5C replaying it re-charged
    the attempt, appended a second ``ProgressClaim`` and re-incremented the detection counter.
    An ACCEPTED claim set ``st.completed``, so a guard-first ordering made its replay answer
    ``None`` instead of the outcome it had produced.  The immutable action identity is now
    resolved BEFORE every guard, counter and mutation.
    """
    run, rc, st = _false_exhaustion_fixture(detect)

    first = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    after_first = _snapshot(run, st)
    if label == "detected":
        assert first is None                                     # rejected, miner continues
        assert run.adversarial_stats["false_exhaustion_detected"] == 1
    else:
        assert first is not None and first.kind == "false_exhaustion_accepted"
        assert run.adversarial_stats["false_exhaustion_accepted"] == 1

    second = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    third = adv.maybe_false_exhaustion(run, rc, st, 5.0)
    after_replays = _snapshot(run, st)

    # the SAME stored result, for both dispositions.
    assert second is first and third is first
    # and nothing at all changed — every field the directive enumerates and the whole snapshot.
    assert after_replays == after_first
    for key in ("false_exhaustion_attempted", "false_exhaustion_detected",
                "false_exhaustion_accepted", "coverage_gap_nonce_count",
                "claim_overstatement_total"):
        assert after_replays["stats"][key] == after_first["stats"][key], key
    assert len(run.progress_claims) == 1
    assert run.adv_actions_this_round.get("round-1", 0) == 1      # charged exactly once


def test_s5c_06b_replaying_an_over_limit_rejection_counts_one_refusal_per_identity():
    """S5C-06 (companion): a replay of an over-limit REJECTED action does not increment the
    rejection diagnostic more than once for the same immutable action identity."""
    run, rc, st = _false_exhaustion_fixture(0.0)
    run.config.adversarial.__dict__["maximum_actions_per_round"] = 0   # refuse everything

    assert adv.maybe_false_exhaustion(run, rc, st, 5.0) is None
    assert run.adversarial_stats["actions_rejected_over_limit"] == 1
    for _ in range(4):                                            # same identity, re-offered
        assert adv.maybe_false_exhaustion(run, rc, st, 5.0) is None
    assert run.adversarial_stats["actions_rejected_over_limit"] == 1     # still ONE
    assert run.progress_claims == [] and run.adv_actions_this_round.get("round-1", 0) == 0


# ================================================ S5C-4 interval-exact reconciliation
def test_s5c_07_the_ownership_reconciliation_is_split_into_exact_subintervals():
    """S5C-07: for M000 evaluating [0,80) and M001 evaluating [40,100), the reconciliation
    contains exactly [0,40), [40,80) and [80,100) — never [40,100) as one duplicate interval —
    and reconciles to the reward ledger."""
    run = RunInitialise(cfg(incentive=IncentivePolicy(enabled=True, r_work=1.0),
                            adversarial=AdversarialPolicy(
                                enabled=True,
                                entities=(("E1", "BYZANTINE", (M0,), None),),
                                miner_behaviours=((0, M0, ("PROGRESS_WITHHOLDER",)),))))
    rc = _rc()
    _eval(run, M0, 0, 80, 1.0)
    _eval(run, M1, 40, 100, 2.0)
    adv.finalise_incentives(run, rc, 10.0)

    rows = adv.ownership_reconciliation(run)
    assert [r["nonce_interval"] for r in rows] == [[0, 40], [40, 80], [80, 100]]

    a, b, c = rows
    assert (a["first_evaluator"], a["reward_owner"], a["later_evaluators"]) == (M0, M0, [])
    assert (a["rewarded_count"], a["duplicate_reward_prevented_count"]) == (40, 0)

    assert (b["first_evaluator"], b["reward_owner"], b["later_evaluators"]) == (M0, M0, [M1])
    assert (b["rewarded_count"], b["duplicate_reward_prevented_count"]) == (40, 40)

    assert (c["first_evaluator"], c["reward_owner"], c["later_evaluators"]) == (M1, M1, [])
    assert (c["rewarded_count"], c["duplicate_reward_prevented_count"]) == (20, 0)

    # no row is the whole raw [40,100) interval.
    assert [40, 100] not in [r["nonce_interval"] for r in rows]

    # ---- the table reconciles to the metrics and to the reward ledger ----
    s = run.adversarial_stats
    assert sum(r["rewarded_count"] for r in rows) == s["unique_rewarded_nonce_count"] == 100
    assert sum(r["duplicate_reward_prevented_count"] for r in rows) \
        == s["duplicate_work_reward_prevented_count"] == 40

    owner_totals = {}
    for r in rows:
        owner_totals[r["reward_owner"]] = owner_totals.get(r["reward_owner"], 0) + \
            r["rewarded_count"]
    ledger_totals = {}
    for e in run.incentive_ledger:
        if e.component == "WORK_REWARD":
            ledger_totals[e.MinerID] = ledger_totals.get(e.MinerID, 0.0) + e.amount
    assert owner_totals == {M0: 80, M1: 20}                       # unchanged 80/20 ownership
    assert ledger_totals == {M0: 80.0, M1: 20.0}
    assert owner_totals.keys() == ledger_totals.keys()
    for mid, positions in owner_totals.items():
        assert ledger_totals[mid] == pytest.approx(float(positions))

    # S5B-2 is preserved: finalising again changes neither the ledger nor any derived metric.
    stats_before = copy.deepcopy(run.adversarial_stats)
    rows_before = copy.deepcopy(rows)
    ledger_before = len(run.incentive_ledger)
    adv.finalise_incentives(run, rc, 10.0)
    assert run.adversarial_stats == stats_before
    assert adv.ownership_reconciliation(run) == rows_before
    assert len(run.incentive_ledger) == ledger_before
