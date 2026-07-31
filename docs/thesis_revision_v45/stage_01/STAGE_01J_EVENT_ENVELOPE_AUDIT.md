# Stage 1J — Event Envelope Audit (J3 / J4 / J9)

A structural audit of the Stage-1J corrections **J3** (complete transition envelope), **J4**
(event-sequence ownership), and **J9** (central scheduler contract) in the **PoCol** protocol
pseudocode (`STAGE_01_PROTOCOL_PSEUDOCODE.md`): every scheduled event carries the immutable §0.2
envelope; the single per-run `event_creation_seq` counter is owned solely by `ScheduleEvent`
(§0.7e); and `ApplyMinerStateTransition` (§0.9) receives the FULL envelope with explicit
`candidate_id` AND `propagation_id`, so its `TransitionEventID` distinguishes two propagation
attempts of one `CandidateID`. This document is documentation only; it audits wording and control
structure, describes only the idle policy within PoCol, introduces no new consensus feature, and
claims **no** security, fairness, energy, or incentive property. The A1 baseline (`8.420833333 kWh`)
is unchanged.

---

## 1. The corrected-away ambiguities

- **J3.** A single ambiguous `candidate_ref` could not distinguish two propagation attempts of one
  `CandidateID`. Stage-1J REPLACES it with two explicit resolved fields, `candidate_id` AND
  `propagation_id`, threaded into `ApplyMinerStateTransition` and into `TransitionEventID` (§0.9).
- **J4.** There was no single declared owner for the event-creation counter — an *ambient undeclared
  seq* could differ across reruns. Stage-1J declares ONE per-run monotonic `event_creation_seq`
  (§0.8), initialised once and owned solely by the scheduler.
- **J9.** Nothing forbade an ad-hoc enqueue skipping the finalised-time and ordering rules. Stage-1J
  routes every `SCHEDULE` through the SOLE interface `ScheduleEvent` (§0.7e), requirement R74.

## 2. Mechanism

### 2.1 The immutable event envelope (§0.2)

Every scheduled event carries the immutable envelope
`{ event_type, event_time, delta_cycle, microphase, RoundID, TemplateID, CandidateID?,
PropagationID?, MinerID?, AssignmentID?, assignment_version?, seq }`. `CandidateID` and
`PropagationID` are REQUIRED on every certificate-arrival, block-arrival, validation, timeout,
cancellation, and resume event; *"a propagation context is NEVER identified by `RoundID` alone."*
Events are ordered by the total key `(event_time, delta_cycle, microphase, stable_tie_key, seq)`,
`stable_tie_key = (CandidateID, MinerID, AssignmentID)`, and `seq` is the value of the single per-run
monotonic `event_creation_seq` (J4), assigned by `ScheduleEvent` (§0.7e/J9) AFTER the deterministic
ordering is established, used ONLY as the final tie-break. *"There is no ambient undeclared seq:
every envelope's `seq` comes from `ScheduleEvent`."*

### 2.2 The complete transition envelope and `TransitionEventID` (J3)

`ApplyMinerStateTransition` (§0.9) receives the full envelope:
`MinerID, old_state, new_state, event_time, delta_cycle, event_seq, reason, assignment_ref,
candidate_id, propagation_id`. `event_time`/`delta_cycle`/`event_seq` are RESOLVED from the
dispatching event's envelope (`event_seq = its event_creation_seq`, assigned by `ScheduleEvent`, J9);
`assignment_ref` RESOLVES `AssignmentID`/`assignment_version`; `candidate_id` and `propagation_id`
are BOTH passed by every candidate-triggered caller (null for non-candidate transitions). Step (0)
builds the immutable id from the full envelope, including BOTH candidate ids:

    TransitionEventID <- (event_time, delta_cycle, event_seq, MinerID, old_state, new_state, reason,
                          AssignmentID(assignment_ref), assignment_version(assignment_ref),
                          candidate_id, propagation_id)                       # immutable (J3)

Because the id embeds `(candidate_id, propagation_id)`, *"two propagation attempts of ONE CandidateID
(different PropagationID) are DISTINCT ids"* (§0.9 step (0)(b)). Callers that pass BOTH ids: the
PATH-B pause `EnterLowPowerListen` (§7) issues `ApplyMinerStateTransition(..., candidate_id =
pause_cause_candidate_id, propagation_id = pause_cause_propagation_id)` (`# J3: BOTH ids`); its
caller `CertificateArrival` (§16b) supplies `pause_cause_candidate_id = CandidateID,
pause_cause_propagation_id = PropagationID`; and the both-ids resume flow `HandlePropagationFailure →
ResumeFromPause` (§16/§16a) matches on BOTH ids (`# G11: both envelope ids must match`). No
`candidate_ref = ...` form remains in any caller.

### 2.3 Event-sequence ownership, init, and preservation (J4)

`event_creation_seq` (§0.8) is *"the ONE per-RUN monotonic event-creation counter. Owned SOLELY by
the event-loop scheduler (`ScheduleEvent`, §0.7e/J9); assigned atomically to each scheduled event
AFTER deterministic stable ordering is established. It is the `event_seq` in every event envelope
(§0.2) and in every `TransitionEventID` (J3). Initialised once at run start and preserved across
rounds (I-04); there is NO ambient undeclared seq."* `RoundInitialise` (§1) sets it exactly once at
run start (`prior_state = null`: `SET event_creation_seq <- 0`) and PRESERVES it thereafter
(`prior_state != null`: `PRESERVE ... event_creation_seq from prior_state (§3.12)`), and returns it
in the RoundContext among the per-run event-loop bookkeeping carried forward across rounds.

### 2.4 The central scheduler `ScheduleEvent` (J9), 5-step body

Per §0.7e, `SCHEDULE event E(...) AT event_time = τ, delta_cycle = k, microphase = m` is SHORTHAND
for `CALL ScheduleEvent(RoundContext, E, τ, k, m, envelope_fields)`; *"there is no other enqueue
path."* Its body:

1. **Reject finalised times.** `IF target_event_time in finalised_event_times: RETURN
   rejected_finalised_time` — a finalised event_time's security epilogue (I-02) has already run.
2. **Delta-cycle forward rule (§0.7-H2).** `SET dc <-
   forward_delta_cycle(target_event_time, target_delta_cycle, target_microphase,
   current_delta_cycle)` — a same-time event at/earlier-than the creating microphase goes to
   `delta_cycle + 1`; never backward.
3. **Assign seq atomically, AFTER ordering.** `SET event_creation_seq <- event_creation_seq + 1;
   SET seq <- event_creation_seq` — after the `(delta_cycle, microphase, stable_tie_key)` order is
   established, so queue order is reproducible and iteration-independent (G7).
4. **Attach epoch + candidate fields.** `CREATE envelope = { ..., RoundID = RoundID_current,
   TemplateID = TemplateID_committed, CandidateID?, PropagationID?, MinerID?, AssignmentID?,
   assignment_version?, seq }`; `stable_tie_key = (CandidateID, MinerID, AssignmentID)`.
5. **Deterministic total-order insert.** `INSERT envelope INTO event_queue ORDERED BY (event_time,
   delta_cycle, microphase, (CandidateID, MinerID, AssignmentID), seq)`.

## 3. Envelope field → source → who sets it → correction

| Envelope field (§0.2) | Source | Who sets it | Correction |
|---|---|---|---|
| `event_type` | caller's `SCHEDULE` expression | caller (via `ScheduleEvent`) | prior |
| `event_time` | `target_event_time` argument | caller; rejected if finalised (step 1) | J9 |
| `delta_cycle` | `forward_delta_cycle(...)` | `ScheduleEvent` step 2 | J9 (H2) |
| `microphase` | `target_microphase` argument | caller (via `ScheduleEvent`) | prior (H2) |
| `RoundID` | `RoundID_current` | `ScheduleEvent` step 4 | J9 |
| `TemplateID` | `TemplateID_committed` | `ScheduleEvent` step 4 | J9 |
| `CandidateID?` | `envelope_fields` | caller (via `ScheduleEvent`) | J3 |
| `PropagationID?` | `envelope_fields` | caller (via `ScheduleEvent`) | J3 |
| `MinerID?` | `envelope_fields` | caller (via `ScheduleEvent`) | prior |
| `AssignmentID?` | resolved from `assignment_ref` | resolved | prior |
| `assignment_version?` | resolved from `assignment_ref` | resolved | prior |
| `seq` (= `event_creation_seq`) | per-run counter (§0.8) | `ScheduleEvent` step 3 (atomic) | J4 / J9 |

The `TransitionEventID` tuple (§0.9 step (0)) draws from this same envelope: `(event_time,
delta_cycle, event_seq, MinerID, old_state, new_state, reason, AssignmentID, assignment_version,
candidate_id, propagation_id)` — `event_seq` is resolved from the dispatching envelope's `seq` (J4);
`candidate_id`/`propagation_id` are passed by the caller (J3); `old_state`/`new_state`/`reason` are
transition arguments; `AssignmentID`/`assignment_version` are resolved from `assignment_ref`.

## 4. One deterministic scheduler contract (gate 11); no ad-hoc enqueue

All scheduling goes through the ONE deterministic scheduler contract `ScheduleEvent` (§0.7e/J9,
requirement R74) — the acceptance gate 11: *sole enqueue interface, rejects finalised event_times,
assigns `event_creation_seq`, applies the delta-cycle forward rule, attaches RoundID/TemplateID +
candidate fields, deterministic total-order insert.* Every `SCHEDULE ...` in the document is shorthand
for a `ScheduleEvent` call, so there is NO ad-hoc enqueue path that could bypass the finalised-time or
ordering rules (R74 forbidden behaviour: *"ad-hoc enqueue bypassing the finalised-time and ordering
rules"*).

## 5. Worked examples

### TV75 — two propagation attempts of one CandidateID → distinct `TransitionEventID`s (J3)

One `CandidateID` runs two propagation attempts, `PropagationID = p1` then `p2`, each causing a
candidate-triggered PATH-B pause via `EnterLowPowerListen` (§7). Both calls pass BOTH `candidate_id`
and `propagation_id` (J3). Since `TransitionEventID` includes `(candidate_id, propagation_id)`, the
`p1` transition id and the `p2` transition id DIFFER even though `CandidateID` is identical — the two
attempts are distinct transitions, neither conflated nor falsely suppressed in
`transition_event_registry`. The old `candidate_ref` ambiguity is gone. (Reqs: **J3**.)

### TV79 — `event_creation_seq` init once, preserved, deterministic ordering (J4/J9)

A run starts (`prior_state = null`): `RoundInitialise` sets `event_creation_seq <- 0` ONCE (§1).
Round 1 schedules events; round 2 begins (`prior_state != null`) and `RoundInitialise` PRESERVES
`event_creation_seq` (§3.12), never re-zeroing it. Every `ScheduleEvent` call increments the counter
and stamps `seq = event_creation_seq` AFTER the deterministic `(delta_cycle, microphase,
stable_tie_key)` order. Two runs with the same seeds/inputs assign identical seqs, so the total-order
key `(event_time, delta_cycle, microphase, stable_tie_key, seq)` yields identical processing order —
one owner, one initialisation, preserved across rounds, no ambient seq. (Reqs: **J4**, J9, I-04.)

## 6. Acceptance-style PASS checklist

| # | Check | Result | Ground |
|---|---|---|---|
| C1 | `ApplyMinerStateTransition` INPUTS carry the full envelope incl. `event_time`, `delta_cycle`, `event_seq`, `candidate_id`, `propagation_id` | PASS | §0.9 INPUTS (J3/J4) |
| C2 | Ambiguous `candidate_ref` REPLACED by explicit `candidate_id` AND `propagation_id`; no `candidate_ref = ...` in any caller | PASS | §0.9; §7; §16b; §16a |
| C3 | Every candidate-triggered caller passes BOTH ids | PASS | `EnterLowPowerListen` (§7); `CertificateArrival` (§16b); `HandlePropagationFailure`/`ResumeFromPause` (§16/§16a) |
| C4 | `TransitionEventID` includes both ids → distinguishes two propagation attempts of one `CandidateID` | PASS | §0.9 step (0)(b); TV75 |
| C5 | ONE per-run monotonic `event_creation_seq`; no ambient undeclared seq | PASS | §0.8; §0.2 |
| C6 | `event_creation_seq` initialised once at run start (`prior_state = null`: `<- 0`) and preserved across rounds (§3.12) | PASS | §1 `RoundInitialise`; TV79 |
| C7 | `event_creation_seq` owned SOLELY by `ScheduleEvent`, assigned atomically AFTER deterministic ordering; it is `seq`/`event_seq` in every envelope and every `TransitionEventID` | PASS | §0.8; §0.7e step 3 |
| C8 | `ScheduleEvent` is the SOLE enqueue interface; every `SCHEDULE` is shorthand for it | PASS | §0.7e |
| C9 | `ScheduleEvent` rejects `target_event_time in finalised_event_times` → `rejected_finalised_time` | PASS | §0.7e step 1 |
| C10 | Deterministic total-order insert `(event_time, delta_cycle, microphase, (CandidateID, MinerID, AssignmentID), seq)` | PASS | §0.7e step 5; §0.2 |
| C11 | One deterministic scheduler contract (gate 11); no ad-hoc enqueue | PASS | §0.7e/J9; R74 |
| C12 | A1 baseline unchanged; no new consensus feature; no property claimed | PASS | A1 = 8.420833333 kWh; §0 |

---

## Result

**EVENT ENVELOPE AUDIT (Stage 1J): PASS** — every scheduled event carries the immutable §0.2 envelope
whose `seq` is the single per-run `event_creation_seq` (J4) owned SOLELY by the central scheduler
`ScheduleEvent` (§0.7e/J9), initialised once at run start and preserved across rounds (§1/§3.12);
`ScheduleEvent` is the sole enqueue interface (gate 11, R74) that rejects finalised event_times,
applies the delta-cycle forward rule (H2), assigns `event_creation_seq` atomically after deterministic
ordering, attaches the RoundID/TemplateID epoch and candidate fields, and inserts by the deterministic
total-order key — with no ad-hoc enqueue; and `ApplyMinerStateTransition` (§0.9) receives the FULL
envelope with the ambiguous `candidate_ref` REPLACED by explicit `candidate_id` AND `propagation_id`,
both passed by every candidate-triggered caller (§7/§16b/§16a), so its `TransitionEventID`
distinguishes two propagation attempts of one `CandidateID` (TV75) and event ordering is reproducible
across reruns (TV79), leaving the A1 baseline (8.420833333 kWh) unchanged with no new consensus
feature and no property claimed.
