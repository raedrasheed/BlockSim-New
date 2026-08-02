# Stage 1AG — Wake-Version Payload Audit (correction AG2)

## Intro

This audit verifies correction **AG2** — the event-scheduled wake (`StartWake` / `WakeCompleteEvent`, §0.10)
now carries the **exact wake-origin `assignment_version`** end to end, so an older wake can never activate a
renewed or superseded version of its target assignment. The consensus algorithm remains **PoCol**; the
mechanism under study is **the idle policy within PoCol**; the **A1 baseline (`8.420833333 kWh`)** is preserved
and unchanged by this documentation-only revision. No executable source, configuration, or experiment is
touched.

All line anchors below refer to the FINAL normative tree in `STAGE_01_PROTOCOL_PSEUDOCODE.md`.

## Per-item verification

| # | Claim | Evidence (line anchors) | Verdict |
|---|-------|-------------------------|:------:|
| 1 | `StartWake`'s `ScheduleEvent(WakeCompleteEvent, …)` seat payload is EXACTLY `{MinerID, AssignmentID(target_assignment), assignment_version(target_assignment)}` — `assignment_version` present (omitting it is `rejected_payload_schema_mismatch` under AF3). | `STAGE_01_PROTOCOL_PSEUDOCODE.md:2189-2192` — `SET seat <- CALL ScheduleEvent(EQ, RoundContext, WakeCompleteEvent, target_event_time = target_time, target_microphase = WAKE_COMPLETE, {MinerID, AssignmentID(target_assignment), assignment_version(target_assignment)}, post_epilogue_context = post_ctx)`. AG2 rationale at `:2186-2188` (exact closed key set; omission rejected). Descriptor's `allowed_payload_keys` (EXACT closed set) `{ MinerID : MinerID, AssignmentID : AssignmentID, assignment_version : Integer }` at `:1018`. | **PASS** |
| 2 | The `wake_seated` result retains `assignment_version` (the exact wake-origin version); `RETURNS` lists `wake_seated(AssignmentID, assignment_version, WakeEventRef, wake_target_time, resulting_state)`. | `STAGE_01_PROTOCOL_PSEUDOCODE.md:2215-2217` — `RETURN wake_seated(AssignmentID = AssignmentID(target_assignment), assignment_version = assignment_version(target_assignment), WakeEventRef = wake_event_ref, wake_target_time = target_time, resulting_state = WAKING)`. `RETURNS:` clause at `:2218` — `wake_seated(AssignmentID, assignment_version, WakeEventRef, wake_target_time, resulting_state = WAKING) \| …`. AG2 retention note at `:2213-2214`. | **PASS** |
| 3 | `WakeCompleteEvent` resolves `target_assignment = version(AssignmentID, assignment_version)` (via the dispatcher / `BuildHandlerInvocation`) and verifies `wake_origin_version` equals the miner's live-head version BEFORE any transition; a renewed/superseded version returns `stale_wake_noop` and is never activated. | Descriptor "Derived by handler (NOT payload)" column `target_assignment = version(AssignmentID, assignment_version)` at `STAGE_01_PROTOCOL_PSEUDOCODE.md:1018`; binding-map row `(AssignmentID, assignment_version) -> target_assignment via version(…)` at `:1049`. `BuildHandlerInvocation` version resolver at `:219-220`, restated in its NOTE at `:245`. Guard in `WakeCompleteEvent`: `wake_origin_version <- assignment_version(target_assignment)` at `:2241`; guard clause `wake_origin_version != assignment_version(miner's bound live head for AssignmentID(target_assignment))` → `RETURN stale_wake_noop` at `:2245-2246`; guard "runs FIRST, BEFORE any state transition" at `:2234` and `:2237-2240`; `stale_wake_noop` in `RETURNS` at `:2298`; NOTE at `:2301-2304`. | **PASS** |
| 4 | Every `wake_seated(` positional match in callers uses the updated 5-field arity `(waid, wav, wref, wtt, ws)` — none broken by the added `assignment_version`. | 5-field positional matches: `STAGE_01_PROTOCOL_PSEUDOCODE.md:2725`, `:2728` (participant setup), `:3317` (RangeAssign), `:5580` (resume path), `:6314`, `:6317` (refresh setup). Wildcard disposition checks unaffected by arity: `:4516` (`IF wr = wake_seated(...)`), `:5397` (`IF wr != wake_seated(...)`). No caller retains a 4-field `wake_seated(waid, wref, wtt, ws)` form. | **PASS** |
| 5 | `StartWake` is the SOLE `WakeCompleteEvent` seating site (`ScheduleEvent(…WakeCompleteEvent…)`) — no site omits `assignment_version`. | The only `ScheduleEvent(… WakeCompleteEvent …)` call is `STAGE_01_PROTOCOL_PSEUDOCODE.md:2189` (inside `StartWake`). All other `WakeCompleteEvent` references are prose/tables confirming `StartWake` ownership (`:550-554`, `:909`, `:911`, `:2173`, `:2220`) or CANCEL/registry lookups; there is no raw enqueue of `WakeCompleteEvent`. The single seating call carries `assignment_version` (item 1). | **PASS** |

## Overall verdict

**PASS.** Correction AG2 is fully realized in the final normative tree: the wake seat payload carries the exact
`assignment_version` (item 1) under the closed descriptor schema, the `wake_seated` transaction result and its
`RETURNS` signature retain that version (item 2), `WakeCompleteEvent` resolves and version-guards the
wake-origin version before any transition — returning `stale_wake_noop` for a renewed/superseded target (item
3), all caller pattern-matches use the 5-field arity or an arity-agnostic wildcard (item 4), and `StartWake`
remains the sole seating site with no version-omitting enqueue (item 5). No defects found. PoCol, the idle
policy within PoCol, and the A1 baseline `8.420833333 kWh` are preserved.
