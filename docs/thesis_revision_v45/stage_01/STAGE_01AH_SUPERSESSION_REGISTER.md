# Stage 1AH — Supersession Register (AH10)

This register records, per correction AH10, the SPECIFIC inaccurate claims of the (now frozen) Stage-1AG audits that
Stage 1AH supersedes. Stage-1A through Stage-1AG lettered artifacts are UNCHANGED on disk; this register is the
authoritative statement of which prior audit conclusions were reached on an inaccurate reading of the same contract and how
the Stage-1AH normative tree corrects them. The algorithm remains **PoCol**; the mechanism is the idle policy within PoCol;
the A1 baseline (`8.420833333 kWh`) is unchanged. Every Stage-1AH audit inspects the FINAL normative tree only AFTER every
normative edit (AH1–AH9) and every semantic vector (TV299–TV312) was complete.

---

## 1. `STAGE_01AG_RUN_BOOTSTRAP_AUDIT` — did not verify the ScheduleEvent driver-source contract or the fixed-past bootstrap time

- **Inaccurate claim.** The AG run-bootstrap audit certified that the first-round bootstrap is executable and the round
  bootstrap is correctly seated.
- **Why it was wrong.** (a) `SeatNextRoundBootstrap` seated `RoundInitialiseEvent` at `RunContext.round_bootstrap_time =
  config.run_start_time` for EVERY round — a subsequent round's bootstrap would target `run_start_time`, which is in the
  past, so `ScheduleEvent` would reject it `rejected_backward_time` (or `rejected_finalised_time`). (b) The seat relied on
  ambient `EQ.current_*` for the delta-cycle derivation even though a bootstrap runs OUTSIDE any active ordinary dispatch
  (at run start `EQ.current_*` is unset; at rotation it is cleared) — the audit never verified a driver-source scheduling
  contract.
- **AH correction.** AH2 removes `round_bootstrap_time`; each round's bootstrap targets its own
  `BootstrapRequest.target_time` (`run_start_time` first, `next_representable_simulation_time(prior terminal)` after). AH1
  makes the seat a `DRIVER` origin that derives `delta_cycle = 0` from the request (no `EQ.current_*`). Verified by
  `STAGE_01AH_BOOTSTRAP_TIME_IDEMPOTENCE_AUDIT.md` and `STAGE_01AH_DRIVER_SCHEDULING_CONTEXT_AUDIT.md` (TV300, TV301).

## 2. `STAGE_01AG_DRIVER_EVENT_SEATING_AUDIT` — proved only syntactic CALL reachability

- **Inaccurate claim.** The AG driver-event-seating audit certified that every driver wrapper has an executable seating
  path.
- **Why it was wrong.** It proved only that a literal `CALL <SeatOwner>` exists — syntactic reachability. It did NOT verify
  (i) that a driver request is actually PRODUCED and CONSUMED (the AG bare pending sets had no producer/lifecycle), (ii) the
  replay identity (a fresh `activation_seq` was minted BEFORE the replay check in `SeatReserveActivate`, so a replay would
  seat a second activation), (iii) a valid driver scheduling context, or (iv) that the seat result was handled.
- **AH correction.** AH4 makes every sim-driver request an explicit `driver_request` record with a named producer
  (`AdmitDriverRequest`) and a lifecycle (`SeatPendingDriverRequests` inspects + terminalises each). AH3 checks the stable
  `DriverRequestID` / `BootstrapRequestID` BEFORE minting any sequence. AH1 supplies an explicit `DRIVER` context. AH6
  inspects every seat result. Verified by `STAGE_01AH_DRIVER_REQUEST_LIFECYCLE_AUDIT.md` and
  `STAGE_01AH_BOOTSTRAP_CHAIN_RESULT_AUDIT.md` (TV304, TV305, TV306, TV308, TV309).

## 3. `STAGE_01AG_ROUND_CONTEXT_ROTATION_AUDIT` — missed the next bootstrap scheduled at run_start_time

- **Inaccurate claim.** The AG round-context-rotation audit certified that a round rotation publishes the prior terminal
  round and seats the next round correctly.
- **Why it was wrong.** It verified that `prior_round_terminal_state` is published, but did not check the next bootstrap's
  TARGET TIME — which was the fixed `run_start_time` (item 1), so a real second round could never be seated. It also did not
  check that the predecessor round is terminal BEFORE the seat (`RoundAbort` transitioned to `ROUND_ABORTED` AFTER
  `CloseRoundAssignments` seated the next bootstrap, so the seat happened while the predecessor was nonterminal).
- **AH correction.** AH2 introduces the one named terminal-round publication owner `PublishTerminalRoundAndSeatNext` with a
  required order and a per-round target time, and moves the `ROUND_ABORTED` transition BEFORE closure so the predecessor is
  terminal first. Verified by `STAGE_01AH_RUNCONTEXT_TERMINAL_PUBLICATION_AUDIT.md` (TV301, TV302).

## 4. `STAGE_01AG_ACCEPTANCE_BATCH_CONTEXT_AUDIT` — missed the record-vs-EventRef cancellation defect and the failed-candidate active-set inconsistency

- **Inaccurate claim.** The AG acceptance-batch-context audit certified that the acceptance-batch seat context is
  type-correct and every seat result is handled with no stranded batch.
- **Why it was wrong.** (a) The finalize-seat-failure path in `BlockAcceptancePoint` set `status(context(CandidateID)) <-
  FAILED` but did NOT remove the candidate from `active_propagation_set` — a `FAILED` candidate left in the propagation-active
  set (violating the §0.6 membership definition). (b) `RoundAbort` called `CancelQueuedEvent(acceptance_batch_finalize_seat[key],
  ...)` passing the whole `{ generation, EventRef }` record where a `CancelQueuedEvent` handle (an `EventRef`) was required —
  a type error.
- **AH correction.** AH7 routes the finalize-seat failure through the single candidate-failure owner
  `HandlePropagationFailure` (FAILED + removed from `active_propagation_set` + events cancelled + paused miners resumed),
  gives `BlockAcceptancePoint` its own `dispatch_envelope` (recv env = yes), makes every closure path cancel
  `acceptance_batch_finalize_seat[key].EventRef`, and states the generation-keyed `acceptance_batch_registry` in the core
  data model. Verified by `STAGE_01AH_ACCEPTANCE_GENERATION_LIFECYCLE_AUDIT.md` (TV310, TV311).

## 5. `STAGE_01AG_EVENT_ORDERING_CONSISTENCY_AUDIT` — excluded the surviving positive four-field generic rule

- **Inaccurate claim.** The AG event-ordering-consistency audit certified that the descriptor-derived `stable_tie_key` is the
  one authoritative ordering rule everywhere and the universal tuple is withdrawn.
- **Why it was wrong.** Its scan classified the 3-field `(CandidateID, MinerID, AssignmentID)` string but did NOT catch the
  surviving POSITIVE 4-field `(CandidateID, MinerID, AssignmentID, seq)` rule asserted in §0.7-H2 ("within a microphase, ties
  break by (CandidateID, MinerID, AssignmentID, seq)"), the deterministic-vs-sampling summary, and the §21 intra-type
  tie-break — all still asserting a universal generic tuple as authoritative.
- **AH correction.** AH8 removes every surviving positive `(CandidateID, MinerID, AssignmentID[, seq])` rule (both 3-field
  and 4-field forms) in §0.7-H2, the deterministic-vs-sampling summary, §21, and the companion documents, replacing each with
  the descriptor-derived `stable_tie_key`; the acceptance value selection is kept separate. Verified by
  `STAGE_01AH_EVENT_ORDERING_ROOT_AUDIT.md` (TV312).

## 6. Test vectors and the AG cross-document audit rested on the above gaps

- **TV291/TV292** exercised the first-round bootstrap / round-context rotation but did NOT exercise a valid DRIVER origin or
  the actual per-round bootstrap target time — they held under the fixed `run_start_time` only because they never seated a
  SECOND round.
- **TV293** checked literal `CALL` reachability of the seat owners, NOT an executable request lifecycle (production /
  consumption / replay identity / valid driver context / result handling).
- **TV294** verified `prior_round_terminal_state` publication but did NOT test the next-round TARGET time (it would have been
  `run_start_time`, backward-rejected).
- **TV295/TV296** exercised the acceptance-batch context/generation but OMITTED the failed-candidate cleanup (the FAILED
  candidate left in `active_propagation_set`) and the typed closure cancellation (`.EventRef` vs the whole record).
- **The Stage-1AG cross-document audit** therefore incorrectly marked the affected gates PASS. `STAGE_01AH_CROSS_DOCUMENT_AUDIT.md`
  re-evaluates every gate against the final Stage-1AH tree.

---

## 7. Frozen-artifact statement

- Stage-1A … Stage-1AG lettered artifacts (`STAGE_01A*`…`STAGE_01AG_*`) are UNCHANGED on disk; this register is the sole
  record of their superseded conclusions.
- No executable source, configuration, DOCX, or PDF was modified; no experiment was run; the A1 baseline `8.420833333 kWh`
  is unchanged; Stage 2 is not begun.
- The Stage-1AH corrections live only in the five modified `STAGE_01_*` normative documents and the new `STAGE_01AH_*`
  deliverables (`STAGE_01AH_CHECKSUM_MANIFEST.sha256`).
