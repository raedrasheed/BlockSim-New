# Stage 7 — Frozen Confirmatory Execution: BLOCKED at the resource preflight

**No confirmatory master seed has been executed.** All eight mandated pre-execution gates pass;
the frozen plan is sound and ready. Execution is blocked by the resource preflight, on the
host, not by the science.

## 1. Pre-execution gates — all PASS

| # | gate | result |
|---:|---|---|
| 1 | 195 accepted executable tests (local) | **195 passed** |
| 2 | frozen engine hashes | all 8 accepted modules byte-identical |
| 3 | deterministic regeneration (matrix, seeds, run registry, frozen configs) | all 6 generators verified |
| 4 | exactly 660 unique run IDs | 660 total, 660 unique |
| 5 | pilot / confirmatory seed disjointness | 8 pilot, 30 confirmatory, 0 overlap |
| 6 | every pair matches on every non-treatment field | 0 mismatches |
| 7 | difficulty and target fixed | 21 scenarios at 1000; C06 declared exception |
| 8 | zero confirmatory output before execution | 0 files; `data/.../stage_07/` absent |

## 2. Preflight verifications

| check | required | available | verdict |
|---|---:|---:|---|
| V1 memory (1.25 x worst heavy worker) | 6.43 GB | 12.56 GB | **PASS** |
| V2 disk (compress-on-write path) | 1.9 GB | 11.35 GB | **PASS** |
| V3 host lifetime (1.25 x projected duration) | **155.3 days** | **0 (no guarantee)** | **FAIL** |

## 3. Why V3 fails

Projected under the **mandated conservative schedule** (SECURITY_FLOOR one at a time,
REASSIGNMENT one at a time, LIGHTWEIGHT up to the measured safe limit of 3):

| class | scenarios | runs | per-run | class total | basis |
|---|---:|---:|---:|---:|---|
| SECURITY_FLOOR | 3 | 90 | 18.57 h | 1 671 h | **ESTIMATED** from the right-censored B02 |
| REASSIGNMENT | 10 | 300 | 4.37 h | 1 311 h | MEASURED (C04) |
| LIGHTWEIGHT | 9 | 270 | 2.75 h | 744 h | MEASURED (A03, A05) |

* heavy serial chain (the binding path): **2 982 h = 124 days**
* lightweight at 3 concurrent: 248 h = 10 days, overlapping
* **resource-aware duration: 124.3 days**; V3 threshold 155.3 days

The host is an ephemeral container with **no lifetime guarantee**. The longest process it has
sustained in this project is **6.24 h** — the B02 pilot, which was reaped before completing.
A single SECURITY_FLOOR run needs ~18.6 h, so **the first run of the mandated priority order
cannot complete here**, let alone all 660. Shortfall against V3: **~597x**.

## 4. Why execution was not started anyway

Starting would produce no completed run in the first class and no analysable dataset, while
consuming the session. Three specific reasons, none of them about effort:

1. **The first mandated run cannot finish.** Priority order puts SECURITY_FLOOR first at
   ~18.6 h against a demonstrated ~6.2 h ceiling.
2. **Reordering to make progress would break the frozen schedule.** Running only LIGHTWEIGHT
   because it fits is convenience-based selection of which conditions get executed, which the
   frozen plan forbids.
3. **A partial confirmatory dataset must not reach Stage 8.** Stage 8 was authorised to follow
   "immediately after Stage 7 completes successfully". It has not, so it must not begin.
   Producing hypothesis decisions from an incomplete or fabricated dataset is the one outcome
   that would invalidate the whole preregistration.

Nothing here is an outcome-based stop: no confirmatory run was executed, so no effect of any
kind has been observed, inspected or inferred.

## 5. Minimum feasible execution plan

| requirement | value | basis |
|---|---|---|
| persistent host lifetime | **>= 155 days** at 1 heavy worker, or **>= 20 days** at 8 heavy workers | V3 = 1.25 x duration |
| CPU cores | >= 16 (3 726 core-hours total) | measured + estimated per class |
| RAM | >= 16 x 5.14 GB = **>= 82 GB** for 16 concurrent worst-case workers | V1 at the 1.25 margin |
| free disk | >= 2 GB with compress-on-write; ~16.3 GB if raw-first | V2, measured |
| durable archive | >= 0.28 GB at the conservative ratio | measured xz, halved |

Two things would each unblock this independently:

* **a persistent execution host** meeting the table above; or
* **completing the B02-class measurement first**, which would replace the ESTIMATED
  SECURITY_FLOOR runtime with a measured one and could materially change the 124-day figure.

The frozen scientific content is untouched and remains exactly as accepted at
`026483496ffb434243f45e174c63b43b77b3b43a`.
