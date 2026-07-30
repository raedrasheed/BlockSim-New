# Stage 7 — Rendering Report

## Outcome: PDF render and visual inspection could NOT be completed (environment blocker)

The examiner-review DOCX `Raed-Rasheed-draft-43-00.docx` was produced and OOXML-validated,
but **`Raed-Rasheed-draft-43-00.pdf` could not be generated** and the §17 visual rendering
inspection could not be performed, because the container's document renderer is
non-functional.

## Evidence (reproducible)

LibreOffice (`soffice` 24.2.7.2) starts and creates a user profile but **fails to load or
convert any input file**, including a one-line `.txt`:

- `soffice --headless --convert-to pdf t.txt` → `Error: source file could not be loaded`
- `soffice.bin … --convert-to pdf draft43.docx` → `Error: source file could not be loaded`
- Attempts covered: the skill's `run_soffice` wrapper; `soffice.bin` directly;
  `SAL_USE_VCLPLUGIN=svp`; fresh `-env:UserInstallation` profiles; input as path and as a
  `file://` URL; working directories under both `/tmp/.../scratchpad` and `/home/user`;
  a trivial `.txt` returned exit code 81 with empty output. `needs_shim` is False (AF_UNIX
  not blocked), fontconfig (59 fonts) and Java are present — the failure is in the import
  path, not a missing font/JRE.

No alternative raster/PDF tool is available either: `pdftoppm`, `pdftocairo`, `mutool`,
`convert` (ImageMagick), `gs`, and `pandoc` are all absent; DOCX→PDF requires LibreOffice
or Word, neither of which is functional here. PyMuPDF (installed) renders PDFs but cannot
open DOCX.

## What this blocks

- §3 render of `draft-43.pdf`.
- §17 items 1–13 that require inspecting a faithful Word render (clipped tables/captions,
  cropped figures, split equations, broken Arabic layout, unreadable red text, page
  numbering, header/footer, white space).

## What was verified WITHOUT a render

- OOXML schema validation: **All validations PASSED**.
- Package integrity: 44/44 parts identical to draft-42; blips 15/15, equations 488/488,
  fields 346/346, hyperlinks 172/172, relationships 33/33 (`STAGE_07_DOCX_INTEGRITY_REPORT.md`).
- Red-format policy: 13 net-new red runs, 0 original runs recoloured
  (`STAGE_07_RED_FORMAT_AUDIT.md`).
- Scientific-number, claim, and citation audits: PASS.
- draft-42 DOCX SHA-256 unchanged (`2c3afdc5…`).

## Required to clear the block

Open `Raed-Rasheed-draft-43-00.docx` in Microsoft Word or a working LibreOffice, export to
PDF, and perform the §17 page-by-page visual inspection; or re-run Stage 7's render step in
an environment with a functional `soffice`/`pdftoppm`. The DOCX is ready for that step.
