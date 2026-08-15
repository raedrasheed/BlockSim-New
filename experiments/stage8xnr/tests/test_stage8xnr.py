"""Stage 8X-NR validation suite — the ten named tests of brief section 30,
plus engine identity and saturation checks.

Toy-domain tests monkeypatch nothing: the interval arithmetic functions take an
explicit ``domain`` parameter, so exact set enumeration on small cyclic domains
is compared directly against the interval model.
"""

import itertools
import random

import pytest

from experiments.stage8xnr.config.nr_config import (
    ARM_CONV_OFF, ARM_CONV_ZERO, ARM_MT_OFF, ARM_MT_ZERO, ARM_PC, N_GRID,
    S_NONCE, derive_difficulty, pocol_partition, predictions,
    subsweep_window_ticks,
)
from experiments.stage8xnr.config.seeds import (
    pilot_seeds, primary_seeds, verify_disjoint,
)
from experiments.stage8xnr.src.noncedomain import (
    arc_intersection_measure, arc_to_linear, expected_unique_random,
    max_multiplicity, measure_covered_at_least, multiplicity_profile,
    pairwise_overlap_summary, union_measure, verify_partition,
)
from experiments.stage8xnr.src.traversal import (
    offset_phase, pocol_window, template_epochs_in_window, window,
    zero_start_phase,
)
from experiments.stage8xnr.src.engine_nr import run_one

import os
REPO = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.dirname(os.path.abspath(__file__)))))


# ---------------- Test 1 — 32-bit domain ----------------------------------
class TestT1Domain:
    def test_domain_size_is_exactly_2_pow_32(self):
        assert S_NONCE == 2 ** 32 == 4_294_967_296

    def test_nonce_values_bounded(self):
        # every phase / arc start produced by the traversal layer is in range
        assert zero_start_phase() == 0
        for s, t in [(0, 0), (S_NONCE - 1, 1), (123, S_NONCE + 5),
                     (2 ** 31, 2 ** 33)]:
            p = offset_phase(s, t)
            assert 0 <= p <= S_NONCE - 1
        w = window(S_NONCE - 1, 10)
        assert 0 <= w.partial_arc[0] <= S_NONCE - 1


# ---------------- Tests 2-4 — PoCol partition -----------------------------
class TestT2T3T4Partition:
    @pytest.mark.parametrize("n", N_GRID)
    def test_full_coverage(self, n):
        v = verify_partition(pocol_partition(n))
        assert v["full_coverage"] and v["covered"] == S_NONCE

    @pytest.mark.parametrize("n", N_GRID)
    def test_no_overlap(self, n):
        v = verify_partition(pocol_partition(n))
        assert v["overlap"] == 0

    @pytest.mark.parametrize("n", N_GRID)
    def test_uneven_partition_spread_at_most_one(self, n):
        v = verify_partition(pocol_partition(n))
        assert v["size_spread_le_1"]
        assert S_NONCE % n != 0          # none of the tested N divides 2^32
        assert v["size_max"] - v["size_min"] == 1

    def test_formula_matches_brief(self):
        n = 300
        ranges = pocol_partition(n)
        for i, (s, e) in enumerate(ranges):
            assert s == i * S_NONCE // n
            assert e - 1 == (i + 1) * S_NONCE // n - 1


# ---------------- Test 5 — cyclic interval overlap / wrap-around ----------
class TestT5CyclicIntervals:
    def test_wraparound_split(self):
        assert arc_to_linear((S_NONCE - 3, 7)) == [(S_NONCE - 3, S_NONCE), (0, 4)]

    def test_wraparound_intersection(self):
        a = (S_NONCE - 5, 10)   # wraps: [S-5,S) u [0,5)
        b = (2, 6)              # [2,8)
        assert arc_intersection_measure(a, b) == 3   # {2,3,4}

    def test_wraparound_union(self):
        assert union_measure([(S_NONCE - 4, 8), (2, 4)]) == 10

    def test_full_domain_clamp(self):
        assert union_measure([(17, S_NONCE)]) == S_NONCE
        assert arc_intersection_measure((0, S_NONCE), (99, 5)) == 5


# ---------------- Tests 6-7 — nonce reuse vs exact duplicate --------------
class TestT6T7Identity:
    def _classify(self, ev_a, ev_b):
        """(template, nonce) pair classification used by the metric layer."""
        nonce_reuse = ev_a[1] == ev_b[1]
        exact_dup = ev_a == ev_b
        return nonce_reuse, exact_dup

    def test_same_nonce_different_template_is_reuse_not_duplicate(self):
        reuse, dup = self._classify(("template_A", 42), ("template_B", 42))
        assert reuse is True and dup is False

    def test_same_nonce_same_template_is_reuse_and_duplicate(self):
        reuse, dup = self._classify(("template_A", 42), ("template_A", 42))
        assert reuse is True and dup is True

    def test_engine_realises_the_distinction(self):
        # CONV: rho_nonce(round) > 0 while rho_exact = 0.
        r = run_one(ARM_CONV_OFF, 100, 4242)
        rows = {sc["scope"]: sc for sc in r.scope_rows}
        assert rows["NR-global-run"]["rho_nonce"] > 0.999
        assert rows["NR-global-run"]["rho_exact"] == 0.0
        # MT: both positive and equal at epoch scope.
        m = run_one(ARM_MT_ZERO, 100, 4242)
        ep = {sc["scope"]: sc for sc in m.scope_rows}["NR-template-epoch"]
        assert ep["rho_nonce"] == ep["rho_exact"] == pytest.approx(99 / 100)


# ---------------- Test 8 — epoch reset ------------------------------------
class TestT8EpochReset:
    def test_cross_epoch_repeat_is_not_within_epoch_overlap(self):
        # PoCol miner sweeps its range in consecutive epochs: same nonce values
        # recur across epochs, but each within-epoch arc set stays disjoint.
        n = 4
        toy = 100
        ranges = [(i * toy // n, (i + 1) * toy // n) for i in range(n)]
        hi = max(e - s for s, e in ranges)
        arcs_by_epoch = {}
        for i, (s, e) in enumerate(ranges):
            for a in pocol_window(s, e - s, hi, 0, 2 * hi):  # two full epochs
                arcs_by_epoch.setdefault(i, []).append(a)
        # every miner repeated its own values across the two epochs...
        for i, arcs in arcs_by_epoch.items():
            assert len(arcs) == 2 and arcs[0] == arcs[1]
        # ...but within-epoch cross-miner multiplicity never exceeds 1
        one_epoch = [arcs_by_epoch[i][0] for i in range(n)]
        prof = multiplicity_profile(one_epoch, domain=toy)
        assert max_multiplicity(prof) == 1

    def test_engine_pc_epoch_scope_is_zero(self):
        r = run_one(ARM_PC, 100, 777)
        ep = {sc["scope"]: sc for sc in r.scope_rows}["NR-template-epoch"]
        assert ep["rho_nonce"] == 0.0 and ep["rho_exact"] == 0.0
        assert ep["m_max"] == 1 and ep["M_ge2"] == 0


# ---------------- Test 9 — analytical occupancy on toy domains ------------
class TestT9Occupancy:
    @pytest.mark.parametrize("s,m", [(50, 10), (50, 80), (256, 256), (1000, 1)])
    def test_occupancy_formula_matches_enumeration(self, s, m):
        rng = random.Random(1234 + s + m)
        trials = 4000
        mean_unique = 0.0
        for _ in range(trials):
            mean_unique += len({rng.randrange(s) for _ in range(m)})
        mean_unique /= trials
        expected = expected_unique_random(m, s)
        assert mean_unique == pytest.approx(expected, rel=0.02)

    def test_expected_repeats(self):
        s, m = 128, 200
        eu = expected_unique_random(m, s)
        assert m - eu > 0                      # repeats must be expected
        assert 0 < eu < min(m, s) + 1e-9


# ---------------- Test 10 — interval model vs explicit enumeration --------
class TestT10IntervalModel:
    @pytest.mark.parametrize("domain", [16, 97, 256])
    def test_union_and_multiplicity_match_sets(self, domain):
        rng = random.Random(domain)
        for _ in range(200):
            arcs = [(rng.randrange(domain), rng.randrange(0, domain + 1))
                    for _ in range(rng.randrange(1, 6))]
            explicit = [set((a + k) % domain for k in range(L))
                        for a, L in arcs]
            assert union_measure(arcs, domain) == len(set().union(*explicit))
            prof = multiplicity_profile(
                [(a, min(L, domain)) for a, L in arcs], domain=domain)
            from collections import Counter
            counts = Counter()
            for s in explicit:
                counts.update(s)
            for mult in range(1, 7):
                got = prof.get(mult, 0)
                want = sum(1 for v in counts.values() if v == mult)
                assert got == want, (arcs, mult)

    @pytest.mark.parametrize("domain", [32, 101])
    def test_pairwise_summary_matches_bruteforce(self, domain):
        rng = random.Random(domain * 7)
        for _ in range(100):
            n = rng.randrange(2, 8)
            L = rng.randrange(1, domain // 2 + 1)
            starts = [rng.randrange(domain) for _ in range(n)]
            summ = pairwise_overlap_summary(starts, L, domain=domain)
            sets = [set((s + k) % domain for k in range(L)) for s in starts]
            ovs = sorted(len(sets[i] & sets[j])
                         for i in range(n) for j in range(i + 1, n))
            assert summ["n_pairs"] == len(ovs)
            assert summ["max"] == (ovs[-1] if ovs else 0)
            assert summ["mean"] == pytest.approx(sum(ovs) / len(ovs))
            import math as _math
            assert summ["p95"] == float(
                ovs[max(0, _math.ceil(0.95 * len(ovs)) - 1)])
            import statistics
            # median definition: median over all pairs, zeros included
            want_med = float(sorted(ovs)[len(ovs) // 2])
            assert summ["median"] == pytest.approx(want_med, abs=max(
                1.0, 0.0)) or summ["median"] == pytest.approx(
                statistics.median(ovs), abs=1.0)


# ---------------- traversal decomposition ---------------------------------
class TestTraversal:
    def test_window_decomposition_exact(self):
        w = window(5, 3 * S_NONCE + 7)
        assert w.full_sweeps == 3 and w.partial_arc == (5, 7)
        assert w.covers_domain

    def test_template_epoch_counting(self):
        assert template_epochs_in_window(S_NONCE, 0) == (1, 0)
        assert template_epochs_in_window(S_NONCE - 1, 1) == (1, 0)
        assert template_epochs_in_window(10, 5) == (0, 15)

    def test_pocol_window_parks_after_range(self):
        arcs = pocol_window(range_start=10, range_len=5, epoch_ticks=8,
                            ticks_into_epoch=0, ticks=8)
        assert arcs == [(10, 5)]           # 3 parked ticks produce no arc


# ---------------- difficulty semantics ------------------------------------
class TestDifficulty:
    @pytest.mark.parametrize("n", N_GRID)
    def test_formula(self, n):
        d = derive_difficulty(n)
        h_total = n * 234_000_000_000_000
        assert d.q_per_candidate == pytest.approx(1.0 / (h_total * 600.0))
        assert d.difficulty == pytest.approx(h_total * 600.0 / 2 ** 32)
        # q * D * 2^32 == 1 by construction
        assert d.q_per_candidate * d.difficulty * 2 ** 32 == pytest.approx(1.0)

    def test_shared_across_arms(self):
        # engine derives difficulty from N only — one D_N for every arm
        d1, d2 = derive_difficulty(300), derive_difficulty(300)
        assert d1 == d2


# ---------------- seeds ----------------------------------------------------
class TestSeeds:
    def test_counts_and_determinism(self):
        assert len(primary_seeds()) == 30
        assert len(set(primary_seeds())) == 30
        assert len(pilot_seeds()) == 2
        assert primary_seeds() == primary_seeds()

    def test_disjoint_from_earlier_stages(self):
        rep = verify_disjoint(REPO)
        assert rep["disjoint"], rep
        assert len(rep["checked_registries"]) >= 2   # 8X and 8Y at minimum


# ---------------- engine identities and saturation predictions ------------
class TestEngine:
    @pytest.mark.parametrize("arm", [ARM_CONV_ZERO, ARM_CONV_OFF, ARM_MT_OFF,
                                     ARM_PC])
    def test_identities(self, arm):
        r = run_one(arm, 100, 20260814)
        assert r.identity_errors["state_time_conservation_rel"] < 1e-12
        assert r.identity_errors["work_identity_rel"] < 1e-12

    def test_conv_round_saturation(self):
        r = run_one(ARM_CONV_OFF, 100, 11)
        for rr in r.round_rows:
            if float(rr["duration_s"]) > 1.0:      # any macroscopic round
                assert rr["round_U_nonce"] == S_NONCE
                assert rr["round_m_max"] == 100
                assert float(rr["round_rho_exact"]) == 0.0

    def test_pc_cross_miner_overlap_zero_everywhere(self):
        r = run_one(ARM_PC, 100, 12)
        for rr in r.round_rows:
            assert rr["round_M_ge2"] == 0 and rr["round_m_max"] <= 1
            assert float(rr["round_O_max"]) == 0
        run_scope = {sc["scope"]: sc for sc in r.scope_rows}["NR-global-run"]
        assert run_scope["m_max"] == 1 and run_scope["M_ge2"] == 0

    def test_mt_zero_stale_co_discovery(self):
        r = run_one(ARM_MT_ZERO, 100, 13)
        assert r.stale_blocks == r.accepted_blocks * 99

    def test_energy_equality_when_active_time_equal(self):
        # brief section 17: same t_active, same P  =>  same E, regardless of
        # nonce-reuse pattern.
        a = run_one(ARM_CONV_ZERO, 100, 14)
        b = run_one(ARM_CONV_OFF, 100, 14)
        c = run_one(ARM_MT_OFF, 100, 14)
        assert a.t_active_miner_s == b.t_active_miner_s == c.t_active_miner_s
        assert a.energy_j(0.0) == b.energy_j(0.0) == c.energy_j(0.0)

    def test_subsweep_zero_vs_offset_differ(self):
        z = run_one(ARM_CONV_ZERO, 100, 15)
        o = run_one(ARM_CONV_OFF, 100, 15)
        w = subsweep_window_ticks(100)
        zrow, orow = z.round_rows[0], o.round_rows[0]
        assert float(zrow["subsweep_O_mean"]) == float(w)      # total overlap
        assert float(orow["subsweep_O_mean"]) < w / 10          # sparse overlap
        assert float(zrow["subsweep_rho_nonce"]) == pytest.approx(0.99)
        assert float(orow["subsweep_rho_nonce"]) < 0.30

    def test_offsets_reproducible_by_seed(self):
        # brief test 10/14: same configuration + same seed => identical run,
        # including the independently seeded offsets.
        a = run_one(ARM_CONV_OFF, 100, 999)
        b = run_one(ARM_CONV_OFF, 100, 999)
        assert a.C_total == b.C_total
        assert a.intervals_s == b.intervals_s
        assert a.round_rows == b.round_rows
        assert a.scope_rows == b.scope_rows
        c = run_one(ARM_CONV_OFF, 100, 998)
        assert c.round_rows[0]["subsweep_U_nonce"] != \
            a.round_rows[0]["subsweep_U_nonce"]   # different seed, different offsets

    def test_template_renewal_after_exhaustion(self):
        # brief test 11: every completed 2^32-tick sweep rolls the template.
        r = run_one(ARM_CONV_OFF, 100, 555)
        assert r.nonce_domain_exhaustions == r.template_epochs_completed
        assert r.nonce_resets == 0                    # OFFSET never resets
        z = run_one(ARM_CONV_ZERO, 100, 555)
        assert z.nonce_resets > z.nonce_domain_exhaustions   # + round boundaries

    def test_multiplicity_extensions_on_toy(self):
        from experiments.stage8xnr.src.metrics_nr import cross_miner_stats
        # domain 10: arcs [0,4), [2,6), [4,8): multiplicities 1/2 alternate
        stats = cross_miner_stats([(0, 4), (2, 6), (4, 8)])
        # explicit enumeration on Z_10 of [0,4),[2,8),[4,12 mod)... use exact:
        # arcs: {0,1,2,3}, {2,3,4,5,6,7}, {4,5,6,7,8,9,10,11 -> mod S_NONCE}
        # over the 2^32 domain these arcs don't wrap; counts:
        # 2,3 covered by 2; 4,5,6,7 covered by 2; rest by 1
        assert stats["M_ge2"] == 6 and stats["M_ge3"] == 0
        assert stats["m_max"] == 2 and stats["mean_mult_reused"] == 2.0
        stats3 = cross_miner_stats([(0, 5), (0, 5), (0, 5)])
        assert stats3["M_ge3"] == 5 and stats3["mean_mult_reused"] == 3.0

    def test_paired_round_process(self):
        # same seed => identical round-duration draws for equal-rate arms
        a = run_one(ARM_CONV_OFF, 100, 16)
        b = run_one(ARM_PC, 100, 16)
        assert a.rounds == pytest.approx(b.rounds, abs=1)
        # PC blocks at most as fast; durations correlate near-perfectly
        if a.intervals_s and b.intervals_s:
            k = min(len(a.intervals_s), len(b.intervals_s))
            for x, y in zip(a.intervals_s[:k], b.intervals_s[:k]):
                assert abs(x - y) / x < 0.05
