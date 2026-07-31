# Stage 1J — Security-Census Coherence Audit (J1 dirty/latest coherence + J8 census provenance)

Normative audit for corrections **J1** (single-writer, atomic dirty/latest coherence) and **J8**
(census provenance travels with the census). It establishes that `security_census_dirty[event_time]`
and `latest_security_census[event_time]` (§0.8) have **one writer** — `ApplyMinerStateTransition`
(§0.9) — that writes them **together in one atomic step** (§0.9 step (8)); that the epilogue
`FinalizeEventTimeSecurityCensus` (§9) may ASSERT `dirty[t] ⇒ latest[t] exists` before reading; that a
candidate failure sets **no** dirty flag (§16d-bis step (3)); and that a census carries its FULL
PROVENANCE so a stale-context census records `stale_census_observation` and triggers no recovery in a
new round/template (§9 `SecurityFloorEvaluate` J8 guard). It EXTENDS the Stage-1I event-time epilogue
spec `STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md` (unchanged here) and the Stage-1H delta-cycle contract; it
describes **PoCol** with **the idle policy within PoCol** enabled and claims **no property** beyond the
coherence structure defined here. No new consensus feature is introduced.

The accepted A1 baseline is `8.420833333 kWh` and is UNCHANGED; no numeric result is asserted here.

## 1. The corrected-away problem (J1)

Two independent map entries at one timestamp `t` — a `bool` dirty flag and a `census_record` — can drift
apart if any procedure writes one without the other:

| # | Failure mode | Cause it would admit |
|---|--------------|----------------------|
| **A** | **False dirty census** | A procedure sets `security_census_dirty[t] <- true` although no boundary changed the `ACTIVE_HASHING` census. The epilogue then reads a stale or absent `latest_security_census[t]` and evaluates the floor against a census that never happened. |
| **B** | **Dirty without latest** | The dirty flag is set but `latest_security_census[t]` is never written (or written by a different writer at a different moment), so the epilogue's `ASSERT latest[t] EXISTS` (§9) has no ground and the read is undefined. |

Under an earlier draft, `HandlePropagationFailure` carried a defensive `SET security_census_dirty[now]
<- true`. A candidate failure changes **no** `ACTIVE_HASHING` census — it only schedules candidate-scoped
resume events — so that flag was exactly a **false dirty census** (mode A). J1 removes it.

## 2. The correction (J1): sole writer, atomic together

`ApplyMinerStateTransition` (§0.9, `EFFECTS` header) is declared "the SOLE writer of
`security_census_dirty[event_time]` and `latest_security_census[event_time]`". On a boundary that changed
the census it executes step **(8)** — "J1/I-01 EVENT-TIME SECURITY BOOKKEEPING" — inside an `ATOMICALLY`
block that writes the census record FIRST and the dirty flag SECOND, so neither is ever set without the
other:

```
    # (8) J1/I-01 EVENT-TIME SECURITY BOOKKEEPING — the dirty flag and the latest census are written
    #     TOGETHER in ONE atomic step; neither is ever set without the other (coherence invariant, J1).
    IF this transition changed the ACTIVE_HASHING census:
      ATOMICALLY:
        SET latest_security_census[event_time] <- census_record(
              RoundID_at_census      = RoundID_current,        # J8 provenance
              TemplateID_at_census   = TemplateID_committed,
              state_version_at_census= state_version_current,
              census_seq             = TransitionEventID,       # J8: producing-transition identity
              H_active   = H_active(event_time),  H_honest = H_honest(event_time),
              H_adversarial = H_adversarial(event_time),  q_adv = q_adv(event_time))   # newest wins
        SET security_census_dirty[event_time] <- true          # J1: set only WITH a coherent latest census
```

The §0.8 declaration binds the same rule at the registry: `security_census_dirty` is "Set true ONLY by
`ApplyMinerStateTransition` (J1), and ONLY together with `latest_security_census[event_time]`", "Cleared
ONLY by `FinalizeEventTimeSecurityCensus(event_time)`". The §0.8 `J1 COHERENCE` comment states the
INVARIANT verbatim: `security_census_dirty[t] = true  =>  latest_security_census[t] exists`.

## 3. The correction (J8): full provenance travels with the census

`latest_security_census[event_time]` is a `census_record` (§0.8) carrying its FULL PROVENANCE:
`RoundID_at_census`, `TemplateID_at_census`, `state_version_at_census`, `census_seq` (= the producing
`TransitionEventID`), plus `H_active`, `H_honest`, `H_adversarial`, `q_adv`. The epilogue (§9) passes the
**stored** provenance — not the current epoch — to `SecurityFloorEvaluate`, whose J8 stale-context guard
records an observation and returns without evaluating thresholds if the census's own epoch is no longer
current (§4).

## 4. Mechanism — the atomic write and the ASSERT

`FinalizeEventTimeSecurityCensus` (§9) checks the dirty flag, ASSERTs coherence, reads the census, clears
the flag, and passes the census's OWN provenance downstream:

```
    IF NOT security_census_dirty[event_time]:
      RETURN no_census_change
    ASSERT latest_security_census[event_time] EXISTS           # J1: dirty[t] = true  =>  latest[t] exists
    SET census <- latest_security_census[event_time]           # includes J8 provenance
    CLEAR security_census_dirty[event_time]
    RETURN CALL SecurityFloorEvaluate(RoundContext,
                 event_RoundID       = census.RoundID_at_census,
                 event_TemplateID    = census.TemplateID_at_census,
                 event_state_version = census.state_version_at_census,
                 (census.H_active, census.H_honest, census.q_adv), floor_state)
```

`SecurityFloorEvaluate` (§9) J8 stale-context guard — after the I-05 terminal-first return, before any
threshold evaluation:

```
    IF event_RoundID != RoundID_current
       OR event_TemplateID != TemplateID_committed
       OR event_state_version != state_version_current:
      RECORD security_census_observation(stale_census, event_RoundID, event_TemplateID, event_state_version,
                                         H_active(t), H_honest(t), q_adv(t))     # J8: observation only
      RETURN stale_census_observation                          # no recovery in the new context
```

`HandlePropagationFailure` (§16d-bis) step **(3)** documents the removal of the defensive flag:

```
    # (3) J1: candidate failure does NOT itself change the ACTIVE_HASHING census, so it MUST NOT set
    #     security_census_dirty (the earlier defensive `SET security_census_dirty[now] <- true` is REMOVED).
```

## 5. Writer/reader coherence table

| Writer / reader | Field | When written / read | Coherence guarantee |
|-----------------|-------|---------------------|---------------------|
| `ApplyMinerStateTransition` §0.9 (8) | `latest_security_census[t]` | On every census-changing boundary, FIRST in the `ATOMICALLY` block (newest wins) | Overwrite carries `census_record` provenance (J8); sole writer |
| `ApplyMinerStateTransition` §0.9 (8) | `security_census_dirty[t]` | SAME atomic step, SECOND | Set only WITH a coherent latest census; never alone (J1) |
| `FinalizeEventTimeSecurityCensus` §9 | `security_census_dirty[t]` | Read then CLEARED at the epilogue | Sole clearer; `dirty[t] ⇒ latest[t] exists` ASSERTed first |
| `FinalizeEventTimeSecurityCensus` §9 | `latest_security_census[t]` | Read at the epilogue after the ASSERT | Passes STORED provenance, not the current epoch |
| `SecurityFloorEvaluate` §9 | `event_RoundID/TemplateID/state_version` | Compared to current epoch | Stale census ⇒ observation only, no recovery (J8) |
| `HandlePropagationFailure` §16d-bis (3) | (none) | Candidate failure | Writes NO dirty flag; cannot create a false dirty census (J1) |

## 6. Worked examples

**(TV71) Candidate failure, no paused miner → no dirty, epilogue returns `no_census_change` without
reading latest.** `HandlePropagationFailure(CandidateID, PropagationID, failure_reason)` marks the
candidate `FAILED`, removes it from `active_propagation_set`, cancels its own events, and finds no paused
miner to resume. Per §16d-bis step (3) it sets NO `security_census_dirty` flag. At the epilogue,
`security_census_dirty[event_time]` is false, so `FinalizeEventTimeSecurityCensus` returns
`no_census_change` (§9) WITHOUT reading `latest_security_census`. The J1 invariant is trivially
preserved: no dirty, so nothing to assert.

**(TV72) Positive-latency resume → dirty set only at the wake boundary.** A candidate fails; miners it
paused have positive `wake_latency`. `HandlePropagationFailure` SCHEDULEs candidate-scoped
`ResumeFromPause` events (both ids) and sets NO dirty flag (§16d-bis step (3)). Each resume later runs
`StartWake`, and at `now + wake_latency` a `WakeCompleteEvent` performs `WAKING -> ACTIVE_HASHING`
through `ApplyMinerStateTransition` — the SOLE writer. THAT boundary, at `wake_time`, sets
`security_census_dirty[wake_time]` AND writes `latest_security_census[wake_time]` together (§0.9 step
(8)); the epilogue at `wake_time` decides once. The failure `event_time` carries no dirty census; the
security update lands only at the re-activation `event_time`, coherently.

**(TV80) Stale-context census → `stale_census_observation`, no recovery in the new template.** A
census-changing boundary at `t` writes `latest_security_census[t]` under `(RoundID_A, TemplateID_A,
state_version_A)` (§0.9 step (8), J8 provenance). Before the epilogue for `t` runs, a same-time template
change commits `TemplateID_B`. `FinalizeEventTimeSecurityCensus` passes the STORED provenance
`(RoundID_A, TemplateID_A, state_version_A)` — not the current epoch — to `SecurityFloorEvaluate` (§9).
The J8 stale-context guard sees `event_TemplateID = TemplateID_A != TemplateID_committed = TemplateID_B`,
`RECORD security_census_observation(stale_census, …)`, and returns `stale_census_observation`. It does
NOT evaluate thresholds against `TemplateID_B` and does NOT trigger recovery in the new round/template.

## 7. Acceptance-style PASS checklist

| # | Check | Ground |
|---|-------|--------|
| 1 | `security_census_dirty[t] = true ⇒ latest_security_census[t] exists`; epilogue ASSERTs it before reading | §0.8 J1 comment, §9 `ASSERT latest_security_census[event_time] EXISTS` |
| 2 | `ApplyMinerStateTransition` is the SOLE writer of both `security_census_dirty` and `latest_security_census` | §0.8, §0.9 `EFFECTS` header + step (8) |
| 3 | Both written TOGETHER in one `ATOMICALLY` step; neither ever set without the other | §0.9 step (8) |
| 4 | Candidate failure sets NO `security_census_dirty` flag (defensive flag REMOVED) | §16d-bis step (3) |
| 5 | `latest_security_census[t]` is a `census_record` storing full provenance (`RoundID_at_census`, `TemplateID_at_census`, `state_version_at_census`, `census_seq`, `H_active`, `H_honest`, `H_adversarial`, `q_adv`) | §0.8, §0.9 step (8) |
| 6 | Epilogue passes the STORED provenance (not the current epoch) to `SecurityFloorEvaluate` | §9 `FinalizeEventTimeSecurityCensus` |
| 7 | Stale-context census records `security_census_observation(stale_census, …)` and returns `stale_census_observation` — no threshold evaluation, no recovery in the new round/template | §9 `SecurityFloorEvaluate` J8 guard |
| 8 | `no_census_change` returned WITHOUT reading `latest_security_census` when the flag is clear | §9, TV71 |
| 9 | Name EXACTLY **PoCol**; mechanism only **the idle policy within PoCol**; "PoCol-E"/"Energy-Aware PoCol"/"Enhanced PoCol" PROHIBITED; A1 baseline `8.420833333 kWh` unchanged; no property claimed | this audit |

## 8. Naming and property discipline

The algorithm name is EXACTLY **PoCol**; the energy mechanism is described ONLY as **the idle policy
within PoCol**. The strings "PoCol-E", "Energy-Aware PoCol", and "Enhanced PoCol" are PROHIBITED and are
not used to denote this algorithm anywhere in the specification. This audit claims no energy, security,
fairness, or incentive property; it fixes only that the dirty flag and the latest census are coherent
(one writer, one atomic step) and that a census's provenance travels with it.

---

**Result: SECURITY-CENSUS COHERENCE AUDIT (Stage 1J): PASS** — `ApplyMinerStateTransition` (§0.9) is the
SOLE writer of `security_census_dirty[event_time]` and `latest_security_census[event_time]` and writes
them TOGETHER in one `ATOMICALLY` step (step (8)), so the J1 invariant `dirty[t] ⇒ latest[t] exists`
holds and `FinalizeEventTimeSecurityCensus` (§9) may ASSERT it before reading; the defensive
`SET security_census_dirty[now] <- true` in `HandlePropagationFailure` is REMOVED (§16d-bis step (3)),
so a candidate failure creates no false dirty census; and each `latest_security_census[event_time]`
is a `census_record` carrying its full provenance (`RoundID_at_census`, `TemplateID_at_census`,
`state_version_at_census`, `census_seq`, `H_active`, `H_honest`, `H_adversarial`, `q_adv`), which the
epilogue passes to `SecurityFloorEvaluate` so a stale-context census records `stale_census_observation`
and triggers no recovery in a new round/template (J8). Extends
`STAGE_01I_EVENT_TIME_EPILOGUE_SPEC.md`; no property is claimed; the A1 baseline `8.420833333 kWh` is
unchanged.
