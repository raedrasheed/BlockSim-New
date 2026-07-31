# Stage 1K — Supersession Register (core-handoff closure)

This register records, in ONE place, every Stage-1K statement that supersedes a prior-stage statement,
so that **no historical Stage-1A..1J artifact is rewritten**: the prior files remain frozen evidence,
and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1K) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1J `PrepareParticipantsForNewRound` `LOW_POWER_LISTEN` DEFAULT/CONTINUE for `VALID_SOLUTION_VERIFIED` (a verified finder/recipient had no next-round path) | K1: EVERY `entry_stop_reason` has an explicit disposition; `VALID_SOLUTION_VERIFIED`/`ROUND_ACCEPTED`/`ROUND_ABORTED` → archive + confirm CLOSED + fresh `ORIGINAL` under the new ids via T10; `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` → new-round policy; no fall-through. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a | correction (complete eligibility) |
| 2 | Stage-1J: `ASSIGNMENT → HASHING` (R4) as explanatory prose; no named completion step | K2: `CompleteAssignmentPhase` is a named procedure performing the executable `ASSIGNMENT → HASHING`; `PrepareParticipantsForNewRound` calls it; a `HashWorkEvent` is a no-op while `ASSIGNMENT`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2b/§2a/§5 | addition (executable phase completion) |
| 3 | Stage-1I/1J `residency_ledger` per-round with no cross-round continuity contract (an open interval could be reset at a round boundary) | K3: `FinalizeRoundResidency`/`BeginRoundResidency` rebase a continuing state at the identical `boundary_time` with no transition energy; the idle interval is counted exactly once. I19 amended. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §1a/§0.8; catalogue I19 | correction (cross-round continuity) |
| 4 | Stage-1J `ApplyMinerStateTransition` resolving `event_time/delta_cycle/event_seq` from the dispatching envelope only (driver entry points had no explicit envelope) | K4: sim-driver transitions carry an explicit `DriverEventEnvelope` (§0.7f); `MinerRegister`, `PrepareParticipantsForNewRound`, `RoundInitialise`/`TemplateCommit` participant actions all supply defined `(event_time, delta_cycle, event_seq)`; no ambient seq. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7f/§0.9/§3 | correction (complete driver envelopes) |
| 5 | Stage-1J `transition_event_registry` with the id ADDed right after the replay check (before validating old-state/legality) | K5: renamed `applied_transition_registry`; the id enters ONLY inside the atomic apply (step 5), after replay-suppress + old-state + legality/envelope validation; rejections go to `transition_rejection_log` and are never in the applied registry. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§0.9 | correction (register only applied) |
| 6 | Stage-1E..1J `LeaseExpiry` `INVALIDATE assignment` (an undefined assignment state) | K6: no `INVALIDATE`; the expiring CURRENT version is CLOSED canonically via `EnterLowPowerListen` (`status = CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry`); accepted coverage preserved, accepted unsearched suffix reassigned; I18a/I18b hold; `SUPERSEDED` renewal-only. New `termination_reason` field. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§7/§12 | correction (declared terminal state only) |
| 7 | Stage-1J `SecurityFloorEvaluate`/`ApplyMinerStateTransition`: the floor was evaluated only when a miner-state boundary set the census (entry to a floor-applicable state with no boundary — e.g. `H_active = 0` on `ASSIGNMENT → HASHING` — produced no decision) | K7: `CaptureSecurityCensusOnApplicabilityEntry` (second coherent census writer) captures on entry to `HASHING` (via `CompleteAssignmentPhase`) and `SOLUTION_PROPAGATION` (via `ScheduleSolutionPropagation`), so the epilogue decides even with no wake; never runs while `ASSIGNMENT` (J6 preserved). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §9/§2b/§16b/§0.8 | correction (applicability-entry evaluation) |
| 8 | Stage-1J `ScheduleEvent` taking an arbitrary `target_delta_cycle` input; dispatch state implicit | K8: explicit `EventQueueContext` (event_queue/current_event_time/current_delta_cycle/current_microphase/event_creation_seq/finalised_event_times); `ScheduleEvent` DERIVES `delta_cycle` (caller supplies only `event_time` + `microphase`, cannot bypass the forward rule; future time → dc 0). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7e | correction (complete dispatch context) |

## Frozen-artifact discipline (A–J lock)

- No `STAGE_01[A-J]_*` file is modified in Stage 1K (verified by `git diff --name-only <base>`; see
  `STAGE_01K_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and
  test vectors remain byte-frozen; entries 1–8 above are the ONLY sanctioned way their now-superseded
  statements are amended.
- The J1–J9 model is PRESERVED and refined: K1 completes the J5 participation path; K2 makes the J5→R4
  handoff executable; K3 extends I19 across rounds; K4 completes the J3/J4 envelope story; K5 refines the
  J2 registry ordering; K6 uses the J7 canonical status for lease expiry; K7 adds a second J1-coherent
  census writer for applicability entry; K8 completes the J9 scheduler context.
- Historical invariants (I1..I19, incl. I18a/I18b) are NOT re-opened; Stage 1K amends I19 for cross-round
  continuity (K3) and adds a `termination_reason` field (K6) without altering the frozen invariant IDs.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
