# Stage 1AF — Hashing Result Contract Audit (AF7)

This audit verifies correction **AF7** against the FINAL Stage-1AF normative tree
(`STAGE_01_PROTOCOL_PSEUDOCODE.md` and its companions), inspected only after every normative edit
(AF1–AF9) and every semantic vector (TV273–TV287) was complete. AF7 closes the hashing-result
reporting contract for the event-scheduled hashing chain (G9): `StartHashing` must RETURN explicitly
on every path, `HashWorkEvent`'s continuation must return the exact shape its declared RETURNS union
names, `ScheduleNextHashWork`'s two-arm result must be wrapped by its `HashWorkEvent` caller, and the
`WakeCompleteEvent` caller of `StartHashing` must be reconciled with the disposition it propagates.

The algorithm remains **PoCol**; the mechanism under audit is the idle policy within PoCol; the A1
baseline (`8.420833333 kWh`) is unchanged. This is a documentation-only verification: no executable
source, configuration, DOCX, or PDF was modified, and no experiment was run.

All line anchors below refer to `STAGE_01_PROTOCOL_PSEUDOCODE.md` unless another file is named.

---

## Findings

### Item 1 — `StartHashing` has an explicit RETURN on BOTH paths (no successful fall-through)

`StartHashing` (procedure header at `:3091`) computes `hw` from `ScheduleNextHashWork` (`:3100–3101`),
then RETURNs explicitly on each arm:

- `:3102`  `IF hw = hash_work_seated(event_ref):`
- `:3103`    `RETURN hashing_started(event_ref)`  — explicit success return carrying the seated first-unit `EventRef`.
- `:3104`  `IF hw = hash_work_not_seated(reason):`
- `:3105`    `RETURN hashing_not_started(reason)`  — the horizon (O2) terminal disposition.

There is no code after `:3105` before the RETURNS declaration, so there is no unguarded fall-through
that would leave the declared success result unreachable. The declared union is exactly
`RETURNS: hashing_started(event_ref) | hashing_not_started(reason)` (`:3106`). The AF7 intent note at
`:3096–3099` states every path RETURNs explicitly and records that the AE9 body had left the
`hash_work_seated` case with no RETURN.

### Item 2 — `HashWorkEvent`'s continuation returns `continued(...)`, matching the declared union exactly

The continuation return is `:3181`:

`RETURN continued(CALL ScheduleNextHashWork(RoundContext, MinerID, assignment, from_cursor = cursor))`

The declared RETURNS union is `:3182`:

`RETURNS: hash_work_result (solution | exhausted | continued(hash_work_seated(EventRef) | hash_work_not_seated(reason)) | noop)`

The returned shape `continued(hash_work_seated(EventRef) | hash_work_not_seated(reason))` is the exact
`continued(...)` arm of the union. The body no longer returns a BARE
`hash_work_seated`/`hash_work_not_seated`; the AF7 note at `:3176–3180` records the fix from the AE9
shape mismatch. The other reachable body returns also match their union arms: `noop` at `:3145`
(`RETURN hash_work_noop`), the `solution` arm via `ScheduleSolutionPropagation` at `:3165`, and the
`exhausted` arm via `ExhaustionAdjudicate` at `:3173`.

### Item 3 — `ScheduleNextHashWork` returns the two-arm result; `HashWorkEvent` wraps it in `continued(...)`

`ScheduleNextHashWork` (header `:3108`) returns:

- `:3122`  `RETURN hash_work_seated(event_ref)`  — on `scheduled(event_ref, record)`.
- `:3123`  `RETURN hash_work_not_seated(r)`  — any non-scheduled result (e.g. `post_horizon_event_rejected`).
- `:3124`  `RETURNS: hash_work_seated(EventRef) | hash_work_not_seated(reason)`

`HashWorkEvent`'s continuation wraps this exact result in `continued(...)` at `:3181` (Item 2), and
`StartHashing` branches on the same two arms at `:3102`/`:3104` (Item 1). Both callers consume
`ScheduleNextHashWork`'s declared shape without assuming any other shape.

### Item 4 — The `WakeCompleteEvent` caller of `StartHashing` is reconciled

`WakeCompleteEvent` (header `:1987`) invokes `StartHashing` on its success path:

- `:2016`  `RETURN CALL StartHashing(RoundContext, MinerID, target_assignment)`

so the disposition `WakeCompleteEvent` returns on that path IS `StartHashing`'s result. Its declared
union includes both `StartHashing` arms plus its own two dispositions:

- `:2051`  `RETURNS: hashing_started(event_ref) | hashing_not_started(reason) | stale_wake_noop | activation_failure`

`stale_wake_noop` is returned by the M3 stale-target guard (`:1999`) and `activation_failure` by the
wake-deadline failure path (`:2050`); the reconciliation note is at `:2052–2053` and `:2013–2015`.

### Item 5 — No caller or test vector still expects the old shapes

- **Sole `StartHashing` caller.** The only `CALL StartHashing` site in the normative tree is
  `:2016` (`WakeCompleteEvent`), which propagates the disposition via `RETURN CALL` (Item 4). No other
  caller reads or branches on a `StartHashing` fall-through.
- **No bypass of the `continued(...)` wrapper.** There is no `RETURN CALL HashWorkEvent` anywhere in
  the pseudocode; `HashWorkEvent` is a dispatched handler whose result returns to the event loop, and
  its own continuation goes through the wrapper at `:3181`.
- **Bare-shape branching is confined to the declared contract.** The only `= hash_work_seated` /
  `= hash_work_not_seated` branches in the pseudocode are inside `StartHashing` at `:3102`/`:3104`,
  which branch on `ScheduleNextHashWork`'s DECLARED return (`:3124`) — the intended contract, not a
  stray bare return.
- **Current test vector expects the new shapes.** TV285 (`STAGE_01AF_SEMANTIC_TEST_VECTORS.md:129–137`)
  expects `StartHashing` to RETURN `hashing_started(event_ref)` explicitly ("no successful fall-through
  without a RETURN") and `HashWorkEvent`'s continuation to RETURN `continued(hash_work_seated(EventRef))`
  / `continued(hash_work_not_seated(reason))`, "never a bare `hash_work_seated`."
- **Old shapes survive only as frozen, superseded record.** The AE9 old shapes are described only in
  the frozen Stage-1AA…AE lettered artifacts and are explicitly superseded by
  `STAGE_01AF_SUPERSESSION_REGISTER.md:58–69` (item 4); the AF7 correction is recorded in
  `STAGE_01AF_CORRECTION_REPORT.md:44–46`. These historical records are not callers or live test
  vectors of the final normative tree.

---

## Verification table

| # | Claim | Primary line anchors | Result |
|---|-------|----------------------|--------|
| 1 | `StartHashing` RETURNs explicitly on both paths; no successful fall-through; declared `hashing_started(event_ref) \| hashing_not_started(reason)` | `:3102–3106` (seated→`:3103`, not_seated→`:3105`, RETURNS `:3106`) | PASS |
| 2 | `HashWorkEvent` continuation RETURNs `continued(CALL ScheduleNextHashWork(...))`, matching the declared union exactly; no bare arm | `:3181` (return), `:3182` (RETURNS union) | PASS |
| 3 | `ScheduleNextHashWork` returns `hash_work_seated(EventRef) \| hash_work_not_seated(reason)`; `HashWorkEvent` wraps it in `continued(...)` | `:3122–3124` (returns), `:3181` (wrap) | PASS |
| 4 | `WakeCompleteEvent` caller `RETURN CALL StartHashing(...)` reconciled; RETURNS union includes both `StartHashing` arms plus `stale_wake_noop \| activation_failure` | `:2016` (call), `:2051` (RETURNS), `:1999`/`:2050` (own arms) | PASS |
| 5 | No caller or test vector still expects the old shapes (no stray bare returns) | Sole caller `:2016`; no `RETURN CALL HashWorkEvent`; branches confined to `:3102`/`:3104`; TV285 `STAGE_01AF_SEMANTIC_TEST_VECTORS.md:129–137`; old shapes frozen at `STAGE_01AF_SUPERSESSION_REGISTER.md:58–69` | PASS |

---

## Overall verdict

**PASS.** Correction AF7 is fully realised in the final Stage-1AF normative tree. `StartHashing`
RETURNs `hashing_started(event_ref)` / `hashing_not_started(reason)` explicitly with no successful
fall-through; `HashWorkEvent`'s continuation returns `continued(...)` matching its declared
`hash_work_result` union exactly; `ScheduleNextHashWork`'s two-arm result is consumed only through that
wrapper and through `StartHashing`'s explicit branches; and the `WakeCompleteEvent` caller is reconciled
with a RETURNS union that admits both propagated arms plus `stale_wake_noop | activation_failure`. No
live caller or test vector expects the old bare shapes. The algorithm remains PoCol, the idle policy
within PoCol is unchanged, and the A1 baseline (`8.420833333 kWh`) is preserved. No defects were found.
