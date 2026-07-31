# Stage 1L — Supersession Register (final contract reconciliation)

This register records, in ONE place, every Stage-1L statement that supersedes a prior-stage statement,
so that **no historical Stage-1A..1K lettered artifact is rewritten**: the prior files remain frozen
evidence, and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1L) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1K `StartWake` had no explicit envelope input; sim-driver entry points built a `DriverEventEnvelope` by manually stamping `{ event_time = now, delta_cycle = 0, event_seq = next EQ.event_creation_seq }`; some callers passed an unsupported `driver_envelope = env` to `StartWake` | L1: `ProcessEventTime` materialises ONE `dispatch_envelope` per event; `StartWake` takes an explicit `dispatch_envelope` threaded by every caller; the manual `next EQ.event_creation_seq` stamp is WITHDRAWN (seq owned solely by `ScheduleEvent`); `driver_envelope = env` is removed; §0.9 positional shorthand binds all three fields at every call. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7/§0.7e/§0.7f/§0.9 | correction (complete envelope threading) |
| 2 | Stage-1K `TemplateRefresh` performed its OWN in-line `TRANSITION round_state -> HASHING` (E8), a SECOND `ASSIGNMENT → HASHING` path distinct from `CompleteAssignmentPhase` | L2: `CompleteAssignmentPhase` is the SOLE executable `ASSIGNMENT → HASHING` (R4) owner; `TemplateRefresh` routes through it (the in-line transition removed); the `SOLUTION_PROPAGATION → HASHING` re-entry is a distinct edge, not an assignment-phase completion. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2b/§19/§16b | correction (single phase-completion path) |
| 3 | Stage-1G..1K `§21` "Consequences" prose said a same-timestamp solution discovery "is processed AFTER the lease-expiry decision", contradicting the §21 priority table (discovery item 7 < lease-expiry item 10) and `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4` (discovery first) | L3: the contradicting prose is REMOVED; the ONE canonical order is discovery BEFORE lease expiry, consistent across §0.7, the §21 table, and the G microphase spec; no statement places lease expiry first. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §21 | correction (single canonical order) |
| 4 | Stage-1E..1K `LeaseExpiry` branched on `miner_state` alone (ACTIVE_HASHING renewal vs expiry), with no explicit disposition for a `PAUSED`, `PENDING`, or already-terminal (`SUPERSEDED`/`CLOSED`) expiring version; `RangeReassign` did not require a CLOSED source | L4: `LeaseExpiry` is STATUS-AWARE (`SUPERSEDED`/`CLOSED` no-op; `CURRENT` renew/CLOSE; `PAUSED` CLOSE-without-wake; `PENDING` CLOSE) and CLOSES the source before reassigning; `RangeReassign` asserts `status(source) = CLOSED`. `SUPERSEDED` renewal-only; I18a/I18b hold. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §12/§13 | correction (status-aware terminal handling) |
| 5 | Stage-1K cross-round residency rebase used TWO procedures `FinalizeRoundResidency` + `BeginRoundResidency` (K3), with no idempotence guard against a replayed/retried `RoundInitialise` | L5: a SINGLE idempotent owner `RebaseResidencyAtRoundBoundary` performs the close+reopen, keyed by `boundary_id = (prior_RoundID, new_RoundID)` (a repeat is a no-op); `CloseRoundAssignments` records `round_terminal_time` ONLY; the idle interval is counted exactly once (I19). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §1a/§0.8/§1/§17a; catalogue I19; energy model I5 | correction (single idempotent boundary owner) |
| 6 | Stage-1H..1K `StartWake` scheduled `WakeCompleteEvent` with an explicit `delta_cycle = 0` / `delta_cycle = current_delta_cycle + 1` in the `SCHEDULE` expression, in tension with K8's "`ScheduleEvent` derives `delta_cycle`" | L6: `ScheduleEvent` is the SOLE delta-cycle authority; NO `SCHEDULE`/`ScheduleEvent` caller supplies `delta_cycle`. `StartWake` schedules `WakeCompleteEvent` with ONLY `(target_event_time, target_microphase)` (positive latency `now + wake_latency`; zero latency `now` at `WAKE_COMPLETE`); `ScheduleEvent` derives the delta-cycle. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7e/§0.10 | correction (sole delta-cycle authority) |

## Frozen-artifact discipline (A–K lock)

- No `STAGE_01[A-K]_*` file is modified in Stage 1L (verified by `git diff --name-only <base>`; see
  `STAGE_01L_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and
  test vectors remain byte-frozen; entries 1–6 above are the ONLY sanctioned way their now-superseded
  statements are amended. In particular, `STAGE_01G_EVENT_MICROPHASE_SPEC.md §4` (discovery-first) is the
  frozen authoritative same-timestamp rule and is CONFIRMED by L3, not rewritten.
- The K1–K8 model is PRESERVED and refined: L1 completes the K4 envelope story (one sanctioned source,
  threaded); L2 makes the K2 handoff the SOLE `ASSIGNMENT → HASHING` owner and reuses the K7 census
  capture; L3 reconciles the G5 microphase order with the §21 prose; L4 extends the K6 canonical terminal
  status to a status-aware `LeaseExpiry`; L5 replaces the K3 two-procedure rebase with one idempotent
  owner; L6 completes the K8 scheduler contract as the sole delta-cycle authority.
- Historical invariants (I1..I19, incl. I18a/I18b) are NOT re-opened; Stage 1L amends I19 for the single
  idempotent boundary owner (L5) without altering the frozen invariant IDs.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
