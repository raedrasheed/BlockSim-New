# Stage 9 — Blocker Report

## Blocker
The environment's LibreOffice (24.2.7.2) cannot load ANY DOCX. Confirmed on:
* the pristine authoritative `docs/Raed-Rasheed-draft-44-00.docx`, and
* a hand-built minimal valid `.docx`,
both failing identically with `Error: source file could not be loaded` for
`--convert-to pdf`, `--convert-to txt`, and `--cat`. Java is present (openjdk-21); the
`javaldx` warning is not the cause — the document-import filter itself is non-functional.
No alternative DOCX->PDF renderer exists in this environment (no pandoc; Chromium renders
HTML, not Word; python-docx not installed).

## Affected mandated items (only these)
1. COMMIT-2 validation step: "render the full document to PDF; inspect every page
   visually" (orphan headings, blank pages, clipped figures, broken tables, TOC refresh).
2. COMMIT-3 deliverable: `Raed-Rasheed-PhD-Thesis-Stage9-Clean.pdf`.
3. COMMIT-3 deliverable: `Raed-Rasheed-PhD-Thesis-Stage9-Redline.pdf`.

## Everything else is complete and preserved
* COMMIT-1 evidence plan (7 docs) — committed and pushed.
* Redline DOCX `Raed-Rasheed-PhD-Thesis-Stage9-Redline.docx` — built, XSD-valid
  (validate.py PASS vs original), structurally audited (figures/tables/numbers/naming/
  media/RQ all PASS).
* Clean DOCX `Raed-Rasheed-PhD-Thesis-Stage9-Clean.docx` — built (deterministic red->
  black recolour), well-formed.
* All renderer-independent audits (structure, numeric, claim, figure, reference, format,
  redline) — written.
* Defence package + change map — written.
* Authoritative `draft-44-00.docx` preserved byte-identical (SHA a31400bc...).
* Zero engine/seed/dataset/analysis/figure changes; zero new simulations; all 257
  accepted tests pass; historical Stage-8S/8U manifests verify.

## Minimum correction to reach COMPLETE
Open `Raed-Rasheed-PhD-Thesis-Stage9-Redline.docx` and
`Raed-Rasheed-PhD-Thesis-Stage9-Clean.docx` in a working LibreOffice/Word (a functional
DOCX import filter), export each to PDF, refresh TOC/cross-reference fields on open, and
perform the per-page visual inspection. No content edit is required; the two DOCX files
are final and validated. This is a rendering-environment fix, not a thesis-content fix.
