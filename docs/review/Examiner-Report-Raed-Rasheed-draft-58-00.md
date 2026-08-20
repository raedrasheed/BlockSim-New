# Examiner's Report — Second Reading

**Thesis:** *Proof-of-Collaboration: A Novel Consensus Algorithm with Highly Efficient Power Consumption*
**Candidate:** Raed S. Rasheed · **Supervisor:** Prof. Aiman AbuSamra
**Degree:** PhD in Computer Engineering, Faculty of Engineering, The Islamic University of Gaza
**Version examined:** `docs/Raed-Rasheed-draft-58-00.pdf` (154 pp., 8 chapters, ~108 references), dated 08/2026
**Also examined:** the cited software artefact — Rasheed, R. S. (2026), *BlockSim-New* [Computer software], GitHub — at its current published state.
**Prior reading:** draft-42-00 (176 pp.), reported separately.

---

## 1. Recommendation

**Major revision.** The thesis is not yet acceptable, but it is now a recoverable thesis and the remaining work is bounded — documentation, provenance, one missing control, a restored security analysis, and corrected headline framing. No new protocol design or re-derivation is required.

This is a very substantial improvement over the previous draft. The defects that made the earlier version unsustainable have been addressed at the root rather than papered over:

* The energy-savings derivation that multiplied power by the redundancy factor (old Eqs. 4.5–4.8, `ESR ≈ n`) has been **withdrawn and explicitly repudiated**. §4.4.2 now states that redundancy is a work measure, not an energy model, that electrical energy is computed from the wall-clock identity `E = Σ Pᵢtᵢ`, and that "this separation supersedes the earlier analytical intuition". That is the correct resolution of my central objection, and the candidate deserves credit for making it plainly rather than quietly.
* The 98–99 % energy claim, the throughput and confirmation-time comparisons, and the stale-block "finding" have all been removed. Stage-1 now establishes the opposite of the old headline: total fixed-horizon energy is **invariant** at 8.420833333 kWh under matched aggregate power, so "partitioning alone does not reduce energy" (Table 7.1, A1). Reaching and reporting that null result is a genuine act of scientific discipline.
* The experimental design is transformed: three declared evidence families, 1,890 + 48 + 60 runs, paired seeds, matched controls, exact sign-permutation inference, Holm correction, integrity gates, and — unusually and commendably — **preregistered decision criteria that are reported as not met**.
* Security-equivalence, fairness, Sybil-resistance and incentive-compatibility claims have been demoted from results to objectives throughout, and §4.3 now explicitly declines to assume that the Nakamoto β threshold transfers to PoCol.
* Chapter 3's reference defects are largely repaired (Castro & Liskov 2002 now cited for proactive recovery; the fossil-fuel history and the retracted article are gone; PoH is correctly re-characterised as an ordering primitive, not a consensus mechanism), and the table numbering and captions are fixed.

What now blocks acceptance is of a different character. The reasoning is sound; the **evidence is not yet verifiable**, one headline is **misattributed**, one comparison rests on an **artefact of the chosen scale**, and the protocol chapter has lost its security analysis entirely. These are set out below.

---

## 2. What the thesis now claims

Four bounded research questions, answered from three frozen evidence families:

| | Claim as stated | Where |
|---|---|---|
| **RQ1** | Disjoint assignment under one common template eliminates exact duplicate serialized inputs | Stage-1 (B3/C1 = 0 duplicates), Stage-3 |
| **RQ2** | 55.05 % calculated energy reduction relative to a within-run power-null reference | Stage-2 (S03) |
| **RQ3** | 90.39 % of the no-floor control's accepted blocks retained | Stage-2 (S03 vs S00) |
| **RQ4** | vs. the active-capacity-matched same-template PoW control: −44.95 % total energy, −19.3 % energy per accepted block, −87.9 % physical evaluations, but 67.70 % of accepted blocks and 5.219× median round duration | Stage-3 |

The thesis characterises RQ4 as an energy–service trade-off rather than joint superiority. That characterisation is correct and appropriately stated.

---

## 3. Major issues

### M1. The cited artefact does not contain the work, and the code it does contain contradicts the results

§6.6 says reproduction requires "checking out the recorded source commit, verifying the relevant checksum manifest, loading the frozen seed registry and scenario matrix, and running the family-specific harness". §6.3 says "the evidence hierarchy and exact source files for each claim are stated explicitly". **None of these objects is identified anywhere in the thesis** — no commit hash, no manifest, no file names, no seed registry, no scenario matrix, no preregistration document, no DOI, and no appendix.

The one artefact that *is* cited resolves to a repository that contains none of the three stages. Its 116 files comprise the original BlockSim tree, the earlier `Models/PoCol` event abstraction, the journal-paper energy scripts and their CSV outputs. There is no target-coupled SHA-256 engine, no Stage-1 63-configuration matrix, no Stage-2/Stage-3 harness, no seed registries, no frozen datasets, no analysis scripts, no checksum manifest.

Worse, the code that *is* published is inconsistent with the reported Stage-1 result. The A1 invariant (8.420833333 kWh for every continuous full-participation configuration and every N from 100 to 500) requires charging all miners active power for the full horizon at a genuinely fixed aggregate rate. In the published code:

* `Models/Node.py:50` computes a PoW miner's rate as `NetworkHashRate_Hps × hashPower/100`, so with `hashPower = 1` per node the aggregate scales as `1.41·N TH/s` — 8.42 kWh at N = 100, but ≈ 42 kWh at N = 500.
* `Models/PoCol/Consensus.py` still charges each miner `time_share = block_time / N_miners`, the rule that produced the now-withdrawn results.

So the published artefact cannot produce the invariant the thesis reports, and still contains the accounting rule the thesis has abandoned. A reader following §6.6 will reproduce the *old* numbers, not the new ones.

This is the single largest obstacle to acceptance. The claims of "machine-verifiable provenance", "byte-identical regeneration of tables, captions, metadata, and figures", and "preregistered" decision rules are, at present, unverifiable assertions. They are also the claims on which the revised thesis rests its credibility, since almost every headline is now an internal accounting relationship rather than an externally checkable physical measurement.

**Required:** deposit the actual Stage-1/2/3 code, seed registries, scenario matrix, preregistration, raw run records and analysis scripts in an archived, versioned artefact with a DOI; cite the exact commit; and either update or clearly retire the superseded paths in the public repository so that the published code no longer contradicts the thesis.

### M2. The energy results depend on power parameters that are never disclosed

The entire Stage-2 and Stage-3 energy story is a power-state residency calculation, `E = Σ Pᵢtᵢ`. It therefore depends on the declared active power, idle power, reserve-standby power and wake-transient power of a miner. **Not one of these values appears anywhere in the thesis.** The only power figure given is the Stage-1 aggregate, 3,031.5 W, which belongs to a different family at a different scale.

The consequence is that the two headline percentages cannot be checked, and their meaning cannot even be assessed: a 55.05 % reduction is a statement about idle *residency fraction* multiplied by `(1 − P_idle/P_active)`, and without the second factor the reader cannot tell whether the result reflects miner behaviour or an aggressive assumption about low-power states. Table 6.1 lists Stage-1 parameters only; Stage-2/Stage-3 parameters are described in prose ("heterogeneous integer miner rates") without a table.

The reader is left to reverse-engineer the scale from Table 7.4: the four attribution components sum to 0.009818 kWh, which at 55.05 % implies a power-null reference of ≈ 0.017835 kWh, hence an aggregate active draw of ≈ 214 W across 20 miners (≈ 10.7 W each) over the 300 s horizon. That arithmetic should be in the thesis, not in the examiner's notes.

**Required:** a complete Stage-2/Stage-3 parameter table — per-state power levels, rate distribution, floor thresholds, reserve policy constants — and a sensitivity analysis over `P_idle/P_active`, since that ratio, not the protocol, sets the magnitude of the reported saving.

### M3. RQ2's headline is misattributed, and on the thesis's own service-normalised metric every floor policy is worse than doing nothing

The abstract, §7.3.2, §8.1 and Table 8.1 present "retained 90.39 % of accepted-block output while achieving a 55.05 % energy reduction" as a single achievement. The pairing invites the reader to attribute the 55.05 % to the operating policy. Table 7.3 shows that it cannot be:

| Scenario | Accepted blocks | Rel. energy reduction | Implied energy (× null) | Energy per accepted block (× null) |
|---|---:|---:|---:|---:|
| S00 (no floor) | 177.9 | 0.5383 | 0.4617 | **4.63 × 10⁻⁵** |
| S01 (static floor) | 150.2 | 0.5722 | 0.4278 | 5.08 × 10⁻⁵ (+9.7 %) |
| S02 (useful floor) | 150.2 | 0.5722 | 0.4278 | 5.08 × 10⁻⁵ (+9.7 %) |
| S03 (coarse reassign.) | 160.8 | 0.5505 | 0.4495 | 4.99 × 10⁻⁵ (+7.7 %) |

Two consequences follow, both from the candidate's own table:

1. **The no-floor control already achieves 53.83 %.** The marginal contribution of the best policy is **1.22 percentage points of energy, bought with a 9.6 % loss of block production**. Reporting 55.05 % beside 90.39 % without stating that 53.83 of those points are present in the control — at no service cost — materially overstates what the policy does.
2. **On energy per accepted block, all three floor policies are dominated by the control.** §4.4.2 itself declares that service-normalised energy is the right quantity "when the denominator is defined"; here it is defined, and it is never computed for Stage-2. Doing so reverses the direction of the result.

This computation assumes the within-run power-null reference is the same constant across the four scenarios, which is what "20 miners over a fixed 300 s horizon at active power" implies. If it is not — if the reference is instead computed per scenario over a scenario-dependent event path — then the four "Rel. energy reduction" figures are not on a common basis and **cannot legitimately be tabulated in one column at all**. Either way the current presentation is defective; the thesis must define the reference formally and report absolute energies alongside the ratios.

**Required:** define the power-null reference by equation; report absolute kWh per scenario; add energy per accepted block to Table 7.3; and restate RQ2 and the abstract as the marginal effect of the policy relative to the control, not as the total distance from a counterfactual.

### M4. The zero-duplicate and −87.9 % work results are artefacts of a nonce domain smaller than the per-round aggregate work, and the one realistic control was executed but not reported

Two separate problems compound here.

**(a) The domain is too small for the duplication result to mean anything outside the simulator.** In Stage-3 the matched PoW control performs 1,158,562 evaluations of which 216,190 are unique — 5.36 evaluations per distinct input. With ≈ 304 rounds, that is ≈ 3,811 evaluations per round against a **1,600-nonce domain**: the aggregate per-round work is 2.4× the entire search space, so 16 independent scanners must collide, and heavy duplication is arithmetically unavoidable. In deployed PoW the per-template input space (nonce plus extranonce rolling) exceeds per-round aggregate work by many orders of magnitude, and cross-miner duplication is correspondingly negligible. The duplication ratio is therefore a function of the chosen domain size, not a property of uncoordinated mining.

§6.4 does warn that the difficulty and domain "are not numerically comparable with the deployed Bitcoin difficulty or its effective header search space", and Table 7.2's note is careful. But the caveat is not attached to the claims that travel: "87.9 % fewer physical evaluations" appears in §7.3.2, in RQ4, in §8.1 and in the summary without it.

**(b) B0 — the only realistic PoW arm — is executed and then never reported.** §6.4 declares B0 as the "independent-template PoW baseline, in which miners search their own block templates", with five configurations × 30 seeds = **150 executed runs**. B0 appears nowhere in Chapter 7. The H1 ordering is given as "B1 > B2 > B3/C1" and Table 7.1 repeats it. B0 is precisely the arm that would establish whether independent-template mining exhibits any cross-miner duplication at all — and if, as the protocol's own logic implies, B0 shows approximately zero duplicates, then PoCol's work-efficiency advantage exists only against common-template controls that no deployed system implements.

Executing an arm and omitting it from the results, when that arm bears directly on the interpretation of the reported ones, is a reporting failure regardless of intent.

**Required:** report B0's duplicate rate alongside B1/B2/B3 in Table 7.1 and Figure 7.2, and state explicitly in the abstract and §8.1 that the duplication and work-efficiency contrasts are defined against common-template controls at a domain size chosen for auditability.

### M5. Chapter 5 no longer contains any security analysis, while Chapter 1 still promises one

The previous draft's §5.11 (double-spend and reorganisation resistance, nonce-domain violations, effects of inactive miners, Sybil attacks, comparison with existing mechanisms) has been deleted, along with §5.2.3 (adversary capabilities) and §5.2.4 (security properties). Chapter 5 now runs from the protocol description directly to §5.11 Summary.

Meanwhile §1.6 still tells the reader that "Chapter 5 specifies the PoCol consensus protocol, including … and preliminary security and robustness analysis. It also compares PoCol conceptually with representative consensus mechanisms such as PoW." Neither is now true.

I understand the motive: the earlier analysis was informal and its central proportionality claim was wrong. Deleting it removes an unsupported claim. But the result is that **a thesis proposing a new consensus protocol contains no security analysis of that protocol at all** — not even the range-membership verification argument, the template-grinding discussion, or the Sybil exposure, all of which are still referenced elsewhere (§4.3, §8.5) as things the design must confront. For a doctorate in this area, that is a gap that cannot stand.

What is needed is not the old text restored, but a modest, correct replacement: state precisely which Nakamoto-backbone assumptions PoCol changes (deterministic nonce ownership, bounded per-round domain, round closure by deadline or exhaustion), state what each change does to the standard argument, and identify which properties are conjectured versus open. Two or three pages of honest, bounded analysis would suffice — and §8.5 already describes exactly this as future work, which is the wrong place for it.

**Required:** restore a bounded security section to Chapter 5; align §1.6 with the actual content; and, at minimum, analyse (i) the effect of equal-range ownership on the hash-rate-proportionality of block discovery, (ii) an adversary that ignores its assignment and searches the full domain while honest miners idle after exhausting theirs, and (iii) the template-agreement liveness surface (a divergent template gates honest mining under §5.8.2, which has no analogue in PoW).

### M6. Specification and implementation still diverge, and one referenced policy no longer exists

* §5.6.3 specifies **equal** contiguous partitioning (Eqs. 5.4a–5.5), independent of hash rate. Stage-1 H4/H5 evaluates **hash-rate-weighted** ranges and reports them as a principal result (Figures 7.3, 7.4). The weighted rule is never specified — no equation, no placement in Chapter 5 — and weighting requires a verifiable on-chain hash-rate estimate that the protocol does not provide (§5.4.1 offers only optional self-declared hash power, which is unverifiable and trivially gamed). The thesis therefore evaluates an allocation rule it has not specified, using an input it cannot obtain.
* §5.6.6 states that "the protocol may apply either an energy-saving idle policy or a continuous-performance policy", but §5.6.6.2 has been deleted; only §5.6.6.1 remains. The continuous policy is referenced in §5.6.6, in §6.4's three-way comparative design, and in §7.3.2, but is defined nowhere.
* The equal-partition rule also has a measured consequence the thesis never connects to it. Under equal ranges and heterogeneous rates, round closure is governed by `maxᵢ(|Rᵢ| / rateᵢ)` — a maximum-order statistic — whereas the uncoordinated control closes at the first success anywhere in the domain. **That is precisely the 5.219× median round duration reported in Stage-3.** The result is presented as a configuration-specific trade-off; it is in fact a structural property of the allocation rule, and it will worsen as rate heterogeneity or miner count grows. Saying so would strengthen the thesis, not weaken it.

**Required:** specify the weighted allocation rule in Chapter 5 (or drop it from Chapter 7); restore or remove the continuous-performance policy; and derive the round-latency consequence of equal partitioning analytically, linking it to the Stage-3 measurement.

### M7. Evidential scale, and what the confirmatory experiments can support

Stages 2 and 3 — which carry RQ2, RQ3 and RQ4, i.e. every quantitative claim in the abstract — are run at 20 logical miners, a 300-second horizon, a 1,600-nonce domain, difficulty 1000, and 12 paired seeds. §6.4 defends each choice carefully and honestly labels the population a "mechanism-test population rather than a claim that 20 nodes represent a production permissionless network". That framing is correct and I do not object to the scale as such.

I do object to two things that follow from it. First, the **macro-scale family (Stage-1, 1,890 runs, N = 100–500) yields only accounting identities and a design invariant** — by the thesis's own disposition column, A1 is an ACCOUNTING IDENTITY, H3 is an ACCOUNTING IDENTITY VERIFIED, H1 is a DESIGN INVARIANT VERIFIED. None of these is a discovery; each follows from the definitions. The 1,890 runs therefore confirm that the simulator implements its own equations, which is a valuable integrity check but is not evidence about PoCol's behaviour. All *behavioural* evidence in the thesis comes from 108 runs of a 20-miner toy.

Second, **no scale-sensitivity study connects the two**. The mechanisms that matter — completion-time dispersion, idle residency, round latency under the max-order statistic, reassignment churn — are all expected to depend strongly on miner count and rate heterogeneity, and the thesis gives no evidence about how they move between 20 and 500 miners. A modest sweep (say 20 / 50 / 100 miners at the reduced horizon) would materially strengthen the external validity of RQ2–RQ4 at low cost.

**Required:** state plainly in the abstract and §8.1 that all quantitative outcome claims derive from the reduced-scale confirmatory family; add a scale sweep for at least the round-duration and idle-residency results.

### M8. The preregistered criteria were not met, and the thesis does not draw the conclusion

Both confirmatory experiments failed their gates: Stage-2's "useful-floor and churn criteria were not both met"; Stage-3's "accepted-block, median-duration, and useful-floor criteria were not simultaneously met". Reporting this is exactly right and I want to say so clearly — preregistration that only ever confirms is not preregistration.

But a preregistered design that misses its gates has a conclusion, and the thesis does not state it: **the preregistered hypothesis was not supported under the evaluated configurations.** Instead §7.3.2 and §8.1 convert the failure into a descriptive "energy-service trade-off", and Table 8.1 answers RQ2 with "Substantial". The gates presumably encoded what the candidate considered a worthwhile trade before seeing the data; that judgement should be honoured now. The correct summary is that PoCol as evaluated buys energy at a price in service and latency that the preregistered criteria classify as too high, and that identifying a configuration which meets the gates is open work.

**Required:** state the gate outcomes as the primary conclusion of Chapters 7 and 8; list the specific criteria and their thresholds (they are nowhere given numerically); and revise Table 8.1's RQ2 answer to reflect the marginal, not total, effect.

---

## 4. Substantive issues

* **S1 — The title now overstates the result.** "Highly Efficient Power Consumption" describes a thesis whose own finding is that partitioning does not reduce energy, that reductions come only from lower-power residency, and that the matched control produces more blocks faster. Consider retitling around coordination and the energy–service trade-off.
* **S2 — Chapter 7 is too thin for the evaluation chapter of a doctorate.** Ten pages, four figures (all Stage-1), no figure for either confirmatory experiment, and no narrative analysis of Stage-2/Stage-3 beyond three short paragraphs. The headline comparison (Stage-3) has no figure at all. Chapter 3, by contrast, runs to 34 pages.
* **S3 — Stage-3's per-block figure does not reconcile.** From the reported aggregates, `1 − 0.5505/0.6770 = 18.7 %`, not the stated ≈ 19.3 %. The difference is presumably ratio-of-means versus mean-of-ratios; whichever is used should be stated, since the two answer different questions.
* **S4 — The Stage-3 control lacks the treatment.** The PoW controls hash continuously by construction; PoCol idles. The contrast therefore conflates *coordination* with *duty-cycling*, and cannot attribute the 19.3 % per-block advantage to the protocol. The missing arm is a PoW control with an equivalent duty cycle (or, equivalently, a PoCol arm with no idle policy measured against W01 — which the data may already permit). Without it, RQ4's efficiency claim is not isolated.
* **S5 — Round latency and security are not connected.** A 5.219× longer round at fixed difficulty means proportionally slower chain growth, which in a cumulative-work system changes the confirmation-time-to-security relationship. §4.4.1 correctly says the Bitcoin confirmation analysis cannot transfer unchanged; Chapter 7 then reports a 5× latency increase without revisiting that point.
* **S6 — Chapter 3 retains its survey voice.** "In this survey" survives in several places (§3.2.7, §3.2 table captions, §3.8.2 note). Minor now, but it should go.
* **S7 — Two mis-citations survive the reference audit.** Tereshchenko & Kyrychenko (2024), *Analysis and justification of the use of existing blockchain solutions for the protection of digital assets*, is cited three times: for the Poisson derivation of Eq. (4.1), for the work/domain notation, and for "substantial energy use by major PoW networks". Xu, X., Sun, G., & Yu (2021), a PBFT-in-IoT paper, is cited for the fairness metric `F_dev = maxᵢ|rᵢ − hᵢ|` in §4.5. Neither supports the claim it is attached to.
* **S8 — No appendices.** For a thesis whose credibility now rests on preregistration, seed registries, a scenario matrix and decision rules, the absence of any appendix reproducing them is a structural omission, and the natural place to fix M1 and M2 in part.

---

## 5. Presentation and editorial

* **P1** — §8.4 is headed "Recommendations for Practitioners" but its content is a summary of four empirical findings; the practitioner recommendations that were present in the previous draft are gone. §8.3 ends abruptly after two paragraphs. Chapter 8 as a whole is under three pages and reads as truncated.
* **P2** — §1.6 describes a Chapter 5 that no longer exists (see M5) and a Chapter 7 structure that does not match the delivered one.
* **P3** — §4.3: "where 𝛽 s a design parameter" (missing "is"); "(Del Monte et al., 2020; Nakamoto, 2008))" (doubled parenthesis).
* **P4** — §7.2 and Table 7.1 render inline LaTeX and escape sequences into the running text: "(3031.5 \times 10000 / 3.6\times10^6 = 8.420833333)", "(2e-4)", "(7.1e-15)". These must be typeset properly.
* **P5** — Reporting precision: 8.420833333 kWh is quoted to ten significant figures throughout for a quantity defined by two-significant-figure inputs (141 TH/s, 21.5 J/TH). Quote the identity symbolically and the value to a sensible precision.
* **P6** — Table 7.1's caption ("replacing the obsolete PoW-versus-PoCol energy/carbon summary") addresses the previous draft's reader, not this thesis's reader. Remove the editorial trace.
* **P7** — Chapter 7's only section for results is §7.3 "Energy Consumption Results", under which work, service and latency results also appear. Restructure so the section titles match the content.
* **P8** — Stage-2/Stage-3 have no parameter table, no figures, and no seed-level results; Stage-1 has four figures and one summary table. The evidential weight and the presentational weight are inverted.
* **P9** — The Publications page states the Frontiers manuscript is accepted (03 Aug 2026) but cites an abstract URL; update to the published DOI before submission.

---

## 6. Chapter-by-chapter

| Ch. | Assessment |
|---|---|
| **1** | Much improved. RQ1–RQ4 are now narrow, answerable and matched to the evidence. §1.6 must be corrected (P2). |
| **2** | Unchanged in substance; still overlaps Chapter 3 and could be reduced to the primitives used later. |
| **3** | Substantially repaired: captions, table order, PoH characterisation, and most citation defects fixed. Residual survey voice (S6) and two surviving mis-citations (S7). |
| **4** | The strongest revision in the thesis. §4.4.2's separation of work redundancy from electrical energy is correct, clearly argued, and explicitly supersedes the earlier error. §4.3 now properly declines to inherit the Nakamoto threshold. |
| **5** | Specification remains detailed and careful, but has lost all security analysis (M5) and now contains a dangling policy reference and an unspecified allocation rule that Chapter 7 evaluates (M6). |
| **6** | Greatly improved in design and in the justification of parameter choices. Undermined by the absence of Stage-2/3 power parameters (M2) and by provenance claims that the cited artefact does not support (M1). |
| **7** | Honest and correctly hedged, but too thin (S2), misattributes RQ2 (M3), omits B0 (M4), omits the service-normalised comparison that reverses the Stage-2 conclusion (M3), and lacks the duty-cycled control needed to isolate RQ4 (S4). |
| **8** | Truncated and mislabelled (P1); does not draw the conclusion its own preregistered gates imply (M8). |

---

## 7. Conditions for re-submission

1. **Deposit and cite the real artefact.** Archived, versioned, DOI'd: Stage-1/2/3 code, seed registries, scenario matrix, preregistration document with numeric thresholds, raw run records, analysis scripts, checksum manifest. Name the commit in the thesis. Reconcile or retire the superseded code in the public repository (M1).
2. **Disclose every power parameter** for Stages 2 and 3 in a table, and add a sensitivity analysis over `P_idle/P_active` (M2).
3. **Restate RQ2 as a marginal effect**, define the power-null reference by equation, report absolute energies, and add energy per accepted block to Table 7.3 — including the finding that the no-floor control dominates on that metric (M3).
4. **Report B0**, and attach the finite-domain caveat to every travelling claim about duplication and physical-evaluation counts (M4).
5. **Restore a bounded security analysis to Chapter 5** and align §1.6 (M5).
6. **Specify the weighted allocation rule or drop it; restore or remove the continuous policy; derive the round-latency consequence of equal partitioning** (M6).
7. **Add a scale sweep** linking the 20-miner confirmatory results to the macro-scale family, and state the scale boundary in the abstract (M7).
8. **State the preregistered gate outcomes as the primary conclusion**, with the criteria and thresholds given numerically (M8).
9. **Add the duty-cycled PoW control** needed to isolate the RQ4 efficiency claim (S4).
10. **Retitle**, correct Chapter 8, fix the typesetting defects, and complete the reference audit (S1, S7, P1–P9).

Items 3, 4, 8 and 10 are editorial and analytical work on data already in hand. Items 1, 2, 5 and 6 are documentation and writing. Only items 7 and 9 require new runs, and both are small. I would expect this to be a matter of weeks rather than a re-execution of the research.

---

## 8. Questions for the defence

1. Where is the code, the seed registry and the preregistration for Stages 1–3? A reader following §6.6 today reaches a repository whose PoCol path still divides each miner's charged time by *N*. How should that reader reproduce the 8.420833333 kWh invariant?
2. What are `P_active`, `P_idle`, the reserve-standby power and the wake-transient power in Stages 2 and 3? How does the 55.05 % figure move if `P_idle/P_active` is doubled?
3. Table 7.3 gives the no-floor control a 53.83 % reduction. What, then, does the operating policy contribute — and why is 55.05 % the number that appears in the abstract?
4. Computing energy per accepted block from Table 7.3 puts S00 ahead of S01, S02 and S03. §4.4.2 says service-normalised energy is the right metric when the denominator is defined. Is it defined here, and if so what does that ordering mean for the thesis's claim?
5. B0 was executed — 5 configurations, 30 seeds, 150 runs. What was its duplicate rate, and why is it absent from Table 7.1 and Figure 7.2?
6. The Stage-3 control performs ≈ 3,811 evaluations per round against a 1,600-nonce domain. In deployed PoW that ratio is smaller by many orders of magnitude. In what sense does "87.9 % fewer physical evaluations" generalise beyond this domain size?
7. The PoW controls hash continuously; PoCol idles. How do you separate the effect of coordination from the effect of duty-cycling in the 19.3 % per-block figure?
8. Chapter 5 no longer analyses security, yet §1.6 says it does. Under equal-range ownership, is the probability that a given miner produces the round's block still proportional to its hash rate?
9. §5.6.3 specifies equal partitioning; Chapter 7 evaluates hash-rate-weighted ranges. Which is PoCol, and where does a verifiable hash-rate estimate come from?
10. Both preregistered gate sets were missed. What is the conclusion of a preregistered experiment whose criteria are not met?

---

*Prepared as an examiner's report on the version of the thesis identified above. Statements about the software artefact refer to the cited repository as currently published; file and function names are given so that each observation can be checked directly. Arithmetic derived from the thesis's own tables is shown so that it can be rechecked.*
