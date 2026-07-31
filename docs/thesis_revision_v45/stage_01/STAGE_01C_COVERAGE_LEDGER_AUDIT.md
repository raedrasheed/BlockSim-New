# Stage 1C — Coverage-Ledger Audit

Verifies C3 (three coverage layers), C4 (accepted unsearched suffix), C5 (template refresh),
and C9 (accepted full-domain exhaustion) across the corpus.

## Three coverage layers (C3)

| Layer | Meaning | Who may write it | Normative role |
|-------|---------|------------------|----------------|
| `actual_frontier` / `actual_searched` | simulator ground truth | simulator model | never asserted by protocol |
| `reported_frontier` / `reported_searched` | protocol-level claim | `ProgressCommit` (reported_* only) | audited input |
| `accepted_frontier` / `accepted_searched` | adjudicated coverage | adjudication only (RangeExhaust honest-completion / audit) | **the only layer in I8a** |

Checks:
- `ProgressCommit` updates `reported_*` only; it does **not** update the I8a accepted measure —
  PASS (`STAGE_01_PROTOCOL_PSEUDOCODE.md` §14, `STAGE_01_PROGRESS_VERIFICATION_ABSTRACTION.md`).
- I8a partition uses **accepted** coverage everywhere:
  `accepted_searched + active_unsearched + inactive_unsearched = assigned_domain` — PASS across
  INVARIANT_CATALOGUE, RANGE_ASSIGNMENT, RANGE_LEASE, PROTOCOL_PSEUDOCODE, TEMPLATE_SPECIFICATION
  (9 documents). No live document leaves the partition labelled bare `searched` (the only bare
  occurrences are historical Stage-1A deliverables, intentionally frozen).
- Reported→accepted promotion occurs only by adjudication (honest ground-truth or modeled
  audit) — PASS.

## Accepted unsearched suffix (C4)

- Reassignment (lease expiry, abandonment, revocation, departure, conflict, security recovery)
  uses only `[accepted_frontier + 1, range_end]`; whole range only if no accepted positions;
  nothing if `accepted_frontier = range_end` — PASS (`LeaseExpiry`, `RangeReassign`, RANGE_LEASE
  §5.3).
- `RangeReassign` receives the exact unsearched suffix and asserts no searched prefix is
  included — PASS.

## Completed ranges (B5)

- A completed range (`coverage_state = searched`, `custody_status = completed`) is never
  released or reassigned under the same `TemplateID`; `RangeReassign` preconditions reject it;
  test vector TV12 confirms rejection — PASS (10 documents state completed-not-reassignable).

## Template refresh (C5)

- `TemplateRefresh` closes old-`TemplateID` assignments, preserves history, mints a fresh
  `TemplateID`, creates new **original** assignments (`previous_assignment_reference = null`),
  never calls `RangeReassign` for old ranges, keeps difficulty fixed — PASS (`TemplateRefresh`,
  RANGE_LEASE §5.4, ROUND_STATE_MACHINE §2.9).

## Full-domain exhaustion (C9)

- `ROUND_EXHAUSTED` requires accepted full-domain coverage (`accepted_searched = domain`) with
  `active_unsearched = 0` and `inactive_unsearched = 0`; reported coverage alone is
  insufficient; adversarial claims need a defined adjudication outcome (modeled acceptance, not
  proof) — PASS (`FullRangeExhaustNoSolution`, ROUND_STATE_MACHINE §2.8).

## Result
**COVERAGE-LEDGER AUDIT: PASS** — three layers separated; I8a uses accepted coverage only;
reassignment is suffix-only; completed ranges are never reassigned; refresh creates original
assignments; full-domain exhaustion needs accepted coverage.
