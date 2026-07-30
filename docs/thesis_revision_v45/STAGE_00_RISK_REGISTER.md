# Stage 0 — Risk Register (thesis-v45 PoCol idle-policy line)

Scientific and process risks for this development line, each with a mitigation and the
stage(s) where it is enforced. Severity: H(igh) / M(edium) / L(ow).

## Scientific-integrity risks

| # | Risk | Sev | Mitigation | Enforced at |
|--:|------|:---:|------------|-------------|
| R1 | Re-introducing the false claim that partitioning inherently reduces energy | H | Global rule 3; A1 invariant is the fixed baseline; any reduction must be attributed to power–time reduction (idle/reserve/participation) | All; audited 8–9 |
| R2 | Claiming energy improvement before the full frozen experiment + analysis complete | H | Global rule 4; confirmatory claims only after Stage 8; pilot data barred from confirmatory use | 6–8 |
| R3 | Energy "saving" that is really reduced security or reduced service | H | Security floor + non-inferiority margins; rule 5; Stage 8 separates "saving with floor satisfied" from "saving via reduced security" | 3, 8 |
| R4 | Dynamic difficulty change contaminating the confirmatory result | H | Global rule 6; difficulty held constant in core experiment; difficulty-control is separate/exploratory (rule 7) | 3, 6, 7, 8 |
| R5 | Double-counting shared physical executions (e.g. B3/C1-style) | H | Global rule 12; one physical run = one dataset; provenance recorded; audited | 4, 7, 8 |
| R6 | Wrong inferential unit / ignoring seed-cluster dependence | M | Global rule 13; physical run / master seed as unit; cluster bootstrap + paired permutation; Holm correction | 6, 8 |
| R7 | Dropping zero-block runs or imputing NA metrics | M | Global rules 10–11; retain zero-block; keep block-normalised metrics NA (not imputed) | 6, 7, 8 |
| R8 | Overclaiming modeled progress verification as a cryptographic proof | H | Global rule 14; all progress commitments labelled "modeled abstraction"; no complete-range-search proof claimed | 1, 4, 5, 9 |
| R9 | Static hash-rate / adversarial-share modeling hiding time-varying effects | M | Global rules 8–9; model H_active(t) and q_adversarial(t) as time-varying | 2, 3, 5 |
| R10 | Claiming incentive compatibility from the reward/penalty interface | M | Reward/penalty specified as parameterised interface only; no incentive-compatibility claim | 1, 5 |
| R11 | Energy-accounting leakage (states not summing to the horizon) | M | Stage-2 invariant `total = hashing+listening+wake+transition+coordination`; degenerate tests; state durations reconcile to round/horizon | 2 |
| R12 | Idle entered before range exhaustion (invalid saving) | M | Stage-2 test: no miner idles before exhausting its assigned range | 2 |

## Naming / narrative risks

| # | Risk | Sev | Mitigation | Enforced at |
|--:|------|:---:|------------|-------------|
| R13 | Naming drift (PoCol-E / Enhanced PoCol / new algorithm name) | H | Global naming rule; idle policy is a policy inside PoCol; audited in thesis stages | All; 9 |
| R14 | Thesis narrative implying unconditional energy reduction | H | Any reduction stated as conditional on operating policy + within security/service limits; red in-place replacement (no correction notices) | 9 |

## Process / integrity risks

| # | Risk | Sev | Mitigation | Enforced at |
|--:|------|:---:|------------|-------------|
| R15 | Modifying a protected artifact (draft-42/43/44, protected branches) | H | Protected-artifact register; read-only; SHA re-verification before any results write | All |
| R16 | Editing the simulator in Stage 0 or the thesis in Stages 0–8 | H | Change map; Stage-0 permitted-files list is exhaustive | 0–8 |
| R17 | Proceeding to the next stage without explicit approval | H | Stop tokens; agent halts and waits at each gate | All |
| R18 | Engine change after viewing frozen results | H | Frozen-after-view rule; a needed change forces a new preregistered freeze cycle | 7, 8 |
| R19 | Non-durable data or unverifiable archives | M | Durable archive + fresh-clone roundtrip; manifests + checksums | 7 |
| R20 | Renderer unavailable → cannot produce/inspect PDF | M | Known environment limitation; Stage 10 may end `STAGE_10_FINALISATION_BLOCKED` with the DOCX ready for an external renderer; does not fabricate a render | 10 |
| R21 | Tests not run before/after frozen execution | M | Run full source tests before execution and after execution (Stage 7) | 7 |

## Residual / accepted limitations (recorded, not mitigated away)

- Simulated cryptographic/progress verification is a **modeled abstraction**, not a complete
  cryptographic proof (R8) — this is a stated scope limitation of the whole line.
- Idle-policy energy reduction is **conditional** (requires hash-rate heterogeneity and a low
  idle-power ratio); it is not a structural property of partitioning.
- Security properties evaluated are **model-supported**, not formally proven; every
  unsupported security property is listed explicitly (global rule 15).
