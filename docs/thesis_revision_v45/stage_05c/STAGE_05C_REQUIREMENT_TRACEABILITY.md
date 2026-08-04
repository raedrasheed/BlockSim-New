# Stage 5C — Requirement Traceability

Every Stage-5C requirement maps to executable code and to at least one executing test.

## Requirements

| Req | Requirement | Implementation | Tests |
|---|---|---|---|
| **S5C-1** | Derive identity and split amplification from executed records; a request never overrides records; 1 real + 3 virtual = 4 identities; 2 real + 5 virtual = 7; naive reward reconstructed from record-derived counts; dedup keeps unique first-evaluator work; per-entity reconciliation table | `adversarial_runtime.entity_record_accounting`, `entity_reconciliation`; the S5C-1 block in `finalise_incentives`; `refresh_incentive_aggregates` (ratios assigned as run-level maxima); stats `assignment_split_amplification_ratio`, `identity_multiplication_amplification_ratio`; adapter key `entity_reconciliation` | S5C-01, S5C-02, S5C-03 |
| **S5C-2** | `physical_evaluation_count` global and ledger-derived, enabled or disabled; residual always the real absolute difference, never forced to zero; disabled still means no adversarial action/claim/reward/penalty; `behaviour_profile_count` exemption removed | `adversarial_runtime.note_physical_evaluation` (counts before the enablement guard); `adapter.results_schema` residual unguarded; `adapter._evaluation_ledger_nonce_total`; Stage-5C metrics invariant with no exemption | S5C-04, S5C-05, S5-01 (retained, strengthened) |
| **S5C-3** | Resolve the immutable claim identity before any counter or state change; exact replay returns the stored result for detected AND accepted claims; over-limit rejection diagnostic counts once per identity | `adversarial_runtime.maybe_false_exhaustion` (identity resolved before every guard); `context.false_exhaustion_results`; `charge_action_budget` + `context.adv_action_rejected` | S5C-06 (both dispositions), S5C-06b |
| **S5C-4** | Interval-exact reconciliation: every evaluation interval split into already-covered and newly-covered subintervals; `[0,80)`+`[40,100)` yields exactly `[0,40)`, `[40,80)`, `[80,100)`; table reconciles to metrics and the reward ledger | `adversarial_runtime._ownership_by_lineage` (atomic segments cut at every interval boundary) | S5C-07, S5B-01 (retained, corrected representation) |

## Tests

| Test | Assertion summary |
|---|---|
| **S5C-01** | One real miner plus three `VirtualIdentityRecord`s yields four represented identities and the naive reward uses four; the records exist, grant no capacity, and the naive figure equals `unique work × split ratio × identity ratio` |
| **S5C-02** | Two real miners plus five `VirtualIdentityRecord`s yields seven represented identities; identities still grant zero physical capacity |
| **S5C-03** | A requested split of 8 over a 3-nonce span creates 3 `SubAssignmentRecord`s; the ratio is 3.0, never 8.0; the request survives unchanged on the config; the subranges still partition the parent range |
| **S5C-04** | The disabled honest control has a non-empty ledger and reports `physical_evaluation_count == evaluation_ledger_nonce_total > 0` with residual 0, while creating no adversarial action, claim, reward or penalty |
| **S5C-05** | The same equality holds across four executions: Stage 5 disabled/enabled × leases off/on |
| **S5C-06** | Exact replay of one false-exhaustion claim (parametrised over detected and accepted) returns the same stored object and leaves the full protocol and metrics snapshot unchanged; one progress claim; charged once |
| **S5C-06b** | Re-offering a refused over-limit action five times records one rejection, zero claims, zero budget |
| **S5C-07** | The reconciliation for `[0,80)` + `[40,100)` is exactly `[0,40)`, `[40,80)`, `[80,100)`; `[40,100)` never appears; rows reconcile to `unique_rewarded_nonce_count = 100`, `duplicate = 40`, and to the WORK_REWARD ledger `{M000: 80, M001: 20}`; a second finalisation still changes nothing |

## Retained tests

All 176 tests accepted at Stage 5B pass. Three mechanical edits were required; none weakens an
assertion.

| File | Edit | Reason |
|---|---|---|
| `test_stage2_adapter.py`, `test_stage3_security_floor.py`, `test_stage4_range_leases.py`, `test_stage5_adversarial_incentive.py`, `test_stage5b_ownership_pathb_wake_coverage.py` | schema literal `stage5b.1` → `stage5c.1` | required by the S5C schema bump; the assertion still pins the declared schema exactly |
| `test_stage5b_ownership_pathb_wake_coverage.py` (S5B-01) | the duplicate row is asserted as the exact segment `[40,80)`, owner M000, later evaluator M001, rewarded 40, duplicate 40 | the previous assertion (`rewarded_count == 0` on the duplicate row) encoded the raw-interval representation S5C-4 replaces. The new assertion is strictly stronger: it pins the interval, first evaluator, owner, later evaluator and both counts. |
| `test_stage5_adversarial_incentive.py` (S5-01) | `physical_evaluation_count` excluded from the all-zero sweep; asserted `== evaluation_ledger_nonce_total > 0` instead | S5C-2 requires the disabled control to report its real count. The directive states that computing this from the immutable ledger "is not a protocol effect and does not violate baseline preservation". The test now proves more, not less: no adversarial action, claim, reward or penalty **and** a correct non-zero physical count. |

No test was deleted, renamed, skipped or relaxed. The corrected S5-18, S5-19 and every Stage-5B
assertion are preserved.
