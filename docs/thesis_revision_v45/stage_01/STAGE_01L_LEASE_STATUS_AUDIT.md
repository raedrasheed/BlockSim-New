# Stage 1L — Lease Status-Aware Expiry Audit (L4)

Audits correction **L4**: `LeaseExpiry` is now **status-aware**. It branches on the CANONICAL
`status` (§0.8/J7) of the EXACT immutable version whose lease expired — NOT on `miner_state` alone —
so each of the five assignment statuses has ONE explicit, terminal-correct disposition, a lease event
for an already-terminal version is a stale no-op, and `RangeReassign` is reached ONLY after the source
version is `CLOSED`. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §12 `LeaseExpiry` (the
`SWITCH status(assignment)` with four cases plus the common reassign tail), §12 `RenewAssignment`
(F7 same-range renewal: old → `SUPERSEDED`, new → `CURRENT`), §7 `EnterLowPowerListen` (the single
canonical closer, `CASE ASSIGNMENT_REVOKED`, K6/H8), §13 `RangeReassign` (the new
`status(source_assignment(unsearched_suffix)) = CLOSED` assertion in both `PRECONDITIONS` and
`EFFECTS`), §0.8 `STRUCTURE Assignment` (the `status` enum `{PENDING, CURRENT, PAUSED, SUPERSEDED,
CLOSED}`, the `J7 CANONICAL TERMINAL STATUS` note, and the K6 `termination_reason` field), and §0.10
`WakeCompleteEvent` (the status-aware wake-failure handling, for comparison); and to
`STAGE_01_INVARIANT_CATALOGUE.md` I18a/I18b (assignment-lineage version invariants, G2) and I8a
(coverage-state partition). This is a specification act on **PoCol** with the idle policy within PoCol
enabled — not a claim of implementation, enforcement, security, fairness, energy, or any derived
property. No new consensus feature is introduced; the eight miner states and the assignment schema are
unchanged, and the A1 baseline (8.420833333 kWh) is untouched — any energy difference is attributable
ONLY to reduced active power-time, and no property is asserted at Stage 1.

## 1. The corrected-away problem (status-blind lease handling)

A `LeaseExpiry` that dispositions from `miner_state` alone conflates distinct assignment states. The
version whose lease elapses may be `CURRENT` (the holder is `ACTIVE_HASHING`), but by the immutable
versioning of F7/G2 it may equally be `SUPERSEDED` (the lineage was renewed onto a new `CURRENT` that
carries its OWN lease), `CLOSED` (already terminated), `PAUSED` (a PATH-B head, holder in
`LOW_POWER_LISTEN` / `VALID_SOLUTION_VERIFIED`), or `PENDING` (bound but not yet activated; the
version was never `CURRENT`). A `miner_state`-only reading assumes an `ACTIVE_HASHING`-on-`CURRENT`
disposition for all of these. That risks: (a) acting on an already-terminal version (`SUPERSEDED` /
`CLOSED`) that holds no live head; (b) routing a `PAUSED` head through a wake it never needs; (c)
mishandling a `PENDING` head that has no `ACTIVE_HASHING` boundary to leave; and (d) reaching
`RangeReassign` from a source that is not yet `CLOSED`, defeating the I18a/I18b head-count reasoning.

## 2. The correction (status-aware SWITCH)

L4 replaces the status-blind disposition with `SWITCH status(assignment)` over the exact expiring
version (§12). Four cases plus a common reassign tail:

- **`CASE SUPERSEDED OR CLOSED`** — the version is ALREADY terminal. `SUPERSEDED` was renewed onto a
  new `CURRENT` on the same lineage (which carries its own lease); `CLOSED` was terminated. The
  lease-expiry event is stale: its window is moot and it holds no live head. `RETURN
  lease_expiry_noop_terminal(status(assignment))` — I18a/I18b untouched.
- **`CASE CURRENT`** — decide renewal FIRST (E9/F7). If the holder is `ACTIVE_HASHING`, wishes to
  continue, and policy allows, `RETURN renewed(CALL RenewAssignment(...))` — old → `SUPERSEDED`, new
  → `CURRENT`, SAME range, retained progress/provenance, NO wake, and NEVER reassigned. Otherwise
  (expiry without renewal) the single closer `EnterLowPowerListen` performs the canonical CLOSE
  (`status → CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry`, K6) via the
  legal revocation edge T27, moving the miner off `ACTIVE_HASHING`; control then falls through to the
  common reassign tail.
- **`CASE PAUSED`** — the PATH-B paused head is the lineage's unique live head. After asserting the
  holder is `LOW_POWER_LISTEN` with `entry_stop_reason = VALID_SOLUTION_VERIFIED`, `LeaseExpiry`
  terminates it canonically in ONE atomic step (`status → CLOSED`, `custody_status = expired`,
  `termination_reason = lease_expiry`) WITHOUT a wake, clears the pause bookkeeping
  (`pause_cause_candidate_id`, `pause_cause_propagation_id`, `retained_actual_frontier`), and
  re-classifies the holder's parked `entry_stop_reason` to `ASSIGNMENT_REVOKED`. No second live head;
  `SUPERSEDED` is never used. Falls through to the common reassign tail.
- **`CASE PENDING`** — the bound-but-not-activated head is CLOSED canonically in one atomic step
  (`CLOSED` / `expired` / `lease_expiry`). If the holder is `WAKING` for THIS version, its later
  `WakeCompleteEvent` finds no live head and self-cancels under the G9 stale guard. Zero live heads
  after. Falls through to the common reassign tail.
- **COMMON REASSIGN TAIL** (reached ONLY for `CURRENT`-without-renewal / `PAUSED` / `PENDING`) —
  `ASSERT status(assignment) = CLOSED`, then reassign ONLY the accepted unsearched suffix
  `[accepted_frontier + 1, range_end]` (C4; whole range if no accepted positions exist; nothing if
  `accepted_frontier = range_end`) via `RangeReassign(... reason = lease_expiry ...)`. The searched
  prefix is never reassigned.

`RangeReassign` (§13) now ASSERTS `status(source_assignment(unsearched_suffix)) = CLOSED` in BOTH its
`PRECONDITIONS` and its `EFFECTS`, so a suffix is reassigned ONLY after its source lineage head reached
`CLOSED` — never from a live `CURRENT`/`PAUSED`/`PENDING` head, and never from a `SUPERSEDED` renewal
head (J7).

## 3. Per-status disposition table

| `status(assignment)` | Disposition in `LeaseExpiry` (§12) | Live heads before | Live heads after | Who CLOSEs |
|---|---|---|---|---|
| `SUPERSEDED` | stale no-op → `RETURN lease_expiry_noop_terminal`; the lineage's live head is a DIFFERENT `CURRENT` version with its own lease | 1 (the separate `CURRENT`; the expiring `SUPERSEDED` version is not it) | 1, unchanged (no-op) | nobody — already terminal |
| `CLOSED` | stale no-op → `RETURN lease_expiry_noop_terminal`; lineage already terminated | 0 (lineage already `CLOSED`) | 0, unchanged (no-op) | nobody — already terminal |
| `CURRENT`, renews | `RenewAssignment` (F7): old → `SUPERSEDED`, new → `CURRENT`, SAME range; `RETURN renewed`; never reassigned, never WAKING | 1 (the `CURRENT` head) | 1 (the new `CURRENT` head) | nobody terminates — renewal, not termination |
| `CURRENT`, no renewal | `EnterLowPowerListen` (T27, `ASSIGNMENT_REVOKED`, `expired`/`lease_expiry`) → `CLOSED`, off `ACTIVE_HASHING`; then reassign suffix | 1 (the `CURRENT` head) | 0 on this lineage (`CLOSED`); suffix opens a SEPARATE `REASSIGNED` lineage | `EnterLowPowerListen` (single closer, §7, K6/H8) |
| `PAUSED` | inline atomic CLOSE (`CLOSED`/`expired`/`lease_expiry`) WITHOUT a wake; clear pause bookkeeping; holder `entry_stop_reason → ASSIGNMENT_REVOKED`; then reassign suffix | 1 (the `PAUSED` head) | 0 (`CLOSED`); suffix opens a separate `REASSIGNED` lineage | `LeaseExpiry` inline atomic step (§12) |
| `PENDING` | inline atomic CLOSE (`CLOSED`/`expired`/`lease_expiry`); pending wake self-cancels (G9); then reassign suffix | 1 (the `PENDING` head) | 0 (`CLOSED`); suffix opens a separate `REASSIGNED` lineage | `LeaseExpiry` inline atomic step (§12) |

For `SUPERSEDED`/`CLOSED` and the two renewal columns, `count(CURRENT) <= 1` per lineage (I18a) holds
trivially; for `PAUSED`/`PENDING` the live head carries zero `CURRENT`, which I18b explicitly permits.

## 4. Who CLOSEs, and the common reassign tail

- The `CURRENT`-without-renewal path delegates the CLOSE to the SINGLE closer `EnterLowPowerListen`
  (§7, `CASE ASSIGNMENT_REVOKED`), which — carrying `custody_on_close = expired`, `termination_reason
  = lease_expiry` — sets `status → CLOSED`, `custody_status = expired`, skips the `revocation_reason`
  write (guarded by `custody_on_close = revoked`, so it stays `null`), sets `termination_reason =
  lease_expiry`, and takes the miner off `ACTIVE_HASHING` through the legal T27 edge. `LeaseExpiry`
  never mutates `status` directly on this path.
- The `PAUSED` and `PENDING` paths do NOT call `EnterLowPowerListen`: there is no `ACTIVE_HASHING`
  exit boundary to cross (the `PAUSED` holder is already `LOW_POWER_LISTEN`; the `PENDING` head was
  never activated). `LeaseExpiry` performs the canonical CLOSE inline in its OWN atomic step
  (`CLOSED`/`expired`/`lease_expiry`), which is exactly the K6 terminal classification the single
  closer would apply. No wake is issued.
- The `SUPERSEDED`/`CLOSED` paths CLOSE nothing — they `RETURN` before the tail.
- The common reassign tail `ASSERT status(assignment) = CLOSED` before computing the C4 suffix and
  calling `RangeReassign`, which itself re-asserts `status(source) = CLOSED`. Reassignment therefore
  reaches a source ONLY after it is terminal, on both the caller and callee sides.

## 5. Comparison — `WakeCompleteEvent` status-aware wake failure (§0.10)

L4 gives `LeaseExpiry` the same status-aware discipline `WakeCompleteEvent` already applies on wake
failure (G4): both `SWITCH status(target_assignment)` rather than reading `miner_state` alone, so a
`PAUSED` head is never handled by a `PENDING`-only rule. In `WakeCompleteEvent`, `CASE PENDING`
preserves the accepted searched prefix and CLOSEs the un-activated `PENDING` head (`custody =
abandoned`), while `CASE PAUSED` preserves all three frontiers, CLOSEs the resumed head (disposition
`resume_wake_failed`), and clears the candidate pause fields — reassigning only the accepted
unsearched suffix, never the whole range. The dispositions differ only in their CAUSE: wake failure
CLOSEs as `abandoned`, whereas lease expiry CLOSEs as `expired` with `termination_reason =
lease_expiry`. In both procedures the terminal status is `CLOSED` and `SUPERSEDED` is never used.

## 6. Argument — I18a/I18b hold throughout

**`SUPERSEDED`/`CLOSED` (stale no-op).** The expiring version is not a live head. A `SUPERSEDED`
version's lineage already has its unique live head on the new `CURRENT` (I18b) with `count(CURRENT) =
1` (I18a); a `CLOSED` lineage has ZERO live heads (I18b). The no-op mutates nothing, so both invariants
are preserved by construction.

**`CURRENT`, renews.** `RenewAssignment` (F7) linearises the swap atomically at `renewal_time`: old →
`SUPERSEDED` and new → `CURRENT` in one step, so no observer sees two `CURRENT` versions (I18a) and the
lineage stays OPEN with exactly one live head (I18b). Nothing is terminated or reassigned.

**`CURRENT`, no renewal.** Before the atomic step the live head is the one `CURRENT` (I18a: exactly
one; I18b: one live head). `EnterLowPowerListen` transitions `CURRENT → CLOSED` in one linearised step
with NO successor published, so no observer sees two `CURRENT` versions and none sees an undeclared
state. After, the lineage is `CLOSED` with ZERO live heads (I18b); I18a is vacuously satisfied. The
reassigned suffix opens a SEPARATE `REASSIGNED` lineage (fresh head on a different `lineage_id`), never
a second head on the closed one.

**`PAUSED`.** Before, the unique live head is `PAUSED` (I18b; zero `CURRENT`, which I18a permits). The
inline atomic step drives `PAUSED → CLOSED` with no successor, leaving ZERO live heads (I18b). No wake
and no second head are introduced; the suffix opens a separate `REASSIGNED` lineage.

**`PENDING`.** Before, the unique live head is `PENDING` (I18b; zero `CURRENT`). The inline atomic step
drives `PENDING → CLOSED`, leaving ZERO live heads. A pending `WakeCompleteEvent` for this version
self-cancels under G9 (its exact version is no longer a live head), so no `CURRENT` is ever activated
after closure. The suffix opens a separate `REASSIGNED` lineage.

Across every case, coverage stays partitioned (I8a): the preserved accepted searched prefix plus the
reassignable `inactive_unsearched` suffix account for the assigned domain with no double count, and
custody/lineage status (I8b) is orthogonal and never an additive coverage term.

## 7. Pseudocode verification

| Site | Text in `STAGE_01_PROTOCOL_PSEUDOCODE.md` | Verdict |
|---|---|---|
| §12 `LeaseExpiry` | `SWITCH status(assignment)` with `CASE SUPERSEDED OR CLOSED` / `CASE CURRENT` / `CASE PAUSED` / `CASE PENDING`, then a common reassign tail | one disposition per status |
| §12 `CASE SUPERSEDED OR CLOSED` | `RETURN lease_expiry_noop_terminal(status(assignment))` — "I18a/I18b untouched" | terminal version → stale no-op |
| §12 `CASE CURRENT` | renewal decided first (`RETURN renewed(CALL RenewAssignment...)`); else `CALL EnterLowPowerListen(... custody_on_close = expired, termination_reason = lease_expiry)` | renew-or-CLOSE; single closer |
| §12 `CASE PAUSED` | `ASSERT miner_state(holder) = LOW_POWER_LISTEN AND entry_stop_reason(holder) = VALID_SOLUTION_VERIFIED`; `ATOMICALLY` CLOSE + clear pause fields + `entry_stop_reason(holder) <- ASSIGNMENT_REVOKED` | CLOSE without wake; no `SUPERSEDED` |
| §12 `CASE PENDING` | `ATOMICALLY` `status <- CLOSED` / `custody_status <- expired` / `termination_reason <- lease_expiry`; wake self-cancels (G9) | un-activated head CLOSED |
| §12 common reassign tail | `ASSERT status(assignment) = CLOSED`; C4 suffix only; `RETURN CALL RangeReassign(... reason = lease_expiry ...)` | reassign only a CLOSED source's suffix |
| §12 `RenewAssignment` | old → `SUPERSEDED`, new → `CURRENT`, SAME lineage/range; `ASSERT exactly one CURRENT`; NO WAKING | `SUPERSEDED` renewal-only |
| §13 `RangeReassign` `PRECONDITIONS` | `status(source_assignment(unsearched_suffix)) = CLOSED` | source must be terminal |
| §13 `RangeReassign` `EFFECTS` | `ASSERT status(source_assignment(unsearched_suffix)) = CLOSED` | asserted again at effect |
| §7 `EnterLowPowerListen` `CASE ASSIGNMENT_REVOKED` | `ATOMICALLY` `status <- CLOSED`; `custody_status <- (custody_on_close = expired ? expired : revoked)`; `revocation_reason` guarded by `custody_on_close = revoked`; `termination_reason <- termination_reason` | single canonical closer, K6 |
| §0.8 `STRUCTURE Assignment` | `status` enum `{PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}`; `J7 CANONICAL TERMINAL STATUS`; `termination_reason` K6 field | no `INVALID`; `SUPERSEDED` renewal-only |

No path writes `SUPERSEDED` on a termination, invents an undeclared state, or calls `RangeReassign`
against a non-`CLOSED` source.

## 8. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `LeaseExpiry` has ONE explicit, terminal-correct disposition per `status` — `SUPERSEDED`/`CLOSED`/`CURRENT`/`PAUSED`/`PENDING` (§12 `SWITCH status(assignment)`) | **PASS** |
| C2 | A lease event for an already-terminal version (`SUPERSEDED` or `CLOSED`) is a stale no-op (`lease_expiry_noop_terminal`), mutating nothing | **PASS** |
| C3 | `CURRENT` decides renewal FIRST (F7 old → `SUPERSEDED`, new → `CURRENT`, never reassigned/WAKING); otherwise CLOSEs via the single closer `EnterLowPowerListen` (`expired`/`lease_expiry`, T27) | **PASS** |
| C4 | `PAUSED` is CLOSED canonically WITHOUT a wake; pause bookkeeping cleared; holder `entry_stop_reason → ASSIGNMENT_REVOKED`; `SUPERSEDED` never used | **PASS** |
| C5 | `PENDING` is CLOSED canonically; a pending wake self-cancels (G9); zero live heads after | **PASS** |
| C6 | Every reassignment CLOSEs the source FIRST — common tail `ASSERT status(assignment) = CLOSED`, and `RangeReassign` asserts `status(source) = CLOSED` in both `PRECONDITIONS` and `EFFECTS` | **PASS** |
| C7 | Only the accepted unsearched suffix `[accepted_frontier + 1, range_end]` is reassigned (C4/I8a); the searched prefix is preserved; `reason = lease_expiry` | **PASS** |
| C8 | `SUPERSEDED` remains renewal-only (`RenewAssignment`, F7/G2/J7); no termination path writes it | **PASS** |
| C9 | I18a/I18b hold at every observable point — one live head before each terminating case, zero after CLOSE; renewal keeps exactly one; the terminal no-op leaves the count unchanged | **PASS** |
| C10 | §12, §7, §13, §0.8, and I18a/I18b/I8a all AGREE; A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; any energy change attributable only to reduced active power-time | **PASS** |

## Result

**Result: LEASE STATUS-AWARE EXPIRY AUDIT (Stage 1L): PASS** — `LeaseExpiry` (§12) branches on the
canonical `status` of the exact expiring version (L4), giving one explicit, terminal-correct
disposition per status: `SUPERSEDED`/`CLOSED` → stale no-op (`lease_expiry_noop_terminal`); `CURRENT`
→ renew first (F7, `SUPERSEDED` + new `CURRENT`, never reassigned) or, on expiry without renewal, CLOSE
via the single closer `EnterLowPowerListen` (`CLOSED`/`expired`/`lease_expiry`, T27) then reassign;
`PAUSED` → inline atomic CLOSE without a wake, pause bookkeeping cleared and the holder's parked reason
set to `ASSIGNMENT_REVOKED`, then reassign; `PENDING` → inline atomic CLOSE with the pending wake
self-cancelling (G9), then reassign. Every reassignment CLOSEs its source first, and `RangeReassign`
(§13) asserts `status(source) = CLOSED` in both `PRECONDITIONS` and `EFFECTS`; `SUPERSEDED` stays
renewal-only (`RenewAssignment`, F7/G2/J7); and I18a/I18b hold at every observable point (one live head
before each terminating case, zero after CLOSE, exactly one preserved across renewal, unchanged on the
terminal no-op). §12/§7/§13/§0.8 and I18a/I18b/I8a all agree, with the A1 baseline 8.420833333 kWh
unchanged and no new consensus feature.
