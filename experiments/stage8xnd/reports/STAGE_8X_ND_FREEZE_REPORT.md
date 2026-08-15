# Stage 8X-ND — Freeze Report

Freeze point: after Pilot PASS, before any primary run. No scientific
parameter, seed, or analysis rule changed after primary results began.

| Item | Value |
|---|---|
| config hash | `d64a7727aef3dcc887b6d4a9aac2b0710f9ae10360a8355a1316c5530f6efb32` |
| seed registry SHA-256 | `17aeab1af54006624aab17c341952e7e...` (full value in freeze manifest) |
| seed registry file | `outputs/stage8xnd_seeds.json` (30 primary + 2 pilot; disjoint from 8X, 8X-NR, 8X-E50, 8Y, 8Z — verified) |
| git commit at freeze | `24a7c2b8` (Stage 8X-ND files added on top; per-file code checksums in `manifests/STAGE_8X_ND_FREEZE_MANIFEST.json`) |
| protected baseline | 602 files, `6bbebb7def76ad36…`, re-verified byte-identical after all execution |

## Frozen parameters

NONCE_DOMAIN_SIZE = 2^32, MAX_NONCE = 2^32−1 (never enlarged); S21 Pro
(234 TH/s, 3510 W, 15 J/TH); N ∈ {100…500}; T = 10 000 s;
q_N = 1/(N·h·600) shared by all arms (no PoCol retargeting); arms ND-PW
(zero-start full-domain primary control), ND-PW-OFFSET (secondary
diagnostic), ND-PC (partition ⌊iS/N⌋…⌊(i+1)S/N⌋−1, post-range low power, no
reassignment), ND-PC-NOLP (derived accounting observation);
α ∈ {0, .10, .25, .50} accounting-only; 30 fresh paired seeds; theory report
(TQ1–TQ6 + §29 validity check) frozen before Pilot, including the
unfavourable TQ6 prediction.

## Amendments after freeze

None.
