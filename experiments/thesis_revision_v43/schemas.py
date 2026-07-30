"""Stage 5B1A output schemas: version tag, explicit NA representation, and the
stable per-miner / per-template / coordination field sets, with validators and
reconciliation helpers. Shared by the engine, the storage probe, and the tests.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# schema / component versions (recorded in the code-freeze manifest)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA_VERSION = "5b1g.2"

# ---------------------------------------------------------------------------
# explicit machine-readable NA (undefined / not-applicable)
# NA is JSON null; every NA value carries a reason code in a companion *_na_reason
# field. NA is NEVER encoded as 0, inf, or a large constant.
# ---------------------------------------------------------------------------
NA = None
NA_REASONS = {
    "no_accepted_blocks": "run produced zero accepted blocks",
    "no_committed_transactions": "no transactions were committed",
    "no_valid_proposals": "no valid block proposals occurred (empty denominator)",
    "not_applicable_scenario": "concept does not apply to this scenario",
}


def is_na(x) -> bool:
    return x is None


# ---------------------------------------------------------------------------
# per-miner summary schema (Section 6) — preserved for EVERY run
# ---------------------------------------------------------------------------
PER_MINER_FIELDS = (
    "run_id", "miner_id", "hash_rate_hps", "hash_rate_hps_int", "hash_rate_share", "allocation_policy",
    "range_start", "range_end", "range_size", "search_start_position",
    "candidates_evaluated", "searched_count", "last_evaluated_position",
    "unsearched_count", "remaining_unsearched", "inactive_count", "active_time_s",
    "idle_time_s", "offline_time_s", "productive_search_time_s",
    "active_energy_kwh", "idle_energy_kwh", "template_generations_participated",
    "range_exhaustion_count", "idle_entry_count", "final_state", "completion_status",
    "stop_reason", "state_transition_reason_counts",
)

# ---------------------------------------------------------------------------
# per-template-generation summary schema (Section 7) — preserved for EVERY run
# ---------------------------------------------------------------------------
PER_TEMPLATE_FIELDS = (
    "run_id", "round_id", "template_generation_id", "parent_block_id", "template_id",
    "target", "mu", "assigned_domain_size", "searched_domain_size",
    "unsearched_domain_size", "inactive_domain_size", "total_template_solution_count",
    "active_range_solution_count", "inactive_range_solution_count",
    "discoverable_finder_count", "solution_count", "finder_count",
    # actual vs potential stale-race taxonomy (Stage 5B1G, Sections 3,8)
    "total_template_solution_position_count", "active_range_solution_position_count",
    "inactive_range_solution_position_count", "distinct_potential_finder_miner_count",
    "potential_competitor_miner_count", "actual_proposal_miner_count",
    "actual_competitor_miner_count", "actual_stale_producer_miner_count",
    "stale_block_count", "single_height_stale_block_count", "height_has_any_stale",
    "stale_producer_miner_ids", "stale_block_ids", "legitimate_stale_block_count",
    "accepted_block_id", "exhausted", "partial", "completed", "accepted",
    "refresh_required", "status", "refresh_cause", "start_time_s",
    "end_time_s", "duration_s", "exhausted_time_s", "active_domain_completion_time_s",
    "partial_cutoff_time_s",
    # exact B2 exhaustion closure (Stage 5B1G, Section 7)
    "exact_exhaustion_verified", "b2_exhaustion_time_fraction_numerator",
    "b2_exhaustion_time_fraction_denominator", "previous_candidate_event_time_s",
    "coverage_before_exhaustion", "coverage_at_exhaustion",
    "legitimate_competitor_count", "obsolete_event_rejection_count",
)

# ---------------------------------------------------------------------------
# per-miner per-generation schema (Stage 5B1F Section 8; extended Stage 5B1G
# Section 5 with single-height stale-race lifecycle fields)
# ---------------------------------------------------------------------------
PER_MINER_GENERATION_FIELDS = (
    "run_id", "template_generation_id", "miner_id", "template_id",
    "assigned_range_start", "assigned_range_end", "assigned_range_size",
    "search_start_position", "candidates_evaluated_this_generation",
    "cumulative_candidates_evaluated", "last_evaluated_position",
    "unsearched_candidates_this_generation", "inactive_candidates_this_generation",
    "productive_search_time_s", "active_nonproductive_time_s", "idle_time_s",
    "offline_time_s", "earliest_solution_position", "earliest_solution_time_s",
    "earliest_solution_identity",
    # circular path provenance (Stage 5B1G.1 §2)
    "path_wraps_around", "path_end_position", "circular_candidates_evaluated",
    "search_progress_reason", "stop_reason", "completed_range", "generated_block_id",
    "received_winner_time_s", "propagation_delay_s", "delivery_stream_key",
    "potential_old_parent_solution_position", "potential_old_parent_solution_time_s",
    "found_competing_solution_before_receipt", "produced_stale_block", "stale_block_id",
)

# lifecycle stop-reason vocabulary for the per-miner-generation record (Section 5)
GENERATION_STOP_REASONS = (
    "solution_found", "stale_block_generated", "winner_received",
    "no_reachable_solution", "simulation_cutoff", "inactive",
)

# machine-readable delivery-delay + stale-race record schemas (Sections 2,4,12).
# A delivery record exists for EVERY active non-winning miner (Stage 5B1G.1 §3),
# regardless of whether it is a potential competitor, a stale producer, a
# same-identity independent finder, or a miner with no reachable solution.
DELIVERY_DELAY_RECORD_FIELDS = (
    "template_generation_id", "parent_block_id", "winner_miner_id",
    "recipient_miner_id", "propagation_delay_s", "received_winner_time_s",
    "recipient_discovery_time_s", "recipient_earliest_solution_identity",
    "delivery_stream_key", "discovered_before_receipt", "potential_competitor",
    "produced_stale_block", "same_identity_independent_discovery", "stop_reason",
)
STALE_RACE_RECORD_FIELDS = (
    "template_generation_id", "parent_block_id", "accepted_block_id",
    "winner_miner_id", "winner_time_s", "potential_finder_miner_count",
    "potential_competitor_miner_count", "actual_stale_producer_miner_count",
    "actual_proposal_miner_count", "actual_competitor_miner_count",
    "stale_block_count", "single_height_stale_block_count", "height_has_any_stale",
    "active_nonwinner_delivery_count",
    # one entry PER stale producer (no collapsing several producers into one block)
    "stale_producer_miner_ids", "stale_block_ids", "stale_candidate_identities",
    "stale_discovery_times", "stale_race_energy_not_integrated",
)


# ---------------------------------------------------------------------------
# coordination schema (Section 10) — message categories kept separate
# ---------------------------------------------------------------------------
COORD_MESSAGE_CATEGORIES = (
    "block_propagation", "transaction_reconciliation", "template_announcement",
    "nonce_allocation", "registration",
)
# count + bytes per category; bytes null when the message size is not configured
COORD_FIELDS = tuple(f"{c}_message_count" for c in COORD_MESSAGE_CATEGORIES) + \
    tuple(f"{c}_bytes" for c in COORD_MESSAGE_CATEGORIES)

# abstract (unimplemented) protocol activity: counts only, never simulated bytes
ABSTRACT_FIELDS = (
    "abstract_template_agreement_operations",
    "abstract_transaction_reconciliation_operations",
    "unimplemented_agreement_energy_kwh",          # always null
)


def validate_fields(record: dict, fields) -> list:
    """Return the list of missing required fields (empty == valid)."""
    return [f for f in fields if f not in record]


def reconcile_per_miner(per_miner: list, run: dict, abs_tol: float = 1e-9) -> dict:
    """Per-miner -> network reconciliation. Returns a dict of residuals; all must
    be within abs_tol for a pass."""
    sa = sum(m["active_energy_kwh"] for m in per_miner)
    si = sum(m["idle_energy_kwh"] for m in per_miner)
    ta = sum(m["active_time_s"] for m in per_miner)
    ti = sum(m["idle_time_s"] for m in per_miner)
    to = sum(m["offline_time_s"] for m in per_miner)
    return dict(
        active_energy_residual=abs(sa - run["active_energy_kwh"]),
        idle_energy_residual=abs(si - run["idle_energy_kwh"]),
        active_time_residual=abs(ta - run["total_active_time_s"]),
        idle_time_residual=abs(ti - run["total_idle_time_s"]),
        offline_time_residual=abs(to - run["total_offline_time_s"]),
        passed=(abs(sa - run["active_energy_kwh"]) <= abs_tol
                and abs(si - run["idle_energy_kwh"]) <= abs_tol
                and abs(ta - run["total_active_time_s"]) <= abs_tol
                and abs(ti - run["total_idle_time_s"]) <= abs_tol
                and abs(to - run["total_offline_time_s"]) <= abs_tol),
    )


def reconcile_per_template(per_template: list) -> dict:
    """Each template: assigned == searched + unsearched + inactive (exact integers,
    Section 4)."""
    bad = [t["template_generation_id"] for t in per_template
           if t["assigned_domain_size"] != (t["searched_domain_size"]
                                            + t["unsearched_domain_size"]
                                            + t["inactive_domain_size"])]
    return dict(bad_templates=bad, passed=(not bad))


def reconcile_solution_positions(per_template: list, disjoint: bool = False) -> dict:
    """Stage 5B1G Section 6: for every template generation the sampled solution
    POSITIONS split exactly into active + inactive regions (universal). For DISJOINT
    scenarios each active position has a single owner, so the number of potential
    finder MINERS never exceeds the number of active positions (a miner may own
    several positions but counts as a single finder). For COMMON-template scenarios
    (B1/B2) every miner can reach every position, so finders may exceed positions and
    that check does not apply."""
    bad_split, bad_finder = [], []
    for t in per_template:
        if (t["active_range_solution_position_count"]
                + t["inactive_range_solution_position_count"]
                != t["total_template_solution_position_count"]):
            bad_split.append(t["template_generation_id"])
        if disjoint and t["distinct_potential_finder_miner_count"] > t["active_range_solution_position_count"]:
            bad_finder.append(t["template_generation_id"])
    return dict(bad_position_split=bad_split, bad_finder_vs_position=bad_finder,
                passed=(not bad_split and not bad_finder))


def reconcile_stale_diagnostic(run: dict, per_template: list, n_active: int = None) -> dict:
    """Stage 5B1G Sections 2,3,8 (corrected): the single-height stale-race diagnostic
    is internally consistent, with NO global one-stale-per-height cap. Per accepted
    height: stale_block_count == #stale producers == #stale block ids == actual
    competitors, and lies in 0..N_active-1; actual proposals == 1 + stale_block_count;
    a miner never produces two stales at one height (producer ids are unique). Run
    level: per-template stale counts sum to the run count; stale-race energy is flagged
    not-integrated; deprecated aliases equal their single_height_ targets."""
    accepted = [t for t in per_template if t["accepted"]]
    bad_count = [t["template_generation_id"] for t in accepted
                 if not (t["stale_block_count"] == t["actual_stale_producer_miner_count"]
                         == len(t["stale_producer_miner_ids"]) == len(t["stale_block_ids"])
                         == t["actual_competitor_miner_count"])]
    bad_prop = [t["template_generation_id"] for t in accepted
                if t["actual_proposal_miner_count"] != 1 + t["stale_block_count"]]
    dup_producer = [t["template_generation_id"] for t in accepted
                    if len(set(t["stale_producer_miner_ids"])) != len(t["stale_producer_miner_ids"])]
    bad_range = []
    if n_active is not None:
        bad_range = [t["template_generation_id"] for t in accepted
                     if not (0 <= t["stale_block_count"] <= n_active - 1)]
    indicator_ok = all(t["height_has_any_stale"] == (t["stale_block_count"] > 0) for t in accepted)
    noblock_nonzero = [t["template_generation_id"] for t in per_template
                       if not t["accepted"]
                       and (t["actual_proposal_miner_count"] != 0
                            or t["actual_competitor_miner_count"] != 0
                            or t["stale_block_count"] != 0)]
    sum_ok = (sum(t["stale_block_count"] for t in per_template)
              == run["stale_block_count"] == run["single_height_stale_block_count"])
    alias_ok = (run["legitimate_stale_block_count"] == run["single_height_stale_block_count"]
                and run["stales_per_accepted_block"] == run["single_height_stales_per_accepted_block"]
                and run["stale_fraction_of_all_valid_blocks"]
                == run["single_height_stale_fraction_of_valid_proposals"])
    not_integrated = run.get("stale_race_energy_not_integrated") is True
    passed = (not bad_count and not bad_prop and not dup_producer and not bad_range
              and indicator_ok and not noblock_nonzero and sum_ok and alias_ok and not_integrated)
    return dict(bad_count=bad_count, bad_proposal=bad_prop, dup_producer=dup_producer,
                bad_range=bad_range, indicator_ok=indicator_ok, noblock_nonzero=noblock_nonzero,
                sum_ok=sum_ok, alias_ok=alias_ok, not_integrated=not_integrated, passed=passed)
