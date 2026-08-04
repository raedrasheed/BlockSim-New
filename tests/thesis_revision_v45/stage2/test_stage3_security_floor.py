"""Stage-3 security-floor + reserve-activation tests S3-01 .. S3-18.

These exercise the OPERATIONAL active-capacity floor and the reserve-activation policy on
top of the accepted Stage-2B search core.  The floor is an operational capacity floor only
(no consensus-security-equivalence claim); reserve activation is distinct from range
reassignment and may increase energy.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (Stage2Config, SecurityFloorPolicy, run_simulation,
                                  RunInitialise, RoundContext, MinerSearchState, EventRef,
                                  compute_h_effective, partition_primary_and_reserve,
                                  SeatReserveActivation, SeatReserveActivationTransaction,
                                  ReserveMinerRecord, RangeSlice, SecurityFloorObservation,
                                  target_for_difficulty, EvaluateSecurityFloor,
                                  TERMINAL_RESERVE_STATUSES, TERMINAL_REQUEST_STATUSES,
                                  FULL_DOMAIN_EXHAUSTED_NO_BLOCK,
                                  ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN,
                                  ACTIVATED_RESERVE_ASSIGNMENT, PRIMARY_ASSIGNMENT)
from Models.PoCol.stage2 import run_pocol_stage2
from Models.PoCol.stage2.security import select_reserves_to_cover
from Models.PoCol.stage2.simulator import _handle_reserve_activation_start

_ZERO_SOLUTION = 1 << 300   # target_for_difficulty(_) == 0 -> deterministically no solution


def floor_cfg(min_rate, *, num_miners=4, reserve_fraction=0.5, D=400,
              difficulty=_ZERO_SOLUTION, horizon=300.0, act_wake=1.0,
              unattainable="CONTINUE_DEGRADED", min_count=None, max_act=1_000_000):
    pol = SecurityFloorPolicy(enabled=True, minimum_active_hash_rate=min_rate,
                              minimum_active_miner_count=min_count,
                              activation_wake_latency=act_wake,
                              maximum_activations_per_round=max_act)
    return Stage2Config(num_miners=num_miners, reserve_fraction=reserve_fraction,
                        nonce_domain_size=D, difficulty=difficulty, batch_size=25,
                        horizon_T=horizon, security_floor=pol,
                        floor_unattainable_policy=unattainable)


# ---------------------------------------------------------------- S3-01
def test_s3_01_floor_satisfied_no_activation():
    """A satisfied floor creates no reserve activation decision or event."""
    run = run_simulation(floor_cfg(0.0))                   # min 0 -> never breached
    s = run.security_stats
    assert s["observation_count"] > 0                      # the floor IS being observed
    assert s["breach_observation_count"] == 0
    assert s["distinct_breach_count"] == 0
    assert s["activations_seated"] == 0
    assert not any(d.policy_result == "ACTIVATION_SEATED" for d in run.activation_decisions)


# ---------------------------------------------------------------- S3-02
def test_s3_02_breach_after_exhaust_seats_activation():
    """H_effective dropping below the floor after a primary exhausts seats an activation."""
    run = run_simulation(floor_cfg(250.0))
    assert any(o.breached for o in run.security_observations)
    assert run.security_stats["activations_seated"] > 0
    assert any(d.policy_result == "ACTIVATION_SEATED" for d in run.activation_decisions)


# ---------------------------------------------------------------- S3-03
def test_s3_03_waking_reserve_not_counted():
    """A reserve in WAKING (no live search state) contributes nothing to H_effective."""
    run = RunInitialise(floor_cfg(250.0))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    run.create_miner("P", 0.0, state="ACTIVE_HASHING")
    st = MinerSearchState("P", "A", 1, 100.0, 0, 50, 21.5, 2.15)
    st.active_start = 0.0
    rc.search_states["P"] = st
    rc.assignments["A"] = {"MinerID": "P", "AssignmentID": "A", "assignment_version": 1,
                           "range": (0, 50), "RoundID": "round-1",
                           "TemplateID": "tpl-round-1", "coverage_state": "OPEN"}
    run.create_miner("R", 0.0, state="WAKING")             # reserve mid-wake, no search state
    h, cnt, ids = compute_h_effective(run, rc)
    assert h == 100.0 and cnt == 1 and "R" not in ids      # WAKING reserve excluded


# ---------------------------------------------------------------- S3-04
def test_s3_04_completed_reserve_active_counts_and_hashes():
    """After completion a reserve becomes ACTIVE, counts toward H_effective and hashes."""
    run = run_simulation(floor_cfg(250.0))
    assert run.security_stats["activations_completed"] > 0
    # it received hash work (activated-reserve ledger entries exist).
    assert run.security_stats["activated_reserve_evaluation_count"] > 0
    assert any(rec.assignment_kind == ACTIVATED_RESERVE_ASSIGNMENT
               for rec in run.evaluation_ledger)
    # at least one observation taken AFTER an activation completed saw active capacity.
    assert any(o.observation_reason == "reserve_activation_completed"
               and o.effective_active_hash_rate > 0 for o in run.security_observations)


# ---------------------------------------------------------------- S3-05
def test_s3_05_minimal_sufficient_subset():
    """Reserve selection is minimal-sufficient (pure) and seats fewer than all when enough."""
    # pure selector: 4 x 100, need 250 -> exactly 3 (sum 300), never 4.
    class R:
        def __init__(self, r): self.hash_rate = r
    chosen = select_reserves_to_cover([R(100), R(100), R(100), R(100)], 250.0, 10)
    assert len(chosen) == 3
    chosen1 = select_reserves_to_cover([R(300), R(400)], 150.0, 10)
    assert len(chosen1) == 1                                # one 300 covers 150
    # integration: a seated decision activated fewer than all eligible reserves.
    run = run_simulation(floor_cfg(250.0))
    seated = [d for d in run.activation_decisions if d.policy_result == "ACTIVATION_SEATED"]
    assert seated and any(len(d.selected_miners) == 1 for d in seated)


# ---------------------------------------------------------------- S3-06
def test_s3_06_two_runs_select_same_reserves_and_slices():
    """Two equivalent runs make identical reserve selections and slice claims."""
    a = run_simulation(floor_cfg(250.0))
    b = run_simulation(floor_cfg(250.0))
    seq_a = [(d.selected_miners, d.selected_slices, d.policy_result) for d in a.activation_decisions]
    seq_b = [(d.selected_miners, d.selected_slices, d.policy_result) for d in b.activation_decisions]
    assert seq_a == seq_b and len(seq_a) > 0


# ---------------------------------------------------------------- S3-07
def test_s3_07_primary_and_reserve_slices_disjoint_cover_domain():
    """Primary ranges and reserve-domain slices are pairwise disjoint and cover [0, D)."""
    run = run_simulation(floor_cfg(250.0, D=400))
    covered = []
    for (s, e) in run.round_ranges["round-1"].values():
        covered.extend(range(s, e))
    for sl in run.reserve_slices["round-1"]:
        covered.extend(range(sl.range_start, sl.range_end))
    assert sorted(covered) == list(range(400))             # exact cover, no overlap


# ---------------------------------------------------------------- S3-08
def test_s3_08_activated_reserve_searches_only_its_slice():
    """An activated reserve evaluates only nonces inside its assigned reserve slice."""
    run = run_simulation(floor_cfg(250.0))
    by_id = run.reserve_slice_by_id
    for rec in run.evaluation_ledger:
        if rec.assignment_kind != ACTIVATED_RESERVE_ASSIGNMENT:
            continue
        rr = run.reserve_records[(rec.RoundID, rec.MinerID)]
        sl = by_id[rr.assigned_reserve_slice_id]
        assert sl.range_start <= rec.interval_start and rec.interval_end <= sl.range_end


# ---------------------------------------------------------------- S3-09
def test_s3_09_ledger_zero_duplicate_across_primary_and_reserve():
    """The ledger has zero duplicate (TemplateID, nonce) across primary AND reserve miners."""
    run = run_simulation(floor_cfg(250.0))
    seen = set()
    dup = 0
    for rec in run.evaluation_ledger:
        for nonce in rec.nonces():
            key = (rec.TemplateID, nonce)
            if key in seen:
                dup += 1
            seen.add(key)
    assert dup == 0


# ---------------------------------------------------------------- S3-10
def test_s3_10_exact_replay_creates_no_second_activation():
    """Exact replay of a ReserveActivationRequestID creates no second event or slice claim."""
    run = RunInitialise(floor_cfg(250.0))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    eq = run.event_queue
    eq.current_event_time = 5.0
    eq.current_delta_cycle = 0
    eq.current_microphase = "RANGE_EXHAUST_ADJUDICATE"
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "RangeExhaustEvent", 5.0, 0,
                                    "RANGE_EXHAUST_ADJUDICATE", 1)
    rr = ReserveMinerRecord("M002", "round-1", "tpl-round-1", 300.0, "AVAILABLE", 0)
    run.reserve_records[("round-1", "M002")] = rr
    sl = RangeSlice("RS-round-1-0", ACTIVATED_RESERVE_ASSIGNMENT, 200, 300)
    run.reserve_slices["round-1"] = [sl]
    run.reserve_slice_by_id["RS-round-1-0"] = sl
    obs = SecurityFloorObservation(("R", "OBS", 1), "round-1", "tpl-round-1", 5.0,
                                   "range_exhaust", 0.0, 0, 250.0, None, 250.0, 0, True)
    req1 = SeatReserveActivation(run, rc, rr, sl, obs, ("R", "DEC", 1))
    n1 = sum(1 for r in eq.queued_event_registry.values()
             if r.event_type == "ReserveActivationStartEvent")
    assert run.security_stats["activations_seated"] == 1 and n1 == 1
    req2 = SeatReserveActivation(run, rc, rr, sl, obs, ("R", "DEC", 1))   # exact replay
    n2 = sum(1 for r in eq.queued_event_registry.values()
             if r.event_type == "ReserveActivationStartEvent")
    assert req2 is req1                                     # same request, no new effect
    assert run.security_stats["activations_seated"] == 1 and n2 == 1
    assert sum(1 for s in run.reserve_slices["round-1"] if s.status == "CLAIMED") == 1


# ---------------------------------------------------------------- S3-11
def test_s3_11_stale_cross_round_activation_no_effect():
    """A round-1 activation event dispatched during round-2 performs no domain effect."""
    run = RunInitialise(floor_cfg(250.0))
    rc2 = RoundContext("round-2", run, round_state="SOLUTION_PROPAGATION",
                       TemplateID_committed="tpl-round-2")
    run.current_round_context = rc2
    eq = run.event_queue
    eq.current_event_time = 9.0
    run.reserve_records[("round-1", "M002")] = ReserveMinerRecord(
        "M002", "round-1", "tpl-round-1", 300.0, "ACTIVATION_PENDING", 0,
        activation_generation=1)
    sl = RangeSlice("RS-round-1-0", ACTIVATED_RESERVE_ASSIGNMENT, 200, 300,
                    status="CLAIMED", claimed_by="M002")
    run.reserve_slice_by_id["RS-round-1-0"] = sl
    stale = {"ReserveActivationRequestID": ("x",), "SecurityFloorObservationID": ("o",),
             "ReserveActivationDecisionID": ("d",), "RoundID_at_seat": "round-1",
             "TemplateID_at_seat": "tpl-round-1", "MinerID": "M002",
             "ReserveSliceID": "RS-round-1-0", "activation_generation": 1,
             "expected_reserve_status": "ACTIVATION_PENDING", "expected_round_state_version": 0}
    res = _handle_reserve_activation_start(run, stale, {})
    assert res.kind == "reserve_activation_start_no_effect"
    assert res.reason.reason == "round_mismatch"           # stale for the current round


# ---------------------------------------------------------------- S3-12
def test_s3_12_pool_insufficient_floor_unattainable_reports_residual():
    """When the reserve pool cannot restore the floor, FLOOR_UNATTAINABLE reports a residual."""
    run = run_simulation(floor_cfg(100_000.0))             # far above total capacity
    assert run.security_stats["floor_unattainable_count"] > 0
    unatt = [d for d in run.activation_decisions if d.policy_result == "FLOOR_UNATTAINABLE"]
    assert unatt and all(d.residual_deficit > 0 for d in unatt)


# ---------------------------------------------------------------- S3-13
def test_s3_13_continue_degraded_accumulates_exact_duration_below_floor():
    """CONTINUE_DEGRADED accumulates exactly the duration H_effective is below the floor."""
    run = run_simulation(floor_cfg(100_000.0, unattainable="CONTINUE_DEGRADED"))
    # independently recompute the below-floor duration from the observation stream.
    per_round = {}
    for o in run.security_observations:
        per_round.setdefault(o.RoundID, []).append(o)
    total = 0.0
    for rid, obs in per_round.items():
        obs = sorted(obs, key=lambda o: o.observation_time)
        since = None
        for o in obs:
            if o.breached and since is None:
                since = o.observation_time
            elif not o.breached and since is not None:
                total += o.observation_time - since
                since = None
        if since is not None:
            total += run.round_terminal_times.get(rid, since) - since
    assert run.security_stats["total_duration_below_floor"] > 0
    assert abs(run.security_stats["total_duration_below_floor"] - total) < 1e-9


# ---------------------------------------------------------------- S3-14
def test_s3_14_abort_round_closes_through_owner_no_live_activation():
    """ABORT_ROUND floor-unattainable closes via the round-closure owner; nothing lives on."""
    run = run_simulation(floor_cfg(100_000.0, unattainable="ABORT_ROUND"))
    assert any(o.kind == "round_aborted"
               and o.data.get("reason") == "security_floor_unattainable" for o in run.log)
    # no reserve request/record/event survives.
    assert not any(rr.reserve_status in ("ACTIVATION_PENDING", "WAKING")
                   for rr in run.reserve_records.values())
    assert not any(r.event_type in ("ReserveActivationStartEvent",
                                    "ReserveActivationCompleteEvent")
                   and r.queue_status in ("QUEUED", "DISPATCHING")
                   for r in run.event_queue.queued_event_registry.values())


# ---------------------------------------------------------------- S3-15
def test_s3_15_closure_cancels_pending_waking_and_terminalises_slices():
    """Round closure cancels ACTIVATION_PENDING/WAKING reserves and terminalises slices."""
    # easy difficulty -> a primary accepts quickly; large activation wake -> a reserve is
    # still WAKING at acceptance, so closure must cancel it.
    cfg = floor_cfg(350.0, difficulty=20, D=1200, act_wake=100.0, horizon=400.0)
    run = run_simulation(cfg)
    assert run.security_stats["activations_cancelled"] > 0
    cancelled = [rr for rr in run.reserve_records.values() if rr.reserve_status == "CANCELLED"]
    assert cancelled
    # every reserve record ends terminal; every slice ends terminal.
    assert all(rr.reserve_status in ("AVAILABLE", "CANCELLED", "EXHAUSTED",
                                     "UNUSED_AT_ROUND_CLOSE", "ACTIVE")
               for rr in run.reserve_records.values())
    for slices in run.reserve_slices.values():
        assert all(sl.status in ("EXHAUSTED", "UNUSED_AT_ROUND_CLOSE") for sl in slices)


# ---------------------------------------------------------------- S3-16
def test_s3_16_reserve_energy_equals_residency_terms():
    """An activated reserve's energy equals its reserve/wake/active/idle residency terms."""
    cfg = floor_cfg(250.0)
    run = run_simulation(cfg)
    P = cfg.per_miner_power
    reserve_ids = getattr(run, "reserve_miner_ids", set())
    checked = 0
    for mid in reserve_ids:
        m = run.miners[mid]
        manual = (P("RESERVE") * m.duration["RESERVE"] + P("WAKING") * m.duration["WAKING"]
                  + P("ACTIVE_HASHING") * m.duration["ACTIVE_HASHING"]
                  + P("LOW_POWER_LISTEN") * m.duration["LOW_POWER_LISTEN"])
        assert abs(run.miner_energy_joules(mid) - manual) < 1e-9
        if m.duration["WAKING"] > 0 and m.duration["ACTIVE_HASHING"] > 0:
            checked += 1                                    # a full activation lifecycle
    assert checked > 0                                      # at least one reserve fully activated


# ---------------------------------------------------------------- S3-17
def test_s3_17_floor_does_not_change_target_or_difficulty():
    """Changing the security floor changes neither the difficulty nor the fixed target."""
    a = floor_cfg(250.0, difficulty=1000)
    b = floor_cfg(999_999.0, difficulty=1000)
    assert a.difficulty == b.difficulty == 1000
    assert target_for_difficulty(a.difficulty) == target_for_difficulty(b.difficulty)
    assert a.security_floor.minimum_active_hash_rate != b.security_floor.minimum_active_hash_rate


# ---------------------------------------------------------------- S3-18
def test_s3_18_full_domain_no_block_includes_reserve_slices_once():
    """Full-domain no-block exhaustion covers every primary + reserve slice exactly once."""
    run = run_simulation(floor_cfg(250.0, D=400))          # zero-solution + positive floor
    r1 = [rec for rec in run.evaluation_ledger if rec.RoundID == "round-1"]
    covered = []
    for rec in r1:
        covered.extend(rec.nonces())
    assert sorted(covered) == list(range(400))             # every nonce once
    assert all(sl.status == "EXHAUSTED" for sl in run.reserve_slices["round-1"])
    kinds = {rec.assignment_kind for rec in r1}
    assert kinds == {PRIMARY_ASSIGNMENT, ACTIVATED_RESERVE_ASSIGNMENT}


# ---------------------------------------------------------------- S3 adapter schema
def test_s3_adapter_schema_stage3_fields():
    """The adapter schema is stage5b.1 and carries the declared Stage-3 security fields,
    with continuous_all_active_control_kwh kept as an accounting reference (S3 results)."""
    out = run_pocol_stage2({"num_miners": 6, "horizon_T": 150.0, "nonce_domain_size": 900,
                            "reserve_fraction": 0.34}, include_matched_experiment=False)
    assert out["schema_version"] == "stage5b.1"
    for key in ("security_floor_enabled", "configured_minimum_active_hash_rate",
                "minimum_active_miner_count", "security_floor_observation_count",
                "breach_count", "reserve_activation_decision_count",
                "reserve_activations_seated", "reserve_activations_completed",
                "reserve_activations_cancelled", "floor_unattainable_count",
                "total_duration_below_floor", "maximum_hash_rate_deficit",
                "reserve_standby_energy_kwh", "reserve_wake_energy_kwh",
                "reserve_active_energy_kwh", "activated_reserve_evaluation_count"):
        assert key in out
    assert "continuous_all_active_control_kwh" in out         # accounting reference, kept
    assert "matched_control_kwh" not in out                   # never a matched saving basis


# ================================================================ Stage-3A corrections
def _live_assignment(mid, aid, ver, rng, rid="round-1", tid="tpl-round-1"):
    return {"MinerID": mid, "AssignmentID": aid, "assignment_version": ver, "range": rng,
            "RoundID": rid, "TemplateID": tid, "coverage_state": "OPEN"}


def _seated_activation(min_rate=250.0):
    """Seat ONE real reserve activation via EvaluateSecurityFloor (full obs->decision->request
    chain) and return ``(run, rc, req, start_ref)`` for the identity/lifecycle tests."""
    run = RunInitialise(floor_cfg(min_rate))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    eq = run.event_queue
    eq.current_event_time = 5.0
    eq.current_delta_cycle = 0
    eq.current_microphase = "RANGE_EXHAUST_ADJUDICATE"
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "RangeExhaustEvent", 5.0, 0,
                                    "RANGE_EXHAUST_ADJUDICATE", 1)
    run.create_miner("M002", 0.0, state="RESERVE")
    run.reserve_records[("round-1", "M002")] = ReserveMinerRecord(
        "M002", "round-1", "tpl-round-1", 300.0, "AVAILABLE", 0)
    sl = RangeSlice("RS-round-1-0", ACTIVATED_RESERVE_ASSIGNMENT, 200, 300)
    run.reserve_slices["round-1"] = [sl]
    run.reserve_slice_by_id["RS-round-1-0"] = sl
    EvaluateSecurityFloor(run, rc, 5.0, "range_exhaust")
    req = next(iter(run.activation_requests.values()))
    return run, rc, req, req.start_event_ref


# ---------------------------------------------------------------- S3A-01
def test_s3a_01_active_hashing_missing_assignment_excluded():
    """An ACTIVE_HASHING miner with a search state but NO assignment record is excluded from
    H_effective (the missing-assignment-as-current fallback is removed)."""
    run = RunInitialise(floor_cfg(250.0))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    run.create_miner("P", 0.0, state="ACTIVE_HASHING")
    stp = MinerSearchState("P", "A", 1, 100.0, 0, 50, 21.5, 2.15)
    stp.active_start = 0.0
    rc.search_states["P"] = stp
    rc.assignments["A"] = _live_assignment("P", "A", 1, (0, 50))
    # Q is ACTIVE_HASHING with a search state but its assignment record is MISSING.
    run.create_miner("Q", 0.0, state="ACTIVE_HASHING")
    stq = MinerSearchState("Q", "AQ", 1, 200.0, 50, 100, 21.5, 2.15)
    stq.active_start = 0.0
    rc.search_states["Q"] = stq                              # "AQ" deliberately absent
    h, cnt, ids = compute_h_effective(run, rc)
    assert h == 100.0 and cnt == 1 and "Q" not in ids       # no fallback: Q excluded
    rc.assignments["AQ"] = _live_assignment("Q", "AQ", 1, (50, 100))
    h2, cnt2, ids2 = compute_h_effective(run, rc)
    assert h2 == 300.0 and cnt2 == 2 and "Q" in ids2        # a live assignment now counts


# ---------------------------------------------------------------- S3A-02
def test_s3a_02_sequential_wakes_observe_and_measure_initial_interval():
    """Sequential primary WakeCompleteEvents create observations at each capacity change and
    the initial below-floor interval (round start -> primaries active) is measured."""
    run = run_simulation(floor_cfg(250.0, num_miners=4, reserve_fraction=0.5))
    reasons = [o.observation_reason for o in run.security_observations]
    assert "participants_prepared" in reasons               # observed at round start
    assert reasons.count("primary_wake_complete") >= 2       # one observation per primary wake
    assert run.security_stats["early_wake_below_floor_duration"] > 0
    r1 = [o for o in run.security_observations if o.RoundID == "round-1"]
    prep = next(o for o in r1 if o.observation_reason == "participants_prepared")
    assert prep.breached and prep.effective_active_hash_rate == 0.0   # real first breach at start


# ---------------------------------------------------------------- S3A-03
def test_s3a_03_observation_key_replay_idempotent():
    """Replaying one SecurityFloorObservationKey creates no duplicate observation, decision or
    activation and advances no counter."""
    run = RunInitialise(floor_cfg(250.0))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    rc.search_states = {}
    eq = run.event_queue
    eq.current_event_time = 5.0
    eq.current_delta_cycle = 0
    eq.current_microphase = "RANGE_EXHAUST_ADJUDICATE"
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "RangeExhaustEvent", 5.0, 0,
                                    "RANGE_EXHAUST_ADJUDICATE", 1)
    run.reserve_records[("round-1", "M002")] = ReserveMinerRecord(
        "M002", "round-1", "tpl-round-1", 300.0, "AVAILABLE", 0)
    sl = RangeSlice("RS-round-1-0", ACTIVATED_RESERVE_ASSIGNMENT, 200, 300)
    run.reserve_slices["round-1"] = [sl]
    run.reserve_slice_by_id["RS-round-1-0"] = sl
    EvaluateSecurityFloor(run, rc, 5.0, "range_exhaust")     # first observation: seats one
    obs0 = run.security_stats["observation_count"]
    seated0 = run.security_stats["activations_seated"]
    dec0 = run.security_stats["decision_count"]
    assert obs0 == 1 and seated0 == 1 and dec0 == 1
    EvaluateSecurityFloor(run, rc, 5.0, "range_exhaust")     # exact replay: same key
    assert run.security_stats["observation_count"] == obs0
    assert run.security_stats["activations_seated"] == seated0
    assert run.security_stats["decision_count"] == dec0
    assert run.security_stats["observation_replay_count"] == 1


# ---------------------------------------------------------------- S3A-04
def test_s3a_04_minimum_cardinality_selects_single_high_rate():
    """Rates [10, 100] with need 90 select ONLY the 100-rate reserve (minimum cardinality)."""
    r10 = ReserveMinerRecord("M-lo", "round-1", "tpl", 10.0, "AVAILABLE", 0)
    r100 = ReserveMinerRecord("M-hi", "round-1", "tpl", 100.0, "AVAILABLE", 1)
    chosen = select_reserves_to_cover([r10, r100], 90.0, 10)
    assert [r.MinerID for r in chosen] == ["M-hi"] and len(chosen) == 1
    # cardinality is established BEFORE priority tie-breaking: even when the low-rate reserve
    # has the lower activation priority, the single 100-rate reserve is still selected.
    r10b = ReserveMinerRecord("M-lo", "round-1", "tpl", 10.0, "AVAILABLE", 0)
    r100b = ReserveMinerRecord("M-hi", "round-1", "tpl", 100.0, "AVAILABLE", 9)
    chosen2 = select_reserves_to_cover([r10b, r100b], 90.0, 10)
    assert [r.MinerID for r in chosen2] == ["M-hi"] and len(chosen2) == 1


# ---------------------------------------------------------------- S3A-05
def test_s3a_05_start_seat_failure_rolls_back():
    """A failed StartEvent seat rolls back the slice claim, reserve status, request and
    counters ALL-OR-NONE."""
    run = RunInitialise(floor_cfg(250.0))
    rc = RoundContext("round-1", run, round_state="SOLUTION_PROPAGATION",
                      TemplateID_committed="tpl-round-1")
    run.current_round_context = rc
    eq = run.event_queue
    eq.current_event_time = 5.0
    eq.current_delta_cycle = 0
    eq.current_microphase = "RANGE_EXHAUST_ADJUDICATE"
    eq.current_event_seq = 1
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "RangeExhaustEvent", 5.0, 0,
                                    "RANGE_EXHAUST_ADJUDICATE", 1)
    rr = ReserveMinerRecord("M002", "round-1", "tpl-round-1", 300.0, "AVAILABLE", 0)
    run.reserve_records[("round-1", "M002")] = rr
    sl = RangeSlice("RS-round-1-0", ACTIVATED_RESERVE_ASSIGNMENT, 200, 300)
    run.reserve_slices["round-1"] = [sl]
    run.reserve_slice_by_id["RS-round-1-0"] = sl
    obs = SecurityFloorObservation(("R", "OBS", 1), "round-1", "tpl-round-1", 5.0,
                                   "range_exhaust", 0.0, 0, 250.0, None, 250.0, 0, True)
    run.force_activation_start_seat_failure = True
    res = SeatReserveActivationTransaction(run, rc, rr, sl, obs, ("R", "DEC", 1))
    assert res.kind == "reserve_activation_seat_failed"
    assert sl.status == "UNCLAIMED" and sl.claimed_by is None
    assert rr.reserve_status == "AVAILABLE" and rr.activation_request_id is None
    assert run.security_stats["activations_seated"] == 0
    assert run.security_stats["activation_seat_rollback_count"] == 1
    assert not run.activation_requests                       # no request committed


# ---------------------------------------------------------------- S3A-06
def test_s3a_06_complete_seat_failure_no_stranded_waking():
    """A failed CompleteEvent seat never leaves a WAKING miner without a controller: the
    request/reserve are terminalised, the slice restored, and the miner returns to idle."""
    run, rc, req, start_ref = _seated_activation()
    eq = run.event_queue
    rec = eq.queued_event_registry[start_ref]
    run.force_activation_complete_seat_failure = True
    eq.current_event_ref = start_ref
    eq.current_event_time = start_ref.event_time
    res = _handle_reserve_activation_start(run, rec.immutable_payload, rec.dispatch_envelope)
    assert res.kind == "reserve_activation_start_complete_seat_failed"
    assert run.miners["M002"].state == "LOW_POWER_LISTEN"    # NOT stranded WAKING
    assert run.reserve_records[("round-1", "M002")].reserve_status == "CANCELLED"
    assert req.status == "FAILED"
    assert run.reserve_slice_by_id["RS-round-1-0"].status == "UNCLAIMED"   # slice restored
    assert run.security_stats["activation_complete_seat_failure_count"] == 1


# ---------------------------------------------------------------- S3A-07
def test_s3a_07_tampered_identity_no_effect():
    """A tampered request / observation / decision id, round-state version or EventRef makes
    the activation event perform NO effect; the untampered event is the control."""
    run, rc, req, start_ref = _seated_activation()
    eq = run.event_queue
    good = dict(eq.queued_event_registry[start_ref].immutable_payload)
    eq.current_event_ref = start_ref
    eq.current_event_time = start_ref.event_time

    def start(**over):
        p = dict(good)
        p.update(over)
        return _handle_reserve_activation_start(run, p, {})

    assert start(ReserveActivationRequestID=("x",)).kind == "reserve_activation_start_no_effect"
    assert start(SecurityFloorObservationID=("x",)).kind == "reserve_activation_start_no_effect"
    assert start(ReserveActivationDecisionID=("x",)).kind == "reserve_activation_start_no_effect"
    assert start(expected_round_state_version=999).kind == "reserve_activation_start_no_effect"
    # tampered EventRef: the current ref does not match the recorded start ref.
    eq.current_event_ref = EventRef("ORDINARY_EVENT", "ReserveActivationStartEvent",
                                    start_ref.event_time, 0, "RESERVE_ACTIVATION_START", 99999)
    assert _handle_reserve_activation_start(run, good, {}).kind \
        == "reserve_activation_start_no_effect"
    # nothing above mutated state: still SEATED / ACTIVATION_PENDING.
    assert req.status == "SEATED"
    assert run.reserve_records[("round-1", "M002")].reserve_status == "ACTIVATION_PENDING"
    # control: the untampered event with the correct ref DOES take effect.
    eq.current_event_ref = start_ref
    assert _handle_reserve_activation_start(run, good, {}).kind == "reserve_activation_started"


# ---------------------------------------------------------------- S3A-08
def test_s3a_08_completed_request_has_both_event_refs():
    """A completed activation request reaches COMPLETED with both EventRefs and timestamps."""
    run = run_simulation(floor_cfg(250.0))
    completed = [r for r in run.activation_requests.values() if r.status == "COMPLETED"]
    assert completed
    for r in completed:
        assert r.start_event_ref is not None and r.complete_event_ref is not None
        assert r.started_at is not None and r.completed_at is not None


# ---------------------------------------------------------------- S3A-09
def test_s3a_09_closure_terminalises_all_records_and_requests():
    """Round closure leaves every reserve record and activation request terminal — no
    closed-round record is ACTIVE or AVAILABLE."""
    run = run_simulation(floor_cfg(250.0))
    assert run.reserve_records
    assert all(rr.reserve_status in TERMINAL_RESERVE_STATUSES
               for rr in run.reserve_records.values())
    assert all(req.status in TERMINAL_REQUEST_STATUSES
               for req in run.activation_requests.values())
    assert not any(rr.reserve_status in ("ACTIVE", "AVAILABLE", "ACTIVATION_PENDING", "WAKING")
                   for rr in run.reserve_records.values())


# ---------------------------------------------------------------- S3A-10
def test_s3a_10_floor_zero_unused_reserve_domain_not_full_domain():
    """Floor == 0 with UNCLAIMED reserve slices closes with the explicit unused-reserve-domain
    disposition and is NEVER labelled full-domain exhaustion."""
    run = run_simulation(floor_cfg(0.0, D=400))
    assert run.security_stats["unused_reserve_domain_count"] > 0
    assert run.security_stats["full_domain_exhausted_count"] == 0
    assert any(o.kind == "round_aborted"
               and o.data.get("reason") == ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN
               for o in run.log)
    # the reserve domain was NOT searched.
    assert not any(rec.assignment_kind == ACTIVATED_RESERVE_ASSIGNMENT
                   for rec in run.evaluation_ledger)
    assert all(sl.status == "UNUSED_AT_ROUND_CLOSE" for sl in run.reserve_slices["round-1"])


# ---------------------------------------------------------------- S3A-11
def test_s3a_11_true_full_domain_exhaustion_covers_all_once():
    """A true full-domain no-block exhaustion searches every primary AND reserve nonce exactly
    once and closes with the full-domain disposition (all reserve slices EXHAUSTED)."""
    run = run_simulation(floor_cfg(250.0, D=400))
    assert run.security_stats["full_domain_exhausted_count"] > 0
    assert any(o.kind == "round_aborted"
               and o.data.get("reason") == FULL_DOMAIN_EXHAUSTED_NO_BLOCK for o in run.log)
    r1 = [rec for rec in run.evaluation_ledger if rec.RoundID == "round-1"]
    covered = []
    for rec in r1:
        covered.extend(rec.nonces())
    assert sorted(covered) == list(range(400))               # every nonce exactly once
    assert all(sl.status == "EXHAUSTED" for sl in run.reserve_slices["round-1"])
    assert {rec.assignment_kind for rec in r1} == {PRIMARY_ASSIGNMENT,
                                                   ACTIVATED_RESERVE_ASSIGNMENT}


# ---------------------------------------------------------------- S3A-12
def test_s3a_12_adapter_enables_floor_and_activates_from_config():
    """The BlockSim adapter enables the floor and executes reserve activation from a config
    dictionary, and rejects unsupported policy names and negative values."""
    out = run_pocol_stage2({
        "num_miners": 4, "reserve_fraction": 0.5, "nonce_domain_size": 400,
        "difficulty": _ZERO_SOLUTION, "batch_size": 25, "horizon_T": 300.0,
        "P_reserve": 2.15, "security_floor_enabled": True,
        "minimum_active_hash_rate": 250.0, "activation_wake_latency": 1.0,
        "reserve_selection_policy": "MINIMUM_CARDINALITY",
        "floor_unattainable_policy": "CONTINUE_DEGRADED",
    }, include_matched_experiment=False)
    assert out["security_floor_enabled"] is True
    assert out["configured_minimum_active_hash_rate"] == 250.0
    assert out["security_floor_observation_count"] >= 1
    assert out["reserve_activations_seated"] >= 1
    assert out["reserve_activations_completed"] >= 1
    # validation: unsupported policy names and negative rates/latencies are rejected.
    with pytest.raises(ValueError):
        run_pocol_stage2({"security_floor_enabled": True,
                          "reserve_selection_policy": "NONSENSE"})
    with pytest.raises(ValueError):
        run_pocol_stage2({"security_floor_enabled": True, "minimum_active_hash_rate": -5})
    with pytest.raises(ValueError):
        run_pocol_stage2({"security_floor_enabled": True,
                          "floor_unattainable_policy": "EXPLODE"})
