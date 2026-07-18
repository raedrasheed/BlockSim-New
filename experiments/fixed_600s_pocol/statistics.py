"""Statistics for the fixed-600s experiment (spec §14).

Reuses the tested bootstrap machinery from
experiments/continuous_distributed_effort/statistics.py:
- summarize: mean / median / std / 2.5th & 97.5th percentiles / bootstrap 95% CI
  / min / max
- paired_diff: paired mean & median difference, Cohen's d, bootstrap CI
- tost_equivalence: equivalence only within a PRE-REGISTERED margin

Note (spec §14): two similar Cohen's d values against a third baseline are NEVER
quoted as 'statistically indistinguishable'; PoCol vs independent-header PoW is
always a DIRECT paired comparison plus TOST.
"""
from experiments.continuous_distributed_effort.statistics import (  # noqa: F401
    summarize, paired_diff, tost_equivalence,
)

# Pre-registered BEFORE inspecting results: PoCol vs independent-header PoW is
# declared equivalent only if the TOST CI lies within +/-1% of the control mean.
POCOL_VS_IND_MARGIN_REL = 0.01
