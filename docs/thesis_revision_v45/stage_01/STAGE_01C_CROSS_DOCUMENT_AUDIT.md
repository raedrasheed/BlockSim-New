# Stage 1C — Cross-Document Audit (acceptance gates)

The Stage-1C acceptance gates, verified by semantic procedure comparison (see
`STAGE_01C_PSEUDOCODE_CONFORMANCE_AUDIT.md`) plus corpus consistency checks. This audit
compares the actual pseudocode procedures against B1–B9 and C1–C10, not merely prohibited
strings.

| # | Acceptance gate | Result |
|--:|-----------------|--------|
| 1 | `EnterLowPowerListen` has five reason-specific dispositions | **PASS** — `RANGE_EXHAUSTED`, `ASSIGNMENT_REVOKED`, `VALID_SOLUTION_VERIFIED`, and the shared `ROUND_ACCEPTED`/`ROUND_ABORTED` closure (C1's canonical grouping); no generic release |
| 2 | Completed ranges are never released or reassigned | **PASS** — `EnterLowPowerListen` RANGE_EXHAUSTED case, T7/T8 (no reclamation), `RangeReassign` rejects `completed`; TV12 |
| 3 | Reported progress never directly updates accepted searched coverage | **PASS** — `ProgressCommit` writes `reported_*` only; I8a uses `accepted_searched` |
| 4 | Exhaustion is adjudicated before searched/completed status | **PASS** — `RangeExhaust` sets `searched`/`completed` only inside the `ACCEPTED` branch (C2) |
| 5 | Lease expiry reassigns only the accepted unsearched suffix | **PASS** — `LeaseExpiry`/`RangeReassign` use `[accepted_frontier+1, range_end]` (C4); TV7 |
| 6 | Template refresh creates new original assignments | **PASS** — `TemplateRefresh` closes old, creates originals, `previous_assignment_reference=null` (C5); TV8 |
| 7 | Solution discovery does not immediately accept the block | **PASS** — `ActiveHashing` calls `ScheduleSolutionPropagation`, not `ValidBlockAccept` (C6) |
| 8 | Certificate and block propagation are event-scheduled | **PASS** — `ScheduleSolutionPropagation`/`CertificateArrival`/`BlockAcceptancePoint` (C6) |
| 9 | `q_adv = NA` is never numerically compared | **PASS** — `ActiveHashRateUpdate` computes only; `SecurityFloorEvaluate` guards `q_adv != NA` (C7); TV9 |
| 10 | One function owns security-floor breach recording | **PASS** — `SecurityFloorEvaluate` alone (`RECORD_ONCE`); `ActiveHashRateUpdate` records no breach (C7) |
| 11 | I17 holds exactly | **PASS** — `H_active = H_honest + H_adversarial` at every event-update (I17) |
| 12 | All semantic test vectors pass on paper | **PASS** — 12/12 (`STAGE_01C_SEMANTIC_TEST_VECTORS.md`) |
| 13 | No source/configuration/DOCX/PDF changes | **PASS** — git delta confined to `docs/thesis_revision_v45/stage_01/`; draft-42 `2c3afdc5…`, draft-44 `a31400bc…` byte-identical |
| — | PoCol remains the algorithm name | **PASS** — forbidden variants only in prohibition statements |
| — | Reward eligibility canonical ("NOT SPECIFIED AT STAGE 1") | **PASS** — MINER_STATE_MACHINE (8 states), REWARD_PENALTY (parameterised/deferred), RESERVE, IDLE, TERMINOLOGY, SCOPE consistent |

## Residual fixes applied during this audit (beyond agent edits)
- MINER_STATE_MACHINE T7/T8 side effects: removed "release … for reclamation"; T19 false
  exhaustion re-attributed to the audit model (not I11); per-state reward eligibility set to the
  canonical wording (C8/C10).
- Traceability matrix: added the modeled acceptance point / accepted coverage (R05/R16/R23).
- RANGE_LEASE §8.1/§9 and TEMPLATE_SPECIFICATION §… I8a partition relabelled to
  `accepted_searched` (corpus uniformity, C3).
- REWARD_PENALTY work-reward reference aligned to I8a accepted coverage and marked a symbolic
  Stage-5 parameter (C10).

## Result
All acceptance gates pass. The executable pseudocode and state-machine side effects now conform
exactly to B1–B9 and C1–C10; the valid-solution and exhaustion paths never merge; acceptance is
event-ordered at the modeled acceptance point; coverage is adjudicated (accepted) before it is
counted; completed ranges are never reassigned; security-floor evaluation is centralised; and
I17 holds exactly. No cross-document semantic contradiction remains.
