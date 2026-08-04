"""Stage-6M validation tests.  No confirmatory master seed is executed here: every executed
fixture uses a PILOT seed."""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
B6M = REPO / "experiments" / "thesis_revision_v45" / "stage_06m"
S6 = REPO / "experiments" / "thesis_revision_v45" / "stage_06"
DOCS = REPO / "docs" / "thesis_revision_v45" / "stage_06m"
for p in (str(REPO), str(S6), str(B6M)):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M                                       # noqa: E402
from Models.PoCol.stage2.config import a1_continuous_control_kwh  # noqa: E402
from Models.PoCol.stage2.simulator import run_simulation       # noqa: E402
from Models.PoCol.stage2.adapter import results_schema         # noqa: E402


def test_s6m_01_core_config_and_a1_exact():
    M.assert_core_matches_directive()
    cfg = M.build_config_6m(M.CONFIRMATORY[0], 0)
    assert a1_continuous_control_kwh(cfg) == pytest.approx(0.035833333333333335, abs=1e-12)
    assert cfg.num_miners == 20 and cfg.horizon_T == 300.0
    assert cfg.nonce_domain_size == 1600 and cfg.difficulty == 1000 and cfg.batch_size == 25
    assert (cfg.P_hash, cfg.P_listen, cfg.P_reserve, cfg.P_wake, cfg.P_offline) == \
        (21.5, 2.15, 2.15, 10.75, 0.0)
    # disabled mechanisms stay at their defaults, i.e. genuinely disabled
    assert not cfg.range_lease.enabled
    assert not cfg.adversarial.enabled
    assert not cfg.incentive.enabled


def test_s6m_02_treatment_isolation():
    """M01 vs M02 differ ONLY in heterogeneity; M01 vs M03 ONLY in the floor fields."""
    a = M.build_config_6m(M.CONFIRMATORY[0], 0)      # M01
    b = M.build_config_6m(M.CONFIRMATORY[1], 0)      # M02
    c = M.build_config_6m(M.CONFIRMATORY[2], 0)      # M03
    d_ab = [f for f in vars(a) if getattr(a, f) != getattr(b, f)]
    assert d_ab == ["heterogeneous_hash_rates"], d_ab
    d_ac = sorted(f for f in vars(a) if getattr(a, f) != getattr(c, f))
    # floor_unattainable_policy is set explicitly to CONTINUE_DEGRADED, which is also the
    # engine default, so the ONLY differing field is the security_floor policy itself.
    assert d_ac == ["security_floor"], d_ac
    fl = c.security_floor
    assert fl.enabled and fl.minimum_active_hash_rate == pytest.approx(0.80 * 4000.0)
    assert fl.minimum_active_miner_count is None
    assert fl.reserve_selection_policy == "MINIMUM_CARDINALITY"
    assert fl.activation_trigger_mode == "ON_CAPACITY_CHANGE"
    assert fl.activation_wake_latency == 1.0 and fl.floor_tolerance == 0.0
    assert c.floor_unattainable_policy == "CONTINUE_DEGRADED"


def test_s6m_03_seeds_are_the_first_ten_confirmatory_and_pilot_disjoint():
    import generate_seed_registry as GSR                        # noqa: PLC0415
    rows = [r for r in GSR.build_rows() if r["seed_class"] == "CONFIRMATORY"]
    rows.sort(key=lambda r: int(r["seed_index"]))
    expected = [int(r["master_seed_decimal"]) for r in rows[:10]]
    got = M.confirmatory_seeds()
    assert got == expected, "the selected seeds are not the FIRST 10 confirmatory seeds"
    assert len(set(got)) == 10
    pilots = set(M.pilot_seeds())
    assert not (pilots & set(got))
    for i in M.STRUCTURAL_PILOT_SEED_INDEXES:
        assert M.pilot_seeds()[i] not in got


def _digests(run):
    led = tuple((r.RoundID, getattr(r, "MinerID", None), r.interval_start, r.interval_end,
                 round(r.completion_time, 9)) for r in run.evaluation_ledger)
    rtt = tuple(sorted((k, round(v, 9)) for k, v in run.round_terminal_times.items()))
    dur = tuple(sorted((m, tuple(sorted((s, round(d, 9))
                                        for s, d in run.miners[m].duration.items())))
                       for m in run.miners))
    return (hashlib.sha256(repr(led).encode()).hexdigest(),
            hashlib.sha256(repr(rtt).encode()).hexdigest(),
            hashlib.sha256(repr(dur).encode()).hexdigest(),
            hashlib.sha256(repr(run.log).encode()).hexdigest())


def test_s6m_04_idle_prices_change_energy_accounting_only():
    """THE required executable invariance proof for the within-run power null.

    Changing only P_listen / P_reserve / P_wake changes no round identity, no accepted block
    count, no winner sequence, no nonce evaluation ledger, no coverage and no terminal
    disposition — only the energy accounting.
    """
    from generate_seed_registry import child_seed               # noqa: PLC0415
    seed = M.pilot_seeds()[0]
    row = M.CONFIRMATORY[0]
    a = M.build_config_6m(row, seed)
    from dataclasses import replace                             # noqa: PLC0415
    b = replace(a, P_listen=a.P_hash, P_reserve=a.P_hash, P_wake=a.P_hash)
    ra = run_simulation(a, run_id="inv-A")
    rb = run_simulation(b, run_id="inv-B")
    res_a, res_b = results_schema(ra, a), results_schema(rb, b)
    da, db = _digests(ra), _digests(rb)
    assert da[0] == db[0], "nonce evaluation ledger changed"
    assert da[1] == db[1], "round identities / terminal times changed"
    assert da[2] == db[2], "residency changed"
    assert da[3] == db[3], "event log (winner sequence superset) changed"
    assert res_a["rounds_accepted"] == res_b["rounds_accepted"]
    assert res_a["run_disposition"] == res_b["run_disposition"]
    assert res_a["loop_result"] == res_b["loop_result"]
    for cov in ("coverage_gap_nonce_count", "uncovered_nonce_count"):
        assert res_a[cov] == res_b[cov]
    assert res_a["energy_kwh"] != res_b["energy_kwh"], "energy accounting did not change"
    # and the within-run E_power_null equals the pure-price run's actual energy
    pair = M.energy_pair_kwh(ra, a)
    assert pair["E_power_null_kwh"] == pytest.approx(res_b["energy_kwh"], abs=1e-12)
    assert pair["E_idle_kwh"] == pytest.approx(res_a["energy_kwh"], abs=1e-12)
    # zero offline residency -> E_power_null equals the analytic continuous control
    assert pair["offline_residency_s"] == 0.0
    assert pair["E_power_null_kwh"] == pytest.approx(
        a1_continuous_control_kwh(a), abs=1e-9)


def test_s6m_05_artifacts_regenerate_byte_identically():
    r = subprocess.run([sys.executable, str(B6M / "generate_6m.py"), "--check"],
                       capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_s6m_06_structural_pilot_passed_and_contains_no_energy_effect():
    p = B6M / "pilot" / "structural_pilot_results.json"
    assert p.exists(), "the structural pilot must run before the freeze"
    data = json.loads(p.read_text())
    assert data["all_structural_gates_pass"] is True
    assert len(data["results"]) == 6                            # 3 scenarios x 2 pilot seeds
    text = p.read_text()
    for forbidden in ("E_idle", "E_power_null", "relative_reduction",
                      "absolute_reduction", "energy_kwh"):
        assert forbidden not in text, f"pilot output leaks an energy effect: {forbidden}"
    for rec in data["results"]:
        assert rec["run_status"] == "COMPLETED"
        assert rec["rounds_executed"] >= 100
        assert rec["all_gates_pass"] is True


def test_s6m_07_matrix_counts_and_exploratory_exclusion():
    rows = list(__import__("csv").DictReader(
        (DOCS / "STAGE_06M_MINIMAL_MATRIX.csv").read_text().splitlines()))
    conf = [r for r in rows if r["role"] == "CONFIRMATORY"]
    expl = [r for r in rows if r["role"] == "EXPLORATORY_SCALE_CHECK"]
    assert len(conf) == 3 and len(expl) == 2
    assert all(r["range_leases"] == "DISABLED" for r in rows)
    assert all(r["adversarial_model"] == "DISABLED" for r in rows)
    assert all(r["incentive_model"] == "DISABLED" for r in rows)
    assert all(r["dynamic_difficulty"] == "FORBIDDEN" for r in rows)
    assert all(r["hypotheses"] == "NONE" for r in expl), \
        "an exploratory scale check is attached to a hypothesis"
    reg = list(__import__("csv").DictReader(
        (DOCS / "STAGE_06M_SEED_REGISTRY.csv").read_text().splitlines()))
    assert sum(1 for r in reg if r["seed_class"] == "CONFIRMATORY") == 10


def test_s6m_08_engine_and_previous_stages_untouched():
    from generate_completion_report import ACCEPTED_DIGESTS     # noqa: PLC0415
    for rel, digest in sorted(ACCEPTED_DIGESTS.items()):
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == digest, rel
    # the superseded Stage-6/Stage-7 artefacts remain as historical records at this base
    # commit (0725f068); the Stage-7A amendment lives on its own branch and is preserved there
    for kept in ("docs/thesis_revision_v45/stage_06/STAGE_06_PREREGISTRATION.md",
                 "docs/thesis_revision_v45/stage_06/STAGE_07_RESOURCE_PREFLIGHT_GATE.md",
                 "docs/thesis_revision_v45/stage_07/STAGE_07_EXECUTION_STATUS.md",
                 "experiments/thesis_revision_v45/stage_07/run_stage7.py",
                 "experiments/thesis_revision_v45/stage_06/scenarios.py"):
        assert (REPO / kept).exists(), f"historical record deleted: {kept}"


def test_s6m_09_supersession_notice_states_the_required_facts():
    text = (DOCS / "STAGE_06M_SUPERSESSION_NOTICE.md").read_text()
    for required in ("660 logical", "630 physical", "zero confirmatory seeds",
                     "measured compute infeasibility", "no effect size",
                     "superseded before data collection"):
        assert required.lower() in text.lower(), f"notice omits: {required}"
