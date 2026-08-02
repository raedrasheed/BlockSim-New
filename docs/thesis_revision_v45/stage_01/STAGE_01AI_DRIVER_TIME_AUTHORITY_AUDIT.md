# Stage 1AI — Driver-Time Authority & Scheduler-Frontier Audit (AI2)

**Audit stage:** Stage 1AI (documentation-only formal-spec correction; no source, config, DOCX, PDF, or
Stage-1A..1AH artifact touched).
**Correction under audit:** AI2 — *authoritative driver-time source + `ScheduleEvent` context checks*.
**Normative object audited:** `docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`
(the FINAL normative tree of the BlockSim/PoCol Stage-1 protocol).
**Method:** every claim below is discharged against an exact `file:line` anchor read from the normative
pseudocode. Anchors are cited as `STAGE_01_PROTOCOL_PSEUDOCODE.md:<line>`. No experiment was run; no artifact
other than this audit file was created or modified.

---

## 1. Defect statement (the pre-AI2 hazard)

Prior to AI2 a sim-driver seat owner derived the *source* time of a `ScheduleEvent` seat as a copy of the
*target* it was about to seat: `source_event_time = requested_event_time`. Because the admissibility guard a
driver seat is subjected to is `target_event_time >= source_event_time`, making the source a copy of the target
reduced that guard to `requested_event_time >= requested_event_time`, which is *vacuously true*. The check was
therefore **self-validating** (source == target): it could never fail, and it carried no information about how
far the simulation had actually advanced.

Consequence: a **stale or mismatched target** — a `requested_event_time` lying *behind the simulation
frontier* (an event_time the run had already finalised) — could be admitted and seated behind that frontier.
The event loop could then be made to move from a later, already-processed time back to an earlier,
newly-admitted driver time, violating the monotone-progress discipline of the idle policy within PoCol and of
the driver-intake path generally. There was no authoritative run-level "how far has the simulation advanced"
fact for either the admission layer (`AdmitDriverRequest`) or the enqueue layer (`ScheduleEvent`) to consult.

The self-validating construction is expressly disavowed by the corrected text: `AdmitDriverRequest` derives the
admission time from the run frontier and annotates the derivation *"not self-validating (source != target)"*
(`STAGE_01_PROTOCOL_PSEUDOCODE.md:1729`); the `RunContext` frontier field is annotated *"NOT a copy of any
requested_event_time"* (`STAGE_01_PROTOCOL_PSEUDOCODE.md:2939-2940`).

## 2. The AI2 fix (design in one paragraph)

A single authoritative run-level fact — `RunContext.last_finalised_event_time` (the simulation frontier) — is
introduced, written *only* by `ProcessEventTime` as it finalises each event_time (monotonically, never
rewound), and reaches the horizon `T` on the no-round finalisation path too. `AdmitDriverRequest` derives the
`driver_admission_time` from that frontier (or from `config.run_start_time` before any finalisation), stamps it
onto the driver_request as a value structurally *distinct* from the request's `requested_event_time`, and
rejects a `requested_event_time` behind the frontier. Each DRIVER seat owner carries that
`driver_admission_time` as the seat's `source_event_time` (never the target). `ScheduleEvent`'s `DRIVER` and
`TERMINAL_ROTATION` cases then validate carried-context identity, kind↔event_type permission, target↔carried-
target agreement, `target >= source`, and — decisively — `target` not behind the frontier, before any state is
mutated. Four new structured rejection variants carry these failures.

---

## 3. Numbered verification table

| # | AI2 claim | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md`) | Verdict |
|---|-----------|----------------------------------------------|---------|
| 1 | Defect characterised: a driver seat used `source_event_time = requested_event_time` (source == target), a self-validating check admitting a stale/mismatched target behind the frontier. | Disavowal at `:1729` (`not self-validating (source != target)`); frontier field `NOT a copy of any requested_event_time` at `:2939-2940`; defensive grep across the whole file returns **zero** occurrences of `source_event_time = requested_event_time` or `= target`. | **PASS** |
| 2 | `STRUCTURE RunContext` declares `last_finalised_event_time` (authoritative frontier), the single source of truth for how far the simulation has advanced. | Declared and specified at `:2931-2940`. | **PASS** |
| 3 | `RunInitialise` initialises `last_finalised_event_time <- NONE`. | `INITIALISE last_finalised_event_time <- NONE` at `:3096`. | **PASS** |
| 4 | `RunInitialise` returns `last_finalised_event_time` in its RETURNS. | `last_finalised_event_time = NONE` in RETURNS at `:3131`. | **PASS** |
| 5 | `ProcessEventTime` is the SOLE writer; it advances the frontier *after* `ADD t to finalised_event_times`, monotonically (never rewound). | `ADD t` at `:422`; sole-writer rationale `:423-427`; monotone advance `IF ... t > last_finalised_event_time: SET ... <- t` at `:428-429`; "SOLE writer" also asserted in the structure at `:2934`. | **PASS** |
| 6 | `FinalizeSimulationRunNoRound` advances the frontier to `run_horizon_T`. | `IF ... run_horizon_T > last_finalised_event_time: SET ... <- run_horizon_T` at `:7366-7367`. | **PASS** |
| 7 | `AdmitDriverRequest` derives `driver_admission_time` from `last_finalised_event_time` (or `config.run_start_time` before any finalisation), NOT a copy of `requested_event_time`. | Ternary derivation `(last_finalised_event_time = NONE ? config.run_start_time : last_finalised_event_time)` at `:1726-1727`. | **PASS** |
| 8 | `AdmitDriverRequest` rejects `requested_event_time < driver_admission_time` with `driver_request_time_before_admission_rejected`. | Guard `IF requested_event_time < driver_admission_time: RETURN driver_request_time_before_admission_rejected(...)` at `:1728-1729`; in RETURNS union at `:1753`. | **PASS** |
| 9 | `STRUCTURE DriverSchedulingContext` (§0.7e) carries `source_event_time = driver_admission_time`, `target_event_time`, `intended_round_scope`, `RunContext`, `EventQueueContext`. | Structure header `:693`; `source_event_time` = authoritative admission time `:704-707`; `target_event_time` `:708-710`; `intended_round_scope` `:711-713`; `RunContext` `:714`; `EventQueueContext` `:715`. | **PASS** |
| 10 | `STRUCTURE TerminalRotationSchedulingContext` exists (§0.7e). | Structure header `:722`; fields `BootstrapRequestID`/`predecessor_terminal_time`/`target_event_time`/`RunContext`/`EventQueueContext` at `:728-732`. | **PASS** |
| 11 | `ScheduleEvent` DRIVER case verifies carried EQ/RunContext identity, else `rejected_driver_context_mismatch`. | `IF (dctx.EventQueueContext is NOT EQ) OR (dctx.RunContext.EventQueueContext is NOT EQ): RETURN rejected_driver_context_mismatch(...)` at `:895-896`. | **PASS** |
| 12 | DRIVER case verifies `driver_kind_may_seat(kind, event_type)`, else `rejected_driver_kind_event_type_mismatch`. | `IF NOT driver_kind_may_seat(dctx.driver_source_kind, event_type): RETURN rejected_driver_kind_event_type_mismatch(...)` at `:897-898`. | **PASS** |
| 13 | DRIVER case verifies `target == carried target`, else `rejected_driver_target_context_mismatch`. | `IF target_event_time != dctx.target_event_time: RETURN rejected_driver_target_context_mismatch(...)` at `:899-900`. | **PASS** |
| 14 | DRIVER case verifies `target >= source` (else `rejected_driver_target_before_source`, AH1). | `IF NOT (target_event_time >= dctx.source_event_time): RETURN rejected_driver_target_before_source(...)` at `:901-902`. | **PASS** |
| 15 | DRIVER case verifies `target` not behind the frontier, else `rejected_driver_target_before_simulation_frontier`. | `IF dctx.RunContext.last_finalised_event_time != NONE AND target_event_time < dctx.RunContext.last_finalised_event_time: RETURN rejected_driver_target_before_simulation_frontier(...)` at `:903-904`. | **PASS** |
| 16 | `ScheduleEvent` TERMINAL_ROTATION case performs the same five checks (context identity, kind, target-context, strictly-later-than-predecessor source, frontier). | Context `:909-910`; kind (`ROUND_ROTATION_BOOTSTRAP`) `:911-912`; target-context `:913-914`; `target > predecessor_terminal_time` `:915-916`; frontier `:917-918`. | **PASS** |
| 17 | All four new rejection variants appear in `ScheduleEvent`'s RETURNS union. | `rejected_driver_target_before_simulation_frontier` `:993`; `rejected_driver_context_mismatch` `:994`; `rejected_driver_kind_event_type_mismatch` `:995`; `rejected_driver_target_context_mismatch` `:996`. | **PASS** |
| 18 | The `driver_kind_may_seat(kind, event_type)` notation is defined with exactly the four TRUE pairs (and FALSE otherwise). | Predicate defined `:764-772`: `RUN_BOOTSTRAP→RoundInitialiseEvent` `:766`; `ROUND_ROTATION_BOOTSTRAP→RoundInitialiseEvent` `:767`; `MINER_JOIN→MinerRegisterEvent` `:768`; `ORDINARY_RESERVE_DEFICIT→ReserveActivateEvent` `:769`; `(_,_) = FALSE` `:770`. | **PASS** |
| 19 | Property stated: the simulation never moves from a later processed time back to an earlier newly-admitted driver time. | Stated in the `ProcessEventTime` frontier rationale `:427`, in the `ScheduleEvent` NOTE `:1031`, and in the `RunContext` field spec `:2938-2939`. | **PASS** |

---

## 4. Explicit check — `source_event_time` is NO LONGER a copy of `requested_event_time` in any DRIVER seat owner

The core of AI2 is that no sim-driver seat owner may re-derive the seat *source* from the seat *target*. Each
of the three DRIVER-origin seat owners is inspected individually, and the whole normative file is swept for the
forbidden pattern.

| Seat owner | Origin built | `source_event_time` set to | `target_event_time` set to | Anchor | Copy of requested? |
|------------|--------------|----------------------------|----------------------------|--------|--------------------|
| `SeatMinerRegister` (DRIVER_INTAKE) | `DRIVER(DriverSchedulingContext(...))` | `driver_request.driver_admission_time` | `driver_request.requested_event_time` | `:1630-1635` (source at `:1632`, target at `:1633`) | **No** — source is the authoritative admission time, target is the request; distinct fields. |
| `SeatReserveActivate` | `DRIVER(DriverSchedulingContext(...))` | `driver_request.driver_admission_time` | `driver_request.requested_event_time` | `:1669-1673` (source at `:1670`, target at `:1671`) | **No** — same distinct-field discipline. |
| `SeatNextRoundBootstrap` (run-start `RUN_BOOTSTRAP`) | `DRIVER(DriverSchedulingContext(...))` | `RunContext.config.run_start_time` | `br.target_time` | `:1530-1532` (source and target at `:1531`) | **No** — source is the run-start clock, not a target copy. |
| `SeatNextRoundBootstrap` (rotation) | `TERMINAL_ROTATION(TerminalRotationSchedulingContext(...))` — AI8 moved the rotation off the DRIVER union | source is `predecessor_terminal_time`; target strictly later | `:1534-1536` | **No** — rotation source is the predecessor terminal time. |

**File-wide sweep.** A regex sweep for `source_event_time = <...>requested_event_time`, `source_event_time =
requested`, and `source_event_time = target` across the entire normative file returns **zero matches**. Every
`source_event_time = requested_event_time` assignment (the pre-AI2 pattern) has been removed; the only
`source_event_time` assignments that survive bind it to `driver_admission_time`, `config.run_start_time`, the
drained epilogue `t` (post-epilogue seats), or the predecessor terminal time — never to the target.

**Admission-layer corroboration.** The `driver_admission_time` that the two request-backed owners carry as the
source is itself derived from the frontier at `AdmitDriverRequest:1726-1727` and stored as a field distinct
from `requested_event_time` on the driver_request (`STAGE_01_PROTOCOL_PSEUDOCODE.md:1744-1745`). Thus the
source and target are provably distinct values by construction, and the guard `target >= source` (`:901-902`)
plus the frontier guard (`:903-904`) are *informative*, not vacuous.

**Verdict for §4: PASS** — `source_event_time` is not a copy of `requested_event_time` in any DRIVER seat
owner, and the self-validating construction is absent from the entire normative tree.

---

## 5. Coherence observations (rigor notes; not defects)

1. **Frontier guard boundary is exact.** The `ScheduleEvent` frontier rejection fires on `target_event_time <
   last_finalised_event_time` (strict), so it permits `target == frontier`. This is not a gap: the frontier is
   the maximum of `finalised_event_times` (`:2931-2933`), so `target == frontier` is a target *at an
   already-finalised time*, which the earlier guard `IF target_event_time in EQ.finalised_event_times: RETURN
   rejected_finalised_time` (`:870-871`) rejects first. The two guards jointly cover `target <= frontier`
   completely, with no admissible target at or behind the frontier.

2. **Sole-writer discipline is closed.** The frontier is written only inside `ProcessEventTime`
   (`:428-429`) and, for the null-round terminal path, `FinalizeSimulationRunNoRound` (`:7366-7367`). The
   latter finalises the horizon `T` with no epilogue (no round/census exists), so it is a genuine finalisation
   and its advance is consistent with the monotone rule. `AdmitDriverRequest` and `ScheduleEvent` are strict
   readers, matching the structure's "ProcessEventTime is its SOLE writer" claim (`:2934`).

3. **DRIVER vs TERMINAL_ROTATION split (AI8) preserves the frontier guard.** The rotation bootstrap was moved
   off the DRIVER union onto `TERMINAL_ROTATION` (`:701`, `:759-763`), but its kind↔event_type permission is
   still checked through the *same* `driver_kind_may_seat` table (`:911-912`) and it is subject to the *same*
   frontier rejection (`:917-918`). No rotation seat can slip behind the frontier.

4. **Naming fidelity.** The normative text and this audit use PoCol nomenclature throughout; the monotone
   driver-time discipline audited here is exactly what protects the idle policy within PoCol from being driven
   backward by a stale driver-intake request.

---

## 6. Overall verdict

**PASS.** All nineteen tabulated claims and the dedicated §4 seat-owner check are satisfied against exact
`file:line` anchors in the final normative tree. The authoritative simulation frontier
(`RunContext.last_finalised_event_time`) is declared, initialised to `NONE`, returned by `RunInitialise`,
written monotonically and solely by `ProcessEventTime` (and advanced to `T` by
`FinalizeSimulationRunNoRound`), consulted by `AdmitDriverRequest` for the admission floor, and enforced by
`ScheduleEvent`'s `DRIVER`/`TERMINAL_ROTATION` cases through four new structured rejection variants. The
pre-AI2 self-validating `source_event_time = requested_event_time` construction is absent from every seat owner
and from the entire normative file. The property "the simulation never moves from a later processed time back
to an earlier newly-admitted driver time" is stated and structurally enforced.

**No genuine FAIL identified.**
