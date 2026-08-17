# PoCol Consensus Flowchart — Figure 5.5 / Figure 5.6

Publication-quality flowchart package for the Proof-of-Collaboration (PoCol) consensus
algorithm, derived **strictly** from Chapter 5 (Sections 5.1–5.11) of

> R. S. Rasheed, *Proof-of-Collaboration: A Novel Blockchain Consensus Algorithm with
> Highly Efficient Power Consumption*, PhD thesis, The Islamic University of Gaza,
> supervised by Prof. Aiman AbuSamra — working draft `docs/Raed-Rasheed-draft-42-00.docx`.

No protocol step, threshold, decision rule, security property or mechanism appears in these
diagrams that is not stated in that chapter. Mechanisms the thesis specifies but does not
implement or validate are drawn **as such** (dashed boxes and an explicit scope panel), not
silently completed.

## Files

| File | Contents |
|---|---|
| `fig_5_5_pocol_complete.mmd` | Output 2 — complete Mermaid flowchart (paste into <https://mermaid.live>) |
| `fig_5_5_pocol_complete.svg` / `.png` / `.pdf` | Rendered complete figure (vector, 2× raster, vector PDF at natural size) |
| `fig_5_5_pocol_complete_A3.pdf` | Complete figure centred on a single A3 portrait page |
| `fig_5_6_pocol_simplified.mmd` | Output 3 — simplified defence-slide Mermaid flowchart |
| `fig_5_6_pocol_simplified.svg` / `.png` / `.pdf` | Rendered simplified figure (vector, 2× raster, vector PDF at natural size) |
| `fig_5_6_pocol_simplified_A4.pdf` | Simplified figure centred on a single A4 portrait page |
| `README.md` | Outputs 1, 4, 5 — specification, caption, defence script, traceability, validation |

**PDF page sizes.** All PDFs are single-page, fully vector, with fonts embedded.

| PDF | Page | Artwork |
|---|---|---|
| `fig_5_5_pocol_complete.pdf` | 600 × 1871 pt (212 × 660 mm) — page fitted to the diagram | full size, ~11 pt type |
| `fig_5_5_pocol_complete_A3.pdf` | A3 portrait, 297 × 420 mm | 128 × 400 mm, scaled 0.61, ~7 pt type |
| `fig_5_6_pocol_simplified.pdf` | 600 × 724 pt (212 × 256 mm) — page fitted to the diagram | full size |
| `fig_5_6_pocol_simplified_A4.pdf` | A4 portrait, 210 × 297 mm | 190 × 230 mm, scaled 0.90 |

The complete figure has a 1 : 3.1 aspect ratio, so it cannot fill a single A3 page: fitting its
height leaves it 128 mm wide with roughly 7 pt type — legible in print, but tight. For a bound
thesis prefer the natural-size PDF as a foldout plate, or split the figure into two plates
(Phases 1–5 and Phases 6–9 plus the scope panel) if a standard page size is required.

**Figure numbering.** Draft 42 contains Figures 5.1–5.4 only (round with an inactive miner;
genesis round; reward distribution; miner leaving). There is no existing Figure 5.5, so the
complete workflow diagram is numbered **Figure 5.5** and the simplified presentation variant
**Figure 5.6**. Figures 5.1–5.4 are sequence-style views of individual scenarios; Figure 5.5
is the first end-to-end algorithmic view of the protocol and supersedes none of them.

Both `.mmd` sources carry a YAML front-matter `config:` block (fonts, colours, wrapping
width). mermaid.live honours it, so the online render matches the committed SVG/PNG.

---

# Output 1 — Detailed flowchart specification

Read this before the code: it is the step-by-step definition the Mermaid source implements.

## 1.0 Conventions

| Symbol | Meaning |
|---|---|
| Rounded (stadium) box | Start / terminal / return connector |
| Rectangle | Process step |
| Diamond | Decision |
| Dashed-border box | Invariant, assumption, scope statement or stated limitation — **not** a protocol step |
| Light-blue fill, heavy border | Core PoCol innovation (template, TemplateID, seed, ordering, ranges, disjoint search, pre-committed reward) |
| Grey fill | Verification checks and reward arithmetic |
| Solid arrow | Control flow |
| Dotted arrow | Annotation attachment or non-control dependency |

Colour is decorative only: every distinction survives greyscale printing, because the core
steps also carry a heavier border weight and the annotations a dashed border.

Loops that would otherwise span the whole page (round cycle, no-solution restart, rejected
block) are drawn with labelled **return connectors** (`↺ RETURN TO PHASE …`) rather than
page-length back-arrows. This is standard algorithm-flowchart practice and keeps the A3 page
free of crossing edges; the cycle is stated explicitly in each connector's text.

## 1.1 Phase 1 — System initialisation / genesis round (r = 0) — §5.7

Kept visually distinct (grey panel, lighter borders) so it does not dominate the normal-round
spine, and exited exactly once.

1. **Initialise PoCol protocol parameters** — protocol version, difficulty target `D₀`,
   permitted nonce-domain size `N_max`, block subsidy `R_blk`, reward function `f_r`,
   transaction-collection window `Δ_tx`.
2. **Establish the genesis blockchain state**, initial balances and ledger state (§5.7.1).
3. **Register the founding miner set `M₀`** — public key, network address, reward address.
   The thesis admits either bootstrapping route: a bootstrapping authority/consortium that
   selects founding miners and allocates first tokens, or the more decentralised route in
   which the first miner self-registers and then validates and admits the others (§5.7.1–5.7.2).
4. **Decision — all miners agree on `M₀` before nonce-domain distribution?** §5.7.2 makes
   this a precondition ("it is essential that all the miners have to agree upon M₀ prior to
   start nonce domain distribution"). *No* → return to registration and reconcile `M₀`.
5. **Derive the canonical genesis block template** `BlockTemplate₀` and the nonce-free
   `HeaderTemplate₀`, including the initial reward-distribution transaction and any bootstrap
   transactions. The template is identical for every miner (§5.7.3).
6. **Compute `TemplateID₀`** over the canonical template representation with the nonce
   excluded or fixed to its canonical placeholder (§5.7.3).
7. **Decision — every miner verifies `TemplateID₀`?** *No* → recompute / re-verify the
   template. *Yes* → proceed. §5.7.3: "Every miner verifies TemplateID₀ before beginning
   proof-of-work evaluation."
8. **Compute the genesis round seed**
   `seed₀ = H("PoColNonce" ‖ genesis_hash ‖ 0 ‖ TemplateID₀)` (§5.7.3).
9. **Deterministic nonce-domain allocation** — tickets, ordered list `L₀`, disjoint ranges
   `R₀(mᵢ)`, exactly as in §5.6.
10. **Start the first collaborative search** — instantiate `Header₀(n)` for `n ∈ R₀(mᵢ)`.
11. **Decision — `H(Serialize(Header₀(n))) ≤ Target`?** *No* → next nonce in range. A dashed
    note records that genesis obeys the same round rules, so exhaustion without a solution
    yields a new template and a new round (§5.8.4) — the genesis path is not given a
    special-case escape.
12. **Verify and commit `B₀`** — the winner publishes the committed template instantiated
    with the successful nonce; other miners verify the complete header, the proof of work,
    the transactions and the template commitment before accepting `B₀` (§5.7.3).
13. **Initialise `S(B₀)`** with balances and `M₀`, then **move to normal PoCol rounds**
    (`r ← 1`) (§5.7.4).

## 1.2 Phase 2 — Round start and committed-state read (r ≥ 1) — §5.8.1

14. **Round `r` starts deterministically the moment `B_(r−1)` is accepted** (§5.8.2, first
    sentence of the transaction-window paragraph).
15. **Read the committed state `S(B_(r−1))`**: previous-block header hash `h_(r−1)`, the
    registered miner set `M_r` derived from registration/deregistration transactions up to
    height `r−1`, balances and application-specific data, and the mempool of pending
    transactions.

## 1.3 Phase 3a — Pre-committed collaborative reward distribution — §5.9

Placed **before** template construction, because the thesis requires `T_reward(r)` to be
computed before mining and committed inside the template. The diagram makes the ordering
structural rather than annotational.

16. `R_tot(r) = R_blk(r) + F_tx(r)`  (5.6)
17. `f_r : M_r → [0,1]`, `sᵢ = f_r(mᵢ) ≥ 0`, `Σ_(mᵢ∈M_r) f_r(mᵢ) = 1`  (5.7)
18. `Reward_r(mᵢ) = sᵢ · R_tot(r)`  (5.8)
19. Equal-sharing baseline `f_r(mᵢ) = 1/|M_r|`  (5.9)
20. **Build `T_reward(r)`** — one output per `mᵢ ∈ M_r` paying `Reward_r(mᵢ)` to that miner's
    registered on-chain reward address; inputs are the newly created subsidy `R_blk(r)` and
    the collected fees `F_tx(r)`; placed first in `B_r` by convention (§5.9.1).
21. Dashed note: computed **before** mining from `S(B_(r−1))` and the protocol rules; the
    baseline membership rule pays every registered miner including inactive ones, and
    activity-filtered variants over `M̃_r ⊆ M_r` with renormalised shares are an explicitly
    optional deployment variant (§5.9.3).

The output of this phase feeds step 25 (embedding in the template).

## 1.4 Phase 3b — Canonical common-template construction — §5.8.2

The most prominent block of the diagram (heaviest panel border).

22. **Open the bounded transaction-collection window `Δ_tx`**; pending transactions are
    exchanged by normal gossip.
23. **Eligible transaction set** — received before the cutoff **and** valid with respect to
    `S(B_(r−1))`; later arrivals stay in the mempool for later rounds.
24. **Deterministic selection and ordering** — decreasing fee density up to the block-size
    limit, ties broken by lexicographic transaction identifier. A dashed note records that
    this is a *proposed protocol requirement* of Chapter 5 and that the Chapter 6 prototype
    sorts by decreasing fee only, after the winning event, with no cross-miner agreement step.
25. **Merkle root** over the ordered list; then **embed `T_reward(r)`** from Phase 3a.
26. **Assemble the canonical `BlockTemplate_r`** — previous-block hash, round number,
    protocol version, difficulty target `D_r`, deterministic timestamp, ordered transaction
    list, Merkle root, reward-distribution transaction, and every other consensus-critical
    field, with the nonce excluded.
27. **Derive the nonce-free `HeaderTemplate_r`** — only the nonce field may vary during the
    active round.
28. **Compute** `TemplateID_r = H(Encode(BlockTemplate_r without a round-specific nonce value))`.
29. **Decision — does the locally derived `TemplateID_r` equal the network-consistent value
    announced by peers?**
    - *No* → **do not begin authorised mining**; reconcile the transaction/template view by
      requesting missing transactions by identifier, validating them and discarding
      ineligible ones; **recompute / re-verify** the template; return to the `TemplateID_r`
      check. (§5.8.2: "Mining in round r may begin only after the miner has verified that its
      TemplateID_r equals the network-consistent value.")
    - *Yes* → **freeze the template**; `BlockTemplate_r` and `HeaderTemplate_r` are immutable
      for the round.
30. Dashed annotations attached here:
    - **Common-Template Invariant** (§5.8.2), quoted in full.
    - Agreement is reached entirely through peer-to-peer gossip of transactions and template
      identifiers — **no centralised coordinator**.

## 1.5 Phase 4 — Deterministic nonce-domain allocation — §5.6, §5.8.3

31. **Round seed** `seed_r = H("PoColNonce" ‖ h_(r−1) ‖ r ‖ TemplateID_r)`  (5.2), with the
    role of each input labelled: `h_(r−1)` is the previous committed block-header hash, `r`
    the round index, and `TemplateID_r` binds the work assignment to the canonical template.
32. **Per-round ticket** `ticket_r(mᵢ) = H(seed_r ‖ id(mᵢ))` for every `mᵢ ∈ M_r`  (5.3).
33. **Pseudo-random deterministic ordering** — sort by increasing ticket value to obtain
    `L_r = [m₍₀₎, …, m₍n−1₎]` with `ticket_r(m₍₀₎) ≤ … ≤ ticket_r(m₍n−1₎)`, `n = |M_r|`  (5.4).
34. **Integer partition** `start_r(i) = ⌊i·N_max/n⌋`, `end_r(i) = ⌊(i+1)·N_max/n⌋ − 1`  (5.4a, 5.4b).
35. **Assigned range** `R_r(m₍ᵢ₎) = [start_r(i), end_r(i)]`  (5.5).
36. Dashed annotations attached here:
    - **Partition properties** — no overlap `R_r(mᵢ) ∩ R_r(m_j) = ∅ (i ≠ j)`; complete
      coverage `⋃ᵢ R_r(m₍ᵢ₎) = N`; approximately balanced sizes
      `|R_r(m₍ᵢ₎)| ∈ {⌊N_max/n⌋, ⌈N_max/n⌉}`.
    - **Domain clarification** — `N = {0,1,…,N_max−1}` is the *permitted nonce domain* of the
      round (e.g. 2³² or 2⁶⁴ depending on implementation constraints); it is **not** the
      SHA-256 output space. Every honest miner recomputes the ordering and its own range
      locally from public inputs; there is **no trusted range coordinator**.
    - **Disjoint-Evaluation Invariant** (§5.8.3), quoted.

## 1.6 Phase 5 — Collaborative proof-of-work search — §5.8.4

Two parallel lanes leave the allocation phase: the active-miner lane and the inactive-miner
lane.

**Active lane (per miner, all miners in parallel):**

37. Miner `mᵢ` takes **only** nonce values `n ∈ R_r(mᵢ)`.
38. Insert `n` into the nonce field of the common `HeaderTemplate_r` → complete candidate
    header `Header_r(n)`.
39. Compute `H(Serialize(Header_r(n)))`.
40. **Decision — `H(Serialize(Header_r(n))) ≤ Target`?**
    - *Yes* → the miner becomes the **successful proposer** of round `r`: it publishes the
      already committed `BlockTemplate_r` instantiated with `n_success`, **does not modify the
      reward transaction**, and broadcasts the proposed block → Phase 8.
    - *No* → **decision: assigned range exhausted?** *No* → next nonce inside the assigned
      range (loop back to step 38). *Yes* → mark the local assigned range exhausted → Phase 6.
41. Dashed annotation: only the nonce varies within one active round; changing the timestamp,
    the transaction set, the reward transaction or any other consensus-critical field yields a
    different template and is prohibited inside round `r` (§5.8.4).

**Inactive lane (§5.6.5, §5.11.3):**

42. A **registered but inactive miner** (`mᵢ ∈ M_r`, `mᵢ ∉ A_r`).
43. Its range `R_r(mᵢ)` **stays assigned** under the deterministic allocation but may remain
    **unevaluated**.
44. Effective hash rate decreases: `H_eff(r) = Σ_(mᵢ∈A_r) Hᵢ(r) ≤ H_tot(r)` and
    `λ_blk^eff(r) = H_eff(r)·p_succ(D_r)`, giving longer block intervals until the difficulty
    adjustment responds. This lane joins the round-outcome decision in Phase 7.

## 1.7 Phase 6 — Post-range operating policies — §5.6.6

Reached only after a miner's assigned range is exhausted. The two policies are **alternatives**
and the diagram says so, together with the thesis requirement that the choice be identified
explicitly for every experimental or deployment configuration.

45. **Decision — configured post-range operating policy?**
46. **Energy-saving idle policy** (§5.6.6.1): stop active hashing; enter a low-power
    idle/listening state until the end of the current collaborative round; stay connected to
    the network; possibly receive notice that another miner produced a valid block; perform no
    further mining hashes during the remaining round.
47. **Continuous-performance policy** (§5.6.6.2): do not idle; continue with newly assigned,
    non-overlapping work bound to an explicitly identified template or sub-round.
48. Both converge on "wait for a valid block or for the termination of round `r`".
49. Dashed annotations attached here — three separate statements, deliberately not merged:
    - The energy saving is caused by the **active-hashing → low-power** transition and the
      idle duration, **not by nonce partitioning alone**; the policy also lowers the active
      network hash rate, so its effects on block interval, range-exhaustion probability,
      liveness and security must be evaluated together with its savings.
    - At equal aggregate hash rate, hardware efficiency, active power and duration, continuous
      operation is **not** expected to reduce energy; its purpose is performance-oriented and
      any gain must be reported as an empirical result.
    - "End of the current collaborative mining round" denotes the round deadline or target
      block interval defined by PoCol — **not** a multi-block difficulty-adjustment epoch.

## 1.8 Phase 7 — Round outcome: unevaluated ranges and no-solution rounds — §5.6.5, §5.8.4

50. **Decision — all ranges assigned to *active* miners exhausted, no header at or below the
    target, and no valid block received?**
    - *No* (a valid block was received) → Phase 8 verification.
    - *Yes* → **the round ends without a block**, and no miner may alter a non-nonce
      consensus-critical field and continue under the same round identifier.
51. **Create a new round** — derive a new canonical template, compute a new `TemplateID`,
    compute a new round seed, generate new nonce assignments, restart the collaborative
    search; resume only after agreement on the new template. Drawn as a labelled return
    connector to Phase 3a/3b.
52. Dashed annotation, deliberately prominent: **all active ranges exhausted ≠ the permitted
    nonce domain is exhausted**. When a registered miner is inactive, a nonce satisfying the
    target may lie inside its assigned range and never be evaluated in this round; the round
    is then closed and a new round with a new template is generated (§5.6.5).

## 1.9 Phase 8 — Block proposal and verification — §5.8.5

Eight checks, in the order given by §5.8.5, performed independently at every receiving node.

| # | Check | Source |
|---|---|---|
| 1 | Previous-block linkage: `prevhash` matches `B_(r−1)`; the block extends the longest valid chain or a competing chain of comparable length | §5.8.5(1) |
| 2 | Canonical-template conformity: recompute `BlockTemplate_r`, `HeaderTemplate_r`, `TemplateID_r`; every non-nonce consensus-critical field must match | §5.8.5(2) |
| 3 | Transactions and Merkle root match the template, and `T_reward(r)` is identical to the pre-committed transaction | §5.8.5(3) |
| 4 | Successful-nonce range membership: recompute `seed_r`, tickets, `L_r`, ranges; verify `n_success ∈ R_r(m_winner)` | §5.8.5(4) |
| 5 | Transaction validity against `S(B_(r−1))`: no double spending, correct state transitions, valid ledger rules | §5.8.5(5) |
| 6 | Reward-distribution validity: completeness, correctness, conservation, ledger validity | §5.8.5(6), §5.9.2 |
| 7 | Proof of work: `H(Serialize(Header_r(n_success))) ≤ Target`, with header Merkle root and committed fields consistent with `BlockTemplate_r` | §5.8.5(7) |
| 8 | Template identifier: a header meeting the target but built from different non-nonce fields carries `TemplateID ≠ TemplateID_r` and is rejected **regardless of its valid PoW** | §5.8.5 closing paragraph |

53. Dashed annotation on Check 4: this verifies range membership of the **successful**
    candidate header only; it does **not** prove that every non-winning miner searched its
    complete assigned range (§5.8.5, §5.11.5).
54. **Decision — does the block pass all checks?** *No* → reject the block and continue
    according to the current round and chain-selection rules (return connector to Phase 7).
55. *Yes* → the block becomes **eligible for the cumulative-work chain-selection rule**.
56. **Decision — selected by the chain-selection rule as the canonical chain?** *No* → retain
    as a competing branch under standard Nakamoto-style fork resolution (return connector to
    Phase 7). *Yes* → append.

## 1.10 Phase 9 — Commitment, state update and round transition — §5.8.5, §5.10

57. Append `B_r`; update balances in `S(B_r)`, including every reward-distribution output.
58. Process miner registration, deregistration and inactivity-removal transactions → update
    the registered miner set `M_(r+1)`.
59. Remove the confirmed transactions from the mempool.
60. `r ← r + 1`, then the return connector **↺ RETURN TO PHASE 2** closes the round cycle:
    read committed state → build the common template → compute `TemplateID` → generate
    assignments → collaborative search.

## 1.11 Side module — Dynamic miner-set management — §5.4, §5.10

Nested inside Phase 9 and entered from the "process miner-set transactions" step, so it reads
as a side module of the state-update stage rather than an interruption of the main spine.

- **Joining** (§5.4.1, §5.10.1): registration transaction carrying public key/identity,
  network address and reward address → validated and included in block `B_h` → `mᵢ ∈ M(r)`
  for every round `r > h` → receives a nonce range → becomes eligible under the applicable
  reward rule.
- **Explicit leaving** (§5.4.2, §5.10.2): signed deregistration transaction → signature valid
  and miner still in `M_h` → confirmed in a block → removed from the registered set,
  immediately or after `k` blocks depending on protocol settings → no future nonce range and
  no future reward under the baseline membership rule; previously earned rewards remain on the
  ledger.
- **Silent leaving / inactivity** (§5.4.3, §5.10.2): the identity remains registered,
  `Hᵢ(r) = 0`, the assigned nonce range may remain unevaluated, the effective active hash rate
  decreases, and under the baseline equal-sharing rule the miner is still paid until it
  deregisters or is removed.
- **Optional long-term-inactivity removal** (§5.4.4, §5.10.3): if `h − ℓᵢ(h) > Θ_inact` the
  miner becomes eligible for forced removal; any honest node may propose a removal
  transaction, and once included `mᵢ ∉ M(r)` for all subsequent rounds `r > h`.

## 1.12 Protocol scope / unresolved requirements panel

A dashed panel, separated from the control flow, carrying five statements only:

1. Full distributed template agreement — the `Δ_tx` collection window, mempool reconciliation,
   `TemplateID` computation and verification, and pre-committed reward enforcement — is
   **specified** in Chapter 5 but is not implemented as executable checks and has not been
   validated experimentally end to end (§5.8.2, §5.11.2, §6.3, §6.9, §8.5).
2. Range membership of the winning nonce does not prove that non-winning miners searched their
   complete assigned ranges; contribution auditing and contribution verification remain
   incomplete (§5.8.5, §5.11.5).
3. Sybil resistance is not experimentally established; it depends on external registration and
   identity policies — curated membership, or costed registration such as a deposit or a
   registration proof of work (§5.11.4).
4. Incentive compatibility is not established, and quantitative reward fairness has not been
   evaluated; both are stated as future work (§5.12, §8.5).
5. PoW-equivalent common-prefix, chain-growth, chain-quality and double-spend guarantees have
   not been formally proved for the complete common-template protocol; §5.11 gives a
   preliminary informal argument only (§5.11.1, §5.11.5, §5.12).

## 1.13 Visual hierarchy — the ten emphasised elements

Rendered in the blue-accent "core innovation" style (heavy border, tinted fill), so they read
as one family when the figure is skimmed: (1) one immutable canonical block template;
(2) one nonce-free header template; (3) `TemplateID` agreement; (4) deterministic round seed;
(5) pseudo-random deterministic miner ordering; (6) mutually disjoint nonce ranges;
(7) parallel collaborative hash search; (8) successful-nonce range verification;
(9) pre-committed collaborative reward distribution; (10) explicit post-range idle /
continuous operating policies.

---

# Output 2 — Complete Mermaid flowchart

Source of truth: [`fig_5_5_pocol_complete.mmd`](fig_5_5_pocol_complete.mmd). Paste the file
contents directly into <https://mermaid.live>. Syntax validated against Mermaid 11
(`mermaid.parse`) and rendered with `@mermaid-js/mermaid-cli`; the committed SVG/PNG are the
output of that render.

Subgraphs: System Initialisation / Genesis · Round Start and Common Template (Phases 2, 3a,
3b) · Deterministic Nonce Allocation · Collaborative Mining · Post-Range Policy · Round
Outcome · Block Verification · Reward Distribution · Round Transition · Dynamic Miner-Set
Management · Protocol Scope.

# Output 3 — Simplified presentation version

Source of truth: [`fig_5_6_pocol_simplified.mmd`](fig_5_6_pocol_simplified.mmd). One slide,
essential path only:

> Start Round → Read State → Build Common Template → Verify `TemplateID` → Generate Round Seed
> → Order Miners → Partition Nonce Domain → Parallel Disjoint Search → Valid Hash? →
> Verify Template + Range + PoW + Reward → Commit Block → Distribute Pre-Committed Reward →
> Update State → Next Round

with the branch *no valid hash + ranges exhausted → post-range policy → new round / new
template* and a single dashed invariant box.

---

# Output 4 — Figure caption

> **Figure 5.5. Complete Proof-of-Collaboration (PoCol) consensus workflow**, from system
> initialisation and the genesis round through repeated collaborative mining rounds. The
> diagram covers canonical common-template formation — the bounded transaction-collection
> window, the deterministic transaction ordering, the nonce-free header template and the
> `TemplateID_r` agreement check that gates the start of mining — followed by deterministic
> nonce-domain partitioning from the round seed
> `seed_r = H("PoColNonce" ‖ h_(r−1) ‖ r ‖ TemplateID_r)` through per-miner tickets, the
> pseudo-random ordering `L_r`, and the disjoint contiguous ranges `R_r(m₍ᵢ₎)` of
> Equations (5.4a)–(5.5); the collaborative proof-of-work search, in which each miner
> instantiates candidate headers only from its assigned range and the block-success condition
> remains `H(Serialize(Header_r(n))) ≤ Target`; the declared post-range operating policy,
> either low-power idle or continued non-overlapping work; the eight-step block validation
> performed independently by every receiving node, including recomputation of the canonical
> template and verification that the successful nonce lies in the proposer's assigned range;
> the pre-committed collaborative reward distribution `Reward_r(mᵢ) = sᵢ · R_tot(r)`, computed
> before mining and committed through the Merkle root; the state update and round transition;
> and dynamic miner-set management covering joining, explicit deregistration, silent
> inactivity and optional inactivity-based removal. All work assignments are derived locally
> by each miner from public protocol state, so the workflow requires no trusted range
> coordinator. Solid boxes denote protocol steps and diamonds denote decisions; dashed boxes
> denote invariants, assumptions and stated limitations, and the scope panel lists protocol
> components that Chapter 5 specifies but that are not implemented or experimentally validated
> in this work.

Short-form caption for the list of figures:

> Figure (5.5) Complete PoCol consensus workflow: common-template formation, deterministic
> nonce-domain partitioning, collaborative proof-of-work search, validation, pre-committed
> reward distribution, round transition and dynamic miner-set management.

Caption for the simplified variant:

> **Figure 5.6. Simplified PoCol consensus round.** Essential control path of one PoCol round:
> common-template agreement, deterministic partitioning of the permitted nonce domain into
> disjoint per-miner ranges, parallel collaborative search under the unchanged proof-of-work
> condition, validation of template conformity and successful-nonce range membership, and
> distribution of the pre-committed reward, with the no-solution branch that closes the round
> and derives a new template.

---

# Output 5 — Defence explanation (≈320 words)

> This figure traces one complete PoCol round from committed state to committed block.
>
> A round begins deterministically the moment the previous block is accepted. Every miner
> reads the same committed state — previous block hash, registered miner set, balances and
> pending transactions — and then does something that classical Proof-of-Work never does: it
> agrees on *what* to mine before deciding *how* to mine it.
>
> That is the common-template stage. Miners collect transactions during a bounded window, order
> them by a fixed deterministic rule, compute the Merkle root, and embed a reward transaction
> that has already been computed — before any hashing. The result is one canonical block
> template and one nonce-free header template, identified by a single hash, `TemplateID_r`. If
> my local identifier does not match my peers', I do not mine: I fetch what I am missing,
> rebuild, and re-check. Agreement gates mining, and it happens entirely by gossip — there is
> no coordinator anywhere in this diagram.
>
> Once the template is frozen, the assignment falls out of it. The round seed hashes the
> previous block hash, the round number and the template identifier. Each miner's ticket
> hashes the seed with its identity. Sorting the tickets gives a pseudo-random order, and
> simple integer division of the permitted nonce domain gives each miner a contiguous,
> disjoint range. Every miner computes this locally, from public inputs, and gets the same
> answer.
>
> The proof of work itself is unchanged: insert a nonce, serialise the header, hash it, compare
> against the target. What changed is the input space. Because the template is common and the
> ranges are disjoint, no two honest miners ever hash the same serialised header.
>
> When a miner exhausts its range without success, the declared policy decides: idle at low
> power, or take new non-overlapping work. The energy saving comes from that transition, not
> from partitioning by itself.
>
> Verification recomputes everything — template, ranges, reward — and rejects a block whose
> template identifier differs, even when its proof of work is valid.
>
> The dashed panel states what is specified but not yet proved or measured.

---

# Traceability

Every diagram element maps to a chapter location.

| Diagram element | Thesis source |
|---|---|
| Genesis parameters, founding miner set `M₀`, bootstrap routes | §5.7.1, §5.7.2 |
| Genesis template, `TemplateID₀`, `seed₀`, genesis search | §5.7.3 |
| Genesis reward and ledger initialisation | §5.7.4 |
| Round start, state read | §5.5.1, §5.8.1 |
| Transaction window `Δ_tx`, eligibility, ordering rule, reconciliation | §5.8.2 |
| `BlockTemplate_r`, `HeaderTemplate_r`, `TemplateID_r` | §5.5.2, §5.8.2 |
| Common-Template Invariant | §5.8.2 (quoted) |
| `seed_r` (5.2), `ticket_r` (5.3), `L_r` (5.4) | §5.6.1, §5.6.2 |
| `start_r(i)`, `end_r(i)`, `R_r(mᵢ)` (5.4a, 5.4b, 5.5) and the three properties | §5.6.3 |
| Permitted nonce domain `N`, `N_max` = 2³² or 2⁶⁴ | §5.6 preamble |
| Disjoint-Evaluation Invariant | §5.8.3 (quoted) |
| Collaborative search, prohibition on altering non-nonce fields | §5.8.4 |
| Range exhaustion, no-solution round, new template/new round | §5.6.5, §5.8.4 |
| Energy-saving idle policy and its caveats | §5.6.6.1 |
| Continuous-performance policy and its caveats | §5.6.6.2 |
| Inactive miners, `H_eff(r)`, `λ_blk^eff(r)` | §5.6.5, §5.10.2, §5.11.3 |
| Verification checks 1–8 | §5.8.5 |
| Range-membership caveat | §5.8.5, §5.11.2, §5.11.5 |
| `R_tot(r)` (5.6), `f_r` (5.7), `Reward_r(mᵢ)` (5.8), equal sharing (5.9) | §5.9 |
| `T_reward(r)` structure, pre-commitment, immutability | §5.9.1 |
| Reward verification: completeness, correctness, conservation, validity | §5.9.2 |
| Activity-filtered `M̃_r` variant | §5.9.3 |
| Joining, explicit leaving, silent leaving | §5.4.1–§5.4.3, §5.10.1, §5.10.2 |
| `h − ℓᵢ(h) > Θ_inact` forced removal | §5.4.4, §5.10.3 |
| Chain selection, fork resolution, cumulative work | §5.8.5, §5.11.1 |
| Scope panel items 1–5 | §5.8.2, §5.11.1, §5.11.2, §5.11.4, §5.11.5, §5.12, §6.3, §6.9, §8.5 |

# Final validation against Chapter 5

| Check | Result |
|---|---|
| Every major PoCol stage represented | Genesis, state read, template construction, `TemplateID` agreement, seed, ordering, partitioning, search, post-range policy, round outcome, verification, reward, state update, miner-set dynamics — all present |
| No non-source mechanism invented | Every node traced in the table above; no thresholds, timers, penalties or committee mechanisms added |
| Equations transcribed correctly | (5.2), (5.3), (5.4), (5.4a), (5.4b), (5.5), (5.6), (5.7), (5.8), (5.9) verbatim, with the thesis's own numbering (note: the thesis labels the ordering equation (5.4) and the partition bounds (5.4a)/(5.4b)) |
| Nonce domain not confused with hash output space | Dedicated dashed note: `N = {0,…,N_max−1}`, e.g. 2³² or 2⁶⁴, explicitly *not* the SHA-256 output space |
| Common-Template Invariant explicit | Quoted in a dashed box attached to the template-freeze step |
| Disjoint ranges explicit | Partition properties box plus the quoted Disjoint-Evaluation Invariant |
| Only the nonce varies within one active round | Stated on the header template step, on the search step, and in the no-solution branch |
| Changing another consensus-critical field requires a new template / new round | Step 50–51 and verification Check 8 |
| Reward distribution pre-committed before mining | Phase 3a precedes template assembly structurally; `T_reward(r)` embedded and committed through the Merkle root |
| Successful-nonce range membership checked | Verification Check 4, with the non-exhaustiveness caveat attached |
| Inactive-range behaviour correct | Separate lane; range assigned but unevaluated; `H_eff` reduction; explicit "all active ranges exhausted ≠ domain exhausted" note |
| Energy saving not attributed to partitioning alone | Dashed note names the active→idle transition as the mechanism and lists the effects that must be co-evaluated |
| Unresolved properties not shown as proven | Five-item scope panel; §5.11 arguments labelled preliminary/informal throughout |

## Reproducing the renders

```bash
npm install @mermaid-js/mermaid-cli
npx mmdc -i fig_5_5_pocol_complete.mmd -o fig_5_5_pocol_complete.svg -b white
npx mmdc -i fig_5_6_pocol_simplified.mmd -o fig_5_6_pocol_simplified.png -b white -s 2
npx mmdc -i fig_5_5_pocol_complete.mmd -o fig_5_5_pocol_complete.pdf -b white --pdfFit
```

`--pdfFit` sizes the PDF page to the diagram. The page-fitted A3/A4 variants are produced from
those PDFs by centring the artwork on a standard page:

```bash
pip install pypdf
python3 - <<'EOF'
from pypdf import PdfReader, PdfWriter, Transformation, PageObject
def place(src, out, pw, ph, margin=28):
    p = PdfReader(src).pages[0]
    w, h = float(p.mediabox.width), float(p.mediabox.height)
    s = min((pw-2*margin)/w, (ph-2*margin)/h)
    page = PageObject.create_blank_page(width=pw, height=ph)
    p.add_transformation(Transformation().scale(s).translate((pw-w*s)/2, (ph-h*s)/2))
    page.merge_page(p)
    w_ = PdfWriter(); w_.add_page(page); w_.write(out)
place('fig_5_5_pocol_complete.pdf',   'fig_5_5_pocol_complete_A3.pdf',   841.89, 1190.55)
place('fig_5_6_pocol_simplified.pdf', 'fig_5_6_pocol_simplified_A4.pdf', 595.28,  841.89)
EOF
```

For thesis typesetting insert the PDF or SVG (both vector, scale without loss). If the printer
requires raster, the 2× PNG is 1568 px wide; re-render with `-s 4` for 300 dpi at A3 width.
