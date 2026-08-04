# Stage 6 — Frozen Exclusion, Retention, Rerun and NA Policy

Sixteen rules, frozen in Stage 6 before any confirmatory seed is executed. They govern Stage 7
execution and Stage 8 analysis.

---

| # | Rule |
|---|---|
| **R01** | **Zero-block runs are retained.** A run that accepts no block is a real observation of this configuration, not a failure. |
| **R02** | **No replacement seed is ever drawn.** A zero-block run, an extreme run, or an inconvenient run never causes a substitute master seed to be used. The confirmatory registry of 30 seeds is fixed. |
| **R03** | **Per-block and per-transaction quantities are NA when their denominator is zero.** With `accepted_blocks = 0`, any per-block ratio is NA. |
| **R04** | **NA is never imputed as zero.** An NA is an NA. |
| **R05** | **NA rows are never dropped from run-level tables.** The run appears with its NA fields recorded as NA. |
| **R06** | **Every physical run is exactly one inferential unit.** Rounds, miners, blocks and transactions are never units. |
| **R07** | **A run contributing to multiple metrics is not duplicated.** One run, one row, however many outcomes it carries. |
| **R08** | **A simulation exception is retained as a failed run**, with its master seed, its full configuration, its logs and `run_status` recorded. It is never silently discarded. |
| **R09** | **A rerun is permitted only for infrastructure failure unrelated to model output** — for example the host being killed, disk exhaustion, or a scheduler eviction. A model-level exception is never grounds for a rerun. |
| **R10** | **A rerun uses the exact same master seed and the exact same configuration.** |
| **R11** | **Both the original failure and the rerun are archived.** The record of the failure is never replaced by the record of the success. |
| **R12** | **No outcome-based exclusion.** No run is ever removed because of the value of any outcome it produced. |
| **R13** | **No manual outlier removal.** There is no discretionary exclusion path at all. |
| **R14** | **Robust-estimator sensitivity analyses are labelled secondary** and never replace the preregistered primary estimand. |
| **R15** | **`q_adv` is NA when `H_active = 0`**, remains NA, and is never numerically compared or aggregated as if it were a number. |
| **R16** | **No post-hoc change** to any margin, outcome priority or hypothesis direction is permitted after the Stage-6 commit. |

---

## Application notes

**Zero-block feasibility is confirmed, not hypothetical.** The Tier-1 pilot produced zero-block
runs (scenario C06, both pilot seeds), so R01/R03/R04/R05 are exercised paths rather than
untested policy. `zero_block_indicator` and `zero_block_rate` are defined in
`STAGE_06_OUTCOME_DICTIONARY.csv` with explicit NA rules.

**NA feasibility is confirmed.** 32 of 42 Tier-1 runs reported `maximum_q_adv = NA`, so the NA
path through the outcome dictionary and the analysis inputs is exercised.

**Failed runs.** `run_status` is recorded per run in the confirmatory output schema with values
`COMPLETED`, `CONFIG_ERROR`, `EXECUTION_ERROR` and `INFRASTRUCTURE_FAILURE`. Only the last
admits a rerun under R09. The Stage-7 failure-stop threshold is defined in
`STAGE_06_STAGE7_EXECUTION_PLAN.md` §7.

**Integrity-gate failures are not exclusions.** If an IP-H9 gate is non-zero in a run, that run
is retained and the gate is reported as failed. A failed integrity gate invalidates the
associated claim; it never removes the observation.

**Empty-ledger guard.** An IP-H9 zero is only evidence if the run actually did work. Any run
with `evaluation_ledger_nonce_total == 0` is reported as a **vacuous** gate evaluation rather
than a pass, exactly as the accepted Stage-5D CI gate does.
