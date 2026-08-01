# Stage 1W — Transition Result Contract Audit (W6)

## 1. Scope

This audit documents correction **W6** (*align `ApplyMinerStateTransition` returns with
`StartWake`*) of the PoCol formal specification and, in particular, of the idle policy within
PoCol whose wake path is governed by `StartWake`. It certifies that, in the *current*
`STAGE_01_PROTOCOL_PSEUDOCODE.md`, the central miner-state transition hook
`ApplyMinerStateTransition` returns **exactly one** of a four-member result union, that each
member carries the `TransitionEventID`, that the withdrawn `transition_record` return name
survives only in explanatory withdrawal prose, and that `StartWake` — the sole inspecting caller
on the wake path — branches on the declared union so that a seated `WakeCompleteEvent` is retained
only on `transition_applied` and cancelled on every other result.

Every claim below is grounded in a re-grep of the current
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; the line numbers cited were obtained from that re-grep and are
reported only as navigation aids to the quoted text, not as stable identifiers. Where a Stage-1W
paper artifact expected by the traceability matrix is not yet present in the directory, this is
stated explicitly (Section 6).

All files inspected are under
`/home/user/blocksim-v45-stage1w/docs/thesis_revision_v45/stage_01/`. The A1 continuous-control
energy accounting baseline `8.420833333 kWh` (per `STAGE_01_ENERGY_MODEL_SPECIFICATION.md`) is
untouched by W6 and is preserved verbatim by this audit; W6 is a result-name contract correction
with no effect on energy accounting.

## 2. The defect corrected

Prior to W6 the `ApplyMinerStateTransition` `RETURNS` clause named a result `transition_record`,
whereas its inspecting caller `StartWake` branched on `transition_applied`. The two names never
denoted the same value: the hook advertised one success name while the wake transaction tested a
different one. The consequence is exactly the ambiguity recorded in the requirement register for
`R165` (`STAGE_01_TRACEABILITY_MATRIX.csv`, current line 166), whose failure mode is

> a StartWake that tests a result name the transition hook does not return leaving the
> wake/transition contract ambiguous

Under that mismatch a `StartWake` test of `transition_applied` could never be satisfied by a hook
that returned `transition_record`, so the disposition of a seated `WakeCompleteEvent` after a
transition step was undefined — the very orphan-wake hazard the wake transaction is designed to
foreclose.

W6 resolves the mismatch by (a) declaring a single explicit four-member result union on the hook,
each member carrying the `TransitionEventID`; (b) withdrawing the `transition_record` name; and
(c) making `StartWake` branch on the declared union. The current pseudocode records the withdrawal
explicitly in the hook's closing `NOTE` (current lines 1073–1078):

> NOTE: W6: ApplyMinerStateTransition returns EXACTLY ONE of four declared results, each carrying
> the TransitionEventID: transition_applied (the atomic step-5 apply succeeded), duplicate_suppressed
> (an exact replay of an already-applied id, step 2), illegal_stale_source (old_state != miner_state,
> step 3), illegal_transition (an illegal edge or a malformed envelope, step 4). The earlier
> `transition_record` return name is WITHDRAWN. StartWake (and any other inspecting caller) branches
> on `transition_applied` versus the three non-applied results; a for-effect caller may ignore the
> value, but no caller may test a name outside this union.

A whole-file re-grep confirms the residual scope of the withdrawn name: `transition_record`
occurs at exactly **two** locations, current lines 1069 and 1076, and both are withdrawal prose —
line 1069 ("never an undeclared `transition_record`") inside the step-6 success comment, and line
1076 ("The earlier `transition_record` return name is WITHDRAWN") inside the NOTE. It appears in
no signature, no `RETURN` statement, no `RETURNS` clause, and no caller predicate. The old-form
predicate `IF tr != transition_applied` does not occur anywhere; the only inequality-style test of
the success name is `StartWake`'s `IF tr is NOT transition_applied(teid)` (current line 1139),
which is tied to the declared union.

## 3. The four-variant result union

The hook's `RETURNS` clause (current lines 1071–1072) declares the union as a single explicit
disjunction:

```
RETURNS: transition_applied(TransitionEventID) | duplicate_suppressed(TransitionEventID) |
         illegal_stale_source(TransitionEventID) | illegal_transition(TransitionEventID)   # W6: one explicit result union
```

Each of the four members is emitted by exactly one `RETURN` site inside the procedure body, and
every site carries the `TransitionEventID` built once at step (1) (current lines 1017–1020). The
mapping is:

| Variant (carries `TransitionEventID`) | Emitting `RETURN` site | When returned |
|---|---|---|
| `duplicate_suppressed(TransitionEventID)` | Step 2, current line 1024 | The `TransitionEventID` is already in `applied_transition_registry` — an exact replay of an already-applied transition; no old-state read, no energy charge |
| `illegal_stale_source(TransitionEventID)` | Step 3, current line 1030 | `old_state != NONE AND old_state != miner_state(MinerID)` — a stale source; recorded in `transition_rejection_log` (`reason_rejected = stale_source`), never in the applied registry |
| `illegal_transition(TransitionEventID)` | Step 4, current line 1038 | The edge is not a legal miner transition, or the envelope is incomplete/malformed (e.g. `RUN_HOOK` without `hook_id`, or a candidate-triggered call missing `candidate_id`/`propagation_id`); recorded in `transition_rejection_log` (`reason_rejected = illegal_or_malformed`) |
| `transition_applied(TransitionEventID)` | Steps 5–6, current line 1070 | The step-5 `ATOMICALLY` apply completed (registry add, residency boundary, boundary energy, assignment status, `miner_state` set, census recompute + `CommitSecurityCensus`); the sole success path |

The step-3 and step-4 sites are quoted here to confirm the carried identifier and the
rejection-log discipline (current lines 1027–1030 and 1033–1038):

```
    IF old_state != NONE AND old_state != miner_state(MinerID):
      RECORD transition_rejection_log(TransitionEventID, reason_rejected = stale_source,
                                      observed_state = miner_state(MinerID))   # K5: NOT applied
      RETURN illegal_stale_source(TransitionEventID)   # W6
```

```
    IF (old_state -> new_state) is NOT a legal miner transition
       OR envelope is incomplete (missing envelope_namespace/event_time/delta_cycle/event_seq)   # K4/R3
       OR (envelope_namespace = RUN_HOOK AND hook_id = null)                     # R3: a RUN_HOOK envelope MUST carry its hook_id
       OR (candidate-triggered AND (candidate_id = null OR propagation_id = null)):   # J3
      RECORD transition_rejection_log(TransitionEventID, reason_rejected = illegal_or_malformed)
      RETURN illegal_transition(TransitionEventID)   # W6
```

The step-2 duplicate site (current lines 1023–1024) likewise carries the identifier:

```
    IF TransitionEventID in applied_transition_registry:
      RETURN duplicate_suppressed(TransitionEventID)        # W6: exact replay of an applied transition; no state check, no charge
```

The union is closed: a re-grep for `transition_applied` returns only the success `RETURN` (line
1070), the `RETURNS` clause (line 1071), the step-6 comment and NOTE prose (lines 1068, 1074,
1077), and the three caller predicates discussed in Sections 4 and 5 (lines 1139, 1656, 1687). No
fifth result name is emitted anywhere in the procedure.

## 4. `StartWake` disposition handling

`StartWake` is the wake-path caller that inspects the hook result. It captures the result into
`tr` and then branches on the union. The capture (current lines 1135–1138):

```
    SET tr <- CALL ApplyMinerStateTransition(MinerID, from_state, WAKING,
                     transition_envelope = dispatch_envelope,           # S1: ONE explicit transition-envelope object
                     reason = wake_start, assignment_ref = target_assignment,
                     candidate_id = null, propagation_id = null)         # F6
```

This call is issued at step (4) of the wake transaction, **only after** a successful
`ScheduleEvent` seat of the `WakeCompleteEvent` at step (3) (current lines 1125–1133). The
disposition then splits exactly on the declared union.

**Non-applied — cancel the seat (current lines 1139–1146):**

```
    IF tr is NOT transition_applied(teid):
      # (5) V3/W6: the transition did NOT apply (duplicate_suppressed / illegal_stale_source / illegal_transition) AFTER
      #     the seat -> CANCEL the seated WakeCompleteEvent so no orphan wake survives; leave the miner in from_state
      #     (NOT WAKING). W6: `tr` is one of the four declared ApplyMinerStateTransition results; only transition_applied
      #     retains the wake.
      IF wake_event_ref is still pending on EQ: CANCEL wake_event_ref on EQ
      RECORD wake_transition_failed(MinerID, wake_event_ref, tr)
      RETURN wake_transition_failed_after_seat(reason = tr, WakeEventRef = wake_event_ref)
```

The predicate `IF tr is NOT transition_applied(teid)` covers precisely the three non-applied
members of the union (`duplicate_suppressed`, `illegal_stale_source`, `illegal_transition`), as the
inline comment enumerates. On any of them the seated `WakeCompleteEvent` is cancelled, the miner is
left in `from_state` (never `WAKING`), and the transaction returns the structured
`wake_transition_failed_after_seat(reason = tr, WakeEventRef = wake_event_ref)` result — the failed
`tr` is threaded back as `reason`.

**Applied — retain the seat (current lines 1147–1151):**

```
    # (6) PUBLISH the WakeEventRef on the assignment's wake registry, so a later rollback/cancel (V4/V8) can find it.
    SET wake_event_ref_of(target_assignment) <- wake_event_ref
    # (7) return the structured transaction result.
    RETURN wake_seated(AssignmentID = AssignmentID(target_assignment), WakeEventRef = wake_event_ref,
                       wake_target_time = target_time, resulting_state = WAKING)
```

Only on `transition_applied` does control fall through the `IF` to publish the `WakeEventRef` and
return `wake_seated(...)`. `StartWake`'s own `RETURNS` clause (current lines 1152–1153) declares
the three-member wake union:

```
  RETURNS: wake_seated(AssignmentID, WakeEventRef, wake_target_time, resulting_state = WAKING) |
           wake_schedule_failed_before_transition(reason) | wake_transition_failed_after_seat(reason, WakeEventRef)
```

Thus `wake_seated` is returned **only** on `transition_applied`, and the seated event is cancelled
(returning `wake_transition_failed_after_seat`) on **any** other result — exactly the W6
requirement. The invariant the branch protects is stated in the procedure's NOTE (current lines
1154–1156): a transition failure after the seat cancels the seated event "so no failure leaves
miner_state = WAKING without a live WakeCompleteEvent (gate 4)."

**Caller-scope confirmation.** The wake path has one inspecting caller (`StartWake`). Two further
inspecting callers exist elsewhere — `RollbackParticipantSetup` (current lines 1653–1656) and
`RollbackTemplateRefreshSetup` (current lines 1684–1687) — each capturing `tr` and testing
`IF tr is transition_applied(teid)`, a name **inside** the union. All remaining call sites are
for-effect (a bare `CALL ApplyMinerStateTransition(...)` with no `SET tr <-`), e.g.
`WakeCompleteEvent` (current lines 1185 and 1195), `MinerRegister` (1821, 1824),
`FullRangeExhaustNoSolution`/exhaustion (2057), `EnterLowPowerListen` (2142),
`AdversarialParticipationChangeEvent` (2226, 2245), and the horizon-close low-power/offline
departures (3780, 4437, 4453, 4567, 4577); consistent with the NOTE, "a for-effect caller may
ignore the value." Re-grep confirms **no** caller tests a name outside the union.

## 5. `transition_applied` returned outside the `ATOMICALLY` block

W6's success disposition is deliberately placed **outside** the step-5 atomic apply, so that the
name is returned only after the atomic effects have committed. The atomic block opens at step (5)
(current line 1040) and its body is indented one level deeper:

```
    ATOMICALLY:
      ADD TransitionEventID to applied_transition_registry             # K5: only APPLIED transitions are registered
      ...
        CALL CommitSecurityCensus(RoundContext, event_time, ...)
    # (6) W6 EXPLICIT SUCCESS DISPOSITION. The atomic apply completed; return the declared applied result carrying the
    #     TransitionEventID. This is the ONLY path that returns transition_applied ...
    RETURN transition_applied(TransitionEventID)
```

A byte-level check of the leading whitespace confirms the placement: `ATOMICALLY:` is indented
four spaces (current line 1040); every statement of its body is indented six or more spaces (e.g.
`ADD TransitionEventID ...` at six spaces, `CALL CommitSecurityCensus(...)` at eight); and
`RETURN transition_applied(TransitionEventID)` (current line 1070) is dedented back to four
spaces, matching the `ATOMICALLY:` header rather than its body. The `RETURN` therefore lies after,
and outside, the atomic region. The step-6 comment states this directly: "The atomic apply
completed; return the declared applied result." Because the identifier enters
`applied_transition_registry` only inside the atomic block (step 5, current line 1041; reaffirmed
in the K5 NOTE at current lines 1079–1083), `transition_applied` is returned strictly after the
registry add, the residency-boundary close/open, the boundary energy record, the `miner_state`
write, the deterministic census recompute, and the `CommitSecurityCensus` publish have all
committed together. The three non-applied results, by contrast, are returned before the atomic
block is ever entered (steps 2–4), so they never register the identifier as applied.

## 6. Mapping to TV194

The Stage-1W blocking test vector `TV194` specifies the observable behaviour W6 guarantees. It is
defined in `STAGE_01_TRACEABILITY_MATRIX.csv` under requirement `R168` (current line 169):

> TV194 ApplyMinerStateTransition transition_applied retains the event and every other result cancels it

The audited pseudocode realizes TV194 on the wake path exactly: `StartWake` retains the seated
`WakeCompleteEvent` (falling through to `wake_seated`, Section 4) on `transition_applied`, and
cancels it (`CANCEL wake_event_ref on EQ`; returning `wake_transition_failed_after_seat`) on each
of the three non-applied results. The "every other result" clause of TV194 corresponds one-to-one
to the three non-applied members of the union enumerated in Section 3.

`R168` names `STAGE_01W_SEMANTIC_TEST_VECTORS` as the artifact intended to host TV194. As of this
audit, no `STAGE_01W_SEMANTIC_TEST_VECTORS.md` (nor any other `STAGE_01W_*` file besides this one)
is present in the stage directory; a re-grep finds `TV194` only in the traceability matrix. TV194
is therefore *specified* but its paper realization is not yet materialized in the directory — this
is recorded here rather than asserted as present.

## 7. Traceability

W6 is anchored consistently across the descriptive corpus; each anchor below was read in the
current file and agrees with the audited pseudocode.

- **Round state machine — §3.10a (W6).** `STAGE_01_ROUND_STATE_MACHINE.md`, section "3.10a
  Stage-1W addendum (legal-rollback & plan-transaction lock)" (current heading line 633), item
  **W6 (transition result union)** (current lines 664–668): `ApplyMinerStateTransition` returns
  exactly one of `transition_applied` | `duplicate_suppressed` | `illegal_stale_source` |
  `illegal_transition`; `StartWake` "retains the wake and returns `wake_seated` only on
  `transition_applied`, and cancels the seated event on any other result. The `transition_record`
  return name is withdrawn." This matches the hook's `RETURNS` clause and `StartWake`'s branch
  verbatim in intent.

- **Terminology — W6.** `STAGE_01_TERMINOLOGY.md`, "Transition result union (W6)" (current lines
  845–847), declares the same four-member union carrying `TransitionEventID`. No lingering
  `transition_record` glossary entry: a re-grep of the terminology file finds W6 only at this
  entry and no occurrence of `transition_record`.

- **Invariant catalogue — I16 (W6/W7).** `STAGE_01_INVARIANT_CATALOGUE.md`, invariant I16
  ("Security-floor breaches are recorded, not silently repaired", current heading line 284),
  clause **W6/W7 (declared results)** (current lines 327–331): `ApplyMinerStateTransition` "returns
  exactly one of {transition_applied, duplicate_suppressed, illegal_stale_source,
  illegal_transition} ... a wake is retained (and an `AssignmentID`/lease/transaction entry
  recorded) ONLY on the applied/created result." This is the invariant-level statement of the
  retain-on-applied / cancel-otherwise discipline audited in Sections 4–5.

- **Requirement — R165.** `STAGE_01_TRACEABILITY_MATRIX.csv` (current line 166): "Align
  ApplyMinerStateTransition returns with StartWake (W6)" — declaring the four-member union, the
  `StartWake` retain-only-on-`transition_applied` / cancel-otherwise rule, and the withdrawal of
  `transition_record`. Procedures listed: `ApplyMinerStateTransition`; `StartWake`. Invariants
  cited: `I3`; `I16`. Status: `SPECIFIED`. Its associated blocking vector TV194 sits under R168
  (Section 6).

## 8. Audit result

The current `STAGE_01_PROTOCOL_PSEUDOCODE.md` conforms to W6:

1. `ApplyMinerStateTransition` declares and emits exactly the four-member union
   `transition_applied | duplicate_suppressed | illegal_stale_source | illegal_transition`, each
   member carrying the `TransitionEventID`, one per `RETURN` site (Section 3).
2. `transition_applied` is returned on the sole success path, outside the step-5 `ATOMICALLY`
   block, strictly after the atomic apply commits (Section 5).
3. `StartWake` captures the hook result and retains the seated `WakeCompleteEvent` (returning
   `wake_seated`) only on `transition_applied`, cancelling it (returning
   `wake_transition_failed_after_seat`) on any other result (Section 4).
4. The withdrawn name `transition_record` survives only in the hook's withdrawal prose (two
   occurrences, both explanatory); no signature, `RETURN`, `RETURNS`, or caller predicate uses it,
   and no old-form `IF tr != transition_applied` predicate remains untied to the union (Sections
   2, 4).
5. No inspecting caller tests a name outside the union; for-effect callers ignore the result
   (Section 4).
6. Signature, `RETURNS`, and call sites agree, and the correction is consistently anchored in
   round-SM §3.10a (W6), terminology (W6), invariant I16 (W6/W7), and requirement R165, with the
   observable guarantee captured by TV194 (Sections 6–7).

The only outstanding item is materialization of the TV194 paper vector in
`STAGE_01W_SEMANTIC_TEST_VECTORS`, which is specified in the traceability matrix but not yet
present in the stage directory (Section 6). The A1 baseline `8.420833333 kWh` is unaffected and
preserved.
