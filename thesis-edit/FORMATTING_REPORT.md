# Formatting Report — IUG University-Format Pass

**Input:** `Raed-Rasheed-draft-39-References-Verified.docx`
**Output:** `Raed-Rasheed-draft-40-UniversityFormat.docx`
**Scope:** formatting only, per the IUG *English Thesis Formatting Guidelines* (the attached
Arabic reference was read and confirms A4 / Times New Roman / 12 pt body / 14 pt bold chapter
titles / 20 pt title). **No scientific content, citations, equations, table/figure data, red
revision text, or Track-Changes status was modified.** Verified: body text identical
(971/971 paragraphs), all table text identical, 15 images intact, 44 tables intact, 72 red
runs preserved, schema-valid (zero new errors), document reopens cleanly.

## Formatting corrections applied
| # | Rule | Action |
|---|---|---|
| 1 | Paper size A4 | Enforced 21 × 29.7 cm on all 4 sections (was already A4). |
| 2 | Margins: Left 3.5, Top/Bottom/Right 3 cm | **Left changed 3 → 3.5 cm**; others confirmed 3 cm; gutter set 0; applied to all sections. |
| 3 | Font: Times New Roman | Set TNR as the document default (docDefaults ascii/hAnsi) and on Normal + all heading + Chapter-divider styles. Arabic (complex-script) runs keep their own script font. |
| 4 | Body text: 12 pt, justified, 1.5 line, 6 pt before/after, 1 cm first-line indent | Applied to the **Normal** style (was 11 pt, 10 pt-after, no indent). |
| 5 | Chapter titles: TNR 14 pt bold centred, new page | **Heading 1** set to 14 pt bold centred (was 16 pt). Chapters already begin on new pages (existing page breaks preserved). |
| 6 | First-level headings (x.y): 13 pt bold left | **Heading 2** set to 13 pt bold left. |
| 7 | Second-level headings (x.y.z): 12 pt bold left | **Heading 3** set to 12 pt bold left; **Heading 4** likewise (guideline unspecified → kept consistent). |
| 8 | Table/figure captions: 12 pt, left, chapter-numbered | The **24 real captions** (Table/Figure N.N.) set to 12 pt, left-aligned, TNR, no indent. Table captions remain **above** their tables; figure captions remain **below** their figures. In-text sentences beginning "Figure 5.1 illustrates…" were correctly **not** treated as captions. |
| 9 | Indent scope | Removed the inherited 1 cm first-line indent from headings, captions, chapter dividers, lists, TOC entries, and **all table cells** (equations, bibliography, data tables) so only body prose is indented. |
| 10 | Page numbers: bottom-centre | All footer page-number paragraphs set to centred. |
| 11 | Page numbering: Roman (prelim) + Arabic (body) | Verified already configured — sections 0–1 upper-Roman, body section Arabic; preserved. |
| 12 | Update TOC / fields | `w:updateFields = true` set, so Word refreshes the Table of Contents, cross-references, and page numbers on open. |
| 13 | Single-sided | Confirmed no mirror margins / even-odd headers. |

## Rules verified (already compliant — no change needed)
- **Preliminary-page order** (present pages) matches the guideline exactly:
  Title → English Abstract → Arabic Abstract → Acknowledgment → **Table of Contents** →
  List of Tables → List of Figures → List of Abbreviations → Chapter 1 → … → References.
- **Chapters begin on a new page** (existing section/page breaks retained).
- **Equations** and their numbering preserved (equations are laid out as 1-row tables; their
  cells were left at their existing size, ≥ the 9 pt minimum).
- **Red revision text** (previous editorial marks) preserved unchanged.

## Items flagged (could not be applied automatically / need author decision)
1. **Chapter-divider pages (36 pt):** each chapter is preceded by a large 36 pt "Chapter N /
   Title" divider page in addition to the 14 pt chapter heading. The guideline specifies 14 pt
   chapter titles; the divider was set to Times New Roman but its **36 pt size was left
   unchanged** (design element) to avoid destroying the existing layout. If strict compliance
   is required, reduce the divider to 14 pt or remove the divider pages.
2. **Caption label style "Table (3.1):":** the guideline example uses parenthesised
   `Table (3.1):`; the thesis uses `Table 3.1.`. The label punctuation was **not** changed,
   because the in-text cross-references (`Table 3.1`, `Figure 7.8`, …) use the non-parenthesised
   form; changing captions alone would desynchronise them. Apply this only together with the
   matching in-text references if the parenthesised style is mandatory.
3. **List of Tables / List of Figures page numbers:** the main **Table of Contents is a Word
   field** and will rebuild on **Ctrl+A → F9**. The **List of Tables and List of Figures are
   typed** (not fields), so their page numbers (including the earlier-added Table 3.9 entry)
   must be updated **manually** after final pagination.
4. **Missing optional preliminary pages** — Declaration, Examination-Result, Epigraph,
   Dedication, and Appendices are not present. Per instructions, **they were not created**;
   add them manually if the faculty requires them.
5. **Arabic abstract font:** the Arabic (الملخص) text keeps its existing script font; please
   confirm it uses the required Arabic face (e.g., Simplified Arabic) from the reference.
6. **Manual spacer paragraphs:** a few empty paragraphs provide spacing; they were **not**
   deleted (content-preservation), so a small amount of manual spacing remains.
7. **Visual/page-level check:** LibreOffice cannot render DOCX in this environment, so the
   page-level result (chapters starting on new pages with no chapter beginning mid-page, footer
   position, TOC pagination) should be confirmed by opening the file in Microsoft Word and
   pressing **Ctrl+A → F9**.

## Required action in Word
Open `Raed-Rasheed-draft-40-UniversityFormat.docx` and press **Ctrl+A → F9** to refresh the
Table of Contents, cross-references, and page numbers; then type the page numbers for the typed
List of Tables / List of Figures entries.
