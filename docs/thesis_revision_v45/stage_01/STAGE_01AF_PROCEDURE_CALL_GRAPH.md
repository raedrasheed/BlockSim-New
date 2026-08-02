# Stage 1AF — Procedure Call Graph

This audit verifies that after the Stage-1AF edits every `CALL <Procedure>` in `STAGE_01_PROTOCOL_PSEUDOCODE.md` resolves to a
defined `PROCEDURE`/`FUNCTION`, and that the eight Stage-1AF procedures are defined and reachable. The A1 baseline
(`8.420833333 kWh`) and the **PoCol** naming are unchanged.

## 1. Resolution summary

- **Defined callables (`PROCEDURE`/`FUNCTION`):** 97 (Stage-1AE was 89; Stage-1AF adds 8 — see §2).
- **Distinct literal `CALL` targets:** 75.
- **Dangling references (called but not defined):** 0.

Method: extract `^(PROCEDURE|FUNCTION)\s+<Name>` as definitions and `\bCALL\s+<Uppercase-Name>` as references; the set
difference (references − definitions) is empty.

## 2. Stage-1AF new callables

| Procedure | Role | Invocation |
|-----------|------|-----------|
| `BuildHandlerInvocation` | AF2 dispatcher adapter — binds exact named handler args | literal `CALL` from `ProcessEventTime` (1 site) |
| `RoundInitialiseEvent` | AF4 wrapper → `RoundInitialise` | dynamic dispatch (`CALL inv.procedure WITH inv.args`) |
| `TemplateCommitEvent` | AF4 wrapper → `TemplateCommit` | dynamic dispatch |
| `MinerRegisterEvent` | AF4 wrapper → `MinerRegister` | dynamic dispatch |
| `PrepareParticipantsEvent` | AF4 wrapper → `PrepareParticipantsForNewRound` | dynamic dispatch |
| `ReserveActivateEvent` | AF4 wrapper → `ReserveActivate` | dynamic dispatch |
| `FullRangeExhaustEvent` | AF4 wrapper → `FullRangeExhaustNoSolution` | dynamic dispatch |
| `SeatAcceptanceBatchFinalize` | AF8 single-seat owner for `AcceptanceBatchFinalize` | literal `CALL` from `BlockAcceptancePoint` (1 site) |

**Dynamic dispatch note.** The six AF4 wrappers and every direct queued handler (`HashWorkEvent`, `WakeCompleteEvent`,
`BlockAcceptancePoint`, `CertificateArrival`, `AcceptanceBatchFinalize`, `ResumeFromPause`, `LeaseExpiry`,
`AdversarialParticipationChangeEvent`, `ActiveHashRateUpdate`, the recovery-due events, `SetupRetryEvent`) are invoked by
`ProcessEventTime` through `CALL inv.procedure WITH inv.args`, where `inv = BuildHandlerInvocation(descriptor(record.event_type),
record, RoundContext, RunContext, ctx)`. They therefore have zero LITERAL `CALL <Name>` sites — this is the intended
executable-dispatch pattern (Stage-1AD/AE dispatched via `DISPATCH record.event_type`; Stage-1AF binds via
`BuildHandlerInvocation` then `CALL inv.procedure`). Each wrapper/handler is nonetheless reachable: its `event_type` has a
descriptor whose `handler_procedure` names it, and `ProcessEventTime` dispatches every POPped QUEUED record.

## 3. Reachability of the domain procedures behind the wrappers

Each AF4 wrapper makes a literal `CALL` to its domain procedure, so the domain procedures remain reachable:

- `RoundInitialiseEvent` → `CALL RoundInitialise`
- `TemplateCommitEvent` → `CALL TemplateCommit`
- `MinerRegisterEvent` → `CALL MinerRegister`
- `PrepareParticipantsEvent` → `CALL PrepareParticipantsForNewRound`
- `ReserveActivateEvent` → `CALL ReserveActivate`
- `FullRangeExhaustEvent` → `CALL FullRangeExhaustNoSolution`

`BuildHandlerInvocation` references (non-`CALL`) the descriptor lookup `descriptor(event_type)` and the resolver
`version(AssignmentID, assignment_version)`; both are helper functions, not queued procedures.

## 4. Result

The Stage-1AF normative pseudocode call graph resolves with **0 dangling references** and **97 defined callables**; the eight
new procedures are defined, and every domain procedure behind an AF4 wrapper is reached by a literal `CALL` inside its wrapper.
