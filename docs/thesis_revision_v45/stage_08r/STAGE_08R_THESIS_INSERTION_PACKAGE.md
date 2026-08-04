# Stage 8R — Thesis Insertion Package

**No thesis DOCX or PDF is edited by this stage.** Insertion-ready text for a later,
separately-authorized integration stage. Every number traces to `stage8r_results.json`
and the frozen `STAGE_08R_RUN_DATASET.csv`. The mandatory caveats of
`STAGE_08R_LIMITATIONS.md` accompany any use.

## I.1 Design paragraph

> Following the Stage-8M finding that the frozen operational-floor controller exceeded its
> service limits, a revised idle and reserve-control policy within PoCol was specified,
> implemented behind a legacy-equivalent default, and evaluated in a fresh preregistered
> experiment: four scenarios (no-floor control, legacy controller, revised controller, and
> an exploratory reassignment arm) on twelve fresh SHA-256-derived seeds, with frozen
> hysteresis thresholds (0.78/0.80/0.82 × H0), predictive wake-ahead bounded by observable
> progress, one live activation batch per breach episode, and a deterministic cooldown.
> The legacy mode reproduces the frozen Stage-8M behaviour bit-exactly, and all
> deterministic integrity gates pass on every run.

## I.2 Results paragraph (required wording preserved)

> Against the legacy controller under the same seeds, the revised policy increased
> accepted blocks (+2.7 per run, 95 % CI [+1.8, +3.7], exact paired p = 0.0005,
> Holm-corrected), reduced below-floor time and floor-deficit area (p = 0.0002), and cut
> floor-unattainable decision churn nineteen-fold (999.8 → 51.8 per run) — while seating
> more activation requests than the legacy controller (312.8 → 593.7), so the
> preregistered churn hypothesis on request volume was refuted and is reported as such.
> The revised controller retained the low-power-state accounting benefit (57.3 % mean
> relative reduction against the within-run power-null counterfactual, 95 % CI
> [57.2 %, 57.5 %]). However, the preregistered operational-acceptance limits were not
> met: accepted-block throughput reached only 0.852 of the no-floor control (limit 0.90)
> and the system remained below the 0.80 × H0 floor for 274 s of the 300 s horizon
> (limit 15 s). Under the frozen joint rule, **the revised-policy claim is not licensed**.
> The dominant cause is structural: the reserve pool (four reserves, 1 000 H combined)
> cannot restore a 3 200 H floor once two to three primaries exhaust, so no decision
> policy within this frozen population can attain the floor. The historical Stage-8M
> conclusion — a large low-power-state energy difference with exceeded service/capacity
> limits — stands unchanged.

## I.3 Main table

| contrast (R02 vs R01, n = 12) | Δ mean | 95 % CI | exact p | Holm |
|---|---|---|---|---|
| accepted blocks (H-R1) | +2.67 | [+1.75, +3.67] | 0.00049 | supported |
| below-floor duration s (H-R2) | −0.54 | [−0.60, −0.46] | 0.00024 | supported |
| floor-unattainable count | −948.1 | [−990, −905] | 0.00024 | supporting |
| activation requests (H-R3) | +280.9 | — | 1.000 | **refuted** |
| H-R4 acceptance (vs R00) | blocks ratio 0.852; below-floor 274 s | — | — | **FAIL** |
| H-R5 energy benefit | rel. reduction 0.574 | [0.572, 0.575] | — | PASS |
| overall claim | — | — | — | **NOT LICENSED** |

## I.4 Energy attribution sentence

> The retained saving is attributable, in declared components, to primary range-idle
> residency (0.0060 kWh per run) and reserve standby (0.0047 kWh), with a small wake
> transient (0.0008 kWh); activated-reserve hashing cost only 0.0004 kWh. Range-idle and
> reserve/wake components are reported separately throughout.

## I.5 Exploratory note (R03)

> An exploratory arm adding bounded 25-nonce suffix reassignment produced the largest
> floor improvement of any arm (below-floor 223 s vs 275 s; deficit area −19 %) at no
> throughput gain; being exploratory, it determines no verdict and motivates, at most, a
> future preregistered experiment.
