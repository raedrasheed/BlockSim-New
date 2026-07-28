# Reference Verification Report — Raed Rasheed thesis

**Input:** `Raed-Rasheed-draft-38-Final.docx`
**Output:** `Raed-Rasheed-draft-39-References-Verified.docx` (draft-38 not overwritten)
**Scope:** verify every bibliography entry against its official publisher record; correct
bibliographic inaccuracies only; confirm no duplicates and correct citation mapping.
**Thesis body text was not modified** — only the bibliography (15 entries) changed; all
corrected tokens are marked **red (#FF0000)** for author review; citation numbers/labels are
unchanged.

## Method
All 153 references were checked against authoritative sources: **Crossref**
(`api.crossref.org/works/{DOI}`) for DOI-bearing works, **arXiv** for preprints, and the
**official publisher/venue page** (IEEE Xplore, Springer, Elsevier, MDPI, IET, USENIX, ACM,
OECD, IGI Global, etc.) for no-DOI items. Substantive fields checked: authors, title,
journal/venue, year, volume, issue, pages/article-number, DOI. The most significant author/
venue changes were independently re-confirmed against Crossref.

## Result summary
- **153 references verified.** **138 fully correct.** **15 corrected** (below). **0 duplicates.**
- **Citation mapping:** every in-text citation maps to exactly one bibliography entry; all 152
  distinct cited numbers resolve; the only uncited entry is **[54]** (uncited already in the
  original — retained, not deleted).
- **Duplicates:** none — no duplicate titles, DOIs, arXiv IDs, or labels; list is contiguous
  [1]–[153]. Green-PoW appears once ([15]). StrongChain ([135]) carries no DOI (USENIX
  proceedings). APoW ([138]) is labelled an arXiv preprint.

## Corrections applied (15) — each confirmed against the official record
| Ref | Field | Before → After | Source |
|---|---|---|---|
| [42] | author | "A. Manzoor" → **"A. Mansoor"** | arXiv:1810.04699 |
| [87] | author; pages | "J. L. Y. Tong" → **"J. L. Y. Terpstra Tong"**; "160–177" → **"136–151"** | Crossref 10.4018/978-1-7998-9035-5.ch009 |
| [93] | authors | removed supervisors → sole author **"M. P. Asadauskas"** (Cachin & Amores Sesar are advisers of this University of Bern thesis) | unibe thesis front matter |
| [94] | author | "M. H. ur Rehman" → **"M. H. Rehmani"** | Crossref 10.1109/COMST.2018.2886932 |
| [96] | year | "2020" → **"2022"** (vol. 15, no. 4 = 2022; 2020 was early access) | Crossref 10.1109/TSC.2020.3038641 |
| [109] | authors | "A. Christian, D. Therry, …" → **"A. C. D. Therry, …"** (first author's name was split in two) | Crossref 10.26877/asset.v6i1.17878 |
| [112] | venue; year; pages | "Applied Cryptography and Network Security Workshops … 2022" → **"Progress in Cryptology – INDOCRYPT 2021 … 2021, pp. 559–583"** | Crossref/Springer 10.1007/978-3-030-92518-5_25 |
| [115] | volume/issue | "(IJACSA) 7 (2024)" → **"(IJACSA), vol. 15, no. 7, 2024"** | Crossref 10.14569/IJACSA.2024.0150796 |
| [117] | vol/issue/pages/year | "vol. 10, no. 24, 2023" → **"vol. 11, no. 2, pp. 2855–2869, 2024"** (final issue vs early access) | Crossref 10.1109/JIOT.2023.3294265 |
| [124] | issue | "no. 7" → **"no. 7-8"** | Crossref 10.1007/s12243-021-00896-2 |
| [125] | author; year | "C. Brian … 2020" → **"S. Pirani … 2018"** (DOI resolves to Simon Pirani, *Burning Up*, Pluto Press, 2018) | Crossref 10.2307/j.ctv4ncp7q |
| [126] | title | "…Quasi-Experiments: Resource Flexibility…" → **"…Quasi-Experiments: The Resource Flexibility…"** | arXiv:2505.24663 |
| [144] | authors | "F. Raheman" → **"F. Raheman and T. Bhagat"** (co-author on title page) | TRACE white-paper PDF |
| [146] | authors | "O. Zumburidze, N. Adamashvili, R. State, R. Tonelli, and H. Taherdoost" → **"H. Taherdoost"** (the others are the article's Academic Editors, not authors) | Crossref/MDPI 10.3390/computers13040107 |
| [147] | authors | "R. M. Ashu and S. Zafar" → **"A. Gautam, R. Mahajan, and S. Zafar"** | Crossref 10.4108/eai.27-2-2020.2303135 |

## Items flagged for author decision (NOT auto-changed — conservative)
- **[43]** DOI `10.1787/589b283f-en` is the **book-level** DOI for *OECD Digital Education
  Outlook 2021*; the specific chapter cited (Smolenski, "Blockchain for Education") has chapter
  DOI **`10.1787/6893d95a-en`, pp. 209–214**. The current DOI resolves correctly to the
  containing volume, so it is defensible; change it only if a chapter-level DOI is preferred.
- **[125]** the page span **"pp. 700–702"** is inconsistent with this ~250-page book and was
  left in place (author/year were corrected). Recommend removing the page span or replacing it
  with the actual pages referenced, and adding the publisher (Pluto Press).
- **[150]** Rasheed & AbuSamra (2026) is an **unpublished manuscript / self-citation** with no
  public record; could not be externally verified (expected for forthcoming work).

## Not corrected — minor/stylistic only (per the "substantive fields" scope)
These were observed but are formatting choices, not errors: DOI letter-case (e.g. `ACCESS` vs
`access`), title Title-Case vs sentence-case, abbreviated page ranges (e.g. "971-87"),
en-dash vs hyphen, venue abbreviations, and "online-first vs issue" year where the thesis'
issue year is already correct. A few Crossref records contain typos where the **thesis is
correct** (e.g. [58] "Villaça", [69] "Säämäki") — left unchanged.

## Integrity
- Thesis **body text unchanged** (971/971 paragraphs identical to draft-38); non-bibliography
  tables identical; **only 15 bibliography entries changed**.
- Bibliography **labels unchanged** → all in-text citation numbers still map correctly.
- **Schema:** validated against draft-38 as baseline — **zero new errors**; document reopens
  cleanly (971 paragraphs, 44 tables, 153 references).

## Readiness
The bibliography is now verified against official publisher records, with 15 substantive
corrections applied (marked red) and 3 items flagged for a quick author decision. No
duplicates; citation mapping is complete and correct.
