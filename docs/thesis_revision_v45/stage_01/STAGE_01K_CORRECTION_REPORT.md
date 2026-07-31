# Stage 1K — Correction Report (core-handoff closure)

**Branch.** `thesis-v45-pocol-stage1k-core-handoff-closure`
**Base.** `431b0d410545f114d2309376a173566c6d689035` (Stage 1J).
**Scope.** Documentation only — no executable source, configuration, DOCX, PDF, or experiment
changes. Protected DOCX drafts byte-identical (draft-42 `2c3afdc5…`, draft-44 `a31400bc…`); Stage
1A–1J artifacts unmodified (A–J-lock).

**Naming rule (binding).** Algorithm is **PoCol**; mechanism is **the idle policy within PoCol**.
Forbidden name strings appear only in prohibition clauses. No property (energy, security, fairness,
incentive) is claimed. The A1 baseline is unchanged (`8.420833333 kWh`); any modeled energy change is
attributable ONLY to reduced active power-time. No new consensus feature — K1…K8 are core-handoff
closure (participation, phase-completion, residency-continuity, envelope, registry, termination,
applicability, scheduler-context) corrections.

## K1 — Complete next-round participant eligibility

`PrepareParticipantsForNewRound` gives EVERY parked `LOW_POWER_LISTEN` miner an explicit next-round
disposition; `VALID_SOLUTION_VERIFIED` no longer falls into DEFAULT/CONTINUE. A finder/recipient parked
as `VALID_SOLUTION_VERIFIED` (or `ROUND_ACCEPTED`/`ROUND_ABORTED`) is archived, its old head confirmed
CLOSED (never reopened, J7/I18b), and re-assigned a fresh `ORIGINAL` `PENDING` bound to the NEW
`RoundID`/`TemplateID` via T10. `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` apply the new-round policy
explicitly. Updated: pseudocode §2a. Audit: `STAGE_01K_NEXT_ROUND_PARTICIPATION_AUDIT.md`. TV81/TV82.

## K2 — Executable assignment-phase completion

New procedure `CompleteAssignmentPhase` performs the executable `ASSIGNMENT → HASHING` transition (R4)
after asserting the intended set is well-formed (each `PENDING` bound to the current `(RoundID,
TemplateID)`, disjoint I1, one live head I18b; none bound to an old epoch), then captures the
applicability-entry census (K7). `PrepareParticipantsForNewRound` calls it. A `HashWorkEvent` is a no-op
while the round is still `ASSIGNMENT`. Updated: pseudocode §2b/§2a/§5. Audit:
`STAGE_01K_ASSIGNMENT_PHASE_AUDIT.md`. TV83/TV84.

## K3 — Cross-round residency continuity

`FinalizeRoundResidency(boundary_time)` closes every open per-miner interval and attributes its energy
to the old round; `BeginRoundResidency(boundary_time)` reopens the SAME state at the identical
`boundary_time` for the new round with NO transition energy. Covers `LOW_POWER_LISTEN`, `REGISTERED`,
`RESERVE`, `OFFLINE`, `DISQUALIFIED`. The idle interval between round closure and the next round's
`StartWake` is counted exactly once. Invariant **I19** amended for cross-round continuity. Updated:
pseudocode §1a/§0.8/§1 (`RoundInitialise` rebase); catalogue I19. Audit:
`STAGE_01K_CROSS_ROUND_RESIDENCY_AUDIT.md`. TV85.

## K4 — Explicit driver event envelopes

Every `ApplyMinerStateTransition` call has a DEFINED `(event_time, delta_cycle, event_seq)`; queued
handlers use the dispatching envelope, sim-driver entry points carry an explicit `DriverEventEnvelope`
(§0.7f). `MinerRegister`, `PrepareParticipantsForNewRound`, and `RoundInitialise`/`TemplateCommit`
participant actions all supply it; no transition depends on an ambient `event_seq`. Updated: pseudocode
§0.7f/§0.9/§3/§2a. Audit: `STAGE_01K_DRIVER_EVENT_ENVELOPE_AUDIT.md`. TV86.

## K5 — Register only applied transitions

`ApplyMinerStateTransition` adds the `TransitionEventID` to `applied_transition_registry` ONLY inside
its atomic apply (step 5), after replay-suppress + old-state + legality/envelope validation succeed. A
rejected (stale/illegal/malformed) transition is recorded in `transition_rejection_log` and is NEVER in
the applied registry. Updated: pseudocode §0.8/§0.9. Audit: `STAGE_01K_TRANSITION_REGISTRY_AUDIT.md`.
TV87/TV88.

## K6 — Remove undeclared invalid assignment state

`LeaseExpiry` performs no undefined `INVALIDATE`; the expiring CURRENT version is CLOSED canonically via
the single closer `EnterLowPowerListen` (`status = CLOSED`, `custody_status = expired`,
`termination_reason = lease_expiry`, a new declared Assignment field). Accepted coverage is preserved,
only the accepted unsearched suffix is reassigned (`RangeReassign`), and I18a/I18b hold at every
observable point. `SUPERSEDED` remains renewal-only. Updated: pseudocode §0.8 (`termination_reason`),
§7 (`EnterLowPowerListen` classification), §12 (`LeaseExpiry`). Audit:
`STAGE_01K_LEASE_TERMINATION_AUDIT.md`. TV89.

## K7 — Security evaluation on applicability entry

New procedure `CaptureSecurityCensusOnApplicabilityEntry` (the SECOND coherent census writer) captures
the census on entry to `HASHING` (via `CompleteAssignmentPhase`) and `SOLUTION_PROPAGATION` (via
`ScheduleSolutionPropagation`), writing `security_census_dirty` and `latest_security_census` together
(J1 coherence), so the event-time epilogue decides the floor even when no miner-state boundary occurred
(e.g. `H_active = 0` on `ASSIGNMENT → HASHING` with no successful wake). It never runs while the round is
`ASSIGNMENT`, so no breach is created in a non-applicable state (J6). Updated: pseudocode §9/§2b/§16b;
registries note. Audit: `STAGE_01K_SECURITY_APPLICABILITY_AUDIT.md`. TV90.

## K8 — Complete scheduler dispatch context

An explicit `EventQueueContext` (`event_queue`, `current_event_time`, `current_delta_cycle`,
`current_microphase`, `event_creation_seq`, `finalised_event_times`) is the single dispatch/scheduling
state. `ScheduleEvent` takes NO `target_delta_cycle`; it DERIVES `delta_cycle` from the context (future
`event_time` → 0; same `event_time` forward rule; past → rejected), so a caller supplies only
`event_time` + `microphase` and cannot bypass the forward-scheduling rule. Updated: pseudocode §0.7e;
§1 `RoundInitialise` (init/preserve). Audit: `STAGE_01K_SCHEDULER_CONTEXT_AUDIT.md`.

## Summary of changed / added artifacts

| Artifact | Change |
|----------|--------|
| `STAGE_01_PROTOCOL_PSEUDOCODE.md` | §0.2 (seq owner); §0.7e `EventQueueContext`+`ScheduleEvent` derive (K8); §0.7f `DriverEventEnvelope` (K4); §0.8 registries (`applied_transition_registry`, `transition_rejection_log`, `event_creation_seq`, K3 continuity; Assignment `termination_reason`, K6); §0.9 `ApplyMinerStateTransition` (K4/K5); §1 `RoundInitialise` (K3/K5/K8); §1a residency rebase (K3); §2a `PrepareParticipantsForNewRound` (K1); §2b `CompleteAssignmentPhase` (K2); §3 `MinerRegister` (K4); §5 `HashWorkEvent` guard (K2); §7 `EnterLowPowerListen` (K6); §9 `CaptureSecurityCensusOnApplicabilityEntry` (K7); §12 `LeaseExpiry` (K6); §16b `ScheduleSolutionPropagation` (K7) |
| `STAGE_01_INVARIANT_CATALOGUE.md` | I19 amended for cross-round continuity (K3) |
| `STAGE_01_TERMINOLOGY.md` | Stage-1K addendum (K1–K8) |
| `STAGE_01_TRACEABILITY_MATRIX.csv` | Rows R75–R82 (K1–K8) |
| `STAGE_01K_*` (14 new deliverables) | this report + next-round / assignment-phase / cross-round-residency / driver-envelope / transition-registry / lease-termination / security-applicability / scheduler-context audits + procedure call graph + semantic test vectors + supersession register + cross-document audit + checksum manifest |

No executable source, configuration, DOCX, or PDF file is modified; no Stage 1A–1J artifact is modified.
The specification conforms to K1–K8 while preserving B1–B9, C1–C10, D1–D9, E1–E10, F1–F9, G1–G11, H1–H9,
I-01…I-08, and J1–J9.
