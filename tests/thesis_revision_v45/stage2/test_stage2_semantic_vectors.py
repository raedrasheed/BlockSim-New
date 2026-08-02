"""Stage-2 semantic test vectors TV325-TV338 (executable).

Each vector exercises a mandatory Stage-1AJ backlog fix or a frozen Stage-1 scheduler
contract against the executable PoCol core.  The algorithm is PoCol; the mechanism is
the idle policy within PoCol.
"""
from __future__ import annotations

import pytest

from Models.PoCol.stage2 import (
    Stage2Config, RunInitialise, RunEventLoopToHorizon, RoundContext, RoundAbort,
    SeatMinerRegister, ScheduleEvent, Driver, Outcome, EXACT_ROUND,
    NEXT_AVAILABLE_ROUND, RUN_LEVEL, CancelQueuedEvent, run_simulation,
    a1_continuous_control_kwh, A1_BASELINE_KWH,
)


def fresh_run(**kw):
    return RunInitialise(Stage2Config(**kw))


def admitting_round(run, rid="round-1", state="ASSIGNMENT", t=0.0):
    rc = RoundContext(RoundID=rid, run_context=run, round_state=state)
    run.current_round_context = rc
    run.event_queue.current_event_time = t
    return rc


# ---------------------------------------------------------------- TV325
def test_tv325_partial_genesis_seating_then_abort():
    """Partial genesis seating followed by abort terminalises every round request."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    ids = []
    for i in range(3):
        a = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                     {"join_request": {"MinerID": f"M{i}"}})
        ids.append(a.DriverRequestID)
    assert SeatMinerRegister(run, run.driver_request_registry[ids[0]],
                             "DRIVER_INTAKE").kind == "miner_register_seated"
    assert SeatMinerRegister(run, run.driver_request_registry[ids[1]],
                             "DRIVER_INTAKE").kind == "miner_register_seated"
    # ids[2] left PENDING; now abort the round.
    run.event_queue.current_event_time = 5.0
    RoundAbort(run, rc, "test_abort", envelope={})
    for did in ids:
        assert run.driver_request_registry[did].status == "CANCELLED"
    assert not run.pending_driver_request_index          # no request left dangling


# ---------------------------------------------------------------- TV326
def test_tv326_queued_exact_round_event_cancelled_before_next_round():
    """A queued EXACT_ROUND driver event is cancelled at closure — never carried on."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    a = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                 {"join_request": {"MinerID": "MX"}})
    dr = run.driver_request_registry[a.DriverRequestID]
    seat = SeatMinerRegister(run, dr, "DRIVER_INTAKE")
    er = seat.event_ref
    assert run.event_queue.queued_event_registry[er].queue_status == "QUEUED"
    run.event_queue.current_event_time = 5.0
    RoundAbort(run, rc, "test_abort", envelope={})
    assert run.event_queue.queued_event_registry[er].queue_status == "CANCELLED"
    assert er not in run.event_queue.event_queue           # gone from the pending frontier


# ---------------------------------------------------------------- TV327
def test_tv327_next_available_round_effective_timing():
    """NEXT_AVAILABLE_ROUND seats at a legal effective time; requested stays immutable."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=60.0)
    run.last_finalised_event_time = 50.0
    run.event_queue.finalised_event_times.add(50.0)
    a = run.admit_driver_request("MINER_JOIN", 50.0, NEXT_AVAILABLE_ROUND,
                                 {"join_request": {"MinerID": "MN"}})
    dr = run.driver_request_registry[a.DriverRequestID]
    res = SeatMinerRegister(run, dr, "DRIVER_INTAKE")
    assert res.kind == "miner_register_seated"
    assert dr.requested_event_time == 50.0                 # immutable original (backlog-5)
    assert dr.effective_event_time > 50.0                  # legal effective seat time (backlog-4)
    assert dr.effective_event_time not in run.event_queue.finalised_event_times


# ---------------------------------------------------------------- TV328
def test_tv328_partial_run_finalization_before_horizon():
    """A next-round seat failure terminates the run PARTIAL before the horizon (AI6)."""
    cfg = Stage2Config(num_miners=4, horizon_T=10_000.0, reserve_fraction=0.25)
    run = RunInitialise(cfg)
    run.force_bootstrap_seat_failure = True
    res = RunEventLoopToHorizon(run)
    assert res.kind == "run_completed_partial"
    assert res.partial_end_time < cfg.horizon_T
    assert run.next_round_bootstrap_status == "NEXT_ROUND_BOOTSTRAP_FAILED"
    assert run.run_finalised


# ---------------------------------------------------------------- TV329
def test_tv329_keyed_persistent_request_update():
    """SetDriverRequestStatus is the keyed guarded mutator; a stale expectation fails."""
    run = fresh_run()
    a = run.admit_driver_request("MINER_JOIN", 0.0, NEXT_AVAILABLE_ROUND,
                                 {"join_request": {"MinerID": "MA"}})
    did = a.DriverRequestID
    r1 = run.set_driver_request_status(did, "PENDING", "REJECTED", Outcome("x"))
    assert r1.kind == "driver_request_status_set"
    assert run.driver_request_registry[did].status == "REJECTED"
    r2 = run.set_driver_request_status(did, "PENDING", "SEATED", Outcome("y"))
    assert r2.kind == "driver_request_status_mismatch"     # keyed CAS guard holds


# ---------------------------------------------------------------- TV330
def test_tv330_seat_publication_coherent():
    """The reverse binding + SEATED are published atomically with the seat."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    a = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                 {"join_request": {"MinerID": "MP"}})
    dr = run.driver_request_registry[a.DriverRequestID]
    seat = SeatMinerRegister(run, dr, "DRIVER_INTAKE")
    er = seat.event_ref
    assert run.driver_request_by_seat_event_ref[er] == dr.DriverRequestID
    assert dr.status == "SEATED" and dr.seated_event_ref == er
    assert dr.DriverRequestID not in run.pending_driver_request_index
    # completing the dispatch drives the exact request SEATED -> CONSUMED.
    done = run.complete_driver_request_on_dispatch(
        er, Outcome("driver_request_consumed", handler_result=Outcome("ok")))
    assert done.kind == "driver_request_status_set"
    assert dr.status == "CONSUMED"


# ---------------------------------------------------------------- TV331
def test_tv331_cancellation_coherence():
    """Cancelling a seated driver event cancels the queue entry AND the request."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    a = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                 {"join_request": {"MinerID": "MC"}})
    dr = run.driver_request_registry[a.DriverRequestID]
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    CancelQueuedEvent(run.event_queue, run, er, "test_cancel")
    assert run.event_queue.queued_event_registry[er].queue_status == "CANCELLED"
    assert dr.status == "CANCELLED"


# ---------------------------------------------------------------- TV332
def test_tv332_distinct_equal_deficit_reserve_incidents():
    """Two distinct reserve incidents with EQUAL deficit get DISTINCT DriverRequestIDs."""
    run = fresh_run()
    p1 = {"RoundID_at_seat": "round-1", "deficit": 5, "incident_id": "inc-1"}
    p2 = {"RoundID_at_seat": "round-1", "deficit": 5, "incident_id": "inc-2"}
    a1 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0,
                                  EXACT_ROUND("round-1"), p1)
    a2 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0,
                                  EXACT_ROUND("round-1"), p2)
    assert a1.kind == "driver_request_admitted" and a2.kind == "driver_request_admitted"
    assert a1.DriverRequestID != a2.DriverRequestID


# ---------------------------------------------------------------- TV333
def test_tv333_replay_of_same_reserve_incident():
    """A replay of the SAME reserve incident returns the SAME DriverRequestID."""
    run = fresh_run()
    p = {"RoundID_at_seat": "round-1", "deficit": 5, "incident_id": "inc-1"}
    a1 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0,
                                  EXACT_ROUND("round-1"), p)
    a2 = run.admit_driver_request("ORDINARY_RESERVE_DEFICIT", 0.0,
                                  EXACT_ROUND("round-1"), dict(p))
    assert a2.kind == "driver_request_already_admitted"
    assert a2.DriverRequestID == a1.DriverRequestID


# ---------------------------------------------------------------- TV334
def test_tv334_foreign_run_context_sharing_eq_rejected():
    """A driver seat whose carried RunContext is not the EQ owner is rejected (backlog-11)."""
    run = fresh_run()
    eq = run.event_queue
    foreign = fresh_run()                                  # its own distinct EQ
    origin = Driver("MINER_JOIN", ("x", 1), 0.0, 0.0, NEXT_AVAILABLE_ROUND,
                    run_ctx=foreign, eq=eq)
    res = ScheduleEvent(eq, None, "MinerRegisterEvent", 0.0, "REGISTRATION",
                        {"join_request": {"MinerID": "MZ"}}, origin)
    assert res.kind == "rejected_driver_context_mismatch"


# ---------------------------------------------------------------- TV335
def test_tv335_duplicate_genesis_join_request_id():
    """Two genesis joins with the same JoinRequestID collapse to one request."""
    run = fresh_run()
    a1 = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                  {"join_request": {"MinerID": "DUP"}})
    a2 = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                  {"join_request": {"MinerID": "DUP"}})
    assert a2.kind == "driver_request_already_admitted"
    assert a2.DriverRequestID == a1.DriverRequestID


# ---------------------------------------------------------------- TV336
def test_tv336_dispatch_of_already_cancelled_request():
    """Completing the dispatch of an already-CANCELLED seat never resurrects it."""
    run = fresh_run()
    rc = admitting_round(run, "round-1", "ASSIGNMENT", t=0.0)
    a = run.admit_driver_request("MINER_JOIN", 0.0, EXACT_ROUND("round-1"),
                                 {"join_request": {"MinerID": "MD"}})
    dr = run.driver_request_registry[a.DriverRequestID]
    er = SeatMinerRegister(run, dr, "DRIVER_INTAKE").event_ref
    CancelQueuedEvent(run.event_queue, run, er, "test_cancel")
    assert dr.status == "CANCELLED"
    res = run.complete_driver_request_on_dispatch(
        er, Outcome("driver_request_consumed", handler_result=Outcome("late")))
    assert res.kind == "driver_request_status_mismatch"
    assert dr.status == "CANCELLED"                        # not resurrected to CONSUMED


# ---------------------------------------------------------------- TV337
def test_tv337_driver_target_before_frontier_rejected():
    """AI2: a driver seat whose target is behind the simulation frontier is rejected."""
    run = fresh_run()
    run.last_finalised_event_time = 100.0
    origin = Driver("MINER_JOIN", ("x", 1), 50.0, 50.0, NEXT_AVAILABLE_ROUND,
                    run_ctx=run, eq=run.event_queue)       # source<=target but target<frontier
    res = ScheduleEvent(run.event_queue, None, "MinerRegisterEvent", 50.0, "REGISTRATION",
                        {"join_request": {"MinerID": "MB"}}, origin)
    assert res.kind == "rejected_driver_target_before_simulation_frontier"


# ---------------------------------------------------------------- TV338
def test_tv338_energy_acceptance_a1_and_idle_saving():
    """A1 continuous control reproduces the baseline; the idle policy saves vs A1."""
    assert abs(a1_continuous_control_kwh(Stage2Config()) - A1_BASELINE_KWH) < 1e-9
    cfg = Stage2Config(num_miners=8, horizon_T=200.0, reserve_fraction=0.25)
    run = run_simulation(cfg)
    E = run.total_energy_kwh()
    A1 = a1_continuous_control_kwh(cfg)
    assert 0.0 < E < A1                                    # idle-policy saving, not partitioning
    assert run.residency_reconciles(run.run_end_time)
