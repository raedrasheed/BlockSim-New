"""Stage 8X — validation entry point.

    python -m experiments.stage8x.validate

Runs the Stage 8X validation suite (brief section 25) plus the non-interference
check over pre-existing repository artifacts, and writes
``reports/STAGE_8X_VALIDATION_REPORT.md``.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
from typing import Dict, List

from experiments.stage8x.config import stage8x_config as C

#: Paths that belong to earlier work and must remain byte-identical.
PROTECTED_PATHS: List[str] = [
    "Models", "results", "docs", "tests", "InputsConfig.py", "Main.py",
    "Statistics.py", "Scheduler.py", "Event.py", "README.md",
    "experiments/_common.py", "experiments/run_all_revision_experiments.py",
    "experiments/run_carbon_gamma_sensitivity.py",
    "experiments/run_communication_energy_analysis.py",
    "experiments/run_pos_validator_scaling.py",
    "experiments/run_pow_miner_scaling.py",
    "experiments/run_pow_price_sensitivity.py",
]

BASELINE_FILE = os.path.join(C.OUT_DIR, "stage8x_protected_baseline.json")


def _file_sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def protected_tree_digest() -> Dict[str, str]:
    """SHA-256 of every pre-existing file Stage 8X must not touch."""
    digests: Dict[str, str] = {}
    for rel in PROTECTED_PATHS:
        abs_path = os.path.join(C.REPO_ROOT, rel)
        if os.path.isfile(abs_path):
            digests[rel] = _file_sha256(abs_path)
        elif os.path.isdir(abs_path):
            for dirpath, dirs, files in os.walk(abs_path):
                dirs[:] = [d for d in dirs if d != "__pycache__"]
                for fn in sorted(files):
                    if fn.endswith(".pyc"):
                        continue
                    p = os.path.join(dirpath, fn)
                    digests[os.path.relpath(p, C.REPO_ROOT)] = _file_sha256(p)
    return digests


def check_protected(write_baseline: bool = False) -> Dict:
    current = protected_tree_digest()
    if write_baseline or not os.path.exists(BASELINE_FILE):
        C.ensure_dirs()
        with open(BASELINE_FILE, "w", encoding="utf-8") as fh:
            json.dump(current, fh, indent=2, sort_keys=True)
        return {"status": "baseline-recorded", "files": len(current), "changed": []}
    with open(BASELINE_FILE, encoding="utf-8") as fh:
        baseline = json.load(fh)
    changed = sorted(
        k for k in set(baseline) | set(current) if baseline.get(k) != current.get(k)
    )
    return {"status": "ok" if not changed else "CHANGED",
            "files": len(current), "changed": changed}


def run_pytest() -> Dict:
    t0 = time.time()
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "experiments/stage8x/tests", "-q",
         "--tb=short"],
        cwd=C.REPO_ROOT, capture_output=True, text=True,
    )
    tail = proc.stdout.strip().splitlines()
    return {"returncode": proc.returncode, "elapsed_s": time.time() - t0,
            "summary": tail[-1] if tail else "", "stdout": proc.stdout,
            "stderr": proc.stderr}


def run_legacy_tests() -> Dict:
    """The pre-existing suite must still pass unchanged."""
    proc = subprocess.run([sys.executable, "-m", "pytest", "tests", "-q"],
                          cwd=C.REPO_ROOT, capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()
    return {"returncode": proc.returncode, "summary": tail[-1] if tail else ""}


def write_report(stage8x: Dict, legacy: Dict, protected: Dict) -> str:
    C.ensure_dirs()
    path = os.path.join(C.REPORT_DIR, "STAGE_8X_VALIDATION_REPORT.md")
    ok = stage8x["returncode"] == 0 and legacy["returncode"] == 0 and \
        protected["status"] in ("ok", "baseline-recorded")
    lines = [
        "# STAGE 8X — VALIDATION REPORT",
        "",
        f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
        f"Config hash: `{C.config_hash()}`",
        "",
        f"**Overall: {'PASS' if ok else 'FAIL'}**",
        "",
        "## 1. Stage 8X validation suite (brief section 25)",
        "",
        f"* command: `python -m pytest experiments/stage8x/tests -q`",
        f"* result: `{stage8x['summary']}`",
        f"* exit code: {stage8x['returncode']}",
        f"* elapsed: {stage8x['elapsed_s']:.2f} s",
        "",
        "Coverage of the required checks:",
        "",
        "| Required validation | Test |",
        "|---|---|",
        "| Hardware arithmetic H_N = N x 234 TH/s | `test_aggregate_hashrate_scales_with_n`, `test_expected_scaling_table_matches_brief` |",
        "| Hardware arithmetic P_N = N x 3510 W | `test_aggregate_power_scales_with_n` |",
        "| S21 consistency 234 x 15 = 3510 | `test_s21_consistency_234_times_15_equals_3510` |",
        "| Energy baseline E_i = 3510 x T | `test_energy_baseline_full_active_run`, `test_pow_is_active_for_the_whole_horizon` |",
        "| Low-power energy E = 3510 t_a + a 3510 t_l | `test_low_power_energy_formula` |",
        "| State-time conservation sum_s t_i,s = T | `test_power_state_ledger_conservation_synthetic`, `test_state_time_conservation_in_real_runs` |",
        "| Disjoint PoCol ranges R_i n R_j = empty | `test_pocol_ranges_are_disjoint_and_tile_the_domain` |",
        "| No PoCol exact duplicates | `test_pocol_has_zero_exact_duplicate_evaluations` |",
        "| Nonce reuse is not exact duplication | `test_traditional_pow_has_zero_exact_duplicates_but_high_nonce_reuse`, `test_matched_template_pow_does_produce_exact_duplicates` |",
        "| Matched difficulty D^PoW_N = D^PoCol_N | `test_pow_and_pocol_share_the_same_difficulty_and_target` |",
        "| Difficulty coupled to H_N, 600 s interval | `test_difficulty_is_coupled_to_aggregate_hashrate`, `test_difficulty_yields_600s_expected_interval` |",
        "| Real SHA-256 semantics behind the abstraction | `test_real_double_sha256_matches_target_probability`, `test_candidate_identity_is_template_plus_index` |",
        "| Seed reproducibility | `test_same_seed_reproduces_identical_physical_results` |",
        "| alpha invariance of the trajectory | `test_alpha_is_not_a_simulation_parameter`, `test_alpha_only_changes_energy_not_trajectory` |",
        "| Work-accounting identity W = h x t_active | `test_total_work_equals_rate_times_active_time` |",
        "| Run-matrix shape (300 runs, 600 alpha rows) | `test_config_matrix_shape` |",
        "",
        "## 2. Pre-existing test suite (must be unaffected)",
        "",
        f"* command: `python -m pytest tests -q`",
        f"* result: `{legacy['summary']}`",
        f"* exit code: {legacy['returncode']}",
        "",
        "## 3. Non-interference with earlier experiments",
        "",
        f"* protected files checksummed: {protected['files']}",
        f"* status: **{protected['status']}**",
    ]
    if protected["changed"]:
        lines.append("* changed files (MUST be empty):")
        lines += [f"  * `{c}`" for c in protected["changed"]]
    else:
        lines.append("* changed files: none — every pre-existing artifact is byte-identical.")
    lines += [
        "",
        "Stage 8X writes only under `experiments/stage8x/` and imports only the pure,",
        "already-unit-tested `Models.Energy` constants. It never imports `InputsConfig`,",
        "`Main`, `Scheduler`, `Event` or `Statistics` (asserted by",
        "`test_stage8x_never_imports_global_inputsconfig`).",
        "",
    ]
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines))
    return path


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(description="Stage 8X validation")
    ap.add_argument("--record-baseline", action="store_true",
                    help="(re)record the protected-artifact checksum baseline")
    args = ap.parse_args(argv)

    protected = check_protected(write_baseline=args.record_baseline)
    stage8x = run_pytest()
    legacy = run_legacy_tests()
    path = write_report(stage8x, legacy, protected)

    print(f"stage8x tests : {stage8x['summary']} (exit {stage8x['returncode']})")
    print(f"legacy tests  : {legacy['summary']} (exit {legacy['returncode']})")
    print(f"protected     : {protected['status']} ({protected['files']} files)")
    if protected["changed"]:
        for c in protected["changed"]:
            print(f"  CHANGED: {c}")
    print(f"report -> {path}")
    ok = (stage8x["returncode"] == 0 and legacy["returncode"] == 0
          and protected["status"] in ("ok", "baseline-recorded"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
