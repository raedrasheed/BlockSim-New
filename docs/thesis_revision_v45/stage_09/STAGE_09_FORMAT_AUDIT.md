# Stage 9 — Format Audit

Renderer-independent format checks (PASS):
* OpenXML XSD validation PASS (no new errors vs original).
* document.xml + rels well-formed; +268 paragraphs; 53 tables; 29 drawings.
* Styles/headings reused from the document's own style set (Heading3 for the new
  subsection; TableGrid for tables); page size, margins and section breaks untouched.
* Arabic insertion carries `<w:bidi/>` and right justification (RTL preserved).
* Tables use DXA column widths summing to 9360 (6.5-inch content) with explicit cell
  widths; result boxes are bordered/shaded single-cell tables.

OUTSTANDING (blocked): visual format inspection — orphan headings, blank pages, clipped
figures, broken table pagination, TOC field refresh — all require the PDF render, which
is blocked (LibreOffice cannot load any DOCX here). TOC/cross-reference fields are
structurally intact but were not re-computed (that requires opening in Word/LibreOffice).
