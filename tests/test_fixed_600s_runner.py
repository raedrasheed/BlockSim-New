"""Fixed-600s runner — invariant 26 (fresh-subprocess isolation) and CLI sanity.

Run:  python -m pytest tests/test_fixed_600s_runner.py -v
  or:  python tests/test_fixed_600s_runner.py
"""
import os
import sys
import json
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

RUNNER = os.path.join(ROOT, "experiments", "fixed_600s_pocol", "run_scenario.py")


def _sub(args):
    out = subprocess.run([sys.executable, RUNNER] + args,
                         capture_output=True, text=True, cwd=ROOT)
    assert out.returncode == 0, out.stderr[-1500:]
    return json.loads(out.stdout.strip().splitlines()[-1])


def test_inv26_fresh_subprocess_reproducibility():
    """Two independent subprocesses with identical args produce identical JSON;
    an interleaved different run cannot contaminate them (fresh interpreter)."""
    args = ["pocol_disjoint_nonce", "50", "--hardware", "H1", "--p", "auto",
            "--seed", "11", "--sim", "3000"]
    a = _sub(args)
    _ = _sub(["common_template_duplicate_pow", "20", "--hardware", "H2",
              "--M", "6000", "--h2-rate", "10", "--p", "0.001", "--seed", "5",
              "--sim", "1800"])                      # different run in between
    b = _sub(args)
    assert a == b


def test_cli_deterministic_spec12():
    rec = _sub(["pocol_disjoint_nonce", "10", "--hardware", "H2", "--M", "100",
                "--h2-rate", "1", "--placement", "last", "--sim", "600"])
    assert rec["total_attempts"] == 100
    assert rec["accepted_blocks"] == 1
    assert abs(rec["mean_discovery_time_s"] - 10.0) < 1e-9


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
