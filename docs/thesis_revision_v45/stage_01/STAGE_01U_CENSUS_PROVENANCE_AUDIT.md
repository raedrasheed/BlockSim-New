# STAGE 01U — Continuation-Due Census Provenance Audit (U7)

## Intro

This audit records ONE Stage-1U correction (U7) to the PoCol protocol pseudocode in
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. U7 is a census-PROVENANCE correction to the event-time
security-census machinery: it gives the branch-C continuation checkpoint its OWN named
`census_source`, `RECOVERY_CONTINUATION_DUE`, so that "assignment continuation is due" is no longer
recorded under the completion-due provenance `RECOVERY_COMPLETION_DUE`. It adds no consensus feature.

U7 changes only WHICH `census_source` label the continuation-due checkpoint stamps onto the census it
refreshes — not how any census is computed, and not how time or energy is counted. The A1 accepted
baseline of **8.420833333 kWh is UNCHANGED**: `CaptureSecurityCensusOnRecoveryDeadline` (§9a) still
sums the same `ACTIVE_HASHING` roster and still publishes `H_active = H_honest + H_adversarial` (I17);
only the provenance stamp differs. No new features are introduced; the mechanism under discussion is
the idle policy within PoCol, and this document is a provenance-ownership audit within the existing
PoCol specification. No property is claimed here.

## U7 — a distinct continuation-due census source

Before U7 the branch-C continuation checkpoint and the completion checkpoint shared the completion-due
label, so a finalised census taken at a continuation-due timestamp named `RECOVERY_COMPLETION_DUE`
even though no completion was due there. U7 introduces `RECOVERY_CONTINUATION_DUE` as a distinct
member of the `census_source` domain and rewires the continuation-due producer to it.

`RecoveryAssignmentContinuationDueEvent` (T1 step 1, §10a) now refreshes its census through the
DISTINCT source. Its body records the continuation-due fact and calls the recovery-timeline capture
procedure with the new label:

```
CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time,
                                             census_source = RECOVERY_CONTINUATION_DUE)   # U7: distinct provenance
```

The inline note states the intent verbatim: the refresh uses "the DISTINCT source
`RECOVERY_CONTINUATION_DUE` (U7 — 'continuation is due' is not conflated with 'completion is due')".
The event still performs NO round-state transition, creates NO assignment, and does NOT mark the
decision `APPLIED` — the branch-C rebuild remains the POST-epilogue hook
`ApplyRecoveryAssignmentContinuationAfterEpilogue`. U7 touches ONLY the census_source stamp.

## The sole atomic writer, now seven named sources

`CommitSecurityCensus` (§0.8a) remains the SOLE atomic writer of the two census maps
`latest_security_census[event_time]` and `security_census_dirty[event_time]` — its header still reads
"the SOLE atomic writer of the two census maps", and its atomic body writes both together (the J1
coherence invariant `dirty[t] = true => latest[t] exists` is therefore STRUCTURAL). The writer's body
is provenance-agnostic: it stamps `census_source = census_source` — whatever label its caller supplies
— so enlarging the source domain requires NO change to the writer's atomic body, only a new caller
passing a new label. U7 needs exactly that.

Per the §0.8 census-source coherence note, the `census_source` domain (`CENSUS_SOURCE`) written through
this one writer now names SEVEN sources, "written by EXACTLY ONE procedure, `CommitSecurityCensus`
(§0.8a), with SEVEN named sources (census_source, R5/U7)". Each source has EXACTLY ONE producer:

| # | `census_source` | Sole producer | Reaches the writer via | § | Provenance meaning |
|:-:|-----------------|---------------|------------------------|---|--------------------|
| 1 | `MINER_STATE_TRANSITION` | `ApplyMinerStateTransition` | direct `CALL CommitSecurityCensus` | §0.9 | a miner `ACTIVE_HASHING` boundary changed the census |
| 2 | `APPLICABILITY_ENTRY` | `CaptureSecurityCensusOnApplicabilityEntry` | direct `CALL CommitSecurityCensus` | §9 | entry into a floor-applicable state |
| 3 | `RECOVERY_DEADLINE` | `RecoveryDeadlineEvent` | `CaptureSecurityCensusOnRecoveryDeadline` | §9a | the recovery deadline is reached |
| 4 | `RECOVERY_COMPLETION_DUE` | `RecoveryCompletionDueEvent` | `CaptureSecurityCensusOnRecoveryDeadline` | §10a | recovery completion is due |
| 5 | `RECOVERY_CONTINUATION_DUE` (U7) | `RecoveryAssignmentContinuationDueEvent` | `CaptureSecurityCensusOnRecoveryDeadline` | §10a | assignment continuation is due |
| 6 | `RECOVERY_WORK_DUE` (U1) | `RecoveryWorkDueEvent` | `CaptureSecurityCensusOnRecoveryDeadline` | §9c | recovery work is due |
| 7 | `POST_RECOVERY_APPLICATION` | `FinalizePostRecoveryApplicationState` | direct `CALL CommitSecurityCensus` | §10a | the single post-application settlement |

Every producer COMPUTES a census and CALLS `CommitSecurityCensus`; NO producer writes the two maps
directly (R5). Sources 3–6 are the four recovery-timeline checkpoints that share the one capture
procedure `CaptureSecurityCensusOnRecoveryDeadline` but pass FOUR distinct labels; sources 1, 2 and 7
call the writer directly. The one-writer / seven-source shape is what keeps the census coherent while
making each checkpoint's provenance self-describing.

## Distinguishable recovery-timeline provenances

Because sources 3–6 are distinct labels carried by the SAME capture procedure, the four
recovery-timeline facts stay separable in `latest_security_census[t].census_source`:

- **recovery completion is due** — `RECOVERY_COMPLETION_DUE`, stamped by `RecoveryCompletionDueEvent`
  (line: `census_source = RECOVERY_COMPLETION_DUE   # R5: completion-due provenance`);
- **assignment continuation is due** — `RECOVERY_CONTINUATION_DUE`, stamped by
  `RecoveryAssignmentContinuationDueEvent` (`census_source = RECOVERY_CONTINUATION_DUE   # U7: distinct
  provenance`);
- **recovery work is due** — `RECOVERY_WORK_DUE`, stamped by `RecoveryWorkDueEvent`
  (`census_source = RECOVERY_WORK_DUE   # U1/R5`);
- **the recovery deadline is reached** — `RECOVERY_DEADLINE`, stamped by `RecoveryDeadlineEvent`
  (`census_source = RECOVERY_DEADLINE   # R5: deadline-fact provenance`).

The capture procedure's own NOTE confirms the outcome verbatim: it carries "`census_source`
`RECOVERY_DEADLINE`, `RECOVERY_COMPLETION_DUE`, `RECOVERY_CONTINUATION_DUE` (U7), or
`RECOVERY_WORK_DUE` (U1), so the FOUR recovery-timeline checkpoints have DISTINCT census provenance."
None of these labels selects an outcome; each only names which checkpoint refreshed the census the
event-time epilogue later decides from, and a same-timestamp `MINER_STATE_TRANSITION` commit still
overwrites the census so the epilogue reads the FINAL value.

## Confirmation: CommitSecurityCensus and CaptureSecurityCensusOnRecoveryDeadline updated (TV173)

Both procedures are confirmed consistent with U7:

- `CaptureSecurityCensusOnRecoveryDeadline` (§9a) declares its `census_source` parameter over the FOUR
  recovery-timeline labels — "`RECOVERY_DEADLINE` (`RecoveryDeadlineEvent`, §9a), `RECOVERY_COMPLETION_DUE`
  (`RecoveryCompletionDueEvent`, §10a), `RECOVERY_CONTINUATION_DUE` (`RecoveryAssignmentContinuationDueEvent`,
  §10a, U7), or `RECOVERY_WORK_DUE` (`RecoveryWorkDueEvent`, §9c, U1)" — and forwards the caller's label
  unchanged to the sole writer (`census_source = census_source`). It accepts and passes
  `RECOVERY_CONTINUATION_DUE`.
- `CommitSecurityCensus` (§0.8a) remains the sole atomic writer through which that label flows; its
  atomic body is unchanged (it stamps whatever `census_source` the caller passes), and per §0.8 the
  domain it is called with now names seven values.

**TV173** — `RecoveryCompletionDueEvent` and `RecoveryAssignmentContinuationDueEvent` write DISTINCT
`census_source` values — holds: the former passes `RECOVERY_COMPLETION_DUE`, the latter passes
`RECOVERY_CONTINUATION_DUE`. The two labels are different members of `CENSUS_SOURCE`, so a census
finalised at a continuation-due timestamp is never labelled with the completion-due provenance, and
vice versa.

## Failure mode contrasted

The defect U7 removes is a PROVENANCE conflation, not a counting error. Under the pre-U7 wiring
`RecoveryAssignmentContinuationDueEvent` would refresh the census with `RECOVERY_COMPLETION_DUE`. The
committed `latest_security_census[t].census_source` at a continuation-due checkpoint would then read
`RECOVERY_COMPLETION_DUE` — asserting "recovery completion is due" at a timestamp where only an
assignment continuation was due. Provenance-based reasoning over the finalised census (and TV173) could
not tell the two recovery-timeline checkpoints apart: the completion-due and continuation-due facts
would be indistinguishable in the stored source field, even though they arise from different
producers on different recovery timelines. The census H_* values would be identical either way — this
was never a mis-count of time or energy — but the RECORD of which checkpoint produced the census would
be wrong. With the distinct `RECOVERY_CONTINUATION_DUE` label the finalised census names its true
checkpoint, and the four recovery-timeline provenances remain separable.

## Result

After U7 the branch-C continuation checkpoint has its OWN `census_source`, `RECOVERY_CONTINUATION_DUE`,
distinct from the completion-due `RECOVERY_COMPLETION_DUE`; `RecoveryAssignmentContinuationDueEvent`
(§10a) now refreshes its census under this label instead of the completion-due one.
`CommitSecurityCensus` (§0.8a) remains the SOLE atomic writer of the two census maps, its
provenance-agnostic atomic body unchanged, and per §0.8 the `census_source` domain now names SEVEN
sources — `MINER_STATE_TRANSITION`, `APPLICABILITY_ENTRY`, `RECOVERY_DEADLINE`,
`RECOVERY_COMPLETION_DUE`, `RECOVERY_CONTINUATION_DUE` (U7), `RECOVERY_WORK_DUE` (U1),
`POST_RECOVERY_APPLICATION` — each with exactly one producer, as the PASS-check table records.
`CaptureSecurityCensusOnRecoveryDeadline` (§9a) accepts and forwards the new label unchanged, and
TV173 confirms the completion-due and continuation-due producers write DISTINCT `census_source`
values. No accounting of time or energy changed: the A1 accepted baseline of 8.420833333 kWh is
UNCHANGED, and no consensus feature was added. U7 is a census-provenance correction documented here
only.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
