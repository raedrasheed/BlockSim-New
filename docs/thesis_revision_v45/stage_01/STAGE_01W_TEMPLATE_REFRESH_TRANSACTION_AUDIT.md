# Stage 1W — Template-Refresh Transaction Audit (W3)

## 0. Scope

This document audits correction **W3** — *"make template-refresh setup a real
transaction"* — as it appears in the *current* Stage-1 formal specification of the idle
policy within PoCol. It is a descriptive audit: it reads and quotes the committed artifacts
and asserts nothing beyond what those artifacts state. It describes the final committed state
of the corpus; there are no open W3 findings against the template-refresh setup.

The object under audit is the procedure `TemplateRefresh` and, as its named collaborators,
`RollbackTemplateRefreshSetup`, `CreatePendingAssignment`, `StartWake`, `CompleteAssignmentPhase`,
`RoundAbort`, and the bounded-retry handler `SetupRetryEvent`. Every claim is grounded in the
following primary sources, all under `docs/thesis_revision_v45/stage_01/`. Line numbers were
re-established by direct search against the committed files and are cited as currently observed.

- `STAGE_01_PROTOCOL_PSEUDOCODE.md`
  - `TemplateRefresh` — §19, lines **4601–4697** (header at 4601).
  - `RollbackTemplateRefreshSetup` — lines **1673–1697** (header at 1673:
    *"W1/W2/V8: executable rollback of a failed template-refresh setup"*).
  - `SetupRetryEvent` — lines **1699–1729** (header at 1699:
    *"W8: a bounded, idempotent, state-compatible retry of a rolled-back setup"*).
  - `StartWake` — lines **1097–1160** (the `wake_seated(...)` result at 1150–1152).
  - `CreatePendingAssignment` — lines **1238** onward (the W7 result contract at 1244–1253).
  - `SetupRetryEvent` event-table row — line **563**.
- `STAGE_01_ROUND_STATE_MACHINE.md` — §3.10a Stage-1W addendum, **W3** block lines **647–650**
  (with the surrounding W1/W2 and W7/W8 blocks).
- `STAGE_01_TERMINOLOGY.md` — Stage-1W terminology addendum, the
  **`refresh_setup_txn` populated in-loop (W3)** entry lines **836–838**.
- `STAGE_01_TRACEABILITY_MATRIX.csv` — requirement **R162** (line 163) and the test-vector
  requirement **R168** carrying **TV189** (line 169).
- `STAGE_01V_WAKE_TRANSACTION_AUDIT.md` — procedure-call-graph row for `TemplateRefresh`
  (line 321), quoted only to characterise the prior (V8) shape that W3 supersedes.

The overall algorithm name remains **PoCol**; the mechanism under revision is **the idle policy
within PoCol**. The A1 accepted-baseline energy figure of `8.420833333 kWh` is unchanged by this
correction — W3 alters the control flow of a failed setup, not any census value, residency
interval, or accounting quantity.

## 1. The defect W3 corrects (the prior V8 shape)

Before W3, `TemplateRefresh` did not treat its setup as a transaction with explicit per-field
capture. The Stage-1V procedure-call-graph row for `TemplateRefresh`
(`STAGE_01V_WAKE_TRANSACTION_AUDIT.md`, line 321) records the prior shape: on a seated wake it
performed `RECORD refresh_wake(m, assignment_m, wref)` and on a failed wake
`RECORD refresh_wake_failed(m, assignment_m, wr)`, and the transaction was *"captured into
`refresh_setup_txn`"* only afterward. Two defects follow from that shape:

1. **The transaction was reconstructed after the loop from prose.** The membership of
   `refresh_setup_txn` (its created assignments, prior states, and wakes) was not written by
   explicit statements at the point each object was created and each wake was seated; it was
   re-derived after the loop from recorded prose — for example, from "the ACTUAL WakeEventRefs
   returned". A rollback record assembled after the fact from narrative text is not a faithful
   ledger of what the setup actually created, and it can silently diverge from the true set of
   live heads and pending wakes.

2. **The refresh could continue after a wake failure.** Because the failure was merely recorded
   (`refresh_wake_failed`) rather than latched into a control variable that short-circuits the
   remainder of setup, nothing structurally prevented `TemplateRefresh` from minting further work
   and proceeding to complete the assignment phase after a `StartWake` had already failed —
   reaching the irreversible `ASSIGNMENT -> HASHING` transition on a setup that was already known
   to be partial.

The current specification names both defects in its own W3 comments and forbids them. The
in-loop capture comment states the corrected discipline: *"Every created AssignmentID, prior
miner state, and StartWake WakeEventRef is captured by EXPLICIT statements INSIDE the loop —
NEVER reconstructed afterward from prose."* (pseudocode line 4625). The wake-capture line is
annotated *"capture ACTUAL WakeEventRef EXPLICITLY"* (line 4648) — the "ACTUAL" qualifier is the
residue of the superseded reconstruction-from-prose idiom, now performed as an explicit `ADD`.

## 2. The corrected transaction (init-before-loop, explicit per-field capture, fail-fast)

W3 makes `TemplateRefresh`'s setup a real transaction with three committed properties.

**(a) Initialised BEFORE the miner loop, carrying the W1 rollback envelope.** The transaction is
created once, ahead of the loop, with an immutable `rollback_envelope` bound to this refresh's own
dispatch envelope (pseudocode lines 4622–4627):

```
    # W1/W3/V8: initialise the refresh setup TRANSACTION BEFORE the miner loop, carrying an IMMUTABLE rollback_envelope
    #   (this refresh's own dispatch_envelope: { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }).
    #   Every created AssignmentID, prior miner state, and StartWake WakeEventRef is captured by EXPLICIT statements
    #   INSIDE the loop — NEVER reconstructed afterward from prose.
    SET refresh_setup_txn <- setup_transaction(rollback_envelope = dispatch_envelope,
          wakes = empty, created_assignments = empty, prior_states = empty)   # W1/W3
    SET refresh_setup_error <- null   # W3: set on a CreatePendingAssignment or StartWake failure; checked after the loop
```

The three ledgers (`wakes`, `created_assignments`, `prior_states`) begin empty, and a companion
`refresh_setup_error` control variable begins `null`. This is the sole `setup_transaction(...)`
construction for the refresh; a corpus-wide search confirms no second construction exists after
the loop (see §7).

**(b) Populated by EXPLICIT statements INSIDE the loop.** The loop iterates eligible miners in
stable `MinerID` order (line 4631) and captures each field at the moment it becomes real
(pseudocode lines 4640–4641, 4648):

```
      RECORD refresh_setup_txn.prior_states[m] <- miner_state(m)                   # W3: capture prior state EXPLICITLY
      ADD AssignmentID(assignment_m) to refresh_setup_txn.created_assignments       # W3: capture AssignmentID EXPLICITLY
      ...
      IF wr = wake_seated(waid, wref, wtt, ws): ADD wref to refresh_setup_txn.wakes   # W3: capture ACTUAL WakeEventRef EXPLICITLY
```

The prior state and the created `AssignmentID` are recorded only after `CreatePendingAssignment`
has returned `assignment_created` and the head has been read out (`SET assignment_m <- cr.assignment`,
line 4639); the `WakeEventRef` is added only on the `wake_seated(...)` result of `StartWake`. No
field is ever inferred later.

**(c) Fail-fast.** The moment `CreatePendingAssignment` or `StartWake` fails, the control variable
`refresh_setup_error` is set, and the loop mints no further work. The guard at the top of each
iteration short-circuits the remainder of setup (line 4632):

```
      IF refresh_setup_error != null: BREAK    # W3: once the refresh has failed, mint NO further work; roll back below
```

## 3. Statement-order walkthrough (§19, lines 4601–4697)

The corrected order of statements is as follows, each grounded at its current line.

1. **Round-state sequencing and template build.** `TemplateRefresh` transitions to
   `TEMPLATE_REFRESH` (4608), closes the old-template assignments via `CloseTemplateAssignments`
   (4610–4611), builds the new candidate template (4613), transitions to `TEMPLATE_COMMITMENT`
   (4615), and commits via `TemplateCommit`, which moves the round to `ASSIGNMENT` (4617).
2. **Eligibility.** The eligible set is the miners whose current state has a legal activation edge
   into `WAKING`: `{ REGISTERED, RESERVE, LOW_POWER_LISTEN }` (4621).
3. **Transaction init BEFORE the loop.** `refresh_setup_txn` is constructed with the immutable
   `rollback_envelope = dispatch_envelope` and empty ledgers (4626–4627); `refresh_setup_error`
   is initialised to `null` (4628).
4. **Loop, in stable `MinerID` order** (4631). Each iteration:
   - checks the fail-fast guard `IF refresh_setup_error != null: BREAK` (4632);
   - calls `CreatePendingAssignment(...)` capturing the result in `cr` (4635–4636);
   - branches on the W7 result BEFORE any read: `IF cr is assignment_creation_failed(reason): SET
     refresh_setup_error <- assignment_creation_failed(reason) ; CONTINUE` (4637–4638);
   - reads the created head `SET assignment_m <- cr.assignment` (4639);
   - records `refresh_setup_txn.prior_states[m]` (4640) and adds
     `AssignmentID(assignment_m)` to `refresh_setup_txn.created_assignments` (4641);
   - sets lease start/expiry (4642–4643);
   - calls the non-blocking `StartWake(...)` capturing the structured result in `wr` (4646–4647);
   - on `wake_seated(waid, wref, wtt, ws)` adds `wref` to `refresh_setup_txn.wakes` (4648);
     otherwise `SET refresh_setup_error <- wr` (4649).
5. **Post-loop assertion.** `ASSERT difficulty unchanged` (4651, invariant I12).
6. **Success/failure fork** (4654–4663). `IF refresh_setup_error != null` the procedure sets
   `setup_reason` and falls through to rollback WITHOUT calling `CompleteAssignmentPhase`; only the
   `ELSE` branch asserts `round_state = ASSIGNMENT`, calls `CompleteAssignmentPhase`, and returns
   `new_TemplateID` on `assignment_phase_completed`.
7. **Rollback and liveness** (4666–4689). On any failure — a setup error, or an
   `assignment_phase_failed` disposition from `CompleteAssignmentPhase` — `RollbackTemplateRefreshSetup`
   is invoked with `refresh_setup_txn`, followed by the bounded retry-or-abort decision (§5).

The ordering property W3 asserts is exactly this: the transaction exists and is populated *before*
any decision reads it, and the failure decision is taken *from* the latched `refresh_setup_error`
rather than reconstructed afterward.

## 4. The success path calls `CompleteAssignmentPhase` exactly once — and only when clean

The `ASSIGNMENT -> HASHING` transition is reached only through the single sanctioned owner
`CompleteAssignmentPhase`, and only in the `ELSE` arm where `refresh_setup_error` is `null`
(pseudocode lines 4656–4663):

```
    ELSE:
      ...
      ASSERT round_state = ASSIGNMENT
      SET disp <- CALL CompleteAssignmentPhase(RoundContext, dispatch_envelope)   # L2/M2/T5: SOLE ASSIGNMENT -> HASHING owner
      IF disp = assignment_phase_completed: RETURN new_TemplateID
      SET setup_reason <- disp.reason        # assignment_phase_failed(reason) — reversible (round still ASSIGNMENT)
```

Because the guard `IF refresh_setup_error != null` (4654) diverts every failed setup to
`setup_reason <- refresh_setup_error` (4655) before this arm is reached, a refresh that recorded a
`CreatePendingAssignment` or `StartWake` failure can never fall into the `CompleteAssignmentPhase`
call. This is the structural guarantee the prior V8 shape lacked.

## 5. The failure path (no `CompleteAssignmentPhase`, named rollback, bounded retry/abort)

When `refresh_setup_error != null`, `TemplateRefresh` takes the failure path directly, skipping
`CompleteAssignmentPhase` entirely (pseudocode lines 4652–4655):

```
    # W3: if a CreatePendingAssignment or StartWake failed, DO NOT call CompleteAssignmentPhase — roll back immediately
    #   and take the declared liveness path.
    IF refresh_setup_error != null:
      SET setup_reason <- refresh_setup_error
```

It then invokes the **named** rollback, which uses the transaction's immutable envelope
(pseudocode line 4666):

```
    SET rb <- CALL RollbackTemplateRefreshSetup(RoundContext, refresh_setup_txn)   # W1/W2/V8
```

`RollbackTemplateRefreshSetup` (lines 1673–1697) cancels each pending `wref` in
`setup_txn.wakes`, departs any miner left `WAKING` to `OFFLINE` via the legal `T12` edge with
`transition_envelope = setup_txn.rollback_envelope` (lines 1682–1687, the W1/W2 discipline),
closes each `aid` in `setup_txn.created_assignments` as `CLOSED` and restores the coverage/custody
ledgers (1688–1691), and returns `rollback_completed(rolled_to_offline)` — or
`rollback_failed(reason = residual_partial_setup)` if any created head, wake, or `WAKING` miner
survives (1692–1694). The transaction populated in §2 is precisely the ledger this rollback
consumes.

The declared liveness decision then follows (pseudocode lines 4667–4689):

- **`rollback_failed` → abort.** `RoundAbort(reason = template_refresh_rollback_failed, ...)`
  (4667–4669).
- **Rollback routed a miner to `OFFLINE` → abort (W8 state-incompatible).** If
  `rb.rolled_to_offline`, `RoundAbort(reason = template_refresh_failed(setup_reason), ...)`
  (4672–4674) — no retry from an incompatible state.
- **Retry budget exhausted → abort.** If `setup_retry_generation[...] >= maximum_setup_retries`,
  `RoundAbort(reason = template_refresh_retries_exhausted(setup_reason), ...)` (4675–4677).
- **Bounded retry within horizon.** If the next representable time is within `run_horizon_T`, the
  generation is advanced, a `SetupRetryID = (RoundID_current, TEMPLATE_REFRESH_SETUP, g)` is
  formed, and a `SetupRetryEvent` is seated at a strictly-later `event_time`; on `scheduled(...)`
  the procedure returns `template_refresh_retry_seated(srid, setup_reason)` (4678–4687).
- **Fallback → abort.** Otherwise `RoundAbort(reason = template_refresh_failed(setup_reason), ...)`
  (4688–4689).

The retry, when seated, re-enters through `SetupRetryEvent` (lines 1699–1729), which is
stale-guarded on `RoundID` (1706), idempotent via `applied_setup_retry_ids` (1709–1710), bounded
by `maximum_setup_retries` (1712), and state-compatible — it aborts rather than retrying if any
eligible participant is `OFFLINE` (1717–1719) — before re-invoking `TemplateRefresh` (1723). The
event itself is registered as `SetupRetryEvent` in the event table (line 563), whose note records
that it *"re-invokes PrepareParticipantsForNewRound / TemplateRefresh at a strictly-later
event_time after a rolled-back setup; stale-guarded on RoundID."* The round is therefore never
left in `ASSIGNMENT` with no controller: every failure either seats a bounded retry or aborts.

## 6. Map to TV189

Requirement **R168** (traceability line 169) specifies the blocking test vector **TV189**:
*"a TemplateRefresh StartWake failure sets `refresh_setup_error` skips `CompleteAssignmentPhase`
and runs the named rollback/liveness."* The corrected control flow satisfies each conjunct of
TV189 at named lines:

- *sets `refresh_setup_error`* — the `StartWake` failure arm `ELSE: SET refresh_setup_error <- wr`
  (pseudocode line 4649);
- *skips `CompleteAssignmentPhase`* — the post-loop guard `IF refresh_setup_error != null: SET
  setup_reason <- refresh_setup_error` (4654–4655) diverts around the `ELSE` arm that alone calls
  `CompleteAssignmentPhase` (4661);
- *runs the named rollback* — `SET rb <- CALL RollbackTemplateRefreshSetup(RoundContext,
  refresh_setup_txn)` (4666);
- *and liveness* — the bounded retry-or-abort cascade (4667–4689) driving `SetupRetryEvent` or
  `RoundAbort`.

TV189 is recorded in the traceability matrix as **SPECIFIED** under R168, targeting a
`STAGE_01W_SEMANTIC_TEST_VECTORS` artifact. As observed at audit time that Stage-1W
semantic-test-vector file is not yet present in `docs/thesis_revision_v45/stage_01/` (no
`STAGE_01W_*` files exist in the corpus); the vector's *specification* is complete and its
executable *paper vector* is the outstanding deliverable of R168. This audit records that gap
rather than asserting the vector exists.

## 7. Traceability

- **Round state machine — §3.10a W3.** `STAGE_01_ROUND_STATE_MACHINE.md` lines 647–650 state the
  requirement verbatim: `TemplateRefresh` *"initialises `refresh_setup_txn` BEFORE its miner loop
  and populates it by EXPLICIT statements inside the loop (each created `AssignmentID`, prior
  state, and the `StartWake` `WakeEventRef`); on any `CreatePendingAssignment` / `StartWake`
  failure it sets `refresh_setup_error`, does NOT call `CompleteAssignmentPhase`, invokes
  `RollbackTemplateRefreshSetup`, and takes the declared retry/abort path."* The pseudocode of §2–§5
  above implements this clause for clause.
- **Terminology — W3.** `STAGE_01_TERMINOLOGY.md` lines 836–838, the entry
  *"`refresh_setup_txn` populated in-loop (W3)"*: the transaction is initialised before the loop and
  each field is populated by explicit statements as assignments are created and wakes seated; a
  wake/creation failure *"sets `refresh_setup_error`, skips `CompleteAssignmentPhase`, and takes the
  named rollback + liveness path."* Consistent with the pseudocode and the round-SM block.
- **Requirement R162.** Traceability line 163 phrases R162 as *"Make template-refresh setup a real
  transaction (W3)"*, names the failing-artifact condition it prohibits — *"a template refresh that
  records a wake failure and proceeds to `CompleteAssignmentPhase` or builds its rollback record
  from prose"* — and links `TemplateRefresh`, `RollbackTemplateRefreshSetup`, and
  `CompleteAssignmentPhase` against invariants I16 and I18b. Status **SPECIFIED**. The corrected
  procedure removes exactly the prohibited condition (§1, §4, §5).

## 8. Grep confirmations (negative checks)

Two searches over the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` confirm the defect residue is
absent:

- `setup_transaction(` matches only line 1533 (`participant_setup_txn`, the W1 analogue in
  `PrepareParticipantsForNewRound`) and line 4626 (`refresh_setup_txn`). The single refresh
  construction is at 4626, which precedes the loop header at 4631 — so **no
  `SET refresh_setup_txn <- setup_transaction(...)` remains after the loop.**
- `ACTUAL WakeEventRefs returned` and equivalent prose-reconstruction idioms return no
  procedural match; the only occurrence of "reconstruct" (line 4625) is the negative directive
  *"NEVER reconstructed afterward from prose,"* and the sole use of "ACTUAL" (line 4648) is the
  explicit `ADD wref to refresh_setup_txn.wakes` capture. **No "the ACTUAL WakeEventRefs
  returned"-style prose construction of the transaction remains.**

## 9. Conclusion

Correction W3 is fully realised in the current specification. `TemplateRefresh` constructs
`refresh_setup_txn` once, before its miner loop, with the immutable W1 `rollback_envelope`;
populates every ledger field (`prior_states`, `created_assignments`, `wakes`) by explicit
statements at the point of creation and seating; latches `refresh_setup_error` on any W7
`assignment_creation_failed` or non-`wake_seated` `StartWake` result; skips
`CompleteAssignmentPhase` on failure; invokes the named `RollbackTemplateRefreshSetup`; and takes
the declared bounded `SetupRetryEvent` (W8) or `RoundAbort`. The transaction is never
reconstructed afterward from prose. The requirement (R162, round-SM §3.10a W3, terminology W3) is
satisfied for clause; its blocking vector TV189 is SPECIFIED, with the Stage-1W semantic-test-vector
file the outstanding R168 deliverable. The A1 baseline of `8.420833333 kWh` is unchanged.
