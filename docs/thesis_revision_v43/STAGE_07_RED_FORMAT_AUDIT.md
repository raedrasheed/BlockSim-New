# Stage 7 — Red-Format Audit

Policy (§4): all newly inserted or substantively modified text is red
(`<w:color w:val="FF0000"/>`); unchanged original text keeps its original formatting and
colour; no uncontrolled Track Changes.

## Verification

| Check | Result |
|-------|--------|
| Red (`FF0000`) runs in draft-42 | **0** |
| Red (`FF0000`) runs in draft-43 | **13** |
| Net new red runs | **13** (all inserted/modified text) |
| Original runs recoloured red | **0** (draft-42 had no red; every red run in draft-43 is new/modified) |
| Track Changes enabled | No (`settings.xml` unchanged; no `<w:ins>/<w:del>`) |
| Bounded-phrase colouring | Corrections are appended red runs/one reworded heading; whole unchanged paragraphs are **not** recoloured |

Each red run copies the local paragraph run's formatting (font family/size) and adds only
the red colour, so inserted text matches the surrounding typeface. The 13 red runs
correspond one-to-one with the 13 rows of `STAGE_07_CHANGE_LEDGER.csv`
(`red_format_verified = yes` for every row).

## Location of the 13 red edits

Abstract EN (×3: energy %, efficiency overclaim, reward-fairness scope), Abstract AR (×1,
RTL correction), §5.6.4 heading reword (×1), §7.4.1 (×2: 98.3% figure, miner-count
scaling), §7.4.2 (×1), §7.4.3 (×2: energy/H7 scope, idle-policy/H3 note), §8.2 (×1, RQ2),
§8.3 (×1, empirical contribution), §7.1 governing correction notice (×1).

Result: **RED-FORMAT POLICY PASSES** — every correction is red, no original text was
recoloured.
