# PoCol Common-Template Revision (final-26 → common-template)

**File:** `PhDThesisRaedRasheed-final26-PoCol-CommonTemplate-Rev.docx`
**Base:** `PhDThesisRaedRasheedFinal26.docx` (uploaded original, unmodified)
**Marking:** every changed or newly inserted passage is colored red (RGB FF0000). No tracked changes. 69 red runs, ≈4,000 words. Unchanged text is untouched.

## Purpose

Addresses the reviewer objection that nonce-space partitioning would not prevent
duplicate computation if miners were allowed to construct different block
headers. The thesis now consistently describes PoCol as a
**common-block-template** consensus mechanism:

> One round → one immutable block template → one TemplateID → disjoint nonce
> ranges → nonce-only search.

## Changes by location

### Abstract (EN + AR)
- Restated the mechanism: all miners of a round mine the same immutable
  canonical block template; nonce is the only mutable field; claim qualified as
  "eliminates duplicate hash inputs among honest miners within a mining round."
- Matching red sentence added to the Arabic abstract.

### Chapter 1 (Background, Problem, Contribution C2)
- Reworded collaborative-mining descriptions and C2 to the precise
  common-template / disjoint-range / duplicate-hash-input formulation.

### Chapter 4 (Redundancy and energy model)
- §4.1/4.2: PoCol coordination now described as common template + nonce-space
  partition; "every miner derives the same canonical block template."
- §4.2/4.4.2: redundancy redefined as repeated evaluation of the same **complete
  hash input** `Hash(BlockTemplate || nonce)`, not duplicate numeric nonces; the
  PoW comparison explicitly labeled a **controlled common-template baseline**
  (no claim that conventional PoW miners always test identical headers).
- R_PoCol = 1 tied to its two conditions (common immutable template + disjoint
  ranges); boundary-of-claim statement added after the energy–latency
  discussion.
- §4.3 threat model: "mining a modified block template" added to
  non-collaborative behaviours.

### Chapter 5 (the main revision)
- §5.1: "same candidate block header" wording replaced with the common-template
  statement.
- §5.5.1: the "PoCol does not explicitly require identical headers" paragraph
  replaced — identical templates are a consensus rule, not an expectation.
- §5.5.2: the four high-level phases rewritten (canonical template construction
  and TemplateID verification; allocation bound to TemplateID; nonce-only
  search; winner publishes the committed template + nonce; exhaustion → new
  round with a new template).
- §5.6.1: round seed changed to `seed_r = H("PoColNonce" || h_{r−1} || r ||
  TemplateID_r)` with explanation; §5.6.3 assignment now determined by
  (M_r, h_{r−1}, r, TemplateID_r); §5.6.4 duplicate-work claim restated as
  no two honest miners evaluating the same (T_r, nonce); §5.6.5 exhaustion
  procedure corrected (no independent timestamp/mempool edits).
- §5.7 genesis round: canonical genesis template + TemplateID_0 derived before
  the seed; winner publishes the committed template.
- **§5.8.2 renamed "Canonical Block Template Construction"** and fully
  rewritten: template contents (prev-hash, round number, version, target,
  deterministic timestamp, ordered transaction list, Merkle root, deterministic
  reward transaction, other consensus-critical fields); deterministic
  transaction ordering (fee density with lexicographic TxID tie-breaking); no
  centralized coordinator; `TemplateID_r = H(BlockTemplate_r)`; the immutability
  sentence; **Common-Template Invariant** stated formally.
- **§5.8.3**: nonce ranges generated for the same TemplateID_r; seed bound to
  the template; ranges pairwise disjoint, covering, verifiable, fixed for the
  round; formal (T_r, nonce) uniqueness argument; **Disjoint-Search Invariant**
  stated formally.
- **§5.8.4**: search is `H(TemplateHeader_r || nonce)` within the assigned
  range only; altering any other field prohibited (creates a different
  TemplateID → rejected); corrected exhaustion procedure (round ends → new
  round number → new deterministic template → verify new TemplateID → new
  ranges → resume only after agreement).
- **§5.8.5**: verification expanded — committed TemplateID, immutable header
  fields, transaction list + Merkle root vs. template, reward transaction vs.
  predetermined T_reward(r), nonce-in-range, PoW target, transaction validity,
  no unauthorized template modification; a valid nonce on a different header is
  not a valid PoCol result for the round.
- **§5.9**: T_reward(r) is deterministic, computed **before** mining, included
  in the common transaction list, committed by the Merkle root, identical for
  all miners; the winner must not create or alter it after finding the nonce
  (may only publish the committed template + nonce + signature). Figure 5.3
  narration and caption corrected accordingly.
- **§5.11.2**: formal duplicate-work definition with domain
  `D_r = {(T_r, n) | n ∈ N_r}`, disjointness/coverage conditions, and
  (T_r, n_i) ≠ (T_r, n_j); new adversarial deviation "mine a modified template";
  modified-template proposals rejected regardless of valid PoW; new paragraphs
  on what the Common-Template Invariant prevents and on the coordination
  requirement (template agreement without a centralized coordinator, TemplateID
  resynchronization, and robust template agreement flagged as an implementation
  requirement / mandatory future extension).
- §5.12 summary aligned with the precise formulation.
- Figures 5.1/5.2 captions annotated (in red) with the common-template
  clarification; figure narrations in §5.6.5, §5.7, §5.9.4 corrected.

### Chapter 6 (Implementation)
- New honest mapping of the prototype to the corrected protocol: the simulator
  keeps one shared round context (one nonce space, one disjoint partition, one
  solution nonce) per parent block — duplicate search work excluded by
  construction — but does **not** build byte-level templates, TemplateIDs, or
  pre-committed reward transactions; explicit common-template enforcement is
  labeled a required protocol correction, not an implemented feature, and noted
  as not affecting the measured results.

### Chapter 7
- §7.6.1 answer to RQ-redundancy qualified with the precise mechanism
  statement; "candidate block activities" wording tightened.

### Chapter 8
- §8.1, §8.2 (RQ1, RQ2) restated with the common-template mechanism and the
  bounded claim (no "eliminates all duplicated PoW computation" wording).
- §8.5 future work: full common-template enforcement in the prototype added as
  the first item.

## Not changed
Experimental results, tables, numerical values, research questions,
references, page layout, and all figure images (embedded bitmaps; the three
Chapter-5 diagrams may optionally be redrawn to show the corrected sequence —
their captions and surrounding narration have been corrected in red).
