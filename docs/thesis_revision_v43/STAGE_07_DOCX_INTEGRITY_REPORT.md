# Stage 7 — DOCX Integrity Report

Examiner-review copy `Raed-Rasheed-draft-43-00.docx` was produced by **surgical OOXML
editing** of the draft-42 package (unzip → merge adjacent identically-formatted runs →
edit `word/document.xml` → rezip), never by reconstructing the document from plain text.

## Package structure

| Check | draft-42 | draft-43 | Result |
|-------|---------:|---------:|--------|
| ZIP parts | 44 | 44 | identical set (added: none, removed: none) |
| `[Content_Types].xml` | present | present | OK |
| Relationships (`word/_rels/document.xml.rels`) | 33 | 33 | all targets preserved |
| Embedded images (`word/media`, `<a:blip>`) | 15 | 15 | all resolve; no external links |
| Word equations (`<m:oMath>`) | 488 | 488 | preserved (not flattened, not screenshots) |
| Field codes (`<w:instrText>`: TOC / cross-refs / captions) | 346 | 346 | preserved |
| Hyperlinks (`<w:hyperlink>`) | 172 | 172 | preserved |
| Paragraphs | 2203 | 2204 | +1 (governing correction notice, red) |

## Schema validation

`scripts/office/validate.py draft43.docx --original draft42.docx` → **All validations
PASSED** (OOXML XSD checks; no namespace errors; all 39 document namespaces preserved and
`mc:Ignorable` prefixes declared).

## Preserved Word objects

Heading styles, section breaks, headers/footers (5 footers), front-matter Roman vs body
Arabic numbering, TOC / list-of-figures / list-of-tables fields, bookmarks, captions,
cross-references, equations, bibliography, image relationships, and RTL properties of the
Arabic abstract are all carried through unchanged — only new red text runs were inserted
and one heading run recolored/reworded. No field or cross-reference was flattened to text;
no equation was replaced by an image.

## Edit mechanism

13 red runs added (`<w:color w:val="FF0000"/>`), each copying the local run's formatting
(font/size) and adding red colour; one heading (§5.6.4) reworded in red. All edits are
additive except the single reworded heading. No Track Changes were enabled.
