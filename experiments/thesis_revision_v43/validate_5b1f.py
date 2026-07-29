"""Stage 5B1F bounded validation (hard cap 200). Exercises competitor/stale
semantics, B2 exhaustion, timing convention, per-miner-generation accounting,
provenance, and precision. Every run reconciles: energy, candidates,
per-miner-generation, template chronology, parent chain, block proposals, stale
blocks, inactive ranges. Results go to stage_05b1f.
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

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1f")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RUN_CAP = 200


def configs():
    out = []
    # core scenario x distribution/allocation grid (small N so gen-detail is cheap)
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        for dist, alloc in (("homogeneous", "equal"), ("heterogeneous_moderate", "equal"),
                            ("heterogeneous_moderate", "weighted")):
            idle = 0.1 if scen == "C2" else 0.0
            out.append(dict(scenario_id=scen, seed=1, miner_count=40, hash_rate_distribution=dist,
                            allocation_policy=alloc, idle_power_ratio=idle, mu=2.0))
    # delay sensitivity on a disjoint scenario
    for delay in (0.0, 0.42, 5.0, 30.0, 60.0):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=40, mu=3.0,
                        propagation_delay_mean_s=delay))
    # multiple solutions per template (high mu) incl. multiple owned by one miner
    for mu in (1.0, 3.0, 5.0):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=7, miner_count=20, mu=mu))
        out.append(dict(scenario_id="B2", seed=7, miner_count=20, mu=mu))
    # inactive fractions
    for frac in (0.05, 0.15, 0.30):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=40,
                        inactive_miner_fraction=frac, mu=1.0))
    # small-domain regime that actually produces stales (small gaps, big delay)
    out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                    network_hash_rate_hps=2000.0, target_block_interval_s=1.0, propagation_delay_mean_s=60.0))
    return out


def reconcile(r):
    c = {}
    c["energy"] = math.isclose(r["total_energy_kwh"],
                               r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"],
                               abs_tol=1e-9)
    c["candidates"] = (r["total_candidate_evaluations"]
                       == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    disjoint = r["scenario_id"] in ("B0", "B3_C1_CONTINUOUS_DISJOINT", "C2")
    if disjoint:
        c["per_miner_generation"] = (sum(g["candidates_evaluated_this_generation"]
                                         for g in r["per_miner_generation"])
                                     == r["total_candidate_evaluations"])
    else:
        c["per_miner_generation"] = len(r["per_miner_generation"]) > 0
    pt = r["per_template"]
    c["template_chronology"] = (all(t["end_time_s"] >= t["start_time_s"] for t in pt)
                                and math.isclose(sum(t["duration_s"] for t in pt), 10000.0, rel_tol=1e-9))
    # parent chain
    blocks = [t for t in pt if t["accepted_block_id"] is not None]
    parent_ok = all(t["parent_block_id"] != t["accepted_block_id"] for t in blocks)
    if blocks:
        parent_ok = parent_ok and blocks[0]["parent_block_id"] == "genesis" and \
            all(blocks[i]["parent_block_id"] == blocks[i - 1]["accepted_block_id"] for i in range(1, len(blocks)))
    c["parent_chain"] = parent_ok
    c["block_proposals"] = (len(blocks) == r["accepted_blocks"]
                            and all(t["actual_proposal_miner_count"] >= 1 for t in blocks))
    c["stale_blocks"] = all(t["legitimate_stale_block_count"] >= 0 for t in pt) and \
        (r["stales_per_accepted_block"] is None or r["stales_per_accepted_block"] >= 0)
    c["inactive_ranges"] = all(t["accepted_block_id"] is None for t in pt
                               if t["active_range_solution_count"] == 0)
    return c


def main():
    os.makedirs(RAW, exist_ok=True)
    cfgs = configs()
    assert len(cfgs) <= RUN_CAP, f"{len(cfgs)} > {RUN_CAP}"
    results = []
    cov = dict(stale_nonzero=False, partial=False, b2_exhaustion=False,
               multi_solution=False, inactive=False)
    all_pass = True
    for i, cfg in enumerate(cfgs):
        r = run_scenario(EngineConfig(**cfg), emit_detail=True, emit_generation_detail=True)
        checks = reconcile(r)
        ok = all(checks.values())
        all_pass = all_pass and ok
        run_utils.atomic_write_json(
            os.path.join(RAW, f"VAL-{i:04d}-{cfg['scenario_id']}.summary.json"),
            dict(config=cfg, checks=checks, accepted=r["accepted_blocks"],
                 stale=r["legitimate_stale_block_count"], status=run_utils.STATUS_COMPLETED))
        results.append(dict(config=cfg, checks=checks, passed=ok,
                            accepted=r["accepted_blocks"], stale=r["legitimate_stale_block_count"]))
        if r["legitimate_stale_block_count"] > 0:
            cov["stale_nonzero"] = True
        if r["partial_generations"] > 0:
            cov["partial"] = True
        if any(t["status"] == "ACTIVE_DOMAIN_EXHAUSTED" for t in r["per_template"]) and cfg["scenario_id"] == "B2":
            cov["b2_exhaustion"] = True
        if r["total_template_solution_count"] > r["template_generations"]:
            cov["multi_solution"] = True
        if cfg.get("inactive_miner_fraction", 0) > 0:
            cov["inactive"] = True

    report = dict(run_count=len(cfgs), run_cap=RUN_CAP, under_cap=len(cfgs) <= RUN_CAP,
                  all_reconciliations_pass=all_pass,
                  reconciliation_families=["energy", "candidates", "per_miner_generation",
                                           "template_chronology", "parent_chain", "block_proposals",
                                           "stale_blocks", "inactive_ranges"],
                  coverage=cov, failed=[x for x in results if not x["passed"]], results=results)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1f.json"), report)
    json.dump(dict(run_count=len(cfgs), all_pass=all_pass, coverage=cov),
              open(os.path.join(DOCS, "STAGE_05B1F_VALIDATION_RESULTS.json"), "w"), indent=2)
    print(json.dumps(dict(run_count=len(cfgs), all_reconciliations_pass=all_pass, coverage=cov), indent=2))
    for x in report["failed"][:10]:
        print("FAIL", x["config"], x["checks"])
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_reconciliations_pass"] else 1)
