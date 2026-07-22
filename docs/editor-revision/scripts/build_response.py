#!/usr/bin/env python3
"""Build Response_to_Handling_Editor.docx"""
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

d = Document()
st = d.styles["Normal"]; st.font.name = "Calibri"; st.font.size = Pt(11)

def H(t, lvl=1):
    p = d.add_heading(t, level=lvl); return p
def P(t, bold=False, italic=False):
    p = d.add_paragraph(); r = p.add_run(t); r.bold = bold; r.italic = italic; return p
def quote(t):
    p = d.add_paragraph(); p.paragraph_format.left_indent = Pt(24)
    r = p.add_run(t); r.italic = True; return p

title = d.add_paragraph(); title.alignment = WD_ALIGN_PARAGRAPH.CENTER
tr = title.add_run("Response to the Handling Editor"); tr.bold = True; tr.font.size = Pt(15)
sub = d.add_paragraph(); sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
sub.add_run("Manuscript: Extending BlockSim with Energy and Carbon Footprint "
            "Modeling for Sustainable Blockchain Evaluation").italic = True

P("Dear Professor Pareschi,")
P("Thank you for your careful editorial assessment and for confirming that the "
  "scientific contribution and substantive revisions have been satisfactorily "
  "addressed. We have revised the manuscript comprehensively to resolve all "
  "remaining numerical, methodological-presentation, consistency, figure, and "
  "editorial issues. No new experiments or unsupported scientific claims have "
  "been introduced. All changes in the revised manuscript have been marked in "
  "red (RGB 255,0,0 / #FF0000) to facilitate editorial verification. A detailed "
  "point-by-point response is provided below; section and figure numbers refer "
  "to the revised clean manuscript (Manuscript_Final_Editor_Revision_Red.docx).")

P("Overarching reconciliation of the response letters.", bold=True)
P("You noted that the response to Reviewer 1 (Bitcoin/Ethereum and "
  "\"historical Ethereum-like PoW\" framing removed) conflicts with the response "
  "to Reviewer 2 (Figures 1-3 kept unchanged). Following your instruction, we "
  "resolved the conflict in favour of Reviewer 1: the residual cryptocurrency "
  "framing has been removed, Figures 1-3 have been eliminated, the remaining "
  "figures generalised to PoW/PoS scenarios and renumbered, and this response "
  "report now reflects the final manuscript exactly (superseding the earlier "
  "reviewer letters where they diverge).")

# ---- point-by-point ----
items = [

("Comment 1 - Remove residual Bitcoin/Ethereum and \"historical Ethereum-like PoW\" framing; generalise to PoW/PoS.",
 "Bitcoin/Ethereum still appeared in the Scope Statement, figure labels, and Results §A "
 "(\"the Ethereum-labeled curve is a historical Ethereum-like PoW configuration\").",
 "Action taken:\n"
 "• The sentence identifying the \"Ethereum-labelled curve\" as a \"historical "
 "Ethereum-like PoW configuration\" was deleted from Results §A (Energy Consumption "
 "Analysis) together with the fixed-power scenario paragraphs that carried the "
 "Bitcoin/Ethereum labels.\n"
 "• The carbon figure (now Figure 4) was regenerated with generic legend labels "
 "\"PoW scenario\" and \"PoS scenario\" in place of \"PoW BTC\"/\"PoS ETH\".\n"
 "• All figure labels containing Bitcoin/Ethereum/BTC/ETH were removed with the "
 "deleted Figures 1-3 (which were the only figures carrying such labels).\n"
 "• A whole-manuscript search reduced Ethereum from 11 to 3 occurrences and Bitcoin "
 "from 8 to 6; every retained occurrence is a literature/historical reference "
 "(intro mention of Bitcoin's inception; the De Vries Merge citation in the "
 "Sybil-resistance subsection and the PoS results literature check; and reference "
 "titles). BTC/ETH: 0 occurrences. \"Ethereum-like\"/\"historical Ethereum-like\": 0.\n"
 "Location: Scope/Abstract; Results §A and §B; Figure 4; reference list. "
 "The Scope-Statement phrase \"reference configurations (Bitcoin and Ethereum)\" and "
 "the word \"validate\" were already absent from this manuscript version (0 occurrences), "
 "so no change was required there; this is documented in the audit report."),

("Comment 2 - Replace overstated \"validate\" language with scenario-based/sanity-check wording.",
 "The Scope Statement previously used \"We validate the framework...\".",
 "Action taken: The current manuscript version already contains no occurrence of "
 "\"validate\" (verified: 0 occurrences). The framework is described as a "
 "\"scenario-based evaluation tool for preliminary what-if analysis rather than a "
 "precise real-world energy estimator\" (Abstract), and the sanity checks are "
 "reported as an \"analytical sanity check\" reproducing E = P·T (Results §A). "
 "The three remaining occurrences of \"validation\" are the standard terms "
 "\"internal/external/construct validity\" and \"block validation\", not claims of "
 "empirical validation. No weakening of accurately supported statements was made. "
 "Location: Abstract; Results §A; Threats to Validity."),

("Comment 3 - Reconcile the inconsistent 1000-miner energy values (6092.25 / 6919 / 6934.13 kWh; 83.84 / 79.79 kWh).",
 "The 1000-miner high-throughput total appeared as 6092.25 kWh (Fig. 1), 6919 kWh "
 "(Fig. 3), and 6934.13 kWh (text); the baseline as 83.84 kWh (text/Fig. 1) vs 79.79 kWh (Fig. 3).",
 "Response: We audited the source of every value. The three high-throughput values and "
 "the two baseline values are single-seed, event-based realisations of the naive "
 "fixed-power simulation over a 10,000 s horizon, sampled at block timestamps: "
 "6092.25 kWh is the Ethereum-1000 end-point of the multi-series Figure 1; 6919 kWh "
 "is the Ethereum-1000 end-point of the pairwise Figure 3; 6934.13 kWh is the "
 "corresponding EnergyLog total quoted in the text; 83.84 kWh and 79.79 kWh are the "
 "matching Bitcoin-1000 end-points of Figures 1 and 3. They disagree because each is "
 "a separate stochastic run (differing block counts/timestamps), none averaged, and "
 "they are reported over a 10,000 s horizon that is inconsistent with the 24 h "
 "horizon of the economic model.\n"
 "Action taken: Per your preferred option, the fixed-power miner-count results were "
 "removed rather than reconciled to one arbitrary value: they were the sole source of "
 "the inconsistency, they are redundant now that the economic PoW model carries the "
 "energy-versus-scale story, and they contradict the economic model. Consequently "
 "6092.25, 6919, 6934.13, 83.84, and 79.79 kWh no longer appear anywhere in the "
 "manuscript (verified: 0 occurrences each), and the same applies to the fixed-power "
 "carbon totals (1.75/37.31/154.28/3085.69 kg). The energy results now reported are "
 "the economic-model values, which are mutually consistent across text, table, and "
 "figures and verified against the released CSV outputs: PoW network energy "
 "≈ 467.5 GWh/24 h (95% CI ± 17.1 GWh), invariant across 50-1000 miners; "
 "155.8 → 779.1 GWh for 20,000 → 100,000 USD/coin.\n"
 "Location: Results §A (Energy) and §B (Carbon); Figures 1-4; Discussion §A."),

("Comment 4 - Wall off (or remove) the fixed-power/miner-count model; do not compare across 10,000 s vs 24 h horizons.",
 "Results §A stated network energy is \"essentially invariant across 50-1000 miners\" "
 "yet reported fixed-power totals that scale with miner count, at a different horizon.",
 "Action taken: The fixed-power/miner-count presentation was removed from the Results. "
 "Results §A now reports only the economic PoW model (invariant to miner count), the "
 "validator-count PoS model, and communication energy, all on a single 24 h horizon. "
 "The naive fixed-power picture is retained only as an explicitly labelled conceptual "
 "contrast in Discussion §A (\"a naïve fixed-power baseline ... not a network-level "
 "estimate\") and as a clearly-flagged \"fixed-power contrast baseline\" row in the new "
 "Table 1. A model-comparison table is included in the audit report. All results are "
 "now reported at the common 24 h horizon, eliminating the 10,000 s vs 24 h "
 "comparison. Location: Results §A; Discussion §A; Table 1."),

("Comment 5 - Eliminate Figures 2 and 3 and simplify/replace Figure 1.",
 "Figures 1-3 used linear axes that compress the smaller series and side-by-side "
 "panels on different y-scales.",
 "Action taken: Figures 1, 2 and 3 (the misleading crypto-labelled, linear, "
 "event-based overlays) were deleted in full - images, caption boxes, in-text "
 "references, and the two duplicated \"step density\" paragraphs that only discussed "
 "them. Figure 1 was removed rather than replaced, because the energy-versus-scale "
 "relationship is now carried by the economic-PoW and PoS figures. The four remaining "
 "figures were renumbered 4→1, 5→2, 6→3, 7→4; all use log axes or "
 "error-bar panels appropriate to their magnitude ranges. Every in-text figure "
 "reference and each caption number was updated and manually verified (references now "
 "point only to Figures 1-4; no reference to Figures 5-7 remains). Location: Results "
 "§A, §B; Figures 1-4."),

("Comment 6 - Add a consolidated experimental-parameters table.",
 "Parameters (κ, C_elec, coin-price range, per-miner wattage, block intervals, "
 "γ values, validator power, peer degree, block size, network sizes, seed count, "
 "horizon) were scattered through the prose.",
 "Action taken: A new Table 1 (Consolidated experimental parameters) was added at the "
 "start of the Experimental Setup, with columns Parameter, Symbol, Value/range, Unit, "
 "Model/scenario, Type (deterministic input / swept / stochastic), and "
 "Source/justification. It separates economic-PoW, fixed-power-baseline, PoS, "
 "communication, and carbon parameters, marks author-selected values as assumptions, "
 "and cites externally sourced values ([6],[11],[13],[14]). Every value was verified "
 "against the released code, CSVs, and equations. Because the table is new, all of its "
 "content is red. Location: Experimental Setup, Table 1."),

("Comment 7 - Specify the source of randomness behind the 30-seed confidence intervals.",
 "The economic-PoW and PoS quantities are deterministic (fixed-power configurations "
 "reproduce E = P·T exactly), so the inputs varying across seeds must be stated.",
 "Action taken: A new subsection \"E. Randomness, Replications, and Confidence-Interval "
 "Construction\" was added to the Experimental Setup. It states that the energy "
 "equations are deterministic and that the 30-seed intervals arise from verified "
 "scenario-level stochasticity: for PoW, a Poisson draw of the block count and "
 "Gaussian jitter on coin price (±5%) and transaction fees (±40%), with "
 "Dirichlet hashpower shares; for PoS, Gaussian jitter on per-validator power "
 "(±10%) and uptime (±1%). Purely deterministic quantities (the E = P·T "
 "sanity check) are reported as exact values without confidence intervals. These "
 "sources are all present in the released code (Models/Energy/scenarios.py). "
 "Location: Experimental Setup §E; Results §A."),

("Comment 8 - Reconcile Threats to Validity with the new γ-sensitivity analysis.",
 "The Threats to Validity paragraph still described a fixed emission factor as a "
 "limitation, contradicting the three-scenario γ analysis.",
 "Action taken: That paragraph was rewritten to state that the analysis evaluates "
 "three discrete emission-factor scenarios which nonetheless do not capture the full "
 "temporal/geographical variability of grid carbon intensity or real-time/marginal "
 "emissions, so carbon estimates are scenario-based comparisons rather than "
 "location-specific measurements. This is now consistent with the matching statement "
 "in \"Additional limitations\" (item three). Location: Threats to Validity."),

("Comment 9 - Remove duplicated/obsolete/placeholder text.",
 "Items flagged: two near-identical \"step density\" paragraphs; the APC funding "
 "placeholder; the truncated Generative-AI-disclosure sentence; \"[21][21]\" in the "
 "reference list; and \"PoW. PoW\" in the keywords.",
 "Action taken:\n"
 "• Step density: both duplicated paragraphs were removed (they discussed only the "
 "deleted event-based Figure 1); 0 occurrences remain.\n"
 "• APC placeholder (\"Raed S. Rasheed will pay the total of APC...\"): already "
 "absent from this manuscript version (0 occurrences); documented in the audit.\n"
 "• Reference 21: the manually-typed \"[21]\" prefix was removed so Word's automatic "
 "numbering is not duplicated; a stray \"]\" prefix on reference 15 was also removed.\n"
 "• Keywords: \"PoW. PoW\" corrected to \"PoW, PoS\" with a consistent comma "
 "separator.\n"
 "• Generative-AI disclosure: no Generative-AI disclosure section exists in this "
 "manuscript version, so there was no truncated sentence to repair; this is flagged in "
 "the audit report as requiring author confirmation if the target journal mandates such "
 "a statement.\n"
 "Location: Results §A; Introduction; Keywords; Reference list."),
]

for head, comment, resp in items:
    H(head, 2)
    P("Editor's comment:", bold=True); quote(comment)
    P("Response and exact action taken:", bold=True)
    for para in resp.split("\n"):
        if para.strip():
            d.add_paragraph(para)
    P("Marked in red in the manuscript: Yes (all inserted/replacement text; "
      "deletions removed from the clean copy and recorded in the change log).", italic=True)

H("Closing", 2)
P("All changes made in the revised manuscript have been marked in red to "
  "facilitate editorial verification. Unchanged text has been retained in its "
  "original formatting, while deleted material has been removed from the clean "
  "manuscript and documented in the accompanying change log "
  "(Revision_Change_Log.xlsx) and internal audit "
  "(Final_Consistency_Numerical_and_Red_Text_Audit.docx). We are happy to make "
  "any further adjustments you require.")
P("")
P("Kind regards,")
P("Raed S. Rasheed and Aiman A. AbuSamra")

d.save("Response_to_Handling_Editor.docx")
print("saved Response_to_Handling_Editor.docx")
