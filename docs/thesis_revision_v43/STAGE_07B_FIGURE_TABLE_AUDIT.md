# Stage 7B — Figure and Table Integrity Audit (§12)

## Embedded images (not linked)

- Total `<a:blip>` image references in draft-44: **17** (draft-42: 15).
- Media parts: **26** (draft-42: 19); parts added: 7 — all PNG
  (`image16.png, image17.png, image18.png, image19.png, image20.png, image21.png, image22.png`); parts removed: 0.
- Image relationships: **22** (draft-42: 15).
- **Unresolved `r:embed` references: 0** (none).
- **Image relationship targets with missing media: 0** (none).

Every embedded figure is a real inline `wp:inline`/`a:blip` drawing whose relationship
resolves to a media file present in the package. No externally linked images.

## Obsolete figures removed

Figures 7.4–7.8 (PoW-vs-PoCol total energy / per-block energy / per-transaction energy /
cumulative energy / carbon footprint) — the drawing paragraph **and** the caption paragraph
were deleted for each (5 figures). Their captions no longer appear in the document body.

## Corrected Stage-6A figures inserted (§7.4.1.1)

| Fig | Source (Stage-6A) | Label |
|-----|-------------------|-------|
| 7.4 | fig02_a1_energy_invariant | INVARIANT (A1, 8.420833333 kWh) |
| 7.5 | fig01_h1_duplicate_rate | CONFIRMATORY (B1>B2>B3/C1; 150 pairs; 30 clusters) |
| 7.6 | fig03_h5_completion_dispersion | CONFIRMATORY |
| 7.7 | fig04_h5_c2_energy_tradeoff | CONFIRMATORY (idle-energy trade-off; **no fairness wording**) |
| 7.8 | fig06_h6_inactive | CONFIRMATORY |
| 7.9 | fig07_h8_mu | CONFIRMATORY |
| 7.10 | fig08_h7_delay_singleheight | SECONDARY (single-height diagnostic) |

fig04's caption states a "completion-balance versus idle-energy trade-off, not a reward or
incentive result" — it carries no positive fairness claim.

## Tables

- Total `<w:tbl>` in draft-44: **43** (draft-42: 42).
- **Table 7.1** replaced in place: obsolete "Summary of the main PoCol and PoW evaluation
  metrics" → corrected 7-row Stage-6A summary (A1 / H1 / H3 / H4–H5 / H6 / H8 / H7). The old
  caption paragraph was deleted (0 occurrences of the old caption text).
- **Table 7.2 (H1)** inserted: duplicate serialized candidate-header evaluation rate by
  scenario, **150 physical seed-matched runs per scenario**, uncertainty from **30
  independent master-seed clusters**; ordering B1 > B2 > B3/C1; B3/C1 = 0 duplicate
  identities; note that **B3 and C1 are one physical dataset, never double-counted**.
- **Table 7.3 (conditional epab)** inserted: columns **total / defined / undefined (NA) /
  reason**; zero-block runs retained, block-normalised metrics NA (not imputed); B3/C1 one
  dataset (870 runs), never counted twice.
- Obsolete energy/carbon numeric data tables removed.

## Verdict

**FIGURE/TABLE INTEGRITY: PASS** — obsolete figures/tables absent; corrected figures
embedded (not linked) with resolving relationships; required H1 (150 pairs / 30 clusters, no
B3/C1 double-count) and conditional (total/defined/undefined/reason) tables present.
