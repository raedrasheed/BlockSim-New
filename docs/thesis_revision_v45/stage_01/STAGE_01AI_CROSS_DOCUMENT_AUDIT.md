# Stage 1AI — Cross-Document Audit (25 acceptance gates)

This audit certifies, against the FINAL Stage-1AI normative tree, that the eight topical audits agree, that the five
modified `STAGE_01_*` documents are mutually consistent, and that every acceptance gate holds. It re-evaluates the tree only
AFTER every normative edit (AI1–AI9), every companion-document update, every semantic vector (TV313–TV324), and the
supersession register were complete. The algorithm is **PoCol**; the mechanism is the idle policy within PoCol; the A1
baseline (`8.420833333 kWh`) is preserved. This supersedes the Stage-1AH audits' gate marks for the contracts AI corrects
(`STAGE_01AI_SUPERSESSION_REGISTER.md`).

## 1. Topical-audit roll-up

| Topical audit | Correction | Verdict |
|---------------|-----------|---------|
| `STAGE_01AI_GENESIS_ADMISSION_TIMESTAMP_AUDIT.md` | AI1 | PASS |
| `STAGE_01AI_DRIVER_TIME_AUTHORITY_AUDIT.md` | AI2 | PASS |
| `STAGE_01AI_DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT.md` | AI3 / AI4 | PASS |
| `STAGE_01AI_DRIVER_ROUND_SCOPE_AUDIT.md` | AI5 | PASS |
| `STAGE_01AI_TERMINAL_PUBLICATION_RESULT_AUDIT.md` | AI6 | PASS |
| `STAGE_01AI_BARRIER_RESULT_PROPAGATION_AUDIT.md` | AI7 | PASS |
| `STAGE_01AI_ROTATION_SCHEDULING_ORIGIN_AUDIT.md` | AI8 | PASS |
| `STAGE_01AI_PROCEDURE_SIGNATURE_CALL_AUDIT.md` | signatures / RETURNS / call sites | PASS |

All eight topical audits report PASS (every item verified against the final tree with exact line anchors). No defect
required a fold-back: unlike Stage 1AH (three folded-back single-line corrections), the Stage-1AI edits were verified clean
on first audit. The call graph closes with 0 dangling references over 110 defined callables (108 `PROCEDURE` + 2 `FUNCTION`).

## 2. Acceptance gates

| # | Gate | Evidence | Verdict |
|---|------|----------|---------|
| 1 | Genesis `MINER_JOIN`s are SEATED in-dispatch at the non-finalised `t0` (ORDINARY_DISPATCH), never left for the post-finalisation outer loop → no `rejected_finalised_time` deadlock | `GENESIS_ADMISSION_TIMESTAMP_AUDIT`; TV313 | PASS |
| 2 | The initial-registration barrier still gates participant setup, so all genesis registrations execute BEFORE participant preparation | `GENESIS_ADMISSION_TIMESTAMP_AUDIT`; TV313 | PASS |
| 3 | Executable genesis invariant: no genesis request remains PENDING after its source timestamp is finalised; a failed genesis seat aborts the round with a declared disposition | `GENESIS_ADMISSION_TIMESTAMP_AUDIT`; TV313 | PASS |
| 4 | `RunContext.last_finalised_event_time` is the authoritative frontier, declared/initialised/returned, and advanced SOLELY by `ProcessEventTime` (and `FinalizeSimulationRunNoRound`) | `DRIVER_TIME_AUTHORITY_AUDIT`; TV314 | PASS |
| 5 | `AdmitDriverRequest` records a frontier-derived `driver_admission_time` (NOT a copy of `requested_event_time`) and rejects a requested time behind it | `DRIVER_TIME_AUTHORITY_AUDIT`; TV314 | PASS |
| 6 | `ScheduleEvent`'s DRIVER/TERMINAL_ROTATION cases reject context-identity / kind↔event_type / target-context / behind-frontier, with the four new result variants in RETURNS | `DRIVER_TIME_AUTHORITY_AUDIT`; TV315 | PASS |
| 7 | No DRIVER seat owner uses `source_event_time = requested_event_time`; the simulation never moves from a later processed time back to an earlier newly-admitted driver time | `DRIVER_TIME_AUTHORITY_AUDIT`; TV315 | PASS |
| 8 | `AdmitDriverRequest` derives a STABLE `logical_request_id` BEFORE minting a `DriverRequestID`; a replay returns `driver_request_already_admitted` with the SAME id and mints nothing new | `DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT`; TV316 | PASS |
| 9 | `SetDriverRequestStatus` is the single guarded mutator (legal-transition table; never SEATED-while-CONSUMED/CANCELLED); no other procedure writes `driver_request.status` | `DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT`; TV317 | PASS |
| 10 | The immutable reverse binding `driver_request_by_seat_event_ref` is published with the seat; `CompleteDriverRequestOnDispatch` drives SEATED→CONSUMED with the actual handler result (`consumed_result`) | `DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT`; TV318 | PASS |
| 11 | `CancelQueuedEvent` reconciles a cancelled driver seat to CANCELLED via the reverse binding; no seat lingers SEATED/PENDING | `DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT`; TV319 | PASS |
| 12 | Every `driver_request` carries a `DriverRoundScope`; a reserve activation is ALWAYS `EXACT_ROUND(RoundID_at_seat)` (structurally enforced at admission) | `DRIVER_ROUND_SCOPE_AUDIT`; TV320 | PASS |
| 13 | `SeatPendingDriverRequests` checks round state + scope (`SCOPE_ADMITS`) BEFORE seating; a stale `EXACT_ROUND` scope is REJECTED, never seated under a terminal/different round | `DRIVER_ROUND_SCOPE_AUDIT`; TV320 | PASS |
| 14 | `CloseRoundAssignments` CAPTURES + STORES the publication result in `RunContext.terminal_publication_result` and sets `NEXT_ROUND_BOOTSTRAP_FAILED` on a seat failure (never discarded) | `TERMINAL_PUBLICATION_RESULT_AUDIT`; TV321 | PASS |
| 15 | `RunEventLoopToHorizon` applies the deterministic terminate-partial policy (`run_completed_partial(next_round_bootstrap_failed)`) rather than spinning with no next round | `TERMINAL_PUBLICATION_RESULT_AUDIT`; TV321 | PASS |
| 16 | `ValidBlockAccept` / `RoundAbort` / `CloseRoundAtHorizon` inspect the captured closure disposition; a horizon close is always `terminal_round_published_no_seat` | `TERMINAL_PUBLICATION_RESULT_AUDIT`; TV321 | PASS |
| 17 | The barrier-completing `MinerRegister` inspects `SeatParticipantSetupOrAbort` and returns a distinct disposition; NO plain success after a participant-setup abort | `BARRIER_RESULT_PROPAGATION_AUDIT`; TV322 | PASS |
| 18 | `MinerRegisterEvent` propagates the disposition; the driver_request records the same final disposition as its `consumed_result` on dispatch | `BARRIER_RESULT_PROPAGATION_AUDIT`; TV322 | PASS |
| 19 | A distinct `TERMINAL_ROTATION(TerminalRotationSchedulingContext)` origin exists; the `SchedulingOrigin` union is four variants; the synchronous rotation seat is TERMINAL_ROTATION and the run-start seat is DRIVER(RUN_BOOTSTRAP) | `ROTATION_SCHEDULING_ORIGIN_AUDIT`; TV323 | PASS |
| 20 | Source classification matches the actual call stack; the predecessor is terminal before any next-round seat; rotation target strictly later; dc=0; no ambient `EQ.current_*` | `ROTATION_SCHEDULING_ORIGIN_AUDIT`; TV323 | PASS |
| 21 | Every AI-changed signature / RETURNS / call site is consistent; the call graph closes with 0 dangling references over 110 callables (`SetDriverRequestStatus`, `CompleteDriverRequestOnDispatch` added) | `PROCEDURE_SIGNATURE_CALL_AUDIT` + `STAGE_01AI_PROCEDURE_CALL_GRAPH.md` | PASS |
| 22 | TV313–TV324 pass on paper (12 vectors; each names only defined procedures/results) | `STAGE_01AI_SEMANTIC_TEST_VECTORS.md` | PASS |
| 23 | AI9 — the checksum manifest is a FULL `stage_01`-tree manifest, self-excluded, `LC_ALL=C`-sorted, covering every Stage-1A through Stage-1AI file except the manifest, verified twice | `STAGE_01AI_CHECKSUM_MANIFEST.sha256`; §3; TV324 | PASS |
| 24 | No executable source/config/DOCX/PDF change; no Stage-1A…1AH artifact modified; protected drafts byte-identical; no forbidden identifier; A1 present; PoCol naming | §3 below | PASS |
| 25 | AI10 supersession recorded (`STAGE_01AI_SUPERSESSION_REGISTER.md`); Stage 2 not begun | §3 below | PASS |

## 3. Scope & integrity verification

- **Protected drafts byte-identical** (unchanged):
  - `docs/Raed-Rasheed-draft-42-00.docx` = `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`
  - `docs/Raed-Rasheed-draft-42-00.pdf` = `131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`
  - `docs/Raed-Rasheed-draft-44-00.docx` = `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`
- **No forbidden identifier.** A word-bounded scan for model/vendor identifiers across every modified `STAGE_01_*` document
  and every `STAGE_01AI_*` deliverable returns no match.
- **A1 baseline** `8.420833333 kWh` present and unchanged (energy-model spec, unmodified); **PoCol** naming and the "idle
  policy within PoCol" mechanism unchanged.
- **Call graph** closes with 0 dangling references over 110 defined callables (`STAGE_01AI_PROCEDURE_CALL_GRAPH.md`).
- **Delta confined** to the five modified normative documents (`STAGE_01_PROTOCOL_PSEUDOCODE.md`,
  `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_INVARIANT_CATALOGUE.md`, `STAGE_01_TERMINOLOGY.md`,
  `STAGE_01_TRACEABILITY_MATRIX.csv`) and the fourteen new `STAGE_01AI_*` deliverables. No executable source,
  configuration, DOCX, or PDF was modified; no Stage-1A…1AH lettered artifact was modified; no experiment was run; Stage 2
  is not begun.
- **Manifest coverage profile (AI9).** `STAGE_01AI_CHECKSUM_MANIFEST.sha256` is a FULL `stage_01`-tree manifest — it covers
  EVERY file under `docs/thesis_revision_v45/stage_01/` (every Stage-1A through Stage-1AI artifact) EXCEPT the manifest
  itself, `LC_ALL=C`-sorted, and is verified twice. This is a deliberate change from the delta-only manifests of earlier
  stages (documented here and in `STAGE_01AI_SUPERSESSION_REGISTER.md`): a silently modified historical Stage-1A–1AH
  artifact would be detected by this full-tree manifest.

## 4. Overall verdict

**PASS — all 25 acceptance gates hold against the final Stage-1AI normative tree.** The genesis-admission,
driver-request-completion, and rotation-result contract (AI1–AI10) is realised faithfully; all eight topical audits PASS
(no fold-back required); the call graph closes with 0 dangling references over 110 callables; the companion documents are
mutually consistent; the protected drafts are byte-identical; and the A1 baseline and PoCol naming are preserved.
