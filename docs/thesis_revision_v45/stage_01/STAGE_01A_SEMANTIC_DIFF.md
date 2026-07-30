# Stage 1A — Semantic Diff (before → after)

The semantic change introduced by each correction. Wording is documentation-only; no code.

## CR1 — Early-stop certificate provenance
- **Before:** an early-stop certificate could be generated from aggregated progress
  commitments / searched-domain coverage / claimed exhaustion / a progress frontier.
- **After:** generated **only** after a miner finds a valid candidate solution satisfying the
  target; carries exactly `RoundID, TemplateID, AssignmentID, MinerID, nonce, candidate_hash,
  target, signature/authentication`; progress verification and early-stop certification are
  **completely separate** mechanisms.

## CR2 — Verification-time state
- **Before:** contradiction — miners "do not stop before verification" yet were "removed from
  active hashing during verification."
- **After:** a miner verifying an unverified certificate **remains in `ACTIVE_HASHING`**,
  keeps hashing, stays in `H_active(t)`; verification cost is a separate `E_verification`; the
  miner leaves `ACTIVE_HASHING` only after **all** validation steps pass; a failed certificate
  causes **no** transition. No `VERIFYING` state.

## CR3 — Single normative energy model
- **Before:** grouped model with ambiguous residency powers (RESERVE = `P_offline` in one doc,
  `P_listen` in another) and a `t_other` term without a power.
- **After:** `E_i = Σ_{s} (P_{i,s}·t_{i,s}) + E_transition,i + E_coordination,i +
  E_verification,i` over the eight states; one canonical state-to-power table; `Σ_s t_{i,s} =
  T`; no residual bucket; RESERVE = `P_reserve` (= `P_listen`, not offline).

## CR4 — I8 split
- **Before:** `I8: searched + unsearched + inactive + reassigned = assigned` (mixes a custody
  status into a coverage partition).
- **After:** **I8a** coverage-state partition `searched + active_unsearched + inactive_unsearched
  = assigned_domain` (pairwise disjoint, collectively exhaustive) **and** **I8b** custody model
  `{original, renewed, reassigned, revoked, expired, abandoned}` (orthogonal, non-additive); a
  reassigned position keeps an independent coverage state.

## CR5 — Actual vs reported progress
- **Before:** progress commitments implied verification that no valid solution exists in the
  range.
- **After:** two layers — simulator **ground truth** (`actual_*`) vs protocol **claim**
  (`reported_*`, `audit_*`, `claim_accepted_or_rejected`). The modeled abstraction does not
  prove actual exhaustion; honest sims may use the actual cursor, adversarial sims compare
  reported vs ground truth via the modeled audit. Modeled, not proven.

## CR6 — Competing valid solutions
- **Before:** global-oracle "smallest `(TemplateID, nonce, MinerID)`" as the primary
  accepted-solution rule.
- **After:** network-arrival semantics — earliest valid arrival wins; others recorded
  competing/stale; only exact arrival-time ties break by smallest `candidate_hash` then
  smallest `MinerID`. No chain-wide fork-choice proof.

## CR7 — Stage traceability
- **Before:** implementation/test-stage mappings inconsistent with Stage-0 governance
  (e.g. split Stage 4/5 for progress).
- **After:** Stage 2 core miner states + complete energy accounting; Stage 3 time-varying hash
  rate + security floor + reserve activation; Stage 4 leases + reassignment + modeled progress
  verification; Stage 5 adversarial + incentive; Stages 6–10 as governed.

## CR8 — Energy-reduction attribution
- **Before:** energy savings attributed generically to nonce partitioning.
- **After:** `Delta_E_total = Delta_E_range_idle + Delta_E_reserve + Delta_E_early_stop −
  Delta_E_transition_and_wake − Delta_E_coordination_and_verification`; early-stop saving is a
  propagation/termination optimisation **not unique to partitioning**; total is net of wake,
  transition, coordination, and verification.
