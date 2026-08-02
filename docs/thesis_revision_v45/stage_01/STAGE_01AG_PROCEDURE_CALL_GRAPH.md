# Stage 1AG — Procedure Call Graph

This audit verifies that after the Stage-1AG edits every `CALL <Procedure>` in `STAGE_01_PROTOCOL_PSEUDOCODE.md` resolves to
a defined `PROCEDURE`/`FUNCTION`, and that the seven Stage-1AG procedures are defined and reachable. The A1 baseline
(`8.420833333 kWh`) and the **PoCol** naming are unchanged.

## 1. Resolution summary

- **Defined callables (`PROCEDURE`/`FUNCTION`):** 104 (Stage-1AF was 97; Stage-1AG adds 7 — see §2).
- **Distinct literal `CALL` targets:** 82.
- **Dangling references (called but not defined):** 0.

Method: extract `^(PROCEDURE|FUNCTION)\s+<Name>` as definitions and `\bCALL\s+<Uppercase-Name>` as references; the set
difference (references − definitions) is empty.

## 2. Stage-1AG new callables and their reachability

| Procedure | Role | Reachable via (literal `CALL` sites) |
|-----------|------|--------------------------------------|
| `SeatNextRoundBootstrap` | AG4 — seats `RoundInitialiseEvent` (first driver event of a round) | `RunEventLoopToHorizon` (run start) + `CloseRoundAssignments` (rotation) = 2 |
| `SeatTemplateCommit` | AG4 — seats `TemplateCommitEvent` | `RoundInitialiseEvent` handler = 1 |
| `SeatPrepareParticipants` | AG4 — seats `PrepareParticipantsEvent` | `TemplateCommitEvent` handler = 1 |
| `SeatMinerRegister` | AG4 — seats `MinerRegisterEvent` | `SeatPendingDriverRequests` = 1 |
| `SeatReserveActivate` | AG4 — seats `ReserveActivateEvent` | `SeatPendingDriverRequests` = 1 |
| `SeatFullRangeExhaust` | AG4 — seats `FullRangeExhaustEvent` | `ExhaustionAdjudicate` (full-domain exhaustion) = 1 |
| `SeatPendingDriverRequests` | AG4 — named sim-driver intake for join requests / ordinary reserve deficits | `RunEventLoopToHorizon` loop = 1 |

**Every driver wrapper has a reachable named seating path (AG4 gate 6):** `RoundInitialiseEvent` ← `SeatNextRoundBootstrap`;
`TemplateCommitEvent` ← `SeatTemplateCommit`; `PrepareParticipantsEvent` ← `SeatPrepareParticipants`; `MinerRegisterEvent` ←
`SeatMinerRegister` ← `SeatPendingDriverRequests`; `ReserveActivateEvent` ← `SeatReserveActivate` ←
`SeatPendingDriverRequests`; `FullRangeExhaustEvent` ← `SeatFullRangeExhaust` ← `ExhaustionAdjudicate`.

## 3. Dynamic dispatch (unchanged from AF)

The six AF4 wrappers and every direct queued handler are invoked by `ProcessEventTime` through `CALL inv.procedure WITH
inv.args`, where `inv = BuildHandlerInvocation(...)` returns `handler_invocation_built(procedure, args)` (AG1). They
therefore have zero LITERAL `CALL <Name>` sites — the intended executable-dispatch pattern — but are reachable: each
`event_type` has a descriptor whose `handler_procedure` names the wrapper, and the wrapper's named seat owner enqueues it.

## 4. Result

The Stage-1AG normative pseudocode call graph resolves with **0 dangling references** and **104 defined callables**; the
seven new procedures are defined and each is reachable, so every driver wrapper has an executable seating path.
