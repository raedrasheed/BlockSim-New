# Thesis Revision Impact

**Branch:** `claude/fix-energy-round-semantics`
**Status:** the thesis document has **not** been edited. This note records, for a
later thesis revision, exactly which claims the corrected simulation
(Phases B1–B6) invalidates or changes, and what the defensible replacement
statements are. It is written so a supervisor/examiner can check each item
against the code and the data in `results/corrected/`.

---

## 1. Claims that must be **withdrawn or rewritten**

### 1.1 The ~98–99 % energy-saving claim for PoCol — **withdraw**

- **Old claim:** PoCol reduces energy consumption by ~98–99 % relative to PoW.
- **Corrected finding:** **0.0 % difference.** Both protocols consume an identical
  8.4208 kWh for the 10 000 s run at every miner count 100–500 (paired
  PoCol−PoW difference 5.9 × 10⁻¹⁷ kWh). See
  `docs/CORRECTED_EXPERIMENT_REPORT.md` §1 and `results/corrected/`.
- **Why the old figure arose:** three defects, all fixed —
  (a) energy charged per produced block instead of integrated over wall-clock
  time; (b) hash-rate normalised as `H_net·(hp/100)`, correct only at N = 100;
  (c) a guaranteed-single-nonce success model that suppressed forks/exhaustion.
- **Defensible replacement:** "Under corrected wall-clock energy accounting, PoCol
  is **energy-neutral** relative to PoW: both consume the same aggregate energy
  because both keep the same hardware powered for the same duration. PoCol
  redistributes *which* miner wins and *how* the search space is partitioned, not
  *how much* hardware runs."

### 1.2 Any figure/table showing PoCol energy far below PoW — **replace**

- Replace with the corrected table (Report §1): PoW = PoCol = 8.4208 kWh at every
  N, i.e. a flat, overlapping pair of lines at the physical bound
  `P_network · simTime`.

### 1.3 Any claim that PoCol's advantage grows with miner count — **withdraw**

- The old scaling was an artefact of the `hp/100` normalisation. Corrected energy
  is **independent of N** for both protocols.

### 1.4 Fork/stale-rate comparisons based on the old model — **replace**

- Old runs reported very high stale rates (62–76 %). Corrected stale rate is ~0 %
  for both protocols (Report §3). Any narrative attributing low staleness to PoCol
  as a distinguishing benefit is unsupported: PoW is equally fork-free here.

---

## 2. Claims that **survive**, possibly with rewording

- **PoW/PoS order-of-magnitude gap and the E = P·T sanity check.** Unaffected —
  these concern the energy-accounting framework, which is now *more* rigorous.
- **Analytical validation to machine precision.** Strengthened: the corrected
  meter reproduces `E = P·T` exactly (`tests/test_energy_invariants.py`).
- **PoCol's mechanism description** (nonce partitioning, collaborative
  assignment). The *mechanism* is intact; only its *energy consequence* changes.

---

## 3. New, honestly-reportable results to **add**

1. **PoCol is energy-neutral, not energy-saving** (headline correction).
2. **Exhausted-round overhead** unique to PoCol (~2.8 per run; PoW = 0): a
   latency cost of finite nonce domains, reported rather than hidden
   (Report §4).
3. **Controlled block-interval calibration**: both protocols realise ~590 s
   accepted intervals (target 600 s), so the comparison is fair (Report §2,
   Methodology §5).
4. **Reproducibility package**: 300 paired runs, fresh process each, with
   `configuration.json` and `reproducibility_manifest.json`
   (Methodology §7).

---

## 4. Suggested revised thesis contribution statement

The energy contribution should be reframed from a *quantitative saving* to a
*methodological and mechanistic* contribution:

> "This work contributes a consensus-aware, physically grounded energy-accounting
> methodology for BlockSim and applies it to a collaborative consensus protocol
> (PoCol). The corrected analysis shows that PoCol, as specified, is
> **energy-neutral** with respect to Nakamoto PoW under equal hardware and equal
> block-production targets. Any energy benefit from collaborative consensus would
> require an explicit power-management or reduced-aggregate-hash-rate mechanism,
> which we identify as the necessary direction for future work rather than a
> result of the present design."

This is honest, still a genuine contribution (a corrected methodology plus a
clear negative/neutral result and a precise statement of what a real saving would
require), and it is fully supported by the committed code, tests, and data.

---

## 5. Where the evidence lives

| Evidence | Location |
|---|---|
| Corrected methodology | `docs/CORRECTED_SIMULATION_METHODOLOGY.md` |
| Corrected results + honest conclusion | `docs/CORRECTED_EXPERIMENT_REPORT.md` |
| Defect audit (root causes) | `docs/POCOL_ENERGY_AND_EVENT_AUDIT.md` |
| Raw + summary data (300 runs) | `results/corrected/` |
| Tests enforcing every rule | `tests/` |

**No thesis file has been modified on this branch.** The revision itself is left
for a later, separately reviewed step, once these corrected results are accepted.
