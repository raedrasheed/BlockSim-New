"""Stage-2B BlockSim integration adapter (S2A-8 / S2B-6).

A thin, documented entry point that lets the existing BlockSim runner invoke the Stage-2
PoCol core WITHOUT replacing the legacy simulator and WITHOUT touching any frozen Stage-1
document.  It maps a BlockSim-style configuration mapping to a `Stage2Config`, runs the
core, and returns round/block/energy results in a declared schema.  The standalone demo
(`python -m Models.PoCol.stage2.demo`) is preserved for testing.

S2B-6 energy labelling: the run's continuous full-participation reference is reported as
``continuous_all_active_control_kwh`` (an accounting reference, NOT a matched CONTROL
simulation), so the run energy vs this reference is never presented as a general PoCol
idle-policy saving.  The constructed matched CONTROL-vs-POCOL_IDLE identity-validation
experiment is exposed SEPARATELY under ``matched_identity_experiment``.
"""
from __future__ import annotations

from typing import Any, Dict, Optional

from .config import Stage2Config, a1_continuous_control_kwh
from .simulator import run_simulation
from .search import SUCCESS_MODEL

# Declared result schema keys (stable contract for BlockSim consumers).
RESULT_SCHEMA_VERSION = "stage3.1"


def stage2config_from_blocksim(blocksim_config: Optional[Dict[str, Any]] = None
                               ) -> Stage2Config:
    """Map a BlockSim-style config mapping to a Stage2Config (unknown keys ignored)."""
    b = dict(blocksim_config or {})

    def pick(*names, default=None):
        for n in names:
            if n in b and b[n] is not None:
                return b[n]
        return default

    kwargs: Dict[str, Any] = {}
    val = pick("num_miners", "Nn", "n_nodes")
    if val is not None:
        kwargs["num_miners"] = int(val)
    val = pick("horizon_T", "simTime", "Tsim")
    if val is not None:
        kwargs["horizon_T"] = float(val)
    val = pick("run_start_time")
    if val is not None:
        kwargs["run_start_time"] = float(val)
    for key in ("P_hash", "P_listen", "P_wake", "P_offline", "nonce_domain_size",
                "difficulty", "batch_size", "base_hash_rate", "reserve_fraction",
                "template_seed", "wake_latency"):
        if key in b and b[key] is not None:
            cur = getattr(Stage2Config, key, None)
            kwargs[key] = type(cur)(b[key]) if isinstance(cur, (int, float)) else b[key]
    return Stage2Config(**kwargs)


def results_schema(run_ctx: Any, cfg: Stage2Config) -> Dict[str, Any]:
    """Return round/block/energy results for a finished run in the declared schema."""
    log_kinds = [o.kind for o in run_ctx.log]
    per_miner_kwh = {mid: run_ctx.miner_energy_joules(mid) / 3_600_000.0
                     for mid in run_ctx.miners}
    queue_terminal = {}
    for rec in run_ctx.event_queue.queued_event_registry.values():
        queue_terminal[rec.queue_status] = queue_terminal.get(rec.queue_status, 0) + 1
    request_terminal = {}
    for dr in run_ctx.driver_request_registry.values():
        request_terminal[dr.status] = request_terminal.get(dr.status, 0) + 1
    out = {
        "schema_version": RESULT_SCHEMA_VERSION,
        "algorithm": "PoCol",
        "mechanism": "idle policy within PoCol",
        "success_model": SUCCESS_MODEL,
        "rounds_executed": run_ctx.round_seq,
        "rounds_accepted": log_kinds.count("accepted_block"),
        "rounds_no_block": log_kinds.count("round_aborted"),
        "loop_result": run_ctx.loop_result.kind,
        "run_disposition": run_ctx.run_disposition,
        "run_end_time": run_ctx.run_end_time,
        "energy_kwh": run_ctx.total_energy_kwh(),
        # S2B-6: an accounting reference (every miner active for the whole horizon), NOT a
        # matched CONTROL simulation — so this is not a general idle-policy saving basis.
        "continuous_all_active_control_kwh": a1_continuous_control_kwh(cfg),
        "residency_reconciles": run_ctx.residency_reconciles(run_ctx.run_end_time),
        "evaluation_ledger_entries": len(run_ctx.evaluation_ledger),
        "per_miner_energy_kwh": per_miner_kwh,
        "queue_terminal_state_counts": queue_terminal,
        "driver_request_terminal_state_counts": request_terminal,
        "config": {"num_miners": cfg.num_miners, "horizon_T": cfg.horizon_T,
                   "nonce_domain_size": cfg.nonce_domain_size, "difficulty": cfg.difficulty},
    }
    out.update(_security_floor_results(run_ctx, cfg))
    return out


def _security_floor_results(run_ctx: Any, cfg: Stage2Config) -> Dict[str, Any]:
    """S3 result fields: security-floor + reserve-activation metrics and reserve energy.

    The security floor is an OPERATIONAL capacity floor only — these fields never assert
    consensus-security equivalence.  Reserve activation may INCREASE energy; it never saves.
    """
    s = run_ctx.security_stats
    pol = cfg.security_floor
    reserve_ids = getattr(run_ctx, "reserve_miner_ids", set())
    P = cfg.per_miner_power
    standby = wake = active = 0.0
    for mid in reserve_ids:
        m = run_ctx.miners.get(mid)
        if m is None:
            continue
        standby += P("RESERVE") * m.duration.get("RESERVE", 0.0)
        wake += P("WAKING") * m.duration.get("WAKING", 0.0)
        active += P("ACTIVE_HASHING") * m.duration.get("ACTIVE_HASHING", 0.0)
    return {
        "security_floor_enabled": pol.enabled,
        "configured_minimum_active_hash_rate": pol.minimum_active_hash_rate,
        "minimum_active_miner_count": pol.minimum_active_miner_count,
        "floor_unattainable_policy": cfg.floor_unattainable_policy,
        "security_floor_observation_count": s["observation_count"],
        "breach_count": s["distinct_breach_count"],
        "reserve_activation_decision_count": s["decision_count"],
        "reserve_activations_seated": s["activations_seated"],
        "reserve_activations_completed": s["activations_completed"],
        "reserve_activations_cancelled": s["activations_cancelled"],
        "floor_unattainable_count": s["floor_unattainable_count"],
        "total_duration_below_floor": s["total_duration_below_floor"],
        "maximum_hash_rate_deficit": s["max_hash_rate_deficit"],
        "reserve_standby_energy_kwh": standby / 3_600_000.0,
        "reserve_wake_energy_kwh": wake / 3_600_000.0,
        "reserve_active_energy_kwh": active / 3_600_000.0,
        "activated_reserve_evaluation_count": s["activated_reserve_evaluation_count"],
    }


def matched_identity_experiment_schema(n_miners: int = 8) -> Dict[str, Any]:
    """S2B-6: expose the CONSTRUCTED matched CONTROL-vs-POCOL_IDLE identity experiment
    SEPARATELY from the run's energy accounting (it validates the residency identity; it
    is not a general PoCol saving)."""
    from .energy_experiment import run_energy_experiment
    res = run_energy_experiment(n_miners=n_miners)
    return {
        "scenario": res.scenario,
        "note": "constructed identity-validation scenario; not a general PoCol saving",
        "success_model": res.success_model,
        "winner": res.winner,
        "winning_nonce": res.winning_nonce,
        "round_end": res.round_end,
        "n_idlers": res.n_idlers,
        "E_control_j": res.total_control_j,
        "E_pocol_idle_j": res.total_idle_j,
        "scenario_saving_j": res.saving_j,
        "max_abs_identity_residual_j": res.max_abs_residual_j,
    }


def run_pocol_stage2(blocksim_config: Optional[Dict[str, Any]] = None,
                     run_id: Any = "blocksim",
                     include_matched_experiment: bool = True) -> Dict[str, Any]:
    """BlockSim entry point: map config -> run the Stage-2 PoCol core -> declared results."""
    cfg = stage2config_from_blocksim(blocksim_config)
    run_ctx = run_simulation(cfg, run_id=run_id)
    out = results_schema(run_ctx, cfg)
    if include_matched_experiment:
        out["matched_identity_experiment"] = matched_identity_experiment_schema()
    return out
