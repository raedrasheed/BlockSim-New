# Raed-Rasheed-draft-37 — External Edit Report

## 1. Files
- **Input (never modified):** `Raed-Rasheed-draft-36-00.docx` (working name; source upload `649e3c32-RaedRasheeddraft3600.docx`).
- **Backup:** `Raed-Rasheed-draft-36-00-BACKUP.docx` — byte-identical to the input (MD5 `1078ca34704897623b24488616ac2950`).
- **Output:** `Raed-Rasheed-draft-37-Related-Work-Added.docx`.
- **This report:** `Raed-Rasheed-draft-37-EDIT-REPORT.md`.

All newly inserted material is coloured **red (RGB FF0000)**. Existing text keeps its original colour. No Track Changes were used (none were enabled in the source).

## 2. Structure discovered before editing
- Heading numbers (e.g. `3.7.`, `3.6.12.`) are **typed text**, not Word list-numbering (`numId=0` cancels list numbering). Renumbering therefore edits the typed number characters.
- The **bibliography is a 148-row 2-column table** (`[n]` | reference text); in-text citations are **plain-text `[n]`** (590 tokens, none split across runs).
- The **Table of Contents, List of Figures** are real Word fields (`TOC`, `PAGEREF`). The **List of Tables** and all **table captions/numbers** are **typed** (no `SEQ` fields).
- The document contains **no Word (OMML) equations** — existing formulas are typed lines; new equations were therefore added as centred typed lines.
- The existing bibliography was already in exact first-appearance order (`[1]`…`[148]`).

## 3. Exact insertion locations
| New material | Inserted |
|---|---|
| New Section 3.7 (5 subsections + Table 3.9 + note) | Immediately after Section 3.6.12 content, before the (renumbered) Section 3.8 |
| Section 5.6.6 (+ 5.6.6.1, 5.6.6.2) | Immediately after Section 5.6.5, before Section 5.7 |
| 4 paragraphs appended to Section 5.11.5 | End of 5.11.5, before Section 5.12 |
| 2 equations + 3 paragraphs appended to Section 4.4.2 | End of 4.4.2, before Section 4.5 |
| 2 paragraphs appended to Section 6.4 | End of 6.4, before Section 6.5 |
| 1 paragraph appended to Section 7.4.3 | End of 7.4.3, before Section 7.5 |
| List-of-Tables entry for Table 3.9 | After the Table 3.8 entry, before the Table 6.1 entry |

## 4. New headings and their final numbers
- 3.7. Parallel, Collaborative, and Energy-Aware Proof-of-Work Approaches
  - 3.7.1. Parallel and Partitioned Mining
  - 3.7.2. Collaborative and Team-Based Proof-of-Work
  - 3.7.3. Energy-Aware Mining Policies
  - 3.7.4. Auditable Mining Contribution
  - 3.7.5. Comparison with PoCol and Identified Research Gap
- 5.6.6. Post-Range Operating Policies
  - 5.6.6.1. Energy-Saving Idle Policy
  - 5.6.6.2. Continuous Performance Policy

**Existing Chapter 3 sections renumbered (typed numbers changed; original colour retained):**
`3.7 → 3.8`, `3.7.1 → 3.8.1`, `3.7.1.1 → 3.8.1.1`, `3.7.1.2 → 3.8.1.2`, `3.7.2 → 3.8.2`, `3.7.3 → 3.8.3`, `3.8 Conclusion → 3.9 Conclusion`.
(No Chapter 5 renumbering was needed: 5.6.6 is new and 5.6.5 was the last 5.6.x subsection.)

## 5. New table
- **Caption (red):** *Table 3.9. Comparison of PoCol with parallel, collaborative, auditable, and energy-aware Proof-of-Work approaches.*
- 12 rows × 8 columns; borders/style copied from the existing Chapter 3 comparison table; **entire table, caption, and note are red**.
- **Table number rationale:** STEP 4 does not instruct renumbering existing tables (contrast STEP 2/STEP 11 which explicitly do). To preserve existing captions/cross-references (non-negotiable rule 2), the new table is numbered **3.9** (next sequential number). Existing Tables 3.7 and 3.8 were **not** renumbered. This is a deliberate, documented choice; if strict by-appearance numbering (new = 3.7) is preferred, tell me and I will renumber the two existing tables, their two in-text references, and their two List-of-Tables entries.

## 6. Final reference numbers (new / reused)
| Reference | Final number | Status |
|---|---|---|
| Parallel PoW — Hazari & Mahmoud, *Future Internet* 12(8):125, 2020, doi 10.3390/fi12080125 | **[133]** | new (red) |
| StrongChain — Szalachowski, Reijsbergen, Homoliak, Sun, USENIX Sec. 2019, pp. 819–836 | **[134]** | new (red) |
| Collaborative PoW — Haque, Aziz, Hossain, Bappy, Yanhaona, Islam, IEEE CCWC 2025, doi 10.1109/CCWC62904.2025.10903711 | **[135]** | new (red) |
| Proof of Team Sprint — Yonezawa, *IET Blockchain* 6(1):e70034, 2026, doi 10.1049/blc2.70034 | **[136]** | new (red) |
| APoW — Lerner, arXiv:2601.02496, 2026, doi 10.48550/arXiv.2601.02496 (arXiv preprint) | **[137]** | new (red) |
| Green-PoW — Lasla, Al-Sahan, Abdallah, Younis, *Computer Networks* 214:109118, 2022 | **[15]** | **reused existing** |

All six were verified to be **real, existing publications** (web-verified titles, venues, DOIs, and — for Collaborative PoW — the exact arXiv author order). StrongChain is cited as the USENIX proceedings entry; the ACM index `10.5555/3361338.3361395` is **not** presented as a publisher DOI. APoW is labelled an arXiv preprint.

## 7. Duplicate references found and merged
- **Green-PoW:** exactly **one** existing entry (`[15]`, Lasla et al., *Computer Networks*, 2022) — matches the requested canonical reference. **No duplicate existed; nothing merged.** All Green-PoW citations map to `[15]`.
- No other duplicates were detected among the affected entries.

## 8. Complete old → new reference-number map
- References **[1] – [132]:** unchanged.
- **New entries inserted by first appearance (new Section 3.7):** [133], [134], [135], [136], [137] (see §6).
- **Existing entries shifted +5** (first appearance falls after new Section 3.7):

| Old | New |  | Old | New |  | Old | New |  | Old | New |
|---|---|---|---|---|---|---|---|---|---|---|
| [133] | [138] | | [137] | [142] | | [141] | [146] | | [145] | [150] |
| [134] | [139] | | [138] | [143] | | [142] | [147] | | [146] | [151] |
| [135] | [140] | | [139] | [144] | | [143] | [148] | | [147] | [152] |
| [136] | [141] | | [140] | [145] | | [144] | [149] | | [148] | [153] |

## 9. In-text citations updated
- **44** in-text citation tokens referencing old `[133]–[148]` were rewritten to `[138]–[153]` (paragraphs and tables; the bibliography table was relabelled separately). Total citation tokens conserved at **590**; automated conservation check passed (every old *n*∈[133,148] → *n*+5, all others unchanged, no residual old [133]–[137]).
- Per rules 13–14, these renumbered existing citations and the 16 relabelled existing bibliography labels **retain their original (black) colour**; only genuinely new material is red. This map is the required renumbering record.

## 10. Validation performed
- **Content integrity:** original 921 body paragraphs vs. output — after applying the two required transforms (citation shift + heading renumber), the 921 existing paragraphs match the output's 921 non-red paragraphs **exactly, in order (0 discrepancies)**. 50 new red paragraphs were added.
- **No deletions:** tables 43 → 44 (+1 comparison table); embedded images/blips 15 → 15 (none lost); 4 section definitions preserved; Arabic/RTL text present and unchanged.
- **Citations:** every in-text citation maps to a bibliography entry; every new entry [133]–[137] is cited; bibliography now [1]–[153].
- **Placeholders:** none of `[PARALLEL_POW] [STRONGCHAIN] [COLLABORATIVE_POW] [POTS] [GREEN_POW] [APOW]` remain.
- **Red formatting:** new Section 3.7 headings/paragraphs, new equations (centred), the 12×8 table + caption + note, Section 5.6.6, all appended paragraphs, the LoT entry, and the five new bibliography rows are red (RGB FF0000); verified run-by-run.
- **DOCX/schema:** package reopens cleanly; validated against the original as baseline — **zero new schema errors introduced** (`All validations PASSED`). One pre-existing `rFonts w:hint="cs"` (Arabic complex-script) remains in both files; it is Word-valid and was **not** introduced by this edit.
- **PDF render:** LibreOffice could not load DOCX in this execution environment, so a rendered PDF review copy could not be produced here. Programmatic validation was used instead.

## 11. Fields the user must update in Word (Ctrl+A → F9)
`w:updateFields=true` was set, so Microsoft Word will offer to update all fields on open. After opening, **select all (Ctrl+A) and press F9** to refresh:
- the **Table of Contents** (new Sections 3.7.x and 5.6.6 appear; renumbered 3.8/3.9 headings update),
- all **PAGEREF/page numbers**.
- **List of Tables (manual):** the LoT is typed text, so Word will **not** auto-generate the Table 3.9 page number. The Table 3.9 entry text was inserted (red); **the page number must be typed in manually** after final pagination.

## 12. Inconsistency between existing energy-saving claims, the new active/idle model, and the implemented scenarios
This is flagged here only; **no Chapter 7 numerical result was altered** (per STEP 9).
- The thesis states PoCol reduces total energy by **≈ 98–99 %** (Abstract, para with "0.454 kWh versus 33.078 kWh at 400 miners"; Section 7.4.1 reports e.g. "≈ 98.3 %" and "≈ 98.6 %" reductions vs. PoW).
- The existing thesis contains **no occurrence of an "idle" policy** — the post-range idle vs. continuous distinction is introduced by this revision. There is therefore **no implementation evidence that an idle scenario was executed**; the reported ≈98–99 % reductions come from the already-implemented PoCol runs.
- **Tension:** the newly added model states that, under the **continuous-performance policy** with active power and duration equal to the PoW baseline, PoCol is *not* expected to consume less energy, and that nonce-range partitioning **alone** does not guarantee energy savings. A ≈98–99 % reduction is far larger than nonce-separation-at-equal-active-power would predict; it implies the implemented PoCol effectively realised a **reduced-active-work regime** (e.g. eliminating duplicated/competitive hashing, or fewer effective active hashes), which is closer in spirit to the idle policy than to equal-active-power continuous operation.
- **Recommended author action (not performed here):** explicitly characterise which operating regime the executed experiments correspond to, and reconcile the ≈98–99 % figure with the active/idle energy model (E = P_active·t_active + P_idle·t_idle + E_coord). The new bounded clarifications added to §4.4.2, §6.4, and §7.4.3 are consistent with the existing results and do not contradict them, but the headline ≈98–99 % claim should be re-grounded in the active/idle formulation.

## 13. Requested modifications not completed / deliberate deviations
- **Table numbering** kept existing Tables 3.7/3.8 unchanged; new table = **3.9** (see §5 rationale). Reversible on request.
- **Renumbered existing numbers** (7 heading numbers, 44 in-text citations, 16 bibliography labels) **retain original colour** with this report serving as the renumbering map, as explicitly permitted by rules 13–14 (avoids run-splitting/field-corruption risk on existing content). New material is red.
- **List-of-Tables page number** for Table 3.9 must be filled manually (typed LoT; see §11).
- **Pre-existing uncited reference:** bibliography entry **[54]** was uncited in the original and remains uncited (it was not removed, per rule 2 / "do not remove an uncited reference without documenting it"). Flagged here for author attention.
- **PDF review copy** not produced (LibreOffice unavailable in this environment).
- Author-name initials for Collaborative PoW ([135]) were rendered in IEEE style from the arXiv author list (`R. Haque, S. M. T. Aziz, T. Hossain, F. H. Bappy, M. N. Yanhaona, and T. Islam`); please verify against the official IEEE Xplore record, as some sources render the first author as "Rizwanul Haque Rizvi".
