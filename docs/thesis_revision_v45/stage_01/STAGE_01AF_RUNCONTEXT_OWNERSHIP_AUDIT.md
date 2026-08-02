# Stage 1AF — RunContext Ownership Audit (correction AF6)

## Intro

This audit verifies correction **AF6 — RunContext ownership** against the FINAL normative
tree, specifically `PROCEDURE RunInitialise` in `STAGE_01_PROTOCOL_PSEUDOCODE.md`
(`L2175`). AF6 makes `RunInitialise` the ONE-TIME owner of EVERY per-run field: each field
is INITIALISEd once at run start AND returned inside the `RunContext(...)` object, and a
stated access convention fixes that every bare per-run registry name denotes a field of the
bound `RunContext` (reached as `RoundContext.RunContext.<field>`), never an implicit global.
The scope for Stage 1AF is unchanged: the algorithm is **PoCol**; the low-power mechanism is
**the idle policy within PoCol** (an operating policy inside PoCol, not a variant or fork);
and the A1 continuous full-participation baseline **`8.420833333 kWh`**
(`STAGE_01_PROTOCOL_SCOPE.md` `L34`) is preserved. This is a documentation-only audit; no
executable source, configuration, DOCX, or PDF was modified, and no experiment was run.

All line anchors below refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless otherwise noted.

## Item 1 — Every per-run field is INITIALISEd AND RETURNed in RunContext

`PROCEDURE RunInitialise` at `L2175` ("Q5: creates ALL per-run fields ONCE at run start").
Its `RETURNS: RunContext(...)` spans `L2201`–`L2207`; its access NOTE spans `L2208`–`L2220`.

| Per-run field | INITIALISE / SET anchor | RETURNS anchor | Result |
|---|---|---|---|
| EventQueueContext (EQ) | `L2180`–`L2182` (INITIALISE EventQueueContext EQ) | `L2201` (`EventQueueContext = EQ`) | PASS |
| queued_event_registry | `L2192` (INITIALISE queued_event_registry) | `L2205` | PASS |
| setup_retry_records | `L2191` (INITIALISE setup_retry_records) | `L2205` | PASS |
| setup_retry_by_seat_event_ref | `L2193` (INITIALISE setup_retry_by_seat_event_ref) | `L2205` | PASS |
| applied_transition_registry | `L2189` (INITIALISE applied_transition_registry) | `L2204` | PASS |
| transition_rejection_log | `L2190` (INITIALISE transition_rejection_log) | `L2204` | PASS |
| security_census_dirty | `L2186` (INITIALISE security_census_dirty) | `L2202` | PASS |
| latest_security_census | `L2187` (INITIALISE latest_security_census) | `L2202` | PASS |
| security_census_write_seq_by_event_time | `L2188` (INITIALISE ...write_seq_by_event_time) | `L2203` | PASS |
| waking_origin_assignment_ref | `L2194` (INITIALISE waking_origin_assignment_ref) | `L2206` | PASS |
| maximum_setup_retries | `L2195` (SET maximum_setup_retries) | `L2206` | PASS |
| config | `L2198` (SET config <- config) | `L2207` | PASS |
| prior_round_terminal_state | `L2199` (INITIALISE prior_round_terminal_state <- null) | `L2207` | PASS |
| current_round_context | `L2200` (INITIALISE current_round_context <- null) | `L2207` | PASS |
| RunHookContext | `L2183` (INITIALISE RunHookContext) | `L2201` | PASS |
| rebased_boundaries | `L2184` (INITIALISE rebased_boundaries) | `L2201` | PASS |
| run_finalised | `L2185` (INITIALISE run_finalised <- false) | `L2201` | PASS |
| run_horizon_T | `L2182` (EQ `run_horizon_T = config.horizon_T`) | `L2202` (`run_horizon_T = config.horizon_T`) | PASS |

Every field in the required minimum set is both INITIALISEd/SET and present in the
`RETURNS: RunContext(...)` list. The NOTE at `L2208`–`L2213` re-enumerates the identical set
("RunContext CONTAINS and RunInitialise RETURNS all of them"). **Item 1: PASS.**

## Item 2 — queued_event_registry and setup_retry_by_seat_event_ref BOTH in RETURNS

Both names appear together on RETURNS line `L2205`:
`setup_retry_records, queued_event_registry, setup_retry_by_seat_event_ref,` — with the
inline note `# AF6: ADDED to RETURNS (were INITIALISEd but not returned)`. This is the exact
Stage-1AE omission AF6 repairs: the two maps were INITIALISEd (`L2192`, `L2193`) but had been
left out of the returned object under Stage-1AE; AF6 adds both.

| Field | INITIALISE anchor | Present in RETURNS | Result |
|---|---|---|---|
| queued_event_registry | `L2192` | `L2205` | PASS |
| setup_retry_by_seat_event_ref | `L2193` | `L2205` | PASS |

**Item 2: PASS.**

## Item 3 — AF6 access convention (bare name = RunContext field, never a global)

The NOTE states the convention explicitly at `L2213`–`L2218`: "AF6 ACCESS CONVENTION: every
bare per-run registry name in this document (`EQ`, `queued_event_registry`,
`setup_retry_by_seat_event_ref`, `setup_retry_records`, `applied_transition_registry`,
`transition_rejection_log`, the security-census maps, `waking_origin_assignment_ref`) denotes
the corresponding FIELD of the bound RunContext (reached as `RoundContext.RunContext.<field>`),
NOT an implicit global — so no procedure reads or writes any of them as an undeclared global."
`L2218`–`L2220` further bind the access paths: `RoundInitialise` receives and preserves the
`RunContext` (never re-creates it); `RunEventLoopToHorizon` obtains `RunHookContext` through
`RunContext.RunHookContext`; and `ProcessEventTime` obtains `RunContext` through
`RoundContext.RunContext`.

| Check | Anchor | Result |
|---|---|---|
| Bare per-run name = `RoundContext.RunContext.<field>` | `L2213`–`L2217` | PASS |
| Explicit "NOT an implicit global" / "no ... undeclared global" | `L2217`–`L2218` | PASS |
| ProcessEventTime path via RoundContext.RunContext | `L2219`–`L2220`, `L249` | PASS |

**Item 3: PASS.**

## Item 4 — AF4-needed fields config / prior_round_terminal_state / current_round_context

The three driver-context fields AF4 requires are owned by `RunContext`: SET/INITIALISEd at
`L2198`–`L2200` (with the AF6 rationale block at `L2196`–`L2197`) and returned at `L2207`
(`config, prior_round_terminal_state, current_round_context) # Z1/Z5/AF6`). Their consumer,
`PROCEDURE RoundInitialiseEvent` (AF4 wrapper, `L1024`), uses them exactly as RunContext
fields:

| Field | RunContext ownership | RoundInitialiseEvent use | Result |
|---|---|---|---|
| config | INIT `L2198`, RETURNS `L2207` | reads `SET config <- RunContext.config` (`L1031`) | PASS |
| prior_round_terminal_state | INIT `L2199`, RETURNS `L2207` | reads `SET prior_state <- RunContext.prior_round_terminal_state` (`L1032`) | PASS |
| current_round_context | INIT `L2200`, RETURNS `L2207` | publishes `SET RunContext.current_round_context <- rc` (`L1034`) | PASS |

`RoundInitialiseEvent` resolves `config`/`prior_state` from `RunContext` as runtime context
(never stored payload) and calls `RoundInitialise(config, RunContext, prior_state)` at `L1033`.
**Item 4: PASS.**

## Item 5 — Spot-check: registry usages honour the convention (no contradicting "global")

Spot-checked procedures that use `queued_event_registry`, `setup_retry_by_seat_event_ref`, and
`EQ`, confirming each uses the bare name as a `RunContext` field per the AF6 convention with no
competing "global" declaration.

| Registry / usage site | Anchor | Observation | Result |
|---|---|---|---|
| EQ bound via RoundContext.RunContext in ProcessEventTime | `L249` (`SET RunContext <- RoundContext.RunContext`) | RunContext obtained by reference, not a local/global | PASS |
| queued_event_registry (dispatch) in ProcessEventTime | `L264`, `L266`, `L282`, `L292` | bare-name reads/writes = RunContext field; ProcessEventTime is sole queue-status owner | PASS |
| queued_event_registry (create) in ScheduleEvent | `L709` (`SET queued_event_registry[event_ref] <- record`) | bare-name write, no global declaration | PASS |
| queued_event_registry (cancel) | `L747`, `L749`, `L755` | bare-name status transitions, no global declaration | PASS |
| setup_retry_by_seat_event_ref (reverse-binding read) | `L380`–`L381` (`owner_id <- setup_retry_by_seat_event_ref[er]`) | owner resolved from trusted EventRef; bare-name field | PASS |
| setup_retry_by_seat_event_ref (publish at seating) | `L2518`, `L6063` | bare-name immutable write, no global declaration | PASS |
| RoundInitialise binds RunContext by reference | `L2279` (`RETURNS: RoundContext(..., RunContext, # Q5: RunContext bound by reference`) | reused, not re-created | PASS |
| No contradicting "global" declaration | `L42`, `L562`, `L698` | only uses are "one global discrete-event loop" and "globally unique per run" (seq); neither declares any per-run registry a global | PASS |

Every "global" occurrence in the document was inspected: `L42` refers to the single
discrete-event loop, `L562` and `L698` refer to `seq` being globally unique per run, and the
remaining occurrences (`L2217`–`L2218`, `L2238`, `L2296`) are the convention's own denials
that any registry is an implicit global. No procedure declares `queued_event_registry`,
`setup_retry_by_seat_event_ref`, or `EQ` as a global. **Item 5: PASS.**

## Summary table

| # | Verification item | Result |
|---|---|---|
| 1 | RunInitialise INITIALISEs AND RETURNs every per-run field | PASS |
| 2 | queued_event_registry AND setup_retry_by_seat_event_ref both in RETURNS (`L2205`) | PASS |
| 3 | AF6 access convention (bare name = RunContext field, never a global) (`L2213`–`L2218`) | PASS |
| 4 | config / prior_round_terminal_state / current_round_context present and consumed (`L2198`–`L2200`, `L2207`, `L1031`–`L1034`) | PASS |
| 5 | Spot-check registry usages honour convention; no contradicting "global" | PASS |

## Overall verdict

**PASS.** Correction AF6 is fully realised in the FINAL normative tree. `PROCEDURE
RunInitialise` (`L2175`) is the single one-time owner of every per-run field: each field in
the required minimum set is INITIALISEd/SET (`L2180`–`L2200`) and returned in
`RunContext(...)` (`L2201`–`L2207`), the two previously-omitted maps `queued_event_registry`
and `setup_retry_by_seat_event_ref` are now both in the RETURNS list (`L2205`), the AF6 access
convention binds every bare per-run registry name to a `RoundContext.RunContext.<field>` and
explicitly forbids implicit globals (`L2213`–`L2218`), the AF4 driver-context fields are owned
and consumed correctly (`L1031`–`L1034`), and no procedure contradicts the convention with a
"global" declaration. The algorithm remains PoCol with the idle policy within PoCol, and the
A1 baseline `8.420833333 kWh` is preserved. No defects found.
