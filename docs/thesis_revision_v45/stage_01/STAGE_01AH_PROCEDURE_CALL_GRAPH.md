# Stage 1AH — Procedure Call Graph

This audit verifies that after the Stage-1AH edits every `CALL <Procedure>` in `STAGE_01_PROTOCOL_PSEUDOCODE.md` resolves to
a defined `PROCEDURE`/`FUNCTION`, and that the four new Stage-1AH procedures are defined and reachable. The A1 baseline
(`8.420833333 kWh`) and the **PoCol** naming are unchanged.

## 1. Resolution summary

- **Defined callables (`PROCEDURE`/`FUNCTION`):** 108 (Stage-1AG was 104; Stage-1AH adds 4 — see §2).
- **Distinct literal `CALL` targets:** 86.
- **Dangling references (called but not defined):** 0.

Method: extract `^(PROCEDURE|FUNCTION)\s+<Name>` as definitions and `\bCALL\s+<Uppercase-Name>` as references; the set
difference (references − definitions) is empty.

## 2. Stage-1AH new callables and their reachability

| Procedure | Role | Reachable via (literal `CALL` sites) |
|-----------|------|--------------------------------------|
| `AdmitDriverRequest` | AH4 — the named producer of a sim-driver `driver_request` record | `RoundInitialise` (genesis import) = 1 (and the sim driver at each external arrival) |
| `SeatParticipantSetupOrAbort` | AH5/AH6 — seats `PrepareParticipantsEvent` once the round is ready and inspects the result | `TemplateCommitEvent` + `MinerRegister` (barrier completion) = 2 |
| `PublishTerminalRoundAndSeatNext` | AH2 — the one named terminal-round publication + next-bootstrap owner | `CloseRoundAssignments` = 1 |
| `FinalizeSimulationRunNoRound` | AH6 — safe run finaliser for the no-round run (first bootstrap seat failed) | `RunEventLoopToHorizon` = 1 |

**Every new procedure is reachable, and no seating/publication owner is dangling.** The AH driver-scheduling and
round-rotation chain is: `RunEventLoopToHorizon` → `SeatPendingDriverRequests` (before selection) →
`SeatMinerRegister`/`SeatReserveActivate`; and `RunEventLoopToHorizon` → `SeatNextRoundBootstrap` → `RoundInitialiseEvent`
→ `SeatTemplateCommit` → `TemplateCommitEvent` → `SeatParticipantSetupOrAbort`/`SeatPrepareParticipants` →
`PrepareParticipantsEvent`; the terminal-round rotation is `CloseRoundAssignments` → `PublishTerminalRoundAndSeatNext` →
`SeatNextRoundBootstrap`.

## 3. Dynamic dispatch (unchanged from AF/AG)

The six AF4 wrappers and every direct queued handler are invoked by `ProcessEventTime` through `CALL inv.procedure WITH
inv.args`, where `inv = BuildHandlerInvocation(...)` returns `handler_invocation_built(procedure, args)` (AG1). They
therefore have zero LITERAL `CALL <Name>` sites — the intended executable-dispatch pattern — but are reachable: each
`event_type` has a descriptor whose `handler_procedure` names the wrapper, and the wrapper's named seat owner enqueues it
(AH1 supplies each seat's explicit `scheduling_origin`).

## 4. Result

The Stage-1AH normative pseudocode call graph resolves with **0 dangling references** and **108 defined callables**; the
four new procedures are defined and each is reachable.
