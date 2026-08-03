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

# Reserve-record lifecycle (S3-3 / S3A-6).  A closed-round record is NEVER left ACTIVE or
# AVAILABLE: an ACTIVE record that did not exhaust its slice terminalises to
# CLOSED_AT_ROUND_CLOSE, an ACTIVE record that exhausted its slice to EXHAUSTED, and an
# AVAILABLE record to UNUSED_AT_ROUND_CLOSE.
RESERVE_STATUSES = ("AVAILABLE", "ACTIVATION_PENDING", "WAKING", "ACTIVE", "EXHAUSTED",
                    "CANCELLED", "UNUSED_AT_ROUND_CLOSE", "CLOSED_AT_ROUND_CLOSE")

# Terminal reserve-record statuses after round closure (S3A-6 / S3A-9).
TERMINAL_RESERVE_STATUSES = ("EXHAUSTED", "CANCELLED", "UNUSED_AT_ROUND_CLOSE",
                             "CLOSED_AT_ROUND_CLOSE")

# Reserve-activation request lifecycle (S3A-6).
REQUEST_STATUSES = ("SEATED", "STARTED", "COMPLETED", "CANCELLED", "FAILED",
                    "STALE_NO_EFFECT")
TERMINAL_REQUEST_STATUSES = ("COMPLETED", "CANCELLED", "FAILED", "STALE_NO_EFFECT")

# Reserve-domain slice claim lifecycle (S3-2).
SLICE_STATUSES = ("UNCLAIMED", "CLAIMED", "EXHAUSTED", "UNUSED_AT_ROUND_CLOSE")

# Slice kinds.
PRIMARY_ASSIGNMENT = "PRIMARY_ASSIGNMENT"
ACTIVATED_RESERVE_ASSIGNMENT = "ACTIVATED_RESERVE_ASSIGNMENT"

# ReserveActivationDecision.policy_result values (S3-5 / S3A-3).
POLICY_RESULTS = ("NO_ACTIVATION_REQUIRED", "ACTIVATION_SEATED", "PARTIAL_RESTORATION",
                  "FLOOR_UNATTAINABLE", "ROUND_ALREADY_TERMINAL", "NO_ELIGIBLE_RESERVE",
                  "ACTIVATION_LIMIT_REACHED")

# Floor-unattainable policies (S3-9).
FLOOR_UNATTAINABLE_POLICIES = ("CONTINUE_DEGRADED", "ABORT_ROUND")

# Validated policy vocabularies (S3A-8): the adapter rejects any name outside these.
ACTIVATION_TRIGGER_MODES = ("ON_CAPACITY_CHANGE",)
RESERVE_SELECTION_POLICIES = ("PRIORITY_THEN_MINERID", "MINIMUM_CARDINALITY")

# No-block round-exhaustion dispositions (S3A-7).
FULL_DOMAIN_EXHAUSTED_NO_BLOCK = "full_domain_exhausted_no_block"
ROUND_CLOSED_WITH_UNUSED_RESERVE_DOMAIN = "round_closed_with_unused_reserve_domain"


@dataclass(frozen=True)
class SecurityFloorPolicy:
    """Immutable, VALIDATED per-run security-floor configuration (S3-1 / S3A-8).

    The floor is disabled by default so the accepted Stage-2B behaviour is unchanged.
    Construction validates the policy vocabulary and rejects negative rates/counts/
    latencies/tolerances, so an invalid BlockSim config never yields a usable policy.
    """

    enabled: bool = False
    minimum_active_hash_rate: float = 0.0
    minimum_active_miner_count: Optional[int] = None
    activation_trigger_mode: str = "ON_CAPACITY_CHANGE"
    reserve_selection_policy: str = "MINIMUM_CARDINALITY"
    maximum_activations_per_round: int = 1_000_000
    activation_wake_latency: float = 1.0
    floor_tolerance: float = 0.0

    def __post_init__(self) -> None:
        if self.minimum_active_hash_rate < 0:
            raise ValueError("minimum_active_hash_rate must be non-negative")
        if self.minimum_active_miner_count is not None and self.minimum_active_miner_count < 0:
            raise ValueError("minimum_active_miner_count must be non-negative or None")
        if self.maximum_activations_per_round < 0:
            raise ValueError("maximum_activations_per_round must be non-negative")
        if self.activation_wake_latency < 0:
            raise ValueError("activation_wake_latency must be non-negative")
        if self.floor_tolerance < 0:
            raise ValueError("floor_tolerance must be non-negative")
        if self.activation_trigger_mode not in ACTIVATION_TRIGGER_MODES:
            raise ValueError(f"unsupported activation_trigger_mode: "
                             f"{self.activation_trigger_mode!r}")
        if self.reserve_selection_policy not in RESERVE_SELECTION_POLICIES:
            raise ValueError(f"unsupported reserve_selection_policy: "
                             f"{self.reserve_selection_policy!r}")


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
    observation_key: Any = None                 # S3A-2 immutable SecurityFloorObservationKey


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
    """Reserve-activation request with immutable identity + a complete lifecycle (S3A-6).

    The identity fields (``ReserveActivationRequestID``, round/template/miner/slice/
    generation, and the originating ``SecurityFloorBreachID`` / ``DecisionID``) are fixed
    at seating and are the authority for the replay guard (S3-10) and the full
    identity verification (S3A-5).  ``status`` advances SEATED -> STARTED -> COMPLETED, or
    to a terminal CANCELLED / FAILED / STALE_NO_EFFECT; it is terminal for every request of
    a closed round (S3A-6 / S3A-9).
    """

    ReserveActivationRequestID: Any
    RoundID: Any
    TemplateID: Any
    SecurityFloorBreachID: Any
    DecisionID: Any
    MinerID: Any
    ReserveSliceID: str
    activation_generation: int
    status: str = "SEATED"
    start_event_ref: Any = None
    complete_event_ref: Any = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    disposition: Any = None


# ------------------------------------------------------------------ pure helpers
_TERMINAL_ROUND_STATES = ("ROUND_ACCEPTED", "ROUND_ABORTED")


def compute_h_effective(run_ctx: Any, rc: Any) -> Tuple[float, int, List[Any]]:
    """The effective active hash rate at the current time (S3-1 / S3A-1).

    A miner contributes ITS hash rate ONLY when ALL of the following hold SIMULTANEOUSLY:

    * the round is nonterminal;
    * ``MinerRecord.state == ACTIVE_HASHING``;
    * a ``MinerSearchState`` exists for it and is not completed;
    * ``rc.assignments`` actually CONTAINS ``st.AssignmentID`` — there is NO fallback that
      treats a missing assignment as current (S3A-1);
    * the assignment's ``MinerID`` equals this miner;
    * the assignment's ``assignment_version`` equals the search state's version;
    * the assignment's ``RoundID`` / ``TemplateID`` match the current round / template;
    * the search cursor lies strictly inside the assigned range.

    WAKING / RESERVE / ACTIVATION_PENDING / idle miners (no live ACTIVE_HASHING assignment)
    contribute nothing.
    """
    if rc is None or getattr(rc, "round_state", None) in _TERMINAL_ROUND_STATES:
        return 0.0, 0, []
    round_id = getattr(rc, "RoundID", None)
    template_id = getattr(rc, "TemplateID_committed", None)
    h = 0.0
    ids: List[Any] = []
    for mid, st in getattr(rc, "search_states", {}).items():
        if st.completed:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":       # WAKING/RESERVE/idle excluded
            continue
        a = rc.assignments.get(st.AssignmentID)
        if a is None:                                      # NO missing-assignment fallback
            continue
        if a.get("MinerID") != mid:
            continue
        if a.get("assignment_version") != st.assignment_version:
            continue
        if a.get("RoundID") != round_id or a.get("TemplateID") != template_id:
            continue
        rng = a.get("range")
        if rng is None:
            continue
        r_start, r_end = rng
        if not (r_start <= st.cursor < r_end):             # cursor inside the assigned range
            continue
        h += st.hash_rate
        ids.append(mid)
    return h, len(ids), ids


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


def _pref_key(rr: Any, idx: int) -> Tuple[Any, Any]:
    """Deterministic preference key ``(activation_priority, MinerID)`` with index fallbacks."""
    return (getattr(rr, "activation_priority", idx), str(getattr(rr, "MinerID", idx)))


def select_reserves_to_cover(eligible: List[ReserveMinerRecord], need: float,
                             remaining_activations: int,
                             need_count: int = 0) -> List[ReserveMinerRecord]:
    """Select the TRUE minimum-cardinality reserve subset that restores the floor (S3A-3).

    Returns the SMALLEST subset whose combined hash rate covers ``need`` and whose size is
    at least ``need_count``, bounded by ``remaining_activations`` (and implicitly by the
    number of eligible reserves).  Minimum cardinality is established FIRST; only then are
    ties broken deterministically by the lexicographically smallest tuple of
    ``activation_priority`` values, then by ``MinerID`` lexical order.

    Counterexample (spec S3A-3 / S3A-04): eligible rates ``[10, 100]`` with ``need == 90``
    selects ONLY the 100-rate reserve (a single miner), never both.

    Returns ``[]`` when nothing is needed.  When the bounded pool cannot cover ``need`` this
    returns the best bounded subset (the ``cap`` highest-rate reserves) so the caller can
    report PARTIAL_RESTORATION / FLOOR_UNATTAINABLE.  The result is sorted by preference.
    """
    cap = min(len(eligible), max(0, remaining_activations))
    if cap <= 0:
        return []
    if need <= 0 and need_count <= 0:
        return []
    rates_desc = sorted((float(getattr(r, "hash_rate", 0.0)) for r in eligible), reverse=True)

    # minimum cardinality k: the fewest reserves (largest-rate first) that reach `need`,
    # never fewer than `need_count`, never more than `cap`.
    k = max(1, int(need_count))
    running = sum(rates_desc[:k])
    while k < cap and (running < need):
        k += 1
        running = sum(rates_desc[:k])
    if k > cap:
        k = cap
    covers = (sum(rates_desc[:k]) >= need) and (k >= need_count)
    if not covers:
        # bounded pool cannot restore the floor: best-effort = the cap highest-rate reserves.
        by_rate = sorted(eligible, key=lambda r: (-float(getattr(r, "hash_rate", 0.0)),
                                                  _pref_key(r, 0)))
        best = by_rate[:cap]
        return sorted(best, key=lambda r: _pref_key(r, eligible.index(r)))

    # among size-k subsets that cover `need`, choose the lexicographically smallest tuple of
    # activation priorities (then MinerID): a feasibility greedy over the preference order.
    pool = sorted(enumerate(eligible), key=lambda ir: _pref_key(ir[1], ir[0]))
    selected: List[Any] = []
    selected_sum = 0.0
    for pos, (_orig_idx, cand) in enumerate(pool):
        if len(selected) == k:
            break
        slots_after = k - len(selected) - 1
        rest_rates = sorted((float(getattr(r, "hash_rate", 0.0)) for _i, r in pool[pos + 1:]),
                            reverse=True)[:slots_after]
        cand_rate = float(getattr(cand, "hash_rate", 0.0))
        if selected_sum + cand_rate + sum(rest_rates) >= need:
            selected.append(cand)
            selected_sum += cand_rate
    if len(selected) < k:                                  # defensive: fall back to top-rate
        chosen = set(id(r) for r in selected)
        for _i, r in sorted(pool, key=lambda ir: -float(getattr(ir[1], "hash_rate", 0.0))):
            if len(selected) == k:
                break
            if id(r) not in chosen:
                selected.append(r)
                chosen.add(id(r))
    return sorted(selected, key=lambda r: _pref_key(r, eligible.index(r)))
