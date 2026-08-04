#!/usr/bin/env python3
"""Stage 6M — STRUCTURAL pilot (structure and runtime ONLY; never an energy effect).

Runs M01, M02 and M03 on two PILOT seeds disjoint from the 10 selected confirmatory seeds.
The output contains NO energy quantity other than deterministic accounting residuals with
fixed tolerances: E_idle, E_power_null, their difference and their ratio are deliberately
NOT computed and NOT recorded here, so no pilot energy effect can be inspected.

If a structural gate fails: STOP.  Nothing is tuned on effect direction.
"""
from __future__ import annotations

import json
import pathlib
import resource
import sys
import time

HERE = pathlib.Path(__file__).resolve().parent
for p in (str(HERE),):
    if p not in sys.path:
        sys.path.insert(0, p)

import scenarios_6m as M                                                       # noqa: E402
from run_pilot import (post_round_audit, residency_and_energy_identity,        # noqa: E402
                       round_durations, nonterminal_activation_request_count)
from Models.PoCol.stage2.simulator import run_simulation                       # noqa: E402
from Models.PoCol.stage2.adapter import results_schema                         # noqa: E402

WALL_LIMIT_S = 600.0          # each run <= 10 minutes
RSS_LIMIT_MB = 4096.0         # each run <= 4 GB


def gates(rec: dict, scenario_id: str) -> list:
    g = []
    def check(name, ok):
        g.append({"gate": name, "pass": bool(ok)})
    check("run completes", rec["run_status"] == "COMPLETED")
    check("closes at least 100 rounds", rec.get("rounds_executed", 0) >= 100)
    check("evaluation ledger non-empty", rec.get("evaluation_ledger_entries", 0) > 0)
    check("duplicate_nonce_count == 0", rec.get("duplicate_nonce_count", 1) == 0)
    check("post_round_evaluation_record_count == 0",
          rec.get("post_round_evaluation_record_count", 1) == 0)
    check("residency reconciliation passes", rec.get("residency_reconciles") is True)
    check("wall time <= 10 min", rec.get("wall_clock_seconds", 1e9) <= WALL_LIMIT_S)
    check("peak RSS <= 4 GB", rec.get("peak_rss_mb", 1e9) <= RSS_LIMIT_MB)
    if scenario_id == "M03_HET_IDLE_FLOOR":
        check("M03 records security-floor observations",
              rec.get("security_floor_observation_count", 0) > 0)
        check("M03 seats at least one reserve activation",
              rec.get("reserve_activations_seated", 0) >= 1)
        check("no nonterminal activation request remains",
              rec.get("nonterminal_activation_request_count", 1) == 0)
    return g


def main() -> int:
    M.assert_core_matches_directive()
    seeds = [M.pilot_seeds()[i] for i in M.STRUCTURAL_PILOT_SEED_INDEXES]
    conf = set(M.confirmatory_seeds())
    assert not (set(seeds) & conf), "structural pilot seeds must be disjoint from confirmatory"
    out_dir = HERE / "pilot"
    out_dir.mkdir(exist_ok=True)
    results, all_pass = [], True
    for row in M.CONFIRMATORY:
        for idx, seed in zip(M.STRUCTURAL_PILOT_SEED_INDEXES, seeds):
            cfg = M.build_config_6m(row, seed)
            t0 = time.time()
            rec = {"scenario_id": row["scenario_id"], "pilot_seed_index": idx,
                   "master_seed": seed}
            try:
                run = run_simulation(cfg, run_id=f"6m-pilot-{row['scenario_id']}-{idx}")
                res = results_schema(run, cfg)
                durs, mono = round_durations(run, cfg)
                ident = residency_and_energy_identity(run, cfg)
                audit = post_round_audit(run)
                rec.update(
                    run_status="COMPLETED",
                    wall_clock_seconds=time.time() - t0,
                    peak_rss_mb=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024.0,
                    rounds_executed=len(run.round_terminal_times),
                    rounds_accepted=res["rounds_accepted"],
                    round_terminal_times_strictly_increasing=bool(mono),
                    evaluation_ledger_entries=res["evaluation_ledger_entries"],
                    duplicate_nonce_count=res["duplicate_nonce_count"],
                    residency_reconciles=bool(res["residency_reconciles"]),
                    maximum_energy_identity_residual_j=ident["maximum_energy_identity_residual_j"],
                    maximum_residency_partition_residual_s=ident["maximum_residency_partition_residual_s"],
                    security_floor_observation_count=res["security_floor_observation_count"],
                    reserve_activations_seated=res["reserve_activations_seated"],
                    reserve_activations_completed=res["reserve_activations_completed"],
                    nonterminal_activation_request_count=nonterminal_activation_request_count(run),
                    **audit)
            except Exception as exc:                                  # noqa: BLE001
                rec.update(run_status="EXCEPTION", exception=repr(exc),
                           wall_clock_seconds=time.time() - t0)
            rec["gates"] = gates(rec, row["scenario_id"])
            rec["all_gates_pass"] = all(x["pass"] for x in rec["gates"])
            all_pass &= rec["all_gates_pass"]
            results.append(rec)
            print(f"  {row['scenario_id']:22s} pilot[{idx}] {rec['run_status']:9s} "
                  f"{rec['wall_clock_seconds']:6.2f}s rounds={rec.get('rounds_executed','-'):>4} "
                  f"gates={'PASS' if rec['all_gates_pass'] else 'FAIL'}")
            if not rec["all_gates_pass"]:
                for x in rec["gates"]:
                    if not x["pass"]:
                        print(f"      FAILED GATE: {x['gate']}")
    payload = {"harness": "run_structural_pilot_6m.py",
               "purpose": ("STRUCTURE AND RUNTIME ONLY. No energy effect is computed or "
                           "recorded: neither the per-run energy total nor the power-null "
                           "counterfactual nor any difference or ratio of them appears in "
                           "this file, by construction."),
               "pilot_seed_indexes": list(M.STRUCTURAL_PILOT_SEED_INDEXES),
               "all_structural_gates_pass": all_pass, "results": results}
    (out_dir / "structural_pilot_results.json").write_text(
        json.dumps(payload, indent=1, sort_keys=True, default=str) + "\n")
    print(f"\nstructural pilot: {'ALL GATES PASS' if all_pass else 'BLOCKED'}")
    return 0 if all_pass else 2


if __name__ == "__main__":
    raise SystemExit(main())
