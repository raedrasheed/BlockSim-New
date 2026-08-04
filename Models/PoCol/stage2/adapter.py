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
from .security import SecurityFloorPolicy, FLOOR_UNATTAINABLE_POLICIES
from .leases import RangeLeasePolicy, REASSIGNED_PRIMARY_WORK, REASSIGNED_RESERVE_WORK
from .adversarial import (AdversarialPolicy, IncentivePolicy, ACTOR_CLASSES, BEHAVIOUR_FLAGS,
                          SOLUTION_RELEASE_POLICIES, ACCOUNTING_MODES,
                          ADVERSARIAL_COVERAGE_GAP_NO_BLOCK)
from . import adversarial_runtime as _adv

# Declared result schema keys (stable contract for BlockSim consumers).
# stage5c.1 ADDS the Stage-5C record-derived-accounting block on top of stage5b.1.  Every earlier
# Stage-5 and Stage-5A key is retained unchanged, and every Stage-5/5A/5B field is inert (zero, or
# NA for q_adv) when the Stage-5 model is disabled — which is the default.
RESULT_SCHEMA_VERSION = "stage5c.1"


def _range_lease_from_blocksim(b: Dict[str, Any]) -> Optional[RangeLeasePolicy]:
    """S4-8: build a VALIDATED immutable RangeLeasePolicy from a BlockSim config mapping.

    Returns ``None`` when no lease keys are present (keeping the disabled default).  Rejects
    unsupported policy names and negative durations/timeouts/latencies/tolerances by raising
    ``ValueError`` (from ``RangeLeasePolicy.__post_init__``).
    """
    lease_keys = ("range_lease_enabled", "lease_duration", "progress_timeout",
                  "reassignment_enabled", "reassignment_selection_policy",
                  "maximum_reassignments_per_slice", "reassignment_wake_latency",
                  "no_eligible_miner_policy", "lease_tolerance")
    if not any(k in b and b[k] is not None for k in lease_keys):
        return None
    kwargs: Dict[str, Any] = {"enabled": bool(b.get("range_lease_enabled", True))}
    if b.get("lease_duration") is not None:
        kwargs["lease_duration"] = float(b["lease_duration"])
    if b.get("progress_timeout") is not None:
        kwargs["progress_timeout"] = float(b["progress_timeout"])
    if b.get("reassignment_enabled") is not None:
        kwargs["reassignment_enabled"] = bool(b["reassignment_enabled"])
    if b.get("reassignment_selection_policy") is not None:
        kwargs["reassignment_selection_policy"] = str(b["reassignment_selection_policy"])
    if b.get("maximum_reassignments_per_slice") is not None:
        kwargs["maximum_reassignments_per_slice"] = int(b["maximum_reassignments_per_slice"])
    if b.get("reassignment_wake_latency") is not None:
        kwargs["reassignment_wake_latency"] = float(b["reassignment_wake_latency"])
    if b.get("no_eligible_miner_policy") is not None:
        kwargs["no_eligible_miner_policy"] = str(b["no_eligible_miner_policy"])
    if b.get("lease_tolerance") is not None:
        kwargs["lease_tolerance"] = float(b["lease_tolerance"])
    return RangeLeasePolicy(**kwargs)                       # __post_init__ validates


def _security_floor_from_blocksim(b: Dict[str, Any]) -> Optional[SecurityFloorPolicy]:
    """S3A-8: build a VALIDATED immutable SecurityFloorPolicy from a BlockSim config mapping.

    Returns ``None`` when no floor keys are present (keeping the disabled default).  Rejects
    unsupported policy names and negative rates/counts/latencies/tolerances by raising
    ``ValueError`` (from ``SecurityFloorPolicy.__post_init__``); an explicitly invalid config
    therefore never yields a usable policy.
    """
    floor_keys = ("security_floor_enabled", "minimum_active_hash_rate",
                  "minimum_active_miner_count", "activation_trigger_mode",
                  "reserve_selection_policy", "maximum_activations_per_round",
                  "activation_wake_latency", "floor_tolerance")
    if not any(k in b and b[k] is not None for k in floor_keys):
        return None
    default = SecurityFloorPolicy()
    kwargs: Dict[str, Any] = {"enabled": bool(b.get("security_floor_enabled", True))}
    if b.get("minimum_active_hash_rate") is not None:
        kwargs["minimum_active_hash_rate"] = float(b["minimum_active_hash_rate"])
    if b.get("minimum_active_miner_count") is not None:
        kwargs["minimum_active_miner_count"] = int(b["minimum_active_miner_count"])
    if b.get("activation_trigger_mode") is not None:
        kwargs["activation_trigger_mode"] = str(b["activation_trigger_mode"])
    if b.get("reserve_selection_policy") is not None:
        kwargs["reserve_selection_policy"] = str(b["reserve_selection_policy"])
    if b.get("maximum_activations_per_round") is not None:
        kwargs["maximum_activations_per_round"] = int(b["maximum_activations_per_round"])
    if b.get("activation_wake_latency") is not None:
        kwargs["activation_wake_latency"] = float(b["activation_wake_latency"])
    if b.get("floor_tolerance") is not None:
        kwargs["floor_tolerance"] = float(b["floor_tolerance"])
    return SecurityFloorPolicy(**kwargs)                    # __post_init__ validates


def _adversarial_from_blocksim(b: Dict[str, Any]) -> Optional[AdversarialPolicy]:
    """S5-2: build a VALIDATED immutable AdversarialPolicy from a BlockSim config mapping.

    Returns ``None`` when no adversarial key is present, so the DISABLED default stands and the
    accepted Stage-4C behaviour is preserved exactly.  Unsupported actor classes, behaviour
    flags, release policies and out-of-range rates/fractions are rejected by
    ``AdversarialPolicy.__post_init__``.  No adversarial key may change the fixed SHA-256 target
    or difficulty (S5-26) — ``difficulty`` is not settable from this mapping.
    """
    keys = ("adversarial_enabled", "adversarial_seed", "audit_detection_probability",
            "solution_release_policy", "solution_withholding_delay",
            "delayed_wake_extra_latency", "free_rider_work_fraction",
            "reported_hash_rate_multiplier", "false_exhaustion_claim_offset",
            "false_exhaustion_claims_range_end",
            "progress_withholding_fraction", "assignment_split_count",
            "sybil_identity_count", "coordinator_uses_reported_hash_rate",
            "maximum_actions_per_round", "q_adv_threshold", "out_of_range_nonce_offset",
            "adversarial_entities", "miner_behaviours")
    if not any(k in b and b[k] is not None for k in keys):
        return None
    kw: Dict[str, Any] = {"enabled": bool(b.get("adversarial_enabled", True))}
    if b.get("adversarial_seed") is not None:
        kw["deterministic_seed"] = int(b["adversarial_seed"])
    for key, cast in (("audit_detection_probability", float),
                      ("solution_withholding_delay", float),
                      ("delayed_wake_extra_latency", float),
                      ("free_rider_work_fraction", float),
                      ("reported_hash_rate_multiplier", float),
                      ("false_exhaustion_claim_offset", int),
                      ("progress_withholding_fraction", float),
                      ("assignment_split_count", int), ("sybil_identity_count", int),
                      ("maximum_actions_per_round", int), ("q_adv_threshold", float),
                      ("out_of_range_nonce_offset", int)):
        if b.get(key) is not None:
            kw[key] = cast(b[key])
    if b.get("solution_release_policy") is not None:
        srp = str(b["solution_release_policy"])
        if srp not in SOLUTION_RELEASE_POLICIES:
            raise ValueError(f"unsupported solution_release_policy: {srp!r}")
        kw["solution_release_policy"] = srp
    if b.get("coordinator_uses_reported_hash_rate") is not None:
        kw["coordinator_uses_reported_hash_rate"] = bool(b["coordinator_uses_reported_hash_rate"])
    # S5B-8: ``false_exhaustion_claims_range_end`` was declared and consumed at runtime but never
    # mapped here, so a configured ``false_exhaustion_claim_offset`` had NO effect through the
    # BlockSim path (range-end claiming, on by default, always won).  Both now travel together and
    # a configured offset means the same thing through every entry point.
    if b.get("false_exhaustion_claims_range_end") is not None:
        kw["false_exhaustion_claims_range_end"] = bool(b["false_exhaustion_claims_range_end"])
    if b.get("adversarial_entities") is not None:
        ents = []
        for ent in b["adversarial_entities"]:
            eid, klass, mids, coal = ent
            if str(klass) not in ACTOR_CLASSES:
                raise ValueError(f"unsupported actor_class: {klass!r}")
            ents.append((eid, str(klass), tuple(mids), coal))
        kw["entities"] = tuple(ents)
    if b.get("miner_behaviours") is not None:
        behs = []
        for beh in b["miner_behaviours"]:
            rseq, mid, flags = beh
            for f in flags:
                if str(f) not in BEHAVIOUR_FLAGS:
                    raise ValueError(f"unsupported behaviour flag: {f!r}")
            behs.append((int(rseq), mid, tuple(str(f) for f in flags)))
        kw["miner_behaviours"] = tuple(behs)
    return AdversarialPolicy(**kw)


def _incentive_from_blocksim(b: Dict[str, Any]) -> Optional[IncentivePolicy]:
    """S5-2: build a VALIDATED immutable IncentivePolicy from a BlockSim config mapping.

    Returns ``None`` when no incentive key is present, so the disabled, all-rates-zero default
    stands.  Negative rates and unsupported accounting modes are rejected.  These are MODEL
    PARAMETERS only: no value is claimed to be optimal, equilibrium-producing, fair or
    Sybil-resistant, and no configuration proves incentive compatibility.
    """
    keys = ("incentive_enabled", "r_work", "r_avail", "r_win", "r_reserve", "r_reassign",
            "q_abandon", "q_false", "q_invalid", "reward_deduplication_policy",
            "entity_aggregation_enabled", "penalise_crash_faults")
    if not any(k in b and b[k] is not None for k in keys):
        return None
    kw: Dict[str, Any] = {"enabled": bool(b.get("incentive_enabled", True))}
    for key in ("r_work", "r_avail", "r_win", "r_reserve", "r_reassign",
                "q_abandon", "q_false", "q_invalid"):
        if b.get(key) is not None:
            kw[key] = float(b[key])
    if b.get("reward_deduplication_policy") is not None:
        mode = str(b["reward_deduplication_policy"])
        if mode not in ACCOUNTING_MODES:
            raise ValueError(f"unsupported reward_deduplication_policy: {mode!r}")
        kw["reward_deduplication_policy"] = mode
    for key in ("entity_aggregation_enabled", "penalise_crash_faults"):
        if b.get(key) is not None:
            kw[key] = bool(b[key])
    return IncentivePolicy(**kw)


def stage2config_from_blocksim(blocksim_config: Optional[Dict[str, Any]] = None
                               ) -> Stage2Config:
    """Map a BlockSim-style config mapping to a Stage2Config (unknown keys ignored).

    S3A-8: this also maps and VALIDATES the Stage-3 security-floor / reserve-activation
    configuration (``P_reserve``, the security-floor policy fields and
    ``floor_unattainable_policy``) into an immutable, validated ``SecurityFloorPolicy``.
    """
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
    for key in ("P_hash", "P_listen", "P_wake", "P_offline", "P_reserve",
                "nonce_domain_size", "difficulty", "batch_size", "base_hash_rate",
                "reserve_fraction", "template_seed", "wake_latency"):
        if key in b and b[key] is not None:
            cur = getattr(Stage2Config, key, None)
            kwargs[key] = type(cur)(b[key]) if isinstance(cur, (int, float)) else b[key]
    # S3A-8: floor-unattainable policy (validated against the declared vocabulary).
    if b.get("floor_unattainable_policy") is not None:
        fup = str(b["floor_unattainable_policy"])
        if fup not in FLOOR_UNATTAINABLE_POLICIES:
            raise ValueError(f"unsupported floor_unattainable_policy: {fup!r}")
        kwargs["floor_unattainable_policy"] = fup
    # S3A-8: the validated immutable security-floor policy.
    pol = _security_floor_from_blocksim(b)
    if pol is not None:
        kwargs["security_floor"] = pol
    # S4-8: the validated immutable range-lease / reassignment policy.
    lease_pol = _range_lease_from_blocksim(b)
    if lease_pol is not None:
        kwargs["range_lease"] = lease_pol
    # S5-2: the validated immutable Stage-5 adversarial + incentive policies (both DISABLED
    # unless the mapping explicitly configures them).
    adv_pol = _adversarial_from_blocksim(b)
    if adv_pol is not None:
        kwargs["adversarial"] = adv_pol
    inc_pol = _incentive_from_blocksim(b)
    if inc_pol is not None:
        kwargs["incentive"] = inc_pol
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
    out.update(_range_lease_results(run_ctx, cfg))
    out.update(_adversarial_incentive_results(run_ctx, cfg))
    return out


def _adversarial_incentive_results(run_ctx: Any, cfg: Stage2Config) -> Dict[str, Any]:
    """S5-11: the Stage-5 adversarial + incentive result block (all inert when disabled).

    WHAT THESE FIELDS ARE: measurements of MODELED bounded behaviours under the accepted PoCol
    core.  WHAT THEY ARE NOT: they do not establish incentive compatibility, fairness, Sybil
    resistance, selfish-mining resistance, coalition resistance, common-prefix security,
    chain-quality security, or Bitcoin/PoW-equivalent security.  Stage 5 measures outcomes; it
    does not prove PoCol defeats any of these behaviours.

    ``q_adv`` is reported as NA (``None``) for any interval in which the ACTUAL active hash rate
    is zero — an NA interval is never compared against the threshold and never enters the
    time-weighted mean.  The security floor remains the OPERATIONAL ACTIVE-CAPACITY floor only.
    """
    s = run_ctx.adversarial_stats
    q = _adv.q_adv_summary(run_ctx)
    ledger_net = sum(e.sign * e.amount for e in run_ctx.incentive_ledger)
    ledger_reward = sum(e.amount for e in run_ctx.incentive_ledger if e.sign > 0)
    ledger_penalty = sum(e.amount for e in run_ctx.incentive_ledger if e.sign < 0)
    per_entity: Dict[Any, float] = {}
    for e in run_ctx.incentive_ledger:
        per_entity[e.EntityID] = per_entity.get(e.EntityID, 0.0) + e.sign * e.amount
    adversarial_miners = sorted(mid for mid in run_ctx.miners
                                if _adv.is_adversarial_miner(run_ctx, mid))
    return {
        "adversarial_model_enabled": bool(cfg.adversarial.enabled),
        "incentive_model_enabled": bool(cfg.incentive.enabled),
        "adversarial_entity_count": len(run_ctx.adversarial_entities),
        "adversarial_miner_count": len(adversarial_miners),
        "behaviour_profile_count": len(run_ctx.behaviour_profiles),
        # --- behaviour execution counters (S5-4 .. S5-9) ---
        "free_rider_count": s["free_rider_count"],
        "hash_rate_misreport_count": s["hash_rate_misreport_count"],
        "allocation_distortion_max_ratio": s["allocation_distortion_max_ratio"],
        "assignment_split_count": s["assignment_split_count"],
        "progress_withholding_count": s["progress_withholding_count"],
        "adversarial_duplicate_evaluation_count": s["adversarial_duplicate_evaluation_count"],
        "false_exhaustion_attempted": s["false_exhaustion_attempted"],
        "false_exhaustion_detected": s["false_exhaustion_detected"],
        "false_exhaustion_accepted": s["false_exhaustion_accepted"],
        "coverage_gap_nonce_count": s["coverage_gap_nonce_count"],
        "adversarial_coverage_gap_round_count": s["adversarial_coverage_gap_round_count"],
        "adversarial_coverage_gap_label": ADVERSARIAL_COVERAGE_GAP_NO_BLOCK,
        "solution_withholding_count": s["solution_withholding_count"],
        "withheld_released_count": s["withheld_released_count"],
        "withheld_never_released_count": s["withheld_never_released_count"],
        "withheld_release_too_late_count": s["withheld_release_too_late_count"],
        "withheld_total_hidden_duration": s["withheld_total_hidden_duration"],
        "delayed_wake_count": s["delayed_wake_count"],
        "out_of_range_attempt_count": s["out_of_range_attempt_count"],
        "invalid_action_rejection_count": s["invalid_action_rejection_count"],
        # --- three-value layer divergence (S5-3) ---
        "progress_claim_count": len(run_ctx.progress_claims),
        "actual_reported_divergence_count": s["actual_reported_divergence_count"],
        "reported_accepted_divergence_count": s["reported_accepted_divergence_count"],
        # --- q_adv(t) over ACTUAL active hash rates (S5-11); NA when H_active == 0 ---
        "maximum_q_adv": q["maximum_q_adv"],
        "time_weighted_q_adv": q["time_weighted_q_adv"],
        "q_adv_threshold": cfg.adversarial.q_adv_threshold,
        "duration_above_q_adv_threshold": q["duration_above_q_adv_threshold"],
        "q_adv_active_duration": q["q_adv_active_duration"],
        "q_adv_na_duration": q["q_adv_na_duration"],
        # --- incentive ledger (S5-8 / S5-10) ---
        "incentive_ledger_entries": len(run_ctx.incentive_ledger),
        "incentive_reward_total": ledger_reward,
        "incentive_penalty_total": ledger_penalty,
        "incentive_net_total": ledger_net,
        "incentive_reconciliation_residual": _adv.incentive_reconciliation_residual(run_ctx),
        "work_reward_total": s["work_reward_total"],
        "availability_reward_total": s["availability_reward_total"],
        "winner_reward_total": s["winner_reward_total"],
        "reserve_activation_reward_total": s["reserve_activation_reward_total"],
        "reassignment_reward_total": s["reassignment_reward_total"],
        "abandonment_penalty_total": s["abandonment_penalty_total"],
        "false_claim_penalty_total": s["false_claim_penalty_total"],
        "invalid_message_penalty_total": s["invalid_message_penalty_total"],
        "naive_identity_reward_total": s["naive_identity_reward_total"],
        "deduplicated_entity_reward_total": s["deduplicated_entity_reward_total"],
        "reward_deduplication_policy": cfg.incentive.reward_deduplication_policy,
        "per_entity_net_reward": per_entity,
        # --- S5A-1 three-value frontier separation (the PHYSICAL frontier never rewinds) ---
        "accepted_frontier_record_count": s["accepted_frontier_record_count"],
        "accepted_below_actual_count": s["accepted_below_actual_count"],
        "physical_frontier_rewind_count": s["physical_frontier_rewind_count"],
        "frontier_reconciliation": _adv.frontier_reconciliation(run_ctx),
        # --- S5A-2 unique-nonce work-reward union ---
        "unique_rewarded_nonce_count": s["unique_rewarded_nonce_count"],
        "physical_evaluation_count": s["physical_evaluation_count"],
        "adversarial_reevaluation_count": s["adversarial_reevaluation_count"],
        "duplicate_work_reward_prevented_count": s["duplicate_work_reward_prevented_count"],
        "work_reward_union_residual": s["work_reward_union_residual"],
        # --- S5A-3 reported-rate allocation (sizing only; never physical capacity) ---
        "reported_rate_allocation_enabled": bool(
            cfg.adversarial.coordinator_uses_reported_hash_rate),
        "reported_rate_allocation_rounds": s["reported_rate_allocation_rounds"],
        "allocation_range_size_distortion_max_ratio":
            s["allocation_range_size_distortion_max_ratio"],
        # --- S5A-4 executable splitting / declared identities ---
        "subassignment_count": s["subassignment_count"],
        "virtual_identity_count": s["virtual_identity_count"],
        "subassignment_capacity_residual": s["subassignment_capacity_residual"],
        # --- S5A-5 EXECUTED abandonment (a penalty requires an action) ---
        "abandonment_action_count": s["abandonment_action_count"],
        "abandoned_nonce_count": s["abandoned_nonce_count"],
        "abandonment_penalty_without_action_count":
            s["abandonment_penalty_without_action_count"],
        # --- S5A-6 delayed-wake impact measured from REAL floor observations ---
        "delayed_wake_below_floor_overlap_total": sum(
            r.below_floor_overlap for r in run_ctx.delayed_wake_actions.values()),
        "delayed_wake_another_reserve_activated_count": sum(
            1 for r in run_ctx.delayed_wake_actions.values() if r.another_reserve_activated),
        "delayed_wake_incremental_energy_j": sum(
            r.incremental_wake_energy_j for r in run_ctx.delayed_wake_actions.values()),
        "attack_induced_floor_breach_duration": s["attack_induced_floor_breach_duration"],
        # --- S5A-7 declared-field enforcement ---
        "actions_rejected_over_limit": s["actions_rejected_over_limit"],
        "withheld_alternative_solution_won_count":
            s["withheld_alternative_solution_won_count"],
        # --- S5B-1 first-physical-evaluator work-reward ownership ---
        "ownership_reconciliation": _adv.ownership_reconciliation(run_ctx),
        # --- S5B-4 delayed wake across EVERY real wake lifecycle ---
        "delayed_wake_primary_count": s["delayed_wake_primary_count"],
        "delayed_wake_reserve_activation_count": s["delayed_wake_reserve_activation_count"],
        "delayed_wake_path_a_reassignment_count": s["delayed_wake_path_a_reassignment_count"],
        "delayed_wake_path_b_reserve_count": s["delayed_wake_path_b_reserve_count"],
        "delayed_wake_unspecified_lifecycle_count":
            s["delayed_wake_unspecified_lifecycle_count"],
        "delayed_wake_unattributed_refused": s["delayed_wake_unattributed_refused"],
        "delayed_wake_replay_no_effect_count": s["delayed_wake_replay_no_effect_count"],
        "delayed_wake_realised_extra_delay_total": sum(
            r.realised_extra_delay for r in run_ctx.delayed_wake_actions.values()),
        # --- S5B-6 conserved effective capacity under splitting / identities ---
        "subassignment_accounting": _adv.subassignment_accounting(
            run_ctx, run_ctx.current_round_context) if run_ctx.current_round_context else
            {"rows": [], "max_physical_capacity_residual": 0.0},
        "virtual_identity_accounting": _adv.virtual_identity_accounting(
            run_ctx, run_ctx.current_round_context) if run_ctx.current_round_context else
            {"rows": [], "physical_capacity_granted_by_identities": 0.0},
        "subassignment_mapped_evaluation_count": s["subassignment_mapped_evaluation_count"],
        "subassignment_unmapped_evaluation_count": s["subassignment_unmapped_evaluation_count"],
        "entity_physical_capacity_residual": s["entity_physical_capacity_residual"],
        "virtual_identity_physical_capacity_granted":
            s["virtual_identity_physical_capacity_granted"],
        # --- S5B-7 coverage separation (claim overstatement vs REAL unsearched suffix) ---
        "claim_overstatement_total": s["claim_overstatement_total"],
        "abandonment_coverage_gap_rounds": s["abandonment_coverage_gap_rounds"],
        # --- S5B-8 complete adapter + metric semantics ---
        "false_exhaustion_claims_range_end": bool(
            cfg.adversarial.false_exhaustion_claims_range_end),
        "false_exhaustion_claim_offset": int(cfg.adversarial.false_exhaustion_claim_offset),
        "evaluation_ledger_nonce_total": _evaluation_ledger_nonce_total(run_ctx),
        # S5C-2: the residual is ALWAYS the real absolute difference between the independently
        # accumulated physical counter and the immutable evaluation ledger.  It is never forced
        # to zero because the Stage-5 model happens to be disabled — that exemption hid a
        # counter which really did read zero beside a non-empty ledger.
        "physical_evaluation_ledger_residual": abs(
            s["physical_evaluation_count"] - _evaluation_ledger_nonce_total(run_ctx)),
        # --- S5C-1 record-derived amplification (requested counts can never override records) ---
        "entity_reconciliation": _adv.entity_reconciliation(run_ctx),
        "assignment_split_amplification_ratio": s["assignment_split_amplification_ratio"],
        "identity_multiplication_amplification_ratio":
            s["identity_multiplication_amplification_ratio"],
        # --- explicit scope statement carried in the results themselves ---
        "stage5_claim_scope": (
            "Stage 5 MODELS bounded adversarial behaviours and MEASURES outcomes under the "
            "accepted PoCol core.  It does NOT establish incentive compatibility, fairness, "
            "Sybil resistance, selfish-mining resistance, coalition resistance, common-prefix "
            "security, chain-quality security, or Bitcoin/PoW-equivalent security.  The "
            "energy-saving mechanism remains the idle policy within PoCol; nonce-domain "
            "partitioning alone is NOT an energy-saving mechanism.  The security floor remains "
            "an operational active-capacity floor only.  Dynamic difficulty remains excluded "
            "and no Stage-5 parameter changes the fixed SHA-256 target or difficulty."),
    }


def _evaluation_ledger_nonce_total(run_ctx: Any) -> int:
    """S5B-8: the nonce positions the EXECUTION ledger actually records.

    ``physical_evaluation_count`` must equal this whenever the Stage-5 model is enabled — the two
    are counted at the same single authority, with or without range leases.  A zero physical count
    beside a non-empty evaluation ledger is therefore impossible.
    """
    return sum(max(0, r.interval_end - r.interval_start) for r in run_ctx.evaluation_ledger)


def _res_delta(start: Any, end: Any) -> float:
    """A non-negative residency-ledger delta over an interval; 0.0 when either end is unknown."""
    if start is None or end is None:
        return 0.0
    return max(0.0, end - start)


def reassignment_energy_report(run_ctx: Any, cfg: Stage2Config) -> Dict[str, Any]:
    """S4C-1/S4C-2: a COMPLETE per-request reassignment-energy attribution in which EVERY component
    is a TRUE request-interval residency-ledger DELTA (never the miner's whole-run cumulative
    residency), plus five independent per-component residuals, an interval-overlap audit and an
    aggregate-vs-integrated-run-residency bound.

    Five components per request (COMPLETED / FAILED / CANCELLED alike):
      1 predecessor ACTIVE energy over [lease_start, revocation];
      2 predecessor IDLE/OFFLINE energy over [revocation, request_terminal];
      3 reassignee STANDBY (reserve+low+offline) energy over [seat, wake_start] (or [seat, terminal]
        when the wake never started);
      4 reassignment WAKE energy over [wake_start, wake_end];
      5 reassigned ACTIVE-hashing energy over [search_start, search_end].

    A chained (reassigned) predecessor's active work is already owned by the request that
    provisioned it (its component 5), so component 1 is NOT re-charged for it — no residency second
    is charged to two requests.  ``max_request_energy_residual_j`` is the largest of the five
    per-component residuals over all requests (0.0 J when every component reconciles).
    ``overlapping_charged_interval_count`` proves no miner-state residency interval is charged
    twice, and the aggregate per (miner, state) never exceeds P_state x that miner's total run
    residency.
    """
    P = cfg.per_miner_power
    Pw, Ph = P("WAKING"), P("ACTIVE_HASHING")
    Pres, Plow, Poff = P("RESERVE"), P("LOW_POWER_LISTEN"), P("OFFLINE")
    P_OF = {"WAKING": Pw, "ACTIVE_HASHING": Ph, "RESERVE": Pres,
            "LOW_POWER_LISTEN": Plow, "OFFLINE": Poff}
    reassigned_kinds = (REASSIGNED_PRIMARY_WORK, REASSIGNED_RESERVE_WORK)
    TOL = 1e-9

    charged: Dict[Any, list] = {}      # (miner, state) -> [(lo, hi), ...] cumulative-residency spans

    def _claim(miner: Any, state: str, lo: Any, hi: Any) -> None:
        if lo is None or hi is None or (hi - lo) <= TOL:
            return
        charged.setdefault((miner, state), []).append((lo, hi))

    def _consistency_resid(power: float, miner: Any, state: str, lo: Any, hi: Any) -> float:
        """Snapshot-vs-final-ledger consistency: a valid charged span is ordered and lies within
        [0, final cumulative residency]; any violation is a real (non-zero) residual."""
        if lo is None or hi is None or miner is None:
            return 0.0                                  # no ledger to reconcile a snapshot against
        final = miner.duration.get(state, 0.0)
        bad = 0.0
        if hi < lo:
            bad += (lo - hi)
        if hi > final + TOL:
            bad += (hi - final)
        if lo < -TOL:
            bad += (-lo)
        return power * bad

    def _time_resid(power: float, snap_lo: Any, snap_hi: Any, t_lo: Any, t_hi: Any) -> float:
        """A provably single-continuous-state interval: the ledger delta must equal the wall
        interval (energy = power x that duration)."""
        if None in (snap_lo, snap_hi, t_lo, t_hi):
            return 0.0
        return power * abs((snap_hi - snap_lo) - (t_hi - t_lo))

    rows = []
    agg = {"predecessor_active_energy_j": 0.0, "predecessor_idle_or_offline_energy_j": 0.0,
           "reassignee_standby_energy_j": 0.0, "reassignment_wake_energy_j": 0.0,
           "reassignment_active_hashing_energy_j": 0.0}
    comp_resid = {"predecessor_active_j": 0.0, "predecessor_idle_or_offline_j": 0.0,
                  "reassignee_standby_j": 0.0, "reassignment_wake_j": 0.0,
                  "reassignment_active_hashing_j": 0.0}
    counts = {"COMPLETED": 0, "FAILED": 0, "CANCELLED": 0}

    for req in run_ctx.reassignment_requests.values():
        pm = run_ctx.miners.get(req.predecessor_MinerID)
        cm = run_ctx.miners.get(req.new_MinerID)
        pred_lease = run_ctx.range_leases.get(req.predecessor_lease_id)
        pred_kind = pred_lease.assignment_kind if pred_lease is not None else None
        counts[req.status] = counts.get(req.status, 0) + 1

        # (1) predecessor ACTIVE energy over [lease_start, revocation].  A chained predecessor's
        # active work was already charged as its provisioning request's component 5 -> not re-charged.
        a_ls = pred_lease.active_residency_at_lease_start if pred_lease is not None else None
        a_rev = req.predecessor_active_residency_at_revocation
        if pred_kind in reassigned_kinds:
            pred_active_j, r1 = 0.0, 0.0
        else:
            pred_active_j = Ph * _res_delta(a_ls, a_rev)
            r1 = _consistency_resid(Ph, pm, "ACTIVE_HASHING", a_ls, a_rev)
            _claim(req.predecessor_MinerID, "ACTIVE_HASHING", a_ls, a_rev)

        # (2) predecessor IDLE/OFFLINE energy over [revocation, request_terminal].
        low_lo, low_hi = (req.predecessor_low_residency_at_revocation,
                          req.predecessor_low_residency_at_request_terminal)
        off_lo, off_hi = (req.predecessor_offline_residency_at_revocation,
                          req.predecessor_offline_residency_at_request_terminal)
        pred_idle_j = Plow * _res_delta(low_lo, low_hi) + Poff * _res_delta(off_lo, off_hi)
        r2 = (_consistency_resid(Plow, pm, "LOW_POWER_LISTEN", low_lo, low_hi)
              + _consistency_resid(Poff, pm, "OFFLINE", off_lo, off_hi))
        # the predecessor is idled continuously over [revocation, terminal]; the idle-state deltas
        # must sum to that wall interval.
        if req.revocation_time is not None and req.terminal_time is not None \
                and low_hi is not None and off_hi is not None:
            idle_delta = _res_delta(low_lo, low_hi) + _res_delta(off_lo, off_hi)
            r2 += max(Plow, Poff) * abs(idle_delta - (req.terminal_time - req.revocation_time))
        _claim(req.predecessor_MinerID, "LOW_POWER_LISTEN", low_lo, low_hi)
        _claim(req.predecessor_MinerID, "OFFLINE", off_lo, off_hi)

        # (3) reassignee STANDBY over [seat, wake_start] (or [seat, terminal] if the wake never ran).
        standby_j = (Pres * _res_delta(req.reassignee_reserve_residency_at_seat,
                                       req.reassignee_reserve_residency_at_wake_start)
                     + Plow * _res_delta(req.reassignee_low_residency_at_seat,
                                         req.reassignee_low_residency_at_wake_start)
                     + Poff * _res_delta(req.reassignee_offline_residency_at_seat,
                                         req.reassignee_offline_residency_at_wake_start))
        r3 = (_consistency_resid(Pres, cm, "RESERVE",
                                 req.reassignee_reserve_residency_at_seat,
                                 req.reassignee_reserve_residency_at_wake_start)
              + _consistency_resid(Plow, cm, "LOW_POWER_LISTEN",
                                   req.reassignee_low_residency_at_seat,
                                   req.reassignee_low_residency_at_wake_start)
              + _consistency_resid(Poff, cm, "OFFLINE",
                                   req.reassignee_offline_residency_at_seat,
                                   req.reassignee_offline_residency_at_wake_start))
        standby_end_t = req.started_at if req.started_at is not None else req.terminal_time
        if req.seated_at is not None and standby_end_t is not None \
                and req.reassignee_reserve_residency_at_wake_start is not None:
            standby_delta = (_res_delta(req.reassignee_reserve_residency_at_seat,
                                        req.reassignee_reserve_residency_at_wake_start)
                             + _res_delta(req.reassignee_low_residency_at_seat,
                                          req.reassignee_low_residency_at_wake_start)
                             + _res_delta(req.reassignee_offline_residency_at_seat,
                                          req.reassignee_offline_residency_at_wake_start))
            r3 += max(Pres, Plow, Poff) * abs(standby_delta - (standby_end_t - req.seated_at))
        _claim(req.new_MinerID, "RESERVE", req.reassignee_reserve_residency_at_seat,
               req.reassignee_reserve_residency_at_wake_start)
        _claim(req.new_MinerID, "LOW_POWER_LISTEN", req.reassignee_low_residency_at_seat,
               req.reassignee_low_residency_at_wake_start)
        _claim(req.new_MinerID, "OFFLINE", req.reassignee_offline_residency_at_seat,
               req.reassignee_offline_residency_at_wake_start)

        # (4) WAKE over [wake_start, wake_end] (continuous WAKING; not omitted when the wake fails).
        wake_end_t = req.completed_at if req.completed_at is not None else req.terminal_time
        wake_j = Pw * _res_delta(req.wake_residency_at_start, req.wake_residency_at_end)
        r4 = _time_resid(Pw, req.wake_residency_at_start, req.wake_residency_at_end,
                         req.started_at, wake_end_t) \
            + _consistency_resid(Pw, cm, "WAKING", req.wake_residency_at_start,
                                 req.wake_residency_at_end)
        _claim(req.new_MinerID, "WAKING", req.wake_residency_at_start, req.wake_residency_at_end)

        # (5) reassigned ACTIVE-hashing over [search_start, search_end] (continuous ACTIVE_HASHING).
        active_j = Ph * _res_delta(req.active_residency_at_search_start,
                                   req.active_residency_at_search_end)
        r5 = _time_resid(Ph, req.active_residency_at_search_start,
                         req.active_residency_at_search_end,
                         req.reassigned_search_start_time, req.reassigned_search_end_time) \
            + _consistency_resid(Ph, cm, "ACTIVE_HASHING", req.active_residency_at_search_start,
                                 req.active_residency_at_search_end)
        _claim(req.new_MinerID, "ACTIVE_HASHING", req.active_residency_at_search_start,
               req.active_residency_at_search_end)

        agg["predecessor_active_energy_j"] += pred_active_j
        agg["predecessor_idle_or_offline_energy_j"] += pred_idle_j
        agg["reassignee_standby_energy_j"] += standby_j
        agg["reassignment_wake_energy_j"] += wake_j
        agg["reassignment_active_hashing_energy_j"] += active_j
        comp_resid["predecessor_active_j"] = max(comp_resid["predecessor_active_j"], r1)
        comp_resid["predecessor_idle_or_offline_j"] = \
            max(comp_resid["predecessor_idle_or_offline_j"], r2)
        comp_resid["reassignee_standby_j"] = max(comp_resid["reassignee_standby_j"], r3)
        comp_resid["reassignment_wake_j"] = max(comp_resid["reassignment_wake_j"], r4)
        comp_resid["reassignment_active_hashing_j"] = \
            max(comp_resid["reassignment_active_hashing_j"], r5)
        rows.append({
            "RangeReassignmentRequestID": req.RangeReassignmentRequestID, "status": req.status,
            "needs_stage3_wake": req.needs_stage3_wake,
            "predecessor_MinerID": req.predecessor_MinerID, "reassignee_MinerID": req.new_MinerID,
            "seated_at": req.seated_at, "started_at": req.started_at,
            "completed_at": req.completed_at, "search_start": req.reassigned_search_start_time,
            "search_end": req.reassigned_search_end_time, "terminal_time": req.terminal_time,
            "predecessor_active_energy_before_revocation_j": pred_active_j,
            "predecessor_idle_or_offline_energy_after_revocation_j": pred_idle_j,
            "reassignee_standby_energy_before_wake_j": standby_j,
            "reassignment_wake_energy_j": wake_j,
            "reassignment_active_hashing_energy_j": active_j,
            "residual_predecessor_active_j": r1, "residual_predecessor_idle_or_offline_j": r2,
            "residual_reassignee_standby_j": r3, "residual_reassignment_wake_j": r4,
            "residual_reassignment_active_hashing_j": r5,
            "disposition": getattr(req.disposition, "kind", None)})

    # interval-overlap audit + aggregate-vs-integrated-run-residency bound (per miner, per state).
    overlap = 0
    aggregate_exceeds_run_residency = 0
    for (miner_id, state), spans in charged.items():
        spans_sorted = sorted(spans)
        prev_hi = None
        total = 0.0
        for lo, hi in spans_sorted:
            if prev_hi is not None and lo < prev_hi - TOL:
                overlap += 1
            prev_hi = hi if prev_hi is None else max(prev_hi, hi)
            total += (hi - lo)
        m = run_ctx.miners.get(miner_id)
        if m is None:
            continue                                    # no ledger to bound a synthetic miner against
        final = m.duration.get(state, 0.0)
        if total > final + TOL:
            aggregate_exceeds_run_residency += 1

    max_req_resid = max([0.0] + list(comp_resid.values()))
    return {"per_request": rows, "aggregate": agg,
            "component_residuals_j": comp_resid,
            "request_count": len(rows), "request_count_by_status": counts,
            "max_request_energy_residual_j": max_req_resid,
            "max_energy_residual_j": max_req_resid,      # back-compat alias (S4B name)
            "overlapping_charged_interval_count": overlap,
            "aggregate_exceeds_run_residency_count": aggregate_exceeds_run_residency}


def _range_lease_results(run_ctx: Any, cfg: Stage2Config) -> Dict[str, Any]:
    """S4-13 / S4A-9 result fields: range-lease / reassignment metrics + reassignment energy.

    Reassignment is a liveness/coverage mechanism that may INCREASE energy and latency; these
    fields never claim it saves energy.  S4A-9: the wake / active energy is attributed by the
    reassignment LIFECYCLE INTERVAL (never the reassignee's full residency, which may include its
    own earlier primary work); ``reassignment_energy_residual_j`` reconciles that interval
    attribution against the residency ledger EXACTLY (0.0 J).  The accepted security-floor and
    energy labels are kept unchanged.
    """
    s = run_ctx.lease_stats
    pol = cfg.range_lease
    P = cfg.per_miner_power
    Pw, Ph = P("WAKING"), P("ACTIVE_HASHING")
    # S4A-9: reassignment wake / active energy attributed by LIFECYCLE INTERVAL, per COMPLETED
    # reassignment request, and reconciled EXACTLY against the residency ledger via the snapshots
    # captured at the wake / active-search start.
    wake_j = active_j = 0.0
    max_energy_residual = 0.0
    for req in run_ctx.reassignment_requests.values():
        if req.status != "COMPLETED":
            continue
        # wake interval [started_at, completed_at]: charged at P_wake; reconciled against the
        # ledger's WAKING delta over exactly that interval (snapshots captured at both ends).
        if req.started_at is not None and req.completed_at is not None:
            wake_dur = req.completed_at - req.started_at
            wake_j += Pw * wake_dur
            if req.wake_residency_at_start is not None and req.wake_residency_at_end is not None:
                ledger_wake = req.wake_residency_at_end - req.wake_residency_at_start
                max_energy_residual = max(max_energy_residual, Pw * abs(ledger_wake - wake_dur))
        # reassigned active interval [search_start, search_end]: charged at P_hash; reconciled
        # against the ledger's ACTIVE_HASHING delta over exactly that interval.
        if req.reassigned_search_start_time is not None \
                and req.reassigned_search_end_time is not None:
            act_dur = req.reassigned_search_end_time - req.reassigned_search_start_time
            active_j += Ph * act_dur
            if req.active_residency_at_search_start is not None \
                    and req.active_residency_at_search_end is not None:
                ledger_act = req.active_residency_at_search_end \
                    - req.active_residency_at_search_start
                max_energy_residual = max(max_energy_residual, Ph * abs(ledger_act - act_dur))
    # duplicate-nonce / post-round-evaluation cross-checks over the ledger (S4-8 / S4-2).
    seen = set()
    dup = 0
    post = 0
    for rec in run_ctx.evaluation_ledger:
        tt = run_ctx.round_terminal_times.get(rec.RoundID)
        if tt is not None and rec.completion_time > tt + 1e-9:
            post += 1
        for n in rec.nonces():
            k = (rec.TemplateID, rec.RangeSliceID, n)
            if k in seen:
                dup += 1
            seen.add(k)
    # non-terminal lease / request residue (must be 0 after every round closes).
    from .leases import TERMINAL_LEASE_STATUSES, TERMINAL_REASSIGN_REQUEST_STATUSES
    nonterminal_leases = sum(1 for l in run_ctx.range_leases.values()
                             if l.lease_status not in TERMINAL_LEASE_STATUSES)
    nonterminal_requests = sum(1 for r in run_ctx.reassignment_requests.values()
                               if r.status not in TERMINAL_REASSIGN_REQUEST_STATUSES)
    energy_report = reassignment_energy_report(run_ctx, cfg)
    residual = max(max_energy_residual, energy_report["max_energy_residual_j"])
    s["max_reassignment_energy_residual"] = residual
    return {
        "range_lease_enabled": pol.enabled,
        "lease_duration": pol.lease_duration,
        "progress_timeout": pol.progress_timeout,
        "reassignment_enabled": pol.reassignment_enabled,
        "no_eligible_miner_policy": pol.no_eligible_miner_policy,
        "leases_created": s["leases_created"],
        "leases_completed": s["leases_completed"],
        "leases_expired": s["leases_expired"],
        "leases_revoked": s["leases_revoked"],
        "leases_cancelled": s["leases_cancelled"],
        "leases_reassigned": s["leases_reassigned"],
        "progress_timeouts": s["progress_timeouts"],
        "miner_cancellations": s["miner_cancellations"],
        "reassignment_decisions": s["reassignment_decisions"],
        "reassignment_requests_seated": s["reassignment_requests_seated"],
        "reassignment_requests_completed": s["reassignment_requests_completed"],
        "reassignment_requests_failed": s["reassignment_requests_failed"],
        # S4C-6: the replay / rejection counters are DIAGNOSTIC (non-protocol) and live outside
        # lease_stats; they are surfaced here for reporting but never mutate protocol state.
        "reassignment_replay_count": run_ctx.lease_diagnostics["reassignment_replay_count"],
        "stale_old_lease_events": s["stale_old_lease_events"],
        "stale_expiry_events": s["stale_expiry_events"],
        "stale_timeout_events": s["stale_timeout_events"],
        "stale_exhaust_events": s["stale_exhaust_events"],
        "lease_observation_count": s["lease_observation_count"],
        "lease_observation_replay_count":
            run_ctx.lease_diagnostics["lease_observation_replay_count"],
        "unknown_trigger_rejections": run_ctx.lease_diagnostics["unknown_trigger_rejections"],
        "pathb_rollback_count": s["pathb_rollback_count"],
        "wake_handles_created": s["wake_handles_created"],
        "wake_start_seat_failures": s["wake_start_seat_failures"],
        "wake_complete_seat_failures": s["wake_complete_seat_failures"],
        "miners_terminalised_with_lease": s["miners_terminalised_with_lease"],
        "wakes_cancelled_with_lease": s["wakes_cancelled_with_lease"],
        "overlapping_slice_count": s["overlapping_slice_count"],
        "uncovered_range_count": s["uncovered_range_count"],
        "uncovered_nonce_count": s["uncovered_nonce_count"],
        "nonterminal_lease_count": nonterminal_leases,
        "nonterminal_reassignment_request_count": nonterminal_requests,
        "total_reassignment_latency": s["total_reassignment_latency"],
        "maximum_reassignment_latency": s["maximum_reassignment_latency"],
        "reassignment_wake_energy_kwh": energy_report["aggregate"]["reassignment_wake_energy_j"]
        / 3_600_000.0,
        "reassignment_active_energy_kwh":
        energy_report["aggregate"]["reassignment_active_hashing_energy_j"] / 3_600_000.0,
        "reassignment_energy_residual_j": residual,
        "reassignment_energy_report": energy_report,
        "duplicate_nonce_count": dup,
        "post_round_evaluation_count": post,
    }


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


# ---------------------------------------------------------------- S5-13 matched attack pair
_MATCHED_PAIR_DELTA_KEYS = (
    "rounds_accepted", "rounds_no_block", "energy_kwh", "evaluation_ledger_entries",
    "coverage_gap_nonce_count", "adversarial_coverage_gap_round_count",
    "adversarial_duplicate_evaluation_count", "solution_withholding_count",
    "withheld_never_released_count", "invalid_action_rejection_count",
    "total_duration_below_floor", "reassignments_completed",
    "incentive_net_total", "naive_identity_reward_total",
    "deduplicated_entity_reward_total",
)


def run_matched_adversarial_pair(config: Optional[Dict[str, Any]] = None,
                                 attack_profile: Optional[Dict[str, Any]] = None,
                                 run_id: Any = "matched") -> Dict[str, Any]:
    """S5-13: run ONE matched pair — identical honest baseline vs the same configuration with
    ``attack_profile`` applied — and report the per-metric DELTA between them.

    Both arms share every non-adversarial parameter, the same miner count, the same nonce
    domain, the same template seed and the SAME fixed SHA-256 target and difficulty; the ONLY
    difference is the declared adversarial/incentive configuration.  That makes the delta
    attributable to the modeled behaviour rather than to a re-parameterised protocol.

    The delta is a MEASUREMENT of one deterministic scenario pair.  It is not a statistical
    result, not an equilibrium analysis and not evidence of incentive compatibility, fairness,
    Sybil resistance, selfish-mining resistance, coalition resistance or any security property.
    It does not execute, and must not be used as, the confirmatory experiment matrix.
    """
    base_cfg = dict(config or {})
    attack = dict(attack_profile or {})
    for forbidden in ("difficulty", "nonce_domain_size", "template_seed"):
        if forbidden in attack:
            raise ValueError(
                f"attack_profile must not change {forbidden!r}: a matched pair differs ONLY in "
                f"the adversarial/incentive configuration, never in the fixed work target, the "
                f"nonce domain or the template seed (S5-13/S5-26)")
    baseline_cfg = stage2config_from_blocksim(base_cfg)
    attacked_cfg = stage2config_from_blocksim({**base_cfg, **attack})
    if (baseline_cfg.difficulty != attacked_cfg.difficulty
            or baseline_cfg.nonce_domain_size != attacked_cfg.nonce_domain_size
            or baseline_cfg.template_seed != attacked_cfg.template_seed
            or baseline_cfg.num_miners != attacked_cfg.num_miners):
        raise ValueError("matched pair arms diverge outside the adversarial/incentive model")
    baseline = results_schema(run_simulation(baseline_cfg, run_id=f"{run_id}-baseline"),
                              baseline_cfg)
    attacked = results_schema(run_simulation(attacked_cfg, run_id=f"{run_id}-attacked"),
                              attacked_cfg)
    delta = {}
    for k in _MATCHED_PAIR_DELTA_KEYS:
        a, b_ = baseline.get(k), attacked.get(k)
        delta[k] = (b_ - a) if isinstance(a, (int, float)) and isinstance(b_, (int, float)) \
            else None
    return {
        "schema_version": RESULT_SCHEMA_VERSION,
        "matched_pair": True,
        "identical_target_and_difficulty": True,
        "difficulty": baseline_cfg.difficulty,
        "nonce_domain_size": baseline_cfg.nonce_domain_size,
        "baseline": baseline,
        "attacked": attacked,
        "delta": delta,
        "interpretation_scope": (
            "One deterministic matched-pair MEASUREMENT of a modeled attack profile.  Not a "
            "statistical result, not an equilibrium analysis, and NOT evidence of incentive "
            "compatibility, fairness, Sybil resistance, selfish-mining resistance, coalition "
            "resistance, common-prefix security, chain-quality security or PoW-equivalent "
            "security.  Not the confirmatory experiment matrix."),
    }
