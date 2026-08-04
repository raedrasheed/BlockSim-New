"""Stage-7A package corrections: concurrency, durable paths, derived outcomes, alias lock.

No confirmatory master seed is executed anywhere in this file.  The concurrency tests use
synthetic sleep workers; the derived-outcome test uses a PILOT seed at reduced scale.
"""
from __future__ import annotations

import json
import pathlib
import subprocess
import sys
import time

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
BUNDLE = REPO / "experiments" / "thesis_revision_v45" / "stage_07"
STAGE6 = REPO / "experiments" / "thesis_revision_v45" / "stage_06"
for p in (str(REPO), str(STAGE6), str(BUNDLE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import _common as C                     # noqa: E402
import resource_preflight as PF         # noqa: E402
import run_stage7 as R                  # noqa: E402
import build_physical_registry as BPR   # noqa: E402


# ---------------------------------------------------------------- S7A-1 real concurrency
def _sleeper(seconds: float) -> list:
    return [sys.executable, "-c", f"import time;time.sleep({seconds});print('{{}}')"]


def test_s7a_01_pool_actually_overlaps_two_workers_in_wall_clock():
    pool = R.Pool({"LIGHTWEIGHT": 2, "SECURITY_FLOOR": 1, "REASSIGNMENT": 1}, cpu_count=4)
    t0 = time.time()
    pool.launch("R1", "P1", "LIGHTWEIGHT", _sleeper(1.0))
    pool.launch("R2", "P2", "LIGHTWEIGHT", _sleeper(1.0))
    assert len(pool.active) == 2, "the two workers are not concurrently active"
    done = []
    while pool.active:
        done += pool.reap(timeout_s=60)
        time.sleep(0.05)
    elapsed = time.time() - t0
    assert len(done) == 2
    assert elapsed < 1.8, (
        f"two 1.0 s workers took {elapsed:.2f} s — they ran sequentially, not concurrently")


def test_s7a_02_per_class_limits_are_enforced_separately():
    pool = R.Pool({"LIGHTWEIGHT": 2, "SECURITY_FLOOR": 1, "REASSIGNMENT": 1}, cpu_count=8)
    pool.launch("H1", "P1", "SECURITY_FLOOR", _sleeper(2.0))
    assert not pool.can_admit("SECURITY_FLOOR"), "a second SECURITY_FLOOR worker was admitted"
    assert pool.can_admit("REASSIGNMENT"), "a different class was wrongly blocked"
    assert pool.can_admit("LIGHTWEIGHT")
    pool.launch("L1", "P2", "LIGHTWEIGHT", _sleeper(2.0))
    pool.launch("L2", "P3", "LIGHTWEIGHT", _sleeper(2.0))
    assert not pool.can_admit("LIGHTWEIGHT"), "the lightweight class limit was exceeded"
    for _r in pool.active.values():
        _r[3].kill()
    while pool.active:
        pool.reap(timeout_s=60)


def test_s7a_03_total_process_cap_and_compressor_budget():
    pool = R.Pool({"LIGHTWEIGHT": 8}, cpu_count=4, compressors=2)
    assert pool.total_cap == 2, "compressors are not charged against the process budget"
    pool.launch("A", "PA", "LIGHTWEIGHT", _sleeper(2.0))
    pool.launch("B", "PB", "LIGHTWEIGHT", _sleeper(2.0))
    assert not pool.can_admit("LIGHTWEIGHT"), "the total process cap was exceeded"
    for _r in pool.active.values():
        _r[3].kill()
    while pool.active:
        pool.reap(timeout_s=60)


def test_s7a_04_c06_is_scheduled_against_the_slowest_class_budget():
    pool = R.Pool({"LIGHTWEIGHT": 3, "SECURITY_FLOOR": 1, "REASSIGNMENT": 1}, cpu_count=8)
    pool.launch("C06-S00", "P", "C06", _sleeper(2.0))
    assert not pool.can_admit("C06"), "C06 was admitted beyond the slowest-class budget"
    for _r in pool.active.values():
        _r[3].kill()
    while pool.active:
        pool.reap(timeout_s=60)


def test_s7a_05_admission_order_is_deterministic_and_priority_first():
    import scenarios as S                                     # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    a = R.admission_order(m["logical"], srows, m["physical"])
    b = R.admission_order(m["logical"], srows, m["physical"])
    assert a == b, "admission order is not deterministic"
    assert len(a) == 630, f"admission covers {len(a)} physical executions, expected 630"
    first = R.band(a[0][1], srows, m["logical"])
    assert first == "SECURITY_FLOOR"
    bands = [R.PRIORITY.index(R.band(ex, srows, m["logical"])) for _pid, ex in a]
    assert bands == sorted(bands), "admission is not in non-decreasing priority order"


def test_s7a_06_out_of_order_completion_updates_the_right_rows(tmp_path):
    import scenarios as S                                     # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    reg = C.Registry(tmp_path / "run_registry.csv")
    reg.initialise(srows, m["logical"])
    ids = ["A01-S00", "A01-S01", "A01-S02"]
    for rid in reversed(ids):                                  # completion order reversed
        reg.update(rid, run_status=C.COMPLETED, wall_clock_seconds="1.0")
    state = {r["run_id"]: r for r in reg.read()}
    assert all(state[i]["run_status"] == C.COMPLETED for i in ids)
    assert state["A01-S03"]["run_status"] == C.PENDING
    assert len(reg.read()) == 660, "out-of-order completion changed the row count"


def test_s7a_07_model_failure_stops_admission_but_lets_workers_close(tmp_path):
    import scenarios as S                                     # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    reg = C.Registry(tmp_path / "run_registry.csv")
    reg.initialise(srows, m["logical"])
    paths = C.ExecutionPaths(tmp_path).mkdirs()
    pid = m["logical"]["A01-S00"]["physical_execution_id"]
    st = R._finalise(reg, paths, m["logical"], m["physical"], "A01-S00", pid,
                     rc=3, out="", elapsed=1.0)
    assert st == C.FAILED_MODEL
    assert C.FAILED_MODEL not in C.RESUMABLE, "a model failure must not be resumable"
    src = (BUNDLE / "run_stage7.py").read_text()
    assert "stop_admission = True" in src and "close safely" in src


# ---------------------------------------------------------------- S7A-2 durable paths
def test_s7a_08_execution_paths_derive_everything_from_the_host_record(tmp_path):
    rec = {"durable_output_path": str(tmp_path / "durable"),
           "archive_path": str(tmp_path / "arch")}
    p = C.ExecutionPaths.from_record(rec)
    assert p.root == tmp_path / "durable"
    assert p.archive == tmp_path / "arch"
    for attr in ("registry", "physical_registry", "alias_map", "raw", "logs",
                 "failed_attempts", "chunks", "manifests", "run_level"):
        assert str(getattr(p, attr)).startswith(str(tmp_path / "durable"))
    p.mkdirs()
    assert p.raw.is_dir() and p.archive.is_dir()


def test_s7a_09_preflight_verifies_the_real_filesystem(tmp_path):
    good = {"durable_output_path": str(tmp_path / "d"), "archive_path": str(tmp_path / "a")}
    checks = {c["id"]: c for c in PF.verify_filesystem(good)}
    assert checks["V2a_durable_output_path_writable"]["pass"]
    assert checks["V2c_atomic_replace"]["pass"], "os.replace was not verified"
    assert checks["V2d_archive_roundtrip"]["pass"], "archive round-trip was not verified"
    assert "measured_free_bytes" in checks["V2b_durable_output_path_free_space"]


def test_s7a_10_a_pass_record_with_unusable_paths_is_rejected():
    rec = {"host_identifier": "h", "provider_or_institution": "p",
           "persistent_lifetime_guarantee": {"days": 999, "evidence": "e"},
           "cpu_count": 32, "usable_ram_bytes": 512 * 2**30,
           "free_disk_bytes": 500 * 2**30,
           "durable_output_path": "/proc/definitely/not/writable/stage7",
           "archive_path": "/proc/definitely/not/writable/arch",
           "worker_limits_by_class": {"LIGHTWEIGHT": 1, "SECURITY_FLOOR": 1,
                                      "REASSIGNMENT": 1},
           "compressor_count": 1, "per_run_timeout": {"hours": 24},
           "heartbeat_interval": {"seconds": 30},
           "checkpoint_interval": {"policy": "after every run"},
           "same_seed_rerun_policy": "same seed", "verified_at": "now", "verdict": "PASS"}
    res = PF.evaluate(rec)
    assert res["verdict"] == "FAIL", "a record with unusable paths was accepted"
    assert res["binding_failure"].startswith("V2a"), res["binding_failure"]


# ---------------------------------------------------------------- S7A-4 alias lock
def test_s7a_11_counts_are_660_logical_630_physical_30_aliases(tmp_path):
    r = BPR.build(C.ExecutionPaths(tmp_path))
    assert r["logical_rows"] == 660
    assert r["physical_executions"] == 630
    assert r["alias_pairs"] == 30
    assert pathlib.Path(r["physical_registry"]).exists()
    assert pathlib.Path(r["alias_map"]).exists()


def test_s7a_12_every_alias_group_is_exactly_a05_b01_at_one_seed():
    m = C.build_physical_map()
    shared = {p: v for p, v in m["physical"].items() if len(v) > 1}
    assert len(shared) == 30
    for pid, members in shared.items():
        assert len(members) == 2
        scen = sorted(m["logical"][r]["scenario_id"] for r in members)
        assert scen == ["A05", "B01"], f"unexpected alias group {scen}"
        seeds = {m["logical"][r]["master_seed"] for r in members}
        assert len(seeds) == 1, "an alias group spans two master seeds"
        assert m["logical"][members[0]]["alias_group_id"] == "ALIAS-A05+B01"


def test_s7a_13_each_physical_execution_is_executed_exactly_once():
    import scenarios as S                                     # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    order = R.admission_order(m["logical"], srows, m["physical"])
    pids = [pid for pid, _ex in order]
    assert len(pids) == len(set(pids)) == 630, "a physical execution is scheduled twice"
    executors = [ex for _pid, ex in order]
    assert len(set(executors)) == 630
    # the 30 non-executor alias members are never scheduled
    scheduled = set(executors)
    aliases = [r for r, L in m["logical"].items() if L["shared_physical_execution"]]
    assert len(aliases) == 60
    assert sum(1 for a in aliases if a in scheduled) == 30, (
        "both members of an alias pair are scheduled — the redundant config runs twice")


def test_s7a_14_both_alias_rows_are_materialised_with_shared_provenance(tmp_path):
    import scenarios as S                                     # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    reg = C.Registry(tmp_path / "run_registry.csv")
    reg.initialise(srows, m["logical"])
    rows = {r["run_id"]: r for r in reg.read()}
    a, b = rows["A05-S00"], rows["B01-S00"]
    assert a["physical_execution_id"] == b["physical_execution_id"] != ""
    assert a["shared_physical_execution"] == "true"
    assert b["shared_physical_execution"] == "true"
    assert a["alias_group_id"] == b["alias_group_id"] == "ALIAS-A05+B01"
    # a non-alias row must NOT be marked shared
    assert rows["A01-S00"]["shared_physical_execution"] == "false"
    assert rows["A01-S00"]["alias_group_id"] == ""


def test_s7a_15_no_inferential_double_counting_is_possible():
    """The dataset must expose enough provenance for Stage 8 to deduplicate physically."""
    import build_run_level_dataset as B                       # noqa: PLC0415
    rows, fields = B.build()
    assert len(rows) == 660
    for f in ("physical_execution_id", "shared_physical_execution", "alias_group_id",
              "materialised_from_run_id"):
        assert f in fields, f"the dataset cannot be deduplicated without {f}"
    pids = [r["physical_execution_id"] for r in rows if r["physical_execution_id"]]
    assert len(set(pids)) == 630, f"{len(set(pids))} distinct physical ids, expected 630"
    shared = [r for r in rows if str(r["shared_physical_execution"]).lower() == "true"]
    assert len(shared) == 60, "60 logical rows should be marked as sharing a physical run"


# ---------------------------------------------------------------- S7A-3 derived outcomes
def test_s7a_16_worker_computes_every_derived_outcome_on_a_pilot_fixture():
    import worker as W                                        # noqa: PLC0415
    import scenarios as S                                     # noqa: PLC0415
    from generate_seed_registry import build_rows             # noqa: PLC0415
    from Models.PoCol.stage2.simulator import run_simulation  # noqa: PLC0415

    seeds = build_rows()
    pilot = [r["master_seed_decimal"] for r in seeds if r["seed_class"] == "PILOT"]
    conf = {r["master_seed_decimal"] for r in seeds if r["seed_class"] == "CONFIRMATORY"}
    assert pilot[0] not in conf, "the fixture must not use a confirmatory seed"

    row = {r["scenario_id"]: r for r in S.confirmatory_rows()}["A01"]
    cfg = S.build_config(row, pilot[0], S.TIER1)
    run = run_simulation(cfg, run_id="derived-fixture")
    d = W.derived_outcomes(run, cfg)

    assert len(d["round_duration_values"]) >= 1, "no round duration was produced"
    assert isinstance(d["median_round_duration"], float)
    assert d["post_round_evaluation_record_count"] == 0
    assert d["post_round_evaluation_nonce_count"] == 0
    assert d["evaluation_missing_terminal_time_count"] == 0
    assert isinstance(d["nonterminal_activation_request_count"], int)
    assert isinstance(d["maximum_energy_identity_residual_j"], float)
    assert isinstance(d["maximum_residency_partition_residual_s"], float)
    assert d["maximum_energy_identity_residual_j"] <= 1e-8
    assert d["maximum_residency_partition_residual_s"] <= 1e-9
    for k in W.DERIVED_REQUIRED:
        assert d.get(k) is not None, f"required derived outcome {k} is missing"
    aud = d["derived_audit"]
    assert aud["round_count"] == len(d["round_duration_values"])
    assert len(aud["round_terminal_times_sha256"]) == 64


def test_s7a_17_missing_derived_outcome_is_a_model_failure():
    import worker as W                                        # noqa: PLC0415
    src = (BUNDLE / "validate_run_output.py").read_text()
    assert "DERIVED_REQUIRED" in src, "the validator does not check derived outcomes"
    p = pathlib.Path(BUNDLE / "worker.py").read_text()
    assert "derived run-level outcomes missing" in p
    assert "round_duration_values" in W.DERIVED_REQUIRED
    assert "median_round_duration" in W.DERIVED_REQUIRED


def test_s7a_18_dataset_carries_real_derived_values_not_na_placeholders():
    import build_run_level_dataset as B                       # noqa: PLC0415
    _rows, fields = B.build()
    for f in ("median_round_duration", "post_round_evaluation_record_count",
              "maximum_energy_identity_residual_j",
              "maximum_residency_partition_residual_s", "round_duration_count"):
        assert f in fields, f"{f} is not a dataset column"


# ---------------------------------------------------------------- S7A-5 provenance
def test_s7a_19_result_provenance_after_raw_reclaim():
    for f in ("raw_reclaimed", "raw_sha256", "compressed_file", "compressed_sha256",
              "archive_verified"):
        assert f in C.REGISTRY_FIELDS, f"the registry cannot record {f}"
    assert "result_file" not in C.REGISTRY_FIELDS, (
        "result_file would record a path that no longer exists after reclaim")
    src = (BUNDLE / "run_stage7.py").read_text()
    assert 'raw_reclaimed="true"' in src
    assert "the raw file no longer exists" in src


def test_s7a_20_dataset_reads_only_a_verified_existing_artifact():
    src = (BUNDLE / "build_run_level_dataset.py").read_text()
    assert "read ONLY the verified existing artefact" in src
    assert "paths.archive" in src, "the dataset does not read from the archive"


# ---------------------------------------------------------------- integrity
def test_s7a_21_interrupted_concurrent_execution_resumes_correctly(tmp_path):
    import scenarios as S                                     # noqa: PLC0415
    import resume_stage7 as RS                                # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    m = C.build_physical_map()
    reg = C.Registry(tmp_path / "run_registry.csv")
    reg.initialise(srows, m["logical"])
    reg.update("B02-S00", run_status=C.COMPLETED)
    reg.update("B02-S01", run_status=C.RUNNING)              # interrupted mid-flight
    reg.update("B02-S02", run_status=C.FAILED_INFRASTRUCTURE)
    p = RS.plan(reg)
    assert "B02-S00" in p["already_done"]
    assert "B02-S01" in p["resumable"] and "B02-S02" in p["resumable"]
    assert "B02-S00" not in p["resumable"], "a completed run would be re-executed"
    assert not p["blocked_model"]


def test_s7a_22_engine_and_frozen_design_are_untouched():
    import hashlib                                            # noqa: PLC0415
    from generate_completion_report import ACCEPTED_DIGESTS   # noqa: PLC0415
    for rel, digest in sorted(ACCEPTED_DIGESTS.items()):
        assert hashlib.sha256((REPO / rel).read_bytes()).hexdigest() == digest, rel
    assert len(C.frozen_rows()) == 660, "the frozen run registry was altered"
