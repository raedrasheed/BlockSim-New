# Stage 8X-NR — Freeze Report

Freeze point: after Pilot PASS (`STAGE_8X_NR_PILOT_REPORT.md`), before any
primary run. Nothing in `config/` or `src/` changed between the freeze and the
completion of the 750-run primary matrix; the analysis/figure modules read frozen
outputs only.

## Frozen artifacts

| Item | Value |
|---|---|
| config hash (canonical JSON, SHA-256) | `36b2bd9617fcf33ca2a0be2c2c74b76d90797cd572915fc5a550fec767cf244c` |
| seed registry SHA-256 | `43c6e9b068215af51fd74eff64883b602b4252d539d26b22a61b6077f61a7bd8` |
| seed registry file | `outputs/stage8x_nr_seeds.json` (30 primary + 2 pilot, disjoint from 8X/8Y/8Z — verified in-registry and in test) |
| git commit at freeze | `e20457fd27385090f394ca9ec8a107701152d875` (pre-existing tree; Stage 8X-NR files added on top and committed after completion — the freeze manifest carries per-file SHA-256 of all 11 frozen code files) |
| code checksums | 11 files under `config/`, `src/`, `tests/` — see `manifests/STAGE_8X_NR_FREEZE_MANIFEST.json` |
| protected baseline | 390 files, `8f45fbf5d989bb65d0a16a8eaf06c2159928360c255c1aa7d491f5220ff8e396`, re-verified byte-identical after all execution |

## Frozen parameters

* S_nonce = 2^32 (explicit 32-bit header-nonce value domain)
* h = 234 TH/s, P_active = 3510 W, η = 15 J/TH per miner (S21 Pro)
* N ∈ {100, 200, 300, 400, 500}; T = 10 000 s; nominal interval 600 s
* D_N = H_N·600/2^32; q_N = 1/(H_N·600); one D_N per N for all arms
* Arms: XNR-PW-CONV-ZERO, XNR-PW-CONV-OFFSET, XNR-PW-MT-ZERO, XNR-PW-MT-OFFSET,
  XNR-PC (primary analysis arms: CONV-OFFSET, MT-OFFSET, PC; ZERO arms are
  synchronized diagnostic bounds — declared before execution)
* PoCol partition: start_i = ⌊i·2^32/N⌋, end_i = ⌊(i+1)·2^32/N⌋−1
* α ∈ {0, 0.10, 0.25, 0.50}, derived observations per run
* Sub-sweep diagnostic window W = ⌊2^32/2N⌋ ticks
* 30 primary paired seeds, 2 pilot seeds, per-purpose stream derivation
* Preregistered analytic expectations frozen in `config/nr_config.predictions`
  and compared in Table NR-J

## Amendments after freeze

**A1 — additive metric extension (reporting only, no scientific change).**
After the primary matrix and first analysis were complete, the refined brief
required additional *derived* quantities: M_≥3, mean miner multiplicity among
reused nonce values, P95 pairwise overlap, a dedicated
`stage8xnr_pairwise_overlap.csv`, brief-canonical `stage8xnr_*` output aliases,
three additional tests, and two additional figures. The metric recorder was
extended and the deterministic engine re-run on the identical frozen seeds and
configuration (config_hash unchanged:
`36b2bd9617fcf33ca2a0be2c2c74b76d90797cd572915fc5a550fec767cf244c`).

Proof that no frozen quantity changed: every shared column of all six primary
output CSVs was compared cell-by-cell between the pre- and post-amendment files —
**0 mismatches** across 750 physical-run rows (58 shared columns), 8 022
round-metric rows (33), 1 500 nonce-reuse rows (14), 1 500 exact-input rows (9),
3 000 energy rows (10) and 750 template-epoch rows (7). No parameter, seed,
probability, or previously reported number was altered; A1 only added columns
and files. Amended code files are checksummed in
`manifests/STAGE_8X_NR_FREEZE_MANIFEST.json` under `amendment_A1`.
