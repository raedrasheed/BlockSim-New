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
