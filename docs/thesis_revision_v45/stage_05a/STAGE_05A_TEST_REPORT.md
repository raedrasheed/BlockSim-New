# Stage 5A — Test Report

**Command:** `python -m pytest tests/thesis_revision_v45/stage2/ -v`
**Result:** `162 passed` — 0 failed, 0 skipped, 0 xfailed
**Evidence:** `evidence/pytest_stage5a.log`, `evidence/pytest_stage5a.junit.xml`
**Environment:** Python 3.11, pytest 9.1.1

---

## 1. Retention

| Suite | Tests |
|---|---:|
| Stage-2B / 3 / 3A / 4 / 4A / 4B / 4C retained | 124 |
| Stage-5 (S5-01 … S5-26) retained | 26 |
| **Retained subtotal** | **150** |
| Stage-5A (S5A-01 … S5A-12) new | 12 |
| **Total** | **162** |

## 2. Two accepted Stage-5 tests were CORRECTED, not weakened

S5-18 and S5-19 asserted behaviour the acceptance review identified as defective. Leaving them
unchanged would have made the Stage-5A corrections impossible to land, because the old
assertions *require* the defects.

| Test | Old assertion (defective) | New assertion (corrected, stronger) |
|---|---|---|
| S5-18 | `prog.committed_frontier == 40` — i.e. the physical frontier **is** rewound | `prog.committed_frontier == 80` (never rewound), plus the separate record's `(actual, reported, accepted) == (80, 40, 40)`, its `reassignment_start`, its `reevaluation_interval` and `physical_frontier_rewind_count == 0` |
| S5-19 | `len(work) == len(raw_intervals)` — one reward per raw interval | one entry per canonical **union** interval, `work_reward_total == r_work × union cardinality`, `unique_rewarded_nonce_count == union cardinality`, `work_reward_union_residual == 0.0` |

Both replacements add assertions rather than remove them. No test anywhere was renamed, deleted,
skipped, or had an assertion relaxed. The schema-version literal moved `stage5.1` → `stage5a.1`
in four places, as the schema bump requires.

## 3. New tests S5A-01 … S5A-12

| ID | Requirement | What it locks |
|---|---|---|
| S5A-01 | S5A-1 | Physical frontier monotonic after an accepted claim — unit **and** end-to-end through a real Path-B reassignment; replay-idempotent |
| S5A-02 | S5A-1 | Actual / reported / accepted independently queryable; identity-bound; detected claim keeps accepted == actual and opens no window |
| S5A-03 | S5A-2 | `[0,80)` + `[40,80)` rewards exactly 80 unique positions |
| S5A-04 | S5A-2 | Union residual 0.0; exactly 40 duplicate rewards prevented; 120 physical positions still visible |
| S5A-05 | S5A-3 | Reported-rate sizing changes ranges, not physical rates; domain, disjointness and coverage preserved; flag OFF reproduces accepted allocation |
| S5A-06 | S5A-4 | Real subassignments; capacity shares sum to one entity budget; residual 0.0 |
| S5A-07 | S5A-4 | Subranges disjoint and contiguous, union == parent; throughput unchanged |
| S5A-08 | S5A-4 | Virtual identities explicit, no physical capacity, no extra assignment |
| S5A-09 | S5A-5 | Round closes before the action ⇒ no action, no penalty |
| S5A-10 | S5A-5 | One executed action ⇒ exactly one penalty; replay adds none; crash fault excluded |
| S5A-11 | S5A-6 | Two wake episodes ⇒ two distinct actions with independent real floor overlap |
| S5A-12 | S5A-7 | Action limit, false-exhaustion offset (incl. the declared zero meaning) and alternative-solution-won all have effects |

## 4. Negative coverage

Assertions that something must **not** happen: no physical rewind (S5A-01, end-to-end);
no re-evaluation window on a detected claim (S5A-02); no double reward for overlapping
intervals (S5A-03/04); no physical-rate change under reported-rate allocation and no allocation
change when the flag is off (S5A-05); no capacity creation from splitting or identities
(S5A-07/08); no penalty without an executed action and none for a crash fault (S5A-09/10); no
action-record collision across wake episodes (S5A-11); no false-exhaustion attempt for a
truthful zero-offset claim and no alternative-solution-won when nobody publishes (S5A-12).

## 5. Two test-calibration errors found and fixed during development

Both were faults in my own new tests, not in the implementation:

- S5A-05 initially used a 3× multiplier, which with rates 100/200/300/400 produces
  `400 × 300/1200 = 100` — coincidentally identical to the equal split, so the assertion could
  not distinguish the modes. Changed to 5×.
- S5A-12 initially declared one claimer against a limit of 2, so the per-round budget was never
  reached. Changed to four claimers.

## 6. Determinism

No test uses wall-clock time, randomness or network access. The modeled audit remains a
deterministic SHA-256 draw over the policy seed and immutable claim identity.
