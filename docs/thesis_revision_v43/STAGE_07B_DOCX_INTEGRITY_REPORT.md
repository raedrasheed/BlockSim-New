# Stage 7B — DOCX Integrity Report

OOXML schema validation (docx skill `validate.py --original draft-42`): **All validations
PASSED** (0 new schema errors relative to the authoritative draft-42; the pre-existing
`w:rFonts@w:hint="cs"` schema-strictness note is present identically in draft-42 and is not
introduced by this stage).

| Component | draft-42 | draft-44 | Δ |
|-----------|----------|----------|---|
| Package parts | 44 | 51 | +7 |
| Media parts | 19 | 26 | +7 |
| Image blips | 15 | 17 | +2 |
| Equations (m:oMath) | 418 | 418 | +0 |
| Fields (fldSimple+instrText) | 173 | 173 | +0 |
| Hyperlinks | 172 | 172 | +0 |
| Relationships (document.xml.rels) | 33 | 40 | +7 |
| Image relationships | 15 | 22 | +7 |
| Red runs | 0 | 186 | +186 |
| Tables | 42 | 43 | +1 |
| Paragraphs | 2203 | 2132 | -71 |

- **Equations, fields, and hyperlinks preserved exactly** (Δ 0 each) — no equation, field,
  or hyperlink was lost or corrupted by the surgical edits.
- Package delta is **additions only**: 7 media parts added
  (`image16.png, image17.png, image18.png, image19.png, image20.png, image21.png, image22.png`), 0 parts removed.
- Image relationships resolve: **0** unresolved `r:embed`; **0** image
  targets missing media.
- Paragraph count decreased (2203→2132) because obsolete figures, the old
  Table 7.1 caption, and obsolete energy/carbon data tables were removed (net of added
  corrected figures, captions, tables, and prose).

## Checksums

- draft-42 SHA-256: `2c3afdc5739109d0ea12ada96c3115d626a2188c1acbaeaa4b6020974884cbda` (unchanged / byte-identical to authoritative input)
- draft-44 SHA-256: `a31400bce212585df8197ee3d63e4eb887b5f5d0f2f8a65b916b2489dbc12340`

## Verdict

**DOCX INTEGRITY: PASS** — schema-valid vs. original; equations/fields/hyperlinks preserved;
additive-only package; all image relationships resolve.
