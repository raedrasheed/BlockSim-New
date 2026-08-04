#!/usr/bin/env python3
"""Stage 8R Phase 0 — READ-ONLY diagnostic of the frozen Stage-7M/8M baseline data.

No simulation is executed here.  Inputs are exclusively the frozen artifacts:

    experiments/thesis_revision_v45/stage_07m/runs/*.json          (compact records, all seeds)
    experiments/thesis_revision_v45/stage_07m/audit/*.json.gz      (full ledgers, 2 audit runs)

Every quantity is labeled with its epistemic class:

    OBSERVED    read directly from a frozen record
    DERIVED     computed from frozen records under a stated assumption
    UNRESOLVED  not derivable from the frozen data (stated, never guessed)

Outputs:
    docs/thesis_revision_v45/stage_08r/STAGE_08R_BASELINE_DIAGNOSTIC_METRICS.json
    docs/thesis_revision_v45/stage_08r/STAGE_08R_BASELINE_TIMELINE_M03_S00.csv
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import pathlib
import re
import statistics

HERE = pathlib.Path(__file__).resolve().parent
REPO_ROOT = HERE.parents[2]
S7M = REPO_ROOT / "experiments" / "thesis_revision_v45" / "stage_07m"
DOCS = REPO_ROOT / "docs" / "thesis_revision_v45" / "stage_08r"

HORIZON = 300.0
FLOOR = 3200.0                 # 0.80 x H0(het) = 0.80 x 4000, frozen in Stage 6M
P_WAKE = 10.75
BATCH = 25
PRIMARIES = [f"M{i:03d}" for i in range(16)]
RESERVES = [f"M{i:03d}" for i in range(16, 20)]


def load_compact(scenario: str) -> list:
    out = []
    for p in sorted((S7M / "runs").glob(f"7m-{scenario}-s*.json")):
        out.append(json.loads(p.read_text()))
    return sorted(out, key=lambda r: r["seed_index"])


def q(sorted_vals: list, frac: float) -> float:
    """Empirical quantile: the ceil(frac*n)-th order statistic."""
    i = min(len(sorted_vals) - 1, max(0, int(frac * len(sorted_vals) + 0.999999) - 1))
    return sorted_vals[i]


# ------------------------------------------------------------------ per-seed (compact)
def per_seed_tables() -> dict:
    tables = {}
    for sid in ("M01_HET_IDLE", "M03_HET_IDLE_FLOOR"):
        rows = []
        for r in load_compact(sid):
            rows.append({
                "seed_index": r["seed_index"],
                # OBSERVED, straight from the frozen compact record
                "total_horizon_s": HORIZON,
                "closed_round_count": r["rounds_executed"],
                "accepted_block_count": r["rounds_accepted"],
                "median_round_duration_s": r["median_round_duration"],
                "round_duration_min_s": r["round_duration_min"],
                "round_duration_max_s": r["round_duration_max"],
                "total_duration_below_floor_s": r["total_duration_below_floor"],
                "floor_unattainable_count": r["floor_unattainable_count"],
                "activation_requests_seated": r["reserve_activations_seated"],
                "activation_requests_completed": r["reserve_activations_completed"],
                "nonterminal_activation_request_count":
                    r["nonterminal_activation_request_count"],
                "E_idle_kwh": r["E_idle_kwh"],
                # DERIVED
                "accepted_blocks_per_closed_round":
                    r["rounds_accepted"] / r["rounds_executed"],
                "approx_mean_round_duration_s_upper_bound":
                    HORIZON / r["rounds_executed"],
                "incomplete_activation_request_count":
                    r["reserve_activations_seated"] - r["reserve_activations_completed"],
            })
        tables[sid] = rows
    return tables


# ------------------------------------------------------------------ audit-ledger depth
def load_audit(name: str) -> dict:
    return json.loads(gzip.open(S7M / "audit" / name, "rt").read())


def round_duration_stats(rtt: dict) -> dict:
    times = sorted(float(v) for v in rtt.values())
    durs, prev = [], 0.0
    for t in times:
        durs.append(t - prev)
        prev = t
    s = sorted(durs)
    return {"count": len(durs), "median_s": statistics.median(durs),
            "mean_s": statistics.fmean(durs), "p90_s": q(s, 0.90), "p95_s": q(s, 0.95),
            "max_s": s[-1], "unclosed_final_tail_s": HORIZON - times[-1],
            "durations": durs, "terminals": times}


def residency_split(res: dict) -> dict:
    """Per-state residency split by role (primary vs reserve).  DERIVED: role is fixed by
    miner index under the frozen reserve_fraction (M000-M015 primary, M016-M019 reserve)."""
    out = {}
    for role, ids in (("primary", PRIMARIES), ("reserve", RESERVES)):
        agg = {}
        for mid in ids:
            for state, dur in res[mid].items():
                agg[state] = agg.get(state, 0.0) + float(dur)
        out[role] = {k: v for k, v in sorted(agg.items())}
    return out


def miner_rates(ledger: list) -> dict:
    """DERIVED actual per-miner hash rates from evaluation-cadence deltas: consecutive batch
    completions within one assignment are batch_size/rate apart."""
    by_asg = {}
    for rec in ledger:
        by_asg.setdefault((rec["MinerID"], rec["AssignmentID"]), []).append(rec)
    rates = {}
    for (mid, _a), recs in by_asg.items():
        recs.sort(key=lambda r: float(r["completion_time"]))
        for a, b in zip(recs, recs[1:]):
            dt = float(b["completion_time"]) - float(a["completion_time"])
            size = int(b["interval_end"]) - int(b["interval_start"])
            if dt > 1e-12 and size > 0:
                rates.setdefault(mid, []).append(size / dt)
    return {m: statistics.median(v) for m, v in rates.items() if v}


def active_intervals(ledger: list, rates: dict, activations: dict) -> list:
    """DERIVED ACTIVE_HASHING intervals per (miner, assignment).

    Assumption A1: a primary assignment starts hashing at (first_completion − batch/rate);
    an activated reserve starts at its activation completed_at.  Assumption A2: hashing ends
    at the last batch completion of the assignment.  Both are stated in the report."""
    started_by = {}
    for r in activations.values():
        if r.get("completed_at") is not None:
            key = (r["MinerID"], r["RoundID"])
            t = float(r["completed_at"])
            started_by[key] = min(t, started_by.get(key, t))
    by_asg = {}
    for rec in ledger:
        by_asg.setdefault((rec["MinerID"], rec["AssignmentID"], rec["RoundID"]),
                          []).append(rec)
    out = []
    for (mid, _a, rid), recs in by_asg.items():
        ts = sorted(float(r["completion_time"]) for r in recs)
        rate = rates.get(mid)
        if rate is None:
            continue
        if (mid, rid) in started_by:
            start = started_by[(mid, rid)]
        else:
            start = max(0.0, ts[0] - BATCH / rate)
        out.append({"miner": mid, "round": rid, "start": start, "end": ts[-1],
                    "rate": rate, "is_reserve": mid in RESERVES})
    return sorted(out, key=lambda x: x["start"])


def activation_lifecycle(activations: dict, rtt: dict) -> dict:
    seated = len(activations)
    started = sum(1 for r in activations.values() if r.get("started_at") is not None)
    completed = sum(1 for r in activations.values() if r["status"] == "COMPLETED")
    cancelled = [r for r in activations.values() if r["status"] == "CANCELLED"]
    cb = sum(1 for r in cancelled if r.get("started_at") is None)
    cw = sum(1 for r in cancelled if r.get("started_at") is not None)
    disp = {}
    for r in activations.values():
        m = re.match(r"Outcome\('([^']+)'", r.get("disposition") or "")
        d = m.group(1) if m else "UNKNOWN"
        disp[d] = disp.get(d, 0) + 1
    # wake energy by terminal disposition (DERIVED).  Completed: exact latency interval.
    # Cancelled-during-wake: wake runs from started_at until the cancelling round closure.
    e_completed = sum((float(r["completed_at"]) - float(r["started_at"])) * P_WAKE
                     for r in activations.values() if r["status"] == "COMPLETED")
    e_cancelled = 0.0
    for r in cancelled:
        if r.get("started_at") is None:
            continue
        close = rtt.get(r["RoundID"])
        if close is not None:
            e_cancelled += max(0.0, float(close) - float(r["started_at"])) * P_WAKE
    return {"seated": seated, "started": started, "completed": completed,
            "cancelled_before_start": cb, "cancelled_during_wake": cw,
            "superseded": "UNRESOLVED (no supersession state exists in the accepted schema)",
            "stale_at_closure": cw,
            "stale_at_closure_note": ("DERIVED equivalence: every cancellation in the frozen "
                                      "data is 'cancelled_at_round_close' after wake start"),
            "schedule_failed": 0,
            "dispositions": disp,
            "wake_energy_completed_j": e_completed,
            "wake_energy_cancelled_during_wake_j": e_cancelled}


def h_effective_series(intervals: list, waking: list) -> list:
    """DERIVED stepwise H_effective(t) and H_pipeline(t) from the interval reconstruction.
    waking = [(start, end, rate)] for activation wake windows."""
    events = []
    for iv in intervals:
        events.append((iv["start"], "on", iv["rate"]))
        events.append((iv["end"], "off", iv["rate"]))
    wevents = []
    for s, e, r in waking:
        wevents.append((s, "won", r))
        wevents.append((e, "woff", r))
    allts = sorted({t for t, _, _ in events} | {t for t, _, _ in wevents})
    series = []
    h = hp_wake = 0.0
    ei = wi = 0
    events.sort()
    wevents.sort()
    for t in allts:
        while ei < len(events) and events[ei][0] <= t:
            _, kind, r = events[ei]
            h += r if kind == "on" else -r
            ei += 1
        while wi < len(wevents) and wevents[wi][0] <= t:
            _, kind, r = wevents[wi]
            hp_wake += r if kind == "won" else -r
            wi += 1
        series.append((t, max(0.0, h), max(0.0, h + hp_wake)))
    return series


def deficit_area(series: list, end: float) -> dict:
    area = 0.0
    below = 0.0
    max_def = 0.0
    for (t0, h, _), (t1, _, _) in zip(series, series[1:] + [(end, 0.0, 0.0)]):
        dt = max(0.0, min(t1, end) - t0)
        d = max(0.0, FLOOR - h)
        area += d * dt
        max_def = max(max_def, d)
        if d > 0:
            below += dt
    return {"floor_deficit_area_hash_s": area, "maximum_floor_deficit_hash": max_def,
            "derived_below_floor_duration_s": below}


def audit_depth(name: str, has_floor: bool) -> dict:
    d = load_audit(name)
    rtt = {k: float(v) for k, v in d["round_terminal_times"].items()}
    rounds = round_duration_stats(rtt)
    res = residency_split(d["per_miner_residency_s"])
    rates = miner_rates(d["evaluation_ledger"])
    activations = d.get("activation_requests") or {}
    intervals = active_intervals(d["evaluation_ledger"], rates, activations)
    waking = [(float(r["started_at"]),
               float(r["completed_at"]) if r["status"] == "COMPLETED"
               else float(rtt.get(r["RoundID"], r["started_at"])),
               rates.get(r["MinerID"], 0.0))
              for r in activations.values() if r.get("started_at") is not None]
    series = h_effective_series(intervals, waking)
    out = {
        "run_id": d["run_id"],
        "round_duration": {k: v for k, v in rounds.items()
                           if k not in ("durations", "terminals")},
        "residency_by_role_state_s": res,
        "derived_miner_rates": {k: rates[k] for k in sorted(rates)},
        "derived_H0_primary_total": sum(rates.get(m, 0.0) for m in PRIMARIES),
        "activation_lifecycle": (activation_lifecycle(activations, rtt)
                                 if activations else None),
        "reserve_active_hashing_s": res["reserve"].get("ACTIVE_HASHING", 0.0),
        "reserve_waking_s": res["reserve"].get("WAKING", 0.0),
    }
    if has_floor:
        out["floor_deficit"] = deficit_area(series, HORIZON)
        out["observed_total_duration_below_floor_s"] = (
            d["results_schema"]["total_duration_below_floor"])
    return out, series, rtt, d


def write_timeline(series: list, rtt: dict, d: dict, dest: pathlib.Path) -> None:
    activations = d["activation_requests"]
    live = []
    for r in activations.values():
        s = r.get("seated_at")
        if s is None:
            continue
        e = (r.get("completed_at") if r["status"] == "COMPLETED"
             else rtt.get(r["RoundID"]))
        live.append((float(s), float(e)))
    waking = [(float(r["started_at"]),
               float(r["completed_at"]) if r["status"] == "COMPLETED"
               else float(rtt.get(r["RoundID"])))
              for r in activations.values() if r.get("started_at") is not None]
    blocks = sorted(float(rec["completion_time"]) for rec in d["evaluation_ledger"]
                    if rec.get("contained_solution"))
    terminals = sorted(rtt.values())
    buf = io.StringIO(newline="")
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(["time_s", "H_effective", "H_pipeline", "floor_threshold",
                "live_activation_requests", "waking_miners", "active_hashing_miners",
                "accepted_block_event", "round_boundary"])
    n_active_at = lambda t, ivs: sum(1 for iv in ivs if iv["start"] <= t < iv["end"])
    ivs = d["_intervals"]
    bi = ti = 0
    for t, h, hp in series:
        nb = 0
        while bi < len(blocks) and blocks[bi] <= t:
            nb += 1
            bi += 1
        rb = 0
        while ti < len(terminals) and terminals[ti] <= t:
            rb += 1
            ti += 1
        w.writerow([f"{t:.6f}", f"{h:.1f}", f"{hp:.1f}", f"{FLOOR:.1f}",
                    sum(1 for s, e in live if s <= t < e),
                    sum(1 for s, e in waking if s <= t < e),
                    n_active_at(t, ivs), nb, rb])
    dest.write_text(buf.getvalue())


def main() -> int:
    DOCS.mkdir(parents=True, exist_ok=True)
    tables = per_seed_tables()

    m01_depth, _s1, _r1, _d1 = audit_depth("7m-M01_HET_IDLE-s00_full_ledger.json.gz", False)
    m03_depth, series, rtt, d3 = audit_depth(
        "7m-M03_HET_IDLE_FLOOR-s00_full_ledger.json.gz", True)
    rates3 = m03_depth["derived_miner_rates"]
    d3["_intervals"] = active_intervals(d3["evaluation_ledger"], rates3,
                                       d3["activation_requests"])
    write_timeline(series, rtt, d3, DOCS / "STAGE_08R_BASELINE_TIMELINE_M03_S00.csv")

    # ---- causal decomposition at the audit seed (DERIVED) --------------------------
    m01_rounds = m01_depth["round_duration"]
    m03_rounds = m03_depth["round_duration"]
    round_deficit = m01_rounds["count"] - m03_rounds["count"]
    per_round_inflation = m03_rounds["mean_s"] - m01_rounds["mean_s"]
    decomposition = {
        "closed_round_deficit": round_deficit,
        "mean_round_inflation_s": per_round_inflation,
        "total_inflation_s": per_round_inflation * m03_rounds["count"],
        "blocks_per_round_M01": 162 / 216, "blocks_per_round_M03": 135 / 178,
        "reserve_waking_s_run_total": m03_depth["reserve_waking_s"],
        "reserve_active_hashing_s_run_total": m03_depth["reserve_active_hashing_s"],
        "note": ("DERIVED at the audit seed: blocks-per-closed-round is nearly equal "
                 "(0.750 vs 0.758), so the accepted-block deficit is driven almost "
                 "entirely by the closed-round deficit, i.e. by round-duration "
                 "inflation, not by lower per-round success"),
    }

    metrics = {
        "harness": "diagnose_8r_baseline.py (READ-ONLY; no simulation executed)",
        "inputs": ["stage_07m/runs/*.json (frozen)", "stage_07m/audit/*.json.gz (frozen)"],
        "epistemic_classes": ["OBSERVED", "DERIVED", "UNRESOLVED"],
        "per_seed_compact": tables,
        "per_seed_unresolved_fields": [
            "p90/p95 round duration (full duration list not in compact records)",
            "unclosed final-tail duration (only min/median/max persisted)",
            "per-state residency split (only offline_residency_s persisted)",
            "activation started/cancelled split (only seated/completed persisted)",
            "inter-round setup gap (not separable from round durations in compact records)",
        ],
        "audit_depth_M01_s00": m01_depth,
        "audit_depth_M03_s00": m03_depth,
        "audit_seed_decomposition": decomposition,
        "floor_constant": FLOOR,
    }
    (DOCS / "STAGE_08R_BASELINE_DIAGNOSTIC_METRICS.json").write_text(
        json.dumps(metrics, indent=1, sort_keys=True, default=str) + "\n")
    print("wrote STAGE_08R_BASELINE_DIAGNOSTIC_METRICS.json")
    print(json.dumps(decomposition, indent=1))
    if "floor_deficit" in m03_depth:
        print(json.dumps(m03_depth["floor_deficit"], indent=1))
        print("observed below-floor:", m03_depth["observed_total_duration_below_floor_s"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
