# Stage 8X-NR — Pilot Report

**Matrix:** N ∈ {100, 300, 500} × 5 arms × 2 dedicated pilot seeds = 30 physical runs.
**Pilot seeds:** derived from `…/pilot/{0,1}` of the Stage 8X-NR master label; never
used for inference. **Runtime:** 0.40 s wall for the full pilot; memory < 100 MB.
**Verdict: PASS — all 13 validation items of brief §31 hold; frozen for primary.**

## Validation checklist (brief §31)

| Item | Check | Result |
|---|---|---|
| 32-bit nonce semantics | `S = 2^32` asserted; all phases/arcs reduced mod 2^32 (Test 1) | pass |
| template/extranonce renewal | CONV: 5.4482e8 template epochs per miner per run, equal to ⌊T·h/2^32⌋ per round summed; MT: 5.4482e8 network epochs; every exhaustion rolls a new template | pass, exact integers |
| conventional PoW traversal | ZERO resets counted (epochs+rounds), OFFSET resets = 0, exhaustions equal in both | pass |
| random offset generation | start_i ~ U(0, 2^32−1) per miner per run from a dedicated stream; distinct across miners | pass |
| PoCol partitioning | full coverage 2^32, zero overlap, size spread = 1 at all five N (Tests 2–4) | pass |
| nonce-value reuse counters | round scope ρ_nonce = 0.9999999919 at N=100 vs predicted 1 − 2^32/(N·h·Δ̄); PC M_≥2 = 0, m_max = 1, O_max = 0 in every round | pass |
| exact-input counters | CONV ρ_exact = 0 exactly; MT ρ_exact = (N−1)/N exactly at epoch scope (0.9900 / 0.9967 / 0.9980); PC 0 | pass |
| analytical expectations | sub-sweep offset mean pairwise overlap 121 441.3 vs predicted W²/S = 121 441.4; MT blocks/run 0–1 vs predicted mean T/(600N) | pass |
| block interval | CONV-OFFSET pooled mean 556.9 s (34 blocks, 2 seeds; SE ≈ 103 s) vs 600 s nominal — within 0.5σ | pass |
| difficulty | q·D·2^32 = 1 identically; one D_N shared by all five arms | pass |
| runtime | 0.40 s / 30 runs → primary (750 runs) projected < 30 s | pass |
| memory | interval arithmetic only; no 2^32 materialisation anywhere | pass |
| energy identities | state-time conservation and W = Σ evaluations both 0.0 relative error (exact integer ticks) | pass |

## Findings previewed by the pilot (not inferential)

1. **Round-scope saturation is real and predicted.** Every active miner sweeps the
   2^32 domain every 18.355 µs, so round-scope U_nonce = 2^32 and ρ_nonce ≈ 1 for
   *all* arms, PoCol included (PoCol's repetition is its own miners re-sweeping
   their ranges across template epochs). The cross-miner columns are what
   discriminate: M_≥2 = 2^32 and m_max = N for all PoW arms; M_≥2 = 0 and
   m_max = 1 for PoCol.
2. **MT block collapse.** With one common template over a 2^32 domain, only
   2^32 distinct inputs exist per epoch, so the matched-template comparator's
   distinct-input throughput is h, not N·h: pilot MT runs produced 0–1 blocks vs
   15–19 for CONV/PC, with intervals scaled ×N. This is the corrected-domain
   analogue of Stage 8X's 0.33 duplicate ratio, taken to its 2^32 extreme.
3. **Energy is unmoved by nonce coordination.** C_total is identical across all
   five arms at every N (t_active equal, P equal ⇒ E equal — brief §17 verified in
   test); PC's low-power residency is F_low = 9.3e-10 … 4.7e-8, i.e. an energy
   saving of at most ~5e-8 fraction at α = 0.

## Deviations / notes

* MT rounds are longer than the horizon at these N, so MT latency statistics rest
  on very few blocks per run; the primary matrix reports them with explicit run
  counts and does not over-interpret them.
* MT-ZERO co-discovery: all N miners evaluate the winning input in the same tick;
  each block carries N−1 stale duplicates. Artifact of the synchronized control,
  reported as such.
* Pilot outputs live under `outputs/stage8x_nr_pilot_*` and are excluded from all
  inferential statistics.
