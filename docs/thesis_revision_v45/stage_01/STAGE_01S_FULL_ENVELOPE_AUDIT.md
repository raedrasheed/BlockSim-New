# STAGE 01S — Full Transition-Envelope Audit (Correction S1)

**Scope.** Documentation-only audit of Stage-1S correction **S1 — one explicit
transition-envelope object** — for the idle policy within PoCol. Source of truth (unmodified):
`STAGE_01_PROTOCOL_PSEUDOCODE.md`, §0.9 `ApplyMinerStateTransition`, §0.7d `ProcessEventTime`,
§20b `CloseRoundAtHorizon`, §17a `CloseRoundAssignments`, §7 `EnterLowPowerListen`. No consensus
feature is added, altered, or removed; S1 is purely an identity/threading correction.

## S1 — statement of the correction

`ApplyMinerStateTransition` now takes ONE explicit object in place of R3's decomposed numeric inputs:

```
ApplyMinerStateTransition(MinerID, old_state, new_state,
                          transition_envelope, reason,
                          assignment_ref, candidate_id, propagation_id)
```

The object carries the COMPLETE dispatch identity:

```
transition_envelope = { envelope_namespace, event_time, delta_cycle, event_seq, hook_id }
```

Step **(0) S1 DESTRUCTURE** (§0.9) unpacks it into exactly those five identity fields, and BOTH the
`TransitionEventID` (step 1) and the malformed-envelope guard (step 4) are built EXCLUSIVELY from
them — there is no other identity source. The R3 clause that let namespace fields "travel implicitly"
alongside a numeric-only call site is **WITHDRAWN**: no identity field is decomposed and none is
omitted at any executable call site. There is no positional shorthand; a call of the form
`ApplyMinerStateTransition(..., now, reason=...)` is not permitted, and no call reads
`EQ.current_event_time`/`current_delta_cycle`/`current_event_seq` implicitly.

**Contract.** EVERY call site passes EXACTLY `transition_envelope = dispatch_envelope`. That envelope
is EITHER an ordinary/driver dispatch envelope (`envelope_namespace = ORDINARY_EVENT`,
`hook_id = null`), materialised by `ProcessEventTime` (§0.7d, line 220: `SET dispatch_envelope <- {
envelope_namespace = ORDINARY_EVENT, hook_id = null, event_time = t, delta_cycle =
current_delta_cycle, event_seq = seq(e), ... }`), OR the single RUN_HOOK horizon envelope
(`envelope_namespace = RUN_HOOK`, `hook_id = HorizonHookID`), minted by `CloseRoundAtHorizon` (§20b).

## TransitionEventID tuple (§0.9, step 1)

Built from the destructured envelope PLUS the transition-specific fields, in this order:

```
TransitionEventID = ( envelope_namespace, hook_id,             # from transition_envelope (R3)
                      event_time, delta_cycle, event_seq,       # from transition_envelope
                      MinerID, old_state, new_state, reason,     # transition-specific
                      AssignmentID(assignment_ref),
                      assignment_version(assignment_ref),
                      candidate_id, propagation_id )
```

The id enters `applied_transition_registry` ONLY inside the atomic apply (step 5); a suppressed
replay or a rejected (stale/illegal/malformed) event never registers. A RUN_HOOK envelope missing its
`hook_id` is rejected at step 4 (`envelope_namespace = RUN_HOOK AND hook_id = null`).

## The 14 direct `CALL ApplyMinerStateTransition(...)` sites

Every site below passes `transition_envelope = dispatch_envelope` verbatim (confirmed at each line).

| # | Procedure (§) | Edge (old_state → new_state) | reason | envelope |
|---|---|---|---|---|
| 1 | `StartWake` (§0.10, L981) | from_state → WAKING | wake_start | ORDINARY_EVENT |
| 2 | `WakeCompleteEvent` (§0.10, L1027) | WAKING → ACTIVE_HASHING | ramp_complete | ORDINARY_EVENT |
| 3 | `WakeCompleteEvent` (§0.10, L1037) | WAKING → OFFLINE | wake_deadline_expiry | ORDINARY_EVENT |
| 4 | `MinerRegister` (§3, L1504) | NONE → REGISTERED | register | ORDINARY_EVENT |
| 5 | `MinerRegister` (§3, L1507) | REGISTERED → RESERVE | admit_to_reserve | ORDINARY_EVENT |
| 6 | `ExhaustionAdjudicate` (§6, L1696) | ACTIVE_HASHING → EXHAUSTED_PENDING | RANGE_EXHAUSTED | ORDINARY_EVENT |
| 7 | `EnterLowPowerListen` (§7, L1781) | from_state → LOW_POWER_LISTEN | stop_reason | ORDINARY_EVENT **or** RUN_HOOK† |
| 8 | `AdversarialParticipationChangeEvent` (§8a, L1865) | ACTIVE_HASHING → OFFLINE | adversarial_withdrawal | ORDINARY_EVENT |
| 9 | `AdversarialParticipationChangeEvent` (§8a, L1884) | OFFLINE → REGISTERED | adversarial_rejoin | ORDINARY_EVENT |
| 10 | `LeaseExpiry` (§12, L2838) | WAKING → OFFLINE | lease_expired_while_waking | ORDINARY_EVENT |
| 11 | `CloseRoundAssignments` (§17a, L3450) | EXHAUSTED_PENDING → LOW_POWER_LISTEN | RANGE_EXHAUSTED | ORDINARY_EVENT **or** RUN_HOOK† |
| 12 | `CloseRoundAssignments` (§17a, L3466) | WAKING → OFFLINE | round_closed_while_waking | ORDINARY_EVENT **or** RUN_HOOK† |
| 13 | `CloseTemplateAssignments` (§19, L3580) | EXHAUSTED_PENDING → LOW_POWER_LISTEN | RANGE_EXHAUSTED | ORDINARY_EVENT |
| 14 | `CloseTemplateAssignments` (§19, L3590) | WAKING → OFFLINE | template_refresh_wake_abort | ORDINARY_EVENT |

† Sites 7, 11, 12 execute one body regardless of namespace: the caller decides which envelope flows
in. At an ordinary closure the caller threads an ORDINARY_EVENT dispatch envelope; at a horizon close
the caller threads the RUN_HOOK horizon envelope (`hook_id = HorizonHookID`). The code is identical;
only the passed `transition_envelope` object differs, which is precisely the S1 guarantee.

## The RUN_HOOK horizon thread (§0.7d → §20b → §17a → §7 / §0.9)

`ProcessEventTime(T)` drains the horizon time to quiescence, then — if the round is still nonterminal
— makes the direct run-level CALL `CloseRoundAtHorizon(RoundContext, RunHookContext)` between the
drain and the epilogue (§0.7d, L233–234). `CloseRoundAtHorizon` mints ONE deterministic envelope:

```
horizon_envelope = { envelope_namespace = RUN_HOOK, event_time = run_horizon_T,
                     delta_cycle = RUN_HOOK_CYCLE, event_seq = run_hook_seq,
                     hook_id = HorizonHookID }              # HorizonHookID = (RunID, run_horizon_T, HORIZON_CLOSE)
```

and passes it as `dispatch_envelope` to `CloseRoundAssignments` (§17a). §17a threads the SAME object
unchanged to every nested `EnterLowPowerListen` (§7) and `ApplyMinerStateTransition` (§0.9) — its
`envelope_namespace = RUN_HOOK` and `hook_id = HorizonHookID` are PRESERVED end-to-end (§20b R3 note,
L3819–3822). Each nested transition therefore carries the RUN_HOOK namespace and HorizonHookID in its
`TransitionEventID`, and the horizon-close hook is idempotent per run via its IN_PROGRESS/APPLIED
state, so a partial invocation can never replay as a second full close.

## Distinctness note

An ORDINARY_EVENT transition and a RUN_HOOK (horizon-close) transition with IDENTICAL numeric
`(event_time, delta_cycle, event_seq)` still produce DISTINCT `TransitionEventID`s, because the
envelope object's `envelope_namespace` differs (ORDINARY_EVENT vs RUN_HOOK) and, for the horizon
transition, `hook_id = HorizonHookID` is present rather than `null`. Both leading tuple positions
enter the id, so the two are never confused by the replay guard or the applied registry — collision
freedom derives from the namespace TAG, not from any magic delta-cycle number (§0.2 Q6; §0.9 R3
note). This is exactly why S1 forbids decomposing the envelope to only the numeric three: dropping
`envelope_namespace`/`hook_id` would have collapsed these two genuinely distinct transitions onto one
id.

## Baseline invariance

The A1 energy baseline **8.420833333 kWh is UNCHANGED**. S1 is an identity/threading correction to how
a transition is *named* (one explicit envelope object instead of decomposed numeric fields); it never
alters how time or energy is counted. Residency accrual (`P_state * Δt`), one-shot boundary energy
(`E_transition`/`E_coordination`), and the census recomputation in `ApplyMinerStateTransition` step 5
are byte-for-byte the same operations they were before S1; only their identity plumbing is now a single
object. No new consensus feature is introduced.

## Result

S1 is fully realised and internally consistent. `ApplyMinerStateTransition` accepts ONE
`transition_envelope` object, destructures it in block (0), and builds `TransitionEventID`
EXCLUSIVELY from that object plus the transition-specific fields; R3's implicit-namespace escape hatch
is withdrawn. All **14** direct call sites — enumerated above across `StartWake`, `WakeCompleteEvent`,
`MinerRegister` (×2), `ExhaustionAdjudicate`, `EnterLowPowerListen`,
`AdversarialParticipationChangeEvent` (×2), `LeaseExpiry`, `CloseRoundAssignments` (×2), and
`CloseTemplateAssignments` (×2) — pass exactly `transition_envelope = dispatch_envelope`, with no
decomposed or omitted identity field anywhere. The horizon path preserves the same RUN_HOOK envelope
and HorizonHookID through `CloseRoundAtHorizon → CloseRoundAssignments → EnterLowPowerListen /
ApplyMinerStateTransition`, so every horizon-close transition is provably distinct from any ordinary
transition sharing its numeric coordinates. The A1 baseline 8.420833333 kWh is unchanged. This is a
documentation-only audit of the idle policy within PoCol; no consensus behaviour is modified.

The prohibited rebranded-algorithm-name variants are not used anywhere in this document.
