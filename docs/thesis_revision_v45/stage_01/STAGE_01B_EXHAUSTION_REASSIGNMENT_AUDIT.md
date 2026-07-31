# Stage 1B — Exhaustion & Reassignment Audit

Verifies CR-B4 (exhaustion semantics) and CR-B5 (completed ranges are not reassignable).

## Exhaustion semantics (CR-B4)

| Property | Result |
|----------|--------|
| Honest path uses actual cursor completion (`actual_frontier=range_end`, `actual_positions_evaluated=range_size`, `actual_exhaustion=true`, no valid solution encountered) | PASS — stated in RANGE_ASSIGNMENT §16, IDLE_POLICY §5.4, PROGRESS_VERIFICATION §3.1, pseudocode `RangeExhaust` |
| Adversarial path = "accepted reported exhaustion under the modeled audit abstraction" | PASS — RANGE_ASSIGNMENT, PROGRESS_VERIFICATION, THREAT_MODEL, FAILURE row 5 |
| No "target-verified exhaustion" / "I11 proves exhaustion" as an active claim | PASS — all remaining occurrences are explicit prohibitions/negations; T7 guard and MINER_STATE_MACHINE §2.3 now say "governed by I4/I8a and the actual-vs-reported progress model, not I11" |
| Exhaustion governed by I4, I8a, and the actual-vs-reported progress model — not I11 | PASS — INVARIANT_CATALOGUE I11 rewritten (solution-certificate only); ROUND_EXHAUSTED (R9) no longer requires I11 target verification |

## Completed-range / reassignment rules (CR-B5)

| Property | Result |
|----------|--------|
| A fully exhausted range is `coverage_state=searched`, `custody_status=completed` | PASS — T7→T8 closes it; RANGE_ASSIGNMENT, RANGE_LEASE, pseudocode `RangeExhaust` |
| `completed` present in the I8b custody set `{original, renewed, reassigned, revoked, expired, abandoned, completed}` | PASS — INVARIANT_CATALOGUE I8b, RANGE_ASSIGNMENT §15/§18, RANGE_LEASE §8.3/§9, TERMINOLOGY, OPEN_QUESTIONS Q5 |
| A completed range is NOT released to the reassignable pool, NOT marked `inactive_unsearched`, NOT reassigned under the same `TemplateID` | PASS — RANGE_LEASE §5.4, RANGE_ASSIGNMENT §13, PROTOCOL_SCOPE, FAILURE row 15 |
| "exhaustion" absent from every reassignment-reason set | PASS — permitted set is exactly `{lease_expiry, abandonment, revocation, departure, conflict, security_recovery}` in RANGE_LEASE §5.3, INVARIANT_CATALOGUE I9, pseudocode `RangeReassign`; no bare `{lease_expiry, exhaustion, ...}` remains |
| Only an unsearched suffix may be reassigned | PASS — RANGE_LEASE §5.3, pseudocode `RangeReassign` (`coverage_state != searched`) |
| Template refresh mints a new candidate-identity domain with new **original** assignments (not a reassignment of the old completed range) | PASS — RANGE_LEASE §5.4, FAILURE row 15, ROUND_STATE_MACHINE §2.9 |
| Contradictory phrase "EXHAUSTED_PENDING without completing the range" removed | PASS — RANGE_LEASE §5.1 |
| `EXHAUSTED_PENDING` reachable only after completion / accepted exhaustion (T7) | PASS — MINER_STATE_MACHINE §2.4 |

The exhausted-miner **redeploy** transition (T9) offers a *different* available unsearched
suffix (permitted reason) to the idle miner; it is not a reassignment of the miner's own
completed range and does not use exhaustion as a reassignment reason.

## Result

**EXHAUSTION & REASSIGNMENT AUDIT: PASS.**
