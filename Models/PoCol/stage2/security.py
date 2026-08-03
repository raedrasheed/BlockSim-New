"""Stage-3 security-floor and reserve-activation policy for PoCol.

This module adds an EXPLICIT, OPERATIONAL active-capacity floor and a reserve-activation
policy ON TOP of the accepted Stage-2B scientific search core (it does not modify that
core).  Its purpose is to prevent the effective active hashing capacity from silently
falling below a declared minimum while a round is still open.

Scope discipline:

* This is an OPERATIONAL capacity floor only.  It does NOT prove chain quality, common
  prefix, Bitcoin/PoW security equivalence, or resistance to any adversarial fraction.
* Reserve activation is DISTINCT from range leasing / reassignment (Stage 4).  A reserve
  miner may search only its own previously UNCLAIMED reserve-domain slice; it never
  reassigns another miner's partially-searched range.
* Reserve activation is a security-capacity policy that may INCREASE energy use; it never
  saves energy.
* The fixed target and difficulty are never changed by this policy.

Only pure data structures and pure helpers live here; the event-seating / mutation logic
(``EvaluateSecurityFloor`` and the activation-event handlers) lives in ``simulator.py`` so
that this module has no dependency on the event core.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# Reserve-record lifecycle (S3-3).
RESERVE_STATUSES = ("AVAILABLE", "ACTIVATION_PENDING", "WAKING", "ACTIVE", "EXHAUSTED",
                    "CANCELLED", "UNUSED_AT_ROUND_CLOSE")

# Reserve-domain slice claim lifecycle (S3-2).
SLICE_STATUSES = ("UNCLAIMED", "CLAIMED", "EXHAUSTED", "UNUSED_AT_ROUND_CLOSE")

# Slice kinds.
PRIMARY_ASSIGNMENT = "PRIMARY_ASSIGNMENT"
ACTIVATED_RESERVE_ASSIGNMENT = "ACTIVATED_RESERVE_ASSIGNMENT"

# ReserveActivationDecision.policy_result values (S3-5).
POLICY_RESULTS = ("NO_ACTIVATION_REQUIRED", "ACTIVATION_SEATED", "PARTIAL_RESTORATION",
                  "FLOOR_UNATTAINABLE", "ROUND_ALREADY_TERMINAL", "NO_ELIGIBLE_RESERVE",
                  "ACTIVATION_LIMIT_REACHED")

# Floor-unattainable policies (S3-9).
FLOOR_UNATTAINABLE_POLICIES = ("CONTINUE_DEGRADED", "ABORT_ROUND")


@dataclass(frozen=True)
class SecurityFloorPolicy:
    """Immutable per-run security-floor configuration (S3-1).

    The floor is disabled by default so the accepted Stage-2B behaviour is unchanged.
    """

    enabled: bool = False
    minimum_active_hash_rate: float = 0.0
    minimum_active_miner_count: Optional[int] = None
    activation_trigger_mode: str = "ON_CAPACITY_CHANGE"
    reserve_selection_policy: str = "PRIORITY_THEN_MINERID"
    maximum_activations_per_round: int = 1_000_000
    activation_wake_latency: float = 1.0
    floor_tolerance: float = 0.0


@dataclass
class RangeSlice:
    """An immutable nonce-domain slice (S3-2)."""

    RangeSliceID: str
    kind: str                     # PRIMARY_ASSIGNMENT | ACTIVATED_RESERVE_ASSIGNMENT
    range_start: int
    range_end: int                # exclusive
    status: str = "UNCLAIMED"     # UNCLAIMED | CLAIMED | EXHAUSTED | UNUSED_AT_ROUND_CLOSE
    claimed_by: Optional[Any] = None

    def size(self) -> int:
        return self.range_end - self.range_start


@dataclass
class ReserveMinerRecord:
    """Per-round reserve-miner record and lifecycle (S3-3)."""

    MinerID: Any
    RoundID: Any
    TemplateID: Any
    hash_rate: float
    reserve_status: str = "AVAILABLE"
    activation_priority: int = 0
    assigned_reserve_slice_id: Optional[str] = None
    activation_request_id: Optional[Any] = None
    activation_event_ref: Optional[Any] = None
    activation_generation: int = 0
    disposition: Any = None


@dataclass
class SecurityFloorObservation:
    """One authoritative security-floor observation (S3-4)."""

    ObservationID: Any
    RoundID: Any
    TemplateID: Any
    observation_time: float
    observation_reason: str
    effective_active_hash_rate: float
    active_miner_count: int
    minimum_required_hash_rate: float
    minimum_required_miner_count: Optional[int]
    hash_rate_deficit: float
    miner_count_deficit: int
    breached: bool
    activation_decision_id: Optional[Any] = None


@dataclass
class ReserveActivationDecision:
    """One reserve-activation decision (S3-5)."""

    DecisionID: Any
    ObservationID: Any
    selected_miners: List[Any]
    selected_slices: List[str]
    projected_hash_rate_after_wake: float
    residual_deficit: float
    policy_result: str


@dataclass
class ReserveActivationRequest:
    """Immutable reserve-activation request identity for replay (S3-3)."""

    ReserveActivationRequestID: Any
    RoundID: Any
    TemplateID: Any
    SecurityFloorBreachID: Any
    MinerID: Any
    ReserveSliceID: str
    activation_generation: int
    start_event_ref: Any = None
    disposition: Any = None


# ------------------------------------------------------------------ pure helpers
def compute_h_effective(run_ctx: Any, rc: Any) -> Tuple[float, int, List[Any]]:
    """The effective active hash rate at the current time (S3-1).

    Sums ``hash_rate`` over miners that SIMULTANEOUSLY: are ACTIVE_HASHING, have a live
    current-round/template/version assignment whose range is not exhausted, and are not
    cancelled/stale/reserve-only/WAKING.  Reserve miners that are AVAILABLE,
    ACTIVATION_PENDING or WAKING contribute nothing (they have no live search state).
    """
    h = 0.0
    ids: List[Any] = []
    for mid, st in getattr(rc, "search_states", {}).items():
        if st.completed:
            continue
        if st.cursor >= st.range_end:                      # range exhausted
            continue
        if st.assignment_version != _current_assignment_version(rc, st):
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":       # WAKING/RESERVE/idle excluded
            continue
        h += st.hash_rate
        ids.append(mid)
    return h, len(ids), ids


def _current_assignment_version(rc: Any, st: Any) -> int:
    a = rc.assignments.get(st.AssignmentID)
    return a["assignment_version"] if a is not None else st.assignment_version


def partition_primary_and_reserve(D: int, primary_ids: List[Any], reserve_ids: List[Any],
                                  RoundID: Any) -> Tuple[Dict[Any, Tuple[int, int]],
                                                         List[RangeSlice]]:
    """Deterministic disjoint partition of ``[0, D)`` into PRIMARY ranges + RESERVE slices.

    Primary ranges are assigned to the sorted primary miners; the remaining contiguous
    slices are UNCLAIMED reserve-domain slices (one per reserve miner).  The union is
    exactly ``[0, D)`` and every segment is pairwise disjoint (S3-2).
    """
    p_ids = sorted(primary_ids, key=str)
    r_ids = sorted(reserve_ids, key=str)
    n = len(p_ids) + len(r_ids)
    if n == 0:
        return {}, []
    base = D // n
    rem = D % n
    sizes = [base + (1 if i < rem else 0) for i in range(n)]
    primary_ranges: Dict[Any, Tuple[int, int]] = {}
    reserve_slices: List[RangeSlice] = []
    start = 0
    idx = 0
    for mid in p_ids:
        end = start + sizes[idx]
        primary_ranges[mid] = (start, end)
        start = end
        idx += 1
    for j, _rid in enumerate(r_ids):
        end = start + sizes[idx]
        reserve_slices.append(RangeSlice(RangeSliceID=f"RS-{RoundID}-{j}",
                                         kind=ACTIVATED_RESERVE_ASSIGNMENT,
                                         range_start=start, range_end=end))
        start = end
        idx += 1
    assert start == D
    return primary_ranges, reserve_slices


def select_reserves_to_cover(eligible: List[ReserveMinerRecord], need: float,
                             remaining_activations: int) -> List[ReserveMinerRecord]:
    """Deterministically select the MINIMUM sufficient reserve subset (S3-5).

    ``eligible`` must already be ordered by ``(activation_priority, MinerID)``.  Greedily
    take reserves until their cumulative hash rate covers ``need`` (or the pool / the
    per-round activation limit is exhausted).  Returns the selected records (possibly all
    eligible, if the pool cannot cover ``need``).
    """
    selected: List[ReserveMinerRecord] = []
    acc = 0.0
    for rr in eligible:
        if len(selected) >= remaining_activations:
            break
        if acc >= need:
            break
        selected.append(rr)
        acc += rr.hash_rate
    return selected
