# Stage 1AI — Terminal-Publication-Result Propagation Audit (AI6)

**Scope.** This audit verifies correction **AI6** — *propagate the next-bootstrap failure to the run
controller* — of the BlockSim/PoCol Stage-1 protocol against the FINAL normative tree. It is a
documentation-only formal-spec verification: no source, config, DOCX, PDF, or any Stage-1A..1AH artifact
was read or modified, and no experiment was run. Every anchor below is an exact `file:line` reference into
the single normative pseudocode document:

`docs/thesis_revision_v45/stage_01/STAGE_01_PROTOCOL_PSEUDOCODE.md`

Procedures inspected (via `grep -n`): `CloseRoundAssignments`, `PublishTerminalRoundAndSeatNext`,
`RunEventLoopToHorizon`, `ValidBlockAccept`, `RoundAbort`, `CloseRoundAtHorizon`, `STRUCTURE RunContext`,
`RunInitialise`.

---

## 1. Defect statement

In the pre-AI6 (AH-era) tree, `CloseRoundAssignments` invoked the single terminal-round publication owner
`PublishTerminalRoundAndSeatNext` — the procedure that records the round-terminal time, publishes the
prior terminal round, and (for an ordinary, non-horizon closure with simulated time remaining) mints and
**seats the next round's bootstrap** — but it **DISCARDED that owner's return value**. Because the seating
result was thrown away at the closure tail, a `terminal_round_published_seat_failed(...)` outcome (the next
round could not be seated) never surfaced above the round layer. The run-level driver
`RunEventLoopToHorizon` therefore had no run-level signal that the successor round failed to bootstrap: it
would return to its selection loop with no next-round event ever seated, silently losing the rotation
failure instead of terminating the run under a declared disposition.

The normative tree names this exact defect and marks its removal: `STRUCTURE RunContext` states that
"a discarded publication result (the AH defect) is REMOVED" (line 2945), and the AI6 comments at the
closure tail and the three call sites explicitly identify "the AH defect" as the discarded publication
result (lines 6785, 6911). The publication owner itself still produces a *declared*
`terminal_round_published_seat_failed(BootstrapRequestID, reason)` disposition (line 6971), so the defect
was purely the **loss of that value at the caller**, not a missing failure signal at the producer.

---

## 2. Numbered verification table

| # | Claim (AI6) | Evidence (`STAGE_01_PROTOCOL_PSEUDOCODE.md:line`) | Verdict |
|---|-------------|---------------------------------------------------|---------|
| 1a | `CloseRoundAssignments` CAPTURES the publication result: `SET pub <- CALL PublishTerminalRoundAndSeatNext(...)` | `6914` | PASS |
| 1b | It STORES it in `RunContext.terminal_publication_result` | `6915` (`SET RoundContext.RunContext.terminal_publication_result <- pub`) | PASS |
| 1c | On `terminal_round_published_seat_failed` it sets `RunContext.next_round_bootstrap_status <- NEXT_ROUND_BOOTSTRAP_FAILED` | `6916`–`6917` (guard `IF pub = terminal_round_published_seat_failed(_, reason)` → set), corroborated by `6918` (`RECORD next_round_bootstrap_failed(...)`) | PASS |
| 1d | It RETURNS `closure_record(publication_result = pub)` | `6919` (RETURN) and `6920` (`RETURNS: closure_record(publication_result)`) | PASS |
| 2a | `STRUCTURE RunContext` declares `terminal_publication_result` | `2941`–`2945` (field + AI6 note; the three declared shapes at `2943`–`2944`) | PASS |
| 2b | `STRUCTURE RunContext` declares `next_round_bootstrap_status` in `{OK, NEXT_ROUND_BOOTSTRAP_FAILED}` | `2946`–`2953` (`run-level state in { OK, NEXT_ROUND_BOOTSTRAP_FAILED }`) | PASS |
| 2c | `RunInitialise` initialises them (`null` / `OK`) | `3097` (`terminal_publication_result <- null`), `3098` (`next_round_bootstrap_status <- OK`) | PASS |
| 2d | `RunInitialise` includes both in RETURNS | `3132` (`terminal_publication_result = null, next_round_bootstrap_status = OK, # AI6`) | PASS |
| 3a | `RunEventLoopToHorizon` inspects `next_round_bootstrap_status` | `537`–`541` (`IF RunContext.next_round_bootstrap_status = NEXT_ROUND_BOOTSTRAP_FAILED:`) | PASS |
| 3b | On `NEXT_ROUND_BOOTSTRAP_FAILED` it TERMINATES via `FinalizeSimulationRun` on the terminal predecessor | `543` (`SET RoundContext <- RunContext.current_round_context` — the terminal predecessor) then `544` (`CALL FinalizeSimulationRun(RunContext, RoundContext)`) | PASS |
| 3c | It RETURNs the declared PARTIAL-RUN disposition `run_completed_partial(next_round_bootstrap_failed)` | `545` (RETURN); recorded at `542` | PASS |
| 3d | Its RETURNS union includes `run_completed_partial` | `562` (`... | run_completed_partial(next_round_bootstrap_failed)   # AI6`) | PASS |
| 4a | `ValidBlockAccept` CAPTURES the closure record and inspects/asserts `clo = closure_record(publication_result = RoundContext.RunContext.terminal_publication_result)` | `6783` (`SET clo <- CALL CloseRoundAssignments(...)`), `6789` (ASSERT) | PASS |
| 4b | `RoundAbort` CAPTURES + asserts the same equality | `7287` (`SET clo <- CALL ...`), `7293` (ASSERT) | PASS |
| 4c | `CloseRoundAtHorizon` CAPTURES + asserts the same equality | `7419` (`SET clo <- CALL ...`), `7424` (ASSERT) | PASS |
| 4d | `CloseRoundAtHorizon` ADDITIONALLY asserts the horizon publication is `terminal_round_published_no_seat` | `7425` (`ASSERT RoundContext.RunContext.terminal_publication_result = terminal_round_published_no_seat(RoundID)`) | PASS |
| 5a | The chosen deterministic policy is terminate-partial (stated) | `539`–`540` (`The DETERMINISTIC policy is terminate-partial`), `2948`–`2951` | PASS |
| 5b | A bounded retry is documented as an ALTERNATIVE (and only an alternative) | `2950`–`2953` (`A bounded retry ... is a documented ALTERNATIVE policy; the chosen deterministic policy here is terminate-partial`) | PASS |
| 5c | No dangling retry field (internal consistency) | No `RunContext` bootstrap-retry field exists (`grep` for `bootstrap_retry`/`retry_at`/`next_round_retry`/`retry_deadline` returns nothing); the only `bounded retry` fields — `maximum_setup_retries` (`3108`) and `setup_retry_generation_by_scope` (`3209`) — belong to the unrelated setup-retry subsystem | PASS |

---

## 3. Explicit check — NO `CloseRoundAssignments` call site discards the result

`CloseRoundAssignments` is the single centralised round-closure path (line 6921). Every *executable* call
of it must bind the returned `closure_record`. Enumerating all executable call sites in the FINAL tree
(`grep -nE "CALL CloseRoundAssignments\("`) yields exactly three, and every one captures the result into
`clo`:

| Caller | Call site | Capture form | Result inspected |
|--------|-----------|--------------|------------------|
| `ValidBlockAccept` (ordinary acceptance, `ROUND_ACCEPTED`) | `6783` | `SET clo <- CALL CloseRoundAssignments(...)` | `6789` ASSERT vs `RunContext.terminal_publication_result` |
| `RoundAbort` (ordinary abort, `ROUND_ABORTED`) | `7287` | `SET clo <- CALL CloseRoundAssignments(...)` | `7293` ASSERT vs `RunContext.terminal_publication_result` |
| `CloseRoundAtHorizon` (horizon close, `ROUND_ABORTED`) | `7419` | `SET clo <- CALL CloseRoundAssignments(...)` | `7424`–`7425` ASSERT (+ `no_seat` assertion) |

There is **no** bare `CALL CloseRoundAssignments(...)` (no un-captured invocation) anywhere in the
document: the same grep that lists the three `SET clo <-` sites returns *no additional* discarding sites.
The recovery-finalising terminations (e.g. `CompleteSecurityRecovery` branch D, the install-fail
continuations) do not call `CloseRoundAssignments` directly — they route through `RoundAbort` (with
`recovery_finalising = true`), so their closure result is captured at the single `RoundAbort` site
(`7287`) like every other abort. The defect (a discarded result) is therefore eliminated at the closure
tail (`6914`–`6919`) and cannot recur at any caller.

**Propagation chain confirmed end-to-end.** The failed rotation now flows:
`PublishTerminalRoundAndSeatNext` returns `terminal_round_published_seat_failed` (`6971`) →
`CloseRoundAssignments` stores it and raises `NEXT_ROUND_BOOTSTRAP_FAILED` (`6915`–`6918`) → the round-layer
caller re-asserts equality with the stored run-level result (`6789` / `7293` / `7424`) → the run controller
`RunEventLoopToHorizon` reads the flag before its next selection (`541`) and terminates the run under the
declared partial disposition (`542`–`545`). At the horizon path the same capture holds but is provably a
no-seat publication (`7425`), so a horizon close never spuriously raises the failed status — consistent with
`PublishTerminalRoundAndSeatNext` returning `terminal_round_published_no_seat` on a `RUN_HOOK` envelope
(`6950`–`6951`).

## 4. Consistency notes (internal coherence)

- **Single-owner invariant preserved.** `PublishTerminalRoundAndSeatNext` remains the one named terminal
  publication + next-bootstrap owner (`6932`, `6974`–`6979`); AI6 changes only how its result is
  *consumed*, not who produces it.
- **Frontier / residency unaffected.** The terminate-partial path finalises against the already-terminal
  predecessor round via the single `FinalizeSimulationRun` settle (`544`); residency between the closure and
  the horizon is still owned solely by `SettleResidencyBoundary` (`6926`–`6928`), so the idle policy within
  PoCol continues to count the idle interval exactly once even when the run ends partial.
- **Result-shape agreement.** `CloseRoundAssignments` RETURNS `closure_record(publication_result)`
  (`6920`); all three callers assert precisely that shape against the stored
  `RunContext.terminal_publication_result` (`6789` / `7293` / `7424`) — no bare token, no aliasing.
- **Policy is closed, not dangling.** The `RunContext` note commits to terminate-partial and explains why a
  run-loop re-seat is rejected (it would blur the AI8 `TERMINAL_ROTATION`-vs-`DRIVER` origin truthfulness),
  and no retry field, deadline, or counter for the next-round bootstrap is declared anywhere
  (`2950`–`2953`). The alternative is documented as prose only — internally consistent.

---

## 5. Overall verdict

**PASS.** All five AI6 claims are fully realised in the FINAL normative tree with exact anchors, and the
governing safety property — that no `CloseRoundAssignments` call site discards the publication result — holds
at every one of the three (and only three) executable call sites. The pre-AI6 defect (a discarded
next-bootstrap result that never reached the run controller) is eliminated at the closure tail and
propagated deterministically to `RunEventLoopToHorizon`, which terminates the run under the declared
`run_completed_partial(next_round_bootstrap_failed)` disposition. No genuine FAIL was found; no dangling
retry field exists.
