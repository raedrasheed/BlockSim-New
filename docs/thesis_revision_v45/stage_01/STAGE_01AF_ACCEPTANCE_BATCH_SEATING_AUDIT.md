# Stage 1AF — Acceptance-Batch Seating Audit (correction AF8)

## Intro

This audit verifies correction **AF8**: the replacement of the descriptive prose
"ENSURE exactly one AcceptanceBatchFinalize … is scheduled" with the named single-seat owner
`SeatAcceptanceBatchFinalize`, which seats the one `AcceptanceBatchFinalize` per
`(acceptance_timestamp, acceptance_point)` through the sole enqueue interface, enforces exactly one
live seat via the per-round `acceptance_batch_finalize_seat` map, stores the cancellable `EventRef`,
and is replay-safe. `RoundAbort` cancels every live seat.

Scope of the underlying protocol is unchanged: the algorithm remains **PoCol**; the mechanism under
audit is the **idle policy within PoCol**; the **A1 baseline (`8.420833333 kWh`)** is preserved
(no executable source, configuration, DOCX, or PDF was touched; no experiment was run).

All line anchors below refer to
`STAGE_01_PROTOCOL_PSEUDOCODE.md` unless another file is named.

## Verification table

| # | Claim | Verdict | Line-anchor evidence |
|---|-------|---------|----------------------|
| 1 | The prose "ENSURE exactly one AcceptanceBatchFinalize … is scheduled" is REPLACED by `CALL SeatAcceptanceBatchFinalize(RoundContext, acceptance_timestamp = now, acceptance_point = …, source_context = …)` inside `BlockAcceptancePoint`; the ENSURE directive is gone. | **PASS** | `BlockAcceptancePoint` (§16d) issues `CALL SeatAcceptanceBatchFinalize(RoundContext, acceptance_timestamp = now, acceptance_point = RoundContext.acceptance_point, source_context = ORDINARY_DISPATCH(EQ.current_event_ref))` at **5478–5480**, flagged "was raw ENSURE prose" at **5476**. A repo-wide grep for `ENSURE … (schedul|AcceptanceBatch|Finalize)` finds no residual directive for `AcceptanceBatchFinalize`: the only match in the pseudocode is the NOTE at **5520** that documents the replacement ("replacing the raw prose "ENSURE ... is scheduled""); the other `ENSURE exactly one … is scheduled` hits belong to `CompleteSecurityRecovery` (§9/N2), a distinct procedure out of scope. |
| 2 | `SeatAcceptanceBatchFinalize` seats through `ScheduleEvent` with the authoritative descriptor payload `{ acceptance_timestamp, acceptance_point }` at microphase `ACCEPTANCE_ARBITRATION` — never a raw enqueue. | **PASS** | Seat call `CALL ScheduleEvent(EQ, RoundContext, AcceptanceBatchFinalize, target_event_time = acceptance_timestamp, target_microphase = ACCEPTANCE_ARBITRATION, {acceptance_timestamp = acceptance_timestamp, acceptance_point = acceptance_point})` at **5510–5512**, prefaced "seat through the SOLE enqueue interface with the AUTHORITATIVE §0.7g descriptor payload — never a raw enqueue" at **5509**. The §0.7g descriptor row **953** fixes the exact closed key set `{ acceptance_timestamp : SimulationTime, acceptance_point : AcceptancePoint }`, target microphase `ACCEPTANCE_ARBITRATION`, and `stable_tie_key = (acceptance_timestamp, acceptance_point)`; the binding row **980** maps both keys straight through. `ScheduleEvent` (§0.7, **620–733**) is declared the SOLE enqueue interface (NOTE **722**). |
| 3 | Enforces EXACTLY ONE live seat per `(acceptance_timestamp, acceptance_point)` via `acceptance_batch_finalize_seat`; a second same-key arrival returns `acceptance_batch_finalize_already_seated` (idempotent/replay-safe); a prior DISPATCHING/terminal seat returns `acceptance_batch_finalize_seat_terminal` (no re-seat). | **PASS** | `SET key <- (acceptance_timestamp, acceptance_point)` at **5501**; `IF acceptance_batch_finalize_seat[key] EXISTS` at **5502–5503**; if the stored `EventRef` is still `QUEUED`, `RETURN acceptance_batch_finalize_already_seated(existing)` at **5505** ("idempotent — exactly one LIVE seat (replay-safe)"); otherwise a prior `DISPATCHING/CONSUMED/CANCELLED` seat is terminal and `RETURN acceptance_batch_finalize_seat_terminal(existing, queued_event_registry[existing].queue_status)` at **5506–5508** (no re-seat). Guard comment at **5498–5500**. |
| 4 | Stores the seated `EventRef` so it is cancellable via `CancelQueuedEvent`; a `ScheduleEvent` rejection returns `acceptance_batch_finalize_seat_failed(r)`; it NEVER creates an unregistered queued event. | **PASS** | On `r = scheduled(event_ref, record)`, `SET acceptance_batch_finalize_seat[key] <- event_ref` at **5514** ("store the seated EventRef (cancellable via CancelQueuedEvent)"), then `RETURN acceptance_batch_finalize_seated(event_ref)` at **5515**; a non-`scheduled` result yields `RETURN acceptance_batch_finalize_seat_failed(r)` at **5516**. No unregistered event can exist: `ScheduleEvent` creates the central `queued_event_record (queue_status = QUEUED)` and inserts into `EQ` as ONE atomic both-or-neither transaction (**703–710**, AE8) and returns a structured rejection BEFORE any mutation (**711–728**); `CancelQueuedEvent` is the sole queue-owner cancellation operation resolving that same registry (**735–763**). |
| 5 | `acceptance_batch_finalize_seat` is INITIALISEd in `RoundInitialise` and returned in the `RoundContext` registry list (per-round, I-04). | **PASS** | Under the "I-04: PER-ROUND registries -- reset FRESH every round" banner (**2238**): `INITIALISE acceptance_batch_finalize_seat <- empty map` at **2241**; returned in the `RoundContext(...)` per-round registry list at **2281** (tagged `# AF8`). NOTE **2290–2296** reaffirms every per-round registry is explicitly owned, no implicit global. |
| 6 | `RoundAbort` cancels every live `acceptance_batch_finalize` seat via `CancelQueuedEvent` and clears the map. | **PASS** | `RoundAbort` (§ N1): `FOR EACH key IN SORT(keys of acceptance_batch_finalize_seat BY (acceptance_timestamp, acceptance_point) ascending): CALL CancelQueuedEvent(acceptance_batch_finalize_seat[key], cancellation_reason = round_aborted_cleanup, cancellation_context = dispatch_envelope)` at **6104–6105**, then `CLEAR acceptance_batch_finalize_seat` at **6106** ("no pending finalize seat survives closure"), guided by comment **6103**. Cancellation is idempotent: `CancelQueuedEvent` is a declared no-op for a seat already `DISPATCHING`/terminal (**758–763**). |
| 7 | The RETURNS union is complete and consistent. | **PASS** | Declared `RETURNS: acceptance_batch_finalize_seated(EventRef) \| acceptance_batch_finalize_already_seated(EventRef) \| acceptance_batch_finalize_seat_terminal(EventRef, status) \| acceptance_batch_finalize_seat_failed(reason)` at **5517–5518**. Every `RETURN` in the body maps to exactly one declared variant: `already_seated` (**5505**), `seat_terminal` (**5508**), `seated` (**5515**), `seat_failed` (**5516**). No body return is undeclared and no declared variant is unreachable. |

## Overall verdict

**PASS (7 / 7).** Correction AF8 is fully realised in the final normative tree. `BlockAcceptancePoint`
delegates to the named owner `SeatAcceptanceBatchFinalize`, which seats the single
`AcceptanceBatchFinalize` per `(acceptance_timestamp, acceptance_point)` through `ScheduleEvent` with
the exact §0.7g descriptor payload at microphase `ACCEPTANCE_ARBITRATION`, enforces one live seat via
the per-round `acceptance_batch_finalize_seat` map (idempotent/replay-safe, terminal-safe), stores the
cancellable `EventRef`, surfaces structured `..._seat_failed` rejections, creates no unregistered
queued event, is initialised and returned per-round under I-04, and is cancelled and cleared by
`RoundAbort`. The RETURNS union is complete and consistent. No defect found. PoCol scope, the idle
policy within PoCol, and the A1 baseline (`8.420833333 kWh`) are preserved.
