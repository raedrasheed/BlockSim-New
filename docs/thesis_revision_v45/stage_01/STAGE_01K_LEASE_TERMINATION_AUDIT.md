# Stage 1K — Lease-Termination Audit (K6)

Audits correction **K6**: lease expiry WITHOUT renewal has NO undefined `INVALIDATE assignment` state.
The expiring `CURRENT` version is terminated by the ONE canonical atomic terminal operation — the
single closer `EnterLowPowerListen` (H8/J7) — as `status = CLOSED`, `custody_status = expired`,
`termination_reason = lease_expiry`. Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §12 `LeaseExpiry` (the
removed `INVALIDATE`; the `EnterLowPowerListen` call carrying `custody_on_close = expired` /
`termination_reason = lease_expiry`), §7 `EnterLowPowerListen` (INPUTS `custody_on_close` /
`termination_reason`; `CASE ASSIGNMENT_REVOKED` atomic close), §0.8 `STRUCTURE Assignment` (`status`
enum, the new declared `termination_reason` field, the `J7 CANONICAL TERMINAL STATUS` note), and §13
`RangeReassign`; to `STAGE_01_INVARIANT_CATALOGUE.md` I18a/I18b (assignment-lineage version invariants,
G2) and I8a (coverage-state partition); and to `STAGE_01K_SEMANTIC_TEST_VECTORS.md` TV89. This is a
specification act on **PoCol** with the idle policy within PoCol enabled — not a claim of
implementation, enforcement, security, fairness, energy, or any derived property. No new consensus
feature is introduced; the eight miner states and the assignment schema are unchanged, and the A1
baseline (8.420833333 kWh) is untouched.

## 1. The corrected-away problem

An earlier reading of `LeaseExpiry` performed an `INVALIDATE assignment` step. No such state field
exists: the §0.8 `status` enum is `{PENDING, CURRENT, PAUSED, SUPERSEDED, CLOSED}` — there is no
`INVALID` member, and no `custody_status`/`termination_reason` value names one. An `INVALIDATE` verb
therefore drove a version into an undeclared, unauditable state, defeating the I18a/I18b head-count
reasoning (a lineage that is neither renewed nor cleanly CLOSED) and leaving the lease-expiry cause
untyped.

## 2. The correction

K6 removes the undeclared state. There is **NO** `INVALID` status. Lease expiry without renewal is a
termination, and a termination has exactly ONE canonical disposition (J7): `CLOSED`.

- **Single closer, atomic step.** The expiring `CURRENT` version is TERMINATED by the canonical atomic
  terminal operation carried out by the SINGLE closer `EnterLowPowerListen` (§7, H8/J7): `status ->
  CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry`. `termination_reason` is a
  newly declared §0.8 Assignment field (K6), set ONLY when `status = CLOSED`.
- **Lease-expiry classification (not revocation).** `LeaseExpiry` passes `custody_on_close = expired`
  and `termination_reason = lease_expiry`, so the close is classified `expired` / `lease_expiry`, NOT
  `revoked`. Because `custody_on_close != revoked`, `revocation_reason` stays `null` — lease expiry is
  not a revocation.
- **SUPERSEDED stays renewal-only.** `SUPERSEDED` is written EXCLUSIVELY by atomic same-range renewal
  (`RenewAssignment`, §12, F7/G2), which publishes a new `CURRENT` on the SAME `lineage_id` in the
  same step. Lease expiry without renewal publishes NO successor, so it never writes `SUPERSEDED`.
- **Still CURRENT at the call.** The assignment is still `CURRENT` when `EnterLowPowerListen` is
  invoked, so its precondition `status(assignment_ref) in {CURRENT, PAUSED}` (§7, H8) is met; the
  `CLOSE` happens INSIDE `EnterLowPowerListen`'s atomic step, not in `LeaseExpiry`.
- **Coverage handling.** The accepted searched prefix is preserved; ONLY the accepted unsearched
  suffix `[accepted_frontier + 1, range_end]` is exposed (C4) and passed to `RangeReassign`
  (§13, `reason = lease_expiry`). I18a/I18b hold at every observable point.

## 3. Mechanism (the idle policy within PoCol)

`LeaseExpiry` (§12) decides renewal FIRST (E9). If the holder renews, control returns via
`RenewAssignment` (old → `SUPERSEDED`, new → `CURRENT`, same range) and nothing is terminated or
reassigned. On expiry WITHOUT renewal, with the holder `ACTIVE_HASHING`, `LeaseExpiry` routes the
holder off `ACTIVE_HASHING` through the legal revocation edge (T27):

```
CALL EnterLowPowerListen(RoundContext, holder, stop_reason = ASSIGNMENT_REVOKED,
                         assignment_ref = assignment,               # H8: exact expiring CURRENT version
                         custody_on_close = expired, termination_reason = lease_expiry)   # K6
```

Inside §7 `CASE ASSIGNMENT_REVOKED`, the atomic step (linearised at `now`) performs:
`SET status(assignment_ref) <- CLOSED`; `SET custody_status(range(assignment_ref)) <- (custody_on_close
= expired ? expired : revoked)` — here `expired`; the `revocation_reason` write is guarded by
`IF custody_on_close = revoked` and is therefore SKIPPED (stays `null`); `SET
termination_reason(assignment_ref) <- termination_reason` — here `lease_expiry`. The accepted searched
prefix is preserved and the accepted unsearched suffix is marked `inactive_unsearched / reassignable`.
Control returns to `LeaseExpiry`, which computes `reassignable_suffix` and CALLs `RangeReassign`
(§13). The single closer owns the CLOSE; `LeaseExpiry` never mutates `status` directly.

## 4. Lease-expiry termination fields (contrasted with SUPERSEDED renewal-only)

| §0.8 field | Lease expiry WITHOUT renewal | Same-range renewal (contrast) |
|---|---|---|
| `status` | `CLOSED` (set inside §7 `CASE ASSIGNMENT_REVOKED`) | old → `SUPERSEDED`, new → `CURRENT` — `SUPERSEDED` is renewal-ONLY |
| `custody_status` | `expired` (`custody_on_close = expired`) | new `CURRENT` on the same range; not an expiry close |
| `termination_reason` | `lease_expiry` (set ONLY when `status = CLOSED`) | `null` — a renewal is not a CLOSE, so no `termination_reason` |
| `revocation_reason` | `null` — lease expiry is NOT a revocation (write guarded by `custody_on_close = revoked`) | `null` |
| successor / live head | NONE published; lineage CLOSED, ZERO live heads (I18b) | new `CURRENT` published; lineage stays OPEN, one live head (I18b) |

Contrast with a plain revocation (also §7 `CASE ASSIGNMENT_REVOKED`, default classification):
`custody_on_close = revoked` → `custody_status = revoked`, `revocation_reason = assignment_revoked`,
`termination_reason = assignment_revoked`. Same closer, same `CLOSED` status; only the K6
classification (`expired`/`lease_expiry` vs `revoked`/`assignment_revoked`) differs — and neither path
writes `SUPERSEDED` or invents an `INVALID` state.

## 5. Argument: I18a/I18b hold throughout

**Before the atomic step.** The holder is `ACTIVE_HASHING` on the expiring version, whose `status =
CURRENT`. By I18a there is at most one `CURRENT` per `lineage_id`; here EXACTLY one — the live head is
that `CURRENT` (I18b, one live head in `{PENDING, CURRENT, PAUSED}`). The §7 precondition
`status(assignment_ref) in {CURRENT, PAUSED}` is satisfied.

**At the atomic step.** `status -> CLOSED` in ONE linearised step; no successor version is published
(a termination, not a renewal), so no observer sees two `CURRENT` versions or an `INVALID` state — the
transition is `CURRENT -> CLOSED` directly.

**After the atomic step.** The lineage is CLOSED with ZERO live heads (I18b); no
`PENDING`/`CURRENT`/`PAUSED` head remains, and I18a is vacuously satisfied (zero `CURRENT` is legal).
The reassigned suffix opens a SEPARATE `REASSIGNED` lineage via `RangeReassign` — a fresh live head on
a different `lineage_id`, never a second head on the closed one. Coverage stays partitioned (I8a): the
preserved accepted searched prefix plus the reassignable `inactive_unsearched` suffix account for the
domain with no double count.

## 6. Pseudocode verification

| Site | Text in `STAGE_01_PROTOCOL_PSEUDOCODE.md` | Verdict |
|---|---|---|
| §12 `LeaseExpiry` | comment "there is NO undefined `INVALIDATE` assignment state"; the CLOSE is delegated, not performed here | no `INVALIDATE`; single closer |
| §12 `LeaseExpiry` | `CALL EnterLowPowerListen(... stop_reason = ASSIGNMENT_REVOKED, assignment_ref = assignment, custody_on_close = expired, termination_reason = lease_expiry)` | expired/lease_expiry classification |
| §7 `EnterLowPowerListen` `CASE ASSIGNMENT_REVOKED` | `ATOMICALLY: SET status <- CLOSED; SET custody_status <- (custody_on_close = expired ? expired : revoked); IF custody_on_close = revoked: SET revocation_reason ...; SET termination_reason <- termination_reason` | atomic CLOSE; `revocation_reason` skipped for expiry |
| §0.8 `STRUCTURE Assignment` | `termination_reason : K6 — set ONLY when status = CLOSED ... For lease expiry: status = CLOSED, custody_status = expired, termination_reason = lease_expiry`; enum has NO `INVALID` | field declared; no `INVALID` member |
| §0.8 `J7 CANONICAL TERMINAL STATUS` | `SUPERSEDED` renewal-only; `CLOSED` for every non-renewal end-of-life; "a version is either renewed (SUPERSEDED + new CURRENT) or terminated (CLOSED)" | SUPERSEDED not written on expiry |
| §13 `RangeReassign` | `reason in {lease_expiry, abandonment, revocation, departure, conflict, security_recovery}`; suffix-only (`coverage_state != searched`) | `lease_expiry` permitted; suffix only |

No procedure performs `INVALIDATE`, writes an `INVALID` status, or writes `SUPERSEDED` on the lease-expiry path.

## 7. Worked example (TV89 — lease expiry closes CURRENT atomically, no INVALID, suffix reassigned)

**Preconditions.** Holder `H` is `ACTIVE_HASHING` on `CURRENT` version `v` (`accepted_frontier = f`,
`s <= f < e` for `range = [s, e]`); `H`'s lease expires and `H` does NOT renew (E9).

**Trace.** `LeaseExpiry` performs NO `INVALIDATE`. It routes `H` through
`EnterLowPowerListen(stop_reason = ASSIGNMENT_REVOKED, assignment_ref = v, custody_on_close = expired,
termination_reason = lease_expiry)`. `v` is still `CURRENT`, so the §7 precondition holds. The atomic
step sets `status(v) = CLOSED`, `custody_status = expired`, `termination_reason = lease_expiry`
(`revocation_reason` stays `null`), preserving the accepted searched prefix `[s, f]` and exposing only
the accepted unsearched suffix `[f+1, e]`. `LeaseExpiry` then CALLs `RangeReassign([f+1, e], reason =
lease_expiry, from_miner = H)`. One live `CURRENT` head existed before (I18a/I18b); zero live heads
remain on `v`'s lineage after (CLOSED). No `INVALID` state is ever entered.

**Expected.** No undefined `INVALID` state; `v` reaches `CLOSED`/`expired`/`lease_expiry` atomically;
I18a/I18b hold at every observable point; the suffix `[f+1, e]` is reassigned. Matches TV89
(Reqs K6, J7, I18a, I18b).

## 8. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | `LeaseExpiry` performs NO `INVALIDATE`; there is NO `INVALID` status/custody/termination value in §0.8 | **PASS** |
| C2 | The expiring `CURRENT` is terminated by the SINGLE closer `EnterLowPowerListen` (H8/J7), atomically to `status = CLOSED` | **PASS** |
| C3 | Lease-expiry fields: `custody_status = expired`, `termination_reason = lease_expiry` (declared K6 field), `revocation_reason = null` — `expired`/`lease_expiry`, NOT `revoked` | **PASS** |
| C4 | `SUPERSEDED` is NOT written on the lease-expiry path; `SUPERSEDED` remains renewal-only (`RenewAssignment`, F7/G2) | **PASS** |
| C5 | Accepted searched prefix preserved; ONLY the accepted unsearched suffix `[accepted_frontier+1, range_end]` reassigned via `RangeReassign` (`reason = lease_expiry`, suffix-only, C4/I8a) | **PASS** |
| C6 | I18a/I18b hold throughout: one live `CURRENT` head before, zero live heads after (CLOSED lineage); reassigned suffix opens a separate `REASSIGNED` lineage | **PASS** |
| C7 | Assignment still `CURRENT` when `EnterLowPowerListen` is invoked (precondition `status in {CURRENT, PAUSED}` met); CLOSE happens inside its atomic step | **PASS** |
| C8 | §12, §7, §0.8, §13, I18a/I18b/I8a, and TV89 all AGREE; A1 baseline **8.420833333 kWh** unchanged; no new consensus feature | **PASS** |

Exercised by **TV89** (lease expiry closes the `CURRENT` version atomically with no undefined
`INVALID` state, I18b preserved, suffix reassigned).

## Result

**Result: LEASE TERMINATION AUDIT (Stage 1K): PASS** — lease expiry without renewal performs NO
`INVALIDATE` and enters NO `INVALID` state; the expiring `CURRENT` version is terminated by the single
canonical closer `EnterLowPowerListen` (§7, H8/J7) atomically to `status = CLOSED`, `custody_status =
expired`, `termination_reason = lease_expiry` (a newly declared §0.8 field, K6), with
`revocation_reason = null` so the close is classified `expired`/`lease_expiry` and NOT `revoked`;
`SUPERSEDED` stays renewal-only (`RenewAssignment`, F7/G2); the accepted searched prefix is preserved
and only the accepted unsearched suffix is reassigned via `RangeReassign` (§13, `reason =
lease_expiry`); I18a/I18b hold at every observable point (one live `CURRENT` head before, zero live
heads after); §12/§7/§0.8/§13, I18a/I18b/I8a, and TV89 all agree, with the A1 baseline 8.420833333 kWh
unchanged and no new consensus feature.
