#!/usr/bin/env python3
"""Stage 8S Phase 0 — READ-ONLY structural feasibility analysis of the frozen Stage-8R data.

No simulation is executed.  Inputs: the frozen STAGE_08R_RUN_DATASET.csv (48 rows) and the
three frozen Stage-8R timelines (R01/R02/R03 seed 0).  Stage-8R is NOT rerun.

Epistemic labels: OBSERVED (read from a frozen record), DERIVED (computed under a stated
assumption), HYPOTHESIS (interpretation), UNRESOLVED (not derivable from frozen data).

Outputs:
    docs/thesis_revision_v45/stage_08s/STAGE_08S_STRUCTURAL_FEASIBILITY_METRICS.json
"""
from __future__ import annotations

import csv
import gzip
import json
import pathlib
import statistics

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
S8R_DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08r"
S8R_TL = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_08r" / "timelines"
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08s"

H0 = 4000.0                                # OBSERVED config fact (16 het primaries)
STATIC_FLOOR = 0.80 * H0                   # 3200
RESERVE_RATES = [100.0, 200.0, 300.0, 400.0]   # M016..M019 het rates (OBSERVED config)
RESERVE_POOL = sum(RESERVE_RATES)          # 1000
MAX_USEFUL = H0 + RESERVE_POOL             # 5000
BATCH = 25
HORIZON = 300.0


def load_dataset() -> dict:
    with open(S8R_DOCS / "STAGE_08R_RUN_DATASET.csv", newline="") as fh:
        rows = list(csv.DictReader(fh))
    by = {}
    for r in rows:
        by.setdefault(r["scenario_id"], []).append(r)
    for rs in by.values():
        rs.sort(key=lambda r: int(r["seed_index"]))
    return by


def per_seed_tables(by: dict) -> dict:
    out = {}
    for sid, rs in sorted(by.items()):
        out[sid] = [{
            "seed_index": int(r["seed_index"]),
            # OBSERVED (frozen dataset)
            "accepted_blocks": int(r["rounds_accepted"]),
            "closed_rounds": int(r["rounds_executed"]),
            "duration_below_static_floor_s": float(r["total_duration_below_floor"]),
            "static_floor_deficit_area_hash_s": float(r["floor_deficit_area_hash_s"]),
            "static_floor_unattainable_decision_count": int(r["floor_unattainable_count"]),
            "activation_requests_seated": int(r["activation_requests_seated"]),
            "activation_requests_completed": int(r["activation_requests_completed"]),
            "incomplete_activation_request_count":
                int(r["incomplete_activation_request_count"]),
            "reassignment_trigger_count": int(r["controller_suffix_reassignment_count"]),
            "E_idle_kwh": float(r["E_idle_kwh"]),
            "relative_reduction": float(r["relative_reduction"]),
            "range_idle_energy_difference_kwh":
                float(r["range_idle_energy_difference_kwh"]),
            "reserve_standby_energy_difference_kwh":
                float(r["reserve_standby_energy_difference_kwh"]),
            "wake_energy_difference_kwh": float(r["wake_energy_difference_kwh"]),
            "activated_reserve_energy_kwh": float(r["activated_reserve_energy_kwh"]),
            # DERIVED (constants + arithmetic)
            "H0": H0, "static_floor": STATIC_FLOOR,
            "maximum_reserve_capacity": RESERVE_POOL,
            "maximum_physically_useful_capacity": MAX_USEFUL,
            "activation_requests_without_useful_completion":
                int(r["activation_requests_seated"])
                - int(r["activation_requests_completed"]),
            "workless_wake_rate": (
                (int(r["activation_requests_seated"])
                 - int(r["activation_requests_completed"]))
                / int(r["activation_requests_seated"])
                if int(r["activation_requests_seated"]) else 0.0),
        } for r in rs]
    return out


def load_timeline(name: str) -> dict:
    return json.loads(gzip.open(S8R_TL / name, "rt").read())


def timeline_depth(name: str, sid: str) -> dict:
    """DERIVED per-observation reconstruction for one frozen timeline run."""
    d = load_timeline(name)
    obs = sorted(d["security_observations"], key=lambda o: (str(o["RoundID"]),
                                                            float(o["observation_time"])))
    rtt = {k: float(v) for k, v in d["round_terminal_times"].items()}
    # remaining useful nonce work per round over time: cumulative evaluated nonces from the
    # frozen ledger; the domain per round is 1600 (primaries 1280 + reserve slices 320).
    by_round_led = {}
    for rec in d["evaluation_ledger"]:
        by_round_led.setdefault(rec["RoundID"], []).append(
            (float(rec["completion_time"]), int(rec["interval_end"]) - int(rec["interval_start"])))
    static_unattainable_periods = 0
    useful_deficit_s = 0.0
    static_deficit_s = 0.0
    remaining_series_sample = []
    by_round_obs = {}
    for o in obs:
        by_round_obs.setdefault(o["RoundID"], []).append(o)
    for rid, os_ in by_round_obs.items():
        os_.sort(key=lambda o: float(o["observation_time"]))
        led = sorted(by_round_led.get(rid, []))
        cum = 0.0
        li = 0
        for a, b in zip(os_, os_[1:]):
            t0, t1 = float(a["observation_time"]), float(b["observation_time"])
            while li < len(led) and led[li][0] <= t0:
                cum += led[li][1]
                li += 1
            remaining = max(0.0, 1600.0 - cum)
            h = float(a["effective_active_hash_rate"])
            dt = max(0.0, t1 - t0)
            if h < STATIC_FLOOR:
                static_deficit_s += dt
                # DERIVED counterfactual: capacity is USEFULLY deficient only when the
                # remaining unsearched work could occupy at least one additional batch
                # beyond what the currently active miners will consume within that window.
                consumed_by_active = h * dt
                if remaining - consumed_by_active >= BATCH:
                    useful_deficit_s += dt
            # DERIVED: mathematically unattainable period = even the FULL reserve pool plus
            # current active capacity cannot reach the static floor.
            if h + RESERVE_POOL < STATIC_FLOOR and dt > 0:
                static_unattainable_periods += 1
        if len(remaining_series_sample) < 40 and os_:
            remaining_series_sample.append(
                {"round": rid, "observations": len(os_),
                 "terminal": rtt.get(rid)})
    # reassignment sizes (R03 only): reassigned-work ledger records grouped by assignment
    sizes = {}
    concurrent = 0
    if "REASSIGNMENT" in sid:
        for rec in d["evaluation_ledger"]:
            if "REASSIGNED" in str(rec.get("assignment_kind", "")):
                key = (rec["RoundID"], rec["AssignmentID"])
                sizes[key] = sizes.get(key, 0) + (int(rec["interval_end"])
                                                  - int(rec["interval_start"]))
        # max simultaneous: overlapping wake windows of REASSIGNMENT_WAKE_ONLY requests
        wins = []
        for r in d["activation_requests"].values():
            if r.get("activation_scope") == "REASSIGNMENT_WAKE_ONLY" \
                    and r.get("started_at") is not None:
                end = r.get("completed_at") or r.get("started_at")
                wins.append((float(r["started_at"]), float(end)))
        events = sorted([(s, 1) for s, _e in wins] + [(e, -1) for _s, e in wins])
        cur = 0
        for _t, k in events:
            cur += k
            concurrent = max(concurrent, cur)
    sz = sorted(sizes.values())
    rs = d["results_schema"]
    return {
        "timeline_run": d["run_id"],
        "static_floor_deficit_time_reconstructed_s": static_deficit_s,
        "useful_work_aware_deficit_time_DERIVED_s": useful_deficit_s,
        "useless_below_floor_time_DERIVED_s": static_deficit_s - useful_deficit_s,
        "mathematically_unattainable_period_count_DERIVED": static_unattainable_periods,
        # OBSERVED from the frozen results schema — the decisive R03 finding:
        "reassignment_trigger_decisions_OBSERVED": rs.get(
            "controller_suffix_reassignment_count", 0),
        "reassignment_requests_seated_OBSERVED": rs.get(
            "reassignment_requests_seated", 0),
        "reassignment_requests_completed_OBSERVED": rs.get(
            "reassignment_requests_completed", 0),
        "reassigned_ledger_record_lineages_OBSERVED": len(sz),
        "mean_reassignment_size_nonces": (statistics.fmean(sz) if sz else None),
        "median_reassignment_size_nonces": (statistics.median(sz) if sz else None),
        "max_simultaneous_reassignment_wakes": concurrent or None,
    }


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    by = load_dataset()
    tables = per_seed_tables(by)
    depth = {
        "R01_s00": timeline_depth("8r-R01_LEGACY_FLOOR-s00_timeline.json.gz",
                                  "R01_LEGACY_FLOOR"),
        "R02_s00": timeline_depth("8r-R02_REVISED_CONTROLLER-s00_timeline.json.gz",
                                  "R02_REVISED_CONTROLLER"),
        "R03_s00": timeline_depth(
            "8r-R03_REVISED_PLUS_REASSIGNMENT-s00_timeline.json.gz",
            "R03_REVISED_PLUS_REASSIGNMENT"),
    }
    metrics = {
        "harness": "diagnose_8s_baseline.py (READ-ONLY; no simulation executed)",
        "constants_OBSERVED": {"H0": H0, "static_floor": STATIC_FLOOR,
                               "maximum_reserve_capacity": RESERVE_POOL,
                               "maximum_physically_useful_capacity": MAX_USEFUL,
                               "batch_size": BATCH, "horizon_s": HORIZON},
        "per_seed": tables,
        "timeline_depth_DERIVED": depth,
        "per_seed_unresolved": [
            "remaining-useful-work time series (persisted only for the 3 timeline seeds)",
            "useful-floor deficit per seed (counterfactual DERIVED for timeline seeds only)",
            "max simultaneous reassignments per seed (R03 timeline seed only)",
        ],
    }
    (DOCS / "STAGE_08S_STRUCTURAL_FEASIBILITY_METRICS.json").write_text(
        json.dumps(metrics, indent=1, sort_keys=True, default=str) + "\n")
    print("wrote STAGE_08S_STRUCTURAL_FEASIBILITY_METRICS.json")
    print(json.dumps(depth, indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
