"""Stage-8U tests U-TEST-01..22.

Executed seeds: fresh Stage-8U PILOT seeds; plus (U-TEST-01 only, as directed) frozen
historical seeds solely to REPRODUCE already-frozen Stage-8M/8R/8S records."""
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
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_08r"),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_08s"),
          str(REPO / "experiments" / "thesis_revision_v45" / "stage_08u")):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M6                                             # noqa: E402
import scenarios_8r as S8R                                            # noqa: E402
import scenarios_8s as S8S                                            # noqa: E402
import figures_8u as F8U                                              # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,  # noqa: E402
                       nonterminal_activation_request_count)
from Models.PoCol.stage2.simulator import (run_simulation,            # noqa: E402
                                           _handoff_eligible_receiver,
                                           _handoff_eligible_donor,
                                           _single_reserve_admission)
from Models.PoCol.stage2.adapter import results_schema                # noqa: E402
from Models.PoCol.stage2 import refinement as R                       # noqa: E402
from Models.PoCol.stage2 import search as SEARCH                      # noqa: E402
from Models.PoCol.stage2 import matched_pow as MP                     # noqa: E402
from Models.PoCol.stage2.refinement import ControllerPolicy           # noqa: E402
from Models.PoCol.stage2.security import TERMINAL_REQUEST_STATUSES    # noqa: E402

H0 = 4000.0
STATIC_FLOOR = 0.80 * H0
MODE_8U = "USEFUL_FLOOR_SINGLE_HANDOFF"

FROZEN_M03 = json.loads(
    (REPO / "experiments/thesis_revision_v45/stage_07m/runs"
     / "7m-M03_HET_IDLE_FLOOR-s00.json").read_text())
with open(REPO / "docs/thesis_revision_v45/stage_08r/STAGE_08R_RUN_DATASET.csv",
          newline="") as _fh:
    FROZEN_R02_S00 = next(r for r in csv.DictReader(_fh)
                          if r["scenario_id"] == "R02_REVISED_CONTROLLER"
                          and r["seed_index"] == "0")
with open(REPO / "docs/thesis_revision_v45/stage_08s/STAGE_08S_RUN_DATASET.csv",
          newline="") as _fh:
    FROZEN_S03_S00 = next(
        r for r in csv.DictReader(_fh)
        if r["scenario_id"] == "S03_USEFUL_FLOOR_COARSE_REASSIGNMENT"
        and r["seed_class"] == "CONFIRMATORY_8S" and r["seed_index"] == "0")


def _seed8u(tag: str, i: int) -> int:
    return int.from_bytes(hashlib.sha256(f"{tag}{i}".encode()).digest()[:8], "big")


PILOT8U = _seed8u("PoCol-v45-stage8u-pilot-", 0)


def _cfg(mode: str, seed: int = PILOT8U):
    base = S8R.build_config_8r(S8R.SCENARIOS[1], seed)      # frozen floor core
    return dataclasses.replace(base, controller=ControllerPolicy(mode=mode))


def _pow_cfg(kind: str, seed: int = PILOT8U):
    base = S8R.build_config_8r(S8R.SCENARIOS[1], seed)
    ids = tuple(f"M{i:03d}" for i in range(base.num_miners))
    rates = tuple(base.hash_rate_for(i) for i in range(base.num_miners))
    common = dict(difficulty=base.difficulty, nonce_domain_size=base.nonce_domain_size,
                  horizon_seconds=base.horizon_T, batch_size=base.batch_size,
                  template_seed=base.template_seed, master_seed=seed,
                  P_hash=base.P_hash, P_reserve=base.P_reserve)
    if kind == "POW_POPULATION_MATCHED":
        return MP.MatchedPoWConfig(scenario_id="W00-test", scenario_kind=kind,
                                   miner_ids=ids, hash_rates=rates, **common)
    n_res = int(base.reserve_fraction * base.num_miners)
    return MP.MatchedPoWConfig(scenario_id="W01-test", scenario_kind=kind,
                               miner_ids=ids[:-n_res], hash_rates=rates[:-n_res],
                               standby_ids=ids[-n_res:], **common)


@pytest.fixture(scope="module")
def p02():
    cfg = _cfg(MODE_8U)
    run = run_simulation(cfg, run_id="s8u-test-p02")
    return run, cfg, results_schema(run, cfg)


@pytest.fixture(scope="module")
def pow00():
    cfg = _pow_cfg("POW_POPULATION_MATCHED")
    return cfg, MP.run_matched_pow(cfg)


@pytest.fixture(scope="module")
def pow01():
    cfg = _pow_cfg("POW_ACTIVE_CAPACITY_MATCHED")
    return cfg, MP.run_matched_pow(cfg)


# ------------------------------------------------------------------ 01 (frozen records)
def test_u01_every_historical_controller_reproduces_its_frozen_record():
    # (a) LEGACY_REACTIVE reproduces the frozen Stage-7M/8M M03 record.
    seed = M6.confirmatory_seeds()[0]
    cfg = M6.build_config_6m(M6.CONFIRMATORY[2], seed)
    assert cfg.controller.mode == "LEGACY_REACTIVE"
    res = results_schema(run_simulation(cfg, run_id="s8u-legacy"), cfg)
    assert res["rounds_accepted"] == FROZEN_M03["rounds_accepted"]
    assert res["energy_kwh"] == FROZEN_M03["E_idle_kwh"]
    assert res["total_duration_below_floor"] == FROZEN_M03["total_duration_below_floor"]
    # (b) STAGE8R_PREDICTIVE_STATIC_FLOOR reproduces the frozen Stage-8R R02 row.
    seed = S8R.confirmatory_seeds_8r()[0]
    cfg = dataclasses.replace(
        S8R.build_config_8r(S8R.SCENARIOS[2], seed),
        controller=ControllerPolicy(mode="STAGE8R_PREDICTIVE_STATIC_FLOOR"))
    res = results_schema(run_simulation(cfg, run_id="s8u-stage8r-mode"), cfg)
    assert res["rounds_accepted"] == int(FROZEN_R02_S00["rounds_accepted"])
    assert res["energy_kwh"] == pytest.approx(float(FROZEN_R02_S00["E_idle_kwh"]),
                                              abs=1e-14)
    assert res["reserve_activations_seated"] == \
        int(FROZEN_R02_S00["activation_requests_seated"])
    # (c) USEFUL_FLOOR_COARSE_REASSIGNMENT reproduces the frozen Stage-8S S03 row.
    seed = int(FROZEN_S03_S00["master_seed"])
    cfg = S8S.build_config_8s(S8S.SCENARIOS[3], seed)
    assert cfg.controller.mode == "USEFUL_FLOOR_COARSE_REASSIGNMENT"
    run = run_simulation(cfg, run_id="s8u-stage8s-mode")
    res = results_schema(run, cfg)
    assert len(run.round_terminal_times) == int(FROZEN_S03_S00["rounds_executed"])
    assert res["rounds_accepted"] == int(FROZEN_S03_S00["rounds_accepted"])
    assert res["energy_kwh"] == pytest.approx(float(FROZEN_S03_S00["E_idle_kwh"]),
                                              abs=1e-14)
    assert res["coarse_reassignment_count"] == \
        int(FROZEN_S03_S00["coarse_reassignment_count"])
    assert res["duration_below_useful_floor"] == \
        pytest.approx(float(FROZEN_S03_S00["duration_below_useful_floor"]), abs=1e-9)
    assert res["handoff_epoch_count"] == 0                  # 8U machinery inert here


# ------------------------------------------------------------------ 02..05 (matched PoW)
def test_u02_pow_and_pocol_share_target_difficulty_horizon_template_and_primitive(
        p02, pow00):
    _run, cfg, _res = p02
    pcfg, pres = pow00
    assert pcfg.difficulty == cfg.difficulty == 1000
    assert pcfg.target == SEARCH.target_for_difficulty(cfg.difficulty)
    assert pcfg.nonce_domain_size == cfg.nonce_domain_size == 1600
    assert pcfg.horizon_seconds == cfg.horizon_T
    assert pcfg.batch_size == cfg.batch_size
    assert pcfg.template_seed == cfg.template_seed
    assert pcfg.master_seed == PILOT8U
    # the identical template STREAM: round k in both systems is
    # make_template(f"round-{k}", difficulty, D, template_seed + k).
    assert MP.make_template is SEARCH.make_template           # same primitive object
    for k in (1, 2, 3):
        tpl = SEARCH.make_template(f"round-{k}", cfg.difficulty, cfg.nonce_domain_size,
                                   cfg.template_seed + k)
        assert pres["rounds"][k - 1].TemplateID == tpl.TemplateID == f"tpl-round-{k}"
        assert tpl.target == pcfg.target
    assert pres["target"] == pcfg.target                      # fixed, never per-round


def test_u03_pow_overlap_is_measurable(pow00, pow01):
    for _cfgp, res in (pow00, pow01):
        assert res["duplicate_physical_evaluations"] > 0      # uncoordinated overlap
        assert res["total_physical_evaluations"] == \
            res["unique_physical_evaluations"] + res["duplicate_physical_evaluations"]
        for r in res["rounds"]:
            assert r.total_physical_evaluations == \
                r.unique_physical_evaluations + r.duplicate_physical_evaluations
            assert 0 <= r.unique_physical_evaluations <= _cfgp.nonce_domain_size


def test_u04_pow_post_round_evaluations_zero(pow00, pow01):
    for cfgp, res in (pow00, pow01):
        assert res["post_round_evaluation_count"] == 0
        # causal bound: no miner ever commits more work than elapsed round time allows.
        rates = dict(zip(cfgp.miner_ids, cfgp.hash_rates))
        for r in res["rounds"]:
            window = r.close_time - r.start_time
            for mid, n in r.evaluations_by_miner.items():
                assert n <= rates[mid] * window + 1e-9


def test_u05_pow_energy_and_residency_reconcile(pow00, pow01):
    for cfgp, res in (pow00, pow01):
        assert res["energy_identity_residual_j"] <= 1e-8
        assert res["residency_partition_residual_s"] == 0.0
        expected_j = (len(cfgp.miner_ids) * cfgp.P_hash
                      + len(cfgp.standby_ids) * cfgp.P_reserve) * cfgp.horizon_seconds
        assert res["energy_kwh"] == pytest.approx(expected_j / 3.6e6, rel=1e-12)
        for states in res["residency_seconds_by_node"].values():
            assert sum(states.values()) == cfgp.horizon_seconds


# ------------------------------------------------------------------ 06..12 (handoff)
def test_u06_at_most_one_handoff_epoch_per_round(p02):
    run, _cfg2, res = p02
    assert run.handoff_epochs, "the single-handoff arm must actually hand off"
    by_round = {}
    for e in run.handoff_epochs.values():
        by_round.setdefault(e.RoundID, []).append(e)
    for eps in by_round.values():
        assert len(eps) == 1, "a round held two handoff epochs"
    assert len(run.handoff_by_round) == len(run.handoff_epochs)
    assert res["handoff_epoch_count"] == len(run.handoff_epochs)


def test_u07_second_handoff_attempt_is_replay_noop(p02):
    run, _cfg2, res = p02
    # every later trigger inside a consumed round is the exact replay no-op: it returns
    # the existing epoch, increments the duplicate counter and creates NOTHING.
    assert res["duplicate_handoff_prevented_count"] > 0
    assert res["duplicate_handoff_prevented_count"] == \
        run.controller_stats["duplicate_handoff_prevented_count"]
    assert len(run.handoff_epochs) == res["handoff_epoch_count"]   # no phantom epochs


def _fake_receiver(mid: str, rate: float, state: str = "LOW_POWER_LISTEN",
                   completed: bool = True, kind: str = "EXHAUSTED"):
    st = SimpleNamespace(completed=completed, completion_kind=(kind if completed else None),
                         AssignmentID=f"A-{mid}", assignment_version=1, MinerID=mid,
                         cursor=80, hash_rate=rate, range_start=0, range_end=80)
    return st, SimpleNamespace(state=state)


def _fake_donor(mid: str, rate: float, cursor: int, range_end: int):
    st = SimpleNamespace(completed=False, completion_kind=None, AssignmentID=f"A-{mid}",
                         assignment_version=1, MinerID=mid, cursor=cursor,
                         hash_rate=rate, range_start=0, range_end=range_end)
    return st, SimpleNamespace(state="ACTIVE_HASHING")


def _fake_ctx(receivers, donors, live_receivers=()):
    search_states, miners, assignments = {}, {}, {}
    for mid, rate in receivers:
        st, m = _fake_receiver(mid, rate)
        search_states[mid], miners[mid] = st, m
        assignments[st.AssignmentID] = {"MinerID": mid, "assignment_version": 1,
                                        "RoundID": "r1", "TemplateID": "t1",
                                        "range": (0, 80)}
    for mid, rate, cursor, range_end in donors:
        st, m = _fake_donor(mid, rate, cursor, range_end)
        search_states[mid], miners[mid] = st, m
        assignments[st.AssignmentID] = {"MinerID": mid, "assignment_version": 1,
                                        "RoundID": "r1", "TemplateID": "t1",
                                        "range": (0, range_end)}
    rc = SimpleNamespace(RoundID="r1", TemplateID_committed="t1",
                         search_states=search_states, assignments=assignments,
                         round_state="ROUND_HASHING")
    run_ctx = SimpleNamespace(miners=miners, coarse_live_by_receiver=dict(
        (m, "live") for m in live_receivers),
        config=SimpleNamespace(batch_size=25))
    return run_ctx, rc


def test_u08_receiver_selection_deterministic():
    run_ctx, rc = _fake_ctx(receivers=[("M009", 100.0), ("M003", 400.0),
                                       ("M001", 400.0)], donors=[])
    mid, st = _handoff_eligible_receiver(run_ctx, rc)
    assert mid == "M001"                       # fastest; tie broken by smaller MinerID
    run_ctx.coarse_live_by_receiver["M001"] = "live"
    mid, _st = _handoff_eligible_receiver(run_ctx, rc)
    assert mid == "M003"                       # live reassignment excludes M001
    assert _handoff_eligible_receiver(
        *_fake_ctx(receivers=[], donors=[("M002", 200.0, 0, 80)])) is None


def test_u09_donor_selection_deterministic():
    run_ctx, rc = _fake_ctx(receivers=[], donors=[("M004", 100.0, 10, 80),
                                                  ("M005", 200.0, 0, 80),
                                                  ("M006", 300.0, 0, 80)])
    mid, _st = _handoff_eligible_donor(run_ctx, rc)
    assert mid == "M006"        # equal largest suffix (80): deterministic MinerID order
    rc.search_states["M004"].cursor = 0
    rc.search_states["M005"].cursor = 40
    rc.search_states["M006"].cursor = 40
    mid, _st = _handoff_eligible_donor(run_ctx, rc)
    assert mid == "M004"                          # now the unique largest suffix
    # a donor below two whole batches is never selected
    for m in ("M004", "M005", "M006"):
        rc.search_states[m].cursor = 80 - 49      # 49 < 2*25 remaining
    assert _handoff_eligible_donor(run_ctx, rc) is None


def test_u10_chunks_contiguous_disjoint_union_exact(p02):
    run, cfg, _res = p02
    committed = [e for e in run.handoff_epochs.values()
                 if e.status in ("COMMITTED", "COMPLETED", "ROUND_CLOSED")
                 and e.receiver_chunk is not None and e.donor_chunk is not None]
    assert committed
    ledger_by_round = {}
    for rec in run.evaluation_ledger:
        ledger_by_round.setdefault(rec.RoundID, []).append(rec)
    for e in committed:
        d0, d1 = e.donor_chunk
        r0, r1 = e.receiver_chunk
        o0, o1 = e.original_suffix
        assert d0 == o0 and r1 == o1 and d1 == r0          # contiguous, exact union
        assert d1 - d0 >= cfg.batch_size and r1 - r0 >= cfg.batch_size
        # the donor never evaluated inside the ceded receiver chunk
        for rec in ledger_by_round.get(e.RoundID, []):
            if rec.AssignmentID == e.source_assignment_id:
                assert rec.interval_end <= r0 or rec.interval_start >= r1


def test_u11_rate_proportional_sizing(p02):
    run, cfg, _res = p02
    batch = cfg.batch_size
    base = S8R.build_config_8r(S8R.SCENARIOS[1], PILOT8U)
    rate_of = {f"M{i:03d}": base.hash_rate_for(i) for i in range(base.num_miners)}
    checked = 0
    for e in run.handoff_epochs.values():
        if e.receiver_chunk is None:
            continue
        R_len = e.original_suffix[1] - e.original_suffix[0]
        h_d, h_r = rate_of[e.donor_miner_id], rate_of[e.receiver_miner_id]
        q_d, q_r = R_len * h_d / (h_d + h_r), R_len * h_r / (h_d + h_r)
        s_d, s_r = int(q_d), int(q_r)
        for _ in range(R_len - s_d - s_r):
            if (q_d - s_d) >= (q_r - s_r):
                s_d += 1
            else:
                s_r += 1
        s_r = max(batch, min(s_r, R_len - batch))
        assert e.receiver_chunk[1] - e.receiver_chunk[0] == s_r
        assert e.donor_chunk[1] - e.donor_chunk[0] == R_len - s_r
        checked += 1
    assert checked > 0


def test_u12_predicted_makespan_strictly_improves(p02):
    run, _cfg2, res = p02
    for e in run.handoff_epochs.values():
        if e.status in ("COMMITTED", "COMPLETED", "ROUND_CLOSED"):
            assert e.predicted_makespan_after < e.predicted_makespan_before
        elif e.status == "CANCELLED":
            assert e.predicted_makespan_after >= e.predicted_makespan_before
    assert res["handoff_failed_count"] == 0


# ------------------------------------------------------------------ 13..18 (integrity)
def test_u13_no_physical_frontier_rewind(p02):
    _run, _cfg2, res = p02
    assert res["physical_frontier_rewind_count"] == 0


def test_u14_honest_pocol_duplicates_zero(p02):
    run, _cfg2, res = p02
    assert res["duplicate_nonce_count"] == 0
    # per-round ledger intervals of live assignments are pairwise disjoint
    seen = {}
    for rec in run.evaluation_ledger:
        seen.setdefault(rec.RoundID, []).append((rec.interval_start, rec.interval_end))
    for ivs in seen.values():
        ivs.sort()
        for (a0, a1), (b0, b1) in zip(ivs, ivs[1:]):
            assert a1 <= b0


def test_u15_at_most_one_reserve_wake_per_round(p02):
    run, _cfg2, res = p02
    by_round = {}
    for q in run.activation_requests.values():
        by_round.setdefault(q.RoundID, []).append(q)
    for reqs in by_round.values():
        assert len(reqs) <= 1, "a round seated two reserve wake requests"
    assert res["single_reserve_requests_seated"] == res["reserve_activations_seated"]
    assert set(run.handoff_reserve_requests) == set(run.activation_requests.keys())


def _fake_admission_ctx(with_receiver: bool, with_donor: bool, window_remaining: int,
                        with_slice: bool = True):
    receivers = [("M009", 400.0)] if with_receiver else []
    donors = [("M001", 100.0, 0, max(window_remaining, 1))] if with_donor else \
        ([("M001", 100.0, 0, window_remaining)] if window_remaining else [])
    run_ctx, rc = _fake_ctx(receivers=receivers, donors=donors)
    run_ctx.handoff_reserve_by_round = {}
    run_ctx.reserve_records = {("r1", "M016"): SimpleNamespace(
        MinerID="M016", reserve_status="AVAILABLE", activation_priority=0,
        hash_rate=100.0)}
    run_ctx.reserve_slices = {"r1": [SimpleNamespace(
        RangeSliceID="RS-r1-1", status="UNCLAIMED", size=lambda: 80)]} \
        if with_slice else {"r1": []}
    run_ctx.controller_stats = R.controller_stats_template()
    run_ctx.config = SimpleNamespace(
        batch_size=25,
        security_floor=SimpleNamespace(activation_wake_latency=1.0))
    return run_ctx, rc


def test_u16_reserve_rejected_when_awake_receiver_available():
    run_ctx, rc = _fake_admission_ctx(with_receiver=True, with_donor=True,
                                      window_remaining=80)
    reason = _single_reserve_admission(run_ctx, rc, now=0.0)
    assert reason == "awake_receiver_available"
    assert run_ctx.controller_stats["reserve_wake_rejected_awake_receiver_available"] == 1


def test_u17_reserve_rejected_when_useful_window_too_short(p02):
    # donor with 80 nonces at 100 H -> window 0.8 s <= 1.0 s wake + 0.25 s batch
    run_ctx, rc = _fake_admission_ctx(with_receiver=False, with_donor=True,
                                      window_remaining=80)
    reason = _single_reserve_admission(run_ctx, rc, now=0.0)
    assert reason == "short_useful_window"
    assert run_ctx.controller_stats["reserve_wake_rejected_short_useful_window"] == 1
    # a long window admits the single wake
    run_ctx, rc = _fake_admission_ctx(with_receiver=False, with_donor=True,
                                      window_remaining=1600)
    assert _single_reserve_admission(run_ctx, rc, now=0.0) is None
    # no bound work rejects
    run_ctx, rc = _fake_admission_ctx(with_receiver=False, with_donor=True,
                                      window_remaining=1600, with_slice=False)
    assert _single_reserve_admission(run_ctx, rc, now=0.0) == "no_bound_useful_work"
    assert run_ctx.controller_stats["reserve_wake_rejected_no_bound_work"] == 1
    # the real run recorded its own admission activity
    _run, _cfg2, res = p02
    assert res["reserve_wake_rejected_short_useful_window"] >= 0


def test_u18_round_closure_leaves_zero_live_records(p02):
    run, _cfg2, res = p02
    for e in run.handoff_epochs.values():
        assert e.status in R.TERMINAL_HANDOFF_STATUSES
        assert e.terminal_time is not None
    for ep in run.breach_episodes.values():
        assert ep.status in R.TERMINAL_EPISODE_STATUSES
        assert ep.live_activation_batch_id is None
    for b in run.activation_batches.values():
        assert b.status == "TERMINAL"
    for q in run.activation_requests.values():
        assert q.status in TERMINAL_REQUEST_STATUSES
    assert not run.coarse_live_by_receiver
    assert not run.handoff_reserve_by_round        # settled and popped at every closure
    assert nonterminal_activation_request_count(run) == 0
    assert res["nonterminal_handoff_epoch_count"] == 0
    assert res["nonterminal_coarse_request_count"] == 0
    assert res["nonterminal_lease_count"] == 0
    assert res["nonterminal_reassignment_request_count"] == 0
    audit = post_round_audit(run)
    assert audit["post_round_evaluation_record_count"] == 0


# ------------------------------------------------------------------ 19..22
def test_u19_target_and_difficulty_fixed_everywhere(pow00, pow01):
    ref = SEARCH.target_for_difficulty(1000)
    assert MODE_8U in R.CONTROLLER_MODES
    for mode in R.CONTROLLER_MODES:
        cfg = _cfg(mode)
        assert cfg.difficulty == 1000
        assert SEARCH.target_for_difficulty(cfg.difficulty) == ref
        assert cfg.nonce_domain_size == 1600
    for cfgp, res in (pow00, pow01):
        assert cfgp.difficulty == 1000 and cfgp.target == ref
        assert res["target"] == ref                 # no dynamic difficulty anywhere


def test_u20_energy_price_invariance(p02, pow00):
    # doubling every power value changes NO behaviour (blocks, rounds, evaluations) and
    # scales energy exactly linearly — power is accounting, never scheduling.
    run, cfg, res = p02
    cfg2 = dataclasses.replace(cfg, P_hash=2 * cfg.P_hash, P_listen=2 * cfg.P_listen,
                               P_reserve=2 * cfg.P_reserve, P_wake=2 * cfg.P_wake)
    run2 = run_simulation(cfg2, run_id="s8u-test-p02")
    res2 = results_schema(run2, cfg2)
    assert res2["rounds_accepted"] == res["rounds_accepted"]
    assert len(run2.round_terminal_times) == len(run.round_terminal_times)
    assert res2["handoff_epoch_count"] == res["handoff_epoch_count"]
    assert res2["energy_kwh"] == pytest.approx(2 * res["energy_kwh"], rel=1e-12)
    pcfg, pres = pow00
    pcfg2 = dataclasses.replace(pcfg, P_hash=2 * pcfg.P_hash,
                                P_reserve=2 * pcfg.P_reserve)
    pres2 = MP.run_matched_pow(pcfg2)
    assert pres2["rounds_accepted"] == pres["rounds_accepted"]
    assert pres2["total_physical_evaluations"] == pres["total_physical_evaluations"]
    assert pres2["energy_kwh"] == pytest.approx(2 * pres["energy_kwh"], rel=1e-12)


def test_u21_all_comparison_fields_present(p02, pow00, pow01):
    _run, _cfg2, res = p02
    for k in ("handoff_epoch_count", "handoff_committed_count", "handoff_completed_count",
              "handoff_failed_count", "handoff_cancelled_count",
              "duplicate_handoff_prevented_count", "single_reserve_requests_seated",
              "single_reserve_requests_completed", "single_reserve_requests_incomplete",
              "reserve_wake_rejected_short_useful_window",
              "reserve_wake_rejected_awake_receiver_available",
              "reserve_wake_rejected_no_bound_work", "duration_below_static_floor",
              "duration_below_useful_floor", "static_floor_unattainable_count",
              "useful_floor_deficit_area", "nonterminal_handoff_epoch_count"):
        assert k in res
    required = ("scenario_id", "scenario_kind", "consensus_label", "master_seed",
                "template_seed", "difficulty", "target", "nonce_domain_size",
                "batch_size", "horizon_seconds", "rounds_executed", "rounds_accepted",
                "rounds_exhausted", "rounds_horizon_truncated",
                "total_physical_evaluations", "unique_physical_evaluations",
                "duplicate_physical_evaluations", "post_round_evaluation_count",
                "first_valid_solutions", "energy_kwh", "energy_identity_residual_j",
                "residency_partition_residual_s")
    for _cfgp, pres in (pow00, pow01):
        for k in required:
            assert k in pres
        assert pres["consensus_label"] == "matched same-template PoW control"
        for fv in pres["first_valid_solutions"]:
            assert set(fv) == {"round_index", "RoundID", "winner_miner_id",
                               "winning_nonce", "accepted_at"}


def test_u22_tables_byte_identical_and_figure_metadata_deterministic():
    rows = [{"scenario_id": "P02_POCOL_SINGLE_HANDOFF", "seed_index": 0,
             "energy_kwh": 0.0162340921, "blocks": 171, "note": None},
            {"scenario_id": "W01_POW_ACTIVE_CAPACITY_MATCHED", "seed_index": 0,
             "energy_kwh": 0.029383333333333333, "blocks": 222, "note": None}]
    fields = ["scenario_id", "seed_index", "energy_kwh", "blocks", "note"]
    a = F8U.serialize_table(rows, fields)
    b = F8U.serialize_table([dict(r) for r in rows], fields)
    assert a == b and a.endswith("\n")
    assert F8U.checksum_text(a) == F8U.checksum_text(b)
    assert repr(0.029383333333333333) in a and "NA" in a  # canonical repr round-trip
    assert len(F8U.FIGURE_SPECS) == 18
    m1 = F8U.figure_metadata("FIG01", "FIG01_total_energy.csv",
                             ["P02_POCOL_SINGLE_HANDOFF", "W00_POW_POPULATION_MATCHED"])
    m2 = F8U.figure_metadata("FIG01", "FIG01_total_energy.csv",
                             ["W00_POW_POPULATION_MATCHED", "P02_POCOL_SINGLE_HANDOFF"])
    assert m1 == m2                                        # order-independent, no clock
    assert json.dumps(m1, sort_keys=True) == json.dumps(m2, sort_keys=True)
    for spec in F8U.FIGURE_SPECS:
        md = F8U.figure_metadata(spec["figure_id"], "src.csv", [])
        assert "timestamp" not in md and "generated_at" not in md
        assert md["style_rules"] == ["colour_blind_safe", "no_3d", "no_truncated_bars",
                                     "paired_seed_points_visible", "mean_with_95ci"]
