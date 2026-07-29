# DECISIONS REQUIRED / RESOLVED — Thesis Scientific Revision v43

Decisions surfaced in Stage 0 and their resolution status. Items marked
**RESOLVED** were decided by the candidate's Stage 1 approval message.
Items marked **OPEN** are deferred to the stage indicated.

| # | Decision | Options | Resolution |
|---|---|---|---|
| 1 | Common-template agreement path | Path A (idealized assumption, narrow claims, future work) vs Path B (executable agreement protocol) | **RESOLVED → Path A.** TemplateID enforcement, mempool reconciliation, distributed commitment, timeout/equivocation/view-change remain *specification + future work*; not to be claimed as implemented unless separately approved. |
| 2 | Authoritative energy model | keep `÷N` vs wall-clock state model | **RESOLVED → wall-clock state model** `E=Σ(P_i^act·t_i^act + P_i^idle·t_i^idle + E_i^coord)`. `÷N` is **not** scientifically valid; not modified in Stage 1 (documented only). |
| 3 | Idle-power policy | fixed vs sensitivity | **RESOLVED.** 0% permitted only as explicitly labelled theoretical lower bound; sensitivity ratios **{0, 5, 10, 20, 30}%** of active power. |
| 4 | Coordination energy | invent vs exclude | **RESOLVED.** Never invented; reported as excluded, or set to 0 only under an explicit idealized lower-bound label. |
| 5 | 98–99% energy claim | keep vs let evidence decide | **RESOLVED.** Removal/replacement authorized if corrected, fair, reproducible experiments do not support it. Do **not** tune implementation/experiment to reproduce the prior percentage. |
| 6 | Nonce-range allocation policy | identity-equal vs hash-rate-weighted | **RESOLVED.** Homogeneous baseline = equal hash rates + equal disjoint ranges. Heterogeneous *sensitivity* = configured actual hash rates, weighted allocation evaluated separately. Must state simulator-known hash rate is **not** verifiable in a permissionless deployment. |
| 7 | Working branch base | `main` vs thesis-bearing commit | **RESOLVED (with caveat).** Branch `claude/thesis-scientific-revision-v43`. `main` (`7f3129e`) lacks the thesis; base is `2d3c243` (= `main` + `Add Raed-Rasheed-draft-42-00`). Both SHAs recorded. Candidate may override. |
| 8 | Thesis title | keep vs change | **RESOLVED → keep.** Alternatives may be *proposed* in a later report; **not** applied without separate explicit approval. |
| 9 | Scope | thesis only vs whole repo | **RESOLVED → thesis only.** The "Extending BlockSim" journal manuscript and its PoW-economic/PoS experiments are out of scope and untouched. |
| 10 | Large Bitcoin/Ethereum workbooks | keep/move/delete | **RESOLVED → keep in place, unmodified.** |

## OPEN decisions deferred to later stages
| # | Decision | Deferred to |
|---|---|---|
| O-1 | Whether to implement any executable subset of common-template agreement (Path B) | Post-Stage 7, separate approval |
| O-2 | Final scenario matrix + estimated runtime sign-off before execution | Stage 4 (approve before Stage 5 runs) |
| O-3 | Optional sensitivity dimensions (topology, churn, tx-arrival, template-sync duration) | Stage 5 (propose before execution) |
| O-4 | Any citation renumbering | Stage 9 (dedicated approved stage) |
| O-5 | Title alternatives (recommend only) | Stage 8/11 |
| O-6 | Whether to pin older pandas/numpy to better match original runs | Stage 2 (once impact assessed) |
