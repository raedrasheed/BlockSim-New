# Stage 8X-E50 — Freeze Report

Freeze point: after Pilot PASS, before any primary run. No config, code, seed,
threshold, fraction grid, or analysis rule changed after primary outcomes
became visible.

| Item | Value |
|---|---|
| config hash | `d74001f4e4b7628b056a536b2404c56ac62148699a212a5babe9a1f2434bd173` |
| seed registry SHA-256 | `0e506b839a3a7589ed04bf1235a25cc7fc0a2f0161a53abbff481c91a79e875d` |
| seed registry file | `outputs/stage8xe50_seeds.json` (30 primary + 2 pilot; disjoint from 8X/8X-NR/8Y/8Z, verified) |
| git commit at freeze | `272e8a1bc99c3eb35e4a06dd06498629fcecf4d7` |
| code checksums | 10 files — `manifests/STAGE_8X_E50_FREEZE_MANIFEST.json` |
| protected baseline | 500 files, `69576696669f4cac…`, re-verified byte-identical after all execution |

## Frozen parameters

S = 2^32; S21 Pro (234 TH/s, 3510 W, 15 J/TH); N ∈ {100…500}; T = 10 000 s;
q_N = 1/(N·h·600) shared by all ten arms (no retargeting for active fractions);
arms E50-CONV100 (external reference), E50-MT100 (primary baseline),
E50-PC{10,20,30,40,50,60,80,100}; partition ⌊iS/N⌋ over the full population;
sliding-window rotation (+1 slot/epoch); matched renewal rule (epoch =
assigned traversal complete); α ∈ {0, .10, .25, .50} accounting-only;
constraints frozen at coverage ≥ 0.95, pooled block retention ≥ 0.90, pooled
median latency ratio ≤ 1.20; per-seed NA rule for zero-block MT100 pairs;
preregistered predictions in `config/e50_config.predictions` and the theory
report.

## Amendments after freeze

None.
