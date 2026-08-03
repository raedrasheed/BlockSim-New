"""Stage-4 nonce-range leases and deterministic reassignment for PoCol.

This module adds EXPLICIT nonce-range leases and deterministic reassignment of the
UNFINISHED SUFFIX of an already-claimed range ON TOP of the accepted Stage-2B search core
and the accepted Stage-3 security-floor / reserve-activation layer (it modifies neither).

Scope discipline:

* Range reassignment transfers ONLY the unfinished suffix ``[committed_frontier, range_end)``
  of an already-claimed primary or reserve slice AFTER that slice's current lease becomes
  terminal.  It is DISTINCT from Stage-3 reserve activation (which claims a previously
  UNCLAIMED reserve-domain slice).
* Reassignment is a LIVENESS / COVERAGE mechanism; it may INCREASE energy and latency and
  NEVER saves energy.  The energy-saving mechanism remains the idle policy within PoCol;
  nonce partitioning alone is never an energy-saving mechanism.
* The fixed target and difficulty are never changed by any lease/reassignment trigger.

Only pure data structures and pure helpers live here; the event-seating / mutation logic
(``EvaluateRangeLease`` and the reassignment transactions/handlers) lives in ``simulator.py``
so that this module has no dependency on the event core.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

# ---------------------------------------------------------------- lifecycles (S4-1)
LEASE_STATUSES = ("PENDING", "ACTIVE", "COMPLETED", "EXPIRED", "REVOKED", "REASSIGNED",
                  "CANCELLED", "STALE_NO_EFFECT")
TERMINAL_LEASE_STATUSES = ("COMPLETED", "EXPIRED", "REVOKED", "REASSIGNED", "CANCELLED",
                           "STALE_NO_EFFECT")

# Reassignment-request lifecycle.
REASSIGN_REQUEST_STATUSES = ("SEATED", "STARTED", "COMPLETED", "CANCELLED", "FAILED",
                             "STALE_NO_EFFECT")
TERMINAL_REASSIGN_REQUEST_STATUSES = ("COMPLETED", "CANCELLED", "FAILED", "STALE_NO_EFFECT")

# Assignment kinds (S4-3): primary / reserve, and their reassigned continuations.
PRIMARY_ASSIGNMENT = "PRIMARY_ASSIGNMENT"
ACTIVATED_RESERVE_ASSIGNMENT = "ACTIVATED_RESERVE_ASSIGNMENT"
REASSIGNED_PRIMARY_WORK = "REASSIGNED_PRIMARY_WORK"
REASSIGNED_RESERVE_WORK = "REASSIGNED_RESERVE_WORK"

# RangeProgress + slice terminal states.
PROGRESS_TERMINAL_STATES = ("OPEN", "COMPLETED", "UNASSIGNED_AT_ROUND_CLOSE",
                            "UNASSIGNED_PENDING_RETRY")

# EvaluateRangeLease decisions (S4-5).
LEASE_DECISIONS = ("LEASE_REMAINS_ACTIVE", "LEASE_COMPLETED", "LEASE_EXPIRED",
                   "LEASE_REVOKED", "REASSIGNMENT_REQUIRED", "REASSIGNMENT_NOT_ALLOWED",
                   "ROUND_ALREADY_TERMINAL")

# RangeReassignmentDecision.policy_result values (S4-7).
REASSIGN_POLICY_RESULTS = ("NO_REASSIGNMENT_REQUIRED", "REASSIGNMENT_SEATED",
                           "REASSIGNMENT_PENDING_WAKE", "NO_ELIGIBLE_MINER",
                           "REASSIGNMENT_LIMIT_REACHED", "ROUND_ALREADY_TERMINAL",
                           "SLICE_ALREADY_COMPLETED")

# Lease expiry / revocation triggers (S4-4).
LEASE_TRIGGERS = ("LEASE_TIME_EXPIRED", "MINER_FAILED", "MINER_CANCELLED",
                  "PROGRESS_TIMEOUT", "ROUND_CLOSING")

# No-eligible-miner policies (S4-11).
NO_ELIGIBLE_MINER_POLICIES = ("CONTINUE_WITH_UNASSIGNED_RANGE", "ABORT_ROUND",
                              "WAIT_FOR_ELIGIBLE_MINER")

# Reassignment selection policies (S4-6).
REASSIGNMENT_SELECTION_POLICIES = ("COMPLETION_TIME_THEN_PRIORITY",)

# Reserve-activation scope (S4A-6): a domain claim vs a wake-only reassignment activation.
RESERVE_ACTIVATION_SCOPES = ("RESERVE_DOMAIN_CLAIM", "REASSIGNMENT_WAKE_ONLY")


@dataclass(frozen=True)
class RangeLeasePolicy:
    """Immutable, VALIDATED per-run range-lease / reassignment configuration (S4-4).

    Disabled by default so the accepted Stage-2B / Stage-3 / Stage-3A behaviour is unchanged.
    """

    enabled: bool = False
    lease_duration: float = 1.0e18            # effectively unbounded unless configured
    progress_timeout: float = 1.0e18
    reassignment_enabled: bool = True
    reassignment_selection_policy: str = "COMPLETION_TIME_THEN_PRIORITY"
    maximum_reassignments_per_slice: int = 1_000_000
    reassignment_wake_latency: float = 1.0
    exhaustion_policy: str = "SEARCH_TO_END"
    lease_tolerance: float = 0.0
    no_eligible_miner_policy: str = "CONTINUE_WITH_UNASSIGNED_RANGE"

    def __post_init__(self) -> None:
        if self.lease_duration < 0:
            raise ValueError("lease_duration must be non-negative")
        if self.progress_timeout < 0:
            raise ValueError("progress_timeout must be non-negative")
        if self.maximum_reassignments_per_slice < 0:
            raise ValueError("maximum_reassignments_per_slice must be non-negative")
        if self.reassignment_wake_latency < 0:
            raise ValueError("reassignment_wake_latency must be non-negative")
        if self.lease_tolerance < 0:
            raise ValueError("lease_tolerance must be non-negative")
        if self.reassignment_selection_policy not in REASSIGNMENT_SELECTION_POLICIES:
            raise ValueError(f"unsupported reassignment_selection_policy: "
                             f"{self.reassignment_selection_policy!r}")
        if self.no_eligible_miner_policy not in NO_ELIGIBLE_MINER_POLICIES:
            raise ValueError(f"unsupported no_eligible_miner_policy: "
                             f"{self.no_eligible_miner_policy!r}")


@dataclass
class RangeLease:
    """An immutable-identity range lease with an explicit lifecycle (S4-1).

    A lease controls ONLY the half-open interval ``[committed_cursor, lease_end_nonce)``;
    a completed or terminal lease never becomes ACTIVE again.
    """

    LeaseID: Any
    RoundID: Any
    TemplateID: Any
    RangeSliceID: str
    lease_generation: int
    AssignmentID: Any
    assignment_version: int
    MinerID: Any
    assignment_kind: str
    lease_start_nonce: int
    lease_end_nonce: int                       # exclusive
    committed_cursor: int
    lease_start_time: float
    lease_expiry_time: float
    lease_status: str = "ACTIVE"
    predecessor_lease_id: Any = None
    reassignment_reason: Any = None
    reserve_activation_request_id: Any = None   # S4-10 link when a reserve wake is required
    # S4A-1: the seated RangeLeaseExpiryEvent ref for this ACTIVE lease (cancelled when the
    # lease terminalises early so no stale deadline fires).
    expiry_event_ref: Any = None
    disposition: Any = None


@dataclass
class RangeProgress:
    """The ONE authoritative progress record per RangeSliceID (S4-2).

    ``committed_frontier`` is monotonic, never decreases, never exceeds ``range_end``, and
    advances ONLY on causally-completed hash work (planning a batch advances nothing).
    """

    RoundID: Any
    TemplateID: Any
    RangeSliceID: str
    range_start: int
    range_end: int                             # exclusive
    committed_frontier: int
    current_lease_id: Any = None
    progress_generation: int = 0
    terminal_status: str = "OPEN"
    assignment_kind: str = PRIMARY_ASSIGNMENT
    # S4A-2: progress-timeout bookkeeping.
    last_progress_time: float = 0.0
    timeout_event_ref: Any = None
    timeout_generation: int = 0
    disposition: Any = None

    def suffix(self) -> Tuple[int, int]:
        """The unfinished suffix ``[committed_frontier, range_end)``."""
        return (self.committed_frontier, self.range_end)

    def uncovered(self) -> int:
        return max(0, self.range_end - self.committed_frontier)


@dataclass
class RangeReassignmentDecision:
    """One deterministic range-reassignment decision (S4-7)."""

    DecisionID: Any
    RoundID: Any
    TemplateID: Any
    RangeSliceID: str
    predecessor_lease_id: Any
    predecessor_committed_frontier: int
    selected_miner_id: Optional[Any]
    new_lease_generation: Optional[int]
    projected_start_time: Optional[float]
    projected_hash_rate: float
    residual_unassigned_work: int
    policy_result: str


@dataclass
class RangeReassignmentRequest:
    """Immutable reassignment-request identity + lifecycle (S4-7)."""

    RangeReassignmentRequestID: Any
    DecisionID: Any
    RoundID: Any
    TemplateID: Any
    RangeSliceID: str
    predecessor_lease_id: Any
    predecessor_committed_frontier: int
    new_MinerID: Any
    new_lease_generation: int
    new_lease_id: Any = None
    needs_stage3_wake: bool = False
    reserve_activation_request_id: Any = None
    status: str = "SEATED"
    start_event_ref: Any = None
    complete_event_ref: Any = None
    seated_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    # S4A-9: exact reassignment-lifecycle interval timestamps + residency snapshots for energy
    # attribution.  The wake/active energy is charged over the LIFECYCLE INTERVAL only (never the
    # reassignee's full residency, which may include its own earlier primary work); the snapshots
    # let the adapter reconcile the interval attribution against the residency ledger EXACTLY.
    reassigned_search_start_time: Optional[float] = None
    reassigned_search_end_time: Optional[float] = None
    wake_residency_at_start: Optional[float] = None
    wake_residency_at_end: Optional[float] = None
    active_residency_at_search_start: Optional[float] = None
    active_residency_at_search_end: Optional[float] = None
    disposition: Any = None


@dataclass
class RangeLeaseObservation:
    """One authoritative, auditable range-lease observation (S4A-4)."""

    ObservationID: Any
    observation_key: Any
    LeaseID: Any
    RoundID: Any
    TemplateID: Any
    observation_time: float
    observation_reason: str
    lease_status_before: str
    committed_frontier: int
    progress_generation: int
    condition_satisfied: bool
    decision_result: str
    reassignment_decision_id: Any = None


@dataclass
class ReassignmentCandidate:
    """A ranked reassignment candidate (S4-6)."""

    MinerID: Any
    category_rank: int                         # lower is preferred
    projected_completion_time: float
    activation_priority: int
    needs_stage3_wake: bool
    hash_rate: float
    reserve_record: Any = None


# ---------------------------------------------------------------- pure identities/helpers
def lease_id(round_id: Any, template_id: Any, slice_id: str, generation: int) -> Tuple:
    """Immutable LeaseID (S4-1): unique per (round, template, slice, generation)."""
    return ("RANGE_LEASE", round_id, template_id, slice_id, generation)


def reassignment_request_id(round_id: Any, template_id: Any, slice_id: str,
                            predecessor_lease_id: Any, committed_frontier: int,
                            new_miner_id: Any, new_lease_generation: int) -> Tuple:
    """Immutable RangeReassignmentRequestID (S4-7)."""
    return ("RANGE_REASSIGNMENT", round_id, template_id, slice_id, predecessor_lease_id,
            committed_frontier, new_miner_id, new_lease_generation)


def select_reassignment_candidate(candidates: List[ReassignmentCandidate]
                                  ) -> Optional[ReassignmentCandidate]:
    """Deterministically pick ONE reassignment miner (S4-6).

    The declared policy ``COMPLETION_TIME_THEN_PRIORITY`` ranks candidates by, in order:

    1. category rank — already-alive miners that finished their own work (rank 0) are
       preferred over activated reserves (rank 1) over available reserves needing a wake
       (rank 2);
    2. lowest projected completion time for the unfinished suffix;
    3. lowest activation priority;
    4. MinerID lexical order.

    Returns ``None`` when no eligible candidate exists.  Never returns more than one miner.
    """
    if not candidates:
        return None
    return min(candidates, key=lambda c: (c.category_rank, c.projected_completion_time,
                                          c.activation_priority, str(c.MinerID)))
