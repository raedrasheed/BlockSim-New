# Stage 9 — Redline Audit

Redline mechanism: **red font RGB FF0000** on all inserted/modified runs, matching the
existing draft-44 convention (186 pre-existing FF0000 runs from earlier redline stages;
draft-44 contains no `<w:ins>` tracked-change blocks). The directive's explicit
requirement is "all inserted or modified text … must use red font: RGB FF0000"; this is
satisfied directly and makes the clean copy a deterministic recolour.

## Verified (renderer-independent)
* +258 new red runs added (196 after the text pass, then tables/boxes/matrix →
  document contains only red Stage-9 insertions plus the 186 pre-existing red runs);
  every Stage-9 insertion is FF0000. Unchanged text was not recoloured.
* Insertions are additive paragraphs/tables/figures at located anchors; no surrounding
  original run was rewritten, so untouched text remains byte-stable.
* Abstract (EN) Stage-8S/8U paragraph inserted after the invariant sentence; Arabic
  abstract mirror inserted with `<w:bidi/>` + right justification.
* RQ1–RQ5 inserted after the legacy RQ block; contributions note after C5.
* §7.3.1 legacy throughput claim bounded (matched-PoW control result stated).
* New §7.4.4 results subsection with two result boxes, Tables 7.2–7.8, Figures
  7.10–7.19; Chapter-8 RQ answer matrix (Table 8.1); threats-to-validity addendum.
* Authoritative `draft-44-00.docx` byte-identical (SHA a31400bc…).

## OUTSTANDING (environment blocker)
* "verify all new text is red" — DONE structurally (FF0000 scan).
* "render to PDF; inspect every page visually; check orphan headings, blank pages,
  clipped figures, broken tables" — **BLOCKED**: LibreOffice cannot load any DOCX in
  this environment; no alternative renderer. See STAGE_09_BLOCKER_REPORT.md.
