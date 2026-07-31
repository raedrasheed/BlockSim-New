# Stage 1J — Supersession Register (implementation-handoff lock)

This register records, in ONE place, every Stage-1J statement that supersedes a prior-stage statement,
so that **no historical Stage-1A..1I artifact is rewritten**: the prior files remain frozen evidence,
and the corrections live here and in the un-suffixed normative documents.

Name remains **PoCol**; mechanism is **the idle policy within PoCol**. No property is claimed; the A1
baseline (`8.420833333 kWh`) is unchanged; no new consensus feature is introduced.

## Supersession entries

| # | Prior statement (frozen source) | Superseded by (Stage 1J) | Nature |
|--:|----------------------------------|---------------------------|--------|
| 1 | Stage-1I `HandlePropagationFailure` step (3) `SET security_census_dirty[now] <- true` (defensive) | J1: REMOVED. Candidate failure changes no ACTIVE_HASHING census and sets no dirty flag; only the later re-activation boundaries do, via `ApplyMinerStateTransition` (the SOLE writer, dirty+latest written atomically). Invariant: `dirty[t] ⇒ latest[t] exists`, asserted by the epilogue. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§0.9/§16 | correction (no false dirty; coherence invariant) |
| 2 | Stage-1I `ApplyMinerStateTransition` PRECONDITIONS listing `old_state = miner_state(MinerID)` as a top-level precondition, with the replay guard inside EFFECTS step (0) | J2: the replay guard (by `TransitionEventID`) is step (1), evaluated BEFORE the old-state precondition (step (2), non-replay only). An exact replay returns `duplicate_suppressed` without reading `old_state` or charging energy. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.9 | correction (replay before precondition) |
| 3 | Stage-1F..1I `ApplyMinerStateTransition` INPUT `candidate_ref` (single, ambiguous) and TransitionEventID using `CandidateID(candidate_ref)?, PropagationID(candidate_ref)?` | J3: explicit `candidate_id` AND `propagation_id` inputs; every candidate-triggered caller passes both; the `TransitionEventID` carries both, distinguishing propagation attempts of one CandidateID. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.9, `EnterLowPowerListen` | correction (complete envelope; no candidate_ref ambiguity) |
| 4 | Stage-1H/1I event envelope `seq` described as "a strictly monotonic per-run creation counter" without a named owner or initialisation path | J4: the ONE per-run `event_creation_seq`, owned SOLELY by `ScheduleEvent`, initialised at run start and preserved across rounds (I-04), assigned atomically after ordering; no ambient seq. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2/§0.8/§1 | correction (explicit seq ownership) |
| 5 | Stage-1I: no named next-round participant path (a `LOW_POWER_LISTEN` miner parked by `ROUND_ACCEPTED`/`ROUND_ABORTED` had no executable route to the next round) | J5: `PrepareParticipantsForNewRound` (ASSIGNMENT phase) binds fresh `ORIGINAL`/`REASSIGNED` `PENDING` under the new `RoundID`/`TemplateID` via T3/T4/T10 before `ASSIGNMENT → HASHING`, never reopening a CLOSED old-round assignment. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §2a | addition (executable participation path) |
| 6 | Stage-1I `SecurityFloorEvaluate`: thresholds evaluated and I16 breach events recorded even in observation-only states (breach recorded then transition suppressed) | J6: round-state applicability is checked BEFORE thresholds; setup/refresh/exhausted states record ONLY a `security_census_observation`; I16 breach events are recorded ONLY in `HASHING`/`SOLUTION_PROPAGATION`/`SECURITY_RECOVERY`. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §9 | correction (no breach in non-applicable states) |
| 7 | Stage-1E..1I ambiguous `CLOSE/SUPERSEDE assignment` operations (EnterLowPowerListen ASSIGNMENT_REVOKED; adversarial exit) | J7: canonical terminal status — `SUPERSEDED` ONLY for atomic same-range renewal; `CLOSED` for every termination (revocation/adversarial withdrawal/abandonment/wake failure/cancellation/round closure/template closure). Adversarial withdrawal: `status = CLOSED`, `custody_status = revoked`, `revocation_reason = adversarial_withdrawal`; zero live heads (I18b). `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§7/§8a; catalogue I18b | correction (unambiguous terminal status) |
| 8 | Stage-1I `latest_security_census[event_time] = (H_active, H_honest, H_adversarial, q_adv)` (no provenance); `FinalizeEventTimeSecurityCensus` attaching the CURRENT `(RoundID, TemplateID, state_version)` to the census | J8: the census is a `census_record` carrying its OWN production epoch (`RoundID_at_census`, `TemplateID_at_census`, `state_version_at_census`, `census_seq`); the epilogue passes the STORED provenance; a stale-context census records `stale_census_observation` and triggers no recovery in a new round/template. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.8/§9 | correction (census provenance) |
| 9 | Stage-1G..1I: scheduling described by bare `SCHEDULE event ...` expressions with no single enqueue contract | J9: `ScheduleEvent` is the sole enqueue interface (rejects finalised event_times, owns `event_creation_seq`, applies the delta-cycle forward rule, attaches the round/template + candidate envelope, inserts by the deterministic total-order key). Every `SCHEDULE` is shorthand for a `ScheduleEvent` call. `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.2/§0.7e | addition (central scheduler contract) |

## Frozen-artifact discipline (A–I lock)

- No `STAGE_01[A-I]_*` file is modified in Stage 1J (verified by `git diff --name-only <base>`; see
  `STAGE_01J_CROSS_DOCUMENT_AUDIT.md`). All prior correction reports, audits, specs, call graphs, and
  test vectors remain byte-frozen; entries 1–9 above are the ONLY sanctioned way their now-superseded
  statements are amended.
- The I-01/I-02 event-time epilogue, the I-03 `TransitionEventID`, the I-04 registry model, and the
  I-05/I-06/I-07 corrections are PRESERVED and refined (not replaced): J1/J8 strengthen the census
  bookkeeping; J2/J3 refine the hook ordering and envelope; J4/J9 name the scheduler and seq owner;
  J5 adds the participation path; J6 tightens floor applicability; J7 disambiguates terminal status.
- Historical invariants (I1..I19, incl. I18a/I18b) are NOT re-opened; Stage 1J adds a J7 note to I18b
  (SUPERSEDED renewal-only / CLOSED zero-live-heads) without altering the frozen definitions.
- The A1 accounting baseline (`8.420833333 kWh`) and the difficulty-fixed rule (I12) are unchanged; no
  energy, security, fairness, or incentive property is claimed.
