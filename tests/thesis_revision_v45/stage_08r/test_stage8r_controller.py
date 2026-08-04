"""Stage-8R controller tests R-TEST-01..R-TEST-18.

Every executed simulation uses either a PILOT seed or (R-TEST-01 only, as the directive
requires) the frozen Stage-7M M03 confirmatory seed 0 to REPRODUCE the already-frozen
Stage-8M record — no new confirmatory information is generated here.
"""
from __future__ import annotations

import dataclasses
import inspect
import json
import pathlib
import sys
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
for p in (str(REPO),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_06"),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_06m")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M6                                             # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,  # noqa: E402
                       nonterminal_activation_request_count)
from Models.PoCol.stage2.simulator import run_simulation              # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                # noqa: E402
from Models.PoCol.stage2 import refinement as R                       # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy           # noqa: E402
from Models.PoCol.stage2.leases import RangeLeasePolicy               # noqa: E402
from Models.PoCol.stage2.security import (TERMINAL_REQUEST_STATUSES,  # noqa: E402
                                          select_reserves_to_cover)

H0 = 4000.0
TARGET = 0.80 * H0            # 3200
TRIGGER = 0.78 * H0           # 3120
RECOVERY = 0.82 * H0          # 3280
COOLDOWN = 1.0                # == activation wake latency (frozen)

FROZEN_M03 = json.loads(
    (REPO / "experiments/thesis_revision_v45/stage_07m/runs"
     / "7m-M03_HET_IDLE_FLOOR-s00.json").read_text())


def _cfg(mode: str, leases: bool = False):
    cfg = M6.build_config_6m(M6.CONFIRMATORY[2], M6.pilot_seeds()[0])   # M03 core, PILOT seed
    kw = {"controller": ControllerPolicy(mode=mode)}
    if leases:
        kw["range_lease"] = RangeLeasePolicy(enabled=True)
    return dataclasses.replace(cfg, **kw)


@pytest.fixture(scope="module")
def r02():
    """One HYSTERESIS_PREDICTIVE run on a PILOT seed, shared by the data-derived tests."""
    cfg = _cfg("HYSTERESIS_PREDICTIVE")
    run = run_simulation(cfg, run_id="rtest-r02")
    return run, cfg, results_schema(run, cfg)


@pytest.fixture(scope="module")
def r03():
    cfg = _cfg("HYSTERESIS_PREDICTIVE_REASSIGNMENT", leases=True)
    run = run_simulation(cfg, run_id="rtest-r03")
    return run, cfg, results_schema(run, cfg)


# ------------------------------------------------------------------ R-TEST-01
def test_r01_legacy_reproduces_frozen_stage8m_m03():
    """LEGACY_REACTIVE reproduces the frozen Stage-8M M03 behaviour for the same seed."""
    seed = M6.confirmatory_seeds()[0]
    cfg = M6.build_config_6m(M6.CONFIRMATORY[2], seed)      # default = LEGACY_REACTIVE
    assert cfg.controller.mode == "LEGACY_REACTIVE"
    run = run_simulation(cfg, run_id="rtest-legacy")
    res = results_schema(run, cfg)
    assert len(run.round_terminal_times) == FROZEN_M03["rounds_executed"]
    assert res["rounds_accepted"] == FROZEN_M03["rounds_accepted"]
    assert res["energy_kwh"] == FROZEN_M03["E_idle_kwh"]
    assert res["reserve_activations_seated"] == FROZEN_M03["reserve_activations_seated"]
    assert res["reserve_activations_completed"] == \
        FROZEN_M03["reserve_activations_completed"]
    assert res["total_duration_below_floor"] == FROZEN_M03["total_duration_below_floor"]
    assert res["floor_unattainable_count"] == FROZEN_M03["floor_unattainable_count"]
    assert res["evaluation_ledger_entries"] == FROZEN_M03["evaluation_ledger_entries"]
    # the refinement layer stayed inert: no episode, no batch, no prediction.
    assert res["breach_episode_count"] == 0
    assert res["activation_batches_seated"] == 0
    assert res["prediction_decision_count"] == 0


# ------------------------------------------------------------------ R-TEST-02 / 03
def _fake_state(miner_state: str):
    st = SimpleNamespace(completed=False, AssignmentID="A1", assignment_version=1,
                         MinerID="M1", cursor=10, hash_rate=100.0)
    rc = SimpleNamespace(round_state="ROUND_HASHING", RoundID="r1",
                         TemplateID_committed="t1", search_states={"M1": st},
                         assignments={"A1": {"MinerID": "M1", "assignment_version": 1,
                                             "RoundID": "r1", "TemplateID": "t1",
                                             "range": (0, 80)}})
    run_ctx = SimpleNamespace(miners={"M1": SimpleNamespace(state=miner_state)},
                              activation_requests={}, reserve_records={})
    return run_ctx, rc


def test_r02_waking_contributes_zero_to_h_effective():
    from Models.PoCol.stage2.security import compute_h_effective    # noqa: PLC0415
    run_ctx, rc = _fake_state("ACTIVE_HASHING")
    h, n, ids = compute_h_effective(run_ctx, rc)
    assert (h, n) == (100.0, 1)
    run_ctx, rc = _fake_state("WAKING")
    h, n, ids = compute_h_effective(run_ctx, rc)
    assert (h, n, ids) == (0.0, 0, [])                    # WAKING is NOT physical capacity


def test_r03_waking_capacity_appears_only_in_h_pipeline():
    run_ctx, rc = _fake_state("WAKING")
    req = SimpleNamespace(RoundID="r1", status="STARTED", MinerID="M9",
                          started_at=0.0, seated_at=0.0)
    run_ctx.activation_requests = {"q1": req}
    run_ctx.reserve_records = {("r1", "M9"): SimpleNamespace(hash_rate=250.0)}
    from Models.PoCol.stage2.security import compute_h_effective    # noqa: PLC0415
    h, _n, _ids = compute_h_effective(run_ctx, rc)
    assert h == 0.0
    assert R.h_pipeline(run_ctx, rc, h) == 250.0          # forecast only, separate quantity


# ------------------------------------------------------------------ R-TEST-04 / 05 / 10
def test_r04_one_episode_never_owns_two_simultaneous_live_batches(r02):
    run, _cfg2, _res = r02
    assert run.breach_episodes, "the refined run must open episodes"
    for ep in run.breach_episodes.values():
        batches = [run.activation_batches[b] for b in ep.activation_batch_ids]
        batches.sort(key=lambda b: b.seated_at)
        for b1, b2 in zip(batches, batches[1:]):
            # b1 must be fully terminal BEFORE b2 was seated: within a round a batch
            # terminalises only when EVERY request completed (cancellation happens only at
            # round close, after which no batch can be seated in that round).
            ends = [run.activation_requests[q].completed_at for q in b1.request_ids]
            assert all(e is not None for e in ends), \
                f"episode {ep.BreachEpisodeID}: second batch seated while first live"
            assert max(ends) <= b2.seated_at + 1e-12


def test_r05_repeated_observations_are_replay_idempotent(r02):
    run, _cfg2, res = r02
    # every seated request belongs to exactly one batch and every batch to one episode
    seen = {}
    for batch in run.activation_batches.values():
        for q in batch.request_ids:
            assert q not in seen, "one activation request mapped into two batches"
            seen[q] = batch.BatchID
            assert run.batch_by_request[q] == batch.BatchID
    assert len(seen) == res["reserve_activations_seated"]
    # repeated capacity observations inside episodes occurred and seated nothing
    assert res["duplicate_activation_batch_prevented_count"] > 0
    assert res["security_floor_observation_count"] > res["activation_batches_seated"]


def test_r10_sufficient_live_batch_prevents_another(r02):
    run, _cfg2, res = r02
    assert res["duplicate_activation_batch_prevented_count"] > 0
    # and no episode ever exceeded one batch WITHOUT the first terminalising (test 04);
    # additionally the maximum LIVE batches at any time per episode is 1 by construction:
    for ep in run.breach_episodes.values():
        assert ep.live_activation_batch_id is None        # nothing live post-run


# ------------------------------------------------------------------ R-TEST-06
def test_r06_hysteresis_prevents_reopen_close_oscillation(r02):
    run, _cfg2, _res = r02
    recovered = [ep for ep in run.breach_episodes.values() if ep.status == "RECOVERED"]
    obs_by_time = {}
    for o in run.security_observations:
        obs_by_time.setdefault((o.RoundID, round(o.observation_time, 9)), []).append(o)
    for ep in run.breach_episodes.values():
        # a REACTIVE episode opens only strictly below the reactive trigger
        if ep.opened_reason == "REACTIVE":
            assert ep.opened_h_effective < TRIGGER + 1e-9
        # RECOVERED requires the recovery threshold, not merely the central target
        if ep.status == "RECOVERED":
            os_ = obs_by_time.get((ep.RoundID, round(ep.recovered_at, 9)), [])
            assert any(o.effective_active_hash_rate + 1e-9 >= RECOVERY for o in os_), \
                "episode closed RECOVERED without a recovery-threshold observation"
    # the deadband is real: some breached observations (below target, above trigger)
    # produced NO new episode — count observations inside the deadband
    deadband = [o for o in run.security_observations
                if TRIGGER <= o.effective_active_hash_rate < TARGET and o.breached]
    opened_at_times = {round(ep.opened_at, 9) for ep in run.breach_episodes.values()}
    inside = [o for o in deadband if round(o.observation_time, 9) in opened_at_times
              and any(ep.opened_reason == "REACTIVE"
                      and round(ep.opened_at, 9) == round(o.observation_time, 9)
                      and ep.opened_h_effective >= TRIGGER
                      for ep in run.breach_episodes.values())]
    assert not inside, "a reactive episode opened inside the hysteresis deadband"


# ------------------------------------------------------------------ R-TEST-07
def test_r07_cooldown_prevents_new_batch_during_interval(r02):
    run, _cfg2, _res = r02
    for ep in run.breach_episodes.values():
        batches = sorted((run.activation_batches[b] for b in ep.activation_batch_ids),
                         key=lambda b: b.seated_at)
        for b1, b2 in zip(batches, batches[1:]):
            gap = b2.seated_at - b1.seated_at
            if gap < COOLDOWN - 1e-12:
                # inside cooldown a new batch is legal ONLY when the prior batch is
                # terminal (test 04) AND capacity stayed below the frozen trigger.
                assert b2.seat_h_effective < TRIGGER + 1e-9, \
                    "batch seated inside cooldown without a persisting deficit"


# ------------------------------------------------------------------ R-TEST-08
def test_r08_predictive_activation_fires_before_reactive_trigger(r02):
    run, _cfg2, res = r02
    assert res["predictive_batches_seated"] > 0
    early = [b for b in run.activation_batches.values()
             if b.origin == "PREDICTIVE" and b.seat_h_effective >= TRIGGER - 1e-9]
    assert early, ("no predictive batch was seated while physical capacity was still at or "
                   "above the reactive trigger")


# ------------------------------------------------------------------ R-TEST-09
def test_r09_prediction_uses_observables_not_future_oracle():
    import ast                                                       # noqa: PLC0415
    tree = ast.parse(inspect.getsource(R.predict_h_future))
    fn = tree.body[0]
    fn.body = [n for n in fn.body                                    # strip the docstring
               if not (isinstance(n, ast.Expr) and isinstance(n.value, ast.Constant))]
    src = ast.unparse(fn)
    for forbidden in ("winning_nonce", "contained_solution", "_first_solution",
                      "header_bytes", "make_template", "round_terminal_time", "random",
                      "sha256"):
        assert forbidden not in src, f"prediction reads a forbidden source: {forbidden}"
    # executable: H_future counts a miner iff its remaining/rate exceeds the lookahead
    run_ctx, rc = _fake_state("ACTIVE_HASHING")
    run_ctx.config = SimpleNamespace(security_floor=SimpleNamespace(
        activation_wake_latency=1.0))
    h, det = R.predict_h_future(run_ctx, rc, now=0.0, lookahead=0.5, target_rate=TARGET)
    assert h == 100.0 and det["expiring"] == []           # 70 nonces / 100 Hz = 0.7 s > 0.5
    h, det = R.predict_h_future(run_ctx, rc, now=0.0, lookahead=0.8, target_rate=TARGET)
    assert h == 0.0 and det["expiring"] == ["M1"]         # 0.7 s <= 0.8 s -> expiring


# ------------------------------------------------------------------ R-TEST-11
def test_r11_minimum_cardinality_selection_deterministic():
    def pool():
        return [SimpleNamespace(MinerID=f"M{i}", hash_rate=r, activation_priority=i)
                for i, r in enumerate([10.0, 100.0, 50.0, 25.0])]
    a = select_reserves_to_cover(pool(), 90.0, 4, 0)
    b = select_reserves_to_cover(pool(), 90.0, 4, 0)
    assert [x.MinerID for x in a] == [x.MinerID for x in b] == ["M1"]   # single 100-rate


# ------------------------------------------------------------------ R-TEST-12 / 18
def test_r12_round_closure_leaves_zero_live_state(r02):
    run, _cfg2, _res = r02
    for ep in run.breach_episodes.values():
        assert ep.status in R.TERMINAL_EPISODE_STATUSES
        assert ep.live_activation_batch_id is None
        assert ep.closed_at is not None
    for batch in run.activation_batches.values():
        assert batch.status == "TERMINAL"
    for req in run.activation_requests.values():
        assert req.status in TERMINAL_REQUEST_STATUSES
    assert nonterminal_activation_request_count(run) == 0


def test_r18_stale_predictive_state_never_affects_next_round(r02):
    run, _cfg2, _res = r02
    terminal = run.round_terminal_times
    for ep in run.breach_episodes.values():
        assert ep.closed_at <= terminal[ep.RoundID] + 1e-9
    for batch in run.activation_batches.values():
        ep = run.breach_episodes[batch.BreachEpisodeID]
        assert batch.RoundID == ep.RoundID
        for q in batch.request_ids:
            req = run.activation_requests[q]
            assert req.RoundID == batch.RoundID           # nothing crosses a round boundary
            if req.completed_at is not None:
                assert req.completed_at <= terminal[req.RoundID] + 1e-9
    for pr in run.prediction_records:
        if pr.seated_batch_id is not None:
            assert run.activation_batches[pr.seated_batch_id].RoundID == pr.RoundID


# ------------------------------------------------------------------ R-TEST-13
def test_r13_target_and_difficulty_unchanged_in_every_mode():
    from Models.PoCol.stage2.search import target_for_difficulty     # noqa: PLC0415
    ref = target_for_difficulty(1000)
    for mode in R.CONTROLLER_MODES:
        cfg = _cfg(mode, leases=(mode == "HYSTERESIS_PREDICTIVE_REASSIGNMENT"))
        assert cfg.difficulty == 1000
        assert target_for_difficulty(cfg.difficulty) == ref
        assert cfg.nonce_domain_size == 1600              # domain semantics untouched


# ------------------------------------------------------------------ R-TEST-14 / 15 / 16
def test_r14_duplicate_nonce_count_zero(r02, r03):
    for run, cfg, res in (r02, r03):
        assert res["duplicate_nonce_count"] == 0


def test_r15_post_round_evaluation_counts_zero(r02, r03):
    for run, cfg, _res in (r02, r03):
        audit = post_round_audit(run)
        assert audit["post_round_evaluation_record_count"] == 0
        assert audit["post_round_evaluation_nonce_count"] == 0
        assert audit["evaluation_missing_terminal_time_count"] == 0


def test_r16_energy_identity_and_residency_reconcile(r02, r03):
    for run, cfg, res in (r02, r03):
        ident = residency_and_energy_identity(run, cfg)
        assert ident["maximum_energy_identity_residual_j"] <= 1e-8
        assert ident["maximum_residency_partition_residual_s"] <= 1e-9
        assert res["residency_reconciles"] is True


# ------------------------------------------------------------------ R-TEST-17
def test_r17_bounded_reassignment_no_overlap_no_rewind(r03):
    run, cfg, res = r03
    assert res["controller_suffix_reassignment_count"] >= 1
    assert res["physical_frontier_rewind_count"] == 0
    assert res["duplicate_nonce_count"] == 0
    assert run.lease_stats["overlapping_slice_count"] == 0
    assert res["nonterminal_lease_count"] == 0
    assert res["nonterminal_reassignment_request_count"] == 0
    # one immutable reassignment trigger per suffix lineage
    assert len(run.controller_reassigned_slices) == \
        res["controller_suffix_reassignment_count"]
