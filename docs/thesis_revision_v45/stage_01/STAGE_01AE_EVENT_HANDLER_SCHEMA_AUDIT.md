# Stage 1AE — Event-Handler Dispatch-Schema Audit (AE4)

This audit verifies correction **AE4 — the authoritative event-type dispatch schema (§0.7g-schema)**: that the single
`§0.7g-schema` table declares, per queued event type, the handler procedure, the required `immutable_payload` fields,
whether the handler receives `dispatch_envelope` (`recv env`), whether it receives `dispatched_event_ref` (`recv ref`),
the target microphase, and the stable tie key; that it covers EVERY `ScheduleEvent` target and driver-entry queued event
type with no omission and no extra; and that every row's declared payload fields / `recv env` / `recv ref` agree with the
named handler's ACTUAL `PROCEDURE … INPUTS` declaration. The audit was generated AFTER the normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TERMINOLOGY.md`) and the Stage-1AE
semantic test vectors (`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, TV262–TV272) were final; it reads the after-final, frozen
source of truth read-only and modifies nothing. The A1 baseline `8.420833333 kWh` is preserved, and the binding PoCol
naming rule is preserved: the algorithm is **PoCol** and the mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`) — the pseudocode is a large file and content above the
audited regions may shift anchors slightly; every quotation is reproduced verbatim from the current normative text and the
content of each audited region was confirmed stable. The audit is corroborated throughout by **TV266** (§0.7g-schema
covers every target and matches every handler INPUTS, AE4; `STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, ~L51–L57) and its twin
**TV265** (`BlockAcceptancePoint` receives exactly its schema-declared arguments, AE4/AE5, ~L43–L49). The `§3.10i`
Stage-1AE addendum (AE4) is the round-state-machine statement of the same rule (`STAGE_01_ROUND_STATE_MACHINE.md`,
~L1050–L1053).

The schema table under audit is `(0.7g-schema) Authoritative event-type dispatch schema (AE4)`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L796 intro; header ~L807–L808; **21 data rows** ~L810–L830; post-table note
~L832–L837). The two enforcement sites are `ProcessEventTime` (AE5 dispatch, ~L245–L247) and `ScheduleEvent` (AE7
validation, ~L599–L610).

---

## Coverage — every queued event type against §0.7g-schema

The schema enumerates 21 queued event types. Every `CALL ScheduleEvent(EQ, RoundContext, <Type>)` seated target (11 call
sites, 10 distinct types) and every driver-entry queued type (`§0.7g-driver` seating table, 12 rows) appears in the
schema; the four remaining schema rows (`AcceptanceBatchFinalize`, `LeaseExpiry`, `AdversarialParticipationChangeEvent`,
`ActiveHashRateUpdate`) are seated by handler / model / monitoring paths and appear in both the schema and the `§0.7g`
canonical microphase map. The union is exactly the 21 schema rows — no queued type is missing and none is undeclared.

| Event type | In §0.7g-schema? | Handler INPUTS agree on payload / recv env / recv ref? |
|-----------|:--:|-------------------------------------------------------|
| `RoundInitialise` | yes (~L810) | **PASS** — env=no ✓ / ref=no ✓ (`RoundInitialise` INPUTS `config, RunContext, prior_state` ~L1945; no `dispatch_envelope`, no `dispatched_event_ref`). Payload `RoundID` is the driver-entry tie-key identity (`§0.7g-driver` tie key `(RoundID)` ~L759); the handler mints the fresh `RoundID`. |
| `TemplateCommit` | yes (~L811) | **PASS** — env=no ✓ / ref=no ✓ (INPUTS `RoundContext, candidate_template` ~L2085). Payload `RoundID, TemplateID` = identity (`RoundID` via `RoundContext`, `TemplateID` bound from `candidate_template`); tie key `(RoundID, TemplateID)`. |
| `PrepareParticipants` | yes (~L812) | **PASS** — env=yes ✓ / ref=no ✓ (`PrepareParticipantsForNewRound` INPUTS `RoundContext, dispatch_envelope` ~L2110). Payload `RoundID, TemplateID` = tie-key identity via `RoundContext`. |
| `MinerRegister` | yes (~L813) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, join_request, dispatch_envelope` ~L2703). Payload `MinerID` derived (`SET MinerID <- identifier for join_request`); tie key `(MinerID)`. |
| `ReserveActivate` | yes (~L814) | **PASS** — env=yes as `scheduling_context` ✓ / ref=no ✓ (INPUTS `RoundContext, deficit, scheduling_context` ~L3912; `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`, never bare). Payload `deficit` ✓. |
| `FullRangeExhaust` | yes (~L815) | **PASS** — env=yes ✓ / ref=no ✓ (`FullRangeExhaustNoSolution` INPUTS `RoundContext, dispatch_envelope` ~L5495). Payload `RoundID, TemplateID` = identity via `RoundContext`; tie key `(RoundID, TemplateID)`. |
| `HashWorkEvent` | yes (~L816) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `…, RoundID, TemplateID, cursor, dispatch_envelope`). Payload `MinerID, AssignmentID, assignment_version, RoundID, TemplateID, from_cursor`; the seat passes `from_cursor`. Field-set exact; the schema row now explicitly annotates that the handler binds `from_cursor` locally as `cursor`, so the payload key (schema + seat) and the handler binding are reconciled in the schema itself. |
| `CertificateArrival` | yes (~L817) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, recipient r, certificate, snapshot, CandidateID, PropagationID, dispatch_envelope` ~L5146). Payload `recipient, certificate, snapshot, CandidateID, PropagationID` ✓. |
| `BlockAcceptancePoint` | yes (~L818) | **PASS** — env=no ✓ / ref=no ✓ (INPUTS `RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` ~L5171; NO `dispatch_envelope`, NO `dispatched_event_ref`). Payload `certificate, snapshot, CandidateID, PropagationID, outcome` ✓. |
| `AcceptanceBatchFinalize` | yes (~L819) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, acceptance_timestamp, acceptance_point, dispatch_envelope` ~L5291). Payload `acceptance_timestamp, acceptance_point` ✓. Seated by `BlockAcceptancePoint` (~L5188). |
| `WakeCompleteEvent` | yes (~L820) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, MinerID, target_assignment, dispatch_envelope` ~L1727). Payload `MinerID, AssignmentID`; the seat passes `{MinerID, AssignmentID(target_assignment)}` (~L1690–L1692) — the seated key set equals the schema; `target_assignment` is the resolved binding of `AssignmentID`. |
| `ResumeFromPause` | yes (~L821) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id, dispatch_envelope` ~L4997). Payload `MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id` ✓. |
| `LeaseExpiry` | yes (~L822) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, assignment, time t, dispatch_envelope` ~L4669). Payload `assignment (AssignmentID, assignment_version), time t` ✓. |
| `AdversarialParticipationChangeEvent` | yes (~L823) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, MinerID, direction, dispatch_envelope`; `direction in {enter, exit}`). Payload `MinerID, direction` — the schema now names the field `direction`, matching the handler INPUT exactly (field-set exact, no naming variance). |
| `ActiveHashRateUpdate` | yes (~L824) | **PASS** — env=no ✓ / ref=no ✓ (INPUTS `RoundContext, time t` ~L3069; NO `dispatch_envelope`, NO `dispatched_event_ref`). Payload `time t` ✓. |
| `RecoveryDeadlineEvent` | yes (~L825) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, dispatch_envelope, RecoveryEpisodeID, RoundID_at_entry, TemplateID_at_entry, state_version_at_entry` ~L3638). Payload matches exactly. |
| `RecoveryCompletionDueEvent` | yes (~L826) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, RecoveryOutcome, RecoveryCensusVersion, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision` ~L4048). Payload matches exactly. |
| `RecoveryAssignmentContinuationDueEvent` | yes (~L827) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, ContinuationGeneration, RecoveryOutcome, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision` ~L4251). Payload matches exactly. |
| `RecoveryWorkDueEvent` | yes (~L828) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryWorkID, WorkGeneration, RecoveryWorkAction, RecoveryCensusVersion, RoundID_at_work, TemplateID_at_work, state_version_at_work` ~L3797). Payload matches exactly. |
| `SetupRetryEvent` | yes (~L829) | **PASS** — env=yes ✓ / **ref=yes ✓ (the ONLY row)** (INPUTS `RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` ~L2379). Payload (seven fields) matches exactly. |
| `RoundAbort` | yes (~L830) | **PASS** — env=yes ✓ / ref=no ✓ (INPUTS `RoundContext, reason, dispatch_envelope, recovery_finalising = false` ~L5754). Payload `RoundID` = identity via `RoundContext`; tie key `(RoundID)`. |

**Naming reconciliation (recorded; both resolved in the final tree, no FAIL).** Two rows initially carried a lexical
difference between the schema's `immutable_payload` key and the handler's local parameter name; the field-sets (arity,
identity, and the KEY actually seated by `ScheduleEvent`) agree one-to-one, and the final tree reconciles both:

- **N1 — `HashWorkEvent`.** The seat passes `from_cursor` (`ScheduleNextHashWork`), so the seated payload key matches the
  schema key `from_cursor` exactly; the handler binds it to the local `cursor`. The schema row now explicitly annotates
  "(the handler binds `from_cursor` locally as `cursor`)", so the binding is reconciled in the schema itself — no residual
  ambiguity.
- **N2 — `AdversarialParticipationChangeEvent`.** The schema now names the payload field `direction`, matching the handler
  INPUT parameter `direction` (`direction in {enter, exit}`) exactly — the field is fully aligned with no remaining naming
  variance.

---

## Checks (tied to TV266)

| Check | Result |
|-------|--------|
| **C1.** §0.7g-schema declares, per queued event type, the six attributes: handler procedure, required `immutable_payload` fields, `recv env`, `recv ref`, target microphase, stable tie key. | **PASS** — schema table columns `Event type / Handler procedure / Required immutable_payload fields / recv env / recv ref / Target microphase / Stable tie key` (~L807–L808) with 21 populated rows (~L810–L830). Matches AE4 (`STAGE_01_ROUND_STATE_MACHINE.md` §3.10i, ~L1050–L1053) and TV266 Expected (~L55–L57). |
| **C2.** Every `CALL ScheduleEvent(EQ, RoundContext, <Type>)` seated target appears in the schema. | **PASS** — 11 call sites (~L1690, ~L2220, ~L2831, ~L3365, ~L3612, ~L3767, ~L4225, ~L5105, ~L5118, ~L5230, ~L5721), 10 distinct types: `WakeCompleteEvent, SetupRetryEvent, HashWorkEvent, RecoveryDeadlineEvent, RecoveryCompletionDueEvent, RecoveryWorkDueEvent, RecoveryAssignmentContinuationDueEvent, CertificateArrival, BlockAcceptancePoint, ResumeFromPause` — each present in the schema. |
| **C3.** Every driver-entry queued type (`§0.7g-driver` seating table, 12 rows, ~L757–L770) appears in the schema. | **PASS** — `RoundInitialise, TemplateCommit, PrepareParticipants, MinerRegister, ReserveActivate, FullRangeExhaust, RecoveryDeadlineEvent, RecoveryCompletionDueEvent, RecoveryAssignmentContinuationDueEvent, RecoveryWorkDueEvent, SetupRetryEvent, RoundAbort` — each present in the schema. |
| **C4.** The four remaining schema types are genuine queued types and are covered; the schema has no omission and no extra (union = 21). | **PASS** — `AcceptanceBatchFinalize` (seated by `BlockAcceptancePoint`, ~L5188; schema ~L819), `LeaseExpiry` (~L822), `AdversarialParticipationChangeEvent` (~L823), `ActiveHashRateUpdate` (~L824) all appear in the schema and the §0.7g microphase map (~L703–L716). §0.7g-map (13) ∪ §0.7g-driver-only (7) ∪ `AcceptanceBatchFinalize` (1) = 21 = the schema rows. |
| **C5.** `SetupRetryEvent` is the ONLY row with `recv ref = yes`, and its INPUTS declare `dispatched_event_ref`. | **PASS** — schema `recv ref = **yes**` for `SetupRetryEvent` (~L829) and `no` for all other 20 rows; post-table note "`SetupRetryEvent` is the ONLY handler with `recv ref` = yes" (~L832). INPUTS declare `dispatched_event_ref` (~L2379). |
| **C6.** `BlockAcceptancePoint`, `RoundInitialise`, `TemplateCommit`, `ActiveHashRateUpdate` declare `recv env = no`, and their INPUTS omit `dispatch_envelope`. | **PASS** — schema `recv env = no` (~L810, L811, L818, L824); INPUTS omit `dispatch_envelope`: `BlockAcceptancePoint` (~L5171), `RoundInitialise` (~L1945), `TemplateCommit` (~L2085), `ActiveHashRateUpdate` (~L3069). Post-table note names exactly these four (~L833–L835). |
| **C7.** `ReserveActivate` receives the envelope wrapped as `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`, not a bare `dispatch_envelope`. | **PASS** — schema `recv env = yes (as scheduling_context)` (~L814); INPUTS `scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(dispatch_envelope)` (~L3912); narrative "the dispatcher supplies that wrapper, not a bare `dispatch_envelope`" (~L796–L797). |
| **C8.** `recv env` and `recv ref` of EVERY schema row match the named handler's INPUTS. | **PASS** — all 21 rows: `recv env` matches the presence/absence of a `dispatch_envelope` INPUT and `recv ref` matches the presence/absence of a `dispatched_event_ref` INPUT (see coverage table). 0 disagreement. Matches TV266 Expected (~L55–L57). |
| **C9.** The required `immutable_payload` field-set of EVERY row corresponds to the handler's INPUTS. | **PASS** — 21/21 field-sets correspond one-to-one; 20 rows match by name and the one remaining binding difference (N1 `HashWorkEvent` `from_cursor`, bound locally as `cursor`) is annotated in the schema row itself (N2 `AdversarialParticipationChangeEvent` now names the field `direction`, fully aligned). No missing, extra, or mistyped field on any row. |
| **C10.** `ScheduleEvent` validates `event_type` + `immutable_payload` against §0.7g-schema BEFORE any state mutation (AE7). | **PASS** — `ScheduleEvent` (~L599–L610): `SET missing_or_invalid_fields <- the required immutable_payload fields of event_type (per §0.7g-schema) that are ABSENT … OR fail their declared type`; `IF event_type is NOT declared in §0.7g-schema OR missing_or_invalid_fields is non-empty:` → `RETURN rejected_payload_schema_mismatch(event_type, missing_or_invalid_fields)   # AE7: STRUCTURED; NO state mutated yet`. Matches TV266 (payload validated against the row) and TV269 (~L79–L86). |
| **C11.** `ProcessEventTime` dispatches ONLY the arguments the schema declares (AE5 Design B). | **PASS** — `ProcessEventTime` (~L245–L247): `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, (AND dispatch_envelope = ctx.dispatch_envelope IFF §0.7g-schema[record.event_type].recv_env = yes), (AND dispatched_event_ref = ctx.dispatched_event_ref IFF §0.7g-schema[record.event_type].recv_ref = yes)`. Matches TV266 and TV265 (~L43–L49). |
| **C12.** The schema is the single source both enforcement sites reference, and the round-state machine states AE4 identically. | **PASS** — schema intro "the SINGLE authoritative schema … the source of truth that `ScheduleEvent` validates … and that `ProcessEventTime` uses to dispatch" (~L796–L798); §3.10i AE4 "§0.7g-schema declares, per queued event type, the handler, required `immutable_payload` fields … `ScheduleEvent` validates `immutable_payload` against this table; `ProcessEventTime` dispatches only the arguments it declares" (`STAGE_01_ROUND_STATE_MACHINE.md`, ~L1050–L1053). |

---

## Result

All twelve checks PASS and every one of the **21** `§0.7g-schema` rows agrees with its handler's declared `PROCEDURE …
INPUTS`. Coverage is complete and exact: every `ScheduleEvent(EQ, RoundContext, <Type>)` seated target and every
driver-entry queued type appears in the schema, the four handler/model/monitoring-seated types are present, and the union
of all seated queued types equals the 21 schema rows — no queued event type is missing and none is undeclared. On the
sharp AE5 attributes there is **no FAIL**: `recv env` and `recv ref` match the handler INPUTS on all 21 rows —
`SetupRetryEvent` is the sole `recv ref = yes` row and correctly declares `dispatched_event_ref`; `BlockAcceptancePoint`,
`RoundInitialise`, `TemplateCommit`, and `ActiveHashRateUpdate` declare `recv env = no` and omit `dispatch_envelope`; and
`ReserveActivate` receives the envelope only as the wrapped `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`,
never bare. Every required `immutable_payload` field-set corresponds one-to-one to the handler INPUTS; the two rows that
initially carried a parameter-name difference are reconciled in the final tree (N1 `HashWorkEvent`: the schema row now
annotates that `from_cursor` is bound locally as `cursor`, and the seated key equals the schema key; N2
`AdversarialParticipationChangeEvent`: the schema field is now named `direction`, matching the handler INPUT exactly), so no
schema/INPUTS disagreement remains. `ScheduleEvent`
validates `immutable_payload` against the table before any mutation (AE7) and `ProcessEventTime` dispatches only the
arguments the table declares (AE5), so the schema is genuinely the single dispatch authority TV266 requires. This is a
documentation-only audit: no source, config, DOCX, or PDF was modified, no experiment was run, the A1 baseline
`8.420833333 kWh` is preserved, and the algorithm remains **PoCol** with the idle policy within PoCol as the mechanism
under audit.
