# Stage 1AF — Event-Descriptor Audit (correction AF1)

## Intro

This audit verifies correction **AF1** of Stage 1AF: the replacement of the descriptive §0.7g event
schema by the SINGLE authoritative, EXECUTABLE `event_descriptor` set in `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(hereafter **PSEUDO**), together with the `§0.7g-driver` seating table that is a consistent VIEW of it.

- **State algorithm:** PoCol.
- **Mechanism under study:** the idle policy within PoCol.
- **A1 energy baseline:** `8.420833333 kWh` — preserved and unchanged by this documentation-only revision
  (`STAGE_01AF_CORRECTION_REPORT.md:6`). No executable source, configuration, DOCX, or PDF was modified.

Scope of the check: the `event_descriptor` STRUCTURE (PSEUDO:901–926); the "Descriptor core" table
(PSEUDO:942–963); the "Descriptor binding" table (PSEUDO:969–990); the "FIVE distinct categories" prose
(PSEUDO:928–937); the cancellation-identity prose (PSEUDO:992–998); the `RoundAbort is NOT a queued event`
note (PSEUDO:1000–1004); the `§0.7g-driver` seating table (PSEUDO:846–858) and its RoundAbort-exclusion note
(PSEUDO:860–863); and the declared `INPUTS` of every queued handler and AF4 wrapper.

Every line anchor below is into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless another file is named.

---

## Item 1 — Every queued event type has exactly one complete `event_descriptor`

The `event_descriptor` STRUCTURE (PSEUDO:901–926) declares all required fields: `event_type`,
`handler_procedure`, `allowed_payload_keys` (EXACT closed set), `payload_field_types`, `payload_to_param_map`,
`runtime_injected`, `derived_by_handler`, `target_microphase`, `stable_tie_key(record)`,
`cancellation_identity`, `recv_env`, `recv_ref`. The Descriptor-core table (PSEUDO:942–963) and the
Descriptor-binding table (PSEUDO:969–990) each carry the SAME 20 rows — one per queued event type — with no
duplicate and no omission.

| Required per-descriptor field | Where realised | Result |
|---|---|---|
| exact CLOSED `allowed_payload_keys` WITH declared types | core table col. 3, `key : type` form, e.g. PSEUDO:944–963; closed-set rule PSEUDO:905–906,939–940 | PASS |
| payload-key → handler-parameter mapping | binding table col. 2, PSEUDO:971–990 | PASS |
| runtime-injected parameters | binding table col. 3, PSEUDO:971–990; injected set enumerated PSEUDO:910–912 | PASS |
| `target_microphase` (FIXED) | core table col. 4, PSEUDO:944–963; reject-on-mismatch rule PSEUDO:916 | PASS |
| descriptor-derived `stable_tie_key` function | core table col. 5, PSEUDO:944–963; derivation rule PSEUDO:917–919 | PASS |
| cancellation identity | STRUCTURE field PSEUDO:920–922; universal `stored EventRef is the SOLE handle` rule + per-descriptor LOCATE keys PSEUDO:992–998 | PASS |
| `recv env` / `recv ref` flags | core table cols. 6–7, PSEUDO:944–963; semantics PSEUDO:923–925; summary PSEUDO:1006–1009 | PASS |

All 20 queued types (RoundInitialiseEvent, TemplateCommitEvent, PrepareParticipantsEvent, MinerRegisterEvent,
ReserveActivateEvent, FullRangeExhaustEvent, HashWorkEvent, CertificateArrival, BlockAcceptancePoint,
AcceptanceBatchFinalize, WakeCompleteEvent, ResumeFromPause, LeaseExpiry, AdversarialParticipationChangeEvent,
ActiveHashRateUpdate, RecoveryDeadlineEvent, RecoveryCompletionDueEvent, RecoveryAssignmentContinuationDueEvent,
RecoveryWorkDueEvent, SetupRetryEvent) appear exactly once in both tables. **Item 1: PASS.**

---

## Item 2 — The five categories are kept apart and never conflated

The prose at PSEUDO:928–937 defines the five categories and states the invariant explicitly (PSEUDO:936–937):
"A minted/derived id (RoundID, TemplateID, MinerID) or a tie-key value is NEVER counted as a handler payload
field." The structural test is: **no value listed in a descriptor's `derived_by_handler` (category 4) or in
its `stable_tie_key` tuple (category 5) also appears as an `allowed_payload_keys` key (category 3).**

| Category | Definition anchor | Held distinct? |
|---|---|---|
| (1) handler input parameters | PSEUDO:929–930 | PASS |
| (2) runtime context injected | PSEUDO:930–933 | PASS |
| (3) payload fields stored at seating | PSEUDO:933 | PASS |
| (4) values derived by the handler | PSEUDO:933–935 | PASS |
| (5) stable ordering keys | PSEUDO:935 | PASS |

Cross-check that no minted/derived id (category 4) leaks into a payload key set (category 3):

| Descriptor | `derived_by_handler` | `allowed_payload_keys` | Derived id in payload? |
|---|---|---|---|
| RoundInitialiseEvent (PSEUDO:944) | `RoundID` (minted) | `{round_setup_seq}` | No — RoundID absent |
| TemplateCommitEvent (PSEUDO:945) | `TemplateID` (minted) | `{RoundID_at_seat, candidate_template}` | No — TemplateID absent |
| MinerRegisterEvent (PSEUDO:947) | `MinerID` (derived) | `{join_request}` | No — MinerID absent |
| ReserveActivateEvent (PSEUDO:948) | reserve `MinerID` (SELECTed) | `{RoundID_at_seat, deficit, activation_seq}` | No — MinerID absent |
| HashWorkEvent (PSEUDO:950) | `assignment = version(...)` | `{MinerID, AssignmentID, assignment_version, RoundID, TemplateID, from_cursor}` | No — the derived value is `assignment`, absent from payload |
| WakeCompleteEvent (PSEUDO:954) | `target_assignment = version(...)` | `{MinerID, AssignmentID, assignment_version}` | No — target_assignment absent |
| LeaseExpiry (PSEUDO:956) | `assignment = version(...)` | `{AssignmentID, assignment_version, t}` | No — assignment absent |

Note on HashWorkEvent: `MinerID`/`RoundID`/`TemplateID` are pre-existing identity keys carried as the
work-unit identity/staleness guard, NOT ids minted or derived by this handler (its only category-4 value is
`assignment`); their presence in the payload therefore does not conflate categories 3 and 4. Likewise the
`stable_tie_key` tuples are FUNCTIONS of payload keys (e.g. `(round_setup_seq)`, `(MinerID, AssignmentID,
assignment_version)`) — no tie-key VALUE is itself stored as a separate payload field. **Item 2: PASS.**

---

## Item 3 — The corrected rows are correct

| Corrected row | Required content | Evidence | Result |
|---|---|---|---|
| RoundInitialiseEvent | payload `{round_setup_seq}`; RoundID minted/derived, not payload | core row PSEUDO:944 (`{round_setup_seq : Integer}`, derived `RoundID (minted)`); binding PSEUDO:971 (payload-to-param none; RunContext injected, config/prior_state resolved); wrapper INPUTS PSEUDO:1025; RoundID minted in domain `RoundInitialise` PSEUDO:2231 | PASS |
| TemplateCommitEvent | payload includes `candidate_template`; TemplateID minted/derived | core row PSEUDO:945 (`candidate_template : CandidateTemplate`, derived `TemplateID (minted from candidate_template)`); binding PSEUDO:972 (`candidate_template -> candidate_template`); wrapper INPUTS PSEUDO:1039; TemplateID minted in domain `TemplateCommit` PSEUDO:2371 | PASS |
| MinerRegisterEvent | payload `{join_request}`; MinerID derived | core row PSEUDO:947 (`{join_request : JoinRequest}`, derived `MinerID (derived from join_request)`); binding PSEUDO:974 (`join_request -> join_request`); wrapper INPUTS PSEUDO:1049; MinerID derived in domain `MinerRegister` PSEUDO:2992 | PASS |
| WakeCompleteEvent | payload gains `assignment_version`; `target_assignment` derived by `version(...)` | core row PSEUDO:954 (`{MinerID, AssignmentID, assignment_version}`, derived `target_assignment = version(AssignmentID, assignment_version)`); binding PSEUDO:981 (`(AssignmentID, assignment_version) -> target_assignment via version(...)`); handler INPUTS declare `target_assignment` PSEUDO:1988 | PASS |
| ReserveActivateEvent | payload `{RoundID_at_seat, deficit, activation_seq}`; receives a `scheduling_context` wrapper | core row PSEUDO:948; binding PSEUDO:975 (`deficit -> deficit`; wrapper builds `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`); wrapper INPUTS PSEUDO:1066 and wrapper call PSEUDO:1074–1075; domain `ReserveActivate` INPUTS declare `scheduling_context` (not a bare envelope) PSEUDO:4201–4204 | PASS |

**Item 3: PASS.**

---

## Item 4 — RoundAbort is removed from the queued descriptor set AND the driver-seating table

| Check | Evidence | Result |
|---|---|---|
| No `event_descriptor` row for RoundAbort in the Descriptor-core / binding tables | RoundAbort absent from PSEUDO:942–963 and PSEUDO:969–990 | PASS |
| Explicit "RoundAbort is NOT a queued event" note | PSEUDO:1000–1004 (SYNCHRONOUS-only; no descriptor; `TERMINAL_ABORT` §21 ordinal retained as priority slot only, not a seated microphase) | PASS |
| RoundAbort absent from the §0.7g-driver seating table | seating table PSEUDO:846–858 (no RoundAbort row); explicit exclusion PSEUDO:860–863 | PASS |
| No `ScheduleEvent(EQ, RoundContext, RoundAbort, …)` seat exists | repository-wide search for `ScheduleEvent(…RoundAbort` returns zero matches; every RoundAbort reference is a synchronous `CALL RoundAbort(...)` (e.g. PSEUDO:2487, 2739, 4465, 5848); confirmed in-text at PSEUDO:861–862 | PASS |

**Item 4: PASS.**

---

## Item 5 — Each descriptor row's payload→param + runtime-injected matches the handler's declared INPUTS exactly

For every queued handler the union of (a) `payload_to_param_map` targets and (b) `runtime_injected`
parameters equals the handler's declared `INPUTS`; descriptor-derived values are computed inside the handler
and never appear as inputs (except where a resolver mints an input, e.g. `target_assignment`/`assignment`).

| Event type / handler | Declared INPUTS (anchor) | Descriptor payload→param + runtime-injected (anchors) | Match |
|---|---|---|---|
| RoundInitialiseEvent (wrapper) | `RunContext, round_setup_seq` (1025) | payload none (round_setup_seq = seat identity/tie key); inject RunContext, resolve config/prior_state from RunContext (944, 971) | PASS |
| TemplateCommitEvent (wrapper) | `RoundContext, RoundID_at_seat, candidate_template` (1039) | `candidate_template -> candidate_template`; RoundContext; RoundID_at_seat = staleness/tie-key (945, 972) | PASS |
| PrepareParticipantsEvent (wrapper) | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` (1057) | payload none (RoundID/TemplateID_at_seat = staleness/tie-key); RoundContext, dispatch_envelope (946, 973) | PASS |
| MinerRegisterEvent (wrapper) | `RoundContext, join_request, dispatch_envelope` (1049) | `join_request -> join_request`; RoundContext, dispatch_envelope (947, 974) | PASS |
| ReserveActivateEvent (wrapper) | `RoundContext, RoundID_at_seat, deficit, activation_seq, dispatch_envelope` (1066) | `deficit -> deficit`; RoundContext, dispatch_envelope; wrapper builds scheduling_context (948, 975) | PASS |
| FullRangeExhaustEvent (wrapper) | `RoundContext, RoundID_at_seat, TemplateID_at_seat, dispatch_envelope` (1082) | payload none (staleness/tie-key); RoundContext, dispatch_envelope (949, 976) | PASS |
| HashWorkEvent | `RoundContext, MinerID, AssignmentID, assignment_version, RoundID, TemplateID, cursor, dispatch_envelope` (3127) | `MinerID/AssignmentID/assignment_version/RoundID/TemplateID` identity, `from_cursor -> cursor`; RoundContext, dispatch_envelope; `assignment` derived (950, 977, 3132) | PASS |
| CertificateArrival | `RoundContext, recipient r, certificate, snapshot, CandidateID, PropagationID, dispatch_envelope` (5435) | `recipient -> r`, certificate/snapshot/CandidateID/PropagationID; RoundContext, dispatch_envelope (951, 978) | PASS |
| BlockAcceptancePoint | `RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` (5460) — NO envelope | certificate/snapshot/CandidateID/PropagationID/outcome; RoundContext only, recv env = **no** (952, 979) | PASS |
| AcceptanceBatchFinalize | `RoundContext, acceptance_timestamp, acceptance_point, dispatch_envelope` (5618) | acceptance_timestamp/acceptance_point; RoundContext, dispatch_envelope (953, 980) | PASS |
| WakeCompleteEvent | `RoundContext, MinerID, target_assignment, dispatch_envelope` (1988) | `MinerID -> MinerID`, `(AssignmentID, assignment_version) -> target_assignment via version(...)`; RoundContext, dispatch_envelope (954, 981) | PASS |
| ResumeFromPause | `RoundContext, MinerID, trigger, pause_cause_candidate_id, pause_cause_propagation_id, dispatch_envelope` (5286) | all four payload keys → same-named params; RoundContext, dispatch_envelope (955, 982) | PASS |
| LeaseExpiry | `RoundContext, assignment, t, dispatch_envelope` (4958) | `(AssignmentID, assignment_version) -> assignment via version(...)`, `t -> t`; RoundContext, dispatch_envelope (956, 983) | PASS |
| AdversarialParticipationChangeEvent | `RoundContext, MinerID, direction, dispatch_envelope` (3383) | `MinerID -> MinerID`, `direction -> direction`; RoundContext, dispatch_envelope (957, 984) | PASS |
| ActiveHashRateUpdate | `RoundContext, t` (3358) — NO envelope | `t -> t`; RoundContext only, recv env = **no** (958, 985) | PASS |
| RecoveryDeadlineEvent | `RoundContext, dispatch_envelope, RecoveryEpisodeID, RoundID_at_entry, TemplateID_at_entry, state_version_at_entry` (3927–3928) | four payload keys → same-named params; RoundContext, dispatch_envelope (959, 986) | PASS |
| RecoveryCompletionDueEvent | `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, RecoveryOutcome, RecoveryCensusVersion, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision` (4337–4338) | each payload key → same-named param; RoundContext, dispatch_envelope (960, 987) | PASS |
| RecoveryAssignmentContinuationDueEvent | `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryDecisionID, ContinuationGeneration, RecoveryOutcome, RoundID_at_decision, TemplateID_at_decision, state_version_at_decision` (4540–4541) | each payload key → same-named param; RoundContext, dispatch_envelope (961, 988) | PASS |
| RecoveryWorkDueEvent | `RoundContext, dispatch_envelope, RecoveryEpisodeID, RecoveryWorkID, WorkGeneration, RecoveryWorkAction, RecoveryCensusVersion, RoundID_at_work, TemplateID_at_work, state_version_at_work` (4086–4087) | each payload key → same-named param; RoundContext, dispatch_envelope (962, 989) | PASS |
| SetupRetryEvent | `RoundContext, dispatch_envelope, dispatched_event_ref, RoundID, setup_kind, SetupRetryID, TemplateID_at_seat, TemplateRefreshSetupID, retry_generation, reason` (2662–2666) | each payload key → same-named param; RoundContext, dispatch_envelope, `dispatched_event_ref <- ctx.dispatched_event_ref`, recv ref = **yes** (963, 990) | PASS |

Domain-procedure INPUTS reached through the AF4 wrappers also agree: `RoundInitialise`
(`config, RunContext, prior_state`, 2227), `TemplateCommit` (`RoundContext, candidate_template`, 2368),
`MinerRegister` (`RoundContext, join_request, dispatch_envelope`, 2986), `PrepareParticipantsForNewRound`
(`RoundContext, dispatch_envelope`, 2393), `ReserveActivate` (`RoundContext, deficit, scheduling_context`,
4201–4204), `FullRangeExhaustNoSolution` (`RoundContext, dispatch_envelope`, 5822) — each supplied by its
wrapper with exactly the named arguments (PSEUDO:1024–1097).

The two `recv env = no` descriptors (BlockAcceptancePoint PSEUDO:952/979; ActiveHashRateUpdate
PSEUDO:958/985) declare no `dispatch_envelope` input, and the sole `recv ref = yes` descriptor (SetupRetryEvent
PSEUDO:963/990) is the only handler declaring `dispatched_event_ref` — consistent with the summary at
PSEUDO:1006–1009. **Item 5: PASS.**

---

## Overall verdict

| Item | Subject | Result |
|---|---|---|
| 1 | One complete `event_descriptor` per queued type (all required fields) | PASS |
| 2 | Five categories kept apart; no minted/derived id or tie-key value as payload | PASS |
| 3 | Corrected rows (RoundInitialise / TemplateCommit / MinerRegister / WakeComplete / ReserveActivate) | PASS |
| 4 | RoundAbort removed from queued schema and driver-seating table; no seat exists | PASS |
| 5 | Descriptor payload→param + runtime-injected matches every handler's declared INPUTS | PASS |

**OVERALL: PASS.** Correction AF1 is realised faithfully in the normative tree. The §0.7g-schema defines
exactly one complete, executable `event_descriptor` for each of the 20 queued event types with closed typed
payload sets, payload→parameter mappings, runtime-injected parameters, fixed target microphases,
descriptor-derived stable tie keys, cancellation identities, and `recv env`/`recv ref` flags; the five
categories are held strictly apart; the five corrected rows are correct; `RoundAbort` is synchronous-only with
no descriptor and no `ScheduleEvent` seat; and every descriptor row agrees exactly with its handler's declared
INPUTS. No defect was found. The PoCol state algorithm and the A1 baseline `8.420833333 kWh` are unaffected.
