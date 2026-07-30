# Stage 7B — Replacement Map

TRUE in-place replacement of obsolete/false thesis claims. Branch
`thesis-v43-stage7-thesis-integration-2` (from analysis-2 `b7b61d20…`). Authoritative
input `Raed-Rasheed-draft-42-00.docx` (SHA-256 `2c3afdc5…`, byte-identical/unchanged).
Output `Raed-Rasheed-draft-44-00.docx` (SHA-256 `a31400bc…`).

**Policy:** every false/obsolete statement is **deleted or replaced in place** (red). The
original wording is preserved only in `STAGE_07B_CHANGE_LEDGER.csv`, never retained in the
revised thesis with an appended red notice. No "superseding notice" paragraph substitutes
for replacing a source sentence. 46 controlled changes in total (27 in-place prose
replacements, 7 deletions, 7 figure insertions, 1 table replacement, 2 table insertions,
2 heading renumberings).

## Abstract (EN + AR) — reconstructed in place

| Loc | Obsolete claim (deleted) | Replacement (red) |
|-----|--------------------------|-------------------|
| Abstract EN eval | "reduces total energy consumption by approximately 98–99 %" + kWh comparison | A1 accounting invariant 8.420833333 kWh; partitioning alone does not reduce energy; duplicate-identity elimination; idle-/participation-only reductions; proof-of-concept scope; H7 secondary |
| Abstract EN contrib | "collaborative mining can make PoW-class consensus substantially more energy-efficient" | duplicate-identity elimination under modeled assumptions; total energy invariant at matched hash rate/power; idle-/participation-only reductions |
| Abstract AR eval | Arabic 98 % / kWh claim | Arabic mirror of corrected EN eval (same scope) |
| Abstract AR contrib | Arabic "substantially more energy-efficient" | Arabic mirror of corrected contributions |

The EN and AR abstracts communicate the same corrected scope. No surviving 98–99 % figure,
obsolete kWh comparison, miner-count energy scaling, unqualified energy-efficiency claim,
fairness claim, or full-network stale/fork claim.

## Chapter 5 (design)

| Loc | Obsolete | Replacement (red) |
|-----|----------|-------------------|
| §5.6.4 heading | "Fairness Across Rounds" | "Range-Assignment Balance Across Rounds" |
| §5.6.4 body | intrinsic-favourability / fairness framing | modeled range-assignment balance only; explicitly **not** a reward/incentive/participation/economic/Sybil/proof-of-effort fairness claim |

## Chapter 6 (methods) — see `STAGE_07B_METHODS_AUDIT.md`

| Loc | Obsolete | Replacement (red) |
|-----|----------|-------------------|
| §6.4 design | ad-hoc "compare the performance of two consensus protocols" over 10 logs | frozen matrix: 63 groups × 30 seeds = 1,890 physical executions; unique run-execution hashes; seed-matched unit; B3/C1 one dataset; integer apportionment; exact candidate/B2 accounting; active/idle/offline states; zero-block/NA; H1 30 clusters/150 pairs; bootstrap/permutation; Holm; H7 secondary |

## Chapter 7 (results) — see `STAGE_07B_RESULTS_AUDIT.md`

| Loc | Obsolete claim (deleted/replaced) | Replacement (red) |
|-----|-----------------------------------|-------------------|
| §7.2 objectives | "ascertain whether PoCol can reduce energy … to what extent are … reduced" | neutral A1/H1/H3–H8 characterisation objectives |
| §7.2 Table 7.1 intro | "PoCol consumes relatively much less energy than PoW … higher throughput" | corrected-table intro (invariant + where design does/does not change quantities) |
| §7.2 old Table 7.1 caption | "Summary of the main PoCol and PoW evaluation metrics …" | **deleted** (corrected red caption present) |
| §7.3.3 stale | "a stale-rate above 70 % … due to designed efficiency" | H7 secondary single-height diagnostic framing; not a chain-wide fork/security rate |
| §7.4.1 energy | "PoW consumed ≈ 7.90 kWh …" | A1 invariant 8.420833333 kWh; partitioning alone does not reduce energy |
| §7.4.1 per-block | "PoCol has a much lower cost per block than PoW" | coverage effect + NA policy, not a total-energy reduction |
| §7.4.1 time-series | "PoW curves rise steeply with miner count …" | no miner-count energy scaling (invariant across N) |
| §7.4.2 | "achieved significantly higher energy efficiency …" | equal total energy; only duplicate elimination / idle / participation |
| §7.4.3 carbon | "Figure 7.8 compares total carbon footprint …" | carbon is linear in energy; no structural carbon reduction |
| §7.4.3 trade-off | "PoCol simultaneously improves throughput and reduces energy" | invariant energy; H7 secondary only; bounded finding |
| §7.4.3 idle | idle-savings framing | verified H3 identity (570/570; residual 7.1e-15 kWh) + H5 trade-off |
| §7.6.1 RQ | "PoCol drastically lowers total energy … relative to PoW" | redundancy removal ≠ total-energy reduction; A1; idle-only reductions; exploratory throughput |
| §7.6.1 close | "powerful path toward sustainable blockchain consensus" | bounded claim (redundancy removal + idle trade-off) |
| §7.7 summary | "significant benefits … reduced energy use … total carbon footprint" | invariant; established results = H1 + idle trade-off |
| §7.7 summary | "substantially improve the energy profile of PoW-style consensus" | removes duplication + idle trade-off, no total-energy reduction |
| §7.7 limitation | "stale-block rate increases exponentially" | H7 secondary diagnostic rises with delay/size; not chain-wide |

## Chapter 8 (conclusion) — see `STAGE_07B_RESULTS_AUDIT.md`

| Loc | Obsolete | Replacement (red) |
|-----|----------|-------------------|
| §8.1 outcomes | "significantly reduced total energy consumption and CO2 emissions" | duplicate removal + idle reduction; total energy invariant; H7 secondary |
| §8.2 RQ2 | "requires substantially lower energy" | bounded by invariant; duplicate-identity elimination; idle-/participation-only |
| §8.3 empirical | "noticeable decrease in energy consumption and carbon emissions compared to PoW" | H1 (150 pairs/30 clusters; B3/C1=0) + idle-driven only; B0/B1 abstractions; B3/C1 one dataset |
| §8.3 conceptual | "basic idea is reducing energy consumption" | reduce redundant duplicated computation (not a total-energy claim) |
| §8.4 caution | "PoCol's sustainability benefits" | bounded efficiency benefits (redundancy removal + idle trade-off) |

## Figures and tables — see `STAGE_07B_FIGURE_TABLE_AUDIT.md`

- **Removed (deleted, not linked):** obsolete Figures 7.4–7.8 (PoW-vs-PoCol energy/carbon
  curves implying miner-count scaling and 98–99 % reduction).
- **Inserted (embedded images + red captions):** Figures 7.4–7.10 = Stage-6A
  fig02/fig01/fig03/fig04/fig06/fig07/fig08; fig04 caption carries no positive-fairness
  wording.
- **Tables:** obsolete Table 7.1 replaced by a corrected 7-row Stage-6A summary; obsolete
  energy/carbon numeric data tables removed; new Table 7.2 (H1: 150 pairs / 30 clusters;
  B3/C1 = 0, one dataset) and Table 7.3 (conditional epab: total/defined/undefined/reason)
  inserted.
