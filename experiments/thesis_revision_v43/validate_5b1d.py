"""Stage 5B1D revalidation after the exact-sampler correction.

Reruns the B1 event-loop zero-block validation with the SAME design as Stage 5B1B
(5 miner counts x 30 validation seeds disjoint from the frozen schedule; exact
analytical P_zero; independent direct reference; exact 99% Clopper-Pearson
criterion) against the corrected engine, plus a Binomial->position reconciliation
and a post-fix sanity check of B2/B3/C1/C2. Historical 5B1B outputs are NOT touched;
results go to stage_05b1d.
"""

from __future__ import annotations
import os
import sys
import json
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario, rng
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import exact_sampling as es
from experiments.thesis_revision_v43 import run_utils

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1d")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")
H, T, TGT, MU = 141e12, 10000.0, 600.0, 2.0
COUNTS = (100, 200, 300, 400, 500)
VALIDATION_SEEDS = [20261001 + i for i in range(30)]
DIRECT_SAMPLES = 100_000
MAX_RUNS = 150
_n = 0


def run(cfg, tag):
    global _n
    _n += 1
    if _n > MAX_RUNS:
        raise RuntimeError(f"event-loop cap {MAX_RUNS} exceeded")
    r = run_scenario(cfg)
    run_utils.atomic_write_json(os.path.join(RAW, f"VAL-{_n:04d}-{tag}.summary.json"),
                                dict(r, status=run_utils.STATUS_COMPLETED))
    return r


def main():
    os.makedirs(RAW, exist_ok=True)
    assert not (set(VALIDATION_SEEDS) & set(range(20260201, 20260231)))

    b1 = []
    all_ci = True
    for N in COUNTS:
        ex = bx.exact_zero_block(H, N, T, TGT, MU)
        p0 = ex["expected_zero_block_probability_exact"]
        direct = bx.direct_reference_sampler(H, N, T, TGT, MU, DIRECT_SAMPLES, seed=90000 + N)
        zeros = sum(1 for s in VALIDATION_SEEDS
                    if run(EngineConfig("B1", seed=s, miner_count=N), f"b1-{N}-{s}")["accepted_blocks"] == 0)
        lo99, hi99 = bx.clopper_pearson(zeros, len(VALIDATION_SEEDS), 0.01)
        inside = lo99 <= p0 <= hi99
        all_ci = all_ci and inside
        b1.append(dict(miner_count=N, exact_p_zero=p0,
                       poisson_p_zero=ex["expected_zero_block_probability_poisson"],
                       direct_reference_frequency=direct["zero_frequency"],
                       event_loop_zero_count=zeros, event_loop_sample_size=len(VALIDATION_SEEDS),
                       event_loop_frequency=zeros / len(VALIDATION_SEEDS),
                       clopper_pearson_99=[lo99, hi99], exact_within_99ci=inside))

    # Binomial-count == distinct-position reconciliation (sampler-level, many draws)
    recon_ok = True
    S = int(round(MU / (1.0 / (H * TGT)))); p = 1.0 / (H * TGT)
    for s in range(2000):
        g = rng(20260201 + s, "solution_positions")
        gk = rng(20260201 + s, "solution_count")
        k = int(gk.binomial(S, p))
        if k == 0:
            continue
        pos = es.sample_without_replacement(g, S, k)
        if not (pos.size == k and len(set(pos.tolist())) == k):
            recon_ok = False
            break

    # post-fix scenario sanity
    b2 = run_scenario(EngineConfig("B2", seed=1, miner_count=100))
    b3 = run_scenario(EngineConfig("B3_C1_CONTINUOUS_DISJOINT", seed=1, miner_count=100))
    c2 = run_scenario(EngineConfig("C2", seed=1, miner_count=100,
                                   hash_rate_distribution="heterogeneous_moderate",
                                   allocation_policy="equal", idle_power_ratio=0.1))
    scenario = dict(
        b2_total_reconciles=math.isclose(b2["total_candidate_evaluations"],
                                         b2["distinct_candidate_identities"] + b2["duplicate_evaluations"],
                                         rel_tol=1e-12),
        b3_energy_invariant=math.isclose(b3["total_energy_kwh"], 8.420833333333333, rel_tol=1e-9),
        c2_energy_reconciles=math.isclose(c2["total_energy_kwh"],
                                          c2["active_energy_kwh"] + c2["idle_energy_kwh"] + c2["coordination_energy_kwh"],
                                          abs_tol=1e-12))

    report = dict(event_loop_runs=_n, cap=MAX_RUNS,
                  acceptance="exact P_zero within event-loop 99% CI for every N; "
                             "Binomial count == distinct position count",
                  b1_all_within_99ci=all_ci,
                  binomial_to_position_reconciliation=recon_ok,
                  scenario_sanity=scenario,
                  all_passed=all_ci and recon_ok and all(scenario.values()),
                  b1=b1)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1d.json"), report)
    json.dump(b1, open(os.path.join(DOCS, "STAGE_05B1D_B1_VALIDATION_TABLE.json"), "w"), indent=2)
    print(json.dumps(dict(event_loop_runs=_n, b1_all_within_99ci=all_ci,
                          binomial_reconciliation=recon_ok, scenario=scenario,
                          all_passed=report["all_passed"]), indent=2))
    for r in b1:
        print(f"  N={r['miner_count']}: exact={r['exact_p_zero']:.4f} direct={r['direct_reference_frequency']:.4f} "
              f"event={r['event_loop_frequency']:.3f} 99%CI=[{r['clopper_pearson_99'][0]:.3f},{r['clopper_pearson_99'][1]:.3f}] "
              f"pass={r['exact_within_99ci']}")
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_passed"] else 1)
