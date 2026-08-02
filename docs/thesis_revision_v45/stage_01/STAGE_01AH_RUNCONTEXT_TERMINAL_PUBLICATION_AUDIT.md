# Stage 1AH — Terminal-Round Publication (AH2) & RunContext Field / Identity Audit (AH9)

**Audit target:** AH2 — the single terminal-round publication procedure
`PublishTerminalRoundAndSeatNext` and its unification of the three terminal closure paths; AH9 —
`STRUCTURE RunContext` driver/bootstrap field declarations and the §0.2 identity-vs-payload
distinctions.
**Scope:** documentation-only pseudocode revision (Stage 1AH). This audit inspects ONLY the final
normative tree under `docs/thesis_revision_v45/stage_01/`; the primary artifact is
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. No historical Stage-1A…1AG artifact is modified and no
executable source is claimed.

**Context invariants (unchanged by AH2/AH9).** The algorithm is **PoCol** and the mechanism is
**the idle policy within PoCol** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:6`–`7`). The A1 accepted-energy
baseline **`8.420833333 kWh`** is unchanged — AH2/AH9 is a structural terminal-publication and
run-context declaration revision that touches no census value, residency interval, or
transition-energy quantity.

All line anchors below are `file:line` into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless a different
file is named.

---

## Check AH2.1 — `PublishTerminalRoundAndSeatNext` is the ONE named publication owner, called by `CloseRoundAssignments`, in the REQUIRED order

**Requirement.** `PublishTerminalRoundAndSeatNext` is the single named terminal-round publication +
next-bootstrap owner, invoked by `CloseRoundAssignments`, executing in the fixed order: assert round
terminal → record `round_terminal_time` → publish `prior_round_terminal_state` → (horizon / RUN_HOOK
close: return no-seat) → create the immutable next `BootstrapRequest` (per-round target, never
`run_start_time`) → seat the next bootstrap → inspect + store the seating result.

**Evidence.**
- Defined as the ONE owner: `PROCEDURE PublishTerminalRoundAndSeatNext` at `6527`
  ("AH2: the ONE named terminal-round publication + next-bootstrap owner").
- Called from `CloseRoundAssignments` at its tail: `6514`
  (`CALL PublishTerminalRoundAndSeatNext(RoundContext, disposition = disposition, dispatch_envelope = dispatch_envelope)`),
  with the surrounding AH2 comment at `6509`–`6513` and the NOTE at `6523`–`6525`.
- Required order inside the procedure body (`6534`–`6566`):
  1. ASSERT round terminal — `6536` (`ASSERT round_state in {ROUND_ACCEPTED, ROUND_ABORTED}`).
  2. record `round_terminal_time` — `6539` (`RECORD round_terminal_time(RoundID_current) <- dispatch_envelope.event_time`).
  3. publish `prior_round_terminal_state` — `6542` (`SET RunContext.prior_round_terminal_state <- RunContext.current_round_context`).
  4. horizon / RUN_HOOK close returns no-seat — `6545`–`6546`
     (`IF dispatch_envelope.envelope_namespace = RUN_HOOK: RETURN terminal_round_published_no_seat(...)`);
     the additional time-exhausted guard returns no-seat at `6548`–`6550`.
  5. create the IMMUTABLE next `BootstrapRequest` with a PER-ROUND target, never `run_start_time` —
     comment "NEVER config.run_start_time (that is the FIRST round's target only)" at `6552`,
     stable id `brid` at `6553`, `next_br` with `target_time = next_target` at `6554`–`6555`
     (`next_target` derived from `next_representable_simulation_time(round_terminal_time(...))` at `6548`),
     registered at `6556` and set as `current_bootstrap_request` at `6557`.
  6. seat the next bootstrap — `6560` (`SET boot <- CALL SeatNextRoundBootstrap(RunContext)`).
  7. inspect + store the seating result — `6561`–`6566` (the `SWITCH boot` with the seated / already-seated
     replay / declared seat-failed dispositions).
- The REQUIRED-order contract is restated in the closing NOTE at `6569`–`6574`, including
  "(5) create the immutable next BootstrapRequest (per-round target_time, never run_start_time)".

**Result: PASS.**

---

## Check AH2.2 — the three terminal paths are UNIFIED, each transitioning to a terminal state BEFORE `CloseRoundAssignments`, guarded by the terminal ASSERT

**Requirement.** ValidBlockAccept (ROUND_ACCEPTED), RoundAbort (ROUND_ABORTED), and
CloseRoundAtHorizon (horizon close, publishes but seats no next round) all route closure through
`CloseRoundAssignments` → `PublishTerminalRoundAndSeatNext`. Each path must have transitioned the
round to its terminal state BEFORE `CloseRoundAssignments`, so the terminal ASSERT at `6536` holds
and no bootstrap is ever seated while the predecessor round is nonterminal.

**Evidence.**
- Unification precondition naming all three paths as already-transitioned-before-closure:
  `6529`–`6533`, which lists "ValidBlockAccept -> ROUND_ACCEPTED (ordinary acceptance),
  RoundAbort -> ROUND_ABORTED (ordinary abort), CloseRoundAtHorizon -> ROUND_ABORTED (horizon
  closure)" at `6530`–`6531`.
- The terminal-predecessor ASSERT is present and unconditional (runs FIRST in the procedure body):
  `6536` (`ASSERT round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` — "never publish/seat a nonterminal predecessor").
- `CloseRoundAssignments` itself performs NO round-state transition — it records per-assignment
  `round_closure_disposition` (`6427`) and `RECORD round_closure(...)` (`6504`) only; the terminal
  round-state transition is the caller's responsibility.
- **ValidBlockAccept** (`PROCEDURE` at `6361`): `TRANSITION round_state -> ROUND_ACCEPTED` at `6389`,
  THEN `CALL CloseRoundAssignments(..., disposition = ROUND_ACCEPTED, ...)` at `6392`. Transition
  precedes closure. **PASS.**
- **RoundAbort** (`PROCEDURE` at `6840`): the reorder is present and documented — comment "move the
  round to its terminal state (G10) BEFORE closure" at `6871`–`6874`, `TRANSITION round_state ->
  ROUND_ABORTED` at `6875` ("AH2: terminal BEFORE closure"), THEN `CALL CloseRoundAssignments(...,
  disposition = ROUND_ABORTED, ...)` at `6882`. Reorder verified. **PASS.**
- **CloseRoundAtHorizon** (`PROCEDURE` at `6975`): the horizon path correctly returns no-seat via the
  RUN_HOOK branch (`6545`–`6546`, reached because the horizon envelope carries
  `envelope_namespace = RUN_HOOK`, minted at `6995`). **However, the terminal transition is placed
  AFTER `CloseRoundAssignments`, not before:** `CALL CloseRoundAssignments(..., disposition =
  ROUND_ABORTED, dispatch_envelope = horizon_envelope)` at `7000`–`7001`, then `RECORD
  horizon_end_disposition(RoundID) <- closed_at_horizon` at `7004`, then `TRANSITION round_state ->
  ROUND_ABORTED` at `7005`. Because `CloseRoundAssignments` invokes `PublishTerminalRoundAndSeatNext`
  unconditionally at its tail (`6514`), and that procedure's first statement is the terminal ASSERT
  (`6536`), the ASSERT executes at `7000` while `round_state` is STILL NONTERMINAL (the horizon
  entry precondition guarantees nonterminal — `6977`–`6978` — and the only transition in the
  procedure is the one at `7005`, which has not yet run). The unification precondition at `6531`
  therefore misstates this path ("CloseRoundAtHorizon -> ROUND_ABORTED" as already transitioned),
  and the ASSERT at `6536` would fail on the horizon path.

**Result: FAIL.** The horizon path breaks the AH2 terminal-before-closure invariant that
ValidBlockAccept (`6389` before `6392`) and RoundAbort (`6875` before `6882`) satisfy.

**Defect.** `STAGE_01_PROTOCOL_PSEUDOCODE.md:7005` — `TRANSITION round_state -> ROUND_ABORTED`
occurs AFTER `CALL CloseRoundAssignments` (`7000`), so on the horizon path the round is still
nonterminal when `PublishTerminalRoundAndSeatNext`'s terminal ASSERT (`6536`) runs, contradicting
that procedure's stated precondition (`6531`).

**Fix.** Move the `TRANSITION round_state -> ROUND_ABORTED` (and, for symmetry with RoundAbort, the
`RECORD horizon_end_disposition(RoundID)` at `7004`) to BEFORE the `CALL CloseRoundAssignments` at
`7000`, mirroring the RoundAbort reorder at `6875` (transition) preceding `6882` (closure). This
makes the horizon path terminal-before-closure, satisfies the ASSERT at `6536`, and makes the
precondition at `6531` truthful.

---

## Check AH9.3 — every driver/bootstrap field is DECLARED directly inside `STRUCTURE RunContext`

**Requirement.** Each of `driver_event_seat`, `next_round_setup_seq`, `bootstrap_request_registry`,
`current_bootstrap_request`, `driver_request_registry`, `driver_request_seq`,
`pending_driver_request_index`, `genesis_miner_registry`, `current_round_context`,
`prior_round_terminal_state`, and `config` must be DECLARED in `STRUCTURE RunContext` (not only
initialised in `RunInitialise`).

**Evidence.** `STRUCTURE RunContext` begins at `2641`; the AH9 banner "EVERY per-run
driver/bootstrap field is DECLARED HERE (previously only initialised in RunInitialise)" is at `2675`.
Each field is declared in the structure body:
- `config` — `2676`
- `current_round_context` — `2678`
- `prior_round_terminal_state` — `2679`
- `driver_event_seat` — `2681`
- `next_round_setup_seq` — `2683`
- `bootstrap_request_registry` — `2686`
- `current_bootstrap_request` — `2689`
- `driver_request_registry` — `2691`
- `driver_request_seq` — `2695`
- `pending_driver_request_index` — `2696`
- `genesis_miner_registry` — `2699`

All eleven appear as structure members, not merely in `RunInitialise`. (`RunInitialise` at `2727`
independently INITIALISES the same fields at `2750`–`2766` and RETURNS them at `2773`–`2777`, and the
NOTE at `2794`–`2798` confirms the structure declaration/initialisation split.)

**Result: PASS.**

---

## Check AH9.4 — §0.2 keeps `EventRef` / `dispatch_envelope` / `immutable_payload` / `queued_event_record` / `stable_tie_key` distinct, with the domain fields as IMMUTABLE PAYLOAD

**Requirement.** §0.2 must keep `EventRef`, `dispatch_envelope`, `immutable_payload`,
`queued_event_record`, and `stable_tie_key` as distinct concepts, and state that `RoundID`,
`TemplateID`, `CandidateID`, `MinerID`, `AssignmentID`, and `assignment_version` are IMMUTABLE
PAYLOAD, NOT `dispatch_envelope` fields.

**Evidence.** §0.2 (event envelope) header at `49`. The AH9 "identity vs payload" clarification is at
`55`–`63`:
- `dispatch_envelope` is EXACTLY the five identity fields
  `{ envelope_namespace, event_time, delta_cycle, event_seq, hook_id }` — `56`–`57`.
- The domain fields "`RoundID`, `TemplateID`, `CandidateID`, `PropagationID`, `MinerID`,
  `AssignmentID`, `assignment_version`" are "IMMUTABLE HANDLER PAYLOAD (they live in
  `queued_event_record.immutable_payload`), NEVER `dispatch_envelope` fields" — `57`–`60`.
- A `queued_event_record` keeps FOUR distinct things apart: its `EventRef` (canonical six-field
  identity), its `dispatch_envelope` (five identity fields), its `immutable_payload` (the domain
  fields), and its descriptor-derived `stable_tie_key` (payload-derived, ordering only) — `61`–`63`.
- The `stable_tie_key` distinctness is reinforced by the AG8 "three identities are kept DISTINCT"
  statement at `86`–`88` and the ordering rule `stable_tie_key =
  descriptor(event_type).stable_tie_key(immutable_payload)` at `76`–`77`.
- The `queued_event_record` schema (the fifth named concept) is defined at `725`–`727`
  (`dispatch_envelope`, `immutable_payload` as separate members), consistent with §0.2.

All five named concepts are present and mutually distinct, and the six domain identifiers the
requirement enumerates are expressly assigned to immutable payload, not the dispatch envelope.

**Result: PASS.**

---

## Check AH9.5 — the stale "ProcessEventTime obtains RunContext through RoundContext.RunContext" note is REMOVED / superseded

**Requirement.** The AF-era note claiming `ProcessEventTime` obtains its `RunContext` via
`RoundContext.RunContext` must be removed/superseded; `ProcessEventTime` (and
`RunEventLoopToHorizon`) receive the `RunContext` directly.

**Evidence.** The `RunInitialise` NOTE at `2789`–`2793` states: "AH9: ProcessEventTime and
RunEventLoopToHorizon RECEIVE the RunContext DIRECTLY (AG3/AG5) — the stale AF-era note that
'ProcessEventTime obtains RunContext through RoundContext.RunContext' is REMOVED
(STAGE_01AH_SUPERSESSION_REGISTER.md)". It further clarifies (`2792`–`2793`) that a handler holding a
`RoundContext` may still reach its `RunContext` as `RoundContext.RunContext`, but the run/event
driver never depends on a `RoundContext` to obtain the `RunContext`. The stale claim survives ONLY as
the explicitly-marked REMOVED quotation, not as a live directive.

**Result: PASS.**

---

## Overall verdict

**OVERALL: PASS (after fold-back correction).**

Four of five checks passed on first inspection (AH2.1, AH9.3, AH9.4, AH9.5). One genuine defect was found and has
been FIXED in the final normative tree:

- `CloseRoundAtHorizon` previously placed `TRANSITION round_state -> ROUND_ABORTED` AFTER `CALL CloseRoundAssignments`,
  so the round was still nonterminal when `PublishTerminalRoundAndSeatNext`'s terminal ASSERT ran — contradicting that
  procedure's precondition and breaking the AH2 terminal-before-closure unification the other two paths satisfy
  (ValidBlockAccept transitions ROUND_ACCEPTED before closure; RoundAbort transitions ROUND_ABORTED before closure).
  **FIXED:** the horizon-end disposition record and the `TRANSITION round_state -> ROUND_ABORTED` are now placed BEFORE
  `CALL CloseRoundAssignments` in `CloseRoundAtHorizon`, mirroring the other two terminal paths; because the horizon
  close uses a RUN_HOOK envelope, `PublishTerminalRoundAndSeatNext` publishes the terminal state but seats no next round.
  All three terminal paths (ordinary acceptance, ordinary abort, horizon close) now transition to a terminal state
  BEFORE the closure/publication, so the ASSERT holds on every path and no bootstrap is seated while a predecessor is
  nonterminal.

The algorithm is **PoCol**, the mechanism is **the idle policy within PoCol**, and the A1 baseline
**`8.420833333 kWh`** is unchanged by this revision.
