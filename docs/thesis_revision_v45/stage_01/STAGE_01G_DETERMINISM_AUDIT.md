# Stage 1G — Determinism Audit (G7)

This audit confirms correction **G7** in the PoCol Stage-1 pseudocode: identifiers are
**deterministic** and every loop that creates, cancels, or schedules events iterates in a
**stable sorted order** over intrinsic keys, so the discrete-event queue order is reproducible
across reruns. It is a structural audit of the specification text (§0.2, §0.7, §0.7a and the
named procedures); no protocol property is claimed or evaluated here.

## 1. Deterministic identifiers

Identifiers are minted deterministically, never as random UUIDs:

- `CandidateID = (RoundID, candidate_discovery_seq)`, where `candidate_discovery_seq` is a
  **per-round monotonic counter** held on `RoundContext` (initialised to `0` in `RoundInitialise`)
  and advanced by exactly one in `CreatePropagationContext` at solution discovery, in deterministic
  discovery order.
- `PropagationID = (CandidateID, propagation_attempt_seq)`, a **per-candidate** monotonic sequence
  (first attempt `= 1`).
- The event-envelope `seq` (§0.2) is a strictly monotonic **per-run** creation counter used ONLY as
  the final deterministic tie-break (§0.7). It is assigned **after** the deterministic order is
  already established, so it never influences the ordering it breaks — it only disambiguates events
  otherwise equal on all intrinsic keys.

No identifier is drawn from randomness; a candidate context is never identified by `RoundID` alone.

## 2. Stable iteration

Every loop that creates, cancels, or schedules events enumerates a **stable sorted** sequence over
intrinsic keys. No loop reads hash-map / set iteration order.

| Procedure | Loop | Stable sorted key |
|-----------|------|-------------------|
| `ScheduleSolutionPropagation` | per-recipient `CertificateArrival` scheduling | recipients SORT by **`MinerID` ascending** |
| `AcceptanceBatchFinalize` | split accepted / failed arrivals | SORT by **`CandidateID` ascending**; winner by (`candidate_hash`, then `MinerID`) |
| `HandlePropagationFailure` | resume paused miners (matching **both** ids) | SORT by **`MinerID` ascending** |
| `ValidBlockAccept` | cancel every other live context's events | SORT by **`CandidateID` ascending** |
| `RoundAbort` | disposition every live context | SORT by **`CandidateID` ascending** |
| `CloseTemplateAssignments` | discard old-template contexts | SORT by **`CandidateID` ascending** |

`AcceptanceBatchFinalize` resume paths and `HandlePropagationFailure` match on **both**
`CandidateID` and `PropagationID`, so only miners paused by the exact candidate are resumed.

## 3. Tie-break

Within one event type at a single `event_time`, ties break by the lexicographic key
`(CandidateID, MinerID, AssignmentID, seq)` (§0.7), NEVER by data-structure iteration order.
Acceptance arbitration (`AcceptanceBatchFinalize` / `ValidBlockAccept`) additionally selects the
winner by `candidate_hash`, then `MinerID`. The `seq` component enters only as the last field,
after the intrinsic keys, and is assigned once the deterministic order is fixed.

## 4. Properties

| # | Property | Result | Why |
|---|----------|--------|-----|
| P1 | Identifiers are deterministic (no UUID) | PASS | `CandidateID = (RoundID, candidate_discovery_seq)`, `PropagationID = (CandidateID, propagation_attempt_seq)`; counters advance monotonically in deterministic order. |
| P2 | All enumerations are stably sorted by intrinsic keys | PASS | Every create/cancel/schedule loop sorts by `MinerID` or `CandidateID` (see §2); none reads hash-map / set order. |
| P3 | `seq` is assigned after ordering is established | PASS | The event-envelope `seq` is the final tie-break only; it is stamped once the intrinsic-key order is fixed (§0.2, §0.7). |
| P4 | Queue order is independent of data-structure iteration | PASS | Ordering derives from intrinsic keys plus the `(CandidateID, MinerID, AssignmentID, seq)` tie-break, not from container traversal order. |
| P5 | Order is identical across reruns with the same seeds/inputs | PASS | Deterministic identifiers, stable sort keys, and reproducible modeled delays make `CandidateID`/`PropagationID` and recipient scheduling order reproduce exactly (TV45). |

## 5. Result

**DETERMINISM AUDIT (G7): PASS**, exercised by **TV45**.
