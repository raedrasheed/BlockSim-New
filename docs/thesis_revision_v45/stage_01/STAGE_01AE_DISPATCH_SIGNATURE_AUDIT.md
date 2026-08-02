# Stage 1AE — Dispatch-Signature Audit (AE5)

This audit verifies correction **AE5 — dispatch-envelope signature agreement (Design B)**: `ProcessEventTime` passes
`dispatch_envelope` to a handler **IFF** the authoritative §0.7g-schema declares `recv env = yes` for that
`event_type`, and passes `dispatched_event_ref` **IFF** the schema declares `recv ref = yes` — it NEVER injects a named
argument the handler does not declare. The audit was generated AFTER the normative documents
(`STAGE_01_PROTOCOL_PSEUDOCODE.md`, `STAGE_01_ROUND_STATE_MACHINE.md`, `STAGE_01_TERMINOLOGY.md`) and the Stage-1AE
semantic test vectors (`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, TV262–TV272) were final; it reads them read-only and
modifies nothing. The A1 baseline `8.420833333 kWh` is unchanged, and the binding PoCol naming rule is preserved: the
algorithm is **PoCol** and the mechanism under audit is the idle policy within PoCol.

Scope is documentation-only. Line anchors are approximate (`~L`). Quotes are reproduced verbatim from the current
normative documents. The audit is corroborated throughout by TV265 (`STAGE_01AE_SEMANTIC_TEST_VECTORS.md`, ~L43–L49),
the vector that exercises the `BlockAcceptancePoint` no-undeclared-argument property (AE4/AE5), and its coverage twin
TV266 (whole-schema agreement).

The exact dispatch line under audit (`PROCEDURE ProcessEventTime`, `STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L245–L247):

```
DISPATCH record.event_type WITH immutable_payload = record.immutable_payload,
         (AND dispatch_envelope = ctx.dispatch_envelope IFF §0.7g-schema[record.event_type].recv_env = yes),
         (AND dispatched_event_ref = ctx.dispatched_event_ref IFF §0.7g-schema[record.event_type].recv_ref = yes)   # AE5
```

The dispatcher builds `ctx <- OrdinaryDispatchContext(dispatch_envelope = record.dispatch_envelope,
dispatched_event_ref = er)` (~L231) from the trusted stored record, but the DISPATCH statement above supplies each of
`dispatch_envelope` / `dispatched_event_ref` to the handler ONLY when the schema row for `record.event_type` declares it.
This is the executable form of the §0.7g-schema narrative (~L789–L799): "the dispatcher passes `dispatch_envelope` to a
handler IFF `recv env` = yes, and `dispatched_event_ref` IFF `recv ref` = yes — it NEVER injects an argument the handler
does not declare", and of the §3.10i AE5 addendum (`STAGE_01_ROUND_STATE_MACHINE.md`, ~L1055–L1058), which states AE5
"closes the AD5 defect whereby `dispatch_envelope` was passed to every ordinary handler including ones (like
`BlockAcceptancePoint`) that do not declare it."

---

## Handler signature agreement (§0.7g-schema row vs handler INPUTS)

Every row of the authoritative §0.7g-schema (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L801–L823) is checked against the
declared INPUTS of its handler procedure. "agree?" is PASS only when the schema `recv env` / `recv ref` flags match the
handler's declared parameters exactly — i.e. the handler declares `dispatch_envelope` IFF `recv env = yes` and
`dispatched_event_ref` IFF `recv ref = yes`, so the dispatch line above can never hand it an undeclared argument.

| Handler (INPUTS anchor) | schema recv env | schema recv ref | INPUTS declare env? | INPUTS declare ref? | agree? |
|-------------------------|:--:|:--:|:--:|:--:|:--:|
| `RoundInitialise` (~L1938) | no | no | no | no | **PASS** |
| `TemplateCommit` (~L2078) | no | no | no | no | **PASS** |
| `PrepareParticipantsForNewRound` (~L2103) | yes | no | yes | no | **PASS** |
| `MinerRegister` (~L2696) | yes | no | yes | no | **PASS** |
| `ReserveActivate` (~L3905) | yes (as `scheduling_context`) | no | yes (as `scheduling_context`) | no | **PASS** |
| `FullRangeExhaustNoSolution` (~L5488) | yes | no | yes | no | **PASS** |
| `HashWorkEvent` (~L2833) | yes | no | yes | no | **PASS** |
| `CertificateArrival` (~L5139) | yes | no | yes | no | **PASS** |
| `BlockAcceptancePoint` (~L5164) | no | no | no | no | **PASS** |
| `AcceptanceBatchFinalize` (~L5284) | yes | no | yes | no | **PASS** |
| `WakeCompleteEvent` (~L1720) | yes | no | yes | no | **PASS** |
| `ResumeFromPause` (~L4990) | yes | no | yes | no | **PASS** |
| `LeaseExpiry` (~L4662) | yes | no | yes | no | **PASS** |
| `AdversarialParticipationChangeEvent` (~L3087) | yes | no | yes | no | **PASS** |
| `ActiveHashRateUpdate` (~L3062) | no | no | no | no | **PASS** |
| `RecoveryDeadlineEvent` (~L3631) | yes | no | yes | no | **PASS** |
| `RecoveryCompletionDueEvent` (~L4041) | yes | no | yes | no | **PASS** |
| `RecoveryAssignmentContinuationDueEvent` (~L4244) | yes | no | yes | no | **PASS** |
| `RecoveryWorkDueEvent` (~L3790) | yes | no | yes | no | **PASS** |
| `SetupRetryEvent` (~L2372) | yes | **yes** | yes | **yes** | **PASS** |

All twenty rows agree. No handler declares an argument the schema withholds, and — crucially for AE5 — the dispatch line
would supply no argument the handler fails to declare. No FAIL: no handler would receive an undeclared argument.

Verbatim corroboration of the key rows:

- `BlockAcceptancePoint` schema row (~L811): `| BlockAcceptancePoint | BlockAcceptancePoint | certificate, snapshot,
  CandidateID, PropagationID, outcome | no | no | FULL_BLOCK_ARRIVAL | (CandidateID, PropagationID) |`. Its handler
  INPUTS (~L5164): `INPUTS: RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` — no
  `dispatch_envelope`, no `dispatched_event_ref`.
- `SetupRetryEvent` schema row (~L822): `recv env` = yes, `recv ref` = **yes**. Its handler INPUTS (~L2372):
  `INPUTS: RoundContext, dispatch_envelope, dispatched_event_ref, …`, with the note (~L2374) "this handler's SIGNATURE
  declares `dispatched_event_ref`, so the dispatcher passes it (AD5 Design B)".
- `ReserveActivate` schema row (~L807): `recv env` = `yes (as scheduling_context)`. Its handler INPUTS (~L3905–L3906):
  `INPUTS: RoundContext, deficit (rate to restore), scheduling_context   # U2: SchedulingSourceContext —
  ORDINARY_DISPATCH(dispatch_envelope) for a dispatched entry point …` — it receives the wrapped
  `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`, never a bare `dispatch_envelope`, exactly as the
  §0.7g-schema narrative parenthetical states (~L796–L797).

---

## Checks (tied to TV265 / TV266)

| Check | Result |
|-------|--------|
| **C1.** The `ProcessEventTime` DISPATCH line passes `dispatch_envelope` IFF `§0.7g-schema[record.event_type].recv_env = yes`, and `dispatched_event_ref` IFF `recv_ref = yes`. | **PASS** — `PROCEDURE ProcessEventTime` (~L245–L247): `DISPATCH record.event_type WITH immutable_payload = record.immutable_payload, (AND dispatch_envelope = ctx.dispatch_envelope IFF §0.7g-schema[record.event_type].recv_env = yes), (AND dispatched_event_ref = ctx.dispatched_event_ref IFF §0.7g-schema[record.event_type].recv_ref = yes)`. Comment (~L242–L244): "No undeclared named argument is injected into any handler." Matches TV266 Expected (~L55–L57): "ProcessEventTime dispatches exactly the row's declared arguments." |
| **C2.** §0.7g-schema declares `BlockAcceptancePoint` with `recv env = no` and `recv ref = no`. | **PASS** — schema row (~L811): `recv env` = no, `recv ref` = no. Matches TV265 Setup (~L46): "§0.7g-schema declares `BlockAcceptancePoint` with `recv env` = no, `recv ref` = no." |
| **C3.** `BlockAcceptancePoint`'s INPUTS omit `dispatch_envelope` (the AD5 defect it closes) AND omit `dispatched_event_ref`. | **PASS** — `PROCEDURE BlockAcceptancePoint` INPUTS (~L5164): `RoundContext, certificate, snapshot, CandidateID, PropagationID, outcome` — neither argument is declared. |
| **C4.** Under the new dispatch line, `BlockAcceptancePoint` is dispatched with its `immutable_payload` ONLY — it does NOT receive `dispatch_envelope` or `dispatched_event_ref`. | **PASS** — C1 dispatch line + C2 (`recv_env = recv_ref = no`) yield only `immutable_payload`. This is exactly TV265 Expected (~L48–L49): "dispatches `BlockAcceptancePoint` with its `immutable_payload` only; it does NOT pass `dispatch_envelope` (nor `dispatched_event_ref`) … No undeclared argument is injected." |
| **C5.** `SetupRetryEvent` is the ONLY handler with `recv ref = yes`, and its INPUTS declare `dispatched_event_ref`. | **PASS** — post-table note (~L825): "`SetupRetryEvent` is the ONLY handler with `recv ref` = yes"; every other schema row shows `recv ref` = no (~L803–L823). Handler INPUTS (~L2372) declare `dispatched_event_ref`; note (~L2381) "a MANDATORY input … ProcessEventTime … always supplies it". |
| **C6.** Sample `recv env = yes` handlers declare `dispatch_envelope`: `HashWorkEvent`, `CertificateArrival`, `WakeCompleteEvent`, `SetupRetryEvent`, and the recovery-due events. | **PASS** — INPUTS declare `dispatch_envelope`: `HashWorkEvent` (~L2833), `CertificateArrival` (~L5139), `WakeCompleteEvent` (~L1720), `SetupRetryEvent` (~L2372), `RecoveryDeadlineEvent` (~L3631), `RecoveryCompletionDueEvent` (~L4041), `RecoveryAssignmentContinuationDueEvent` (~L4244), `RecoveryWorkDueEvent` (~L3790). |
| **C7.** `recv env = no` handlers do NOT declare `dispatch_envelope`: `BlockAcceptancePoint`, `RoundInitialise`, `TemplateCommit`, `ActiveHashRateUpdate`. | **PASS** — INPUTS omit `dispatch_envelope`: `BlockAcceptancePoint` (~L5164), `RoundInitialise` (~L1938: `config …, RunContext, prior_state`), `TemplateCommit` (~L2078: `RoundContext, candidate_template`), `ActiveHashRateUpdate` (~L3062: `RoundContext, time t`). Matches the post-table note (~L826–L828). |
| **C8.** `ReserveActivate` receives the envelope wrapped as `scheduling_context = ORDINARY_DISPATCH(dispatch_envelope)`, not a bare `dispatch_envelope`. | **PASS** — schema row (~L807) `recv env` = `yes (as scheduling_context)`; INPUTS (~L3905–L3906) take `scheduling_context   # U2: SchedulingSourceContext — ORDINARY_DISPATCH(dispatch_envelope) for a dispatched entry point`; narrative (~L796–L797): "the dispatcher supplies that wrapper, not a bare `dispatch_envelope`." |
| **C9.** No handler in §0.7g-schema would receive an argument its INPUTS do not declare (whole-table agreement). | **PASS** — all twenty rows of the handler-signature table above agree; no FAIL, no undeclared-argument site. Matches TV266 Expected (~L55–L57): each schema row's `recv env` + `recv ref` "match that handler's declared INPUTS." |
| **C10.** AE5 is stated identically in the round-state machine, closing the AD5 defect. | **PASS** — `STAGE_01_ROUND_STATE_MACHINE.md` §3.10i (~L1055–L1058): the dispatcher passes `dispatch_envelope` "IFF the schema's `recv env` = yes and `dispatched_event_ref` IFF `recv ref` = yes — never an undeclared argument. This closes the AD5 defect whereby `dispatch_envelope` was passed to every ordinary handler including ones (like `BlockAcceptancePoint`) that do not declare it." Agrees with the pseudocode post-table note (~L827–L828). |

---

## Result

All ten checks PASS with no inconsistency, and every one of the twenty §0.7g-schema rows agrees with its handler's
declared INPUTS. The Design-B dispatch line (`STAGE_01_PROTOCOL_PSEUDOCODE.md`, ~L245–L247) makes argument delivery a
strict function of the authoritative schema: `dispatch_envelope` is supplied IFF `recv_env = yes` and
`dispatched_event_ref` IFF `recv_ref = yes`, so no handler is ever handed an argument it does not declare. The AD5 defect
is closed at its named site: `BlockAcceptancePoint` declares `recv env = no` / `recv ref = no` (~L811), its INPUTS omit
both arguments (~L5164), and under the new dispatch line it receives its `immutable_payload` only — exactly the property
TV265 requires. `SetupRetryEvent` is the sole `recv ref = yes` handler and correctly declares `dispatched_event_ref`;
`ReserveActivate` correctly receives the envelope only as the wrapped `scheduling_context =
ORDINARY_DISPATCH(dispatch_envelope)`, never bare. No handler would receive an undeclared argument; there is no FAIL.
This is a documentation-only audit: no source, config, or test was modified, the A1 baseline `8.420833333 kWh` is
preserved, and the algorithm remains **PoCol** with the idle policy within PoCol as the mechanism under audit.
