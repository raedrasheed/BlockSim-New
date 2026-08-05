# Stage 9 — DOCX Structure Audit

Target: `docs/Raed-Rasheed-PhD-Thesis-Stage9-Redline.docx`
(SHA-256 `af077bc484214847d8a959d0b5485a19423bbc2a78766dc71c5bec9f83ebf3c2`).
Source: `docs/Raed-Rasheed-draft-44-00.docx` (unchanged, SHA-256 `a31400bc…`).

## OpenXML validation (skill validator, XSD + relationship checks)

`validate.py Raed-Rasheed-PhD-Thesis-Stage9-Redline.docx --original Raed-Rasheed-draft-44-00.docx`
→ **All validations PASSED**. No new validation errors versus the original.
Paragraph count 2132 → 2400 (+268 Stage-9 additions).

One schema-ordering defect found and fixed during construction: `<w:tcPr>` child order
(the result-box cells had `tcBorders` after `shd`; corrected so `tcBorders` precedes
`shd`). Re-validation is clean.

## Media relationships

* 10 Stage-9 figure images added to `word/media/` (`imageStage9_1.png` … `_10.png`),
  each with a new `word/_rels/document.xml.rels` image relationship (rId41–rId50).
* Every `r:embed` in `document.xml` resolves to a declared relationship: **0 dangling
  embeds**.
* Every media relationship `Target` exists on disk: **0 missing media**.
* PNG content-type already registered in `[Content_Types].xml` (no override needed).
* Well-formedness: `document.xml` and `document.xml.rels` parse as well-formed XML.

## Structure preserved

Styles, headings, equations, page dimensions, margins, section breaks, Arabic RTL
(`<w:bidi/>` + `w:jc="right"` on the Arabic insertion), citations, bibliography, TOC field
structure and existing figure numbering are all retained; Stage-9 additions are appended
red paragraphs/tables/figures at located anchors and do not rewrite surrounding runs.

## OUTSTANDING (environment blocker)

The mandated **PDF render and per-page visual inspection** could not be performed:
LibreOffice 24.2.7.2 in this environment fails to load *any* DOCX (confirmed on the
pristine `draft-44-00.docx` and on a hand-built minimal valid `.docx`, both failing with
`Error: source file could not be loaded`; `--cat` fails identically). No alternative
DOCX→PDF renderer is available (no pandoc; Chromium renders HTML, not Word). This blocks
the two PDF deliverables and the pixel-level visual inspection. See
`STAGE_09_BLOCKER_REPORT.md`. All renderer-independent structural checks above PASS.
