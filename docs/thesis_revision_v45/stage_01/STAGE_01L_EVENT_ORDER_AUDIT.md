# Stage 1L — Event-Order Audit (L3)

Documentation-only audit of correction **L3**: there is exactly ONE canonical same-timestamp order
for solution discovery versus lease expiry in **PoCol** — **discovery first** — and that order is
now stated identically in every place the corpus fixes it. L3 removed a latent CONTRADICTION in
`STAGE_01_PROTOCOL_PSEUDOCODE.md` §21: the §21 inter-type priority table already ordered discovery
(item 7) ahead of lease expiry (item 10), but the §21 "Consequences" prose said the opposite — that
same-timestamp discovery is processed AFTER the lease-expiry decision. L3 deleted the contradicting
prose and replaced it with the canonical rule (discovery BEFORE lease expiry), bringing §21 into
agreement with §0.7 (the timestamp microphase contract) and with the FROZEN authoritative
`STAGE_01G_EVENT_MICROPHASE_SPEC.md` §4, which already stated discovery is processed first. This
deliverable audits wording and event-ordering structure only; it claims **no** security, fairness,
liveness, or incentive property, adds **no new consensus feature**, and concerns the idle policy
within PoCol. No property is experimentally supported at Stage 1. The A1 baseline
(**8.420833333 kWh**) is untouched; any energy change under the idle policy within PoCol is
attributable ONLY to reduced active power-time, and this correction changes no energy quantity.

Binds to `STAGE_01_PROTOCOL_PSEUDOCODE.md` §0.7 (timestamp microphase contract; the PHASE 5+
microphase list places solution-discovery before lease expiry), §21 (Global event-priority contract:
the inter-type priority table with item 7 = Solution discovery and item 10 = Lease expiry, the two
`# L3` annotations, and the `L3 (canonical discovery-before-lease-expiry order)` paragraph that
REPLACED the contradicting prose), §12 `LeaseExpiry` (the L4 status-aware `CASE PAUSED`), §16
`ScheduleSolutionPropagation`, §15 `CreateSolutionEligibilitySnapshot`, §7 `EnterLowPowerListen`,
§0.5/§0.5g (immutable assignment versions; discovery-time acceptance eligibility, I2/E1), and §0.7b
(the G9 stale guard on `HashWorkEvent`); and to `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §2 (microphase
table, phase 6+), §4 (Solution-discovery vs same-time lease expiry — canonical rule), and §5
(required-race table).

---

## 1. The corrected-away contradiction (before → after)

**Before L3 (latent contradiction within §21).** §21 stated the same-timestamp order at two levels:

- The **inter-type priority table** ordered `7  Solution discovery` ahead of `10  Lease expiry`
  (lower number = higher priority = processed first), i.e. discovery BEFORE lease expiry.
- The **"Consequences" prose** then asserted the reverse: that "solution discovery sharing a
  timestamp with a lease expiry is processed AFTER the lease-expiry decision."

The table said discovery-first; the prose said lease-expiry-first. The two statements inside the
SAME section could not both hold, and the prose also contradicted §0.7 (whose PHASE 5+ list places
solution-discovery before lease expiry) and the frozen `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §4
(discovery first). The contradiction was latent — it left the reader unable to determine which event
acts first at a lease boundary — and, taken in the lease-expiry-first reading, it would silently lose
a valid boundary solution (see §4).

**After L3 (single canonical order).** L3 DELETED the contradicting "Consequences" sentence. The
current §21 "Consequences" paragraph names only two consequences of the order — a same-timestamp
full-block arrival is processed AFTER a round closure, and a `WakeCompleteEvent` sharing a timestamp
with round acceptance finds the round already closed (T12) — and makes NO claim about discovery
versus lease expiry. In its place L3 added the paragraph **"L3 (canonical
discovery-before-lease-expiry order)"**, which states: *"Solution discovery (item 7) is processed
**BEFORE** lease expiry (item 10) whenever the two share a timestamp — this is the ONE canonical
order, encoded by the priority numbers and enforced identically here, in `§0.7`, and in the
microphase spec."* Its closing sentence removes any residual ambiguity: *"No statement anywhere in
the corpus places lease expiry before same-timestamp discovery (L3)."* The priority table itself now
carries two `# L3` annotations — `7 Solution discovery … # L3: BEFORE lease expiry` and `10 Lease
expiry … # L3: AFTER solution discovery` — so the table and the prose agree verbatim.

**Confirmed: the lease-expiry-first statement is gone, and no surviving statement places lease
expiry before same-timestamp discovery.**

## 2. The canonical rule

The single canonical rule (identical in all three fixing locations) is:

> At a shared `event_time`, **solution discovery is processed FIRST** and captures its immutable
> `SolutionEligibilitySnapshot` against the version that was `CURRENT` at that instant; the
> same-time lease expiry / renewal is ordered strictly after it.

This is not a new mechanism: it fixes *which event acts first* so that the discovery-time acceptance
eligibility already guaranteed by §0.5/§0.5g (invariant I2, corrected — acceptance binds to the
immutable version that was VALID and `CURRENT` at `discovery_time`, E1) is actually reachable at a
lease boundary. `ValidateCandidate` continues to resolve each certificate against its immutable
discovery snapshot (E1); L3 only guarantees that a validly discovered boundary solution *stays
valid* by ensuring the discovery is captured before the lease can retract the head.

## 3. Consistency across the three fixing locations

| # | Location (current text) | What it says about the same-timestamp order | Discovery-first? |
|--:|---|---|:--:|
| 1 | `STAGE_01_PROTOCOL_PSEUDOCODE.md` **§0.7** — timestamp microphase contract | PHASE 5+ processes, in list order, "certificate arrivals, **solution-discovery**, range completion, reported exhaustion, **lease expiry**, wake completion, resume, periodic monitoring" — discovery precedes lease expiry in the microphase list. | **YES** |
| 2 | `STAGE_01_PROTOCOL_PSEUDOCODE.md` **§21** — Global event-priority contract | Inter-type priority table: `7 Solution discovery (# L3: BEFORE lease expiry)` < `10 Lease expiry (# L3: AFTER solution discovery)`; the `L3` paragraph states discovery is processed BEFORE lease expiry and "No statement anywhere in the corpus places lease expiry before same-timestamp discovery." | **YES** |
| 3 | `STAGE_01G_EVENT_MICROPHASE_SPEC.md` **§4** (frozen, authoritative) — Solution-discovery vs same-time lease expiry | "Single canonical rule: solution discovery is processed FIRST and captures its discovery snapshot BEFORE the same-time lease expiry / renewal." Corroborated by §2 phase 6+ (discovery before lease expiry) and §5 required-race table row "Solution discovery vs lease expiry → Discovery first (§4)". | **YES** |

All three agree on ONE order — discovery first — and no location any longer states the reverse.
§0.7 designates `STAGE_01G_EVENT_MICROPHASE_SPEC.md` as the authoritative same-timestamp contract;
§21 explicitly defers to §0.7 where they might differ ("§0.7 (microphases + epilogue) is
authoritative"); here they do NOT differ. The frozen G spec required no edit under L3 because it was
already discovery-first — L3's work was entirely in §21, deleting the one out-of-line prose sentence.

## 4. Rationale — a boundary discovery stays valid (mechanism: the idle policy within PoCol)

Consider a solution found EXACTLY at a lease boundary — the discovery's `HashWorkEvent` hit and the
holder's `LeaseExpiry` carry the same `event_time`. Under the canonical discovery-first order the
sequence is:

1. **Discovery captures the snapshot against the still-live head.** The `HashWorkEvent` hit
   (§0.7b/G9) invokes `ScheduleSolutionPropagation` (§16), which builds the propagation context and
   binds the immutable `SolutionEligibilitySnapshot` (E1, §15 `CreateSolutionEligibilitySnapshot`)
   to the version that is still `CURRENT` at this instant. Because the version is `CURRENT` when the
   `HashWorkEvent` fires, the G9 stale guard does NOT fire (the guard no-ops a `HashWorkEvent` only
   once the miner is no longer `ACTIVE_HASHING` or the exact version is no longer `CURRENT`).
2. **The finder pauses (PATH B).** `ScheduleSolutionPropagation` then calls `EnterLowPowerListen`
   (§7) with `stop_reason = VALID_SOLUTION_VERIFIED`, recording the candidate's pause cause. The head
   moves to `PAUSED` and remains the lineage's unique live head (I18b); the miner is now
   `LOW_POWER_LISTEN`.
3. **Only THEN does `LeaseExpiry` run.** `LeaseExpiry` (§12) fires next at the same `event_time` and
   finds the head `PAUSED`, so it takes the L4 status-aware **`CASE PAUSED`**: it terminates the
   paused head canonically WITHOUT a wake — `status → CLOSED`, `custody_status = expired`,
   `termination_reason = lease_expiry` — clears the pause bookkeeping, re-classifies the parked
   holder's `entry_stop_reason` to `ASSIGNMENT_REVOKED`, and reassigns ONLY the accepted unsearched
   suffix `[accepted_frontier + 1, range_end]` (never `SUPERSEDED`, never a second live head). This
   close acts on the head AFTER the snapshot was already captured; it **cannot retract the
   already-captured discovery**, because the snapshot resolves to the exact immutable version that
   was `CURRENT` at discovery and stays verifiable even once that version is `CLOSED`/`PAUSED`/
   `SUPERSEDED` (§0.5, E1/I2/I18). The candidate proceeds to acceptance on its own snapshot.

**Why the reverse order is FORBIDDEN.** If `LeaseExpiry` ran first, it would CLOSE/reassign the
version before the same-timestamp discovery is processed. The head would no longer be `CURRENT` (or
would be `PAUSED`/`CLOSED` under a different path), so the discovery's `HashWorkEvent` would then
no-op against a no-longer-live head under the §0.7b/G9 stale guard — silently losing a valid boundary
solution. The canonical discovery-first order is exactly what prevents this loss; the §21 L3
paragraph names this as the reason the reverse order is forbidden.

## 5. Pseudocode verification

| Site | Text in the corpus | Verdict |
|---|---|---|
| §0.7 (microphase contract) | PHASE 5+ list: "…certificate arrivals, **solution-discovery**, range completion, reported exhaustion, **lease expiry**, wake completion, resume, periodic monitoring" | discovery listed before lease expiry |
| §21 priority table | `7  Solution discovery (HashWorkEvent hit -> ScheduleSolutionPropagation)   # L3: BEFORE lease expiry`; `10  Lease expiry (LeaseExpiry)   # L3: AFTER solution discovery` | table encodes discovery-first |
| §21 "Consequences" paragraph | Names only the full-block-after-closure and `WakeCompleteEvent`-after-closure consequences; NO discovery-vs-lease sentence remains | contradicting prose removed |
| §21 "L3" paragraph | "Solution discovery (item 7) is processed **BEFORE** lease expiry (item 10)… No statement anywhere in the corpus places lease expiry before same-timestamp discovery (L3)." | canonical rule stated; reverse ruled out |
| `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §4 | "solution discovery is processed FIRST and captures its discovery snapshot BEFORE the same-time lease expiry / renewal" | frozen spec already discovery-first |
| `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §5 | required-race row "Solution discovery vs lease expiry → Discovery first (§4) → Discovery captures its snapshot before the expiry/renewal; snapshot stays valid" | race resolved discovery-first |
| §16 `ScheduleSolutionPropagation` | builds context, takes E1 snapshot of the still-`CURRENT` head, then `EnterLowPowerListen(stop_reason = VALID_SOLUTION_VERIFIED)` | discovery captures snapshot, finder pauses |
| §12 `LeaseExpiry` `CASE PAUSED` (L4) | `ASSERT miner_state(holder) = LOW_POWER_LISTEN AND entry_stop_reason(holder) = VALID_SOLUTION_VERIFIED`; atomic CLOSE (`CLOSED`/`expired`/`lease_expiry`), clear pause fields, suffix reassign | closes AFTER capture; cannot retract discovery |
| §0.7b (G9 stale guard) | "A pending `HashWorkEvent` becomes a no-op (or is cancelled) once its miner is no longer `ACTIVE_HASHING` or its exact assignment version is no longer `CURRENT`." | reverse order would lose the boundary solution |
| §0.5 / §0.5g (E1/I2) | snapshot "resolves to the exact immutable version that was `CURRENT` at discovery… stays verifiable after renewal even once that version is `SUPERSEDED` or `PAUSED`" | captured discovery stays valid |

No surviving statement in `STAGE_01_PROTOCOL_PSEUDOCODE.md` or `STAGE_01G_EVENT_MICROPHASE_SPEC.md`
orders lease expiry before same-timestamp discovery.

## 6. Acceptance-style PASS checklist

| # | Check | Result |
|--:|-------|--------|
| C1 | There is exactly ONE canonical same-timestamp order for discovery vs lease expiry: **discovery first** (§21 table 7 < 10; §21 L3 paragraph; §0.7; G spec §4) | **PASS** |
| C2 | The order is consistent across §0.7 (microphase list), the §21 priority table, and `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §4 (all discovery-first) | **PASS** |
| C3 | The contradicting §21 "Consequences" statement (discovery processed AFTER lease expiry) is REMOVED; the current §21 prose makes no discovery-vs-lease claim | **PASS** |
| C4 | No corpus statement places lease expiry before same-timestamp discovery (confirmed by the §21 L3 closing sentence and §5 exhaustive check) | **PASS** |
| C5 | A boundary discovery stays valid: `ScheduleSolutionPropagation` (§16) captures the E1 snapshot of the still-`CURRENT` head and the finder pauses BEFORE `LeaseExpiry` runs | **PASS** |
| C6 | `LeaseExpiry` `CASE PAUSED` (§12, L4) closes the paused head canonically (`CLOSED`/`expired`/`lease_expiry`) AFTER the snapshot is captured and cannot retract it (E1/I2/I18, §0.5) | **PASS** |
| C7 | The reverse order is forbidden precisely because the discovery's `HashWorkEvent` would no-op against a no-longer-live head under the §0.7b/G9 stale guard | **PASS** |
| C8 | §0.7, §21, §12, §16, §15, §7, §0.5/§0.5g, §0.7b, and G spec §2/§4/§5 all AGREE; A1 baseline **8.420833333 kWh** unchanged; no new consensus feature; concerns the idle policy within PoCol | **PASS** |

## Result

**EVENT-ORDER AUDIT (Stage 1L): PASS** — correction L3 establishes ONE canonical same-timestamp
order for solution discovery versus lease expiry in **PoCol**, **discovery first**, and removes the
latent §21 contradiction by DELETING the "Consequences" sentence that had said same-timestamp
discovery is processed AFTER the lease-expiry decision, replacing it with the canonical
discovery-before-lease-expiry rule. The order is now stated identically in the §0.7 microphase list,
the §21 priority table (item 7 < item 10, with explicit `# L3` annotations and the L3 paragraph), and
the frozen authoritative `STAGE_01G_EVENT_MICROPHASE_SPEC.md` §4 — and no surviving corpus statement
places lease expiry before same-timestamp discovery. The rationale holds structurally: a boundary
discovery captures its immutable `SolutionEligibilitySnapshot` (E1, §16 `ScheduleSolutionPropagation`
/ §15) against the still-`CURRENT` head, the finder pauses (`VALID_SOLUTION_VERIFIED`, §7), and only
then does `LeaseExpiry` (§12) find the head `PAUSED` and handle it via the L4 `CASE PAUSED` canonical
close (suffix reassign), which cannot retract the already-captured discovery (§0.5, E1/I2/I18); the
reverse order is forbidden because the discovery's `HashWorkEvent` would no-op against a
no-longer-live head under the §0.7b/G9 stale guard, silently losing a valid boundary solution. This
is a documentation-only ordering correction with no new consensus feature and the A1 baseline
(8.420833333 kWh) unchanged; any energy difference under the idle policy within PoCol is attributable
only to reduced active power-time.
