# Stage 2A — Known Limitations

Honest scope statement for the Stage-2A executable PoCol scientific core. None of these
affect the acceptance gates; they bound what the core does and does not claim.

## Modeling scope

1. **Success model is B (exact without-replacement sampler), not full PoW inversion.**
   A real SHA-256 digest of `header‖nonce` is computed and counted for every searched
   nonce (genuine per-nonce work), but the *success predicate* is membership in a
   deterministically sampled winning-nonce set rather than `digest < target`. This was
   chosen (and recorded in `search.SUCCESS_MODEL`) to give a deterministic, matched success
   position across the CONTROL/POCOL_IDLE pair (SCI-7) and a reproducible test suite. A
   difficulty-target predicate (`Template.target`, `target_for_difficulty`) is implemented
   and available; switching the predicate to `digest < target` would make round durations
   probabilistic and is out of scope for the confirmatory core (no dynamic difficulty).

2. **Confirmatory two-power energy form.** Energy uses the canonical per-state powers with
   `P_offline ≤ P_listen = P_reserve = P_registered ≤ P_hash` and a transient `P_wake`.
   The matched energy experiment reduces to the two-power identity
   `E_i = P_active·t_active + P_idle·t_idle`; richer per-state schedules are supported by
   the residency ledger but not exercised by the experiment.

3. **Single winning nonce per round by default.** `make_template(n_winners=1)` is used in
   the confirmatory core. Multiple winners are supported by the sampler but not used, so
   the first solver deterministically ends the round.

4. **Homogeneous batch size.** Every miner uses the same declared `batch_size` per
   `HashWorkEvent`; heterogeneity is expressed through per-miner `hash_rate`
   (`config.hash_rate_for`), not batch size.

## Integration scope

5. **BlockSim adapter is minimal and additive.** `adapter.run_pocol_stage2` maps a
   BlockSim-style config to `Stage2Config` and returns a declared result schema
   (`stage2a.1`). It does not embed the PoCol core inside BlockSim's own event loop or
   node/network model; it is a documented entry point that runs the standalone core and
   returns results. The legacy simulator and the standalone demo are untouched.

6. **Reserve set fixed once per run.** The participation/reserve pool
   (`reserve_miner_ids`) is computed once from the genesis population and reused each round.
   Dynamic reserve churn across rounds is not modeled.

## Determinism / performance

7. **Search cost scales with the nonce domain.** Real SHA-256 is computed per searched
   nonce, so large `nonce_domain_size` values increase runtime linearly. The confirmatory
   and test configs use modest domains (≤ 4000) to keep the suite fast.

8. **No concurrency.** The event loop is single-threaded and deterministic by design
   (seeded sampler, no wall-clock / RNG / network), which is what makes the counts in the
   test report reproducible.

## Explicit non-claims

9. **Nonce partitioning is NOT an energy-saving mechanism.** SCI-5 proves that with
   `P_idle == P_active` the saving is exactly `0.0`; the reported saving comes only from
   post-range-exhaustion low-power residency (the idle policy within PoCol).

10. **A1 is the fixed accounting invariant, not a demo output.** A1 is 141 miners × 21.5 W
    × 10 000 s = 8.420833333 kWh. No smaller demo/confirmatory scenario is labelled A1.
