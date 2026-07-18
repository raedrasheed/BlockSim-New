"""Phase B4 — block-interval calibration.

PoW and PoCol must be compared under approximately equivalent realized
accepted-main-chain block intervals, so that neither protocol is advantaged by
running at a different production rate. The shared target is:

    T = Binterval = 600 s per accepted main-chain block.

Calibration rule (deterministic, identical target for both protocols):

  PoW   — each miner i draws its next-block delay from
            Exp( rate = (h_i / H_total) / T ).
          The network's first block is the minimum of N independent
          exponentials, itself Exp( rate = (Σ h_i/H_total)/T ) = Exp(1/T),
          so E[interval] = T.

  PoCol — the shared nonce domain is auto-sized to S = 2·H_total·T, giving a
          per-hash success probability p = 1/(H_total·T). The network first-
          success time is Exp(1/T) (mean T), truncated by the domain horizon
          h = S/H_total = 2T (a round may EXHAUST and redraw). The truncation
          identity E[block_time] = E[N]·h + E[X | X≤h] = T holds exactly, so
          E[interval] = T as well.

Both protocols therefore target the SAME expected interval T by construction;
this test verifies the two realized means agree with each other and with T
within Monte-Carlo tolerance. (The realized mean sits slightly below T for BOTH
protocols because the estimator (t_last−t_first)/(n−1) omits the censored gap
past simTime; the bias is identical across protocols, which is what a controlled
comparison requires.)

Run:  python -m pytest tests/ -v   or   python tests/test_block_interval_calibration.py
"""
import os
import sys
import statistics

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from experiments.run_scenario import run

TARGET = 600.0
N = 100
SEEDS = range(1, 31)


def _mean_interval(protocol):
    xs = [run(protocol, N, s)["accepted_block_interval_s"] for s in SEEDS]
    xs = [x for x in xs if x == x]        # drop any nan
    return statistics.mean(xs)


def test_pow_mean_interval_near_target():
    m = _mean_interval("PoW")
    assert abs(m - TARGET) / TARGET < 0.25, f"PoW mean interval {m:.1f}s not ~= {TARGET}s"


def test_pocol_mean_interval_near_target():
    m = _mean_interval("PoCol")
    assert abs(m - TARGET) / TARGET < 0.25, f"PoCol mean interval {m:.1f}s not ~= {TARGET}s"


def test_both_protocols_run_at_equivalent_intervals():
    """The controlled comparison requires PoW and PoCol to realize approximately
    the same accepted-main-chain interval (neither runs faster than the other)."""
    mp = _mean_interval("PoW")
    mc = _mean_interval("PoCol")
    rel = abs(mp - mc) / ((mp + mc) / 2.0)
    assert rel < 0.15, f"PoW ({mp:.1f}s) and PoCol ({mc:.1f}s) intervals differ by {rel*100:.1f}%"


def test_calibration_is_deterministic_per_seed():
    """Same (protocol, n, seed) reproduces the same interval bit-for-bit."""
    a = run("PoCol", N, 3)["accepted_block_interval_s"]
    b = run("PoCol", N, 3)["accepted_block_interval_s"]
    assert a == b, f"non-deterministic interval: {a} vs {b}"


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
