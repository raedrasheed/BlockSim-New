# Stage 1AC — Supersession Register

Stage 1AC supersedes specific Stage-1AB statements about the scheduler result contract, the dispatch-ownership reference,
the `SetupRetryEvent` guard order, the scope of an integrity abort, the status-transition discipline, and the retry
record's event-reference field. Each row records the SUPERSEDED statement, the SUPERSEDING Stage-1AC statement, and the
authoritative location in the current `STAGE_01_PROTOCOL_PSEUDOCODE.md` (line anchors approximate). No Stage-1A–1AB
lettered artifact (`STAGE_01[A-Z]_*` / `STAGE_01AA_*` / `STAGE_01AB_*`) is modified; the historical layers remain frozen,
and this register is the sole record of what Stage 1AC overrides.

## 1. Superseded → superseding statements

| # | Superseded (Stage 1AB) | Superseding (Stage 1AC) | Authoritative location |
|--:|------------------------|--------------------------|------------------------|
| AC1 | `ScheduleEvent` returned `scheduled(envelope)` while callers bound `scheduled(event_ref)` / accessed `.event_ref` — `event_ref`, `envelope`, and `dispatched_event_ref` were silently interchangeable and there was no declared `EventRef` type | `STRUCTURE EventRef` (six-field canonical immutable reference) is declared; `ScheduleEvent` derives one and returns `scheduled(EventRef, envelope)`; cancellation / retry ownership / dispatch ownership all use `EventRef` | `STRUCTURE EventRef` (~L432); `ScheduleEvent` (~L503, RETURNS ~L506) |
| AC2 | `dispatched_event_ref` was described as "materialised by ProcessEventTime … derivable from dispatch_envelope" (a prose derivation), not a dispatcher-owned injected value | `EventQueueContext.current_event_ref` is set by `ProcessEventTime` to `EventRef(e)`, injected as `dispatched_event_ref`, and cleared after the handler returns; `SetupRetryEvent` receives it as a mandatory input from this path, never from its payload | `EventQueueContext` (~L379); `ProcessEventTime` (~L226–L228); `SetupRetryEvent` INPUTS (~L2054); seating table row (~L599) |
| AC3 | `SetupRetryEvent` validated the payload (integrity abort) BEFORE the non-SEATED replay check, so a terminal replay with a corrupted payload could abort a round | The guard order resolves the record, checks EventRef ownership, then suppresses a non-SEATED replay BEFORE any payload-integrity handling | `SetupRetryEvent` EFFECTS steps (1)–(6) (~L2067–L2130) |
| AC4 | The integrity abort used the incoming PAYLOAD fields to decide the record's round membership, so a corrupted historical retry could abort a later round | Stale/closed disposition is decided from the IMMUTABLE record fields (`rec.RoundID`, the record's round state, `rec.TemplateID_at_seat`); an older/terminal-round record is terminalised, never aborting the current round | `SetupRetryEvent` step (5) (~L2105–L2130) |
| AC5 | A known genuine dispatch with a corrupted payload was terminalised, but the malformed-envelope case and the current-round scoping of the abort were not separated from the foreign-ref case | Cases A/B/C are explicit: unknown id → stale no-op; foreign `EventRef` → stale no-op leaving the record SEATED; genuine `EventRef` + incomplete envelope/payload mismatch → current-round integrity abort only if the record is of the current nonterminal round | `SetupRetryEvent` steps (1)–(3),(6) (~L2067–L2145) |
| AC6 | A guard-driven abort wrote `status <- ABORTED` directly (a straight SEATED → ABORTED), and `CancelSetupRetriesForRound` could set `CANCELLED` on a record another path then ABORTED (a terminal → terminal rewrite risk) | Every aborting guard moves `SEATED → APPLYING` before `RoundAbort` and finishes `APPLYING → ABORTED`; `CancelSetupRetriesForRound` sets `terminal_closure_pending` on an `APPLYING` record; `CANCELLED → ABORTED` is forbidden | `SetupRetryEvent` abort blocks (~L2131–L2175); `CancelSetupRetriesForRound` (~L2223) |
| AC7 | Status writes were direct keyed `UPDATE …status <- …` with no declared transition table or guard | `SetSetupRetryStatus` is the sole status writer and enforces the authoritative `setup_retry_status_transitions` table, rejecting every illegal (esp. terminal → terminal) transition with no mutation | `PROCEDURE SetSetupRetryStatus` (~L2290) |
| AC8 | The record's `event_ref` was set to null on cancellation (AB6), erasing the identity needed for replay-ownership auditing | The record carries `seat_event_ref : EventRef` (immutable) + `event_queue_status : EventQueueStatus`; ownership uses `seat_event_ref`; cancellation sets `event_queue_status <- CANCELLED` and preserves `seat_event_ref` | record def (§0.8/RunInitialise ~L1616); seats (~L1944, ~L5351); `CancelSetupRetriesForRound` (~L2219) |

## 2. Companion normative-document supersessions

| Document | Superseding Stage-1AC addendum |
|----------|-------------------------------|
| `STAGE_01_ROUND_STATE_MACHINE.md` | §3.10g Stage-1AC addendum (AC1–AC8); §3.10a–§3.10f retained as the frozen W/X/Y/Z/AA/AB layers |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I16 Stage-1AC clause (AC1–AC8) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1AC terminology addendum (`EventRef`, `current_event_ref` / `dispatched_event_ref`, `seat_event_ref` + `event_queue_status`, `EventQueueStatus`, the `SetupRetryStatus` transition table + `SetSetupRetryStatus`, `setup_retry_payload_integrity_failure`) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R206–R214 (AC1–AC8 + the TV244–TV251 block) |

The miner state machine is not modified — AC1–AC8 concern the scheduler/dispatcher and the retry-record lifecycle only.

## 3. Freeze statement

Stage-1A through Stage-1AB lettered artifacts (`STAGE_01[A-Z]_*`, `STAGE_01AA_*`, `STAGE_01AB_*`) are byte-identical to the
Stage-1AB parent commit (`b575bfa64c25571ffe4359557011a316492e374c`). Stage 1AC modifies only the five normative
`STAGE_01_*` documents it touches and adds the twelve `STAGE_01AC_*` deliverables; every override of a prior-letter
statement is recorded in this register.
