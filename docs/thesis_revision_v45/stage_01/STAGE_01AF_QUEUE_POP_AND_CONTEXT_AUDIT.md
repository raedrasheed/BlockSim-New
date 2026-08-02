# STAGE 01AF — Queue-Pop and Dispatch-Context Audit (Correction AF5)

## Intro

This audit records the Stage-1AF (correction AF5) verification of the atomic queue-pop
and dispatch-context discipline in `ProcessEventTime`, the ONE-representation model of the
event queue, and the strengthening of invariant I21. The scope is the PoCol
(Proof-of-Collaboration) discrete-event protocol: within PoCol the idle policy is a
state-only residency policy (idle time is accounted through `ApplyMinerStateTransition` and
the residency ledger, never by dispatching an ordinary queue event), so the correctness of
the event-loop drain and the single-authoritative queue-status registry directly underwrites
the energy accounting. This is a formal-specification (normative-tree) audit only; it changes
no numeric contract and the A1 energy baseline **8.420833333 kWh** is preserved
(I21 explicitly notes it does not change the A1 baseline).

Sources audited:
- `STAGE_01_PROTOCOL_PSEUDOCODE.md` — `PROCEDURE ProcessEventTime` (from L233), its dispatch
  `LOOP`/`WHILE` with the ATOMIC POP block, the AE10/AF5 coherence-invariant comment block
  (from L597, "ONE REPRESENTATION (AF5)"), `PROCEDURE CancelQueuedEvent` (from L735).
- `STAGE_01_INVARIANT_CATALOGUE.md` — the I21 clause (from L661).

All line anchors below are 1-based line numbers in the named file at the time of audit.

## Per-item findings

| # | Claim under audit | Verdict | Line-anchor citations |
|---|---|:---:|---|
| 1 | `ProcessEventTime` ATOMICALLY POPs `er` FROM `EQ.event_queue`; asserts `registry[er].queue_status = QUEUED`; sets `DISPATCHING`; sets ALL of `EQ.current_event_time` / `current_delta_cycle` / `current_microphase` / `current_event_seq` / `current_event_ref` from `er.*` — in one atomic step. | **PASS** | `STAGE_01_PROTOCOL_PSEUDOCODE.md` L262 `ATOMICALLY:`; L263 `POP er FROM EQ.event_queue`; L264 `SET record <- queued_event_registry[er]`; L265 `ASSERT record EXISTS AND record.queue_status = QUEUED`; L266 `SET ...queue_status <- DISPATCHING`; L267–L271 set `EQ.current_event_time/current_delta_cycle/current_microphase/current_event_seq/current_event_ref` from `er.*`. All five sets, the assert, the POP and the status write are inside the single `ATOMICALLY:` block opened at L262. |
| 2 | After the handler (and after the integrity path) it ATOMICALLY sets `CONSUMED` and CLEARS all `EQ.current_*` fields. | **PASS** | Post-handler: `STAGE_01_PROTOCOL_PSEUDOCODE.md` L291 `ATOMICALLY:`; L292 `SET ...queue_status <- CONSUMED`; L293 `CLEAR EQ.current_event_time, ...current_delta_cycle, ...current_microphase, ...current_event_seq, ...current_event_ref`. Integrity path: L281 `ATOMICALLY:`; L282 `SET ...queue_status <- CONSUMED`; L283 identical `CLEAR` of all five `EQ.current_*`; L284 `CONTINUE`. Both completions are `DISPATCHING -> CONSUMED` + clear in one atomic step. |
| 3 | `EQ.event_queue` is the ONE representation: pending `QUEUED` only; `DISPATCHING`/`CONSUMED`/`CANCELLED` never on it. The ambiguous "by projection" convention is REMOVED; the only surviving `projection` mentions in the pseudocode are the explicit removal statements, not a live convention. | **PASS** | `STAGE_01_PROTOCOL_PSEUDOCODE.md` L598–L603 "ONE REPRESENTATION (AF5): EQ.event_queue holds EXACTLY the pending QUEUED events — nothing else"; L601 "A DISPATCHING / CONSUMED / CANCELLED EventRef is therefore NEVER on EQ.event_queue"; coherence clauses (a)–(f) at L604–L610. A `grep` for `projection` across the pseudocode returns EXACTLY two matches — L254 ("the earlier ambiguous \"by projection\" convention is REMOVED") and L598 ("It is NOT a \"projection\" of the registry (that ambiguous convention is REMOVED)") — both explicit removal statements, no live convention remains. (Note: L566 uses the distinct word "projects" for `EventRef(envelope)` six-field projection, an unrelated concept, and is not a queue-representation convention.) |
| 4 | AE3 re-query preserved: the `WHILE` re-POPs each iteration; a mid-batch cancelled event (removed from `EQ` by `CancelQueuedEvent`) is never POPped; dispatch is exactly one event per iteration. | **PASS** | `STAGE_01_PROTOCOL_PSEUDOCODE.md` L258 `WHILE a QUEUED EventRef exists at (t, current_delta_cycle) on EQ.event_queue:` — re-evaluated each iteration; L263 pops exactly one `er` per iteration; L253–L257 "RE-POP the smallest each iteration ... CancelQueuedEvent (AE1) ATOMICALLY removes a cancelled event from EQ.event_queue, a cancelled event can never be POPped — no stale-snapshot skip guard is needed"; L294–L296 "the WHILE RE-POPS EQ.event_queue — a handler may have CANCELLED a later same-cycle event (already removed ... so never POPped)". `CancelQueuedEvent` L753–L755 atomically `REMOVE EventRef FROM EQ.event_queue` + `SET ...queue_status <- CANCELLED`, so the removed event is absent from the next re-POP. One POP (L263) and one handler `CALL inv.procedure` (L289) per iteration. |
| 5 | `BuildHandlerInvocation` is invoked with `RunContext` resolved from `RoundContext.RunContext`. | **PASS** | `STAGE_01_PROTOCOL_PSEUDOCODE.md` L249 `SET RunContext <- RoundContext.RunContext` (AF6); L288 `SET inv <- CALL BuildHandlerInvocation(descriptor(record.event_type), record, RoundContext, RunContext, ctx)` — the `RunContext` argument is the value bound at L249. |
| 6 | The finalisation assertions after the drain still hold (no event at `t` remains `QUEUED` or `DISPATCHING`). | **PASS** | `STAGE_01_PROTOCOL_PSEUDOCODE.md` L342 `ASSERT no ordinary event with event_time = t has queue_status QUEUED OR DISPATCHING` (R1/AD4/AE10(e)); reinforced by L343 (`security_census_dirty[t] = false`), L344–L345 (no `DUE` continuation at `t`), L346–L347 (no `DUE` recovery-work at `t`) before L348 `ADD t to finalised_event_times`. The drain-to-quiescence assertion is intact and is reached only after the `LOOP`/`WHILE` drain completes. |
| 7 | I21 is strengthened with an AF5 one-representation / atomic-pop clause. | **PASS** | `STAGE_01_INVARIANT_CATALOGUE.md` L661 heading "...coherent at all times (Stage 1AE, AE10; strengthened Stage 1AF, AF5)"; L672–L679 "Stage-1AF strengthening (AF5 — ONE representation + atomic pop)" — single representation, no separate "projection" convention, atomic POP moving `QUEUED -> DISPATCHING` and setting complete `EQ.current_*` in one step, atomic `DISPATCHING -> CONSUMED` + clear, so (a)–(f) hold "by construction rather than by a projection convention"; enforcement point updated at L683–L686; A1 baseline preservation noted at L681. |

## Overall verdict

**PASS (7 of 7).** The final normative tree implements correction AF5 exactly as specified:
`ProcessEventTime` performs an atomic POP-with-ownership that sets the complete dispatch
context indivisibly, completes the lifecycle atomically (`DISPATCHING -> CONSUMED` + clear)
on both the handler and integrity paths, treats `EQ.event_queue` as the single representation
of the pending frontier with the "by projection" convention fully removed, preserves the AE3
per-iteration re-POP so a mid-batch cancelled event is never dispatched, resolves `RunContext`
from `RoundContext.RunContext` for `BuildHandlerInvocation`, retains the post-drain
finalisation assertions, and I21 is strengthened with the AF5 one-representation / atomic-pop
clause. No defect was found; the A1 baseline 8.420833333 kWh is preserved.
