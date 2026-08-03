# Stage 2B — Known Limitations

Honest scope statement for the Stage-2B target-coupled / causal-search PoCol core. None of
these affect the acceptance gates; they bound what the core does and does not claim.

## Modeling scope

1. **Success is a real target-coupled digest test, single-hash.** A nonce succeeds iff
   `sha256_int(header, nonce) <= target` with a fixed per-round target
   (`target = floor((2^256−1)/difficulty)`). This is a genuine proof-of-work success
   predicate over a finite domain; it is not a full double-SHA256 Bitcoin header nor a
   variable-length extranonce. No dynamic difficulty is used in the confirmatory core.

2. **Deterministic, seeded headers.** Each round's template header is
   `SHA256("{RoundID}|{difficulty}|{D}|{seed}")`, so runs are fully reproducible (no
   wall-clock / RNG / network). The per-nonce success probability is `p = (target+1)/2^256`;
   for the default confirmatory config `p = 1e-3`, giving a realistic mix of accepted and
   zero-solution rounds.

3. **Planned batch-completion timing (design B).** Hash work is committed at the batch's
   completion time; the scheduler's read-only seat-time scan determines that completion
   time (including the winning nonce's exact time when a solution lies in the batch). Both
   the seat-time scan and the dispatch-time commit compute the same deterministic digests;
   the ledger and all state mutation happen only at the dispatch (completion) time.

4. **Confirmatory two-power energy form.** The matched energy experiment reduces to
   `E_i = P_active·t_active + P_idle·t_idle`; richer per-state power schedules are supported
   by the residency ledger but not exercised by the experiment.

## Integration scope

5. **BlockSim adapter is minimal and additive.** `adapter.run_pocol_stage2` maps a
   BlockSim-style config to `Stage2Config` and returns the declared `stage2b.1` schema. It
   does not embed the PoCol core in BlockSim's node/network event loop; the legacy
   simulator and the standalone demo are untouched.

6. **Reserve set fixed once per run.** The participation/reserve pool is computed once from
   the genesis population and reused each round; dynamic reserve churn is not modeled.

## Determinism / performance

7. **Search cost scales with the domain.** Real SHA-256 is computed for each searched
   nonce (twice per batch: once for seat-time timing, once for dispatch-time commit), so
   large `nonce_domain_size` values increase runtime. Confirmatory and test configs use
   modest domains (≤ 4000).

8. **No concurrency.** The event loop is single-threaded and deterministic by design.

## Explicit non-claims

9. **The run-vs-continuous-reference difference is NOT a general PoCol saving.** The
   adapter reports `continuous_all_active_control_kwh` as an accounting reference only. The
   idle-policy identity is validated separately by the constructed matched experiment
   (`matched_identity_experiment`), which is labelled "not a general PoCol saving".

10. **Nonce partitioning is NOT an energy-saving mechanism.** SCI-9 proves that with
    `P_idle == P_active` the saving is exactly `0.0`; the saving comes only from post-range
    low-power residency (the idle policy within PoCol).

11. **A1 is the fixed accounting invariant, not a demo output.** A1 = 141 miners × 21.5 W ×
    10 000 s = 8.420833333 kWh. No smaller demo/confirmatory scenario is labelled A1.
