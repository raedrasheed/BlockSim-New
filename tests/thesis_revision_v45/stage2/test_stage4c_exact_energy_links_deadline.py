"""Stage-4C exact-interval-energy / Path-B reverse-link / deadline-identity / state-purity tests
S4C-01 .. S4C-09.

These lock the final Stage-4 corrections demanded by the acceptance review:

* S4C-1/2 every energy component is a TRUE request-interval residency-ledger delta (never the
          miner's whole-run cumulative residency), with five per-component residuals, an
          interval-overlap audit and an aggregate-vs-run-residency bound;
* S4C-3   both Path-B seat-failure points clear every reserve field / reverse link / wake handle;
* S4C-4   the Path-B activation identity (WakeHandleID / OriginalRangeSliceID /
          RangeReassignmentRequestID) is stored explicitly and stays auditable after handle removal;
* S4C-5   BOTH deadline payloads are verified TOTALLY + safely (missing/tampered -> structured
          no-effect, no KeyError);
* S4C-6   exact replay + unknown-trigger rejection are STATE-PURE.

The whole lease layer stays disabled by default, so all 115 retained tests are unchanged.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, RangeLeasePolicy, RunInitialise, ProcessEventTime,
                                  SeatNextRoundBootstrap, RunEventLoopToHorizon, run_simulation,
                                  RoundContext, MinerSearchState, EventRef, PRIMARY_ASSIGNMENT,
                                  REASSIGNED_PRIMARY_WORK, REASSIGNED_RESERVE_WORK,
                                  RangeReassignmentRequest, RangeLease)
from Models.PoCol.stage2.adapter import reassignment_energy_report, _range_lease_results

_ZERO = 1 << 300

_ENERGY_KEYS = ("predecessor_active_energy_before_revocation_j",
                "predecessor_idle_or_offline_energy_after_revocation_j",
                "reassignee_standby_energy_before_wake_j", "reassignment_wake_energy_j",
                "reassignment_active_hashing_energy_j")
_RESIDUAL_KEYS = ("residual_predecessor_active_j", "residual_predecessor_idle_or_offline_j",
                  "residual_reassignee_standby_j", "residual_reassignment_wake_j",
                  "residual_reassignment_active_hashing_j")


def lease_cfg(*, num_miners=4, reserve_fraction=0.0, D=400, difficulty=_ZERO, horizon=120.0,
              wake=1.0, lease_duration=1.0e18, progress_timeout=1.0e18, faults=(),
              cancellations=(), no_eligible="CONTINUE_WITH_UNASSIGNED_RANGE"):
    pol = RangeLeasePolicy(enabled=True, reassignment_wake_latency=wake,
                           lease_duration=lease_duration, progress_timeout=progress_timeout,
                           no_eligible_miner_policy=no_eligible)
    return Stage2Config(num_miners=num_miners, reserve_fraction=reserve_fraction,
                        nonce_domain_size=D, difficulty=difficulty, batch_size=25,
                        horizon_T=horizon, range_lease=pol, injected_lease_faults=faults,
                        injected_lease_cancellations=cancellations)


def _lease(run, lid, mid, kind, **kw):
    from Models.PoCol.stage2 import RangeLease as _RL
    run.range_leases[lid] = _RL(
        LeaseID=lid, RoundID="round-1", TemplateID="tpl", RangeSliceID="PS-" + lid,
        lease_generation=1, AssignmentID="A", assignment_version=1, MinerID=mid,
        assignment_kind=kind, lease_start_nonce=0, lease_end_nonce=100, committed_cursor=0,
        lease_start_time=0.0, lease_expiry_time=1e18, lease_status="REVOKED", **kw)
    return run.range_leases[lid]


# ---------------------------------------------------------------- S4C-01
def test_s4c_01_predecessor_active_energy_is_only_the_current_lease_delta():
    """A predecessor that already did ACTIVE work in earlier rounds is charged ONLY the active-energy
    delta of its CURRENT (revoked) lease, never its whole-run cumulative ACTIVE residency."""
    run = RunInitialise(lease_cfg())
    Ph = run.config.per_miner_power("ACTIVE_HASHING")
    run.create_miner("P", 0.0, state="OFFLINE")
    run.miners["P"].duration["ACTIVE_HASHING"] = 9.0        # whole-run cumulative ACTIVE residency
    # the CURRENT primary lease started at cumulative ACTIVE 6.0 (its earlier-round work), and the
    # predecessor is revoked at cumulative ACTIVE 9.0.
    _lease(run, "Lp", "P", PRIMARY_ASSIGNMENT, active_residency_at_lease_start=6.0)
    run.reassignment_requests["RR"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR", DecisionID=("d",), RoundID="round-1", TemplateID="tpl",
        RangeSliceID="PS-Lp", predecessor_lease_id="Lp", predecessor_committed_frontier=0,
        new_MinerID="Q", new_lease_generation=2, predecessor_MinerID="P", status="COMPLETED",
        revocation_time=6.0, predecessor_active_residency_at_revocation=9.0)
    rep = reassignment_energy_report(run, run.config)
    row = next(r for r in rep["per_request"] if r["RangeReassignmentRequestID"] == "RR")
    # charged EXACTLY the current-lease active delta [6, 9] = 3.0 ...
    assert row["predecessor_active_energy_before_revocation_j"] == pytest.approx(Ph * 3.0)
    # ... NOT the whole-run cumulative 9.0 (that would be a 3x over-charge).
    assert row["predecessor_active_energy_before_revocation_j"] < Ph * 9.0 - 1e-9
    assert rep["max_request_energy_residual_j"] < 1e-6
    assert rep["overlapping_charged_interval_count"] == 0


# ---------------------------------------------------------------- S4C-02
def test_s4c_02_no_later_round_idle_charged_to_the_earlier_request():
    """A predecessor that keeps running (and idling) in LATER rounds after its request ends is charged
    idle energy ONLY over [revocation, request_terminal] — no later-round low/offline residency
    leaks in (the FINAL run residency is NOT used when the request terminal is earlier)."""
    run = RunInitialise(lease_cfg())
    Plow = run.config.per_miner_power("LOW_POWER_LISTEN")
    run.create_miner("P", 0.0, state="LOW_POWER_LISTEN")
    run.miners["P"].duration["LOW_POWER_LISTEN"] = 10.0     # includes much later-round idle
    _lease(run, "Lp", "P", PRIMARY_ASSIGNMENT, active_residency_at_lease_start=0.0)
    run.reassignment_requests["RR"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR", DecisionID=("d",), RoundID="round-1", TemplateID="tpl",
        RangeSliceID="PS-Lp", predecessor_lease_id="Lp", predecessor_committed_frontier=0,
        new_MinerID="Q", new_lease_generation=2, predecessor_MinerID="P", status="COMPLETED",
        revocation_time=1.0, predecessor_active_residency_at_revocation=0.0,
        predecessor_low_residency_at_revocation=1.0,
        predecessor_low_residency_at_request_terminal=3.0,
        predecessor_offline_residency_at_revocation=0.0,
        predecessor_offline_residency_at_request_terminal=0.0, terminal_time=3.0)
    rep = reassignment_energy_report(run, run.config)
    row = next(r for r in rep["per_request"] if r["RangeReassignmentRequestID"] == "RR")
    # charged idle ONLY over [1, 3] = Plow x 2 ...
    assert row["predecessor_idle_or_offline_energy_after_revocation_j"] == pytest.approx(Plow * 2.0)
    # ... even though the miner's FINAL low residency (10.0) is far larger (later-round idle).
    assert run.miners["P"].duration["LOW_POWER_LISTEN"] > 3.0
    assert row["predecessor_idle_or_offline_energy_after_revocation_j"] < Plow * 10.0 - 1e-9
    assert rep["max_request_energy_residual_j"] < 1e-6


# ---------------------------------------------------------------- S4C-03
def test_s4c_03_reassignee_standby_is_only_seat_to_wake_interval():
    """A reserve reassignee with prior RESERVE history is charged standby energy ONLY over
    [seat, wake_start] — not its whole prior RESERVE residency."""
    run = run_simulation(lease_cfg(reserve_fraction=0.5, horizon=120.0,
                                   faults=((1, "M000", 1.3, "MINER_FAILED"),)))
    Pres = run.config.per_miner_power("RESERVE")
    rows = {r["RangeReassignmentRequestID"]: r for r in
            reassignment_energy_report(run, run.config)["per_request"]}
    checked = 0
    for req in run.reassignment_requests.values():
        if not req.needs_stage3_wake or req.reassignee_reserve_residency_at_seat is None:
            continue
        row = rows[req.RangeReassignmentRequestID]
        seat = req.reassignee_reserve_residency_at_seat
        ws = req.reassignee_reserve_residency_at_wake_start
        # the reserve reassignee sat in RESERVE from round start until seated: a real prior history.
        assert seat > 0.0
        # standby energy is the [seat, wake_start] delta only (reserve component here).
        assert row["reassignee_standby_energy_before_wake_j"] == \
            pytest.approx(Pres * max(0.0, ws - seat), abs=1e-9)
        # and that delta is far smaller than charging the whole prior RESERVE residency would be.
        assert Pres * max(0.0, ws - seat) < Pres * seat + 1e-9
        checked += 1
    assert checked >= 1


# ---------------------------------------------------------------- S4C-04
def test_s4c_04_all_statuses_carry_all_five_components_and_residuals():
    """COMPLETED, FAILED and CANCELLED requests each carry all five energy components and all five
    per-component residuals in the report."""
    demo = RunInitialise(lease_cfg())
    Pw = demo.config.per_miner_power("WAKING")
    common = dict(DecisionID=("d",), RoundID="round-1", TemplateID="tpl", RangeSliceID="PS-x",
                  predecessor_lease_id="L0", predecessor_committed_frontier=0,
                  new_lease_generation=2, predecessor_MinerID="M0")
    demo.reassignment_requests["RR-C"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-C", new_MinerID="Ma", status="COMPLETED",
        seated_at=1.0, started_at=1.0, completed_at=2.0, terminal_time=5.0,
        wake_residency_at_start=0.0, wake_residency_at_end=1.0,
        reassigned_search_start_time=2.0, reassigned_search_end_time=5.0,
        active_residency_at_search_start=0.0, active_residency_at_search_end=3.0, **common)
    demo.reassignment_requests["RR-F"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-F", new_MinerID="Mb", status="FAILED",
        seated_at=1.0, started_at=1.0, terminal_time=2.0,
        wake_residency_at_start=0.0, wake_residency_at_end=1.0, **common)
    demo.reassignment_requests["RR-X"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-X", new_MinerID="Mc", status="CANCELLED",
        seated_at=1.0, terminal_time=3.0, **common)
    rep = reassignment_energy_report(demo, demo.config)
    by_id = {r["RangeReassignmentRequestID"]: r for r in rep["per_request"]}
    for rid in ("RR-C", "RR-F", "RR-X"):
        row = by_id[rid]
        for k in _ENERGY_KEYS + _RESIDUAL_KEYS:
            assert k in row, (rid, k)
    assert rep["request_count_by_status"]["COMPLETED"] >= 1
    assert rep["request_count_by_status"]["FAILED"] >= 1
    assert rep["request_count_by_status"]["CANCELLED"] >= 1
    # a FAILED wake with a real wake interval is attributed (not omitted).
    assert by_id["RR-F"]["reassignment_wake_energy_j"] == pytest.approx(Pw * 1.0)


# ---------------------------------------------------------------- S4C-05
def test_s4c_05_same_miner_two_requests_no_double_charge():
    """Two requests involving the SAME miner never double-charge an overlapping residency interval:
    a reassignee's ACTIVE work (charged once as its provisioning request's reassigned-active) is NOT
    re-charged as the predecessor-active of a downstream revocation."""
    demo = RunInitialise(lease_cfg())
    Ph = demo.config.per_miner_power("ACTIVE_HASHING")
    # a REASSIGNED lease for miner M with its active-at-lease-start snapshot at cumulative 0.
    demo.range_leases["L-reassigned"] = RangeLease(
        LeaseID="L-reassigned", RoundID="round-1", TemplateID="tpl", RangeSliceID="PS-y",
        lease_generation=2, AssignmentID="AR", assignment_version=1, MinerID="M",
        assignment_kind=REASSIGNED_PRIMARY_WORK, lease_start_nonce=0, lease_end_nonce=100,
        committed_cursor=0, lease_start_time=1.0, lease_expiry_time=1e18, lease_status="REVOKED",
        active_residency_at_lease_start=0.0)
    common = dict(DecisionID=("d",), RoundID="round-1", TemplateID="tpl", RangeSliceID="PS-y",
                  predecessor_committed_frontier=0, new_lease_generation=3)
    # request A provisioned M's reassigned ACTIVE work over cumulative [0, 3].
    demo.reassignment_requests["RR-A"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-A", new_MinerID="M", status="COMPLETED",
        predecessor_lease_id="L0", predecessor_MinerID="P0", seated_at=1.0, started_at=1.0,
        completed_at=2.0, terminal_time=5.0, reassigned_search_start_time=2.0,
        reassigned_search_end_time=5.0, active_residency_at_search_start=0.0,
        active_residency_at_search_end=3.0, **common)
    # request B revokes M's reassigned lease: its predecessor-active interval is the SAME [0, 3].
    demo.reassignment_requests["RR-B"] = RangeReassignmentRequest(
        RangeReassignmentRequestID="RR-B", new_MinerID="Q", status="COMPLETED",
        predecessor_lease_id="L-reassigned", predecessor_MinerID="M", seated_at=5.0,
        revocation_time=5.0, predecessor_active_residency_at_revocation=3.0,
        predecessor_low_residency_at_revocation=0.0, predecessor_low_residency_at_request_terminal=0.0,
        predecessor_offline_residency_at_revocation=0.0,
        predecessor_offline_residency_at_request_terminal=0.0, terminal_time=6.0, **common)
    rep = reassignment_energy_report(demo, demo.config)
    by_id = {r["RangeReassignmentRequestID"]: r for r in rep["per_request"]}
    # A owns the ACTIVE work; B's chained predecessor-active is 0 -> the interval is charged ONCE.
    assert by_id["RR-A"]["reassignment_active_hashing_energy_j"] == pytest.approx(Ph * 3.0)
    assert by_id["RR-B"]["predecessor_active_energy_before_revocation_j"] == 0.0
    assert rep["overlapping_charged_interval_count"] == 0
    assert rep["aggregate_exceeds_run_residency_count"] == 0
    # and it holds on a real multi-fault run too.
    run = run_simulation(lease_cfg(reserve_fraction=0.25, num_miners=8, D=800, horizon=200.0,
                                   faults=((1, "M000", 1.6, "MINER_FAILED"),
                                           (2, "M001", 1.6, "MINER_FAILED"))))
    real = reassignment_energy_report(run, run.config)
    assert real["overlapping_charged_interval_count"] == 0
    assert real["aggregate_exceeds_run_residency_count"] == 0
    assert real["max_request_energy_residual_j"] < 1e-6


# ---------------------------------------------------------------- S4C-06
def test_s4c_06_pathb_complete_seat_failure_clears_every_reverse_link():
    """A Path-B ReserveActivationCompleteEvent seat failure clears every reserve field, reverse link
    and WakeHandle reference, and gives the synthetic activation decision a terminal outcome."""
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    run = RunInitialise(cfg)
    run.force_activation_complete_seat_failure = True
    RunEventLoopToHorizon(run)
    assert run.lease_stats["wake_complete_seat_failures"] >= 1
    # no wake handle, and no nonce-domain / suffix registry references a removed WakeHandleID.
    assert not run.reassignment_wake_handles
    assert not any(str(k).startswith("WH-") for k in run.reassign_by_suffix_slice)
    # every reserve record that lost its activation has all three reverse links cleared.
    for rr in run.reserve_records.values():
        if rr.reserve_status == "CANCELLED":
            assert rr.assigned_reserve_slice_id is None
            assert rr.activation_request_id is None
            assert rr.activation_event_ref is None
    # no synthetic ACTIVATION_SEATED decision is left without a recorded failed terminal outcome.
    for dec in run.activation_decisions:
        if dec.policy_result == "ACTIVATION_SEATED" and str(dec.DecisionID[1]) == "RDEC3":
            reqs = [r for r in run.activation_requests.values() if r.DecisionID == dec.DecisionID]
            if reqs and all(r.status == "FAILED" for r in reqs):
                assert dec.disposition is not None
    assert not any(m.state == "WAKING" for m in run.miners.values())


# ---------------------------------------------------------------- S4C-07
def test_s4c_07_pathb_identity_auditable_after_handle_removal():
    """A Path-B activation request retains explicit WakeHandleID / OriginalRangeSliceID /
    RangeReassignmentRequestID even AFTER its wake handle has been removed by the failure cleanup."""
    cfg = lease_cfg(reserve_fraction=0.5, faults=((1, "M000", 1.3, "MINER_FAILED"),))
    run = RunInitialise(cfg)
    run.force_activation_complete_seat_failure = True
    RunEventLoopToHorizon(run)
    failed_wake_acts = [a for a in run.activation_requests.values()
                        if a.activation_scope == "REASSIGNMENT_WAKE_ONLY" and a.status == "FAILED"]
    assert failed_wake_acts
    for act in failed_wake_acts:
        assert act.WakeHandleID is not None
        assert act.OriginalRangeSliceID is not None
        assert act.RangeReassignmentRequestID is not None
        assert str(act.OriginalRangeSliceID).startswith("PS-")     # authoritative RangeProgress
        # the wake handle itself is gone, yet its identity is still auditable on the request.
        assert act.WakeHandleID not in run.reassignment_wake_handles


# ---------------------------------------------------------------- S4C-08
def _round_with_armed_deadlines():
    cfg = lease_cfg(lease_duration=2.0, progress_timeout=5.0, wake=1.0, horizon=40.0)
    run = RunInitialise(cfg)
    SeatNextRoundBootstrap(run)
    ProcessEventTime(run, cfg.run_start_time)
    rc = run.current_round_context
    mid = sorted(run.round_participants[rc.RoundID])[0]
    prog = run.range_progress[run.slice_of_miner[(rc.RoundID, mid)]]
    lease = run.range_leases[prog.current_lease_id]
    return run, rc, lease, prog


def test_s4c_08_missing_or_tampered_deadline_field_is_structured_no_effect():
    """Removing OR tampering ANY declared deadline-payload field makes the dispatch a structured
    no-effect (never a KeyError, never a state mutation); the untampered event is the control."""
    from Models.PoCol.stage2.simulator import (_handle_range_lease_expiry,
                                               _handle_range_progress_timeout)
    for is_timeout, handler in ((False, _handle_range_lease_expiry),
                                (True, _handle_range_progress_timeout)):
        run, rc, lease, prog = _round_with_armed_deadlines()
        eq = run.event_queue
        ref = prog.timeout_event_ref if is_timeout else lease.expiry_event_ref
        good = dict(eq.queued_event_registry[ref].immutable_payload)
        deadline_t = prog.last_progress_time + 5.0 if is_timeout else lease.lease_expiry_time

        def dispatch(payload, event_ref=ref):
            eq.current_event_time = deadline_t
            eq.current_event_ref = event_ref
            return handler(run, payload, {})

        # every declared field: (a) removed and (b) tampered -> structured no-effect, no exception.
        for field in list(good.keys()):
            removed = {k: v for k, v in good.items() if k != field}
            out = dispatch(removed)
            assert out.kind == "range_deadline_no_effect"
            assert out.reason == "missing_or_tampered_identity"
            tampered = dict(good)
            tampered[field] = ("TAMPER", tampered[field])
            assert dispatch(tampered).kind == "range_deadline_no_effect"
            assert lease.lease_status == "ACTIVE" and prog.current_lease_id == lease.LeaseID
        # a current EventRef that is not the armed deadline ref -> no effect.
        bogus = EventRef("ORDINARY_EVENT", "RangeLeaseExpiryEvent", deadline_t, 0,
                         "RANGE_LEASE_EXPIRY", 999999)
        assert dispatch(good, event_ref=bogus).kind == "range_deadline_no_effect"
        assert lease.lease_status == "ACTIVE"
        # control: the untampered event with the armed ref DOES take effect.
        assert dispatch(good).kind != "range_deadline_no_effect"


# ---------------------------------------------------------------- S4C-09
def _protocol_snapshot(run):
    """A byte-comparable snapshot of PROTOCOL state (excludes the diagnostic namespace)."""
    def statuses(d, attr):
        return {k: getattr(v, attr) for k, v in d.items()}
    eq = run.event_queue
    return {
        "lease_stats": dict(run.lease_stats),
        "lease_status": statuses(run.range_leases, "lease_status"),
        "reassign_status": statuses(run.reassignment_requests, "status"),
        "n_decisions": len(run.reassignment_decisions),
        "n_observations": len(run.lease_observations),
        "n_leases": len(run.range_leases),
        "n_requests": len(run.reassignment_requests),
        "lease_observation_seq": run.lease_observation_seq,
        "observation_seq": run.observation_seq,
        "miner_states": {m: run.miners[m].state for m in run.miners},
        "lease_obs_by_key": len(run.lease_observation_by_key),
        "reassign_by_predecessor": dict(run.reassignment_by_predecessor),
        "queue_len": len(eq.queued_event_registry),
        "queue_statuses": sorted(r.queue_status for r in eq.queued_event_registry.values()),
    }


def test_s4c_09_replay_and_rejection_are_state_pure():
    """Exact reassignment replay AND unknown-trigger rejection leave the entire protocol-state
    snapshot byte-equivalent; only the diagnostic (non-protocol) counters move."""
    from Models.PoCol.stage2.simulator import (RevokeRangeLeaseTransaction,
                                               SeatRangeReassignmentTransaction,
                                               _eligible_reassignment_candidates, EvaluateRangeLease)
    from Models.PoCol.stage2 import select_reassignment_candidate
    # build a round, revoke M000 and seat a reassignment so a NATURAL replay is possible.
    run = RunInitialise(lease_cfg())
    from Models.PoCol.stage2.simulator import _create_range_progress_and_lease
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    rc.state_version = 4
    run.current_round_context = rc
    rc.search_states = {}
    run.round_ranges["round-1"] = {"M000": (0, 100), "M001": (100, 200)}
    run.create_miner("M000", 0.0, state="ACTIVE_HASHING")
    st0 = MinerSearchState("M000", "A0", 1, 100.0, 0, 100, 21.5, 2.15)
    st0.cursor = 25
    rc.search_states["M000"] = st0
    run.search_assignment_kind[("round-1", "M000")] = PRIMARY_ASSIGNMENT
    _create_range_progress_and_lease(run, rc, "M000", "A0", 1, "PS-round-1-M000", 0, 100,
                                     PRIMARY_ASSIGNMENT, 0.0)
    run.range_progress["PS-round-1-M000"].committed_frontier = 25
    run.create_miner("M001", 0.0, state="LOW_POWER_LISTEN")
    st1 = MinerSearchState("M001", "A1", 1, 200.0, 100, 200, 21.5, 2.15)
    st1.cursor = 200
    st1.completed = True
    st1.completion_kind = "EXHAUSTED"
    rc.search_states["M001"] = st1
    run.search_assignment_kind[("round-1", "M001")] = PRIMARY_ASSIGNMENT
    eq = run.event_queue
    eq.current_event_time = 2.5
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "MinerFailureEvent", 2.5, 0,
                                    "MINER_FAILURE", 1)
    prog = run.range_progress["PS-round-1-M000"]
    lease = run.range_leases[prog.current_lease_id]
    run.miners["M000"].state = "OFFLINE"
    RevokeRangeLeaseTransaction(run, rc, lease, "MINER_FAILED")
    cands = _eligible_reassignment_candidates(run, rc, "PS-round-1-M000", "M000", 25, 2.5)
    chosen = select_reassignment_candidate(cands)
    SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")

    before = _protocol_snapshot(run)
    diag_before = dict(run.lease_diagnostics)
    # (a) exact NATURAL replay of the same terminal predecessor lease.
    again = SeatRangeReassignmentTransaction(run, rc, prog, lease, chosen, 2.5, "MINER_FAILED")
    assert again.kind == "range_reassignment_already_exists"
    # (b) unknown-trigger rejection on a still-ACTIVE lease (the successor).
    succ = run.range_leases.get(
        list(run.reassignment_requests.values())[0].new_lease_id)
    target_lease = succ if succ is not None else lease
    out = EvaluateRangeLease(run, rc, target_lease.LeaseID, 3.0, "TOTALLY_BOGUS_TRIGGER")
    assert out.kind == "range_lease_observation_rejected_unknown_trigger"

    after = _protocol_snapshot(run)
    assert after == before                                  # protocol state byte-equivalent
    assert run.lease_diagnostics != diag_before             # only diagnostics moved
    assert run.lease_diagnostics["reassignment_replay_count"] >= 1
    assert run.lease_diagnostics["unknown_trigger_rejections"] >= 1
