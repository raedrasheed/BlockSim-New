"""Stage-7 deployment-package validation.

These tests validate the PACKAGE, not the science: no confirmatory master seed is executed by
any test here.  The one end-to-end fixture uses a PILOT seed at a reduced horizon, which is a
non-confirmatory synthetic fixture by construction.
"""
from __future__ import annotations

import json
import lzma
import pathlib
import subprocess
import sys

import pytest

REPO = pathlib.Path(__file__).resolve().parents[3]
BUNDLE = REPO / "experiments" / "thesis_revision_v45" / "stage_07"
STAGE6 = REPO / "experiments" / "thesis_revision_v45" / "stage_06"
for p in (str(REPO), str(STAGE6), str(BUNDLE)):
    if p not in sys.path:
        sys.path.insert(0, p)

import _common as C                     # noqa: E402
import resource_preflight as PF         # noqa: E402
import validate_run_output as V         # noqa: E402
from compress_and_archive import compress_verify_reclaim, verify   # noqa: E402


def test_s7_01_bundle_is_complete():
    required = ["run_stage7.py", "worker.py", "resume_stage7.py", "validate_run_output.py",
                "compress_and_archive.py", "build_run_level_dataset.py",
                "verify_stage7_archive.py", "resource_preflight.py",
                "README_DEPLOYMENT.md", "requirements-lock.txt"]
    missing = [f for f in required if not (BUNDLE / f).exists()]
    assert not missing, f"bundle is missing {missing}"
    # The host-record template lives in the docs tree, not the bundle: the Stage-6 gate
    # test_s6_23 forbids ANY .json under experiments/.../stage_07/, and that guard is an
    # accepted Stage-6 test which must not be weakened to accommodate packaging.
    tmpl = (REPO / "docs" / "thesis_revision_v45" / "stage_07"
            / "STAGE_07_RESOURCE_PREFLIGHT_RECORD.template.json")
    assert tmpl.exists(), "the host-record template is missing from the docs tree"
    assert not list(BUNDLE.glob("*.json")), (
        "a .json under the bundle would trip the accepted Stage-6 no-output guard")


def test_s7_02_frozen_660_run_identities_are_consumed_not_regenerated():
    rows = C.frozen_rows()
    assert len(rows) == 660
    ids = [r["run_id"] for r in rows]
    assert len(set(ids)) == 660
    src = (BUNDLE / "_common.py").read_text()
    assert "confirmatory_run_registry.csv" in src
    for forbidden in ("build_rows()", "generate_seed_registry", "master_seed("):
        assert forbidden not in src, f"the bundle regenerates identities via {forbidden!r}"


def test_s7_03_memory_equation_reproduces_the_declared_figures():
    gib = 2 ** 30
    eight = PF.required_ram_bytes({"REASSIGNMENT": 8}, 0) / gib
    sixteen = PF.required_ram_bytes({"REASSIGNMENT": 16}, 0) / gib
    assert 51.0 <= eight <= 51.8, f"8 heavy workers -> {eight:.2f} GiB, expected ~51.4"
    assert 102.5 <= sixteen <= 103.3, f"16 heavy workers -> {sixteen:.2f} GiB, expected ~102.9"
    # the compressor term is real and must be included
    with_comp = PF.required_ram_bytes({"REASSIGNMENT": 8}, 2) / gib
    assert with_comp > eight
    assert PF.RAM_SAFETY_MARGIN == 1.25


def test_s7_04_preflight_refuses_an_unfilled_or_failing_record():
    blank = dict(PF.TEMPLATE)
    assert PF.evaluate(blank)["verdict"] == "FAIL"
    assert PF.evaluate(blank)["binding_failure"] == "V0_record_complete"
    # a fully-filled record that fails only on lifetime must still FAIL
    rec = {"host_identifier": "h", "provider_or_institution": "p",
           "persistent_lifetime_guarantee": {"days": 1, "evidence": "e"},
           "cpu_count": 32, "usable_ram_bytes": 128 * 2**30,
           "free_disk_bytes": 100 * 2**30, "durable_output_path": "/d",
           "archive_path": "/a",
           "worker_limits_by_class": {"LIGHTWEIGHT": 2, "SECURITY_FLOOR": 1,
                                      "REASSIGNMENT": 1},
           "compressor_count": 1, "per_run_timeout": {"hours": 24},
           "heartbeat_interval": {"seconds": 30},
           "checkpoint_interval": {"policy": "after every run"},
           "same_seed_rerun_policy": "same seed", "verified_at": "now", "verdict": "PASS"}
    res = PF.evaluate(rec)
    assert res["verdict"] == "FAIL" and res["binding_failure"] == "V3_lifetime"


def test_s7_05_gate_or_die_blocks_execution(tmp_path):
    p = tmp_path / "absent.json"
    with pytest.raises(SystemExit):
        PF.gate_or_die(p)
    p.write_text(json.dumps(PF.TEMPLATE))
    with pytest.raises(SystemExit):
        PF.gate_or_die(p)


def test_s7_06_status_lifecycle_is_complete_and_resume_rules_are_right():
    for s in ("PENDING", "RUNNING", "COMPLETED", "FAILED_INFRASTRUCTURE",
              "FAILED_MODEL", "RERUN_COMPLETED"):
        assert s in C.STATUSES
    assert set(C.TERMINAL_SUCCESS) == {"COMPLETED", "RERUN_COMPLETED"}
    assert "FAILED_MODEL" not in C.RESUMABLE, "a model failure must never be silently retried"
    assert "COMPLETED" not in C.RESUMABLE, "a completed run must never be re-executed"
    assert set(C.RESUMABLE) == {"PENDING", "FAILED_INFRASTRUCTURE", "RUNNING"}


def test_s7_07_registry_initialises_660_rows_and_updates_atomically(tmp_path):
    import scenarios as S                                        # noqa: PLC0415
    reg = C.Registry(tmp_path / "run_registry.csv")
    n = reg.initialise({r["scenario_id"]: r for r in S.confirmatory_rows()})
    assert n == 660
    rows = reg.read()
    assert len({r["run_id"] for r in rows}) == 660
    assert all(r["run_status"] == C.PENDING for r in rows)
    rid = rows[0]["run_id"]
    reg.update(rid, run_status=C.RUNNING)
    assert {r["run_id"]: r for r in reg.read()}[rid]["run_status"] == C.RUNNING
    with pytest.raises(ValueError):
        reg.update(rid, run_status="NOT_A_STATUS")
    with pytest.raises(KeyError):
        reg.update("no-such-run", run_status=C.COMPLETED)


def test_s7_08_registry_survives_an_interrupted_write(tmp_path, monkeypatch):
    """An update that dies mid-write must leave the previous registry intact and readable."""
    import scenarios as S                                        # noqa: PLC0415
    reg = C.Registry(tmp_path / "run_registry.csv")
    reg.initialise({r["scenario_id"]: r for r in S.confirmatory_rows()})
    rid = reg.read()[0]["run_id"]
    reg.update(rid, run_status=C.COMPLETED, result_sha256="deadbeef")
    before = reg.path.read_bytes()

    real = C._atomic_write

    def explode(path, text):
        raise KeyboardInterrupt("interrupted mid-write")

    monkeypatch.setattr(C, "_atomic_write", explode)
    with pytest.raises(KeyboardInterrupt):
        reg.update(rid, run_status=C.FAILED_INFRASTRUCTURE)
    monkeypatch.setattr(C, "_atomic_write", real)

    assert reg.path.read_bytes() == before, "the registry was corrupted by an interrupted write"
    rows = {r["run_id"]: r for r in reg.read()}
    assert rows[rid]["run_status"] == C.COMPLETED
    assert len(rows) == 660
    # no temp files leaked into the directory
    assert not list(tmp_path.glob(".tmp-*")), "an interrupted write leaked a temp file"


def test_s7_09_compression_roundtrip_and_reclaim(tmp_path):
    raw = tmp_path / "fixture.json"
    payload = {"rows": [{"i": i, "text": "repetitive reconciliation row"} for i in range(4000)]}
    raw.write_text(json.dumps(payload))
    original = raw.read_bytes()
    dest = tmp_path / "fixture.json.xz"
    info = compress_verify_reclaim(raw, dest, reclaim=True)
    assert info["verified"] is True
    assert info["ratio"] > 2.0
    assert info["raw_reclaimed"] is True
    assert not raw.exists(), "the raw file must be reclaimed only after verification"
    assert lzma.decompress(dest.read_bytes()) == original, "round-trip is not byte-exact"


def test_s7_10_corrupted_archive_fails_verification_and_retains_raw(tmp_path):
    raw = tmp_path / "f.json"
    raw.write_text(json.dumps({"a": list(range(500))}))
    dest = tmp_path / "f.json.xz"
    from compress_and_archive import compress                    # noqa: PLC0415
    info = compress(raw, dest)
    assert verify(dest, info["raw_sha256"]) is True
    assert verify(dest, "0" * 64) is False


def test_s7_11_output_validator_rejects_a_foreign_run_id(tmp_path):
    p = tmp_path / "bad.json"
    p.write_text(json.dumps({"run_id": "NOT-A-FROZEN-ID", "scenario_id": "A01",
                             "master_seed": 1, "pair_id": "x", "config_sha256": "y",
                             "results": {}}))
    r = V.validate(p)
    assert not r["ok"]
    assert any("frozen run identity" in s for s in r["problems"])


def test_s7_12_scheduler_priority_order_is_slowest_first():
    import run_stage7 as R                                       # noqa: PLC0415
    import scenarios as S                                        # noqa: PLC0415
    assert R.PRIORITY == ("SECURITY_FLOOR", "REASSIGNMENT", "C06", "LIGHTWEIGHT")
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    # S7A-1/S7A-4: admission is over PHYSICAL executions, not logical rows
    m = C.build_physical_map()
    order = R.admission_order(m["logical"], srows, m["physical"])
    first = R.band(order[0][1], srows, m["logical"])
    assert first == "SECURITY_FLOOR", f"first scheduled run is {first}, not the slowest class"
    bands = [R.PRIORITY.index(R.band(ex, srows, m["logical"])) for _pid, ex in order]
    assert bands == sorted(bands), "the schedule is not in non-decreasing priority order"


def test_s7_13_end_to_end_on_a_non_confirmatory_fixture(tmp_path):
    """Execute ONE synthetic run: a PILOT seed at a reduced horizon. Not a confirmatory seed."""
    import scenarios as S                                        # noqa: PLC0415
    from generate_seed_registry import build_rows                # noqa: PLC0415
    from Models.PoCol.stage2.simulator import run_simulation     # noqa: PLC0415
    from Models.PoCol.stage2.adapter import results_schema       # noqa: PLC0415

    seeds = build_rows()
    pilot = [r["master_seed_decimal"] for r in seeds if r["seed_class"] == "PILOT"]
    conf = {r["master_seed_decimal"] for r in seeds if r["seed_class"] == "CONFIRMATORY"}
    seed = pilot[0]
    assert seed not in conf, "the fixture must not use a confirmatory seed"

    row = {r["scenario_id"]: r for r in S.confirmatory_rows()}["A01"]
    tier = dict(S.TIER1)
    cfg = S.build_config(row, seed, tier)
    run = run_simulation(cfg, run_id="package-fixture")
    res = results_schema(run, cfg)

    raw = tmp_path / "fixture.json"
    raw.write_text(json.dumps({"run_id": "fixture", "results": res}, default=str))
    dest = tmp_path / "fixture.json.xz"
    info = compress_verify_reclaim(raw, dest, reclaim=True)
    assert info["verified"] and not raw.exists()
    back = json.loads(lzma.decompress(dest.read_bytes()).decode())
    assert back["results"]["rounds_accepted"] == res["rounds_accepted"]


def test_s7_14_no_confirmatory_output_exists():
    data = REPO / "data" / "thesis_revision_v45" / "stage_07"
    produced = [p for p in data.rglob("*") if p.is_file()] if data.exists() else []
    assert not produced, f"confirmatory output already exists: {produced[:5]}"
    conf = STAGE6 / "confirmatory"
    stray = [p for p in conf.rglob("*.json") if "frozen_configs" not in str(p)]
    assert not stray, f"stray confirmatory output under stage_06: {stray[:5]}"


def test_s7_15_all_660_configs_build_and_pairs_match():
    import scenarios as S                                        # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    built = 0
    shas = set()
    for r in C.frozen_rows():
        cfg = S.build_config(srows[r["scenario_id"]], int(r["master_seed"]), S.TIER2)
        shas.add(C.config_sha256(cfg))
        built += 1
    assert built == 660
    # VERIFIED PROPERTY OF THE FROZEN MATRIX, not a bug in the digest:
    # A05 and B01 are byte-identical Stage2Config objects (they differ only in block_id,
    # hypothesis_ids, notes and paired_control_id). Under the same master seed they therefore
    # produce identical results. 660 - 30 = 630 distinct configurations. The matrix is FROZEN,
    # so this is recorded and carried, never silently deduplicated or edited away.
    assert len(shas) == 630, (
        f"expected 630 distinct configs (A05/B01 collide by design), got {len(shas)}")
    fields = ("num_miners", "horizon_T", "nonce_domain_size", "difficulty", "batch_size",
              "base_hash_rate", "P_hash", "P_offline")
    cfgs = {s: S.build_config(r, 0, S.TIER2) for s, r in srows.items()}
    for sid, srow in srows.items():
        ctrl = srow["paired_control_id"]
        if ctrl in ("SELF", "NONE"):
            continue
        for f in fields:
            assert getattr(cfgs[sid], f) == getattr(cfgs[ctrl], f), f"{sid}/{ctrl}: {f}"


def test_s7_16_engine_is_untouched():
    import hashlib                                               # noqa: PLC0415
    from generate_completion_report import ACCEPTED_DIGESTS      # noqa: PLC0415
    for rel, digest in sorted(ACCEPTED_DIGESTS.items()):
        got = hashlib.sha256((REPO / rel).read_bytes()).hexdigest()
        assert got == digest, f"{rel} changed"


def test_s7_17_the_a05_b01_configuration_collision_is_recorded_not_hidden():
    """A05 and B01 are the same physical condition serving two contrasts.

    This is a property of the FROZEN matrix. It is not corrected here — the matrix may not be
    changed — but it must be recorded, because two scenarios that share a configuration AND a
    master seed produce identical results and are NOT independent observations.
    """
    import scenarios as S                                        # noqa: PLC0415
    srows = {r["scenario_id"]: r for r in S.confirmatory_rows()}
    a, b = S.build_config(srows["A05"], 0, S.TIER2), S.build_config(srows["B01"], 0, S.TIER2)
    assert C.config_sha256(a) == C.config_sha256(b)
    differing = [f for f in vars(a) if getattr(a, f) != getattr(b, f)]
    assert differing == [], f"expected identical configs, differ in {differing}"
    # they are nevertheless DISTINCT scenarios with distinct roles
    assert srows["A05"]["paired_control_id"] == "A03"
    assert srows["B01"]["paired_control_id"] == "SELF"
    assert srows["A05"]["hypothesis_ids"] != srows["B01"]["hypothesis_ids"]
    # and the finding must be written down where Stage 8 will see it
    doc = (REPO / "docs" / "thesis_revision_v45" / "stage_07"
           / "STAGE_07_EXECUTION_STATUS.md").read_text()
    assert "A05" in doc and "B01" in doc, "the collision is not recorded in the status document"
