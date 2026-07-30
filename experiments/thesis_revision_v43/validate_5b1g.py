"""Stage 5B1G bounded validation (hard cap 150). Exercises the single-height
stale-race diagnostic (one stale per miner per height, NO global cap; multiple
distinct producers per height), the per-delivery propagation-delay stream, the
actual/potential taxonomy, the solution-position/finder taxonomy and the EXACT B2
exhaustion closure. Every run reconciles across TEN families. The full 1 890-run
matrix is NOT executed. Results go to stage_05b1g.
"""

from __future__ import annotations
import os
import sys
import json
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import (
    EngineConfig, run_scenario, _delivery_delay)
from experiments.thesis_revision_v43 import run_utils, schemas

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1g")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RUN_CAP = 150

DISJOINT = {"B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"}

# a small-domain, high-delay regime that yields MANY distinct stale producers per height
MULTI_STALE = dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                   network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                   propagation_delay_mean_s=60.0)


def configs():
    out = []
    # core scenario x distribution/allocation grid
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        for dist, alloc in (("homogeneous", "equal"), ("heterogeneous_moderate", "equal"),
                            ("heterogeneous_moderate", "weighted")):
            out.append(dict(scenario_id=scen, seed=1, miner_count=40, hash_rate_distribution=dist,
                            allocation_policy=alloc, idle_power_ratio=(0.1 if scen == "C2" else 0.0),
                            mu=2.0))
    # propagation-delay sweep on a disjoint scenario (0, 0.42, 5, 30, 60)
    for delay in (0.0, 0.42, 5.0, 30.0, 60.0):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=40, mu=3.0,
                        propagation_delay_mean_s=delay))
    # multiple solutions per template incl. several owned by one miner (few miners, high mu)
    for mu in (1.0, 3.0, 5.0):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=7, miner_count=5, mu=mu))
        out.append(dict(scenario_id="B2", seed=7, miner_count=8, mu=mu))
    # inactive fractions
    for frac in (0.05, 0.15, 0.30):
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=40,
                        inactive_miner_fraction=frac, mu=1.0))
    # controlled MULTI-STALE-PRODUCER regime (>=2 and >=3 distinct producers per height)
    out.append(dict(**MULTI_STALE))
    out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=9, miner_count=15, mu=4.0,
                    network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                    propagation_delay_mean_s=30.0))
    # B2 low-mu exhaustion regime (exact circular exhaustion generations)
    for seed in (11, 12):
        out.append(dict(scenario_id="B2", seed=seed, miner_count=8, mu=0.5))
    # partial cutoff (long block interval so the final generation is interrupted)
    out.append(dict(scenario_id="B1", seed=20260201, miner_count=100,
                    target_block_interval_s=9000.0, mu=2.0))
    return out


def reconcile(r, cfg):
    disjoint = r["scenario_id"] in DISJOINT
    c = {}
    c["energy"] = math.isclose(r["total_energy_kwh"],
                               r["active_energy_kwh"] + r["idle_energy_kwh"]
                               + r["coordination_energy_kwh"], abs_tol=1e-9)
    c["candidates"] = (r["total_candidate_evaluations"]
                       == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    if disjoint:
        c["per_miner_generation"] = (sum(g["candidates_evaluated_this_generation"]
                                         for g in r["per_miner_generation"])
                                     == r["total_candidate_evaluations"])
    else:
        c["per_miner_generation"] = len(r["per_miner_generation"]) > 0
    pt = r["per_template"]
    c["template_chronology"] = (all(t["end_time_s"] >= t["start_time_s"] for t in pt)
                                and math.isclose(sum(t["duration_s"] for t in pt), 10000.0, rel_tol=1e-9))
    blocks = [t for t in pt if t["accepted_block_id"] is not None]
    parent_ok = all(t["parent_block_id"] != t["accepted_block_id"] for t in blocks)
    if blocks:
        parent_ok = parent_ok and blocks[0]["parent_block_id"] == "genesis" and \
            all(blocks[i]["parent_block_id"] == blocks[i - 1]["accepted_block_id"]
                for i in range(1, len(blocks)))
    c["parent_chain"] = parent_ok
    c["block_proposals"] = (len(blocks) == r["accepted_blocks"]
                            and all(t["actual_proposal_miner_count"] == 1 + t["stale_block_count"]
                                    for t in blocks))
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    c["stale_diagnostic"] = schemas.reconcile_stale_diagnostic(r, pt, n_active=n_active)["passed"]
    c["solution_positions"] = schemas.reconcile_solution_positions(pt, disjoint=disjoint)["passed"]
    # exact B2 exhaustion closure on every B2 exhaustion generation
    exh = [t for t in pt if t.get("exact_exhaustion_verified") is not None]
    c["b2_exhaustion"] = all(t["exact_exhaustion_verified"] is True
                             and t["coverage_at_exhaustion"] == r["domain_size"]
                             and t["coverage_before_exhaustion"] < r["domain_size"] for t in exh)
    # delay-stream reproducibility (recorded delay reconstructs from the delivery identity)
    ddr = r.get("delivery_delay_records") or []
    ds_ok = True
    for rec in ddr[:200]:
        d, key = _delivery_delay(EngineConfig(**{**dict(scenario_id=r["scenario_id"], seed=r["seed"],
                                                        miner_count=r["miners"]),
                                                 "propagation_delay_mean_s": cfg.get("propagation_delay_mean_s", 0.42)}),
                                 rec["template_generation_id"], rec["parent_block_id"],
                                 rec["winner_miner_id"], rec["recipient_miner_id"])
        if key != rec["delivery_stream_key"] or abs(float(d) - rec["propagation_delay_s"]) > 1e-12:
            ds_ok = False
            break
    c["delay_stream"] = ds_ok
    return c


def main():
    os.makedirs(RAW, exist_ok=True)
    cfgs = configs()
    assert len(cfgs) <= RUN_CAP, f"{len(cfgs)} > {RUN_CAP}"
    results = []
    cov = dict(stale_nonzero=False, multi_stale_producer_height=False,
               three_stale_producer_height=False, partial=False, b2_exhaustion=False,
               multi_position_per_miner=False, inactive=False, zero_delay_no_stale=False,
               delay_levels=set())
    all_pass = True
    for i, cfg in enumerate(cfgs):
        r = run_scenario(EngineConfig(**cfg), emit_detail=True, emit_generation_detail=True)
        checks = reconcile(r, cfg)
        ok = all(checks.values())
        all_pass = all_pass and ok
        results.append(dict(config=cfg, checks=checks, passed=ok,
                            accepted=r["accepted_blocks"], stale=r["stale_block_count"],
                            max_stale_at_height=max((t["stale_block_count"] for t in r["per_template"]),
                                                    default=0)))
        run_utils.atomic_write_json(
            os.path.join(RAW, f"VAL-{i:04d}-{cfg['scenario_id']}.summary.json"),
            dict(config=cfg, checks=checks, accepted=r["accepted_blocks"],
                 stale_block_count=r["stale_block_count"], status=run_utils.STATUS_COMPLETED))
        if r["stale_block_count"] > 0:
            cov["stale_nonzero"] = True
        mx = max((t["stale_block_count"] for t in r["per_template"]), default=0)
        if mx >= 2:
            cov["multi_stale_producer_height"] = True
        if mx >= 3:
            cov["three_stale_producer_height"] = True
        if r["partial_generations"] > 0:
            cov["partial"] = True
        if any(t.get("exact_exhaustion_verified") is not None for t in r["per_template"]):
            cov["b2_exhaustion"] = True
        if any(t["active_range_solution_position_count"] > t["distinct_potential_finder_miner_count"]
               for t in r["per_template"]):
            cov["multi_position_per_miner"] = True
        if cfg.get("inactive_miner_fraction", 0) > 0:
            cov["inactive"] = True
        if cfg.get("propagation_delay_mean_s", 0.42) == 0.0 and r["stale_block_count"] == 0:
            cov["zero_delay_no_stale"] = True
        cov["delay_levels"].add(cfg.get("propagation_delay_mean_s", 0.42))

    cov["delay_levels"] = sorted(cov["delay_levels"])
    report = dict(
        run_count=len(cfgs), run_cap=RUN_CAP, under_cap=len(cfgs) <= RUN_CAP,
        all_reconciliations_pass=all_pass,
        reconciliation_families=["energy", "candidates", "per_miner_generation",
                                 "template_chronology", "parent_chain", "block_proposals",
                                 "stale_diagnostic", "solution_positions", "b2_exhaustion",
                                 "delay_stream"],
        coverage=cov, failed=[x for x in results if not x["passed"]], results=results)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1g.json"), report)
    json.dump(dict(run_count=len(cfgs), all_pass=all_pass, coverage=cov),
              open(os.path.join(DOCS, "STAGE_05B1G_VALIDATION_RESULTS.json"), "w"), indent=2)
    print(json.dumps(dict(run_count=len(cfgs), all_reconciliations_pass=all_pass, coverage=cov),
                     indent=2))
    for x in report["failed"][:10]:
        print("FAIL", x["config"], x["checks"])
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_reconciliations_pass"] else 1)
