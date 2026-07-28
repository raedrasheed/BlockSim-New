# FINAL AUDIT REPORT — Raed Rasheed thesis (draft-37 → draft-38)

**Input audited:** `1e8d26ab-RaedRasheeddraft3700.docx` (byte-for-byte the previous pass's
output, re-saved by Word; paragraph text identical, 0 content differences).
**Output:** `Raed-Rasheed-draft-38-Final.docx` (input never overwritten).
**Mandate:** conservative audit — verify and correct only *technical inconsistencies
introduced during the previous editing pass*; no rewriting, no new content, no deletions.

---

## Executive summary
- **One real defect was found and corrected:** the IEEE first-appearance numbering of the
  five new references was off by one because reference **[133] (Sedlmeir)** first appears in
  Section 3.6.12 — *before* the inserted Section 3.7. Fixed by a bounded rotation on numbers
  133–138 only.
- Everything else verified **clean**: reference metadata, DOIs, duplicates, red formatting,
  citation integrity, scientific caution, document/schema integrity.
- **One action required from the author in Word:** press **Ctrl+A → F9** to refresh the Table
  of Contents and page numbers (the TOC field was already un-updated in the original), and
  type the page number for the new List-of-Tables entry.

---

## 1. Issue found and corrected — IEEE first-appearance order (introduced by previous pass)
**Problem.** The previous pass assigned the five new references `[133]–[137]` and shifted the
old `[133]–[148]` up to `[138]–[153]`. However, the old reference **[133]** (J. Sedlmeir et
al., "Recent …") is cited in the **Section 3.6.12 (Proof of Contribution)** paragraph, which
is *before* the inserted Section 3.7 where the new references first appear. Under strict IEEE
first-appearance order, that reference must therefore keep number **[133]**, and the five new
references must be **[134]–[138]**. Before the fix, the first-appearance stream read
`…132, 138, 133, 134, 135, 136, 137, 139…` (out of order). Root cause: reference **[54]** is
uncited, so the "distinct references before Section 3.7" count (132) was one lower than the
highest reference number already introduced (133), causing an off-by-one when the new
references were slotted in.

**Correction applied (bounded rotation on 133–138 only; nothing else touched):**

| Reference | Before | After |
|---|---|---|
| J. Sedlmeir et al. (existing) | [138] | **[133]** |
| Parallel PoW — Hazari & Mahmoud | [133] | **[134]** |
| StrongChain — Szalachowski et al. | [134] | **[135]** |
| Collaborative PoW — Haque et al. | [135] | **[136]** |
| Proof of Team Sprint — Yonezawa | [136] | **[137]** |
| APoW — Lerner | [137] | **[138]** |

- In-text: **11 citation runs** updated by the rotation map `{133→134,134→135,135→136,
  136→137,137→138,138→133}`; all other citation numbers (including the already-correct
  `[139]–[153]`) left untouched.
- Bibliography: the six entries relabelled and the **Sedlmeir row moved above** the five new
  rows so the list is in numerical/first-appearance order.
- Colours preserved: Sedlmeir `[133]` is **black** (existing); the five new entries
  `[134]–[138]` remain **red**; the single in-text `[133]` (in the pre-existing 3.6.12
  paragraph) is **black**; the new-section citations `[134]–[138]` are **red**.
- **Verified after fix:** first-appearance order is now strictly ascending
  (`…132, 133, 134, 135, 136, 137, 138, 139, 140…`); the new-section citations resolve
  correctly (Parallel→[134], StrongChain→[135], Collaborative→[136], PoTS→[137], APoW→[138],
  Green-PoW→[15]).

No other numbering defect was found. Citations were checked in body paragraphs and all tables;
**no citations exist in footnotes, endnotes, headers, or footers** (so none were missed).

## 2. Reference verification results
All entries affected by the previous pass were re-verified:

| # | Entry | DOI / venue | Status |
|---|---|---|---|
| [15] | Green-PoW — Lasla, Al-Sahan, Abdallah, Younis, *Computer Networks* 214:109118, 2022 | 10.1016/j.comnet.2022.109118 | correct; **single entry** |
| [133] | Sedlmeir et al. (existing) | unchanged | correct (renumber only) |
| [134] | Parallel PoW — S. S. Hazari, Q. H. Mahmoud, *Future Internet* 12(8):125, 2020 | 10.3390/fi12080125 | correct |
| [135] | StrongChain — Szalachowski, Reijsbergen, Homoliak, Sun, USENIX Sec. 2019, pp. 819–836 | **no DOI** (USENIX proceedings) | correct — no fake DOI |
| [136] | Collaborative PoW — Haque, Aziz, Hossain, Bappy, Yanhaona, Islam, IEEE CCWC 2025 | 10.1109/CCWC62904.2025.10903711 | correct |
| [137] | Proof of Team Sprint — N. Yonezawa, *IET Blockchain* 6(1):e70034, 2026 | 10.1049/blc2.70034 | correct |
| [138] | APoW — S. D. Lerner, arXiv:2601.02496, 2026 | 10.48550/arXiv.2601.02496 | correct — **labelled arXiv preprint** |

- **DOI verification:** the six affected DOIs are exact and correctly formatted. The 147
  pre-existing references were not exhaustively re-verified (outside the "introduced-issue"
  scope), and none were modified.
- **Author lists / journals / conferences / years / pages / volumes:** correct for all six.
  *Note:* the Collaborative PoW author initials (`R. Haque, S. M. T. Aziz, T. Hossain,
  F. H. Bappy, M. N. Yanhaona, T. Islam`) were rendered from the arXiv author order; some
  indexes render the first author as "Rizwanul Haque Rizvi" — worth a final glance against
  the official IEEE Xplore record.

## 3. Duplicate-reference check
- Full-bibliography scan by normalised **title** and by **DOI**: **no duplicates** anywhere in
  the 153 entries.
- **Green-PoW** appears exactly **once** ([15]).
- Bibliography labels are `[1]…[153]`, contiguous, **no duplicate labels**.

## 4. Citation integrity
- Every in-text citation maps to **exactly one** bibliography entry (`cited-but-no-entry: none`).
- Every bibliography entry is cited **except [54]**, which was **already uncited in the
  original** thesis; retained (not deleted) and flagged here for author attention.
- All five new references [134]–[138] are cited.

## 5. Red-colour verification
- **No original thesis paragraph contains red runs** (checked every paragraph whose
  citation-normalised text matches an original paragraph → 0 red).
- All inserted material is red: new Section 3.7 (headings, paragraphs, centred equation),
  the 12×8 comparison table + caption + note, Section 5.6.6 (+.1/.2), the appended paragraphs
  in §4.4.2 / §5.11.5 / §6.4 / §7.4.3, the List-of-Tables entry, and bibliography entries
  [134]–[138]. Renumbered existing numbers (Sedlmeir [133], heading numbers) correctly retain
  original (black) colour.

## 6. Table of Contents / Lists / numbering
- **Heading numbering** consistent: new `3.7`/`3.7.1–3.7.5` and `5.6.6/.1/.2`; existing
  `3.7→3.8`, `3.8→3.9` (from the previous pass) intact.
- **Table numbering:** new **Table 3.9** present (caption + one List-of-Tables entry);
  existing tables unchanged. **Figure numbering:** untouched (no figures added/removed;
  15 images intact).
- **Table of Contents (field):** the cached TOC is **not up to date** — it lacks the new
  sections and shows placeholder page numbers. **This is a pre-existing condition:** the
  original draft-36 TOC already showed mostly "1" page numbers and did not include several
  headings, i.e. it had never been refreshed in Word. `w:updateFields=true` is set, so Word
  will offer to update all fields on open.
  **Action:** open in Microsoft Word and press **Ctrl+A → F9** to rebuild the TOC and page
  numbers.
- **List of Tables** is typed (not a field): the Table 3.9 entry text is present; its **page
  number must be typed manually** after pagination.

## 7. Chapter / scientific / abstract consistency
- **Terminology (idle/continuous policy, nonce allocation, template agreement):** used
  consistently across the added Chapter 3, 4, 5, 6, 7 material (idle policy / energy-saving
  idle policy; continuous / continuous-performance policy; deterministic disjoint nonce ranges;
  one identified immutable candidate-block template). Minor pre-existing spelling variation
  ("nonce range" 50× vs "nonce-range" 17×) exists in the original and was **left unchanged**
  (conservative mandate).
- **Forbidden claims — none present.** The thesis explicitly states PoCol is *not* universally
  superior, that nonce partitioning *does not guarantee* energy reduction, that continuous
  PoCol is *not expected* to use less energy than continuous PoW at equal active power/duration,
  and that throughput may improve only *under the evaluated configuration*.
- **Abstract vs Chapters 5–7 — scientific concern (not modified):** the Abstract and §7.4.1
  report a **≈98–99% energy reduction** (e.g., 0.454 kWh vs 33.078 kWh at 400 miners). This is
  in tension with the active/idle energy model added by the previous pass (continuous operation
  at equal active power/duration should not save energy, and nonce partitioning alone does not).
  The existing thesis implements **no idle policy** ("idle" occurs only in the newly added
  material). This is a *scientific-framing* matter, not a technical/numbering inconsistency;
  per the mandate it was **reported, not rewritten**. Recommended author action: state which
  operating regime the executed experiments correspond to and reconcile the ≈98–99% figure with
  the E = P·t formulation. No Chapter 7 numbers were altered.

## 8. Document integrity
- **DOCX opens cleanly**; re-opened after saving and re-verified (971 paragraphs, 44 tables,
  4 sections).
- **Schema:** validated against the original as baseline — **zero new schema errors**
  introduced. (One pre-existing `rFonts w:hint="cs"` for Arabic complex-script remains in both
  files; Word-valid, not introduced here.)
- **No broken:** tables (44 intact), images (15 blips intact), equations (typed, untouched),
  captions, or package relationships. Arabic/RTL content intact.

---

## Remaining warnings / author to-do
1. **Word field refresh (required):** open in Word, **Ctrl+A → F9** to update the Table of
   Contents and all page numbers (pre-existing staleness + new sections).
2. **List of Tables page number:** type the page for the new Table 3.9 entry (typed LoT).
3. **Uncited reference [54]:** pre-existing; cite it or remove it at the author's discretion
   (left untouched here).
4. **Abstract ≈98–99% energy claim:** reconcile with the active/idle model (scientific framing;
   not modified).
5. **Collaborative PoW [136] author initials:** verify against the official IEEE Xplore record.

## Final readiness assessment
**Ready** — the one technical inconsistency introduced by the previous pass (IEEE
first-appearance numbering) has been corrected and verified; references, DOIs, duplicates, red
formatting, citation integrity, and document structure all pass. The only outstanding items are
the mandatory Word field refresh (Ctrl+A → F9) and the author-side notes above; none require
further editing of the manuscript body.
