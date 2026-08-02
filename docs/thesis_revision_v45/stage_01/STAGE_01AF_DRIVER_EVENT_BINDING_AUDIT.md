# Stage 1AF — Driver-Event Wrapper Binding Audit (AF4)

## Intro

This audit verifies correction **AF4** ("executable driver-event wrappers") of the Stage-1AF normative
revision. The six queued driver types whose domain procedures `ProcessEventTime` cannot supply with their
REAL inputs — because the domain procedure mints/derives an id, receives a `RunContext`, or needs the
`scheduling_context` wrapper — are dispatched through an **executable WRAPPER** rather than directly. The
wrappers audited are:

| Wrapper | Domain procedure |
|---------|------------------|
| `RoundInitialiseEvent` | `RoundInitialise` |
| `TemplateCommitEvent` | `TemplateCommit` |
| `MinerRegisterEvent` | `MinerRegister` |
| `PrepareParticipantsEvent` | `PrepareParticipantsForNewRound` |
| `ReserveActivateEvent` | `ReserveActivate` |
| `FullRangeExhaustEvent` | `FullRangeExhaustNoSolution` |

The algorithm under study remains **PoCol**; the mechanism under study is the **idle policy within PoCol**;
the **A1 baseline energy figure `8.420833333 kWh` is preserved and unchanged** by this documentation-only
revision (no executable source, configuration, DOCX, or PDF modified; no experiment re-run).

All line anchors below refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The primary artefacts inspected are the
`(0.7g-wrappers)` subsection (fenced block, lines 1023–1097), the `(0.7g-schema)` descriptor tables
(category-3 payload table lines 942–949; category-1/2 binding table lines 969–990), the `(0.7g-driver)`
seating table (lines 846–853), and the six domain-procedure `PROCEDURE` blocks
(`RoundInitialise` 2226, `TemplateCommit` 2367, `PrepareParticipantsForNewRound` 2392, `MinerRegister`
2985, `ReserveActivate` 4200, `FullRangeExhaustNoSolution` 5821).

## Verification criteria

1. **C1 — stores EXACTLY its descriptor payload** (wrapper `INPUTS` = declared `allowed_payload_keys` +
   declared runtime context; no missing, no extra payload key).
2. **C2 — receives its declared runtime context** (`RoundInitialiseEvent` = `RunContext` only, NOT
   `RoundContext`, NOT `dispatch_envelope`; `TemplateCommitEvent` = `RoundContext`;
   `MinerRegisterEvent` / `PrepareParticipantsEvent` / `ReserveActivateEvent` / `FullRangeExhaustEvent`
   = `RoundContext` + `dispatch_envelope`), matching descriptor `recv env` / `recv ref`.
3. **C3 — CALLs the domain procedure with the EXACT arguments the domain procedure declares.**
4. **C4 — INSPECTS the domain result and RETURNS its own disposition with a SOUND declared RETURNS
   union** (union covers every value the wrapper can actually return, including any propagated domain
   disposition and any stale-noop guard where present).
5. **C5 — exactly ONE `§0.7g` descriptor row matching its OWN inputs; no domain procedure listed as a
   queued handler** where `ProcessEventTime` cannot supply its real inputs.
6. **C6 — the domain procedure is reachable via a literal `CALL` inside the wrapper.**

## Per-wrapper result table

| Wrapper | C1 payload | C2 context | C3 CALL args | C4 disposition/union | C5 descriptor row | C6 literal CALL | Verdict |
|---------|:--:|:--:|:--:|:--:|:--:|:--:|:--:|
| `RoundInitialiseEvent` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `TemplateCommitEvent` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `MinerRegisterEvent` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `PrepareParticipantsEvent` | PASS | PASS | PASS | PASS (corrected) | PASS | PASS | **PASS** |
| `ReserveActivateEvent` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |
| `FullRangeExhaustEvent` | PASS | PASS | PASS | PASS | PASS | PASS | **PASS** |

## Per-wrapper evidence

### `RoundInitialiseEvent` — PASS

- **C1.** `INPUTS: RunContext, round_setup_seq` (line 1025). Descriptor `allowed_payload_keys =
  { round_setup_seq : Integer }` (line 944); binding row `payload_to_param_map` = "(none — `round_setup_seq`
  is the seat identity / idempotence key only)" (line 971). Payload key set matches EXACTLY; the sole
  payload key is stored, nothing extra.
- **C2.** Receives `RunContext` as runtime context (line 1025; `runtime_injected = RunContext -> RunContext`,
  line 971); descriptor `recv env = no`, `recv ref = no` (line 944) and precondition "recv env = no, recv
  ref = no" (line 1026). NOT `RoundContext`, NOT `dispatch_envelope`. `config`/`prior_state` are resolved
  from `RunContext` (AF6), never from payload: `SET config <- RunContext.config` (line 1031),
  `SET prior_state <- RunContext.prior_round_terminal_state` (line 1032).
- **C3.** `SET rc <- CALL RoundInitialise(config = config, RunContext = RunContext, prior_state = prior_state)`
  (line 1033). Domain `RoundInitialise INPUTS: config, RunContext, prior_state` (line 2227). Arguments match
  EXACTLY.
- **C4.** Inspects the returned `RoundContext` (domain `RETURNS: RoundContext(...)`, line 2279), publishes it
  (`SET RunContext.current_round_context <- rc`, line 1034), then `RETURN round_initialised(rc.RoundID)`
  (line 1035). Declared `RETURNS: round_initialised(RoundID)` (line 1036) — sound and complete. No stale-noop
  guard is required (this wrapper mints a fresh round at a fresh `event_time`; its payload carries no
  `RoundID_at_seat` staleness key).
- **C5.** Exactly one descriptor row, `RoundInitialiseEvent -> RoundInitialise` (line 944); `RoundInitialise`
  is NOT itself a queued handler. Seating row present (line 848).
- **C6.** Literal `CALL RoundInitialise(...)` at line 1033.

### `TemplateCommitEvent` — PASS

- **C1.** `INPUTS: RoundContext, RoundID_at_seat, candidate_template` (line 1039). Descriptor
  `allowed_payload_keys = { RoundID_at_seat : RoundID, candidate_template : CandidateTemplate }` (line 945).
  Payload key set (`RoundID_at_seat`, `candidate_template`) matches EXACTLY; `RoundContext` is context, not
  payload.
- **C2.** Receives `RoundContext` (`runtime_injected = RoundContext -> RoundContext`, line 972); descriptor
  `recv env = no`, `recv ref = no` (line 945; precondition line 1040). No `dispatch_envelope`.
- **C3.** `SET TemplateID <- CALL TemplateCommit(RoundContext, candidate_template = candidate_template)`
  (line 1044). Domain `TemplateCommit INPUTS: RoundContext, candidate_template` (line 2368). EXACT.
- **C4.** Stale-noop guard present: `IF RoundID_at_seat != RoundID_current: RETURN
  template_commit_stale_noop(RoundID_at_seat)` (lines 1042–1043). Otherwise mints and returns
  `template_committed(RoundID_current, TemplateID)` (line 1045; `TemplateID` derived, never payload).
  Declared `RETURNS: template_committed(RoundID, TemplateID) | template_commit_stale_noop(RoundID_at_seat)`
  (line 1046). Domain returns `TemplateID` (line 2376); wrapper wraps it. Union sound and complete.
- **C5.** One descriptor row `TemplateCommitEvent -> TemplateCommit` (line 945); `TemplateCommit` not queued
  directly. Seating row line 849.
- **C6.** Literal `CALL TemplateCommit(...)` at line 1044.

### `MinerRegisterEvent` — PASS

- **C1.** `INPUTS: RoundContext, join_request, dispatch_envelope` (line 1049). Descriptor
  `allowed_payload_keys = { join_request : JoinRequest }` (line 947). Sole payload key `join_request`
  matches EXACTLY; `RoundContext` and `dispatch_envelope` are runtime context.
- **C2.** Receives `RoundContext` + `dispatch_envelope` (binding row line 974); descriptor `recv env = yes`,
  `recv ref = no` (line 947; precondition line 1050).
- **C3.** `SET MinerID <- CALL MinerRegister(RoundContext, join_request = join_request, dispatch_envelope =
  dispatch_envelope)` (line 1052). Domain `MinerRegister INPUTS: RoundContext, join_request,
  dispatch_envelope` (line 2986). EXACT.
- **C4.** `RETURN miner_registered(MinerID)` (line 1053; `MinerID` derived, never payload). Domain returns
  `MinerID` (line 3004). Declared `RETURNS: miner_registered(MinerID)` (line 1054) — sound and complete. No
  stale-noop guard applicable (payload carries no `RoundID_at_seat`; the "round admits participation"
  precondition, line 1050, governs admissibility).
- **C5.** One descriptor row `MinerRegisterEvent -> MinerRegister` (line 947); `MinerRegister` not queued
  directly. Seating row line 851.
- **C6.** Literal `CALL MinerRegister(...)` at line 1052.

### `PrepareParticipantsEvent` — PASS (C4 defect corrected)

> **Correction applied.** The C4 defect identified by this audit was corrected in the final normative tree: the
> `PrepareParticipantsEvent` RETURNS union at line 1063 now enumerates every propagated domain disposition, including
> `participant_set_setup_retry_seated(SetupRetryID, reason)`, so the wrapper can no longer return a value it does not
> declare. The FAIL analysis below is retained as the record of the defect that was found and fixed.


- **C1 — PASS.** `INPUTS: RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` (line 1057).
  Descriptor `allowed_payload_keys = { RoundID_at_seat : RoundID, TemplateID_at_seat : TemplateID }`
  (line 946). Payload key set matches EXACTLY; `RoundContext` and `dispatch_envelope` are runtime context.
- **C2 — PASS.** Receives `RoundContext` + `dispatch_envelope` (binding row line 973); descriptor
  `recv env = yes`, `recv ref = no` (line 946; precondition line 1058).
- **C3 — PASS.** `RETURN CALL PrepareParticipantsForNewRound(RoundContext, dispatch_envelope =
  dispatch_envelope)` (line 1062). Domain `PrepareParticipantsForNewRound INPUTS: RoundContext,
  dispatch_envelope` (line 2393). Arguments match EXACTLY.
- **C4 — FAIL.** The wrapper propagates the domain disposition by a direct `RETURN CALL` (line 1062,
  comment "propagate the domain disposition"). The domain procedure declares
  **three** dispositions: `RETURNS: participant_set_prepared | participant_set_setup_retry_seated(SetupRetryID,
  reason) | round_aborted(abort_record)` (line 2522), and the retry-seating branch is reachable on the
  wrapper-dispatched first invocation (a `StartWake`/`CompleteAssignmentPhase` failure with a clean rollback,
  budget not exhausted, target within horizon seats a `SetupRetryEvent` and returns
  `participant_set_setup_retry_seated(srid, setup_reason)` — line 2519). The wrapper's declared union is
  `RETURNS: participant_set_prepared | round_aborted(abort_record) | participant_setup_stale_noop(RoundID_at_seat,
  TemplateID_at_seat)` (line 1063), which **omits the propagated disposition
  `participant_set_setup_retry_seated(SetupRetryID, reason)`**. The stale-noop guard itself is correct
  (lines 1060–1061). The defect is confined to the RETURNS union being **unsound (incomplete)**: the wrapper
  can return a value it does not declare.

  *Contrast with the two sibling wrappers that also propagate by `RETURN CALL`:* `ReserveActivateEvent`
  enumerates all three `ReserveActivate` dispositions plus its stale-noop (lines 1076–1079), and
  `FullRangeExhaustEvent` enumerates all four `FullRangeExhaustNoSolution` dispositions plus its stale-noop
  (lines 1089–1091). By the spec's own established pattern the analogous
  `participant_set_setup_retry_seated(SetupRetryID, reason)` must appear at line 1063.

  *Minimal remedy* (single-line edit to line 1063): add
  `| participant_set_setup_retry_seated(SetupRetryID, reason)` to the declared union.
- **C5 — PASS.** One descriptor row `PrepareParticipantsEvent -> PrepareParticipantsForNewRound` (line 946);
  `PrepareParticipantsForNewRound` is NOT queued directly. Seating row line 850.
- **C6 — PASS.** Literal `CALL PrepareParticipantsForNewRound(...)` at line 1062.

### `ReserveActivateEvent` — PASS

- **C1.** `INPUTS: RoundContext, RoundID_at_seat, deficit, activation_seq, dispatch_envelope` (line 1066).
  Descriptor `allowed_payload_keys = { RoundID_at_seat : RoundID, deficit : Rate, activation_seq : Integer }`
  (line 948). Payload key set matches EXACTLY; `RoundContext` and `dispatch_envelope` are runtime context.
- **C2.** Receives `RoundContext` + `dispatch_envelope` (binding row line 975); descriptor `recv env = yes`,
  `recv ref = no` (line 948; precondition line 1067).
- **C3.** Stale-guarded, then `RETURN CALL ReserveActivate(RoundContext, deficit = deficit,
  scheduling_context = ORDINARY_DISPATCH(dispatch_envelope))` (lines 1074–1075). Domain `ReserveActivate
  INPUTS: RoundContext, deficit, scheduling_context` (lines 4200–4204). EXACT — the wrapper builds the
  `SchedulingSourceContext` wrapper `ORDINARY_DISPATCH(dispatch_envelope)` (AF2), so a bare envelope never
  reaches `ReserveActivate`; the tie-key context keys `RoundID_at_seat` / `activation_seq` are correctly NOT
  passed as domain arguments (binding row line 975).
- **C4.** Stale-noop guard: `IF RoundID_at_seat != RoundID_current: RETURN
  reserve_activation_stale_noop(RoundID_at_seat)` (lines 1069–1070). Declared `RETURNS:
  reserve_activation_committed(...) | reserve_activation_failed_before_mutation(reason) |
  reserve_activation_failed_after_assignment(reason, AssignmentID, rollback_record) |
  reserve_activation_stale_noop(RoundID_at_seat)` (lines 1076–1079). Domain `RETURNS` is the first three
  (lines 4222–4224); the wrapper adds its own stale-noop. Union sound and complete.
- **C5.** One descriptor row `ReserveActivateEvent -> ReserveActivate` (line 948); `ReserveActivate` not
  queued directly. Seating row line 852.
- **C6.** Literal `CALL ReserveActivate(...)` at line 1074.

### `FullRangeExhaustEvent` — PASS

- **C1.** `INPUTS: RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` (line 1082).
  Descriptor `allowed_payload_keys = { RoundID_at_seat : RoundID, TemplateID_at_seat : TemplateID }`
  (line 949). Payload key set matches EXACTLY; `RoundContext` and `dispatch_envelope` are runtime context.
- **C2.** Receives `RoundContext` + `dispatch_envelope` (binding row line 976); descriptor `recv env = yes`,
  `recv ref = no` (line 949; precondition line 1083).
- **C3.** Stale-guarded, then `RETURN CALL FullRangeExhaustNoSolution(RoundContext, dispatch_envelope =
  dispatch_envelope)` (line 1088). Domain `FullRangeExhaustNoSolution INPUTS: RoundContext,
  dispatch_envelope` (line 5822). EXACT.
- **C4.** Stale-noop guard: `IF RoundID_at_seat != RoundID_current OR TemplateID_at_seat !=
  TemplateID_committed: RETURN range_exhaust_stale_noop(RoundID_at_seat, TemplateID_at_seat)`
  (lines 1086–1087). Declared `RETURNS: (FullRangeExhaustNoSolution disposition: new_TemplateID |
  template_refresh_retry_seated(SetupRetryID, reason) | template_refresh_retry_stale_noop(TemplateRefreshSetupID)
  | round_aborted(abort_record)) | range_exhaust_stale_noop(RoundID_at_seat, TemplateID_at_seat)`
  (lines 1089–1091). Domain `RETURNS` enumerates exactly those four propagated dispositions (line 5856); the
  wrapper adds its own stale-noop. Union sound and complete.
- **C5.** One descriptor row `FullRangeExhaustEvent -> FullRangeExhaustNoSolution` (line 949);
  `FullRangeExhaustNoSolution` not queued directly. Seating row line 853.
- **C6.** Literal `CALL FullRangeExhaustNoSolution(...)` at line 1088.

## Cross-cutting confirmations

- **No domain procedure appears as a queued handler.** The six domain procedures
  (`RoundInitialise`, `TemplateCommit`, `MinerRegister`, `PrepareParticipantsForNewRound`, `ReserveActivate`,
  `FullRangeExhaustNoSolution`) never appear as a `handler_procedure`; every category-3 row (lines 944–949)
  and every `(0.7g-driver)` seating row (lines 848–853) names the WRAPPER, satisfying the AF4 intent stated
  at lines 896–898 and the wrapper NOTE at lines 1092–1096. This closes the superseded AE4 defect in which
  those domain procedures were listed as queued handlers although `ProcessEventTime` could not supply their
  real inputs (lines 1019–1021).
- **`recv env` / `recv ref` agree end-to-end.** `RoundInitialiseEvent` and `TemplateCommitEvent` alone carry
  no `dispatch_envelope` (`recv env = no`, lines 944–945), consistent with their wrapper `INPUTS` and with
  the general `recv env = no` statement (line 1007); no wrapper declares `recv ref = yes` (that is
  `SetupRetryEvent` only, line 1006).
- **Each wrapper stores EXACTLY its descriptor payload (C1 across the set).** Every wrapper's payload-key set
  equals its descriptor's `allowed_payload_keys` with no missing and no extra key; minted/derived ids
  (`RoundID`, `TemplateID`, `MinerID`, reserve `MinerID`) are `derived_by_handler`, never payload
  (lines 944–949, category-4 column).

## Overall verdict

**PASS (after correction) — all six AF4 driver-event wrappers conform on all six criteria in the final tree.**
The audit initially found one genuine, narrowly-scoped defect in `PrepareParticipantsEvent` (criterion C4); that
defect was corrected in the final normative tree before this audit was finalised (see the correction note in the
`PrepareParticipantsEvent` section). All six wrappers (`RoundInitialiseEvent`, `TemplateCommitEvent`,
`MinerRegisterEvent`, `PrepareParticipantsEvent`, `ReserveActivateEvent`, `FullRangeExhaustEvent`) now: store exactly
their descriptor payload, receive exactly their declared runtime context, call their domain procedure with the exact
declared arguments via a literal `CALL`, inspect the result and return a SOUND disposition union (enumerating every
propagated domain disposition, with stale-noop guards where the payload carries a staleness key), and own exactly one
`§0.7g` descriptor row while the domain procedure is never listed as a queued handler.

**Defect found and fixed (record).** `PrepareParticipantsEvent`'s declared RETURNS union at line 1063 originally omitted
the reachable propagated disposition `participant_set_setup_retry_seated(SetupRetryID, reason)` (declared by the domain
procedure at line 2522, and enumerated by the two sibling propagating wrappers at lines 1076–1079 and 1089–1091). The
correction appended `| participant_set_setup_retry_seated(SetupRetryID, reason)` to the wrapper's RETURNS union, so the
wrapper can no longer return a value it does not declare. No other wrapper required a change.
