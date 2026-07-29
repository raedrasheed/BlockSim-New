"""Stage 5B1A output schemas: version tag, explicit NA representation, and the
stable per-miner / per-template / coordination field sets, with validators and
reconciliation helpers. Shared by the engine, the storage probe, and the tests.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# schema / component versions (recorded in the code-freeze manifest)
# ---------------------------------------------------------------------------
OUTPUT_SCHEMA_VERSION = "5b1a.1"

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
    "run_id", "miner_id", "hash_rate_hps", "hash_rate_share", "allocation_policy",
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
    "accepted_block_id", "exhausted", "status", "refresh_cause", "start_time_s",
    "end_time_s", "duration_s", "exhausted_time_s", "active_domain_completion_time_s",
    "partial_cutoff_time_s", "legitimate_competitor_count", "obsolete_event_rejection_count",
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
