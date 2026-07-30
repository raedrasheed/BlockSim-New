# Stage 7B — Obsolete-Text Audit (§11)

Assertion: obsolete/false claims do **not** survive as active claims in
`Raed-Rasheed-draft-44-00.docx`. Verified by string search over `word/document.xml` and by
a qualitative scan for empirical energy/carbon-reduction claims in non-red (black) text.

## Numeric / verbatim obsolete strings

| String | Occurrences | Status |
|--------|-------------|--------|
| `98.3%` | 0 | PASS |
| `98%` | 0 | PASS |
| `99%` | 0 | PASS |
| `7.90 kWh` | 0 | PASS |
| `0.131` | 0 | PASS |
| `33.078` | 0 | PASS |
| `40.408` | 0 | PASS |
| `0.454` | 0 | PASS |
| `substantially more energy-efficient` | 0 | PASS |
| `significantly reduced total energy consumption` | 0 | PASS |
| `much less energy than PoW` | 0 | PASS |
| `drastically lowers total energy` | 0 | PASS |
| `Summary of the main PoCol and PoW evaluation metrics extracted` | 0 | PASS |

Note: `98.3%` occurrences reported above are 0. The token `98.3` appears once elsewhere as
part of a DOI (`10.1145/3605098.3635970`) in the bibliography and is not an energy figure.

## Qualitative empirical-claim scan (black text only)

A regex scan for empirical claims that PoCol's own experiments *reduced* total energy or
carbon (e.g. "PoCol … reduces/lowers", "significantly/substantially reduced total energy",
"much less energy than PoW", "sustainability benefits were") over **non-red** paragraphs
returns **no surviving false claims**. The only matches are:

- a literature/design sentence stating *"nonce-range partitioning alone does not guarantee
  energy reduction"* (correct, and consistent with the A1 invariant); and
- a literature/design sentence describing that *PoCol reduces active hashing duration*
  (the idle-policy mechanism, consistent with H3–H5).

Both are accurate design/literature statements, not obsolete result claims.

## Banned-claim classes (Stage 7B §3) — all absent as active claims

- 98–99 % energy-reduction figure: **absent**
- obsolete kWh PoW-vs-PoCol comparison (7.90 / 0.131 / 33.078 / 40.408 / 0.454): **absent**
- miner-count energy scaling: **absent** (replaced by invariance across N)
- unqualified energy-efficiency claim: **absent**
- fairness (reward/incentive) claim: **absent** (§5.6.4 reframed as range-assignment balance)
- full-network stale/fork claim: **absent** (H7 reported as secondary single-height diagnostic)

## Verdict

**OBSOLETE-TEXT AUDIT: PASS** — no obsolete or false claim survives as an active
(black-text) statement; all surviving corrected claims are red.
