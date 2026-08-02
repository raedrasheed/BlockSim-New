# Stage 1AI — Barrier / Participant-Setup Result-Propagation Audit (AI7)

This audit verifies correction **AI7**: the barrier-completing `MinerRegister` now **inspects** the result of
`SeatParticipantSetupOrAbort` and reports it through a **distinct disposition union**, so a participant-setup abort
during the first round's initial-registration barrier can no longer be hidden behind a plain `miner_registered(MinerID)`
success. It confirms end-to-end that the inspected disposition (i) is returned distinctly by `MinerRegister`, (ii) is
propagated verbatim by the `MinerRegisterEvent` wrapper, and (iii) is recorded verbatim as the driver_request's
`consumed_result` when the `MinerRegisterEvent` dispatch completes.

Scope is documentation-only. The algorithm is **PoCol** and the mechanism is the idle policy within PoCol. No source,
config, DOCX, PDF, or any Stage-1A–1AH historical artifact is modified; this file is the sole artifact created. All line
anchors below are quoted from the current normative
`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md` and are exact against the FINAL normative tree.

Source of truth (read-only): `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

---

## 1. Defect statement

Before AI7, the barrier-completing `MinerRegister` — the registration that completes the FIRST round's declared
initial-registration barrier while the round is already in `ASSIGNMENT` with a committed `TemplateID` (the case in which
`TemplateCommitEvent` had **deferred** participant setup, `STAGE_01_PROTOCOL_PSEUDOCODE.md:1421–1422`) — **called**
`SeatParticipantSetupOrAbort` to seat participant setup but did **not inspect** the returned disposition. Because
`SeatParticipantSetupOrAbort` is the single site that turns an un-seatable participant setup into a **declared round
abort** (`participant_setup_aborted(participant_setup_seat_failed_round_abort(reason))`,
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1598–1603`), discarding its result meant the barrier-completing registration could
return a plain `miner_registered(MinerID)` **even when the round had just been aborted**. The abort was therefore
invisible to the `MinerRegisterEvent` wrapper and, downstream, to the driver_request's `consumed_result` recorded by
`ProcessEventTime` — a success masking a round abort.

AI7 corrects this by (a) giving `MinerRegister` a distinct five-arm disposition union, (b) making the barrier-completing
path SWITCH on the `SeatParticipantSetupOrAbort` result with **no plain success on the abort arm**, (c) propagating that
disposition verbatim through `MinerRegisterEvent`, and (d) recording it verbatim as the driver_request's
`consumed_result` at dispatch completion.

---

## 2. Verification table

| # | Claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-------|-----------------------------------------------|---------|
| 1 | `MinerRegister`'s `RETURNS` union is the distinct five-arm disposition: `miner_registered` / `_barrier_pending` / `_participant_setup_seated` / `_already_seated` / `_participant_setup_aborted(MinerID, participant_setup_seat_failed_round_abort(reason))`. | `line 4012`–`4014` (`RETURNS: miner_registered(MinerID) \| miner_registered_barrier_pending(MinerID) \| miner_registered_participant_setup_seated(MinerID) \| miner_registered_participant_setup_already_seated(MinerID) \| miner_registered_participant_setup_aborted(MinerID, participant_setup_seat_failed_round_abort(reason))`). | PASS |
| 2 | Ordinary / non-barrier registration returns the plain `miner_registered(MinerID)` and does so **before** any participant-setup seating (it never reaches the seat call). | `line 3990`–`3991` (`IF MinerID NOT in RoundContext.initial_registration_barrier.expected: RETURN miner_registered(MinerID)`). | PASS |
| 3 | A registration that advances but does not complete the barrier returns `_barrier_pending` (no seat attempted). | `line 3993`–`3995` (`IF NOT ( … registered CONTAINS every member … ) OR … satisfied: RETURN miner_registered_barrier_pending(MinerID)`). | PASS |
| 4 | The barrier-completing registration seats participant setup ONLY when `round_state = ASSIGNMENT AND TemplateID_committed != null`; otherwise it returns `_barrier_pending` (TemplateCommitEvent will seat). | `line 4002`–`4003` (`IF NOT (round_state = ASSIGNMENT AND TemplateID_committed != null): RETURN miner_registered_barrier_pending(MinerID)`). | PASS |
| 5 | On that barrier-completing path, `MinerRegister` CALLS `SeatParticipantSetupOrAbort` with the committed round/template and the dispatched frame as `abort_envelope`. | `line 4004`–`4007` (`SET abort_envelope <- { … EQ.current_* … }; SET ps <- CALL SeatParticipantSetupOrAbort(RoundContext.RunContext, RoundContext, RoundID_at_seat = RoundID_current, TemplateID_at_seat = TemplateID_committed, abort_envelope = abort_envelope)`). | PASS |
| 6 | `MinerRegister` SWITCHes on the `SeatParticipantSetupOrAbort` result — `participant_setup_seated` → `_participant_setup_seated`; `participant_setup_already_seated` → `_already_seated`; `participant_setup_aborted(reason)` → `_participant_setup_aborted` (explicitly "NO plain success after an abort"). | `line 4008`–`4011` (`SWITCH ps: CASE participant_setup_seated(_): RETURN miner_registered_participant_setup_seated(MinerID); CASE participant_setup_already_seated: RETURN miner_registered_participant_setup_already_seated(MinerID); CASE participant_setup_aborted(reason): RETURN miner_registered_participant_setup_aborted(MinerID, reason) # AI7: NO plain success after an abort`). | PASS |
| 7 | `SeatParticipantSetupOrAbort` returns exactly the three variants the SWITCH covers, and is the single site converting a seat failure into a declared round abort. | `line 1595`–`1605` (`SWITCH pp: … prepare_participants_seat_failed(reason): … SET disp <- CALL RoundAbort(…, reason = participant_setup_seat_failed_round_abort(reason), …); RETURN participant_setup_aborted(…)`; `RETURNS: participant_setup_seated(EventRef) \| participant_setup_already_seated \| participant_setup_aborted(participant_setup_seat_failed_round_abort(reason))`). | PASS |
| 8 | `MinerRegisterEvent` captures `MinerRegister`'s result and propagates it verbatim (`SET mr <- CALL MinerRegister(...); RETURN mr`). | `line 1443`–`1444` (`SET mr <- CALL MinerRegister(RoundContext, join_request = join_request, dispatch_envelope = dispatch_envelope); RETURN mr`). | PASS |
| 9 | `MinerRegisterEvent`'s `RETURNS` lists all five `MinerRegister` dispositions verbatim. | `line 1445`–`1447` (same five-arm union as item 1). | PASS |
| 10 | `ProcessEventTime` captures the dispatched handler's actual result as `handler_result`. | `line 351` (`SET handler_result <- CALL inv.procedure WITH inv.args    # … AI4: CAPTURE the actual result`). | PASS |
| 11 | On dispatch completion `ProcessEventTime` calls `CompleteDriverRequestOnDispatch(…, disposition = driver_request_consumed(handler_result))` with the seat EventRef. | `line 362`–`363` (`CALL CompleteDriverRequestOnDispatch(RunContext, seat_event_ref = er, disposition = driver_request_consumed(handler_result))`). | PASS |
| 12 | `CompleteDriverRequestOnDispatch` resolves the exact driver_request from the trusted seat EventRef and drives SEATED → CONSUMED through the guarded mutator, forwarding the disposition. | `line 1790`–`1795` (`IF RunContext.driver_request_by_seat_event_ref[seat_event_ref] does not exist: RETURN driver_request_not_a_seat(...); SET drid <- …; RETURN CALL SetDriverRequestStatus(RunContext, drid, expected_status = SEATED, new_status = CONSUMED, disposition = disposition)`). | PASS |
| 13 | `SetDriverRequestStatus` records the ACTUAL `handler_result` as `dr.consumed_result` when the disposition is `driver_request_consumed(handler_result)` — completing the linkage from `MinerRegister`'s disposition to the driver_request's `consumed_result`. | `line 1777`–`1778` (`IF new_status = CONSUMED AND disposition = driver_request_consumed(handler_result): SET dr.consumed_result <- handler_result`). | PASS |

---

## 3. Explicit check: `MinerRegister` has NO path returning a plain success after a participant-setup abort

Every `RETURN` in `PROCEDURE MinerRegister` (`line 3965`–`4022`) was enumerated. The plain success token
`miner_registered(MinerID)` appears at exactly one RETURN site:

- `line 3991` — the ordinary non-barrier arm, guarded by `IF MinerID NOT in RoundContext.initial_registration_barrier.expected`
  (`line 3990`). This arm returns **before** the barrier bookkeeping and therefore **before** any call to
  `SeatParticipantSetupOrAbort` (`line 4006`); no abort can have occurred on this path.

The `SeatParticipantSetupOrAbort` call at `line 4006` is followed by a total SWITCH on its result (`line 4008`–`4011`).
`SeatParticipantSetupOrAbort` returns exactly three variants (`line 1604`–`1605`) and each is handled by a dedicated
`CASE` that RETURNs a **distinct** disposition:

- `participant_setup_seated(_)` → `miner_registered_participant_setup_seated(MinerID)` (`line 4009`);
- `participant_setup_already_seated` → `miner_registered_participant_setup_already_seated(MinerID)` (`line 4010`);
- `participant_setup_aborted(reason)` → `miner_registered_participant_setup_aborted(MinerID, reason)` (`line 4011`).

There is no `default`/fall-through arm and no statement after the SWITCH before the procedure's `RETURNS` declaration
(`line 4012`), so no execution path reaches a plain `miner_registered(MinerID)` after the seat call. The abort arm
(`line 4011`) returns `miner_registered_participant_setup_aborted(...)` and nothing else — the AI7 in-line assertion
"NO plain success after an abort" is structurally realised. The two `_barrier_pending` returns (`line 3995`, `line 4003`)
also precede any seat attempt, so neither can mask an abort.

**Result: CONFIRMED — no path in `MinerRegister` returns a plain success after a participant-setup abort.**

---

## 4. End-to-end propagation chain

The inspected disposition flows without loss or aliasing:

`SeatParticipantSetupOrAbort` result (`line 1604`–`1605`)
→ `MinerRegister` distinct disposition (SWITCH `line 4008`–`4011`; RETURNS `line 4012`–`4014`)
→ `MinerRegisterEvent` verbatim (`SET mr <- CALL MinerRegister(...)`, `RETURN mr`, `line 1443`–`1444`; RETURNS `line 1445`–`1447`)
→ `ProcessEventTime` `handler_result` (`line 351`)
→ `CompleteDriverRequestOnDispatch(..., disposition = driver_request_consumed(handler_result))` (`line 362`–`363`; procedure `line 1790`–`1795`)
→ `SetDriverRequestStatus` records `dr.consumed_result <- handler_result` on SEATED → CONSUMED (`line 1777`–`1778`).

The driver_request that seated the `MinerRegisterEvent` therefore records the **same** final disposition
(`miner_registered_participant_setup_aborted(...)` on the abort path) as its `consumed_result`, satisfying the AI7
linkage asserted in the `MinerRegisterEvent` note (`line 1439`–`1442`) and the `MinerRegister` note (`line 4017`–`4022`).

---

## 5. Overall verdict

**PASS.** All thirteen table items and the explicit no-plain-success-after-abort check hold against the FINAL normative
tree with exact `file:line` anchors. Correction AI7 is faithfully realised: `MinerRegister` inspects the
`SeatParticipantSetupOrAbort` result and returns a distinct five-arm disposition with no plain success on the abort arm;
`MinerRegisterEvent` propagates it verbatim; and `ProcessEventTime` / `CompleteDriverRequestOnDispatch` /
`SetDriverRequestStatus` record that same disposition as the driver_request's `consumed_result`. No defects were found.
