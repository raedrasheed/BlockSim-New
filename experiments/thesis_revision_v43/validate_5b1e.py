"""Stage 5B1E bounded validation (hard cap 200 runs). Exercises inactive ranges,
exact per-miner accounting, lifecycle, and integer metrics; every run must pass six
reconciliations: energy, candidate, domain, time, block, inactive-range. Historical
outputs are untouched; results go to stage_05b1e.
"""

from __future__ import annotations
import os
import sys
import json
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import run_utils

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1e")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RUN_CAP = 200


def configs():
    out = []
    for scen in ("B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        for N in (10, 100, 500):
            for dist, alloc in (("homogeneous", "equal"),
                                ("heterogeneous_moderate", "equal"),
                                ("heterogeneous_moderate", "weighted")):
                for frac in (0.0, 0.05, 0.15, 0.30):
                    idle = 0.1 if scen == "C2" else 0.0
                    # keep the grid bounded: only vary inactive at N=100
                    if frac not in (0.0,) and N != 100:
                        continue
                    out.append(dict(scenario_id=scen, seed=1, miner_count=N,
                                    hash_rate_distribution=dist, allocation_policy=alloc,
                                    inactive_miner_fraction=frac, idle_power_ratio=idle,
                                    mu=(0.5 if (frac == 0.30) else 2.0)))
    return out


def reconcile(r):
    checks = {}
    # energy
    checks["energy"] = math.isclose(r["total_energy_kwh"],
                                    r["active_energy_kwh"] + r["idle_energy_kwh"]
                                    + r["coordination_energy_kwh"], abs_tol=1e-9)
    # candidate (exact integer)
    checks["candidate"] = (r["total_candidate_evaluations"]
                           == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    # domain (per template)
    checks["domain"] = all(t["assigned_domain_size"] == (t["searched_domain_size"]
                           + t["unsearched_domain_size"] + t["inactive_domain_size"])
                           for t in r["per_template"])
    # time (per-template durations tile the horizon)
    checks["time"] = math.isclose(sum(t["duration_s"] for t in r["per_template"]),
                                  10000.0, rel_tol=1e-9)
    # block (every accepted block has an active finder; count matches)
    blocks = [t for t in r["per_template"] if t["accepted_block_id"] is not None]
    checks["block"] = (len(blocks) == r["accepted_blocks"]
                       and all(t["active_range_solution_count"] >= 1 for t in blocks))
    # inactive-range (inactive-only generations never block; per-miner sum == total)
    checks["inactive_range"] = (all(t["accepted_block_id"] is None
                                    for t in r["per_template"] if t["active_range_solution_count"] == 0)
                                and sum(m["candidates_evaluated"] for m in r["per_miner"])
                                == r["total_candidate_evaluations"])
    return checks


def main():
    os.makedirs(RAW, exist_ok=True)
    cfgs = configs()
    assert len(cfgs) <= RUN_CAP, f"{len(cfgs)} > {RUN_CAP}"
    results = []
    coverage = dict(inactive_only_gen=False, partial_gen=False, early_winner=False,
                    nonzero_idle=False, zero_idle=False, no_active_solution=False)
    all_pass = True
    for i, c in enumerate(cfgs):
        r = run_scenario(EngineConfig(**c), emit_detail=True)
        checks = reconcile(r)
        ok = all(checks.values())
        all_pass = all_pass and ok
        run_utils.atomic_write_json(
            os.path.join(RAW, f"VAL-{i:04d}-{c['scenario_id']}-N{c['miner_count']}.summary.json"),
            dict(scenario=c, checks=checks, accepted=r["accepted_blocks"],
                 energy=r["total_energy_kwh"], status=run_utils.STATUS_COMPLETED))
        results.append(dict(config=c, checks=checks, passed=ok,
                            accepted=r["accepted_blocks"],
                            inactive_solutions=r["inactive_range_solution_count"]))
        # coverage flags
        if any(t["active_range_solution_count"] == 0 and t["total_template_solution_count"] > 0
               for t in r["per_template"]):
            coverage["inactive_only_gen"] = True
            coverage["no_active_solution"] = True
        if any(t["status"] == "PARTIAL_AT_CUTOFF" for t in r["per_template"]):
            coverage["partial_gen"] = True
        if r["accepted_blocks"] > 0:
            coverage["early_winner"] = True
        if r["total_idle_time_s"] > 0:
            coverage["nonzero_idle"] = True
        if c["scenario_id"] == "C2" and c["hash_rate_distribution"] == "homogeneous" and r["total_idle_time_s"] == 0:
            coverage["zero_idle"] = True

    report = dict(run_count=len(cfgs), run_cap=RUN_CAP, under_cap=len(cfgs) <= RUN_CAP,
                  all_reconciliations_pass=all_pass,
                  reconciliation_families=["energy", "candidate", "domain", "time", "block", "inactive_range"],
                  coverage=coverage, all_coverage_hit=all(coverage.values()),
                  failed=[x for x in results if not x["passed"]], results=results)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1e.json"), report)
    json.dump(dict(run_count=len(cfgs), all_pass=all_pass, coverage=coverage),
              open(os.path.join(DOCS, "STAGE_05B1E_VALIDATION_RESULTS.json"), "w"), indent=2)
    print(json.dumps(dict(run_count=len(cfgs), all_reconciliations_pass=all_pass,
                          coverage=coverage, all_coverage_hit=all(coverage.values())), indent=2))
    if report["failed"]:
        for x in report["failed"][:10]:
            print("FAIL", x["config"], x["checks"])
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_reconciliations_pass"] and rep["all_coverage_hit"] else 1)
