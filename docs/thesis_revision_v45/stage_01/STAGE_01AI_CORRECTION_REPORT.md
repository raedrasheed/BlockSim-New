# Stage 1AI — Correction Report (genesis-admission, driver-request-completion & rotation-result lock)

This report records the Stage-1AI documentation-only correction of the BlockSim/PoCol Stage-1 formal specification. It
fixes the ten defects an independent final-acceptance review found in the Stage-1AH driver machinery. The algorithm remains
**PoCol**; the mechanism is the idle policy within PoCol; the A1 baseline (`8.420833333 kWh`, in the unmodified energy-model
spec) is preserved. NO executable source, configuration, DOCX, or PDF file is modified; no experiment is run; no Stage-1A
through Stage-1AH artifact is modified; Stage 2 is not begun.

**Branch:** `thesis-v45-pocol-stage1ai-genesis-admission-driver-request-completion-rotation-result-lock`
**Base commit:** `6f502b0103857fa99c51b391d6c6916a8720a224` (the Stage-1AH commit).

## 1. What was wrong (the AH defects) and what AI does

| # | Defect (as found in the Stage-1AH tree) | Stage-1AI correction |
|---|------------------------------------------|----------------------|
| AI1 | Genesis `MINER_JOIN` requests were admitted at the round-setup time `t0` but seated only by the outer-loop intake, which runs AFTER `t0` is finalised → every genesis `MinerRegisterEvent` hit `rejected_finalised_time` (a deadlock: the round never left `TEMPLATE_COMMITMENT`). | The `RoundInitialiseEvent` handler seats each genesis `MinerRegisterEvent` SYNCHRONOUSLY inside its own dispatch at the non-finalised `t0` (an `ORDINARY_DISPATCH` origin via `SeatMinerRegister(admission_mode = IN_DISPATCH_GENESIS)`); the barrier still gates participant setup; a failed genesis seat aborts the round with a declared disposition. |
| AI2 | A driver seat used `source_event_time = requested_event_time` (source == target), a self-validating check; no authoritative run-level time, so a stale/mismatched target could be admitted behind the frontier. | `RunContext.last_finalised_event_time` (advanced solely by `ProcessEventTime`) is the authoritative frontier; `AdmitDriverRequest` records a frontier-derived `driver_admission_time`; `ScheduleEvent`'s `DRIVER`/`TERMINAL_ROTATION` cases reject context/kind/target mismatches and a target behind the frontier (four new results). |
| AI3 | A `DriverRequestID` was minted on every `AdmitDriverRequest`, so a replayed ADMISSION produced a second request/event. | `AdmitDriverRequest` derives a STABLE `logical_request_id` before minting; a replay returns `driver_request_already_admitted` with the SAME id and mints nothing new. |
| AI4 | The 5-status lifecycle was declared but had no `CONSUMED`/`CANCELLED` producer; `SEATED` was effectively terminal. | The single guarded mutator `SetDriverRequestStatus` (legal-transition table); the immutable reverse binding `driver_request_by_seat_event_ref`; the dispatcher-owned `CompleteDriverRequestOnDispatch` (`SEATED → CONSUMED` with the actual handler result); `CancelQueuedEvent` reconciliation (`SEATED → CANCELLED`). |
| AI5 | A `driver_request` had no round scope, so a stale request could execute against a different round. | Every `driver_request` carries a `DriverRoundScope`; a reserve activation is always `EXACT_ROUND`; `SeatPendingDriverRequests` checks round state + scope (`SCOPE_ADMITS`) and rejects a stale `EXACT_ROUND` scope rather than seating it under a terminal round. |
| AI6 | `CloseRoundAssignments` discarded `PublishTerminalRoundAndSeatNext`'s result, so a failed next-round bootstrap never reached the run controller. | `CloseRoundAssignments` captures + stores the result in `RunContext.terminal_publication_result`; a seat failure sets `NEXT_ROUND_BOOTSTRAP_FAILED`; `RunEventLoopToHorizon` terminates with a declared PARTIAL-RUN disposition; the three terminal paths inspect the captured disposition. |
| AI7 | The barrier-completing `MinerRegister` discarded `SeatParticipantSetupOrAbort`'s result, hiding a participant-setup abort behind a plain success. | `MinerRegister` inspects the result and returns a distinct disposition (`_barrier_pending` / `_participant_setup_seated` / `_already_seated` / `_participant_setup_aborted`); the driver_request records the same final disposition. |
| AI8 | The synchronous next-round bootstrap seated from inside a terminal-publication handler was classified `DRIVER` (defined as OUTSIDE dispatch) — an untruthful origin. | Option A: a distinct `TERMINAL_ROTATION(TerminalRotationSchedulingContext)` origin for the rotation seat; the run-start seat remains a genuine outside-dispatch `DRIVER(RUN_BOOTSTRAP)` seat. |
| AI9 | The checksum manifest covered only the stage delta, so a silently modified historical artifact would go undetected. | A FULL `stage_01`-tree manifest, self-excluded, `LC_ALL=C`-sorted, covering every Stage-1A through Stage-1AI file except the manifest, verified twice. |
| AI10 | The Stage-1AH audits marked the affected gates PASS on the above inaccurate readings. | `STAGE_01AI_SUPERSESSION_REGISTER.md` records each inaccurate AH audit claim and how AI corrects it. |

## 2. Delta

- **Five modified normative documents:** `STAGE_01_PROTOCOL_PSEUDOCODE.md` (AI1–AI8), `STAGE_01_ROUND_STATE_MACHINE.md`
  (§3.10m addendum), `STAGE_01_INVARIANT_CATALOGUE.md` (I16 + I21 Stage-1AI clauses), `STAGE_01_TERMINOLOGY.md` (Stage-1AI
  addendum), `STAGE_01_TRACEABILITY_MATRIX.csv` (rows R270–R280).
- **Fourteen new `STAGE_01AI_*` deliverables:** this correction report; eight topical audits
  (`GENESIS_ADMISSION_TIMESTAMP`, `DRIVER_TIME_AUTHORITY`, `DRIVER_REQUEST_IDENTITY_LIFECYCLE`, `DRIVER_ROUND_SCOPE`,
  `TERMINAL_PUBLICATION_RESULT`, `BARRIER_RESULT_PROPAGATION`, `ROTATION_SCHEDULING_ORIGIN`, `PROCEDURE_SIGNATURE_CALL`);
  the procedure call graph; the semantic test vectors (TV313–TV324); the supersession register; the cross-document audit;
  and the checksum manifest.
- **New callables (+2 over AH's 108 → 110):** `SetDriverRequestStatus`, `CompleteDriverRequestOnDispatch`. Call graph closes
  with 0 dangling references.

## 3. Integrity

- Protected drafts byte-identical (unchanged): `Raed-Rasheed-draft-42-00.docx`
  (`2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda`), `Raed-Rasheed-draft-42-00.pdf`
  (`131412bb2ce17ed97b98dfbefc136c7b5b226b9fd7372e79a25e4b0dc057e9c4`), `Raed-Rasheed-draft-44-00.docx`
  (`a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`).
- A1 baseline `8.420833333 kWh` present and unchanged (energy-model spec, unmodified). PoCol naming and the "idle policy
  within PoCol" mechanism unchanged. No forbidden model/vendor identifier appears in any modified or new file.
- Delta confined to the five modified `STAGE_01_*` documents and the fourteen new `STAGE_01AI_*` deliverables; no executable
  source, configuration, DOCX, or PDF modified; no Stage-1A through Stage-1AH lettered artifact modified; no experiment run;
  Stage 2 not begun.

## 4. Verdict

The genesis-admission, driver-request-completion, and rotation-result contract (AI1–AI10) is realised faithfully in the
final Stage-1AI normative tree; the eight topical audits and the cross-document audit certify it against the tree with exact
line anchors; the call graph closes with 0 dangling references over 110 callables; and the protected drafts, the A1
baseline, and the PoCol naming are preserved. See `STAGE_01AI_CROSS_DOCUMENT_AUDIT.md` for the acceptance-gate roll-up.
