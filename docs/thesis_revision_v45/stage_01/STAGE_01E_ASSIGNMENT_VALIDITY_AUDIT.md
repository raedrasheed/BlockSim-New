# Stage 1E — Assignment-Validity Audit

Audits how an assignment's validity is established, preserved, and consumed across the corrected
procedures, with emphasis on the discovery snapshot (E1/E2), reserve activation (E4), and lease
renewal (E9). Verified by procedure-call-graph analysis over `STAGE_01_PROTOCOL_PSEUDOCODE.md`,
not string search alone.

## 1. Assignment lifecycle (status field)

An assignment's `status` is one of `{PENDING, CURRENT, PAUSED, CLOSED}` (invalidated ⇒ not CURRENT).
Every legal producer of each status:

| Status | Set by | Precondition |
|--------|--------|--------------|
| `PENDING` | `RangeAssign`, `ReserveActivate` (E4), `RangeReassign`, `TemplateRefresh` | a range is bound to a holder before waking |
| `CURRENT` | `WakeComplete` (T5), `LeaseExpiry` renewal (E9, stays CURRENT), `ResumeFromPause` (D5) | successful wake, or same-range renewal, or resume from `actual_frontier` |
| `PAUSED` | `EnterLowPowerListen(VALID_SOLUTION_VERIFIED)` (PATH B) | verified valid-solution stop; `actual_frontier` retained |
| `CLOSED` | `EnterLowPowerListen(RANGE_EXHAUSTED/ROUND_*)`, `CloseRoundAssignments`, `CloseTemplateAssignments`, `LeaseExpiry` expiry | exhaustion, revocation, round or template closure |

**Property A1 — PENDING never skips WAKING.** No procedure sets `CURRENT` directly from `PENDING`
outside `WakeComplete` (the T5 owner). `ReserveActivate` (E4), `RangeAssign`, `RangeReassign`, and
`TemplateRefresh` all create PENDING and reach CURRENT only through `WakeComplete`. **PASS.**

**Property A2 — a failed wake yields no CURRENT assignment.** `WakeComplete` on
`wake_latency > wake_deadline` records `reserve_wake_failure`, moves the miner OFFLINE (T12), and
returns `activation_failure`; `ReserveActivate` then releases the bound range
(`inactive_unsearched`, `custody_status <- abandoned`). No PENDING is promoted. **PASS** (E4).

## 2. Discovery snapshot (E1/E2)

**Property S1 — the snapshot is immutable and CURRENT at discovery.**
`CreateSolutionEligibilitySnapshot` asserts `assignment_status_at_discovery = CURRENT` and records
the snapshot immutably; later PAUSING of the assignment does not mutate it. **PASS.**

**Property S2 — validation is against the snapshot, not the later assignment state.**
`ValidateCandidate(RoundContext, certificate, snapshot)` requires: (i) the certificate binds the
snapshot (RoundID/TemplateID/AssignmentID/assignment_version/nonce/candidate_hash/target); (ii)
`snapshot.assignment_status_at_discovery = CURRENT`; (iii) the assignment version was not revoked
before `snapshot.discovery_time`; (iv) `snapshot.range_start ≤ nonce ≤ snapshot.range_end` (I2);
(v) bound RoundID = current, TemplateID = committed (I3); (vi) target satisfied under fixed D;
(vii) signature valid. It does **NOT** require the finder's assignment to be CURRENT at arrival.
**PASS.** (Exercised by TV18.)

**Property S3 — one canonical predicate for finder, recipients, and acceptance.** The three call
sites `SelfValidateFoundSolution`, `EarlyStopVerify`, and `AcceptanceTimestampBatch` all invoke the
SAME `ValidateCandidate`. A finder self-validates the SIGNED certificate (E2), not an unsigned
candidate. **PASS.** (Exercised by TV20.)

**Property S4 — a PAUSED assignment authenticates its solution but not new hashing.** A miner in
`LOW_POWER_LISTEN` (PAUSED) cannot run `ActiveHashing` (precondition `miner_state = ACTIVE_HASHING`);
new scored search requires `ResumeFromPause → WAKING → ACTIVE_HASHING`. Yet `ValidateCandidate`
against its snapshot still returns `ok`. **PASS.** (Exercised by TV19.)

## 3. Lease renewal vs reassignment (E5/E9)

**Property L1 — renewal preserves a valid CURRENT assignment.** `LeaseExpiry` decides renewal
BEFORE any invalidation. On renewal: same range and holder; fresh
`AssignmentID`/`assignment_version`; extended lease window; `custody_status <- renewed`; retained
`actual_frontier`/`accepted_frontier`/`reported_frontier`/provenance; status stays CURRENT; no
WAKING, no `RangeReassign`. **PASS.**

**Property L2 — expiry without renewal invalidates and reassigns only the suffix.** Only after the
renewal decision is negative does `LeaseExpiry` INVALIDATE the assignment,
`EnterLowPowerListen(ASSIGNMENT_REVOKED)` (T27), and `RangeReassign` the accepted unsearched suffix
`[accepted_frontier+1, range_end]` (never the searched prefix). **PASS.** (Exercised by TV27.)

**Property L3 — a changed range is never a renewal (T6 removed).** There is no `ACTIVE_HASHING →
ACTIVE_HASHING` self-loop; acquiring a different range is a reassignment through WAKING. **PASS**
(E5). (Exercised by TV23.)

## 4. Overlap (I1/I10) preserved through the new PENDING flow

Every producer of a PENDING range performs the disjointness guard before binding: `RangeAssign`,
`ReserveActivate` (E4 — overlap guard + `custody_status != completed` + `coverage_state != searched`),
`RangeReassign`, and `TemplateRefresh` (fresh domain). `WakeComplete` re-validates I1/RoundID/
TemplateID at T5. **PASS.**

## Result

**ASSIGNMENT-VALIDITY AUDIT: PASS.** A discovered solution is validated against the immutable
discovery snapshot and survives the finder pausing (E1/E2); reserve activation always creates and
ledgers a PENDING assignment and reaches CURRENT only on a successful wake (E4); lease renewal
preserves a valid CURRENT assignment on the same range while expiry-without-renewal reassigns only
the accepted unsearched suffix (E5/E9); and I1/I10 disjointness holds across the corrected flow.
