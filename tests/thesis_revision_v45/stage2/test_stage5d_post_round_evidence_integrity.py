"""Stage-5D post-round evidence-integrity tests S5D-01 .. S5D-03.

The Stage-5C evidence generator defined

    post_round_evaluation_count = len(run.evaluation_ledger)

which counts EVERY evaluation record rather than the evaluations occurring after their round
closed.  A metric named "post-round" that is really "all records" cannot detect the defect it
exists to detect: it is non-zero in every healthy run and would stay non-zero if genuine
post-round work appeared.

Stage 5D replaces it with a CAUSAL computation over the immutable evaluation ledger and
``run_ctx.round_terminal_times``:

* ``post_round_evaluation_record_count`` — records whose ``completion_time`` is strictly later
  than their round's terminal time plus a declared tolerance;
* ``post_round_evaluation_nonce_count`` — the nonce positions those records cover;
* ``evaluation_missing_terminal_time_count`` — finalised records whose ``RoundID`` has no
  terminal time at all.  A missing terminal time is never silently treated as valid.

These tests compute all three INDEPENDENTLY, from the ledger and the terminal-time registry
directly — they never read the reported value and compare it with itself.

Stage 5D changes no executable model code, adds no security, fairness,
incentive-compatibility or Sybil-resistance claim, and does not begin Stage 6.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, run_simulation, AdversarialPolicy,
                                 IncentivePolicy, RangeLeasePolicy)

_HARD = 1 << 300          # unreachable target: the whole domain is searched, no block is found
_TRIVIAL = 1              # target == 2^256 - 1: every nonce is a valid solution
M0, M1, M2, M3 = "M000", "M001", "M002", "M003"
_ALL = (M0, M1, M2, M3)

#: S5D-1 declared floating-point tolerance for the causal post-round comparison.  Simulation
#: times are IEEE doubles produced by repeated addition, so a record completing exactly AT its
#: round's terminal time may differ in the last ulp.  Only work strictly later than
#: ``terminal_time + POST_ROUND_TOLERANCE`` is post-round.
POST_ROUND_TOLERANCE = 1e-9


def post_round_audit(run, tolerance: float = POST_ROUND_TOLERANCE):
    """Compute the three integrity metrics INDEPENDENTLY from immutable run state.

    This deliberately re-derives the quantities from ``run.evaluation_ledger`` and
    ``run.round_terminal_times`` rather than reading any reported field, so the assertions
    below verify the simulation rather than verifying a report against itself.
    """
    post_records = 0
    post_nonces = 0
    missing_terminal_time = 0
    for rec in run.evaluation_ledger:
        terminal_time = run.round_terminal_times.get(rec.RoundID)
        if terminal_time is None:
            missing_terminal_time += 1          # never silently treated as valid
            continue
        if rec.completion_time > terminal_time + tolerance:
            post_records += 1
            post_nonces += max(0, rec.interval_end - rec.interval_start)
    return {
        "post_round_evaluation_record_count": post_records,
        "post_round_evaluation_nonce_count": post_nonces,
        "evaluation_missing_terminal_time_count": missing_terminal_time,
    }


def cfg(**kw):
    base = dict(num_miners=4, reserve_fraction=0.0, nonce_domain_size=400,
                difficulty=_HARD, batch_size=25, horizon_T=30.0)
    base.update(kw)
    return Stage2Config(**base)


_LEASE = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                          lease_duration=1e18, progress_timeout=1e18)
_INC = IncentivePolicy(enabled=True, r_work=1.0)


def _adv(flags, miners=(M0,), klass="RATIONAL", **pol):
    return AdversarialPolicy(enabled=True,
                             entities=(("E1", klass, tuple(miners), None),),
                             miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


_FREE_RIDER = _adv(("FREE_RIDER",), free_rider_work_fraction=0.5)
_WITHHOLDER = _adv(("PROGRESS_WITHHOLDER",), klass="BYZANTINE",
                   audit_detection_probability=0.0, progress_withholding_fraction=0.5)

#: the eight scenarios the directive enumerates, each an EXECUTED simulation.
SCENARIOS = {
    "disabled_honest_control": cfg(),
    "enabled_without_leases": cfg(adversarial=_FREE_RIDER, incentive=_INC),
    "enabled_with_leases": cfg(adversarial=_FREE_RIDER, incentive=_INC, range_lease=_LEASE),
    # Path A: no reserve domain, and the fault lands once another PRIMARY has exhausted its own
    # range, so the reassignee is an already-alive miner and no Stage-3 wake is needed.
    "path_a_reassignment": cfg(adversarial=_WITHHOLDER, incentive=_INC, range_lease=_LEASE,
                               horizon_T=90.0,
                               injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)),
    "path_b_reassignment": cfg(adversarial=_WITHHOLDER, incentive=_INC, range_lease=_LEASE,
                               horizon_T=120.0, reserve_fraction=0.5,
                               injected_lease_faults=((1, M0, 1.3, "MINER_FAILED"),)),
    "abandonment_coverage_gap": cfg(
        adversarial=_adv(("IDLE_POLICY_DEFECTOR",), miners=_ALL, klass="BYZANTINE",
                         maximum_actions_per_round=50),
        incentive=_INC, horizon_T=60.0),
    "false_exhaustion_coverage_gap": cfg(
        adversarial=_adv(("FALSE_EXHAUSTION_CLAIMER",), miners=_ALL, klass="BYZANTINE",
                         audit_detection_probability=0.0, maximum_actions_per_round=50),
        incentive=_INC, horizon_T=60.0),
    "solution_withholding": cfg(
        adversarial=_adv(("SOLUTION_WITHHOLDER",), miners=_ALL, klass="BYZANTINE",
                         solution_release_policy="NEVER_RELEASE",
                         maximum_actions_per_round=50),
        incentive=_INC, difficulty=_TRIVIAL, horizon_T=30.0),
}


# ============================================================ S5D-2 executable acceptance checks
@pytest.mark.parametrize("label", sorted(SCENARIOS))
def test_s5d_01_no_evaluation_is_committed_after_its_round_closed(label):
    """S5D-01: in every required scenario, no EvaluationRecord completes after its own round's
    terminal time, no post-round nonce is committed, and every record's round has a terminal
    time.  Computed independently from the immutable ledger and ``round_terminal_times``."""
    run = run_simulation(SCENARIOS[label], run_id=f"s5d-01-{label}")
    assert run.evaluation_ledger, f"{label}: the scenario must really evaluate nonces"

    audit = post_round_audit(run)
    assert audit["post_round_evaluation_record_count"] == 0, label
    assert audit["post_round_evaluation_nonce_count"] == 0, label
    assert audit["evaluation_missing_terminal_time_count"] == 0, label

    # every record's round really is present in the terminal-time registry.
    ledger_rounds = {r.RoundID for r in run.evaluation_ledger}
    assert ledger_rounds <= set(run.round_terminal_times), label
    # and every record completes at or before its round's terminal time.
    for rec in run.evaluation_ledger:
        tt = run.round_terminal_times[rec.RoundID]
        assert rec.completion_time <= tt + POST_ROUND_TOLERANCE, (label, rec.RoundID)


def test_s5d_02_the_corrected_metric_is_not_the_ledger_length():
    """S5D-02: the corrected metric measures post-round work, not ledger size.

    The superseded Stage-5C definition (``len(run.evaluation_ledger)``) is non-zero in every
    healthy run, so it could never have detected post-round work.  A metric that cannot fail is
    not evidence.  This test pins the distinction and shows the corrected computation DOES
    respond to genuine post-round work.
    """
    run = run_simulation(SCENARIOS["enabled_with_leases"], run_id="s5d-02")
    audit = post_round_audit(run)

    superseded = len(run.evaluation_ledger)          # the invalid Stage-5C definition
    assert superseded > 0                            # ... always non-zero in a healthy run
    assert audit["post_round_evaluation_record_count"] == 0
    assert superseded != audit["post_round_evaluation_record_count"]

    # POSITIVE CONTROL: the corrected computation is sensitive.  Shrinking one round's terminal
    # time below its own records' completion times must make the audit report them.
    victim = run.evaluation_ledger[-1]
    affected = [r for r in run.evaluation_ledger if r.RoundID == victim.RoundID]
    earliest = min(r.completion_time for r in affected)
    probe = dict(run.round_terminal_times)
    probe[victim.RoundID] = earliest - 1.0
    original = run.round_terminal_times
    try:
        run.round_terminal_times = probe
        tampered = post_round_audit(run)
    finally:
        run.round_terminal_times = original
    assert tampered["post_round_evaluation_record_count"] == len(affected) > 0
    assert tampered["post_round_evaluation_nonce_count"] == sum(
        r.interval_end - r.interval_start for r in affected) > 0
    assert tampered["evaluation_missing_terminal_time_count"] == 0

    # POSITIVE CONTROL: a missing terminal time is COUNTED, never silently accepted.
    probe_missing = {k: v for k, v in run.round_terminal_times.items() if k != victim.RoundID}
    try:
        run.round_terminal_times = probe_missing
        missing = post_round_audit(run)
    finally:
        run.round_terminal_times = original
    assert missing["evaluation_missing_terminal_time_count"] == len(affected) > 0
    # the skipped records are NOT counted as post-round — they are reported as missing instead.
    assert missing["post_round_evaluation_record_count"] == 0

    # the audit is restored exactly.
    assert post_round_audit(run) == audit


def test_s5d_03_the_required_scenarios_really_exercise_their_named_behaviour():
    """S5D-03: the eight scenarios are not vacuous — each really performs the behaviour it is
    named for, so the zero post-round result is evidence rather than an absence of activity."""
    runs = {label: run_simulation(c, run_id=f"s5d-03-{label}")
            for label, c in SCENARIOS.items()}

    # the disabled control is genuinely disabled yet genuinely searches.
    ctl = runs["disabled_honest_control"]
    assert ctl.behaviour_profiles == {} and ctl.incentive_ledger == []
    assert sum(r.interval_end - r.interval_start for r in ctl.evaluation_ledger) > 0

    # leases really engaged where they are supposed to be.
    assert runs["enabled_with_leases"].range_leases
    assert not runs["enabled_without_leases"].range_leases

    # Path A really seated a reassignment WITHOUT a Stage-3 wake ...
    pa = runs["path_a_reassignment"]
    assert pa.lease_stats["reassignment_requests_seated"] >= 1
    assert pa.lease_stats["wake_handles_created"] == 0
    assert not [r for r in pa.reassignment_requests.values() if r.needs_stage3_wake]

    # ... and Path B really is Path B: a Stage-3 wake through a non-domain wake handle.
    pb = runs["path_b_reassignment"]
    assert pb.lease_stats["wake_handles_created"] >= 1
    wake_reqs = [r for r in pb.reassignment_requests.values() if r.needs_stage3_wake]
    assert wake_reqs
    act = pb.activation_requests[wake_reqs[0].reserve_activation_request_id]
    assert act.activation_scope == "REASSIGNMENT_WAKE_ONLY"

    # the coverage-gap scenarios really produced coverage gaps.
    ab = runs["abandonment_coverage_gap"].adversarial_stats
    assert ab["abandonment_action_count"] > 0 and ab["coverage_gap_nonce_count"] > 0
    fe = runs["false_exhaustion_coverage_gap"].adversarial_stats
    assert fe["false_exhaustion_accepted"] > 0 and fe["coverage_gap_nonce_count"] > 0

    # withholding really withheld a valid solution.
    sw = runs["solution_withholding"]
    assert sw.adversarial_stats["solution_withholding_count"] > 0
    assert sw.withheld_solutions

    # and the integrity metrics are zero in all eight.
    for label, run in runs.items():
        audit = post_round_audit(run)
        assert audit == {"post_round_evaluation_record_count": 0,
                         "post_round_evaluation_nonce_count": 0,
                         "evaluation_missing_terminal_time_count": 0}, label
