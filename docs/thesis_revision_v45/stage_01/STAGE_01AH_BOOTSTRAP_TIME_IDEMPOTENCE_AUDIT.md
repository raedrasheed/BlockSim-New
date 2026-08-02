# Stage 1AH — Bootstrap Target-Time & Request-Identity Idempotence Audit (AH2 + AH3)

Scope: this audit inspects ONLY the final normative tree at
`docs/thesis_revision_v45/stage_01/`, primary source
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. It verifies the AH2 (per-round bootstrap
target time) and AH3 (stable request identity before minting) corrections
against the actual final text. Every claim cites an exact `file:line` anchor.

Context: the algorithm is **PoCol**; the mechanism is **the idle policy within
PoCol**; the A1 baseline (`8.420833333 kWh`) is unchanged by this
documentation-only pseudocode revision. This audit adds no consensus feature and
alters no energy result.

All line anchors below are into
`STAGE_01_PROTOCOL_PSEUDOCODE.md` unless otherwise noted.

---

## AH2 — Item 1: `RunContext.round_bootstrap_time = config.run_start_time` is REMOVED

A `grep` for `round_bootstrap_time` across the primary file returns FIVE hits,
every one of them a REMOVED / superseded note — never a live field, never a
`ScheduleEvent` target.

- `STAGE_01_PROTOCOL_PSEUDOCODE.md:2703-2704` — inside `STRUCTURE RunContext`:
  "AH2: round_bootstrap_time (the AG fixed `config.run_start_time` target for
  EVERY round) is REMOVED — every round's bootstrap target is the per-round
  BootstrapRequest.target_time (STAGE_01AH_SUPERSESSION_REGISTER.md)." It is a
  comment, not a declared field of the structure.
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:2755-2757` — `RunInitialise`: "AH2: NO fixed
  round_bootstrap_time. Create the FIRST round's immutable BootstrapRequest …"
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:2797-2798` — `RunInitialise` NOTE: "There is
  NO fixed round_bootstrap_time (AH2): every round's target is its own
  BootstrapRequest.target_time."
- `STAGE_01_PROTOCOL_PSEUDOCODE.md:497` and `:538` —
  `RunEventLoopToHorizon` note: the seat targets the RUN_START
  `BootstrapRequest.target_time` "(= config.run_start_time), not a fixed
  round_bootstrap_time."

The actual `ScheduleEvent` seat of `RoundInitialiseEvent` uses
`target_event_time = br.target_time`
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:1379`), never a `round_bootstrap_time` field.
No live declaration of `round_bootstrap_time` exists anywhere in the file
(it is neither `SET`, `INITIALISE`d, nor returned by `RunInitialise`; cf. the
RunContext field list and RETURNS at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2758-2777`).

**PASS** — `round_bootstrap_time` survives only as a REMOVED/superseded note; it
is neither a live field nor a scheduling target.

---

## AH2 — Item 2: `STRUCTURE BootstrapRequest`, first-round `RUN_START`, and rotation target

### 2a. The structure and its four fields

`STAGE_01_PROTOCOL_PSEUDOCODE.md:2706` declares
`STRUCTURE BootstrapRequest (AH2/AH3 — the IMMUTABLE per-round bootstrap request …)`
with exactly the four required members:

- `BootstrapRequestID` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2707-2709`
- `predecessor_round_id` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2710`
- `predecessor_terminal_time` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2711`
- `target_time` — `STAGE_01_PROTOCOL_PSEUDOCODE.md:2712-2715`

The `target_time` field carries the REQUIRED constraints at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2713-2715`: "target_time >
predecessor_terminal_time (a rotation) AND target_time <= run_horizon_T; NO
subsequent bootstrap ever reuses config.run_start_time."

**PASS** — structure present with the exact required field set.

### 2b. First round's request is `RUN_START`, target = `config.run_start_time`, created in `RunInitialise`

`STAGE_01_PROTOCOL_PSEUDOCODE.md:2759-2760` in `RunInitialise`:
`SET first_bootstrap <- BootstrapRequest(BootstrapRequestID = RUN_START,
predecessor_round_id = RUN_START, predecessor_terminal_time = null,
target_time = config.run_start_time)`. It is registered under its stable id and
made the request the seat consumes at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2761-2762`.

**PASS** — the first round's `RUN_START` request (target `config.run_start_time`)
is created in `RunInitialise`.

### 2c. Rotation target = `next_representable_simulation_time(predecessor_terminal_time)`, strictly later, `<= run_horizon_T`, never reusing run_start_time, created in `PublishTerminalRoundAndSeatNext`

`STAGE_01_PROTOCOL_PSEUDOCODE.md:6548`:
`SET next_target <- next_representable_simulation_time(round_terminal_time(RoundID_current))`.
The horizon guard `STAGE_01_PROTOCOL_PSEUDOCODE.md:6549` (`IF NOT (next_target <=
RunContext.run_horizon_T)` -> published, no next round) enforces the `<= T`
bound. The immutable rotation request is minted at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:6553-6555`:
`brid <- (RoundID_current, round_terminal_time(RoundID_current), NEXT_ROUND)` and
`next_br <- BootstrapRequest(… predecessor_terminal_time =
round_terminal_time(RoundID_current), target_time = next_target)`. The inline
step comment `STAGE_01_PROTOCOL_PSEUDOCODE.md:6551-6552` states the target is
"strictly LATER than the predecessor's terminal time and <= T, NEVER
config.run_start_time (that is the FIRST round's target only)." Because
`next_representable_simulation_time(...)` of the terminal time is by construction
strictly greater than that terminal time, "strictly later than predecessor
terminal" holds; the "never run_start_time" invariant is the structure-level
REQUIRED at `STAGE_01_PROTOCOL_PSEUDOCODE.md:2714-2715`.

**PASS** — rotation request created in `PublishTerminalRoundAndSeatNext` with the
per-round, strictly-later, `<= T`, never-run_start_time target.

---

## AH3 — Item 3: `SeatNextRoundBootstrap` keys on the STABLE `BootstrapRequestID`, checks replay BEFORE reading `next_round_setup_seq`

`PROCEDURE SeatNextRoundBootstrap` at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1351`:

- The replay key is the STABLE `BootstrapRequestID`:
  `SET key <- (ROUND_INITIALISE, br.BootstrapRequestID)` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1362`.
- The replay is checked FIRST:
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1363-1364`, returning
  `round_bootstrap_already_seated(br.BootstrapRequestID,
  RunContext.driver_event_seat[key])`.
- ONLY AFTER the replay check is the descriptor tie key read:
  `SET round_setup_seq <- RunContext.next_round_setup_seq` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1367` (guarded by the explicit comment at
  `:1365-1366` that it is READ here, never read+incremented before the replay
  check).
- `next_round_setup_seq` is advanced ONLY after a successful seat:
  `SET RunContext.next_round_setup_seq <- round_setup_seq + 1` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1384` (inside the `scheduled(...)` branch).

The RunContext field note corroborates the ordering:
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2684-2685` — `next_round_setup_seq` "is READ
(not incremented) to LABEL a bootstrap and advanced ONLY after a NEW
BootstrapRequestID is shown to seat (never before the replay check)."

**PASS** — stable-id replay key, checked before the sequence is read; the seq is
advanced only post-seat.

---

## AH3 — Item 4: `SeatReserveActivate` / `SeatMinerRegister` check replay BEFORE minting the seq (the AG defect is corrected)

### 4a. `SeatReserveActivate` — replay key BEFORE `reserve_activation_seq`

`PROCEDURE SeatReserveActivate` at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1471`:

- Replay key on the request identity:
  `SET key <- (RESERVE_ACTIVATE, driver_request.DriverRequestID)` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1479`.
- Replay checked FIRST:
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1480-1481`, returning
  `reserve_activate_already_seated(driver_request.DriverRequestID, …)`.
- `reserve_activation_seq` is read ONLY AFTER the replay check passes:
  `SET activation_seq <- RunContext.current_round_context.reserve_activation_seq`
  — `STAGE_01_PROTOCOL_PSEUDOCODE.md:1483` (guarded by the comment at `:1482`:
  "ONLY NOW (request shown NEW) READ the per-round activation_seq …").
- It is incremented only after a successful seat:
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1494`.

The AG defect — where "next value of … `reserve_activation_seq`" was minted
BEFORE the replay check — is absent: no read or increment of
`reserve_activation_seq` occurs on `STAGE_01_PROTOCOL_PSEUDOCODE.md:1477-1481`
prior to the guard.

### 4b. `SeatMinerRegister` — replay key on `DriverRequestID`

`PROCEDURE SeatMinerRegister` at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1447`:

- `SET key <- (MINER_REGISTER, driver_request.DriverRequestID)` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1453`.
- Replay checked FIRST, returning
  `miner_register_already_seated(driver_request.DriverRequestID, …)` —
  `STAGE_01_PROTOCOL_PSEUDOCODE.md:1454-1455`. `SeatMinerRegister` mints no
  per-round sequence at all (its descriptor identity is the DriverRequestID),
  so there is no pre-guard seq to hoist.

**PASS** — both owners key on the stable `DriverRequestID` and check replay
before any sequence is read; the AG "mint-seq-first" defect is corrected.

---

## AH3 — Item 5: a replay of the same request returns the same seated `EventRef` and seats no second event

Every driver-seat owner returns the STORED `driver_event_seat[key]` EventRef on a
replay (no second `ScheduleEvent` call is reached):

- `SeatNextRoundBootstrap`: `STAGE_01_PROTOCOL_PSEUDOCODE.md:1364` returns
  `round_bootstrap_already_seated(br.BootstrapRequestID,
  RunContext.driver_event_seat[key])`.
- `SeatMinerRegister`: `STAGE_01_PROTOCOL_PSEUDOCODE.md:1455`.
- `SeatReserveActivate`: `STAGE_01_PROTOCOL_PSEUDOCODE.md:1481`.

The terminal-round publication owner folds the replay result into the SAME
outcome as a fresh seat, returning the SAME EventRef:
`STAGE_01_PROTOCOL_PSEUDOCODE.md:6562-6563`
(`round_bootstrap_already_seated(_, event_ref)` ->
`terminal_round_published_and_seated(brid, event_ref)`).

The sim-driver intake terminalises a replay as a no-op that seats nothing new and
leaves nothing pending: `SeatPendingDriverRequests` at
`STAGE_01_PROTOCOL_PSEUDOCODE.md:1559-1561` — the `*_already_seated(_, event_ref)`
cases set `dr.status <- SEATED`, `dr.seated_event_ref <- event_ref`,
`dr.disposition <- driver_request_replay_noop(event_ref)`.

The RunContext field note confirms the guarantee:
`STAGE_01_PROTOCOL_PSEUDOCODE.md:2686-2688` — "a replay of the SAME logical
bootstrap returns the SAME seated EventRef."

**PASS** — a replay returns the identical seated EventRef and seats no second
event.

---

## Overall verdict

**PASS** — AH2 (per-round bootstrap target time) and AH3 (stable request identity
before minting) are correctly and consistently realised in the final normative
tree. `round_bootstrap_time` is fully removed (notes only);
`STRUCTURE BootstrapRequest` carries the exact four fields with the per-round
target invariants; the first-round `RUN_START` request is created in
`RunInitialise` and each rotation request in `PublishTerminalRoundAndSeatNext`;
`SeatNextRoundBootstrap`, `SeatReserveActivate`, and `SeatMinerRegister` all key
on their STABLE request identity and check the replay guard BEFORE any sequence
is read or minted; and a replay of any request returns the same seated EventRef
without seating a second event. No genuine defect requiring a fix in the
normative tree was found. Algorithm PoCol, the idle policy within PoCol, and the
A1 baseline `8.420833333 kWh` are unchanged.
