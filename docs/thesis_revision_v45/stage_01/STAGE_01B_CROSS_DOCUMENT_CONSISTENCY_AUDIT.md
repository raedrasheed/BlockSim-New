# Stage 1B — Cross-Document Consistency Audit

The 15 required checks, run by semantic state-path review plus string search across
`docs/thesis_revision_v45/stage_01/`. Each flagged hit was read in context to confirm it is a
prohibition/negation, not an active claim.

| # | Check | Result |
|--:|-------|--------|
| 1 | No valid-solution path enters `EXHAUSTED_PENDING` | **PASS** — PATH B (T26) goes `ACTIVE_HASHING → LOW_POWER_LISTEN` directly; the only hit is the explicit prohibited-transition entry in MINER_STATE_MACHINE §3.1 |
| 2 | `EXHAUSTED_PENDING` reachable only through range exhaustion | **PASS** — sole incoming edge is T7 (`RANGE_EXHAUSTED`); stated in MINER_STATE_MACHINE §2.4 and the state-path audit |
| 3 | I11 has no progress/coverage/exhaustion dependency | **PASS** — I11 rewritten to early-stop-certificate validation only; explicitly delegates exhaustion to I4, I8a, and the actual-vs-reported progress model |
| 4 | I4 includes verified-solution stop as a separate legal trigger | **PASS** — I4 lists four triggers, each with a `stop_reason`; `VALID_SOLUTION_VERIFIED` is distinct |
| 5 | No document uses "target-verified/checked exhaustion" as a claim | **PASS** — all remaining occurrences are prohibitions/negations; T7 guard and MINER_STATE_MACHINE §2.3 now cite I4/I8a, not I11 |
| 6 | No completed/exhausted range is reassignable under the same `TemplateID` | **PASS** — `custody_status = completed`; RANGE_LEASE §5.4, RANGE_ASSIGNMENT, SCOPE, FAILURE row 15 |
| 7 | "exhaustion" absent from every reassignment-reason set | **PASS** — permitted set exactly `{lease_expiry, abandonment, revocation, departure, conflict, security_recovery}`; no `{lease_expiry, exhaustion, …}` remains (I9 aligned) |
| 8 | Every reassignment covers only an unsearched range/suffix | **PASS** — RANGE_LEASE §5.3, pseudocode `RangeReassign` (`coverage_state != searched`) |
| 9 | `H_active = H_honest + H_adversarial` exactly | **PASS** — invariant I17; SECURITY_FLOOR, INVARIANT_CATALOGUE, TERMINOLOGY, TRACEABILITY |
| 10 | `H_adversarial` not independently sampled after `H_active` | **PASS** — pseudocode `ActiveHashRateUpdate` samples the adversarial active-state census, then derives all three deterministically |
| 11 | `q_adv` NA when total active hash rate is zero, breach recorded | **PASS** — SECURITY_FLOOR §1.1, I17, TERMINOLOGY, OPEN_QUESTIONS Q9 |
| 12 | Early-stop wording narrowed to solution-triggered stopping | **PASS** — "the only solution-triggered mechanism … before full-block propagation completes"; other cessation causes listed (EARLY_STOP, SCOPE) |
| 13 | Fixed-horizon control text does not claim equal realised work | **PASS** — ENERGY_MODEL §4/§ and SCOPE §D state the scenarios do **not** realise the same total work; not service/security-equivalent |
| 14 | No executable code, configuration, DOCX, or PDF changed | **PASS** — git delta confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| 15 | PoCol remains the algorithm name | **PASS** — forbidden variants appear only inside prohibition statements |

## Residual fixes applied during this audit (beyond the agent edits)

- `STAGE_01_ROUND_STATE_MACHINE.md`: `ROUND_EXHAUSTED` (§2.8, R9, §3.9, §4.1) decoupled from
  "I11 target verification / verified target-checked exhaustion" → accepted range-exhaustion
  accounting governed by I4/I8a and the actual-vs-reported progress model.
- `STAGE_01_MINER_STATE_MACHINE.md`: T7 guard and §2.3 transition-guard prose decoupled from
  I11/target verification; T9 renamed to a redeploy offer of an available unsearched suffix
  (exhaustion is not a reassignment reason).
- `STAGE_01_INVARIANT_CATALOGUE.md`: I9 reassignment-reason enum aligned to the permitted set
  (removed "exhaustion").
- Stale `I1..I16` range references updated to `I1..I17` (COMPLETION_REPORT, OPEN_QUESTIONS,
  THREAT_MODEL, FAILURE, PROTOCOL_SCOPE; TERMINOLOGY already aligned).

## Result

All 15 cross-document consistency checks pass. The valid-solution and exhaustion paths never
merge, I4/I11/I17 are consistent, completed ranges are non-reassignable, and the hash-rate
identity holds. No cross-document semantic contradiction remains.
