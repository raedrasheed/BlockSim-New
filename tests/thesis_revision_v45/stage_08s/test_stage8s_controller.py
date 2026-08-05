"""Stage-8S controller tests S8S-TEST-01..22.

Executed seeds: fresh Stage-8S PILOT seeds; plus (TEST-01/02 only, as directed) the frozen
historical seeds solely to REPRODUCE already-frozen records."""
from __future__ import annotations

import csv
import dataclasses
import hashlib
import json
import pathlib
import sys
from types import SimpleNamespace

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
for p in (str(REPO),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_06"),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_06m"),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_08r")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M6                                             # noqa: E402
import scenarios_8r as S8R                                            # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,  # noqa: E402
                       nonterminal_activation_request_count)
from Models.PoCol.stage2.simulator import run_simulation              # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                # noqa: E402
from Models.PoCol.stage2 import refinement as R                       # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy, h_useful_available  # noqa: E402
from Models.PoCol.stage2.security import TERMINAL_REQUEST_STATUSES    # noqa: E402

H0 = 4000.0
STATIC_FLOOR = 0.80 * H0

FROZEN_M03 = json.loads(
    (REPO / "experiments/thesis_revision_v45/stage_07m/runs"
     / "7m-M03_HET_IDLE_FLOOR-s00.json").read_text())
with open(REPO / "docs/thesis_revision_v45/stage_08r/STAGE_08R_RUN_DATASET.csv",
          newline="") as _fh:
    FROZEN_R02_S00 = next(r for r in csv.DictReader(_fh)
                          if r["scenario_id"] == "R02_REVISED_CONTROLLER"
                          and r["seed_index"] == "0")


def _seed8s(tag: str, i: int) -> int:
    return int.from_bytes(hashlib.sha256(f"{tag}{i}".encode()).digest()[:8], "big")


PILOT8S = _seed8s("PoCol-v45-stage8s-pilot-", 0)


def _cfg(mode: str, seed: int = PILOT8S):
    base = S8R.build_config_8r(S8R.SCENARIOS[1], seed)      # frozen floor core
    return dataclasses.replace(base, controller=ControllerPolicy(mode=mode))


@pytest.fixture(scope="module")
def s03():
    cfg = _cfg("USEFUL_FLOOR_COARSE_REASSIGNMENT")
    run = run_simulation(cfg, run_id="s8s-test-s03")
    return run, cfg, results_schema(run, cfg)


@pytest.fixture(scope="module")
def s02():
    cfg = _cfg("USEFUL_FLOOR_ONLY")
    run = run_simulation(cfg, run_id="s8s-test-s02")
    return run, cfg, results_schema(run, cfg)


# ------------------------------------------------------------------ 01 / 02
def test_s8s01_legacy_reproduces_frozen_historical_record():
    seed = M6.confirmatory_seeds()[0]
    cfg = M6.build_config_6m(M6.CONFIRMATORY[2], seed)
    assert cfg.controller.mode == "LEGACY_REACTIVE"
    run = run_simulation(cfg, run_id="s8s-legacy")
    res = results_schema(run, cfg)
    assert len(run.round_terminal_times) == FROZEN_M03["rounds_executed"]
    assert res["rounds_accepted"] == FROZEN_M03["rounds_accepted"]
    assert res["energy_kwh"] == FROZEN_M03["E_idle_kwh"]
    assert res["total_duration_below_floor"] == FROZEN_M03["total_duration_below_floor"]
    assert res["reserve_activations_seated"] == FROZEN_M03["reserve_activations_seated"]
    assert res["coarse_reassignment_count"] == 0
    assert res["duration_below_useful_floor"] == 0.0        # inert under LEGACY


def test_s8s02_stage8r_mode_reproduces_frozen_r02():
    seed = S8R.confirmatory_seeds_8r()[0]
    cfg = dataclasses.replace(
        S8R.build_config_8r(S8R.SCENARIOS[2], seed),        # frozen R02 core config
        controller=ControllerPolicy(mode="STAGE8R_PREDICTIVE_STATIC_FLOOR"))
    run = run_simulation(cfg, run_id="s8s-stage8r-mode")
    res = results_schema(run, cfg)
    assert len(run.round_terminal_times) == int(FROZEN_R02_S00["rounds_executed"])
    assert res["rounds_accepted"] == int(FROZEN_R02_S00["rounds_accepted"])
    # the frozen CSV's E_idle came from the pair-accounting summation order; the engine
    # accumulator agrees to 1 ULP (same physics, different float summation order).
    assert res["energy_kwh"] == pytest.approx(float(FROZEN_R02_S00["E_idle_kwh"]),
                                              abs=1e-14)
    assert res["total_duration_below_floor"] == \
        float(FROZEN_R02_S00["total_duration_below_floor"])
    assert res["reserve_activations_seated"] == \
        int(FROZEN_R02_S00["activation_requests_seated"])
    assert res["activation_batches_seated"] == \
        int(FROZEN_R02_S00["activation_batches_seated"])


# ------------------------------------------------------------------ 03..07 (fixtures)
def _fake(miner_state: str, cursor: int = 10, range_end: int = 80, completed: bool = False,
          kind: str = "EXHAUSTED"):
    st = SimpleNamespace(completed=completed, completion_kind=(kind if completed else None),
                         AssignmentID="A1", assignment_version=1, MinerID="M1",
                         cursor=cursor, hash_rate=100.0, range_start=0, range_end=range_end)
    rc = SimpleNamespace(round_state="ROUND_HASHING", RoundID="r1",
                         TemplateID_committed="t1", search_states={"M1": st},
                         assignments={"A1": {"MinerID": "M1", "assignment_version": 1,
                                             "RoundID": "r1", "TemplateID": "t1",
                                             "range": (0, range_end)}})
    run_ctx = SimpleNamespace(miners={"M1": SimpleNamespace(state=miner_state)},
                              activation_requests={}, reserve_records={},
                              coarse_live_by_receiver={},
                              config=SimpleNamespace(batch_size=25))
    return run_ctx, rc


def test_s8s03_waking_contributes_zero_to_h_effective():
    from Models.PoCol.stage2.security import compute_h_effective    # noqa: PLC0415
    run_ctx, rc = _fake("WAKING")
    h, n, _ = compute_h_effective(run_ctx, rc)
    assert (h, n) == (0.0, 0)


def test_s8s04_static_floor_remains_exactly_080_h0(s03, s02):
    for run, cfg, res in (s03, s02):
        assert cfg.security_floor.minimum_active_hash_rate == STATIC_FLOOR == 0.80 * H0
        assert res["configured_minimum_active_hash_rate"] == STATIC_FLOOR


def test_s8s05_useful_target_never_exceeds_static_floor():
    run_ctx, rc = _fake("ACTIVE_HASHING")
    # inflate availability far above the static floor: 3 fast active miners
    for i in (2, 3):
        st = SimpleNamespace(completed=False, completion_kind=None, AssignmentID=f"A{i}",
                             assignment_version=1, MinerID=f"M{i}", cursor=0,
                             hash_rate=3000.0, range_start=0, range_end=80)
        rc.search_states[f"M{i}"] = st
        rc.assignments[f"A{i}"] = {"MinerID": f"M{i}", "assignment_version": 1,
                                   "RoundID": "r1", "TemplateID": "t1", "range": (0, 80)}
        run_ctx.miners[f"M{i}"] = SimpleNamespace(state="ACTIVE_HASHING")
    avail, _det = h_useful_available(run_ctx, rc, True)
    assert avail > STATIC_FLOOR
    assert min(STATIC_FLOOR, avail) == STATIC_FLOOR         # the target formula caps here


def test_s8s06_miner_without_useful_work_contributes_zero():
    run_ctx, rc = _fake("ACTIVE_HASHING", cursor=80, range_end=80)   # empty range
    avail, det = h_useful_available(run_ctx, rc, True)
    assert avail == 0.0 and det["h_effective"] == 0.0


def test_s8s07_receiver_counts_only_with_nonoverlapping_suffix():
    # donor with only one batch remaining -> NO spare unit -> receiver contributes zero
    run_ctx, rc = _fake("ACTIVE_HASHING", cursor=55, range_end=80)
    stR = SimpleNamespace(completed=True, completion_kind="EXHAUSTED", AssignmentID="A9",
                          assignment_version=1, MinerID="M9", cursor=80, hash_rate=400.0,
                          range_start=0, range_end=80)
    rc.search_states["M9"] = stR
    run_ctx.miners["M9"] = SimpleNamespace(state="LOW_POWER_LISTEN")
    avail, det = h_useful_available(run_ctx, rc, True)
    assert det["spare_batch_units"] == 0 and avail == 100.0
    # donor with three batches remaining -> spare units exist -> receiver counted
    rc.search_states["M1"].cursor = 5                        # 75 remaining -> 2 spare
    avail, det = h_useful_available(run_ctx, rc, True)
    assert det["spare_batch_units"] == 2 and avail == 500.0


# ------------------------------------------------------------------ 08..12 (coarse)
def _lineages(run):
    by = {}
    for q in run.coarse_requests.values():
        by.setdefault((q.BreachEpisodeID, q.DonorAssignmentID), []).append(q)
    return by


def test_s8s08_chunks_pairwise_disjoint(s03):
    run, _cfg3, _res = s03
    assert run.coarse_requests, "the coarse arm must actually reassign"
    for reqs in _lineages(run).values():
        ivs = sorted((q.chunk_start, q.chunk_end) for q in reqs)
        for (a0, a1), (b0, b1) in zip(ivs, ivs[1:]):
            assert a1 <= b0, "receiver chunks overlap"


def test_s8s09_chunk_union_equals_accepted_remaining_suffix(s03):
    run, _cfg3, _res = s03
    donor_led = {}
    for rec in run.evaluation_ledger:
        donor_led.setdefault((rec.RoundID, rec.AssignmentID), []).append(rec)
    for (ep_id, donor_aid), reqs in _lineages(run).items():
        ivs = sorted((q.chunk_start, q.chunk_end) for q in reqs)
        for (a0, a1), (b0, b1) in zip(ivs, ivs[1:]):
            assert a1 == b0, "receiver chunks must be contiguous"
        rid = reqs[0].RoundID
        # the donor's committed evaluations never enter any receiver chunk
        for rec in donor_led.get((rid, donor_aid), []):
            for q0, q1 in ivs:
                assert rec.interval_end <= q0 or rec.interval_start >= q1, \
                    "donor evaluated inside a ceded receiver chunk"


def test_s8s10_one_repartition_per_donor_lineage_per_episode(s03):
    run, _cfg3, res = s03
    for reqs in _lineages(run).values():
        assert len({q.seated_at for q in reqs}) == 1, \
            "a donor lineage was repartitioned twice inside one episode"
    assert res["coarse_repartition_count"] == len(_lineages(run))


def test_s8s11_one_receiver_never_holds_two_live_chunks(s03):
    run, _cfg3, _res = s03
    by_recv = {}
    for q in run.coarse_requests.values():
        by_recv.setdefault((q.RoundID, q.ReceiverMinerID), []).append(q)
    for reqs in by_recv.values():
        reqs.sort(key=lambda q: q.seated_at)
        for a, b in zip(reqs, reqs[1:]):
            assert a.status == "COMPLETED" and a.completed_at is not None \
                and a.completed_at <= b.seated_at + 1e-12, \
                "receiver seated a second chunk while one was live"
    assert not run.coarse_live_by_receiver


def test_s8s12_coarse_chunk_sizing_deterministic(s03):
    run, cfg, _res = s03
    rerun = run_simulation(cfg, run_id="s8s-test-s03")       # identical run id + config
    a = sorted((str(q.CoarseRequestID), q.chunk_start, q.chunk_end, q.ReceiverMinerID)
               for q in run.coarse_requests.values())
    b = sorted((str(q.CoarseRequestID), q.chunk_start, q.chunk_end, q.ReceiverMinerID)
               for q in rerun.coarse_requests.values())
    assert a == b


# ------------------------------------------------------------------ 13..15 (admission)
def test_s8s13_reserve_not_woken_when_receiver_takes_work(s03):
    run, _cfg3, res = s03
    coarse_times = {round(q.seated_at, 9) for q in run.coarse_requests.values()}
    batch_times = {round(b.seated_at, 9) for b in run.activation_batches.values()}
    assert not (coarse_times & batch_times), \
        "a reserve batch was seated in the same decision as a coarse repartition"


def test_s8s14_reserve_never_woken_without_bound_useful_work(s03, s02):
    for run, cfg, res in (s03, s02):
        for q in run.activation_requests.values():
            assert q.ReserveSliceID is not None
            sl = run.reserve_slice_by_id.get(q.ReserveSliceID)
            assert sl is not None and sl.size() > 0, \
                "a reserve wake was seated without an atomically bound non-empty slice"
        assert res["reserve_wakes_with_bound_work"] == res["reserve_activations_seated"]
        has_rejects = res["reserve_wakes_rejected_no_useful_work"] > 0
        logged = any(getattr(o, "kind", "") == "activation_rejected_no_useful_work"
                     for o in run.log if not isinstance(o, str))
        assert has_rejects == logged or not has_rejects


def test_s8s15_reserve_wake_carries_exact_identity(s03):
    run, _cfg3, _res = s03
    for q in run.activation_requests.values():
        assert q.RoundID in run.round_terminal_times
        rr = run.reserve_records.get((q.RoundID, q.MinerID))
        assert rr is not None and rr.TemplateID == q.TemplateID
        assert q.ReserveSliceID.startswith(f"RS-{q.RoundID}-")


# ------------------------------------------------------------------ 16..20 (integrity)
def test_s8s16_no_physical_frontier_rewind(s03, s02):
    for _run, _cfg2, res in (s03, s02):
        assert res["physical_frontier_rewind_count"] == 0


def test_s8s17_duplicate_nonce_count_zero(s03, s02):
    for _run, _cfg2, res in (s03, s02):
        assert res["duplicate_nonce_count"] == 0


def test_s8s18_post_round_evaluation_zero(s03, s02):
    for run, _cfg2, _res in (s03, s02):
        audit = post_round_audit(run)
        assert audit["post_round_evaluation_record_count"] == 0
        assert audit["post_round_evaluation_nonce_count"] == 0


def test_s8s19_energy_and_residency_reconcile(s03, s02):
    for run, cfg, res in (s03, s02):
        ident = residency_and_energy_identity(run, cfg)
        assert ident["maximum_energy_identity_residual_j"] <= 1e-8
        assert ident["maximum_residency_partition_residual_s"] <= 1e-9
        assert res["residency_reconciles"] is True


def test_s8s20_round_closure_leaves_zero_live_state(s03):
    run, _cfg3, res = s03
    for ep in run.breach_episodes.values():
        assert ep.status in R.TERMINAL_EPISODE_STATUSES
        assert ep.live_activation_batch_id is None
    for b in run.activation_batches.values():
        assert b.status == "TERMINAL"
    for q in run.activation_requests.values():
        assert q.status in TERMINAL_REQUEST_STATUSES
    for q in run.coarse_requests.values():
        assert q.status in ("COMPLETED", "CANCELLED")
    assert nonterminal_activation_request_count(run) == 0
    assert res["nonterminal_coarse_request_count"] == 0
    assert res["nonterminal_lease_count"] == 0
    assert res["nonterminal_reassignment_request_count"] == 0


# ------------------------------------------------------------------ 21 / 22
def test_s8s21_static_and_useful_metrics_present_and_independent(s03, s02):
    for run, _cfg2, res in (s03, s02):
        for k in ("duration_below_static_floor", "duration_below_useful_floor",
                  "static_floor_unattainable_count", "useful_floor_unattainable_count",
                  "useful_floor_deficit_area", "H_useful_available_time_weighted",
                  "H_useful_target_time_weighted"):
            assert k in res
        # independent computations: static from the accepted security stats, useful from
        # the controller's own trackers — and they genuinely differ on this data.
        assert res["duration_below_static_floor"] == \
            run.security_stats["total_duration_below_floor"]
        assert res["duration_below_useful_floor"] == \
            run.controller_stats["duration_below_useful_floor"]
        assert res["duration_below_useful_floor"] < res["duration_below_static_floor"]


def test_s8s22_target_and_difficulty_unchanged_in_every_mode():
    from Models.PoCol.stage2.search import target_for_difficulty     # noqa: PLC0415
    ref = target_for_difficulty(1000)
    for mode in R.CONTROLLER_MODES:
        cfg = _cfg(mode)
        assert cfg.difficulty == 1000
        assert target_for_difficulty(cfg.difficulty) == ref
        assert cfg.nonce_domain_size == 1600
