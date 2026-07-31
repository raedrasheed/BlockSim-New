# Stage 1 — PoCol Round State Machine

**Document status:** Stage-1 specification-only. This document DEFINES the round-level state
machine of **PoCol** with the idle policy enabled. It does NOT claim that any state,
transition, guard, or effect described here is implemented, validated, secure, fair, or
incentive-compatible. Stage 1 SPECIFIES structure; it demonstrates no property.

**Naming rule (binding).** The algorithm is ALWAYS **PoCol**. The low-power mechanism is
**the idle policy within PoCol** — an operating policy INSIDE PoCol, not a new algorithm,
variant, or fork. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are
prohibited.

**Cross-references.** Protocol scope and the accepted baseline (A1) are fixed in
`STAGE_01_PROTOCOL_SCOPE.md`. Per-miner states are specified in
`STAGE_01_MINER_STATE_MACHINE.md`. Symbols and terms are defined in
`STAGE_01_TERMINOLOGY.md`. Invariants are referenced by ID from the separate Invariant
Catalogue.

---

## 1. Miner-state vs round-state separation (binding)

**The round state machine and the miner state machine are two distinct transition systems.**
They MUST NOT be conflated:

- A **round state** is a **global** property of one consensus round, identified by its
  `RoundID` and the committed `TemplateID`. It describes what the round as a whole is doing.
  The ten round states are `ROUND_INITIALISING`, `TEMPLATE_COMMITMENT`, `ASSIGNMENT`,
  `HASHING`, `SECURITY_RECOVERY`, `SOLUTION_PROPAGATION`, `ROUND_ACCEPTED`,
  `ROUND_EXHAUSTED`, `TEMPLATE_REFRESH`, `ROUND_ABORTED`.
- A **miner state** is a **local** property of one participant, identified by its `MinerID`.
  The eight miner states are `REGISTERED`, `RESERVE`, `ACTIVE_HASHING`, `EXHAUSTED_PENDING`,
  `LOW_POWER_LISTEN`, `WAKING`, `OFFLINE`, `DISQUALIFIED`
  (`STAGE_01_MINER_STATE_MACHINE.md`).

The two systems evolve on **separate transition relations** and are **coupled only through
events**. A round-level entry (for example, into `ASSIGNMENT`) emits assignment offers that
individual miners consume, producing local miner transitions (for example `REGISTERED →
WAKING`). Conversely, aggregated miner-level facts (for example, all active ranges reported
exhausted) are events that drive round transitions (for example `HASHING → ROUND_EXHAUSTED`).

Consequences that MUST hold:

1. The round being in `HASHING` does **not** place, or require, any particular miner in
   `ACTIVE_HASHING`. Miners in that round may simultaneously be in `LOW_POWER_LISTEN`,
   `RESERVE`, `WAKING`, `OFFLINE`, etc.
2. A single miner transition never, by itself, moves the round state; round transitions
   are driven by round-level guards over aggregated conditions (for example the
   security-floor check, or the "all active ranges exhausted" predicate).
3. Terminal miner states (`DISQUALIFIED`) and absence states (`OFFLINE`) are miner-scoped
   and do not terminate the round; the round has its own terminal/return states
   (`ROUND_ACCEPTED`, `ROUND_ABORTED`).
4. Only miners in `ACTIVE_HASHING` contribute to `H_active(t)`; the round-state census of
   active hash rate is therefore an aggregate over miner states, never a restatement of the
   round state.

---

## 2. Per-state specification (meaning, entry, exit)

Difficulty is **FIXED** across all round states in the confirmatory design (invariant
**I12**); no round transition changes it. All energy quantities referenced are the modeled
quantities of `STAGE_01_PROTOCOL_SCOPE.md` §0.3.

### 2.1 `ROUND_INITIALISING`

- **Meaning.** The round is being set up: a fresh `RoundID` is established, the participant
  census (active, reserve, offline) is gathered, and the modeled active-hash-rate baseline
  `H_active(t)` and security floor are prepared. No template is committed yet.
- **Entry condition.** Genesis, or the immediately preceding round reached `ROUND_ACCEPTED`
  or `ROUND_ABORTED` and control returns to start a new round.
- **Exit condition(s).** To `TEMPLATE_COMMITMENT` once the round parameters and the
  template-proposal context are established.

### 2.2 `TEMPLATE_COMMITMENT`

- **Meaning.** The single common immutable block template for the round is committed and
  assigned a stable `TemplateID` (scope §A.1–A.2). Once committed, template content does not
  change except through `TEMPLATE_REFRESH`. Difficulty is fixed (I12).
- **Entry condition.** From `ROUND_INITIALISING` with round parameters established; or from
  `TEMPLATE_REFRESH` carrying a new template to commit.
- **Exit condition(s).** To `ASSIGNMENT` once the template is committed and its `TemplateID`
  published.

### 2.3 `ASSIGNMENT`

- **Meaning.** The nonce domain is partitioned into disjoint ranges and distributed as
  range leases to eligible miners under the committed `TemplateID`. Partitioning organises
  the search; per A1 it does NOT by itself reduce fixed-horizon energy.
- **Entry condition.** From `TEMPLATE_COMMITMENT` with a committed `TemplateID`; or from
  `TEMPLATE_REFRESH`/`SECURITY_RECOVERY` when ranges must be (re)distributed.
- **Exit condition(s).** To `HASHING` once every intended active assignment is distributed
  and the assignment set is valid (pairwise disjoint per I1, all bound to the current
  `RoundID`+`TemplateID` per I3).

### 2.4 `HASHING`

- **Meaning.** Assigned miners search their leased ranges against the fixed target under the
  committed template. This is the round state during which miner-level `ACTIVE_HASHING`
  residency accrues and `H_active(t)` is populated.
- **Entry condition.** From `ASSIGNMENT` with a valid assignment set; or a return from
  `SECURITY_RECOVERY` (recovery succeeded) or `SOLUTION_PROPAGATION` (candidate rejected/
  withheld) that resumes searching.
- **Exit condition(s).** To `SOLUTION_PROPAGATION` on a candidate solution meeting target;
  to `ROUND_EXHAUSTED` when every active range is exhausted; to `SECURITY_RECOVERY` on a
  security-floor violation; to `TEMPLATE_REFRESH` on a refresh trigger; to `ROUND_ABORTED`
  on an unrecoverable fault.

### 2.5 `SECURITY_RECOVERY`

- **Meaning.** A remediation state entered when security-floor monitoring reports that
  modeled active honest hash rate has fallen below the floor (for example after
  participation reduction or miner departures). Reserve miners are activated to restore
  coverage: this emits activation events that drive `RESERVE → WAKING` (and
  `LOW_POWER_LISTEN → WAKING`) at the miner level. Monitoring is specified; enforcement
  soundness is out of scope (scope §C).
- **Entry condition.** From `HASHING` **or `SOLUTION_PROPAGATION`** when the scheduled, terminal-guarded
  `SecurityFloorEvaluate` reports a breach (`H_honest(t)` below the modeled floor, or an invariant-risk
  condition). It is never entered from a terminal round (G10).
- **Coexistence with live candidates (G8).** `SECURITY_RECOVERY` MAY coexist with a non-empty
  `active_propagation_set`. Entering it does NOT cancel live candidate contexts; block arrivals and
  `AcceptanceBatchFinalize` remain processable during recovery, and a valid accepted candidate MAY
  close a recovery-state round (`SECURITY_RECOVERY → ROUND_ACCEPTED`, R6). The round-state and the
  propagation set are not identified.
- **Exit condition(s).** Back to `HASHING` (via re-`ASSIGNMENT` of activated reserves) when the floor
  is restored **and `propagation_quiescent` holds**; back to `SOLUTION_PROPAGATION` when the floor is
  restored while live candidates remain (G8); to `ROUND_ACCEPTED` if a valid candidate is accepted
  during recovery (G8); to `ROUND_ABORTED` if the floor cannot be restored.

### 2.6 `SOLUTION_PROPAGATION`

- **Meaning.** A candidate solution meeting target is propagated and validated: it is
  checked to bind to the assignment version eligible at its discovery_time (I2, discovery-time per G1) and to match the current
  `RoundID`+`TemplateID` (I3), using target validation as the acceptance predicate
  (scope §A.5).
- **Entry timing (E6).** The round enters `SOLUTION_PROPAGATION` at the **first valid
  found-solution event** — i.e. at propagation START (`HASHING → SOLUTION_PROPAGATION`, R5),
  **NOT** after block acceptance. There is exactly one canonical model for the entry:
  1. the round enters `SOLUTION_PROPAGATION` when the first candidate solution satisfying the
     fixed target is found (`ScheduleSolutionPropagation` performs `HASHING →
     SOLUTION_PROPAGATION`);
  2. while the round is in `SOLUTION_PROPAGATION`, miners that have **not yet verified** a
     certificate **continue hashing** (they remain in `ACTIVE_HASHING` and in `H_active(t)`),
     and event-scheduled hashing (`HashWorkEvent`, G9) is permitted in `{HASHING,
     SOLUTION_PROPAGATION, SECURITY_RECOVERY}`;
  3. **further candidate solutions may still be found and scheduled** during
     `SOLUTION_PROPAGATION`; each gets its OWN `CandidatePropagationContext` and joins the
     `active_propagation_set` (F1/F3);
  4. a rejected/unavailable/timed-out full block, or an empty valid acceptance batch, fails ONLY
     that candidate (candidate-scoped `HandlePropagationFailure`, F2); the round returns
     `SOLUTION_PROPAGATION → HASHING` (R7) **only when `active_propagation_set` becomes empty and
     no acceptance batch / candidate acceptance event remains** (`propagation_quiescent`, F3), or
     `SOLUTION_PROPAGATION → SECURITY_RECOVERY` (R8) on a coincident floor breach (which PRESERVES
     the remaining live contexts);
  5. accepted same-timestamp arbitration transitions `SOLUTION_PROPAGATION → ROUND_ACCEPTED`
     (R6) in a **single** step (the round is already in `SOLUTION_PROPAGATION`); acceptance of one
     candidate marks every OTHER live candidate `COMPETING`/`STALE`/`CANCELLED`, cancels their
     remaining events, and closes the round **exactly once** (F3).
- **Active propagation set (F3, refined G6; NOT identified with the round-state, G8/H1).**
  `active_propagation_set` holds EXACTLY the propagation-active contexts — those with
  `status ∈ {PROPAGATING, PENDING_ACCEPTANCE}` (G6). `DISCOVERED` and `SELF_VALIDATED` contexts
  exist but are NOT yet in the set; `FAILED`/`ACCEPTED`/`COMPETING`/`STALE`/`CANCELLED` contexts
  have LEFT it. It is therefore NOT "every live context". **There is NO `iff` tying the round-state
  to the set (H1):** a non-empty set does not force `SOLUTION_PROPAGATION` (the same live candidates
  are preserved while the round is in `SECURITY_RECOVERY`, G8), and the round leaves
  `SOLUTION_PROPAGATION` only when `propagation_quiescent` holds (set empty AND no pending
  acceptance batch AND no live candidate acceptance event AND `block_accepted` false). Failure of
  one candidate removes ONLY that candidate; the round stays `SOLUTION_PROPAGATION` while any other
  candidate is propagation-active. One candidate's failure never cancels another candidate's
  certificate-arrival, block-arrival, acceptance-batch, or timeout events, and never resumes a miner
  paused by a different live candidate (F2).
- **Same-timestamp event order (authoritative: `STAGE_01G_EVENT_MICROPHASE_SPEC.md`, extended by the
  H2 delta-cycle rule).** When events share an `event_time`, they fire in the explicit microphase
  order (terminal closure → template refresh → collect block arrivals → `AcceptanceBatchFinalize` →
  the single settled-census `FinalizeTimestampSecurityCensus` → certificate/discovery/…), with a
  same-`event_time` event created inside a handler placed in the current or next `delta_cycle` per
  §0.7-H2 (never backward into a completed microphase), and intra-microphase ties broken by
  `(CandidateID, MinerID, AssignmentID, seq)` — never by iteration order. The frozen Stage-1F
  `STAGE_01F_EVENT_PRIORITY_TABLE.md` is **NOT** authoritative (superseded by the microphase model,
  G5/H1). This makes the round-state evolution reproducible across reruns.
- **Miner-state note (CR2).** While a round is in `SOLUTION_PROPAGATION`, certificate
  verification does **not** remove verifying miners from `ACTIVE_HASHING` or from `H_active(t)`:
  each miner remains in `ACTIVE_HASHING` and continues hashing until it has itself completed all
  certificate-validation steps (`STAGE_01_EARLY_STOP_CERTIFICATE.md`, Section 3), with
  verification energy recorded separately as `E_verification`. No `VERIFYING` miner state exists,
  and a failed certificate produces no hashing-state transition.
- **Network-arrival and early-stop ordering (CR-B9, C6).** Early stop and block acceptance
  within `SOLUTION_PROPAGATION` are **event-scheduled** on the discrete-event queue; block
  acceptance NEVER occurs at solution-discovery time. The ordering is:
  1. A candidate solution is found; `ROUND_ACCEPTED` is **NOT** set at this point.
  2. An early-stop certificate is constructed, and its per-recipient certificate-arrival events
     are scheduled with modeled propagation delays; full-block propagation/arrival events are
     likewise scheduled with modeled per-recipient delays.
  3. Each recipient continues hashing (remains in `ACTIVE_HASHING`) until its certificate-arrival
     event fully validates.
  4. After successful validation, that recipient enters `LOW_POWER_LISTEN` with
     `stop_reason = VALID_SOLUTION_VERIFIED`, its assignment **PAUSED** (retained
     `actual_frontier`) — miner-level PATH B (`STAGE_01_MINER_STATE_MACHINE.md`, T26),
     **directly** and never via `EXHAUSTED_PENDING`.
  5. Full-block propagation/validation continues on the event queue; block acceptance occurs
     **only at the modeled acceptance point** — a designated coordinator/validator, or a clearly
     identified canonical local view — after the full block arrives and validates.
  6. If the full block is accepted at that acceptance point, the round closes
     (`SOLUTION_PROPAGATION → ROUND_ACCEPTED`); remaining assignments close because the **round
     ended** (`stop_reason = ROUND_ACCEPTED`), not because their ranges were exhausted.
  7. If the full block is rejected or times out, stopped miners wake and resume their paused
     assignments (`LOW_POWER_LISTEN → WAKING → ACTIVE_HASHING`, T30 → T5) from the retained
     `actual_frontier`, with wake and transition energy accounted.

  The **discrete-event queue itself establishes earliest arrival**; only exactly-equal
  acceptance timestamps break deterministically by `candidate_hash` then `MinerID`, and
  competing proposals become stale/competing records.

  **No recipient is labeled `EXHAUSTED` merely because a valid solution was received** — a
  received solution PAUSES the assignment (PATH B); it never marks the range searched or
  exhausted. No chain-wide fork-choice proof is claimed.
- **Entry condition.** From `HASHING` when a miner submits a candidate digest satisfying the
  target.
- **Exit condition(s).** To `ROUND_ACCEPTED` when a candidate validates (I2 ∧ I3 hold and target is
  satisfied) and its full block is accepted at the **modeled acceptance point** (acceptance marks
  all other live candidates COMPETING/STALE/CANCELLED and closes the round exactly once, F3); back
  to `HASHING` **only when `propagation_quiescent` holds** — i.e. no block was accepted,
  `active_propagation_set` is empty, no same-timestamp acceptance batch is pending, and no live
  candidate-specific acceptance event remains (F3) — in which case the PATH-B miners paused by the
  failed candidates have already resumed candidate-scoped (T30 → T5); to `SECURITY_RECOVERY` if a
  floor breach coincides, preserving the remaining live candidate contexts. A single candidate's
  failure does **not** exit `SOLUTION_PROPAGATION` while other candidates are still live (F3).

### 2.7 `ROUND_ACCEPTED`

- **Meaning.** A valid solution has been accepted; accepted-block handling records the
  block, credits the solver (the `ACTIVE_HASHING` miner whose assignment contained the
  solution, per I2), and closes the round (scope §A.6). This is a terminal-accept round
  state.
- **Entry condition.** From `SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** (G8/H1) on a validated
  accepted candidate — the atomic result of `AcceptanceBatchFinalize → ValidBlockAccept` (R6). A
  block arrival never closes the round directly; acceptance is causally downstream of arbitration
  (G5). Recovery-state acceptance is legal because the round-state and the propagation set are not
  identified (G8): a valid candidate that was preserved through `SECURITY_RECOVERY` can still be
  accepted.
- **Exit condition(s).** To `ROUND_INITIALISING` to begin the next round (carrying forward
  the preserved cross-round information of Section 4).

### 2.8 `ROUND_EXHAUSTED`

- **Meaning.** Every active range has been searched to accepted exhaustion (each contributing
  miner reached `EXHAUSTED_PENDING` via PATH A range-exhaustion accounting (governed by I4/I8a and the actual-vs-reported progress model, not I11)) with no valid
  solution found for the committed template.
- **Entry condition.** From `HASHING` when the "all active ranges exhausted" predicate holds
  over the current assignment set — that is, the I8a ledger shows the **entire assigned domain
  as accepted searched coverage** (reported coverage alone is insufficient) and no
  `active_unsearched` or `inactive_unsearched` coverage remains (C9).
- **Exit condition(s).** To `TEMPLATE_REFRESH` to mine a new immutable template; or to
  `ROUND_ABORTED` if no refresh is possible.

### 2.9 `TEMPLATE_REFRESH`

- **Meaning.** The committed template is replaced by a new immutable template with a new
  `TemplateID` — the only sanctioned way the mined content changes (scope §A.7). Difficulty
  remains fixed (I12). The `RoundID` is retained; only the template (and hence the search
  content) changes.
- **Entry condition.** From `ROUND_EXHAUSTED` (exhausted template), or from `HASHING` on a
  refresh trigger (for example a superseding template becomes available).
- **Exit condition(s).** To `TEMPLATE_COMMITMENT` **only** — a template refresh ALWAYS commits
  the new immutable template through `TEMPLATE_COMMITMENT` (R17) before any re-partitioning; it
  NEVER goes directly to `ASSIGNMENT`. Re-partitioning of the new template's nonce domain
  happens on the subsequent `TEMPLATE_COMMITMENT → ASSIGNMENT` step (R18), not by bypassing
  `TEMPLATE_COMMITMENT` (D8/E8).

### 2.10 `ROUND_ABORTED`

- **Meaning.** The round terminates without acceptance due to an unrecoverable condition:
  security floor unrecoverable in `SECURITY_RECOVERY`, an invalid/uncommittable template, or
  a round-level timeout. This is a terminal-abort round state.
- **Entry condition.** From `SECURITY_RECOVERY` (floor unrecoverable), `HASHING` (fatal
  fault/timeout), `ROUND_EXHAUSTED` (no refresh possible), or `TEMPLATE_REFRESH` (refresh
  failed).
- **Exit condition(s).** To `ROUND_INITIALISING` to restart the round (carrying forward the
  preserved cross-round information of Section 4).

---

## 3. Round lifecycle rules

### 3.1 When a round begins

A round begins at entry to `ROUND_INITIALISING` — at genesis, or when the preceding round
reaches `ROUND_ACCEPTED` or `ROUND_ABORTED`. Beginning a round establishes a fresh `RoundID`
and the participant census, but commits no template and distributes no ranges yet.

### 3.2 When hashing may begin

Hashing may begin ONLY at entry to `HASHING`, which requires (a) a committed `TemplateID`
(from `TEMPLATE_COMMITMENT`) and (b) a **valid assignment set** produced by `ASSIGNMENT`.
Until both hold, no round-level hashing occurs, and no miner should be in `ACTIVE_HASHING`
for this round.

### 3.3 What constitutes a valid assignment

An assignment set is valid when every distributed range is (a) pairwise disjoint from all
other valid active assignments (invariant **I1** — no two valid active assignments overlap),
(b) bound to the current `RoundID` and committed `TemplateID` (invariant **I3**), and (c)
granted as a lease with a defined `lease_start`/`lease_expiry` (scope §B.5). A solution is
acceptable only if it binds to the assignment version that was eligible at its discovery_time
(invariant **I2**, corrected to discovery-time eligibility in G1; the version may later be PAUSED or
SUPERSEDED).

### 3.4 What terminates a round

A round terminates by reaching a terminal round state: `ROUND_ACCEPTED` (a valid solution
was accepted) or `ROUND_ABORTED` (unrecoverable failure). `ROUND_EXHAUSTED` and
`TEMPLATE_REFRESH` are NOT terminal — they route the round toward a new template rather than
ending it.

### 3.5 What happens when every active range is exhausted

When the "all active ranges exhausted" predicate holds (each active miner reached **accepted**
exhaustion via PATH A range-exhaustion accounting governed by I4/I8a and the actual-vs-reported
progress model — **not** I11 — and `EXHAUSTED_PENDING`), the round moves `HASHING →
ROUND_EXHAUSTED` **only when the I8a ledger shows the entire assigned domain as accepted searched
coverage** (reported coverage alone is insufficient) with no `active_unsearched` or
`inactive_unsearched` coverage remaining (C9). From
`ROUND_EXHAUSTED` the round proceeds to `TEMPLATE_REFRESH` to obtain a new immutable
template (new `TemplateID`, difficulty fixed per I12) and re-`ASSIGNMENT`, or to
`ROUND_ABORTED` if no refresh is possible. Exhausted miners, at the miner level, may drop to
`LOW_POWER_LISTEN` only through the confirmed-exhaustion path of I4.

### 3.6 What happens when reserve miners are activated

Reserve activation occurs via `SECURITY_RECOVERY`. When security-floor monitoring reports
`H_honest(t)` below the modeled floor, the round moves `HASHING → SECURITY_RECOVERY`, which
emits activation events. At the miner level these drive `RESERVE → WAKING` (T4) and, where
applicable, `LOW_POWER_LISTEN → WAKING` (T10), followed by `WAKING → ACTIVE_HASHING` (T5).
Re-`ASSIGNMENT` distributes disjoint ranges (I1) to the newly active miners, and the round
returns to `HASHING` once the floor is restored.

### 3.7 What happens when a miner disappears

A miner disappearing is a **miner-level** transition to `OFFLINE` (T11–T16); it does not by
itself terminate the round. Its leased range is released for reclamation. If the departures
drop `H_honest(t)` below the security floor, the round-level guard fires and moves `HASHING
→ SECURITY_RECOVERY` (Section 3.6); otherwise the released range is redistributed during a
re-`ASSIGNMENT` and hashing continues. The separation of Section 1 is why one miner's
disappearance is handled by reclamation/recovery rather than by a round transition tied to
that miner.

### 3.8 What happens when a solution is withheld

If a candidate solution is withheld (found but not propagated), the round cannot advance to
`ROUND_ACCEPTED` on it, because acceptance requires propagation and validation
(`SOLUTION_PROPAGATION`, satisfying I2 ∧ I3). The round remains in `HASHING`
(or returns there from `SOLUTION_PROPAGATION` if a partial/invalid propagation was seen)
and continues searching. Withholding does not, on its own, produce a round transition; if it
coincides with a floor breach, `SECURITY_RECOVERY` handles the coverage shortfall. No
incentive or fairness claim is made about withholding (scope §C).

### 3.9 What happens after an invalid early-stop message

An invalid (unverified) early-stop message MUST NOT end hashing (invariant **I11**). At the
round level it does not move `HASHING → ROUND_EXHAUSTED`, because that predicate requires
accepted exhaustion of every active range. At the miner level, emitting an unverified
early-stop is a protocol violation routing the emitter to `DISQUALIFIED` (miner T18). The
round remains in `HASHING`. Only accepted range-exhaustion accounting counts toward
`ROUND_EXHAUSTED`.

### 3.10 What happens after a security-floor violation

A security-floor violation (modeled `H_honest(t)` below the floor) moves `HASHING →
SECURITY_RECOVERY`, which activates reserves and re-establishes coverage (Section 3.6). If
recovery succeeds the round returns to `HASHING`; if the floor cannot be restored the round
moves `SECURITY_RECOVERY → ROUND_ABORTED`. Monitoring is specified only; no claim is made
that the floor is actually preserved (scope §C).

### 3.11 What causes a template refresh

A template refresh (`TEMPLATE_REFRESH`) is caused by (a) exhaustion of the committed
template's search space (`ROUND_EXHAUSTED → TEMPLATE_REFRESH`), or (b) a refresh trigger
during `HASHING` (for example a superseding immutable template becomes available). Refresh
produces a new `TemplateID` (difficulty fixed, I12) and returns the round to
`TEMPLATE_COMMITMENT` (R17), which then proceeds to `ASSIGNMENT` (R18) — refresh NEVER
bypasses `TEMPLATE_COMMITMENT` (D8/E8). Refresh is the ONLY sanctioned way the mined content
changes (scope §A.7).

### 3.12 What information is preserved between rounds

Across a round boundary (`ROUND_ACCEPTED` or `ROUND_ABORTED` → `ROUND_INITIALISING`) the
following is preserved:

- the chain head / accepted-block record and the monotonic `RoundID` sequence;
- the miner registry and persistent miner states (`REGISTERED`, `RESERVE`, and terminal
  `DISQUALIFIED` carry over; a miner's `MinerID` and disqualification are not reset by a new
  round);
- the reserve pool membership;
- the per-miner energy-accounting accumulators of the model (`t_hash,i`, `t_listen,i`,
  `t_wake,i`, `t_offline,i`, `E_transition,i`, `E_coordination,i`) and the aggregate ledger,
  reconciled to the fixed horizon per invariant **I5**;
- the security-accounting history (`H_active(t)`, `H_honest(t)`, `H_adversarial(t)`,
  `q_adv(t)`) and the invariant audit log;
- the fixed difficulty (I12) and the accepted baseline/A1 reference quantities.

A **new** `TemplateID` is minted per round (or per refresh); template content is NOT carried
across a completed round except as the historical accepted block.

### 3.13 What happens when multiple valid solutions compete

Two or more distinct valid solutions may arrive for the same round. Competing valid solutions
are resolved by **network-arrival semantics** (CR6), consistent with
`STAGE_01_EARLY_STOP_CERTIFICATE.md` (Section 4.5):

1. Each valid solution's propagation is event-scheduled with modeled per-recipient delays, so
   the **discrete-event queue** establishes a reproducible arrival order.
2. Local acceptance at the **modeled acceptance point** (`SOLUTION_PROPAGATION → ROUND_ACCEPTED`)
   uses the **earliest valid arrival** established by the discrete-event queue.
3. Other valid solutions are recorded as competing/stale proposals.
4. Only exactly-equal acceptance timestamps use a deterministic secondary rule: smallest
   `candidate_hash`, then smallest `MinerID`.

No global-oracle "smallest `(TemplateID, nonce, MinerID)`" primary rule is used, no global set
of future solutions is consulted, and **no chain-wide fork-choice proof** is claimed.

---

## 4. Round-transition table

Every legal round transition is enumerated below with a guard and an action. Columns:
`current_round_state | trigger/event | guard | action | next_round_state | notes`. These are
**round-level** transitions; the miner-level transitions they emit or consume are named in
the notes and specified in `STAGE_01_MINER_STATE_MACHINE.md`.

| ID | current_round_state | trigger/event | guard | action | next_round_state | notes |
|----|---------------------|---------------|-------|--------|------------------|-------|
| R1 | `∅` / prior round closed | RoundStart | Genesis, or prior round in `ROUND_ACCEPTED`/`ROUND_ABORTED` | Mint `RoundID`; gather census; prepare `H_active(t)` baseline and security floor | `ROUND_INITIALISING` | Begins a round (§3.1); preserved info from §3.12 carried in |
| R2 | `ROUND_INITIALISING` | ParamsReady | Round parameters and proposal context established | Prepare template proposal | `TEMPLATE_COMMITMENT` | No template committed yet |
| R3 | `TEMPLATE_COMMITMENT` | TemplateCommitted | Immutable template finalised; difficulty fixed (I12) | Publish `TemplateID` | `ASSIGNMENT` | Template content frozen until `TEMPLATE_REFRESH` |
| R4 | `ASSIGNMENT` | AssignmentSetValid | Ranges pairwise disjoint (I1), bound to `RoundID`+`TemplateID` (I3), leased with `lease_start`/`lease_expiry` | Distribute range leases; emit assignment offers | `HASHING` | Emits miner offers → `REGISTERED/RESERVE/… → WAKING → ACTIVE_HASHING`; hashing may begin (§3.2–3.3) |
| R5 | `HASHING` | CandidateSolution | A submitted digest satisfies the fixed target | Begin propagation/validation | `SOLUTION_PROPAGATION` | Validation checks I2 (in signer's assignment) and I3 (current round/template) |
| R6 | `SOLUTION_PROPAGATION` **or `SECURITY_RECOVERY`** (G8) | SolutionValid (via `AcceptanceBatchFinalize`, microphase 4) | Target satisfied AND I2 (discovery-time, G1) ∧ I3 hold AND the block is the winner of the atomic `AcceptanceBatchFinalize` after ALL same-timestamp arrivals were collected (never at solution-discovery); winner's `RoundID`/`TemplateID` still valid | `ValidBlockAccept`: record block, set `block_accepted`, credit solver; mark every OTHER live candidate COMPETING/STALE/CANCELLED and cancel their events; close round **exactly once** (F3/G5) | `ROUND_ACCEPTED` | A valid candidate may close a round that is in `SECURITY_RECOVERY` too (G8). Solver is the miner whose discovery-eligible assignment version contained the solution (I2/G1); competing valid solutions resolved by the deterministic winner rule (`candidate_hash` then `MinerID`, §3.13, C6, G5/G7); all remaining assignments close because the **round ended** (`stop_reason = ROUND_ACCEPTED`), NOT exhausted and NOT resumed (CR-B1, F3) |
| R7 | `SOLUTION_PROPAGATION` | PropagationQuiescent | A candidate failed (invalid/withheld/rejected/timeout/empty-batch) AND, after candidate-scoped `HandlePropagationFailure`, `propagation_quiescent` holds — `active_propagation_set` empty, no acceptance batch pending, no live candidate acceptance event, no block accepted (F3); floor still satisfied | Return to searching; the PATH-B miners paused by the failed candidate(s) have already resumed candidate-scoped (T30 → T5) | `HASHING` | The round returns to `HASHING` ONLY when quiescent; a single candidate's failure while others remain live does NOT fire R7 (F3, §3.8) |
| R8 | `SOLUTION_PROPAGATION` | InvalidWithFloorBreach | A candidate failed AND `H_honest(t)` below floor | Enter remediation; PRESERVE the remaining live candidate contexts in `active_propagation_set` (F3 defined rule) | `SECURITY_RECOVERY` | Coverage shortfall handled by reserve activation; on recovery the round returns to `SOLUTION_PROPAGATION` if the set is still non-empty, else to `HASHING` |
| R9 | `HASHING` | AllActiveRangesExhausted | Every active range reached accepted exhaustion (I4/I8a; PATH A) and `EXHAUSTED_PENDING`; the I8a ledger shows the entire assigned domain as accepted searched coverage with no `active_unsearched`/`inactive_unsearched` remaining | Close current template's search | `ROUND_EXHAUSTED` | Only accepted exhaustion counts, reported coverage alone is insufficient (§3.5, §3.9, C9) |
| R10 | `HASHING` | SecurityFloorViolation | Modeled `H_honest(t)` below the security floor, or invariant-risk detected | Trigger reserve activation | `SECURITY_RECOVERY` | Emits miner activation → `RESERVE → WAKING` (T4), `LOW_POWER_LISTEN → WAKING` (T10) |
| R11 | `HASHING` | RefreshTrigger | A superseding immutable template is available | Prepare template replacement | `TEMPLATE_REFRESH` | Refresh is the only way mined content changes (§3.11) |
| R12 | `HASHING` | FatalFault / RoundTimeout | Unrecoverable fault or round-level timeout | Abort round | `ROUND_ABORTED` | Terminal-abort (§3.4) |
| R13 | `SECURITY_RECOVERY` | FloorRestored | Activated reserves raise `H_honest(t)` to/above the floor | Re-partition/redistribute disjoint ranges (I1); if live candidates remain, resume propagation instead | `ASSIGNMENT` (→ `HASHING` at R4) **or `SOLUTION_PROPAGATION`** if `active_propagation_set` is non-empty (G8) | Re-`ASSIGNMENT` returns to `HASHING` at R4 when `propagation_quiescent`; when live candidates were preserved during recovery (G8), the round returns to `SOLUTION_PROPAGATION` and those candidates' acceptance events continue (§3.6) |
| R14 | `SECURITY_RECOVERY` | FloorUnrecoverable | Floor cannot be restored (insufficient reserves) | Abort round | `ROUND_ABORTED` | Terminal-abort (§3.10) |
| R15 | `ROUND_EXHAUSTED` | RefreshAvailable | A new immutable template can be committed; difficulty fixed (I12) | Prepare new `TemplateID` | `TEMPLATE_REFRESH` | Retains `RoundID`; new template only (§3.5) |
| R16 | `ROUND_EXHAUSTED` | NoRefreshPossible | No new template can be produced | Abort round | `ROUND_ABORTED` | Terminal-abort |
| R17 | `TEMPLATE_REFRESH` | NewTemplateReady | New immutable template prepared | Commit new template | `TEMPLATE_COMMITMENT` | Then R3 → `ASSIGNMENT` re-partitions the new domain |
| R18 | `TEMPLATE_COMMITMENT` | TemplateCommitted (refresh) | New immutable template committed via TemplateCommit (D8) | Enter partitioning of the NEW candidate-identity domain | `ASSIGNMENT` | Refresh ALWAYS mints a fresh TemplateID via TEMPLATE_COMMITMENT (R17); no commitment-bypass. New ORIGINAL assignments only (C5) |
| R19 | `TEMPLATE_REFRESH` | RefreshFailed | New template invalid/uncommittable | Abort round | `ROUND_ABORTED` | Terminal-abort |
| R20 | `ROUND_ACCEPTED` | NextRound | Accepted block recorded and round closed | Advance `RoundID`; carry forward preserved info (§3.12) | `ROUND_INITIALISING` | Terminal-accept → next round |
| R21 | `ROUND_ABORTED` | RestartRound | Round closed without acceptance | Carry forward preserved info (§3.12) | `ROUND_INITIALISING` | Terminal-abort → restart |

### 4.1 Round-level invariant enforcement summary

- **I1** (no two valid active assignments overlap) gates every (re-)assignment: R4, R13,
  R18.
- **I2 / I3** (accepted solution binds to the discovery-time-eligible assignment version, G1 / matching current
  `RoundID`+`TemplateID`) gate acceptance: R6 (via the R5 validation).
- **I4 (amended, CR-B2)** (no `LOW_POWER_LISTEN` before one of the recorded `stop_reason`
  triggers) is a miner-level invariant. At round level, `ROUND_EXHAUSTED` (R9) still requires
  accepted exhaustion of every active range and is **never** driven by an unverified
  early-stop. A **verified valid-solution** early-stop is a separate, legitimate miner-level
  idle drop (PATH B, `stop_reason = VALID_SOLUTION_VERIFIED`, assignment PAUSED) that does
  **not** move the round to `ROUND_EXHAUSTED` and marks no range exhausted (§2.6, CR-B1,
  CR-B9).
- **I5** (durations ≥ 0, reconcile to horizon) governs the preserved energy accumulators
  carried across R20/R21.
- **I11** (false early-stop cannot end hashing) means R9 is never triggered by an unverified early-stop certificate; range exhaustion is governed by I4/I8a and the actual-vs-reported progress model (not I11); an unverified early-stop keeps the round in `HASHING`
  (§3.9) and disqualifies the emitter at the miner level.
- **I12** (difficulty constant) holds across every round state; no transition changes
  difficulty.

### 4.2 Separation restated

No row above equates a round state with a miner state. Round transitions are driven by
round-level guards over aggregated conditions (target satisfaction, exhaustion of all active
ranges, security-floor status, refresh availability), and they emit or consume miner-level
events. The miner state machine (`STAGE_01_MINER_STATE_MACHINE.md`) is the sole authority on
per-`MinerID` states; this document is the sole authority on per-`RoundID` states. No
security, fairness, or incentive property is claimed by either (scope §C).
