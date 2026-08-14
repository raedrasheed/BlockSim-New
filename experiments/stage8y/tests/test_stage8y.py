"""Stage 8Y validation suite (brief section 36).

    python -m pytest experiments/stage8y/tests -q
"""

from __future__ import annotations

import itertools
import json
import math
import os
import random

import pytest

from experiments.stage8y.config import difficulty as diffmod
from experiments.stage8y.config import hardware as hw
from experiments.stage8y.config import policies as pol
from experiments.stage8y.config import seeds as seedmod
from experiments.stage8y.config import stage8y_config as C
from experiments.stage8y.src import energy as em
from experiments.stage8y.src import metrics as mx
from experiments.stage8y.src import powerstate as ps
from experiments.stage8y.src.engine import simulate

PILOT_SEED = seedmod.pilot_seeds()[0]


def _cfg(protocol, comp="H2", n=100, seed=PILOT_SEED, k=1, **kw):
    extra = {} if protocol in (C.POW, C.POW_CT) else C._conf_pocol(protocol)
    extra.update(kw)
    return C.RunConfig(protocol=protocol, composition=comp, n_miners=n, seed=seed,
                       seed_index=k, phase="pilot", **extra)


# ==========================================================================
# 1. Registry, heterogeneous hash rate and power
# ==========================================================================
def test_registry_loads_and_is_self_consistent():
    reg = hw.registry_raw()
    assert reg["registry_version"] == 1
    for d in reg["devices"]:
        derived = d["active_power_W"] / d["hashrate_THs"]
        assert d["efficiency_J_per_TH_derived"] == pytest.approx(derived, rel=1e-12)
        assert d["low_power_W_documented"] is None      # never invented
        assert d["source_url"].startswith("https://")
        assert d["manufacturer_certified"] in (
            "verified_quote", "url_located_content_not_retrievable")


def test_device_efficiency_spread_is_real():
    effs = sorted(d.efficiency_j_per_th for d in hw.DEVICES.values())
    assert effs[0] == pytest.approx(15.0)
    assert effs[-1] == pytest.approx(29.5)
    assert effs[-1] / effs[0] > 1.9


@pytest.mark.parametrize("comp", list(C.ALL_COMPOSITIONS))
@pytest.mark.parametrize("n", [100, 300, 500])
def test_heterogeneous_aggregates(comp, n):
    pop = hw.build_population(comp, n)
    assert pop.n_miners == n
    assert sum(pop.counts.values()) == n
    assert pop.total_hashrate_hps == pytest.approx(
        sum(m.hashrate_hps for m in pop.miners))
    assert pop.total_power_w == pytest.approx(sum(m.active_power_w for m in pop.miners))
    assert pop.network_efficiency_j_per_th == pytest.approx(
        pop.total_power_w / pop.total_hashrate_ths)


def test_aggregate_hashrate_is_not_held_constant():
    """H_N must grow with N and differ across compositions."""
    base = hw.build_population("H2", 100).total_hashrate_hps
    assert hw.build_population("H2", 300).total_hashrate_hps == pytest.approx(3 * base)
    assert hw.build_population("H2", 500).total_hashrate_hps == pytest.approx(5 * base)
    per_comp = {c: hw.build_population(c, 300).total_hashrate_hps
                for c in C.ALL_COMPOSITIONS}
    assert len(set(round(v) for v in per_comp.values())) == len(per_comp)


def test_population_is_deterministic_and_identical_for_all_protocols():
    a = hw.build_population("H4", 300)
    b = hw.build_population("H4", 300)
    assert [(m.id, m.device_key, m.hashrate_hps) for m in a.miners] == \
           [(m.id, m.device_key, m.hashrate_hps) for m in b.miners]
    for proto in (C.POW,) + C.POCOL_PROTOCOLS:
        pop = _cfg(proto, comp="H4", n=300).population
        assert pop.counts == a.counts
        assert pop.total_hashrate_hps == a.total_hashrate_hps
        assert pop.total_power_w == a.total_power_w


# ==========================================================================
# 2. Difficulty: one per configuration, never PoCol-specific
# ==========================================================================
@pytest.mark.parametrize("comp", list(C.PRIMARY_COMPOSITIONS))
@pytest.mark.parametrize("n", list(C.PRIMARY_NETWORK_SIZES))
def test_matched_difficulty_across_all_protocols(comp, n):
    specs = [_cfg(p, comp=comp, n=n).spec for p in (C.POW,) + C.POCOL_PROTOCOLS]
    assert len({s.difficulty for s in specs}) == 1
    assert len({s.target_int for s in specs}) == 1
    assert len({s.q_per_candidate for s in specs}) == 1
    assert len({s.nonce_domain for s in specs}) == 1


def test_no_pocol_specific_difficulty_recalibration_in_source():
    """The difficulty path must not branch on protocol anywhere."""
    src = open("experiments/stage8y/config/difficulty.py", encoding="utf-8").read()
    for token in ("POCOL", "P3_ENERGY", "P4_RESERVE", "protocol"):
        assert token not in src


def test_difficulty_is_derived_from_full_installed_hardware():
    for comp in C.ALL_COMPOSITIONS:
        for n in C.ALL_NETWORK_SIZES:
            pop = hw.build_population(comp, n)
            s = diffmod.derive(comp, n)
            assert s.difficulty == pytest.approx(
                pop.total_hashrate_hps * 600.0 / 2 ** 32)
            assert 1.0 / (pop.total_hashrate_hps * s.q_per_candidate) == pytest.approx(600.0)
            assert s.target_int / (2 ** 256) == pytest.approx(s.q_per_candidate, rel=1e-9)


def test_difficulty_does_not_depend_on_active_fraction():
    a = _cfg(C.P3_ENERGY, target_hash_fraction=0.30).spec
    b = _cfg(C.P3_ENERGY, target_hash_fraction=0.90).spec
    c = _cfg(C.POW).spec
    assert a.difficulty == b.difficulty == c.difficulty
    assert a.nonce_domain == b.nonce_domain == c.nonce_domain


# ==========================================================================
# 3. Nonce-domain integrity and range allocation
# ==========================================================================
@pytest.mark.parametrize("alloc", [pol.ALLOC_EQUAL, pol.ALLOC_HASH])
@pytest.mark.parametrize("comp", ["H0", "H2", "H4"])
def test_slots_are_disjoint_and_tile_the_domain(alloc, comp):
    pop = hw.build_population(comp, 300)
    spec = diffmod.derive(comp, 300)
    lengths = diffmod.slot_lengths(pop, spec, alloc)
    bounds = diffmod.slot_bounds(lengths)
    assert sum(lengths) == spec.nonce_domain
    assert bounds[0][0] == 0 and bounds[-1][1] == spec.nonce_domain
    for i in range(len(bounds) - 1):
        assert bounds[i][1] == bounds[i + 1][0]
    rng = random.Random(0)
    for _ in range(300):
        i, j = rng.randrange(300), rng.randrange(300)
        if i != j:
            a, b = bounds[i], bounds[j]
            assert max(a[0], b[0]) >= min(a[1], b[1])       # empty intersection


def test_hash_proportional_slots_equalise_completion_time():
    pop = hw.build_population("H4", 300)
    spec = diffmod.derive("H4", 300)
    lengths = diffmod.slot_lengths(pop, spec, pol.ALLOC_HASH)
    times = [L / m.hashrate_hps for L, m in zip(lengths, pop.miners)]
    assert max(times) == pytest.approx(min(times), rel=1e-6)
    assert times[0] == pytest.approx(C.EPOCH_SWEEP_S, rel=1e-6)


def test_equal_slots_make_fast_miners_finish_first():
    pop = hw.build_population("H2", 300)
    spec = diffmod.derive("H2", 300)
    lengths = diffmod.slot_lengths(pop, spec, pol.ALLOC_EQUAL)
    times = {}
    for L, m in zip(lengths, pop.miners):
        times.setdefault(m.device_key, L / m.hashrate_hps)
    assert times["S21PRO"] < times["S19JPRO"]


def test_domain_is_not_reduced_by_parking_miners():
    """The work requirement must not shrink when fewer miners are active."""
    full = _cfg(C.P0_ALL).spec.nonce_domain
    for frac in (0.3, 0.5, 0.8):
        assert _cfg(C.P3_ENERGY, target_hash_fraction=frac).spec.nonce_domain == full


# ==========================================================================
# 4. Active-set selection
# ==========================================================================
@pytest.mark.parametrize("rule", list(pol.SELECTION_RULES))
def test_selection_meets_the_hash_floor(rule):
    pop = hw.build_population("H4", 300)
    for frac in (0.4, 0.6, 0.8):
        ids = pol.select_active(pop, rule, target_hash_fraction=frac,
                                rng=random.Random(1))
        f = pol.active_fractions(pop, ids)
        assert f["r_hash"] >= frac - 1e-9


@pytest.mark.parametrize("comp", ["H1", "H2", "H3", "H4"])
@pytest.mark.parametrize("frac", [0.4, 0.6, 0.8])
def test_S4_is_exactly_optimal(comp, frac):
    """Verify the optimiser against exhaustive enumeration over device classes."""
    pop = hw.build_population(comp, 200)
    ids = pol.select_active(pop, pol.S4_OPTIMIZE, target_hash_fraction=frac)
    got = pol.active_fractions(pop, ids)["P_active_W"]
    classes = pol._sorted_classes(pop)
    need = frac * pop.total_hashrate_hps
    best = None
    for combo in itertools.product(*[range(len(c[3]) + 1) for c in classes]):
        h = sum(n * c[1] for n, c in zip(combo, classes))
        if h + 1e-6 < need:
            continue
        p = sum(n * c[2] for n, c in zip(combo, classes))
        if best is None or p < best:
            best = p
    assert got == pytest.approx(best)


def test_selection_is_deterministic_with_stable_tie_break():
    pop = hw.build_population("H4", 300)
    for rule in pol.SELECTION_RULES:
        a = pol.select_active(pop, rule, target_hash_fraction=0.6,
                              rng=random.Random(7))
        b = pol.select_active(pop, rule, target_hash_fraction=0.6,
                              rng=random.Random(7))
        assert a == b == sorted(a)


def test_efficiency_first_picks_the_efficient_devices_first():
    pop = hw.build_population("H4", 300)
    ids = set(pol.select_active(pop, pol.S3_EFF_FIRST, target_hash_fraction=0.30))
    picked = {m.device_key for m in pop.miners if m.id in ids}
    assert picked == {"S21PRO"}


def test_count_fraction_is_not_hash_or_power_fraction():
    """r != r_H != r_P in a heterogeneous network (brief section 15)."""
    pop = hw.build_population("H4", 300)
    ids = pol.select_active(pop, pol.S4_OPTIMIZE, target_count_fraction=0.50)
    f = pol.active_fractions(pop, ids)
    assert f["r_count"] == pytest.approx(0.50, abs=0.01)
    assert abs(f["r_hash"] - f["r_count"]) > 0.02
    assert abs(f["r_power"] - f["r_count"]) > 0.01
    assert abs(f["r_hash"] - f["r_power"]) > 0.02
    # in the homogeneous control the three coincide
    pop0 = hw.build_population("H0", 300)
    f0 = pol.active_fractions(pop0, pol.select_active(
        pop0, pol.S4_OPTIMIZE, target_count_fraction=0.50))
    assert f0["r_hash"] == pytest.approx(f0["r_count"])
    assert f0["r_power"] == pytest.approx(f0["r_count"])


def test_reserve_stage_sets_are_nested_and_monotone_in_hash():
    pop = hw.build_population("H4", 300)
    sets = pol.reserve_stage_sets(pop, pol.S4_OPTIMIZE, C.CONF_RESERVE_SCHEDULE)
    prev, prev_h = set(), -1.0
    for s in sets:
        cur = set(s)
        assert prev <= cur                       # reserves are only ever added
        h = pol.active_fractions(pop, s)["r_hash"]
        assert h >= prev_h
        prev, prev_h = cur, h
    assert pol.active_fractions(pop, sets[-1])["r_hash"] == pytest.approx(1.0)


# ==========================================================================
# 5. Power states, residence and energy accounting
# ==========================================================================
def test_ledger_four_state_conservation_synthetic():
    led = ps.PowerStateLedger([1.0, 2.0], [10.0, 20.0], 100.0,
                              [ps.ACTIVE, ps.STANDBY])
    led.transition(0, ps.LOW_POWER, 20.0)
    led.transition(0, ps.ACTIVE, 50.0)
    led.transition(1, ps.WAKING, 30.0)
    led.transition(1, ps.ACTIVE, 40.0)
    led.close()
    assert sum(led.t[0].values()) == pytest.approx(100.0)
    assert sum(led.t[1].values()) == pytest.approx(100.0)
    assert led.t[0][ps.LOW_POWER] == pytest.approx(30.0)
    assert led.t[1][ps.STANDBY] == pytest.approx(30.0)
    assert led.t[1][ps.WAKING] == pytest.approx(10.0)
    assert led.t[1][ps.ACTIVE] == pytest.approx(60.0)
    assert led.conservation_error() == pytest.approx(0.0, abs=1e-9)
    assert led.min_residence() >= 0.0


def test_energy_formula_matches_state_times():
    for alpha in (0.0, 0.05, 0.10, 0.25, 0.50):
        r = em.account(pw_active_Ws=3510.0 * 100, pw_waking_Ws=3510.0 * 10,
                       pw_low_Ws=3510.0 * 50, pw_standby_Ws=3510.0 * 40,
                       alpha=alpha)
        assert r.total_J == pytest.approx(
            3510.0 * 100 + 3510.0 * 10 + alpha * 3510.0 * (50 + 40))
        assert r.total_kWh == pytest.approx(r.total_J / 3.6e6)


def test_pow_energy_reference_is_full_active():
    cfg = _cfg(C.POW, comp="H4", n=300)
    r = simulate(cfg)
    p = r.power_state
    assert p["t_low_miner_s"] == 0.0 and p["t_standby_miner_s"] == 0.0
    assert p["t_waking_miner_s"] == 0.0
    assert p["t_active_miner_s"] == pytest.approx(300 * cfg.horizon_s)
    e = em.account(p["pw_active_Ws"], p["pw_waking_Ws"], p["pw_low_Ws"],
                   p["pw_standby_Ws"], 0.0)
    assert e.total_J == pytest.approx(em.full_active_energy_J(r.P_N_W, r.horizon_s))


@pytest.mark.parametrize("protocol", [C.POW, C.P0_ALL, C.P1_EQUAL, C.P2_HASHPROP,
                                      C.P3_ENERGY, C.P4_RESERVE, C.POW_CT])
@pytest.mark.parametrize("comp", ["H0", "H4"])
def test_state_time_conservation_in_real_runs(protocol, comp):
    r = simulate(_cfg(protocol, comp=comp, n=100))
    p = r.power_state
    assert p["state_time_conservation_error_s"] < 1e-6
    assert p["min_state_residence_s"] >= 0.0
    total = (p["t_active_miner_s"] + p["t_low_miner_s"]
             + p["t_standby_miner_s"] + p["t_waking_miner_s"])
    assert total == pytest.approx(r.n_miners * r.horizon_s, rel=1e-12)


def test_power_identity_holds_exactly():
    """P_N * T = pw_active + pw_waking + pw_low + pw_standby."""
    for proto in (C.P0_ALL, C.P3_ENERGY, C.P4_RESERVE):
        r = simulate(_cfg(proto, comp="H4", n=200))
        p = r.power_state
        assert (p["pw_active_Ws"] + p["pw_waking_Ws"] + p["pw_low_Ws"]
                + p["pw_standby_Ws"]) == pytest.approx(r.P_N_W * r.horizon_s, rel=1e-12)


# ==========================================================================
# 6. Physical work: no hashing in forbidden states, no double counting
# ==========================================================================
@pytest.mark.parametrize("protocol", [C.POW, C.P0_ALL, C.P1_EQUAL, C.P2_HASHPROP,
                                      C.P3_ENERGY, C.P4_RESERVE, C.POW_CT])
def test_work_equals_integral_of_active_hashrate(protocol):
    """W = int H_active(t) dt. Proves no hashing while parked or waking, and no
    double-counted evaluation."""
    r = simulate(_cfg(protocol, comp="H4", n=200))
    assert r.work_accounting_error < 1e-9
    assert r.total_evaluations == pytest.approx(
        r.power_state["integral_H_active_hashes"], rel=1e-9)


def test_no_hash_work_attributed_to_parked_capacity():
    """A run with a 40% active set must do ~40% of the hashing of the all-active run."""
    a = simulate(_cfg(C.P0_ALL, comp="H2", n=200))
    b = simulate(_cfg(C.P3_ENERGY, comp="H2", n=200, target_hash_fraction=0.40))
    assert b.total_evaluations < 0.5 * a.total_evaluations


def test_duplicate_identity_and_pocol_zero_duplicates():
    for proto in (C.POW, C.P0_ALL, C.P1_EQUAL, C.P2_HASHPROP, C.P3_ENERGY,
                  C.P4_RESERVE):
        r = simulate(_cfg(proto, comp="H2", n=100))
        assert r.total_evaluations == r.unique_evaluations + r.duplicate_evaluations
        assert r.duplicate_evaluations == 0          # disjoint slots / distinct templates


def test_nonce_value_reuse_is_not_exact_duplication():
    r = simulate(_cfg(C.POW, comp="H2", n=100))
    assert r.duplicate_evaluations == 0
    assert r.nonce_value_reuse_ratio > 0.999999
    ct = simulate(_cfg(C.POW_CT, comp="H2", n=100))
    assert ct.duplicate_evaluations > 0              # shared template => real duplicates


def test_completed_ranges_are_not_rescanned():
    """Total evaluations must never exceed the domain times the number of epochs
    a miner could have been assigned."""
    r = simulate(_cfg(C.P2_HASHPROP, comp="H4", n=100))
    per_template = r.total_evaluations / max(1, r.n_templates)
    assert per_template <= r.nonce_domain + 1


# ==========================================================================
# 7. Reserve activation and wake transitions
# ==========================================================================
def test_reserve_activation_produces_wake_transitions():
    r = simulate(_cfg(C.P4_RESERVE, comp="H2", n=200, wake_s=10.0))
    p = r.power_state
    assert r.reserve_activations > 0
    assert p["wake_events"] > 0
    assert p["t_waking_miner_s"] > 0
    assert p.get("trans_STANDBY->WAKING", 0) + p.get("trans_LOW_POWER->WAKING", 0) > 0
    assert p.get("trans_WAKING->ACTIVE", 0) > 0


def test_zero_wake_delay_produces_no_waking_residence():
    r = simulate(_cfg(C.P4_RESERVE, comp="H2", n=200, wake_s=0.0))
    assert r.power_state["t_waking_miner_s"] == pytest.approx(0.0)
    assert r.reserve_activations > 0


def test_wake_delay_costs_energy_and_is_conservative():
    """Longer wake delay must not reduce drawn power: waking draws full power."""
    lo = simulate(_cfg(C.P4_RESERVE, comp="H2", n=200, wake_s=0.0))
    hi = simulate(_cfg(C.P4_RESERVE, comp="H2", n=200, wake_s=30.0))
    assert hi.power_state["integral_P_waking_Ws"] > lo.power_state["integral_P_waking_Ws"]
    assert C.WAKE_POWER_RATIO == 1.0


def test_reserve_activation_raises_active_capacity_above_stage_zero():
    """Reserve activation must actually add capacity at some point in the run.

    Note this is a statement about the *peak*, not the mean: a miner that completes
    its slot parks in LOW_POWER, so the time-average active capacity of P4 can and
    does fall below its stage-0 target. That is legitimate post-range parking, not a
    violation, and it is reported rather than asserted away.
    """
    r = simulate(_cfg(C.P4_RESERVE, comp="H4", n=300))
    assert r.reserve_activations > 0
    assert r.stage_max_reached >= 1
    peak = max(hf for _t, hf, _p in r.trace_h_active)
    assert peak > r.r_hash_initial + 1e-9


def test_p3_never_activates_reserves():
    r = simulate(_cfg(C.P3_ENERGY, comp="H2", n=200))
    assert r.reserve_activations == 0
    assert r.power_state["wake_events"] == 0
    assert r.power_state["t_standby_miner_s"] > 0


# ==========================================================================
# 8. Seeds, pairing and reproducibility
# ==========================================================================
def test_seed_groups_are_disjoint_and_fresh():
    groups = {"pilot": seedmod.pilot_seeds(), "primary": seedmod.primary_seeds(),
              "secondary": seedmod.secondary_seeds(),
              "long": seedmod.longhorizon_seeds()}
    for a, b in itertools.combinations(groups, 2):
        assert not (set(groups[a]) & set(groups[b]))
    for g in groups.values():
        assert len(g) == len(set(g))
    assert "Stage8Y" in seedmod.NAMESPACE


def test_seeds_are_disjoint_from_stage8x():
    from experiments.stage8x.config import seeds as x_seeds
    x_all = set(x_seeds.primary_seeds()) | set(x_seeds.pilot_seeds())
    y_all = set(seedmod.pilot_seeds()) | set(seedmod.primary_seeds()) | \
        set(seedmod.secondary_seeds()) | set(seedmod.longhorizon_seeds())
    assert not (x_all & y_all)
    assert seedmod.NAMESPACE != x_seeds.NAMESPACE


@pytest.mark.parametrize("protocol", [C.POW, C.P1_EQUAL, C.P3_ENERGY, C.P4_RESERVE])
def test_seed_reproducibility(protocol):
    cfg = _cfg(protocol, comp="H4", n=200)
    a, b = simulate(cfg), simulate(cfg)
    for f in ("accepted_blocks", "blocks_created", "total_evaluations",
              "duplicate_evaluations", "reserve_activations", "range_completions",
              "epoch_exhaustions"):
        assert getattr(a, f) == getattr(b, f)
    assert a.block_intervals == b.block_intervals
    assert a.power_state["pw_active_Ws"] == pytest.approx(b.power_state["pw_active_Ws"])


def test_matched_runs_share_seed_and_hardware():
    runs = C.primary_matrix()
    by = {}
    for r in runs:
        by.setdefault((r.composition, r.n_miners, r.seed_index), {})[r.protocol] = r
    for _key, d in by.items():
        seeds = {r.seed for r in d.values()}
        assert len(seeds) == 1
        pops = {(r.population.total_hashrate_hps, r.population.total_power_w)
                for r in d.values()}
        assert len(pops) == 1


def test_alpha_is_accounting_only():
    src = open("experiments/stage8y/src/engine.py", encoding="utf-8").read()
    assert "alpha" not in src.lower()
    fields = {f for f in C.RunConfig.__dataclass_fields__}
    assert "alpha" not in fields


def test_alpha_changes_only_energy_not_trajectory():
    cfg = _cfg(C.P4_RESERVE, comp="H4", n=200)
    r = simulate(cfg)
    p = r.power_state
    prices = em.account_all(p["pw_active_Ws"], p["pw_waking_Ws"], p["pw_low_Ws"],
                            p["pw_standby_Ws"], C.ALPHA_CASES)
    r2 = simulate(cfg)
    assert (r.accepted_blocks, r.total_evaluations, r.block_intervals) == \
           (r2.accepted_blocks, r2.total_evaluations, r2.block_intervals)
    tot = [prices[k].total_kWh for k in ("alpha_0", "alpha_005", "alpha_010",
                                         "alpha_025", "alpha_050")]
    assert tot == sorted(tot)
    assert all(pr.active_J == pytest.approx(prices["alpha_0"].active_J)
               for pr in prices.values())


# ==========================================================================
# 9. Metrics and the mandatory decomposition
# ==========================================================================
def test_decomposition_is_exact_and_additive():
    r = simulate(_cfg(C.P4_RESERVE, comp="H4", n=300))
    for alpha in (0.0, 0.10, 0.25):
        d = mx.decompose_saving(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s, alpha)
        assert d["power_identity_error_Ws"] < 1e-3
        assert d["decomposition_residual_J"] == pytest.approx(0.0, abs=1e-3)
        assert (d["dE_participation_J"] + d["dE_selection_J"]) == pytest.approx(
            d["dE_total_J"], rel=1e-12)
        assert (d["dE_postrange_J"] + d["dE_reserve_J"]) == pytest.approx(
            d["dE_total_J"], rel=1e-12)
        assert (d["dE_participation_shapley_J"] + d["dE_selection_shapley_J"]
                ) == pytest.approx(d["dE_total_J"], rel=1e-12)
        assert d["dE_stale_J"] == 0.0


def test_selection_term_is_zero_in_the_homogeneous_control():
    r = simulate(_cfg(C.P3_ENERGY, comp="H0", n=300))
    d = mx.decompose_saving(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s, 0.0)
    assert abs(d["share_selection"]) < 1e-6
    m = mx.participation_metrics(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s)
    assert m["SelectivityGain"] == pytest.approx(1.0, abs=1e-6)


def test_selectivity_gain_exceeds_one_when_heterogeneous():
    r = simulate(_cfg(C.P3_ENERGY, comp="H2", n=300))
    m = mx.participation_metrics(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s)
    assert m["SelectivityGain"] > 1.0


def test_security_hash_fraction_bounds():
    r = simulate(_cfg(C.P3_ENERGY, comp="H4", n=300, target_hash_fraction=0.6))
    m = mx.participation_metrics(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s)
    assert 0.0 <= m["min_SecurityHashFraction"] <= m["mean_SecurityHashFraction"] <= 1.0
    assert m["mean_SecurityHashFraction"] < 0.95


def test_pocol_has_zero_hash_gaps_at_template_refresh():
    """Documented, reportable diagnostic: because hash-proportional slots make every
    active miner finish at the same instant, the whole network is momentarily parked
    between domain exhaustion and receipt of the refreshed common template, so the
    *minimum instantaneous* security hash fraction is 0 for every PoCol policy while
    the *time-average* stays high. PoW has no such gap."""
    for proto in (C.P0_ALL, C.P2_HASHPROP, C.P3_ENERGY, C.P4_RESERVE):
        r = simulate(_cfg(proto, comp="H2", n=200))
        m = mx.participation_metrics(r.power_state, r.H_N_Hps, r.P_N_W, r.horizon_s)
        assert m["min_SecurityHashFraction"] == pytest.approx(0.0, abs=1e-12)
        assert m["mean_SecurityHashFraction"] > 0.3
    rp = simulate(_cfg(C.POW, comp="H2", n=200))
    mp = mx.participation_metrics(rp.power_state, rp.H_N_Hps, rp.P_N_W, rp.horizon_s)
    assert mp["min_SecurityHashFraction"] == pytest.approx(1.0)


def test_gini_and_fairness_bounds():
    assert mx.gini([1, 1, 1, 1]) == pytest.approx(0.0, abs=1e-12)
    assert mx.gini([0, 0, 0, 4]) > 0.7
    assert mx.gini([0, 0, 0, 0]) is None
    r = simulate(_cfg(C.P3_ENERGY, comp="H2", n=200))
    f = mx.fairness_metrics(r.device_stats, r.blocks_by_miner,
                            r.active_seconds_by_miner, r.n_miners, r.horizon_s)
    assert f["miners_with_zero_active_time"] > 0        # parked miners never mine
    assert 0.0 <= f["gini_active_time_by_miner"] <= 1.0


def test_na_is_never_replaced_by_zero():
    assert em.saving_fraction(1.0, 0.0) is None
    assert mx._safe_div(1.0, 0.0) is None
    assert mx.paired_service_metrics(
        {"accepted_blocks": 5, "median_block_interval": None,
         "mean_block_interval": None, "power_state": {"integral_H_active_hashes": 1.0}},
        {"accepted_blocks": 0, "median_block_interval": None,
         "mean_block_interval": None, "power_state": {"integral_H_active_hashes": 1.0}}
    )["BlockRetention"] is None


# ==========================================================================
# 10. Matrix shapes and configuration integrity
# ==========================================================================
def test_primary_matrix_shape():
    runs = C.primary_matrix()
    assert len(runs) == 1080
    assert len({r.run_id for r in runs}) == 1080
    assert {r.protocol for r in runs} == set(C.PRIMARY_PROTOCOLS)
    assert {r.composition for r in runs} == set(C.PRIMARY_COMPOSITIONS)
    assert {r.n_miners for r in runs} == set(C.PRIMARY_NETWORK_SIZES)
    for proto in C.PRIMARY_PROTOCOLS:
        assert sum(1 for r in runs if r.protocol == proto) == 270


def test_phases_are_separated():
    ids = {}
    for name, mat in (("pilot", C.pilot_matrix()), ("primary", C.primary_matrix()),
                      ("secondary", C.secondary_matrix()),
                      ("longhorizon", C.longhorizon_matrix())):
        ids[name] = {r.run_id for r in mat}
        assert len(ids[name]) == len(mat)
    for a, b in itertools.combinations(ids, 2):
        assert not (ids[a] & ids[b])


def test_acceptance_criteria_are_preregistered():
    a = C.ACCEPTANCE
    assert a["saving_threshold"] == 0.50
    assert a["retention_strong"] == 0.95 and a["retention_moderate"] == 0.90
    assert a["latency_ratio_max"] == 1.10
    assert "alpha > 0" in a["outcome_A"]


def test_alpha_labels_are_not_vendor_modes():
    assert set(C.ALPHA_CASES) == {"alpha_0", "alpha_005", "alpha_010",
                                  "alpha_025", "alpha_050"}
    assert "not manufacturer-certified" in C.ALPHA_NOTE
    for label in C.ALPHA_CASES:
        assert "bitmain" not in label.lower() and "mode" not in label.lower()


def test_stage8y_never_imports_global_state():
    banned = ("InputsConfig", "Main", "Scheduler", "Statistics", "Event")
    for dirpath, dirs, files in os.walk("experiments/stage8y"):
        dirs[:] = [d for d in dirs if d != "__pycache__"]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            for line in open(os.path.join(dirpath, fn), encoding="utf-8"):
                ls = line.strip()
                if ls.startswith(("import ", "from ")):
                    for b in banned:
                        assert f" {b}" not in ls and not ls.startswith(f"import {b}")


def test_only_stage8x_hashing_is_imported_from_outside():
    allowed = "experiments.stage8x.simulator import hashing"
    for dirpath, dirs, files in os.walk("experiments/stage8y"):
        # the test module itself imports the Stage 8X seed registry, read-only, purely
        # to assert seed disjointness; that is not production code.
        dirs[:] = [d for d in dirs if d not in ("__pycache__", "tests")]
        for fn in files:
            if not fn.endswith(".py"):
                continue
            src = open(os.path.join(dirpath, fn), encoding="utf-8").read()
            for line in src.splitlines():
                ls = line.strip()
                if "stage8x" in ls and ls.startswith(("import ", "from ")):
                    assert allowed in ls
