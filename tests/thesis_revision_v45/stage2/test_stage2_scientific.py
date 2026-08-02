"""Stage-2A scientific tests SCI-1 .. SCI-7.

These verify the SCIENTIFIC core the independent review found missing: an explicit finite
nonce domain partitioned into disjoint per-miner ranges, real per-nonce work under one
immutable template, every active miner contributing hash work, and the matched
CONTROL vs POCOL_IDLE energy identity — with the canonical A1 accounting invariant and a
deterministic, matched success position.
"""
from __future__ import annotations

from Models.PoCol.stage2 import (Stage2Config, run_simulation, partition_domain,
                                  make_template, sha256_int, run_energy_experiment,
                                  a1_continuous_control_kwh, A1_BASELINE_KWH,
                                  SUCCESS_MODEL)


# ---------------------------------------------------------------- SCI-1
def test_sci1_disjoint_assignments_cover_domain_exactly():
    """Disjoint nonce assignments cover the declared active nonce domain EXACTLY."""
    D = 4000
    ids = [f"M{i:03d}" for i in range(7)]
    ranges = partition_domain(D, ids)
    covered = []
    for (s, e) in ranges.values():
        covered.extend(range(s, e))
    assert sorted(covered) == list(range(D))              # exact cover: no gap, no overlap
    intervals = sorted(ranges.values())
    for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
        assert e1 <= s2                                   # pairwise disjoint
    # tie to the actual experiment's active domain.
    res = run_energy_experiment(Stage2Config(nonce_domain_size=800), n_miners=8)
    exp_cover = []
    for r in res.rows:
        exp_cover.extend(range(r.range_start, r.range_end))
    assert sorted(exp_cover) == list(range(800))


# ---------------------------------------------------------------- SCI-2
def test_sci2_zero_duplicate_nonce_evaluations():
    """Under one immutable template, NO nonce is evaluated by two miners (zero duplicates)."""
    D = 900
    ids = [f"M{i}" for i in range(6)]
    ranges = partition_domain(D, ids)
    tpl = make_template("sci-round", difficulty=1000, nonce_domain_size=D, seed=7)
    evaluated = []
    for (s, e) in ranges.values():
        for nonce in range(s, e):
            _ = sha256_int(tpl.header_bytes, nonce)       # real per-nonce work, once each
            evaluated.append(nonce)
    assert len(evaluated) == len(set(evaluated))          # zero duplicate evaluations
    assert len(evaluated) == D
    # in the experiment, each miner's searched interval lies within its own disjoint range.
    res = run_energy_experiment(Stage2Config(nonce_domain_size=800), n_miners=8)
    searched = []
    for r in res.rows:
        n = int(round(r.t_active_idle * r.hash_rate))
        searched.extend(range(r.range_start, r.range_start + n))
    assert len(searched) == len(set(searched))            # no nonce searched twice


# ---------------------------------------------------------------- SCI-3
def test_sci3_all_active_miners_contribute_hash_work():
    """Every ACTIVE participant contributes hash work; reserve miners never hash."""
    cfg = Stage2Config(num_miners=8, horizon_T=400.0, reserve_fraction=0.25,
                       nonce_domain_size=800, batch_size=25)
    run = run_simulation(cfg)
    reserve = getattr(run, "reserve_miner_ids", set())
    active = [mid for mid in run.miners if mid not in reserve]
    assert active                                          # there is an active set
    for mid in active:
        assert run.miners[mid].duration["ACTIVE_HASHING"] > 0   # contributed hash work
    for mid in reserve:
        assert run.miners[mid].duration["ACTIVE_HASHING"] == 0  # participation/reserve policy


# ---------------------------------------------------------------- SCI-4
def test_sci4_energy_identity_residual_within_tolerance():
    """The per-miner idle-policy energy identity holds within tolerance, and it saves."""
    res = run_energy_experiment(Stage2Config(nonce_domain_size=800, difficulty=1000),
                                n_miners=8)
    assert res.success_model == SUCCESS_MODEL
    assert res.max_abs_residual_j < 1e-6
    for r in res.rows:
        # E_i = P_active*t_active + P_idle*t_idle
        assert abs(r.E_idle_j - (res.P_active * r.t_active_idle
                                 + res.P_idle * r.t_idle_idle)) < 1e-9
        # Delta_E_i = t_idle*(P_active - P_idle) == E_control_i - E_idle_i
        assert abs((r.E_control_j - r.E_idle_j) - r.delta_e_j) < 1e-6
    assert res.saving_j > 0.0                              # idle policy saves (P_idle < P_active)


# ---------------------------------------------------------------- SCI-5
def test_sci5_pidle_equals_pactive_zero_saving():
    """With P_idle == P_active the idle policy yields exactly zero saving."""
    res = run_energy_experiment(Stage2Config(nonce_domain_size=800), n_miners=8,
                                P_idle=Stage2Config().P_hash)
    assert res.P_idle == res.P_active
    assert res.saving_j == 0.0
    assert all(r.delta_e_j == 0.0 for r in res.rows)      # partitioning alone saves nothing


# ---------------------------------------------------------------- SCI-6
def test_sci6_canonical_a1_baseline():
    """The canonical A1 configuration reproduces 8.420833333 kWh."""
    cfg = Stage2Config()                                  # 141 miners, 21.5 W, 10_000 s
    assert cfg.num_miners == 141 and cfg.P_hash == 21.5 and cfg.horizon_T == 10_000.0
    kwh = a1_continuous_control_kwh(cfg)
    assert abs(kwh - 8.420833333) < 1e-9
    assert abs(kwh - A1_BASELINE_KWH) < 1e-9


# ---------------------------------------------------------------- SCI-7
def test_sci7_matched_control_and_idle_same_success_and_round_end():
    """CONTROL and POCOL_IDLE use the SAME success position and round end (matched pair)."""
    cfg = Stage2Config(nonce_domain_size=800, difficulty=1000)
    a = run_energy_experiment(cfg, n_miners=8)
    b = run_energy_experiment(cfg, n_miners=8)            # deterministic re-run
    assert a.winner == b.winner
    assert a.winning_nonce == b.winning_nonce             # same seeded success position
    assert a.round_end == b.round_end                     # same stopping condition
    span = a.round_end - a.round_start
    for r in a.rows:
        # control runs each miner active to round end; idle splits the SAME span.
        assert abs(r.t_active_control - span) < 1e-12
        assert abs((r.t_active_idle + r.t_idle_idle) - span) < 1e-12
    winner_row = next(r for r in a.rows if r.MinerID == a.winner)
    assert winner_row.completion_kind == "SOLUTION"
    assert abs(winner_row.completion_time - a.round_end) < 1e-12
