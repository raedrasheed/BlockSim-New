# Equation Conversion Report — Native Word Equations (OMML)

**Input:** `Raed-Rasheed-draft-40-UniversityFormat.docx`
**Output:** `Raed-Rasheed-draft-41-WordEquations.docx` (draft-40 not overwritten)
**Scope:** convert **only** the mathematical expressions into native Microsoft Word
Equation objects (OMML). **No scientific content, sentence, notation, variable, symbol,
equation numbering, cross-reference, caption, or any formatting outside the equations was
changed.** Equations were neither added, removed, simplified, nor derived.

## 1. Totals

| Metric | Count |
|---|---:|
| **Total equations converted (native OMML objects)** | **419** |
| — Display equations (`m:oMathPara`) | **36** |
| — Inline equations (`m:oMath`) | **383** |
| Equations that could **not** be auto-converted | **0** genuine (see §4) |
| Round-trip / prose-integrity mismatches | **0** |
| New schema-validation errors vs. draft-40 | **0** |

Every expression was converted with a **round-trip safety net**: an expression becomes an
OMML object only if the built OMML linearises back **character-for-character** to the source
mathematics (spaces/braces/dash-forms normalised). After each paragraph was rebuilt, the
residual non-math prose was verified to equal the original text with the converted spans
removed; otherwise the paragraph was rolled back untouched. This guarantees the surrounding
prose is byte-for-byte preserved.

## 2. Display equations (36)

- **28 numbered/displayed equations** laid out as equation tables (Chapters 4–5, e.g. 4.1–4.8,
  5.1–5.9, and the register/hash-rate equations). The **equation-number cells** (e.g. `(4.1)`,
  `(5.2)`) were confirmed **unchanged** (0 of them modified) and their alignment preserved via
  `m:oMathParaPr/m:jc` matched to each paragraph.
- **8 centred / standalone displayed equations** in body paragraphs, including the three **red
  revision** energy equations (`E_i = P_i^(active) t_i^(active) + …`, the idle and continuous
  `E_PoCol` sums). These were converted **while preserving their red colour** (`w:color=FF0000`
  on the math runs) so the revision marking is intact.

## 3. Inline equations (383)

All inline mathematics woven through the prose of Chapters 1–7 was converted, including:
- subscripts / superscripts — `P_PoW`, `E_block`, `H_i(r)`, `m_i`, `H_active(t)`, `2^256`,
  `{0,1}^256`, `O(n^2)`, `10^-6`, `10^12`;
- Unicode maths normalised to true formatting — `mᵢ→m_i`, `∑ⁿᵢ₌₁→∑_{i=1}^{n}`, `t₁,t₂`, `CO₂`;
- Greek symbols as Word math symbols — `λ, β, Θ, π, ε, δ, σ, µ`;
- fractions as **stacked** fractions — `1/λ`, `(P/λ)/B_tx`;
- summations with proper **Σ** and under/over limits; set / logic notation — `∈, ∉, ∩, ∪, ⊆,
  ∅, ⋃, |M|`, set-builder `{Serialize(Header_r(n)) | n ∈ N_r}`, piecewise braces;
- function names kept upright (`H`, `floor`, `ceil`, `Serialize`, `header`) while variables
  stay italic.

Fractions were emitted as `m:f` (num/den), summations/unions as `m:nary` with the correct
`m:chr`, sub/superscripts as `m:sSub` / `m:sSup` / `m:sSubSup`, and brackets as `m:d`
delimiters. Structural audit: 24 `m:f` (all with num+den), 14 `m:nary` (all with `m:e`),
475 `m:sSub`, 6 `m:sSup`, 18 `m:sSubSup`, 234 `m:d` — **0 malformed**.

## 4. Expressions intentionally **not** converted (integrity rules)

Per the "do NOT modify headings / tables / bibliography / references" instruction, these
were left as-is by design (they are not defects):

1. **Heading `5.8 PoCol Normal Rounds (r ≥ 1)`** — the `(r ≥ 1)` sits inside a chapter
   sub-heading; headings were not modified.
2. **Results/data-table cells** — e.g. `CO₂`, `CO₂ (kg)`, `141 × 10^12 H/s` in the
   parameter/results tables. These are data-table contents, not numbered equations; data
   tables were not modified.
3. **Bibliography (153-row reference table)** — untouched (0 cells changed); references were
   not modified.

There were **no equations that failed to convert for technical reasons** — every genuine
mathematical expression in the body prose, equation tables, and equation captions/appendix
lines was converted.

## 5. Confirmation — native OMML & editability

- The output was **reopened** and every one of the **419** equation objects is a **native
  Office Math (`m:oMath`) object** in the OMML namespace
  `http://schemas.openxmlformats.org/officeDocument/2006/math`, i.e. **double-click editable
  in Microsoft Word's Equation Editor**. None remain as plain text (the only residual maths
  glyph in body prose is the heading in §4.1).
- **Document integrity:** 971/971 paragraphs, 44/44 tables, 15/15 images preserved; page
  numbering, TOC, cross-references, captions, and figures untouched; **schema-valid with zero
  new errors** relative to draft-40; document reopens cleanly.
- **Prose fidelity:** an end-to-end check linearised every OMML object back to text and
  reconstructed each of the 971 paragraphs — **0 mismatches** against draft-40.

## 6. Tooling (reproducible)

- `omml.py` — faithful plain-maths → OMML builder with a lineariser used as a round-trip
  guarantee (only content-preserving conversions are accepted).
- `convert.py` — paragraph-level conversion engine (Unicode normalisation, span detection,
  colour/format preservation, per-paragraph rollback safety).
- `validate_conv.py` — end-to-end verifier (reads OMML back and reconstructs the original
  text for all 971 paragraphs).

## Required action in Word
Open `Raed-Rasheed-draft-41-WordEquations.docx` and press **Ctrl+A → F9** to refresh the
Table of Contents / cross-references / page numbers (equation content is already native OMML
and needs no further action).
