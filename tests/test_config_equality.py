"""Phase B3 — the PoW and PoCol experimental configurations must be identical
except for explicitly justified, protocol-inherent parameters.

Run:  python -m pytest tests/ -v   or   python tests/test_config_equality.py
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from Models.scenario import (
    ScenarioConfig, effective_params, apply_to, non_protocol_difference,
    PROTOCOL_SPECIFIC,
)


def test_no_non_protocol_parameter_differs():
    for n in (100, 300, 500):
        sc = ScenarioConfig(n_miners=n, seed=1)
        diff = non_protocol_difference(sc)
        assert diff == set(), f"non-protocol parameters differ between PoW/PoCol: {diff}"


def test_workload_is_shared_single_source():
    """Tn (and the whole workload) comes from ONE field, so PoW==PoCol."""
    sc = ScenarioConfig(n_miners=200, seed=1)
    pw = effective_params(sc, "PoW")
    pc = effective_params(sc, "PoCol")
    for key in ("Tn", "Binterval", "Bsize", "Bdelay", "Tdelay", "Tfee", "Tsize",
                "NetworkHashRate_Hps", "MinerEfficiency_J_per_TH",
                "GridEF_kgCO2e_per_kWh", "simTime"):
        assert pw[key] == pc[key], f"{key} differs: PoW={pw[key]} PoCol={pc[key]}"


def test_only_documented_protocol_specifics_exist():
    """PoCol may add only nonce-partitioning parameters; PoW adds none."""
    assert PROTOCOL_SPECIFIC["PoW"] == {}
    allowed = {"PoCol_AutoNonceSpace", "PoCol_TargetInterval", "PoCol_AssignStrategy"}
    assert set(PROTOCOL_SPECIFIC["PoCol"]).issubset(allowed)


def test_apply_to_sets_identical_shared_values_on_inputsconfig():
    from InputsConfig import InputsConfig as p
    sc = ScenarioConfig(n_miners=300, seed=7)

    apply_to(p, sc, "PoW")
    pw = {k: getattr(p, k) for k in ("Tn", "Binterval", "Bsize", "Bdelay",
          "NetworkHashRate_Hps", "MinerEfficiency_J_per_TH", "simTime", "Nn")}
    apply_to(p, sc, "PoCol")
    pc = {k: getattr(p, k) for k in ("Tn", "Binterval", "Bsize", "Bdelay",
          "NetworkHashRate_Hps", "MinerEfficiency_J_per_TH", "simTime", "Nn")}
    assert pw == pc, f"apply_to produced diverging shared config: {pw} vs {pc}"


def test_config_hash_is_protocol_independent_and_seed_independent():
    a = ScenarioConfig(n_miners=100, seed=1)
    b = ScenarioConfig(n_miners=100, seed=2)     # different seed only
    c = ScenarioConfig(n_miners=200, seed=1)     # different N
    assert a.config_hash() == b.config_hash(), "hash must ignore seed"
    assert a.config_hash() != c.config_hash(), "hash must reflect N"


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
