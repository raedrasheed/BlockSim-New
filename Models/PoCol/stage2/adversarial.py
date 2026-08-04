"""Stage-5 adversarial-behaviour and parameterised incentive model for the PoCol core.

The algorithm is **PoCol**; the energy-saving mechanism remains **the idle policy within
PoCol** (never nonce partitioning).  The security floor remains an operational
active-capacity floor only; dynamic difficulty remains excluded.

Stage 5 MODELS bounded behaviours and MEASURES outcomes.  It makes NO claim of incentive
compatibility, fairness, Sybil resistance, selfish-mining resistance, coalition
resistance, common-prefix security, chain-quality security, or Bitcoin/PoW-equivalent
security.  All adversarial and incentive features are DISABLED by default so the accepted
Stage-4C baseline is behaviourally unchanged.

Three explicit value layers are kept distinct wherever a participant claim can differ
from ground truth (S5-3):

* ``actual_*``   — simulator ground truth (the physical search core always runs on it);
* ``reported_*`` — miner-provided information (never silently overwrites ground truth);
* ``accepted_*`` — what the MODELED protocol accepts after the MODELED audit abstraction
  (never described as cryptographically proven).
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple

# --------------------------------------------------------------------- vocabularies
ACTOR_CLASSES = ("HONEST", "CRASH_FAULTY", "RATIONAL", "BYZANTINE",
                 "ADVERSARIAL_COORDINATOR")
# actor classes counted on the ADVERSARIAL side of q_adv(t) (S5-11); HONEST and
# CRASH_FAULTY are the non-strategic side.
ADVERSARIAL_ACTOR_CLASSES = ("RATIONAL", "BYZANTINE", "ADVERSARIAL_COORDINATOR")

BEHAVIOUR_FLAGS = ("FREE_RIDER", "HASH_RATE_MISREPORTER", "ASSIGNMENT_SPLITTER",
                   "PROGRESS_WITHHOLDER", "FALSE_EXHAUSTION_CLAIMER",
                   "SOLUTION_WITHHOLDER", "DELAYED_WAKE", "OUT_OF_RANGE_ACTOR",
                   "IDLE_POLICY_DEFECTOR")

SOLUTION_RELEASE_POLICIES = ("PROMPT_RELEASE", "DELAYED_RELEASE", "NEVER_RELEASE")

CLAIM_TYPES = ("PROGRESS_REPORT", "EXHAUSTION_CLAIM")

REWARD_COMPONENTS = ("WORK_REWARD", "AVAILABILITY_REWARD", "WINNER_REWARD",
                     "RESERVE_ACTIVATION_REWARD", "REASSIGNMENT_REWARD")
PENALTY_COMPONENTS = ("ABANDONMENT_PENALTY", "FALSE_CLAIM_PENALTY",
                      "INVALID_MESSAGE_PENALTY")

ACCOUNTING_MODES = ("NAIVE_IDENTITY_ACCOUNTING", "ENTITY_AND_LINEAGE_DEDUPLICATED")

# miner states that count as sanctioned availability residency for the availability
# reward (availability is a RESIDENCY quantity — it is never proof of actual work, S5-10).
AVAILABILITY_STATES = ("REGISTERED", "RESERVE", "ACTIVE_HASHING", "EXHAUSTED_PENDING",
                       "LOW_POWER_LISTEN", "WAKING")

# S5-5/S5-6: the honest no-block closure label for a round whose nonce domain was NOT actually
# searched because an accepted false-exhaustion claim left an uncovered suffix, or because a
# valid solution was withheld.  Such a round must NEVER be reported as a full-domain
# exhaustion — the domain coverage claim would simply be untrue.
ADVERSARIAL_COVERAGE_GAP_NO_BLOCK = "ROUND_CLOSED_WITH_ADVERSARIAL_COVERAGE_GAP"


# --------------------------------------------------------------------- policies
@dataclass
class AdversarialPolicy:
    """Immutable Stage-5 adversarial-model configuration (disabled by default, S5-2).

    A non-default configuration is used only in deterministic Stage-5 tests and pilot
    micro-scenarios.  No parameter value is claimed to be optimal, equilibrium-producing,
    fair or Sybil-resistant.
    """

    enabled: bool = False
    deterministic_seed: int = 1
    # modeled audit abstraction (S5-3): probability that a false/withheld claim is
    # detected.  This is a MODEL PARAMETER, not a cryptographic verification claim.
    audit_detection_probability: float = 1.0
    # solution withholding (S5-6).
    solution_release_policy: str = "PROMPT_RELEASE"
    solution_withholding_delay: float = 0.0
    # delayed wake (S5-7).
    delayed_wake_extra_latency: float = 0.0
    # free riding / misreporting (S5-4).
    free_rider_work_fraction: float = 1.0
    reported_hash_rate_multiplier: float = 1.0
    # false exhaustion / progress withholding (S5-5).
    # S5A-7: the reported exhaustion claim is derived DETERMINISTICALLY as
    #   reported = min(range_end, cursor + false_exhaustion_claim_offset)
    # so the offset has an executable effect.  The declared meaning of 0 is "claim exactly the
    # current cursor" — a zero-offset claim reports the truth and is therefore NOT a false
    # claim, and does not create a coverage gap.  Set a positive offset (or
    # ``false_exhaustion_claims_range_end``) to model a miner that overstates its coverage.
    false_exhaustion_claim_offset: int = 0
    # when true the claimer asserts the FULL range_end regardless of the offset (the strongest
    # modeled overstatement); kept explicit so the offset never silently means "range_end".
    false_exhaustion_claims_range_end: bool = True
    progress_withholding_fraction: float = 0.0
    # assignment splitting / identity multiplication (S5-8; exploratory sensitivity only —
    # NOT a Sybil defence and never described as one).
    assignment_split_count: int = 1
    sybil_identity_count: int = 1
    # adversarial allocation scenario (S5-4): assignment SIZING may use reported rates
    # ONLY when this is explicitly enabled; physical work always uses actual rates.
    coordinator_uses_reported_hash_rate: bool = False
    maximum_actions_per_round: int = 1000
    # exploratory adversarial-share threshold for duration-above reporting (S5-11).
    q_adv_threshold: float = 0.5
    # out-of-range attempt offset: attempted nonce = lease range_end + offset (S5-9).
    out_of_range_nonce_offset: int = 0
    # declared adversarial entities: (EntityID, actor_class, (miner_ids...), coalition|None).
    entities: tuple = ()
    # declared per-miner behaviours: (round_seq | 0 for every round, MinerID, (flags...)).
    miner_behaviours: tuple = ()

    def __post_init__(self) -> None:
        if not (0.0 <= self.audit_detection_probability <= 1.0):
            raise ValueError("audit_detection_probability must be in [0,1]")
        if not (0.0 <= self.free_rider_work_fraction <= 1.0):
            raise ValueError("free_rider_work_fraction must be in [0,1]")
        if not (0.0 <= self.progress_withholding_fraction <= 1.0):
            raise ValueError("progress_withholding_fraction must be in [0,1]")
        if self.solution_release_policy not in SOLUTION_RELEASE_POLICIES:
            raise ValueError(f"unsupported solution_release_policy: "
                             f"{self.solution_release_policy!r}")
        if self.solution_withholding_delay < 0 or self.delayed_wake_extra_latency < 0:
            raise ValueError("withholding/wake delays must be non-negative")
        if self.reported_hash_rate_multiplier <= 0:
            raise ValueError("reported_hash_rate_multiplier must be positive")
        if self.false_exhaustion_claim_offset < 0:
            raise ValueError("false_exhaustion_claim_offset must be non-negative")
        if self.assignment_split_count < 1 or self.sybil_identity_count < 1:
            raise ValueError("split/identity counts must be >= 1")
        if self.maximum_actions_per_round < 0:
            raise ValueError("maximum_actions_per_round must be non-negative")
        for ent in self.entities:
            _eid, klass, mids, _coal = ent
            if klass not in ACTOR_CLASSES:
                raise ValueError(f"unsupported actor_class: {klass!r}")
            if not isinstance(mids, tuple):
                raise ValueError("entity controlled_miner_ids must be a tuple")
        for beh in self.miner_behaviours:
            _rseq, _mid, flags = beh
            for f in flags:
                if f not in BEHAVIOUR_FLAGS:
                    raise ValueError(f"unsupported behaviour flag: {f!r}")


@dataclass
class IncentivePolicy:
    """Immutable Stage-5 incentive configuration (disabled, all rates zero by default).

    Reward/penalty parameters are MODEL PARAMETERS for deterministic tests and pilot
    micro-scenarios only.  No value is claimed optimal, equilibrium-producing, fair or
    Sybil-resistant.
    """

    enabled: bool = False
    # reward rates (default zero, S5-2).
    r_work: float = 0.0        # per unique accepted committed evaluation
    r_avail: float = 0.0       # per second of sanctioned availability residency
    r_win: float = 0.0         # per accepted block (to its solver only)
    r_reserve: float = 0.0     # per completed reserve activation request
    r_reassign: float = 0.0    # per completed reassignment request
    # penalty rates (default zero).
    q_abandon: float = 0.0     # intentional abandonment
    q_false: float = 0.0       # detected false claim
    q_invalid: float = 0.0     # rejected invalid/out-of-range action
    reward_deduplication_policy: str = "ENTITY_AND_LINEAGE_DEDUPLICATED"
    availability_eligibility_policy: str = "SANCTIONED_RESIDENCY"
    work_reward_basis: str = "UNIQUE_ACCEPTED_COMMITTED_EVALUATIONS"
    assignment_split_policy: str = "PER_RANGE_LINEAGE"
    entity_aggregation_enabled: bool = True
    # crash-fault injection is NOT penalised unless explicitly configured (S5-10).
    penalise_crash_faults: bool = False

    def __post_init__(self) -> None:
        if self.reward_deduplication_policy not in ACCOUNTING_MODES:
            raise ValueError(f"unsupported reward_deduplication_policy: "
                             f"{self.reward_deduplication_policy!r}")
        for name in ("r_work", "r_avail", "r_win", "r_reserve", "r_reassign",
                     "q_abandon", "q_false", "q_invalid"):
            if getattr(self, name) < 0:
                raise ValueError(f"{name} must be non-negative")


# --------------------------------------------------------------------- actor records
@dataclass(frozen=True)
class AdversarialEntity:
    """One immutable adversarial (or honest) entity controlling >= 1 miner identity."""

    EntityID: Any
    actor_class: str
    controlled_miner_ids: Tuple[Any, ...]
    coalition_id: Any = None
    disposition: Any = None


@dataclass(frozen=True)
class MinerBehaviourProfile:
    """One ROUND-BOUND, IMMUTABLE behaviour profile (S5-1).

    Materialised exactly once when the round's participant set is prepared; immutable
    once the round starts (frozen dataclass); replay-safe (re-materialisation returns
    the existing profile).
    """

    MinerID: Any
    EntityID: Any
    RoundID: Any
    behaviour_set: Tuple[str, ...]
    actual_hash_rate: float
    reported_hash_rate: float
    work_fraction: float
    wake_delay_multiplier: float
    solution_release_policy: str
    progress_reporting_policy: str
    exhaustion_claim_policy: str
    assignment_split_count: int
    identity_group_id: Any
    behaviour_generation: int


# --------------------------------------------------------------------- claim / action records
@dataclass
class ProgressClaim:
    """One miner-reported progress/exhaustion claim through the modeled audit (S5-3/S5-5)."""

    ClaimID: Any
    RoundID: Any
    TemplateID: Any
    LeaseID: Any
    MinerID: Any
    actual_frontier: int
    reported_frontier: int
    claim_type: str
    audit_draw: float
    detection_probability: float
    detected: bool
    accepted: bool
    accepted_frontier: int
    # S5B-7: the OVERSTATEMENT (how much the miner claimed beyond what it really searched) is a
    # DIFFERENT quantity from the actual uncovered suffix (how much of the range is genuinely
    # unsearched).  Coverage accounting and round closure must use the latter.
    claim_overstatement: int = 0
    actual_unsearched_suffix: int = 0
    disposition: Any = None


@dataclass
class WithheldSolutionRecord:
    """One valid solution consulted against its finder's behaviour profile (S5-6)."""

    WithheldSolutionID: Any
    RoundID: Any
    TemplateID: Any
    MinerID: Any
    AssignmentID: Any
    assignment_version: int
    nonce: int
    digest: int
    found_time: float
    release_policy: str
    scheduled_release_time: Optional[float] = None
    release_event_ref: Any = None
    release_time: Optional[float] = None
    status: str = "WITHHELD"     # WITHHELD -> RELEASED_ACCEPTED / RELEASED_TOO_LATE /
                                 # HIDDEN_AT_CLOSE / CANCELLED_AT_CLOSE
    alternative_solution_won: bool = False
    disposition: Any = None


@dataclass
class DelayedWakeAction:
    """One intentional delayed-wake action (S5-7); round-bound and replay-safe."""

    ActionID: Any
    RoundID: Any
    MinerID: Any
    honest_expected_wake_time: float
    adversarial_scheduled_wake_time: float
    extra_delay: float
    actual_wake_time: Optional[float] = None
    # S5B-4: which REAL wake lifecycle this action delayed, and the real request identity /
    # EventRef of that wake.  Both are part of the action's audit trail, not decoration.
    wake_lifecycle: str = "UNSPECIFIED"
    wake_request_identity: Any = None
    wake_generation: int = 0
    # S5A-6: measured from REAL security-floor observations at round close, never a constant.
    below_floor_overlap: float = 0.0
    another_reserve_activated: bool = False
    realised_extra_delay: float = 0.0
    incremental_wake_energy_j: float = 0.0
    impact_finalised: bool = False
    penalty_eligible: bool = True
    status: str = "PENDING"      # PENDING -> COMPLETED / CANCELLED_AT_CLOSE
    disposition: Any = None


@dataclass
class InvalidActionRecord:
    """One rejected invalid/out-of-range attempt (S5-9)."""

    InvalidActionID: Any
    RoundID: Any
    TemplateID: Any
    MinerID: Any
    action_type: str
    attempted_nonce: Optional[int]
    attempted_assignment_id: Any
    detected_at: float
    rejected: bool
    penalty_eligible: bool
    disposition: Any = None


@dataclass
class AcceptedFrontierRecord:
    """S5A-1: the THREE-VALUE frontier decision for one adversarial claim, kept strictly SEPARATE
    from the accepted Stage-4C authoritative physical ``RangeProgress.committed_frontier``.

    ``actual_frontier`` is simulator ground truth and is monotonic.  ``reported_frontier`` is the
    miner's claim.  ``accepted_frontier`` is the modeled protocol decision after the modeled
    audit and MAY be below ``actual_frontier`` — but recording that decision NEVER rewinds the
    physical frontier, which continues to describe what was really committed.

    Bound to round / template / slice / lease / assignment version, so replaying the same claim
    returns the same decision and performs no second effect.
    """

    RecordID: Any
    RoundID: Any
    TemplateID: Any
    RangeSliceID: Any
    LeaseID: Any
    assignment_version: int
    MinerID: Any
    EntityID: Any
    actual_frontier: int
    reported_frontier: int
    accepted_frontier: int
    physical_committed_frontier_at_decision: int
    reassignment_start: Optional[int] = None
    reevaluation_interval: Optional[Tuple[int, int]] = None
    detected: bool = False
    disposition: Any = None


@dataclass
class SubAssignmentRecord:
    """S5A-4: one EXECUTABLE subassignment created by an ASSIGNMENT_SPLITTER.

    Subranges are disjoint and their union equals the entity's original allocated range.  Every
    subassignment carries an explicit share of the ENTITY's single physical capacity budget: the
    shares sum to the entity's actual hash rate, so splitting an assignment can never manufacture
    physical throughput.  This is an accounting / sensitivity model, NOT a Sybil defence.
    """

    SubAssignmentID: Any
    ParentAssignmentID: Any
    RoundID: Any
    TemplateID: Any
    EntityID: Any
    MinerID: Any
    index: int
    range_start: int
    range_end: int                      # exclusive
    capacity_share: float               # nonces/second budgeted to this subassignment
    entity_capacity_budget: float       # the entity's TOTAL actual physical capacity
    lineage_id: Any = None
    # S5B-6: the record is the ACCOUNTING UNIT, not decoration.  Every physical evaluation the
    # parent assignment commits is mapped onto exactly one subassignment per nonce position by
    # the virtual-subassignment accounting authority, and these fields are what the
    # subassignment view of the round is derived from.
    evaluated_nonce_count: int = 0
    first_evaluation_time: Optional[float] = None
    last_evaluation_time: Optional[float] = None
    disposition: Any = None


@dataclass
class VirtualIdentityRecord:
    """S5A-4: one declared virtual identity bound to a single EntityID.

    A virtual identity is an ACCOUNTING artefact only: it creates no additional physical
    capacity, holds no additional assignment or lease, and is counted separately from the
    entity's real miner count.  Declaring identities is never described as a capability the
    protocol is shown to resist.
    """

    VirtualIdentityID: Any
    EntityID: Any
    RoundID: Any
    index: int
    backing_miner_id: Any
    grants_physical_capacity: bool = False
    disposition: Any = None


@dataclass
class AbandonmentActionRecord:
    """S5A-5: one EXECUTED intentional abandonment.

    An ABANDONMENT_PENALTY may be emitted ONLY when such a record exists.  Declaring the
    IDLE_POLICY_DEFECTOR flag in a profile is not itself an abandonment: if the round closes
    before the action executes there is no action and therefore no penalty.  Crash and failure
    paths are NOT intentional abandonment unless explicitly configured.
    """

    ActionID: Any
    RoundID: Any
    TemplateID: Any
    EntityID: Any
    MinerID: Any
    LeaseID: Any
    actual_frontier: int
    abandoned_suffix_start: int
    abandoned_suffix_end: int           # exclusive
    action_time: float
    status: str = "EXECUTED"
    penalty_eligible: bool = True
    disposition: Any = None

    def abandoned_nonce_count(self) -> int:
        return max(0, self.abandoned_suffix_end - self.abandoned_suffix_start)

    def actual_unsearched_suffix(self) -> int:
        """S5B-7: the REAL uncovered suffix left behind — range_end minus the actual frontier.
        This is what the round's coverage accounting and closure label must use."""
        return max(0, self.abandoned_suffix_end - self.actual_frontier)


@dataclass(frozen=True)
class IncentiveLedgerEntry:
    """One immutable, replay-idempotent reward/penalty ledger entry (S5-10)."""

    EntryID: Any
    RoundID: Any
    TemplateID: Any
    EntityID: Any
    MinerID: Any
    component: str
    source_event_id: Any
    range_lineage_id: Any
    amount: float
    sign: int                    # +1 reward, -1 penalty
    eligibility_reason: str
    deduplication_key: Any
    disposition: Any = None


# --------------------------------------------------------------------- deterministic audit
def audit_draw(seed: int, claim_key: Any) -> float:
    """Deterministic uniform draw in [0,1) for the MODELED audit abstraction.

    Derived from SHA-256 over the policy seed and the immutable claim identity, so exact
    replay of the same claim gets the same draw (idempotent audit, S5-3).
    """
    h = hashlib.sha256(f"{seed}|{claim_key}".encode()).digest()
    return int.from_bytes(h[:8], "big") / float(1 << 64)


def default_adversarial_stats() -> Dict[str, Any]:
    """The Stage-5 counter ledger (all zero when the model is disabled)."""
    return {
        "free_rider_count": 0, "hash_rate_misreport_count": 0,
        "assignment_split_count": 0, "progress_withholding_count": 0,
        "false_exhaustion_attempted": 0, "false_exhaustion_detected": 0,
        "false_exhaustion_accepted": 0, "coverage_gap_nonce_count": 0,
        "adversarial_duplicate_evaluation_count": 0,
        "solution_withholding_count": 0, "withheld_released_count": 0,
        "withheld_never_released_count": 0, "withheld_release_too_late_count": 0,
        "withheld_total_hidden_duration": 0.0,
        "withheld_alternative_solution_won_count": 0,       # S5A-7
        "adversarial_coverage_gap_round_count": 0,
        "delayed_wake_count": 0, "out_of_range_attempt_count": 0,
        "invalid_action_rejection_count": 0,
        # --- S5B-4 wake-lifecycle coverage (one scalar counter per REAL wake lifecycle) ---
        "delayed_wake_unattributed_refused": 0,            # MUST remain 0 (every wake is attributed)
        "delayed_wake_replay_no_effect_count": 0,
        "delayed_wake_primary_count": 0,
        "delayed_wake_reserve_activation_count": 0,
        "delayed_wake_path_a_reassignment_count": 0,
        "delayed_wake_path_b_reserve_count": 0,
        "delayed_wake_unspecified_lifecycle_count": 0,     # MUST remain 0 in an executed run
        # --- S5A-1 three-value frontier separation ---
        "accepted_frontier_record_count": 0,
        "accepted_below_actual_count": 0,
        "physical_frontier_rewind_count": 0,               # MUST remain 0
        # --- S5A-2 unique-nonce work-reward union ---
        "unique_rewarded_nonce_count": 0,
        "physical_evaluation_count": 0,
        "adversarial_reevaluation_count": 0,
        "duplicate_work_reward_prevented_count": 0,
        "work_reward_union_residual": 0.0,
        # --- S5A-3 reported-rate allocation ---
        "reported_rate_allocation_rounds": 0,
        "allocation_range_size_distortion_max_ratio": 1.0,
        # --- S5A-4 executable splitting / identities ---
        "subassignment_count": 0,
        "virtual_identity_count": 0,
        "subassignment_capacity_residual": 0.0,            # MUST remain 0.0
        # --- S5B-6 virtual-subassignment accounting authority ---
        "subassignment_mapped_evaluation_count": 0,
        "subassignment_unmapped_evaluation_count": 0,      # MUST remain 0
        "entity_physical_capacity_residual": 0.0,          # MUST remain 0.0
        "virtual_identity_physical_capacity_granted": 0.0,  # MUST remain 0.0
        # --- S5A-5 executed abandonment ---
        "abandonment_action_count": 0,
        "abandonment_penalty_without_action_count": 0,     # MUST remain 0
        "abandoned_nonce_count": 0,
        # --- S5A-7 declared-limit enforcement ---
        "actions_rejected_over_limit": 0,
        # --- S5B-7 coverage separation ---
        "claim_overstatement_total": 0,
        "abandonment_coverage_gap_rounds": 0,
        "attack_induced_floor_breach_duration": 0.0,
        "allocation_distortion_max_ratio": 1.0,
        "actual_reported_divergence_count": 0,
        "reported_accepted_divergence_count": 0,
        # incentive accounting (both accounting views computed in parallel, S5-8).
        "naive_identity_reward_total": 0.0,
        "deduplicated_entity_reward_total": 0.0,
        "work_reward_total": 0.0, "availability_reward_total": 0.0,
        "winner_reward_total": 0.0, "reserve_activation_reward_total": 0.0,
        "reassignment_reward_total": 0.0,
        "abandonment_penalty_total": 0.0, "false_claim_penalty_total": 0.0,
        "invalid_message_penalty_total": 0.0,
    }


def default_q_adv_state() -> Dict[str, Any]:
    """Piecewise-constant q_adv(t) accumulators (S5-11).  q_adv is NA when H_active == 0."""
    return {"last_time": None, "last_q": None, "last_active": 0.0,
            "max_q": None, "q_time_integral": 0.0, "active_duration": 0.0,
            "above_threshold_duration": 0.0, "na_duration": 0.0}
