# Stage 1M — Correction Report (minimal executable closure)

**Branch.** `thesis-v45-pocol-stage1m-minimal-executable-closure`
**Base.** `0a272a3ff22cf11187045ff694241cdc6a9b1b93` (Stage 1L).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1L lettered artifacts unmodified (A–L-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**. No
property (energy, security, fairness, incentive) is claimed. The A1 baseline is unchanged
(`8.420833333 kWh`); any modeled energy change is attributable ONLY to reduced active power-time. No new
consensus feature — M1…M6 make the Stage-1L contract executable and internally complete.

## M1 — Remove the transition-envelope shorthand

The Stage-1L POSITIONAL SHORTHAND (a positional `ApplyMinerStateTransition(…, now, reason=…)` that
implicitly read `EQ.current_event_time/current_delta_cycle/current_event_seq`) is REMOVED (§0.9). Every
procedure that directly OR indirectly calls the hook now carries an explicit `dispatch_envelope` input and
threads it unchanged, and every hook call spells out `event_time = dispatch_envelope.event_time`,
`delta_cycle = dispatch_envelope.delta_cycle`, `event_seq = dispatch_envelope.event_seq`. A queued handler
(`WakeCompleteEvent`, `HashWorkEvent`, `CertificateArrival`, `BlockAcceptancePoint`, `ResumeFromPause`)
obtains its envelope from its own dispatched event; a sim-driver entry point (`MinerRegister`,
`PrepareParticipantsForNewRound`, `ReserveActivate`, `LeaseExpiry`, `AdversarialParticipationChangeEvent`,
`AcceptanceBatchFinalize`, `FullRangeExhaustNoSolution`) is itself dispatched and receives the same; a
synchronous nested procedure (`StartWake`, `EnterLowPowerListen`, `ExhaustionAdjudicate`,
`CloseRoundAssignments`, `CloseTemplateAssignments`, `ScheduleSolutionPropagation`, `EarlyStopVerify`,
`CompleteAssignmentPhase`, `HandlePropagationFailure`, `ValidBlockAccept`, `RoundAbort`, `RangeAssign`,
`RangeReassign`, `TemplateRefresh`) receives the same envelope as an explicit input. All 14 LIVE hook
call sites are now explicit (a 15th `grep` match is the §0.3 normative prose "a state change is always
written `CALL ApplyMinerStateTransition(...)`", not an invocation); no procedure stamps `next
EQ.event_creation_seq`. Updated: pseudocode
§0.7/§0.9/§0.10/§2b/§3/§4/§5/§6/§7/§8a/§10/§12/§13/§16a–d/§17/§17a/§18/§19/§20. Audit:
`STAGE_01M_TRANSITION_ENVELOPE_AUDIT.md`. TV98.

## M2 — Capture census on every floor-applicable round entry

A single round-state transition helper `TransitionRoundState` (§2a-bis) bumps `state_version` and, whenever
the NEW state is floor-applicable (`HASHING`, `SOLUTION_PROPAGATION`, `SECURITY_RECOVERY`), captures the
applicability-entry census at `dispatch_envelope.event_time`. All three executable floor-applicable ENTRY
transitions route through it: `ASSIGNMENT → HASHING` (`CompleteAssignmentPhase`), `HASHING →
SOLUTION_PROPAGATION` (`ScheduleSolutionPropagation`), and — the key fix — the `SOLUTION_PROPAGATION →
HASHING` re-entry in `HandlePropagationFailure`, which now captures a census EVEN when no miner was paused,
all resumes carry positive wake latency, or `H_active` did not change. The ONE floor-applicable entry not
routed through the helper is the `SecurityFloorEvaluate` epilogue's `→ SECURITY_RECOVERY` (its census is the
one the epilogue just evaluated; re-dirtying a mid-epilogue `event_time` is forbidden) — a documented
exception, not a gap. There is no executable `SECURITY_RECOVERY → HASHING` restore transition (round SM
R13). Updated: pseudocode §2a-bis/§2b/§16b/§16d. Audit: `STAGE_01M_APPLICABILITY_ENTRY_AUDIT.md`. TV99.

## M3 — Make PENDING lease expiry executable

`LeaseExpiry` `CASE PENDING` is now executable: it (1) identifies and (2) CANCELS the exact pending
`WakeCompleteEvent` for `AssignmentID + assignment_version + MinerID`; (3) if the holder is `WAKING` for
this head, moves it `WAKING → OFFLINE` (`reason = lease_expired_while_waking`) with the exact
`dispatch_envelope`; (4) CLOSES the head (`CLOSED`/`expired`/`lease_expiry`); (5) preserves the accepted
searched prefix; (6) exposes only the accepted unsearched suffix; (7) reassigns only after the source is
CLOSED. `CASE PAUSED` additionally cancels candidate-specific `ResumeFromPause`/`WakeCompleteEvent` for the
closed head. `WakeCompleteEvent` BEGINS with an explicit stale-target guard (`status ∈ {PENDING, PAUSED}`,
current round/template epoch, the miner's own live head) returning `stale_wake_noop` — independent of the
`HashWorkEvent` G9 guard, which does not protect wakes. Updated: pseudocode §12 (`LeaseExpiry`), §0.10
(`WakeCompleteEvent`). Audit: `STAGE_01M_PENDING_LEASE_EXPIRY_AUDIT.md`. TV100/TV101.

## M4 — One residency-boundary owner in executable text

`CloseRoundAssignments` no longer finalises residency/energy — the in-line `finalise state durations and
energy to the exact closure time` line is REMOVED; it records `round_terminal_time` ONLY. The single
idempotent owner is generalised from `RebaseResidencyAtRoundBoundary` to `SettleResidencyBoundary`
(§1a), with two modes: `REBASE_TO_NEXT_ROUND` (close old + reopen new at the same `boundary_time`, no
transition energy — called by `RoundInitialise`) and `FINAL_RUN_END` (close all open intervals at the run
horizon, no reopen — called by `RoundAbort` before its I5/I6/I7 accounting checks). It is idempotent via
`boundary_id`, so a replayed `RoundInitialise`/`RoundAbort` cannot double-close. Invariant **I19** and the
energy-model I5 duration reconciliation are updated; TV96 (frozen Stage-1L) is superseded on paper by the
new TV102. Updated: pseudocode §1a/§0.8/§1/§17a/§20; catalogue I19; energy model §I5. Audit:
`STAGE_01M_RESIDENCY_SINGLE_OWNER_AUDIT.md`. TV102.

## M5 — Every enqueue conforms to ScheduleEvent

A canonical event-type → microphase mapping is added (§0.7g): `FULL_BLOCK_ARRIVAL`, `CERTIFICATE_ARRIVAL`,
`HASH_WORK`, `LEASE_EXPIRY`, `WAKE_COMPLETE`, `RESUME`, `PARTICIPATION_CHANGE`, `MONITORING`. Every
operational enqueue is a `ScheduleEvent` call (or its `SCHEDULE` shorthand) supplying an EXPLICIT
`target_microphase`; the previously bare `SCHEDULE event` expressions for `HashWorkEvent`,
`CertificateArrival`, `BlockAcceptancePoint`, and `ResumeFromPause` are converted to explicit
`ScheduleEvent` calls with a `target_microphase`. Every event-producing loop is stably sorted before the
seq is assigned: `TemplateRefresh` (`SORT eligible BY MinerID`), `CloseRoundAssignments` /
`CloseTemplateAssignments` (`SORT BY (holder MinerID, AssignmentID)`), plus the already-sorted
recipient/resume loops. Updated: pseudocode §0.7g/§5/§16b/§16d/§17a/§19. Audit:
`STAGE_01M_SCHEDULER_MICROPHASE_AUDIT.md`. TV103.

## M6 — Corrected blocking test vectors

TV98 (M1 explicit envelopes for REGISTERED/RESERVE/LOW_POWER_LISTEN wakes), TV99 (M2 census on
`SOLUTION_PROPAGATION → HASHING` re-entry with no paused miner), TV100 (M3 PENDING lease expiry while
`WAKING` — wake cancelled, `WAKING → OFFLINE`, close, then reassign), TV101 (M3 stale `WakeCompleteEvent`
for a CLOSED assignment → `stale_wake_noop`), TV102 (M4 `CloseRoundAssignments` records `round_terminal_time`
but does not close a residency interval; the single boundary owner closes/reopens once), TV103 (M5 every
scheduled event has a microphase and every event-producing miner loop is stably sorted). Deliverable:
`STAGE_01M_SEMANTIC_TEST_VECTORS.md`.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.9 shorthand removed + explicit-threading mandate (M1); dispatch_envelope threaded through every hook-reaching procedure + all 15 hook calls explicit (M1); §2a-bis `TransitionRoundState` helper + routed floor-applicable entries (M2); §0.10 WakeCompleteEvent stale guard (M3); §12 executable PENDING/PAUSED lease expiry (M3); §1a `SettleResidencyBoundary` REBASE/FINAL_RUN_END (M4); §17a CloseRoundAssignments finalisation removed (M4); §20 RoundAbort FINAL_RUN_END settle (M4); §0.7g event-type→microphase mapping + explicit `ScheduleEvent` enqueues + sorted loops (M5) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19 updated: `SettleResidencyBoundary` (REBASE/FINAL_RUN_END); CloseRoundAssignments no finalisation (M4) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1M addendum (M1–M6); residency entry annotated renamed/generalised |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | R77/R87 updated to `SettleResidencyBoundary`; rows R89–R94 (M1–M6) |
| `STAGE_01_ENERGY_MODEL_SPECIFICATION.md` | I5 boundary-settle paragraph updated (M4) |
| `STAGE_01M_*` (11 new deliverables) | this report + transition-envelope / applicability-entry / pending-lease-expiry / residency-single-owner / scheduler-microphase audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1L lettered artifact is
modified. The specification conforms to M1–M6 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9,
G1–G11, H1–H9, I-01…I-08, J1–J9, K1–K8, and L1–L6. Name remains PoCol; the idle policy within PoCol is
described as a mechanism only; A1 baseline unchanged.
