"""Phase B5 — target-based stochastic success model for PoCol rounds.

Replaces the old "sample exactly one solution nonce, winner = range containing
it" rule (which guaranteed exactly one success every round). The new model draws
a network first-success time ~ Exponential(1/T), allows zero-success (exhausted)
domains, and picks the winner in proportion to hash share.

Validated analytically against the expected distribution.

Run:  python -m pytest tests/ -v   or   python tests/test_pow_success_model.py
"""
import os
import sys
import math
import random
import statistics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from InputsConfig import InputsConfig as p
from Models.PoCol.Node import Node as PoColNode
from Models.PoCol.Consensus import Consensus as C


class _M:
    def __init__(self, id_, rate): self.id = id_; self._r = rate
    def get_hashrate_hps(self): return self._r


def _setup(n=100, net=141e12):
    p.HashPowerIsShare = True
    p.NetworkHashRate_Hps = net
    p.MinerEfficiency_J_per_TH = 21.5
    p.NODES = [PoColNode(id=i, hashPower=1) for i in range(n)]
    return net


def test_block_time_is_exponential_mean_T():
    """Mean network block time ~= T and CV ~= 1 (exponential signature)."""
    _setup(n=100)
    T = 600.0
    H_total = 141e12
    space = int(2.0 * H_total * T)          # same sizing as _get_nonce_space
    rng = random.Random(42)
    miners = [_M(i, H_total / 100) for i in range(100)]
    rates = [H_total / 100] * 100
    times = []
    for _ in range(20000):
        _, bt, _ex = C._sample_round_outcome(miners, rates, H_total, space, T, rng=rng)
        times.append(bt)
    mean = statistics.mean(times)
    sd = statistics.pstdev(times)
    assert abs(mean - T) / T < 0.05, f"mean block time {mean} not ~= {T}"
    assert abs(sd / mean - 1.0) < 0.10, f"CV {sd/mean} not ~= 1 (not exponential)"


def test_zero_one_and_many_successes_are_all_possible():
    """Exhaustion (zero-success domains) must occur with the expected frequency.

    With horizon = space/H_total = 2T, P(one drawn attempt exhausts) = P(Exp(1/T) > 2T)
    = e^-2 ~= 0.135, so exhausted rounds must appear (not be impossible).
    """
    _setup(n=50)
    T = 600.0
    H_total = 141e12
    space = int(2.0 * H_total * T)
    rng = random.Random(7)
    miners = [_M(i, H_total / 50) for i in range(50)]
    rates = [H_total / 50] * 50
    total_exhausted = 0
    rounds = 20000
    for _ in range(rounds):
        _, _bt, ex = C._sample_round_outcome(miners, rates, H_total, space, T, rng=rng)
        total_exhausted += ex
    # expected exhausted attempts per successful round = e^-2/(1-e^-2) ~= 0.156
    exp_per_round = math.exp(-2) / (1 - math.exp(-2))
    observed = total_exhausted / rounds
    assert observed > 0, "zero-success domains never occurred (model still guarantees success)"
    assert abs(observed - exp_per_round) / exp_per_round < 0.15, \
        f"exhaustion rate {observed:.3f} not ~= {exp_per_round:.3f}"


def test_winner_is_hash_weighted():
    """A miner with double the hash rate wins ~2x as often."""
    _setup(n=3)
    T = 600.0
    rates = [1e12, 1e12, 2e12]      # shares 25/25/50
    H_total = sum(rates)
    space = int(2.0 * H_total * T)
    miners = [_M(i, rates[i]) for i in range(3)]
    rng = random.Random(99)
    wins = {0: 0, 1: 0, 2: 0}
    for _ in range(30000):
        w, _bt, _ex = C._sample_round_outcome(miners, rates, H_total, space, T, rng=rng)
        wins[w] += 1
    frac2 = wins[2] / 30000.0
    assert abs(frac2 - 0.5) < 0.03, f"miner 2 (50% hash) won {frac2:.3f}, expected ~0.5"
    assert abs(wins[0] / 30000.0 - 0.25) < 0.03


def test_no_predetermined_solution_nonce():
    """The old guaranteed-nonce field is no longer the winner mechanism."""
    src = open(os.path.join(os.path.dirname(__file__), "..",
               "Models", "PoCol", "Consensus.py"), encoding="utf-8").read()
    assert "active_solution_nonce = random.randrange(0, space)" not in src, \
        "PoCol still pre-samples one guaranteed solution nonce"


def _run_all():
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    failed = 0
    for fn in fns:
        try:
            fn(); print(f"PASS  {fn.__name__}")
        except AssertionError as e:
            failed += 1; print(f"FAIL  {fn.__name__}: {e}")
    print(f"\n{len(fns)-failed}/{len(fns)} passed")
    return failed


if __name__ == "__main__":
    sys.exit(1 if _run_all() else 0)
