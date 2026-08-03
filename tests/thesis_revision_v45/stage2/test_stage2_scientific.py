"""Stage-2B scientific tests SCI-1 .. SCI-10 (executable-ledger based) plus the S2B-1
target-coupling tests.

These verify the corrected scientific core against the ACTUAL simulator execution ledger:
target-coupled success, an explicit finite domain that admits zero / one / many solutions
and full-domain exhaustion, disjoint per-miner ranges, real per-nonce evaluations recorded
in the ledger, causal accounting (no evaluation after round end; searched == ledger count),
and the constructed matched CONTROL-vs-POCOL_IDLE energy identity.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict

from Models.PoCol.stage2 import (Stage2Config, run_simulation, make_template, sha256_int,
                                  target_for_difficulty, success_probability,
                                  run_energy_experiment, a1_continuous_control_kwh,
                                  A1_BASELINE_KWH, SUCCESS_MODEL, Template)

_TOL = 1e-9


def _template_with_target(header: bytes, difficulty: int, D: int) -> Template:
    """A template with a GIVEN fixed header and the target for ``difficulty`` (so the
    superset/monotone tests vary ONLY the target, holding the header fixed)."""
    return Template(TemplateID="t", RoundID="t", header_bytes=header, difficulty=difficulty,
                    nonce_domain_size=D, target=target_for_difficulty(difficulty))


def _confirmatory_run():
    """A deterministic multi-round run with a mix of accepted and no-block rounds."""
    cfg = Stage2Config(num_miners=8, horizon_T=150.0, reserve_fraction=0.25,
                       nonce_domain_size=1200, difficulty=1000, batch_size=25)
    return run_simulation(cfg), cfg


def _ledger_counts_by_round_miner(run):
    d = defaultdict(int)
    for rec in run.evaluation_ledger:
        d[(rec.RoundID, rec.MinerID)] += rec.count()
    return d


# ---------------------------------------------------------------- SCI-1
def test_sci1_simulator_ranges_disjoint_and_cover_domain():
    """Actual simulator assignment ranges are disjoint and cover the active domain exactly."""
    run, cfg = _confirmatory_run()
    assert run.round_ranges
    for rid, ranges in run.round_ranges.items():
        covered = []
        for (s, e) in ranges.values():
            covered.extend(range(s, e))
        assert sorted(covered) == list(range(cfg.nonce_domain_size))   # exact cover
        intervals = sorted(ranges.values())
        for (s1, e1), (s2, e2) in zip(intervals, intervals[1:]):
            assert e1 <= s2                                            # pairwise disjoint


# ---------------------------------------------------------------- SCI-2
def test_sci2_ledger_zero_duplicate_template_nonce():
    """The actual evaluation ledger has zero duplicate (TemplateID, nonce) entries."""
    run, _ = _confirmatory_run()
    assert run.evaluation_ledger                                       # non-trivial
    seen = set()
    dup = 0
    for rec in run.evaluation_ledger:
        for nonce in rec.nonces():
            key = (rec.TemplateID, nonce)
            if key in seen:
                dup += 1
            seen.add(key)
    assert dup == 0


# ---------------------------------------------------------------- SCI-3
def test_sci3_every_active_miner_worked_or_justified_zero():
    """Every active miner committed work, or its zero-work is justified (round ended first)."""
    run, _ = _confirmatory_run()
    counts = _ledger_counts_by_round_miner(run)
    for rid, participants in run.round_participants.items():
        for mid in participants:
            committed = counts.get((rid, mid), 0)
            if committed > 0:
                continue
            # justified zero-work: the round ended no later than this miner's first completion.
            fc = run.round_first_completion.get((rid, mid))
            rtt = run.round_terminal_times.get(rid)
            assert fc is not None and rtt is not None
            assert rtt <= fc + _TOL, (rid, mid, rtt, fc)


# ---------------------------------------------------------------- SCI-4
def test_sci4_no_ledger_completion_after_round_end():
    """No ledger completion_time exceeds its round's terminal time (causal accounting)."""
    run, _ = _confirmatory_run()
    for rec in run.evaluation_ledger:
        rtt = run.round_terminal_times.get(rec.RoundID)
        assert rtt is not None
        assert rec.completion_time <= rtt + _TOL, (rec.RoundID, rec.completion_time, rtt)


# ---------------------------------------------------------------- SCI-5
def test_sci5_searched_count_equals_ledger_count():
    """Each miner's final searched_count equals its committed ledger count."""
    run, _ = _confirmatory_run()
    counts = _ledger_counts_by_round_miner(run)
    assert run.final_searched
    for (rid, mid), searched in run.final_searched.items():
        assert counts.get((rid, mid), 0) == searched, (rid, mid, searched)


# ---------------------------------------------------------------- SCI-6
def test_sci6_fixed_target_hash_validation_exact():
    """Fixed-target hash validation accepts EXACTLY digest <= target (nothing else)."""
    tpl = make_template("sci6", difficulty=500, nonce_domain_size=2000, seed=11)
    for nonce in range(2000):
        expected = sha256_int(tpl.header_bytes, nonce) <= tpl.target
        assert tpl.is_solution(nonce) is expected
    assert tpl.target == target_for_difficulty(500)          # coupled to difficulty


# ---------------------------------------------------------------- SCI-7
def test_sci7_zero_solution_template_full_domain_exhaustion():
    """A deterministic no-solution template reaches full-domain exhaustion (no block)."""
    cfg = Stage2Config(num_miners=6, horizon_T=50.0, reserve_fraction=0.0,
                       nonce_domain_size=600, difficulty=(1 << 300), batch_size=25)
    assert target_for_difficulty(cfg.difficulty) == 0        # deterministically unsatisfiable
    run = run_simulation(cfg)
    kinds = [o.kind for o in run.log]
    assert "accepted_block" not in kinds                     # no block ever
    r1 = [rec for rec in run.evaluation_ledger if rec.RoundID == "round-1"]
    covered = []
    for rec in r1:
        assert rec.contained_solution is False
        covered.extend(rec.nonces())
    assert sorted(covered) == list(range(cfg.nonce_domain_size))   # entire domain, once
    assert run.residency_reconciles(run.run_end_time)


# ---------------------------------------------------------------- SCI-8
def test_sci8_matched_control_and_idle_same_template_target_winner_end():
    """CONTROL and POCOL_IDLE share template, target, evaluations, winner and round end."""
    a = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8)
    b = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8)
    assert a.success_model == SUCCESS_MODEL == "TARGET_COUPLED_SHA256_DIGEST_LEQ_TARGET"
    assert a.target == b.target                               # same fixed target
    assert a.winner == b.winner and a.winning_nonce == b.winning_nonce
    assert a.round_end == b.round_end                         # same round end
    span = a.round_end - a.round_start
    for r in a.rows:
        assert abs(r.t_active_control - span) < 1e-12
        assert abs((r.t_active_idle + r.t_idle_idle) - span) < 1e-12
    wrow = next(r for r in a.rows if r.MinerID == a.winner)
    assert wrow.completion_kind == "SOLUTION"
    assert abs(wrow.completion_time - a.round_end) < 1e-12
    # the recorded winner is a genuine target-coupled solution.
    header = hashlib.sha256(f"energy2b|2400|{a.difficulty}|{a.seed}".encode()).digest()
    assert sha256_int(header, a.winning_nonce) <= a.target


# ---------------------------------------------------------------- SCI-9
def test_sci9_pidle_equals_pactive_zero_saving():
    """With P_idle == P_active the constructed idle scenario yields exactly zero saving."""
    res = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8,
                                P_idle=Stage2Config().P_hash)
    assert res.P_idle == res.P_active
    assert res.saving_j == 0.0
    assert all(r.delta_e_j == 0.0 for r in res.rows)
    good = run_energy_experiment(Stage2Config(nonce_domain_size=2400), n_miners=8)
    assert good.saving_j > 0.0                                # a real idle saving exists
    assert good.max_abs_residual_j < 1e-6                     # identity holds


# ---------------------------------------------------------------- SCI-10
def test_sci10_canonical_a1_baseline():
    """The canonical A1 configuration reproduces 8.420833333 kWh."""
    cfg = Stage2Config()
    assert cfg.num_miners == 141 and cfg.P_hash == 21.5 and cfg.horizon_T == 10_000.0
    kwh = a1_continuous_control_kwh(cfg)
    assert abs(kwh - 8.420833333) < 1e-9
    assert abs(kwh - A1_BASELINE_KWH) < 1e-9


# ============================================================ S2B-1 target coupling
def _solutions(header, target, D):
    return {n for n in range(D) if sha256_int(header, n) <= target}


def test_s2b1_easier_target_is_superset():
    """An easier (larger) target yields a SUPERSET of the harder target's solutions."""
    D = 3000
    header = hashlib.sha256(b"s2b1-superset").digest()       # SAME header, only target varies
    hard = _template_with_target(header, difficulty=2000, D=D)   # small target
    easy = _template_with_target(header, difficulty=200, D=D)    # large target
    assert easy.target > hard.target
    s_hard = _solutions(header, hard.target, D)
    s_easy = _solutions(header, easy.target, D)
    assert s_hard <= s_easy                                  # superset
    assert success_probability(easy.target) > success_probability(hard.target)


def test_s2b1_difficulty_changes_success_distribution():
    """Higher difficulty strictly reduces the number of in-domain solutions (same header)."""
    D = 4000
    header = hashlib.sha256(b"s2b1-distribution").digest()   # SAME header, only target varies
    counts = []
    for diff in (100, 500, 2000):
        tpl = _template_with_target(header, difficulty=diff, D=D)
        counts.append(len(_solutions(header, tpl.target, D)))
    assert counts[0] > counts[1] > counts[2]                 # monotone: harder -> fewer


def test_s2b1_target_is_used_not_stored_and_ignored():
    """Success genuinely depends on the target: a solution at an easy target is NOT one at 0."""
    D = 2000
    easy = make_template("u", difficulty=50, nonce_domain_size=D, seed=3)
    sols = _solutions(easy.header_bytes, easy.target, D)
    assert sols                                              # easy target admits solutions
    zero = make_template("u", difficulty=(1 << 300), nonce_domain_size=D, seed=3)
    assert zero.target == 0
    assert all(not zero.is_solution(n) for n in sols)        # target used, not ignored


def test_s2b1_zero_and_multi_solution_outcomes_exist():
    """The finite domain genuinely admits both zero-solution and multi-solution rounds."""
    D = 1500
    zero = make_template("z", difficulty=(1 << 300), nonce_domain_size=D, seed=1)
    assert len(_solutions(zero.header_bytes, zero.target, D)) == 0
    multi = make_template("m", difficulty=100, nonce_domain_size=D, seed=1)
    assert len(_solutions(multi.header_bytes, multi.target, D)) >= 2
