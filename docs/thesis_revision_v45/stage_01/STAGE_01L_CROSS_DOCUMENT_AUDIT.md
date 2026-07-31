# Stage 1L — Cross-Document Audit (acceptance gates)

The thirteen Stage-1L acceptance gates, verified by procedure-call-graph, event-envelope, and corpus
analysis over `docs/thesis_revision_v45/stage_01/` (not string search alone), plus cross-document
consistency and protected/historical-artifact verification. Name remains **PoCol**; mechanism is **the
idle policy within PoCol**; no property is claimed; the A1 baseline (`8.420833333 kWh`) is unchanged.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | No `ApplyMinerStateTransition` call omits `event_time`/`delta_cycle`/`event_seq` (semantically or syntactically) | **PASS** — §0.9 POSITIONAL SHORTHAND binds all three from `dispatch_envelope` (threaded parameter OR the equivalent `EQ.current_*` fields); driver calls (`StartWake`, `MinerRegister`) spell them out. `STAGE_01L_EVENT_ENVELOPE_AUDIT.md`; TV91 |
| 2 | One sanctioned envelope source; no manual seq stamp; no unsupported `driver_envelope` | **PASS** — `ProcessEventTime` materialises the ONE `dispatch_envelope` and sets `EQ.current_event_seq` (§0.7e); §0.7f withdraws the manual `next EQ.event_creation_seq` stamp; grep confirms 0 live `SET env <- DriverEventEnvelope` and 0 `driver_envelope =`. `STAGE_01L_EVENT_ENVELOPE_AUDIT.md`; TV91 |
| 3 | A single executable `ASSIGNMENT → HASHING` path through `CompleteAssignmentPhase` | **PASS** — `CompleteAssignmentPhase` (§2b) is the sole R4 owner; `PrepareParticipantsForNewRound` AND `TemplateRefresh` both `CALL CompleteAssignmentPhase`; the former in-line transition in `TemplateRefresh` is removed. `STAGE_01L_ASSIGNMENT_PHASE_UNIFICATION_AUDIT.md`; TV92 |
| 4 | The `SOLUTION_PROPAGATION → HASHING` re-entry is a distinct edge; every assignment-phase HASHING entry captures the census | **PASS** — the re-entry in `HandlePropagationFailure` is annotated NOT-R4 and is not routed through `CompleteAssignmentPhase`; `CompleteAssignmentPhase → CaptureSecurityCensusOnApplicabilityEntry` (K7) on every assignment-phase HASHING entry. `STAGE_01L_ASSIGNMENT_PHASE_UNIFICATION_AUDIT.md`; TV92 |
| 5 | One canonical discovery-before-lease-expiry order; no contradicting statement | **PASS** — discovery (item 7) precedes lease expiry (item 10) in §0.7, the §21 priority table, and the frozen `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4`; the contradicting §21 prose is removed. `STAGE_01L_EVENT_ORDER_AUDIT.md`; TV93 |
| 6 | `LeaseExpiry` is status-aware with one explicit disposition per status | **PASS** — §12 `SWITCH status(assignment)`: `SUPERSEDED`/`CLOSED` no-op; `CURRENT` renew-or-CLOSE; `PAUSED` CLOSE-without-wake; `PENDING` CLOSE. `STAGE_01L_LEASE_STATUS_AUDIT.md`; TV94/TV95 |
| 7 | Every reassignment CLOSES the source first; `RangeReassign` asserts `status(source) = CLOSED` | **PASS** — §12 common tail asserts `status(assignment) = CLOSED` before `RangeReassign`; §13 `RangeReassign` carries the precondition AND the `ASSERT status(source_assignment(unsearched_suffix)) = CLOSED`. `STAGE_01L_LEASE_STATUS_AUDIT.md`; TV94 |
| 8 | One idempotent cross-round residency owner; the two K3 procedures removed | **PASS** — §1a `RebaseResidencyAtRoundBoundary` defined (idempotent via `boundary_id`, per-run `rebased_boundaries`); `PROCEDURE FinalizeRoundResidency`/`BeginRoundResidency` no longer defined and have no call site. `STAGE_01L_RESIDENCY_BOUNDARY_AUDIT.md`; TV96 |
| 9 | `CloseRoundAssignments` records `round_terminal_time` only; idle interval counted once (I19); A1 unchanged | **PASS** — §17a `RECORD round_terminal_time(RoundID) <- now` and a NOTE that it performs no rebase; I19 amended; energy-model I5 cross-round paragraph; baseline `8.420833333 kWh` unchanged. `STAGE_01L_RESIDENCY_BOUNDARY_AUDIT.md`; TV96 |
| 10 | `ScheduleEvent` is the sole delta-cycle authority; `StartWake` schedules with only `event_time`+`microphase` | **PASS** — §0.7e strengthened; no `SCHEDULE`/`ScheduleEvent` caller supplies `delta_cycle`; `StartWake` (§0.10) schedules `WakeCompleteEvent` positive-latency `now + wake_latency` / zero-latency `now` at `WAKE_COMPLETE`. `STAGE_01L_SCHEDULER_CONFORMANCE_AUDIT.md`; TV97 |
| 11 | TV91 through TV97 pass on paper | **PASS** — `STAGE_01L_SEMANTIC_TEST_VECTORS.md`; every vector names exact procedures + preconditions; no unmodeled external action; A1 preserved |
| 12 | No executable source, configuration, DOCX, or PDF changes | **PASS** — `git diff` confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 13 | No Stage-1A..1K lettered artifact is modified | **PASS** — `git diff --name-only <base>` shows no `STAGE_01[A-K]_*` file; supersessions recorded in `STAGE_01L_SUPERSESSION_REGISTER.md`, not by rewriting prior evidence |

## Cross-document consistency

| Check | Result |
|-------|--------|
| Name always **PoCol**; mechanism only "the idle policy within PoCol" | **PASS** — 0 occurrences of any forbidden name string in the normative corpus |
| Envelope threading (pseudocode ↔ call graph) | **PASS** — `ProcessEventTime` materialises `dispatch_envelope`; every StartWake/driver transition binds it (L1) |
| Single ASSIGNMENT → HASHING (pseudocode ↔ round-SM) | **PASS** — both owners route through `CompleteAssignmentPhase`; re-entry edge distinct (L2) |
| Same-timestamp order (pseudocode ↔ G microphase spec) | **PASS** — discovery-before-lease-expiry consistent across §0.7, §21, and the frozen G spec (L3) |
| Status-aware lease + canonical terminal status | **PASS** — `LeaseExpiry` per-status; `RangeReassign` requires CLOSED source; `SUPERSEDED` renewal-only (L4/J7) |
| Single idempotent residency boundary owner | **PASS** — `RebaseResidencyAtRoundBoundary`; I19 + energy-model I5 updated; `ApplyMinerStateTransition` still sole interval owner (L5) |
| Sole delta-cycle authority | **PASS** — `ScheduleEvent` derives every `delta_cycle`; no caller override (L6/K8) |
| Invariant catalogue updated | **PASS** — I19 amended for the single idempotent boundary owner (L5) |
| Terminology addendum | **PASS** — Stage-1L addendum covers L1–L6; K3 rebase entry annotated superseded |
| Traceability updated | **PASS** — R77 updated to the L5 owner; R83–R88 (L1–L6) |
| Call graph has no dangling calls | **PASS** — 48 defined; 0 called-but-undefined (`STAGE_01L_PROCEDURE_CALL_GRAPH.md`) |
| A1 discipline | **PASS** — baseline `8.420833333 kWh` unchanged; the L5 rebase changes only how time is split across rounds, never the total |

## Supersession notes

All Stage-1L supersessions of prior-stage statements are recorded in
`STAGE_01L_SUPERSESSION_REGISTER.md` (6 entries) — historical `STAGE_01[A-K]_*` files are NOT modified.

## Git delta

Modified (5, all un-suffixed normative): `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
`STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_TRACEABILITY_MATRIX.csv`,
`STAGE_01_ENERGY_MODEL_SPECIFICATION.md`. Added (12): the `STAGE_01L_*` deliverables. No file outside
`docs/thesis_revision_v45/stage_01/` is touched; no `STAGE_01[A-K]_*` file is modified.

## Result

All thirteen acceptance gates pass and all cross-document consistency checks hold. The specification
conforms to L1–L6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9, I-01…I-08,
J1–J9, and K1–K8. Name remains PoCol; no new consensus feature; documentation only; protected drafts
byte-identical; Stage-1A–1K lettered artifacts frozen; A1 baseline unchanged.
