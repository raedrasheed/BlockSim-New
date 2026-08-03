"""Stage-2 event core: EventRef, the event queue, scheduling origins, ScheduleEvent
and CancelQueuedEvent.

This is the executable realisation of the frozen Stage-1 scheduler contract
(STAGE_01_PROTOCOL_PSEUDOCODE.md s.0.7e): the SOLE enqueue interface derives the
delta_cycle from an EXPLICIT SchedulingOrigin (never ambient state), owns the per-run
monotonic event_creation_seq, enforces the descriptor schema, and keeps the event queue
and the central queued-event registry atomically coherent.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

ORDINARY_EVENT = "ORDINARY_EVENT"


# --------------------------------------------------------------------------- results
class Outcome:
    """A lightweight structured result: ``o.kind`` plus named attributes."""

    __slots__ = ("kind", "data")

    def __init__(self, kind: str, **data: Any):
        self.kind = kind
        self.data = data

    def __getattr__(self, name: str) -> Any:  # attribute access to payload
        try:
            return self.data[name]
        except KeyError as exc:  # pragma: no cover - defensive
            raise AttributeError(name) from exc

    def __repr__(self) -> str:  # pragma: no cover - debugging aid
        return f"Outcome({self.kind!r}, {self.data!r})"

    def __eq__(self, other: object) -> bool:
        return (isinstance(other, Outcome) and other.kind == self.kind
                and other.data == self.data)


# --------------------------------------------------------------------------- microphases
# A total order over the per-event_time microphases (STAGE_01 s.0.7 / s.0.7g).  A lower
# ordinal is processed first at a shared (event_time, delta_cycle).  REGISTRATION and
# TEMPLATE_COMMIT are LATER than ROUND_SETUP, so a genesis MinerRegisterEvent seated by
# RoundInitialiseEvent via the forward rule (target microphase > source) lands in the
# SAME delta_cycle and dispatches at the same non-finalised t0 (AI1).
MICROPHASE_ORDINAL: Dict[str, int] = {
    "TERMINAL_CLOSE": 0,
    "TEMPLATE_REFRESH": 1,
    "ROUND_SETUP": 2,
    "REGISTRATION": 3,
    "TEMPLATE_COMMIT": 4,
    "ASSIGNMENT_SETUP": 5,
    "ASSIGNMENT": 6,
    "RECOVERY_ACTIVATE": 7,
    "ACCEPTANCE_COLLECT": 8,
    "ACCEPTANCE_FINALIZE": 9,
    "CERTIFICATE": 10,
    "WAKE_COMPLETE": 11,
    "HASH_WORK": 12,
    "RANGE_EXHAUST_ADJUDICATE": 13,
    "RESUME": 14,
    "MONITOR": 15,
    # Stage-3 reserve-activation lifecycle (after range-exhaust adjudication).
    "RESERVE_ACTIVATION_START": 16,
    "RESERVE_ACTIVATION_COMPLETE": 17,
    # Stage-4 range-lease / reassignment lifecycle.
    "MINER_FAILURE": 18,
    "RANGE_REASSIGNMENT_START": 19,
    "RANGE_REASSIGNMENT_COMPLETE": 20,
    "RANGE_REASSIGNMENT_RETRY": 21,
    # Stage-4A lease expiry / progress-timeout / cancellation.  These land AFTER HASH_WORK
    # (12) at a shared event_time (S4A-1 documented ordering): work completing exactly AT the
    # deadline commits first, then the deadline fires and observes the advanced frontier;
    # work strictly AFTER the deadline never commits (its event is at a later time and is
    # cancelled by the fired deadline).
    "MINER_CANCELLED": 22,
    "RANGE_LEASE_EXPIRY": 23,
    "RANGE_PROGRESS_TIMEOUT": 24,
}

# Stage-3 activation-event payload identity (S3-6): full round/template/assignment identity.
_ACTIVATION_PAYLOAD_KEYS = (
    "ReserveActivationRequestID", "SecurityFloorObservationID", "ReserveActivationDecisionID",
    "RoundID_at_seat", "TemplateID_at_seat", "MinerID", "ReserveSliceID",
    "activation_generation", "expected_reserve_status", "expected_round_state_version",
)

# Stage-4 reassignment-event payload identity (S4-8): full predecessor/successor identity.
_REASSIGN_PAYLOAD_KEYS = (
    "RangeReassignmentRequestID", "DecisionID", "predecessor_lease_id", "new_lease_id",
    "RoundID_at_seat", "TemplateID_at_seat", "RangeSliceID", "old_MinerID", "new_MinerID",
    "predecessor_committed_frontier", "new_lease_generation", "expected_old_lease_status",
    "expected_new_request_status", "expected_progress_generation",
    "expected_round_state_version",
)

# Stage-4A lease-deadline payload identities.
_LEASE_EXPIRY_PAYLOAD_KEYS = (
    "LeaseID", "RoundID_at_seat", "TemplateID_at_seat", "RangeSliceID", "MinerID",
    "lease_generation", "expected_lease_status", "expected_progress_generation",
    "expected_committed_frontier", "expected_round_state_version",
)
_PROGRESS_TIMEOUT_PAYLOAD_KEYS = (
    "LeaseID", "RoundID_at_seat", "TemplateID_at_seat", "RangeSliceID", "MinerID",
    "lease_generation", "expected_committed_frontier", "expected_progress_generation",
    "timeout_generation", "expected_round_state_version",
)


# --------------------------------------------------------------------------- descriptors
@dataclass(frozen=True)
class EventDescriptor:
    event_type: str
    target_microphase: str
    tie_key_fields: Tuple[str, ...]
    allowed_payload_keys: Tuple[str, ...]
    recv_env: bool = False
    # Stage-4: keys that MAY appear in the payload but are not required (e.g. an optional
    # LeaseID carried only when the range-lease layer is enabled).  Backward-compatible: an
    # empty tuple reproduces the exact prior strict-schema behaviour.
    optional_payload_keys: Tuple[str, ...] = ()


DESCRIPTORS: Dict[str, EventDescriptor] = {
    d.event_type: d for d in [
        EventDescriptor("RoundInitialiseEvent", "ROUND_SETUP", ("round_setup_seq",),
                        ("round_setup_seq",)),
        EventDescriptor("TemplateCommitEvent", "TEMPLATE_COMMIT",
                        ("RoundID_at_seat", "candidate_template_id"),
                        ("RoundID_at_seat", "candidate_template")),
        EventDescriptor("PrepareParticipantsEvent", "ASSIGNMENT_SETUP",
                        ("RoundID_at_seat", "TemplateID_at_seat"),
                        ("RoundID_at_seat", "TemplateID_at_seat"), recv_env=True),
        EventDescriptor("MinerRegisterEvent", "REGISTRATION", ("join_request_id",),
                        ("join_request", "DriverRequestID", "round_scope",
                         "RoundID_at_seat"), recv_env=True),
        EventDescriptor("ReserveActivateEvent", "RECOVERY_ACTIVATE",
                        ("RoundID_at_seat", "activation_seq"),
                        ("RoundID_at_seat", "deficit", "activation_seq",
                         "DriverRequestID", "round_scope"), recv_env=True),
        # S4-3: a range-exhaust event OPTIONALLY carries the current LeaseID + generation.
        EventDescriptor("RangeExhaustEvent", "RANGE_EXHAUST_ADJUDICATE",
                        ("MinerID", "AssignmentID"),
                        ("MinerID", "AssignmentID", "RoundID_at_seat",
                         "TemplateID_at_seat", "assignment_version",
                         "expected_search_generation"), recv_env=True,
                        optional_payload_keys=("LeaseID", "lease_generation")),
        EventDescriptor("WakeCompleteEvent", "WAKE_COMPLETE",
                        ("MinerID", "AssignmentID", "assignment_version"),
                        ("MinerID", "AssignmentID", "assignment_version"), recv_env=True),
        # S2B-3: a hash event carries the complete immutable round/template/assignment
        # identity plus the planned cursor interval and the expected search generation.
        # S4-3: it OPTIONALLY also carries the current LeaseID + lease generation.
        EventDescriptor("HashWorkEvent", "HASH_WORK",
                        ("MinerID", "AssignmentID", "cursor_start"),
                        ("RoundID_at_seat", "TemplateID_at_seat", "AssignmentID",
                         "assignment_version", "MinerID", "cursor_start", "cursor_end",
                         "expected_search_generation"), recv_env=True,
                        optional_payload_keys=("LeaseID", "lease_generation")),
        EventDescriptor("AcceptanceEvent", "ACCEPTANCE_FINALIZE",
                        ("RoundID_at_seat", "acceptance_seq"),
                        ("RoundID_at_seat", "acceptance_seq"), recv_env=True),
        # Stage-3 two-step reserve-activation lifecycle (S3-6).
        EventDescriptor("ReserveActivationStartEvent", "RESERVE_ACTIVATION_START",
                        ("MinerID", "ReserveSliceID"), _ACTIVATION_PAYLOAD_KEYS,
                        recv_env=True),
        EventDescriptor("ReserveActivationCompleteEvent", "RESERVE_ACTIVATION_COMPLETE",
                        ("MinerID", "ReserveSliceID"), _ACTIVATION_PAYLOAD_KEYS,
                        recv_env=True),
        # Stage-4 range-lease / reassignment lifecycle (S4-4/S4-8).
        EventDescriptor("MinerFailureEvent", "MINER_FAILURE", ("MinerID",),
                        ("MinerID", "RoundID_at_seat", "TemplateID_at_seat", "fault_reason"),
                        recv_env=True),
        EventDescriptor("RangeReassignmentStartEvent", "RANGE_REASSIGNMENT_START",
                        ("RangeSliceID", "new_lease_generation"), _REASSIGN_PAYLOAD_KEYS,
                        recv_env=True),
        EventDescriptor("RangeReassignmentCompleteEvent", "RANGE_REASSIGNMENT_COMPLETE",
                        ("RangeSliceID", "new_lease_generation"), _REASSIGN_PAYLOAD_KEYS,
                        recv_env=True),
        EventDescriptor("RangeReassignmentRetryEvent", "RANGE_REASSIGNMENT_RETRY",
                        ("RangeSliceID", "retry_seq"),
                        ("RangeSliceID", "RoundID_at_seat", "TemplateID_at_seat",
                         "predecessor_lease_id", "retry_seq"), recv_env=True),
        # Stage-4A lease-deadline / cancellation events (S4A-1/S4A-2/S4A-3).
        EventDescriptor("MinerCancelledEvent", "MINER_CANCELLED", ("MinerID",),
                        ("MinerID", "RoundID_at_seat", "TemplateID_at_seat",
                         "cancellation_reason"), recv_env=True),
        EventDescriptor("RangeLeaseExpiryEvent", "RANGE_LEASE_EXPIRY",
                        ("RangeSliceID", "lease_generation"), _LEASE_EXPIRY_PAYLOAD_KEYS,
                        recv_env=True),
        EventDescriptor("RangeProgressTimeoutEvent", "RANGE_PROGRESS_TIMEOUT",
                        ("RangeSliceID", "timeout_generation"),
                        _PROGRESS_TIMEOUT_PAYLOAD_KEYS, recv_env=True),
    ]
}


def _tie_key(descriptor: EventDescriptor, payload: Dict[str, Any]) -> Optional[Tuple]:
    """Descriptor-derived stable tie key; ``None`` if a named field is unavailable."""
    vals = []
    for f in descriptor.tie_key_fields:
        if f == "candidate_template_id" and "candidate_template" in payload:
            vals.append(candidate_template_id(payload["candidate_template"]))
        elif f == "join_request_id" and "join_request" in payload:
            vals.append(join_request_id(payload["join_request"]))
        elif f in payload:
            vals.append(payload[f])
        else:
            return None
    return tuple(str(v) for v in vals)


# --------------------------------------------------------------------------- identities
def candidate_template_id(candidate_template: Any) -> str:
    if isinstance(candidate_template, dict):
        return str(candidate_template.get("id", candidate_template))
    return str(candidate_template)


def join_request_id(join_request: Any) -> str:
    if isinstance(join_request, dict):
        return str(join_request["MinerID"])
    return str(join_request)


def next_representable_simulation_time(t: float) -> float:
    """The strictly-later representable time (causal-forward, minimal duration)."""
    return math.nextafter(t, math.inf)


# --------------------------------------------------------------------------- EventRef
@dataclass(frozen=True)
class EventRef:
    envelope_namespace: str
    event_type: str
    event_time: float
    delta_cycle: int
    microphase: str
    seq: int


@dataclass
class QueuedEventRecord:
    event_ref: EventRef
    event_type: str
    dispatch_envelope: Dict[str, Any]
    immutable_payload: Dict[str, Any]
    queue_status: str  # QUEUED | DISPATCHING | CONSUMED | CANCELLED


# --------------------------------------------------------------------------- scheduling origins
@dataclass
class OrdinaryDispatch:
    dispatch_envelope: Dict[str, Any]
    dispatched_event_ref: EventRef


@dataclass
class Driver:
    driver_source_kind: str            # RUN_BOOTSTRAP | MINER_JOIN | ORDINARY_RESERVE_DEFICIT
    driver_request_id: Any
    source_event_time: float           # AI2 authoritative admission time (never a copy of target)
    target_event_time: float
    intended_round_scope: Any
    run_ctx: Any
    eq: Any


@dataclass
class PostEpilogue:
    source_event_time: float
    run_ctx: Any
    eq: Any


@dataclass
class TerminalRotation:
    bootstrap_request_id: Any
    predecessor_terminal_time: float
    target_event_time: float
    run_ctx: Any
    eq: Any


# AI2: fixed driver/rotation kind -> event_type permission predicate.
_DRIVER_KIND_MAY_SEAT = {
    ("RUN_BOOTSTRAP", "RoundInitialiseEvent"),
    ("ROUND_ROTATION_BOOTSTRAP", "RoundInitialiseEvent"),
    ("MINER_JOIN", "MinerRegisterEvent"),
    ("ORDINARY_RESERVE_DEFICIT", "ReserveActivateEvent"),
}


def driver_kind_may_seat(kind: str, event_type: str) -> bool:
    return (kind, event_type) in _DRIVER_KIND_MAY_SEAT


def ordinary_dispatch_origin(eq: "EventQueue") -> "OrdinaryDispatch":
    """Build the ordinary-dispatch origin from the current dispatch frame (s.0.7e).

    Valid ONLY inside an active ordinary dispatch (EQ.current_* set).
    """
    envelope = {"envelope_namespace": ORDINARY_EVENT, "event_time": eq.current_event_time,
                "delta_cycle": eq.current_delta_cycle, "event_seq": eq.current_event_seq,
                "hook_id": None}
    return OrdinaryDispatch(dispatch_envelope=envelope,
                            dispatched_event_ref=eq.current_event_ref)


# --------------------------------------------------------------------------- event queue
class EventQueue:
    """The sole dispatch/scheduling state (STAGE_01 s.0.7e)."""

    def __init__(self, run_horizon_T: float):
        self.owner_run_context: Any = None   # set by the owning RunContext (exact-ownership check)
        self.event_queue: Dict[EventRef, Tuple] = {}   # ref -> total-order key
        self.queued_event_registry: Dict[EventRef, QueuedEventRecord] = {}
        self.current_event_time: Optional[float] = None
        self.current_delta_cycle: Optional[int] = None
        self.current_microphase: Optional[str] = None
        self.current_event_seq: Optional[int] = None
        self.current_event_ref: Optional[EventRef] = None
        self.event_creation_seq: int = 0
        self.finalised_event_times: set = set()
        self.run_horizon_T: float = run_horizon_T

    # -- selection helpers --
    def has_pending_before(self, t: float) -> bool:
        return any(k[0] < t for k in self.event_queue.values())

    def earliest_time(self) -> Optional[float]:
        if not self.event_queue:
            return None
        return min(k[0] for k in self.event_queue.values())

    def pending_at(self, t: float) -> Dict[EventRef, Tuple]:
        return {r: k for r, k in self.event_queue.items() if k[0] == t}

    def smallest_delta_cycle_at(self, t: float) -> Optional[int]:
        cycles = [k[1] for k in self.event_queue.values() if k[0] == t]
        return min(cycles) if cycles else None

    def pop_front_at(self, t: float, dc: int) -> Optional[EventRef]:
        candidates = [(k, r) for r, k in self.event_queue.items()
                      if k[0] == t and k[1] == dc]
        if not candidates:
            return None
        candidates.sort(key=lambda kr: kr[0])
        ref = candidates[0][1]
        del self.event_queue[ref]
        return ref

    def any_pending_or_dispatching_at(self, t: float) -> bool:
        for ref, rec in self.queued_event_registry.items():
            if ref.event_time == t and rec.queue_status in ("QUEUED", "DISPATCHING"):
                return True
        return False


# --------------------------------------------------------------------------- ScheduleEvent
def ScheduleEvent(eq: EventQueue, round_context: Any, event_type: str,
                  target_event_time: float, target_microphase: str,
                  payload: Dict[str, Any], scheduling_origin: Any) -> Outcome:
    """The ONE enqueue interface (STAGE_01 s.0.7e; AH1/AI2/AI8)."""
    # K8/J9: reject finalised, post-horizon.
    if target_event_time in eq.finalised_event_times:
        return Outcome("rejected_finalised_time", event_type=event_type,
                       target_event_time=target_event_time)
    if target_event_time > eq.run_horizon_T:
        return Outcome("post_horizon_event_rejected", event_type=event_type,
                       target_event_time=target_event_time)

    # AH1/AI2/AI8: derive delta_cycle from the EXPLICIT origin's own source frame.
    if isinstance(scheduling_origin, PostEpilogue):
        if not (target_event_time > scheduling_origin.source_event_time):
            return Outcome("rejected_post_epilogue_not_strictly_later")
        dc = 0
    elif isinstance(scheduling_origin, Driver):
        d = scheduling_origin
        # S2A-4/backlog-11: EXACT ownership — the carried EQ must be this EQ and the carried
        # RunContext must be the EQ's OWNER (a foreign RunContext sharing the same EQ is rejected).
        if (d.eq is not eq) or (d.run_ctx is not eq.owner_run_context) \
                or (getattr(d.run_ctx, "event_queue", None) is not eq):
            return Outcome("rejected_driver_context_mismatch", event_type=event_type)
        if not driver_kind_may_seat(d.driver_source_kind, event_type):
            return Outcome("rejected_driver_kind_event_type_mismatch",
                           event_type=event_type, driver_source_kind=d.driver_source_kind)
        if target_event_time != d.target_event_time:
            return Outcome("rejected_driver_target_context_mismatch",
                           event_type=event_type, target_event_time=target_event_time,
                           carried_target_event_time=d.target_event_time)
        if not (target_event_time >= d.source_event_time):
            return Outcome("rejected_driver_target_before_source",
                           event_type=event_type, target_event_time=target_event_time,
                           source_event_time=d.source_event_time)
        frontier = getattr(d.run_ctx, "last_finalised_event_time", None)
        if frontier is not None and target_event_time < frontier:
            return Outcome("rejected_driver_target_before_simulation_frontier",
                           event_type=event_type, target_event_time=target_event_time,
                           last_finalised_event_time=frontier)
        dc = 0
    elif isinstance(scheduling_origin, TerminalRotation):
        tr = scheduling_origin
        if (tr.eq is not eq) or (tr.run_ctx is not eq.owner_run_context) \
                or (getattr(tr.run_ctx, "event_queue", None) is not eq):
            return Outcome("rejected_driver_context_mismatch", event_type=event_type)
        if not driver_kind_may_seat("ROUND_ROTATION_BOOTSTRAP", event_type):
            return Outcome("rejected_driver_kind_event_type_mismatch",
                           event_type=event_type,
                           driver_source_kind="ROUND_ROTATION_BOOTSTRAP")
        if target_event_time != tr.target_event_time:
            return Outcome("rejected_driver_target_context_mismatch",
                           event_type=event_type, target_event_time=target_event_time,
                           carried_target_event_time=tr.target_event_time)
        if not (target_event_time > tr.predecessor_terminal_time):
            return Outcome("rejected_driver_target_before_source",
                           event_type=event_type, target_event_time=target_event_time,
                           source_event_time=tr.predecessor_terminal_time)
        frontier = getattr(tr.run_ctx, "last_finalised_event_time", None)
        if frontier is not None and target_event_time < frontier:
            return Outcome("rejected_driver_target_before_simulation_frontier",
                           event_type=event_type, target_event_time=target_event_time,
                           last_finalised_event_time=frontier)
        dc = 0
    elif isinstance(scheduling_origin, OrdinaryDispatch):
        octx = scheduling_origin
        src_time = octx.dispatch_envelope["event_time"]
        src_cycle = octx.dispatch_envelope["delta_cycle"]
        src_phase = MICROPHASE_ORDINAL[octx.dispatched_event_ref.microphase]
        tgt_phase = MICROPHASE_ORDINAL[target_microphase]
        if target_event_time > src_time:
            dc = 0
        elif target_event_time == src_time:
            dc = src_cycle if tgt_phase > src_phase else src_cycle + 1
        else:
            return Outcome("rejected_backward_time", event_type=event_type)
    else:
        return Outcome("rejected_invalid_scheduling_origin", event_type=event_type,
                       scheduling_origin=scheduling_origin)

    # AF3: full descriptor schema enforcement BEFORE any state mutation.
    d = DESCRIPTORS.get(event_type)
    if d is None:
        return Outcome("rejected_event_type_unknown", event_type=event_type)
    if target_microphase != d.target_microphase:
        return Outcome("rejected_microphase_mismatch", event_type=event_type,
                       target_microphase=target_microphase,
                       expected_microphase=d.target_microphase)
    missing = [k for k in d.allowed_payload_keys if k not in payload]
    permitted = set(d.allowed_payload_keys) | set(d.optional_payload_keys)
    extra = [k for k in payload if k not in permitted]
    if missing or extra:
        return Outcome("rejected_payload_schema_mismatch", event_type=event_type,
                       missing_fields=missing, extra_fields=extra)
    tie_key = _tie_key(d, payload)
    if tie_key is None:
        return Outcome("rejected_stable_tie_key_unavailable", event_type=event_type)

    # AE8: atomic registration — mint seq + EventRef, create QUEUED record, insert.
    eq.event_creation_seq += 1
    seq = eq.event_creation_seq
    event_ref = EventRef(ORDINARY_EVENT, event_type, target_event_time, dc,
                         target_microphase, seq)
    dispatch_envelope = {"envelope_namespace": ORDINARY_EVENT,
                         "event_time": target_event_time, "delta_cycle": dc,
                         "event_seq": seq, "hook_id": None}
    record = QueuedEventRecord(event_ref, event_type, dispatch_envelope,
                               dict(payload), "QUEUED")
    eq.queued_event_registry[event_ref] = record
    order_key = (target_event_time, dc, MICROPHASE_ORDINAL[target_microphase],
                 tie_key, seq)
    eq.event_queue[event_ref] = order_key
    return Outcome("scheduled", event_ref=event_ref, record=record)


# --------------------------------------------------------------------------- CancelQueuedEvent
def CancelQueuedEvent(eq: EventQueue, run_ctx: Any, event_ref: EventRef,
                      cancellation_reason: str,
                      cancellation_context: Any = None) -> Outcome:
    """The SOLE queue-owner cancellation (AE1); AI4 reconciles a cancelled driver seat."""
    rec = eq.queued_event_registry.get(event_ref)
    if rec is None:
        return Outcome("cancellation_unknown_event", event_ref=event_ref)
    if rec.queue_status == "QUEUED":
        eq.event_queue.pop(event_ref, None)
        rec.queue_status = "CANCELLED"
        # AI4: reconcile a cancelled sim-driver seat to CANCELLED via the reverse binding.
        # The reconcile RESULT is captured (S2A-5): a coherent commit returns
        # driver_request_status_set; a declared integrity failure (e.g. the request already
        # terminal) returns a status_mismatch that the caller can record.
        drid = run_ctx.driver_request_by_seat_event_ref.get(event_ref)
        reconcile = None
        if drid is not None:
            reconcile = run_ctx.set_driver_request_status(
                drid, expected_status="SEATED", new_status="CANCELLED",
                disposition=Outcome("driver_request_seat_cancelled",
                                     event_ref=event_ref, reason=cancellation_reason))
        return Outcome("event_cancelled", event_ref=event_ref, reconcile=reconcile)
    if rec.queue_status == "DISPATCHING":
        return Outcome("event_already_dispatching", event_ref=event_ref)
    return Outcome("cancellation_terminal_noop", event_ref=event_ref)
