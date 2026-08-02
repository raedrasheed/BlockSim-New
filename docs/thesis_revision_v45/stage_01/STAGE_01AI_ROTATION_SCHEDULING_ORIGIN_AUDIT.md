# Stage 1AI — Rotation Scheduling-Origin Truthfulness Audit (AI8)

Scope: documentation-only formal-spec audit of correction **AI8** (truthful round-rotation
scheduling-origin — **Option A**: a distinct `SchedulingOrigin` variant) of the BlockSim / PoCol
Stage-1 protocol. This audit verifies the FINAL normative tree; it runs no experiments and touches no
source, config, DOCX, PDF, or any Stage-1A..1AH artifact. Every anchor below is an exact `file:line`
into the single normative source of record:

> `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`

For brevity the anchor column cites that file as `PSEUDOCODE.md:<line>`.

---

## 1. Defect statement (the untruthful origin, pre-AI8)

Under the AH1 scheduling-origin discipline, `ScheduleEvent` carries ONE explicit `scheduling_origin`
tag and NEVER infers the source from ambient `EQ.current_*`. AH1 defines the `DRIVER` origin as a
**sim-driver seat that runs OUTSIDE any active ordinary dispatch** — the run-start bootstrap, an
external miner join, or a driver-sourced reserve activation, whose `EQ.current_*` may be unset,
cleared, or stale (`PSEUDOCODE.md:693`–`700`; `PSEUDOCODE.md:855`–`856`).

The next-round bootstrap, however, is seated by `PublishTerminalRoundAndSeatNext`, which calls
`SeatNextRoundBootstrap(RunContext)` **synchronously** (`PSEUDOCODE.md:6965`). That publication
procedure is invoked at the tail of `CloseRoundAssignments` (`PSEUDOCODE.md:6914`), which is itself
reached from `ValidBlockAccept` (`PSEUDOCODE.md:6783`) and `RoundAbort` (`PSEUDOCODE.md:7287`) —
**ordinary dispatched handlers** that each thread a `dispatch_envelope` from their dispatched caller
(`PSEUDOCODE.md:6753`, `PSEUDOCODE.md:7246`). Therefore the rotation seat occurs while an ordinary
dispatch frame is live (INSIDE dispatch).

The defect: classifying this synchronous, in-dispatch rotation seat as `DRIVER` — an origin AH1
reserves for OUTSIDE-dispatch sim-driver seats — is an **untruthful origin classification**. It
mislabels the call stack and, in principle, invites a `DRIVER` seat to reason about `EQ.current_*` on
a path where the ambient frame belongs to the terminal-round handler, not to the seat's own source.

AI8 Option A repairs this by introducing a **distinct** `SchedulingOrigin` variant,
`TERMINAL_ROTATION`, whose carried context makes the terminal-publication source explicit and lets
`ScheduleEvent` derive the delta-cycle from the predecessor terminal time WITHOUT reading ambient
`EQ.current_*`. The run-start bootstrap — a genuine OUTSIDE-dispatch seat made by
`RunEventLoopToHorizon` before the loop (`PSEUDOCODE.md:520`, with `current_round_context = null`,
`PSEUDOCODE.md:514`) — correctly REMAINS a `DRIVER` seat. This preserves the idle policy within PoCol
across the round boundary (the cross-round residency close/reopen owned solely by
`SettleResidencyBoundary`, `PSEUDOCODE.md:6926`–`6928`) while making the scheduling origin match the
actual control flow.

---

## 2. Numbered verification table

| # | Claim (AI8 Option A) | Evidence (`file:line`) | Verdict |
|---|----------------------|------------------------|---------|
| D1 | AH1 defines `DRIVER` as a sim-driver seat OUTSIDE any active ordinary dispatch (the classification the rotation seat violated). | `PSEUDOCODE.md:693`–`700`; `PSEUDOCODE.md:855`–`856`; union comment `PSEUDOCODE.md:745`–`746` | PASS |
| D2 | The next-round bootstrap is seated SYNCHRONOUSLY by `PublishTerminalRoundAndSeatNext` calling `SeatNextRoundBootstrap`. | `PSEUDOCODE.md:6965` (`SET boot <- CALL SeatNextRoundBootstrap(RunContext)`) | PASS |
| D3 | `PublishTerminalRoundAndSeatNext` runs inside an ordinary dispatched handler (`ValidBlockAccept` / `RoundAbort` → `CloseRoundAssignments` tail). | caller: `PSEUDOCODE.md:6914`; `ValidBlockAccept`→`CloseRoundAssignments` `PSEUDOCODE.md:6783`; `RoundAbort`→ `PSEUDOCODE.md:7287`; both dispatched (thread `dispatch_envelope`) `PSEUDOCODE.md:6753`, `PSEUDOCODE.md:7246` | PASS |
| D4 | The defect is stated in-spec: the rotation seat is synchronous from inside a dispatched terminal-publication path, so its truthful origin is neither plain `DRIVER` nor `POST_EPILOGUE`. | `PSEUDOCODE.md:723`–`727` | PASS |
| 1a | A new `STRUCTURE TerminalRotationSchedulingContext` exists (§0.7e). | `PSEUDOCODE.md:722` | PASS |
| 1b | It carries `BootstrapRequestID`. | `PSEUDOCODE.md:728` | PASS |
| 1c | It carries `predecessor_terminal_time` (the SOURCE time; not `EQ.current_*`). | `PSEUDOCODE.md:729` | PASS |
| 1d | It carries `target_event_time` = `next_representable_simulation_time(predecessor_terminal_time)`, strictly later than source. | `PSEUDOCODE.md:730` | PASS |
| 1e | It carries `RunContext` (verified by `ScheduleEvent`). | `PSEUDOCODE.md:731` | PASS |
| 1f | It carries `EventQueueContext` (the sole dispatch/scheduling state; verified). | `PSEUDOCODE.md:732` | PASS |
| 2a | `SchedulingOrigin` union enumerates FOUR variants. | `PSEUDOCODE.md:740`–`752` | PASS |
| 2b | Variant 1 = `ORDINARY_DISPATCH(OrdinaryDispatchContext)`. | `PSEUDOCODE.md:741` | PASS |
| 2c | Variant 2 = `DRIVER(DriverSchedulingContext)`. | `PSEUDOCODE.md:745` | PASS |
| 2d | Variant 3 = `POST_EPILOGUE(PostEpilogueSchedulingContext)`. | `PSEUDOCODE.md:747` | PASS |
| 2e | Variant 4 = `TERMINAL_ROTATION(TerminalRotationSchedulingContext)` (AI8). | `PSEUDOCODE.md:749`–`751` | PASS |
| 3a | `ScheduleEvent` INPUTS: `scheduling_origin` lists all four variants. | `PSEUDOCODE.md:837`–`839` | PASS |
| 3b | `ScheduleEvent` PRECONDITIONS enumerate all four declared sources ((1)–(4), incl. `TERMINAL_ROTATION(trctx)`). | `PSEUDOCODE.md:850`–`863` (variant 4 at `PSEUDOCODE.md:859`–`861`) | PASS |
| 3c | The SWITCH has a `CASE TERMINAL_ROTATION(trctx)`. | `PSEUDOCODE.md:906` | PASS |
| 3d | That case validates context identity (carried EQ/RunContext are the ones `ScheduleEvent` was called with). | `PSEUDOCODE.md:909`–`910` | PASS |
| 3e | That case checks `driver_kind_may_seat(ROUND_ROTATION_BOOTSTRAP, event_type)`. | `PSEUDOCODE.md:911`–`912` | PASS |
| 3f | That case checks `target_event_time == trctx.target_event_time` (carried target). | `PSEUDOCODE.md:913`–`914` | PASS |
| 3g | That case checks `target_event_time > trctx.predecessor_terminal_time` (STRICTLY later). | `PSEUDOCODE.md:915`–`916` | PASS |
| 3h | That case checks the target is NOT behind the simulation frontier (`last_finalised_event_time`). | `PSEUDOCODE.md:917`–`918` | PASS |
| 3i | That case derives `dc = 0`. | `PSEUDOCODE.md:919` | PASS |
| 3j | That case reads NO `EQ.current_*` (derives from `trctx` fields only). | `PSEUDOCODE.md:907`–`908` (case body `906`–`919` reads only `trctx`/`target_event_time`) | PASS |
| 4a | `SeatNextRoundBootstrap` builds the origin from the call context (no `EQ.current_*` read). | `PSEUDOCODE.md:1523`–`1526` | PASS |
| 4b | Run-start (`br.predecessor_round_id = RUN_START`) → `DRIVER(DriverSchedulingContext(driver_source_kind = RUN_BOOTSTRAP, …))`. | `PSEUDOCODE.md:1529`–`1532` | PASS |
| 4c | A rotation (ELSE) → `TERMINAL_ROTATION(TerminalRotationSchedulingContext(…))`. | `PSEUDOCODE.md:1533`–`1536` | PASS |
| 4d | The single seat passes `scheduling_origin = origin` to `ScheduleEvent`. | `PSEUDOCODE.md:1538`–`1541` | PASS |
| 5a | `ROUND_ROTATION_BOOTSTRAP` is REMOVED from the `DriverSchedulingContext` `DriverSourceKind` set (now `{RUN_BOOTSTRAP, MINER_JOIN, ORDINARY_RESERVE_DEFICIT}`). | `PSEUDOCODE.md:701` | PASS |
| 5b | `ROUND_ROTATION_BOOTSTRAP` is now carried by `TERMINAL_ROTATION` (moved off the DRIVER union). | `PSEUDOCODE.md:759`–`763` | PASS |
| 5c | `driver_kind_may_seat(ROUND_ROTATION_BOOTSTRAP, RoundInitialiseEvent) = TRUE` is STILL permitted. | `PSEUDOCODE.md:767` | PASS |
| 5d | The rotation's kind↔event_type permission is checked through the SAME `driver_kind_may_seat` table as the DRIVER kinds. | `PSEUDOCODE.md:764`–`772`; consumed at `PSEUDOCODE.md:911` | PASS |
| 6a | Source classification matches the actual call stack (run-start = DRIVER outside dispatch; rotation = TERMINAL_ROTATION inside terminal publication). | `PSEUDOCODE.md:1523`–`1536`; run-start call site `PSEUDOCODE.md:520` | PASS |
| 6b | No next-round event is seated before terminal publication: `PublishTerminalRoundAndSeatNext` ASSERTs the predecessor is terminal FIRST, then creates the request and seats. | ASSERT `PSEUDOCODE.md:6941`; request created `PSEUDOCODE.md:6959`; seat `PSEUDOCODE.md:6965`; precondition `PSEUDOCODE.md:6934`–`6938` | PASS |
| 6c | Target is STRICTLY after the predecessor terminal time. | `PSEUDOCODE.md:915`–`916`; structure `PSEUDOCODE.md:730`; `next_target` `PSEUDOCODE.md:6953`–`6960` | PASS |
| 6d | Deterministic delta_cycle (`dc = 0`), sole authority `ScheduleEvent` (L6). | `PSEUDOCODE.md:919`; `PSEUDOCODE.md:733`–`735` | PASS |
| 6e | No ambient cleared `EQ.current_*` is read on the rotation path. | `PSEUDOCODE.md:907`–`908`; `PSEUDOCODE.md:733`–`735`; `PSEUDOCODE.md:1523` | PASS |
| 6f | `event_creation_seq` is STILL minted solely by `ScheduleEvent` (J4) — the origin change does not touch seq ownership. | `PSEUDOCODE.md:735`; `PSEUDOCODE.md:973`–`975` | PASS |

---

## 3. Explicit origin-truthfulness check (the crux of AI8)

The correction's whole purpose is that the ORIGIN TAG matches the control flow. Two mutually
exclusive branches in `SeatNextRoundBootstrap` must be resolved by exactly one predicate,
`br.predecessor_round_id = RUN_START`:

**(a) The SYNCHRONOUS rotation seat is `TERMINAL_ROTATION` (NOT `DRIVER`).**
`SeatNextRoundBootstrap` takes the ELSE branch for a rotation (`br.predecessor_round_id != RUN_START`)
and sets `origin <- TERMINAL_ROTATION(TerminalRotationSchedulingContext(...))`
(`PSEUDOCODE.md:1533`–`1536`). This is the branch reached when the caller is
`PublishTerminalRoundAndSeatNext` (`PSEUDOCODE.md:6965`) — synchronously, from inside the
terminal-publication path of `ValidBlockAccept`/`RoundAbort` (an ordinary dispatched handler chain,
`PSEUDOCODE.md:6914`, `6783`, `7287`). Because this is inside dispatch, an AH1 `DRIVER`
(outside-dispatch) tag would be untruthful; the `TERMINAL_ROTATION` variant is the truthful origin.
`ScheduleEvent`'s `CASE TERMINAL_ROTATION` (`PSEUDOCODE.md:906`–`919`) then derives `dc = 0` from
`trctx.predecessor_terminal_time` with NO `EQ.current_*` read. **VERDICT: PASS.**

**(b) The run-start seat REMAINS `DRIVER`.**
For the first round, `br.predecessor_round_id = RUN_START` (`PSEUDOCODE.md:1529`), and the origin is
`DRIVER(DriverSchedulingContext(driver_source_kind = RUN_BOOTSTRAP, ..., intended_round_scope =
RUN_LEVEL, ...))` (`PSEUDOCODE.md:1530`–`1532`). This is a genuine OUTSIDE-dispatch sim-driver seat:
`RunEventLoopToHorizon` calls `SeatNextRoundBootstrap` BEFORE entering the loop, while
`current_round_context = null` (`PSEUDOCODE.md:520`, `514`), so no ordinary dispatch frame is live —
`DRIVER` is truthful here. **VERDICT: PASS.**

The two branches are exhaustive and disjoint over the `RUN_START` predicate, and each origin tag
matches its actual call stack. The first-round `BootstrapRequest` carries
`predecessor_round_id = RUN_START`, `predecessor_terminal_time = null`, `target_time =
config.run_start_time` (`PSEUDOCODE.md:3120`–`3121`); every subsequent (rotation) request carries a
real predecessor id and terminal time with `target_time =
next_representable_simulation_time(predecessor_terminal_time)` (`PSEUDOCODE.md:3053`–`3058`,
`6956`–`6960`). Thus the predicate reliably selects the correct origin.

---

## 4. Ordering / safety corroboration

- **Terminal-before-seat ordering.** `PublishTerminalRoundAndSeatNext` opens with
  `ASSERT round_state in {ROUND_ACCEPTED, ROUND_ABORTED}` (`PSEUDOCODE.md:6941`) BEFORE recording
  `round_terminal_time`, creating the next `BootstrapRequest` (`PSEUDOCODE.md:6959`), and seating
  (`PSEUDOCODE.md:6965`). `SeatNextRoundBootstrap`'s own preconditions restate that the request is
  "NEVER seated while the predecessor round is nonterminal" (`PSEUDOCODE.md:1511`–`1512`). No next
  round can be seated before terminal publication.
- **Strictly-later target.** Enforced in three places: the structure invariant
  (`PSEUDOCODE.md:730`), the request invariant (`PSEUDOCODE.md:3056`–`3057`), and the
  `ScheduleEvent` guard `IF NOT (target_event_time > trctx.predecessor_terminal_time)`
  (`PSEUDOCODE.md:915`–`916`), returning `rejected_driver_target_before_source`.
- **Deterministic delta-cycle, no ambient read.** `CASE TERMINAL_ROTATION` sets `dc <- 0`
  (`PSEUDOCODE.md:919`) reading only `trctx` fields; the union comment reiterates "NO `EQ.current_*`
  read" (`PSEUDOCODE.md:749`–`751`). `ScheduleEvent` remains the sole delta-cycle authority (L6,
  `PSEUDOCODE.md:1019`–`1023`) and the sole `event_creation_seq` minter
  (`PSEUDOCODE.md:973`–`975`).
- **Result union completeness.** The `TERMINAL_ROTATION` case reuses the shared AI2 driver-context
  rejections (`rejected_driver_context_mismatch`, `rejected_driver_kind_event_type_mismatch`,
  `rejected_driver_target_context_mismatch`, `rejected_driver_target_before_source`,
  `rejected_driver_target_before_simulation_frontier`), all declared in `ScheduleEvent`'s RETURNS
  (`PSEUDOCODE.md:989`–`1007`) — no undeclared variant is produced by the new case.

---

## 5. Overall verdict

**PASS.** Correction AI8 (truthful round-rotation scheduling origin — Option A) is fully and
consistently realised in the FINAL normative tree:

1. `STRUCTURE TerminalRotationSchedulingContext` (§0.7e) exists with all five declared fields
   (`PSEUDOCODE.md:722`–`735`).
2. `SchedulingOrigin` is a four-variant union including `TERMINAL_ROTATION`
   (`PSEUDOCODE.md:740`–`752`).
3. `ScheduleEvent` INPUTS, PRECONDITIONS, and SWITCH all account for the fourth variant, and the
   `CASE TERMINAL_ROTATION` performs the full validation set (context identity, `driver_kind_may_seat`,
   carried-target equality, strictly-later-than-predecessor, frontier, `dc = 0`, no `EQ.current_*`)
   (`PSEUDOCODE.md:837`–`839`, `850`–`863`, `906`–`919`).
4. `SeatNextRoundBootstrap` builds the origin from the truthful call stack — `DRIVER`/`RUN_BOOTSTRAP`
   for run-start, `TERMINAL_ROTATION` for a rotation (`PSEUDOCODE.md:1529`–`1541`).
5. `ROUND_ROTATION_BOOTSTRAP` is removed from `DriverSchedulingContext.DriverSourceKind`
   (`PSEUDOCODE.md:701`), carried instead by `TERMINAL_ROTATION` (`PSEUDOCODE.md:759`–`763`), while
   `driver_kind_may_seat(ROUND_ROTATION_BOOTSTRAP, RoundInitialiseEvent)` is still permitted
   (`PSEUDOCODE.md:767`).
6. Source classification matches the call stack; no next-round event is seated before terminal
   publication (`ASSERT`, `PSEUDOCODE.md:6941`); the target is strictly after the predecessor terminal
   time; the delta-cycle is deterministic (`dc = 0`); and no ambient cleared `EQ.current_*` is read.

The explicit crux check confirms the synchronous rotation seat is classified `TERMINAL_ROTATION` (not
`DRIVER`) and the run-start seat remains `DRIVER`. **No genuine FAIL was found.**
