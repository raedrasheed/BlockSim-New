"""PoCol equal-share idle extension (PoCol_IdleAfterRange) — main-simulator tests.

The extension is OPT-IN (default OFF). OFF must reproduce the corrected Finding-1
energy exactly (8.4208 kWh); ON must (a) save energy only through genuinely
shorter ACTIVE time, (b) distribute work/energy equally across miners, and
(c) never charge energy while idle.

Run:  python -m pytest tests/test_idle_after_range.py -v
  or:  python tests/test_idle_after_range.py
"""
import os
import sys
import json
import math
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)

E_CONT = 8.420833333333333          # P_network * simTime = 3031.5 W * 10000 s
_CACHE = {}


def _run(protocol, n, seed, idle):
    key = (protocol, n, seed, idle)
    if key not in _CACHE:
        out = subprocess.run(
            [sys.executable, os.path.join(ROOT, "experiments", "run_scenario_idle.py"),
             protocol, str(n), str(seed), "1" if idle else "0"],
            capture_output=True, text=True, cwd=ROOT)
        assert out.returncode == 0, out.stderr[-1500:]
        _CACHE[key] = json.loads(out.stdout.strip().splitlines()[-1])
    return _CACHE[key]


def test_flag_off_preserves_finding1_energy():
    """Default OFF: the corrected continuous-mining energy is untouched."""
    r = _run("PoCol", 100, 1, idle=False)
    assert math.isclose(r["energy_kWh"], E_CONT, rel_tol=1e-9)
    assert r["idle_miner_seconds"] == 0.0
    assert math.isclose(r["pct_time_active"], 100.0, abs_tol=1e-6)


def test_flag_on_saves_energy_via_active_time_only():
    """ON: energy = E_continuous * active_fraction exactly (wall-clock integral),
    i.e. the saving comes from shorter ACTIVE time, never from dividing by N."""
    r = _run("PoCol", 100, 1, idle=True)
    assert r["energy_kWh"] < E_CONT
    active_fraction = r["pct_time_active"] / 100.0
    assert math.isclose(r["energy_kWh"], E_CONT * active_fraction, rel_tol=1e-6), \
        f"{r['energy_kWh']} != {E_CONT} * {active_fraction}"


def test_flag_on_distributes_energy_equally():
    """Equal shares of the nonce domain -> equal ACTIVE time -> equal energy."""
    r = _run("PoCol", 100, 1, idle=True)
    assert math.isclose(r["per_miner_energy_kwh_min"], r["per_miner_energy_kwh_max"],
                        rel_tol=1e-9), "per-miner energy must be equal for equal miners"


def test_flag_on_state_time_conservation():
    """active + idle miner-seconds ~= N * simTime (every second accounted for)."""
    r = _run("PoCol", 100, 1, idle=True)
    n, sim = 100, r["sim_time"]
    active_s = (r["pct_time_active"] / 100.0) * n * sim
    assert math.isclose(active_s + r["idle_miner_seconds"], n * sim, rel_tol=1e-6)


def test_flag_on_is_deterministic():
    a = _run("PoCol", 100, 3, idle=True)
    out = subprocess.run(
        [sys.executable, os.path.join(ROOT, "experiments", "run_scenario_idle.py"),
         "PoCol", "100", "3", "1"], capture_output=True, text=True, cwd=ROOT)
    b = json.loads(out.stdout.strip().splitlines()[-1])
    assert a == b


def test_unit_pause_until_next_slot():
    """Unit-level: pause powers miners to 0 W until the next slot boundary and the
    idle window is charged at exactly 0 J."""
    from InputsConfig import InputsConfig as p
    from Models.PoCol.Node import Node as PoColNode
    from Models.PoCol.Consensus import Consensus as C

    p.model = 3
    p.HashPowerIsShare = True
    p.NetworkHashRate_Hps = 141e12
    p.MinerEfficiency_J_per_TH = 21.5
    p.GridEF_kgCO2e_per_kWh = 0.445
    p.simTime = 10000.0
    p.Binterval = 600.0
    p.PoCol_IdleAfterRange = True
    p.NODES = [PoColNode(id=i, hashPower=1) for i in range(4)]
    C.next_slot_start = 0.0
    for nd in p.NODES:
        nd.begin_mining(0.0)

    C.pause_miners_until_next_slot(250.0)          # mid-slot close
    assert C.next_slot_start == 600.0
    nd = p.NODES[0]
    e_at_close = nd.cumulative_energy_j
    assert e_at_close > 0.0                        # ACTIVE [0,250] was charged
    # idle window [250,600) charged at 0 W; miner re-armed ACTIVE at 600
    assert math.isclose(nd.cumulative_energy_j, e_at_close)
    assert nd.last_energy_update_time == 600.0
    assert nd.mining_state == "ACTIVE"
    assert math.isclose(nd.pocol_idle_time_s, 350.0)
    # cleanup so other tests see the default-OFF flag
    p.PoCol_IdleAfterRange = False
    C.next_slot_start = 0.0


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
