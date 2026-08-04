# Stage 5D — Post-Round Evidence-Integrity Lock

**Branch:** `thesis-v45-pocol-stage5d-post-round-evidence-integrity-lock`
**Base:** `89055b7b1c5dcf01d821037c7cd4c0d518983096` (Stage 5C)
**Tests:** 195 passed (185 retained + 10 new)
**Executable model code changed:** **none**

---

## 1. The defect

`docs/thesis_revision_v45/stage_05c/generate_stage5c_metrics.py` defined, per scenario:

```python
"post_round_evaluation_count": len(run.evaluation_ledger),
```

This counts **every** evaluation record, not evaluations occurring after round closure. The
name asserts a causal property the computation never tested.

The consequence is worse than an inaccurate number. Because the value equals the ledger length,
it is non-zero in every healthy run **and would have remained non-zero if genuine post-round
work had appeared**. A metric that cannot fail is not evidence. It reported a number in the
hundreds where the correct answer is zero, so any reviewer reading it as "post-round
evaluations" was reading a false positive of the exact kind the metric was meant to exclude.

## 2. The correction

Stage 5D replaces the field with a **causal** computation over the immutable evaluation ledger
and `run_ctx.round_terminal_times` — both of which already exist in accepted Stage-5C code, so
no executable module needed to change:

| metric | definition |
|---|---|
| `post_round_evaluation_record_count` | records whose `completion_time` is strictly later than `round_terminal_times[RoundID] + tolerance` |
| `post_round_evaluation_nonce_count` | `sum(interval_end - interval_start)` over exactly those records |
| `evaluation_missing_terminal_time_count` | finalised records whose `RoundID` has **no** terminal time |

**Declared tolerance: `1e-9`.** Simulation times are IEEE doubles produced by repeated addition,
so a record completing exactly *at* its round's terminal time can differ in the last ulp. Only
work strictly later than `terminal_time + 1e-9` is post-round.

**A missing terminal time is never silently treated as valid.** It is counted in its own metric
and listed in `offending_records` with reason `missing_terminal_time`, rather than being skipped
by an `if tt is not None` guard.

## 3. Measured result

All eight required scenarios, executed:

| scenario | post-round records | post-round nonces | missing terminal time | superseded field (`len(ledger)`) |
|---|---:|---:|---:|---:|
| A — Stage-5 disabled honest control | **0** | **0** | **0** | 239 |
| B — Stage 5 enabled, no leases | **0** | **0** | **0** | 159 |
| C — Stage 5 enabled, with leases | **0** | **0** | **0** | 159 |
| D — Path-A reassignment | **0** | **0** | **0** | 717 |
| E — genuine Path-B reassignment | **0** | **0** | **0** | 641 |
| F — abandonment coverage gap | **0** | **0** | **0** | 191 |
| G — false-exhaustion coverage gap | **0** | **0** | **0** | 191 |
| H — solution withholding | **0** | **0** | **0** | 4 |

The last column is the superseded definition, recorded for comparison only. The contrast is the
point: the invalid metric reported 4 – 717 where the correct answer is 0 everywhere.

## 4. The zero is evidence, not absence

A zero post-round count would be worthless if the scenario had done nothing. Each scenario is
therefore asserted to really perform the behaviour it is named for (test S5D-03 and the
generator's liveness invariants):

* every scenario has a non-empty evaluation ledger;
* Path A seated a reassignment with **no** Stage-3 wake (`wake_handles_created == 0`);
* Path B is a **genuine** Path B — `needs_stage3_wake`, an AVAILABLE reserve and a non-domain
  `ReassignmentWakeHandle` with `activation_scope == "REASSIGNMENT_WAKE_ONLY"`;
* the abandonment scenario really abandoned and really left a coverage gap;
* the false-exhaustion scenario really had a claim accepted and really left a coverage gap;
* the withholding scenario really withheld a valid solution.

## 5. The corrected computation is sensitive

Test S5D-02 carries two positive controls proving the audit responds rather than always
returning zero:

* shrinking one round's terminal time below its own records' completion times makes the audit
  report exactly those records and exactly their nonce count;
* removing a round's terminal time entirely makes the audit report them as
  `evaluation_missing_terminal_time_count`, **not** as post-round and **not** silently skipped.

Both probes restore the original state and the audit returns to its original values.

## 6. Scope of change

| area | changed? |
|---|---|
| `Models/PoCol/stage2/search.py` | no — byte-identical to the frozen Stage-4C baseline |
| every accepted Stage-5C executable module | no — byte-identical, enforced by a CI gate listing all seven digests |
| adversarial behaviour execution, reward ownership, frontier separation, identity/split accounting, false-exhaustion replay | no |
| accepted Stage-5C tests | no — all 185 retained byte-identical |
| historical Stage-5C evidence | not rewritten and not deleted; one **additive** supersession notice was placed alongside it |

Stage 6 and preregistration are not begun.

## 7. Claim scope — unchanged

Stage 5D adds **no** security, fairness, incentive-compatibility, Sybil-resistance,
selfish-mining-resistance, coalition-resistance, common-prefix, chain-quality or
Bitcoin/PoW-equivalent security claim. The algorithm remains PoCol; the energy-saving mechanism
remains the idle policy within PoCol; nonce-domain partitioning alone is never described as an
energy-saving mechanism; the security floor remains an operational active-capacity floor only;
dynamic difficulty remains excluded and no Stage-5 parameter changes the fixed SHA-256 target.
