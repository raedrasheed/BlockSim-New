# Examiner's Report

**Thesis:** *Proof-of-Collaboration: A Novel Blockchain Consensus Algorithm with Highly Efficient Power Consumption*
**Candidate:** Raed S. Rasheed · **Supervisor:** Prof. Aiman AbuSamra
**Degree:** PhD in Computer Engineering, Faculty of Engineering, The Islamic University of Gaza
**Version examined:** `docs/Raed-Rasheed-draft-42-00.docx` / `.pdf` (176 pp., 8 chapters, 153 references), dated 08/2026
**Supporting artefacts examined:** the `BlockSim-New` implementation (`Models/PoCol/*`, `Models/Node.py`, `InputsConfig.py`, `Statistics.py`) and the simulation workbooks committed to the repository.

---

## 1. Recommendation

**Major revision and re-examination of the experimental chapters (Chapters 6–7).** The thesis is **not acceptable in its present form**.

The design contribution (Chapters 4–5) and the comparative review (Chapter 3) are of near-defensible quality and can be retained with revision. The empirical case on which the thesis's headline claims rest — a 98–99 % energy reduction, higher throughput, and shorter confirmation time — does **not** survive inspection: each of these results is traceable to a specific accounting or scheduling decision in the prototype rather than to the proposed protocol. In addition, the central analytical claim (Eq. 4.8, `ESR ≈ n`) is inconsistent with the energy–security conservation property of Nakamoto consensus and is not defended anywhere in the thesis.

I want to record at the outset that the thesis is unusually candid about the distance between the specification and the prototype (§6.3, §6.9, §8.2). That honesty is to the candidate's credit and should be preserved in revision. The problem is that the disclaimers stop one step short: they say the prototype is *idealised*, but they do not recognise that the idealisation is what produces the results.

**Conditions for re-submission** are itemised in §7.

---

## 2. Summary of the work

The thesis proposes **Proof-of-Collaboration (PoCol)**, a Nakamoto-style consensus protocol in which, within each mining round, all registered miners commit to a single immutable canonical block template (bound by a `TemplateID`) and a derived nonce-free header template; the permitted nonce domain is then deterministically partitioned into disjoint ranges by a seeded, publicly verifiable allocation function, and each miner evaluates only candidate headers instantiated from its own range. The block reward and fees are paid through a multi-output reward-distribution transaction that is committed *before* mining, so the winner cannot alter it. The protocol specification includes miner registration/deregistration, silent-leave and inactivity handling, two post-range operating policies (idle vs. continuous), and an informal security discussion.

The evaluation extends BlockSim with energy and carbon instrumentation and compares an abstraction of PoCol with a PoW baseline for miner populations of 100–500 over a 10,000 s horizon.

**Strengths.** (i) The topic is timely and the motivation is clearly established. (ii) Chapter 5 is a genuinely detailed protocol specification; the common-template invariant, the binding of nonce allocation to `TemplateID`, and the pre-committed reward transaction are carefully and correctly reasoned. (iii) §3.7 positions PoCol against Parallel PoW, StrongChain, Collaborative PoW, Proof of Team Sprint, Green-PoW and APoW with a clarity that is rare in this literature, and §3.7.4 correctly identifies the missing verifiable-search primitive. (iv) The instrumented simulator is a reusable artefact. (v) The framing of qualitative comparison as evidence-based synthesis rather than measurement (§3.2.8–§3.2.10) is methodologically responsible.

---

## 3. Major issues (thesis-blocking)

### M1. The problem the thesis solves is not the problem PoW has

The energy claim rests on eliminating *duplicate serialized candidate-header inputs* between honest miners. §5.1 itself states the correct fact: real miners vary the coinbase extra nonce (hence the Merkle root) and other permitted fields, so two miners essentially never hash the same serialized header. Duplicate-input redundancy in deployed PoW is therefore ≈ 0, and eliminating it can save ≈ 0.

The thesis resolves this by evaluating against a constructed **"common-template PoW baseline"** in which every miner is *stipulated* to scan the same header template from the same nonce domain. This baseline exists in no deployed system, is not derived from any cited protocol, and — critically — is **not what the prototype implements**: `Models/Bitcoin/Consensus.py` models PoW as an exponential race with no notion of headers at all, so no duplicate inputs are generated or counted in the baseline either. The redundancy factor `R_PoW` (Eq. 4.3), which is the sole quantitative link between the mechanism and the energy claim, is **never measured in any experiment**.

The candidate must either (a) demonstrate empirically that a realistic PoW deployment incurs a redundancy factor materially above 1, or (b) abandon duplicate-input elimination as the energy mechanism and rest the thesis on the *idle policy*, which is the only mechanism in the design that can physically reduce electricity consumption — and which is neither implemented nor measured (see M3, S5).

### M2. Eq. (4.5)–(4.8) are not physically sound

Equation (4.1) correctly gives `E_block = P/λ`. Equations (4.5)–(4.6) then write `E_PoW = (1/λ)·P_PoW·R_PoW`, i.e. they multiply the energy per block *again* by the redundancy factor. If `P` is the network's actual power draw, redundancy is already contained in it (or in the difficulty that sets λ); multiplying by `R` double-counts. Equation (4.8), `ESR ≈ n·Q_avg/U_total,PoW`, consequently predicts an energy saving that grows **linearly in the number of miners**.

This cannot be correct, and the reason is a conservation property that the thesis never confronts. In any hash-target protocol, the expected number of header evaluations required to produce a block is `1/p`, fixed by the target — not by how the work is coordinated. Partitioning the search space converts sampling-with-replacement into sampling-without-replacement over a domain astronomically larger than the number of trials performed; the resulting saving is negligible, not `n`-fold. It follows that, at a fixed block interval and fixed hardware efficiency, **a 98–99 % reduction in network energy is identical to a 98–99 % reduction in the work securing each block**, and hence to a 98–99 % reduction in the cost of a majority attack. Claims C2, G1 and §5.11.1 ("security comparable to PoW") and claim G3/RQ2 (large energy saving at the same λ) are therefore mutually inconsistent as stated.

This is the single most important objection, and it must be addressed head-on in the revision — not by a disclaimer, but by an explicit analysis of where on the energy–security curve PoCol sits.

### M3. The reported energy saving is an artefact of the prototype's accounting rule

`Models/PoCol/Consensus.py::apply_energy_for_created_block` charges each miner

```
time_share = block_time / N_miners      # per created block, per miner
```

so the network total per round is `P_total × block_time / N`. The PoW baseline (`Models/Node.py::stop_mining_and_account`) charges every miner for its **full wall-clock mining time**. In other words, PoCol is billed as though only *one* miner were powered on at any instant, while PoW is billed for all `N`.

This is arithmetically sufficient to produce the entire reported effect. Reconstructing the N = 100 case from Table 6.2: PoW's 7.9018 kWh at 3031.5 W aggregate corresponds to ≈ 9,385 miner-seconds per miner (i.e. essentially the whole 10,000 s horizon, correctly); PoCol's 0.1308 kWh corresponds to ≈ 155 s per miner, i.e. `Σ(round durations)/N` — one miner's worth of hashing spread across the population. The ratio, 60×, is the `1/N` division modulated by the number of rounds. It is not a measurement of anything the protocol does.

Under PoCol's own specification (§5.5.2, §5.8.4) **all** registered miners hash concurrently over their disjoint ranges for the whole round. With the nonce domain auto-sized as `S = 2·H_total·T` (`Consensus._get_nonce_space`), the expected round duration is `T`, exactly as in PoW; so the correct energy per block is `P_total·T` — **identical to the baseline**. The prototype's own configuration therefore implies energy parity, not a 98–99 % saving. Figures 7.4–7.8, Table 6.2, Table 7.1 and all associated text must be withdrawn and recomputed.

### M4. The two arms are not run at the same aggregate hash rate

`Models/Node.py:50` computes a PoW miner's rate as `NetworkHashRate_Hps × hashPower/100`. With `hashPower = 1` per node, the divisor should be `Σ hashPower = N`, not the literal constant `100`. The PoW arm therefore runs at `1.41·N TH/s`, matching the configured 141 TH/s only at N = 100. `Models/PoCol/Node.py::hashrate_fraction` does divide by `Σ hashPower`, so the PoCol arm is correctly held at 141 TH/s for every N.

The committed workbooks confirm this exactly: PoW total energy is 3.93 / 8.16 / 40.41 / 83.84 kWh for 50 / 100 / 500 / 1000 miners — perfectly linear in N, at a nominally constant network hash rate. Table 6.1's statement that the total network hash rate was fixed at 141 × 10¹² H/s across all scenarios is **factually incorrect for the PoW arm**, and at N = 500 the baseline is being charged for 5× the hash rate given to PoCol.

This defect alone explains the *widening* of the reported gap with population (98.3 % → 99.2 %), and it invalidates the Chapter 7 narrative that "PoW energy scales with network size". It does not; in a correct model, PoW energy at fixed difficulty is independent of the number of miners.

### M5. The two arms do not run at the same effective difficulty, so the performance results are not comparable

Both arms are configured with a 600 s target interval over a 10,000 s horizon, giving ≈ 16.7 expected main-chain blocks. PoW delivers 18 / 14 / 16 / 27 / 19 (consistent with Poisson noise). PoCol delivers 18 / 36 / 62 / 59 / 46 — up to **62 main-chain blocks, a mean interval of ≈ 161 s**, roughly 3.7× the configured rate. Two protocols with the same target and the same aggregate hash rate must produce the same expected main-chain block rate; that they do not shows the PoCol arm is effectively running at a much lower difficulty (round state is re-initialised, and a fresh solution nonce re-sampled, whenever a miner's parent changes — `Consensus._init_round`).

Every throughput and latency conclusion in §7.3.1–§7.3.2 and in the abstract (11.33 vs 2.87 TPS; six-confirmation time of 957 s vs 3,635 s) is a restatement of this difficulty mismatch. Transactions per block are essentially identical in the two arms (≈ 1,790–1,830, capped by the 1 MB block size), so TPS here is nothing more than block count. Collaboration is not the cause.

### M6. The stale-block "finding" is a scheduling artefact and cannot occur in PoCol as specified

`Consensus.Protocol` schedules *every non-winning miner* to create a block at `winner_time + loser_lag`, with `loser_lag = max(5·Bdelay, 1.0) = 2.1 s`. Propagation delay is exponential with mean 0.42 s, so each loser fails to receive the winner's block in time with probability `e^{-5} ≈ 0.67 %` and then emits a competing block. The expected number of such blocks per round is ≈ 0.0067·(N−1), which yields stale rates of roughly 40 % / 57 % / 67 % / 73 % / 77 % for N = 100…500 — the same shape and order as the reported 35.7 % / 68.1 % / 78.4 % / 82.7 % / 85.7 %.

In PoCol as specified, a miner that has not found a nonce satisfying the target **has no block to publish**. Blocks of this kind cannot exist. The high stale rate is therefore an artefact of a scheduling device used to keep losing miners from "winning" in the simulator, not a property of collaborative mining.

This matters beyond the numbers: the stale rate is presented as the thesis's principal honest limitation (abstract, §7.3.3, §7.6, §8.5) and is the basis of its main future-work programme. That programme is currently aimed at a bug.

### M7. The evaluated reward rule is not incentive-compatible, and the thesis's own goal G6 is unmet

The baseline reward function (Eq. 5.9) pays every registered miner `1/|M(r)|` of the reward, in a transaction fixed **before** mining, with no verifiable evidence that any miner searched its range (§5.9, §5.6.5, and the range-membership check of §5.8.5, which the thesis correctly notes proves nothing about non-winners). Under this rule, not hashing strictly dominates hashing: a registered miner that spends nothing receives the same share as one that spends its full range. Registering many identities is likewise strictly profitable. §5.11.4 and §3.7.4 identify both problems and propose remedies (costed registration, non-identity-proportional weights, APoW-style audits) but none is specified in enforceable detail, and none is evaluated.

The consequence is not merely theoretical: a protocol whose equilibrium is zero hash rate has zero security. The thesis cannot claim G4 (fairness/decentralisation) or G6 (protection from strategic behaviour) on the present design. Either specify and analyse a verifiable contribution proof, or state plainly that PoCol is incomplete without one and remove the corresponding claims.

### M8. The common-template requirement introduces an unanalysed liveness/DoS surface

§5.8.2 requires that a miner whose locally derived `TemplateID` differs from its peers' **does not mine** until it resynchronises. An adversary can therefore stall or split honest hash power at negligible cost by broadcasting transactions timed to arrive near the boundary of the collection window `T_sync`, so that different subsets of honest miners derive different eligible sets and hence different templates. This is a new attack that classical PoW does not admit (a Bitcoin miner with a divergent mempool simply mines a different, equally valid block). §5.11 does not consider it; §4.3 lists eclipse/partition attacks but Chapter 5 never analyses them. Given that template agreement is the mechanism on which the whole design rests, this analysis is mandatory.

### M9. Statistical basis and reproducibility are insufficient

* **One run per configuration, no repetition, no confidence intervals, no significance testing.** The thesis acknowledges this (§6.9) but nonetheless draws directional conclusions from differences well inside the noise. PoW main-chain block counts range 14–27 across populations from a process with mean 16.7 — pure Poisson variance — yet §7.3.2 reads a "trend" into PoW's six-confirmation times (3,128 / 3,959 / 3,635 / 2,182 / 3,033 s).
* **No random seeding.** `Main.py` and the model code call `random` without seeding; seeds exist only in `Models/Energy/scenarios.py`, which is not used by the thesis runs. The reproducibility procedure of §6.8 therefore cannot reproduce the reported figures, and §6.8's claim that the workbook is a "primary empirical record" cannot be honoured.
* **The primary records are not in the repository.** The ten PoW/PoCol workbooks underlying Tables 6.2 and 7.1 are absent from `[153]`; the repository contains Bitcoin and Ethereum runs at 50/100/500/1000 miners instead. Where a comparison is possible the correspondence is inconsistent: the repository's PoW N = 500 run matches Table 6.2 exactly (19 main blocks, 40.4078 kWh, 34,117 tx), whereas its PoW N = 100 run does not (13 main blocks, 8.157 kWh, vs. the reported 18 blocks and 7.9018 kWh).
* **Uncontrolled parameter difference between arms.** `InputsConfig.py` sets `Tn = 3` for the PoW model and `Tn = 10` for PoCol, contradicting §6.4's statement that all inputs other than the miner population were held constant. The effect here is small (blocks are size-capped) but the discrepancy must be removed and the claim corrected.

### M10. Specification defects in the allocation function

1. **Equal partitioning contradicts the security argument.** §5.6.3 divides the nonce domain into `n` equal contiguous ranges, independent of hash rate. The probability that the winning nonce lies in miner *i*'s range is then `1/n`, *independent of h_i*; hash rate affects only how quickly the range is traversed. §5.11.1's claim that "the distribution of successful blocks between honest and adversarial miners is still governed by their hash-rate proportions" is therefore false under the specification as written, and the backbone-model inheritance argument does not go through. It also creates a liveness hazard: a registered miner with negligible hash rate holds `1/n` of the domain and can delay or stall every round in which the solution falls inside it.
2. **Specification and implementation diverge.** The prototype (`Consensus._init_round`) partitions *proportionally to hash rate*, not equally — i.e. it implements a different protocol from the one specified. Proportional allocation, in turn, requires each miner's hash rate to be known on-chain; the only available source is self-declaration (§5.4.1, "optional declared hash power"), which is unverifiable and trivially gamed.
3. **Nonce-domain sizing is unaddressed.** §5.6 offers `2^32 or 2^64`. At 141 TH/s a 32-bit domain is exhausted in ≈ 30 µs, which would require a full distributed template re-agreement thousands of times per second — plainly infeasible, and fatal to G5 (compatibility with existing block/header structures, since Bitcoin's header nonce is 32-bit). A 64-bit domain requires a header format change. The thesis must fix the domain size, justify it, and analyse the resulting round-restart rate against the template-agreement latency `T_sync`.
4. **Difficulty adjustment is absent** from both the specification and the prototype, yet the interaction between the idle policy (which lowers effective hash rate), retargeting, and security is precisely the crux of the thesis. It cannot be left out.

---

## 4. Substantive issues

* **S1 — Chapters 2 and 3 overlap heavily.** Both survey the same consensus families at similar depth. Chapter 2 should be reduced to the primitives actually used later (hash-target condition, header structure, partial synchrony, backbone properties, power vs. energy), and the survey consolidated into Chapter 3.
* **S2 — Chapter 3 is a transplanted paper.** It refers to itself as "this survey"/"this research paper", speaks of "the authors" (also in §4.7), and carries its own research questions RQ3.1–RQ3.5 that are never mapped to the thesis's RQ1–RQ3. It must be rewritten in the thesis's voice and integrated.
* **S3 — Qualitative tables lack per-cell traceability.** Tables 3.6–3.8 assign labels ("Medium to High", "Very Good") without a citation on each cell. The rubric in §3.2.8–§3.2.10 is a good start; complete it by making every cell traceable to at least one source.
* **S4 — PRISMA framing.** The thesis is right not to claim a full systematic review, but it should still report the number of records identified, screened, excluded and included; that costs little and materially improves credibility.
* **S5 — The idle policy, the only genuine energy mechanism, is never implemented.** §3.7.3 and §4.4.2 correctly state that "deterministic nonce-range separation does not independently imply lower electricity consumption. Energy reduction requires a measurable transition from active hashing to a lower-power state." No idle power `P_idle` is defined anywhere in the configuration, no idle interval is logged, and no coordination overhead `E_coord` is measured — the three quantities the thesis's own energy equation requires. The corrected theory in Chapters 3–5 and the implementation in Chapter 6 are therefore describing different protocols.
* **S6 — No collaborative baseline is simulated.** Parallel PoW, Green-PoW and Proof of Team Sprint are the natural comparators, and §6.4 rightly forbids cross-paper numerical claims — but the consequence is that PoCol is never compared with any collaborative design. At least one should be implemented in the same harness.
* **S7 — Fairness and decentralisation are claimed but not delivered.** They appear in RQ3, G4, C3 and C4, and the thesis states four times that they remain future work. Either evaluate them (the Gini machinery is straightforward from the per-miner reward logs already produced) or remove them from the contribution claims. As it stands, C3/C4 overstate what was done.
* **S8 — Carbon results are informationally empty.** CO₂ is energy × 0.445 throughout; Figure 7.8 is Figure 7.4 rescaled. Present it as such in one sentence rather than as an independent result, or add the grid-intensity sensitivity analysis (γ) that the repository's own scripts already support.
* **S9 — Energy model scope.** No PUE/cooling, no idle draw, no network/coordination energy, no embodied hardware energy. For a thesis whose contribution is a "sustainability-aware evaluation framework", these omissions should at minimum be stated as model boundaries in Chapter 4, not only in §8.5.
* **S10 — "Permissionless" is overclaimed.** PoCol requires on-chain registration to receive a range, and admits governance-driven inactivity removal. Participation without registration is impossible. The design is closer to an open-membership consortium protocol; say so, and revisit the comparison with PoA/PBFT accordingly.
* **S11 — §7.4.2 is titled "Comparison with PoW, PoS, PBFT, etc."** but the text correctly states that no PoS or PBFT runs were performed. Retitle.
* **S12 — Tone.** §7.6.2 ("We recommend a substantial increase in the amount of both research funding and engineering development") is advocacy, not a research finding; remove.

---

## 5. Presentation, referencing and formal issues

**Structure and numbering**

* **P1** Tables 3.6 and 3.7 carry an *identical* caption, though Table 3.7 is a deployment/decision matrix. Re-caption 3.7.
* **P2** Tables are introduced out of order: Table 3.9 appears in §3.7.5, before Tables 3.7 and 3.8 in §3.8. The List of Tables reflects this (3.9 → p. 52, listed after 3.8 → p. 59). Renumber.
* **P3** §3.8.3: the fourth question is labelled "RQ4"; should be RQ3.4.
* **P4** §3.3.4 repeats an entire passage verbatim ("…the table's purpose is to provide a description of the primary platforms…"). Delete the duplicate.
* **P5** §4.7 ends mid-sentence: "Then showed what are the requirements of the PoCol protocol concerning safety,".
* **P6** Abbreviation inconsistency: PoC is "Proof of Contribution" in the abbreviation list and Table 3.5, but "Proof-of-Capacity" in §3.3.4; PoR is "Proof of Reputation" but "Proof-of-Resilience" in §3.3.4.
* **P7** Table 3.5 dates PBFT to 1998 while [8] is OSDI '99, and PoSpace to 2013 while [33] is CRYPTO 2015. Reconcile dates with the cited sources or cite the earlier preprints.
* **P8** §3.8.2 contains a stray citation in the wrong style: "[2-4]".
* **P9** Equation numbering: (5.4) is used for the permutation and again as (5.4a)/(5.4b) for the partition; several equations in §5.10 and §5.11.3 are unnumbered. Add a consolidated notation table — the reader currently has to reconstruct `M(r)`, `A(r)`, `h_i`, `H_eff`, `Q`, `U`, `R`, `β`, `ε`, `Λ` from scattered definitions.
* **P10** Chapter 5 contains no algorithm environments. The round seed, ticket/permutation, partition, verification procedure and reward computation should each be given as numbered pseudocode.
* **P11** §6.4 renders parameter values as broken fragments in the extracted text ("target block  seconds", "141 × hashes per second"); verify the equation fields render correctly in the final PDF.
* **P12** Front matter: the List of Tables/Figures uses Arabic numerals while the automatic ToC uses Roman for front matter; page numbers in the manual lists should be regenerated after final pagination.

**Referencing — this needs a systematic pass; the following are examples, not an exhaustive list**

* **P13** *Content mismatches between claim and cited source:*
  * §2.2.1, "the addition of proactive recovery [59]" — [59] is a blockchain energy-trading paper. The correct source (Castro & Liskov, 2002) is already in the list as [116].
  * §2.3.2, "Green-PoW modifies competition and reward policies [16], [70]" — Green-PoW is [15]; [16] and [70] are Proof-of-Learning papers.
  * §2.3.2, "Proof of Federated Learning … [60]" — PoFL is [18]; [60] is "Performance of PBFT Consensus under Voting by Groups".
  * §3.6.8 (PoB) cites [34], [52] — [52] is DPNPBFT — and elsewhere [125], which is *Burning Up: A Global History of Fossil Fuel Consumption*. This citation cannot stand.
  * §3.6.11 (PoR) cites [59] again.
  * §3.8.1.1, "PoW … very large power consumption [142]" — [142] is titled "Proof of Reputation".
  * §3.8.1.1, "PoS … stake concentration [26], [33]" — [33] is *Proofs of Space*.
  * §5.6.2 names Ouroboros, Algorand and Snow White but cites [27], [29]; none of the three primary papers appears in the reference list at all.
  * §5.11.1 attributes the common-prefix property to [46], [34] — [34] is *Proof-of-Burn*; the intended source is presumably [47] (Pass et al.).
  * Chapters 4–5 repeatedly use [99] (Tereshchenko & Kyrychenko, on digital-asset protection) to support the Poisson block-arrival model and PoW energy magnitudes.
  * Application-domain papers — [95] supply-chain sensing, [97] RFID authentication, [100] medical supply chains, [101] bio-inspired IP-network security, [103] healthcare fog, [104] IoT trust, [118] spam detection, [147] healthcare big data, [148] insurance, [149] a cement factory — are cited as evidence for consensus-security and consensus-trade-off statements. These should be replaced with consensus literature.
* **P14** [5] is a **retracted** article. The thesis flags the retraction in the reference entry, which is good practice, but it is still used in §1.1 as positive support. Remove it or justify the citation explicitly.
* **P15** [89] is an edited proceedings volume rather than a paper; [91] is a project homepage; several entries are theses, preprints or non-indexed venues ([93], [110], [122], [123], [138], [144]). For a doctoral bibliography, prefer peer-reviewed sources and mark preprints as such — the thesis does this correctly for APoW [138] and should do so consistently.
* **P16** Two different simulators are both called "BlockSim": [40] (Alharby & van Moorsel) and [151] (Faria & Correia). The work extends [40]; state this once, explicitly, and cite consistently thereafter.
* **P17** [150] is "unpublished manuscript" and [153] is the software repository. Update the status of [150] before submission, and archive [153] with a DOI (e.g. Zenodo) including the ten primary workbooks and the exact configuration files.
* **P18** The abstract quotes headline figures (11.33 vs 2.87 TPS; 0.454 vs 33.078 kWh). These must be removed or fully re-qualified pending the corrected evaluation.

**Language.** The thesis needs a full language edit. Comma splices are pervasive ("…provide open participation and strong security, but their…", "…remains possible, this…"). Several passages — §3.6, §3.8.1, §8.4 in particular — are repetitive and read as generated boilerplate ("the right tool for the right job", "as a whole, these resource-based validation mechanisms highlight that there is no one-size-fits-all"). Chapter 3 and Chapter 8 would each lose 20–30 % of their length with no loss of content.

---

## 6. Chapter-by-chapter notes

| Ch. | Assessment |
|---|---|
| **1 Introduction** | Adequate. Objective (i) — "uses less than 50 % of the energy consumed by the evaluated PoW baseline" — should be restated once the baseline is corrected. RQ2 is well scoped ("under the controlled simulation assumptions"); RQ1 and RQ3 promise more than the thesis delivers. |
| **2 Background** | Technically correct but largely duplicative of Ch. 3 (S1). §2.2.2's description of PoW is accurate and is the right basis for the corrections requested in M1. |
| **3 Literature review** | The strongest chapter. Needs re-voicing (S2), per-cell citation (S3), renumbering (P1–P2) and a reference audit (P13). §3.7 should be promoted: the gap analysis there is the thesis's clearest intellectual contribution. |
| **4 System model** | The modelling apparatus is appropriate, but Eqs. (4.3)–(4.8) are the analytical root of M2 and must be rederived. The constrained-optimisation formulation in §4.6 is never used again — either use it (as the evaluation's objective function) or reduce it to a statement of requirements. |
| **5 PoCol protocol** | Detailed and mostly careful; the specification-level work is of doctoral standard *except* for M8 and M10. The security section is explicitly informal; at minimum, the chain-quality argument under the new work assignment should be made rigorous, since that is what the partition actually changes. |
| **6 Implementation** | Commendably transparent about what is and is not implemented, but it does not disclose the two decisions that drive the results (`time_share = block_time/N`; the loser-lag scheduling). Both must be documented — and then fixed. |
| **7 Results** | Must be re-run in full. As it stands, no conclusion in this chapter is supported: energy (M3, M4), throughput and latency (M5), stale rate (M6), and all of it on n = 1 runs (M9). §7.5 correctly notes that no factorial sensitivity study was performed; after the fixes, one is essential. |
| **8 Conclusion** | Honest about limitations, but it inherits the Chapter 7 claims. §8.5's future-work programme is sensible; note that the first item ("reduce stale blocks") will largely dissolve once M6 is fixed, and should be replaced by the template-agreement overhead study. |

---

## 7. Conditions for re-submission

1. **Re-derive the energy model.** Remove the double counting in Eqs. (4.5)–(4.8); state and defend the energy–security relationship at fixed λ (M2); make explicit which mechanism — duplicate elimination or idle-state transition — is claimed to save energy (M1).
2. **Fix the simulator and re-run everything.**
   * Correct the PoW hash-rate share (`Models/Node.py:50`) so both arms share one aggregate hash rate (M4).
   * Replace `time_share = block_time/N` with concurrent per-miner accounting: active power over the miner's actual active interval, plus idle power over its idle interval, plus coordination energy (M3, S5).
   * Remove the loser-lag block generation; non-winning miners must not emit blocks (M6).
   * Verify that both arms reproduce the configured 600 s target interval before any comparison is drawn (M5).
3. **Implement and measure the idle policy**, with an explicit `P_idle`, logged idle durations, and the resulting effective hash rate — plus difficulty retargeting, so the security consequence of the reduced hash rate is visible (M2, M10.4, S5).
4. **Repeat every scenario** with ≥ 30 seeded runs; report means with confidence intervals; seed all RNGs; archive configurations and workbooks with a DOI (M9).
5. **Resolve the specification defects**: equal vs. proportional partitioning and its effect on the hash-rate-proportionality argument; nonce-domain size and round-restart rate; header-format implications for G5 (M10).
6. **Analyse the template-agreement attack surface** and the cost of `T_sync` (M8).
7. **Specify a verifiable contribution mechanism** (or state explicitly that PoCol is incomplete without one) and align the reward rule, G4 and G6 with what is actually enforceable (M7).
8. **Either evaluate fairness/decentralisation or withdraw those contribution claims** (S6/S7).
9. **Complete a systematic reference audit** (P13–P17) and a full language edit.
10. **Rewrite the abstract, §1.5 and §8.3** to match the corrected results.

Should the corrected experiments show energy parity with PoW — which the prototype's own configuration implies (M3) — that is a publishable and defensible negative result, and combined with the protocol specification of Chapter 5 and the gap analysis of §3.7 it can still support a doctoral thesis. What cannot be sustained is the present claim of a 98–99 % saving at unchanged security.

---

## 8. Questions for the defence

1. In a hash-target protocol, the expected number of header evaluations per block is fixed by the target. By what physical mechanism does PoCol reduce the *energy* per block without reducing the *work* per block — and if it reduces the work, what happens to the cost of a majority attack?
2. §5.1 states that real PoW miners do not evaluate identical serialized headers. What, then, is the deployed system against which the 98–99 % saving is measured?
3. In `apply_energy_for_created_block`, each miner is charged `block_time/N`. Under the specification, how many miners are hashing during a round, and for how long? How do you reconcile the two?
4. At N = 300, PoCol produced 62 main-chain blocks and PoW 16, over the same horizon with the same 600 s target. What sets the effective difficulty in each arm?
5. In PoCol, can a miner that has not found a nonce below the target publish a block? If not, what do the reported stale blocks represent?
6. Under Eq. (5.9), what is a rational registered miner's best response? What prevents an operator from registering 1,000 identities and hashing with none of them?
7. §5.6.3 assigns equal ranges regardless of hash rate, but the prototype assigns proportional ranges. Which is PoCol? Under equal ranges, is the probability of producing a block still proportional to hash rate?
8. If the nonce domain is 2^32, how often must the network agree on a new template at 141 TH/s? How does that compare with `T_sync`?
9. What is the cheapest way for an adversary to prevent honest miners from agreeing on a `TemplateID`, and what does it cost them?
10. Which single experiment, if it failed, would falsify the thesis's central claim?

---

*Prepared as an examiner's report on the version of the thesis and supporting code identified above. Statements about the implementation refer to the code as committed in this repository; file and function names are given so that each observation can be checked directly.*
