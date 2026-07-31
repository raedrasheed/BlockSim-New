# Stage 1M — PENDING Lease-Expiry Executability & Wake Stale-Target Guard Audit (M3)

Audits correction **M3**: PENDING lease expiry is now **executable**, and `WakeCompleteEvent` now
BEGINS with an explicit **stale-target guard**. `LeaseExpiry` §12 `CASE PENDING` no longer defers to an
implicit "the pending wake self-cancels" hand-wave; it identifies and CANCELs the exact pending
`WakeCompleteEvent` for the head, resolves a `WAKING` holder OFF `WAKING` via the legal edge (T12,
`reason = lease_expired_while_waking`) BEFORE closing, CLOSEs the head canonically, preserves the
accepted searched prefix, and reassigns ONLY the accepted unsearched suffix — and only after the source
is `CLOSED`. In parallel, `WakeCompleteEvent` §0.10 now runs an explicit stale-target guard as its FIRST
step so a wake for a `CLOSED`/superseded/reassigned target returns `stale_wake_noop` and CANNOT activate
the miner; the spec is explicit that this guard is INDEPENDENT of the HashWorkEvent G9 guard, which does
NOT protect wakes. `CASE PAUSED` likewise now explicitly CANCELs the candidate-specific `ResumeFromPause`
and any `WakeCompleteEvent` for the closed assignment.

Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §12 `LeaseExpiry` (the executable `CASE PENDING` steps (1)–(5)
plus the common reassign tail; the augmented `CASE PAUSED` cancellations), §0.10 `WakeCompleteEvent` (the
M3 stale-target guard and its NOTE on independence from G9), §0.10 `StartWake` (which SCHEDULES the
`WakeCompleteEvent`), §0.9 `ApplyMinerStateTransition` (the T12 `WAKING → OFFLINE` edge, F6), §0.7b
`HashWorkEvent` / G9 (the guard that protects hashing, for contrast), §0.7g (the canonical
event-type → microphase mapping placing `WakeCompleteEvent` at `WAKE_COMPLETE`, §21 priority 11), §13
`RangeReassign` (the `status(source_assignment(unsearched_suffix)) = CLOSED` assertion in both
`PRECONDITIONS` and `EFFECTS`), and §0.8 `STRUCTURE Assignment` (the `status` enum `{PENDING, CURRENT,
PAUSED, SUPERSEDED, CLOSED}`, the `J7 CANONICAL TERMINAL STATUS` note, and the K6 `termination_reason`
field); and to `STAGE_01_INVARIANT_CATALOGUE.md` I18a/I18b (assignment-lineage version invariants, G2)
and I8a (coverage-state partition). This is a specification act on **PoCol** with the idle policy within
PoCol enabled — not a claim of implementation, enforcement, security, fairness, energy, or any derived
property. No new consensus feature is introduced; the eight miner states and the assignment schema are
unchanged, and the A1 baseline (8.420833333 kWh) is untouched — any energy difference is attributable
ONLY to reduced active power-time, and no property is asserted at Stage 1.

## 1. The corrected-away problem (a PENDING wake that G9 never guards)

The earlier reading of `CASE PENDING` (recorded in the Stage-1L audit) said the un-activated head is
CLOSED and "a pending `WakeCompleteEvent` for this version self-cancels under the G9 stale guard." That
reasoning is unsound, because **G9 does not run for a `WakeCompleteEvent`**. The G9 guard (§0.7b) is a
property of `HashWorkEvent`: "A pending `HashWorkEvent` becomes a no-op (or is cancelled) once its miner
is no longer `ACTIVE_HASHING` or its exact assignment version is no longer `CURRENT`." A
`WakeCompleteEvent` is a DISTINCT event type (§0.7g: target microphase `WAKE_COMPLETE`, §21 priority 11)
that fires while the miner is `WAKING` — not `ACTIVE_HASHING` — and whose whole job is to drive
`WAKING → ACTIVE_HASHING` and to activate `PENDING → CURRENT`. G9's predicate ("no longer
`ACTIVE_HASHING`", "no longer `CURRENT`") is exactly the state a legitimate pending wake is in, so G9
neither fires for it nor suppresses it.

Two concrete failures followed. (a) A `WakeCompleteEvent` scheduled by `StartWake` BEFORE the PENDING
head was closed could still be on the queue when `LeaseExpiry` CLOSEs that head. Nothing in the old
`CASE PENDING` cancelled it, and G9 does not cover it, so the wake could later dispatch, pass the
activation path, and drive the miner `WAKING → ACTIVE_HASHING`, activating a `CLOSED` (or already
REASSIGNED) target — a second live head on a closed lineage, or activation onto a range now owned by a
different `REASSIGNED` lineage, breaking I18a/I18b. (b) `CASE PENDING` was under-specified operationally:
it did not explicitly resolve a `WAKING` holder off `WAKING`, so the miner could be stranded mid-ramp
with its head gone.

## 2. The correction (M3): executable PENDING + an independent wake guard

M3 makes two coordinated changes.

**(A) `CASE PENDING` is now fully executable (§12).** In order:

1. **(1)–(2) Cancel the exact pending wake.** `CANCEL the scheduled WakeCompleteEvent for (holder,
   AssignmentID(assignment), assignment_version(assignment))` — the precise (holder, AssignmentID,
   assignment_version) triple, BEFORE closing, so no pre-scheduled wake survives the closure.
2. **(3) Resolve a `WAKING` holder off `WAKING`.** `IF miner_state(holder) = WAKING AND
   target_assignment(holder) = assignment`, `CALL ApplyMinerStateTransition(holder, WAKING, OFFLINE, …,
   reason = lease_expired_while_waking, assignment_ref = assignment, …)` — the legal T12 edge with the
   EXACT `dispatch_envelope` (F6/M1). A pre-wake holder (`REGISTERED`/`RESERVE`/`LOW_POWER_LISTEN`) needs
   no edge.
3. **(4)–(5) Close canonically, preserve coverage.** `PRESERVE accepted searched prefix
   [range_start(assignment), accepted_frontier(assignment)]`, then `ATOMICALLY` `status ← CLOSED`,
   `custody_status ← expired`, `termination_reason ← lease_expiry` (K6 canonical terminal).
4. **Common reassign tail.** `ASSERT status(assignment) = CLOSED`, compute the C4 suffix
   (`[accepted_frontier + 1, range_end]`; whole range if no accepted positions; nothing if
   `accepted_frontier = range_end`), mark it `inactive_unsearched / reassignable`, and `CALL
   RangeReassign(… reason = lease_expiry …)`, which itself re-asserts `status(source) = CLOSED`.

**(B) `WakeCompleteEvent` BEGINS with an explicit stale-target guard (§0.10).** Before any assertion or
activation:

```
IF status(target_assignment) NOT in {PENDING, PAUSED}
   OR RoundID(target_assignment) != RoundID_current OR TemplateID(target_assignment) != TemplateID_committed
   OR target_assignment is NOT the miner's bound live head (I18b):
  RETURN stale_wake_noop            # M3: cannot activate a CLOSED/superseded/stale target; miner unchanged
```

Its NOTE states plainly: "This guard is independent of the HashWorkEvent G9 guard, which does not protect
`WakeCompleteEvent`." So even if a wake for a closed target were NOT cancelled by `CASE PENDING`, the
guard is an independent backstop: a `CLOSED` head fails `status ∈ {PENDING, PAUSED}` and returns
`stale_wake_noop`; a reassigned range fails "the miner's bound live head"; a superseded round/template
epoch fails the `RoundID`/`TemplateID` check.

**(C) `CASE PAUSED` now also cancels candidate-specific resume/wake events (§12).** `CANCEL every
scheduled ResumeFromPause for (holder, pause_cause_candidate_id(assignment),
pause_cause_propagation_id(assignment))` and `CANCEL any scheduled WakeCompleteEvent for (holder,
AssignmentID(assignment), assignment_version(assignment))`, before the atomic CLOSE and the
`entry_stop_reason(holder) ← ASSIGNMENT_REVOKED` re-classification — so no scheduled resume or wake can
re-activate the miner onto the now-`CLOSED` paused head.

## 3. `CASE PENDING` — step-by-step trace table

**Preconditions.** Holder `H` is bound to PENDING head `v` (`AssignmentID = a`, `assignment_version = k`,
`range = [s, e]`, `accepted_frontier = f` with `s <= f < e`). `H` is `WAKING` toward `v`
(`target_assignment(H) = v`), and a `WakeCompleteEvent W = (H, a, k)` sits on the queue from a prior
`StartWake`. The lease expires: `LeaseExpiry(v, t)` fires at `t >= lease_expiry(v)`.

| Step | §12 `CASE PENDING` action | Effect on state | Live heads on `v`'s lineage |
|--:|---|---|:-:|
| 0 | `SWITCH status(v)` → `status(v) = PENDING` selects `CASE PENDING` | dispatch to the executable branch | 1 (`PENDING` head `v`) |
| 1 | (1)–(2) `CANCEL the scheduled WakeCompleteEvent for (H, a, k)` | `W` removed from the event queue BEFORE closure | 1 |
| 2 | (3) `miner_state(H) = WAKING AND target_assignment(H) = v` → `ApplyMinerStateTransition(H, WAKING, OFFLINE, reason = lease_expired_while_waking, assignment_ref = v, dispatch_envelope)` (T12/F6) | `miner_state(H) = OFFLINE`; the holder is resolved off `WAKING` | 1 |
| 3 | (4)–(5) `PRESERVE accepted searched prefix [s, f]` | `[s, f]` untouched (accepted coverage retained) | 1 |
| 4 | (4)–(5) `ATOMICALLY` `status(v) ← CLOSED`, `custody_status(range) ← expired`, `termination_reason(v) ← lease_expiry` | `v` terminated canonically (K6) | **0** (`CLOSED`) |
| 5 | Common tail `ASSERT status(v) = CLOSED` | holds — closed at step 4 | 0 |
| 6 | Suffix: `f != e` and accepted positions exist → `reassignable_suffix = [f + 1, e]`; `MARK inactive_unsearched / reassignable` | only the accepted unsearched suffix exposed; prefix `[s, f]` never reassigned | 0 |
| 7 | `RETURN CALL RangeReassign([f + 1, e], reason = lease_expiry, from_miner = H, dispatch_envelope)` — §13 asserts `status(source(=v)) = CLOSED` | suffix reassigned onto a SEPARATE `REASSIGNED` lineage (fresh head, different `lineage_id`) | 0 on `v`; 1 on the new lineage |

At step 4 exactly one live head existed before (the `PENDING` head `v`); zero remain on `v`'s lineage
after. The cancelled `W` (step 1) can never fire; and even if a stray wake for `v` reached dispatch, the
§0.10 stale-target guard would return `stale_wake_noop` because `status(v) = CLOSED ∉ {PENDING, PAUSED}`.

Boundary sub-cases of the tail: if `accepted_frontier(v) = e` the tail `RETURN
released_nothing_to_reassign` (range complete, nothing unsearched); if no accepted positions exist,
`reassignable_suffix = whole range [s, e]`. In every sub-case the searched prefix is preserved and the
source is `CLOSED` before `RangeReassign` is reached.

## 4. `WakeCompleteEvent` stale-target guard — before / after

| Aspect | Before M3 | After M3 (current §0.10) |
|---|---|---|
| First step of `WakeCompleteEvent` | `ASSERT miner_state(MinerID) = WAKING`, then the `wake_within_deadline` branch | explicit **STALE-TARGET GUARD** runs FIRST, before any assertion |
| Wake for a `CLOSED` target | not intercepted; the activation path could run and drive `WAKING → ACTIVE_HASHING`, activating `PENDING → CURRENT` on a closed head | `status(target) ∉ {PENDING, PAUSED}` → `RETURN stale_wake_noop`; miner unchanged |
| Wake for a reassigned range | not intercepted; could activate onto a range now owned by a different `REASSIGNED` lineage | "`target_assignment` is NOT the miner's bound live head (I18b)" → `stale_wake_noop` |
| Wake after a round/template epoch move | not checked at the wake head | `RoundID(target) != RoundID_current OR TemplateID(target) != TemplateID_committed` → `stale_wake_noop` |
| Protection relied upon | (implicitly) the HashWorkEvent G9 guard — which does NOT run for a `WakeCompleteEvent` | the `WakeCompleteEvent`'s OWN guard, explicitly INDEPENDENT of G9 (§0.10 NOTE) |
| Outcome for a stale wake | could produce a second live head / activate a `CLOSED` target (I18a/I18b violation) | `stale_wake_noop` — no transition, no activation, invariants preserved |

The guard is defence-in-depth alongside §2(A) step 1: `LeaseExpiry` cancels the exact wake, and the guard
independently rejects any wake that nonetheless reaches dispatch.

## 5. `CASE PAUSED` — cancellation additions (M3)

`CASE PAUSED` continues to `ASSERT miner_state(holder) = LOW_POWER_LISTEN AND entry_stop_reason(holder) =
VALID_SOLUTION_VERIFIED`, then close the paused head canonically without a wake and re-classify the
holder's parked reason to `ASSIGNMENT_REVOKED` (L4). M3 adds, BEFORE the atomic CLOSE, two explicit
cancellations so no scheduled event can re-activate the miner onto the closed head:

| M3 cancellation in `CASE PAUSED` | Target |
|---|---|
| `CANCEL every scheduled ResumeFromPause for (holder, pause_cause_candidate_id(assignment), pause_cause_propagation_id(assignment))` | the candidate-specific resume that would restore the paused head |
| `CANCEL any scheduled WakeCompleteEvent for (holder, AssignmentID(assignment), assignment_version(assignment))` | any wake targeting the exact paused version |

The subsequent `ATOMICALLY` block then sets `status ← CLOSED`, `custody_status ← expired`,
`termination_reason ← lease_expiry`, clears the pause bookkeeping (`pause_cause_candidate_id`,
`pause_cause_propagation_id`, `retained_actual_frontier`), and sets `entry_stop_reason(holder) ←
ASSIGNMENT_REVOKED`. The common reassign tail then applies exactly as for `CASE PENDING`.

## 6. Independence from the HashWorkEvent G9 guard

The correction is precise about scope: the spec does NOT claim G9 protects `WakeCompleteEvent`.

| Guard | Scope (spec text) | Protects `WakeCompleteEvent`? |
|---|---|---|
| G9 (§0.7b) | "A pending `HashWorkEvent` becomes a no-op (or is cancelled) once its miner is no longer `ACTIVE_HASHING` or its exact assignment version is no longer `CURRENT`." | **No** — a `WakeCompleteEvent` fires while `WAKING`, not `ACTIVE_HASHING`, and legitimately targets a `PENDING`/`PAUSED` (non-`CURRENT`) head; G9's predicate never matches it |
| M3 stale-target guard (§0.10) | "IF `status(target_assignment)` NOT in `{PENDING, PAUSED}` OR round/template epoch moved OR not the miner's bound live head → `RETURN stale_wake_noop`." | **Yes** — this is the `WakeCompleteEvent`'s OWN first step |

The §0.10 NOTE and the §12 `LeaseExpiry` NOTE both state it: "The `WakeCompleteEvent` stale guard (M3,
§0.10) is the independent backstop; the HashWorkEvent G9 guard does NOT protect wakes."

## 7. Argument — I18a/I18b hold throughout

**`CASE PENDING`.** Before the atomic CLOSE the lineage's unique live head is the `PENDING` version `v`
(I18b, one live head in `{PENDING, CURRENT, PAUSED}`; zero `CURRENT`, which I18a permits). The T12
`WAKING → OFFLINE` transition (step 2) changes only `miner_state`, not the lineage head count. The atomic
CLOSE (step 4) drives `PENDING → CLOSED` with NO successor published, leaving ZERO live heads on `v`'s
lineage (I18b); I18a is vacuously satisfied. Because the exact wake was cancelled (step 1) AND the §0.10
guard independently returns `stale_wake_noop` for a `CLOSED` target, no `WakeCompleteEvent` can ever
activate `v` after closure — so no second live head or spurious `CURRENT` is introduced. The reassigned
suffix opens a SEPARATE `REASSIGNED` lineage (fresh head, different `lineage_id`), never a second head on
the closed one.

**`CASE PAUSED`.** Before, the unique live head is `PAUSED` (I18b; zero `CURRENT`). The two cancellations
remove any resume/wake that could re-activate it; the atomic step drives `PAUSED → CLOSED` with no
successor, leaving ZERO live heads. The suffix opens a separate `REASSIGNED` lineage.

**Reassignment gating.** Both the `LeaseExpiry` common tail and `RangeReassign` (§13) assert
`status(source) = CLOSED` — in `RangeReassign` in BOTH `PRECONDITIONS` and `EFFECTS` — so a suffix is
reassigned ONLY after its source lineage head is terminal, never from a live `CURRENT`/`PAUSED`/`PENDING`
head and never from a `SUPERSEDED` renewal head (J7). Coverage stays partitioned (I8a): the preserved
accepted searched prefix plus the reassignable `inactive_unsearched` suffix account for the assigned
domain with no double count; custody/lineage status (I8b) is orthogonal and never an additive coverage
term.

## 8. Pseudocode verification

| Site | Text in `STAGE_01_PROTOCOL_PSEUDOCODE.md` | Verdict |
|---|---|---|
| §12 `CASE PENDING` (1)–(2) | `CANCEL the scheduled WakeCompleteEvent for (holder, AssignmentID(assignment), assignment_version(assignment))` | exact wake cancelled before closure |
| §12 `CASE PENDING` (3) | `IF miner_state(holder) = WAKING AND target_assignment(holder) = assignment: CALL ApplyMinerStateTransition(holder, WAKING, OFFLINE, … reason = lease_expired_while_waking …)` (T12) | `WAKING` holder resolved off `WAKING` |
| §12 `CASE PENDING` (4)–(5) | `PRESERVE accepted searched prefix [range_start, accepted_frontier]`; `ATOMICALLY status ← CLOSED / custody_status ← expired / termination_reason ← lease_expiry` | canonical CLOSE; prefix preserved |
| §12 common reassign tail | `ASSERT status(assignment) = CLOSED`; C4 suffix `[accepted_frontier + 1, range_end]`; `RETURN CALL RangeReassign(… reason = lease_expiry …)` | reassign only a CLOSED source's suffix |
| §12 `CASE PAUSED` | `CANCEL every scheduled ResumeFromPause for (holder, pause_cause_candidate_id, pause_cause_propagation_id)`; `CANCEL any scheduled WakeCompleteEvent for (holder, AssignmentID, assignment_version)` | candidate-specific resume/wake cancelled |
| §0.10 `WakeCompleteEvent` head | `IF status(target_assignment) NOT in {PENDING, PAUSED} OR RoundID/TemplateID moved OR NOT the miner's bound live head: RETURN stale_wake_noop` | stale-target guard runs FIRST |
| §0.10 `WakeCompleteEvent` NOTE | "This guard is independent of the HashWorkEvent G9 guard, which does not protect `WakeCompleteEvent`." | independence stated explicitly |
| §0.7b `HashWorkEvent` / G9 | "A pending `HashWorkEvent` becomes a no-op … once its miner is no longer `ACTIVE_HASHING` or its exact assignment version is no longer `CURRENT`." | G9 scoped to hashing only |
| §0.9 `ApplyMinerStateTransition` | `WAKING → OFFLINE` is the sole owner of the state change (F6); threads the explicit `dispatch_envelope` (M1) | T12 edge via the central hook |
| §13 `RangeReassign` | `status(source_assignment(unsearched_suffix)) = CLOSED` in `PRECONDITIONS` and `ASSERT …` in `EFFECTS` | source must be terminal |
| §0.8 `STRUCTURE Assignment` | `status` enum `{PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}`; `termination_reason` K6 (`lease_expiry`); `J7 CANONICAL TERMINAL STATUS` | `CLOSED`/`expired`/`lease_expiry`; `SUPERSEDED` renewal-only |

No path activates a `CLOSED` target, relies on G9 to guard a wake, reassigns a non-`CLOSED` source, or
writes `SUPERSEDED` on a termination.

## 9. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | A PENDING lease expiry CANCELs the exact pending `WakeCompleteEvent` for `(holder, AssignmentID, assignment_version)` and resolves a `WAKING` holder off `WAKING` (T12, `lease_expired_while_waking`) BEFORE reassignment (§12 `CASE PENDING` (1)–(3)) | **PASS** |
| C2 | `WakeCompleteEvent` cannot activate a `CLOSED` assignment: its FIRST-step stale-target guard returns `stale_wake_noop` when `status(target) ∉ {PENDING, PAUSED}` (or the epoch moved / not the bound live head) (§0.10) | **PASS** |
| C3 | The accepted searched prefix `[range_start, accepted_frontier]` is preserved and ONLY the accepted unsearched suffix `[accepted_frontier + 1, range_end]` is reassigned, ONLY after the source is `CLOSED` — the common tail asserts `status = CLOSED` and `RangeReassign` asserts `status(source) = CLOSED` (§12/§13) | **PASS** |
| C4 | I18a/I18b hold: exactly one live head before each terminating case (`PENDING`/`PAUSED`), zero live heads after CLOSE; the reassigned suffix opens a SEPARATE `REASSIGNED` lineage, never a second head on the closed one | **PASS** |
| C5 | `CASE PAUSED` also CANCELs the candidate-specific `ResumeFromPause` and any `WakeCompleteEvent` for the closed assignment before the atomic CLOSE (§12 `CASE PAUSED`) | **PASS** |
| C6 | The `WakeCompleteEvent` stale-target guard is INDEPENDENT of the HashWorkEvent G9 guard; the spec does NOT claim G9 protects wakes (§0.10 NOTE; §12 `LeaseExpiry` NOTE; G9 scoped to `HashWorkEvent` in §0.7b) | **PASS** |
| C7 | Termination is canonical: `status = CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry` (K6); `SUPERSEDED` stays renewal-only (`RenewAssignment`, F7/G2/J7); no undefined state | **PASS** |
| C8 | §12, §0.10, §0.9, §0.7b, §13, §0.8, and I18a/I18b/I8a all AGREE; A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; any energy change attributable only to reduced active power-time | **PASS** |

## Result

**Result: PENDING LEASE-EXPIRY EXECUTABILITY & WAKE STALE-TARGET GUARD AUDIT (Stage 1M): PASS** —
`LeaseExpiry` (§12) `CASE PENDING` is now executable: it CANCELs the exact pending `WakeCompleteEvent`
for `(holder, AssignmentID, assignment_version)`, resolves a `WAKING` holder off `WAKING` via the legal
T12 edge (`reason = lease_expired_while_waking`) with the exact `dispatch_envelope`, CLOSEs the
un-activated head canonically (`CLOSED`/`expired`/`lease_expiry`, K6), preserves the accepted searched
prefix, and reassigns ONLY the accepted unsearched suffix after the source is `CLOSED` — with the common
tail and `RangeReassign` (§13) both asserting `status(source) = CLOSED`. `CASE PAUSED` additionally
CANCELs the candidate-specific `ResumeFromPause` and any `WakeCompleteEvent` for the closed assignment.
`WakeCompleteEvent` (§0.10) BEGINS with an explicit stale-target guard that returns `stale_wake_noop`
for any target not in `{PENDING, PAUSED}`, whose round/template epoch moved, or that is not the miner's
bound live head — so a wake for a `CLOSED`/superseded/reassigned target CANNOT activate the miner — and
the spec is explicit that this guard is INDEPENDENT of the HashWorkEvent G9 guard, which does NOT protect
wakes. I18a/I18b hold at every observable point (one live head before each terminating case, zero after
CLOSE; the reassigned suffix opens a separate `REASSIGNED` lineage). §12/§0.10/§0.9/§0.7b/§13/§0.8 and
I18a/I18b/I8a all agree, with the A1 baseline 8.420833333 kWh unchanged and no new consensus feature.
