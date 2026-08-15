# Stage 8X-ND — Pilot Report

**Matrix:** N ∈ {100, 300, 500} × 3 physical arms × 2 dedicated pilot seeds =
18 physical runs (+6 derived ND-PC-NOLP observations). Runtime 0.29 s; memory
trivial. **Verdict: PASS on all 17 checklist items of brief §34; frozen.**

| §34 item | Result |
|---|---|
| 1 nonce domain exactly 2^32 | pass (test 1) |
| 2 max nonce exactly 2^32−1 | pass (test 2; partition end = 2^32−1 inclusive) |
| 3 PoW: every miner owns the full domain | pass (test 3; U_nonce = 2^32 per miner-scope, m_max = N) |
| 4 PoCol partitions the full domain | pass (tiling, Σ sizes = 2^32) |
| 5 zero PoCol range overlap | pass (contiguous inclusive tiling) |
| 6 range coverage exact | pass |
| 7 header renewal after full PoW sweep | pass (5.4482e8 renewals per miner per run, = T·h/2^32) |
| 8 common-template renewal after full coordinated sweep | pass (T·h/⌈2^32/N⌉ epochs) |
| 9 rate-based success model | pass (Bernoulli-field abstraction, no enumeration) |
| 10 range completion timing | pass (t_range = 183.55/91.77/61.18/45.89/36.71 ns) |
| 11 low-power transition timing | pass (F_low = straggler closed form to 1e-3) |
| 12 state-time accounting | pass (0.0 relative error) |
| 13 energy identity | pass (E = 3510·(T_act + αT_low) exact) |
| 14 block interval | pass (14–18 blocks/run at ~600 s scale, both arms) |
| 15 runtime | 0.29 s / 18 runs |
| 16 memory | O(N) |
| 17 reproducibility | pass (bitwise, test 19) |

Pilot previews (not inferential): paired ND-PW vs ND-PC block counts identical
(14/14, 18/18) — the TQ4 trial-rate identity; ND-PC saving = 9.3e-10 at N=100
(the straggler gap); ND-PC-NOLP saving = 0 exactly; energy-per-block ratio
≈ 1.0. No tuning toward any energy result occurred.
