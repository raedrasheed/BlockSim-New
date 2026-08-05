# Stage 8U — Caption Package

Naming discipline: the algorithm is **PoCol**; the treatment is **the single-handoff useful-work policy within PoCol**; W00 and W01 are **matched same-template PoW controls** and are never described as Bitcoin, the Bitcoin network or real-world PoW.  Every comparison below is a controlled simulator comparison under matched templates, targets, difficulty, horizon, rates, powers and seeds; W00 and W01 answer different matching questions and are never merged.

# FIG01 — Total energy per run, all five scenarios

Total executed energy per 300 s run for the two matched same-template PoW controls and the three PoCol arms; per-seed points with means and 95% bootstrap CIs.  Controlled simulator comparison — not a claim about any deployed network.

# FIG02 — Relative energy difference of P02 versus W00 and versus W01 (separate panels)

Per-seed paired relative total-energy difference of every PoCol arm against each matched PoW control, shown separately (W00 population-matched is SENSITIVITY; W01 active-capacity-matched carries the preregistered H-U3 gate).  The two controls answer different matching questions and are never merged.

# FIG03 — Accepted blocks per run

Accepted blocks per 300 s run; per-seed points with means and 95% bootstrap CIs.  The preregistered H-U2 service gate compares P02 with W01 only.

# FIG04 — Median and p95 closed-round duration (separate panels)

Median (left panel) and 95th-percentile (right panel) closed-round durations per run, in separate panels as preregistered; per-seed points with means and 95% bootstrap CIs.

# FIG05 — Energy per accepted block (NA when a run has zero blocks)

Energy per accepted block.  A run with zero accepted blocks is recorded as NA and excluded from the mean rather than imputed; no such run occurred among the 60 confirmatory runs.

# FIG06 — Total, unique and duplicate physical evaluations

Total, unique and duplicate committed physical SHA-256 evaluations per run.  PoCol's disjoint-range coordination holds duplicates at exactly zero; the uncoordinated matched PoW controls duplicate most of their work.  Bars are means, black points the 12 per-seed values; the axis starts at zero.

# FIG07 — Accepted blocks per million physical evaluations

Work-efficiency of service: accepted blocks per million committed physical evaluations; per-seed points with means and 95% bootstrap CIs.

# FIG08 — Stacked per-state residency decomposition

Stacked mean per-state residency (node-seconds; the whole population is 20 nodes × 300 s).  The matched PoW controls hold every mining node in ACTIVE_HASHING for the entire horizon — W01 additionally holds 4 non-mining standby nodes at RESERVE_STANDBY — while the PoCol arms spend most node-time in LOW_POWER_LISTEN once assigned ranges complete.

# FIG09 — Stacked energy decomposition (primary hashing, range idle, reserve standby, wake transient, activated-reserve hashing, offline/other)

Stacked mean energy decomposition per run: primary hashing, range idle (LOW_POWER_LISTEN), reserve standby, wake transient, activated-reserve hashing and offline/other.  Reserve and wake components are reported separately from range-idle, as preregistered — the two savings are never combined into a single figure.

# FIG10 — Static and useful floor durations and deficit areas

Static-floor and useful-floor families for the PoCol arms, reported independently (U5: the historical static floor is never lowered or redefined): durations below each floor (left) and deficit areas (right).  Bars are means; black points are per-seed values.

# FIG11 — Activation requests, incomplete activations, handoffs and reassignments per closed round

Controller churn per closed round for the PoCol arms: activation requests, incomplete activations, committed handoffs and total reassignments.  The single-handoff arm removes reserve-wake churn entirely and holds reassignments below one per round by construction.

# FIG12 — Energy-service Pareto plane (per-seed points and scenario centroids)

Energy–service plane: one point per seed plus scenario centroids (stars).  Lower is cheaper, further right is more service; the PoCol arms sit far below the matched PoW controls in energy at reduced block counts.

# FIG13 — Paired per-seed energy slopes W01->P02 and W00->P02

Paired per-seed energy slopes from each matched PoW control to the single-handoff PoCol arm (left: W01, the preregistered gate control; right: W00, sensitivity).  Every seed's line falls.

# FIG14 — Paired per-seed service slopes (accepted blocks)

Paired per-seed service slopes (accepted blocks) from each matched PoW control to the single-handoff PoCol arm (left: W01 gate control; right: W00 sensitivity).  Every seed's line falls, which is why the preregistered H-U2 block-ratio gate fails.

# FIG15 — Representative P02 timeline (H_effective, H_pipeline, static floor, useful target, live wakes, the handoff event, accepted blocks)

Representative P02 timeline (confirmatory seed 0, first 30 s of the horizon): physical H_effective, the H_pipeline scheduling forecast (never a security metric), the useful-work-aware target, the historical static 3200 H floor, accepted blocks (vertical bands), committed handoffs (dotted) and reserve-wake requests (dash-dotted).

# FIG16 — Normalised summary heatmap across scenarios and metrics

Normalised summary heatmap of scenario means; each metric row is scaled min→0 and max→1 with the raw means preserved in the source CSV.  A perceptually uniform, colour-blind-safe colormap is used; the normalisation direction carries no value judgement — integrity gates passed in all 60 runs and are therefore constant across the panel.

# FIG17 — Policy evolution 8M -> 8R -> 8S -> P02 (descriptive only; no cross-stage inferential statistic)

DESCRIPTIVE ONLY: policy evolution across the frozen primary arms of stages 8M (legacy reactive), 8R (predictive static floor), 8S (coarse reassignment) and 8U (single handoff).  Each stage used its own fresh seed registry, so NO cross-stage inferential statistic or p-value is computed or implied.

# FIG18 — Decision dashboard against the frozen pass/fail criteria

Decision dashboard against the frozen preregistered pass/fail criteria of STAGE_08U_PREREGISTRATION.md §5.  The joint licensing rule is H-U1 ∧ H-U2 ∧ H-U3 ∧ H-U5 ∧ all integrity gates; the honest outcome is shown unmodified.
