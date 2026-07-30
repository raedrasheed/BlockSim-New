# Stage 0 — Protected-Artifact Register

Artifacts and branches that are **immutable** in the thesis-v45 development line. This line
adds new commits on `thesis-v45-*` branches only; it never modifies, rewrites, force-updates,
or deletes any entry below. Verified on the Stage-0 base commit
`6cb4c9b89f265af95857fdda4417d03ad336edfa`.

## 1. Protected thesis documents (DOCX)

| Artifact | SHA-256 | Location |
|----------|---------|----------|
| `docs/Raed-Rasheed-draft-42-00.docx` | `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` | in base tree (`6cb4c9b…`) |
| `docs/Raed-Rasheed-draft-43-00.docx` | `b53e5eb74aaff713cc3348b2945935f4015db0368654a5db097a3cc15eedfead` | branch `thesis-v43-stage7-thesis-integration-1` (`a57a8c3d…`) |
| `docs/Raed-Rasheed-draft-44-00.docx` | `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340` | in base tree (`6cb4c9b…`) |

- draft-42 = authoritative pre-revision source. draft-44 = Stage-7B corrected thesis. draft-43
  = Stage-7 examiner copy (superseded but preserved).
- **No `.docx` is created, modified, or deleted in Stages 0–8.** The next thesis document is
  `draft-45-00.docx`, created only in **Stage 9** from draft-44 (draft-44 stays unchanged).

## 2. Protected branches (remote tips at Stage-0 base)

### Data / archive
| Branch | Tip |
|--------|-----|
| `thesis-v43-stage5b2-data-1` | `b44975dd0803e3912f6151398a5a93c34eb95082` |

### Freeze
| Branch | Tip |
|--------|-----|
| `thesis-v43-stage5b2-freeze-1` | `c0ff48e462b90870540caf7461831c9ef795a77f` |
| `thesis-v43-stage5b2-freeze-2` | `03591d8f5424bf1e55ea0f60a7fb1db794c1cb36` |
| `thesis-v43-stage5b2-freeze-3` | `069a0c5344d24e82add9df5d76f8cf41ff932574` |
| `thesis-v43-stage5b2-freeze-4` | `8cb490caa9088baeeb54e5284a01be7ae3131c9e` |
| `thesis-v43-stage5b2-freeze-5` | `e7f046bb5c3873b9fe176aba20ce95d4df79773c` |
| `thesis-v43-stage5b2-freeze-6` | `45361674e6278971d430a79531f7aaac5cae3281` |

### Results
| Branch | Tip |
|--------|-----|
| `thesis-v43-stage5b2-results-1` | `d2ef6012afc8275c108ef56737a54a156abe5ceb` |
| `thesis-v43-stage5b2-results-2` | `9347ec969bd59a3337582571668ae2140c40485b` |
| `thesis-v43-stage5b2-results-3` | `278af17e76416c6018df6ffa23795904ae5a4e89` |

### Accepted analysis
| Branch | Tip |
|--------|-----|
| `thesis-v43-stage6-analysis-1` | `547ea339c64aa2475b8faa4e88b934925d550df4` |
| `thesis-v43-stage6-analysis-2` (base lineage) | `b7b61d20db08c7c1fba744ba7f536f65c8ae795e` |

### Stage-7 integration
| Branch | Tip |
|--------|-----|
| `thesis-v43-stage7-thesis-integration-1` (draft-43) | `a57a8c3dec3403202baa2e91cefde6de360b0c7f` |
| `thesis-v43-stage7-thesis-integration-2` (draft-44, base) | `6cb4c9b89f265af95857fdda4417d03ad336edfa` |

## 3. Previous scientific outputs (immutable)

All Stage-2 … Stage-7B deliverables carried in the base tree remain unchanged, including:
`docs/thesis_revision_v43/` (STAGE_02 … STAGE_07B reports, ledgers, audits, manifests) and
the frozen `results/thesis_revision_v43/` analysis outputs (Stage-6 tables, figures,
plot_data). Stage 0 adds only `docs/thesis_revision_v45/` documents.

## 4. Integrity rule

Before any later stage writes results, it must re-verify:
- draft-42 SHA-256 `= 2c3afdc5…`, draft-44 SHA-256 `= a31400bc…` (byte-identical);
- the base commit is `6cb4c9b…`;
- no protected branch tip has moved.

Any deviation halts the line and is reported, not worked around.
