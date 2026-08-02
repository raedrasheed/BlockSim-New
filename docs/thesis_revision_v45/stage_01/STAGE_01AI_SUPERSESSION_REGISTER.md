# Stage 1AI — Supersession Register (AI10)

This register records, per correction AI10, the SPECIFIC inaccurate claims of the (now frozen) Stage-1AH audits that
Stage 1AI supersedes. Stage-1A through Stage-1AH lettered artifacts are UNCHANGED on disk; this register is the
authoritative statement of which prior audit conclusions were reached on an inaccurate reading of the same contract and how
the Stage-1AI normative tree corrects them. The algorithm remains **PoCol**; the mechanism is the idle policy within PoCol;
the A1 baseline (`8.420833333 kWh`) is unchanged. Every Stage-1AI audit inspects the FINAL normative tree only AFTER every
normative edit (AI1–AI9), every companion-document update, and every semantic vector (TV313–TV324) were complete.

---

## 1. `STAGE_01AH_BOOTSTRAP_CHAIN_RESULT_AUDIT` — missed the finalised-time genesis-admission deadlock

- **Inaccurate claim.** The AH bootstrap-chain-result audit certified (gates 12–13) that first-round miner admission is not
  skipped — the genesis registry is imported and the initial-registration barrier gates participant setup — and marked the
  first-round admission path PASS.
- **Why it was wrong.** The AH design admitted the genesis `MINER_JOIN` `driver_request`s at the round-setup time `t0` but
  left them PENDING for the outer-loop `SeatPendingDriverRequests`, which runs only AFTER `ProcessEventTime(t0)` finalises
  `t0`. Every genesis `MinerRegisterEvent` therefore targeted `requested_event_time = t0`, which was by then in
  `finalised_event_times`, so `ScheduleEvent` returned `rejected_finalised_time` — the genesis registrations could NEVER be
  seated, and the round could never leave `TEMPLATE_COMMITMENT`. The audit verified the barrier's existence but not that the
  genesis registrations could actually be seated at a non-finalised time.
- **AI correction.** AI1 seats each genesis `MinerRegisterEvent` SYNCHRONOUSLY inside the dispatched `RoundInitialiseEvent`
  at the non-finalised `t0` (an `ORDINARY_DISPATCH` origin via `SeatMinerRegister(admission_mode = IN_DISPATCH_GENESIS)`),
  never leaving them for the post-finalisation intake. Verified by `STAGE_01AI_GENESIS_ADMISSION_TIMESTAMP_AUDIT.md`
  (TV313), including the executable genesis invariant.

## 2. `STAGE_01AH_DRIVER_REQUEST_LIFECYCLE_AUDIT` — treated SEATED as terminalisation; found no CONSUMED/CANCELLED producer

- **Inaccurate claim.** The AH driver-request-lifecycle audit certified (gate 10) that every sim-driver request is an
  explicit `driver_request` record with a 5-status lifecycle and that each seat result is inspected and "terminalised".
- **Why it was wrong.** The AH tree declared the statuses `{PENDING, SEATED, CONSUMED, REJECTED, CANCELLED}` but had NO
  producer of `CONSUMED` or a driver-request-level `CANCELLED`: a request was set `SEATED` and then never advanced when its
  seated event actually dispatched, and a cancelled seated event did not reconcile its `driver_request`. `SEATED` was
  effectively treated as terminal, so the declared lifecycle was not executable. There was no guarded mutator, no legal
  transition table, and no reverse binding from a seat `EventRef` back to its request.
- **AI correction.** AI4 adds the single guarded mutator `SetDriverRequestStatus` (declared legal-transition table;
  never SEATED-while-CONSUMED/CANCELLED), the immutable reverse binding `driver_request_by_seat_event_ref` published
  atomically with the seat, the dispatcher-owned completion owner `CompleteDriverRequestOnDispatch` (SEATED → CONSUMED with
  the actual handler result), and `CancelQueuedEvent` reconciliation (SEATED → CANCELLED). Verified by
  `STAGE_01AI_DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT.md` (TV317, TV318, TV319).

## 3. `STAGE_01AH_DRIVER_SCHEDULING_CONTEXT_AUDIT` — missed the source_event_time = requested_event_time self-validating copy

- **Inaccurate claim.** The AH driver-scheduling-context audit certified (gates 1–3) that a `DRIVER` seat carries an
  explicit `DriverSchedulingContext` and that `ScheduleEvent` derives `delta_cycle = 0` and requires `target ≥ source`.
- **Why it was wrong.** The AH seat owners built the context with `source_event_time = requested_event_time` — the source
  and target were the SAME value, so the `target ≥ source` check was self-validating (trivially true) and validated nothing
  about how far the simulation had actually advanced. There was no authoritative run-level time source; a stale or
  context-mismatched driver target could be admitted behind the simulation frontier.
- **AI correction.** AI2 adds `RunContext.last_finalised_event_time` (the authoritative frontier, advanced solely by
  `ProcessEventTime`); `AdmitDriverRequest` records a frontier-derived `driver_admission_time` (never a copy of the
  requested target); and `ScheduleEvent`'s `DRIVER`/`TERMINAL_ROTATION` cases reject a context-identity mismatch, a
  kind↔event_type mismatch, a target ≠ carried target, and a target behind the frontier. Verified by
  `STAGE_01AI_DRIVER_TIME_AUTHORITY_AUDIT.md` (TV314, TV315).

## 4. `STAGE_01AH_BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT` — did not test admission-level replay

- **Inaccurate claim.** The AH bootstrap-time-idempotence audit certified (gates 8–9) that a stable `BootstrapRequestID` /
  `DriverRequestID` is the replay key checked BEFORE any sequence is minted, and that a replay seats no second event.
- **Why it was wrong.** The AH replay guard operated only at the SEAT layer (`driver_event_seat` keyed by the
  `DriverRequestID`). But a `DriverRequestID` was minted fresh on EVERY `AdmitDriverRequest` call, so a replayed ADMISSION
  of the same logical request (the same external join / the same reserve deficit) produced a NEW `DriverRequestID` and a new
  record — a second logical request that would seat a second event. The audit tested seat-layer replay but not
  admission-layer replay.
- **AI correction.** AI3 derives a STABLE logical identity (`logical_request_id`) from the request's own content BEFORE the
  sequence advances, checks `driver_request_by_logical_id`, and returns `driver_request_already_admitted` with the SAME
  `DriverRequestID` on a replay. Verified by `STAGE_01AI_DRIVER_REQUEST_IDENTITY_LIFECYCLE_AUDIT.md` (TV316).

## 5. `STAGE_01AH_BOOTSTRAP_CHAIN_RESULT_AUDIT` — missed the bare SeatParticipantSetupOrAbort in MinerRegister

- **Inaccurate claim.** The AH bootstrap-chain-result audit certified (gate 14) that every bootstrap-chain seat result is
  inspected and turned into a declared disposition, and that no caller returns success after a required successor failed to
  seat.
- **Why it was wrong.** The barrier-completing `MinerRegister` CALLED `SeatParticipantSetupOrAbort` but DISCARDED its
  result and returned a plain `MinerID` regardless — so a participant-setup abort during the barrier-completing registration
  was hidden behind a plain `miner_registered` success. The one seat result on the registration path was not inspected.
- **AI correction.** AI7 makes `MinerRegister` inspect `SeatParticipantSetupOrAbort` and return a DISTINCT disposition
  (`miner_registered_barrier_pending` / `_participant_setup_seated` / `_already_seated` / `_participant_setup_aborted`); no
  plain success follows an abort, and the driver_request records the same final disposition. Verified by
  `STAGE_01AI_BARRIER_RESULT_PROPAGATION_AUDIT.md` (TV322).

## 6. `STAGE_01AH_RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT` — missed CloseRoundAssignments discarding the publication result

- **Inaccurate claim.** The AH runcontext-terminal-publication audit certified (gates 6–7) that ONE named owner
  `PublishTerminalRoundAndSeatNext` publishes the terminal round and seats the next bootstrap in the required order, and
  that a bootstrap is never seated while the predecessor is nonterminal.
- **Why it was wrong.** `PublishTerminalRoundAndSeatNext` returned a structured result including
  `terminal_round_published_seat_failed`, but its sole caller `CloseRoundAssignments` DISCARDED that result. A failed
  next-round bootstrap therefore never reached the run controller: the run would simply drain to the horizon with no next
  round and no declared disposition — the failure was silently swallowed. The audit verified the publication order but not
  that its result was consumed.
- **AI correction.** AI6 has `CloseRoundAssignments` capture the result, store it in
  `RunContext.terminal_publication_result`, and on a seat failure set the run-level `NEXT_ROUND_BOOTSTRAP_FAILED` state;
  `RunEventLoopToHorizon` terminates the run with a declared PARTIAL-RUN disposition; `ValidBlockAccept` / `RoundAbort` /
  `CloseRoundAtHorizon` inspect the captured disposition. Verified by `STAGE_01AI_TERMINAL_PUBLICATION_RESULT_AUDIT.md`
  (TV321).

## 7. `STAGE_01AH_DRIVER_SCHEDULING_CONTEXT_AUDIT` / round-rotation classification — the synchronous rotation seat was classified DRIVER

- **Inaccurate claim.** The AH driver-scheduling contract certified that the round-rotation next-bootstrap seat is a
  `DRIVER` sim-driver seat.
- **Why it was wrong.** `PublishTerminalRoundAndSeatNext` calls `SeatNextRoundBootstrap` SYNCHRONOUSLY from inside a
  terminal-publication path (`ValidBlockAccept` / `RoundAbort` — ordinary dispatched handlers). Classifying that seat as
  `DRIVER` (defined by AH1 as OUTSIDE any active ordinary dispatch) was untruthful: the source classification did not match
  the actual call stack.
- **AI correction.** AI8 (Option A) adds a distinct `TERMINAL_ROTATION(TerminalRotationSchedulingContext)` origin for the
  synchronous rotation seat and keeps the run-start seat a genuine outside-dispatch `DRIVER(RUN_BOOTSTRAP)` seat. Verified
  by `STAGE_01AI_ROTATION_SCHEDULING_ORIGIN_AUDIT.md` (TV323).

## 8. `STAGE_01AH_CROSS_DOCUMENT_AUDIT` — marked the affected gates PASS on the above inaccurate readings

- **Inaccurate claim.** The AH cross-document audit rolled up the eight AH topical audits and marked all 26 acceptance
  gates PASS against the "final Stage-1AH normative tree".
- **Why it was wrong.** Because the underlying topical audits (§§1–7 above) reached PASS on inaccurate readings of the
  genesis-admission, driver-request-lifecycle, driver-time, admission-replay, participant-setup-result, terminal-publication,
  and rotation-origin contracts, the AH cross-document roll-up inherited those inaccuracies — the gates it marked PASS
  (notably the AH analogues of first-round admission, driver-request lifecycle, driver scheduling, bootstrap idempotence,
  bootstrap-chain result, and terminal publication) did not hold as claimed. The AH semantic vectors TV301/TV302/TV303/
  TV304/TV305/TV306/TV312 exercised the same contracts on paper and inherited the same gaps.
- **AI correction.** The Stage-1AI cross-document audit (`STAGE_01AI_CROSS_DOCUMENT_AUDIT.md`) re-evaluates the FULL tree
  only after every AI edit and every AI vector (TV313–TV324) is complete; each AI topical audit inspects the final tree with
  exact line anchors.

---

## Scope of this supersession

- **What is superseded:** the SPECIFIC gate conclusions of the Stage-1AH audits enumerated above, to the extent they rest on
  the seven inaccurate readings AI1–AI8 correct. All OTHER Stage-1AH conclusions (AH1's explicit `SchedulingOrigin` union,
  AH2's per-round bootstrap target and single publication owner, AH7's generation-keyed acceptance registry, AH8's one
  ordering key, AH9's identity/payload distinctions) remain valid and are carried forward unchanged; Stage 1AI builds ON
  them.
- **What is NOT changed:** the Stage-1AH artifacts themselves (frozen on disk), the algorithm name (**PoCol**), the
  mechanism ("the idle policy within PoCol"), the A1 baseline (`8.420833333 kWh`), and every executable source /
  configuration / DOCX / PDF file. No experiment was run; Stage 2 is not begun.
