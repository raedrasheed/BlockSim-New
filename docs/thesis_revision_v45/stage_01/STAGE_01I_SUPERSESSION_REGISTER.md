# Stage 1I — Supersession Register (execution-contract lock)

This register records, in ONE place, every Stage-1I statement that supersedes a prior-stage statement,
so that **no historical Stage-1A..1H artifact is rewritten**: the prior files remain frozen evidence,
and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1I) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1H `FinalizeTimestampSecurityCensus` keyed by `(event_time, delta_cycle)`, run as microphase 5, reading the settled census of that `(event_time, delta_cycle)`; `security_evaluation_required[(event_time, delta_cycle)]` flag | I-01: `FinalizeEventTimeSecurityCensus(event_time)` keyed by `event_time` ALONE; `security_census_dirty[event_time]` + `latest_security_census[event_time]` (newest wins); one decision per event_time. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§0.9/§9 | correction (no stranded dirty flag between delta-cycles) |
| 2 | Stage-1G/1H "PHASE 5 the SINGLE settled-census security evaluation" as a microphase event in the §0.7 microphase contract | I-02: the security decision is NOT a microphase event; it is the event-time EPILOGUE run by `ProcessEventTime` after the whole `event_time` is quiescent (so it cannot be missed when no later event exists). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7/§0.7d/§21 | correction (structural epilogue, not a queued event) |
| 3 | Stage-1F..1H `ApplyMinerStateTransition` idempotence "per `(MinerID, event_time, new_state)`" / `already_applied(MinerID, event_time, old_state -> new_state)` | I-03: idempotence keyed by immutable `TransitionEventID` (incl. `delta_cycle` and `seq`); only an exact-id replay is suppressed; a legitimate same-edge in another `delta_cycle` is applied. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§0.9 | correction (no false suppression of a legitimate repeated edge) |
| 4 | Stage-1G/1H `RoundInitialise` initialising a subset of registries; event-loop bookkeeping (`security_census_dirty`, `latest_security_census`, `transition_event_registry`, `finalised_event_times`, `current_delta_cycle`) implied but not explicitly initialised or scoped | I-04: `RoundInitialise` explicitly initialises and returns EVERY registry; per-round vs per-run scope defined; per-run bookkeeping preserved across rounds. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§1 | correction (no implicit runtime global) |
| 5 | Stage-1H `SecurityFloorEvaluate` H4 branch: legal recovery source set `{HASHING, SOLUTION_PROPAGATION, SECURITY_RECOVERY}`, with terminal handling as a branch AFTER breach recording | I-05: terminal-first (`ROUND_ACCEPTED`/`ROUND_ABORTED` → `terminal_stale_noop`) BEFORE any breach recording; recovery transition ONLY from `{HASHING, SOLUTION_PROPAGATION}`; a persistent breach in `SECURITY_RECOVERY` records `breach_persists` with NO self-transition and NO `state_version` bump. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §9 | correction (terminal-first; no SR→SR self-churn) |
| 6 | Stage-1H `AdversarialParticipationChangeEvent` `LOW_POWER_LISTEN` else-branch lumping `{RANGE_EXHAUSTED, ASSIGNMENT_REVOKED, ROUND_ACCEPTED, ROUND_ABORTED}` into one "fresh ORIGINAL + StartWake (T10)" path | I-06: split by `entry_stop_reason`; `ROUND_ACCEPTED`/`ROUND_ABORTED` create NO assignment/wake in the closed round; `RANGE_EXHAUSTED`/`ASSIGNMENT_REVOKED` create a fresh T10 assignment only in a nonterminal, non-refreshing, committed-eligible-template round; `TEMPLATE_REFRESH` defers to the new-template procedure. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §8a | correction (no activation into a closed/discarded-template round) |
| 7 | Stage-1H adversarial exit `custody_status(range(X)) <- revoked_adversarial_exit` (an undeclared custody value) | I-07: `custody_status = revoked` (canonical enum) + `revocation_reason = adversarial_withdrawal` (two-field); `revoked_adversarial_exit` is never a custody value. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§8a; `STAGE_01_INVARIANT_CATALOGUE.md` I8b; `STAGE_01_TERMINOLOGY.md` | correction (canonical closed custody enum) |
| 8 | Un-suffixed normative files referencing the invariant range as `I1..I17` (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_COMPLETION_REPORT.md`, `STAGE_01_OPEN_QUESTIONS.md`, `STAGE_01_THREAT_MODEL.md`, `STAGE_01_TERMINOLOGY.md`, `STAGE_01_FAILURE_AND_ADVERSARIAL_PATHS.md`, `STAGE_01_PROTOCOL_SCOPE.md`) | I-08: all now reference `I1..I19` (incl. `I18a`/`I18b`); genuine single-invariant `I17` references unchanged. | correction (complete, consistent invariant references) |

## Frozen-artifact discipline (A–H lock)

- No `STAGE_01[A-H]_*` file is modified in Stage 1I (verified by `git diff --name-only <base>`; see
  `STAGE_01I_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and
  test vectors — including the Stage-1H `STAGE_01H_DELTA_CYCLE_CONTRACT.md` and
  `STAGE_01H_FINAL_CENSUS_AUDIT.md` — remain byte-frozen; entries 1–8 above are the ONLY sanctioned way
  their now-superseded statements are amended.
- The delta-cycle contract (H2) is PRESERVED and EXTENDED by the I-01/I-02 epilogue, not replaced: the
  microphase ordering and delta-cycle forward-only rule still hold; the security decision is relocated
  to run AFTER all delta-cycles at an `event_time` are drained.
- Historical invariants (I2 discovery-time, I18a/I18b, I19) are NOT re-opened; Stage 1I reconciles
  cross-document references to `I1..I19` (I-08) and clarifies the I8b custody enum (I-07) without
  altering the frozen definitions.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
