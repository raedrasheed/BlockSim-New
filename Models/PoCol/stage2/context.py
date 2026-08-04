"""Stage-2 run/round contexts, the driver-request lifecycle, miner records and the
residency/energy ledger.

Realises the frozen Stage-1 ownership contracts (RunContext s.1.0; driver_request
AH4/AI2-AI5; the residency/energy model s.1/s.1a) and the mandatory Stage-1AJ backlog
fixes (immutable requested_event_time, effective seat time, keyed registry updates,
distinct reserve-incident identities, exact RunContext ownership, structured genesis
outcomes).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from .config import Stage2Config, JOULES_PER_KWH
from .events import EventQueue, EventRef, Outcome

# ------------------------------------------------------------------ enumerations
MINER_STATES = ("REGISTERED", "RESERVE", "ACTIVE_HASHING", "EXHAUSTED_PENDING",
                "LOW_POWER_LISTEN", "WAKING", "OFFLINE", "DISQUALIFIED")

DRIVER_REQUEST_STATUSES = ("PENDING", "SEATED", "CONSUMED", "REJECTED", "CANCELLED")

# AI4 legal transition table: the only edges SetDriverRequestStatus permits.
_LEGAL_TRANSITIONS = {
    ("PENDING", "SEATED"), ("PENDING", "REJECTED"), ("PENDING", "CANCELLED"),
    ("SEATED", "CONSUMED"), ("SEATED", "CANCELLED"),
}


# DriverRoundScope helpers (AI5).
def EXACT_ROUND(round_id: Any) -> Tuple[str, Any]:
    return ("EXACT_ROUND", round_id)


NEXT_AVAILABLE_ROUND = ("NEXT_AVAILABLE_ROUND",)
RUN_LEVEL = ("RUN_LEVEL",)


# ------------------------------------------------------------------ records
@dataclass
class BootstrapRequest:
    BootstrapRequestID: Any
    predecessor_round_id: Any
    predecessor_terminal_time: Optional[float]
    target_time: float


@dataclass
class DriverRequest:
    DriverRequestID: Any
    logical_request_id: Any
    kind: str
    driver_admission_time: float               # AI2 authoritative (not a copy of target)
    requested_event_time: float                # AI5/backlog-5 IMMUTABLE original request
    effective_event_time: float                # backlog-4 legal effective seat time
    round_scope: Any
    payload: Dict[str, Any]
    status: str = "PENDING"
    seated_event_ref: Optional[EventRef] = None
    disposition: Any = None
    consumed_result: Any = None


@dataclass
class MinerRecord:
    MinerID: Any
    state: str
    registered_at: float
    state_since: float
    duration: Dict[str, float] = field(default_factory=lambda: {s: 0.0 for s in MINER_STATES})
    adversarial: bool = False


@dataclass
class EvaluationRecord:
    """S2B-4: one executable record of a COMMITTED contiguous nonce-evaluation interval.

    Each committed hash-work event appends exactly one record for the interval
    ``[interval_start, interval_end)`` it evaluated, at its ``completion_time``.  The
    ledger is the authority for the scientific ledger tests (zero duplicates, in-range,
    no post-round evaluation, searched_count == ledger count).
    """
    RoundID: Any
    TemplateID: Any
    MinerID: Any
    AssignmentID: Any
    assignment_version: int
    interval_start: int
    interval_end: int                 # exclusive
    completion_time: float
    contained_solution: bool
    winning_nonce: Optional[int]
    event_ref: Any
    assignment_kind: str = "PRIMARY_ASSIGNMENT"   # S3-7/S4-3: PRIMARY/ACTIVATED_RESERVE/REASSIGNED_*
    # S4-3: the range slice + lease provenance for the committed interval.
    RangeSliceID: Any = None
    LeaseID: Any = None
    lease_generation: int = 0
    progress_generation: int = 0
    predecessor_lease_id: Any = None

    def count(self) -> int:
        return self.interval_end - self.interval_start

    def nonces(self):
        return range(self.interval_start, self.interval_end)


# ------------------------------------------------------------------ RoundContext
@dataclass
class RoundContext:
    RoundID: Any
    run_context: "RunContext"
    round_state: str = "ROUND_INITIALISING"
    state_version: int = 0
    TemplateID_committed: Optional[Any] = None
    round_terminal_time: Optional[float] = None
    terminal_disposition: Optional[str] = None
    reserve_activation_seq: int = 0
    acceptance_seq: int = 0
    block_accepted: bool = False
    # AH5 initial-registration barrier
    barrier_expected: set = field(default_factory=set)
    barrier_registered: set = field(default_factory=set)
    barrier_satisfied: bool = True
    # participants (assignments) of this round
    assignments: Dict[Any, Dict[str, Any]] = field(default_factory=dict)
    participant_setup_seated: bool = False
    # Stage-3 per-round security-floor breach tracking (S3-4/S3-13/S3A-2).
    below_floor_since: Optional[float] = None
    below_floor_open_reason: Optional[str] = None
    current_breach_id: Any = None

    def transition(self, new_state: str) -> None:
        self.round_state = new_state
        self.state_version += 1


# ------------------------------------------------------------------ RunContext
class RunContext:
    """The SOLE owner of per-run runtime state (Q5)."""

    def __init__(self, run_id: Any, config: Stage2Config):
        self.RunID = run_id
        self.config = config
        self.event_queue = EventQueue(config.horizon_T)
        self.event_queue.owner_run_context = self   # exact-ownership check (S2A-4/backlog-11)
        self.last_finalised_event_time: Optional[float] = None   # AI2 frontier
        self.run_horizon_T = config.horizon_T
        self.run_finalised = False
        self.run_end_time: Optional[float] = None
        self.run_disposition: Optional[str] = None
        # rounds
        self.current_round_context: Optional[RoundContext] = None
        self.prior_round_terminal_state: Optional[Dict[str, Any]] = None
        self.round_seq: int = 0
        # driver-event seating idempotence
        self.driver_event_seat: Dict[Any, EventRef] = {}
        self.next_round_setup_seq: int = 0
        # bootstrap
        self.bootstrap_request_registry: Dict[Any, BootstrapRequest] = {}
        self.current_bootstrap_request: Optional[BootstrapRequest] = None
        # driver requests (AH4/AI2-AI5)
        self.driver_request_registry: Dict[Any, DriverRequest] = {}
        self.driver_request_seq: int = 0
        self.pending_driver_request_index: set = set()
        self.driver_request_by_logical_id: Dict[Any, Any] = {}      # AI3
        self.driver_request_by_seat_event_ref: Dict[EventRef, Any] = {}  # AI4
        # genesis
        self.genesis_miner_registry: List[Dict[str, Any]] = []
        # AI6 terminal-publication propagation
        self.terminal_publication_result: Any = None
        self.next_round_bootstrap_status: str = "OK"
        # population + energy
        self.miners: Dict[Any, MinerRecord] = {}
        # S2B-4 executable evaluation ledger + per-round scientific provenance.
        self.evaluation_ledger: List[EvaluationRecord] = []
        self.round_participants: Dict[Any, set] = {}
        self.round_ranges: Dict[Any, Dict[Any, Tuple[int, int]]] = {}
        self.round_terminal_times: Dict[Any, float] = {}
        self.final_searched: Dict[Any, int] = {}   # (RoundID, MinerID) -> final searched_count
        self.round_first_completion: Dict[Any, float] = {}  # (RoundID, MinerID) -> first batch completion time
        self.max_search_time_residual: float = 0.0   # S2B-2: max |searched_count - rate*elapsed|
        self.search_assignment_kind: Dict[Any, str] = {}  # (RoundID, MinerID) -> PRIMARY/RESERVE kind
        # Stage-3 security-floor + reserve-activation state.
        self.security_observations: List[Any] = []
        self.activation_decisions: List[Any] = []
        self.activation_requests: Dict[Any, Any] = {}   # ReserveActivationRequestID -> request (replay)
        self.reserve_records: Dict[Any, Any] = {}       # (RoundID, MinerID) -> ReserveMinerRecord
        self.reserve_slices: Dict[Any, List[Any]] = {}  # RoundID -> [RangeSlice]
        self.reserve_slice_by_id: Dict[str, Any] = {}   # RangeSliceID -> RangeSlice
        self.activations_per_round: Dict[Any, int] = {}  # RoundID -> activations seated
        self.observation_seq: int = 0
        self.decision_seq: int = 0
        # S3A-1/S3A-2: a capacity-state version that bumps on every miner state transition
        # (the only thing that changes H_effective's composition), used in the immutable
        # SecurityFloorObservationKey so a replay at unchanged capacity is idempotent.
        self.capacity_state_version: int = 0
        # S3A-2: observation replay registry keyed by the immutable SecurityFloorObservationKey.
        self.observation_by_key: Dict[Any, Any] = {}
        self.security_stats: Dict[str, Any] = {
            "observation_count": 0, "breach_observation_count": 0, "distinct_breach_count": 0,
            "decision_count": 0, "activations_seated": 0, "activations_completed": 0,
            "activations_cancelled": 0, "floor_unattainable_count": 0,
            "total_duration_below_floor": 0.0, "max_hash_rate_deficit": 0.0,
            "activated_reserve_evaluation_count": 0,
            # S3A-2/S3A-4/S3A-7 correction metrics.
            "observation_replay_count": 0,
            "early_wake_below_floor_duration": 0.0,
            "activation_seat_rollback_count": 0,
            "activation_complete_seat_failure_count": 0,
            "partial_restoration_count": 0,
            "full_domain_exhausted_count": 0,
            "unused_reserve_domain_count": 0,
        }
        # Stage-4 range-lease + reassignment state.
        self.range_leases: Dict[Any, Any] = {}          # LeaseID -> RangeLease
        self.range_progress: Dict[str, Any] = {}        # RangeSliceID -> RangeProgress
        self.slice_of_miner: Dict[Any, str] = {}        # (RoundID, MinerID) -> RangeSliceID
        self.reassignment_decisions: List[Any] = []
        self.reassignment_requests: Dict[Any, Any] = {}  # RangeReassignmentRequestID -> request
        self.reassignments_per_slice: Dict[str, int] = {}  # RangeSliceID -> count
        self.lease_generation_of_slice: Dict[str, int] = {}  # RangeSliceID -> latest generation
        self.reassign_by_suffix_slice: Dict[str, Any] = {}   # suffix RangeSliceID -> (req_id, slice_id)
        # S4A-8: natural reassignment-replay registry keyed on the (terminal) predecessor lease +
        # frontier, so re-observing the SAME terminal lease returns the existing request with no
        # manual generation rewind.
        self.reassignment_by_predecessor: Dict[Any, Any] = {}
        # S4B-4: reassignment wake handles (Stage-3 REASSIGNMENT_WAKE_ONLY scope) — NON-domain
        # lifecycle tokens with NO nonce interval; NEVER a nonce-domain partition member.  The
        # ORIGINAL RangeProgress (OriginalRangeSliceID) remains the sole interval authority.
        self.reassignment_wake_handles: Dict[str, Any] = {}
        # S4B-2: the idempotent replay registry stores the FULL stored result per observation key
        # (observation, decision-or-null, outcome-or-disposition) so an exact replay can return it.
        self.lease_observation_by_key: Dict[Any, Any] = {}
        self.lease_seq: int = 0
        self.reassignment_decision_seq: int = 0
        self.reassignment_retry_seq: Dict[str, int] = {}
        # S4A-4: the ONE authoritative, auditable list of range-lease observations, plus its
        # immutable-key replay registry and monotone sequence.
        self.lease_observations: List[Any] = []
        self.lease_observation_record_by_key: Dict[Any, Any] = {}
        self.lease_observation_seq: int = 0
        self.lease_stats: Dict[str, Any] = {
            "leases_created": 0, "leases_completed": 0, "leases_expired": 0,
            "leases_revoked": 0, "leases_reassigned": 0, "reassignment_decisions": 0,
            "reassignment_requests_seated": 0, "reassignment_requests_completed": 0,
            "reassignment_requests_failed": 0, "reassignment_seat_rollback_count": 0,
            "stale_old_lease_events": 0,
            "uncovered_range_count": 0, "uncovered_nonce_count": 0,
            "total_reassignment_latency": 0.0, "maximum_reassignment_latency": 0.0,
            "reassignment_wake_energy_j": 0.0, "reassignment_active_energy_j": 0.0,
            "max_progress_frontier_residual": 0, "max_reassignment_latency_residual": 0.0,
            # S4A-1/S4A-2/S4A-3 executable-disposition counters.
            "leases_cancelled": 0, "progress_timeouts": 0, "miner_cancellations": 0,
            # S4A-1/S4A-2/S4A-5 stale, no-effect executable dispositions.
            "stale_expiry_events": 0, "stale_timeout_events": 0, "stale_exhaust_events": 0,
            # S4A-7/S4A-6/S4A-8/S4A-9 transactional-integrity counters.
            "pathb_rollback_count": 0, "overlapping_slice_count": 0, "orphan_count": 0,
            "lease_observation_count": 0,
            "max_reassignment_energy_residual": 0.0,
            # S4B executable-blocker counters.
            "wake_start_seat_failures": 0,
            "wake_complete_seat_failures": 0, "miners_terminalised_with_lease": 0,
            "wakes_cancelled_with_lease": 0, "wake_handles_created": 0,
        }
        # S4C-6: DIAGNOSTIC counters that live OUTSIDE the protocol-state ledger.  They record how
        # many exact replays / unknown-trigger rejections were observed, but the state-pure
        # acceptance paths that produce them mutate NO protocol state (lease_stats, leases,
        # progress, miner state, decisions, observations, queue, sequences) — so these are excluded
        # from the deterministic result metrics and from the S4C-9 protocol-state snapshot.
        self.lease_diagnostics: Dict[str, int] = {
            "reassignment_replay_count": 0, "lease_observation_replay_count": 0,
            "unknown_trigger_rejections": 0,
        }
        # ------------------------------------------------ Stage-5 adversarial + incentive model
        # ALL empty / inert when the Stage-5 model is disabled (the default), so the accepted
        # Stage-4C baseline is behaviourally unchanged (S5-01).
        from .adversarial import default_adversarial_stats, default_q_adv_state
        self.adversarial_entities: Dict[Any, Any] = {}       # EntityID -> AdversarialEntity
        self.entity_of_miner: Dict[Any, Any] = {}            # MinerID -> EntityID
        self.behaviour_profiles: Dict[Any, Any] = {}         # (RoundID, MinerID) -> profile
        self.progress_claims: List[Any] = []
        self.progress_claim_by_id: Dict[Any, Any] = {}
        self.withheld_solutions: Dict[Any, Any] = {}         # id -> WithheldSolutionRecord
        self.invalid_actions: Dict[Any, Any] = {}            # id -> InvalidActionRecord
        self.delayed_wake_actions: Dict[Any, Any] = {}       # id -> DelayedWakeAction
        self.adversarial_actions: Dict[Any, Any] = {}        # AdversarialActionID -> record
        self.incentive_ledger: List[Any] = []
        self.incentive_ledger_by_key: Dict[Any, Any] = {}    # dedup key -> entry (idempotent)
        self.incentive_entry_seq: int = 0
        # S5-3 ground-truth layers kept SEPARATE from the accepted lease/progress layer.
        self.adv_actual_frontier: Dict[str, int] = {}        # slice_id -> actual evaluated frontier
        self.adv_reeval_boundary: Dict[str, int] = {}        # slice_id -> actual frontier at revoke
        self.adv_credited_frontier: Dict[str, int] = {}      # slice_id -> work-reward credited end
        self.adv_round_coverage_gap: Dict[Any, int] = {}     # RoundID -> accepted-false-claim gap
        # S5B-7: rounds whose coverage gap came from an EXECUTED abandonment.
        self.adv_abandonment_gap_rounds: set = set()
        self.adv_gap_rounds_counted: set = set()             # RoundIDs already counted as gapped
        # ---------------------------------------------- Stage-5A executable corrections
        # S5A-1: the ACCEPTED frontier layer, kept strictly SEPARATE from the accepted Stage-4C
        # authoritative physical RangeProgress.committed_frontier (which never rewinds).
        self.accepted_frontier_records: List[Any] = []
        self.accepted_frontier_by_id: Dict[Any, Any] = {}
        self.adv_reeval_window: Dict[Any, Dict[str, Any]] = {}  # slice_id -> open re-eval window
        self.adv_physical_applied: set = set()               # (RoundID, mid) physical effects done
        # S5A-3 reported-rate allocation bookkeeping.
        self.adv_allocated_range_size: Dict[Any, int] = {}
        self.adv_allocation_projection: Dict[Any, Dict[str, Any]] = {}
        # S5A-4 executable subassignments + declared virtual identities.
        self.subassignments: List[Any] = []
        self.subassignment_by_id: Dict[Any, Any] = {}
        # S5B-6: (RoundID, ParentAssignmentID) -> ordered SubAssignmentRecords.  The
        # virtual-subassignment accounting authority maps every physical evaluation through
        # this index, so a split assignment's accounting DERIVES from the records.
        self.subassignments_by_parent: Dict[Any, List[Any]] = {}
        self.virtual_identities: List[Any] = []
        self.virtual_identity_by_id: Dict[Any, Any] = {}
        # S5A-5 EXECUTED abandonment actions (an abandonment penalty requires one of these).
        self.abandonment_actions: List[Any] = []
        self.abandonment_by_id: Dict[Any, Any] = {}
        # S5A-6 real security-floor breach intervals + per-(round, miner) wake generation.
        self.adv_floor_breach_intervals: List[Any] = []
        self.adv_wake_generation: Dict[Any, int] = {}
        # S5B-4: (round, template, miner, real wake-request identity) -> DelayedWakeAction id.  An
        # exact replay of the same wake request resolves here and creates NO second action.
        self.adv_wake_action_by_request: Dict[Any, Any] = {}
        # S5A-7 declared per-round adversarial action budget.
        self.adv_actions_this_round: Dict[Any, int] = {}
        # S5B-2: per-round incentive results.  Aggregates are RECOMPUTED from these plus the
        # immutable ledger, so repeating finalisation is byte-for-byte state-pure.
        self.round_incentive_result: Dict[Any, Dict[str, Any]] = {}
        # S5B-5: replay-safe action-budget accounting — an action identity already charged is
        # never charged twice.
        self.adv_action_budget_charged: set = set()
        # S5C-3: identities already REFUSED over the limit, so the rejection diagnostic counts one
        # refusal per immutable identity rather than one per re-offer.
        self.adv_action_rejected: set = set()
        # S5C-3: false-exhaustion action identity -> its stored result.  An exact replay returns
        # this and mutates nothing, for BOTH the detected and the accepted disposition.
        self.false_exhaustion_results: Dict[Any, Any] = {}
        self.availability_snapshot: Dict[Any, float] = {}    # (RoundID, mid) -> residency at start
        self.adversarial_stats: Dict[str, Any] = default_adversarial_stats()
        self.q_adv_state: Dict[str, Any] = default_q_adv_state()
        self.acceptance_times: List[float] = []              # accepted-block times (diagnostics)
        # optional capacity-observation hook (set ONLY when the Stage-5 model is enabled).
        self.adversarial_share_hook = None
        # audit log
        self.log: List[Outcome] = []

    # ----------------------------------------------------------- AI2/AI3 admission
    def admit_driver_request(self, kind: str, requested_event_time: float,
                             round_scope: Any, payload: Dict[str, Any]) -> Outcome:
        """The NAMED producer of a driver_request (AH4/AI2/AI3/AI5)."""
        # AI5 structural scope check for a reserve deficit.
        if kind == "ORDINARY_RESERVE_DEFICIT" and round_scope != EXACT_ROUND(
                payload.get("RoundID_at_seat")):
            return Outcome("driver_request_scope_invalid", kind=kind, round_scope=round_scope)
        # AI2 authoritative admission time (never a copy of the requested target).
        driver_admission_time = (self.config.run_start_time
                                 if self.last_finalised_event_time is None
                                 else self.last_finalised_event_time)
        if requested_event_time < driver_admission_time:
            return Outcome("driver_request_time_before_admission_rejected",
                           requested_event_time=requested_event_time,
                           driver_admission_time=driver_admission_time)
        # AI3 stable logical identity BEFORE minting.
        if kind == "MINER_JOIN":
            from .events import join_request_id
            logical_id = ("JOIN_REQUEST", join_request_id(payload["join_request"]))
        elif kind == "ORDINARY_RESERVE_DEFICIT":
            # backlog-10: distinct incidents -> distinct ids; a replay reuses incident_id.
            logical_id = ("RESERVE_ACTIVATION", payload["RoundID_at_seat"],
                          payload["incident_id"])
        else:  # pragma: no cover - defensive
            return Outcome("driver_request_kind_unknown", kind=kind)
        if logical_id in self.driver_request_by_logical_id:
            return Outcome("driver_request_already_admitted",
                           DriverRequestID=self.driver_request_by_logical_id[logical_id])
        # only a genuinely new logical request advances a new sequence.
        self.driver_request_seq += 1
        drid = (self.RunID, self.driver_request_seq)
        dr = DriverRequest(
            DriverRequestID=drid, logical_request_id=logical_id, kind=kind,
            driver_admission_time=driver_admission_time,
            requested_event_time=requested_event_time,          # immutable original
            effective_event_time=requested_event_time,          # default; NEXT_AVAILABLE recomputes
            round_scope=round_scope, payload=dict(payload), status="PENDING",
            disposition=Outcome("driver_request_pending"))
        self.driver_request_registry[drid] = dr
        self.driver_request_by_logical_id[logical_id] = drid
        self.pending_driver_request_index.add(drid)
        return Outcome("driver_request_admitted", DriverRequestID=drid)

    # ----------------------------------------------------------- AI4 guarded mutator
    def set_driver_request_status(self, DriverRequestID: Any, expected_status: str,
                                  new_status: str, disposition: Any) -> Outcome:
        """The SINGLE guarded mutator of driver_request.status (AI4)."""
        dr = self.driver_request_registry.get(DriverRequestID)
        if dr is None:
            return Outcome("driver_request_unknown", DriverRequestID=DriverRequestID)
        if dr.status != expected_status:
            return Outcome("driver_request_status_mismatch", DriverRequestID=DriverRequestID,
                           actual_status=dr.status, expected_status=expected_status)
        if (expected_status, new_status) not in _LEGAL_TRANSITIONS:
            return Outcome("driver_request_illegal_transition",
                           DriverRequestID=DriverRequestID, expected_status=expected_status,
                           new_status=new_status)
        # backlog-7: explicit keyed registry update.
        dr.status = new_status
        dr.disposition = disposition
        if new_status == "CONSUMED" and isinstance(disposition, Outcome) \
                and disposition.kind == "driver_request_consumed":
            dr.consumed_result = disposition.data.get("handler_result")
        self.driver_request_registry[DriverRequestID] = dr
        return Outcome("driver_request_status_set", DriverRequestID=DriverRequestID,
                       new_status=new_status)

    # ----------------------------------------------------------- AI4 completion owner
    def complete_driver_request_on_dispatch(self, seat_event_ref: EventRef,
                                            disposition: Any) -> Outcome:
        """SEATED -> CONSUMED via the immutable reverse binding (AI4)."""
        drid = self.driver_request_by_seat_event_ref.get(seat_event_ref)
        if drid is None:
            return Outcome("driver_request_not_a_seat", seat_event_ref=seat_event_ref)
        return self.set_driver_request_status(drid, expected_status="SEATED",
                                              new_status="CONSUMED", disposition=disposition)

    # ----------------------------------------------------------- residency / energy
    def apply_miner_state_transition(self, MinerID: Any, new_state: str,
                                     at_time: float) -> Outcome:
        """Close the current residency interval and open the new one (H7/I19)."""
        m = self.miners[MinerID]
        elapsed = at_time - m.state_since
        if elapsed < 0:
            return Outcome("residency_backward_time", MinerID=MinerID)
        m.duration[m.state] += elapsed
        old = m.state
        m.state = new_state
        m.state_since = at_time
        # S3A-1/S3A-2: a miner state change is the only thing that alters H_effective's
        # composition — bump the capacity-state version so the next observation gets a fresh
        # SecurityFloorObservationKey (replay of an unchanged capacity stays idempotent).
        self.capacity_state_version += 1
        # S5-11: when the Stage-5 adversarial model is enabled, every capacity-changing
        # miner-state transition triggers one adversarial-share observation (q_adv uses
        # ACTUAL active hash rates, never reported rates).  None when disabled (default).
        if self.adversarial_share_hook is not None:
            self.adversarial_share_hook(at_time)
        return Outcome("miner_state_transition_applied", MinerID=MinerID,
                       old_state=old, new_state=new_state)

    def create_miner(self, MinerID: Any, at_time: float, state: str = "REGISTERED",
                     adversarial: bool = False) -> MinerRecord:
        m = MinerRecord(MinerID=MinerID, state=state, registered_at=at_time,
                        state_since=at_time, adversarial=adversarial)
        self.miners[MinerID] = m
        return m

    def settle_residency_to(self, end_time: float) -> None:
        """Close every open residency interval at ``end_time`` (run-end settle, M4/L5)."""
        for m in self.miners.values():
            elapsed = end_time - m.state_since
            if elapsed > 0:
                m.duration[m.state] += elapsed
                m.state_since = end_time

    def miner_energy_joules(self, MinerID: Any) -> float:
        m = self.miners[MinerID]
        return sum(self.config.per_miner_power(s) * dt for s, dt in m.duration.items())

    def total_energy_kwh(self) -> float:
        joules = sum(self.miner_energy_joules(mid) for mid in self.miners)
        return joules / JOULES_PER_KWH

    def residency_reconciles(self, end_time: float, tol: float = 1e-6) -> bool:
        """I5: every miner's state durations sum to (end_time - registered_at)."""
        for m in self.miners.values():
            total = sum(m.duration.values())
            if abs(total - (end_time - m.registered_at)) > tol:
                return False
        return True
