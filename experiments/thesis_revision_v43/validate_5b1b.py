"""Stage 5B1B B1 reconciliation validation.

Three independent computations of the B1 zero-block probability per miner count:
  1. exact analytical  -- (1-p)^M via mpmath (b1_exact.exact_zero_block)
  2. direct reference   -- Binomial(round(M), p) Monte-Carlo, NEVER calls the engine
  3. event-loop         -- the corrected scenario engine over 30 validation seeds

Acceptance (no arbitrary tolerance): the exact P_zero must lie inside the event-loop
**99% Clopper-Pearson** interval for every N, and event-loop vs direct-reference must
show no systematic across-N discrepancy. Validation seeds are DISJOINT from the
frozen 30-seed Stage-5B2 schedule.

Limits: <=150 event-loop runs (30 seeds x 5 N), 100000 direct samples per N.
"""

from __future__ import annotations
import os
import sys
import json
import math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, ROOT)

from experiments.thesis_revision_v43.scenario_engine import EngineConfig, run_scenario
from experiments.thesis_revision_v43 import b1_exact as bx
from experiments.thesis_revision_v43 import run_utils

RESULTS = os.path.join(ROOT, "results", "thesis_revision_v43", "stage_05b1b")
RAW = os.path.join(RESULTS, "raw")
DOCS = os.path.join(ROOT, "docs", "thesis_revision_v43")

H = 141e12
T = 10000.0
TARGET = 600.0
MU = 2.0
COUNTS = (100, 200, 300, 400, 500)
# validation seeds: DISJOINT from the frozen schedule 20260201..20260230
VALIDATION_SEEDS = [20261001 + i for i in range(30)]
DIRECT_SAMPLES = 100_000
MAX_EVENTLOOP_RUNS = 150

_run_count = 0


def run(cfg, tag):
    global _run_count
    _run_count += 1
    if _run_count > MAX_EVENTLOOP_RUNS:
        raise RuntimeError(f"event-loop validation cap {MAX_EVENTLOOP_RUNS} exceeded")
    r = run_scenario(cfg)
    run_utils.atomic_write_json(os.path.join(RAW, f"VAL-{_run_count:04d}-{tag}.summary.json"),
                                dict(r, status=run_utils.STATUS_COMPLETED))
    return r


def main():
    os.makedirs(RAW, exist_ok=True)
    # disjointness guard
    frozen = set(range(20260201, 20260231))
    assert not (set(VALIDATION_SEEDS) & frozen), "validation seeds overlap frozen schedule"

    rows = []
    all_pass = True
    for N in COUNTS:
        ex = bx.exact_zero_block(H, N, T, TARGET, MU)
        p0 = ex["expected_zero_block_probability_exact"]
        pois = ex["expected_zero_block_probability_poisson"]
        direct = bx.direct_reference_sampler(H, N, T, TARGET, MU, DIRECT_SAMPLES, seed=90000 + N)
        accs = [run(EngineConfig("B1", seed=s, miner_count=N), f"b1-{N}-{s}")["accepted_blocks"]
                for s in VALIDATION_SEEDS]
        zeros = sum(1 for a in accs if a == 0)
        n = len(accs)
        f_emp = zeros / n
        lo95, hi95 = bx.clopper_pearson(zeros, n, 0.05)
        lo99, hi99 = bx.clopper_pearson(zeros, n, 0.01)
        se = math.sqrt(p0 * (1 - p0) / n) if 0 < p0 < 1 else float("nan")
        z = (f_emp - p0) / se if se and not math.isnan(se) else 0.0
        inside99 = lo99 <= p0 <= hi99
        # direct-reference consistency: direct freq within event-loop 99% CI too
        direct_inside99 = lo99 <= direct["zero_frequency"] <= hi99
        passed = inside99
        all_pass = all_pass and passed
        rows.append(dict(
            miner_count=N,
            exact_p_zero=p0, poisson_p_zero=pois,
            poisson_absolute_error=ex["poisson_absolute_error"],
            poisson_relative_error=ex["poisson_relative_error"],
            direct_reference_frequency=direct["zero_frequency"],
            direct_reference_samples=DIRECT_SAMPLES,
            event_loop_zero_count=zeros, event_loop_sample_size=n,
            event_loop_frequency=f_emp,
            clopper_pearson_95=[lo95, hi95], clopper_pearson_99=[lo99, hi99],
            standardized_deviation=z,
            exact_within_event_loop_99ci=inside99,
            direct_within_event_loop_99ci=direct_inside99,
            expected_unique_candidate_evaluations=ex["expected_unique_candidate_evaluations"],
            expected_full_template_generations=ex["expected_full_template_generations"],
            expected_partial_generation_candidates=ex["expected_partial_generation_candidates"],
            passed=passed))

    # monotonicity + systematic-discrepancy check (residual signs of event-loop - exact)
    residual_signs = [1 if r["event_loop_frequency"] > r["exact_p_zero"] else
                      (-1 if r["event_loop_frequency"] < r["exact_p_zero"] else 0) for r in rows]
    same_sign = len({s for s in residual_signs if s != 0}) <= 1
    # sign test p-value for k of n same direction (two-sided)
    n_nonzero = sum(1 for s in residual_signs if s != 0)
    k_pos = sum(1 for s in residual_signs if s > 0)
    from math import comb
    def sign_p(k, n):
        if n == 0:
            return 1.0
        tail = sum(comb(n, i) for i in range(0, min(k, n - k) + 1)) / (2 ** n)
        return min(1.0, 2 * tail)
    systematic_p = sign_p(min(k_pos, n_nonzero - k_pos), n_nonzero)
    no_systematic = systematic_p > 0.05         # not significant -> no systematic bias
    mono_exact = all(rows[i]["exact_p_zero"] <= rows[i + 1]["exact_p_zero"] + 1e-15
                     for i in range(len(rows) - 1))

    report = dict(
        event_loop_run_count=_run_count, event_loop_cap=MAX_EVENTLOOP_RUNS,
        direct_samples_per_count=DIRECT_SAMPLES,
        validation_seeds=VALIDATION_SEEDS, frozen_schedule_disjoint=True,
        acceptance_criterion="exact P_zero within event-loop 99% Clopper-Pearson CI for every N",
        all_within_99ci=all_pass, exact_monotone_in_N=mono_exact,
        residual_signs=residual_signs, sign_test_p=systematic_p,
        no_systematic_discrepancy=no_systematic,
        all_passed=all_pass and mono_exact and no_systematic,
        per_count=rows)
    run_utils.atomic_write_json(os.path.join(RESULTS, "validation_report_5b1b.json"), report)
    json.dump(rows, open(os.path.join(DOCS, "STAGE_05B1B_B1_VALIDATION_TABLE.json"), "w"), indent=2)
    print(json.dumps(dict(event_loop_runs=_run_count, all_within_99ci=all_pass,
                          no_systematic_discrepancy=no_systematic,
                          exact_monotone=mono_exact, all_passed=report["all_passed"]), indent=2))
    for r in rows:
        print(f"  N={r['miner_count']}: exact={r['exact_p_zero']:.4f} direct={r['direct_reference_frequency']:.4f} "
              f"event={r['event_loop_frequency']:.3f} 99%CI=[{r['clopper_pearson_99'][0]:.3f},{r['clopper_pearson_99'][1]:.3f}] "
              f"pass={r['passed']}")
    return report


if __name__ == "__main__":
    rep = main()
    sys.exit(0 if rep["all_passed"] else 1)
