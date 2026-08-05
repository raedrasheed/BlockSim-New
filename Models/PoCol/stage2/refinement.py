"""Stage-8R revised idle and reserve-control policy within PoCol (pure structures/helpers).

This module defines the REVISED operating policy's data model: controller modes, the
breach-episode authority (R1), hysteresis thresholds (R2), the one-live-activation-batch
rule (R3), predictive wake-ahead inputs (R4) and the H_pipeline reporting quantity (R5).

Scope discipline (unchanged from the accepted engine):

* The SHA-256 search, target, difficulty, nonce-domain semantics, evaluation-ledger
  semantics, accepted-frontier authority, reward model, adversarial model and physical
  hash-rate definitions are NOT touched by any controller mode.
* ``H_effective`` remains PHYSICAL: WAKING miners contribute zero to it (R5).
* ``H_pipeline`` is a scheduling forecast only — never a security metric, never
  substituted for ``H_effective`` in any integrity check.
* Every refinement is DISABLED by default: mode ``LEGACY_REACTIVE`` reproduces the
  accepted Stage-8M controller exactly.
* A prediction is an engineering estimate, not a security proof.

Only pure data structures and pure helpers live here; the event-seating / mutation logic
stays in ``simulator.py`` (same layering as ``security.py``).
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple

CONTROLLER_MODES = ("LEGACY_REACTIVE", "HYSTERESIS_ONLY", "HYSTERESIS_PREDICTIVE",
                    "HYSTERESIS_PREDICTIVE_REASSIGNMENT",
                    # Stage-8S: STAGE8R_PREDICTIVE_STATIC_FLOOR is behaviourally identical
                    # to HYSTERESIS_PREDICTIVE (it exists as the frozen named baseline);
                    # the two USEFUL_FLOOR modes add the useful-work-aware target and (for
                    # the second) work-conserving coarse suffix repartition.
                    "STAGE8R_PREDICTIVE_STATIC_FLOOR",
                    "USEFUL_FLOOR_ONLY", "USEFUL_FLOOR_COARSE_REASSIGNMENT",
                    # Stage-8U: the single-handoff useful-work policy within PoCol — at
                    # most ONE donor->receiver handoff per round plus at most ONE
                    # reserve-wake fallback per round (U1..U5).
                    "USEFUL_FLOOR_SINGLE_HANDOFF")
PREDICTIVE_MODES = ("HYSTERESIS_PREDICTIVE", "HYSTERESIS_PREDICTIVE_REASSIGNMENT",
                    "STAGE8R_PREDICTIVE_STATIC_FLOOR",
                    "USEFUL_FLOOR_ONLY", "USEFUL_FLOOR_COARSE_REASSIGNMENT",
                    "USEFUL_FLOOR_SINGLE_HANDOFF")
USEFUL_FLOOR_MODES = ("USEFUL_FLOOR_ONLY", "USEFUL_FLOOR_COARSE_REASSIGNMENT",
                      "USEFUL_FLOOR_SINGLE_HANDOFF")

EPISODE_STATUSES = ("OPEN", "RECOVERY_IN_PROGRESS", "RECOVERED", "ROUND_CLOSED",
                    "UNATTAINABLE")
TERMINAL_EPISODE_STATUSES = ("RECOVERED", "ROUND_CLOSED", "UNATTAINABLE")

BATCH_STATUSES = ("LIVE", "TERMINAL")

HANDOFF_STATUSES = ("OPEN", "COMMITTED", "COMPLETED", "CANCELLED", "FAILED",
                    "ROUND_CLOSED")
TERMINAL_HANDOFF_STATUSES = ("COMPLETED", "CANCELLED", "FAILED", "ROUND_CLOSED")


@dataclass(frozen=True)
class ControllerPolicy:
    """Immutable, validated revised-controller configuration.

    The frozen engineering constants (0.78 / 0.80 / 0.82, lookahead = cooldown = the
    activation wake latency, 25-nonce reassignment chunk) are DECLARED here and are not
    tunable after the Stage-8R pilot.  ``central_target_ratio`` maps onto the frozen
    ``SecurityFloorPolicy.minimum_active_hash_rate`` (0.80 x H0), so the reactive trigger
    and recovery threshold are derived from the SAME frozen floor:

        trigger  = minimum_active_hash_rate * reactive_trigger_ratio / central_target_ratio
        recovery = minimum_active_hash_rate * recovery_ratio        / central_target_ratio

    The central 0.80 target is an OPERATIONAL target, not a formal security threshold.
    """

    mode: str = "LEGACY_REACTIVE"
    reactive_trigger_ratio: float = 0.78
    central_target_ratio: float = 0.80
    recovery_ratio: float = 0.82
    #: ``None`` means "equal to SecurityFloorPolicy.activation_wake_latency" (frozen rule).
    lookahead_seconds: Optional[float] = None
    cooldown_seconds: Optional[float] = None
    #: R6 exploratory bounded suffix reassignment (fixed chunk; never tuned post-pilot).
    reassignment_chunk_nonces: int = 25

    def __post_init__(self) -> None:
        if self.mode not in CONTROLLER_MODES:
            raise ValueError(f"unsupported controller mode: {self.mode!r}")
        if not (0.0 < self.reactive_trigger_ratio < self.central_target_ratio
                < self.recovery_ratio):
            raise ValueError("controller ratios must satisfy 0 < trigger < central < recovery")
        if self.lookahead_seconds is not None and self.lookahead_seconds < 0:
            raise ValueError("lookahead_seconds must be non-negative or None")
        if self.cooldown_seconds is not None and self.cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be non-negative or None")
        if self.reassignment_chunk_nonces <= 0:
            raise ValueError("reassignment_chunk_nonces must be positive")

    # ---- derived frozen quantities -------------------------------------------------
    def is_refined(self) -> bool:
        return self.mode != "LEGACY_REACTIVE"

    def is_predictive(self) -> bool:
        return self.mode in PREDICTIVE_MODES

    def is_useful_floor(self) -> bool:
        return self.mode in USEFUL_FLOOR_MODES

    def is_coarse(self) -> bool:
        return self.mode == "USEFUL_FLOOR_COARSE_REASSIGNMENT"

    def is_single_handoff(self) -> bool:
        return self.mode == "USEFUL_FLOOR_SINGLE_HANDOFF"

    def can_reassign_to_receivers(self) -> bool:
        """True when the mode's mechanism can actually deliver ceded suffix work to an
        already-awake receiver (coarse repartition or the single handoff)."""
        return self.is_coarse() or self.is_single_handoff()

    def trigger_rate(self, minimum_active_hash_rate: float) -> float:
        return minimum_active_hash_rate * self.reactive_trigger_ratio / self.central_target_ratio

    def recovery_rate(self, minimum_active_hash_rate: float) -> float:
        return minimum_active_hash_rate * self.recovery_ratio / self.central_target_ratio

    def lookahead(self, wake_latency: float) -> float:
        return wake_latency if self.lookahead_seconds is None else self.lookahead_seconds

    def cooldown(self, wake_latency: float) -> float:
        return wake_latency if self.cooldown_seconds is None else self.cooldown_seconds


@dataclass
class BreachEpisode:
    """R1: the immutable-identity breach-episode authority.

    At most ONE live activation batch may belong to an episode at any time; repeated
    capacity observations inside the episode never seat a second batch while a sufficient
    live batch exists; exact replay returns the existing episode.  An episode never closes
    merely because H_effective crosses the central target — RECOVERED requires the recovery
    threshold (and no live batch still in flight).  Round closure terminalises every
    episode; no episode may affect the next round.
    """

    BreachEpisodeID: Any
    RoundID: Any
    TemplateID: Any
    episode_generation: int
    opened_at: float
    opened_h_effective: float
    target_hash_rate: float
    reactive_trigger_hash_rate: float
    recovery_hash_rate: float
    status: str = "OPEN"
    live_activation_batch_id: Optional[Any] = None
    activation_batch_ids: List[Any] = field(default_factory=list)
    recovered_at: Optional[float] = None
    closed_at: Optional[float] = None
    disposition: Any = None
    opened_reason: str = "REACTIVE"          # REACTIVE | PREDICTIVE
    cooldown_until: float = 0.0


@dataclass
class ActivationBatch:
    """R3: one activation batch — the set of reserve-activation requests seated together
    from one controller decision, owned by exactly one breach episode."""

    BatchID: Any
    BreachEpisodeID: Any
    RoundID: Any
    seated_at: float
    request_ids: List[Any] = field(default_factory=list)
    miner_ids: List[Any] = field(default_factory=list)
    requested_hash_rate: float = 0.0
    completed_hash_rate: float = 0.0
    cancelled_hash_rate: float = 0.0
    status: str = "LIVE"
    policy_result: str = ""
    origin: str = "REACTIVE"                 # REACTIVE | PREDICTIVE
    excess_activation_hash_rate: float = 0.0
    under_activation_hash_rate: float = 0.0
    #: physical H_effective and covered capacity at the seat decision (audit fields).
    seat_h_effective: float = 0.0
    seat_covered_capacity: float = 0.0


@dataclass
class PredictionRecord:
    """R4: one predictive wake-ahead decision (an engineering estimate, never a proof)."""

    PredictionID: Any
    RoundID: Any
    decision_time: float
    lookahead: float
    current_h_effective: float
    predicted_h_future: float
    predicted_expiring_miners: List[Any] = field(default_factory=list)
    live_incoming_capacity: float = 0.0
    selected_reserve_set: List[Any] = field(default_factory=list)
    predicted_deficit: float = 0.0
    seated_batch_id: Optional[Any] = None
    # resolved at (or after) the prediction horizon:
    resolution_time: Optional[float] = None
    actual_h_effective_at_horizon: Optional[float] = None
    prediction_error: Optional[float] = None
    false_positive_wake: Optional[bool] = None
    late_wake: bool = False


@dataclass
class CoarseRequest:
    """S8S-4: one immutable coarse-reassignment chunk request.

    The donor's accepted remaining suffix is partitioned into deterministic contiguous
    near-equal chunks; the donor retains the first chunk and each receiver gets at most one
    chunk.  One repartition per donor lineage per breach episode; one live chunk per
    receiver; the chunk union equals the original suffix exactly and chunks are pairwise
    disjoint by construction."""

    CoarseRequestID: Any
    RoundID: Any
    TemplateID: Any
    BreachEpisodeID: Any
    DonorMinerID: Any
    DonorAssignmentID: Any
    ReceiverMinerID: Any
    AssignmentID: Any
    chunk_start: int
    chunk_end: int                      # exclusive
    seated_at: float
    status: str = "SEATED"              # SEATED | ACTIVE | COMPLETED | CANCELLED
    started_at: Optional[float] = None
    completed_at: Optional[float] = None

    def size(self) -> int:
        return self.chunk_end - self.chunk_start


@dataclass
class RoundHandoffEpoch:
    """U1: the per-round single-handoff authority — at most ONE handoff epoch per round.

    The epoch opens when a concrete (donor, receiver, split) proposal exists; exact replay
    returns the existing epoch and performs no second reassignment in the round.  Round
    closure terminalises the epoch; an epoch never crosses rounds.  Statuses: OPEN (proposal
    made), COMMITTED (the atomic split applied), COMPLETED (the receiver's chunk finished
    before round close), CANCELLED (the deterministic benefit gate refused the split),
    FAILED (the atomic apply failed and was fully unwound), ROUND_CLOSED (still live at
    closure)."""

    RoundHandoffEpochID: Any
    RoundID: Any
    TemplateID: Any
    generation: int
    opened_at: float
    donor_miner_id: Optional[Any] = None
    receiver_miner_id: Optional[Any] = None
    source_assignment_id: Optional[Any] = None
    receiver_assignment_id: Optional[Any] = None
    original_suffix: Optional[Tuple[int, int]] = None
    donor_chunk: Optional[Tuple[int, int]] = None
    receiver_chunk: Optional[Tuple[int, int]] = None
    predicted_makespan_before: float = 0.0
    predicted_makespan_after: float = 0.0
    status: str = "OPEN"
    terminal_time: Optional[float] = None
    disposition: Any = None


def h_useful_available(run_ctx: Any, rc: Any, include_receivers: bool,
                       max_receivers: Optional[int] = None) -> Tuple[float, dict]:
    """S8S-2: the maximum ACTUAL capacity assignable useful, non-overlapping nonce work now.

    Includes ONLY (1) ACTIVE_HASHING miners on a non-empty accepted range and (2) — when
    the coarse-reassignment mechanism exists to deliver work (``include_receivers``) —
    already-awake eligible receivers, bounded by the spare whole batches that active donors
    could cede while keeping one batch each.  WAKING miners, reserves, stale assignments
    and any future-solution information are excluded; live wake requests belong to
    H_pipeline only.
    """
    from .security import compute_h_effective            # local import (no cycle at load)
    h_eff, _n, _ids = compute_h_effective(run_ctx, rc)
    cfg = run_ctx.config
    spare_units = 0
    for mid, st in getattr(rc, "search_states", {}).items():
        if st.completed:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":
            continue
        remaining = max(0, st.range_end - st.cursor)
        spare_units += max(0, remaining // cfg.batch_size - 1)
    receivers = []
    if include_receivers:
        live = getattr(run_ctx, "coarse_live_by_receiver", {})
        for mid, st in getattr(rc, "search_states", {}).items():
            if not st.completed or getattr(st, "completion_kind", None) != "EXHAUSTED":
                continue
            m = run_ctx.miners.get(mid)
            if m is None or m.state != "LOW_POWER_LISTEN":
                continue
            if mid in live:
                continue                                  # one live reassignment per receiver
            receivers.append((float(st.hash_rate), str(mid), mid))
        receivers.sort(key=lambda x: (-x[0], x[1]))       # deterministic: rate desc, then id
    cap = spare_units if max_receivers is None else min(spare_units, max_receivers)
    counted = receivers[:cap] if include_receivers else []
    value = h_eff + sum(r for r, _s, _m in counted)
    return value, {"h_effective": h_eff, "spare_batch_units": spare_units,
                   "eligible_receivers": [m for _r, _s, m in receivers],
                   "counted_receivers": [m for _r, _s, m in counted]}


def predict_h_future(run_ctx: Any, rc: Any, now: float, lookahead: float,
                     target_rate: float) -> Tuple[float, dict]:
    """R4 predictive capacity forecast from OBSERVABLE protocol state only.

    Uses: each active miner's assigned range end, its accepted committed cursor and its
    executable hash rate (all controller-observable under the existing model), plus the
    capacity of valid live wake requests expected to complete inside the lookahead window.
    NEVER uses: the future winning nonce, the future accepted solution, any simulator
    oracle, the actual future round-end time, or future random draws.
    """
    expiring: List[Any] = []
    h_surviving = 0.0
    round_id = getattr(rc, "RoundID", None)
    template_id = getattr(rc, "TemplateID_committed", None)
    for mid, st in getattr(rc, "search_states", {}).items():
        if st.completed:
            continue
        m = run_ctx.miners.get(mid)
        if m is None or m.state != "ACTIVE_HASHING":
            continue
        a = rc.assignments.get(st.AssignmentID)
        if a is None or a.get("MinerID") != mid \
                or a.get("assignment_version") != st.assignment_version \
                or a.get("RoundID") != round_id or a.get("TemplateID") != template_id:
            continue
        rng = a.get("range")
        if rng is None or not (rng[0] <= st.cursor < rng[1]):
            continue
        remaining = max(0, rng[1] - st.cursor)
        rate = float(st.hash_rate)
        predicted_remaining_time = remaining / rate if rate > 0 else 0.0
        if predicted_remaining_time > lookahead:
            h_surviving += rate
        else:
            expiring.append(mid)
    live_incoming = 0.0
    wake_latency = run_ctx.config.security_floor.activation_wake_latency
    for req in run_ctx.activation_requests.values():
        if req.RoundID != round_id or req.status not in ("SEATED", "STARTED"):
            continue
        started = req.started_at if req.started_at is not None else req.seated_at
        if started is None:
            continue
        if started + wake_latency <= now + lookahead:
            rr = run_ctx.reserve_records.get((round_id, req.MinerID))
            if rr is not None:
                live_incoming += float(rr.hash_rate)
    # WAKING primaries with a live assignment complete within wake_latency of their start;
    # counted like live wake requests when inside the window (observable protocol state).
    h_future = h_surviving + live_incoming
    return h_future, {"expiring": expiring, "surviving_rate": h_surviving,
                      "live_incoming": live_incoming}


def h_pipeline(run_ctx: Any, rc: Any, h_effective: float) -> float:
    """R5: H_pipeline = H_effective + rates of valid accepted LIVE wake requests.

    A scheduling forecast, NOT current active capacity, NOT an accepted security metric;
    it is never substituted for H_effective in any integrity check and never supports a
    claim that WAKING miners provide current hashing security.
    """
    round_id = getattr(rc, "RoundID", None)
    incoming = 0.0
    for req in run_ctx.activation_requests.values():
        if req.RoundID != round_id or req.status not in ("SEATED", "STARTED"):
            continue
        rr = run_ctx.reserve_records.get((round_id, req.MinerID))
        if rr is not None:
            incoming += float(rr.hash_rate)
    return h_effective + incoming


def controller_stats_template() -> dict:
    """All revised-controller counters, present (zero) in EVERY mode so the run-level
    schema is mode-invariant."""
    return {
        "breach_episode_count": 0,
        "breach_episode_recovered_count": 0,
        "episode_unattainable_count": 0,
        "episode_round_closed_count": 0,
        "episode_closed_with_live_activation_count": 0,
        "total_episode_recovery_time_s": 0.0,
        "activation_batches_seated": 0,
        "predictive_batches_seated": 0,
        "reactive_batches_seated": 0,
        "duplicate_activation_batch_prevented_count": 0,
        "max_batches_per_episode": 0,
        "prediction_decision_count": 0,
        "resolved_prediction_count": 0,
        "sum_absolute_prediction_error": 0.0,
        "false_positive_wake_count": 0,
        "late_wake_count": 0,
        "requested_reserve_hash_rate_total": 0.0,
        "completed_reserve_hash_rate_total": 0.0,
        "cancelled_reserve_hash_rate_total": 0.0,
        "excess_activation_hash_rate_total": 0.0,
        "under_activation_hash_rate_total": 0.0,
        "maximum_H_pipeline": 0.0,
        "H_pipeline_time_integral": 0.0,
        "duration_pipeline_above_target_while_H_effective_below_target": 0.0,
        "controller_suffix_reassignment_count": 0,
        "controller_suffix_reassignment_skipped_in_flight": 0,
        # ---- Stage-8S useful-floor metrics (independent of the static-floor metrics) ----
        "duration_below_useful_floor": 0.0,
        "useful_floor_deficit_area": 0.0,
        "useful_floor_unattainable_count": 0,
        "H_useful_available_time_integral": 0.0,
        "H_useful_target_time_integral": 0.0,
        # ---- Stage-8S coarse-reassignment metrics ----
        "coarse_repartition_count": 0,
        "coarse_reassignment_count": 0,
        "sum_coarse_chunk_size": 0,
        "minimum_coarse_chunk_size": 0,
        "maximum_coarse_chunk_size": 0,
        "donor_lineage_repartition_replay_count": 0,
        "duplicate_reassignment_prevented_count": 0,
        # ---- Stage-8S reserve admission control ----
        "reserve_wakes_rejected_no_useful_work": 0,
        "reserve_wakes_with_bound_work": 0,
        # ---- Stage-8U single-handoff metrics (U1) ----
        "handoff_epoch_count": 0,
        "handoff_committed_count": 0,
        "handoff_completed_count": 0,
        "handoff_failed_count": 0,
        "handoff_cancelled_count": 0,
        "duplicate_handoff_prevented_count": 0,
        # ---- Stage-8U single reserve-wake fallback (U4) ----
        "single_reserve_requests_seated": 0,
        "single_reserve_requests_completed": 0,
        "single_reserve_requests_incomplete": 0,
        "reserve_wake_rejected_short_useful_window": 0,
        "reserve_wake_rejected_awake_receiver_available": 0,
        "reserve_wake_rejected_no_bound_work": 0,
    }
