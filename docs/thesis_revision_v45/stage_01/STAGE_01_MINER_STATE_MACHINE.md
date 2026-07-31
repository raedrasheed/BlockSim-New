# Stage 1 — PoCol Miner State Machine

**Document status:** Stage-1 specification-only. This document DEFINES the per-miner state
machine of **PoCol** with the idle policy enabled. It does NOT claim that any state,
transition, guard, or accounting effect described here is implemented, validated, secure,
fair, or incentive-compatible. Stage 1 SPECIFIES structure; it demonstrates no property.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The low-power mechanism is
**the idle policy within PoCol** — an operating policy INSIDE PoCol, not a new algorithm,
variant, or fork. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are
prohibited.

**Cross-references.** Protocol scope and the accepted baseline (A1) are fixed in
`STAGE_01_PROTOCOL_SCOPE.md`. Round-level states are specified in
`STAGE_01_ROUND_STATE_MACHINE.md`. Symbols and terms are defined in
`STAGE_01_TERMINOLOGY.md`. Invariants are referenced by ID from the separate Invariant
Catalogue.

---

## 1. Scope, separation, and normative conventions

### 1.1 Miner state is per-miner and local

This document specifies the **miner state machine**: the local lifecycle of a single
registered participant identified by its `MinerID`. It is a distinct transition system from
the **round state machine** (`STAGE_01_ROUND_STATE_MACHINE.md`), which is a global property
of a consensus round. The two systems are **coupled only through events** — a round-level
event (for example, entry to `ASSIGNMENT`) may emit an assignment offer that a miner
consumes, causing a local miner transition — but they are never identified with each other.
A miner may be `OFFLINE` while the round is in `HASHING`; the round being in `HASHING` does
NOT force any individual miner into `ACTIVE_HASHING`. This separation is restated in the
round document and is binding throughout the Stage-1 set.

### 1.2 The eight miner states are mutually exclusive

At any instant a miner occupies **exactly one** of the following eight states:

`REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`, `LOW_POWER_LISTEN`,
`WAKING`, `OFFLINE`, `DISQUALIFIED`.

Mutual exclusivity is total: there is no composite or overlapping occupancy, and every
legal transition in Section 3 moves the miner from exactly one of these states to exactly
one of these states.

### 1.3 Energy accounting convention (normative)

Per-miner energy follows the normative state-complete model of
`STAGE_01_PROTOCOL_SCOPE.md` §0.3 and the canonical state-to-power mapping of
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md` §1.0:

    E_i = Σ_{s∈States} (P_{i,s} · t_{i,s})
        + E_transition,i
        + E_coordination,i
        + E_verification,i

over the eight miner states. Each state maps to **exactly one residency power** per the
canonical mapping: `REGISTERED = P_registered` (= `P_listen`); `RESERVE = P_reserve`
(= `P_listen`; low-power standby, **not** `P_offline`); `ACTIVE_HASHING = P_hash`;
`EXHAUSTED_PENDING = P_hash` (short transient); `LOW_POWER_LISTEN = P_listen`;
`WAKING = P_wake`; `OFFLINE = P_offline`; `DISQUALIFIED = P_offline`. Crossing a state
boundary may additionally charge a **one-shot** `E_transition,i` increment and/or an
`E_coordination,i` increment for the messaging required to effect the transition;
`E_verification,i` is a **separate event-energy term** for validating a received early-stop
certificate (see §1.5). Per invariant **I5**, all state durations are ≥ 0 and reconcile to
the fixed horizon `T`: `Σ_{s∈States} t_{i,s} = T` for each miner over the horizon, with **no
residual / `t_other` bucket** — every instant is charged to exactly one of the eight states.

**Only `ACTIVE_HASHING` contributes to the active hash rate.** No other state adds to
`H_active(t)` — in particular `EXHAUSTED_PENDING`, although it draws `P_hash` for its short
transient, contributes **nothing** to `H_active(t)`. Consistent with the accepted baseline
and A1, partitioning the nonce domain does not by itself reduce fixed-horizon energy; the
idle policy reduces energy only by reducing summed active power-time
`Σ_i P_hash,i * t_hash,i`.

### 1.4 Security accounting convention

`H_active(t)` is the aggregate rate of miners in `ACTIVE_HASHING`. `H_honest(t)` and
`H_adversarial(t)` decompose it by attributed behaviour, and `q_adv(t)` is the modeled
adversarial fraction. The "security_accounting_effect" column of the transition table
(Section 3) records only how a transition changes the **modeled** `H_active(t)` census and
the invariant audit log. No security, fairness, or incentive property is claimed for any
transition; monitoring is specified, enforcement soundness is out of scope (scope §C).

### 1.5 Progress-verification convention

A miner's assertion that it has searched (part of) its assigned range is treated ONLY as a
**modeled progress-verification abstraction** (progress commitments; scope §B). Progress
verification and the early-stop certificate (which carries a found solution) are **separate
mechanisms**, not one evidence type. Range exhaustion is governed by **I4, I8a, and the
actual/reported/accepted adjudication model** (ExhaustionAdjudicate); a false exhaustion claim
is a progress/audit violation, **not** an I11 violation. Invariant **I11** applies ONLY to
validating a solution-bearing early-stop certificate — it forbids any false or unverified
early-stop certificate from ending hashing. I11 does **not** gate the range-exhaustion
transition T7 and does **not** prove or confirm exhaustion; target verification checks one
candidate solution, whereas progress verification models claimed range progress.

**Verification-time state rule (CR2).** A miner receiving an unverified early-stop
certificate **remains in `ACTIVE_HASHING`**; it continues hashing while verifying; it
remains included in `H_active(t)`; verification energy is recorded separately as
`E_verification` (a clearly identified coordination/verification energy increment), added on
top of the `ACTIVE_HASHING` residency energy and **not double-counted**; only after **all**
certificate-validation steps pass may the miner leave `ACTIVE_HASHING`; a failed certificate
produces **no** hashing-state transition. **No `VERIFYING` miner state is introduced.**

### 1.6 Difficulty convention

Difficulty is **FIXED** in the confirmatory design (invariant **I12**). No transition,
guard, or action in this document changes difficulty; dynamic-difficulty behaviour is out
of scope (scope §C).

---

## 2. Per-state specification

Each subsection specifies, for one state: exact meaning; allowed computation; allowed
network messages; residency power term; active-hash-rate contribution; whether it may hold
or act on a new range; reward eligibility (NOT SPECIFIED AT STAGE 1 — incentive semantics are deferred to Stage 5;
the only Stage-1 record is that a valid solution may be recorded as having a solver identity,
which by invariant **I2** requires an accepted solution inside the signer's valid current
assignment); permitted incoming and outgoing transitions;
transition guards; transition side effects; timeout behaviour; and failure behaviour.

Reward eligibility is NOT SPECIFIED AT STAGE 1 (deferred to Stage 5); no incentive,
fairness, or reward-crediting property is asserted (scope §C.3). The only Stage-1 record is
solver identity for a valid solution.

### 2.1 `REGISTERED`

- **Exact meaning.** The miner has completed registration and holds a valid `MinerID`, but
  is not currently held in the reserve pool and holds no active nonce-range assignment. It
  is the neutral admitted state and the precondition for receiving any assignment.
- **Allowed computation.** Registration/identity bookkeeping and heartbeat only. No nonce
  search.
- **Allowed network messages.** Registration acknowledgement, capability advertisement,
  heartbeat, and receipt of an assignment offer or reserve-admission notice. It may NOT
  emit solutions, progress commitments, or early-stop certificates.
- **Residency power term.** `P_registered,i` (= `P_listen,i`; low-power admitted residency
  per the canonical mapping, **not** `P_offline`); registration messaging charges
  `E_coordination,i`.
- **Active-hash-rate contribution.** None.
- **May hold/act on a new range.** No. An assignment offer directed at a `REGISTERED` miner
  does not grant an active range in place; it triggers the transition to `WAKING`, where the
  pending assignment is bound and validated before hashing.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From external registration (T1); from `OFFLINE` on
  rejoin (T17); from `RESERVE` on administrative release (T25).
- **Permitted outgoing transitions.** To `RESERVE` (T2); to `WAKING` on assignment offer
  (T3); to `OFFLINE` (T16); to `DISQUALIFIED` on violation (T23).
- **Transition guards.** Admission to `RESERVE` requires reserve-pool capacity; an
  assignment offer requires a committed template (`TemplateID`) and a disjoint candidate
  range consistent with I1.
- **Transition side effects.** Persist `MinerID` and capability record; on offer, bind the
  pending assignment reference carried into `WAKING`.
- **Timeout behaviour.** A registration/idle time-to-live bounds residency; on expiry
  without admission or offer, the miner transitions to `OFFLINE` (T16).
- **Failure behaviour.** A malformed registration or an attributable protocol violation
  routes to `DISQUALIFIED` (T23); loss of heartbeat routes to `OFFLINE` (T16).

### 2.2 `RESERVE`

- **Exact meaning.** A registered miner held in the reserve pool: admitted and available
  for promotion but not currently assigned an active range, so it draws no active hashing
  power. Reserve miners are the population that `SECURITY_RECOVERY` may activate.
- **Allowed computation.** Standby bookkeeping and heartbeat; readiness self-checks. No
  nonce search.
- **Allowed network messages.** Reserve heartbeat/liveness, readiness advertisement, and
  receipt of an activation notice. No solutions, progress commitments, or early-stop
  certificates.
- **Residency power term.** `P_reserve,i` (= `P_listen,i`; low-power standby listening for
  the activation signal, **not** `P_offline`), per the canonical mapping.
- **Active-hash-rate contribution.** None. Reserve residency is invisible to `H_active(t)`
  until promotion completes through `WAKING` into `ACTIVE_HASHING`.
- **May hold/act on a new range.** No while in `RESERVE`; activation binds a pending range
  and routes through `WAKING`.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From `REGISTERED` (T2).
- **Permitted outgoing transitions.** To `WAKING` on reserve activation (T4); to
  `REGISTERED` on administrative release (T25); to `OFFLINE` (T15); to `DISQUALIFIED` (T22).
- **Transition guards.** Activation requires a round-level activation event (typically
  emitted by `SECURITY_RECOVERY`) and a disjoint candidate range consistent with I1.
- **Transition side effects.** On activation, bind the pending assignment reference carried
  into `WAKING`; on release, clear standby marker.
- **Timeout behaviour.** Standby heartbeat interval; on missed liveness the miner
  transitions to `OFFLINE` (T15).
- **Failure behaviour.** Attributable violation → `DISQUALIFIED` (T22); liveness loss →
  `OFFLINE` (T15).

### 2.3 `ACTIVE_HASHING`

- **Exact meaning.** The miner holds a valid current nonce-range assignment (a range lease
  under the committed `TemplateID`) and is actively searching it against the fixed target.
  This is the ONLY hash-rate-bearing state.
- **Allowed computation.** Nonce search over the assigned range under the committed
  template at fixed difficulty (I12); target validation of candidate digests; maintenance
  of the modeled progress-verification abstraction over the covered portion of the range;
  validation of a **received** early-stop certificate while continuing to hash — the miner
  **stays in `ACTIVE_HASHING`** throughout verification and keeps contributing to
  `H_active(t)`, charging the separate `E_verification,i` term; it may leave `ACTIVE_HASHING`
  only after **all** certificate-validation steps pass, and a failed certificate produces
  **no** transition (CR2).
- **Allowed network messages.** Candidate-solution submission, progress commitments,
  verified early-stop participation, lease renewal requests, and heartbeat. All references
  MUST carry the current `RoundID` and `TemplateID` (I3).
- **Residency power term.** `P_hash,i` (accrues `t_hash,i`). Entry from `WAKING` closes the
  wake boundary and charges one-shot `E_transition,i`. Validating a received early-stop
  certificate does not change the residency: the miner keeps drawing `P_hash,i` and the
  incremental verification cost is charged **separately** as `E_verification,i`, not folded
  into `P_hash·t_hash` and not double-counted (CR2).
- **Active-hash-rate contribution.** Yes — the miner's rate is added to `H_active(t)` (and
  to `H_honest(t)` or `H_adversarial(t)` per attribution).
- **May hold/act on a new range.** Yes. It holds its current range and may accept a
  reassignment (self-transition T6) that replaces it with another disjoint range consistent
  with I1 (for example on lease expiry/renewal or a template refresh that preserves the
  miner's active status).
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5). The only record kept at Stage 1 is that a valid solution this miner submits may be recorded as having a solver identity, which by I2/I3 requires an accepted solution inside the signer's valid current assignment matching the current RoundID and TemplateID.
- **Permitted incoming transitions.** From `WAKING` on ramp completion (T5) — whether a
  first activation or a **resume** of a paused (PATH B) assignment from its retained
  `actual_frontier`; self-loop from `ACTIVE_HASHING` on range reassignment (T6).
- **Permitted outgoing transitions.** There are **two completely separate stop paths that
  never merge** (CR-B1):
  - **PATH A — local range exhaustion** (own assigned range fully searched, no valid
    solution found): to `EXHAUSTED_PENDING` on range exhaustion (T7),
    `stop_reason = RANGE_EXHAUSTED`, before dropping to `LOW_POWER_LISTEN` (T8). Only this
    path marks the range `coverage_state = searched`, `custody_status = completed`.
  - **PATH B — verified valid-solution stop** (the miner verifies a valid early-stop
    certificate for the current round): to `LOW_POWER_LISTEN` **directly** (T26),
    `stop_reason = VALID_SOLUTION_VERIFIED`. PATH B **MUST NOT pass through
    `EXHAUSTED_PENDING`**; the assignment is **PAUSED** (its `actual_frontier` retained), not
    searched or exhausted, and **no unsearched positions are credited as searched**.
  - Also to `LOW_POWER_LISTEN` directly on assignment revocation (T27,
    `stop_reason = ASSIGNMENT_REVOKED`; only the unsearched suffix is returned for
    reassignment), on round acceptance (T28, `stop_reason = ROUND_ACCEPTED`), and on round
    abort (T29, `stop_reason = ROUND_ABORTED`); neither round-closure reason marks the range
    exhausted.
  - Self-loop to `ACTIVE_HASHING` (T6, reassignment); to `OFFLINE` (T11); to `DISQUALIFIED`
    (T18).
- **Transition guards.** Range exhaustion (T7, PATH A) requires that the entire assigned
  range has been searched with no valid solution encountered in the actual evaluated
  sequence (honest: `actual_exhaustion = true`; adversarial: accepted reported exhaustion
  under the modeled audit abstraction) — governed by **I4/I8a and the actual-vs-reported
  progress model, not I11**. The verified valid-solution stop (T26, PATH B) requires
  that **all** early-stop-certificate validation steps have passed
  (`STAGE_01_EARLY_STOP_CERTIFICATE.md`, Section 3) while the miner remained in
  `ACTIVE_HASHING`; a failed or partially verified certificate produces **no** transition
  (CR2). Reassignment (T6) requires the new range be disjoint from all other valid active
  assignments (I1) and bound to the current or refreshed `TemplateID`.
- **Transition side effects.** On range exhaustion (T7, PATH A), freeze the final progress
  commitment; on ACCEPTED exhaustion the range is closed (`coverage_state = searched`,
  `custody_status = completed`) and is NOT released or reassigned. On the verified valid-solution stop
  (T26, PATH B), **pause** the assignment: retain its `actual_frontier`, credit no unsearched
  position as searched, and record `stop_reason = VALID_SOLUTION_VERIFIED`; the paused
  assignment may later resume (T30 → T5) if the full block is rejected, unavailable, or times
  out. On revocation (T27), return only the unsearched suffix to the assignable pool. On
  reassignment (T6), atomically release the old lease and bind the new one.
- **Timeout behaviour.** Range lease `lease_expiry` bounds residency on a given range; on
  expiry the range is reclaimed for reassignment (round-level) and the miner either renews
  (T6) or is reassigned; unresponsiveness past the lease/heartbeat bound routes to `OFFLINE`
  (T11).
- **Failure behaviour.** Emitting an unverified early-stop claim, a solution outside the
  assigned range (I2 violation), or a solution bound to a stale `RoundID`/`TemplateID` (I3
  violation) is a protocol violation → `DISQUALIFIED` (T18). Crash or heartbeat loss →
  `OFFLINE` (T11).

### 2.4 `EXHAUSTED_PENDING`

- **Exact meaning.** The miner has completed a search of its **entire** assigned range
  without a valid solution (PATH A — local range exhaustion) and awaits confirmation of that
  exhaustion before it may drop to low-power listening. `EXHAUSTED_PENDING` is reachable
  **ONLY** via range exhaustion from `ACTIVE_HASHING` (T7, `stop_reason = RANGE_EXHAUSTED`);
  it is the antechamber for the **exhaustion path only**. It is **not** a waypoint for the
  verified valid-solution stop (PATH B), for assignment revocation, or for round closure —
  those enter `LOW_POWER_LISTEN` **directly** from `ACTIVE_HASHING` and MUST NOT pass through
  `EXHAUSTED_PENDING` (CR-B1, CR-B2).
- **Allowed computation.** Finalisation of the modeled progress-verification abstraction for
  the completed range; no further nonce search on the exhausted range.
- **Allowed network messages.** Submission/repair of the final progress commitment, receipt
  of an exhaustion-confirmation or revocation, receipt of a reassignment offer, and
  heartbeat. No new solutions on the exhausted range.
- **Residency power term.** `P_hash,i` (short transient awaiting confirmation; **no idle
  saving is credited here**), per the canonical mapping; entry from `ACTIVE_HASHING` charges
  one-shot `E_transition,i`.
- **Active-hash-rate contribution.** None (search on the range has ceased).
- **May hold/act on a new range.** Yes as an offer — a reassignment offer here binds a
  pending range and routes through `WAKING` (T9); it does not resume hashing in place.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From `ACTIVE_HASHING` on range exhaustion (T7,
  `stop_reason = RANGE_EXHAUSTED`) — the ONLY entry.
- **Permitted outgoing transitions.** To `LOW_POWER_LISTEN` on confirmed exhaustion (T8,
  `stop_reason = RANGE_EXHAUSTED`); to `WAKING` on a redeploy offer of an available unsearched suffix (T9); to
  `OFFLINE` (T13); to `DISQUALIFIED` (T19).
- **Transition guards.** T8 requires a **valid exhaustion confirmation** for the assigned
  range (I4); absent that confirmation the drop to `LOW_POWER_LISTEN` is forbidden. On this
  path the range is closed: `coverage_state = searched`, `custody_status = completed`. T9
  requires a disjoint candidate range consistent with I1.
- **Transition side effects.** On T8, confirm/finalise the accepted exhaustion and record it in the audit log (the completed
  range is NOT released or reassigned); on T9, bind the pending reassignment carried into `WAKING`.
- **Timeout behaviour.** A confirmation deadline bounds residency; on expiry without
  confirmation the miner is reassigned (T9) if a range is offered, otherwise it routes to
  `OFFLINE` (T13). It NEVER auto-drops to `LOW_POWER_LISTEN` on timeout — that would violate
  I4.
- **Failure behaviour.** Fabricating exhaustion (a progress/audit violation detected by the modeled audit, not I11) or otherwise
  violating protocol → `DISQUALIFIED` (T19); crash/heartbeat loss → `OFFLINE` (T13).

### 2.5 `LOW_POWER_LISTEN`

- **Exact meaning.** The idle state of the idle policy: the miner monitors round progress at
  reduced power rather than hashing. It is the state that realises reduced active power-time.
  Every entry records exactly one `stop_reason` (amended I4, CR-B2), and the state is reached
  by one of two structurally separate paths (CR-B1): the **exhaustion path** (PATH A) via
  `EXHAUSTED_PENDING`, or a **direct** edge from `ACTIVE_HASHING` (PATH B and the closure/
  revocation reasons).
- **`stop_reason` (mandatory field).** Every occupancy of `LOW_POWER_LISTEN` carries exactly
  one `stop_reason` recorded at entry, drawn from `{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED,
  VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED, ROUND_ABORTED}`. `RANGE_EXHAUSTED` closes the range
  (`coverage_state = searched`, `custody_status = completed`); `VALID_SOLUTION_VERIFIED`
  leaves the assignment **PAUSED** with its `actual_frontier` retained (resumable); the other
  reasons close the assignment without marking the range exhausted.
- **Allowed computation.** Low-rate monitoring of round-progress messages and wake-trigger
  evaluation; no nonce search.
- **Allowed network messages.** Round-progress subscription/monitoring, heartbeat, and
  receipt of a wake request. No solutions, no progress commitments on any range.
- **Residency power term.** `P_listen,i` (accrues `t_listen,i`). Consistent with scope §B.1,
  listening contributes to `P_listen,i * t_listen,i` and NOT to the active hash rate.
- **Active-hash-rate contribution.** None.
- **May hold/act on a new range.** No in place; a wake request binds a pending range and
  routes through `WAKING`.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From `EXHAUSTED_PENDING` on confirmed exhaustion (T8,
  `stop_reason = RANGE_EXHAUSTED`) — the exhaustion path (PATH A); and **directly** from
  `ACTIVE_HASHING` on a verified valid-solution stop (T26, `stop_reason =
  VALID_SOLUTION_VERIFIED`, assignment PAUSED — PATH B), on assignment revocation (T27,
  `stop_reason = ASSIGNMENT_REVOKED`), on round acceptance (T28, `stop_reason =
  ROUND_ACCEPTED`), and on round abort (T29, `stop_reason = ROUND_ABORTED`). Each entry
  records its `stop_reason` (amended I4, CR-B2).
- **Permitted outgoing transitions.** To `WAKING` on wake request for a new assignment (T10);
  to `WAKING` on **resume of a paused (PATH B) assignment** (T30), resuming from the retained
  `actual_frontier`; to `OFFLINE` (T14); to `DISQUALIFIED` (T20).
- **Transition guards.** T10 requires a wake trigger (new-round assignment offer, template
  refresh, or `SECURITY_RECOVERY` activation) and a disjoint candidate range consistent with
  I1. T30 requires that the miner holds a paused assignment (entered via T26,
  `stop_reason = VALID_SOLUTION_VERIFIED`) whose full block was subsequently rejected,
  unavailable, or timed out, so that the retained `actual_frontier` is resumed. There is NO
  guard permitting a direct edge to `ACTIVE_HASHING`; resumption of hashing must pass through
  `WAKING` so that wake energy is charged.
- **Transition side effects.** On T10, bind the pending assignment carried into `WAKING`. On
  T30, carry the retained paused assignment and its `actual_frontier` into `WAKING` so hashing
  resumes from the retained frontier.
- **Timeout behaviour.** Listen interval with a wake deadline; missed heartbeat/liveness →
  `OFFLINE` (T14). Absent a wake trigger the miner remains in `LOW_POWER_LISTEN`.
- **Failure behaviour.** Emitting hashing-only messages while listening, or other protocol
  violation → `DISQUALIFIED` (T20); liveness loss → `OFFLINE` (T14).

### 2.6 `WAKING`

- **Exact meaning.** The spin-up state a miner occupies while ramping from a reduced-power
  or unassigned state back toward active hashing. It carries a bound pending assignment that
  is validated before hashing begins; it incurs wake latency and wake energy.
- **Allowed computation.** Ramp/initialisation of the hashing pipeline and validation of the
  bound pending assignment against the committed `TemplateID` and I1; no scored nonce search
  is counted yet.
- **Allowed network messages.** Wake acknowledgement, assignment (lease) confirmation, and
  heartbeat. No solutions or progress commitments until entry to `ACTIVE_HASHING`.
- **Residency power term.** `P_wake,i` (accrues `t_wake,i`); the entry boundary and the exit
  boundary to `ACTIVE_HASHING` charge one-shot `E_transition,i` per scope §B.3.
- **Active-hash-rate contribution.** None — a waking miner is not yet in `H_active(t)`.
- **May hold/act on a new range.** It holds a **pending** assignment — either a newly bound
  (not yet searched) range or a **resumed paused (PATH B) assignment** carrying its retained
  `actual_frontier`; it acts on it only upon entry to `ACTIVE_HASHING`, and a resumed
  assignment continues from the retained frontier (no unsearched position is credited as
  searched).
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From `REGISTERED` (T3); from `RESERVE` (T4); from
  `EXHAUSTED_PENDING` (T9); from `LOW_POWER_LISTEN` on a new-assignment wake (T10); from
  `LOW_POWER_LISTEN` on **resume of a paused (PATH B) assignment** (T30), carrying the
  retained `actual_frontier`.
- **Permitted outgoing transitions.** To `ACTIVE_HASHING` on ramp completion (T5); to
  `OFFLINE` (T12); to `DISQUALIFIED` (T21).
- **Transition guards.** T5 requires ramp completion AND validation that the bound pending
  assignment is disjoint from all other valid active assignments (I1) and bound to the
  current `TemplateID`.
- **Transition side effects.** On T5, activate the range lease and begin `t_hash,i`
  accrual (a resumed paused assignment continues from its retained `actual_frontier`); close
  the wake boundary with `E_transition,i`.
- **Timeout behaviour.** A wake deadline bounds residency; if ramp does not complete or the
  pending assignment fails validation within the deadline, the miner routes to `OFFLINE`
  (T12) and its bound range is released for round-level reassignment.
- **Failure behaviour.** Validation failure of the bound assignment (e.g. overlap with an
  existing active assignment, I1) aborts the wake to `OFFLINE` (T12); attributable protocol
  violation → `DISQUALIFIED` (T21).

### 2.7 `OFFLINE`

- **Exact meaning.** The miner is not participating: powered down, disconnected, or having
  lost liveness. It holds no active range and emits nothing but (optionally) a rejoin
  attempt. It is a non-terminal absence state — the miner may rejoin — as distinct from the
  terminal `DISQUALIFIED`.
- **Allowed computation.** None counted by the protocol (out of the modeled participation).
- **Allowed network messages.** Only a rejoin/registration attempt. No solutions, progress
  commitments, assignments, or early-stop messages.
- **Residency power term.** `P_offline,i` (accrues `t_offline,i`).
- **Active-hash-rate contribution.** None.
- **May hold/act on a new range.** No.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From any active/standby state — `ACTIVE_HASHING`
  (T11), `WAKING` (T12), `EXHAUSTED_PENDING` (T13), `LOW_POWER_LISTEN` (T14), `RESERVE`
  (T15), `REGISTERED` (T16).
- **Permitted outgoing transitions.** To `REGISTERED` on rejoin (T17); to `DISQUALIFIED` on
  an attributable violation discovered while offline (T24).
- **Transition guards.** Rejoin (T17) requires a valid re-registration within the rejoin
  window and that the `MinerID` is not already `DISQUALIFIED`.
- **Transition side effects.** On entry, release any held range lease for round-level
  reclamation and stop all active-term accrual; on rejoin, re-establish the `MinerID`
  record.
- **Timeout behaviour.** A rejoin/grace window bounds how long the miner is retained;
  beyond it the miner remains `OFFLINE` (pruned from active scheduling) unless an
  attributable violation forces `DISQUALIFIED` (T24).
- **Failure behaviour.** Discovery of an attributable prior violation (e.g. equivocation)
  routes to `DISQUALIFIED` (T24).

### 2.8 `DISQUALIFIED`

- **Exact meaning.** Terminal removal of the `MinerID` from participation following a
  protocol violation (for example: a solution outside the signer's assignment (I2), a
  stale-round/template solution (I3), an overlapping-assignment attempt (I1), or an
  unverified early-stop (I11)). It is absorbing.
- **Allowed computation.** None.
- **Allowed network messages.** None accepted from a disqualified `MinerID`.
- **Residency power term.** `P_offline,i` (no active draw); any coordination to record
  disqualification is a one-shot `E_coordination,i`.
- **Active-hash-rate contribution.** None; any prior contribution ceases at entry.
- **May hold/act on a new range.** No.
- **Reward eligibility.** NOT SPECIFIED AT STAGE 1 (incentive semantics deferred to Stage 5).
- **Permitted incoming transitions.** From every non-terminal state on protocol violation —
  `ACTIVE_HASHING` (T18), `EXHAUSTED_PENDING` (T19), `LOW_POWER_LISTEN` (T20), `WAKING`
  (T21), `RESERVE` (T22), `REGISTERED` (T23), `OFFLINE` (T24).
- **Permitted outgoing transitions.** None (terminal/absorbing).
- **Transition guards.** Entry requires a recorded violation attributable to the `MinerID`.
- **Transition side effects.** Release any held range lease; void pending credit; append the
  violation to the invariant audit log; remove the `MinerID` from all scheduling sets.
- **Timeout behaviour.** None (absorbing).
- **Failure behaviour.** Not applicable — the state is the terminal result of failure.

---

## 3. Transition table

The table below enumerates **every legal transition** among the eight miner states. No
transition is described informally: each row carries a guard and an action. Columns:
`current_state | event | guard | action | next_state | energy_accounting_effect |
security_accounting_effect | failure_result`.

Notation: `∅` = pre-registration external origin; `E_transition` / `E_coordination` /
`E_verification` refer to the event-energy terms of the energy model (`E_verification` is
charged **in-state** while a miner validates a received early-stop certificate — it is **not**
a transition and does **not** remove the miner from `H_active(t)`, per CR2); "census +rate" /
"census −rate" refer to the miner's contribution to `H_active(t)`.

Every transition whose `next_state` is `LOW_POWER_LISTEN` records exactly one `stop_reason`
from `{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, VALID_SOLUTION_VERIFIED, ROUND_ACCEPTED,
ROUND_ABORTED}` in its action (amended I4, CR-B2). The two stop paths of CR-B1 never merge:
PATH A reaches `LOW_POWER_LISTEN` only through `EXHAUSTED_PENDING` (T7 → T8), while PATH B (the
verified valid-solution stop, assignment PAUSED) and the revocation/closure reasons reach it
**directly** from `ACTIVE_HASHING` (T26–T29).

| ID | current_state | event | guard | action | next_state | energy_accounting_effect | security_accounting_effect | failure_result |
|----|---------------|-------|-------|--------|------------|--------------------------|----------------------------|----------------|
| T1 | `∅` (external) | RegisterRequest | Valid registration payload; `MinerID` not already `DISQUALIFIED` | Create `MinerID` record; admit to participation | `REGISTERED` | Begin `P_registered` (= `P_listen`) residency; `E_coordination` for registration handshake | No change to `H_active(t)` census | Malformed/duplicate registration rejected; origin stays external (no state created) |
| T2 | `REGISTERED` | AdmitToReserve | Reserve-pool capacity available | Mark standby; enroll in reserve pool | `RESERVE` | Switch residency `P_registered → P_reserve` (both = `P_listen`); `E_coordination` | No census change | If pool full, guard fails; miner remains `REGISTERED` |
| T3 | `REGISTERED` | AssignmentOffer (WakeForAssignment) | Committed `TemplateID` exists; offered range disjoint per I1 | Bind pending assignment; begin spin-up | `WAKING` | Switch residency `P_registered → P_wake`; entry `E_transition` | No census change (not yet hashing) | Overlapping/invalid range (I1): offer rejected, miner remains `REGISTERED` |
| T4 | `RESERVE` | ReserveActivation | Round activation event (typically from `SECURITY_RECOVERY`); offered range disjoint per I1 | Bind pending assignment; begin spin-up | `WAKING` | Switch residency `P_reserve → P_wake`; entry `E_transition` | No census change yet; activation is toward raising `H_active(t)` | Invalid range (I1) or no activation event: guard fails, miner remains `RESERVE` |
| T5 | `WAKING` | RampComplete | Ramp complete AND bound assignment validated disjoint per I1 and bound to current `TemplateID` | Activate range lease; start `t_hash` accrual (a **resumed** paused PATH-B assignment continues from its retained `actual_frontier`) | `ACTIVE_HASHING` | End `P_wake`; exit `E_transition`; begin `P_hash` residency | Census +rate: add miner rate to `H_active(t)` (and `H_honest(t)`/`H_adversarial(t)` by attribution) | Validation failure → wake abort to `OFFLINE` (T12); range released |
| T6 | `ACTIVE_HASHING` | RangeReassignment | New range disjoint from all valid active assignments (I1); bound to current or refreshed `TemplateID` (I3); difficulty unchanged (I12) | Atomically release old lease; bind new lease | `ACTIVE_HASHING` | Continue `P_hash`; one-shot `E_coordination` for reassignment; no wake term | Census unchanged in magnitude; audit log records lease change | Overlap (I1) or stale template (I3): reassignment rejected; miner keeps current range |
| T7 | `ACTIVE_HASHING` | RangeExhausted (PATH A) | Entire assigned range searched with no valid solution encountered in the actual evaluated sequence (honest: `actual_frontier = range_end`, `actual_positions_evaluated = range_size`, `actual_exhaustion = true`; adversarial: accepted reported exhaustion under the modeled audit abstraction); governed by I4/I8a and the actual-vs-reported progress model, not I11 | Freeze final progress commitment; on ACCEPTED exhaustion mark `coverage_state = searched`, `custody_status = completed`; `stop_reason = RANGE_EXHAUSTED`; do NOT release or reassign the completed range | `EXHAUSTED_PENDING` | Continue `P_hash` residency (short `EXHAUSTED_PENDING` transient; no idle saving credited); entry `E_transition` | Census −rate: remove miner rate from `H_active(t)` | Fabricated/false exhaustion detected by the modeled audit (adversarial path) → exhaustion NOT recorded, range not closed; attributable violation → `DISQUALIFIED` (T18) |
| T8 | `EXHAUSTED_PENDING` | ExhaustionConfirmed (PATH A) | Valid exhaustion confirmation for the range (I4) | Confirm/finalise the accepted exhaustion (coverage_state/custody already set at T7); record confirmed exhaustion and `stop_reason = RANGE_EXHAUSTED` in audit log; do NOT release or reassign the completed range | `LOW_POWER_LISTEN` | End `P_hash` transient; begin `P_listen` residency; one-shot `E_coordination` | No census change (already removed at T7) | No confirmation before deadline → reassign (T9) or `OFFLINE` (T13); NEVER auto-drop here (I4) |
| T9 | `EXHAUSTED_PENDING` | RedeployOffer | An **unsearched suffix** became available for a permitted reassignment reason ({lease_expiry, abandonment, revocation, departure, conflict, security_recovery}) and is offered to this available miner, disjoint per I1, on the committed `TemplateID`; the miner's own completed range stays `custody_status = completed` and is NOT reassigned (exhaustion is never a reassignment reason) | Bind the offered unsearched suffix as a new assignment; begin spin-up | `WAKING` | Switch residency `P_hash → P_wake`; entry `E_transition` | No census change yet (toward re-raising `H_active(t)`) | Invalid range (I1): offer rejected; miner remains `EXHAUSTED_PENDING` |
| T10 | `LOW_POWER_LISTEN` | WakeRequest | Wake trigger (new-round assignment, template refresh, or `SECURITY_RECOVERY`); offered range disjoint per I1 | Bind pending assignment; begin spin-up | `WAKING` | Switch residency `P_listen → P_wake`; entry `E_transition` | No census change yet; wake is toward raising `H_active(t)` | Invalid range (I1) or absent trigger: guard fails; miner remains `LOW_POWER_LISTEN` |
| T11 | `ACTIVE_HASHING` | Departure / HeartbeatLoss / lease-timeout unresponsive | Liveness lost past heartbeat/`lease_expiry` bound, or voluntary shutdown | Release range lease for reclamation; stop `t_hash` accrual | `OFFLINE` | End `P_hash`; begin `P_offline` residency | Census −rate: remove miner rate from `H_active(t)` | If departure is attributable to a violation instead, route to `DISQUALIFIED` (T18) |
| T12 | `WAKING` | Departure / WakeDeadlineExpiry / ValidationAbort | Ramp not completed or bound assignment fails I1/`TemplateID` validation within wake deadline, or liveness lost | Release bound range; stop wake accrual | `OFFLINE` | End `P_wake`; begin `P_offline` residency | No census change (never entered `H_active(t)`) | Attributable violation instead → `DISQUALIFIED` (T21) |
| T13 | `EXHAUSTED_PENDING` | Departure / HeartbeatLoss / ConfirmDeadlineExpiry | Liveness lost, or confirmation deadline expired with no reassignment offer | Release range; stop accrual | `OFFLINE` | End `P_hash` transient; begin `P_offline` residency | No census change (already removed at T7) | Attributable violation instead → `DISQUALIFIED` (T19) |
| T14 | `LOW_POWER_LISTEN` | Departure / HeartbeatLoss | Liveness/heartbeat lost past bound | Stop listen accrual | `OFFLINE` | End `P_listen`; begin `P_offline` residency | No census change | Attributable violation instead → `DISQUALIFIED` (T20) |
| T15 | `RESERVE` | Departure / LivenessLoss | Standby liveness lost past bound | Remove from reserve pool | `OFFLINE` | End `P_reserve` (= `P_listen`); begin `P_offline` residency | No census change | Attributable violation instead → `DISQUALIFIED` (T22) |
| T16 | `REGISTERED` | Departure / RegistrationTTLExpiry | Idle TTL expired without admission/offer, or liveness lost | Stop accrual | `OFFLINE` | End `P_registered` (= `P_listen`); begin `P_offline` residency | No census change | Attributable violation instead → `DISQUALIFIED` (T23) |
| T17 | `OFFLINE` | Rejoin | Valid re-registration within rejoin window; `MinerID` not `DISQUALIFIED` | Re-establish `MinerID` record | `REGISTERED` | End `P_offline` absence; begin `P_registered` (= `P_listen`) residency; `E_coordination` | No census change | Rejoin window expired or `MinerID` disqualified: guard fails; miner remains `OFFLINE` |
| T18 | `ACTIVE_HASHING` | ProtocolViolation | Recorded violation attributable to `MinerID` (e.g. solution outside assignment I2, stale round/template I3, unverified early-stop I11) | Release lease; void pending credit; append to audit log; remove from scheduling | `DISQUALIFIED` | End `P_hash`; `E_coordination` to record; begin `P_offline` (terminal) | Census −rate: remove miner rate from `H_active(t)`; violation logged against `q_adv(t)` accounting | Terminal — no recovery |
| T19 | `EXHAUSTED_PENDING` | ProtocolViolation | Recorded attributable violation (e.g. fabricated exhaustion detected by the modeled audit — a progress/audit-model finding, not I11) | Release range; void credit; append to audit log; remove from scheduling | `DISQUALIFIED` | End `P_hash` transient; `E_coordination`; begin `P_offline` (terminal) | No census change (already removed at T7); violation logged | Terminal — no recovery |
| T20 | `LOW_POWER_LISTEN` | ProtocolViolation | Recorded attributable violation (e.g. hashing-only message while listening) | Void credit; append to audit log; remove from scheduling | `DISQUALIFIED` | End `P_listen`; `E_coordination`; begin `P_offline` (terminal) | No census change; violation logged | Terminal — no recovery |
| T21 | `WAKING` | ProtocolViolation | Recorded attributable violation | Release bound range; void credit; append to audit log | `DISQUALIFIED` | End `P_wake`; `E_coordination`; begin `P_offline` (terminal) | No census change; violation logged | Terminal — no recovery |
| T22 | `RESERVE` | ProtocolViolation | Recorded attributable violation | Remove from reserve pool; append to audit log | `DISQUALIFIED` | End `P_reserve` (= `P_listen`); `E_coordination`; begin `P_offline` (terminal) | No census change; violation logged | Terminal — no recovery |
| T23 | `REGISTERED` | ProtocolViolation | Recorded attributable violation | Append to audit log; remove from scheduling | `DISQUALIFIED` | End `P_registered` (= `P_listen`); `E_coordination`; begin `P_offline` (terminal) | No census change; violation logged | Terminal — no recovery |
| T24 | `OFFLINE` | ViolationDiscovered | Attributable prior violation discovered while offline (e.g. equivocation) | Append to audit log; permanently bar `MinerID` | `DISQUALIFIED` | Continue `P_offline` (terminal); `E_coordination` to record | No census change; violation logged | Terminal — no recovery |
| T25 | `RESERVE` | ReserveRelease | Administrative demotion; no active assignment held | Clear standby marker; return to neutral admitted pool | `REGISTERED` | Switch residency `P_reserve → P_registered` (both = `P_listen`); `E_coordination` | No census change | If a pending activation exists, release is deferred; miner remains `RESERVE` |
| T26 | `ACTIVE_HASHING` | ValidSolutionVerified (PATH B) | **All** early-stop-certificate validation steps passed (`STAGE_01_EARLY_STOP_CERTIFICATE.md` §3) while the miner stayed in `ACTIVE_HASHING` (CR2); direct, NOT via `EXHAUSTED_PENDING` | **Pause** the assignment: retain `actual_frontier`, credit no unsearched position as searched; record `stop_reason = VALID_SOLUTION_VERIFIED` | `LOW_POWER_LISTEN` | End `P_hash`; begin `P_listen` residency; one-shot `E_transition` | Census −rate: remove miner rate from `H_active(t)` | Failed/partial certificate → NO transition, miner stays `ACTIVE_HASHING` (CR2); attributable violation → `DISQUALIFIED` (T18) |
| T27 | `ACTIVE_HASHING` | AssignmentRevoked | Valid protocol revocation of the assignment (CR-B1); direct, NOT via `EXHAUSTED_PENDING` | Return only the unsearched suffix to the assignable pool; record `stop_reason = ASSIGNMENT_REVOKED` | `LOW_POWER_LISTEN` | End `P_hash`; begin `P_listen` residency; one-shot `E_coordination` | Census −rate: remove miner rate from `H_active(t)` | Attributable violation → `DISQUALIFIED` (T18) |
| T28 | `ACTIVE_HASHING` | RoundAccepted | The round closed on an accepted block (round-level `ROUND_ACCEPTED`); the assignment closes because the **round ended**, NOT because the range was exhausted (CR-B1) | Close the assignment as round-ended (range NOT marked exhausted/searched); record `stop_reason = ROUND_ACCEPTED` | `LOW_POWER_LISTEN` | End `P_hash`; begin `P_listen` residency; one-shot `E_coordination` | Census −rate: remove miner rate from `H_active(t)` | — |
| T29 | `ACTIVE_HASHING` | RoundAborted | The round closed by `ROUND_ABORTED`; the assignment closes because the round ended, NOT because the range was exhausted (CR-B1) | Close the assignment as round-ended (range NOT marked exhausted/searched); record `stop_reason = ROUND_ABORTED` | `LOW_POWER_LISTEN` | End `P_hash`; begin `P_listen` residency; one-shot `E_coordination` | Census −rate: remove miner rate from `H_active(t)` | — |
| T30 | `LOW_POWER_LISTEN` | ResumePausedAssignment | Miner holds a paused (PATH B, `VALID_SOLUTION_VERIFIED`) assignment whose full block was rejected, unavailable, or timed out; retained `actual_frontier` available | Carry the retained paused assignment and its `actual_frontier` into spin-up | `WAKING` | Switch residency `P_listen → P_wake`; entry `E_transition` | No census change yet; resume is toward re-raising `H_active(t)` | Absent a paused assignment or resume trigger, guard fails; miner remains `LOW_POWER_LISTEN` |

### 3.1 Explicitly prohibited (illegal) transitions

The following are NOT legal and MUST be rejected; they are listed to make the invariant
enforcement explicit:

- **Any edge into `LOW_POWER_LISTEN` without a recorded `stop_reason`, or from a state other
  than `EXHAUSTED_PENDING` (T8) or `ACTIVE_HASHING` (T26–T29).** In particular `WAKING →
  LOW_POWER_LISTEN`, `RESERVE → LOW_POWER_LISTEN`, and `REGISTERED → LOW_POWER_LISTEN` are
  prohibited. The legal entries are exactly: T8 (`RANGE_EXHAUSTED`, PATH A, via
  `EXHAUSTED_PENDING`) and the **direct** edges from `ACTIVE_HASHING` — T26
  (`VALID_SOLUTION_VERIFIED`, PATH B, assignment PAUSED), T27 (`ASSIGNMENT_REVOKED`), T28
  (`ROUND_ACCEPTED`), T29 (`ROUND_ABORTED`). Each records exactly one `stop_reason` (amended
  I4, CR-B2).
- **Any PATH B (verified valid-solution) stop routed through `EXHAUSTED_PENDING`.** The two
  paths of CR-B1 never merge: a verified valid-solution stop enters `LOW_POWER_LISTEN`
  **directly** (T26) with the assignment PAUSED; it MUST NOT be modeled as exhaustion and
  MUST NOT mark the range `searched`/`completed`. `EXHAUSTED_PENDING` is reachable ONLY via
  `RANGE_EXHAUSTED` (T7, PATH A).
- **Any direct `LOW_POWER_LISTEN → ACTIVE_HASHING` or `RESERVE → ACTIVE_HASHING`.**
  Resumption of hashing MUST pass through `WAKING` so that wake energy `P_wake,i * t_wake,i`
  and `E_transition,i` are charged; skipping the wake state would misstate the energy model.
- **Any `ACTIVE_HASHING → EXHAUSTED_PENDING` without ACCEPTED exhaustion adjudication.**
  Entering `EXHAUSTED_PENDING` is a PATH-A range-exhaustion transition governed by **I4, I8a,
  and ExhaustionAdjudicate** (accepted coverage), never by an early-stop certificate or I11. A
  fabricated exhaustion claim is a progress/audit violation (detected by the modeled audit)
  routing to `DISQUALIFIED` (T19); it is not an I11 matter.
- **Any outgoing edge from `DISQUALIFIED`.** The state is absorbing.
- **Concurrent occupancy of two states.** The eight states are mutually exclusive; no
  transition may leave a miner in more than one.

### 3.2 Invariant enforcement summary

- **I1** (no two valid active assignments overlap) is checked at every range-binding guard:
  T3, T4, T6, T9, T10, and the T5 validation.
- **I2** (accepted solution ∈ signer's valid current assignment) and **I3** (accepted
  solution matches current `RoundID`+`TemplateID`) gate reward eligibility, which only
  `ACTIVE_HASHING` can satisfy; their violation routes to `DISQUALIFIED` (T18).
- **I4 (amended, CR-B2)** — a miner may enter `LOW_POWER_LISTEN` only after one of: accepted
  range-exhaustion accounting via `EXHAUSTED_PENDING` (T8, `RANGE_EXHAUSTED`); explicit
  assignment revocation (T27, `ASSIGNMENT_REVOKED`); a fully verified valid-solution
  early-stop certificate (T26, `VALID_SOLUTION_VERIFIED`, assignment PAUSED); or round closure
  (T28 `ROUND_ACCEPTED` / T29 `ROUND_ABORTED`). Every entry records exactly one `stop_reason`,
  no unverified certificate may cause the transition, and `EXHAUSTED_PENDING` remains
  exclusive to the range-exhaustion path (PATH A). Timeout-driven drops from
  `EXHAUSTED_PENDING` remain forbidden.
- **I5** (durations ≥ 0, reconcile to horizon) governs the residency-term accrual declared
  per state; every transition begins/ends exactly one residency term.
- **I11** (false early-stop cannot end hashing without target verification) gates T7 and
  makes an unverified early-stop a disqualifying violation.
- **I12** (difficulty constant) is preserved by every guard: no transition alters
  difficulty.

No security, fairness, or incentive property is claimed by any part of this state machine;
the accounting effects above are modeled quantities only (scope §C).
