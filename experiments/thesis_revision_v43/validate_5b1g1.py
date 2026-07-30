"""Stage 5B1G.1 bounded validation (hard cap 50). Exercises the three micro-
corrections: exact Fraction/integer B2 candidate coverage (no float), B2 path
provenance (real seeded start, circular last position, wraparound), and a winner
delivery + post-winner diagnostic for EVERY active non-winning miner. Every run
reconciles across EIGHT families. The full 1 890-run matrix is NOT executed.
"""

from __future__ import annotations
import os
import sys
import json
import math
from collections import Counter
from fractions import Fraction

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, _delivery_delay
from experiments.thesis_revision_v43 import run_utils, schemas, coverage as cov

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1g1")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
RUN_CAP = 50
DISJOINT = {"B0", "B3_C1_CONTINUOUS_DISJOINT", "C2"}
CONTINUOUS_FULL = {"B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT"}


def configs():
    out = []
    for scen in ("B0", "B1", "B2", "B3_C1_CONTINUOUS_DISJOINT", "C2"):
        for dist, alloc in (("homogeneous", "equal"), ("heterogeneous_moderate", "weighted")):
            out.append(dict(scenario_id=scen, seed=1, miner_count=40, hash_rate_distribution=dist,
                            allocation_policy=alloc, idle_power_ratio=(0.1 if scen == "C2" else 0.0),
                            mu=2.0))
    for delay in (0.0, 0.42, 5.0, 30.0, 60.0):                       # zero + nonzero delay
        out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=3, miner_count=40, mu=1.0,
                        propagation_delay_mean_s=delay))
    # B2 random starts + wraparound
    for seed in (5, 7):
        out.append(dict(scenario_id="B2", seed=seed, miner_count=12, mu=4.0))
    # B2 low-mu exact exhaustion
    out.append(dict(scenario_id="B2", seed=11, miner_count=8, mu=0.5))
    # B1 small-domain: same-identity deliveries, no stale
    out.append(dict(scenario_id="B1", seed=5, miner_count=20, mu=4.0,
                    network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                    propagation_delay_mean_s=60.0))
    # multiple stale producers per height
    out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=5, miner_count=20, mu=4.0,
                    network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                    propagation_delay_mean_s=60.0))
    out.append(dict(scenario_id="B3_C1_CONTINUOUS_DISJOINT", seed=9, miner_count=15, mu=4.0,
                    network_hash_rate_hps=2000.0, target_block_interval_s=1.0,
                    propagation_delay_mean_s=30.0))
    # inactive B2 (null start recorded)
    out.append(dict(scenario_id="B2", seed=2, miner_count=20, mu=3.0, inactive_miner_fraction=0.2))
    return out


def reconcile(r, cfg):
    disjoint = r["scenario_id"] in DISJOINT
    is_b2 = r["scenario_id"] == "B2"
    n_active = r["miners"] - int(round(r["inactive_fraction"] * r["miners"]))
    c = {}
    # 1. network/per-generation candidate totals exact
    s = sum(g["candidates_evaluated_this_generation"] for g in r["per_miner_generation"])
    c["network_generation_totals"] = (s == r["total_candidate_evaluations"])
    # 2. exact B2 candidate counts (total == distinct + duplicate, integers)
    c["exact_b2_candidates"] = (r["total_candidate_evaluations"]
                                == r["distinct_candidate_identities"] + r["duplicate_evaluations"])
    # 3. B2 circular path provenance
    if is_b2:
        S = r["domain_size"]
        ok = True
        for g in r["per_miner_generation"]:
            cc = g["candidates_evaluated_this_generation"]
            if cc > 0 and g["search_start_position"] is not None:
                if g["last_evaluated_position"] != (g["search_start_position"] + cc - 1) % S:
                    ok = False
                    break
        c["b2_paths"] = ok
    else:
        c["b2_paths"] = True
    # 4. a delivery record for every active non-winner at every accepted height
    per_gen = Counter(d["template_generation_id"] for d in r["delivery_delay_records"])
    accepted_gens = {x["template_generation_id"] for x in r["stale_race_records"]}
    c["all_nonwinner_deliveries"] = all(per_gen[g] == n_active - 1 for g in accepted_gens) and \
        all(x["active_nonwinner_delivery_count"] == n_active - 1 for x in r["stale_race_records"])
    # 5. post-winner diagnostic separated from primary
    c["postwinner_separation"] = (r["post_winner_energy_not_integrated"] is True
                                  and r["stale_race_energy_not_integrated"] is True
                                  and r["stale_race_candidate_evaluations"] == r["post_winner_candidate_evaluations"]
                                  and r["post_winner_candidate_evaluations"]
                                  >= r["stale_producer_postwinner_candidate_evaluations"])
    # 6. primary energy unchanged for continuous full-participation
    if r["scenario_id"] in CONTINUOUS_FULL and r["inactive_fraction"] == 0 \
            and abs(cfg.get("network_hash_rate_hps", 141e12) - 141e12) < 1 \
            and abs(cfg.get("target_block_interval_s", 600.0) - 600.0) < 1e-9:
        c["primary_energy_invariant"] = math.isclose(r["total_energy_kwh"], 8.420833333333333, rel_tol=1e-12)
    else:
        c["primary_energy_invariant"] = math.isclose(
            r["total_energy_kwh"],
            r["active_energy_kwh"] + r["idle_energy_kwh"] + r["coordination_energy_kwh"], abs_tol=1e-9)
    # 7. delivery-stream reproducibility
    ds = True
    rcfg = EngineConfig(scenario_id=r["scenario_id"], seed=r["seed"], miner_count=r["miners"],
                        propagation_delay_mean_s=cfg.get("propagation_delay_mean_s", 0.42))
    for rec in r["delivery_delay_records"][:200]:
        d, key = _delivery_delay(rcfg, rec["template_generation_id"], rec["parent_block_id"],
                                 rec["winner_miner_id"], rec["recipient_miner_id"])
        if key != rec["delivery_stream_key"] or abs(float(d) - rec["propagation_delay_s"]) > 1e-12:
            ds = False
            break
    c["delivery_stream"] = ds
    # 8. stale diagnostic internal consistency
    c["stale_diagnostic"] = schemas.reconcile_stale_diagnostic(r, r["per_template"], n_active=n_active)["passed"]
    return c


def main():
    os.makedirs(RAW, exist_ok=True)
    os.makedirs(os.path.join(RESULTS, "manifests"), exist_ok=True)
    os.makedirs(os.path.join(RESULTS, "logs"), exist_ok=True)
    cfgs = configs()
    assert len(cfgs) <= RUN_CAP, f"{len(cfgs)} > {RUN_CAP}"
    # adversarial Fraction boundary (unit property, exact != float)
    adv_exact = cov.lengths_at_time_exact([49], Fraction(1, 49), 100)[0]
    adv_float = math.floor(49 * float(Fraction(1, 49)))
    adversarial_ok = (adv_exact == 1 and adv_float == 0)

    results, all_pass = [], True
    cov_flags = dict(b1_same_identity=False, b2_random_start=False, b2_wraparound=False,
                     adversarial_boundary=adversarial_ok, no_reachable_solution_miner=False,
                     nonstale_competitor=False, multiple_stale_producers=False,
                     zero_delay=False, nonzero_delay=False, delay_levels=set())
    for i, cfg in enumerate(cfgs):
        r = run_scenario(EngineConfig(**cfg), emit_detail=True, emit_generation_detail=True)
        checks = reconcile(r, cfg)
        ok = all(checks.values()) and adversarial_ok
        all_pass = all_pass and ok
        mx = max((t["stale_block_count"] for t in r["per_template"]), default=0)
        results.append(dict(config=cfg, checks=checks, passed=ok,
                            accepted=r["accepted_blocks"], stale=r["stale_block_count"],
                            max_stale_at_height=mx))
        run_utils.atomic_write_json(
            os.path.join(RAW, f"VAL-{i:04d}-{cfg['scenario_id']}.summary.json"),
            dict(config=cfg, checks=checks, accepted=r["accepted_blocks"],
                 stale_block_count=r["stale_block_count"], status=run_utils.STATUS_COMPLETED))
        ddr = r["delivery_delay_records"]
        if r["scenario_id"] == "B1" and ddr and all(d["same_identity_independent_discovery"] for d in ddr):
            cov_flags["b1_same_identity"] = True
        if r["scenario_id"] == "B2" and any(g["search_start_position"] not in (None, 0)
                                            for g in r["per_miner_generation"]):
            cov_flags["b2_random_start"] = True
        if any(g["path_wraps_around"] for g in r["per_miner_generation"]):
            cov_flags["b2_wraparound"] = True
        if any(d["recipient_discovery_time_s"] is None for d in ddr):
            cov_flags["no_reachable_solution_miner"] = True
        if any(d["potential_competitor"] and not d["produced_stale_block"] for d in ddr):
            cov_flags["nonstale_competitor"] = True
        if mx >= 2:
            cov_flags["multiple_stale_producers"] = True
        dly = cfg.get("propagation_delay_mean_s", 0.42)
        cov_flags["zero_delay"] = cov_flags["zero_delay"] or (dly == 0.0 and r["stale_block_count"] == 0)
        cov_flags["nonzero_delay"] = cov_flags["nonzero_delay"] or dly > 0
        cov_flags["delay_levels"].add(dly)

    cov_flags["delay_levels"] = sorted(cov_flags["delay_levels"])
    report = dict(run_count=len(cfgs), run_cap=RUN_CAP, under_cap=len(cfgs) <= RUN_CAP,
                  all_reconciliations_pass=all_pass, adversarial_boundary_exact_ne_float=adversarial_ok,
                  reconciliation_families=["network_generation_totals", "exact_b2_candidates",
                                           "b2_paths", "all_nonwinner_deliveries",
                                           "postwinner_separation", "primary_energy_invariant",
                                           "delivery_stream", "stale_diagnostic"],
                  coverage=cov_flags, failed=[x for x in results if not x["passed"]], results=results)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1g1.json"), report)
    json.dump(dict(run_count=len(cfgs), all_pass=all_pass, coverage=cov_flags),
              open(os.path.join(DOCS, "STAGE_05B1G1_VALIDATION_RESULTS.json"), "w"), indent=2)
    print(json.dumps(dict(run_count=len(cfgs), all_reconciliations_pass=all_pass,
                          adversarial=adversarial_ok, coverage=cov_flags), indent=2))
    for x in report["failed"][:10]:
        print("FAIL", x["config"], x["checks"])
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_reconciliations_pass"] else 1)
