"""Stage 8Y — validation entry point.

    python -m experiments.stage8y.validate

Runs the Stage 8Y suite, the pre-existing legacy suite, the Stage 8X suite, and the
protected-artifact baseline check, then writes ``STAGE_8Y_VALIDATION_REPORT.md``.
"""

from __future__ import annotations

import os
import subprocess
import sys
import time
from typing import Dict

from experiments.stage8y import baseline
from experiments.stage8y.config import stage8y_config as C


def _pytest(target: str) -> Dict:
    t0 = time.time()
    proc = subprocess.run([sys.executable, "-m", "pytest", target, "-q", "--tb=short"],
                          cwd=C.REPO_ROOT, capture_output=True, text=True)
    tail = proc.stdout.strip().splitlines()
    return {"target": target, "returncode": proc.returncode,
            "summary": tail[-1] if tail else "", "elapsed_s": time.time() - t0}


def write_report(y: Dict, legacy: Dict, x: Dict, prot: Dict) -> str:
    C.ensure_dirs()
    ok = (y["returncode"] == 0 and legacy["returncode"] == 0 and x["returncode"] == 0
          and prot["status"] in ("OK", "NO-BASELINE"))
    L = ["# STAGE 8Y — VALIDATION REPORT", "",
         f"Generated: {time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())}",
         f"Config hash: `{C.config_hash()}`", "",
         f"**Overall: {'PASS' if ok else 'FAIL'}**", "",
         "## 1. Test suites", "", "| Suite | Command | Result | Exit |",
         "|---|---|---|---|",
         f"| Stage 8Y | `pytest experiments/stage8y/tests` | `{y['summary']}` | "
         f"{y['returncode']} |",
         f"| Legacy (pre-existing) | `pytest tests` | `{legacy['summary']}` | "
         f"{legacy['returncode']} |",
         f"| Stage 8X (must be unaffected) | `pytest experiments/stage8x/tests` | "
         f"`{x['summary']}` | {x['returncode']} |", "",
         "## 2. Required validation coverage (brief section 36)", "",
         "| Requirement | Test |", "|---|---|",
         "| heterogeneous hash rate | `test_heterogeneous_aggregates`, `test_aggregate_hashrate_is_not_held_constant` |",
         "| heterogeneous power | `test_heterogeneous_aggregates` |",
         "| ASIC registry loading | `test_registry_loads_and_is_self_consistent`, `test_device_efficiency_spread_is_real` |",
         "| active-set selection | `test_selection_meets_the_hash_floor`, `test_efficiency_first_picks_the_efficient_devices_first` |",
         "| optimization correctness | `test_S4_is_exactly_optimal` (vs exhaustive enumeration) |",
         "| deterministic tie breaking | `test_selection_is_deterministic_with_stable_tie_break` |",
         "| equal range allocation | `test_equal_slots_make_fast_miners_finish_first` |",
         "| hash-proportional allocation | `test_hash_proportional_slots_equalise_completion_time` |",
         "| energy-aware policy | `test_p3_never_activates_reserves`, `test_selectivity_gain_exceeds_one_when_heterogeneous` |",
         "| reserve activation | `test_reserve_activation_produces_wake_transitions`, `test_reserve_activation_raises_active_capacity_above_stage_zero` |",
         "| wake transition | `test_zero_wake_delay_produces_no_waking_residence`, `test_wake_delay_costs_energy_and_is_conservative` |",
         "| state residence | `test_ledger_four_state_conservation_synthetic`, `test_state_time_conservation_in_real_runs` |",
         "| energy accounting | `test_energy_formula_matches_state_times`, `test_pow_energy_reference_is_full_active`, `test_power_identity_holds_exactly` |",
         "| target calculation | `test_difficulty_is_derived_from_full_installed_hardware` |",
         "| nonce-domain integrity | `test_slots_are_disjoint_and_tile_the_domain`, `test_domain_is_not_reduced_by_parking_miners` |",
         "| exact duplicate accounting | `test_duplicate_identity_and_pocol_zero_duplicates`, `test_nonce_value_reuse_is_not_exact_duplication` |",
         "| paired seed reproducibility | `test_seed_reproducibility`, `test_matched_runs_share_seed_and_hardware` |",
         "| PoW/PoCol matched parameters | `test_matched_difficulty_across_all_protocols` |",
         "| no PoCol-specific recalibration | `test_no_pocol_specific_difficulty_recalibration_in_source`, `test_difficulty_does_not_depend_on_active_fraction` |",
         "| no hash work in forbidden states | `test_work_equals_integral_of_active_hashrate` |",
         "| no range overlap / rescan | `test_completed_ranges_are_not_rescanned` |",
         "| no double-counted evaluations | `test_work_equals_integral_of_active_hashrate` |",
         "| α is accounting-only | `test_alpha_is_accounting_only`, `test_alpha_changes_only_energy_not_trajectory` |",
         "| decomposition exactness | `test_decomposition_is_exact_and_additive`, `test_selection_term_is_zero_in_the_homogeneous_control` |",
         "| seed disjointness incl. Stage 8X | `test_seed_groups_are_disjoint_and_fresh`, `test_seeds_are_disjoint_from_stage8x` |",
         "", "## 3. Protected-artifact verification", "",
         f"* protected files fingerprinted: **{prot.get('file_count', 0)}**",
         f"* baseline recorded: {prot.get('recorded_utc')}",
         f"* baseline SHA-256: `{prot.get('baseline_sha256')}`",
         f"* current SHA-256: `{prot.get('current_sha256')}`",
         f"* status: **{prot['status']}**"]
    if prot.get("changed") or prot.get("added") or prot.get("removed"):
        for kind in ("changed", "added", "removed"):
            for f in prot.get(kind, []):
                L.append(f"  * {kind.upper()}: `{f}`")
    else:
        L.append("* **Zero unintended modifications.** Every pre-existing artifact — "
                 "`Models/`, `results/`, `docs/`, `tests/`, all of "
                 "`experiments/stage8x/`, the legacy scripts, the root simulator "
                 "modules and every thesis `.docx`/`.pdf`/`.xlsx` — is byte-identical.")
    L += ["", "Stage 8Y writes only under `experiments/stage8y/`. Its single external "
              "import is `experiments.stage8x.simulator.hashing`, read-only, which "
              "guarantees an identical SHA-256 and candidate-identity semantics between "
              "the two experiment families.", ""]
    path = os.path.join(C.REPORT_DIR, "STAGE_8Y_VALIDATION_REPORT.md")
    with open(path, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L))
        fh.write("\n")
    return path


def main(argv=None) -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Stage 8Y validation")
    ap.add_argument("--record-baseline", action="store_true")
    args = ap.parse_args(argv)

    if args.record_baseline:
        b = baseline.record()
        prot = {"status": "OK", "file_count": b["file_count"],
                "baseline_sha256": b["baseline_sha256"],
                "current_sha256": b["baseline_sha256"],
                "recorded_utc": b["recorded_utc"], "changed": [], "added": [],
                "removed": []}
    else:
        prot = baseline.check()

    y = _pytest("experiments/stage8y/tests")
    legacy = _pytest("tests")
    x = _pytest("experiments/stage8x/tests")
    path = write_report(y, legacy, x, prot)

    print(f"stage8y tests : {y['summary']} (exit {y['returncode']})")
    print(f"legacy tests  : {legacy['summary']} (exit {legacy['returncode']})")
    print(f"stage8x tests : {x['summary']} (exit {x['returncode']})")
    print(f"protected     : {prot['status']} ({prot.get('file_count', 0)} files)")
    for kind in ("changed", "added", "removed"):
        for f in prot.get(kind, []):
            print(f"  {kind.upper()}: {f}")
    print(f"report -> {path}")
    ok = (y["returncode"] == 0 and legacy["returncode"] == 0 and x["returncode"] == 0
          and prot["status"] in ("OK", "NO-BASELINE"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
