# Stage 1AF — Integrity Reverse-Binding Audit (AF9)

This audit verifies correction **AF9** ("non-asserting reverse-binding corruption") against the FINAL
Stage-1AF normative tree — specifically `PROCEDURE HandleDispatchIntegrityFailure` and the integrity-path
call site inside `PROCEDURE ProcessEventTime` in `STAGE_01_PROTOCOL_PSEUDOCODE.md`. The concern AF9 closes is
that the prior Stage-1AE contract used a raw `ASSERT` on the reverse ownership binding
(`setup_retry_by_seat_event_ref`); on corrupted ownership metadata that assertion would crash the run rather
than record and drain the corrupt event. AF9 replaces the assertion with an AUDITED, non-mutating,
non-aborting corruption path.

The algorithm remains **PoCol**; the mechanism is the **idle policy within PoCol**; the **A1 baseline
(`8.420833333 kWh`)** is preserved. This is a documentation-only structural-safety correction: no census
value, residency interval, or energy quantity is touched, no new consensus feature is introduced, and no
Stage-1A through Stage-1AE artifact is modified. All line anchors below are into the final
`STAGE_01_PROTOCOL_PSEUDOCODE.md`; the corroborating vector is TV287 in
`STAGE_01AF_SEMANTIC_TEST_VECTORS.md`.

## Verification table

| # | Verification item | Result | Line-anchor citation |
|---|-------------------|--------|----------------------|
| 1 | `HandleDispatchIntegrityFailure` NO LONGER contains a raw `ASSERT setup_retry_records[owner_id] EXISTS AND … seat_event_ref = er` — the raw ASSERT is gone. | **PASS** | Procedure body spans `STAGE_01_PROTOCOL_PSEUDOCODE.md` L362–L425; it contains NO executable `ASSERT` on the owner binding. The owner-binding check is the `IF … RECORD … RETURN` at L387–L391, not an assertion. The only two lines mentioning `ASSERT` are comments that explicitly forbid it: L382 ("NEVER raw-ASSERT it (an ASSERT here would crash the run on corrupted ownership metadata)") and L386 ("(Supersedes the AE6 raw ASSERT — STAGE_01AF_SUPERSESSION_REGISTER.md.)"). |
| 2 | On ANY of {owner record missing, `owner.seat_event_ref != er`, more than one `setup_retry_records` entry has `seat_event_ref = er`} it RECORDS `dispatch_integrity_owner_binding_corrupt(er, owner_id)` and RETURNs `dispatch_integrity_owner_binding_corrupt(er)`. | **PASS** | L387 `IF setup_retry_records[owner_id] does NOT exist`; L388 `OR setup_retry_records[owner_id].seat_event_ref != er`; L389 `OR MORE THAN ONE setup_retry_records entry has seat_event_ref = er:`; L390 `RECORD dispatch_integrity_owner_binding_corrupt(er, owner_id)`; L391 `RETURN dispatch_integrity_owner_binding_corrupt(er)`. All three disjuncts present; RECORD carries `(er, owner_id)`; RETURN carries `(er)`. |
| 3 | The corrupt-binding branch mutates NO retry record and aborts NO round; `ProcessEventTime` then CONSUMEs the queued event (sets CONSUMED and clears context after the call). | **PASS** | Corrupt branch = only L390 (RECORD) + L391 (RETURN); it precedes and thus short-circuits the sole mutation/abort statements (L400/L404/L407 `SetSetupRetryStatus`, L403/L408 `UPDATE`, L401 `RoundAbort`), so none execute — see the in-line rationale at L391 ("no unverified retry mutated; no unrelated round aborted"). Call site: L280 `CALL HandleDispatchIntegrityFailure(...)`, then unconditionally L281 `ATOMICALLY:`, L282 `SET queued_event_registry[er].queue_status <- CONSUMED`, L283 `CLEAR EQ.current_event_time … current_event_ref`, L284 `CONTINUE`. |
| 4 | The RETURNS union includes `dispatch_integrity_owner_binding_corrupt(er)` alongside `dispatch_integrity_handled(er)`. | **PASS** | L415 `RETURNS: dispatch_integrity_handled(er) \| dispatch_integrity_owner_binding_corrupt(er)`. Both members present. |
| 5 | The rest of the AE6 ownership resolution is preserved: owner from `setup_retry_by_seat_event_ref[er]`; foreign-payload-id mismatch audited; no-owner event mutates nothing. | **PASS** | Owner from trusted reverse binding: L380 `IF er is a key of setup_retry_by_seat_event_ref:`, L381 `SET owner_id <- setup_retry_by_seat_event_ref[er]`. Foreign-payload-id mismatch audited (foreign id never touched): L396 `IF the payload's SetupRetryID is PRESENT AND … != owner_id:`, L397 `RECORD setup_retry_owner_mismatch(er, owner_id, payload_setup_retry_id = …)`. No-owner event mutates nothing: L410 `ELSE:`, L413 `RECORD dispatch_integrity_no_owner(er)` (no retry mutation, no abort). Verified-owner disposition remains scoped to the owner's own round: L398–L409. |
| 6 | The corruption handler is SAFE under corrupted ownership metadata — no path can crash on a corrupt binding. | **PASS** | Every path is total. The verification is entered only when the key exists (L380), so `owner_id` is well-defined (L381). In the disjunction, the missing-record test is FIRST (L387), so short-circuit evaluation guards the field dereference at L388 (never dereferenced when the record is absent); the duplicate-ownership test (L389) is a count/scan over existing records and cannot fault. The absent-key case is the separate `ELSE` (L410–L413). No `ASSERT` can abort the run (item 1). The design intent is stated at L382–L386 ("Safe under corrupted ownership metadata") and reaffirmed in the NOTE at L421–L425 ("returns WITHOUT mutating any retry record or aborting any round (safe under corrupted ownership metadata)"). Exercised end-to-end by TV287 ("The run does not crash under corrupted ownership metadata"). |

## Overall verdict

**PASS (6 / 6).** In the final Stage-1AF normative tree, `HandleDispatchIntegrityFailure` no longer
raw-asserts the reverse ownership binding: on a missing owner record, a `seat_event_ref` mismatch, or duplicate
seat ownership it RECORDS `dispatch_integrity_owner_binding_corrupt(er, owner_id)` and returns that result
without mutating any retry record or aborting any round, after which `ProcessEventTime` deterministically marks
the corrupt event CONSUMED and clears the dispatch context. The declared RETURNS union admits both
`dispatch_integrity_handled(er)` and `dispatch_integrity_owner_binding_corrupt(er)`. The remaining AE6
ownership resolution — trusted-EventRef owner lookup, foreign-payload-id mismatch audit, and the no-owner
mutate-nothing path — is preserved, and no code path can crash on corrupted ownership metadata. AF9 is
correctly and completely realised; no defect found. The A1 baseline `8.420833333 kWh` is unchanged.
