# Stage 5 — Test Report

**Command:** `python -m pytest tests/thesis_revision_v45/stage2/ -v`
**Result:** `150 passed in 13.58s` — 0 failed, 0 skipped, 0 xfailed
**Evidence:** `evidence/pytest_stage5.log`, `evidence/pytest_stage5.junit.xml`
**Environment:** Python 3.11, pytest 9.1.1

---

## 1. Retention

| Suite | Tests | Status |
|---|---:|---|
| `test_stage2_adapter.py` | 4 | retained |
| `test_stage2_e2e.py` | 5 | retained |
| `test_stage2_scientific.py` | 14 | retained |
| `test_stage2_semantic_vectors.py` | 14 | retained |
| `test_stage3_security_floor.py` | 31 | retained |
| `test_stage4_range_leases.py` | 21 | retained |
| `test_stage4a_lease_lifecycle.py` | 14 | retained |
| `test_stage4b_terminal_pathb_replay_energy.py` | 12 | retained |
| `test_stage4c_exact_energy_links_deadline.py` | 9 | retained |
| **Accepted Stage-4C subtotal** | **124** | **all retained, all passing** |
| `test_stage5_adversarial_incentive.py` | 26 | new (S5-01 … S5-26) |
| **Total** | **150** | |

### The only change to a retained test

Four lines pin the adapter result-schema literal, which Stage 5 is required to bump:

| File | Change |
|---|---|
| `test_stage2_adapter.py:32` | `"stage4.1"` → `"stage5.1"` |
| `test_stage3_security_floor.py:332` | docstring `stage4.1` → `stage5.1` |
| `test_stage3_security_floor.py:336` | `"stage4.1"` → `"stage5.1"` |
| `test_stage4_range_leases.py:415` | `"stage4.1"` → `"stage5.1"` |

No assertion was removed, relaxed, renamed or skipped. `git diff` against the frozen baseline
shows exactly six deleted lines across the whole change set: these four, plus the
`RESULT_SCHEMA_VERSION` constant and one import line in `adapter.py`/`__init__.py`.

## 2. New tests S5-01 … S5-26

| ID | Requirement | What it locks |
|---|---|---|
| S5-01 | S5-2 | Every feature disabled by default; a default run touches no Stage-5 registry |
| S5-02 | S5-1 | One immutable profile per (round, miner); re-materialisation is a no-op |
| S5-03 | S5-2 | Undeclared vocabulary and out-of-range parameters rejected at construction |
| S5-04 | S5-3, S5-11 | Only RATIONAL / BYZANTINE / COORDINATOR count as adversarial |
| S5-05 | S5-4 | Free riding reduces the **actual physical** rate; ground truth preserved |
| S5-06 | S5-4 | A misreported rate never changes the physical search rate |
| S5-07 | S5-3 | The modeled audit draw is deterministic and replay-idempotent |
| S5-08 | S5-5 | A detected false claim is rejected; the real state stands |
| S5-09 | S5-5 | An undetected claim leaves a recorded, quantified coverage gap |
| S5-10 | S5-5 | A gapped round is never labelled a full-domain exhaustion |
| S5-11 | S5-6 | A withheld solution is not published and no block is accepted |
| S5-12 | S5-6 | Delayed release is accepted through the normal acceptance path |
| S5-13 | S5-6, S5-12 | Release into a closed round is a no-op; replay is a second no-op |
| S5-14 | S5-6 | A withheld round is never labelled a full-domain exhaustion |
| S5-15 | S5-7 | Delayed wake extends the WAKING interval; both times recorded |
| S5-16 | S5-7 | **Delaying a wake costs energy and never saves it** |
| S5-17 | S5-9 | Out-of-range attempts earn no credit of any kind |
| S5-18 | S5-5 | Withheld progress lowers the accepted frontier; re-evaluation counted |
| S5-19 | S5-10 | Work reward per unique accepted committed evaluation |
| S5-20 | S5-10 | The ledger is replay-idempotent and reconciles to residual 0.0 |
| S5-21 | S5-10 | Winner reward only to the solver of an accepted block |
| S5-22 | S5-10 | Penalties need a detected/rejected action; crash faults spared |
| S5-23 | S5-8 | Naive and deduplicated accounting computed in parallel |
| S5-24 | S5-11 | `q_adv` uses actual active rates; NA when no capacity is active |
| S5-25 | S5-12 | Stage-5 actions are round-terminal; the registry is idempotent |
| S5-26 | S5-13, S5-26 | No Stage-5 parameter changes the fixed target; schema preserved |

## 3. Negative and no-effect coverage

Tests that assert something must **not** happen:

- S5-01 — no registry populated, `q_adv` reported NA rather than a fabricated 0.0;
- S5-03 — seven distinct `ValueError` paths across both policies;
- S5-08 — a rejected claim creates no coverage gap and no gap label;
- S5-10 / S5-14 — `FULL_DOMAIN_EXHAUSTED_NO_BLOCK` absent, `full_domain_exhausted_count == 0`;
- S5-13 — stale release produces `withheld_release_stale_noop`, replay produces
  `withheld_release_replay_noop`, and the counter increments exactly once;
- S5-17 — no reward entry references any rejected invalid action;
- S5-21 — a withholding run pays zero winner reward;
- S5-22 — detection off ⇒ no false-claim penalty; a crash fault ⇒ no abandonment penalty;
- S5-26 — three separate forbidden attack profiles each raise `ValueError`.

## 4. Prohibited-claim assertions

S5-26 asserts positively that the results block's `stage5_claim_scope` names every property
Stage 5 does not establish: incentive compatibility, fairness, Sybil resistance, selfish-mining
resistance, coalition resistance, common-prefix security, chain-quality security and
PoW-equivalent security — and that the mechanism string remains
`"idle policy within PoCol"`.

## 5. Determinism

The suite was executed repeatedly during development with identical results. No test uses
wall-clock time, randomness, or network access. The modeled audit derives from SHA-256 over the
policy seed and the immutable claim identity, so every audit verdict is reproducible.

## 6. What the tests deliberately do not do

They do not execute the confirmatory experiment matrix, perform statistical analysis, or assert
any security property. Where a modeled attack succeeds — solution withholding denying liveness
entirely, undetected false exhaustion leaving 3,000 nonces unsearched — the tests assert that it
succeeds and that the protocol reports the failure honestly, not that PoCol prevents it.
