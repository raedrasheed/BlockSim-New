"""Stage-2A end-to-end tests E2E-1 .. E2E-5 for the mandatory core execution path.

The implementation is not acceptable if it runs only one round; these tests drive the
full path across MULTIPLE rounds — genesis admission, TemplateCommit, participant
preparation, StartWake, ACTIVE_HASHING, real nonce search, acceptance OR abort, closure,
rotation, horizon, and partial termination — and check the idle-policy energy/residency
reconciliation.  The energy saving comes from the idle policy (post-range low-power
residency), never from nonce partitioning.
"""
from __future__ import annotations

from Models.PoCol.stage2 import (Stage2Config, RunInitialise, RunEventLoopToHorizon,
                                  run_simulation, a1_continuous_control_kwh)


def _kinds(run):
    return [o.kind for o in run.log]


# ---------------------------------------------------------------- E2E-1
def test_e2e1_first_round_reaches_hashing_and_accepts():
    """Round 1 reaches ACTIVE_HASHING and closes by acceptance (real search)."""
    cfg = Stage2Config(num_miners=6, horizon_T=200.0, reserve_fraction=0.34,
                       nonce_domain_size=1200, batch_size=50)
    run = run_simulation(cfg)
    assert any(m.duration["ACTIVE_HASHING"] > 0 for m in run.miners.values())
    assert "wake_completed" in _kinds(run)
    assert "accepted_block" in _kinds(run)


# ---------------------------------------------------------------- E2E-2
def test_e2e2_first_round_aborts_then_second_round_starts():
    """An injected round-1 abort is followed by a genuine second round."""
    cfg = Stage2Config(num_miners=6, horizon_T=400.0, reserve_fraction=0.34,
                       nonce_domain_size=1200, abort_round_seqs=frozenset({1}))
    run = run_simulation(cfg)
    kinds = _kinds(run)
    assert "round_aborted" in kinds                       # round 1 aborted
    assert run.round_seq >= 2                              # a second round started
    assert kinds.count("round_initialised") >= 1


# ---------------------------------------------------------------- E2E-3
def test_e2e3_consecutive_rounds_no_event_leakage():
    """Across consecutive rounds no event or request leaks past its round."""
    cfg = Stage2Config(num_miners=6, horizon_T=300.0, reserve_fraction=0.34,
                       nonce_domain_size=1200)
    run = run_simulation(cfg)
    assert run.round_seq >= 2
    statuses = {rec.queue_status for rec in run.event_queue.queued_event_registry.values()}
    assert statuses <= {"CONSUMED", "CANCELLED"}          # every event terminal
    assert not run.event_queue.event_queue                # pending frontier empty at end
    assert all(dr.status in ("CONSUMED", "CANCELLED", "REJECTED")
               for dr in run.driver_request_registry.values())


# ---------------------------------------------------------------- E2E-4
def test_e2e4_reaches_horizon_energy_and_residency_reconcile():
    """The run reaches the horizon; residency partitions [0,T] and energy < A1."""
    cfg = Stage2Config(num_miners=8, horizon_T=600.0, reserve_fraction=0.25,
                       nonce_domain_size=1600)
    run = run_simulation(cfg)
    assert run.loop_result.kind == "run_completed"
    assert run.run_end_time == cfg.horizon_T
    assert run.residency_reconciles(cfg.horizon_T)        # I5: durations partition [0,T]
    E = run.total_energy_kwh()
    assert 0.0 < E < a1_continuous_control_kwh(cfg)       # idle-policy saving vs A1


# ---------------------------------------------------------------- E2E-5
def test_e2e5_next_round_bootstrap_failure_partial_finalization():
    """A next-round bootstrap seat failure terminates the run PARTIAL before the horizon."""
    cfg = Stage2Config(num_miners=5, horizon_T=10_000.0, reserve_fraction=0.2,
                       nonce_domain_size=1000)
    run = RunInitialise(cfg)
    run.force_bootstrap_seat_failure = True               # first rotation fails to seat
    res = RunEventLoopToHorizon(run)
    assert res.kind == "run_completed_partial"
    assert res.partial_end_time == run.prior_round_terminal_state["round_terminal_time"]
    assert res.partial_end_time < cfg.horizon_T           # declared partial, never full-horizon
    assert run.run_finalised and run.run_disposition == "next_round_bootstrap_failed"
    assert run.residency_reconciles(res.partial_end_time)
    # no live event or request survives the partial finalization.
    assert not any(r.queue_status in ("QUEUED", "DISPATCHING")
                   for r in run.event_queue.queued_event_registry.values())
    assert not any(d.status in ("PENDING", "SEATED")
                   for d in run.driver_request_registry.values())
