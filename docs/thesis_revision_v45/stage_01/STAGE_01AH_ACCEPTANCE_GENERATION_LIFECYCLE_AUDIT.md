# Stage 1AH — Acceptance-Batch Generation Lifecycle & Candidate-Failure Owner Audit (AH7)

**Audit target:** AH7 — acceptance-batch generation lifecycle + candidate-failure owner.
**Scope:** documentation-only pseudocode revision (Stage 1AH). This audit inspects ONLY the
final normative tree under `docs/thesis_revision_v45/stage_01/`; the primary artifact is
`STAGE_01_PROTOCOL_PSEUDOCODE.md`. No historical Stage-1A…1AG artifact is modified and no
executable source is claimed.

**Context invariants (unchanged by AH7).** The algorithm is **PoCol** and the mechanism is
**the idle policy within PoCol** (`STAGE_01_PROTOCOL_PSEUDOCODE.md:6`–`7`). The A1 accepted
energy baseline **`8.420833333 kWh`** is unchanged — AH7 is a structural data-model /
candidate-failure-ownership revision that touches no census value, residency interval, or
transition-energy quantity.

All line anchors below are `file:line` into `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless a different
file is named.

---

## Check AH7.1 — `acceptance_batch_registry` is generation-keyed in the core data model; the obsolete per-`(acceptance_timestamp, acceptance_point)` claim is dropped; every root+companion statement carries `batch_generation`

**Requirement.** The `STRUCTURE RoundContext registries` declaration must key
`acceptance_batch_registry` by `(acceptance_timestamp, acceptance_point, batch_generation)` and
explicitly WITHDRAW the obsolete per-`(acceptance_timestamp, acceptance_point)` key. Every
root/companion statement of "one AcceptanceBatchFinalize per (…)" must read
`(acceptance_timestamp, acceptance_point, batch_generation)` — namely the §0.7 microphase text,
the §0.7g enqueue text, and the `AcceptanceBatchFinalize` NOTE.

**Evidence.**
- Core data model (`STRUCTURE RoundContext registries`): `acceptance_batch_registry` declared
  "map `(acceptance_timestamp, acceptance_point, batch_generation)` -> list of registered block
  arrivals" and "GENERATION-KEYED in the core data model (AG7/AH7)" at `1615`–`1616`; the obsolete
  key is expressly retired — "the obsolete per-(acceptance_timestamp, acceptance_point) key is
  WITHDRAWN" (`1617`), with the later-delta rationale ("a later-delta same-timestamp arrival after
  a consumed finalize registers into a NEW generation (never a stranded batch)") at `1617`–`1618`.
- §0.7 microphase text: PHASE 4 runs `AcceptanceBatchFinalize` "exactly once per
  (`acceptance_timestamp`, acceptance point, `batch_generation`) (AH7)" at `139`.
- §0.7g enqueue text: `AcceptanceBatchFinalize` "is enqueued once per (`acceptance_timestamp`,
  acceptance point, `batch_generation`) (AH7)" at `1009`–`1010`.
- `AcceptanceBatchFinalize` NOTE: "exactly one finalize per (`acceptance_timestamp`, acceptance
  point, `batch_generation`)" at `6349`.
- Companion statements (all generation-qualified): seat data-model NOTE "There is EXACTLY ONE
  AcceptanceBatchFinalize per (acceptance_timestamp, acceptance_point, batch_generation)"
  (`1620`–`1621`); `BlockAcceptancePoint` NOTE "The ONE AcceptanceBatchFinalize per (timestamp,
  acceptance point, generation)" (`6167`); `SeatAcceptanceBatchFinalize` NOTE "the ONE named owner
  that seats the AcceptanceBatchFinalize of a (timestamp, acceptance point) GENERATION" (`6207`);
  and the "EXACTLY ONE live AcceptanceBatchFinalize seat per (acceptance_timestamp,
  acceptance_point) GENERATION" line at `6181`. No surviving statement claims one finalize per a
  bare `(acceptance_timestamp, acceptance_point)` pair.

**Result: PASS.**

---

## Check AH7.2 — `ACCEPTANCE_BATCH_UNFINALISABLE` added to the candidate `failure_reason` enum AND to `HandlePropagationFailure`'s accepted `failure_reason` set

**Requirement.** The candidate `failure_reason` enum must include `ACCEPTANCE_BATCH_UNFINALISABLE`,
and `HandlePropagationFailure`'s PRECONDITIONS `failure_reason` set must accept it.

**Evidence.**
- Candidate `failure_reason` field enum: `{REJECTED, BLOCK_UNAVAILABLE, PROPAGATION_TIMEOUT,
  NO_VALID_CANDIDATE, ACCEPTANCE_BATCH_UNFINALISABLE} or null` at `1598`–`1599`, with the AH7 gloss
  "the finalize seat could not be created" (`1599`).
- `HandlePropagationFailure` PRECONDITIONS: `failure_reason in {REJECTED, BLOCK_UNAVAILABLE,
  PROPAGATION_TIMEOUT, NO_VALID_CANDIDATE, ACCEPTANCE_BATCH_UNFINALISABLE}` at `6221`–`6222`,
  annotated "AH7: added the finalize-seat-failure reason" (`6222`).

**Result: PASS.**

---

## Check AH7.3 — the finalize-seat-failure path routes through the SINGLE named candidate-failure owner `HandlePropagationFailure`, NOT an inline `status <- FAILED` that leaves the candidate in `active_propagation_set` (the AG defect)

**Requirement.** In `BlockAcceptancePoint`, the seat-failure case must delegate to
`HandlePropagationFailure` (which sets FAILED AND removes the candidate from
`active_propagation_set` AND cancels its events AND resumes only its matching paused miners). It
must NOT set `status <- FAILED` inline while leaving the candidate in `active_propagation_set`.

**Evidence.**
- `BlockAcceptancePoint` seat-failure case (`CASE acceptance_batch_finalize_seat_failed(reason)`)
  at `6144`: it does NOT register the arrival and calls the named owner —
  `CALL HandlePropagationFailure(RoundContext, CandidateID, PropagationID, failure_reason =
  ACCEPTANCE_BATCH_UNFINALISABLE, dispatch_envelope = dispatch_envelope)` at `6150`–`6151`, then
  `RECORD acceptance_batch_seat_failed(...)` (`6152`) and returns
  `acceptance_registration_failed(...)` (`6153`). There is NO inline `status <- FAILED` on this
  path; the intent comment at `6145`–`6149` states the owner "sets FAILED, REMOVES it from
  active_propagation_set, cancels its remaining events, and resumes ONLY its paused miners — so a
  FAILED candidate is NEVER left in active_propagation_set (the AG defect)".
- `HandlePropagationFailure` performs the full owner contract: `SET status(cpc) <- FAILED` (`6235`);
  `SET failure_reason(cpc) <- failure_reason` (`6236`); `REMOVE cpc from active_propagation_set`
  (`6238`); cancels this candidate's certificate-arrival events (`6241`) and its block-arrival event
  (`6242`); resumes ONLY miners whose pause cause matches BOTH ids of this candidate
  (`6245`–`6256`). Its NOTE reaffirms "A candidate is NEVER left status=FAILED while still in
  active_propagation_set" (`6229`).
- Defect-absence check: a search for an inline `status(...) <- FAILED` returns exactly one hit,
  `6036` in `ScheduleSolutionPropagation` (self-validation failure of a context that is "never
  propagation-active" — it was never added to `active_propagation_set`), which is a legitimate
  non-set path and NOT the AH7 seat-failure path. `BlockAcceptancePoint` contains no inline FAILED.

**Result: PASS.**

---

## Check AH7.4 — `BlockAcceptancePoint` receives its OWN `dispatch_envelope` (recv env = yes in descriptor row + binding row + INPUTS), threads it to `HandlePropagationFailure`, and the note declares `ActiveHashRateUpdate` the ONLY recv env = no

**Requirement.** `BlockAcceptancePoint` must have `recv env` = yes in its executable descriptor
row, its descriptor-binding row, and its handler INPUTS line; it must thread that envelope to
`HandlePropagationFailure`; and the descriptor prose must state that `ActiveHashRateUpdate` is now
the ONLY `recv env` = no.

**Evidence.**
- Executable descriptor row (§0.7g-schema): `BlockAcceptancePoint … | FULL_BLOCK_ARRIVAL |
  (CandidateID, PropagationID) | — | **yes** (AH7) | no |` at `1138` (the `recv env` column is
  **yes**).
- Descriptor-binding row: `BlockAcceptancePoint … runtime_injected` includes
  `dispatch_envelope -> dispatch_envelope` with "(AH7: recv env = yes — threaded ONLY to the
  candidate-failure owner on the finalize-seat-failure path; NO `dispatched_event_ref`)" at `1169`.
- Handler INPUTS line: `INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID,
  outcome, dispatch_envelope   # AH7: dispatch_envelope (recv env = yes)` at `6122`.
- Threaded to the owner: `HandlePropagationFailure(..., dispatch_envelope = dispatch_envelope)` at
  `6150`–`6151`, and `HandlePropagationFailure` INPUTS declare `dispatch_envelope` at `6220`, with
  the source note "the dispatched BlockAcceptancePoint's own envelope" (`6225`).
- Descriptor prose: "`ActiveHashRateUpdate` is now the ONLY descriptor with `recv env` = no" at
  `1213`, immediately followed by "**AH7: `BlockAcceptancePoint` becomes `recv env` = yes**"
  (`1214`), noting the type-correct envelope replaces "the withdrawn AF8
  `ORDINARY_DISPATCH(EventRef)`" (`1215`). Corroborated by the `ActiveHashRateUpdate` descriptor row
  `… | MONITORING | (t) | — | **no** | no |` at `1144` and its binding row "(no envelope)" at `1175`.

**Result: PASS.**

---

## Check AH7.5 — every closure path cancels `acceptance_batch_finalize_seat[key].EventRef` (NOT the whole `{generation, EventRef}` record)

**Requirement.** Both `RoundAbort` and `CloseRoundAssignments` must cancel the seat via its
`.EventRef` field, never by passing the whole `{generation, EventRef}` record to
`CancelQueuedEvent`.

**Evidence.**
- `CloseRoundAssignments` (procedure at `6405`): iterates seat keys in stable order (`6494`) and
  cancels `acceptance_batch_finalize_seat[key].EventRef` (`6495`), then `CLEAR
  acceptance_batch_finalize_seat` (`6496`) and `CLEAR acceptance_batch_registry` (`6497`). The
  preceding comment is explicit: cancel "using its .EventRef (NOT the { generation, EventRef }
  record)" (`6491`–`6492`).
- `RoundAbort` (procedure at `6840`): iterates seat keys in stable order (`6866`) and cancels
  `acceptance_batch_finalize_seat[key].EventRef` (`6867`), then `CLEAR
  acceptance_batch_finalize_seat` (`6868`) and `CLEAR acceptance_batch_registry` (`6869`). The
  preceding comment states "the stored value is { generation, EventRef } — cancel its .EventRef,
  NEVER the whole record (a record is not an EventRef; passing the record was a type error)"
  (`6863`–`6865`).

**Result: PASS.**

---

## Check AH7.6 — every create/read/cancel/clear site uses the correct generation key and correct `.EventRef` typing

**Requirement.** All sites touching `acceptance_batch_registry` (generation-keyed) and
`acceptance_batch_finalize_seat` (value `{generation, EventRef}`) must use the correct key shape
and the correct `.EventRef` typing.

**Evidence — `acceptance_batch_registry`.**
- Initialise: `INITIALISE acceptance_batch_registry <- empty` in `RoundInitialise` (`2818`);
  returned as a per-round registry at `2877`.
- Create (append): `APPEND (...) to acceptance_batch_registry[(now, RoundContext.acceptance_point,
  gen)]` at `6159` — generation-keyed by the live `gen` captured from the seat result (`6142`–`6143`).
- Read: `SET batch <- acceptance_batch_registry[(acceptance_timestamp, acceptance_point,
  batch_generation)]` at `6322` — generation-keyed.
- Clear one generation: `CLEAR acceptance_batch_registry[(acceptance_timestamp, acceptance_point,
  batch_generation)]` at `6347` — generation-keyed, "clear ONLY this generation's batch".
- Bulk clears at closure: `CLEAR acceptance_batch_registry` (`6497`, CloseRoundAssignments) and
  (`6869`, RoundAbort); template-refresh bulk clear "CLEAR every acceptance_batch_registry entry
  whose acceptance_point candidates are bound to old_TemplateID" (`6679`) — correct as a
  whole-entry clear scoped by template binding (generation-agnostic by design).

**Evidence — `acceptance_batch_finalize_seat`.**
- Initialise: `INITIALISE acceptance_batch_finalize_seat <- empty map` in `RoundInitialise`
  (`2819`); returned at `2877`.
- Owner `SeatAcceptanceBatchFinalize` (procedure at `6173`): key `(acceptance_timestamp,
  acceptance_point)` at `6186`; reads `s.EventRef`/`s.generation` (`6188`–`6192`); stores the value
  as `{ generation = generation, EventRef = event_ref }` at `6202`, matching the data-model value
  type at `1619`–`1620`.
- Read in dispatch: `queued_event_registry[s.EventRef].queue_status` at `6189` — `.EventRef` typing.
- Cancel/clear at closure: `.EventRef` cancels at `6495` (CloseRoundAssignments) and `6867`
  (RoundAbort); `CLEAR acceptance_batch_finalize_seat` at `6496` and `6868`.
- Consistency note: the seat map is intentionally keyed by `(acceptance_timestamp,
  acceptance_point)` (it holds only the CURRENT generation's live seat, per `1619`–`1620`), while
  the registry is keyed by the full `(acceptance_timestamp, acceptance_point, batch_generation)`
  triple. The two key shapes are correct and mutually consistent; the generation lives inside the
  seat value and advances via `SeatAcceptanceBatchFinalize` (`6191`–`6194`).

**Result: PASS.**

---

## Overall verdict

**PASS.** All six AH7 checks hold against the final normative text of
`STAGE_01_PROTOCOL_PSEUDOCODE.md`: `acceptance_batch_registry` is generation-keyed in the core data
model with the obsolete per-`(acceptance_timestamp, acceptance_point)` key withdrawn and every
root/companion "one finalize per (…)" statement generation-qualified (AH7.1);
`ACCEPTANCE_BATCH_UNFINALISABLE` is present in both the candidate `failure_reason` enum and
`HandlePropagationFailure`'s accepted set (AH7.2); the finalize-seat-failure path routes solely
through the named candidate-failure owner `HandlePropagationFailure` with no inline
FAILED-left-in-set defect (AH7.3); `BlockAcceptancePoint` carries its own `dispatch_envelope`
(recv env = yes in descriptor row, binding row, and INPUTS), threads it to the owner, and the prose
names `ActiveHashRateUpdate` the only `recv env` = no descriptor (AH7.4); both closure paths cancel
the seat via `.EventRef`, never the whole record (AH7.5); and every create/read/cancel/clear site
uses the correct key shape and `.EventRef` typing (AH7.6). The algorithm remains **PoCol** with
**the idle policy within PoCol**, and the A1 baseline `8.420833333 kWh` is unchanged.
