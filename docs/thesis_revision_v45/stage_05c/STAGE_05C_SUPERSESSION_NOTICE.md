# Stage 5C — Supersession Notice

**Added by Stage 5D. No Stage-5C evidence file has been rewritten, altered or deleted; this
notice is additive.**

## The `post_round_evaluation_count` field is INVALID and has been superseded

`docs/thesis_revision_v45/stage_05c/generate_stage5c_metrics.py` defined, per scenario:

```python
"post_round_evaluation_count": len(run.evaluation_ledger),
```

That is the **total number of evaluation records**, not the number of evaluations occurring
after their round closed. The field's name asserts a causal property the computation never
tested. Because it equals the ledger length, it is non-zero in every healthy run and would have
stayed non-zero if genuine post-round work had appeared — it could not fail, so it was not
evidence.

Every occurrence of `post_round_evaluation_count` in Stage-5C evidence
(`STAGE_05C_METRICS.json`, `evidence/stage5c_metrics.json`, and the "post-round evaluation
count" row of `STAGE_05C_TEST_REPORT.md`) must therefore be read as **ledger size**, and carries
no post-round meaning.

## What replaces it

Stage 5D computes three causal metrics over the immutable evaluation ledger and
`run_ctx.round_terminal_times`, with a declared floating-point tolerance of `1e-9`:

| metric | definition |
|---|---|
| `post_round_evaluation_record_count` | records whose `completion_time` is strictly later than their round's terminal time plus the tolerance |
| `post_round_evaluation_nonce_count` | `sum(interval_end - interval_start)` over exactly those records |
| `evaluation_missing_terminal_time_count` | finalised records whose `RoundID` has **no** terminal time — never silently treated as valid |

All three are **0** in all eight Stage-5D evidence scenarios, and the same three quantities are
asserted independently by `tests/thesis_revision_v45/stage2/test_stage5d_post_round_evidence_integrity.py`.

See `docs/thesis_revision_v45/stage_05d/` for the correction report, tests and regenerated
metrics.

## What is unaffected

No executable model code changed in Stage 5D — every accepted Stage-5C module under
`Models/PoCol/stage2/` is byte-identical, enforced as a CI gate. All other Stage-5C measurements,
invariants and conclusions stand as recorded. Note in particular that the adapter's own
`post_round_evaluation_count` (in `_range_lease_results`) was always a genuine causal
computation and is a *different* field from the generator's; only the generator's shadowing
definition was invalid.
