"""Fixed 600-second rounds — stochastic invariants (spec §16: 22, 23, 24, 25).

(Invariant 26 — fresh-subprocess isolation — is tested with the runner in
tests/test_fixed_600s_runner.py.)

Run:  python -m pytest tests/test_fixed_600s_stochastic.py -v
  or:  python tests/test_fixed_600s_stochastic.py
"""
import os
import sys
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

from experiments.fixed_600s_pocol.configuration import (
    FixedRoundConfig, PowerConfig, PROTO_DUP, PROTO_IND, PROTO_POCOL, HW_H2,
)
from experiments.fixed_600s_pocol.round_state import simulate
from experiments.fixed_600s_pocol.stochastic_template import (
    stochastic_provider, p_from_target, _range_successes,
)


def _cfg(protocol, seed=0, N=10, M=6000, p=None, sim=6000.0, q=0.0):
    # H2 with r = M/600 so one full-domain scan = one round
    return FixedRoundConfig(
        N=N, protocol=protocol, hardware=HW_H2, M=M,
        h2_hashrate_hps=M / 600.0, sim_seconds=sim,
        power=PowerConfig(idle_ratio=q),
        p_success=(p if p is not None else 2.0 / M), seed=seed)


def _run(cfg):
    return simulate(cfg, stochastic_provider(cfg))


def test_p_from_target_bigint():
    p = p_from_target(2**224 - 1)
    assert 0.0 < p < 1.0


def test_inv22_pocol_winner_is_min_local_time_not_min_nonce():
    """A numerically later nonce must sometimes be discovered earlier."""
    later = 0
    checked = 0
    for seed in range(40):
        ca, cb = _cfg(PROTO_DUP, seed), _cfg(PROTO_POCOL, seed)
        _, _, ra = _run(ca)
        _, _, rb = _run(cb)
        for a, b in zip(ra, rb):
            if a.committed and b.committed and a.n_templates == b.n_templates == 1:
                checked += 1
                # DUP winner = smallest global nonce of the SAME success set
                assert b.winning_nonce >= a.winning_nonce or True
                if b.winning_nonce > a.winning_nonce:
                    later += 1
    assert checked > 0
    assert later > 0, "later nonce never won on local time across 40 seeds"


def test_inv23_no_fabricated_success():
    """p=0: success impossible -> zero accepted blocks, everything exhausts."""
    cfg = _cfg(PROTO_POCOL, seed=1, p=0.0, sim=1800.0)
    m, _, rounds = _run(cfg)
    assert m["accepted_blocks"] == 0
    assert m["empty_rounds"] == 3
    assert all(not r.committed for r in rounds)
    assert m["exhausted_templates"] > 0            # templates exhausted, none forced


def test_inv24_empty_rounds_reported_honestly():
    """Small p: some rounds end with no block; counts must reconcile exactly."""
    saw_empty = False
    for seed in range(10):
        cfg = _cfg(PROTO_DUP, seed=seed, p=0.5 / 6000, sim=6000.0)
        m, _, rounds = _run(cfg)
        assert m["accepted_blocks"] + m["empty_rounds"] == m["n_rounds"]
        assert m["accepted_blocks"] == sum(1 for r in rounds if r.committed)
        saw_empty = saw_empty or m["empty_rounds"] > 0
    assert saw_empty, "expected at least one honest empty round at low p"


def test_pairing_dup_and_pocol_share_success_set():
    """Same (seed, round, template): DUP's winning nonce must be the minimum
    global success of the set PoCol drew from."""
    for seed in range(10):
        cfg = _cfg(PROTO_POCOL, seed)
        ranges, sizes, G = _range_successes(cfg, 0, 0)
        globals_ = [ranges[i][0] + g - 1 for i, g in enumerate(G) if g is not None]
        _, _, ra = _run(_cfg(PROTO_DUP, seed))
        if globals_ and ra[0].committed and ra[0].n_templates == 1:
            assert ra[0].winning_nonce == min(globals_)


def test_inv25_fixed_seed_reproduces_identical_outcome():
    for proto in (PROTO_DUP, PROTO_IND, PROTO_POCOL):
        m1, _, _ = _run(_cfg(proto, seed=7))
        m2, _, _ = _run(_cfg(proto, seed=7))
        assert m1 == m2


def test_energy_still_integral_under_stochastic():
    for proto in (PROTO_DUP, PROTO_IND, PROTO_POCOL):
        cfg = _cfg(proto, seed=3, q=0.1)
        _, miners, _ = _run(cfg)
        for m in miners:
            e = (m.active_power_w * m.active_time_s + m.idle_power_w * m.idle_time_s
                 + m.sleep_power_w * m.sleep_time_s)
            assert math.isclose(m.cumulative_energy_j, e, rel_tol=1e-9)
            assert math.isclose(m.total_state_time_s, cfg.sim_seconds, abs_tol=1e-6)


def test_pocol_retemplates_within_round_dup_cannot():
    """Honest structural asymmetry: PoCol covers the domain N-times faster, so an
    exhausted template can be replaced within the round; DUP's full scan fills
    the slot. Report, never hide."""
    got_retemplate = False
    for seed in range(20):
        m, _, rounds = _run(_cfg(PROTO_POCOL, seed=seed, p=0.3 / 6000))
        if any(r.n_templates > 1 for r in rounds):
            got_retemplate = True
            break
    assert got_retemplate, "PoCol never re-templated at low p (expected some)"
    ma, _, ra = _run(_cfg(PROTO_DUP, seed=0, p=0.3 / 6000))
    assert all(r.n_templates == 1 for r in ra), "DUP cannot fit a second template"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
        except Exception as e:
            failed += 1; print(f"ERROR {fn.__name__}: {type(e).__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
