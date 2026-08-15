# Stage 8X-E50 — Pilot Report

**Matrix:** N ∈ {100, 300, 500} × 10 arms × 2 dedicated pilot seeds = 60 runs.
**Runtime:** 0.09 s wall; memory < 100 MB (prefix-sum epoch arithmetic, no
per-epoch iteration beyond ≤N steps per round). Primary (1500 runs) projected
< 5 s. **Verdict: PASS on all 13 checklist items of brief §32; frozen.**

| §32 item | Check | Result |
|---|---|---|
| 1 common-template MT semantics | one template per S-tick epoch; U = S per epoch; ρ_exact = (N−1)/N to 2e-4 (0.9900/0.9967/0.9980) | pass |
| 2 PoCol disjoint semantics | partition tiling asserted; only active owners search; no borrowing; U = C exactly | pass |
| 3 exact-input accounting | MT U = 2.3400e18 = h·T at every N; CONV U = C = N·h·T | pass |
| 4 unique-coverage accounting | PC(A) U = k·h·T exactly (retention = k, e.g. 10.00 at PC10/N=100, 50.00 at PC10/N=500) | pass |
| 5 epoch renewal | matched rule verified in test 14: epoch seconds = assignment ticks / h in both arms | pass |
| 6 exhaustion | assigned-traversal completions = k per PC epoch, N per MT epoch, exact ints | pass |
| 7 active-fraction implementation | k = ⌈A·N⌉ asserted at every (N, A); test 8 | pass |
| 8 energy state-time accounting | conservation and work identity exactly 0.0 in all 60 runs; α accounting-only (test 20) | pass |
| 9 fairness rotation | sliding window: duty exactly k/N per slot per cycle (test 9/10); Jain = 1.0000 | pass |
| 10 block interval | CONV pooled mean ≈ 600 s scale; PC100 blocks identical to CONV per paired seed (14/14 at N=100 seed 1) — the k = N limit reproduces full-throughput behaviour | pass |
| 11 target/difficulty | one q_N for all 10 arms; q·D·2^32 = 1 (test 13) | pass |
| 12 runtime | 0.09 s / 60 runs | pass |
| 13 memory | O(N) state per run | pass |

Pilot previews (not inferential): PC out-produces MT100 at every fraction
(PC10: 2 blocks vs MT100: 0 at N=100), savings land exactly on the
preregistered (1−k/N)(1−α) surface (0.9000/0.4500 at PC10 LP0/LP50), and MT100
frequently has zero blocks per run, confirming the preregistered pooled-
retention + per-seed-NA analysis rule.

No Pilot modification was made toward any energy target; the only changes
during Pilot development were instrumentation-level. Pilot outputs live under
`outputs/stage8xe50_pilot_*` and are excluded from inference.
