"""Stage 8X-NR — scoped nonce-value-reuse and exact-input metrics.

Scopes and reset rules (brief section 7; documented reset points)
-----------------------------------------------------------------
NR-round           counters reset at every round boundary (a round = one block
                   race under one previous-block context; it ends when a block
                   is accepted or the run horizon truncates it).
NR-template-epoch  counters reset at every template-epoch boundary (2^32 ticks
                   per template for CONV/MT; one partitioned domain sweep for
                   PC). Cross-epoch repetition of a nonce value is legitimate
                   and is NOT counted at this scope.
NR-global-run      diagnostic only; counters never reset within a run.
NR-subsweep        auxiliary diagnostic: the first W = floor(S/2N) ticks of each
                   round, below the saturation threshold, so traversal policies
                   remain distinguishable (Comparison C).

Metric definitions (brief sections 13-14)
-----------------------------------------
C_nonce  total nonce evaluations (every miner evaluation counts)
U_nonce  distinct nonce32 values evaluated in the scope
R_nonce  C_nonce - U_nonce   (counts ALL repetition, including one miner
         re-sweeping values across template epochs)
rho_nonce = R_nonce / C_nonce
M_ge2    measure of nonce values evaluated by >= 2 DISTINCT miners
m_max    maximum number of distinct miners sharing any one nonce value
O_ij     |V_i ∩ V_j| pairwise; reported as mean / median / max

C_exact / U_exact / R_exact / rho_exact use identity (template_id, nonce32):
evaluations under different templates are never exact duplicates.

R_nonce is repetition-based; M_ge2 / m_max / O_ij are cross-miner-based. Both
families are reported because "nonce-value reuse" (same value used by multiple
miners) and total value repetition differ exactly when one miner re-sweeps its
own values — PoCol's case.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from experiments.stage8xnr.config.nr_config import S_NONCE
from experiments.stage8xnr.src.noncedomain import (
    Arc,
    max_multiplicity,
    measure_covered_at_least,
    multiplicity_profile,
    pairwise_overlap_summary,
    union_measure,
)


@dataclass
class ScopeMetrics:
    scope: str
    C_nonce: int = 0
    U_nonce: int = 0
    M_ge2: int = 0
    m_max: int = 0
    O_mean: float = 0.0
    O_median: float = 0.0
    O_max: int = 0
    C_exact: int = 0
    U_exact: int = 0

    @property
    def R_nonce(self) -> int:
        return self.C_nonce - self.U_nonce

    @property
    def rho_nonce(self) -> float:
        return self.R_nonce / self.C_nonce if self.C_nonce else 0.0

    @property
    def R_exact(self) -> int:
        return self.C_exact - self.U_exact

    @property
    def rho_exact(self) -> float:
        return self.R_exact / self.C_exact if self.C_exact else 0.0

    def as_row(self) -> Dict[str, object]:
        return {
            "scope": self.scope,
            "C_nonce": self.C_nonce, "U_nonce": self.U_nonce,
            "R_nonce": self.R_nonce, "rho_nonce": self.rho_nonce,
            "M_ge2": self.M_ge2, "m_max": self.m_max,
            "O_mean": self.O_mean, "O_median": self.O_median, "O_max": self.O_max,
            "C_exact": self.C_exact, "U_exact": self.U_exact,
            "R_exact": self.R_exact, "rho_exact": self.rho_exact,
        }


def cross_miner_stats(coverage_arcs: Sequence[Arc]) -> Dict[str, int]:
    """M_ge2 and m_max from one COVERAGE arc per miner (length clamped to S)."""
    prof = multiplicity_profile(coverage_arcs)
    return {"M_ge2": measure_covered_at_least(prof, 2),
            "m_max": max_multiplicity(prof)}


def scope_from_miners(
    scope: str,
    eval_counts: Sequence[int],
    coverage_arcs: Sequence[Arc],
    exact_C: int,
    exact_U: int,
    pair_summary: Optional[Dict[str, float]] = None,
    pairwise_zero: bool = False,
) -> ScopeMetrics:
    """Assemble one scope's metrics from per-miner exact traversal data.

    eval_counts    per-miner evaluation counts in the scope (exact ints)
    coverage_arcs  per-miner SET of touched values as one arc each
    exact_*        exact-input totals for the scope (computed by the engine,
                   which knows the template structure)
    pair_summary   precomputed O_ij summary; if None and pairwise_zero, all
                   pairwise overlaps are exactly zero (verified disjointness);
                   if None otherwise, derived from the coverage arcs.
    """
    m = ScopeMetrics(scope=scope)
    m.C_nonce = int(sum(eval_counts))
    m.U_nonce = union_measure(coverage_arcs)
    cm = cross_miner_stats(coverage_arcs)
    m.M_ge2, m.m_max = cm["M_ge2"], cm["m_max"]
    if pair_summary is not None:
        m.O_mean = float(pair_summary["mean"])
        m.O_median = float(pair_summary["median"])
        m.O_max = int(pair_summary["max"])
    elif pairwise_zero:
        m.O_mean = m.O_median = 0.0
        m.O_max = 0
    else:
        # generic exact fallback: equal-length arcs summary or full saturation
        lengths = {a[1] for a in coverage_arcs}
        if lengths == {S_NONCE}:
            n = len(coverage_arcs)
            m.O_mean = m.O_median = float(S_NONCE)
            m.O_max = S_NONCE
        elif len(lengths) == 1:
            summ = pairwise_overlap_summary(
                [a[0] for a in coverage_arcs], lengths.pop())
            m.O_mean, m.O_median, m.O_max = (
                float(summ["mean"]), float(summ["median"]), int(summ["max"]))
        else:
            raise ValueError(
                "pairwise summary for unequal partial arcs must be precomputed")
    m.C_exact = int(exact_C)
    m.U_exact = int(exact_U)
    if m.U_nonce > m.C_nonce or m.U_exact > m.C_exact:
        raise AssertionError("unique count exceeds evaluation count")
    return m


@dataclass
class RunAccumulator:
    """Aggregates round-scope metrics into run-level summaries."""
    rows: List[Dict[str, object]] = field(default_factory=list)

    def add_round(self, round_index: int, duration_s: float, block: bool,
                  metrics: Dict[str, ScopeMetrics]) -> None:
        row: Dict[str, object] = {
            "round": round_index, "duration_s": duration_s, "block": int(block),
        }
        for name, sm in metrics.items():
            for k, v in sm.as_row().items():
                if k == "scope":
                    continue
                row[f"{name}_{k}"] = v
        self.rows.append(row)

    def mean(self, col: str) -> float:
        vals = [float(r[col]) for r in self.rows if col in r]
        return sum(vals) / len(vals) if vals else 0.0
