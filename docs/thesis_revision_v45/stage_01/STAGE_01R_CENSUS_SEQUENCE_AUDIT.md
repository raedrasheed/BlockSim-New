# STAGE 01R — Security-Census Write-Sequence and Source Audit (R5)

## Intro

This audit records ONE Stage-1R correction (R5) to the PoCol protocol pseudocode in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. R5 makes the per-event-time census-write ordinal EXPLICIT and
names all census sources. It adds `security_census_write_seq_by_event_time` to `RunContext`, makes
`CommitSecurityCensus` (§0.8a) its SOLE owner, extends `CENSUS_SOURCE` to FIVE values, and removes
every residual statement that called `ApplyMinerStateTransition` or a capture procedure a "direct
writer" of the two census maps. Those procedures are PRODUCERS; only `CommitSecurityCensus` writes
`latest_security_census` and `security_census_dirty`.

R5 is a PROVENANCE and ORDERING correction only. It never changes how time or energy is counted:
the A1 accepted baseline of **8.420833333 kWh is UNCHANGED**. No new consensus features are
introduced — this is documentation of an ordering/provenance discipline within the existing PoCol
specification, and the mechanism under discussion is the idle policy within PoCol.

## One writer, one ordinal owner

`CommitSecurityCensus` (§0.8a) is the SINGLE canonical atomic writer of the two maps and the SOLE
owner of the census-write ordinal. Inside its atomic body it advances the explicit per-event_time
counter held in `RunContext` and stamps that value as `census_seq` on the record it writes:

```
SET RunContext.security_census_write_seq_by_event_time[event_time] <-
      (RunContext.security_census_write_seq_by_event_time[event_time] OR 0) + 1
SET latest_security_census[event_time] <- census_record(
      ...,
      census_source = census_source,
      census_seq    = RunContext.security_census_write_seq_by_event_time[event_time],   # R5: explicit deterministic ordinal
      ...)
SET security_census_dirty[event_time] <- true
```

This REPLACES the earlier implicit "next per-event-time census-write ordinal": the write order is
now a declared deterministic increment with a named owner, not an ambient side effect.

The counter is a per-run field. `RunInitialise` (§1.0, the one-time owner of every per-run field)
initialises it once at run start:

```
INITIALISE security_census_write_seq_by_event_time <- empty map   # R5
```

Because the map is keyed by `event_time` (which embeds the monotonic run-level ordinal) it is
PRESERVED across round boundaries; `RoundInitialise` never re-creates it. The declaration in the
`RunContext` structure states this explicitly: the map is the EXPLICIT deterministic write order for
`latest_security_census`, owned SOLELY by `CommitSecurityCensus`, initialised in `RunInitialise` and
preserved across rounds.

## The FIVE census sources

`CENSUS_SOURCE` is extended from the earlier framing to exactly FIVE values. Each value has a single
named PRODUCER procedure that computes a coherent census and then CALLS `CommitSecurityCensus`; none
of them writes the maps:

| `census_source`            | Producer procedure                          | Section                          |
|----------------------------|---------------------------------------------|----------------------------------|
| `MINER_STATE_TRANSITION`   | `ApplyMinerStateTransition`                 | §0.9                             |
| `APPLICABILITY_ENTRY`      | `CaptureSecurityCensusOnApplicabilityEntry` | §9                               |
| `RECOVERY_DEADLINE`        | `CaptureSecurityCensusOnRecoveryDeadline` (via `RecoveryDeadlineEvent`)      | §9 (producer) / §9a (caller)   |
| `RECOVERY_COMPLETION_DUE`  | `CaptureSecurityCensusOnRecoveryDeadline` (via `RecoveryCompletionDueEvent`) | §9 (producer) / §10a (caller)  |
| `POST_RECOVERY_APPLICATION`| `FinalizePostRecoveryApplicationState`      | §10a                             |

Notes on the two recovery-timeline rows:

- `CaptureSecurityCensusOnRecoveryDeadline` (§9) is now PARAMETERISED by `census_source`. Called
  from `RecoveryDeadlineEvent` (§9a) it carries `RECOVERY_DEADLINE`; called from
  `RecoveryCompletionDueEvent` (§10a) it carries `RECOVERY_COMPLETION_DUE`. R5 fixes the completion-
  due checkpoint to use `RECOVERY_COMPLETION_DUE` — NOT `RECOVERY_DEADLINE` — so the two recovery-
  timeline checkpoints have DISTINCT census provenance.
- `FinalizePostRecoveryApplicationState` (§10a), when it writes an observation, calls
  `CommitSecurityCensus` with `census_source = POST_RECOVERY_APPLICATION`, stamping the settlement's
  own provenance over the same `H_*` values (no re-count of time or energy).

## Producers are not writers

Every producer CALLS the sole writer and no longer writes the maps directly:

- `ApplyMinerStateTransition` (§0.9) is the SOLE owner of every miner-state change and a PRODUCER of
  the census: step (5f) computes the post-transition census and CALLS `CommitSecurityCensus` with
  `census_source = MINER_STATE_TRANSITION`. It is NOT a direct writer of `security_census_dirty` /
  `latest_security_census`. The leftover statement that framed it as "a writer … the other writer is
  `CaptureSecurityCensusOnApplicabilityEntry`" is WITHDRAWN.
- `CaptureSecurityCensusOnApplicabilityEntry` (§9) computes the census on entry to a floor-applicable
  state and CALLS `CommitSecurityCensus` with `APPLICABILITY_ENTRY`.
- `CaptureSecurityCensusOnRecoveryDeadline` (§9) computes the census at a recovery-timeline checkpoint
  and CALLS `CommitSecurityCensus` with the caller's `census_source`.
- `FinalizePostRecoveryApplicationState` (§10a) archives the post-application census and CALLS
  `CommitSecurityCensus` with `POST_RECOVERY_APPLICATION`.

The earlier "exactly two writers" / "third writer" / "the other writer" framing is superseded by
"ONE writer, FIVE sources". No producer is a direct writer of the two maps.

## Structural coherence retained

The coherence invariant is unchanged and remains STRUCTURAL: `security_census_dirty[t] = true ⇒
latest_security_census[t] exists`. This holds automatically because the two writes are the atomic
body of the SOLE writer `CommitSecurityCensus`; it is not a per-caller discipline. The flag is
cleared only by `FinalizeEventTimeSecurityCensus(event_time)` (the epilogue).

## Result

After R5 the census maps have exactly one writer (`CommitSecurityCensus`, §0.8a), one explicitly
owned per-event_time write ordinal (`RunContext.security_census_write_seq_by_event_time`, initialised
in `RunInitialise` §1.0 and preserved across rounds), and five named sources whose producers CALL —
never bypass — that writer. Each committed record carries both its `census_source` and its
deterministic `census_seq`, giving every event-time census unambiguous provenance and write order.
No accounting of time or energy changed: the A1 accepted baseline of 8.420833333 kWh is UNCHANGED,
and no consensus feature was added. R5 is documentation of ordering and provenance only.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
