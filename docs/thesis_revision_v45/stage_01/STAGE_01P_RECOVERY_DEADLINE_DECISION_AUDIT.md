# Stage 1P — Recovery-Deadline Decision Audit (P3)

This audit is a documentation-only record for the PhD-thesis revision of the **PoCol** consensus
specification. It describes PoCol with **the idle policy within PoCol** in effect, treated here strictly
as a mechanism; no security, liveness, or energy property is claimed. The A1 baseline of
**8.420833333 kWh** is UNCHANGED by this correction. The prohibited rebranded-algorithm-name variants are
not used anywhere in this document.

**Scope.** Stage 1P correction **P3 — the recovery deadline is a FACT, not a pre-epilogue outcome**, in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` (`RecoveryDeadlineEvent` and `CaptureSecurityCensusOnRecoveryDeadline`,
§9a; `SecurityFloorEvaluate` epilogue, §9) and `STAGE_01_ROUND_STATE_MACHINE.md` (§2.5, §3.10, R14). P3 is
a corrective edit to who SELECTS the recovery outcome; it introduces no new state, alters no threshold, and
changes no metric.

---

## 1. `RecoveryDeadlineEvent` records only the FACT and dirties the census (§9a)

At Stage 1P, `PROCEDURE RecoveryDeadlineEvent` (§9a) NO LONGER selects `UNRECOVERABLE` and NO LONGER seats a
completion. After its O3/O4 stale guard — which returns `recovery_deadline_stale_noop` unless the round is
STILL in `SECURITY_RECOVERY`, on the SAME `current_recovery_episode` and the SAME
`(RoundID, TemplateID, state_version)` epoch, with no finalised outcome — the handler does exactly two
things and then returns:

```
    SET recovery_deadline_reached[RecoveryEpisodeID] <- true
    CALL CaptureSecurityCensusOnRecoveryDeadline(RoundContext, dispatch_envelope.event_time)
    RETURN recovery_deadline_recorded(RecoveryEpisodeID)
```

The handler records the per-episode FACT `recovery_deadline_reached[RecoveryEpisodeID] <- true` (a map
initialised empty at round setup, §0.8) and dirties the census at its own timestamp. Its §9a NOTE makes the
constraint explicit: the deadline "records `recovery_deadline_reached` and dirties the census; it NEVER
selects `UNRECOVERABLE` and NEVER seats a completion." It MUST NEVER assume that remaining in
`SECURITY_RECOVERY` means the floor is still breached — a same-timestamp `WakeCompleteEvent` may already have
restored the floor. The OUTCOME is chosen later, by the event-time epilogue, from the FINAL census.

## 2. `CaptureSecurityCensusOnRecoveryDeadline` — the THIRD coherent census writer (§9a)

`PROCEDURE CaptureSecurityCensusOnRecoveryDeadline` (§9a) is the THIRD coherent writer of the paired maps
`security_census_dirty` / `latest_security_census`, alongside `ApplyMinerStateTransition` (the miner-state
boundary hook, J1) and `CaptureSecurityCensusOnApplicabilityEntry` (the applicability-entry writer, §9/K7).
Called ONLY by `RecoveryDeadlineEvent` while `round_state = SECURITY_RECOVERY`, it computes
`H_honest / H_adversarial / H_active / q_adv` from the CURRENT `ACTIVE_HASHING` roster (identically to K7)
and writes both maps TOGETHER, atomically:

```
    ATOMICALLY:                                     # J1 coherence: dirty + latest together
      SET latest_security_census[at] <- census_record(..., census_seq = recovery_deadline(episode, at), ...)
      SET security_census_dirty[at] <- true
```

This upholds the J1 coherence invariant (`security_census_dirty[t] = true => latest_security_census[t]
exists`) and guarantees the deadline timestamp `at` has a census for the epilogue to decide from EVEN IF no
miner-state boundary occurred at `at`. Because every coherent writer OVERWRITES `latest_security_census[at]`,
a later same-`at` `ApplyMinerStateTransition` — for example a `WakeCompleteEvent` that moves a reserve miner
onto `ACTIVE_HASHING` and restores the floor — overwrites the deadline capture. Latest-wins therefore
leaves `latest_security_census[at]` holding the FINAL census at `at`, which is precisely what the epilogue
reads (§9a NOTE; `P3/gate 6`).

## 3. The epilogue selects `UNRECOVERABLE` vs `RESTORED` from the FINAL census (§9)

`FinalizeEventTimeSecurityCensus(event_time)` (§9) is the SOLE caller of `SecurityFloorEvaluate` and runs
EXACTLY ONCE per event_time, AFTER that event_time is QUIESCENT — every ordinary event and every delta-cycle
at the timestamp has drained. It reads the FINAL `latest_security_census[event_time]`, clears the dirty
flag, and passes the census's own stored provenance to `SecurityFloorEvaluate`. In the applicable-state
branches, `SecurityFloorEvaluate` decides:

- `breach AND round_state = SECURITY_RECOVERY`: record `breach_persists(t)`; then
  `IF recovery_deadline_reached[current_recovery_episode]` → `CALL SeatRecoveryCompletion(..., UNRECOVERABLE, t)`;
  otherwise keep waiting (return `breach_persists`, no completion seated).
- `(NOT breach) AND round_state = SECURITY_RECOVERY` → `CALL SeatRecoveryCompletion(..., RESTORED, t)`.

The deadline FACT is consulted ONLY inside the breach branch. A restored FINAL census takes the `NOT breach`
branch and yields `RESTORED` whether or not the deadline was reached — the `RESTORED` branch never reads
`recovery_deadline_reached`. `UNRECOVERABLE` is reached only when BOTH the FINAL census still breaches AND the
deadline FACT is set. All seating flows through the SOLE seater `SeatRecoveryCompletion` (§9), which mints a
versioned `RecoveryDecisionID` (P5) and sets `recovery_completion_pending` only after a successful enqueue
(P4).

## 4. Worked same-timestamp example — deadline + `WakeCompleteEvent` restore → `RESTORED`

Round is in `SECURITY_RECOVERY` on episode `E`. At event_time `t_d`, two ordinary events are queued: the
seated `RecoveryDeadlineEvent(E)` and a `WakeCompleteEvent` that completes a reserve wake and restores the
floor. Regardless of their relative dispatch order:

1. `RecoveryDeadlineEvent(E)` passes its stale guard, sets `recovery_deadline_reached[E] <- true`, and calls
   `CaptureSecurityCensusOnRecoveryDeadline(RoundContext, t_d)`, writing `latest_security_census[t_d]` +
   `security_census_dirty[t_d] = true` from the roster visible at that moment.
2. `WakeCompleteEvent` moves the reserve miner onto `ACTIVE_HASHING`; `ApplyMinerStateTransition` (J1)
   OVERWRITES `latest_security_census[t_d]` with a census in which `H_honest(t_d)` is back above the floor.
   (If the wake is dispatched first, the deadline's own capture recomputes from the already-restored roster —
   either way the FINAL census at `t_d` is restored.)
3. Once `t_d` is QUIESCENT, `FinalizeEventTimeSecurityCensus(t_d)` runs ONCE and reads the FINAL (restored)
   census. `SecurityFloorEvaluate` takes the `(NOT breach) AND SECURITY_RECOVERY` branch and calls
   `SeatRecoveryCompletion(E, RESTORED, t_d)`.

Outcome: `RESTORED`, even though `recovery_deadline_reached[E] = true`. The same-timestamp restoration is
visible BEFORE the outcome is chosen, so the deadline never forces `UNRECOVERABLE` when the FINAL census is
restored.

## 5. BEFORE (Stage 1O) vs AFTER (Stage 1P)

| Aspect | BEFORE — Stage 1O | AFTER — Stage 1P |
| --- | --- | --- |
| Who selects the outcome | `RecoveryDeadlineEvent` seats `CompleteSecurityRecovery(UNRECOVERABLE)` directly | `SecurityFloorEvaluate` epilogue selects from the FINAL census (§9) |
| Deadline semantics | An OUTCOME (elapsing selects `UNRECOVERABLE`) | A FACT: `recovery_deadline_reached[episode] <- true` (§9a) |
| Census at deadline timestamp | not written by the deadline | written coherently by `CaptureSecurityCensusOnRecoveryDeadline` (§9a) |
| Same-`t_d` floor restoration | could be lost — deadline already committed `UNRECOVERABLE` | visible via latest-wins FINAL census → `RESTORED` (gate 6) |
| Coherent census writers | two (J1, K7) | three (J1, K7, and §9a `CaptureSecurityCensusOnRecoveryDeadline`) |
| Sole seater | not centralised at the deadline path | `SeatRecoveryCompletion` (§9), P4/P5 |

## 6. Acceptance checks

| # | Check | Result | Evidence |
| --- | --- | --- | --- |
| A1 | `RecoveryDeadlineEvent` sets `recovery_deadline_reached <- true`, calls the deadline census writer, returns `recovery_deadline_recorded`; seats nothing | PASS | `RecoveryDeadlineEvent` EFFECTS/NOTE, §9a |
| A2 | The deadline never assumes a persisting breach and never selects `UNRECOVERABLE` inline | PASS | §9a comment; `RecoveryDeadlineEvent` NOTE |
| A3 | `CaptureSecurityCensusOnRecoveryDeadline` writes `latest_security_census[at]` + `security_census_dirty[at]` atomically (J1) | PASS | `CaptureSecurityCensusOnRecoveryDeadline` EFFECTS, §9a |
| A4 | It is the THIRD coherent writer, with `ApplyMinerStateTransition` (J1) and `CaptureSecurityCensusOnApplicabilityEntry` (§9/K7) | PASS | `CaptureSecurityCensusOnRecoveryDeadline` NOTE, §9a |
| A5 | Epilogue decides from FINAL census: breach + deadline → `UNRECOVERABLE`; else keep waiting | PASS | `SecurityFloorEvaluate` `SECURITY_RECOVERY` breach branch, §9 |
| A6 | Restored FINAL census → `RESTORED` regardless of `recovery_deadline_reached` | PASS | `SecurityFloorEvaluate` `(NOT breach)` branch, §9; RSM §2.5/§3.10/R14 |
| A7 | Gate 5 — the deadline does not select an outcome before the epilogue | PASS | `RecoveryDeadlineEvent` NOTE, §9a; `SecurityFloorEvaluate`, §9 |
| A8 | Gate 6 — a same-`t_d` `WakeCompleteEvent` restoring the floor is visible before the outcome is chosen (`RESTORED`, never `UNRECOVERABLE`) | PASS | latest-wins note, §9a (`P3/gate 6`); §4 worked example |

---

*Documentation only. Algorithm name: PoCol. The idle policy within PoCol is described as a mechanism only;
no property is claimed. A1 baseline 8.420833333 kWh unchanged. The prohibited rebranded-algorithm-name
variants are not used anywhere in this document.*
