# Stage 7B — Red-Format Audit (§10)

Corrections are applied as **explicit red runs** (`<w:color w:val="FF0000"/>`), **not** Word
Track Changes. Deleted false claims are removed outright and are not visible in the revised
thesis (their text is preserved only in `STAGE_07B_CHANGE_LEDGER.csv`).

| Metric | draft-42 | draft-44 |
|--------|----------|----------|
| Red runs (`w:color=FF0000`) | 0 | 186 |
| Net-new red runs | — | 186 |
| Track-changes elements (`w:ins`/`w:del`) | 0 | 0 |

- draft-42 contains **0** red runs; therefore **all 186 red runs in draft-44 are
  net-new**, and no original run was recoloured.
- Red content comprises replacement prose (in-place whole-paragraph red runs preserving the
  original paragraph style/rPr, including Arabic RTL), corrected red figure captions, and
  red table cells/headings/captions for the inserted corrected tables. The higher red count
  vs. the number of prose edits reflects one red run per table cell in Tables 7.1–7.3.
- **No uncontrolled Track Changes**: 0 `w:ins`/`w:del` elements introduced.

## Verdict

**RED-FORMAT POLICY: PASS** — all corrections are red (not track-changes); 186
net-new red runs; 0 original runs recoloured; deleted false claims not visible in the body.
