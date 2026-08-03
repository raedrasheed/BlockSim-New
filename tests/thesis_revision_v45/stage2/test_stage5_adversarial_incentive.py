"""Stage-5 adversarial-behaviour + incentive-model tests S5-01 .. S5-26.

Stage 5 adds an explicit, bounded adversarial-behaviour layer and a parameterised incentive
layer ON TOP of the accepted, frozen Stage-4C PoCol core.  These tests lock what the layer
actually DOES:

* S5-1/S5-2  round-bound immutable behaviour profiles, disabled-by-default validated policies;
* S5-3/S5-4  the three-value actual / reported / accepted separation, with the physical search
             core ALWAYS running on the actual rate;
* S5-5       progress withholding and false exhaustion through one modeled audit abstraction;
* S5-6       solution withholding (prompt / delayed / never) through the normal acceptance path;
* S5-7       delayed wake (which COSTS wake energy — it is never an energy saving);
* S5-8       naive-identity vs entity-and-lineage-deduplicated reward accounting;
* S5-9       rejected out-of-range / invalid actions;
* S5-10      the replay-idempotent reward + penalty ledger;
* S5-11      q_adv(t) over ACTUAL active hash rates, reported NA when H_active == 0;
* S5-12      round-terminal adversarial actions and a replay-idempotent action registry;
* S5-13      the matched honest-vs-attacked pair harness.

WHAT THESE TESTS DO NOT ESTABLISH.  Stage 5 MODELS bounded behaviours and MEASURES outcomes.
Nothing here shows — and nothing in Stage 5 claims — incentive compatibility, fairness, Sybil
resistance, selfish-mining resistance, coalition resistance, common-prefix security,
chain-quality security or Bitcoin/PoW-equivalent security.  The energy-saving mechanism
remains the idle policy within PoCol; nonce-domain partitioning alone is never an energy-saving
mechanism.  The security floor remains an operational active-capacity floor only.  Dynamic
difficulty remains excluded, and no Stage-5 parameter changes the fixed SHA-256 target.

Every Stage-5 feature is disabled by default, so all 124 accepted tests are unchanged.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, RunInitialise, run_simulation,
                                 AdversarialPolicy, IncentivePolicy, audit_draw,
                                 ACTOR_CLASSES, ADVERSARIAL_ACTOR_CLASSES, BEHAVIOUR_FLAGS,
                                 SOLUTION_RELEASE_POLICIES, ACCOUNTING_MODES,
                                 ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
                                 run_matched_adversarial_pair, results_schema,
                                 stage2config_from_blocksim, RESULT_SCHEMA_VERSION)
from Models.PoCol.stage2 import adversarial_runtime as adv
from Models.PoCol.stage2.search import target_for_difficulty

_HARD = 1 << 300      # unreachable target: the whole domain is searched, no block is ever found
_TRIVIAL = 1          # target == 2^256 - 1: every nonce is a valid solution

M0, M1, M2, M3 = "M000", "M001", "M002", "M003"
_ALL = (M0, M1, M2, M3)


def cfg(*, adversarial=None, incentive=None, difficulty=_HARD, D=400, horizon=60.0,
        n=4, reserve_fraction=0.0, batch=25, lease=None, **kw):
    """A deterministic 4-miner Stage-5 scenario configuration."""
    extra = {}
    if lease is not None:
        extra["range_lease"] = lease
    return Stage2Config(num_miners=n, reserve_fraction=reserve_fraction, nonce_domain_size=D,
                        difficulty=difficulty, batch_size=batch, horizon_T=horizon,
                        adversarial=adversarial or AdversarialPolicy(),
                        incentive=incentive or IncentivePolicy(), **extra, **kw)


def attacker(flags, miners=(M0,), klass="BYZANTINE", **pol):
    """An AdversarialPolicy in which ``miners`` carry ``flags`` in every round."""
    return AdversarialPolicy(
        enabled=True,
        entities=(("E1", klass, tuple(miners), None),),
        miner_behaviours=tuple((0, m, tuple(flags)) for m in miners), **pol)


def terminal_reasons(run):
    return [o.data.get("reason") for o in run.log if o.kind == "round_aborted"]


# ============================================================== S5-1 / S5-2 defaults + profiles
def test_s5_01_every_stage5_feature_is_disabled_by_default():
    """S5-01: the Stage-5 model is OFF by default with every rate zero, so the frozen Stage-4C
    behaviour is reproduced exactly and the accepted baseline is preserved."""
    c = Stage2Config()
    assert c.adversarial.enabled is False
    assert c.incentive.enabled is False
    for rate in ("r_work", "r_avail", "r_win", "r_reserve", "r_reassign",
                 "q_abandon", "q_false", "q_invalid"):
        assert getattr(c.incentive, rate) == 0.0, rate
    assert c.adversarial.entities == () and c.adversarial.miner_behaviours == ()
    assert c.adversarial.free_rider_work_fraction == 1.0
    assert c.adversarial.solution_release_policy == "PROMPT_RELEASE"

    # a disabled run touches NO Stage-5 registry and produces NO Stage-5 effect.
    run = run_simulation(cfg(), run_id="s5-01")
    assert run.behaviour_profiles == {} and run.adversarial_entities == {}
    assert run.withheld_solutions == {} and run.invalid_actions == {}
    assert run.progress_claims == [] and run.incentive_ledger == []
    assert all(v in (0, 0.0, 1.0) for v in run.adversarial_stats.values())
    assert adv.q_adv_summary(run)["maximum_q_adv"] is None      # never observed => NA
    # the honest run still reaches its ordinary Stage-4C disposition.
    assert run.round_seq > 0 and terminal_reasons(run)


def test_s5_02_behaviour_profiles_are_round_bound_immutable_and_replay_safe():
    """S5-02: exactly one IMMUTABLE profile per (round, miner), materialised once; a repeat
    materialisation for the same round is a no-op, and a profile cannot be mutated."""
    run = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",),
                                                  free_rider_work_fraction=0.5)), run_id="s5-02")
    keys = list(run.behaviour_profiles)
    assert keys and len(set(keys)) == len(keys)               # one profile per (round, miner)
    prof = run.behaviour_profiles[keys[0]]
    assert prof.RoundID == keys[0][0] and prof.MinerID == keys[0][1]
    with pytest.raises(Exception):                            # frozen dataclass
        prof.work_fraction = 0.1
    # re-materialising the same round returns the existing profiles unchanged (replay-safe).
    rc = run.current_round_context
    before = dict(run.behaviour_profiles)
    adv.materialise_behaviours(run, rc, list(getattr(rc, "search_states", {})))
    assert run.behaviour_profiles == before


def test_s5_03_policies_reject_undeclared_vocabulary_and_out_of_range_parameters():
    """S5-2: both Stage-5 policies are VALIDATED — undeclared actor classes, behaviour flags,
    release policies, accounting modes and out-of-range rates are rejected at construction."""
    with pytest.raises(ValueError):
        AdversarialPolicy(enabled=True, entities=(("E", "SUPERVILLAIN", (M0,), None),))
    with pytest.raises(ValueError):
        AdversarialPolicy(enabled=True, miner_behaviours=((0, M0, ("TIME_TRAVELLER",)),))
    with pytest.raises(ValueError):
        AdversarialPolicy(enabled=True, solution_release_policy="PUBLISH_EVENTUALLY")
    with pytest.raises(ValueError):
        AdversarialPolicy(enabled=True, audit_detection_probability=1.5)
    with pytest.raises(ValueError):
        AdversarialPolicy(enabled=True, free_rider_work_fraction=-0.1)
    with pytest.raises(ValueError):
        IncentivePolicy(enabled=True, r_work=-1.0)
    with pytest.raises(ValueError):
        IncentivePolicy(enabled=True, reward_deduplication_policy="TRUST_THE_MINER")
    # the declared vocabularies themselves are stable.
    assert ADVERSARIAL_ACTOR_CLASSES == ("RATIONAL", "BYZANTINE", "ADVERSARIAL_COORDINATOR")
    assert set(ADVERSARIAL_ACTOR_CLASSES) < set(ACTOR_CLASSES)
    assert "SOLUTION_WITHHOLDER" in BEHAVIOUR_FLAGS
    assert "NEVER_RELEASE" in SOLUTION_RELEASE_POLICIES
    assert "ENTITY_AND_LINEAGE_DEDUPLICATED" in ACCOUNTING_MODES


def test_s5_04_only_strategic_actor_classes_count_as_adversarial():
    """S5-3/S5-11: HONEST and CRASH_FAULTY entities are NOT counted on the adversarial side of
    q_adv; RATIONAL / BYZANTINE / ADVERSARIAL_COORDINATOR are."""
    pol = AdversarialPolicy(enabled=True,
                            entities=(("H", "HONEST", (M0,), None),
                                      ("C", "CRASH_FAULTY", (M1,), None),
                                      ("R", "RATIONAL", (M2,), None),
                                      ("B", "BYZANTINE", (M3,), None)))
    run = run_simulation(cfg(adversarial=pol), run_id="s5-04")
    assert adv.is_adversarial_miner(run, M0) is False
    assert adv.is_adversarial_miner(run, M1) is False
    assert adv.is_adversarial_miner(run, M2) is True
    assert adv.is_adversarial_miner(run, M3) is True


# ============================================================== S5-4 actual vs reported
def test_s5_05_free_riding_reduces_the_actual_physical_rate_and_is_counted():
    """S5-4: a FREE_RIDER's declared work fraction reduces its EFFECTIVE physical hash rate, so
    it really does less work.  The ground-truth actual rate stays on the immutable profile."""
    honest = run_simulation(cfg(), run_id="s5-05-h")
    run = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                  free_rider_work_fraction=0.5)), run_id="s5-05")
    prof = next(p for k, p in run.behaviour_profiles.items() if k[1] == M0)
    assert "FREE_RIDER" in prof.behaviour_set and prof.work_fraction == 0.5
    assert run.adversarial_stats["free_rider_count"] > 0
    # the profile preserves the ACTUAL (pre-reduction) rate as ground truth ...
    assert prof.actual_hash_rate == honest.config.hash_rate_for(0)
    # ... while the physical search state runs at the reduced effective rate.
    st = run.current_round_context.search_states.get(M0)
    if st is not None:
        assert st.hash_rate == pytest.approx(prof.actual_hash_rate * 0.5)
    # a free rider genuinely evaluates fewer nonces than the same miner does honestly.
    def searched(r):
        return sum(v for (rid, mid), v in r.final_searched.items() if mid == M0)
    assert searched(run) < searched(honest)


def test_s5_06_a_misreported_hash_rate_never_changes_the_physical_search_rate():
    """S5-4: a HASH_RATE_MISREPORTER's REPORTED rate diverges from its ACTUAL rate, but the
    physical search core always runs on the actual rate — the claim buys no real work."""
    honest = run_simulation(cfg(), run_id="s5-06-h")
    run = run_simulation(cfg(adversarial=attacker(("HASH_RATE_MISREPORTER",),
                                                  klass="RATIONAL",
                                                  reported_hash_rate_multiplier=3.0)),
                         run_id="s5-06")
    prof = next(p for k, p in run.behaviour_profiles.items() if k[1] == M0)
    assert prof.reported_hash_rate == pytest.approx(prof.actual_hash_rate * 3.0)
    assert prof.reported_hash_rate != prof.actual_hash_rate
    assert run.adversarial_stats["hash_rate_misreport_count"] > 0
    assert run.adversarial_stats["allocation_distortion_max_ratio"] == pytest.approx(3.0)
    assert run.adversarial_stats["actual_reported_divergence_count"] > 0
    # the PHYSICAL state is untouched: the miner evaluates exactly as much as an honest one.
    st = run.current_round_context.search_states.get(M0)
    if st is not None:
        assert st.hash_rate == pytest.approx(prof.actual_hash_rate)
    def searched(r):
        return sum(v for (rid, mid), v in r.final_searched.items() if mid == M0)
    assert searched(run) == searched(honest)


# ============================================================== S5-5 modeled audit
def test_s5_07_the_modeled_audit_draw_is_deterministic_and_replay_idempotent():
    """S5-3: the audit outcome is a deterministic function of the seed and the IMMUTABLE claim
    identity, so replaying the same claim gets the same draw and creates no second record."""
    assert audit_draw(1, ("c", 1)) == audit_draw(1, ("c", 1))
    assert audit_draw(1, ("c", 1)) != audit_draw(2, ("c", 1))
    assert 0.0 <= audit_draw(7, ("c", 1)) < 1.0

    run = RunInitialise(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",))))
    rc = type("RC", (), {"RoundID": "r1", "TemplateID_committed": "t1"})()
    first = adv.audit_claim(run, rc, "L1", M0, 10, 40, "EXHAUSTION_CLAIM")
    again = adv.audit_claim(run, rc, "L1", M0, 10, 40, "EXHAUSTION_CLAIM")
    assert again is first                                     # idempotent: the SAME record
    assert len(run.progress_claims) == 1
    assert first.actual_frontier == 10 and first.reported_frontier == 40


def test_s5_08_a_detected_false_exhaustion_claim_is_rejected_and_the_real_state_stands():
    """S5-5: with the modeled audit detecting (p = 1), a false exhaustion claim is REJECTED —
    the miner keeps searching honestly, no coverage gap is created, and the round reaches an
    ordinary honest disposition."""
    run = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                  audit_detection_probability=1.0)),
                         run_id="s5-08")
    s = run.adversarial_stats
    assert s["false_exhaustion_attempted"] > 0
    assert s["false_exhaustion_detected"] == s["false_exhaustion_attempted"]
    assert s["false_exhaustion_accepted"] == 0
    assert s["coverage_gap_nonce_count"] == 0
    assert ADVERSARIAL_COVERAGE_GAP_NO_BLOCK not in terminal_reasons(run)
    assert all(c.detected and not c.accepted for c in run.progress_claims)


def test_s5_09_an_undetected_false_exhaustion_leaves_a_recorded_coverage_gap():
    """S5-5: with the modeled audit missing it (p = 0), the claim is ACCEPTED: the miner idles
    with an uncovered suffix, the ACTUAL frontier is preserved as ground truth, and the gap is
    counted in nonces rather than silently absorbed."""
    run = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                  audit_detection_probability=0.0)),
                         run_id="s5-09")
    s = run.adversarial_stats
    assert s["false_exhaustion_accepted"] > 0 and s["false_exhaustion_detected"] == 0
    assert s["coverage_gap_nonce_count"] > 0
    assert s["adversarial_coverage_gap_round_count"] > 0
    st = run.current_round_context.search_states.get(M0)
    if st is not None and st.completion_kind == "FALSE_EXHAUSTION_ACCEPTED":
        assert st.cursor < st.range_end                       # the suffix really is unsearched
    claims = [c for c in run.progress_claims if c.claim_type == "EXHAUSTION_CLAIM"]
    assert claims and all(c.accepted and c.accepted_frontier != c.actual_frontier
                          for c in claims)


def test_s5_10_a_coverage_gap_round_is_never_labelled_a_full_domain_exhaustion():
    """S5-5: a round holding an accepted-false-exhaustion gap did NOT search its domain, so it
    must never carry the full-domain exhaustion label.  It closes with its own honest label."""
    run = run_simulation(cfg(adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                  audit_detection_probability=0.0)),
                         run_id="s5-10")
    reasons = terminal_reasons(run)
    assert ADVERSARIAL_COVERAGE_GAP_NO_BLOCK in reasons
    assert "FULL_DOMAIN_EXHAUSTED_NO_BLOCK" not in reasons
    assert run.security_stats["full_domain_exhausted_count"] == 0
    # the honest control DOES honestly exhaust the same domain.
    honest = run_simulation(cfg(), run_id="s5-10-h")
    assert ADVERSARIAL_COVERAGE_GAP_NO_BLOCK not in terminal_reasons(honest)


# ============================================================== S5-6 solution withholding
def test_s5_11_a_withheld_solution_is_not_published_and_no_block_is_accepted():
    """S5-6: a SOLUTION_WITHHOLDER records the valid block it found as ground truth but seats no
    acceptance.  With every miner withholding, the round yields no block at all."""
    run = run_simulation(cfg(difficulty=_TRIVIAL,
                             adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=_ALL,
                                                  solution_release_policy="NEVER_RELEASE")),
                         run_id="s5-11")
    s = run.adversarial_stats
    assert s["solution_withholding_count"] > 0
    assert s["withheld_never_released_count"] > 0
    assert len(run.acceptance_times) == 0                     # nothing was ever accepted
    recs = list(run.withheld_solutions.values())
    assert recs and all(r.status == "HIDDEN_AT_CLOSE" for r in recs)
    # the solution really was valid against the round's fixed target (ground truth preserved).
    tgt = target_for_difficulty(_TRIVIAL)
    assert all(r.digest <= tgt and r.nonce >= 0 for r in recs)


def test_s5_12_a_delayed_release_is_accepted_through_the_normal_acceptance_path():
    """S5-6: DELAYED_RELEASE publishes at found_time + delay and is then accepted by the SAME
    acceptance path as a prompt publication — withholding does not bypass any check."""
    delay = 2.0
    run = run_simulation(cfg(difficulty=_TRIVIAL, horizon=30.0,
                             adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=_ALL,
                                                  solution_release_policy="DELAYED_RELEASE",
                                                  solution_withholding_delay=delay)),
                         run_id="s5-12")
    s = run.adversarial_stats
    assert s["solution_withholding_count"] > 0
    assert s["withheld_released_count"] > 0
    released = [r for r in run.withheld_solutions.values() if r.status == "RELEASED_ACCEPTED"]
    assert released
    for r in released:
        assert r.release_time == pytest.approx(r.found_time + delay)
        assert r.scheduled_release_time == pytest.approx(r.found_time + delay)
    assert len(run.acceptance_times) == s["withheld_released_count"]
    assert s["withheld_total_hidden_duration"] == pytest.approx(delay * len(released))


def test_s5_13_a_release_into_a_closed_round_performs_no_effect():
    """S5-6/S5-12: a withheld solution released after its round closed (or after another miner
    won) is REJECTED by the ordinary identity checks — it seats no acceptance."""
    run = RunInitialise(cfg(adversarial=attacker(("SOLUTION_WITHHOLDER",))))
    from Models.PoCol.stage2.simulator import _handle_withheld_release
    from Models.PoCol.stage2.adversarial import WithheldSolutionRecord
    ws_id = ("round-1", "tpl", M0, "A", 7)
    run.withheld_solutions[ws_id] = WithheldSolutionRecord(
        WithheldSolutionID=ws_id, RoundID="round-1", TemplateID="tpl", MinerID=M0,
        AssignmentID="A", assignment_version=1, nonce=7, digest=0, found_time=0.0,
        release_policy="DELAYED_RELEASE")
    run.current_round_context = type("RC", (), {
        "RoundID": "round-1", "TemplateID_committed": "tpl", "round_state": "ROUND_ABORTED",
        "block_accepted": False, "acceptance_seq": 0})()
    payload = {"WithheldSolutionID": ws_id, "RoundID_at_seat": "round-1",
               "TemplateID_at_seat": "tpl", "MinerID": M0, "nonce": 7}
    out = _handle_withheld_release(run, payload, {})
    assert out.kind == "withheld_release_stale_noop"
    assert run.withheld_solutions[ws_id].status == "RELEASED_TOO_LATE"
    assert run.adversarial_stats["withheld_release_too_late_count"] == 1
    # replaying the same release is a second no-op, not a second effect.
    assert _handle_withheld_release(run, payload, {}).kind == "withheld_release_replay_noop"
    assert run.adversarial_stats["withheld_release_too_late_count"] == 1


def test_s5_14_a_withheld_round_is_never_labelled_a_full_domain_exhaustion():
    """S5-6: a round in which a valid solution was hidden did not honestly fail to find one, so
    it must never be reported as a clean whole-domain exhaustion."""
    run = run_simulation(cfg(difficulty=_TRIVIAL,
                             adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=_ALL,
                                                  solution_release_policy="NEVER_RELEASE")),
                         run_id="s5-14")
    reasons = terminal_reasons(run)
    assert "FULL_DOMAIN_EXHAUSTED_NO_BLOCK" not in reasons
    assert run.security_stats["full_domain_exhausted_count"] == 0


# ============================================================== S5-7 delayed wake
def test_s5_15_a_delayed_wake_keeps_the_miner_waking_for_the_whole_extra_interval():
    """S5-7: DELAYED_WAKE extends the WAKING interval by the configured amount.  The action is
    recorded with both the honest and the adversarial wake time, and it completes at the later
    one — the miner contributes nothing to active capacity for the whole interval."""
    extra = 5.0
    run = run_simulation(cfg(adversarial=attacker(("DELAYED_WAKE",),
                                                  delayed_wake_extra_latency=extra)),
                         run_id="s5-15")
    assert run.adversarial_stats["delayed_wake_count"] > 0
    acts = [a for a in run.delayed_wake_actions.values() if a.MinerID == M0]
    assert acts
    for a in acts:
        assert a.extra_delay == pytest.approx(extra)
        assert a.adversarial_scheduled_wake_time == pytest.approx(
            a.honest_expected_wake_time + extra)
        if a.status == "COMPLETED":
            assert a.actual_wake_time == pytest.approx(a.adversarial_scheduled_wake_time)


def test_s5_16_delaying_a_wake_costs_wake_energy_and_never_saves_energy():
    """S5-7: the delayed waker is charged P_wake over the WHOLE extended interval.  Delaying a
    wake is a liveness cost, NOT an energy-saving mechanism — the energy-saving mechanism in
    PoCol remains the idle policy."""
    c_honest = cfg(horizon=20.0)
    c_delay = cfg(horizon=20.0, adversarial=attacker(("DELAYED_WAKE",),
                                                     delayed_wake_extra_latency=5.0))
    honest = run_simulation(c_honest, run_id="s5-16-h")
    delayed = run_simulation(c_delay, run_id="s5-16-d")
    assert c_honest.per_miner_power("WAKING") > 0.0
    waking = lambda r: r.miners[M0].duration.get("WAKING", 0.0)
    assert waking(delayed) > waking(honest)
    wake_energy = lambda r, c: c.per_miner_power("WAKING") * waking(r)
    assert wake_energy(delayed, c_delay) > wake_energy(honest, c_honest)


# ============================================================== S5-9 invalid / out-of-range
def test_s5_17_an_out_of_range_attempt_is_rejected_with_no_credit_of_any_kind():
    """S5-9: an OUT_OF_RANGE_ACTOR's attempt outside its own assigned range is REJECTED before
    any accounting — it enters no evaluation ledger, advances no frontier and earns no reward;
    it only becomes invalid-message penalty eligible."""
    inc = IncentivePolicy(enabled=True, r_work=1.0, q_invalid=5.0)
    run = run_simulation(cfg(incentive=inc,
                             adversarial=attacker(("OUT_OF_RANGE_ACTOR",),
                                                  out_of_range_nonce_offset=5)),
                         run_id="s5-17")
    s = run.adversarial_stats
    assert s["out_of_range_attempt_count"] > 0
    assert s["invalid_action_rejection_count"] == s["out_of_range_attempt_count"]
    recs = list(run.invalid_actions.values())
    assert recs and all(r.rejected and r.penalty_eligible and r.action_type == "OUT_OF_RANGE"
                        for r in recs)
    # the attacker's OWN evaluation records stay strictly inside its OWN assigned range: the
    # out-of-range attempt bought it no committed work anywhere.
    own_ranges = {rid: rng for rid, per in run.round_ranges.items()
                  for mid, rng in per.items() if mid == M0}
    own = [rec for rec in run.evaluation_ledger if rec.MinerID == M0]
    assert own
    for rec in own:
        lo, hi = own_ranges[rec.RoundID]
        assert lo <= rec.interval_start and rec.interval_end <= hi
    # and no attempted nonce was ever credited to the attacker.
    attempted = {r.attempted_nonce for r in recs}
    for rec in own:
        assert not any(rec.interval_start <= a < rec.interval_end for a in attempted)
    # a rejected attempt earns NO reward entry, only a penalty entry.
    inv_ids = {r.InvalidActionID for r in recs}
    assert not any(e.sign > 0 and e.source_event_id in inv_ids for e in run.incentive_ledger)
    assert s["invalid_message_penalty_total"] == pytest.approx(5.0 * len(recs))


def test_s5_18_progress_withholding_lowers_the_accepted_frontier_and_costs_re_evaluation():
    """S5-5: an undetected under-report lowers the ACCEPTED frontier the protocol acts on while
    the ACTUAL frontier is preserved separately.  The successor lease must then re-evaluate the
    difference, and that induced duplicate work is COUNTED, not hidden."""
    run = RunInitialise(cfg(adversarial=attacker(("PROGRESS_WITHHOLDER",),
                                                 audit_detection_probability=0.0,
                                                 progress_withholding_fraction=0.5)))
    from Models.PoCol.stage2 import RangeLease
    rc = type("RC", (), {"RoundID": "round-1", "TemplateID_committed": "tpl"})()
    prof_key = ("round-1", M0)
    run.behaviour_profiles[prof_key] = adv.MinerBehaviourProfile(
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

    adv.apply_progress_withholding(run, rc, prog, "L1", 5.0)
    assert prog.committed_frontier == 40                      # accepted frontier lowered ...
    assert run.adv_actual_frontier["S1"] == 80                # ... actual ground truth kept
    adv.note_reassignment_reeval(run, rc, "S1", prog.committed_frontier, 80)
    assert run.adversarial_stats["adversarial_duplicate_evaluation_count"] == 40
    assert run.adversarial_stats["progress_withholding_count"] == 1
    claim = run.progress_claims[0]
    assert claim.actual_frontier == 80 and claim.reported_frontier == 40 and claim.accepted


# ============================================================== S5-10 incentive ledger
def test_s5_19_work_reward_is_paid_per_unique_accepted_committed_evaluation():
    """S5-10: WORK_REWARD is derived ONLY from unique accepted committed evaluations in the
    executable evaluation ledger, deduplicated by range lineage and interval."""
    inc = IncentivePolicy(enabled=True, r_work=2.0)
    run = run_simulation(cfg(incentive=inc, horizon=30.0), run_id="s5-19")
    work = [e for e in run.incentive_ledger if e.component == "WORK_REWARD"]
    assert work
    unique = {(r.RangeSliceID if r.RangeSliceID is not None else r.AssignmentID,
               r.interval_start, r.interval_end) for r in run.evaluation_ledger}
    assert len(work) == len(unique)                           # one entry per unique interval
    total_nonces = sum(hi - lo for (_lin, lo, hi) in unique)
    assert run.adversarial_stats["work_reward_total"] == pytest.approx(2.0 * total_nonces)
    assert all(e.eligibility_reason == "unique_accepted_committed_evaluations" for e in work)


def test_s5_20_the_ledger_is_replay_idempotent_and_reconciles_exactly():
    """S5-10: a duplicate deduplication key writes nothing, so no reward or penalty can ever be
    counted twice; every per-component total reconciles against the immutable ledger."""
    inc = IncentivePolicy(enabled=True, r_work=1.0, r_avail=0.1, r_win=50.0, q_invalid=3.0)
    run = run_simulation(cfg(incentive=inc, difficulty=_TRIVIAL, horizon=30.0,
                             adversarial=attacker(("OUT_OF_RANGE_ACTOR",),
                                                  out_of_range_nonce_offset=5)),
                         run_id="s5-20")
    assert run.incentive_ledger
    keys = [e.deduplication_key for e in run.incentive_ledger]
    assert len(keys) == len(set(keys))                        # every key is unique
    assert adv.incentive_reconciliation_residual(run) == pytest.approx(0.0)
    # replaying the whole round's finalisation adds nothing.
    before = len(run.incentive_ledger)
    adv.finalise_incentives(run, run.current_round_context, run.run_end_time)
    assert len(run.incentive_ledger) == before
    assert adv.incentive_reconciliation_residual(run) == pytest.approx(0.0)


def test_s5_21_the_winner_reward_goes_only_to_the_solver_of_an_accepted_block():
    """S5-10: WINNER_REWARD is paid once per accepted block, to its solver alone — never to a
    miner whose solution was withheld and never accepted."""
    inc = IncentivePolicy(enabled=True, r_win=100.0)
    accepted = run_simulation(cfg(incentive=inc, difficulty=_TRIVIAL, horizon=30.0),
                              run_id="s5-21-a")
    wins = [e for e in accepted.incentive_ledger if e.component == "WINNER_REWARD"]
    assert wins and len(wins) == len(accepted.acceptance_times)
    assert all(e.eligibility_reason == "accepted_block_solver" for e in wins)
    assert all(e.amount == 100.0 and e.sign == 1 for e in wins)

    # every miner withholds => no block is accepted => no winner reward is paid at all.
    withheld = run_simulation(cfg(incentive=inc, difficulty=_TRIVIAL, horizon=30.0,
                                  adversarial=attacker(("SOLUTION_WITHHOLDER",), miners=_ALL,
                                                       solution_release_policy="NEVER_RELEASE")),
                             run_id="s5-21-w")
    assert not [e for e in withheld.incentive_ledger if e.component == "WINNER_REWARD"]
    assert withheld.adversarial_stats["winner_reward_total"] == 0.0


def test_s5_22_penalties_require_a_detected_or_rejected_action_and_spare_crash_faults():
    """S5-10: a penalty needs an actual detected false claim or a rejected invalid action.  An
    injected crash fault is NOT an intentional abandonment and is not penalised by default."""
    inc = IncentivePolicy(enabled=True, q_false=7.0, q_invalid=3.0, q_abandon=11.0)
    assert inc.penalise_crash_faults is False
    # detection ON => the false claim is caught and penalised.
    caught = run_simulation(cfg(incentive=inc,
                                adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                     audit_detection_probability=1.0)),
                            run_id="s5-22-c")
    pens = [e for e in caught.incentive_ledger if e.component == "FALSE_CLAIM_PENALTY"]
    assert pens and all(e.sign == -1 and e.amount == 7.0 for e in pens)
    assert all(e.eligibility_reason == "detected_false_claim" for e in pens)
    # detection OFF => nothing was detected, so no false-claim penalty may be charged.
    missed = run_simulation(cfg(incentive=inc,
                                adversarial=attacker(("FALSE_EXHAUSTION_CLAIMER",),
                                                     audit_detection_probability=0.0)),
                            run_id="s5-22-m")
    assert not [e for e in missed.incentive_ledger if e.component == "FALSE_CLAIM_PENALTY"]
    # a crash-faulted miner accrues no abandonment penalty.
    lease = RangeLeasePolicy(enabled=True, reassignment_wake_latency=1.0,
                             lease_duration=1e18, progress_timeout=1e18)
    crashed = run_simulation(cfg(incentive=inc, lease=lease, horizon=30.0,
                                 injected_lease_faults=((1, M0, 2.0, "crash"),)),
                             run_id="s5-22-x")
    assert not [e for e in crashed.incentive_ledger if e.component == "ABANDONMENT_PENALTY"]
    assert crashed.adversarial_stats["abandonment_penalty_total"] == 0.0


def test_s5_23_naive_and_deduplicated_accounting_are_computed_in_parallel():
    """S5-8: both reward views are reported.  Under the deduplicated policy, multiplying an
    entity's identities or assignment splits does NOT multiply its credited work — the naive
    view is reported ALONGSIDE it purely to expose the amplification exposure.

    This measures an accounting exposure.  It is NOT a claim of Sybil resistance."""
    inc = IncentivePolicy(enabled=True, r_work=1.0)
    assert inc.reward_deduplication_policy == "ENTITY_AND_LINEAGE_DEDUPLICATED"
    plain = run_simulation(cfg(incentive=inc,
                               adversarial=attacker(("FREE_RIDER",), klass="RATIONAL",
                                                    free_rider_work_fraction=1.0)),
                           run_id="s5-23-p")
    split = run_simulation(cfg(incentive=inc,
                               adversarial=attacker(("ASSIGNMENT_SPLITTER",), klass="RATIONAL",
                                                    assignment_split_count=4,
                                                    sybil_identity_count=3)),
                           run_id="s5-23-s")
    sp, ss = plain.adversarial_stats, split.adversarial_stats
    # the DEDUPLICATED total is unchanged by splitting / identity multiplication ...
    assert ss["deduplicated_entity_reward_total"] == pytest.approx(
        sp["deduplicated_entity_reward_total"])
    # ... while the NAIVE view exposes exactly the amplification the dedup policy removes.
    assert ss["naive_identity_reward_total"] > ss["deduplicated_entity_reward_total"]
    assert sp["naive_identity_reward_total"] == pytest.approx(
        sp["deduplicated_entity_reward_total"])
    assert split.adversarial_stats["assignment_split_count"] > 0


# ============================================================== S5-11 q_adv
def test_s5_24_q_adv_uses_actual_active_rates_and_is_na_when_no_capacity_is_active():
    """S5-11: q_adv(t) = H_adversarial / H_active over ACTUAL active hash rates.  When no miner
    is actively hashing the ratio is undefined, so it is reported as NA — an NA interval is
    never compared against the threshold and never enters the time-weighted mean."""
    # every miner adversarial => q_adv == 1 whenever anything is active.
    allbad = run_simulation(cfg(adversarial=attacker(("FREE_RIDER",), miners=_ALL,
                                                     klass="RATIONAL",
                                                     free_rider_work_fraction=1.0)),
                            run_id="s5-24-a")
    q = adv.q_adv_summary(allbad)
    assert q["maximum_q_adv"] == pytest.approx(1.0)
    assert q["time_weighted_q_adv"] == pytest.approx(1.0)
    assert q["q_adv_active_duration"] > 0 and q["q_adv_na_duration"] > 0

    # NA intervals are excluded from both the mean and the above-threshold duration.
    assert q["duration_above_q_adv_threshold"] <= q["q_adv_active_duration"]
    assert q["q_adv_na_duration"] > 0                        # pre-wake / post-exhaustion gaps

    # no declared adversarial entity => q_adv is 0 while active, never NA-by-accident.
    nobad = run_simulation(cfg(adversarial=AdversarialPolicy(
        enabled=True, entities=(("H", "HONEST", _ALL, None),))), run_id="s5-24-n")
    qn = adv.q_adv_summary(nobad)
    assert qn["maximum_q_adv"] == pytest.approx(0.0)
    assert qn["duration_above_q_adv_threshold"] == pytest.approx(0.0)

    # a run that never observes an active interval reports NA (None), not a fabricated 0.0.
    fresh = RunInitialise(cfg(adversarial=attacker(("FREE_RIDER",))))
    assert adv.q_adv_summary(fresh)["time_weighted_q_adv"] is None
    assert adv.q_adv_summary(fresh)["maximum_q_adv"] is None


# ============================================================== S5-12 round termination
def test_s5_25_stage5_actions_are_round_terminal_and_the_registry_is_replay_idempotent():
    """S5-12: at round closure every withheld solution, delayed wake and claim reaches a
    terminal status and any queued release event is cancelled, so no adversarial action can
    affect a later round.  Re-registering the same immutable action id has no second effect."""
    run = run_simulation(cfg(difficulty=_TRIVIAL, horizon=30.0,
                             adversarial=attacker(("SOLUTION_WITHHOLDER", "DELAYED_WAKE"),
                                                  miners=_ALL,
                                                  solution_release_policy="DELAYED_RELEASE",
                                                  solution_withholding_delay=2.0,
                                                  delayed_wake_extra_latency=1.0)),
                         run_id="s5-25")
    assert run.round_seq > 1                                  # several rounds really ran
    live_rounds = {run.current_round_context.RoundID}
    for w in run.withheld_solutions.values():
        if w.RoundID not in live_rounds:
            assert w.status != "WITHHELD", w
    for a in run.delayed_wake_actions.values():
        if a.RoundID not in live_rounds:
            assert a.status in ("COMPLETED", "CANCELLED_AT_CLOSE"), a
    for w in run.withheld_solutions.values():
        if w.release_event_ref is not None and w.status != "RELEASED_ACCEPTED":
            rec = run.event_queue.queued_event_registry.get(w.release_event_ref)
            assert rec is None or rec.queue_status != "QUEUED"

    # the action registry is replay-idempotent: the same id returns the same record.
    calls = []
    first = adv.register_action(run, ("A", 1), lambda: calls.append(1) or "rec")
    again = adv.register_action(run, ("A", 1), lambda: calls.append(1) or "other")
    assert first == "rec" and again == "rec" and len(calls) == 1


# ============================================================== S5-13 / S5-26 harness + scope
def test_s5_26_no_stage5_parameter_changes_the_fixed_target_and_the_schema_is_preserved():
    """S5-26: the fixed SHA-256 target and difficulty are untouched by every Stage-5 parameter,
    the matched-pair harness refuses any profile that would change them, and the stage5.1 schema
    RETAINS every accepted Stage-4C key while carrying an explicit scope statement."""
    base = {"num_miners": 4, "nonce_domain_size": 200, "difficulty": 1, "horizon_T": 30.0,
            "batch_size": 25, "reserve_fraction": 0.0}
    honest_cfg = stage2config_from_blocksim(base)
    attacked_cfg = stage2config_from_blocksim({
        **base, "adversarial_enabled": True, "solution_release_policy": "NEVER_RELEASE",
        "audit_detection_probability": 0.0, "free_rider_work_fraction": 0.25,
        "delayed_wake_extra_latency": 3.0, "sybil_identity_count": 8,
        "incentive_enabled": True, "r_work": 1.0, "q_invalid": 2.0,
        "adversarial_entities": [("E1", "BYZANTINE", _ALL, None)],
        "miner_behaviours": [(0, m, ("SOLUTION_WITHHOLDER",)) for m in _ALL]})
    assert attacked_cfg.difficulty == honest_cfg.difficulty
    assert attacked_cfg.nonce_domain_size == honest_cfg.nonce_domain_size
    assert (target_for_difficulty(attacked_cfg.difficulty)
            == target_for_difficulty(honest_cfg.difficulty))
    assert attacked_cfg.adversarial.enabled and attacked_cfg.incentive.enabled

    # the harness rejects any attack profile that would move the work target or the domain.
    for forbidden in ({"difficulty": 2}, {"nonce_domain_size": 999}, {"template_seed": 1}):
        with pytest.raises(ValueError):
            run_matched_adversarial_pair(base, forbidden)

    pair = run_matched_adversarial_pair(base, {
        "adversarial_enabled": True, "solution_release_policy": "NEVER_RELEASE",
        "adversarial_entities": [("E1", "BYZANTINE", _ALL, None)],
        "miner_behaviours": [(0, m, ("SOLUTION_WITHHOLDER",)) for m in _ALL]},
        run_id="s5-26")
    assert pair["identical_target_and_difficulty"] is True
    assert pair["baseline"]["rounds_accepted"] > 0            # the honest arm produces blocks
    assert pair["attacked"]["rounds_accepted"] == 0           # the attacked arm produces none
    assert pair["delta"]["rounds_accepted"] < 0
    assert pair["attacked"]["solution_withholding_count"] > 0
    assert "NOT evidence of incentive" in pair["interpretation_scope"]

    # the declared schema is stage5.1 and every Stage-4C key survives.
    res = pair["baseline"]
    assert res["schema_version"] == RESULT_SCHEMA_VERSION == "stage5.1"
    for retained in ("algorithm", "mechanism", "success_model", "energy_kwh",
                     "continuous_all_active_control_kwh", "residency_reconciles",
                     "evaluation_ledger_entries", "security_floor_enabled",
                     "range_lease_enabled", "per_miner_energy_kwh"):
        assert retained in res, retained
    assert res["algorithm"] == "PoCol"
    assert res["mechanism"] == "idle policy within PoCol"
    assert res["adversarial_model_enabled"] is False          # baseline arm stays honest
    scope = res["stage5_claim_scope"]
    for forbidden_claim in ("incentive compatibility", "fairness", "Sybil resistance",
                            "selfish-mining resistance", "coalition resistance",
                            "common-prefix", "chain-quality", "PoW-equivalent"):
        assert forbidden_claim in scope, forbidden_claim
    assert "idle policy within PoCol" in scope
