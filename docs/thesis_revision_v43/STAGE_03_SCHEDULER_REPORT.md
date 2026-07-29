# STAGE 03 — Scheduler, Round-State, and Stale-Block Correction Report

Corrects the PoCol simulator's round/event-validity/difficulty/finite-domain/
stale semantics. **Result:** the Stage-1/2 "stale explosion" (35–86 %) is shown
to be an artefact of scheduling a block event for every miner; with the
finder-based model the corrected legitimate stale rate is **0 %** under the
modelled network, PoCol at 100–500 miners now completes in **1–3 s** (was timing
out beyond the 240 s cap), and the Stage-2 energy invariant (8.4208 kWh) is
preserved. Scheduling now costs O(N) queue, not O(N·blocks). No thesis file was
touched.

Companion docs: `STAGE_03_EVENT_SEMANTICS.md`, `STAGE_03_DIFFICULTY_AUDIT.md`,
`STAGE_03_STALE_CLASSIFICATION.csv`, `STAGE_03_BEFORE_AFTER.csv`.
Raw data + diagnostics (read-only): `results/thesis_revision_v43/stage_03/`.

---

## 1. Root cause and fix

**Root cause (M-1).** Every round, every one of the `N` miners was scheduled a
`create_block` event and credited with a block whenever its (stale) parent still
matched — even though its disjoint nonce range contained no solution. Those
"blocks" were **finite-domain non-solutions mislabelled as stale blocks**, and
scheduling `N` events/round produced the O(N·blocks) slowdown.

**Fix (finder-based model).** Only miners whose range actually contains a drawn
solution ("finders", `k ~ Poisson(p·S)`, ≈ 2/round) are scheduled a block event,
each stamped with an immutable `EventIdentity`. On firing, every event is
classified (`round_state.classify_event`) against the miner's **local** tip and
acted on: valid winner → one round transition; legitimate propagation competitor
→ genuine stale; obsolete/invalid → rejected (never a stale/block/reward/round
advance); finite-domain exhaustion → new template generation (never a block).

## 2. Before / after (PoCol, mean over seeds)

| Miners | old stale % (thesis) | corrected legit stale % | obsolete rejections | accepted blocks | exhausted rounds | queue peak | runtime |
|---|---|---|---|---|---|---|---|
| 100 | 35.71 | **0.00** | 19.4 | 16.2 | 2.4 | 106 | 1.1 s |
| 200 | 68.14 | **0.00** | 23.7 | 18.0 | 3.3 | 208 | 1.6 s |
| 300 | 78.40 | **0.00** | 15.0 | 16.7 | 3.3 | 306 | 2.1 s |
| 400 | 82.75 | **0.00** | 26.3 | 17.3 | 2.7 | 409 | 2.7 s |
| 500 | 85.67 | **0.00** | 22.2 | 15.4 | 3.2 | 519 | 2.9 s |

> The reduction from 35–86 % to 0 % resulted from **excluding obsolete scheduled
> events that did not represent valid competing blocks** (loser miners whose
> range held no solution). The remaining 0 % reflects legitimate propagation
> competition under the implemented network model: with a 0.42 s propagation
> delay, two finders essentially never find within the propagation window. When
> the delay is enlarged (test 14, `bdelay = 300 s`), legitimate propagation
> stales do appear and are correctly counted as stale — the machinery is present,
> the rate is simply ~0 at realistic delay.

PoW baseline is unchanged: stale 0 %, energy 8.4208 kWh, all seeds (see stale
CSV). Energy is identical to Stage 2 for both protocols at every miner count.

## 3. Difficulty and block-rate (see DIFFICULTY_AUDIT)

`p = 1/(H·B) = 1.182e-17`, `target ≈ 1.369e60`, `target_version = 1`,
`lambda = H·p = 1/600 s⁻¹`, independent of miner count.

**Seeded block-interval validation** (unbounded waiting-time abstraction, section
13): seed 20260729, N = 200 000 samples, expected mean 600.0 s, **observed mean
600.85 s**, SE 1.35 s, 95 % CI [598.21, 603.48] (contains 600), relative error
**0.14 %** — statistically consistent with the configured target.

The PoCol *effective* interval (finite-domain, incl. exhaustion) is reported per
run in the stale CSV (`eff_interval_s`, ≈ 550–900 s across seeds); it is measured,
not forced to equal B.

## 4. Reconciliations (section 19)

**A. Event classification (all PoCol runs):**
```
scheduled events (717) = processed valid (314)
                       + legitimate competitors (0)
                       + obsolete rejected (403)
                       + cancelled (0, lazy validation)
                       + remaining beyond cutoff (0)
```
`717 = 314 + 0 + 403`, unfired `= scheduled − processed = 0`. Exact.

**B. Stale reconciliation:** all recorded stale blocks = legitimate propagation
competitors that lost (0 at realistic delay) + other valid fork categories (0).
Obsolete rejections (403) are **not** stale.

**C. Round reconciliation:** per run, `rounds_started (start_round calls) =
accepted-block transitions + 1 genesis round + 1 incomplete round at cutoff`.
Finite-domain **exhaustion** is a template-generation refresh *within* a round's
`start_round` (recorded as `exhausted_rounds` / `template_refreshes`), not a
separate round; it never produces a block.

**D. Performance scaling** (mean): queue peak ≈ N (one propagation burst),
runtime grows ~linearly with N (1.1 s→2.9 s for N=100→500), runtime per processed
event ≈ constant. This is O(N) per accepted block, not the previous
O(N·stale-blocks).

## 5. Energy interaction (Stage 2 preserved)

All 84 tests pass, including the 20 Stage-2 energy tests and 11 journal tests,
unchanged. Diagnostic energy is 8.4208 kWh for PoW and PoCol at every miner count
and seed. The PoW `/100` fix and PoCol wall-clock model are untouched; obsolete
rejections do not erase already-consumed energy nor add energy after
invalidation (section 10).

## 6. Idealization and boundary (Path A)

A centralized round coordinator is assumed only for **template supply** (each new
round/refresh gets a fresh `template_id` / `template_generation_id`); the round
**state each miner acts on is local** (its own tip), so miners hold different
local rounds during propagation delay. The distributed common-template agreement
protocol is **not** implemented (Path A) — this is an explicit simulation
assumption, not a claim of implemented agreement.

## 7. Limitations / deferred

- Legitimate stale rate is ~0 at realistic delay (single-solution-dominated
  rounds); a richer multi-solution-collision regime would need larger delay or a
  different template model — noted, not forced.
- B0–B3 / C1–C2 scenarios, idle policy, heterogeneous hash rates, and the 30-seed
  matrix remain Stage 4/5.
- The Bitcoin recipient re-open-mining sub-percent energy gap (Stage 2 note)
  remains out of scope.
