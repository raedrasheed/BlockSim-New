# Stage 7 — Thesis Insertion Map

Pre-insertion audit of `docs/Raed-Rasheed-draft-42-00.docx` (SHA-256
`2c3afdc5…`, 2203 paragraphs, 175 heading-styled) against the corrected Stage-6A
analysis (branch `thesis-v43-stage6-analysis-2`, commit `b7b61d20…`). Each location that
conflicts with the corrected findings is listed with the action taken in the examiner-
review copy `Raed-Rasheed-draft-43-00.docx`. All inserted/modified text is red
(`w:color=FF0000`); original text is preserved in its original formatting. Paragraph
indices are body `<w:p>` positions in the merged document.

## Conflict classes located and actions

| # | Location (¶ / §) | Current wording (excerpt) | Class | Action | Corrected source |
|--|--|--|--|--|--|
| 1 | Abstract EN ¶33 | "reduces total energy consumption by approximately 98–99% (…0.454 kWh versus 33.078 kWh at 400 miners)" | obsolete energy result; miner-count scaling | ADD LIMITATION (red correction: A1 fixed-horizon invariant 8.420833333 kWh; partitioning alone does not reduce energy) | STAGE_06_RESULTS_REPORT; a1_invariant.json |
| 2 | Abstract EN ¶34 | "collaborative mining can make PoW-class consensus substantially more energy-efficient" | energy overclaim | ADD LIMITATION (red: duplicate-identity elimination, not total-energy reduction) | STAGE_06_CLAIM_CLASSIFICATION |
| 3 | Abstract EN ¶32 | reward mechanism "designed to improve fairness" | fairness wording | ADD LIMITATION (red scope: modeled reward-share proportionality only) | STAGE_06_LIMITATIONS |
| 4 | Abstract AR ¶40 | Arabic contributions mirror | must mirror EN scope | ADD LIMITATION (red Arabic correction, RTL) | STAGE_06_RESULTS_REPORT |
| 5 | §5.6.4 heading ¶1326 | "Fairness Across Rounds" | fairness wording | REPLACE heading → "Range-Assignment Balance Across Rounds" (red) | STAGE_06A_CORRECTION_REPORT |
| 6 | §7.4.1 ¶1816 | "reduction of approximately 98.3% from PoW" | obsolete energy result | ADD LIMITATION (red: A1 invariant) | a1_invariant.json |
| 7 | §7.4.1 ¶1824 | "PoW curves rise steeply with miner count, whereas the PoCol curves stay compressed" | forbidden miner-count energy scaling | ADD LIMITATION (red: energy does not scale with N at fixed aggregate hash/power) | STAGE_06_RESULTS_REPORT |
| 8 | §7.4.2 ¶1828 | "significantly higher energy efficiency" | energy overclaim | ADD LIMITATION (red: equal total energy; advantage is duplicate elimination) | STAGE_06_CONFIRMATORY_RESULTS |
| 9 | §7.4.3 ¶1834 | "simultaneously improves throughput and reduces energy … sharp increase in stale blocks" | energy overclaim + H7 over-scope | ADD LIMITATION (red: energy invariant; H7 SECONDARY single-height count-rate only, N separate, no binomial) | STAGE_06_SECONDARY_DIAGNOSTICS; STAGE_06A_H7_INTERVAL_AUDIT |
| 10 | §7.4.3 ¶1835 | idle-policy description | needs alignment | ADD (red: verified H3 identity residual 7.1e-15; H5 completion-balance vs idle-energy trade-off) | STAGE_06A_H3_IDENTITY_AUDIT |
| 11 | §8.2 ¶1874 | RQ2 "energy-saving potential of PoCol" | energy answer must reflect invariant | ADD LIMITATION (red) | STAGE_06_RESULTS_REPORT |
| 12 | §8.3 ¶1879 | empirical contribution "noticeable decrease in energy consumption" | energy overclaim; B0/B1; B3/C1 | ADD LIMITATION (red: duplicate-elimination + idle/participation; B0/B1 not real BTC; B3/C1 one dataset) | STAGE_06_CLAIM_CLASSIFICATION; STAGE_06A_DEPENDENCE_AUDIT |
| 13 | §7.1 ¶1702 | (start of results chapter) | governing notice | ADD red paragraph summarising A1/H1/H3–H5/H6/H8/H7 governing findings | STAGE_06_RESULTS_REPORT |

## Zero-block / undefined-metric, B3-C1, and H7 scope

- The governing correction notice (row 13) and rows 9–12 explicitly state: zero-block runs
  are retained and block-normalised metrics stay NA (conditional on ≥1 accepted block);
  B3 and C1 are two interpretations of one physical dataset (never independent samples);
  H7 is a single-height stale-race SECONDARY diagnostic (count-rate, N separate, no
  binomial/Wilson), not a chain-wide/fork/security result. Table 6.1 (¶1561–1581) already
  carries the correct frozen parameters (141 TH/s, 21.5 J/TH, 10,000 s, 0.42 s, 600 s) and
  is KEPT; the obsolete results narrative that contradicts those same parameters is
  corrected in red.

## Items KEPT (no conflict)

Chapters 1–4 background, Chapter 3 literature review, the PoCol protocol specification
(Chapter 5 except the 5.6.4 heading), Chapter 6 methods/Table 6.1 parameters, references,
and all front matter are retained unchanged. Only claims conflicting with Stage-6A are
touched.
