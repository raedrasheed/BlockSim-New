# Stage 1AG — Driver-Event Seating Audit (AG4)

This audit verifies correction **AG4** ("Named driver-event seating owners") in the final normative tree of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. AG4 makes the AF4 driver-event wrappers genuinely seatable: every driver wrapper is
enqueued by a NAMED seat owner that calls `ScheduleEvent` with the wrapper's exact closed payload, records the seated
`EventRef` in `RunContext.driver_event_seat` under a bounded idempotence identity, and returns a structured result — so a
replay cannot create two rounds or commit one template twice, and the run-bootstrap chain
(`SeatNextRoundBootstrap` → `RoundInitialiseEvent` → `SeatTemplateCommit` → `TemplateCommitEvent` →
`SeatPrepareParticipants` → `PrepareParticipantsEvent`) is realised end-to-end.

The algorithm remains **PoCol**; the mechanism under audit is the idle policy within PoCol; the A1 baseline
(`8.420833333 kWh`) is preserved and unchanged. This is a documentation-only verification: no executable source,
configuration, or experiment is touched, and all line anchors (`L<n>`) refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

The normative block under audit is **(0.7g-seating) Named driver-event seating owners (AG4)** (L1192–L1333), which defines
the six driver-wrapper seat owners plus the `SeatPendingDriverRequests` intake.

## Verification items

| # | Claim verified | Evidence (line anchors, `STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Result |
|---|----------------|-----------------------------------------------------------|--------|
| 1 | Each of the six driver wrappers has a NAMED seat owner that enqueues it via `ScheduleEvent` with its exact closed payload and returns a structured result. | `SeatNextRoundBootstrap` DEF L1202, `ScheduleEvent` L1214–L1216 payload `{round_setup_seq}`, result L1222; `SeatTemplateCommit` DEF L1224, `ScheduleEvent` L1232–L1234 payload `{RoundID_at_seat, candidate_template}`, result L1239; `SeatPrepareParticipants` DEF L1241, `ScheduleEvent` L1249–L1251 payload `{RoundID_at_seat, TemplateID_at_seat}`, result L1256; `SeatMinerRegister` DEF L1258, `ScheduleEvent` L1266–L1268 payload `{join_request}`, result L1273; `SeatReserveActivate` DEF L1275, `ScheduleEvent` L1284–L1286 payload `{RoundID_at_seat, deficit, activation_seq}`, result L1291; `SeatFullRangeExhaust` DEF L1293, `ScheduleEvent` L1301–L1303 payload `{RoundID_at_seat, TemplateID_at_seat}`, result L1308. | **PASS** |
| 2 | Each owner stores the seated `EventRef` in `RunContext.driver_event_seat` keyed by a bounded idempotence identity; a replay with the same identity returns `*_already_seated` (no second seat). | Field `driver_event_seat <- empty map` L2448 (created once by `RunInitialise`); supporting ordinals `next_round_setup_seq <- 0` L2449 and per-round `reserve_activation_seq <- 0` L2496. Per owner — key / replay-guard / store: `SeatNextRoundBootstrap` key `(ROUND_INITIALISE, round_setup_seq)` L1209, guard L1210 → `round_bootstrap_already_seated` L1211, store L1218; `SeatTemplateCommit` key `(TEMPLATE_COMMIT, RoundID_at_seat, candidate_template_id)` L1229, guard L1230 → `template_commit_already_seated` L1231, store L1236; `SeatPrepareParticipants` key `(PREPARE_PARTICIPANTS, RoundID_at_seat, TemplateID_at_seat)` L1246, guard L1247 → `prepare_participants_already_seated` L1248, store L1253; `SeatMinerRegister` key `(MINER_REGISTER, join_request_id)` L1263, guard L1264 → `miner_register_already_seated` L1265, store L1270; `SeatReserveActivate` key `(RESERVE_ACTIVATE, RoundID_at_seat, activation_seq)` L1281, guard L1282 → `reserve_activate_already_seated` L1283, store L1288; `SeatFullRangeExhaust` key `(RANGE_EXHAUST, RoundID_at_seat, TemplateID_at_seat)` L1298, guard L1299 → `full_range_exhaust_already_seated` L1300, store L1305. Every guard admits only `queue_status in {QUEUED, DISPATCHING, CONSUMED}`, so a live seat blocks a second — no double round, no double template commit. | **PASS** |
| 3 | Each wrapper has at least one REACHABLE literal `CALL` to its owner. | `RoundInitialiseEvent` ← `SeatNextRoundBootstrap`: **2 sites** — `RunEventLoopToHorizon` L484 (run start) + `CloseRoundAssignments` L6102 (rotation, guarded by non-`RUN_HOOK` + time-remaining L6100–L6101). `TemplateCommitEvent` ← `SeatTemplateCommit`: L1121 in the `RoundInitialiseEvent` handler. `PrepareParticipantsEvent` ← `SeatPrepareParticipants`: L1134 in the `TemplateCommitEvent` handler. `FullRangeExhaustEvent` ← `SeatFullRangeExhaust`: L3521 in `ExhaustionAdjudicate` (C9-guarded accepted-exhaustion branch, L3518–L3520). `MinerRegisterEvent` ← `SeatMinerRegister`: L1321, and `ReserveActivateEvent` ← `SeatReserveActivate`: L1323 — both inside `SeatPendingDriverRequests`, itself called from `RunEventLoopToHorizon` L491 (reachable). | **PASS** |
| 4 | The bootstrap SEQUENCE (AG4 steps 1–5) is realised: `SeatNextRoundBootstrap` seats `RoundInitialiseEvent`; the `RoundInitialiseEvent` handler publishes the RoundContext + seats `TemplateCommitEvent`; the `TemplateCommitEvent` handler seats `PrepareParticipantsEvent`. | Step 1: `SeatNextRoundBootstrap` seats `RoundInitialiseEvent` via `ScheduleEvent` L1214–L1216. Step 2: `RoundInitialiseEvent` handler publishes `RunContext.current_round_context <- rc` L1118. Step 3: same handler seats `TemplateCommitEvent` via `CALL SeatTemplateCommit` L1121. Step 4: `TemplateCommitEvent` handler, after `TemplateCommit` succeeds (L1131), seats `PrepareParticipantsEvent` via `CALL SeatPrepareParticipants` L1134. Chain summarised normatively at L1195–L1199 and the closing NOTE L1330–L1332. | **PASS** |
| 5 | Grep-based call-graph closure: each seat owner is DEFINED and has ≥1 literal `CALL` site; 0 dangling. | `SeatNextRoundBootstrap` DEF L1202 / CALL L484, L6102; `SeatTemplateCommit` DEF L1224 / CALL L1121; `SeatPrepareParticipants` DEF L1241 / CALL L1134; `SeatMinerRegister` DEF L1258 / CALL L1321; `SeatReserveActivate` DEF L1275 / CALL L1323; `SeatFullRangeExhaust` DEF L1293 / CALL L3521; `SeatPendingDriverRequests` DEF L1310 / CALL L491. All 7 defined, each with ≥1 literal `CALL`, **0 dangling** — consistent with `STAGE_01AG_PROCEDURE_CALL_GRAPH.md`. | **PASS** |

## Method (item 5)

Definitions were extracted as `^PROCEDURE\s+<Name>` and references as `\bCALL\s+<Name>` over
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; for each of the seven seat owners the reference set is non-empty and the definition
exists, so the set difference (called − defined) is empty for this AG4 subgraph. `SeatMinerRegister` and
`SeatReserveActivate` are reached transitively through `SeatPendingDriverRequests` (their real sim-driver trigger site,
L1321 / L1323), which is itself literally called from the run driver (L491); this is a reachable named seating path, not
a dangling one.

## Overall verdict

**PASS.** All five items pass. Every one of the six driver wrappers has exactly one named seat owner that enqueues it
through `ScheduleEvent` with its exact closed payload and a structured result (item 1); every owner is idempotent via a
bounded `RunContext.driver_event_seat` identity that returns `*_already_seated` on replay, so replay cannot create two
rounds or commit one template twice (item 2); every wrapper has at least one reachable literal `CALL` to its owner, with
`RoundInitialiseEvent` reachable from two sites (item 3); the AG4 steps 1–5 bootstrap chain is realised end-to-end
(item 4); and the seat-owner call graph closes with zero dangling references (item 5). The algorithm remains **PoCol**,
the idle policy within PoCol is the mechanism, and the A1 baseline `8.420833333 kWh` is preserved.
